# Deep Analysis — Portfolio History Chart: Bugs & Architecture

**Context project:** LibreFolio — self-hosted portfolio tracker (FastAPI + SvelteKit 5 + ECharts 6)
**Goal of this prompt:** Analisi approfondita di 4 problemi aperti nel grafico NAV del dashboard.
Produci: diagnosi precisa per ciascun bug + proposte risolutive concrete con pseudocodice/snippet.

---

## Stack tecnico rilevante

| Layer | Tech |
|-------|------|
| Backend | Python 3.13 + FastAPI + SQLModel/SQLite |
| Frontend | SvelteKit 2 + Svelte 5 Runes + ECharts 6 |
| API client | Zodios v10 (`@zodios/core ^10.9.6`) + openapi-zod-client |

---

## Stato attuale (cosa funziona già)

Il network tab del browser mostra richieste corrette:
```
history?date_from=2025-12-11&date_to=2026-06-11    200 xhr   4.0 kB
history?date_from=2026-03-11&date_to=2026-06-11    200 xhr   4.0 kB
history?date_from=2026-01-01&date_to=2026-06-11    200 xhr   4.0 kB
history?date_from=2025-06-11&date_to=2026-06-11    200 xhr   5.0 kB
summary?target_currency=EUR                         200 xhr   5.3 kB
history?date_from=2025-06-11&date_to=2026-06-11&target_currency=EUR   200 xhr  5.0 kB
summary?target_currency=USD                         200 xhr   4.9 kB
history?date_from=2025-06-11&date_to=2026-06-11&target_currency=USD   200 xhr  4.8 kB
```

→ Zodios invia correttamente tutti i query param (date_from, date_to, target_currency).
→ Il backend risponde con dati diversi per USD vs EUR (diversa size).
→ Il backend risponde con dati di dimensione diversa per range temporali diversi (4.0 kB vs 5.0 kB).

---

## Bug 1 — Il grafico ignora il date range: mostra sempre da 2025-09-30

### Sintomo
Qualunque range si scelga nel DateRangePicker (3M, 6M, 1Y), il grafico NAV mostra sempre
dati a partire dal 2025-09-30 (data del primo deposito nel DB di test).

### Codice rilevante — Frontend

**`frontend/src/lib/components/dashboard/GrowthChart.svelte`** (estratto):
```typescript
// Props ricevute dal parent
let {history = [], height = '360px', loading = false, baseCurrency = 'EUR'}: Props = $props();

// Derived: date per l'asse X
const dates = $derived(history.map((pt) => pt.date));

// Effect: ri-renderizza quando history o viewMode cambiano
$effect(() => {
    void history;   // ← traccia history come dipendenza
    void viewMode;
    if (chartContainer) {
        tick().then(() => {
            setupResizeObserver();
            renderChart();
        });
    }
});

function renderChart() {
    // ... costruisce option con xAxis.data = activeDates (= dates)
    chartInstance.setOption(option, {notMerge: true});  // notMerge: true già presente!
}
```

**`frontend/src/routes/(app)/dashboard/+page.svelte`** (estratto):
```typescript
let history = $state<PortfolioHistoryPoint[]>([]);
let dateFrom = $state(getStart());  // es. "2026-03-11" (default 3M)
let dateTo = $state(getEnd());      // es. "2026-06-11"

async function loadHistory(force = false) {
    historyLoading = true;
    try {
        history = await fetchHistory(
            activeBrokerIds,
            dateFrom || undefined,
            dateTo || undefined,
            targetCurrency || undefined,
            force
        );
    } finally {
        historyLoading = false;
    }
}

function handleDateChange(from: string, to: string) {
    dateFrom = from;
    dateTo = to;
    setDateRange(from, to);
    void loadHistory();   // ← non awaited
}

// In template:
// <GrowthChart {history} loading={historyLoading} {baseCurrency} />
```

**`frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`** (estratto):
```typescript
let historyCache = $state(new Map<CacheKey, CacheEntry<PortfolioHistoryPoint[]>>());

function makeCacheKey(brokerIds?, dateFrom?, dateTo?, targetCurrency?): CacheKey {
    return [brokerIds?.sort().join(',') ?? 'all', dateFrom ?? '', dateTo ?? '', targetCurrency ?? ''].join('|');
}

export async function fetchHistory(brokerIds?, dateFrom?, dateTo?, targetCurrency?, force = false) {
    const key = makeCacheKey(brokerIds, dateFrom, dateTo, targetCurrency);

    if (!force) {
        const cached = historyCache.get(key);
        if (cached) return cached.data;
    }
    // ... fa la richiesta con { queries: { broker_ids, date_from, date_to, target_currency } }
    const data = await zodiosApi.get_portfolio_history_api_v1_portfolio_history_get({ queries });
    historyCache = new Map(historyCache).set(key, {data, timestamp: Date.now()});
    return data;
}
```

