/**
 * Shared constants for E2E tests.
 *
 * The mock LLM provider uses "use <tool_name> <args>" pattern matching
 * to detect tool requests. These constants encode that convention.
 */

/** AG-UI Chat page route */
export const CHAT_ROUTE = '/chat'

/** MCP Chat page route */
export const MCP_CHAT_ROUTE = '/mcp-chat'

/** Tool invocation commands (mock LLM format: "use <tool_name> <args>") */
export const ECHO_COMMAND = 'use echo_text hello world'
export const ECHO_EXPECTED = 'Echo: hello world'

export const ADD_COMMAND = 'use add_numbers 5 3'
export const ADD_EXPECTED = '8'

/** Timeouts */
export const RESPONSE_TIMEOUT = 30_000
export const MCP_CONNECT_TIMEOUT = 15_000

/** Backend health check URL */
export const BACKEND_HEALTH_URL = 'http://localhost:8888/health'
export const BACKEND_READY_TIMEOUT = 60_000
