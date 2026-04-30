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

---

## 🔮 Next: Round 6 — Dark Mode Vibrancy + Dual-Transaction Form

### R6-A: Dark Mode Color Fix (DONE)

**Problem**: Row backgrounds in both light/dark mode were barely distinguishable between brokers.

**Root causes**:
1. **CSS class mismatch**: styles targeted `.tx-cash-amount/.tx-cash-symbol/.tx-cash-code` but `formatCurrencyAmountHtml` emits `.currency-amount/.currency-symbol/.currency-code` → dark overrides never applied.
2. **Pastel row tints**: `--broker-bg` was `hsl(hue, 35-55%, 92%)` — almost white. Mixed at any % with white/dark, the tint was invisible.
3. **Tags too desaturated**: `getIndexColor` dark mode saturation was `sat - 10%` at lightness 75%.

**Fix applied**:
- Fixed CSS class names → `currency-amount`, `currency-symbol`, `currency-code`
- Added `vivid: hsl(hue, 100%, 50%)` to `ColorSet` → `--broker-vivid` CSS variable
- Row tint now uses `color-mix(in srgb, var(--broker-vivid) N%, base)`:
  - Light: 12% vivid + white (hover 18%)
  - Dark: 15% vivid + #0f0f18 (hover 22%)
- Boosted `getIndexColor` dark mode: `sat + 10%` (was `sat - 10%`), text lightness 82% (was 75%), bg lightness 25% (was 20%)
- TransactionTypeSearchSelect: translated label priority over raw code on mobile (`hidden sm:inline` on code span)
- i18n FX_CONVERSION: EN="Currency Exchange", IT="Cambio Valuta", FR="Change de Devises", ES="Cambio de Divisas"
- Numbers (qty/cash) kept neutral grey — sign is context-dependent, not inherently good/bad.

---

### R6-B: Dual-Transaction Form — ✅ DECISION: Option A

**Decision**: `pair_form_layout` explicit in backend metadata.

```python
pair_form_layout: Optional[Literal["fx", "transfer_asset", "transfer_cash"]] = None
```

**Behaviour rules**:
- **Create**: Both sides created in one form submit → 2 linked rows.
- **Edit**: Selecting one side in table → form loads BOTH (via `related_transaction_id`), edits both.
- **Promote (link)**: Select exactly 2 rows in main table → if compatible, show 🔗 bulk action → confirmation banner → backend links them.
- **Unlink (split)**: Per-row action with 🔗‍💥 (broken chain icon) → confirmation banner → backend unlinks.

---

#### R6-B.1 — TransactionFormModal: FX_CONVERSION (pair_form_layout = "fx")

**Desktop layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  💱 Cambio Valuta                                          [X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Data:  [  2026-04-30  📅 ]        Broker: [ Interactive ▼ ]   │
│                                                                 │
│  ┌─── Da ──────────────────┐       ┌─── A ───────────────────┐ │
│  │ [ EUR 🇪🇺  ▼ ] [1.000,00]│  ──→  │ [ USD 🇺🇸  ▼ ] [1.090,00]│ │
│  └─────────────────────────┘       └─────────────────────────┘ │
│                                                                 │
│  ▸ Avanzate                                                     │
│    Tag: [________]   Note: [____________________]               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Annulla]  [💾 Salva]              │
└─────────────────────────────────────────────────────────────────┘
```

**Mobile layout** (stacked, currency+amount always on same line):
```
┌──────────────────────────────┐
│  💱 Cambio Valuta        [X] │
├──────────────────────────────┤
│                               │
│  Data:   [  2026-04-30  📅 ] │
│  Broker: [ Interactive ▼ ]   │
│                               │
│  ── Da ───────────────────── │
│  [ EUR 🇪🇺  ▼ ] [ 1.000,00 ] │
│                               │
│             ↓                 │
│                               │
│  ── A ────────────────────── │
│  [ USD 🇺🇸  ▼ ] [ 1.090,00 ] │
│                               │
│  ▸ Avanzate                   │
│                               │
├───────────────────────────────┤
│        [Annulla]  [💾 Salva]  │
└───────────────────────────────┘
```

**Constraints**: Valuta Da ≠ Valuta A (validation error if same). Broker shared (one selector).

---

#### R6-B.2 — TransactionFormModal: TRANSFER (pair_form_layout = "transfer_asset")

**Desktop layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  📦 Trasferimento Asset                                    [X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Data:  [  2026-04-30  📅 ]     Asset: [ 🅱 Bitcoin  ▼ ]       │
│  Quantità: [ 0,5       ]                                       │
│                                                                 │
│  ┌─── Da ──────────────────┐       ┌─── A ───────────────────┐ │
│  │ Broker: [ Coinbase ▼ ]  │  ──→  │ Broker: [ Binance  ▼ ]  │ │
│  └─────────────────────────┘       └─────────────────────────┘ │
│                                                                 │
│  ▸ Avanzate                                                     │
│    Cost basis override: [________]                              │
│    Tag: [________]   Note: [____________________]               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Annulla]  [💾 Salva]              │
└─────────────────────────────────────────────────────────────────┘
```

