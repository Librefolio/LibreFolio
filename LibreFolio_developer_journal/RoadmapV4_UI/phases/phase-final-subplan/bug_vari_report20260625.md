# Bug Report — LibreFolio QA (Docker Build)
> Analisi statica del codice — nessuna modifica apportata. Pronto per review.

---

## CATEGORIA A — Icona Broker (Fallback Chain incompleta)

Tre occorrenze dello stesso difetto: l'icona broker mostra solo il dot colorato invece di seguire la chain `icon_url → favicon → plugin_icon`.

---

### A-1 · `files?tab=brim` — FilesTable: icon assente se broker ha solo plugin

**File**: [`FilesTable.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/files/FilesTable.svelte#L231-L266)

**Root cause**: `getBrokerIconUrl()` (step 3 della chain) legge `_pluginIconCache` — una mappa riempita da `ensurePluginIconsLoaded()`. In `FilesTable` questa funzione **non viene mai chiamata**: nessuna chiamata a `ensurePluginIconsLoaded()` in tutta la pagina `/files`. Di conseguenza, se il broker ha solo `default_import_plugin` (senza `icon_url` né `portal_url`), `_pluginIconCache` è `null` → `getPluginIconUrl()` restituisce `null` → viene mostrato solo il dot.

**Evidenza sw**:
```ts
// brokerHelpers.ts:50-53
function getPluginIconUrl(pluginCode): string | null {
    if (!pluginCode || !_pluginIconCache) return null;  // ← null se non caricata
    return _pluginIconCache.get(pluginCode) ?? null;
}
```
`ensurePluginIconsLoaded()` è chiamata in `dashboard/+page.svelte:418`, `transactions/+page.svelte:145`, `RecentTransactionsPanel:61` — ma **non** in `files/+page.svelte`.

**Fix suggerito**: Aggiungere `await ensurePluginIconsLoaded()` nel blocco `onMount` di `files/+page.svelte` (o in `FilesTable.svelte` stesso all'`onMount`).

---

### A-2 · `transactions/` — Filtro broker (pannel laterale): solo dot per broker RecRowd

**File**: [`transactions/+page.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/transactions/+page.svelte#L145)

**Root cause**: Qui `ensurePluginIconsLoaded()` è chiamata (L145), quindi i casi con solo `portal_url` dovrebbero funzionare. Se Recrowd ha `portal_url` configurato ma il filtro mostra solo il dot, la causa è probabilmente che il **filtro broker nella sidebar** usa un componente separato che non passa `pluginCode` a `BrokerIcon`, oppure usa `getBrokerIconUrl()` in modo sincrono prima che la cache sia pronta (race condition: il filtro si renderizza prima che la `Promise` di `ensurePluginIconsLoaded` si risolva).

**Evidenza sw**: `getBrokerIconUrl` è una funzione **sincrona** che legge la cache. Se viene chiamata prima del ritorno di `ensurePluginIconsLoaded`, legge `_pluginIconCache = null`.

**Fix suggerito**: Garantire che il filtro broker si aggiorni *dopo* la risoluzione di `ensurePluginIconsLoaded` (es. svuotare/ricreare il derived che alimenta le enum options del filtro dopo che la promise è settled, oppure spostare il render del filtro broker sotto un `{#await}` / `$effect` reattivo).

---

### A-3 · Dashboard home — Filtro broker: solo dot colorato

**File**: [`dashboard/+page.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/dashboard/+page.svelte#L418)

**Root cause**: Stessa race condition di A-2. `ensurePluginIconsLoaded()` è chiamata ma i broker-icon cells che usano `getBrokerIconUrl()` come parte di un `$derived` si calcolano prima che la Promise sia settled.

**Fix suggerito**: Uguale ad A-2.

---

## CATEGORIA B — Pulsante Refresh assente in `/files`

**File**: [`files/+page.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/files/+page.svelte)

**Problema**: Non esiste alcun pulsante "Ricarica" né in `tab=static` né in `tab=brim`. L'utente non può forzare un aggiornamento della lista file dal backend senza ricaricare l'intera pagina.

**Evidenza sw**: Il codice al mount carica i file una sola volta. Non c'è funzione `reload()` pubblica né un pulsante collegato.

**Fix suggerito**: Aggiungere un'icona `RefreshCw` (lucide) nell'header accanto al bottone Upload, che richiami la funzione di caricamento (`loadFiles()` o equivalente). Pattern già presente in altre pagine.

---

## CATEGORIA C — Import BRIM: modale identificativo mancante su asset appena creato

**File**: [`ImportWizardModal.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/transactions/modals/ImportWizardModal.svelte#L2377-L2382)

**Problema**: Quando nel wizard l'utente crea un nuovo asset tramite `AssetModal` e poi al salva viene assegnato l'asset, se il provider non ha identificativo, la modale "Vuoi assegnare questo identificativo?" **non si apre**. Succede solo con `resolveAssetManual()` (selezione manuale da AssetSelect), non con il percorso `oncreated` del nuovo asset.

**Evidenza sw**:
```ts
// ImportWizardModal.svelte:2377-2380
oncreated={(assetId) => {
    resolveAsset(createAssetForFakeId!, assetId);  // ← chiama resolveAsset (semplice)
    createAssetForFakeId = null;
}}
```
`resolveAsset()` (L352) si limita a salvare la risoluzione — **non chiama mai** `resolveAssetManual()` (L391) che è l'unica che apre `identifierPromptOpen`. Quindi l'asset appena creato non riceve mai il prompt identificativo.

**Secondo problema**: La modale `AssetModal` aperta dall'import wizard parte con `providerNoProvider = false` (L469, inizializzazione di default) ma dovrebbe aprirsi con **"nessun provider" già selezionato** — perché l'asset viene creato manualmente dall'import, non da una ricerca online.

**Fix suggerito**:
1. In `oncreated`, dopo `resolveAsset()`, replicare la logica di `resolveAssetManual()` per controllare se l'asset appena creato manca dell'identificativo estratto e aprire il prompt.
2. Passare una prop `initialNoProvider={true}` all'`AssetModal` aperto dall'import wizard.

---

## CATEGORIA D — BulkTransactionModal: selettore righe non compare

**File**: [`TransactionBulkModal.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/transactions/modals/TransactionBulkModal.svelte#L3015-L3034)

**Problema**: Dopo un import, la toolbar di selezione righe non compare. Il sospetto iniziale era `pageSize=∞` ma il DataTable ha `enablePagination={false}` — quindi non è questo.

**Root cause probabile**: Il DataTable è configurato con `enableSelection={true}` e `selectionMode='multi'` (default). La toolbar di selezione bulk è **inline nella modal** (L2969-L2980) e compare solo se `bulkTableSelectedRows.length > 0`. Il problema è che dopo l'import il `DataTable` interno non propaga la selezione a `bulkTableSelectedRows` via `onSelectionChange` — oppure c'è un **z-index conflict** tra la modal (`zIndex=50`) e il dropdown/toolbar che viene renderizzato sotto.

**Evidenza sw**:
- Il DataTable del bulk usa `stickyActions={false}` ma non ha impostazione esplicita di z-index.
- La modal `ModalBase` ha z-index 50; i figli della `DataTable.svelte` con `position: sticky` o `position: absolute` potrebbero essere clippati dall'`overflow-y: auto` del contenitore `flex-1 min-h-0 overflow-y-auto` a L3014.
- Il `SelectionBar` esterno (visibile nelle altre pagine) non è usato nella BulkModal — la toolbar è embedded nella top-bar (L2969).

**Fix suggerito**: Verificare se il contenitore `overflow-y: auto` della BulkModal stia clippando elementi position-absolute della DataTable (checkbox, context menu). Aggiungere `overflow: visible` o usare `isolation: isolate` sul contenitore della tabella. In alternativa, verificare che `onSelectionChange` stia aggiornando correttamente `bulkTableSelectedRows`.

---

## CATEGORIA E — Emoji settori assenti in Asset Detail (ma presenti in Dashboard)

**File**: [`assets/[id]/+page.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/assets/%5Bid%5D/+page.svelte#L1937), [`AllocationPieChart.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/AllocationPieChart.svelte#L131-L135)

**Problema**: Nel grafico a torta settoriale dell'asset detail le emoji non compaiono. In dashboard funzionano.

**Root cause**: Differenza nel formato dati:

- **Dashboard** (`+page.svelte:171`): costruisce entries con `emoji: i?.emoji ?? null` — l'emoji arriva dal backend come campo dell'`AllocationItem`.
- **Asset Detail** (`+page.svelte:937`): legge `cp.sector_area?.distribution` che è un `Record<string, number>` (solo chiave→peso) — **nessun campo emoji**. Le entries passate ad `AllocationPieChart` hanno quindi `emoji: undefined`.

```svelte
<!-- asset detail +page.svelte:1937 — nessun emoji -->
<AllocationPieChart data={Object.entries(sectorDistribution).map(([name, w]) =>
    ({name, value: w * 100, amount: 0}))} ... />
```

Il componente usa `entry.emoji ?? ''` — quindi stringa vuota, nessuna emoji visualizzata. Il `sectorStore` ha la mappa emoji (da backend) ma non viene usata in questo path.

**Fix suggerito**: Nel `map()` di L1937, aggiungere `emoji: getSectorEmoji(name)` importando da `sectorStore`. Analogamente per il selettore di settore nella modale edit/create (`DistributionEditor`): già usa `getSectorKeysList()` ma non mostra l'emoji nel selector label.

---

## CATEGORIA F — Middle-click su righe DataTable non apre nuovo tab

**File**: [`DataTable.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/table/DataTable.svelte#L1211-L1232)

**Problema**: Il click centrale del mouse su una riga dovrebbe aprire il link in un nuovo tab (comportamento nativo `<a>` che non è implementato).

**Root cause**: Le righe sono `<tr>` con `onclick` — non sono `<a>` tag, né hanno un `auxclick` handler. Il browser gestisce il middle-click solo su tag `<a href>` nativi. La navigazione avviene tramite `onRowClick → goto()` in Svelte (SPA navigation), che non è intercettabile dal browser per aprire nuovi tab.

**Evidenza sw**: `DataTable.svelte:1215-1219` — `onclick` SPA, nessun `onauxclick`, nessun `href` su `<tr>`.

**Fix suggerito**: Due approcci:
1. Wrappare la cella "nome" con un `<a href={rowUrl}>` reale (se ogni riga ha un URL destinazione), lasciando che `onclick` faccia `e.preventDefault()` + `goto()` per il click sinistro, mentre middle-click viene gestito nativamente dal browser.
2. Aggiungere un prop `getRowHref?: (row: T) => string` a `DataTable` e gestire `onauxclick={(e) => { if(e.button === 1) window.open(getRowHref(row), '_blank') }}` sul `<tr>`.

---

## CATEGORIA G — Valuta di default nella creazione asset: USD hardcoded invece di impostazione utente

**File**: [`AssetModal.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/assets/AssetModal.svelte#L122)

**Root cause**:
```ts
let currency = $state('USD');  // L122 — hardcoded
```
Il reset all'apertura in modalità create (L454): `currency = 'USD'`. Il valore corretto è `userSettings.base_currency` (store disponibile a `settings.ts:19` con default `'EUR'`) o `globalSettings.default_currency`.

**Fix suggerito**: Al reset dei form fields in modalità create, leggere `get(userSettings)?.base_currency ?? 'EUR'` come valore iniziale di `currency`.

---

## CATEGORIA H — Traduzione `asset.type.LIQUIDITY` mancante

**File**: [`en.json`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/i18n/en.json#L114-L125)

**Root cause**: La chiave nel JSON è `"Liquidity"` (con L maiuscola), ma il codice che genera la chiave i18n usa `"LIQUIDITY"` (tutto maiuscolo come gli altri tipi).

**Evidenza sw**:
```json
// en.json:124
"Liquidity": "Liquidity"
```
Tutti gli altri tipi: `"STOCK"`, `"ETF"`, `"BOND"`, `"CRYPTO"`, ecc. — la convenzione è UPPERCASE. La chiave dovrebbe essere `"LIQUIDITY"`.

**Fix suggerito**: Rinominare `"Liquidity"` → `"LIQUIDITY"` in tutti e 4 i file i18n (`en.json`, `it.json`, `fr.json`, `es.json`).

---

## CATEGORIA I — Tooltip MWRR cumulativo fuoriesce dallo schermo su mobile

**File**: [`Tooltip.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/ui/feedback/Tooltip.svelte#L291-L315), [`KpiMetricBar.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/dashboard/KpiMetricBar.svelte#L47)

**Root cause**: Il tooltip ha `max-width: 400px` (prop default, L30) e `width: max-content`. Su schermi <400px il `left` calcolato è corretto (clamped a L186) ma **il testo non va a capo** perché `max-width: 400px` > viewport width. Il `max-width` via style inline viene impostato a 400px sempre, anche su mobile.

**Evidenza sw**:
```svelte
<!-- Tooltip.svelte:274 -->
<div ... style="max-width: {maxWidth}; ..."
```
`maxWidth='400px'` su un viewport a 375px → tooltip largo 375px ma il posizionamento si basa su `tooltipRect.width` che potrebbe non considerare il wrapping prima del paint.

**Fix suggerito**:
1. Cambiare `maxWidth` default a `min(400px, calc(100vw - 20px))` usando CSS `min()`.
2. Oppure nei `KpiMetricBar` usare un `maxWidth` esplicito più stretto (es. `220px`) per i tooltip da KPI card.
3. Soluzione robusta: nel CSS di `.tooltip-fixed` aggiungere `max-width: min(var(--tooltip-max-w, 400px), calc(100vw - 20px))`.

---

## CATEGORIA J — Card KPI: tooltip mancanti su Valore Mercato, Valore Contabile, Liquidità + marker liquidità

**File**: [`dashboard/+page.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/dashboard/+page.svelte#L620-L626), [`KpiMetricBar.svelte`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/dashboard/KpiMetricBar.svelte)

**Problema**: Le metriche "Valore di Mercato", "Valore Contabile" e "Liquidità" nella card KPI principale non hanno tooltip, a differenza delle metriche MWRR che ne hanno uno.

**Evidenza sw**: `KpiMetricBar` supporta già il prop `tooltip` — basta aggiungerlo nelle invocazioni.

**Secondo problema**: Liquidità non ha il marker sulla barra per la liquidità a inizio periodo (il prop `marker` su `KpiMetricBar` esiste ma non viene passato per Liquidità).

**Fix suggerito**:
1. Aggiungere chiavi i18n per i tooltip di queste 3 metriche.
2. Passare `marker={liquidityAtStart}` e `markerTooltip={...}` al `KpiMetricBar` della Liquidità.

---

## CATEGORIA K — Sync completo alla creazione asset con provider

**File**: [`AssetModal.svelte:saveCreate()`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/assets/AssetModal.svelte#L887-L950)

**Problema**: Alla **creazione** di un asset con provider, non viene eseguito nessun sync iniziale. Il sync automatico (L1087-L1099) è nella funzione `saveEdit()`, non in `saveCreate()`. Quindi un asset creato ex novo con provider assegnato non ha nessun dato storico finché l'utente non sincronizza manualmente.

**Evidenza sw**: `saveCreate()` termina a L947-L949 senza alcuna chiamata a `sync_prices_bulk`. `saveEdit()` invece a L1088-L1095 fa il sync automatico degli ultimi 5 anni.

**Richiesta specifica**: Il sync alla creazione dovrebbe essere "all/max" — cioè con `start` = 50 anni fa (o la data minima supportata dal provider). Questo richiederebbe o un parametro speciale `"MAX"` nell'API di sync, o una data hardcoded tipo `1975-01-01`.

**Fix suggerito**:
1. Nel backend aggiungere un tag/sentinel `"MAX"` alla `DateRangeModel` del sync endpoint (già esiste logica simile in `date_sentinel.py`).
2. In `saveCreate()`, dopo l'assign provider, chiamare sync con `start="MAX"` (o `1975-01-01`) ed `end=today` — solo se il provider non è `scheduled_investment` o altri provider parametrici speciali.

---

## CATEGORIA L — Soglie observer `createResponsiveLayout` da ricalibrate

**File**: [`assets/+page.svelte:183`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/assets/+page.svelte#L183), [`assets/[id]/+page.svelte:113`](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/(app)/assets/%5Bid%5D/+page.svelte#L113)

**Problema**: Le soglie del `createResponsiveLayout` delle pagine "asset global" e "FX global" erano state calibrate prima dell'aggiunta dei preset `YTD` e `ALL` al `DateRangePicker`. L'aggiunta di questi due pulsanti occupa più spazio orizzontale nella filter bar, provocando wrapping indesiderato o layout compresso.

**Evidenza sw**:
```ts
// assets/+page.svelte:183
const layout = createResponsiveLayout({wide: 1240, tablet: 960, tabletS: 500, labelHide: 460});
// fx/+page.svelte:105
const fxLayout = createResponsiveLayout({wide: 1020, tablet: 660, tabletS: 520, labelHide: 500});
```

**Fix suggerito**: Aumentare i valori `wide` e `tablet` di ~80-120px nelle due pagine (la quantità esatta va verificata visivamente). La fx page usa un metodo di calibrazione già documentato nei commenti (L216-L218) che può essere riapplicato.

---

## Riepilogo Priorità

| # | Issue | Categoria | Impatto | File Principale |
|---|-------|-----------|---------|-----------------|
| A-1 | Icona broker mancante in `/files?tab=brim` | Bug | Alto | `FilesTable.svelte` / `files/+page.svelte` |
| A-2 | Icona broker mancante filtro transactions | Bug | Medio | `transactions/+page.svelte` |
| A-3 | Icona broker mancante filtro dashboard | Bug | Medio | `dashboard/+page.svelte` |
| B | Refresh mancante in `/files` | UX | Medio | `files/+page.svelte` |
| C | Modale identificativo assente su asset creato da import | Bug | Alto | `ImportWizardModal.svelte` |
| D | Toolbar selezione righe non compare in BulkModal | Bug | Alto | `TransactionBulkModal.svelte` |
| E | Emoji settori assenti in Asset Detail | Bug | Basso | `assets/[id]/+page.svelte` |
| F | Middle-click non apre nuovo tab | UX | Basso | `DataTable.svelte` |
| G | Valuta default USD hardcoded in creazione asset | Bug | Medio | `AssetModal.svelte` |
| H | Traduzione `LIQUIDITY` mancante | Bug | Medio | `*.json` i18n files |
| I | Tooltip MWRR fuoriesce su mobile | Bug | Basso | `Tooltip.svelte` |
| J | Tooltip mancanti su 3 metriche KPI + marker liquidità | UX | Basso | `dashboard/+page.svelte` |
| K | Nessun sync full-history alla creazione asset | Feature | Medio | `AssetModal.svelte` / backend |
| L | Soglie observer da ricalibrate (YTD/ALL aggiunti) | UX | Basso | `assets/+page.svelte`, `fx/+page.svelte` |


---

Scoperto bug sul promote in bulk modal che suggerisce promote per asset che hanno solo tipo invertito e data range compatibile, ma ammontare sbagliato.

---

## Fix effettuati (sintesi per categoria)

### A — Icona Broker (Fallback Chain)

**A-1** (`files/+page.svelte`, `types/broker.ts`, `FilesTable.svelte`):
- `BrokerInfo` type era privo di `default_import_plugin` → aggiunto
- `brokerMap` in files/ ricostruita includendo il campo
- Aggiunto `await ensurePluginIconsLoaded()` in `onMount` di files/ prima di `loadBrokers()`
- `FilesTable.svelte` enumOptions broker: aggiunto `dotColor` mancante

**A-2/A-3** (`TransactionsTable.svelte`, `DataTableColumnFilter.svelte`, `dashboard/+page.svelte`, `BrokerIcon.svelte`):
- Race condition: aggiunto `pluginIconsReady = $state(false)` in transactions e dashboard; impostato `true` dopo `ensurePluginIconsLoaded()`, usato come dipendenza in `$derived brokers` per forzare re-render dopo cache
- Favicon fallback: in `DataTableColumnFilter.svelte` adottato overlay pattern (dot colorato dietro, img sopra con `visibility:hidden` on error); `dotColor` ora sempre impostato per broker enum options in `TransactionsTable` e `FilesTable`
- Dashboard sidebar broker filter: stesso overlay pattern con dot colorato
- Aggiunto `referrerpolicy="no-referrer"` su tutte le favicon `<img>` (`BrokerIcon`, `DataTableColumnFilter` ×2, `dashboard/+page.svelte`)

> **⚠️ Fuori pista**: `SectorSearchSelect.svelte` (non `DistributionEditor.allSectorOptions`) era il target corretto per E; la prima patch era sul componente sbagliato.

---

### B — Refresh in `/files`

`files/+page.svelte`: aggiunta icona `RefreshCw` (lucide) nell'header accanto al pulsante Upload; onclick chiama `loadFiles()`.

---

### C — Import Wizard: modale identificativo mancante

`ImportWizardModal.svelte` + `AssetModal.svelte`:
- Estratta funzione `checkAndPromptIdentifier(fakeId, realAssetId, res)` condivisa tra `resolveAssetManual` e `oncreated`
- Nel callback `oncreated`, dopo `resolveAsset()`, chiamata `checkAndPromptIdentifier` per aprire il prompt se l'asset manca dell'identificativo estratto
- Aggiunto prop `initialNoProvider?: boolean` ad `AssetModal`; passato `initialNoProvider={true}` all'AssetModal aperto dall'import wizard

---

### D — BulkModal: selezione, promote falsi positivi, paginazione

**Selezione** (`TransactionBulkModal.svelte`):
- Round 1: introdotto `$effect` per pulizia selezione — rivelatosi regressione (cancellava selezione su add/clone) → rimosso in Round 2

**Promote falsi positivi** (`TransactionBulkModal.svelte`):
- Estratta funzione `cashAmountsCancel(opA, opB)`: verifica che `numA + numB ≈ 0` (somma zero con epsilon 1e-9) — rigetta suggest per importi diversi
- Applicata in **tutti e tre** i punti: `localSuggestions`, `bannerSuggestions` (edit loop), `selectedForPromote`
- Prima iterazione applicava solo a `selectedForPromote` → bug persisteva perché il banner viene da `localSuggestions`

> **⚠️ Fuori pista**: il suggest "Merge → Cash Transfer" veniva da `localSuggestions` (banner auto), non da `selectedForPromote` (selezione manuale); il fix andava applicato in entrambi i posti.

**Paginazione** (`DataTable.svelte`, `TransactionBulkModal.svelte`):
- Aggiunto prop `alwaysShowPagination?: boolean` a `DataTable`; quando `true` mostra la barra di paginazione anche se tutti gli item entrano nella prima pagina
- BulkModal: `enablePagination={true}`, `alwaysShowPagination={true}`, `defaultPageSize=25`, `pageSizeOptions=[5, 10, 25, 50, 0]`

---

### E — Emoji settori

`AllocationPieChart.svelte`: in mode=type aggiunto lookup `$t('asset.types.' + name.toUpperCase())` con fallback al nome raw; risolve "LIQUIDITY" in tutte le lingue.

`SectorSearchSelect.svelte`: aggiunto `getSectorEmoji(k)` nel label del `sectorOptions` derived (questo è il componente reale usato da DistributionEditor per il selettore settore).

`assets/[id]/+page.svelte`: aggiunto `emoji: getSectorEmoji(name)` nel map del pie chart settoriale.

---

### F — Middle-click DataTable

`DataTable.svelte`: aggiunto prop `getRowHref?: (row: T) => string | undefined` e handler `onauxclick` sul `<tr>` (button=1 → `window.open`). Passato a `AssetTable.svelte`.

---

### G — Valuta default USD

`AssetModal.svelte`: in `resetForm()` cambiato `currency = 'USD'` in `currency = get(userSettings)?.base_currency ?? 'EUR'`. Aggiunti import `userSettings` e `get`.

---

### H — Traduzione LIQUIDITY

4 file i18n: rinominata chiave `"Liquidity"` → `"LIQUIDITY"` in `asset.types`. `AllocationPieChart` type mode ora cerca `$t('asset.types.' + name.toUpperCase())` per tradurre i nomi tipi asset nei grafici.

---

### K — Sync full-history alla creazione asset

`AssetModal.svelte saveCreate()`: dopo assign provider, chiamata sync non-bloccante `start='1975-01-01'` → `end=today`. Esclusi provider parametrici (`isParametricProvider`).

---

### L — Responsive layout thresholds

`assets/+page.svelte`: `wide 1240→1340`, `tablet 960→1060`.
`fx/+page.svelte`: `wide 1020→1120`, `tablet 660→760`.

---

## Test da scrivere / potenziare (non-regression)

Solo per i bug funzionali; label, tooltip e UX non coperti.

### A — Broker icon fallback chain

**Unit test** (`brokerHelpers.test.ts`):
- `getBrokerIconUrl(broker)` ritorna `null` se `_pluginIconCache = null` e broker ha solo `default_import_plugin` → dopo `ensurePluginIconsLoaded()` ritorna l'URL corretto
- `getBrokerIconUrl(broker)` ritorna il favicon URL se broker ha `portal_url`

**E2E** (`files.spec.ts`):
- Navigare `files/?tab=brim` con un broker che ha solo `default_import_plugin` → nel filtro broker deve comparire un dot colorato (non elemento vuoto)
- Dopo apertura dropdown filtro broker: verificare `data-testid="filter-enum-option-{id}"` presente per ogni broker

**E2E** (`transactions.spec.ts`, `dashboard.spec.ts`):
- Il dropdown filtro broker (`data-testid="filter-enum-option-{id}"`) contiene un elemento icona (img o dot span) per ogni broker

---

### C — Import wizard: identifier prompt su asset creato

**E2E** (`import-wizard.spec.ts`):
1. Aprire import wizard con un file BRIM che ha un asset con ISIN estratto
2. Per quell'asset scegliere "Crea nuovo asset" → compilare e salvare
3. Verificare che appaia la modale "Vuoi assegnare questo identificativo?" (`data-testid="identifier-prompt-modal"` o simile)
4. Verificare che la modale `AssetModal` aperta dal wizard mostri "Nessun provider" pre-selezionato

---

### D — Promote: nessun falso positivo su importi diversi

**Unit test** (`promoteHelpers.test.ts` o inline `TransactionBulkModal.test.ts`):
- `cashAmountsCancel(opA, opB)` = `true` per cash.amount `"-360.87"` + `"360.87"` (esatta cancellazione)
- `cashAmountsCancel(opA, opB)` = `false` per cash.amount `"-360.87"` + `"1445.00"` (importi diversi)
- `cashAmountsCancel(opA, opB)` = `false` se uno dei due ha `cash = null`

**E2E** (`bulk-modal.spec.ts`):
- Importare due transazioni CASH_IN/CASH_OUT con importi diversi → nessun banner "Merge → Cash Transfer" comparire
- Importare due transazioni CASH_IN/CASH_OUT con stesso importo e segno opposto (e broker diversi) → banner promote DEVE comparire

---

### D — Paginazione BulkModal

**E2E** (`bulk-modal.spec.ts`):
- Aprire BulkModal con almeno 1 riga → `DataTablePagination` componente visibile (`data-testid="pagination"` o selector del componente)
- Verificare che le page size options includano 5

---

### G — Valuta default in creazione asset

**E2E** (`asset-modal.spec.ts`):
1. Impostare `base_currency = 'EUR'` nelle user settings
2. Aprire modale creazione asset
3. Verificare che il campo Valuta mostri "EUR" come default (non "USD")

**Unit test** / `$effect` test:
- `resetForm()` legge `userSettings.base_currency` e lo imposta come `currency`

---

### K — Sync automatico alla creazione asset

**E2E** (`asset-modal.spec.ts`):
1. Creare asset con provider assegnato
2. Intercettare (mock/network spy) la chiamata a `sync_prices_bulk`
3. Verificare che la chiamata avvenga con `date_range.start = '1975-01-01'`
4. Ripetere con provider parametrico (`scheduled_investment`) → nessuna chiamata sync

---

### E — Emoji nei selettori settore

**E2E** (`asset-modal.spec.ts`):
- Aprire modale creazione asset → tab "Classificazione" → aprire dropdown settore
- Verificare che ogni opzione nel dropdown contenga un carattere emoji prima del nome settore (regex `\p{Emoji}`)

