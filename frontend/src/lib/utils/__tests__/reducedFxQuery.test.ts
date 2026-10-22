/**
 * reducedFxQuery.ts (Y-40, the FX half): what the FX list asks `POST /fx/currencies/convert` for the cards in the
 * rolling-return view, on the backend's sampled conversions (Z-29fx).
 *
 * The contract:
 * - A card asks one conversion of 1 unit in the direction the card shows the pair (swapped: from the quote), over the
 *   range on screen, with the calendar rolling return as its signal, named `fx:<slug>` (`key`), with the `max_points` its
 *   plot takes: the backend reduces the return to the card's buckets.
 * - Each FX pair compared on the card (a saved `fx-pair` signal) asks its own rolling return on the card's buckets: a
 *   conversion `sample_like` the card's key, in the direction the signal shows the pair (its `_inverted`). A comparison with
 *   the card's own pair asks nothing.
 * - The members of a card go together (`group`), so `bulkBatches.ts` never cuts between them; each entry says whose it is.
 * - Its cost against the backend's day budget: the range and the signals' margin.
 *
 * Pure: no store, no clock.
 *
 * Red first: the module does not exist.
 */
import {describe, expect, it} from 'vitest';

import {BULK_SIGNAL_MARGIN_DAYS, bulkRangeDays} from '$lib/api/bulkBatches';
import {compactMaxPoints} from '$lib/components/charts/timeSeriesAggregation';

import {buildFxCalendarQuery, estimateFxCalendarDays, fxCalendarRequest, fxCardKey, type FxCalendarCardInput} from '../reducedFxQuery';

const RANGE = {start: '2026-01-01', end: '2026-06-30'};
const card = (extra: Partial<FxCalendarCardInput> = {}): FxCalendarCardInput => ({slug: 'EUR-USD', base: 'EUR', quote: 'USD', inverted: false, plotWidthPx: 290, ...RANGE, windowDays: 90, pairTargets: [], ...extra});
const CAL = {instance_id: 'asset-calendar-return', signal_code: 'ASSET_CALENDAR_ROLLING_RETURN', params: {window_days: 90}};

describe('fxCalendarRequest and fxCardKey', () => {
    it('asks the calendar rolling return over the window, under the detail’s instance id', () => {
        expect(fxCalendarRequest(90)).toEqual(CAL);
    });

    it('names a card’s conversion by its pair, in the characters the backend allows for a key', () => {
        expect(fxCardKey('EUR-USD')).toBe('fx:EUR-USD');
        expect(fxCardKey('EUR-USD')).toMatch(/^[A-Za-z0-9_.:-]{1,64}$/);
    });
});

describe('buildFxCalendarQuery', () => {
    it('asks a card’s rolling return on 1 unit of its pair, named, with the max_points of its plot', () => {
        const [entry] = buildFxCalendarQuery([card()]);

        expect(entry.request).toEqual({from_amount: {code: 'EUR', amount: '1'}, to: 'USD', date_range: RANGE, signals: [CAL], key: 'fx:EUR-USD', max_points: compactMaxPoints(290)});
        expect([entry.group, entry.role, entry.cardSlug, entry.configId]).toEqual(['fx:EUR-USD', 'card', 'EUR-USD', null]);
    });

    it('asks a swapped card the way it shows the pair: from the quote', () => {
        const [entry] = buildFxCalendarQuery([card({inverted: true})]);

        expect([entry.request.from_amount.code, entry.request.to]).toEqual(['USD', 'EUR']);
    });

    it('asks each compared pair on the card’s buckets, the way its signal shows it, and nothing for the card’s own pair', () => {
        const entries = buildFxCalendarQuery([
            card({
                pairTargets: [
                    {configId: 'fx-gbp', pairSlug: 'EUR-GBP', inverted: false},
                    {configId: 'fx-jpy', pairSlug: 'USD-JPY', inverted: true},
                    {configId: 'fx-self', pairSlug: 'EUR-USD', inverted: false},
                ],
            }),
        ]);

        expect(entries.slice(1).map((entry) => entry.request)).toEqual([
            {from_amount: {code: 'EUR', amount: '1'}, to: 'GBP', date_range: RANGE, signals: [CAL], sample_like: 'fx:EUR-USD'},
            {from_amount: {code: 'JPY', amount: '1'}, to: 'USD', date_range: RANGE, signals: [CAL], sample_like: 'fx:EUR-USD'},
        ]);
        expect(entries.map((entry) => [entry.group, entry.role, entry.configId])).toEqual([
            ['fx:EUR-USD', 'card', null],
            ['fx:EUR-USD', 'target', 'fx-gbp'],
            ['fx:EUR-USD', 'target', 'fx-jpy'],
        ]);
    });

    it('keeps the members of a card together, before the next card’s', () => {
        const entries = buildFxCalendarQuery([card({pairTargets: [{configId: 'fx-gbp', pairSlug: 'EUR-GBP', inverted: false}]}), card({slug: 'USD-CHF', base: 'USD', quote: 'CHF'})]);

        expect(entries.map((entry) => entry.group)).toEqual(['fx:EUR-USD', 'fx:EUR-USD', 'fx:USD-CHF']);
    });
});

describe('estimateFxCalendarDays', () => {
    it('counts the range and the signals’ margin', () => {
        const [entry] = buildFxCalendarQuery([card()]);

        expect(estimateFxCalendarDays(entry, '2026-06-30')).toBe(bulkRangeDays(RANGE.start, RANGE.end, '2026-06-30') + BULK_SIGNAL_MARGIN_DAYS);
    });
});
