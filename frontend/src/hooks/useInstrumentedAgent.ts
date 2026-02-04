import { useMemo } from 'preact/hooks'
import { HttpAgent } from '@ag-ui/client'
import { getSessionId } from '../services/telemetry'

/**
 * Options for useInstrumentedAgent hook
 */
export interface UseInstrumentedAgentOptions {
  /** Backend agent URL (e.g., '/api' or 'http://localhost:8888') */
  url: string
}

/**
 * Return type for useInstrumentedAgent hook
 */
export interface UseInstrumentedAgentReturn {
  /** The HttpAgent instance configured for the given URL */
  agent: HttpAgent
  /** Current session ID for trace correlation */
  sessionId: string | null
}

/**
 * Hook that creates an instrumented HttpAgent for AG-UI protocol communication.
 *
 * The agent is configured to work with OpenTelemetry's fetch instrumentation,
 * which automatically injects `traceparent` headers for distributed tracing.
 *
 * The session ID is provided for additional trace correlation in custom
 * instrumentation scenarios.
 *
 * @param options - Configuration options including the backend URL
 * @returns An object containing the agent instance and session ID
 *
 * @example
 * ```tsx
 * import { useInstrumentedAgent } from '../hooks';
 * import { ChatProvider, MessageList } from 'react-ag-ui';
 *
 * function MyChat() {
 *   const { agent, sessionId } = useInstrumentedAgent({ url: '/api' });
 *
 *   console.log('Session:', sessionId);
 *
 *   return (
 *     <ChatProvider agent={agent}>
 *       <MessageList />
 *     </ChatProvider>
 *   );
 * }
 * ```
 */
export function useInstrumentedAgent(options: UseInstrumentedAgentOptions): UseInstrumentedAgentReturn {
  const { url } = options

  // Create agent with memoization based on URL
  // The fetch instrumentation from initTelemetry will automatically inject
  // traceparent headers for requests to the backend
  const agent = useMemo(() => new HttpAgent({ url }), [url])

  // Get session ID for trace correlation
  const sessionId = useMemo(() => getSessionId(), [])

  return useMemo(() => ({
    agent,
    sessionId,
  }), [agent, sessionId])
}
