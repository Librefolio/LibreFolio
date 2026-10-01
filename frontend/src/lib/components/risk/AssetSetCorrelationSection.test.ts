// @vitest-environment jsdom
//
// The docblock above is load-bearing: the section builds a real panel controller, and under the
// default `node` environment its `$effect`s never fire — no base wave, no failure, no discard, and
// every "the section shows nothing of the sort" below would pass about a section that never asked
// anything. `assertEffectsRun()` in the first test turns that into a message.
/**
 * AssetSetCorrelationSection — component test (Vitest + jsdom).
 *
 * The laboratory's matrix already said, in its body, when its answer was discarded twice running
 * (`risk-correlation-discarded`, a retry and nothing else); when its base wave failed it said so
 * in a sentence and offered no way out. What it did not say is *why* a retry is all a discarded
 * answer offers: that body carries no sentence by design, and its frame carried no line either.
 * Aligned with the comparison levels below it, the failed wave now offers the same retry beside its
 * sentence, and the frame says a discard once, as its error line `answer_discarded`
 * (`risk-correlation-section-error[data-code]`). Pinned here:
 *
 *   - a failed wave shows its sentence and a retry that asks the base again, past the cache, and
 *     nothing of a discard;
 *   - a discarded answer shows the retry in the body and the `answer_discarded` line in the frame;
 *   - an answer — nothing failed, nothing discarded — shows none of it.
 *
 * The complement's answer has nothing to draw, on purpose. Drawing the matrix takes ECharts and
 * a canvas jsdom does not have (the drawn matrix is `e2e/portfolio/risk-lab.spec.ts` ground), and
 * an answer with nothing in it is the sharper case anyway: it is the one state a discard could be
 * mistaken for, so it is the one where claiming a lost answer would be a lie.
 *
 * **The harness is `AssetSetReplaySection.test.ts`'s**: the real controller, observed through its
 * factory so each case states its premise first; `queryRisk` answered by outcome; capabilities
 * gated as the backend declares them for an asset set, so the section's base load is exactly its
 * one question, `[correlation]`. The matrix's grouping inputs (`createMatrixMetadata`) are read
 * over the network and are not this file's subject: they are replaced by the empty maps a failed
 * read leaves, so no request leaves the test.
 *
 * **No text is asserted**: testids and `data-code` are the contract; a sentence is only checked
 * to be there, never read.
 *
 * Left elsewhere: the discard and re-ask rules (`riskPanelController.test.ts`), the matrix itself
 * (`correlationHelpers.test.ts`, the E2E), and the levels' own states
 * (`AssetSetComparisonLevels.test.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());
/** Every controller the section creates, in order. Observed, never replaced. */
const created = vi.hoisted(() => ({controllers: [] as unknown[]}));
/** What the backend's catalogue offers an asset set: the correlation and the per-asset family, historical only. */
const ASSET_SET_HISTORICAL_CODES = vi.hoisted(() => new Set(['correlation', 'asset_set_kpi', 'asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_comparison']));

vi.mock('$lib/stores/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskStore.svelte')>();
    return {
        ...actual,
        fetchRiskCatalog,
        fetchRiskScenarioCatalog,
        queryRisk,
        invalidateRisk,
        hasRiskCapability: (_catalog: unknown, code: string, scope: string, mode: string) => scope === 'asset_set' && mode === 'historical' && ASSET_SET_HISTORICAL_CODES.has(code),
    };
});

vi.mock('$lib/stores/risk/riskPanelController.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/risk/riskPanelController.svelte')>();
    return {
        ...actual,
        createRiskPanelController: (...args: Parameters<typeof actual.createRiskPanelController>) => {
            const controller = actual.createRiskPanelController(...args);
            created.controllers.push(controller);
            return controller;
        },
    };
});

/** Calls to the stand-in for the matrix's grouping inputs: the premise that no metadata read leaves the test. */
const metadataStandIn = vi.hoisted(() => ({calls: 0}));

