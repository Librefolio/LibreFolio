---
title: "Gross vs Net Dual Reporting"
category: "concept"
tags: ["backend", "frontend", "fifo", "net-metrics"]
related: ["decisions/fifo-v4-gross-net-status-model", "entities/fifo-lot-engine", "concepts/deterministic-cost-matching-ladder"]
---

# Concept: Gross vs Net Dual Reporting

## Definition
Gross and net performance figures **coexist** as two permanently-visible accumulators, not as a single value
behind a "gross/net" mode toggle. Net is always computed the same feed-forward way:

```
net = gross - allocated_fees - allocated_taxes
```

Gross accumulators (`original_cost`, `sale_proceeds`, `gross_income`, `open_value`, `TotalPnL`, `TotalReturn`,
…) are **never** mutated by fee/tax allocation — `allocated_fees`/`allocated_taxes` are separate, additive
accumulators, and every net figure is derived from its own gross counterpart exactly once.

## Where It Applies
- Per-lot summary metrics in [[entities/fifo-lot-engine]]: `NetTotalPnL_i = TotalPnL_i - Fees_i - Taxes_i`,
  `NetTotalReturn_i = NetTotalPnL_i / OpeningValue_i`.
- Per-lot **history** series: a deliberately different, *capital-only* net figure,
  `pnl_i - Fees_i - Taxes_i`, which **excludes** income (unlike the income-inclusive summary net). Each net
  line mirrors its own gross counterpart minus costs — the asymmetry between summary and history net is
  intentional, not a bug.
- Frontend: `UnifiedLotsTable.svelte` net columns, `LotCustodyModal.svelte` gross→fees→taxes→net breakdown.

## Why this shape
Folding fees/taxes directly into `original_cost` or another gross accumulator would make gross values stop
being bit-for-bit comparable to pre-v4 behavior, and would require every existing consumer of gross fields to
be re-verified. Keeping gross untouched and deriving net additively means zero behavior change for gross-only
consumers, and a net figure that's always trivially auditable (gross minus a small number of new, transparent
accumulators) instead of buried inside a recomputed cost basis.

## Related decision
See [[decisions/fifo-v4-gross-net-status-model]] for the full decision record, including the associated
`analysis_status`/`LotNetMetricsStatus` reliability model and a real UI bug this surfaced
([[problems/datatable-net-columns-hidden-override-model]]).

## Source files
| File |
|------|
| `backend/app/services/fifo_lot_engine.py` |
| `backend/app/schemas/portfolio.py` |
| `frontend/src/lib/components/brokers/lots/UnifiedLotsTable.svelte` |
| `frontend/src/lib/components/brokers/lots/LotCustodyModal.svelte` |
| `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.en.md` §"Costs & Net Metrics" → "Gross vs net" |
