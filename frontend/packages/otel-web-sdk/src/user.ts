/**
 * @fileoverview User tracking module.
 *
 * Stores user information in memory for session attribution.
 * Never logs user data automatically for privacy.
 */

/** User information */
export interface UserInfo {
  id: string
  attributes?: Record<string, string>
}

// Module state
let currentUser: UserInfo | null = null

/**
 * Set the current user for session attribution.
 *
 * @param id - Unique user identifier (must be non-empty string)
 * @param attributes - Optional user attributes (email, role, etc.)
 *
 * @example
 * ```ts
 * setUser('user-123', { email: 'user@example.com', role: 'admin' })
 * ```
 */
export function setUser(id: string, attributes?: Record<string, string>): void {
  if (!id || typeof id !== 'string') return
  currentUser = { id, attributes }
}

/**
 * Clear the current user (e.g., on logout).
 */
export function clearUser(): void {
  currentUser = null
}

/**
 * Get the current user info.
 *
 * @returns User info or null if no user is set
 */
export function getUser(): UserInfo | null {
  return currentUser
}
