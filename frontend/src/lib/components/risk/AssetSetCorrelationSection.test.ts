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
 *
 * **One notice for the lab** (the developer's decision, 2026-10-05): what came back `partial`, and
 * every warning, is said once by the lab panel's `RiskPartialNotice`, as the Dashboard says it above its
 * levels; the frame keeps only what did not come back at all (`levelErrorHealth`) and no reasons. The
 * panel reads the matrix's result through `bind:this`, so the section publishes `qualitySource()`: its
 * one result, `null` when absent, no labels, and its controller's data-quality issues. Pinned by the
 * final blocks; written red first, against a frame that still lists a partial result and repeats its
 * warning, and no `qualitySource`.
 *
 * **Why it did not come back**: L1°, L3° and the replay hand their frames the error codes of their
 * results, then the discard's; the matrix handed only the discard's, so a correlation that did not
 * come back was named in the frame and never explained — and an unavailable one carries its cause in
 * `error.code` alone (`RiskService._unavailable` sets no warning). Pinned by the last block; written
 * red first, against a section that passed its frame `answer_discarded` alone.
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
import {assertEffectsRun, recordReads} from '$test/runes.svelte';
import type {RiskDataQualityReport, RiskResultMetadata} from '$lib/risk/riskTypes';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetCorrelationSection from './AssetSetCorrelationSection.svelte';
import type {AssetSetQualitySource} from './assetSetLevels';

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

/**
 * ─── One notice for the lab: the frame keeps what did not come back at all ───────────────────
 *
 * The developer's decision of 2026-10-05, the Dashboard's pattern (`RiskLevelsPanel`): the matrix's
 * frame passes `levelErrorHealth(health)` — `unavailable` and `failed`, never `partial` — and no
 * `reasons`; what came back partial, with every warning, is said once by the lab panel's
 * `RiskPartialNotice`. The frame renders one result, so the filter is proven across cases: a partial
 * correlation is not listed, an unavailable or a failed one still is. Error codes are not this
 * decision's, so no case here reads one: why a correlation did not come back is the last block's.
 *
 * Every answer has nothing to draw, on purpose, as the complement above: drawing the matrix takes
 * ECharts and a canvas jsdom does not have, and the frame's disclosures read the status, the warnings
 * and the metadata — never the output. The barrier of every case is the frame's provenance block
 * (`risk-correlation-section-metadata`), which `RiskLevelSection` draws from the same result as its
 * health and its reasons: an absence read after it is about where a disclosure lives, not about an
 * answer that had not landed. The warnings are invented and never read: routed, not worded.
 */

/** The one result the section renders, as `buildBaseAnalytics` names it (`base-historical-<code>`). */
const CORRELATION_INSTANCE = 'base-historical-correlation';

/** Invented: the window the matrix was measured over — what the frame's provenance block draws. */
const WINDOW = {
    analyzed_range: {start: DATE_START, end: DATE_END},
    frequency: 'daily',
    n_observations: 740,
    calendar_days: 1090,
    annualization_factor: (740 * 365) / 1090,
    coverage: 1,
    currency: 'EUR',
    scope: 'asset_set',
    return_basis: 'price_only',
    algorithm_version: 'invented-correlation',
    computed_at: '2026-10-05T09:00:00+00:00',
} satisfies RiskResultMetadata;

type ResultWarning = NonNullable<RiskAnalyticResult['warnings']>[number];

/** Invented: a warning that degrades the matrix, as too short an overlap between two series does. */
const PARTIAL_WARNING: ResultWarning = {code: 'invented_short_overlap', message: 'Invented: two pairs had too few overlapping sessions.', degrades_result: true};
/** Invented: a note on a matrix that is whole (`degrades_result: false`). */
const NOTE_WARNING: ResultWarning = {code: 'invented_note', message: 'Invented: a note on a matrix that is whole.', degrades_result: false};

/** What stops a measurement from coming back at all, by the status it then carries. */
const STOPPED_BY = {unavailable: 'insufficient_history', failed: 'execution_failed'} as const;
type Stopped = keyof typeof STOPPED_BY;

/** A correlation shaped like the API's, with its window and nothing to draw. */
function correlation(status: RiskAnalyticResult['status'], extra: Partial<RiskAnalyticResult> = {}): RiskAnalyticResult {
    return {instance_id: CORRELATION_INSTANCE, analytic_code: 'correlation', status, output: null, metadata: WINDOW, warnings: [], ...extra};
}

/** A correlation that did not come back at all, with the code of what stopped it. */
function stoppedCorrelation(status: Stopped): RiskAnalyticResult {
    return correlation(status, {error: {code: STOPPED_BY[status], message: `Invented: the correlation came back ${status}.`}});
}

/** Answer every base question with the results it asked for, out of `results`, and keep it. One test's scope: `beforeEach` installs the ordinary answers again. */
function answerWith(results: RiskAnalyticResult[]): void {
    queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        const asked = new Set(request.analytics.map((analytic) => analytic.instance_id));
        return {items: results.filter((result) => asked.has(result.instance_id))};
    });
}

