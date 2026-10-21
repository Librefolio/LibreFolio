import {describe, expect, it} from 'vitest';

import {processPriceRequest} from '../priceProcessing.worker';

describe('price processing worker signal preservation', () => {
    it('preserves validated signal results when prices are omitted', () => {
        const response = processPriceRequest({
            items: [
                {
                    asset_id: 42,
                    signals: [
                        {
                            instance_id: 'ema-1',
                            signal_code: 'EMA',
                            status: 'unavailable',
                        },
                    ],
                },
            ],
        });

        expect(response.invalidItemErrors).toEqual([]);
        expect(response.results).toMatchObject([
            {
                assetId: 42,
                mappedPoints: [],
                signals: [
                    {
                        instance_id: 'ema-1',
                        signal_code: 'EMA',
                        status: 'unavailable',
                    },
                ],
            },
        ]);
    });

    it('surfaces invalid signal payloads instead of dropping them', () => {
        const response = processPriceRequest({
            items: [
                {
                    asset_id: 42,
                    signals: [
                        {
                            instance_id: 'ema-1',
                            signal_code: 'EMA',
                            status: 'not-a-status',
                        },
                    ],
                },
            ],
        });

        expect(response.results).toEqual([]);
        expect(response.invalidItemErrors).toHaveLength(1);
    });
});

/** A price point as the backend writes it (`FAPricePoint`): a stored row has no `backward_fill_info`. */
const point = (date: string, close: string, backFill?: {daysBack: number; rowDate: string}) => ({date, close, ...(backFill === undefined ? {} : {backward_fill_info: {days_back: backFill.daysBack, actual_rate_date: backFill.rowDate}})});

describe('price processing worker: the position, the step and the base of a sampled item (Z-29b)', () => {
    it('says the position of each result in the request, whatever an invalid item before it', () => {
        const response = processPriceRequest({
            items: [
                {asset_id: 7, prices: [point('2026-01-05', '1')]},
                {asset_id: 8, signals: [{instance_id: 'ema-1', signal_code: 'EMA', status: 'not-a-status'}]},
                {asset_id: 7, prices: [point('2026-01-05', '2')]},
            ],
        });

        expect(response.results.map((result) => [result.requestIndex, result.assetId])).toEqual([
            [0, 7],
            [2, 7],
        ]);
    });

    it('carries the step of the item: daily when the backend does not say it', () => {
        const response = processPriceRequest({
            items: [
                {asset_id: 1, prices: [point('2026-01-05', '1')]},
                {asset_id: 2, resolution: 'weekly', prices: [point('2026-01-11', '5')], sample_bounds: {first: point('2026-01-05', '4'), last: point('2026-01-11', '5')}},
            ],
        });

        expect(response.results.map((result) => result.resolution)).toEqual(['daily', 'weekly']);
    });

    it('reads the base from sample_bounds.first, the fill’s point on its first day, not from the first bucket’s point', () => {
        const response = processPriceRequest({
            items: [
                {
                    asset_id: 2,
                    resolution: 'weekly',
                    prices: [point('2026-01-11', '5'), point('2026-01-18', '6')],
                    sample_bounds: {first: point('2026-01-07', '4', {daysBack: 2, rowDate: '2026-01-05'}), last: point('2026-01-18', '6')},
                },
            ],
        });

        const [result] = response.results;
        expect(result.derived.base).toEqual({date: '2026-01-07', value: 4});
        expect(result.derived.chartData.map((p) => p.value)).toEqual([5, 6]);
        expect(result.derived.lastPrice).toBe(6);
    });
});
