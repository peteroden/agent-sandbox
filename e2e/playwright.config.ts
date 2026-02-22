import { defineConfig } from '@playwright/test'

/**
 * Playwright config for Agent Sandbox E2E tests.
 *
 * Uses scripts/dev.sh --mock to start the full stack (frontend + backend + MCP servers)
 * with the mock LLM provider for deterministic, fast tests.
 *
 * An in-memory OTLP collector (global-setup.ts) receives backend trace exports
 * so tests can verify end-to-end trace propagation through the backend.
 */
export default defineConfig({
  globalSetup: './global-setup.ts',
  globalTeardown: './global-teardown.ts',

  testDir: './tests',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'html',

  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],

  webServer: {
    command: [
      'cd .. &&',
      'ENABLE_INSTRUMENTATION=true',
      'OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf',
      'OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4319/v1/traces',
      'bash scripts/dev.sh --mock',
    ].join(' '),
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    stdout: 'pipe',
    stderr: 'pipe',
  },
})
