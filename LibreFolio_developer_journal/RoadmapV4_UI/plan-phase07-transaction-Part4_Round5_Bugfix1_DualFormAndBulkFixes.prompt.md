# Plan — Phase 7 · Part 4 · Round 5 · Bugfix 1 — Dual Form & Unified BulkModal Fixes

**Date**: 2026-04-30
**Status**: ✅ DONE
**Priority**: P1 (blocking bugs + architectural)
**Estimated effort**: ~12 h

**Parent**: [`plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md`](./plan-phase07-transaction-Part4_Round5_ServerDrivenTypeRules.prompt.md) §R6-B implementation

**Child**: [`plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix2_PostTestWalkOverhaul.prompt.md) — post-testwalk fixes (readonly BulkModal, dual dates, i18n, docs)

---

## 🎯 Obiettivo

1. Fix blocking bugs from manual testing of dual-form + unified BulkModal
2. Add `CASH_TRANSFER` backend type (Opzione C — approved)
3. Implement paired row rendering in BulkModal (W46 — not deferred)
4. Resolve split/promote architecture: immediate bulk endpoints + server-driven metadata
5. Add split/promote metadata to `TXTypeMetadata` (field constraints, split/promote rules)
6. Remove PromotePairWizardModal → selection-based promote flow

---

## ✅ Architectural Decision: Opzione C — Backend Composite Types + Split with Type Mutation

**Decision date**: 2026-04-30
**Status**: ✅ APPROVED

All three composite transaction types exist as first-class backend enum values:
- `TRANSFER` — asset transfer between brokers (same-type pair)
- `FX_CONVERSION` — currency exchange (same-type pair)
- `CASH_TRANSFER` — **NEW** — wire transfer / bonifico (same-type pair)

### Split Rules (deterministic type mutation)

When a linked pair is unlinked ("split"), both halves are mutated to standalone types:

| Original type | "From" half → | "To" half → | Mutation details |
|---|---|---|---|
| `CASH_TRANSFER` | `WITHDRAWAL` | `DEPOSIT` | cash preserved, `link_uuid` removed |
| `TRANSFER` | `ADJUSTMENT` (-qty) | `ADJUSTMENT` (+qty) | qty preserved, `link_uuid` removed |
| `FX_CONVERSION` | `WITHDRAWAL` (cash neg) | `DEPOSIT` (cash pos) | cash preserved, `link_uuid` removed |

### Promote Rules (inverse of split)

When two standalone rows are "promoted" to a pair:

| Standalone types | → Pair type | Validation |
|---|---|---|
| `WITHDRAWAL` + `DEPOSIT` | `CASH_TRANSFER` | same currency, different brokers |
| `ADJUSTMENT` + `ADJUSTMENT` | `TRANSFER` | same asset, different brokers, opposite qty |
| `WITHDRAWAL` + `DEPOSIT` | `FX_CONVERSION` | different currencies, same broker |

### Backend Changes Required

1. **Enum**: add `CASH_TRANSFER` to `TransactionType`
2. **Metadata**: `TXTypeMetadata` for `CASH_TRANSFER` (`requires_link=true`, `pair_form_layout="transfer_cash"`)
3. **Remove W34 hack**: delete `VALID_MIXED_PAIRS` — CASH_TRANSFER+CASH_TRANSFER is same-type ✅
4. **`collectDualCreates('transfer_cash')`**: emit `CASH_TRANSFER`+`CASH_TRANSFER` (not WITHDRAWAL+DEPOSIT)
5. **Migration**: modify `001_initial.py`, `./dev.py db create-clean`
6. **`./dev.py api sync`** after metadata changes

---

## ✅ Architectural Decision: Split & Promote — Immediate with Dedicated Endpoints

**Decision date**: 2026-04-30
**Status**: ✅ APPROVED

### The problem

Split/promote are **structural transformations** (mutate type, create/remove links). The batch model "prepare all → save all" works for data edits but creates an unmanageable state graph for structural ops (split → edit → re-promote → edit partner → split again...).

### Decision: Split/Promote are always **immediate** (not deferred in batch)

Split/promote are **safe for business logic** — they're deterministic type mutations that never violate constraints. Therefore they can be executed serenely from both the main table and the BulkModal.

| Operation | Context | Backend | Frontend |
|---|---|---|---|
| **Split DB pair** | BulkModal or main table | `POST /tx/split` (bulk) → mutates types, removes link, returns split results | ConfirmModal → on success, grid replaces paired row(s) with standalone rows |
| **Promote 2 DB rows** | BulkModal or main table | `POST /tx/promote` (bulk) → mutates types, creates link, returns pairs | ConfirmModal → on success, grid merges rows into paired rows |
| **Create new pair** | FormModal (dual mode) | Normal `POST /commit` with 2 creates sharing `link_uuid` | Already works via `collectDualCreates()` |
| **Split unsaved pair** | BulkModal (2 new drafts) | No backend call needed | Frontend removes paired draft, adds 2 single drafts |
| **Promote 2 new drafts** | BulkModal | No backend call needed | Frontend merges 2 drafts into paired draft |
| **Promote 1 DB + 1 new** | BulkModal | ❌ **Not allowed** | Tooltip: "Save the new row first, then link" |

### API Endpoints (Bulk)

Both endpoints accept **lists of pairs** for consistency with the rest of the system. Even if splitting multiple pairs at once may seem overkill, it keeps the API coherent and future-proof.

```
POST /api/v1/transactions/split
  → Body: { items: [ { id: int }, ... ] }
    Each id is one half of a pair; backend finds partner via link_uuid.
  → Response: { results: [ { from: TXReadItem, to: TXReadItem }, ... ] }
  → Backend applies SPLIT_TYPE_MAP, removes link_uuid for each pair.
  → Errors: if any id has no link_uuid → 422 with per-item error.

POST /api/v1/transactions/promote
  → Body: { items: [ { id_a: int, id_b: int }, ... ] }
  → Response: { results: [ { pair_a: TXReadItem, pair_b: TXReadItem }, ... ] }
  → Backend applies PROMOTE_TYPE_MAP, generates link_uuid for each pair.
  → Validation: checks type compatibility + field constraints per promote_rules.
  → Errors: if any pair fails validation → 422 with per-item error.
```

### Batch `TXMixedBatch` stays unchanged

`POST /transactions/commit` keeps `creates + updates + deletes` only. No `splits[]`/`promotes[]`. Clean separation.

### PromotePairWizardModal → to be removed

The dedicated wizard is replaced by:
- **Main table**: select 2 rows → bulk action 🔗 → ConfirmModal → `POST /promote`
- **BulkModal**: same flow for DB rows, or frontend-only merge for new drafts
- Step for removal added in Batch 2 (B1-15)

---

## ✅ Architectural Decision: Server-Driven Split/Promote Metadata

**Decision date**: 2026-04-30
**Status**: ✅ APPROVED

### The problem

Frontend currently hardcodes knowledge of how pairs split/promote and what field constraints exist between halves. This violates the "backend is source of truth" principle and creates drift risk.

### Decision: Backend communicates split/promote rules via `TXTypeMetadata` extensions

The backend provides all info the frontend needs to:
1. Know what 2 rows a pair splits into (for preview before ConfirmModal)
2. Know if 2 selected standalone rows can be promoted (for enabling/disabling the promote action)
3. Know field equivalence constraints (equal/opposite/different) for creating new pairs and validating promotes

### New Schema Types

```python
class PairFieldConstraint(BaseModel):
    """How a field relates between the two halves of a pair."""
    field: Literal["broker_id", "asset_id", "cash_currency", "cash_amount", "quantity"]
    relation: Literal["equal", "opposite", "different"]
    # equal: same value on both sides (e.g. asset in TRANSFER)
    # opposite: negated value (e.g. quantity in TRANSFER: -qty / +qty)
    # different: must be different (e.g. broker in TRANSFER, currency in FX)

class SplitMeta(BaseModel):
    """How a paired type splits into 2 standalone types."""
    from_type: str  # type for "from" half (negative/source side)
    to_type: str    # type for "to" half (positive/destination side)

class PromoteRule(BaseModel):
    """How 2 standalone types can be promoted to this paired type."""
    type_a: str  # first standalone type
    type_b: str  # second standalone type
    field_constraints: list[PairFieldConstraint]  # validation rules
```

### New fields on `TXTypeMetadata` (only for paired types, None for standalone)

```python
# Added to TXTypeMetadata:
split_into: SplitMeta | None = None
promote_from: list[PromoteRule] | None = None
pair_field_constraints: list[PairFieldConstraint] | None = None
```

### Concrete Values

| Pair Type | `split_into` | `promote_from` | `pair_field_constraints` |
|---|---|---|---|
| `TRANSFER` | `{from: ADJUSTMENT, to: ADJUSTMENT}` | `[{ADJUSTMENT, ADJUSTMENT, [asset=equal, broker=different, quantity=opposite]}]` | `[asset=equal, broker=different, quantity=opposite]` |
| `CASH_TRANSFER` | `{from: WITHDRAWAL, to: DEPOSIT}` | `[{WITHDRAWAL, DEPOSIT, [cash_currency=equal, broker=different, cash_amount=opposite]}]` | `[cash_currency=equal, broker=different, cash_amount=opposite]` |
| `FX_CONVERSION` | `{from: WITHDRAWAL, to: DEPOSIT}` | `[{WITHDRAWAL, DEPOSIT, [cash_currency=different, broker=equal, cash_amount=any]}]` | `[cash_currency=different, broker=equal]` |

### Frontend Usage

1. **Creating new pair**: frontend reads `pair_field_constraints` to auto-populate mirrored fields
2. **Promote check**: given 2 selected rows, scan all paired types' `promote_from` — if any matches → enable 🔗 action
3. **Split preview**: read `split_into` to show "This will become: WITHDRAWAL + DEPOSIT" in ConfirmModal
4. **BulkModal new draft pairs**: `pair_field_constraints` drives which fields to mirror/negate when creating dual drafts

---

## ✅ Already Fixed (Batch 1)

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| W32 | DEPOSIT/WITHDRAWAL trigger dual form | `pairLayout` dual only when `requiresPair=true` | ✅ |
| W33 | FX/TRANSFER not in dropdown | All types visible, pair types prefixed `↔` | ✅ |
| W34 | Backend rejects WITHDRAWAL↔DEPOSIT | `VALID_MIXED_PAIRS` (to be replaced by CASH_TRANSFER) | ✅→superseded |
| W35 | Type names not translated in errors | `resolveIssueMessage` translates `typeA`/`typeB` | ✅ |
| W36 | Arrow is text `──→` | Lucide icons, clickable swap | ✅ |
| W37 | Same broker on both sides | Filtered broker lists | ✅ |

---

## 🐛 Issues (Batch 2)

### W40 — Add `CASH_TRANSFER` backend type (replaces virtual frontend approach)
**Severity**: P1
**Fix**: New enum + metadata + migration. Frontend dropdown shows it naturally (no virtual hack).

### W41 — Type readonly in create dual mode
**Severity**: P2
**Fix**: Dual template uses `typeImmutable` guard (false in create).

### W42 — Duplicate validation errors + qty=0 in payload
**Severity**: P2
**Fix**: Deduplicate by `code`. Fix `collectDualCreates` qty propagation.

### W43/W44 — "Create new" as persistent dropdown option
**Severity**: P2
**Fix**: `SearchSelect` footer (`createLabel` + `onCreateNew` props).

### W45 — BrokerModal z-index too low
**Severity**: P2
**Fix**: Add `zIndex` prop passthrough.

### W46 — BulkModal paired row single-height
**Severity**: P2
**Fix**: Double-height rendering with Da:/A: labels. **NOT deferred**.

### W47 — `{type}` literal in error message
**Severity**: P3

### W48 — Cost basis tooltip
**Severity**: P3

### W49 — Documentation link (📖) next to type
**Severity**: P3

### W50 — i18n `common.createNew`
**Severity**: P3

### W51 — Split/Promote metadata not server-driven
**Severity**: P1
**Fix**: Add `split_into`, `promote_from`, `pair_field_constraints` to `TXTypeMetadata`. Frontend reads them instead of hardcoding rules.

### W52 — Split/Promote API endpoints missing (bulk)
**Severity**: P1
**Fix**: `POST /transactions/split` (bulk) + `POST /transactions/promote` (bulk). Dedicated endpoints, not in TXMixedBatch.

### W53 — PromotePairWizardModal still exists
**Severity**: P2
**Fix**: Remove wizard. Replace with: select 2 rows → bulk action 🔗 → ConfirmModal → `POST /promote`.

---

## 📋 Steps — Batch 2

### Step B1-8 — W40: Backend `CASH_TRANSFER` type (~45 min)

**Files**: `backend/app/models/transaction.py`, `backend/app/schemas/transactions.py`, `backend/app/services/transaction_service.py`

1. Add `CASH_TRANSFER = "CASH_TRANSFER"` to `TransactionType` enum
2. Add `TXTypeMetadata` for CASH_TRANSFER:
   - `requires_link=True`, `pair_form_layout="transfer_cash"`
   - `asset_mode="forbidden"`, `cash_mode="required"`, `quantity_mode="forbidden"`
   - `cash_sign="nonzero"`, `quantity_sign="zero"`
   - `icon_slug="cash-transfer"` (fallback to `transfer.png` if missing)
3. Remove `VALID_MIXED_PAIRS` from `_validate_linked_pair` (no longer needed)
4. Remove `pair_form_layout` from DEPOSIT and WITHDRAWAL metadata (they're standalone)
5. Modify `001_initial.py` → `./dev.py db create-clean`
6. `./dev.py api sync`

### Step B1-8b — Frontend: update `collectDualCreates('transfer_cash')` (~15 min)

**File**: `TransactionFormModal.svelte`

Change WITHDRAWAL+DEPOSIT → CASH_TRANSFER+CASH_TRANSFER:
```javascript
if (pairLayout === 'transfer_cash') {
    const fromItem = { type: 'CASH_TRANSFER', cash: {code, amount: -abs}, ... };
    const toItem   = { type: 'CASH_TRANSFER', cash: {code, amount: +abs}, ... };
}
```

### Step B1-9 — W41: Fix type readonly in create dual mode (~15 min)

Dual template: `{#if typeImmutable}` → readonly badge, else `<TransactionTypeSearchSelect>`.

### Step B1-10 — W42: Deduplicate errors + fix qty propagation (~20 min)

1. Deduplicate issues by `code` in dual validate path
2. Fix `collectDualCreates('transfer_asset')` qty from `draft.quantity`

### Step B1-11 — W43/W44: "Create new" dropdown footer (~1 h)

`SearchSelect` → `createLabel` + `onCreateNew` props. Sticky footer row.
Remove old `+ Add` links below fields.

### Step B1-12 — W45: z-index stacked modals (~15 min)

BrokerModal/AssetModal: `zIndex` prop → ModalBase.

### Step B1-13 — W46: BulkModal paired row rendering (~1.5 h)

**File**: `TransactionBulkModal.svelte`

For rows where `getTypeRule(row.type).requiresPair`:
- **Broker column**: render 2 lines `Da: {broker1}` / `A: {broker2}` (transfer_asset, transfer_cash)
- **Cash column**: render 2 lines `Da: -1.000€` / `A: +1.090$` (fx)
- **Asset column**: single value (shared) for transfer_asset
- **Qty column**: single positive value for transfer_asset, `—` for others
- Row height: `min-h-[3.5rem]` or auto-expand

Implementation: in the `cell()` callback for broker/cash columns, check if the row's type has `requiresPair`. If yes, render multi-line HTML with `Da:`/`A:` labels.

Note: the DraftRow currently stores a single broker_id and single cash. For paired rendering, the nested FormModal stores the partner data separately (dualTo). The BulkModal needs to either:
- (a) Store the partner's data in DraftRow (add `partnerBrokerId`, `partnerCash` fields)
- (b) Fetch the partner lazily when rendering

Approach (a) is simpler for create-mode (user fills both sides in FormModal → pushes both fields to the grid). For edit-mode, the partner data comes from `related_transaction_id` fetch.

### Step B1-14 — W47/W48/W49/W50: i18n + tooltips + doc link (~30 min)

Batch the small fixes: error params, cost basis tooltip, BookOpen doc link, `common.createNew` key.

### Step B1-15 — W51: Split/Promote server-driven metadata (~1 h)

**Files**: `backend/app/schemas/transactions.py`

1. Add `PairFieldConstraint`, `SplitMeta`, `PromoteRule` Pydantic models
2. Add `split_into`, `promote_from`, `pair_field_constraints` fields to `TXTypeMetadata` (all `| None`, default None)
3. Populate for TRANSFER, FX_CONVERSION, CASH_TRANSFER (see concrete values table above)
4. `./dev.py api sync` → frontend gains typed access to split/promote rules
5. Frontend: replace hardcoded pair creation logic with metadata-driven `pair_field_constraints` reads

### Step B1-16 — W52: Bulk Split/Promote endpoints (~2 h)

**Files**: `backend/app/api/v1/transactions.py`, `backend/app/services/transaction_service.py`, `backend/app/schemas/transactions.py`

1. Add request/response schemas:
   - `TXSplitRequest`: `items: list[TXSplitItem]` where `TXSplitItem = { id: int }`
   - `TXSplitResponse`: `results: list[TXSplitResult]` where `TXSplitResult = { from_tx: TXReadItem, to_tx: TXReadItem }`
   - `TXPromoteRequest`: `items: list[TXPromoteItem]` where `TXPromoteItem = { id_a: int, id_b: int }`
   - `TXPromoteResponse`: `results: list[TXPromoteResult]` where `TXPromoteResult = { pair_a: TXReadItem, pair_b: TXReadItem }`
2. Service layer:
   - `split_pairs(user_id, items)`: for each item, find tx + partner via link_uuid, apply SPLIT_TYPE_MAP, remove link_uuid, save
   - `promote_pairs(user_id, items)`: for each pair, validate type compatibility via `promote_from` rules, apply PROMOTE_TYPE_MAP, generate link_uuid, save
3. API routes:
   - `POST /api/v1/transactions/split` → `split_pairs`
   - `POST /api/v1/transactions/promote` → `promote_pairs`
4. Error handling: per-item errors (422 with array of issues per item index)
5. `./dev.py api sync`

### Step B1-17 — W53: Remove PromotePairWizardModal (~30 min)

1. Delete `PromotePairWizardModal.svelte` component
2. Remove references from parent components
3. Replace with: row selection (2 rows) → toolbar 🔗 action → ConfirmModal → `POST /promote`
4. Same flow accessible from BulkModal for DB rows

---

## 🎨 ASCII Art — Modal Mockups

### Split ConfirmModal (immediato — da BulkModal o Main Table)

Split è **sempre immediato**: click → ConfirmModal → backend `POST /split` → grid aggiornata.

**Da BulkModal** (riga paired → action ⛓💥):

L'utente clicca ⛓💥 sulla riga paired nel BulkModal:
```
┌───────────────────────────────────────────────────────────────────────────┐
│  📋 Transazioni · 4 righe                                            [X] │
├───────────────────────────────────────────────────────────────────────────┤
│  ☐ │ S    │ Data  │ Tipo   │ Broker        │ Importo       │ Asset      │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ edit │ 26/04 │ BUY    │ IBKR          │ -500 $ USD    │ AAPL       │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│    │      │       │        │ Da: IBKR      │               │            │
│  ☐ │ edit │ 27/04 │ 🏦 BO  │───────────────│ 5.000 € EUR   │ —    [⛓💥] │ ← click
│    │      │       │        │ A:  Fineco     │               │            │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ new  │ 28/04 │ DIV    │ Fineco        │ +50 € EUR     │ VWCE       │
├────┴──────┴───────┴────────┴───────────────┴───────────────┴────────────┤
│                                        [Annulla]  [💾 Salva tutto]       │
└──────────────────────────────────────────────────────────────────────────┘
```

→ Si apre una **ConfirmModal sopra tutto** (z-index > BulkModal, con backdrop scuro):
```
 ╔══════════════════════════════════════════════════════════════════╗
 ║                                                                  ║
 ║   ⚠ Scollegare questa coppia?                               [X] ║
 ║                                                                  ║
 ║   Le 2 transazioni diventeranno righe indipendenti:              ║
 ║     CASH_TRANSFER → WITHDRAWAL  (IBKR: -5.000 € EUR)            ║
 ║     CASH_TRANSFER → DEPOSIT     (Fineco: +5.000 € EUR)          ║
 ║                                                                  ║
 ║   ⚡ Operazione immediata (salvataggio non necessario)           ║
 ║                                                                  ║
 ║                                 [Annulla]  [⛓💥 Scollega]       ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝
      ░░░░░░░░░░░░░░ backdrop scuro (BulkModal sotto) ░░░░░░░░░░░░
```

**Dopo conferma split** → la riga paired scompare, appaiono 2 righe standalone:
```
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ edit │ 27/04 │ WITHDR │ IBKR          │ -5.000 € EUR  │ —          │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ edit │ 27/04 │ DEPOS  │ Fineco        │ +5.000 € EUR  │ —          │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
```

**Da Main Table** (per-row action ⛓💥): stessa ConfirmModal sopra tutto.
```
│  27/04 │ 🏦 BO │ Da:IBKR/A:Fineco │ 5.000€ │ — │ [👁][✎][📋][🗑][⛓💥] │
                                                                   ↑ click
```
→ stessa ConfirmModal (doppio bordo ═) sopra la tabella → POST /split → tabella si aggiorna

---

### Split di coppia non salvata (frontend-only)

Se la coppia è un **draft nuovo** (non ancora nel DB), lo split è puramente frontend:
nessuna chiamata backend, nessuna ConfirmModal — il draft coppia viene rimosso e
sostituito da 2 draft singoli.

```
┌───────────────────────────────────────────────────────────────────────────┐
│  📋 Transazioni · 3 righe                                            [X] │
├───────────────────────────────────────────────────────────────────────────┤
│    │      │       │        │ Da: IBKR      │               │            │
│  ☐ │ new  │ 29/04 │ 🏦 BO  │───────────────│ 2.000 € EUR   │ —    [⛓💥] │ ← click
│    │      │       │        │ A:  Fineco     │               │            │
├────┴──────┴───────┴────────┴───────────────┴───────────────┴────────────┤
│   (nessuna modale — split immediato nel grid, zero DB)                   │
├────┬──────┬───────┬────────┬───────────────┬───────────────┬────────────┤
│  ☐ │ new  │ 29/04 │ WITHDR │ IBKR          │ -2.000 € EUR  │ —          │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ new  │ 29/04 │ DEPOS  │ Fineco        │ +2.000 € EUR  │ —          │
└────┴──────┴───────┴────────┴───────────────┴───────────────┴────────────┘
```

---

### Promote ConfirmModal (immediato — da BulkModal o Main Table)

Promote è **sempre immediato** per righe DB. Frontend verifica compatibilità
usando `promote_from` metadata → se match, mostra 🔗.

**Da BulkModal** (seleziona 2 righe standalone → barra azione 🔗):

L'utente seleziona 2 righe e clicca 🔗:
```
┌───────────────────────────────────────────────────────────────────────────┐
│  📋 Transazioni · 5 righe                                            [X] │
├───────────────────────────────────────────────────────────────────────────┤
│  ☐ │ S    │ Data  │ Tipo   │ Broker        │ Importo       │ Asset      │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☑ │ edit │ 26/04 │ WITHDR │ IBKR          │ -1.000 € EUR  │ —          │ ← sel
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☑ │ edit │ 26/04 │ DEPOS  │ Fineco        │ +1.000 € EUR  │ —          │ ← sel
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☐ │ edit │ 27/04 │ BUY    │ IBKR          │ -500 $ USD    │ AAPL       │
├────┴──────┴───────┴────────┴───────────────┴───────────────┴────────────┤
│  ☑ 2 sel.   [🗑 Elimina sel.]  [🔗 Collega coppia]  ← click             │
│                                        [Annulla]  [💾 Salva tutto]       │
└──────────────────────────────────────────────────────────────────────────┘
```

→ Si apre una **ConfirmModal sopra tutto** (z-index > BulkModal, con backdrop scuro):
```
 ╔══════════════════════════════════════════════════════════════════╗
 ║                                                                  ║
 ║   🔗 Collegare come coppia CASH_TRANSFER?                    [X] ║
 ║                                                                  ║
 ║   WITHDRAWAL → CASH_TRANSFER  (IBKR: -1.000 € EUR)             ║
 ║   DEPOSIT    → CASH_TRANSFER  (Fineco: +1.000 € EUR)           ║
 ║                                                                  ║
 ║   Vincoli verificati:                                            ║
 ║     ✓ Stessa valuta (EUR)                                        ║
 ║     ✓ Broker diversi (IBKR ≠ Fineco)                            ║
 ║     ✓ Importi opposti (-1000 / +1000)                           ║
 ║                                                                  ║
 ║   ⚡ Operazione immediata                                       ║
 ║                                                                  ║
 ║                                  [Annulla]  [🔗 Collega]        ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝
      ░░░░░░░░░░░░░░ backdrop scuro (BulkModal sotto) ░░░░░░░░░░░░
```

**Dopo conferma promote** → le 2 righe diventano 1 riga paired:
```
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│    │      │       │        │ Da: IBKR      │               │            │
│  ☐ │ edit │ 26/04 │ 🏦 BO  │───────────────│ 1.000 € EUR   │ —          │
│    │      │       │        │ A:  Fineco     │               │            │
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
```

---

### Promote di 2 draft nuovi (frontend-only)

Se entrambe le righe sono **draft nuovi**, il promote è puramente frontend:
nessuna chiamata backend. I 2 draft vengono fusi in un unico draft coppia.

```
┌───────────────────────────────────────────────────────────────────────────┐
│  ☑ 2 sel.   [🗑 Elimina sel.]  [🔗 Collega coppia]                      │
│                                                                          │
│   (nessuna ConfirmModal — merge immediato nel grid, zero DB)             │
│                                                                          │
│  Risultato: 2 draft → 1 draft paired con Da:/A:                         │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Promote disabilitato — caso misto (1 DB + 1 nuova)

Quando l'utente seleziona 1 riga DB + 1 draft nuovo, il pulsante 🔗 è **disabilitato**
con tooltip esplicativo:

```
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☑ │ edit │ 26/04 │ WITHDR │ IBKR          │ -1.000 € EUR  │ —          │ ← DB (id=5)
├────┼──────┼───────┼────────┼───────────────┼───────────────┼────────────┤
│  ☑ │ new  │ 26/04 │ DEPOS  │ Fineco        │ +1.000 € EUR  │ —          │ ← draft
├────┴──────┴───────┴────────┴───────────────┴───────────────┴────────────┤
│  ☑ 2 sel.   [🗑 Elimina sel.]  [🔗 Collega coppia ⃠]                    │
│                                 ┌─────────────────────────────────────┐  │
│                                 │ 💡 Salva prima la nuova riga,       │  │
│                                 │    poi potrai collegare le due.     │  │
│                                 └─────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### Promote da Main Table (2 righe selezionate → azione rapida)

L'utente seleziona 2 righe nella tabella principale e clicca 🔗:
```
┌──────────────────────────────────────────────────────────────────┐
│  ☐ Data     │ Tipo │ Qtà  │ Importo     │ Asset │ Broker  │ Tag │
├──────────────┼──────┼──────┼─────────────┼───────┼─────────┼─────┤
│  ☑ 26/04     │ ADJ  │ -10  │ —           │ VWCE  │ IBKR    │     │
│  ☑ 26/04     │ ADJ  │ +10  │ —           │ VWCE  │ Fineco  │     │
├──────────────┴──────┴──────┴─────────────┴───────┴─────────┴─────┤
│  ☑ 2 sel.  [🗑 Elimina]  [🔗 Collega come coppia]  ← click      │
└──────────────────────────────────────────────────────────────────┘
```

→ Si apre la **ConfirmModal sopra tutto**:
```
 ╔══════════════════════════════════════════════════════════════════╗
 ║                                                                  ║
 ║   🔗 Collegare come TRANSFER?                                [X] ║
 ║                                                                  ║
 ║   ADJUSTMENT → TRANSFER  (IBKR: -10 VWCE)                       ║
 ║   ADJUSTMENT → TRANSFER  (Fineco: +10 VWCE)                     ║
 ║                                                                  ║
 ║   Vincoli verificati:                                            ║
 ║     ✓ Stesso asset (VWCE)                                        ║
 ║     ✓ Broker diversi (IBKR ≠ Fineco)                            ║
 ║     ✓ Quantità opposte (-10 / +10)                              ║
 ║                                                                  ║
 ║   ⚡ Operazione immediata                                       ║
 ║                                                                  ║
 ║                                  [Annulla]  [🔗 Collega]        ║
 ║                                                                  ║
 ╚══════════════════════════════════════════════════════════════════╝
      ░░░░░░░░░░░░░ backdrop scuro (Main Table sotto) ░░░░░░░░░░░░
```

---

### Bulk Split/Promote — API Request/Response Visualization

**Split (bulk)** — esempio: 2 coppie splittate in un'unica chiamata:
```
POST /api/v1/transactions/split
Body:
{
  "items": [
    { "id": 5 },     ← una metà della coppia CASH_TRANSFER (backend trova partner)
    { "id": 12 }     ← una metà della coppia TRANSFER
  ]
}

Response 200:
{
  "results": [
    {
      "from_tx": { "id": 5,  "type": "WITHDRAWAL", "link_uuid": null, ... },
      "to_tx":   { "id": 6,  "type": "DEPOSIT",    "link_uuid": null, ... }
    },
    {
      "from_tx": { "id": 12, "type": "ADJUSTMENT",  "link_uuid": null, ... },
      "to_tx":   { "id": 13, "type": "ADJUSTMENT",  "link_uuid": null, ... }
    }
  ]
}
```

**Promote (bulk)** — esempio: 2 coppie promosse in un'unica chiamata:
```
POST /api/v1/transactions/promote
Body:
{
  "items": [
    { "id_a": 5, "id_b": 6 },      ← WITHDRAWAL + DEPOSIT → CASH_TRANSFER
    { "id_a": 12, "id_b": 13 }     ← ADJUSTMENT + ADJUSTMENT → TRANSFER
  ]
}

Response 200:
{
  "results": [
    {
      "pair_a": { "id": 5,  "type": "CASH_TRANSFER", "link_uuid": "abc-...", ... },
      "pair_b": { "id": 6,  "type": "CASH_TRANSFER", "link_uuid": "abc-...", ... }
    },
    {
      "pair_a": { "id": 12, "type": "TRANSFER", "link_uuid": "def-...", ... },
      "pair_b": { "id": 13, "type": "TRANSFER", "link_uuid": "def-...", ... }
    }
  ]
}
```

**Errore per-item** (es. id non ha partner):
```
Response 422:
{
  "detail": [
    { "index": 0, "error": "Transaction 5 has no link_uuid — cannot split" },
    { "index": 1, "ok": true }
  ]
}
```

---

### Metadata server-driven — Split/Promote rules nella response `/types`

```
GET /api/v1/transactions/types

Response (excerpt for CASH_TRANSFER):
{
  "code": "CASH_TRANSFER",
  "name": "Cash Transfer",
  "requires_link": true,
  "pair_form_layout": "transfer_cash",
  "asset_mode": "forbidden",
  "cash_mode": "required",
  "quantity_mode": "forbidden",
  ...
  "split_into": {
    "from_type": "WITHDRAWAL",
    "to_type": "DEPOSIT"
  },
  "promote_from": [
    {
      "type_a": "WITHDRAWAL",
      "type_b": "DEPOSIT",
      "field_constraints": [
        { "field": "cash_currency", "relation": "equal" },
        { "field": "broker_id",     "relation": "different" },
        { "field": "cash_amount",   "relation": "opposite" }
      ]
    }
  ],
  "pair_field_constraints": [
    { "field": "cash_currency", "relation": "equal" },
    { "field": "broker_id",     "relation": "different" },
    { "field": "cash_amount",   "relation": "opposite" }
  ]
}
```

**Frontend usage flow**:
```
  User selects 2 rows
         │
         ▼
  Frontend scans all types where promote_from ≠ null
         │
         ▼
  For each promote_from rule:
    type_a matches row1.type AND type_b matches row2.type?
    (or vice versa)
         │
    YES  │  NO
    ▼    │  → try next rule
  Check field_constraints:
    cash_currency equal? ✓
    broker_id different? ✓
    cash_amount opposite? ✓
         │
    ALL PASS → enable 🔗 button, show target pair type
    ANY FAIL → 🔗 disabled, tooltip shows which constraint failed
```

---

## ✅ Checklist

### Batch 1 (done)
- [x] B1-1 (W32): FormModal dual trigger only when requiresPair
- [x] B1-2 (W34): Backend WITHDRAWAL↔DEPOSIT pair validation (→ superseded by CASH_TRANSFER)
- [x] B1-3 (W35): Translate typeA/typeB in errors
- [x] B1-4 (W36): Lucide arrows + swap
- [x] B1-5 (W37): Filter brokers dual sides
- [x] B1-7 (W39): Add broker/asset quicklinks (→ superseded by B1-11)

### Batch 2
- [x] B1-8 (W40): Backend `CASH_TRANSFER` type + metadata + migration
- [x] B1-8b: Frontend `collectDualCreates` → CASH_TRANSFER+CASH_TRANSFER
- [x] B1-9 (W41): Type editable in create dual mode
- [x] B1-10 (W42): Deduplicate errors + fix qty propagation
- [x] B1-11 (W43/W44): "Create new" dropdown footer in SearchSelect
- [x] B1-12 (W45): z-index stacked modals
- [x] B1-13 (W46): BulkModal paired row rendering (Da:/A: double-height)
- [x] B1-14 (W47-W50): i18n + cost basis tooltip + doc link + createNew key
- [x] B1-15 (W51): Split/Promote server-driven metadata (schemas + api sync)
- [x] B1-16 (W52): Bulk Split/Promote endpoints + service logic
- [x] B1-17 (W53): Remove PromotePairWizardModal → selection-based promote

---

## 🔍 Review Fixes (Post-Batch 2)

**Date**: 2026-05-01
**Trigger**: Manual testing by user after Batch 2 commit

### R1 — Dual type dropdown locks out normal types
**Symptom**: After selecting a paired type (TRANSFER, FX_CONVERSION, CASH_TRANSFER), user cannot switch back to a normal type (BUY, SELL, etc.) because the dropdown only shows pair types.
**Root cause**: `filterPairOnly={true}` hardcoded on `TransactionTypeSearchSelect` in dual template (L1220).
**Fix**: Removed `filterPairOnly={true}`. All types visible. Selecting a non-pair type auto-exits dual mode via existing `setType()` → `pairLayout` recalculation.
**File**: `TransactionFormModal.svelte`

### R2 — CASH_TRANSFER missing icon
**Symptom**: No icon displayed for Cash Transfer type in dropdowns and table.
**Root cause**: `icon_slug="cash-transfer"` in backend metadata, but `cash-transfer.png` didn't exist in `frontend/static/icons/transactions/`.
**Fix**: Copied `transfer.png` → `cash-transfer.png` as placeholder. TODO: create dedicated icon.
**File**: `frontend/static/icons/transactions/cash-transfer.png`

### R3 — "Transfer" name ambiguous (asset vs cash)
**Symptom**: With CASH_TRANSFER added, "Transfer" alone is confusing — which kind?
**Fix**: Renamed to "Asset Transfer" in backend metadata (`name="Asset Transfer"`) and all 4 i18n locales (`transactions.types.TRANSFER`).
**Files**: `backend/app/schemas/transactions.py`, `frontend/src/lib/i18n/{en,it,fr,es}.json`

### R4 — FX_CONVERSION shows Da:/A: on broker column (wrong)
**Symptom**: FX_CONVERSION paired row in BulkModal shows `Da: IBKR / A: IBKR` in broker column — same broker twice with Da:/A: labels, confusing.
**Root cause**: Broker cell condition was `rule.requiresPair && row.partnerBrokerId != null` — true for FX too. But for FX, `pair_field_constraints` has `broker_id: equal`, so both brokers are the same.
**Fix**: Added `&& row.partnerBrokerId !== row.broker_id` — Da:/A: only when brokers differ (TRANSFER, CASH_TRANSFER). FX falls through to normal single-broker display.
**File**: `TransactionBulkModal.svelte`

### R5 — "Add asset" button outside dropdown
**Symptom**: `+ Add asset` link appears below the AssetSelect, not inside the dropdown like BrokerSearchSelect's `+ New broker` footer.
**Fix**: Added `createLabel` and `onCreateNew` props to `AssetSelect.svelte` (passthrough to `SearchSelect`). Updated `TransactionFormModal.svelte` to use these props (both standard and dual templates), removed old inline `<button>`.
**Files**: `AssetSelect.svelte`, `TransactionFormModal.svelte`