**Mobile layout**:
```
┌──────────────────────────────┐
│  📦 Trasferimento Asset  [X] │
├──────────────────────────────┤
│                               │
│  Data:  [  2026-04-30  📅 ]  │
│  Asset: [ 🅱 Bitcoin  ▼ ]    │
│  Quantità: [ 0,5       ]    │
│                               │
│  ── Da ───────────────────── │
│  Broker: [ Coinbase  ▼ ]    │
│                               │
│             ↓                 │
│                               │
│  ── A ────────────────────── │
│  Broker: [ Binance   ▼ ]    │
│                               │
│  ▸ Avanzate                   │
│                               │
├───────────────────────────────┤
│        [Annulla]  [💾 Salva]  │
└───────────────────────────────┘
```

**Constraints**: Broker Da ≠ Broker A. Asset + qty shared. User enters ONE positive qty — backend auto-generates -qty on "Da" side and +qty on "A" side.

---

#### R6-B.3 — TransactionFormModal: Cash Transfer (pair_form_layout = "transfer_cash")

**Desktop layout**:
```
┌─────────────────────────────────────────────────────────────────┐
│  🏦 Bonifico                                               [X] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Data:  [  2026-04-30  📅 ]                                    │
│  [ EUR 🇪🇺  ▼ ]  [ 5.000,00 ]                                   │
│                                                                 │
│  ┌─── Da ──────────────────┐       ┌─── A ───────────────────┐ │
│  │ Broker: [ IBKR     ▼ ]  │  ──→  │ Broker: [ Fineco   ▼ ]  │ │
│  └─────────────────────────┘       └─────────────────────────┘ │
│                                                                 │
│  ▸ Avanzate                                                     │
│    Tag: [________]   Note: [____________________]               │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                              [Annulla]  [💾 Salva]              │
└─────────────────────────────────────────────────────────────────┘
```

**Mobile layout**:
```
┌──────────────────────────────┐
│  🏦 Bonifico             [X] │
├──────────────────────────────┤
│                               │
│  Data:  [  2026-04-30  📅 ]  │
│  [ EUR 🇪🇺  ▼ ] [ 5.000,00 ] │
│                               │
│  ── Da ───────────────────── │
│  Broker: [ IBKR      ▼ ]    │
│                               │
│             ↓                 │
│                               │
│  ── A ────────────────────── │
│  Broker: [ Fineco    ▼ ]    │
│                               │
│  ▸ Avanzate                   │
│                               │
├───────────────────────────────┤
│        [Annulla]  [💾 Salva]  │
└───────────────────────────────┘
```

**Constraints**: Broker Da ≠ Broker A. Currency + amount shared. Amount auto-split by backend (WITHDRAWAL negative, DEPOSIT positive).

---

#### R6-B.4 — Unified BulkModal: Merged Create + Edit

**Key decision**: Unify "create-many" and "edit-many" into a single `TransactionBulkModal`.
The distinction `mode: 'create-many' | 'edit-many'` disappears — the modal always contains
a mixed bag of new drafts + existing rows, validated+committed together via the unified
backend pipeline.

**New capabilities**:
1. Pre-populated rows (from "New Transaction" → 1 empty draft, or "Edit selected" → N existing)
2. `[+ Nuova riga]` button to add blank drafts (already exists)
3. `[🔍 Cerca e aggiungi]` button → opens a **TransactionPickerModal** (see R6-B.5)
4. Row selection via checkboxes for bulk operations (link, unlink, delete)
5. Paired rows render as 2 internal lines within the same DataTable row
6. **Three row states**: `new` (green), `edit` (blue), `delete` (red bg → marked for DB deletion)

**Why unified**:
- Backend already validates+commits a mixed batch (new + updated) in one call
- The picker modal enables `promote` (link 2 unlinked rows)
  inside the same workflow — no need for the separate `PromotePairWizardModal`
- Edit of a paired row auto-fetches its partner → both appear in the grid

