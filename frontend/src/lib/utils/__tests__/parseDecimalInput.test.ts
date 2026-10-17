import {beforeEach, describe, expect, it, vi} from 'vitest';
import {decimalArrowStep, exactDecimalArrowStep, filterDecimalInput, normalizeDecimalInput, resetDecimalArrowHold, stepDecimalValue, stepExactDecimalValue} from '$lib/utils/core/parseDecimalInput';

describe('filterDecimalInput', () => {
    it('drops letters immediately while preserving decimal punctuation and every digit', () => {
        expect(filterDecimalInput('EUR 12,34abc')).toBe('12,34');
        expect(filterDecimalInput('1x.2y,3z')).toBe('1.2,3');
    });

    it('preserves partial comma and dot drafts for later normalization', () => {
        expect(filterDecimalInput('12,')).toBe('12,');
        expect(filterDecimalInput('.')).toBe('.');
        expect(filterDecimalInput(',5')).toBe(',5');
    });

    it('keeps only a permitted leading sign', () => {
        expect(filterDecimalInput('-12,3')).toBe('12,3');
        expect(filterDecimalInput('-12,3', true)).toBe('-12,3');
        expect(filterDecimalInput('12-3', true)).toBe('123');
        expect(filterDecimalInput('  -0.5', true)).toBe('-0.5');
    });
});

describe('normalizeDecimalInput', () => {
    it('leaves canonical input untouched', () => {
        expect(normalizeDecimalInput('5.9')).toBe('5.9');
        expect(normalizeDecimalInput('1234')).toBe('1234');
        expect(normalizeDecimalInput('-0.125')).toBe('-0.125');
        expect(normalizeDecimalInput('')).toBe('');
    });

    it('reads a lone comma as the decimal separator', () => {
        expect(normalizeDecimalInput('5,9')).toBe('5.9');
        expect(normalizeDecimalInput('-1234,5678')).toBe('-1234.5678');
        expect(normalizeDecimalInput(' 0,5 ')).toBe('0.5');
    });

    it('unpacks European grouping', () => {
        expect(normalizeDecimalInput('1.234,56')).toBe('1234.56');
        expect(normalizeDecimalInput('1.234.567,89')).toBe('1234567.89');
        expect(normalizeDecimalInput('-12.345,6')).toBe('-12345.6');
        expect(normalizeDecimalInput('1.234.567')).toBe('1234567');
    });

    it('unpacks Anglo grouping', () => {
        expect(normalizeDecimalInput('1,234.56')).toBe('1234.56');
        expect(normalizeDecimalInput('1,234,567.89')).toBe('1234567.89');
        expect(normalizeDecimalInput('1,234,567')).toBe('1234567');
    });

    it('keeps every digit when the grouping is not well formed', () => {
        expect(normalizeDecimalInput('1.4,1')).toBe('1.41');
        expect(normalizeDecimalInput('4.6,30')).toBe('4.630');
        expect(normalizeDecimalInput('4,6.30')).toBe('4.630');
        expect(normalizeDecimalInput('1.2.3')).toBe('1.23');
        expect(normalizeDecimalInput('-4.6,30')).toBe('-4.630');
        expect(normalizeDecimalInput('12,34,56')).toBe('12.3456');
    });

    it('keeps half-typed values usable', () => {
        expect(normalizeDecimalInput('5,')).toBe('5.');
        expect(normalizeDecimalInput('5.')).toBe('5.');
        expect(normalizeDecimalInput('.5')).toBe('.5');
    });

    it('returns the raw input when there is no number in it', () => {
        expect(normalizeDecimalInput('abc')).toBe('abc');
        expect(normalizeDecimalInput('-')).toBe('-');
    });

    it('strips stray characters around a number', () => {
        expect(normalizeDecimalInput('1 234,5')).toBe('1234.5');
        expect(normalizeDecimalInput('€ 12,50')).toBe('12.50');
    });
});

