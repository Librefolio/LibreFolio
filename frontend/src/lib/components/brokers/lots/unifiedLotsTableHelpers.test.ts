/**
 * @vitest-environment node
 *
 * Branch-exhaustive unit tests for the pure helpers extracted from
 * UnifiedLotsTable.svelte. State derivation, quantity formatting, broker lookup,
 * and the footer aggregations are all pure functions of their input; the HTML
 * cell renderers stay in the component and are not exercised here.
 *
 * Numbers are formatted with an explicit `'en-US'` locale so assertions are
 * deterministic regardless of the machine running them.
 */
import {describe, it, expect} from 'vitest';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {primaryState, secondaryStates, filterStates, formatLotQuantity, findBroker, sameIdSet, sumNumeric, weightedAverage, ratioOrNull} from './unifiedLotsTableHelpers';

describe('primaryState', () => {
    it('prefers PARTIALLY_CLOSED over everything else (first if true)', () => {
        expect(primaryState(['OPEN', 'PARTIALLY_CLOSED', 'CLOSED'])).toBe('PARTIALLY_CLOSED');
    });

    it('returns OPEN when partially-closed is absent (first if false, second true)', () => {
        expect(primaryState(['OPEN', 'CLOSED'])).toBe('OPEN');
    });

    it('returns CLOSED when neither partial nor open is present (third if true)', () => {
        expect(primaryState(['CLOSED', 'DISTRIBUTED'])).toBe('CLOSED');
    });

    it('falls back to DEGRADED when none of the three are present (all ifs false)', () => {
        expect(primaryState(['IN_TRANSIT'])).toBe('DEGRADED');
        expect(primaryState([])).toBe('DEGRADED');
    });
});

describe('secondaryStates', () => {
    it('returns all three in fixed display order when present', () => {
        expect(secondaryStates(['DEGRADED', 'IN_TRANSIT', 'DISTRIBUTED'])).toEqual(['DISTRIBUTED', 'IN_TRANSIT', 'DEGRADED']);
    });

    it('returns only the present subset (mixed filter true/false)', () => {
        expect(secondaryStates(['OPEN', 'IN_TRANSIT'])).toEqual(['IN_TRANSIT']);
    });

    it('returns an empty list when none of the secondary states are present', () => {
        expect(secondaryStates(['OPEN', 'CLOSED'])).toEqual([]);
    });
});

describe('filterStates', () => {
    it('combines primary and secondary states without duplicates', () => {
        expect(filterStates(['OPEN', 'IN_TRANSIT'])).toEqual(['OPEN', 'IN_TRANSIT']);
    });

    it('deduplicates when DEGRADED is both the primary fallback and a secondary state', () => {
        // No PARTIALLY_CLOSED/OPEN/CLOSED ⇒ primary is DEGRADED; DEGRADED also secondary ⇒ Set collapses.
        expect(filterStates(['DEGRADED'])).toEqual(['DEGRADED']);
    });

    it('lists primary first, then secondaries in display order', () => {
        expect(filterStates(['PARTIALLY_CLOSED', 'DISTRIBUTED', 'IN_TRANSIT'])).toEqual(['PARTIALLY_CLOSED', 'DISTRIBUTED', 'IN_TRANSIT']);
    });
});

describe('formatLotQuantity', () => {
    it('renders an em dash for a null value (== null branch)', () => {
        expect(formatLotQuantity(null, 'en-US')).toBe('—');
    });

    it('formats a finite value with up to six fraction digits (not-null branch)', () => {
        expect(formatLotQuantity(1000.5, 'en-US')).toBe('1,000.5');
    });

    it('caps at six fraction digits', () => {
        expect(formatLotQuantity(0.123456789, 'en-US')).toBe('0.123457');
    });

    it('accepts the default (machine) locale when none is passed', () => {
        // Exercises the optional-locale call path; only assert it is a non-empty numeric string.
        expect(formatLotQuantity(42)).toMatch(/42/);
    });
});

