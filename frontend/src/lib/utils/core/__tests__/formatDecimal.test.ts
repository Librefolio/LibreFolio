/**
 * formatDecimal.test.ts — display formatting of backend decimal strings.
 *
 * The idempotence block exists because of a real defect: the WAC field showed
 * `191.50591660` (truncation to 8 decimals had exposed a trailing zero), and
 * re-formatting that string produced `191.5059166`. `WacPreviewSection` compares
 * the two to decide whether the user edited the amount, so simply focusing the
 * field and clicking away silently switched the form to Manual mode.
 */
import {describe, expect, it} from 'vitest';
import {formatDecimalForDisplay} from '../formatDecimal';

describe('formatDecimalForDisplay', () => {
    it('returns empty for null, undefined and empty string', () => {
        expect(formatDecimalForDisplay(null)).toBe('');
        expect(formatDecimalForDisplay(undefined)).toBe('');
        expect(formatDecimalForDisplay('')).toBe('');
    });

    it('leaves non-numeric input untouched', () => {
        expect(formatDecimalForDisplay('abc')).toBe('abc');
        expect(formatDecimalForDisplay('1,5')).toBe('1,5');
    });

    it('drops insignificant trailing zeros', () => {
        expect(formatDecimalForDisplay('6.000000')).toBe('6');
        expect(formatDecimalForDisplay('6.500000')).toBe('6.5');
        expect(formatDecimalForDisplay('-0.250')).toBe('-0.25');
    });

    it('keeps significant fractional digits up to maxFrac', () => {
        expect(formatDecimalForDisplay('0.00000123')).toBe('0.00000123');
        expect(formatDecimalForDisplay('1.234567891234')).toBe('1.23456789');
    });

    it('pads to minFrac when asked', () => {
        expect(formatDecimalForDisplay('6', {minFrac: 2})).toBe('6.00');
        expect(formatDecimalForDisplay('6.5', {minFrac: 2})).toBe('6.50');
    });

    it('never leaves a trailing zero exposed by truncation', () => {
        // The 9th decimal onwards is cut; the 8th is a zero and must go too.
        expect(formatDecimalForDisplay('191.5059166043')).toBe('191.5059166');
        expect(formatDecimalForDisplay('1.2345678000009')).toBe('1.2345678');
    });

    it('is idempotent — a round trip through an input is not an edit', () => {
        const samples = ['191.5059166043', '170.3261122757978', '1.2345678000009', '6.000000', '0.00000123', '-0.250', '42.00', '1.234567891234'];
        for (const raw of samples) {
            const once = formatDecimalForDisplay(raw);
            expect(formatDecimalForDisplay(once), `not idempotent for ${raw}`).toBe(once);
        }
    });

    it('is idempotent with minFrac too', () => {
        for (const raw of ['6', '6.5', '191.5059166043']) {
            const once = formatDecimalForDisplay(raw, {minFrac: 2});
            expect(formatDecimalForDisplay(once, {minFrac: 2}), `not idempotent for ${raw}`).toBe(once);
        }
    });
});

/*
 * W-B66 — a huge paste blocks the paster's own tab (D-W66-1 (b), 17/10).
 *
 * Two patterns here cost quadratic time on a long text: the plain-decimal test `/^-?\d*\.?\d*$/`, on a
 * text it rejects (every split of the digits between its two `\d*` is tried before the last character
 * fails it), and the trailing-zero strip `frac.replace(/0+$/, '')`, on a zero run that does not end the
 * fraction (it restarts from each zero of the run). The cure: the linear `^-?\d*(?:\.\d*)?$` — the same
 * language — and a loop for the zeros.
 *
 * 40 000 characters: the quadratic forms take seconds there (3.3 and 3.6 s, measured in V8), the linear
 * ones a fraction of a millisecond, so a 1 000 ms bound separates them even under load. A quadratic regex
 * is synchronous and Vitest cannot interrupt it, which is why the size is not 200 000 (about 90 s).
 */
const HUGE = 40_000;
const BOUND_MS = 1_000;

function timed<T>(run: () => T): {result: T; ms: number} {
    const started = performance.now();
    const result = run();
    return {result, ms: performance.now() - started};
}

/** A text as a failure message can show it: whole when short, its two ends and its length when huge. */
function shown(text: string): string {
    return text.length <= 64 ? JSON.stringify(text) : `${JSON.stringify(text.slice(0, 24))}…${JSON.stringify(text.slice(-16))} (${text.length} chars)`;
}

