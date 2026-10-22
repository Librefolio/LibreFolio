/**
 * Unit tests for assetPriceStoreRegistry — ensureAssetPriceRangeLoaded helper.
 *
 * Tests the gap-detection + bulk fetch + merge + return flow.
 * zodiosApi is mocked so no real network calls are made.
 *
 * The last block (Z-14): the registry listens to the portfolio bus from its import, and a price
 * catch-up (`notifyPricesCaughtUp()`, `{kind: 'prices'}`) makes every cached range stale. It is driven
 * through the real bus, never through a helper exported for the test (N58).
 *
 * And the one before it (N64): the generation each store carries comes through the registry with no change of its own.
 * A cache of signal answers files an answer with the generations of the price stores it was drawn over, so the
 * registry's operations must move them exactly where the prices may have changed: `invalidateAssetPriceStore(id)` for
 * every currency of that asset and no other, the bus's `{kind: 'prices'}` for every store, and a store removed and made
 * again never keeps the number of the one it replaced.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

// vi.mock is hoisted by Vitest — the factory runs before any imports below
vi.mock('$lib/api', () => ({
    zodiosApi: {
        query_prices_bulk_api_v1_assets_prices_query_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {notifyPortfolioMutation, notifyPricesCaughtUp, requestPortfolioRefresh} from '$lib/stores/portfolio/portfolioMutation';
import {ensureAssetPriceRangeLoaded, getAssetPriceStore, invalidateAssetPriceStore, apiPricesToAssetPricePoints, removeAssetPriceStore} from '../assetPriceStoreRegistry';

const mockQuery = vi.mocked(zodiosApi.query_prices_bulk_api_v1_assets_prices_query_post);

/** Build a fake API response with price points */
function apiResp(assetId: number, ...dates: string[]) {
    return {
        items: [
            {
                asset_id: assetId,
                prices: dates.map((d) => ({
                    date: d,
                    close: '100.50',
                    open: '99.00',
                    high: '101.00',
                    low: '98.50',
                    volume: '1000',
                    currency: 'USD',
                    backward_fill_info: null,
                })),
                events: [],
                errors: [],
            },
        ],
    } as any;
}

beforeEach(() => {
    // Clear all stores between tests by invalidating known test assets
    invalidateAssetPriceStore(1);
    invalidateAssetPriceStore(2);
    mockQuery.mockReset();
});

