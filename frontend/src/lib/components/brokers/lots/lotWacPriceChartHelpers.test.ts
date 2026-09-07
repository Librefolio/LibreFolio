/**
 * Branch-coverage tests for lotWacPriceChartHelpers.
 *
 * These are the pure functions lifted out of LotWacPriceChart.svelte — the ones
 * that never touch a canvas and so can be exercised directly in a node
 * environment (ECharts cannot mount in jsdom). Each block below walks the
 * decision points of one function, not just its happy path, because the whole
 * point of the extraction was to make those branches reachable.
 */

import {describe, expect, it} from 'vitest';
import {
    applyLotEvent,
    bubbleEdgePadding,
    cloneLotEventState,
    computeLineBucketCounts,
    computePaddedValueBounds,
    computeVisibleLogicalRange,
    eventCategory,
    eventKey,
    eventTimelineOrder,
    findTransferArriveEvent,
    findTransferDepartEvent,
    isoDateToUtcMs,
    LOT_BUBBLE_MAX_RADIUS,
    LOT_BUBBLE_MIN_RADIUS,
    LOT_BUBBLE_ZERO_EPS,
    lotBubbleRadius,
    lotBubbleSignColor,
    nullifyZeroWac,
    orderDateBounds,
    padDateBoundsForBubbles,
    readZoomPercent,
    resolveMarketPriceAtOrBefore,
    resolveQbqScale,
    scaleUnitPrice,
    sortDates,
    toPercentSeries,
    utcMsToIsoDate,
    type LotEventInput,
    type LotEventKind,
} from './lotWacPriceChartHelpers';

describe('sortDates', () => {
    it('orders YYYY-MM-DD strings chronologically', () => {
        expect(sortDates('2024-01-01', '2024-03-15')).toBeLessThan(0);
        expect(sortDates('2024-03-15', '2024-01-01')).toBeGreaterThan(0);
        expect(sortDates('2024-03-15', '2024-03-15')).toBe(0);
    });
});

describe('isoDateToUtcMs / utcMsToIsoDate', () => {
    it('maps a calendar day to its UTC-midnight epoch and back', () => {
        const ms = isoDateToUtcMs('2024-03-15');
        expect(ms).toBe(Date.UTC(2024, 2, 15));
        expect(utcMsToIsoDate(ms)).toBe('2024-03-15');
    });

    it('returns NaN when a component is not a finite number', () => {
        expect(isoDateToUtcMs('2024-03-xx')).toBeNaN();
        expect(isoDateToUtcMs('not-a-date')).toBeNaN();
    });

    it('zero-pads single-digit month and day on the way back', () => {
        expect(utcMsToIsoDate(Date.UTC(2024, 0, 5))).toBe('2024-01-05');
    });
});

describe('resolveQbqScale', () => {
    it('returns the quantity when it is strictly positive', () => {
        expect(resolveQbqScale(100)).toBe(100);
    });

    it('degrades a missing, zero or negative quantity to 1', () => {
        expect(resolveQbqScale(null)).toBe(1);
        expect(resolveQbqScale(undefined)).toBe(1);
        expect(resolveQbqScale(0)).toBe(1);
        expect(resolveQbqScale(-5)).toBe(1);
    });
});

describe('scaleUnitPrice', () => {
    it('scales a numeric price and preserves null', () => {
        expect(scaleUnitPrice(1.5, 100)).toBe(150);
        expect(scaleUnitPrice(null, 100)).toBeNull();
    });
});

describe('nullifyZeroWac', () => {
    it('passes through a real WAC against a real pool', () => {
        expect(nullifyZeroWac(12.5, 3)).toBe(12.5);
    });

    it('nullifies a null WAC, a zero WAC, or a WAC against an empty pool', () => {
        expect(nullifyZeroWac(null, 3)).toBeNull();
        expect(nullifyZeroWac(0, 3)).toBeNull();
        expect(nullifyZeroWac(12.5, 0)).toBeNull();
    });
});