describe('stepDecimalValue', () => {
    it('steps at the precision already in use', () => {
        expect(stepDecimalValue('5.9', 1)).toBe('6.9');
        expect(stepDecimalValue('5.9', -1)).toBe('4.9');
        expect(stepDecimalValue('5', 1)).toBe('6');
        expect(stepDecimalValue('', 1)).toBe('1');
    });

    it('does not drift on floats', () => {
        expect(stepDecimalValue('5.9', -1, 0.1)).toBe('5.8');
        expect(stepDecimalValue('0.3', -1, 0.1)).toBe('0.2');
    });

    it('normalizes before stepping', () => {
        expect(stepDecimalValue('5,9', 1)).toBe('6.9');
        expect(stepDecimalValue('1.234,50', 1)).toBe('1235.50');
    });

    it('goes below zero when asked', () => {
        expect(stepDecimalValue('0', -1)).toBe('-1');
    });
});

describe('stepExactDecimalValue', () => {
    it('keeps twelve integer and twelve fractional digits exact', () => {
        expect(stepExactDecimalValue('999999999998.999999999999', 1, '0.000000000001')).toBe('999999999999.000000000000');
        expect(stepExactDecimalValue('0.300000000001', -1, '0.000000000001')).toBe('0.300000000000');
    });

    it('normalizes locale input before applying the exact step', () => {
        expect(stepExactDecimalValue('1.234,500000000001', 1, '0,000000000001')).toBe('1234.500000000002');
    });

    it('steps through zero without losing the sign or precision contract', () => {
        expect(stepExactDecimalValue('0.000000000000', -1, '0.000000000001')).toBe('-0.000000000001');
        expect(stepExactDecimalValue('-0.000000000001', 1, '0.000000000001')).toBe('0.000000000000');
    });

    it('uses zero as the starting point for an invalid current value', () => {
        expect(stepExactDecimalValue('not-a-number', 1, '0.25')).toBe('0.25');
    });

    it.each(['0', '-1', 'Infinity', 'not-a-step'])('leaves the raw value alone for invalid step %s', (step) => {
        expect(stepExactDecimalValue('1.25', 1, step)).toBe('1.25');
    });
});

describe('exactDecimalArrowStep', () => {
    function keyEvent(key: string, modifiers: Partial<Pick<KeyboardEvent, 'ctrlKey' | 'metaKey' | 'altKey'>> = {}) {
        return {
            key,
            ctrlKey: false,
            metaKey: false,
            altKey: false,
            preventDefault: vi.fn(),
            ...modifiers,
        } as unknown as KeyboardEvent;
    }

    it('maps ArrowUp and ArrowDown to exact string arithmetic and prevents the native step', () => {
        const up = keyEvent('ArrowUp');
        const down = keyEvent('ArrowDown');

        expect(exactDecimalArrowStep(up, '5.900000000001', '0.000000000001')).toBe('5.900000000002');
        expect(exactDecimalArrowStep(down, '5.900000000001', '0.000000000001')).toBe('5.900000000000');
        expect(up.preventDefault).toHaveBeenCalledTimes(1);
        expect(down.preventDefault).toHaveBeenCalledTimes(1);
    });

    it.each([
        ['a non-arrow key', keyEvent('Enter')],
        ['Ctrl+ArrowUp', keyEvent('ArrowUp', {ctrlKey: true})],
        ['Meta+ArrowDown', keyEvent('ArrowDown', {metaKey: true})],
        ['Alt+ArrowUp', keyEvent('ArrowUp', {altKey: true})],
    ])('leaves %s to the browser', (_label, event) => {
        expect(exactDecimalArrowStep(event, '1.5', '0.1')).toBeNull();
        expect(event.preventDefault).not.toHaveBeenCalled();
    });
});

