/**
 * decimal — the exact display rounding of the PAC planner (R14, Vitest, node).
 *
 * Subject. R14 shows an amount the backend computed at the minor unit of its currency, and a
 * solver count to two decimals. The rounding is done here, on decimal text, never on a float:
 *   - `roundDecimal(text, places)` rounds a plain decimal to `places` fraction digits;
 *   - `roundRatio(numerator, denominator, places)` rounds the exact ratio of two integers;
 *   - `decimalEqualsRatio(text, numerator, denominator)` tells whether a decimal *is* the ratio,
 *     which is how the formatter decides whether a rounded ratio deserves `≈`.
 * The rule is half away from zero, symmetric in the sign, done with `BigInt`.
 *
 * Expectations. Every expected value is a literal worked out by hand from that rule. Literals
 * are safe here because nothing in this module reads the locale: the output is wire-form
 * decimal text. Each half-way case is paired with its mirror of the opposite sign, and the
 * neighbours just below the half are there so that a rule which always rounds up would fail.
 *
 * Canonical output. A result never carries trailing zeros and is never `-0`. A value that
 * rounds to zero loses its sign, and a value that already has `places` digits or fewer comes
 * back in canonical form, with no padding.
 *
 * Refusals. Plain decimal text only: no exponent, no `+`, no grouping, no hex. Ratio operands
 * must be plain integers, because `BigInt` alone would read `''`, `0x10` and padded text. A
 * zero denominator gives `null` from the rounders, and `false` from the equality, even for 0/0.
 *
 * Exactness. Several values are far beyond the 15-17 significant digits of a double. A
 * float-based implementation would round or drop their low digits, so these cases separate
 * "exact" from "close enough".
 */
import {describe, expect, it} from 'vitest';
import {decimalEqualsRatio, roundDecimal, roundRatio} from './decimal';

/** 30 significant digits: twice what a double carries. */
const BIG = '123456789012345678901234567890';

describe('roundDecimal — exact, half away from zero', () => {
    it.each([
        ['1.005', 2, '1.01'],
        ['-1.005', 2, '-1.01'],
        ['0.125', 2, '0.13'],
        ['-0.125', 2, '-0.13'],
        ['-0.005', 2, '-0.01'],
        ['2.5', 0, '3'],
        ['-2.5', 0, '-3'],
        ['1234.5', 0, '1235'],
        ['-1234.5', 0, '-1235'],
        ['1.25', 1, '1.3'],
        ['-1.25', 1, '-1.3'],
    ])('rounds the half-way %s at %i places away from zero: %s', (text, places, expected) => {
        expect(roundDecimal(text, places)).toBe(expected);
    });

    it('is exact where a float is not: 1.005 is a half-way case, and a double does not store it', () => {
        // Premise: the double nearest to 1.005 sits just below it, so the float route says 1.00.
        expect((1.005).toFixed(2)).toBe('1.00');
        expect(Math.round(1.005 * 100) / 100).toBe(1);

        expect(roundDecimal('1.005', 2)).toBe('1.01');
    });

    it.each([
        ['2.4999', 0, '2'],
        ['-2.4999', 0, '-2'],
        ['1.004', 2, '1'],
        ['1.0049999', 2, '1'],
        ['0.0051', 2, '0.01'],
        ['-0.0051', 2, '-0.01'],
        ['1234.4999', 0, '1234'],
        ['0.49', 0, '0'],
        ['0.5', 0, '1'],
        ['-0.5', 0, '-1'],
    ])('rounds %s at %i places to the nearest neighbour: %s', (text, places, expected) => {
        expect(roundDecimal(text, places)).toBe(expected);
    });

    it.each([
        ['-0.004', 2],
        ['-0.0049', 2],
        ['-0.49', 0],
        ['-0.4', 0],
    ])('never returns -0: %s at %i places rounds to an unsigned 0', (text, places) => {
        expect(roundDecimal(text, places)).toBe('0');
    });

    it.each([
        ['1.5', 2, '1.5'],
        ['1.50', 2, '1.5'],
        ['1.500', 2, '1.5'],
        ['7', 2, '7'],
        ['7', 0, '7'],
        ['-12.3', 2, '-12.3'],
        ['0.00', 2, '0'],
        ['-0', 2, '0'],
        ['-0.00', 2, '0'],
        ['007.10', 2, '7.1'],
        ['.5', 2, '0.5'],
        ['5.', 0, '5'],
        [' 1.25 ', 2, '1.25'],
    ])('returns %j at %i places in canonical form, with no padding: %s', (text, places, expected) => {
        expect(roundDecimal(text, places)).toBe(expected);
    });

    it('strips the trailing zeros a rounding leaves behind', () => {
        expect(roundDecimal('1.004', 2), '1.00 → 1').toBe('1');
        expect(roundDecimal('2.0951', 2), '2.10 → 2.1').toBe('2.1');
        expect(roundDecimal('9.996', 2), 'the carry ripples into the integer part: 10.00 → 10').toBe('10');
        expect(roundDecimal('-9.996', 2)).toBe('-10');
    });

    it.each(['1e3', '1E3', '1.5e-2', '+1', '+1.5', '1,000', '1.000,5', '1 000', '', '   ', 'abc', '-', '.', '-.', '1.2.3', '--1', '0x10', 'NaN', 'Infinity', '-Infinity', '١٢'])('refuses the non-plain text %j', (text) => {
        expect(roundDecimal(text, 2)).toBeNull();
    });

    it.each([-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])('refuses places = %d, which is not a non-negative integer', (places) => {
        expect(roundDecimal('1.5', places)).toBeNull();
    });

    it('keeps every digit of a value a double cannot hold', () => {
        const text = `${BIG}.125`;
        // Premise: through a double the low digits are gone before any rounding starts.
        expect(String(Number(text))).not.toContain(BIG);

        expect(roundDecimal(text, 2)).toBe(`${BIG}.13`);
        expect(roundDecimal(`-${text}`, 2)).toBe(`-${BIG}.13`);
        expect(roundDecimal(`${BIG}.4999`, 0)).toBe(BIG);
        expect(roundDecimal(`${BIG}.5`, 0)).toBe('123456789012345678901234567891');
    });

    it('carries a half-way rounding through thirty nines, in both signs', () => {
        const nines = '9'.repeat(30);
        const power = '1' + '0'.repeat(30);

        expect(roundDecimal(`${nines}.995`, 2)).toBe(power);
        expect(roundDecimal(`-${nines}.995`, 2)).toBe(`-${power}`);
        expect(roundDecimal(`${nines}.994`, 2), 'just below the half: no carry').toBe(`${nines}.99`);
    });
});

