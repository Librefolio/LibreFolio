# Plan — Phase 07 · Part 4 · Step 5 · Round 1 — Tabella `/transactions` refactor + Bugfix Add modal

**Date**: 2026-04-27
**Status**: 🔨 IN CORSO (Step 1–6 ✅, Round 1.2 W17–W33 ✅, Round 1.3 W34–W46 ✅ tranne W35 visual + W46 /files deferred)
**Priority**: P0 (blocker: Add transaction modal va in infinite loop)
**Estimated effort**: ~1 day

**Parent plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md) (Steps 1–10 ✅, ma walkthrough manuale ha rivelato regressioni — vedi sotto)
**Walkthrough sorgente**: [`walkthrough-phase07-transaction-Part4.md`](./walkthrough-phase07-transaction-Part4.md)
**Successor (deferito)**: `plan-phase07-transaction-Part4_Round2-stagingModalDataTable.prompt.md` — restyle StagingModal su `DataTable` (titolo "0 of 0 edited", layout non-DataTable, Promote/BulkDelete extender refresh).

---

## 🎯 Obiettivo

Risolvere l'infinite-loop bloccante che impedisce di aprire la modale **Add Transaction**, e rifondare la tabella principale `/transactions` sul pattern `DataTable + DataTableToolbar + DataTablePagination` di Assets/FX (eliminando il markup parzialmente custom corrente). Le modali interne (`TransactionStagingModal`, `TransferPromoteModal`, `BulkDeleteLinkedPairModal`) restano fuori scope di questo Round e saranno riprese in Round 2 dopo che la tabella è solida.

In aggiunta:
1. Filtro **`currency-stack`** generico in `DataTable` (riusabile da TX, FX, Assets futuri).
2. Filtro **`tags`** multi-select derivato client-side dal set dei tag presenti nelle righe attualmente caricate (no nuovi endpoint).
3. **Mock data**: aggiungere tag rappresentativi a un sottoinsieme di TX in `populate_mock_data.py` per validazione visiva del filtro.

**Esplicitamente fuori scope**:
- Restyle interno modali (StagingModal, Promote, BulkDelete) — Round 2.
- Endpoint backend nuovi.
- `/transactions/tags/distinct` o simili — il set tag è derivato dalle righe visibili.

---

## 🐞 Issues raccolte dal walkthrough

| ID | Severity | Descrizione | Step |
|----|----------|-------------|------|
| W1 | ❌ blocker | Click su `+ Add Transaction` → `effect_update_depth_exceeded` (infinite loop), modale non apre | 1 |
| W2 | ⚠ UX | Broker color è una "striscia" 4px accanto a date; atteso = intera riga tinta del colore broker | 2 |
| W3 | ⚠ UX | Broker badge non mostra l'icona del broker | 2 |
| W4 | ⚠ UX | Manca colonna Type-as-icon (con tooltip che mostra il tipo) immediatamente dopo Date | 2 |
| W5 | ⚠ UX | Cella `asset` non mostra l'icona dell'asset accanto al nome | 2 |
| W6 | ⚠ UX | Filtro `type` è completamente vuoto (manca `enumOptions`) | 5 |
| W7 | ⚠ UX | Filtro `tags` non esiste come UX dedicata; l'utente vuole multi-select a spunte derivato dai tag visibili (con search) — i tag in DB sono CSV | 3 |
| W8 | ⚠ UX | Filtro `cash` deve essere multi-currency: lista di righe currency, ognuna con il proprio range numerico, imbuto e cestino | 4 |
| W9 | ❌ regressione | URL non riflette i filtri applicati (encoding mancante / `onFiltersChange` non collegato) | 5 |
| W10 | ⚠ UX | Manca l'occhio (`ColumnVisibilityToggle`) della tabella | 6 |
| W11 | ⚠ UX | Manca `DataTablePagination` (paginatore custom usato al suo posto) | 6 |
| W12 | ⚠ UX | `DataTableToolbar` è renderizzato come banner verde **in fondo** invece che in cima | 6 |
| W13 | ⚠ UX | Single-row actions: presente solo `edit` — atteso anche `clone` e `delete` (parità con bulk) | 6 |
| W14 | ⚠ UX | Badge `●evt` deve essere un puntino dentro la colonna **azioni** con `Tooltip` che mostra le caratteristiche dell'evento | 2 |
| W15 | ⚠ UX | Manca counter "N transactions" nel header/toolbar | 6 |
| W16 | (deferito Round 2) | Modale edit con titolo "0 of 0 edited" e layout non-DataTable, broker badge senza icona, ecc. | — |

---

## 📊 Situazione di partenza (riferimenti rapidi)

| Cosa | Path |
|------|------|
| Pagina TX (con bug filtri URL + SelectionBar in fondo) | `frontend/src/routes/(app)/transactions/+page.svelte` |
| Tabella TX (color band 4px, `enablePagination=false`, `enableColumnVisibility` non passato) | `frontend/src/lib/components/transactions/TransactionsTable.svelte` |
| Modale con loop | `frontend/src/lib/components/transactions/TransactionStagingModal.svelte` (`$effect` riga 155) |
| `DataTable` generico (con `enableColumnVisibility`, `onFiltersChange`, `initialFilters`) | `frontend/src/lib/components/table/DataTable.svelte` |
| `DataTableColumnFilter` (variants: text/number/size/date/enum) | `frontend/src/lib/components/table/DataTableColumnFilter.svelte` |
| `DataTablePagination` | `frontend/src/lib/components/table/DataTablePagination.svelte` |
| `DataTableToolbar` (counter + bulk actions, usato in `/assets`, `/fx`) | `frontend/src/lib/components/table/DataTableToolbar.svelte` |
| `ColumnVisibilityToggle` (occhio) | `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` |
| `CurrencySearchSelect` riusabile | `frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte` |
| Tooltip generico | `frontend/src/lib/components/ui/Tooltip.svelte` |
| Asset icon helper | `frontend/src/lib/utils/assetTypes.ts` (+ `assetStore.getAssetInfo(id).icon_url`) |
| Broker icon (esiste in /static?) | da verificare in Step 2 |
| TX type PNG | `frontend/static/icons/transactions/{TYPE}.png` (Step 1 Part 4) |
| Backend `Transaction.tags` storage | `backend/app/db/models.py:633` (CSV stringa) — schema espone `List[str]` |
| Mock TX seed | `backend/test_scripts/test_db/populate_mock_data.py` |

---

## 🧱 Step di implementazione

### Step 1 — Bugfix `effect_update_depth_exceeded` su Add Transaction ✅ DONE

> **Fix applicato** in `frontend/src/lib/components/transactions/TransactionStagingModal.svelte`: l'`$effect` che reset i drafts ora calcola la lista in una variabile locale `next: DraftRow[]` e itera quella per raccogliere gli `asset_id`, **prima** di assegnare a `drafts`. Così la rune `drafts` non diventa più una dipendenza dell'effect (no more read-write loop). svelte-check: 0 errors / 0 warnings. Verifica runtime: TBD via dev server. ✅ DONE

> **Fix applicato**: in `TransactionStagingModal.svelte` l'`$effect` che reset i drafts ora calcola la lista in una variabile locale `next: DraftRow[]` e itera quella per raccogliere gli `asset_id`, **prima** di assegnare a `drafts`. Così la rune `drafts` non diventa più una dipendenza dell'effect (no more read-write loop). svelte-check: 0 errors / 0 warnings. Verifica runtime: TBD via dev server.

**Files**:
- `frontend/src/lib/components/transactions/TransactionStagingModal.svelte`

**Root cause**: in `TransactionStagingModal.svelte` riga ~155 c'è un `$effect` che **scrive `drafts`** e poi **rilegge `drafts`** all'interno dello stesso effetto:
```ts
$effect(() => {
    if (!open) return;
    rolledBack = null;
    issues = [];
    if (mode === 'create-many') {
        drafts = initialRows.length > 0 ? ... : [freshEmptyDraft()];
    } else {
        drafts = initialRows.map(freshDraftFromTx);
    }
    const ids = new Set<number>();
    for (const d of drafts) if (d.draft.asset_id != null) ids.add(d.draft.asset_id);  // ← read of drafts ← retriggers effect
    if (ids.size > 0) void ensureAssetsLoaded();
});
```
Svelte 5 traccia ogni `read` durante la run dell'effect — il `for (const d of drafts)` rende `drafts` una dipendenza, e la `=` precedente lo invalida → re-run infinito.

**Deliverable**:
1. Computare `ids` **prima** della scrittura `drafts = …`, leggendo da una variabile locale (`computed: DraftRow[]`) anziché dallo stato runico:
   ```ts
   $effect(() => {
       if (!open) return;
       rolledBack = null;
       issues = [];
       const next: DraftRow[] = mode === 'create-many'
           ? (initialRows.length > 0 ? initialRows.map(freshDraftFromTx).map(d => ({...d, status:'new', draft:{...d.draft, id:undefined}})) : [freshEmptyDraft()])
           : initialRows.map(freshDraftFromTx);
       const ids = new Set<number>();
       for (const d of next) if (d.draft.asset_id != null) ids.add(d.draft.asset_id);
       drafts = next;            // single write at the end
       if (ids.size > 0) void ensureAssetsLoaded();
   });
   ```
2. Aggiungere un `prevOpen` locale (modulo-scope) o `untrack(() => …)` se l'edge `open false → true` deve essere isolato da re-run su `mode`/`initialRows` reference-changes (verificare a runtime).
3. Test: aprire/chiudere la modale 5× consecutive senza errori console.

**Tests**: smoke E2E manuale + verifica console pulita.

**Stima**: 0.5h

---

### Step 2 — Riga colorata per broker + colonne icona (type, asset, broker) ✅ DONE

> **Modifiche applicate**:
> - `TransactionsTable.svelte`: rimossa colonna `colorBand` (4px stripe). Aggiunta classe riga `tx-row-tinted` con background `color-mix(in srgb, var(--broker-bg) 12%, transparent)` (light) / 22% (dark) — l'intera riga è ora tinted del colore broker.
> - **Colonna `typeIcon`** (subito dopo `date`, larghezza 60px): `type:'html'` con `<img class="tx-type-icon">` da `getTransactionTypeIconUrl()`, sortable+filterable, `tooltip:{text: localized label}` via `Tooltip` di `DataTable`'s HtmlCell. Il `TransactionTypeBadge` resta usato in modali/altrove ma non in tabella.
> - **Cella `asset`** ora usa `type:'image'` con `src=info.icon_url`, `text=display_name`, `size=20`, fallback al testo nudo se l'asset non ha `icon_url`.
> - **Cella `broker`**: rimosso il pill grande, sostituito con `<span class="tx-broker-cell">[dot tinted] name</span>` — il dot è 10px tondo colorato dalle CSS vars broker (`--broker-bg` / `--broker-dark-bg`). Niente icona broker dedicata (non esiste in `static/icons/brokers/`).
> - **`●evt` rimosso da colonna `links`**, spostato come **rowAction `event`** (lucide `Sparkles` viola, visible solo se `asset_event_id != null`, click → `onEventBadgeClick`). `RowAction.label` esteso a `string | (() => string) | ((row: T) => string)` e `DataTable` aggiornato per renderizzare title row-aware → tooltip event mostra `[type · date · value currency · auto/manual]` da `eventTooltipMap` come HTML title (tooltip ricco con `<Tooltip>` componente è follow-up Round 2).
> - **Row actions parity**: aggiunte `clone` (lucide `Copy`) e `delete` (lucide `Trash2`, variant danger) nella tabella, cablate via nuove props `onCloneRow` / `onDeleteRow` riusate in `+page.svelte` (clone replica logic di `onCloneBulk` su singola riga; delete riusa `onBulkDelete` con `selectedRows=[row]` per gestire automaticamente il linked-pair extender).
>
> svelte-check: 0/0. Lint format: clean.

**Files**:
- `frontend/src/lib/components/transactions/TransactionsTable.svelte`
- `frontend/src/lib/utils/brokerColors.ts` (estensione `getBrokerIconUrl` se serve)

**Deliverable**:
1. **Riga colorata broker** — sostituire la color-band 4px con tinta sull'**intera riga** via `getRowStyle(d) = brokerStyle(broker_id) + ` background-color:rgb(var(--broker-bg))/0.10` `` (oppure usare CSS class `tx-row-broker-{id}` con `:global` rules in `<style>` che leggono `var(--broker-bg)`). Manteniamo dark-mode parity. La color-band 4px viene rimossa dalle colonne.
2. **Type-icon-only column** (immediatamente dopo `date`) — nuova colonna `type-icon`:
   - `type: 'custom'`, `width: 48`, `sortable: true` (sort by enum), `filterable: true` (enum, vedi Step 3).
   - Cell renderizza solo `<img src={getTransactionTypeIconUrl(d.tx.type)} class="w-5 h-5">` wrappato in `Tooltip` con label localizzata (`$t('transactions.types.{TYPE}')`).
   - Mantenere il `TransactionTypeBadge` per altri usi (modali) ma non in questa cella.
3. **Asset icon nella cella `asset`** — wrappare display name con `[icon] display_name` via `assetStore.getAssetInfo(id).icon_url` (fallback: lucide `Package`).
4. **Broker badge con icona** — la cella `broker` mostra `[broker_icon] broker_name`. Se manca un'icona broker dedicata, fallback su pallino tinta (CSS dot) — verificare in `static/icons/brokers/` se esiste.
5. **Sposta `●evt` da `links` ad `actions`** — eliminare la sotto-cella `●evt` dalla colonna `links`; renderlo come `<Tooltip>` con un dot (lucide `Sparkles` o un piccolo cerchio viola) **dentro la actions column** (vedi Step 6 per parity edit/clone/delete). Tooltip mostra `[type · date · value currency · auto/manual]` da `eventTooltipMap`.

**Tests**: visual check su 3 brokers + dark mode + tooltip hover.

**Stima**: 2h

---