### Codice rilevante — Backend

**`backend/app/services/portfolio_service.py`** — `get_history()`:
```python
async def get_history(
    self,
    user_id: int,
    broker_ids: list[int] | None = None,
    date_from: date_type | None = None,   # ← Python date object, FastAPI parses from "2026-03-11"
    date_to: date_type | None = None,
    target_currency_override: str | None = None,
) -> list[PortfolioHistoryPoint]:
    # ... accumula transazioni da t=0 (ignora date_from per correttezza NAV)
    all_history = _build_history_series(rows)  # points only at transaction dates!
    
    # Mark-to-market patch su all_history
    # ...
    
    # Slice finale
    if date_from:
        history = [pt for pt in all_history if pt.date >= date_from]
    else:
        history = all_history
    
    # ROI re-basing + TWRR/MWRR mapping su history (sliced)
    # ...
    return history
```

### Domande per l'analisi

1. Con `notMerge: true` in `setOption`, perché il grafico mostrerebbe dati storici di `all_history`
   invece del `history` sliced? ECharts sostituisce completamente il chart ad ogni renderChart().

2. In Svelte 5 con Runes, quando il parent assegna `history = await fetchHistory(...)`,
   il `$effect` nel child che legge `void history` (prop) — si ri-esegue correttamente?
   Esiste un problema noto con `$props()` in Svelte 5 e tracking degli array re-assegnati?

3. C'è un race condition tra `loadHistory()` non-awaited e l'aggiornamento dello `$state`?

4. Il backend torna DAVVERO solo i punti da `date_from` in poi? Verifica controllando
   l'array JSON nel response (primo elemento `date` deve essere >= date_from).

5. La cache del portfolioStore potrebbe restituire dati di un range precedente con una chiave
   diversa ma data simile? (Controllo logica `makeCacheKey`)

---

## Bug 2 — Cambiare la valuta target non aggiorna visualmente il grafico

### Sintomo
Selezionando "USD" nel CurrencySearchSelect del filter bar, il network tab mostra la richiesta
corretta con `target_currency=USD` e risposta di dimensione diversa (4.8 kB vs 5.0 kB per EUR).
Ma il grafico NAV non cambia visualmente.

### Codice rilevante

**Dashboard `+page.svelte`**:
```typescript
let targetCurrency = $state('');

// In template:
// <CurrencySearchSelect
//     bind:value={targetCurrency}
//     compact={true}
//     includeAll={true}
//     placeholder={baseCurrency}
//     onchange={() => void loadAll()}
// />
```

**`CurrencySearchSelect.svelte`** — interfaccia Props:
```typescript
interface Props {
    value?: string;          // bindable
    includeAll?: boolean;    // aggiunge opzione "All currencies" con value ''
    onchange?: (value: string) => void;
    compact?: boolean;
    // ...
}
let {value = $bindable(''), ..., onchange, ...}: Props = $props();
```

### Domande per l'analisi

1. In Svelte 5, `bind:value={targetCurrency}` + `onchange={() => void loadAll()}`:
   al momento in cui `loadAll()` legge `targetCurrency`, il valore è già aggiornato?
   Oppure l'aggiornamento del `$bindable` avviene in un micro-task successivo?

2. Con `includeAll={true}`, quando si seleziona "All currencies" il value diventa `''`.
   `targetCurrency || undefined = undefined` → backend usa la valuta base dell'utente (EUR).
   Se la valuta base è già EUR, selezionare EUR esplicito e "All" dà la **stessa risposta backend**.
   → Il problema visivo potrebbe essere che si confrontano risposte identiche?

3. Il `$effect` in GrowthChart traccia `void history`. Se `history` viene riassegnato con un nuovo
   array che ha gli stessi valori numerici ma in valuta diversa (es. multipli simili EUR≈USD a breve
   range), i `$derived` (dates, eurSeries) si ricalcolano ma i valori potrebbero essere troppo
   simili da sembrare invariati graficamente.

4. C'è un possibile problema di referential equality in Svelte 5? Se `fetchHistory` restituisce
   lo stesso array (dalla cache) invece di uno nuovo, `$state` potrebbe non notificare il cambiamento?

