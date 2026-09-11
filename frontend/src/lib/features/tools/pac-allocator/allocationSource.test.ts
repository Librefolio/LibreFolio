import {beforeEach, describe, expect, it, vi} from 'vitest';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {fetchPacAllocationSource} from './allocationSource';

const {reportMock} = vi.hoisted(() => ({
    reportMock: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_portfolio_report_api_v1_portfolio_report_post: reportMock,
    },
}));

vi.mock('$lib/features/tools/client', async () => {
    const {ToolClientError} = await import('$lib/features/tools/contracts');
    return {
        safeToolTransportError(error: unknown) {
            return error instanceof ToolClientError ? error : new ToolClientError('internal', 'unexpected_transport_error');
        },
    };
});

let accountSequence = 0;

beforeEach(() => {
    reportMock.mockReset();
    transitionClientSession(`pac-source-test-${++accountSequence}`);
});

describe('PAC allocation source', () => {
    it('requests only the allocation-source projection from the portfolio report API', async () => {
        reportMock.mockResolvedValueOnce({
            allocation_source: {
                generated_at: '2026-09-11T00:00:00Z',
                as_of_date: '2026-09-10',
                assets: [
                    {
                        asset_id: 17,
                        instrument_key: 'asset:17',
                        name: 'Fixture asset',
                        ticker: 'FIX',
                        asset_type: 'ETF',
                        icon_url: null,
                        quote: {
                            raw_price: '123.450000000001',
                            currency: 'USD',
                            quote_base_quantity: 100,
                            reference_date: '2026-09-09',
                            source: 'fixture',
                            days_before_requested: 1,
                        },
                        contexts: [
                            {
                                context_key: 'asset:17:broker:3',
                                broker_id: 3,
                                broker_name: 'Fixture broker',
                                ownership_share_percent: '25',
                                custody_quantity: '12.345678901234',
                            },
                        ],
                    },
                ],
            },
        });

        const source = await fetchPacAllocationSource('2026-09-10', getClientSessionGeneration());

        expect(reportMock).toHaveBeenCalledExactlyOnceWith(
            {
                include_summary: false,
                include_history: false,
                include_allocation_history: false,
                include_positions_contribution: false,
                include_breakdown: false,
                allocation_source: {as_of_date: '2026-09-10'},
            },
            {signal: expect.any(AbortSignal)},
        );
        expect(source).toEqual({
            generatedAt: '2026-09-11T00:00:00Z',
            asOfDate: '2026-09-10',
            assets: [
                {
                    assetId: 17,
                    instrumentKey: 'asset:17',
                    name: 'Fixture asset',
                    ticker: 'FIX',
                    assetType: 'ETF',
                    iconUrl: null,
                    quote: {
                        rawPrice: '123.450000000001',
                        currency: 'USD',
                        quoteBaseQuantity: 100,
                        referenceDate: '2026-09-09',
                        source: 'fixture',
                        daysBeforeRequested: 1,
                    },
                    contexts: [
                        {
                            contextKey: 'asset:17:broker:3',
                            brokerId: 3,
                            brokerName: 'Fixture broker',
                            ownershipSharePercent: '25',
                            custodyQuantity: '12.345678901234',
                        },
                    ],
                },
            ],
        });
    });

    it('fails closed when the source projection does not match its wire shape', async () => {
        reportMock.mockResolvedValueOnce({
            allocation_source: {
                generated_at: '2026-09-11T00:00:00Z',
                as_of_date: '2026-09-10',
                assets: [{asset_id: '17'}],
            },
        });

        await expect(fetchPacAllocationSource('2026-09-10', getClientSessionGeneration())).rejects.toMatchObject({
            kind: 'protocol',
            code: 'invalid_response',
        });
    });
});
