import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const catalogApi = vi.hoisted(() => vi.fn());
const scenarioCatalogApi = vi.hoisted(() => vi.fn());
const queryApi = vi.hoisted(() => vi.fn());
const eligibilityApi = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/api')>();
    return {
        ...actual,
        zodiosApi: {
            ...actual.zodiosApi,
            get_risk_catalog_api_v1_risk_catalog_get: catalogApi,
            get_scenario_catalog_api_v1_risk_scenario_catalog_get: scenarioCatalogApi,
            query_risk_api_v1_risk_query_post: queryApi,
            asset_eligibility_api_v1_risk_eligibility_post: eligibilityApi,
        },
    };
});

import type {AssetEligibilityItem, EligibilityVerdicts} from '$lib/components/risk/eligibility';
import {buildHistoricalReplayParameters, buildRiskQueryRequest, buildSimulationParameters, canonicalizeScope, type RiskScope} from '$lib/risk/riskRequest';
import {transitionClientSession} from '$lib/stores/app/clientSession';
import {notifyPortfolioMutation} from '$lib/stores/portfolio/portfolioMutation';

let fetchRiskCatalog: typeof import('./riskStore.svelte').fetchRiskCatalog;
let fetchRiskScenarioCatalog: typeof import('./riskStore.svelte').fetchRiskScenarioCatalog;
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
        ({fetchRiskCatalog, fetchRiskScenarioCatalog, getRiskQuerySnapshot, hasRiskCapability, invalidateRisk, makeRiskRequestKey, queryRisk} = await import('./riskStore.svelte'));
    });

    beforeEach(() => {
        catalogApi.mockReset();
        scenarioCatalogApi.mockReset();
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

    // One bound for every discarded risk answer: the two catalog fetches here, and the
    // base wave and on-demand runs of `riskPanelController`, which re-ask a `null` from
    // `queryRisk` (that function deliberately never re-asks by itself: see 'discards an
    // answer to a question asked before the identity existed').
    it('exports the discard bound every risk question shares: three attempts in all', async () => {
        // Read through the namespace rather than as a named import: the name is the subject,
        // and a named import of a name not exported yet fails the type check, not this test.
        const store = (await import('./riskStore.svelte')) as unknown as Record<string, unknown>;
        expect(store.RISK_DISCARD_ATTEMPTS, 'RISK_DISCARD_ATTEMPTS is not exported as 3: the catalogs, the base wave and the on-demand runs would each keep a bound of their own, free to drift apart').toBe(3);
    });

    it.each<[string, typeof catalogApi, () => Promise<unknown>]>([
        ['the risk catalog', catalogApi, () => fetchRiskCatalog()],
        ['the scenario catalog', scenarioCatalogApi, () => fetchRiskScenarioCatalog()],
    ])('gives up on %s after three attempts discarded in flight, and asks no fourth time', async (_name, api, load) => {
        // Every attempt is invalidated while it is in flight, as the live price poll's
        // portfolio mutation does; a fourth would be kept. A fetch that asked until something
        // stuck, instead of within its bound, would return that fourth answer and look healthy.
        // `invalidateRisk` rather than `notifyPortfolioMutation`: it is bound with the fetch in
        // `beforeAll`, so both always reach the same module instance, whichever order the
        // module-resetting block below runs in.
        let attempts = 0;
        api.mockImplementation(() => {
            attempts += 1;
            if (attempts <= 3) invalidateRisk();
            return Promise.resolve({items: [{analytic_code: `attempt ${attempts}`}]});
        });

        expect(await load(), 'an answer discarded on every attempt was handed back as current, or a fourth attempt was made and kept').toBeNull();
        expect(api, 'the fetch is not bounded at three attempts').toHaveBeenCalledTimes(3);
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
                process: 'gbm',
                regime: 'none',
                samplingMethod: 'mc',
                horizonDays: 365,
                pathCount: 8192,
                randomSeed: 7,
                sobolStartIndex: 11,
            }),
        ).toEqual({
            process: 'gbm',
            regime: 'none',
            sampling_method: 'mc',
            horizon_days: 365,
            path_count: 8192,
            random_seed: 7,
        });
        expect(
            buildSimulationParameters({
                process: 'gbm',
                regime: 'none',
                samplingMethod: 'qmc',
                horizonDays: 365,
                pathCount: 8192,
                randomSeed: 7,
                sobolStartIndex: 11,
            }),
        ).toEqual({
            process: 'gbm',
            regime: 'none',
            sampling_method: 'qmc',
            horizon_days: 365,
            path_count: 8192,
            sobol_start_index: 11,
        });
    });
});

