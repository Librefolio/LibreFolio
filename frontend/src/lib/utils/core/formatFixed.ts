/**
 * The localized `toFixed`: a number with a fixed count of decimals, written the way the interface
 * language writes numbers — its decimal mark and its grouping — instead of always with a dot.
 *
 * `toFixed` goes through no locale, so in Italian, French or Spanish it printed `9.2` next to
 * amounts written `4788,01` (M-18). This is the one place a bare figure gets its digits; the
 * percentages build on it through `formatPercent`.
 *
 * - `digits` is exact, as with `toFixed`; with `trim` it becomes a maximum and trailing zeros go,
 *   which is what `toFixed(n).replace(/\.?0+$/, '')` did.
 * - The digits are `toFixed`'s, rounding included; Intl only writes them. `-0` prints as `0`.
 * - `signed` writes `+` before a positive value; zero and negatives carry no added sign.
 * - `locale` defaults to the interface locale (`uiLocale()`); a legacy component passes
 *   `$uiLocaleStore` read in its template.
 *
 * `formatExactDecimal` is its sibling for an exact decimal — a backend decimal string, a
 * quantity, a rate, a split ratio — which must never go through a float.
 */
import {uiLocale} from '$lib/stores/app/uiLocale';
import {formatDecimalForDisplay} from './formatDecimal';

export interface FormatFixedOptions {
    /** Prefix positive values with `+`. */
    signed?: boolean;
    /** Drop trailing zeros: `digits` becomes the maximum. */
    trim?: boolean;
    /** Locale to write in; defaults to the interface locale. */
    locale?: string;
}

export function formatFixed(value: number, digits: number, {signed = false, trim = false, locale = uiLocale()}: FormatFixedOptions = {}): string {
    const normalized = Object.is(value, -0) ? 0 : value;
    // Rounded by `toFixed` first: Intl rounds the shortest decimal that reads back as the value
    // (`1.45` → `1.5`), `toFixed` the value itself (`1.4499…` → `1.4`), and the digits must stay
    // the ones the app printed before. A tiny negative keeps its minus (`-0.00`), as with `toFixed`.
    const rounded = Number(normalized.toFixed(digits));
    const text = rounded.toLocaleString(locale, {minimumFractionDigits: trim ? 0 : digits, maximumFractionDigits: digits});
    return signed && normalized > 0 ? `+${text}` : text;
}

export interface FormatExactDecimalOptions {
    /** Pad the fraction to at least this many digits (default 0). */
    minFrac?: number;
    /** Cut the fraction after this many digits — truncated, never rounded (default 8). */
    maxFrac?: number;
    /** Locale to write in; defaults to the interface locale. */
    locale?: string;
}

/**
 * An exact decimal written in the interface locale (M-18): the digits are those of
 * `formatDecimalForDisplay` — cut at `maxFrac`, trailing zeros dropped, padded to `minFrac`,
 * `-0` read as `0` — and Intl only writes them, with the locale's decimal mark, grouping and
 * minus. Intl is handed the decimal as a STRING, so no digit is lost beyond float precision.
 *
 * Empty input gives `''`, and anything that is not a plain decimal comes back as
 * `formatDecimalForDisplay` returns it. For display only: a value an input must read back stays
 * with `formatDecimalForDisplay`, which round-trips through `normalizeDecimalInput`.
 */
export function formatExactDecimal(value: string | number | null | undefined, {minFrac = 0, maxFrac = 8, locale = uiLocale()}: FormatExactDecimalOptions = {}): string {
    const plain = formatDecimalForDisplay(value, {minFrac, maxFrac});
    if (!/^-?\d+(\.\d+)?$/.test(plain)) return plain;
    const digits = plain.split('.')[1]?.length ?? 0;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(plain as Intl.StringNumericLiteral);
}

/** The most decimals a price shows: what `price_history` keeps (C-97a). */
const PRICE_MAX_DECIMALS = 12;
/** The significant digits a price shows at least, so one under a cent never reads `0,00` (D-C97c-1). */
const PRICE_SIGNIFICANT_DIGITS = 4;

export interface PriceDecimalsOptions {
    /** Decimals always shown, padded with zeros (default 2). */
    minDecimals?: number;
    /** Decimals a value may show before its trailing zeros drop, whatever its size, so a site keeps the range it showed
     *  (the data editor 0–4, the running average 2–4). Defaults to `minDecimals`. */
    floorDecimals?: number;
}

export interface FormatPriceOptions extends PriceDecimalsOptions {
    /** Prefix positive values with `+`; zero and negatives carry no added sign. */
    signed?: boolean;
    /** Locale to write in; defaults to the interface locale. */
    locale?: string;
}

/**
 * The fraction digits a price shows (C-97c, decision D-C97c-1): as many as 4 significant digits need, never fewer than
 * `floorDecimals`, never more than 12; `min` is `minDecimals`, the digits always shown. `0.0000034573` → 2…9, `123.45`
 * → 2…2, `0.5` → 2…4. For a formatter that writes the amount itself, such as `formatCurrencyAmountPlain`.
 */
export function priceFractionDigits(value: number | string, {minDecimals = 2, floorDecimals = minDecimals}: PriceDecimalsOptions = {}): {min: number; max: number} {
    const magnitude = Math.abs(Number(value));
    const significant = magnitude > 0 && Number.isFinite(magnitude) ? PRICE_SIGNIFICANT_DIGITS - 1 - Math.floor(Math.log10(magnitude)) : 0;
    const max = Math.min(PRICE_MAX_DECIMALS, Math.max(minDecimals, floorDecimals, significant));
    return {min: Math.min(minDecimals, max), max};
}

/**
 * A price written in the interface locale with the digits of `priceFractionDigits` (C-97c): `0.0000034573` →
 * `0,000003457`, `1.23456` → `1,235`, `65000.123` → `65.000,12`, `0.5` → `0,50`; an exchange rate passes
 * `minDecimals: 4`. A string is written exactly (Intl is handed it as a string literal), a number as the number it is;
 * `-0` prints as `0`. `''` for a value that is empty, not a number or not finite: it never echoes its input, so all it
 * writes is digits and the locale's marks.
 */
export function formatPrice(value: number | string | null | undefined, {signed = false, locale = uiLocale(), ...digits}: FormatPriceOptions = {}): string {
    if (value === null || value === undefined || value === '') return '';
    const number = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(number)) return '';
    const {min, max} = priceFractionDigits(number, digits);
    const literal = number === 0 ? 0 : typeof value === 'string' ? (value.trim() as Intl.StringNumericLiteral) : number;
    return new Intl.NumberFormat(locale, {minimumFractionDigits: min, maximumFractionDigits: max, signDisplay: signed ? 'exceptZero' : 'auto'}).format(literal);
}
