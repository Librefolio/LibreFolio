/**
 * txTradeAmountApi.ts — the one call of «Total amount / Unit price» (#47): `POST /transactions/trade-amount`.
 *
 * Never throws: a refusal or a network failure answers `null` and the form leaves the calculated field empty.
 */
import {zodiosApi} from '$lib/api';
import {trySave} from '$lib/utils/trySave';
import type {TradeAmountRequest} from './txTradeAmount';

/** What the backend calculated: the other value as a plain decimal, and the asset's quote base it used. */
export interface TradeAmountResult {
    result: string;
    quote_base_quantity: number;
}

export async function convertTradeAmount(request: TradeAmountRequest): Promise<TradeAmountResult | null> {
    // `toast: false`: the form just leaves the calculated field empty; an unexpected failure reaches the console through
    // the API client (H-60), never through this wrapper.
    const saved = await trySave(() => zodiosApi.trade_amount_api_v1_transactions_trade_amount_post(request), {fallback: 'Trade amount failed', toast: false});
    if (saved.status === 'error') return null;
    const answer = saved.data;
    if (typeof answer?.result !== 'string') return null;
    return {result: answer.result, quote_base_quantity: answer.quote_base_quantity};
}
