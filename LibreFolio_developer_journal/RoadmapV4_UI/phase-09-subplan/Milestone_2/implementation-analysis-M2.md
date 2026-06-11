# Implementation Analysis: Phase 09 Step 2 — Dashboard Home & Backend ROI Series Patch

> **Tipo documento**: Piano implementativo interno generato dall'agente prima dell'esecuzione.
> **Sessione**: 2026-06-11 — Copilot CLI session `c0f2e647`
> **Piano sorgente**: [`plan-phase09Step2-DashboardAndPatch.prompt.md`](./plan-phase09Step2-DashboardAndPatch.prompt.md)
> **Stato**: ✅ Implementato (Step 1.3 deferred)

---

## Analisi Stato Codebase (pre-implementazione)

### Già presente (nessun lavoro necessario):
- `PortfolioHistoryPoint` + `AssetHistoryPoint` hanno già i campi `twrr/mwrr/roi` Optional ✅
- `calculate_twrr_series` + `calculate_mwrr_series` già importati in `portfolio_service.py` ✅
- Sidebar già ha link `/dashboard` con icona `LayoutDashboard` ✅
- Root `+page.svelte` già redirige gli utenti autenticati a `/dashboard` ✅
- `(app)/dashboard/+page.svelte` già esiste (placeholder con `€ --,---.--` hardcoded) ✅

### Gap da colmare:
- `calculate_simple_roi_series` NON importato in `portfolio_service.py`
- `get_history()` non popola `twrr/mwrr/roi` sui punti history
- `get_asset_history()` stesso gap
- `portfolioStore.svelte.ts` inesistente
- `KpiCard.svelte` inesistente
- `GrowthChart.svelte` inesistente
- `RecentTransactionsPanel.svelte` inesistente (`TransactionsTable` non ha prop `compact/limit`)
- Dashboard `+page.svelte` è un placeholder

---

## Scoperte Architetturali Chiave

### 1. `SemiDonutChart` non adatto per allocation
`SemiDonutChart` (ownership sharing modal) usa `OwnerSlice[]` con avatar — non compatibile con `AllocationItem[]`.
**Soluzione**: usare `SectorPieChart` per sia Tipo Asset che Settore.
**Transform**: `AllocationItem[] → Record<string, number>` dove `value / 100`.

### 2. `LineChart` è single-series
`LineChart.svelte` accetta solo `data: LineDataPoint[]` (una serie).
**Soluzione**: `GrowthChart.svelte` usa ECharts direttamente (3 serie contemporanee).

### 3. `TransactionsTable` non ha props compact/limit
La componente richiede `mainRows/partnerRows` raw + gestione CRUD completa.
**Soluzione**: creare `RecentTransactionsPanel.svelte` — fetch diretto last-N TX, tabella read-only semplificata.

### 4. `MultiSelectPopover` non esiste nel codebase
Il piano lo riferenziava ma il componente non è mai stato creato.
**Soluzione**: inline con `BaseDropdown` (snippet-based, già esistente) + checkbox list broker.

### 5. `brokerStore.ts` usa `createEntityStore`, non module-level runes
Il piano lo indicava come template per `portfolioStore`. In realtà il pattern corretto è `txStore.svelte.ts` (module-level `$state()`).

### 6. `twrr_percent`/`mwrr_percent` in `PortfolioSummary` hanno tipo unione
Nel client Zodios generato: `string | (string | null)[] | null | undefined` — legacy dal codegen.
**Soluzione**: helper `safeStr()` per estrarre il valore scalare.

### 7. ROI `get_asset_history()` — problema unità miste (DEFERRED)
`AssetHistoryPoint` memorizza `wac` in base currency e `market_price` in asset currency — unità miste.
Richiederebbe FX call per ogni data di prezzo (costoso). La dashboard usa solo `get_history()` (portfolio-level).
**Decisione**: deferred a futura fase dedicata.

---

## Piano di Implementazione Eseguito

### STEP 1 — Backend: Popolare Serie ROI in `portfolio_service.py`

#### 1.1 — Import mancante ✅
```python
from backend.app.utils.financial.roi_utils import (
    CashFlowInput,
    NAVSnapshot,
    calculate_mwrr,
    calculate_mwrr_series,
    calculate_simple_roi,
    calculate_simple_roi_series,   # ← AGGIUNTO
    calculate_twrr,
    calculate_twrr_series,
)
```

