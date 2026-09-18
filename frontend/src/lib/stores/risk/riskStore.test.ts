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

import {buildHistoricalReplayParameters, buildRiskQueryRequest, buildSimulationParameters, canonicalizeScope, type RiskScope} from '$lib/risk/riskRequest';
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

    it('canonicalizes a portfolio slice that carries no broker subset', () => {
        // The Dashboard mounts `{kind: 'portfolio'}` with no broker subset, so an asset
        // slice there reaches canonicalization with `broker_ids` absent. Ordering must
        // not depend on the presence of the other narrowing.
        // Asserted on `canonicalizeScope` directly and not through the request key,
        // because the key currently cannot see the field at all — see the boundary
        // test below, which is what makes this one non-vacuous.
        const sliced = (assetIds: number[]) => canonicalizeScope({kind: 'portfolio', asset_ids: assetIds} as unknown as RiskScope) as unknown as {asset_ids: number[]};

        expect(sliced([9, 3]).asset_ids).toEqual([3, 9]);
        expect(sliced([3, 9]).asset_ids).toEqual([3, 9]);
    });

    it('keeps the broker and asset narrowings independent', () => {
        const scoped = canonicalizeScope({kind: 'portfolio', broker_ids: [9, 3], asset_ids: [4, 2]} as unknown as RiskScope) as unknown as {
            broker_ids: number[];
            asset_ids: number[];
        };

        expect(scoped.broker_ids).toEqual([3, 9]);
        expect(scoped.asset_ids).toEqual([2, 4]);
    });

    it('gives a portfolio slice its own request key, apart from another slice and from the whole', () => {
        transitionClientSession(105);
        // The alarm planted at `bf34f3a0a` has fired, and this is the invariant it asked
        // for. Before the field landed, `canonicalizeRiskRequest` ended in
        // `schemas.RiskQueryRequest.parse(...)`, Zod dropped `asset_ids` as an unknown
        // key, and every slice collapsed onto the unsliced portfolio's key. The danger
        // was never a cache that doubles: it was the whole portfolio served under a
        // sliced heading. `PortfolioRiskScope` now carries the field, so the key has to
        // keep apart three requests that used to be one — and the cast this test needed
        // while the field was missing is gone, which is the same fact stated in types.
        const scoped = (assetIds: number[]) => ({...baseRequest, scope: {...baseRequest.scope, asset_ids: assetIds}});

        expect(makeRiskRequestKey(scoped([2, 4])), 'two different slices must not share one cached answer').not.toBe(makeRiskRequestKey(scoped([2, 5])));
        expect(makeRiskRequestKey(scoped([2, 4])), 'a slice must not be served the unsliced portfolio — the failure the alarm was planted for').not.toBe(makeRiskRequestKey(baseRequest));
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

    it('re-issues a catalog fetch whose answer a mid-flight mutation discarded', async () => {
        // Opening an asset page persists today's price, which notifies the portfolio
        // mutation listeners, which invalidate risk — so a catalog request can be
        // discarded for an entirely mundane reason. Handing the caller a null there
        // leaves the panel stuck on an error it can never leave: nothing re-asks.
        let resolveFirst: (value: unknown) => void = () => undefined;
        catalogApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveFirst = resolve;
                }),
        );
        const pending = fetchRiskCatalog();

        notifyPortfolioMutation('POST', '/api/v1/assets/prices/sync');
        catalogApi.mockResolvedValueOnce({items: [{analytic_code: 'retried'}]});
        resolveFirst({items: [{analytic_code: 'discarded'}]});

        expect(await pending).toEqual({items: [{analytic_code: 'retried'}]});
        expect(catalogApi).toHaveBeenCalledTimes(2);
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

/**
 * The first identity resolution is the one path that bumps the session generation
 * *without* running the registered resetters (clientSession.transition returns
 * early at the `!hasResolvedIdentity` branch). Anything already in flight when the
 * app learns who the user is therefore gets discarded on arrival with nobody
 * clearing its in-flight slot — so it needs its own module state to reproduce.
 */
describe('riskStore — first identity resolution', () => {
    it('releases the in-flight catalog slot discarded by the first identity resolution', async () => {
        vi.resetModules();
        catalogApi.mockReset();

        const {transitionClientSession: freshTransition} = await import('$lib/stores/app/clientSession');
        const {fetchRiskCatalog: freshFetchCatalog} = await import('./riskStore.svelte');

        let resolveFirst: (value: unknown) => void = () => undefined;
        catalogApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveFirst = resolve;
                }),
        );
        // Fired before the app knows who is logged in — the panel mounts and asks
        // for its capability catalog while identity is still resolving.
        const straddling = freshFetchCatalog();

        freshTransition(701);
        catalogApi.mockResolvedValueOnce({items: [{analytic_code: 'fresh'}]});
        resolveFirst({items: [{analytic_code: 'discarded'}]});

        // Dropping the stale response is right; dropping the request with it is not.
        // Nothing else re-asks: the single module-level slot would stay parked on an
        // already-resolved null and every later caller would short-circuit on it, so
        // the panel would sit unable to load for the life of the page.
        expect(await straddling).toEqual({items: [{analytic_code: 'fresh'}]});
        expect(catalogApi).toHaveBeenCalledTimes(2);
    });

    it('discards an answer to a question asked before the identity existed', async () => {
        // Not a second copy of 'drops stale responses after an account transition'
        // in the block above. That one moves 301 → 302 — the *second* transition,
        // which runs the registered resetters on its way through, so the cache is
        // cleared as it passes. This is the *first* resolution, which returns early
        // before any resetter runs, and it is the only one a page reload performs.
        //
        // The ordering is the whole subject. Every test in the block above resolves
        // the identity and *then* queries; the app does the opposite, and has no
        // choice about it: `(app)/+layout.svelte` fires `checkAuth()` from `onMount`
        // behind no auth gate — its only top-level `{#if}` is `$i18nLoading` — so a
        // panel mounts and asks its question at generation 0 while `GET /auth/me` is
        // still in flight.
        vi.resetModules();
        queryApi.mockReset();

        const {transitionClientSession: freshTransition} = await import('$lib/stores/app/clientSession');
        const {queryRisk: freshQueryRisk} = await import('./riskStore.svelte');

        let resolveStraddling: (value: unknown) => void = () => undefined;
        queryApi.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    resolveStraddling = resolve;
                }),
        );
        // Asked before the app knows who is logged in.
        const straddling = freshQueryRisk(baseRequest);

        // Identity resolves for the first time, on top of the question. The generation
        // moves without anything being cleared, so the request is still parked in its
        // in-flight slot at the moment its own answer stops being usable.
        freshTransition(801);
        resolveStraddling({items: [{instance_id: 'kpi', analytic_code: 'correlation'}]});

        // Discarding it is right — it was computed for nobody in particular. What the
        // null cannot say is that it is a discard: it is shaped exactly like a query
        // that ran and found nothing, and folding the two together is how a complete
        // 16/16 matrix reached the screen as an empty panel that never refilled.
        expect(await straddling, 'a full answer to a question asked before the identity resolved was handed back as though it belonged to the resolved account').toBeNull();
        expect(queryApi, 'queryRisk re-asked the discarded question by itself; unlike the catalog above it deliberately does not, because only the caller knows whether the question still stands').toHaveBeenCalledTimes(1);
    });
});
