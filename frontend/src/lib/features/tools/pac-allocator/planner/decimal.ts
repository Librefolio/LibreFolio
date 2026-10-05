/**
 * Exact decimal text for the PAC planner draft.
 *
 * Every economic value travels as decimal text. The UI validates its shape,
 * compares two values expressed in the same unit, and derives the control
 * percentages allowed by Q-C0-2 (target total and remainder). It never
 * computes an economic result: those numbers come from the backend.
 */
import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';

interface Scaled {
    coefficient: bigint;
    scale: number;
}

const PLAIN = /^-?(?:\d+(?:\.\d*)?|\.\d+)$/;
const INTEGER = /^-?\d+$/;

function parse(text: string): Scaled | null {
    const trimmed = text.trim();
    if (!PLAIN.test(trimmed)) return null;
    const negative = trimmed.startsWith('-');
    const body = negative ? trimmed.slice(1) : trimmed;
    const [integer, fraction = ''] = body.split('.');
    const magnitude = BigInt(`${integer || '0'}${fraction}` || '0');
    return {coefficient: negative ? -magnitude : magnitude, scale: fraction.length};
}

function render(value: Scaled): string {
    let {coefficient, scale} = value;
    while (scale > 0 && coefficient % 10n === 0n) {
        coefficient /= 10n;
        scale -= 1;
    }
    const negative = coefficient < 0n;
    const digits = (negative ? -coefficient : coefficient).toString().padStart(scale + 1, '0');
    const integer = scale === 0 ? digits : digits.slice(0, -scale);
    const fraction = scale === 0 ? '' : digits.slice(-scale);
    const text = fraction === '' ? integer : [integer, fraction].join('.');
    return negative ? '-' + text : text;
}

function align(left: Scaled, right: Scaled): [bigint, bigint, number] {
    const scale = Math.max(left.scale, right.scale);
    return [left.coefficient * 10n ** BigInt(scale - left.scale), right.coefficient * 10n ** BigInt(scale - right.scale), scale];
}

/** Wire form: no exponent, no grouping, no trailing zeros, never `-0`. */
export function canonicalDecimal(text: string | null | undefined): string | null {
    if (text === null || text === undefined) return null;
    const parsed = parse(text);
    return parsed ? render(parsed) : null;
}

/** Reads a typed value (grouping and decimal separators tolerated) into wire form. */
export function canonicalInput(text: string | null | undefined): string | null {
    if (text === null || text === undefined) return null;
    const trimmed = text.trim();
    if (trimmed === '') return null;
    return canonicalDecimal(normalizeDecimalInput(trimmed));
}

export function compareDecimal(left: string, right: string): -1 | 0 | 1 | null {
    const a = parse(left);
    const b = parse(right);
    if (!a || !b) return null;
    const [x, y] = align(a, b);
    return x === y ? 0 : x < y ? -1 : 1;
}

export function decimalSign(text: string): -1 | 0 | 1 | null {
    const parsed = parse(text);
    if (!parsed) return null;
    return parsed.coefficient === 0n ? 0 : parsed.coefficient < 0n ? -1 : 1;
}

export function isWholeDecimal(text: string): boolean {
    const canonical = canonicalDecimal(text);
    return canonical !== null && !canonical.includes('.');
}

/** Fraction digits of the canonical form. */
export function decimalScale(text: string): number {
    const canonical = canonicalDecimal(text);
    if (canonical === null) return 0;
    const dot = canonical.indexOf('.');
    return dot < 0 ? 0 : canonical.length - dot - 1;
}

/** Multiplies by 10^places exactly (moves the decimal point). */
export function shiftDecimal(text: string, places: number): string | null {
    const parsed = parse(text);
    if (!parsed) return null;
    const scale = parsed.scale - places;
    if (scale >= 0) return render({coefficient: parsed.coefficient, scale});
    return render({coefficient: parsed.coefficient * 10n ** BigInt(-scale), scale: 0});
}

/** Display only: rounds a magnitude half away from zero, then restores the sign. */
function roundScaled(negative: boolean, magnitude: bigint, divisor: bigint, places: number): string {
    let quotient = magnitude / divisor;
    if ((magnitude % divisor) * 2n >= divisor) quotient += 1n;
    return render({coefficient: negative ? -quotient : quotient, scale: places});
}

/** Display only (R14): a decimal text rounded to `places` fraction digits, half away from zero, exactly. */
export function roundDecimal(text: string, places: number): string | null {
    const parsed = parse(text);
    if (!parsed || !Number.isInteger(places) || places < 0) return null;
    if (parsed.scale <= places) return render(parsed);
    const negative = parsed.coefficient < 0n;
    return roundScaled(negative, negative ? -parsed.coefficient : parsed.coefficient, 10n ** BigInt(parsed.scale - places), places);
}

