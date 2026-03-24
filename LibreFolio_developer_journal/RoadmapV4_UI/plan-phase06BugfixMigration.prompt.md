# Plan: Phase 06 — Bugfix, Migrazione e UX Refinement (Rientro post Step 1+2)

**Data creazione**: 23 Marzo 2026
**Ultimo aggiornamento**: 23 Marzo 2026
**Contesto**: Dopo il completamento di Phase 06 Step 1 (backend) e Step 2 (frontend dual view),
la review ha evidenziato bug, debiti tecnici e miglioramenti UX da risolvere prima di procedere
con Step 3 (AssetModal). Questo piano di rientro corregge tutto in ordine di dipendenza.

**Durata stimata**: ~0.5 giorni
**Dipendenze**: Phase 06 Step 1 + Step 2 completati

**Stato**: ✅ Step 1-15 completati | ✅ Feature F1-F5 completate | ✅ Step 2c (B1-B9) completati | ✅ Step 2d (C1-C12) completati | ⬜ Step 2e (D1-D12) in attesa

---

## Glossario Terminologia Sync/Query

> **Convenzione progetto** (allineata con FX):
>
> | Termine | Direzione | Endpoint Asset | Endpoint FX |
> |---------|-----------|----------------|-------------|
> | **Sync** | Provider → DB | `POST /assets/prices/refresh` | `POST /fx/currencies/sync` |
> | **Query** (refresh frontend) | DB → Frontend | `POST /assets/prices/query` | `POST /fx/currencies/convert` |
> | **Upsert manuale** | Frontend → DB | `POST /assets/prices` | `POST /fx/currencies/rate` |
>
> **Anti-pattern rimosso**: Il vecchio `GET /assets/prices/{id}` faceva Sync+Query in un'unica
> chiamata — se c'era un provider assegnato, contattava il provider (HTTP esterna a yfinance/justetf),
> salvava nel DB, poi restituiva i dati. Ogni lettura poteva generare chiamate HTTP.
> Con N asset = N chiamate HTTP sequenziali. Ora i due flussi sono separati:
> - **Sync** è esplicita, solo su richiesta utente (bottone "Sync" / `prices/refresh`)
> - **Query** è pura lettura da DB, nessun side-effect (bottone "Refresh" / `prices/query`)

---

## Indice

| # | Titolo | Area | Priorità | Stato |
|---|--------|------|----------|-------|
| 1 | Fix crash `.toFixed()` su pagina Assets | Frontend | 🔴 Bloccante | ✅ |
| 2 | Migrazione BrokerIcon a Svelte 5 runes | Frontend | 🟡 Debito tecnico | ✅ |
| 3 | Migrazione localStorage a user-scoped | Frontend | 🟡 Debito tecnico | ✅ |
| 4 | Fix FX delete 422 (`date_range` array → oggetto) | Frontend | 🔴 Bug | ✅ |
| 5 | Fix FX detail UX per coppie manual-only | Frontend + UX | 🟡 UX | ✅ |
| 6 | Spostare ViewModeToggle nell'header | Frontend | 🟢 Estetica | ✅ |
| 7 | Endpoint bulk asset prices + colonne Δ multi-periodo | Backend + Frontend + Test | 🟢 Feature | ✅ |
| 8 | Fix test upload 401 | Backend test | 🟡 Test | ✅ |
| 9 | Rimuovere chiave i18n orfana | i18n | 🟢 Pulizia | ✅ |
| 10 | Fix auth in TUTTI i test API (8+1 file) | Backend test | 🔴 Bug | ✅ |
| 11 | Ottimizzazione FX delete (merge date consecutive in range) | Frontend | 🟢 Ottimizzazione | ✅ |
| 12 | Fix crash JustETF search (`.fillna` su colonne con NaN) | Backend | 🔴 Bug | ✅ |
| 13 | Fix `FAAssetCreateResult` extra field `identifier` | Backend | 🔴 Bug | ✅ |
| 14 | Migrazione COMPLETA test all'architettura Sync→Query | Backend test | 🟡 Test | ✅ |
| 15 | Test runner label + nuovo test "query senza sync = vuoto" | Backend test | 🟢 Test | ✅ |

---

## Feedback Review — TODO per Step 2b successivo ✅ Completati

Questi punti emersi dalla review dell'utente sono stati implementati:

### F1 — Toast message dopo save in FxDataEditorSection ✅
**Area**: Frontend UX
**File**: `FxDataEditorSection.svelte`
**Problema**: Dopo il salvataggio (upsert + delete) non c'è feedback visivo.
**Soluzione**: Aggiungere toast success con conteggio punti inseriti/aggiornati/cancellati.
Toast error in caso di fallimento con messaggio di errore dal backend.
Usare il componente toast custom esistente (`toasts.success()` / `toasts.error()`).

### F2 — Impedire rate negativi nell'editor FX ✅
**Area**: Frontend validation
**File**: `DataEditor.svelte` o `FxDataEditorSection.svelte`
**Problema**: Il campo rate permette valori negativi tramite freccia giù della tastiera.
**Soluzione**: Aggiungere `min="0"` all'input numerico e/o clamping nel handler.

### F3 — Marker circolare per singolo punto nel chart ✅
**Area**: Frontend chart
**File**: `PriceChartCompact.svelte`, `PriceChartFull.svelte`, `LineChart.svelte`
**Problema**: Un singolo data point è invisibile perché non crea un segmento di linea.
**Soluzione**: Se i dati contengono un solo punto, renderizzarlo come marker circolare.
Se il marker è assente o null, usare il circolare di default. Dal 2° punto in poi,
si usa il comportamento normale (segmento di linea).

### F4 — ColumnVisibilityToggle nella pagina Assets (table mode) ✅
**Area**: Frontend UX
**File**: `assets/+page.svelte`
**Problema**: In modalità tabella manca il selettore di visibilità colonne (occhio).
**Soluzione**: Accanto al ViewModeToggle, mostrare `ColumnVisibilityToggle` quando
`viewMode === 'list'`, come già fatto nella pagina files.

### F5 — Colonne Δ multi-periodo nella tabella FX ✅
**Area**: Frontend feature
**File**: `fx/+page.svelte`, `FxTable.svelte`
**Problema**: Le colonne Δ multi-periodo sono solo nella tabella Assets, non in FX.
**Soluzione**: Replicare la stessa logica di `DELTA_PERIODS` + `visiblePeriods` +
`computePeriodDelta()` nella pagina FX e nel componente FxTable.

---

## Step 2c — Post-Review Fixes & UX Improvements (24 Marzo 2026)

Sezione aggiuntiva emersa dalla seconda e terza review. Copre bug, refactoring UX, nuove feature
e migrazione test backend. I fix sono raggruppati per dipendenza: prima bug atomici (B1–B3),
poi refactoring azioni (B4), poi visibilità colonne (B7), poi feature complesse (B5–B6),
poi miglioramenti test (B8–B9).

**Durata stimata**: ~1.5 giorni
**Dipendenze**: Step 1-15 + F1-F5 completati

### Indice Step 2c

| # | Titolo | Area | Priorità | Stato |
|---|--------|------|----------|-------|
| B1 | Messaggio validazione rate: "strictly > 0" | Frontend copy | 🟢 Facile | ✅ |
| B2 | Chart non si aggiorna dopo cancellazione dati FX | Frontend bug | 🔴 Bug | ✅ |
| B3 | Action button in tabella naviga invece di eseguire azione | Frontend bug | 🔴 Bug | ✅ |
| B4 | Rimuovere icona edit ridondante, aggiungere sync/refresh | Frontend UX | 🟡 Refactor | ✅ |
| B5 | Multi-selezione con azioni di gruppo + toolbar esterna | Frontend feature | 🟡 Feature | ✅ |
| B6 | Blocco 2×2 azioni mancante in pagina Assets + ColumnVisibility | Frontend UX | 🟡 Feature | ✅ |
| B7 | Colonne Δ periodo: columnOrder non sincronizza colonne dinamiche | Frontend bug | 🟡 Bug | ✅ |
| B8 | Test CSS Scraper: skip condizionale per mercato chiuso | Backend test | 🟢 Test | ✅ |
| B9 | Migrazione test_asset_source.py: `get_prices` → `get_prices_bulk` | Backend test | 🔴 Bug | ✅ |

**Ordine di implementazione**: B9 → B1 → B3 → B2 → B7 → B4 → B5 → B6 → B8

---

### B1 — Messaggio validazione rate: "strictly > 0"

**Area**: Frontend copy
**Priorità**: 🟢 Facile (1 riga)
**File**: `frontend/src/lib/components/fx/FxDataEditorSection.svelte` (riga 169)

**Problema**: Quando l'utente inserisce 0 come rate, il messaggio di errore dice
`"Please enter a valid positive rate"`, che non chiarisce esplicitamente che 0 è escluso.
La validazione (riga 160: `rate > 0`) è corretta, ma il messaggio è ambiguo.

**Fix**: Cambiare il messaggio in:
```
"${invalidCount} row(s) have invalid rate values. Rate must be strictly greater than zero (0 is not allowed)."
```

**Tasks**:
- [ ] Aggiornare stringa errore in `FxDataEditorSection.svelte` riga 169

---

### B2 — Chart non si aggiorna dopo cancellazione dati FX

**Area**: Frontend bug
**Priorità**: 🔴 Bug (UX rotto — chart mostra dati vecchi)
**File**: `frontend/src/routes/(app)/fx/[pair]/+page.svelte` (righe 268-277)

**Problema**: Dopo aver cancellato tutti i dati nell'editor, il banner "No rate data available"
appare correttamente, ma il **grafico mostra ancora i dati pre-delete**. Dopo F5 funziona.

**Root cause**: In `loadChartData()`, nel blocco `catch` path 404 (riga 272-273), viene settato
`error` al messaggio banner ma `chartData` **NON viene resettato a `[]`**. Il vecchio array
rimane in memoria e il chart continua a renderizzarlo.

**Fix**:
```javascript
// Nel blocco catch, path 404:
} else if (e?.response?.status === 404) {
    chartData = [];  // ← AGGIUNGERE: pulire dati chart
    store.invalidateRange(dateStart, dateEnd);  // ← AGGIUNGERE: invalidare cache store
    error = 'No rate data available for this range. Try syncing first or adjusting the date range.';
}
// Anche nel path errore generico, aggiungere chartData = [] quando existingData è vuoto
```

**Tasks**:
- [ ] Aggiungere `chartData = []` nel path 404 (prima di settare `error`)
- [ ] Aggiungere `store.invalidateRange(dateStart, dateEnd)` nel path 404
- [ ] Nel path errore generico (riga 275-276), se `existingData.length === 0`, settare `chartData = []`

---

### B3 — Action button in tabella naviga invece di eseguire azione

**Area**: Frontend bug
**Priorità**: 🔴 Bug (click handler ambiguo — double-fire)
**File**: `frontend/src/lib/components/table/DataTable.svelte` (riga 1035)

**Problema**: Cliccando un bottone azione (edit, delete, swap) nella riga della tabella FX,
**sia** l'azione del bottone **sia** la navigazione al dettaglio vengono eseguite. L'utente
finisce nella pagina dettaglio invece di eseguire solo l'azione.

**Root cause**: Il bottone azione (riga 1035) ha `onclick={() => handleRowAction(action, row)}`
senza `e.stopPropagation()`. Il click risale al `<tr>` (riga 897) che ha
`onclick={() => handleRowClick(row)}` → `onRowClick` → `goto('/fx/...')`.

Il checkbox (riga 906) **già ha** `e.stopPropagation()`. Manca solo nel bottone action.

**Fix**:
```svelte
<!-- DataTable.svelte riga 1035 — PRIMA: -->
onclick={() => handleRowAction(action, row)}

<!-- DOPO: -->
onclick={(e) => { e.stopPropagation(); handleRowAction(action, row); }}
```

**Tasks**:
- [ ] Aggiungere `e.stopPropagation()` all'onclick del bottone action in `DataTable.svelte` riga 1035

---

