/**
 * Percentages, formatted the same way everywhere.
 *
 * This replaced five private copies that were **not** the same function. Two of
 * them received a value already expressed in percent (0-100) and printed it as
 * is; the other three received a fraction (0-1) and multiplied by 100. Unifying
 * them on either behaviour would have moved every affected number by a factor of
 * a hundred — the same trap `safeNumber` and `safeNum` set earlier in this
 * codebase, where one is a type guard and the other a parser.
 *
 * The difference is not a reason for two functions, though: it is a parameter
 * the *caller* knows and the callee cannot. So it says so, once, at the call
 * site, and `scale` defaults to 1 because "the number I hand you is already a
 * percentage" is the reading that needs no arithmetic.
 *
 * The other three differences were smaller and are options too: whether a
 * positive value gets a `+`, what to print when the value is missing, and how
 * many decimals. The `-0` guard was in only two of the copies and is now in all
 * of them — a negative zero prints as "-0.00%", which no user has ever wanted.
 *
 * ## Why `suffix` exists
 *
 * Because the unit is not always `%`. A *difference* between two percentages is
 * measured in **percentage points**: a holding weighing 20% of a portfolio and
 * producing 80% of its risk differs by `+60pp`, and writing that `+60%` states
 * a different quantity. The two units look alike and are not, which is the same
 * shape of trap as `scale` above.
 *
 * The illustration is round and invented on purpose. A real weight or risk
 * share integrates over the query window that produced it, so a measured pair
 * written here would go on reading as a fact long after it stopped being one —
 * and this file is generic, so nobody arriving in it has the context to doubt it.
 *
 * Before this option the callers that needed `pp` had no way to ask for it, so
 * they hand-rolled `toFixed` and lost the `-0` guard, the missing-value
 * placeholder and the sign rule along with it. The alternative on offer was
 * `formatPercent(...).replace('%', 'pp')`, which is worse than the problem: it
 * rewrites a *formatted* string, so it also mangles any placeholder or future
 * separator that happens to contain a `%`.
 */

export interface FormatPercentOptions {
    /** Multiplier applied before formatting: 1 when the value is already a
     *  percentage, 100 when it is a fraction. */
    scale?: number;
    /** Prefix positive values with `+`. Charts comparing against a baseline want
     *  this; a plain "share of total" does not. */
    signed?: boolean;
    /** Printed when the value is null, undefined or not finite. */
    empty?: string;
    /** Digits after the decimal point. */
    digits?: number;
    /**
     * Unit written after the number. Defaults to `%`.
     *
     * Pass `'pp'` for a difference between two percentages, and `''` for a bare
     * number. `empty` is returned untouched, so the placeholder never acquires a
     * unit it cannot carry.
     */
    suffix?: string;
}

export function formatPercent(value: number | null | undefined, {scale = 1, signed = true, empty = '—', digits = 2, suffix = '%'}: FormatPercentOptions = {}): string {
    if (value == null || !Number.isFinite(value)) return empty;
    const scaled = value * scale;
    // `-0` survives arithmetic and prints as "-0.00%", which reads as a loss that
    // is not there. Two of the five copies guarded against it; now all do.
    const normalized = Object.is(scaled, -0) ? 0 : scaled;
    const sign = signed && normalized > 0 ? '+' : '';
    return `${sign}${normalized.toFixed(digits)}${suffix}`;
}
