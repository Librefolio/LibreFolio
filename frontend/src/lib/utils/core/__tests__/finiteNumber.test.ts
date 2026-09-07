/**
 * finiteNumber.test.ts — "is this a plottable number?" guard.
 *
 * The edge cases are the reason it exists as a *distinct* helper from
 * `safeNumber`: it rejects `NaN`/`Infinity` (which `safeNumber` passes through)
 * and rejects arrays (which `safeNumber` unwraps). Those rows are asserted
 * explicitly so a future "just reuse safeNumber" never slips through green.
 */
import {describe, expect, it} from 'vitest';
import {finiteNumber} from '../finiteNumber';
import {safeNumber} from '$lib/types/common';

describe('finiteNumber', () => {
    it('accepts finite numbers, including 0 and negatives', () => {
        expect(finiteNumber(0)).toBe(0);
        expect(finiteNumber(42)).toBe(42);
        expect(finiteNumber(-3.5)).toBe(-3.5);
    });

    it('rejects NaN and both infinities', () => {
        expect(finiteNumber(NaN)).toBeNull();
        expect(finiteNumber(Infinity)).toBeNull();
        expect(finiteNumber(-Infinity)).toBeNull();
    });

    it('rejects null, undefined and empty string', () => {
        expect(finiteNumber(null)).toBeNull();
        expect(finiteNumber(undefined)).toBeNull();
        expect(finiteNumber('')).toBeNull();
    });

    it('rejects numeric strings (it is a number guard, not a parser)', () => {
        expect(finiteNumber('12.34')).toBeNull();
        expect(finiteNumber('0')).toBeNull();
    });

    it('rejects arrays and objects', () => {
        expect(finiteNumber([5])).toBeNull();
        expect(finiteNumber([])).toBeNull();
        expect(finiteNumber({value: 5})).toBeNull();
    });

    it('diverges from safeNumber on exactly the cases it was written to filter', () => {
        // Documented contract: these two must never be swapped.
        expect(safeNumber(NaN)).toBeNaN();
        expect(finiteNumber(NaN)).toBeNull();
        expect(safeNumber(Infinity)).toBe(Infinity);
        expect(finiteNumber(Infinity)).toBeNull();
        expect(safeNumber([5])).toBe(5);
        expect(finiteNumber([5])).toBeNull();
    });
});
