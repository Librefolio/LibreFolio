/**
 * formatShare — a share of the portfolio never prints as zero unless it is one.
 *
 * Developer's decision of 01/10/2026, «per le quote sotto l'1% metti un decimale o
 * due», refined and approved the same day. The digits follow the magnitude of the
 * share, in percent:
 *
 *   - from 1 % up, the caller's own format, so large figures do not move;
 *   - from 0.1 % to just under 1 %, at least one decimal;
 *   - under 0.1 %, at least two;
 *   - a share that two decimals would still round to zero reads «< 0.01%», or
 *     «> -0.01%» when negative — so only a true zero prints as zero.
 *
 * Every expected string is a literal written here. One computed with `formatPercent`,
 * which `formatShare` keeps for the large shares, would agree with the code by
 * construction and pin nothing.
 *
 * Each threshold is probed on both sides, with values whose product by 100 lands
 * exactly where it reads: `0.01 * 100 === 1` and `0.001 * 100 === 0.1` both hold in
 * binary floating point, so a red at an edge is about the rule, never about the
 * representation. The two-decimal edge is approached at 0.00499 % and 0.00501 % for the
 * same reason — at 0.005 % itself, the digit `toFixed` prints depends on which side of
 * the half the double happens to fall.
 *
 * `\u00A0` in the expected strings is a NO-BREAK SPACE, and its four hex digits end the
 * escape: `'<\u00A00.01%'` is «<», the space, then `0.01%`. Inside a sentence, «<» must
 * never end a line alone.
 */
import {describe, expect, it} from 'vitest';

import {formatShare} from './shareFormat';

/** The bases the function accepts, read off its signature so the cases follow it. */
type BaseDigits = Parameters<typeof formatShare>[1];

/** L3's sentences under the scatter write a share in whole percentages. */
const L3_DIGITS: BaseDigits = 0;
/** L2 writes it with one decimal: the card, the residual line, weights and contributions. */
const L2_DIGITS: BaseDigits = 1;

