import { useState, useEffect, useRef, useCallback, useMemo } from 'preact/hooks'
import {
  HttpAgent,
  type Message,
  type BaseEvent,
  type AgentSubscriber,
  type TextMessageContentEvent,
  type ToolCallStartEvent,
  type ToolCallEndEvent,
  type ToolCallArgsEvent,
  type RunErrorEvent,
  type Tool,
} from '@ag-ui/client'
import { context, SpanStatusCode, trace, type Span } from '@opentelemetry/api'
import { getTracer, startSpan, logger, type Span as TelemetrySpan } from '../services/telemetry'

export type { Tool }

export type ToolHandler = (args: Record<string, unknown>) => Promise<string> | string

export interface UseChatOptions {
  url: string
  tools?: Tool[]
  toolHandlers?: Record<string, ToolHandler>
  enableTelemetry?: boolean
  onEvent?: (event: BaseEvent) => void
  onTextContent?: (content: string, messageId: string) => void
  onToolCallStart?: (toolName: string, toolCallId: string) => void
  onToolCallArgs?: (toolCallId: string, args: string) => void
  onToolCallEnd?: (toolCallId: string, toolName: string, args: string) => void
  onError?: (error: Error) => void
  onRunStart?: () => void
  onRunEnd?: () => void
}

export interface UseChatReturn {
  messages: Message[]
  isLoading: boolean
  error: Error | null
  agent: HttpAgent
  sendMessage: (content: string) => Promise<void>
  clearMessages: () => void
  addToolResult: (toolCallId: string, result: string) => void
}

