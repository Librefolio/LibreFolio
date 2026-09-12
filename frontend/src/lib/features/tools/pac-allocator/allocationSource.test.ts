import {beforeEach, describe, expect, it, vi} from 'vitest';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {fetchPacAllocationSource} from './allocationSource';

const {reportMock, safeToolTransportErrorMock} = vi.hoisted(() => ({
    reportMock: vi.fn(),
    safeToolTransportErrorMock: vi.fn(),
}));

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_portfolio_report_api_v1_portfolio_report_post: reportMock,
    },
}));

vi.mock('$lib/features/tools/client', async () => {
    const {ToolClientError} = await import('$lib/features/tools/contracts');
    safeToolTransportErrorMock.mockImplementation((error: unknown) => (error instanceof ToolClientError ? error : new ToolClientError('internal', 'unexpected_transport_error')));
    return {
        safeToolTransportError: safeToolTransportErrorMock,
    };
});

let accountSequence = 0;

function quoteWire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        raw_price: '123.450000000001',
        currency: 'USD',
        quote_base_quantity: 100,
        reference_date: '2026-09-09',
        source: 'fixture',
        days_before_requested: 1,
        ...overrides,
    };
}

function contextWire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        context_key: 'asset:17:broker:3',
        broker_id: 3,
        broker_name: 'Owner broker',
        broker_icon_url: '/api/v1/brokers/3/icon',
        broker_portal_url: 'https://broker.example/portfolio',
        broker_default_import_plugin: 'fixture_csv',
        ownership_share_percent: '100.000000000000',
        custody_quantity: '12.345678901234',
        ...overrides,
    };
}

function assetWire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        asset_id: 17,
        instrument_key: 'asset:17',
        candidate_key: 'candidate:asset:17',
        name: 'Fixture asset',
        ticker: 'FIX',
        asset_type: 'ETF',
        icon_url: null,
        active: true,
        usage_scope: 'owned',
        quote: quoteWire(),
        contexts: [contextWire()],
        ...overrides,
    };
}

function cashSourceWire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        broker_id: 3,
        broker_name: 'Owner broker',
        broker_icon_url: '/api/v1/brokers/3/icon',
        broker_portal_url: 'https://broker.example/portfolio',
        broker_default_import_plugin: 'fixture_csv',
        ownership_share_percent: '100.000000000000',
        balances: [
            {currency: 'USD', amount: '9876543210.123456789012'},
            {currency: 'EUR', amount: '-0.000000000001'},
        ],
        ...overrides,
    };
}

function allocationSourceWire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
    return {
        generated_at: '2026-09-11T00:00:00Z',
        as_of_date: '2026-09-10',
        assets: [assetWire()],
        cash_sources: [cashSourceWire()],
        selected_cash_balances: [
            {currency: 'USD', amount: '333.333333333333'},
            {currency: 'EUR', amount: '0.000000000009'},
        ],
        ...overrides,
    };
}

beforeEach(() => {
    reportMock.mockReset();
    safeToolTransportErrorMock.mockClear();
    transitionClientSession(`pac-source-test-${++accountSequence}`);
});

