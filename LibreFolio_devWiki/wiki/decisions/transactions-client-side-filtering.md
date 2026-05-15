---
title: "Transactions Client-Side Filtering — W28 decision"
category: decision
tags: [transactions, frontend, datatable, filtering, performance, ux]
status: active
date: 2026-04-28
related:
  - features/F-047
  - sources/phase07-part4-round1
---

# Decision: Transactions Client-Side Filtering

## Status: Active

## Context

Phase 7 Part 4 original plan had server-side filter parameters on `GET /transactions` (broker_id, asset_id, types, date ranges, tags). The `/transactions` page was initially loading with server-side pagination (limit/offset).

During Round 1 walkthrough, issue W28 was raised:

> "Adding filter params to a server that already has 100+ TX and returns in <100ms adds API complexity, breaks always-pair-adjacent rendering (paired rows could be on different filter pages), and makes client-side 'ghost row' logic impossible."

## Decision

**All filtering on `/transactions` is 100% client-side.** `GET /transactions` loads ALL transactions for the user without filter parameters. The DataTable handles filtering, sorting, and pagination in-browser via its existing column filter system.

An explicit **Refresh** button (`↺`) was added to the toolbar to allow the user to trigger a reload when they know data has changed (new import, external edit).

## Consequences

| ✅ Pros | ⚠️ Cons |
|---------|---------|
| Enables always-pair-adjacent rendering | Full list loaded on first visit |
| Ghost row logic feasible | Not practical for >10,000 TX |
| No API filter endpoint complexity | Refresh is manual |
| Instant filter response | |

## Scope

The decision assumes LibreFolio is a **personal** portfolio tracker with a single-owner dataset. Datasets >10,000 transactions are considered edge cases for v1. If performance becomes an issue, a virtualized DataTable or server pagination with pair-chunking would be the migration path.

## What Changed vs Original Plan

Original plan had:
```
GET /transactions?broker_id=X&asset_id=Y&types=TRANSFER,DEPOSIT&date_from=...&date_to=...
```

Actual:
```
GET /transactions      # loads ALL
                       # DataTable.svelte handles filter+sort+paginate
```

Also removed: `limit/offset` parameters from API, `FilterMap.broker_id`, `FilterMap.asset_id`, `FilterMap.date_from`, `FilterMap.date_to` from frontend state.

## Source

W28 decision documented in:
`LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round1-3/plan-phase07-transaction-Part4_Round1-tableRefactorBugfix.prompt.md`, sub-round 1.7, W28.
