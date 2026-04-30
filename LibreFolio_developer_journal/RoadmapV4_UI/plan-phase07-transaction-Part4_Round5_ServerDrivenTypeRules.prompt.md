# Plan — Phase 7 · Part 4 · Round 5 — Server-Driven Type Rules + Form Adaptation

**Date**: 2026-04-30
**Status**: ✅ COMPLETED
**Priority**: P2 (UX + architecture)
**Estimated effort**: ~7 h

**Parent**: [`plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md`](./plan-phase07-transaction-Part4_Round4_UnifiedBatchPipeline.prompt.md) §"Frontend Issues Found (2026-04-30)" — W28/W29/W30/W31

---

## 🎯 Obiettivo

1. **W28**: Balance errors attributed to the offending row in BulkModal
2. **W29**: Replace 3 hardcoded frontend files (`transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`) with a single `transactionTypeStore` driven by `GET /transactions/types`
3. **W29a**: Auto-sign negation — user enters positive numbers, frontend auto-negates for SELL qty / BUY cash
4. **W30**: Cash field UX — currency pre-select without amount + "↩ reset to asset currency"
5. **W31**: Form fields fully adapt to type rules (asset/cash/qty placeholders, event gating)

---

## ✅ Decisions Confirmed

| Topic | Decision |
|-------|----------|
| **Icon tx types** | Slug convention: backend `"buy"` → frontend `/icons/transactions/buy.png` |
| **Icon events** | Emoji for now, `emoji` field in backend `EventTypeMetadata` |
| **docUrl** | Backend field `doc_slug` → frontend resolves mkdocs path. `transactionTypes.ts` eliminated |
| **Asset types** | Same slug pattern, out of scope (noted for future consistency) |
| **Form adaptation** | All fields dynamically adapt to type, deriving rules from backend |
| **HTTP 200 for committed:false** | Confirmed correct by design (W27) |

---

## 📋 Steps

### Step R5-1 — W28: Balance error row attribution (~20 min)

**File**: `TransactionBulkModal.svelte`

Add helper `findRowForBalanceIssue(issue, drafts)`:
- `balanceAssetNegative` → last draft matching `broker_id === params.brokerId && asset_id === params.assetId`
- `balanceCashNegative` → last draft matching `broker_id === params.brokerId && cash?.code === params.currency`
- Found → return row index. Not found → return -1.

Update both banner templates (red commit + yellow validate): for balance issues with `index < 0`, call the helper. If resolved index ≥ 0 → show "Riga N:" clickable + scroll. Otherwise → no prefix (current fallback).

---

### Step R5-2 — Backend: update `TXTypeMetadata` schema (~45 min)

**File**: `backend/app/schemas/transactions.py`

Changes to `TXTypeMetadata`:
- `icon` (emoji) → `icon_slug: str` (e.g. `"buy"`, `"sell"`, `"fx-conversion"`)
- Add `doc_slug: Optional[str]` (e.g. `"buy-sell"`, `"deposit-withdrawal"`, `null` if no dedicated page)
- Update all 11 entries in `TX_TYPE_METADATA`

Slug → PNG mapping:

| Type | `icon_slug` | `doc_slug` |
|------|-------------|------------|
| BUY | `buy` | `buy-sell` |
| SELL | `sell` | `buy-sell` |
| DIVIDEND | `dividend` | `dividend` |
| INTEREST | `interest` | `interest` |
| DEPOSIT | `deposit` | `deposit-withdrawal` |
| WITHDRAWAL | `withdrawal` | `deposit-withdrawal` |
| FEE | `fee` | `fee` |
| TAX | `tax` | `fee` |
| TRANSFER | `transfer` | `transfer` |
| FX_CONVERSION | `fx-conversion` | `null` |
| ADJUSTMENT | `adjustment` | `null` |

---

### Step R5-3 — Backend: wrap response + event types (~30 min)

**Files**: `backend/app/schemas/transactions.py`, `backend/app/api/v1/transactions.py`

New schemas:
```python
class EventTypeMetadata(BaseModel):
    code: str
    name: str
    emoji: str
    compatible_tx_types: List[str]

class TXTypesResponse(BaseModel):
    transaction_types: List[TXTypeMetadata]
    event_types: List[EventTypeMetadata]
```

Endpoint `GET /types` returns `TXTypesResponse` instead of `List[TXTypeMetadata]`.

Event types metadata:

