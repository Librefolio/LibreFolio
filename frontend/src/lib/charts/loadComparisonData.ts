/**
 * Shared utility for loading comparison asset data (prices + events).
 *
 * Used by both asset detail and FX detail pages to avoid duplication.
 * Fetches price data and events for asset-comparison signals, injects
 * resolved data into signal configs, and returns a map of comparison events.
 *
 * @module charts/loadComparisonData
 */

import {zodiosApi} from '$lib/api';
import type {SignalConfig} from '$lib/charts/signals';

export interface ComparisonAssetMeta {
    id: number;
    display_name: string;
    icon_url?: string | null;
    asset_type?: string | null;
}

/**
 * Load comparison asset data (prices + events) for the given signals.
 *
 * @param compSignals - Signal configs of type 'asset-comparison'
 * @param dateRange - Start/end date range for the query
 * @param allAssets - Full asset list (for metadata lookup)
 * @param existingEvents - Current comparison events map (merged into)
 * @param excludeAssetId - Asset ID to exclude from loading (the page's own asset)
 * @returns Updated comparison events map
 */
export async function loadComparisonAssetsData(
    compSignals: SignalConfig[],
    dateRange: { start: string; end: string },
    allAssets: ComparisonAssetMeta[],
    existingEvents: Map<number, any[]>,
    excludeAssetId?: number,
): Promise<Map<number, any[]>> {
    const idsToLoad = compSignals
        .map(s => Number(s.params.assetId))
        .filter(id => id > 0 && id !== excludeAssetId);
    if (idsToLoad.length === 0) return existingEvents;

    const queries = idsToLoad.map(id => ({
        asset_id: id,
        date_range: {start: dateRange.start, end: dateRange.end},
        include_events: true,
    }));
    const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post(queries);
    const items = (response as any)?.items ?? [];
    const newCompEvents = new Map<number, any[]>(existingEvents);

    for (const result of items) {
        const aid = result.asset_id;
        const prices = (result.prices ?? []).map((p: any) => ({date: p.date, value: Number(p.close ?? 0)}));
        const assetMeta = allAssets.find(a => a.id === aid);
        for (const cfg of compSignals) {
            if (Number(cfg.params.assetId) === aid) {
                cfg.params._resolvedData = prices;
                cfg.params._assetIconUrl = assetMeta?.icon_url ?? null;
                cfg.params._assetType = assetMeta?.asset_type ?? null;
            }
        }
        newCompEvents.set(aid, result.events ?? []);
    }

    return newCompEvents;
}

