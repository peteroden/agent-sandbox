import { Route, Switch, Link } from 'wouter'
import { Home } from './pages/Home'
import { Chat } from './pages/Chat'
import { McpChat } from './pages/McpChat'
import { McpAppDemo } from './pages/McpAppDemo'
import { Report } from './pages/Report'
import { ObserveDashboard } from './pages/observe/ObserveDashboard'

export function App() {
  return (
    <div class="min-h-screen bg-gray-50">
      <nav class="bg-white shadow-sm">
        <div class="container mx-auto px-4 py-3 flex gap-4">
          <Link href="/" class="text-blue-600 hover:text-blue-800">Home</Link>
          <Link href="/chat" class="text-blue-600 hover:text-blue-800">Chat</Link>
          <Link href="/mcp-chat" class="text-blue-600 hover:text-blue-800">MCP Chat</Link>
          <Link href="/mcp-app" class="text-blue-600 hover:text-blue-800">MCP App</Link>
          <Link href="/report" class="text-blue-600 hover:text-blue-800">Report</Link>
          <Link href="/observe" class="text-blue-600 hover:text-blue-800">Observe</Link>
        </div>
      </nav>
      <main class="py-6">
        <Switch>
          <Route path="/" component={Home} />
          <Route path="/chat" component={Chat} />
          <Route path="/mcp-chat" component={McpChat} />
          <Route path="/mcp-app" component={McpAppDemo} />
          <Route path="/report" component={Report} />
          <Route path="/observe" component={ObserveDashboard} />
          <Route path="/observe/:rest*" component={ObserveDashboard} />
          <Route>404: Not Found</Route>
        </Switch>
      </main>
    </div>
  )
}

