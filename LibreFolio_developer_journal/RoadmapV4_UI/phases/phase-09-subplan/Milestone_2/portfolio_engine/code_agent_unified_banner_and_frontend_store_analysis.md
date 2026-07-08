# Unified Banner & Frontend Store Analysis

**Data:** 2026-06-20  
**Autore:** Claude Sonnet 4.6  
**Riferimento:** asset/[id], fx/[pair], dashboard/+page.svelte, portfolioStore, TimeSeriesStore, fxStoreRegistry, assetPriceStoreRegistry

---

## 1. Analisi banner/alert esistenti

### 1.1 Asset Detail — `frontend/src/routes/(app)/assets/[id]/+page.svelte`

**Componenti riusabili già esistenti:**
- Nessun componente banner estratto — tutto inline nel page file

**Store usati:**
- `assetPriceStoreRegistry` (TimeSeriesStore per prezzi)  
- `fxStoreRegistry` (TimeSeriesStore per FX)
- `currencyGraphStore` (per verificare coppie configurate)
- `chartSettingsStore` (segnali attivi)

**API/backend response:**
- `GET /assets/{id}/info` → `FAinfoResponse` (`.active`, `.currency`, `.display_name`)
- `POST /assets/prices/query` → `AssetPricePoint[]` (`.backward_fill_info.days_back`)
- `POST /assets/prices` (per sync)

**Severità visive:**
| Stato | Classe background | Classe testo | Simbolo |
|-------|------------------|-------------|---------|
| error/warning | `bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800` | `text-amber-700 dark:text-amber-400` | ⚠️ 📦 |
| info/data | `bg-sky-50 dark:bg-sky-900/20 border-sky-200 dark:border-sky-800` | `text-sky-700 dark:text-sky-400` | 📊 |

**Struttura HTML ricorrente:**
```html
<div class="bg-{COLOR}-50 ... rounded-xl p-4 text-sm ... flex items-center gap-2">
  <span>{emoji}</span>
  <span>{message}</span>
  <button class="ml-auto ...">CTA</button>  <!-- opzionale -->
</div>
```

**CTA presenti:**
- `[×] close` → `error = null` (dismiss)
- `[Add FX pair]` → apre `FxPairAddModal` con `fxPairCreateSlug`
- `[↻ Sync]` → `handleSyncPair(slug)`
- `[→ FX pair detail]` → `<a href="/fx/{slug}?start=...&end=...">`

**Banner tipologia FX (il più elaborato):**
```svelte
{#each requiredFxPairs.filter(p => p.status !== 'ok') as pair}
  <!-- isAmber = missing | no-data | partial-gap (amber) vs sky (partial-gap via info) -->
  <!-- CTA inline: Add FX pair (modal) | Sync | Navigate -->
{/each}
```
Status calcolato client-side in `requiredFxPairs` derived. Include:
- Coppia main asset
- Coppie segnali comparison
- Coppie valute eventi (dividendi in altra valuta)

**Logica dismiss:** solo banner `error` è dismissibile (close button).  
**Logica accordion/details:** nessuna — ogni banner è flat.  
**i18n:** `$t('assetDetail.fxPairMissing', {values: {base, quote}})` — `svelte-i18n` con parametri.

**Cosa funziona bene:**
- Banner FX con CTA contestuale (modal/sync/navigate) per ogni coppia problematica
- Distinzione amber vs sky semanticamente corretta
- Parametrizzazione i18n per nomi dinamici

**Cosa è duplicato:**
- La struttura HTML amber/sky è ripetuta 4+ volte nel file
- Stesso pattern esiste identico in FX detail

**Cosa è specifico del dominio:**
- `RequiredFxPairInfo` con icon asset, tipi — specifico asset
- Stato `partial-gap` con `firstDate` — specifico timeseries

---

### 1.2 FX Detail — `frontend/src/routes/(app)/fx/[pair]/+page.svelte`

**Store usati:**
- `fxStoreRegistry` (TimeSeriesStore per FX, condiviso con asset detail)

**API/backend:**
- `POST /fx/currencies/convert` → `FxDataPoint[]` con `backwardFillInfo.daysBack`
- `staleDays = max(days_back, fx_days_back)` → derivato client-side

**Severità visive:** identiche ad asset detail (amber / sky).