describe('ensureAssetPriceRangeLoaded', () => {
    // =========================================================================
    // Test 1: Cache hit — no API call
    // =========================================================================
    it('returns cached data without calling the API when range is fully covered', async () => {
        const store = getAssetPriceStore(1, 'USD');
        store.merge(
            apiPricesToAssetPricePoints([
                {date: '2024-01-01', close: '100', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null},
                {date: '2024-01-02', close: '101', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null},
                {date: '2024-01-03', close: '102', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null},
            ]),
        );

        const result = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');

        expect(mockQuery).not.toHaveBeenCalled();
        expect(result).toHaveLength(3);
        expect(result[0].close).toBe(100);
        expect(result[2].close).toBe(102);
    });

    // =========================================================================
    // Test 2: Cache miss — fetches from API
    // =========================================================================
    it('calls the API when store is empty and merges results', async () => {
        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-01', '2024-01-02', '2024-01-03'));

        const result = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');

        expect(mockQuery).toHaveBeenCalledTimes(1);
        expect(result).toHaveLength(3);
        expect(result[0].close).toBe(100.5);
    });

    // =========================================================================
    // Test 3: Partial gap — fetches only the missing range
    // =========================================================================
    it('only fetches for gaps when store has partial data', async () => {
        const store = getAssetPriceStore(1, 'USD');
        store.merge(
            apiPricesToAssetPricePoints([
                {date: '2024-01-01', close: '100', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null},
                {date: '2024-01-02', close: '101', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null},
            ]),
        );
        // Mark 01-01 to 01-02 as fetched
        store.markFetched('2024-01-01', '2024-01-02');

        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-03', '2024-01-04', '2024-01-05'));

        const result = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-05');

        expect(mockQuery).toHaveBeenCalledTimes(1);
        // The call should request the full range since API doesn't support multi-range
        const callArgs = mockQuery.mock.calls[0][0] as any;
        expect(callArgs[0].date_range.start).toBe('2024-01-01');
        expect(callArgs[0].date_range.end).toBe('2024-01-05');
        // Result includes original + new
        expect(result).toHaveLength(5);
    });

    // =========================================================================
    // Test 4: Network error allows retry (not marked as fetched)
    // =========================================================================
    it('allows retry after network error', async () => {
        mockQuery.mockRejectedValueOnce(new Error('Network error'));

        await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');
        expect(mockQuery).toHaveBeenCalledTimes(1);

        // Second call should still try to fetch (not marked)
        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-01', '2024-01-02', '2024-01-03'));
        const result = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');

        expect(mockQuery).toHaveBeenCalledTimes(2);
        expect(result).toHaveLength(3);
    });

    // =========================================================================
    // Test 5: 404 marks as fetched (no retry loop)
    // =========================================================================
    it('marks range as fetched on 404 to prevent retry loop', async () => {
        const error404 = new Error('Not Found');
        (error404 as any).response = {status: 404};
        mockQuery.mockRejectedValueOnce(error404);

        await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');
        expect(mockQuery).toHaveBeenCalledTimes(1);

        // Second call should NOT re-fetch (marked as fetched)
        const result = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-03');
        expect(mockQuery).toHaveBeenCalledTimes(1); // No new call
        expect(result).toHaveLength(0);
    });

    // =========================================================================
    // Test 6: Different currencies use different stores
    // =========================================================================
    it('separates cache by currency', async () => {
        const storeUSD = getAssetPriceStore(1, 'USD');
        storeUSD.merge(apiPricesToAssetPricePoints([{date: '2024-01-01', close: '100', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null}]));
        storeUSD.markFetched('2024-01-01', '2024-01-01');

        // EUR store is empty — should trigger a fetch
        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-01'));

        await ensureAssetPriceRangeLoaded(1, 'EUR', '2024-01-01', '2024-01-01');
        expect(mockQuery).toHaveBeenCalledTimes(1);

        // USD store still has cached data — no fetch
        const usdResult = await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-01');
        expect(mockQuery).toHaveBeenCalledTimes(1); // Still 1 — no new call
        expect(usdResult).toHaveLength(1);
        expect(usdResult[0].close).toBe(100);
    });

    // =========================================================================
    // Test 7: invalidateAssetPriceStore clears ALL currencies
    // =========================================================================
    it('invalidateAssetPriceStore clears all currencies for an asset', async () => {
        const storeUSD = getAssetPriceStore(1, 'USD');
        const storeEUR = getAssetPriceStore(1, 'EUR');
        storeUSD.merge(apiPricesToAssetPricePoints([{date: '2024-01-01', close: '100', open: null, high: null, low: null, volume: null, currency: 'USD', backward_fill_info: null}]));
        storeEUR.merge(apiPricesToAssetPricePoints([{date: '2024-01-01', close: '92', open: null, high: null, low: null, volume: null, currency: 'EUR', backward_fill_info: null}]));
        storeUSD.markFetched('2024-01-01', '2024-01-01');
        storeEUR.markFetched('2024-01-01', '2024-01-01');

        invalidateAssetPriceStore(1);

        // Both stores should be empty now
        expect(storeUSD.size).toBe(0);
        expect(storeEUR.size).toBe(0);

        // Subsequent call should fetch
        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-01'));
        await ensureAssetPriceRangeLoaded(1, 'USD', '2024-01-01', '2024-01-01');
        expect(mockQuery).toHaveBeenCalledTimes(1);
    });

    // =========================================================================
    // Test 8: target_currency option is passed to API
    // =========================================================================
    it('passes targetCurrency option to the API', async () => {
        mockQuery.mockResolvedValueOnce(apiResp(1, '2024-01-01'));

        await ensureAssetPriceRangeLoaded(1, 'EUR', '2024-01-01', '2024-01-01', {targetCurrency: 'EUR'});

        const callArgs = mockQuery.mock.calls[0][0] as any;
        expect(callArgs[0].target_currency).toBe('EUR');
    });
});