describe('decimalArrowStep hold acceleration', () => {
    const target = {} as EventTarget;

    function press(value: string, {repeat, key = 'ArrowUp', step = 1}: {repeat: boolean; key?: string; step?: number}): string {
        const event = {key, repeat, target, ctrlKey: false, metaKey: false, altKey: false, preventDefault: () => {}} as unknown as KeyboardEvent;
        return decimalArrowStep(event, value, step) as string;
    }

    beforeEach(() => resetDecimalArrowHold());

    it('steps by one while the key is tapped, however many times', () => {
        let value = '7';
        for (let i = 0; i < 30; i += 1) value = press(value, {repeat: false});
        expect(value).toBe('37');
    });

    it('escalates to ten only after fifteen repeats and at the next round ten', () => {
        let value = press('7', {repeat: false});
        const seen: string[] = [value];
        for (let i = 0; i < 25; i += 1) {
            value = press(value, {repeat: true});
            seen.push(value);
        }
        // Unit steps up to 30 (the first ten reached after the 15th repeat), then tens.
        expect(seen.slice(0, 22)).toEqual(Array.from({length: 22}, (_, i) => String(8 + i)));
        expect(seen).toContain('30');
        expect(seen).toContain('40');
        expect(Number(value)).toBe(60);
    });

    it('accelerates downwards too', () => {
        let value = press('100', {repeat: false, key: 'ArrowDown'});
        for (let i = 0; i < 25; i += 1) value = press(value, {repeat: true, key: 'ArrowDown'});
        // 99 … 80 one by one, then tens all the way down.
        expect(Number(value)).toBe(20);
    });

    it('drops back to the base step when the direction changes', () => {
        let value = press('7', {repeat: false});
        for (let i = 0; i < 25; i += 1) value = press(value, {repeat: true});
        const afterTurn = press(value, {repeat: true, key: 'ArrowDown'});
        expect(Number(value) - Number(afterTurn)).toBe(1);
    });
});

/*
 * W-B66 — a pasted exponent, read exactly or kept (D-W66-1 (a), 17/10).
 *
 * Typed key by key, an `e` never enters a decimal field; pasted, a whole `1e-8` arrives at once. Until
 * W-B66 both readers kept only its digits: `filterDecimalInput` (every input event of ExactDecimalInput)
 * and `normalizeDecimalInput` (the fields that call it directly: the data editor's cells, the PAC planner,
 * FixFlaggedStep, EventCreateMiniModal, CompactCashCell's blur). `1e-8` read 18, `3E+150` read 3150, `1e5x`
 * read 15: another number, silently.
 *
 * The contract — a number is never changed in silence:
 * - A text WHOLLY in scientific notation (trimmed; an optional leading `-`; a mantissa of digits with at
 *   most one `.` or `,` mark and at least one digit; `e` or `E`; an optional exponent sign; exponent
 *   digits) is expanded exactly to a canonical plain decimal when |exponent| ≤ 100, the backend's bound
 *   (R13-SEC7-3).
 * - Any other text holding an EXPONENT MARKER — a digit, an optional `.` or `,`, `e` or `E`, an optional
 *   sign, a digit (`/\d[.,]?[eE][+-]?\d/`, unanchored) — is kept exactly as typed (trimmed), its sign
 *   included even without allowNegative, so the field can say why it refuses it: beyond ±100 (`3E+150`),
 *   or not wholly scientific (`1e5x`, `1.234,5e2`).
 * - A text holding no marker is read exactly as before: a lone `e` is still dropped.
 */

/** The coordinator's table. `-2.5e2` reads `-250` where a leading minus is allowed. */
const EXPANSIONS: ReadonlyArray<readonly [string, string]> = [
    ['1e-8', '0.00000001'],
    ['1,5E+3', '1500'],
    ['-2.5e2', '-250'],
    ['1.00E-08', '0.00000001'],
    ['0e5', '0'],
    ['12.34e1', '123.4'],
    ['5e0', '5'],
    ['1e100', `1${'0'.repeat(100)}`],
    ['1e-100', `0.${'0'.repeat(99)}1`],
];

/** One row per rule of the canonical expansion, named by the rule it pins. */
const CANONICAL_RULES: ReadonlyArray<readonly [string, string, string]> = [
    ['a dot is the decimal mark, whatever the pasted one', '1,5e-1', '0.15'],
    ['no leading zeros in the integer part', '0012e-1', '1.2'],
    ['no trailing zeros in the fraction', '12.50e0', '12.5'],
    ['no trailing dot', '2.0e0', '2'],
    ['exact: no float rounding', '0.1234567890123456789e1', '1.234567890123456789'],
    ['the whole value is trimmed first', ' \t1e-8 ', '0.00000001'],
];

/** The edges of the form, one row each. */
const FORM_EDGES: ReadonlyArray<readonly [string, string, string]> = [
    ['a mark may open the mantissa', '.5e1', '5'],
    ['a mark may close the mantissa', '5.e1', '50'],
    ['the exponent may carry leading zeros', '1e0005', '100000'],
];

