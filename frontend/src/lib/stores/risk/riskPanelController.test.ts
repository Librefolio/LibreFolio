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
