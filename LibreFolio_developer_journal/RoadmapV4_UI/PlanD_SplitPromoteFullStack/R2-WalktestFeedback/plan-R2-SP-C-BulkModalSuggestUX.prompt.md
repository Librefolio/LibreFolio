# Task: SP-C — BulkModal UX Polish + Suggest Overhaul + Modal Cleanup + E2E

> **✅ STATUS (2026-05-24)**: COMPLETATO. Inclusi BugfixRound1 (12/12) e BugfixRound2 (WAC Preview + 11 bug).

**Parent plan**: [`plan-R2-WalktestFeedbackRound`](../plan-R2-WalktestFeedbackRound.prompt.md)
**Depends on**: SP-A ✅ + SP-B ✅ + `./dev.py api sync`
**Previous bugfix**: [`bugfix_4_SplitSuggestPmcOverrideUx`](../PlanD2-bugfix/plan-bugfix4_SplitSuggestPmcOverrideUx.prompt.md)

## Context

Backend completato (SP-A+B), api sync eseguito. 7 step dal piano master (7-12, 17) + test E2E per le feature toccate. Tutto frontend: `TransactionBulkModal.svelte` (2438 righe), `PromoteMergeModal.svelte` (274 righe), `TransactionActionModal.svelte` (324 righe), nuovo spec E2E, i18n incrementale via `./dev.py i18n`.

## ⚠️ Test Runner Registration Rule

Ogni nuovo file di test (sia backend `test_*.py` che frontend `*.spec.ts`) **deve** essere registrato nel test runner (`scripts/test_runner/`):
- **Backend API tests** → `scripts/test_runner/_backend_api.py`: aggiungere funzione runner + `add_test()` in `populate_registry()`
- **Frontend E2E tests** → `scripts/test_runner/_frontend_transaction.py`: aggiungere funzione runner + `add_test()` in `populate_registry()` + aggiungere alla lista in `front_transaction_all()`

Senza registrazione, `./dev.py test api all` / `./dev.py test front-transaction all` **non** eseguiranno i nuovi test.

## Key files to read first

- `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` — BulkModal (toolbar, columns, suggest, split, commit)
- `frontend/src/lib/components/transactions/PromoteMergeModal.svelte` — Merge UI for divergent fields
- `frontend/src/lib/components/transactions/TransactionActionModal.svelte` — Split/Promote confirmation modal
- `frontend/src/lib/components/transactions/TransactionFormModal.svelte` — FormModal (edit row click target)
- `frontend/e2e/transactions/tx-split-promote.spec.ts` — existing split/promote E2E tests
- `frontend/e2e/transactions/tx-bulk-operations.spec.ts` — existing bulk E2E tests
- `scripts/test_runner/_frontend_transaction.py` — test runner registry

## Steps

### Step 1: Toolbar alignment (Master Step 7)

**File**: `TransactionBulkModal.svelte` riga 2236-2316

Il layout `flex` è già corretto (left-group + `ml-auto`). Fix: spostare il delta-days `<div>` (riga 2251-2259) dentro il left-group con gap coerente. Aggiornare `justify-between` sul wrapper principale. i18n: verificare chiavi esistenti con `./dev.py i18n search`.

### Step 2: Split edit apre come ADJUSTMENT (Master Step 8)

**File**: `TransactionBulkModal.svelte` `handleEditRowClick` (riga 1607) / `openEditRowForm` (riga 1630)

Se `splitTxIdsSet.has(row.txId)` → prima di aprire FormModal, sovrascrivere `formInitial.type` col target da `SPLIT_TYPE_MAP`. La logica per determinare il target corretto:
- Leggere il tipo originale dalla riga
- Determinare se sender o receiver (qty < 0 → sender → `splitTypes[0]`, qty > 0 → receiver → `splitTypes[1]`)
- Settare `formInitial.type = targetType` prima di aprire il FormModal

Label undo-split (riga 1467): i18n key `transactions.bulk.undoSplit` → "Undo".

### Step 3: Split type preview migliorata (Master Step 9)

**File**: `TransactionBulkModal.svelte` colonna `type` (riga 1243-1251)

