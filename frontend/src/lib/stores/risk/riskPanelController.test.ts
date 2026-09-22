// @vitest-environment jsdom
//
// The docblock above is load-bearing, not decoration. Under the repository's
// default `node` environment a `.svelte.ts` compiles but its effects never run,
// so every negative assertion in this file would pass while proving nothing.
// `assertEffectsRun()` in the first test fails loudly if it is ever removed.
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());

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
        hasRiskCapability: () => true,
    };
});

import {assertEffectsRun, effectRoot, reactiveBox} from '$test/runes.svelte';
import {baseSignature, createRiskPanelController, type RiskControllerInputs} from '$lib/stores/risk/riskPanelController.svelte';

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

describe('riskPanelController', () => {
    beforeEach(() => {
        fetchRiskCatalog.mockReset().mockResolvedValue(CATALOG);
        fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
        queryRisk.mockReset().mockResolvedValue({items: []});
        invalidateRisk.mockReset();
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
});
