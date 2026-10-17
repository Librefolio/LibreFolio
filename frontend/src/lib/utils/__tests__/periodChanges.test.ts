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
 *   - `fetchAssetPeriodChanges`, `fetchFxPeriodChanges`: through `zodiosApi.post`, every asset (pair) in the order given,
 *     up to `as_of`, and no call for an empty list. At most 1,000 items a call (lot X-R64: since MF's X-R59, aligned to
 *     Z-25, both endpoints refuse more than the backend's `MAX_BULK_ITEMS`, 1,000, with a 422 `bulk_too_many_items`): a
 *     longer list goes as consecutive calls in its order, each sent once the one before answered (Z-27's
 *     `sendBulkBatches`), and up to 1,000 items go as one call, as before. The answers merge as if one call had
 *     answered: the periods of the first item that has any, whichever call answered it; each item's changes in percent,
 *     a pair's in both orientations (`direct`, `inverse`) under `BASE/QUOTE`. A failed call rejects with its own error,
 *     for the page to handle: no partial answer, and no call after it;
 *   - `PeriodChangesLedger` (lot X-R60): which answer of those calls a list keeps when several are in flight and land in
 *     any order, whether the list is busy, and what a failed call leaves on screen.
 *
 * `$lib/api` is mocked: `post` answers what each case gives it, shaped as the generated client declares the answers
 * (`FAPeriodChangesResponse`, `FXPeriodChangesResponse`); past 1,000 items, a fake backend answers each call from its
 * own body, one item per asset (pair), as the real one does.
 *
 * Red today (X-R64): each function sends every item in one call, so the cases past 1,000 items see one call where they
 * expect two or three; the case of exactly 1,000 items is their guard, green today.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const post = vi.hoisted(() => vi.fn<(path: string, body: unknown) => Promise<unknown>>());
vi.mock('$lib/api', () => ({zodiosApi: {post}, ApiError: class ApiError extends Error {}, axiosInstance: {}}));

import {fetchAssetPeriodChanges, fetchFxPeriodChanges, PeriodChangesLedger, ratioToPercent, visiblePeriodColumns, type PeriodChangesTicket, type PeriodDeltas, type PeriodSpec} from '../periodChanges';

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

/** The body of the one call a list of up to 1,000 items makes, as it reaches the backend: through JSON, where a key holding `undefined` is not sent. */
function sentBody(): unknown {
    expect(post, 'one call: a list of up to 1,000 items, the backend’s MAX_BULK_ITEMS, goes whole').toHaveBeenCalledTimes(1);
    return JSON.parse(JSON.stringify(post.mock.calls[0][1]));
}

/** Each call made, in call order: its path and how many items it carried. */
function sentCalls(): Array<{path: string; items: number}> {
    return post.mock.calls.map(([path, body]) => ({path, items: (body as unknown[]).length}));
}

/** Every item sent, the calls joined in call order, as they reach the backend (through JSON). */
function sentItems(): unknown[] {
    return post.mock.calls.flatMap(([, body]) => JSON.parse(JSON.stringify(body)) as unknown[]);
}

/** How a call settled, without throwing: a case that expects a rejection still reads the calls made when it resolved instead. */
function settled<T>(promise: Promise<T>): Promise<PromiseSettledResult<Awaited<T>>> {
    return Promise.allSettled([promise]).then(([outcome]) => outcome);
}

/** A change of `percent` % as the backend writes it: a fraction, in a decimal string (`7` → `"0.07"`, `-1001` → `"-10.01"`). */
const ratioOf = (percent: number): string => (percent / 100).toFixed(2);

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
        await expect(fetchAssetPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByAssetId: new Map(), rangeDeltaByAssetId: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /assets/prices/period-changes answered 500');
        post.mockRejectedValueOnce(failure);

        await expect(fetchAssetPeriodChanges([7], AS_OF)).rejects.toBe(failure);
    });

    /**
     * Past 1,000 assets (lot X-R64). Since MF's X-R59, aligned to Z-25, the endpoint refuses more than the backend's
     * `MAX_BULK_ITEMS` (1,000) items with a 422 `bulk_too_many_items`, and the list sent every asset in one call: past
     * 1,000 assets it lost its Δ columns. The assets go in consecutive calls of at most 1,000, in the order given, each
     * sent once the one before answered (Z-27's `sendBulkBatches`, with no day estimate: the endpoint has no day budget),
     * and the answers merge as if one call had answered. The fake backend answers each call from its own body.
     *
     * Red today: one call carries every asset, where these cases expect two or three; exactly 1,000 assets, their guard,
     * is green.
     */
    describe('past 1,000 assets: consecutive calls of at most 1,000, answered as one (X-R64)', () => {
        /** `count` asset ids in a list's order, which is not theirs: `count` down to 1, so a call out of order, or a list sorted on the way, shows. */
        const assetIdsOf = (count: number): number[] => Array.from({length: count}, (_, index) => count - index);

        /** The items of `ids` as they must reach the backend: every asset up to the same as_of, nothing else. */
        const queryItems = (ids: readonly number[]) => ids.map((assetId) => ({asset_id: assetId, as_of: AS_OF}));

        /**
         * The backend answering a call from its own body, as the real one does: one item per asset, in the order sent.
         * Asset `n` moved `n` % over 1D, every other period without a price; an asset `hasPrices` turns down has no price
         * up to as_of, so no period at all.
         */
        function assetBackend(hasPrices: (assetId: number) => boolean = () => true) {
            return async (_path: string, body: unknown) => ({
                items: (body as Array<{asset_id: number}>).map(({asset_id: assetId}) => (hasPrices(assetId) ? assetItem(assetId, {'1D': ratioOf(assetId)}) : {asset_id: assetId, as_of: AS_OF, currency: null, periods: [], errors: []})),
            });
        }

        /** The assets whose 1D change is not their own, `n` % for asset `n`: missing from the result, or another's. */
        const misfiled = (ids: readonly number[], deltasByAssetId: ReadonlyMap<number, PeriodDeltas>): number[] => ids.filter((assetId) => deltasByAssetId.get(assetId)?.['1D'] !== assetId);

        it('sends 1,001 assets as two calls, 1,000 then 1, in the order given and up to the same as_of, and merges both answers', async () => {
            const ids = assetIdsOf(1_001);
            post.mockImplementation(assetBackend());

            const result = await fetchAssetPeriodChanges(ids, AS_OF);

            expect(sentCalls(), 'at most 1,000 assets a call: the backend refuses one more (422 bulk_too_many_items)').toEqual([
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 1},
            ]);
            expect(sentItems(), 'consecutive calls: every asset once, in the order given, each up to as_of').toStrictEqual(queryItems(ids));
            expect(result.periods).toEqual(PERIODS);
            expect(result.deltasByAssetId.size, 'the assets of both answers, and no other').toBe(1_001);
            expect(misfiled(ids, result.deltasByAssetId), 'each asset’s own change under its id, whichever call answered it').toEqual([]);
            expect(result.deltasByAssetId.get(ids[1_000]), 'the asset of the second call, keyed as those of the first').toEqual(deltas({'1D': ids[1_000]}));
        });

        it('takes the periods from the first item that has any, whichever call answered it: none in the first call, some in the second', async () => {
            // 2,001 assets, three calls; only the assets of the second have prices: the periods are in neither the first
            // answer nor the last.
            const ids = assetIdsOf(2_001);
            const priced = new Set(ids.slice(1_000, 2_000));
            post.mockImplementation(assetBackend((assetId) => priced.has(assetId)));

            const result = await fetchAssetPeriodChanges(ids, AS_OF);

            expect(sentCalls()).toEqual([
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 1},
            ]);
            expect(result.periods, 'the periods of the second call’s assets, the first that have any').toEqual(PERIODS);
            expect(result.deltasByAssetId.get(ids[0]), 'an asset of the first call: no price up to as_of, no change').toEqual({});
            expect(result.deltasByAssetId.get(ids[1_000])).toEqual(deltas({'1D': ids[1_000]}));
            expect(result.deltasByAssetId.get(ids[2_000]), 'the asset of the third call').toEqual({});
        });

        it('sends 2,500 assets as three calls: 1,000, 1,000 and 500', async () => {
            const ids = assetIdsOf(2_500);
            post.mockImplementation(assetBackend());

            const result = await fetchAssetPeriodChanges(ids, AS_OF);

            expect(sentCalls()).toEqual([
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 500},
            ]);
            expect(sentItems(), 'consecutive calls: every asset once, in the order given, each up to as_of').toStrictEqual(queryItems(ids));
            expect(result.deltasByAssetId.size).toBe(2_500);
            expect(misfiled(ids, result.deltasByAssetId)).toEqual([]);
        });

        it('sends exactly 1,000 assets as one call, as before (the guard: green today)', async () => {
            const ids = assetIdsOf(1_000);
            post.mockImplementation(assetBackend());

            const result = await fetchAssetPeriodChanges(ids, AS_OF);

            expect(sentBody(), 'the backend takes 1,000 items').toStrictEqual(queryItems(ids));
            expect(post.mock.calls[0][0]).toBe(ASSET_PATH);
            expect(misfiled(ids, result.deltasByAssetId)).toEqual([]);
        });

        it('rejects with the error of the call that failed and sends nothing after it: the call before it went, no partial answer', async () => {
            const ids = assetIdsOf(2_500);
            const failure = new Error('synthetic: the second POST /assets/prices/period-changes answered 500');
            // The first call answers, the second fails; a third, were it sent, would answer.
            post.mockImplementationOnce(assetBackend()).mockRejectedValueOnce(failure).mockImplementation(assetBackend());

            const outcome = await settled(fetchAssetPeriodChanges(ids, AS_OF));

            expect(sentCalls(), 'the first call answered, the second failed, the third never went').toEqual([
                {path: ASSET_PATH, items: 1_000},
                {path: ASSET_PATH, items: 1_000},
            ]);
            expect(outcome.status, 'no answer, not even the first call’s').toBe('rejected');
            expect((outcome as PromiseRejectedResult).reason, 'the failure of the second call, as it was raised').toBe(failure);
        });
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
        await expect(fetchFxPeriodChanges([], AS_OF)).resolves.toEqual({periods: [], deltasByPair: new Map(), rangeDeltasByPair: new Map()});
        expect(post, 'an empty list is answered without a call').not.toHaveBeenCalled();
    });

    it('rejects with the failure of the call, for the page to handle', async () => {
        const failure = new Error('synthetic: POST /fx/currencies/period-changes answered 500');
        post.mockRejectedValueOnce(failure);

        await expect(fetchFxPeriodChanges([{base: 'EUR', quote: 'USD'}], AS_OF)).rejects.toBe(failure);
    });

    /**
     * Past 1,000 pairs (lot X-R64), as for the assets: since X-R59 the endpoint refuses more than the
     * backend's `MAX_BULK_ITEMS` (1,000) pairs with a 422 `bulk_too_many_items`, and the list sent every pair in one
     * call. The pairs go in consecutive calls of at most 1,000, in the order given, each sent once the one before
     * answered, and the answers merge as one. The pairs are generated, each its own base against USD; the fake backend
     * answers each call from its own body.
     *
     * Red today: one call carries every pair, where these cases expect two or three; exactly 1,000 pairs, their guard,
     * is green.
     */
    describe('past 1,000 pairs: consecutive calls of at most 1,000, answered as one (X-R64)', () => {
        type Pair = {base: string; quote: string};

        /** The n-th of 17,576 three-letter codes, AAA, AAB, …: none is a real currency, and the list holds whatever pairs it is given. */
        function currencyCode(n: number): string {
            const letter = (k: number) => String.fromCharCode(65 + (k % 26));
            return letter(Math.floor(n / 676)) + letter(Math.floor(n / 26)) + letter(n);
        }

        /** `count` pairs in a list's order, each its own base against USD: the n-th is `currencyCode(n)/USD`. */
        const pairsOf = (count: number): Pair[] => Array.from({length: count}, (_, n) => ({base: currencyCode(n), quote: 'USD'}));

        /** A pair as the result keys it. */
        const keyOf = ({base, quote}: Pair): string => `${base}/${quote}`;

        /** The items of `pairs` as they must reach the backend: every pair up to the same as_of, its base and quote only. */
        const queryItems = (pairs: readonly Pair[]) => pairs.map(({base, quote}) => ({base, quote, as_of: AS_OF}));

        /** What the fake backend says a pair moved over 1D, in percent, read back from its base: n + 1 for the n-th pair. */
        const moveOf = (base: string): number => [...base].reduce((n, letter) => n * 26 + letter.charCodeAt(0) - 65, 0) + 1;

        /** The changes the fake backend gives a pair, as the module must give them: its move directly, the opposite inverted. */
        const changesOf = ({base}: Pair) => ({direct: deltas({'1D': moveOf(base)}), inverse: deltas({'1D': -moveOf(base)})});

        /**
         * The backend answering a call from its own body, as the real one does: one item per pair, in the order sent. The
         * n-th pair moved n + 1 % over 1D and −(n + 1) % inverted, every other period without a rate; a pair whose base
         * `hasRates` turns down has no rate up to as_of, so no period at all.
         */
        function fxBackend(hasRates: (base: string) => boolean = () => true) {
            return async (_path: string, body: unknown) => ({
                items: (body as Pair[]).map(({base, quote}) => (hasRates(base) ? fxItem(base, quote, {'1D': [ratioOf(moveOf(base)), ratioOf(-moveOf(base))]}) : {base, quote, as_of: AS_OF, periods: [], errors: ['no rate']})),
            });
        }

        /** The pairs whose 1D changes are not their own, either way: missing from the result, or another's. As `BASE/QUOTE`. */
        function misfiled(pairs: readonly Pair[], deltasByPair: ReadonlyMap<string, {direct: PeriodDeltas; inverse: PeriodDeltas}>): string[] {
            const wrong = pairs.filter((pair) => {
                const both = deltasByPair.get(keyOf(pair));
                return both?.direct['1D'] !== moveOf(pair.base) || both?.inverse['1D'] !== -moveOf(pair.base);
            });
            return wrong.map(keyOf);
        }

        it('sends 1,001 pairs as two calls, 1,000 then 1, in the order given and up to the same as_of, and merges both answers', async () => {
            const pairs = pairsOf(1_001);
            post.mockImplementation(fxBackend());

            const result = await fetchFxPeriodChanges(pairs, AS_OF);

            expect(sentCalls(), 'at most 1,000 pairs a call: the backend refuses one more (422 bulk_too_many_items)').toEqual([
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 1},
            ]);
            expect(sentItems(), 'consecutive calls: every pair once, in the order given, each up to as_of').toStrictEqual(queryItems(pairs));
            expect(result.periods).toEqual(PERIODS);
            expect(result.deltasByPair.size, 'the pairs of both answers, and no other').toBe(1_001);
            expect(misfiled(pairs, result.deltasByPair), 'each pair’s own changes under BASE/QUOTE, both ways, whichever call answered it').toEqual([]);
            expect(result.deltasByPair.get(keyOf(pairs[1_000])), 'the pair of the second call, keyed as those of the first').toEqual(changesOf(pairs[1_000]));
        });

        it('takes the periods from the first pair that has any, whichever call answered it: none in the first call, some in the second', async () => {
            // 2,001 pairs, three calls; only the pairs of the second have rates: the periods are in neither the first
            // answer nor the last.
            const pairs = pairsOf(2_001);
            const rated = new Set(pairs.slice(1_000, 2_000).map(({base}) => base));
            post.mockImplementation(fxBackend((base) => rated.has(base)));

            const result = await fetchFxPeriodChanges(pairs, AS_OF);

            expect(sentCalls()).toEqual([
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 1},
            ]);
            expect(result.periods, 'the periods of the second call’s pairs, the first that have any').toEqual(PERIODS);
            expect(result.deltasByPair.get(keyOf(pairs[0])), 'a pair of the first call: no rate up to as_of, no change either way').toEqual({direct: {}, inverse: {}});
            expect(result.deltasByPair.get(keyOf(pairs[1_000]))).toEqual(changesOf(pairs[1_000]));
            expect(result.deltasByPair.get(keyOf(pairs[2_000])), 'the pair of the third call').toEqual({direct: {}, inverse: {}});
        });

        it('sends 2,500 pairs as three calls: 1,000, 1,000 and 500', async () => {
            const pairs = pairsOf(2_500);
            post.mockImplementation(fxBackend());

            const result = await fetchFxPeriodChanges(pairs, AS_OF);

            expect(sentCalls()).toEqual([
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 500},
            ]);
            expect(sentItems(), 'consecutive calls: every pair once, in the order given, each up to as_of').toStrictEqual(queryItems(pairs));
            expect(result.deltasByPair.size).toBe(2_500);
            expect(misfiled(pairs, result.deltasByPair)).toEqual([]);
        });

        it('sends exactly 1,000 pairs as one call, as before (the guard: green today)', async () => {
            const pairs = pairsOf(1_000);
            post.mockImplementation(fxBackend());

            const result = await fetchFxPeriodChanges(pairs, AS_OF);

            expect(sentBody(), 'the backend takes 1,000 items').toStrictEqual(queryItems(pairs));
            expect(post.mock.calls[0][0]).toBe(FX_PATH);
            expect(misfiled(pairs, result.deltasByPair)).toEqual([]);
        });

        it('rejects with the error of the call that failed and sends nothing after it: the call before it went, no partial answer', async () => {
            const pairs = pairsOf(2_500);
            const failure = new Error('synthetic: the second POST /fx/currencies/period-changes answered 500');
            // The first call answers, the second fails; a third, were it sent, would answer.
            post.mockImplementationOnce(fxBackend()).mockRejectedValueOnce(failure).mockImplementation(fxBackend());

            const outcome = await settled(fetchFxPeriodChanges(pairs, AS_OF));

            expect(sentCalls(), 'the first call answered, the second failed, the third never went').toEqual([
                {path: FX_PATH, items: 1_000},
                {path: FX_PATH, items: 1_000},
            ]);
            expect(outcome.status, 'no answer, not even the first call’s').toBe('rejected');
            expect((outcome as PromiseRejectedResult).reason, 'the failure of the second call, as it was raised').toBe(failure);
        });
    });
});

