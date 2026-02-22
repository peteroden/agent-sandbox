/**
 * @fileoverview Tests for user tracking.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'

// Test constants
const TEST_USER_ID = 'user-123'
const TEST_USER_EMAIL = 'user@example.com'

describe('user', () => {
  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(async () => {
    const { clearUser } = await import('../src/user')
    clearUser()
  })

  it('setUser stores user information', async () => {
    // Arrange
    const { setUser, getUser } = await import('../src/user')

    // Act
    setUser(TEST_USER_ID, { email: TEST_USER_EMAIL })

    // Assert
    const user = getUser()
    expect(user).not.toBeNull()
    expect(user?.id).toBe(TEST_USER_ID)
    expect(user?.attributes?.email).toBe(TEST_USER_EMAIL)
  })

  it('clearUser removes user information', async () => {
    // Arrange
    const { setUser, clearUser, getUser } = await import('../src/user')
    setUser(TEST_USER_ID)

    // Act
    clearUser()

    // Assert
    expect(getUser()).toBeNull()
  })

  it('getUser returns null when no user is set', async () => {
    // Arrange
    const { getUser, clearUser } = await import('../src/user')
    clearUser()

    // Act & Assert
    expect(getUser()).toBeNull()
  })

  it('setUser overwrites previous user', async () => {
    // Arrange
    const { setUser, getUser } = await import('../src/user')
    setUser('old-user')

    // Act
    setUser('new-user', { role: 'admin' })

    // Assert
    const user = getUser()
    expect(user?.id).toBe('new-user')
    expect(user?.attributes?.role).toBe('admin')
  })

  it('setUser works without attributes', async () => {
    // Arrange
    const { setUser, getUser } = await import('../src/user')

    // Act
    setUser(TEST_USER_ID)

    // Assert
    const user = getUser()
    expect(user?.id).toBe(TEST_USER_ID)
    expect(user?.attributes).toBeUndefined()
  })
})