### B4 — Rimuovere icona edit ridondante, aggiungere sync/refresh nelle azioni

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/lib/components/fx/FxTable.svelte`
- `frontend/src/lib/components/assets/AssetTable.svelte`
- `frontend/src/lib/components/fx/FxCard.svelte`
- `frontend/src/lib/components/assets/AssetCard.svelte`
- `frontend/src/routes/(app)/fx/+page.svelte`
- `frontend/src/routes/(app)/assets/+page.svelte`

**Problema**: Il click su riga/card già naviga al dettaglio. Il bottone Pencil/edit è ridondante.
Servono invece Sync e Refresh come azioni dirette, oltre al Delete.

**Fix per ciascun componente**:

1. **FxTable.svelte**: Rimuovere azione `id: 'edit'` (Pencil). Aggiungere:
   - `id: 'sync'` (icona `RotateCw`) — `disabled: (row) => row.manualOnly`
   - `id: 'refresh'` (icona `RefreshCw`)
   Aggiungere prop `onsync`, `onrefresh` al Props interface.

2. **AssetTable.svelte**: Rimuovere azione `id: 'edit'` (Pencil). Aggiungere:
   - `id: 'sync'` (icona `RotateCw`) — `disabled: (row) => !row.has_provider`
   - `id: 'refresh'` (icona `RefreshCw`)
   Aggiungere prop `onsync`, `onrefresh` al Props interface.

3. **FxCard.svelte**: Rimuovere bottone Pencil dal footer destro (ha già sync/refresh nel footer sinistro).

4. **AssetCard.svelte**: Rimuovere bottone Pencil. Aggiungere sync + refresh nel footer
   (stesso pattern FxCard). Sync disabilitato se `!has_provider`.
   Aggiungere prop `onsync`, `onrefresh`.

5. **Pages parent**: Propagare i callback `onsync`/`onrefresh` da `fx/+page.svelte` e
   `assets/+page.svelte` ai componenti tabella/card. Riusare handler già esistenti
   (`handleSyncPair`, `handleRefreshPair` per FX).

**Tasks**:
- [ ] FxTable: rimuovere edit, aggiungere sync + refresh nelle rowActions; aggiungere prop `onsync`/`onrefresh`
- [ ] AssetTable: rimuovere edit, aggiungere sync + refresh; aggiungere prop `onsync`/`onrefresh`
- [ ] FxCard: rimuovere bottone Pencil dal footer destro
- [ ] AssetCard: rimuovere Pencil, aggiungere sync + refresh; prop `onsync`/`onrefresh`
- [ ] fx/+page.svelte: passare `onsync`/`onrefresh` a `FxTable`
- [ ] assets/+page.svelte: implementare `handleSyncAsset(id)` e `handleRefreshAsset(id)`, passare a tabella e card
- [ ] Rimuovere import `Pencil` dove non più usato

---

### B5 — Multi-selezione con azioni di gruppo + toolbar esterna

**Area**: Frontend feature
**Priorità**: 🟡 Feature (media complessità)
**File coinvolti**:
- `frontend/src/lib/components/table/DataTable.svelte` — rimuovere toolbar built-in
- `frontend/src/lib/components/table/DataTableToolbar.svelte` — componente esterno (già esiste)
- `frontend/src/lib/components/fx/FxTable.svelte`
- `frontend/src/lib/components/assets/AssetTable.svelte`
- `frontend/src/routes/(app)/fx/+page.svelte`
- `frontend/src/routes/(app)/assets/+page.svelte`

**Problema**: L'utente vuole selezionare più righe e applicare azioni in blocco:
sync, refresh, invert, delete per FX; sync, refresh, delete per Assets.
Inoltre, il sync di gruppo deve **aprire la modale sync-all** filtrata solo sulle coppie selezionate.

**Decisione architetturale (confermata dall'utente)**: Usare `DataTableToolbar.svelte` come
componente **esterno** nelle pagine parent. **Rimuovere la toolbar built-in** dal DataTable.svelte
(righe 746-758: import + render di `DataTableToolbar` inside DataTable). I consumatori che la
usavano vanno migrati al nuovo pattern esterno.

**Pattern toolbar esterna**:
```svelte
<!-- Nella pagina parent (es. fx/+page.svelte) -->
{#if selectedRows.length > 0}
    <DataTableToolbar
        selectedCount={selectedRows.length}
        bulkActions={bulkActions}
        onClearSelection={() => { /* reset selection */ }}
    />
{/if}
<FxTable bind:this={fxTableComponent} onSelectionChange={(rows) => selectedRows = rows} ... />
```

Il DataTable deve esporre `selectedRows` (già espone `onSelectionChange`) e un metodo
`clearSelection()` richiamabile dal parent.

**Refactoring DataTable.svelte**:
1. Rimuovere `import DataTableToolbar` (riga 21)
2. Rimuovere blocco render `{#if showToolbar && ...}` (righe 746-758)
3. Rimuovere prop `showToolbar` e `bulkActions` dall'interfaccia Props (non più necessari internamente)
4. Esporre `export function clearSelection()` (chiama `clearAllSelection()` interno)
5. Esporre `export function getSelectedRows(): T[]` per il parent

**Fix per i componenti wrapper**:

1. **FxTable.svelte**: Esporre `onselectionchange` callback al parent. Definire `bulkActions` come
   dati (non come prop DataTable): `sync`, `refresh`, `invert`, `delete`.
   - `Sync Selected` → apre modale sync-all con **solo le coppie selezionate** (non tutte)
   - `Invert Selected` (icona `ArrowLeftRight`)

2. **AssetTable.svelte**: Analogo, con azioni: `sync`, `refresh`, `delete` (no invert).

3. **Pages parent**: Importare `DataTableToolbar` direttamente e renderizzarlo nell'header/filter
   bar quando `selectedRows.length > 0`. Implementare handler bulk.

**Sync di gruppo → modale sync-all filtrata**:
Quando l'utente seleziona N coppie FX e clicca "Sync Selected", si apre la stessa modale
di "Sync All" ma pre-filtrata per mostrare solo le coppie selezionate. Questo evita di
creare una nuova modale e riusa l'infrastruttura esistente.

**Tasks**:
- [ ] DataTable: rimuovere import `DataTableToolbar`, blocco render toolbar, props `showToolbar`/`bulkActions`
- [ ] DataTable: esporre `clearSelection()` e `getSelectedRows()`
- [ ] FxTable: esporre callback `onselectionchange`; passare `selectionMode='multi'` al DataTable
- [ ] AssetTable: analogo a FxTable
- [ ] fx/+page.svelte: importare `DataTableToolbar`, renderizzare in header, implementare bulk handlers
- [ ] fx/+page.svelte: `handleBulkSync` apre modale sync-all con solo coppie selezionate
- [ ] assets/+page.svelte: analogo, con bulk handlers per assets
- [ ] Verificare che nessun altro componente usi la toolbar built-in di DataTable

---

### B6 — Blocco 2×2 azioni mancante in pagina Assets + riposizionamento ColumnVisibility

**Area**: Frontend UX
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte`
- `frontend/src/routes/(app)/fx/+page.svelte` (riferimento)

**Problema**: La pagina Assets manca del blocco 2×2 azioni (Abs/%, Settings, Sync All, Refresh All)
che la pagina FX ha nella filter bar (righe 629-674). Inoltre in modalità tabella il toggle Abs/%
non serve (non ci sono mini chart), quindi quello slot potrebbe ospitare ColumnVisibilityToggle.

**Fix proposto**:

1. Aggiungere blocco 2×2 azioni nella filter bar Assets (stesso layout responsive FX
   con `ResizeObserver` + `layoutMode`).

2. Contenuto condizionale del blocco 2×2:
   ```
   Grid mode:                     Table mode:
   ┌──────────┬──────────┐       ┌──────────────┬──────────┐
   │ Abs / %  │ Settings │       │ ColVisibility │ Settings │
   ├──────────┼──────────┤       ├──────────────┼──────────┤
   │ Sync All │ Refresh  │       │ Sync All      │ Refresh  │
   └──────────┴──────────┘       └──────────────┴──────────┘
   ```

3. Implementare `handleSyncAll()` in assets/+page.svelte: chiama `POST /assets/prices/refresh`
   per tutti gli asset con provider. Implementare `handleRefreshAll()`: ri-chiama
   `fetchAllPriceData()`.

4. Spostare `ColumnVisibilityToggle` dall'header della pagina al blocco 2×2 (slot top-left
   in table mode), rimuovendolo dalla sezione header.

5. Replicare lo stesso pattern di condizionalità su FX page: in table mode mostrare
   ColumnVisibilityToggle al posto di Abs/%.

**Tasks**:
- [ ] assets/+page.svelte: aggiungere `ResizeObserver` + `layoutMode` nella filter bar
- [ ] assets/+page.svelte: creare blocco 2×2 con contenuto condizionale grid/table
- [ ] Implementare `handleSyncAll()` e `handleRefreshAll()` nella pagina Assets
- [ ] Spostare `ColumnVisibilityToggle` dall'header al blocco 2×2 (table mode slot)
- [ ] Rimuovere `ColumnVisibilityToggle` dalla sezione header di assets
- [ ] fx/+page.svelte: in table mode mostrare ColumnVisibilityToggle al posto di Abs/%

---

### B7 — Colonne Δ periodo: `columnOrder` non sincronizza colonne dinamiche

**Area**: Frontend bug
**Priorità**: 🟡 Bug (logica visibilità — root cause trovata)
**File coinvolti**:
- `frontend/src/lib/components/table/DataTable.svelte` — `columnOrder` e `columnVisibility`
- `frontend/src/lib/components/fx/FxTable.svelte` — `hiddenByDefault: true` riga 194
- `frontend/src/lib/components/assets/AssetTable.svelte`

**Problema osservato**: Selezionando range 3M si vedono solo Δ 1W e Δ 1M (corretto).
Cambiando a 6M, dovrebbero apparire anche Δ 3M, ma **restano solo 1W e 1M**.
Andando su 1Y, mancano Δ 3M e Δ 6M. Il problema persiste in entrambe le pagine (FX e Assets).

**Root cause (confermata da analisi codice)**:

Il bug è in `DataTable.svelte`, **NON** nella logica `visiblePeriods` o `hiddenByDefault`.
Il flusso è:

1. **Mount con range 3M** → `visiblePeriods = [{key: '1W'}, {key: '1M'}]`
   → `columns` $derived include `delta_1W`, `delta_1M`
   → `columnOrder` (da localStorage o `defaultColumnOrder`) = `[..., 'delta_1W', 'delta_1M']`

2. **Cambio a 6M** → `visiblePeriods` aggiunge `{key: '3M'}`
   → `columns` $derived include ora anche `delta_3M`
   → MA `columnOrder` è `$state`, inizializzato al mount, **non si aggiorna**!
   → `orderedColumns = columnOrder.map(id => columns.find(c => c.id === id))` → `delta_3M` NON è in `columnOrder` → **non viene renderizzata**

3. La `$effect` alle righe 674-684 aggiorna `columnOrder` solo se `length === 0` (primo mount).
   Dopo il mount, `columnOrder` è "congelato".

**Il `columnVisibility` non è il problema**: `columnVisibility[c.id] !== false` restituirebbe
`true` per colonne non presenti nello state (undefined !== false). Ma la colonna non arriva
nemmeno al filtro di visibilità perché viene eliminata prima da `orderedColumns`.

**Fix proposto** (duplice):

1. **DataTable.svelte — Sync `columnOrder` con colonne dinamiche**:
   Aggiungere un `$effect` che, quando `columns` cambia, rileva le colonne nuove (non presenti
   in `columnOrder`) e le aggiunge; rileva le colonne rimosse e le elimina.
   ```typescript
   $effect(() => {
       const currentIds = new Set(columns.map(c => c.id));
       const orderedIds = new Set(columnOrder);
       // Add new columns at end
       const newIds = columns.filter(c => !orderedIds.has(c.id)).map(c => c.id);
       // Remove stale columns
       const filtered = columnOrder.filter(id => currentIds.has(id));
       if (newIds.length > 0 || filtered.length !== columnOrder.length) {
           columnOrder = [...filtered, ...newIds];
           saveToStorage(getStorageKey('columnOrder'), columnOrder);
           // Also set visibility for new columns
           for (const id of newIds) {
               const col = columns.find(c => c.id === id);
               columnVisibility[id] = col ? !col.hiddenByDefault : true;
           }
           // Remove stale visibility
           for (const id of Object.keys(columnVisibility)) {
               if (!currentIds.has(id)) delete columnVisibility[id];
           }
           saveToStorage(getStorageKey('columnVisibility'), columnVisibility);
       }
   });
   ```

2. **FxTable.svelte — Rimuovere `hiddenByDefault: true`** (riga 194):
   L'utente vuole le colonne Δ visibili di default, con auto-show/hide al variare del periodo.
   Con il fix al punto 1, il `hiddenByDefault` diventa opzionale per il toggle manuale,
   non per colonne che appaiono/scompaiono dinamicamente.

**Nota**: Questo fix risolve anche il caso inverso — quando il range si riduce (es. 1Y → 3M),
le colonne `delta_6M`/`delta_1Y` scompaiono perché non sono più in `columns` (il spread
`...visiblePeriods.map(...)` non le include) e vengono rimosse da `columnOrder`.

**Tasks**:
- [ ] DataTable: aggiungere `$effect` per sync `columnOrder` + `columnVisibility` con colonne dinamiche
- [ ] FxTable: rimuovere `hiddenByDefault: true` dalla definizione colonne Δ periodo (riga 194)
- [ ] Testare: cambiare range da 3M → 6M → 1Y → 3M e verificare colonne appaiono/scompaiono

---

### B8 — Test CSS Scraper: skip condizionale per mercato chiuso

**Area**: Backend test
**Priorità**: 🟢 Test (resiliency)
**File**: `backend/test_scripts/test_external/test_asset_providers.py` (funzione `test_current_value`)

**Problema**: Il test `test_current_value[cssscraper]` fallisce quando il mercato Borsa Italiana
è in stato "Call" (pre-apertura, chiusura, festività). L'elemento `.summary-value strong` esiste
ma è vuoto → `parse_price("")` lancia `AssetSourceError("Empty price text")`.

**Non è un bug del codice**: il CSS scraper funziona correttamente. Il test è fragile perché
dipende dall'orario di mercato.

**Fix**: Aggiungere un `try/except` specifico nel test che cattura `AssetSourceError` con
messaggio "Empty price text" e:
1. Stampa un messaggio esplicativo con la causa probabile (mercato chiuso/Call)
2. Suggerisce come verificare: "Visita la pagina Borsa Italiana e controlla lo status del mercato"
3. Suggerisce di rieseguire il test quando il mercato è aperto
4. Fa `pytest.skip()` con il motivo, non `pytest.fail()`

```python
try:
    result = await provider.get_current_value(identifier, identifier_type, provider_params)
except AssetSourceError as e:
    if "Empty price text" in str(e):
        msg = (
            f"⚠️ CSS Scraper returned empty price text for {identifier}.\n"
            f"   Probable cause: market is closed or in 'Call' status.\n"
            f"   How to verify: open the URL in a browser and check the market status.\n"
            f"   Retry this test when the market is open (Mon-Fri, 9:00-17:30 CET)."
        )
        print_warning(msg)
        pytest.skip(f"Market likely closed: {e}")
    raise  # Re-raise other AssetSourceError types
```

**Tasks**:
- [ ] Aggiungere try/except in `test_current_value` per catturare "Empty price text"
- [ ] Stampare messaggio esplicativo con causa probabile e istruzioni
- [ ] Usare `pytest.skip()` anziché far fallire il test
- [ ] Importare `AssetSourceError` nel file test

---

### B9 — Migrazione test_asset_source.py: `get_prices` → `get_prices_bulk`

**Area**: Backend test
**Priorità**: 🔴 Bug (test rotti — bloccano la suite di test)
**File**: `backend/test_scripts/test_services/test_asset_source.py` (test 10-13)

**Problema**: I test 10, 11, 12 e 13 chiamano `AssetSourceManager.get_prices()`, un metodo che
**non esiste più**. È stato rimosso durante la separazione architetturale Sync/Query.
Il metodo è stato sostituito da `get_prices_bulk()` (riga 1222 di `asset_source.py`).

**Errore**: `AttributeError: type object 'AssetSourceManager' has no attribute 'get_prices'`

**Migrazione per test 10, 11, 12 (backfill puro — solo lettura DB)**:

Questi test inseriscono dati manualmente nel DB e poi li leggono con backward-fill.
Non coinvolgono provider. La migrazione è diretta:

```python
# PRIMA (non esiste più):
prices = await AssetSourceManager.get_prices(
    asset_id=X, start_date=S, end_date=E, session=session)

# DOPO:
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.common import DateRangeModel

results = await AssetSourceManager.get_prices_bulk(
    requests=[FAPriceQueryItem(asset_id=X, date_range=DateRangeModel(start=S, end=E))],
    session=session)
prices = results[0].prices  # list[FAPricePoint] con backward_fill_info
```

**Migrazione per test 13 (Provider Fallback — redesign necessario)**:

Con la nuova architettura, `get_prices_bulk()` **non contatta MAI i provider** — è pura lettura DB.
Il concetto di "fallback su DB quando il provider è invalido" non si applica più nel path di query.

Il test va riscritto per testare la separazione:
1. Inserire provider invalido + dati manuali nel DB
2. **Sync** con provider invalido → deve fallire gracefully (errore catturato, no crash)
3. **Query** dal DB → deve restituire i dati manuali comunque (la query è indipendente dal provider)

Questo testa la robustezza di entrambi i path separatamente, anziché un singolo path combinato.

**Import aggiuntivi** da aggiungere al file test:
```python
from backend.app.schemas.prices import FAPriceQueryItem
from backend.app.schemas.common import DateRangeModel
```

**Tasks**:
- [ ] Aggiungere import `FAPriceQueryItem` e `DateRangeModel` in testa al file
- [ ] Test 10 (`test_get_prices_with_backfill`): migrare a `get_prices_bulk`
- [ ] Test 11 (`test_backward_fill_volume_propagation`): migrare a `get_prices_bulk`
- [ ] Test 12 (`test_backward_fill_edge_case_no_initial_data`): migrare a `get_prices_bulk`
- [ ] Test 13 (`test_provider_fallback_invalid`): riscrivere con sync separato + query
- [ ] Verificare che tutti e 13 i test passino

---

### Riepilogo dipendenze Step 2c

```
B9 (test backend) ──────────────────────────── indipendente, fare per primo (sblocca suite)
B1 (copy) ──────────────────────────────────┐
B3 (stopPropagation) ──────────────────────│── frontend, indipendenti, fare dopo B9
B2 (chartData reset) ─────────────────────│
B8 (test CSS skip) ───────────────────────│── indipendente, fare in parallelo a B1-B3
                                            │
B7 (columnOrder sync) ── prerequisito per corretta visualizzazione colonne
    │
B4 (rimuovere edit, aggiungere sync/refresh) ← dopo B3 (azioni funzionano senza navigate)
    │
    ├── B5 (bulk actions + toolbar esterna) ← dipende da B4 (sync/refresh callback esistono)
    │
    └── B6 (blocco 2×2 Assets) ← dipende da B4 (handleSyncAll/RefreshAll)
```

---

## Step 1 — Fix crash `.toFixed()` su pagina Assets

**Problema**: La pagina `/assets` crasha con `TypeError: O(...).toFixed is not a function`.
L'API backend restituisce `close` come stringa (Python `Decimal` serializzato), ma il frontend
lo usa direttamente come number senza conversione.

**File da modificare**:

### 1a) `src/routes/(app)/assets/+page.svelte` — funzione `fetchPriceData()`

Alle righe ~190-197, wrappare i valori con `Number()`:

```typescript
// PRIMA (crash — close è stringa):
const firstPrice = prices[0]?.close ?? null;
const lastPrice = prices[prices.length - 1]?.close ?? null;

// DOPO:
const firstPrice = prices[0]?.close != null ? Number(prices[0].close) : null;
const lastPrice = prices[prices.length - 1]?.close != null
    ? Number(prices[prices.length - 1].close) : null;
```

Anche `chartData.value`:

```typescript
// PRIMA:
value: p.close ?? 0,

// DOPO:
value: Number(p.close ?? 0),
```

### 1b) `src/lib/components/assets/AssetCard.svelte` — template

Aggiungere guard `Number()` nel template (riga ~128):

```svelte
<!-- PRIMA -->
{lastPrice.toFixed(2)}
{deltaPercent.toFixed(2)}%

<!-- DOPO -->
{Number(lastPrice).toFixed(2)}
{Number(deltaPercent).toFixed(2)}%
```

### 1c) `src/lib/components/assets/AssetTable.svelte`

Verificare che anche la tabella usi `Number()` per i valori `lastPrice`, `deltaAbs`, `deltaPercent`
nelle colonne renderizzate.

### Checklist Step 1

- [ ] `Number()` wrap in `fetchPriceData()` per `firstPrice`, `lastPrice`, `deltaAbs`, `deltaPercent`
- [ ] `Number()` wrap in `chartData.value`
- [ ] `Number()` guard in `AssetCard.svelte` template
- [ ] `Number()` guard in `AssetTable.svelte` colonne Δ
- [ ] Pagina `/assets` si carica senza crash

---

## Step 2 — Migrazione BrokerIcon a Svelte 5 runes

**Problema**: `BrokerIcon.svelte` usa ancora pattern Svelte 4: `export let`, `$:` reactive
statements, `on:load`/`on:error`, `class:opacity-0`. Va migrato a Svelte 5 runes.

**File**: `src/lib/components/brokers/BrokerIcon.svelte`

### Modifiche

| Pattern Svelte 4 | Pattern Svelte 5 |
|-------------------|------------------|
| `export let iconUrl = null` | `let { iconUrl, ... }: Props = $props()` |
| `$: mainPropsKey = ...` | `let mainPropsKey = $derived(...)` |
| `$: if (mainPropsKey !== prev) { ... }` | `$effect(() => { ... })` |
| `on:load={handleLoad}` | `onload={handleLoad}` |
| `on:error={handleError}` | `onerror={handleError}` |
| `class:opacity-0={!imageLoaded}` | `class="... {imageLoaded ? '' : 'opacity-0'}"` |

### Logica da preservare

- Fallback chain: `icon_url` → `portal_url` favicon → `plugin icon_url` → Briefcase
- `onMount` per caricare plugin icons
- `imageKey` per forzare re-render di `<img>` dopo cambio URL
- Reset automatico quando le props cambiano

### Checklist Step 2

- [ ] `export let` → `$props()` con interfaccia `Props`
- [ ] `$:` → `$derived` per `mainPropsKey`
- [ ] `$: if (...)` → `$effect` per reset e plugin load
- [ ] `on:load`/`on:error` → `onload`/`onerror`
- [ ] `class:opacity-0` → ternario in class string
- [ ] `bind:this={imgElement}` mantenuto (invariato in Svelte 5)
- [ ] Test visivo: BrokerIcon funziona con icon_url, con portal fallback, con plugin fallback

---

## Step 3 — Migrazione localStorage a user-scoped

**Problema**: Le preferenze utente sono salvate in localStorage con chiavi globali. In deployment
multi-utente sullo stesso browser (es. due account diversi), le preferenze si sovrascrivono.

**Soluzione**: Usare `getUserStorageKey()` da `$lib/utils/storage.ts` (già creato nello Step 2
di Phase 06). La chiave diventa `lf_{userId}_{baseKey}`.

**NON migrare**: `librefolio-locale` e `librefolio-theme` — servono prima del login (per
Accept-Language header e flash prevention del tema).

**Nessuna migrazione automatica** delle vecchie chiavi — siamo in pre-alpha, le vecchie chiavi
vengono semplicemente ignorate. L'utente perderà le preferenze salvate (sidebar collapsed,
view mode, etc.) ma le ri-selezionerà in pochi click.

### File da modificare

#### 3a) `src/routes/(app)/files/+page.svelte`

Righe ~52-54: 3 chiavi da migrare.

```typescript
// PRIMA:
const STORAGE_KEY_VIEW_MODE = 'filesPage_viewMode';
const STORAGE_KEY_ACTIVE_TAB = 'filesPage_activeTab';
const STORAGE_KEY_BROKER_FILTER = 'filesPage_brokerFilter';
// ... localStorage.getItem(STORAGE_KEY_VIEW_MODE) ...

// DOPO:
import { getUserStorage, setUserStorage } from '$lib/utils/storage';
// Usare getUserStorage('filesPage_viewMode', 'grid') al posto di localStorage.getItem(...)
// Usare setUserStorage('filesPage_viewMode', value) al posto di localStorage.setItem(...)
```

#### 3b) `src/routes/(app)/+layout.svelte` — riga ~32

```typescript
// PRIMA:
const saved = localStorage.getItem('sidebar-collapsed');

// DOPO:
import { getUserStorage } from '$lib/utils/storage';
const saved = getUserStorage('sidebar-collapsed', 'false');
```

#### 3c) `src/lib/components/layout/Sidebar.svelte` — righe ~23, ~68

```typescript
// PRIMA:
const saved = localStorage.getItem('sidebar-collapsed');
localStorage.setItem('sidebar-collapsed', String(collapsed));

// DOPO:
import { getUserStorage, setUserStorage } from '$lib/utils/storage';
const saved = getUserStorage('sidebar-collapsed', 'false');
setUserStorage('sidebar-collapsed', String(collapsed));
```

#### 3d) `src/lib/components/table/DataTable.svelte` — riga ~158

```typescript
// PRIMA:
function getStorageKey(suffix: string): string {
    return `dataTable_${storageKey}_${suffix}`;
}

// DOPO:
import { getUserStorageKey } from '$lib/utils/storage';
function getStorageKey(suffix: string): string {
    return getUserStorageKey(`dataTable_${storageKey}_${suffix}`);
}
```

#### 3e) `src/lib/utils/storage.ts` — rimuovere il TODO

Rimuovere il commento `TODO: Existing localStorage keys ... should eventually be migrated`
dato che la migrazione la stiamo facendo ora (senza migrazione automatica delle vecchie chiavi).

### Checklist Step 3

- [ ] `files/+page.svelte`: 3 chiavi → `getUserStorage` / `setUserStorage`
- [ ] `+layout.svelte`: `sidebar-collapsed` → `getUserStorage`
- [ ] `Sidebar.svelte`: `sidebar-collapsed` → `getUserStorage` + `setUserStorage`
- [ ] `DataTable.svelte`: `getStorageKey` → usa `getUserStorageKey`
- [ ] `storage.ts`: TODO rimosso
- [ ] Nessuna funzione `migrateStorageKey` (pre-alpha, non serve)

---

## Step 4 — Fix FX delete 422

**Problema**: In `FxDataEditorSection.svelte` (riga ~191), la delete invia `date_range` come
array `[{start: "2026-01-01"}]`, ma il backend `FXDeleteItem.date_range` si aspetta un singolo
oggetto `DateRangeModel`.

**Root cause**: Bug **frontend**. Lo schema backend `FXDeleteItem.date_range` è
`Optional[DateRangeModel]` — un singolo oggetto `{start, end?}`, non un array. Il frontend
erroneamente costruisce `date_range: deleteRows.map(dr => ({start: dr.date}))` che produce
un array. La soluzione è generare un `FXDeleteItem` separato per ogni data da eliminare.

**Errore backend**:
```json
{
  "type": "model_attributes_type",
  "loc": ["body", 0, "date_range"],
  "msg": "Input should be a valid dictionary or object to extract fields from",
  "input": [{"start": "2026-01-01"}]
}
```

**File**: `src/lib/components/fx/FxDataEditorSection.svelte`

### Fix

```typescript
// PRIMA (riga ~189-194):
const deleteItems = [{
    from: base < quote ? base : quote,
    to: base < quote ? quote : base,
    date_range: deleteRows.map(dr => ({start: dr.date})),
}];

// DOPO:
const baseNormDel = base < quote ? base : quote;
const quoteNormDel = base < quote ? quote : base;
const deleteItems = deleteRows.map(dr => ({
    from: baseNormDel,
    to: quoteNormDel,
    date_range: { start: dr.date },
}));
```

### Checklist Step 4

- [ ] `date_range` da array → oggetto singolo per item
- [ ] Un `FXDeleteItem` per ogni data da eliminare
- [ ] Test: eliminazione singola data funziona (no 422)
- [ ] Test: eliminazione multipla date funziona (batch di items)

---

## Step 5 — Fix FX detail UX per coppie manual-only

**Problema**: Se una coppia FX è manual-only (nessun provider reale, solo MANUAL), nella pagina
detail:
1. Il chart empty state mostra "Sync Rates" che non ha senso senza provider
2. Il bottone Sync nella matrice 2×2 dell'action bar è cliccabile ma non può fare nulla

**File**: `src/routes/(app)/fx/[pair]/+page.svelte`

### Modifiche

#### 5a) Aggiungere variabile derivata

```typescript
// Dopo il caricamento providers (loadProviders), dove i MANUAL sono già filtrati:
let isManualOnly = $derived(providers.length === 0);
```

La variabile `providers` (riga ~298-299) esclude già il provider MANUAL sentinel dal filtro,
quindi `providers.length === 0` indica "nessun provider reale configurato".

#### 5b) Modificare il blocco `:else` del chart (righe ~764-776)

```svelte
<!-- PRIMA: -->
{:else}
    <div class="h-96 flex items-center justify-center">
        <div class="text-center">
            <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('fxDetail.noData')}</p>
            <button
                class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg ..."
                onclick={handleSync}
                disabled={syncing}
            >
                {syncing ? $t('fx.syncing') : $t('fxDetail.syncRates')}
            </button>
        </div>
    </div>
{/if}

<!-- DOPO: -->
{:else}
    <div class="h-96 flex items-center justify-center">
        <div class="text-center">
            {#if isManualOnly}
                <p class="text-gray-400 dark:text-gray-500 mb-3">
                    {$t('fxDetail.noDataManual')}
                </p>
                <button
                    class="px-4 py-2 text-sm bg-amber-500 text-white rounded-lg
                           hover:bg-amber-600 transition-colors"
                    onclick={() => { showDataEditor = true; }}
                >
                    {$t('fxDetail.insertManually')}
                </button>
            {:else}
                <p class="text-gray-400 dark:text-gray-500 mb-3">{$t('fxDetail.noData')}</p>
                <button
                    class="px-4 py-2 text-sm bg-libre-green text-white rounded-lg
                           hover:bg-libre-green/90 transition-colors"
                    onclick={handleSync}
                    disabled={syncing}
                >
                    {syncing ? $t('fx.syncing') : $t('fxDetail.syncRates')}
                </button>
            {/if}
        </div>
    </div>
{/if}
```

#### 5c) Disabilitare il bottone Sync nella matrice 2×2 (riga ~626-634)

Come nel `fx/+page.svelte` dove Sync All è sempre attivo perché opera solo sulle coppie con
provider, nella pagina detail il bottone Sync nella matrice 2×2 deve essere **disabilitato**
quando `isManualOnly`:

```svelte
<!-- PRIMA (riga ~626-634): -->
<button
    data-testid="fx-detail-sync-btn"
    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs ..."
    onclick={handleSync}
    disabled={syncing}
>
    <RotateCw size={14} class={syncing ? 'animate-spin' : ''} />
    {#if showActionLabels}<span>{syncing ? $t('fx.syncing') : $t('common.sync')}</span>{/if}
</button>

<!-- DOPO: -->
<button
    data-testid="fx-detail-sync-btn"
    class="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-xs ...
           {isManualOnly ? 'opacity-50 cursor-not-allowed' : ''}"
    onclick={handleSync}
    disabled={syncing || isManualOnly}
    title={isManualOnly ? $t('fxDetail.syncDisabledManual') : ''}
>
    <RotateCw size={14} class={syncing ? 'animate-spin' : ''} />
    {#if showActionLabels}<span>{syncing ? $t('fx.syncing') : $t('common.sync')}</span>{/if}
</button>
```

#### 5d) Nuove chiavi i18n (da aggiungere con `./dev.py i18n add`)

| Chiave | EN | IT |
|--------|----|----|
| `fxDetail.noDataManual` | `No data available — insert rates manually` | `Nessun dato disponibile — inserire i tassi manualmente` |
| `fxDetail.insertManually` | `Insert Manually` | `Inserisci manualmente` |
| `fxDetail.syncDisabledManual` | `Sync disabled — no provider configured. Add a provider or insert rates manually.` | `Sync disabilitato — nessun provider configurato. Aggiungere un provider o inserire i tassi manualmente.` |

### Checklist Step 5

- [ ] `isManualOnly` derivato da `providers.length === 0`
- [ ] Blocco `:else` del chart: se manual-only → testo diverso + apre editor
- [ ] Se non manual-only → mantiene "Sync Rates" come prima
- [ ] Bottone Sync nella matrice 2×2: `disabled={syncing || isManualOnly}` + `opacity-50`
- [ ] 3 nuove chiavi i18n aggiunte con `./dev.py i18n add`
- [ ] Test: coppia manual-only → Sync disabilitato + chart mostra "Inserisci manualmente"
- [ ] Test: coppia con provider → Sync attivo + chart mostra "Sync Rates"

---

## Step 6 — Spostare ViewModeToggle nell'header

**Problema**: Il `ViewModeToggle` è dentro la filter bar (matrice 2×2 nelle pagine FX), che
rovina l'estetica. Va spostato nell'header, tra il titolo e il bottone "Add".

**File da modificare**:
- `src/routes/(app)/assets/+page.svelte`
- `src/routes/(app)/fx/+page.svelte`

### 6a) Assets page

Spostare `ViewModeToggle` dalla filter bar (riga ~360) all'header row, tra titolo e bottone Add:

```svelte
<!-- Header -->
<div class="flex items-center justify-between">
    <div>
        <h2>...</h2>
        <p>...</p>
    </div>
    <div class="flex items-center gap-2">
        <ViewModeToggle bind:mode={viewMode} storageKey="assetsViewMode" />
        <button onclick={handleAddAsset}>
            <Plus size={16} /> {$t('assets.addAsset')}
        </button>
    </div>
</div>
```

Rimuovere il `ViewModeToggle` dalla filter bar.

### 6b) FX page

Identico: spostare dalla matrice 2×2 (riga ~621) all'header row, prima del bottone "Add Pair":

```svelte
<div class="flex items-center gap-2">
    <ViewModeToggle bind:mode={viewMode} storageKey="fxViewMode" />
    <button onclick={handleAddPair}>
        <Plus size={16} /> {$_('fx.actions.addPair')}
    </button>
</div>
```

La matrice 2×2 degli actions resta invariata ma senza il toggle.

### Checklist Step 6

- [ ] Assets: ViewModeToggle nell'header (tra titolo e Add)
- [ ] Assets: Rimosso dalla filter bar
- [ ] FX: ViewModeToggle nell'header (tra titolo e Add Pair)
- [ ] FX: Rimosso dalla matrice 2×2
- [ ] Layout visivamente pulito in entrambe le pagine

---

## Step 7 — Endpoint bulk asset prices + colonne Δ multi-periodo

**Approccio**: I dati prezzi sono già nel DB (nessuna chiamata ai provider), quindi il costo
di scaricare l'intera serie storica è trascurabile. Sia in grid che in table si scaricano
**sempre tutti i giorni** nel range selezionato. Nessun fetch differenziato grid/table,
nessun refresh al cambio vista.

Lo Step si compone di 3 parti:
1. **7a — Backend**: creare endpoint bulk `POST /assets/prices/query`
2. **7b — Test migration**: migrare tutti i test che usano `GET /assets/prices/{id}` alla nuova POST
3. **7c — Frontend**: colonne Δ multi-periodo nella tabella + migrazione a bulk endpoint

### 7a) Backend — Nuovo endpoint `POST /assets/prices/query` (bulk)

Creare un endpoint bulk analogo a `POST /fx/currencies/convert` per gli asset prices.
L'endpoint attuale `GET /assets/prices/{asset_id}` viene **eliminato** (delegava ai provider
ad ogni lettura — disallineato con FX). Il nuovo endpoint è l'unico modo per leggere prezzi.

#### Schema — usare archetipi di `common.py`

**File**: `backend/app/schemas/prices.py`

Seguire il pattern FX: `FXConversionRequest` → `FXConversionResult` → `FXConvertResponse(BaseBulkResponse[Result])`.
Per la price query non ci sono errori per-item (è una lettura), quindi usare
`BaseListResponse[T]` che ha solo `items: List[T]`.

```python
from backend.app.schemas.common import DateRangeModel, BaseListResponse


class FAPriceQueryItem(BaseModel):
    """Single asset price query in a bulk request.

    Uses DateRangeModel from common.py (same as FXConversionRequest.date_range).
    If date_range.end is None, defaults to date_range.start (single day).
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID to query")
    date_range: DateRangeModel = Field(..., description="Date range (end defaults to start)")


class FAPriceQueryResult(BaseModel):
    """Response for a single asset price query."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID queried")
    prices: List[FAPricePoint] = Field(default_factory=list, description="Price history with backward-fill")


class FAPriceQueryResponse(BaseListResponse[FAPriceQueryResult]):
    """Bulk response for price queries.

    Inherits from BaseListResponse[FAPriceQueryResult]:
    - items: List[FAPriceQueryResult]  (one per asset queried)
    """
    pass
```

Export in `schemas/__init__.py`: `FAPriceQueryItem`, `FAPriceQueryResult`, `FAPriceQueryResponse`.

#### Service layer — query bulk con singola lettura DB

**File**: `backend/app/services/asset_source.py`

Aggiungere un metodo statico `get_prices_bulk` al `AssetSourceManager` che fa **una sola
query SQL** per tutti gli asset, poi partiziona e applica backward-fill per ognuno.

Pattern identico a `fx.py → convert_bulk()` (riga 1440-1460): una singola query con
`WHERE asset_id IN (...) AND date BETWEEN start AND end`, poi elaborazione in memoria.

```python
@staticmethod
async def get_prices_bulk(
    requests: list[FAPriceQueryItem],
    session: AsyncSession,
) -> list[FAPriceQueryResult]:
    """Bulk query prices for multiple assets with a single DB read.

    Fetches all prices in one query and partitions the result by asset_id.
    Each asset then gets its own backward-filled series.

    We don't use asyncio.gather here because all work is a single DB query
    followed by in-memory processing — there's no I/O parallelism to exploit
    since it's always this same process executing the flow sequentially.

    This method reads ONLY from DB — it does NOT delegate to providers.
    Provider fetch is a separate operation (POST /assets/prices/refresh).
    For the list/detail pages, data should already be in DB after refresh.
    """
    if not requests:
        return []

    # Collect all unique asset_ids and compute the global date range
    asset_ids = list({req.asset_id for req in requests})

    # Build per-asset date ranges (different assets could have different ranges)
    asset_ranges: dict[int, tuple[date_type, date_type]] = {}
    for req in requests:
        end = req.date_range.end or req.date_range.start
        asset_ranges[req.asset_id] = (req.date_range.start, end)

    # Compute global min/max date for single query
    global_start = min(r[0] for r in asset_ranges.values())
    global_end = max(r[1] for r in asset_ranges.values())

    # Single DB query for ALL assets in the date range
    stmt = (
        select(PriceHistory)
        .where(
            and_(
                PriceHistory.asset_id.in_(asset_ids),
                PriceHistory.date >= global_start,
                PriceHistory.date <= global_end,
            )
        )
        .order_by(PriceHistory.asset_id, PriceHistory.date)
    )
    db_result = await session.execute(stmt)
    all_prices = db_result.scalars().all()

    # Partition by asset_id
    price_maps: dict[int, dict[date_type, PriceHistory]] = {aid: {} for aid in asset_ids}
    for p in all_prices:
        if p.asset_id in price_maps:
            price_maps[p.asset_id][p.date] = p

    # Build backward-filled series per asset (preserving request order)
    results = []
    for req in requests:
        aid = req.asset_id
        start, end = asset_ranges[aid]
        price_map = price_maps.get(aid, {})
        series = AssetSourceManager._build_backward_filled_series(price_map, start, end)
        results.append(FAPriceQueryResult(asset_id=aid, prices=series))

    return results
```

#### Endpoint

**File**: `backend/app/api/v1/assets.py`

```python
@price_router.post("/query", response_model=FAPriceQueryResponse)
async def query_prices_bulk(
    requests: List[FAPriceQueryItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """Bulk query prices for multiple assets.

    Reads from DB only (no provider delegation). Uses a single SQL query
    for all assets, then applies backward-fill per asset.
    Analogous to POST /fx/currencies/convert for FX rates.
    """
    results = await AssetSourceManager.get_prices_bulk(requests, session)
    return FAPriceQueryResponse(items=results)
```

Eliminare il vecchio endpoint GET e il metodo `get_prices()`:

**In `assets.py`**: rimuovere l'intero blocco `@price_router.get("/{asset_id}", ...)` e la
funzione `async def get_prices(...)` (righe 556-583).

**In `asset_source.py`**: rimuovere il metodo `get_prices()` (righe 1222-1257). La logica
di provider delegation (`_fetch_provider_history`) resta nel codice perché è usata da
`bulk_refresh_prices()` — ma non viene più invocata durante una lettura.

Dopo: `./dev.py api sync` per rigenerare il client Zodios (il metodo
`get_prices_api_v1_assets_prices__asset_id__get` scomparirà dal client generato).

### 7b) Test migration — da GET a POST bulk

Migrare **tutti** i test che usano `GET /assets/prices/{asset_id}` alla nuova
`POST /assets/prices/query`. Il GET viene eliminato, quindi i test **devono** essere
migrati per continuare a funzionare.

**File da modificare**:

| File | Occorrenze GET | Descrizione |
|------|---------------|-------------|
| `backend/test_scripts/test_api/test_assets_prices.py` | 4 (righe 103, 151, 214, 278) | Test 1 (verifica upsert), Test 2 (get history), Test 3 (verifica delete), Test 4 (verifica refresh) |
| `backend/test_scripts/test_e2e/test_search_to_prices.py` | 1 (riga 247) | Step 6: verify prices exist |

**Pattern di migrazione**:

```python
# PRIMA (GET singolo):
get_resp = await client.get(
    f"{API_BASE}/assets/prices/{asset_id}",
    params={"start_date": "2025-01-01", "end_date": "2025-01-05"},
    timeout=TIMEOUT,
)
assert get_resp.status_code == 200
price_history = get_resp.json()

# DOPO (POST bulk):
query_resp = await client.post(
    f"{API_BASE}/assets/prices/query",
    json=[{
        "asset_id": asset_id,
        "date_range": {"start": "2025-01-01", "end": "2025-01-05"},
    }],
    timeout=TIMEOUT,
)
assert query_resp.status_code == 200
query_data = query_resp.json()
price_history = query_data["items"][0]["prices"]
```

Aggiornare anche il docstring del file test e i commenti delle sezioni.

**Nota**: aggiungere anche un test specifico per il bulk con **più asset** in una singola
richiesta (query per 2-3 asset diversi in un unico POST), per validare il comportamento bulk.

### 7c) Frontend — Colonne Δ multi-periodo + migrazione a bulk

**File**: `src/routes/(app)/assets/+page.svelte`, `src/lib/components/assets/AssetTable.svelte`

#### Migrazione fetch a bulk

L'endpoint `GET /assets/prices/{id}` viene eliminato. Sostituire le N chiamate
`zodiosApi.get_prices_api_v1_assets_prices__asset_id__get(...)` con una singola
`POST /assets/prices/query`:

```typescript
async function fetchAllPriceData() {
    const queries = assets.map(a => ({
        asset_id: a.id,
        date_range: { start: dateStart, end: dateEnd },
    }));

    const response = await zodiosApi.query_prices_bulk_...(queries);
    const items = response.items;  // BaseListResponse → items

    for (const result of items) {
        const idx = assets.findIndex(a => a.id === result.asset_id);
        if (idx < 0) continue;
        const prices = result.prices;
        // ... stessa logica di prima per popolare lastPrice, deltas, chartData
    }
}
```

#### Colonne Δ multi-periodo

La tabella mostra **colonne Δ dinamiche** basate sulla larghezza del range temporale
selezionato. Se il range è sufficientemente ampio, appaiono colonne aggiuntive per i
periodi standard. Se il range si restringe, le colonne scompaiono automaticamente.

**Periodi disponibili**:

| Periodo | Sigla | Giorni approx. | Visibile se range ≥ |
|---------|-------|----------------|---------------------|
| 1 settimana | 1W | 7 | 7 giorni |
| 1 mese | 1M | 30 | 30 giorni |
| 3 mesi | 3M | 91 | 91 giorni |
| 6 mesi | 6M | 182 | 182 giorni |
| 1 anno | 1Y | 365 | 365 giorni |
| 2 anni | 2Y | 730 | 730 giorni |
| 3 anni | 3Y | 1095 | 1095 giorni |
| 5 anni | 5Y | 1825 | 1825 giorni |

**Calcolo Δ per ogni periodo**:

```
Δ% = (Pₙ - P_start) / P_start × 100
```

dove:
- **Pₙ** = prezzo all'ultimo giorno del range selezionato (non necessariamente oggi)
- **P_start** = prezzo alla data `Pₙ - periodo`
- Se `Pₙ - periodo` cade prima dell'inizio del range, la colonna **non viene mostrata**
- Per trovare il prezzo a una data specifica, si cerca il data point più vicino ≤ target
  nel `chartData` già scaricato (backward-fill)

```typescript
const DELTA_PERIODS = [
    { key: '1W', days: 7 },
    { key: '1M', days: 30 },
    { key: '3M', days: 91 },
    { key: '6M', days: 182 },
    { key: '1Y', days: 365 },
    { key: '2Y', days: 730 },
    { key: '3Y', days: 1095 },
    { key: '5Y', days: 1825 },
] as const;

// Quali periodi sono visibili per il range corrente
let visiblePeriods = $derived(
    DELTA_PERIODS.filter(p => {
        const rangeMs = new Date(dateEnd).getTime() - new Date(dateStart).getTime();
        const rangeDays = rangeMs / (1000 * 60 * 60 * 24);
        return rangeDays >= p.days;
    })
);

// Per un asset, calcola Δ% per un dato periodo
function computePeriodDelta(
    chartData: Array<{date: string; value: number}>,
    periodDays: number,
): number | null {
    if (chartData.length === 0) return null;

    // Pₙ = ultimo punto nel chartData
    const pn = chartData[chartData.length - 1];
    if (!pn || pn.value === 0) return null;

    // Data target = Pₙ - periodo
    const targetDate = new Date(pn.date);
    targetDate.setDate(targetDate.getDate() - periodDays);
    const targetStr = targetDate.toISOString().slice(0, 10);

    // Cerca il punto più vicino <= targetDate (backward-fill)
    let startPoint: {date: string; value: number} | null = null;
    for (const point of chartData) {
        if (point.date <= targetStr) {
            startPoint = point;
        } else {
            break;
        }
    }

    if (!startPoint || startPoint.value === 0) return null;
    return ((pn.value - startPoint.value) / startPoint.value) * 100;
}
```

**AssetState esteso**: aggiungere un campo `deltas`:

```typescript
interface AssetState extends AssetInfo {
    // ...existing fields...
    deltas: Record<string, number | null>;  // key = '1W' | '1M' | etc.
}
```

`deltas` viene calcolato dopo il fetch di `chartData`:

```typescript
const deltas: Record<string, number | null> = {};
for (const period of DELTA_PERIODS) {
    deltas[period.key] = computePeriodDelta(chartData, period.days);
}
```

#### `AssetTable.svelte` — Colonne dinamiche

La tabella riceve `visiblePeriods` come prop e genera colonne DataTable dinamiche:

**Colonne tabella** (ordine):

| Colonna | Sempre visibile | Nota |
|---------|-----------------|------|
| Name | ✅ | Icon + display_name |
| Type | ✅ | Badge colorato |
| Currency | ✅ | Flag emoji + codice |
| Last Price | ✅ | Ultimo close |
| Δ 1W | ❌ (se range ≥ 7g) | % con colore verde/rosso |
| Δ 1M | ❌ (se range ≥ 30g) | % |
| Δ 3M | ❌ (se range ≥ 91g) | % |
| Δ 6M | ❌ (se range ≥ 182g) | % |
| Δ 1Y | ❌ (se range ≥ 365g) | % |
| Δ 2Y | ❌ (se range ≥ 730g) | % |
| Δ 3Y | ❌ (se range ≥ 1095g) | % |
| Δ 5Y | ❌ (se range ≥ 1825g) | % |
| Provider | ✅ | ✅/❌ |
| Active | ✅ | Badge |
| Actions | ✅ | Edit, Delete |

Ogni cella Δ mostra: **Verde** (▲) se positivo, **Rosso** (▼) se negativo, **—** se null.

#### Card — invariata

La card continua a mostrare il Δ del range completo (P₀ → Pₙ) come prima.

#### FX — stessa logica applicabile in futuro

Per ora FxTable mantiene il singolo Δ del range. La logica multi-periodo potrà essere
replicata su FxTable in futuro.

### Checklist Step 7

**Backend**:
- [ ] `FAPriceQueryItem`, `FAPriceQueryResult` in `prices.py` (con `ConfigDict(extra="forbid")`)
- [ ] `FAPriceQueryResponse(BaseListResponse[FAPriceQueryResult])` in `prices.py`
- [ ] `AssetSourceManager.get_prices_bulk()` in `asset_source.py` — singola query DB, partiziona per `asset_id`, backward-fill per asset
- [ ] `POST /assets/prices/query` endpoint in `assets.py` (chiama `get_prices_bulk`)
- [ ] **Eliminare** `GET /assets/prices/{asset_id}` endpoint da `assets.py`
- [ ] **Eliminare** `get_prices()` da `asset_source.py` (la logica provider delegation resta solo in `refresh`)
- [ ] `./dev.py api sync` (il client Zodios non genererà più il metodo GET prices)
- [ ] Export nuovi schemi in `schemas/__init__.py`

**Test migration**:
- [ ] `test_assets_prices.py`: migrare 4 occorrenze GET → POST bulk
- [ ] `test_search_to_prices.py`: migrare 1 occorrenza GET → POST bulk (Step 6 verify)
- [ ] Aggiungere test specifico per bulk multi-asset (2-3 asset in una POST)
- [ ] Tutti i test passano con la nuova POST

**Frontend**:
- [ ] `fetchAllPriceData()` usa una singola `POST /assets/prices/query` invece di N GET
- [ ] `DELTA_PERIODS` costante definita
- [ ] `visiblePeriods` derivato dalla larghezza del range selezionato
- [ ] `computePeriodDelta()` funzione helper (backward-fill lookup)
- [ ] `AssetState.deltas` calcolato dopo fetch di `chartData`
- [ ] `AssetTable.svelte`: prop `visiblePeriods`, colonne Δ dinamiche
- [ ] Celle Δ con colore verde/rosso e `—` per null
- [ ] Colonne appaiono/scompaiono cambiando il range nel DateRangePicker
- [ ] Card invariata (mostra solo Δ full-range)

---

## Step 8 — Fix test upload 401

**Problema**: `test_plugin_static_not_found` (riga ~317 di `test_uploads_api.py`) fa una GET
senza autenticazione, ma l'endpoint restituisce 401 perché richiede `Depends(get_current_user)`.
Il test attende 404.

**File**: `backend/test_scripts/test_api/test_uploads_api.py`

### Fix

Aggiungere `create_user_and_login(client)` prima della richiesta, come fanno gli altri test
della stessa suite:

```python
@pytest.mark.asyncio
async def test_plugin_static_not_found(self, test_server):
    """UPLOAD-011: 404 for non-existent plugin asset."""
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)  # <-- aggiunto
        response = await client.get(
            f"{API_BASE}/uploads/plugin/brim/nonexistent/logo.png",
            timeout=TIMEOUT
        )
        assert response.status_code == 404
```

### Checklist Step 8

- [ ] `create_user_and_login(client)` aggiunto
- [ ] Test passa (`assert 404 == 404`)
- [ ] Tutti i test upload passano

---

## Step 9 — Rimuovere chiave i18n orfana

**Problema**: L'audit i18n rileva `assets.placeholderMessage` come chiave inutilizzata.

**Comando**:

```bash
./dev.py i18n remove assets.placeholderMessage
```

### Checklist Step 9

- [ ] Chiave rimossa da en.json, it.json, fr.json, es.json
- [ ] `./dev.py i18n audit` non rileva più chiavi inutilizzate

---

## Step 12 — Fix crash JustETF search (`.fillna` su colonne con NaN)

**Problema**: La ricerca JustETF fallisce con `sequence item 2: expected str instance, float found`.
Il metodo `search()` cerca di fare `" ".join()` sulle colonne `["name", "ticker", "wkn"]` del
DataFrame, ma la colonna `wkn` (indice 2) contiene valori `float` (`NaN`) quando il dato originale
è mancante o numerico. Il `.astype(str)` da solo non gestisce in modo affidabile `NaN`/`pd.NA` in
tutte le versioni di pandas — `" ".join()` riceve un `float` e crasha.

**Test falliti**: `test_search_assets_semiconductor` (Test 7), `test_search_assets_provider_filter`
(Test 8), `test_search_to_asset_e2e` (Test 13 — parzialmente)

**Log errore**:
```
ERROR  asset_source.py:2351 "Search error from provider 'justetf':
  Search failed for 'Semiconductor' on JustETF: sequence item 2: expected str instance, float found"
```

**File**: `backend/app/services/asset_source_providers/justetf.py`, righe 266-270

**Root cause**: `load_overview()` dalla libreria `justetf-scraping` restituisce un DataFrame in cui
la colonna `wkn` può essere tipizzata come `float64` (quando valori mancanti producono `NaN` nel
DataFrame). La sequenza `.astype(str).agg(" ".join, axis=1)` non converte in modo affidabile tutti
i `NaN` a stringa prima del join.

### Fix

```python
# PRIMA (riga 268-270 — crash se wkn ha NaN):
mask_cols = (
    df_all[cols_only].astype(str).agg(" ".join, axis=1).str.contains(query, case=False)
)

# DOPO (fillna forza tutti i NaN a stringa vuota prima del join):
mask_cols = (
    df_all[cols_only].fillna('').astype(str).agg(" ".join, axis=1).str.contains(query, case=False)
)
```

### Checklist Step 12

- [ ] Aggiungere `.fillna('')` prima di `.astype(str)` nella riga 268 di `justetf.py`
- [ ] Test: `test_search_assets_semiconductor` passa (JustETF trova ETF semiconduttori)
- [ ] Test: `test_search_assets_provider_filter` passa (JustETF trova ETF MSCI)
- [ ] Test: `test_search_to_asset_e2e` non ha più errore JustETF search

---

## Step 13 — Fix `FAAssetCreateResult` extra field `identifier`

**Problema**: La creazione asset fallisce con `Extra inputs are not permitted` quando il
`display_name` esiste già (es. "Microsoft Corporation" da un test precedente). Il codice di
controllo duplicati passa `identifier=None` a `FAAssetCreateResult`, ma lo schema ha
`ConfigDict(extra="forbid")` e non prevede il campo `identifier`.

**Test falliti**: `test_search_to_asset_e2e` (Test 13)

**Log errore**:
```
ERROR  asset_source.py:1645 "Error creating asset Microsoft Corporation:
  1 validation error for FAAssetCreateResult
  identifier
    Extra inputs are not permitted [type=extra_forbidden, input_value=None, input_type=NoneType]"
```

**File**: `backend/app/services/asset_source.py`, righe 1596-1604

**Root cause**: Nel branch di controllo duplicati (riga 1595-1604), viene passato
`identifier=None` al costruttore di `FAAssetCreateResult`. Questo campo **non esiste** nello
schema (che ha solo: `asset_id`, `success`, `message`, `display_name`). La `ValidationError` di
Pydantic viene catturata dal `except Exception` esterno (riga 1644), mascherando il messaggio
di errore originale ("already exists").

### Schema di riferimento (`backend/app/schemas/assets.py`, righe 722-730)

```python
class FAAssetCreateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: Optional[int] = Field(None, description="Created asset ID (null if failed)")
    success: bool = Field(..., description="Whether creation succeeded")
    message: str = Field(..., description="Success message or error description")
    display_name: str = Field(..., description="Asset display name (for identification)")
```

### Fix

```python
# PRIMA (riga 1596-1604):
results.append(
    FAAssetCreateResult(
        asset_id=None,
        success=False,
        message=f"Asset with display_name '{item.display_name}' already exists",
        display_name=item.display_name,
        identifier=None,  # <-- BUG: campo extra non nello schema
    )
)

# DOPO:
results.append(
    FAAssetCreateResult(
        asset_id=None,
        success=False,
        message=f"Asset with display_name '{item.display_name}' already exists",
        display_name=item.display_name,
    )
)
```

### Checklist Step 13

- [ ] Rimuovere `identifier=None` dalla riga 1602 di `asset_source.py`
- [ ] Test: creazione asset con `display_name` duplicato restituisce `success=False` con messaggio "already exists" (non più un errore Pydantic)
- [ ] Test: `test_search_to_asset_e2e` crea asset con successo (se display_name unico)

---

## Step 14 — Migrazione COMPLETA test all'architettura Sync→Query

**Problema architetturale**:
Il vecchio `GET /assets/prices/{asset_id}` era un anti-pattern: faceva **Sync + Query** in un'unica
chiamata. Se l'asset aveva un provider assegnato, il GET contattava il provider (HTTP call esterna),
salvava i dati nel DB, poi li restituiva. Ogni lettura = potenziale chiamata HTTP.

Con la nuova architettura (Step 7a), il flusso è separato in due operazioni indipendenti:
1. **Sync** (`POST /assets/prices/refresh`): provider → DB — solo su richiesta esplicita
2. **Query** (`POST /assets/prices/query`): DB → frontend — pura lettura, zero side-effect

I test devono riflettere questa separazione: **prima sync, poi query**.

### Stato migrazioni GET→POST

Tutti i test che usavano il vecchio `GET /assets/prices/{asset_id}` sono stati migrati a
`POST /assets/prices/query`. Nessun file di test contiene più il vecchio endpoint.

| File | Test | Vecchio | Nuovo | Sync prima? | Stato |
|------|------|---------|-------|-------------|-------|
| `test_assets_prices.py` | Test 1 (upsert → read) | GET | POST /query | N/A (upsert manuale) | ✅ |
| `test_assets_prices.py` | Test 2 (history) | GET | POST /query | N/A (upsert manuale) | ✅ |
| `test_assets_prices.py` | Test 3 (delete → read) | GET | POST /query | N/A (upsert manuale) | ✅ |
| `test_assets_prices.py` | Test 4 (refresh → read) | GET | POST /query | ✅ POST /refresh | ✅ |
| `test_assets_prices.py` | Test 5 (multi-asset bulk) | — | POST /query | N/A (upsert manuale) | ✅ |
| `test_search_to_prices.py` | Step 5→6 (refresh → verify) | GET | POST /query | ✅ POST /refresh | ✅ |
| `test_assets_provider.py` | Test 13 Step 6→7 (e2e) | GET | POST /query | ✅ POST /refresh | ✅ |
| `test_assets_provider.py` | Test 14 (current value) | GET | POST /query | ✅ POST /refresh | ✅ |
| `test_assets_provider.py` | Test 15 (CSS scraper) | GET | POST /query | ✅ POST /refresh | ✅ |

**Nota**: I test 1-3, 5 di `test_assets_prices.py` usano **upsert manuale** (`POST /assets/prices`)
per inserire dati nel DB prima della query. Non passano per il provider — il flusso è:
`upsert → query`, non `sync → query`. Questo è corretto: testano il CRUD puro, non il provider.

I test 4, 14, 15 di provider e il test e2e usano **sync via provider** (`POST /assets/prices/refresh`)
prima della query. Questo è il pattern corretto per testare il flusso provider → DB → frontend.

### Residuo: label nel test_runner.py

`scripts/test_runner.py` riga 917 ha ancora il label del vecchio endpoint:
```python
print_info("Tests: GET /assets/prices/{asset_id}")  # → da aggiornare
```

### Checklist Step 14

- [x] `test_assets_prices.py` — Test 1-5: tutti migrati a POST /query
- [x] `test_search_to_prices.py` — Step 6: migrato a POST /query
- [x] `test_assets_provider.py` — Test 13 Step 7: migrato a POST /query
- [x] `test_assets_provider.py` — Test 14: migrato a POST /query
- [x] `test_assets_provider.py` — Test 15: migrato a POST /query
- [ ] Tutti i test che leggono dal DB dopo sync hanno il sync esplicito prima (confermato ✅)
- [ ] `scripts/test_runner.py` riga 917: aggiornare label
- [ ] Grep finale: `grep -r "assets/prices/{" backend/` restituisce 0 risultati

---

## Step 15 — Test runner label + nuovo test "query senza sync = vuoto"

**Obiettivo**: Certificare il nuovo comportamento architetturale con un test dedicato.

### 15a — Aggiornare label test_runner.py

`scripts/test_runner.py` riga 917:
```python
# PRIMA:
print_info("Tests: GET /assets/prices/{asset_id}")

# DOPO:
print_info("Tests: POST /assets/prices/query (bulk read from DB)")
```

### 15b — Nuovo test: query senza sync restituisce vuoto

Questo test **certifica** che la separazione Sync/Query funziona come previsto:
un asset con provider assegnato ma MAI sincronizzato non ha dati nel DB.

```python
@pytest.mark.asyncio
async def test_query_without_sync_returns_empty(test_server):
    """Test: Query on asset with provider but no sync returns empty prices.
    
    Certifies the architectural separation:
    - Assigning a provider does NOT auto-fetch prices
    - Prices appear in DB only after explicit sync (POST /assets/prices/refresh)
    - Query (POST /assets/prices/query) reads ONLY from DB, never from provider
    """
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        
        # 1. Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"No-Sync Test {unique_id('NOSYNC')}",
            currency="USD", asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[asset_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id
        
        # 2. Assign provider (yfinance/AAPL — ha sempre dati)
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id, provider_code="yfinance",
            identifier="AAPL", identifier_type=IdentifierType.TICKER,
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        
        # 3. Query SENZA sync — deve restituire 0 prezzi
        today = date.today()
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{
                "asset_id": asset_id,
                "date_range": {
                    "start": (today - timedelta(days=7)).isoformat(),
                    "end": today.isoformat(),
                },
            }],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200
        prices = query_resp.json()["items"][0]["prices"]
        assert len(prices) == 0, f"Expected 0 prices before sync, got {len(prices)}"
        
        # 4. Sync esplicita — scarica dal provider nel DB
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/refresh",
            json=[{
                "asset_id": asset_id,
                "date_range": {
                    "start": (today - timedelta(days=7)).isoformat(),
                    "end": today.isoformat(),
                },
            }],
            timeout=TIMEOUT,
        )
        assert sync_resp.status_code == 200
        
        # 5. Query DOPO sync — deve restituire ≥1 prezzo
        query_resp2 = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{
                "asset_id": asset_id,
                "date_range": {
                    "start": (today - timedelta(days=7)).isoformat(),
                    "end": today.isoformat(),
                },
            }],
            timeout=TIMEOUT,
        )
        assert query_resp2.status_code == 200
        prices_after = query_resp2.json()["items"][0]["prices"]
        assert len(prices_after) > 0, "Should have prices after sync"
        
        # Cleanup
        await client.delete(
            f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT
        )
```

**Dove inserirlo**: `test_assets_prices.py` come Test 6, oppure in `test_assets_provider.py`
come Test 16 (dato che testa il comportamento del provider assignment).

### Checklist Step 15

- [ ] `scripts/test_runner.py` riga 917: label aggiornato
- [ ] Nuovo test `test_query_without_sync_returns_empty` aggiunto
- [ ] Test passa: query pre-sync = 0 prezzi, query post-sync ≥ 1 prezzo

---

## Dependency Graph

```
Step 1 (fix .toFixed crash) ─── bloccante, la pagina non si carica senza
   │
   ├── Step 2 (BrokerIcon Svelte 5) ─── indipendente
   │
   ├── Step 3 (localStorage user-scoped) ─── indipendente, usa storage.ts già esistente
   │
   ├── Step 4 (FX delete 422) ─── indipendente
   │
   ├── Step 5 (FX manual-only UX) ─── indipendente, richiede Step 4 per poter testare delete
   │
   ├── Step 6 (ViewModeToggle header) ─── indipendente
   │
   ├── Step 7 (bulk prices + Δ multi-periodo) ─── richiede Step 1 (pagina funzionante)
   │   ├── 7a (backend: elimina GET, crea POST /query, elimina get_prices()) ─── prima
   │   ├── 7b (test migration GET → POST /query) ─── dopo 7a
   │   └── 7c (frontend bulk + colonne Δ) ─── dopo 7a (serve client Zodios aggiornato)
   │
   ├── Step 8 (fix test upload) ─── indipendente (backend)
   │
   ├── Step 9 (i18n cleanup) ─── indipendente
   │
   ├── Step 12 (fix JustETF search NaN) ─── indipendente (backend, bug pre-esistente)
   │
   ├── Step 13 (fix FAAssetCreateResult identifier) ─── indipendente (backend, bug pre-esistente)
   │
   ├── Step 14 (migrazione completa test Sync→Query) ─── dopo 7a (include Test 13/14/15 del file provider)
   │
   └── Step 15 (test runner label + test architettura Sync/Query) ─── dopo 14
       ├── 15a (label test_runner.py)
       └── 15b (test "query senza sync = vuoto")

Step 2-6, 8-9, 12-13 sono parallelizzabili.
Step 7a → 7b/7c → 14 → 15 è sequenziale.
Step 7 richiede Step 1.
```

---

## Riepilogo File

### Backend — Modifiche

| File | Step | Modifica |
|------|------|----------|
| `backend/app/schemas/prices.py` | 7a | `FAPriceQueryItem`, `FAPriceQueryResult`, `FAPriceQueryResponse(BaseListResponse)` |
| `backend/app/schemas/__init__.py` | 7a | Export nuovi schemi |
| `backend/app/services/asset_source.py` | 7a | `get_prices_bulk()` (nuovo) + **eliminare** `get_prices()` |
| `backend/app/api/v1/assets.py` | 7a | `POST /prices/query` (nuovo) + **eliminare** `GET /prices/{asset_id}` |
| `backend/test_scripts/test_api/test_assets_prices.py` | 7b | Migrare 4 GET → POST bulk + test multi-asset |
| `backend/test_scripts/test_e2e/test_search_to_prices.py` | 7b | Migrare 1 GET → POST bulk (Step 6) |
| `backend/test_scripts/test_api/test_uploads_api.py` | 8 | Login prima del test 404 |
| `backend/app/services/asset_source_providers/justetf.py` | 12 | `.fillna('')` prima di `.astype(str)` nella search |
| `backend/app/services/asset_source.py` | 13 | Rimuovere `identifier=None` da `FAAssetCreateResult` duplicato |
| `backend/test_scripts/test_api/test_assets_provider.py` | 14 | Migrare `GET /prices/{id}` → `POST /prices/query` in test_price_refresh |

### Frontend — Modifiche

| File | Step | Modifica |
|------|------|----------|
| `src/routes/(app)/assets/+page.svelte` | 1, 6, 7c | `Number()` wrap, ViewModeToggle nell'header, bulk fetch + `DELTA_PERIODS` + `visiblePeriods` + `computePeriodDelta()` |
| `src/lib/components/assets/AssetCard.svelte` | 1 | `Number()` guard nel template |
| `src/lib/components/assets/AssetTable.svelte` | 1, 7c | `Number()` guard, colonne Δ dinamiche multi-periodo |
| `src/lib/components/brokers/BrokerIcon.svelte` | 2 | Migrazione completa Svelte 5 runes |
| `src/lib/utils/storage.ts` | 3 | Rimuovere TODO migrazione |
| `src/routes/(app)/files/+page.svelte` | 3 | 3 chiavi localStorage → user-scoped |
| `src/routes/(app)/+layout.svelte` | 3 | `sidebar-collapsed` → user-scoped |
| `src/lib/components/layout/Sidebar.svelte` | 3 | `sidebar-collapsed` → user-scoped |
| `src/lib/components/table/DataTable.svelte` | 3 | `getStorageKey()` → `getUserStorageKey()` |
| `src/lib/components/fx/FxDataEditorSection.svelte` | 4 | `date_range` da array → oggetto singolo |
| `src/routes/(app)/fx/[pair]/+page.svelte` | 5 | `isManualOnly`, chart empty state, Sync btn disabled |
| `src/routes/(app)/fx/+page.svelte` | 6 | ViewModeToggle nell'header |

### i18n — Modifiche

| Operazione | Step | Dettaglio |
|------------|------|-----------|
| `./dev.py i18n add` | 5 | `fxDetail.noDataManual`, `fxDetail.insertManually`, `fxDetail.syncDisabledManual` |
| `./dev.py i18n remove` | 9 | `assets.placeholderMessage` |

---

## Note sulla Cache e Persistenza Dati

**Stato attuale**: i dati prezzi degli asset vivono come `$state` nella pagina
`assets/+page.svelte`. Quando l'utente naviga via (verso `/assets/[id]` o altra pagina),
SvelteKit distrugge il componente e i dati vengono persi. Al ritorno sulla lista, vengono
ri-fetchati. Non c'è persistenza cross-pagina.

**Fetch unificato**: si scarica **sempre il range completo** (tutti i giorni) con una
singola `POST /assets/prices/query`, sia per grid che per table. Il backend esegue
**una sola query SQL** (`WHERE asset_id IN (...) AND date BETWEEN ...`) per tutti gli
asset, poi applica backward-fill per ognuno in memoria. I dati sono nel DB (nessuna
chiamata ai provider), quindi il costo è trascurabile. Nessun refresh al cambio vista —
gli stessi dati servono entrambe le visualizzazioni.

**Colonne Δ**: calcolate interamente frontend-side dai dati `chartData` già in memoria.
Il cambio di range (DateRangePicker) ri-fetcha i dati e ri-calcola automaticamente i Δ
multi-periodo, mostrando/nascondendo le colonne pertinenti.

**Evoluzione futura (Phase 06 Step 4)**: quando si creerà la pagina detail asset, si
introdurrà un `assetPriceStoreRegistry` con `TimeSeriesStore<AssetPricePoint>` analogo a
`fxStoreRegistry`, con gap detection e delta-fetching.

---

## Analisi Allineamento FX ↔ Assets (macro-comportamento)

Confronto sistematico delle operazioni parallele tra i due sottosistemi.
Il comportamento FX è considerato **corretto e di riferimento**.

### Terminologia

| Operazione utente | Direzione dati | FX | Assets |
|---|---|---|---|
| **Sync** (scarica dai provider) | Provider → DB | `POST /fx/currencies/sync` | `POST /assets/prices/refresh` |
| **Refresh** (leggi dal DB) | DB → Frontend | `POST /fx/currencies/convert` | `POST /assets/prices/query` |
| **Upsert manuale** | Frontend → DB | `POST /fx/currencies/rate` | `POST /assets/prices` |
| **Delete** | DB ← Frontend | `DELETE /fx/currencies/rate` | `DELETE /assets/prices` |

> **Nota nome endpoint**: L'endpoint Asset di sync si chiama `/refresh` nell'URL, ma
> **semanticamente è un sync** (scarica dal provider nel DB). Questa è un'incongruenza
> di naming che potrebbe essere risolta in futuro rinominandolo in `/sync`.
> Per ora usiamo il termine "sync" nella documentazione e "refresh" nell'URL.

### Operazioni allineate ✅

| Operazione | FX | Assets | Note |
|---|---|---|---|
| **Upsert manuale** | `POST /fx/currencies/rate` → `upsert_rates_bulk()` | `POST /assets/prices` → `bulk_upsert_prices()` | Entrambi bulk. ✅ |
| **Delete** | `DELETE /fx/currencies/rate` → `delete_rates_bulk()` | `DELETE /assets/prices` → `bulk_delete_prices()` | Entrambi bulk. ✅ |
| **Sync da provider** | `POST /fx/currencies/sync` → `sync_pairs_bulk()` | `POST /assets/prices/refresh` → `bulk_refresh_prices()` | Entrambi: provider fetch → store in DB. ✅ |
| **Provider management** | `GET/POST/DELETE /fx/providers/routes` | `GET/POST/DELETE /assets/provider` | Entrambi CRUD provider. ✅ |
| **Query (refresh frontend)** | `POST /fx/currencies/convert` → `convert_bulk()` → **solo DB** | `POST /assets/prices/query` → `get_prices_bulk()` → **solo DB** | Entrambi: singola query SQL, backward-fill in memoria. ✅ |

### Anti-pattern rimosso in questo piano ⚠️ → ✅

| Operazione | FX (corretto) | Assets (PRIMA) | Assets (DOPO) |
|---|---|---|---|
| **Lettura prezzi** | `convert()` → **solo DB**, mai provider | `GET /prices/{id}` → **Sync + Query in un'unica chiamata** (provider HTTP + fallback DB) | **Eliminato.** Sync e Query sono operazioni separate |

#### Dettaglio dell'anti-pattern

**FX** separa nettamente le due operazioni:
- **Sync** = scarica dati dai provider e salvali nel DB — solo su richiesta esplicita dell'utente
- **Refresh/Query** = leggi dati dal DB e mandali al frontend — mai provider, zero side-effect

**Asset `GET /prices/{id}`** (il vecchio metodo `get_prices()`) faceva entrambe le cose:
1. Controllava se c'era un provider assegnato
2. Se sì → **chiamava il provider** (HTTP call esterna a yfinance/justetf/cssscraper!)
3. Salvava i risultati nel DB
4. Restituiva i dati al frontend

Ogni **lettura** generava potenziali chiamate HTTP esterne. Per una lista con 50 asset = 50 HTTP call
sequenziali ai provider. Questo era un side-effect nascosto in un'operazione di lettura.

#### Correzione (completata)

**Backend**:
- **Eliminato** `GET /assets/prices/{asset_id}` e il metodo `get_prices()` dal service layer
- Il flusso è ora separato in due operazioni indipendenti:
  - **Sync**: `POST /assets/prices/refresh` → `bulk_refresh_prices()` → provider HTTP → DB
  - **Query**: `POST /assets/prices/query` → `get_prices_bulk()` → solo DB → frontend

**Test**:
- Tutti i test che usavano `GET /prices/{id}` migrati a `POST /query` (Step 7b + Step 14)
- Nessun test contiene più il vecchio endpoint (confermato via grep)
- I test che leggono dopo sync hanno TUTTI il sync esplicito prima della query
- Step 15b aggiunge un test che **certifica** la separazione: query senza sync = 0 risultati

**Frontend (Phase 06 Step 4 — Asset Detail, futuro)**:
La pagina detail leggerà dal DB via `POST /assets/prices/query`.
Il bottone Sync (che chiama `POST /assets/prices/refresh`) segue lo stesso pattern di FX:
- Provider presente → bottone Sync attivo
- Nessun provider → bottone Sync **disabilitato**, messaggio "inserire manualmente"

#### Impatto sui test: flusso corretto

```
┌─────────────────┐     ┌──────────────┐     ┌────────────────┐
│  Provider API   │ ──→ │  DB (prices) │ ──→ │   Frontend     │
│ (yfinance, etc) │     │              │     │   (Svelte)     │
└─────────────────┘     └──────────────┘     └────────────────┘
        ↑                      ↑                     ↑
   POST /refresh          POST /query            Svelte fetch
   (sync: provider→DB)   (query: DB→FE)        (in +page.svelte)
```

I test devono seguire la stessa sequenza:
1. **Upsert manuale** OPPURE **Sync da provider** → dati nel DB
2. **Query** → leggi dal DB, verifica risultati
3. Mai aspettarsi dati nel DB senza un upsert o sync esplicito precedente

---

## Step 2d — UX Refinement Round 3 (24 Marzo 2026)

Sezione emersa dalla terza review. Copre bug di interazione, raffinamento colonne tabella,
visualizzazione provider chain, toolbar di selezione, icone asset e colonne dinamiche.

**Durata stimata**: ~1.5 giorni
**Dipendenze**: Step 2c (B1-B9) completati

### Prompt Originale Utente (Step 2d)

> b9, b9 e b3 ok
> nel testarli però mi sono reso conto che il pulsante di refresh in riga, mentre è in corso non gira in senso orario (se cliccato singolarmente)
> tra le colonne del columorder c'è anche una colonna swapped che se anche è mostrata non contiene nulla, ma in generale non ha senso mostrarla, essendo tutte le valute per loro natura bidirezionali.
> in oltre la lista degli elementi nell'orderibleList ora è lunga abbastanza da far comparire la barra verticale, ma quando provo a scrollarla il menù si chiude immediatamente.
>
> La colonna manual la eliminerei e metterei semplicemente l'icona della matita accanto alle bandiere nel nome (sempre dentro il badge ambra)
> La colonna Providers dovrebbe essere nascosta di default e se viene mostrata dovrebbe mostrare la catena sotto forma di icone dei provider, in maniera simile a come avviene in add Pair, che ha anche le valute ponte, in questo caso basta sapere l'ordine dei provider se non recuperi facilmente l'informazione. In realtà la stessa cosa la vorrei anche nella modale di sinc all, dove ora viene solo mostrato il testo alla stessa maniera. Parsa il contenuto della risposta e genera questa visualizzazione carina.
>
> Il toggleVisibleColums ha l'icona ma non la lable nella matrice 2x2, falla in tutte le lingue per uniformarla alle altre
>
> Le colonne delta extra non vanno inserite alla fine, ma una dopo l'altra, vicine, ed in ordine.
>
> B4 ok
>
> b5, si ma è sopra la tabella, deve essere nell'header a sinistra del togle griglia/tabella
> in oltre il sinc della toolbar apre il sincall e mostra tutte e 14 le coppie, credo che devi modificare la modale per prendere in input la lista delle coppie, non sempre tutte.
>
> ---
>
> ti ho detto sopra riguardo forex, similmente anche in asset:
> Manca nella matrice 2x2 il bottone settings, sia in tabella che in griglia, capisco che in tabella non serva molto, per ora, ma poi gli troveremo senso, intanto mettila, e anche in asset i settings devono fare le stesse cose, ovvero configurare l'estetica delle card.
> la colonna active non ha senso, metterei quel pallino verdo o rosso a destra del nome, mentre a sinistra, se configurato metterei l'icona dell'asset custom, altrimenti come fallback l'icona del tipo dell'asset.
> Nel tipo dell'asset, oltre al testo, vorrei anche l'immagine del tipo dell'asset
> per entrambe le richieste, le icone le trovi qui:  frontend/static/icons/asset-types

### Indice Step 2d

| # | Titolo | Area | Priorità | Stato |
|---|--------|------|----------|-------|
| C1 | ColumnVisibilityToggle: scroll interno chiude il dropdown | Frontend bug | 🔴 Bug | ✅ |
| C2 | ColumnVisibilityToggle: aggiungere label i18n nel bottone | Frontend i18n | 🟢 Facile | ✅ |
| C3 | Colonne Δ dinamiche: inserimento posizionale (non in coda) | Frontend bug | 🟡 Bug | ✅ |
| C4 | FxTable: eliminare colonne `swap` e `manualOnly`, mergiare badge manual nel nome | Frontend UX | 🟡 Refactor | ✅ |
| C5 | FxTable: colonna `providers` nascosta di default + catena icone provider | Frontend feature | 🟡 Feature | ✅ |
| C6 | FxSyncModal: visualizzazione catena provider con icone | Frontend feature | 🟡 Feature | ✅ |
| C7 | FxSyncModal: accettare lista filtrata di coppie per bulk sync | Frontend bug | 🟡 Bug | ✅ |
| C8 | DataTableToolbar: spostare nell'header (sinistra di ViewModeToggle) | Frontend UX | 🟡 Refactor | ✅ |
| C9 | Assets: aggiungere bottone Settings nella matrice 2×2 | Frontend UX | 🟢 Facile | ✅ |
| C10 | AssetTable: colonna nome con icona asset + indicatore active, rimuovere colonna `active` | Frontend UX | 🟡 Refactor | ✅ |
| C11 | AssetTable: colonna type con icona PNG del tipo asset | Frontend UX | 🟡 Feature | ✅ |
| C12 | Row-level refresh: animazione spin sul bottone singolo | Frontend bug | 🟡 Bug | ✅ |

**Ordine di implementazione**: C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8 → C9 → C10 → C11 → C12

---

### C1 — ColumnVisibilityToggle: scroll interno chiude il dropdown

**Area**: Frontend bug
**Priorità**: 🔴 Bug
**File coinvolti**:
- `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` (linee 80-86)

**Problema**: Il dropdown del ColumnVisibilityToggle si chiude immediatamente quando l'utente
prova a scrollare la lista degli elementi (OrderableList). La causa è il listener `scroll` in
capture phase (`window.addEventListener('scroll', handleScroll, true)`) che cattura **tutti** gli
eventi scroll, inclusi quelli interni al dropdown stesso.

**Causa root**: L'evento `scroll` con `capture: true` cattura anche lo scroll del contenitore
`overflow-y-auto` del dropdown. Il listener chiama `close()` senza verificare se la sorgente
dello scroll è interna o esterna al dropdown.

**Soluzione**:
1. Aggiungere un `ref` al contenitore del dropdown (`dropdownRef`)
2. Nel `handleScroll`, verificare se `e.target` è contenuto nel dropdown:
   ```typescript
   const handleScroll = (e: Event) => {
       if (dropdownRef && dropdownRef.contains(e.target as Node)) return;
       close();
   };
   ```
3. Se lo scroll è interno al dropdown → ignorare. Se esterno → chiudere.

**Stima**: 10 min

---

### C2 — ColumnVisibilityToggle: aggiungere label i18n nel bottone

**Area**: Frontend i18n
**Priorità**: 🟢 Facile
**File coinvolti**:
- `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` (linea 106-114)
- `frontend/src/lib/i18n/en.json`
- `frontend/src/lib/i18n/it.json`
- `frontend/src/lib/i18n/fr.json`
- `frontend/src/lib/i18n/es.json`

**Problema**: Il bottone ColumnVisibilityToggle nella matrice 2×2 mostra solo l'icona `Eye`,
senza label testuale, a differenza degli altri bottoni della matrice che hanno etichette
(es. "Settings", "Sync", "Refresh").

**Soluzione**:
1. Aggiungere la chiave i18n `table.columns` in tutte e 4 le lingue:
   - EN: `"Columns"`
   - IT: `"Colonne"`
   - FR: `"Colonnes"`
   - ES: `"Columnas"`
2. Aggiungere una prop `showLabel` (default `false`) al componente
3. Nei punti d'uso (FX e Assets 2×2 block), passare `showLabel={showActionLabels}` o `showLabel={true}`
4. Modificare il template del bottone per mostrare `<span>{$t('table.columns')}</span>` quando
   `showLabel` è true

**Stima**: 15 min

---

### C3 — Colonne Δ dinamiche: inserimento posizionale (non in coda)

**Area**: Frontend bug
**Priorità**: 🟡 Bug
**File coinvolti**:
- `frontend/src/lib/components/table/DataTable.svelte` (linee 669-720, `$effect` sync colonne)

**Problema**: Quando il date range cambia e nuove colonne Δ periodo diventano visibili (es. da
3M a 6M, compaiono `Δ 3M` e `Δ 6M`), queste vengono aggiunte **alla fine** di `columnOrder`
invece che nella posizione corretta (adiacenti alle colonne Δ esistenti).

**Causa root**: Il codice attuale fa `columnOrder = [...filtered, ...newIds]`, che appende
sempre in coda. Non c'è logica per determinare la posizione semantica corretta.

**Soluzione**:
Modificare la logica di inserimento nel `$effect` di sync colonne per usare l'ordine del
`columns` array come guida per la posizione:

```typescript
// Per ogni nuova colonna, trovare la posizione nell'array columns originale
// e inserirla dopo l'ultima colonna già presente che la precede nel columns array
for (const newId of newIds) {
    const colIndex = columns.findIndex(c => c.id === newId);
    // Trova l'ultima colonna nel filtered che precede newId nell'ordine di columns
    let insertAfterIdx = -1;
    for (let i = 0; i < filtered.length; i++) {
        const existingColIdx = columns.findIndex(c => c.id === filtered[i]);
        if (existingColIdx < colIndex) insertAfterIdx = i;
    }
    filtered.splice(insertAfterIdx + 1, 0, newId);
}
columnOrder = filtered;
```

Questo assicura che `delta_1W`, `delta_1M`, `delta_3M` appaiano sempre consecutivi e nell'ordine
definito dall'array `columns`, che a sua volta rispecchia l'ordine dei `DELTA_PERIODS`.

**Stima**: 30 min

---

### C4 — FxTable: eliminare colonne `swap` e `manualOnly`, mergiare badge manual nel nome

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/lib/components/fx/FxTable.svelte` (linee 119-224, definizione colonne)

**Problema**:
1. La colonna `swap` è mostrata nel ColumnVisibilityToggle ma non ha contenuto utile — lo swap
   è già gestito tramite rowAction con icona ⇄
2. La colonna `manualOnly` occupa spazio come colonna separata. L'utente preferisce un badge
   ✏️ compatto nel nome della coppia (dentro il badge ambra esistente, accanto alle bandiere)

**Soluzione**:
1. **Rimuovere** la colonna `swap` dall'array `columns` (l'azione swap resta come rowAction)
2. **Rimuovere** la colonna `manualOnly` dall'array `columns`
3. **Modificare** la cella `pair` per aggiungere il badge manual inline:
   ```typescript
   cell: (row) => {
       const db = getDisplayBase(row);
       const dq = getDisplayQuote(row);
       const bFlag = getCurrencyInfo(db).flag_emoji;
       const qFlag = getCurrencyInfo(dq).flag_emoji;
       const manualBadge = row.manualOnly
           ? ' <span class="inline-flex items-center px-1 py-0.5 text-[9px] font-medium rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 ml-1">✏️</span>'
           : '';
       return {type: 'html', html: `<span class="emoji-flag">${bFlag}</span> <span class="font-semibold">${db}</span> <span class="text-gray-400">→</span> <span class="emoji-flag">${qFlag}</span> <span class="font-semibold">${dq}</span>${manualBadge}`};
   },
   ```

