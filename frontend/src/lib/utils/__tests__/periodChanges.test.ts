/**
 * periodChanges — the Δ columns of the Assets and FX lists, read from the backend (workstream X, lot X-R53).
 *
 * One home for financial math: the backend (MF-P2). The lists' Δ columns — the fixed 1D and the periods the range on
 * screen holds (1W … 5Y) — stop being computed in the browser from the prices it loaded, and come from two endpoints:
 * `POST /assets/prices/period-changes` (`[{asset_id, as_of}]`, one item per asset) and
 * `POST /fx/currencies/period-changes` (`[{base, quote, as_of}]`, one item per pair, in both orientations). A change is a
 * decimal string holding a fraction (`"0.125"` = +12.5 %), or null when the backend has no price (no rate) on either
 * day of the period.
 *
 * The module the pages read them through:
 *   - `ratioToPercent`: a ratio as the tables show it, in percent; anything that is not a finite number is null, never 0
 *     (`Number("")` is 0);
 *   - `visiblePeriodColumns`: the period columns of a range — every period but 1D, the tables' fixed column, whose days
 *     fit the whole calendar days of the range — in the order given; calendar days, so a night the clocks change takes
 *     no day away and adds none;
 *   - `fetchAssetPeriodChanges`, `fetchFxPeriodChanges`: one call each through `zodiosApi.post`, every asset (pair) in
 *     the order given, up to `as_of`, and none for an empty list; the periods of the first item that has any; each
 *     item's changes in percent, a pair's in both orientations (`direct`, `inverse`) under `BASE/QUOTE`; a failed call
 *     rejects, for the page to handle.
 *
 * `$lib/api` is mocked: `post` answers what each case gives it, shaped as the generated client declares the answers
 * (`FAPeriodChangesResponse`, `FXPeriodChangesResponse`).
 *
 * Red today: the module does not exist, so the file fails to load.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const post = vi.hoisted(() => vi.fn<(path: string, body: unknown) => Promise<unknown>>());
vi.mock('$lib/api', () => ({zodiosApi: {post}, ApiError: class ApiError extends Error {}, axiosInstance: {}}));

import {fetchAssetPeriodChanges, fetchFxPeriodChanges, ratioToPercent, visiblePeriodColumns, type PeriodSpec} from '../periodChanges';

const ASSET_PATH = '/api/v1/assets/prices/period-changes';
const FX_PATH = '/api/v1/fx/currencies/period-changes';
/** The anchor day of every request here: the end of a range on screen. */
const AS_OF = '2026-10-16';

/** The backend's fixed periods, in display order: the `key` and `days` of `FAPeriodChange` and `FXPeriodChange`. */
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

/** A percentage as the module must give it: the ratio × 100, whatever route the float takes there. */
const pct = (value: number) => expect.closeTo(value, 9);

/** The changes of an item, as the module must give them: every period null but those in `values`, in percent. */
function deltas(values: Record<string, number> = {}): Record<string, unknown> {
    return Object.fromEntries(PERIODS.map(({key}) => [key, key in values ? pct(values[key]) : null]));
}

/** One asset of an answer (`FAPeriodChangesResult`): every period, its ratio from `ratios` or null. */
function assetItem(assetId: number, ratios: Record<string, string> = {}) {
    return {asset_id: assetId, as_of: AS_OF, currency: 'EUR', periods: PERIODS.map(({key, days}) => ({key, days, change_ratio: ratios[key] ?? null})), errors: []};
}

/** One pair of an answer (`FXPeriodChangesResult`): every period, its `[change_ratio, inverse_change_ratio]` from `ratios` or null. */
function fxItem(base: string, quote: string, ratios: Record<string, [string, string]> = {}) {
    return {
        base,
        quote,
        as_of: AS_OF,
        periods: PERIODS.map(({key, days}) => ({key, days, change_ratio: ratios[key]?.[0] ?? null, inverse_change_ratio: ratios[key]?.[1] ?? null})),
        errors: [],
    };
}

/** The body of the one call, as it reaches the backend: through JSON, where a key holding `undefined` is not sent. */
function sentBody(): unknown {
    expect(post, 'one call, whatever the number of items').toHaveBeenCalledTimes(1);
    return JSON.parse(JSON.stringify(post.mock.calls[0][1]));
}

beforeEach(() => {
    post.mockReset();
});

