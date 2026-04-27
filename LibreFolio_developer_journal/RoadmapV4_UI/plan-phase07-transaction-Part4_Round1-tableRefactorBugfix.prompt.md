# Plan — Phase 07 · Part 4 · Step 5 · Round 1 — Tabella `/transactions` refactor + Bugfix Add modal

**Date**: 2026-04-27
**Status**: 🔨 IN CORSO (Step 1–5 ✅, Step 6 ⏳)
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