**Impatto localStorage**: L'utente potrebbe avere `swap` e `manualOnly` nel `columnOrder`
salvato in localStorage. La logica di sync colonne dinamiche (C3/B7) elimina automaticamente
gli ID orfani, quindi non serve pulizia manuale.

**Stima**: 20 min

---

### C5 — FxTable: colonna `providers` nascosta di default + catena icone provider

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/lib/components/fx/FxTable.svelte` (linea 197-208, colonna providers)
- (Opzionale) Creare `frontend/src/lib/components/fx/ProviderChainIcons.svelte`

**Problema**: La colonna `providers` è visibile di default e mostra solo testo piatto
(es. `"CHAIN:ECB+FIXED_RATE"`). L'utente vuole:
1. Nascosta di default (`hiddenByDefault: true`)
2. Quando visibile, mostrare la catena come icone/badge (simile a FxPairAddModal)

**Dati disponibili**: L'oggetto `FxRow` ha `providers: Array<{providerCode: string; priority: number}>`.
Il `providerCode` è tipo `"CHAIN:ECB+FIXED_RATE"` o singolo `"ECB"`. Dalla pagina FX,
i `chainSteps` sono disponibili nell'oggetto `FxPairConfig` (caricati da `list_routes`).

**Soluzione**:
1. Aggiungere `hiddenByDefault: true` alla colonna `providers`
2. Aggiungere il campo `chainSteps` nel tipo `FxRow` (passato da `fx/+page.svelte`)
3. Modificare la cella per mostrare icone/badge per ogni step della catena:
   ```html
   <!-- Catena: ECB → EUR/USD → FIXED_RATE → USD/CHF -->
   <div class="flex items-center gap-0.5">
     <span class="px-1 py-0.5 text-[9px] rounded bg-blue-100 text-blue-700">ECB</span>
     <span class="text-gray-400 text-[8px]">→</span>
     <span class="text-[9px] text-gray-400">EUR/USD</span>
     <span class="text-gray-400 text-[8px]">→</span>
     <span class="px-1 py-0.5 text-[9px] rounded bg-green-100 text-green-700">FIXED_RATE</span>
   </div>
   ```
4. Per provider diretti (non chain), mostrare semplicemente il badge singolo

**Mappa colori provider** (consistente con FxPairAddModal):
| Provider | Badge color |
|----------|-------------|
| ECB | blue |
| FRANKFURTER | indigo |
| FIXED_RATE | emerald |
| MANUAL | amber |
| Fallback | gray |

**Stima**: 45 min

---

### C6 — FxSyncModal: visualizzazione catena provider con icone

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/lib/components/fx/FxSyncModal.svelte` (linee 276-318, per-pair results)

