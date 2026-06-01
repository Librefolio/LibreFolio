# Plan D2 Bugfix 1 — Split/Promote Polish & Test Coverage

**Date**: 2026-05-12
**Status**: ✅ COMPLETED (steps F2-F14 absorbed by bugfix2-4)
**Priority**: P1 (critical bugs + UX polish + test coverage)
**Estimated effort**: ~20h (~4 days)

**Parent**: [`plan-PlanD2_FrontendSplitPromoteUI.prompt.md`](../plan-PlanD2_FrontendSplitPromoteUI.prompt.md)
**Companion**: [`plan-PlanD1_BackendBatchSuggest.prompt.md`](../plan-PlanD1_BackendBatchSuggest.prompt.md)

---

## 🎯 Obiettivo

Risolvere tutti i bug trovati nel test manuale di D2, migliorare UX delle modali split/promote/merge, aggiungere le traduzioni mancanti, correggere i dati mock, e creare la test suite E2E automatizzata (D3 del piano padre).

---

## 📋 Bug Inventory (dal test manuale)

| # | Area | Severità | Descrizione |
|---|------|----------|-------------|
| B1 | Split Main Table | 🔴 Critical | Split invia solo `{splits:[{id:38}]}` → manca il secondo ID. Il backend accetta 1 ID (split entrambi internamente), ma la response contiene solo 1 result. Il balance walk fallisce perché `populate_mock_data` non bilancia le qty (Apple goes negative). |
| B2 | Split ConfirmModal | 🟡 UX | La modale mostra solo testo generico. Deve mostrare le 2 TX a confronto come nella delete linked (2 colonne). |
| B3 | Main Table Actions | 🟡 UX | Colonna azioni troppo stretta, bottoni non allineati a destra. |
| B4 | BulkModal open bug | 🔴 Critical | Se si fa Edit su una riga linked subito dopo il refresh della pagina, poi Apply, la BulkModal si apre malformata (colonne vuote/rotte). Funziona al secondo tentativo. Race condition nell'init. |
| B5 | BulkModal Split | 🔴 Critical | Dopo split nel BulkModal, appare solo 1 riga (non 2), e il validate porta errore "Cannot change type from TRANSFER to ADJUSTMENT (allowed swaps: TRANSFER)". Lo split locale viene trattato come un update di tipo, non come un'operazione split. |
| B6 | Promote ConfirmModal | 🟡 UX | Modale troppo semplice (solo tipo target). Deve mostrare le 2 TX in 2 colonne con anteprima della trasformazione. |
| B7 | PromoteMergeModal i18n | 🔴 Bug | Chiavi i18n non risolte: `transactions.promote.mergeTitle` appare raw nel titolo e nel sottotitolo. Le chiavi esistono in en.json ma non vengono renderizzate correttamente. |
| B8 | PromoteMergeModal layout | 🟡 UX | Layout 3-colonne scomodo (frecce piccole, textarea a 1 riga, tags non colorati, nessun componente tag balloon, no bottoni bulk all◀/all▸/all⟷). |
| B9 | PromoteMergeModal mobile | 🟡 UX | Su mobile la 3-colonne è inutilizzabile. Serve layout stacked: [read1][read2] / [merge] sotto. |
| B10 | PromoteMergeModal description | 🟡 UX | Accapo non rispettati (usa `<input>` anziché `<textarea>`). |
| B11 | Promote response | 🟢 Minor | Response contiene solo 1 dei 2 ID: `{id: 39}`. Sarebbe utile avere entrambi (o il link_uuid) per debug. |
| B12 | BulkModal Promote toolbar | 🔴 Critical | Selezionando 2 righe standalone compatibili nel BulkModal, nessun banner/toolbar Promote appare. La feature C4 non funziona. |
| B13 | BulkModal row remove | 🟡 UX | Manca l'azione per rimuovere una riga dal batch corrente (senza cancellarla dal DB). L'azione `remove-from-batch` esiste solo per `addedViaPicker` rows. |
| B14 | Suggest banner type sbagliato | 🔴 Bug | Il suggest mostra `DEPOSIT & WITHDRAWAL → Cambio Valuta` (FX_CONVERSION) invece di `→ Cash Transfer` (CASH_TRANSFER). La logica `findPromoteMatch` o il backend suggest ritorna il tipo sbagliato. |
| B15 | Suggest banner messaggio | 🟡 UX | Messaggio poco chiaro. Solo `DEPOSIT & WITHDRAWAL → Cambio Valuta`. Serve: "In data XXX, Riga #1 (icona) e Riga #3 (icona) → Cash Transfer (icona)". |
| B16 | Suggest banner → promote crea 2 righe separate | 🔴 Critical | Click su 🔗 nel banner: le 2 righe restano separate (non collassate in 1 riga paired con Da:/A:). La promote locale deve collassare le 2 ops in una sola riga paired. |
| B17 | BulkModal row ordering | 🟡 UX | Le righe nel BulkModal non hanno un ordine logico. Dovrebbero usare `orderItem` per ordinamento consistente. |
| B18 | Commit toast | 🟡 UX | Toast dice "✅ 3 create". Dovrebbe dire "✅ 3 transazioni salvate nel DB" (frase localizzata). |
| B19 | Validation error codes hardcoded | 🟡 Tech debt | `balanceAssetNegative`, `balanceCashNegative` sono hardcodati sia in backend che frontend. Servono un enum centralizzato e un endpoint info che li esponga. |
| B20 | populate_mock_data balance | 🔴 Critical | Mock data generano posizioni negative su Apple (ADJUSTMENT -2 su IB senza BUY che bilanci). I test passano ma i dati sono inconsistenti → i test E2E (split/promote) falliscono. |
| B21 | Context menu Promote | 🟡 UX | Quando 2 righe sono selezionate nella Main Table, manca l'opzione Promote nel context menu (3 puntini). L'utente deve sempre usare il bottone toolbar. |

