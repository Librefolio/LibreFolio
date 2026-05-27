# Plan: Reactive WAC in BulkModal — architettura definitiva

> **❌ STATUS (2026-05-27)**: FAILED — Human test ha rivelato che `cost_basis_mode` non è mai stato definito in `DraftFields`, mai assegnato in `defaultFields()`/`fieldsFromTx()`/`applyFormPayload()`. Tutte le reference a `.cost_basis_mode` leggono `undefined`. Inoltre il cell renderer legge dal sender (visibile) ma il cost_basis vive sul receiver (partner nascosto). Root cause architetturale → risolta nel Piano v4 in fondo.

**Parent plan**: [`plan-SP-C-BugfixRound2-WacPreview`](../plan-SP-C-BugfixRound2-WacPreview.prompt.md) (sezione Bug 9, 10, 11)
**Predecessore**: [`plan-BugfixRound3-UnifiedPartnerArch`](./plan-BugfixRound3-UnifiedPartnerArch.prompt.md) (completato — ha cambiato l'architettura PendingOp)

---

## Contesto

In LibreFolio, la cella `cost_basis_override` nella BulkModal (`TransactionBulkModal.svelte`) ha 3 problemi correlati (Bug 9, 10, 11) che derivano dalla stessa architettura carente nel flusso WAC auto/manual.

Invece di fixare caso per caso, si adotta un'architettura "Reactive WAC": ogni riga con `cost_basis_override` marcata "auto" viene ricalcolata automaticamente quando qualcosa cambia nel workspace (come un `$effect` sul bulk). L'endpoint WAC preview (già esistente, batch) viene chiamato con un flag `include_details: false` per evitare il payload pesante dei qualifying_txs.

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

5. **FormModal aperta**: quando il FormModal è aperta su una riga "auto", il `WacPreviewSection` calcola con `include_details: true` (per mostrare tabella qualifying). Al "Apply" il valore torna alla BulkModal via payload. Il batch $effect ricalcolerà comunque al prossimo trigger (idempotente — il valore sarà lo stesso o aggiornato se nel frattempo altre righe sono cambiate).

---

## Test

- ✅ `./dev.py test front-transaction all` → 15/15 passed (test non coprono il rendering della cella cost_basis)
- ✅ `./dev.py front check` (svelte-check) → 0 errors (campo acceduto dinamicamente, no type error)
- ✅ `./dev.py front build --debug` → build riuscita
- ✅ `./dev.py api sync` eseguito dopo Step 2
- ❌ Verifica manuale dei 6 scenari → FALLITA (Bug 9, 10 confermati dall'utente)

---

## Piano v4: Backend-Driven `cost_basis_mode` (2026-05-27)

> **⏳ STATUS**: IN REVIEW — In attesa di feedback utente.

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

#### Step v4.1: Backend — aggiungere campi a `TXTypeMetadata`

**File**: `backend/app/schemas/transactions.py`

- Definire `CostBasisFieldMode = Literal["forbidden", "optional", "required_qty_pos"]`
- Aggiungere `cost_basis_mode: CostBasisFieldMode` e `cost_basis_pair: list[CostBasisFieldMode] | None` a `TXTypeMetadata`
- Popolare in `_build_tx_type_metadata()`: ADJUSTMENT → `cost_basis_mode="required_qty_pos"`, TRANSFER → `cost_basis_pair=["forbidden", "required_qty_pos"]`

#### Step v4.2: Backend — test API

**File**: `backend/test_scripts/test_api/test_transactions_api.py`

Estendere `test_get_transaction_types`:
- Ogni item ha `cost_basis_mode` in `["forbidden", "optional", "required_qty_pos"]`
- ADJUSTMENT: `cost_basis_mode == "required_qty_pos"`, `cost_basis_pair == None`
- TRANSFER: `cost_basis_pair == ["forbidden", "required_qty_pos"]`
- BUY: `cost_basis_mode == "forbidden"`, `cost_basis_pair == None`

#### Step v4.3: `./dev.py api sync`

Rigenerare il client TypeScript con i nuovi campi.

#### Step v4.4: Frontend — estendere `TypeRule` in `transactionTypeStore.ts`

- Aggiungere `costBasisMode: CostBasisFieldMode` e `costBasisPair: [CostBasisFieldMode, CostBasisFieldMode] | null`
- Mappare in `serverTypeToRule()`
- Aggiungere export type `CostBasisFieldMode = 'forbidden' | 'optional' | 'required_qty_pos'`
- Export helper:
  ```typescript
  /** Get cost_basis rule for a type given its role.
   *  side: 'from' (index 0), 'to' (index 1), 'self' (standalone) */
  export function getCostBasisRule(type: string, side: 'from' | 'to' | 'self'): CostBasisFieldMode
  ```

#### Step v4.5: BulkModal — tipizzare `cost_basis_mode` in `DraftFields`

Aggiungere `cost_basis_mode: 'auto' | 'manual' | null;` a `DraftFields`.

#### Step v4.6: BulkModal — `defaultFields()`

`cost_basis_mode: null` — un nuovo BUY non usa cost_basis.

#### Step v4.7: BulkModal — `fieldsFromTx(tx)` (righe DB)

```
side = (tx ha related_transaction_id e qty < 0) ? 'from' : (tx ha related_transaction_id e qty >= 0) ? 'to' : 'self'
rule = getCostBasisRule(tx.type, side)
if (rule === 'forbidden') → cost_basis_mode = null
else if (tx.cost_basis_override != null) → cost_basis_mode = 'manual'
else → cost_basis_mode = 'auto'
```

#### Step v4.8: BulkModal — `applyFormPayload()` derivazione mode

Dopo aver assegnato tutti i campi a `target`:

```typescript
// 1. Se il FormModal ha passato esplicitamente il mode, usalo
if (typeof p._cost_basis_mode === 'string') {
    target.cost_basis_mode = p._cost_basis_mode as 'auto' | 'manual' | null;
} else {
    // 2. Fallback: derivare dalla regola backend
    const qty = Number(target.quantity ?? 0);
    const side: 'from' | 'to' | 'self' = /* determinare dal contesto */;
    // Per single ops: 'self'; per dual, vedi Step v4.8b
    const rule = getCostBasisRule(target.type, side);
    if (rule === 'forbidden') {
        target.cost_basis_mode = null;
        target.cost_basis_override = null;
    } else {
        target.cost_basis_mode = target.cost_basis_override ? 'manual' : 'auto';
    }
}
```

**Step v4.8b**: In `addDualRowFromForm` / `patchDualRowFromForm`, dopo `applyFormPayload`:
- `fromOp.fields.cost_basis_mode = null` (forzato — pair[0] = forbidden)
- `toOp.fields.cost_basis_mode = payload._cost_basis_mode ?? 'auto'` (pair[1] = required_qty_pos)

Nota: `applyFormPayload` riceve `items[0]` (con qty negativa) → `getCostBasisRule('TRANSFER', 'from')` = forbidden → mode=null. E `items[1]` (con qty positiva) → `getCostBasisRule('TRANSFER', 'to')` = required_qty_pos → auto/manual. Il side si deduce dal segno: `qty < 0 ? 'from' : qty > 0 ? 'to' : 'self'`.

#### Step v4.9: BulkModal — cell renderer con partner lookup

Per righe paired (sender visibile), il cost_basis vive sul receiver (partner nascosto):

```typescript
cell: (row): CellContent => {
    const partner = getPartnerOp(row.tempId);
    const source = partner ?? row;
    const mode = source.fields.cost_basis_mode;
    const cbo = source.fields.cost_basis_override;
    // ...rest of renderer (null→—, auto→💡, manual→value)...
}
```

#### Step v4.10: Verifica autoWacItems

Nessuna modifica necessaria — con mode assegnato correttamente:
- Sender (qty<0) → mode=null → escluso da `=== 'auto'`
- Receiver (qty>0) → mode='auto' → incluso ✅
- BUY/SELL/etc. → mode=null → escluso ✅

### Test Plan v4

- [ ] `./dev.py test api all` — verifica nuovi campi in response `/transactions/types`
- [ ] `./dev.py api sync` — client rigenerato
- [ ] `./dev.py front check` — 0 errors
- [ ] `./dev.py front build --debug` — build ok
- [ ] `./dev.py test front-transaction all` — E2E pass
- [ ] Human test: Bug 9 (auto → 💡 value), Bug 10 (manual → value shown), Bug 11 (DB row → manual shown)