/** Beyond ±100: the trimmed text, exactly as pasted. */
const OUT_OF_RANGE: ReadonlyArray<readonly [string, string]> = [
    ['1e-101', '1e-101'],
    ['1e101', '1e101'],
    ['3E+150', '3E+150'],
    ['7,5E+150, its comma kept', '7,5E+150'],
    ['an exponent of 400 digits', `2.5e${'9'.repeat(400)}`],
    ['3E+150 between blanks, trimmed', '  3E+150 \t'],
    ['-7.5e-1000, a permitted sign kept', '-7.5e-1000'],
];

/** Holding an exponent marker without being wholly scientific: the text, exactly as typed. */
const MARKED: ReadonlyArray<readonly [string, string]> = [
    ['1e5x', 'something after the exponent'],
    ['1e-200x', 'beyond ±100, then a stray character'],
    ['1e5e3', 'two exponents'],
    ['1.2.3e4', 'two decimal marks'],
    ['1.234,5e2', 'a grouped mantissa'],
];

/** A row's leading minus is meant: read it where a sign is allowed. */
function signed(text: string): boolean {
    return text.trim().startsWith('-');
}

describe('filterDecimalInput — a pasted exponent is read exactly, or kept (W-B66, D-W66-1 (a))', () => {
    // Red before the W-B66 cure: the `e` and its sign are filtered out and the digits run together (1e-8 → 18).
    it.each(EXPANSIONS)('expands %s exactly to %s', (pasted, expanded) => {
        expect(filterDecimalInput(pasted, signed(pasted)), `${pasted} is wholly scientific, |exponent| ≤ 100: today its e is filtered out and the digits run together`).toBe(expanded);
    });

    // Red before the W-B66 cure, for the same reason.
    it.each(CANONICAL_RULES)('expands to the canonical form — %s: %j → %j', (_rule, pasted, expanded) => {
        expect(filterDecimalInput(pasted), 'today the e is filtered out and the digits run together').toBe(expanded);
    });

    // Red before the W-B66 cure: .5e1 → .51, 5.e1 → 5.1, 1e0005 → 10005.
    it.each(FORM_EDGES)('reads the form at its edge — %s: %j → %j', (_rule, pasted, expanded) => {
        expect(filterDecimalInput(pasted), 'today the e is filtered out and the digits run together').toBe(expanded);
    });

    // Red before the W-B66 cure: `-1e2` reads 12 — the minus is rightly dropped, but so is the e.
    it.each([
        ['-1e2', '100'],
        ['-2.5e2', '250'],
        [' -1e-8', '0.00000001'],
    ])('drops the leading minus of %j without allowNegative, as for any number: %j', (pasted, expanded) => {
        expect(filterDecimalInput(pasted, false), 'today the e is filtered out and the digits run together').toBe(expanded);
    });

    // Red before the W-B66 cure: beyond ±100 the text loses its e and becomes another number (3E+150 → 3150).
    it.each(OUT_OF_RANGE)('keeps %s as pasted: beyond ±100 it is never a number without its e', (_label, pasted) => {
        expect(filterDecimalInput(pasted, signed(pasted)), 'beyond ±100 the trimmed text stays as pasted; today its e is filtered out').toBe(pasted.trim());
    });

    // Red before the W-B66 cure: 1e5x → 15, 1e-200x → 1200, 1e5e3 → 153, 1.2.3e4 → 1.2.34, 1.234,5e2 → 1.234,52.
    it.each(MARKED)('keeps %j as typed — %s: it holds an exponent marker without being wholly scientific', (typed) => {
        expect(filterDecimalInput(typed), 'a text holding an exponent marker is kept as typed; today its e is filtered out').toBe(typed);
    });

    // Red before the W-B66 cure: the minus is dropped (no allowNegative), and the e with it: -1e-200 → 1200.
    it.each([
        ['-1e-200', 'beyond ±100'],
        ['-1e5x', 'not wholly scientific'],
    ])('keeps %j as typed without allowNegative, its sign included: kept (%s) beats the sign rule', (typed) => {
        expect(filterDecimalInput(typed, false), 'a kept text keeps its sign; today the minus and the e are both filtered out').toBe(typed);
    });

    // Guard: a text holding no exponent marker filters exactly as before — a lone e is still dropped.
    it.each([
        ['12a3', '123', 'a letter among the digits'],
        ['1.234,56', '1.234,56', 'grouping punctuation'],
        ['1,234.56', '1,234.56', 'grouping punctuation'],
        ['EUR 12,34', '12,34', 'an E with no digit before it'],
        ['12EUR', '12', 'an E with no digit after it'],
        ['1e', '1', 'no digit after the e'],
        ['e5', '5', 'no digit before the e'],
        ['e', '', 'a lone e'],
        ['1e+-5', '15', 'two signs: no digit right after the first'],
        ['1 e5', '15', 'a blank between the digit and the e'],
    ])('filters %j as today, to %j: %s, so no exponent marker', (typed, filtered) => {
        expect(filterDecimalInput(typed)).toBe(filtered);
    });
});