---

## ✅ Decisioni architetturali (confermate con l'utente)

### DD-BF1 — Split saved nel BulkModal: rimuovi dal batch (F2)
Quando l'utente fa split su una saved paired nel BulkModal:
1. **Rimuovere la riga** dal batch (`removeRow(row.tempId)`)
2. Accumulare `{id: row.txId}` in `pendingSplits`
3. Badge "⚡ N split in coda" nella toolbar stats

L'utente non vede preview locale → il comportamento è coerente con la semantica: lo split è atomico del backend, non ha senso editare una riga che sarà splittata.

### DD-BF2 — Collapse post-promote: pattern unificato con split (F5)
Sia per split che per promote nel BulkModal, il pattern di collapsamento è lo stesso:
- **Split**: rimuovi riga dal batch → accumula in `pendingSplits`
- **Promote 2 new**: collassa come paired → opA diventa "main" con `partnerPayload`/`partnerBrokerId`/`partnerCash`/`partnerDate`, opB viene rimossa
- **Promote 2 saved**: accumulare in `pendingPromotes`, poi collassare (opB rimossa, opA con partner display)

Il collapsamento post-promote usa un **helper dedicato `collapseIntoPaired(opA, opB)`** e NON riusa `collapsePairedOps()`:
- `collapsePairedOps()` dipende da `txStoreGet()` per `related_transaction_id` → non funziona per 2 create ops che non sono nel txStore
- `collapsePairedOps()` è pensata per array-wide processing all'init → effetti collaterali possibili se chiamata mid-session
- Il helper dedicato è esplicito: prende 2 ops, determina from/to, setta i campi partner, ritorna la main op + la op da rimuovere

### DD-BF3 — BulkModal primo open rotto: `getTypeRule()` + FALLBACK_RULE (F6) ✅
**Root cause CONFERMATA**: `getTypeRule(code)` restituisce `FALLBACK_RULE` (con `requiresPair: false`) quando `_ruleMap` è vuoto (types non ancora caricati dal server). L'`$effect` init assegnava `ops` prima che `ensureTypesLoaded()` completasse → DataTable rendeva paired rows come singles.
**Fix**: deferred `ops` assignment — dual-path con fast (types cached) e slow (types loading). Vedi Step F6 per dettagli completi.

### DD-BF4 — `findPromoteMatch`: constraint client-side (F4)
Arricchire `findPromoteMatch()` con `brokerA`, `brokerB`, `currencyA`, `currencyB` opzionali per verificare `field_constraints` lato client. Questo serve sia per il suggest banner (tipo corretto) sia per la toolbar promote (tipo preciso):
- WITHDRAWAL+DEPOSIT + same currency + diff broker → CASH_TRANSFER
- WITHDRAWAL+DEPOSIT + diff currency + same broker → FX_CONVERSION
- Se constraint non verificabili (mancano info) → NON restituire match (meglio nessun suggest che uno sbagliato)

**Nota**: il backend `/promote-suggest` già verifica i constraint. Il fix frontend è parallelo: per le local suggestions (new+new), il client deve verificare i constraint da sé.

**Nota futura**: FX_CONVERSION è attualmente vincolata a `broker_id: equal` — se in futuro si rilassa per supportare conversioni cross-broker, servirà: (1) modificare il pair_form_layout nel frontend per secondo selettore broker, (2) aggiornare `findPromoteMatch()`, (3) aggiornare test E2E. Per ora il vincolo è voluto.

### DD-BF5 — Tags nella PromoteMergeModal: riuso TagInput (F7)
Usare il componente `TagInput.svelte` già presente in `$lib/components/ui/TagInput.svelte` (usato in TransactionFormModal). Nessuna logica da estrarre — il componente è già standalone.

### DD-BF6 — Validation error codes: dentro GET /transactions/types + enum ora (F13)
- Backend: creare `TXValidationCode` StrEnum + esporlo in `GET /transactions/types`
- Frontend: leggere i codici dal response e mappare ai messaggi i18n
- Farlo ora per facilitare sviluppi futuri

---

## Steps

### Step F1 — Fix `populate_mock_data.py` balance issues — ✅ COMPLETATO

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

**Fix applicata** (2026-05-13): Aggiunta BUY Apple qty=+5 su IB (day -9) con tag `balance-safe` per coprire i -2 del promote-test ADJUSTMENT. Balance ora: 15 - 5 - 5 - 3 - 1 + 5 - 2 = +4 (positivo).

---

### Step F2 — Fix BulkModal split logic (B5) — ~1.5h ✂️

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Problema**: `handleSplitRow()` per saved paired cambia il tipo localmente (riga 601) → `collectUpdate()` genera un update con cambio tipo illegale → conflitto con lo split nel payload.

**Root cause**: Lo split saved muta `row.fields.type` (riga 601) e poi `deriveStatus()` ritorna `'edited'` → `collectUpdate()` produce `{id:38, type:"ADJUSTMENT"}` → il backend riceve sia `splits:[{id:38}]` che `updates:[{id:38, type:"ADJUSTMENT"}]` → il validate vede un type swap forbidden + uno split → fallimento.

