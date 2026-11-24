/**
 * The sums under the «Limits» column of the targets table (TL-4 of project 67, the developer's testlist of 21/11: «metterei
 * in fondo alla tabella una riga di summary»): the minimums together, and the maximums together, in the valuation currency.
 *
 * @financial-math-exception TL-4 of project 67, the Targets step's summary row: the minimums typed together and the maximums typed together, an amount as it is and a percentage as share × the preview's total, on exact rationals
 *
 * A small sum on the figures the user types (developer decision of 25/10/2026): an amount counts as typed, a percentage as
 * its share of the Tool's base, the preview's `total`. It is drawn only. Whether the minimums are too many is the backend's
 * verdict (`limit_problems`), never this sum: in the PAC a cash entry's trapped cash already honours its minimum, so the sum
 * here may pass the total while the plan accepts it.
 *
 * **Arithmetic.** Exact rationals on `BigInt`: the total may be an exact ratio with no decimal form, so it is read from its
 * numerator and denominator, never from its display text.
 */
import {canonicalDecimal, decimalEqualsRatio, roundRatio} from '$lib/utils/core/exactDecimal';
import {cldrCurrencyDigits, formatPlannerMoneyPlain} from './format';
import type {PlannerDraft} from './draft.svelte';
import {parseLimit, type LimitSide} from './limits';
import type {PlannerExactMoney, PlannerExactNumber} from './types';

/** An exact sum, numerator over a positive denominator. */
export interface ExactSum {
    numerator: bigint;
    denominator: bigint;
}

/** One side's sum: `none` with no limit typed on it; `unknown` when a percentage needs a base there is not yet. */
export type LimitSum = {kind: 'none'} | {kind: 'unknown'} | {kind: 'sum'; value: ExactSum};

function decimalRatio(text: string): ExactSum | null {
    const canonical = canonicalDecimal(text);
    if (canonical === null) return null;
    const negative = canonical.startsWith('-');
    const [integer, fraction = ''] = (negative ? canonical.slice(1) : canonical).split('.');
    const numerator = BigInt(integer + fraction);
    return {numerator: negative ? -numerator : numerator, denominator: 10n ** BigInt(fraction.length)};
}

function exactRatio(value: PlannerExactNumber): ExactSum | null {
    try {
        if (value.kind === 'finite_decimal') return decimalRatio(value.value);
        const numerator = BigInt(value.numerator);
        const denominator = BigInt(value.denominator);
        if (denominator === 0n) return null;
        return denominator < 0n ? {numerator: -numerator, denominator: -denominator} : {numerator, denominator};
    } catch {
        return null;
    }
}

function add(left: ExactSum, right: ExactSum): ExactSum {
    return {numerator: left.numerator * right.denominator + right.numerator * left.denominator, denominator: left.denominator * right.denominator};
}

/** The limits typed on `side` over every row of the table (Assets and cash entries), on the base `total`. */
export function limitSum(draft: PlannerDraft, side: LimitSide, total: PlannerExactMoney | null): LimitSum {
    const base = total === null ? null : exactRatio(total.value);
    let sum: ExactSum = {numerator: 0n, denominator: 1n};
    let typed = false;
    let unknown = false;
    for (const row of draft.targetRows) {
        const limit = parseLimit(draft.data.limits[row.key]?.[side]);
        if (limit === null || limit === 'invalid') continue;
        typed = true;
        if (limit.kind === 'amount') {
            const amount = decimalRatio(limit.value);
            if (amount === null) continue;
            sum = add(sum, amount);
        } else if (base === null) {
            unknown = true;
        } else {
            const share = decimalRatio(limit.percent);
            if (share === null) continue;
            sum = add(sum, {numerator: share.numerator * base.numerator, denominator: share.denominator * base.denominator * 100n});
        }
    }
    if (!typed) return {kind: 'none'};
    return unknown ? {kind: 'unknown'} : {kind: 'sum', value: sum};
}

/** A sum as the user reads it: at the minor unit of the valuation currency, `≈` when that rounds it (R14); personal. */
export function formatLimitSum(sum: ExactSum, currency: string): string {
    const numerator = sum.numerator.toString();
    const denominator = sum.denominator.toString();
    const shown = roundRatio(numerator, denominator, cldrCurrencyDigits(currency));
    if (shown === null) return '—';
    return formatPlannerMoneyPlain(shown, currency, {approx: !decimalEqualsRatio(shown, numerator, denominator)});
}