### Step 3 — Filtro `tags` multi-select da set visibile ✅ DONE

> **Modifiche applicate**:
> - **`types.ts`**: aggiunto `MultiEnumFilter` (`{type:'multi-enum', selected: string[]}`); aggiunto `'multi-enum'` a `ColumnType`; nuovo campo `ColumnDef.getMultiValue?: (row) => string[]`.
> - **`DataTable.svelte`**:
>   - Filter logic per `multi-enum`: row passes se `selected` vuota OR ∃ overlap con `getMultiValue(row)`.
>   - Helper `getMultiEnumOptions(column)` che computa il set ordinato dei valori distinti su `data` (NO endpoint nuovo). Passato come `enumOptions` al popover quando `type === 'multi-enum'`.
> - **`DataTableColumnFilter.svelte`**:
>   - Stato `multiEnums: Set<string>` + `multiEnumSearch: string`.
>   - UI: search-box (`<Search>` icon) + checkbox-list con `data-testid="filter-multi-enum-option-{value}"`. Vuoto → no filter; almeno 1 → applica.
> - **`TransactionsTable.svelte`**: cella `tags` ora `type:'multi-enum'` con `getMultiValue: d => d.tx.tags ?? []`.
> - **`populate_mock_data.py`**: ogni TX viene auto-taggata in base a tipo/asset_type (`core`, `speculative`, `rebalance`, `long-term`, `fees`) + tag `review` deterministico ogni 4 giorni indietro. Garantisce ≥4 tag distinti su molte TX dopo `./dev.py db create-clean && ./dev.py db populate`.
>
> svelte-check: 0/0.

### Step 4 — Filtro `currency-stack` generico in `DataTable` ✅ DONE

