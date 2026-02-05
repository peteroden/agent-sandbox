/**
 * Barrel export for all hooks.
 *
 * Import hooks from this module for consistent instrumentation across the app:
 *
 * @example
 * ```typescript
 * import { useChat } from './hooks';
 * ```
 */

export { useChat } from './useChat'
export type { UseChatOptions, UseChatReturn, Tool, ToolHandler } from './useChat'
