---
title: "Phase 0 / 19 — Yield on Cost from the transaction ledger (U3, SP06)"
category: source
source_type: plan
date_ingested: 2026-10-09
original_path: LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/plan-phase00YieldOnCost.prompt.md
tags: [phase0, release2, yield-on-cost, income, dashboard, fifo, wac]
related:
  - decisions/yield-on-cost-definition
  - features/F-100
  - decisions/fifo-v4-income-eligibility-d1
  - decisions/financial-math-single-average-cost
---

# Source: Phase 0 / 19 — Yield on Cost

## Summary

One plan (~1 050 lines) and a README, archived on 2026-10-09. It defined Yield on Cost from the user's transaction
ledger, per `(asset, broker)`, and shipped it as a column of the Dashboard positions (`74afcebce`, 2026-09-11,
merged as `d7d40c0ec`). The plan's long middle is the definition's case analysis — partial sales, same-day trades,
transfers, splits, missing FX — and its rejected alternatives; the code at `586a4f0ea` follows it, with one later
change: since #32 the denominator comes from the single average-cost function.

## Key takeaways

- The formula, the D-1 eligibility reused from FIFO, the status contract and the five rejected alternatives:
  [[decisions/yield-on-cost-definition]].
- A metric that cannot be computed says why (`unavailable` + reason) instead of showing a partial number.
- Reuse over re-implementation: the D-1 eligible quantity is the FIFO engine's (`eligible_income_quantity`), the
  third copy was refused.

## Residuals (backlog 38)

I-08 — the YOC theory page exists only in English.

## Wiki pages updated

- [[decisions/yield-on-cost-definition]], [[features/F-100]] — new.
- [[features/registry]] — F-100 added.

## Source files

| Role | Path |
|------|------|
| README | `LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/README.md` |
| Plan | `LibreFolio_developer_journal/Release_2/phases/19_yieldOnCost/plan-phase00YieldOnCost.prompt.md` |
| Calculation | `backend/app/services/yield_on_cost.py` |
| Cell | `frontend/src/lib/components/dashboard/YieldOnCostCell.svelte` |
| Theory page | `mkdocs_src/docs/financial-theory/technical-analysis/performance-metrics/portfolio-engine/yield-on-cost.en.md` |