describe('formatDecimalForDisplay — linear time on a huge text (W-B66, D-W66-1 (b))', () => {
    // Red before the W-B66 cure: the plain-decimal test backtracks quadratically before rejecting the final "x".
    it('returns 40 000 digits followed by an "x" unchanged, within 1 000 ms', () => {
        const text = `${'9'.repeat(HUGE)}x`;
        const {result, ms} = timed(() => formatDecimalForDisplay(text));
        expect(result === text, `not a plain decimal, so returned as is; got ${shown(result)}`).toBe(true);
        expect(ms, `took ${ms.toFixed(0)} ms: /^-?\\d*\\.?\\d*$/ backtracks quadratically on a long text it rejects`).toBeLessThan(BOUND_MS);
    });

    const bulk = `0.${'0'.repeat(HUGE)}1000`;

    // Red before the W-B66 cure: the strip restarts from each zero of a run that does not end the fraction. Nothing truncates
    // the run first: the Bulk cell passes `maxFrac: value.length`.
    it.each([
        ['a 40 000-zero run then 1', `0.${'0'.repeat(HUGE)}1`, 40_002, `0.${'0'.repeat(HUGE)}1`],
        ['the same run then 1 and three trailing zeros, at the Bulk cell maxFrac', bulk, bulk.length, `0.${'0'.repeat(HUGE)}1`],
    ] as const)('keeps %s, stripping only trailing zeros, within 1 000 ms', (_label, text, maxFrac, expected) => {
        const {result, ms} = timed(() => formatDecimalForDisplay(text, {maxFrac}));
        expect(result === expected, `formatted as ${shown(result)}, not ${shown(expected)}`).toBe(true);
        expect(ms, `took ${ms.toFixed(0)} ms: frac.replace(/0+$/, '') rescans the zero run from each of its zeros`).toBeLessThan(BOUND_MS);
    });
});

describe('formatDecimalForDisplay — the plain-decimal test keeps its language (W-B66 guard)', () => {
    // Guard: what the old and the linear pattern both accept is formatted exactly as before.
    it.each([
        ['-', '0'],
        ['.', '0'],
        ['-.', '0'],
        ['5.', '5'],
        ['.5', '0.5'],
        ['-.5', '-0.5'],
        ['-5.', '-5'],
        ['  7.10  ', '7.1'],
        ['007', '007'],
        ['-42', '-42'],
    ])('formats the plain decimal %j as %j', (text, formatted) => {
        expect(formatDecimalForDisplay(text)).toBe(formatted);
    });

    // Guard: what both reject is returned untouched.
    it.each(['1,5', '1.2.3', '-1.2.3', '--1', '1-', '+5', '1e5', '1 2', '0x1A', 'NaN', '.-5', '5.-'])('returns %j untouched: not a plain decimal', (text) => {
        expect(formatDecimalForDisplay(text)).toBe(text);
    });

    // Guard: a number is stringified first, so an exponent form stays as JavaScript wrote it.
    it.each([
        [1e21, '1e+21'],
        [1e-7, '1e-7'],
        [-0.5, '-0.5'],
    ])('formats the number %s as %j', (value, formatted) => {
        expect(formatDecimalForDisplay(value)).toBe(formatted);
    });
});

describe('formatDecimalForDisplay — trailing zeros are still stripped (W-B66 guard)', () => {
    // Guard: whatever replaces the regex strips exactly the trailing zeros of the fraction.
    it.each([
        ['1.2300', {}, '1.23'],
        ['0.10', {}, '0.1'],
        ['-0.000', {}, '0'],
        ['100', {}, '100'],
        ['100.0', {}, '100'],
        ['6.5000', {minFrac: 2}, '6.50'],
    ])('formats %j with %j as %j', (text, opts, formatted) => {
        expect(formatDecimalForDisplay(text, opts)).toBe(formatted);
    });

    // Guard: a run that does end the fraction matches at its first zero, so it is linear already.
    it('strips a fraction of 40 000 zeros down to the integer, within 1 000 ms', () => {
        const text = `1.${'0'.repeat(HUGE)}`;
        const {result, ms} = timed(() => formatDecimalForDisplay(text, {maxFrac: HUGE}));
        expect(result).toBe('1');
        expect(ms, `took ${ms.toFixed(0)} ms`).toBeLessThan(BOUND_MS);
    });
});