Attualmente mostra `renderTypeHtml(originale) → ✂️ ADJUSTMENT` come testo piatto con `targetType = splitTypes[0]` (sempre il primo). Fix:
- Usare icona originale **sola** (solo img, no testo label) + freccia `→` + rendering pieno del target (icon + label)
- Determinare il target corretto per ciascun lato del pair: usare la stessa logica sender/receiver di Step 2 (qty < 0 → `splitTypes[0]`, qty > 0 → `splitTypes[1]`)
- Non forzare sempre `splitTypes[0]`

### Step 4: Suggest overhaul (Master Step 10)

**File**: `TransactionBulkModal.svelte`

#### 4a. Filtro sottrattivo
In `$effect` (riga 1880-1913): nella request `promote-suggest`, filtrare client-side i risultati rimuovendo candidati il cui `id` è già presente tra gli `ops[]` (edit rows). Se il backend supporta `exclude_ids`, usarlo; altrimenti filtro post-risposta:
```typescript
// dopo aver ricevuto suggestFromDB
for (const [txId, candidates] of suggestFromDB) {
    suggestFromDB.set(txId, candidates.filter(c => !opsEditIds.has(c.id)));
}
```

#### 4b. Banner human-readable
Riga 2194-2226. Formato aggiornato:
- Per suggest local (new+new): `• [🔗 Merge] Row#N (icon) and Row#M (icon) → Target (icon) (ΔNd)`
- Per suggest DB: `• [🔗 Merge] Row#N (icon) and DB#ID (icon) → Target (icon) (ΔNd)`
- `Row#N` = indice 1-based della riga nella griglia, cliccabile → scroll-to-row nella DataTable
- Multi-match: se un input TX ha >1 candidato DB → sotto-lista `<ul>` indentata

#### 4c. Lightbulb per-row
Aggiungere row action `suggest` (icona `Lightbulb` da lucide-svelte):
- `visible`: riga standalone (no `partnerId`, no `partnerPayload`) che ha almeno un suggest in `allSuggestions`
- `onClick`: scroll al banner suggest + evidenziarlo con flash animation

#### 4d. Banner show condition
Il banner suggest compare solo se almeno 1 TX suggerita è già caricata nella griglia (`ops[]`). Se i suggerimenti sono solo tra DB↔DB (nessuna TX nella griglia), non mostrare.

### Step 5: PromoteMergeModal — rimuovere date e cost_basis (Master Step 11)

**File**: `PromoteMergeModal.svelte`

#### 5a. Rimuovere sezioni date e cost_basis
- Rimuovere `diffDate` derived (riga 47) e `diffCostBasis` derived (riga 48)
- Rimuovere `resDate` state (riga 37) e `resCostBasis` state (riga 38)
- Rimuovere dal `hasDifferences` computed: togliere `|| diffDate || diffCostBasis` (riga 49)
- Rimuovere dalla `currentSnapshot()` (riga 55): togliere `resDate, resCostBasis`
- Rimuovere dal `$effect` reset (riga 61-71): togliere settaggio `resDate` e `resCostBasis`
- Rimuovere da `allLeft/allMerge/allRight` gli if per date/cost_basis
- Rimuovere da `handleConfirm` gli if per date/cost_basis
- Rimuovere le sezioni HTML dei campi date (riga 212-227) e cost_basis (riga 229-245)

Se date o cost_basis divergono, l'utente li corregge nel FormModal dopo il promote — non nella merge modal.

#### 5b. Layout bottoni globali
Spostare il div `allLeft/allMerge/allRight` (riga 136-152) **sotto** i campi divergenti, sopra il footer. Invertire label:
- Sinistra: `◀ {$t('transactions.promote.allLeft')}`
- Centro: solo icona `⟷` (size=24), nessun testo
- Destra: `{$t('transactions.promote.allRight')} ▶`

#### 5c. Footer align
Cambiare footer (riga 252) da `justify-end` a `justify-between`.

### Step 6: TransactionActionModal — allineare righe BEFORE/AFTER (Master Step 12)

**File**: `TransactionActionModal.svelte`

#### 6a. Split BEFORE: tipo su due colonne
Riga 125-134: il tipo è con `colspan="2"` centrato. Cambiarlo a **due colonne separate** (From e To) con icona+label. Entrambi i lati mostrano lo stesso tipo paired, ma con layout coerente con gli altri campi (date, qty, cash, broker).

