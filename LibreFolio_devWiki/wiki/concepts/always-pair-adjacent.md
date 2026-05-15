---
title: "Pair-Adjacent Rendering + GoTo — linked TX pairs in TransactionsTable"
category: concept
tags: [frontend, transactions, datatable, rendering, pairs, transfer, fx-conversion, goto, pulse]
related:
  - features/F-047
  - features/F-046
  - decisions/tx-link-uuid-semantics
  - sources/phase07-part4-transactions-ui
---

# Concept: Pair-Adjacent Rendering + GoTo

## Overview

Linked transaction pairs (TRANSFER, FX_CONVERSION, soft-linked DEPOSIT↔WITHDRAWAL) arrive from the backend **already fetched together**. The frontend has two complementary mechanisms to keep them navigable:

1. **Pair-adjacent layout** (no filters/sort): the pair is placed visually adjacent — giver above, receiver below — so both are visible at a glance with no navigation needed.
2. **🔗 GoTo button** (always available): clicking the chain icon navigates to the partner row regardless of distance, changing page and scrolling as needed, then pulses the target row.

Both mechanisms coexist. The GoTo button is always present; it is *especially* important when filters or sort separate the pair.

## Pair-Adjacent Layout

**Active only when: no column filters AND no sort are applied.**

When active (`isGrouped = true`), a reordering algorithm rebuilds `displayRows[]`:

```
mainRows (default sort: date desc)
  → iterate; for each row:
      if row.related_transaction_id != null and partner NOT yet rendered:
          push self
          push partner immediately after (from mainRows if present, else as ghost row)
          mark partner as visited
      if row is already-rendered partner → skip (deduplication)
  → result: displayRows[]
```

Within-pair ordering:
- **TRANSFER**: `quantity < 0` = giver (📤 above), `quantity > 0` = receiver (📥 below)
- **FX_CONVERSION**: `cash.amount < 0` = giver, `cash.amount > 0` = receiver

### Paginator: Pair-Never-Split

In grouped mode the paginator ensures a linked pair is **never split across pages**. If a pair would straddle a boundary, the first member is moved to the next page. Target page size 50, effective range 49–51 is acceptable.

### Ghost Rows

When one partner is absent from the server response (access-controlled or filtered by server), it appears as a **ghost row** with `opacity: 0.7`. Ghost rows are still selectable and usable in bulk actions. The interactive ✕/+ chip originally planned was deferred and not implemented in Phase 7 Part 4.

## Pair-Adjacent Disabled (filters or sort active)

When the user applies any column filter or sort → `isGrouped = false`:
- The reordering algorithm is **not applied**; rows appear in DataTable's natural filtered/sorted order
- The two rows of a pair may end up on different pages or far apart
- Ghost rows become ordinary independent rows
- DataTable handles pagination internally (`enablePagination={true}`)
- External `DataTablePagination` shown only in grouped mode

**The 🔗 GoTo button is the primary navigation tool in this mode.**

## 🔗 GoTo Button — Pulse Animation

Clicking the 🔗 icon on any linked row navigates to its partner:

1. If the partner is on a different page → change page first
2. Scroll the partner into view (`scrollIntoView({behavior: 'smooth', block: 'center'})`)
3. Pulse the partner row via DOM-direct manipulation:

```js
el.classList.remove('tx-row-highlight');
void el.offsetWidth;    // force reflow to restart CSS animation
el.classList.add('tx-row-highlight');
// auto-clear after 1.6s
```

CSS target: `tr.tx-row-highlight > td` (animation on `<td>`, not `<tr>` — `box-shadow` on `<tr>` is unreliable cross-browser).

**Implementation note**: DOM-direct manipulation (not Svelte reactive state) because Svelte 5 does not re-trigger CSS animations on function-reference-equal closures. Click uses **capture phase** (`addEventListener('click', h, true)`) to intercept before DataTable's row-selection handler.

## Source files

| Role | Path |
|------|------|
| TransactionsTable (algorithm) | `frontend/src/lib/components/transactions/TransactionsTable.svelte` |
| +page.svelte (pulse handler) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Plan where designed | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/plan-phase07-transaction-Part4.prompt.md` (Step 5) |
