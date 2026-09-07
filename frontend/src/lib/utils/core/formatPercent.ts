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
}

export function formatPercent(value: number | null | undefined, {scale = 1, signed = true, empty = '—', digits = 2}: FormatPercentOptions = {}): string {
    if (value == null || !Number.isFinite(value)) return empty;
    const scaled = value * scale;
    // `-0` survives arithmetic and prints as "-0.00%", which reads as a loss that
    // is not there. Two of the five copies guarded against it; now all do.
    const normalized = Object.is(scaled, -0) ? 0 : scaled;
    const sign = signed && normalized > 0 ? '+' : '';
    return `${sign}${normalized.toFixed(digits)}%`;
}
