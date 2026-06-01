# Plan: Fix WAC Partner Rows (Bug F2 + 9-10-11) + Test FM1-FM9

> **✅ STATUS**: COMPLETED (2026-05-30)

**Parent plan**: [`plan-WacInlineValidateCommit.prompt.md`](./plan-WacInlineValidateCommit.prompt.md) (sezione "Bug post-completamento — Bug F2")

---

## Obiettivo

Risolvere **definitivamente** Bug F2, 9, 10, 11: il receiver TRANSFER/ADJUSTMENT+ nella BulkModal deve avere `cost_basis_mode: 'auto'` → backend calcola WAC → cella mostra il valore. Aggiungere test E2E FormModal mancanti (FM1-FM9).

---

## Contesto

Dopo il refactoring WAC inline (`plan-WacInlineValidateCommit`), il calcolo WAC avviene in `/validate` e `/commit`. Il frontend manda `cost_basis_mode: "auto"` su items eligible → backend calcola → ritorna `wac_results[]`. Il problema: le **partner rows** (receiver TRANSFER, ADJUSTMENT+) create nella BulkModal non hanno `cost_basis_mode: 'auto'` nei fields → `buildCreatePayload` non include il campo → backend non calcola → `wac_results: null` → cella mostra `—`.

### Bug Summary

| Bug | Sintomo | Root Cause | Status |
|-----|---------|-----------|--------|
| **F2** | TRANSFER receiver → `wac_results: null` | Partner row ha `cost_basis_mode: null` | DA FIXARE |
| **9** | Cella BulkModal non mostra WAC per TRANSFER auto | Conseguenza diretta di F2 | DA FIXARE |
| **10** | FormModal manual override non propaga alla cella | Probabilmente già risolto dal refactoring | DA VERIFICARE |
| **11** | TX DB con `cost_basis_override` mostra `—` | Probabilmente già risolto (`fieldsFromTx` setta 'manual') | DA VERIFICARE |

---

## Decisioni architetturali

1. **Usare SEMPRE `getCostBasisRule()`** (che legge da `/api/v1/transactions/types`) per decidere eligibilità — mai hardcodare tipi
2. **Clone di TX con cost_basis → mode 'auto'**: un nuovo TRANSFER deve ricalcolare il WAC alla nuova data, non copiare il valore vecchio
3. **`patchDualRowFromForm` e Bug 10**: se il test FM7 mostra che il toggle funziona già, nessun fix. Se fallisce, propagare `_cost_basis_mode` come fa `addDualRowFromForm`

---

## Steps di esecuzione

### Phase F: Fix partner rows `cost_basis_mode`

#### Step F1: Fix `collapsePairedOps` — clone path (pass 3) ✅ 2026-05-30

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (~line 618)

Nel pass 3 di `collapsePairedOps` (collapse create ops con shared link_uuid), dopo `opArr[toIdx].pairedWith = opArr[fromIdx].tempId`, derivare il `cost_basis_mode` per il receiver:

```typescript
// After: opArr[toIdx].pairedWith = opArr[fromIdx].tempId;
// Derive cost_basis_mode for receiver (to) side using backend rules
const toQty = Number(opArr[toIdx].fields.quantity ?? 0);
if (toQty > 0) {
    const toSide: 'from' | 'to' | 'self' = 'to';
    const toCbRule = getCostBasisRule(opArr[toIdx].fields.type, toSide);
    if (toCbRule !== 'forbidden') {
        opArr[toIdx].fields.cost_basis_mode = 'auto';
        opArr[toIdx].fields.cost_basis_override = null; // reset — will be filled by WAC
    }
}
```

**Motivazione**: quando si clona un TRANSFER pair da DB, il receiver ha `'manual'` (da `fieldsFromTx`) ma essendo una nuova TX deve ricalcolare. Per nuove create con link_uuid, stessa logica.

> **Note implementazione**: Aggiunto blocco dopo `opArr[toIdx].pairedWith = ...` nel pass 3: usa `getCostBasisRule(type, 'to')` per derivare eligibilità, setta `cost_basis_mode: 'auto'` e `cost_basis_override: null` sul receiver se `qty > 0` e rule !== 'forbidden'.