/** A plain integer text (`-12`), or null: `BigInt` alone would also read `''`, `0x10` and padded text. */
function parseInteger(text: string): bigint | null {
    return INTEGER.test(text) ? BigInt(text) : null;
}

/** Display only (R14): an exact ratio of two integers rounded to `places` fraction digits, half away from zero. */
export function roundRatio(numerator: string, denominator: string, places: number): string | null {
    if (!Number.isInteger(places) || places < 0) return null;
    const n = parseInteger(numerator);
    const d = parseInteger(denominator);
    if (n === null || d === null || d === 0n) return null;
    const negative = n < 0n !== d < 0n;
    const magnitude = (n < 0n ? -n : n) * 10n ** BigInt(places);
    return roundScaled(negative, magnitude, d < 0n ? -d : d, places);
}

/** Whether a decimal text equals an exact ratio of two integers; never for a zero denominator. */
export function decimalEqualsRatio(text: string, numerator: string, denominator: string): boolean {
    const parsed = parse(text);
    const n = parseInteger(numerator);
    const d = parseInteger(denominator);
    if (!parsed || n === null || d === null || d === 0n) return false;
    return parsed.coefficient * d === n * 10n ** BigInt(parsed.scale);
}

/** A percentage typed by the user (60 → 0.6), exactly. */
export function percentToFraction(text: string): string | null {
    return shiftDecimal(text, -2);
}

/** A backend fraction shown as a percentage (0.7215 → 72.15), exactly. */
export function fractionToPercent(text: string): string | null {
    return shiftDecimal(text, 2);
}

/** Control arithmetic only (Q-C0-2): percentages in one unit, never amounts. */
export function sumControlPercentages(values: readonly string[]): string | null {
    let total: Scaled = {coefficient: 0n, scale: 0};
    for (const value of values) {
        const parsed = parse(value);
        if (!parsed) return null;
        const [x, y, scale] = align(total, parsed);
        total = {coefficient: x + y, scale};
    }
    return render(total);
}

/** Control arithmetic only (Q-C0-2): the remainder of a percentage total. */
export function remainingControlPercentage(total: string, of = '100'): string | null {
    const a = parse(of);
    const b = parse(total);
    if (!a || !b) return null;
    const [x, y, scale] = align(a, b);
    return render({coefficient: x - y, scale});
}

/**
 * Control arithmetic only (Q-C0-2): rescales the selected percentages so the
 * whole list adds up to exactly `of`, keeping their ratios; the other rows do
 * not change. Selected rows that are all 0 get equal parts.
 *
 * Exact, at max(2, input scale) fraction digits: each share is floored and the
 * leftover last digits go to the largest remainders, ties by row order.
 * Null when a value is not a number or negative, when nothing is selected, or
 * when the other rows alone already exceed `of`.
 */
export function rebalanceControlPercentages(values: readonly string[], selected: readonly number[], of = '100'): string[] | null {
    const parsed = values.map(parse);
    const total = parse(of);
    if (!total || total.coefficient < 0n || parsed.some((value) => !value || value.coefficient < 0n)) return null;
    const picked = [...new Set(selected)].filter((index) => index >= 0 && index < values.length).sort((a, b) => a - b);
    if (picked.length === 0) return null;
    const scale = Math.max(2, total.scale, ...parsed.map((value) => (value as Scaled).scale));
    const units = (value: Scaled) => value.coefficient * 10n ** BigInt(scale - value.scale);
    const weights = parsed.map((value) => units(value as Scaled));
    const isPicked = new Set(picked);
    const others = weights.reduce((sum, weight, index) => (isPicked.has(index) ? sum : sum + weight), 0n);
    const room = units(total) - others;
    if (room < 0n) return null;
    const weightSum = picked.reduce((sum, index) => sum + weights[index], 0n);
    const shares = picked.map((index) => {
        const numerator = weightSum === 0n ? room : room * weights[index];
        const denominator = weightSum === 0n ? BigInt(picked.length) : weightSum;
        return {index, floor: numerator / denominator, remainder: numerator % denominator};
    });
    let leftover = room - shares.reduce((sum, share) => sum + share.floor, 0n);
    const byRemainder = [...shares].sort((a, b) => (a.remainder === b.remainder ? a.index - b.index : a.remainder > b.remainder ? -1 : 1));
    for (const share of byRemainder) {
        if (leftover === 0n) break;
        share.floor += 1n;
        leftover -= 1n;
    }
    const next = values.map((value) => canonicalDecimal(value) as string);
    for (const share of shares) next[share.index] = render({coefficient: share.floor, scale});
    return next;
}
