/**
 * FX Store Registry — Global registry of TimeSeriesStore instances for FX pairs.
 *
 * Provides a shared TimeSeriesStore<FxDataPoint> for each currency pair.
 * The same instance is used by FxCard in the list page and the FX detail page,
 * so navigating from card → detail preserves cached data (only gaps are fetched).
 *
 * Keys are slugs in alphabetical order (e.g., "EUR-USD"), matching the backend
 * convention where base < quote.
 *
 * @module stores/fxStoreRegistry
 */

import type {TimeSeriesPoint} from './core/TimeSeriesStore';
import {TimeSeriesStore} from './core/TimeSeriesStore';
import type {ChainStep} from '$lib/utils/currency/currencyGraph';
import {zodiosApi} from '$lib/api';

// Re-export ChainStep for consumers that import from fxStoreRegistry
export type {ChainStep};

// ============================================================================
// FX DATA TYPES
// ============================================================================

/**
 * FX time-series data point.
 * Derived from POST /fx/currencies/convert response with amount=1.
 */
export interface FxDataPoint extends TimeSeriesPoint {
    /** ISO date YYYY-MM-DD */
    date: string;
    /** Exchange rate (1 base = rate * quote) */
    rate: number;
    /** Backward-fill info — null means exact date match */
    backwardFillInfo: {
        actualRateDate: string;
        daysBack: number; // = staleDays for gradient opacity
    } | null;
}

/**
 * FX pair configuration derived from GET /fx/providers/routes.
 * Represents a unique currency pair with its route configuration.
 */
export interface FxPairConfig {
    /** Base currency ISO code (alphabetically first) */
    base: string;
    /** Quote currency ISO code (alphabetically second) */
    quote: string;
    /** Slug for routing: "EUR-USD" */
    slug: string;
    /** Route configurations ordered by priority */
    providers: Array<{
        /** Primary provider code (first step's provider, for display) */
        providerCode: string;
        priority: number;
        /** Full chain steps — 1 step = direct, 2+ = chain */
        chainSteps: ChainStep[];
        fetchInterval?: number | null;
    }>;
}

// ============================================================================
// REGISTRY
// ============================================================================

/** Global registry of FX TimeSeriesStore instances, keyed by pair slug */
const fxStores: Map<string, TimeSeriesStore<FxDataPoint>> = new Map();

/**
 * Create a pair slug from base and quote currencies.
 * Always in alphabetical order (matching backend convention).
 *
 * @example
 * createPairSlug('EUR', 'USD') → 'EUR-USD'
 * createPairSlug('USD', 'EUR') → 'EUR-USD'  // normalized
 */
export function createPairSlug(base: string, quote: string): string {
    const a = base.toUpperCase();
    const b = quote.toUpperCase();
    return a < b ? `${a}-${b}` : `${b}-${a}`;
}

/**
 * Parse a pair slug back into base and quote currencies.
 *
 * @example
 * parsePairSlug('EUR-USD') → { base: 'EUR', quote: 'USD' }
 */
export function parsePairSlug(slug: string): {base: string; quote: string} {
    const parts = slug.split('-');
    if (parts.length !== 2) {
        throw new Error(`Invalid pair slug: "${slug}". Expected format: "AAA-BBB"`);
    }
    return {base: parts[0].toUpperCase(), quote: parts[1].toUpperCase()};
}

/**
 * Get or create a TimeSeriesStore for a currency pair.
 * If the store already exists, returns the shared instance.
 *
 * @param slug - Pair slug in alphabetical order (e.g., "EUR-USD")
 */
export function getFxStore(slug: string): TimeSeriesStore<FxDataPoint> {
    let store = fxStores.get(slug);
    if (!store) {
        store = new TimeSeriesStore<FxDataPoint>();
        fxStores.set(slug, store);
    }
    return store;
}

/**
 * Get a store by base/quote currencies (convenience wrapper).
 * Normalizes to alphabetical order automatically.
 */
export function getFxStoreByPair(base: string, quote: string): TimeSeriesStore<FxDataPoint> {
    return getFxStore(createPairSlug(base, quote));
}

/**
 * Invalidate all FX stores (for global refresh).
 */
export function invalidateAllFxStores(): void {
    for (const store of fxStores.values()) {
        store.invalidateAll();
    }
}

/**
 * Remove a specific FX store from the registry (for pair deletion).
 */
export function removeFxStore(slug: string): boolean {
    const store = fxStores.get(slug);
    if (store) {
        store.invalidateAll();
        fxStores.delete(slug);
        return true;
    }
    return false;
}

/**
 * Get all registered pair slugs.
 */
export function getRegisteredPairs(): string[] {
    return Array.from(fxStores.keys());
}

/**
 * Convert a FXConversionResult from the API to an FxDataPoint.
 *
 * @param result - Single conversion result from POST /fx/currencies/convert
 */
export function apiResultToFxDataPoint(result: {
    conversion_date: string;
    rate?: string | null;
    backward_fill_info?: {
        actual_rate_date: string;
        days_back: number;
    } | null;
}): FxDataPoint {
    return {
        date: result.conversion_date,
        rate: result.rate ? parseFloat(String(result.rate)) : 0,
        backwardFillInfo: result.backward_fill_info
            ? {
                  actualRateDate: result.backward_fill_info.actual_rate_date,
                  daysBack: result.backward_fill_info.days_back,
              }
            : null,
    };
}

// ============================================================================
// SPOT LOOKUPS
// ============================================================================

/**
 * Synchronous cache-only lookup. Returns the FxDataPoint if already cached,
 * undefined otherwise. Use for instant reads without triggering fetches.
 */
