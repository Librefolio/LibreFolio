import {describe, expect, it} from 'vitest';
import {formatPercent} from '../formatPercent';

/**
 * These pin the five behaviours that used to live in five private copies, because
 * the copies disagreed and the disagreement was invisible: each one was correct
 * where it stood, and wrong anywhere else.
 *
 * The one that matters is `scale`. `formatPercent(2.5)` and
 * `formatPercent(0.025, {scale: 100})` must both print "2.50%" — get that
 * backwards and every figure on the affected screen is off by a hundred, with
 * nothing failing to say so.
 */
describe('formatPercent', () => {
    describe('scale', () => {
        it('treats the value as already a percentage by default', () => {
            expect(formatPercent(2.5)).toBe('+2.50%');
            expect(formatPercent(-2.5)).toBe('-2.50%');
        });

        it('multiplies a fraction when told the value is one', () => {
            expect(formatPercent(0.025, {scale: 100})).toBe('+2.50%');
            expect(formatPercent(-0.025, {scale: 100})).toBe('-2.50%');
        });

        it('agrees with itself across the two scales', () => {
            // The property the five copies violated: the same quantity, expressed
            // either way, must print identically.
            expect(formatPercent(7.25)).toBe(formatPercent(0.0725, {scale: 100}));
        });
    });

    describe('sign', () => {
        it('marks positives with a plus by default', () => {
            expect(formatPercent(1)).toBe('+1.00%');
        });

        it('omits the plus when the caller does not want a comparison', () => {
            expect(formatPercent(1, {signed: false})).toBe('1.00%');
            // A negative keeps its sign either way — that one is arithmetic, not decoration.
            expect(formatPercent(-1, {signed: false})).toBe('-1.00%');
        });

        it('never marks zero as positive', () => {
            expect(formatPercent(0)).toBe('0.00%');
        });
    });

    describe('negative zero', () => {
        it('prints a plain zero', () => {
            // `-0` survives multiplication and toFixed renders it "-0.00%", which
            // reads as a small loss. Two of the five copies guarded against this
            // and three did not, so the same value rendered differently depending
            // on which chart you were looking at.
            expect(formatPercent(-0)).toBe('0.00%');
            expect(formatPercent(-0.0000001, {scale: 100})).toBe('-0.00%');
        });

        it('handles a negative zero arriving through the scale', () => {
            expect(formatPercent(-0, {scale: 100})).toBe('0.00%');
        });
    });

    describe('missing values', () => {
        it('prints an em dash for null and undefined', () => {
            expect(formatPercent(null)).toBe('—');
            expect(formatPercent(undefined)).toBe('—');
        });

        it('prints an em dash for values that are not finite', () => {
            // A ratio whose denominator was zero reaches here as Infinity, and
            // "∞%" is not a fact about the portfolio.
            expect(formatPercent(Infinity)).toBe('—');
            expect(formatPercent(-Infinity)).toBe('—');
            expect(formatPercent(NaN)).toBe('—');
        });

        it('lets the caller choose the placeholder', () => {
            expect(formatPercent(null, {empty: 'n/a'})).toBe('n/a');
            expect(formatPercent(null, {empty: ''})).toBe('');
        });
    });

    describe('digits', () => {
        it('uses two decimals by default', () => {
            expect(formatPercent(1.5)).toBe('+1.50%');
            expect(formatPercent(1.239)).toBe('+1.24%');
        });

        it('honours a different precision', () => {
            expect(formatPercent(1.2345, {digits: 0})).toBe('+1%');
            expect(formatPercent(1.6, {digits: 0})).toBe('+2%');
            expect(formatPercent(1.2349, {digits: 3})).toBe('+1.235%');
        });

        it('rounds the way toFixed does, which is not the way school does', () => {
            // `(1.005).toFixed(2)` is "1.00", not "1.01": 1.005 has no exact binary
            // representation and the stored value sits just below the midpoint, so
            // it rounds down. Pinned because it looks like a bug in the formatter
            // when it is a property of the language, and because anyone tempted to
            // "fix" it by adding an epsilon should see this test first.
            expect(formatPercent(1.005)).toBe('+1.00%');
            expect(formatPercent(1.2345, {digits: 3})).toBe('+1.234%');
        });
    });
});