**Banner presenti:**
| Banner | Trigger | Severity | CTA |
|--------|---------|----------|-----|
| Error generico | `error` string | amber | [×] close |
| Range before data | `rangeStartsBeforeData` | sky (info) | nessuna |
| No data (inline chart) | `chartData.length === 0` | inline chart area | [Insert manually] / inline message |
| Stale gradient | `staleDays > 0` | Visivo sul chart (non banner) | nessuna |

**Nota:** non c'è un banner dedicato per "stale" — viene usato il gradiente visivo nel chart. Solo `LineChart.svelte` gestisce `staleDays` sulla serie.

**Logica accordion:** nessuna.

---

### 1.3 Dashboard Portfolio — `frontend/src/routes/(app)/dashboard/+page.svelte`

**Store usati:** `portfolioStore.svelte.ts` (cache key-based)

**API/backend:**
- `POST /portfolio/summary` → `PortfolioSummary` (`.missing_price_assets[]`, `.missing_fx_pairs[]`, `.data_quality`)

**Banner presenti:**
| Banner | Campo backend | Severity | CTA |
|--------|--------------|----------|-----|
| Missing prices | `summary.missing_price_assets[].name` | amber (flat join) | nessuna |
| Missing FX | `summary.missing_fx_pairs[].pair` | amber (flat join) | nessuna |

**Problemi attuali:**
- `data_quality` (DataQualityReport) è popolato ma **mai letto**
- Nessuna CTA, nessuna navigazione verso l'asset/FX pair
- Nessuna severity distinction (tutto amber uniforme)
- Lista nomi flat (join con virgola) — non scala, non cliccabile
- `stale_prices` e `incomplete_nav_dates` esistono nel DTO ma non mostrati

---

## 2. Proposta DataQualityIssue cross-subsystem

### 2.1 Valutazione campi proposti

```text
DataQualityIssue proposto:
- id optional                   → utile per deduplication, opzionale
- domain                        → NECESSARIO (portfolio|asset|forex|transaction)
- code                          → NECESSARIO
- severity                      → NECESSARIO
- message_i18n_key              → NECESSARIO
- message_params                → NECESSARIO (dict per interpolazione)
- affected_asset_ids            → NECESSARIO (per CTA navigate)
- affected_asset_names          → COMODO (evita join client-side)
- affected_fx_pairs             → NECESSARIO
- affected_broker_ids           → UTILE (per dashboard multi-broker)
- affected_transaction_ids      → RARO (solo per broken linked tx)
- affected_dates                → UTILE (incomplete NAV dates, N elementi max)
- cta_action                    → NECESSARIO (string enum: navigate|add_fx_pair|sync|dismiss)
- cta_target                    → NECESSARIO (URL o ID)
- details_i18n_key optional     → UTILE (testo espandibile)
- details_params optional       → UTILE
- dismissible boolean           → UTILE
- group_key optional            → NECESSARIO per aggregazione
```

**Campi da rimuovere o ridurre:**
- `affected_transaction_ids` → può essere omesso per ora (nessun use case urgente)
- `affected_dates` → limitare a max N (es. 30) per payload size

**Campi mancanti:**
- `affected_broker_names: List[str]` → come `affected_asset_names`, evita join
- `severity_detail: str | None` → testo tecnico breve (es. "WAC missing per EUR/CHF")
- `count: int | None` → "3 asset interessati" senza espandere tutta la lista

### 2.2 DTO finale consigliato