**Fix** (decisione DD-BF1 — rimuovi dal batch):
1. In `handleSplitRow()` per saved paired, **rimuovere la riga dal batch** dopo aver accumulato in pendingSplits:
   ```ts
   // Case A: Saved paired → backend split
   pendingSplits = [...pendingSplits, {id: (row as any).txId}];
   removeRow(row.tempId);
   ```
2. Rimuovere TUTTO il codice che muta `row.fields.type`, `row.partnerId`, ecc. per il caso saved — non serve più.
3. In toolbar stats, mostrare badge "⚡ N split in coda" quando `pendingSplits.length > 0`.

**Per il caso B (new paired, link_uuid shared)**: la logica attuale è corretta (trasformazione locale, nessun backend call). Nessuna modifica.

---

### Step F3 — ~~BulkModal promote toolbar (B12)~~ → RISOLTO DA F4

**Status**: ✅ Risolto — non è un bug separato.

Il bug B12 (promote toolbar non appariva su 2 new rows nel BulkModal) era causato dal fatto che `findPromoteMatch()` restituiva FX_CONVERSION (tipo sbagliato) per WITHDRAWAL+DEPOSIT senza verificare i constraint. Con le 2 new rows dell'utente (stessa valuta, broker diversi), il match corretto era CASH_TRANSFER.

La catena reattiva (onSelectionChange → bulkTableSelectedRows → selectedForPromote $derived) è **corretta** e funzionante. Il fix di F4 (constraint check in `findPromoteMatch`) risolve automaticamente anche questo bug.

---

### Step F4 — Fix promote suggest type mapping (B14) — ~1.5h 🎯

**File**: `frontend/src/lib/stores/transactionTypeStore.ts`
**File**: `backend/app/schemas/transactions.py` (verifica ordine metadata)

**Root cause CONFERMATA da code review**:

`findPromoteMatch()` (riga 294) scansiona `_cache.transaction_types` in ordine e restituisce il **primo type match** senza verificare i `field_constraints`. Le regole nell'ordine di metadata:
1. TRANSFER: ADJUSTMENT+ADJUSTMENT (con constraint asset_id equal, broker different, qty opposite)
2. **FX_CONVERSION**: WITHDRAWAL+DEPOSIT (con constraint **currency different**, **broker equal**)
3. **CASH_TRANSFER**: WITHDRAWAL+DEPOSIT (con constraint **currency equal**, **broker different**)

Per WITHDRAWAL+DEPOSIT, FX_CONVERSION viene PRIMA di CASH_TRANSFER → il frontend restituisce sempre FX_CONVERSION, ignorando i constraint di currency/broker. **Il bug è puramente frontend** — il backend con `_check_promote_constraints` verifica correttamente.

**Fix**:
1. Estendere la firma di `findPromoteMatch`:
   ```ts
   export function findPromoteMatch(
       typeA: string, typeB: string, t: (key: string) => string,
       context?: {brokerA?: number; brokerB?: number; currencyA?: string; currencyB?: string; assetA?: number; assetB?: number; qtyA?: number; qtyB?: number}
   ): PromoteMatch | null
   ```
2. Se `context` è fornito, verificare i `field_constraints` della regola prima di restituire il match:
   - `broker_id: different` → `context.brokerA !== context.brokerB`
   - `broker_id: equal` → `context.brokerA === context.brokerB`
   - `cash_currency: equal` → `context.currencyA === context.currencyB`
   - `cash_currency: different` → `context.currencyA !== context.currencyB`
   - `asset_id: equal` → `context.assetA === context.assetB`
   - `quantity: opposite` → segni opposti di `qtyA`/`qtyB`
   - `cash_amount: opposite` → segni opposti (già coperto da currency check)
3. Se `context` non è fornito → fallback al comportamento attuale (primo match = backward compat per la Main Table toolbar dove il context è disponibile dai `selectedRows`)
4. **Ma**: nella Main Table `onPromotePair()`, passare il context dai `selectedRows`:
   ```ts
   const match = findPromoteMatch(a.type, b.type, $_, {
       brokerA: a.broker_id, brokerB: b.broker_id,
       currencyA: a.cash?.code, currencyB: b.cash?.code,
       assetA: a.asset_id, assetB: b.asset_id,
       qtyA: Number(a.quantity), qtyB: Number(b.quantity),
   });
   ```
5. Nel BulkModal `selectedForPromote` e `localSuggestions`, passare il context dai `DraftFields`.
6. Se nessun match con constraint → `null` (nessun suggest sbagliato è meglio di uno errato).

**Backend**: nessuna modifica necessaria — il backend già verifica i constraint correttamente. La `field_constraints` viene esposta nel response di `GET /transactions/types` quindi il frontend ha già i dati per la verifica client-side.

**Rispost all'utente re: cambio valute nello stesso broker**: Sì, è vincolato. FX_CONVERSION richiede `broker_id: equal` + `cash_currency: different`. CASH_TRANSFER richiede `broker_id: different` + `cash_currency: equal`. Quindi:
- Stessa valuta, broker diversi → CASH_TRANSFER (bonifico)
- Valuta diversa, stesso broker → FX_CONVERSION (cambio valute)
- Stessa valuta, stesso broker → nessun match (non ha senso)
- Valuta diversa, broker diversi → nessun match (non ha senso)

---

