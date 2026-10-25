/**
 * txTradeAmount.ts — the plumbing of «Total amount / Unit price» in the transaction form (#47).
 *
 * The form computes nothing: the other value comes from the backend (`POST /transactions/trade-amount`, one home in
 * `financial_math/trade_amount.py`). This file decides WHEN to ask and WHICH value drives, both pure.
 *
 * The driver is the value the user wrote last: the other one is calculated from it. It is `amount` until the user types
 * in the unit-price field; typing an amount (or switching the badge) hands it back to `amount`; a new quantity or asset
 * keeps whoever drives and recalculates the other.
 */
import {decimalDigitCounts, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';

/** The two values that can be typed. */
export type TradeAmountDriver = 'amount' | 'unit_price';
/** What the user touched: a field of the pair, or what the pair depends on. */
export type TradeAmountEdit = 'amount' | 'unit_price' | 'quantity' | 'asset';

/** The body of `POST /transactions/trade-amount`. */
export interface TradeAmountRequest {
    asset_id: number;
    quantity: string;
    mode: 'price_to_amount' | 'amount_to_price';
    value: string;
}

export interface TradeAmountInput {
    driver: TradeAmountDriver;
    assetId: number | null;
    /** The quantity as typed, in canonical decimal form. */
    quantity: string;
    amount: string;
    unitPrice: string;
}

/** The driver after the user touched something. */
export function driverAfterEdit(current: TradeAmountDriver, edit: TradeAmountEdit): TradeAmountDriver {
    if (edit === 'amount') return 'amount';
    if (edit === 'unit_price') return 'unit_price';
    return current;
}

/** The decimals each value keeps in the backend (`db/precision.py`): quantity 10, amount 6, unit price 12. */
const QUANTITY_DECIMALS = 10;
const AMOUNT_DECIMALS = 6;
const UNIT_PRICE_DECIMALS = 12;

/** A value the backend accepts to calculate from: a canonical positive decimal inside its column's limits. */
function isAskable(text: string, maxDecimals: number): boolean {
    const counts = decimalDigitCounts(text);
    if (counts === null || counts.stripped === '0' || counts.stripped.startsWith('-')) return false;
    return counts.fractionDigits <= maxDecimals && counts.significantDigits <= REAL_SIGNIFICANT_DIGITS;
}

/**
 * The request that follows from the form's state, or `null` when there is nothing to ask: no asset, a quantity or
 * a driving value that is blank, zero, not positive, not a number, or past the limits the backend keeps (quantity
 * 10 decimals, amount 6, unit price 12, 15 significant digits). A refused value is already red in its own field.
 */
export function planTradeAmountRequest(input: TradeAmountInput): TradeAmountRequest | null {
    if (input.assetId == null || !isAskable(input.quantity, QUANTITY_DECIMALS)) return null;
    if (input.driver === 'unit_price') {
        return isAskable(input.unitPrice, UNIT_PRICE_DECIMALS) ? {asset_id: input.assetId, quantity: input.quantity, mode: 'price_to_amount', value: input.unitPrice} : null;
    }
    return isAskable(input.amount, AMOUNT_DECIMALS) ? {asset_id: input.assetId, quantity: input.quantity, mode: 'amount_to_price', value: input.amount} : null;
}
