/**
 * txTradeAmount.ts — «Total amount / Unit price» of a BUY or SELL in the transaction form (#47).
 *
 * The form stores a quantity and an amount; the unit price is only another way of typing the amount. Switching between
 * the two is one multiplication or one division, so it is done here, in the browser, on the decimal text itself
 * (developer decision of 25/10/2026: the frontend does no complex calculation, but small sums and products are its
 * own). The backend never sees the unit price: it receives the amount, which it validates like any other.
 *
 * The convention is the whole app's, the market quote's (`financial_math/valuation.py`): `amount = quantity /
 * quote_base_quantity × price`. A bond quoted on base 100 is entered the way its quote is read. The result is rounded
 * half-even to the scale of the column that keeps it (an amount 6 decimals, a unit price 12), so what the form shows is
 * what is stored.
 *
 * ## Arithmetic
 *
 * Exact, on integers: every decimal is read as `coefficient × 10^-scale` (a `BigInt` and a count of fraction digits),
 * the product or the quotient is formed as one fraction, and that fraction is rounded once at the end. A `number` is
 * never used: with 15 significant digits a float already gets the decimals wrong. There is no library behind it.
 *
 * ## Who drives
 *
 * The driver is the value the user wrote last: the other one is calculated from it. It is `amount` until the user types
 * in the unit-price field; typing an amount (or switching the badge) hands it back to `amount`; a new quantity or asset
 * keeps whoever drives and recalculates the other.
 *
 * @financial-math-exception W5-9 (#47), the transaction form: the amount of a trade from the unit price the user types, or the unit price from the amount (quantity / quote_base_quantity × price), exact decimal arithmetic rounded half-even to the stored scales
 */
import {decimalDigitCounts, REAL_SIGNIFICANT_DIGITS} from '$lib/utils/core/parseDecimalInput';

/** The two values that can be typed. */
export type TradeAmountDriver = 'amount' | 'unit_price';
/** What the user touched: a field of the pair, or what the pair depends on. */
export type TradeAmountEdit = 'amount' | 'unit_price' | 'quantity' | 'asset';
/** Which value is calculated: the amount from the unit price, or the unit price from the amount. */
export type TradeAmountMode = 'price_to_amount' | 'amount_to_price';

export interface TradeAmountInput {
    driver: TradeAmountDriver;
    /** The asset's `quote_base_quantity`: how many units its market quote refers to. `null` when the asset is not known (yet). */
    quoteBaseQuantity: number | null | undefined;
    /** The quantity as typed, in canonical decimal form. */
    quantity: string;
    amount: string;
    unitPrice: string;
}

/** The value that follows from the one the user wrote: `mode` says which it is, `result` is a plain decimal. */
export interface TradeAmountResult {
    mode: TradeAmountMode;
    result: string;
}

/** The driver after the user touched something. */
export function driverAfterEdit(current: TradeAmountDriver, edit: TradeAmountEdit): TradeAmountDriver {
    if (edit === 'amount') return 'amount';
    if (edit === 'unit_price') return 'unit_price';
    return current;
}

/** The decimals each value keeps in the backend (`db/precision.py`): quantity 10, amount 6, unit price 12. */
const QUANTITY_DECIMALS = 10;
export const AMOUNT_DECIMALS = 6;
export const UNIT_PRICE_DECIMALS = 12;

/** A value to calculate from: a canonical positive decimal inside its column's limits. */
function isAskable(text: string, maxDecimals: number): boolean {
    const counts = decimalDigitCounts(text);
    if (counts === null || counts.stripped === '0' || counts.stripped.startsWith('-')) return false;
    return counts.fractionDigits <= maxDecimals && counts.significantDigits <= REAL_SIGNIFICANT_DIGITS;
}

/** A positive decimal text as `coefficient × 10^-scale`. Only called on text `isAskable` accepted: no sign, no exponent. */
function scaled(text: string): {coefficient: bigint; scale: number} {
    const [integer, fraction = ''] = text.split('.');
    return {coefficient: BigInt(`${integer || '0'}${fraction}`), scale: fraction.length};
}

/** `numerator / denominator` rounded half-even to an integer; both positive. */
function divideHalfEven(numerator: bigint, denominator: bigint): bigint {
    const quotient = numerator / denominator;
    const twiceRemainder = (numerator % denominator) * 2n;
    if (twiceRemainder > denominator || (twiceRemainder === denominator && quotient % 2n === 1n)) return quotient + 1n;
    return quotient;
}

/** An integer `coefficient × 10^-scale` as plain text: no exponent, no trailing zeros in the fraction, `0` for zero. */
function plain(coefficient: bigint, scale: number): string {
    if (coefficient === 0n) return '0';
    const digits = coefficient.toString().padStart(scale + 1, '0');
    const integer = digits.slice(0, digits.length - scale);
    const fraction = digits.slice(digits.length - scale).replace(/0+$/, '');
    return fraction === '' ? integer : `${integer}.${fraction}`;
}

/** `numerator / denominator` rounded half-even to `scale` decimals, as plain text. */
function ratio(numerator: bigint, denominator: bigint, scale: number): string {
    return plain(divideHalfEven(numerator * 10n ** BigInt(scale), denominator), scale);
}

/** The base the asset's quote refers to, as the backend reads it (`normalize_quote_base_quantity`): a missing or non-positive one is 1. */
function quoteBase(value: number): bigint {
    return Number.isInteger(value) && value > 0 ? BigInt(value) : 1n;
}

/** The amount of `quantity` units at `unitPrice` per `quoteBaseQuantity` units, rounded half-even to the amount's 6 decimals. */
export function amountFromUnitPrice(quantity: string, unitPrice: string, quoteBaseQuantity: number): string {
    const q = scaled(quantity);
    const p = scaled(unitPrice);
    return ratio(q.coefficient * p.coefficient, 10n ** BigInt(q.scale + p.scale) * quoteBase(quoteBaseQuantity), AMOUNT_DECIMALS);
}

/** The unit price (per `quoteBaseQuantity` units) that `amount` paid for `quantity` units, rounded half-even to the price's 12 decimals. */
export function unitPriceFromAmount(quantity: string, amount: string, quoteBaseQuantity: number): string {
    const q = scaled(quantity);
    const a = scaled(amount);
    return ratio(a.coefficient * 10n ** BigInt(q.scale) * quoteBase(quoteBaseQuantity), q.coefficient * 10n ** BigInt(a.scale), UNIT_PRICE_DECIMALS);
}

/**
 * The value that follows from the form's state, or `null` when there is nothing to calculate: the asset is not known
 * yet, or the quantity or the driving value is blank, zero, not positive, not a number, or past the limits the backend
 * keeps (quantity 10 decimals, amount 6, unit price 12, 15 significant digits). A refused value is already red in its
 * own field.
 */
export function calculateTradeValue(input: TradeAmountInput): TradeAmountResult | null {
    if (input.quoteBaseQuantity === undefined || input.quoteBaseQuantity === null || !isAskable(input.quantity, QUANTITY_DECIMALS)) return null;
    if (input.driver === 'unit_price') {
        return isAskable(input.unitPrice, UNIT_PRICE_DECIMALS) ? {mode: 'price_to_amount', result: amountFromUnitPrice(input.quantity, input.unitPrice, input.quoteBaseQuantity)} : null;
    }
    return isAskable(input.amount, AMOUNT_DECIMALS) ? {mode: 'amount_to_price', result: unitPriceFromAmount(input.quantity, input.amount, input.quoteBaseQuantity)} : null;
}