### Step F5 — Fix promote locale crea 2 righe separate | B16) — ~2h

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

**Problema**: `executePromote()` per 2 new rows (riga 1620-1629) assegna `link_uuid` condiviso e muta i tipi, ma le 2 ops restano come 2 righe separate nella griglia.

**Fix** (decisione DD-BF2 — helper dedicato `collapseIntoPaired`):

1. Creare helper:
   ```ts
   /** Collapse two standalone ops into one paired row (main + hidden partner).
    *  Used post-promote and for consistency with collapsePairedOps() at init.
    *  @returns {main, removeTempId} — the caller must filter out removeTempId from ops. */
   function collapseIntoPaired(opA: PendingOp, opB: PendingOp): {main: PendingOp; removeTempId: string} {
       // Determine from/to: "from" = negative cash or negative qty
       const cashA = Number(opA.fields.cash?.amount ?? 0);
       const cashB = Number(opB.fields.cash?.amount ?? 0);
       const qtyA = Number(opA.fields.quantity ?? 0);
       const qtyB = Number(opB.fields.quantity ?? 0);
       let from = opA, to = opB;
       if (cashA > 0 && cashB <= 0) { from = opB; to = opA; }
       else if (cashA === 0 && cashB === 0 && qtyA > 0) { from = opB; to = opA; }
       // Set partner display on "from" (the main visible row)
       from.partnerId = opTxId(to);
       from.partnerBrokerId = to.fields.broker_id;
       from.partnerCash = to.fields.cash;
       from.partnerDate = to.fields.date;
       from.partnerPayload = opToTxFields(to) as unknown as TxFields;
       return {main: from, removeTempId: to.tempId};
   }
   ```

2. In `executePromote()`, dopo aver mutato i tipi e settato link_uuid, chiamare:
   ```ts
   // Collapse into paired row
   const {main, removeTempId} = collapseIntoPaired(opA, opB);
   ops = ops.filter(o => o.tempId !== removeTempId);
   ops = [...ops]; // trigger reactivity
   ```

3. Questo pattern è **identico per tutti e 3 i casi promote** (2 new, 2 saved, mixed):
   - Dopo aver accumulato in `pendingPromotes` (se serve) e mutato i tipi → collapsare
   - Il caso 2 saved: opB.tempId viene rimosso dall'array ops (la riga non è più visibile singolarmente)

---

### Step F6 — Fix BulkModal first-open broken grid (B4) — ✅ COMPLETATO

**Status**: ✅ Risolto — fix applicata e verificata manualmente (2026-05-13)

**File modificato**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (righe 286-363)

**Ipotesi investigate e ESCLUSE da test manuale**:
- ❌ Race condition sugli store → atteso 1 min, 366 data-testid presenti, store caricati
- ❌ ResizeObserver → resize finestra, nessun effetto
- ❌ FormModal auto-open → bug anche con 2 rows senza auto-open
- ❌ `patchDualRowFromForm` → breakpoint mai colpito su cancel
- ❌ localStorage stale → pulizia `tx-bulk-modal` localStorage keys, nessun effetto

**Root cause CONFERMATA (breakpoint a riga 157 di transactionTypeStore.ts)**:

`getTypeRule(code)` restituisce `FALLBACK_RULE` (con `requiresPair: false`) quando `_ruleMap` è vuoto (types non caricati dal server). Il `$effect` init del BulkModal assegna `ops` **sincronamente**, prima che `ensureTypesLoaded()` completi il fetch asincrono. Di conseguenza:

1. **Primo open post-refresh**: `_ruleMap = {}` → `getTypeRule('TRANSFER')` restituisce `FALLBACK_RULE` → `requiresPair = false` → DataTable rende righe paired come singles → layout rotto
2. **Secondo open**: types già cached in `_cache` → `_ruleMap` populato → `getTypeRule('TRANSFER')` restituisce la rule corretta → `requiresPair = true` → layout corretto

