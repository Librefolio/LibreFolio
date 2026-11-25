/**
 * The value on receipt of a REWARD, read from the asset's stored price history (project 79): the transaction form's
 * suggestion (STK-2a) and the bulk workspace's «fill from price history» (STK-4b) ask the same backend reader,
 * `POST /assets/prices/reward-values`. Its rule is the domain consultant's: the close of that very day, never the day
 * before or after, per unit (the backend divides by the quote base), in the price's own currency. Without a close that
 * day nothing is suggested: no value is ever invented.
 */

import {zodiosApi} from '$lib/api';
import {compareDecimal} from '$lib/utils/core/exactDecimal';

/** A value on receipt read from the price history: per unit, in the price's currency, with the day of the close. */
export interface RewardValueSuggestion {
    code: string;
    amount: string;
    /** The day of the close read: always the reward's own day. */
    priceDate: string;
}

/** What the history gives for one reward: a value, no close that day, or no stored price at all. */
export type RewardValueStatus = 'FILLED' | 'NO_PRICE_THAT_DAY' | 'NO_HISTORY';

/** One reward asked for. */
export interface RewardValueRequest {
    assetId: number;
    date: string;
}

/** The answer for one reward, in the order asked. */
export interface RewardValueAnswer extends RewardValueRequest {
    status: RewardValueStatus;
    suggestion: RewardValueSuggestion | null;
}

/** The most items one request carries (the backend's `MAX_BULK_ITEMS`); a longer list goes in several requests. */
export const REWARD_VALUES_BATCH = 1000;

type RawAnswer = {asset_id: number; date: string; status: RewardValueStatus; value?: {code: string; amount: string | number} | null};

function toAnswer(raw: RawAnswer): RewardValueAnswer {
    const value = raw.status === 'FILLED' && raw.value ? {code: raw.value.code, amount: String(raw.value.amount), priceDate: raw.date} : null;
    return {assetId: raw.asset_id, date: raw.date, status: value ? 'FILLED' : raw.status === 'FILLED' ? 'NO_PRICE_THAT_DAY' : raw.status, suggestion: value};
}

/** The values on receipt of `requests`, in their order; `null` when a request fails (the API client logs it). */
export async function fetchRewardValues(requests: readonly RewardValueRequest[]): Promise<RewardValueAnswer[] | null> {
    const answers: RewardValueAnswer[] = [];
    try {
        for (let start = 0; start < requests.length; start += REWARD_VALUES_BATCH) {
            const batch = requests.slice(start, start + REWARD_VALUES_BATCH).map((request) => ({asset_id: request.assetId, date: request.date}));
            const response = await zodiosApi.query_reward_values_api_v1_assets_prices_reward_values_post(batch as never);
            answers.push(...((response as {items?: RawAnswer[]}).items ?? []).map(toAnswer));
        }
    } catch {
        // A failed read fills nothing: the caller says so. The API client has already written it to the console (apiErrorConsole).
        return null;
    }
    return answers;
}

/** The suggestion for `assetId` on `date` (ISO day); `null` without a close that day or on a failed read. */
export async function fetchRewardValue(assetId: number, date: string): Promise<RewardValueSuggestion | null> {
    const answers = await fetchRewardValues([{assetId, date}]);
    return answers?.find((answer) => answer.assetId === assetId && answer.date === date)?.suggestion ?? null;
}

/** Whether two values on receipt are the same number in the same currency (`61.250000` is `61.25`); an empty one equals nothing. */
export function sameRewardValue(left: {code: string; amount: string} | null | undefined, right: {code: string; amount: string} | null | undefined): boolean {
    return left != null && right != null && left.code === right.code && compareDecimal(left.amount, right.amount) === 0;
}
