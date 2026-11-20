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
 * ## The total of a parent and its charges (project 66, F1)
 *
 * The form of a parent shows, under its linked charges, «Addebito totale» (cash out) or «Netto incassato» (cash in): the
 * trade amount plus or minus the charges, per currency. A read-only line, never a field: every voice is only itself, so
 * the trade amount never holds its charges (developer decisions of 12/11/2026), and there is no sum across currencies.
 *
 * @financial-math-exception W5-9 (#47), the transaction form: the amount of a trade from the unit price the user types, or the unit price from the amount (quantity / quote_base_quantity × price), exact decimal arithmetic rounded half-even to the stored scales; and (project 66, F1) the total of a parent with its linked charges, «Addebito totale» / «Netto incassato», one exact sum per currency of the amounts the user types
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

/**
 * The unit price a saved or pending row implies (W2-6, the read-only «unit price» column of the transactions table and the bulk
 * editor): `|amount| / |quantity| × quote_base_quantity`, through the same `calculateTradeValue` the form uses, never a second
 * formula. Signs do not matter (a SELL has a negative quantity and a positive cash, a BUY the opposite), so both sides are read
 * as magnitudes. `null` when the price cannot be calculated: a blank, zero or non-numeric quantity or amount, a value past the
 * limits the backend keeps, or an asset whose quote base is not known.
 */
export function rowUnitPrice(row: {quantity: string | null | undefined; amount: string | null | undefined; quoteBaseQuantity: number | null | undefined}): string | null {
    const quantity = magnitudeText(row.quantity);
    const amount = magnitudeText(row.amount);
    if (quantity === null || amount === null) return null;
    return calculateTradeValue({driver: 'amount', quoteBaseQuantity: row.quoteBaseQuantity, quantity, amount, unitPrice: ''})?.result ?? null;
}

/** A decimal text without its one leading sign, `null` for anything that is not text. */
function magnitudeText(text: string | null | undefined): string | null {
    if (typeof text !== 'string') return null;
    const trimmed = text.trim();
    return trimmed.startsWith('-') || trimmed.startsWith('+') ? trimmed.slice(1) : trimmed;
}

/**
 * Whether a transaction type has a unit price: it carries a quantity, a cash amount and an asset, all three (a BUY or SELL and
 * any single type like them). A leg of a pair has none, the caller excludes it.
 */
export function tradeHasUnitPrice(rule: {quantityMode: string; cashField: string; assetField: string}): boolean {
    return rule.quantityMode !== 'forbidden' && rule.cashField !== 'forbidden' && rule.assetField !== 'forbidden';
}

// ─── linked charges: the computed total of a parent (project 66, F1) ─────────────────────────────────────────────────

/** Which way a parent's cash goes: out for a BUY or a WITHDRAWAL, in for a SELL, DIVIDEND, INTEREST or DEPOSIT. */
export type CashDirection = 'out' | 'in';

/** An amount in canonical decimal text, like `TradeAmountInput` (a magnitude; one leading sign is ignored), with its currency. */
export interface CashLine {
    amount: string;
    currency: string | null | undefined;
}

/** A total in one currency, as plain decimal text. */
export interface CurrencyTotal {
    currency: string;
    amount: string;
}

/** A signed decimal text as `coefficient × 10^-scale`, or `null` when it is not a decimal inside an amount's limits. */
function signedAmount(text: string): {coefficient: bigint; scale: number} | null {
    const magnitude = magnitudeText(text)?.trim() ?? '';
    if (!isAmount(magnitude)) return null;
    return scaled(magnitude);
}

/** A magnitude inside an amount's limits (6 decimals, 15 significant digits); zero is allowed here. */
function isAmount(text: string): boolean {
    const counts = decimalDigitCounts(text);
    if (counts === null || counts.stripped.startsWith('-')) return false;
    return counts.fractionDigits <= AMOUNT_DECIMALS && counts.significantDigits <= REAL_SIGNIFICANT_DIGITS;
}

/**
 * «Addebito totale» (cash `out`) or «Netto incassato» (cash `in`) of a parent with its linked charges: per currency, the
 * trade amount plus (out) or minus (in) the charges in that currency. Every voice is only itself — the trade amount never
 * holds its charges — and there is no sum across currencies: one entry per currency, the trade's first, then the others
 * in the order the charges bring them. Exact, on the decimal text.
 *
 * A charge whose amount is still blank (a row just added) is skipped. `null` when there is nothing sure to show: the trade
 * amount blank or not a decimal, any typed amount not a decimal or past an amount's limits, or a counted line without a
 * currency.
 */
export function tradeTotalWithCharges(direction: CashDirection, trade: CashLine, charges: readonly CashLine[]): CurrencyTotal[] | null {
    if (trade.amount.trim() === '' || !trade.currency) return null;
    const totals = new Map<string, {coefficient: bigint; scale: number}>();
    const add = (currency: string, value: {coefficient: bigint; scale: number}, sign: 1n | -1n): void => {
        const current = totals.get(currency) ?? {coefficient: 0n, scale: 0};
        const scale = Math.max(current.scale, value.scale);
        const coefficient = current.coefficient * 10n ** BigInt(scale - current.scale) + sign * value.coefficient * 10n ** BigInt(scale - value.scale);
        totals.set(currency, {coefficient, scale});
    };
    const tradeValue = signedAmount(trade.amount);
    if (tradeValue === null) return null;
    add(trade.currency, tradeValue, 1n);
    for (const charge of charges) {
        if (charge.amount.trim() === '') continue;
        const value = signedAmount(charge.amount);
        if (value === null || !charge.currency) return null;
        add(charge.currency, value, direction === 'out' ? 1n : -1n);
    }
    return [...totals].map(([currency, {coefficient, scale}]) => ({currency, amount: signedPlain(coefficient, scale)}));
}

/** `plain` for a coefficient that may be negative. */
function signedPlain(coefficient: bigint, scale: number): string {
    return coefficient < 0n ? `-${plain(-coefficient, scale)}` : plain(coefficient, scale);
}
