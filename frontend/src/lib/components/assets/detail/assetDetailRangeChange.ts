/**
 * The Δ of the asset page's price summary over the range on screen, read from the backend (X-R59, lot B).
 *
 * The summary shows the change from the first point of the range to the last price: the live quote when the range ends
 * today and the page shows one (`AssetDetailLive` asks it with the quote, `POST /assets/prices/current?range_start=`),
 * else the stored series' last close, whose change is asked here (`POST /assets/prices/period-changes`, one item). The
 * browser computes neither.
 *
 * @module components/assets/detail/assetDetailRangeChange
 */
import {zodiosApi} from '$lib/api';
import {assetRangeDelta, rangeStartFor, type RangeDelta} from '$lib/utils/rangeChange';

/** The Δ the price summary shows: the live quote's when the summary shows the live price, else the stored series'. Never the series' next to a live price. */
export function summaryRangeDelta(liveShown: boolean, live: RangeDelta | null, series: RangeDelta | null): RangeDelta {
    return (liveShown ? live : series) ?? {abs: null, pct: null};
}

/**
 * The stored series' Δ over the range `dateStart … asOf`, in `targetCurrency` when given (the chart's display currency,
 * when the chart is converted). No call, and no change, when the range has no day the backend would accept
 * (`rangeStartFor`); a failed call rejects, for the page to handle.
 */
export async function fetchSeriesRangeDelta(input: {assetId: number; asOf: string; dateStart: string; targetCurrency?: string | null}): Promise<RangeDelta> {
    const start = rangeStartFor(input.dateStart, input.asOf);
    if (start === null) return {abs: null, pct: null};
    const response = await zodiosApi.post('/api/v1/assets/prices/period-changes', [{asset_id: input.assetId, as_of: input.asOf, range_start: start, ...(input.targetCurrency ? {target_currency: input.targetCurrency} : {})}]);
    const item = (response.items ?? []).find((candidate) => candidate.asset_id === input.assetId);
    return assetRangeDelta(item?.range_change);
}
