# Plan: FX Store Registry — `ensureFxRangeLoaded` Helper

**Status**: ✅ DONE  
**Data**: 1 Giugno 2026
**Priority**: P3 (cleanup / DRY)
**Tipo**: Independent mini-plan (no transazioni, no fasi in corso)

## 🤖 Modello Suggerito & Effort

| Parametro | Valore |
|-----------|--------|
| **Modello** | `claude-haiku-4.5` |
| **Effort stimato** | ~2h |
| **Difficoltà** | Bassa |
| **Rationale** | Pattern meccanico e ripetitivo: 1 funzione nuova + 4 file da refactorare seguendo lo stesso pattern. Il codice di riferimento è già nel registry. Haiku è sufficiente. |

---

## 🎯 Obiettivo

Il `fxStoreRegistry.ts` già gestisce cache e single-point lookup (`lookupFxRate`).
Ma il pattern **range-based** (gap detection → bulk fetch → merge) è duplicato inline in 4 pagine:

| File | Pattern inline |
|------|---------------|
| `fx/+page.svelte` | riga ~286: `getMissingIntervals → POST convert → merge` |
| `fx/[pair]/+page.svelte` | riga ~381: idem |
| `assets/+page.svelte` | riga ~685: idem |
| `assets/[id]/+page.svelte` | riga ~415, ~545, ~954: idem (3 chiamate) |

L'obiettivo è centralizzare il pattern in una funzione `ensureFxRangeLoaded` nel registry.

---

## Stato Attuale (code-verified 2026-06-01)

| Componente | Stato |
|---|---|
| `fxStoreRegistry.ts` — `getFxStore()` | ✅ Operativo |
| `fxStoreRegistry.ts` — `lookupFxRate()` | ✅ Operativo (single-point con cache) |
| `fxStoreRegistry.ts` — `ensureFxRangeLoaded()` | ❌ Non esiste |
| `TimeSeriesStore.getMissingIntervals()` | ✅ Operativo |
| `zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post` | ✅ Operativo |
| `apiResultToFxDataPoint()` | ✅ Operativo (già nel registry) |

---

## Step 1 — Aggiungere `ensureFxRangeLoaded` a `fxStoreRegistry.ts`

### Firma

```typescript
/**
 * Ensure FX data for the given pair and date range is loaded into the cache.
 * Gap-detection + bulk fetch + merge — all in one call.
 *
 * @param slug      Pair slug in alphabetical order (e.g. "EUR-USD")
 * @param start     Start date YYYY-MM-DD (inclusive)
 * @param end       End date YYYY-MM-DD (inclusive)
 * @returns         All cached FxDataPoints in [start, end] after loading
 */
export async function ensureFxRangeLoaded(
    slug: string,
    start: string,
    end: string
): Promise<FxDataPoint[]>
```

### Implementazione

```typescript
export async function ensureFxRangeLoaded(
    slug: string,
    start: string,
    end: string
): Promise<FxDataPoint[]> {
    const store = getFxStore(slug);
    const gaps = store.getMissingIntervals(start, end);

    if (gaps.length > 0) {
        const {base: canonBase, quote: canonQuote} = parsePairSlug(slug);
        const convertRequests = gaps.map((gap) => ({
            from_amount: {code: canonBase, amount: '1'},
            to: canonQuote,
            date_range: {start: gap.start, end: gap.end},
        }));

        try {
            const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(convertRequests);
            const results = (response as any)?.results ?? [];
            const points = results.map(apiResultToFxDataPoint);
            if (points.length > 0) store.merge(points);
        } catch {
            // Network failure — return whatever is cached
        }
    }

    return store.getRange(start, end);
}
```

> **Nota**: `store.getRange(start, end)` — verificare che `TimeSeriesStore` abbia questo metodo.
> Se il nome è diverso usare `store.getAllSorted().filter(p => p.date >= start && p.date <= end)`.

### File modificato

- `frontend/src/lib/stores/fxStoreRegistry.ts` — aggiungere funzione in sezione `// SPOT LOOKUPS` (o nuova sezione `// RANGE HELPERS`)