**Problema**: Nella modale di sync, il campo `provider_used` è mostrato come testo piatto
in parentesi (es. `(CHAIN:ECB+FIXED_RATE)`). L'utente vuole la stessa visualizzazione a catena
icone definita in C5.

**Soluzione**:
1. Estrarre la logica di rendering della catena provider in un helper condiviso
   (snippet Svelte o funzione che genera HTML)
2. Sostituire `<span class="text-gray-400">({pr.provider_used})</span>` con la visualizzazione
   a badge/icone
3. Parsare `provider_used`: se inizia con `"CHAIN:"`, splitta per `+`; altrimenti singolo badge
4. Riutilizzare la stessa mappa colori di C5

**Stima**: 30 min

---

### C7 — FxSyncModal: accettare lista filtrata di coppie per bulk sync

**Area**: Frontend bug
**Priorità**: 🟡 Bug
**File coinvolti**:
- `frontend/src/routes/(app)/fx/+page.svelte` (linee 475-479, `handleBulkSyncFx`)
- `frontend/src/routes/(app)/fx/+page.svelte` (linee 819-828, `<FxSyncModal>`)

**Problema**: Quando l'utente fa una selezione multipla in tabella e clicca "Sync" dalla toolbar,
la modale si apre ma mostra **tutte** le coppie (quelle passate dalla prop `pairs` che è fissa).
Dovrebbe mostrare solo le coppie selezionate.

