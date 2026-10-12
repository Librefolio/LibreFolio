---
title: "AI Export said «not reconciled» for a 1e-24 residual, printed as 0 beside it"
category: problem
status: resolved
date: 2026-10-12
tags: [ai-export, backend, decimal, rounding, reconciliation, contracts, versioning, native-cash]
related:
  - decisions/ai-export-version-bump-once-per-release
  - entities/native-cash
  - decisions/native-cash-daily-revaluation
  - entities/ai-export-snapshot-service
  - sources/phase00-financial-math-home-2026-10
---

# Problem: «not reconciled» on a rounding residual

## Symptom

The `portfolio.reconciliation` and `broker.reconciliation` sections of an AI Export prompt could state
`reconciled: false` next to `residual: 0`. A reader — the AI the prompt is for — saw a contradiction. Found by lot 41
step F-4 while comparing 33 snapshots of the mock database before and after F: 5 of 33 had `reconciled` false, with a
largest residual of 1e-24, both before and after F — F only changed which five (backlog C-53).

## Root Cause

- Both builders computed `reconciled = residual_amount == Decimal("0")`, on a residual that is not quantized.
- The residual is period P&L minus its components (unrealized change, realized, income, costs and taxes, other). The
  service computes `period_other_result` as the closing term of that same decomposition, so the residual is zero by
  construction; when it is not, what is left is the rounding of `Decimal`'s 28 digits.
- The renderer prints a monetary residual smaller than the currency's minor unit as `0`
  (`monetary_residuals_zeroed`), so the noise was invisible in the very line that contradicted the flag.

## Solution

Commit `876d2b430` (2026-10-12, workstream T, train 47), approved by the developer for release 1.2:

- `reconciled = abs(residual_amount) < CONVERSION_DUST` in both builders, `CONVERSION_DUST` (1e-9) imported from
  `financial_math/native_cash.py` ([[entities/native-cash]]) — the same threshold that hides conversion dust in the
  «FX on cash» row; `None` when a term is missing, as before;
- `residual` itself unchanged: still the exact difference;
- both components to v2, in the spec, in the catalogue placeholder and in `COMPACT_COMPONENT_VERSIONS` `{1, 2}` —
  one step over `v1.1.0` ([[decisions/ai-export-version-bump-once-per-release]]);
- one paragraph in «Snapshot Data Tables» of `ai_export_composition.md`.

Tests written red first: 10 of 22 backend cases failed for the expected reason (dust and a closing case with a rate of
1.09 gave `False`; the versions read 1), the control cases stayed green (exact zero, 899, `None`, ±`CONVERSION_DUST`
against a forgotten `<=` or `abs`, −99); on the frontend, 4 of 403 failed because v2 fell to YAML. Injecting the dust
into the canonical JSON reproduced the prompt line before the fix (`|reconciled|false|` beside `|residual.amount|0|`)
and showed it fixed after.

## Prevention

- Compare a computed `Decimal` with a tolerance, never with `== 0`, when it comes out of a chain of conversions.
- Print a flag and the figure it judges with the same precision, or say why they differ.

## Impact

Wrong flag only; no figure changed. Still possible after the fix, and unlikely because the summary closes the
decomposition by construction (backlog T-B9): a real residual between `CONVERSION_DUST` and the currency's minor unit
would print `0` next to `reconciled: false`.

## Source files

| Role | Path |
|------|------|
| Portfolio reconciliation | `backend/app/services/ai_export/components/portfolio_financial.py` |
| Broker reconciliation | `backend/app/services/ai_export/components/broker_financial.py` |
| Versions (v2) | `backend/app/services/ai_export/components/catalog.py` |
| Compact map `{1, 2}` | `frontend/src/lib/features/ai-export/templates/snapshotDataRenderer.ts` |
| `CONVERSION_DUST` | `backend/app/services/financial_math/native_cash.py` |
| Doc paragraph | `mkdocs_src/docs/developer/architecture/patterns/ai_export_composition.md` |
| Analysis and implementation notes | `LibreFolio_developer_journal/Release_2/Phase_0/43_financialMathHome/plan-phase00FinancialMathHome.prompt.md` |
