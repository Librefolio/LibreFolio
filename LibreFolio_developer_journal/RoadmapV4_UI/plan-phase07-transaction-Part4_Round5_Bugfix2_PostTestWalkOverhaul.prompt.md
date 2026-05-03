# Plan — Phase 7 · Part 4 · Round 5 · Bugfix 2 — Post-TestWalk Overhaul

**Date**: 2026-05-02
**Status**: ✅ DONE
**Priority**: P1 (blocking bugs + architectural refactor)
**Estimated effort**: ~16 h

**Parent**: [`plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix1_DualFormAndBulkFixes.prompt.md)
**Next**: [`plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md`](./plan-phase07-transaction-Part4_Round5_Bugfix3_TestWalkFixes.prompt.md)

---

## 🎯 Obiettivo

BulkModal → griglia **completamente readonly**; FormModal unico punto di editing. Il FormModal emette la coppia completa per tipi paired. Edit/clone singoli da main table passano per BulkModal→FormModal. Pulsante "Salva" → "✓ Applica" quando embeddato. Fix massivo i18n, delete modal, date duali, documentazione, DRY refactor.

---

## 📋 Steps

### Step 1 — BulkModal completamente readonly + doppio-click → FormModal (~2 h)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

(a) Tutte le colonne diventano display-only (rimuovere tutti i `type: 'custom'` con component editabili e i `type: 'editable-*'`; ogni cella renderizza HTML statico formattato).
(b) Aggiungere `ondblclick` sulle righe → `openEditRowForm(row)`.
(c) Il pulsante matita (già presente) resta come azione per riga.
(d) Creare funzione helper `renderReadonlyCell(row, columnId)` per DRY: usata sia per le colonne standalone che per le righe paired con Da:/A:.

### Step 2 — Fix `openEditRowForm`: status `new` → mode `create` pre-populated (~15 min)

**File**: `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

In `openEditRowForm()` (L1109): quando `row.status === 'new'`, impostare `formMode = 'create'` anziché `'edit'`, così il tipo resta editabile nel FormModal. Il `formEditingTempId` resta settato (così `handleFormPushed` esegue `patchRowFromForm` anziché `addRowFromForm`). Quando `row.status !== 'new'`, usare `formMode = 'edit'` come oggi.

**Rationale**: se si fa edit su una riga `new`, il form si deve aprire in modalità create pre-popolato, altrimenti il tipo diventa fisso (immutabile in edit mode).

### Step 3 — FormModal: pulsante "✓ Applica" quando embeddato (~20 min)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Nel footer (L1608): quando `commitOnSave === false`, cambiare label da `$t('common.save')` a `$t('transactions.form.apply')` (nuova chiave i18n: EN "Apply", IT "Applica", FR "Appliquer", ES "Aplicar"). Aggiungere icona `Check` da lucide-svelte. La semantica rimane identica (`onPushDraft`).

### Step 4 — FormModal dual: emettere coppia completa nel pushDraft (~1.5 h)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

In TransactionFormModal L847-860: quando `!commitOnSave && pairLayout`, usare `collectDualCreates()` anziché `collectCreate()`. Il payload diventa `{_dual: true, items: [...], _partnerBrokerId, _partnerCash, _partnerDate}`.

In TransactionBulkModal `handleFormPushed`: se il payload ha `_dual === true`:
- (a) in create: creare il draft visibile con `link_uuid` + `partnerBrokerId` + `partnerCash` + `partnerDate` e un draft `_hidden` per la metà "to"
- (b) in edit: aggiornare sia la riga visibile che la `_hidden`

In `collectCreate`/`collectUpdate`: iterare anche le righe `_hidden` per includerle nel payload backend.

**Fattorizzare** in `buildPairedDrafts()` riusata da tutti i percorsi.

### Step 5 — Date duali nel form paired (~1 h)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`, `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

In TransactionFormModal: aggiungere `date: string` a `DualDraftTo`. Nel dual template, sezione Da/A (L1281-1317): aggiungere un DatePicker per lato. `collectDualCreates()`: item "from" usa `draft.date`, item "to" usa `dualTo.date`.

In BulkModal, la colonna `date` per paired rows renderizza Da:/A: con 2 date. `DraftRow` si arricchisce di `partnerDate?: string`.

### Step 6 — Edit/Clone singoli da main table → BulkModal + FormModal (~1 h)

**Files**: `frontend/src/routes/(app)/transactions/+page.svelte`, `frontend/src/lib/components/transactions/TransactionBulkModal.svelte`

In `+page.svelte`:
- `handleEditRow(row)` (L583) → apre `bulkOpen=true, bulkMode='edit-many', bulkInitial=[row]` con `bulkAutoOpenForm='edit'`
- `handleCloneRow(row)` → `bulkMode='create-many'`, `bulkInitial=[cloned row]`, `bulkAutoOpenForm='create'`

In TransactionBulkModal: nuova prop `autoOpenForm?: 'create' | 'edit' | null`; nell'`$effect` di apertura, quando impostata, `queueMicrotask(() => openEditRowForm(drafts[0]))` (edit) o `openAddRowForm()` (create).

Rimuovere il `TransactionFormModal` standalone e `formOpen`/`formMode`/`formInitial` dal `+page.svelte`.

### Step 7 — Fix BulkDeleteLinkedPairModal: i18n + UX singola (~1.5 h)

**Files**: `frontend/src/lib/components/transactions/BulkDeleteLinkedPairModal.svelte`, `frontend/src/lib/i18n/{en,it,fr,es}.json`

(a) Aggiungere tutte le chiavi `transactions.bulkDelete.*` nei 4 file i18n (title, intro, applyToAll, removeAll, extendAll, cancel, confirm, summary, noConflicts, noConflictsDesc, deleting, rolledBack).
(b) Quando `problemRows.length === 0`, mostrare UI semplificata "Eliminare {n} transazioni?" con solo [Annulla] e [🗑 Elimina] — senza tabella/radio/dettagli.
(c) Tradurre stringhe hardcoded residue nella tabella (colonne, labels riga).

### Step 8 — Fix i18n mancanti (~30 min)

**Files**: `frontend/src/lib/i18n/{en,it,fr,es}.json`

(a) `assets.create` → EN "New asset", IT "Nuovo asset", FR "Nouvel actif", ES "Nuevo activo"
(b) `transactions.form.apply` → EN "Apply", IT "Applica", FR "Appliquer", ES "Aplicar"
(c) `transactions.form.assetOptional` → EN "(optional)", IT "(opzionale)", FR "(optionnel)", ES "(opcional)" — mostrare nel form quando `assetField === 'optional'`

### Step 9 — Fix `↔` prefix non visibile al primo render (~30 min)

**File**: `frontend/src/lib/components/transactions/TransactionTypeSearchSelect.svelte`

Le opzioni derivano da `getTypeRule()` che ritorna `FALLBACK_RULE` (con `requiresPair: false`) prima del fetch API. Fix: rendere `optionTypes` dipendente da `isTypesLoading()` — se loading, ritornare array vuoto (nessuna opzione finché i dati reali non arrivano). Oppure attendere `ensureTypesLoaded()` e forzare un re-render.

### Step 10 — Fix FX dual form layout overflow desktop (~15 min)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Dual template Da/A cash cells (L1286, L1308): aggiungere `min-w-0` al container CompactCashCell per impedire overflow della grid. Verificare che il grid parent abbia `overflow-hidden`.

### Step 11 — Banner validazione verde → inline footer (~20 min)

**File**: `frontend/src/lib/components/transactions/TransactionFormModal.svelte`

Rimuovere `InfoBanner variant="success"` per lo stato "valid". Nel footer (L1594), tra "⚡ Verifica" e Salva/Applica:
```svelte
{#if isFreshlyValid}
    <span class="text-emerald-600 dark:text-emerald-400 text-xs flex items-center gap-1">
        <Check size={14}/> {$t('transactions.validate.valid')}
    </span>
{/if}
```
Banner resta solo per warning/errori.

### Step 12 — Fix `BrokerSearchSelect.svelte` errori IDE (~15 min)

**File**: `frontend/src/lib/components/ui/select/BrokerSearchSelect.svelte`

(a) Rimuovere variabile `selectedBroker` non usata (L56).
(b) Sostituire `{@const broker = option.data as BrokerSelectItem}` (L67, L74) con pattern Svelte 5 compatibile — rimuovere il cast `as`, usare JSDoc o un helper inline. Esempio:
```svelte
{#snippet item(option)}
    {@const broker = /** @type {BrokerSelectItem} */ (option.data)}
    <!-- ... -->
{/snippet}
```

### Step 13 — Fix `cash-transfer.png` non mostrata (~10 min)

Il file esiste in `frontend/static/icons/transactions/cash-transfer.png` e il backend metadata dice `icon_slug="cash-transfer"`. In modalità dev Vite, i file statici sono serviti direttamente da `static/` senza build. L'icona potrebbe non apparire per cache browser.

Verifica: se dopo hard-refresh persiste, controllare che il file sia effettivamente un'immagine valida (non una copia rinominata di un formato sbagliato). Nessuna modifica di codice necessaria, solo verifica runtime.

### Step 14 — Documentazione mkdocs (solo EN) (~1 h)

**Files**: `mkdocs_src/docs/financial-theory/instruments/transaction-types/transfer.en.md`, `mkdocs_src/docs/financial-theory/instruments/transaction-types/index.en.md`, `backend/app/schemas/transactions.py`

(a) Ristrutturare `transfer.en.md`: titolo "Asset Transfer, Cash Transfer, FX Conversion & Adjustment", documentare i 4 tipi reali (`TRANSFER`, `CASH_TRANSFER`, `FX_CONVERSION`, `ADJUSTMENT`), rimuovere i vecchi codici `TRANSFER_IN/OUT`.
(b) Copiare `cash-transfer.png` in `mkdocs_src/docs/static/icons/transactions/`.
(c) Aggiornare `index.en.md`: righe separate per Asset Transfer, Cash Transfer, FX Conversion, Adjustment.
(d) Aggiornare `doc_slug` backend: `FX_CONVERSION` → `"transfer"`, `ADJUSTMENT` → `"transfer"`.
(e) `./dev.py api sync` dopo modifica backend.

---

## ✅ Checklist

- [x] Step 1: BulkModal completamente readonly + doppio-click → FormModal
- [x] Step 2: Fix `openEditRowForm` — status `new` → mode `create`
- [x] Step 3: FormModal pulsante "✓ Applica" quando embeddato
- [x] Step 4: FormModal dual emette coppia completa nel pushDraft
- [x] Step 5: Date duali nel form paired
- [x] Step 6: Edit/Clone singoli → BulkModal + FormModal
- [x] Step 7: Fix BulkDeleteLinkedPairModal i18n + UX singola
- [x] Step 8: Fix i18n mancanti (assets.create, form.apply, assetOptional)
- [x] Step 9: Fix `↔` prefix non visibile al primo render
- [x] Step 10: Fix FX dual form layout overflow desktop
- [x] Step 11: Banner validazione verde → inline footer
- [x] Step 12: Fix BrokerSearchSelect errori IDE
- [x] Step 13: Fix cash-transfer.png non mostrata (verifica runtime — file valido, cache browser)
- [x] Step 14: Documentazione mkdocs (solo EN) + doc_slug backend + api sync