**Prove decisive** (eseguite dall'utente con console breakpoint):
```js
// Primo open dopo refresh:
console.log('_ruleMap keys:', Object.keys(_ruleMap)); // → []
console.log('code:', 'TRANSFER', 'found:', !!_ruleMap['TRANSFER']); // → false

// Secondo open (types cached):
console.log('_ruleMap keys:', Object.keys(_ruleMap)); // → ['BUY','SELL',...12 types]
console.log('code:', 'TRANSFER', 'found:', !!_ruleMap['TRANSFER']); // → true
```

**Fix applicata** — deferred `ops` assignment:

Il `$effect` init ora usa un **dual-path**:
- **Fast path** (`isTypesLoaded() === true`): assegna `ops` + `scheduleAutoOpen` immediatamente (comportamento esistente, nessuna latenza aggiuntiva). Questo path copre tutti gli open successivi al primo.
- **Slow path** (`isTypesLoaded() === false`): assegna `ops = []` (DataTable vuota, nessun rendering sbagliato). Dopo `Promise.all([...ensureTypesLoaded()])`, ricostruisce `next2` e assegna `ops = next2`. Il DataTable render correttamente con `_ruleMap` populato.

```ts
// B4-fix: Build ops eagerly but only assign after types are loaded,
// because getTypeRule() returns FALLBACK_RULE (requiresPair=false)
// until _ruleMap is populated → paired rows render as singles.
if (isTypesLoaded()) {
    // Fast path: types already cached → assign + auto-open immediately.
    ops = next;
    initialOpsKey = serializeOps(next);
    scheduleAutoOpen(autoForm, next);
} else {
    // Slow path: keep ops empty so DataTable doesn't render
    // with FALLBACK_RULE. Ops will be assigned after Promise.all.
    ops = [];
    initialOpsKey = '';
}
// ... then in the async IIFE after Promise.all:
// B4-fix: if ops was deferred (slow path), rebuild + assign now.
if (ops.length === 0 && rows.length > 0) {
    let next2 = /* rebuild from rows */;
    next2 = collapsePairedOps(next2);
    ops = next2;
    initialOpsKey = serializeOps(next2);
}
```

**Perché `collapsePairedOps()` non è affetto**: `collapsePairedOps()` usa `related_transaction_id` (dal txStore, già caricato) per la pair detection — NON dipende da `getTypeRule()`. Il problema era solo nel rendering delle colonne DataTable, dove le column definitions usano `getTypeRule()` per determinare se mostrare il layout paired (Da:/A:) o single.

---

### Step F7 — PromoteMergeModal redesign (B7, B8, B9, B10) — ~3h

**File**: `frontend/src/lib/components/transactions/PromoteMergeModal.svelte`

**Decisioni**: DD-BF5 — usare `TagInput.svelte` (già standalone in `$lib/components/ui/TagInput.svelte`).

**Sottoproblemi**:

**F7a — Fix i18n (B7)**: Il sottotitolo a riga 86 riusa `mergeTitle` (duplicato). Sostituire con nuova chiave `promote.mergeSubtitle`. Aggiungere in 4 lingue.

**F7b — Redesign layout (B8, B9)**: Nuovo layout stacked (funziona sia desktop che mobile):

```
┌─────────────────────────────────────────────────┐
│  🔗 Promote to {targetTypeLabel}            [X] │
│                                                  │
│  Resolve divergent fields:                       │
│                                                  │
│  ─── Description ────────────────────────────── │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ #39 readonly  │  │ #38 readonly  │  ← clic = seleziona
│  │ (description) │  │ (description) │             │
│  └──────────────┘  └──────────────┘             │
│  ┌──────────────────────────────────┐           │
│  │ Merged result (editable textarea) │           │
│  │ [⟷ Concat]                       │           │
│  └──────────────────────────────────┘           │
│                                                  │
│  ─── Tags ───────────────────────────────────── │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ #39 [tag1]   │  │ #38 [tag1]   │  ← clic = seleziona
│  │ [tag2][tag3]  │  │ [tag2]       │             │
│  └──────────────┘  └──────────────┘             │
│  ┌──────────────────────────────────┐           │
│  │ <TagInput> con balloon + search   │  ← componente TagInput.svelte
│  │ [⟷ Union]                        │           │
│  └──────────────────────────────────┘           │
│                                                  │
│  ────── Global actions ─────────────────────── │
│  [◀ All left]    [⟷ All merge]    [All right ▸] │
│                                                  │
│                     [Cancel] [🔗 Confirm promotion] │
└─────────────────────────────────────────────────┘
```

**Logica**:
- I 2 blocchi readonly sono **bottoni clickabili**: click = copia quel valore nel merge
- Il blocco merge è editabile
- Per description: usare `<textarea>` con `rows=3` e `white-space: pre-wrap` (B10)
- Per tags: usare `<TagInput value={resTags} availableTags={allTagSuggestions} onchange={(v) => resTags = v} />`
  - `allTagSuggestions` = union di tags da txA.tags + txB.tags + availableTags (passato come prop)
- Tags nei blocchi readonly: colorati con `getStringColor()` per coerenza con il FormModal
- Bottoni globali in fondo: `◀ All left`, `⟷ All merge`, `All right ▸`

**F7c — Mobile (B9)**: I 2 readonly sono in `grid grid-cols-2`, il merge sotto è `col-span-2`. Funziona nativamente su qualsiasi viewport.

---

### Step F8 — Split ConfirmModal arricchita (B2) — ~1h

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

**Fix**: La ConfirmModal per split deve mostrare le 2 TX con i dettagli:
- 2 colonne: TX originale (sinistra) → TX splittata (destra)
- Per ciascuna: tipo (con icona), asset, broker, qty/amount
- Mostrare i nuovi tipi post-split (es. TRANSFER → ADJUSTMENT)

**Implementazione**: Usare un `ConfirmModal` con slot `message` custom (HTML rich) o un componente dedicato `SplitConfirmContent.svelte`.

---

### Step F9 — Promote ConfirmModal arricchita (B6) — ~30min

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

**Fix**: Come B2 ma per promote. Mostrare le 2 TX originali e il tipo target:
- Colonna sinistra: TX A (tipo, broker, amount, asset)
- Colonna destra: TX B (tipo, broker, amount, asset)
- Centro/sotto: tipo target con icona

---

### Step F10 — Main Table actions layout (B3) — ~30min

**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`

**Fix**:
1. Allargare `width` della colonna actions (minWidth da ~120 a ~180).
2. Allineare i bottoni a destra (flex `justify-end`).

---

### Step F11 — Commit toast migliorato (B18) — ~15min

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

**Fix**: `handleBulkCommitted()` deve generare messaggi localizzati completi:
- `✅ Salvate 3 transazioni` (non `✅ 3 create`)
- Usare chiavi i18n: `transactions.toast.commitSummary`: "Saved {n} transactions"
- Includere split e promote nel conteggio.

---

### Step F12 — i18n chiavi mancanti — ~30min

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Chiavi da aggiungere:

| Key | EN | IT | FR | ES |
|-----|----|----|----|----|
| `transactions.promote.mergeSubtitle` | `Resolve divergent fields:` | `Risolvi i campi divergenti:` | `Résoudre les champs divergents :` | `Resolver campos divergentes:` |
| `transactions.promote.allLeft` | `All left` | `Tutti sinistra` | `Tout à gauche` | `Todo izquierda` |
| `transactions.promote.allMerge` | `All merge` | `Unisci tutti` | `Tout fusionner` | `Combinar todo` |
| `transactions.promote.allRight` | `All right` | `Tutti destra` | `Tout à droite` | `Todo derecha` |
| `transactions.promote.concat` | `Concatenate` | `Concatena` | `Concaténer` | `Concatenar` |
| `transactions.promote.union` | `Union` | `Unione` | `Union` | `Unión` |
| `transactions.split.fromType` | `Will become: {type}` | `Diventerà: {type}` | `Deviendra : {type}` | `Se convertirá en: {type}` |
| `transactions.toast.commitSummary` | `Saved {n} transactions` | `Salvate {n} transazioni` | `{n} transactions enregistrées` | `{n} transacciones guardadas` |
| `transactions.toast.splitCount` | `{n} split` | `{n} scollegati` | `{n} dissociés` | `{n} separados` |
| `transactions.toast.promoteCount` | `{n} promoted` | `{n} promossi` | `{n} promus` | `{n} promocionados` |
| `transactions.promoteSuggest.bannerDetailed` | `On {date}, Row #{a} and Row #{b} could become {type}` | `In data {date}, la riga #{a} e la riga #{b} potrebbero diventare {type}` | `Le {date}, la ligne #{a} et la ligne #{b} pourraient devenir {type}` | `El {date}, la fila #{a} y la fila #{b} podrían convertirse en {type}` |
| `transactions.bulk.splitQueued` | `{n} split queued` | `{n} split in coda` | `{n} dissociations en file` | `{n} separaciones en cola` |

---

### Step F13 — Validation error codes enum (B19) — ~2h

**Backend**: `backend/app/schemas/transactions.py`
**Backend**: `backend/app/services/transaction_service.py`
**Backend**: `backend/app/api/v1/transactions.py`

**Decisione**: DD-BF6 — enum ora + esporre in `GET /transactions/types`.

**Fix**:
1. Creare un `TXValidationCode` enum (StrEnum) in `transactions.py`:
   ```python
   class TXValidationCode(str, Enum):
       BALANCE_ASSET_NEGATIVE = "balanceAssetNegative"
       BALANCE_CASH_NEGATIVE = "balanceCashNegative"
       TX_NOT_FOUND = "txNotFound"
       NO_PAIR_TO_SPLIT = "noPairToSplit"
       PARTNER_NOT_FOUND = "partnerNotFound"
       TYPE_CANNOT_SPLIT = "typeCannotSplit"
       PROMOTE_REF_NOT_FOUND = "promoteRefNotFound"
       ALREADY_PAIRED = "alreadyPaired"
       NO_PROMOTE_RULE = "noPromoteRule"
       ACCESS_DENIED = "accessDenied"
       PARSE_ERROR = "parseError"
       TYPE_SWAP_FORBIDDEN = "typeSwapForbidden"
       EXTRA_FORBIDDEN = "extra_forbidden"
       LINK_UUID_PAIR_COUNT = "linkUuidPairCount"
   ```
2. Usare `TXValidationCode.XXX.value` ovunque si costruisce `TXValidationIssue` nel `transaction_service.py`.
3. Aggiungere un campo `validation_codes: list[TXValidationCodeInfo]` nella response di `GET /transactions/types` (dentro `TXTypesResponse`):
   ```python
   class TXValidationCodeInfo(BaseModel):
       code: str
       description: str
       severity: Literal["error", "warning"]
   ```
4. Nel frontend `resolveValidationMessage.ts`, mappare i codici ai messaggi i18n dinamicamente (lookup dalla response di types).
5. `./dev.py api sync` per rigenerare il client TS.

---

### Step F14 — E2E Test Suite `tx-split-promote.spec.ts` — ~4h

**New file**: `frontend/e2e/transactions/tx-split-promote.spec.ts`

Scenari:

| # | Test | Scenario | Verifica |
|---|------|----------|----------|
| 1 | Split da Main Table | Trova paired `delete-safe`, 3 puntini → Split → Confirm → 2 righe ADJUSTMENT standalone | row actions, confirm modal, table update |
| 2 | Split da BulkModal (saved) | Edit paired → bulk → split row action → riga rimossa + badge split queued → commit | `pendingSplits` nel payload, backend result |
| 3 | Promote da Main Table (identico) | Seleziona 2 `promote-test` withdraw+deposit → Promote → confirm | CASH_TRANSFER pair in table |
| 4 | Promote da Main Table (divergente) | Seleziona 2 con desc/tags diversi → MergeModal → resolve → confirm | MergeModal fields, resolved payload |
| 5 | Promote suggest banner nel BulkModal | Edit 2+ standalone compatibili → banner verde visibile | `data-testid="promote-suggest-banner"` |
| 6 | Promote suggest → click 🔗 | Banner → click link → auto-promote → righe collassate in 1 paired | Da:/A: rendering |
| 7 | Guard: split nascosto su standalone | TX senza `related_transaction_id` → no split button | row action assente |
| 8 | Guard: promote nascosto su paired | TX con `related_transaction_id` → no promote toolbar | toolbar assente |
| 9 | Split+Promote mixed batch | In BulkModal: split 1 pair + promote 2 standalone → commit | Payload contiene `splits[]` + creates/updates |
| 10 | BulkModal open after page refresh | Refresh → edit linked → Apply → BulkModal OK | No race condition |

**Registration**: `scripts/test_runner/_frontend_transaction.py` + `front_transaction_all()`.

---

## 📊 Step Classification & Priorità

| Step | Tipo | Stima | Priorità | Dipendenze |
|------|------|-------|----------|------------|
| F1 | ✅ **Completato** | ~30min | P0 | — |
| F2 | ✅ **Completato** | ~1.5h | P0 | — |
| ~~F3~~ | ~~🔍 Investigate~~ | — | — | ✅ Risolto da F4 |
| F4 | ✅ **Completato** | ~1.5h | P0 | — |
| F5 | ✅ **Completato** | ~2h | P0 | — |
| F6 | ✅ **Completato** | ~1.5h | P0 | ✅ Fix applicata 2026-05-13 |
| F7 | ✅ **Completato** | ~3h | P1 | F12 |
| F8 | 🟡 UX | ~1h | P2 | — |
| F9 | 🟡 UX | ~30min | P2 | — |
| F10 | ✅ **Completato** | ~30min | P2 | — |
| F11 | ✅ **Completato** | ~15min | P2 | F12 |
| F12 | ✅ **Completato** | ~30min | P1 | — |
| F13 | ✅ **Completato** | ~2h | P1 | — |
| F14 | ✅ **Completato** | ~4h | P1 | F1-F6 |

**Totale stimato**: ~20h

---

## 🔀 Ordine di esecuzione

```
Wave 1 — Critical fixes (P0):
  ✅ F6 (BulkModal first-open: COMPLETATO — deferred ops assignment)
  ✅ F1 (mock data balance) — 2026-05-13: BUY AAPL +5 day -9 balance-safe
  ✅ F12 (i18n keys) — 2026-05-13: 12 keys × 4 lingue
         ↓
  ✅ F2 (BulkModal split: rimuovi dal batch + badge splitQueued) — 2026-05-13
         ↓
  ✅ F4 (findPromoteMatch constraint check — risolve anche B12/F3) — 2026-05-13
         ↓
  ✅ F5 (promote collapse: helper collapseIntoPaired) — 2026-05-13

Wave 2 — UX polish (P1-P2):
  ✅ F7 (PromoteMergeModal redesign + TagInput) — 2026-05-13
  ⏳ F8 (Split ConfirmModal arricchita) — P2, rimandata
  ⏳ F9 (Promote ConfirmModal arricchita) — P2, rimandata
  ✅ F10 (Main Table actions layout) — 2026-05-13
  ✅ F11 (Commit toast migliorato) — 2026-05-13

Wave 3 — Tech debt + Tests:
  ✅ F13 (Validation error codes enum + GET /types + api sync) — 2026-05-13
  ⏳ F14 (E2E test suite) — TODO
```

---

## Riepilogo file modificati

| File | Tipo modifica | Step |
|------|--------------|------|
| `backend/test_scripts/test_db/populate_mock_data.py` | Fix balance data | F1 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | ✅ F6 deferred ops. Split: rimuovi da batch + badge. Promote: `collapseIntoPaired()`. | F2, F5, ✅F6 |
| `frontend/src/lib/stores/transactionTypeStore.ts` | `findPromoteMatch` + constraint check con context opzionale | F4 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Split/promote confirm modals, toast, promote context | F8, F9, F11 |
| `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` | Redesign completo con TagInput, textarea, layout stacked | F7 |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Actions column width + align right | F10 |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | ~12 nuove chiavi × 4 lingue | F12 |
| `backend/app/schemas/transactions.py` | `TXValidationCode` enum + `TXValidationCodeInfo` + esporre in TXTypesResponse | F13 |
| `backend/app/services/transaction_service.py` | Usare enum codes | F13 |
| `backend/app/api/v1/transactions.py` | TXTypesResponse estesa | F13 |
| `frontend/src/lib/utils/resolveValidationMessage.ts` | Dynamic code mapping dal types response | F13 |
| `frontend/e2e/transactions/tx-split-promote.spec.ts` | **NUOVO** — 10 scenari E2E | F14 |
| `scripts/test_runner/_frontend_transaction.py` | Register new spec | F14 |

---

## Rischi e mitigazioni

| Rischio | Prob. | Mitigazione |
|---------|-------|-------------|
| F2 rimuovere la riga spezza il flusso utente | Bassa | Badge "split queued" chiaro + comportamento coerente |
| F4 constraint check client-side diverge dal backend | Media | I constraint vengono da TX_TYPE_METADATA (stessa source) — test E2E verifica end-to-end |
| F5 `collapseIntoPaired` per create ops: partnerPayload non mappato correttamente | Media | Unit test sul helper + test E2E F14 scenario 6 |
| F7 redesign PromoteMergeModal regressione | Media | Test E2E F14 scenario 4 |

---

## Decisioni rimandate (fuori scope)

| Item | Motivo |
|------|--------|
| Context menu promote per 2 righe selezionate (B21) | UX nice-to-have, non critico per il rilascio D2 |
| BulkModal row ordering con `orderItem` (B17) | Impatto basso, rischio di regressione |
| Backend response con entrambi gli ID per promote (B11) | Richiede modifica schema, basso ROI |

---

## 🧪 Non-Regression Test Plan

Oltre ai 10 scenari di F14 (`tx-split-promote.spec.ts`), servono test specifici per garantire che le fix non regrediscano. Questi test vanno integrati in F14 o in un file separato `tx-bulk-init.spec.ts`.

### Test per F6 — BulkModal deferred ops (non-regression `getTypeRule` + `FALLBACK_RULE`)

| # | Test | Precondizioni | Azioni | Verifiche |
|---|------|--------------|--------|-----------|
| NR-1 | BulkModal open paired dopo page refresh | Pagina transactions con TX TRANSFER paired | `page.reload()` → attendi table → click Edit su paired row → Apply | Grid non rotta: presenza di `data-testid="paired-from-label"` O colonne Da:/A: visibili |
| NR-2 | BulkModal open single dopo page refresh | Pagina transactions con TX standalone | `page.reload()` → attendi table → click Edit su single row → Apply | FormModal si apre (auto-open), tipo corretto visibile |
| NR-3 | BulkModal open 2+ rows dopo refresh | 2 righe selezionate | `page.reload()` → attendi table → seleziona 2 → Edit → Apply | Grid mostra 2 righe con colonne corrette, nessun layout rotto |
| NR-4 | BulkModal secondo open identico | Qualsiasi TX | Open → cancel → re-open | Grid identica in entrambi gli open (nessuna differenza visiva) |

**Pattern di implementazione**:
```ts
test('NR-1: BulkModal renders paired correctly after page refresh', async ({page}) => {
    await login(page);
    await navigateTo(page, 'transactions');
    // Find a TRANSFER paired row
    const pairedRow = page.locator('[data-testid="tx-row"]').filter({has: page.locator('[data-testid="pair-icon"]')}).first();
    await expect(pairedRow).toBeVisible({timeout: 10000});

    // Refresh → reopen
    await page.reload();
    await expect(page.locator('[data-testid="tx-row"]').first()).toBeVisible({timeout: 10000});

    // Click edit on paired row
    await pairedRow.locator('[data-testid="row-action-edit"]').click();
    // Apply to open BulkModal
    await page.locator('[data-testid="bulk-apply-btn"]').click();
    await expect(page.locator('[data-testid="bulk-modal"]')).toBeVisible({timeout: 5000});

    // Verify paired rendering (not broken singles)
    const pairedLabel = page.locator('[data-testid="bulk-modal"] [data-testid^="paired-"]');
    await expect(pairedLabel.first()).toBeVisible({timeout: 5000});
});
```

### Test per F4 — `findPromoteMatch` constraint check

| # | Test | Precondizioni | Azioni | Verifiche |
|---|------|--------------|--------|-----------|
| NR-5 | Suggest banner show CASH_TRANSFER (not FX_CONVERSION) | 2 standalone: WITHDRAWAL + DEPOSIT, same currency, diff broker | Edit both → BulkModal → attendi suggest banner | Banner mostra `→ Cash Transfer` (non `→ Cambio Valuta`) |
| NR-6 | Suggest banner shows FX_CONVERSION | 2 standalone: WITHDRAWAL + DEPOSIT, diff currency, same broker | Edit both → BulkModal → attendi suggest banner | Banner mostra `→ FX Conversion` |
| NR-7 | No suggest for incompatible pair | 2 standalone: WITHDRAWAL + DEPOSIT, diff currency + diff broker | Edit both → BulkModal | Nessun suggest banner visibile |

### Test per F2 — Split saved nel BulkModal

| # | Test | Precondizioni | Azioni | Verifiche |
|---|------|--------------|--------|-----------|
| NR-8 | Split saved rimuove riga e mostra badge | TX paired TRANSFER nel BulkModal | Click split action su riga paired | Riga rimossa da grid + badge "⚡ N split in coda" visibile |
| NR-9 | Split saved + commit | Dopo NR-8 | Click Commit | Payload contiene `splits:[{id:X}]`, NO `updates` con type change |

### Test per F5 — Promote collapse

| # | Test | Precondizioni | Azioni | Verifiche |
|---|------|--------------|--------|-----------|
| NR-10 | Promote 2 new collapses into paired | 2 new rows: WITHDRAWAL + DEPOSIT, same currency, diff broker | Seleziona entrambi → Promote → Confirm | 1 riga paired (Da:/A:), non 2 righe separate |
| NR-11 | Promote 2 saved collapses | 2 saved standalone compatibili | Seleziona → Promote → Confirm/MergeModal → Confirm | 1 riga paired nel grid, `pendingPromotes` nel payload |

---

## 🔗 Cross-links

- **Parent (D2)**: [`plan-PlanD2_FrontendSplitPromoteUI.prompt.md`](../plan-PlanD2_FrontendSplitPromoteUI.prompt.md)
- **D1 Backend**: [`plan-PlanD1_BackendBatchSuggest.prompt.md`](../plan-PlanD1_BackendBatchSuggest.prompt.md)
- **Parent plan (D)**: [`plan-phase07-PlanD_SplitPromoteFullStack.prompt.md`](../../plan-phase07-PlanD_SplitPromoteFullStack.prompt.md)
- **Next (Bugfix 2)**: [`plan-bugfix2_PayloadSplitPreviewUX.prompt.md`](./plan-bugfix2_PayloadSplitPreviewUX.prompt.md)
- **Next (D3 E2E)**: Embedded in this plan as Step F14

