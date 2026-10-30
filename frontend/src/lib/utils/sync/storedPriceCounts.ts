/**
 * The stored prices a sync would replace, counted by the server (X-R29 follow-up).
 *
 * `POST /assets/prices/stored-count` says, for each asset and the range a sync would ask for, how many prices are stored
 * and how many of them were entered by hand. The sync dialogs (the Assets list's, the selection's, the detail page's)
 * read it before Start, to warn and to name the manual ones.
 *
 * @module utils/sync/storedPriceCounts
 */

import {zodiosApi} from '$lib/api';

/** The endpoint's cap per request (`MAX_BULK_ITEMS`). */
const COUNT_ITEMS_PER_REQUEST = 1000;

export interface StoredPriceCount {
    stored: number;
    manual: number;
}

/**
 * The stored and manual price counts of `assetIds` over `range` (`start` may be `'min'`), by asset id. An asset is asked once,
 * 1 000 at most per request; one the answer leaves out is absent. Rejects when a request fails.
 */
export async function loadStoredPriceCounts(assetIds: readonly number[], range: {start: string; end: string}): Promise<Map<number, StoredPriceCount>> {
    const counts = new Map<number, StoredPriceCount>();
    const ids = [...new Set(assetIds)];
    for (let from = 0; from < ids.length; from += COUNT_ITEMS_PER_REQUEST) {
        const answer = await zodiosApi.count_stored_prices_api_v1_assets_prices_stored_count_post(ids.slice(from, from + COUNT_ITEMS_PER_REQUEST).map((assetId) => ({asset_id: assetId, date_range: {start: range.start, end: range.end}})));
        for (const item of answer.items ?? []) counts.set(item.asset_id, {stored: item.stored_count ?? 0, manual: item.manual_count ?? 0});
    }
    return counts;
}
