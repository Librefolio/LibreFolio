---
title: "Phase 09 Milestone 3 — Broker UI v2 Redesign, Archival (2026-07-15)"
category: source
source_type: plan
date_ingested: 2026-07-15
original_path: LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/
tags: [phase09, archive, broker, dashboard, chart-resolution, semantic-zoom, discovery, sharing, fifo-ui]
related:
  - domains/brokers
  - domains/dashboard
  - entities/portfolio-engine
  - entities/time-series-aggregation
  - concepts/chart-resolution-semantic-zoom
  - concepts/portfolio-report-unified
  - concepts/fifo-lot-tracking
  - decisions/broker-list-visibility-non-members
  - decisions/broker-card-aggregation-no-n-plus-one
  - problems/portfolio-asset-history-regression-restored
  - sources/phase09-m1-m2-archive-2026-07
---

# Source: Phase 09 Milestone 3 — Broker UI v2 Redesign

## Summary

Milestone 3 of Phase 9 redesigns the Broker pages (global list + per-broker detail with 3 tabs: Panoramica,
Posizioni, Transazioni) to reuse the widgets and the unified `/portfolio/report` engine entrypoint built in
Milestones 1/2, rather than the pre-Portfolio-Engine designs written earlier. It was archived via `git mv`
from `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/` into
`LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/` on 2026-07-15, joining the
already-archived M1/M2. All 3 fasi (Overview/Discovery/Sharing, Holdings + FIFO lots panel, Transactions)
show ✅ design · ✅ implementation plan · ✅ implemented. A separate cross-cutting workstream —
**dynamic chart resolution / semantic zoom** (`chart_resolution/`, 7 implementation plans + 1 feasibility
study) — was developed in parallel by a fleet of agents and is also ✅ implemented, verified against sources.

## Key Takeaways

### Broker List & Detail Shell (Fase 1 — ✅ implemented 2026-07-06)

- **`GET /portfolio/asset-history` regression restored** — see [[problems/portfolio-asset-history-regression-restored]].
- **Broker Discovery**: `GET /brokers?include_inaccessible=true` (opt-in, default `False`) surfaces brokers the
  user doesn't own/have access to, exposing only `{id, name, icon_url}` — no "request access" flow in this
  phase. See [[decisions/broker-list-visibility-non-members]].
- **Share icon everywhere, read-only for non-owners**: every broker card (own or others') gets a Condividi
  icon opening `BrokerSharingModal` — editable for OWNER (unchanged), **read-only** for EDITOR/VIEWER and for
  non-members (both previously impossible: the button was OWNER-only and `GET /brokers/{id}/access` 404'd for
  non-members). See [[decisions/broker-list-visibility-non-members]].
- **Per-card quota%/NAV/Gain/cash-multivaluta without N+1 calls**: `cash_balances: List[Currency]` added
  natively to `BrokerBreakdown` (was missing multi-currency detail); `GET /brokers` gained
  `user_share_percentage` (always included, no extra cost). See [[decisions/broker-card-aggregation-no-n-plus-one]].
- Currency selector pattern (global list + per-broker overview): independent `CurrencySearchSelect` instances,
  pre-populated from `globalSettings.default_currency`, used as `target_currency` for NAV/Gain — reused
  Dashboard pattern, no new concept.
- All other widgets needed (KPI cards, GrowthChart, AllocationPanel, PositionsPanel, RecentTransactionsPanel,
  `GET /portfolio/lots`, `<TransactionsTable>`, BRIM import history/wizard) already existed and were only
  reused/reparametrized to the single-broker scope — no new backend work.

### Holdings Tab + FIFO Lots Panel (Fase 2 — ✅ implemented 2026-07-10, evolved multi-broker 2026-07-11)

Reuses `PositionsPanel` (see [[concepts/holdings-performance-panel]]) plus a new **inline multi-broker FIFO
lots panel**: bubble timeline of open/closed lots and per-broker + combined WAC/price. This is a **UI/display
design over the existing FIFO engine** (`GET /portfolio/lots`, `FIFOLotsResponse` — see
[[concepts/fifo-lot-tracking]]); it does not change FIFO engine internals. (Note: a separate, still-open
technical investigation into FIFO/WAC/transfer engine internals — `RoadmapV4_UI/fifo-engine/` — is unrelated
to this UI work and was explicitly excluded from this ingest pass.)

### Transactions Tab (Fase 3 — ✅ implemented, closed 2026-07-08)

Reuses `<TransactionsTable>` plus the broker's imported-file history — recap in-doc, no separate
`impl_plan_*.md` was needed.

### Dynamic Chart Resolution / Semantic Zoom (cross-cutting, ✅ implemented)

New shared architecture for resolution-aware charts (daily→weekly→monthly bucketing as the user zooms). See
[[concepts/chart-resolution-semantic-zoom]] and [[entities/time-series-aggregation]] for the foundational
utility. Applies to `PriceChartFull`/`CandlestickChart`, `GrowthChart`, `AllocationHistoryChart`, the 9 signal
overlay types, a shared `ResolutionBadge` + i18n keys, and the **static** compact-card variant
(`PriceChartCompact`/`LineChart` on `/assets` and `/fx` cards — no `dataZoom`, no hysteresis/badge).

## Wiki Pages Created / Updated

**Created**:
- [[sources/phase09-m3-broker-redesign-2026-07]] — this page
- [[concepts/chart-resolution-semantic-zoom]] — semantic-zoom bucketing architecture
- [[entities/time-series-aggregation]] — `timeSeriesAggregation.ts` foundational utility
- [[decisions/broker-list-visibility-non-members]] — discovery opt-in + read-only sharing for non-members
- [[decisions/broker-card-aggregation-no-n-plus-one]] — per-card quota/NAV/cash without N+1 calls
- [[problems/portfolio-asset-history-regression-restored]] — regression found + restored

**Updated**:
- [[domains/brokers]] — Broker List/Detail v2 redesign summary added
- [[domains/dashboard]] — "What comes next" M3 note resolved (was "in progress, not archived")
- [[entities/portfolio-engine]] — History row for the M3 archiving milestone

## Source files

| Role | Path |
|------|------|
| Archived M3 index | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/README.md` |
| Fase 1 design + impl | `.../Milestone_3/plan_ui_broker_overview.md`, `.../impl_plan_broker_overview.md` |
| Fase 2 design + impl | `.../Milestone_3/plan_ui_broker_holdings.md`, `.../impl_plan_broker_holdings.md` |
| Fase 3 design | `.../Milestone_3/plan_ui_broker_transactions.md` |
| Chart resolution study + 7 impl plans | `.../Milestone_3/chart_resolution/` |
| Responsive toolbar guide | `.../Milestone_3/GUIDA-TOOLBAR-RESPONSIVE-v2.md` |
| Broker schema (cash_balances) | `backend/app/schemas/portfolio.py` |
| Broker service (discovery) | `backend/app/services/broker_service.py` |
| Broker API | `backend/app/api/v1/brokers.py` |
| Broker sharing/discovery components | `frontend/src/lib/components/brokers/BrokerSharingModal.svelte`, `BrokerSharingPanel.svelte`, `BrokerDiscoveryCard.svelte` |
