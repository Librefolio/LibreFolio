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
