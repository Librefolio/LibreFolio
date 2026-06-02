/**
 * Unit tests for assetPriceStoreRegistry — ensureAssetPriceRangeLoaded helper.
 *
 * Tests the gap-detection + bulk fetch + merge + return flow.
 * zodiosApi is mocked so no real network calls are made.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

// vi.mock is hoisted by Vitest — the factory runs before any imports below
vi.mock('$lib/api', () => ({
    zodiosApi: {
        query_prices_bulk_api_v1_assets_prices_query_post: vi.fn(),
    },
}));

import {zodiosApi} from '$lib/api';
import {ensureAssetPriceRangeLoaded, getAssetPriceStore, invalidateAssetPriceStore, apiPricesToAssetPricePoints} from '../assetPriceStoreRegistry';

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
