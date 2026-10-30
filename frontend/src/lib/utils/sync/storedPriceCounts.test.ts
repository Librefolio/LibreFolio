/**
 * storedPriceCounts — unit tests (Vitest, node). Lot «avviso di SyncModalBase» (X-R29 follow-up).
 *
 * The sync dialogs warn before they replace stored prices, and count them from the server: `POST /assets/prices/stored-count`
 * answers, per asset, how many prices are stored in the range a sync would ask for and how many of them were entered by hand.
 *
 * Contract (`loadStoredPriceCounts(assetIds, range)`):
 * - one request per 1 000 assets at most (the endpoint's cap), the items `{asset_id, date_range: {start, end}}`, the range as
 *   given (a start may be `'min'`); no asset, no request;
 * - the answer is a map by asset id: `{stored, manual}`; an asset the answer leaves out is absent;
 * - a request that fails rejects: the caller decides what the dialog shows without a count.
 *
 * Red first: the module does not exist.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({count: vi.fn()}));
vi.mock('$lib/api', () => ({zodiosApi: {count_stored_prices_api_v1_assets_prices_stored_count_post: mocks.count}}));

import {loadStoredPriceCounts} from './storedPriceCounts';

beforeEach(() => {
    mocks.count.mockReset();
});

describe('loadStoredPriceCounts', () => {
    it('asks once for a few assets, with the range as given, and maps the answer by asset id', async () => {
        mocks.count.mockResolvedValue({
            items: [
                {asset_id: 1, stored_count: 3, manual_count: 2},
                {asset_id: 2, stored_count: 0, manual_count: 0},
            ],
        });

        const counts = await loadStoredPriceCounts([1, 2], {start: 'min', end: '2024-03-31'});

        expect(mocks.count).toHaveBeenCalledTimes(1);
        expect(mocks.count).toHaveBeenCalledWith([
            {asset_id: 1, date_range: {start: 'min', end: '2024-03-31'}},
            {asset_id: 2, date_range: {start: 'min', end: '2024-03-31'}},
        ]);
        expect(counts.get(1)).toEqual({stored: 3, manual: 2});
        expect(counts.get(2)).toEqual({stored: 0, manual: 0});
    });

    it('splits more than 1 000 assets into requests of 1 000 at most and joins their answers', async () => {
        const ids = Array.from({length: 1001}, (_, n) => n + 1);
        mocks.count.mockImplementation(async (items: Array<{asset_id: number}>) => ({items: items.map((item) => ({asset_id: item.asset_id, stored_count: 1, manual_count: 0}))}));

        const counts = await loadStoredPriceCounts(ids, {start: '2024-01-01', end: '2024-01-31'});

        expect(mocks.count).toHaveBeenCalledTimes(2);
        expect((mocks.count.mock.calls[0][0] as unknown[]).length).toBe(1000);
        expect((mocks.count.mock.calls[1][0] as unknown[]).length).toBe(1);
        expect(counts.size).toBe(1001);
    });

    it('asks nothing for no asset', async () => {
        const counts = await loadStoredPriceCounts([], {start: '2024-01-01', end: '2024-01-31'});

        expect(mocks.count).not.toHaveBeenCalled();
        expect(counts.size).toBe(0);
    });

    it('leaves out an asset the answer does not name, and asks an asset once however many times it is listed', async () => {
        mocks.count.mockResolvedValue({items: [{asset_id: 1, stored_count: 2, manual_count: 1}]});

        const counts = await loadStoredPriceCounts([1, 2, 1], {start: '2024-01-01', end: '2024-01-31'});

        expect([...counts.keys()]).toEqual([1]);
        expect((mocks.count.mock.calls[0][0] as unknown[]).length).toBe(2);
    });

    it('rejects when the request fails', async () => {
        mocks.count.mockRejectedValue(new Error('boom'));

        await expect(loadStoredPriceCounts([1], {start: '2024-01-01', end: '2024-01-31'})).rejects.toThrow('boom');
    });
});
