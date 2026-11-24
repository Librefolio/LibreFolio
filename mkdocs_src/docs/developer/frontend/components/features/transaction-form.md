# 📝 Transaction Form Modal

The Transaction Form Modal (`TransactionFormModal.svelte`, in
`frontend/src/lib/features/transactions/form/`) creates, edits or displays one transaction —
or one linked pair, shown as a single two-sided form. It adapts its fields to the selected
transaction type, validates against the backend while the user types, and either hands the result
back to the bulk workspace or commits it itself.

The modal owns the whole state — the draft, the validation, the handlers — and renders its
sections through six components in `frontend/src/lib/features/transactions/form/`, which read
that state as props, write back only what they bind, and call the modal's handlers:

| Component | Section |
|---|---|
| `TxFormBanners` | The inline banners: a failed commit, the validation result and its issues, the partner loading |
| `TxFormPairSection` | The two-sided form of a pair (FX, transfer of an asset, transfer of cash): the shared fields, then **From** and **To** |
| `TxFormSingleSection` | The one-row form: date, type, quantity and cash, asset, broker, and the cost basis of an adjustment |
| `TxFormChargesSection` | The linked charges of a parent (a BUY, SELL, DIVIDEND, INTEREST, DEPOSIT or WITHDRAWAL): its FEE and TAX rows, «Open» on each, and the read-only total, «Total charged» or «Net received», one amount per currency (see [Linked charges](#linked-charges)) |
| `TxFormParentSection` | «Linked to», in the form of a FEE or a TAX: the transaction it belongs to, with «Open» |
| `TxFormOptionalSection` | The optional fields: linked event, tags, description, link id, pair partner |

The header, the footer, the read-only footer and the stacked modals stay in the modal.

---

## 🏗️ Architecture

The form works on a local copy of one row; nothing it holds is shared until the user presses the
footer button.

| `mode` | Footer button | Behaviour |
|---|---|---|
| `create` | **Apply** / **Save** | Blank form, or pre-filled from `items[0]` (e.g. a staged row) |
| `edit` | **Apply** / **Save** | Existing row; type and broker are locked unless `unlockImmutable` (then the type list is limited to the original type's swap group) |
| `view` | — | Read-only; the pencil switches to edit through `onSwitchToEdit`, shown only when `canEdit` |

`commitOnSave` decides where the result goes:

- **`commitOnSave={false}` — Apply.** `onPushDraft(payload)` hands a create-shaped payload back
  to the caller, and the modal closes. `TransactionBulkModal` mounts the form this way (with
  `unlockImmutable` in edit mode), so every row created or edited in the workspace goes through
  it.
- **`commitOnSave={true}` (default) — Save.** The form posts to `POST /transactions/commit` itself
  and reports `onCommitted`. The Transactions, broker-detail and dashboard pages mount the form in
  `view` mode only; on the Transactions page, the pencil reopens the row in the bulk workspace.

Closing the form with unsaved changes asks for confirmation (*Discard Changes?*).

### 🔀 Form State vs Staging State

It is important to keep the single-item form state apart from the workspace's staging state:

* **Form state** — `draft: FormDraft`, plus `dualTo: DualDraftTo` for a pair, is local Svelte 5
  `$state` inside the modal. It is rebuilt from `items` each time the modal opens (a new `openKey`
  forces a rebuild even when `open` never went back to `false`) and may be incomplete or invalid
  while the user types.
* **Staging state** — on **Apply**, `TransactionBulkModal` writes the pushed payload into the row's
  `DraftFields` (`applyFormPayload`) and keeps the row as a `PendingOp`. The payload is signed, as
  a create is sent, while the workspace holds a value whose type rule demands a negative (a
  `SELL`'s quantity, a `BUY`'s cash) as its magnitude: `applyFormPayload` ends by bringing the
  quantity and the cash back to that convention (`magnitudeForRule`), so an untouched **Apply**
  leaves them as the row held them (W-B65). Read more in the
  **[Transaction Staging State](../../state/transaction-draft.md)** guide.

---

## 🗄️ State Schema

Which fields are shown, required or forbidden comes from the type rules that
`transactionTypeStore` loads from `GET /transactions/types` (`assetField`, `cashField`,
`quantityMode`, the quantity and cash sign rules, `eventLinkable`). Changing the type clears the
values the new type forbids.

### 📋 Common Fields

`FormDraft` (declared, with `DualDraftTo`, in `features/transactions/form/txFormTypes.ts`):

| Field | Type | Description |
|-------|------|-------------|
| `type` | `TransactionTypeCode` | Core discriminator (`BUY`, `SELL`, `DIVIDEND`, …) |
| `broker_id` | `number` | `0` until chosen; pre-filled from `forcedBroker` (locked), `defaultBrokerId`, or the only broker the user can edit. **Create new** in the broker select opens a stacked `BrokerModal` (`zIndex + 10`) |
| `date` | `string` | `YYYY-MM-DD`; today on a blank form |
| `cash` | `{code, amount} \| null` | ISO 4217 code and decimal string, edited with `CompactCashCell` |
| `tags` | `string[]` | Free tags, with suggestions from `availableTags` |
| `description` | `string` | Free-text memo |
| `asset_event_id` | `number \| null` | Linked asset event (**Linked Event**, `AssetEventPicker`), for the event-linkable types (`DIVIDEND`, `INTEREST`, `ADJUSTMENT`); the picker shows once an asset and a date are set (`canShowAssetEvent`). **+ New event** in the picker (not in `view` mode) opens a stacked `EventCreateMiniModal` (`zIndex + 10`), which sends the new event with `mode: "create"`. Its amount is handled as a decimal string: the suggestion (the form's cash) is prefilled whole (`0.2345` stays `0.2345`), blur pads it to two decimals at least and keeps the typed ones, the event is sent with that string, and past the 6 decimals an event value keeps (trailing zeros not counted, as the backend counts them) the field is `aria-invalid`, `event-create-amount-digits-error` (`data-max="6"`, `common.decimalPlacesExceeded`) shows under it and the submit button (`event-create-submit`) is disabled. On `EVENT_EXISTS` it shows `EventExistsPanel`: **Use this** (writes nothing), **Edit this** for manual events only (the form then saves that event by its `id`, `mode: "upsert"`), **Cancel**. The field then holds the id the response names (`results[0].event_ids[0]`), or the id of the event chosen with **Use this**. Any refusal other than `EVENT_EXISTS` shows as one sentence in the modal's error banner (`eventSaveErrorMessage()`, `lib/features/transactions/events/eventSaveError.ts`); a 400 `EVENT_TOO_MANY_DIGITS` has its own, `events.saveError.tooManyDigits`, which names the first event at fault (date and type), how many more there are, and the three maxima of its `params`: decimal places, significant digits and digits before the decimal point (`max_decimal_places`, `max_significant_digits`, `max_integer_digits`) |
| `cost_basis_override` | `{code, amount} \| null` | Manual cost basis (see [WAC State](#wac-state)) |
| `link_uuid` | `string \| null` | Pairing UUID; shown read-only when set |

### 📦 Asset Operations (BUY / SELL / TRANSFER)

Shown when the type's rules allow them:

| Field | Type | Description |
|-------|------|-------------|
| `asset_id` | `number \| null` | Selected asset (`TxFormAssetField`, the shared `AssetPickerPanel` in single mode); **New asset**, at the foot of the list while the row can be edited, opens a stacked `AssetModal` |
| `quantity` | `string` | Exact decimal string, edited with `ExactQuantityInput` (built on `ExactDecimalInput`; at most 15 integer and 10 fraction digits); `'0'` when the type forbids a quantity |

---

## 💱 Paired layouts and FX conversion {: #fx-conversion }

When the type requires a link (`requiresPair`, the backend's `requires_link`), the form switches to
a two-sided layout chosen by the type's `pairFormLayout`: `transfer_asset` for `TRANSFER`,
`transfer_cash` for `CASH_TRANSFER` and `fx` for `FX_CONVERSION`. Each side, **From** and **To**,
has its own date. **Swap sides** (`swapDualSides()`) exchanges the two dates and, for the transfer
layouts, the two brokers; for FX it exchanges the amounts instead (see below). The **To** side
lives in `dualTo`:

```typescript
interface DualDraftTo {
    broker_id: number;                                    // transfers: the receiving broker
    cash: {code: string; amount: string} | null;          // fx: the currency bought
    date: string;                                         // this leg's own date
    quantity?: string;                                    // transfer_asset: receiver quantity
    cost_basis_override?: {code: string; amount: string} | null; // transfer_asset: receiver cost basis
}
```

### 🧾 The two FX legs {: #fx-legs }

An `FX_CONVERSION` exchanges one currency for another inside **one broker**: one leg spends a
currency, the other receives a different one.

| Part | Fields | Notes |
|---|---|---|
| Shared | `type`, `broker_id` | One broker field for both legs. Outside `view` mode, `effectiveDualTo` always puts the To leg on the source broker, as the type's `pair_field_constraints` ask (`broker_id` equal, `cash_currency` different) |
| From | `date`, `cash` | The currency sold and its amount (`tx-form-cash-from`) |
| To | `dualTo.date`, `dualTo.cash` | The currency bought and its amount (`tx-form-cash-to`); its date may differ from the From date |
| Shared | `tags`, `description` | Copied onto both legs |

Both amounts are typed as magnitudes; the signs are applied when the payload is built. The swap
arrow (`tx-form-dual-swap`) exchanges the amounts and the dates of the two legs and keeps the
broker. Once both amounts are set in two different currencies, a badge (`tx-form-fx-info`) shows
the implied rate (To ÷ From) and, in its tooltip, the market rate on the From date
(`lookupFxRate` from `fxStoreRegistry`); ⚠️ marks a market rate carried over from an earlier day.

### ✅ Pair validation {: #pair-validation }

- **Different currencies** — `dualValidationError` reports *Currencies must be different*
  (`transactions.form.sameCurrencyError`) and disables the footer button. Transfers check the
  reverse: their two brokers must differ (`sameBrokerError`).
- **Completeness** — `isFormComplete` needs the From fields the type requires, a destination broker
  and a destination date and, for FX, a currency and a finite, non-zero amount on both legs. It
  gates the automatic validation, **⚡ Validate now** and, in the bulk workspace, **Apply**.
- **Sign** — the paired cash editors use the `positive` rule: a negative amount on either leg
  (`cashSignResult`, `cashToSignViolation`) disables the footer button.
- **Server** — both legs are validated together in one `POST /transactions/validate`; the issues
  the two halves share are shown once (`deduplicateIssues`, by issue code).

### 📤 How the pair is submitted {: #pair-submission }

`collectDualCreates()` calls `buildDualCreatePayloads('fx', …)`
(`lib/features/transactions/txPayloadHelpers.ts`), which returns two `FX_CONVERSION` items:

| Field | From item | To item |
|---|---|---|
| `broker_id` | source broker | source broker |
| `date` | From date | To date (the From date when empty) |
| `quantity` | `'0'` | `'0'` |
| `cash` | sold currency, **negative** amount | bought currency, **positive** amount |
| `link_uuid` | shared | shared |
| `tags`, `description` | when set | same as From |

The signs are applied on the decimal strings (`applySign`), never through a float. The two items
share one `link_uuid`: `draft.link_uuid` when it is set, otherwise a fresh `generateUUID()`.

- **Apply** (bulk workspace) — the pushed payload carries `_dual: true` and `_items: [from, to]`
  (with `_partnerBrokerId`, `_partnerCash`, `_partnerDate`). `TransactionBulkModal` turns it into
  a visible row plus a hidden partner op that points to it through `pairedWith`; both keep the
  shared `link_uuid`.
- **Save** (standalone) — a new pair is sent as `{creates: [from, to]}`. An edited pair, once its
  partner is loaded, is sent as `{updates: …}`: `collectDualUpdates()` matches each leg to its
  original by the sign of its cash and keeps only the legs that changed (`diffDualItem`).

Opening an existing pair loads the partner (passed in `items[1]`, or read with
`GET /transactions?ids=…`), puts the spending leg on **From**, and merges diverging descriptions
and tags of the two legs.

---

## ✅ Client-Side Validation

The form checks locally only what it can know without the ledger:

- **Required fields** — `isDraftReadyForValidation()` (`transactionTypeStore`) needs a broker, the
  asset when the type requires one, a non-zero cash amount when cash is required and a non-zero
  quantity unless the type forbids it; the form also needs a date, and for a pair the destination
  side ([Pair validation](#pair-validation)). Until then there is no automatic validation and
  **⚡ Validate now** stays disabled.
- **Quantity** — `ExactQuantityInput` checks the syntax, the 15 + 10 digit budget (the 15 integer
  digits, decision N63, and the 10 decimals the backend keeps for a quantity; zeros that do not
  change the value are not counted: `0.10000000000` has one decimal, `007` one integer digit) and
  the type's sign rule, and reports its validity (`onvaliditychange`); an invalid quantity
  disables the footer button. A fraction past those 10 decimals is also said under the field
  (`tx-form-quantity-digits-error`, `common.decimalPlacesExceeded`), and the value stays as typed.
- **Cash sign** — for a type whose cash rule is `negative` the user types a magnitude and the
  payload builder negates it (`applySignRules`). An amount that still breaks the rule
  (`computeSignHint`) disables the footer button.
- **Hints** — the single-layout cash editor always carries *💡 Total amount (not per share)*
  (`transactions.form.cashLabelTotal`). The quantity and cash editors also show the hint of the
  type's sign rule (`signHintText()` → `signHintKey()` in `lib/features/transactions/form/txFormFields.ts`:
  *must be > 0*, *enter positive — auto-negated on save*, *must be 0*, *must be ≠ 0*). Negative
  quantity rules are auto-flipped like cash (`effectiveQtyRule`), so a `SELL` quantity is typed as
  a positive number.

Everything deeper — balances, pairing rules, access — belongs to the backend's
**[Balance Validation](../../../backend/transactions/balance_validation.md)**. While the form is
complete, every change schedules `POST /transactions/validate` (`createValidateScheduler`, debounced
500 ms by default). Inside the bulk workspace the request also carries the other staged rows
(`getBulkContext()`), so the balance walk sees the whole batch; for a single-row layout the banner
then keeps only this row's issues plus the global ones.

---

## 💰 WAC State

The cost-basis editor is `WacPreviewSection`
(`frontend/src/lib/features/transactions/wac/WacPreviewSection.svelte`). The form shows it where
a cost basis applies: on the receiving side of a paired `TRANSFER`, and on an `ADJUSTMENT` with a
positive quantity (`showCostBasisField` in `TransactionFormModal.svelte`). An `ADJUSTMENT` taking
units out has no value (N78-1), so the form shows no cost basis for it, and the bulk editor gives
such a saved row no `cbMode` (`TransactionBulkModal.svelte`). BUY and SELL do not
show it.

- `costBasisMode` is `'auto'` (the backend computes the weighted average cost) or `'manual'` (the
  user's `cost_basis_override`). In Auto mode the item is sent with `cost_basis_mode: 'auto'` and,
  once `wacCurrencyHint` holds a currency (the user's pick, the first WAC result's, or the one in
  the row's sentinel), the hint `{code, amount: '0'}` as override.
- In Auto mode the backend writes the WAC into `cost_basis_override`
  (`TransactionService._compute_wac_for_auto_items()` → `compute_wac_iterative()`): for the
  receiving side of a `TRANSFER` pair, the WAC of the partner's broker as of the partner's date,
  without the partner's outgoing leg; otherwise the WAC of the row's own broker as of the row's
  date, without the row. The batch's other Auto rows not yet costed are left out too, and the rows
  are costed in date order (W-B67; see
  [Inline Batch Auto Modes](../../../backend/transactions/wac.md#inline-batch-auto-modes)). When that broker has no other row of
  the asset up to that date — the transfer's own outgoing leg aside — the WAC is `0`, and the row
  is saved with a zero cost basis. That is by design (developer decision of 2026-10-09): the user
  corrects that transaction later if needed. Auto rows skip the required-cost-basis check
  (`_auto_mode_indices()`); split-linked adjustments and missing FX are covered in
  [WAC & Cost Basis](../../../backend/transactions/wac.md).
- In Manual mode, a `TRANSFER` or `ADJUSTMENT` with a positive quantity and no
  `cost_basis_override` gets a `costBasisRequired` issue (`validate_cost_basis()`) when it is
  created, and when an update changes its type, quantity, cost basis or its asset event link.
  `TransactionService._requires_cost_basis()` reads which rows need one from `TX_TYPE_METADATA`,
  the table `GET /transactions/types` serves (`cost_basis_required()` in
  `backend/app/schemas/transactions/type_metadata.py`). Like any issue, it makes the batch
  `committed=False`, and `POST /transactions/commit` rolls the whole batch back: the row is not
  saved. A free acquisition is entered as `0`.
- Known mismatch: for an `ADJUSTMENT` with a positive quantity, not in Auto mode and with an empty
  manual field, the form shows `transactions.costBasisOverride.warningAdjustment`
  (`tx-form-cost-basis-warning`), which says the transaction cannot be saved without a cost basis.
  That holds for a create, not for an update that leaves the type, quantity, cost basis and asset
  event link alone: editing only the notes, tags or date of an older row stored without a cost
  basis gets no `costBasisRequired`, and the row stays without one.
- For validation, `upgradeAutoToDetail()` turns `'auto'` into `'auto-detail'`, so the response's
  `wac_results` carries the WAC with its qualifying transactions. Standalone, the form keeps that
  result in `formWacResult`; inside the bulk workspace it first reads the workspace's own result
  (`getWacResult(editingTempId)`).
- A `wacFxUnavailable` issue comes with a link that opens `FxSyncModal` on the missing pairs and
  dates (`handleSyncFx`).

---

## 💸 Linked charges {: #linked-charges }

A FEE or a TAX can point at the transaction it belongs to (project 66; the backend side is in
[Transaction Service, «Linked Charges»](../../../backend/transactions/service.md#linked-charges)).

- **The model** is `form/txCharges.ts`, pure: a `ChargeDraft` per row, with a state `linked`, `unlink` or `delete`; the
  rows from the API (`GET /transactions?parent_ids=…`, only the rows whose `parent_transaction_id` is the parent), a new
  row, the total (`tradeTotalWithCharges` of `form/txTradeAmount.ts`, exact, per currency, never across currencies), the
  rows without an amount, and `buildChargesBatch`, the creates, updates and deletes the batch sends.
- **Where it can be edited.** In the app the form never saves by itself: the page opens it read-only, and an edit goes
  through the bulk workspace, where the form hands its rows back. The section is therefore read-only unless the host
  passes `allowChargeEdits`: then it adds, changes, unlinks and deletes rows, and «Apply» hands every draft over as
  `_charges` (and a charge's own form hands `_parent_unlink`). The bulk workspace turns it on once it saves them.
- **Linking what already exists** (also behind `allowChargeEdits`) reuses `bulk/TransactionPickerModal.svelte` with the
  rows the form fetched (`rows`, plus `title`, `filterLabel`, `addLabel`, `maxSelect` and `zIndex` above the form):
    - «Link an existing charge…», in the parent's section: the FEE and TAX rows of the same broker with no parent
      (`GET /transactions?without_parent=true&broker_id=…`), on the parent's asset (`null` with `null`) and not already in
      the section. Each picked row becomes a `ChargeDraft` with `linkNew` (`chargeFromPicked`), and the batch always
      sends its link. Unlinking or trashing a picked row only takes it back out of the section: it was never linked,
      and the picker offers it again. Inside the Bulk (66 TL-2) the host's prop `bulkCandidates('charges', probe)` adds
      the Bulk's own rows, read on its state by the selection's «Link» rule (`bulkChargeCandidates` in
      `bulk/bulkCharges.ts`, the probe being the form's broker, asset and type): a row in both sources is the Bulk's, and
      `exclude` drops the saved rows the Bulk marked «del» or linked elsewhere. A new row carries a negative id, its key
      `_bulkKey` (`op-<tempId>`) and its name `_rowRef` (the picker's ID cell shows it); `chargeFromPicked` turns it into
      the draft of that very row, which `applyChargeDrafts` links as `linkInBulk` does. The parent picker still reads the
      database only.
    - `groupSync` (66 TL-3b): the Bulk sets it on the Form of a row of an all-new group (`newGroupOf`), whose broker and
      asset move together; `TxFormSingleSection` shows a line under the broker (`tx-form-group-sync-hint`), never in a
      read-only Form.
    - «Link to a transaction…», in the form of a FEE or TAX with no parent: the rows of the same broker whose type has
      `charge_role` `parent`, on the charge's asset and not paired. One row; it shows as pending, with «Undo», and «Apply»
      hands `_parent_link`.
    - A failed fetch shows a toast and opens no picker. Changing the form's broker or asset drops what was picked.
- **«Open»** (`onOpenTransaction`): the host shows the other transaction in the same modal, in the same mode, and passes
  `highlightTxId` so the charge the user came from is highlighted in its parent's section. With unsaved changes the
  existing discard confirmation comes first. The transactions page and the portfolio views wire it in read-only; the
  bulk workspace wires it too, and brings the target into the batch as a row ([«Open» in the
  workspace](../../state/transaction-draft.md#workspace-intent)).
- **The unsaved-changes baseline** (`baselineKey()`) includes the charges; a charge row without an amount is a local
  error that blocks «Apply».

---

## 🔗 Related

- 📝 **[Transaction Staging State](../../state/transaction-draft.md)** — Staging area and bulk operations
- 🧭 **[Import Wizard](import-wizard.md)** — Hands imported rows to the bulk workspace
- 🔒 **[Backend Balance Validation](../../../backend/transactions/balance_validation.md)** — Balance walk validation rules
- ⚖️ **[Backend WAC & Cost Basis](../../../backend/transactions/wac.md)** — Cost basis computation engine
- ✂️ **[Backend Split & Promote](../../../backend/transactions/split_promote.md)** — Linking and unlinking pairs
