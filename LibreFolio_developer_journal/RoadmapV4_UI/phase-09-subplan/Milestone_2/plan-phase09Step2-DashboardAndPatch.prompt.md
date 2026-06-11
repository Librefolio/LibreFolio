# Piano Implementativo di Dettaglio: Milestone 2 — Dashboard Home & Backend Patch

> **Contesto**: Questo è il piano esecutivo per la Milestone 2 del progetto LibreFolio (Phase 09 — Riprogettazione Dashboard & Broker).
> La Milestone 1 ha creato il backend (endpoint, servizi, algoritmi finanziari). Questa milestone connette tutto al frontend con la Dashboard Home e risolve un gap backend (serie storiche percentuali).

## Riferimenti Documentali e Decisionali

| Documento | Percorso | Contenuto |
|-----------|----------|-----------|
| **Wireframe Dashboard** | [plan_ui_dashboard.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_dashboard.md) | ASCII wireframe della Dashboard, requisiti dati frontend, specifiche KPI cards e Growth chart |
| **Implementation Plan** | [implementation_plan.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_plan.md) | Gap analysis completa, decisioni architetturali su store, caching, allocazioni pesate |
| **Roadmap Milestone** | [implementation_roadmap.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_roadmap.md) | Target point M2 (L31-49): criterio di verifica utente |
| **Copilot Instructions** | [copilot-instructions.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/.github/copilot-instructions.md) | Regole progetto: Svelte 5 Runes, Tailwind CSS 4, asyncio.to_thread, `./dev.py` CLI, no git commit |
| **Algoritmi Finanziari** | [plan_financial_algorithms.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_financial_algorithms.md) | Specifiche matematiche TWRR, MWRR (XIRR), Simple ROI, WAC |

## Riferimenti Sorgenti Chiave

### Backend
| File | Percorso | Ruolo |
|------|----------|-------|
| **Schemi Analytics** | [analytics.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/schemas/analytics.py) | `PortfolioHistoryPoint` (L144), `AssetHistoryPoint` (L156), `PortfolioSummary` (L121) |
| **Portfolio Service** | [portfolio_service.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/services/portfolio_service.py) | `get_history()` (L745), `get_asset_history()` (L801), `_build_history_series()` (L302) |
| **API Endpoints** | [analytics.py (api)](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/api/v1/analytics.py) | `/portfolio/history` (L160), `/portfolio/asset-history` (L183) |
| **ROI Utils** | [roi_utils.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/utils/financial/roi_utils.py) | `calculate_twrr_series` (L180), `calculate_mwrr_series` (L270), `calculate_simple_roi_series` (L81) |

### Frontend — Componenti Esistenti (da riutilizzare)
| Componente | Percorso | Props Chiave | Note |
|------------|----------|-------------|------|
| **DateRangePicker** | [DateRangePicker.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/DateRangePicker.svelte) | `dateFrom`, `dateTo`, `onchange` | Preset: 1W/1M/3M/6M/1Y/2Y/YTD/ALL |
| **MultiSelectPopover** | [MultiSelectPopover.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/MultiSelectPopover.svelte) | `items: {id, label, checked}[]`, `onchange` | Perfetto per il filtro broker |
| **TransactionsTable** | [TransactionsTable.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/transactions/TransactionsTable.svelte) | `compact`, `limit`, `showFilters`, `showPagination`, `brokerId` | 789 righe, TanStack Table |
| **LineChart** | [LineChart.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/LineChart.svelte) | `dates`, `series: SeriesConfig[]`, `height`, `yAxisLabel` | Multi-serie, DataZoom, multi-asse Y |
| **SemiDonutChart** | [SemiDonutChart.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/SemiDonutChart.svelte) | `data: {name, value, color?}[]`, `title`, `centerLabel` | Donut 180° |
| **SectorPieChart** | [SectorPieChart.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/SectorPieChart.svelte) | `data: {name, value}[]`, `title` | Donut pieno con colori settore |
| **GeographyMap** | [GeographyMap.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/GeographyMap.svelte) | `data: {name, value}[]`, `title`, `height` | Mappa mondo ECharts, gestisce già "Unknown" |
| **Chart Index** | [index.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/charts/index.ts) | — | Re-export di tutti i chart |

