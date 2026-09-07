---
title: "FIFO v4 cost allocation: deterministic FEE/TAX ladders"
category: decision
status: resolved
date: 2026-07-22
tags: [backend, fifo, fee, tax, cost-basis]
related: [fifo-v4-income-eligibility-d1, fifo-v4-engine-architecture, entities/fifo-lot-engine, concepts/deterministic-cost-matching-ladder, concepts/asset-orphan-vs-portfolio-level-cost]
---

# Decision: FIFO v4 cost allocation — deterministic FEE/TAX ladders

## Context
Asset-linked `FEE`/`TAX` rows had no per-lot attribution before v4. Two related questions had to be settled:
(a) which costs even enter the FIFO domain, and (b) for those that do, which lot(s) do they land on when the
ledger has no explicit causal link between a cost row and a specific trade or lot.

## Options Considered
- **Route all FEE/TAX through FIFO, including assetless rows** vs **only asset-linked rows enter FIFO, `asset_id
  = null` stays portfolio/broker-level** — chosen the latter: no defensible lot-level allocation exists without
  an asset anchor, and this matches the Portfolio Engine's existing assetless buckets.
- **One unified matching ladder for FEE and TAX** (as in `high-level-analysis-v2.md` §8:
  `SAME_DAY_SELL → SAME_DAY_BUY → SAME_DAY_INCOME → ADJACENT_DAY_INCOME → ...`) — rejected: TAX on income (e.g.
  withholding tax on a dividend) could get hijacked by an unrelated same-day SELL before ever considering the
  income event it actually belongs to.
- **Distinct ladders, TAX income-first — CHOSEN**:
  - `FEE`: same-day trades → previous-day trades → open holdings (fallback) → asset orphan
  - `TAX`: same-day income → same-day trades → previous-day income → previous-day trades → open holdings
    (fallback) → asset orphan
- **Adjacent-day matching on both sides (D-1 and D+1)** with tie-break rules (early drafts, `feasibility-analysis-v2.md`
  §5, `high-level-analysis-v2.md` lines ~478-483) — rejected: tie-breaks stayed ambiguous and D+1 is
  future-looking (attributing a cost to a trade that hasn't happened relative to the booking date yet).
  **Final: previous-day only, never D+1.**
- **Same-day pool containing both BUY and SELL trades**: mark as ambiguous / invent a stronger causal-matching
  heuristic / distribute proportionally by value — chosen proportional distribution: the ledger has no causal
  link to exploit, so an explicit, deterministic, documented rule (`SAME_DAY_MIXED_TRADES`, value-weighted, no
  warning) beats inventing a heuristic that would still be a guess.
- **Trade weighting basis**: `Quantity × ExecutionPrice` (qbq-ambiguous, wrong for bonds quoted per 100 nominal)
  vs **`|TransactionAmount|`** — chosen the latter: already qbq-safe and equals the real economic notional in
  code, no ×100 bond error risk.
- **Crossing trades** (one trade that both closes part of a position and opens the opposite direction in the
  same fill): mutate the closure, attach the whole cost to one side, or **split the trade's cost by
  `q_close/q_total` and `q_open/q_total`** — chosen the split: closure records stay immutable, and the cost
  split still lands on the right economic buckets (close share → the closures it paid for; open share → the
  new lot).

## Decision
Two separate, ordered, deterministic ladders (above) route each asset-linked cost pool `(asset, broker, date,
type)` to its target lot(s); assetless costs never enter this flow at all; unmatched pools become
**asset-level orphan cost**, never silently dropped and never forced onto an unrelated lot.

## Consequences
- A FEE with no candidate trade/holding on the day or the previous day becomes orphan, surfaced as
  `asset_orphan_fees`/`asset_orphan_taxes` rather than disappearing.
- Some fees that "feel" BUY-only or SELL-only may in practice be spread across both sides of a mixed same-day
  pool — the rule is explicit and auditable, not hidden.
- No qbq/bond-scaling bug risk in fee weighting, by construction.
- `LotClosure` records remain immutable even when a single trade both closes and opens lots.
- Documented in `mkdocs_src/.../fifo-lot-analysis.en.md` new "💸 Costs & Net Metrics" section, including the
  matching-order table.

## Related
- [[concepts/deterministic-cost-matching-ladder]]
- [[concepts/asset-orphan-vs-portfolio-level-cost]]
- [[decisions/fifo-v4-income-eligibility-d1]] — TAX's income-first step reuses the same D-1/broker eligibility rule
- [[entities/fifo-lot-engine]]
- [[sources/fifo-v4-fee-tax-integration]]

## Source files

| Role | Path |
|------|------|
| Final ladder design | `LibreFolio_developer_journal/RoadmapV4_UI/fifo-engine/v4-fee_tax_integration/hig-level-analysis-v5.md` §13-§16 |
| Trade-value weighting critique → fix | `.../v4-fee_tax_integration/feasibility-analysis-v4-review.md` C2/§4; `feasibility-analysis-v4.1.md` §3.1-3.3 |
| Rejected unified ladder | `.../v4-fee_tax_integration/high-level-analysis-v2.md` §8 |
| Rejected adjacent-day matching | `.../v4-fee_tax_integration/feasibility-analysis-v2.md` §5 |
| Executable plan | `.../v4-fee_tax_integration/implementation-plan-v5.md` Fase 4-5 |
| Engine implementation | `backend/app/services/fifo_lot_engine.py` |
| User-facing doc | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Costs & Net Metrics" |