describe('toPercentSeries', () => {
    it('rebases on the first non-null, non-zero value', () => {
        const out = toPercentSeries([
            {date: '2024-01-01', value: null},
            {date: '2024-01-02', value: 0},
            {date: '2024-01-03', value: 100},
            {date: '2024-01-04', value: 110},
        ]);
        expect(out[0].percent).toBeNull(); // value null → percent null
        expect(out[1].percent).toBe(-100); // value 0, baseline 100 → (0-100)/100*100
        expect(out[2].percent).toBe(0); // baseline itself
        expect(out[3].percent).toBeCloseTo(10);
        expect(out.map((p) => p.absolute)).toEqual([null, 0, 100, 110]);
    });

    it('leaves every percent null when there is no usable baseline', () => {
        const out = toPercentSeries([
            {date: '2024-01-01', value: null},
            {date: '2024-01-02', value: 0},
        ]);
        expect(out.every((p) => p.percent === null)).toBe(true);
    });
});

describe('orderDateBounds', () => {
    it('returns null when either side is absent', () => {
        expect(orderDateBounds(null, '2024-01-01')).toBeNull();
        expect(orderDateBounds('2024-01-01', null)).toBeNull();
        expect(orderDateBounds(undefined, undefined)).toBeNull();
    });

    it('keeps an ordered pair and swaps a reversed one', () => {
        expect(orderDateBounds('2024-01-01', '2024-06-01')).toEqual({min: '2024-01-01', max: '2024-06-01'});
        expect(orderDateBounds('2024-06-01', '2024-01-01')).toEqual({min: '2024-01-01', max: '2024-06-01'});
    });
});

describe('readZoomPercent', () => {
    it('defaults a missing window to the full 0..100', () => {
        expect(readZoomPercent(undefined)).toEqual({start: 0, end: 100});
        expect(readZoomPercent({})).toEqual({start: 0, end: 100});
    });

    it('reads numeric start/end and clamps them into range', () => {
        expect(readZoomPercent({start: 25, end: 75})).toEqual({start: 25, end: 75});
        expect(readZoomPercent({start: -10, end: 150})).toEqual({start: 0, end: 100});
    });

    it('ignores non-number fields', () => {
        expect(readZoomPercent({start: 'x' as unknown as number, end: 40})).toEqual({start: 0, end: 40});
    });
});

describe('computeVisibleLogicalRange', () => {
    const axis = {startDate: '2024-01-01', endDate: '2024-01-11'}; // 10-day span

    it('maps a percentage window linearly onto the axis span', () => {
        expect(computeVisibleLogicalRange(axis, {start: 0, end: 50})).toEqual({startDate: '2024-01-01', endDate: '2024-01-06'});
        expect(computeVisibleLogicalRange(axis, {start: 50, end: 100})).toEqual({startDate: '2024-01-06', endDate: '2024-01-11'});
    });

    it('orders a reversed window before mapping', () => {
        expect(computeVisibleLogicalRange(axis, {start: 100, end: 0})).toEqual({startDate: '2024-01-01', endDate: '2024-01-11'});
    });

    it('returns the axis unchanged for a degenerate or unparseable span', () => {
        expect(computeVisibleLogicalRange({startDate: '2024-01-05', endDate: '2024-01-05'}, {start: 0, end: 100})).toEqual({startDate: '2024-01-05', endDate: '2024-01-05'});
        expect(computeVisibleLogicalRange({startDate: 'bad', endDate: '2024-01-11'}, {start: 0, end: 100})).toEqual({startDate: 'bad', endDate: '2024-01-11'});
    });
});