```python
class IssueDomain(str, Enum):
    PORTFOLIO = "portfolio"
    ASSET     = "asset"
    FOREX     = "forex"
    TRANSACTION = "transaction"
    SYSTEM    = "system"

class IssueSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"
    INFO    = "info"

class IssueCode(str, Enum):
    # Portfolio
    MISSING_PRICE             = "MISSING_PRICE"
    TRANSACTION_IMPLIED       = "TRANSACTION_IMPLIED"
    STALE_PRICE               = "STALE_PRICE"
    MISSING_FX_MARKET         = "MISSING_FX_MARKET"
    MISSING_FX_COST_BASIS     = "MISSING_FX_COST_BASIS"
    IN_TRANSIT_NO_PRICE       = "IN_TRANSIT_NO_PRICE"
    IN_TRANSIT_CB_FALLBACK    = "IN_TRANSIT_CB_FALLBACK"
    LINKED_TX_BROKEN          = "LINKED_TX_BROKEN"
    SHARE_MISMATCH            = "SHARE_MISMATCH"
    NAV_INCOMPLETE            = "NAV_INCOMPLETE"
    ALLOCATION_PARTIAL        = "ALLOCATION_PARTIAL"
    PERFORMANCE_PARTIAL       = "PERFORMANCE_PARTIAL"
    MWRR_NOT_CALCULABLE       = "MWRR_NOT_CALCULABLE"
    ASSET_AT_COST             = "ASSET_AT_COST"
    ASSET_UNVALUED            = "ASSET_UNVALUED"
    # Asset
    ASSET_ARCHIVED            = "ASSET_ARCHIVED"
    RANGE_BEFORE_FIRST_DATA   = "RANGE_BEFORE_FIRST_DATA"
    FX_PAIR_MISSING           = "FX_PAIR_MISSING"
    FX_PAIR_NO_DATA           = "FX_PAIR_NO_DATA"
    FX_PAIR_PARTIAL_GAP       = "FX_PAIR_PARTIAL_GAP"
    PRICE_HISTORY_EMPTY       = "PRICE_HISTORY_EMPTY"
    PROVIDER_SYNC_ERROR       = "PROVIDER_SYNC_ERROR"
    # Forex
    CONVERSION_ROUTE_MISSING  = "CONVERSION_ROUTE_MISSING"
    FOREX_NO_DATA             = "FOREX_NO_DATA"
    FOREX_STALE               = "FOREX_STALE"

class DataQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: IssueDomain
    code: IssueCode
    severity: IssueSeverity
    message_i18n_key: str
    message_params: dict = Field(default_factory=dict)
    count: Optional[int] = None                  # N entità coinvolte
    affected_asset_ids: List[int] = []
    affected_asset_names: List[str] = []
    affected_fx_pairs: List[str] = []
    affected_broker_ids: List[int] = []
    affected_dates: List[date] = []              # max 30
    cta_action: Optional[str] = None            # "navigate_asset"|"add_fx_pair"|"sync"|None
    cta_target: Optional[str] = None            # es. "/assets/42" o "EUR-USD"
    details_i18n_key: Optional[str] = None
    details_params: dict = Field(default_factory=dict)
    dismissible: bool = False
    group_key: Optional[str] = None             # raggruppa issues simili
```

### 2.3 Enum unico vs per-dominio

**Raccomandazione: enum unico** (`IssueCode`) con prefissazione semantica.  
Motivo: il banner component è unico, deve fare switch su code. Un enum frammentato richiederebbe union types complessi nel frontend.

### 2.4 CTA per dominio

| cta_action | Comportamento frontend |
|------------|----------------------|
| `navigate_asset` | `href="/assets/{cta_target}"` |
| `navigate_fx` | `href="/fx/{cta_target}"` |
| `add_fx_pair` | apre `FxPairAddModal(cta_target)` |
| `sync_asset` | chiama sync API su `cta_target` (asset_id) |
| `sync_fx` | chiama sync FX su `cta_target` (slug) |
| `navigate_transactions` | `href="/transactions?filter={cta_target}"` |
| `none` | nessuna CTA (solo informativo) |

---

## 3. Scenari asset detail → DataQualityIssue

| Scenario | Trigger attuale | Severity attuale | Domain | IssueCode | CTA |
|----------|----------------|------------------|--------|-----------|-----|
| Asset archived | `assetInfo.active === false` | amber (warning) | ASSET | ASSET_ARCHIVED | none |
| Range before first data | `dateStart < firstDataDate` | sky (info) | ASSET | RANGE_BEFORE_FIRST_DATA | none |
| FX pair missing | `pair.status === 'missing'` | amber (error) | FOREX | FX_PAIR_MISSING | add_fx_pair |
| FX pair no data | `pair.status === 'no-data'` | amber (warning) | FOREX | FX_PAIR_NO_DATA | sync_fx |
| FX pair partial gap | `pair.status === 'partial-gap'` | sky (info) | FOREX | FX_PAIR_PARTIAL_GAP | navigate_fx |
| Provider sync error | `error` string | amber (error) | ASSET | PROVIDER_SYNC_ERROR | dismiss |
| Price history empty | `chartData.length === 0` | inline chart | ASSET | PRICE_HISTORY_EMPTY | sync_asset / add_manually |
| Live price FX failed | `livePriceConversionFailed` | inline (AssetPriceSummary) | FOREX | FX_PAIR_NO_DATA | navigate_fx |

**Compatibilità componente:** tutti compatibili. I banner FX multipli si mappano a N issue con `group_key = "fx_pairs"` per eventuale collapse.

---

