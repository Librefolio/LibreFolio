// @vitest-environment jsdom
//
// The docblock above is load-bearing, not decoration. Under the repository's
// default `node` environment a `.svelte.ts` compiles but its effects never run,
// so every negative assertion in this file would pass while proving nothing.
// `assertEffectsRun()` in the first test fails loudly if it is ever removed.
import {beforeEach, describe, expect, it, onTestFinished, vi} from 'vitest';
import {flushSync} from 'svelte';

import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import type {RiskAnalyticParameters, RiskMode, RiskQueryRequest} from '$lib/risk/riskRequest';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());
/** Read at call time by the `hasRiskCapability` stub; `beforeEach` puts it back. */
const capability = vi.hoisted(() => ({supported: true}));

vi.mock('$lib/stores/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskStore.svelte')>();
    return {
        ...actual,
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        queryRisk,
        invalidateRisk,
        // Every analytic is available: capability gating is the panel's business,
        // not the controller's, and stubbing it here keeps the subject singular.
        // The one test about an unsupported analytic flips it for itself.
        hasRiskCapability: () => capability.supported,
    };
});

import {assertEffectsRun, effectRoot, reactiveBox, recordReads} from '$test/runes.svelte';
import {ANSWER_DISCARDED_CODE, baseSignature, createRiskPanelController, discardedErrorCodes, LEVEL_ON_DEMAND_ANALYSES, mergeQualityIssues, ON_DEMAND_ANALYSES, type OnDemandAnalysis, type RiskControllerInputs, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import {normalizeQualityIssue} from '$lib/components/risk/riskAnalysisHelpers';
import type {DataQualityIssue} from '$lib/components/ui/feedback/DataQualityBanner.svelte';

/** `asset_ids` reaches the portfolio scope with K4; the generated client does not
 *  declare it yet, so the test states the shape the controller will actually see. */
function portfolioSlice(assetIds: number[]): RiskControllerInputs['scope'] {
    return {kind: 'portfolio', asset_ids: assetIds} as unknown as RiskControllerInputs['scope'];
}

const CATALOG = {items: []};

function defaultInputs(): RiskControllerInputs {
    return {
        scope: {kind: 'portfolio'},
        dateStart: '2025-01-01',
        dateEnd: '2025-12-31',
        targetCurrency: 'EUR',
        appliedRiskFreePercent: 2,
        refreshVersion: 0,
    };
}

/** A promise whose resolution this test controls, so "in flight" is a real state
 *  rather than a race we hope to win. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((r) => {
        resolve = r;
    });
    return {promise, resolve};
}

function mountController(initial: RiskControllerInputs = defaultInputs()) {
    const inputs = reactiveBox(initial);
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => inputs));
    flushSync();
    return {controller, inputs, stop};
}

type Mounted = ReturnType<typeof mountController>;

/** What an on-demand question answers here: a response, a *discard* (`null`, what
 *  `queryRisk` returns when the client session or the cache generation moved while
 *  the request was in flight), a failure, or a promise of either that the test
 *  settles itself. */
type OnDemandAnswer = {items: {analytic_code: string}[]} | null;
type Scripted = OnDemandAnswer | Error | Promise<OnDemandAnswer>;

/** One question per analysis, phrased the way its host phrases it (`L3Benchmark`,
 *  `L4Shock`, `L4Replay`, `L4Simulation`). The controller never reads the
 *  parameters; they are here so the two analyses sharing the `stress` code can be
 *  told apart on the wire. */
const QUESTIONS: Record<OnDemandAnalysis, {code: string; mode: RiskMode; parameters: RiskAnalyticParameters}> = {
    comparison: {code: 'comparison', mode: 'current_composition', parameters: {comparison_asset_id: 7}},
    stress: {code: 'stress', mode: 'current_composition', parameters: {method: 'hypothetical', dimension: 'asset_class', bucket_shocks: {STOCK: -0.2}}},
    replay: {code: 'stress', mode: 'current_composition', parameters: {method: 'historical_replay', replay_range: {start: '2020-02-19', end: '2020-03-23'}, missing_history_policy: 'manual_proxy_or_exclude', proxy_assets: [], excluded_assets: []}},
    simulation: {code: 'simulation', mode: 'current_composition', parameters: {horizon_days: 21, path_count: 500, random_seed: 11}},
};

const NONE_DISCARDED: Record<OnDemandAnalysis, boolean> = {comparison: false, stress: false, replay: false, simulation: false};

function answer(label: string): {items: {analytic_code: string}[]} {
    return {items: [{analytic_code: label}]};
}

/** The analysis a request was asked for, or `null` for the base wave: `runSingle`
 *  names every on-demand instance `single-<code>`, `buildBaseAnalytics` never does. */
function onDemandAnalysisOf(request: RiskQueryRequest): OnDemandAnalysis | null {
    const [analytic] = request.analytics;
    if (!analytic?.instance_id.startsWith('single-')) return null;
    if (analytic.analytic_code === 'comparison') return 'comparison';
    if (analytic.analytic_code === 'simulation') return 'simulation';
    // `L4Replay` asks a `stress` with a historical method: the code alone cannot tell it from a shock.
    const parameters = analytic.parameters as Record<string, unknown> | undefined;
    return parameters?.method === 'historical_replay' ? 'replay' : 'stress';
}

/**
 * Answers each analysis's questions from its own queue, in order, and records
 * them; the base wave that mounting fires is answered empty and never counted.
 *
 * A question past the end of its queue is rejected rather than answered, so a
 * controller that asks more often than a test allows is caught by the count and
 * never rescued by a reply nobody scripted.
 */
function scriptOnDemand(answers: Partial<Record<OnDemandAnalysis, Scripted[]>>) {
    const queues = {comparison: [...(answers.comparison ?? [])], stress: [...(answers.stress ?? [])], replay: [...(answers.replay ?? [])], simulation: [...(answers.simulation ?? [])]};
    const asked: Record<OnDemandAnalysis, {request: RiskQueryRequest; forced: boolean}[]> = {comparison: [], stress: [], replay: [], simulation: []};
    const waiters: {analysis: OnDemandAnalysis; count: number; resolve: () => void}[] = [];

    queryRisk.mockImplementation((request: RiskQueryRequest, force?: boolean) => {
        const analysis = onDemandAnalysisOf(request);
        if (analysis === null) return Promise.resolve({items: []});
        asked[analysis].push({request, forced: force === true});
        for (const waiter of waiters) if (waiter.analysis === analysis && asked[analysis].length >= waiter.count) waiter.resolve();
        const next = queues[analysis].shift();
        if (next === undefined) return Promise.reject(new Error(`${analysis} was asked ${asked[analysis].length} times; this test scripted fewer answers`));
        return next instanceof Error ? Promise.reject(next) : Promise.resolve(next);
    });

    return {
        asked: (analysis: OnDemandAnalysis) => asked[analysis],
        unused: (analysis: OnDemandAnalysis) => queues[analysis].length,
        /** Settles once `analysis` has been asked `count` times. Never alone: race it
         *  against the run, or a controller that stops asking hangs the test instead
         *  of failing it. */
        askedTimes: (analysis: OnDemandAnalysis, count: number) =>
            new Promise<void>((resolve) => {
                if (asked[analysis].length >= count) resolve();
                else waiters.push({analysis, count, resolve});
            }),
    };
}

function resultOf(controller: RiskPanelController, analysis: OnDemandAnalysis) {
    return {comparison: controller.comparisonResult, stress: controller.stressResult, replay: controller.replayResult, simulation: controller.simulationResult}[analysis];
}

function loadingOf(controller: RiskPanelController, analysis: OnDemandAnalysis): boolean {
    return {comparison: controller.comparisonLoading, stress: controller.stressLoading, replay: controller.replayLoading, simulation: controller.simulationLoading}[analysis];
}

// ----------------------------------------------------------------------
// Data-quality issues, shaped as `portfolio_engine.py` builds them in its
// data-quality report: the count is the length of the list the issue is
// about, and the CTA targets the first entry of that list.
// ----------------------------------------------------------------------

/** An issue as a result's report carries it, before `normalizeQualityIssue`. */
type RawQualityIssue = Parameters<typeof normalizeQualityIssue>[0];

type NamedAsset = readonly [id: number, name: string];

/** An issue as the controller hands it to the merge: normalized. */
function normalized(raw: RawQualityIssue): DataQualityIssue {
    return normalizeQualityIssue(raw);
}

function stalePriceIssue(assets: readonly NamedAsset[], overrides: Partial<RawQualityIssue> = {}): RawQualityIssue {
    return {
        domain: 'portfolio',
        code: 'STALE_PRICE',
        severity: 'warning',
        message_i18n_key: 'dataQuality.stalePrice',
        message_params: {count: assets.length},
        count: assets.length,
        affected_asset_ids: assets.map(([id]) => id),
        affected_asset_names: assets.map(([, name]) => name),
        cta_action: 'sync_asset_prices',
        cta_target: String(assets[0][0]),
        group_key: 'stale_price',
        ...overrides,
    };
}

/** Carries a parameter of its own beside the count: the date its positions are implied at. */
function transactionImpliedIssue(assets: readonly NamedAsset[], asOfDate: string): RawQualityIssue {
    return {
        domain: 'portfolio',
        code: 'TRANSACTION_IMPLIED',
        severity: 'warning',
        message_i18n_key: 'dataQuality.transactionImplied',
        message_params: {count: assets.length, as_of_date: asOfDate},
        count: assets.length,
        affected_asset_ids: assets.map(([id]) => id),
        affected_asset_names: assets.map(([, name]) => name),
        cta_action: 'navigate_asset',
        cta_target: String(assets[0][0]),
        group_key: 'transaction_implied',
    };
}

/** MISSING_FX_RATES for pairs a provider serves: its dates span what is missing across them. */
function missingFxRatesIssue(pairs: readonly string[], dates: {from: string; to: string; count: number}): RawQualityIssue {
    return {
        domain: 'portfolio',
        code: 'MISSING_FX_RATES',
        severity: 'warning',
        message_i18n_key: 'dataQuality.missingFxRates',
        message_params: {count: pairs.length, date_from: dates.from, date_to: dates.to, dates_count: dates.count},
        count: pairs.length,
        affected_fx_pairs: [...pairs],
        cta_action: 'sync_fx_pair',
        cta_target: pairs[0],
        group_key: 'missing_fx_rates',
    };
}

/** MISSING_FX_RATES for manual pairs: the same code, a group of its own, and no dates. */
function missingFxRatesManualIssue(pairs: readonly string[]): RawQualityIssue {
    return {
        domain: 'portfolio',
        code: 'MISSING_FX_RATES',
        severity: 'warning',
        message_i18n_key: 'dataQuality.missingFxRatesManual',
        message_params: {count: pairs.length},
        count: pairs.length,
        affected_fx_pairs: [...pairs],
        cta_action: 'navigate_fx',
        cta_target: pairs[0],
        group_key: 'missing_fx_rates_manual',
    };
}

/** About dates, not about assets or pairs: a count and a span, and no list. */
function navIncompleteIssue(dates: readonly string[]): RawQualityIssue {
    return {
        domain: 'portfolio',
        code: 'NAV_INCOMPLETE',
        severity: 'info',
        message_i18n_key: 'dataQuality.navIncomplete',
        message_params: {count: dates.length, date_from: dates[0], date_to: dates[dates.length - 1]},
        count: dates.length,
        group_key: 'nav_incomplete',
    };
}

/** No count, no list, no parameter. */
function mwrrNotCalculableIssue(): RawQualityIssue {
    return {domain: 'portfolio', code: 'MWRR_NOT_CALCULABLE', severity: 'info', message_i18n_key: 'dataQuality.mwrrNotAvailable', group_key: 'mwrr'};
}

/**
 * What every result of a Dashboard wave carries today: one portfolio over one window makes one report,
 * repeated on each analytic. Both groups of MISSING_FX_RATES, and two issues about no list at all.
 */
function dashboardReportIssues(): RawQualityIssue[] {
    return [
        stalePriceIssue([
            [11, 'Alpha'],
            [12, 'Beta'],
        ]),
        missingFxRatesIssue(['EUR-USD', 'EUR-GBP'], {from: '2025-03-03', to: '2025-03-14', count: 5}),
        missingFxRatesManualIssue(['CHF-EUR']),
        navIncompleteIssue(['2025-03-07', '2025-03-10', '2025-03-11']),
        mwrrNotCalculableIssue(),
    ];
}

/** A risk result whose data-quality report carries `issues`, as the risk API answers it. */
function resultWithIssues(analyticCode: string, issues: RawQualityIssue[]) {
    return {analytic_code: analyticCode, data_quality: {issues, data_quality_status: 'carried_forward'}};
}

/** Answers the base wave: the historical question with `historical`, the current-composition one with `current`. */
function answerBaseWave(historical: object[], current: object[]): void {
    queryRisk.mockImplementation((request: RiskQueryRequest) => Promise.resolve({items: request.mode === 'historical' ? historical : current}));
}

describe('riskPanelController', () => {
    beforeEach(() => {
        fetchRiskCatalog.mockReset().mockResolvedValue(CATALOG);
        fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
        queryRisk.mockReset().mockResolvedValue({items: []});
        invalidateRisk.mockReset();
        capability.supported = true;
    });

    it('does not touch its inputs while the host script is still running', () => {
        // A Svelte component declares its `$state` with `let`. Reading an input
        // during construction therefore lands in the temporal dead zone of any
        // binding declared below the call, and the ReferenceError does not show up
        // as a broken panel — it takes the whole page down. Measured once, for
        // real: it turned six green E2E tests red with `dashboard-risk-tab` simply
        // absent, which looks nothing like its cause.
        let reads = 0;
        const {stop} = effectRoot(() =>
            createRiskPanelController(() => {
                reads += 1;
                return defaultInputs();
            }),
        );

        expect(reads).toBe(0);
        stop();
    });

    it('runs effects at all — guards every negative assertion below', () => {
        expect(() => assertEffectsRun()).not.toThrow();
    });

    // ------------------------------------------------------------------
    // The defect this controller exists to prevent.
    // See LibreFolio_devWiki/concepts/discard-the-answer-not-the-question.md
    // ------------------------------------------------------------------
    it('re-issues an in-flight analysis when the signature moves under it', async () => {
        const {controller, inputs, stop} = mountController();
        const pending = deferred<{items: never[]}>();
        queryRisk.mockReturnValue(pending.promise);

        const launch = vi.fn(async () => {
            await controller.runGuarded('comparison', () => ({code: 'comparison', mode: 'historical', parameters: {comparison_asset_id: 7}}));
        });
        controller.registerLauncher('comparison', launch);

        void launch();
        flushSync();
        expect(controller.comparisonLoading).toBe(true);
        expect(launch).toHaveBeenCalledTimes(1);

        // The asset page resolves `targetCurrency` from a response that can land
        // *after* the user pressed the button. That is the whole scenario.
        inputs.targetCurrency = 'USD';
        flushSync();

        // The answer is discarded — it was computed for a currency that no longer
        // holds — but the question is not.
        expect(controller.comparisonResult).toBeNull();
        expect(launch).toHaveBeenCalledTimes(2);
        expect(controller.comparisonLoading).toBe(true);

        pending.resolve({items: []});
        stop();
    });

    it('does not mistake a reordered slice for a new question', async () => {
        // The signature is what decides whether an answer still holds. The request
        // canonicalizes its scope, so if the signature did not, an unordered slice
        // would look like a different question and discard answers that were still
        // valid — the same defect as above, entering through the scope instead of
        // through the dates.
        const {controller, inputs, stop} = mountController({...defaultInputs(), scope: portfolioSlice([9, 3])});
        const pending = deferred<{items: never[]}>();
        queryRisk.mockReturnValue(pending.promise);

        const launch = vi.fn(async () => {
            await controller.runGuarded('comparison', () => ({code: 'comparison', mode: 'historical', parameters: {comparison_asset_id: 7}}));
        });
        controller.registerLauncher('comparison', launch);

        void launch();
        flushSync();
        expect(launch).toHaveBeenCalledTimes(1);

        // The Dashboard derives the slice from the order of its holdings, and a
        // reload can return the same positions in a different order.
        inputs.scope = portfolioSlice([3, 9]);
        flushSync();
        expect(launch).toHaveBeenCalledTimes(1);
        expect(controller.comparisonLoading).toBe(true);

        // A genuinely different slice is a different question, and must still invalidate.
        inputs.scope = portfolioSlice([3, 10]);
        flushSync();
        expect(launch).toHaveBeenCalledTimes(2);

        pending.resolve({items: []});
        stop();
    });

    it('gives an unordered slice one identity, and two slices two', () => {
        const withScope = (scope: RiskControllerInputs['scope']) => baseSignature({...defaultInputs(), scope});

        expect(withScope(portfolioSlice([9, 3]))).toBe(withScope(portfolioSlice([3, 9])));
        expect(withScope(portfolioSlice([3, 9]))).not.toBe(withScope(portfolioSlice([3, 10])));
    });

    it('does not re-issue an analysis that was not running', () => {
        const {controller, inputs, stop} = mountController();
        const launch = vi.fn(async () => {});
        controller.registerLauncher('stress', launch);

        inputs.targetCurrency = 'USD';
        flushSync();

        expect(launch).not.toHaveBeenCalled();
        stop();
    });

    // The counterpart to the test above: `stress` is right not to be re-issued,
    // but a standing choice still has to learn that its answer was thrown away.
    it('counts a moved signature, so a standing analysis can re-ask itself', () => {
        const {controller, inputs, stop} = mountController();
        const first = controller.baseEpoch;

        inputs.targetCurrency = 'USD';
        flushSync();
        const afterMove = controller.baseEpoch;
        expect(afterMove).toBeGreaterThan(first);

        // Setting the same value again is not a new question, and a benchmark
        // that re-asked on every re-render would issue one request per keystroke
        // somewhere else on the page.
        inputs.targetCurrency = 'USD';
        flushSync();
        expect(controller.baseEpoch).toBe(afterMove);
        stop();
    });

    it('ignores a stale answer that lands after a newer run started', async () => {
        const {controller, stop} = mountController();
        const first = deferred<{items: {analytic_code: string}[]}>();
        const second = deferred<{items: {analytic_code: string}[]}>();
        queryRisk.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

        const build = () => ({code: 'stress', mode: 'current_composition' as const, parameters: {}});
        const runA = controller.runGuarded('stress', build);
        const runB = controller.runGuarded('stress', build);

        second.resolve({items: [{analytic_code: 'fresh'}]});
        await runB;
        first.resolve({items: [{analytic_code: 'stale'}]});
        await runA;

        expect(controller.stressResult).toEqual({analytic_code: 'fresh'});
        expect(controller.stressLoading).toBe(false);
        stop();
    });

    it('does not reload when the signature is unchanged', async () => {
        const {controller, inputs, stop} = mountController();
        await vi.waitFor(() => expect(controller.initialLoading).toBe(false));
        const callsAfterMount = queryRisk.mock.calls.length;

        // Presentation state moving must not invalidate data. Reopening a closed
        // accordion is not a reason to refetch.
        inputs.refreshVersion = 0;
        flushSync();

        expect(queryRisk.mock.calls.length).toBe(callsAfterMount);
        stop();
    });

    it('reloads when the refresh version is bumped', async () => {
        const {controller, inputs, stop} = mountController();
        await vi.waitFor(() => expect(controller.initialLoading).toBe(false));
        const callsAfterMount = queryRisk.mock.calls.length;

        inputs.refreshVersion = 1;
        flushSync();
        await vi.waitFor(() => expect(queryRisk.mock.calls.length).toBeGreaterThan(callsAfterMount));
        stop();
    });

    it('separates a catalog that failed from one that is merely slow', async () => {
        const {controller, stop} = mountController();
        expect(controller.catalogState).toBe('pending');

        fetchRiskCatalog.mockResolvedValue(null);
        await controller.loadBase(true);

        expect(controller.catalogState).toBe('error');
        expect(controller.loadError).toBe(true);
        stop();
    });

    // ------------------------------------------------------------------
    // The same repair, one level down: `queryRisk` answers in three ways — a
    // response, a throw, and a *discard* (null, when the client session or the
    // cache generation moved while the request was in flight). `?? []` folded the
    // third into the first, which states something about the world when the fact
    // is about this client. See riskStore.test.ts, 'discards an answer to a
    // question asked before the identity existed', for where that null is born.
    // ------------------------------------------------------------------
    it('re-asks a question whose answer was discarded, instead of showing an empty result', async () => {
        // Why 'ignores a stale answer that lands after a newer run started' and
        // 'does not reload when the signature is unchanged' both passing was never
        // enough, and why neither of them is wrong: the first says an answer whose
        // question moved must be dropped, the second says a question that has not
        // moved must not be re-asked. Both correct, and on a page reload their
        // combination is a screen that lies — the answer is dropped by the guard,
        // the signature never moves afterwards, so nothing ever asks again and the
        // empty state is permanent. The missing party is the one that notices the
        // discard and re-asks once, under the generation that caused it.
        const {controller, stop} = mountController();

        // One base load asks two questions in a single Promise.all — historical and
        // current_composition — so the unit of discard is a wave, not a call. In the
        // real defect both are discarded together: both were in flight when the
        // first `/auth/me` landed, so both captured the same session generation.
        const questionsPerWave = 2;
        let asked = 0;
        queryRisk.mockImplementation((request: {mode: string}) => {
            asked += 1;
            if (asked <= questionsPerWave) return Promise.resolve(null);
            return Promise.resolve({items: [{analytic_code: request.mode === 'historical' ? 'historical_kpi' : 'risk_contribution'}]});
        });

        await controller.loadBase(false);

        expect(controller.historicalResults, 'a discarded answer was folded into "no data" again: a complete response renders as an empty panel, and no signature change follows a reload to shake it loose').toEqual([{analytic_code: 'historical_kpi'}]);
        expect(controller.currentResults, 'only half the wave was recovered, so the panel would show historical figures beside an empty composition it never failed to compute').toEqual([{analytic_code: 'risk_contribution'}]);
        expect(asked, 'the discarded wave was not re-asked exactly once: either the controller gave up on a healthy answer, or it asked more times than the bound allows').toBe(2 * questionsPerWave);
        expect(controller.loadDiscarded, 'a load that recovered still reports itself discarded, so a surface reading the flag would offer a retry for data it already has').toBe(false);
        expect(controller.loadError, 'a discard was reported as a failure; nothing failed, and the user would be asked to retry something that never broke').toBe(false);
        stop();
    });

    it('separates an answer that was discarded from one that came back empty', async () => {
        // The counterpart to the test above, and the reason `loadDiscarded` exists at
        // all: when the re-ask is discarded too, the honest report is "your answer was
        // thrown away", which is neither an error nor an absence of data. Surrendering
        // in silence is what produced the original defect; surrendering out loud is a
        // state a surface can act on.
        const {controller, stop} = mountController();

        let asked = 0;
        queryRisk.mockImplementation(() => {
            asked += 1;
            return Promise.resolve(null);
        });

        await controller.loadBase(false);

        expect(controller.loadDiscarded, 'a load whose answer was discarded twice running says nothing about it, so an empty panel is indistinguishable from a portfolio with no data').toBe(true);
        expect(controller.loadError, 'a discard was promoted to a failure; nothing failed, and an error banner would describe a breakage that did not happen').toBe(false);
        expect(controller.historicalResults, 'an answer that was never accepted was filed as a result, which asserts an empty portfolio on the strength of a request this client threw away').toEqual([]);
        expect(controller.currentResults, 'same for the current-composition half of the wave: a discard is not a measurement').toEqual([]);
        expect(asked, 'the re-ask is not bounded at one retry: a session generation that keeps moving would spin here instead of surrendering, or the second discard was never attempted').toBe(4);
        expect(controller.initialLoading, 'the panel is still spinning after the controller gave up, so the discard it just recorded can never be rendered').toBe(false);
        stop();
    });

    it('refreshes in place instead of blanking once results exist', async () => {
        const {controller, stop} = mountController();
        queryRisk.mockResolvedValue({items: [{analytic_code: 'historical_kpi'}]});
        await controller.loadBase(false);
        expect(controller.historicalResults.length).toBe(1);

        const slow = deferred<{items: never[]}>();
        queryRisk.mockReturnValue(slow.promise);
        const reload = controller.loadBase(true);

        expect(controller.refreshing).toBe(true);
        expect(controller.initialLoading).toBe(false);

        slow.resolve({items: []});
        await reload;
        expect(controller.refreshing).toBe(false);
        stop();
    });

    it('drops every on-demand result after a sync, then reloads the base wave', async () => {
        const {controller, stop} = mountController();
        controller.setResult('simulation', {analytic_code: 'simulation'} as never);
        expect(controller.simulationResult).not.toBeNull();

        await controller.handleSynced();

        expect(invalidateRisk).toHaveBeenCalledTimes(1);
        expect(controller.simulationResult).toBeNull();
        stop();
    });

    it('asks for the scenario catalog once, however often it is requested', async () => {
        const {controller, stop} = mountController();
        await Promise.all([controller.loadScenarioCatalog(), controller.loadScenarioCatalog()]);
        await controller.loadScenarioCatalog();

        expect(fetchRiskScenarioCatalog).toHaveBeenCalledTimes(1);
        stop();
    });

    // ------------------------------------------------------------------
    // The same repair once more, on the path the reader launches by hand.
    // `runSingle` folded the discard into "no result" (`response?.items?.[0] ??
    // null`) and `runGuarded` stored it, so a comparison, a shock, a replay or a
    // simulation whose answer was thrown away simply vanished: the spinner
    // stopped, nothing rendered, and no sentence said why. Live polling on Asset
    // Global's Correlation tab (D11) discards in-flight answers every 30 s, which
    // turns that from a rare state into a routine one.
    //
    // The contract these tests hold: a discard under a generation that still
    // holds is re-asked once, with the same request; a second discard is said
    // out loud through `discarded.<analysis>` — neither an error nor an empty
    // answer; a discard under a generation that moved is dropped like any stale
    // answer, with no re-ask and no flag.
    // ------------------------------------------------------------------
    describe('an on-demand answer that was discarded', () => {
        it.each(ON_DEMAND_ANALYSES)('re-asks a discarded %s question once, with the same request, and shows the second answer', async (analysis) => {
            const {controller, stop} = mountController();
            const second = answer(`${analysis} second answer`);
            const script = scriptOnDemand({[analysis]: [null, second]});
            const build = vi.fn(() => QUESTIONS[analysis]);

            await controller.runGuarded(analysis, build);

            expect(resultOf(controller, analysis), 'the discard was stored as "no result": the run ends with no figure, no spinner and no sentence, and nothing ever asks again').toEqual(second.items[0]);
            expect(script.asked(analysis), 'the discarded question was not re-asked exactly once').toHaveLength(2);
            expect(build, 'the re-ask rebuilt the question instead of repeating the one whose answer was discarded').toHaveBeenCalledTimes(1);
            expect(script.asked(analysis)[1], 'the re-ask is not the question that was discarded (request or cache policy differ)').toEqual(script.asked(analysis)[0]);
            expect(loadingOf(controller, analysis), 'the spinner outlived the answer it was waiting for').toBe(false);
            expect(controller.discarded[analysis], 'a run that recovered still reports its answer discarded, so the level would offer a retry for a result already on screen').toBe(false);
            stop();
        });

        it.each(ON_DEMAND_ANALYSES)('says so when a %s answer is discarded twice running, and stops asking', async (analysis) => {
            const {controller, stop} = mountController();
            // An older answer is on screen: after two discards it must not stand under the new question.
            controller.setResult(analysis, answer(`${analysis} previous answer`).items[0] as never);
            const script = scriptOnDemand({[analysis]: [null, null, answer(`${analysis} third answer`)]});

            await controller.runGuarded(analysis, () => QUESTIONS[analysis]);

            expect(script.asked(analysis), 'the re-ask is not bounded at one: either the second discard was never re-asked, or a generation that keeps moving would spin here instead of surrendering').toHaveLength(2);
            expect(script.unused(analysis), 'a third answer was consumed').toBe(1);
            expect(resultOf(controller, analysis), 'an answer that was never accepted is on screen: the older answer survived under the new question, or a discard was filed as a result').toBeNull();
            expect(loadingOf(controller, analysis), 'the level is still spinning after the controller gave up, so the discard can never be rendered').toBe(false);
            expect(controller.discarded[analysis], 'an answer discarded twice running disappears in silence: the reader sees an empty level and no reason to ask again').toBe(true);
            stop();
        });

        it('takes an answer that came back empty for an answer: no re-ask, no discard', async () => {
            const {controller, stop} = mountController();
            const script = scriptOnDemand({simulation: [{items: []}, answer('simulation never asked')]});

            await controller.runGuarded('simulation', () => QUESTIONS.simulation);

            expect(script.asked('simulation'), 'an empty answer was mistaken for a discard and asked again').toHaveLength(1);
            expect(controller.simulationResult).toBeNull();
            expect(controller.simulationLoading).toBe(false);
            expect(controller.discarded.simulation, 'an empty answer was reported as discarded, so the level would promise a retry that can only return the same nothing').toBe(false);
            stop();
        });

        it('drops a discard whose run was superseded by a newer run, without re-asking it', async () => {
            const {controller, stop} = mountController();
            const stale = deferred<OnDemandAnswer>();
            const fresh = deferred<OnDemandAnswer>();
            const script = scriptOnDemand({comparison: [stale.promise, fresh.promise]});
            const build = () => QUESTIONS.comparison;

            const older = controller.runGuarded('comparison', build);
            const newer = controller.runGuarded('comparison', build);

            stale.resolve(null);
            await older;
            expect(script.asked('comparison'), 'a superseded run re-asked a question nobody is waiting for any more').toHaveLength(2);
            expect(controller.comparisonLoading, "the stale run switched off the newer run's spinner").toBe(true);
            expect(controller.comparisonResult).toBeNull();

            const current = answer('comparison newer answer');
            fresh.resolve(current);
            await newer;
            expect(controller.comparisonResult, "the newer run's answer is not the one on screen").toEqual(current.items[0]);
            expect(script.asked('comparison')).toHaveLength(2);
            expect(controller.comparisonLoading).toBe(false);
            expect(controller.discarded.comparison, 'a discard nobody was waiting for is reported over the run that superseded it').toBe(false);
            stop();
        });

        it('drops a stale discard that lands after the newer run already answered', async () => {
            const {controller, stop} = mountController();
            const stale = deferred<OnDemandAnswer>();
            const fresh = deferred<OnDemandAnswer>();
            const script = scriptOnDemand({comparison: [stale.promise, fresh.promise]});
            const build = () => QUESTIONS.comparison;

            const older = controller.runGuarded('comparison', build);
            const newer = controller.runGuarded('comparison', build);

            const current = answer('comparison newer answer');
            fresh.resolve(current);
            await newer;
            stale.resolve(null);
            await older;

            expect(controller.comparisonResult, 'a stale discard blanked the answer of the run that superseded it').toEqual(current.items[0]);
            expect(script.asked('comparison'), 'a superseded run re-asked a question nobody is waiting for any more').toHaveLength(2);
            expect(controller.comparisonLoading).toBe(false);
            expect(controller.discarded.comparison, 'a stale discard raised the flag beside a fresh answer').toBe(false);
            stop();
        });

        it.each<[string, (mounted: Mounted) => void]>([
            ['resetAnalysis', ({controller}) => controller.resetAnalysis('replay')],
            ['bumpGeneration', ({controller}) => controller.bumpGeneration('replay')],
            [
                'a signature move',
                ({inputs}) => {
                    inputs.targetCurrency = 'USD';
                    flushSync();
                },
            ],
        ])('drops a discard whose question was withdrawn by %s while it was in flight', async (_how, withdraw) => {
            const mounted = mountController();
            const {controller, stop} = mounted;
            const pending = deferred<OnDemandAnswer>();
            const script = scriptOnDemand({replay: [pending.promise]});

            const run = controller.runGuarded('replay', () => QUESTIONS.replay);
            withdraw(mounted);
            pending.resolve(null);
            await run;

            expect(script.asked('replay'), 'a withdrawn question was asked again: its answer could only land under a question that has since changed').toHaveLength(1);
            expect(controller.replayResult).toBeNull();
            expect(controller.discarded.replay, 'the discard of a withdrawn question is reported, so the level would call a change the reader made a lost answer').toBe(false);
            stop();
        });

        it.each<[string, OnDemandAnswer]>([
            ['is discarded again', null],
            ['comes back', answer('stress answer to a withdrawn re-ask')],
        ])('drops a re-ask whose question was withdrawn while it was in flight, when it %s', async (_outcome, reAnswer) => {
            const {controller, stop} = mountController();
            const reAsk = deferred<OnDemandAnswer>();
            const script = scriptOnDemand({stress: [null, reAsk.promise]});

            const run = controller.runGuarded('stress', () => QUESTIONS.stress);
            // Settles on the re-ask, or on the run if the controller never re-asks.
            await Promise.race([script.askedTimes('stress', 2), run]);
            expect(script.asked('stress'), 'precondition: the discarded question was re-asked').toHaveLength(2);
            expect(controller.stressLoading, 'the spinner stopped between the discard and its re-ask, so the run blinks off while it is still running').toBe(true);

            controller.resetAnalysis('stress');
            reAsk.resolve(reAnswer);
            await run;

            expect(script.asked('stress'), 'a withdrawn re-ask was asked a third time').toHaveLength(2);
            expect(controller.stressResult, 'the answer to a withdrawn question landed on screen').toBeNull();
            expect(controller.stressLoading).toBe(false);
            expect(controller.discarded.stress, 'the re-ask of a withdrawn question was reported as discarded').toBe(false);
            stop();
        });

        it('clears the discard as soon as the same analysis is asked again', async () => {
            const {controller, stop} = mountController();
            const retry = deferred<OnDemandAnswer>();
            const script = scriptOnDemand({simulation: [null, null, retry.promise]});
            const build = () => QUESTIONS.simulation;

            await controller.runGuarded('simulation', build);
            expect(controller.discarded.simulation, 'precondition: two discards running are reported').toBe(true);

            const rerun = controller.runGuarded('simulation', build);
            expect(controller.discarded.simulation, 'the sentence about the old answer stays on screen while the new question is in flight').toBe(false);
            expect(controller.simulationLoading).toBe(true);

            const fresh = answer('simulation fresh answer');
            retry.resolve(fresh);
            await rerun;
            expect(controller.simulationResult).toEqual(fresh.items[0]);
            expect(controller.discarded.simulation).toBe(false);
            expect(script.asked('simulation')).toHaveLength(3);
            stop();
        });

        it('keeps the discard when a run is declined before it asks anything', async () => {
            // `build` returning null declines the run "without touching any state"
            // (runGuarded's own contract): no question left, so nothing happened
            // that could replace the sentence about the one that was thrown away.
            const {controller, stop} = mountController();
            const script = scriptOnDemand({comparison: [null, null]});

            await controller.runGuarded('comparison', () => QUESTIONS.comparison);
            expect(controller.discarded.comparison, 'precondition: two discards running are reported').toBe(true);

            await controller.runGuarded('comparison', () => null);

            expect(script.asked('comparison')).toHaveLength(2);
            expect(controller.discarded.comparison, 'a declined run erased the sentence about an answer it never replaced').toBe(true);
            stop();
        });

        it('forgets the discard of the analysis that is reset, and only that one', async () => {
            const {controller, stop} = mountController();
            scriptOnDemand({stress: [null, null], replay: [null, null]});
            await controller.runGuarded('stress', () => QUESTIONS.stress);
            await controller.runGuarded('replay', () => QUESTIONS.replay);
            expect(controller.discarded, 'precondition: both analyses were discarded twice running').toEqual({...NONE_DISCARDED, stress: true, replay: true});

            controller.resetAnalysis('stress');

            expect(controller.discarded, 'resetting one analysis left its discard on screen, or erased the discard of another').toEqual({...NONE_DISCARDED, replay: true});
            stop();
        });

        it.each<[string, (mounted: Mounted) => Promise<void>]>([
            [
                'the signature moves',
                async ({inputs}) => {
                    inputs.targetCurrency = 'USD';
                    flushSync();
                },
            ],
            ['a sync completes', async ({controller}) => controller.handleSynced()],
        ])('forgets every discard when %s', async (_when, move) => {
            const mounted = mountController();
            const {controller, stop} = mounted;
            scriptOnDemand({comparison: [null, null], stress: [null, null], replay: [null, null], simulation: [null, null]});
            for (const analysis of ON_DEMAND_ANALYSES) await controller.runGuarded(analysis, () => QUESTIONS[analysis]);
            expect(controller.discarded, 'precondition: every analysis was discarded twice running').toEqual({comparison: true, stress: true, replay: true, simulation: true});

            await move(mounted);

            expect(controller.discarded, 'a discard outlived the question it was about: the level would say an answer was lost for a question nobody is asking any more').toEqual(NONE_DISCARDED);
            stop();
        });

        it('neither asks nor reports a discard when the analytic is not supported here', async () => {
            const {controller, stop} = mountController();
            controller.setResult('stress', answer('stress previous answer').items[0] as never);
            const script = scriptOnDemand({stress: [answer('stress never asked')]});
            capability.supported = false;

            await controller.runGuarded('stress', () => QUESTIONS.stress);

            expect(script.asked('stress'), 'an analytic this scope does not support was put on the wire').toHaveLength(0);
            expect(controller.stressResult, 'an answer from before stands under a question that cannot be asked here').toBeNull();
            expect(controller.stressLoading).toBe(false);
            expect(controller.discarded.stress, '"not supported here" was reported as a discarded answer, promising a retry that cannot succeed').toBe(false);
            stop();
        });

        it.each<[string, Scripted[]]>([
            ['on the first ask', [new Error('synthetic calculation failure')]],
            ['on the re-ask after a discard', [null, new Error('synthetic calculation failure')]],
        ])('reports a failure %s as a failure, not as a discard', async (_when, answers) => {
            const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
            onTestFinished(() => consoleError.mockRestore());
            const {controller, stop} = mountController();
            controller.setResult('replay', answer('replay previous answer').items[0] as never);
            const script = scriptOnDemand({replay: answers});

            await controller.runGuarded('replay', () => QUESTIONS.replay);

            expect(script.asked('replay'), 'a failure was asked again, or the discard before it was not').toHaveLength(answers.length);
            expect(controller.replayResult, 'an answer from before survived a run that failed').toBeNull();
            expect(consoleError, 'the failure no longer reaches the console').toHaveBeenCalled();
            expect(controller.replayLoading).toBe(false);
            expect(controller.discarded.replay, 'a failure was reported as a discarded answer: nothing was thrown away, the calculation broke').toBe(false);
            stop();
        });

        it('keeps each analysis its own discard: a replay thrown away says nothing about the shock', async () => {
            // Replay and shock share the `stress` code, so a flag keyed by the code
            // rather than by the analysis would pass every other test in this block.
            const {controller, stop} = mountController();
            const shock = answer('stress shock answer');
            const script = scriptOnDemand({replay: [null, null], stress: [shock]});

            await Promise.all([controller.runGuarded('replay', () => QUESTIONS.replay), controller.runGuarded('stress', () => QUESTIONS.stress)]);

            expect(script.asked('replay'), 'the discarded replay was not re-asked exactly once').toHaveLength(2);
            expect(controller.stressResult, "the shock's answer was lost to the replay's discard").toEqual(shock.items[0]);
            expect(controller.discarded, 'a discard was reported on an analysis that answered, or on one that never ran').toEqual({...NONE_DISCARDED, replay: true});
            stop();
        });

        it('publishes no discard before anything was asked', () => {
            const {controller, stop} = mountController();
            expect(controller.discarded).toEqual(NONE_DISCARDED);
            stop();
        });

        it('publishes the discard reactively, so the level that reads it re-renders', async () => {
            const {controller, stop} = mountController();
            scriptOnDemand({comparison: [null, null]});
            const reads = recordReads(() => controller.discarded.comparison);
            expect(reads.values, 'precondition: the flag is readable from an effect').toEqual([false]);

            await controller.runGuarded('comparison', () => QUESTIONS.comparison);
            flushSync();

            expect(reads.values.at(-1), 'the flag flipped but no effect reading it re-ran: a level deriving its sentence from it would never show it').toBe(true);
            reads.stop();
            stop();
        });
    });

    // ------------------------------------------------------------------
    // The list the data-quality banner renders. `dataQualityIssues` is
    // `mergeQualityIssues` over the normalized issues of every result, in
    // result order: the base wave, then the four on-demand answers. It used
    // to deduplicate by code and lists, so one code and group reached the
    // banner once per distinct list, and the banner keys its rows by code and
    // group: Svelte's `each_key_duplicate`.
    // ------------------------------------------------------------------
    describe('the data-quality list the banner renders', () => {
        it('merges one STALE_PRICE carried by two results into one item: [1, 2] and [2, 3] become [1, 2, 3], counted 3', async () => {
            const {controller, stop} = mountController();
            answerBaseWave(
                [
                    resultWithIssues('historical_kpi', [
                        stalePriceIssue([
                            [1, 'Alpha'],
                            [2, 'Beta'],
                        ]),
                    ]),
                ],
                [
                    resultWithIssues('risk_contribution', [
                        stalePriceIssue([
                            [2, 'Beta'],
                            [3, 'Gamma'],
                        ]),
                    ]),
                ],
            );

            await controller.loadBase(false);

            // Precondition: both reports reached the list, so a red below is the merge and not the plumbing.
            expect(controller.historicalResults.map((result) => result.analytic_code)).toEqual(['historical_kpi']);
            expect(controller.currentResults.map((result) => result.analytic_code)).toEqual(['risk_contribution']);
            expect(new Set(controller.dataQualityIssues.flatMap((issue) => issue.affected_asset_ids ?? [])), 'the issues of both reports did not reach the list').toEqual(new Set([1, 2, 3]));

            expect(controller.dataQualityIssues, 'one code and group reached the banner more than once: its rows, keyed by code and group, throw each_key_duplicate').toEqual([
                expect.objectContaining({
                    code: 'STALE_PRICE',
                    group_key: 'stale_price',
                    affected_asset_ids: [1, 2, 3],
                    affected_asset_names: ['Alpha', 'Beta', 'Gamma'],
                    count: 3,
                    message_params: {count: 3},
                    // The historical result comes first in result order, so its issue is the first one.
                    cta_target: '1',
                }),
            ]);
            stop();
        });

        it("keeps the Dashboard's list as it is today when every result carries the same report", async () => {
            const {controller, stop} = mountController();
            const historicalCodes = ['historical_kpi', 'correlation', 'historical_var', 'drawdown_summary'];
            answerBaseWave(
                historicalCodes.map((code) => resultWithIssues(code, dashboardReportIssues())),
                [resultWithIssues('risk_contribution', dashboardReportIssues())],
            );

            await controller.loadBase(false);

            expect(
                controller.historicalResults.map((result) => result.analytic_code),
                'precondition: the historical half of the wave reached the controller',
            ).toEqual(historicalCodes);
            expect(
                controller.currentResults.map((result) => result.analytic_code),
                'precondition: the current-composition half of the wave reached the controller',
            ).toEqual(['risk_contribution']);
            expect(controller.dataQualityIssues, 'the Dashboard banner changed: the issues every result carries no longer come out once each, as they went in').toEqual(dashboardReportIssues().map(normalized));
            stop();
        });
    });
});

describe('discardedErrorCodes', () => {
    const L3: readonly OnDemandAnalysis[] = ['comparison'];
    const L4: readonly OnDemandAnalysis[] = ['stress', 'replay', 'simulation'];

    it('is keyed by the code RiskLevelSection words as risk.errors.answer_discarded', () => {
        expect(ANSWER_DISCARDED_CODE).toBe('answer_discarded');
    });

    it.each<[string, Record<OnDemandAnalysis, boolean>, readonly OnDemandAnalysis[], string[]]>([
        ['nothing when nothing is discarded', NONE_DISCARDED, L4, []],
        ['the code when one listed analysis is discarded', {...NONE_DISCARDED, replay: true}, L4, ['answer_discarded']],
        ['the code once when two listed analyses are discarded', {...NONE_DISCARDED, stress: true, simulation: true}, L4, ['answer_discarded']],
        ['nothing when only an analysis the level does not show is discarded', {...NONE_DISCARDED, comparison: true}, L4, []],
        ["the code for L3's comparison", {...NONE_DISCARDED, comparison: true}, L3, ['answer_discarded']],
    ])('returns %s', (_title, discarded, analyses, expected) => {
        expect(discardedErrorCodes(discarded, analyses)).toEqual(expected);
    });

    it('wires every on-demand analysis into exactly one level: the comparison under L3, the what-if steps under L4', () => {
        const wired = [...LEVEL_ON_DEMAND_ANALYSES.l3, ...LEVEL_ON_DEMAND_ANALYSES.l4];
        expect(new Set(wired).size, 'an analysis is wired into two levels, so its discard would be disclosed twice').toBe(wired.length);
        expect([...wired].sort(), 'an on-demand analysis is wired into no level, so its discarded answer would vanish in silence again').toEqual([...ON_DEMAND_ANALYSES].sort());
        expect(LEVEL_ON_DEMAND_ANALYSES.l3, 'the benchmark comparison is not disclosed under L3, where its figures are').toEqual(['comparison']);
        expect(new Set(LEVEL_ON_DEMAND_ANALYSES.l4), 'the what-if steps are not the analyses disclosed under L4').toEqual(new Set(['stress', 'replay', 'simulation']));
    });
});

// ----------------------------------------------------------------------
// One merge for the data-quality banner — the owner's contract (05/10).
// The banner keys its rows by code and group, so one code and group must
// reach it once, whatever windows and sets the issues came from; the Asset
// Global lab asks about several, and workstream F merges the issues of its
// four controllers with this same function.
// ----------------------------------------------------------------------
describe('mergeQualityIssues', () => {
    const keyOf = (issue: DataQualityIssue): string => `${issue.code}/${issue.group_key ?? ''}`;

    /** The one item that issues of one code and group merge into; fails, listing what came out, otherwise. */
    const onlyItem = (merged: DataQualityIssue[]): DataQualityIssue => {
        expect(merged.map(keyOf), 'one code and group make one item').toHaveLength(1);
        return merged[0];
    };

    it('keys an issue by its code and its group, in order of first appearance, and passes an issue met once through as it is', () => {
        const fxRates = normalized(missingFxRatesIssue(['EUR-USD'], {from: '2025-03-03', to: '2025-03-07', count: 3}));
        const fxManual = normalized(missingFxRatesManualIssue(['CHF-EUR']));
        const nav = normalized(navIncompleteIssue(['2025-03-10']));

        const merged = mergeQualityIssues([normalized(stalePriceIssue([[1, 'Alpha']])), fxRates, normalized(stalePriceIssue([[2, 'Beta']])), fxManual, nav]);

        expect(merged.map(keyOf), 'not one item per code and group, in the order each first appeared').toEqual(['STALE_PRICE/stale_price', 'MISSING_FX_RATES/missing_fx_rates', 'MISSING_FX_RATES/missing_fx_rates_manual', 'NAV_INCOMPLETE/nav_incomplete']);
        expect(merged.slice(1), 'an issue whose code and group appear once was changed on its way through').toEqual([fxRates, fxManual, nav]);
    });

    it('keeps one code apart under two groups, even over the same pairs: MISSING_FX_RATES for provider pairs and for manual ones', () => {
        const provider = normalized(missingFxRatesIssue(['EUR-USD'], {from: '2025-03-03', to: '2025-03-07', count: 3}));
        const manual = normalized(missingFxRatesManualIssue(['EUR-USD']));

        expect(mergeQualityIssues([provider, manual]), 'two groups of one code were merged, or told apart by their lists: one of the two sentences would be lost').toEqual([provider, manual]);
    });

    it('takes a missing group, a null one and an empty one for the same group, as the banner does', () => {
        // The banner keys a row by `code + (group_key ?? '')`: the three spellings make one key there, so
        // they must make one item here, or the banner throws each_key_duplicate.
        const withoutGroup = normalized(stalePriceIssue([[1, 'Alpha']]));
        delete withoutGroup.group_key;
        const merged = mergeQualityIssues([withoutGroup, {...normalized(stalePriceIssue([[2, 'Beta']])), group_key: null}, {...normalized(stalePriceIssue([[3, 'Gamma']])), group_key: ''}]);

        expect(merged.map((issue) => issue.affected_asset_ids)).toEqual([[1, 2, 3]]);
    });

    it('unions the affected assets in order of first appearance, each name staying with its id — the first name seen for an id wins', () => {
        const merged = mergeQualityIssues([
            normalized(
                stalePriceIssue([
                    [2, 'Beta'],
                    [1, 'Alpha'],
                ]),
            ),
            normalized(
                stalePriceIssue([
                    [3, 'Gamma'],
                    [2, 'Beta, renamed'],
                ]),
            ),
            normalized(
                stalePriceIssue([
                    [1, 'Alpha, renamed'],
                    [4, 'Delta'],
                ]),
            ),
        ]);

        expect(merged, 'one code and group make one item').toHaveLength(1);
        expect(merged[0].affected_asset_ids, 'the ids are not their union in order of first appearance').toEqual([2, 1, 3, 4]);
        expect(merged[0].affected_asset_names, 'a name left its id, or a later name replaced the first one seen').toEqual(['Beta', 'Alpha', 'Gamma', 'Delta']);
        expect(merged[0].count, 'the count is not the size of the union').toBe(4);
        expect(merged[0].message_params, 'the count the sentence shows is not the size of the union').toEqual({count: 4});
    });

    it("names an id that comes without a name '#<id>', the replay block's fallback, keeping every name beside its id", () => {
        // Each issue lists two ids and names only the first. The backend's lists always align; a merge
        // across controllers must not shift a name onto the wrong id when one does not.
        const merged = onlyItem(mergeQualityIssues([normalized({...stalePriceIssue([[1, 'Alpha']]), affected_asset_ids: [1, 2], affected_asset_names: ['Alpha']}), normalized({...stalePriceIssue([[3, 'Gamma']]), affected_asset_ids: [3, 4], affected_asset_names: ['Gamma']})]));

        expect(merged.affected_asset_ids, 'precondition: the ids are their union').toEqual([1, 2, 3, 4]);
        expect(merged.affected_asset_names, "an id no issue names is not called '#<id>', or a name left its id").toEqual(['Alpha', '#2', 'Gamma', '#4']);
    });

    it("lets a later real name replace a missing one, even after the merge has stood in '#<id>' for it", () => {
        const unnamedTwo = (): DataQualityIssue =>
            normalized({
                ...stalePriceIssue([
                    [1, 'Alpha'],
                    [2, 'Beta'],
                ]),
                affected_asset_names: ['Alpha'],
            });
        // Two issues: the second names the id the first left unnamed.
        const two = onlyItem(mergeQualityIssues([unnamedTwo(), normalized(stalePriceIssue([[2, 'Beta']]))]));
        // Three: one in between names something else, so the merge has had to stand in '#2' for the
        // missing name before the real one arrives.
        const three = onlyItem(mergeQualityIssues([unnamedTwo(), normalized(stalePriceIssue([[3, 'Gamma']])), normalized(stalePriceIssue([[2, 'Beta']]))]));

        expect(two.affected_asset_names, 'a later real name did not replace the missing one').toEqual(['Alpha', 'Beta']);
        expect(three.affected_asset_ids, 'precondition: the ids are their union').toEqual([1, 2, 3]);
        expect(three.affected_asset_names, "the stand-in '#2' was kept as if it were a name: once a merge has filled it, a later real name no longer replaces it").toEqual(['Alpha', 'Beta', 'Gamma']);
    });

    it('unions the affected pairs in order of first appearance, and counts the pairs', () => {
        const merged = mergeQualityIssues([normalized(missingFxRatesManualIssue(['EUR-USD', 'EUR-GBP'])), normalized(missingFxRatesManualIssue(['EUR-GBP', 'CHF-EUR']))]);

        expect(merged).toEqual([expect.objectContaining({affected_fx_pairs: ['EUR-USD', 'EUR-GBP', 'CHF-EUR'], count: 3, message_params: {count: 3}})]);
    });

    it('counts the pairs, not the assets, when the merged issue carries pairs', () => {
        const withAssets = (raw: RawQualityIssue, ids: number[]): DataQualityIssue => normalized({...raw, affected_asset_ids: ids, affected_asset_names: ids.map((id) => `Asset ${id}`)});

        const merged = mergeQualityIssues([withAssets(missingFxRatesManualIssue(['EUR-USD', 'EUR-GBP']), [1]), withAssets(missingFxRatesManualIssue(['EUR-GBP']), [2, 3])]);

        expect(merged, 'one code and group make one item').toHaveLength(1);
        // Precondition: the two unions differ in size, or this could not tell which one is counted.
        expect(merged[0].affected_asset_ids).toEqual([1, 2, 3]);
        expect(merged[0].affected_fx_pairs).toEqual(['EUR-USD', 'EUR-GBP']);
        expect(merged[0].count, 'an issue about pairs was counted by its assets').toBe(2);
        expect(merged[0].message_params?.count, 'an issue about pairs was counted by its assets').toBe(2);
    });

    it('invents no list that no merged issue has, and takes the list of the one issue that has it', () => {
        const stale = onlyItem(mergeQualityIssues([normalized(stalePriceIssue([[1, 'Alpha']])), normalized(stalePriceIssue([[2, 'Beta']]))]));
        const manual = onlyItem(mergeQualityIssues([normalized(missingFxRatesManualIssue(['EUR-USD'])), normalized(missingFxRatesManualIssue(['CHF-EUR']))]));
        // Pairs in the first issue only, assets in the second only.
        const assetsOnly = normalized({...missingFxRatesManualIssue(['EUR-USD']), affected_fx_pairs: undefined, affected_asset_ids: [7, 8], affected_asset_names: ['Eta', 'Theta']});
        const mixed = onlyItem(mergeQualityIssues([normalized(missingFxRatesManualIssue(['EUR-GBP'])), assetsOnly]));

        expect(stale.affected_asset_ids, 'precondition: the two stale prices merged').toEqual([1, 2]);
        expect(stale.affected_fx_pairs, 'a pair list was invented for issues that list no pair').toBeUndefined();
        expect(manual.affected_fx_pairs, 'precondition: the two manual-rate issues merged').toEqual(['EUR-USD', 'CHF-EUR']);
        expect(manual.affected_asset_ids, 'an asset list was invented for issues that list no asset').toBeUndefined();
        expect(manual.affected_asset_names, 'a name list was invented for issues that name nothing').toBeUndefined();
        expect(mixed.affected_fx_pairs, 'the pairs only the first issue lists are not the merged pairs').toEqual(['EUR-GBP']);
        expect(mixed.affected_asset_ids, 'the assets only the second issue lists are not the merged assets').toEqual([7, 8]);
        expect(mixed.affected_asset_names, 'the names only the second issue gives are not the merged names').toEqual(['Eta', 'Theta']);
    });

    it.each<[string, DataQualityIssue['severity'][], DataQualityIssue['severity']]>([
        ['a warning, then an error', ['warning', 'error'], 'error'],
        ['an error, then an info', ['error', 'info'], 'error'],
        ['an info, then a warning', ['info', 'warning'], 'warning'],
        ['an info, an error, a warning', ['info', 'error', 'warning'], 'error'],
    ])('keeps the most severe severity, of %s', (_title, severities, mostSevere) => {
        const merged = mergeQualityIssues(severities.map((severity, index) => normalized(stalePriceIssue([[index + 1, `Asset ${index + 1}`]], {severity}))));

        expect(merged.map((issue) => issue.severity)).toEqual([mostSevere]);
    });

    it("keeps the first issue's CTA, domain, message key and other parameters", () => {
        const first = normalized(transactionImpliedIssue([[5, 'Epsilon']], '2025-06-30'));
        const second = normalized({...transactionImpliedIssue([[9, 'Iota']], '2025-12-31'), domain: 'asset', message_i18n_key: 'dataQuality.transactionImpliedElsewhere', cta_action: 'sync_asset_prices'});

        expect(mergeQualityIssues([first, second])).toEqual([
            expect.objectContaining({
                domain: 'portfolio',
                message_i18n_key: 'dataQuality.transactionImplied',
                cta_action: 'navigate_asset',
                cta_target: '5',
                message_params: {count: 2, as_of_date: '2025-06-30'},
                affected_asset_ids: [5, 9],
                count: 2,
            }),
        ]);
    });

    it("builds the parameters from the first issue's: a key only a later issue has is added, a shared key keeps its first value, and a count is updated only where one is carried", () => {
        const withParams = (raw: RawQualityIssue, params: Record<string, string | number>): DataQualityIssue => normalized({...raw, message_params: params});

        const implied = onlyItem(mergeQualityIssues([normalized(transactionImpliedIssue([[5, 'Epsilon']], '2025-06-30')), withParams(transactionImpliedIssue([[9, 'Iota']], '2025-12-31'), {count: 1, as_of_date: '2025-12-31', days: 14})]));
        const uncounted = onlyItem(mergeQualityIssues([withParams(stalePriceIssue([[1, 'Alpha']]), {days: 7}), withParams(stalePriceIssue([[2, 'Beta']]), {days: 30})]));
        // Only the later issue carries a count: added, then updated like any carried count.
        const countedLater = onlyItem(mergeQualityIssues([withParams(stalePriceIssue([[1, 'Alpha']]), {days: 7}), normalized(stalePriceIssue([[2, 'Beta']]))]));

        expect(implied.message_params, 'a key only the later issue has was dropped, or the later value of a shared key won').toEqual({count: 2, as_of_date: '2025-06-30', days: 14});
        expect(uncounted.count, 'the issue itself is no longer counted by its list').toBe(2);
        expect(uncounted.message_params, 'a count was created in parameters that carried none, or the later value of a shared key won').toEqual({days: 7});
        expect(countedLater.message_params, 'a count only the later issue carries was not added, or not updated to the size of the union').toEqual({days: 7, count: 2});
    });

    it('spans the dates of MISSING_FX_RATES — the earliest date_from, the latest date_to, the larger dates_count — wherever each one is', () => {
        const merged = mergeQualityIssues([
            normalized(missingFxRatesIssue(['EUR-USD'], {from: '2025-03-03', to: '2025-03-14', count: 8})),
            normalized(missingFxRatesIssue(['EUR-GBP'], {from: '2025-02-24', to: '2025-03-07', count: 4})),
            normalized(missingFxRatesIssue(['EUR-USD', 'EUR-JPY'], {from: '2025-03-01', to: '2025-03-20', count: 6})),
        ]);

        expect(merged).toEqual([
            expect.objectContaining({
                affected_fx_pairs: ['EUR-USD', 'EUR-GBP', 'EUR-JPY'],
                count: 3,
                // The larger dates_count, a lower bound: two windows may miss the same dates.
                message_params: {count: 3, date_from: '2025-02-24', date_to: '2025-03-20', dates_count: 8},
                cta_target: 'EUR-USD',
            }),
        ]);
    });

    it('merges issues that list nothing — NAV_INCOMPLETE over three windows — into the larger count, a lower bound, and the widest date range', () => {
        const merged = onlyItem(mergeQualityIssues([normalized(navIncompleteIssue(['2025-03-07', '2025-03-10', '2025-03-18'])), normalized(navIncompleteIssue(['2025-03-03', '2025-03-04', '2025-03-05', '2025-03-06', '2025-03-07'])), normalized(navIncompleteIssue(['2025-02-26', '2025-03-14']))]));

        // The larger count, never the sum: two windows may count the same incomplete dates. Count, start
        // and end each come from a different issue, so neither the first nor the last issue can pass for the rule.
        expect(merged.count, 'not the larger count of issues that list nothing').toBe(5);
        expect(merged.message_params, 'the count the sentence shows is not the larger one, or the date range did not widen').toEqual({count: 5, date_from: '2025-02-26', date_to: '2025-03-18'});
    });

    it('collapses identical issues to exactly one each, equal to the input: the Dashboard, where every result carries the same report', () => {
        const report = dashboardReportIssues().map(normalized);
        // Five results, each with a copy of its own: every result's report is parsed apart.
        const carried = Array.from({length: 5}, () => report.map((issue) => structuredClone(issue))).flat();

        expect(mergeQualityIssues(carried), 'identical issues did not come out once each, as they went in: the Dashboard banner would change').toEqual(report);
    });

    it('keeps identical issues equal to the input even when their names are fewer than their ids: an issue equal to the one held is skipped, not merged', () => {
        // Count and parameters agree with the ids, so only the names can tell a skip from a merge: a
        // merge would stand in '#2' for the missing name.
        const shortOfNames = normalized({
            ...stalePriceIssue([
                [1, 'Alpha'],
                [2, 'Beta'],
            ]),
            affected_asset_names: ['Alpha'],
        });

        expect(mergeQualityIssues([shortOfNames, structuredClone(shortOfNames), structuredClone(shortOfNames)]), "identical issues were merged instead of skipped: the missing name became '#2' and the item no longer equals its input").toEqual([shortOfNames]);
    });

    it('never mutates the issues it merges', () => {
        const issues = [
            normalized(
                stalePriceIssue([
                    [1, 'Alpha'],
                    [2, 'Beta'],
                ]),
            ),
            normalized(missingFxRatesIssue(['EUR-USD'], {from: '2025-03-03', to: '2025-03-14', count: 8})),
            normalized(
                stalePriceIssue(
                    [
                        [2, 'Beta'],
                        [3, 'Gamma'],
                    ],
                    {severity: 'error'},
                ),
            ),
            normalized(missingFxRatesIssue(['EUR-GBP'], {from: '2025-02-24', to: '2025-03-20', count: 9})),
            normalized(transactionImpliedIssue([[5, 'Epsilon']], '2025-06-30')),
            normalized(transactionImpliedIssue([[9, 'Iota']], '2025-12-31')),
        ];
        const before = structuredClone(issues);

        const merged = mergeQualityIssues(issues);

        // Precondition: the merges happened — six issues, three items — so every rule had something it could change in place.
        expect(merged.map(keyOf)).toEqual(['STALE_PRICE/stale_price', 'MISSING_FX_RATES/missing_fx_rates', 'TRANSACTION_IMPLIED/transaction_implied']);
        expect(issues, 'an issue, one of its lists or its parameters was changed in place').toStrictEqual(before);
    });

    it('reads any iterable, once: the lab merges the issues of four controllers', () => {
        const issues = [normalized(stalePriceIssue([[1, 'Alpha']])), normalized(missingFxRatesManualIssue(['CHF-EUR'])), normalized(stalePriceIssue([[2, 'Beta']]))];
        function* oneByOne(): Generator<DataQualityIssue> {
            yield* issues;
        }

        const fromGenerator = mergeQualityIssues(oneByOne());

        expect(fromGenerator.map(keyOf)).toEqual(['STALE_PRICE/stale_price', 'MISSING_FX_RATES/missing_fx_rates_manual']);
        expect(fromGenerator[0].affected_asset_ids).toEqual([1, 2]);
        expect(fromGenerator, 'a generator, which can be read once, gave another answer than an array').toEqual(mergeQualityIssues(issues));
        expect(mergeQualityIssues([])).toEqual([]);
    });
});

describe('the risk.errors.answer_discarded sentence', () => {
    const CATALOGUES = {en, it: itCatalogue, fr, es};

    it.each(Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[])('ships in %s.json as a sentence RiskLevelSection can word without values', (locale) => {
        const errors = CATALOGUES[locale].risk.errors as Record<string, unknown>;
        // Positive control: this is where the section's own fallback lives, so a red
        // below means the key is missing, not that this guard reads the wrong place.
        expect(typeof errors.unknown, `risk.errors.unknown is not a sentence in ${locale}.json: this guard reads the wrong place`).toBe('string');

        const sentence = errors.answer_discarded;
        expect(typeof sentence, `risk.errors.answer_discarded is missing from ${locale}.json: a discarded answer would be worded as another sentence, or as its raw key`).toBe('string');
        expect(String(sentence).trim(), `risk.errors.answer_discarded is empty in ${locale}.json`).not.toBe('');
        expect(String(sentence), `risk.errors.answer_discarded takes ICU arguments in ${locale}.json, but translateErrorCode words a code without values: the reader would see raw braces`).not.toMatch(/[{}]/);
    });
});
