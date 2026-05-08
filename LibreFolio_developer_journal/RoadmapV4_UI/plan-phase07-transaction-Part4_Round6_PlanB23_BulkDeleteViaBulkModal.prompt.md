# Plan — Phase 07 · Part 4 · Round 6 — Piano B23: Bulk Delete via BulkModal + DeleteModal Polish

**Date**: 2026-05-07
**Status**: ✅ COMPLETED
**Parent**: [`plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md`](./plan-phase07-transaction-Part4_Round6_ContextMenuDeletePolish.prompt.md) (Step 7 + 9)
**Previous iteration**: [`plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB_TestWalkPhase2.prompt.md)

---

## TL;DR

Eliminare `BulkDeleteLinkedPairModal` — la delete multipla avviene direttamente nella `TransactionBulkModal` con righe pre-marcate `status: 'delete'`. L'utente può usare tutte le funzionalità della bulk (restore, edit, clone, add) dallo stesso batch atomico. Fix bug `committed:false` nel `TransactionDeleteModal` singolo, polish UI (ordine righe, tag colorati, icona asset, description), guard nel `PickerModal` per righe non-editabili, conferma "edit su riga delete", mock data per test, E2E suite.

---

## Steps

### Step 1 — Rimuovere `BulkDeleteLinkedPairModal` e relativo wiring ✅ (~30min)

**Eliminare**: [`BulkDeleteLinkedPairModal.svelte`](frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte)

**Modificare** [+page.svelte](frontend/src/routes/(app)/transactions/+page.svelte):
- Rimuovere tutto lo state dedicato: `bulkDeleteOpen`, `bulkDeleteClean`, `bulkDeleteProblems`, `simpleDeleteOpen`, `simpleDeleteRows`, `simpleDeleting`, `confirmSimpleDelete()`, `handleBulkDeleteCommitted()` (L.509-603)
- Rimuovere il rendering di `<BulkDeleteLinkedPairModal>` e `<ConfirmModal>` simpleDelete dal template
- Rimuovere l'import di `BulkDeleteLinkedPairModal` e del tipo `ProblemPair`

**i18n**: le chiavi `transactions.bulkDelete.*` in [en.json](frontend/src/lib/i18n/en.json) (L.618-638) possono essere rimosse (erano usate solo da questo componente)

---

### Step 2 — Riscrivere `onBulkDelete()` → apre BulkModal con `initialStatus: 'delete'` ✅ (~1h)

**File**: [+page.svelte](frontend/src/routes/(app)/transactions/+page.svelte)

Riscrivere `onBulkDelete()` (L.517) con la stessa logica di `onEditBulk()`:
1. Raccogliere `selectedRows`
2. Auto-include partner paired mancanti: per ogni riga con `related_transaction_id != null`, se il partner non è nella selezione, cercarlo in `partnerRows` / `mainRows` / fetch batch API
3. Settare `bulkMode = 'edit-many'`, `bulkInitial = [...allRows]`
4. Settare un nuovo stato `bulkInitialStatus = 'delete' as const`
5. Aprire `bulkOpen = true`

**Aggiungere prop** `initialStatus?: 'delete'` a `<TransactionBulkModal>` nel template.

---

### Step 3 — `TransactionBulkModal`: supporto `initialStatus: 'delete'` ✅ (~1h)

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

### Step 4 — Conferma "Edit su riga marcata delete" ✅ (~45min)

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

### Step 5 — `TransactionDeleteModal`: fix bug `committed:false` + toast success ✅ (~1.5h)

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

### Step 6 — `TransactionDeleteModal`: UI polish ✅ (~1h)

**File**: [TransactionDeleteModal.svelte](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**6a.** Riordinare righe Layout A (L.112-136): Data → Tipo → Qty → Cash → Asset → Broker → Tags → Description (coerente con colonne tabella principale).

**6b.** Tag colorati: sostituire `bg-gray-100 dark:bg-gray-700` (L.130) con `style={getStringBadgeStyle(tag)}` importato da [`colors.ts`](frontend/src/lib/utils/colors.ts).

**6c.** Asset con icona: nella riga asset, mostrare `<img>` con `getAssetInfo(id)?.icon_url` o fallback `getAssetTypeIconUrl(assetType)` prima del nome. Applicare sia a Layout A che Layout B.

**6d.** Aggiungere riga Description: dopo Tags, se `transaction.description` è non-vuoto, mostrare una riga con troncamento e tooltip.

---

### Step 7 — BulkModal UI polish: icone toolbar + posizione Cerca ✅ (~30min)

**File**: [TransactionBulkModal.svelte](frontend/src/lib/components/transactions/TransactionBulkModal.svelte)

**7a.** Icona `Undo2` su pulsante "Reimposta tutto" (L.1520): aggiungere `<Undo2 size={12} />` prima del testo. `Undo2` è già importata (L.19 — verifica; se manca, aggiungere import).

**7b.** Spostare "🔍 Cerca e aggiungi" a **sinistra** nella toolbar (L.1514-1517): fuori dal container `ml-auto flex-row-reverse`, posizionarlo all'inizio (slot sinistro). La ricerca è un'azione primaria.

**7c.** Icon reset riga: sostituire `() => '↺'` (L.1131) con l'import `Undo2` per coerenza con il reset globale.

---

### Step 8 — PickerModal: guard righe non-editabili + dblclick/long-press ✅ (~2h)

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

### Step 9 — Mock data: TX deletable in `populate_mock_data.py` ✅ (~30min)

**File**: `backend/app/db/populate_mock_data.py`

**9a.** Aggiungere 2 TX standalone con tag `delete-safe` su broker editabili (IB, Directa):
- 1× `DEPOSIT` con cash positivo, senza asset → eliminabile senza impatto balance
- 1× `FEE` con cash negativo piccolo → eliminabile senza impatto

**9b.** Aggiungere 1 coppia paired `TRANSFER` con tag `delete-safe` su broker editabili (IB↔Coinbase):
- Asset con balance sufficiente (o asset dedicato con solo questa TX, così eliminare non causa negativi)

---

### Step 10 — E2E test suite `tx-delete.spec.ts` ✅ (~2h)

**Nuovo file**: `frontend/e2e/transactions/tx-delete.spec.ts`

**10a.** Layout A standalone: apre DeleteModal → verifica campi (data, tipo, qty, cash, asset con icona, broker, tags colorati, description) → cancel → reopen → confirm → riga scompare → toast success

**10b.** Layout B paired: apre DeleteModal → verifica From/To con icone asset → confirm → entrambe scompaiono → toast success paired

**10c.** Layout C guard: verifica 🗑 nascosto su righe viewer/hidden

**10d.** Bulk delete via BulkModal: selezione 2+ righe → 🗑 toolbar → BulkModal si apre con righe pre-delete (sfondo rosso barrato) → restore 1 riga → commit → righe delete scompaiono, riga restored resta

**10e.** Banner errore su delete fallita (balance negativo): tentare delete di TX che causa balance negativo → banner rosso nella DeleteModal con messaggio errore

**10f.** PickerModal: verifica righe VIEWER disabilitate (icona ⊘ rossa, tooltip), select-all le salta, dblclick su riga abilitata la seleziona

---

### Step 11 — i18n: nuove chiavi in 4 lingue ✅ (~30min)

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

### Step 12 — Nota forward-link nel piano C (Split/Promote) ✅ (~5min)

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

---

## Post-completion polish (from TestWalk feedback)

Appunti estetici emersi dal test umano post-implementazione, corretti in-place:

### P1 — Toast success arricchito (standalone + paired)
- Toast non più plain text → HTML con icona tipo transazione, icona broker, nome broker **bold**, SVG ruolo accesso (corona OWNER / matita EDITOR)
- Usa `getTransactionTypeIconUrl()`, `getBrokerIconUrlById()`, `getRoleSvgHtml()` per comporre il messaggio
- Paired toast: `"{typeIcon}TypeName AssetName {brokerIconA}BrokerA{roleA} → {brokerIconB}BrokerB{roleB}"`

### P2 — Error banner con resolveIssueMessage
- L'error banner nella DeleteModal ora usa `resolveIssueMessage()` (stessa logica di BulkModal/FormModal)
- Gli ID di asset e broker vengono risolti in nomi con icone: `"Asset 1 quantity goes negative..."` → icona Apple + "Apple Inc. quantity goes negative -5 📉 on 2026-04-25 for {brokerIcon}Interactive Brokers{roleIcon}"`
- Banner spostato SOPRA i dettagli (dopo il titolo), coerente con BulkModal

### P3 — Validate now + segnale verde
- Aggiunto pulsante "⚡ Validate now" nel footer sinistro della DeleteModal (come in BulkModal)
- Chiama `POST /transactions/validate` con `{deletes: [...ids]}`
- Se validazione ok → banner verde "✓ This transaction can be deleted safely."
- Se errori → banner rosso con messaggi risolti (P2)
- i18n chiave `transactions.deleteModal.canBeDeleted` in 4 lingue

---

## Follow-up: Rimuovere `mode` dalla TransactionBulkModal

**Status**: ✅ COMPLETED (2026-05-07)
**Trigger**: emerso dall'osservazione che la BulkModal è ormai una modale unica create+edit+delete, il `mode: 'create-many' | 'edit-many'` è ridondante.

### Analisi dello stato attuale

La prop `mode` impatta **6 punti** nel codice della BulkModal:

| # | Dove | Effetto |
|---|------|---------|
| 1 | `fromTx()` L185 | `create-many` → `status='new'`, id strippato, date=today, link_uuid rigenerato. `edit-many` → `status='original'`, preserva id/date |
| 2 | `$effect` open L261 | `mergePairedRows()` eseguito solo in `edit-many` |
| 3 | `$effect` open L279 | Auto-open FormModal vuoto solo in `create-many` con 0 righe |
| 4 | `resetRow`/`resetAll` L543-549 | Passa `mode` a `fromTx()` per sapere come resettare |
| 5 | `editMode` L804 | Derivato da `mode === 'edit-many'` ma **mai usato** nel template (dead code) |
| 6 | Toolbar L1570 | "🔍 Search & add" picker visibile solo in `edit-many` |

Nel parent (`+page.svelte`) ci sono **8 punti** che settano `bulkMode`.

### Osservazione chiave

La distinzione `create-many` vs `edit-many` è **già implicita nelle righe stesse**:
- Se `initialRow.id > 0` → è una riga DB esistente (edit)
- Se `initialRow.id === 0` o assente → è un template/clone (create)

Il commit **non usa mai `mode`** — distingue per `status` (`new`→CREATE, `edited`→UPDATE, `delete`→DELETE). Il `mode` quindi è un'astrazione che non corrisponde più a ciò che fa la modale.

### Pro della rimozione ✅

| Aspetto | Beneficio |
|---------|-----------|
| **API semplificata** | 1 prop in meno nella BulkModal, meno stato nel parent (eliminare `bulkMode` e le 8 assegnazioni) |
| **Batch misti nativi** | Oggi se apri in `edit-many` e aggiungi righe nuove con "+ Add row", le nuove righe sono `status='new'` indipendentemente dal `mode` — il `mode` è già incoerente per le righe inserite dopo l'apertura |
| **Meno branching** | `fromTx()` non cede più il parametro `m`, l'`$effect` di init si semplifica |
| **Dead code rimosso** | `editMode` (L804) eliminato |
| **Coerenza concettuale** | La modale gestisce batch misti (new + edit + delete in uno stream) ma ha un "mode" che dice "sei in create o edit" — contraddizione filosofica risolta |
| **PickerModal** | Visibilità basata su `allMainRows.length > 0` (condizione già presente L1570), non serve `mode` |
| **Manutenibilità** | Ogni futuro sviluppo non deve più chiedersi "questo deve funzionare solo in create-many o anche in edit-many?" |

### Contro / Rischi della rimozione ⚠️

| Rischio | Gravità | Mitigazione |
|---------|---------|-------------|
| **Regressione sul clone** | 🟢 Bassa | Il parent già setta `id: 0` e `date: today` nelle righe clonate — `fromTx` le tratterebbe come nuove anche senza `mode` |
| **`resetAll` ambiguo** | 🟢 Bassa | `resetAll` ha senso solo su righe con `original` (edit) — la condizione era già presente: `d.original ? fromTx(d.original, mode) : d`. Senza `mode`, diventa `d.original ? fromTx(d.original) : d` con flag inferito da `d.original.id > 0` |
| **Auto-open FormModal vuoto** | 🟢 Bassa | Oggi triggerato da `mode === 'create-many' && rows.length === 0`. Senza `mode`: `initialRows.length === 0` basta — se apri la bulk vuota, vuoi creare |
| **`mergePairedRows` condizione** | 🟢 Bassa | Ora `if (m === 'edit-many')`. Senza `mode`: `if (rows.some(r => r.id > 0 && r.related_transaction_id != null))` — stessa semantica, più precisa |
| **Test E2E** | 🟡 Media | Nessun test E2E passa `mode` direttamente (viene settato nel parent). I test non cambiano, ma serve un run completo per conferma |
| **Perdita di leggibilità nel parent** | 🟡 Media | `bulkMode = 'edit-many'` comunicava chiaramente l'intento. Senza, l'intento si legge da `bulkInitial` (righe con `id > 0` vs `id = 0`). Lievemente meno esplicito ma più onesto (riflette ciò che fa veramente il codice) |

### Piano di implementazione

**Effort stimato**: ~30 min, ~25 righe cambiate totali

#### A — `TransactionBulkModal.svelte` (15 righe)

1. Rimuovere `type Mode = 'create-many' | 'edit-many'` e la prop `mode` da `Props`
2. Modificare `fromTx(tx, overrideStatus?)`: inferire create vs edit da `tx.id > 0`
   ```ts
   function fromTx(tx: TXReadItem, overrideStatus?: 'delete'): DraftRow {
       const isCreate = !(tx.id > 0);
       // ...resto invariato, usa isCreate al posto di m === 'create-many'
   }
   ```
3. `$effect` init: `mergePairedRows()` condizionato a `rows.some(r => r.id > 0 && r.related_transaction_id != null)` anziché `m === 'edit-many'`
4. `$effect` init: auto-open FormModal vuoto → `rows.length === 0` (senza check mode)
5. `resetRow`/`resetAll`: `fromTx(d.original)` senza mode (original ha sempre `id > 0`)
6. Rimuovere `const editMode = $derived(...)` (dead code)
7. Toolbar picker: già condizionato a `allMainRows.length > 0` — nessun cambiamento

#### B — `+page.svelte` (10 righe)

1. Rimuovere `let bulkMode = $state<...>('create-many')`
2. Rimuovere le 7 assegnazioni `bulkMode = '...'` in:
   - `onAddTransaction()`: non serviva — initialRows vuote → create
   - `onEditBulk()`: non serviva — initialRows con `id > 0` → edit
   - `onCloneBulk()`: non serviva — già setta `id: 0` nelle righe
   - `onBulkDelete()`: non serviva — initialRows con `id > 0` + `initialStatus: 'delete'`
   - `handleEditRow()`: non serviva — row con `id > 0` → edit
   - `handleCloneRow()`: non serviva — row con `id: 0` → create
3. Rimuovere la prop `mode={bulkMode}` dal template `<TransactionBulkModal>`

### Risultato atteso

| Prima | Dopo |
|-------|------|
| `Props` ha `mode: 'create-many' \| 'edit-many'` | Nessuna prop `mode` |
| Parent gestisce `bulkMode` con 8 assegnazioni | Parent prepara solo `bulkInitial` (le righe dicono tutto) |
| `fromTx(tx, mode)` branch su `mode` | `fromTx(tx)` branch su `tx.id > 0` |
| Dead code `editMode` presente | Rimosso |
| Ambiguità concettuale: "mode è create ma ho appena aggiunto una riga edit" | Coerente: ogni riga è quello che dice il suo `id`/`status` |
| `mergePairedRows` legato a stringa mode | `mergePairedRows` legato alla presenza di dati reali |

La modale diventa una **unified batch editor** pura, dove il comportamento di ogni riga è determinato dai suoi dati, non da un flag globale. I test E2E non richiedono modifiche perché non interagiscono con la prop `mode`.

---

## Bugfix Round 2 — Tooltip arricchiti, Pagination PickerModal, Riformulazione messaggi validazione

**Date**: 2026-05-07
**Status**: ✅ COMPLETED
**Trigger**: Test walk post-completion

---

### Bug 1 — Tooltip PickerModal mostra `#1` anziché icona+nome+ruolo

**Sintomo**: nel PickerModal "Cerca e aggiungi", il tooltip sulle righe disabilitate mostra:
```
Accesso Editor richiesto sul broker #1
```

**Atteso**: il tooltip deve mostrare icona broker + nome broker + icona SVG del ruolo corrente dell'utente + ruolo minimo richiesto con icona. Esempio:
```
[🏦ico] Interactive Brokers [👁 Viewer] — richiesto [✏ Editor]
```

**Root cause**: `disabledTooltipFn()` in `TransactionPickerModal.svelte` (L.88-91) fa solo `brokers.find(b => b.id === brokerId)?.name ?? '#${brokerId}'` e non risolve icona/ruolo.

**Fix proposto**:
1. Usare `getBrokerIconUrlById(brokerId)` per l'icona
2. Usare `getBrokerRole(brokerId)` per il ruolo corrente
3. Usare `getRoleSvgHtml(role)` per icona SVG ruolo
4. Comporre: `"<img...> <strong>BrokerName</strong> <svg...role_icon> CurrentRole — richiesto <svg...editor_icon> Editor"`
5. Aggiornare chiave i18n `transactions.picker.disabledTooltip` in 4 lingue

**File**: `TransactionPickerModal.svelte`, `{en,it,fr,es}.json`

---

### Bug 2 — Pagination PickerModal non funziona

**Sintomo**: il componente `DataTablePagination` si mostra nel PickerModal ma cliccando i pulsanti non succede nulla — non cambia pagina né il numero di elementi per riga.

**Root cause** (investigata):

La catena di rendering è:

```
PickerModal → TransactionsTable → DataTable + DataTablePagination (external)
```

Quando non ci sono filtri né sort attivi, `isGrouped = true` (L.169 TransactionsTable). In questo stato:
1. DataTable riceve `enablePagination={!isGrouped}` = `false` → paginazione interna disattivata (L.946)
2. TransactionsTable mostra il **paginator esterno** (L.966-968), la versione pair-never-split
3. Il paginator esterno chiama `onPageChange?.(idx + 1)` e `onPageSizeChange?.(s)` — ma questi callback vengono dal **parent** (PickerModal)
4. **PickerModal non passa né `onPageChange` né `onPageSizeChange`** (L.158-170) → entrambi sono `undefined` → il click fa nulla
5. `currentPage` resta fisso a `1` (default dalla prop) perché nessuno lo aggiorna

Inoltre, `pageSize={20}` è passato come prop ma senza callback per cambiarlo → il dropdown "righe per pagina" è visivamente presente ma inerte.

**Nota positiva**: `ModalBase` usa `{#if open}` (L.112 ModalBase.svelte) → il contenuto viene **distrutto** alla chiusura e **ricreato** all'apertura. Questo significa che filtri, sort, selezione e pagina si resettano automaticamente ad ogni riapertura. Non serve logica di reset esplicita — il requisito "riapertura = stato fresco" è già soddisfatto dall'architettura.

Le `filteredMain` e `filteredPartners` sono `$derived` da `mainRows` + `excludeIds`, quindi le righe mostrate sono sempre aggiornate (righe già aggiunte alla BulkModal vengono escluse tramite `excludeIds`).

**Fix proposto** — solo `TransactionPickerModal.svelte` (~10 righe):

1. Aggiungere stato locale:
   ```ts
   let pickerPage = $state(1);
   let pickerPageSize = $state(20);
   ```

2. Passare i callback a `TransactionsTable`:
   ```svelte
   <TransactionsTable
       ...props esistenti...
       currentPage={pickerPage}
       pageSize={pickerPageSize}
       onPageChange={(p) => pickerPage = p}
       onPageSizeChange={(s) => { pickerPageSize = s; pickerPage = 1; }}
   />
   ```

3. Non serve reset esplicito al reopen: `ModalBase` distrugge+ricrea il contenuto, gli `$state()` tornano ai valori iniziali.

**File**: `TransactionPickerModal.svelte` (unico file da modificare)

---

### Bug 3 — Riformulazione messaggi validazione: contesto operazione

**Problema**: i messaggi di errore validazione nelle 3 modali (FormModal, BulkModal, DeleteModal) descrivono la violazione come fatto compiuto ("le posizioni vanno in negativo") anziché come conseguenza dell'operazione ("eliminando/salvando → le posizioni andrebbero in negativo"). L'utente non capisce che è l'azione stessa a causare il problema.

**Principio**: ogni messaggio deve comunicare chiaramente:
1. **Cosa** — quale entità è coinvolta (asset, valuta)
2. **Quando** — la data della violazione
3. **Dove** — su quale broker
4. **Perché** — quale operazione causerebbe il problema
5. **Che effetto** — il risultato negativo (saldo negativo, posizione negativa)

#### 3a — Codici errore backend e parametri

| Codice | `params` dal backend | Contesto |
|--------|---------------------|----------|
| `balanceCashNegative` | `{brokerId, currency, balance, date}` | Saldo cash di una valuta va sotto zero |
| `balanceAssetNegative` | `{brokerId, assetId, balance, date}` | Quantità detenuta di un asset va sotto zero |
| `accessDenied` | `{brokerId}` | L'utente non ha ruolo EDITOR sul broker |

#### 3b — Frasi attuali vs proposte

**`balanceCashNegative`**:

| Lingua | Attuale | Proposta |
|--------|---------|----------|
| EN | `Cash balance for {currency} goes negative ({formattedBalance}) on {date} at {brokerName}` | `Saving would cause {currency} cash to go negative ({formattedBalance}) on {date} at {brokerName}` |
| IT | `Il saldo {currency} va in negativo ({formattedBalance}) il {date} su {brokerName}` | `Il salvataggio porterebbe il saldo {currency} in negativo ({formattedBalance}) il {date} su {brokerName}` |
| FR | `Le solde {currency} devient négatif ({formattedBalance}) le {date} chez {brokerName}` | `L'enregistrement ferait passer le solde {currency} en négatif ({formattedBalance}) le {date} chez {brokerName}` |
| ES | `El saldo {currency} se vuelve negativo ({formattedBalance}) el {date} en {brokerName}` | `Guardar haría que el saldo {currency} sea negativo ({formattedBalance}) el {date} en {brokerName}` |

**`balanceAssetNegative`**:

| Lingua | Attuale | Proposta |
|--------|---------|----------|
| EN | `{assetName} holdings go negative ({balance}) on {date} at {brokerName}` | `Saving would cause {assetName} holdings to go negative ({balance}) on {date} at {brokerName}` |
| IT | `Le posizioni di {assetName} vanno in negativo ({balance}) il {date} su {brokerName}` | `Il salvataggio porterebbe le posizioni di {assetName} in negativo ({balance}) il {date} su {brokerName}` |
| FR | `Les positions de {assetName} deviennent négatives ({balance}) le {date} chez {brokerName}` | `L'enregistrement ferait passer les positions de {assetName} en négatif ({balance}) le {date} chez {brokerName}` |
| ES | `Las posiciones de {assetName} se vuelven negativas ({balance}) el {date} en {brokerName}` | `Guardar haría que las posiciones de {assetName} sean negativas ({balance}) el {date} en {brokerName}` |

> **Nota**: usiamo "Saving" (generico) anziché "Deleting" perché lo stesso messaggio viene usato da FormModal (create/edit), BulkModal (batch misto create+edit+delete) e DeleteModal. Il backend non distingue il contesto — emette sempre lo stesso codice. "Saving" copre tutti i casi: "salvare questa modifica/creazione/eliminazione porterebbe a..."

#### 3c — Banner colori e titoli per la DeleteModal

Attualmente la DeleteModal ha:
- **Validazione OK** → banner verde "✓ This transaction can be deleted safely" — ✅ OK
- **Errori** → banner con errori risolti — ma senza titolo chiaro

**Proposta banner DeleteModal**:

| Stato | Colore | Titolo | Contenuto |
|-------|--------|--------|-----------|
| Validate OK (issues=[]) | 🟢 Verde | `✓ {canBeDeleted}` | Testo chiave esistente |
| Validate fallita (issues.length > 0) | 🟡 Giallo | `⚠️ {validateWarningTitle}` | Lista issues con `resolveIssueMessage()` |
| Commit fallito (committed:false) | 🔴 Rosso | `⛔ {deleteAbortedTitle}` | Lista issues + spiega che l'operazione è stata annullata |

**Nuove chiavi i18n**:

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `transactions.deleteModal.validateWarningTitle` | `Validation issues` | `Problemi di validazione` | `Problèmes de validation` | `Problemas de validación` |
| `transactions.deleteModal.deleteAbortedTitle` | `Deletion cancelled` | `Eliminazione annullata` | `Suppression annulée` | `Eliminación cancelada` |
| `transactions.deleteModal.deleteAbortedDetail` | `The operation was rolled back because it would violate balance rules:` | `L'operazione è stata annullata perché violerebbe le regole di saldo:` | `L'opération a été annulée car elle violerait les règles de solde :` | `La operación fue cancelada porque violaría las reglas de saldo:` |

#### 3d — Banner colori e titoli per FormModal e BulkModal (coerenza)

Per coerenza, verificare e uniformare anche nei FormModal e BulkModal:

| Stato | Colore | Titolo FormModal/BulkModal |
|-------|--------|---------------------------|
| Validate OK | 🟢 Verde | `✓ Validation passed` / `✓ Validazione superata` |
| Validate fallita | 🟡 Giallo | `⚠️ Validation issues` / `⚠️ Problemi di validazione` |
| Commit fallito | 🔴 Rosso | `⛔ Save cancelled` / `⛔ Salvataggio annullato` |

Le chiavi per BulkModal/FormModal esistono già (`transactions.bulk.commitRolledBack` etc.) — verificare che siano coerenti.

#### 3e — Nota sulla risposta `{committed: false, issues: [], results: [...]}`

⚠️ Attenzione al caso `committed: false` con `issues: []` (array vuoto) ma `results` con `status: "success"`. Questo sembra un bug backend o un edge case — se non c'è alcun issue perché `committed` è `false`? Da investigare:
- Se è un Validate (dry-run), `committed` è sempre `false` e `issues: []` significa "nessun problema" → è il caso successo
- Se è un Commit reale, `committed: false` con `issues: []` non dovrebbe accadere

**Verifica necessaria**: il frontend deve distinguere tra:
1. `POST /validate` (dry-run: `committed` sempre `false`, `issues: []` = tutto OK)
2. `POST /commit` (real: `committed: false` + `issues: [...]` = errore, `committed: true` = successo)

Se la DeleteModal chiama `/validate` e riceve `{committed: false, issues: []}` → questo è **successo validazione** → banner verde.
Se chiama `/commit` e riceve `{committed: false, issues: []}` → questo è un **bug** o un caso anomalo → trattare come errore generico.

---

## Bugfix Round 3 — Picker paired reset, remove row action, banner coerenza, currency flag

**Date**: 2026-05-08
**Status**: ⏳ PLANNED
**Trigger**: Test walk post Round 2 fix

---

### Bug 4 — "Reimposta tutto" slega le paired transactions importate dal Picker

**Sintomo**: dopo aver aggiunto una coppia paired (#38/#39) dal PickerModal, se si clicca "Reimposta tutto" nella BulkModal, le 2 metà vengono slegate — ottengono `related_transaction_id = null`, `link_uuid` diversi, e appaiono come 2 transazioni standalone indipendenti.

**Root cause**: `resetAll()` chiama `fromTx(d.original)` su ogni draft. Se `fromTx` genera un nuovo `link_uuid` per le righe create (caso `isCreate`), ma le righe paired dal picker hanno `id > 0` (sono edit), il problema è in `mergePairedRows(drafts, ...)` che non viene richiamato dopo il reset. Il risultato:
- `resetAll` resetta i draft singolarmente
- I campi `partnerBrokerId`, `_partnerId`, `_hidden`, `link_uuid` vengono persi nel reset
- Serviva un re-merge dopo il reset

**Fix proposto**:
1. In `resetAll()`, dopo aver resettato tutti i draft, ri-chiamare `mergePairedRows(drafts, [...allMainRows, ...allPartnerRows])` per ricostruire i legami paired
2. Trigger `drafts = [...drafts]` per reattività

**File**: `TransactionBulkModal.svelte` — funzione `resetAll()` (~5 righe)

---

### Bug 5 — Nessuna azione "Remove" per righe aggiunte dal Picker (solo "Delete mark")

**Sintomo**: una volta aggiunte righe dal PickerModal, l'unica azione distruttiva è "Segna per eliminazione" (🗑). Ma l'utente vuole poter **rimuovere** la riga dal batch senza marcarla per delete nel DB. Attualmente se rimuovi una riga `status: 'original'`, non c'è modo di farlo — puoi solo marcarla delete (che al commit esegue `DELETE` nel DB).

**Atteso**: un'azione "✕ Rimuovi dal batch" (NOT "elimina dal DB") che:
- Per righe `status: 'new'` → già presente (il pulsante ✕ remove esiste)
- Per righe `status: 'original'` aggiunte **dal picker** → rimuove la riga dal batch senza segnarla per l'eliminazione. La riga torna disponibile nel picker (il suo ID esce da `excludeIds`)
- Per righe `status: 'original'` presenti **dall'apertura iniziale** → NON mostrare l'azione remove (queste vanno solo editate/delete)

**Differenza chiave**:
- `🗑 Segna per eliminazione` → `status: 'delete'` → al commit: `DELETE /api/v1/transactions/{id}`
- `✕ Rimuovi dal batch` → rimuove la DraftRow da `drafts[]` → al commit: nessuna operazione su quella TX

**Implementazione proposta**:
1. Aggiungere un campo `_addedViaPicker: boolean` al DraftRow (default `false`)
2. In `handlePickerAdd()`, settare `d._addedViaPicker = true` su ogni draft creato dal picker
3. Aggiungere un'azione riga "✕ Remove" visibile quando `row._addedViaPicker && row.status !== 'new'`
4. L'azione chiama `removeRow(row.tempId)` (già esistente per `status: 'new'`)
5. Per paired: se rimuovi una metà, rimuovi anche il partner (come in `removeRow()` attuale)

**i18n**: chiave `transactions.bulk.removeFromBatch` — "Remove from batch" / "Rimuovi dal batch" / "Retirer du lot" / "Quitar del lote"

**File**: `TransactionBulkModal.svelte` — interfaccia DraftRow, handlePickerAdd, actions list (~15 righe)

---

### Bug 6 — Banner validazione: coerenza helper + currency con flag

**6a — Coerenza helper banner**

**Sintomo**: i banner di validazione/commit in FormModal, BulkModal e DeleteModal usano codice duplicato per costruire il markup (icona, titolo, lista issues). Serve un componente unico dedicato alle transazioni.

**Nome**: `TransactionResultBanner.svelte` — non "ValidationBanner" perché copre sia validazione (dry-run) sia commit (salvataggio/eliminazione reale). È specifico per le transazioni, non un generico UI banner.

**Fix proposto**: creare `TransactionResultBanner.svelte` in `lib/components/transactions/` con:
- Props: `variant: 'success' | 'warning' | 'error'`, `title: string`, `messages: string[]`
- Varianti:
  - `success` → verde, icona ✓ (CheckCircle)
  - `warning` → giallo/amber, icona ⚠️ (TriangleAlert)
  - `error` → rosso, icona ⛔ (emoji, NON XCircle — coerente con i banner commit attuali che usano emoji per i rollback)
- Messaggi renderizzati con `{@html}` (contengono `<strong>`, `<img>`, SVGs dal `resolveIssueMessage`)
- Usato in: `TransactionDeleteModal`, `TransactionBulkModal`, `TransactionFormModal`

**File**: nuovo `frontend/src/lib/components/transactions/TransactionResultBanner.svelte` + refactor 3 modali

---

**6b — Currency con flag+simbolo nel messaggio**

**Sintomo**: nel messaggio di validazione, la currency appare come testo plain `<strong>USD</strong>` senza flag né simbolo. Ma il saldo formattato dopo (tra parentesi) ha già flag+simbolo: `(-2633,50 $ 🇺🇸 USD)`. La prima menzione della currency dovrebbe essere coerente.

**Atteso**: `<strong>$ 🇺🇸 USD</strong>` anziché `<strong>USD</strong>`.

**Root cause**: `resolveIssueMessage()` nella BulkModal/DeleteModal formatta `currency` (dalla prop `params.currency`) come semplice testo bold. Non applica il formatter di valuta con flag.

**Fix proposto**:
1. In `resolveIssueMessage()`, per il codice `balanceCashNegative`, formattare `params.currency` con la stessa funzione che produce `$ 🇺🇸 USD`:
   - Usare `formatCurrencyWithFlag(code)` → `{symbol} {flag} {code}`
   - Dove `symbol` = `getCurrencySymbol(code)`, `flag` = `getCurrencyFlag(code)`
2. Wrappare in `<strong>`: `<strong>${formatCurrencyWithFlag(code)}</strong>`

**File**: `resolveIssueMessage()` in BulkModal (e stessa logica in DeleteModal/FormModal — se centralizzata con 6a, basta un punto)

---

### Ordine di implementazione Round 3

1. **Bug 6a** (ValidationBanner component) — crea il componente, poi refactora le 3 modali
2. **Bug 6b** (currency flag) — tocca `resolveIssueMessage`, 1 punto se centralizzato
3. **Bug 4** (reset paired) — ~5 righe in `resetAll()`
4. **Bug 5** (remove from batch) — ~15 righe, nuovo campo DraftRow + azione

**Stima totale Round 3**: ~3-4h