---

## Bug 3 — I punti del grafico sono sparsi (solo alle date di transazione)

### Sintomo
Il grafico mostra punti solo ogni 2-3 giorni (corrispondenti alle date delle transazioni nel DB).
Tra un acquisto e il successivo, il NAV non si aggiorna per riflettere le variazioni di prezzo
degli asset in portafoglio, anche se PriceHistory ha dati giornalieri.

### Root Cause (accertata)

**`_build_history_series`** crea snapshot SOLO alle date delle transazioni:
```python
def _build_history_series(transactions: list[_HistoryTxRow]) -> list[PortfolioHistoryPoint]:
    daily: dict[date_type, ...] = defaultdict(...)
    for row in sorted(transactions, key=lambda r: r.date):
        daily[row.date]["cash"] = ...  # solo ai giorni con transazioni!
    return [PortfolioHistoryPoint(...) for dt in sorted(daily.keys())]
```

Il mark-to-market patch successivo calcola `nav = cash + market_value` ma solo per quei
stessi giorni. Tra due transazioni consecutive (es. 2026-05-21 → 2026-05-26), il NAV evolve
perché i prezzi cambiano ogni giorno, ma il grafico non cattura quella variazione.

### Impatto

- Grafico "a gradini": salta di giorno in giorno solo quando c'è un trade
- Anomalie nelle metriche TWRR/MWRR: i periodi sub-period sono solo transaction-to-transaction
- Il grafico non rappresenta fedelmente l'andamento del portafoglio

### Architettura attuale

```
Transazioni DB → _build_history_series → snapshot per date-tx → mark-to-market
                                                                  (price_map da PriceHistory)
```

Il `price_map` (bulk SQL su PriceHistory) carica prezzi in tutto il range ma li usa solo
per le date in `all_history` (= transaction dates). I prezzi intermedi vengono caricati
ma non usati per generare nuovi snapshot.

### Proposte di soluzione da esplorare

**Opzione A — Daily expansion nel backend (raccomandato)**
Invece di partire dalle transaction dates, generare una griglia giornaliera:
```python
# Pseudocodice
all_dates = [date_min + timedelta(d) for d in range((date_max - date_min).days + 1)]
for snap_date in all_dates:
    cash = cum_cash_up_to(snap_date, rows)        # forward-fill dalle transazioni
    qtys = cum_qtys_up_to(snap_date, qty_rows)    # forward-fill dalle transazioni
    market_value = sum(qty * price_on_date(asset, snap_date) for asset, qty in qtys.items())
    nav = cash + market_value
    yield PortfolioHistoryPoint(date=snap_date, ...)
```
Pro: dati giornalieri, curve smooth, metriche più accurate
Contro: risposta più grande, più lavoro per range lunghi
Mitigazione: limite configurabile (es. max 730 giorni) + possibile downsampling per range > 2Y

**Opzione B — Frontend linear interpolation**
ECharts può interpolare tra punti sparsi se l'asse X è di tipo `time` invece di `category`.
Ma l'interpolazione lineare è fuorviante: ignora le variazioni di prezzo reali tra tx.

**Opzione C — Hybrid: transaction-dates + PriceHistory dates**
Unire le date delle transazioni con le date della PriceHistory:
```python
price_dates = set of all dates with at least one PriceHistory entry for held assets
all_snapshot_dates = sorted(transaction_dates | price_dates)
```
Pro: cattura i movimenti di prezzo senza inventare date
Contro: gap nei weekend/festivi (molte PH hanno dati solo nei giorni di mercato aperto)

**Domande per l'analisi**

1. Quale opzione bilancia meglio performance vs accuratezza?
2. Va ripensata la struttura dell'endpoint? `GET /portfolio/history?granularity=daily|transaction`?
3. Per range > 1 anno, il downsampling è necessario per mantenere la risposta < 1 MB?
4. Come cambia la logica di TWRR/MWRR con daily snapshots? Migliora o degrada?

---

## Bug 4 — roi (simple_roi) non forzato a 0 al primo punto

### Sintomo
`history[0].twrr` e `history[0].mwrr` vengono forzati a `Decimal("0")` (fix recente).
Ma `history[0].roi` (simple_roi) può ancora essere `None` al primo punto → linea spezzata
nel toggle "%" del grafico.

### Codice rilevante

