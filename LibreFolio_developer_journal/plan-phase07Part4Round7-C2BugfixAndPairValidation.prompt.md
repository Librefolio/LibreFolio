# Plan: C2 Merged — Bugfix + Pair Desc/Tags Validation + Test Coverage

**Origine**: 5 bug trovati nel test manuale del Piano C (txStore refactor) + problema di description/tags divergenti nelle coppie linkate di mock data. Fix mirati + regola di validazione backend + copertura E2E da ~68 a ~82 test.

---

## 🐛 Bug

| # | Titolo | Root Cause | File |
|---|--------|-----------|------|
| B1 | `deriveStatus()` false positive "edited" su Edit paired senza modifiche | **Due cause**: (a) mock data con description diverse tra i due lati della coppia → `collectDualCreates()` copia la description del "from" su entrambi → `diffDualItem` rileva cambio nel "to" rispetto al suo original; (b) per dati legacy/sporchi il FormModal deve rendere esplicita la situazione (concatenazione + nota). La causa (a) è risolta dalla bonifica mock data. | `populate_mock_data.py`, `TransactionFormModal.svelte` |
| B2 | Clone paired TX clona solo la metà cliccata | `resolveInitialRows()` riga 235: `intent.action !== 'clone'` esclude il partner dalla risoluzione automatica | `TransactionBulkModal.svelte` |
| B3 | Picker: context menu + action buttons attivi | `TransactionsTable` definisce sempre `rowActions` e `enableActions=true`. Nessun meccanismo per disabilitarli in contesto picker. | `TransactionsTable.svelte`, `TransactionPickerModal.svelte` |
| B4 | Nessun toast dopo bulk commit | `handleBulkCommitted()` in `+page.svelte` fa solo reload. Non riceve resp dal server e non mostra toast. | `+page.svelte` |
| B5 | Reset toglie label ma sfondo resta | Conseguenza di B1 — si risolve automaticamente fixando B1 | — |
| B6 | Mock data: description divergenti nelle coppie linkate | Tutte le 8 coppie linkate in `populate_mock_data.py` hanno description diverse tra out/in (es. "Transfer AAPL to DEGIRO" vs "Transfer AAPL from IB"). Causa root del B1 e incoerenza con l'invariante "una coppia = una operazione logica". | `populate_mock_data.py` |

---

## Steps

### Step 1 — Fix B6: Bonifica mock data (tutte le coppie linkate) ✅

**File**: `backend/test_scripts/test_db/populate_mock_data.py`

Allineare description su **tutte le 8 coppie linkate**, dare la stessa stringa ad entrambi i lati:

| Coppia | Righe | Description OUT attuale | Description IN attuale | Description nuova (identica su entrambi) |
|--------|-------|------------------------|------------------------|------------------------------------------|
| 1 AAPL transfer | 1136–1163 | `"Transfer AAPL to DEGIRO"` | `"Transfer AAPL from IB"` | `"Transfer AAPL IB ↔ DEGIRO"` |
| 2 BTC transfer | 1167–1194 | `"Transfer BTC to IB"` | `"Transfer BTC from Coinbase"` | `"Transfer BTC Coinbase ↔ IB"` |
| 3 FX EUR→USD | 1198–1223 | `"FX conversion EUR→USD"` | `"FX conversion EUR→USD"` | ✅ già identiche — nessuna modifica |
| 4 Cash transfer | 1227–1254 | `"Cash transfer to IB"` | `"Cash transfer from DEGIRO"` | `"Cash transfer DEGIRO ↔ IB"` |
| Asym-a | 1269–1288 | `"[Asym-a] AAPL IB→Directa (...)"` | `"[Asym-a] AAPL Directa←IB (...)"` | `"[Asym-a] AAPL IB ↔ Directa (OWNER↔EDITOR=full)"` |
| Asym-b | 1292–1311 | analogo | analogo | `"[Asym-b] BTC IB ↔ Coinbase (OWNER↔EDITOR=full)"` |
| Asym-c | 1315–1334 | analogo | analogo | `"[Asym-c] MSFT IB ↔ DEGIRO (OWNER↔VIEWER=view-only)"` |
| Delete-safe | 1341–1360 | `"[delete-safe] ETH Coinbase→IB..."` | `"[delete-safe] ETH IB←Coinbase..."` | `"[delete-safe] ETH Coinbase ↔ IB"` |
| Asym-d | 1687–1706 | analogo | analogo | `"[Asym-d] AAPL IB ↔ HiddenBroker (OWNER↔none=locked)"` |