### Frontend — Store Esistenti (pattern di riferimento)
| Store | Percorso | Pattern |
|-------|----------|---------|
| **brokerStore** | [brokerStore.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/stores/brokerStore.ts) | Svelte 5 `$state`, `fetchBrokers(force)`, `invalidateBrokers()` — **da usare come template** |
| **countryStore** | [countryStore.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/stores/countryStore.ts) | Dati country per le mappe |

### Frontend — API Client
| File | Percorso | Note |
|------|----------|------|
| **Zodios Client** | [client.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/api/client.ts) | Instanza Zodios con auth interceptor |
| **Endpoints** (auto-gen) | [endpoints.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/api/endpoints.ts) | Rigenerato da `./dev.py api sync` |

### Frontend — Layout e Routing
| File | Percorso | Note |
|------|----------|------|
| **Layout App** | [+layout.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/+layout.svelte) | Sidebar nav — **aggiungere link a `/dashboard`** |
| **Home attuale** | [+page.svelte](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/routes/+page.svelte) | Redirect/landing — **redirigere a `/dashboard`** |
| **Tailwind Theme** | [app.css](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/app.css) | Token: `--color-success`/`--color-danger` per gain/loss |

---

## Decisioni Architetturali Prese

1. **MWRR incluso nelle serie storiche**: Nonostante sia computazionalmente pesante (Newton-Raphson per ogni giorno), l'ottimizzazione warm-start in `roi_utils.py` (L298: `prev_guess = rate`) lo rende accettabile. I test sono tutti verdi. Va avvolto in `asyncio.to_thread()` come da docstring L279.
2. **Allocazioni pesate sul Valore di Mercato**: Le allocazioni (tipo, settore, geografia) sono pesate sul NAV corrente, non sul costo. Gli asset senza metadati → categoria **"Unknown"** (non "Other"). Cfr. [implementation_plan.md L51-53](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_plan.md).
3. **Svelte 5 Runes obbligatorie**: `$state()`, `$derived()`, `$effect()` — mai il vecchio `$:` reattivo. Cfr. [copilot-instructions.md L74](file:///Users/ea_enel/Documents/00_My/LibreFolio/.github/copilot-instructions.md).
4. **portfolioStore come Single Source of Truth**: Cache parametrizzata (chiave = `broker_ids + date_range`), invalidata su CRUD transazioni e import CSV. Cfr. [implementation_plan.md L79-90](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_plan.md).

---

Questo piano andrà seguito passo per passo. Ricordarsi di aggiornare questo file annotando "✅" e le "Note implementazione" alla fine di ogni step.

---

## Step 1: Backend Patch — Popolare le Serie Storiche Percentuali ✅

**Target files:**
- [portfolio_service.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/services/portfolio_service.py)
- [analytics.py (schemas)](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/schemas/analytics.py)

### 1.0 Stato Attuale (da verifica codebase)
I campi `twrr: Optional[SafeDecimal]`, `mwrr: Optional[SafeDecimal]`, `roi: Optional[SafeDecimal]` **esistono già** nei modelli Pydantic `PortfolioHistoryPoint` (L144-153) e `AssetHistoryPoint` (L156-164). Sono stati aggiunti durante la Milestone 1 ma **non vengono mai popolati** — restano sempre `None`.

Le funzioni `calculate_twrr_series` e `calculate_mwrr_series` sono **già importate** in `portfolio_service.py` (L58) ma **mai chiamate**. La funzione `calculate_simple_roi_series` **non è importata**.

### 1.1 Aggiungere l'import mancante ✅
In [portfolio_service.py](file:///Users/ea_enel/Documents/00_My/LibreFolio/backend/app/services/portfolio_service.py), aggiungere `calculate_simple_roi_series` all'import da `roi_utils` (area L55-58).

> **Note implementazione (2026-06-11)**: Import aggiunto alla riga del blocco `roi_utils`. Verificato con `python -c "from backend.app.services.portfolio_service import PortfolioService"` — OK.

### 1.2 Modificare `get_history()` (L745-799) ✅
Dopo che `_build_history_series()` ha prodotto la lista di `PortfolioHistoryPoint` (con `cash_value`, `invested_value`, `nav_value`):

1. **Costruire gli input ROI** a partire dalla serie già calcolata:
   - `nav_snapshots: list[NAVSnapshot]` → uno per ogni `PortfolioHistoryPoint` con `(date, nav_value)`
   - `cash_flows: list[CashFlowInput]` → derivati dalle transazioni di tipo `DEPOSIT`/`WITHDRAWAL` (sign convention: deposit < 0)

2. **Chiamare le tre funzioni serie in parallelo dove possibile:**
   ```python
   twrr_series = calculate_twrr_series(nav_snapshots, cash_flows)        # O(N), CPU leggero
   roi_series = calculate_simple_roi_series(nav_snapshots, cash_flows)    # O(N), CPU leggero
   mwrr_series = await asyncio.to_thread(                                # CPU pesante → thread
       calculate_mwrr_series, nav_snapshots, cash_flows
   )
   ```

3. **Mappare i risultati sui PortfolioHistoryPoint esistenti:**
   Creare un dizionario `{date → (twrr, mwrr, roi)}` dalle tre serie e aggiornare ogni punto della history.
   > **Nota:** `twrr_series` e `roi_series` hanno un punto per ogni snapshot (escluso il primo), `mwrr_series` idem. Il primo punto della history non avrà metriche percentuali (resta `None`).

> **Note implementazione (2026-06-11)**: Implementato come pianificato. I `cash_flows` vengono costruiti dai `rows` già in memoria (DEPOSIT → negative, WITHDRAWAL → positive, già convertiti in base currency). La `mwrr_series` è avvolta in `asyncio.to_thread`. I risultati mappati con dict `{date → value}` su ogni `PortfolioHistoryPoint`.

### 1.3 Modificare `get_asset_history()` (L801-854) — ⚠️ DEFERRED
Stessa logica di 1.2 adattata al contesto asset:
- `nav_snapshots` → `(date, market_price * quantity)` per ogni `AssetHistoryPoint`
- `cash_flows` → transazioni BUY/SELL per quell'asset
- Chiamare `calculate_twrr_series`, `calculate_simple_roi_series`, `calculate_mwrr_series` (quest'ultimo con `asyncio.to_thread`)
- Mappare `twrr`, `roi`, `mwrr` su ogni `AssetHistoryPoint`

> **⚠️ Fuori pista**: `AssetHistoryPoint` memorizza `wac` in base currency e `market_price` in asset native currency (unità miste). Per calcolare ROI corretto servirebbero FX calls per ogni data di prezzo — un call per ogni `PriceHistory` row. La dashboard usa solo `get_history()` (livello portafoglio), non `get_asset_history()`. Deferred a una futura fase dedicata all'asset detail ROI con caching FX.

### 1.4 Rigenerazione Client TypeScript ✅
```bash
./dev.py api sync
```
> **Note implementazione (2026-06-11)**: `./dev.py api sync` eseguito con successo. I campi `twrr/mwrr/roi` su `PortfolioHistoryPoint` confermati in `frontend/src/lib/api/generated.ts`.

### 1.5 Test Rapido
Testare via Swagger UI (`http://localhost:6041/docs`) che:
- `GET /api/v1/portfolio/history` ora ritorna `twrr`, `roi`, `mwrr` diversi da `null` (tranne il primo punto)
- `GET /api/v1/portfolio/asset-history?asset_id=X` idem
- I valori finali di `twrr` e `mwrr` sono coerenti con quelli del `summary`

---

## Step 2: Frontend State Management — `portfolioStore.svelte.ts` ✅

**Target file da creare:** `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`

**Pattern di riferimento:** [brokerStore.ts](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/stores/brokerStore.ts) — usa `$state()` a livello di modulo con funzioni esportate.

> **Note implementazione (2026-06-11)**: Store creato in `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`. Pattern identico a `txStore.svelte.ts` (modulo-level `$state()`). Deduplicazione in-flight requests tramite Map di Promise. Tipi inferiti da Zodios client via `Awaited<ReturnType<...>>`. `invalidate()` hookata in `transactions/+page.svelte` → `reload({soft: true})` e in `CashTransactionModal.svelte` → dopo commit con successo.

> **⚠️ Fuori pista**: `brokerStore.ts` (il pattern di riferimento del piano) in realtà usa `createEntityStore` (pattern diverso, non module-level runes). Il pattern effettivo usato è quello di `txStore.svelte.ts`.

### 2.1 Struttura dello Store
```typescript
// Svelte 5 runes — module-level reactive state

// --- Types ---
type CacheKey = string;  // serialized from broker_ids + date_range

interface PortfolioCache<T> {
  data: T;
  timestamp: number;
}

// --- State ---
let summaryCache = $state<Map<CacheKey, PortfolioCache<PortfolioSummary>>>(new Map());
let historyCache = $state<Map<CacheKey, PortfolioCache<PortfolioHistoryPoint[]>>>(new Map());
let isLoading = $state(false);
let error = $state<string | null>(null);
```

### 2.2 Funzioni Esportate
| Funzione | Scopo |
|----------|-------|
| `fetchSummary(brokerIds?, includeBreakdown?, force?)` | Ritorna summary da cache o API. Chiama `GET /portfolio/summary`. |
| `fetchHistory(brokerIds?, dateFrom?, dateTo?, force?)` | Ritorna history da cache o API. Chiama `GET /portfolio/history`. |
| `invalidate()` | Svuota entrambe le cache. Da chiamare su: CRUD transazioni, import CSV, click `[↻]`. |
| `getIsLoading()` | Getter per lo stato di caricamento (bind UI). |
| `getError()` | Getter per l'errore (bind UI). |

### 2.3 Logica di Cache Key
```typescript
function makeCacheKey(brokerIds?: number[], dateFrom?: string, dateTo?: string): CacheKey {
  const parts = [
    brokerIds ? brokerIds.sort().join(',') : 'all',
    dateFrom ?? '',
    dateTo ?? '',
  ];
  return parts.join('|');
}
```

### 2.4 Integrazione con Invalidazione
Cercare nel codebase i punti dove le transazioni vengono create/modificate/eliminate (nel `TransactionsTable` e nell'import wizard) e aggiungere la chiamata a `invalidate()` dopo ogni operazione riuscita.

---

## Step 3: Dashboard Home — Pagina e Componenti UI

**Target route da creare:** `frontend/src/routes/dashboard/+page.svelte`

Il wireframe di riferimento è in [plan_ui_dashboard.md](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/plan_ui_dashboard.md). Riporto il layout:

```text
+-----------------------------------------------------------------------------------+
| DASHBOARD HOME                                                                    |
| Filtra Broker: [MultiSelectPopover]    [↻ Sincronizza]  [DateRangePicker]         |
|                                                                                   |
| +------------------+  +-------------------+  +------------------+                 |
| | NET WORTH        |  | GAIN/LOSS         |  | ROI PESATO       |                 |
| | EUR 124.500      |  | +14.250 (+12,9%)  |  | TWRR: 12,1%      |                 |
| |                  |  |                   |  | MWRR: 11,2%      |                 |
| +------------------+  +-------------------+  +------------------+                 |
|                                                                                   |
| +----------------------------------+  +---------------------------+               |
| | GROWTH CHART      [EUR | %]     |  | ALLOCAZIONE               |               |
| | 3 linee EUR: Cash/Invest/NAV    |  | [Tipo] [Settore] [Geogr.] |               |
| | 3 linee %: ROI/TWRR/MWRR       |  | Donut + Mappa Mondo       |               |
| +----------------------------------+  +---------------------------+               |
|                                                                                   |
| +-------------------------------------------------------------------------+       |
| | ULTIME TRANSAZIONI                                        [Vedi Tutte →]|       |
| | <TransactionsTable compact limit=10 showFilters=false />                |       |
| +-------------------------------------------------------------------------+       |
+-----------------------------------------------------------------------------------+
```

### 3.1 Aggiornare il Routing e la Navigazione ✅ (già presente)

1. **Creare la route** `frontend/src/routes/dashboard/+page.svelte` ← era già presente come placeholder
2. **Aggiungere il link nella sidebar** ← già presente con icona `LayoutDashboard`
3. **Redirect dalla Home** ← già presente in `+page.svelte` via `goto('/dashboard')`

> **Note implementazione (2026-06-11)**: Tutti e tre i punti erano già implementati dalla Milestone 1. La route esisteva come placeholder con Quick Stats hardcoded. La sidebar aveva già `/dashboard`. La root page già faceva redirect. Nessuna modifica necessaria al routing.

### 3.2 Header Dashboard — Filtri e Controlli ✅

| Componente | Dettaglio |
|------------|-----------|
| **Filtro Broker** | Usare [MultiSelectPopover](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/MultiSelectPopover.svelte). Popolare `items` con la lista broker da [brokerStore](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/stores/brokerStore.ts). Al cambiamento → ri-fetch via `portfolioStore.fetchSummary(selectedIds)` e `fetchHistory(selectedIds, ...)`. |
| **Pulsante Sincronizza [↻]** | Bottone con icona `RefreshCw` da `lucide-svelte`. `onclick` → `portfolioStore.invalidate()` + ri-fetch forzato (`force=true`). |
| **DateRangePicker** | Usare [DateRangePicker](file:///Users/ea_enel/Documents/00_My/LibreFolio/frontend/src/lib/components/DateRangePicker.svelte). `onchange` → ri-fetch `fetchHistory(brokerIds, from, to)`. |

> **⚠️ Fuori pista**: `MultiSelectPopover` non esiste nel codebase. Implementato inline usando `BaseDropdown` (snippet-based) con checkbox list dei broker. Stessa UX, nessun nuovo componente necessario.

### 3.3 KPI Cards ✅

Creato `frontend/src/lib/components/dashboard/KpiCard.svelte`:

| Prop | Tipo | Esempio |
|------|------|---------|
| `label` | `string` | `"Net Worth Complessivo"` |
| `value` | `string` | `"EUR 124.500,00"` |
| `subLabel?` | `string` | `"TWRR: 12,1% | MWRR: 11,2%"` |
| `changeValue?` | `string` | `"+14.250,32"` |
| `changePercent?` | `number` | `12.9` |
| `positive?` | `boolean` | Per colorazione gain (success) vs loss (danger) |

> **Note implementazione (2026-06-11)**: `--color-success`/`--color-danger` non esistono in `app.css`. Usati `text-green-600/text-red-600` (pattern esistente in tutti i componenti). Accent bar in cima alla card per segnalare positivo/negativo.

Tre KPI cards nella riga superiore alimentate da `portfolioStore.fetchSummary()`:
1. **Net Worth** → `summary.net_worth`, sotto-dettaglio `summary.cash_total`
2. **Gain/Loss** → `summary.total_gain_loss` e `summary.total_gain_loss_percent`
3. **ROI Pesato** → `summary.simple_roi_percent` (primario) + subLabel con TWRR/MWRR

### 3.4 Grafico di Crescita — GrowthChart ✅

Creato `frontend/src/lib/components/dashboard/GrowthChart.svelte`.

> **⚠️ Fuori pista**: Il piano diceva "usa LineChart esistente". LineChart è single-series (una sola `data: LineDataPoint[]`). GrowthChart usa **ECharts direttamente** per 3 serie contemporanee. MutationObserver per dark mode, ResizeObserver per resize.

| Stato | Serie | Sorgente dati |
|-------|-------|---------------|
| **EUR** (default) | NAV (solid), Invested (dashed), Cash (dotted) | `history[].nav_value`, `.invested_value`, `.cash_value` |
| **%** | MWRR (solid), TWRR (dashed), ROI (dotted) | `history[].mwrr`, `.twrr`, `.roi` |

Il toggle `[EUR | %]` disabilita la vista `%` se nessun dato ROI è disponibile.

### 3.5 Grafici di Allocazione ✅

Pannello destro con **3 sotto-tab** gestiti con variabile `$state` locale.

| Sotto-tab | Componente | Dati |
|-----------|-----------|------|
| **Tipo Asset** | `SectorPieChart` | `summary.allocation_by_type` |
| **Settore** | `SectorPieChart` | `summary.allocation_by_sector` |
| **Geografica** | `GeographyMap` | `summary.allocation_by_geography` |

> **⚠️ Fuori pista**: `SemiDonutChart` è per ownership sharing (ha `OwnerSlice[]` con avatar), non adatto per allocation. Usato `SectorPieChart` per entrambi Tipo e Settore. Transform dati: `AllocationItem[] → Record<string, number>` dove `value / 100`.

### 3.6 Ultime Transazioni ✅

Creato `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`.

> **⚠️ Fuori pista**: `TransactionsTable` non ha prop `compact/limit/showFilters` — richiede raw `mainRows/partnerRows` e gestione CRUD completa. Creato `RecentTransactionsPanel.svelte`: fetch diretto delle ultime N transazioni via `zodiosApi.query_transactions_api_v1_transactions_get({limit: N*3})`, sort per data desc, rimozione partner rows, display semplificato (date/type/asset/broker/amount). Link "Vedi tutte →" a `/transactions`.

### 3.7 Layout Responsivo ✅

Struttura Tailwind CSS a griglia:
```
- Header: flex-wrap gap-4 (filtri + sync + date picker)
- KPI row: grid grid-cols-1 md:grid-cols-3 gap-4
- Charts row: grid grid-cols-1 lg:grid-cols-5 gap-4
  - Growth chart: col-span-3
  - Allocation: col-span-2
- Transactions: full width
```

---

## Step 4: Verifica Finale e Debugging

**Target:** Manual testing + debug

### Criterio di Verifica Utente (da [implementation_roadmap.md L48-49](file:///Users/ea_enel/Documents/00_My/LibreFolio/LibreFolio_developer_journal/RoadmapV4_UI/phase-09-subplan/implementation_roadmap.md)):
> *«L'utente apre l'app sulla Dashboard, interagisce con il selettore date e i filtri broker, e vede tutti i grafici (Mappa inclusa) aggiornarsi fluidamente con i dati corretti. I KPI totali combaciano con le aspettative.»*

### Checklist di Verifica — Stato Implementazione

1. ✅ **API Backend**: `GET /portfolio/history` ora popola `twrr`, `roi`, `mwrr` su ogni punto (tranne il primo)
2. ⬜ **API Backend**: Verificare manualmente via Swagger UI che i valori finali sono coerenti con `summary`
3. ✅ **Navigazione**: Sidebar con link "Dashboard", home redirige a `/dashboard`
4. ✅ **KPI Cards**: Implementate (Net Worth, Gain/Loss, ROI) alimentate da `portfolioStore.fetchSummary()`
5. ✅ **Toggle Growth `[EUR | %]`**: Implementato in `GrowthChart.svelte`
6. ✅ **Filtro Broker**: `BaseDropdown` con checkboxes broker, trigger `loadAll()` al cambio
7. ✅ **DateRangePicker**: Collegato a `loadHistory()` via `onchange`
8. ✅ **Allocazione 3 tab**: `SectorPieChart` (Tipo+Settore), `GeographyMap` (Geografica)
9. ✅ **GeographyMap**: Componente esistente già gestisce "Unknown"
10. ✅ **Ultime Transazioni**: `RecentTransactionsPanel.svelte` (last-10, read-only)
11. ✅ **Caching Store**: `portfolioStore` con Map-based cache, deduplication in-flight
12. ✅ **Invalidazione**: `[↻ Sincronizza]` chiama `invalidate()` + `loadAll(force=true)`
13. ⬜ **Dark mode**: Verificare manualmente in browser
14. ✅ **Responsività**: Grid `grid-cols-1 md:grid-cols-3` per KPI, `lg:grid-cols-5` per charts

---

## Riepilogo File Creati / Modificati

### Creati (nuovo)
| File | Tipo |
|------|------|
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Store caching portafoglio (Svelte 5 runes) |
| `frontend/src/lib/components/dashboard/KpiCard.svelte` | Componente KPI card |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | Multi-serie ECharts con toggle EUR/% |
| `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte` | Panel ultime transazioni |

### Modificati
| File | Modifica |
|------|----------|
| `backend/app/services/portfolio_service.py` | `get_history()` → popola `twrr`, `mwrr`, `roi`; import `calculate_simple_roi_series` |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Sostituito placeholder con dashboard reale |
| `frontend/src/routes/(app)/transactions/+page.svelte` | `invalidate()` hookata in `reload({soft: true})` |
| `frontend/src/lib/components/brokers/CashTransactionModal.svelte` | `invalidate()` dopo commit |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Nuove chiavi `dashboard.*` |

### Rigenerati
| File | Comando |
|------|---------|
| `frontend/src/lib/api/generated.ts` | `./dev.py api sync` |