describe('roundRatio — an exact ratio of two integers, half away from zero', () => {
    it.each([
        ['1', '3', 2, '0.33'],
        ['2', '3', 2, '0.67'],
        ['-2', '3', 2, '-0.67'],
        ['2', '-3', 2, '-0.67'],
        ['-2', '-3', 2, '0.67'],
        ['1', '8', 2, '0.13'],
        ['-1', '8', 2, '-0.13'],
        ['1', '-8', 2, '-0.13'],
        ['-1', '-8', 2, '0.13'],
        ['5', '2', 0, '3'],
        ['-5', '2', 0, '-3'],
        ['5', '-2', 0, '-3'],
        ['10', '4', 1, '2.5'],
        ['1', '3', 0, '0'],
        ['2', '3', 0, '1'],
        ['1234567', '1000', 2, '1234.57'],
    ])('%s / %s at %i places is %s', (numerator, denominator, places, expected) => {
        expect(roundRatio(numerator, denominator, places)).toBe(expected);
    });

    it.each([
        ['-1', '300', 2],
        ['1', '-300', 2],
        ['-1', '201', 2],
        ['-1', '3', 0],
    ])('never returns -0: %s / %s at %i places rounds to an unsigned 0', (numerator, denominator, places) => {
        expect(roundRatio(numerator, denominator, places)).toBe('0');
    });

    it.each([
        ['10', '4', 3, '2.5'],
        ['6', '3', 2, '2'],
        ['-6', '3', 2, '-2'],
        ['0', '7', 2, '0'],
        ['1', '4', 18, '0.25'],
    ])('returns %s / %s at %i places in canonical form, with no trailing zeros: %s', (numerator, denominator, places, expected) => {
        expect(roundRatio(numerator, denominator, places)).toBe(expected);
    });

    it('keeps 30 fraction digits exactly, beyond what a double resolves', () => {
        expect(roundRatio('1', '3', 30)).toBe('0.' + '3'.repeat(30));
        expect(roundRatio('2', '3', 30)).toBe('0.' + '6'.repeat(29) + '7');
        expect(roundRatio('-2', '3', 30)).toBe('-0.' + '6'.repeat(29) + '7');
    });

    it('keeps every digit of a 30-digit numerator', () => {
        expect(roundRatio(BIG, '1', 2)).toBe(BIG);
        expect(roundRatio(`-${BIG}`, '1', 0)).toBe(`-${BIG}`);
        // 123456789012345678901234567891 / 2 = 61728394506172839450617283945.5 exactly: half away from zero.
        expect(roundRatio('123456789012345678901234567891', '2', 0)).toBe('61728394506172839450617283946');
        expect(roundRatio('-123456789012345678901234567891', '2', 0)).toBe('-61728394506172839450617283946');
        expect(roundRatio(BIG, '3', 2)).toBe('41152263004115226300411522630');
    });

    it.each(['', '1.5', '0x10', ' 3', '3 ', '1e3', '+3', '-', 'abc', '1_000', '١'])('refuses the operand %j, as numerator and as denominator', (operand) => {
        expect(roundRatio(operand, '3', 2), 'numerator').toBeNull();
        expect(roundRatio('1', operand, 2), 'denominator').toBeNull();
    });

    it('refuses what BigInt alone would have read', () => {
        // Premise: these are the shapes the plain-integer guard exists for.
        expect(BigInt('')).toBe(0n);
        expect(BigInt('0x10')).toBe(16n);
        expect(BigInt(' 3')).toBe(3n);

        expect(roundRatio('0x10', '3', 2)).toBeNull();
        expect(roundRatio(' 3', '3', 2)).toBeNull();
        expect(roundRatio('1', '', 2), 'an empty denominator is not a zero to divide by').toBeNull();
    });

    it.each(['0', '-0', '00'])('refuses the zero denominator %j', (denominator) => {
        expect(roundRatio('1', denominator, 2)).toBeNull();
        expect(roundRatio('0', denominator, 2)).toBeNull();
    });

    it.each([-1, 1.5, Number.NaN, Number.POSITIVE_INFINITY])('refuses places = %d, which is not a non-negative integer', (places) => {
        expect(roundRatio('1', '3', places)).toBeNull();
    });
});

