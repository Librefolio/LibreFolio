---
title: "Portfolio Report Unified Endpoint"
category: concept
tags: [backend, api, portfolio, dashboard, unified, report, l2-cache, performance]
related:
  - entities/portfolio-engine
  - entities/portfolio-service
  - concepts/3-pool-cash-model
  - concepts/holdings-performance-panel
  - decisions/portfolio-summary-direct-wiring
  - features/F-054
  - features/F-055
---

# Concept: Portfolio Report Unified Endpoint

## Definition

`POST /portfolio/report` is the single API entry point for all dashboard data. Instead of the frontend making 3–5 separate calls (`/summary`, `/history`, `/allocation-history`, `/contribution`), it calls `/report` once and receives all data in one response. The engine runs ONCE internally, and all views are derived from the same `EngineResult`.

This is the key architectural pattern that prevents redundant engine runs and ensures all dashboard widgets are always consistent (same NAV, same scope, same time range).

## Where It Applies

- Frontend: `portfolioStore.svelte.ts` → `fetchReport()` → `POST /portfolio/report`
- Backend: `portfolio_api.py` → `PortfolioService.get_report()` → engine runs once → all sub-methods receive `_precomputed_engine_result`

## The Response Shape

```typescript
interface PortfolioReportResponse {
  summary?: PortfolioSummary;          // KPIs, holdings, allocations
  history?: PortfolioHistoryPoint[];   // Daily NAV series
  allocation_history?: AllocationHistoryResponse; // 3 dimensions
  data_quality?: DataQualityReport;   // Issues, warnings, missing prices
  positions_contribution?: PositionsContrib; // Per-asset period P&L (optional)
}
```

All sections are optional (`include_*` flags). The frontend requests all sections in one call.

## L2 Cache Key

```python
cache_key = (
    user_id, broker_ids, currency, date_from, date_to,
    include_summary, include_history, include_allocation_history,
    include_breakdown, include_positions_contribution,
    tx_fingerprint,    # changes on any tx mutation
    price_fingerprint  # changes on any price update
)
```

Cache TTL = session duration (invalidated by content fingerprint, not time).

## Frontend Cache

`portfolioStore.svelte.ts` implements a client-side L2 cache:
```
cache_key = broker_ids|dateFrom|dateTo|currency|contrib_flag
```

If the key matches a cached entry, `fetchReport()` returns immediately without hitting the API. Cache invalidated on: any transaction CRUD, manual refresh button.

## Why Not Separate Endpoints?

The previous `/summary` + `/history` separate calls caused:
1. **Race conditions**: summary and chart showed different NAV values (different engine runs, different snapshots)
2. **Double engine cost**: two engine runs per page load
3. **Code duplication**: frontend managed two loading states

`/report` solves all three.

## Confirmed as Sole Entrypoint (2026-07-06)

An earlier proposal for a standalone `/allocation-history` endpoint (in early Milestone 2 architecture drafts)
was never built — superseded by this unified endpoint. As of the Holdings/Performance panel refactor (commit
`78aaa0a3`), this was explicitly re-confirmed: *"Endpoint `/portfolio/report` confermato come entrypoint
unico — nessun nuovo endpoint creato."* No separate endpoint is planned. See
[[decisions/portfolio-summary-direct-wiring]] for the full rationale.

## Source files

| Role | Path |
|------|------|
| API endpoint | `backend/app/api/v1/portfolio_api.py` |
| Service method | `backend/app/services/portfolio_service.py` (`get_report()`) |
| Frontend store | `frontend/src/lib/stores/portfolioStore.svelte.ts` |
| Dashboard page | `frontend/src/routes/(app)/dashboard/+page.svelte` |
