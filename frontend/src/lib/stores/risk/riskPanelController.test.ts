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
/** Read at call time by the `hasRiskCapability` stub; `beforeEach` puts it back. `only`, when a
 *  test sets it, narrows "everything" to what one catalogue offers. */
const capability = vi.hoisted(() => ({supported: true, only: null as ((code: string, scopeKind: string, mode: string) => boolean) | null}));

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
        // The one test about an unsupported analytic flips it for itself, and the
        // asset-set cases narrow it to what an asset set is offered, so the lab's
        // request here is the one the lab sends.
        hasRiskCapability: (_catalog: unknown, code: string, scopeKind: string, mode: string) => capability.supported && (capability.only?.(code, scopeKind, mode) ?? true),
    };
});

import {assertEffectsRun, effectRoot, reactiveBox, recordReads} from '$test/runes.svelte';
import {ANSWER_DISCARDED_CODE, baseSignature, createRiskPanelController, discardedErrorCodes, LEVEL_ON_DEMAND_ANALYSES, ON_DEMAND_ANALYSES, type OnDemandAnalysis, type RiskControllerInputs, type RiskControllerOptions, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';

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

function mountController(initial: RiskControllerInputs = defaultInputs(), options: RiskControllerOptions = {}) {
    const inputs = reactiveBox(initial);
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => inputs, options));
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

