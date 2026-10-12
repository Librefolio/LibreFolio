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
 */
import {uiLocale} from '$lib/stores/app/uiLocale';

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