## 4. Scenari forex detail → DataQualityIssue

| Scenario | Trigger attuale | Severity attuale | Domain | IssueCode | CTA |
|----------|----------------|------------------|--------|-----------|-----|
| Error generico | `error` string | amber | FOREX | PROVIDER_SYNC_ERROR | dismiss |
| Range before first data | `rangeStartsBeforeData` | sky | FOREX | RANGE_BEFORE_FIRST_DATA | none |
| No data | `chartData.length === 0` | inline | FOREX | FOREX_NO_DATA | sync_fx / add_manually |
| Stale / backward fill | `staleDays > 0` | visuale chart | FOREX | FOREX_STALE | sync_fx |
| Route mancante | non implementato oggi | — | FOREX | CONVERSION_ROUTE_MISSING | add_fx_pair |
| Multi-step route | non implementato | — | FOREX | INFO (futuro) | none |

**Nota:** il FOREX_STALE è oggi gestito visivamente (gradiente sul chart) senza banner. Con il nuovo sistema potrebbe essere un INFO banner con `dismissible: true`.

---

## 5. Scenari portfolio → DataQualityIssue

| Scenario | Severity | IssueCode | Banner principale? | CTA |
|----------|----------|-----------|-------------------|-----|
| Missing price senza cost basis | ERROR | MISSING_PRICE | Sì (prominente) | navigate_asset |
| Transaction-implied valuation | WARNING | TRANSACTION_IMPLIED | Sì | navigate_asset |
| Stale market price (>7gg) | WARNING | STALE_PRICE | Sì (aggregato) | sync_asset |
| Missing FX market value | ERROR | MISSING_FX_MARKET | Sì | add_fx_pair / navigate_fx |
| Missing FX cost basis | WARNING | MISSING_FX_COST_BASIS | Dettaglio secondario | add_fx_pair |
| Asset in transit senza prezzo | WARNING | IN_TRANSIT_NO_PRICE | Dettaglio secondario | navigate_asset |
| Asset in transit fallback CB | INFO | IN_TRANSIT_CB_FALLBACK | Dettaglio espandibile | none |
| Linked tx rotta | WARNING | LINKED_TX_BROKEN | Sì | navigate_transactions |
| Share mismatch broker linked | INFO | SHARE_MISMATCH | Dettaglio espandibile | none |
| NAV incompleto | ERROR | NAV_INCOMPLETE | Sì (derivato da altri) | — |
| Allocation su NAV parziale | WARNING | ALLOCATION_PARTIAL | Dettaglio secondario | — |
| Performance su NAV parziale | WARNING | PERFORMANCE_PARTIAL | Dettaglio secondario | — |
| MWRR non calcolabile | INFO | MWRR_NOT_CALCULABLE | Dettaglio espandibile | none |
| Asset manuale a costo | INFO | ASSET_AT_COST | Dettaglio espandibile | navigate_asset |
| Asset manuale senza valor. | WARNING | ASSET_UNVALUED | Sì | navigate_asset |

**Regola display:**  
- ERROR → sempre banner visibile  
- WARNING → banner visibile (collassabile se >3 item)  
- INFO → solo nel dettaglio espandibile, non banner principale

---

## 6. Store frontend intelligenti esistenti

### 6.1 `TimeSeriesStore<T>` — `frontend/src/lib/stores/core/TimeSeriesStore.ts`

**Responsabilità:** Cache client-side di serie temporali giornaliere.  
**Struttura stato:** `Map<string, T>` (date ISO → punto), `fetchedRanges[]`  
**Cache key:** data ISO come chiave diretta della Map  
**Date from/to:** `getRange(start, end)` — restituisce data + gaps  
**Decisione fetch:** `getMissingIntervals()` → filtra gaps non ancora fetchati  
**Invalidazione:** `invalidateRange(start, end)` o `invalidateAll()`  
**Refresh manuale:** chiamata a `invalidateAll()` + reload  
**Concorrenza:** nessuna deduplication in-flight (gestita sopra dal registry)  
**Limite:** day-granularity only; non supporta weekly/monthly; non gestisce metadata (data_quality)

### 6.2 `fxStoreRegistry` — `frontend/src/lib/stores/fxStoreRegistry.ts`