/** The barrier: the controller holds one answer with this status, and the frame has drawn that answer's provenance. */
async function frameDrew(controller: RiskPanelController, status: RiskAnalyticResult['status']): Promise<void> {
    await waitFor(() =>
        expect(
            controller.historicalResults.map((result) => result.status),
            'premise: the controller never held the planted answer',
        ).toEqual([status]),
    );
    await waitFor(() => expect(screen.queryByTestId(`${FRAME}-metadata`), "the frame never drew its answer's provenance: an absence read now would be about rendering").not.toBeNull());
}

describe("AssetSetCorrelationSection — the frame keeps only what did not come back at all: the lab's notice says the rest", () => {
    it("a partial correlation carrying a warning is named in neither the frame's health nor its reasons", async () => {
        answerWith([correlation('partial', {warnings: [PARTIAL_WARNING]})]);
        const controller = mount();
        await frameDrew(controller, 'partial');

        expect(screen.queryByTestId(`${FRAME}-health`), "the frame still lists a partial correlation: the lab's one notice names it, once").toBeNull();
        expect(screen.queryByTestId(`${FRAME}-reasons`), "the frame still repeats the partial correlation's warning: the lab's one notice says it, once").toBeNull();
    });

    it('a note on a complete correlation is not repeated in the frame either: the frame carries no reasons at all', async () => {
        answerWith([correlation('ok', {warnings: [NOTE_WARNING]})]);
        const controller = mount();
        await frameDrew(controller, 'ok');

        expect(screen.queryByTestId(`${FRAME}-reasons`), "the frame still words a warning: every warning is the lab's notice's, partial or not").toBeNull();
        expect(screen.queryByTestId(`${FRAME}-health`), 'the frame lists a complete correlation as degraded').toBeNull();
    });

    it.each(['unavailable', 'failed'] as const)('a correlation that came back %s is still listed in the frame: what did not come back at all stays where it is missing', async (status) => {
        answerWith([stoppedCorrelation(status)]);
        const controller = mount();
        await frameDrew(controller, status);

        const health = await waitFor(() => screen.getByTestId(`${FRAME}-health`));
        expect(health, `the frame renders one result, and it came back ${status}: one entry`).toHaveAttribute('data-count', '1');
        expect(screen.queryByTestId(`${FRAME}-reasons`), 'the frame words reasons, and the backend sends none with a result that did not come back').toBeNull();
    });
});

/**
 * ─── `qualitySource()`: what the lab panel reads through `bind:this` ───────────────────────────
 *
 * The panel feeds `partialNotice` with `qualitySource().results` — first, in page order — and merges
 * `.issues` with the levels'. So the export hands over the one result the frame renders — the
 * controller's own object, `null` when the answer had none — no labels, since the matrix's name is not
 * ambiguous, and the controller's `dataQualityIssues`; and it stays reactive, since the panel calls it
 * inside a `$derived`.
 *
 * ⚠️ "The object the store answered" is the controller's entry: a controller keeps its answer in
 * `$state`, which wraps every result in a proxy, so the fixture `queryRisk` returned is never the object
 * the frame reads. Identity is checked against the controller's own entry; content against the fixture.
 */

/** The section's `qualitySource`, reached through the instance the harness mounted — as the panel reaches it, through `bind:this`. */
function qualitySourceOf(view: {component: unknown}): () => AssetSetQualitySource {
    const read = (view.component as {qualitySource?: unknown}).qualitySource;
    expect(typeof read, 'the section exports no qualitySource(): the lab panel has nothing to read its result and issues through bind:this').toBe('function');
    return read as () => AssetSetQualitySource;
}

/** `mount`, keeping the instance as well: `qualitySource()` is reached through it. */
function mountKeepingInstance() {
    const view = render(AssetSetCorrelationSection, {props: PROPS});
    expect(created.controllers, 'the section did not create a controller of its own').toHaveLength(1);
    return {view, controller: created.controllers[0] as RiskPanelController};
}

/** The entry the controller holds for the correlation — the very object the frame reads — or null. */
function heldCorrelation(controller: RiskPanelController): RiskAnalyticResult | null {
    return controller.historicalResults.find((result) => result.instance_id === CORRELATION_INSTANCE) ?? null;
}