describe('ratioToPercent — a backend ratio, as the tables show it', () => {
    it.each([
        ['0.125', 12.5],
        ['-0.25', -25],
        ['0', 0],
        ['0.0125', 1.25],
        ['1.5', 150],
    ])('reads %s as %s percent', (ratio, percent) => {
        expect(ratioToPercent(ratio)).toBeCloseTo(percent, 9);
    });

    it.each([
        ['null', null],
        ['undefined', undefined],
        ['an empty string', ''],
        ['a word', 'abc'],
        ['Infinity', 'Infinity'],
        ['-Infinity', '-Infinity'],
        ['NaN', 'NaN'],
    ])('reads %s as null: a change the table cannot show, never 0', (_case, ratio) => {
        expect(ratioToPercent(ratio as string | null | undefined)).toBeNull();
    });
});

describe('visiblePeriodColumns — the period columns of a range', () => {
    const keysOf = (columns: readonly PeriodSpec[]) => columns.map(({key}) => key);

    it('never offers 1D, the tables’ fixed column: five years hold every other period', () => {
        // 2021-10-16 … 2026-10-16: 1826 days, 29 February 2024 among them, so 5Y (1825) fits.
        expect(visiblePeriodColumns(PERIODS, '2021-10-16', '2026-10-16')).toEqual(PERIODS.filter(({key}) => key !== '1D'));
    });

    it.each([
        {case: 'a range of no day holds none', start: '2026-10-16', end: '2026-10-16', keys: []},
        {case: 'a range of one day holds none: 1D is the fixed column', start: '2026-10-15', end: '2026-10-16', keys: []},
        {case: 'a range of six days holds none', start: '2026-10-01', end: '2026-10-07', keys: []},
        {case: 'exactly seven days hold 1W', start: '2026-10-01', end: '2026-10-08', keys: ['1W']},
        {case: 'twenty-nine days hold 1W only', start: '2026-09-01', end: '2026-09-30', keys: ['1W']},
        {case: 'exactly thirty days hold 1W and 1M', start: '2026-09-01', end: '2026-10-01', keys: ['1W', '1M']},
        {case: 'a year holds 1W … 1Y, not 2Y', start: '2025-10-16', end: '2026-10-16', keys: ['1W', '1M', '3M', '6M', '1Y']},
    ])('$case ($start … $end)', ({start, end, keys}) => {
        expect(keysOf(visiblePeriodColumns(PERIODS, start, end))).toEqual(keys);
    });

    it('keeps the order it is given', () => {
        const reversed = [...PERIODS].reverse();

        expect(keysOf(visiblePeriodColumns(reversed, '2025-10-16', '2026-10-16'))).toEqual(['1Y', '6M', '3M', '1M', '1W']);
    });

    it('offers none when the end comes before the start, or a date is not a calendar day', () => {
        expect(visiblePeriodColumns(PERIODS, '2026-10-08', '2026-10-01'), 'the end a week before the start: no range, not a week').toEqual([]);
        expect(visiblePeriodColumns(PERIODS, '2026-10-16', '2021-10-16'), 'the end five years before the start').toEqual([]);
        expect(visiblePeriodColumns(PERIODS, 'not-a-date', '2026-10-16'), 'a start that is no date').toEqual([]);
        expect(visiblePeriodColumns(PERIODS, '', '2026-10-16'), 'an empty start').toEqual([]);
        expect(visiblePeriodColumns(PERIODS, '2021-10-16', '2026-13-01'), 'an end in a thirteenth month').toEqual([]);
    });

    describe('counted on calendar days, in a zone whose clocks change (Europe/Rome)', () => {
        /** How long a local day lasts, in hours: 24, except on the nights the clocks change. */
        function localDayHours(year: number, monthIndex: number, day: number): number {
            return (new Date(year, monthIndex, day + 1).getTime() - new Date(year, monthIndex, day).getTime()) / 3_600_000;
        }

        /**
         * `read`, run with the process in Europe/Rome whatever zone the suite started in, the zone put back after. Node
         * re-reads the zone when `process.env.TZ` is assigned (as in `assetSetLevels.test.ts`); the premises prove it
         * took, so a suite started in UTC cannot pass these rows for want of a night that is not 24 hours.
         */
        function inEuropeRome<T>(read: () => T): T {
            const previousTimeZone = process.env.TZ;
            process.env.TZ = 'Europe/Rome';
            try {
                expect(localDayHours(2026, 2, 29), 'premise: in Europe/Rome, Sunday 29 March 2026 lasts 23 hours').toBe(23);
                expect(localDayHours(2026, 9, 25), 'premise: in Europe/Rome, Sunday 25 October 2026 lasts 25 hours').toBe(25);
                return read();
            } finally {
                if (previousTimeZone === undefined) delete process.env.TZ;
                else process.env.TZ = previousTimeZone;
            }
        }

        // Read from local midnight to local midnight, the first two weeks last 168 hours: the clocks change at 02:00
        // (03:00 in October) of their last day, after its midnight. The others span the night itself, and the hours given
        // are theirs in Europe/Rome: a range read as instants rather than calendar days comes out a day short (167 hours
        // floored to six days) or a day long (145 hours rounded up to seven).
        it.each([
            {case: 'a week ending on the Sunday the clocks go forward holds 1W', start: '2026-03-22', end: '2026-03-29', keys: ['1W']},
            {case: 'a week ending on the Sunday the clocks go back holds 1W', start: '2026-10-18', end: '2026-10-25', keys: ['1W']},
            {case: 'a week across the night the clocks go forward (167 hours) holds 1W', start: '2026-03-23', end: '2026-03-30', keys: ['1W']},
            {case: 'a week across the night the clocks go back (169 hours) holds 1W', start: '2026-10-19', end: '2026-10-26', keys: ['1W']},
            {case: 'six days across the night the clocks go back (145 hours) are still six', start: '2026-10-20', end: '2026-10-26', keys: []},
            {case: 'thirty days across the night the clocks go forward (719 hours) hold 1M', start: '2026-03-15', end: '2026-04-14', keys: ['1W', '1M']},
        ])('$case ($start … $end)', ({start, end, keys}) => {
            expect(inEuropeRome(() => keysOf(visiblePeriodColumns(PERIODS, start, end)))).toEqual(keys);
        });
    });
});

