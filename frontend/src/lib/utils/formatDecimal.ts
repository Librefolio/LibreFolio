/**
 * formatDecimal.ts — Display-only formatting helpers for decimal-string values
 * coming from the backend.
 *
 * The backend serializes monetary amounts and quantities as fixed-precision
 * decimal strings (e.g. "6.000000", "0.00000123"). Showing those raw in form
 * inputs is noisy: trailing zeros are visually heavy and convey false
 * precision. These helpers strip insignificant trailing zeros while
 * preserving any *significant* fractional digits the user supplied.
 *
 * Rules (Bugfix-4 §C14, §U18):
 * - Empty / null / non-numeric → returned unchanged.
 * - Integer values → no decimal point ("6").
 * - Values with significant fractional digits → keep all of them (no
 *   truncation), but remove trailing zeros and trailing dot.
 * - Optionally enforce a minimum number of fractional digits (e.g. 2 for
 *   currency display). When `minFrac > 0` and the value has fewer
 *   significant fractional digits, pad with zeros until `minFrac`.
 *
 * Important: these helpers operate on the *display* value only — the raw
 * string the user typed must be preserved by the caller during editing
 * (don't reformat mid-typing).
 */

export interface FormatDecimalOptions {
    /** Minimum number of fractional digits to display (default: 0 = no padding). */
    minFrac?: number;
    /** Maximum number of fractional digits to display (default: 8 = crypto-safe). */
    maxFrac?: number;
}

export function formatDecimalForDisplay(value: string | number | null | undefined, opts: FormatDecimalOptions = {}): string {
    if (value === null || value === undefined) return '';
    const raw = typeof value === 'number' ? String(value) : value;
    if (raw === '') return '';
    const trimmed = raw.trim();
    if (!/^-?\d*\.?\d*$/.test(trimmed)) return trimmed; // not a plain decimal — leave as-is

    const minFrac = Math.max(0, opts.minFrac ?? 0);
    const maxFrac = Math.max(minFrac, opts.maxFrac ?? 8);

    const negative = trimmed.startsWith('-');
    const unsigned = negative ? trimmed.slice(1) : trimmed;
    const [intPartRaw, fracPartRaw = ''] = unsigned.split('.');
    const intPart = intPartRaw === '' ? '0' : intPartRaw;

    // Strip trailing zeros from fractional part, then truncate to maxFrac.
    let frac = fracPartRaw.replace(/0+$/, '');
    if (frac.length > maxFrac) frac = frac.slice(0, maxFrac);
    // Pad up to minFrac (only if we actually have any fraction OR the caller
    // wants a forced minimum like 2 for currency).
    if (frac.length < minFrac && minFrac > 0) {
        frac = frac.padEnd(minFrac, '0');
    }

    const out = frac.length > 0 ? `${intPart}.${frac}` : intPart;
    return negative && out !== '0' ? `-${out}` : out;
}
