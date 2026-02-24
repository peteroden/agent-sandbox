# OTel Web SDK Gap Analysis: Commercial Observability Parity

This report compares the `@agent-sandbox/otel-web-sdk` package against commercial
frontend observability SDKs (Datadog RUM, Dynatrace RUM, New Relic Browser, Sentry)
and estimates the effort required to close each gap.

## Current SDK Baseline

The SDK currently provides:

* Distributed tracing (fetch, XHR, document-load, user-interaction auto-instrumentation)
* Structured logging with automatic trace correlation
* Histogram metrics via `trackMetric()`
* Global error capture (`window.onerror`, `window.onunhandledrejection`)
* Session ID (persisted in `sessionStorage`)
* PII path sanitization for stack traces
* Preact error boundary component (`OTelErrorBoundary`)
* W3C Trace Context propagation with Zone.js async context management
* Bootstrap fetch trap (IIFE for early `fetch` reference caching)
* OTLP HTTP/JSON export for all three signals (traces, logs, metrics)
* Page-unload flushing via `visibilitychange` and `pagehide`

| Metric | Value |
| ------ | ----- |
| Source LOC | 1,084 |
| Test LOC | 1,169 |
| Source files | 12 |
| Test files | 10 |

## Gap Inventory

### Gap 1: Core Web Vitals

Commercial SDKs auto-collect Core Web Vitals out of the box.

| Metric | Collected? |
| ------ | ---------- |
| Largest Contentful Paint (LCP) | No |
| Cumulative Layout Shift (CLS) | No |
| Interaction to Next Paint (INP) | No |
| First Contentful Paint (FCP) | No |
| Time to First Byte (TTFB) | No |

The SDK only gets navigation timing from document-load instrumentation. There is no
`PerformanceObserver`-based CWV collection.

### Gap 2: SPA Route Change Tracking

Datadog and New Relic auto-instrument SPA route transitions as "views," capturing
route change duration, resources loaded per view, errors per view, and loading states.
The SDK has no concept of views or pages. There is no integration with Wouter, React
Router, or History API changes.

### Gap 3: User Identity on Telemetry

`setUser()` stores user info in memory but never attaches it to spans, logs, or
metrics. Commercial SDKs stamp every telemetry event with user ID, email, plan tier,
and similar attributes, enabling per-user debugging and cohort analysis.

### Gap 4: Session Timeout and Rotation

Session ID persists for the entire `sessionStorage` lifetime with no rotation.
Commercial SDKs rotate session IDs after inactivity timeouts (typically 15 to 30
minutes) to properly segment distinct user visits in long-lived tabs.

### Gap 5: Long Task Detection

Tasks blocking the main thread longer than 50ms are tracked by all commercial SDKs.
OpenTelemetry's `@opentelemetry/instrumentation-long-task` exists but is not enabled
in the SDK despite the auto-instrumentations bundle being present.

### Gap 6: Global Custom Attributes

Commercial SDKs let you set global tags (for example, `env:production`,
`team:checkout`, `feature_flag:new_cart`) that get attached to every event. The SDK
has no API to add custom attributes globally to all spans, logs, and metrics.

### Gap 7: Smart Sampling (Keep Errors)

Commercial SDKs offer conditional sampling (sample 100% of errors, 10% of normal
sessions), priority sampling (keep traces with errors), and head-based plus tail-based
sampling options. The SDK only has a flat `TraceIdRatioBasedSampler` with no ability to
always keep error traces or sample by route or user.

### Gap 8: Baggage Propagation

Only `W3CTraceContextPropagator` is configured. No `W3CBaggagePropagator` is present,
so custom context (user ID, A/B test bucket) cannot propagate across service boundaries.

### Gap 9: Richer Metric Types

`trackMetric()` only creates histograms. Commercial SDKs expose counters, gauges, and
distributions. There is no API for incrementing counters (for example, button click
count) or tracking gauge values (for example, cart size).

### Gap 10: Resource and Asset Monitoring

Commercial SDKs collect detailed waterfall data for every resource: JS, CSS, image,
and font load times and sizes; cache hit rates; CDN performance; and slow resource
detection. The SDK only gets basic resource timing through document-load, not ongoing
`PerformanceObserver` monitoring for dynamically loaded resources.

### Gap 11: Error Fingerprinting and Source Maps

Sentry, Datadog, and New Relic perform intelligent error grouping by deduplicating
errors by stack signature, source map resolution, and custom fingerprints. The SDK has
no source map upload mechanism, no deduplication, and no error fingerprinting.

### Gap 12: Offline Buffering

When the network is unavailable, Datadog and New Relic buffer events locally
(IndexedDB) and flush when connectivity returns. The SDK relies on default batch
processor retry with no persistent buffering.

### Gap 13: Session Replay

All three major vendors offer session replay: recording DOM mutations, mouse movements,
scroll positions, and input interactions to reconstruct a visual replay of user
sessions. This capability is completely absent from the SDK and represents the largest
single feature gap.

