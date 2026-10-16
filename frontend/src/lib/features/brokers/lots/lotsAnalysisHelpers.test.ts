/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * LotsAnalysisPanel.svelte: the redundant-union unwrappers, the open-ness
 * predicate, the open/closed visibility filter, the quote-base clamp, and the
 * double-click lot gathering. No fetch, no DOM, no ECharts.
 */
import {describe, it, expect} from 'vitest';
import {asArray, asObject, lotIsOpenish, filterVisibleLots, normalizeQuoteBaseQuantity, collectInvolvedLotIds, type LotOpenish, type InvolvedEventRow} from './lotsAnalysisHelpers';

describe('asArray', () => {
    it('returns [] for null / undefined (falsy → first guard)', () => {
        expect(asArray<number>(null)).toEqual([]);
        expect(asArray<number>(undefined)).toEqual([]);
    });

    it('returns [] for a non-array truthy value (!isArray → first guard)', () => {
        expect(asArray<number>({} as unknown)).toEqual([]);
        expect(asArray<number>('nope')).toEqual([]);
    });

    it('returns a flat array of scalars unchanged (second guard false)', () => {
        expect(asArray<number>([1, 2, 3])).toEqual([1, 2, 3]);
    });

    it('returns [] for an empty array (length 0 → second guard false)', () => {
        expect(asArray<number>([])).toEqual([]);
    });

    it('flattens an array of arrays (second guard true)', () => {
        expect(asArray<number>([[1, 2], [3]])).toEqual([1, 2, 3]);
    });

    it('treats a null inner array as empty when flattening (item ?? [] branch)', () => {
        expect(asArray<number>([[1], null])).toEqual([1]);
    });
});

describe('asObject', () => {
    it('returns null for a falsy value (first guard)', () => {
        expect(asObject<{a: number}>(null)).toBeNull();
        expect(asObject<{a: number}>(undefined)).toBeNull();
        expect(asObject<{a: number}>(0)).toBeNull();
    });

    it('returns the object itself when it is not an array (isArray false)', () => {
        expect(asObject<{a: number}>({a: 1})).toEqual({a: 1});
    });

    it('returns the first element for an array (isArray true, ?? left)', () => {
        expect(asObject<{a: number}>([{a: 2}, {a: 3}])).toEqual({a: 2});
    });

    it('returns null for an empty array (isArray true, ?? right)', () => {
        expect(asObject<{a: number}>([])).toBeNull();
    });
});

const lot = (open_quantity: string, states?: string[] | null): LotOpenish => ({open_quantity, states});

describe('lotIsOpenish', () => {
    it('is true when open_quantity is positive (|| left true, short-circuit)', () => {
        expect(lotIsOpenish(lot('5', []))).toBe(true);
    });

    it('is true when quantity is zero but the OPEN tag is present (left false, right true)', () => {
        expect(lotIsOpenish(lot('0', ['OPEN', 'PARTIALLY_CLOSED']))).toBe(true);
    });

    it('is false when quantity is zero and no OPEN tag (left false, right false)', () => {
        expect(lotIsOpenish(lot('0', ['CLOSED']))).toBe(false);
    });

    it('tolerates a missing states list (states ?? [] branch)', () => {
        expect(lotIsOpenish(lot('0', null))).toBe(false);
        expect(lotIsOpenish(lot('0'))).toBe(false);
    });
});

describe('filterVisibleLots', () => {
    const openLot = lot('10', ['OPEN']);
    const closedLot = lot('0', ['CLOSED']);
    const lots = [openLot, closedLot];

    it('shows every lot when both buckets are on (bothSame true)', () => {
        expect(filterVisibleLots(lots, {open: true, closed: true})).toEqual([openLot, closedLot]);
    });

    it('shows every lot when both buckets are off (bothSame true, the "neither" case)', () => {
        expect(filterVisibleLots(lots, {open: false, closed: false})).toEqual([openLot, closedLot]);
    });

    it('shows only open-ish lots when only the open bucket is on (|| right-true / right-false)', () => {
        expect(filterVisibleLots(lots, {open: true, closed: false})).toEqual([openLot]);
    });

    it('shows only closed lots when only the closed bucket is on (|| right-false / right-true)', () => {
        expect(filterVisibleLots(lots, {open: false, closed: true})).toEqual([closedLot]);
    });
});

