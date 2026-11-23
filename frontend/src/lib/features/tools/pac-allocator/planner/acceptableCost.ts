/**
 * The table «Maximum acceptable cost» of the Rebalancer's target fidelity (decisioni-REB §7.3; R1-F (b) of project 67).
 *
 * A plan scores `J = λ·D/F + (F − W)`. Moving `d` misplaced euros back to their target shortens the distance `D` by about
 * `2·d²`, so a plan accepts to spend up to `2·λ·d²/F` for it: one row per amount of misplaced money, one column per
 * fidelity level. The rows are 1 %, 2.5 %, 5 % and 10 % of the plan's total `F`, rounded to two significant digits; the
 * reference row is the 5 % one. «Custom» turns the euros typed on that row into `λ = x·F / (2·d_ref²)`, with `d_ref` the
 * figure **shown** in the row, rounded to six significant digits (`LAMBDA_SIGNIFICANT_DIGITS`): `λ` travels to the plan as
 * a decimal, and the column and the field's euros are computed from that rounded `λ`, never from the euros typed, so
 * what the table shows is what the plan runs on.
 *
 * **Where the numbers come from.** `F` and the λ of the three levels are the backend preview's (`total`,
 * `fidelity_level_weights`): the plan reads the same λ through its normalizer, so they have one home there. This module
 * only combines them, on the spot, so a figure typed or a level chosen changes the table at once, with no call (the
 * developer's «istantaneo», R1-F (b)). The plan never reads the table: it reads `λ`.
 *
 * **Arithmetic.** Exact rationals on `BigInt`: `F` may be an exact ratio with no decimal form (an FX rate), so it is read
 * from its numerator and denominator, never from its display text. Every cell is returned as a wire-shaped exact number
 * (a terminating decimal, or a reduced ratio marked non-authoritative for display), so the planner's formatters
 * (`format.ts`) show and mask it as they show the backend's amounts. Rounding is half up, as the backend's was.
 *
 * @financial-math-exception R1-F (b) of project 67 (developer decision of 21/11/2026), the Rebalancer's Strategy step: the table «Maximum acceptable cost» — rows of misplaced money at 1 %, 2.5 %, 5 % and 10 % of the preview's total to two significant digits, 2·λ·d²/F per fidelity level, and the custom λ from the euros the user types on the reference row, x·F/(2·d²) to six significant digits; exact rationals on BigInt
 */
import {canonicalDecimal, canonicalInput, decimalSign, roundRatio} from '$lib/utils/core/exactDecimal';
import type {PlannerExactMoney, PlannerExactNumber} from './types';

/** The significant digits of a «custom» λ computed from euros (B4, the consultant's Q1): a ppm at most on every cell. */
export const LAMBDA_SIGNIFICANT_DIGITS = 6;
/** The reference row: the 5 % one, the third. */
const REFERENCE_ROW_INDEX = 2;
/** The longest decimal the plan's request accepts for λ (`PlannerPositiveDecimal`, 96 characters). */
const MAX_LAMBDA_CHARS = 96;
/** The digits of a non-terminating cell's display text (non-authoritative: the formatters round the ratio itself). */
const DISPLAY_SCALE = 18;

/** The λ of the three levels, as the preview gives them (`fidelity_level_weights`). */
export interface FidelityLevelWeights {
    cost_aware: PlannerExactNumber;
    balanced: PlannerExactNumber;
    faithful: PlannerExactNumber;
}

/** One row: misplaced money and, per level, the most a plan accepts to spend to put it back; `custom` only with a λ. */
export interface AcceptableCostRow {
    misplaced: PlannerExactMoney;
    reference: boolean;
    cost_aware: PlannerExactMoney;
    balanced: PlannerExactMoney;
    faithful: PlannerExactMoney;
    custom: PlannerExactMoney | null;
}

const LEVELS = ['cost_aware', 'balanced', 'faithful'] as const;

/** A reduced rational, the denominator positive. */
interface Ratio {
    n: bigint;
    d: bigint;
}

function gcd(a: bigint, b: bigint): bigint {
    let x = a < 0n ? -a : a;
    let y = b;
    while (y !== 0n) [x, y] = [y, x % y];
    return x;
}

