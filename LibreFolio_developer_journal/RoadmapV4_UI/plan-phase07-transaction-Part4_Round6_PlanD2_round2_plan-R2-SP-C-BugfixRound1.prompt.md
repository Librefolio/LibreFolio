# Plan: SP-C Bugfix Round 1 — Rientro 12 Bug Walktest

> **✅ STATUS (2026-05-24)**: COMPLETATO (12/12).

**Parent plan**: [`plan-R2-SP-C-BulkModalSuggestUX`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BulkModalSuggestUX.prompt.md)
**Depends on**: SP-C completato (tutti gli step 1-10 eseguiti)
**Triggered by**: Walktest 2026-05-16 — 6 passed, 11 bug identificati + 1 bug scoperto durante debug (BUG-C12)

## Context

Bugfix per i 12 bug emersi dal walktest SP-C + debug session. File principale: `TransactionBulkModal.svelte` (~2494 righe). Touch secondari su `TransactionActionModal.svelte`, `PromoteMergeModal.svelte`, `TransactionFormModal.svelte`, `DataTableColumnFilter.svelte`, `TransactionPickerModal.svelte`.

## Key files to read first

- `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` — BulkModal (commit, validate, split, suggest, columns)
- `frontend/src/lib/components/transactions/TransactionActionModal.svelte` — Split/Promote confirmation modal
- `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` — Merge UI for divergent fields
- `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — FormModal (cost_basis_override field)
- `frontend/src/lib/components/transactions/TransactionPickerModal.svelte` — Picker (includeIds prop needed)
- `frontend/src/lib/components/table/DataTableColumnFilter.svelte` — Column filter (integer step)
- `backend/app/services/transaction_service.py` — execute_batch order (splits at 3b, updates at 4)
- `backend/app/schemas/transactions.py` — TXSplitBatchItem (extra="forbid")

## Bug Classification

### Classe A — Commit/Payload Logic (CRITICO)
- **BUG-C3**: edits persi nel commit per righe split-queued
- **BUG-C12**: promote-suggest $effect manda amount/quantity senza segno → constraint `cash_amount=opposite` fallisce

### Classe B — Suggest Architecture (REDESIGN)
- **BUG-C7**: suggest mostra candidati DB come azioni dirette (architetturalmente sbagliato)
- **BUG-C10**: suggest non rileva coppia dopo edit locale

### Classe C — UX/Layout (quick fixes)
- **BUG-C1**: partner row aggiunta in fondo (non adiacente)
- **BUG-C2**: Reset All non annulla split
- **BUG-C4**: preview tipo partner formato vecchio dopo edit
- **BUG-C5**: ActionModal non scrolla, footer irraggiungibile
- **BUG-C6**: numeri non formattati (trailing zeros) in ActionModal
- **BUG-C8**: frecce invertite + concat con label in PromoteMergeModal
- **BUG-C11**: filtro colonna ID permette decimali

### Classe D — FormModal Currency
- **BUG-C9**: cost_basis_override campo mancante formato Currency nel FormModal

## Steps

### Step 1: BUG-C3 (P0 — Commit perde edits di righe split-queued)

**File**: `TransactionBulkModal.svelte`

Il commit (riga 1028) e il validate (riga 866) fanno `continue` su righe split-queued:
```typescript
// Riga 866 (validate) e 1028 (commit):
if (d.op === 'edit' && splitTxIds.has((d as any).txId)) continue;
```

Il backend esegue splits al passo 3b, updates al passo 4 (`transaction_service.py` riga 1158→1238) → l'ordine è corretto: l'update arriva su TX già splittata.

**Fix**: NON skippare se `deriveStatus(d) === 'edited'` — aggiungerla agli `updates[]`:
```typescript
// Skip split-queued edit rows ONLY if unchanged
if (d.op === 'edit' && splitTxIds.has((d as any).txId)) {
    const st = deriveStatus(d);
    if (st !== 'edited') continue;
    // If edited, fall through to process as update
}
```

`collectUpdate(d)` diffara `fields.type` (ADJUSTMENT) vs originale txStore (TRANSFER) → diff non vuoto → status `'edited'`. Applicare la stessa logica in entrambi i punti (validate + commit).

### Step 2: BUG-C4 + C1 (P2 — Preview partner tipo + posizionamento adiacente)

**File**: `TransactionBulkModal.svelte`

#### 2a. BUG-C4 — Root cause confermata

Dopo edit via FormModal:
1. `fields.type` diventa `ADJUSTMENT` (tramite `patchRowFromForm` → `applyFormPayload`)
2. Colonna type: `SPLIT_TYPE_MAP['ADJUSTMENT']` → `undefined` → fallback vecchio formato

**Fix**: Estendere la shape **client-side** di `pendingSplits` da `{id_a, id_b}` a `{id_a, id_b, originalType}`:

```typescript
// Riga 223: type definition
let pendingSplits = $state<{id_a: number; id_b: number; originalType: string}[]>([]);
```

In `handleSplitRow` (riga 662):
```typescript
pendingSplits = [...pendingSplits, {id_a: txId, id_b: partnerId, originalType: row.fields.type}];
```

Nella colonna type (riga 1249), recuperare `originalType`:
```typescript
if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId)) {
    const splitEntry = pendingSplits.find(s => s.id_a === (row as any).txId || s.id_b === (row as any).txId);
    const origType = splitEntry?.originalType ?? row.fields.type;
    const splitTypes = SPLIT_TYPE_MAP[origType];
    // ... rest of logic using splitTypes
}
```

Stesso fix per `openEditRowForm` (riga 1675):
```typescript
if (row.op === 'edit' && splitTxIdsSet.has((row as any).txId) && formInitial) {
    const splitEntry = pendingSplits.find(s => s.id_a === (row as any).txId || s.id_b === (row as any).txId);
    const origType = splitEntry?.originalType ?? row.fields.type;
    const splitTypes = SPLIT_TYPE_MAP[origType];
    // ...
}
```

Nel commit payload (riga 1064), inviare solo `{id_a, id_b}` (backend ha `extra="forbid"`):
```typescript
if (pendingSplits.length > 0) payload.splits = pendingSplits.map(s => ({id_a: s.id_a, id_b: s.id_b}));
```

#### 2b. BUG-C1 — Posizionamento partner

In `handleSplitRow` (riga 680), `ops = [...ops, partnerOp]` aggiunge in fondo.

**Fix**: inserire adiacente:
```typescript
const mainIdx = ops.findIndex(o => o.tempId === row.tempId);
const newOps = [...ops];
newOps.splice(mainIdx + 1, 0, partnerOp);
ops = newOps;
```

### Step 3: BUG-C2 (P2 — Reset All non annulla split)

**File**: `TransactionBulkModal.svelte`

#### 3a. Marcare partner ops aggiunte dallo split

In `handleSplitRow` (riga 674), marcare:
```typescript
const partnerOp = editOpFromTx(partnerId);
(partnerOp as any).addedBySplit = true;
```

#### 3b. `resetAll()` annulla anche gli split

```typescript
function resetAll() {
    // Remove partner rows added by split
    ops = ops.filter(d => !(d as any).addedBySplit);
    // Reset remaining edit rows to original state
    ops = ops.map((d) => {
        if (d.op !== 'edit') return d;
        const reset = editOpFromTx(d.txId, {addedViaPicker: d.addedViaPicker});
        populatePartnerDisplay(reset);
        return reset;
    });
    // Clear split state
    pendingSplits = [];
}
```

#### 3c. Condizione visibilità del bottone

Riga 2323: aggiungere `|| pendingSplits.length > 0`:
```svelte
{#if visibleOps.some((d) => d.op === 'edit' && (deriveStatus(d) === 'edited' || deriveStatus(d) === 'delete')) || pendingSplits.length > 0}
```

### Step 4: BUG-C7 + C10 (P1 — Suggest redesign architetturale)

**File**: `TransactionBulkModal.svelte`, `TransactionPickerModal.svelte`

#### 4a. Fields correnti nell'$effect (fix C10)

L'`$effect` (riga 1925) già usa `o.fields.*` (non txStore). Verificare che un edit locale invalidi `lastSuggestKey`:
- `patchRowFromForm` (riga 581) fa `ops = ops.map(...)` che cambia il riferimento `ops`
- L'`$effect` traccia `ops` → si riattiva → computa nuovo `key` → diverso da `lastSuggestKey` → riscatena la call ✅

Ma c'è un bug sottile: l'`$effect` filtra solo `editStandalone` (righe senza `partnerId`). Dopo `handleSplitRow`, la riga principale ha `partnerId = undefined` → viene inclusa ✅. La partner row anche ha `partnerId = undefined` → inclusa ✅.

Problema: se l'utente **non** ha editato ma solo importato una TX suggerita dal picker, la TX era già nei `fields` prima (dal txStore) → il `key` non cambia → nessun re-trigger. Fix: aggiungere `lastSuggestKey = ''` in `handlePickerAdd` (riga 1622), come già fatto altrove.

#### 4b. Separare allSuggestions in banner + importable

Riga 1999, sostituire `allSuggestions` con due derived:

```typescript
/** Banner suggestions: only pairs where BOTH TX are in ops[] */
let bannerSuggestions = $derived.by(() => {
    const combined: Array<{...}> = [];
    // Local new+new (entrambe già in ops per definizione)
    for (const s of localSuggestions) combined.push(s);
    // DB suggestions where the candidate IS already in ops
    const opsEditIds = new Set(ops.filter(o => o.op === 'edit').map(o => (o as any).txId as number));
    for (const [txId, candidates] of suggestFromDB) {
        const op = ops.find((o) => o.op === 'edit' && (o as any).txId === txId);
        if (!op || !candidates.length) continue;
        for (const cand of candidates) {
            if (!opsEditIds.has(cand.id)) continue; // Only if candidate is IN ops
            // ... build suggestion entry (same as current allSuggestions logic)
        }
    }
    return combined;
});

/** Importable suggestions: DB candidates NOT yet in ops (for 💡 button) */
let importableSuggestions = $derived.by(() => {
    const result: Array<{txId: number; tempId: string; candidates: Array<{id: number; type: string; broker_id: number; date: string}>}> = [];
    const opsEditIds = new Set(ops.filter(o => o.op === 'edit').map(o => (o as any).txId as number));
    for (const [txId, candidates] of suggestFromDB) {
        const op = ops.find((o) => o.op === 'edit' && (o as any).txId === txId);
        if (!op) return;
        const importable = candidates.filter(c => !opsEditIds.has(c.id));
        if (importable.length > 0) {
            result.push({txId, tempId: op.tempId, candidates: importable});
        }
    }
    return result;
});
```

#### 4c. Banner mostra solo bannerSuggestions

Riga 2238: cambiare da `allSuggestions` a `bannerSuggestions`:
```svelte
{#if bannerSuggestions.length > 0}
    <!-- banner content iterates bannerSuggestions -->
{/if}
```

#### 4d. Bottone 💡 — PickerModal con includeIds

**Toolbar** (right group): aggiungere bottone 💡globale se `importableSuggestions.length > 0`:
```svelte
{#if importableSuggestions.length > 0}
    <button type="button" class="..." onclick={openSuggestPicker} data-testid="tx-bulk-suggest-import" title={$t('transactions.bulk.suggestLightbulb')}>
        <Lightbulb size={14} class="text-amber-500" />
        <span class="text-[10px]">{importableSuggestions.reduce((n, s) => n + s.candidates.length, 0)}</span>
    </button>
{/if}
```

**PickerModal**: aggiungere prop `includeIds?: Set<number>` a `TransactionPickerModal.svelte`:
```typescript
interface Props {
    open: boolean;
    excludeIds: Set<number>;
    includeIds?: Set<number>;  // NEW: when set, show ONLY these IDs
    onAdd: (rows: TXReadItem[]) => void;
    onClose: () => void;
}
```

In `filteredMain` (riga 44):
```typescript
let filteredMain = $derived(
    allRows.filter((r) => !excludeIds.has(r.id) && (includeIds == null || includeIds.has(r.id)))
);
```

**BulkModal**: variabili per il suggest picker:
```typescript
let suggestPickerOpen = $state(false);
let suggestPickerIncludeIds = $derived(
    new Set(importableSuggestions.flatMap(s => s.candidates.map(c => c.id)))
);

function openSuggestPicker() {
    suggestPickerOpen = true;
}
```

Secondo `<TransactionPickerModal>` instance (o riusare la stessa con flag):
```svelte
<TransactionPickerModal open={suggestPickerOpen} excludeIds={pickerExcludeIds} includeIds={suggestPickerIncludeIds} onAdd={handlePickerAdd} onClose={() => (suggestPickerOpen = false)} />
```

**💡 per-row**: nell'array `rowActions`, aggiornare la condizione del lightbulb action (riga 1510 area) per usare `importableSuggestions` anziché `allSuggestions`. onClick: aprire il picker con `includeIds` filtrato ai soli candidati di QUELLA riga.

#### 4e. Auto-update dopo import

Già gestito: `handlePickerAdd` aggiunge righe a `ops[]` → `$effect` ricalcola → `suggestFromDB` riesegue (via `lastSuggestKey = ''` — da aggiungere in `handlePickerAdd`) → candidato ora in griglia → appare in `bannerSuggestions`.

### Step 5: BUG-C5 + C6 + C8 (P2 — Modal polish)

#### 5a. BUG-C5 — ActionModal non scrolla

**File**: `TransactionActionModal.svelte`

Aggiungere `overflow-y-auto max-h-[80vh]` al div wrapper interno (il primo child di ModalBase):
```svelte
<ModalBase {open} ...>
    <div class="p-5 space-y-4 overflow-y-auto max-h-[80vh]">
        <!-- existing content -->
    </div>
</ModalBase>
```

#### 5b. BUG-C6 — Numeri non formattati

**File**: `TransactionActionModal.svelte`

Per quantity nelle tabelle BEFORE (riga 146) e AFTER (riga 216), formattare con trailing zeros removal:
```typescript
function fQ(qty: string | null | undefined): string {
    if (qty == null || qty === '') return '—';
    const n = parseFloat(qty);
    return isNaN(n) ? qty : n.toString();
}
```

Usare `{fQ(transaction.quantity)}` e `{fQ(partner?.quantity)}` al posto di `{transaction.quantity ?? '—'}`.

#### 5c. BUG-C8 — Frecce invertite PromoteMergeModal

**File**: `PromoteMergeModal.svelte`

Localizzare il div con i bottoni globali (dopo `hasDifferences` check). Cambiare:
- Frecce: `▶ All Left` (freccia punta al centro) e `All Right ◀` (freccia punta al centro)
- Concat: solo `↔` senza label testuale
- Layout: `justify-between` per posizionare sui bordi

```svelte
<div class="flex items-center justify-between mt-3 mb-1">
    <button type="button" class="..." onclick={allLeft}>
        ▶ {$t('transactions.promote.allLeft')}
    </button>
    <button type="button" class="..." onclick={allMerge} title={$t('transactions.promote.merge')}>
        ↔
    </button>
    <button type="button" class="..." onclick={allRight}>
        {$t('transactions.promote.allRight')} ◀
    </button>
</div>
```

### Step 6: BUG-C9 (P2 — FormModal cost_basis_override Currency)

**File**: `TransactionFormModal.svelte`

#### 6a. Draft shape

Da `cost_basis_override: string` a due campi interni:
```typescript
interface FormDraft {
    // ...existing fields...
    cost_basis_amount: string;   // numeric amount (empty = auto)
    cost_basis_code: string;     // currency code (default from TX/asset currency)
}
```

In `draftFromTx` (riga 232):
```typescript
cost_basis_amount: (() => {
    const cbo = tx.cost_basis_override;
    if (!cbo) return '';
    if (typeof cbo === 'object' && cbo !== null) return String((cbo as any).amount ?? '');
    // Legacy string "42.50 EUR" → parse
    const parts = String(cbo).trim().split(/\s+/);
    return parts[0] ?? '';
})(),
cost_basis_code: (() => {
    const cbo = tx.cost_basis_override;
    if (!cbo) return tx.cash?.code ?? '';
    if (typeof cbo === 'object' && cbo !== null) return String((cbo as any).code ?? tx.cash?.code ?? '');
    const parts = String(cbo).trim().split(/\s+/);
    return parts[1] ?? tx.cash?.code ?? '';
})(),
```

In `emptyDraft()`:
```typescript
cost_basis_amount: '',
cost_basis_code: '',
```

#### 6b. UI field

Riga 1885-1900, sostituire con:
```svelte
{#if showCostBasisField}
    <label class="flex items-center gap-2">
        <span class="text-xs text-gray-500 dark:text-gray-400 w-32 shrink-0">{$t('transactions.form.costBasis')}</span>
        <div class="flex-1 flex items-center gap-1">
            <input
                type="number"
                step="any"
                inputmode="decimal"
                autocomplete="off"
                class="flex-1 px-3 py-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 rounded-lg disabled:opacity-60"
                placeholder="auto"
                value={draft.cost_basis_amount}
                disabled={isReadonly}
                oninput={(e) => { draft = {...draft, cost_basis_amount: (e.currentTarget as HTMLInputElement).value}; }}
                data-testid="tx-form-cost-basis-amount"
            />
            <span class="text-xs text-gray-500 dark:text-gray-400 font-mono px-2 py-2 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg" data-testid="tx-form-cost-basis-code">
                {draft.cost_basis_code || '—'}
            </span>
        </div>
    </label>
{/if}
```

La currency code è readonly — ereditata dalla valuta della TX (`draft.cash?.code`). Se l'utente cambia la valuta cash, aggiornare anche `cost_basis_code` nell'`$effect` che gestisce i cambi di tipo/valuta.

#### 6c. buildPayload

Righe 855/928, assemblare come Currency object:
```typescript
// Single mode (riga 855):
cost_basis_override: draft.cost_basis_amount.trim()
    ? {code: draft.cost_basis_code || draft.cash?.code || '', amount: draft.cost_basis_amount.trim()}
    : null,

// Dual mode (riga 928):
if (draft.cost_basis_amount.trim()) {
    toItem.cost_basis_override = {code: draft.cost_basis_code || draft.cash?.code || '', amount: draft.cost_basis_amount.trim()};
}
```

#### 6d. BulkModal applyFormPayload

In `TransactionBulkModal.svelte` riga 600, adattare `cost_basis_override` handling:
```typescript
// In applyFormPayload:
target.cost_basis_override = typeof p.cost_basis_override === 'object' && p.cost_basis_override !== null
    ? `${(p.cost_basis_override as any).amount} ${(p.cost_basis_override as any).code}`
    : typeof p.cost_basis_override === 'string' ? p.cost_basis_override : '';
```

### Step 7: BUG-C11 (P3 — Filtro ID decimali)

**File**: `DataTableColumnFilter.svelte`

Per colonne numeriche dove tutti i valori sono interi (floor === value), aggiungere `step="1"` sugli input number/range. Aggiungere una prop o auto-detect:

```typescript
// Derive if column values are all integers
let isIntegerColumn = $derived(
    numericValues.length > 0 && numericValues.every(v => Math.floor(v) === v)
);
```

Sugli `<input type="number">` e `<input type="range">`:
```svelte
<input type="number" step={isIntegerColumn ? "1" : "any"} ... />
```

## Execution Checklist

- [x] Step 1: BUG-C3 — commit + validate skip logic (P0)
- [x] Step 2a: BUG-C4 — pendingSplits.originalType + colonna type + openEditRowForm
- [x] Step 2b: BUG-C1 — splice partner adiacente
- [x] Step 3: BUG-C2 — resetAll annulla split + visibilità bottone
- [x] Step 4a: BUG-C10 — lastSuggestKey invalidation in handlePickerAdd
- [x] Step 4b: BUG-C7 — bannerSuggestions + importableSuggestions derived
- [x] Step 4c: BUG-C7 — banner usa bannerSuggestions
- [x] Step 4d: BUG-C7 — 💡 button + PickerModal includeIds prop
- [x] Step 4e: BUG-C7 — auto-update verify
- [x] Step 5a: BUG-C5 — ActionModal overflow-y-auto
- [x] Step 5b: BUG-C6 — quantity formatting fQ()
- [x] Step 5c: BUG-C8 — frecce invertite + justify-between
- [x] Step 6: BUG-C9 — FormModal cost_basis Currency (CompactCashCell)
- [x] Step 7: BUG-C11 — DataTableColumnFilter integer step
- [x] Step 8: BUG-C12 — promote-suggest $effect applySignRules (P0)
- [x] Walktest finale: tutti i 12 bug risolti ✅ (2026-05-19)
- [x] Backend suggest: verified working (see debug test `/tmp/libreFolio_test_suggest_debug.py`)
- [x] `./dev.py test front-transaction tx-bulk-suggest-ux` → verde ✅ (2026-05-18)
- [x] `./dev.py test front-transaction tx-split-promote` → verde (NR) ✅ (2026-05-18)
- [x] `./dev.py test front-transaction tx-bulk-operations` → verde (NR) ✅ (2026-05-18)
- [x] All 14 transaction E2E suites green (2026-05-18) — FxImpliedRateSpread child plan also passes

## Deviations from plan

1. **Step 6 (BUG-C9)**: instead of keeping `cost_basis_override` as a string internally and serializing/deserializing, we fully migrated to `{code: string; amount: string} | null` across `FormDraft`, `DraftFields` (BulkModal), `TxFields` and `TxOriginal` (txPayloadHelpers.ts). Replaced the raw `<input type="number">` with `CompactCashCell` component (same as `cash` field). This is the correct architecture — consistent with how cash amounts are handled.

2. **Step 2 (BUG-C4)**: also updated the split payload mapping in commit (`pendingSplits.map(s => ({id_a: s.id_a, id_b: s.id_b}))`) to strip the `originalType` field before sending to backend (which has `extra="forbid"` on `TXSplitBatchItem`).

3. **Step 3 (BUG-C2)**: added `addedBySplit: true` flag on partner ops created by `handleSplitRow`. `resetAll()` now first removes addedBySplit ops, then resets remaining. Also clears `pendingSplits`.

4. **Step 4 (BUG-C7)**: reused the existing `handlePickerAdd` for both picker instances (suggest + normal). The suggest picker passes `includeIds` to filter to only suggested candidates. Added `suggestPickerOpen` state separately from `pickerOpen`.

5. **Step 4b (BUG-C7) — bannerSuggestions redesign**: the original implementation relied on `suggestFromDB` (backend response) for edit-op pairing, which broke when both candidates were in the input set (backend excludes all input IDs from results). Redesigned `bannerSuggestions` to use **local matching** via `findPromoteMatch()` — iterates all standalone edit ops in the grid and checks promote compatibility (same logic as `localSuggestions` for new ops). This makes the banner fully independent of backend suggest — it persists as long as both TX are in the grid and are compatible. The backend `promote-suggest` endpoint now serves a narrower role: finding candidates that exist in DB but are NOT yet in the grid (surfaced via the 💡 importable button + PickerModal with `includeIds`).

   **Architecture after fix**:
   - `bannerSuggestions`: LOCAL matching among ALL ops in the grid (new+edit). Uses `findPromoteMatch()`. Always up-to-date.
   - `importableSuggestions` (💡 button): DB candidates NOT in grid. Derived from `suggestFromDB` response.
   - Backend `promote-suggest`: only useful for discovering off-grid candidates. Empty result for inputs that pair with each other is CORRECT behavior (local handles it).

6. **Backend suggest "bug" clarification**: the user observed `{"results":{"38":[],"39":[],"42":[]}}` when sending 3 TX (two ADJUSTMENT + one WITHDRAWAL). This is CORRECT:
   - TX 38+39 (ADJUSTMENT, same asset, different brokers): excluded from each other because both are in `input_positive_ids`. Local `bannerSuggestions` detects them ✓
   - TX 42 (WITHDRAWAL): no matching standalone DEPOSIT was in DB at call time. After user manually added TX 43 (DEPOSIT), local banner detected it ✓
   - Design: backend = off-grid discovery; frontend = in-grid pairing.
   - **Verified with debug test** (`/tmp/libreFolio_test_suggest_debug.py`): after clean test DB populate, TX 42 correctly finds TX 43, TX 49 finds TX 50+54, TX 46 finds TX 47. All constraints pass.

7. **Added suggest-discover test data** in `populate_mock_data.py`: 3 pairs of standalone TX tagged `suggest-discover` (with sub-tags `suggest-discover-loaded` and `suggest-discover-hidden`) to test the backend suggest → 💡 import flow:
   - Pair A: Cash Transfer W#49 (IB/loaded) ↔ D#50 (Directa/hidden)
   - Pair B: Asset Transfer Adj-#51 (Coinbase/loaded) ↔ Adj+#52 (IB/hidden)
   - Pair C: FX Conversion W#53 (IB-EUR/loaded) ↔ D#54 (IB-USD/hidden)
   - Plus pre-fund deposit #48 (balance-safe).

8. **BUG-C12 (P0): promote-suggest $effect sent unsigned amount/quantity** — `fieldsFromTx()` strips the sign from `cash.amount` for UX editing (WITHDRAWAL -500 → displays as 500). But the `$effect` sent `fields.cash.amount` raw (positive 500) to the backend. The `cash_amount=opposite` constraint then failed: `500 != -(+500)`. Fix: use `applySignRules()` in the $effect to re-apply sign rules before sending. This also fixes quantity for SELL type (quantityRule='negative'). Import added: `applySignRules` from `txPayloadHelpers.ts`.

9. **WT-C3 walktest discovered deeper BUG-C3 root cause** — The original Step 1 fix (skip split-queued only if `st !== 'edited'`) was incomplete. Three issues found:
   - **`type` leak in update**: `collectUpdate()` diffs `fields.type` (ADJUSTMENT, set by FormModal) vs original (TRANSFER), always producing a `type` diff. Backend rejects with "Cannot change type from TRANSFER to ADJUSTMENT" because type-change should come from split, not update.
   - **`deriveStatus` always returned 'edited'**: Since `fields.type` was always different for split-queued rows, they were NEVER skipped (even when user made no real edits).
   - **Validate payload missing splits**: The validate function didn't include `splits` in its payload, so backend couldn't execute split before checking the update.
   
   **Fix** (3 parts):
   1. `deriveStatus`: after computing diff, if row is in `pendingSplits` → `delete diff.type` before checking length
   2. Validate + commit loops: after `collectUpdate(d)`, if row is split-queued → `delete upd.type`
   3. Validate payload: add `if (pendingSplits.length > 0) payload.splits = ...` (same as commit)
   
   **E2E test added**: `tx-split-promote.spec.ts` now has "C3: Split + edit quantity → commit payload has splits + updates without type" — verifies payload structure and absence of "Cannot change type" error.
   
   **Quantity column trailing zeros**: also fixed BulkModal quantity column (was showing `-0.001000`, now shows `-0.001`) using `parseFloat(qty).toString()`.

10. **BUG-C3b: Mock data balance issue** — The `delete-safe` TX pair (Asset Transfer on Coinbase, broker 5) causes `balanceAssetNegative` when split is committed because Coinbase doesn't have enough Apple Inc. shares to cover the split. The split splits a TRANSFER into two ADJUSTMENT rows, but the balance walk fails. Fix: add a covering BUY TX for Apple on Coinbase in `populate_mock_data.py` before the delete-safe pair date.

11. **PromoteMergeModal tag badges not colored** — Tag badges in the left/right selection buttons had CSS custom properties set (via `getStringBadgeStyle`) but no CSS rule consuming them (unlike `TagInput` which has `.tag-chip` scoped style). Fix: added `.merge-tag-badge` class + `<style>` block in `PromoteMergeModal.svelte`. Also improved `hashString()` in `colors.ts` (djb2 + XOR-fold) to produce more distinct hues for strings with shared prefixes (e.g. `suggest-discover-hidden` vs `suggest-discover-loaded`).

12. **Promote button missing from main table toolbar** — `findPromoteMatch()` uses `_cache` from `transactionTypeStore`, which was only loaded inside BulkModal/FormModal (`ensureTypesLoaded()`). The page never called it, so `_cache` was always null → `promoteMatch` always null → button never shown. Fix: added `ensureTypesLoaded()` to page's `onMount` Promise.all + `void $typesVersion` dependency in `$derived.by` to re-evaluate when cache populates.

13. **C5/C6 walktest refinements** — Multiple UX improvements during walktest:
    - **ActionModal sticky header/footer**: restructured from single scrollable div to `flex flex-col max-h-[80vh]` with header (shrink-0 + border-b), scrollable body (overflow-y-auto flex-1 min-h-0), sticky footer (shrink-0 + border-t).
    - **PromoteMergeModal sticky layout + dirty guard**: same structure applied. Added `interacted` flag set by ALL per-field buttons (left/right/concat/union) and global buttons (allLeft/allMerge/allRight). `dirty = interacted || snapshot differs`. Reset on open.
    - **AFTER table row order**: aligned BEFORE/AFTER to same order (date → type → quantity → cash → broker → tags → desc). Was type-first in AFTER.
    - **i18n `standalone` → plural**: IT "Indipendenti", FR "Indépendantes", ES "Independientes". EN invariant.
    - **Tag badges in ActionModal**: replaced `tags.join(', ')` (6 occurrences) with colored badge rendering via `getStringBadgeStyle` + `.action-tag-badge` scoped CSS.
    - **Quantity emoji + zero handling**: `fQ` replaced with `formatTxQuantity` from shared helper — shows `+n 📈` / `-n 📉` / `—` for null/0.

14. **Created `txDisplayHelpers.ts`** — Extracted shared formatting logic into `frontend/src/lib/components/transactions/txDisplayHelpers.ts`:
    - `formatTxQuantity(qty)` — unified quantity display (emoji, sign, — for zero)
    - `formatTxCash(cash)` — unified cash display (formatted with sign, — for null)
    - Consumed by: `TransactionActionModal`, `TransactionDeleteModal`, `TransactionsTable`
    - Eliminates 3 redundant local `fQ`/`fC`/`formatQty` implementations.

15. **BUG-C9 walktest fixes** — Multiple issues found during WT-C9:
    - **ADJUSTMENT field hidden**: `showAdvancedSection` didn't include ADJUSTMENT → field was gated behind invisible `<details>`. Fix: added `|| draft.type === 'ADJUSTMENT'`.
    - **Dual mode TRANSFER tooltip missing**: the dual-form variant of cost_basis had plain `<span>` label without info icon. Fix: added `<Tooltip>` with `costBasisOverride.tooltip` text.
    - **Used `title` instead of `<Tooltip>`**: replaced native title attribute with proper `<Tooltip>` component for both dual and single form variants.
    - **Empty amount sent to backend**: `cost_basis_override: {amount: "", code: "EUR"}` caused "Cannot convert '' to Decimal". Fix: `draftToTxFields()` normalizes empty amount to `null`; `collectDualCreates()` checks `amount?.trim()` before including.
    - **`asset_event_id` still a numbox for ADJUSTMENT**: noted as future improvement (not in C9 scope). Will be tracked separately.

## Walktest Protocol (2026-05-18)

Prerequisiti: `./dev.py server --test --force` attivo su porta 8001. Login come `e2e_test_user`. Navigare a Transactions.

---

### WT-C3: Edits su righe split-queued persistono nel commit (P0)

**Precondizione**: avere una TX paired (es. Asset Transfer) nella tabella.

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Seleziona una TX paired (Asset Transfer) → click **Edit** (toolbar) | BulkModal si apre con la riga |
| 2 | Click **✂️ Split** sulla riga | Badge `✂️ split` appare; partner row appare sotto (adiacente) |
| 3 | Click **Edit** (pencil) sulla riga main (split-queued) | FormModal si apre con tipo target (es. ADJUSTMENT) |
| 4 | Cambia **description** → "WT-C3 test edit" → Salva | FormModal si chiude, riga mostra status `edited` (indicatore giallo) |
| 5 | Click **Validate** (se presente) o direttamente **Commit** | Il payload inviato deve includere BOTH `splits: [{id_a, id_b}]` AND `updates: [{id: ..., description: "WT-C3 test edit"}]` |
| 6 | Verifica risposta commit: `committed: true` | Toast success ✅ |
| 7 | Riapri la TX nella tabella → verifica description = "WT-C3 test edit" | Persiste ✅ |

**Pass criteria**: step 5-7 tutti verdi. Il commit NON deve restituire solo `splits` senza `updates`.

---

### WT-C12: Promote-suggest $effect segno corretto (P0)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Seleziona 2+ TX standalone compatibili per Cash Transfer (es. WITHDRAWAL + DEPOSIT, stesso broker, stesse date ±tolerance) → Edit | BulkModal si apre |
| 2 | Attendi 1-2s per il suggest $effect | Banner **"Promote to pair"** appare con le 2 TX |
| 3 | Click **🔗 Merge** nel banner | ActionModal o PromoteMergeModal si apre |
| 4 | Conferma promote | Nessun errore `cash_amount=opposite` — la constraint passa |
| 5 | Commit | `committed: true`, toast success |
| 6 | Verifica nella tabella: le 2 TX sono ora linked (icona link nella colonna pair) | Pair creato ✅ |

**Pass criteria**: step 4 non rigetta con errore di segno.

---

### WT-C7: Suggest mostra solo coppie in-grid + 💡 per import (P1)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Filtra tabella per tag `suggest-discover-loaded` → seleziona tutte → Edit | BulkModal con TX standalone |
| 2 | Attendi suggest | Banner suggest **NON** mostra candidati DB (es. "DB #50") — solo coppie dove ENTRAMBE le TX sono nella griglia |
| 3 | Verifica: se solo 1 TX di una coppia è in griglia, appare il bottone **💡** (lightbulb) nella toolbar o per-row | 💡 visibile con conteggio candidati |
| 4 | Click 💡 | PickerModal si apre, filtrato ai soli candidati suggeriti (es. mostra solo TX #50, #52, #54) |
| 5 | Importa una TX dal picker (es. #50) | TX aggiunta alla griglia; banner si aggiorna mostrando la coppia (#49 ↔ #50) |
| 6 | Verifica che il 💡 conteggio diminuisce (o scompare se era l'ultimo) | Aggiornamento ✅ |

**Pass criteria**: banner = solo local; 💡 = DB candidates; import → banner update.

---

### WT-C10: Suggest rileva coppia dopo edit locale (P1)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Importa 2 TX standalone nello stesso batch che NON sono compatibili (es. date distanti > tolerance) | Nessun banner suggest |
| 2 | Edita (FormModal) una TX: cambia la **data** per portarla entro il tolerance dell'altra | Banner suggest **appare** dopo il salvataggio FormModal |
| 3 | Inverso: edita per allontanare la data | Banner suggest **scompare** |

**Pass criteria**: il suggest è reattivo ai dati correnti, non solo ai valori originali.

---

### WT-C1: Partner row adiacente (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | BulkModal → seleziona TX paired → Split | Partner row appare **subito sotto** la riga main (non in fondo alla lista) |

---

### WT-C2: Reset All annulla split (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Split una riga → badge `✂️` appare + partner row aggiunta | — |
| 2 | Verifica: bottone **"Reimposta tutto"** è visibile | Visibile ✅ |
| 3 | Click Reset All | Badge split sparisce, partner row rimossa, `pendingSplits` vuoto |

---

### WT-C4: Preview tipo partner dopo edit (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Split una TX paired (es. TRANSFER) → ottieni 2 righe con tipo preview corretto | `[icona TRANSFER] → [icona ADJUSTMENT + label]` |
| 2 | Edita la riga main via FormModal (cambia description) → salva | — |
| 3 | Verifica colonna Type della riga main: ancora preview corretta | NON mostra "undefined" o tipo post-edit grezzo |
| 4 | Verifica colonna Type della partner row: stessa preview corretta (lato opposto) | ✅ |

---

### WT-C5: ActionModal scrolla (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Apri ActionModal (Split o Promote) su una TX con tags + description lunghi | — |
| 2 | Se il contenuto eccede il viewport | Modale **scrolla** verticalmente, footer sempre raggiungibile |

---

### WT-C6: Numeri formattati in ActionModal (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Apri ActionModal su una TX con quantity `10.000000` o `0.050000` | Mostra `10` e `0.05` (no trailing zeros) |

---

### WT-C8: Frecce PromoteMergeModal (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Promote 2 TX con campi divergenti (description diversa) → MergeModal si apre | — |
| 2 | Layout bottoni: `[All Left ▶]   [↔]   [◀ All Right]` | Frecce puntano verso il centro; ↔ senza testo; layout justify-between |

---

### WT-C9: cost_basis_override come Currency nel FormModal (P2)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Crea o edita una TX **TRANSFER** | Campo **Cost Basis** visibile |
| 2 | Verifica: ha input numerico + codice valuta (readonly, ereditato dalla valuta TX) | Format CompactCashCell ✅ |
| 3 | Inserisci valore (es. 42.50) → Commit | Toast success |
| 4 | Riapri la TX → cost basis = 42.50 + codice valuta | Persistito ✅ |
| 5 | Svuota cost basis → Commit → riapri | Mostra "auto" o vuoto (backend calcola WAC) |
| 6 | Crea/edita una TX **ADJUSTMENT** con qty positiva | Campo **Cost Basis** visibile + warning amber se vuoto |
| 7 | Edita una TX **BUY** | Campo Cost Basis **NON** visibile (costo = price×qty) |

---

### WT-C11: Filtro colonna ID solo interi (P3)

| # | Azione | Verifica |
|---|--------|----------|
| 1 | Tabella transazioni → apri filtro colonna ID | — |
| 2 | Input numerico ha `step=1` | Non permette decimali (42.5 impossibile) |
| 3 | Slider produce solo valori interi | ✅ |

---

### Walktest Results

| Bug | Status | Note |
|-----|--------|------|
| C3 | ✅ | Fixed: type stripped from split-queued updates, splits added to validate. E2E test added + mock data balanced. |
| C12 | ✅ | Merge modal worked, promote committed successfully. Minor fix: description concat button label + ⟷ symbol uniformed. |
| C7 | ✅ | Verified: banner shows only in-grid pairs; 💡 button shows DB candidates; import updates banner. |
| C10 | ✅ | Verified: suggest reacts to local edits (date change triggers/removes banner). |
| C1 | ✅ | Verified: partner row appears adjacent after split. |
| C2 | ✅ | Verified: Reset All removes split badge + partner row. |
| C4 | ✅ | Verified: type preview correct after edit. |
| C5 | ✅ | Fixed: ActionModal restructured with sticky header/footer (flex-col max-h-[80vh]) + scrollable body. PromoteMergeModal same structure + `interacted` flag for discard-confirm on outside click. Row order aligned (date→type in both BEFORE/AFTER). i18n `standalone` pluralized (IT/FR/ES). Tags rendered as colored badges via `getStringBadgeStyle` + `.action-tag-badge` scoped CSS. Quantity uses `formatTxQuantity` with emoji 📈/📉 and — for zero. |
| C6 | ✅ | Fixed: refactored into shared `txDisplayHelpers.ts` (`formatTxQuantity`, `formatTxCash`). All modal/table components use unified helpers. Zero → "—" everywhere. |
| C8 | ✅ | Fixed during C12 walktest: description field shows `⟷ Concatenate` label (like tags shows `⟷ Union`). Global ⟷ button uses same symbol. Removed unused `allMerge` i18n key. Tag badges in MergeModal now colored (added `.merge-tag-badge` scoped style consuming CSS custom properties). Hash function improved (djb2 + XOR-fold) for better color separation on similar-prefix strings. |
| C9 | ✅ | Fixed: cost_basis field visible for TRANSFER (dual+single) and ADJUSTMENT (single). `showAdvancedSection` expanded to include ADJUSTMENT. Tooltip uses `<Tooltip>` component (not native `title`). Payload normalizes empty amount → null (fixes "Cannot convert '' to Decimal"). Warning amber for ADJUSTMENT with positive qty and no cost basis. |
| C11 | ✅ | Fixed: `sliderPosToNum` now rounds to integer when `isIntegerRange`; `syncNumSlidersFromInput` also rounds on change. Slider and inputs both enforce integer-only for ID columns. |

---

## Follow-up Plans

→ [`plan-R2-SP-C-FxImpliedRateSpread`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-FxImpliedRateSpread.prompt.md) — FX Implied Rate & Market Spread UX (banner suffix + FormModal info marker). Triggered by BUG-C12 fix revealing FX_CONVERSION suggestions in the suggest banner.

→ `plan-R2-SP-C-BugfixRound2` (se necessario) — eventuali regressioni o nuovi bug scoperti durante il walktest finale.

→ [`plan-R2-SP-C-BugfixRound2-WacPreview`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md) — WAC Preview Architecture: nuovo endpoint `wac-preview`, toggle Auto/Manual nel form, rimozione auto-calc al commit, E2E W8/W9/W10. Triggered by C9 walktest gaps → architectural rethink.

