---
title: "The PAC failed with «Calculation failed» whenever a funding source was in another currency: a repeating FX residual, and cross rates that did not agree"
category: problem
status: resolved
date: 2026-10-08
updated: 2026-10-09
tags: [backend, frontend, pac-allocator, fx, exact-arithmetic, serialization, cross-rates, arbitrage, gallery, release-1.2, workstream-d]
related:
  - features/F-107
  - decisions/pac-fx-one-rate-map-direct-conversions
  - decisions/pac-rounding-against-the-plan
  - problems/pac-tool-error-instead-of-plan
  - sources/phase00-pac-implementation-2026-10
---

# Problem: a foreign funding source broke the calculation

## Symptom

Workstream M, shooting the gallery on 2026-10-08, got **Calculation failed** (`tool_error`) on every PAC scenario
where a funding source was in a currency different from the scenario's. Two different errors were behind it:
`WireNumberTooLargeError: -47/21700`, and `ValueError: spread_loss must be nonnegative`.

## Root Cause

- **A — a residual that cannot be written.** A conversion in the inverse direction of a stored pair uses `1/r`
  (for example 200/217). The ledger stored the posting's `rounding_delta` exactly, as a repeating ratio, and the
  report's `ratio_to_fixed_decimal` could not write a non-terminating number into the published result.
- **2A — rates that create money.** A pairwise rate map does not rule out a triangle: converting c → q → V could
  yield more than c → V directly. Real data mixes the latest rates of different dates and sources, and the spread
  defaults to zero, so the spread loss came out negative. The review dossier had called rate inconsistency
  «structurally impossible» after the FX redesign; it was not, for three currencies, and the dossier got a dated
  correction.

## Solution

`bffc634b0` (2026-10-09, «exact FX residual, coherent cross rates»), with the contract kept at `1.0.0`:

- **A**: `PlannerLedgerRow.rounding_delta` becomes an `ExactNumber` — a finite decimal or an exact ratio
  (`ratio_to_exact_number()`); the schema fingerprint moved (`4f061103…` → `a999932e…`). The page shows such a
  number with «≈» and an adaptive precision of two significant digits (`exactMoneyDisplay`), never «≈ −0.00».
- **2A**: `validate_fx_coherence()` in the normalizer refuses a buy conversion when
  `r(c,q)·(1−s)·r(q,V) > r(c,V)`, with the new issue `allocation.fx_rate_inconsistent` (an `invalid` outcome; one
  i18n key in four languages).
- `b3843e2f8` logs up to two caller frames of an engine failure — never its message — so the next one names its
  origin; `f720f7879` tells the user that exchange rates must agree.

The developer accepted the plan on 2026-10-08 with one remark: «se l'inverso è un numero periodico, arrotondare alla
prima untà valida per quella valuta, in eccesso o difetto, non credo sia corretto dire che non è più l'ottimo, al
massimo possiamo dire "ottimo arrotondato" se proprio serve distinguerlo» — the coordinator's guarantees followed:
the plan stays `optimal_proven`, because the optimum is computed on amounts already rounded to the minor unit, and
«non autorevole» means only the «≈» sign.

## What came next

With a zero spread, about half of the cross rates derived from rates stored with ten decimals were now refused. The
question went to the developer, who chose the band B1 later the same day: a triangle within the storage error is accepted,
and the conversion is planned at the triangle — [[decisions/pac-rounding-against-the-plan]].

## Prevention

- `test_pac_planner_planner.py` (R1, R1b: `optimal_proven` and the residual recomputed with `Fraction`), report tests
  for both exact forms, seven normalizer cases, and five Tool API tests for the logged callers.
- No ledger field assumes a terminating decimal any more: an exact quantity that may repeat travels as an
  `ExactNumber`.

## Source files

| Role | Path |
|------|------|
| `ExactNumber` writer | `backend/app/services/pac_allocator/wire_numbers.py` |
| Ledger row field | `backend/app/schemas/pac_allocator/rows.py` |
| Coherence check | `backend/app/services/pac_allocator/normalize.py` |
| Report | `backend/app/services/pac_allocator/planner_report.py` |
| Adaptive display | `frontend/src/lib/features/tools/pac-allocator/planner/format.ts` |
| Planner and normalizer tests | `backend/test_scripts/test_services/test_pac_planner_planner.py`, `backend/test_scripts/test_services/test_pac_planner_normalize.py` |
| FX fix plan (row 15) | `LibreFolio_developer_journal/Release_2/Phase_0/13_pacAllocator/implementation/plan-phase00PacFxConversionFix.prompt.md` |