describe('apiPricesToAssetPricePoints', () => {
    it('converts API response to AssetPricePoint format', () => {
        const points = apiPricesToAssetPricePoints([
            {
                date: '2024-01-01',
                close: '100.50',
                open: '99.00',
                high: '101.00',
                low: '98.50',
                volume: '5000',
                currency: 'USD',
                backward_fill_info: {days_back: 2},
            },
        ]);

        expect(points).toHaveLength(1);
        expect(points[0].date).toBe('2024-01-01');
        expect(points[0].close).toBe(100.5);
        expect(points[0].open).toBe(99);
        expect(points[0].high).toBe(101);
        expect(points[0].low).toBe(98.5);
        expect(points[0].volume).toBe(5000);
        expect(points[0].currency).toBe('USD');
        expect(points[0].backwardFillInfo).toEqual({daysBack: 2});
    });
});

// =============================================================================
//  A price catch-up makes every cached range stale (Z-14)
//
//  The answers fill backward the days without a price, so a loaded range holds
//  a point for every day and was never asked again in the session — not even
//  after the server caught up on prices (a cloud instance that woke up, say).
//  The registry listens to the portfolio bus from its import
//  (`registerPortfolioMutationListener('assetPriceStoreRegistry', …)`): on
//  `{kind: 'prices'}` — `notifyPricesCaughtUp()` — it marks every store stale,
//  every asset in every currency. The next `ensureAssetPriceRangeLoaded` of a
//  range loaded before asks it again, once, while the old points stay readable
//  until the answer lands. `{kind: 'mutation'}` — the live poll's
//  `POST /assets/prices/current` every 30 s, a commit — and `{kind: 'refresh'}`
//  («Aggiorna») change nothing.
//
//  The registry and the bus are module singletons: every case takes asset ids
//  of its own and removes their stores afterwards. Red first: until the
//  listener exists the signal reaches nobody, and the range comes from the
//  cache again.
// =============================================================================

