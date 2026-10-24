/**
 * Tests for the positions-series controller (Y5-2, #48): the request it builds, when it asks again, and which answer it keeps.
 */
import {get} from 'svelte/store';
import {describe, expect, it, vi} from 'vitest';
import {buildPositionsSeriesQuery, createPositionsSeriesController, positionsSeriesScopeKey, type PositionsSeriesScope} from './positionsSeriesController';
import type {PositionKey, PositionsSeriesResponse} from './positionsSeries';

vi.mock('$lib/api', () => ({zodiosApi: {get_positions_series_api_v1_portfolio_positions_series_post: vi.fn()}}));

const scope: PositionsSeriesScope = {brokerIds: [2, 1], start: '2026-01-01', end: '2026-06-30', currency: 'EUR', ready: true, version: 0};
const key = (asset_id: number, broker_id: number | null = null): PositionKey => ({asset_id, broker_id});
const answer = (currency = 'EUR'): PositionsSeriesResponse => ({currency, date_from: '2026-01-01', date_to: '2026-06-30', series: [], missing_fx_pairs: []});

function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

describe('buildPositionsSeriesQuery', () => {
    it('carries the report scope and the positions, a null broker for the asset summed over the brokers', () => {
        expect(buildPositionsSeriesQuery([key(7), key(8, 2)], scope)).toEqual({
            positions: [
                {asset_id: 7, broker_id: null},
                {asset_id: 8, broker_id: 2},
            ],
            broker_ids: [2, 1],
            date_range: {start: '2026-01-01', end: '2026-06-30'},
            target_currency: 'EUR',
        });
    });

    it('leaves out what the scope does not say: no brokers, no period, no currency', () => {
        expect(buildPositionsSeriesQuery([key(7)], {ready: true})).toEqual({positions: [{asset_id: 7, broker_id: null}]});
    });

    it('sends an open end of the period as the start alone', () => {
        expect(buildPositionsSeriesQuery([key(7)], {ready: true, start: 'min'}).date_range).toEqual({start: 'min'});
    });
});

describe('positionsSeriesScopeKey', () => {
    it('does not depend on the order of the brokers, and follows the version', () => {
        expect(positionsSeriesScopeKey({...scope, brokerIds: [1, 2]})).toBe(positionsSeriesScopeKey(scope));
        expect(positionsSeriesScopeKey({...scope, version: 1})).not.toBe(positionsSeriesScopeKey(scope));
    });
});

describe('createPositionsSeriesController', () => {
    it('asks for the ticked positions and keeps the answer', async () => {
        const fetcher = vi.fn().mockResolvedValue(answer());
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], scope);
        expect(get(controller).loading).toBe(true);
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
        expect(fetcher).toHaveBeenCalledTimes(1);
        expect(get(controller).response?.currency).toBe('EUR');
        expect(get(controller).failed).toBe(false);
    });

    it('does not ask while the page cannot ask yet', () => {
        const fetcher = vi.fn().mockResolvedValue(answer());
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], {...scope, ready: false});
        expect(fetcher).not.toHaveBeenCalled();
        expect(get(controller).loading).toBe(false);
    });

    it('does not ask again for a subset of what it already asked, nor twice while the first is in flight', async () => {
        const first = deferred<PositionsSeriesResponse>();
        const fetcher = vi.fn().mockReturnValueOnce(first.promise);
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7), key(8)], scope);
        controller.request([key(7), key(8)], scope);
        controller.request([key(8)], scope);
        controller.sync(scope);
        expect(fetcher).toHaveBeenCalledTimes(1);
        first.resolve(answer());
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
    });

    it('asks again, with the whole selection, when a position is added', async () => {
        const fetcher = vi.fn().mockResolvedValue(answer());
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], scope);
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
        controller.request([key(7), key(9)], scope);
        expect(fetcher).toHaveBeenCalledTimes(2);
        expect(fetcher.mock.calls[1][0].positions).toEqual([
            {asset_id: 7, broker_id: null},
            {asset_id: 9, broker_id: null},
        ]);
    });

    it('asks again for the same selection when the scope changes, and not before', async () => {
        const fetcher = vi.fn().mockResolvedValue(answer());
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], scope);
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
        controller.sync(scope);
        expect(fetcher).toHaveBeenCalledTimes(1);
        controller.sync({...scope, currency: 'USD'});
        expect(fetcher).toHaveBeenCalledTimes(2);
        expect(fetcher.mock.calls[1][0].target_currency).toBe('USD');
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
    });

    it('does nothing on a scope change when nothing is ticked', () => {
        const fetcher = vi.fn().mockResolvedValue(answer());
        const controller = createPositionsSeriesController(fetcher);
        controller.sync({...scope, currency: 'USD'});
        expect(fetcher).not.toHaveBeenCalled();
    });

    it('keeps the newest answer when an older one lands late', async () => {
        const older = deferred<PositionsSeriesResponse>();
        const newer = deferred<PositionsSeriesResponse>();
        const fetcher = vi.fn().mockReturnValueOnce(older.promise).mockReturnValueOnce(newer.promise);
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], scope);
        controller.request([key(7), key(8)], scope);
        newer.resolve(answer('USD'));
        await vi.waitFor(() => expect(get(controller).response?.currency).toBe('USD'));
        older.resolve(answer('GBP'));
        await Promise.resolve();
        await Promise.resolve();
        expect(get(controller).response?.currency).toBe('USD');
        expect(get(controller).loading).toBe(false);
    });

    it('flags a failure, keeps the last answer, and asks again with the next tick or scope change', async () => {
        const fetcher = vi.fn().mockResolvedValueOnce(answer('EUR')).mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(answer('USD'));
        const controller = createPositionsSeriesController(fetcher);
        controller.request([key(7)], scope);
        await vi.waitFor(() => expect(get(controller).loading).toBe(false));
        controller.request([key(7), key(8)], scope);
        await vi.waitFor(() => expect(get(controller).failed).toBe(true));
        expect(get(controller).loading).toBe(false);
        expect(get(controller).response?.currency).toBe('EUR');
        controller.sync(scope);
        expect(fetcher).toHaveBeenCalledTimes(3);
        await vi.waitFor(() => expect(get(controller).failed).toBe(false));
        expect(get(controller).response?.currency).toBe('USD');
    });

    it('drops an answer that lands after dispose', async () => {
        const late = deferred<PositionsSeriesResponse>();
        const controller = createPositionsSeriesController(vi.fn().mockReturnValue(late.promise));
        controller.request([key(7)], scope);
        controller.dispose();
        late.resolve(answer());
        await Promise.resolve();
        await Promise.resolve();
        expect(get(controller).response).toBeNull();
    });
});
