---
title: "Backend plugin architecture for technical signals"
category: decision
status: resolved
date: 2026-07-23
tags: [backend, frontend, signals, plugins, bulk-api, architecture]
related: [backend-only-calculations, provider-registry-decision, signal-label-unification]
---

# Decision: Backend plugin architecture for technical signals

## Context

Technical indicators were calculated in TypeScript inside chart classes and recalculated separately by AI Export. This violated the backend-only calculation rule, prevented reuse by future AI/MCP consumers, and made every new indicator a frontend implementation task.

## Options Considered

1. **Keep the TypeScript engine** — lowest migration cost, but preserves duplicated math and blocks non-UI consumers.
2. **Expose a generic raw-array compute endpoint** — reusable, but creates an unbounded public calculation API detached from Asset/FX data policy.
3. **Backend plugin service enriched through existing Asset/FX bulk APIs** — central calculation contract, domain adapters remain responsible for loading/conversion, and no new raw endpoint.

## Decision

LibreFolio uses one domain-neutral `SignalService` with auto-discovered, pure Python `SignalPlugin` classes. Plugins accept canonical price/event arrays, own params/warm-up/library calls, and return flat canonical line/bar/band series plus annotations. Asset and FX remain thin adapters: each view sends all applicable instances in one bulk POST; cached Asset prices use `include_price=false`; FX daily rates stay separate from grouped signal results.

The frontend keeps `SignalConfig` and all local style/view behavior. Backend catalog JSON Schema drives technical controls and compatibility. Comparison signals, synthetic benchmarks, and Measure remain frontend-local. No generic public raw-array endpoint and no persisted computed results are introduced.

## Consequences

- New technical indicators are normally one Python plugin plus i18n/docs metadata.
- Asset exposes 17 plugins; FX exposes the 9 close-only compatible plugins.
- Status is explicit per instance (`ok`, `partial`, `unavailable`, `failed`); one failure never removes prices or sibling results.
- One bulk request is mandatory for list views; no request-per-card/pair/signal.
- The old TypeScript technical classes remain only as rollback until Gate E visual review, then are removed.

## Source files

| Role | Path |
|------|------|
| Canonical contracts | `backend/app/schemas/signals.py` |
| Signal orchestration | `backend/app/services/signal_service.py` |
| Plugin registry | `backend/app/services/provider_registry.py` |
| Production plugins | `backend/app/services/signal_plugins/` |
| Asset adapter | `backend/app/services/asset_source.py` |
| FX adapter | `backend/app/api/v1/fx.py` |
| Frontend catalog/renderer | `frontend/src/lib/charts/signals/catalogMapper.ts`, `backendRenderer.ts` |
| Bulk request/result mapping | `frontend/src/lib/charts/signals/requestBuilder.ts`, `resultMapper.ts` |
| Execution plan | `LibreFolio_developer_journal/Release_2/phases/01_signalMigration/plan-phase00SignalsBackendMigrationImplementation.prompt.md` |
