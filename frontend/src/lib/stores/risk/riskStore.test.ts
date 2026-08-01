import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const catalogApi = vi.hoisted(() => vi.fn());
const queryApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {
        ...actual,
        zodiosApi: {
            ...actual.zodiosApi,
            get_risk_catalog_api_v1_risk_catalog_get: catalogApi,
            query_risk_api_v1_risk_query_post: queryApi,
        },
    };
});

import {buildHistoricalReplayParameters, buildRiskQueryRequest, buildSimulationParameters} from '$lib/risk/riskRequest';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {notifyPortfolioMutation} from '$lib/stores/portfolio/portfolioMutation';

let fetchRiskCatalog: typeof import('./riskStore.svelte').fetchRiskCatalog;
let getRiskQuerySnapshot: typeof import('./riskStore.svelte').getRiskQuerySnapshot;
let hasRiskCapability: typeof import('./riskStore.svelte').hasRiskCapability;
let invalidateRisk: typeof import('./riskStore.svelte').invalidateRisk;
let makeRiskRequestKey: typeof import('./riskStore.svelte').makeRiskRequestKey;
let queryRisk: typeof import('./riskStore.svelte').queryRisk;

const baseRequest = {
    scope: {kind: 'portfolio' as const},
    date_range: {start: '2025-01-01', end: '2025-12-31'},
    target_currency: 'EUR',
    mode: 'historical' as const,
    analytics: [{instance_id: 'kpi', analytic_code: 'historical_kpi', parameters: {}}],
};