vi.mock('$lib/components/risk/matrixMetadata.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/components/risk/matrixMetadata.svelte')>();
    return {
        ...actual,
        createMatrixMetadata: () => {
            metadataStandIn.calls += 1;
            return actual.EMPTY_MATRIX_METADATA;
        },
    };
});

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import AssetSetCorrelationSection from './AssetSetCorrelationSection.svelte';

// Invented: a window, and a selection of two with their names.
const DATE_START = '2021-01-04';
const DATE_END = '2023-12-29';
const HOLDING_A = 12;
const HOLDING_B = 15;
const LABELS: ReadonlyMap<number, string> = new Map([
    [HOLDING_A, 'Invented holding A'],
    [HOLDING_B, 'Invented holding B'],
]);
const PROPS = {assetIds: [HOLDING_A, HOLDING_B], assetLabels: LABELS, dateStart: DATE_START, dateEnd: DATE_END, targetCurrency: 'EUR'};

/** The frame the section renders its body in. */
const FRAME = 'risk-correlation-section';

/**
 * How every base question is answered, and every question as it was asked.
 *
 *  - `nothing`: an answer with no result in it — nothing failed, nothing to draw;
 *  - `reject`: the request throws, as a failed wave does (`loadError`);
 *  - `discard`: `null`, an answer that arrived and was discarded. The controller re-asks once,
 *    and a second `null` is what sets `loadDiscarded`.
 */
type Outcome = 'nothing' | 'reject' | 'discard';
const script = {outcome: 'nothing' as Outcome, asked: [] as {request: RiskQueryRequest; force: boolean}[]};

let consoleError: MockInstance<Console['error']>;

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    created.controllers.length = 0;
    metadataStandIn.calls = 0;
    script.outcome = 'nothing';
    script.asked = [];
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        if (script.outcome === 'reject') throw new Error('invented: the base wave failed');
        if (script.outcome === 'discard') return null;
        return {items: []};
    });
    // The controller logs a failed wave. That one line is expected and kept out of the run's
    // output; anything else still reaches it.
    const passThrough = console.error.bind(console);
    consoleError = vi.spyOn(console, 'error').mockImplementation((...args: unknown[]) => {
        if (typeof args[0] === 'string' && args[0].startsWith('[Risk] Failed to load base analytics')) return;
        passThrough(...args);
    });
});

afterEach(() => {
    consoleError.mockRestore();
});

function mount(): RiskPanelController {
    render(AssetSetCorrelationSection, {props: PROPS});
    expect(created.controllers, 'the section did not create a controller of its own').toHaveLength(1);
    return created.controllers[0] as RiskPanelController;
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** The frame's error lines, as the codes they carry. */
function frameCodes(): string[] {
    return screen.queryAllByTestId(`${FRAME}-error`).map((line) => line.getAttribute('data-code') ?? '');
}

/** What a block says besides its button — its sentence, if it has one. Checked for presence, never read. */
function sentenceBeside(block: HTMLElement, button: HTMLElement): string {
    const copy = block.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(`[data-testid="${button.getAttribute('data-testid')}"]`).forEach((node) => node.remove());
    return normalize(copy.textContent);
}

/** Mounted with the wave failing, and the premise: the controller recorded the failure. */
async function mountFailed(): Promise<RiskPanelController> {
    script.outcome = 'reject';
    const controller = mount();
    await waitFor(() => expect(controller.loadError, 'the controller never recorded the failure: the path under test did not run').toBe(true));
    expect(controller.loadDiscarded, 'a failure is not a discard').toBe(false);
    return controller;
}

/** The error block, which must hold the section's retry button. */
async function errorBlockWithRetry(): Promise<{block: HTMLElement; retry: HTMLElement}> {
    const block = await waitFor(() => screen.getByTestId('risk-correlation-error'));
    const retry = within(block).queryByTestId('risk-correlation-retry');
    expect(retry, 'the base wave failed and the section offers no way to ask again').not.toBeNull();
    expect(retry?.tagName, 'the retry is not a button').toBe('BUTTON');
    return {block, retry: retry as HTMLElement};
}

describe('AssetSetCorrelationSection — the harness itself', () => {
    it('runs effects, reads no metadata, and a base load is its one question: the correlation', async () => {
        expect(() => assertEffectsRun()).not.toThrow();

        const controller = mount();
        expect(metadataStandIn.calls, 'the section built its grouping inputs through something other than the stand-in: a real read may have left the test').toBe(1);
        await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));
        expect(script.asked, 'one base load must be one question: the capability gate lets only the asset-set wave through').toHaveLength(1);
        expect(script.asked[0].request.analytics.map((analytic) => analytic.analytic_code)).toEqual(['correlation']);
    });
});

