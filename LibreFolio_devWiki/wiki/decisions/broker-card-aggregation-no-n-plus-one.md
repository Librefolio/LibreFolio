---
title: "Broker Card Aggregation Without N+1 Calls"
category: decision
status: resolved
date: 2026-07-06
tags: [backend, frontend, brokers, portfolio-engine, performance]
related:
  - domains/brokers
  - concepts/portfolio-report-unified
  - entities/portfolio-engine
  - sources/phase09-m3-broker-redesign-2026-07
---

# Decision: Broker Card Aggregation Without N+1 Calls

## Context

The global broker list redesign needed to show, per card, quota % + NAV/Gain + multi-currency cash — without
issuing one `/summary` (or similar) call per broker (N+1 pattern), and without losing multi-currency detail
that the existing `BrokerBreakdown` schema didn't carry natively.

## Options Considered

1. **Per-card `/summary` call** — simplest to implement, but N+1 network calls as the broker count grows;
   rejected.
2. **Extend `GET /brokers` + reuse `PortfolioReportQuery(include_breakdown=true, by_broker=true)`** (chosen)
   — one lightweight call for identity/share%, one Portfolio Engine call (already cached, see
   [[concepts/portfolio-report-unified]]) for the financial breakdown by broker.
3. **New dedicated `/portfolio/broker-cards` endpoint** — rejected as unnecessary duplication; the unified
   `/portfolio/report` breakdown already has everything needed once `cash_balances` is added.

## Decision

- `GET /brokers` gains `user_share_percentage` on every returned broker — always included, no extra query
  cost.
- `BrokerBreakdown` (in `POST /portfolio/report` responses) gains `cash_balances: List[Currency]` — the same
  field/pattern already used on `PortfolioSummary.cash_balances`, populated by projecting `broker_cash` per
  broker with no new aggregation logic (`backend/app/schemas/portfolio.py:344-366`,
  `backend/app/services/portfolio_service.py`).
- The per-broker breakdown call is kept **separate** from `GET /brokers` (which feeds lightweight selectors
  used throughout the app) and is cached client-side by `portfolioStore` like every other `/report` call —
  it uses the Portfolio Engine, `GET /brokers` does not.

## Consequences

- Global broker list renders NAV/Gain/cash-multivaluta/quota% for all cards with exactly 2 network calls
  total (`GET /brokers` + one `POST /portfolio/report` with `by_broker` breakdown), regardless of broker
  count.
- `BrokerBreakdown.cash_balances` is now available to any other consumer that reads the breakdown, not just
  the broker list.

## Links
- [[domains/brokers]]
- [[concepts/portfolio-report-unified]]
- [[decisions/broker-list-visibility-non-members]] — same redesign, companion decision on discovery/sharing
- Source: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/Milestone_3/plan_ui_broker_overview.md`, `impl_plan_broker_overview.md` (§1.2, §1.3)