Tags: già identici su entrambi i lati in tutte le coppie — nessuna modifica necessaria.

---

### Step 2 — Backend: regola di validazione pair desc/tags consistency ✅

**File**: `backend/app/services/transaction_service.py`

**Nuovo metodo statico** nella classe `TransactionService`:

```python
@staticmethod
def _validate_pair_description_tags(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
    """Validate that linked pair has identical description and tags.
    Returns None if OK, otherwise (error_msg, code, params)."""
```

Logica:
- Se `a.description != b.description` → return error tuple `("Linked pair must have identical description", "pairDescriptionMismatch", {})`
- Se `a.tags != b.tags` (confronto stringhe CSV) → return error tuple `("Linked pair must have identical tags", "pairTagsMismatch", {})`
- Altrimenti → `None`

**Hook in step 6 (link resolution), righe 1127–1135**: dopo aver assegnato `related_transaction_id` e dopo `_validate_linked_pair()`, chiamare `_validate_pair_description_tags()`. Se ritorna errore → aggiungere `TXValidationIssue` con code corrispondente.

```python
# EXISTING: semantic validation
pair_result = self._validate_linked_pair(pairs[0][1], pairs[1][1])
if pair_result is not None:
    ...
    continue
# NEW: description/tags consistency
desc_result = self._validate_pair_description_tags(pairs[0][1], pairs[1][1])
if desc_result is not None:
    desc_error, desc_code, desc_params = desc_result
    issues.append(TXValidationIssue(operation="create", index=pairs[0][0], ...))
    continue
# EXISTING: set related_transaction_id
pairs[0][1].related_transaction_id = pairs[1][1].id
pairs[1][1].related_transaction_id = pairs[0][1].id
```

**Hook in step 4 (updates)**: dopo il loop degli update (dopo riga 1088), aggiungere un secondo pass per verificare la consistency finale delle coppie toccate:

```python
# 4b. Validate pair desc/tags consistency for all updated linked TXs
updated_linked_ids = set()
for orig_idx, item in parsed_updates:
    tx = existing_by_id.get(item.id)
    if tx and tx.related_transaction_id and (item.tags is not None or item.description is not None):
        updated_linked_ids.add(tx.id)

for tx_id in updated_linked_ids:
    tx = existing_by_id.get(tx_id)
    if not tx or not tx.related_transaction_id:
        continue
    partner = existing_by_id.get(tx.related_transaction_id)
    if partner is None:
        partner = await self.session.get(Transaction, tx.related_transaction_id)
    if partner is not None:
        result = self._validate_pair_description_tags(tx, partner)
        if result is not None:
            err_msg, err_code, err_params = result
            orig_idx = next((i for i, item in parsed_updates if item.id == tx_id), -1)
            issues.append(TXValidationIssue(
                operation="update", index=orig_idx, ref_id=tx_id,
                error=err_msg, code=err_code, params=err_params,
            ))
```

---

### Step 3 — Fix B1: Gestione dati sporchi nel FormModal paired ✅

**Causa B1**: se una coppia ha description diverse (dati legacy/sporchi), il FormModal mostra solo la description del "from". Quando l'utente salva senza modifiche, `collectDualCreates()` copia quella description su entrambi → `diffDualItem` rileva giustamente un cambio sul "to" → status "edited" è **corretto** perché il dato cambia davvero.

**Fix**: rendere esplicita la situazione all'utente. Quando il FormModal apre un paired edit e rileva description diverse tra `initialRow` e `partnerRow`:

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, nella `$effect` che inizializza il draft (dove fa `buildDraft(initialRow)` per riempire `draft.description`)

```typescript
// After building the draft from initialRow and fetching partnerRow:
if (partnerRow && initialRow.description !== partnerRow.description) {
    // Concatenate mismatched descriptions with explanatory note
    const fromDesc = initialRow.description ?? '';
    const partnerDesc = partnerRow.description ?? '';
    const parts: string[] = [];
    if (fromDesc) parts.push(fromDesc);
    if (partnerDesc) parts.push(partnerDesc);
    draft.description = parts.join(' | ') + 
        ' [auto-merged: pair had mismatched descriptions]';
}
```