#### Step F2: Fix `collapsePairedOps` — edit path (pass 1+2) ✅ 2026-05-30

Nella sezione dove si crea la hidden partner op da `fieldsFromTx(partnerTx)` (~line 588-596), NON modificare: il partner edit da DB con `cost_basis_override` deve restare `'manual'` (Bug 11 fix).

**Nessuna modifica necessaria** — `fieldsFromTx` setta `'manual'` quando `cbRule !== 'forbidden'`, e la cella renderizza il valore. Questo risolve Bug 11 by design.

> **Note implementazione**: No-op confermata. Il path edit (pass 1+2) gestisce correttamente il `cost_basis_mode` tramite `fieldsFromTx`.

#### Step F3: Verificare `addDualRowFromForm` propagation (FormModal → BulkModal) ✅ 2026-05-30

**Verifica manuale** (confermata dall'analisi del codice):
1. `collectDualCreates()` → `buildDualCreatePayloads('transfer_asset', ...)` → `toItem.cost_basis_mode = "auto"` ✓
2. `addDualRowFromForm` propaga `payload._cost_basis_mode` a `items[1]._cost_basis_mode` (line 1917) ✓
3. `applyFormPayload(toOp.fields, items[1])` → line 688: legge `p._cost_basis_mode === 'auto'` → setta `target.cost_basis_mode = 'auto'` ✓

**Conclusione**: il path FormModal → BulkModal funziona. Test FM3 confermerà.

> **Note implementazione**: No-op confermata. La catena `collectDualCreates` → `addDualRowFromForm` → `applyFormPayload` propaga correttamente `cost_basis_mode: 'auto'` al receiver.

#### Step F4: Verificare `patchDualRowFromForm` (Bug 10 — toggle Manual/Auto) ✅ 2026-05-30

**Analisi**: line 1943 dice "do NOT propagate `_cost_basis_mode`" per patch. Ma `items[1]` da `collectDualCreates()` → `buildDualCreatePayloads` include `cost_basis_mode: "auto"` come campo raw (senza underscore). E `applyFormPayload` legge `p._cost_basis_mode` (con underscore) — diverso da `p.cost_basis_mode`.

**Scenario problematico**: utente edita un TRANSFER pair, switcha Manual→Auto nel FormModal, salva → `patchDualRowFromForm` non propaga il nuovo mode al partner op.

**Fix potenziale** (da applicare solo se test FM7 fallisce):
```typescript
// In patchDualRowFromForm, after items extraction (~line 1942):
if (typeof payload._cost_basis_mode === 'string') {
    if (!('_cost_basis_mode' in items[1])) {
        items[1]._cost_basis_mode = payload._cost_basis_mode;
    }
}
```

> **Note implementazione**: FM7 fallito come previsto — il `patchDualRowFromForm` non propagava `_cost_basis_mode` a `items[1]`. Fix applicato: prima di applyFormPayload, copia `payload._cost_basis_mode` in `items[1]._cost_basis_mode` se assente. Anche rimosso il commento "do NOT propagate" che era errato.

---

### Phase G: Test E2E FormModal (FM1-FM9)

#### Step G1: Creare `frontend/e2e/transactions/tx-wac-formmodal.spec.ts` ✅ 2026-05-30

**Prerequisiti mock data**: un asset con almeno 1 BUY nel broker 1 (per avere un pool WAC calcolabile). L'asset 9 (ETF1) con BUY 10@50 nel `populate_mock_data.py` copre questo caso.

| Test | Scenario | Verifica |
|------|----------|----------|
| FM1 | BUY via FormModal → validate | Payload: `cost_basis_mode` ASSENTE |
| FM2 | SELL via FormModal → validate | Payload: `cost_basis_mode` ASSENTE |
| FM3 | TRANSFER pair via FormModal → validate | Receiver payload: `cost_basis_mode: "auto"`, response: `wac_results` non null |
| FM4 | ADJUSTMENT+ via FormModal → validate | Payload: `cost_basis_mode: "auto"` |
| FM5 | ADJUSTMENT- via FormModal → validate | Payload: `cost_basis_mode` ASSENTE |
| FM6 | Edit TRANSFER salvato con cbo → cella BulkModal | Cella mostra valore (non `—`), `data-testid="tx-bulk-cost-basis-manual"` |
| FM7 | Toggle Auto→Manual nel FormModal su TRANSFER receiver | Payload ha `cost_basis_override` esplicito, NO `cost_basis_mode: "auto"` |
| FM8 | DEPOSIT via FormModal → validate | Nessun `cost_basis_mode` nel payload |
| FM9 | BUY via FormModal → validate OK | Nessun issue `costBasisModeIncompatible` in response |

**Pattern**: usare `page.waitForRequest()` per intercettare il payload validate/commit e asserire sul body JSON.

#### Step G2: Registrare nel test runner ✅ 2026-05-30

**File**: `scripts/test_runner/_frontend_transaction.py`

1. Aggiungere runner function: `def front_tx_wac_formmodal(...)`
2. Aggiungere alla lista in `front_transaction_all()`
3. Aggiungere a `populate_registry()` con `add_test(cat, "tx-wac-formmodal", ...)`

#### Step G3: Run & fix ✅ 2026-05-30

```bash
./dev.py test front-transaction tx-wac-formmodal
```

Se FM7 fallisce → applicare fix F4.
Se FM3/FM6 falliscono → debug e fix.

> **Note implementazione**: Round 1: FM1-5,8,9 passed. FM6 fallito per date format (tabella mostra "May 30, 2026" non "2026-05-30"). FM7 fallito come previsto → F4 fix applicato. Round 2 dopo fix F4 + FM6 date search: 9/9 passed (1.4m).

---

### Phase H: Validate & Regression

#### Step H1: `./dev.py front check` → 0 errors ✅ 2026-05-30

> **Note implementazione**: svelte-check 0 errors, 0 warnings dopo tutti i fix (F1, F4).

#### Step H2: `./dev.py test front-transaction tx-wac-bulk` → no regression ✅ 2026-05-30

> **Note implementazione**: 7/7 passed (1.4m). WB4 aveva lo stesso bug di FM6 (date format ISO vs locale) — fixato nella stessa sessione.

#### Step H3: `./dev.py test front-transaction tx-wac-formmodal` → all pass ✅ 2026-05-30

> **Note implementazione**: 9/9 passed (1.4m). FM1-FM5,FM8,FM9 passati al primo colpo. FM6 e FM7 richiesero fix (date search + F4 patchDualRowFromForm).

#### Step H4: Aggiornare status in questo file ✅ 2026-05-30

> **Note implementazione**: Piano completato. Status → ✅ COMPLETED.

---

## Dipendenze e parallelismo

```
F1 ──┐
     ├──→ G1 ──→ G2 ──→ G3 ──→ H1-H4
F2 ──┘     │
F3 (verify)┘
F4 (conditional on G3/FM7 result)
```

- **F1** (fix clone path) è il fix critico — da fare PRIMA dei test
- **F2** (verify edit path) è una no-op (nessuna modifica)
- **F3** (verify FormModal path) è una no-op (già funziona)
- **G1+G2** (scrivere test) possono iniziare in parallelo con F1 (non dipendono dal fix per essere scritti)
- **G3** (run test) richiede F1 completato
- **F4** (fix patchDualRow) è condizionale: solo se FM7 fallisce in G3
- **H1-H4** (validate) richiedono tutto il resto completato

---

## File coinvolti

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | F1: fix `collapsePairedOps` pass 3 |
| `frontend/e2e/transactions/tx-wac-formmodal.spec.ts` | G1: nuovo file test |
| `scripts/test_runner/_frontend_transaction.py` | G2: registrazione test |

---

## Test Criteria

- [x] FM3 passa: TRANSFER pair via FormModal → receiver ha `cost_basis_mode: "auto"` → `wac_results` non null
- [x] FM6 passa: TX DB con `cost_basis_override` → cella mostra valore (non `—`)
- [x] FM7 passa: toggle Auto→Manual propaga correttamente
- [x] WB1-WB7 (tx-wac-bulk.spec.ts) non regrediscono
- [x] `./dev.py front check` → 0 errors

---

## Rischi

| Rischio | Mitigazione |
|---------|-------------|
| Fix F1 sovrascrive mode 'manual' su edit rows | Pass 3 opera solo su create ops (`op !== 'create'` guard già presente a line 603) |
| FM7 fallisce (Bug 10 non risolto) | Fix F4 pronto — applicare e re-run |
| Mock data insufficiente per FM3/FM4 | Verificare `populate_mock_data.py` ha asset con BUY nel broker target |

---
---

# Addendum: Bug 12 (Reactivity) + Bug 13 (auto-detail)

> **✅ STATUS**: COMPLETED (2026-05-30)
> **Discovered**: 2026-05-30 — walktest manuale post-completamento Phase F–H
> **Depends on**: Phase F–H (completata) — questo addendum estende lo stesso file

---

## Obiettivo

Risolvere due bug emersi dal walktest manuale:

1. **Bug 12 — Cella WAC non si popola** (Reactivity): dopo validate, il backend ritorna `wac_results` con WAC calcolato correttamente, il codice scrive `cost_basis_override` sull'op receiver (nascosto), ma la cella nella DataTable **non si aggiorna**
2. **Bug 13 — `auto-detail` per qualifying_txs**: il FormModal manda `"auto"` al backend, che non include `qualifying_txs` nella response → la tabella dettaglio PMC nel WacPreviewSection resta vuota

---

## Contesto

### Bug 12 — Evidenza dal walktest

**Payload inviato** (confermato dal network tab):
```json
{"creates":[
  {"broker_id":1,"type":"TRANSFER","date":"2026-05-30","quantity":"-2","link_uuid":"...","asset_id":1},
  {"broker_id":3,"type":"TRANSFER","date":"2026-05-30","quantity":"2","link_uuid":"...","asset_id":1,"cost_basis_mode":"auto","cost_basis_override":null}
]}
```

**Risposta dal backend** (confermata):
```json
{
  "wac_results": [{
    "wac": {"code":"USD","amount":"138.4493784808250217055248502"},
    "operation":"create","index":1,"source_broker_id":1,
    "wac_qualifying_txs":[]
  }]
}
```

**Risultato visibile**: la cella cost_basis mostra il campo vuoto (placeholder "auto") — **non** il valore `💡 $138.45`.

Il frontend ha rebuildato correttamente (`./dev.py front build --debug`). Il payload e la response sono corretti. Il bug è nel rendering.

### Bug 12 — Root cause: Svelte 5 reactivity

La DataTable riceve `data={visibleOps}` (line 2724) dove:
```typescript
let visibleOps = $derived(ops.filter(o => !o.pairedWith));  // L227
```

L'WAC extraction (L1100-1104) scrive `cost_basis_override` sul receiver:
```typescript
ops = ops.map((o) => {
    if (o.tempId !== tempId) return o;  // sender → STESSA reference!
    return {...o, fields: {...o.fields, cost_basis_override: wacVal}};
});
```

Il **receiver** (nascosto, `pairedWith` settato) ottiene un nuovo oggetto. Ma il **sender** (visibile, `!pairedWith`) mantiene la **stessa object reference** — viene restituito identico dal `map`. Quindi `visibleOps` produce un nuovo array con lo stesso sender object. La DataTable con keyed rendering (`getRowId={(d) => d.tempId}`) vede lo stesso oggetto per il sender → **non ri-renderizza la cella** → il cell renderer che chiama `getPartnerOp(row.tempId)` per leggere il partner **non viene mai ri-chiamato**.

### Bug 13 — Design: rename solo nel validate

Il backend supporta `cost_basis_mode: Literal["auto", "auto-detail", "manual"]`:
- `"auto"`: calcola WAC, ritorna `wac_results[].wac` — **ma `qualifying_txs: []`** e `asset_price: null`
- `"auto-detail"`: calcola WAC + ritorna `qualifying_txs`, `asset_price`, `asset_price_stale`

**Decisione architetturale**: il rename `auto → auto-detail` avviene **esclusivamente nel validate payload** (post-processing), non nei DraftFields né nei payload builders. Motivazione:
- `DraftFields.cost_basis_mode` resta `'auto' | 'manual' | null` — il tipo `auto-detail` non ha senso nella UI
- I payload builders (`buildCreatePayload`, `buildDualCreatePayloads`, `buildUpdateDiff`) continuano a produrre `'auto'`
- Il **commit** manda `'auto'` — safe perché il FormModal è chiuso al commit e non servono i qualifying_txs
- Solo il **validate** rename `auto → auto-detail` per ottenere i dettagli nella response

---

## Decisioni architetturali (addendum)

4. **Reactivity fix pattern**: quando si aggiorna un campo sul partner nascosto, creare un **nuovo reference** anche per il sender visibile (`{...o}`) per forzare la DataTable a ri-renderizzare la cella
5. **`auto-detail` solo nel validate**: l'upgrade `auto → auto-detail` è un post-processing sul payload dopo `buildBatchPayload` / prima di `validateTransactions`. Il commit riceve `'auto'`. Il backend tratta `auto` e `auto-detail` identicamente per il calcolo WAC — differisce solo nella verbosità della response
6. **WAC engine condiviso**: confermato che `compute_wac_iterative()` in `wac_service.py` è l'unico engine WAC — usato sia dall'inline batch validate/commit sia dall'endpoint analytics `POST /analytics/wac`. Zero duplicazione

---

## Steps di esecuzione

### Phase I: Fix Bug 12 — Reactivity sender reference

#### Step I1: Fix `ops.map` nel WAC extraction — anche il sender deve cambiare reference ✅ 2026-05-30

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (~L1100-1104)

**Codice attuale**:
```typescript
ops = ops.map((o) => {
    if (o.tempId !== tempId) return o;
    return {...o, fields: {...o.fields, cost_basis_override: {code: wacVal.code, amount: wacVal.amount}}};
});
```

**Fix**: identificare il sender (il main op il cui partner è stato aggiornato) e creare un nuovo reference anche per lui. Il sender è l'op il cui `tempId` coincide con `opObj.pairedWith` (il receiver punta al sender tramite `pairedWith`).

```typescript
const mainTempId = opObj.pairedWith;  // sender's tempId (receiver points to sender)
ops = ops.map((o) => {
    if (o.tempId === tempId) {
        // Receiver: new object with updated cost_basis_override
        return {...o, fields: {...o.fields, cost_basis_override: {code: wacVal.code, amount: wacVal.amount}}};
    }
    if (mainTempId && o.tempId === mainTempId) {
        // Sender: new reference to force DataTable cell re-render
        return {...o};
    }
    return o;
});
```

**Perché funziona**: la cella `cost_basis_override` della DataTable usa `const partner = getPartnerOp(row.tempId); const source = partner ?? row;`. Il sender visibile cambia reference → Svelte 5 ri-renderizza la riga → il cell renderer chiama `getPartnerOp()` → trova il partner aggiornato → mostra `💡 $138.45`.

**Edge case — ops standalone (ADJUSTMENT)**: quando l'op non ha `pairedWith` (es. ADJUSTMENT+), `mainTempId` è undefined/null → nessun sender da aggiornare → solo il receiver stesso cambia, ed è anche visibile → la cella si aggiorna correttamente (nessun problema di reactivity).

---

### Phase J: Fix Bug 13 — `auto` → `auto-detail` nel validate

#### Step J1: Creare utility `upgradeAutoToDetail()` in txPayloadHelpers.ts ✅ 2026-05-30

**File**: `frontend/src/lib/utils/txPayloadHelpers.ts` (in fondo, prima di `export function buildBatchPayload`)

```typescript
/**
 * Post-process a batch payload for validate: upgrade cost_basis_mode 'auto' → 'auto-detail'
 * so the backend includes qualifying_txs + asset_price in the response.
 * Mutates the payload in-place (safe — the object is local to the validate call).
 * Must NOT be called on commit payloads (commit doesn't need details).
 */
export function upgradeAutoToDetail(payload: Record<string, unknown>): void {
    const arrays = ['creates', 'updates'] as const;
    for (const key of arrays) {
        const items = payload[key] as Record<string, unknown>[] | undefined;
        if (!items) continue;
        for (const item of items) {
            if (item.cost_basis_mode === 'auto') {
                item.cost_basis_mode = 'auto-detail';
            }
        }
    }
}
```

**Motivazione**: mutazione in-place è safe perché il payload è un oggetto locale costruito da `buildBatchPayload` (crea array freschi). Nessun side effect su `ops` o `DraftFields`.

#### Step J2: Applicare in BulkModal `validateFn` ✅ 2026-05-30

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (~L1058-1064)

**Codice attuale** (L1058-1064):
```typescript
const payload = buildBatchPayload({
    ops: resolved,
    splits: pendingSplits.length > 0 ? pendingSplits.map((s) => ({id_a: s.id_a, id_b: s.id_b})) : undefined,
});
const sentKey = lastDraftKey;
const result = await validateTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
```

**Fix**: aggiungere `upgradeAutoToDetail(payload)` tra `buildBatchPayload` e `validateTransactions`:
```typescript
const payload = buildBatchPayload({
    ops: resolved,
    splits: pendingSplits.length > 0 ? pendingSplits.map((s) => ({id_a: s.id_a, id_b: s.id_b})) : undefined,
});
upgradeAutoToDetail(payload);  // ← NEW: validate gets 'auto-detail' for qualifying_txs
const sentKey = lastDraftKey;
const result = await validateTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});
```

**Import**: aggiungere `upgradeAutoToDetail` all'import esistente da `$lib/utils/txPayloadHelpers` (L50).

**NON applicare nel commit path** (~L1214): il commit usa `buildBatchPayload` ma NON deve fare l'upgrade — `'auto'` è sufficiente (il FormModal è chiuso, nessuno legge qualifying_txs).

#### Step J3: Applicare in FormModal `validateFn` ✅ 2026-05-30

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte` (~L747-767)

**Codice attuale** (L747-767):
```typescript
const myPayload: Record<string, unknown> = pairLayout
    ? (mode === 'edit' ? {updates: collectDualUpdates()} : {creates: collectDualCreates()})
    : mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]};

