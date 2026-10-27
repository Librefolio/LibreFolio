/**
 * periodChanges with a range — the two fetchers also ask the Δ over the range on screen (workstream Y, lot X-R59 A;
 * decision N80).
 *
 * One home for financial math: the backend (rule 10). The change from the first to the last point of the range a page
 * shows comes from the same two calls as the period changes (commit a8de6b584): an item that carries a `range_start`
 * answers a `range_change` — null when the item asked none, every field null when there was no usable price (rate).
 * `fetchAssetPeriodChanges` and `fetchFxPeriodChanges` take the start of the range as a third argument, as the page holds
 * it, and apply `rangeStartFor` (`utils/rangeChange.ts`) themselves:
 *   - when it gives a day, every item carries it as `range_start`, and the result gains a map of each answered item’s
 *     change as the page shows it — `rangeDeltaByAssetId` under the asset id (`assetRangeDelta`), `rangeDeltasByPair`
 *     under `BASE/QUOTE`, both ways (`fxRangeDeltas`) —, one entry per answered item, all null where the backend had no
 *     usable value;
 *   - when it gives none (no third argument, null, a start that is no day, a start after `as_of`), the items are today’s,
 *     without a `range_start` key at all, and the map is empty.
 * Everything else is unchanged: one call, the same path, the periods, the period changes, no call for no item, a failed
 * call rejected.
 *
 * `$lib/api` is mocked as in `periodChanges.test.ts`: `post` answers what each case gives it, shaped as the backend
 * serialises `FAPeriodChangesResult` and `FXPeriodChangesResult` since a8de6b584 (`range_change` on every result). The
 * body is read as the fetcher built it, not through JSON, so a `range_start` key holding nothing is caught too.
 * `RangeDelta` is imported as a type only, erased: the file runs against today’s module and fails on its assertions.
 *
 * Red today: the fetchers ignore a third argument, so no item carries a `range_start` and the result has no range map.
 * The cases that send none are red on the missing map alone: their bodies are already today’s.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const post = vi.hoisted(() => vi.fn<(path: string, body: unknown) => Promise<unknown>>());
vi.mock('$lib/api', () => ({zodiosApi: {post}, ApiError: class ApiError extends Error {}, axiosInstance: {}}));

import {fetchAssetPeriodChanges, fetchFxPeriodChanges, type PeriodSpec} from '../periodChanges';
import type {RangeDelta} from '../rangeChange';

const ASSET_PATH = '/api/v1/assets/prices/period-changes';
const FX_PATH = '/api/v1/fx/currencies/period-changes';
/** The anchor day of every request here: the end of a range on screen. */
const AS_OF = '2026-10-16';
/** The start of that range, a year before: the day every item carries as `range_start`. */
const RANGE_START = '2025-10-16';

/** The backend’s fixed periods, in display order: the `key` and `days` of `FAPeriodChange` and `FXPeriodChange`. */
const PERIODS: PeriodSpec[] = [
    {key: '1D', days: 1},
    {key: '1W', days: 7},
    {key: '1M', days: 30},
    {key: '3M', days: 91},
    {key: '6M', days: 182},
    {key: '1Y', days: 365},
    {key: '2Y', days: 730},
    {key: '3Y', days: 1095},
    {key: '5Y', days: 1825},
];

/** No change: an item whose range had no usable price (rate). */
const NONE: RangeDelta = {abs: null, pct: null};

/**
 * A third argument that gives no `range_start`, by case. `undefined` stands for no third argument at all, the call of
 * today’s pages. Every string but "min" and the day after `as_of` comes before `as_of` as text: only its shape or the
 * calendar can refuse it.
 */
const NO_START_CASES: Array<{case: string; start: string | null | undefined}> = [
    {case: 'there is no third argument, as today’s pages call it', start: undefined},
    {case: 'it is null', start: null},
    {case: 'it is empty', start: ''},
    {case: 'it is the "min" sentinel, not yet resolved to a day', start: 'min'},
    {case: 'it is not a bare YYYY-MM-DD', start: '2025-1-16'},
    {case: 'it is a day the calendar does not have', start: '2026-02-30'},
    {case: 'it falls after as_of', start: '2026-10-17'},
];

/** The period changes of an item, in percent: every period null but those in `values` (binary-exact ratios only). */
function deltas(values: Record<string, number> = {}): Record<string, number | null> {
    return Object.fromEntries(PERIODS.map(({key}) => [key, key in values ? values[key] : null]));
}

