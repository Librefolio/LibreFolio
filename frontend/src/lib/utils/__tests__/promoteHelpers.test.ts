/**
 * Unit tests for cashAmountsCancel — pure promote helper.
 *
 * This function guards CASH_TRANSFER promote suggestions:
 * only pairs where amounts are exactly opposite (sum = 0)
 * should be promoted, preventing false positives from unrelated
 * transactions with the same type/date but different amounts.
 *
 * The suite is split in two halves on purpose. The first half feeds SIGNED amounts, the
 * representation an import-pool row carries. The second half feeds NORMALISED amounts, the
 * representation `fieldsFromTx` produces for a row read from the database — where a
 * WITHDRAWAL of -11 is stored as "11" because the form shows a magnitude and the type
 * carries the sign. Both halves must give the same answers: that equivalence is the whole
 * point of routing the comparison through `signedCashAmount`, and it is what was broken
 * (edit+edit pairs could never be promoted, because +11 + +11 is never 0).
 */
import {describe, expect, it} from 'vitest';
import {cashAmountsCancel, mergeStrings, mergeTagSets, type CashCancelable} from '../transactions/promoteHelpers';
import type {TypeRule} from '$lib/stores/transactions/transactionTypeStore';

/** Rule stub — only `cashSign` is read by the helper under test. */
function rule(cashSign: string): TypeRule {
    return {cashSign} as unknown as TypeRule;
}

/** Type-rule resolver mirroring the real one for the three types used here. */
const resolve = (type: string): TypeRule => {
    if (type === 'CASH_OUT') return rule('negative');
    if (type === 'CASH_IN') return rule('positive');
    return rule('free'); // ADJUSTMENT / TRANSFER legs: the stored sign is meaningful
};

function op(amount: string | null, type = 'FREE'): CashCancelable {
    return {fields: {type, cash: amount !== null ? {code: 'EUR', amount} : null}};
}

describe('cashAmountsCancel', () => {
    // --- true cases: exact cancellation ---------------------------------

    it('returns true for exact opposite integer amounts', () => {
        expect(cashAmountsCancel(op('-100'), op('100'), resolve)).toBe(true);
    });

    it('returns true for exact opposite decimal amounts', () => {
        expect(cashAmountsCancel(op('-360.87'), op('360.87'), resolve)).toBe(true);
    });

    it('returns true regardless of argument order', () => {
        expect(cashAmountsCancel(op('360.87'), op('-360.87'), resolve)).toBe(true);
    });

    it('handles very small amounts that cancel exactly', () => {
        expect(cashAmountsCancel(op('-0.01'), op('0.01'), resolve)).toBe(true);
    });

    // --- false cases: different amounts ---------------------------------

    it('returns false when amounts are clearly different', () => {
        // The real bug: CASH_OUT -360.87 matched with CASH_IN +1445.00
        expect(cashAmountsCancel(op('-360.87'), op('1445.00'), resolve)).toBe(false);
    });

    it('returns false for same sign (no cancellation)', () => {
        expect(cashAmountsCancel(op('100'), op('100'), resolve)).toBe(false);
    });

    it('returns false when amounts differ by 1 cent', () => {
        expect(cashAmountsCancel(op('-100.00'), op('100.01'), resolve)).toBe(false);
    });

    // --- false cases: missing cash field --------------------------------

    it('returns false when first op has cash=null', () => {
        expect(cashAmountsCancel(op(null), op('100'), resolve)).toBe(false);
    });

    it('returns false when second op has cash=null', () => {
        expect(cashAmountsCancel(op('-100'), op(null), resolve)).toBe(false);
    });

    it('returns false when both ops have cash=null', () => {
        expect(cashAmountsCancel(op(null), op(null), resolve)).toBe(false);
    });

    // --- edge: zero amounts ---------------------------------------------

    it('returns false when both amounts are zero (maxAbs=0 guard)', () => {
        expect(cashAmountsCancel(op('0'), op('0'), resolve)).toBe(false);
    });

    it('returns false when one amount is zero (non-cancelling)', () => {
        expect(cashAmountsCancel(op('0'), op('100'), resolve)).toBe(false);
    });
});