**Responsabilità:** Registry globale di `TimeSeriesStore<FxDataPoint>` per coppia.  
**Cache key:** `"EUR-USD"` (slug alfabetico)  
**Gap detection:** `store.getMissingIntervals(start, end)` → fetch solo gap  
**Invalidazione:** `invalidateAllFxStores()` o per slug  
**Refresh:** chiama `invalidateAll()` su singolo store + re-fetch  
**Deduplication:** non esplicita a livello registry — `getMissingIntervals` non re-fetcha range già marcati  
**Pattern eccellente:** fetch solo gap, markFetched per 404, merge idempotente

### 6.3 `assetPriceStoreRegistry` — `frontend/src/lib/stores/assetPriceStoreRegistry.ts`

**Responsabilità:** Registry per `TimeSeriesStore<AssetPricePoint>` per (assetId, currency).  
**Cache key:** `"42:EUR"`  
**Pattern:** identico a fxStoreRegistry — gap detection + merge  
**Particolarità:** `invalidateAssetPriceStore(assetId)` invalida tutte le currency

### 6.4 `portfolioStore.svelte.ts` — `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts`

**Responsabilità:** Cache semplice per summary e history.  
**Cache key:** `"brokerIds|dateFrom|dateTo|currency"` — esatta, nessun range coverage  
**Date from/to:** inclusi nella key — nessun subset/superrange  
**Decisione fetch:** `cache.has(key)` → tutto o niente  
**Deduplication:** mappa `inflightMap` — concurrent callers condividono la stessa Promise  
**Invalidazione:** `invalidate()` → svuota tutto  
**Limite principale:** nessun subset client-side; cambio date = nuovo fetch; nessuna data_quality; nessuna history allocation

### 6.5 `entityStore.ts` — `frontend/src/lib/stores/core/entityStore.ts`

**Responsabilità:** Cache di entità list-bounded (asset, broker).  
**Cache key:** entity ID  
**Range:** non pertinente (lista statica)  
**Pattern da riusare:** `ensureLoaded` (lazy+idempotent), `merge` (upsert), concurrent-safe via `loadPromise`

---

## 7. `portfolioReportStore` — Design proposto

### 7.1 Shape dello stato

```typescript
interface PortfolioReport {
    // Metadati della risposta
    brokerIds: number[] | undefined;
    targetCurrency: string;
    dateFrom: string;   // data effettiva calcolata dal backend
    dateTo: string;     // data effettiva calcolata dal backend
    requestedFrom: string;  // data richiesta dal client
    requestedTo: string;
    generatedAt: number;    // timestamp locale

    // Dati
    summary: PortfolioSummary;
    history: PortfolioHistoryPoint[];
    allocationHistory: {
        type?: AllocationHistoryPoint[];
        sector?: AllocationHistoryPoint[];
        geography?: AllocationHistoryPoint[];
    };
    dataQuality: DataQualityReport;
}

interface PortfolioReportStore {
    report: PortfolioReport | null;
    loading: boolean;
    loadingViews: Set<'summary' | 'history' | 'allocation'>;
    error: string | null;
    lastCacheKey: string | null;
}
```

### 7.2 Cache key

```typescript
function makeCacheKey(brokerIds, currency): string {
    return [brokerIds?.sort().join(',') ?? 'all', currency ?? ''].join('|');
}
// NB: dateFrom/dateTo NON fanno parte della cache key — si tiene un solo report
// per combinazione (brokers, currency), con il range più ampio possibile.
```

### 7.3 Coverage temporale

Il report viene sempre fetchato su **full history** (dateFrom=undefined → t=0):

```typescript
// Fetch sempre da t=0 a today
const result = await fetch({
    date_from: undefined,
    date_to: today,
    broker_ids,
    target_currency,
    include_summary: true,
    include_history: true,
    include_allocation_history: true,
    allocation_dimensions: ['type', 'sector', 'geography'],
});
```

Questo permette subset client-side per la history e allocation history.

### 7.4 Subset client-side — quando è sicuro

| Vista | Subset sicuro? | Regola |
|-------|---------------|--------|
| `history` | ✅ Sì | `history.filter(pt => pt.date >= dateFrom && pt.date <= dateTo)` |
| `allocationHistory.*` | ✅ Sì | stesso filtro per date |
| `summary.net_worth` | ✅ Sì (se il report copre fino a `dateTo`) | last daily state = `history[last].nav_value` |
| `summary.cash_total` | ✅ Sì | idem |
| `summary.market_value` | ✅ Sì | idem |
| `summary.total_invested` | ⚠️ No — serve refetch | `total_invested` = Σ deposits - withdrawals **nel range selezionato** |
| `summary.twrr_percent` | ❌ No — serve refetch | TWRR è rebased sul periodo selezionato |
| `summary.mwrr_percent` | ❌ No — serve refetch | idem |
| `summary.simple_roi_percent` | ❌ No — serve refetch | dipende da initial capital che cambia con dateFrom |
| `summary.total_gain_loss` | ❌ No — serve refetch | dipende da total_invested rebased |
| `summary.allocation_by_*` | ✅ Sì | deriva dall'ultimo punto della history filtrata |

