/**
 * Branch-coverage tests for lotWacPriceChartHelpers.
 *
 * These are the pure functions lifted out of LotWacPriceChart.svelte — the ones
 * that never touch a canvas and so can be exercised directly in a node
 * environment (ECharts cannot mount in jsdom). Each block below walks the
 * decision points of one function, not just its happy path, because the whole
 * point of the extraction was to make those branches reachable.
 *
 * Two blocks then pin V11 (workstream Y, lot Y12b): the opening value a BUY
 * marker shows is the backend's `opening_value`, read by `eventOpeningValue`,
 * and LotWacPriceChart.svelte's source is read to pin the tooltip's glue, which
 * a node test cannot render. The next two pin Y-30 the same way: the market
 * price line is the asset's own `market_price_history`, read by
 * `marketPriceLine`, and the source is read to pin that the component reads it.
 * The last pins J-48: a TRANSFER leg crossing the analysis scope is drawn in the
 * transfer series, and replayed as the adjustment it is.
 */

import {readFileSync} from 'node:fs';
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
    marketPriceLine,
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

// WHY: `Date.UTC(24, …)` reads the year as 1924, and an unpadded year would write `24-03-01`: the zoom window of a chart
// whose lot starts in the year 24 sat a century off.
describe('isoDateToUtcMs / utcMsToIsoDate with a year before 100', () => {
    it.each(['0024-03-01', '0001-01-01', '0099-12-31'])('%s is read in its own year and written back whole', (date) => {
        const ms = isoDateToUtcMs(date);
        expect(new Date(ms).toISOString().slice(0, 10)).toBe(date);
        expect(utcMsToIsoDate(ms)).toBe(date);
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
        expect(lotBubbleSignColor(1, false)).toBe('#18794e');
        expect(lotBubbleSignColor(1, true)).toBe('#5ed69a');
        expect(lotBubbleSignColor(-1, false)).toBe('#c82838');
        expect(lotBubbleSignColor(-1, true)).toBe('#ff7a86');
        expect(lotBubbleSignColor(0, false)).toBe('#727b87');
        expect(lotBubbleSignColor(0, true)).toBe('#a9b0bb');
    });

    it('treats a crumb within ±epsilon as flat', () => {
        expect(lotBubbleSignColor(LOT_BUBBLE_ZERO_EPS / 2, false)).toBe('#727b87');
        expect(lotBubbleSignColor(-LOT_BUBBLE_ZERO_EPS / 2, false)).toBe('#727b87');
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

/*
 * V11 (workstream Y, lot Y12b) — the opening value of a BUY marker is the backend's.
 *
 * The contract. The tooltip of a BUY marker shows the lot's opening value. The backend sends that figure on the event:
 * `LotTimelineEventSchema.opening_value` (MF-E1) — for the event that opens a lot (BUY, ADJUSTMENT_IN), the lot's
 * original cost in target_currency, converted at the opening date: the lot summary's `original_cost`, in the currency
 * of `unit_price`; null on every other kind and when the conversion is missing. Rule 10 of the project: one home for
 * financial math, so the chart shows the backend's field and never recomputes it.
 *
 * Red on bab5a8fb9. `buildMarkerTooltip` (LotWacPriceChart.svelte) computes the figure from the event's own fields,
 * `Math.abs(quantity) * unitPrice`, and this module has no reader for the backend's. The fix exports
 * `eventOpeningValue(event)`, the field parsed as the chart parses every amount (`safeDecimal`: null when absent or not
 * a finite number), and the BUY branch of the tooltip reads it; its quantity and unit-price rows stay. ADJUSTMENT_IN
 * gets no value row (coordinator's decision), so nothing here pins one.
 *
 * How. The reader is loaded inside each case and typed through `unknown`: while the export is missing only these cases
 * fail, on the V11 barrier, and the file type-checks before the export exists and after. The amounts disagree on
 * purpose — 3 × 10 = 30 where the backend says 29.97, or says nothing — so a value can match one source only. The
 * tooltip is built inside the component, out of reach of a node test (ECharts draws on a canvas), so its glue is pinned
 * on the source, comments removed: the BUY branch calls the reader and multiplies no quantity by a unit price, and the
 * component imports the reader from this module.
 */

/** The reader V11 adds, as these cases call it: on whole timeline events, so each fixture reads as the backend sends it. */
type EventOpeningValue = (event: Partial<LotEventInput> & {opening_value?: unknown}) => number | null;

/** `eventOpeningValue` off the helper module, through `unknown`; fails on the V11 barrier while the export is missing. */
async function loadEventOpeningValue(): Promise<EventOpeningValue> {
    const helpers: unknown = await import('./lotWacPriceChartHelpers');
    const {eventOpeningValue} = helpers as {eventOpeningValue?: unknown};
    expect(eventOpeningValue, 'V11 barrier: lotWacPriceChartHelpers.ts exports no eventOpeningValue(event), so the WAC chart has no reader for the backend’s opening_value and its BUY tooltip rebuilds the figure as |quantity| × unit price').toBeTypeOf('function');
    return eventOpeningValue as EventOpeningValue;
}

describe('eventOpeningValue — a BUY’s opening value is the backend’s opening_value (Y12b, V11)', () => {
    // Red on bab5a8fb9, on the barrier: the export is missing.
    it('reads a decimal string as its number, zero included', async () => {
        const eventOpeningValue = await loadEventOpeningValue();
        expect(eventOpeningValue({kind: 'BUY', opening_value: '1234.56'}), 'V11: the opening_value "1234.56" is the number 1234.56').toBe(1234.56);
        // J's edge case (Y12a, U8): a lot opened without cost is worth zero — a value, not a missing one.
        expect(eventOpeningValue({kind: 'BUY', quantity: '5', unit_price: '0', opening_value: '0'}), 'V11: an opening value of zero is 0, not null').toBe(0);
    });

    // Red on bab5a8fb9, on the barrier. Today the tooltip shows 30 for this event.
    it('takes the backend’s figure where it differs from |quantity| × unit price: 29.97, never 3 × 10 = 30', async () => {
        const eventOpeningValue = await loadEventOpeningValue();
        expect(eventOpeningValue({kind: 'BUY', quantity: '3', unit_price: '10', opening_value: '29.97'}), 'V11: the opening value is the backend’s opening_value, 29.97, not the event’s |quantity| × unit price, 30').toBe(29.97);
    });

    // Red on bab5a8fb9, on the barrier. Today the tooltip shows 30 for both events: it has their quantity and price.
    it('is null when the backend sends none, null or absent, though quantity and unit price are there', async () => {
        const eventOpeningValue = await loadEventOpeningValue();
        expect(eventOpeningValue({kind: 'BUY', quantity: '3', unit_price: '10', opening_value: null}), 'V11: no conversion at the opening date is no opening value (null, «—»), not a product rebuilt in the browser').toBeNull();
        expect(eventOpeningValue({kind: 'BUY', quantity: '3', unit_price: '10'}), 'V11: an event without opening_value has no opening value, not |quantity| × unit price').toBeNull();
    });

    // Red on bab5a8fb9, on the barrier.
    it('is null for a value that is not a finite number', async () => {
        const eventOpeningValue = await loadEventOpeningValue();
        expect(eventOpeningValue({kind: 'BUY', opening_value: 'n/a'}), 'V11: a non-numeric opening_value is null').toBeNull();
        // safeDecimal's own guard: the backend's SafeDecimal serialises an overflowed Decimal as "Infinity", which is no amount.
        expect(eventOpeningValue({kind: 'BUY', opening_value: 'Infinity'}), 'V11: an opening_value of "Infinity" is null, not an amount').toBeNull();
    });
});

describe('LotWacPriceChart BUY tooltip — the opening value’s glue on the source (Y12b, V11)', () => {
    /** LotWacPriceChart.svelte as it is on disk: a node test cannot render the tooltip it builds. */
    function componentSource(): string {
        return readFileSync(new URL('./LotWacPriceChart.svelte', import.meta.url), 'utf8');
    }

    /** `code` without its comments: a comment that names a call is not the call. Cut at `//`, so it assumes no string of the code holds one. */
    function withoutComments(code: string): string {
        return code.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '');
    }

    /** The body of the block that `opener` (ending in `{`) opens first after `anchor`, braces balanced. */
    function blockAfter(source: string, anchor: string, opener: string): string | undefined {
        const at = source.indexOf(anchor);
        const open = at < 0 ? -1 : source.indexOf(opener, at + anchor.length);
        if (open < 0) return undefined;
        const bodyStart = open + opener.length;
        let depth = 1;
        for (let i = bodyStart; i < source.length; i++) {
            if (source[i] === '{') depth++;
            else if (source[i] === '}' && --depth === 0) return source.slice(bodyStart, i);
        }
        return undefined;
    }

    /**
     * The BUY branch of buildMarkerTooltip, comments removed, so the pins cannot match code elsewhere in the component.
     * The function's body is the first block after its name, which holds while its signature carries no brace. Throws,
     * naming the block, when either is not found.
     */
    function buyBranch(): string {
        const tooltip = blockAfter(componentSource(), 'function buildMarkerTooltip(', '{');
        if (tooltip === undefined) throw new Error('LotWacPriceChart.svelte: the body of function buildMarkerTooltip(…) { … } was not found');
        const branch = blockAfter(tooltip, "if (event.kind === 'BUY')", '{');
        if (branch === undefined) throw new Error("LotWacPriceChart.svelte: buildMarkerTooltip holds no if (event.kind === 'BUY') { … } branch");
        return withoutComments(branch);
    }

    /** `import {…, name, …} from './lotWacPriceChartHelpers'`, whatever the other names and their order. */
    function importFromHelpers(name: string): RegExp {
        return new RegExp(`import\\s*\\{[^}]*\\b${name}\\b[^}]*\\}\\s*from\\s*'\\./lotWacPriceChartHelpers'`);
    }

    /** |quantity| × unit price, in either order, with or without Math.abs: the opening value the tooltip computes on bab5a8fb9. */
    const QUANTITY_TIMES_PRICE = /(?:Math\.abs\(\s*quantity\s*\)|\bquantity\b)\s*\*\s*unitPrice\b|\bunitPrice\s*\*\s*(?:Math\.abs\(\s*quantity\s*\)|\bquantity\b)/;

    // Green before and after the fix: the positive controls. Without them the pins below could pass on an empty or a
    // wrong slice, or with a pattern that matches nothing.
    it('slices the BUY branch itself, sees the helper import, and the product pin sees every spelling of the product', () => {
        const branch = buyBranch();
        expect(branch, 'the BUY branch shows the quantity row').toMatch(/\blabels\.quantity\b/);
        expect(branch, 'the BUY branch shows the unit-price row').toMatch(/\blabels\.unitPrice\b/);
        expect(branch, 'the BUY branch shows the opening-value row').toMatch(/\blabels\.openingValue\b/);
        expect(withoutComments(componentSource()), 'the import pin sees a name the component imports from ./lotWacPriceChartHelpers today').toMatch(importFromHelpers('toPercentSeries'));
        for (const product of ['Math.abs(quantity) * unitPrice', 'quantity * unitPrice', 'unitPrice * Math.abs(quantity)', 'unitPrice * quantity']) {
            expect(product, 'the product pin sees this spelling').toMatch(QUANTITY_TIMES_PRICE);
        }
        expect('const openingValue = eventOpeningValue(event);', 'the product pin spares the reader').not.toMatch(QUANTITY_TIMES_PRICE);
    });

    // Red on bab5a8fb9: the branch computes the figure itself and calls no reader.
    it('reads the opening value with eventOpeningValue(event)', () => {
        expect(buyBranch(), 'V11: the BUY branch of buildMarkerTooltip does not call eventOpeningValue(event), so the tooltip does not show the backend’s opening_value').toMatch(/\beventOpeningValue\(\s*event\s*\)/);
    });

    // Red on bab5a8fb9: `Math.abs(quantity) * unitPrice`.
    it('computes no opening value from the event’s quantity and unit price', () => {
        expect(buyBranch(), 'V11: the BUY branch of buildMarkerTooltip still computes the opening value in the browser, as |quantity| × unit price').not.toMatch(QUANTITY_TIMES_PRICE);
    });

    // Red on bab5a8fb9: the component imports no eventOpeningValue.
    it('imports eventOpeningValue from ./lotWacPriceChartHelpers', () => {
        expect(withoutComments(componentSource()), 'V11: LotWacPriceChart.svelte does not import eventOpeningValue from ./lotWacPriceChartHelpers').toMatch(importFromHelpers('eventOpeningValue'));
    });
});

/*
 * Y-30 (workstream Y) — the market price line is the asset's own series, not a union of the lots'.
 *
 * The contract. The lots analysis answers `MARKET_PRICE_HISTORY` with `market_price_history`: the asset's market price on
 * each day of the window that has a mark convertible to the target currency, `{date, market_price, currency, estimated}`
 * with the price a decimal string, whatever lots are open — and kept when the analysis FAILED, where J-12 nulls every lot
 * section, the per-lot `price_history` with them. The coordinator's decision («always», N89): the WAC chart draws its
 * price line, its axis dates and the bubbles' opening price from that series, and the panel no longer asks for
 * `PRICE_HISTORY`.
 *
 * The reader. `marketPriceLine(points)` turns the series into the line the chart draws: one point per date, in date order
 * (`sortDates`), a repeated date keeping its first point; `value` parsed as the chart parses every amount (`safeDecimal`:
 * null when absent or not a finite number — the date stays, a gap in the line, not a dropped day); `estimated` true only
 * for `true`. It replaces the component's union by date of the per-lot `price_history` points.
 *
 * Red today. `lotWacPriceChartHelpers.ts` exports no `marketPriceLine`: the name imported at the top of this file is
 * `undefined` at run time, so each case of the first block below fails with «marketPriceLine is not a function», and
 * every block above stays green. The glue is pinned on the source, comments removed, as V11's is: today the component
 * imports no `marketPriceLine`, and its `$props()` still takes the per-lot `priceHistory`.
 *
 * Fixtures are points as the client receives them (`MarketPriceHistoryPoint`, currency included), each case's series held
 * in a typed constant so the field the reader ignores type-checks.
 */

/** A `market_price_history` point as the client receives it, the fields a case may leave out made optional. */
interface WireMarketPricePoint {
    date: string;
    market_price?: unknown;
    currency: string;
    estimated?: boolean | null;
}

describe('marketPriceLine — the market price line is the asset’s market_price_history (Y-30)', () => {
    // Red today: marketPriceLine is not a function.
    it('draws one point per date, in date order, whatever order the series arrives in', () => {
        const series: WireMarketPricePoint[] = [
            {date: '2024-01-10', market_price: '104.25', currency: 'EUR', estimated: false},
            {date: '2023-12-29', market_price: '101', currency: 'EUR', estimated: false},
            {date: '2024-01-02', market_price: '103.5', currency: 'EUR', estimated: false},
            {date: '2023-12-31', market_price: '102.125', currency: 'EUR', estimated: false},
        ];
        expect(marketPriceLine(series), 'Y-30: the line is the series in date order, one point per date, each price read as its number').toEqual([
            {date: '2023-12-29', value: 101, estimated: false},
            {date: '2023-12-31', value: 102.125, estimated: false},
            {date: '2024-01-02', value: 103.5, estimated: false},
            {date: '2024-01-10', value: 104.25, estimated: false},
        ]);
    });

    // Red today: marketPriceLine is not a function.
    it('marks a point estimated only when the series says true: false, null and an absent flag are a real quote', () => {
        const series: WireMarketPricePoint[] = [
            {date: '2024-03-01', market_price: '101', currency: 'EUR', estimated: true},
            {date: '2024-03-02', market_price: '102', currency: 'EUR', estimated: false},
            {date: '2024-03-03', market_price: '103', currency: 'EUR', estimated: null},
            {date: '2024-03-04', market_price: '104', currency: 'EUR'},
        ];
        expect(marketPriceLine(series), 'Y-30: estimated is true for true only; false, null and an absent flag read false').toEqual([
            {date: '2024-03-01', value: 101, estimated: true},
            {date: '2024-03-02', value: 102, estimated: false},
            {date: '2024-03-03', value: 103, estimated: false},
            {date: '2024-03-04', value: 104, estimated: false},
        ]);
    });

    // Red today: marketPriceLine is not a function.
    it('keeps a day whose price is absent or not a finite number, valued null: a gap in the line, not a dropped day', () => {
        const series: WireMarketPricePoint[] = [
            {date: '2024-03-01', market_price: '101', currency: 'EUR', estimated: false},
            {date: '2024-03-02', market_price: 'n/a', currency: 'EUR', estimated: false},
            {date: '2024-03-03', currency: 'EUR', estimated: false},
            {date: '2024-03-04', market_price: null, currency: 'EUR', estimated: false},
            // safeDecimal's own guard: the backend's SafeDecimal serialises an overflowed Decimal as "Infinity", which is no price.
            {date: '2024-03-05', market_price: 'Infinity', currency: 'EUR', estimated: false},
            // A price of zero is a price: a value of the line, not a gap.
            {date: '2024-03-06', market_price: '0', currency: 'EUR', estimated: false},
        ];
        expect(marketPriceLine(series), 'Y-30: a day without a readable price keeps its date, valued null; zero stays a value').toEqual([
            {date: '2024-03-01', value: 101, estimated: false},
            {date: '2024-03-02', value: null, estimated: false},
            {date: '2024-03-03', value: null, estimated: false},
            {date: '2024-03-04', value: null, estimated: false},
            {date: '2024-03-05', value: null, estimated: false},
            {date: '2024-03-06', value: 0, estimated: false},
        ]);
    });

    // Red today: marketPriceLine is not a function.
    it('keeps the first point of a repeated date', () => {
        const series: WireMarketPricePoint[] = [
            {date: '2024-03-02', market_price: '102', currency: 'EUR', estimated: false},
            {date: '2024-03-01', market_price: '101', currency: 'EUR', estimated: false},
            {date: '2024-03-02', market_price: '109', currency: 'EUR', estimated: true},
        ];
        expect(marketPriceLine(series), 'Y-30: 2024-03-02 is drawn once, with its first point (102, a real quote), not the later one (109, estimated)').toEqual([
            {date: '2024-03-01', value: 101, estimated: false},
            {date: '2024-03-02', value: 102, estimated: false},
        ]);
        const unreadableFirst: WireMarketPricePoint[] = [
            {date: '2024-03-01', market_price: 'n/a', currency: 'EUR', estimated: true},
            {date: '2024-03-01', market_price: '101', currency: 'EUR', estimated: false},
        ];
        expect(marketPriceLine(unreadableFirst), 'Y-30: the first point is kept even without a readable price: the per-lot union’s preference for a later value is gone').toEqual([{date: '2024-03-01', value: null, estimated: true}]);
    });

    // Red today: marketPriceLine is not a function.
    it('draws no point from an empty series', () => {
        expect(marketPriceLine([]), 'Y-30: an empty market_price_history is an empty line').toEqual([]);
    });
});

describe('LotWacPriceChart market price line — the glue on the source (Y-30)', () => {
    /**
     * LotWacPriceChart.svelte as it is on disk, comments removed: a comment that names a call or a prop is not one. A
     * `//` inside a string — the markers' `path://` symbols — cuts the rest of its line as well, which no pin below reads.
     */
    function componentCode(): string {
        return readFileSync(new URL('./LotWacPriceChart.svelte', import.meta.url), 'utf8')
            .replace(/\/\*[\s\S]*?\*\//g, '')
            .replace(/\/\/[^\n]*/g, '');
    }

    /** `import {…, name, …} from './lotWacPriceChartHelpers'`, whatever the other names and their order. */
    function importFromHelpers(name: string): RegExp {
        return new RegExp(`import\\s*\\{[^}]*\\b${name}\\b[^}]*\\}\\s*from\\s*'\\./lotWacPriceChartHelpers'`);
    }

    /** The component's `import {…} from './lotWacPriceChartHelpers'` statements: what a failing import pin prints, not the whole file. */
    function helperImports(code: string): string {
        return (code.match(/import\s*\{[^}]*\}\s*from\s*'\.\/lotWacPriceChartHelpers'/g) ?? []).join('\n');
    }

    /** The props the component takes: its pattern from the last `let {` before `$props()` up to the call. Throws when there is none. */
    function propsPattern(code: string): string {
        const call = code.indexOf('$props()');
        const open = call < 0 ? undefined : [...code.slice(0, call).matchAll(/\blet\s*\{/g)].at(-1)?.index;
        if (open === undefined) throw new Error('LotWacPriceChart.svelte: no let {…} = $props() was found');
        return code.slice(open, call);
    }

    /** The per-lot series' prop, by its name: `marketPriceHistory` is another name. */
    const PRICE_HISTORY_PROP = /\bpriceHistory\b/;

    // Green before and after the fix: the positive controls. Without them the pins below could pass on an empty or a
    // wrong slice, or with a pattern that matches nothing.
    it('sees a helper import, and slices the props the component takes', () => {
        const code = componentCode();
        expect(helperImports(code), 'the import pin sees a name the component imports from ./lotWacPriceChartHelpers today').toMatch(importFromHelpers('applyLotEvent'));
        const props = propsPattern(code);
        for (const name of ['brokerWacHistory', 'cumulativeWacHistory', 'lotEvents', 'onSelectionChange']) {
            expect(props, `the slice is the props’ pattern: it takes ${name}`).toMatch(new RegExp(`\\b${name}\\b`));
        }
        expect('priceHistory = [],', 'the prop pin sees the per-lot prop').toMatch(PRICE_HISTORY_PROP);
        expect('marketPriceHistory = [],', 'the prop pin spares the market series’ own prop').not.toMatch(PRICE_HISTORY_PROP);
    });

    // Red today: the component imports no marketPriceLine.
    it('imports marketPriceLine from ./lotWacPriceChartHelpers', () => {
        expect(helperImports(componentCode()), 'Y-30: LotWacPriceChart.svelte does not import marketPriceLine from ./lotWacPriceChartHelpers: its price line is still the union by date of the lots’ price_history').toMatch(importFromHelpers('marketPriceLine'));
    });

    // Red today: its $props() takes `priceHistory = []`.
    it('takes no per-lot priceHistory prop: the union of the lots’ price_history is gone', () => {
        expect(propsPattern(componentCode()), 'Y-30: LotWacPriceChart.svelte still takes the per-lot priceHistory, which a FAILED analysis empties: the price line goes with the lots').not.toMatch(PRICE_HISTORY_PROP);
    });
});

/*
 * J-48 (workstream J) — a TRANSFER leg crossing the analysis scope is a transfer marker, replayed as the adjustment it is.
 *
 * The contract. The backend reads a TRANSFER leg whose partner sits at a broker outside the lots' scope as an
 * ADJUSTMENT_IN (entering, at its own cost basis) or an ADJUSTMENT_OUT (leaving, at the market value of its day) row
 * (J-10), so the WAC chart puts it in the adjustment series, labelled as an adjustment. J-48 gives each lot timeline event
 * an optional `scope_boundary`, which lotChartShared's `scopeBoundaryOf` reads as 'IN' | 'OUT' | null, and the chart
 * shows a boundary row as a transfer — its marker series and its label only:
 * - `eventCategory(kind, scopeBoundary?)` answers 'transfer' for an IN or OUT boundary, ADJUSTMENT_IN and ADJUSTMENT_OUT
 *   alike, and maps the kind as before without one: 'adjustment' for an adjustment, null for a departure, which draws
 *   no marker;
 * - the replay keeps reading `kind`: `applyLotEvent` moves a boundary row's quantity and unit price as the adjustment it
 *   is. A cure that replayed it as a transfer would carry the running state across unchanged, which the controls below
 *   tell apart.
 *
 * Red, before the cure: the two boundary cases of `eventCategory`, on their assertion — today the second argument is
 * ignored, so a boundary row stays in the adjustment series. The cases named «control» hold today and after the cure.
 * An event carrying the new field reaches `applyLotEvent` as a variable, not as a literal: `LotEventInput` need not
 * declare a field the replay does not read.
 */
describe('J-48 — scope boundary', () => {
    /** The two directions a leg crosses the scope, each with the adjustment kind the backend reads it as (J-10). */
    const CROSSINGS = [
        {kind: 'ADJUSTMENT_IN', boundary: 'IN'},
        {kind: 'ADJUSTMENT_OUT', boundary: 'OUT'},
    ] as const;

    // RED until J-48's cure: the second argument is ignored today, so the row stays in the adjustment series.
    it.each(CROSSINGS)('eventCategory: $kind across an $boundary boundary is in the transfer series', ({kind, boundary}) => {
        expect(eventCategory(kind, boundary), 'J-48: a leg crossing the scope is a transfer marker (today: adjustment)').toBe('transfer');
    });

    // Control, green before and after the cure: the no-boundary case beside each red.
    it.each(CROSSINGS)('control: eventCategory — $kind without a boundary, absent, null or undefined, stays an adjustment', ({kind}) => {
        expect(eventCategory(kind), 'absent').toBe('adjustment');
        expect(eventCategory(kind, null), 'null').toBe('adjustment');
        expect(eventCategory(kind, undefined), 'undefined').toBe('adjustment');
    });

    // Control, green before and after the cure: a null boundary moves no other kind — a departure still draws no marker.
    it('control: eventCategory — every other kind keeps its series under a null boundary, a departure none', () => {
        const kinds: LotEventKind[] = ['BUY', 'SELL', 'SPLIT', 'TRANSFER_ARRIVE', 'TRANSFER_DEPART'];
        expect(kinds.map((kind) => eventCategory(kind, null))).toEqual(['buy', 'sell', 'split', 'transfer', null]);
    });

    describe('applyLotEvent replays a boundary row as the adjustment it is', () => {
        const ev = (kind: LotEventKind, extra: Partial<LotEventInput> = {}): LotEventInput => ({kind, ...extra});
        /** `event` carrying J-48's field as sent: the scalar, or the array shape of the generated client. */
        const withBoundary = (event: LotEventInput, scopeBoundary: unknown): LotEventInput & {scope_boundary: unknown} => ({...event, scope_boundary: scopeBoundary});

        // Control, green before and after the cure. Why: replayed as a transfer, 10 @ 2 would cross unchanged.
        it('control: an ADJUSTMENT_IN blends its units in the same with or without an IN boundary — 10 @ 2 plus 10 @ 4 is 20 @ 3', () => {
            const before = {quantity: 10, unitPrice: 2};
            const entering = ev('ADJUSTMENT_IN', {quantity: '10', unit_price: '4'});
            expect(applyLotEvent(before, entering), 'barrier: without a boundary, the quantity-weighted blend').toEqual({quantity: 20, unitPrice: 3});
            expect(applyLotEvent(before, withBoundary(entering, 'IN')), 'IN').toEqual({quantity: 20, unitPrice: 3});
            expect(applyLotEvent(before, withBoundary(entering, ['IN'])), '[IN]').toEqual({quantity: 20, unitPrice: 3});
        });

        // Control, green before and after the cure. Why: replayed as a transfer, the 10 units would all stay.
        it('control: an ADJUSTMENT_OUT hands its units over the same with or without an OUT boundary — 10 less 4 is 6, the unit price kept', () => {
            const before = {quantity: 10, unitPrice: 2};
            // A leg leaving the scope at the market value of its day (J-10): its close price is not the lot's unit price.
            const leaving = ev('ADJUSTMENT_OUT', {quantity: '4', close_unit_price: '5'});
            expect(applyLotEvent(before, leaving), 'barrier: without a boundary, the units leave and the unit price stays').toEqual({quantity: 6, unitPrice: 2});
            expect(applyLotEvent(before, withBoundary(leaving, 'OUT')), 'OUT').toEqual({quantity: 6, unitPrice: 2});
            expect(applyLotEvent(before, withBoundary(leaving, ['OUT'])), '[OUT]').toEqual({quantity: 6, unitPrice: 2});
        });
    });
});
