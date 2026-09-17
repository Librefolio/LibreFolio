# ✂️ Split & Promote

Split and batch promote both change the shape of composite transactions, but they
are not implemented as delete-and-recreate inverses:

| Operation | Direction | Batch behavior |
|-----------|-----------|----------------|
| **Split** | Composite pair → two standalone rows | Mutates both persisted rows in place and removes their reciprocal links |
| **Promote** | Two standalone rows → composite pair | Mutates the resolved rows in place and creates reciprocal links |

The durable pair is always stored with reciprocal `related_transaction_id` values.
`link_uuid` is only a request-scoped correlation value for creates; it is not a
column on `Transaction`.

---

## 🔢 Pipeline Position

The relevant `execute_batch()` stages run in this order:

```text
delete → split → update → updated-pair validation → create → promote → create-link resolution
```

Split deliberately precedes update. A batch can therefore split a pair and then
apply updates whose type swaps are legal only for the resulting standalone types.
Promote follows create so its references can resolve either persisted rows or rows
that were flushed earlier in the same batch.

---

## ✂️ Split

### ⚙️ In-place behavior

For each `TXSplitBatchItem`, `apply_splits()`:

1. resolves both required database IDs;
2. verifies that each row's `related_transaction_id` points to the other;
3. determines source/destination by negative/positive quantity for `TRANSFER`, or
   by negative/positive amount for cash pairs;
4. changes both row types using `SPLIT_TYPE_MAP`;
5. clears both `related_transaction_id` values;
6. clears `asset_id` for the cash split outcomes; and
7. records both brokers' affected dates and a two-ID `split` result.

The rows keep their IDs. No create or delete is involved.

| Source composite type | Negative/source leg | Positive/destination leg |
|-----------------------|---------------------|--------------------------|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` |
| `TRANSFER` | `ADJUSTMENT` | `ADJUSTMENT` |
| `FX_CONVERSION` | `WITHDRAWAL` | `DEPOSIT` |

### 📦 Request shape

Split is a first-class item in the unified batch:

```json
POST /transactions/commit
{
  "splits": [
    {"id_a": 101, "id_b": 102}
  ]
}
```

`id_a` and `id_b` must be different positive IDs and must identify the two
reciprocally linked rows. Their input order does not determine source and
destination; the signed quantity or amount does.

---

## 🔗 Batch Promote

### ⚙️ In-place behavior

`apply_promotes()` accepts:

- two saved rows (`id_a` + `id_b`);
- two creates from this batch (`link_uuid_a` + `link_uuid_b`); or
- one saved and one same-batch row.

Each side must provide exactly one reference form: `id_*` or `link_uuid_*`, never
both. After resolving the references, the stage:

1. rejects a row that already has `related_transaction_id`;
2. calls `_find_promote_rule_match()` to infer the target type from
   `TX_TYPE_METADATA.promote_from` and its field constraints;
3. assigns the inferred type to both existing ORM rows;
4. writes reciprocal `related_transaction_id` values;
5. applies recognized `resolved_fields`;
6. marks same-batch correlation keys as consumed so the later create-link stage
   does not process them again; and
7. emits a `promote` result containing the same two row IDs.

No original row is deleted and no replacement row is created.

### 🧭 Inferred target rules

The batch payload does not contain `new_type`. The current metadata permits:

| Standalone input types | Inferred target | Required constraints |
|------------------------|-----------------|----------------------|
| `ADJUSTMENT` + `ADJUSTMENT` | `TRANSFER` | Same `asset_id`, different brokers, opposite quantities |
| `WITHDRAWAL` + `DEPOSIT` | `FX_CONVERSION` | Same broker, different cash currencies |
| `WITHDRAWAL` + `DEPOSIT` | `CASH_TRANSFER` | Different brokers, same cash currency, opposite cash amounts |

The match is symmetric: either row may be supplied as side A.

### 📦 Request shape

A saved-row promote can include values already resolved by the merge UI:

```json
POST /transactions/commit
{
  "promotes": [
    {
      "id_a": 201,
      "id_b": 202,
      "resolved_fields": {
        "description": "Broker transfer",
        "tags": ["internal"],
        "date": "2026-09-11",
        "cost_basis_override": {"code": "EUR", "amount": "42.50"}
      }
    }
  ]
}
```

The recognized `resolved_fields` keys are `description`, `tags`, `date`, and
`cost_basis_override`. Description, tags, and date are applied to both rows. For
an asset transfer, the cost basis is applied to the positive-quantity receiver
and cleared from the sender.

A mixed saved/new request uses a create correlation value:

```json
POST /transactions/commit
{
  "creates": [
    {
      "broker_id": 8,
      "type": "DEPOSIT",
      "date": "2026-09-11",
      "cash": {"code": "EUR", "amount": "300"},
      "link_uuid": "draft-deposit-8"
    }
  ],
  "promotes": [
    {"id_a": 201, "link_uuid_b": "draft-deposit-8"}
  ]
}
```

Here `link_uuid_b` resolves the just-flushed create. Once consumed by promote,
that correlation group is skipped by `resolve_create_links()`. The persisted
rows contain only reciprocal `related_transaction_id` values.

### 🧮 Cost basis boundary

A promote item has no `cost_basis_mode`, and `apply_promotes()` does not calculate
WAC. The later `_compute_wac_for_auto_items()` worklist is built only from parsed
create and update items. Promote-specific cost-basis resolution therefore comes
from `resolved_fields.cost_basis_override`, supplied by the frontend merge flow
or another API client.

---

## 🛣️ Legacy Live Promote Endpoint

`POST /transactions/transfers/promote` remains a separate live endpoint with a
different contract:

- request: `from_tx_id`, `to_tx_id`, `new_type`, and the optional
  `asset_id`, `quantity`, and `cost_basis_override` fields needed for
  `TRANSFER`;
- implementation: snapshot the two `DEPOSIT`/`WITHDRAWAL` rows, delete them,
  build two replacement create payloads with a shared `link_uuid`, and call
  `execute_batch()` with those deletes and creates; and
- response: `TXTransferPromoteResponse`, whose fields include the legacy
  `rolled_back`, `new_from_tx_id`, `new_to_tx_id`, and `errors`.

This delete-and-create behavior applies only to the legacy endpoint. It must not
be used to describe `promotes[]` in `/transactions/validate` or
`/transactions/commit`.

---

## 🧯 Errors and Rollback

Split/promote row failures are accumulated as `TXValidationIssue` entries while
their stage loops continue. Common stable codes are:

| Code | Cause |
|------|-------|
| `txNotFound` | A split ID does not resolve |
| `splitIdsMismatch` | Split IDs are not reciprocal partners |
| `typeCannotSplit` | The current pair type has no split mapping |
| `promoteRefNotFound` | A saved or same-batch promote reference cannot be resolved |
| `alreadyPaired` | A promote candidate already has a persistent partner |
| `noPromoteRule` | No metadata rule and constraint set matches the two rows |

The service does not roll the session back itself. `/transactions/validate`
always rolls back; `/transactions/commit` commits only when
`TXBatchResponse.committed` is true and rolls back otherwise. Access denial may
return before either mutation stage, and balance replay stops after its first
balance exception, so the overall pipeline is not an unconditional
collect-every-error pass.

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — Batch order, context, and transaction ownership
- ⚖️ **[WAC & Cost Basis](wac.md)** — Create/update auto-WAC and promote's payload boundary
- 🔒 **[Balance Validation](balance_validation.md)** — Final post-flush balance replay
