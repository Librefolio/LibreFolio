# Plan: Reactive WAC in BulkModal — architettura definitiva

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

### Step 1: Estendere `DraftFields`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (riga 74-84)

Aggiungere `cost_basis_mode: 'auto' | 'manual' | null` a `DraftFields`.

Inizializzazione:
- `fieldsFromTx()` (DB row): `'manual'` se `cost_basis_override` non-null, `'auto'` se tipo TRANSFER/ADJUSTMENT senza override, `null` altrimenti
- `createOpEmpty()`: `'auto'` se tipo TRANSFER/ADJUSTMENT, `null` altrimenti
- `applyFormPayload()`: propagare il mode dal FormModal (nuovo campo `_cost_basis_mode` nel payload push)

### Step 2: Flag `include_details` su WACPreviewRequest

**File**: `backend/app/schemas/transactions.py` (riga 707-714)

Aggiungere campo `include_details: bool = Field(True, description="If False, skip qualifying_txs and missing_pairs in response")`.

**File**: `backend/app/api/v1/transactions.py` (riga 380-427)

Se `body.include_details is False`: restituire `wac_qualifying_txs: []` e `wac_missing_pairs: []` (skip del payload pesante).

### Step 3: Fingerprint derivata + `$effect` batch WAC

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

Nuovi blocchi:

```typescript
// Fingerprint di tutti i campi WAC-relevant di TUTTE le ops
let wacFingerprint = $derived.by(() => {
    // Serializza campi che influenzano il WAC di qualsiasi riga
    return ops.map(o => `${o.fields.broker_id}|${o.fields.asset_id}|${o.fields.date}|${o.fields.quantity}|${o.fields.cash?.amount ?? ''}|${o.fields.type}|${o.markedDelete ?? false}`).join(';;');
});

// Lista delle righe con mode 'auto' e params validi
let autoWacItems = $derived.by(() => {
    return ops.filter(o => o.fields.cost_basis_mode === 'auto' && o.fields.broker_id && o.fields.asset_id && o.fields.date);
});

let wacFetchInFlight = $state(false);
let wacAbortController: AbortController | null = null;
let wacDebounceTimer: ReturnType<typeof setTimeout> | null = null;

$effect(() => {
    const _fp = wacFingerprint;
    const _autoItems = autoWacItems;
    
    if (_autoItems.length === 0) return;
    
    // Debounce 800ms trailing
    if (wacDebounceTimer) clearTimeout(wacDebounceTimer);
    wacDebounceTimer = setTimeout(() => {
        fetchBatchWac(_autoItems);
    }, 800);
    
    return () => {
        if (wacDebounceTimer) clearTimeout(wacDebounceTimer);
    };
});
```

`fetchBatchWac()`:
- Abort previous request
- Build `pending_txs` from all non-delete ops (serialized as WACPendingTXItem)
- Build `excluded_tx_ids` from markedDelete edit ops
- Build `items[]` from autoWacItems (sender_broker_id, asset_id, date_range.end)
- Call `POST /wac-preview` with `include_details: false`
- On response: write `cost_basis_override` back into the matching ops
- Set `wacFetchInFlight = false`

### Step 4: Pre-commit guard

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (riga 995, `commit()`)

Prima di `buildBatchPayload()`:
- Se `autoWacItems.length > 0` e qualcuna ha `cost_basis_override === null`:
  - Se `wacFetchInFlight`: attendere il fetch in corso (await una Promise)
  - Se ancora null dopo il fetch: forzare un call sincrono (no debounce)
  - Se il fetch fallisce → bloccare commit con errore toast

### Step 5: Cell renderer — riscrittura type-agnostic

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (riga 1308-1326)

Nuova logica basata su `cost_basis_mode`:

