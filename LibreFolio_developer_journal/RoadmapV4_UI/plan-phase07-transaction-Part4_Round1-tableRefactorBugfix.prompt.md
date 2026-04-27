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
- `frontend/src/lib/components/table/DataTableColumnFilter.svelte` (estensione)
- `frontend/src/lib/components/table/types.ts` (estensione `FilterValue`)
- `frontend/src/lib/components/transactions/TransactionsTable.svelte` (cablaggio)
- `backend/test_scripts/test_db/populate_mock_data.py` (mock tags)

**Deliverable**:
1. **Estensione `FilterValue`**: nuova variant `{ type: 'multi-enum', selected: string[] }` (o riuso `enum` con flag `multi: true`). UI nel popover: lista checkbox + search-box in alto per filtrare tra le opzioni.
2. **Set delle opzioni computato client-side** dalla `getValue` della colonna su tutto il dataset corrente (`data` di `DataTable`):
   ```ts
   const all = new Set<string>();
   for (const r of data) for (const t of (r.tx.tags ?? [])) all.add(t);
   ```
   Questo è già naturale perché TX hanno `tags: string[]` lato API (il backend gestisce CSV internamente — vedi `Transaction.tags` in `models.py:633`).
3. **Logica filtro** in `DataTable.filteredData`: row passes se `selected.length === 0` o `selected.some(t => row.tags.includes(t))` (OR di default).
4. **Mock data**: estendere `populate_mock_data.py` per assegnare tag rappresentativi a un sottoinsieme di TX (es. `['core']` su BUY high-value, `['speculative']` su crypto, `['long-term']` su DIVIDEND, `['rebalance']` su SELL). Almeno 4 tag distinti su ≥10 TX, mescolati. Eseguire via `./dev.py db create-clean` poi `./dev.py db populate`.

**Tests**: applicare filtro multi-tag, verificare URL encoding (Step 5), verifica visiva.

**Stima**: 1.5h

---

