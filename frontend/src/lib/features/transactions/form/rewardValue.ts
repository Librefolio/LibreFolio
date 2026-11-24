/**
 * The value on receipt the transaction form suggests for a REWARD (project 79, STK-2a): the asset's close of the day,
 * or the last one before it, from its stored price history. A suggestion only: the form fills an empty field with it,
 * marks it «from price history», and never overwrites a value the user typed. Without a stored price it suggests
 * nothing: no value is ever invented.
 *
 * The close is per `quote_base_quantity` units (a bond quoted per 100); the cost basis is per unit, so the close is
 * divided by the base through the form's one helper for it (`unitPriceFromAmount`), the declared frontend exception
 * of `txTradeAmount.ts`.
 */

import {zodiosApi} from '$lib/api';
import {unitPriceFromAmount} from './txTradeAmount';

/** A suggested value on receipt: per unit, in the price's currency, with the day of the close it comes from. */
export interface RewardValueSuggestion {
    code: string;
    amount: string;
    /** The day of the close read: the reward's day, or an earlier one when the history has a gap. */
    priceDate: string;
}

/** The price points the suggestion reads: the shape of `FAPricePoint` it needs. */
export interface RewardPricePoint {
    date: string;
    close: string | number | null | undefined;
    currency: string | null | undefined;
}

/**
 * The suggestion from the points a one-day price query returned (the backend fills a gap backward): the last point dated
 * on or before `date` with a positive close and a currency, per unit. `null` when there is none.
 */
export function rewardValueFromPoints(points: readonly RewardPricePoint[], date: string, quoteBaseQuantity: number | null | undefined): RewardValueSuggestion | null {
    let best: RewardPricePoint | null = null;
    for (const point of points) {
        if (point.date > date || !point.currency || point.close == null) continue;
        const close = String(point.close).trim();
        if (close === '' || !(Number(close) > 0)) continue;
        if (best == null || point.date >= best.date) best = point;
    }
    if (best == null || !best.currency) return null;
    const close = String(best.close).trim();
    const base = Number.isInteger(quoteBaseQuantity) && (quoteBaseQuantity ?? 0) > 1 ? (quoteBaseQuantity as number) : 1;
    const amount = base === 1 ? close : unitPriceFromAmount(String(base), close, 1);
    return {code: best.currency, amount, priceDate: best.date};
}

/** The suggestion for `assetId` on `date` (ISO day), read from its stored prices; `null` without one or on a failed read. */
export async function fetchRewardValue(assetId: number, date: string, quoteBaseQuantity: number | null | undefined): Promise<RewardValueSuggestion | null> {
    try {
        const response = await zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post([{asset_id: assetId, date_range: {start: date, end: date}, include_price: true, include_events: false}] as never);
        const items = (response as {items?: {asset_id: number; prices?: RewardPricePoint[]}[]}).items ?? [];
        const item = items.find((candidate) => candidate.asset_id === assetId);
        return item ? rewardValueFromPoints(item.prices ?? [], date, quoteBaseQuantity) : null;
    } catch {
        // A suggestion that cannot be read is no suggestion: the field stays empty and the missing-value warning shows.
        // The API client has already written the failure to the console (apiErrorConsole).
        return null;
    }
}
