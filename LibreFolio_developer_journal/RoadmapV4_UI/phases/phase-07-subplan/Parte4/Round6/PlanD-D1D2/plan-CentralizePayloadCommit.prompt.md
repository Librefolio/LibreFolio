# Plan: Centralizzazione Payload + API Commit/Validate — Creazione, Migrazione, Test

**Date**: 2026-05-20
**Status**: ✅ COMPLETED (2026-05-20) — txPayloadHelpers.ts + txCommitApi.ts implemented
**Link back**: [`plan-SP-C-BugfixRound2-WacPreview.prompt.md`](./R2-WalktestFeedback/SP-C-Bugfix/plan-SP-C-BugfixRound2-WacPreview.prompt.md) (riga 762)

---

**TL;DR**: Creare un sotto-sistema centralizzato (`txPayloadHelpers.ts` + nuovo `txCommitApi.ts`) che racchiude: (1) la costruzione dei payload (single, dual, batch), (2) la chiamata API commit/validate con gestione risposta uniforme. Migrare tutti i 9 callsite (FormModal, BulkModal, BulkDeleteLinkedPairModal, +page.svelte) al sotto-sistema unificato. Poi creare una suite Vitest completa per le funzioni pure. I test E2E esistenti continuano a passare: l'interfaccia utente è identica, cambia solo l'interno della costruzione del pacchetto.

---

## Callsite attuali (prima della migrazione)

| Caller | Tipo | Payload |
|--------|------|---------|
| `TransactionFormModal` commit | 4 branch (create, update, dual-create, dual-update) | `{creates:[…]}` o `{updates:[…]}` |
| `TransactionFormModal` validate | 4 branch + merge con bulk context | same + merge |
| `TransactionBulkModal` commit | Mixed batch | `{creates, updates, deletes, splits, promotes}` |
| `TransactionBulkModal` validate | Mixed batch | same (no promotes) |
| `BulkDeleteLinkedPairModal` commit | Deletes only | `{deletes:[…]}` |
| `+page.svelte` confirmDeleteModal | Deletes only | `{deletes:[…]}` |
| `+page.svelte` validateDeleteModal | Validate deletes | `{deletes:[…]}` |
| `+page.svelte` confirmSplit | Splits only | `{splits:[…]}` |
| `+page.svelte` onPromoteMergeConfirm | Promotes only | `{promotes:[…]}` |

---

## Decisioni architetturali

- **`opsToIntents` eliminato** — `PendingOp.op` + `markedDelete` + `deriveStatus()` descrivono già l'intent. Nessun layer aggiuntivo.
- **Nessuna pre-validazione frontend** — il backend valida in `execute_batch`, il frontend invia e basta. Future-proof.
- **FormModal con transazioni collegate** — nessun caso speciale: `collectDualCreates()` / `collectDualUpdates()` emettono sempre 2 items in `_items[]`. Sempre 2 transazioni arrivano, sempre 2 vengono gestite.

---

## Step 0 — Rinominare `saveWithRetry` → `trySave`

**File**: `frontend/src/lib/utils/saveWithRetry.ts` → `frontend/src/lib/utils/trySave.ts`

Il nome `saveWithRetry` è fuorviante: la funzione NON fa retry. È un wrapper try/catch unificato che:
- Esegue una chiamata async
- Mai lancia (ritorna `SaveResult<T>` discriminated union)
- Estrae messaggi human-readable da errori FastAPI/Pydantic
- Opzionalmente mostra toast

**Azioni**:
1. Rinominare il file: `saveWithRetry.ts` → `trySave.ts`
2. Rinominare la funzione esportata: `saveWithRetry` → `trySave`
3. Rinominare il tipo: `SaveWithRetryOptions` → `TrySaveOptions`
4. Aggiornare tutti gli import (7 file):
   - `AssetModal.svelte`
   - `AssetCurrencyChangeModal.svelte`
   - `PasswordChangeModal.svelte`
   - `FxPairAddModal.svelte`
   - `TransactionFormModal.svelte`
   - `TransactionBulkModal.svelte`
   - `txCommitApi.ts` (nuovo, Step 2)
5. Aggiornare commenti/docstring nel file che referenziano il vecchio nome

**Nota**: `extractErrorMessage`, `extractValidationIssues`, `formatValidationIssues` restano nello stesso file (ora `trySave.ts`) — sono helper correlati. Il tipo `SaveResult<T>` resta invariato.

---

## Step 1 — Estendere `txPayloadHelpers.ts` con `buildDualCreatePayloads`