describe('decimalEqualsRatio — whether a decimal is exactly the ratio', () => {
    it.each([
        ['0.5', '1', '2'],
        ['0.50', '1', '2'],
        ['1', '3', '3'],
        ['2.5', '10', '4'],
        ['-0.25', '1', '-4'],
        ['-0.25', '-1', '4'],
        ['0.25', '-1', '-4'],
        ['0', '0', '5'],
        ['0.125', '1', '8'],
    ])('%s equals %s / %s', (text, numerator, denominator) => {
        expect(decimalEqualsRatio(text, numerator, denominator)).toBe(true);
    });

    it.each([
        ['0.33', '1', '3'],
        ['0.0' + '3'.repeat(30), '1', '30'],
        ['0.' + '3'.repeat(30), '1', '3'],
        ['0.25', '1', '-4'],
        ['-0.25', '1', '4'],
        ['0.13', '1', '8'],
        ['2.4', '5', '2'],
    ])('%s does not equal %s / %s', (text, numerator, denominator) => {
        expect(decimalEqualsRatio(text, numerator, denominator)).toBe(false);
    });

    it('agrees with roundRatio: a rounding that changed nothing is the ratio, any other is not', () => {
        expect(decimalEqualsRatio(roundRatio('10', '4', 1) as string, '10', '4')).toBe(true);
        expect(decimalEqualsRatio(roundRatio('1', '8', 3) as string, '1', '8')).toBe(true);
        expect(decimalEqualsRatio(roundRatio('1', '8', 2) as string, '1', '8')).toBe(false);
        expect(decimalEqualsRatio(roundRatio('1', '3', 2) as string, '1', '3')).toBe(false);
    });

    it('compares exactly at 30 digits, where a double sees two equal numbers', () => {
        const quotient = '41152263004115226300411522630';
        const nextUp = '41152263004115226300411522631';
        // Premise: a double cannot tell the two quotients apart.
        expect(Number(quotient)).toBe(Number(nextUp));

        expect(decimalEqualsRatio(quotient, BIG, '3')).toBe(true);
        expect(decimalEqualsRatio(nextUp, BIG, '3')).toBe(false);
    });

    it.each([
        ['1', '1', '0'],
        ['0', '5', '0'],
        ['0', '0', '-0'],
    ])('is false for a zero denominator: %s vs %s / %s', (text, numerator, denominator) => {
        expect(decimalEqualsRatio(text, numerator, denominator)).toBe(false);
    });

    it('is false for 0/0, although the cross-product 0 × 0 = 0 × 1 would call it equal', () => {
        expect(decimalEqualsRatio('0', '0', '0')).toBe(false);
        expect(decimalEqualsRatio('0.00', '0', '00')).toBe(false);
    });

    it.each(['abc', '1e3', '', '+0.5', '0,5'])('is false for the non-plain decimal %j', (text) => {
        expect(decimalEqualsRatio(text, '1', '2')).toBe(false);
    });

    it.each([
        ['+1', '2'],
        [' 1', '2'],
        ['1 ', '2'],
        ['0x1', '2'],
        ['1', '+2'],
        ['1', ' 2'],
        ['1', '0x2'],
    ])('is false for %j / %j, which BigInt alone would read as the true 1/2', (numerator, denominator) => {
        // Premise: without the plain-integer guard this pair would equal 0.5.
        expect(BigInt(numerator) * 2n).toBe(BigInt(denominator));

        expect(decimalEqualsRatio('0.5', numerator, denominator)).toBe(false);
    });

    it.each(['1.5', '1e0'])('is false, instead of throwing like BigInt, for the operand %j', (operand) => {
        expect(() => BigInt(operand)).toThrow(SyntaxError);

        expect(decimalEqualsRatio('0.5', operand, '2'), 'numerator').toBe(false);
        expect(decimalEqualsRatio('0.5', '1', operand), 'denominator').toBe(false);
    });
});