describe('computeLineBucketCounts', () => {
    const range = {startDate: '2024-01-01', endDate: '2024-12-31'};

    it('counts only dates inside the range and de-dups weekly/monthly buckets', () => {
        const dates = ['2023-12-31', '2024-01-01', '2024-01-02', '2024-02-15', '2025-01-01'];
        const counts = computeLineBucketCounts(dates, range);
        expect(counts.dailyCount).toBe(3); // the two Jan + one Feb; the 2023 and 2025 dates fall outside
        expect(counts.monthlyCount).toBe(2); // January and February
        expect(counts.weeklyCount).toBeGreaterThanOrEqual(2);
    });

    it('is empty when nothing lands in the range', () => {
        expect(computeLineBucketCounts(['2020-01-01'], range)).toEqual({dailyCount: 0, weeklyCount: 0, monthlyCount: 0});
    });
});

describe('bubbleEdgePadding', () => {
    it('scales the radius into a span delta', () => {
        // fraction = 20/100 = 0.2; pad = 1000*0.2 / (1 - 0.4) = 200 / 0.6
        expect(bubbleEdgePadding(1000, 20, 100)).toBeCloseTo((1000 * 0.2) / 0.6);
    });

    it('caps the edge fraction at 0.3 for an oversized radius', () => {
        // fraction capped at 0.3 → denom 1 - 0.6 = 0.4
        expect(bubbleEdgePadding(1000, 90, 100)).toBeCloseTo((1000 * 0.3) / 0.4);
    });

    it('floors the denominator so an enormous radius cannot divide by zero', () => {
        // fraction 0.3 (capped), denom max(0.1, 0.4) = 0.4; the floor only bites past the cap,
        // so drive it with a tiny plot: fraction still caps at 0.3, denom 0.4 → finite
        expect(Number.isFinite(bubbleEdgePadding(10, 1000, 1))).toBe(true);
    });
});

describe('padDateBoundsForBubbles', () => {
    const bounds = {min: '2024-01-01T00:00:00.000Z', max: '2024-01-31T00:00:00.000Z'};

    it('is a no-op without bounds or without a positive radius', () => {
        expect(padDateBoundsForBubbles(null, 10, 500)).toBeNull();
        expect(padDateBoundsForBubbles(bounds, 0, 500)).toBe(bounds);
        expect(padDateBoundsForBubbles(bounds, -3, 500)).toBe(bounds);
    });

    it('is a no-op for unparseable or non-increasing bounds', () => {
        expect(padDateBoundsForBubbles({min: 'x', max: 'y'}, 10, 500)).toEqual({min: 'x', max: 'y'});
        const reversed = {min: '2024-02-01T00:00:00.000Z', max: '2024-01-01T00:00:00.000Z'};
        expect(padDateBoundsForBubbles(reversed, 10, 500)).toBe(reversed);
    });

    it('widens both sides symmetrically when there are bubbles', () => {
        const padded = padDateBoundsForBubbles(bounds, 10, 500);
        expect(padded).not.toBeNull();
        expect(new Date(padded!.min).getTime()).toBeLessThan(new Date(bounds.min).getTime());
        expect(new Date(padded!.max).getTime()).toBeGreaterThan(new Date(bounds.max).getTime());
    });
});

describe('computePaddedValueBounds', () => {
    it('returns null for an empty value set', () => {
        expect(computePaddedValueBounds([], 0, 288)).toBeNull();
    });

    it('pads a real span by 4% each side', () => {
        const out = computePaddedValueBounds([0, 100], 0, 288);
        expect(out).toEqual({min: -4, max: 104});
    });

    it('pads a degenerate (all-equal) span by 4% of the magnitude', () => {
        const out = computePaddedValueBounds([50, 50], 0, 288);
        // span 0 → padding = max(|50|,|50|,1)*0.04 = 2
        expect(out).toEqual({min: 48, max: 52});
    });

    it('expands further when a bubble radius is present', () => {
        const plain = computePaddedValueBounds([0, 100], 0, 288)!;
        const withBubble = computePaddedValueBounds([0, 100], 12, 288)!;
        expect(withBubble.min).toBeLessThan(plain.min);
        expect(withBubble.max).toBeGreaterThan(plain.max);
    });
});