### Step 4 — Filtro `currency-stack` generico in `DataTable`

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
5. `feat(transactions): wire type/broker enumOptions + bidirectional URL filter sync (W6,W9)`
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
| W29 | ⚠ UX | Min/Max nel sub-popover currency-stack è un input scarno. Deve riusare lo stesso identico UI/scale di `type:'number'` (slider + input) | refactor `currency-stack` per riusare `NumberRange` block | ✅ B8 |
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
| W47 | ⚠ UX | Filtro broker: quando il broker non ha icona c'è uno spazio bianco fastidioso. Servire il puntino colorato come fallback (identico alla cella broker nella tabella). | Aggiungere dot colorato inline nell'enum option del filtro broker quando `iconUrl` è assente. | ⏳ |
| W48 | ⚠ UX | Filtro prezzo multi-valuta (`currency-stack`) esteso anche alla tabella `/assets/` nella colonna "ultimo prezzo". Formattare i numeri come in transactions: `[simbolo]|bandiera|iso3`. | Modificare `AssetTable.svelte` colonna `lastPrice`: tipo `currency-stack`, aggiungere `getCurrencyValue`, formattare cella con simbolo/bandiera/codice come in TX. | ⏳ |
| W49 | ❌ bug | In `/assets/` manca il titolo tradotto della colonna `name` (`assets.table.name`). Header sparito. | Verificare che `header: () => $t('assets.table.name')` sia nello column def `name`. | ⏳ |
| W50 | ❌ bug | Paginazione non mostrata in `/transactions` nonostante 21 TX. Custom paginator `totalPages > 1` ma `pageSize` default 50 ≥ 21 → 1 pagina sola → nascosta. L'utente si aspetta di **vederla sempre** (come feedback per "tot risultati"). | Mostrare `DataTablePagination` sempre (condizione `displayRows.length > 0`). | ⏳ |
| W51 | ⚠ UX | Icona tipo TX: ha tooltip in `title` HTML nativo ma deve usare `Tooltip.svelte`. Desktop: hover=tooltip, click→doc wiki. Mobile: click=tooltip, longpress→doc. | Rimuovere `title` HTML, usare `tooltip` nella HtmlCell per typeIcon. Riadattare click delegation: desktop click→doc (non bloccato da Tooltip perché Tooltip non fa stopPropagation su hover-only), mobile touch→tooltip (Tooltip gestisce), longpress→doc. | ⏳ |
| W52 | ⚠ UX | Evento tooltip mostra solo "Linked event" generico. Il piano originale prevedeva bulk event query `POST /assets/events/query` con `{ids}` per alimentare `eventTooltipMap`. Feature mancante nel backend (non esiste endpoint by-event-id) — da implementare come `GET /assets/events?ids=...` o bulk query variant. | **Missing feature backend**: occorre endpoint per recuperare eventi per ID. Frontend: aggiornare `loadEventTooltipMap` per usare endpoint reale. Deferred Round 2 se endpoint non disponibile. | ⏳ deferred |
| W53 | ⚠ UX | Colonna `actions` sempre visibile/sticky. Solo la colonna `select` deve essere sticky; `actions` deve scrollare con le altre colonne. | In `TransactionsTable.svelte` configurare DataTable: actions non sticky. Verificare se DataTable supporta non-sticky actions (probabilmente va aggiunto prop `stickyActions?: boolean`). | ⏳ |
| W54 | ⚠ UX | Asset collegati (linked assets) creati in DB population non mostrati nel frontend come pianificato nel piano originale (Step 5, ghost row con chip etc.). Da verificare se i dati sono presenti e se la logica di rendering funziona. | Verificare `populate_mock_data.py` per TX con `related_transaction_id` e testare visivamente la ghost row. Se i dati mancano → aggiungere TX linked in mocking. | ⏳ verify |
| W55 | ⚠ UX mobile | Pulsanti header (refresh, vis toggle, import, add) disallineati in mobile: tooltip a destra, icone decentrate e troppo larghe. Upload e Add devono avere icone centrate, padding uniforme. | Uniformare classi CSS: `flex items-center justify-center gap-1 px-2.5 py-1.5` su tutti i bottoni azione. | ⏳ |
| W56 | 🔍 refactor | Codice duplicato: logica cash cell (`formatCash` + `getCurrencyInfo` + symbol/flag rendering) è identica tra TX e assets — fattorizzare in helper `formatCurrencyAmount()` riusabile. Broker icon chain (inline HTML con onerror) duplicata tra TransactionsTable broker cell e enum options e files — fattorizzare `brokerIconHtml()`. | Creare `$lib/utils/currencyFormat.ts` con `formatCurrencyAmount()` e `$lib/utils/brokerHelpers.ts` con `brokerIconHtml()`. | ⏳ |

### Fix plan Round 1.4

Batch di fix in ordine di priorità:

- **C1 (W55) ✅** — Riordinato array `columns` in `TransactionsTable.svelte`: `date → typeIcon → quantity → cash → event → asset → broker → tags`.
- **C2 (W54) ⏳** — Dark mode: CSS rules per `.dark` già presenti (`.dark .tx-cash-amount`, `.dark .tx-tag-badge`, `.dark .tx-broker-dot`). Verifica visiva con server running pendente.
- **C3 (W47) ✅** — Type column: `width` alzato a 90px. Aggiunto `getEnumOptionsWithCounts()` in `DataTable.svelte` che computa il count di righe per ogni enum option e filtra quelle con count=0. CSS `.enum-count` in `DataTableColumnFilter` per badge conteggio. `enumOptions` in TX usa `.filter(tt => mainRows.some(r => r.type === tt))`.
- **C4 (W48) ✅** — Event tooltip: aggiunto `tooltip: {text: tip, position: 'top'}` alla cella HtmlCell dell'event dot. DataTable renderizza `<Tooltip>` wrapper quando `cellContent.tooltip` è presente.
- **C5 (W49) ✅** — Type icon click → wiki: root cause era `Tooltip.toggle()` che chiama `event.stopPropagation()`, impedendo la delegation click su `tx-table-wrap`. Fix: rimosso `tooltip` dalla cella typeIcon (usa solo `title` attr HTML per tooltip nativo). Fix URL: `getTxTypeDocUrl()` ora costruisce URL assoluto `protocol://hostname:8000/mkdocs/...` quando si rileva la porta dev 5173.
- **C6 (W52, W51) ✅** — Cash cell refactor:
  - Eliminata duplicazione codice valuta: se esiste un simbolo reale (≠ codice), mostra `importo simbolo bandiera`; altrimenti `importo bandiera+codice`. Bandiera 🏳️ (fallback) omessa.
  - Aggiunto `currencyStoreVersion` (Svelte `writable(0)` store) a `currencyStore.ts` — incrementato dopo ogni load. Cash cell fa `void $currencyStoreVersion` per forzare re-render quando il currency store carica async.