**Causa root**: `handleBulkSyncFx()` semplicemente fa `syncModalOpen = true` senza passare
le coppie selezionate. La prop `pairs` della modale è calcolata staticamente da `pairs.filter(...)`.

**Soluzione**:
1. Aggiungere uno state `syncModalPairs = $state<string[]>([])` in `fx/+page.svelte`
2. In `handleBulkSyncFx()`:
   ```typescript
   function handleBulkSyncFx() {
       syncModalPairs = selectedFxRows
           .filter(r => !r.manualOnly)
           .map(r => `${r.base}-${r.quote}`);
       syncModalOpen = true;
   }
   ```
3. In `handleSyncAll()`:
   ```typescript
   function handleSyncAll() {
       syncModalPairs = pairs
           .filter(p => !(p.config.providers.length === 1 && p.config.providers[0].providerCode === 'MANUAL'))
           .map(p => `${p.config.base}-${p.config.quote}`);
       syncModalOpen = true;
   }
   ```
4. Passare `syncModalPairs` alla prop `pairs` di `<FxSyncModal>`:
   ```svelte
   <FxSyncModal
       bind:open={syncModalOpen}
       {dateStart}
       {dateEnd}
       pairs={syncModalPairs}
       onsynced={handleSynced}
       onclose={() => syncModalOpen = false}
   />
   ```