#### 6b. Split AFTER: aggiungere righe mancanti
Riga 183-213: la tabella AFTER ha solo `type`, `cash`, `broker`. Mancano:
- **date** — stesse date del BEFORE (split non cambia la data)
- **quantity** — stessi valori del BEFORE
- **tags** — stessi valori del BEFORE (condizionale: mostrare riga solo se almeno un lato ha tags)
- **description** — stessi valori del BEFORE (condizionale)

Aggiungere dopo il `<tr>` del type, prima di cash:
```
date → transaction.date / partner?.date
quantity → transaction.quantity / partner?.quantity
```
E dopo broker:
```
tags → transaction.tags / partner?.tags (condizionale)
description → transaction.description / partner?.description (condizionale)
```

#### 6c. Promote source table: aggiungere righe mancanti
Riga 231-266: la tabella promote ha `date`, `type`, `cash`, `broker`. Mancano:
- **quantity** — dopo cash
- **tags** — dopo broker (condizionale)
- **description** — dopo tags (condizionale)

### Step 7: Fix cella link_uuid nel BulkModal (Master Step 17)

**File**: `TransactionBulkModal.svelte` colonna `link_uuid` (riga 1389-1403)

La cella `link_uuid` mostra solo il partner ID (`↔ #75`) — dovrebbe mostrare **entrambi** gli ID nel formato `#62 ↔ #75`. Fix:

```typescript
// PRIMA (riga 1398) — mostra solo il partner
if (row.partnerId != null) return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">↔ #${row.partnerId}</code>`};

// DOPO — mostra self ↔ partner
if (row.partnerId != null) {
    const selfId = opTxId(row) ?? '?';
    return {type: 'html', html: `<code class="text-[10px] font-mono text-gray-400">#${selfId} ↔ #${row.partnerId}</code>`};
}
```

Anche il ramo 3 (riga 1400) ha una condizione ridondante `row.op === 'create' ? ... : ''` (siamo già dentro un `if (row.op === 'create')`) — semplificare in `row.link_uuid?.slice(0, 8)`.

Il fix riguarda **solo questa cella** della colonna `link_uuid` — non toccare le colonne ID, date, cash, broker che usano `renderDualHtml` con Da:/A: (quelle sono OK).

### Step 8: cost_basis_override column — adattare a Currency (SP-A follow-up)

**File**: `TransactionBulkModal.svelte`

Dopo SP-A il backend invia `cost_basis_override` come `{code, amount}` (oggetto Currency), non più stringa.

#### 8a. `fieldsFromTx` (riga 180)
Attualmente: `cost_basis_override: tx.cost_basis_override ?? ''`
Se `tx.cost_basis_override` è oggetto Currency `{code, amount}` → serializzare come stringa `"amount code"` (es. `"42.50 EUR"`).
Se `null` → stringa vuota `''`.
```typescript
cost_basis_override: tx.cost_basis_override
    ? `${tx.cost_basis_override.amount} ${tx.cost_basis_override.code}`
    : '',
