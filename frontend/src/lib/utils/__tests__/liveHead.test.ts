/**
 * Y6-1 — the last point of a card's series follows the live quote, on the spot.
 *
 * A quote carries the day it belongs to (`as_of_date`). A daily series either already has that day (its last point takes the quote's price)
 * or ends before it (the quote is one more day). A weekly or monthly sample has a point per bucket, so the quote moves its last point
 * instead of adding one: the bucket count, and with it the step the cache answers, does not change.
 */
import {describe, expect, it} from 'vitest';
import type {DerivedChartPoint} from '$lib/features/assets/assetPriceDerived';
import {withLiveHead} from '../liveHead';

const point = (date: string, value: number, staleDays = 0): DerivedChartPoint => ({date, value, staleDays});
const SERIES = [point('2026-10-14', 100), point('2026-10-15', 101), point('2026-10-16', 102)];

describe('withLiveHead — a daily series', () => {
    it('gives the last point the price of the quote of the same day', () => {
        expect(withLiveHead(SERIES, 'daily', '2026-10-16', 103.5)).toEqual([...SERIES.slice(0, 2), point('2026-10-16', 103.5)]);
    });

    it('a quote of the same day and the same price changes nothing: null, and the caller redraws nothing', () => {
        expect(withLiveHead(SERIES, 'daily', '2026-10-16', 102)).toBeNull();
    });

    it('a stale last point (filled backward) turns fresh with the quote of its day', () => {
        const stale = [point('2026-10-15', 101), point('2026-10-16', 102, 3)];
        expect(withLiveHead(stale, 'daily', '2026-10-16', 102)).toEqual([point('2026-10-15', 101), point('2026-10-16', 102, 0)]);
    });

    it('adds one more day when the quote is of a day after the last point', () => {
        expect(withLiveHead(SERIES, 'daily', '2026-10-19', 104)).toEqual([...SERIES, point('2026-10-19', 104)]);
    });

    it('does not touch the points before the last, nor the array given', () => {
        const before = JSON.parse(JSON.stringify(SERIES));
        const next = withLiveHead(SERIES, 'daily', '2026-10-16', 110);
        expect(SERIES).toEqual(before);
        expect(next?.slice(0, 2)).toEqual(SERIES.slice(0, 2));
    });

    it('ignores a quote of a day before the last point: it is old news', () => {
        expect(withLiveHead(SERIES, 'daily', '2026-10-15', 999)).toBeNull();
    });

    it('has no head to extend on an empty series', () => {
        expect(withLiveHead([], 'daily', '2026-10-16', 100)).toBeNull();
    });
});

describe('withLiveHead — a weekly or a monthly sample', () => {
    it.each(['weekly', 'monthly'] as const)('%s: the quote moves the last point, in price and day, and adds none', (resolution) => {
        const sample = [point('2026-09-30', 90), point('2026-10-14', 100)];
        expect(withLiveHead(sample, resolution, '2026-10-16', 103)).toEqual([point('2026-09-30', 90), point('2026-10-16', 103)]);
    });

    it('a quote of the last point’s own day only changes its price', () => {
        expect(withLiveHead([point('2026-09-30', 90), point('2026-10-16', 100)], 'weekly', '2026-10-16', 101)).toEqual([point('2026-09-30', 90), point('2026-10-16', 101)]);
    });

    it('a quote of a day before the last point is ignored', () => {
        expect(withLiveHead([point('2026-09-30', 90), point('2026-10-16', 100)], 'weekly', '2026-10-14', 50)).toBeNull();
    });
});
