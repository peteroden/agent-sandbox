import { useEffect } from 'preact/hooks'
import { ChatProvider, ChatHeader, MessageList, MessageInput } from 'react-ag-ui'
import { useChat } from '../hooks/useChat'
import { logger } from '../services/telemetry'
import 'react-ag-ui/dist/styles.css'

const AGENT_URL = import.meta.env.VITE_AGENT_URL ?? '/api'

export function Chat() {
  const { agent } = useChat({ url: AGENT_URL, enableTelemetry: true })

  useEffect(() => {
    logger.info('Chat page loaded', { 'agent.url': AGENT_URL })
  }, [])

  return (
    <ChatProvider agent={agent}>
      <div class="w-full max-w-md h-[80vh] border border-gray-300 flex flex-col mx-auto">
        <ChatHeader />
        <div class="flex-1 overflow-y-auto p-2.5">
          <MessageList />
        </div>
        <MessageInput />
      </div>
    </ChatProvider>
  )
}