describe('lotBubbleRadius', () => {
    const mid = (LOT_BUBBLE_MIN_RADIUS + LOT_BUBBLE_MAX_RADIUS) / 2;

    it('returns the midpoint radius for a degenerate range', () => {
        expect(lotBubbleRadius(5, 10, 10)).toBe(mid); // max <= min
        expect(lotBubbleRadius(5, 10, 5)).toBe(mid); // max < min
    });

    it('returns the midpoint when the roots collapse', () => {
        // min and max both floor to 0 under sqrt(max(0, .)) → equal roots
        expect(lotBubbleRadius(0, -3, -1)).toBe(mid);
    });

    it('interpolates by sqrt between the bounds', () => {
        expect(lotBubbleRadius(0, 0, 100)).toBe(LOT_BUBBLE_MIN_RADIUS);
        expect(lotBubbleRadius(100, 0, 100)).toBe(LOT_BUBBLE_MAX_RADIUS);
        expect(lotBubbleRadius(25, 0, 100)).toBeCloseTo(LOT_BUBBLE_MIN_RADIUS + 0.5 * (LOT_BUBBLE_MAX_RADIUS - LOT_BUBBLE_MIN_RADIUS));
    });

    it('clamps values outside the range and floors negatives at zero', () => {
        expect(lotBubbleRadius(1000, 0, 100)).toBe(LOT_BUBBLE_MAX_RADIUS);
        expect(lotBubbleRadius(-50, 0, 100)).toBe(LOT_BUBBLE_MIN_RADIUS);
    });
});

describe('lotBubbleSignColor', () => {
    it('paints gains, losses and a flat dead band per theme', () => {
        expect(lotBubbleSignColor(1, false)).toBe('#16a34a');
        expect(lotBubbleSignColor(1, true)).toBe('#4ade80');
        expect(lotBubbleSignColor(-1, false)).toBe('#dc2626');
        expect(lotBubbleSignColor(-1, true)).toBe('#f87171');
        expect(lotBubbleSignColor(0, false)).toBe('#64748b');
        expect(lotBubbleSignColor(0, true)).toBe('#94a3b8');
    });

    it('treats a crumb within ±epsilon as flat', () => {
        expect(lotBubbleSignColor(LOT_BUBBLE_ZERO_EPS / 2, false)).toBe('#64748b');
        expect(lotBubbleSignColor(-LOT_BUBBLE_ZERO_EPS / 2, false)).toBe('#64748b');
    });
});

describe('eventKey', () => {
    const base = {lot_id: 7, date: '2024-03-15', kind: 'BUY' as LotEventKind, transaction_id: 42};

    it('includes the optional related tx and fragment when present', () => {
        expect(eventKey({...base, related_transaction_id: 99, fragment_id: 'f1'})).toBe('7:2024-03-15:BUY:42:99:f1');
    });

    it('substitutes empty strings when the optionals are absent', () => {
        expect(eventKey(base)).toBe('7:2024-03-15:BUY:42::');
        expect(eventKey({...base, related_transaction_id: null, fragment_id: null})).toBe('7:2024-03-15:BUY:42::');
    });
});

describe('eventCategory', () => {
    it('maps each drawable kind to its marker series', () => {
        expect(eventCategory('BUY')).toBe('buy');
        expect(eventCategory('SELL')).toBe('sell');
        expect(eventCategory('TRANSFER_ARRIVE')).toBe('transfer');
        expect(eventCategory('ADJUSTMENT_IN')).toBe('adjustment');
        expect(eventCategory('ADJUSTMENT_OUT')).toBe('adjustment');
        expect(eventCategory('SPLIT')).toBe('split');
    });

    it('returns null for a kind that draws no marker', () => {
        expect(eventCategory('TRANSFER_DEPART')).toBeNull();
    });
});