describe('normalizeDecimalInput — an exponent is read exactly, or kept, too (W-B66, D-W66-1 (a))', () => {
    // Red before the W-B66 cure: 1e-8 → 18, 1,5E+3 → 1.53, -2.5e2 → -2.52. No allowNegative here: the sign is kept.
    it.each(EXPANSIONS)('expands %s exactly to %s, as filterDecimalInput does', (pasted, expanded) => {
        expect(normalizeDecimalInput(pasted), `${pasted} is wholly scientific, |exponent| ≤ 100: today its e is dropped and the digits run together`).toBe(expanded);
    });

    // Red before the W-B66 cure, for the same reason.
    it.each(CANONICAL_RULES)('expands to the canonical form — %s: %j → %j', (_rule, pasted, expanded) => {
        expect(normalizeDecimalInput(pasted), 'today the e is dropped and the digits run together').toBe(expanded);
    });

    // Red before the W-B66 cure: .5e1 → .51, 5.e1 → 5.1, 1e0005 → 10005.
    it.each(FORM_EDGES)('reads the form at its edge — %s: %j → %j', (_rule, pasted, expanded) => {
        expect(normalizeDecimalInput(pasted), 'today the e is dropped and the digits run together').toBe(expanded);
    });

    // Red before the W-B66 cure: beyond ±100 the text loses its e and becomes another number (3E+150 → 3150).
    it.each(OUT_OF_RANGE)('returns %s untouched: beyond ±100 it is never a number without its e', (_label, pasted) => {
        expect(normalizeDecimalInput(pasted), 'beyond ±100 the trimmed text is returned untouched; today its e is dropped').toBe(pasted.trim());
    });

    // Red before the W-B66 cure: 1e5x → 15, 1e-200x → 1200, 1e5e3 → 153, 1.2.3e4 → 1.234, 1.234,5e2 → 1234.52.
    it.each(MARKED)('returns %j untouched — %s: it holds an exponent marker without being wholly scientific', (typed) => {
        expect(normalizeDecimalInput(typed), 'a text holding an exponent marker is returned untouched; today its e is dropped').toBe(typed);
    });

    // Guard: a text holding no exponent marker normalizes exactly as before.
    it.each([
        ['1.234,56', '1234.56'],
        ['1,234.56', '1234.56'],
        ['1.4,1', '1.41'],
        ['-12', '-12'],
        ['12a3', '123'],
        ['', ''],
        ['EUR 12,34', '12.34'],
        ['12EUR', '12'],
        ['1e', '1'],
        ['e5', '5'],
        ['1e+-5', '15'],
        ['1 e5', '15'],
    ])('normalizes %j as today, to %j: no exponent marker in it', (typed, normalized) => {
        expect(normalizeDecimalInput(typed)).toBe(normalized);
    });
});

/*
 * W-B66 — a huge paste costs linear time (D-W66-1 (b)).
 *
 * 40 000 characters: a quadratic pattern takes seconds there (2.7–3.3 s, measured in V8), a linear one a
 * fraction of a millisecond, so a 1 000 ms bound separates them even under load. A quadratic regex is
 * synchronous and Vitest cannot interrupt it, which is why the size is not 200 000 (about 90 s).
 */
const HUGE = 40_000;
const BOUND_MS = 1_000;
const NINES = '9'.repeat(HUGE);

function timed<T>(run: () => T): {result: T; ms: number} {
    const started = performance.now();
    const result = run();
    return {result, ms: performance.now() - started};
}

/** A text as a failure message can show it: whole when short, its two ends and its length when huge. */
function shown(text: string): string {
    return text.length <= 64 ? JSON.stringify(text) : `${JSON.stringify(text.slice(0, 24))}…${JSON.stringify(text.slice(-16))} (${text.length} chars)`;
}

