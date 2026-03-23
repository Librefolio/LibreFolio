# Plan: Phase 06 — Bugfix, Migrazione e UX Refinement (Rientro post Step 1+2)

**Data creazione**: 23 Marzo 2026
**Ultimo aggiornamento**: 23 Marzo 2026
**Contesto**: Dopo il completamento di Phase 06 Step 1 (backend) e Step 2 (frontend dual view),
la review ha evidenziato bug, debiti tecnici e miglioramenti UX da risolvere prima di procedere
con Step 3 (AssetModal). Questo piano di rientro corregge tutto in ordine di dipendenza.

**Durata stimata**: ~0.5 giorni
**Dipendenze**: Phase 06 Step 1 + Step 2 completati

---

## Indice

| # | Titolo | Area | Priorità |
|---|--------|------|----------|
| 1 | Fix crash `.toFixed()` su pagina Assets | Frontend | 🔴 Bloccante |
| 2 | Migrazione BrokerIcon a Svelte 5 runes | Frontend | 🟡 Debito tecnico |
| 3 | Migrazione localStorage a user-scoped | Frontend | 🟡 Debito tecnico |
| 4 | Fix FX delete 422 (`date_range` array → oggetto) | Frontend | 🔴 Bug |
| 5 | Fix FX detail UX per coppie manual-only | Frontend + UX | 🟡 UX |
| 6 | Spostare ViewModeToggle nell'header | Frontend | 🟢 Estetica |
| 7 | Endpoint bulk asset prices + colonne Δ multi-periodo | Backend + Frontend + Test | 🟢 Feature |
| 8 | Fix test upload 401 | Backend test | 🟡 Test |
| 9 | Rimuovere chiave i18n orfana | i18n | 🟢 Pulizia |

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
   │   ├── 7a (backend bulk endpoint) ─── prima
   │   ├── 7b (test migration GET → POST) ─── dopo 7a
   │   └── 7c (frontend bulk + colonne Δ) ─── dopo 7a (serve client Zodios aggiornato)
   │
   ├── Step 8 (fix test upload) ─── indipendente (backend)
   │
   └── Step 9 (i18n cleanup) ─── indipendente

Step 2-6, 8-9 sono parallelizzabili.
Step 7a → 7b/7c è sequenziale.
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

### Operazioni allineate ✅

| Operazione | FX | Assets | Note |
|---|---|---|---|
| **Upsert manuale** | `POST /fx/currencies/rate` → loop per-item nel controller, chiama `upsert_rates_bulk()` | `POST /assets/prices` → chiama `bulk_upsert_prices()` direttamente | Entrambi bulk, loop nel service layer. ✅ |
| **Delete** | `DELETE /fx/currencies/rate` → normalizza, separa `delete_all` da date-range, chiama `delete_rates_bulk()` | `DELETE /assets/prices` → chiama `bulk_delete_prices()` | Entrambi bulk. ✅ |
| **Sync/Refresh da provider** | `POST /fx/currencies/sync` → `sync_pairs_bulk()` | `POST /assets/prices/refresh` → `bulk_refresh_prices()` | Entrambi: provider fetch → store in DB. ✅ |
| **Provider management** | `GET/POST/DELETE /fx/providers/routes` | `GET/POST/DELETE /assets/provider` | Entrambi CRUD provider. ✅ |
| **Bulk read** | `POST /fx/currencies/convert` → `convert_bulk()` → **1 query DB** | `POST /assets/prices/query` → `get_prices_bulk()` → **1 query DB** | Entrambi: singola query, partizionamento in memoria, backward-fill. ✅ |

### Disallineamento corretto in questo piano ⚠️ → ✅

| Operazione | FX (corretto) | Assets (PRIMA) | Assets (DOPO) |
|---|---|---|---|
| **Read prezzi** | `convert()` → `convert_bulk()` → **solo DB**, mai provider | `GET /prices/{id}` → `get_prices()` → **provider HTTP + fallback DB** | **Eliminato.** Usa solo `POST /prices/query` → `get_prices_bulk()` → **solo DB** |

#### Dettaglio del problema originale

**FX** separa nettamente lettura da sync:
- `sync` = scrivi dati nel DB (dai provider) — solo su richiesta utente
- `convert` = leggi dati dal DB — mai provider

**Asset `get_prices()`** (riga 1222 di `asset_source.py`) aveva una logica ibrida:
1. Check se c'è un provider assignment
2. Se sì → **chiama il provider** (HTTP call a yfinance/justetf/css scraper!)
3. Se provider fallisce → fallback al DB

Ogni lettura poteva generare chiamate HTTP esterne. Per la lista con 50 asset = 50 HTTP calls.

#### Correzione (inclusa in questo piano)

**Backend**:
- **Eliminare** `GET /assets/prices/{asset_id}` e il metodo `get_prices()` dal service layer
- **Eliminare** `_fetch_provider_history()` dal flusso di lettura (resta usata solo da `refresh`)
- L'unico modo per leggere prezzi è `POST /assets/prices/query` → `get_prices_bulk()` → **solo DB**
- I provider vengono contattati **solo** via `POST /assets/prices/refresh` su richiesta esplicita dell'utente

**Frontend — pagina detail asset (Phase 06 Step 4)**:
La pagina detail leggerà i prezzi dal DB via `POST /assets/prices/query` (stessa del list).
Il comportamento del bottone Refresh/Sync segue lo **stesso pattern di FX detail**:
- Se c'è almeno 1 provider → bottone Refresh attivo → `POST /assets/prices/refresh`
- Se non c'è provider → bottone Refresh **disabilitato** (`opacity-50 cursor-not-allowed`)
  e il grafico mostra un messaggio "Nessun dato — inserire i prezzi manualmente" con
  bottone per aprire l'editor (identico a Step 5 per FX manual-only)

**Test**:
- Tutti i test che usavano `GET /assets/prices/{id}` sono già migrati a `POST /query` (Step 7b)
- L'endpoint GET non esiste più → nessun test da mantenere

#### Impatto sul piano

Lo Step 7a include già la rimozione: nella checklist aggiungere:
- Eliminare `GET /{asset_id}` da `assets.py`
- Eliminare `get_prices()` da `asset_source.py` (o rinominarlo in `_get_prices_with_provider`
  e renderlo privato, usato solo internamente da `refresh`)
- Aggiornare `./dev.py api sync` (il client Zodios non genererà più il metodo GET)

Lo Step 4 del piano principale (Phase 06 Step 4 — Asset Detail) dovrà seguire il pattern
FX detail per il bottone refresh, con le stesse chiavi i18n `assetDetail.noDataManual`,
`assetDetail.insertManually`, `assetDetail.refreshDisabledNoProvider`.