describe('eventTimelineOrder', () => {
    it('ranks intra-day replay order', () => {
        expect(eventTimelineOrder('TRANSFER_DEPART')).toBe(0);
        expect(eventTimelineOrder('TRANSFER_ARRIVE')).toBe(1);
        expect(eventTimelineOrder('SPLIT')).toBe(2);
        expect(eventTimelineOrder('BUY')).toBe(3);
        expect(eventTimelineOrder('ADJUSTMENT_IN')).toBe(3);
        expect(eventTimelineOrder('SELL')).toBe(4);
        expect(eventTimelineOrder('ADJUSTMENT_OUT')).toBe(4);
    });
});

describe('resolveMarketPriceAtOrBefore', () => {
    const points = [
        {date: '2024-01-01', absolute: 10},
        {date: '2024-01-05', absolute: 20},
        {date: '2024-01-10', absolute: 30},
    ];

    it('returns null on an empty array or a date before every point', () => {
        expect(resolveMarketPriceAtOrBefore('2024-01-01', [])).toBeNull();
        expect(resolveMarketPriceAtOrBefore('2023-12-31', points)).toBeNull();
    });

    it('finds the exact match and the last point at-or-before a gap', () => {
        expect(resolveMarketPriceAtOrBefore('2024-01-05', points)?.absolute).toBe(20);
        expect(resolveMarketPriceAtOrBefore('2024-01-07', points)?.absolute).toBe(20);
        expect(resolveMarketPriceAtOrBefore('2024-02-01', points)?.absolute).toBe(30);
    });
});

