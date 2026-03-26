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

import type {TimeSeriesPoint} from './TimeSeriesStore';
import {TimeSeriesStore} from './TimeSeriesStore';
import type {ChainStep} from '$lib/utils/currencyGraph';

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
export function parsePairSlug(slug: string): { base: string; quote: string } {
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