| Code | Name | Emoji | Compatible TX types |
|------|------|-------|---------------------|
| DIVIDEND | Dividend | 💰 | DIVIDEND |
| INTEREST | Interest | 📈 | INTEREST |
| SPLIT | Split | ✂️ | ADJUSTMENT |
| PRICE_ADJUSTMENT | Price Adjustment | 📊 | ADJUSTMENT |
| MATURITY_SETTLEMENT | Maturity Settlement | 🏁 | INTEREST |

---

### Step R5-4 — Frontend: `transactionTypeStore` (~1.5 h)

**New file**: `frontend/src/lib/stores/transactionTypeStore.ts`

1. Lazy fetch `GET /transactions/types`, cache in reactive store
2. Expose (replaces 3 deleted files):
   - `ensureTypesLoaded()` — call at modal open
   - `getTypeRule(code)` → `TypeRule` derived from server data
   - `getTypeIconUrl(code)` → `/icons/transactions/${icon_slug}.png`
   - `getTypeDocUrl(code, lang)` → resolve `doc_slug` to full mkdocs path
   - `getEventTypeEmoji(code)` → from `EventTypeMetadata.emoji`
   - `getStandaloneTypes()` — types where `requiresPair === false`
   - `getPairTypes()` — types where `requiresPair === true`
   - `getEventLinkableTypes()` — types where `eventLinkable === true`
   - `isDraftReadyForValidation(draft)` — uses fetched rules
   - `buildTransactionTypeOptions(t)` — with icon URLs from slugs

3. ~~Mapping from server fields to `TypeRule`~~ **SUPERSEDED** by lowercase pass-through (R5-9).

**R5-9 refactor**: Backend now sends all values lowercase and adds `cash_mode`/`quantity_mode` (same `FieldMode` as `asset_mode`). Frontend uses server data **as-is** — zero mapping functions.

| Server field (backend) | `TypeRule` field (frontend) | Notes |
|------------------------|-----------------------------|-------|
| `asset_mode: "required\|optional\|forbidden"` | `assetField` | direct, lowercase |
| `cash_mode: "required\|optional\|forbidden"` | `cashField` | direct, replaces old `requires_cash` + `allowed_cash_sign` combo |
| `quantity_mode: "required\|optional\|forbidden"` | `quantityMode` | direct, new field |
| `quantity_sign: "positive\|negative\|zero\|nonzero\|free"` | `quantityRule` | direct, lowercase |
| `cash_sign: "positive\|negative\|zero\|nonzero\|free"` | `cashSign` | direct, lowercase |
| `requires_link` | `requiresPair` | direct |
| `event_compatible` | `eventLinkable` | direct |

**Removed from backend**: `requires_cash` (redundant with `cash_mode`), `allowed_quantity_sign`/`allowed_cash_sign` (renamed to `quantity_sign`/`cash_sign`), `AssetMode` (replaced by `FieldMode`).

**Frontend types derived from Zod client**: `FieldMode` and `SignRule` are inferred from `schemas.TXTypeMetadata` (generated by `openapi-zod-client`), not manually declared.

**Delete**: `transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`

---

### Step R5-5 — Auto-sign negation in modals (~1.5 h)

**Files**: `TransactionFormModal.svelte`, `TransactionBulkModal.svelte`, `CompactCashCell.svelte`

**Principle**: When `allowed_quantity_sign === "-"` or `allowed_cash_sign === "-"`:

1. User enters **positive** numbers (natural UX)
2. `collectCreate()` / `collectUpdate()` auto-negates before backend send
3. On **edit** (incoming negative values): `Math.abs()` for display, re-negate on collect
4. Visual hint: label suffix "(−)" on the input label
5. `signHint` in `CompactCashCell`: when auto-sign is active, flip the hint — green when user enters positive (since it will be negated)

For `"+/-"`: no auto-negation, user enters sign explicitly.
For `"0"`: quantity hidden/forced to 0 (unchanged behavior).

**Error message display**: When the backend returns e.g. "SELL requires quantity < 0", the user entered a positive number. The existing i18n keys (`qtyPositive`, `qtyNegative`) already describe the backend's perspective. Since auto-sign transparently handles the negation, the resolved message "La quantità deve essere maggiore di 0" is correct from the user's viewpoint. No i18n key changes needed.

---

### Step R5-6 — Form fields fully driven by type rules (~1 h)

**File**: `TransactionFormModal.svelte`

Every field adapts using the derived `rule` (from store):

