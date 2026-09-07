---
title: "Risk G6 application contracts"
category: decision
status: accepted
date: 2026-07-29
tags: [risk, frontend, scenarios, cache, historical-replay, yaml]
related:
  - risk-quant-engine-process-boundary
  - cancellation-safe-inflight-deduplication
  - backend-only-calculations
---

# Decision: Risk G6 application contracts

## Context

G6 Information Architecture was approved by the user on 2026-07-29. Four final
ambiguities needed explicit contracts before implementation: historical-replay
proxy auditability, lazy-panel retention/cache behavior, hypothetical-shock
bucket UX, and future-proof scenario catalog tags.

## Decision

### Historical replay audit

Historical replay carries a typed, serializable audit trail. It always reports
proxy/exclusion counts, original-to-proxy mappings, excluded assets with their
reason or effective policy, the missing-history policy, and the effective
composition policy. Proxy mappings and exclusions participate in request/cache
identity. `RiskResultMetadata` owns execution choices; `DataQualityReport` keeps
source coverage and quality. The UI shows both a summary and per-asset detail.

### Lazy panels and cache

Accordion state is not data invalidation. Closing and reopening a panel with the
same canonical request identity reuses its in-flight/result/error state and does
not refetch. Date, scope, currency, analytic parameters, scenario configuration,
proxy mapping, or other relevant input changes produce a new identity. Open
panels query immediately; closed panels wait until reopened. Sync/mutations can
invalidate data even when identity is unchanged. Same-mount retention is a UI
guarantee; cross-mount `riskStore` reuse is a session-cache optimization.

### Hypothetical-shock buckets

Editors show buckets present in the selected scope by default and provide a
`Show all` toggle. `Other` stays visible for sector/geography even at zero
exposure; manually edited valid buckets remain visible. Visibility never changes
the effective configuration or calculation. Requests/metadata preserve all
configured shocks, while results audit buckets and precedence actually applied.

### YAML tags

Scenario YAML may contain optional machine-readable tags. Tags are lowercase,
unique, bounded slugs with an open vocabulary. They are inert discovery metadata:
not localized copy, not financial semantics, and not part of calculation cache
identity. G6 carries them in the typed catalog but adds no advanced search,
filtering, grouping, or tag UI.

## Consequences

- Proxy use cannot be hidden in frontend state or logs.
- Accordion interaction cannot accidentally trigger repeated financial queries.
- Geography catalogs remain usable at scale without hiding available buckets.
- Scenario files gain forward-compatible discovery metadata without a schema
  migration later.
- Portfolio/broker replay exclusions retain their weight as a zero-return
  residual; remaining assets are not renormalized.
- Execution proceeds backend-first, then one functional view at a time with a
  mandatory human visual gate.

## Source files

| Role | Path |
|------|------|
| Authoritative IA | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendInformationArchitecture.prompt.md` |
| Execution plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01Step6RiskFrontendIntegration.prompt.md` |
| Mathematical/semantic contract | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/contract-phase01RiskMetricsMathematical.md` |
| Application plan | `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/plan-phase01RiskAnalysisApplication.prompt.md` |
