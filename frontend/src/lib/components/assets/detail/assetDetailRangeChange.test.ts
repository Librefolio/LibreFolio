/**
 * assetDetailRangeChange — the Δ of the asset detail page's price summary, read from the backend (workstream Y, lot X-R59
 * B; decision N80).
 *
 * One home for financial math: the backend (rule 10). The summary's Δ runs from the first point of the range on screen to
 * the last price — the live quote when the range ends today and a live price is there, else the last stored close — and
 * stops being computed in the browser from the chart's points. The live quote's change comes with the quote
 * (`AssetDetailLive.rangeDelta`, `POST /assets/prices/current?range_start=…`); the stored series' comes from
 * `POST /assets/prices/period-changes`, whose items accept `range_start` and `target_currency` (lot A's endpoint).
 *
 * The module the page reads them through:
 *   - `summaryRangeDelta(liveShown, live, series)`: the Δ the summary shows — the live quote's when the summary shows the
 *     live price, else the series'. Never the series' beside a live price, whose last point is not the price shown, and
 *     never the live quote's beside a stored close; no change, never null, where the one it picks is not known;
 *   - `fetchSeriesRangeDelta({assetId, asOf, dateStart, targetCurrency})`: the series' Δ over `dateStart … asOf`, in the
 *     display currency when one is given. One `POST /assets/prices/period-changes` for the one asset, its `range_start`
 *     from `rangeStartFor` — none to send: no call, and no change —, `target_currency` only for a non-empty currency; the
 *     answer's item for that asset read through `assetRangeDelta`, no change without one; a failed call rejects, for the
 *     page to handle.
 *
 * `$lib/api` is mocked as in `periodChanges.rangeChange.test.ts`: `post` answers what each case gives it, shaped as the
 * backend serialises `FAPeriodChangesResponse`. The call is read as the module made it, not through JSON, so a
 * `target_currency` key holding nothing is caught too.
 *
 * Red today: the module does not exist, so the file fails to load.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {RangeDelta} from '$lib/utils/rangeChange';

const post = vi.hoisted(() => vi.fn<(path: string, body: unknown) => Promise<unknown>>());
vi.mock('$lib/api', () => ({zodiosApi: {post}, ApiError: class ApiError extends Error {}, axiosInstance: {}}));

import {fetchSeriesRangeDelta, summaryRangeDelta} from './assetDetailRangeChange';

const PATH = '/api/v1/assets/prices/period-changes';
const ASSET_ID = 7;
const OTHER_ASSET_ID = 8;
/** The end of the range on screen. */
const AS_OF = '2026-10-16';
/** Its first day, a year before. */
const DATE_START = '2025-10-16';

/** No change, known: what the summary shows where there is none. */
const NO_CHANGE: RangeDelta = {abs: null, pct: null};
/** The live quote's change over the range, as `AssetDetailLive.rangeDelta` holds it. */
const LIVE: RangeDelta = {abs: 11, pct: 12.5};
/** The stored series' change over the range: what `SERIES_CHANGE` reads as. */
const SERIES: RangeDelta = {abs: 10, pct: 11.25};

/** A `range_change` as the backend serialises `FARangeChange`. */
function change(changeAbs: string | null, changeRatio: string | null, referenceDate: string | null = DATE_START) {
    return {reference_date: referenceDate, change_abs: changeAbs, change_ratio: changeRatio};
}

/** The series' change over the range as the backend answers it: +10, +11.25 %. */
const SERIES_CHANGE = change('10', '0.1125');

/** One asset of an answer (`FAPeriodChangesResult`), with its change over the range. */
function item(assetId: number, rangeChange: unknown) {
    return {asset_id: assetId, as_of: AS_OF, currency: 'EUR', periods: [], range_change: rangeChange, errors: []};
}

/** The one call, as the module made it: its path and its body. */
function sentCall(): unknown[] {
    expect(post, 'one call').toHaveBeenCalledTimes(1);
    return post.mock.calls[0];
}

beforeEach(() => {
    post.mockReset();
});