function ratio(n: bigint, d: bigint): Ratio {
    if (d === 0n) throw new RangeError('zero denominator');
    const sign = d < 0n ? -1n : 1n;
    const g = gcd(n, d) || 1n;
    return {n: (sign * n) / g, d: (sign * d) / g};
}

const mul = (a: Ratio, b: Ratio): Ratio => ratio(a.n * b.n, a.d * b.d);
const div = (a: Ratio, b: Ratio): Ratio => ratio(a.n * b.d, a.d * b.n);
/** -1, 0 or 1 as `a` is below, equal to or above `b`. */
const compare = (a: Ratio, b: Ratio): number => {
    const left = a.n * b.d;
    const right = b.n * a.d;
    return left === right ? 0 : left < right ? -1 : 1;
};
const pow10 = (k: number): Ratio => (k >= 0 ? ratio(10n ** BigInt(k), 1n) : ratio(1n, 10n ** BigInt(-k)));

/** A plain decimal text as a rational, or `null`. */
function ratioOfDecimal(text: string): Ratio | null {
    const canonical = canonicalDecimal(text);
    if (canonical === null) return null;
    const negative = canonical.startsWith('-');
    const [whole, fraction = ''] = (negative ? canonical.slice(1) : canonical).split('.');
    const magnitude = BigInt(whole + fraction);
    return ratio(negative ? -magnitude : magnitude, 10n ** BigInt(fraction.length));
}

/** An exact wire number as a rational: a ratio from its numerator and denominator, never from its display text. */
function ratioOf(value: PlannerExactNumber): Ratio | null {
    if (value.kind === 'finite_decimal') return ratioOfDecimal(value.value);
    if (!/^-?\d+$/.test(value.numerator) || !/^\d+$/.test(value.denominator) || BigInt(value.denominator) === 0n) return null;
    return ratio(BigInt(value.numerator), BigInt(value.denominator));
}

/** The decimal text of a rational whose denominator has only the factors 2 and 5; `null` for any other. */
function terminatingText(value: Ratio): string | null {
    let rest = value.d;
    let twos = 0;
    let fives = 0;
    while (rest % 2n === 0n) [rest, twos] = [rest / 2n, twos + 1];
    while (rest % 5n === 0n) [rest, fives] = [rest / 5n, fives + 1];
    if (rest !== 1n) return null;
    const scale = Math.max(twos, fives);
    const scaled = (value.n * 10n ** BigInt(scale)) / value.d;
    const negative = scaled < 0n;
    const digits = (negative ? -scaled : scaled).toString().padStart(scale + 1, '0');
    const text = scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
    return (negative ? '-' : '') + (canonicalDecimal(text) ?? text);
}

/** A rational as the wire's exact number: a decimal when it terminates, else the reduced ratio with a display text. */
function exactNumber(value: Ratio): PlannerExactNumber {
    const text = terminatingText(value);
    if (text !== null) return {kind: 'finite_decimal', value: text};
    const display = roundRatio(value.n.toString(), value.d.toString(), DISPLAY_SCALE) ?? '0';
    const dot = display.indexOf('.');
    return {
        kind: 'exact_ratio',
        numerator: value.n.toString(),
        denominator: value.d.toString(),
        display_decimal: display,
        display_scale: dot < 0 ? 0 : display.length - dot - 1,
        display_authority: 'non_authoritative',
    };
}

function money(value: Ratio, currency: string): PlannerExactMoney {
    return {value: exactNumber(value), currency};
}

/**
 * `value` rounded to `digits` significant digits, half up (two digits: 134.57 → 130, 335 → 340, 995 → 1 000); zero stays
 * zero. A negative value or fewer than one digit is refused: the table's rows and λ are positive quantities.
 */
function significant(value: Ratio, digits: number): Ratio {
    if (value.n < 0n) throw new RangeError('significant digits of a negative value');
    if (!Number.isInteger(digits) || digits < 1) throw new RangeError('at least one significant digit');
    if (value.n === 0n) return value;
    const top = pow10(digits);
    const bottom = pow10(digits - 1);
    let k = 0;
    while (compare(div(value, pow10(k)), top) >= 0) k += 1;
    while (compare(div(value, pow10(k)), bottom) < 0) k -= 1;
    const mantissa = div(value, pow10(k));
    const whole = mantissa.n / mantissa.d;
    const rounded = whole + ((mantissa.n - whole * mantissa.d) * 2n >= mantissa.d ? 1n : 0n);
    return mul(ratio(rounded, 1n), pow10(k));
}