/** The latest value an effect read, or the error its read threw. */
function lastRead<T>(values: ReadonlyArray<T | Error>): T {
    const last = values.at(-1);
    if (last === undefined) throw new Error('the effect never read qualitySource()');
    if (last instanceof Error) throw last;
    return last;
}

/** Invented: a data-quality issue the backend reports beside the matrix. */
type QualityIssue = NonNullable<RiskDataQualityReport['issues']>[number];
const ISSUE: QualityIssue = {domain: 'asset', code: 'STALE_PRICE', severity: 'warning', message_i18n_key: 'invented.dataQuality.stalePrice', affected_asset_ids: [HOLDING_A]};

describe('AssetSetCorrelationSection — qualitySource(), what the lab panel reads through bind:this', () => {
    it("returns the correlation the frame renders — the controller's own object — no labels, and the controller's data-quality issues", async () => {
        const answered = correlation('partial', {warnings: [PARTIAL_WARNING], data_quality: {issues: [ISSUE], data_quality_status: 'carried_forward'}});
        answerWith([answered]);
        const {view, controller} = mountKeepingInstance();
        await frameDrew(controller, 'partial');
        expect(
            controller.dataQualityIssues.map((issue) => issue.code),
            'premise: the controller does not hold the issue planted in the answer',
        ).toEqual([ISSUE.code]);

        const source = qualitySourceOf(view)();
        expect(source.results, 'not the one result the frame renders').toHaveLength(1);
        expect(source.results[0], 'not the object the controller holds: the notice would read a copy, not what the frame reads').toBe(heldCorrelation(controller));
        expect(source.results[0], 'does not carry what the store answered').toEqual(answered);
        expect(source.labels, "the matrix's name is not ambiguous: nothing to label").toEqual({});
        expect(source.issues, "not the controller's data-quality issues").toEqual(controller.dataQualityIssues);
    });

    it('returns null where the answer had no correlation, and no issues', async () => {
        // The harness's ordinary answer: nothing in it.
        const {view, controller} = mountKeepingInstance();
        await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));
        await waitFor(() => expect(screen.queryByTestId('risk-correlation-empty'), 'the section did not settle on its empty state').not.toBeNull());

        const source = qualitySourceOf(view)();
        expect(source.results, 'the frame renders nothing: the slot says so with null, it does not vanish').toEqual([null]);
        expect(source.labels).toEqual({});
        expect(source.issues).toEqual([]);
    });

    it('answered again, returns the new result — to a plain call, and to an effect that reads it, as the panel does', async () => {
        answerWith([correlation('partial', {warnings: [PARTIAL_WARNING]})]);
        const {view, controller} = mountKeepingInstance();
        await frameDrew(controller, 'partial');
        const source = qualitySourceOf(view);
        const reads = recordReads(() => source());
        try {
            expect(lastRead(reads.values).results, 'the first answer, read by an effect').toEqual([heldCorrelation(controller)]);

            // An accepted sync re-reads the base, and the store answers with a different result.
            answerWith([stoppedCorrelation('unavailable')]);
            await view.rerender({refreshVersion: 1});
            await waitFor(() => expect(heldCorrelation(controller)?.status, 'the second answer never reached the controller').toBe('unavailable'));
            await waitFor(() => expect(controller.initialLoading || controller.refreshing, 'the second answer never settled').toBe(false));

            const now = heldCorrelation(controller);
            expect(source().results[0], 'a plain call after the second answer still returns the first').toBe(now);
            await waitFor(() => expect(lastRead(reads.values).results[0], "an effect reading qualitySource() after the second answer — it never re-ran, so the panel's notice would keep the first").toBe(now));
        } finally {
            reads.stop();
        }
    });
});

/**
 * ─── Why it did not come back: the result's error code, under the frame ───────────────────────
 *
 * The frame keeps what did not come back at all and, like L1°'s, L3°'s and the replay's, why: the
 * section hands it `[...resultErrorCodes([result]), ...discarded]`, so `{frame}-errors` counts the
 * codes (`data-count`) and each `{frame}-error` carries one (`data-code`), the result's before the
 * discard's. An unavailable correlation carries its cause in `error.code` and in no warning
 * (`RiskService._unavailable`), so this list is the only place the frame can say it.
 *
 * Codes, never sentences: the wording is `RiskLevelSection`'s and is not read here. The barrier is the
 * frame's provenance block again (`frameDrew`), drawn from the same result as the error list; where a
 * discard is the subject, the body's discarded block too, which reads the flag the frame's
 * `answer_discarded` line reads. Written red first, against a section that passed `answer_discarded`
 * alone: every case that needs the result's code fails on its absence.
 */