describe('findTransferDepartEvent / findTransferArriveEvent', () => {
    const arrive = {lot_id: 1, date: '2024-03-10', transaction_id: 200, related_transaction_id: 100, source_broker_id: 5, destination_broker_id: 6};

    it('matches a departure by paired transaction id, respecting lot and date', () => {
        const departs = [
            {lot_id: 1, date: '2024-03-08', transaction_id: 100},
            {lot_id: 2, date: '2024-03-08', transaction_id: 101}, // wrong lot
        ];
        expect(findTransferDepartEvent(arrive, departs)?.transaction_id).toBe(100);
    });

    it('rejects a departure dated after the arrival', () => {
        const departs = [{lot_id: 1, date: '2024-03-20', transaction_id: 100}];
        expect(findTransferDepartEvent(arrive, departs)).toBeNull();
    });

    it('rejects a departure whose named source or destination broker disagrees', () => {
        expect(findTransferDepartEvent(arrive, [{lot_id: 1, date: '2024-03-08', transaction_id: 100, source_broker_id: 99}])).toBeNull();
        expect(findTransferDepartEvent(arrive, [{lot_id: 1, date: '2024-03-08', transaction_id: 100, destination_broker_id: 99}])).toBeNull();
    });

    it('matches by fragment id when transaction ids do not pair', () => {
        const noRelation = {lot_id: 1, date: '2024-03-10', transaction_id: 200, fragment_id: 'frag-A'};
        const departs = [{lot_id: 1, date: '2024-03-08', transaction_id: 555, fragment_id: 'frag-A'}];
        expect(findTransferDepartEvent(noRelation, departs)?.transaction_id).toBe(555);
    });

    it('matches by the reverse transaction pairing (candidate.related → arrive.tx)', () => {
        const noRelation = {lot_id: 1, date: '2024-03-10', transaction_id: 200};
        const departs = [{lot_id: 1, date: '2024-03-08', transaction_id: 300, related_transaction_id: 200}];
        expect(findTransferDepartEvent(noRelation, departs)?.transaction_id).toBe(300);
    });

    it('breaks ties toward the most recent then highest-id departure', () => {
        const departs = [
            {lot_id: 1, date: '2024-03-05', transaction_id: 100},
            {lot_id: 1, date: '2024-03-08', transaction_id: 100},
            {lot_id: 1, date: '2024-03-08', transaction_id: 100},
        ];
        expect(findTransferDepartEvent(arrive, departs)?.date).toBe('2024-03-08');
    });

    const depart = {lot_id: 1, date: '2024-03-08', transaction_id: 100, related_transaction_id: 200, source_broker_id: 5, destination_broker_id: 6};

    it('mirror: matches an arrival at-or-after the departure, earliest first', () => {
        const arrives = [
            {lot_id: 1, date: '2024-03-05', transaction_id: 200}, // before → rejected
            {lot_id: 1, date: '2024-03-12', transaction_id: 200},
            {lot_id: 1, date: '2024-03-10', transaction_id: 200},
        ];
        expect(findTransferArriveEvent(depart, arrives)?.date).toBe('2024-03-10');
    });

    it('mirror: rejects a different lot and a disagreeing broker slot', () => {
        expect(findTransferArriveEvent(depart, [{lot_id: 9, date: '2024-03-10', transaction_id: 200}])).toBeNull();
        expect(findTransferArriveEvent(depart, [{lot_id: 1, date: '2024-03-10', transaction_id: 200, source_broker_id: 99}])).toBeNull();
        expect(findTransferArriveEvent(depart, [{lot_id: 1, date: '2024-03-10', transaction_id: 200, destination_broker_id: 99}])).toBeNull();
    });

    it('mirror: matches by reverse pairing or fragment, and breaks ties toward the lowest id', () => {
        const byReverse = {lot_id: 1, date: '2024-03-08', transaction_id: 100};
        expect(findTransferArriveEvent(byReverse, [{lot_id: 1, date: '2024-03-10', transaction_id: 400, related_transaction_id: 100}])?.transaction_id).toBe(400);
        const byFragment = {lot_id: 1, date: '2024-03-08', transaction_id: 100, fragment_id: 'frag-Z'};
        expect(findTransferArriveEvent(byFragment, [{lot_id: 1, date: '2024-03-10', transaction_id: 401, fragment_id: 'frag-Z'}])?.transaction_id).toBe(401);
        const tie = [
            {lot_id: 1, date: '2024-03-10', transaction_id: 210, related_transaction_id: 100},
            {lot_id: 1, date: '2024-03-10', transaction_id: 205, related_transaction_id: 100},
        ];
        expect(findTransferArriveEvent(depart, tie)?.transaction_id).toBe(205);
    });

    it('returns null when nothing matches', () => {
        expect(findTransferDepartEvent(arrive, [])).toBeNull();
        expect(findTransferArriveEvent(arrive, [{lot_id: 1, date: '2024-03-20', transaction_id: 777}])).toBeNull();
    });
});

describe('cloneLotEventState', () => {
    it('reads a missing state as all-null and copies a present one', () => {
        expect(cloneLotEventState(undefined)).toEqual({quantity: null, unitPrice: null});
        expect(cloneLotEventState({quantity: 5, unitPrice: 2})).toEqual({quantity: 5, unitPrice: 2});
    });
});