/** An asset’s `range_change` as the backend serialises `FARangeChange`. */
function assetChange(changeAbs: string | null, changeRatio: string | null, referenceDate: string | null = RANGE_START) {
    return {reference_date: referenceDate, change_abs: changeAbs, change_ratio: changeRatio};
}

/** A pair’s `range_change` as the backend serialises `FXRangeChange`: the direct change, then the inverse one. */
function fxChange(changeAbs: string | null, changeRatio: string | null, inverseChangeAbs: string | null, inverseChangeRatio: string | null, referenceDate: string | null = RANGE_START) {
    return {reference_date: referenceDate, change_abs: changeAbs, change_ratio: changeRatio, inverse_change_abs: inverseChangeAbs, inverse_change_ratio: inverseChangeRatio};
}

/** One asset of an answer (`FAPeriodChangesResult`): every period, its ratio from `ratios` or null, and its `range_change`. */
function assetItem(assetId: number, rangeChange: ReturnType<typeof assetChange> | null, ratios: Record<string, string> = {}) {
    return {asset_id: assetId, as_of: AS_OF, currency: 'EUR', periods: PERIODS.map(({key, days}) => ({key, days, change_ratio: ratios[key] ?? null})), range_change: rangeChange, errors: []};
}

/** One pair of an answer (`FXPeriodChangesResult`): every period, its `[change_ratio, inverse_change_ratio]` from `ratios` or null, and its `range_change`. */
function fxItem(base: string, quote: string, rangeChange: ReturnType<typeof fxChange> | null, ratios: Record<string, [string, string]> = {}) {
    return {
        base,
        quote,
        as_of: AS_OF,
        periods: PERIODS.map(({key, days}) => ({key, days, change_ratio: ratios[key]?.[0] ?? null, inverse_change_ratio: ratios[key]?.[1] ?? null})),
        range_change: rangeChange,
        errors: [],
    };
}

/** The body of the one call as the fetcher built it — not through JSON, where a key holding `undefined` would vanish. */
function sentBody(): unknown {
    expect(post, 'one call, whatever the number of items').toHaveBeenCalledTimes(1);
    return post.mock.calls[0][1];
}

beforeEach(() => {
    post.mockReset();
});