describe('PAC allocation source', () => {
    it('requests the selected cash brokers and normalizes the complete allocation source', async () => {
        reportMock.mockResolvedValueOnce({
            allocation_source: allocationSourceWire(),
        });

        const source = await fetchPacAllocationSource('2026-09-10', getClientSessionGeneration(), {
            selectedCashBrokerIds: [3],
        });

        expect(reportMock).toHaveBeenCalledExactlyOnceWith(
            {
                include_summary: false,
                include_history: false,
                include_allocation_history: false,
                include_positions_contribution: false,
                include_breakdown: false,
                allocation_source: {
                    as_of_date: '2026-09-10',
                    selected_cash_broker_ids: [3],
                },
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
                    candidateKey: 'candidate:asset:17',
                    name: 'Fixture asset',
                    ticker: 'FIX',
                    assetType: 'ETF',
                    iconUrl: null,
                    active: true,
                    usageScope: 'owned',
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
                            brokerName: 'Owner broker',
                            brokerIconUrl: '/api/v1/brokers/3/icon',
                            brokerPortalUrl: 'https://broker.example/portfolio',
                            brokerDefaultImportPlugin: 'fixture_csv',
                            ownershipSharePercent: '100.000000000000',
                            custodyQuantity: '12.345678901234',
                        },
                    ],
                },
            ],
            cashSources: [
                {
                    brokerId: 3,
                    brokerName: 'Owner broker',
                    brokerIconUrl: '/api/v1/brokers/3/icon',
                    brokerPortalUrl: 'https://broker.example/portfolio',
                    brokerDefaultImportPlugin: 'fixture_csv',
                    ownershipSharePercent: '100.000000000000',
                    balances: [
                        {currency: 'USD', amount: '9876543210.123456789012'},
                        {currency: 'EUR', amount: '-0.000000000001'},
                    ],
                },
            ],
            selectedCashBalances: [
                {currency: 'USD', amount: '333.333333333333'},
                {currency: 'EUR', amount: '0.000000000009'},
            ],
        });
    });

    it('sends an explicit empty cash-broker selection and defaults omitted top-level arrays', async () => {
        reportMock.mockResolvedValueOnce({
            allocation_source: {
                generated_at: '2026-09-11T00:00:00Z',
                as_of_date: '2026-09-10',
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
                allocation_source: {
                    as_of_date: '2026-09-10',
                    selected_cash_broker_ids: [],
                },
            },
            {signal: expect.any(AbortSignal)},
        );
        expect(source).toEqual({
            generatedAt: '2026-09-11T00:00:00Z',
            asOfDate: '2026-09-10',
            assets: [],
            cashSources: [],
            selectedCashBalances: [],
        });
    });

    it('defaults omitted nested arrays and optional broker metadata', async () => {
        reportMock.mockResolvedValueOnce({
            allocation_source: {
                generated_at: '2026-09-11T00:00:00Z',
                as_of_date: '2026-09-10',
                assets: [
                    {
                        asset_id: 29,
                        instrument_key: 'asset:29',
                        candidate_key: 'candidate:asset:29',
                        name: 'Observed asset',
                        asset_type: 'FUND',
                        active: false,
                        usage_scope: 'observed',
                        quote: {
                            currency: 'EUR',
                            quote_base_quantity: 1,
                        },
                    },
                ],
                cash_sources: [
                    {
                        broker_id: 4,
                        broker_name: 'Metadata-free owner broker',
                        ownership_share_percent: '50',
                    },
                ],
            },
        });

        const source = await fetchPacAllocationSource('2026-09-10', getClientSessionGeneration());

        expect(source).toEqual({
            generatedAt: '2026-09-11T00:00:00Z',
            asOfDate: '2026-09-10',
            assets: [
                {
                    assetId: 29,
                    instrumentKey: 'asset:29',
                    candidateKey: 'candidate:asset:29',
                    name: 'Observed asset',
                    ticker: null,
                    assetType: 'FUND',
                    iconUrl: null,
                    active: false,
                    usageScope: 'observed',
                    quote: {
                        rawPrice: null,
                        currency: 'EUR',
                        quoteBaseQuantity: 1,
                        referenceDate: null,
                        source: null,
                        daysBeforeRequested: null,
                    },
                    contexts: [],
                },
            ],
            cashSources: [
                {
                    brokerId: 4,
                    brokerName: 'Metadata-free owner broker',
                    brokerIconUrl: null,
                    brokerPortalUrl: null,
                    brokerDefaultImportPlugin: null,
                    ownershipSharePercent: '50',
                    balances: [],
                },
            ],
            selectedCashBalances: [],
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

    const malformedRequiredFieldCases: ReadonlyArray<{
        name: string;
        source: () => Record<string, unknown>;
    }> = [
        {
            name: 'asset candidate_key',
            source: () => allocationSourceWire({assets: [assetWire({candidate_key: undefined})]}),
        },
        {
            name: 'asset active flag',
            source: () => allocationSourceWire({assets: [assetWire({active: 'true'})]}),
        },
        {
            name: 'asset usage_scope',
            source: () => allocationSourceWire({assets: [assetWire({usage_scope: 'shared'})]}),
        },
        {
            name: 'context ownership_share_percent',
            source: () =>
                allocationSourceWire({
                    assets: [assetWire({contexts: [contextWire({ownership_share_percent: undefined})]})],
                }),
        },
        {
            name: 'cash-source ownership_share_percent',
            source: () =>
                allocationSourceWire({
                    cash_sources: [cashSourceWire({ownership_share_percent: 100})],
                }),
        },
        {
            name: 'native cash balance amount',
            source: () =>
                allocationSourceWire({
                    cash_sources: [
                        cashSourceWire({
                            balances: [{currency: 'USD', amount: 12.5}],
                        }),
                    ],
                }),
        },
        {
            name: 'selected cash balance amount',
            source: () =>
                allocationSourceWire({
                    selected_cash_balances: [{currency: 'USD', amount: 12.5}],
                }),
        },
    ];

    it.each(malformedRequiredFieldCases)('rejects malformed $name as a protocol error', async ({source}) => {
        reportMock.mockResolvedValueOnce({allocation_source: source()});

        await expect(fetchPacAllocationSource('2026-09-10', getClientSessionGeneration())).rejects.toMatchObject({
            kind: 'protocol',
            code: 'invalid_response',
        });
    });

    it('rejects a response made stale by an account-generation transition', async () => {
        let resolveReport!: (value: unknown) => void;
        reportMock.mockReturnValueOnce(
            new Promise<unknown>((resolve) => {
                resolveReport = resolve;
            }),
        );
        const accountGeneration = getClientSessionGeneration();
        const request = fetchPacAllocationSource('2026-09-10', accountGeneration);

        await vi.waitFor(() => expect(reportMock).toHaveBeenCalledTimes(1));
        const requestSignal = reportMock.mock.calls[0]?.[1]?.signal as AbortSignal;
        expect(requestSignal).toBeInstanceOf(AbortSignal);
        expect(requestSignal.aborted).toBe(false);
        transitionClientSession(`pac-source-stale-${++accountSequence}`);
        expect(requestSignal.aborted).toBe(true);
        resolveReport({allocation_source: allocationSourceWire()});

        await expect(request).rejects.toMatchObject({kind: 'session', code: 'session_changed'});
    });

    it('passes the account generation to transport-error normalization', async () => {
        const transportFailure = new TypeError('network unavailable');
        const accountGeneration = getClientSessionGeneration();
        reportMock.mockRejectedValueOnce(transportFailure);

        await expect(fetchPacAllocationSource('2026-09-10', accountGeneration)).rejects.toMatchObject({
            kind: 'internal',
            code: 'unexpected_transport_error',
        });
        expect(safeToolTransportErrorMock).toHaveBeenCalledExactlyOnceWith(transportFailure, accountGeneration);
    });

    it('connects caller cancellation to the request AbortSignal', async () => {
        const controller = new AbortController();
        reportMock.mockReturnValueOnce(new Promise<never>(() => {}));

        const request = fetchPacAllocationSource('2026-09-10', getClientSessionGeneration(), {
            signal: controller.signal,
        });

        await vi.waitFor(() => expect(reportMock).toHaveBeenCalledTimes(1));
        const requestSignal = reportMock.mock.calls[0]?.[1]?.signal as AbortSignal;
        expect(requestSignal).toBeInstanceOf(AbortSignal);
        expect(requestSignal).not.toBe(controller.signal);
        expect(requestSignal.aborted).toBe(false);
        controller.abort(new Error('cancelled by test'));
        expect(requestSignal.aborted).toBe(true);
        await expect(request).rejects.toMatchObject({kind: 'aborted', code: 'waiting_stopped'});
    });
});