| `cost_basis_mode` | `cost_basis_override` | Display |
|---|---|---|
| `null` | any | `—` |
| `'auto'` | valore presente | `💡 {formatted}` (grigio corsivo) |
| `'auto'` | null (loading) | `💡 …` |
| `'manual'` | valore presente | `{formatted}` (nero mono) |
| `'manual'` | null | `—` (utente ha svuotato esplicitamente) |

### Step 6: Fix parsing `fieldsFromTx`

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (riga 173-177)

Normalizzare il check `undefined` vs `null`:
```typescript
cost_basis_override: tx.cost_basis_override != null
    ? (typeof tx.cost_basis_override === 'object'
        ? {code: String(tx.cost_basis_override.code ?? ''), amount: String(tx.cost_basis_override.amount ?? '')}
        : {amount: String(tx.cost_basis_override), code: tx.cash?.code ?? ''})
    : null,
cost_basis_mode: tx.cost_basis_override != null ? 'manual' : (['TRANSFER', 'ADJUSTMENT'].includes(tx.type) ? 'auto' : null),
```

### Step 7: Sync FormModal → BulkModal mode

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Al "Apply" (`collectCreate()` / `collectDualCreates()`), aggiungere nel payload:
```typescript
_cost_basis_mode: wacPreviewMode  // 'auto' | 'manual' dal WacPreviewSection state
```

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` (`applyFormPayload()`, riga 605-616)

Aggiungere:
```typescript
if (typeof p._cost_basis_mode === 'string') target.cost_basis_mode = p._cost_basis_mode as 'auto' | 'manual';
```

### Step 8: Reazione a cambio tipo

Quando il FormModal restituisce un payload con tipo diverso:
- Se nuovo tipo ∈ `{TRANSFER, ADJUSTMENT}` e `_cost_basis_mode` non fornito → default `'auto'`
- Se nuovo tipo ∉ `{TRANSFER, ADJUSTMENT}` → `cost_basis_mode = null`, `cost_basis_override = null`

Questo avviene già in `applyFormPayload()` quando il form cambia tipo e svuota il cost_basis (FormModal riga 534: `if (t !== 'TRANSFER' && next.cost_basis_override) next.cost_basis_override = null`).

---

## Further Considerations

1. **La fingerprint è sull'intero `ops` array**: la strategia "ricalcola tutte le auto" è O(1) call con N items. Con il debounce a 800ms e il flag `include_details: false`, il costo è minimo. Non serve tracking granulare "quale riga ha invalidato quale" — troppa complessità per nessun beneficio reale sotto 50 righe.

2. **Pre-commit blocking**: se il WAC batch è in flight (debounce attivo o fetch pendente), il commit deve aspettare. Implementare con un `$state` `wacFetchInFlight: boolean` + il commit fa `await` su una Promise resoluta dal callback del fetch.

3. **L'endpoint già supporta `pending_txs`**: il BulkModal può mandare TUTTE le ops (create + edit) come `pending_txs` nel WAC call, così il calcolo tiene conto di tutto il workspace. Le righe delete vanno in `excluded_tx_ids`.

4. **Nessuna dipendenza circolare**: il WAC calc usa `quantity`, `type`, `date`, `cash` delle pending — NON il `cost_basis_override` della stessa riga. Quindi scrivere il risultato WAC nella riga non re-triggera un ricalcolo (la fingerprint non include `cost_basis_override` delle righe auto).

5. **FormModal aperta**: quando il FormModal è aperta su una riga "auto", il `WacPreviewSection` calcola con `include_details: true` (per mostrare tabella qualifying). Al "Apply" il valore torna alla BulkModal via payload. Il batch $effect ricalcolerà comunque al prossimo trigger (idempotente — il valore sarà lo stesso o aggiornato se nel frattempo altre righe sono cambiate).

---

## Test

- `./dev.py test front-transaction all` deve passare (non-regressione)
- Verifica manuale dei 6 scenari nella tabella del renderer (Step 5)
- Dopo Step 2: `./dev.py api sync` per rigenerare il client TypeScript