/** No exponent marker: [label, text, filtered, normalized] — each read as before. */
const HUGE_PLAIN: ReadonlyArray<readonly [string, string, string, string]> = [
    ['digits then "-"', `${NINES}-`, NINES, NINES],
    ['digits then "x"', `${NINES}x`, NINES, NINES],
    ['digits then a dangling "e"', `${NINES}e`, NINES, NINES],
    ['a decimal then "x"', `1.${NINES}x`, `1.${NINES}`, `1.${NINES}`],
];

/** Holding an exponent marker: [label, text, read as]. */
const HUGE_MARKED: ReadonlyArray<readonly [string, string, string]> = [
    ['a 40 000-digit mantissa, expanded exactly', `1.${NINES}e-5`, `0.00001${NINES}`],
    ['a 40 000-digit exponent, kept as pasted', `1e${NINES}`, `1e${NINES}`],
    ['a 40 000-digit mantissa then e5x, kept as typed', `${NINES}e5x`, `${NINES}e5x`],
];

describe('a huge paste costs linear time (W-B66, D-W66-1 (b))', () => {
    /*
     * Guard — the red the brief asked for here cannot exist. CANONICAL (`/^-?(?:\d+\.?\d*|\.\d+)$/`) IS
     * quadratic on 40 000 digits then `-`, but no such candidate reaches it: the body is filtered to
     * digits, dots and commas before the test (the trailing `-` is gone), and every branch collapses the
     * separators to one dot, so the only candidates CANONICAL rejects are `.` and `-.`. The bound stays as
     * a guard on the exponent reading the cure adds to this function: a `\d*[.,]?\d*[eE]…` pattern would
     * be quadratic on exactly these texts.
     */
    it.each(HUGE_PLAIN)('normalizeDecimalInput reads %s as today, in linear time', (_label, text, _filtered, normalized) => {
        const {result, ms} = timed(() => normalizeDecimalInput(text));
        expect(result === normalized, `normalized to ${shown(result)}, not ${shown(normalized)}`).toBe(true);
        expect(ms, `normalizeDecimalInput took ${ms.toFixed(0)} ms on ${text.length} characters`).toBeLessThan(BOUND_MS);
    });

    // Guard: the filter is one character class. It stays linear once it reads exponents, on every input event.
    it.each(HUGE_PLAIN)('filterDecimalInput reads %s as today, in linear time', (_label, text, filtered) => {
        const {result, ms} = timed(() => filterDecimalInput(text));
        expect(result === filtered, `filtered to ${shown(result)}, not ${shown(filtered)}`).toBe(true);
        expect(ms, `filterDecimalInput took ${ms.toFixed(0)} ms on ${text.length} characters`).toBeLessThan(BOUND_MS);
    });

    /*
     * Red before the W-B66 cure: the e is filtered out and the digits run together (…95, 1999…, …95). The
     * bound keeps the reading linear: on the last row, past its marker, a two-star pattern such as
     * `^-?\d*[.,]?\d*[eE][+-]?\d+$` takes 2.5 s (V8); `^-?(?:\d+(?:[.,]\d*)?|[.,]\d+)[eE][+-]?\d+$` 0.3 ms.
     */
    it.each(HUGE_MARKED)('filterDecimalInput reads %s, in linear time', (_label, text, expected) => {
        const {result, ms} = timed(() => filterDecimalInput(text));
        expect(result === expected, `read as ${shown(result)}, not ${shown(expected)}: today the e is filtered out`).toBe(true);
        expect(ms, `filterDecimalInput took ${ms.toFixed(0)} ms on ${text.length} characters`).toBeLessThan(BOUND_MS);
    });

    // Red before the W-B66 cure, for the same reason.
    it.each(HUGE_MARKED)('normalizeDecimalInput reads %s, in linear time', (_label, text, expected) => {
        const {result, ms} = timed(() => normalizeDecimalInput(text));
        expect(result === expected, `read as ${shown(result)}, not ${shown(expected)}: today the e is dropped`).toBe(true);
        expect(ms, `normalizeDecimalInput took ${ms.toFixed(0)} ms on ${text.length} characters`).toBeLessThan(BOUND_MS);
    });
});