/** The four rows' shares of the total: 1 %, 2.5 %, 5 %, 10 % (§7.3). */
const ROW_SHARES: readonly Ratio[] = [ratio(1n, 100n), ratio(1n, 40n), ratio(1n, 20n), ratio(1n, 10n)];

/** The four rows of misplaced money on `total`, each to two significant digits. */
function rows(total: Ratio): Ratio[] {
    return ROW_SHARES.map((share) => significant(mul(total, share), 2));
}

/** `2·λ·d²/F`: the most a plan accepts to spend to put `misplaced` back, at fidelity `λ`, on a total `F`. */
function maxCost(lambda: Ratio, misplaced: Ratio, total: Ratio): Ratio {
    return div(mul(mul(ratio(2n, 1n), lambda), mul(misplaced, misplaced)), total);
}

/** A positive total of the preview as a rational; `null` for anything else (no table without one). */
function positiveTotal(total: PlannerExactMoney): Ratio | null {
    const value = ratioOf(total.value);
    return value !== null && value.n > 0n ? value : null;
}

/** A positive λ written as decimal text (the draft's, or a level's), or `null`. */
function positiveLambda(text: string | null | undefined): Ratio | null {
    const canonical = canonicalInput(text);
    if (canonical === null || decimalSign(canonical) !== 1) return null;
    return ratioOfDecimal(canonical);
}

/**
 * The table on the preview's `total`, with the λ of the levels it gave; the «Custom» column from `customLambda`, the
 * draft's λ, when it is a positive decimal. `null` when the total is not positive or a level's λ cannot be read.
 */
export function acceptableCostTable(total: PlannerExactMoney, levels: FidelityLevelWeights, customLambda: string | null): AcceptableCostRow[] | null {
    const wealth = positiveTotal(total);
    if (wealth === null) return null;
    const weights = LEVELS.map((level) => ratioOf(levels[level]));
    if (weights.some((weight) => weight === null || weight.n <= 0n)) return null;
    const custom = positiveLambda(customLambda);
    return rows(wealth).map((misplaced, index) => {
        const [costAware, balanced, faithful] = weights.map((weight) => money(maxCost(weight as Ratio, misplaced, wealth), total.currency));
        return {
            misplaced: money(misplaced, total.currency),
            reference: index === REFERENCE_ROW_INDEX,
            cost_aware: costAware,
            balanced,
            faithful,
            custom: custom === null ? null : money(maxCost(custom, misplaced, wealth), total.currency),
        };
    });
}

/** The reference row's misplaced money on `total` (what «Custom»'s sentence names); `null` without a positive total. */
export function referenceMisplaced(total: PlannerExactMoney): PlannerExactMoney | null {
    const wealth = positiveTotal(total);
    return wealth === null ? null : money(rows(wealth)[REFERENCE_ROW_INDEX], total.currency);
}

/**
 * «Custom»: the λ, as decimal text, that accepts to spend `euros` to put the reference row's money back on `total`,
 * `x·F / (2·d_ref²)` to six significant digits. `null` when the euros are not a positive figure, without a positive
 * total, or when the λ would not fit the plan's request (the step then keeps «Custom» without a λ, a problem of the step).
 */
export function lambdaFromReferenceAmount(total: PlannerExactMoney, euros: string): string | null {
    const wealth = positiveTotal(total);
    const amount = positiveLambda(euros);
    if (wealth === null || amount === null) return null;
    const reference = rows(wealth)[REFERENCE_ROW_INDEX];
    const lambda = significant(div(mul(amount, wealth), mul(ratio(2n, 1n), mul(reference, reference))), LAMBDA_SIGNIFICANT_DIGITS);
    const text = terminatingText(lambda);
    return text !== null && text.length <= MAX_LAMBDA_CHARS ? text : null;
}

/** «Custom» the other way: the euros a positive `lambda` accepts to spend on the reference row of `total`; else `null`. */
export function referenceAmountFor(total: PlannerExactMoney, lambda: string | null): PlannerExactMoney | null {
    const wealth = positiveTotal(total);
    const weight = positiveLambda(lambda);
    if (wealth === null || weight === null) return null;
    return money(maxCost(weight, rows(wealth)[REFERENCE_ROW_INDEX], wealth), total.currency);
}
