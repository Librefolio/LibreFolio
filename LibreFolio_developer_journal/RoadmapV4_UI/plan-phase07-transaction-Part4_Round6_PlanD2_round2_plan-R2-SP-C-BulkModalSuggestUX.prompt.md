# Task: SP-C — BulkModal UX Polish + Suggest Overhaul + Modal Cleanup + E2E

**Parent plan**: [`plan-R2-WalktestFeedbackRound`](plan-phase07-transaction-Part4_Round6_PlanD2_round2_WalktestFeedbackRound.prompt.md)
**Depends on**: SP-A ✅ + SP-B ✅ + `./dev.py api sync`
**Previous bugfix**: [`bugfix_4_SplitSuggestPmcOverrideUx`](plan-phase07-transaction-Part4_Round6_PlanD2_bugfix_4_SplitSuggestPmcOverrideUx.prompt.md)

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

- [ ] Leggere i file chiave per capire stato attuale DOM/componenti
- [ ] Step 1: Toolbar alignment
- [ ] Step 2: Split edit → ADJUSTMENT type
- [ ] Step 3: Split type preview (icon orig → icon+label target)
- [ ] Step 4a: Suggest filtro sottrattivo
- [ ] Step 4b: Suggest banner human-readable
- [ ] Step 4c: Lightbulb per-row
- [ ] Step 4d: Banner show condition
- [ ] Step 5a: PromoteMergeModal rimuovere date/cost_basis
- [ ] Step 5b: Layout bottoni globali
- [ ] Step 5c: Footer justify-between
- [ ] Step 6a: ActionModal split BEFORE tipo su 2 colonne
- [ ] Step 6b: ActionModal split AFTER righe mancanti
- [ ] Step 6c: ActionModal promote source righe mancanti
- [ ] Step 7: Fix cella link_uuid
- [ ] Step 8a: fieldsFromTx Currency
- [ ] Step 8b: cost_basis column display
- [ ] Step 9: E2E test file + registrazione runner
- [ ] Step 10: i18n keys (4 lingue)
- [ ] `./dev.py i18n audit` → no missing keys
- [ ] `./dev.py test front-transaction tx-split-promote` → verde (NR)
- [ ] `./dev.py test front-transaction tx-bulk-operations` → verde (NR)
- [ ] `./dev.py test front-transaction tx-bulk-suggest-ux` → verde (new)