/**
 * PeriodChangesLedger — which answer of the period changes a list keeps (workstream X, lot X-R60).
 *
 * A list asks its period changes in two shapes: every key it lists at once (`full`: the load, a reload, a new range) and,
 * on the FX list, one pair alone after its refresh or sync. Several can be in flight together and land in any order. The
 * pages tell the ledger when each request begins (`begin`) and when it is over (`end`, in a `finally`, answered or not),
 * and the ledger says what an answer (`settle`) or a failure (`fail`) leaves on screen — a new map, or null when nothing
 * is to change:
 *   1. a full request replaces every request begun before it;
 *   2. a one-key request begun after a full one is fresher for its keys than that full one, whichever lands first;
 *   3. a one-key request begun before a newer full one is moot;
 *   4. of two one-key requests for one key, the later-begun wins, whatever the landing order;
 *   5. a full answer drops the keys it lacks, unless a one-key answer begun after it wrote them;
 *   6. the list is busy while a request still kept is in flight, a one-key request alone included, a moot one not;
 *   7. a failed full request still kept keeps the values asked up to its own day and drops the others; a failed one-key
 *      request, or a failed full one already replaced, changes nothing;
 *   8. the map on screen is never written to: every map handed in here throws on a write;
 *   9. keys are asset ids on the Assets list (numbers), `BASE/QUOTE` on the FX list (strings).
 *
 * Every answer lands as the pages land it: `settle` or `fail`, then `end`. The values are labels naming the request
 * that gave them, so a failure reads which one was kept.
 *
 * `periodChanges.ts` exports `PeriodChangesLedger`, the class each list holds; every case builds a ledger of its own
 * with `new`, so none inherits the requests of another.
 */