/**
 * `queryEligibility(assetIds, period, currency)` — Risk's verdicts on a set of assets for a
 * period and a currency, asked once per question (stage 2: `BenchmarkSelect` on F's asset
 * picker panel, D371 for the lab and D378 for every page).
 *
 * The verdict is the engine's (`POST /api/v1/risk/eligibility`): the store only asks, in the
 * batches the engine accepts (`eligibilityBatches`, at most 500 ids, never an empty list), and
 * merges the answers (`mergeEligibilityAnswers`). What is pinned:
 *
 *   1. **No assets, no question**: `EMPTY_VERDICTS`, and nothing reaches the engine.
 *   2. **The question as the engine takes it**: `{asset_ids, date_range: {start, end},
 *      target_currency}` through the generated client, batched, each id asked once.
 *   3. **One question, one request**: cached per (sorted unique ids, start, end, currency), so
 *      the order of the ids and their repetitions do not matter and every other part does; and
 *      identical questions asked at once share the request in flight. Two pickers, or one
 *      picker remounted, never ask twice.
 *   4. **`invalidateRisk()` forgets the answers**: the next question asks again, and does not
 *      wait on a request that left before the invalidation. That request's answer, when it
 *      lands, is discarded: it resolves `null` — as `queryRisk`'s does — and is cached nowhere.
 *   5. **A failure rejects and is not remembered**: the caller decides what a failure means,
 *      and the same question asked later asks again. Unlike `queryRisk`, which keeps errors.
 *
 * Self-contained on purpose. The block below resets the module registry (`vi.resetModules`),
 * so a function bound in a `beforeAll` may belong to a module instance the store no longer is
 * under a shuffled order. This block binds nothing: every case reads `queryEligibility`, its
 * `invalidateRisk` and the eligibility module from the registry at call time, so they are
 * always one instance, and it never transitions the client session.
 */
