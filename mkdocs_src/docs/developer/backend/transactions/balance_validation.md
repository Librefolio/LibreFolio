# 🔒 Balance Validation

Transaction batches perform a final **end-of-day balance replay** before the
response is finalized. The stage wrapper is
`transaction_batch_stages.validate_balances()`; the broker replay itself remains
`TransactionService._validate_broker_balances()`.

This is validation inside the caller's current database transaction. It is not a
commit and it does not own rollback.

---

## 🧭 Pipeline Boundary

Balance replay runs after delete, split, update, updated-pair validation, create,
promote, create-link resolution, inline WAC/FX handling, and required-cost-basis
validation.

`TransactionBatchContext.earliest_date_by_broker` is updated by successful
mutation stages. For each broker, the context retains the minimum date reported
by those operations; a moved update uses the earlier of its old and new dates.
Immediately before replay, `validate_balances()`:

1. calls `session.flush()` so queries see the staged mutations;
2. maps successful result IDs back to their operation and batch index for issue
   attribution; and
3. calls `_validate_broker_balances(broker_id, from_date, batch_tx_ids=...)` for
   each affected broker.

---

## ⚖️ What Is Validated

Two independent dimensions are tracked per broker:

| Dimension | Unit | Violation |
|-----------|------|-----------|
| **Cash** | Amount per currency code | End-of-day cash balance below zero |
| **Asset holdings** | Quantity per asset ID | End-of-day asset quantity below zero |

Broker settings control each check:

| Broker flag | Effect when `True` |
|-------------|-------------------|
| `allow_cash_overdraft` | Negative cash is permitted |
| `allow_asset_shorting` | Negative asset quantity is permitted |

When both flags are true, `_validate_broker_balances()` returns without querying
or replaying transactions.

---

## 📅 End-of-day Replay

For an incremental replay beginning at `from_date`, the service first obtains
cash and asset balances from all rows with `date < from_date`. It then queries
the broker's rows from `from_date` onward, groups them by date, and applies every
row for a date before checking either balance dimension:

```text
balances = SUM(all rows before from_date)

for each date through the final transaction date:
    apply every cash and quantity delta dated that day
    validate all cash balances unless overdraft is allowed
    validate all asset balances unless shorting is allowed
```

The invariant is therefore **end-of-day**, not per-row or intraday. Opposing
movements on the same date are netted before validation. A later date cannot
repair an earlier negative close because each date is checked before replay
advances.

Starting at the earliest affected date preserves correctness for backdated
creates, deletes, splits, promotions, and updates without replaying the broker's
complete history on every batch.

---

## 🚨 Issue Shape and Stop Condition

`BalanceValidationError` is defined in
`backend/app/services/transaction_batch_context.py` and carries:

```python
broker_id: int
date: date
currency_or_asset: str
balance: Decimal
code: str
params: dict
batch_index: int
batch_operation: str
```

The two stable validation codes are:

| Code | Condition |
|------|-----------|
| `balanceCashNegative` | A currency closes a day below zero |
| `balanceAssetNegative` | An asset quantity closes a day below zero |

When possible, the replay attributes the issue to the last staged batch
transaction that reduced that currency or asset on the failing date. Otherwise
it uses operation `create` and index `-1` as a broker-level fallback.

`validate_balances()` wraps the broker loop in one `try` block. It catches the
first `BalanceValidationError`, appends one `TXValidationIssue`, and exits the
stage; it does not continue collecting later balance exceptions from other
currencies, dates, or brokers. Unexpected replay exceptions likewise become one
broker-level balance-validation issue.

---

## 🔁 Transaction Ownership

The replay only flushes the session. Neither the stage nor `execute_batch()`
calls `commit()` or `rollback()`:

- `/transactions/validate` always rolls back after receiving the response;
- `/transactions/commit` commits only when `response.committed` is true;
- any balance issue makes `committed` false, so the commit route rolls back all
  staged mutations.

This caller-owned boundary is what makes a multi-broker batch atomic while still
allowing the same service pipeline to power a dry run.

---

## ❓ Why End-of-day Instead of a DB Constraint?

Running balances depend on the aggregate of all prior rows and cannot be
expressed as a simple row constraint. Checking once after all rows for a date
also avoids rejecting a valid same-day set merely because of insertion order,
while still rejecting a negative close before a later day's deposit or
acquisition can mask it.

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — Ordered stages and response semantics
- ✂️ **[Split & Promote](split_promote.md)** — Mutations that feed the replay boundary
- 📖 **[Access Control (RBAC)](../../architecture/access_control.md)** — Broker ownership model