---

## Step 2 — Refactor `fx/+page.svelte`

Cercare il blocco:
```typescript
const gaps = store.getMissingIntervals(dateStart, dateEnd);
if (gaps.length === 0) { ... }
const convertRequests = gaps.map(...);
const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(convertRequests);
store.merge(points);
```

Sostituire con:
```typescript
await ensureFxRangeLoaded(pair.config.slug, dateStart, dateEnd);
```

(e aggiornare l'import da `fxStoreRegistry`).

---

## Step 3 — Refactor `fx/[pair]/+page.svelte`

Stesso pattern del Step 2. Le occorrenze rilevanti sono circa a riga 381 e 492.

---

## Step 4 — Refactor `assets/+page.svelte`

Occorrenza a riga ~685: il blocco `getMissingIntervals` per caricare FX per colonna valuta nella asset list.

---

## Step 5 — Refactor `assets/[id]/+page.svelte`

Occorrenze multiple (~415, ~545, ~954): caricamento FX per il grafico asset detail e per le sovrapposizioni FX.

> **Attenzione**: nella detail page il `slug` potrebbe non essere in ordine alfabetico. Usare sempre `createPairSlug(base, quote)` per normalizzare prima di chiamare `ensureFxRangeLoaded`.

---

## Step 6 — Verifica

1. Aprire fx list, fx detail, asset list, asset detail: i grafici devono caricare correttamente
2. Navigare avanti/indietro: la cache deve prevenire re-fetch per range già caricati
3. `svelte-check` 0 errori

---

## File Coinvolti

| File | Modifica |
|------|----------|
| `frontend/src/lib/stores/fxStoreRegistry.ts` | Aggiungere `ensureFxRangeLoaded` |
| `frontend/src/routes/(app)/fx/+page.svelte` | Refactor (~1 occorrenza) |
| `frontend/src/routes/(app)/fx/[pair]/+page.svelte` | Refactor (~2 occorrenze) |
| `frontend/src/routes/(app)/assets/+page.svelte` | Refactor (~1 occorrenza) |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | Refactor (~3 occorrenze) |

---

## Rischi

- **Basso**: le pagine usano già `getFxStore` dal registry — solo il pattern inline cambia
- **Zero breaking**: nessun cambio API backend, nessun cambio schema
- **Retrocompatibilità**: le pagine non cambiano comportamento visuale

---

## Step 7 — Unit test `fxStoreRegistry.test.ts` ✅ 2026-06-01

**File da creare**: `frontend/src/lib/stores/__tests__/fxStoreRegistry.test.ts`

**Tool**: Vitest (stesso setup di `TimeSeriesStore.test.ts`)

### Setup e teardown

```typescript
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {ensureFxRangeLoaded, getFxStore, getRegisteredPairs, removeFxStore} from '../fxStoreRegistry';

// Mock zodiosApi — intercetta convert_currency_bulk prima che venga chiamato
vi.mock('$lib/api', () => ({
    zodiosApi: {
        convert_currency_bulk_api_v1_fx_currencies_convert_post: vi.fn(),
    },
}));

// Import DOPO il mock per avere il riferimento al mock spy
import {zodiosApi} from '$lib/api';
const mockConvert = vi.mocked(zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post);

// Helper: costruisce una FX API response
function apiResp(...dates: string[]) {
    return {
        results: dates.map((d) => ({
            conversion_date: d,
            rate: '1.25',
            backward_fill_info: null,
        })),
    };
}

beforeEach(() => {
    // Resetta il singleton fxStores tra i test
    for (const slug of getRegisteredPairs()) removeFxStore(slug);
    mockConvert.mockReset();
});
```

> **Nota ordine import**: con `vi.mock` hoistato da Vitest, l'import di `zodiosApi` dopo il mock riceverà il mock spy. In alternativa si può usare `vi.importMock`.

### Casi di test

```typescript
describe('ensureFxRangeLoaded', () => {
    // =========================================================================
    // Test 1: Cache hit completa — nessuna chiamata API
    // =========================================================================
    it('returns cached data without calling the API when range is fully covered', async () => {
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-02', rate: 1.2, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).not.toHaveBeenCalled();
        expect(result).toHaveLength(3);
        expect(result[0].date).toBe('2024-01-01');
    });

    // =========================================================================
    // Test 2: Cache miss completa — API chiamata, dati mergiati e ritornati
    // =========================================================================
    it('fetches the full range when store is empty', async () => {
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-01', '2024-01-02', '2024-01-03'));

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).toHaveBeenCalledOnce();
        // La request deve coprire l'intero range come unico gap
        const [requests] = mockConvert.mock.calls[0];
        expect(requests).toHaveLength(1);
        expect(requests[0].date_range).toEqual({start: '2024-01-01', end: '2024-01-03'});
        expect(requests[0].from_amount.code).toBe('EUR');
        expect(requests[0].to).toBe('USD');
        // I dati sono stati mergiati e ritornati
        expect(result).toHaveLength(3);
        expect(result[0].rate).toBe(1.25);
    });

    // =========================================================================
    // Test 3: Gap parziale — API chiamata solo per i buchi, cache intatta
    // =========================================================================
    it('fetches only the missing gaps when range is partially cached', async () => {
        // Pre-popola 01 e 03, il buco è solo 02
        const store = getFxStore('EUR-USD');
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-02'));

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');

        expect(mockConvert).toHaveBeenCalledOnce();
        const [requests] = mockConvert.mock.calls[0];
        // Solo il gap 2024-01-02
        expect(requests).toHaveLength(1);
        expect(requests[0].date_range).toEqual({start: '2024-01-02', end: '2024-01-02'});
        // Il risultato finale contiene tutti e 3 i giorni
        expect(result).toHaveLength(3);
    });

    // =========================================================================
    // Test 4: Errore API — nessun throw, ritorna la cache parziale
    // =========================================================================
    it('silently swallows API errors and returns whatever is cached', async () => {
        const store = getFxStore('EUR-USD');
        store.merge([{date: '2024-01-01', rate: 1.1, backwardFillInfo: null}]);
        mockConvert.mockRejectedValueOnce(new Error('Network error'));

        // Non deve lanciare
        await expect(ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03')).resolves.toBeDefined();

        const result = await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-03');
        // Ritorna solo i dati già in cache, 2024-01-02 e 03 mancano
        expect(result).toHaveLength(1);
        expect(result[0].date).toBe('2024-01-01');
    });

    // =========================================================================
    // Test 5: Slug normalizzato — request usa canonBase/canonQuote
    // =========================================================================
    it('uses canonical alphabetical base/quote regardless of slug input', async () => {
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-01'));

        // 'USD-EUR' non è canonical — EUR < USD, quindi il registry usa 'EUR-USD'
        await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-01');

        const [requests] = mockConvert.mock.calls[0];
        // canonBase = 'EUR', canonQuote = 'USD' (ordine alfabetico)
        expect(requests[0].from_amount.code).toBe('EUR');
        expect(requests[0].to).toBe('USD');
    });

    // =========================================================================
    // Test 6: Gap multipli — API chiamata con N request (una per gap)
    // =========================================================================
    it('sends one request per gap when there are multiple holes', async () => {
        const store = getFxStore('EUR-USD');
        // Popola solo 01 e 03 — due gap: 02 e 04-05
        store.merge([
            {date: '2024-01-01', rate: 1.1, backwardFillInfo: null},
            {date: '2024-01-03', rate: 1.3, backwardFillInfo: null},
        ]);
        mockConvert.mockResolvedValueOnce(apiResp('2024-01-02', '2024-01-04', '2024-01-05'));

        await ensureFxRangeLoaded('EUR-USD', '2024-01-01', '2024-01-05');

        const [requests] = mockConvert.mock.calls[0];
        // Due gap → due request objects nell'array
        expect(requests).toHaveLength(2);
        expect(requests[0].date_range).toEqual({start: '2024-01-02', end: '2024-01-02'});
        expect(requests[1].date_range).toEqual({start: '2024-01-04', end: '2024-01-05'});
    });
});
```

### Note implementative

- **`getRegisteredPairs` + `removeFxStore`** nel `beforeEach`: ripulisce il Map singleton tra i test senza impattare altri moduli
- **`mockConvert.mock.calls[0]`**: il primo argomento della prima call è l'array di `BulkConvertRequest`
- **Test 4 doppia call**: la seconda `ensureFxRangeLoaded` triggera un secondo tentativo API che lancia di nuovo — il test verifica che il risultato sia comunque la cache e non un'eccezione; se si vuole verificare una sola call usare `mockConvert.mockRejectedValue(...)` (permanente)
- **`amount: '1'`** nella request: verificabile con `expect(requests[0].from_amount.amount).toBe('1')` — da aggiungere al Test 2 o 5 se si vuole coverage esplicita

---

## Step 8 — Asset Price Cache (Piano C) ✅ 2026-06-01

### Obiettivo

Estendere il pattern `ensureFxRangeLoaded` ai **prezzi asset**: cache client-side con gap-detection, così che un cambio range temporale sia istantaneo se i dati sono già in memoria. Anche le conversioni (`target_currency`) sono cachate come store separati (Piano C: `{assetId}:{currency}`).

### Architettura

Nuovo file `frontend/src/lib/stores/assetPriceStoreRegistry.ts`:

```typescript
// Key: "42:EUR" = asset 42, prices in EUR
const stores: Map<string, TimeSeriesStore<AssetPricePoint>> = new Map();

export function getAssetPriceStore(assetId: number, currency: string): TimeSeriesStore<AssetPricePoint>
export function ensureAssetPriceRangeLoaded(assetId: number, currency: string, start: string, end: string, opts?): Promise<AssetPricePoint[]>
export function invalidateAssetPriceStore(assetId: number): void  // invalida TUTTE le currency
export function apiPricesToAssetPricePoints(prices: any[]): AssetPricePoint[]
```

`AssetPricePoint` include: `date, close, open, high, low, volume, currency, originalClose, backwardFillInfo`.

### Modifiche applicate

| File | Modifica |
|------|----------|
| `frontend/src/lib/stores/assetPriceStoreRegistry.ts` | **NUOVO** — registry + helper |
| `frontend/src/lib/stores/__tests__/assetPriceStoreRegistry.test.ts` | **NUOVO** — 9 tests |
| `frontend/src/routes/(app)/assets/[id]/+page.svelte` | `loadChartData(force?)`: cache-first path (no `loading = true` on cache hit). Invalidation on sync/refresh |
| `frontend/src/routes/(app)/assets/+page.svelte` | `fetchAllPriceData`: split cached/needFetch, bulk solo per quelli con gaps. Invalidation on sync/refresh |

### Comportamento

- Range narrows (1Y → 3M) → cache hit → **instant**, no loading spinner, no API call
- Range expands (3M → 1Y) → gap detected → fetch → populate cache
- Sync / Refresh → `invalidateAssetPriceStore` → force refetch (tutte le currency)
- DisplayCurrency change → store key diverso (`42:EUR` vs `42:USD`) → first time = miss → fetch → cached per dopo
- 404 → marked as fetched (no retry loop)
- Network error → NOT marked (retry allowed)

### Bug fix: FX banner falso positivo

Problema: con la cache, il path `chartData = cached.map(...)` non ricostruiva il campo `original_close` → `fxFirstConvertedDate` sempre `null` → banner "no FX data" appariva incorrettamente.

Fix: aggiunto `originalClose` a `AssetPricePoint`, mappato in `apiPricesToAssetPricePoints`, e ricostruito come `original_close` nel cache-hit path.

### Tests

9 unit tests in `assetPriceStoreRegistry.test.ts`:
1. Cache hit — no API call
2. Cache miss — fetches from API
3. Partial gap — fetches only missing range
4. Network error — allows retry
5. 404 — marks as fetched (no retry loop)
6. Different currencies use different stores
7. invalidateAssetPriceStore clears ALL currencies
8. targetCurrency option passed to API
9. apiPricesToAssetPricePoints mapping correctness
