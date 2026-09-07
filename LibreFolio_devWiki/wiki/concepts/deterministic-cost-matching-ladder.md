---
title: "Deterministic Cost-Matching Ladder"
category: "concept"
tags: ["backend", "fifo", "fee", "tax", "cost-basis"]
related: ["decisions/fifo-v4-cost-allocation-ladder", "entities/fifo-lot-engine", "concepts/asset-orphan-vs-portfolio-level-cost", "concepts/d1-income-eligibility-window"]
---

# Concept: Deterministic Cost-Matching Ladder

## Definition
An ordered list of candidate targets that an asset-linked cost pool (grouped by `asset, broker, date, type`)
is matched against, stopping at the **first non-empty** target. Two distinct ladders exist, because `FEE` and
`TAX` have different real-world causal structure:

```
FEE:  same-day trades → previous-day trades → open holdings (fallback) → asset orphan
TAX:  same-day income → same-day trades → previous-day income → previous-day trades → open holdings (fallback) → asset orphan
```

`TAX` is income-first because taxation is frequently tied to an income event (e.g. withholding tax on a
dividend); `FEE` is trade-centric and never targets an income event.

## Where It Applies
- Any asset-linked `FEE`/`TAX` row inside [[entities/fifo-lot-engine]].
- Only for rows with a non-null `asset_id` — assetless rows never enter this ladder at all, see
  [[concepts/asset-orphan-vs-portfolio-level-cost]].
- The "same-day/previous-day income" steps of the TAX ladder reuse the D-1/broker eligibility test from
  [[concepts/d1-income-eligibility-window]].

## Matching sub-rules
- **Never adjacent-day D+1** — only the previous day is a valid fallback window; this mirrors the
  income-eligibility rule and was chosen for the same reason (determinism over completeness).
- **Same-day mixed BUY+SELL pool**: when a same-day trade pool contains both directions with no explicit
  causal link to the cost, the pool is split by **value-weight** (`|TransactionAmount|`, qbq-safe), not
  arbitrarily assigned to one side — an explicit rule (`SAME_DAY_MIXED_TRADES`), not treated as an error.
- **Crossing trades** (one trade that both closes an existing lot and opens a new one in the opposite
  direction): the trade's cost is split proportionally by `q_close/q_total` and `q_open/q_total` — the close
  share allocates to the closures it paid for, the open share to the newly opened lot. `LotClosure` records
  stay immutable either way.
- **Fallback to open holdings**: if no same-day or previous-day trade exists, the cost can still land on
  currently open lots (weighted the same way) before finally becoming orphan.

## Examples
- A same-day FEE with only a BUY trade that day: 100% to the lot(s) that BUY opened.
- A same-day FEE with both a BUY and a SELL that day: split between the BUY's opened lot and the SELL's
  consumed lots, by each trade's absolute value.
- A TAX row with a matching same-day dividend: allocated exactly like that dividend's D-1/broker-eligible lots,
  before ever considering trades.
- A FEE booked after the position is already fully closed, with nothing on the previous day either: becomes
  **asset-level orphan cost** — flagged, never dropped, never forced onto an unrelated lot.

## Source files
| File |
|------|
| `backend/app/services/fifo_lot_engine.py` |
| `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §13-16 |
| `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Costs & Net Metrics" |