Stessa logica per tags: se diversi, fare union (dedup) senza nota (i tags sono atomici, l'union è autoesplicativa).

**Risultato**:
- L'utente vede la concatenazione + nota → capisce cosa è successo
- Status "edited" → **corretto**, la description sta genuinamente cambiando
- Al save il backend valida che entrambi i lati abbiano stessa description → ✅ passa
- Nessuna logica di soppressione diff, nessun caso speciale in `collectDualUpdates()`

**B5** si risolve comunque: se i dati di partenza sono puliti (Step 1 bonifica), la concatenazione non scatta mai e status resta "original".

---

### Step 4 — Fix B2: Clone paired TX ✅

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`, `resolveInitialRows()` riga 246

Modificare il blocco `intent.action === 'clone'` (righe 246–255):

1. Aggiungere auto-inclusione partner: prima del `map`, per ogni TX clicata che ha `related_transaction_id`, fare `txStoreGet(tx.related_transaction_id)` e aggiungerla al `resolved` (come nel blocco edit/delete riga 235)
2. Generare un `link_uuid` condiviso per la coppia clonata
3. Su entrambe: `id: 0`, `date: today`, `related_transaction_id: null`
4. Applicare `quantityRule: 'zero'` se il tipo lo richiede

```typescript
if (intent.action === 'clone') {
    // Auto-include partner for paired clone
    for (const id of txIds) {
        const tx = txStoreGet(id);
        if (tx?.related_transaction_id && !seen.has(tx.related_transaction_id)) {
            const partner = txStoreGet(tx.related_transaction_id);
            if (partner) { resolved.push(partner); seen.add(partner.id); }
        }
    }
    const today = todayIso();
    const cloned = resolved.map((r) => {
        const c = {...r, id: 0, date: today, related_transaction_id: null} as TXReadItem;
        const rule = getTypeRule(r.type);
        if (rule.quantityRule === 'zero') c.quantity = '0';
        return c;
    });
    // Generate shared link_uuid for paired clones
    if (cloned.length === 2 && cloned[0].type === cloned[1].type) {
        const uuid = generateUUID();
        (cloned[0] as any).link_uuid = uuid;
        (cloned[1] as any).link_uuid = uuid;
    }
    return {rows: cloned, autoForm: cloned.length === 1 ? 'create' : null};
}
```

**Verifica**: Clone paired → BulkModal con 2 righe `new`, Da:/A: con link_uuid condiviso.

---

### Step 5 — Fix B3: Picker context menu ✅

**File**: `frontend/src/lib/components/transactions/TransactionsTable.svelte`, `TransactionPickerModal.svelte`

1. Aggiungere prop `hideActions?: boolean` a `TransactionsTable` (default `false`)
2. Quando `hideActions=true`: settare `enableActions=false`, `enableContextMenu=false`, `rowActions=[]`
3. In `TransactionPickerModal`: passare `hideActions={true}`

---

### Step 6 — Fix B4: Toast dopo bulk commit ✅

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

1. `handleBulkCommitted(resp)` accetta il response body `TXBatchResponse` con `results[]`
2. Conta per tipo di operazione (`create`/`update`/`delete`) i `status:'success'`
3. Singola operazione → toast dettagliato (stile delete: tipo, asset, broker, data)
4. Multiple operazioni → toast sommario: "✅ N creazioni, M modifiche, D eliminazioni salvate"
5. Chiavi i18n: `transactions.toast.bulkSummary`, `transactions.toast.created`, `transactions.toast.updated`, `transactions.toast.deleted`

---

### Step 7 — Test backend: pair desc/tags validation ✅

**File**: `backend/test_scripts/test_api/test_transactions_api.py`

Nuova classe `TestPairDescriptionTagsValidation` con 4 test:

1. **`test_create_pair_same_description_ok`** — crea coppia TRANSFER via `/transactions/commit` con description identica su entrambi → commit OK, `committed=True`

2. **`test_create_pair_different_description_rejected`** — crea coppia con description diverse → `committed=False`, issue con `code="pairDescriptionMismatch"`

3. **`test_create_pair_different_tags_rejected`** — crea coppia con tags diverse → `committed=False`, issue con `code="pairTagsMismatch"`

4. **`test_update_description_pair_consistency`** — crea coppia con description identica → update description solo su un lato senza aggiornare il partner → `committed=False`, issue `pairDescriptionMismatch`. Poi update entrambi nella stessa batch → OK

---

### Step 8 — Nuovi E2E test

**Nuovo `tx-clone.spec.ts`** (~5 test):
- Clone standalone → 1 riga new, `date=today`
- Clone paired → 2 righe new (Da:/A:), `date=today`, `link_uuid` condiviso
- Clone con `quantityRule='zero'` → `qty=0`
- Clone paired commit → coppia creata nel DB
- Clone da broker view-only → bottone non visibile

**Nuovo `tx-bulk-operations.spec.ts`** (~7 test):
- Bulk edit 2+ → griglia senza FormModal auto-open
- Edit senza modifiche + Apply → status `original` (B1 regression test)
- Mark delete + unmark → torna `original`
- Reset singola riga + Reset tutte → valori originali
- Mixed commit (create+update+delete) → toast con conteggio
- Picker: no context menu, no action buttons
- Create coppia con description diverse → errore validazione (B6/Step 2 regression test)

**Estendere `tx-paired-edit.spec.ts`** (~2 test):
- Edit paired → Apply senza modifiche → status `original`
- Edit paired cross-broker (full+view-only)

---

### Step 9 — Registrazione test runner

**File**: `scripts/test_runner/_frontend_transaction.py`

1. Aggiungere `front_tx_clone()` → `_run_playwright("transactions/tx-clone.spec.ts")`
2. Aggiungere `front_tx_bulk_operations()` → `_run_playwright("transactions/tx-bulk-operations.spec.ts")`
3. Aggiungere entrambi a `front_transaction_all()` tests list
4. Registrare in `populate_registry()` con `add_test()`

---

### Step 10 — Nota in `phase-07-transactions.md` ✅

**File**: `LibreFolio_developer_journal/RoadmapV4_UI/phases/phase-07-transactions.md`

Aggiungere dopo riga 537 (nel blocco "Features deferred from Part 4 → Part 5"):

> - **Description/Tags merge su Promote**: quando la Staging Modal propone il promote di due TX standalone in coppia, le description possono differire. Il backend rifiuterà il commit se description/tags non sono identici (`pairDescriptionMismatch`). La UX per la Parte 5 dovrà offrire una **modale di diff a 3 vie** (description lato A, description lato B, risultato merged editabile) dove l'utente sceglie o compone il testo finale. Per i tags: proporre l'**union** dei due set con checkbox per deselezionare quelli indesiderati. Solo dopo l'allineamento l'utente può committare il promote. Vedi `TransactionService._validate_pair_description_tags()`.

---

## Riepilogo file modificati

| File | Tipo | Step |
|------|------|------|
| `backend/test_scripts/test_db/populate_mock_data.py` | Edit: 8 coppie description allineate | 1 |
| `backend/app/services/transaction_service.py` | Edit: nuovo `_validate_pair_description_tags()`, hook in step 4b e step 6 | 2 |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | Edit: concatenazione dati sporchi + nota in paired edit | 3 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | Edit: clone paired auto-include partner | 4 |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Edit: prop `hideActions` | 5 |
| `frontend/src/lib/components/transactions/TransactionPickerModal.svelte` | Edit: passare `hideActions={true}` | 5 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Edit: toast dopo bulk commit | 6 |
| `backend/test_scripts/test_api/test_transactions_api.py` | Edit: nuova classe 4 test pair validation | 7 |
| `frontend/e2e/transactions/tx-clone.spec.ts` | Nuovo: ~5 test | 8 |
| `frontend/e2e/transactions/tx-bulk-operations.spec.ts` | Nuovo: ~7 test | 8 |
| `frontend/e2e/transactions/tx-paired-edit.spec.ts` | Edit: +2 test | 8 |
| `scripts/test_runner/_frontend_transaction.py` | Edit: registrazione 2 nuovi spec | 9 |
| `LibreFolio_developer_journal/.../phase-07-transactions.md` | Edit: nota diff 3-vie per Parte 5 | 10 |

## Post-modifiche

1. `./dev.py db create-clean --test` (mock data cambiati)
2. `./dev.py test api all` (test pair validation + nessuna regressione)
3. `./dev.py test front-transaction all` (E2E nuovi + regressione)

## Gap UC coverage (prima → dopo)

| Metrica | Prima | Dopo |
|---------|-------|------|
| UC coperti | 15/26 (58%) | 24/26 (92%) |
| Test E2E | 68 | ~82 |
| Spec file | 7 | 9 |
| UC non coperti | UC27-UC28 (future: Split/Promote) | Solo UC27-UC28 |

## Further Considerations

- **Mock data**: verificare che `populate_mock_data.py` abbia TX paired cross-broker con ruoli diversi per i test cross-access
- **Toast singola op**: riutilizzare `typeHtml()` e `brokerHtml()` da `+page.svelte` (stesso layout del delete toast)
- **B1 dati legacy**: la concatenazione nel FormModal è un fallback per vecchie coppie; con la regola di validazione backend (Step 2), le nuove coppie non potranno mai divergere