describe('fetchAssetPeriodChanges with a range — the Assets list’s Δ over the range', () => {
    it('sends the start of the range on every item of the one call, beside its as_of', async () => {
        post.mockResolvedValueOnce({items: [assetItem(7, assetChange('1', '0.125')), assetItem(3, assetChange('1', '0.125')), assetItem(11, assetChange('1', '0.125'))]});

        await fetchAssetPeriodChanges([7, 3, 11], AS_OF, RANGE_START);

        const body = sentBody();
        expect(post.mock.calls[0][0]).toBe(ASSET_PATH);
        expect(body, 'one item per asset, each with the range’s start').toStrictEqual([
            {asset_id: 7, as_of: AS_OF, range_start: RANGE_START},
            {asset_id: 3, as_of: AS_OF, range_start: RANGE_START},
            {asset_id: 11, as_of: AS_OF, range_start: RANGE_START},
        ]);
    });

    it.each([
        // X5-6 (D-P4 L4): the backend values any day, so the true start goes out, not 1900-01-01.
        {case: 'sends a start before 1900 as it is', start: '1850-03-01', sent: '1850-03-01'},
        {case: 'sends a start on as_of: a range of one day', start: AS_OF, sent: AS_OF},
    ])('$case', async ({start, sent}) => {
        post.mockResolvedValueOnce({items: [assetItem(7, assetChange(null, null, null))]});

        await fetchAssetPeriodChanges([7], AS_OF, start);

        expect(sentBody()).toStrictEqual([{asset_id: 7, as_of: AS_OF, range_start: sent}]);
    });

    it('gives each asset’s change over the range under its id, as the page shows it, beside the periods and their changes', async () => {
        post.mockResolvedValueOnce({
            items: [assetItem(7, assetChange('10.5', '0.125'), {'1D': '0.125'}), assetItem(3, assetChange('-2.25', '-0.0625')), assetItem(11, assetChange(null, null, null), {'5Y': '1.5'})],
        });

        const result = await fetchAssetPeriodChanges([7, 3, 11], AS_OF, RANGE_START);

        expect(result.periods, 'control: the periods of the answer').toEqual(PERIODS);
        expect(result.deltasByAssetId.get(7), 'control: the period changes, read as before').toEqual(deltas({'1D': 12.5}));
        expect(result.deltasByAssetId.get(11)).toEqual(deltas({'5Y': 150}));
        expect(result.rangeDeltaByAssetId, 'one entry per answered asset: abs in the price’s unit, pct in percent, null without a usable price').toEqual(
            new Map<number, RangeDelta>([
                [7, {abs: 10.5, pct: 12.5}],
                [3, {abs: -2.25, pct: -6.25}],
                [11, NONE],
            ]),
        );
    });

    it('gives an entry, all null, to an asset answered with no range_change, or without the field', async () => {
        // The backend answers an object to every item that asked one: a reader of the answer survives one that is not.
        post.mockResolvedValueOnce({items: [assetItem(7, null), {asset_id: 5, as_of: AS_OF, currency: null, periods: [], errors: []}]});

        const result = await fetchAssetPeriodChanges([7, 5], AS_OF, RANGE_START);

        expect(result.rangeDeltaByAssetId).toEqual(
            new Map<number, RangeDelta>([
                [7, NONE],
                [5, NONE],
            ]),
        );
    });

    it.each(NO_START_CASES)('sends today’s items, without a range_start key, and gives no range change, when $case', async ({start}) => {
        post.mockResolvedValueOnce({items: [assetItem(7, null), assetItem(3, null)]});

        const result = start === undefined ? await fetchAssetPeriodChanges([7, 3], AS_OF) : await fetchAssetPeriodChanges([7, 3], AS_OF, start);

        expect(sentBody(), 'the items of a request without a range, exactly: no range_start key, not even an empty one').toStrictEqual([
            {asset_id: 7, as_of: AS_OF},
            {asset_id: 3, as_of: AS_OF},
        ]);
        expect(result.rangeDeltaByAssetId, 'no entry — not entries of nulls: nothing was asked').toEqual(new Map());
    });

    it('asks nothing for no asset, with a range or without', async () => {
        await expect(fetchAssetPeriodChanges([], AS_OF, RANGE_START)).resolves.toEqual({periods: [], deltasByAssetId: new Map(), rangeDeltaByAssetId: new Map()});
        await expect(fetchAssetPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByAssetId: new Map(), rangeDeltaByAssetId: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, a range asked or not, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /assets/prices/period-changes answered 422');
        post.mockRejectedValueOnce(failure);

        await expect(fetchAssetPeriodChanges([7], AS_OF, RANGE_START)).rejects.toBe(failure);
    });
});

describe('fetchFxPeriodChanges with a range — the FX list’s Δ over the range, both ways', () => {
    it('sends the start of the range on every pair of the one call, beside its base, quote and as_of only', async () => {
        // A pair configuration handed in whole: the backend refuses any field it does not declare (StrictModel, a 422).
        const configs = [
            {base: 'EUR', quote: 'USD', slug: 'EUR-USD'},
            {base: 'CHF', quote: 'EUR', slug: 'CHF-EUR'},
        ];
        post.mockResolvedValueOnce({items: [fxItem('EUR', 'USD', fxChange('0.2', '0.25', '-0.25', '-0.2')), fxItem('CHF', 'EUR', fxChange('0.2', '0.25', '-0.25', '-0.2'))]});

        await fetchFxPeriodChanges(configs, AS_OF, RANGE_START);

        const body = sentBody();
        expect(post.mock.calls[0][0]).toBe(FX_PATH);
        expect(body, 'one item per pair, as the pair is configured, each with the range’s start').toStrictEqual([
            {base: 'EUR', quote: 'USD', as_of: AS_OF, range_start: RANGE_START},
            {base: 'CHF', quote: 'EUR', as_of: AS_OF, range_start: RANGE_START},
        ]);
    });

    it.each([
        // X5-6 (D-P4 L4): the backend values any day, so the true start goes out, not 1900-01-01.
        {case: 'sends a start before 1900 as it is', start: '0999-12-31', sent: '0999-12-31'},
        {case: 'sends a start on as_of: a range of one day', start: AS_OF, sent: AS_OF},
    ])('$case', async ({start, sent}) => {
        post.mockResolvedValueOnce({items: [fxItem('EUR', 'USD', fxChange(null, null, null, null, null))]});

        await fetchFxPeriodChanges([{base: 'EUR', quote: 'USD'}], AS_OF, start);

        expect(sentBody()).toStrictEqual([{base: 'EUR', quote: 'USD', as_of: AS_OF, range_start: sent}]);
    });

    it('gives each pair’s change over the range under BASE/QUOTE, both ways: direct from change_abs and change_ratio, inverse from inverse_change_abs and inverse_change_ratio', async () => {
        // The inverse figures are not the inversion of the direct ones (0.5 → 0.625 inverted is −0.4 and −20 %): each
        // orientation is the answer’s own, read and never derived.
        post.mockResolvedValueOnce({
            items: [fxItem('EUR', 'USD', fxChange('0.125', '0.25', '-0.0375', '-0.3'), {'1D': ['0.25', '-0.2']}), fxItem('CHF', 'EUR', fxChange(null, null, null, null, null))],
        });

        const result = await fetchFxPeriodChanges(
            [
                {base: 'EUR', quote: 'USD'},
                {base: 'CHF', quote: 'EUR'},
            ],
            AS_OF,
            RANGE_START,
        );

        expect(result.periods, 'control: the periods of the answer').toEqual(PERIODS);
        expect(result.deltasByPair.get('EUR/USD'), 'control: the period changes, both ways, read as before').toEqual({direct: deltas({'1D': 25}), inverse: deltas({'1D': -20})});
        expect(result.rangeDeltasByPair, 'one entry per answered pair, both ways, null without a usable rate').toEqual(
            new Map<string, {direct: RangeDelta; inverse: RangeDelta}>([
                ['EUR/USD', {direct: {abs: 0.125, pct: 25}, inverse: {abs: -0.0375, pct: -30}}],
                ['CHF/EUR', {direct: NONE, inverse: NONE}],
            ]),
        );
    });

    it('gives an entry, all null both ways, to a pair answered with no range_change, or without the field', async () => {
        // The backend answers an object to every item that asked one: a reader of the answer survives one that is not.
        post.mockResolvedValueOnce({items: [fxItem('EUR', 'USD', null), {base: 'CHF', quote: 'EUR', as_of: AS_OF, errors: []}]});

        const result = await fetchFxPeriodChanges(
            [
                {base: 'EUR', quote: 'USD'},
                {base: 'CHF', quote: 'EUR'},
            ],
            AS_OF,
            RANGE_START,
        );

        expect(result.rangeDeltasByPair).toEqual(
            new Map<string, {direct: RangeDelta; inverse: RangeDelta}>([
                ['EUR/USD', {direct: NONE, inverse: NONE}],
                ['CHF/EUR', {direct: NONE, inverse: NONE}],
            ]),
        );
    });

    it.each(NO_START_CASES)('sends today’s pairs, without a range_start key, and gives no range change, when $case', async ({start}) => {
        const pairs = [
            {base: 'EUR', quote: 'USD'},
            {base: 'CHF', quote: 'EUR'},
        ];
        post.mockResolvedValueOnce({items: [fxItem('EUR', 'USD', null), fxItem('CHF', 'EUR', null)]});

        const result = start === undefined ? await fetchFxPeriodChanges(pairs, AS_OF) : await fetchFxPeriodChanges(pairs, AS_OF, start);

        expect(sentBody(), 'the items of a request without a range, exactly: no range_start key, not even an empty one').toStrictEqual([
            {base: 'EUR', quote: 'USD', as_of: AS_OF},
            {base: 'CHF', quote: 'EUR', as_of: AS_OF},
        ]);
        expect(result.rangeDeltasByPair, 'no entry — not entries of nulls: nothing was asked').toEqual(new Map());
    });

    it('asks nothing for no pair, with a range or without', async () => {
        await expect(fetchFxPeriodChanges([], AS_OF, RANGE_START)).resolves.toEqual({periods: [], deltasByPair: new Map(), rangeDeltasByPair: new Map()});
        await expect(fetchFxPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByPair: new Map(), rangeDeltasByPair: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, a range asked or not, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /fx/currencies/period-changes answered 422');
        post.mockRejectedValueOnce(failure);

        await expect(fetchFxPeriodChanges([{base: 'EUR', quote: 'USD'}], AS_OF, RANGE_START)).rejects.toBe(failure);
    });
});