describe('riskStore — queryEligibility', () => {
    interface Period {
        start: string;
        end: string;
    }

    type QueryEligibility = (assetIds: readonly number[], period: Period, currency: string) => Promise<EligibilityVerdicts | null>;

    interface EligibilityBody {
        asset_ids: number[];
        date_range: {start: string; end?: string | null};
        target_currency: string;
    }

    interface EligibilityAnswer {
        items: AssetEligibilityItem[];
        min_quotes: number;
        stale_days: number;
        common_range?: Period | null;
        suggested_range?: Period | null;
    }

    const PERIOD: Period = {start: '2025-01-01', end: '2025-12-31'};
    const byNumber = (left: number, right: number): number => left - right;

    /**
     * The store and the eligibility module, as the registry holds them now. A missing export
     * fails the case that asked for it, with the contract in the message, rather than the import.
     */
    async function subject(): Promise<{queryEligibility: QueryEligibility; invalidateRisk: () => void; eligibility: typeof import('$lib/components/risk/eligibility')}> {
        const store = (await import('./riskStore.svelte')) as unknown as Record<string, unknown>;
        const eligibility = await import('$lib/components/risk/eligibility');
        expect(typeof store.queryEligibility, 'riskStore exports no queryEligibility(assetIds, period, currency): the pickers have no shared, cached way to ask the eligibility engine').toBe('function');
        return {queryEligibility: store.queryEligibility as QueryEligibility, invalidateRisk: store.invalidateRisk as () => void, eligibility};
    }

    /** A verdict per id, mixed so a dropped or misplaced batch shows: every third id is ruled out. */
    function verdictFor(assetId: number): AssetEligibilityItem {
        return assetId % 3 === 0 ? {asset_id: assetId, level: 'ineligible', reasons: ['no_prices'], first_quote: null, last_quote: null, quotes_in_period: 0} : {asset_id: assetId, level: 'eligible', reasons: [], first_quote: '2024-06-03', last_quote: '2025-12-30', quotes_in_period: 250};
    }

    /** The engine's answer to one request: a verdict for exactly the ids it was asked about. */
    function answerTo(body: EligibilityBody, extra: Partial<EligibilityAnswer> = {}): EligibilityAnswer {
        return {items: body.asset_ids.map(verdictFor), min_quotes: 20, stale_days: 7, ...extra};
    }

    function engineAnswers(extra: Partial<EligibilityAnswer> = {}): void {
        eligibilityApi.mockImplementation(async (body: EligibilityBody) => answerTo(body, extra));
    }

    /** Every request body the generated client received, in order. */
    function bodies(): EligibilityBody[] {
        return eligibilityApi.mock.calls.map(([body]) => body as EligibilityBody);
    }

    function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
        let resolve!: (value: T) => void;
        const promise = new Promise<T>((settle) => {
            resolve = settle;
        });
        return {promise, resolve};
    }

    beforeEach(async () => {
        eligibilityApi.mockReset();
        // An answer cached by a neighbouring case would let a question here pass without asking.
        ((await import('./riskStore.svelte')) as unknown as {invalidateRisk: () => void}).invalidateRisk();
    });

    it('exports queryEligibility(assetIds, period, currency)', async () => {
        await subject();
    });

    it('resolves EMPTY_VERDICTS for no assets, without asking the engine', async () => {
        const {queryEligibility, eligibility} = await subject();
        engineAnswers();

        // The engine rejects an empty list: the question must not leave at all.
        await expect(queryEligibility([], PERIOD, 'EUR')).resolves.toBe(eligibility.EMPTY_VERDICTS);
        expect(eligibilityApi, 'an empty question reached the engine').not.toHaveBeenCalled();
    });

    it('asks the generated client with the ids, the period and the currency, and merges the answer', async () => {
        const {queryEligibility, eligibility} = await subject();
        // A single request keeps the ranges: they describe the assets of that request taken together.
        const ranges = {common_range: {start: '2025-03-14', end: '2025-12-30'}, suggested_range: {start: '2025-03-15', end: '2025-12-30'}};
        engineAnswers(ranges);

        const verdicts = await queryEligibility([7, 3, 9], PERIOD, 'EUR');

        expect(eligibilityApi).toHaveBeenCalledTimes(1);
        const [body] = bodies();
        expect({...body, asset_ids: [...body.asset_ids].sort(byNumber)}, 'the request is not the question as the engine takes it').toEqual({asset_ids: [3, 7, 9], date_range: {start: PERIOD.start, end: PERIOD.end}, target_currency: 'EUR'});
        expect(verdicts, 'the answer was not merged by mergeEligibilityAnswers').toEqual(eligibility.mergeEligibilityAnswers([answerTo(body, ranges)]));
        expect(verdicts?.items.get(3)?.level, 'premise: the merged answer carries the engine’s verdicts').toBe('ineligible');
        expect(verdicts?.commonRange).toEqual(ranges.common_range);
    });

    it('splits a question larger than the engine accepts into batches of at most 500, each id asked once, and merges every batch', async () => {
        const {queryEligibility, eligibility} = await subject();
        engineAnswers();
        const ids = Array.from({length: 2 * eligibility.ELIGIBILITY_BATCH + 1}, (_, index) => index + 1);

        const verdicts = await queryEligibility(ids, PERIOD, 'EUR');

        const batches = bodies().map((body) => body.asset_ids);
        expect(batches.length, 'not split as eligibilityBatches splits: 1001 ids are three requests').toBe(3);
        for (const batch of batches) expect(batch.length).toBeLessThanOrEqual(eligibility.ELIGIBILITY_BATCH);
        expect(batches.flat().sort(byNumber), 'an id was asked twice, or never').toEqual(ids);
        for (const body of bodies()) {
            expect(body.date_range).toEqual({start: PERIOD.start, end: PERIOD.end});
            expect(body.target_currency).toBe('EUR');
        }
        expect(verdicts, 'the batches were not merged by mergeEligibilityAnswers').toEqual(eligibility.mergeEligibilityAnswers(bodies().map((body) => answerTo(body))));
        expect(verdicts?.items.size).toBe(ids.length);
    });

    it('serves the same question again from its cache, whatever the order of the ids or their repetitions', async () => {
        const {queryEligibility} = await subject();
        engineAnswers();

        const first = await queryEligibility([3, 1, 2], PERIOD, 'EUR');
        const again = await queryEligibility([2, 3, 1, 3, 1], {...PERIOD}, 'EUR');

        expect(eligibilityApi, 'the same question reached the engine twice').toHaveBeenCalledTimes(1);
        expect(again).toEqual(first);
        expect(again?.items.size).toBe(3);
    });

    it('asks again when any part of the question changes: the ids, the start, the end or the currency', async () => {
        const {queryEligibility} = await subject();
        engineAnswers();

        await queryEligibility([1, 2, 3], PERIOD, 'EUR');
        await queryEligibility([1, 2, 4], PERIOD, 'EUR');
        await queryEligibility([1, 2, 3], {start: '2025-02-01', end: PERIOD.end}, 'EUR');
        await queryEligibility([1, 2, 3], {start: PERIOD.start, end: '2025-11-28'}, 'EUR');
        await queryEligibility([1, 2, 3], PERIOD, 'USD');

        expect(eligibilityApi, 'two different questions shared one cached answer').toHaveBeenCalledTimes(5);
        expect(bodies().map((body) => [body.date_range.start, body.date_range.end, body.target_currency])).toEqual([
            [PERIOD.start, PERIOD.end, 'EUR'],
            [PERIOD.start, PERIOD.end, 'EUR'],
            ['2025-02-01', PERIOD.end, 'EUR'],
            [PERIOD.start, '2025-11-28', 'EUR'],
            [PERIOD.start, PERIOD.end, 'USD'],
        ]);

        // …while the first question is still answered from the cache.
        await queryEligibility([3, 2, 1], PERIOD, 'EUR');
        expect(eligibilityApi).toHaveBeenCalledTimes(5);
    });

    it('shares one request between identical questions asked at once', async () => {
        const {queryEligibility} = await subject();
        const answer = deferred<EligibilityAnswer>();
        eligibilityApi.mockImplementation(() => answer.promise);

        const first = queryEligibility([1, 2, 3], PERIOD, 'EUR');
        const second = queryEligibility([3, 2, 1, 1], PERIOD, 'EUR');
        answer.resolve(answerTo({asset_ids: [1, 2, 3], date_range: PERIOD, target_currency: 'EUR'}));
        const [left, right] = await Promise.all([first, second]);

        expect(eligibilityApi, 'a question asked while the same one was in flight sent a request of its own').toHaveBeenCalledTimes(1);
        expect(left?.items.size).toBe(3);
        expect(right).toEqual(left);
    });

    it('asks again after invalidateRisk()', async () => {
        const {queryEligibility, invalidateRisk} = await subject();
        engineAnswers();

        await queryEligibility([1, 2, 3], PERIOD, 'EUR');
        invalidateRisk();
        await queryEligibility([1, 2, 3], PERIOD, 'EUR');

        expect(eligibilityApi, 'invalidateRisk() left the eligibility answers cached').toHaveBeenCalledTimes(2);
    });

    it('resolves null for an answer that lands after invalidateRisk(), and caches nothing', async () => {
        const {queryEligibility, invalidateRisk} = await subject();
        const late = deferred<EligibilityAnswer>();
        eligibilityApi.mockImplementationOnce(() => late.promise);

        const straddling = queryEligibility([1, 2, 3], PERIOD, 'EUR');
        await vi.waitFor(() => expect(eligibilityApi, 'the question never left').toHaveBeenCalledTimes(1));
        invalidateRisk();
        late.resolve(answerTo({asset_ids: [1, 2, 3], date_range: PERIOD, target_currency: 'EUR'}));

        // The answer describes a world the invalidation said is gone: discarded, as queryRisk's is.
        expect(await straddling, 'an answer to a question asked before the invalidation was handed back as current').toBeNull();
        engineAnswers();
        const asked = await queryEligibility([1, 2, 3], PERIOD, 'EUR');
        expect(eligibilityApi, 'the discarded answer was cached: the same question did not ask again').toHaveBeenCalledTimes(2);
        expect(asked?.items.size).toBe(3);
    });

    it('does not hand a question asked after invalidateRisk() to a request that left before it', async () => {
        const {queryEligibility, invalidateRisk} = await subject();
        const late = deferred<EligibilityAnswer>();
        eligibilityApi.mockImplementationOnce(() => late.promise);

        const straddling = queryEligibility([1, 2, 3], PERIOD, 'EUR');
        await vi.waitFor(() => expect(eligibilityApi, 'the question never left').toHaveBeenCalledTimes(1));
        invalidateRisk();
        engineAnswers();
        const fresh = queryEligibility([1, 2, 3], PERIOD, 'EUR');

        // Joining the request in flight would hand this caller the null its answer is bound to become.
        await vi.waitFor(() => expect(eligibilityApi, 'the question asked after the invalidation joined the request in flight instead of asking again').toHaveBeenCalledTimes(2));
        expect((await fresh)?.items.size).toBe(3);
        late.resolve(answerTo({asset_ids: [1, 2, 3], date_range: PERIOD, target_currency: 'EUR'}));
        expect(await straddling).toBeNull();
    });

    it('rejects when the request fails, and does not remember the failure: the same question asks again', async () => {
        const {queryEligibility} = await subject();
        const failure = new Error('synthetic: eligibility engine unreachable');
        eligibilityApi.mockRejectedValueOnce(failure);

        await expect(queryEligibility([1, 2, 3], PERIOD, 'EUR'), 'a failed request must reach the caller, which decides what it means').rejects.toBe(failure);

        engineAnswers();
        const retried = await queryEligibility([1, 2, 3], PERIOD, 'EUR');
        expect(eligibilityApi, 'the failure was cached: the same question did not ask again').toHaveBeenCalledTimes(2);
        expect(retried?.items.size).toBe(3);
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
