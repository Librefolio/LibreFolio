/**
 * The reduced price cache (Z-29b): the series a card draws, sampled by the backend for the card's plot, kept beside the
 * daily cache (`assetPriceStoreRegistry`), which this does not touch. It answers by asset, range and step: the step a
 * width asks is computed from the fill's own counts, so a resize that keeps the step reads the same entry and one that
 * changes it reads nothing and the page asks again (MF n2). The comparison targets are sampled like a card, so they are
 * kept by card. A price catch-up (`{kind: 'prices'}` on the portfolio bus) marks everything stale: still readable, to be
 * read again.
 *
 * Red first: the module does not exist.
 */
import {afterEach, describe, expect, it} from 'vitest';

import {notifyPricesCaughtUp} from '$lib/stores/portfolio/portfolioMutation';
import type {DerivedPriceState} from '$lib/utils/assetPriceDerived';

import {reducedPrices} from '../reducedPriceCache';

const RANGE = ['2025-01-01', '2026-06-30'] as const;

/** A series of `count` points from `first`, a week apart, the way a weekly sample is. */
function weekly(first: string, last: string, count = 3): {resolution: 'weekly'; derived: DerivedPriceState} {
    const chartData = Array.from({length: count}, (_, i) => ({date: i === count - 1 ? last : `2026-01-${String(11 + 7 * i).padStart(2, '0')}`, value: 100 + i, staleDays: 0}));
    return {resolution: 'weekly', derived: {lastPrice: 100 + count - 1, chartData, base: {date: first, value: 99}}};
}

function daily(first: string, days: number): {resolution: 'daily'; derived: DerivedPriceState} {
    const chartData = Array.from({length: days}, (_, i) => ({date: new Date(Date.parse(first) + i * 86_400_000).toISOString().slice(0, 10), value: 100 + i, staleDays: 0}));
    return {resolution: 'daily', derived: {lastPrice: chartData[days - 1].value, chartData, base: {date: first, value: 100}}};
}

afterEach(() => reducedPrices.clear());

describe('the card series, by asset, range and step', () => {
    it('answers nothing before anything was read', () => {
        expect(reducedPrices.getCard(7, ...RANGE, 100)).toBeNull();
    });

    it('answers the entry put, fresh', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        const entry = reducedPrices.getCard(7, ...RANGE, 100);

        expect(entry).toMatchObject({resolution: 'weekly', stale: false});
        expect(entry?.derived.base).toEqual({date: '2026-01-07', value: 99});
    });

    it('keeps an asset’s ranges apart', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        expect(reducedPrices.getCard(7, '2025-01-01', '2026-03-31', 100)).toBeNull();
        expect(reducedPrices.getCard(8, ...RANGE, 100)).toBeNull();
    });

    it('answers a width that keeps the step, from the counts of the fill: 2026-01-07 to 2026-06-30 is 175 days and 26 weeks', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        // 175 days over 26 ISO weeks: weekly for a plot that takes 26 to 174 points.
        expect(reducedPrices.getCard(7, ...RANGE, 26)?.resolution).toBe('weekly');
        expect(reducedPrices.getCard(7, ...RANGE, 174)?.resolution).toBe('weekly');
    });

    it('answers nothing for a width that changes the step, either way: it is read again, never re-aggregated or turned back to daily', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        expect(reducedPrices.getCard(7, ...RANGE, 175), 'the days fit now: daily').toBeNull();
        expect(reducedPrices.getCard(7, ...RANGE, 25), 'the weeks do not fit any more: monthly').toBeNull();
    });

    it('answers a daily entry only while the days fit', () => {
        reducedPrices.putCard(7, ...RANGE, daily('2026-06-01', 30));

        expect(reducedPrices.getCard(7, ...RANGE, 30)?.resolution).toBe('daily');
        expect(reducedPrices.getCard(7, ...RANGE, 29)).toBeNull();
    });

    it('answers an empty series, nothing to fill, for any width', () => {
        reducedPrices.putCard(7, ...RANGE, {resolution: 'daily', derived: {lastPrice: null, chartData: [], base: null}});

        expect(reducedPrices.getCard(7, ...RANGE, 1)?.derived.chartData).toEqual([]);
        expect(reducedPrices.getCard(7, ...RANGE, 5000)?.derived.chartData).toEqual([]);
    });

    it('keeps one entry per asset and range: the last put replaces the one before, whatever its step', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30', 3));
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30', 4));

        expect(reducedPrices.getCard(7, ...RANGE, 100)?.derived.chartData).toHaveLength(4);

        reducedPrices.putCard(7, ...RANGE, daily('2026-06-01', 30));

        expect(reducedPrices.getCard(7, ...RANGE, 100)?.resolution).toBe('daily');
    });
});

describe('the targets of a card’s comparisons', () => {
    it('keeps a target by its card and range, for the step of the card', () => {
        reducedPrices.putTarget(9, 7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        expect(reducedPrices.getTarget(9, 7, ...RANGE, 'weekly')?.resolution).toBe('weekly');
        expect(reducedPrices.getTarget(9, 7, ...RANGE, 'monthly'), 'another step of the card: read again').toBeNull();
        expect(reducedPrices.getTarget(9, 8, ...RANGE, 'weekly'), 'another card: its own sample').toBeNull();
        expect(reducedPrices.getTarget(10, 7, ...RANGE, 'weekly')).toBeNull();
    });
});

describe('staleness and invalidation', () => {
    it('marks every entry stale after a price catch-up: still readable, to be read again', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        reducedPrices.putTarget(9, 7, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        notifyPricesCaughtUp();

        expect(reducedPrices.getCard(7, ...RANGE, 100)?.stale).toBe(true);
        expect(reducedPrices.getTarget(9, 7, ...RANGE, 'weekly')?.stale).toBe(true);
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        expect(reducedPrices.getCard(7, ...RANGE, 100)?.stale, 'a read makes it fresh').toBe(false);
    });

    it('drops what an asset’s sync touched: its card entries and every entry of it as a target, and no other', () => {
        reducedPrices.putCard(7, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        reducedPrices.putCard(9, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        reducedPrices.putTarget(9, 7, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        reducedPrices.putTarget(8, 7, ...RANGE, weekly('2026-01-07', '2026-06-30'));
        reducedPrices.putTarget(8, 9, ...RANGE, weekly('2026-01-07', '2026-06-30'));

        reducedPrices.invalidateAsset(9);

        expect(reducedPrices.getCard(9, ...RANGE, 100)).toBeNull();
        expect(reducedPrices.getTarget(9, 7, ...RANGE, 'weekly')).toBeNull();
        expect(reducedPrices.getCard(7, ...RANGE, 100)).not.toBeNull();
        expect(reducedPrices.getTarget(8, 7, ...RANGE, 'weekly')).not.toBeNull();
        expect(reducedPrices.getTarget(8, 9, ...RANGE, 'weekly'), 'the card 9 is gone with its targets').toBeNull();
    });
});
