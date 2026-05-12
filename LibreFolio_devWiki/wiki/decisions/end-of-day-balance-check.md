---
title: "Balance validation uses end-of-day aggregation — intra-day order irrelevant"
category: decision
status: resolved
date: 2026-05-11
tags: [backend, transactions, validation, balance, daily-point]
related:
  - concepts/daily-point-policy
  - decisions/formmodal-contextual-validate
  - features/F-046
---

# Decision: End-of-Day Balance Check (Order-Independent)

## Context

During Plan C2 testing, a question arose: if a user creates DEPOSIT + BUY on the same day, does the order matter? Investigation of `_validate_broker_balances()` in `transaction_service.py` revealed the algorithm already accumulates all transactions for a day before checking the balance — making intra-day order irrelevant.

## Options Considered

1. **Type-priority ordering** (`ORDER BY date, type_priority, id`): DEPOSIT before BUY by convention. Deterministic but imposes artificial constraints.
2. **End-of-day aggregation** (current implementation): Sum all deltas for the day, check balance at end-of-day only. Intra-day order doesn't matter.

## Decision

**Option 2 is already implemented** and is the correct design for a daily-point system (one price per day, one balance per day). Intra-day states are not observable, so imposing ordering constraints would be arbitrary.

The "problem" users observed was not an algorithm bug but **context starvation** in FormModal (validated single row without bulk context) — fixed by [[decisions/formmodal-contextual-validate]].

## Consequences

- Same-day DEPOSIT+BUY always passes regardless of insertion order (net positive = OK)
- Same-day BUY+DEPOSIT also passes (aggregated to same end-of-day balance)
- Insertion order (`id`) used only for deterministic rendering, not validation
- 8 dedicated backend tests (`test_tx_balance_walk.py`) document and verify this behavior
- Consistent with [[concepts/daily-point-policy]] (one record per day)

## Source files

| Role | Path |
|------|------|
| Balance validation | `backend/app/services/transaction_service.py` |
| Balance walk tests | `backend/test_scripts/test_api/test_tx_balance_walk.py` |