| Field | Rule | Current State | Change |
|-------|------|--------------|--------|
| **Asset** | `assetField: 'forbidden'` | Hidden ✅ | + greyed-out i18n placeholder: `transactions.form.assetNotApplicable` |
| **Asset** | `assetField: 'optional'` | Shown, no hint | + italic grey "(opzionale)" hint: `transactions.form.assetOptional` |
| **Asset** | `assetField: 'required'` | Shown with `*` ✅ | No change |
| **Cash** | `cashField: 'forbidden'` | Greyed box, English text | Fix: use i18n `transactions.form.cashNotApplicable` |
| **Cash** | `cashField: 'optional'` | (not used yet) | Show without `*`, same component |
| **Cash** | `cashField: 'required'` | Shown with `*` ✅ | No change |
| **Quantity** | `quantityRule: 'zero'` | Hidden, cash full-width ✅ | Clean up hint text with i18n |
| **Quantity** | `quantityRule: 'positive'` | Shown ✅ | Label: `transactions.form.qtySignPositive` → "Quantity (+)" |
| **Quantity** | `quantityRule: 'negative'` | Shown ✅ | Label: `transactions.form.qtySignNegative` → "Quantity (−)" (user enters positive, auto-negated) |
| **Quantity** | `quantityRule: 'nonzero'` | Shown ✅ | Label: `transactions.form.qtySignFree` → "Quantity (±)" |
| **Event link** | `eventLinkable: true` | Gated in Advanced ✅ | Derives from server `event_compatible` |
| **Event link** | `eventLinkable: false` | Hidden ✅ | No change |
| **Pair/link** | `requiresPair: true` | Redirects to wizard ✅ | No change |

New i18n keys (4 locales):
- `transactions.form.assetOptional`: "(optional)" / "(opzionale)" / "(optionnel)" / "(opcional)"
- `transactions.form.assetNotApplicable`: "— {type} does not use assets" / "— {type} non richiede un asset" / …
- `transactions.form.cashNotApplicable`: "— {type} does not use cash" / "— {type} non richiede un importo" / …
- `transactions.form.qtySignPositive`: "Quantity (+)" / "Quantità (+)" / …
- `transactions.form.qtySignNegative`: "Quantity (−)" / "Quantità (−)" / …
- `transactions.form.qtySignFree`: "Quantity (±)" / "Quantità (±)" / …

---

### Step R5-7 — W30: Cash field UX fixes (~30 min)

**Files**: `CompactCashCell.svelte`, `TransactionFormModal.svelte`

**7a** — Currency pre-select without amount:
Modify `CompactCashCell.emit()` — when `amountStr` is empty but `code` is set, emit `{amount: '', code}` instead of `null`. This preserves the selected currency while the user hasn't typed the amount yet. Backend validation catches empty-amount-with-currency if submitted.

**7b** — "Reset to asset currency" link:
In `TransactionFormModal`, when `draft.asset_id != null` and asset's native currency ≠ `draft.cash?.code`, show a small clickable hint below the cash field:

```
↩ USD
```

Clicking sets `draft.cash.code = assetCurrency`. Only shown when there's a mismatch.

---

### Step R5-8 — Cleanup + api sync + tests (~30 min)

- `./dev.py api sync` (response shape changed: `List[TXTypeMetadata]` → `TXTypesResponse`)
- Delete `transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`
- Update all imports in consumers:
  - `TransactionFormModal.svelte`
  - `TransactionBulkModal.svelte`
  - `PromotePairWizardModal.svelte`
  - `TransactionsTable.svelte`
  - `TransactionTypeSearchSelect.svelte`
  - `TransactionTypeBadge.svelte` (if exists)
  - `AssetDataEditorSection.svelte`
  - `CashTransactionModal.svelte`
- Backend tests for updated `/types` endpoint (new response shape)
- i18n keys added (4 locales × 6 new keys)
- Manual E2E: change type in FormModal → verify all fields adapt correctly

---

## ✅ Checklist

- [x] R5-1: Balance error row attribution in BulkModal
- [x] R5-2: Backend `icon_slug` + `doc_slug` in `TXTypeMetadata`
- [x] R5-3: Backend `TXTypesResponse` + `EventTypeMetadata` + 5 event types
- [x] R5-4: Frontend `transactionTypeStore` (lazy fetch + cache)
- [x] R5-4b: Delete `transactionTypeRules.ts`, `transactionTypes.ts`, `eventTypes.ts`
- [x] R5-5: Auto-sign negation (positive input → auto-negate on collect)
- [x] R5-6: Form fields fully driven by rules (placeholders, labels, gating)
- [x] R5-6b: i18n keys for field labels and placeholders (4 locales)
- [x] R5-7a: Cash currency pre-select without amount
- [x] R5-7b: "↩ Reset to asset currency" link
- [x] R5-8: `./dev.py api sync` + import migration + tests