describe('cashAmountsCancel — representation independence', () => {
    // A row read from the DB is normalised to a magnitude by fieldsFromTx: a WITHDRAWAL of
    // -11 becomes "11". Every case below is the same money as the signed cases above.

    it('cancels a normalised (DB) pair — the edit+edit case that never worked', () => {
        const withdrawal = op('11', 'CASH_OUT'); // stored as a magnitude
        const deposit = op('11', 'CASH_IN');
        expect(cashAmountsCancel(withdrawal, deposit, resolve)).toBe(true);
    });

    it('cancels a mixed pair — one row from the pool, one from the DB', () => {
        const fromPool = op('-11', 'CASH_OUT'); // already signed
        const fromDb = op('11', 'CASH_IN'); // normalised
        expect(cashAmountsCancel(fromPool, fromDb, resolve)).toBe(true);
    });

    it('is idempotent: the stored sign never changes the answer for a signed type', () => {
        // Same money, four ways of writing it. A rule that flipped instead of coercing
        // ("multiply by -1" rather than "-Math.abs") would give different answers here.
        const expected = true;
        expect(cashAmountsCancel(op('-11', 'CASH_OUT'), op('11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('-11', 'CASH_OUT'), op('-11', 'CASH_IN'), resolve)).toBe(expected);
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('-11', 'CASH_IN'), resolve)).toBe(expected);
    });

    it('still rejects a normalised pair with different amounts', () => {
        expect(cashAmountsCancel(op('11', 'CASH_OUT'), op('12', 'CASH_IN'), resolve)).toBe(false);
    });

    it('leaves free-sign types untouched, where the stored sign is the information', () => {
        // Two ADJUSTMENTs of +50 do not cancel; +50 and -50 do. Coercing either one would
        // destroy the only thing distinguishing them.
        expect(cashAmountsCancel(op('50'), op('50'), resolve)).toBe(false);
        expect(cashAmountsCancel(op('50'), op('-50'), resolve)).toBe(true);
    });

    it('returns false when an amount is not a number', () => {
        expect(cashAmountsCancel(op('abc'), op('100'), resolve)).toBe(false);
    });
});

/**
 * mergeStrings / mergeTagSets — pure field-merge helpers used by PromoteMergeModal to pre-fill
 * the resolved description and tags when two rows are merged into a promoted pair.
 */
describe('mergeStrings', () => {
    it('returns the other side when one is empty', () => {
        expect(mergeStrings('', 'B')).toBe('B');
        expect(mergeStrings('A', '')).toBe('A');
    });

    it('returns both empty as empty (first-branch short-circuit)', () => {
        expect(mergeStrings('', '')).toBe('');
    });

    it('collapses identical sides to a single copy', () => {
        expect(mergeStrings('same', 'same')).toBe('same');
    });

    it('stacks two distinct values on separate lines', () => {
        expect(mergeStrings('first', 'second')).toBe('first\nsecond');
    });
});

describe('mergeTagSets', () => {
    it('unions two lists and de-duplicates, preserving first-seen order', () => {
        expect(mergeTagSets(['a', 'b'], ['b', 'c'])).toEqual(['a', 'b', 'c']);
    });

    it('treats a nullish first list as empty', () => {
        expect(mergeTagSets(null as unknown as string[], ['x'])).toEqual(['x']);
    });

    it('treats a nullish second list as empty', () => {
        expect(mergeTagSets(['x'], undefined as unknown as string[])).toEqual(['x']);
    });

    it('returns [] when both are nullish', () => {
        expect(mergeTagSets(null as unknown as string[], null as unknown as string[])).toEqual([]);
    });
});
