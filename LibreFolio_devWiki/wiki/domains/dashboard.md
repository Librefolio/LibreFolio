---
title: "Domain: DASHBOARD"
category: domain
features: [F-054, F-055]
status: planned
mkdocs: null
---

# Domain: DASHBOARD

> ⚠️ This domain is under active development (Phase 7). Content reflects design intent, not final implementation.

> The portfolio at a glance — KPI cards, allocation charts, and recent activity for a user's weighted view across all their brokers.

## What it does

The Dashboard is the first page a user sees after logging in and the natural home for the question "how is my portfolio doing today?" It aggregates data across all brokers the user has access to — weighted by each broker's `share_percentage` in `BrokerUserAccess` — to produce a unified portfolio view in the user's preferred currency.

The KPI section shows Net Asset Value (the current market value of all holdings), Profit & Loss (unrealized gain from cost basis), and Return on Investment (percentage gain, duration-weighted). These numbers are expensive to compute: they require FIFO cost basis (F-056), cross-currency conversion (F-057), and ROI calculations (F-058) all running together. The backend endpoint `GET /api/v1/portfolio/overview` will aggregate these per broker and apply the ownership share weights.

The portfolio charts section (F-055) visualizes allocation (by asset type, sector, and geography as pie/donut charts) and portfolio evolution over time (NAV history as a line chart). A recent transactions widget rounds out the page with the last 10 transactions across all accessible brokers.

The share percentage weighting model deserves special mention: a user with EDITOR access and `share_percentage=0` has no ownership — they can enter transactions but the broker's NAV does not count toward their net worth. An OWNER with `share_percentage=100` owns the full broker value. A household might have two users each with `share_percentage=50`. The sum of percentages is not enforced to be 100% — the system warns if it exceeds 100% but allows it (useful for fractional/joint ownership scenarios).

## Feature cluster

| Code | Feature | Layer | Role in domain | Status |
|------|---------|-------|----------------|--------|
| [[F-054]] | Dashboard KPI & Overview | fullstack | core — NAV, PnL, ROI cards + recent transactions widget | planned |
| [[F-055]] | Portfolio Charts (allocation, evolution) | frontend | display — allocation pie/donut + NAV evolution line chart | planned |

## Architecture at a glance

```mermaid
graph TD
    DashPage[/dashboard +page.svelte<br/>placeholder today] -->|GET /portfolio/overview| OverviewAPI[Portfolio Overview API<br/>planned: GET /api/v1/portfolio/overview]
    OverviewAPI -->|per broker| TxSvc[Transaction service]
    TxSvc -->|FIFO lots| FIFO[F-056 FIFO at Runtime]
    TxSvc -->|prices| PriceDB[(PriceHistory)]
    FIFO --> CostBasis[Cost basis per lot]
    CostBasis --> UnrealizedPnL[Unrealized PnL]
    PriceDB --> MarketValue[Current market value NAV]
    MarketValue --> FXConv[F-057 Currency Conversion<br/>triangulation to base currency]
    FXConv --> BrokerNAV[Per-broker NAV]
    BrokerNAV -->|× share_percentage| UserNAV[User-weighted NAV]
    UserNAV --> KPICARD[KPICard.svelte<br/>NAV / PnL / ROI]
    TxDB[(Transaction table)] --> RecentTx[RecentTransactions.svelte<br/>last 10 tx]
    PriceDB --> Evolution[Portfolio evolution chart<br/>F-055]
    AssetAlloc[Asset type/sector/geo breakdown] --> Alloc[Allocation charts<br/>F-055]
    ROI[F-058 ROI Calculations] --> KPICARD
```

## Key decisions that shaped this domain

- **share_percentage weighting, never averaging percentages** — NAV is summed (broker_1_NAV × share_1% + broker_2_NAV × share_2%), not averaged. Averaging percentages when brokers have different sizes would produce meaningless numbers.
- **All calculations in backend** (see [[concepts/backend-only-calculations]]) — the frontend receives pre-computed KPI values; it never performs financial calculations. This keeps the frontend as a presentation layer and ensures consistent results across devices.
- **Phase 9 target** — this domain deliberately waits for Phase 7 (transactions, BRIM import) and Phase 8 (FIFO engine integration, ROI calculations) to complete. Building the dashboard shell before the data it displays exists would create maintenance burden.

## Known problems / limitations

No open problems — this domain is not yet implemented. The current `/dashboard` route is a confirmed placeholder.

## What comes next

This entire domain is Phase 9. The implementation order:
1. `GET /api/v1/portfolio/overview` backend endpoint with FIFO + FX conversion + share weighting
2. F-058 ROI Calculations (depends on F-056 FIFO, Phase 8)
3. F-054 Dashboard KPI page — `KPICard.svelte`, `RecentTransactions.svelte`, `QuickActions.svelte`
4. F-055 Portfolio Charts — allocation pie charts, NAV evolution line chart

Later ideas:
- [[F-085]] QuarkAI Assistant — AI-powered portfolio commentary and question-answering (long-term idea).
- [[F-084]] Transaction Gain Chart — per-asset realized gain visualization.

## Source files

| Role | Path |
|------|------|
| Dashboard page (placeholder) | `frontend/src/routes/(app)/dashboard/+page.svelte` |
| Transaction service (aggregation base) | `backend/app/services/transaction_service.py` |
| FX conversion service | `backend/app/services/fx.py` |
| DB model (BrokerUserAccess.share_percentage) | `backend/app/db/models.py` |
