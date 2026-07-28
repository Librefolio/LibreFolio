import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const catalogApi = vi.hoisted(() => vi.fn());
const queryApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: {
        get_risk_catalog_api_v1_risk_catalog_get: catalogApi,
        query_risk_api_v1_risk_query_post: queryApi,
    },
}));

import {transitionClientSession} from '$lib/stores/app/clientSession';
import {notifyPortfolioMutation} from '$lib/stores/portfolio/portfolioMutation';

let fetchRiskCatalog: typeof import('./riskStore.svelte').fetchRiskCatalog;
let hasRiskCapability: typeof import('./riskStore.svelte').hasRiskCapability;
let invalidateRisk: typeof import('./riskStore.svelte').invalidateRisk;
let makeRiskRequestKey: typeof import('./riskStore.svelte').makeRiskRequestKey;
let queryRisk: typeof import('./riskStore.svelte').queryRisk;

const baseRequest = {
    scope: {kind: 'portfolio' as const},
    date_range: {start: '2025-01-01', end: '2025-12-31'},
    target_currency: 'EUR',
    mode: 'historical' as const,
    analytics: [{instance_id: 'kpi', analytic_code: 'portfolio_kpi', parameters: {}}],
};

describe('riskStore', () => {
    beforeAll(async () => {
        Object.defineProperty(globalThis, '$state', {
            configurable: true,
            value: <T>(value: T): T => value,
        });
        ({fetchRiskCatalog, hasRiskCapability, invalidateRisk, makeRiskRequestKey, queryRisk} = await import('./riskStore.svelte'));
    });

    beforeEach(() => {
        catalogApi.mockReset();
        queryApi.mockReset();
        invalidateRisk();
    });

    it('uses a stable key for equivalent object construction order', () => {
        transitionClientSession(101);
        const reordered = {
            analytics: [{parameters: {}, analytic_code: 'portfolio_kpi', instance_id: 'kpi'}],
            mode: 'historical' as const,
            target_currency: 'EUR',
            date_range: {end: '2025-12-31', start: '2025-01-01'},
            scope: {kind: 'portfolio' as const},
        };

        expect(makeRiskRequestKey(baseRequest)).toBe(makeRiskRequestKey(reordered));
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
        expect(hasRiskCapability(catalog, 'correlation', 'broker', 'historical')).toBe(false);
        expect(hasRiskCapability(catalog, 'correlation', 'portfolio', 'current_composition')).toBe(false);
    });
});
