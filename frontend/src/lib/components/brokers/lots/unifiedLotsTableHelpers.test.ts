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
 *
 * Two helpers are not pure: `formatLotQuantityMasked` and `formatLotQuantityCell`
 * read the global privacy flag (decision D5′), so their blocks reset it on both
 * sides of each test — the store is module level, and a flag left on by one test
 * would mask the next one's clear-text controls.
 */
import {afterEach, beforeEach, describe, it, expect} from 'vitest';
import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {primaryState, secondaryStates, filterStates, formatLotQuantity, formatLotQuantityMasked, formatLotQuantityCell, findBroker, sameIdSet, sumNumeric, weightedAverage, ratioOrNull} from './unifiedLotsTableHelpers';

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

describe('formatLotQuantityMasked', () => {
    // A lot quantity sits next to a price, and quantity × price rebuilds what the user owns: masked under privacy (D5′).
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('formats exactly like formatLotQuantity while privacy is off', () => {
        expect(formatLotQuantityMasked(1000.5, 'en-US')).toBe(formatLotQuantity(1000.5, 'en-US'));
        expect(formatLotQuantityMasked(-2.5, 'en-US')).toBe('-2.5');
    });

    it('masks a present quantity under privacy, keeping the sign of a short one', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityMasked(1000.5, 'en-US')).toBe('•••');
        expect(formatLotQuantityMasked(-2.5, 'en-US')).toBe('-•••');
    });

    it('keeps the em dash for an absent quantity in both states', () => {
        expect(formatLotQuantityMasked(null, 'en-US')).toBe('—');

        setPrivacyEnabled(true);
        // Masking an absence would claim a quantity the lot does not have.
        expect(formatLotQuantityMasked(null, 'en-US')).toBe('—');
        // Positive control: in this exact state a present quantity is masked, so
        // the em dash above is the absence check and not a flag that stayed off.
        expect(formatLotQuantityMasked(6, 'en-US')).toBe('•••');
    });
});

describe('formatLotQuantityCell', () => {
    // A partially closed lot keeps its reading key under privacy as the open share (Q8); percentages stay visible (D6).
    beforeEach(() => setPrivacyEnabled(false));
    afterEach(() => setPrivacyEnabled(false));

    it('shows open / original for a partially closed lot while privacy is off', () => {
        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('6 / 10');
    });

    it('shows the open share instead of the two quantities under privacy', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('••• (60%)');
    });

    it('falls back to the placeholder alone when there is no share to compute', () => {
        setPrivacyEnabled(true);

        expect(formatLotQuantityCell(6, 0, true, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(6, null, true, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(null, 10, true, 'en-US')).toBe('•••');
        // Positive control: same flag, and a lot with an original to divide by shows its share.
        expect(formatLotQuantityCell(6, 10, true, 'en-US')).toBe('••• (60%)');
    });

    it('renders a lot that is not partial through formatLotQuantityMasked', () => {
        expect(formatLotQuantityCell(6, 10, false, 'en-US')).toBe('6');
        expect(formatLotQuantityCell(null, 10, false, 'en-US')).toBe('—');

        setPrivacyEnabled(true);
        expect(formatLotQuantityCell(6, 10, false, 'en-US')).toBe('•••');
        expect(formatLotQuantityCell(-2.5, 10, false, 'en-US')).toBe('-•••');
        expect(formatLotQuantityCell(null, 10, false, 'en-US')).toBe('—');
    });

    it('never shows a quantity through the share: the only digits left are the percentage', () => {
        // Control: in the clear the partial cell carries both quantities, so the
        // absence checks below are able to see them.
        expect(formatLotQuantityCell(1234.5, 5000, true, 'en-US')).toBe('1,234.5 / 5,000');

        setPrivacyEnabled(true);
        const masked = formatLotQuantityCell(1234.5, 5000, true, 'en-US');
        expect(masked).toBe('••• (25%)');
        // Exactly one digit group, and it is the share (24.69%, rounded), not a quantity.
        expect(masked.match(/\d+/g)).toEqual([String(Math.round((1234.5 / 5000) * 100))]);
        expect(masked).not.toContain('1,234.5');
        expect(masked).not.toContain('5,000');

        const third = formatLotQuantityCell(1, 3, true, 'en-US');
        expect(third).toBe('••• (33%)');
        expect(third.match(/\d+/g)).toEqual(['33']);
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
