# Balance Validation

After every mutation batch, LibreFolio performs a **chronological balance walk** to ensure no broker ends up in an invalid state. This is implemented in `TransactionService._validate_broker_balances()`.

---

## What Is Validated

Two independent balance dimensions are tracked per broker:

| Dimension | Unit | Violation |
|-----------|------|-----------|
| **Cash balance** | Currency amount per currency code | Negative cash balance |
| **Asset holdings** | Quantity per asset ID | Negative asset position (shorting) |

These constraints can be **individually disabled per broker** via broker settings:

| Broker flag | Effect when `True` |
|-------------|-------------------|
| `allow_cash_overdraft` | Cash balance may go negative — no validation |
| `allow_asset_shorting` | Asset quantity may go negative — no validation |

When both flags are `True`, the balance walk is **skipped entirely** for that broker.

---

## The Balance Walk

The algorithm processes all transactions for a broker in **chronological order**, day by day:

```
For each day from start_date to end_date:
    For each transaction on this day:
        cash_balances[currency]  += transaction.amount
        asset_balances[asset_id] += transaction.quantity

    If not allow_cash_overdraft:
        assert all cash_balances[c] >= 0

    If not allow_asset_shorting:
        assert all asset_balances[a] >= 0
```

When a mutation affects only transactions after a certain date, the walk is **incremental**: it starts from pre-computed balances up to `from_date - 1` (fetched by `_get_balances_before_date()`) and only replays transactions from `from_date` forward. This avoids full re-scans of large brokers.

---

## Validation Errors

A violation raises `BalanceValidationError`, which is caught in `execute_batch()` and converted into a `TXValidationIssue`:

```python
class BalanceValidationError(Exception):
    broker_id: int
    date: date
    currency_or_asset: str   # e.g. "EUR" or "asset:42"
    balance: Decimal
    code: str                # TXValidationCode enum value
    params: dict             # for frontend i18n interpolation
```

| Code | Condition |
|------|-----------|
| `BALANCE_CASH_NEGATIVE` | Cash for a currency goes below 0 |
| `BALANCE_ASSET_NEGATIVE` | Quantity for an asset goes below 0 |

---

## Triggering Conditions

Balance validation runs automatically after every `execute_batch()` commit for each broker touched by the batch. The set of brokers to validate is determined from:

- `broker_id` of every created/updated transaction
- `broker_id` of every deleted transaction
- Both sides of linked pairs (TRANSFER, FX_CONVERSION)

---

## Design Rationale

### Why day-by-day and not just a final snapshot?

A transaction on 2024-01-05 might temporarily push cash negative even though a subsequent deposit on 2024-01-10 would bring it positive again. Day-by-day ensures **intra-period violations** are caught, not just end-state.

### Why not a DB constraint?

Running balances cannot be expressed as a simple DB constraint because they are **computed** from the aggregate of all prior transactions. A trigger-based approach would also be O(N) per row. The service-level walk runs once per batch at commit time, which is the correct trade-off.

---

## Broker Settings Reference

See `admin/settings.md` for how to enable overdraft/shorting per broker in the admin panel.

---

## Related

- 🏗️ **[Transaction Service](service.md)** — Where the validation is called
- ✂️ **[Split & Promote](split_promote.md)** — Validation runs after these too
- 📖 **[Access Control (RBAC)](../../architecture/access_control.md)** — Broker ownership model