> **Modifiche applicate**:
> - **`types.ts`**: nuovo `CurrencyStackFilter` (`{type:'currency-stack', items: Array<{code, min?, max?}>}`); aggiunto `'currency-stack'` a `ColumnType`; nuovo campo `ColumnDef.getCurrencyValue?: (row) => {code, amount} | null`.
> - **`DataTable.svelte`**:
>   - Filter logic: row passes se `items` vuota OR ∃ item match (`code` ∧ `amount` entro `[min,max]`).
>   - Helper `getCurrencyOptions(column)`: estrae i codici currency presenti nel dataset → seed per il `CurrencySearchSelect` del popover.
>   - Nuova prop `currencyOptions: string[]` passata al `DataTableColumnFilter`.
> - **`DataTableColumnFilter.svelte`**:
>   - Stato `currencyStack: Array<{code, min?, max?}>`, `currencyToAdd: string`, `currencyOpenIdx: number | null`.
>   - UI: header con `<CurrencySearchSelect compact={true}>` (esclude le currency già nello stack); per ogni item una row con `[CODE]` + range corrente o "any amount" + bottone imbuto (`Filter` lucide) che apre inline editor min/max + bottone `Trash2` per rimuovere.
>   - `data-testid` per ogni interazione (`filter-currency-row-{code}`, `filter-currency-funnel-{code}`, `filter-currency-trash-{code}`).
> - **Riusabile** da Assets/FX: per usarlo basta dichiarare `type:'currency-stack'` e `getCurrencyValue` sulla `ColumnDef`. Il cablaggio sulla cella `cash` di TX arriva nello Step 5 (insieme all'URL encoding).
>
> svelte-check: 0/0.

**Files**:
- `frontend/src/lib/components/table/types.ts`
- `frontend/src/lib/components/table/DataTableColumnFilter.svelte`
- `frontend/src/lib/components/table/DataTable.svelte`
- `frontend/src/lib/components/transactions/TransactionsTable.svelte` (cablaggio sulla colonna `cash`)

**Deliverable**:
1. **Nuova variant `FilterValue`**:
   ```ts
   { type: 'currency-stack', items: Array<{ code: string; min?: number; max?: number }> }
   ```
2. **UI nel popover**:
   - Header: `<CurrencySearchSelect>` per aggiungere una nuova currency-row.
   - Per ogni item della lista: badge `[CODE]` + valore corrente min/max + icona imbuto (apre subpopover numeric range identico a `type:'number'`) + icona cestino (rimuove la riga).
   - Empty state quando `items.length === 0` (= nessun filtro applicato).
3. **Logica filtro** in `DataTable.filteredData`:
   - La colonna deve dichiarare una `getCurrencyValue?: (row) => { code: string; amount: number } | null` (nuovo campo `ColumnDef`), oppure il filter detecta cell type `'currency'` se introdotto in futuro. Per ora: passare `getCurrencyValue` come prop nella column TX `cash`.
   - Row passes se `items.length === 0` **OR** existsItem `i: i.code === row.code && (i.min === undefined || row.amount >= i.min) && (i.max === undefined || row.amount <= i.max)`.
4. **Generico** — l'estensione vive in `DataTable`/`DataTableColumnFilter`, **non** in TX-specific code, così è subito riusabile da `/fx` e `/assets` (cell `pricing`).
5. **URL encoding** del filter: serializzato come `cash=USD:0:1000,EUR:-500:500` (CSV di `code:min:max`, `min`/`max` opzionali → empty token). Documentato in `urlFilters.ts` se esiste o creato ad-hoc nel column.

**Tests**: filtro multi-currency su `cash`, sort+filter combinati, URL deep-link.

**Stima**: 2.5h

---

### Step 5 — Filtri `type` + `broker` popolati + URL encoding bidirezionale ✅ DONE

> **Modifiche applicate**:
> - **`TransactionsTable.svelte`**:
>   - `typeIcon` → `enumOptions: TX_TYPES.map(...)` (label i18n via `transactions.types.{TYPE}`), `urlKey: 'types'`.
>   - `broker` → `enumOptions: brokers.map(b => ({value:String(b.id), label: b.name}))`, `urlKey: 'broker_id'`.
>   - `date` → `urlKey: 'date'`; `asset` → `urlKey: 'asset_id'`; `tags` → `urlKey: 'tags'`; `cash` → `type:'currency-stack'` con `getCurrencyValue`, `urlKey: 'cash'`.
>   - Aggiunte props `onFiltersChange` + `initialFilters` passate al `<DataTable>` interno.
> - **`+page.svelte`**:
>   - `FilterMap.cash: Array<{code, min?, max?}>` aggiunta.
>   - `parseFiltersFromUrl` / `buildFiltersUrl` estesi: serializzazione `cash=USD:0:1000,EUR::500` (CSV di `code:min:max`, min/max opzionali con empty token).
>   - `filtersToColumnFilters(filters)` → seed `initialFilters` per il DataTable (mapping `types`→enum, `tags`→multi-enum, `broker_id`→enum, `date`→date, `cash`→currency-stack).
>   - `handleColumnFiltersChange(record)` → reverse mapping nei `filters` di pagina + reset `page=1` + `reload()` per re-fetch server-side.
>   - `$effect` esteso a tracciare `filters.cash`.
>
> svelte-check: 0/0. Filter UI ↔ URL ↔ server-fetch ora bidirezionale.

**Files**:
- `frontend/src/lib/components/transactions/TransactionsTable.svelte`
- `frontend/src/routes/(app)/transactions/+page.svelte`

**Deliverable**:
1. **`type` filter** — passare `enumOptions` dal `txTypeStore` (label localizzata + value enum). Stesso pattern già usato in `assets/AssetTable` per `asset_type`.
2. **`broker` filter** — passare `enumOptions` da `brokers` array.
3. **`urlKey` per ogni colonna filtrabile**:
   - `date` → `date_start` / `date_end`
   - `type` → `types` (CSV)
   - `asset` → `asset_id`
   - `broker` → `broker_id`
   - `tags` → `tags` (CSV)
   - `cash` → `cash` (formato `currency-stack` di Step 4)
4. **Bidirezionale**:
   - Outbound: collegare `onFiltersChange` di `DataTable` → callback in `TransactionsTable` → emit verso `+page.svelte` → mappare in `filters` state e `goto(buildFiltersUrl(filters), {replaceState:true, noScroll:true, keepFocus:true})`.
   - Inbound: passare `initialFilters` derivati da `parseFiltersFromUrl($page.url.searchParams)` al `DataTable` al primo mount.
5. **Filtri server-side vs client-side** — `broker_id`, `asset_id`, `types`, `date_start`, `date_end`, `tags`, `currency` continuano ad andare al backend (parametri di `GET /transactions`). I filtri di colonna del `DataTable` operano in **aggiunta** lato client su ciò che è già in memoria. Decidiamo: un filtro applicato dall'header push nei `filters` server-side per ridurre il dataset (consistente con `/files`).

**Tests**: deep-link `/transactions?types=BUY,SELL&tags=core,speculative&cash=USD::1000`, back/forward, reload preserva stato.

**Stima**: 2h

---

### Step 6 — Toolbar in cima + Pagination + Visibility + Row actions parity + Counter ✅ DONE

> **Modifiche applicate**:
> - **`TransactionsTable.svelte`**:
>   - Aggiunto `bind:this={tableRef}` sul `DataTable` interno + `export function getTableRef()` per esporre il ref a `ColumnVisibilityToggle`/`clearSelection`.
>   - Abilitato `enableColumnVisibility={true}` (l'occhio è ora reso esternamente dal parent via `ColumnVisibilityToggle tableRef={...}`).
>   - Sostituito il paginatore custom (`◂ N/M ▸`) con `<DataTablePagination>` standard: page-size dropdown (10/25/50/100/∞), navigation, jump-to-page input. La logica `pages` pair-aware resta: `DataTablePagination` viene mostrato quando `displayRows.length > 10`.
>   - Aggiunta prop `onPageSizeChange?: (pageSize: number) => void`.
>   - Aggiunto `export function getTotalCount()` per esporre il conteggio dataset.
> - **`+page.svelte`**:
>   - Header rifatto sul pattern Assets/FX:
>     - Counter badge "N" mono-font accanto al titolo (`data-testid="tx-count-badge"`).
>     - `<DataTableToolbar>` inline (mostrato quando `selectedRows.length > 0`) con bulk actions Edit (`Pencil`) / Clone (`Copy`) / Promote pair (`Zap`, condizionale) / Delete (`Trash2`, danger). `onClearSelection` chiama `tableRef.clearSelection()`.
>     - `<ColumnVisibilityToggle tableRef={transactionsTableComponent?.getTableRef()} />` accanto a Import/Add.
>   - Rimosso il banner verde inline in fondo (`tx-selection-bar`) — la toolbar in alto è ora l'unico entry point per le bulk actions.
>   - Aggiunto handler `handlePageSizeChange` che resetta `page=1` e re-fetcha.
>   - Reference `transactionsTableComponent` (`bind:this`) usato sia per `clearSelection()` che per il `tableRef` di `ColumnVisibilityToggle`.
> - **i18n**: aggiunte chiavi `transactions.actions.clone`/`delete`/`promotePair` in EN/IT/FR/ES.
> - **Format/check**: `./dev.py front format` (2 file ripuliti) + `./dev.py front check` → 0 errors / 0 warnings.

**Files**:
- `frontend/src/lib/components/transactions/TransactionsTable.svelte`
- `frontend/src/routes/(app)/transactions/+page.svelte`

**Deliverable**:
1. **Pagination** — `enablePagination={true}` su `DataTable`; rimuovere il paginatore custom in `TransactionsTable.svelte` riga ~447 (`{#if totalPages > 1}…{/if}`). La logica di pair-never-split resta nel `displayRows` derived; `DataTable` pagina su `displayRows` accettando page-size variabile naturale.
2. **Column visibility (occhio)** — `enableColumnVisibility={true}`. L'occhio verrà reso da `DataTable` stesso (eventualmente via `DataTableToolbar`); verificare flow corrente in Assets.
3. **`DataTableToolbar` in cima** in `+page.svelte`, sopra `<TransactionsTable>`:
   - Counter "N transactions" (totale del dataset corrente, non solo della pagina).
   - "M selected" quando N>0.
   - Bulk actions: `Edit`, `Clone`, `Delete`, `Promote pair` (condizionale).
   - Slot/sezione destra per `Add transaction` + `Import`.
   - Rimuovere il banner verde inline in fondo (`{#if selectedRows.length > 0}…{/if}` riga ~475–491 di `+page.svelte`).
4. **Row actions parity** in `rowActions` di `TransactionsTable`:
   - `edit` → `onEditRow` (esistente).
   - `clone` → handler in page che apre `TransactionStagingModal` mode `create-many` con la singola riga clonata (riusa logic di `onCloneBulk`).
   - `delete` → handler che riusa `onBulkDelete` con `selectedRows = [row]` (gestisce automaticamente linked-pair extender).
   - **Event dot** per `asset_event_id != null` come icon-action visiva (tooltip con dettagli evento, click no-op per ora — popover è follow-up Round 2).
5. **Toolbar slot per "Add"/"Import"** — i due bottoni del header migrano nel toolbar (decisione UX: meno duplicazione). Confermare in refinement.

**Tests**: counter aggiorna correttamente, occhio nasconde colonna, pagination nav, single-row clone+delete.

**Stima**: 2h

---

### Step 7 — i18n + lint + svelte-check + walkthrough re-run

**Files**:
- `frontend/src/lib/i18n/{en,it,fr,es}.json`

**Deliverable**:
1. Aggiungere chiavi nuove via `./dev.py i18n add`:
   - `transactions.table.eventTooltip` (`{type} · {date} · {value} {currency}`)
   - `transactions.filters.tags.searchPlaceholder`
   - `transactions.filters.cash.addCurrency`
   - `transactions.filters.cash.empty`
   - `transactions.toolbar.totalCount` (`{count} transactions`)
   - `transactions.actions.clone` / `transactions.actions.delete`
   - `table.filter.multiEnum.searchPlaceholder` (generico)
   - `table.filter.currencyStack.title` (generico)
2. Eseguire `./dev.py i18n update` per verificare 0 incomplete.
3. `./dev.py front lint` + `./dev.py front check` puliti.
4. Re-eseguire walkthrough sezione 1–6 di `walkthrough-phase07-transaction-Part4.md` e annotare residual ⚠.

**Stima**: 0.5h

---

## 🧪 Strategia test

### Smoke manuale (priorità)
1. Click `+ Add Transaction` → modale apre senza loop (W1).
2. Filtro `type` mostra opzioni (W6).
3. Filtro `tags` multi-select su mock data esteso (W7).
4. Filtro `cash` currency-stack con 2+ currency (W8).
5. Cambia un filtro header → URL aggiornato (W9). Reload preserva stato.
6. Toolbar in cima con counter + bulk actions (W12, W15).
7. Occhio nasconde colonna `tags` (W10).
8. Paginatore standard (W11).
9. Single-row actions: edit + clone + delete (W13).
10. Hover dot `●evt` in actions column → tooltip evento (W14).
11. Riga con tinta broker (W2), broker badge con icona (W3), type-icon column (W4), asset icon (W5).

### E2E (deferito Round 2 + Phase 7 final)
Le 6 spec del plan parent (`transactions-list`, `-goto`, `-staging`, `-bulk-delete`, `-promote`, `asset-event-delete`) restano follow-up.

### Lint/typecheck
- `./dev.py front lint` clean.
- `./dev.py front check` 0 errors / 0 warnings.

### Mock data
- `populate_mock_data.py` esteso con tag su ≥10 TX (Step 3).

---

## 🚧 Open Questions

1. **Filtro server-side vs client-side overlap (Step 5.5)** — il `DataTable` filter UI dovrebbe pushare nei query params di `GET /transactions` (consistente con `/files`) o restare puramente client-side sul dataset già caricato? Proposta: server-side per `broker`, `type`, `date`, `asset` (riducono il payload), client-side per `tags` (solo per finezza visiva sul caricato) e `cash` currency-stack (composizione complessa, server non lo supporta nativamente). Conferma in refinement.
2. **`currency-stack` URL format** (Step 4.5) — `cash=USD:0:1000,EUR::500` con `:` separator funziona, ma il valore decimale potrebbe collidere col separator? Decisione attuale: gli amount sono interi/float senza `:` → safe. In refinement valutare se preferire JSON-encoded.
3. **Toolbar Add/Import location** (Step 6.5) — migrare nel `DataTableToolbar` (top) o tenerli nel page-header? Plan attuale: nel toolbar per ridurre duplicazione e tenere le azioni "vicino al dato".
4. **`enableColumnVisibility` UX in `DataTable`** — il flag `enableColumnVisibility={true}` esiste ma il rendering dell'occhio è gestito tramite il toolbar (vedi `getColumnsForVisibility`/`toggleColumnVisibilityById` exports). Verificare in refinement come lo espone Assets/FX e replicare.
5. **`getCurrencyValue` sulla `ColumnDef`** (Step 4.3) — è la prima volta che una `ColumnDef` ha bisogno di un getter tipato. Alternativa: introdurre cell-type `'currency'` in `CellContent` e fare detect via `cell.type === 'currency'`. Decisione in refinement.

---

## 🔗 Cross-link

- **Parent plan**: [`plan-phase07-transaction-Part4.prompt.md`](./plan-phase07-transaction-Part4.prompt.md)
- **Walkthrough**: [`walkthrough-phase07-transaction-Part4.md`](./walkthrough-phase07-transaction-Part4.md)
- **Successor (deferito)**: `plan-phase07Step5Round2-stagingModalDataTable.prompt.md` (TBD)
- **devWiki**:
  - `concepts/svelte5-runes` — pattern `$effect` write-then-read trap (W1 root cause)
  - `concepts/e2e-data-testid-rule` — selettori test
  - `decisions/multi-broker-atomic-tx` — context atomicità su clone/delete singoli

---

## 📝 Commit strategy

Conventional Commits, 7 commit incrementali (uno per Step), ognuno verde su lint+typecheck:

1. `fix(transactions): break $effect read-write loop in TransactionStagingModal (W1)`
2. `feat(transactions): broker-tinted rows + type/asset/broker icon columns + event dot in actions (W2-W5,W14)`
3. `feat(table): add multi-enum filter variant + tags filter on TransactionsTable + mock data tags (W7)`
4. `feat(table): add generic currency-stack filter variant in DataTable (W8)`
5. `feat(transactions): wire type/broker enumOptions + bidirezionale URL filter sync (W6,W9)`
6. `feat(transactions): DataTableToolbar on top + Pagination + Visibility + row actions parity + counter (W10-W13,W15)`
7. `chore(transactions): i18n EN/IT/FR/ES + lint/check pass`

---

## ✅ Final-check (eseguito su questo plan)

- ✅ Issue del walkthrough mappate 1-a-1 con step (W1→S1, W2-W5+W14→S2, W7→S3, W8→S4, W6+W9→S5, W10-W13+W15→S6).
- ✅ Modali interne (W16) escluse e tracciate per Round 2.
- ✅ Filtro `currency-stack` generico (riusabile FX/Assets).
- ✅ Filtro `tags` client-side da set visibile (no nuovi endpoint).
- ✅ Mock data extension per tags.
- ✅ URL encoding bidirezionale tutti i filtri.
- ✅ Atomicità preservata (single-row clone/delete riusano gli stessi handler bulk).
- ✅ Plan auto-contenuto con cross-link a parent + walkthrough.

---

## 🔁 Walkthrough Round 1.2 — issues residue dopo Step 6 (2026-04-27)

Walkthrough manuale seguente al primo deploy degli step 1–6. Tracciate qui in fondo per fix in coda allo stesso Round (commit autonomi dopo ogni gruppo).

| ID | Severity | Descrizione | Action | Status |
|----|----------|-------------|--------|--------|
| W17 | ⚠ regressione | Quando page-size scende a `10` la paginazione sparisce (la condizione `displayRows.length > 10` esclude i casi `<= 10`) | fix soglia | ✅ B1 |
| W18 | ⚠ UX | Tinta riga broker troppo sbiadita in light, troppo scura in dark — alzare contrasto | css color-mix bump | ✅ B2 |
| W19 | ⚠ UX (feature) | Click sulle icone tipo TX → apre la pagina mkdocs `…/transaction-types/{slug}/` nella lingua corrente. Mobile: doppio-click o long-press, **non** single-tap | helper `getTxTypeDocUrl` + click delegation | ✅ B3 |
| W20 | ⚠ UX | Asset cell continua a mostrare solo testo, manca l'icona accanto al nome (regressione vs Assets table) | `ensureAssetsLoaded` early + `type:'image'` | ✅ B4 |
| W21 | ⚠ UX | Broker cell ha un dot-color e non il logo broker | dot conservato (no asset broker_icon disponibile in /static); riapertura quando logo dedicato sarà aggiunto | ⏳ deferred Round 2 |
| W22 | ⚠ UX | Ordine colonne: broker DEVE precedere asset | swap | ✅ B1 |
| W23 | ⚠ UX | Icone TX troppo piccole | enlarge `1.25rem → 1.75rem` | ✅ B1 |
| W24 | ⚠ regressione i18n | Modale "Add transaction" mostra `transactions.staging.createTitle — 1 draft` (chiave non tradotta) | aggiungere chiavi `staging.*` 4 lingue + plural | ✅ B9 |
| W25 | ⚠ architettura | La modale Add e Edit DEVONO essere la stessa (parametrizzata `mode`), import incluso. Verificare | audit + nota in JSDoc | ✅ B10 |
| W26 | ⚠ regressione i18n | Filtro `currency-stack`: chiavi `table.filter.currencyStack.*` non risolte | aggiungere chiavi 4 lingue | ✅ B9 |
| W27 | ❌ UX | Quando aggiungo una currency al filtro, il popover si chiude immediatamente | escludere `[role="listbox"]/[option]/[combobox]` dal click-outside | ✅ B7 |
| W28 | ❌ architettura | I filtri header lanciano `GET /api/v1/transactions?...` con i filtri server-side: NON deve. Backend invia tutto, frontend filtra solo client-side. Aggiungere bottone Refresh esplicito | rimuovere `queries` filter dal client + bottone Refresh in toolbar | ✅ B6 |
| W29 | ⚠ UX bug | Broker cell: alle larghezze "intermedie" compaiono "..." che però se allargo la colonna non spariscono (testo nascosto). Va parametrizzato sulla larghezza colonna o rimosso del tutto | css `min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap` | ✅ B2 |
| W30 | ⚠ UX | Tags renderizzati come `tag1, tag2, tag3` separati da virgola — vogliamo badge colorati (1 badge per tag, colore deterministico dal contenuto) | `getStringBadgeStyle` + `.tx-tag-badge` | ✅ B5 |
| W31 | ⚠ UX | Linked-event in `actions` è il posto sbagliato → spostare in **colonna dedicata** dopo `cash` (con dot tinted + tooltip evento) | nuova colonna `event` | ✅ B4 |
| W32 | ⚠ UX | Cash deve mostrare solo valuta (ISO3 + bandiera), come fa la tabella Assets | refactor cell `cash` | ✅ B4 |
| W33 | ⚠ UX bug | Broker cell: alle larghezze "intermedie" compaiono "..." che però se allargo la colonna non spariscono (testo nascosto). Va parametrizzato sulla larghezza colonna o rimosso del tutto | css `min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap` | ✅ B2 |

### Implementazione (eseguita in batch, nello stesso commit-set)

- **B1 (W17, W22, W23) ✅** — `TransactionsTable.svelte`: soglia paginatore `displayRows.length > pageSize` (mostra il paginatore quando esiste almeno 1 pagina aggiuntiva). Reorder colonne: broker prima di asset. Icona TX `1.25rem → 1.75rem` (con cursore + hover-lift, click-target più grande).
- **B2 (W18, W33) ✅** — Tinta riga: `light 12%→22%` (hover 32%), `dark 22%→38%` (hover 48%). Cell broker: `min-width:0; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap` sulla `.tx-broker-name` → ellipsis robusto a tutte le larghezze.
- **B3 (W19) ✅** — `transactionTypes.ts`: aggiunti `TX_TYPE_DOC_SLUG` (BUY/SELL→buy-sell, DEPOSIT/WITHDRAWAL→deposit-withdrawal, DIVIDEND/INTEREST/FEE/TAX/TRANSFER → matching pages, fallback a section index per FX_CONVERSION/ADJUSTMENT) + helper `getTxTypeDocUrl(type, lang)` con prefisso `/<lang>` per non-default. Cell `typeIcon` ora rende un `<button data-tx-type-doc>` e la table-wrap delega click/dblclick/pointerdown: desktop=single click, mobile (`pointer:coarse`)=dblclick o long-press ≥500ms. (Componente `TxTypeIconLink.svelte` non usato — la cell HtmlCell non monta componenti Svelte; delegazione HTML scelta per semplicità).
- **B4 (W20, W31, W32) ✅** — Cell `asset`: `void ensureAssetsLoaded()` chiamato in script-init, cell continua a usare `type:'image'` con `info.icon_url`. Cell `cash` ora `[flag] CODE` via `getCurrencyInfo(code).flag_emoji` (stesso pattern di Assets table). Nuova **colonna `event`** dopo `cash`: dot violet 10px con tooltip `[type · date · value currency · auto/manual]`, click delegato → `onEventBadgeClick`. Rimossa `event` da `rowActions`.
- **B5 (W30) ✅** — Helper `getStringBadgeStyle(tag)` (in `colors.ts`) usato come inline-style su `<span class="tx-tag-badge" style="--badge-bg:…">`. CSS `.tx-tag-badge` legge le CSS vars; rendering = wrap chips colorati con golden-ratio palette deterministica.
- **B6 (W28) ✅** — `+page.svelte` `loadMainRows`: rimossi tutti i filtri (`broker_id`/`asset_id`/`types`/`date_*`/`tags`/`currency`) dalle `queries`; restano solo `limit`/`offset` come soft-cap. `handleColumnFiltersChange` non chiama più `reload()`, e `handlePageSizeChange` nemmeno: il filtraggio + sort + paginazione sono ora 100% client-side via `DataTable`. Aggiunto bottone **Refresh** (`RefreshCw`, `data-testid="tx-refresh-button"`) nel header, accanto a `ColumnVisibilityToggle`/Import/Add, che invoca `void reload()` e mostra `animate-spin` mentre `loading=true`.
- **B7 (W27) ✅** — `DataTableColumnFilter.handleClickOutside`: aggiunto early-return su `target.closest('[role="listbox"], [role="option"], [role="combobox"]')` → la dropdown del `CurrencySearchSelect` (resa in portale esterno al popover) non chiude più il filtro al click su un'opzione.
- **B8 (W29) ✅** — Sub-popover `currency-stack` min/max: ora replica esattamente l'UI di `type:'number'` (input numerici + dual range slider lineare con tick a 25/50/75%, label min/mid/max in basso). Helper `curMinPos`/`curMaxPos`, `updateCurrencyMin/MaxSlider` per ogni riga della stack, scale linear `numToSliderPos`/`sliderPosToNum` riusati 1:1.
- **B9 (W24, W26) ✅** — i18n keys aggiunte in EN/IT/FR/ES (script `/tmp/libreFolio_i18n_round12.py`):
  - `transactions.staging.createTitle/editTitle/draftSingular/draftPlural/editedFmt`
  - `transactions.refresh`
  - `transactions.table.event`
  - `table.filter.currencyStack.addCurrency/empty/any`

  Titolo `TransactionStagingModal` ora usa interpolazione `{n}` / `{n}/{total}` invece di stringa hard-coded.
- **B10 (W25) ✅** — Audit + documentazione: il JSDoc di `TransactionStagingModal.svelte` è stato esteso per chiarire che è la **modale universale** per tutti i flussi (manual create-many, edit-many, single-row edit/clone, BRIM import-from-broker in Round 2). Niente codice duplicato — Round 2 estenderà il `mode` dispatcher per il flusso BRIM.

**Validazione**: `./dev.py front check` → 0/0 ✅; `./dev.py i18n audit` → 939 keys, 0 incomplete ✅; smoke walkthrough rapido sui punti W17–W33 (residui visibili pendenti).

**Residui aperti**:
- **W21** ⏳ — Broker logo: nessun asset broker_icon disponibile in `static/icons/brokers/`. Dot CSS resta. Quando si introdurranno gli asset broker_icon (Round 2 / Phase 7 final) basta upgradare la cell `broker` per renderizzare `<img>` invece del dot.

---

## 🔁 Walkthrough Round 1.3 — issues residue post Round 1.2 (2026-04-27)

**⚠️ Nessun commit è stato fatto nel Round 1.2 — tutte le modifiche sono unstaged.**

Walkthrough manuale post Round 1.2. Issues tracciate qui per fix immediato nello stesso Round.

| ID | Severity | Descrizione | Action | Status |
|----|----------|-------------|--------|--------|
| W34 | ❌ bug i18n | `[object Object]` nel titolo di TUTTI i filter popover (`DataTableColumnFilter`). Causa: `$t('table.filter')` restituisce il sotto-oggetto `{ currencyStack: {…} }` anziché una stringa. | Aggiunta chiave `table.filterLabel` in 4 lingue; `DataTableColumnFilter` usa `$t('table.filterLabel')` anziché `$t('table.filter')`. | ✅ C1 |
| W35 | ⚠ UX dark | Colori riga broker in dark mode non corretti — la tinta dark (38%/48%) non è visibile o troppo smorza. | Verifica richiesta — i valori CSS `color-mix` dark 38%/48% sono già presenti nel CSS; possibile problema di specificità o variabile `--broker-dark-bg` non impostata. | ⏳ deferred visual |
| W36 | ⚠ UX | Icone asset mancanti nelle celle: il componente `AssetIcon.svelte` (chain: icon_url → asset-type PNG → BarChart3 fallback) non è usato nella cella tabella TX. La cella `asset` usa `type:'image'` che funziona solo con `icon_url` ma non ha fallback al PNG del tipo. | Cell `asset` ora usa `getAssetTypeIconUrl(info.asset_type)` come fallback quando `icon_url` è null. | ✅ C3 |
| W37 | ⚠ UX | Icone broker mancanti: il componente `BrokerIcon.svelte` (chain: icon_url → portal favicon → plugin icon → Briefcase) non è usato. La cella `broker` mostra solo un dot colorato. | Esteso `BrokerLike` con `icon_url?/portal_url?/default_import_plugin?`; `loadBrokers` carica i campi extra; cell broker mostra `<img>` con fallback a dot colorato via `onerror`. Broker `enumOptions` ora include `iconUrl` per il filtro. | ✅ C3 |
| W38 | ⚠ UX | Double-click su icona tipo TX non naviga alla pagina doc. Il click event è intercettato ma `openInNewTab` non si attiva su desktop. | Click delegation semplificata: rimosso handling `data-tx-link` (ora row action); `data-tx-type-doc` handler desktop (single click → `openInNewTab`) verificato funzionante. | ✅ C7 |
| W39 | ⚠ UX | Filtro `type` (enum) ha solo checkbox senza icone, conteggi e Select All/Clear All. Desiderato: stile identico al filtro asset-type nella pagina `/assets` (con icona PNG del tipo, conteggio, bottoni Select All / Clear All). | Esteso `EnumOption` con `iconUrl?`; UI `DataTableColumnFilter` enum ora rende `<img>` per ogni opzione quando `iconUrl` è fornito + `data-testid` per ogni opzione; TX `typeIcon` enumOptions include `iconUrl: getTransactionTypeIconUrl(tt)`. Select All/Clear All già presenti nel template `enum`. | ✅ C8 |
| W40 | ⚠ UX | Filtro `broker` (enum) ha solo checkbox senza icone e nomi broker stilizzati. Desiderato: stile identico con icona broker (chain BrokerIcon), nome, conteggio. | Broker `enumOptions` ora include `iconUrl` derivata dalla chain (icon_url → portal favicon). | ✅ C8 |
| W41 | ❌ bug | Pagination mancante: `DataTablePagination` non compare nella tabella TX. Causa: `displayRows.length > pageSize` non è soddisfatta perché pagination è completamente client-side ma il backend continua a ricevere `limit=100&offset=0`. | Rimossi `limit/offset` dalla query `loadMainRows` (carica TUTTI i TX); condizione visibilità `DataTablePagination` cambiata a `totalPages > 1`. | ✅ C2 |
| W42 | ⚠ UX | Event dot (`●`) non centrato nella colonna — è allineato a sinistra. | Aggiunto wrapper `<div class="tx-event-cell">` con `display:flex; justify-content:center; align-items:center; width:100%`. | ✅ C5 |
| W43 | ⚠ UX | Colonna event dovrebbe essere tra `typeIcon` e `asset` (non dopo `cash`). | Riordinata: `date → typeIcon → event → broker → asset → quantity → cash → tags`. | ✅ C5 |
| W44 | ⚠ UX residuo | Colonna `links` (ultima, header vuoto) crea una colonna fantasma visibile. | Rimossa colonna `links`; funzionalità `🔗 Go to linked pair` spostata in row action (`linked-pair`, icona Link2, visibile solo quando `related_transaction_id != null`). Ghost chip non più necessario (il ghost è già segnalato dalla tinta violetta della riga). | ✅ C5 |
| W45 | ⚠ UX | Cella `cash` mostra solo `🇪🇺 EUR` (bandiera + codice). Desiderato: `5,00 € 🇪🇺EUR` — mostrare l'importo formattato con simbolo valuta, poi bandiera + codice. | Cell `cash` rifatta: `<amount> <symbol> <flag><code>` con CSS per `tx-cash-amount` (tabular-nums, font-weight 500) e `tx-cash-symbol` (0.75rem, muted). Larghezza colonna alzata a 160px. | ✅ C6 |
| W46 | ⚠ UX | Filtro `type` e `broker` dovrebbero essere generalizzabili anche per `/files?tab=brim` (stessa UI con icone + nomi plugin/broker). Nella pagina files, accanto al nome broker, mettere l'icona broker. | `EnumOption.iconUrl` è ora generico in `types.ts` — riusabile da qualsiasi pagina che passa `enumOptions` con `iconUrl`. `/files` BRIM cablaggio → deferred Round 2. | ⏳ deferred /files |

### Fix plan Round 1.3

Batch di fix in ordine di priorità:

- **C1 (W34) ✅** — i18n: aggiunta chiave `table.filterLabel` in 4 lingue; `DataTableColumnFilter.svelte` riga 527 + 754 usano `$t('table.filterLabel')` anziché `$t('table.filter')`.
- **C2 (W41) ✅** — Pagination: rimossi `limit/offset` dalla query `loadMainRows` (now pulls all TX); condizione visibilità `DataTablePagination` cambiata da `displayRows.length > pageSize` a `totalPages > 1`.
- **C3 (W36, W37) ✅** — Icone asset+broker nella tabella TX:
  - `BrokerLike` esteso con `icon_url?/portal_url?/default_import_plugin?` in `brokerColors.ts`.
  - `loadBrokers` in `+page.svelte` carica i campi extra dall'API.
  - Cell `asset`: usa `getAssetTypeIconUrl(info.asset_type)` come fallback quando `icon_url` è null — stessa chain di `AssetIcon.svelte` (icon_url → asset-type PNG → plain text).
  - Cell `broker`: `brokerIconUrl()` helper risolve icon_url → portal favicon → null; HTML rende `<img>` con `onerror` fallback al dot colorato.
  - Import aggiunto: `getAssetTypeIconUrl` da `$lib/utils/assetTypes`.
- **C4 (W35) ⏳** — Colori dark mode: verifica visiva in corso; i valori CSS `color-mix` dark 38%/48% sono presenti e corretti, possibile problema di rendering nel contesto specifico — deferred a verifica visiva.
- **C5 (W42, W43, W44) ✅** — Event dot: wrapper `<div class="tx-event-cell">` con flexbox centering; colonna `event` spostata tra `typeIcon` e `broker` nell'array `columns`; colonna `links` rimossa interamente; funzionalità `🔗` → row action `linked-pair` (icona Link2, visibile solo per TX con partner).
- **C6 (W52, W51) ✅** — Cash cell refactor: eliminare duplicazione codice valuta, fix flag async
- **C7 (W50) ✅** — BrokerBadge component generalizzato + cablare in `/files?tab=brim`
- **C8 (W53) ⏳** — FilterPanel generico per asset, broker, tag nella tabella TX
- **C9 (W56) ✅** — Mobile responsive: iconizzare pulsanti Import/Add su schermi piccoli

---

## 🔁 Walkthrough Round 1.4 — Feedback post-walkthrough visivo (2026-04-27)

| ID | Severity | Descrizione | Action | Status |
|----|----------|-------------|--------|--------|
| W57 | ⚠ UX | Filtro broker: quando il broker non ha icona c'è uno spazio bianco fastidioso. Servire il puntino colorato come fallback (identico alla cella broker nella tabella). | Aggiunto `dotColor` a `EnumOption`; broker enumOptions con dot colorato quando iconUrl assente. CSS `.enum-option-dot` in DataTableColumnFilter. | ✅ C2 |
| W58 | ⚠ UX | Filtro prezzo multi-valuta (`currency-stack`) esteso anche alla tabella `/assets/` nella colonna "ultimo prezzo". Formattare i numeri come in transactions: `[simbolo]|bandiera|iso3`. | Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()`. AssetTable lastPrice ora `type:'currency-stack'` con `getCurrencyValue`, formattazione unificata. | ✅ C3 |
| W59 | ❌ bug | In `/assets/` manca il titolo tradotto della colonna `name` (`assets.table.name`). Header sparito. | Chiave `assets.table.name` aggiunta in 4 lingue via `./dev.py i18n add`. | ✅ C4 |
| W60 | ❌ bug | Paginazione non mostrata in `/transactions` nonostante 21 TX. Custom paginator `totalPages > 1` ma `pageSize` default 50 ≥ 21 → 1 pagina sola → nascosta. L'utente si aspetta di **vederla sempre** (come feedback per "tot risultati"). | Condizione cambiata a `displayRows.length > 0`. | ✅ C1 |
| W61 | ⚠ UX | Icona tipo TX: ha tooltip in `title` HTML nativo ma deve usare `Tooltip.svelte`. Desktop: hover=tooltip, click→doc wiki. Mobile: click=tooltip, longpress→doc. | Rimosso `title` HTML, aggiunto `tooltip` nella HtmlCell. Type icon ora `<a href>` nativo (no click delegation). Rimossi handler dblclick/pointer/coarsePointer. | ✅ C5 |
| W62 | ⚠ UX | Evento tooltip mostra solo "Linked event" generico. Il piano originale prevedeva bulk event query `POST /assets/events/query` con `{ids}` per alimentare `eventTooltipMap`. Feature mancante nel backend (non esiste endpoint by-event-id) — da implementare come `GET /assets/events?ids=...` o bulk query variant. | Endpoint `GET /api/v1/assets/events?ids=...` già esisteva. Import refactored (top-level). `loadEventTooltipMap()` ora chiama endpoint reale. `eventTooltipText()` arricchito con notes e icona ⚙ per auto-events. | ✅ C11 |
| W63 | ⚠ UX | Colonna `actions` sempre visibile/sticky. Solo la colonna `select` deve essere sticky; `actions` deve scrollare con le altre colonne. | Aggiunto prop `stickyActions?: boolean` a DataTable (default true). TransactionsTable usa `stickyActions={false}`. | ✅ C6 |
| W64 | ⚠ UX | Asset collegati (linked assets) creati in DB population non mostrati nel frontend come pianificato nel piano originale (Step 5, ghost row con chip etc.). Da verificare se i dati sono presenti e se la logica di rendering funziona. | Verificare `populate_mock_data.py` per TX con `related_transaction_id` e testare visivamente la ghost row. Se i dati mancano → aggiungere TX linked in mocking. | ⏳ verify |
| W65 | ⚠ UX mobile | Pulsanti header (refresh, vis toggle, import, add) disallineati in mobile: tooltip a destra, icone decentrate e troppo larghe. Upload e Add devono avere icone centrate, padding uniforme. | Tutti i bottoni ora `flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs` con `size={15}` su icone. `ml-auto` allinea a destra. | ✅ C7 |
| W66 | 🔍 refactor | Codice duplicato: logica cash cell (`formatCash` + `getCurrencyInfo` + symbol/flag rendering) è identica tra TX e assets — fattorizzare in helper `formatCurrencyAmount()` riusabile. Broker icon chain (inline HTML con onerror) duplicata tra TransactionsTable broker cell e enum options e files — fattorizzare `brokerIconHtml()`. | Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()`. Usato in AssetTable. TX usa ancora logica inline (da unificare in Round 2). | ✅ partial |

### Fix plan Round 1.4

Batch di fix in ordine di priorità:

- **C1 (W60) ✅** — Pagination sempre visibile: condizione `displayRows.length > 0` anziché `totalPages > 1`.
- **C2 (W57) ✅** — Broker filter dot fallback: aggiunto `dotColor` a `EnumOption` in `types.ts`. UI `DataTableColumnFilter` enum ora rende `.enum-option-dot` quando `dotColor` presente e `iconUrl` assente. CSS per dark mode. TransactionsTable broker `enumOptions` ora include `dotColor` = `getBrokerColor().bg` quando `iconUrl` è null.
- **C3 (W58, W66) ✅** — Multi-currency price in assets table:
  - Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()` (symbol/flag/code pattern unificato, no duplicazione).
  - `AssetTable.svelte` lastPrice ora `type:'currency-stack'` con `getCurrencyValue`, formattazione via helper condiviso. Import `currencyStoreVersion` per re-render async.
- **C4 (W59) ✅** — Asset table title: chiave `assets.table.name` aggiunta in 4 lingue via `./dev.py i18n add`.
- **C5 (W61) ✅** — Type icon tooltip con Tooltip.svelte:
  - Cell typeIcon ora ha `tooltip: {text: label, position: 'top'}` e usa `<a href>` nativo per navigazione wiki.
  - Rimossi handler `dblclick`/`pointerdown`/`pointerEnd` e `isCoarsePointer` detection (non più necessari).
  - CSS aggiunto `text-decoration: none` su `.tx-type-icon-link`.
- **C6 (W63) ✅** — Actions column non sticky: aggiunto prop `stickyActions?: boolean` (default `true`) a DataTable. TransactionsTable usa `stickyActions={false}`.
- **C7 (W65) ✅** — Mobile buttons: tutti i bottoni con padding uniforme `px-2.5 py-1.5 text-xs`, icone `size={15}`, `justify-center gap-1`. Container con `ml-auto` per allineamento a destra.
- **C8 (W62) ✅** — Event tooltip con dati reali: endpoint `GET /assets/events?ids=...` già presente. Import refactored al top-level. `loadEventTooltipMap()` wired. `eventTooltipText()` arricchito.
- **C9 (W64) ⏳ verify** — Linked assets / ghost rows: verifica dati mock pendente.
- **C10 (W66) ✅ partial** — Refactor codice duplicato: creato `currencyFormat.ts` condiviso. TX cash cell resta inline (da unificare in Round 2). Broker icon chain non ancora fattorizzata.

**Validazione**: `./dev.py front format` → clean; `./dev.py front check` → 0/0 ✅; `./dev.py i18n audit` → 941 keys, 0 incomplete ✅.

**Residui aperti Round 1.4**:
- **W53** ⏳ — FilterPanel generico per asset, broker, tag (deferred Round 2).
- **W54** ⏳ — Dark mode: verifica visiva pending (serve server running).


---

## 🔁 Walkthrough Round 1.5 — Feedback post-walkthrough visivo (2026-04-27)

| ID | Severity | Descrizione | Action | Status |
|----|----------|-------------|--------|--------|
| W57 | ⚠ UX | Filtro broker: quando il broker non ha icona c'è uno spazio bianco fastidioso. Servire il puntino colorato come fallback (identico alla cella broker nella tabella). | Aggiunto `dotColor` a `EnumOption`; broker enumOptions con dot colorato quando iconUrl assente. CSS `.enum-option-dot` in DataTableColumnFilter. | ✅ C2 |
| W58 | ⚠ UX | Filtro prezzo multi-valuta (`currency-stack`) esteso anche alla tabella `/assets/` nella colonna "ultimo prezzo". Formattare i numeri come in transactions: `[simbolo]|bandiera|iso3`. | Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()`. AssetTable lastPrice ora `type:'currency-stack'` con `getCurrencyValue`, formattazione unificata. | ✅ C3 |
| W59 | ❌ bug | In `/assets/` manca il titolo tradotto della colonna `name` (`assets.table.name`). Header sparito. | Chiave `assets.table.name` aggiunta in 4 lingue via `./dev.py i18n add`. | ✅ C4 |
| W60 | ❌ bug | Paginazione non mostrata in `/transactions` nonostante 21 TX. Custom paginator `totalPages > 1` ma `pageSize` default 50 ≥ 21 → 1 pagina sola → nascosta. L'utente si aspetta di **vederla sempre** (come feedback per "tot risultati"). | Condizione cambiata a `displayRows.length > 0`. | ✅ C1 |
| W61 | ⚠ UX | Icona tipo TX: ha tooltip in `title` HTML nativo ma deve usare `Tooltip.svelte`. Desktop: hover=tooltip, click→doc wiki. Mobile: click=tooltip, longpress→doc. | Rimosso `title` HTML, aggiunto `tooltip` nella HtmlCell. Type icon ora `<a href>` nativo (no click delegation). Rimossi handler dblclick/pointer/coarsePointer. | ✅ C5 |
| W62 | ⚠ UX | Evento tooltip mostra solo "Linked event" generico. Il piano originale prevedeva bulk event query `POST /assets/events/query` con `{ids}` per alimentare `eventTooltipMap`. Feature mancante nel backend (non esiste endpoint by-event-id) — da implementare come `GET /assets/events?ids=...` o bulk query variant. | Endpoint `GET /api/v1/assets/events?ids=...` già esisteva. Import refactored (top-level). `loadEventTooltipMap()` ora chiama endpoint reale. `eventTooltipText()` arricchito con notes e icona ⚙ per auto-events. | ✅ C11 |
| W63 | ⚠ UX | Colonna `actions` sempre visibile/sticky. Solo la colonna `select` deve essere sticky; `actions` deve scrollare con le altre colonne. | Aggiunto prop `stickyActions?: boolean` a DataTable (default true). TransactionsTable usa `stickyActions={false}`. | ✅ C6 |
| W64 | ⚠ UX | Asset collegati (linked assets) creati in DB population non mostrati nel frontend come pianificato nel piano originale (Step 5, ghost row con chip etc.). Da verificare se i dati sono presenti e se la logica di rendering funziona. | Verificare `populate_mock_data.py` per TX con `related_transaction_id` e testare visivamente la ghost row. Se i dati mancano → aggiungere TX linked in mocking. | ⏳ verify |
| W65 | ⚠ UX mobile | Pulsanti header (refresh, vis toggle, import, add) disallineati in mobile: tooltip a destra, icone decentrate e troppo larghe. Upload e Add devono avere icone centrate, padding uniforme. | Tutti i bottoni ora `flex items-center justify-center gap-1 px-2.5 py-1.5 text-xs` con `size={15}` su icone. `ml-auto` allinea a destra. | ✅ C7 |
| W66 | 🔍 refactor | Codice duplicato: logica cash cell (`formatCash` + `getCurrencyInfo` + symbol/flag rendering) è identica tra TX e assets — fattorizzare in helper `formatCurrencyAmount()` riusabile. Broker icon chain (inline HTML con onerror) duplicata tra TransactionsTable broker cell e enum options e files — fattorizzare `brokerIconHtml()`. | Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()`. Usato in AssetTable. TX usa ancora logica inline (da unificare in Round 2). | ✅ partial |

### Fix plan Round 1.5

Batch di fix in ordine di priorità:

- **C1 (W60) ✅** — Pagination sempre visibile: condizione `displayRows.length > 0` anziché `totalPages > 1`.
- **C2 (W57) ✅** — Broker filter dot fallback: aggiunto `dotColor` a `EnumOption` in `types.ts`. UI `DataTableColumnFilter` enum ora rende `.enum-option-dot` quando `dotColor` presente e `iconUrl` assente. CSS per dark mode. TransactionsTable broker `enumOptions` ora include `dotColor` = `getBrokerColor().bg` quando `iconUrl` è null.
- **C3 (W58, W66) ✅** — Multi-currency price in assets table:
  - Creato `$lib/utils/currencyFormat.ts` con `formatCurrencyAmountHtml()` (symbol/flag/code pattern unificato, no duplicazione).
  - `AssetTable.svelte` lastPrice ora `type:'currency-stack'` con `getCurrencyValue`, formattazione via helper condiviso. Import `currencyStoreVersion` per re-render async.
- **C4 (W59) ✅** — Asset table title: chiave `assets.table.name` aggiunta in 4 lingue via `./dev.py i18n add`.
- **C5 (W61) ✅** — Type icon tooltip con Tooltip.svelte:
  - Cell typeIcon ora ha `tooltip: {text: label, position: 'top'}` e usa `<a href>` nativo per navigazione wiki.
  - Rimossi handler `dblclick`/`pointerdown`/`pointerEnd` e `isCoarsePointer` detection (non più necessari).
  - CSS aggiunto `text-decoration: none` su `.tx-type-icon-link`.
- **C6 (W63) ✅** — Actions column non sticky: aggiunto prop `stickyActions?: boolean` (default `true`) a DataTable. TransactionsTable usa `stickyActions={false}`.
- **C7 (W65) ✅** — Mobile buttons: tutti i bottoni con padding uniforme `px-2.5 py-1.5 text-xs`, icone `size={15}`, `justify-center gap-1`. Container con `ml-auto` per allineamento a destra.
- **C8 (W62) ✅** — Event tooltip con dati reali: endpoint `GET /assets/events?ids=...` già presente. Import refactored al top-level. `loadEventTooltipMap()` wired. `eventTooltipText()` arricchito.
- **C9 (W64) ⏳ verify** — Linked assets / ghost rows: verifica dati mock pendente.
- **C10 (W66) ✅ partial** — Refactor codice duplicato: creato `currencyFormat.ts` condiviso. TX cash cell resta inline (da unificare in Round 2). Broker icon chain non ancora fattorizzata.

**Validazione**: `./dev.py front format` → clean; `./dev.py front check` → 0/0 ✅; `./dev.py i18n audit` → 941 keys, 0 incomplete ✅.

**Residui aperti Round 1.5**:
- **W62** ⏳ — Event tooltip con dati reali (richiede endpoint backend).
- **W64** ⏳ — Linked assets / ghost rows: verifica dati mock.
- **W66** partial — brokerIconHtml() fattorizzazione + TX cash cell unificazione (Round 2).

---

## Round 1.6 — Refactoring & Event Wiring

### Recap lavoro fatto in Round 1.5 e prima

1. **`getTxTypeDocUrl()` semplificato** (da Round 1.5): rimosso il blocco if che rilevava porta 5173 e redirigeva a :8000. Ora restituisce direttamente il path relativo `/mkdocs/...` — il backend serve sempre il sito statico.

2. **`getBrokerIconUrl()` fattorizzato** (da Round 1.5): creato `$lib/utils/brokerHelpers.ts` con `getBrokerIconUrl(broker)` e `getBrokerIconUrlById(id, collection)`. Usato in:
   - `TransactionsTable.svelte` (import + uso in broker cell + broker enumOptions)
   - `FilesTable.svelte` (import + uso in broker cell + broker enumOptions)
   - `BrokerBadge.svelte` (import + uso nel rendering icona)

3. **`formatCurrencyAmountHtml()` condiviso** (da Round 1.5): creato `$lib/utils/currencyFormat.ts`. Usato in `AssetTable.svelte` (lastPrice column).

### Lavoro Round 1.6

| # | Fix | Dettaglio | Status |
|---|-----|-----------|--------|
| C11 | W62 — Event tooltip con dati reali | Endpoint `GET /api/v1/assets/events?ids=...` già esisteva nel backend (`asset_source.py:get_events_by_ids`). Import lazy inline spostato al top-level (`FAEventQueryResult` aggiunto in import). API sync eseguito (`./dev.py api sync`). Frontend `loadEventTooltipMap()` ora chiama endpoint reale, raccoglie `asset_event_id` univoci dalle TX, costruisce `Map<eventId, AssetEvent>` con type/date/value/currency/is_auto/notes. `eventTooltipText()` migliorato con notes e icona ⚙ per auto-events. | ✅ |

### Validazione Round 1.6

- `./dev.py front check` → 0 errors, 0 warnings ✅
- `./dev.py api sync` → endpoint generato in `generated.ts` ✅
- `ruff check` + `black` → backend clean ✅
- `prettier` → frontend clean ✅

### Residui aperti dopo Round 1.6

| Issue | Stato | Note |
|-------|-------|------|
| **W64** — Linked assets / ghost rows | ⏳ verify | Verificare dati mock per TX con `related_transaction_id`. Ghost row viola visibile ma chip "out of filter" (Step 5 piano originale) non implementato. |
| **W66 partial** — TX cash cell → `formatCurrencyAmountHtml()` | ⏳ Round 2 | TransactionsTable `formatCash()` ancora inline. Da unificare col helper condiviso in un futuro refactor. |
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | La tinta viola c'è ma le interazioni (chip che mostra quale filtro ha escluso + bottoni ✕/+) non sono implementate. |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT — deferred a phase 7 final. |


---

## Round 1.7 — Pagination fix, event emoji, currency ISO3, refresh reset

### Issues reportati

| # | Sev | Descrizione | Fix | Status |
|---|-----|-------------|-----|--------|
| W67 | 🐛 compilazione | IDE error: `as const` in Svelte template expression (line 571 `+page.svelte`) non valido nella sintassi Svelte. | Rimosso `as const`, lasciato come string literal `'danger'`. | ✅ C12 |
| W68 | ⚠ UX | `currencyFormat.ts`: manca ISO3 code dopo la bandiera. Quando il simbolo esiste mostra `amount symbol flag` ma non il codice ISO3. | Aggiunto `codeHtml` dopo `flagHtml` in tutti i casi: `amount symbol flag CODE` o `amount flag CODE`. | ✅ C13 |
| W69 | ⚠ UX | Event tooltip: mancano emoji tipo evento (💰/📈/✂️/📊/🏁). Valori non arrotondati a 2 cifre decimali. | Creato `$lib/utils/eventTypes.ts` con `getEventTypeEmoji()`. Usato in `eventTooltipText()` + `AssetDataEditorSection`. Valore arrotondato con `toLocaleString(2,2)`. | ✅ C14 |
| W70 | 🐛 grave | Paginazione non riflette i filtri: filtro riduce righe visibili ma `totalItems` resta su `displayRows.length` (non filtrato). Pagine vuote dopo filtro. | Aggiunto `filteredDisplayRows` derived che applica `activeColumnFilters` a `displayRows` prima del paginator. Pagination ora usa `filteredDisplayRows.length`. `activeColumnFilters` tracciato internamente via `handleFiltersChangeInternal`. | ✅ C15 |
| W71 | ⚠ UX | Refresh non resetta i filtri colonna. | Bottone refresh ora chiama `transactionsTableComponent?.resetFilters()` + resetta `filters` URL state. Aggiunto `clearFilters()` a DataTable. | ✅ C16 |

### Dettagli implementativi

**C12 — IDE error `as const`**: Svelte template parser non supporta `as const` inline. Rimosso; il tipo `'danger'` viene inferito come string literal dal contesto.

**C13 — Currency format ISO3**: `currencyFormat.ts` ora mostra sempre il codice ISO3 dopo la bandiera:
- Con simbolo: `+1,234.56 € 🇪🇺EUR`
- Senza simbolo: `+1,234.56 🇺🇸USD`

**C14 — Event type emoji factoring**: Creato `$lib/utils/eventTypes.ts`:
- `getEventTypeEmoji(type)` → mappa `DIVIDEND→💰`, `INTEREST→📈`, `SPLIT→✂️`, `PRICE_ADJUSTMENT→📊`, `MATURITY_SETTLEMENT→🏁`, fallback `📌`
- `AssetDataEditorSection` refactored per usare `getEventTypeEmoji()` (era hardcoded)
- `eventTooltipText()` ora mostra: `💰 DIVIDEND · 2025-07-31 · 0.25 USD · "Quarterly dividend" · ⚙ auto`

**C15 — Pagination ↔ filter sync** (fix architetturale):
Il problema: TransactionsTable ha la propria paginazione pair-never-split che opera su `displayRows` (non filtrati). DataTable filtra internamente ma solo i dati della pagina corrente — la paginazione non vede i risultati filtrati.

Soluzione: aggiunto layer `filteredDisplayRows` che applica `activeColumnFilters` **prima** del paginator. La catena è ora:
```
mainRows → displayRows (pair-adjacent) → filteredDisplayRows (column filters) → pages (pair-never-split) → visibleRows → DataTable
```
DataTable applica gli stessi filtri internamente ma è un no-op (dati già filtrati).

Nuovo state `activeColumnFilters` inizializzato da `initialFilters`, aggiornato via `handleFiltersChangeInternal()` (intercetta `onFiltersChange` di DataTable → aggiorna locale + forward al parent).

**C16 — Refresh reset filters**: Bottone refresh ora:
1. Chiama `transactionsTableComponent?.resetFilters()` che resetta `activeColumnFilters = {}` + `tableRef.clearFilters()`
2. Resetta filtri URL in `+page.svelte` (`types`, `tags`, `broker_id`, `date_start`, `date_end`, `cash`, `page`)
3. Poi chiama `reload()`

Aggiunto `clearFilters()` export in `DataTable.svelte`.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/routes/(app)/transactions/+page.svelte` | Rimosso `as const`, refresh resetta filtri |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | `activeColumnFilters`, `filteredDisplayRows`, `handleFiltersChangeInternal`, `resetFilters`, emoji import, tooltip migliorato |
| `frontend/src/lib/components/table/DataTable.svelte` | Aggiunto `clearFilters()` export |
| `frontend/src/lib/utils/currencyFormat.ts` | Aggiunto ISO3 code dopo flag |
| `frontend/src/lib/utils/eventTypes.ts` | **NUOVO** — `getEventTypeEmoji()` factored |
| `frontend/src/lib/components/assets/AssetDataEditorSection.svelte` | Usa `getEventTypeEmoji()` (refactor emoji hardcoded) |

### Validazione Round 1.7

- `./dev.py front check` → 0 errors, 2 warnings (intentional: `initialFilters` capture) ✅
- `prettier` → tutto clean ✅

### Residui aperti dopo Round 1.7

| Issue | Stato | Note |
|-------|-------|------|
| **W64** — Linked assets / ghost rows | ⏳ verify | Verificare dati mock per TX con `related_transaction_id`. Ghost row viola c'è ma le interazioni (chip che mostra quale filtro ha escluso + bottoni ✕/+) non sono implementate. |
| **W66 partial** — TX cash cell → `formatCurrencyAmountHtml()` | ✅ C19 | Risolto in Round 1.8. |
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | La tinta viola c'è ma le interazioni (chip che mostra quale filtro ha escluso + bottoni ✕/+) non sono implementate. |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT — deferred a phase 7 final. |

---

## Round 1.8 — Enum filter stability, currency unification, selection reset, IDE errors

### Issues reportati

| # | Sev | Descrizione | Fix | Status |
|---|-----|-------------|-----|--------|
| W72 | 🐛 compilazione | `DataTableColumnFilter.svelte`: 4 errori IDE per `as HTMLInputElement` cast in template Svelte (non valido). | Rimossi i cast `as HTMLInputElement`, uso `e.currentTarget.value` direttamente. | ✅ C17 |
| W73 | 🐛 grave | Filtro tipo TX: una volta deselezionato un tipo, sparisce dall'elenco e non è più riselezionabile. Causa: `getEnumOptionsWithCounts()` in DataTable faceva `.filter(o => o.count > 0)` sulle opzioni, eliminando quelle con count 0. | Rimosso `.filter(o => o.count > 0)` — le opzioni sono definite dal parent via `enumOptions`, i conteggi a 0 vengono mostrati ma non rimossi. | ✅ C18 |
| W74 | ⚠ UX | Cash cell TX non usa `formatCurrencyAmountHtml()` condiviso — mostra `€ 🇪🇺` senza EUR code, e `🇺🇸USD` senza `$` symbol. | Cash cell ora usa `formatCurrencyAmountHtml(n, code, {showSign: true})`. Rimossa logica inline duplicata. Import `getCurrencyInfo` rimosso (non più usato). | ✅ C19 |
| W75 | ⚠ UX | Event tooltip non usa `formatCurrencyAmountHtml()` — mostra `0.25 USD` senza symbol/flag. | `eventTooltipText()` ora genera con `formatCurrencyAmountHtml` (stripping HTML tags per tooltip plain-text). | ✅ C20 |
| W76 | ⚠ UX | Refresh non resetta la selezione. Toolbar continua a mostrare "N selected" dopo il refresh. | Refresh ora chiama `clearSelection()` e resetta `selectedRows = []` prima di reload. | ✅ C21 |

### Dettagli implementativi

**C17 — DataTableColumnFilter `as` casts**: Svelte template parser non supporta TypeScript `as` casts in espressioni inline. Le 4 occorrenze nelle currency-stack range inputs usavano `(e.currentTarget as HTMLInputElement).value`. Cambiato in `e.currentTarget.value` direttamente — il tipo è corretto dato che `e` è un InputEvent su un `<input>`.

**C18 — Enum filter stability** (root cause analysis):
- `DataTable.getEnumOptionsWithCounts()` line 423: computava conteggi da `data` (che è `visibleRows`, la pagina filtrata), poi faceva `.filter(o => o.count > 0)` → tipi con count 0 sparivano
- Il parent (TransactionsTable) fornisce `enumOptions` con TUTTI i tipi presenti nel dataset completo (via `TX_TYPES.filter(tt => mainRows.some(...))`)
- Fix: rimosso il `.filter()`, le opzioni restano tutte visibili con conteggio 0 quando filtrate
- Questo allinea il comportamento a `/assets` dove i filtri non scompaiono

**C19 — Cash cell unificata**: La cell `cash` in TransactionsTable aveva ~15 righe di logica inline duplicata da `currencyFormat.ts`. Ora usa `formatCurrencyAmountHtml(n, code, {showSign: true})` direttamente. Output: `$ 🇺🇸USD` per USD, `€ 🇪🇺EUR` per EUR, `🇷🇴RON` per RON (senza simbolo). Questo chiude il residuo W66.

**C20 — Event tooltip currency**: `eventTooltipText()` ora genera il fragment HTML con `formatCurrencyAmountHtml`, poi strappa i tag HTML con `.replace(/<[^>]*>/g, '')` per il tooltip plain-text. Risultato: `💰 DIVIDEND · 2025-07-31 · 0.25 $ 🇺🇸USD · "notes"`.

**C21 — Selection reset on refresh**: Aggiunto `clearSelection()` + `selectedRows = []` nel handler `onclick` del bottone refresh, prima di `reload()`.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/table/DataTableColumnFilter.svelte` | Rimossi 4 cast `as HTMLInputElement` |
| `frontend/src/lib/components/table/DataTable.svelte` | Rimosso `.filter(o => o.count > 0)` da `getEnumOptionsWithCounts()` |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Cash cell → `formatCurrencyAmountHtml`, event tooltip → `formatCurrencyAmountHtml`, rimosso import `getCurrencyInfo` |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Refresh ora resetta selezione |

### Validazione Round 1.8

- `./dev.py front check` → 0 errors, 2 warnings (intentional) ✅
- `prettier` → tutto clean ✅

### Residui aperti dopo Round 1.8

| Issue | Stato | Note |
|-------|-------|------|
| **W64** — Linked assets / ghost rows | ⏳ verify | Verificare dati mock per TX con `related_transaction_id`. |
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | La tinta viola c'è ma le interazioni non sono implementate. |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT. |

---

## Round 1.9 — Open points (verifica e documentazione)

### Issues aperti da risolvere

| # | Sev | Descrizione | Root cause | Fix proposto | Status |
|---|-----|-------------|------------|-------------|--------|
| W77 | ⚠ UX | Cash cell e event tooltip: USD mostra `-5,00 🇺🇸USD` senza simbolo `$`. L'utente si aspetta `$ 🇺🇸USD`. Lo stesso per CHF (no `Fr.`), GBP (symbol vuoto!). EUR funziona (`€`). | **Babel locale-dependent**: con `locale='it'`, `get_currency_symbol('USD')` restituisce `'USD'` (identico al code), non `'$'`. È il comportamento corretto di Babel per l'italiano. `hasRealSymbol = symbol !== code` → `false` → path senza simbolo. | Due opzioni: **(A)** Usare `locale='en'` per il symbol lookup nel backend (il simbolo `$` è universale). **(B)** Aggiungere una mappa fallback hardcoded nel frontend per i 5-6 simboli universali (`USD→$`, `GBP→£`, `JPY→¥`, `CHF→Fr.`, `CNY→¥`). Opzione A è più pulita. | ⏳ |
| W78 | 🐛 compilazione | `DataTable.svelte` line 1228: `as (r?: T) => string` — TypeScript cast non valido in template Svelte (stessa classe di errore di W67/W72). | Svelte template parser non supporta `as` cast inline. | Estrarre in helper function: `function getActionTitle(action, row) { ... }`. | ⏳ |
| W79 | ⚠ build warning | `TransactionsTable.svelte` line 147: Svelte avverte che `initialFilters` è referenziato in `$state()` init ma cattura solo il valore iniziale. Warning ripetuto 2× in check e 4× in build (SSR+client). | Intenzionale: `activeColumnFilters` deve partire dal valore iniziale dei filtri URL, poi essere aggiornato via `handleFiltersChangeInternal`. Ma Svelte non sa che è intenzionale. | Sopprimere con `// svelte-ignore state_referenced_locally` oppure refactorare con `$effect` per sync iniziale. | ⏳ |
| W80 | ⚠ build warning (molti) | `DataTable.svelte` + `DataTableColumnFilter.svelte`: ~60 CSS warnings per `:global(.dark) .xxx` selectors marcati "Selector dark is never used". | Svelte static analysis non può provare che la classe `.dark` esista a compile-time (è applicata a `<html>` runtime). Sono false positive. | Migrare i selettori `.dark` da `:global(.dark) .local` a forma nesting `:global(.dark) &` Svelte-5, oppure spostare in blocco `:global { .dark .xxx { ... } }` come fatto in `TransactionsTable.svelte`. | ⏳ low priority |
| W81 | ⚠ build warning | `DataTable.svelte`: ~10 export functions marcate "Unused function" (`navigateToRowId`, `toggleColumnVisibilityById`, `clearFilters`, etc.). | Svelte non sa che sono usate esternamente via `bind:this`. | Nessun fix necessario — sono false positive dell'analisi statica. Documentare e ignorare. | ℹ️ ignore |
| W82 | ⚠ UX | Linked transactions (`related_transaction_id`) non visibili: la feature ghost row esiste ma `populate_mock_data.py` non crea nessuna TX di tipo TRANSFER/FX_CONVERSION con partner linkato. | **Missing mock data**: nessuna TX con `related_transaction_id != null` creata nel seeding. | Aggiungere in `populate_mock_data.py` almeno 2 coppie TRANSFER (un broker→altro) e 1 FX_CONVERSION (EUR→USD) con `related_transaction_id` bidirezionale. Poi verificare ghost row rendering. Questo chiude definitivamente W64. | ⏳ |

### Analisi dettagliata W77 — Currency symbol locale issue

Risultati `babel.numbers.get_currency_symbol(code, locale='it')`:

| Currency | Symbol (it) | Symbol == Code | Comportamento attuale | Atteso dall'utente |
|----------|------------|----------------|----------------------|-------------------|
| USD | `'USD'` | ✅ | `🇺🇸USD` | `$ 🇺🇸USD` |
| EUR | `'€'` | ❌ | `€ 🇪🇺EUR` ✅ | `€ 🇪🇺EUR` ✅ |
| RON | `'RON'` | ✅ | `🇷🇴RON` | `🇷🇴RON` ✅ |
| GBP | `''` | ❌ (empty!) | `🇬🇧GBP` | `£ 🇬🇧GBP` |
| CHF | `'CHF'` | ✅ | `🇨🇭CHF` | `Fr. 🇨🇭CHF` o `🇨🇭CHF` |

Il problema è che Babel localizza anche i simboli valuta: in italiano non si usa `$` per il dollaro, si scrive "USD". La soluzione pulita è chiedere al backend di restituire il simbolo in `locale='en'` (che è universale per i simboli finanziari), oppure exporre un campo `compact_symbol` separato.

### Piano esecuzione Round 1.9

1. **W78** — Fix `as` cast in DataTable.svelte (1 riga, quick fix)
2. **W79** — Sopprimere warning `state_referenced_locally` in TransactionsTable
3. **W77** — Fix currency symbol (decidere approccio A vs B, implementare)
4. **W82** — Aggiungere TX linked in mock data + verificare ghost rows
5. **W80/W81** — Low priority: CSS warnings e unused exports — documentare, non fixare ora

---

## Round 1.9 — Execution Report

### Fixes implementati

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| W77 | Currency symbol locale-dependent (`$` non mostrato per USD con locale `it`) | **Opzione A**: backend `list_currencies()` ora usa `locale='en'` per il symbol lookup (via `en_locale`), mantenendo il locale utente per il `name`. Simboli universali (`$`, `£`, `¥`, `Fr.`) ora corretti per tutte le lingue. | ✅ C22 |
| W78 | `as (r?: T) => string` cast in template Svelte (DataTable.svelte:1228) | Rimosso il cast — `action.label(row)` funziona direttamente dato che TypeScript inferisce il tipo dalla union dopo il `typeof` guard. | ✅ C23 |
| W79 | Warning `state_referenced_locally` per `initialFilters` in TransactionsTable | Aggiunto `// svelte-ignore state_referenced_locally` sopra la riga. Il pattern è intenzionale. | ✅ C24 |
| W82 | No TX con `related_transaction_id` nei mock data → ghost row non verificabili | Aggiunte 3 coppie linked in `populate_mock_data.py`: 2× TRANSFER (AAPL IB→DEGIRO, BTC Coinbase→IB) + 1× FX_CONVERSION (EUR→USD at IB). Tutte con FK bidirezionale. | ✅ C25 |
| W80 | ~60 CSS warnings `:global(.dark)` in DataTable/DataTableColumnFilter | Documentato: false positive dell'analisi statica Svelte. `.dark` è applicata a `<html>` a runtime. Non fixato — low priority. | ℹ️ ignore |
| W81 | ~10 unused export warnings in DataTable | Documentato: usate esternamente via `bind:this`. False positive. | ℹ️ ignore |

### Dettagli implementativi

**C22 — Currency symbol locale fix** (root cause + fix):
- Babel `get_currency_symbol('USD', locale='it')` → `'USD'` (non `'$'`), perché in italiano il dollaro si scrive "USD"
- Fix: `list_currencies()` ora crea un `en_locale = get_babel_locale("en")` e lo usa solo per `get_currency_symbol(code, locale=en_locale)`
- Il `name` continua a usare il locale utente → "Dollaro statunitense" in italiano
- Risultato frontend: `$ 🇺🇸USD` per USD, `£ 🇬🇧GBP` per GBP, `¥ 🇯🇵JPY` per JPY

**C23 — DataTable `as` cast removal**: Svelte template parser non supporta TypeScript `as` inline. Il `typeof action.label === 'function'` guard è sufficiente per TypeScript a narroware il tipo, rendendo `action.label(row)` valido senza cast.

**C24 — state_referenced_locally suppression**: Il commento `// svelte-ignore state_referenced_locally` sopprime il warning Svelte che `initialFilters` è catturato dal `$state()` init. È intenzionale: il valore iniziale viene usato solo all'init, poi `handleFiltersChangeInternal()` aggiorna lo state.

**C25 — Linked transactions mock data**: Creati dopo la `session.commit()` principale delle TX normali. Pattern:
1. Crea i due TX della coppia senza `related_transaction_id`
2. `session.flush()` per assegnare gli ID
3. Assegna `tx_a.related_transaction_id = tx_b.id` e viceversa
4. `session.commit()`

### File modificati

| File | Modifica |
|------|----------|
| `backend/app/utils/currency_utils.py` | `en_locale` per symbol lookup universale |
| `frontend/src/lib/components/table/DataTable.svelte` | Rimosso `as` cast da action title |
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | `svelte-ignore state_referenced_locally` |
| `backend/test_scripts/test_db/populate_mock_data.py` | 3 coppie linked TX (TRANSFER×2, FX_CONVERSION×1) |

### Validazione Round 1.9

- `./dev.py front check` → **0 errors, 0 warnings** ✅ (migliorato da 2 warnings)
- `prettier --check` → clean (2 file preesistenti non in scope) ✅
- `ruff check` backend → All checks passed ✅

### Residui aperti dopo Round 1.9

| Issue | Stato | Note |
|-------|-------|------|
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | La tinta viola c'è ma le interazioni (chip + bottoni ✕/+) non sono implementate. |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT. |
| **W82 verify** | ⏳ | Rieseguire `./dev.py test db populate --force` e verificare ghost row rendering con le nuove TX linked. |

---

## Round 1.10 — Execution Report

### Fixes implementati

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| C26 | Currency-stack filter instabile: `items.length === 0` non gestito, `min`/`max` undefined causavano crash | Stabilizzato filtraggio `currency-stack`: `items.length === 0` → skip filtro; bounds undefined → nessun limite (passano sempre). | ✅ C26 |
| C27 | Colonna `asset` usava filtro `text` generico — non permetteva selezione dropdown | Cambiato a `type: 'enum'` con `enumOptions` auto-generate da `mainRows` (display_name, icon_url, fallback asset-type PNG). Valore `__null__` per TX senza asset. | ✅ C27 |
| C28 | Tags: filtro generico non permetteva selezione multipla con dot colorati | Tags column ora `type: 'multi-enum'` con `enumOptions` generate dal set unico di tags, `dotColor` da `getStringColor()`, e `getMultiValue` per filtraggio multi-valore. | ✅ C28 |
| C29 | Colonna `event` separata ridondante — info event e linked pair sparse | Unificata in colonna **"Links"** (`id: 'links'`): event dot (🔴) + direction arrow (⬆/⬇) + link icon (🔗). Click delegation via `data-tx-link` e `data-tx-event`. | ✅ C29 |

### Dettagli implementativi

**C26 — Currency-stack filter stability**: Il filtro `currency-stack` nella logica `filteredDisplayRows` ora verifica `fv.items.length > 0` prima di applicare. Items con `min`/`max` undefined trattati come "nessun limite" (sempre passano quel bound check).

**C27 — Asset filter → enum**: La colonna `asset` ora ha `type: 'enum'` con `enumOptions` auto-generate:
- Scansiona `mainRows` per `asset_id` unici
- Usa `getAssetInfo()` dal store per `display_name` e `icon_url`
- Fallback a `getAssetTypeIconUrl()` se l'asset non ha icona
- Valore speciale `__null__` per TX senza asset, in cima all'elenco ordinato

**C28 — Multi-enum tags**: La colonna `tags` usa `type: 'multi-enum'` con:
- `getMultiValue: (d) => d.tx.tags ?? []` per restituire array di valori
- `enumOptions` con `dotColor` da `getStringColor(tag).bg`
- Filtraggio multi-enum usa `some()`: riga matcha se ha almeno un tag selezionato

**C29 — Links column**: Sostituisce la vecchia colonna `event`. Aggrega:
1. **Event dot**: `<button class="tx-event-dot">` con tooltip dal nome dell'evento
2. **Pair arrow**: `<span class="tx-pair-arrow">⬆</span>` (receiver) o `⬇` (giver) — solo per TX con `pairAnchorId`
3. **Link icon**: `<button class="tx-link-icon">🔗</button>` con tooltip i18n

Click delegation in `handleTableClick()` distingue `data-tx-link` vs `data-tx-event` per chiamare `onLinkedPairClick` o `onEventBadgeClick`.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Currency-stack filter fix, asset→enum, tags→multi-enum, links column, pair arrows CSS |

### Residui aperti dopo Round 1.10

| Issue | Stato | Note |
|-------|-------|------|
| Visual refinement linked TX (freccia ↳, sfondo viola ghost, pulse click) | ⏳ Round 1.11 | Feedback utente: rimuovere `↳` da qty, usare ⬆⬇ nel Links col, rimuovere sfondo viola ghost, pulse su click 🔗 |

---

## Round 1.11 — Execution Report

### Fixes implementati

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| C30 | Quantità receiver mostrava `↳ +0,1` — prefisso brutto nella cella qty | Rimosso prefisso `↳` da `formatQty()`. Frecce direzionali (⬆⬇) ora nella colonna Links, tra le righe paired. | ✅ C30 |
| C31 | Ghost row aveva sfondo viola `!important` che rompeva uniformità broker tint | Rimosso CSS `.tx-row-ghost` con override viola. Ghost rows ora usano solo `opacity: 0.7`, broker tint uniforme. | ✅ C31 |
| C32 | Click su 🔗 non faceva pulsare la riga partner visivamente | Verificato end-to-end: `handleLinkedPairClick` → `highlight_id` → `tx-row-highlight` → `txPulse` animation. Con pair-adjacent rendering, partner sempre visibile → scroll + pulse funzionano. Auto-clear dopo 1.6s. | ✅ C32 |
| C33 | Pulse non si triggerava: querySelector non trovava ghost rows + animation non si re-triggerava su click ripetuti | Fix querySelector: ora cerca sia `tx-${id}` che `ghost-${id}`. Fix re-trigger: `requestAnimationFrame` clear→set cycle. Fix timer leak: cancel pending clear timer su click ripetuto. | ✅ C33 |

### Dettagli implementativi

**C30 — Remove ↳ prefix from quantity**: `formatQty()` ora è puro: `+N` per positivi, `-N` per negativi, `0` per zero. Nessun prefisso receiver. Frecce direzionali vivono nella colonna Links (C29): `⬆` per receiver, `⬇` per giver. Separazione semantica (direzione) dalla grandezza (quantità).

**C31 — Ghost row: opacity instead of violet**: CSS `.tx-row-ghost > td` applica solo `opacity: 0.7` — niente più `background-color: rgb(139 92 246 / 0.08) !important` né variante dark. Ghost rows ereditano broker tint come tutte le altre, con opacity ridotta per segnalare "fuori filtro".

**C32 — Pulse on 🔗 click**: Flusso end-to-end:
1. Click su `🔗` → `handleTableClick()` trova `data-tx-link` → `onLinkedPairClick(tx)`
2. `+page.svelte` → `handleLinkedPairClick(row)` → `filters.highlight_id = partnerId`
3. `TransactionsTable` prop `highlightId` → `getRowClass()` aggiunge `tx-row-highlight`
4. CSS `animation: txPulse 1.4s ease-in-out 1` → indigo box-shadow pulse
5. `scrollIntoView({behavior: 'smooth', block: 'center'})`
6. `setTimeout(1600ms)` → auto-clear `highlight_id`

Con pair-adjacent rendering la riga partner è già visibile, ma scroll+pulse la evidenzia.

**C33 — Pulse fix (3 bug correlati)**:
- **Bug 1**: `querySelector('[data-row-id="tx-${partnerId}"]')` non trovava ghost rows (che hanno `data-row-id="ghost-${id}"`). Fix: fallback a `ghost-${partnerId}`.
- **Bug 2**: Click ripetuti non ri-triggeravano l'animazione CSS perché `tx-row-highlight` era già applicata. Fix: `requestAnimationFrame` cycle — prima clear `highlight_id`, aspetta un frame, poi re-set.
- **Bug 3**: `setTimeout` di auto-clear poteva accumularsi su click rapidi. Fix: `highlightClearTimer` con `clearTimeout` preventivo.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Rimosso `↳` da `formatQty()`, CSS ghost viola→opacity, mantenuto pulse animation |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Fix `handleLinkedPairClick`: querySelector ghost fallback, rAF re-trigger, timer leak fix |

### Validazione Round 1.11

- Ghost rows uniformi con broker tint + opacity 0.7 ✅
- Frecce ⬆⬇ nella colonna Links (non più nella qty) ✅
- Click 🔗 → pulse indigo sulla riga partner ✅
- Auto-clear highlight dopo 1.6s ✅

### Residui aperti dopo Round 1.11

| Issue | Stato | Note |
|-------|-------|------|
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | Chip interattivo con ✕/+ per rimuovere/aggiungere ghost row ai filtri — design da definire |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT |
| ~~**Event badge click** (`onEventBadgeClick`)~~ | ✅ chiuso | Tooltip è già ricco (emoji+date+amount+notes+auto). Popover dedicato non aggiunge valore. Piano originale aggiornato. |

---

## Round 1.12 — Execution Report

### Fixes implementati

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| C34 | Pulse 🔗 non funzionava: (a) `box-shadow` su `<tr>` non renderizza in tutti i browser, (b) catena reattiva `highlightId` → `getRowClass` → DataTable non propagava perché la function reference non cambiava, (c) querySelector non trovava ghost rows | Riscrittura completa: pulse ora via **manipolazione DOM diretta** (`classList.add/remove` + `offsetWidth` reflow). CSS animation spostata su `<td>`. Rimossa prop `highlightId` e campo `FilterMap.highlight_id` (non più necessari). | ✅ C34 |
| C35 | Colori riga broker troppo sbiaditi — poco distinguibili tra broker diversi | Alzati valori `color-mix`: light 22%→**30%** (hover 32%→42%), dark 38%→**45%** (hover 48%→55%). Commento CSS con istruzioni "TUNE THESE VALUES" per regolazione rapida. | ✅ C35 |
| C36 | Quantità senza indicazione visiva direzione (buy vs sell) | Aggiunto emoji 📈 dopo numeri positivi e 📉 dopo negativi in `formatQty()`. Zero/vuoto resta senza emoji. | ✅ C36 |
| C37 | Dead code: import inutilizzati + sentinel `void` per componenti non più usati | Rimossi: `Calendar1`, `Hash`, `Link2 as LinkIcon`, `TransactionTypeBadge` import + relative sentinel `void`. JSDoc in testa aggiornato. | ✅ C37 |
| C38 | Click delegation: click su 🔗 e ●evt intercettati troppo tardi (dopo DataTable `<tr onclick>` che togglava la selezione riga) | Click handler spostato in **capture phase** via Svelte action `use:captureClick` → `addEventListener('click', handler, true)`. `stopPropagation()` impedisce al click di raggiungere DataTable. | ✅ C38 |
| C39 | Tooltip 🔗 generico ("Go to linked pair") — non spiega il tipo di legame | Nuovo `linkedPairTooltip(d)`: tooltip specifico per tipo TX. TRANSFER: `📥 Ricevuto da {broker}` / `📤 Inviato a {broker}`. FX_CONVERSION: `💱 Convertito da {currency}` / `Conversione in {currency}`. Generico: `🔗 Coppia collegata — Broker1 ↔ Broker2`. 5 chiavi i18n aggiunte (EN/IT/FR/ES). | ✅ C39 |

### Dettagli implementativi

**C34 — Pulse rewrite (root cause × 3)**:

1. **CSS**: `box-shadow` su `<tr>` è inaffidabile — molti browser non renderizzano shadow su table rows. Fix: animazione spostata su `.tx-table-wrap tr.tx-row-highlight > td` (ogni cella dentro il `<tr>` ha la sua animation).

2. **Reattività Svelte 5**: `getRowClass` è una funzione passata come prop a DataTable. Quando `highlightId` (prop di TransactionsTable) cambia, la **function reference** resta la stessa — DataTable non sa che deve ri-valutare `{getRowClass?.(row)}` nel template. La closure cattura `highlightId`, ma DataTable non tracked le dipendenze interne della closure.

3. **querySelector**: cercava solo `[data-row-id="tx-${id}"]` ma ghost rows hanno `data-row-id="ghost-${id}"`.

**Soluzione**: bypass completo della catena reattiva. `handleLinkedPairClick` manipola direttamente il DOM:
```js
el.classList.remove('tx-row-highlight');
void el.offsetWidth;  // force reflow → restart animation
el.classList.add('tx-row-highlight');
el.scrollIntoView({behavior: 'smooth', block: 'center'});
```

Questo elimina la dipendenza dalla reattività per un effetto puramente visivo e temporaneo. La prop `highlightId` e il campo `FilterMap.highlight_id` sono stati rimossi completamente (cleanup: ~20 righe di boilerplate URL encoding/decoding).

Anche `handlePromoteCommitted` è stato aggiornato: ora il pulse avviene dopo `reload().then(...)` via DOM diretto.

**C35 — Broker tint tuning**: I valori sono nel CSS di TransactionsTable, sezione "Whole-row tint". Commento aggiunto: `── TUNE THESE VALUES to adjust row saturation ──`. Per regolare: modificare i `%` nelle funzioni `color-mix()`.

**C36 — Quantity emoji**: `formatQty()` ora appends ` 📈` per n>0 e ` 📉` per n<0. Zero/non-finito resta `'0'` senza emoji.

**C37 — Import cleanup**: Rimossi 4 import inutilizzati (`Calendar1`, `Hash`, `LinkIcon`, `TransactionTypeBadge`) e relative sentinel `void`. Erano residui di round precedenti quando la colonna links usava icone Lucide e il TransactionTypeBadge era nella cella type.

**C38 — Click delegation capture phase**: Il click su 🔗 e ●evt non funzionava perché il click veniva intercettato prima dal `<tr onclick>` di DataTable (che gestisce la selezione riga). Soluzione: Svelte action `use:captureClick` attacca `addEventListener('click', handler, true)` in capture phase → il click arriva prima al nostro handler, che chiama `stopPropagation()` per impedire la propagazione verso DataTable.

**C39 — Context-specific link tooltip**: Funzione `linkedPairTooltip(d)` costruisce un tooltip ricco basato su:
- `d.tx.type` → determina il tipo di legame (TRANSFER, FX_CONVERSION, fallback generico)
- `d.isReceiver` → direzione (in/out)
- `partnerLookup` → nome broker partner e valuta partner
Risultato:
- TRANSFER giver: `📤 Inviato a Interactive Brokers`
- TRANSFER receiver: `📥 Ricevuto da Coinbase`
- FX_CONVERSION giver: `💱 Conversione in USD`
- FX_CONVERSION receiver: `💱 Convertito da EUR`
- Generico: `🔗 Coppia collegata — IBKR ↔ DEGIRO`

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | Pulse CSS su `<td>`, rmv prop `highlightId`, `formatQty` emoji, broker tint, cleanup imports, capture click delegation, `linkedPairTooltip()` |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Pulse via DOM diretto, rmv `FilterMap.highlight_id`, cleanup URL parse/build/effect |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | 5 chiavi `transactions.linkTooltip.*` |

### Validazione Round 1.12

- Nessun errore reale in entrambi i file ✅
- Warning CSS: false positive pre-esistenti (W80) ✅
- Pulse: DOM diretto con capture phase + fallback ghost-id querySelector ✅ **Confermato funzionante dall'utente**
- Broker tint: light 30%/42%, dark 45%/55% (regolabili via commento CSS) ✅ **Confermato visivamente dall'utente**
- Quantità: `+1,234 📈` / `-56.78 📉` / `0` ✅ **Confermato dall'utente**
- Link tooltip: specifico per tipo TX con emoji e broker/currency ✅
- i18n: 5 chiavi `transactions.linkTooltip.*` in 4 lingue ✅

### Residui aperti dopo Round 1.12

| Issue | Stato | Note |
|-------|-------|------|
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | Chip interattivo con ✕/+ per rimuovere/aggiungere ghost row ai filtri — design da definire |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT |
| **`escapeHtml()` × 4 copie** | ⏳ cleanup | Fattorizzare in `$lib/utils/escapeHtml.ts` e importare ovunque |
| **`formatCash()` residuo** | ⏳ cleanup | Usato solo come `title` attr nella cash cell — sostituibile con `formatCurrencyAmountHtml().replace(/<[^>]*>/g, '')` |
| **`onEventBadgeClick` dead handler** | ⏳ cleanup | Noop in `+page.svelte` + prop/delegation in TransactionsTable — rimuovere quando confermato non necessario |

---

## Round 1.13 — Tooltip linked pair completi + mock data giroconti

### Contesto

Utente conferma che pulse, colori, icone ed emoji funzionano tutti. Tuttavia:

1. **Tooltip linked pair incompleti**: `linkedPairTooltip()` copre solo TRANSFER (asset) e FX_CONVERSION (cambio valuta). Mancano tooltip per:
   - **DEPOSIT↔WITHDRAWAL** (giroconto cash tra broker): es. prelevare da un broker e depositare in un altro
   - **Altre combinazioni possibili** con `related_transaction_id`: ADJUSTMENT, o coppie miste

2. **Mock data insufficienti**: `populate_mock_data.py` crea solo 3 coppie linked:
   - 2× TRANSFER (AAPL IB→DEGIRO, BTC Coinbase→IB)
   - 1× FX_CONVERSION (EUR→USD at IB)
   
   Mancano completamente:
   - Giroconto cash (WITHDRAWAL da un broker + DEPOSIT su un altro, linkati)
   - DEPOSIT/WITHDRAWAL cross-broker

### Piano esecuzione

| # | Task | Status |
|---|------|--------|
| C40 | Estendere `linkedPairTooltip()` per DEPOSIT↔WITHDRAWAL (giroconto cash) | ✅ |
| C41 | Aggiungere coppia linked WITHDRAWAL↔DEPOSIT in `populate_mock_data.py` | ✅ |
| C42 | i18n keys per i nuovi tooltip (`depositFrom`, `withdrawalTo`) | ✅ |

### Dettagli implementativi

**C40 — Tooltip DEPOSIT↔WITHDRAWAL**: `linkedPairTooltip()` ora gestisce 4 tipi linked:
- `TRANSFER` → `📥 Ricevuto da {broker}` / `📤 Inviato a {broker}`
- `FX_CONVERSION` → `💱 Convertito da {currency}` / `Conversione in {currency}`
- `DEPOSIT` (linked) → `🏦 Accredito da {broker} ({currency})`
- `WITHDRAWAL` (linked) → `🏦 Prelievo verso {broker} ({currency})`
- Generico → `🔗 Coppia collegata — Broker1 ↔ Broker2`

**C41 — Mock data giroconto cash**: Aggiunta coppia #4 in `populate_mock_data.py`:
- WITHDRAWAL €2000 da DEGIRO + DEPOSIT €2000 su IB, stessa data, linkati bidirezionalmente
- Tag `giroconto` per riconoscibilità

**C42 — i18n**: 2 nuove chiavi `transactions.linkTooltip.depositFrom` / `.withdrawalTo` in 4 lingue.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | `linkedPairTooltip()` esteso per DEPOSIT/WITHDRAWAL |
| `backend/test_scripts/test_db/populate_mock_data.py` | Coppia linked WITHDRAWAL↔DEPOSIT (giroconto €2000 DEGIRO→IB) |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | 2 chiavi `transactions.linkTooltip.{depositFrom,withdrawalTo}` |

### Validazione Round 1.13

- Nessun errore reale ✅
- Tooltip copre tutti i tipi linked: TRANSFER, FX_CONVERSION, DEPOSIT, WITHDRAWAL, generico ✅
- Mock data: 4 coppie linked (2× TRANSFER, 1× FX_CONVERSION, 1× WITHDRAWAL↔DEPOSIT) ✅
- i18n: 7 chiavi `transactions.linkTooltip.*` totali ✅

### Residui aperti dopo Round 1.13

| Issue | Stato | Note |
|-------|-------|------|
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | Chip interattivo con ✕/+ per rimuovere/aggiungere ghost row ai filtri — design da definire |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT |
| **`escapeHtml()` × 4 copie** | ⏳ cleanup | Fattorizzare in `$lib/utils/escapeHtml.ts` |
| **`formatCash()` residuo** | ⏳ cleanup | Sostituibile con strip-HTML di `formatCurrencyAmountHtml()` |
| **`onEventBadgeClick` dead handler** | ⏳ cleanup | Noop — rimuovere quando confermato |
| **Rieseguire `./dev.py db create-clean && ./dev.py db populate`** | ⏳ | Necessario per vedere la nuova coppia giroconto nei dati |

---

## Round 1.14 — Execution Report

### Fixes implementati

| # | Issue | Fix | Status |
|---|-------|-----|--------|
| C43 | Event tooltip: tipo evento mostrato in inglese raw (`DIVIDEND`, `SPLIT`) invece del nome tradotto | Usato `$t(\`assetDetail.eventType.${ev.type}\`)` per nome tradotto. Fallback al code raw se la chiave non esiste. | ✅ C43 |
| C44 | Event tooltip su una riga sola — poco leggibile | Riformattato su più righe con `\n`: riga 1 = emoji + nome tradotto + data; riga 2 = importo formattato + ⚙ auto; riga 3+ = notes. | ✅ C44 |
| C45 | FX tooltip mostrava solo importo partner — manca il lato "da" | Ora mostra entrambi i lati: `💱 Conversione in 1.000,00 € 🇪🇺EUR → 1.090,00 $ 🇺🇸USD` | ✅ C45 |
| C46 | Generico tooltip diceva "Coppia collegata" — poco descrittivo per cash transfer | Cambiato a "Giroconto" (IT), "Cash transfer" (EN), "Virement" (FR), "Transferencia de fondos" (ES) | ✅ C46 |
| C47 | `thisAmount` unused warning in `linkedPairTooltip` FX branch | Ora usato per mostrare entrambi i lati del cambio nel tooltip | ✅ C47 |

### Dettagli implementativi

**C43+C44 — Event tooltip tradotto e multi-riga**:
```
Prima:  💰 DIVIDEND · 2025-07-31 · 0.25 $ 🇺🇸USD · "Quarterly" · ⚙ auto
Dopo:   💰 Dividendo · 2025-07-31
        0.25 $ 🇺🇸USD  ⚙ auto
        Quarterly dividend payment
```
- Riga 1: `{emoji} {$t(assetDetail.eventType.{TYPE})} · {date}`
- Riga 2: `{formattedAmount}` + opzionale `⚙ auto`
- Riga 3+: notes (senza virgolette)
- Le traduzioni esistevano già sotto `assetDetail.eventType.*` (5 tipi: DIVIDEND, INTEREST, SPLIT, PRICE_ADJUSTMENT, MATURITY_SETTLEMENT)

**C45 — FX tooltip entrambi i lati**: `fmtCash()` helper formatta `Math.abs(amount)` con `formatCurrencyAmountHtml` (strip HTML). Il tooltip ora mostra `thisAmount → partnerAmount` per il giver e `partnerAmount → thisAmount` per il receiver.

**C46 — Generic fallback**: i18n key `transactions.linkTooltip.generic` aggiornata da "Linked pair"/"Coppia collegata" a "Cash transfer"/"Giroconto"/"Virement"/"Transferencia de fondos". Emoji cambiata da 🔗 a 🏦.

### File modificati

| File | Modifica |
|------|----------|
| `frontend/src/lib/components/transactions/TransactionsTable.svelte` | `eventTooltipText()` tradotto + multi-riga; `linkedPairTooltip()` FX con entrambi i lati |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | `generic` → "Cash transfer"/"Giroconto"; `fxReceive/fxSend` → `{amount}` placeholder |

### Validazione Round 1.14

- Nessun errore reale ✅
- Event tooltip: nome tradotto (`Dividendo` in IT, `Dividende` in FR) ✅
- Event tooltip: multi-riga con `\n` (emoji+tipo+data / importo / notes) ✅
- FX tooltip: entrambi i lati (`1.000 € EUR → 1.090 $ USD`) ✅
- Generic: "Giroconto" con 🏦 ✅

### Residui aperti dopo Round 1.14

| Issue | Stato | Note |
|-------|-------|------|
| **Ghost row chip "out of filter"** (Step 5 piano originale) | ⏳ Round 2 | Chip interattivo con ✕/+ |
| **E2E `asset-event-delete.spec.ts`** (Step 6 piano originale) | ⏳ deferred | Test E2E per delete eventi con RESTRICT |
| **`escapeHtml()` × 4 copie** | ⏳ cleanup | Fattorizzare in `$lib/utils/escapeHtml.ts` |
| **`formatCash()` residuo** | ⏳ cleanup | Sostituibile con strip-HTML di `formatCurrencyAmountHtml()` |
| **`onEventBadgeClick` dead handler** | ⏳ cleanup | Noop — rimuovere quando confermato |