Session replay is predominantly a frontend SDK responsibility. The capture pipeline
works as follows:

1. **Recording (frontend):** The SDK uses `MutationObserver` to capture DOM changes,
   plus event listeners for mouse movement, clicks, scrolls, input, and resize.
   Libraries like `rrweb` serialize an initial DOM snapshot and then record incremental
   mutations as a compact event stream. This runs in the user's browser in real time.
2. **Transport (frontend to backend):** The recorded event stream is compressed and
   sent in chunks to a backend endpoint, alongside a session ID and trace context.
3. **Playback (dashboard):** The backend stores the raw event stream. A separate
   frontend viewer reconstructs the DOM from the snapshot plus mutations to replay the
   session. This is a dashboard or UI concern, not an SDK concern.

The backend's role is limited to storage, indexing, and serving the replay data. It
does not analyze or reconstruct anything. The intelligence (what to record, privacy
masking, compression, sampling, linking to traces) lives entirely in the frontend SDK.
This is why session replay is the largest item in the gap analysis: the frontend SDK
must handle DOM serialization, input masking, event throttling, chunked upload, storage
quota awareness, and privacy controls, all running in the browser's main thread without
degrading performance.

### Gap 14: Rage and Dead Click Detection

Dynatrace and Datadog detect rage clicks (rapid repeated clicks on the same element)
and dead clicks (clicks that produce no DOM change). This helps identify UX frustration
points and is entirely missing from the SDK.

### Gap 15: ANR Detection

Dynatrace and New Relic detect Application Not Responding (ANR) states when the main
thread is blocked for extended periods (longer than 5 seconds). The SDK has no
equivalent.

### Gap 16: Consent and Privacy Framework

Commercial SDKs provide built-in GDPR consent mode (collect versus do not collect
before consent), data masking rules (mask inputs, scrub PII from URLs), and cookie or
storage opt-out capabilities. The SDK has basic path sanitization but no consent
framework, no URL parameter scrubbing, and no form input masking.

### Gap 17: Feature Flag Correlation

All major vendors integrate with feature flag tools (LaunchDarkly, Split) to correlate
telemetry with active experiments. This is not present in the SDK.

### Gap 18: Network Error Monitoring (Deep)

Beyond HTTP status codes, commercial SDKs capture DNS lookup time, TCP connect, TLS
handshake (from `PerformanceResourceTiming`), request and response body size, CORS
errors with actionable diagnostics, and GraphQL operation-level tracking. The fetch and
XHR instrumentations capture basic request spans but lack this depth.

## Effort Estimates

> [!NOTE]
> Source LOC includes types, exports, and JSDoc. Test LOC assumes thorough coverage per
> project TDD standards. Effort is calendar time for one experienced developer.

### Quick Wins (Under 1 Day Each)

| # | Gap | Effort | Source LOC | Test LOC | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 3 | User identity on telemetry | 0.5 day | 40-60 | 60-80 | None | Modify `setUser()` to inject attributes via a `SpanProcessor`. Touches `init.ts`, `user.ts`, `logger.ts`. |
| 5 | Long task detection | 0.5 day | 20-30 | 40-60 | Already bundled | Enable `@opentelemetry/instrumentation-long-task` in auto-instrumentations config. Mostly configuration plus tests. |
| 8 | Baggage propagation | 0.5 day | 15-25 | 40-60 | Already available | Switch to `CompositePropagator` with `W3CTraceContextPropagator` and `W3CBaggagePropagator`. Add `setBaggage()` helper. |

### Small Items (1 to 2 Days Each)

| # | Gap | Effort | Source LOC | Test LOC | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Core Web Vitals | 1-2 days | 120-160 | 150-200 | `web-vitals` (~3KB) | Wrap Google's `web-vitals` library, emit each as a metric plus span event. Needs `PerformanceObserver` setup and attribution mode. |
| 4 | Session timeout and rotation | 1 day | 80-120 | 120-160 | None | Add inactivity timer (visibility plus interaction events), rotate session ID after configurable timeout (default 30 min). |
| 6 | Global custom attributes | 1 day | 80-120 | 100-140 | None | New `setGlobalAttributes()` API. Custom `SpanProcessor` that injects attributes on span start. Also inject into log records and metric attributes. |
| 9 | Richer metric types | 1 day | 80-120 | 100-150 | None | Add `trackCounter()` and `trackGauge()` APIs alongside existing `trackMetric()`. Internal instrument cache for counters and gauges. |
| 14 | Rage and dead click detection | 1-2 days | 120-180 | 150-200 | None | Track click timestamps plus targets. Rage: N+ clicks on same element within M ms. Dead: click with no subsequent DOM mutation via `MutationObserver`. |
| 15 | ANR detection | 1-2 days | 100-150 | 120-180 | None | Heartbeat via `setTimeout` or `MessageChannel`. If main thread blocked longer than 5s, emit ANR event. May need Web Worker for accurate timing. |