**File**: `frontend/src/lib/utils/txPayloadHelpers.ts`

Aggiungere:

- **`TxDualSide`** — interfaccia minimale per il lato "to": `{broker_id, date?, cash?, quantity?, cost_basis_override?}`
- **`buildDualCreatePayloads(layout, from, to, linkUuid): [Record, Record]`** — centralizza la logica dei 3 rami di `FormModal.collectDualCreates()` (fx, transfer_asset, transfer_cash). Usa internamente `buildCreatePayload` dove possibile, oppure costruzione manuale dove le regole di segno sono specifiche al layout.
- **`buildBatchPayload(input)`** — pura aggregazione di resolved ops + comandi split/promote in payload API:

```typescript
/** A single resolved operation — result of iterating PendingOps and diffing. */
export interface ResolvedOp {
    intent: 'create' | 'update' | 'delete';
    payload?: Record<string, unknown>;        // for create/update
    deleteId?: number;                        // for delete
    partnerPayload?: Record<string, unknown> | null;  // partner create/update
    partnerDeleteId?: number | null;          // partner delete
}

/**
 * Assemble the final batch API payload from resolved CUD ops + atomic commands.
 *
 * Splits/promotes are first-class inputs (not "extras") because they affect
 * how edits are resolved: split-queued rows have type stripped from updates,
 * promote-queued rows are skipped entirely. The resolveOps() caller has already
 * applied these rules — buildBatchPayload just assembles the final payload.
 */
export function buildBatchPayload(input: {
    ops: ResolvedOp[];
    splits?: {id_a: number; id_b: number}[];
    promotes?: Record<string, unknown>[];
}): Record<string, unknown>
```

**Design rationale — splits/promotes come input atomico**:
Il backend esegue la batch atomicamente: `deletes → splits → updates → creates → link resolution`. Il frontend deve assemblare il payload completo in una volta perché splits influenzano gli updates (tipo viene strippato dalle righe split-queued). `resolveOps()` riceve `splitTxIds`/`promoteTxIds` per skipare/strippare correttamente, poi `buildBatchPayload` mette tutto insieme.

Nessuna dipendenza da Svelte, txStore, o API — funzioni pure testabili.

---

## Step 2 — Creare `txCommitApi.ts` — wrapper API commit + validate

**File**: `frontend/src/lib/utils/txCommitApi.ts` (NUOVO)

Centralizza la chiamata API + gestione risposta:

```typescript
export interface CommitResult {
    committed: boolean;
    issues: ValidationIssue[];
    results?: Array<{ids?: number[]; operation?: string}>;
    /** Set only on network/HTTP error (saveWithRetry returned status='error'). */
    networkError?: string;
    rawResponse: unknown;
}

/** Call POST /transactions/commit. Always uses saveWithRetry internally. */
export async function commitTransactions(
    payload: Record<string, unknown>,
    opts?: { fallback?: string; toast?: boolean }
): Promise<CommitResult>

/** Call POST /transactions/validate. Same pattern, different endpoint. */
export async function validateTransactions(
    payload: Record<string, unknown>,
    opts?: { fallback?: string; toast?: boolean }
): Promise<CommitResult>
```