/** A case of this block: what stopped the correlation, and the code the frame must then show. */
const NO_HISTORY = {status: 'unavailable', code: 'insufficient_history'} as const;
/**
 * Invented pairing: the risk service reports its own failures as `execution_failed`, and a timeout
 * arrives `unavailable`. The frame reads the code, never the pair — and a code that no status implies
 * is what proves the line comes from the result, not from its status.
 */
const TIMED_OUT = {status: 'failed', code: 'execution_timeout'} as const;
type Refusal = typeof NO_HISTORY | typeof TIMED_OUT;

/** A correlation that did not come back, with the code of what stopped it. */
function refusedCorrelation({status, code}: Refusal): RiskAnalyticResult {
    return correlation(status, {error: {code, message: `Invented: the correlation came back ${status}, stopped by ${code}.`}});
}

/** Discard every base answer from now on — `null`, as `queryRisk` answers when the session moved in flight. One test's scope, as `answerWith`'s. */
function discardEveryAnswer(): void {
    queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        return null;
    });
}

describe("AssetSetCorrelationSection — why it did not come back: the result's error code, under the frame", () => {
    it.each([NO_HISTORY, TIMED_OUT])('a correlation that came back $status is still listed, and the frame says why: one error line, $code', async (refusal) => {
        answerWith([refusedCorrelation(refusal)]);
        const controller = mount();
        await frameDrew(controller, refusal.status);
        expect(controller.loadDiscarded, "premise: nothing was discarded, so any line under the frame is the result's").toBe(false);

        // The guard that already holds: the frame lists the correlation that did not come back.
        const health = screen.queryByTestId(`${FRAME}-health`);
        expect(health, `the frame no longer lists a correlation that came back ${refusal.status}`).not.toBeNull();
        expect(health, 'the frame renders one result: one entry').toHaveAttribute('data-count', '1');

        // What it did not say: why.
        const errors = screen.queryByTestId(`${FRAME}-errors`);
        expect(errors, `the frame says the correlation came back ${refusal.status} and never why: ${refusal.code} is in the answer and nowhere under the frame`).not.toBeNull();
        expect(errors, 'one result that did not come back, one cause: one error line').toHaveAttribute('data-count', '1');
        expect(frameCodes(), 'the error line does not carry the code that stopped the correlation').toEqual([refusal.code]);
    });

    it('a correlation that came back ok has no error line at all: there is no why to say', async () => {
        answerWith([correlation('ok')]);
        const controller = mount();
        await frameDrew(controller, 'ok');
        // The body as well: it settled on what it draws for this answer.
        await waitFor(() => expect(screen.queryByTestId('risk-correlation-empty'), 'the section did not settle on its body for this answer').not.toBeNull());
        expect(controller.loadDiscarded, 'premise: nothing was discarded').toBe(false);

        expect(screen.queryByTestId(`${FRAME}-errors`), 'the frame says why a correlation did not come back, and it came back whole').toBeNull();
    });

    it("an unavailable correlation whose refreshed answer is discarded twice running: both codes, the result's first, then answer_discarded", async () => {
        answerWith([refusedCorrelation(NO_HISTORY)]);
        const {view, controller} = mountKeepingInstance();
        await frameDrew(controller, NO_HISTORY.status);

        // An accepted sync re-reads the base, and its answer is discarded twice running.
        discardEveryAnswer();
        const before = script.asked.length;
        await view.rerender({refreshVersion: 1});
        await waitFor(() => expect(controller.loadDiscarded, 'the controller never recorded the discard: the path under test did not run').toBe(true));
        expect(script.asked.length - before, 'the refreshed question was not asked and then re-asked exactly once').toBe(2);
        expect(heldCorrelation(controller)?.status, 'premise: a discard is not an answer, yet the controller no longer holds the unavailable correlation').toBe(NO_HISTORY.status);
        // The barrier: the body settled on the discard's retry, which reads the flag the frame's line reads.
        await waitFor(() => expect(screen.queryByTestId('risk-correlation-discarded'), 'the section did not settle on its discarded state').not.toBeNull());

        expect(screen.getByTestId(`${FRAME}-health`), 'the frame no longer lists the correlation the controller still holds').toHaveAttribute('data-count', '1');
        expect(frameCodes(), "both apply, and the frame says one: the result's code first, then the discard's").toEqual([NO_HISTORY.code, ANSWER_DISCARDED_CODE]);
        expect(screen.getByTestId(`${FRAME}-errors`), 'two causes: two error lines').toHaveAttribute('data-count', '2');
    });
});
