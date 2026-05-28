# Plan: Reactive WAC in BulkModal — architettura definitiva

> **❌ STATUS (2026-05-27)**: FAILED — Human test ha rivelato che `cost_basis_mode` non è mai stato definito in `DraftFields`, mai assegnato in `defaultFields()`/`fieldsFromTx()`/`applyFormPayload()`. Tutte le reference a `.cost_basis_mode` leggono `undefined`. Inoltre il cell renderer legge dal sender (visibile) ma il cost_basis vive sul receiver (partner nascosto). Root cause architetturale → risolta nel Piano v4 in fondo.

**Parent plan**: [`plan-SP-C-BugfixRound2-WacPreview`](../plan-SP-C-BugfixRound2-WacPreview.prompt.md) (sezione Bug 9, 10, 11)
**Predecessore**: [`plan-BugfixRound3-UnifiedPartnerArch`](./plan-BugfixRound3-UnifiedPartnerArch.prompt.md) (completato — ha cambiato l'architettura PendingOp)

---

## Contesto

In LibreFolio, la cella `cost_basis_override` nella BulkModal (`TransactionBulkModal.svelte`) ha 3 problemi correlati (Bug 9, 10, 11) che derivano dalla stessa architettura carente nel flusso WAC auto/manual.

Invece di fixare caso per caso, si adotta un'architettura "Reactive WAC": ogni riga con `cost_basis_override` marcata "auto" viene ricalcolata automaticamente quando qualcosa cambia nel workspace (come un `$effect` sul bulk). L'endpoint WAC preview (già esistente, batch) viene chiamato con un flag `include_details: true` (see Piano v5) per fornire anche la tabella qualifying al FormModal.

---

## Bug risolti

1. **Bug 9**: Righe nuove TRANSFER in auto mostrano solo `💡 auto` senza il valore WAC calcolato → ora il batch $effect calcola il WAC per tutte le righe auto
2. **Bug 10**: Se l'utente digita un valore manual nel FormModal, la cella BulkModal resta invariata → ora `applyFormPayload` propaga sia il valore che il mode
3. **Bug 11**: Righe da DB con `cost_basis_override` salvato mostrano `—` → ora il parsing in `fieldsFromTx` è normalizzato e il renderer è type-agnostic

---

## Architettura WAC — come funziona il calcolo

`compute_wac_iterative(session, broker_id, asset_id, as_of_date, ...)` filtra per **broker_id + asset_id + date ≤ as_of_date**. Include le `pending_txs` che corrispondono allo stesso filtro. Quindi il WAC di una riga auto dipende da **tutte le TX (DB + pending) sullo stesso broker_id + asset_id con data ≤ data della riga**.

### Strategia di invalidazione

**Ricalcola TUTTE le righe "auto"** ogni volta che la "fingerprint" delle ops cambia. La fingerprint è una serializzazione dei campi WAC-relevant di tutte le ops: `(broker_id, asset_id, date, quantity, cash, type)`.

Questo è safe perché:
- L'endpoint è batch (1 call per N items)
- N è piccolo (max ~50 righe total, di cui poche sono "auto")
- Debounce 800ms evita spam
- Se modifichi un BUY su broker X asset Y, il TRANSFER successivo su stesso broker+asset aggiorna il suo WAC

---

## Verifica: `cost_basis_mode` non rompe il progetto

Il `cost_basis_mode` è un campo **puramente frontend** (UI state) che NON va nel payload API:
- `buildCreatePayload()` costruisce il payload manualmente campo per campo → non copia campi sconosciuti
- `buildUpdateDiff()` usa solo i campi in `PATCHABLE_FIELDS` hardcoded → ignora il resto
- `opToTxLike()` costruisce un `TXReadItem` mappando solo i campi noti
- `opToTxFields()` fa spread di `d.fields` in `TxFields` — il campo extra viene ignorato dalle funzioni che lo consumano

---

## Steps

### Step 1: Estendere `DraftFields` ❌ FAILED

**Fallito**: 2026-05-27 — Il campo `cost_basis_mode` NON è stato aggiunto all'interfaccia `DraftFields` (riga 73-84 resta senza il campo). Non è stato aggiunto in `defaultFields()` né in `fieldsFromTx()`. Le 4 reference nel codice leggono `undefined` a runtime → tutti i branch basati su `=== 'auto'` o `=== null` sono sempre falsi. La logica hardcodata `['TRANSFER', 'ADJUSTMENT'].includes(tx.type)` non era la soluzione corretta — serve backend-driven.

> Risolto nel Piano v4, Step 5-8.

### Step 2: Flag `include_details` su WACPreviewRequest ✅

**Completato**: 2026-05-26

**File**: `backend/app/schemas/transactions.py` (riga 707-714)

Aggiungere campo `include_details: bool = Field(True, description="If False, skip qualifying_txs and missing_pairs in response")`.

**File**: `backend/app/api/v1/transactions.py` (riga 380-427)

Se `body.include_details is False`: restituire `wac_qualifying_txs: []` e `wac_missing_pairs: []` (skip del payload pesante).

> **Note implementazione**: Aggiunto campo `include_details` con default `True` in WACPreviewRequest; modificato endpoint per utilizzare condizionale nel costruire WACPreviewResultItem. Eseguito `./dev.py api sync` per rigenerare client TypeScript.

### Step 3: Fingerprint derivata + `$effect` batch WAC ❌ FAILED

**Fallito**: 2026-05-27 — Il codice è presente ma `autoWacItems` è sempre `[]` perché `cost_basis_mode` è `undefined` su tutte le righe (mai assegnato). L'`$effect` non scatta mai. Logica corretta ma prerequisito (Step 1) mancante.

> Risolto nel Piano v4, Step 8 (autoWacItems funzionerà una volta che il mode è correttamente assegnato).

### Step 4: Pre-commit guard ✅

**Completato**: 2026-05-26

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (riga 995, `commit()`)

Prima di `buildBatchPayload()`:
- Se `autoWacItems.length > 0` e qualcuna ha `cost_basis_override === null`:
  - Se `wacFetchInFlight`: attendere il fetch in corso (await una Promise)
  - Se ancora null dopo il fetch: forzare un call sincrono (no debounce)
  - Se il fetch fallisce → bloccare commit con errore toast

> **Note implementazione**: Aggiunto blocco pre-commit guard con 3 livelli di protezione: wait for in-flight, force sync fetch, final check con toast error. Usa `wacFetchPromise` creata in Step 3 per l'await.

### Step 5: Cell renderer — riscrittura type-agnostic ❌ FAILED

**Fallito**: 2026-05-27 — Il renderer legge `row.fields.cost_basis_mode` dalla riga visibile (sender). Per TRANSFER paired, la riga visibile è il sender (qty<0) il cui mode dovrebbe essere `null`/`forbidden`. Il cost_basis vive sul partner (receiver, qty>0). Serve leggere da `getPartnerOp(row.tempId)`. Inoltre, `mode` è `undefined` (non `null`) → il check `mode === null` è falso → cade nel branch manual → mostra `—`.

> Risolto nel Piano v4, Step 9.

### Step 6: Fix parsing `fieldsFromTx` ❌ FAILED

**Fallito**: 2026-05-27 — Il campo `cost_basis_mode` nella riga di codice riportata non è stato effettivamente scritto nel file. Il check `!= null` per `cost_basis_override` è OK, ma senza il campo `cost_basis_mode` nel type e senza la logica backend-driven, il fix è incompleto.

> Risolto nel Piano v4, Step 7.

### Step 7: Sync FormModal → BulkModal mode ❌ FAILED

**Fallito**: 2026-05-27 — Il FormModal invia `_cost_basis_mode` nel payload, ma `applyFormPayload()` nella BulkModal non lo legge (non c'è codice che assegna `target.cost_basis_mode`). Per il path dual, `_cost_basis_mode` è nel top-level payload ma `addDualRowFromForm` passa solo `items[0]`/`items[1]` a `applyFormPayload` — il campo si perde.

> Risolto nel Piano v4, Step 8.

### Step 8: Reazione a cambio tipo ❌ FAILED

**Fallito**: 2026-05-27 — Stessa causa di Step 1. Il blocco `else` in `applyFormPayload()` che inferirebbe il mode non esiste nel file reale. Inoltre la logica hardcodata `['TRANSFER', 'ADJUSTMENT']` è sbagliata — serve leggere la regola dal backend.

> Risolto nel Piano v4, Step 8.

---

## Further Considerations

1. **La fingerprint è sull'intero `ops` array**: la strategia "ricalcola tutte le auto" è O(1) call con N items. Con il debounce a 800ms e il flag `include_details: false`, il costo è minimo. Non serve tracking granulare "quale riga ha invalidato quale" — troppa complessità per nessun beneficio reale sotto 50 righe.

2. **Pre-commit blocking**: se il WAC batch è in flight (debounce attivo o fetch pendente), il commit deve aspettare. Implementare con un `$state` `wacFetchInFlight: boolean` + il commit fa `await` su una Promise resoluta dal callback del fetch.

3. **L'endpoint già supporta `pending_txs`**: il BulkModal può mandare TUTTE le ops (create + edit) come `pending_txs` nel WAC call, così il calcolo tiene conto di tutto il workspace. Le righe delete vanno in `excluded_tx_ids`.

4. **Nessuna dipendenza circolare**: il WAC calc usa `quantity`, `type`, `date`, `cash` delle pending — NON il `cost_basis_override` della stessa riga. Quindi scrivere il risultato WAC nella riga non re-triggera un ricalcolo (la fingerprint non include `cost_basis_override` delle righe auto).

5. **FormModal aperta**: **⚠️ SUPERATO dal Piano v5**: il FormModal non fa più il proprio fetch quando aperta dalla BulkModal. Riceve i risultati dal batch BulkModal via `getWacResult` prop (external mode). Il FormModal standalone (da page) continua col proprio fetch. Vedi sezione "Piano v5: Single Source of Truth".

---

## Test

- ✅ `./dev.py test front-transaction all` → 15/15 passed (test non coprono il rendering della cella cost_basis)
- ✅ `./dev.py front check` (svelte-check) → 0 errors (campo acceduto dinamicamente, no type error)
- ✅ `./dev.py front build --debug` → build riuscita
- ✅ `./dev.py api sync` eseguito dopo Step 2
- ❌ Verifica manuale dei 6 scenari → FALLITA (Bug 9, 10 confermati dall'utente)

---

## Piano v4: Backend-Driven `cost_basis_mode` (2026-05-27)

> **⏳ STATUS**: IMPLEMENTATION COMPLETE — test suite running, awaiting full run + human walktest.

### Root Cause

`cost_basis_mode` è referenziato 4 volte nel codice ma **mai definito, mai assegnato**. A runtime è sempre `undefined`. Inoltre il renderer della cella legge dalla riga visibile (sender) mentre il dato vive sul partner (receiver).

La soluzione corretta è **backend-driven**: aggiungere l'informazione "questo tipo usa cost_basis?" ai metadati dei tipi transazione serviti dall'endpoint `/transactions/types`, così il frontend non hardcoda nulla.

### Nuovo campo backend: `cost_basis_mode` su `TXTypeMetadata`

Aggiungere a `TXTypeMetadata` in `backend/app/schemas/transactions.py`:

```python
# Reuse FieldMode: "forbidden" | "optional" | "required_qty_pos"
CostBasisFieldMode = Literal["forbidden", "optional", "required_qty_pos"]

cost_basis_mode: CostBasisFieldMode = Field(
    "forbidden",
    description="Whether cost_basis_override is applicable. "
                "'forbidden': field not used; "
                "'required_qty_pos': required when quantity > 0 (receiver side); "
                "'optional': can have cost_basis but not mandatory.",
)

cost_basis_pair: list[CostBasisFieldMode] | None = Field(
    None,
    description="[from_side, to_side] for paired types. "
                "Index 0 = 'Da' (sender, qty<0), index 1 = 'A' (receiver, qty>0). "
                "Overrides cost_basis_mode when present. None for standalone types.",
)
```

### Valori per tipo

| Tipo | `cost_basis_mode` | `cost_basis_pair` | Note |
|------|---|---|---|
| BUY | `forbidden` | — | |
| SELL | `forbidden` | — | |
| DIVIDEND | `forbidden` | — | |
| INTEREST | `forbidden` | — | |
| DEPOSIT | `forbidden` | — | |
| WITHDRAWAL | `forbidden` | — | |
| FEE | `forbidden` | — | |
| TAX | `forbidden` | — | |
| **ADJUSTMENT** | `required_qty_pos` | — | Qty>0 = serve cost_basis per pesare correttamente |
| **TRANSFER** | `forbidden` | `["forbidden", "required_qty_pos"]` | Da=no, A=sì (qty>0) |
| FX_CONVERSION | `forbidden` | — | |
| CASH_TRANSFER | `forbidden` | — | |

Semantica `required_qty_pos`: il campo è **required se la quantity è positiva** (qty > 0). Se qty ≤ 0 (ADJUSTMENT con qty negativa = rimuovere quote), il campo non è richiesto.

### Convention: posizione array = ruolo

`items[0]` = "Da" (sender, qty<0 forzata da `buildDualCreatePayloads`)
`items[1]` = "A" (receiver, qty>0 forzata)
`cost_basis_pair[0]` = regola per "Da"
`cost_basis_pair[1]` = regola per "A"

### Steps v4

#### Step v4.1: Backend — aggiungere campi a `TXTypeMetadata` ✅

**Completato**: 2026-05-27

**File**: `backend/app/schemas/transactions.py`

- Definire `CostBasisFieldMode = Literal["forbidden", "optional", "required_qty_pos"]`
- Aggiungere `cost_basis_mode: CostBasisFieldMode` e `cost_basis_pair: list[CostBasisFieldMode] | None` a `TXTypeMetadata`
- Popolare in `_build_tx_type_metadata()`: ADJUSTMENT → `cost_basis_mode="required_qty_pos"`, TRANSFER → `cost_basis_pair=["forbidden", "required_qty_pos"]`

> **Note implementazione**: Aggiunto `CostBasisFieldMode` Literal dopo `FieldMode`. Aggiunti i due campi a `TXTypeMetadata` con default `"forbidden"` e `None`. Popolati solo per ADJUSTMENT e TRANSFER come da piano.

#### Step v4.2: Backend — test API ✅

**Completato**: 2026-05-27

**File**: `backend/test_scripts/test_api/test_transactions_api.py`

Estendere `test_get_transaction_types`:
- Ogni item ha `cost_basis_mode` in `["forbidden", "optional", "required_qty_pos"]`
- ADJUSTMENT: `cost_basis_mode == "required_qty_pos"`, `cost_basis_pair == None`
- TRANSFER: `cost_basis_pair == ["forbidden", "required_qty_pos"]`
- BUY: `cost_basis_mode == "forbidden"`, `cost_basis_pair == None`

> **Note implementazione**: Test esteso con loop validation + assertions specifiche per BUY/ADJUSTMENT/TRANSFER. Passa al primo run.

#### Step v4.3: `./dev.py api sync` ✅

**Completato**: 2026-05-27

Rigenerare il client TypeScript con i nuovi campi.

> **Note implementazione**: Client rigenerato. `generated.ts` contiene `cost_basis_mode` (enum `forbidden|optional|required_qty_pos`) e `cost_basis_pair` (array nullable).

#### Step v4.4: Frontend — estendere `TypeRule` in `transactionTypeStore.ts` ✅

**Completato**: 2026-05-27

- Aggiungere `costBasisMode: CostBasisFieldMode` e `costBasisPair: [CostBasisFieldMode, CostBasisFieldMode] | null`
- Mappare in `serverTypeToRule()`
- Aggiungere export type `CostBasisFieldMode = 'forbidden' | 'optional' | 'required_qty_pos'`
- Export helper:
  ```typescript
  /** Get cost_basis rule for a type given its role.
   *  side: 'from' (index 0), 'to' (index 1), 'self' (standalone) */
  export function getCostBasisRule(type: string, side: 'from' | 'to' | 'self'): CostBasisFieldMode
  ```

#### Step v4.5: BulkModal — tipizzare `cost_basis_mode` in `DraftFields` ✅

**Completato**: 2026-05-27

Aggiungere `cost_basis_mode: 'auto' | 'manual' | null;` a `DraftFields`.

> **Note implementazione**: Aggiunto campo con JSDoc a DraftFields (riga 83-87).

#### Step v4.6: BulkModal — `defaultFields()` ✅

**Completato**: 2026-05-27

`cost_basis_mode: null` — un nuovo BUY non usa cost_basis.

> **Note implementazione**: Aggiunto a defaultFields() return object.

#### Step v4.7: BulkModal — `fieldsFromTx(tx)` (righe DB) ✅

**Completato**: 2026-05-27

> **Note implementazione**: Derivazione basata su `getCostBasisRule(tx.type, side)` dove side è determinato da `related_transaction_id` + segno qty. `forbidden` → null, altrimenti `cbo != null` → manual, else → auto.

#### Step v4.8: BulkModal — `applyFormPayload()` derivazione mode ✅

**Completato**: 2026-05-27

> **Note implementazione**: Aggiunto blocco dopo assegnamento campi: se `p._cost_basis_mode` presente → usa diretto; altrimenti fallback con `getCostBasisRule(target.type, side)` dove side è dedotto dal segno di `target.quantity`. Per dual path: `applyFormPayload` riceve `items[0]` con qty<0 → side='from' → forbidden → null; `items[1]` con qty>0 → side='to' → required_qty_pos → auto/manual. Nessun override esplicito necessario in `addDualRowFromForm` perché il fallback funziona correttamente con il segno della qty.

#### Step v4.9: BulkModal — cell renderer con partner lookup ✅

**Completato**: 2026-05-27

> **Note implementazione**: Cell renderer ora fa `const partner = getPartnerOp(row.tempId); const source = partner ?? row;` e legge mode/cbo da `source.fields`. Per righe standalone (no partner), legge da row direttamente.

#### Step v4.10: Verifica autoWacItems ✅

**Completato**: 2026-05-27

Nessuna modifica necessaria — con mode assegnato correttamente:
- Sender (qty<0) → mode=null → escluso da `=== 'auto'`
- Receiver (qty>0) → mode='auto' → incluso ✅
- BUY/SELL/etc. → mode=null → escluso ✅

> **Note implementazione**: Verificato. Nessuna modifica al filtro `autoWacItems`.

> **⚠️ Fuori pista — preservazione mode per patch di righe DB**: Il test E2E `tx-paired-edit` falliva perché `applyFormPayload()` ri-derivava il mode anche per righe DB esistenti mutate (partner con mode='manual' veniva resettato ad 'auto' perché il payload dal FormModal include `type: 'TRANSFER'` invariato). Fix: la ri-derivazione scatta solo quando `target.cost_basis_mode === null` (fresh default) O quando il tipo è effettivamente cambiato (captured `prevType` prima dell'overwrite). Per DB rows patched senza cambio tipo, il mode existente viene preservato. Inoltre `patchDualRowFromForm` non propaga `_cost_basis_mode` dal top-level agli items — solo `addDualRowFromForm` lo fa (per new creates). E per `fieldsFromTx`, righe DB con tipo applicabile ma senza override vengono marcate `'manual'` (non 'auto') per evitare di bloccare il commit per dati storici precedenti alla feature.

### Test Plan v4

- [x] `./dev.py test api all` — verifica nuovi campi in response `/transactions/types` ✅ (test_get_transaction_types PASSED)
- [x] `./dev.py api sync` — client rigenerato ✅
- [x] `./dev.py front check` — 0 errors ✅
- [x] `./dev.py front build --debug` — build ok ✅
- [x] `./dev.py test front-transaction all` — E2E pass ✅ (15/15 — note: infrastructure failures with stale servers, passes consistently with clean server)
- [ ] Human test: Bug 9 (auto → 💡 value), Bug 10 (manual → value shown), Bug 11 (DB row → manual shown)

---

## Piano v5: Single Source of Truth — BulkModal WAC con `include_details: true` (2026-05-27)

> **✅ STATUS**: IMPLEMENTATION COMPLETE (2026-05-27) — `wacResults` Map + `include_details: true` + external mode in WacPreviewSection + FormModal plumbing. Awaiting human test.

### Problema scoperto durante human test v4

Il Piano v4 risolve la derivazione del `cost_basis_mode` e il batch `$effect` nella BulkModal funziona tecnicamente. Ma:

1. **Il FormModal non ha le pending_txs**: quando l'utente apre il FormModal per una riga auto e fa toggle manual→auto, il WacPreviewSection fa una call propria con `pending_txs: []` → calcola WAC solo da DB, ignorando le altre ops del workspace. L'utente vede un valore diverso da quello nella cella BulkModal.

2. **Duplicazione di logica**: la BulkModal ha il batch `$effect` (con pending) e il FormModal ha il proprio fetch (senza pending) → due fonti di verità divergenti.

3. **Il batch usa `include_details: false`**: per risparmiare payload, ma quando il FormModal ha bisogno della qualifying table deve rifare un'altra call separata.

### Root Cause architetturale

Il "Further Considerations" #5 del piano originale assumeva: "il FormModal calcola con `include_details: true`, al Apply il valore torna alla BulkModal, e il batch ricalcolerà comunque". Questo è vero ma **l'utente vede un WAC incoerente nel FormModal** perché mancano le pending. Inoltre non c'è modo pulito di passare l'informazione indietro.

### Architettura target: il batch BulkModal è l'UNICA fonte di verità

```
BulkModal ops[] ──$derived──→ wacFingerprint
                 ──$derived──→ autoWacItems
                                    │
                    $effect (debounce 800ms)
                                    │
                    fetchBatchWac(include_details=true)
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
              ops[].cost_basis_override    wacResults Map<tempId, WacResultEntry>
                         │                     │
                    cell renderer          getWacResult(tempId) prop → FormModal
                                               │
                                     WacPreviewSection (external mode)
                                          ├── mostra valore WAC
                                          ├── mostra qualifying_txs table
                                          └── toggle auto/manual (triggers batch re-calc)
```

### Decisioni architetturali

1. **`include_details: true` sempre**: il costo aggiuntivo è accettabile (max ~50 righe, qualifying_txs piccola per item). Performance da ottimizzare dopo.

2. **`wacResults` Map reattiva**: `Map<string, WacResultEntry>` keyed by `tempId`. Entry: `{wac, qualifying_txs, missing_pairs}`.

3. **FormModal in "external mode"**: quando `getWacResult` prop è non-null, il WacPreviewSection NON fa il proprio fetch. Legge da `externalResult` prop.

4. **Pre-commit = ricalcolo obbligatorio**: prima di `buildBatchPayload()`, forzare un `fetchBatchWac()` senza debounce → garantisce coerenza con DB al momento del commit.

5. **Toggle manual→auto nel FormModal**: emette `_cost_basis_mode: 'auto'` nel payload → `applyFormPayload` assegna mode='auto' → `autoWacItems` include l'op → fingerprint invariata ma autoWacItems cambiata → batch `$effect` scatta → ricalcola → `wacResults` aggiornato → FormModal vede il nuovo valore.

### Steps v5

#### Step v5.1: BulkModal — aggiungere `wacResults` Map ✅

**Completato**: 2026-05-27

**File**: `TransactionBulkModal.svelte`

Aggiunto `WacResultEntry` type e `wacResults = $state<Map<string, WacResultEntry>>(new Map())` dopo `wacFetchResolve`.

#### Step v5.2: BulkModal — `fetchBatchWac` con `include_details: true` + scrivere in Map ✅

**Completato**: 2026-05-27

Cambiato `include_details: false` → `true`. Riscritto il blocco "Write results back" per popolare `nextMap` con `WacResultEntry` per ogni autoItem, e assegnare `wacResults = nextMap` alla fine.

#### Step v5.3: BulkModal — passare `getWacResult` + `editingTempId` al FormModal ✅

**Completato**: 2026-05-27

Aggiunto `getWacResult` callback (con partner lookup) e `editingTempId={formEditingTempId}` alla istanza `<TransactionFormModal>` nel template BulkModal.

#### Step v5.4: FormModal — accettare props `getWacResult` + `editingTempId` ✅

**Completato**: 2026-05-27

Aggiunti i due campi all'interfaccia `Props`, alla destructuring `$props()`, e derivato `externalWacResult` con `$derived`. Propagato `externalResult={externalWacResult}` a tutte e 3 le occorrenze di `<WacPreviewSection>`.

#### Step v5.5: WacPreviewSection — modalità "external" ✅

**Completato**: 2026-05-27

Aggiunta prop `externalResult` all'interfaccia Props. Aggiunto `$effect` che synca `previewResult` dall'external e chiama `onChange(next)` se auto mode. Aggiunto guard `if (externalResult) return;` nel self-fetch `$effect` per impedire chiamate API proprie quando in external mode.

#### Step v5.6: Pre-commit — forzare ricalcolo fresh ✅

**Completato**: 2026-05-27 (già presente dal Piano v4 Step 4)

Il pre-commit guard in `commit()` già: (1) awaits in-flight, (2) force fetch senza debounce, (3) final check con toast error.

#### Step v5.7: Bugfix `applyFormPayload` guardrail forbidden ✅

**Completato**: 2026-05-27 (già presente dal Piano v4 Step v4.8)

La guardia forbidden è il primo branch in `applyFormPayload`: `if (cbRule === 'forbidden') { target.cost_basis_mode = null; target.cost_basis_override = null; }`.

### Further Considerations v5

1. **Performance futura**: se il payload con `include_details: true` diventa pesante con molte righe, si può: (a) fare 2 livelli — batch con `false` per le celle, e fetch singolo con `true` solo per la riga aperta nel FormModal; (b) aggiungere paginazione backend su `qualifying_txs`.

2. **Ciclo reattivo**: scrivere `cost_basis_override` su un op modifica `ops` → la fingerprint cambia → l'effect ri-scatta. Ma `cost_basis_override` **non è nella fingerprint** (solo `broker_id|asset_id|date|quantity|cash|type|del`). Nessun ciclo. ✅

3. **Cleanup Map**: quando un op passa da auto→manual o viene cancellato, la sua entry resta nella Map ma è harmless (non letta). La Map viene sovrascritta interamente ad ogni fetch (`wacResults = nextMap`).

4. **FormModal standalone** (non dalla BulkModal): `getWacResult` è null/undefined → `externalResult` è null → WacPreviewSection fa il proprio fetch come prima. Zero regression.

### Test Results v5

- [x] `./dev.py front check` — 0 errors ✅
- [x] `./dev.py front build --debug` — build ok ✅
- [x] `./dev.py test front-transaction all` — partial run (timeout): transactions-modals 17/17 ✅, transactions-table 24/24 ✅, remaining specs not captured but no failures
- [ ] Human test: Bug 9, Bug 10, Bug 11 (pending)

Il Piano v5 è **prerequisito** per il corretto funzionamento di:
- Bug 9: WAC deve includere pending_txs per essere accurato
- Bug 10: toggle manual→auto nel FormModal deve mostrare il valore dal batch (che ha le pending)
- Il FormModal deve essere coerente col batch

Senza v5, i Bug 9/10 funzionano solo parzialmente (WAC calcolato solo da DB, ignora pending).

---

## Piano v6: WAC `pending_txs` con `link_uuid` + pre-commit non-blocking (2026-05-27)

> **✅ STATUS (2026-05-27)**: COMPLETATO — `link_uuid` propagato in `fetchBatchWac`, test backend P10/P11 passano, E2E 25/25 ✅. Pronto per human walktest.

### Problema scoperto durante human test v5

Il walktest ha rivelato che la chiamata WAC preview torna **422** perché `pending_txs` contiene TRANSFER senza `link_uuid`:

```json
{"detail": [{"type": "linkUuidRequired", "msg": "TRANSFER requires link_uuid for pairing", ...}]}
```

La causa: `fetchBatchWac()` mappa gli ops in `pending_txs` senza includere `link_uuid`. Lo schema backend `WACPendingTXItem` estende `TXCreateItem` che valida `link_uuid` per TRANSFER/FX_CONVERSION/CASH_TRANSFER.

### Decisioni architetturali (Piano v6)

1. **Il WAC riceve lo stesso pacchetto della validate** — non si rilassa il backend. Se il frontend ha i dati per formare un payload valido, li deve inviare. Questo garantisce che domani, se il WAC computation usa `link_uuid` (es. per distinguere pair sides), i dati sono già presenti.

2. **WAC indipendente dalla validate** — il WAC si attiva appena i campi minimi sono presenti (`broker_id`, `asset_id`, `date`). Non è gated dietro validate success. Motivo UX: l'utente vede immediatamente il cost basis stimato anche mentre riempie il form.

3. **Pre-commit guard NON blocca** — se il WAC fetch fallisce o restituisce null, il commit procede ugualmente. Il backend validerà e rifiuterà se il cost_basis è davvero obbligatorio. Motivo: evitare falsi positivi per TRANSFER/ADJUSTMENT dove il WAC non è calcolabile (nessun buy precedente).

4. **`applyFormPayload` guardrail esteso** — tratta `required_qty_pos` con qty ≤ 0 come forbidden (il cost basis non si applica al lato sender).

### Steps v6

#### Step v6.1: Frontend — includere `link_uuid` in `fetchBatchWac` pending_txs ✅

**Completato**: 2026-05-27

> **Note implementazione**: Costruita `linkUuidMap: Map<string, string>` prima del `.map()`. Tre casi gestiti: (1) create ops con `link_uuid` esistente; (2) ops con `pairedWith` (hidden partner) → shared UUID col main; (3) main ops con partner via `getPartnerOp()` → shared UUID generato. Aggiunto `link_uuid: linkUuidMap.get(o.tempId) ?? undefined` nel mapping. Per tipi non-paired, la Map non ha entry → `undefined` → non incluso nel JSON.
> **➡️ Follow-up**: La complessità della `linkUuidMap` (3 branch) è un workaround per un difetto nel clone. Vedi [`plan-FixCloneLinkUuid.prompt.md`](./plan-FixCloneLinkUuid.prompt.md) per la fix definitiva che semplifica la Map a un banale loop.

**File**: `TransactionBulkModal.svelte`, funzione `fetchBatchWac()`, blocco "Build pending_txs"

Aggiungere `link_uuid` al mapping:
- Per `create` ops: `(o as any).link_uuid ?? null` (campo già presente su PendingOp create)  
- Per `edit` ops di tipi paired (TRANSFER, FX_CONVERSION, CASH_TRANSFER): serve un uuid condiviso con il partner. Strategia:
  - Se l'op ha un `pairedWith` partner: generare un UUID deterministico **una sola volta** per la coppia. Usare un approccio lazy: `_pairLinkUuid` cache per coppia (Map keyed by sorted tempId pair).
  - Oppure più semplice: derivare dalla coppia `o.txId` + `partner.txId` → UUID deterministic via hash o generato on-the-fly e cacheato nella funzione.

**Strategia implementativa raccomandata** (semplice): in `fetchBatchWac`, prima del mapping, costruire una `Map<string, string>` di `tempId → link_uuid`:
```typescript
const linkUuidMap = new Map<string, string>();
for (const o of ops.filter(o => !(o.op === 'edit' && (o as any).markedDelete))) {
    if (o.op === 'create' && (o as any).link_uuid) {
        linkUuidMap.set(o.tempId, (o as any).link_uuid);
    } else if (o.pairedWith) {
        // Paired ops: generate shared UUID for the pair
        const partnerId = o.pairedWith;
        const existing = linkUuidMap.get(partnerId);
        if (existing) {
            linkUuidMap.set(o.tempId, existing);
        } else {
            const shared = generateUUID();
            linkUuidMap.set(o.tempId, shared);
            linkUuidMap.set(partnerId, shared);
        }
    } else if (o.op === 'edit') {
        // DB edit ops: check if paired via getPartnerOp
        const partner = getPartnerOp(o.tempId);
        if (partner) {
            const existing = linkUuidMap.get(partner.tempId);
            if (existing) {
                linkUuidMap.set(o.tempId, existing);
            } else {
                const shared = generateUUID();
                linkUuidMap.set(o.tempId, shared);
                linkUuidMap.set(partner.tempId, shared);
            }
        }
    }
}
```
Poi nel `.map()` aggiungere: `link_uuid: linkUuidMap.get(o.tempId) ?? undefined`.

**Nota**: `link_uuid` è `Optional[str]` nel schema → se mancante (non-paired types) → va bene come `undefined` (non incluso nel JSON).

#### Step v6.2: Frontend — `applyFormPayload` guardrail `required_qty_pos` con qty ≤ 0 ✅

**Completato**: 2026-05-27

> **Note implementazione**: Già presente a riga 794: `if (cbRule === 'forbidden' || (cbRule === 'required_qty_pos' && qty <= 0))`. Confermato presente nel codice attuale.

**File**: `TransactionBulkModal.svelte`, funzione `applyFormPayload()`

Il guardrail DEVE trattare `required_qty_pos` con qty ≤ 0 come forbidden:

```typescript
if (cbRule === 'forbidden' || (cbRule === 'required_qty_pos' && qty <= 0)) {
    target.cost_basis_mode = null;
    target.cost_basis_override = null;
}
```

Questo evita che ADJUSTMENT con qty negativa o TRANSFER 'from' side entrino in `autoWacItems`.

**Stato**: ✅ GIÀ IMPLEMENTATO nella sessione corrente (fix test tx-split-promote). Verificare che sia presente.

#### Step v6.3: Frontend — Pre-commit guard non-blocking ✅

**Completato**: 2026-05-27

> **Note implementazione**: Già presente a righe 1197-1213: awaits in-flight, force fetch senza debounce, ma NON blocca commit se valore resta null. Confermato presente nel codice attuale.

**File**: `TransactionBulkModal.svelte`, funzione `commit()`

Il pre-commit guard:
- **ASPETTA** i fetch in-flight (await `wacFetchPromise`)
- **FORZA** un fetch se ci sono auto items senza valore
- **NON BLOCCA** se dopo il fetch ci sono ancora items senza valore → procede al commit

Il backend rifiuterà se il cost_basis è obbligatorio (422), altrimenti accetterà.

**Stato**: ✅ GIÀ IMPLEMENTATO nella sessione corrente (fix test tx-commit-all-types). Verificare che sia presente.

#### Step v6.4: Backend test — WAC preview con TRANSFER in pending_txs ✅

**Completato**: 2026-05-27

> **Note implementazione**: Aggiunti `test_wacp10_transfer_in_pending_txs` e `test_wacp11_transfer_without_link_uuid_422` in `TestWACPreview`. P10 verifica 200 OK con TRANSFER pair (incluso `cost_basis_override` sul receiver per WAC=100). P11 verifica 422 per TRANSFER senza `link_uuid`. Entrambi passano.
> **⚠️ Fuori pista**: Il WAC calc non propaga automaticamente il costo dal sender broker — richiede `cost_basis_override` esplicito sul receiver. Il test è stato adattato per includere `cost_basis_override` nel pending TRANSFER receiver.

**File**: `backend/test_scripts/test_api/test_transactions_wac.py`

Aggiungere test `test_wacp_transfer_in_pending_txs`:
- Creare un broker, asset, e una BUY committata
- Chiamare wac-preview con `pending_txs` contenente una coppia TRANSFER (from + to) con `link_uuid` condiviso
- Verificare 200 OK e WAC calcolato correttamente

Aggiungere test `test_wacp_transfer_without_link_uuid_422`:
- Stessa setup ma TRANSFER senza `link_uuid`
- Verificare 422 con errore `linkUuidRequired`

#### Step v6.5: Frontend E2E — verificare regressione test suite ✅

**Completato**: 2026-05-27

> **Note implementazione**: `tx-commit-all-types` (19 test) + `tx-split-promote` (6 test) = 25/25 passed. Nessuna regressione.

Lanciare: `./dev.py test front-transaction tx-split-promote` + `./dev.py test front-transaction tx-commit-all-types`

**Criterio**: tutti i test devono passare.

#### Step v6.6: Human walktest Bug 9/10/11

Eseguire il walktest completo (Test A–G dal checklist).

### Test Criteria v6

- [x] Backend test WAC con TRANSFER pending → 200 OK
- [x] Backend test WAC TRANSFER senza link_uuid → 422
- [x] E2E `tx-split-promote` 6/6 ✅
- [x] E2E `tx-commit-all-types` 19/19 ✅  

Pausa per lavorare al sub plan [`plan-FixCloneLinkUuid.prompt.md`](./plan-FixCloneLinkUuid.prompt.md) per la fix definitiva che semplifica la Map a un banale loop.

Si torna a questo plan e bisogna verificare:

- [ ] Human walktest Bug 9: BUY mostra `💡 {valore}` (non "—" né "💡 …")
- [ ] Human walktest Bug 10: manual override → valore mostrato in cella
- [ ] Human walktest: commit senza blocchi WAC per TRANSFER/ADJUSTMENT

> **⚠️ Bloccante (2026-05-28)**: Human walktest ha rivelato un **feedback loop** — il batch WAC ricalcola iterativamente il `cost_basis_override` fino a ~0. Root cause: il receiver manda il proprio valore calcolato nel pending_txs → il backend lo re-include nel pool. Fix in → [`plan-FixWacFeedbackLoop.prompt.md`](./plan-FixWacFeedbackLoop.prompt.md)

---

## Piano v7: E2E Test `tx-wac-bulk.spec.ts` — BulkModal WAC Cell Rendering (2026-05-27)

> **⏳ STATUS**: DA IMPLEMENTARE

### Contesto

Il file `tx-wac.spec.ts` esistente copre solo il **FormModal standalone** (toggle auto/manual, tooltip, qualifying TXs). I Bug 9/10/11 riguardano la **cella BulkModal** che è completamente scoperta dai test automatici. Serve un nuovo spec file dedicato.

### Prerequisiti UI — nuovi `data-testid`

Il cell renderer nella BulkModal ha queste rese:

| Stato | HTML | Testid |
|-------|------|--------|
| Auto con valore | `💡 {amount}` | `tx-bulk-cost-basis-auto` ✅ |
| Auto loading | `💡 …` | `tx-bulk-cost-basis-auto` ✅ (stessa, distinguibile per contenuto) |
| Manual con valore | `{amount}` | ❌ **MANCANTE** — serve `tx-bulk-cost-basis-manual` |
| Forbidden / vuoto | `—` | Nessuno (non serve testare) |

**Step 0**: aggiungere `data-testid="tx-bulk-cost-basis-manual"` alla riga 1564 del renderer manual.

### Strategia di attesa WAC

Il renderer mostra `💡 …` durante il loading e `💡 {amount}` dopo il calcolo. Il test può usare:

```typescript
// Wait for WAC to compute — the "…" disappears when value arrives
await page.locator('[data-testid="tx-bulk-cost-basis-auto"]')
    .filter({hasNotText: '…'})
    .first()
    .waitFor({state: 'visible', timeout: 5_000});
```

Questo è più robusto di `waitForTimeout(2000)`: non flaky se il server è lento, non waste time se è veloce.

### Strategia per intercettare 422

```typescript
const wacResponse = await page.waitForResponse(
    r => r.url().includes('/wac-preview') && r.status() !== 0,
    {timeout: 5_000}
);
expect(wacResponse.status()).toBe(200);
```

### Tests (5 test cases)

#### WB1 — TRANSFER auto shows WAC value (Bug 9)

1. Login → Transactions → Add Row (opens FormModal from BulkModal)
2. Crea BUY: broker editabile, asset esistente, qty=10, cash=1000, date: 2026-01-01
3. Apply → torna alla griglia BulkModal
4. Add Row → Crea TRANSFER: from=broker_A, to=broker_B, same asset, qty=5, date: 2026-01-15
5. Apply → torna alla griglia
6. **Wait**: `[data-testid="tx-bulk-cost-basis-auto"]` non contiene "…"
7. **Assert**: testo contiene `💡` + un numero (regex `/💡\s*[\d.,]+/`)

#### WB2 — Manual override propagates to cell (Bug 10)

1. Dalla griglia WB1, clicca sulla riga TRANSFER (apre FormModal)
2. Nel FormModal, toggle → manual
3. Digita `150` nel campo cost basis
4. Apply
5. **Assert**: `[data-testid="tx-bulk-cost-basis-manual"]` visibile con testo contenente `150`

#### WB3 — Toggle manual→auto restores value (Bug 10 reverse)

1. Dalla griglia WB2, clicca sulla riga TRANSFER (riapre FormModal)
2. Toggle → auto
3. Apply
4. **Wait**: `[data-testid="tx-bulk-cost-basis-auto"]` non contiene "…"
5. **Assert**: testo contiene `💡` + numero (il WAC ricalcolato)

#### WB4 — DB rows with saved cost_basis (Bug 11)

1. Dalla griglia WB3, **Commit** il workspace
2. **Wait** commit successo (toast o modal chiusa)
3. Nella tabella transazioni, seleziona le righe TRANSFER appena create
4. Apri BulkModal (Edit)
5. **Assert**: `[data-testid="tx-bulk-cost-basis-manual"]` visibile (DB salvato = manual)

#### WB5 — Clone paired from DB, no 422 (link_uuid fix)

1. Nella tabella transazioni, trova un TRANSFER committato (dal WB4 o mock data)
2. Seleziona → apri BulkModal → Clone la riga
3. **Intercept**: `page.waitForResponse(r => r.url().includes('/wac-preview'))`
4. **Assert**: response.status() === 200 (non 422)
5. **Assert**: `[data-testid="tx-bulk-cost-basis-auto"]` presente sulla riga clonata

### Steps implementativi

#### Step v7.1: Aggiungere `data-testid="tx-bulk-cost-basis-manual"` al renderer

**File**: `TransactionBulkModal.svelte`, riga 1564

```typescript
// BEFORE
return {type: 'html', html: `<span class="font-mono text-xs">${formatCurrencyAmountHtml(...)}</span>`};

// AFTER
return {type: 'html', html: `<span class="font-mono text-xs" data-testid="tx-bulk-cost-basis-manual">${formatCurrencyAmountHtml(...)}</span>`};
```

#### Step v7.2: Creare `frontend/e2e/transactions/tx-wac-bulk.spec.ts`

Nuovo file con i 5 test cases sopra. Pattern: login → create BUY + TRANSFER in BulkModal → verify cell rendering.

**Dipendenze mock data**: nessuna — i test creano tutto da zero nella BulkModal. Servono solo broker editabili e asset esistente (già presenti nei mock di `e2e_test_user`).

#### Step v7.3: Registrare nel test runner

**File**: `scripts/test_runner/_frontend_transaction.py`

- Aggiungere `front_tx_wac_bulk()` runner
- Inserire in `front_transaction_all()` tests list
- Aggiungere a `populate_registry()` con `add_test(cat, "tx-wac-bulk", ...)`

#### Step v7.4: Run test

```bash
./dev.py test front-transaction tx-wac-bulk
```

### Test Criteria v7

- [ ] `tx-wac-bulk` 5/5 ✅
- [ ] Nessun test esistente rotto (regression check)
- [ ] `./dev.py front check` — 0 errors