**Row state semantics**:

| State | Badge | Background | On Save | Notes |
|-------|-------|------------|---------|-------|
| `new` | 🟢 new | default | CREATE | Blank draft or from TransactionFormModal |
| `edit` | 🟡 edit | default | UPDATE | Pulled from DB (edit selection or picker) |
| `delete` | 🔴 del | red tint | DELETE | User marked for deletion. Still visible for review |

**Row actions**:
- `[✎]` Edit → opens nested TransactionFormModal
- `[📋]` Clone → duplicates as `new` draft
- `[➖]` Remove from batch → silently removes from grid (no DB change)
- `[🗑]` Mark for deletion → toggles red `delete` state (on save → backend DELETE)
  - If already `delete`, clicking again reverts to `edit` (toggle)
  - Only available for existing rows (not `new` drafts — those just use `[➖]` remove)

**Sorting & Filtering**:
- Default sort: date ascending
- Sortable columns: date (asc/desc toggling)
- Column filters (same Excel-style as main table): type, broker, asset, tags, cash currency
- Paired row filter matching: row shown if **either half** matches active filters
  (e.g. filter broker="IBKR" → shows a transfer pair where one side is IBKR)

**Modal layout**:
```
┌───────────────────────────────────────────────────────────────────────────┐
│  📋 Transazioni · 6 righe (2 nuove · 1 coppia · 1 elimina)         [X]  │
├───────────────────────────────────────────────────────────────────────────┤
│  [🔍 Cerca e aggiungi]          [+ Nuova riga]          [👁 Col]        │
├───────────────────────────────────────────────────────────────────────────┤
│  ☐ │ S    │ Data ⇅ │ Tipo 🔽│ Broker 🔽│ Qtà     │ Importo 🔽    │ Asset 🔽│
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│  ☐ │ new  │ 25/04  │ BUY   │ IBKR    │ 10      │ -500 $ USD    │ AAPL   │
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│  ☐ │ edit │ 26/04  │ SELL  │ Fineco  │ -5      │ +250 € EUR    │ VWCE   │
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│    │      │        │       │         │         │ Da:-1000€ EUR │        │
│  ☐ │ new  │ 28/04  │ 💱 FX │ IBKR    │ —       │───────────────│ —      │
│    │      │        │       │         │         │ A: +1090$ USD │        │
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│    │      │        │       │Da:Coinb.│         │               │        │
│  ☐ │ edit │ 27/04  │ 📦 TR │─────────│ 0,5     │ —             │ BTC    │
│    │      │        │       │A: Binan.│         │               │        │
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│    │      │        │       │Da: IBKR │         │               │        │
│  ☐ │ new  │ 29/04  │ 🏦 BO │─────────│ —       │ 5.000 € EUR   │ —      │
│    │      │        │       │A: Fineco│         │               │        │
├────┼──────┼────────┼───────┼─────────┼─────────┼───────────────┼────────┤
│  ☐ │ 🔴del│ 30/04  │ FEE   │ IBKR    │ 0       │ -2 $ USD      │ —      │  ← red bg
├────┴──────┴────────┴───────┴─────────┴─────────┴───────────────┴────────┤
│  ☑ 2 selezionate   [🗑 Elimina sel.]  [🔗 Collega coppia]  [⛓💥 Scolleg]│
├─────────────────────────────────────────────────────────────────────────┤
│  ✓ Validazione OK                                                       │
│                                        [Annulla]  [💾 Salva tutto]      │
└─────────────────────────────────────────────────────────────────────────┘
```

**Paired row rendering detail** — each pair type uses 2 internal lines in the
SAME existing columns (no new "Da"/"A" columns), with `Da:`/`A:` labels:

**FX** (`pair_form_layout = "fx"`):
- Broker: single value (shared), no split
- Importo: 2 lines → `Da: -1.000 € EUR` / `A: +1.090 $ USD`
- Qtà: `—` (forbidden)
- Asset: `—` (forbidden)

**Transfer Asset** (`pair_form_layout = "transfer_asset"`):
- Broker: 2 lines → `Da: Coinbase` / `A: Binance`
- Qtà: **single positive value** (user enters once, backend splits ±)
- Importo: `—` (forbidden)
- Asset: single value (shared), no split

**Transfer Cash / Bonifico** (`pair_form_layout = "transfer_cash"`):
- Broker: 2 lines → `Da: IBKR` / `A: Fineco`
- Importo: single value (shared — same currency+amount, backend splits ±)
- Qtà: `—` (forbidden)
- Asset: `—` (forbidden)