**Conclusione pratica:** se l'utente cambia solo `dateTo` → subset sicuro per history + allocations + NAV attuale. Se cambia `dateFrom` → serve refetch per summary/performance metrics.

### 7.5 Strategia cache

```typescript
class PortfolioReportStore {
    // Il report copre SEMPRE da t=0 a today per (brokers, currency)
    private fullReport: PortfolioReport | null = null;
    private cacheKey: string | null = null;
    private inflight: Promise<PortfolioReport> | null = null;

    needsRefetch(brokerIds, currency, dateFrom, dateTo): boolean {
        const key = makeCacheKey(brokerIds, currency);
        if (key !== this.cacheKey) return true;     // brokers/currency cambiati
        if (!this.fullReport) return true;
        // Controllo coverage: il report deve coprire dateTo richiesto
        if (dateTo > this.fullReport.dateTo) return true;
        return false;
    }

    async getView(brokerIds, currency, dateFrom, dateTo): Promise<PortfolioView> {
        if (this.needsRefetch(brokerIds, currency, dateFrom, dateTo)) {
            await this.fetchFull(brokerIds, currency);
        }
        return this.extractSubset(dateFrom, dateTo);
    }

    extractSubset(dateFrom, dateTo): PortfolioView {
        const history = this.fullReport.history
            .filter(pt => pt.date >= dateFrom && pt.date <= dateTo);

        // Summary: solo campi derivabili dall'ultimo punto
        const lastPt = history[history.length - 1];
        const summarySubset = {
            net_worth: lastPt?.nav_value,
            cash_total: lastPt?.cash_value,
            market_value: lastPt?.market_value,
            book_value: lastPt?.book_value,
            unrealized_gain_loss: lastPt?.unrealized_gain_loss,
            // Performance: solo dal report completo se dateFrom == fullReport.dateFrom
            // Altrimenti: segnala che il dato non è derivabile → refetch
            twrr_percent: dateFrom <= this.fullReport.dateFrom ? this.fullReport.summary.twrr_percent : null,
            // ... ecc
        };

        const allocHistory = {
            type: this.fullReport.allocationHistory.type?.filter(pt => pt.date >= dateFrom && pt.date <= dateTo),
            sector: /* idem */,
            geography: /* idem */,
        };

        return {history, summary: summarySubset, allocationHistory: allocHistory, dataQuality: this.fullReport.dataQuality};
    }
}
```

### 7.6 Race condition prevention

```typescript
async fetchFull(brokerIds, currency): Promise<void> {
    const key = makeCacheKey(brokerIds, currency);

    // Deduplication: se già in volo per la stessa key, aspettare
    if (this.inflight && this.cacheKey === key) {
        await this.inflight;
        return;
    }

    this.inflight = (async () => {
        const result = await callReportEndpoint({ brokerIds, currency });
        this.fullReport = result;
        this.cacheKey = key;
    })();

    try { await this.inflight; }
    finally { this.inflight = null; }
}
```

### 7.7 Invalidazione

```typescript
invalidate(): void {
    this.fullReport = null;
    this.cacheKey = null;
    this.inflight = null;
}
```
Trigger: dopo CRUD transazioni, dopo sync prezzi/FX, dopo cambio provider.

### 7.8 Loading per viste

```typescript
loadingViews: $state(new Set<string>());
// 'summary' | 'history' | 'allocation_type' | 'allocation_sector' | 'allocation_geography'
// Consente skeleton separati nelle diverse sezioni della dashboard
```

---

## 8. Endpoint `/portfolio/report`

### 8.1 Request shape consigliata

```json
{
  "date_from": null,
  "date_to": "2025-12-31",
  "broker_ids": [1, 2],
  "target_currency": "EUR",
  "include_summary": true,
  "include_history": true,
  "include_allocation_history": true,
  "allocation_dimensions": ["type", "sector", "geography"]
}
```