Logica interna:
- Wrappa con `trySave` (wrapper try/catch unificato che estrae messaggi human-readable da FastAPI — NON fa retry)
- Default: `{toast: false}` — quasi tutti i caller gestiscono errori inline, non via toast
- Caller passa `fallback` con la stringa i18n già tradotta: `$t('transactions.form.saveFailed')`
- Se `trySave` ritorna `status='error'` → `CommitResult.networkError` = messaggio, `committed=false`
- Se la risposta ha successo HTTP ma `committed=false` → filtra `extra_forbidden` issues (li logga come bug FE, non li mostra all'utente)
- Ritorna `CommitResult` uniforme

**Design rationale — perché `trySave` è sempre usato**:
Attualmente 5 callsite su 9 usano raw try/catch con `e.message`. `trySave` con `toast:false` NON ha side-effects e dà messaggi più ricchi gratis (FastAPI detail parsing, Pydantic validation array). Tutti i callsite migliorano senza costo.

Questo elimina la duplicazione del pattern try/catch + response handling in tutti i 9 callsite.

---

## Step 3 — Migrare `TransactionFormModal.svelte` (4 branch commit + 2 validate)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

1. `collectDualCreates()` (~100 LOC) → diventa ~5 LOC che chiama `buildDualCreatePayloads(pairLayout, draftToTxFields(), dualToSide, linkUuid)`
2. `commit()` (righe 1062-1177, ~115 LOC, 4 branch identici nel try/catch) → diventa ~30 LOC:
   ```typescript
   const payload = pairLayout
       ? (mode === 'edit' ? {updates: collectDualUpdates()} : {creates: collectDualCreates()})
       : (mode === 'edit' ? {updates: [collectUpdate()]} : {creates: [collectCreate()]});
   const result = await commitTransactions(payload);
   if (!result.committed) { issues = result.issues; commitFailed = true; return; }
   onCommitted?.({transaction_id: result.results?.[0]?.ids?.[0] ?? null});
   onClose();
   ```
3. `validateFn` (righe 714-808, ~95 LOC) → semplificato: payload building + `const result = await validateTransactions(payload)` + filter issues per `myIndex`

**Delta stimato**: −140 LOC

---

## Step 4 — Migrare `TransactionBulkModal.svelte` (commit + validate + getBulkContext)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

1. Estrarre `resolveOps(excludeTempId?): ResolvedOp[]` — funzione interna che itera `ops`, chiama `deriveStatus`, `collectCreate`, `collectUpdate`, riceve `splitTxIds`/`promoteTxIds` per skipare/strippare, produce array `ResolvedOp[]`
2. `commit()` (righe 1025-1129):
   - `const payload = buildBatchPayload({ops: resolveOps(), splits: pendingSplits.map(s => ({id_a: s.id_a, id_b: s.id_b})), promotes: pendingPromotes});`
   - `const result = await commitTransactions(payload, {fallback: $t('transactions.bulk.saveFailed')});`
   - gestione `result.committed` / `result.issues` / `result.networkError`
3. `validateFn` (righe 878-948): `validateTransactions(buildBatchPayload({ops: resolveOps(), splits: pendingSplits.map(...)}))`
4. `getBulkContextExcluding(tempId)` (righe 801-831): `buildBatchPayload({ops: resolveOps(tempId)})`

**Delta stimato**: −60 LOC (3 loop da ~30 LOC → 3 one-liner)

---

## Step 5 — Migrare `BulkDeleteLinkedPairModal.svelte`

**File**: `frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte`

`commit()` (righe 120-142) → usa `commitTransactions({deletes: finalIds})`:
```typescript
const result = await commitTransactions({deletes: finalIds});
if (!result.committed) { rolledBack = {errors: result.issues.map(i => i.error)}; }
else { onCommitted?.(result.rawResponse); onClose(); }
```

**Delta stimato**: −8 LOC (rimuove try/catch manuale)

---

## Step 6 — Migrare `+page.svelte` (delete, validate-delete, split, promote)

**File**: `frontend/src/routes/(app)/transactions/+page.svelte`

1. `confirmDeleteModal()` (righe 813-860): → `commitTransactions({deletes: ids})`
2. `validateDeleteModal()` (righe 870-892): → `validateTransactions({deletes: ids})`
3. `confirmSplit()` (righe 634-658): → `commitTransactions({splits: [{id_a, id_b}]})`
4. `onPromoteMergeConfirm()` (righe 603-626): → `commitTransactions({promotes: [...]})`

Ogni funzione perde il try/catch boilerplate e usa il `CommitResult` uniforme.

**Delta stimato**: −40 LOC

---

## Step 7 — Rimuovere duplicazioni `TXReadItem` interface

Le interfacce locali `TXReadItem` sono duplicate in 4 file (`TransactionDeleteModal`, `TransactionActionModal`, `BulkDeleteLinkedPairModal`, `FormModal`). Ora che esiste `types.ts` nella cartella transactions, verificare che tutti importino da lì. Se non lo fanno già, migrare.

---

## Step 8 — Verifiche post-migrazione

```bash
./dev.py lint-format frontend          # svelte-check 0 errors
./dev.py test front-transaction all    # 84+ E2E test
./dev.py test all-frontend             # full regression
```

Nessun test E2E cambia — l'interfaccia utente è identica, i `data-testid` invariati, i payload al backend semanticamente identici.

---

## Step 9 — Suite Vitest per funzioni pure (`txPayloadHelpers.test.ts`)

**File**: `frontend/src/lib/utils/__tests__/txPayloadHelpers.test.ts` (NUOVO)

### 9.1 — Fixture TypeRule

Record `TYPE_RULES` con tutti i 15 tipi (BUY, SELL, DIVIDEND, INTEREST, DEPOSIT, WITHDRAWAL, FEE, TAX, TRANSFER, FX_CONVERSION, CASH_TRANSFER, ADJUSTMENT + altri). Unico punto hardcoded, derivato dalla struttura backend.

### 9.2 — `applySignRules` (~12 casi)

- Parametrici: `it.each(Object.entries(TYPE_RULES))` → quantityRule rispettata
- Cash null → null
- qty=0 + sign negative → 0 (non -0)
- Combinazioni BUY (positive/negative) e SELL (negative/positive)

### 9.3 — `fieldEq` (~15 casi)

- quantity: formati diversi (`"0.1"` vs `"0.100000"`)
- cash: code+amount, null cases
- tags: order-independent, empty vs null
- description/cost_basis_override: normalizzazione vuoto
- asset_event_id: sentinel 0/null
- campo generico: strict equality

### 9.4 — `buildCreatePayload` (~10 casi)

- Per tipo: campi `forbidden` omessi
- Segni corretti per BUY, SELL, WITHDRAWAL, FEE
- `requiresPair=true` → `link_uuid` presente
- Campi opzionali vuoti omessi
- `eventLinkable=false` → no `asset_event_id`

### 9.5 — `buildUpdateDiff` (~12 casi)

- Zero diff → solo `{id}`
- Cambio tipo con type-swap (regole segno ricalcolate)
- Cambio singolo campo
- `asset_event_id` unlink → sentinel 0
- Campi non-PATCHABLE mai presenti
- cost_basis_override

### 9.6 — `diffDualItem` (~5 casi)

- Zero diff, cambio singolo, campi estranei ignorati

### 9.7 — `buildDualCreatePayloads` (~9 casi)

- **Layout fx**: qty=0 entrambi, cash segni opposti, currencies diverse, link_uuid condiviso
- **Layout transfer_asset**: qty segni opposti, no cash, asset condiviso
- **Layout transfer_cash**: cash segni opposti, stessa currency, broker diversi
- Tags/description condivisi
- cost_basis_override solo su TO

### 9.8 — `buildBatchPayload` (~10 casi)

- Array vuoto → `{}`
- Solo creates → `{creates:[…]}`
- Solo deletes → `{deletes:[…]}`
- Mix creates+updates+deletes
- Partner payloads inclusi nella lista corretta (partner create → pushato in creates; partner delete → pushato in deletes)
- Chiavi vuote omesse
- Splits e promotes pass-through

### 9.9 — Smoke test parametrico

```typescript
it.each(Object.entries(TYPE_RULES))('%s → buildCreatePayload no throw', (code, rule) => {
    const fields: TxFields = {
        type: code, broker_id: 1, date: '2024-01-01', quantity: '10',
        cash: {code: 'EUR', amount: '100'}, tags: [], description: '',
        cost_basis_override: null, asset_event_id: null, link_uuid: null,
    };
    expect(() => buildCreatePayload(fields, rule)).not.toThrow();
});
```

---

## Step 10 — Suite Vitest per `txCommitApi.ts`

**File**: `frontend/src/lib/utils/__tests__/txCommitApi.test.ts` (NUOVO)

Testa con mock di `zodiosApi`:

- `commitTransactions` con risposta `committed: true` → ritorna `CommitResult` con `committed=true`
- `commitTransactions` con risposta `committed: false, issues:[…]` → issues normalizzati
- `commitTransactions` con network error → issues con messaggio generico
- `commitTransactions` filtra `extra_forbidden` issues (li logga, non li ritorna)
- `validateTransactions` con 422 → estrae issues dalla risposta HTTP
- `validateTransactions` clean → `{committed: true, issues: []}`

~12 casi.

---

## Step 11 — Registrare vitest nel dev.py runner (se mancante)

Verificare che esista `./dev.py test unit-frontend`. Se non c'è, aggiungere runner in `scripts/test_runner/_frontend_unit.py` che esegue `npx vitest run`.

---

## Riepilogo file

| File | Azione | Step |
|------|--------|------|
| `frontend/src/lib/utils/saveWithRetry.ts` → `trySave.ts` | Rename file + funzione `saveWithRetry`→`trySave` + tipo `SaveWithRetryOptions`→`TrySaveOptions` | 0 |
| 7 file con import di `saveWithRetry` | Aggiorna import path e nome funzione | 0 |
| `frontend/src/lib/utils/txPayloadHelpers.ts` | +`TxDualSide`, +`buildDualCreatePayloads`, +`ResolvedOp`, +`buildBatchPayload` | 1 |
| `frontend/src/lib/utils/txCommitApi.ts` | NUOVO — `commitTransactions`, `validateTransactions` (usa `trySave`) | 2 |
| `frontend/src/lib/components/transactions/TransactionFormModal.svelte` | Semplifica `collectDualCreates`, `commit()`, `validateFn` | 3 |
| `frontend/src/lib/components/transactions/TransactionBulkModal.svelte` | +`resolveOps()`, semplifica commit/validate/getBulkContext | 4 |
| `frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte` | Usa `commitTransactions()` | 5 |
| `frontend/src/routes/(app)/transactions/+page.svelte` | 4 funzioni (delete, validate-delete, split, promote) → usano `commitTransactions`/`validateTransactions` | 6 |
| `frontend/src/lib/components/transactions/types.ts` | Consolidamento `TXReadItem` (se mancante) | 7 |
| `frontend/src/lib/utils/__tests__/txPayloadHelpers.test.ts` | NUOVO — ~70 test cases | 9 |
| `frontend/src/lib/utils/__tests__/txCommitApi.test.ts` | NUOVO — ~12 test cases | 10 |
| `scripts/test_runner/` | Runner vitest (se mancante) | 11 |

## Stima LOC

| Area | Delta |
|------|-------|
| `txPayloadHelpers.ts` | +90 |
| `txCommitApi.ts` | +60 (nuovo) |
| `TransactionFormModal.svelte` | −140 |
| `TransactionBulkModal.svelte` | −60 |
| `BulkDeleteLinkedPairModal.svelte` | −8 |
| `+page.svelte` | −40 |
| Test (2 file) | +500 |
| **Netto produzione** | −198 |
| **Netto totale (con test)** | +302 |

## Ordine esecuzione e dipendenze

```
Step 0 (rename) → Step 1 → Step 2 → Step 3-6 (paralleli) → Step 7 → Step 8 (verify) → Step 9-10 (test) → Step 11
```

Step 0 è preliminare (rename meccanico). Steps 3-6 sono indipendenti tra loro (migrano file diversi) ma dipendono tutti da Steps 1+2.

## Rischi

| Rischio | Prob. | Mitigazione |
|---------|-------|-------------|
| Regressione segni dual-create | Media | Tests parametrici layout × tipo + E2E `tx-paired-edit.spec.ts` |
| `txCommitApi` non gestisce edge-case 422 | Bassa | Mock test + E2E commit-failure tests |
| `resolveOps` in BulkModal non copre split/promote skip | Bassa | Logica copiata 1:1 dall'attuale `commit()` |
| Ordine ops nel payload diverge (creates before deletes) | Zero | `buildBatchPayload` preserva l'ordine backend (deletes → updates → creates) |
| Test E2E rotti | ~Zero | Interfaccia UI identica, solo interno |

---

## Note dalla verifica logica (2026-05-20)

1. **`commitOnSave=false` branch in FormModal** — quando il FormModal è wired dalla BulkModal, `commit()` non chiama l'API ma emette `onPushDraft(payload)`. Questo branch NON va toccato dalla migrazione (non usa `commitTransactions`). L'agente deve saltarlo.

2. **Splits/Promotes come input atomico** — ✅ RISOLTO. Sono input espliciti a `buildBatchPayload({ops, splits?, promotes?})`. `resolveOps()` riceve `splitTxIds`/`promoteTxIds` per applicare le regole di skip/strip type sugli edits. Il backend esegue atomicamente e il frontend assembla il payload completo in una volta.

3. **`commitTransactions` usa SEMPRE `trySave`** — ✅ RISOLTO. `trySave` (ex `saveWithRetry`, rinominato in Step 0) con default `{toast: false}`. Nessun side-effect per chi prima faceva raw try/catch — estrazione messaggi migliore gratis.

4. **Anti-bounce resta nei componenti** — la logica `lastDraftKey`/`lastCommitDraftKey`/`COMMIT_ANTI_BOUNCE_MS` è stato locale del UI component. NON va centralizzata in `txCommitApi.ts`.

---

Al termine del piano tornare a plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md 

---

## Post-implementazione (progresso incrementale)

### Step 0 — ✅ Completato (2026-05-20)

- File rinominati: `saveWithRetry.ts` → `trySave.ts`
- Funzione: `saveWithRetry` → `trySave`
- Tipo: `SaveWithRetryOptions` → `TrySaveOptions`
- **10 file aggiornati** (non 7 come stimato): i 3 extra sono `BrokerImportFilesModal.svelte`, `BrokerModal.svelte`, `BrokerSharingModal.svelte`, `CashTransactionModal.svelte`
- svelte-check: 0 errors, 1 warning pre-esistente (WacPreviewSection, non correlato)

### Step 1 — ✅ Completato (2026-05-20)

- Aggiunte in `txPayloadHelpers.ts`: `TxDualSide`, `PairFormLayout`, `buildDualCreatePayloads`, `ResolvedOp`, `buildBatchPayload`
- File passa da 196 → 392 LOC (+196)
- svelte-check: 0 errors

### Step 2 — ✅ Completato (2026-05-20)

- Creato `frontend/src/lib/utils/txCommitApi.ts` (137 LOC)
- Exports: `CommitResult`, `CommitOptions`, `TxValidationIssue`, `commitTransactions`, `validateTransactions`
- Usa `trySave` internamente, filtra `extra_forbidden`, normalizza risposta
- svelte-check: 0 errors


## Post-implementazione (2026-05-20)

### Steps 3-7 — Migrazione completata

- **Step 3 (FormModal)**: già migrato nella sessione precedente — usa `commitTransactions`, `validateTransactions`, `buildCreatePayload`, `buildDualCreatePayloads`
- **Step 4 (BulkModal)**: refactored con `resolveOps()` interna + `buildBatchPayload()` + `commitTransactions`/`validateTransactions`. Rimosso import di `trySave`/`extractValidationIssues` diretti
- **Step 5 (BulkDeleteLinkedPairModal)**: migrato a `commitTransactions()`, rimosso import `zodiosApi` diretto
- **Step 6 (+page.svelte)**: migrati `confirmDeleteModal`, `validateDeleteModal`, `confirmSplit`, `onPromoteMergeConfirm` a `commitTransactions`/`validateTransactions`
- **Step 7 (TXReadItem consolidation)**: arricchito `types.ts` con `cost_basis_override?: {code: string; amount: string} | string | null`, rimossa definizione duplicata da FormModal e BulkDeleteLinkedPairModal

### Fix aggiuntivo

- `DualDraftTo` interface in FormModal: aggiunto campo `quantity?: string` mancante (errore TS pre-esistente emerso dopo Step 3)

### Steps 9-11 — Testing

- **Step 9**: Creato `frontend/src/lib/utils/__tests__/txPayloadHelpers.test.ts` — 56 unit tests (parametrici con `it.each`)
- **Step 10**: Creato `frontend/src/lib/utils/__tests__/txCommitApi.test.ts` — 12 unit tests con mock di `trySave`
- **Step 11**: Registrato `tx-unit` in `scripts/test_runner/_frontend_transaction.py` → `./dev.py test front-transaction tx-unit`
- Totale vitest: 95 tests (4 files), tutti ✅

### Verifica finale

- `./dev.py front check`: 0 errors, 0 warnings
- `./dev.py test front-transaction all`: 14 PASSED, 0 FAILED (backend + Playwright)
- `npx vitest run`: 95 tests passed (4 files, 273ms)

> ⚠️ **NOTA**: La verifica finale sopra è da confermare manualmente dall'umano — possibili regressioni non coperte dai test automatici (edge-case UI, interazioni multi-modale, segni dual-create in scenari non testati).

### Status globale (2026-05-20)

**Steps 0-11**: ✅ COMPLETATI
**Step 12**: ✅ COMPLETATO (eliminazione `test.skip` condizionali — 0 skip rimasti)

### FIXME asset-event-delete — ✅ RISOLTO (2026-05-20)

**File**: `frontend/e2e/assets/asset-event-delete.spec.ts`

Il `test.fixme('delete unlinked event succeeds')` che assumeva un "Events tab" separato è stato riscritto per matchare l'UI attuale:
- Flusso: `asset-detail-editdata-btn` → `asset-detail-editor-panel` → `asset-editor-events-tab` → DataEditor rows → `data-action-id="delete"` → `asset-editor-save-btn`
- Aggiunto `data-testid="asset-editor-save-btn"` e `data-testid="asset-editor-cancel-btn"` a `AssetDataEditorSection.svelte`
- 4 scenari ora funzionanti: delete unlinked (Loan Milano), delete linked/RESTRICT (Apple), cascade check, event badge

### Fix tx-wac.spec.ts — ✅ RISOLTO (2026-05-20)

Tutti 7 test WAC fallivano per testid errati (generati in una sessione precedente senza verificare l'UI reale):
- `tx-new-btn` → `tx-add-button` (testid reale del pulsante "Add Transaction")
- `tx-type-option-${type}` → `search-select-option-${type}` (testid generico del SearchSelect)
- `selectType()` helper riscritto: apre il combobox SearchSelect, poi clicca l'opzione
- `goToTransactions()` allineato al pattern degli altri spec: `Promise.race` su `tx-table` / `tx-loading`
- `42.50` → `42.5` (normalizzazione `input[type="number"]`)

Risultato: 7/7 PASSED.

---

## Post-migrazione: Micro-improvements UX + Test Coverage (2026-05-21)

### Toast commit con elenco puntato + emoji

**File**: `frontend/src/routes/(app)/transactions/+page.svelte` (`handleBulkCommitted`)

Formato precedente: `✅ Salvate 9 transazioni (6 create, 2 aggiornate, 1 eliminate)`

Formato nuovo (multilinea con `whitespace-pre-line`):
```
✅ Salvate 9 transazioni
• ➕ 6 create
• ✏️ 2 aggiornate
• 🗑️ 1 eliminate
```

Emoji per ogni stato: `➕ create`, `✏️ updated`, `🗑️ deleted`, `✂️ split`, `🔗 promoted`.

### Sign coloring (bordo qty + cash)

**Helper condiviso**: `frontend/src/lib/utils/signHintColor.ts` (NUOVO, 44 LOC)
- Esporta `computeSignHint(value: number, rule: SignRule): {ok, bad}`
- Copre tutte le regole backend: `positive`, `negative`, `nonzero`, `zero`, `any`/`free`
- Ragiona sul valore POST auto-flip (utente entra positivo → sistema nega → finale = negativo = OK per `'negative'`)

**Qty (FormModal)**: 3 istanze → `style:border-color={qtyBorderColor || undefined}`
- Verde oklch `0.765 0.177 163.223 / 0.7` quando conforme
- Rosso oklch `0.637 0.237 25.331 / 0.7` quando viola
- Nessuno style quando neutro (NaN, rule='any')

**Cash (CompactCashCell)**: refactored da ~20 LOC switch/case a 5 LOC con `computeSignHint()` — funzionalità invariata, ora copre anche `nonzero` e `zero`.

### Test E2E aggiunti (transactions-modals.spec.ts)

| Test | ID | Scenario | Verifiche |
|------|----|----------|-----------|
| T12a | Sign coloring BUY | qty neg → red, pos → green | `el.style.borderColor` contiene hue oklch |
| T12b | Sign coloring SELL | pos → green (auto-flip), neg → red | Attende `(−)` label come signal type rules loaded |
| T13 | BulkModal validate | ADJUSTMENT + asset + qty → Apply → workspace → validate | Issues banner con testo non vuoto OPPURE valid badge ✓ |

### Note tecniche

- **Tailwind v4 + classi dinamiche**: le classi interpolate `{variabile}` NON vengono generate dal JIT. Soluzione: `style:border-color` inline (Svelte applica via CSSOM, non come attributo HTML).
- **Type rules async**: il form usa la fallback rule (`quantityRule:'free'`) fino a quando il server risponde. Test devono attendere il label `(+)/(−)` come proxy per "rules loaded".
- **Frontend build stale**: i test E2E usano il build statico servito da FastAPI — dopo modifiche svelte serve `./dev.py front build` prima dei test.

### Verifica finale (2026-05-21)

- `svelte-check`: 0 errors, 0 warnings
- `transactions-modals.spec.ts`: 17/17 PASSED (14 pre-esistenti + 3 nuovi)
- `./dev.py test front-transaction all`: 15/15 PASSED
- `grep -rn "test.skip\|test.fixme" frontend/e2e/ | grep -v gallery`: **0 risultati**

---

## Step 12 — Eliminazione `test.skip` condizionali dai test E2E

**Date**: 2026-05-20
**Status**: ⏳ IN PIANO
**Rationale**: Il `populate_mock_data.py` gira sempre prima dei test E2E (via global-setup). Tutti i dati necessari **devono** esistere. I `test.skip` condizionali mascherano problemi reali (dati mancanti = bug nel seeding, UI non renderizzata = bug FE). Vanno eliminati: se il dato manca → aggiungere al mock; se il componente non renderizza → test deve fallire.

### Inventario skip (69 occorrenze in ~10 file)

| File | Skip count | Categoria prevalente |
|------|-----------|---------------------|
| `tx-picker-pagination.spec.ts` | 15 | UI component non visibile |
| `tx-split-promote.spec.ts` | 7 | Dati paired/tagged non trovati |
| `transactions-modals.spec.ts` | 7 | Dati mancanti + UI |
| `transactions-table.spec.ts` | 4 | Linked pairs non trovati |
| `tx-bulk-suggest-ux.spec.ts` | 1 | Split button non visibile |
| `tx-delete.spec.ts` | 4 | Righe non trovate (paginazione) |
| `tx-crud-full.spec.ts` | 1 | Test placeholder vuoto |
| `utilities.spec.ts` | 2 | FX/Assets non disponibili |

### Strategia per categoria

| Categoria | Azione | N. skip |
|-----------|--------|---------|
| **Paginazione** (riga non in pagina 1) | Navigare con `?page_size=200` | ~6 |
| **Dati garantiti** (linked pairs, tags, TX, brokers, FX, assets) | `expect(x).toBeTruthy()` hard fail — se manca → fix mock | ~35 |
| **UI component** (BulkModal, Picker, PageSize selector) | `await expect(x).toBeVisible()` hard fail — se non renderizza → bug FE | ~20 |
| **Test placeholder** (corpo vuoto) | Completare con assertions reali o eliminare se coperto altrove | ~2 |
| **Access-level fallback** (split non visibile su VIEWER row) | Usare riga con accesso OWNER/EDITOR garantito dal mock | ~6 |

### Ordine esecuzione

```
12.1  utilities.spec.ts (2 skip — più semplice, warm-up)
12.2  transactions-table.spec.ts (4 skip)
12.3  transactions-modals.spec.ts (7 skip)
12.4  tx-delete.spec.ts (4 skip — 2 già fixati con page_size=200)
12.5  tx-crud-full.spec.ts (1 skip — placeholder)
12.6  tx-split-promote.spec.ts (7 skip)
12.7  tx-bulk-suggest-ux.spec.ts (1 skip)
12.8  tx-picker-pagination.spec.ts (15 skip — più complesso)
12.9  Run finale: ./dev.py test all-frontend (0 skip, 0 fail)
```

### Per ogni file (workflow)

1. Leggere i `test.skip` → capire il dato richiesto
2. Verificare che `populate_mock_data.py` lo crea (grep la descrizione/tag)
3. Se manca → aggiungere al mock + `./dev.py db create-clean --test`
4. Sostituire `test.skip(!x, msg)` → `expect(x, msg + ' — check populate_mock_data.py').toBeTruthy()`
5. Se è un UI component → `await expect(x).toBeVisible({timeout: N})`
6. Eseguire `npx playwright test <file> --project desktop` → verificare 0 skip, 0 fail
7. Next file

### Dati mock potenzialmente da aggiungere

| Dato | Usato da | Presente oggi? |
|------|----------|---------------|
| Linked pairs visibili in pagina 1 | `transactions-table.spec.ts` TT2/TT3/TT9 | ✅ Sì (Asym-a/b/c/d + delete-safe) |
| Tagged transactions | `transactions-table.spec.ts` TT11 | ✅ Sì (access-test, delete-safe, promote-test) |
| ≥21 TX non-paired per picker pagination | `tx-picker-pagination.spec.ts` P1 | ✅ Probabile (mock ha ~80 TX) |
| FX pairs configurati | `utilities.spec.ts` | ✅ Sì (EUR/USD, EUR/CHF, etc.) |
| Assets configurati | `utilities.spec.ts` | ✅ Sì (Apple, Bitcoin, etc.) |
| promote-test WITHDRAWAL+DEPOSIT rows | `tx-split-promote.spec.ts` | ✅ Sì (TX #{W,D} taggati `promote-test`) |
| Delete-safe paired TX con accesso EDITOR+ | `tx-split-promote.spec.ts` C3 | ✅ Sì (ETH Coinbase↔IB) |

### Rischi

| Rischio | Mitigazione |
|---------|-------------|
| Test fragili dopo rimozione skip (race condition UI) | Usare timeout ragionevoli (non 500ms, ma 3-5s per modali) |
| Ordine distruttivo (test precedente elimina riga usata dopo) | Verificare che test distruttivi usino SOLO righe `delete-safe`; test di lettura usino righe diverse |
| Mock data cresce troppo | Ogni aggiunta è tagged e documentata — nessun dato "generico" |

### Definizione di done

- `grep -rn "test.skip" frontend/e2e/ | wc -l` → **0**
- `./dev.py test all-frontend` → tutti PASSED, **0 skipped**
- PR con messaggio: `test(e2e): remove all conditional test.skip — hard-fail on missing data`

