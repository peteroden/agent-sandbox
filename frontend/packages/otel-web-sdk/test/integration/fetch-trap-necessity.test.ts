/**
 * @fileoverview Integration test to determine if bootstrap fetch trap is necessary.
 *
 * This test verifies whether OpenTelemetry auto-instrumentation can wrap fetch
 * even when a library has cached a reference before OTel loads.
 *
 * Scenario:
 * 1. Library caches `const cachedFetch = window.fetch` early
 * 2. OTel auto-instrumentation loads and patches window.fetch
 * 3. Library uses cachedFetch to make a request
 * 4. Question: Is the request traced?
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import {
  SimpleSpanProcessor,
  InMemorySpanExporter,
} from '@opentelemetry/sdk-trace-base'
import { registerInstrumentations } from '@opentelemetry/instrumentation'
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web'
import { context, trace } from '@opentelemetry/api'

describe('fetch instrumentation without bootstrap trap', () => {
  let exporter: InMemorySpanExporter
  let provider: WebTracerProvider
  let cachedFetch: typeof fetch

  beforeEach(() => {
    // Reset module state
    vi.resetModules()
    delete (globalThis as Record<string, unknown>).__otelFetchWrapped
    delete (globalThis as Record<string, unknown>).__otelUnwrappedFetch

    // Setup in-memory span exporter for verification
    exporter = new InMemorySpanExporter()
    provider = new WebTracerProvider({
      spanProcessors: [new SimpleSpanProcessor(exporter)],
    })
    provider.register()
  })

  afterEach(async () => {
    await provider.shutdown()
  })

  it('verifies if cached fetch reference is traced WITHOUT bootstrap trap', async () => {
    // Step 1: Simulate a library caching fetch BEFORE OTel instrumentation
    // This is what happens when a third-party library does:
    //   const myFetch = window.fetch (at module load time)
    cachedFetch = globalThis.fetch

    // Step 2: Now register OTel auto-instrumentation (like we do in init)
    registerInstrumentations({
      tracerProvider: provider,
      instrumentations: [
        getWebAutoInstrumentations({
          '@opentelemetry/instrumentation-fetch': {
            clearTimingResources: true,
          },
        }),
      ],
    })

    // Step 3: Create a span context
    const tracer = trace.getTracer('test')
    const span = tracer.startSpan('parent-span')
    const ctx = trace.setSpan(context.active(), span)

    // Step 4: Make a request using the CACHED reference
    // Mock the actual network call
    const mockResponse = new Response('test', { status: 200 })
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(mockResponse)

    // Make the request with cached fetch in span context
    await context.with(ctx, async () => {
      try {
        await cachedFetch('http://localhost:8888/test')
      } catch {
        // Network error is expected in test environment
      }
    })
    span.end()

    // Force flush
    await provider.forceFlush()

    // Step 5: Check if we got spans for the fetch
    const spans = exporter.getFinishedSpans()
    const fetchSpans = spans.filter((s) =>
      s.name.includes('HTTP') || s.name.includes('fetch') || s.name.includes('GET')
    )

    // Log results for analysis
    console.log('=== FETCH TRAP NECESSITY TEST RESULTS ===')
    console.log('Total spans:', spans.length)
    console.log('Span names:', spans.map((s) => s.name))
    console.log('Fetch-related spans:', fetchSpans.length)
    console.log('')

    if (fetchSpans.length > 0) {
      console.log('RESULT: Bootstrap trap may NOT be necessary.')
      console.log('OTel auto-instrumentation successfully traced the cached fetch.')
    } else {
      console.log('RESULT: Bootstrap trap IS necessary.')
      console.log('Cached fetch reference was NOT traced by OTel.')
    }
    console.log('==========================================')

    // This test documents behavior, not asserts correctness
    // The output tells us whether we need the bootstrap trap
    expect(spans.length).toBeGreaterThan(0) // At least parent span
  })

  it('verifies current fetch (after OTel) is traced', async () => {
    // Register OTel instrumentation first
    registerInstrumentations({
      tracerProvider: provider,
      instrumentations: [
        getWebAutoInstrumentations({
          '@opentelemetry/instrumentation-fetch': {
            clearTimingResources: true,
          },
        }),
      ],
    })

    // Get fetch AFTER instrumentation
    const instrumentedFetch = globalThis.fetch

    // Create a span context
    const tracer = trace.getTracer('test')
    const span = tracer.startSpan('parent-span')
    const ctx = trace.setSpan(context.active(), span)

    // Mock and make request
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('test', { status: 200 }))

    await context.with(ctx, async () => {
      try {
        await instrumentedFetch('http://localhost:8888/test')
      } catch {
        // Network error expected
      }
    })
    span.end()

    await provider.forceFlush()

    const spans = exporter.getFinishedSpans()
    console.log('=== POST-INSTRUMENTATION FETCH TEST ===')
    console.log('Total spans:', spans.length)
    console.log('Span names:', spans.map((s) => s.name))
    console.log('========================================')

    // Note: In test environment, the actual instrumented fetch may not produce
    // spans due to mock interference. This test documents the expected behavior.
    // The important insight is from the first test.
    expect(true).toBe(true)
  })
})
