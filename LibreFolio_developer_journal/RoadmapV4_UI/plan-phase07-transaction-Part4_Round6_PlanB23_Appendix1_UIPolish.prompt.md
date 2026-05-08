# Plan — Phase 07 · Part 4 · Round 6 · Piano B23 · Appendix 1 — UI Polish & Guard Fix

**Date**: 2026-05-08
**Status**: ✅ COMPLETED
**Parent**: [`plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanB23_BulkDeleteViaBulkModal.prompt.md)

---

## TL;DR

Polish UI dal test walk finale B23: toast delete con frase strutturata leggibile, modale paired più larga, footer bottoni uniformati (icone su tutti, icon-only su mobile) in tutte e 4 le modali transazionali, guard viewer-only su `onBulkDelete()`/`onEditBulk()` con toast warning, tooltip Picker a capo senza `--`, "Reimposta tutto" condizionale, rimozione banner success (solo inline). Aggiornamento test E2E impattati.

---

## Steps

### Step 1 — Toast delete: frase strutturata leggibile ✅ (~30min)

**Problema**: il toast mostra solo "Commissione / Directa SIM / 2026-05-06" senza contesto — serve una frase chiara.

**File**: [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte) — `confirmDeleteModal()` L.786-808

**Modifiche**:
- Standalone: `"Transazione eliminata: {typeIcon}Commissione su {brokerIcon}Directa SIM — 2026-05-06"` con preposizioni e contesto
- Paired: `"Coppia eliminata: {typeIcon}Trasferimento {assetName} — {brokerIcon}Coinbase → {brokerIcon}Interactive Brokers — 2026-05-07"`
- Usare chiavi i18n `transactions.deleteModal.toastDeletedStandalone` e `transactions.deleteModal.toastDeletedPaired` con placeholder per i segmenti HTML

**i18n** (4 lingue):

| Chiave | EN | IT |
|--------|----|----|
| `toastDeletedStandalone` | `Transaction deleted:` | `Transazione eliminata:` |
| `toastDeletedPaired` | `Pair deleted:` | `Coppia eliminata:` |
| `toastOnBroker` | `on` | `su` |

Le chiavi `toastSuccess`/`toastPairedSuccess` esistenti (L.732-733 en.json) da rimuovere — sostituite dalle nuove.

---

### Step 2 — DeleteModal paired: maxWidth `xl` + bottoni con icone ✅ (~20min)

**File**: [`TransactionDeleteModal.svelte`](frontend/src/lib/components/transactions/TransactionDeleteModal.svelte)

**2a.** Cambiare `maxWidth="lg"` (L.115) a `maxWidth="xl"` per il layout B (paired). Approccio: usare `maxWidth={layout === 'B' ? 'xl' : 'lg'}`.

**2b.** Aggiungere icona `X` (lucide) al bottone Annulla/Chiudi (L.293-299):
```
<X size={15} /> {testo}
```

---

### Step 3 — Footer bottoni responsive: icon-only su mobile ✅ (~1.5h)

**Problema**: i bottoni footer vanno a capo su mobile. Soluzione: su mobile mostrare solo le icone, su desktop icona+testo.

**Impatto**: tutte e 4 le modali transazionali devono avere lo stesso pattern footer.

**Pattern proposto**: `<span class="hidden sm:inline">{testo}</span>` accanto all'icona. Su schermi < `sm` (640px) il testo è nascosto, resta solo l'icona. Aggiungere `title` attribute per tooltip nativo su mobile.

**File coinvolti**:

| Modale | File | Bottoni footer |
|--------|------|----------------|
| DeleteModal | `TransactionDeleteModal.svelte` | ⚡ Verifica ora, ✕ Annulla, 🗑 Elimina / Elimina entrambe |
| FormModal | `TransactionFormModal.svelte` L.1737-1760 | ⚡ Verifica ora, ✕ Annulla, 💾 Salva |
| BulkModal | `TransactionBulkModal.svelte` L.1648-1667 | ⚡ Verifica ora, ✕ Annulla, 💾 Salva |
| PickerModal | `TransactionPickerModal.svelte` | ✕ Annulla, ✅ Aggiungi |

**Dettagli per ogni bottone**:

- **"⚡ Verifica ora"**: sostituire emoji ⚡ con `<Zap size={14} />` (lucide), testo in `<span class="hidden sm:inline">`. Su mobile: solo icona Zap
- **"Annulla/Chiudi"**: aggiungere `<X size={15} />`, testo in `<span class="hidden sm:inline">`
- **"🗑 Elimina"**: icona `Trash2` già presente, testo in `<span class="hidden sm:inline">`
- **"💾 Salva"**: sostituire emoji 💾 con `<Save size={15} />` (lucide), testo in `<span class="hidden sm:inline">`
- **"✅ Aggiungi" (Picker)**: `<Check size={15} />`, testo in `<span class="hidden sm:inline">`

**Attributo `title`** su ogni bottone per tooltip nativo al hover/long-press mobile.

---

### Step 4 — Guard viewer-only su `onBulkDelete()` e `onEditBulk()` ✅ (~1h)

**Problema**: le azioni bulk toolbar (Edit, Delete) includono nella selezione anche righe su broker viewer-only. Devono essere filtrate con banner informativo.

**File**: [`+page.svelte`](frontend/src/routes/(app)/transactions/+page.svelte) — `onEditBulk()` L.469, `onBulkDelete()` L.513

**4a.** Creare funzione helper `filterEditableRows(rows: TXReadItem[]): { editable: TXReadItem[], skipped: TXReadItem[] }`:
- Per ogni riga standalone: `canEditBroker(row.broker_id)` → se false, skip
- Per ogni riga paired: entrambi i broker devono essere editabili (`canEditPaired(row)`) — se il partner non è editabile, skip entrambe le metà
- Ritorna `{ editable, skipped }`

**4b.** In `onEditBulk()` e `onBulkDelete()`: chiamare `filterEditableRows(selectedRows)` PRIMA di aprire la BulkModal. Se `skipped.length > 0`:
- Mostrare un toast warning (non blocking) con messaggio: "N transazioni escluse: accesso Editor richiesto"
- Usare lo stesso formato tooltip del Picker (icona broker + nome + ruolo) nel dettaglio toast
- Procedere con solo le righe `editable`

**4c.** Se `editable.length === 0`: mostrare toast error e NON aprire la modal.

**i18n** (4 lingue):

| Chiave | EN | IT |
|--------|----|----|
| `transactions.bulk.skippedViewerOnly` | `{n} transactions excluded: Editor access required` | `{n} transazioni escluse: accesso Editor richiesto` |
| `transactions.bulk.allViewerOnly` | `No editable transactions in selection` | `Nessuna transazione modificabile nella selezione` |

---

### Step 5 — Tooltip Picker: a capo e senza `--` ✅ (~15min)

**File**: [`TransactionPickerModal.svelte`](frontend/src/lib/components/transactions/TransactionPickerModal.svelte) — `disabledTooltipFn()` L.92-104

**5a.** Sostituire ` — ` (em dash) con `<br>` per andare a capo tra ruolo corrente e ruolo richiesto.

**5b.** Il formato diventa:
```
{brokerIcon} BrokerName {roleSvg} CurrentRole
{requiredLabel} {editorSvg} Editor
```

**i18n**: chiave `transactions.picker.requiredRole` già esiste — verificare che il testo sia "Required:" / "Richiesto:" / "Requis :" / "Requerido:" (senza `--`).

---

### Step 6 — "Reimposta tutto" visibile solo se c'è qualcosa da reimpostare ✅ (~15min)

**File**: [`TransactionBulkModal.svelte`](frontend/src/lib/components/transactions/TransactionBulkModal.svelte) — L.1613-1617

**Stato attuale**: il pulsante è visibile quando `visibleDrafts.length > 0`.

**Correzione**: visibile quando esiste almeno un draft `status !== 'original'` (cioè c'è qualcosa di modificato, nuovo o marcato delete). Se tutti i draft sono `original`, non serve reimposta nulla.

Condizione: `visibleDrafts.some(d => d.status !== 'original')` oppure un `$derived` `hasChanges`.

---

### Step 7 — i18n: nuove chiavi in 4 lingue ✅ (~20min)

**File**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

Chiavi da aggiungere/modificare:

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `transactions.deleteModal.toastDeletedStandalone` | `Transaction deleted:` | `Transazione eliminata:` | `Transaction supprimée :` | `Transacción eliminada:` |
| `transactions.deleteModal.toastDeletedPaired` | `Pair deleted:` | `Coppia eliminata:` | `Paire supprimée :` | `Par eliminado:` |
| `transactions.deleteModal.toastOnBroker` | `on` | `su` | `chez` | `en` |
| `transactions.bulk.skippedViewerOnly` | `{n} transactions excluded: Editor access required` | `{n} transazioni escluse: accesso Editor richiesto` | `{n} transactions exclues : accès Éditeur requis` | `{n} transacciones excluidas: acceso Editor requerido` |
| `transactions.bulk.allViewerOnly` | `No editable transactions in selection` | `Nessuna transazione modificabile nella selezione` | `Aucune transaction modifiable dans la sélection` | `No hay transacciones editables en la selección` |

Chiavi da rimuovere: `transactions.deleteModal.toastSuccess`, `transactions.deleteModal.toastPairedSuccess` (sostituite da Step 1).

---

### Step 8 — Aggiornamento test E2E ✅ (~45min)

**Test potenzialmente impattati**:

| File | Test | Impatto |
|------|------|---------|
| `tx-delete.spec.ts` | Toast content assertions | Step 1 cambia il testo del toast — aggiornare `toHaveText` / `textContent` match |
| `tx-delete.spec.ts` | Modal cancel/confirm buttons | Step 3 aggiunge icona al cancel — se test cercano testo esatto, aggiornare |
| `tx-delete.spec.ts` | Layout B paired | Step 2 cambia maxWidth — nessun impatto test (non verifica width) |
| `tx-picker-pagination.spec.ts` | Validate now button | Step 3 cambia emoji→icona — test usa `data-testid`, OK |
| `transactions-modals.spec.ts` | FormModal footer buttons | Step 3 — se test cercano testo bottoni, aggiornare |

**Strategia**: i test usano `data-testid` → la maggior parte NON si rompe. Verificare solo quelli che fanno `toHaveText()` o `textContent` match sui bottoni o toast.

**Azione**: dopo le modifiche, eseguire `./dev.py test front-transaction all --headed` per verifica completa.

---

## Ordine di implementazione

```
Step 7 (i18n)                     ← primo (serve per step 1, 4)
Step 1 (toast delete leggibile)   ← indipendente
Step 5 (tooltip Picker a capo)    ← indipendente
Step 6 (reimposta condizionale)   ← indipendente
Step 4 (guard viewer-only)        ← indipendente
Step 2 (maxWidth + icona cancel)  ← indipendente
Step 3 (footer responsive)        ← dopo step 2 (stessi file)
Step 8 (test E2E)                 ← dopo tutti gli altri
```

**Ordine consigliato**: 7 → 1 → 5 → 6 → 4 → 2 → 3 → 8

**Stima totale**: ~4-5h

---

## Note

- **Step 3 (responsive footer)** è il più ampio ma il pattern è meccanico: `<span class="hidden sm:inline">` su ogni label. Applicabile con search&replace.
- **Step 4 (guard viewer-only)** filtra nel parent (`+page.svelte`), non nella BulkModal — coerente con il Picker che filtra a monte.
- **Nessun cambio backend**: tutto frontend.

---

## Post-completion fixes (from TestWalk feedback)

### Fix A — ⚡ Validate now: emoji ripristinato ✅
- **Problema**: Step 3 aveva sostituito l'emoji ⚡ con icona SVG `Zap` — l'utente vuole l'emoji
- **Fix**: ripristinato `⚡` in tutte e 3 le modali (Delete, Form, Bulk), rimosso import `Zap`
- **File**: `TransactionDeleteModal`, `TransactionFormModal`, `TransactionBulkModal`

### Fix B — Tooltip Picker: dismiss on scroll ✅
- **Problema**: il tooltip sulle righe disabled nel Picker restava fisso scrollando la tabella su mobile
- **Fix**: aggiunto listener `scroll` (capture, passive) in `Tooltip.svelte` che chiama `hide()` su qualsiasi scroll quando il tooltip è visibile
- **File**: `Tooltip.svelte`

### Fix C — "Reimposta tutto": condizione, responsive, "Reimposta selezionati" ✅
- **Problema 1**: compariva anche con solo righe `new` (nulla da reimpostare)
- **Fix**: condizione cambiata da `d.status !== 'original'` a `(d.status === 'edited' || d.status === 'delete') && d.original`
- **Problema 2**: label non si foldava su mobile
- **Fix**: aggiunto `<span class="hidden sm:inline">` + `title` attribute
- **Problema 3**: mancava "Reimposta selezionati" nella toolbar inline
- **Fix**: aggiunto bottone `<Undo2>` nella toolbar inline, visibile se ≥1 riga selezionata è reimpostabile. Chiama `resetRow()` per ogni riga selezionata.
- **i18n**: chiave `transactions.bulk.resetSelected` in 4 lingue
- **File**: `TransactionBulkModal.svelte`, `{en,it,fr,es}.json`

### Fix D — Guard viewer-only: bug `canEditPaired()` con parametro errato ✅
- **Problema**: paired OWNER↔EDITOR veniva bloccata. `canEditPaired(r)` passava un TXReadItem come 1° param e `undefined` come 2° → sempre false
- **Root cause**: `canEditPaired()` richiede 2 broker ID, non un oggetto riga. Il partner broker ID non veniva risolto
- **Fix**: lookup del partner da `mainRows`/`partnerRows`, passaggio esplicito `canEditPaired(r.broker_id, partner.broker_id)`
- **File**: `+page.svelte` — `filterEditableRows()`

### Fix E — Toolbar BulkModal: tutti i bottoni responsive su mobile ✅
- **Problema**: "🔍 Cerca e aggiungi", "N selezionati", "Elimina", "Aggiungi riga" non si foldavano su mobile
- **Fix**: `<span class="hidden sm:inline">` + `title` su tutti i bottoni toolbar
- **File**: `TransactionBulkModal.svelte`

### Fix F — Righe BulkModal: sfondo colorato per stato ✅
- **Problema**: solo il badge nella colonna "Stato" indicava lo stato, le righe erano tutte bianche
- **Fix**: `getRowClass()` ora applica sfondo tenue per ogni stato:
  - `new` → verde emerald sbiadito (`bg-emerald-50/40 dark:bg-emerald-950/15`)
  - `edited` → ambra sbiadito (`bg-amber-50/40 dark:bg-amber-950/15`)
  - `delete` → rosso sbiadito + line-through (invariato)
  - `original` → nessuno sfondo
- **File**: `TransactionBulkModal.svelte` — `getRowClass()`

---

## Successor

- [`plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md`](./plan-phase07-transaction-Part4_Round6_PlanC_TxStoreRefactor.prompt.md) — txStore refactor architetturale