export function useChat(options: UseChatOptions): UseChatReturn {
  const { 
    url, 
    tools, 
    toolHandlers, 
    enableTelemetry = false,
    onEvent, 
    onTextContent, 
    onToolCallStart, 
    onToolCallArgs,
    onToolCallEnd, 
    onError, 
    onRunStart, 
    onRunEnd 
  } = options

  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const agent = useMemo(() => new HttpAgent({ url }), [url])
  const agentRef = useRef<HttpAgent | null>(null)
  const toolCallArgsRef = useRef<Map<string, { name: string; args: string }>>(new Map())
  const toolSpansRef = useRef<Map<string, TelemetrySpan>>(new Map())
  const runSpanRef = useRef<Span | null>(null)
  const isLoadingRef = useRef(false)

  // Update ref when state changes
  useEffect(() => {
    isLoadingRef.current = isLoading
  }, [isLoading])

  const executeToolHandler = useCallback(async (toolCallId: string, toolName: string, argsJson: string) => {
    const handler = toolHandlers?.[toolName]
    if (!handler || !agentRef.current) return

    logger.debug('Executing tool handler', { 'tool.name': toolName, 'tool.call_id': toolCallId })

    try {
      const args = JSON.parse(argsJson || '{}')
      const result = await handler(args)
      
      logger.info('Tool handler completed', { 'tool.name': toolName, 'tool.call_id': toolCallId })

      agentRef.current.addMessage({
        id: crypto.randomUUID(),
        role: 'tool',
        toolCallId,
        content: result,
      } as Message)
      
      // Continue the conversation with the tool result
      await agentRef.current.runAgent({ tools })
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      logger.error('Tool handler failed', { 
        'tool.name': toolName, 
        'tool.call_id': toolCallId,
        'error.message': error.message,
      })
      setError(error)
      onError?.(error)
    }
  }, [toolHandlers, tools, onError])

  useEffect(() => {
    agentRef.current = agent
    toolCallArgsRef.current = new Map()

    const subscriber: AgentSubscriber = {
      onMessagesChanged: ({ messages: agentMessages }) => {
        setMessages([...agentMessages])
      },
      onEvent: ({ event }) => {
        // Add event to all active tool spans when telemetry is enabled
        if (enableTelemetry) {
          toolSpansRef.current.forEach((span) => {
            span.addEvent(event.type)
          })
        }
        onEvent?.(event)
      },
      onTextMessageContentEvent: ({ event }) => {
        const e = event as TextMessageContentEvent
        onTextContent?.(e.delta, e.messageId)
      },
      onToolCallStartEvent: ({ event }) => {
        const e = event as ToolCallStartEvent
        toolCallArgsRef.current.set(e.toolCallId, { name: e.toolCallName, args: '' })
        
        logger.info('Tool call started', { 'tool.name': e.toolCallName, 'tool.call_id': e.toolCallId })

        // Start telemetry span for tool call
        if (enableTelemetry) {
          const span = startSpan('agui.tool_call', {
            attributes: {
              'tool.call_id': e.toolCallId,
              'tool.name': e.toolCallName,
            },
          })
          toolSpansRef.current.set(e.toolCallId, span)
        }
        
        onToolCallStart?.(e.toolCallName, e.toolCallId)
      },
      onToolCallArgsEvent: ({ event }) => {
        const e = event as ToolCallArgsEvent
        const existing = toolCallArgsRef.current.get(e.toolCallId)
        if (existing) {
          existing.args += e.delta
        }
        onToolCallArgs?.(e.toolCallId, e.delta)
      },
      onToolCallEndEvent: ({ event }) => {
        const e = event as ToolCallEndEvent
        const toolCall = toolCallArgsRef.current.get(e.toolCallId)
        const toolName = toolCall?.name || ''
        const args = toolCall?.args || ''
        
        logger.info('Tool call ended', { 'tool.name': toolName, 'tool.call_id': e.toolCallId })

        // End telemetry span for tool call
        if (enableTelemetry) {
          const span = toolSpansRef.current.get(e.toolCallId)
          if (span) {
            span.end()
            toolSpansRef.current.delete(e.toolCallId)
          }
        }
        
        onToolCallEnd?.(e.toolCallId, toolName, args)
        
        // Auto-execute if handler exists
        if (toolHandlers?.[toolName]) {
          executeToolHandler(e.toolCallId, toolName, args)
        }
        
        toolCallArgsRef.current.delete(e.toolCallId)
      },
      onRunStartedEvent: () => {
        logger.info('Agent run started')
        onRunStart?.()
      },
      onRunFinishedEvent: () => {
        logger.info('Agent run finished')
        onRunEnd?.()
      },
      onRunErrorEvent: ({ event }) => {
        const e = event as RunErrorEvent
        const err = new Error(e.message)
        logger.error('Agent run error', { 'error.message': e.message })
        setError(err)
        onError?.(err)
      },
    }

    const { unsubscribe } = agent.subscribe(subscriber)

    return () => {
      // End any orphaned spans on cleanup
      if (enableTelemetry) {
        toolSpansRef.current.forEach((span) => span.end())
        toolSpansRef.current.clear()
      }
      unsubscribe()
      agentRef.current = null
    }
  }, [agent, tools, toolHandlers, enableTelemetry, onEvent, onTextContent, onToolCallStart, onToolCallArgs, onToolCallEnd, onError, onRunStart, onRunEnd, executeToolHandler])

  const sendMessage = useCallback(async (content: string) => {
    if (!agentRef.current || isLoadingRef.current) return

    logger.info('Sending chat message', { 'message.length': content.length })

    const tracer = getTracer()
    const span = tracer.startSpan('chat.send_message')
    runSpanRef.current = span

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
    }

    span.setAttribute('message.id', userMessage.id)

    setError(null)
    setIsLoading(true)

    try {
      // Set the span as active so fetch instrumentation injects traceparent header
      const activeContext = trace.setSpan(context.active(), span)
      await context.with(activeContext, async () => {
        agentRef.current!.addMessage(userMessage)
        await agentRef.current!.runAgent({ tools })
      })
      span.setStatus({ code: SpanStatusCode.OK })
      logger.info('Chat message sent successfully', { 'message.id': userMessage.id })
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err))
      span.setStatus({ code: SpanStatusCode.ERROR, message: error.message })
      span.recordException(error)
      logger.error('Failed to send chat message', { 'error.message': error.message })
      setError(error)
      onError?.(error)
    } finally {
      span.end()
      runSpanRef.current = null
      setIsLoading(false)
    }
  }, [tools, onError])

  const clearMessages = useCallback(() => {
    if (agentRef.current) {
      agentRef.current.setMessages([])
    }
    setMessages([])
    setError(null)
  }, [])

  const addToolResult = useCallback((toolCallId: string, result: string) => {
    if (!agentRef.current) return

    agentRef.current.addMessage({
      id: crypto.randomUUID(),
      role: 'tool',
      toolCallId,
      content: result,
    } as Message)
  }, [])

  return {
    messages,
    isLoading,
    error,
    agent,
    sendMessage,
    clearMessages,
    addToolResult,
  }
}
