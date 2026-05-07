# Plan — Phase 07 · Part 4 · Round 6 — Piano B23: Bulk Delete via BulkModal + DeleteModal Polish

**Date**: 2026-05-07
**Status**: ⏳ DRAFT
**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md) (Step 7 + 9)
**Previous iteration**: [`plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2.prompt.md)

---

## TL;DR

Eliminare `BulkDeleteLinkedPairModal` — la delete multipla avviene direttamente nella `TransactionBulkModal` con righe pre-marcate `status: 'delete'`. L'utente può usare tutte le funzionalità della bulk (restore, edit, clone, add) dallo stesso batch atomico. Fix bug `committed:false` nel `TransactionDeleteModal` singolo, polish UI (ordine righe, tag colorati, icona asset, description), guard nel `PickerModal` per righe non-editabili, conferma "edit su riga delete", mock data per test, E2E suite.

---

## Steps

### Step 1 — Rimuovere `BulkDeleteLinkedPairModal` e relativo wiring (~30min)

**Eliminare**: [`BulkDeleteLinkedPairModal.svelte`](frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte)

**Modificare** [+page.svelte](frontend/src/routes/(app)/transactions/+page.svelte):
- Rimuovere tutto lo state dedicato: `bulkDeleteOpen`, `bulkDeleteClean`, `bulkDeleteProblems`, `simpleDeleteOpen`, `simpleDeleteRows`, `simpleDeleting`, `confirmSimpleDelete()`, `handleBulkDeleteCommitted()` (L.509-603)
- Rimuovere il rendering di `<BulkDeleteLinkedPairModal>` e `<ConfirmModal>` simpleDelete dal template
- Rimuovere l'import di `BulkDeleteLinkedPairModal` e del tipo `ProblemPair`

**i18n**: le chiavi `transactions.bulkDelete.*` in [en.json](frontend/src/lib/i18n/en.json) (L.618-638) possono essere rimosse (erano usate solo da questo componente)

---

### Step 2 — Riscrivere `onBulkDelete()` → apre BulkModal con `initialStatus: 'delete'` (~1h)

**File**: [+page.svelte](frontend/src/routes/(app)/transactions/+page.svelte)

Riscrivere `onBulkDelete()` (L.517) con la stessa logica di `onEditBulk()`:
1. Raccogliere `selectedRows`
2. Auto-include partner paired mancanti: per ogni riga con `related_transaction_id != null`, se il partner non è nella selezione, cercarlo in `partnerRows` / `mainRows` / fetch batch API
3. Settare `bulkMode = 'edit-many'`, `bulkInitial = [...allRows]`
4. Settare un nuovo stato `bulkInitialStatus = 'delete' as const`
5. Aprire `bulkOpen = true`

**Aggiungere prop** `initialStatus?: 'delete'` a `<TransactionBulkModal>` nel template.

---

### Step 3 — `TransactionBulkModal`: supporto `initialStatus: 'delete'` (~1h)

**File**: [TransactionBulkModal.svelte](frontend/src/lib/components/transactions/TransactionBulkModal.svelte)

**3a.** Aggiungere prop `initialStatus?: 'delete'` nell'interfaccia `Props` (L.129).

**3b.** Modificare `fromTx()` (L.183): accettare un parametro opzionale `overrideStatus?: 'delete'`. Quando presente e `mode === 'edit-many'`, settare `status: 'delete'` anziché `'original'`.

**3c.** Modificare l'`$effect` di init (L.239): passare `initialStatus` a `fromTx()` nel `rows.map()`:
```ts
const next = rows.map(r => fromTx(r, m, initialStatus));
```

**3d.** `mergePairedRows()` (L.429): quando il giver è `status: 'delete'`, anche il partner nascosto deve ereditare `status: 'delete'` — così la coppia intera è marcata.

**3e.** Aggiungere `InfoBanner` split hint: quando ci sono righe paired con `status: 'delete'` nella griglia, mostrare un banner informativo variant `info`:
> "Per eliminare solo un lato di una coppia collegata, prima esegui lo Split per scollegarle."

Usare la chiave i18n `transactions.deleteModal.splitHint` già esistente (L.719 en.json).

---

### Step 4 — Conferma "Edit su riga marcata delete" (~45min)

**File**: [TransactionBulkModal.svelte](frontend/src/lib/components/transactions/TransactionBulkModal.svelte)

Quando l'utente clicca l'azione "✏ Edit" (o doppio-click) su una riga con `status === 'delete'`:

**4a.** Non aprire subito la FormModal. Mostrare una `ConfirmModal` con variant `warning` (gialla):
- Titolo: "Transaction marked for deletion"
- Messaggio: "This transaction is marked for deletion. Do you want to restore it and edit it instead?"
- Pulsante conferma: "Restore & Edit" (giallo/amber)
- Pulsante cancel: "Cancel" (neutro)

**4b.** Su conferma: cambiare `status` da `'delete'` a `'original'` (il draft non ha modifiche → resta `original`, le eventuali modifiche nella FormModal lo porteranno a `'edited'`). Poi aprire la FormModal normalmente.

**4c.** Su cancel: non fare nulla, la riga resta `delete`.

**4d.** i18n: aggiungere chiavi `transactions.bulk.confirmEditDelete`, `transactions.bulk.confirmEditDeleteMessage`, `transactions.bulk.restoreAndEdit` in 4 lingue.

**4e.** La `visible` dell'azione `edit-single` (L.1103) va cambiata: rimuovere `row.status !== 'delete'` — l'azione edit deve essere visibile anche sulle righe delete (ma passerà per la conferma). Analogamente per `clone` (L.1110): se si clona una riga delete, clonare come `status: 'new'` (già il comportamento attuale di `cloneRow`).

**4f.** L'azione `reset` (L.1130, icona `↺`): sulla riga in stato `delete`, il reset deve riportare a `'original'` (undo della marcatura delete). L'azione deve essere visibile anche per righe `delete` → rimuovere il check `row.status !== 'delete'` dalla `visible` (L.1134).

---

### Step 5 — `TransactionDeleteModal`: fix bug `committed:false` + toast success (~1.5h)

**File**: [+page.svelte](frontend/src/routes/(app)/transactions/+page.svelte) `confirmDeleteModal()` (L.790), [TransactionDeleteModal.svelte](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**5a.** In `confirmDeleteModal()`: parsificare la risposta completa `{committed, issues, results}`. Quando `committed === false`:
- Non chiudere la modale
- Passare `issues[].error` al `TransactionDeleteModal` via un nuovo prop `errors: string[]`

**5b.** In `TransactionDeleteModal.svelte`: aggiungere prop `errors: string[]` (default `[]`). Quando non vuoto, mostrare un banner rosso (stile identico a `BulkDeleteLinkedPairModal` L.227-237) con icona `AlertTriangle` e lista errori. Aggiungere pulsante "Validate" sotto il banner che riesegue la commit (re-try).

**5c.** Quando `committed === true`: mostrare un toast success con dati della TX cached:
- Standalone: `"Deleted: {type} {asset} on {broker} ({date})"`
- Paired: `"Deleted paired: {type} {asset} from {broker_from} to {broker_to}"`
- Usare `getAssetInfo()`, `getBrokerInfo()`, `$t('transactions.types.{type}')` per popolare

**5d.** i18n: aggiungere chiavi `transactions.deleteModal.toastSuccess`, `transactions.deleteModal.toastPairedSuccess`, `transactions.deleteModal.toastError` in 4 lingue.

---

### Step 6 — `TransactionDeleteModal`: UI polish (~1h)

**File**: [TransactionDeleteModal.svelte](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**6a.** Riordinare righe Layout A (L.112-136): Data → Tipo → Qty → Cash → Asset → Broker → Tags → Description (coerente con colonne tabella principale).

**6b.** Tag colorati: sostituire `bg-gray-100 dark:bg-gray-700` (L.130) con `style={getStringBadgeStyle(tag)}` importato da [`colors.ts`](frontend/src/lib/utils/colors.ts).

**6c.** Asset con icona: nella riga asset, mostrare `<img>` con `getAssetInfo(id)?.icon_url` o fallback `getAssetTypeIconUrl(assetType)` prima del nome. Applicare sia a Layout A che Layout B.

**6d.** Aggiungere riga Description: dopo Tags, se `transaction.description` è non-vuoto, mostrare una riga con troncamento e tooltip.

---

### Step 7 — BulkModal UI polish: icone toolbar + posizione Cerca (~30min)

**File**: [TransactionBulkModal.svelte](frontend/src/lib/components/transactions/TransactionBulkModal.svelte)

**7a.** Icona `Undo2` su pulsante "Reimposta tutto" (L.1520): aggiungere `<Undo2 size={12} />` prima del testo. `Undo2` è già importata (L.19 — verifica; se manca, aggiungere import).

**7b.** Spostare "🔍 Cerca e aggiungi" a **sinistra** nella toolbar (L.1514-1517): fuori dal container `ml-auto flex-row-reverse`, posizionarlo all'inizio (slot sinistro). La ricerca è un'azione primaria.

**7c.** Icon reset riga: sostituire `() => '↺'` (L.1131) con l'import `Undo2` per coerenza con il reset globale.

---

### Step 8 — PickerModal: guard righe non-editabili + dblclick/long-press (~2h)

**File**: [TransactionPickerModal.svelte](frontend/src/lib/components/transactions/TransactionPickerModal.svelte), [TransactionsTable.svelte](frontend/src/lib/components/transactions/TransactionsTable.svelte), [DataTable.svelte](frontend/src/lib/components/table/DataTable.svelte)

**8a.** `TransactionPickerModal`: calcolare `disabledIds: Set<number>` dal parent:
- Righe standalone su broker VIEWER o senza ruolo (null) → disabled
- Righe paired il cui partner è su broker non-editabile → disabled (entrambe le metà)
- Usare `canEditBroker(brokerId)` dallo store

**8b.** `TransactionsTable` / `DataTable`: passare `disabledRowIds` prop. Per le righe disabled:
- Checkbox sostituita da icona ⊘ rossa (`Ban` da lucide o `CircleX`)
- Hover → [`Tooltip`](frontend/src/lib/components/ui/Tooltip.svelte) "Editor access required on broker {brokerName}"
- "Select all" header skip le righe disabled

**8c.** Row dblclick desktop: `onRowDoubleClick` handler che toggle la selezione. Nel PickerModal, il dblclick su riga abilitata → toggle checkbox.

**8d.** Long-press mobile: `touchstart`/`touchend` handler con timer 500ms. `touchmove` cancella il timer (non interferisce con scroll). Al trigger → `toggleSelection(rowId)`. **Non** usare il `contextmenu` nativo (quello apre il ContextMenu, non seleziona).

---

### Step 9 — Mock data: TX deletable in `populate_mock_data.py` (~30min)

**File**: `backend/app/db/populate_mock_data.py`

**9a.** Aggiungere 2 TX standalone con tag `delete-safe` su broker editabili (IB, Directa):
- 1× `DEPOSIT` con cash positivo, senza asset → eliminabile senza impatto balance
- 1× `FEE` con cash negativo piccolo → eliminabile senza impatto

**9b.** Aggiungere 1 coppia paired `TRANSFER` con tag `delete-safe` su broker editabili (IB↔Coinbase):
- Asset con balance sufficiente (o asset dedicato con solo questa TX, così eliminare non causa negativi)

---

### Step 10 — E2E test suite `tx-delete.spec.ts` (~2h)

**Nuovo file**: `frontend/e2e/transactions/tx-delete.spec.ts`

**10a.** Layout A standalone: apre DeleteModal → verifica campi (data, tipo, qty, cash, asset con icona, broker, tags colorati, description) → cancel → reopen → confirm → riga scompare → toast success

**10b.** Layout B paired: apre DeleteModal → verifica From/To con icone asset → confirm → entrambe scompaiono → toast success paired

**10c.** Layout C guard: verifica 🗑 nascosto su righe viewer/hidden

**10d.** Bulk delete via BulkModal: selezione 2+ righe → 🗑 toolbar → BulkModal si apre con righe pre-delete (sfondo rosso barrato) → restore 1 riga → commit → righe delete scompaiono, riga restored resta

**10e.** Banner errore su delete fallita (balance negativo): tentare delete di TX che causa balance negativo → banner rosso nella DeleteModal con messaggio errore

**10f.** PickerModal: verifica righe VIEWER disabilitate (icona ⊘ rossa, tooltip), select-all le salta, dblclick su riga abilitata la seleziona

---

### Step 11 — i18n: nuove chiavi in 4 lingue (~30min)

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Prima eseguire `./dev.py i18n search` per verificare chiavi riutilizzabili.

Chiavi nuove:
- `transactions.deleteModal.toastSuccess` — "Deleted: {type} {asset} on {broker}"
- `transactions.deleteModal.toastPairedSuccess` — "Deleted paired: {type} {asset} {brokerFrom} → {brokerTo}"
- `transactions.deleteModal.toastError` — "Delete failed"
- `transactions.bulk.confirmEditDelete` — "Transaction marked for deletion"
- `transactions.bulk.confirmEditDeleteMessage` — "This transaction is marked for deletion. Do you want to restore it and edit it instead?"
- `transactions.bulk.restoreAndEdit` — "Restore & Edit"
- `transactions.picker.disabledTooltip` — "Editor access required on broker {broker}"

---

### Step 12 — Nota forward-link nel piano C (Split/Promote) (~5min)

**File**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](LibreFolio_developer_journal/RoadmapV4_UI/plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md)

Aggiungere nella sezione "Piani di dettaglio" (L.738-744), sotto la riga Piano C, una nota:

> **Nota Piano C**: Quando si implementa Split, aggiungere nella `TransactionBulkModal` un'azione riga "✂ Split" visibile solo su righe paired. L'azione chiama `POST /transactions/split` e aggiorna il batch in-place (le due metà diventano standalone). Questo completa il flusso "elimina solo un lato" suggerito dall'InfoBanner di Step 3e.

---

## Dipendenze e ordine

```
Step 1 (rimuovi BulkDeleteModal)  ← primo
Step 2 (riscrivere onBulkDelete)  ← DIPENDE da Step 1
Step 3 (BulkModal initialStatus)  ← DIPENDE da Step 2
Step 4 (conferma edit su delete)  ← DIPENDE da Step 3
Step 5 (fix committed:false)      ← indipendente
Step 6 (DeleteModal polish)       ← indipendente
Step 7 (BulkModal toolbar polish) ← indipendente
Step 8 (PickerModal guard)        ← indipendente
Step 9 (mock data)                ← prima di Step 10
Step 10 (E2E test)                ← DIPENDE da tutti gli altri
Step 11 (i18n)                    ← necessario per Step 4, 5, 8
Step 12 (nota Piano C)            ← indipendente, 5 min
```

**Ordine consigliato**: 11 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 12 → 10

**Stima totale**: ~11-12h

---

## Considerazioni

1. **Single-row delete → manteniamo TransactionDeleteModal**: per la delete singola (1 o 2 righe paired) la modale leggera dedicata è più diretta e non richiede la complessità della DataTable. La BulkModal si usa solo per la multi-selezione.

2. **Split non ancora implementato**: l'info box nella BulkModal suggerisce lo split, ma il pulsante/azione non esiste ancora. Il Piano C (Step 10-12 del piano padre) lo implementerà. Per ora basta il testo informativo.

3. **PickerModal guard + dblclick/long-press**: indipendenti dal refactor delete, procedere come pianificato.

