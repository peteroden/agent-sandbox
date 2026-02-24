---
description: "Research prompt for evaluating open-source frontend observability SDKs against the otel-web-sdk gap analysis"
---

# Open-Source Frontend Observability SDK Landscape Research

## Context

We maintain a custom OpenTelemetry-based frontend SDK (`@agent-sandbox/otel-web-sdk`)
built on `@opentelemetry/sdk-trace-web` and related OTel JS packages. It currently
provides: distributed tracing (fetch, XHR, document-load, user-interaction),
structured logging with trace correlation, histogram metrics, global error capture,
session ID, PII path sanitization, a Preact error boundary, W3C Trace Context
propagation, and OTLP HTTP/JSON export.

We identified 18 feature gaps compared to commercial SDKs (Datadog RUM, Dynatrace
RUM, New Relic Browser, Sentry). Before investing 7 to 12 weeks of development to
close these gaps, we need to understand what the open-source ecosystem already offers.

## Research Objective

Determine whether existing open-source packages or frameworks already provide the
capabilities we plan to build, and whether adopting or extending them would be more
effective than building from scratch.

## Specific Gaps to Research

For each gap listed below, find open-source packages (npm, GitHub) that address it.
Evaluate maturity, maintenance status, compatibility with OpenTelemetry JS SDK v2,
and integration complexity.

### Performance and User Experience Monitoring

1. **Core Web Vitals collection** (LCP, CLS, INP, FCP, TTFB): Are there OTel-native
   packages that collect CWV and emit them as OTel metrics or spans? How does
   `web-vitals` (Google) integrate with OTel? Are there existing OTel instrumentations
   beyond `@opentelemetry/instrumentation-document-load`?

2. **SPA route change tracking**: Are there open-source OTel instrumentations for
   History API, React Router, or generic SPA navigation? Does any package create
   "view" or "page" spans for route transitions?

3. **Long task detection**: Beyond `@opentelemetry/instrumentation-long-task`, are
   there alternatives with richer attribution (linking long tasks to the triggering
   interaction)?

4. **Rage and dead click detection**: Are there open-source libraries that detect
   rage clicks and dead clicks? Can they emit events compatible with OTel?

5. **ANR (Application Not Responding) detection**: Are there browser-side ANR
   detection libraries? How does Sentry's ANR detection work, and is it extractable?

### Data Quality and Context

6. **Smart sampling (error-aware)**: Are there custom OTel samplers for the browser
   that always keep error traces? Any open-source implementations of browser-side
   tail sampling or sampling decision upgrade?

7. **Baggage propagation helpers**: Beyond the raw `W3CBaggagePropagator`, are there
   higher-level libraries that manage baggage for user context, feature flags, or
   A/B test buckets?

8. **Session management with timeout rotation**: Are there open-source session ID
   managers that handle inactivity-based rotation, compatible with OTel resource
   attributes?

9. **User identity enrichment**: Are there OTel SpanProcessors or plugins that
   automatically inject user attributes into all telemetry signals?

10. **Global attribute injection**: Are there reusable OTel SpanProcessors that
    add custom global attributes to every span, log, and metric?

### Error Management

11. **Error fingerprinting and grouping**: Are there open-source JS libraries for
    normalizing stack traces, generating error fingerprints, and deduplicating errors
    client-side? How do Sentry's open-source SDKs handle this?

12. **Source map integration**: Are there open-source tools for uploading source maps
    to an OTel-compatible backend and symbolication? How do open-source backends
    (SigNoz, Grafana, Uptrace) handle browser source maps?

### Reliability and Privacy

13. **Offline buffering with IndexedDB**: Are there OTel exporter wrappers that
    buffer telemetry to IndexedDB when offline and flush on reconnect? Any
    general-purpose telemetry queue libraries?

14. **Consent and privacy framework**: Are there open-source consent management
    libraries designed for telemetry SDKs (not just cookie banners)? How do
    open-source RUM tools handle GDPR consent gating?

### Extended Capabilities

15. **Session replay**: What open-source session replay libraries exist (rrweb,
    OpenReplay, highlight.io)? How mature are they? Can they integrate with OTel
    trace context to link replays to traces?

16. **Feature flag correlation**: Are there open-source integrations between feature
    flag SDKs (OpenFeature, Flagsmith) and OTel that attach flag evaluations to spans?

17. **Resource and asset monitoring**: Beyond document-load instrumentation, are there
    OTel instrumentations that use `PerformanceObserver` for ongoing resource timing
    collection?

18. **Richer metric types**: Are there OTel web SDK wrappers that provide
    higher-level counter and gauge APIs on top of the raw `MeterProvider`?

19. **Deep network error monitoring**: Are there packages that extract detailed
    `PerformanceResourceTiming` data (DNS, TCP, TLS breakdown) and attach it to
    OTel fetch/XHR spans? Any GraphQL-aware OTel instrumentations for the browser?

## Comprehensive SDK Alternatives

Beyond individual packages, evaluate these full-stack open-source alternatives that
might replace our custom SDK entirely:

- **Grafana Faro Web SDK** (`@grafana/faro-web-sdk`): How does its feature set
  compare to our 18-gap list? What does it provide out of the box? Is it
  OTel-compatible or does it use a proprietary protocol? Can it export to
  non-Grafana backends?

- **OpenReplay**: Is the tracker SDK usable standalone? Does it support OTel export?
  What RUM features does it include beyond session replay?

- **Sentry Browser SDK** (`@sentry/browser`): Which of Sentry's features are
  available in the open-source SDK versus requiring the SaaS platform? Can Sentry's
  SDK export to OTel or be used with self-hosted backends?

- **Highlight.io**: Is the frontend SDK open-source? What RUM features does it
  provide? OTel compatibility?

- **Uptrace JS**: Does Uptrace offer a browser SDK? What features does it include?

- **SigNoz browser instrumentation**: Does SigNoz provide or recommend a specific
  browser SDK beyond vanilla OTel?

## Evaluation Criteria

For each package or alternative found, capture:

| Criterion          | What to Assess                                                           |
| ------------------ | ------------------------------------------------------------------------ |
| Feature coverage   | Which of our 18 gaps does it address?                                    |
| OTel compatibility | Does it use or integrate with `@opentelemetry/*` packages?               |
| Export flexibility | Can it send to any OTLP endpoint, or is it locked to a specific backend? |
| Maintenance health | Last release date, commit frequency, open issues, bus factor             |
| Bundle size        | Gzipped size impact for browser deployment                               |
| License            | OSI-approved? Compatible with our project (check for AGPL or similar)?   |
| Adoption signals   | npm weekly downloads, GitHub stars, known production users               |
| Integration effort | How much work to integrate with our existing SDK or replace it?          |

## Desired Output

Produce a comparison matrix with:

1. A row per open-source solution evaluated.
2. Columns for each of the 18 gaps (checkmark if addressed).
3. The evaluation criteria columns listed above.
4. A recommendation section answering:
   - Should we adopt an existing comprehensive SDK (like Grafana Faro) and contribute
     missing features upstream?
   - Should we compose individual best-of-breed packages into our existing SDK?
   - Should we build the gaps ourselves on top of vanilla OTel?
   - What is the hybrid approach: which gaps have strong OSS solutions to adopt, and
     which require custom development?
