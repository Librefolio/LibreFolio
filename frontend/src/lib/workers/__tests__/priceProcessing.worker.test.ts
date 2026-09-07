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