**Domande chiuse:**
- **Chiedere sempre tutte le dimensioni:** Sì — costo marginale trascurabile, evita re-fetch
- **Range più ampio:** Sì — fetchare sempre da t=0 lato frontend, non esporre al client
- **Granularity:** parametro opzionale `"daily" | "weekly" | "monthly"` per `allocation_history`. Default: `"daily"` per range < 2 anni, `"weekly"` per > 2 anni (decidere lato backend o frontend)
- **`requested_range` vs `computed_range`:** necessario — il backend può avere dati da data X, il client chiede da prima

### 8.2 Response metadata necessari

```json
{
  "metadata": {
    "broker_ids": [1, 2],
    "target_currency": "EUR",
    "requested_date_from": null,
    "computed_date_from": "2022-03-15",
    "date_to": "2025-12-31",
    "generated_at": "2025-12-31T18:00:00Z",
    "allocation_dimensions": ["type", "sector", "geography"],
    "granularity": "daily"
  },
  "summary": { ... },
  "history": [ ... ],
  "allocation_history": {
    "type": [ ... ],
    "sector": [ ... ],
    "geography": [ ... ]
  },
  "data_quality": {
    "issues": [ ... ]
  }
}
```

**`data_version`:** non disponibile ora — omettere.

---

## 9. Output finale

### 9.1 Raccomandazione DataQualityIssue cross-subsystem

Usare un DTO unico con `domain` + `code` enum. Il componente frontend `DataQualityBanner.svelte` switch su `severity` per stile e su `code` per CTA. Issue raggruppate via `group_key`.

### 9.2 Campi DTO finali

Vedi §2.2. Aggiungere a `DataQualityReport` un campo `issues: List[DataQualityIssue]` mantenendo i campi legacy per backward compat.

### 9.3 Mappa IssueCode per dominio

```
ASSET:       ASSET_ARCHIVED, RANGE_BEFORE_FIRST_DATA, FX_PAIR_MISSING, FX_PAIR_NO_DATA,
             FX_PAIR_PARTIAL_GAP, PRICE_HISTORY_EMPTY, PROVIDER_SYNC_ERROR
FOREX:       CONVERSION_ROUTE_MISSING, FOREX_NO_DATA, FOREX_STALE, FX_PAIR_MISSING,
             RANGE_BEFORE_FIRST_DATA, PROVIDER_SYNC_ERROR
PORTFOLIO:   MISSING_PRICE, TRANSACTION_IMPLIED, STALE_PRICE, MISSING_FX_MARKET,
             MISSING_FX_COST_BASIS, IN_TRANSIT_NO_PRICE, IN_TRANSIT_CB_FALLBACK,
             LINKED_TX_BROKEN, SHARE_MISMATCH, NAV_INCOMPLETE, ALLOCATION_PARTIAL,
             PERFORMANCE_PARTIAL, MWRR_NOT_CALCULABLE, ASSET_AT_COST, ASSET_UNVALUED
TRANSACTION: LINKED_TX_BROKEN (condiviso con PORTFOLIO)
```

### 9.4 Strategia UI DataQualityBanner

```svelte
<!-- DataQualityBanner.svelte -->
<!-- Props: issues: DataQualityIssue[], context?: 'portfolio'|'asset'|'forex' -->
{#each groupedIssues as group}
  <div class="{severityClass(group.severity)} rounded-xl px-4 py-2.5 flex ...">
    <span>{emoji(group.severity)}</span>
    <div class="flex-1">
      <span>{$t(group.message_i18n_key, {values: group.message_params})}</span>
      {#if group.count && group.count > 1}
        <!-- Accordion per lista asset coinvolti -->
        <details>
          <summary>{$t('dq.affectedCount', {values: {n: group.count}})}</summary>
          {#each group.affected_asset_names as name}
            <a href="/assets/{...}">{name}</a>
          {/each}
        </details>
      {/if}
    </div>
    <!-- CTA inline -->
    {#if group.cta_action === 'add_fx_pair'}
      <button onclick={() => openFxModal(group.cta_target)}>Add FX pair</button>
    {:else if group.cta_action === 'navigate_asset'}
      <a href="/assets/{group.cta_target}">→ Asset</a>
    {/if}
    {#if group.dismissible}
      <button onclick={() => dismiss(group)}>×</button>
    {/if}
  </div>
{/each}
```

**Stile:** identico ad asset detail (amber vs sky), con `<details>` per accordion.

### 9.5 Raccomandazione portfolioReportStore