export function lookupFxRateSync(base: string, quote: string, date: string): FxDataPoint | undefined {
    const slug = createPairSlug(base, quote);
    const store = fxStores.get(slug);
    if (!store) return undefined;
    const point = store.get(date);
    if (!point) return undefined;
    const {base: canonBase} = parsePairSlug(slug);
    if (canonBase === base.toUpperCase()) return point;
    // Invert: stored is canonBase→canonQuote, we need base→quote where base != canonBase
    return {...point, rate: point.rate !== 0 ? 1 / point.rate : 0};
}

// ============================================================================
// RANGE HELPERS
// ============================================================================

/**
 * Ensure FX data for the given pair and date range is loaded into the cache.
 * Gap-detection + bulk fetch + merge — all in one call.
 *
 * @param slug   Pair slug in alphabetical order (e.g. "EUR-USD")
 * @param start  Start date YYYY-MM-DD (inclusive)
 * @param end    End date YYYY-MM-DD (inclusive)
 * @returns      All cached FxDataPoints in [start, end] after loading
 */
export async function ensureFxRangeLoaded(slug: string, start: string, end: string): Promise<FxDataPoint[]> {
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
            // Mark all fetched gaps so getMissingIntervals won't re-detect them
            for (const gap of gaps) store.markFetched(gap.start, gap.end);
        } catch (e: any) {
            if (e?.response?.status === 404) {
                // No rates available for this pair/range — mark fetched to avoid re-fetching
                for (const gap of gaps) store.markFetched(gap.start, gap.end);
            }
            // Network / 5xx errors: don't mark — allow retry on next call
        }
    }

    return store.getRange(start, end).data;
}

/**
 * Bulk-load FX data for multiple pairs in a single HTTP call.
 * Collects gaps from all pairs, issues one /fx/currencies/convert request,
 * and distributes results back to per-pair stores.
 *
 * @param requests  Array of { slug, start, end } for each pair
 * @returns         Map from slug to FxDataPoint[] (all cached data in [start, end])
 */
export async function ensureFxRangeLoadedBulk(requests: Array<{slug: string; start: string; end: string}>): Promise<Map<string, FxDataPoint[]>> {
    // Collect all gaps across all pairs
    type GapEntry = {slug: string; base: string; quote: string; gap: {start: string; end: string}};
    const allGaps: GapEntry[] = [];

    for (const req of requests) {
        const store = getFxStore(req.slug);
        const gaps = store.getMissingIntervals(req.start, req.end);
        if (gaps.length > 0) {
            const {base, quote} = parsePairSlug(req.slug);
            for (const gap of gaps) {
                allGaps.push({slug: req.slug, base, quote, gap});
            }
        }
    }

    // If there are gaps, fetch them all in one bulk call
    if (allGaps.length > 0) {
        const convertRequests = allGaps.map((entry) => ({
            from_amount: {code: entry.base, amount: '1'},
            to: entry.quote,
            date_range: {start: entry.gap.start, end: entry.gap.end},
        }));

        try {
            const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post(convertRequests);
            const results = (response as any)?.results ?? [];

            // Group results by pair slug for efficient store updates
            const pointsBySlug = new Map<string, FxDataPoint[]>();
            for (const result of results) {
                const fromCode = result.from_amount?.code;
                const toCode = result.to_amount?.code;
                if (!fromCode || !toCode) continue;
                const slug = createPairSlug(fromCode, toCode);
                const point = apiResultToFxDataPoint(result);
                if (!pointsBySlug.has(slug)) pointsBySlug.set(slug, []);
                pointsBySlug.get(slug)!.push(point);
            }

            // Merge results into each pair's store
            for (const [slug, points] of pointsBySlug) {
                if (points.length > 0) {
                    getFxStore(slug).merge(points);
                }
            }

            // Mark all gaps as fetched (even those with no results — avoids re-fetch)
            for (const entry of allGaps) {
                getFxStore(entry.slug).markFetched(entry.gap.start, entry.gap.end);
            }
        } catch (e: any) {
            if (e?.response?.status === 404) {
                // No rates for any pair — mark all fetched to avoid re-fetch
                for (const entry of allGaps) {
                    getFxStore(entry.slug).markFetched(entry.gap.start, entry.gap.end);
                }
            }
            // Network / 5xx errors: don't mark — allow retry
        }
    }

    // Return all cached data for each requested pair
    const resultMap = new Map<string, FxDataPoint[]>();
    for (const req of requests) {
        resultMap.set(req.slug, getFxStore(req.slug).getRange(req.start, req.end).data);
    }
    return resultMap;
}

/**
 * Async lookup with auto-fetch. Checks cache first, fetches from backend if miss.
 * Result is merged into TimeSeriesStore for future cache hits.
 * Returns null if the pair is not configured (404) or fetch fails.
 */
export async function lookupFxRate(base: string, quote: string, date: string): Promise<FxDataPoint | null> {
    const cached = lookupFxRateSync(base, quote, date);
    if (cached) return cached;

    const slug = createPairSlug(base, quote);
    const {base: canonBase, quote: canonQuote} = parsePairSlug(slug);
    try {
        const response = await zodiosApi.convert_currency_bulk_api_v1_fx_currencies_convert_post([
            {
                from_amount: {code: canonBase, amount: '1'},
                to: canonQuote,
                date_range: {start: date, end: date},
            },
        ]);
        const results = (response as any)?.results || [];
        if (results.length === 0) return null;
        const point = apiResultToFxDataPoint(results[0]);
        if (point.rate === 0) return null;
        // Merge into cache
        const store = getFxStore(slug);
        store.merge([point]);
        // Return in requested direction
        if (canonBase === base.toUpperCase()) return point;
        return {...point, rate: point.rate !== 0 ? 1 / point.rate : 0};
    } catch {
        return null;
    }
}