describe('riskPanelController', () => {
    beforeEach(() => {
        fetchRiskCatalog.mockReset().mockResolvedValue(CATALOG);
        fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
        queryRisk.mockReset().mockResolvedValue({items: []});
        invalidateRisk.mockReset();
        capability.supported = true;
        capability.only = null;
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
    // The asset-set wave, split per level (the developer's decision, 2026-10-02): L1° is measured
    // without the benchmark and only L3° asks with it, so the lab builds one controller per level —
    // `includeAssetSetLossLevels` for L1°, `includeAssetSetPaidLevels` for L3° — and each option has
    // to reach the request the way `includeAssetSetLevels` does. Written red first: today the
    // controller passes neither on, so the request it issues carries no per-asset analytic at all.
    //
    // The pins are the other half, green today and meant to stay so: the callers that never opt in
    // — the Dashboard's levels, Asset Detail's panel — and the lab as it asks today, on the union,
    // each send byte for byte the requests they send now. Copied from a run before the split.
    // ------------------------------------------------------------------
    describe('the asset-set wave, split per level', () => {
        /** Invented, and unlike any other number a request carries — an id, a horizon, a rate. */
        const BENCHMARK = 47;
        /** What the backend's catalogue offers an asset set — the correlation and the per-asset family, historical only — as `AssetSetComparisonLevels.test.ts` declares it. */
        const ASSET_SET_HISTORICAL_CODES = new Set(['correlation', 'asset_set_kpi', 'asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_comparison']);

        function assetSetCatalogue(code: string, scopeKind: string, mode: string): boolean {
            return scopeKind === 'asset_set' && mode === 'historical' && ASSET_SET_HISTORICAL_CODES.has(code);
        }

        /** The lab's inputs: two holdings, a 0% risk-free rate (the page has no control for one), and a benchmark outside the selection. */
        function labInputs(): RiskControllerInputs {
            return {...defaultInputs(), scope: {kind: 'asset_set', asset_ids: [12, 15]}, appliedRiskFreePercent: 0, assetSetBenchmarkId: BENCHMARK};
        }

        /** Mounted with `options`, its first base wave settled, and stopped when the test ends, red or green. */
        async function settledController(initial: RiskControllerInputs, options: RiskControllerOptions): Promise<void> {
            const {controller, stop} = mountController(initial, options);
            onTestFinished(stop);
            await vi.waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));
        }

        /** The per-asset analytics of the one historical request issued: instance and parameters. */
        function assetSetAnalyticsAsked(): unknown[] {
            const historical = queryRisk.mock.calls.map(([request]) => request as RiskQueryRequest).filter((request) => request.mode === 'historical');
            expect(historical, 'premise: one base load is one historical request').toHaveLength(1);
            return historical[0].analytics.filter((analytic) => analytic.analytic_code.startsWith('asset_set_')).map((analytic) => [analytic.instance_id, analytic.parameters]);
        }

        /** Every request issued, with its `force` flag: first as data, for a readable diff, then as the bytes the wire carries. */
        function expectIssuedToday(today: unknown[], caller: string): void {
            expect(queryRisk.mock.calls, `${caller}: the requests moved — a caller that never asked for the split sends something new`).toEqual(today);
            expect(JSON.stringify(queryRisk.mock.calls), `${caller}: the same requests in different bytes — a key moved, or one appeared that serialises`).toBe(JSON.stringify(today));
        }

        /** The Dashboard's levels over 2025, in EUR, at a 2% risk-free rate: two requests, historical then current composition. */
        const DASHBOARD_TODAY = [
            [
                {
                    scope: {kind: 'portfolio'},
                    date_range: {start: '2025-01-01', end: '2025-12-31'},
                    target_currency: 'EUR',
                    mode: 'historical',
                    analytics: [
                        {instance_id: 'base-historical-historical_kpi', analytic_code: 'historical_kpi', parameters: {risk_free_annual_rate: 0.02, target_annual_return: 0}},
                        {instance_id: 'base-historical-correlation', analytic_code: 'correlation', parameters: {}},
                        {instance_id: 'base-historical-historical_var', analytic_code: 'historical_var', parameters: {confidence_level: 0.95, horizon_days: 1}},
                        {instance_id: 'base-historical-historical_var-monthly', analytic_code: 'historical_var', parameters: {confidence_level: 0.95, horizon_days: 30}},
                        {instance_id: 'base-historical-drawdown_summary', analytic_code: 'drawdown_summary', parameters: {}},
                    ],
                },
                false,
            ],
            [
                {
                    scope: {kind: 'portfolio'},
                    date_range: {start: '2025-01-01', end: '2025-12-31'},
                    target_currency: 'EUR',
                    mode: 'current_composition',
                    composition_policy: 'current_buy_and_hold',
                    analytics: [
                        {instance_id: 'base-current_composition-risk_contribution', analytic_code: 'risk_contribution', parameters: {}},
                        {instance_id: 'base-current_composition-historical_kpi', analytic_code: 'historical_kpi', parameters: {risk_free_annual_rate: 0.02, target_annual_return: 0}},
                        {instance_id: 'base-current_composition-asset_risk_return', analytic_code: 'asset_risk_return', parameters: {}},
                    ],
                },
                false,
            ],
        ];

        /** Asset Detail's panel for one asset, same window: two requests. */
        const ASSET_DETAIL_TODAY = [
            [
                {
                    scope: {kind: 'asset', asset_id: 12},
                    date_range: {start: '2025-01-01', end: '2025-12-31'},
                    target_currency: 'EUR',
                    mode: 'historical',
                    analytics: [
                        {instance_id: 'base-historical-historical_kpi', analytic_code: 'historical_kpi', parameters: {risk_free_annual_rate: 0.02, target_annual_return: 0}},
                        {instance_id: 'base-historical-correlation', analytic_code: 'correlation', parameters: {}},
                        {instance_id: 'base-historical-historical_var', analytic_code: 'historical_var', parameters: {confidence_level: 0.95, horizon_days: 1}},
                    ],
                },
                false,
            ],
            [
                {
                    scope: {kind: 'asset', asset_id: 12},
                    date_range: {start: '2025-01-01', end: '2025-12-31'},
                    target_currency: 'EUR',
                    mode: 'current_composition',
                    composition_policy: 'current_buy_and_hold',
                    analytics: [{instance_id: 'base-current_composition-risk_contribution', analytic_code: 'risk_contribution', parameters: {}}],
                },
                false,
            ],
        ];

        /** The lab's two levels as they ask today, on the union, the benchmark inside: one request for both. */
        const LAB_UNION_TODAY = [
            [
                {
                    scope: {kind: 'asset_set', asset_ids: [12, 15]},
                    date_range: {start: '2025-01-01', end: '2025-12-31'},
                    target_currency: 'EUR',
                    mode: 'historical',
                    analytics: [
                        {instance_id: 'base-historical-correlation', analytic_code: 'correlation', parameters: {}},
                        {instance_id: 'base-historical-asset_set_kpi', analytic_code: 'asset_set_kpi', parameters: {risk_free_annual_rate: 0, target_annual_return: 0}},
                        {instance_id: 'base-historical-asset_set_var', analytic_code: 'asset_set_var', parameters: {confidence_level: 0.95, horizon_days: 1}},
                        {instance_id: 'base-historical-asset_set_var-monthly', analytic_code: 'asset_set_var', parameters: {confidence_level: 0.95, horizon_days: 30}},
                        {instance_id: 'base-historical-asset_set_drawdown', analytic_code: 'asset_set_drawdown', parameters: {}},
                        {instance_id: 'base-historical-asset_set_risk_return', analytic_code: 'asset_set_risk_return', parameters: {}},
                        {instance_id: 'base-historical-asset_set_comparison', analytic_code: 'asset_set_comparison', parameters: {comparison_asset_id: 47}},
                    ],
                },
                false,
            ],
        ];

        it('includeAssetSetLossLevels reaches the request: the bad day, the bad month and the drawdown, and nothing of the benchmark', async () => {
            capability.only = assetSetCatalogue;
            await settledController(labInputs(), {includeAssetSetLossLevels: true});

            expect(assetSetAnalyticsAsked(), "the loss option never reached L1°'s request, or brought the benchmark into it").toEqual([
                ['base-historical-asset_set_var', {confidence_level: 0.95, horizon_days: 1}],
                ['base-historical-asset_set_var-monthly', {confidence_level: 0.95, horizon_days: 30}],
                ['base-historical-asset_set_drawdown', {}],
            ]);
        });

        it('includeAssetSetPaidLevels reaches the request: the KPI, the risk/return and the comparison against the benchmark', async () => {
            capability.only = assetSetCatalogue;
            await settledController(labInputs(), {includeAssetSetPaidLevels: true});

            expect(assetSetAnalyticsAsked(), "the paid option never reached L3°'s request").toEqual([
                ['base-historical-asset_set_kpi', {risk_free_annual_rate: 0, target_annual_return: 0}],
                ['base-historical-asset_set_risk_return', {}],
                ['base-historical-asset_set_comparison', {comparison_asset_id: BENCHMARK}],
            ]);
        });

        it("pins the Dashboard's levels: the requests they send today, byte for byte", async () => {
            // `RiskLevelsPanel`'s options (the Dashboard and the broker page), callbacks aside: those change no request.
            // Every analytic stays advertised, so a split option that defaulted to on would put the per-asset family on this wire.
            await settledController(defaultInputs(), {includeDrawdownSummary: true, includeMonthlyVar: true, includeCurrentCompositionRiskReturn: true});
            expectIssuedToday(DASHBOARD_TODAY, "the Dashboard's levels");
        });

        it("pins Asset Detail's panel: the requests it sends today, byte for byte", async () => {
            // `RiskAnalysisPanel`'s only option is a callback.
            await settledController({...defaultInputs(), scope: {kind: 'asset', asset_id: 12}}, {scenarioCatalogLoaded: () => undefined});
            expectIssuedToday(ASSET_DETAIL_TODAY, "Asset Detail's panel");
        });

        it('pins the lab as it asks today, on the union with a benchmark: one request, byte for byte', async () => {
            capability.only = assetSetCatalogue;
            await settledController(labInputs(), {includeAssetSetLevels: true});
            expectIssuedToday(LAB_UNION_TODAY, 'the lab on the union');
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
