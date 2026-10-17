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
       → WAC and FX issues
```

Split deliberately precedes update. A batch can therefore split a pair and then
apply updates whose type swaps are legal only for the resulting standalone types.
Promote follows create so its references can resolve either persisted rows or rows
that were flushed earlier in the same batch. The cost of a split `TRANSFER`'s giving
leg waits for the WAC stage, which sees every other row of the batch (see
[The giving leg of a `TRANSFER`](#transfer-giving-leg)).

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
6. clears `asset_id` for the cash split outcomes;
7. for a `TRANSFER` pair, records the giving leg, with the split's index, in
   `context.handover_rows`, for the WAC stage to price (see
   [The giving leg of a `TRANSFER`](#transfer-giving-leg)); and
8. records both brokers' affected dates and a two-ID `split` result.

The rows keep their IDs. No create or delete is involved.

| Source composite type | Negative/source leg | Positive/destination leg |
|-----------------------|---------------------|--------------------------|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` |
| `TRANSFER` | `ADJUSTMENT` | `ADJUSTMENT` |
| `FX_CONVERSION` | `WITHDRAWAL` | `DEPOSIT` |

Deleting a broker with its transactions converts the surviving half of each pair
with another broker by the same rules, through the same helpers of
`batch_edits.py`: `pair_sides()` (step 3) and `make_standalone()` (steps 4–6), and
gives a giving `TRANSFER` leg the cost a split gives it (below). Two differences: a
received `TRANSFER` without a cost basis first gets its sender's Auto cost, which a
split does not write; and a giving leg whose cost needs a missing conversion stays a
`TRANSFER` without its link, where a split is refused. See
[Transaction Service — Broker Deletion](service.md#broker-deletion).

### 📤 The giving leg of a `TRANSFER` {: #transfer-giving-leg }

A split `TRANSFER` pair leaves two `ADJUSTMENT`s. The receiving one keeps its cost
basis. The giving one takes units out, and without a cost basis the FIFO lots would
read them as destroyed — a write-off — so it leaves at the **Auto cost of its own
broker**, at which the lots hand its units over (decision 47 of release 1.3; see
[Hand-over at cost](fifo_lot_engine.md#handover-at-cost)):

- `apply_splits()` only records the leg (step 7). `compute_wac_and_fx_issues()`
  (`batch_costs.py`) prices it after the Auto rows of
  `_compute_wac_for_auto_items()`, once every row of the batch is in place: a
  purchase the same batch adds on that broker before the leg's date counts.
- The cost is `TransactionService._handover_cost()`: `_auto_cost()` on the leg's
  broker, up to its date, without the leg itself — the cost a broker deletion
  writes too. `_write_auto_cost()` stores `cost_basis_override` and
  `cost_basis_currency` together.
- An update of the same batch that gives the leg a `cost_basis_override` wins: the
  stage leaves that leg alone. Such an update sends the cost without a
  `cost_basis_mode`: rule 12 refuses a mode on an `ADJUSTMENT` taking units out (see
  [Per-type rules](service.md#per-type-rules)).
- When the cost needs a missing conversion, the split is refused: one
  `wacFxUnavailable` issue on operation `split`, at the split's index, `ref_id` the
  giving leg, `field` `cost_basis_override`, with `pairs` and `pair_details` in
  `params` as for an Auto row. Nothing commits, and `/transactions/validate`
  reports the same issue.
- When the leg's broker pool holds a row that cannot be read — a quantity, amount or
  stored cost basis that reads `None` (see [Unreadable pool](wac.md#unreadable-pool)) —
  the split is refused the same way: one `autoCostUnreadable` issue on operation
  `split`, `ref_id` the giving leg, `params` `{"count": N}`, no id of those rows (W-B69).
- Like the inline WAC, the stage prices the leg only when no non-balance issue
  exists yet.

Tests: `./dev.py test services transaction-cost-basis-rule`
(`TestDecision47TheGivingLegOfATransfer`).

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

The Transactions page sends this item on its own, outside the bulk workspace:
**Split pair** in a row's actions asks for confirmation, then calls
`commitTransactions({splits: [{id_a, id_b}]})`. Inside the workspace a saved
pair is queued in `pendingSplits` and travels with **Save All** instead (see
[Transaction Staging State](../../frontend/state/transaction-draft.md)).

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
3. validates both rows as they would be once promoted: `_promoted_state_issues()`
   runs `validate_transaction_business_rules()` on each row with the target type,
   the per-type rules that creates and updates go through too. Each error becomes
   an issue on operation `promote`, at the promote's index, with `ref_id` set only
   for a saved row; the promote is then skipped and neither row changes;
4. assigns the inferred type to both existing ORM rows;
5. writes reciprocal `related_transaction_id` values;
6. clears `cost_basis_override` and `cost_basis_currency` on a side whose new type
   takes no cost basis (`cost_basis_allowed()` is false: the giving side of a
   `TRANSFER`), such as an `ADJUSTMENT` taking units out that a split left with a
   cost; the receiving side keeps its own (decision 47);
7. applies the merged values of `resolved_fields`, the keys the request names (see
   [Request shape](#promote-request-shape));
8. marks same-batch correlation keys as consumed so the later create-link stage
   does not process them again; and
9. emits a `promote` result containing the same two row IDs.

No original row is deleted and no replacement row is created.

Step 3 exists for a row linked to an asset event, such as an `ADJUSTMENT` linked to a
`SPLIT`. A promote never clears `asset_event_id`, and the business rules accept that
link only on the types `TX_TYPE_METADATA` marks `event_compatible` (`DIVIDEND`,
`INTEREST`, `ADJUSTMENT`; see [Per-type rules](service.md#per-type-rules)): every
promote target has `event_compatible: false`, so such a row is refused with
`eventTypeIncompatible`. Without the check it would become a `TRANSFER` still linked
to the split, and the average cost, which treats every row linked to a `SPLIT` event
as a split whatever its type, would read it as one.

### 🧭 Inferred target rules

The batch payload does not contain `new_type`. The current metadata permits:

| Standalone input types | Inferred target | Required constraints |
|------------------------|-----------------|----------------------|
| `ADJUSTMENT` + `ADJUSTMENT` | `TRANSFER` | Same `asset_id`, different brokers, opposite quantities |
| `WITHDRAWAL` + `DEPOSIT` | `FX_CONVERSION` | Same broker, different cash currencies |
| `WITHDRAWAL` + `DEPOSIT` | `CASH_TRANSFER` | Different brokers, same cash currency, opposite cash amounts |

The match is symmetric: either row may be supplied as side A.

### 📦 Request shape {: #promote-request-shape }

A saved-row promote can carry merged values, `resolved_fields`:

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

`resolved_fields` is a `TXPromoteResolvedFields` (`backend/app/schemas/transactions/batch.py`;
H-41, within R13-SEC7-3): a `StrictModel` typed like a create's fields, so an unknown key is
refused.

| Key | Type | Applied to |
|-----|------|------------|
| `description` | `Optional[str]`, at most 500 characters | Both rows |
| `tags` | `Optional[List[str]]`, through the create's tag validator (`validate_tags_list()`: a list, or a comma-separated string) | Both rows |
| `date` | `Optional[date]`; an explicit `null` is refused | Both rows |
| `cost_basis_override` | `Optional[Currency]` | For an asset transfer, the positive-quantity receiver only; the sender's is cleared (decision 47) |

`_apply_promote_resolved_fields()` (`batch_creates.py`) applies the keys the request
names (`model_fields_set`): a key left out leaves both rows alone, and an explicit
`null` clears the description, the tags or the cost basis. Once parsed, the resolved
cost basis is checked against its column (`check_decimal_limits()`, see
[Decimal limits](service.md#decimal-limits)) and the resolved date against the range
(`check_dates()`, see [Transaction dates](service.md#transaction-dates)), before any
stage applies them.

A value the model refuses becomes an issue of the promote at the batch's parse
(`_parse_lenient()`): `operation` `promote`, pydantic's error type as `code`, `params`
null, and a `field` named by the merged field itself, without the `resolved_fields.`
prefix (`_loc_to_field()`): `description`, `tags`, `date`, `cost_basis_override`,
`cost_basis_override.amount`, or the unknown key. The issue thus carries that field's
label. As with any parse refusal of this lenient batch, the other operations are
still checked, then nothing is saved (`committed=False`). Before H-41 the dict was
applied as sent: a malformed date, tags or cost basis raised out of the batch, a 500;
a description that was no string reached the `Text` column; an unknown key was
ignored.

The Transactions page sends a saved-row promote on its own, outside the
workspace, when exactly two selected rows are unpaired, sit on brokers the user
can edit, and match a rule (`findPromoteMatch()` on the `promote_from` metadata
of `GET /transactions/types`, which finds none when a row is linked to an asset
event and the target type refuses the link). **🔗 Promote pair** then opens a plain
confirmation, or `PromoteMergeModal` when the two rows differ in description,
tags, date or cost basis; only the merge dialog adds `resolved_fields`, with
`description` and `tags` alone, as **Merge all** does in the bulk workspace
(`PromoteAllModal`): `date` and `cost_basis_override` come from API clients only.
The merged description joins the two with a line break (`mergeStrings()` in
`frontend/src/lib/features/transactions/bulk/promoteHelpers.ts`), so two long
descriptions can pass 500 characters and are then refused, as a create's
description is (`TXCreateItem.description` takes 500 too).

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
from `resolved_fields.cost_basis_override`, which only an API client sends (the
merge dialogs send `description` and `tags`); without that key, the receiver keeps
the cost basis it already has, and the sender is left without one (step 6).

Because `apply_promotes()` writes `related_transaction_id` before the WAC step, a
create or update in Auto that the promote makes the receiving side averages its
partner's broker, as of the partner's date and without the partner's outgoing leg.

`validate_cost_basis()` then checks the receiving side like any other row: a new
row as a create and a saved row also in `updates[]` as that update (the promote
changes its type, so even an update of its notes alone is checked), both unless in
Auto; any other saved row without a cost basis gets `costBasisRequired` on
operation `promote`, with the promote's index and `ref_id` set to that row. See
[WAC & Cost Basis](wac.md#promote-boundary).

---

## 🛣️ Legacy Live Promote Endpoint

`POST /transactions/transfers/promote` remains a separate live endpoint with a
different contract:

- request: `from_tx_id`, `to_tx_id`, `new_type`, and the optional
  `asset_id`, `quantity`, and `cost_basis_override` fields needed for
  `TRANSFER`; a `quantity`, or a `cost_basis_override` amount, whose exponent is
  outside ±100 is refused with a 422 before any work (R13-SEC7-3, see
  [Decimal Columns](../../architecture/database/index.md#decimal-columns));
- implementation: snapshot the two `DEPOSIT`/`WITHDRAWAL` rows, delete them,
  build two replacement create payloads with a shared `link_uuid`, and call
  `execute_batch()` with those deletes and creates. The payloads are raw dicts:
  a `TRANSFER`'s quantity and cost basis go in their short form, `str(v)`, with
  the signs from `copy_abs()` and `copy_negate()`. Neither a fixed-point
  expansion (`format(v, "f")`) nor a decimal context is involved (`abs()` of
  `1E+1000000` raises `decimal.Overflow`), so the batch refuses a value past its
  column's limits (R13-SEC7-3); and
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
| `wacFxUnavailable` | On operation `split`: the giving leg of a `TRANSFER` pair has no Auto cost, a conversion is missing ([The giving leg of a `TRANSFER`](#transfer-giving-leg)) |
| `autoCostUnreadable` | On operation `split`: the pool of the giving leg's Auto cost holds rows that cannot be read, `params` `{"count": N}` ([Unreadable pool](wac.md#unreadable-pool), W-B69) |
| `promoteRefNotFound` | A saved or same-batch promote reference cannot be resolved |
| `alreadyPaired` | A promote candidate already has a persistent partner |
| `noPromoteRule` | No metadata rule and constraint set matches the two rows |
| `eventTypeIncompatible` | A promoted row is linked to an asset event, which the target type refuses (step 3) |

The service does not roll the session back itself. `/transactions/validate`
always rolls back; `/transactions/commit` commits only when
`TXBatchResponse.committed` is true and rolls back otherwise. Access denial, a
value past its column's digits before the decimal point or a date out of range may
return before either mutation stage, and balance replay stops after its first
balance exception, so the overall pipeline is not an unconditional
collect-every-error pass.

---

## 🔗 Related

- 🏗️ **[Transaction Service](service.md)** — Batch order, context, and transaction ownership
- ⚖️ **[WAC & Cost Basis](wac.md)** — Create/update auto-WAC and promote's payload boundary
- 🔒 **[Balance Validation](balance_validation.md)** — Final post-flush balance replay