describe('fetchAssetPeriodChanges — the Assets list’s Δ columns', () => {
    it('asks POST /assets/prices/period-changes once: every asset in the order given, up to as_of, in its own currency', async () => {
        post.mockResolvedValueOnce({items: [assetItem(7), assetItem(3), assetItem(11)]});

        await fetchAssetPeriodChanges([7, 3, 11], AS_OF);

        const body = sentBody();
        expect(post.mock.calls[0][0]).toBe(ASSET_PATH);
        expect(body, 'one item per asset, as_of the end of the range and no target_currency: a Δ compares the asset’s own prices').toStrictEqual([
            {asset_id: 7, as_of: AS_OF},
            {asset_id: 3, as_of: AS_OF},
            {asset_id: 11, as_of: AS_OF},
        ]);
    });

    it('gives the periods, and each asset’s changes in percent under its id', async () => {
        post.mockResolvedValueOnce({items: [assetItem(7, {'1D': '0.125', '1W': '-0.25', '1M': '0'}), assetItem(3), assetItem(11, {'1D': '-0.0625', '5Y': '1.5'})]});

        const result = await fetchAssetPeriodChanges([7, 3, 11], AS_OF);

        expect(result.periods, 'the key and days of each period of the answer, in its order').toEqual(PERIODS);
        expect([...result.deltasByAssetId.keys()].sort((a, b) => a - b)).toEqual([3, 7, 11]);
        expect(result.deltasByAssetId.get(7)).toEqual(deltas({'1D': 12.5, '1W': -25, '1M': 0}));
        expect(result.deltasByAssetId.get(3), 'no change the backend could compute: every period null').toEqual(deltas());
        expect(result.deltasByAssetId.get(11)).toEqual(deltas({'1D': -6.25, '5Y': 150}));
    });

    it('takes the periods from the first item that has any: an asset with no price up to as_of has no change', async () => {
        post.mockResolvedValueOnce({
            items: [{asset_id: 7, as_of: AS_OF, currency: null, periods: [], errors: []}, {asset_id: 5, as_of: AS_OF, currency: null, errors: []}, assetItem(3, {'1M': '0.02'})],
        });

        const result = await fetchAssetPeriodChanges([7, 5, 3], AS_OF);

        expect(result.periods, 'the periods of the third asset, the first that has any').toEqual(PERIODS);
        expect(result.deltasByAssetId.get(7), 'an empty list of periods').toEqual({});
        expect(result.deltasByAssetId.get(5), 'no list of periods at all').toEqual({});
        expect(result.deltasByAssetId.get(3)).toEqual(deltas({'1M': 2}));
    });

    it('gives no period when no item has any', async () => {
        post.mockResolvedValueOnce({items: [{asset_id: 7, as_of: AS_OF, currency: null, periods: [], errors: []}]});

        const result = await fetchAssetPeriodChanges([7], AS_OF);

        expect(result.periods).toEqual([]);
        expect(result.deltasByAssetId.get(7)).toEqual({});
    });

    it('asks nothing for no asset', async () => {
        await expect(fetchAssetPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByAssetId: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /assets/prices/period-changes answered 500');
        post.mockRejectedValueOnce(failure);

        await expect(fetchAssetPeriodChanges([7], AS_OF)).rejects.toBe(failure);
    });
});

describe('fetchFxPeriodChanges — the FX list’s Δ columns, in both orientations', () => {
    it('asks POST /fx/currencies/period-changes once: every pair in the order given, up to as_of, its base and quote only', async () => {
        // A pair configuration handed in whole: the backend refuses any field it does not declare (StrictModel, a 422).
        const configs = [
            {base: 'EUR', quote: 'USD', slug: 'EUR-USD'},
            {base: 'CHF', quote: 'EUR', slug: 'CHF-EUR'},
            {base: 'GBP', quote: 'JPY', slug: 'GBP-JPY'},
        ];
        post.mockResolvedValueOnce({items: [fxItem('EUR', 'USD'), fxItem('CHF', 'EUR'), fxItem('GBP', 'JPY')]});

        await fetchFxPeriodChanges(configs, AS_OF);

        const body = sentBody();
        expect(post.mock.calls[0][0]).toBe(FX_PATH);
        expect(body, 'one item per pair, as the pair is configured, as_of the end of the range').toStrictEqual([
            {base: 'EUR', quote: 'USD', as_of: AS_OF},
            {base: 'CHF', quote: 'EUR', as_of: AS_OF},
            {base: 'GBP', quote: 'JPY', as_of: AS_OF},
        ]);
    });

    it('gives the periods, and each pair’s changes in percent under BASE/QUOTE: direct from change_ratio, inverse from inverse_change_ratio', async () => {
        // 1M's inverse is not the inversion of its direct change (that would be −9.09 %): the inverse orientation is the
        // answer's own figure, read and never derived.
        post.mockResolvedValueOnce({
            items: [fxItem('EUR', 'USD', {'1D': ['0.25', '-0.2'], '1W': ['-0.5', '1'], '1M': ['0.1', '-0.3']}), fxItem('CHF', 'EUR', {'5Y': ['1', '-0.5']})],
        });

        const result = await fetchFxPeriodChanges(
            [
                {base: 'EUR', quote: 'USD'},
                {base: 'CHF', quote: 'EUR'},
            ],
            AS_OF,
        );

        expect(result.periods, 'the key and days of each period of the answer, in its order').toEqual(PERIODS);
        expect([...result.deltasByPair.keys()].sort()).toEqual(['CHF/EUR', 'EUR/USD']);
        expect(result.deltasByPair.get('EUR/USD')).toEqual({direct: deltas({'1D': 25, '1W': -50, '1M': 10}), inverse: deltas({'1D': -20, '1W': 100, '1M': -30})});
        expect(result.deltasByPair.get('CHF/EUR')).toEqual({direct: deltas({'5Y': 100}), inverse: deltas({'5Y': -50})});
    });

    it('takes the periods from the first item that has any: a pair without them has no change in either orientation', async () => {
        post.mockResolvedValueOnce({
            items: [{base: 'EUR', quote: 'USD', as_of: AS_OF, periods: [], errors: ['no rate']}, {base: 'CHF', quote: 'EUR', as_of: AS_OF, errors: []}, fxItem('GBP', 'JPY', {'1D': ['0.02', '-0.0196']})],
        });

        const result = await fetchFxPeriodChanges(
            [
                {base: 'EUR', quote: 'USD'},
                {base: 'CHF', quote: 'EUR'},
                {base: 'GBP', quote: 'JPY'},
            ],
            AS_OF,
        );

        expect(result.periods, 'the periods of the third pair, the first that has any').toEqual(PERIODS);
        expect(result.deltasByPair.get('EUR/USD'), 'an empty list of periods').toEqual({direct: {}, inverse: {}});
        expect(result.deltasByPair.get('CHF/EUR'), 'no list of periods at all').toEqual({direct: {}, inverse: {}});
        expect(result.deltasByPair.get('GBP/JPY')).toEqual({direct: deltas({'1D': 2}), inverse: deltas({'1D': -1.96})});
    });

    it('asks nothing for no pair', async () => {
        await expect(fetchFxPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByPair: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /fx/currencies/period-changes answered 500');
        post.mockRejectedValueOnce(failure);

        await expect(fetchFxPeriodChanges([{base: 'EUR', quote: 'USD'}], AS_OF)).rejects.toBe(failure);
    });
});