**`portfolio_service.py`** — fine di `get_history()`:
```python
for pt in history:
    pt.twrr = twrr_map.get(pt.date)
    pt.roi = roi_map.get(pt.date)
    pt.mwrr = mwrr_map.get(pt.date)

if history:
    if history[0].twrr is None:
        history[0].twrr = Decimal("0")
    if history[0].mwrr is None:
        history[0].mwrr = Decimal("0")
    # ← history[0].roi NON è forzato a 0!
```

**GrowthChart.svelte** — pctSeries:
```typescript
const pctSeries = $derived([
    { name: 'MWRR',   data: history.map((pt) => (pt.mwrr != null ? Number(pt.mwrr) * 100 : null)) },
    { name: 'TWRR',   data: history.map((pt) => (pt.twrr != null ? Number(pt.twrr) * 100 : null)) },
    { name: 'Simple ROI', data: history.map((pt) => (pt.roi != null ? Number(pt.roi) * 100 : null)) },
]);
```

Con `connectNulls: false` in ECharts, un valore `null` spezza la linea ROI al primo punto.

### Fix atteso (triviale)
```python
if history:
    if history[0].twrr is None: history[0].twrr = Decimal("0")
    if history[0].mwrr is None: history[0].mwrr = Decimal("0")
    if history[0].roi  is None: history[0].roi  = Decimal("0")   # ← manca questo
```

---

## Riflessioni architetturali aggiuntive

### A — GET vs POST per `/portfolio/history`

Attualmente: `GET /api/v1/portfolio/history?broker_ids=1&broker_ids=2&date_from=...&date_to=...&target_currency=...`

Il GET è semanticamente corretto (operazione di lettura idempotente). Diventare POST ha senso solo se:
- Si devono inviare parametri complessi non serializzabili come query string (es. filtri annidati)
- La URL supera i 2KB (limite dei browser)

Per il caso attuale il GET è appropriato. L'unico scenario che potrebbe giustificare POST è
se in futuro si aggiungessero filtri per asset_type, sector, ecc.

**Domanda**: Prevedete filtri complessi nel medio termine? In caso negativo, mantenere GET.

### B — Endpoint separato vs parametro `granularity`

Due opzioni:
1. `GET /portfolio/history?granularity=daily|sparse` — stesso endpoint, parametro opzionale
2. `GET /portfolio/history/daily` + `GET /portfolio/history/sparse` — due endpoint distinti

Raccomandazione: opzione 1 con default `daily` una volta implementato. Mantieni
`sparse` per backward compatibility o per debug.

### C — Performance del daily expansion

Per 1 anno di storia (365 gg) con 10 asset e FX → circa 3650 price lookups.
Con `_bulk_load_asset_prices` già ottimizzato (1 SQL query, dict in memory), il
bottleneck è probabilmente il `convert_bulk` FX. Valutare se pre-caricare tutti i
tassi di cambio del periodo in una sola query invece di usare `convert_bulk` per ogni giorno.

---

## Files rilevanti (percorsi assoluti nel repo)

```
backend/app/services/portfolio_service.py      # get_history(), _build_history_series(), _bulk_load_asset_prices()
backend/app/api/v1/analytics.py                # endpoint GET /portfolio/history + GET /portfolio/summary
backend/app/utils/financial/roi_utils.py        # calculate_mwrr, calculate_mwrr_series, calculate_twrr_series
frontend/src/lib/components/dashboard/GrowthChart.svelte      # ECharts rendering, $effect, renderChart()
frontend/src/routes/(app)/dashboard/+page.svelte               # state, loaders, handleDateChange
frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts     # fetchHistory, fetchSummary, cache
frontend/src/lib/api/generated.ts              # Zodios client generato da OpenAPI (già aggiornato)
frontend/src/lib/components/ui/select/CurrencySearchSelect.svelte
```

---

## Output atteso dall'analisi

Per ciascuno dei 4 bug:
1. **Diagnosi definitiva**: qual è esattamente la causa (con riga di codice se possibile)
2. **Fix minimale**: snippet pronto da applicare (cambiare il meno possibile)
3. **Fix ideale**: se il fix minimale non basta, proposta di refactor con pseudocodice
4. **Test di verifica**: come verificare che il fix funziona (curl, log, assertion)

Per il Bug 3 (architettura sparsa):
5. **Proposta di refactor backend** completa di signature aggiornata, logica di generazione
   daily snapshots, e considerazioni su performance/caching

Per tutti:
6. **Dipendenze tra fix**: ordinare i fix per poterli applicare in sequenza sicura
