/**
 * Shared test constants used across multiple test files.
 * Single-file constants should remain local to their test file.
 */

export const TestDefaults = {
  // API endpoints (used in 3 files)
  API_URL: '/api',
  API_URL_CUSTOM: '/api/custom',
  API_URL_V2: '/api/v2',

  // Session ID (used in 4 files)
  SESSION_ID: 'test-session-uuid-12345',
} as const;