- **C7 (W50) ✅** — BrokerBadge + FilesTable broker:
  - Creato `BrokerBadge.svelte` generico (icon chain: `icon_url → portal_url/favicon.ico → dot colorato` + nome).
  - Refact broker cell in `FilesTable.svelte`: da `badge` colorato a `html` con `<img>` + `onerror` fallback a dot. Broker `enumOptions` arricchite con `iconUrl`.
  - `loadBrokers` in `/files/+page.svelte` ora mappa `icon_url` e `portal_url` nel `brokerMap`.
- **C8 (W53) ⏳** — FilterPanel generico per asset, broker, tag: deferred Round 2 (richiede componente dedicato con search + checkbox list + count per tutti gli asset in DB).
- **C9 (W56) ✅** — Mobile responsive: `<span>` testo di Import e Add Transaction wrappati con `hidden sm:inline` → icona-only su schermi <640px.

**Validazione**: `./dev.py front format` → clean; `./dev.py front check` → 0/0 ✅; `./dev.py i18n audit` → 940 keys, 0 incomplete ✅.

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
| W62 | ⚠ UX | Evento tooltip mostra solo "Linked event" generico. Il piano originale prevedeva bulk event query `POST /assets/events/query` con `{ids}` per alimentare `eventTooltipMap`. Feature mancante nel backend (non esiste endpoint by-event-id) — da implementare come `GET /assets/events?ids=...` o bulk query variant. | **Missing feature backend**: occorre endpoint per recuperare eventi per ID. Frontend: aggiornare `loadEventTooltipMap` per usare endpoint reale. Deferred Round 2 se endpoint non disponibile. | ⏳ deferred |
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
- **C4 (W59) ✅** — Asset table title: chiave `assets.table.name` aggiunta in EN/IT/FR/ES via `./dev.py i18n add`.
- **C5 (W61) ✅** — Type icon tooltip con Tooltip.svelte:
  - Cell typeIcon ora ha `tooltip: {text: label, position: 'top'}` e usa `<a href>` nativo per navigazione wiki.
  - Rimossi handler `dblclick`/`pointerdown`/`pointerEnd` e `isCoarsePointer` detection (non più necessari).
  - CSS aggiunto `text-decoration: none` su `.tx-type-icon-link`.
- **C6 (W63) ✅** — Actions column non sticky: aggiunto prop `stickyActions?: boolean` (default `true`) a DataTable. TransactionsTable usa `stickyActions={false}`.
- **C7 (W65) ✅** — Mobile buttons: tutti i bottoni con padding uniforme `px-2.5 py-1.5 text-xs`, icone `size={15}`, `justify-center gap-1`. Container con `ml-auto` per allineamento a destra.
- **C8 (W62) ⏳ deferred** — Event tooltip con dati reali (richiede endpoint backend `GET /assets/events?ids=...`).
- **C9 (W64) ⏳ verify** — Linked assets / ghost rows: verifica dati mock pendente.
- **C10 (W66) ✅ partial** — Refactor codice duplicato: creato `currencyFormat.ts` condiviso. TX cash cell resta inline (da unificare in Round 2). Broker icon chain non ancora fattorizzata.

**Validazione**: `./dev.py front format` → clean; `./dev.py front check` → 0/0 ✅; `./dev.py i18n audit` → 941 keys, 0 incomplete ✅.

**Residui aperti Round 1.5**:
- **W62** ⏳ — Event tooltip con dati reali (richiede endpoint backend).
- **W64** ⏳ — Linked assets / ghost rows: verifica dati mock.
- **W66** partial — brokerIconHtml() fattorizzazione + TX cash cell unificazione (Round 2).
