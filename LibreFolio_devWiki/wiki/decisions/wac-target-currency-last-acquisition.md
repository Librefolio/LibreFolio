---
title: "WAC target currency = last acquisition's currency (deterministic)"
category: decision
status: resolved
date: 2026-06-03
updated: 2026-10-07
tags: [transactions, wac, currency, cost-basis, backend, deterministic]
related_features: [F-097]
related_decisions:
  - decisions/cost-basis-currency-object
  - decisions/wac-inline-validate-commit
  - decisions/financial-math-single-average-cost
---

# WAC Target Currency = Last Acquisition's Currency

> **Scope note (2026-10-07).** This rule now governs only the callers of the WAC facade `compute_wac_iterative()`. See
> [Scope since 2026-10-07](#scope-since-2026-10-07) below.

## Context

When calculating WAC (Weighted Average Cost) for a multi-currency portfolio, the system needs to decide what currency to express the result in. Previously the heuristic was "majority currency among qualifying transactions" — but this is non-deterministic when there's a tie and confusing when adding a single new TX flips the majority.

## Decision

**Target currency = currency of the most recent acquisition transaction (BUY/TRANSFER-IN).**

When no explicit override is provided (`cost_basis_override: null` + mode auto), the backend calls `determine_target_currency()` which:
1. Finds all qualifying BUY/TRANSFER-IN transactions for the (broker, asset)
2. Takes the **most recent** one by date
3. Returns its currency as the target

## Override Mechanism

The user can override via the chip valuta selector in the WAC preview:
- Frontend sends `cost_basis_override: {code: "KRW", amount: "0"}` (sentinella)
- Backend sees `amount = "0"` + mode auto → interprets `code` as target currency hint
- Calculates WAC in KRW, converting all qualifying TX costs via FX

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Majority currency | Non-deterministic on tie, confusing when a single TX flips result |
| Asset's base currency | Many assets are traded in multiple currencies across brokers |
| Portfolio base currency | Doesn't respect user's actual trading pattern |
| Always ask user | Too many clicks for the common case |

## Consequences

- **Predictable**: same inputs always produce same target currency
- **Last-write-wins feel**: the most recent purchase "sets the tone"
- **Override available**: power users can always pick their preferred currency via chip
- **Backward compat**: existing TXs with `cost_basis_override: null` get auto-determined currency on next validate

## Scope since 2026-10-07

Release 2 workstream P (issue #32) gave the application a single average-cost function,
`compute_average_costs(..., report_currency=T)`, which every caller runs in a currency it chooses — see
[[decisions/financial-math-single-average-cost]]. The rule recorded on this page is how **the facade's callers**
choose it:

| Caller | Target currency |
|--------|-----------------|
| Transaction preview / automatic cost basis (`TransactionService._compute_wac_for_auto_items()`, via `compute_wac_iterative()`) | The `cost_basis_override.code` sent as a hint (the sentinel above), otherwise **the last acquisition's currency** — this rule |
| `POST /portfolio/wac` (`portfolio_api.py`, via `compute_wac_iterative()`) | **The last acquisition's currency** — this rule |
| PAC planner (`portfolio_allocation_source.py`, via `compute_wac_iterative()`) | The report currency T, passed as `target_currency_override` |
| Portfolio engine → Dashboard purchase cost, realized/unrealized P&L, holdings' WAC per unit, Yield on Cost | The report currency T |
| Lots analysis WAC lines | The analysis report currency T |
| Broker summary (`GET /brokers/{id}/summary`) | T = the asset's own currency, one call per currency group |

So the alternative this page rejected — "portfolio base currency" — is exactly what the Dashboard uses. That is not a
contradiction: it answers a different question (what the position cost, in the currency the user is reading the
portfolio in), not which currency to freeze into a transfer's editable cost basis.

The implementation moved too: `determine_target_currency()` now lives in
`backend/app/services/financial_math/average_cost.py` and is used only by the facade. It returns the currency of the
most recent movement that adds quantity; on a date tie the first in input order wins; when that latest addition is a
split or an acquisition of unknown cost — or there is no addition at all — it returns the asset currency.

## Source files

| Role | Path |
|------|------|
| determine_target_currency | `backend/app/services/financial_math/average_cost.py` |
| WAC facade `compute_wac_iterative()` (override, or this rule) | `backend/app/services/portfolio_service.py` |
| Currency sentinella logic | `backend/app/services/transaction_service.py` |
| `POST /portfolio/wac` | `backend/app/api/v1/portfolio_api.py` |
| PAC planner (passes T as override) | `backend/app/services/portfolio_allocation_source.py` |
| Frontend chip selector | `frontend/src/lib/components/transactions/wac/WacPreviewSection.svelte` |
| Target-currency unit tests (`TestTargetCurrency`) | `backend/test_scripts/test_services/test_financial_math/test_average_cost.py` |
| Developer docs (the WAC facade, "Two target-currency rules") | `mkdocs_src/docs/developer/backend/transactions/wac.md` |
| Plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` |

> Until 2026-10-07 the first row cited `backend/app/services/wac_service.py`. The function actually lived in
> `backend/app/utils/financial_utils.py`, which Phase 09 M1 (commit `81fc556d7`) moved to
> `backend/app/utils/financial/wac_utils.py`, deleted on 2026-10-07; `wac_service.py` became `portfolio_service.py` in
> the same commit.

