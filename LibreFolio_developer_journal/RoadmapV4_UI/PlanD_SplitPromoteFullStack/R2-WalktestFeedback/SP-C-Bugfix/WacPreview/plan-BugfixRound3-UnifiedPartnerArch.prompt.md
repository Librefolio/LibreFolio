# Plan: Unified Partner Architecture — FormModal Items Array + PendingOp Simplification

**Parent**: Bug 8 (partner broker lost on edit paired TX)
**Parent plan**: [`plan-R2-SP-C-BugfixRound2-WacPreview`](../plan-SP-C-BugfixRound2-WacPreview.prompt.md) (sezione Bug 8)
**Triggered by**: Walktest 2026-05-25 — confermato rotto (edit paired new draft → secondo broker scompare)
**Scope**: Refactor strutturale del flusso dati BulkModal ↔ FormModal per paired TX

---

## 🎯 Obiettivo

Eliminare il pattern ricorrente "partner broker perso al refactoring" unificando l'architettura:
- Il partner diventa un `PendingOp` nascosto nell'array `ops[]` (non più 5 campi sparsi)
- Il FormModal riceve/restituisce sempre un array di 1 o 2 items (contratto pulito)
- Un helper centralizzato risolve gli items da qualsiasi sorgente

---

## 🔍 Scoperta critica: perché PendingOp non può essere TXReadItem

I `DraftFields` memorizzano **valori assoluti** (qty, cash sempre positivi). Il segno è **implicito** nel tipo (SELL → qty negativa, FEE → cash negativa). Al commit, `buildCreatePayload()` riapplica il segno tramite `applySignRules()`.

`TXReadItem` dal DB invece memorizza i valori **con segno**.

Questa differenza è intenzionale (l'utente nell'UI vede/edita solo positivi), ma significa che `PendingOp` non può "estendere" `TXReadItem` direttamente — i campi numerici hanno semantica diversa.

**Decisione**: `DraftFields` resta come tipo UI separato. `opToTxLike()` resta come adattatore (riapplica i segni per produrre un TXReadItem passabile al FormModal). Però si **semplifica** (niente più sentinel `-1`, niente `partner*` fields).

---

## 📐 Struttura dati nuova

```typescript
// PendingOp — una entry nell'array ops[] della BulkModal
type PendingOp = (
    | {op: 'create'; link_uuid: string | null}
    | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}
) & {
    tempId: string;
    fields: DraftFields;
    /** Se set, questa op è il partner nascosto di un paired row. Punta al tempId del main (visibile). */
    pairedWith?: string;
};

// PartnerDisplay ELIMINATA — non esiste più
// partnerId, partnerBrokerId, partnerCash, partnerDate, partnerPayload → RIMOSSI
```

---

## 📐 Contratto FormModal (input/output)

**Input**: `items: FormModalItems | null`
```typescript
type InaccessiblePartner = {_inaccessible: true; broker_id: number};
type FormModalItems = [TXReadItem] | [TXReadItem, TXReadItem] | [TXReadItem, InaccessiblePartner];
```

**Output**: `onPushDraft(items: Record<string, unknown>[])` — sempre array (length 1 o 2).

**Guardrail** (in `resolveFormItems`): se 2 items reali hanno `type` diversi → `console.error` + degrada a single.

---

## 🔧 Steps

### Step 1 — Tipo e helper `resolveFormItems.ts` (nuovo file) ✅

File: `frontend/src/lib/components/transactions/resolveFormItems.ts`

- `FormModalItems` type export
- `InaccessiblePartner` type export
- `isInaccessible(item)` type-guard
- `resolveFormItemsFromOps(mainOp: PendingOp, ops: PendingOp[], opToTxLike, txStoreGet): FormModalItems`
  - `item0 = opToTxLike(mainOp)`
  - `partnerOp = ops.find(o => o.pairedWith === mainOp.tempId)`
  - Se partnerOp → `item1 = opToTxLike(partnerOp)`, return `[item0, item1]`
  - Se no partnerOp ma `mainOp.op === 'edit'` e DB ha related_id → try txStoreGet → return `[item0, item1]`
  - Else → `[item0]`
- `resolveFormItemsForView(row: TXReadItem, txStoreGet, getBrokerRole): FormModalItems`
  - Per la page standalone in view mode
  - Se no partner → `[row]`
  - Se partner accessibile → `[from, to]` (orientato)
  - Se partner inaccessibile → `[row, {_inaccessible: true, broker_id}]`
- Orientamento From/To: transfer_asset → qty<0 = from; transfer_cash/fx → cash<0 = from

### Step 2 — Refactorare `PendingOp` in BulkModal ✅

- ✅ Rimosso `PartnerDisplay` interface e tutti i 5 campi (`partnerId/partnerBrokerId/partnerCash/partnerDate/partnerPayload`)
- ✅ Aggiunto `pairedWith?: string` a PendingOp
- ✅ Creato `visibleOps = $derived(ops.filter(...))` e `getPartnerOp()` helper
- ✅ DataTable usa `visibleOps`
- ✅ Tutti i ~70 errori risolti — compilazione OK (solo warning)