Fetch full history da t=0 a today per (brokers, currency). Subset client-side per history e allocation history. Refetch obbligatorio per performance metrics se dateFrom cambia. Cache invalidata dopo CRUD/sync. Deduplication in-flight via Promise condivisa.

### 9.6 Cosa può essere filtrato client-side

✅ Sicuro: `history`, `allocationHistory.*`, `summary.{net_worth, cash_total, market_value, book_value, unrealized_gain_loss, allocation_by_*}` usando l'ultimo punto della history filtrata.

❌ Richiede refetch: `summary.{twrr_percent, mwrr_percent, simple_roi_percent, total_gain_loss, total_invested}` — tutti dipendono dal periodo di calcolo.

### 9.7 `/portfolio/report` request/response

Request: `{date_from?, date_to, broker_ids?, target_currency, include_summary, include_history, include_allocation_history, allocation_dimensions[], granularity?}`

Response: `{metadata: {computed_date_from, date_to, broker_ids, target_currency, granularity, generated_at}, summary, history, allocation_history: {type?, sector?, geography?}, data_quality: {issues[]}}`

### 9.8 File da modificare

| File | Modifica |
|------|---------|
| `backend/app/schemas/portfolio.py` | Aggiungere `IssueDomain`, `IssueSeverity`, `IssueCode`, `DataQualityIssue`; aggiornare `DataQualityReport.issues`; nuovo `PortfolioReport` response DTO |
| `backend/app/services/portfolio_engine.py` | `build_data_quality_report()` produce `List[DataQualityIssue]`; `_market_value_for()` fallback TRANSACTION_IMPLIED |
| `backend/app/services/portfolio_service.py` | `get_summary()` popola `data_quality.issues` |
| `backend/app/api/v1/portfolio_api.py` | Nuovo `POST /portfolio/report` endpoint |
| `frontend/src/lib/stores/portfolio/portfolioStore.svelte.ts` | Evolvere o affiancare con `portfolioReportStore.svelte.ts` |
| `frontend/src/lib/components/ui/DataQualityBanner.svelte` | **Nuovo** — componente unificato |
| `frontend/src/routes/(app)/dashboard/+page.svelte` | Sostituire banner inline con `<DataQualityBanner>` |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | Integrare `DataQualityBanner` per FX/data issues |
| `frontend/src/lib/i18n/{en,it,fr,es}.json` | Chiavi `dq.*` per ogni IssueCode |

### 9.9 Test minimi

```
backend:
  test_data_quality_issue_schema_serialization
  test_issue_code_enum_complete
  test_missing_price_produces_error_issue
  test_stale_price_produces_warning_issue
  test_transaction_implied_produces_warning_issue
  test_nav_incomplete_dates_in_report
  test_portfolio_report_endpoint_full_response

frontend:
  unit: DataQualityBanner renders amber for ERROR
  unit: DataQualityBanner renders sky for INFO
  unit: DataQualityBanner renders CTA button for add_fx_pair
  unit: DataQualityBanner accordion expands for count > 3
  unit: portfolioReportStore extracts subset for history
  unit: portfolioReportStore returns null for twrr on dateFrom change
  unit: portfolioReportStore deduplicates concurrent fetches
  e2e: dashboard_shows_dq_banner_on_missing_price
  e2e: dashboard_dq_banner_navigates_to_asset
```

### 9.10 Domande aperte residue

1. **TRANSACTION_IMPLIED vs ASSET_AT_COST:** termini diversi per l'utente finale? Suggerito: TRANSACTION_IMPLIED per "sto usando il prezzo di acquisto provvisoriamente", ASSET_AT_COST per "asset manuale permanentemente a costo".
2. **Granularity allocation history:** decidere lato backend (basato su range) o lato frontend (parametro esplicito)? Lato backend semplifica il client ma riduce flessibilità.
3. **Banner asset/forex:** retrocompatibilità — è accettabile che asset e forex detail ricevano issue dal backend o la logica rimane client-side? La soluzione ibrida è possibile: frontend costruisce issue localmente + backend li include nelle response dove appropriato.
4. **`computed_date_from` nel metadata:** il backend lo restituisce già oggi o serve aggiungerlo?
5. **Store unico vs separati:** `portfolioReportStore` sostituisce `portfolioStore` o coesistono? Suggerito: coesistenza temporanea, migrazione progressiva.
6. **Dismissal persistence:** le issue dismissibili devono essere ricordate tra sessioni (localStorage) o solo per la sessione corrente?
