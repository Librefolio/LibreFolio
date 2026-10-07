# 📝 Transaction Form Modal

The Transaction Form Modal (`TransactionFormModal.svelte`, in
`frontend/src/lib/components/transactions/modals/`) creates, edits or displays one transaction —
or one linked pair, shown as a single two-sided form. It adapts its fields to the selected
transaction type, validates against the backend while the user types, and either hands the result
back to the bulk workspace or commits it itself.

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

### Form State vs Staging State

It is important to keep the single-item form state apart from the workspace's staging state:

* **Form state** — `draft: FormDraft`, plus `dualTo: DualDraftTo` for a pair, is local Svelte 5
  `$state` inside the modal. It is rebuilt from `items` each time the modal opens (a new `openKey`
  forces a rebuild even when `open` never went back to `false`) and may be incomplete or invalid
  while the user types.
* **Staging state** — on **Apply**, `TransactionBulkModal` writes the pushed payload into the row's
  `DraftFields` (`applyFormPayload`) and keeps the row as a `PendingOp`. Read more in the
  **[Transaction Staging State](../../state/transaction-draft.md)** guide.

---

## 🗄️ State Schema

Which fields are shown, required or forbidden comes from the type rules that
`transactionTypeStore` loads from `GET /transactions/types` (`assetField`, `cashField`,
`quantityMode`, the quantity and cash sign rules, `eventLinkable`). Changing the type clears the
values the new type forbids.

### Common Fields

`FormDraft` (declared in `TransactionFormModal.svelte`):

| Field | Type | Description |
|-------|------|-------------|
| `type` | `TransactionTypeCode` | Core discriminator (`BUY`, `SELL`, `DIVIDEND`, …) |
| `broker_id` | `number` | `0` until chosen; pre-filled from `forcedBroker` (locked), `defaultBrokerId`, or the only broker the user can edit |
| `date` | `string` | `YYYY-MM-DD`; today on a blank form |
| `cash` | `{code, amount} \| null` | ISO 4217 code and decimal string, edited with `CompactCashCell` |
| `tags` | `string[]` | Free tags, with suggestions from `availableTags` |
| `description` | `string` | Free-text memo |
| `asset_event_id` | `number \| null` | Linked asset event, for event-linkable types |
| `cost_basis_override` | `{code, amount} \| null` | Manual cost basis (see [WAC State](#wac-state)) |
| `link_uuid` | `string \| null` | Pairing UUID; shown read-only when set |

### Asset Operations (BUY / SELL / TRANSFER)

Shown when the type's rules allow them:

| Field | Type | Description |
|-------|------|-------------|
| `asset_id` | `number \| null` | Selected asset (`AssetSelect`) |
| `quantity` | `string` | Exact decimal string, edited with `ExactQuantityInput` (built on `ExactDecimalInput`; at most 12 integer and 6 fraction digits); `'0'` when the type forbids a quantity |

---

## 💱 Paired layouts and FX conversion {: #fx-conversion }

When the type requires a link (`requiresPair`, the backend's `requires_link`), the form switches to
a two-sided layout chosen by the type's `pairFormLayout`: `transfer_asset` for `TRANSFER`,
`transfer_cash` for `CASH_TRANSFER` and `fx` for `FX_CONVERSION`. Each side, **From** and **To**,
has its own date. The **To** side lives in `dualTo`:

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
(`lib/utils/transactions/txPayloadHelpers.ts`), which returns two `FX_CONVERSION` items:

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
- **Quantity** — `ExactQuantityInput` checks the syntax, the 12 + 6 digit budget and the type's
  sign rule, and reports its validity (`onvaliditychange`); an invalid quantity disables the
  footer button.
- **Cash sign** — for a type whose cash rule is `negative` the user types a magnitude and the
  payload builder negates it (`applySignRules`). An amount that still breaks the rule
  (`computeSignHint`) disables the footer button.

Everything deeper — balances, pairing rules, access — belongs to the backend's
**[Balance Validation](../../../backend/transactions/balance_validation.md)**. While the form is
complete, every change schedules `POST /transactions/validate` (`createValidateScheduler`, debounced
500 ms by default). Inside the bulk workspace the request also carries the other staged rows
(`getBulkContext()`), so the balance walk sees the whole batch; for a single-row layout the banner
then keeps only this row's issues plus the global ones.

---

## 💰 WAC State

The cost-basis editor is `WacPreviewSection`
(`frontend/src/lib/components/transactions/wac/WacPreviewSection.svelte`). The form shows it where
a cost basis applies: on the receiving side of a paired `TRANSFER`, and on an `ADJUSTMENT` — with a
warning when a positive quantity has neither Auto mode nor a manual value, since the lot would be
created at zero cost. BUY and SELL do not show it.

- `costBasisMode` is `'auto'` (the backend computes the weighted average cost) or `'manual'` (the
  user's `cost_basis_override`). In Auto mode the item is sent with `cost_basis_mode: 'auto'` and,
  when the user picked a WAC currency, the hint `{code, amount: '0'}` as override.
- For validation, `upgradeAutoToDetail()` turns `'auto'` into `'auto-detail'`, so the response's
  `wac_results` carries the WAC with its qualifying transactions. Standalone, the form keeps that
  result in `formWacResult`; inside the bulk workspace it first reads the workspace's own result
  (`getWacResult(editingTempId)`).
- A `wacFxUnavailable` issue comes with a link that opens `FxSyncModal` on the missing pairs and
  dates (`handleSyncFx`).

---

## 🔗 Related

- 📝 **[Transaction Staging State](../../state/transaction-draft.md)** — Staging area and bulk operations
- 🧭 **[Import Wizard](import-wizard.md)** — Hands imported rows to the bulk workspace
- 🔒 **[Backend Balance Validation](../../../backend/transactions/balance_validation.md)** — Balance walk validation rules
- ⚖️ **[Backend WAC & Cost Basis](../../../backend/transactions/wac.md)** — Cost basis computation engine
- ✂️ **[Backend Split & Promote](../../../backend/transactions/split_promote.md)** — Linking and unlinking pairs
