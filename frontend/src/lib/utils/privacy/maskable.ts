/**
 * Privacy masking — formatter level (the load-bearing level of U2).
 *
 * Responsibility: decide, *before* the string exists, whether a caller receives the
 * real amount or the placeholder. Because the substitution happens upstream of the
 * markup, the position of the resulting node is irrelevant — a masked amount is safe
 * in a table cell, in an ECharts tooltip and in a `title` attribute alike.
 *
 * @module utils/privacy/maskable
 */

import {isPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';

/**
 * Placeholder substituted for a masked monetary amount.
 *
 * The placeholder itself is a constant: it carries nothing derived from the real value —
 * not the magnitude, not the digit count, not the sign. A placeholder whose width tracked
 * the amount would leak the order of magnitude of every masked figure.
 *
 * What the *rendered cell* discloses is a separate question, and the answer is not "nothing":
 * see `maskable` for the sign that callers deliberately keep outside the substitution.
 */
export const PRIVACY_PLACEHOLDER = '•••';

/**
 * Explicit classification of an amount at the formatter boundary.
 *
 * Two values, not the three of the D5 taxonomy: the *structural* class (quantities,
 * dates, counts) cannot reach a currency formatter by construction. Offering it here
 * would create a switch usable to silence the masking of real money.
 *
 * Omitted ⇒ `personal` ⇒ masked. Forgetting to classify a public value makes it
 * disappear, which the user reports; forgetting to classify a personal one would leave
 * it in the clear, which nobody sees.
 */
export type AmountSensitivity = 'personal' | 'public';

/**
 * Whether an amount with this classification must be replaced right now.
 *
 * `public` short-circuits before reading the store: a public amount never changes with
 * the privacy flag, so registering a reactive dependency on it would only cause
 * invalidations that cannot alter the output.
 */
export function shouldMaskAmount(sensitivity?: AmountSensitivity): boolean {
    return sensitivity !== 'public' && isPrivacyEnabled();
}

/**
 * Return either the formatted amount or the placeholder.
 *
 * The argument is the amount **without its sign prefix**, and that is a decision, not an
 * oversight. Masking the sign too was implemented first, on the argument that the sign is
 * derived from the value and reveals whether the holder is up or down — arguably the most
 * sensitive bit of a P&L figure. The argument was put to the product owner and rejected in
 * favour of readability (decision D8): a masked P&L column keeps `+•••` / `-•••`.
 *
 * What that costs, stated so nobody has to rediscover it: the rendered cell discloses
 * `sign(amount)`, which has **three** values, not two. Six call sites pass
 * `showSign: value !== 0`, so there the prefix is present exactly when the amount is
 * non-zero — and a masked column of period contributions therefore still shows which
 * periods had activity.
 *
 * Do not "fix" this by moving the sign back inside the mask: that reverses a decision with
 * an owner, and the owner took it with the objection on the table.
 */
export function maskable(formatted: string, sensitivity?: AmountSensitivity): string {
    return shouldMaskAmount(sensitivity) ? PRIVACY_PLACEHOLDER : formatted;
}

/** The parts of a number formatted by `Intl.NumberFormat` that carry its magnitude. */
const MAGNITUDE_PARTS: ReadonlySet<string> = new Set(['integer', 'group', 'decimal', 'fraction', 'compact', 'exponentSeparator', 'exponentMinusSign', 'exponentInteger', 'nan', 'infinity']);

/**
 * Mask the number inside an `Intl.NumberFormat#formatToParts` result, keeping the currency.
 *
 * `maskable` replaces a whole string, which is right for the D8 formatters: they append the
 * currency themselves, *after* masking. A formatter that lets `Intl` place the currency cannot
 * do that — the symbol sits inside the string, before or after the digits depending on the
 * locale — and masking its whole output hides the currency too. The product owner ruled that
 * out on 2026-09-22: privacy hides the number, not the currency.
 *
 * So this works on the parts. The run from the first to the last magnitude part — digits,
 * grouping and decimal separators, the compact suffix, and any literal between them — becomes
 * one placeholder; the currency, the sign and the literals around the number stay. `compact` is
 * inside the run on purpose: `€•••K` would disclose the order of magnitude the placeholder
 * exists to hide. The sign stays outside, as in D8 (see `maskable`).
 *
 * Unmasked, the result is the parts joined, which is exactly what `format` would return.
 */
export function maskCurrencyParts(parts: readonly Intl.NumberFormatPart[], sensitivity?: AmountSensitivity): string {
    const joined = parts.map((part) => part.value).join('');
    if (!shouldMaskAmount(sensitivity)) return joined;

    let first = -1;
    let last = -1;
    parts.forEach((part, index) => {
        if (!MAGNITUDE_PARTS.has(part.type)) return;
        if (first < 0) first = index;
        last = index;
    });
    if (first < 0) return joined;

    let result = '';
    parts.forEach((part, index) => {
        if (index < first || index > last) {
            result += part.value;
            return;
        }
        if (index === first) result += PRIVACY_PLACEHOLDER;
        // A currency placed inside the number by some locale is still the currency.
        if (part.type === 'currency') result += part.value;
    });
    return result;
}

/** A sign at the start of a formatted number, with the invisible bidi marks some locales write around it. */
const LEADING_SIGN = /^[\p{Cf}+\-\u2212]*/u;

/**
 * Mask an already formatted number, keeping its sign.
 *
 * For numbers that carry no currency and are not formatted through `Intl` parts — an axis tick
 * built by a shared helper, for instance. Everything after the leading sign is the magnitude,
 * compact suffix included, and becomes the placeholder. The sign stays outside, as in D8, and
 * is kept exactly as the locale wrote it (U+2212 in Swedish, a bidi mark before the hyphen in
 * Arabic): rebuilding it as an ASCII hyphen would change the unmasked output too.
 *
 * Absence is the caller's job, as with `maskable`: an em-dash handed in comes back masked, so
 * check for a missing value before calling (see `formatCurrencyAmount` in the risk helpers).
 */
export function maskFormattedNumber(formatted: string, sensitivity?: AmountSensitivity): string {
    if (!shouldMaskAmount(sensitivity)) return formatted;
    return `${LEADING_SIGN.exec(formatted)?.[0] ?? ''}${PRIVACY_PLACEHOLDER}`;
}

/**
 * Mask a quantity the user holds, formatted, where it sits next to a price (decision D5′).
 *
 * D5 left quantities visible: they were the reading key of a lot row, and masking the value
 * while showing the quantity was an accepted residual. On 2026-09-23 the product owner
 * revised it: a quantity is masked **where it sits next to a price** — positions and lots —
 * because quantity × public price rebuilds what the user owns, and it stays visible in
 * transactions. So the class of a quantity is decided by its context, not by its formatter:
 * the same number is masked in a lot and shown in a transaction. That is why this is a
 * separate name called at the site, and not a flag inside a shared quantity formatter.
 *
 * Behaves like `maskFormattedNumber` — the leading sign, written as the locale wrote it,
 * stays outside the placeholder — so a short position keeps its direction. Units and
 * tickers belong outside the argument, as the currency does for money. Absence is the
 * caller's job: pass a number, not an em-dash.
 */
export function maskableQuantity(formatted: string): string {
    return maskFormattedNumber(formatted);
}