describe('normalizeQuoteBaseQuantity', () => {
    it('keeps a finite positive number (both && sides true)', () => {
        expect(normalizeQuoteBaseQuantity(2.5)).toBe(2.5);
    });

    it('parses a numeric string', () => {
        expect(normalizeQuoteBaseQuantity('100')).toBe(100);
    });

    it('clamps a non-numeric string to 1 (isFinite false)', () => {
        expect(normalizeQuoteBaseQuantity('abc')).toBe(1);
    });

    it('clamps NaN / Infinity to 1 (isFinite false)', () => {
        expect(normalizeQuoteBaseQuantity(NaN)).toBe(1);
        expect(normalizeQuoteBaseQuantity(Infinity)).toBe(1);
    });

    it('clamps zero and negatives to 1 (isFinite true, > 0 false)', () => {
        expect(normalizeQuoteBaseQuantity(0)).toBe(1);
        expect(normalizeQuoteBaseQuantity(-3)).toBe(1);
    });

    it('clamps null / undefined to 1', () => {
        expect(normalizeQuoteBaseQuantity(null)).toBe(1);
        expect(normalizeQuoteBaseQuantity(undefined)).toBe(1);
    });
});

describe('collectInvolvedLotIds', () => {
    const row = (transaction_id: number, lot_id: number, related_transaction_id?: number | (number | null)[] | null): InvolvedEventRow => ({
        transaction_id,
        lot_id,
        related_transaction_id,
    });

    it('returns just the clicked lot when nothing else shares its transaction', () => {
        const events = [row(1, 10), row(2, 20)];
        expect(collectInvolvedLotIds(events, row(1, 10))).toEqual([10]);
    });

    it('gathers every row on the same transaction (transaction_id === txId branch)', () => {
        const events = [row(5, 100), row(5, 101), row(9, 200)];
        expect(collectInvolvedLotIds(events, row(5, 100))).toEqual([100, 101]);
    });

    it('follows the clicked event related id to its paired rows (relatedId != null && match)', () => {
        // clicked tx 5, paired tx 6; row on tx 6 must be pulled in.
        const events = [row(5, 100), row(6, 101)];
        expect(collectInvolvedLotIds(events, row(5, 100, 6))).toEqual([100, 101]);
    });

    it('pulls in a row whose own related id points back at the clicked tx (rowRelated === txId)', () => {
        const events = [row(5, 100), row(7, 101, 5)];
        expect(collectInvolvedLotIds(events, row(5, 100))).toEqual([100, 101]);
    });

    it('unwraps an array-shaped related id (redundant-union arm)', () => {
        const events = [row(5, 100), row(6, 101)];
        expect(collectInvolvedLotIds(events, row(5, 100, [6]))).toEqual([100, 101]);
    });

    it('ignores a row whose related id does not match (relatedId != null but no match)', () => {
        const events = [row(5, 100), row(8, 101, 99)];
        expect(collectInvolvedLotIds(events, row(5, 100, 42))).toEqual([100]);
    });

    it('de-duplicates lot ids and keeps the clicked lot first', () => {
        const events = [row(5, 100), row(5, 100), row(5, 101)];
        expect(collectInvolvedLotIds(events, row(5, 100))).toEqual([100, 101]);
    });

    it('treats a null related id as "no pairing" (relatedId != null short-circuit)', () => {
        const events = [row(5, 100), row(6, 101, null)];
        expect(collectInvolvedLotIds(events, row(5, 100, null))).toEqual([100]);
    });

    it('treats an empty / all-null related array as no pairing (value[0] ?? null right arm)', () => {
        const events = [row(5, 100), row(6, 101, [null])];
        expect(collectInvolvedLotIds(events, row(5, 100, []))).toEqual([100]);
    });
});
