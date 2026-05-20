# Plan: Centralizzazione Payload + API Commit/Validate — Creazione, Migrazione, Test

**Date**: 2026-05-20
**Status**: ⏳ DA ESEGUIRE
**Link back**: [`plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanD2_round2_plan-R2-SP-C-BugfixRound2-WacPreview.prompt.md) (riga 762)

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