**Stima**: 15 min

---

### C8 — DataTableToolbar: spostare nell'header (sinistra di ViewModeToggle)

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/routes/(app)/fx/+page.svelte` (linee 560-583, header + linee 773-784, toolbar)
- `frontend/src/routes/(app)/assets/+page.svelte` (linee 365-388, header + linee 561-571, toolbar)

**Problema**: Il `DataTableToolbar` (contatore selezione + azioni bulk) è posizionato
**sopra la tabella**, ma l'utente lo vuole **nell'header**, a sinistra del `ViewModeToggle`.
Questo allinea visivamente la toolbar alla barra degli strumenti esistente.

**Soluzione**:
1. **FX page**: spostare il blocco `{#if selectedFxRows.length > 0} <DataTableToolbar .../> {/if}`
   dall'area sopra `<FxTable>` nell'header, dentro il `<div class="flex items-center gap-2">`
   che contiene `ViewModeToggle` e "Add Pair"
2. **Assets page**: stessa operazione — spostare il blocco toolbar nell'header

L'ordine nell'header sarà:
```
[Titolo + subtitolo]                    [DataTableToolbar?] [ViewModeToggle] [Add Pair/Asset]
```

Il `DataTableToolbar` appare solo quando c'è una selezione attiva e la vista è `list` (tabella).

**Stima**: 20 min

---

### C9 — Assets: aggiungere bottone Settings nella matrice 2×2

**Area**: Frontend UX
**Priorità**: 🟢 Facile
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte` (linee 463-489, matrice 2×2)

**Problema**: La matrice 2×2 azioni nella pagina Assets ha: ColumnVisibility (o vuoto),
Sync, e Refresh. Manca il bottone **Settings** presente nella matrice FX.
L'utente vuole uniformità: anche in Assets il bottone Settings deve aprire il modale per
configurare l'estetica delle card (stesso `ChartSettingsModal` usato in FX).

**Soluzione**:
1. Importare `Settings` da `lucide-svelte` (già importato in FX)
2. Importare `ChartSettingsModal` in `assets/+page.svelte`
3. Aggiungere state `settingsModalOpen`, `settingsForModal` etc.
4. Aggiungere il bottone Settings nella matrice 2×2 (posizione: top-right, come in FX)
5. Aggiungere `<ChartSettingsModal>` nel template

**Nota**: Per ora il settings potrebbe non avere tutte le opzioni significative per gli asset
(es. signal overlay non è ancora implementato per asset), ma la modale si apre e funziona.
Sarà esteso in Phase 06 Step 3/4.

**Matrice 2×2 risultante**:
```
| ColumnVisibility (list) / vuoto (grid) | Settings |
| Sync                                    | Refresh  |
```

**Stima**: 25 min

---

### C10 — AssetTable: colonna nome con icona asset + indicatore active

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/lib/components/assets/AssetTable.svelte` (linee 90-99, colonna `name`;
  linee 164-178, colonna `active`)

**Problema**:
1. La colonna `active` mostra un pallino verde/rosso come colonna separata. L'utente vuole
   il pallino **a destra del nome** nella colonna nome
2. La colonna nome non mostra l'icona dell'asset. L'utente vuole:
   - **A sinistra** del nome: icona custom dell'asset (`icon_url`), oppure fallback all'icona
     PNG del tipo asset (da `frontend/static/icons/asset-types/{type}.png`)
   - **A destra** del nome: pallino verde (active) o rosso (inactive)

**Soluzione**:
1. **Rimuovere** la colonna `active` dall'array `columns`
2. **Modificare** la cella `name` per includere icona + pallino:
   ```typescript
   cell: (row) => {
       // Icon: custom icon_url, fallback to asset-type PNG
       const typeMap: Record<string, string> = {
           STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
           FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
       };
       const iconSrc = row.icon_url
           || (row.asset_type ? `/icons/asset-types/${typeMap[row.asset_type] ?? 'other'}.png` : null);
       const iconHtml = iconSrc
           ? `<img src="${iconSrc}" alt="" class="w-5 h-5 rounded-full object-cover shrink-0" onerror="this.style.display='none'" />`
           : `<div class="w-5 h-5 rounded-full bg-libre-green/10 flex items-center justify-center shrink-0"><svg ...></svg></div>`;
       const activeDot = row.active
           ? '<span class="w-2 h-2 rounded-full bg-emerald-500 shrink-0"></span>'
           : '<span class="w-2 h-2 rounded-full bg-red-400 shrink-0"></span>';
       return {
           type: 'html',
           html: `<div class="flex items-center gap-2">${iconHtml}<span class="font-medium text-gray-800 dark:text-gray-100">${row.display_name}</span>${activeDot}</div>`,
       };
   },
   ```

**Mappa tipo → file PNG**:
| `asset_type` | File PNG |
|--------------|----------|
| STOCK | `stock.png` |
| ETF | `etf.png` |
| BOND | `bond.png` |
| CRYPTO | `crypto.png` |
| FUND | `fund.png` |
| HOLD | `hold.png` |
| CROWDFUND_LOAN | `crowdfunding.png` |
| OTHER | `other.png` |

**Stima**: 30 min

---

### C11 — AssetTable: colonna type con icona PNG del tipo asset

**Area**: Frontend UX
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/lib/components/assets/AssetTable.svelte` (linee 100-109, colonna `type`)

**Problema**: La colonna `type` mostra solo un badge testuale (es. `ETF`, `STOCK`). L'utente
vuole che, oltre al testo, venga mostrata anche l'icona PNG del tipo asset.

**Soluzione**:
Modificare `typeBadgeHtml()` per includere l'immagine:
```typescript
function typeBadgeHtml(type: string | null | undefined): string {
    if (!type) return '<span class="text-gray-400">—</span>';
    const typeMap: Record<string, string> = {
        STOCK: 'stock', ETF: 'etf', BOND: 'bond', CRYPTO: 'crypto',
        FUND: 'fund', HOLD: 'hold', CROWDFUND_LOAN: 'crowdfunding', OTHER: 'other',
    };
    const imgSrc = `/icons/asset-types/${typeMap[type] ?? 'other'}.png`;
    const colors: Record<string, string> = { /* ... colori esistenti ... */ };
    const cls = colors[type] ?? '...';
    return `<span class="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded ${cls}">
        <img src="${imgSrc}" alt="" class="w-3.5 h-3.5 object-contain" onerror="this.style.display='none'" />
        ${type}
    </span>`;
}
```

**Stima**: 15 min

---

### C12 — Row-level refresh: animazione spin sul bottone singolo

**Area**: Frontend bug
**Priorità**: 🟡 Bug
**File coinvolti**:
- `frontend/src/lib/components/table/DataTable.svelte` (linee 1060-1073, action buttons)
- `frontend/src/lib/components/fx/FxTable.svelte` (rowActions `refresh`)
- `frontend/src/lib/components/assets/AssetTable.svelte` (rowActions `refresh`)
- `frontend/src/lib/components/table/types.ts` — aggiungere campo `iconClass` al tipo `RowAction`

**Problema**: Quando l'utente clicca il bottone refresh su una singola riga, l'icona non gira
(nessuna animazione `animate-spin`). L'utente si aspetta un feedback visivo durante il caricamento.

**Causa root**: Il DataTable non ha un meccanismo per tracciare lo stato di loading per azione
singola. L'azione `onClick` è fire-and-forget.

**Soluzione** (approccio pragmatico: stato loading per riga nel componente wrapper):
1. Aggiungere un campo `loadingRowIds` state in `FxTable.svelte` e `AssetTable.svelte`
2. Il rowAction `refresh` diventa:
   ```typescript
   {
       id: 'refresh',
       label: () => $t('common.refresh'),
       icon: RefreshCw,
       onClick: async (row) => {
           loadingRowIds.add(row.slug);
           loadingRowIds = new Set(loadingRowIds); // trigger reactivity
           await onrefresh?.({...});
           loadingRowIds.delete(row.slug);
           loadingRowIds = new Set(loadingRowIds);
       },
       // Classe CSS condizionale per animazione
       iconClass: (row) => loadingRowIds.has(row.slug) ? 'animate-spin' : '',
   }
   ```
3. **DataTable**: Estendere il tipo `RowAction` per supportare `iconClass?: (row: T) => string`
4. Nel template DataTable, applicare la classe dinamica:
   ```svelte
   <action.icon size={16} class={action.iconClass?.(row) ?? ''} />
   ```

**Alternativa** (più semplice, tramite stato sulla riga):
- Aggiungere un campo `_refreshing?: boolean` alla `FxRow` / `AssetRow`
- Settarlo in `handleRefreshPair` prima e dopo l'operazione
- Usare `iconClass: (row) => row._refreshing ? 'animate-spin' : ''`

L'approccio con `loadingRowIds` è più pulito perché non inquina il modello dati.

**Stima**: 40 min

---

### Riepilogo Dipendenze Step 2d

```
C1 (scroll fix) ─────────────── indipendente, fare per primo (bug UX base)
C2 (label i18n) ─────────────── indipendente, facile
C3 (column position) ────────── indipendente, modifica DataTable.$effect
    │
C4 (swap/manual merge) ──────── dopo C3 (rimozione colonne swap/manualOnly usa il sync dinamico)
    │
C5 (providers chain FxTable) ── dopo C4 (stessa area codice FxTable columns)
    │
C6 (providers chain SyncModal)─ dopo C5 (condivide helper rendering catena)
    │
C7 (sync modal filtered) ────── dopo C6 (modifica la stessa modale)
    │
C8 (toolbar header) ─────────── indipendente, refactor posizionamento
C9 (settings Assets) ────────── indipendente
C10 (nome + icon + active) ──── indipendente (modifica AssetTable)
C11 (type icon) ──────────────── dopo C10 (stessa area AssetTable columns)
C12 (refresh spin) ──────────── indipendente (modifica DataTable types + template)
```

### Checklist Pre-Implementazione Step 2d

- [x] C1: Fix scroll ColumnVisibilityToggle — `dropdownRef.contains(e.target)`
- [x] C2: Label i18n ColumnVisibilityToggle — 4 lingue + prop `showLabel`
- [x] C3: Inserimento posizionale colonne Δ — logica `columns.findIndex` per posizione
- [x] C4: FxTable rimozione `swap`/`manualOnly` + badge manual nel nome
- [x] C5: FxTable colonna providers con catena icone + `hiddenByDefault`
- [x] C6: FxSyncModal catena provider visualizzazione
- [x] C7: FxSyncModal lista filtrata coppie + state `syncModalPairs`
- [x] C8: DataTableToolbar nell'header (FX + Assets)
- [x] C9: Assets matrice 2×2 + Settings + ChartSettingsModal
- [x] C10: AssetTable nome con icona + active dot, rimozione colonna `active`
- [x] C11: AssetTable type badge con icona PNG
- [x] C12: Row-level refresh spin — `loadingRowIds` + `iconClass` in RowAction type

---

## Step 2e — Post-Review Fixes Step 2d + UX Filtro Assets (24 Marzo 2026)

Correzioni emerse dalla review dello Step 2d, più nuove richieste UX per filtri pagina Assets,
i18n tipi asset, icone tipo nelle card, e layout responsive della filter bar.

**Durata stimata**: ~1.5 giorni
**Dipendenze**: Step 2d (C1-C12) completati

### Prompt Originale Utente (Step 2e — Review C + nuove richieste)

> C1 e C2 corrette, ma il bottone è allineato a sinistra, mentre dovrebbe essere centrato
>
> C5 e C6: invece del badge mi aspettavo una visualizzazione come in FxProviderSelect
> (con bandiere valute intermedie, icone provider favicon, frecce ⇆)
>
> C7: ho selezionato 3 e ho provato a fare la sinc ma il pacchetto dal frontend contiene
> `"pairs":["undefined-undefined","undefined-undefined","undefined-undefined"]`
>
> C9: ora dovresti metterci la stessa modale di configurazione dei grafici con stessa logica
>
> C11: se riesci stessa icona anche nel filtro della tabella
>
> ---
>
> L'icona del tipo di asset non deve essere solo nella tabella, ma anche nella card.
> Stavo pensando che è brutto avere i tipi solo in inglese, potremmo aggiungere delle chiavi
> di traduzioni uguali ai nomi del backend e tradurli nelle varie lingue con i18n?
> Idem per le icone vicino al nome nelle card, come per le tabelle.
>
> Riguardo i filtri nella parte alta, vicino ai tempi, mi torna, così è applicabile sia in
> tabella che in card. Quindi bisognerebbe rimuovere dalla colonne tipo e valuta il filtro,
> lasciare solo il riordinamento.
>
> Il filtro sui tipi globali dovrebbe essere delle checkbox come per la tabella, volendo potresti
> riusare proprio quel pannello per il filtro. Lato valuta hai fatto benissimo a mettere il
> CurrencySearchSelect, solo che non sono convinto che debba essere solo uno, mi dai delle
> proposte per fare una selezione multi-valuta in cui le varie valute si sommano in OR?
>
> Il pulsante degli attivi mi torna al 100%, non essendoci più la colonna.
>
> In ogni caso quei 4 selettori così in riga non vanno bene, mi proponi 3 arrangiamenti in ASCII art.

### Indice Step 2e

| # | Titolo | Area | Priorità | Stato |
|---|--------|------|----------|-------|
| D1 | ColumnVisibilityToggle: centrare bottone nel layout 2×2 | Frontend UX | 🟢 Facile | ⬜ |
| D2 | Provider chain: visualizzazione ricca con bandiere + icone favicon (FxTable + FxSyncModal) | Frontend feature | 🟡 Feature | ⬜ |
| D3 | Bulk sync: fix `undefined-undefined` — `onSelectionChange` restituisce `string[]` non `FxRow[]` | Frontend bug | 🔴 Bug | ⬜ |
| D4 | Assets: integrazione completa ChartSettingsModal (global + per-card) | Frontend feature | 🟡 Feature | ⬜ |
| D5 | AssetTable + filtro enum: icone PNG tipo asset | Frontend UX | 🟢 Nice-to-have | ⬜ |
| D6 | i18n tipi asset (STOCK → Azione, ETF → ETF, etc.) + icona tipo in AssetCard | Frontend i18n | 🟡 Feature | ⬜ |
| D7 | AssetCard: icona asset nel nome (come in tabella) + indicatore active | Frontend UX | 🟡 Refactor | ⬜ |
| D8 | Rimuovere filtro colonna type e currency dalla tabella (solo sorting) | Frontend UX | 🟡 Refactor | ⬜ |
| D9 | Filtro tipo globale: checkbox multi-select con pannello (come DataTableColumnFilter enum) | Frontend feature | 🟡 Feature | ⬜ |
| D10 | Filtro valuta: multi-select con badge rimuovibili (OR logic) | Frontend feature | 🟡 Feature | ⬜ |
| D11 | Filter bar Assets: redesign layout responsive (3 proposte ASCII art) | Frontend UX | 🟡 Refactor | ⬜ |
| D12 | Provider chain: fallback iniziali per icone non disponibili | Frontend UX | 🟢 Facile | ⬜ |

**Ordine di implementazione**: D1 → D3 → D6 → D7 → D2 → D12 → D8 → D9 → D10 → D11 → D4 → D5

---

### D1 — ColumnVisibilityToggle: centrare bottone nel layout 2×2

**Area**: Frontend UX
**Priorità**: 🟢 Facile
**File coinvolti**:
- `frontend/src/lib/components/table/ColumnVisibilityToggle.svelte` (linea 116)

**Problema**: Il bottone ColumnVisibilityToggle nella matrice 2×2 è allineato a sinistra
anziché centrato come gli altri bottoni della griglia.

**Causa root**: Il bottone non ha `justify-center` nella classe CSS. Gli altri bottoni
della griglia 2×2 hanno `flex items-center justify-center`.

**Soluzione**: Aggiungere `justify-center` alla classe del bottone trigger:
```svelte
class="flex items-center justify-center gap-1 px-2.5 py-1.5 ..."
```

**Stima**: 5 min

---

### D2 — Provider chain: visualizzazione ricca con bandiere + icone favicon

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/lib/components/fx/FxTable.svelte` (funzione `providerChainHtml`)
- `frontend/src/lib/components/fx/FxSyncModal.svelte` (rendering provider chain)
- `frontend/src/lib/utils/colors.ts` (riuso `getProviderColor`)
- `frontend/src/lib/stores/currencyGraphStore.ts` (`getCachedProviders`)

**Problema**: La visualizzazione dei provider nella colonna tabella e nella modale sync
mostra solo badge testuali (es. `ECB`). L'utente vuole la stessa visualizzazione ricca
usata in `FxProviderSelect.svelte`: bandiere valuta, icone provider (favicon), frecce ⇆.

**Dati disponibili**:
- `FxRow.providers[0].chainSteps[]` → `{from, to, provider}` per ogni step
- `getCurrencyInfo(code)` → `{flag_emoji}` per le bandiere
- `getCachedProviders()` → `[{code, icon_url, name}]` per icone provider
- `getProviderColor(code)` → `{bg, border}` per colori badge

**Pattern di rendering** (da FxProviderSelect, adattato per inline HTML):
```
🇦🇺 AUD [⇆ 🌐ECB ⇆] 🇪🇺 EUR [⇆ 🌐ECB ⇆] 🇬🇧 GBP
```

**Soluzione — FxTable (HTML inline nella cella)**:
1. Importare `getCachedProviders` da `$lib/stores/currencyGraphStore`
2. Importare `getProviderColor` da `$lib/utils/colors`
3. Costruire un `providerMap` derivato per lookup `icon_url` e iniziali
4. Riscrivere `providerChainHtml()`:
   - Per ogni step: `flag_from CODE_from [⇆ icon/initials ⇆] flag_to CODE_to`
   - Badge con sfondo colorato via `getProviderColor`
   - Icona = `<img>` se `icon_url` disponibile, altrimenti iniziali 2-char
5. Per chain (>1 step): mostrare step intermedi concatenati

**Soluzione — FxSyncModal (Svelte nativo)**:
1. Parsare `provider_used` (es. `"CHAIN:ECB+FIXED_RATE"`) → lista codici
2. Per ogni codice, renderizzare badge Svelte con icona/iniziali + colore
3. Non serve la catena completa con bandiere (la modale mostra solo i provider usati)

**Stima**: 45 min

---

### D3 — Bulk sync: fix `undefined-undefined`

**Area**: Frontend bug
**Priorità**: 🔴 Bug
**File coinvolti**:
- `frontend/src/lib/components/fx/FxTable.svelte` (linea 247, `onSelectionChange`)
- `frontend/src/lib/components/assets/AssetTable.svelte` (stessa issue)

**Problema**: `DataTable.onSelectionChange` passa `selectedIds: string[]` (gli ID delle righe),
ma FxTable lo passa direttamente a `onselectionchange` che si aspetta `(rows: FxRow[])`.
Il callback riceve stringhe, non oggetti, quindi `row.base` e `row.quote` sono `undefined`.

**Soluzione**: In FxTable e AssetTable, mappare gli ID alle righe complete:
```typescript
// FxTable
onSelectionChange={(ids: string[]) => {
    onselectionchange?.(data.filter(row => ids.includes(row.slug)));
}}

// AssetTable
onSelectionChange={(ids: string[]) => {
    onselectionchange?.(data.filter(row => ids.includes(String(row.id))));
}}
```

**Stima**: 10 min

---

### D4 — Assets: integrazione completa ChartSettingsModal (global + per-card)

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte`
- `frontend/src/lib/components/assets/AssetCard.svelte`

**Problema**: Il bottone Settings nella matrice 2×2 è un placeholder. L'utente vuole:
- Settings globale dalla matrice → configura tutti i grafici
- Settings per-card dal bottone ⚙️ → configura solo quell'asset
- Preview nella modale mostra solo i dati di quell'asset

**Soluzione**:
1. Importare `ChartSettingsModal`, `getGlobalSettings`, `setGlobalSettings`,
   `getSettingsForPair`, `setPairSettings`, `getSettingsVersion`
2. State: `settingsModalOpen`, `settingsTargetId: string | null`
3. Derivata `settingsForModal` (globale o per-asset)
4. `handleGlobalSettings()` e `handleCardSettings({id})`
5. `handleSettingsSave(s)` → `setPairSettings` o `setGlobalSettings`
6. `<ChartSettingsModal>` nel template con props corrette
7. In `AssetCard`: aggiungere bottone ⚙️ nel footer + prop `onsettings`

**Nota**: Per assets, la chiave nel `chartSettingsStore` è `asset-{id}` (stringa).

**Stima**: 40 min

---

### D5 — AssetTable + filtro enum: icone PNG tipo asset

**Area**: Frontend UX
**Priorità**: 🟢 Nice-to-have
**File coinvolti**:
- `frontend/src/lib/components/table/types.ts` (tipo `EnumOption`)
- `frontend/src/lib/components/table/DataTableColumnFilter.svelte` (rendering enum)
- `frontend/src/lib/components/assets/AssetTable.svelte` (opzioni enum)

**Problema**: Il filtro dropdown della colonna `type` mostra solo testo. L'utente vorrebbe
le stesse icone PNG del badge nella cella.

**Soluzione**:
1. Estendere `EnumOption` con `iconUrl?: string`
2. In `DataTableColumnFilter.svelte`, renderizzare `<img>` accanto a `.enum-label` se presente
3. In `AssetTable`, popolare `iconUrl` per ogni tipo asset:
   ```typescript
   enumOptions: ASSET_TYPES.map(v => ({
       value: v,
       label: $t(`assets.types.${v}`),
       iconUrl: `/icons/asset-types/${ASSET_TYPE_ICON_MAP[v] ?? 'other'}.png`,
   }))
   ```

**Stima**: 20 min

---

### D6 — i18n tipi asset + icona tipo in badge AssetCard

**Area**: Frontend i18n + UX
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/lib/i18n/en.json`, `it.json`, `fr.json`, `es.json`
- `frontend/src/lib/components/assets/AssetTable.svelte` (badge tipo)
- `frontend/src/lib/components/assets/AssetCard.svelte` (badge tipo)
- `frontend/src/routes/(app)/assets/+page.svelte` (typeOptions)

**Problema**: I tipi asset sono mostrati in inglese raw dal backend (`STOCK`, `ETF`, etc.).
L'utente vuole traduzioni i18n. Inoltre il badge tipo nella card non ha l'icona PNG.

**Chiavi i18n da aggiungere**:

| Chiave | EN | IT | FR | ES |
|--------|----|----|----|----|
| `assets.types.STOCK` | Stock | Azione | Action | Acción |
| `assets.types.ETF` | ETF | ETF | ETF | ETF |
| `assets.types.BOND` | Bond | Obbligazione | Obligation | Bono |
| `assets.types.CRYPTO` | Crypto | Cripto | Crypto | Cripto |
| `assets.types.FUND` | Fund | Fondo | Fonds | Fondo |
| `assets.types.HOLD` | Hold | Liquidità | Liquidité | Liquidez |
| `assets.types.CROWDFUND_LOAN` | Crowdfund | Crowdfunding | Crowdfunding | Crowdfunding |
| `assets.types.OTHER` | Other | Altro | Autre | Otro |

**Soluzione**:
1. Aggiungere le chiavi i18n `assets.types.*` in tutte le 4 lingue
2. In `AssetTable.typeBadgeHtml()`: sostituire il testo raw con traduzione via `get(_)`
3. In `AssetCard`: aggiungere icona PNG nel badge tipo (stessa logica della tabella)
4. In `assets/+page.svelte typeOptions`: usare `$t('assets.types.STOCK')` come label
5. In `AssetTable enumOptions`: usare label tradotta anziché raw

**Stima**: 30 min

---

### D7 — AssetCard: icona asset nel nome + indicatore active (come tabella)

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/lib/components/assets/AssetCard.svelte` (linee 104-123)

**Problema**: L'AssetCard usa `AssetIcon` (Lucide fallback), ma la tabella ora mostra
l'icona PNG del tipo asset come fallback. Il comportamento deve essere uniforme.
Inoltre, la card usa un badge "Inactive" separato — nella tabella si usa un pallino
verde/rosso a destra del nome.

**Soluzione**:
1. Nel header card, assicurare che `AssetIcon` segua la stessa catena di fallback:
   `icon_url` → type PNG → fallback SVG
2. Aggiungere pallino active verde/rosso a destra del nome (come nella tabella)
3. Rimuovere il badge "Inactive" separato (ridondante col pallino)

**Stima**: 20 min

---

### D8 — Rimuovere filtro colonna type e currency dalla tabella (solo sorting)

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/lib/components/assets/AssetTable.svelte` (colonne `type` e `currency`)

**Problema**: Ora che i filtri tipo e valuta sono nella filter bar globale (applicabili
sia a card che a tabella), i filtri per-colonna nelle colonne `type` e `currency` sono
ridondanti. L'utente vuole mantenerli solo per il sorting (ordinamento), non per il filtro.

**Soluzione**:
Aggiungere `filterable: false` alle colonne `type` e `currency`:
```typescript
{
    id: 'type',
    // ...existing...
    filterable: false,  // ← filtro globale nella filter bar
},
{
    id: 'currency',
    // ...existing...
    filterable: false,  // ← filtro globale nella filter bar
},
```

**Stima**: 5 min

---

### D9 — Filtro tipo globale: checkbox multi-select con pannello

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte` (filter bar, stato `filterType`)

**Problema**: Il filtro tipo è un `SimpleSelect` singolo (dropdown con un valore).
L'utente vuole un pannello con checkbox multi-select, come il filtro enum del DataTable,
in modo da poter selezionare più tipi contemporaneamente (es. STOCK + ETF).

**Soluzione**: Creare un componente `TypeFilterPopover.svelte` (o inline nella pagina):
1. State: `filterTypes = $state<Set<string>>(new Set())` (vuoto = tutti)
2. Bottone trigger: mostra "All Types" o il conteggio dei tipi selezionati
3. Pannello dropdown con checkbox per ogni tipo (con icona PNG + label tradotta)
4. Tasti "Select All" / "Clear All"
5. Logica di filtraggio: `filterTypes.size === 0 || filterTypes.has(asset.asset_type)`

**Pattern alternativo (semplice)**: Riusare `DataTableColumnFilter` con `type='enum'`
come componente standalone, con un anchor button personalizzato. Ma DataTableColumnFilter
è progettato per DataTable interno — meglio un componente leggero ad hoc.

**Stima**: 35 min

---

### D10 — Filtro valuta: multi-select con badge rimuovibili (OR logic)

**Area**: Frontend feature
**Priorità**: 🟡 Feature
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte` (filter bar, stato `filterCurrency`)

**Problema**: Il filtro valuta usa un singolo `CurrencySearchSelect`. L'utente vuole
poter selezionare più valute contemporaneamente, con logica OR (es. EUR + USD mostra
tutti gli asset in EUR o USD).

**3 Proposte per multi-select valuta**:

**Proposta A — Badge rimuovibili + CurrencySearchSelect**:
Il CurrencySearchSelect resta, ma ogni selezione **aggiunge** un badge anziché sostituire.
I badge selezionati compaiono come chips accanto/sotto il select. Click × per rimuovere.

```
┌─ All currencies ─▼─┐  [EUR ×] [USD ×] [CHF ×]
```

Pro: Minimo impatto UX, familiare. Contro: Occupa spazio orizzontale.

**Proposta B — Multi-checkbox dropdown (come tipo)**:
Un pannello dropdown con tutte le valute disponibili come checkbox, con bandiere.
Ricerca testuale in cima.

```
┌─ Currencies (3) ─▼─┐
│ 🔍 Search...         │
│ ☑ 🇪🇺 EUR             │
│ ☑ 🇺🇸 USD             │
│ ☑ 🇨🇭 CHF             │
│ ☐ 🇬🇧 GBP             │
│ [All] [Clear]        │
└──────────────────────┘
```

Pro: Compatto, uniforme con tipo. Contro: Se ci sono molte valute, serve scroll.

**Proposta C — CurrencySearchSelect multiplo con chips integrate**:
Il CurrencySearchSelect ha internamente un `mode: 'multi'` che mostra i valori
selezionati come chips dentro il campo. Al click apre il dropdown, le scelte si
accumulano. Pattern comune (Slack, Discord, JIRA tag picker).

```
┌─ [EUR ×] [USD ×] [+ Add...] ─┐
│ 🇨🇭 CHF - Swiss Franc         │
│ 🇬🇧 GBP - British Pound       │
│ 🇯🇵 JPY - Japanese Yen        │
└────────────────────────────────┘
```

Pro: Elegante, UX professionale. Contro: Più complesso da implementare.

**Scelta**: **Proposta A** — badge rimuovibili + CurrencySearchSelect.
State: `filterCurrencies = $state<Set<string>>(new Set())`.
Logica: `filterCurrencies.size === 0 || filterCurrencies.has(asset.currency)`.

> ℹ️ **Proposta C** (chips integrate nel campo, stile Slack/JIRA) rimandata a TODO_FUTURI
> come evoluzione futura. Vedi `TODO_FUTURI.md § CurrencySearchSelect multi-mode`.

**Stima**: 30 min

---

### D11 — Filter bar Assets: layout responsive dei filtri (Proposta D)

**Area**: Frontend UX
**Priorità**: 🟡 Refactor
**File coinvolti**:
- `frontend/src/routes/(app)/assets/+page.svelte` (filter bar)

**Problema**: I filtri (Search, Type, Currency multi-select, Active, Reset) che sostituiscono
la coppia di valute FX devono essere disposti in modo ergonomico nelle 3 modalità responsive.

**Nota**: Il DateRangePicker e il blocco azioni 2×2 **non cambiano** — restano identici alla
pagina FX. Questa sezione riguarda **solo** la disposizione dei filtri tra il datepicker e il
blocco 2×2.

**Contesto — FX filter bar attuale (riferimento)**:
```
FX wide:   [ datepicker ] [ valuta1 ] [ valuta2 ] [×]  ─── [ 2×2 ]
FX tablet: [ datepicker              ]                  [ 2×2 ]
           [ valuta1 ] [ valuta2 ] [×]
FX mobile: [ datepicker              ]
           [ valuta1 ] [ valuta2 ] [×]
           [ 2×2 in riga orizzontale ]
```

**Scelta: Proposta D** (derivata da C, proposta dall'utente), con filtri in blocco 2×2 in
tablet. Il layout dei 4 filtri segue l'ordine: 🔍Search → Active✓ → Type▼ → Currency badges.

#### Layout base Proposta D (senza badge valuta)

```
WIDE (≥950px) — filtri inline tra datepicker e 2×2:
┌────────────────────────────────────────────────────────────────────────────────┐
│ [◄3M►][24Dec—24Mar]  | [🔍Search] [Active✓] [Type▼(2)] [???badges???] × | [2×2] │
└────────────────────────────────────────────────────────────────────────────────┘

TABLET (500–950px) — filtri come blocco 2×2 a sinistra del 2×2 azioni:
┌──────────────────────────────────────────────────────────┐
│ [◄3M►][24Dec—24Mar] | [🔍Search  ] [Active✓]         | [2×2] │
│                      | [Type▼(2) ] [???badges???] ×  |       │
└──────────────────────────────────────────────────────────┘

MOBILE (<500px) — stacked centrato:
┌────────────────────────────┐
│   [◄ 3M ►][24Dec—24Mar]   │
│   [🔍 Search...         ]  │
│   [Active✓] [Type▼(2)]  × │
│   [???badges???]           │
│   [👁] [⚙] [↻] [↺]       │
└────────────────────────────┘
```

#### Posizionamento badge valuta — 3 opzioni

I badge (`[EUR×][USD×]`) hanno larghezza variabile (0-N valute). Il CurrencySearchSelect
(dropdown per aggiungere valute) sta nella cella bottom-right del 2×2 filtri in tutte le
opzioni. La domanda è: **dove finiscono i badge delle valute selezionate?**

---

**Opzione α — Badge nella cella bottom-right del 2×2 filtri**

I badge stanno accanto al CurrencySearchSelect nella cella bottom-right. Se ci sono 3+ badge,
la cella si espande e i badge wrappano.

```
WIDE (≥950px):
┌───────────────────────────────────────────────────────────────────────────────────┐
│ [◄3M►][24Dec—24Mar] | [🔍Search] [Active✓] [Type▼(2)] [EUR×][USD×][+] × | [2×2] │
└───────────────────────────────────────────────────────────────────────────────────┘

TABLET (500–950px):
┌───────────────────────────────────────────────────────────────┐
│ [◄3M►][24Dec—24Mar] | [🔍Search     ] [Active✓]          | [2×2] │
│                      | [Type▼(2)     ] [EUR×][USD×][+] × |       │
└───────────────────────────────────────────────────────────────┘
```

Pro: Compatto, 1-2 badge stanno perfetti.
Contro: 3+ badge rompono la simmetria; il CurrencySearchSelect diventa un ibrido
(dropdown + badge container) → non riutilizzabile immediatamente.

---

**Opzione β — Badge su riga dedicata sotto il 2×2 filtri**

Il CurrencySearchSelect resta un dropdown puro nella cella bottom-right. I badge compaiono
come "chips row" sotto la griglia, visibile solo se `filterCurrencies.size > 0`.

```
TABLET (500–950px):
┌───────────────────────────────────────────────────────────────┐
│ [◄3M►][24Dec—24Mar] | [🔍Search     ] [Active✓]          | [2×2] │
│                      | [Type▼(2)     ] [Currency ▼]    × |       │
│                      ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌       │
│                        [EUR×] [USD×] [CHF×] [GBP×]               │
└───────────────────────────────────────────────────────────────┘
```

Pro: 2×2 sempre simmetrico, CurrencySearchSelect riutilizzabile as-is.
Contro: Riga extra quando ci sono selezioni.

---

**Opzione γ — Badge nell'header, a sinistra del ViewModeToggle** ⭐ SCELTA

Il CurrencySearchSelect resta un dropdown puro nella cella bottom-right del 2×2 filtri
(come β). I badge delle valute selezionate salgono nell'**header bar**, allineati a destra,
immediatamente prima del toggle Grid/Table. Condizionali: appaiono solo se
`filterCurrencies.size > 0`.

```
WIDE (≥950px):
┌────────────────────────────────────────────────────────────────────────────────┐
│ Assets (12)                        [EUR×][USD×][CHF×]  [Grid|Table] [+ Add]  │
├────────────────────────────────────────────────────────────────────────────────┤
│ [◄3M►][24Dec—24Mar] | [🔍Search] [Active✓] [Type▼(2)] [Currency▼] × | [2×2] │
└────────────────────────────────────────────────────────────────────────────────┘

  senza selezioni valuta, header pulito:
┌────────────────────────────────────────────────────────────────────────────────┐
│ Assets (12)                                            [Grid|Table] [+ Add]  │
├────────────────────────────────────────────────────────────────────────────────┤
│ [◄3M►][24Dec—24Mar] | [🔍Search] [Active✓] [Type▼(2)] [Currency▼] × | [2×2] │
└────────────────────────────────────────────────────────────────────────────────┘

TABLET (500–950px):
┌──────────────────────────────────────────────────────────────┐
│ Assets (12)                  [EUR×][USD×]  [Grid|Table] [+]  │
├──────────────────────────────────────────────────────────────┤
│ [◄3M►][24Dec—24Mar] | [🔍Search     ] [Active✓]          | [2×2] │
│                      | [Type▼(2)     ] [Currency▼]     × |       │
└──────────────────────────────────────────────────────────────┘

  con DataTableToolbar attiva (bulk selection), i badge si nascondono:
┌──────────────────────────────────────────────────────────────┐
│ Assets (12)         [3 selected: Sync|Refresh|Delete|×]  [+] │
├──────────────────────────────────────────────────────────────┤
│ ...                                                          │
└──────────────────────────────────────────────────────────────┘

MOBILE (<500px):
┌──────────────────────────────────┐
│ Assets (12)      [Grid|Table] [+] │
│ [EUR×] [USD×] [CHF×]             │
├──────────────────────────────────┤
│   [◄ 3M ►][24Dec—24Mar]         │
│   [🔍 Search...              ]   │
│   [Active✓] [Type▼(2)]          │
│   [Currency▼]                 ×  │
│   [👁] [⚙] [↻] [↺]             │
└──────────────────────────────────┘
```

**Vantaggi di γ**:
1. **CurrencySearchSelect riutilizzabile** — resta un dropdown puro, identico a quello FX
2. **2×2 filtri sempre simmetrico** — nessuna cella che si espande
3. **Badge sempre visibili** — nell'header restano visibili anche scrollando il contenuto
4. **Separazione semantica chiara** — il dropdown (nel filter bar) è l'"azione di aggiungere",
   i badge (nell'header) sono il "risultato visibile" dei filtri attivi
5. **Graceful degradation** — quando la DataTableToolbar compare (bulk selection), i badge
   si nascondono con un semplice `{#if}` (non servono entrambi contemporaneamente)
6. **Pattern coerente** — l'header già ospita contenuto condizionale (DataTableToolbar)

**Implementazione** (nell'header, tra DataTableToolbar e ViewModeToggle):
```svelte
<!-- Currency filter badges — nell'header -->
{#if filterCurrencies.size > 0 && selectedAssetRows.length === 0}
    <div class="flex items-center gap-1.5 flex-wrap">
        {#each [...filterCurrencies] as currency}
            <span class="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium
                         bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300
                         border border-amber-200 dark:border-amber-700 rounded-full">
                {currency}
                <button onclick={() => filterCurrencies.delete(currency)}>×</button>
            </span>
        {/each}
    </div>
{/if}
```

**Stima**: 40 min (layout programmatico con `layoutMode` — pattern identico a FX page)

---

### D12 — Provider chain: fallback iniziali per icone non disponibili

**Area**: Frontend UX
**Priorità**: 🟢 Facile

**Problema**: Se un provider non ha `icon_url`, la visualizzazione ricca (D2) deve
mostrare le iniziali (2 char) come fallback, con sfondo colorato dal sistema di colori.

**Nota**: Incluso nella logica di D2. Documentato qui come promemoria per test.

**Stima**: incluso in D2

---

### Riepilogo Dipendenze Step 2e

```
D1 (centra bottone)  ────────── indipendente, facile
D3 (fix undefined)   ────────── 🔴 indipendente, bug bloccante
    │
D6 (i18n tipi asset) ────────── prerequisito per D7, D5, D9
    │
D7 (card icon + active) ─────── dopo D6 (usa stessi i18n e PNG)
    │
D2 (provider chain ricca) ───── indipendente (FxTable/FxSyncModal)
D12 (fallback iniziali) ─────── incluso in D2
    │
D8 (rimuovere filtro colonna)── indipendente, ma logico dopo D9
    │
D9 (tipo multi-checkbox) ────── dopo D6 (usa label tradotte)
D10 (valuta multi-select) ────── indipendente
D11 (layout filter bar) ──────── dopo D9 + D10 (dipende dalla UI dei filtri)
    │
D4 (ChartSettings Assets) ───── indipendente
D5 (icone filtro enum) ──────── dopo D6 (usa stesse icon map)
```

### Checklist Pre-Implementazione Step 2e

- [ ] D1: Centrare bottone ColumnVisibilityToggle — `justify-center`
- [ ] D2: Provider chain ricca con bandiere + icone favicon (FxTable + FxSyncModal)
- [ ] D3: Fix bulk sync undefined — mappare `string[]` a `FxRow[]` in `onSelectionChange`
- [ ] D4: Assets integrazione ChartSettingsModal (global + per-card)
- [ ] D5: AssetTable filtro tipo con icone PNG — estendere `EnumOption`
- [ ] D6: i18n tipi asset (8 tipi × 4 lingue) + icona PNG nel badge card
- [ ] D7: AssetCard icona asset + pallino active (come tabella)
- [ ] D8: Rimuovere `filterable` da colonne type e currency in AssetTable
- [ ] D9: Filtro tipo globale multi-checkbox con pannello
- [ ] D10: Filtro valuta multi-select — **Proposta A** (badge rimuovibili + CurrencySearchSelect) — Proposta C in TODO_FUTURI
- [ ] D11: Layout responsive filter bar Assets — **Proposta D** + **Opzione γ** (badge nell'header, CurrencySearchSelect puro nel 2×2)
- [ ] D12: Provider chain fallback iniziali (incluso in D2)