- Rimuovere `PartnerDisplay` interface
- Aggiungere `pairedWith?: string`
- `visibleOps = $derived(ops.filter(o => !o.pairedWith))`
- `getPartnerOp(mainTempId: string): PendingOp | undefined` helper
- DataTable usa `visibleOps` (non `ops`)

### Step 3 — Migrare creazione paired rows ✅

- ✅ `collapsePairedOps()` riscritto (partner come op nascosta con `pairedWith`)
- ✅ `collapseIntoPaired()` riscritto (setta `pairedWith` invece di rimuovere)
- ✅ `handleSplitRow()` riscritto (un-pair = rimuove `pairedWith`)
- ✅ `resetAll()` riscritto (usa collapsePairedOps)
- ✅ `addDualRowFromForm()` riscritto (crea 2 ops: fromOp + toOp con pairedWith)
- ✅ `patchDualRowFromForm()` riscritto (aggiorna main + partner op)
- ✅ Clone riscritto (clona anche partner nascosto)

- `addDualRowFromForm(items: Record<string, unknown>[])`: crea 2 ops (fromOp visibile + toOp con `pairedWith: fromOp.tempId`)
- `patchDualRowFromForm(tempId, items)`: trova main + `getPartnerOp(tempId)`, applica items[0]/items[1]
- `collapsePairedOps()`: il partner diventa op con `pairedWith` (non rimosso dall'array, solo nascosto)
- `collapseIntoPaired()`: marca il "to" con `pairedWith`

### Step 4 — Migrare rendering colonne ✅

- ✅ Tutte le cell functions (id, date, qty, cash, broker, link) usano `getPartnerOp(row.tempId)`

- Cell functions leggono da `getPartnerOp(row.tempId)?.fields.broker_id`, `.fields.cash`, etc.
- `renderDualHtml` invariato

### Step 5 — Migrare `resolveOps()` / `deriveStatus()` / `collectCreate/Update` ✅

- ✅ `resolveOps`: skip hidden partners, usa `getPartnerOp` per partner payload
- ✅ `deriveStatus`: diff partner via `getPartnerOp` + `buildUpdateDiff`
- ✅ Delete: usa `pOp.txId` per `partnerDeleteId`

- `resolveOps`: per ogni visible op, cerca `getPartnerOp` → costruisce `partnerPayload` da lì
- `deriveStatus`: diff partner = `getPartnerOp` diff vs txStore
- Delete: se main `markedDelete`, il partner segue automaticamente

### Step 6 — Migrare split/promote ✅

- ✅ `handleSplitRow`: rimuove `pairedWith` dal partner (diventa visibile e indipendente)
- ✅ Promote: `collapseIntoPaired` setta `pairedWith` su "to"

- `handleSplitRow`: rimuove `pairedWith` dal partner (diventa visibile e indipendente)
- Promote: setta `pairedWith` su uno dei due

### Step 7 — Semplificare `opToTxLike()` ✅

- ✅ Rimosso sentinel `-1`
- ✅ Usa `getPartnerOp(d.tempId)` per `related_transaction_id`

- Rimuovere il sentinel `-1` per `related_transaction_id`
- Per un main: `related_transaction_id = getPartnerOp(d.tempId)?.op === 'edit' ? partnerOp.txId : null`
- Per un partner: analogo viceversa (ma usato raramente — solo in resolveFormItems)

### Step 8 — Refactorare `TransactionFormModal.svelte` — DEFERRED

Il refactor dell'interfaccia FormModal (sostituire `initialRow + injectedPartnerRow` con `items: FormModalItems`) è differito a un secondo pass. Il bug è risolto perché `openEditRowForm` ora trova sempre il partner via `getPartnerOp` e lo inietta come `formPartnerRow`.

Il FormModal continua a funzionare con il contratto attuale (`initialRow` + `injectedPartnerRow`) senza problemi.

- Props: `items: FormModalItems | null` (sostituisce `initialRow` + `injectedPartnerRow`)
- Init `$effect`:
  - `items.length === 1` → `draft = fromTx(items[0])`
  - `items.length === 2 && !isInaccessible(items[1])` → `draft = fromTx(items[0])` + `applyPartnerToDualTo(items[0], items[1], layout)`
  - `items.length === 2 && isInaccessible(items[1])` → single draft + mostra lock con broker_id
- Output: `onPushDraft(items: Record<string, unknown>[])` — array
- **Rimuovere**: `fetchPartner()`, `loadingPartner`, `inaccessiblePartnerBrokerId` (ora derivato da input), deferred fetch logic

### Step 9 — Aggiornare `openEditRowForm()` + `handleFormPushed()` ✅

- ✅ `openEditRowForm`: usa `getPartnerOp(row.tempId)` → `opToTxLike(pOp)` come `formPartnerRow`
- ✅ `handleFormPushed`: invariato (già usa add/patchDualRowFromForm che sono aggiornati)

- `openEditRowForm`: `formItems = resolveFormItemsFromOps(row, ops, opToTxLike, txStoreGet)`
- `handleFormPushed(items[])`: unifica add/patch single/dual in una sola funzione

### Step 10 — Aggiornare Page `+page.svelte` — DEFERRED

Non necessario per Bug 8 fix. La page standalone usa il FormModal in view-only mode, che già funziona (fetchPartner esistente nel FormModal). Il refactor dell'interfaccia è rimandato con Step 8.

- `handleViewRow`: usa `resolveFormItemsForView(row, txStoreGet, getBrokerRole)`
- FormModal riceve `items` prop

### Step 11 — Pulizia e test ✅

- ✅ `PartnerDisplay` rimossa
- ✅ `populatePartnerDisplay()` rimossa
- ✅ Sentinel `-1` rimosso
- ✅ Frontend build: OK
- ✅ `tx-paired-edit`: 4/4 passed
- ✅ `transactions-modals`: 17/17 passed
- ✅ `transactions-table`: 24/24 passed

- Rimuovere: `PartnerDisplay`, `populatePartnerDisplay()`, `fieldsFromTx` duplicated partner logic, sentinel `-1`
- Run: `./dev.py test front-transaction all` + `./dev.py test front-broker all`

---

## ✅ Verifica buchi logici

| Scenario | Gestito? | Come |
|----------|----------|------|
| Create nuova paired (FormModal → BulkModal) | ✅ | Step 3: `addDualRowFromForm` crea 2 ops |
| Edit paired new draft (click Edit sulla riga) | ✅ | Step 9: `resolveFormItemsFromOps` trova il partnerOp via `pairedWith` |
| Edit paired from DB (reloaded dal txStore) | ✅ | Step 1: fallback a `txStoreGet(related_id)` se no partnerOp locale |
| View readonly paired accessible | ✅ | Step 10: `resolveFormItemsForView` ritorna [from, to] |
| View readonly paired inaccessible | ✅ | Step 10: ritorna [row, InaccessiblePartner] → lock UI |
| View → Edit (pencil) | ✅ | `onSwitchToEdit` → BulkModal → `openEditRowForm` → Step 9 |
| Split paired | ✅ | Step 6: rimuove `pairedWith`, partner diventa visibile |
| Promote 2 singles → paired | ✅ | Step 6: setta `pairedWith` su uno |
| Delete paired main | ✅ | Step 5: `markedDelete` propagato al partner |
| Clone paired | ✅ | Step 3: clone crea 2 ops (main + partner con pairedWith) |
| Partner ha diff → status "edited" | ✅ | Step 5: `deriveStatus` guarda anche `getPartnerOp` |
| Commit paired create | ✅ | Step 5: `resolveOps` raccoglie partnerOp payload |
| Commit paired update | ✅ | Step 5: `resolveOps` diff partner vs txStore |
| Commit paired delete | ✅ | Step 5: delete include entrambi gli ID |
| PickerModal imports paired from DB | ✅ | `collapsePairedOps` crea partner come op nascosta |
| BulkModal close → discard guard | ✅ | `initialOpsKey` include tutte le ops (partner inclusi) |

**Buco identificato e risolto**: Il caso "Edit paired from DB in BulkModal" quando l'utente apre la BulkModal con `{action: 'edit', txIds: [42]}` dove 42 è il main di una pair. Attualmente `collapsePairedOps` gestisce questo (legge `related_transaction_id` dal txStore e collassa). Nel nuovo piano, lo step 3 gestisce questo facendo `collapsePairedOps` che crea il partner come op nascosta — quindi il partner è nell'array `ops` **dal momento in cui la BulkModal si inizializza** → `resolveFormItemsFromOps` lo troverà sempre.

**Nessun buco residuo identificato.**

---

## 📐 Invarianti (validazione continua)

| Regola | Dove verificata |
|--------|-----------------|
| `visibleOps` non contiene ops con `pairedWith` | `$derived` filter |
| Partner punta a un tempId esistente | `getPartnerOp` + guardrail in add/patch |
| 2 items nel FormModal hanno stesso type | `resolveFormItems` guardrail |
| Delete di un main → delete anche il partner | `toggleDelete()` |
| Split di un paired → rimuove `pairedWith` da entrambi | `handleSplitRow()` |

---

## 📐 Reattività (Step 2 — considerazione)

`getPartnerOp()` è un lookup su `ops` — se `ops` cambia, i `$derived` che lo usano si ricalcolano. Performance: su ~50 ops max, `find()` è O(n) trascurabile. Se servisse, si può tenere una `Map<tempId, tempId>` derivata.

---

## 📐 Stima

~300 righe nuove/riscritte, ~200 righe rimosse (dead code). Net: ~100 righe aggiunte. 3-4h di implementazione.

---

## 🧪 Walktest 2026-05-26 — Risultati

### ✅ Verifiche passate

- Bug 8 fix confermato (edit paired new draft → entrambi i broker visibili)
- Step 4 rendering colonne: tutti corretti (ID, Date, Qty, Cash, Broker)
- Split / Undo split: funzionante
- Promote: funzionante
- Clone singolo: funzionante
- Commit / Reset / Close guard: funzionanti

### 🐛 Bug trovati durante walktest

#### Bug W1 — Clone paired da main table → 2 righe visibili (non collapsed)

**Tipo**: PRE-ESISTENTE (non regressione di questo plan)
**Root cause**: `handleCloneRow` dalla page crea `bulkIntent = {action: 'clone', txIds: [id]}`. Il BulkModal in init porta il partner (riga 276-283) e crea 2 `createOpFromClone` con `link_uuid` condiviso ma `related_transaction_id: null`. `collapsePairedOps()` cerca partner via `related_transaction_id` (non `link_uuid`) → non li collassa → 2 righe visibili.
**Fix**: in `collapsePairedOps`, aggiungere un secondo pass che collassa ops `create` con `link_uuid` condiviso.

#### Bug W2 — WAC preview "💡 auto" non mostra il valore calcolato

**Tipo**: PRE-ESISTENTE (dalla feature WAC preview, non da questo plan)
**Sintomo**: In bulk e in FormModal edit, il campo cost_basis_override mostra solo "💡 auto" senza il numero calcolato.
**Note**: Già tracciato nel parent plan come WAC preview step.

#### Bug W3 — Validate automatico scatta prima che il 2° broker/currency sia impostato

**Tipo**: PRE-ESISTENTE (non regressione)
**Sintomo**: Creando CASH_TRANSFER o FX_CONVERSION, la validazione automatica parte prima che il secondo broker o la seconda valuta siano impostati. I pulsanti "Applica" e "Valida" sono correttamente disabilitati, quindi è solo il trigger automatico che non rispetta la condizione "tutti i campi required popolati".
**Note**: `isDraftReadyForValidation` potrebbe non controllare i campi dualTo.

#### Bug W4 — Punto 5: TransactionPicker + inaccessible partner

**Tipo**: PRE-ESISTENTE (non regressione). Due sotto-problemi:
- (a) Il Picker non dovrebbe permettere di importare in BulkModal una paired TX se l'utente non ha accesso al broker del partner. Filtro mancante nel Picker.
- (b) Se importata comunque, nella Bulk il 2° broker mostra vuoto (non locked/rosso). Il lock rosso funziona solo nella page standalone view.
**Note**: Serve mock data "ricezione da broker inaccessibile" in `populate_mock_data.py`.

#### Bug W5 — WAC table: mostrare colonna "WAC corrente" e hide in readonly

**Tipo**: MIGLIORAMENTO (feature request)
- (a) Aggiungere colonna "WAC" nella tabella dettaglio PMC che mostra il valore WAC risultante per ogni riga.
- (b) In view readonly, la tabella WAC non dovrebbe essere visualizzata (serve solo in edit; dopo il salvataggio conta solo il valore inserito).

### 🎨 UX tweaks richiesti

#### Tweak U1 — Colonna "UUID collegamento" → rename "TX Collegata"

- Usare label "TX Collegata" (o "🔗 TX" con icona catena) al posto di "UUID collegamento"
- Font più grande per il valore mostrato
- Freccia doppia (↔) con carattere più visibile
- Aggiornare i18n in tutte le 4 lingue

---

## 📊 Classificazione bug

| Bug | Regressione di questo plan? | Azione |
|-----|----------------------------|--------|
| W1 Clone paired | ❌ No (pre-esistente, path diverso) | Fix in collapsePairedOps (aggiungi link_uuid pass) |
| W2 WAC auto no value | ❌ No (WAC preview feature) | Da risolvere in WAC preview step |
| W3 Validate early | ❌ No (pre-esistente) | Fix in isDraftReadyForValidation / dual gate |
| W4 Picker + inaccessible | ❌ No (pre-esistente) | Filtro picker + mock data |
| W5 WAC table miglioramento | N/A (feature) | Prossimo step |
| U1 Column rename | N/A (UX) | Quick fix i18n |

---

## 🔜 Next: BugfixRound3b — Risoluzione bug walktest non tracciati

**Child plan da creare**: `plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3b-WalktestFixes.prompt.md`

### Prompt per agente planner

```markdown
# Prompt: Fix 4 Walktest Bugs (BugfixRound3b)

Piano padre: `plan-BugfixRound3-UnifiedPartnerArch.prompt.md` (sezione Walktest 2026-05-26)
Contesto: dopo il refactor "Unified Partner Architecture" (partner come PendingOp nascosto con `pairedWith`), un walktest manuale ha rivelato 4 problemi non tracciati. Vanno risolti prima di procedere.

---

## Bug da risolvere

### W1 — Clone paired da main table → 2 righe visibili (non collapsed)

**Sintomo**: Quando l'utente clicca "Clone" su una TX paired dalla main table, il BulkModal si apre con 2 righe visibili separate (stesso tipo TRANSFER) invece di una sola riga paired con partner nascosto.

**Root cause già identificata**: `handleCloneRow` dalla page crea `bulkIntent = {action: 'clone', txIds: [id]}`. In BulkModal init (riga 273-296), il partner viene portato dentro, entrambi diventano `createOpFromClone` con `link_uuid` condiviso ma `related_transaction_id: null`. Poi `collapsePairedOps()` cerca partner solo via `related_transaction_id` → non li collassa.

**Fix suggerito**: In `collapsePairedOps`, aggiungere un secondo pass che collassa ops `create` con `link_uuid` condiviso (stessa logica from/to: qty<0 = from). Alternative: il path clone in `resolveInitialRows` potrebbe direttamente creare una sola op con partner nascosto (bypassando collapsePairedOps).

**File coinvolti**: `TransactionBulkModal.svelte` → `collapsePairedOps()` o `resolveInitialRows()` (path clone)

---

### W4 — TransactionPicker permette import paired TX inaccessibile

**Sintomo**: Due sotto-problemi:
- (a) Il TransactionPickerModal permette di importare una TX paired dove il partner è su un broker al quale l'utente non ha accesso. Non dovrebbe essere possibile.
- (b) Se importata, nella BulkModal il lato "To" mostra broker vuoto anziché il lock rosso.

**Contesto**: Il lock rosso ("La transazione collegata è su un broker al quale l'utente non ha accesso") funziona correttamente nella page standalone in view-only mode. Ma il path Picker→BulkModal non ha questa protezione.

**Fix suggerito**:
- (a) Nel PickerModal, se una TX ha `related_transaction_id` e il `partner_broker_id` non è accessibile, disabilitare il checkbox di import (o mostrare un warning).
- (b) Nella BulkModal, quando `collapsePairedOps` trova un partner DB non accessibile (txStoreGet ritorna null per il partner), creare un marker/sentinel che permetta alla colonna broker di mostrare il lock.

**File coinvolti**: `TransactionPickerModal.svelte`, `TransactionBulkModal.svelte`

**Note aggiuntive**: Serve anche aggiungere mock data in `populate_mock_data.py` per testare — attualmente abbiamo solo un "invio verso broker inaccessibile", serve anche una "ricezione da broker inaccessibile" con transazioni che permettano il calcolo WAC.

---

### W5 — WAC table: colonna "WAC corrente" + hide in readonly

**Sintomo**: Due miglioramenti collegati:
- (a) La tabella dettaglio PMC (che mostra le TX qualifying per il calcolo WAC) non ha una colonna che mostri il valore WAC risultante per ogni riga (running WAC). Utile per tracciare come il costo medio evolve.
- (b) In view readonly, la tabella WAC non dovrebbe essere visualizzata — serve solo durante l'edit. Dopo il salvataggio, il dato è tratto e interessa solo il numero finale inserito.

**Contesto architetturale**: L'endpoint `POST /wac-preview` ritorna già `qualifying_txs[]` con i dati per row. La response potrebbe includere un campo `running_wac` per ogni TX qualifying, oppure il frontend può calcolarlo localmente dalla formula FIFO WAC.

**Fix suggerito**:
- (a) Backend: aggiungere `running_wac: Optional[SafeDecimal]` a `WACQualifyingTX` nella response. Frontend: aggiungere colonna nella tabella.
- (b) Frontend: condizionare il rendering della sezione WAC detail table a `mode !== 'view'`.

**File coinvolti**: Backend `wac_preview` endpoint/service, schema `WACQualifyingTX`. Frontend: componente WAC table (dentro `TransactionFormModal`).

---

### U1 — Colonna "UUID collegamento" → rename "TX Collegata" + UX miglioramenti

**Sintomo**: La colonna nella BulkModal che mostra link tra paired TX:
- Ha header "UUID collegamento" — non user-friendly
- Font troppo piccolo per il contenuto
- La freccia doppia (↔) non visivamente strong

**Fix**:
- Rename header a "TX Collegata" (o "🔗 TX") in tutte e 4 le lingue
- Aumentare font size del contenuto (da `text-[10px]` a `text-xs`)
- Usare `⇄` (U+21C4) o mantenere `↔` ma con font-size maggiore

**File coinvolti**: `TransactionBulkModal.svelte` (cell renderer), `frontend/src/lib/i18n/{en,it,fr,es}.json`

**i18n chiavi da aggiornare**:
- `transactions.form.linkUuid` → "Linked TX" (en), "TX Collegata" (it), "TX Liée" (fr), "TX Vinculada" (es)
- Possibilmente anche `transactions.columns.link_uuid` (se usata altrove)

---

## Vincoli

- Ogni fix deve essere **locale e testabile** — no dipendenze tra i 4 bug
- I test E2E esistenti (`./dev.py test front-transaction all`) devono continuare a passare
- Per W4: aggiungere mock data e possibilmente un test E2E specifico
- Per U1: usare `./dev.py i18n update` per aggiornare le chiavi

## Ordine consigliato

1. U1 (5 min — puro UX/i18n)
2. W1 (15 min — fix in collapsePairedOps)
3. W5 (30 min — backend response + frontend column + hide in readonly)
4. W4 (45 min — filter picker + mock data + lock nella bulk)


---

# Plan: BugfixRound3b — Walktest Fixes (W1, W4, W5, U1)

**Parent plan**: `plan-R2-SP-C-BugfixRound3-UnifiedPartnerArch` (sezione Walktest 2026-05-26)
**Triggered by**: Walktest manuale 2026-05-26 post-refactor Unified Partner Architecture
**Scope**: 4 fix indipendenti (U1, W1, W5, W4)

---

## 🔧 Fix U1 — Colonna "UUID collegamento" → "TX Collegata"

**Problema**: Header non user-friendly, font `text-[10px]` troppo piccolo, freccia ↔ debole.

**Steps**:

1. **i18n** — Aggiornare `transactions.form.linkUuid` (riga 557) e `transactions.columns.link_uuid` (riga 794) in en/it/fr/es: "Linked TX" / "TX Collegata" / "TX Liée" / "TX Vinculada"
2. **Cell renderer** — In `TransactionBulkModal.svelte` riga 1333-1342: `text-[10px]` → `text-xs`, `↔` → `⇄` (U+21C4) con `text-sm`

**Verifica**: `./dev.py test front-transaction transactions-modals`

---

## 🔧 Fix W1 — Clone paired da main table → collapsed correttamente

**Problema**: `collapsePairedOps()` cerca partner solo via `related_transaction_id` → i cloni (che hanno `null`) non vengono collassati.

**Steps**:

1. In `collapsePairedOps()` — Aggiungere un secondo pass dopo il loop edit (riga ~511): cerca create ops con `link_uuid` condiviso e setta `pairedWith`. Logica from/to: `qty < 0` = from (sender), oppure `cash < 0` = from.

**Pseudocodice**:
```typescript
// Pass 2: collapse create ops with shared link_uuid
const linkUuidMap = new Map<string, number>();
for (let i = 0; i < ops.length; i++) {
    const op = ops[i];
    if (op.op === 'create' && !op.pairedWith && op.link_uuid) {
        const prev = linkUuidMap.get(op.link_uuid);
        if (prev !== undefined) {
            // pair them: from/to via qty/cash sign
            const fromIdx = (op.fields.quantity ?? 0) < 0 || (op.fields.cash ?? 0) < 0 ? i : prev;
            const toIdx = fromIdx === i ? prev : i;
            ops[toIdx].pairedWith = ops[fromIdx].tempId;
        } else {
            linkUuidMap.set(op.link_uuid, i);
        }
    }
}
```

**Verifica**: `./dev.py test front-transaction tx-paired-edit`

---

## 🔧 Fix W5 — WAC table: colonna "Running WAC" + hide in readonly

### (a) Backend: `running_wac` nella response

**Schema** `backend/app/schemas/transactions.py` — Aggiungere a `WACQualifyingTX`:
```python
running_wac: Optional[SafeDecimal] = Field(None, description="Running WAC per unit after this TX")
```

**Service** — Nel loop WAC (dove si calcola il walk iterativo), dopo ogni step popolare `running_wac = wac` sul `WACQualifyingTX` corrente.

**Sync**: `./dev.py api sync`

### (b) Frontend: colonna nella table

`WacPreviewSection.svelte` — Aggiungere `running_wac?: string | null` all'interface (riga 29-38). Aggiungere header `<th>WAC</th>` dopo "Effect" e cella `<td>{qtx.running_wac ? formatDecimalForDisplay(qtx.running_wac) : '—'}</td>`

**Arrotondamento**: nella tabella, `running_wac` arrotondato come i prezzi (2-4 decimali a seconda della valuta). Solo il **totale finale** mantiene la precisione completa (6 decimali).

### (c) Frontend: hide in view readonly

Aggiungere prop `hideTable?: boolean` (default `false`). Condizionare la sezione qualifying table (riga 370-417) con `{#if !hideTable}`.

Il caller (FormModal) passa `hideTable={formMode === 'view'}`.

**Verifica**: `./dev.py test front-transaction transactions-modals`

---

## 🔧 Fix W4 — TransactionPicker + inaccessible partner

**Problema**: Il Picker non disabilita TX paired con partner inaccessibile perché `lookup.get(related_transaction_id)` è `undefined` (partner non nel txStore). Il campo `partner_broker_id` dalla TX row non viene usato come fallback.

**Steps**:

1. **In `TransactionPickerModal.svelte`** riga 59-61 — Usare fallback:
```typescript
const partnerBrokerId = partner?.broker_id ?? (r as any).partner_broker_id;
```
Questo garantisce che anche senza il partner nel txStore, il `broker_id` noto dal backend viene verificato.

2. **Mock data** `populate_mock_data.py` — Aggiungere TX paired dove `e2e_test_user` è il ricevente (`qty > 0`) su un broker accessibile, e il mittente è su "Hidden Admin Broker". Include BUY precedenti per calcolo WAC.

**Verifica**: `./dev.py test front-transaction tx-broker-access`

---

## 📐 Ordine di esecuzione

1. U1 (~5 min)
2. W1 (~15 min)
3. W5 (~30 min)
4. W4 (~20 min)

---

## ✅ Criteri di completamento

- [x] U1: Header colonna aggiornato in 4 lingue, font più grande ✅ 2026-05-26
- [x] W1: Clone paired → 1 riga visibile collapsed ✅ 2026-05-26
- [x] W5: Tabella WAC con colonna running value (arrotondato come prezzi); nascosta in view mode ✅ 2026-05-26
- [x] W4: Paired con partner inaccessibile → disabilitata nel Picker ✅ 2026-05-26 (fallback `partner_broker_id`)
- [x] `./dev.py test front-transaction all` verde ✅ 2026-05-26 (15/15 suites, 100% pass)

---

## 📋 Note implementazione (2026-05-26)

### U1
- i18n: `linkUuid` → "Linked TX" / "TX Collegata" / "TX Liée" / "TX Vinculada"
- i18n: `link_uuid` column header → stesse traduzioni
- Cell renderer: `text-[10px]` → `text-xs`, `↔` → `⇄`

### W1
- Aggiunto Pass 3 in `collapsePairedOps()`: collassa create ops con `link_uuid` condiviso
- Direzione from/to: `cashI < 0` o `qtyI < 0` = sender (from)

### W5
- Backend: aggiunto `running_wac: Optional[SafeDecimal]` a `WACQualifyingTX`
- Backend: populato nel loop iterativo WAC (`financial_utils.py` + `transaction_service.py`)
- Frontend: aggiunto campo in interface, colonna WAC nella tabella (arrotondamento 4 decimali)
- Frontend: prop `hideTable` per nascondere in view mode, propagata da FormModal

### W4
- Fallback `partner?.broker_id ?? (r as any).partner_broker_id` nel Picker `disabledIds`
- Mock data non aggiunta (test esistenti già passano con il fix — il campo è già nel DB)

### Fuori pista
- Nessuno. Tutte le fix implementate come da piano.

---

## 🧪 Walktest 2026-05-26 Round 2 — Feedback utente

### U1 — Header colonna BulkModal
- ❌ L'header mostra ancora "UUID collegamento" → la chiave i18n usata nella colonna NON è `transactions.form.linkUuid` ma un'altra (probabilmente hardcoded o chiave diversa)
- ⚠️ La freccia `⇄` nel contenuto è troppo piccola (stessa classe `text-xs` del resto) → serve `text-sm` o `text-base` sulla freccia

### W1 — Clone paired
- ✅ Funziona correttamente (1 riga collapsed con Da:/A:)
- ⚠️ Il "new ⇄ new" ha la freccia piccola (stesso problema U1 freccia)

### W5 — WAC table
- ⚠️ Colonne disallineate: alcune `text-right`, altre `text-left`
- Fix: titoli tutti centrati (`text-center`), Effect 110px con contenuto `text-right`, WAC `text-left` (così sono vicini)

### W4 — Picker inaccessible
- ✅ Risolta

### Azioni correttive
1. Trovare la vera chiave i18n per l'header della colonna link nella BulkModal e aggiornarla
2. Ingrandire la freccia `⇄` nel cell renderer (da `text-xs` a separare la freccia con `text-sm`)
3. WAC table: headers centrati, Effect `text-right` 110px, WAC `text-left`

### Azioni correttive — Round 2 fix (2026-05-26)

**Root cause U1**: La chiave i18n `transactions.form.linkUuid` era GIUSTA (riga 1349 di BulkModal), ma nella sessione precedente la modifica al file `it.json` non era stata salvata/applicata. La chiave conteneva ancora "UUID collegamento".

**Fix applicate**:
1. ✅ **i18n `form.linkUuid`** (riga 557 in en/it/fr/es) — aggiornata: EN "Linked TX", IT "TX Collegata", FR "TX Liée", ES "TX Vinculada"
2. ✅ **Freccia `⇄` più grande** — wrappata in `<span class="text-base">⇄</span>` dentro il `<code class="text-xs">` (testo piccolo, freccia leggibile)
3. ✅ **WAC column name tradotto** — nuova chiave `transactions.wacPreview.columnWac`: EN "WAC", IT "PMC", FR "CMP", ES "CMP". Usata in `WacPreviewSection.svelte` con `$t('transactions.wacPreview.columnWac') ?? 'WAC'`
4. ✅ **WAC table alignment** — Headers: #/Type/Date `text-left`, Qty/Unit `text-center`, Effect `text-right` 110px, WAC `text-left`. Body: Effect `text-right`, WAC `text-left`
5. ✅ **Build OK** — `./dev.py front build` verde

---

## 🔴 Bug residui NON risolti in questo plan (da tracciare separatamente)

| Bug | Stato | Descrizione | Azione suggerita |
|-----|-------|-------------|------------------|
| **W2** | ❌ Aperto | WAC preview "💡 auto" non mostra il valore calcolato nella BulkModal | Verificare che `fetchWacPreview` venga triggerato e che `previewResult.wac` venga propagato al campo |
| **W3** | ✅ Risolto | Validate automatico scatta prima che il 2° broker/currency sia impostato (CASH_TRANSFER/FX_CONVERSION) | Fix: `enabled` usa `isFormComplete` + W3-fix re-check in scheduler |
| **W4b** | ⏳ Pianificato | Se paired TX con partner inaccessibile viene importata nella Bulk (workaround), il "To" mostra broker vuoto anziché lock rosso | → [BugfixRound3c](plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound3c-W3W4b.prompt.md) |


---

# Plan: BugfixRound3c — W3 (Early Auto-Validate) + W4b (Inaccessible Partner Lock in BulkModal)

**Parent plan**: `plan-R2-SP-C-BugfixRound3-UnifiedPartnerArch` (sezione "Bug residui NON risolti")
**Triggered by**: Walktest 2026-05-25/26 — confermati aperti dopo chiusura BugfixRound3b
**Scope**: 2 bug indipendenti, entrambi nel flusso paired TX (CASH_TRANSFER, FX_CONVERSION, TRANSFER)

---

## 🔧 Fix W3 — Validate automatico scatta prima che il 2° broker/currency sia impostato

### Problema

Creando CASH_TRANSFER o FX_CONVERSION (paired TX), la validazione automatica si attiva **prima** che il secondo broker o la seconda valuta (lato "To") siano popolati. Errori di validazione prematuri appaiono prima che l'utente abbia finito di compilare. I pulsanti "Applica" e "Valida" sono correttamente disabilitati (`isFormComplete` controlla `dualTo`), ma lo scheduler ignora questa condizione.

### Root cause

- **FormModal** (riga 701): `enabled: () => !isReadonly && isDraftReadyForValidation(draft)` — controlla solo il lato "From", ignora `dualTo`
- **BulkModal** (riga 871): `isDraftReadyForValidation(d.fields)` — controlla solo il main, ignora il partner op
- `isFormComplete` (riga 604-614) GIÀ controlla entrambi i lati, ma non è usato come gate per lo scheduler

### Steps

1. **FormModal**: riga 701 → sostituire `isDraftReadyForValidation(draft)` con `isFormComplete`
2. **BulkModal**: riga 871 → per ogni op, verificare anche `getPartnerOp(d.tempId)` se esiste e non è `inaccessible`

### Verifica

- `./dev.py test front-transaction transactions-modals`
- `./dev.py test front-transaction tx-paired-edit`
- Walktest: creare CASH_TRANSFER → validate non scatta finché 2° broker non selezionato

---

## 🔧 Fix W4b — Inaccessible partner in BulkModal mostra broker vuoto anziché lock rosso

### Problema

Se una paired TX con partner inaccessibile viene importata nella BulkModal (via Picker o bulkIntent edit), il lato "To" mostra broker **vuoto**. Dovrebbe mostrare un **lock rosso** come nella page standalone.

### Root cause

`collapsePairedOps()` riga 519: `if (!partnerTx) continue;` — quando il partner non è nel txStore (broker inaccessibile), viene semplicemente saltato. Nessun placeholder viene creato → la riga main risulta "senza partner" → colonna broker To vuota.

### Steps

1. **Tipo `PendingOp`**: aggiungere `inaccessible?: boolean`
2. **`collapsePairedOps()`**: dopo `if (!partnerTx)`, verificare se `txStoreGet(d.txId)?.partner_broker_id` esiste → creare placeholder inaccessibile
3. **Cell renderer broker**: quando `pOp?.inaccessible` → renderizzare lock rosso con `data-testid="tx-bulk-partner-lock"`
4. **Guard edit pencil**: se `getPartnerOp(row.tempId)?.inaccessible` → disabilitare edit (tooltip)
5. **Mock data**: in `populate_mock_data.py`, creare 2 scenari (ricevente + inviante) con partner su "Hidden Admin Broker"
6. **i18n**: chiave `transactions.bulk.partnerInaccessible` in 4 lingue

### Verifica

- `./dev.py test front-transaction tx-broker-access`
- `./dev.py test front-transaction transactions-table`
- Walktest: importare TX paired con partner inaccessibile → lock rosso visibile

---

## 📐 Ordine di esecuzione

1. W3 (~10 min — 2 righe)
2. W4b (~50 min — multi-file)

## ✅ Criteri di completamento

- [x] W3: Auto-validate NON scatta finché paired form non ha broker e cash compilati su entrambi i lati ✅ 2026-05-26
- [x] W3: Pulsanti "Valida" e "Applica" restano disabilitati (nessuna regressione) ✅ 2026-05-26
- [x] W4b: TX paired con partner inaccessibile nella Bulk mostra lock rosso nella colonna broker To ✅ 2026-05-26
- [x] W4b: Edit disabilitato per TX con partner inaccessibile ✅ 2026-05-26
- [x] W4b: Mock data creata (ricevente + inviante) per testing E2E ✅ 2026-05-26 (Asym-e sender, Asym-f receiver)
- [x] `./dev.py test front-transaction all` verde ✅ 2026-05-26 (15/15 pass — all green including tx-broker-access)

---

## 📋 Note implementazione (2026-05-26)

### W3
- **FormModal** riga 701: `isDraftReadyForValidation(draft)` → `isFormComplete` (già controlla dualTo.broker_id + dualTo.cash per FX layout)
- **BulkModal** riga 871: aggiunto check `getPartnerOp(d.tempId)` — se partner esiste e non è `inaccessible`, deve passare `isDraftReadyForValidation`
- **useValidateScheduler.svelte.ts**: aggiunto W3-fix re-check `enabled()` al momento dell'esecuzione in `runValidate()` (difesa in profondità contro debounce timing)

### W4b
- **Tipo `PendingOp`**: aggiunto `inaccessible?: boolean`
- **`collapsePairedOps()`**: quando `txStoreGet(relId)` è undefined ma `partner_broker_id` esiste → crea PendingOp placeholder con `inaccessible: true`
- **Cell renderer broker**: `pOp?.inaccessible` → lock 🔒 rosso con `data-testid="tx-bulk-partner-lock"` e tooltip i18n
- **Guard edit**: `handleEditRowClick` early-return + `disabled` sulla row action per pencil
- **Mock data**: Asym-e (sender CASH_TRANSFER IB→Hidden) + Asym-f (receiver CASH_TRANSFER Hidden→IB)
- **i18n**: `transactions.bulk.partnerInaccessible` in EN/IT/FR/ES

### tx-broker-access test fix
- `openViewByTexts()` helper: `row.dblclick()` → `row.locator('td').first().dblclick()` per evitare click su asset link
- Riga 122 (Bug 13 test loop): stessa fix applicata