describe('assetPriceStoreRegistry after a price catch-up (Z-14)', () => {
    const START = '2026-01-01';
    const END = '2026-01-05';
    const DAYS = ['2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05'] as const;
    let nextAssetId = 9_000;
    let owned: number[] = [];

    /** An asset id no other case uses; its stores are removed after the case. */
    function freshAssetId(): number {
        const assetId = ++nextAssetId;
        owned.push(assetId);
        return assetId;
    }

    afterEach(() => {
        for (const assetId of owned) removeAssetPriceStore(assetId);
        owned = [];
    });

    /** A `query_prices_bulk` answer with a price for every day — what the backward fill gives —, all closing at `close`. */
    function pricesAt(assetId: number, close: string, currency = 'USD') {
        return {
            items: [
                {
                    asset_id: assetId,
                    prices: DAYS.map((date) => ({date, close, open: null, high: null, low: null, volume: null, currency, backward_fill_info: null})),
                    events: [],
                    errors: [],
                },
            ],
        } as any;
    }

    /** A range loaded the way a page leaves it: a point for every day, the range marked fetched. */
    function loaded(assetId: number, currency: string, close = '100'): void {
        const store = getAssetPriceStore(assetId, currency);
        store.merge(apiPricesToAssetPricePoints(DAYS.map((date) => ({date, close, open: null, high: null, low: null, volume: null, currency, backward_fill_info: null}))));
        store.markFetched(START, END);
    }

    function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
        let resolve!: (value: T) => void;
        const promise = new Promise<T>((settle) => {
            resolve = settle;
        });
        return {promise, resolve};
    }

    it('asks a range loaded before the catch-up again, once, for the whole range — then serves it from the cache', async () => {
        const assetId = freshAssetId();
        mockQuery.mockResolvedValueOnce(pricesAt(assetId, '100.00'));
        await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        expect(mockQuery, 'premise: a loaded range is served from the cache').toHaveBeenCalledTimes(1);

        notifyPricesCaughtUp();
        expect(mockQuery, 'the mark must not ask anything by itself').toHaveBeenCalledTimes(1);

        mockQuery.mockResolvedValueOnce(pricesAt(assetId, '120.00'));
        const fresh = await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);

        expect(mockQuery, 'after a price catch-up the range loaded before came from the cache again: its backward-filled days hide what the server caught up on (Z-14)').toHaveBeenCalledTimes(2);
        const request = mockQuery.mock.calls[1][0] as any[];
        expect(request, 'one query for the whole range: query_prices_bulk takes one range per asset').toHaveLength(1);
        expect(request[0]).toMatchObject({asset_id: assetId, date_range: {start: START, end: END}});
        expect(
            fresh.map((point) => point.close),
            'the fresh prices replace the stale ones',
        ).toEqual([120, 120, 120, 120, 120]);

        await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        expect(mockQuery, 'the fresh answer marks the range fetched: one catch-up, one question').toHaveBeenCalledTimes(2);
    });

    it('keeps the stale points readable until the fresh answer lands', async () => {
        const assetId = freshAssetId();
        loaded(assetId, 'USD', '100');
        const store = getAssetPriceStore(assetId, 'USD');

        notifyPricesCaughtUp();
        expect(
            store.getRange(START, END).data.map((point) => point.close),
            'the catch-up emptied the store: a chart would blank out until the answer lands',
        ).toEqual([100, 100, 100, 100, 100]);

        const answer = deferred<unknown>();
        mockQuery.mockReturnValueOnce(answer.promise as any);
        const loading = ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        await vi.waitFor(() => expect(mockQuery, 'after a price catch-up the range loaded before was not asked again (Z-14)').toHaveBeenCalledTimes(1));
        expect(store.get('2026-01-03')?.close, 'while the answer is in flight a sync read still gets the old point').toBe(100);
        expect(store.getAllSorted()).toHaveLength(DAYS.length);

        answer.resolve(pricesAt(assetId, '120.00'));
        expect((await loading).map((point) => point.close)).toEqual([120, 120, 120, 120, 120]);
        expect(store.get('2026-01-03')?.close).toBe(120);
    });

    it('marks every store stale: two assets, each in its own currency and converted, are all asked again', async () => {
        const [first, second] = [freshAssetId(), freshAssetId()];
        const loads = [
            {assetId: first, currency: 'USD', opts: undefined},
            {assetId: first, currency: 'EUR', opts: {targetCurrency: 'EUR'}},
            {assetId: second, currency: 'USD', opts: undefined},
            {assetId: second, currency: 'EUR', opts: {targetCurrency: 'EUR'}},
        ];
        for (const {assetId, currency} of loads) loaded(assetId, currency);
        for (const {assetId, currency, opts} of loads) await ensureAssetPriceRangeLoaded(assetId, currency, START, END, opts);
        expect(mockQuery, 'premise: four loaded ranges, four cache hits').not.toHaveBeenCalled();

        notifyPricesCaughtUp();
        mockQuery.mockImplementation(async (body: any) => pricesAt(body[0].asset_id, '120.00', body[0].target_currency ?? 'USD'));
        for (const {assetId, currency, opts} of loads) await ensureAssetPriceRangeLoaded(assetId, currency, START, END, opts);

        const asked = mockQuery.mock.calls.map(([body]) => {
            const [item] = body as any[];
            return {asset_id: item.asset_id, target_currency: item.target_currency, date_range: item.date_range};
        });
        const everyLoad = loads.map(({assetId, opts}) => ({asset_id: assetId, target_currency: opts?.targetCurrency, date_range: {start: START, end: END}}));
        expect(asked, 'after a price catch-up a store was left fresh: every asset in every currency holds prices the server may have changed (Z-14)').toEqual(everyLoad);
    });

    it('changes nothing on a portfolio mutation or «Aggiorna»: the cache answers until a price catch-up', async () => {
        const assetId = freshAssetId();
        loaded(assetId, 'USD');

        // The live poll's write (every 30 s on a page that reaches today), a commit, and «Aggiorna».
        notifyPortfolioMutation('POST', '/api/v1/assets/prices/current', {results: [], success_count: 0, errors: []});
        notifyPortfolioMutation('POST', '/api/v1/transactions/commit');
        requestPortfolioRefresh();
        await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        expect(mockQuery, 'a portfolio mutation or «Aggiorna» made the price cache stale: the live poll alone would ask every chart again every 30 s').not.toHaveBeenCalled();

        // The control, in the same store: the catch-up does reach it, so the silence above is the listener's choice.
        notifyPricesCaughtUp();
        mockQuery.mockResolvedValueOnce(pricesAt(assetId, '120.00'));
        await ensureAssetPriceRangeLoaded(assetId, 'USD', START, END);
        expect(mockQuery, 'the control: a price catch-up did not make the range stale either, so the silence above proves nothing (Z-14)').toHaveBeenCalledTimes(1);
    });
});