describe('applyLotEvent', () => {
    const start = {quantity: null, unitPrice: null};
    const ev = (kind: LotEventKind, extra: Partial<LotEventInput> = {}): LotEventInput => ({kind, ...extra});

    it('BUY adds absolute quantity onto the base and adopts the price', () => {
        expect(applyLotEvent(start, ev('BUY', {quantity: '10', unit_price: '3'}))).toEqual({quantity: 10, unitPrice: 3});
        expect(applyLotEvent({quantity: 4, unitPrice: 2}, ev('BUY', {quantity: '-6'}))).toEqual({quantity: 10, unitPrice: 2});
    });

    it('BUY with a null quantity leaves the running quantity unchanged', () => {
        expect(applyLotEvent({quantity: 4, unitPrice: 2}, ev('BUY', {}))).toEqual({quantity: 4, unitPrice: 2});
    });

    it('ADJUSTMENT_IN blends the unit price by quantity weight when it can', () => {
        // base 10 @ 2, add 10 @ 4 → 20 @ 3
        expect(applyLotEvent({quantity: 10, unitPrice: 2}, ev('ADJUSTMENT_IN', {quantity: '10', unit_price: '4'}))).toEqual({quantity: 20, unitPrice: 3});
    });

    it('ADJUSTMENT_IN adopts the event price when there is no base to blend', () => {
        expect(applyLotEvent(start, ev('ADJUSTMENT_IN', {quantity: '5', unit_price: '9'}))).toEqual({quantity: 5, unitPrice: 9});
    });

    it('ADJUSTMENT_IN keeps the prior unit price when the event carries none', () => {
        // base 0 → no weighting; event has no price → afterUnitPrice = null ?? beforeUnitPrice
        expect(applyLotEvent({quantity: 0, unitPrice: 5}, ev('ADJUSTMENT_IN', {quantity: '3'}))).toEqual({quantity: 3, unitPrice: 5});
    });

    it('ADJUSTMENT_IN with a null quantity is inert', () => {
        expect(applyLotEvent({quantity: 3, unitPrice: 1}, ev('ADJUSTMENT_IN', {}))).toEqual({quantity: 3, unitPrice: 1});
    });

    it('SELL / ADJUSTMENT_OUT subtract, floored at zero, and keep the price', () => {
        expect(applyLotEvent({quantity: 10, unitPrice: 2}, ev('SELL', {quantity: '4'}))).toEqual({quantity: 6, unitPrice: 2});
        expect(applyLotEvent({quantity: 3, unitPrice: 2}, ev('ADJUSTMENT_OUT', {quantity: '10'}))).toEqual({quantity: 0, unitPrice: 2});
    });

    it('SELL with a null running quantity or null event quantity carries state through', () => {
        expect(applyLotEvent(start, ev('SELL', {quantity: '4'}))).toEqual({quantity: null, unitPrice: null});
        expect(applyLotEvent({quantity: 5, unitPrice: 2}, ev('SELL', {}))).toEqual({quantity: 5, unitPrice: 2});
    });

    it('SPLIT multiplies quantity and divides price by the ratio', () => {
        expect(applyLotEvent({quantity: 10, unitPrice: 8}, ev('SPLIT', {ratio: '2'}))).toEqual({quantity: 20, unitPrice: 4});
    });

    it('SPLIT derives a missing base quantity from quantity / ratio', () => {
        // no running quantity, event quantity 20 (after), ratio 2 → before 10 → after 20
        expect(applyLotEvent(start, ev('SPLIT', {quantity: '20', ratio: '2'})).quantity).toBe(20);
    });

    it('SPLIT with a null ratio leaves quantity as the base and price untouched', () => {
        expect(applyLotEvent({quantity: 10, unitPrice: 8}, ev('SPLIT', {}))).toEqual({quantity: 10, unitPrice: 8});
    });

    it('TRANSFER seeds from the event only while the running state is null', () => {
        expect(applyLotEvent(start, ev('TRANSFER_ARRIVE', {quantity: '7', unit_price: '3'}))).toEqual({quantity: 7, unitPrice: 3});
        expect(applyLotEvent({quantity: 5, unitPrice: 2}, ev('TRANSFER_DEPART', {quantity: '7', unit_price: '3'}))).toEqual({quantity: 5, unitPrice: 2});
    });

    it('TRANSFER with a null running quantity and a null event quantity stays null', () => {
        expect(applyLotEvent(start, ev('TRANSFER_ARRIVE', {}))).toEqual({quantity: null, unitPrice: null});
    });

    it('falls back to open_unit_price / close_unit_price for the price', () => {
        expect(applyLotEvent(start, ev('BUY', {quantity: '1', open_unit_price: '11'})).unitPrice).toBe(11);
        expect(applyLotEvent(start, ev('BUY', {quantity: '1', close_unit_price: '13'})).unitPrice).toBe(13);
    });
});
