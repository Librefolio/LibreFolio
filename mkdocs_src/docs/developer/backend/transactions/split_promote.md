# Split & Promote

**Split** and **Promote** are two inverse operations on composite transactions (`TRANSFER`, `FX_CONVERSION`, `CASH_TRANSFER`). Both are implemented in `TransactionService` as atomic operations within `execute_batch()`.

---

## Concepts

| Operation | Direction | Description |
|-----------|-----------|-------------|
| **Split** | Composite → Two independent | Break a linked pair into two standalone transactions |
| **Promote** | Two independent → Composite | Merge two standalone transactions into a linked pair |

---

## Split

### What It Does

A split takes a **linked pair** (two transactions sharing a `link_uuid`) and:

1. Detaches both legs (removes `link_uuid` from both)
2. Re-types each leg according to the deterministic **Split Type Map**:

| Source composite type | From-leg becomes | To-leg becomes |
|-----------------------|-----------------|---------------|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` |
| `TRANSFER` | `ADJUSTMENT` | `ADJUSTMENT` |
| `FX_CONVERSION` | `WITHDRAWAL` | `DEPOSIT` |

3. Writes the two modified transactions back — in the same atomic batch

### When to Use

- A broker CSV imported a cross-currency transfer as a single row; BRIM created it as `CASH_TRANSFER` but the two legs actually belong to different purposes
- A `TRANSFER` was created incorrectly and needs to be corrected independently

### API

The split is submitted as part of the standard batch endpoint:

```json
POST /transactions/commit
{
  "splits": [
    { "id_a": 101, "id_b": 102 }
  ]
}
```

Both `id_a` and `id_b` must be the two legs of the same linked pair (same `link_uuid`). Passing unlinked transactions raises a validation error.

---

## Promote

### What It Does

Promote merges two **independent** transactions (no `link_uuid`) into a new linked composite. The operation is atomic:

1. Validates that the two transactions are compatible (types, currencies, brokers)
2. **Deletes** the two originals
3. **Creates** two new linked transactions (same data, new `link_uuid`, updated types)

This delete-and-recreate approach (rather than update-in-place) ensures balance validation runs cleanly from scratch on the new pair.

### Promotion Rules

The allowed promotion pairs are defined in `TX_TYPE_METADATA.promote_from` rules:

| From types | Target composite | Constraints |
|-----------|-----------------|-------------|
| `DEPOSIT` + `WITHDRAWAL` | `CASH_TRANSFER` | Distinct brokers, same currency |
| `DEPOSIT` + `WITHDRAWAL` | `FX_CONVERSION` | Same or distinct brokers, different currencies |
| `DEPOSIT` + `WITHDRAWAL` + asset fields | `TRANSFER` | Distinct brokers, requires `asset_id` + `quantity` |

Rule matching is handled by `_find_promote_rule_match()` and additional constraint checks in `_check_promote_constraints()`.

### Promote Suggest

Before promoting manually, clients can call the **suggest endpoint** to get candidate pairs:

```
POST /transactions/promote-suggest
{
  "items": [{ "tx_id": 101 }]
}
```

`promote_suggest_bulk()` scans accessible transactions and returns ranked candidates compatible with the input transaction, including which composite type would result.

### API

```json
POST /transactions/commit
{
  "promotes": [
    {
      "id_a": 201,
      "id_b": 202,
      "new_type": "CASH_TRANSFER"
    }
  ]
}
```

For `TRANSFER` promotion, additionally supply `asset_id`, `quantity`, and optionally `cost_basis_override`.

---

## Error Handling

Both operations participate in the standard **collect-all-errors** pipeline:

- Errors are reported as `TXValidationIssue` items in the response
- A single error in any split or promote item **rolls back the entire batch**
- The frontend receives the full set of issues to highlight every problem at once

Common errors:

| Code | Cause |
|------|-------|
| `pairTypeMismatch` | Split IDs do not belong to the same linked pair |
| `pairSameBroker` | TRANSFER/CASH_TRANSFER promote attempted with same broker on both sides |
| `promoteIncompatible` | The two transaction types cannot form any composite |
| `missingField` | TRANSFER promote missing `asset_id` or `quantity` |

---

## Related

- 🏗️ **[Transaction Service](service.md)** — Batch pipeline and execution model
- ⚖️ **[WAC & Cost Basis](wac.md)** — Cost basis impact of TRANSFER promotes
- 🔒 **[Balance Validation](balance_validation.md)** — Runs after every split/promote
