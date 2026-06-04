---
title: "WAC target currency = last acquisition's currency (deterministic)"
category: decision
status: resolved
date: 2026-06-03
tags: [transactions, wac, currency, cost-basis, backend, deterministic]
related_features: [F-097]
related_decisions:
  - decisions/cost-basis-currency-object
  - decisions/wac-inline-validate-commit
---

# WAC Target Currency = Last Acquisition's Currency

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

## Source files

| Role | Path |
|------|------|
| determine_target_currency | `backend/app/services/wac_service.py` |
| Currency sentinella logic | `backend/app/services/transaction_service.py` |
| Frontend chip selector | `frontend/src/lib/components/transactions/WacPreviewSection.svelte` |
| Plan | `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-subplan/Parte4/Round6/Bugfix-SPD/plan-R3-SP-D-WacCurrency.prompt.md` |