#### 1.2 — Modifica `get_history()` ✅
Dopo `_build_history_series(rows)`:
1. `nav_snapshots` dai `PortfolioHistoryPoint` già calcolati
2. `cash_flows` dai `rows` già in memoria (DEPOSIT → negativo, WITHDRAWAL → positivo)
   — nessuna query extra necessaria
3. Chiamate:
   ```python
   twrr_series = calculate_twrr_series(nav_snapshots, cash_flows)
   roi_series = calculate_simple_roi_series(nav_snapshots, cash_flows)
   mwrr_series = await asyncio.to_thread(calculate_mwrr_series, nav_snapshots, cash_flows)
   ```
4. Mappatura con `{date → value}` su ogni `PortfolioHistoryPoint`

#### 1.3 — Modifica `get_asset_history()` — ⚠️ DEFERRED
Problema unità miste (vedi Scoperte #7 sopra).

#### 1.4 — Rigenerazione client TS ✅
```bash
./dev.py api sync
```

---

### STEP 2 — Store: `portfolioStore.svelte.ts` ✅

**File**: `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`

```typescript
// Svelte 5 module-level $state()
type CacheKey = string;
interface CacheEntry<T> { data: T; timestamp: number; }

let summaryCache = $state(new Map<CacheKey, CacheEntry<PortfolioSummary>>());
let historyCache = $state(new Map<CacheKey, CacheEntry<PortfolioHistoryPoint[]>>());
```

| Funzione | Comportamento |
|----------|--------------|
| `fetchSummary(brokerIds?, includeBreakdown?, force?)` | GET /portfolio/summary, cache per key |
| `fetchHistory(brokerIds?, dateFrom?, dateTo?, force?)` | GET /portfolio/history, cache per key |
| `invalidate()` | Svuota entrambe le cache |
| `portfolioIsLoading()` | Getter stato caricamento |
| `portfolioError()` | Getter errore |

**Cache key**: `broker_ids.sort().join(',') + '|' + dateFrom + '|' + dateTo`
**Deduplication**: Map di Promise in-flight per chiave

**Hookup invalidazione**:
- `transactions/+page.svelte` → `reload({soft: true})` chiama `invalidate()` prima
- `CashTransactionModal.svelte` → `invalidate()` dopo commit con successo

---

### STEP 3 — Componenti Dashboard ✅

#### `KpiCard.svelte`
**File**: `frontend/src/lib/components/dashboard/KpiCard.svelte`

```typescript
interface Props {
    label: string;
    value: string;
    subLabel?: string;
    changeValue?: string;
    changePercent?: number;
    positive?: boolean;
    loading?: boolean;
}
```
- Accent bar colorata (verde/rosso) in cima alla card
- Skeleton con `animate-pulse` durante loading
- `text-green-600`/`text-red-600` per gain/loss (non `--color-success` — non esiste in `app.css`)

#### `GrowthChart.svelte`
**File**: `frontend/src/lib/components/dashboard/GrowthChart.svelte`

```typescript
interface Props {
    history: PortfolioHistoryPoint[];
    height?: string;
    loading?: boolean;
    baseCurrency?: string;
}
```
- ECharts diretto (non LineChart — single-series)
- Toggle `[EUR | %]` — vista % disabilitata se nessun dato ROI disponibile
- EUR: NAV (solid), Invested (dashed), Cash (dotted)
- %: MWRR (solid), TWRR (dashed), ROI (dotted)
- MutationObserver per dark mode, ResizeObserver per resize
- DataZoom via slider + mouse wheel

#### `RecentTransactionsPanel.svelte`
**File**: `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte`

```typescript
interface Props {
    limit?: number;      // default 10
    brokerIds?: number[];
}
```
- Fetch `zodiosApi.query_transactions_api_v1_transactions_get({limit: limit*3})`
- Sort per data desc, remove partner rows, slice(0, limit)
- Tipo API inferito da `Awaited<ReturnType<...>>` (non TXReadItem component — tipo incompatibile)
- Colonne: Data, Tipo (icon), Asset (`display_name`), Broker, Importo
- Link "Vedi tutte →" a `/transactions`

#### Allocation Panel (inline in `+page.svelte`)
- Tab `type | sector | geo` con `$state`
- `SectorPieChart` per Tipo e Settore
- `GeographyMap` per Geografica
- Transform: `AllocationItem[] → Record<string, number>` (value/100)

---

### STEP 4 — Dashboard Page ✅

**File**: `frontend/src/routes/(app)/dashboard/+page.svelte` (sostituito placeholder)

```
+----------------------------------------------------------+
| [BaseDropdown broker filter] [↻ Sync] [DateRangePicker] |
+----------------------------------------------------------+
| [KpiCard: Net Worth] [KpiCard: Gain/Loss] [KpiCard: ROI] |
+----------------------------------------------------------+
| [GrowthChart (col-span-3)] | [Allocation Panel (col-span-2)] |
|   toggle EUR/%              |   tabs: Tipo | Settore | Geo   |
+----------------------------------------------------------+
| [RecentTransactionsPanel]                                |
+----------------------------------------------------------+
```

Griglia Tailwind:
- Header: `flex flex-wrap gap-3`
- KPI: `grid grid-cols-1 md:grid-cols-3 gap-4`
- Charts: `grid grid-cols-1 lg:grid-cols-5 gap-4`

---

### STEP 5 — i18n ✅

28 nuove chiavi `dashboard.*` aggiunte a EN/IT/FR/ES:
`netWorth`, `gainLoss`, `roiWeighted`, `growth`, `allocation`, `recentTransactions`,
`allBrokers`, `syncData`, `seeAll`, `typeAllocation`, `sectorAllocation`, `geoAllocation`,
`filterBrokers`, `eur`, `pct`, `noData`, `cashValue`, `investedCapital`, `navValue`,
`mwrr`, `twrr`, `simpleRoi`, `twrrMwrr`, `manageBrokers`, `manageAssets`,
`manageTransactions`, `manageFx`

---

## File Modificati / Creati

### Creati
| File | Tipo |
|------|------|
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Store cache portafoglio |
| `frontend/src/lib/components/dashboard/KpiCard.svelte` | KPI card |
| `frontend/src/lib/components/dashboard/GrowthChart.svelte` | Growth chart multi-serie |
| `frontend/src/lib/components/dashboard/RecentTransactionsPanel.svelte` | Ultime transazioni |

### Modificati
| File | Modifica |
|------|----------|
| `backend/app/services/portfolio_service.py` | Import + ROI series in `get_history()` |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Placeholder → dashboard reale |
| `frontend/src/routes/(app)/transactions/+page.svelte` | Hook `invalidate()` in `reload({soft: true})` |
| `frontend/src/lib/components/brokers/CashTransactionModal.svelte` | Hook `invalidate()` dopo commit |
| `frontend/src/lib/i18n/en.json` | 28 nuove chiavi dashboard |
| `frontend/src/lib/i18n/it.json` | 28 nuove chiavi dashboard |
| `frontend/src/lib/i18n/fr.json` | 28 nuove chiavi dashboard |
| `frontend/src/lib/i18n/es.json` | 28 nuove chiavi dashboard |

### Rigenerati
| File | Comando |
|------|---------|
| `frontend/src/lib/api/generated.ts` | `./dev.py api sync` |

---

## Verifica Qualità

- ✅ `python -c "from backend.app.services.portfolio_service import PortfolioService"` — OK
- ✅ `python -m black --check backend/app/services/portfolio_service.py` → reformatted
- ✅ `./dev.py front check` → **0 errors, 0 warnings**
- ✅ `cd frontend && npx prettier --check` → tutti i nuovi file passano

## Checklist Manuale (da verificare in browser)

1. ⬜ `GET /portfolio/history` → `twrr/roi/mwrr` non-null (tranne primo punto)
2. ⬜ Valori finali `twrr`/`mwrr` coerenti con `summary`
3. ✅ Navigazione: sidebar link + redirect `/` → `/dashboard`
4. ⬜ KPI cards mostrano valori corretti
5. ⬜ Toggle Growth `[EUR | %]` fluido
6. ⬜ Filtro broker aggiorna tutti i dati
7. ⬜ DateRangePicker aggiorna grafico e KPI
8. ⬜ Allocazione 3 tab corretta
9. ⬜ GeographyMap + "Unknown" gestito
10. ⬜ Ultime 10 transazioni in modalità compatta
11. ⬜ Cache: no chiamate ridondanti alla ri-navigazione
12. ⬜ Sync `[↻]` invalida + re-fetch
13. ⬜ Dark mode tutti i componenti
14. ⬜ Responsività < 768px