```

#### 8b. Colonna cell (riga 1377)
Display: se `cost_basis_override` non vuoto → mostrare con `formatCurrencyAmountHtml` (riusare il pattern di `formatCashText`).
Se vuoto → mostrare `<span class="text-gray-400 italic">auto</span>` (senza flag valuta — "auto" indica che il backend calcola il WAC).

### Step 9: E2E test `tx-bulk-suggest-ux.spec.ts`

**File**: `frontend/e2e/transactions/tx-bulk-suggest-ux.spec.ts` (nuovo)

Nuovo file test per feature SP-C + registrazione in `scripts/test_runner/_frontend_transaction.py`.

| ID | Test | Verifica |
|----|------|----------|
| FE-SP-C1 | Split badge + type preview | Select TX paired → open bulk edit → verify `✂️ split` badge e preview tipo `→ ADJUSTMENT` con icone |
| FE-SP-C2 | Split edit apre come ADJUSTMENT | Click edit su riga split-queued → verify FormModal si apre con type diverso dall'originale |
| FE-SP-C3 | Undo split | Dopo split → click undo → verify badge rimosso e riga partner sparita |
| FE-SP-C4 | Suggest banner + delta slider | Apri bulk con TX standalone → verify banner `data-testid="promote-suggest-banner"` presente → cambia slider → verify banner aggiorna |
| FE-SP-C5 | ActionModal split AFTER rows | Split da main table → verify modale `data-testid="tx-action-after"` ha righe date, qty, tags, desc |

Registrare in `_frontend_transaction.py`:
```python
def front_tx_bulk_suggest_ux(...): ...
add_test(cat, "tx-bulk-suggest-ux", front_tx_bulk_suggest_ux, ...)
```
Aggiungere a `front_transaction_all()` tests list.

### Step 10: i18n incrementale

Via `./dev.py i18n add` — tutte 4 le lingue (EN, IT, FR, ES). Chiavi nuove:

| Key | EN | IT | FR | ES |
|-----|----|----|----|-----|
| `transactions.bulk.undoSplit` | Undo | Annulla | Annuler | Deshacer |
| `transactions.promoteSuggest.rowRef` | Row #{n} | Riga #{n} | Ligne #{n} | Fila #{n} |
| `transactions.bulk.suggestLightbulb` | Show suggestion | Mostra suggerimento | Afficher suggestion | Mostrar sugerencia |

Verificare con `./dev.py i18n audit` alla fine per assicurarsi che non ci siano chiavi mancanti.

## Resolved Considerations

1. **`cost_basis_override` display "auto"**: quando il campo è vuoto (= calcolato dal backend via WAC), mostrare solo la label `auto` in grigio corsivo — nessun flag valuta, nessun importo. Quando è valorizzato (manual override), mostrare `42.50 EUR` con il pattern `formatCurrencyAmountHtml`. Questo differenzia visivamente "il backend calcola" da "l'utente ha impostato".

2. **Suggest `exclude_ids`**: il backend `promote-suggest` (`POST /transactions/promote-suggest`) **non** supporta `exclude_ids` — accetta solo `inputs[]` + `tolerance_days` query param. Il filtro va fatto **client-side**: dopo aver ricevuto i risultati, rimuovere i candidati il cui `id` è già tra gli `ops[]` edit rows. Nessuna modifica backend necessaria.

3. **Mock data per E2E**: verificato in `populate_mock_data.py` — entrambi i tag presenti:
   - `delete-safe` tag → TX paired TRANSFER ETH IB↔Coinbase (righe 1368-1398) ✅
   - `promote-test` tag → TX standalone W/D/Adj su Coinbase+IB (righe 1419-1488) ✅
   Nessuna modifica mock data necessaria.

## Execution checklist

- [x] Leggere i file chiave per capire stato attuale DOM/componenti
- [x] Step 1: Toolbar alignment
- [x] Step 2: Split edit → ADJUSTMENT type
- [x] Step 3: Split type preview (icon orig → icon+label target)
- [x] Step 4a: Suggest filtro sottrattivo
- [x] Step 4b: Suggest banner human-readable
- [x] Step 4c: Lightbulb per-row
- [x] Step 4d: Banner show condition
- [x] Step 5a: PromoteMergeModal rimuovere date/cost_basis
- [x] Step 5b: Layout bottoni globali
- [x] Step 5c: Footer justify-between
- [x] Step 6a: ActionModal split BEFORE tipo su 2 colonne
- [x] Step 6b: ActionModal split AFTER righe mancanti
- [x] Step 6c: ActionModal promote source righe mancanti
- [x] Step 7: Fix cella link_uuid
- [x] Step 8a: fieldsFromTx Currency
- [x] Step 8b: cost_basis column display
- [x] Step 9: E2E test file + registrazione runner
- [x] Step 10: i18n keys (4 lingue)
- [x] `./dev.py i18n audit` → no missing keys
- [x] `./dev.py test front-transaction tx-split-promote` → verde (NR) ✅ 4 passed, 1 skipped
- [x] `./dev.py test front-transaction tx-bulk-operations` → verde (NR) ✅ 10 passed
- [x] `./dev.py test front-transaction tx-bulk-suggest-ux` → verde (new) ✅ 3 passed
- [x] All 14 transaction E2E suites green (2026-05-18) — includes fixes to tx-bulk-operations + tx-commit-all-types (Coinbase balance issue, CompactCashCell testid, paired row filters)

## Deviations from plan

1. **Step 1 (Toolbar alignment)**: the step was about the inline selection toolbar inside `TransactionBulkModal.svelte` (not the main page toolbar nor the delta-days slider). The selection toolbar (counter + reset + delete + promote) was positioned LEFT, near the picker/slider. Fix: moved the entire `{#if bulkTableSelectedRows.length > 0}` block INSIDE the `ml-auto` right group, after `ColumnVisibilityToggle`. Now when rows are selected the selection actions appear RIGHT, next to the column filter toggle. Note: `flex-row-reverse` on the right group means visual order is reversed (leftmost in code = rightmost visually).

2. **Step 5 (PromoteMergeModal)**: also needed to update the divergence checks in `BulkModal.svelte` — 3 places where `handlePromoteSelected` and `triggerPromoteFromSuggestion` compared date/cost_basis. Removed those from divergence detection (only description+tags trigger MergeModal now).

3. **Step 9 (E2E tests)**: tests initially failed because:
   - Wrong toolbar testid: used `tx-toolbar-edit` instead of correct `toolbar-action-edit`
   - Single row selection triggers FormModal auto-open (blocking BulkModal). Fix: select 2+ rows to get grid-only view, plus dismiss FormModal if it appears.
   - Reduced test count to 3 (C1, C4, C5) — C2/C3 patterns already covered by existing tx-split-promote.spec.ts tests.

4. **i18n `transactions.promoteSuggest.rowRef`**: added and wired to the suggest banner template (replaced hardcoded `Row #N` with `$t('transactions.promoteSuggest.rowRef', {values: {n}})`).

5. **"Remove from batch" action missing on initial edit rows** (post-walktest discovery): the `remove-from-batch` row action was only visible for rows added via PickerModal (`addedViaPicker === true`). Rows loaded from the initial intent (selected in main table → Edit) did **not** show the action. Root cause: visibility condition `row.op === 'edit' && row.addedViaPicker && deriveStatus(row) !== 'new'` was too restrictive. Fix: changed to `row.op === 'edit' && deriveStatus(row) !== 'delete'` — now all edit rows (both intent-loaded and picker-added) show the remove action, except those already marked for deletion. The `deriveStatus !== 'delete'` guard avoids showing "remove" on a row that's already in delete state (user should use "reset" or "undo delete" instead).

6. **Actions column too narrow in BulkModal**: with the addition of lightbulb, split, undo-split, and remove-from-batch row actions, the default `100px` actions column was too narrow — icons overflowed or wrapped. Fix: passed `actionsColumnWidth="160px"` to the DataTable in BulkModal.

## Walktest Results (2026-05-16)

### Passed ✅
| # | Test |
|---|------|
| WT-1 | Toolbar alignment (right) |
| WT-2 | Split edit → target type (FormModal opens with correct ADJUSTMENT type) |
| WT-10 | ActionModal promote source (quantity, tags, desc rows present) |
| WT-11 | Link UUID cell (#self ↔ #partner) |
| WT-13 | Remove from batch (all edit rows) |
| WT-14 | Actions column width (160px) |

### Failed / Partial ❌

#### BUG-C1: Split partner row position (WT-2)
**Observed**: la transazione splittata (partner row) viene aggiunta **in fondo** alla griglia.
**Expected**: deve apparire subito **sotto** la riga principale (adiacente).
**File**: `TransactionBulkModal.svelte` — dove si inserisce il partner op in `ops[]` dopo lo split.

#### BUG-C2: Reset All non visibile dopo split / non annulla split (WT-2)
**Observed**: "Reimposta tutto" non compare dopo un split (solo dopo un edit). Quando cliccato dopo un edit, annulla l'edit ma NON lo split.
**Expected**: reset all dovrebbe resettare anche gli split pendenti (rimuovere da `pendingSplits` + rimuovere partner rows aggiunte).
**File**: `TransactionBulkModal.svelte` — `resetAll()` function + condizione di visibilità del bottone.

#### BUG-C3: Split + Edit → commit perde gli edit (WT-2) ⚠️ CRITICO
**Observed**: dopo split + edit di una riga splittata, il validate mostra `{}` e il commit invia solo `{"splits":[...]}` senza le edits.
**Root cause probabile**: la riga split-queued è `op === 'edit'` ma `deriveStatus()` potrebbe non marcarla come `edited` perché i suoi fields originali vengono confrontati con quelli attuali senza considerare il cambio di tipo. Oppure il `buildCommitPayload` filtra le righe split-queued in modo errato.
**File**: `TransactionBulkModal.svelte` — `buildCommitPayload()` + `deriveStatus()` per split-queued rows.

#### BUG-C4: Split type preview — seconda riga ha formato vecchio (WT-3)
**Observed**: la prima riga mostra correttamente `[icona orig] → [icona target + label]`, ma la **seconda** riga (partner aggiunta dallo split) mostra ancora il formato vecchio: `renderTypeHtml → ✂️ ADJUSTMENT`.
**Root cause**: il partner row viene aggiunto con un path diverso (forse senza passare per la stessa colonna cell logic, o la condizione `splitTxIdsSet.has(txId)` non rileva il partner).
**File**: `TransactionBulkModal.svelte` — colonna `type` cell function, verificare che il partner txId sia in `splitTxIdsSet`.

#### BUG-C5: ActionModal — non scrolla, footer irraggiungibile (WT-3/9)
**Observed**: la modale ActionModal (split BEFORE/AFTER) non scrolla verticalmente. Con dati lunghi (tags, desc) il footer è tagliato.
**Fix**: aggiungere `overflow-y-auto max-h-[80vh]` al contenuto della modale.
**File**: `TransactionActionModal.svelte` — div wrapper interno.

#### BUG-C6: Numeri non formattati (quantità/importo) in ActionModal (WT-3/9)
**Observed**: quantità mostra `0.050000` e `-0.050000` (6 decimali inutili).
**Expected**: usare l'helper di formattazione numeri (trailing zeros removal). Esistente nel progetto — trovare e riusare.
**File**: `TransactionActionModal.svelte` — dove mostra `transaction.quantity`.

#### BUG-C7: Suggest redesign — logica completamente sbagliata (WT-4/5/6/7) ⚠️ CRITICO
**Observed**: il banner mostra suggerimenti dal DB (`DB #44`) per TX nella griglia. L'utente importa la gemella dal picker, ma il banner SCOMPARE invece di aggiornarsi.
**Expected behavior (ridefinito)**:
1. Il banner deve mostrare SOLO suggerimenti **tra righe già presenti nella BulkModal** (local↔local), MAI righe DB non caricate.
2. Il bottone 💡 (lightbulb) **globale** (nella toolbar, tra "cerca/aggiungi" e "max Δ giorni") → apre il **PickerModal** pre-filtrato con gli ID dei candidati compatibili ottenuti dall'endpoint `promote-suggest` per le TX attualmente caricate.
3. Il bottone 💡 per-row fa la stessa cosa ma filtrato per quella specifica riga.
4. Una volta che l'utente importa una TX suggerita, il banner si aggiorna mostrando la coppia (poiché ora entrambe sono nella griglia).
5. L'endpoint `promote-suggest` riceve TUTTI i campi della TX (non filtrare nel frontend — `id`, `type`, `broker_id`, `date`, `currency`, `asset_id`, `amount`, `quantity`) così il backend ha tutto per fare matching corretto.

**Problema secondario**: `promote-suggest` riceve input parziali (mancano `amount`/`quantity` per alcune TX → il backend non può fare matching).

#### BUG-C8: PromoteMergeModal — frecce invertite + concat non centrato (WT-8)
**Observed**: 
- Bottone "◀ Tutti sinistra" ha la freccia che punta via dal centro (dovrebbe puntare VERSO il centro = `▶` per sinistra)
- Bottone "Tutti destra ▶" ha la freccia che punta via dal centro (dovrebbe puntare VERSO il centro = `◀` per destra)  
- Il concatena (⟷) nella sezione descrizione mostra la label — deve solo mostrare il simbolo `↔`
- I bottoni sinistra/destra devono essere sui BORDI (non centrati), solo il merge `↔` al centro → usare `justify-between`

**Fix atteso**:
```
[▶ All Left]          [↔]          [All Right ◀]
```
Frecce che "puntano al centro" = indicano da dove prendono i valori.

#### BUG-C9: Cost basis override — campo mancante nel FormModal (WT-12)
**Observed**: FormModal non ha un campo per `cost_basis_override` in formato Currency `{code, amount}`. Inserendo manualmente una stringa, il backend rigetta con "Input should be a valid dictionary or instance of Currency".
**Root cause**: il FormModal non è stato aggiornato per SP-A (Currency object). La colonna display nella griglia BulkModal funziona, ma edit/create nel FormModal è rotto.
**Fix**: aggiungere un campo stile "importo + valuta" nel FormModal con tooltip esplicativo. **Questo è fuori scope SP-C** — va pianificato come step separato.

#### BUG-C10: Suggest — non rileva coppia se una TX è stata editata localmente (WT-15)
**Observed**: se dopo aver importato una TX nel batch la si edita (es. cambio data), il suggest non la riconosce più come coppia.
**Root cause**: l'endpoint `promote-suggest` confronta con i dati inviati come `inputs[]`. Se s edits i dati nella BulkModal ma non si riinvia il suggest con i dati AGGIORNATI, il match fallisce.
**Fix**: il `$effect` che chiama `promote-suggest` deve usare i **fields correnti** dalla griglia (post-edit), non i dati originali.

#### BUG-C11: ID filter nel DataTable — permette decimali (minor)
**Observed**: il filtro colonna ID (sia main table che picker) permette di inserire numeri decimali (slider/input). Gli ID sono interi.
**Fix**: forzare `step="1"` e `type="number"` con validazione integer nel DataTableColumnFilter per colonne con tipo ID/integer.

---

## Analisi Classi di Problemi

### Classe A — Commit/Payload Logic (CRITICO)
**BUG-C3** (edits persi nel commit)

Questo è il bug più grave. Il `buildCommitPayload` non include le edits per righe split-queued, probabilmente perché il `deriveStatus` non le segna come `edited`. Il tipo cambia (TRANSFER → ADJUSTMENT) ma questo cambio avviene solo nel FormModal overlay — molto probabilmente non viene persistito nei `fields` dell'op.

### Classe B — Suggest Architecture (REDESIGN)
**BUG-C7, BUG-C10**

La suggest logic è architetturalmente sbagliata. Il flusso corretto è:
1. Chiamare `promote-suggest` con TUTTI i dati correnti delle TX nella griglia
2. Usare i risultati per due cose: (a) mostrare nel banner le coppie **già presenti** nella griglia, (b) offrire il bottone 💡 per importare le coppie **non ancora** nella griglia
3. Il banner deve SOLO fare local matching; le coppie DB sono un "suggerimento per importare" via picker, non un suggerimento di azione diretta

### Classe C — UX/Layout (tutti fixabili rapidamente)
**BUG-C1** (posizione partner), **BUG-C2** (reset all + split), **BUG-C4** (preview partner), **BUG-C5** (scroll modale), **BUG-C6** (formattazione numeri), **BUG-C8** (frecce invertite), **BUG-C11** (filtro ID decimali)

### Classe D — FormModal Currency (fuori scope)
**BUG-C9** (cost_basis_override field nel FormModal)

Questo richiede un redesign del campo nel FormModal — non era in scope SP-C (che lavorava solo sulla colonna display BulkModal). Va schedulato come step dedicato.

### Priorità suggerita per il prossimo bugfix plan
1. **BUG-C3** (commit perde edits) — P0, blocca l'uso reale dello split
2. **BUG-C7** (suggest redesign) — P1, architettura da rivedere
3. **BUG-C4** (preview partner) — P2, cosmetico ma confuso
4. **BUG-C1, C2, C5, C6, C8** — P2, quick fixes
5. **BUG-C9** (FormModal currency) — P3, feature incomplete ma non bloccante
6. **BUG-C10, C11** — P3, polish

## Follow-up Plan

→ [`plan-R2-SP-C-BugfixRound1`](./SP-C-Bugfix/plan-SP-C-BugfixRound1.prompt.md) — rientro completo per tutti gli 11 bug.
