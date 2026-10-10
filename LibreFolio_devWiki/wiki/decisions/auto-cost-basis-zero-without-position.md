---
title: "Auto cost basis without a position: 0 is the correct fallback, and the user corrects that transaction"
category: decision
status: resolved
date: 2026-10-09
tags: [backend, frontend, transactions, cost-basis, wac, auto-mode, adjustment, transfer, product-decision]
related: [decisions/wac-inline-validate-commit, decisions/financial-math-single-average-cost, decisions/cost-basis-currency-object, features/F-097, features/F-046, entities/transaction-batch-pipeline, sources/phase00-auto-cost-no-position-2026-10]
---

# Decision: in Auto, an empty pool gives a cost of 0 — by choice

## Context

Backlog item **P-1** ("Auto cost with no position: cost 0 saved without a warning"), found while verifying the #32
archive: an incoming `ADJUSTMENT` — or the receiving side of a `TRANSFER` — saved in `cost_basis_mode: auto` on a
broker whose pool holds no units of the asset on that date gets a cost basis of **0 per unit**, and its whole value
then reads as gain. Typical cases: an opening position, a gift, the new line of a spin-off. Auto is the default for
incoming rows, so the default path produces it. Checked at `083ed26dc`:

- the WAC facade `compute_wac_iterative()` returns `Currency(asset_currency, 0)` when there are no rows
  (`backend/app/services/portfolio_service.py`, ~`:185-190`), and a pool emptied by sales has a unit cost of 0
  (`CostStep.unit_cost_report`, `backend/app/services/financial_math/average_cost.py`, ~`:155`);
- Auto writes that value: `if wac_result.wac:` is true for a `Currency` of amount 0
  (`_compute_wac_for_auto_items()`, `backend/app/services/transaction_service.py`, ~`:1012-1014`);
- the required-cost-basis check skips Auto rows (`_auto_mode_indices` and its three callers,
  `backend/app/services/transaction_batch_stages.py`, ~`:875`, `:889`, `:914`, `:935`);
- an explicit 0 is `ADD_ZERO_COST` and raises no `MISSING_COST_BASIS` (`average_cost.py`, ~`:431-432`);
- Auto is the default in the form (`costBasisMode = $state('auto')`, `TransactionFormModal.svelte`) and for new bulk
  rows that allow a cost basis (`TransactionBulkModal.svelte`);
- for a `TRANSFER` the pool is the origin broker's: if it is empty the balance check usually refuses the pair already,
  so the `ADJUSTMENT` is the case that matters;
- v1.1.0 behaved the same way (checked on the tag).

## Options considered

1. **Treat Auto on an empty pool as a missing cost basis** — the same `costBasisRequired` issue that blocks a Manual
   row with an empty field; the user must type a cost (0 included) to save. Analysed in full (plan §2: a facade flag
   `empty_pool_as_missing`, the same issue shape, no new schema), and the analyst's recommendation, because a silent
   0 sits badly next to the "no silent zero" rule of #32.
2. **Save at 0 with a warning** — what three user-facing texts already promised (residual P-11).
3. **"Enter the empty field and leave it = explicit 0"** — the developer's first direction ("as now: entering and
   leaving means the user accepts the 0"). The plan showed it does not exist today: in Manual a blur on an empty field
   emits `null` (→ `costBasisRequired`); in Auto a blur keeps the value — which, on an empty pool, is precisely this 0.
4. **Change nothing** — chosen.

## Decision (developer, 2026-10-09)

> «no chat, non facciamolo e segnamo la decisione, se i dati mancano lo 0 come fallback per auto è corretto. se
> bisogna cambiare sarà l'utente ad andare su quella transazione e correggere.»
>
> (No chat — let's not do it and record the decision: if the data is missing, 0 as the fallback for Auto is correct.
> If it has to change, the user will go to that transaction and correct it.)

- **No implementation.** In Auto, with the source pool empty at the row's date, the cost per unit is 0 by choice: it
  is the correct fallback when the data is missing.
- If the true cost differs, the user opens that transaction and enters it (Manual). The remedy is the user's, not the
  app's.
- Options 1–3 and the drafted CHANGELOG entry were dropped; the first direction (option 3) is superseded.

## Consequences

- `test_wac_inline.py::test_wacp27_empty_pool_wac_zero` now pins the intended behaviour.
- **Not a contradiction of #32.** [[decisions/financial-math-single-average-cost]] forbids silent zeros for *missing
  exchange rates and unknown costs* — a movement whose cost is `None` is `ADD_UNKNOWN_COST` and surfaces as
  `MISSING_COST_BASIS`. Here the cost is not unknown: Auto computed it from an empty pool and wrote 0, a deliberate
  and documented fallback.
- [[decisions/wac-inline-validate-commit]] gains a note on `'auto'`.
- Residuals moved to backlog 38: **P-10** — `MISSING_COST_BASIS` is reachable from the app by retyping a SPLIT event
  that has a linked `ADJUSTMENT` (the row was saved in Auto without a cost while it was split-linked); **P-11** — three
  texts promise a zero-cost lot when a Manual cost basis is left empty, while the backend refuses that save with
  `COST_BASIS_REQUIRED`.

## Links

- [[sources/phase00-auto-cost-no-position-2026-10]] — the analysis and the closing note.
- [[features/F-097]] — WAC.

## Source files

| Role | Path |
|------|------|
| WAC facade — zero WAC without rows | `backend/app/services/portfolio_service.py` |
| Auto writes the WAC (`_compute_wac_for_auto_items`) | `backend/app/services/transaction_service.py` |
| Required-cost-basis check, Auto rows skipped | `backend/app/services/transaction_batch_stages.py` |
| `ADD_ZERO_COST`, empty-pool unit cost | `backend/app/services/financial_math/average_cost.py` |
| Form default (Auto) | `frontend/src/lib/components/transactions/modals/TransactionFormModal.svelte` |
| Bulk default for new rows (Auto) | `frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte` |
| Test pinning the decision | `backend/test_scripts/test_api/test_wac_inline.py` |
| Analysis and decision (§1, §2, §10) | `LibreFolio_developer_journal/Release_2/phases/39_autoCostNoPosition/plan-phase00AutoCostNoPosition.prompt.md` |