### Medium Items (2 to 3 Days Each)

| # | Gap | Effort | Source LOC | Test LOC | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | SPA route change tracking | 2-3 days | 180-250 | 200-280 | None (History API) | Listen to `popstate`, patch `pushState` and `replaceState`. Create "view" spans per route change. Generic approach plus optional Wouter hook. |
| 7 | Smart sampling | 1-2 days | 100-150 | 150-200 | None | Custom `Sampler` composing `TraceIdRatioBasedSampler` with always-on for errors. Requires a `SpanProcessor` that upgrades sampling decision on error (brief buffering). |
| 10 | Resource and asset monitoring | 2-3 days | 200-280 | 200-250 | None | `PerformanceObserver` for `resource` entries post-load. Capture timing breakdown, size, cache status. Configurable slow-resource thresholds. |
| 16 | Consent and privacy framework | 2-3 days | 200-300 | 200-280 | None | Before-init consent gate, runtime consent changes, URL parameter scrubbing, request and response body redaction, configurable PII masking. Touches nearly every module. |
| 17 | Feature flag correlation | 1-2 days | 100-150 | 120-160 | None | Generic `setFeatureFlags()` API that attaches flags as span and log attributes. Optional adapter pattern for LaunchDarkly and Split. |
| 18 | Deep network error monitoring | 2-3 days | 200-280 | 180-250 | None | Enhance fetch and XHR instrumentation with `PerformanceResourceTiming` breakdown, response size, GraphQL operation extraction, CORS diagnostics. |

### Large Items (3 to 5 Days Each)

| # | Gap | Effort | Source LOC | Test LOC | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 11 | Error fingerprinting and source maps | 3-5 days | 300-400 | 250-350 | Source map library | Client-side: normalize stacks, generate fingerprint hash, attach `error.group`. Build-side: source map upload CLI and symbolication (bulk of work). |
| 12 | Offline buffering | 3-5 days | 350-500 | 300-400 | None (IndexedDB) | Custom `SpanExporter` wrapper detecting `navigator.onLine`, buffering to IndexedDB, flushing on reconnect. Storage quota management, TTL eviction, retry logic. |

### Extra-Large Items (4 to 8 Weeks)

| # | Gap | Effort | Source LOC | Test LOC | Dependencies | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 13 | Session replay | 4-8 weeks | 2,000-4,000 | 1,500-2,500 | `rrweb` (~50KB) | DOM mutation recording, input masking, mouse tracking, scroll and resize events, compression, chunked upload, privacy controls. Essentially a product unto itself. |

## Priority Matrix

| Priority | Gap | Impact |
| --- | --- | --- |
| High | Core Web Vitals (LCP, CLS, INP) | Cannot measure real performance |
| High | SPA route change tracking | Cannot attribute errors and performance to pages |
| High | User identity on telemetry | `setUser()` is a no-op for observability |
| High | Session timeout and rotation | Inflated session counts |
| High | Long task detection | Missing jank visibility |
| Medium | Global custom attributes | Cannot tag by env, team, or feature |
| Medium | Smart sampling (keep errors) | Lose critical error traces |
| Medium | Baggage propagation | Broken cross-service context |
| Medium | Richer metric types | Counter and gauge use cases blocked |
| Medium | Resource and asset monitoring | No CDN or asset performance visibility |
| Medium | Error fingerprinting and source maps | Noisy, ungrouped errors |
| Medium | Offline buffering | Data loss on flaky connections |
| Lower | Session replay | Major feature, large effort |
| Lower | Rage and dead click detection | UX quality signal |
| Lower | ANR detection | Niche but valuable |
| Lower | Consent and privacy framework | Required for regulated apps |
| Lower | Feature flag correlation | Nice-to-have integration |

## Rollup Summary

| Category | Items | Total Source LOC | Total Test LOC | Combined Effort |
| --- | --- | --- | --- | --- |
| Quick wins (under 1 day) | #3, #5, #8 | 75-115 | 140-200 | 1.5 days |
| Small (1-2 days) | #1, #4, #6, #9, #14, #15 | 580-860 | 660-930 | 6-10 days |
| Medium (2-3 days) | #2, #7, #10, #16, #17, #18 | 980-1,410 | 1,050-1,420 | 12-19 days |
| Large (3-5 days) | #11, #12 | 650-900 | 550-750 | 6-10 days |
| Extra-large (4-8 weeks) | #13 | 2,000-4,000 | 1,500-2,500 | 4-8 weeks |
| **Grand total** | **18 items** | **~4,300-7,300** | **~3,900-5,800** | **~7-12 weeks** (excluding session replay) |

> [!IMPORTANT]
> The SDK would roughly 4 to 6x its current size to reach commercial parity. Excluding
> session replay (essentially a standalone product), the remaining 17 items represent
> about 7 to 12 weeks of work for one developer.