describe('formatShare', () => {
    describe("at base 0, as in L3's sentences under the scatter", () => {
        it('leaves 31 % as L3 always printed it: nothing changes from 1 % up', () => {
            expect(formatShare(0.31, L3_DIGITS), 'a share of 1 % or more must keep the caller format: no decimal is added to 31 %').toBe('31%');
        });

        it('keeps exactly 1 % in the caller format: the threshold belongs to the large shares', () => {
            expect(formatShare(0.01, L3_DIGITS), 'exactly 1 % must read «1%»: it is the first share in the caller format, not the last in the one-decimal band').toBe('1%');
        });

        it('gives 0.99 % its decimal, even though it rounds to one', () => {
            // The band is chosen on the share, not on the figure it rounds to. Printed
            // whole, 0.99 % would read «1%», as if it had reached the line it sits under.
            expect(formatShare(0.0099, L3_DIGITS), '0.99 % is under 1 %, so it must carry one decimal, even if that decimal is a zero').toBe('1.0%');
        });

        it('prints 0.4 % as 0.4 %, not as zero: the case the rule was written for', () => {
            // The developer's example: 0.4 % of net worth in cash, printed whole, reads
            // «0%» — a claim the data does not make.
            expect(formatShare(0.004, L3_DIGITS), 'a 0.4 % share must read «0.4%»: printed whole it reads «0%», as if the holding were not there').toBe('0.4%');
        });

        it('keeps exactly 0.1 % in the one-decimal band', () => {
            expect(formatShare(0.001, L3_DIGITS), 'exactly 0.1 % must read «0.1%»: it is the first share in the one-decimal band, not the last in the two-decimal band').toBe('0.1%');
        });

        it('gives 0.099 % two decimals, even though one would round it to 0.1', () => {
            expect(formatShare(0.00099, L3_DIGITS), '0.099 % is under 0.1 %, so it must carry two decimals, even if the second is a zero').toBe('0.10%');
        });

        it('prints 0.05 % with the two decimals that neither erase it nor double it', () => {
            expect(formatShare(0.0005, L3_DIGITS), 'a 0.05 % share must read «0.05%»: with no decimal it reads «0%», with one it rounds up to «0.1%», twice its size').toBe('0.05%');
        });

        it('prints 0.01 %, the smallest share two decimals can still show', () => {
            expect(formatShare(0.0001, L3_DIGITS), 'two decimals can show 0.01 %, so it must read «0.01%»: neither «0%» nor «< 0.01%»').toBe('0.01%');
        });
    });

    describe("at base 1, as in L2's card, residual line, weights and contributions", () => {
        // L2 already prints the one decimal the band between 0.1 % and 1 % asks for, so
        // in that band its figures read as they did before the rule: only the shares
        // under 0.1 % change.

        it('leaves 30.6 % as L2 always printed it: nothing changes from 1 % up', () => {
            expect(formatShare(0.306, L2_DIGITS), "a share of 1 % or more must keep the caller format: 30.6 % keeps L2's one decimal and gains no other").toBe('30.6%');
        });

        it("adds no second decimal to 0.4 %: L2's own decimal is all the band asks for", () => {
            // «At least one decimal» raises the caller's digits; it does not replace them.
            // This case reads the same with or without the rule, and is here to pin that
            // the rule does not overshoot: a red reading «0.40%» means the band imposed
            // its own count on a caller that already had enough.
            expect(formatShare(0.004, L2_DIGITS), "a 0.4 % share must read «0.4%» at base 1: L2's decimal already satisfies the band, and a second one is not due").toBe('0.4%');
        });

        it("gives 0.05 % the second decimal that L2's single one would round away", () => {
            expect(formatShare(0.0005, L2_DIGITS), "a 0.05 % share must read «0.05%»: with L2's single decimal it rounds up to «0.1%», twice its size").toBe('0.05%');
        });

        it('writes 0.004 % as «< 0.01%», because two decimals still round it to zero', () => {
            expect(formatShare(0.00004, L2_DIGITS), 'a 0.004 % share is not nothing: it must read «< 0.01%», never «0.0%», which only a true zero may print').toBe('<\u00A00.01%');
        });
    });

    describe('at the edge where two decimals print zero', () => {
        // The floor has no threshold of its own: it applies exactly when two decimals
        // would print zero, whatever the caller's base.

        it.each([L3_DIGITS, L2_DIGITS])('at base %i, floors 0.00499 %: two decimals print it as zero', (base) => {
            expect(formatShare(0.0000499, base), `0.00499 % prints «0.00» at two decimals, so at base ${base} it must read «< 0.01%»`).toBe('<\u00A00.01%');
        });

        it.each([L3_DIGITS, L2_DIGITS])('at base %i, prints 0.00501 %: two decimals round it up to 0.01', (base) => {
            expect(formatShare(0.0000501, base), `0.00501 % prints «0.01» at two decimals, so at base ${base} it must read «0.01%», not the floor`).toBe('0.01%');
        });
    });

    describe('of a true zero', () => {
        // The floor is for shares that exist and are too small to show. Zero is not one
        // of them: it reads as the caller's own zero.
        const ZEROS: [base: BaseDigits, expected: string][] = [
            [L3_DIGITS, '0%'],
            [L2_DIGITS, '0.0%'],
        ];

        it.each(ZEROS)('at base %i, prints 0 as %s', (base, expected) => {
            expect(formatShare(0, base), `zero is a fact, not a small share: at base ${base} it must read «${expected}», never «< 0.01%»`).toBe(expected);
        });

        it.each(ZEROS)('at base %i, prints -0 as %s, without a sign', (base, expected) => {
            expect(formatShare(-0, base), `-0 is zero: at base ${base} it must read «${expected}», with no minus and never «> -0.01%»`).toBe(expected);
        });
    });

    describe("of a negative share, as in L2's contributions", () => {
        // Only L2's contribution column can go below zero: a hedge that lowers the
        // portfolio's risk. The band follows the magnitude, so a small negative gets the
        // digits of a small positive, and the floor mirrors: «> -0.01%» is below zero,
        // but closer to it than two decimals can show.
        //
        // Base 1 is the one that ships. The small ones are pinned at base 0 as well, the
        // way the positive ones are: at base 1, L2's own decimal is already what the
        // one-decimal band asks for, so -0.3 % reads the same with or without the rule —
        // at base 0, without it, it reads «-0%».
        //
        // The minus is the ASCII hyphen-minus `formatPercent` prints. The U+2212 of L2's
        // divergence column is composed by that column, and is not this function's.

        it("keeps -31 % in L2's own format, minus sign included", () => {
            expect(formatShare(-0.31, L2_DIGITS), "a -31 % contribution must read «-31.0%»: L2's one decimal and its minus sign, nothing else").toBe('-31.0%');
        });

        it.each([L3_DIGITS, L2_DIGITS])('at base %i, gives -0.3 % the decimal its size calls for', (base) => {
            expect(formatShare(-0.003, base), `a -0.3 % contribution must read «-0.3%» at base ${base}: the band follows the magnitude, and «-0%» is a zero with a sign`).toBe('-0.3%');
        });

        it.each([L3_DIGITS, L2_DIGITS])('at base %i, gives -0.05 % two decimals', (base) => {
            expect(formatShare(-0.0005, base), `a -0.05 % contribution must read «-0.05%» at base ${base}: one decimal doubles it to «-0.1%», none prints «-0%»`).toBe('-0.05%');
        });

        it.each([L3_DIGITS, L2_DIGITS])('at base %i, writes -0.004 % as «> -0.01%», because two decimals still round it to zero', (base) => {
            expect(formatShare(-0.00004, base), `a -0.004 % contribution must read «> -0.01%» at base ${base}: «-0.0%» is a zero with a sign`).toBe('>\u00A0-0.01%');
        });
    });

    describe('of something that is not a share', () => {
        // Missing or non-finite input prints the placeholder `formatPercent` prints, at
        // either base. A zero or the floor would each invent a value.

        it.each([null, undefined, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])('prints the placeholder for %s, at either base', (value) => {
            expect(formatShare(value, L3_DIGITS), `${String(value)} is not a share: at base 0 it must print «—», never a figure`).toBe('—');
            expect(formatShare(value, L2_DIGITS), `${String(value)} is not a share: at base 1 it must print «—», never a figure`).toBe('—');
        });
    });

    describe('the space after «<» and «>»', () => {
        it('is U+00A0, so a regular space cannot pass for it', () => {
            // The expected strings above already carry `\u00A0`, but an escape is easy to
            // tidy into a literal character, and a literal no-break space looks like any
            // other space in a diff. A code point compared as a number cannot be mistaken.
            expect(formatShare(0.00004, L2_DIGITS).charCodeAt(1), 'the character after «<» must be U+00A0 NO-BREAK SPACE, or «<» can end a line alone').toBe(0xa0);
            expect(formatShare(-0.00004, L2_DIGITS).charCodeAt(1), 'the character after «>» must be U+00A0 NO-BREAK SPACE, or «>» can end a line alone').toBe(0xa0);
        });
    });
});