---

#### R6-B.5 — TransactionPickerModal: Search & Add Existing Transactions

The `[🔍 Cerca e aggiungi]` button opens a **modal containing the exact same
`TransactionsTable` component** used in the main page. This ensures:
- Same columns, filters, sorting, pagination
- Zero code duplication for maintenance
- Full power of column filters for finding transactions

The picker receives `excludeIds: Set<number>` — IDs already in the bulk grid
are hidden from the picker so the user can't add duplicates.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔍 Seleziona transazioni da aggiungere                            [X] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─── TransactionsTable (same component as main page) ───────────────┐ │
│  │  ☐ │ Data ⇅ │ Tipo 🔽│ Qtà    │ Importo 🔽    │ Asset 🔽│ Broker 🔽│ │
│  │ ────┼────────┼───────┼────────┼───────────────┼────────┼─────────│ │
│  │  ☑  │ 27/04  │ BUY   │ +0.5   │ -15.000 $ USD │ BTC    │ IBKR    │ │
│  │  ☐  │ 25/04  │ SELL  │ -1.0   │ +30.000 € EUR │ BTC    │ Fineco  │ │
│  │  ☑  │ 20/04  │ BUY   │ +0.2   │ -6.000 $ USD  │ BTC    │ IBKR    │ │
│  │  ☐  │ 15/04  │ 📦 TR │ -0.1   │ —             │ BTC    │ Coinbase│ │
│  │     │        │       │ +0.1   │               │        │ Binance │ │
│  │  ☐  │ 10/04  │ DIV   │ 0      │ +50 $ USD     │ AAPL   │ IBKR    │ │
│  │                                                                    │ │
│  │  ◀ 1 2 3 … ▶   Pagina 1 di 5 · 50 per pagina                     │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ☑ 2 selezionate                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│                              [Annulla]  [✓ Aggiungi selezionate]        │
└─────────────────────────────────────────────────────────────────────────┘
```

**Behaviour**:
- Opens read-only with multi-select enabled
- Rows already in the bulk grid are excluded (`excludeIds`)
- Linked pairs: selecting one side auto-selects the partner
- On `[✓ Aggiungi]`: selected rows are pulled into the bulk grid as `edit` state
- If a selected TX has a linked partner → both halves are added (paired row)
- The picker component is literally `<TransactionsTable>` with a prop flag
  `pickerMode={true}` that hides row actions and enables selection-only UX

**Use cases**:
- **Promote**: Add 2 unlinked rows → back in bulk → select both → 🔗 Collega
- **Edit alongside new**: Mix existing corrections with new additions in one batch
- **Batch review**: Pull in related TXs via column filters to inspect/fix together
- **Mark for deletion**: Add a TX via picker → then mark it 🔴 delete in the bulk grid

---

#### R6-B.6 — Promote & Split Within Bulk Modal

**Promote (Link)**: Select exactly 2 compatible rows → `[🔗 Collega coppia]` button appears.

```
┌────────────────────────────────────────────────────────────────────────┐
│  ☑ 2 selezionate   [🗑 Elimina sel.]  [🔗 Collega coppia]             │
├────────────────────────────────────────────────────────────────────────┤
│  Clicking 🔗 → inline confirmation banner:                            │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ ⚠ Collegare come coppia DEPOSIT ↔ WITHDRAWAL?                   │ │
│  │   Riga 3: IBKR +1.000 EUR (DEPOSIT)                             │ │
│  │   Riga 5: Fineco -1.000 EUR (WITHDRAWAL)                        │ │
│  │                                        [Annulla]  [✓ Collega]   │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  After confirm → rows merge into a single paired row with Da:/A:      │
│  labels. The pair is committed as linked on 💾 Salva.                  │
└────────────────────────────────────────────────────────────────────────┘
```

**Compatibility check** (frontend-side, before showing 🔗):
- Both rows must have `requires_link === true` (pair types only)
- For `transfer_asset`: same asset, different broker, type === TRANSFER
- For `transfer_cash`: same currency, different broker, type DEPOSIT+WITHDRAWAL
- For `fx`: same broker, different currency, type === FX_CONVERSION

**Split (Unlink)**: Row action `⛓💥` on a paired row → confirmation → pair splits
into 2 independent rows in the grid.

```
┌────────────────────────────────────────────────────────────────────────┐
│  Row actions for a paired row:                                         │
│                          [✎ Edit] [📋 Clone] [➖ Remove] [🗑 Del] [⛓💥] │
│                                                                        │
│  Clicking ⛓💥 → inline confirmation banner:                            │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │ ⚠ Scollegare questa coppia?                                     │  │
│  │   Le 2 transazioni diventeranno righe indipendenti.              │  │
│  │   IBKR: +1.000 EUR (DEPOSIT) ↔ Fineco: -1.000 EUR (WITHDRAWAL) │  │
│  │                                     [Annulla]  [⛓💥 Scollega]   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  After confirm → paired row splits into 2 separate rows in the grid.   │
│  The unlink is committed on 💾 Salva.                                   │
└────────────────────────────────────────────────────────────────────────┘
```

---

#### R6-B.7 — Main Table: Promote & Split Actions

These actions also remain available in the main `TransactionsTable` for quick operations
without opening the bulk modal:

**Promote**: Select exactly 2 rows → bulk action bar shows `[🔗 Collega come coppia]`.
```
┌──────────────────────────────────────────────────────────────────┐
│  ☐ Data     │ Tipo │ Qtà  │ Importo     │ Asset │ Broker  │ Tag │
├──────────────┼──────┼──────┼─────────────┼───────┼─────────┼─────┤
│  ☑ 26/04     │ 🏦   │  0   │ +1.000 EUR  │  —    │ IBKR    │     │
│  ☑ 26/04     │ 🏦   │  0   │ -1.000 EUR  │  —    │ Fineco  │     │
├──────────────┴──────┴──────┴─────────────┴───────┴─────────┴─────┤
│  ☑ 2 sel.  [🗑 Elimina]  [🔗 Collega come coppia]               │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ ⚠ Collegare come DEPOSIT↔WITHDRAWAL?                       │  │
│  │   IBKR: +1.000 EUR · Fineco: -1.000 EUR                    │  │
│  │                              [Annulla]  [✓ Collega]         │  │
│  └─────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

