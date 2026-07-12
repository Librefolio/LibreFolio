/**
 * Asset Price Store Registry — Global cache of TimeSeriesStore instances for asset prices.
 *
 * Provides a shared TimeSeriesStore<AssetPricePoint> for each (assetId, currency) pair.
 * The same instance is reused across range changes, so narrowing/expanding the date range
 * is instant when data is already cached (only gaps trigger API calls).
 *
 * Keys are "{assetId}:{currency}" (e.g. "42:EUR"). When target_currency conversion is
 * active, converted prices are cached separately from native-currency prices.
 *
 * @module stores/assetPriceStoreRegistry
 */

import {TimeSeriesStore} from './core/TimeSeriesStore';
import {zodiosApi} from '$lib/api';
// AssetPricePoint/apiPricesToAssetPricePoints now live in assetPriceDerived.ts (a
// Zodios/SvelteKit-free module, importable from a Web Worker) — re-exported here so
// existing call sites of this file don't need to change their import path.
import {apiPricesToAssetPricePoints, type AssetPricePoint} from '$lib/utils/assetPriceDerived';
export {apiPricesToAssetPricePoints, type AssetPricePoint};

// ============================================================================
// TYPES
// ============================================================================

// ============================================================================
// REGISTRY
// ============================================================================

const stores: Map<string, TimeSeriesStore<AssetPricePoint>> = new Map();

function storeKey(assetId: number, currency: string): string {
    return `${assetId}:${currency.toUpperCase()}`;
}

/**
 * Get or create a TimeSeriesStore for an asset in a specific currency.
 */
export function getAssetPriceStore(assetId: number, currency: string): TimeSeriesStore<AssetPricePoint> {
    const key = storeKey(assetId, currency);
    let store = stores.get(key);
    if (!store) {
        store = new TimeSeriesStore<AssetPricePoint>();
        stores.set(key, store);
    }
    return store;
}

/**
 * Invalidate ALL currency stores for a given asset (used after sync/refresh).
 */
export function invalidateAssetPriceStore(assetId: number): void {
    const prefix = `${assetId}:`;
    for (const [key, store] of stores) {
        if (key.startsWith(prefix)) {
            store.invalidateAll();
        }
    }
}

/**
 * Remove all stores for a given asset (used on asset deletion).
 */
export function removeAssetPriceStore(assetId: number): void {
    const prefix = `${assetId}:`;
    for (const key of stores.keys()) {
        if (key.startsWith(prefix)) {
            stores.delete(key);
        }
    }
}

// ============================================================================
// RANGE HELPERS
// ============================================================================

/**
 * Ensure asset price data for the given asset, currency, and date range is cached.
 * Gap-detection + fetch only missing intervals.
 *
 * @param assetId   Asset ID
 * @param currency  Effective currency (native if no conversion, target if converted)
 * @param start     Start date YYYY-MM-DD (inclusive)
 * @param end       End date YYYY-MM-DD (inclusive)
 * @param opts      Options: targetCurrency for server-side conversion
 * @returns         All cached AssetPricePoints in [start, end] after loading
 */
export async function ensureAssetPriceRangeLoaded(assetId: number, currency: string, start: string, end: string, opts?: {targetCurrency?: string}): Promise<AssetPricePoint[]> {
    const store = getAssetPriceStore(assetId, currency);
    const gaps = store.getMissingIntervals(start, end);

    if (gaps.length > 0) {
        // Fetch the full requested range (query_prices_bulk doesn't support multi-range)
        try {
            const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post([
                {
                    asset_id: assetId,
                    date_range: {start, end},
                    include_events: false,
                    target_currency: opts?.targetCurrency,
                },
            ]);
            const result = (response as any)?.items?.[0];
            const apiPrices = result?.prices ?? [];
            const points = apiPricesToAssetPricePoints(apiPrices);
            if (points.length > 0) store.merge(points);
            // Mark the full range as fetched (even if empty — avoids re-fetching)
            store.markFetched(start, end);
        } catch (e: any) {
            if (e?.response?.status === 404) {
                store.markFetched(start, end);
            }
            // Network / 5xx: don't mark — allow retry
        }
    }

    return store.getRange(start, end).data;
}
