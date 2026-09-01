---
title: "FIFO Lot Tracking"
category: "concept"
tags: ["finance", "fifo", "holdings", "tax"]
related: ["phase09-dashboard-batch", "entities/fifo-lot-engine", "decisions/fifo-v4-income-eligibility-d1", "decisions/fifo-v4-cost-allocation-ladder", "concepts/gross-net-dual-reporting"]
---

# FIFO Lot Tracking

## Context
In Phase 09 (Dashboard), granular tracking of open and closed asset lots is introduced via the Broker Holdings view.

## Concept
The **First-In, First-Out (FIFO)** accounting method is standard for tracking capital gains in many jurisdictions. 
- When an asset is sold, the system matches the sale against the earliest available purchase ("First-In").
- This tracking requires maintaining a ledger of all open lots (purchases not yet fully sold).
- The Broker Holdings UI presents this via a detailed "Slide-over" modal, showing open lots, closed lots, and the cost basis for each.
- FIFO logic is complementary to the WAC (Weighted Average Cost) logic used elsewhere for simple price visualization.

## Implementation Details
Requires precise matching of transaction quantities. Partial fills and splits must be handled carefully to maintain the integrity of the lot ledger.

## v4 evolution (2026-07): economic allocation, not just quantity
The original quantity/custody-only tracking described above was extended (not replaced) to also allocate the
*economic* life of a lot — dividends/interest, fees, and taxes — per lot, with gross vs net metrics. See
[[entities/fifo-lot-engine]] for the current canonical implementation, and:
- [[decisions/fifo-v4-income-eligibility-d1]] — dividend/interest eligibility (D-1, broker-scoped)
- [[decisions/fifo-v4-cost-allocation-ladder]] — deterministic FEE/TAX matching to lots
- [[concepts/gross-net-dual-reporting]] — resulting gross/net reporting model

## Source files
| File |
|------|
| `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-09-subplan/plan_ui_broker_holdings.md` |
| `backend/app/services/fifo_lot_engine.py` |
