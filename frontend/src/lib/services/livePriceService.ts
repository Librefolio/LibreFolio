/**
 * livePriceService.ts — Shared utility for fetching live current prices.
 *
 * Single API wrapper used by:
 * - LiveTicker.svelte (dashboard, detail summary)
 * - Assets list page (cards + table)
 *
 * Always non-blocking: callers fire-and-forget via promises.
 */
import {axiosInstance} from '$lib/api';

export type LivePriceDirection = 'up' | 'down' | 'neutral';

export interface LivePriceResult {
    assetId: number;
    value: number | null;
    currency: string;
    source: string | null;
    error: string | null;
}

/**
 * Fetch current live prices for a list of asset IDs.
 * Wraps POST /api/v1/assets/prices/current.
 */
export async function fetchCurrentPrices(ids: number[]): Promise<LivePriceResult[]> {
    if (ids.length === 0) return [];
    const res = await axiosInstance.post('/api/v1/assets/prices/current', ids);
    const results: any[] = res.data?.results ?? [];
    return results.map((r: any) => ({
        assetId: r.asset_id,
        value: r.value != null ? parseFloat(r.value) : null,
        currency: r.currency ?? '',
        source: r.source ?? null,
        error: r.error ?? null,
    }));
}

/**
 * Compute price direction comparing current to previous value.
 */
export function computeDirection(current: number | null, prev: number | null): LivePriceDirection {
    if (current == null || prev == null || current === prev) return 'neutral';
    return current > prev ? 'up' : 'down';
}