describe('summaryRangeDelta — the Δ the price summary shows', () => {
    it.each([
        {case: 'the live quote’s, beside the live price', liveShown: true, live: LIVE, series: SERIES, shown: LIVE},
        {case: 'no change while the live quote’s is not known, never the series’ beside the live price', liveShown: true, live: null, series: SERIES, shown: NO_CHANGE},
        {case: 'no change beside the live price when neither is known', liveShown: true, live: null, series: null, shown: NO_CHANGE},
        {case: 'the series’, beside the last stored close', liveShown: false, live: LIVE, series: SERIES, shown: SERIES},
        {case: 'no change while the series’ is not known, never the live quote’s beside a stored close', liveShown: false, live: LIVE, series: null, shown: NO_CHANGE},
        {case: 'no change beside a stored close when neither is known', liveShown: false, live: null, series: null, shown: NO_CHANGE},
    ])('shows $case', ({liveShown, live, series, shown}) => {
        expect(summaryRangeDelta(liveShown, live, series)).toEqual(shown);
    });

    it('shows a known absence as it is: the one it picks having no change is never replaced by the other', () => {
        expect(summaryRangeDelta(true, NO_CHANGE, SERIES), 'beside the live price').toEqual(NO_CHANGE);
        expect(summaryRangeDelta(false, LIVE, NO_CHANGE), 'beside a stored close').toEqual(NO_CHANGE);
    });
});

describe('fetchSeriesRangeDelta — the stored series’ Δ over the range on screen', () => {
    it('asks POST /assets/prices/period-changes once, for the asset, up to as_of, from the range’s first day, and reads the change answered', async () => {
        post.mockResolvedValueOnce({items: [item(ASSET_ID, SERIES_CHANGE)]});

        await expect(fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: DATE_START})).resolves.toEqual(SERIES);

        expect(sentCall(), 'the path, and one item: no target_currency, the asset’s own currency').toStrictEqual([PATH, [{asset_id: ASSET_ID, as_of: AS_OF, range_start: DATE_START}]]);
    });

    it.each([
        {case: 'undefined', targetCurrency: undefined, sent: {}},
        {case: 'null', targetCurrency: null, sent: {}},
        {case: 'empty', targetCurrency: '', sent: {}},
        {case: 'EUR', targetCurrency: 'EUR', sent: {target_currency: 'EUR'}},
    ])('sends target_currency only for a display currency that is one: $case', async ({targetCurrency, sent}) => {
        post.mockResolvedValueOnce({items: [item(ASSET_ID, SERIES_CHANGE)]});

        await fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: DATE_START, targetCurrency});

        expect(sentCall()).toStrictEqual([PATH, [{asset_id: ASSET_ID, as_of: AS_OF, range_start: DATE_START, ...sent}]]);
    });

    it('raises a first day before 1900 to 1900-01-01, the first day the backend values', async () => {
        post.mockResolvedValueOnce({items: [item(ASSET_ID, SERIES_CHANGE)]});

        await fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: '1850-06-01', targetCurrency: 'EUR'});

        expect(sentCall()).toStrictEqual([PATH, [{asset_id: ASSET_ID, as_of: AS_OF, range_start: '1900-01-01', target_currency: 'EUR'}]]);
    });

    it.each([
        {case: 'the "min" sentinel, not yet a day', dateStart: 'min', asOf: AS_OF},
        {case: 'an empty first day', dateStart: '', asOf: AS_OF},
        {case: 'a first day the calendar does not have', dateStart: '2026-02-30', asOf: AS_OF},
        {case: 'a first day after as_of', dateStart: '2026-10-17', asOf: AS_OF},
        {case: 'an as_of the calendar does not have', dateStart: DATE_START, asOf: '2026-13-01'},
    ])('asks nothing and resolves no change for $case: no range_start to send', async ({dateStart, asOf}) => {
        await expect(fetchSeriesRangeDelta({assetId: ASSET_ID, asOf, dateStart, targetCurrency: 'EUR'})).resolves.toEqual(NO_CHANGE);

        expect(post).not.toHaveBeenCalled();
    });

    it('reads the item of the asset it asked for, wherever it stands in the answer', async () => {
        post.mockResolvedValueOnce({items: [item(OTHER_ASSET_ID, change('99', '0.99')), item(ASSET_ID, SERIES_CHANGE)]});

        await expect(fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: DATE_START})).resolves.toEqual(SERIES);
    });

    it.each([
        {answer: 'no items field', response: {}},
        {answer: 'an empty list', response: {items: []}},
        {answer: 'another asset’s item only', response: {items: [item(OTHER_ASSET_ID, SERIES_CHANGE)]}},
        {answer: 'the asset’s item with no range_change', response: {items: [item(ASSET_ID, null)]}},
        {answer: 'the asset’s item with a range the backend could not value, every field null', response: {items: [item(ASSET_ID, change(null, null, null))]}},
    ])('resolves no change for $answer', async ({response}) => {
        post.mockResolvedValueOnce(response);

        await expect(fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: DATE_START})).resolves.toEqual(NO_CHANGE);
    });

    it('rejects with the failure of the call, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /assets/prices/period-changes answered 422');
        post.mockRejectedValueOnce(failure);

        await expect(fetchSeriesRangeDelta({assetId: ASSET_ID, asOf: AS_OF, dateStart: DATE_START})).rejects.toBe(failure);
    });
});
