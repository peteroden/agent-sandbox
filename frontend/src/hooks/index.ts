/**
 * Barrel export for all hooks.
 *
 * Import hooks from this module for consistent instrumentation across the app:
 *
 * @example
 * ```typescript
 * import { useChat, useTelemetry, useInstrumentedAgent } from './hooks';
 * ```
 */

export { useChat } from './useChat'
export type { UseChatOptions, UseChatReturn, Tool, ToolHandler } from './useChat'

export { useTelemetry } from './useTelemetry'
export type { UseTelemetryReturn } from './useTelemetry'

export { useInstrumentedAgent } from './useInstrumentedAgent'
export type { UseInstrumentedAgentOptions, UseInstrumentedAgentReturn } from './useInstrumentedAgent'