describe('riskStore', () => {
    beforeAll(async () => {
        Object.defineProperty(globalThis, '$state', {
            configurable: true,
            value: <T>(value: T): T => value,
        });
        ({fetchRiskCatalog, getRiskQuerySnapshot, hasRiskCapability, invalidateRisk, makeRiskRequestKey, queryRisk} = await import('./riskStore.svelte'));
    });

    beforeEach(() => {
        catalogApi.mockReset();
        queryApi.mockReset();
        invalidateRisk();
    });

    it('uses a stable key for equivalent object construction order', () => {
        transitionClientSession(101);
        const reordered = {
            analytics: [{parameters: {}, analytic_code: 'historical_kpi', instance_id: 'kpi'}],
            mode: 'historical' as const,
            target_currency: 'EUR',
            date_range: {end: '2025-12-31', start: '2025-01-01'},
            scope: {kind: 'portfolio' as const},
        };

        expect(makeRiskRequestKey(baseRequest)).toBe(makeRiskRequestKey(reordered));
    });

    it('canonicalizes unordered portfolio broker subsets', () => {
        transitionClientSession(102);
        const first = {
            ...baseRequest,
            scope: {kind: 'portfolio' as const, broker_ids: [9, 3]},
        };
        const second = {
            ...baseRequest,
            scope: {kind: 'portfolio' as const, broker_ids: [3, 9]},
        };

        expect(makeRiskRequestKey(first)).toBe(makeRiskRequestKey(second));
    });

    it('canonicalizes asset universes, replay proxies, exclusions, and currency', () => {
        transitionClientSession(103);
        const first = buildRiskQueryRequest({
            scope: {kind: 'asset_set', asset_ids: [9, 3]},
            dateStart: '2025-01-01',
            dateEnd: '2025-12-31',
            targetCurrency: ' eur ',
            mode: 'current_composition',
            compositionPolicy: 'current_buy_and_hold',
            analytics: [
                {
                    instance_id: 'replay',
                    analytic_code: 'stress',
                    parameters: buildHistoricalReplayParameters({
                        start: '2020-02-01',
                        end: '2020-04-30',
                        missingHistoryPolicy: 'manual_proxy_or_exclude',
                        proxyAssets: [
                            {asset_id: 9, proxy_asset_id: 19},
                            {asset_id: 3, proxy_asset_id: 13},
                        ],
                        excludedAssetIds: [8, 4],
                    }),
                },
            ],
        });
        const second = buildRiskQueryRequest({
            ...first,
            scope: {kind: 'asset_set', asset_ids: [3, 9]},
            dateStart: '2025-01-01',
            dateEnd: '2025-12-31',
            targetCurrency: 'EUR',
            mode: first.mode,
            compositionPolicy: first.composition_policy,
            analytics: [
                {
                    ...first.analytics[0],
                    parameters: buildHistoricalReplayParameters({
                        start: '2020-02-01',
                        end: '2020-04-30',
                        missingHistoryPolicy: 'manual_proxy_or_exclude',
                        proxyAssets: [
                            {asset_id: 3, proxy_asset_id: 13},
                            {asset_id: 9, proxy_asset_id: 19},
                        ],
                        excludedAssetIds: [4, 8],
                    }),
                },
            ],
        });

        expect(first.target_currency).toBe('EUR');
        expect(makeRiskRequestKey(first)).toBe(makeRiskRequestKey(second));
    });

    it('preserves contractually ordered arrays in request identity', () => {
        transitionClientSession(104);
        const reversed = {
            ...baseRequest,
            analytics: [
                {instance_id: 'var', analytic_code: 'historical_var', parameters: {}},
                {instance_id: 'kpi', analytic_code: 'historical_kpi', parameters: {}},
            ],
        };
        const forward = {...reversed, analytics: [...reversed.analytics].reverse()};

        expect(makeRiskRequestKey(reversed)).not.toBe(makeRiskRequestKey(forward));
    });

    it('deduplicates and caches identical bulk queries', async () => {
        transitionClientSession(201);
        queryApi.mockResolvedValue({items: []});

        const first = queryRisk(baseRequest);
        const second = queryRisk(baseRequest);

        expect(await first).toEqual({items: []});
        expect(await second).toEqual({items: []});
        expect(await queryRisk(baseRequest)).toEqual({items: []});
        expect(queryApi).toHaveBeenCalledTimes(1);
    });

    it('retains query errors by identity until force refresh or invalidation', async () => {
        transitionClientSession(202);
        const failure = new Error('offline');
        queryApi.mockRejectedValueOnce(failure);

        await expect(queryRisk(baseRequest)).rejects.toBe(failure);
        await expect(queryRisk(baseRequest)).rejects.toBe(failure);
        expect(queryApi).toHaveBeenCalledTimes(1);
        expect(getRiskQuerySnapshot(baseRequest)).toMatchObject({
            status: 'error',
            response: null,
            error: failure,
        });

        queryApi.mockResolvedValueOnce({items: []});
        await expect(queryRisk(baseRequest, true)).resolves.toEqual({items: []});
        expect(queryApi).toHaveBeenCalledTimes(2);
        expect(getRiskQuerySnapshot(baseRequest)).toMatchObject({
            status: 'success',
            response: {items: []},
            error: null,
        });
    });

    it('sends the canonical request to the generated client', async () => {
        transitionClientSession(203);
        queryApi.mockResolvedValueOnce({items: []});
        const request = {
            ...baseRequest,
            target_currency: ' eur ',
            scope: {kind: 'portfolio' as const, broker_ids: [9, 3]},
        };

        await queryRisk(request);

        expect(queryApi).toHaveBeenCalledWith(
            expect.objectContaining({
                target_currency: 'EUR',
                scope: {kind: 'portfolio', broker_ids: [3, 9]},
            }),
        );
    });

    it('drops stale responses after an account transition', async () => {
        let resolveFirst: (value: unknown) => void = () => undefined;
        transitionClientSession(301);
        queryApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveFirst = resolve;
                }),
        );
        const stale = queryRisk(baseRequest);

        transitionClientSession(302);
        queryApi.mockResolvedValueOnce({items: [{instance_id: 'current'}]});
        const current = await queryRisk(baseRequest);

        resolveFirst({items: [{instance_id: 'stale'}]});
        expect(await stale).toBeNull();
        expect(current).toEqual({items: [{instance_id: 'current'}]});
    });

    it('invalidates catalog and queries after portfolio-affecting mutations', async () => {
        transitionClientSession(401);
        catalogApi.mockResolvedValue({items: []});
        queryApi.mockResolvedValue({items: []});

        await fetchRiskCatalog();
        await queryRisk(baseRequest);
        notifyPortfolioMutation('POST', '/api/v1/assets/prices/sync');
        await fetchRiskCatalog();
        await queryRisk(baseRequest);

        expect(catalogApi).toHaveBeenCalledTimes(2);
        expect(queryApi).toHaveBeenCalledTimes(2);
    });

    it('checks catalog scope and mode capabilities', () => {
        const catalog = {
            items: [
                {
                    analytic_code: 'correlation',
                    name_i18n_key: 'risk.analytics.correlation.name',
                    description_i18n_key: 'risk.analytics.correlation.description',
                    output_kind: 'matrix' as const,
                    supported_scopes: ['asset_set' as const, 'portfolio' as const],
                    supported_modes: ['historical' as const],
                    parameters_schema: {},
                    min_observations: 2,
                    algorithm_version: '1.0.0',
                },
            ],
        };

        expect(hasRiskCapability(catalog, 'correlation', 'portfolio', 'historical')).toBe(true);
        expect(hasRiskCapability(catalog, 'correlation', 'asset', 'historical')).toBe(false);
        expect(hasRiskCapability(catalog, 'correlation', 'portfolio', 'current_composition')).toBe(false);
    });

    it('builds mutually exclusive MC and QMC simulation controls', () => {
        expect(
            buildSimulationParameters({
                samplingMethod: 'mc',
                horizonDays: 365,
                pathCount: 8192,
                randomSeed: 7,
                sobolStartIndex: 11,
            }),
        ).toEqual({
            process: 'gbm',
            sampling_method: 'mc',
            horizon_days: 365,
            path_count: 8192,
            random_seed: 7,
        });
        expect(
            buildSimulationParameters({
                samplingMethod: 'qmc',
                horizonDays: 365,
                pathCount: 8192,
                randomSeed: 7,
                sobolStartIndex: 11,
            }),
        ).toEqual({
            process: 'gbm',
            sampling_method: 'qmc',
            horizon_days: 365,
            path_count: 8192,
            sobol_start_index: 11,
        });
    });
});