**Split**: Per-row action `⛓💥` (shown only on linked rows):
```
│  26/04  │ 🏦  │ 0  │+1.000 EUR │⬆🔗│ — │ IBKR  │ [👁][✎][📋][🗑][⛓💥] │
                                                      ↑ Scollega coppia

      │ click ⛓💥
      ▼

┌──────────────────────────────────────────────────────────────────┐
│ ⚠ Scollegare questa coppia?                                     │
│   Le 2 transazioni diventeranno indipendenti.                    │
│   IBKR: +1.000 EUR (DEPOSIT) ↔ Fineco: -1.000 EUR (WITHDRAWAL) │
│                         [Annulla]  [⛓💥 Scollega]                │
└──────────────────────────────────────────────────────────────────┘
```

---

#### R6-B.8 — Entry Points & Flow Summary

```
                    ┌─────────────────────┐
                    │   TransactionsTable  │
                    │   (main page)        │
                    └──┬──────┬──────┬─────┘
                       │      │      │
         [+ Aggiungi]  │  [✎ Edit]  [🔗/⛓💥]
         (1 new draft) │  (N sel.)  (quick)
                       │      │      │
                       ▼      ▼      │
              ┌────────────────────┐  │
              │  Unified BulkModal │◄─┘ (promote/split also here)
              │                    │
              │  - pre-pop rows    │
              │  - + Nuova riga    │
              │  - 🔍 Picker modal │←── TransactionsTable (pickerMode)
              │  - ☐ selection     │      same component, excludeIds
              │  - 🔗 link pair    │
              │  - ⛓💥 split pair  │
              │  - 🔴 mark delete  │
              │  - ➖ remove batch │
              │  - 💾 Salva tutto  │
              └────────────────────┘
```

**Flow: New single TX** → opens BulkModal with 1 empty draft. User fills it, can add more.
**Flow: Edit single TX** → opens BulkModal with that TX loaded. If paired, partner auto-loaded.
**Flow: Edit N selected** → opens BulkModal with all N rows. Paired partners auto-loaded.
**Flow: Add existing** → from BulkModal: 🔍 → TransactionPickerModal (full table) → select → Aggiungi.
**Flow: Promote** → from BulkModal: add 2 TXs via picker → select both → 🔗 Collega.
  Or from main table: select 2 → 🔗 quick action (backend PATCH immediately).
**Flow: Delete** → from BulkModal: add TX via picker → mark 🔴 delete → on 💾 Salva → backend DELETE.
  Or from main table: 🗑 per-row action (existing behavior).
**Flow: Split** → from BulkModal: ⛓💥 on paired row → splits in grid → committed on save.
  Or from main table: ⛓💥 per-row action → confirmation → backend PATCH immediately.