// Context-aware: merge bulk context if available
let payload: Record<string, unknown>;
// ... merging logic ...

const sentKey = lastDraftKey;
const result = await validateTransactions(payload, {fallback: $t('transactions.form.saveFailed')});
```

**Fix**: aggiungere `upgradeAutoToDetail(payload)` dopo la costruzione di `payload` e prima di `validateTransactions`:
```typescript
upgradeAutoToDetail(payload);  // ← NEW
const sentKey = lastDraftKey;
const result = await validateTransactions(payload, ...);
```

**Import**: aggiungere `upgradeAutoToDetail` all'import da `$lib/utils/txPayloadHelpers` (L44).

**NON applicare nel commit path** (~L1003): il commit standalone manda `'auto'` — safe.

---

### Phase K: Test E2E — Aggiornamento assertions

#### Step K1: Aggiornare FM3 e FM4 ✅ 2026-05-30

**File**: `frontend/e2e/transactions/tx-wac-formmodal.spec.ts`

I test intercettano il *request body* del validate con `captureValidatePayload`. Dopo il fix J3, il payload conterrà `"auto-detail"` invece di `"auto"`.

**FM3** (L240):
```diff
- expect(receiver!.cost_basis_mode).toBe('auto');
+ expect(receiver!.cost_basis_mode).toBe('auto-detail');
```

**FM4** (L271):
```diff
- expect(adjItem!.cost_basis_mode).toBe('auto');
+ expect(adjItem!.cost_basis_mode).toBe('auto-detail');
```

**Test NON impattati** (nessuna modifica):
- FM1, FM2, FM5, FM8: asseriscono `not.toHaveProperty('cost_basis_mode')` → invariato
- FM6: testa cella BulkModal, non payload validate → invariato
- FM7: asserisce `not.toHaveProperty('cost_basis_mode')` (manual mode) → invariato
- FM9: asserisce assenza di issue `costBasisModeIncompatible` → invariato
- WB1-WB7: non intercettano `cost_basis_mode` → invariato

---

### Phase L: Validate & Regression

#### Step L1: `./dev.py front check` → 0 errors ✅ 2026-05-30

> **Note implementazione**: svelte-check 0 errors, 0 warnings dopo fix I1+J1-J3.

#### Step L2: `./dev.py test front-transaction tx-wac-formmodal` → all pass ✅ 2026-05-30

> **Note implementazione**: 9/9 passed (1.6m). FM3 e FM4 passano con assertion `'auto-detail'`. Nessun test regredito.

#### Step L3: `./dev.py test front-transaction tx-wac-bulk` → no regression ✅ 2026-05-30

> **Note implementazione**: 7/7 passed (1.6m). Nessuna regressione sui test WB1-WB7.

#### Step L4: Walktest manuale ✅ 2026-05-30

> **⚠️ Fuori pista**: Walktest ha rivelato Bug 13b — la Phase D extraction nel FormModal era guardata da `!getWacResult` che bloccava l'estrazione in CREATE mode dal BulkModal (dove `editingTempId` è null → `externalWacResult` usa `formWacResult` → ma `formWacResult` non veniva mai settato). Fix: guard cambiata in `(!getWacResult || !editingTempId)`. Rebuild + 9/9 FM tests pass.

1. `./dev.py front build --debug && ./dev.py server --debug --force --test`
2. Creare BUY 10@500 in broker 1
3. Creare TRANSFER 5 da broker 1 a broker 3
4. **Verificare Bug 12**: la cella cost_basis sulla riga TRANSFER mostra `💡 $value` dopo validate (non `💡 …`) ✓
5. **Verificare Bug 13**: aprire il FormModal sulla TRANSFER, sezione WAC → la tabella qualifying_txs è visibile e contiene le BUY usate per il calcolo ✓ (dopo fix 13b)
6. Commit → nessun errore

---

## Dipendenze e parallelismo (addendum)

```
I1 (reactivity fix) ──→ ┐
                         ├──→ L1-L4