describe('PeriodChangesLedger — the answer a list keeps, whatever order its requests land in (X-R60)', () => {
    /** The end of the range on screen: what each request asks up to, unless a case moves it. */
    const DAY = '2026-10-16';
    /** The end of the range the list showed before the user moved it. */
    const EARLIER_DAY = '2026-09-30';

    /** A map as a list shows it, handed to the ledger: any write to it throws, where it is made. */
    function onScreen<K, V>(entries: Iterable<readonly [K, V]> = []): ReadonlyMap<K, V> {
        const shown = new Map<K, V>(entries);
        for (const write of ['set', 'delete', 'clear'] as const) {
            Object.defineProperty(shown, write, {
                value: () => {
                    throw new Error(`the ledger wrote to the map on screen (${write}): it must return a new one`);
                },
            });
        }
        return shown;
    }

    /** An answer of the backend: each key's values. */
    function answer<K, V>(...entries: Array<[K, V]>): ReadonlyMap<K, V> {
        return new Map(entries);
    }

    /**
     * A request's answer landing as the pages land it — `settle`, then `end` in a `finally` — and what the list shows
     * after: the map the ledger returned, or what it showed already when the answer is not kept.
     */
    function land<K, V>(ledger: PeriodChangesLedger<K>, ticket: PeriodChangesTicket, shown: ReadonlyMap<K, V>, values: ReadonlyMap<K, V>): {kept: boolean; shown: ReadonlyMap<K, V>} {
        try {
            const next = ledger.settle(ticket, shown, values);
            return {kept: next !== null, shown: next === null ? shown : onScreen(next)};
        } finally {
            ledger.end(ticket);
        }
    }

    /** A request failing as the pages fail it — `fail`, then `end` in a `finally` — and what the list shows after. */
    function failed<K, V>(ledger: PeriodChangesLedger<K>, ticket: PeriodChangesTicket, shown: ReadonlyMap<K, V>): {changed: boolean; shown: ReadonlyMap<K, V>} {
        try {
            const next = ledger.fail(ticket, shown);
            return {changed: next !== null, shown: next === null ? shown : onScreen(next)};
        } finally {
            ledger.end(ticket);
        }
    }

    /** The list once it has loaded: one full request up to `asOf`, answered with `entries`. */
    function loaded<K, V>(ledger: PeriodChangesLedger<K>, asOf: string, ...entries: Array<[K, V]>): ReadonlyMap<K, V> {
        const step = land(ledger, ledger.begin(asOf, true), onScreen<K, V>(), answer(...entries));
        expect(step.kept, 'premise: the answer of a lone full request is kept').toBe(true);
        return step.shown;
    }

    it('shows the answer of a lone full request, whole', () => {
        const ledger = new PeriodChangesLedger<string>();

        const step = land(ledger, ledger.begin(DAY, true), onScreen<string, string>(), answer(['EUR/USD', 'load'], ['CHF/EUR', 'load']));

        expect(step.kept).toBe(true);
        expect(step.shown).toEqual(
            new Map([
                ['EUR/USD', 'load'],
                ['CHF/EUR', 'load'],
            ]),
        );
    });

    it('1 · a full request replaces the full ones begun before it: an older answer landing first is not kept', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load']);
        const older = ledger.begin(DAY, true);
        const newer = ledger.begin(DAY, true);

        // Landing order: the older reload, then the newer one.
        const first = land(ledger, older, shown, answer(['EUR/USD', 'older']));
        expect(first.kept, 'a newer full request began after it: the older answer is not kept').toBe(false);
        expect(first.shown).toEqual(new Map([['EUR/USD', 'load']]));
        const second = land(ledger, newer, first.shown, answer(['EUR/USD', 'newer']));

        expect(second.shown).toEqual(new Map([['EUR/USD', 'newer']]));
    });

    it('1 · … nor, landing after the newer answer, does it undo it', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load']);
        const older = ledger.begin(DAY, true);
        const newer = ledger.begin(DAY, true);

        // Landing order: the newer reload, then the older one.
        const first = land(ledger, newer, shown, answer(['EUR/USD', 'newer']));
        const second = land(ledger, older, first.shown, answer(['EUR/USD', 'older']));

        expect(second.kept, 'the older answer lands last, and is still not kept').toBe(false);
        expect(second.shown).toEqual(new Map([['EUR/USD', 'newer']]));
    });

    it('1 · a full request also replaces what a one-key request wrote before it began', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const refreshed = land(ledger, ledger.begin(DAY, false), shown, answer(['EUR/USD', 'refresh']));
        expect(refreshed.shown, 'premise: the refresh, begun after the load, is shown').toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'load'],
            ]),
        );

        const step = land(ledger, ledger.begin(DAY, true), refreshed.shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));

        expect(step.shown, 'the reload began after the refresh: it is the fresher for every pair').toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('2 · a one-key request begun after a full one is fresher for its key: the full answer, landing last, keeps it and applies the other keys', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const reload = ledger.begin(DAY, true);
        const refresh = ledger.begin(DAY, false);

        // Landing order: the pair's own refresh, then the reload of every pair.
        const first = land(ledger, refresh, shown, answer(['EUR/USD', 'refresh']));
        expect(first.shown, 'the refresh is shown as it lands').toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'load'],
            ]),
        );
        const second = land(ledger, reload, first.shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));

        expect(second.shown, 'EUR/USD keeps its refresh, CHF/EUR takes the reload').toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('2 · … and with the full answer landing first, the one-key answer landing after it is applied over it', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const reload = ledger.begin(DAY, true);
        const refresh = ledger.begin(DAY, false);

        // Landing order: the reload of every pair, then the pair's own refresh.
        const first = land(ledger, reload, shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));
        expect(first.shown).toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
            ]),
        );
        const second = land(ledger, refresh, first.shown, answer(['EUR/USD', 'refresh']));

        expect(second.kept, 'the refresh began after the reload: it is kept, though it lands last').toBe(true);
        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('3 · a one-key request begun before a newer full one is moot: its answer, landing first, is not kept', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const refresh = ledger.begin(DAY, false);
        const reload = ledger.begin(DAY, true);

        // Landing order: the refresh, then the reload begun after it.
        const first = land(ledger, refresh, shown, answer(['EUR/USD', 'refresh']));
        expect(first.kept, 'a reload of every pair began after the refresh: the refresh is moot').toBe(false);
        expect(first.shown).toEqual(
            new Map([
                ['EUR/USD', 'load'],
                ['CHF/EUR', 'load'],
            ]),
        );
        const second = land(ledger, reload, first.shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));

        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('3 · … nor landing last', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const refresh = ledger.begin(DAY, false);
        const reload = ledger.begin(DAY, true);

        // Landing order: the reload, then the refresh begun before it.
        const first = land(ledger, reload, shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));
        const second = land(ledger, refresh, first.shown, answer(['EUR/USD', 'refresh']));

        expect(second.kept, 'the refresh lands last, and is still moot').toBe(false);
        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('4 · of two one-key requests for one key, the later-begun wins, landing last', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const earlier = ledger.begin(DAY, false);
        const later = ledger.begin(DAY, false);

        // Landing order: the earlier refresh, then the later one.
        const first = land(ledger, earlier, shown, answer(['EUR/USD', 'earlier']));
        const second = land(ledger, later, first.shown, answer(['EUR/USD', 'later']));

        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', 'later'],
                ['CHF/EUR', 'load'],
            ]),
        );
    });

    it('4 · … and landing first', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const earlier = ledger.begin(DAY, false);
        const later = ledger.begin(DAY, false);

        // Landing order: the later refresh, then the earlier one.
        const first = land(ledger, later, shown, answer(['EUR/USD', 'later']));
        const second = land(ledger, earlier, first.shown, answer(['EUR/USD', 'earlier']));

        expect(second.shown, 'the earlier refresh lands last: it must not replace the later one').toEqual(
            new Map([
                ['EUR/USD', 'later'],
                ['CHF/EUR', 'load'],
            ]),
        );
    });

    it('4 · one-key requests for different keys are each kept, whatever their order', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const usd = ledger.begin(DAY, false);
        const chf = ledger.begin(DAY, false);

        // Landing order: the later-begun first.
        const first = land(ledger, chf, shown, answer(['CHF/EUR', 'refresh']));
        const second = land(ledger, usd, first.shown, answer(['EUR/USD', 'refresh']));

        expect(second.shown, 'each refresh is the fresher for its own pair').toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'refresh'],
            ]),
        );
    });

    it('5 · a full answer drops the keys it lacks', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load'], ['GBP/JPY', 'load']);

        const step = land(ledger, ledger.begin(DAY, true), shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));

        expect(step.shown, 'GBP/JPY is not in the reload: its figures go').toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
            ]),
        );
    });

    it('5 · … unless a one-key request begun after it wrote them', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load'], ['GBP/JPY', 'load']);
        const reload = ledger.begin(DAY, true);
        const refresh = ledger.begin(DAY, false);

        // Landing order: GBP/JPY's own refresh, then the reload that lacks it.
        const first = land(ledger, refresh, shown, answer(['GBP/JPY', 'refresh']));
        const second = land(ledger, reload, first.shown, answer(['EUR/USD', 'reload'], ['CHF/EUR', 'reload']));

        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', 'reload'],
                ['CHF/EUR', 'reload'],
                ['GBP/JPY', 'refresh'],
            ]),
        );
    });

    it('5 · … while a key a one-key request wrote before the full one began goes as well', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['GBP/JPY', 'load']);
        const refreshed = land(ledger, ledger.begin(DAY, false), shown, answer(['GBP/JPY', 'refresh']));

        const step = land(ledger, ledger.begin(DAY, true), refreshed.shown, answer(['EUR/USD', 'reload']));

        expect(step.shown, 'the refresh is older than the reload, which no longer lists GBP/JPY').toEqual(new Map([['EUR/USD', 'reload']]));
    });

    it('6 · busy while a request still kept is in flight — a one-key request alone included — and no longer once each has ended', () => {
        const ledger = new PeriodChangesLedger<string>();
        expect(ledger.busy, 'nothing asked yet').toBe(false);

        const refresh = ledger.begin(DAY, false);
        expect(ledger.busy, 'a pair’s own request alone holds the list busy').toBe(true);
        ledger.end(refresh);
        expect(ledger.busy).toBe(false);

        const reload = ledger.begin(DAY, true);
        expect(ledger.busy).toBe(true);
        const later = ledger.begin(DAY, false);
        ledger.end(reload);
        expect(ledger.busy, 'the reload is over; the refresh begun after it is still in flight').toBe(true);
        ledger.end(later);
        expect(ledger.busy, 'every request has ended').toBe(false);
    });

    it('6 · a moot request does not hold the list busy', () => {
        const ledger = new PeriodChangesLedger<string>();

        const refresh = ledger.begin(DAY, false);
        const reload = ledger.begin(DAY, true);
        ledger.end(reload);
        expect(ledger.busy, 'only the refresh is in flight, and a reload began after it: its answer would not be kept').toBe(false);
        ledger.end(refresh);
        expect(ledger.busy).toBe(false);

        const older = ledger.begin(DAY, true);
        const newer = ledger.begin(DAY, true);
        ledger.end(newer);
        expect(ledger.busy, 'only the replaced reload is in flight').toBe(false);
        ledger.end(older);
        expect(ledger.busy).toBe(false);
    });

    it('7 · a failed full request keeps the values asked up to its own day', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);

        const step = failed(ledger, ledger.begin(DAY, true), shown);

        expect(step.shown, 'a refresh of the same range failed: the figures of that day stay').toEqual(
            new Map([
                ['EUR/USD', 'load'],
                ['CHF/EUR', 'load'],
            ]),
        );
    });

    it('7 · … and drops those asked up to another day', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, EARLIER_DAY, ['EUR/USD', 'earlier'], ['CHF/EUR', 'earlier']);

        const step = failed(ledger, ledger.begin(DAY, true), shown);

        expect(step.changed, 'the range moved and its request failed: the figures of the earlier range must go').toBe(true);
        expect(step.shown).toEqual(new Map());
    });

    it('7 · … keeping a value a one-key request asked up to the new day', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, EARLIER_DAY, ['EUR/USD', 'earlier'], ['CHF/EUR', 'earlier']);
        const moved = ledger.begin(DAY, true);
        const refreshed = land(ledger, ledger.begin(DAY, false), shown, answer(['EUR/USD', 'refresh']));
        expect(refreshed.shown, 'premise: the refresh, begun after the move, is shown').toEqual(
            new Map([
                ['EUR/USD', 'refresh'],
                ['CHF/EUR', 'earlier'],
            ]),
        );

        const step = failed(ledger, moved, refreshed.shown);

        expect(step.shown, 'EUR/USD was asked up to the new day, CHF/EUR up to the earlier one').toEqual(new Map([['EUR/USD', 'refresh']]));
    });

    it('7 · a failed one-key request changes nothing', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, DAY, ['EUR/USD', 'load'], ['CHF/EUR', 'load']);
        const refresh = ledger.begin(DAY, false);

        try {
            expect(ledger.fail(refresh, shown), 'the pair keeps the figures it shows').toBeNull();
        } finally {
            ledger.end(refresh);
        }
    });

    it('7 · a failed full request a newer one replaced changes nothing', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded(ledger, EARLIER_DAY, ['EUR/USD', 'earlier']);
        const older = ledger.begin(EARLIER_DAY, true);
        ledger.begin(DAY, true);

        try {
            expect(ledger.fail(older, shown), 'the older request is moot: nothing to keep, nothing to drop').toBeNull();
        } finally {
            ledger.end(older);
        }
    });

    it('8 · settle and fail never write to the map on screen, nor to the values in it', () => {
        const ledger = new PeriodChangesLedger<string>();
        const shown = loaded<string, PeriodDeltas>(ledger, DAY, ['EUR/USD', {'1D': 1.25, '1W': -25}], ['CHF/EUR', {'1D': -6.25, '1W': null}]);
        const before = structuredClone([...shown]);
        const reload = ledger.begin(DAY, true);
        const refresh = ledger.begin(DAY, false);

        // Every call is handed the same map, one that throws on a write (`onScreen`).
        ledger.settle(refresh, shown, answer<string, PeriodDeltas>(['EUR/USD', {'1D': 2.5, '1W': 0}]));
        ledger.settle(reload, shown, answer<string, PeriodDeltas>(['EUR/USD', {'1D': 0, '1W': 0}], ['GBP/JPY', {'1D': 1, '1W': 1}]));
        ledger.fail(ledger.begin(DAY, true), shown);
        ledger.fail(ledger.begin(EARLIER_DAY, true), shown);
        ledger.fail(ledger.begin(DAY, false), shown);

        expect([...shown], 'the map on screen and its values are as they were').toEqual(before);
    });

    it('9 · keys may be asset ids: the Assets list', () => {
        const ledger = new PeriodChangesLedger<number>();
        const shown = loaded<number, PeriodDeltas>(ledger, DAY, [7, {'1D': 1.25}], [3, {'1D': -6.25}]);

        // The page's refresh over the same range fails: the figures of that day stay.
        const refreshed = failed(ledger, ledger.begin(DAY, true), shown);
        expect(refreshed.shown).toEqual(
            new Map([
                [7, {'1D': 1.25}],
                [3, {'1D': -6.25}],
            ]),
        );

        // Two reloads; the older one lands last.
        const older = ledger.begin(DAY, true);
        const newer = ledger.begin(DAY, true);
        const first = land(ledger, newer, refreshed.shown, answer<number, PeriodDeltas>([7, {'1D': 2.5}]));
        const second = land(ledger, older, first.shown, answer<number, PeriodDeltas>([7, {'1D': 0}], [3, {'1D': 0}]));

        expect(second.shown, 'asset 3 is not in the newer answer, and the older one, landing last, is not kept').toEqual(new Map([[7, {'1D': 2.5}]]));
    });

    it('9 · keys may be BASE/QUOTE: the FX list, each value both ways', () => {
        type BothWays = {direct: PeriodDeltas; inverse: PeriodDeltas};
        const ledger = new PeriodChangesLedger<string>();
        const fresh: BothWays = {direct: {'1D': 1.25}, inverse: {'1D': -4}};
        const stale: BothWays = {direct: {'1D': -50}, inverse: {'1D': 100}};
        const chf: BothWays = {direct: {'1D': 0.5}, inverse: {'1D': -0.5}};
        const shown = loaded<string, BothWays>(ledger, DAY, ['EUR/USD', {direct: {'1D': 0}, inverse: {'1D': 0}}], ['CHF/EUR', {direct: {'1D': 0}, inverse: {'1D': 0}}]);
        const reload = ledger.begin(DAY, true);
        const refresh = ledger.begin(DAY, false);

        // Landing order: EUR/USD's own refresh, then the reload of every pair.
        const first = land(ledger, refresh, shown, answer(['EUR/USD', fresh]));
        const second = land(ledger, reload, first.shown, answer(['EUR/USD', stale], ['CHF/EUR', chf]));

        expect(second.shown).toEqual(
            new Map([
                ['EUR/USD', fresh],
                ['CHF/EUR', chf],
            ]),
        );
    });
});
