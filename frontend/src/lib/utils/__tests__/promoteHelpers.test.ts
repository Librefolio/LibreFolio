/**
 * Unit tests for cashAmountsCancel — pure promote helper.
 *
 * This function guards CASH_TRANSFER promote suggestions:
 * only pairs where amounts are exactly opposite (sum = 0)
 * should be promoted, preventing false positives from unrelated
 * transactions with the same type/date but different amounts.
 */
import {describe, expect, it} from 'vitest';
import {cashAmountsCancel, type CashCancelable} from '../transactions/promoteHelpers';

function op(amount: string | null): CashCancelable {
    return {fields: {cash: amount !== null ? {amount} : null}};
}

describe('cashAmountsCancel', () => {
    // --- true cases: exact cancellation ---------------------------------

    it('returns true for exact opposite integer amounts', () => {
        expect(cashAmountsCancel(op('-100'), op('100'))).toBe(true);
    });

    it('returns true for exact opposite decimal amounts', () => {
        expect(cashAmountsCancel(op('-360.87'), op('360.87'))).toBe(true);
    });

    it('returns true regardless of argument order', () => {
        expect(cashAmountsCancel(op('360.87'), op('-360.87'))).toBe(true);
    });

    it('handles very small amounts that cancel exactly', () => {
        expect(cashAmountsCancel(op('-0.01'), op('0.01'))).toBe(true);
    });

    // --- false cases: different amounts ---------------------------------

    it('returns false when amounts are clearly different', () => {
        // The real bug: CASH_OUT -360.87 matched with CASH_IN +1445.00
        expect(cashAmountsCancel(op('-360.87'), op('1445.00'))).toBe(false);
    });

    it('returns false for same sign (no cancellation)', () => {
        expect(cashAmountsCancel(op('100'), op('100'))).toBe(false);
    });

    it('returns false when amounts differ by 1 cent', () => {
        expect(cashAmountsCancel(op('-100.00'), op('100.01'))).toBe(false);
    });

    // --- false cases: missing cash field --------------------------------

    it('returns false when first op has cash=null', () => {
        expect(cashAmountsCancel(op(null), op('100'))).toBe(false);
    });

    it('returns false when second op has cash=null', () => {
        expect(cashAmountsCancel(op('-100'), op(null))).toBe(false);
    });

    it('returns false when both ops have cash=null', () => {
        expect(cashAmountsCancel(op(null), op(null))).toBe(false);
    });

    // --- edge: zero amounts ---------------------------------------------

    it('returns false when both amounts are zero (maxAbs=0 guard)', () => {
        expect(cashAmountsCancel(op('0'), op('0'))).toBe(false);
    });

    it('returns false when one amount is zero (non-cancelling)', () => {
        expect(cashAmountsCancel(op('0'), op('100'))).toBe(false);
    });
});