// =============================================================================
//  The generation of a price store, through the registry (N64)
//
//  The registry adds no state of its own: a store's generation moves because
//  the store's own operations move it (`TimeSeriesStore.test.ts`). What is
//  pinned here is which stores the registry reaches with them.
//
//  - `invalidateAssetPriceStore(id)` reaches every currency store of that asset
//    — native and converted — and no other asset's, not even one whose id starts
//    with the same digits.
//  - `{kind: 'prices'}` on the portfolio bus (`notifyPricesCaughtUp()`) marks
//    every store stale, so it moves every generation; `{kind: 'mutation'}` (the
//    live poll, a commit) and `{kind: 'refresh'}` («Aggiorna») move none.
//  - `removeAssetPriceStore(id)` followed by `getAssetPriceStore(id, cur)` makes
//    a new store, and its generation is a number neither the removed store nor
//    its last change had: the answers cached for the old one cannot be taken for
//    the new one's.
//
//  `generation` is read by name, and every case asserts it is a number before
//  it compares: red first, for the right reason. The registry is a module
//  singleton: every case takes asset ids of its own and removes their stores
//  afterwards.
// =============================================================================

describe('assetPriceStoreRegistry generations (N64)', () => {
    const CURRENCIES = ['USD', 'EUR', 'GBP'] as const;
    let nextAssetId = 19_000;
    let owned: number[] = [];

    /** An asset id no other case uses; its stores are removed after the case. */
    function freshAssetId(): number {
        const assetId = ++nextAssetId;
        owned.push(assetId);
        return assetId;
    }

    afterEach(() => {
        for (const assetId of owned) removeAssetPriceStore(assetId);
        owned = [];
    });

    type PriceStore = ReturnType<typeof getAssetPriceStore>;

    /** `store.generation`, read by name (see above). */
    function generationOf(store: PriceStore): number {
        const generation = (store as unknown as {generation?: unknown}).generation;
        expect(typeof generation, 'TimeSeriesStore has no numeric generation: a cache of signal answers cannot tell whether the prices an answer was drawn over have changed (N64)').toBe('number');
        return generation as number;
    }

    /** The stores of an asset, one per currency: native and converted are cached apart. */
    function storesOf(assetId: number): PriceStore[] {
        return CURRENCIES.map((currency) => getAssetPriceStore(assetId, currency));
    }

    /** Asserts every store moved to a number nobody had — not its own before, not another store's — and no two share one. */
    function expectAllFresh(stores: readonly PriceStore[], before: readonly number[], also: readonly number[], what: string): void {
        const after = stores.map(generationOf);
        const taken = new Set([...before, ...also]);
        expect(
            after.map((generation) => taken.has(generation)),
            `${what} left a store with a generation it, or another store, already had: an answer drawn over its old prices would still be taken for current (N64)`,
        ).toEqual(after.map(() => false));
        expect(new Set(after).size, `${what} gave two stores the same new generation`).toBe(after.length);
    }

    it('invalidateAssetPriceStore changes the generation of every currency store of the asset, and of no other asset', () => {
        const target = freshAssetId();
        const neighbour = freshAssetId();
        const longer = Number(`${target}0`); // shares the digits of the target's id: «190010» is not «19001»
        owned.push(longer);
        const targetStores = storesOf(target);
        const otherStores = [...storesOf(neighbour), ...storesOf(longer)];
        const targetBefore = targetStores.map(generationOf);
        const otherBefore = otherStores.map(generationOf);

        invalidateAssetPriceStore(target);

        expectAllFresh(targetStores, targetBefore, otherBefore, 'invalidateAssetPriceStore(id)');
        expect(otherStores.map(generationOf), 'the invalidation of one asset moved the generation of another asset’s store: its cached answers would be asked again for nothing (N64)').toEqual(otherBefore);
    });

    it('invalidateAssetPriceStore of an asset with no store changes no generation', () => {
        const held = freshAssetId();
        const never = freshAssetId();
        const stores = storesOf(held);
        const before = stores.map(generationOf);

        invalidateAssetPriceStore(never);

        expect(stores.map(generationOf)).toEqual(before);
    });

    it('a price catch-up on the bus ({kind: prices}) changes the generation of every store, every asset in every currency', () => {
        const assetIds = [freshAssetId(), freshAssetId()];
        const stores = assetIds.flatMap(storesOf);
        const before = stores.map(generationOf);

        notifyPricesCaughtUp();

        expectAllFresh(stores, before, [], 'a price catch-up');
    });

    it('a portfolio mutation and «Aggiorna» change no generation — a price catch-up, the control, changes them all', () => {
        const stores = [...storesOf(freshAssetId()), ...storesOf(freshAssetId())];
        const before = stores.map(generationOf);

        // The live poll's write (every 30 s on a page that reaches today), a commit, and «Aggiorna».
        notifyPortfolioMutation('POST', '/api/v1/assets/prices/current', {results: [], success_count: 0, errors: []});
        expect(stores.map(generationOf), 'the live poll’s write moved the generations: every cached signal answer would be asked again every 30 s (N64)').toEqual(before);
        notifyPortfolioMutation('POST', '/api/v1/transactions/commit');
        expect(stores.map(generationOf), 'a commit moved the generations').toEqual(before);
        requestPortfolioRefresh();
        expect(stores.map(generationOf), '«Aggiorna» moved the generations').toEqual(before);

        // The control, on the same stores: the catch-up does reach them, so the silence above is the listener's choice.
        notifyPricesCaughtUp();
        expectAllFresh(stores, before, [], 'the control: a price catch-up');
    });

    it('removeAssetPriceStore then getAssetPriceStore gives a store whose generation is neither the removed one’s nor the one its removal left', () => {
        const assetId = freshAssetId();
        const removed = storesOf(assetId);
        const before = removed.map(generationOf);

        removeAssetPriceStore(assetId);
        const afterRemoval = removed.map(generationOf); // whatever the removal did to them: a number the new stores must not take
        const reborn = storesOf(assetId);

        expect(
            reborn.map((store, index) => store === removed[index]),
            'premise: the registry made a new store, not the removed one again',
        ).toEqual(reborn.map(() => false));
        expectAllFresh(reborn, before, afterRemoval, 'removeAssetPriceStore(id) then getAssetPriceStore(id, currency)');
    });

    it('asking the registry for a store again returns the same store with the same generation', () => {
        const assetId = freshAssetId();
        const store = getAssetPriceStore(assetId, 'USD');
        const generation = generationOf(store);

        const again = getAssetPriceStore(assetId, 'usd');

        expect(again, 'premise: one store per asset and currency, whatever the case of the code').toBe(store);
        expect(generationOf(again), 'a read of the registry moved a generation').toBe(generation);
    });
});
