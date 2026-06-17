---
title: "FIFO Lot Tracking"
category: "concept"
tags: ["finance", "fifo", "holdings", "tax"]
related: ["phase09-dashboard-batch"]
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

## Source files
| File |
|------|
| `LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_broker_holdings.md` |