describe('findBroker', () => {
    const brokers: BrokerLike[] = [
        {id: 1, name: 'Fineco'},
        {id: 2, name: 'Directa'},
    ];

    it('returns null for a null id (== null branch)', () => {
        expect(findBroker(null, brokers)).toBeNull();
    });

    it('returns null for an undefined id (== null branch)', () => {
        expect(findBroker(undefined, brokers)).toBeNull();
    });

    it('returns the matching broker (?? left branch)', () => {
        expect(findBroker(2, brokers)).toEqual({id: 2, name: 'Directa'});
    });

    it('returns null on a miss — no synthetic placeholder, unlike the modal (?? right branch)', () => {
        expect(findBroker(99, brokers)).toBeNull();
    });
});

describe('sameIdSet', () => {
    it('returns false when the lengths differ (length guard)', () => {
        expect(sameIdSet(['a', 'b'], ['a'])).toBe(false);
    });

    it('returns true for equal sets regardless of order (every true)', () => {
        expect(sameIdSet(['a', 'b', 'c'], ['c', 'a', 'b'])).toBe(true);
    });

    it('returns false for same length but differing members (every false)', () => {
        expect(sameIdSet(['a', 'b'], ['a', 'x'])).toBe(false);
    });

    it('treats two empty lists as equal', () => {
        expect(sameIdSet([], [])).toBe(true);
    });
});

interface Row {
    v: number | null;
    w: number | null;
}

describe('sumNumeric', () => {
    it('returns null for no rows (count 0 branch)', () => {
        expect(sumNumeric<Row>([], (r) => r.v)).toBeNull();
    });

    it('sums all finite values (count > 0 branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: 1, w: 0},
                    {v: 2, w: 0},
                    {v: 3, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(6);
    });

    it('skips null cells (value == null branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: 5, w: 0},
                    {v: null, w: 0},
                    {v: 5, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(10);
    });

    it('skips non-finite cells (NaN / Infinity → !isFinite branch)', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: NaN, w: 0},
                    {v: Infinity, w: 0},
                    {v: 7, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBe(7);
    });

    it('returns null when every cell is skipped', () => {
        expect(
            sumNumeric<Row>(
                [
                    {v: null, w: 0},
                    {v: NaN, w: 0},
                ],
                (r) => r.v,
            ),
        ).toBeNull();
    });
});

describe('weightedAverage', () => {
    it('weights values by the second column', () => {
        // (10*1 + 20*3) / (1+3) = 70/4 = 17.5
        expect(
            weightedAverage<Row>(
                [
                    {v: 10, w: 1},
                    {v: 20, w: 3},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(17.5);
    });

    it('skips a row whose value is null', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: null, w: 5},
                    {v: 8, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(8);
    });

    it('skips a row whose weight is null', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 8, w: null},
                    {v: 4, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(4);
    });

    it('skips a row whose value is non-finite', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: Infinity, w: 5},
                    {v: 6, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(6);
    });

    it('skips a row whose weight is non-finite', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 6, w: NaN},
                    {v: 9, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(9);
    });

    it('skips a row whose weight is exactly zero (weight === 0 branch)', () => {
        expect(
            weightedAverage<Row>(
                [
                    {v: 100, w: 0},
                    {v: 9, w: 2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(9);
    });

    it('uses the absolute value of a negative weight', () => {
        // (10*|−2| + 20*|−2|)/(2+2) = 60/4 = 15
        expect(
            weightedAverage<Row>(
                [
                    {v: 10, w: -2},
                    {v: 20, w: -2},
                ],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBe(15);
    });

    it('returns null when the total weight is zero (denominator > 0 false branch)', () => {
        expect(
            weightedAverage<Row>(
                [{v: 100, w: 0}],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBeNull();
        expect(
            weightedAverage<Row>(
                [],
                (r) => r.v,
                (r) => r.w,
            ),
        ).toBeNull();
    });
});

describe('ratioOrNull', () => {
    it('divides when both are present and the denominator is non-zero', () => {
        expect(ratioOrNull(30, 120)).toBe(0.25);
    });

    it('returns null when the numerator is null', () => {
        expect(ratioOrNull(null, 120)).toBeNull();
    });

    it('returns null when the denominator is null', () => {
        expect(ratioOrNull(30, null)).toBeNull();
    });

    it('returns null when the denominator is zero (division guard)', () => {
        expect(ratioOrNull(30, 0)).toBeNull();
    });

    it('accepts a zero numerator as a real ratio', () => {
        expect(ratioOrNull(0, 120)).toBe(0);
    });
});