J1 (utility) ──→ J2 + J3 ──→ K1 ──→ ┘
```

- **I1** e **J1** sono indipendenti — possono essere fatti in parallelo
- **J2** e **J3** dipendono da **J1** (utility deve esistere prima dell'import)
- **K1** dipende da **J2+J3** (i test devono matchare il nuovo payload)
- **L1-L4** richiedono tutto completato

---

## File coinvolti (addendum)

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | I1: fix reactivity nell'WAC extraction (L1100-1104); J2: `upgradeAutoToDetail` nel validateFn (L1062) |
| `frontend/src/lib/utils/txPayloadHelpers.ts` | J1: nuova funzione `upgradeAutoToDetail()` |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | J3: `upgradeAutoToDetail` nel validateFn (L767); Bug13b: Phase D guard `(!getWacResult \|\| !editingTempId)` (L781) |
| `frontend/e2e/transactions/tx-wac-formmodal.spec.ts` | K1: FM3 L240 + FM4 L271 → `'auto-detail'` |

---

## Test Criteria (addendum)

- [x] Cella TRANSFER receiver in BulkModal mostra `💡 $value` dopo validate (Bug 12 risolto)
- [x] WacPreviewSection nel FormModal mostra tabella qualifying_txs non vuota (Bug 13 risolto)
- [x] Network tab validate: payload contiene `cost_basis_mode: "auto-detail"` per receiver TRANSFER
- [x] Network tab commit: payload contiene `cost_basis_mode: "auto"` (NON `auto-detail`)
- [x] FM3 e FM4 passano con assertion `'auto-detail'`
- [x] FM1,FM2,FM5-FM9 passano invariati
- [x] WB1-WB7 passano invariati
- [x] `./dev.py front check` → 0 errors

---

## Rischi (addendum)

| Rischio | Mitigazione |
|---------|-------------|
| Reactivity fix crea shallow copy inutili per ops non-paired | Guard `if (mainTempId && ...)` — solo quando c'è un sender paired. Per standalone (ADJUSTMENT) nessun overhead |
| `upgradeAutoToDetail` muta payload che potrebbe essere riusato | Il payload è creato fresco da `buildBatchPayload` / `collectDualCreates` — non riusato altrove |
| FormModal in BulkModal fa upgrade anche sulle ops del bulk context | Safe: il backend tratta `auto-detail` come `auto` per il calcolo. Il validate del FormModal è indipendente e la response viene usata solo per issues display + WAC |
| Test FM3/FM4 intercettano validate ma non commit | Corretto per design: il commit NON ha `auto-detail`. Se in futuro serve testare il commit payload, aggiungere un test dedicato |
| L'ADJUSTMENT standalone (senza pairedWith) non beneficia del fix I1 reactivity | L'ADJUSTMENT è visibile direttamente (non nascosto) → il `map` crea un nuovo reference direttamente sull'op target → la DataTable lo vede → non serve il fix sender |