describe('AssetSetCorrelationSection — a base wave that fails', () => {
    it('shows its sentence and a retry, and nothing of a discard', async () => {
        await mountFailed();

        const {block, retry} = await errorBlockWithRetry();
        expect(sentenceBeside(block, retry), 'the error block offers a retry but no sentence saying what failed').not.toBe('');
        expect(screen.queryByTestId('risk-correlation-discarded'), 'a failed wave is shown as a discarded answer').toBeNull();
    });

    it('its retry asks the base question again, past the cache', async () => {
        const controller = await mountFailed();
        const {retry} = await errorBlockWithRetry();
        const before = script.asked.length;

        await fireEvent.click(retry);

        await waitFor(() => expect(script.asked.length, 'pressing retry asked nothing').toBeGreaterThan(before));
        expect(
            script.asked.slice(before).every((question) => question.force),
            'the retry must ask past the cache — controller.loadBase(true)',
        ).toBe(true);
        await waitFor(() => expect(controller.loadError, 'the re-asked wave never settled').toBe(true));
    });
});

describe('AssetSetCorrelationSection — a base answer discarded twice running', () => {
    it('offers the retry in the body, and the frame says why, once, as answer_discarded', async () => {
        script.outcome = 'discard';
        const controller = mount();
        await waitFor(() => expect(controller.loadDiscarded, 'the controller never recorded the discard: the path under test did not run').toBe(true));
        expect(script.asked, 'the base question was not asked and then re-asked exactly once').toHaveLength(2);

        // The body, as it already was: a retry and nothing else.
        const block = await waitFor(() => screen.getByTestId('risk-correlation-discarded'));
        expect(within(block).getByTestId('risk-correlation-retry').tagName, 'the retry is not a button').toBe('BUTTON');
        expect(screen.queryByTestId('risk-correlation-error'), 'a discarded answer is shown as a failed wave').toBeNull();

        // The frame, which did not say it.
        await waitFor(() => expect(frameCodes(), 'the controller recorded a discarded answer and the frame does not say so: the body offers a retry with no word of why').toEqual([ANSWER_DISCARDED_CODE]));
        expect(normalize(screen.getByTestId(`${FRAME}-error`).textContent), "the frame's line carries no sentence").not.toBe('');
    });
});

describe('AssetSetCorrelationSection — an answer: nothing failed, nothing discarded', () => {
    it('with nothing to draw, shows none of it: an empty answer is not a lost one', async () => {
        const controller = mount();
        await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));
        expect(controller.loadError).toBe(false);
        expect(controller.loadDiscarded).toBe(false);

        // The barrier: the section settled on its empty state.
        await waitFor(() => expect(screen.queryByTestId('risk-correlation-empty'), 'the section did not settle on its empty state').not.toBeNull());
        for (const testId of ['risk-correlation-error', 'risk-correlation-discarded', 'risk-correlation-retry']) {
            expect(screen.queryByTestId(testId), `an answer with nothing to draw shows ${testId}`).toBeNull();
        }
        expect(frameCodes(), 'the frame says an answer was discarded when none was').not.toContain(ANSWER_DISCARDED_CODE);
    });
});
