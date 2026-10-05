// @vitest-environment jsdom
//
// The docblock above is load-bearing: the levels build a real panel controller, and under the
// default `node` environment its `$effect`s never fire — no base wave, no failure, no discard, and
// every "the level shows nothing of the sort" below would pass about a page that never asked
// anything. `assertEffectsRun()` in the first test turns that into a message.
/**
 * AssetSetComparisonLevels — component test (Vitest + jsdom).
 *
 * L1° ("how much did each hurt") and L3° ("was each paid") of Asset Global take their rows from
 * the selection, not from the answer: one row per selected asset, its cells empty until a
 * measurement fills them. That is what keeps an asset nobody could measure on screen — and it is
 * also why a base wave that failed, or whose answer was discarded twice running, looked exactly
 * like one that measured nothing: two tables of em-dashes, and not a word. The controller knows
 * the difference (`loadError`, `loadDiscarded`); these tests pin that both levels say it, in the
 * form Risk settled on for the laboratory ("(b)", the correlation section's):
 *
 *   - **a failed wave**: each level's body holds an error block, a sentence and a retry
 *     (`risk-asset-set-l{1,3}-error` around `risk-asset-set-l{1,3}-retry`);
 *   - **an answer discarded twice running**: each level's frame says it once, as its error line
 *     with `data-code="answer_discarded"` (`risk-asset-set-{loss,paid}-error`), and a body with no
 *     figure offers the retry and nothing else (`risk-asset-set-l{1,3}-discarded`);
 *   - **a retry** asks the base question again, past the cache (`controller.loadBase(true)`).
 *
 * The complements keep both states from being claimed where they do not apply: an answer with
 * figures shows none of it; an answer that measured nothing shows none of it either, because a
 * blank is not a failure; and a discard *after* an answer keeps its figures — the frames say the
 * new answer was lost, and the table is not replaced by a retry.
 *
 * **The harness is `AssetSetReplaySection.test.ts`'s.** The controllers are the real ones, observed
 * through their factory, so every case first states its premise — every controller the levels
 * created did record the failure, or the discard — before asserting what the page makes of it. The
 * premises are stated over all of them because their number is what the split below changes: one
 * today, one per level once the levels ask apart. `queryRisk` answers by outcome, with the results the
 * question asked for (by instance, as the backend answers), and keeps every question with its `force`
 * flag. Capabilities are gated the way the backend declares them for an asset set (historical only;
 * the correlation and the per-asset family), so each controller's base load is one question and
 * "asked again" is a count.
 *
 * **No text is asserted.** Testids, `data-code` and `data-measured` are the contract; a sentence
 * is only checked to be there (non-empty) or not there, never read.
 *
 * ⚠️ Every figure and name below is invented, shaped to pass the schemas the levels parse it
 * through (`assetSetLevels.ts`); nothing was read off a running backend. The answer with figures
 * carries L1's two VaR horizons and L3's KPI — volatility, Sortino and Sharpe — and never a
 * risk/return point: two of those would draw the scatter, which needs a canvas jsdom does not have.
 *
 * **Both levels are tables now** (the developer's review, 30/09: L3° gets L1°'s treatment), so the
 * column toggle and the icons are asked of both: one toggle per level table, each in its own frame's
 * header before its own manual icon, each reading its own table; and the icons the panel resolved
 * reach both asset columns. The L3° halves are written red first, against the hand-written table they
 * replace.
 *
 * **The toolbar's period reaches L3°** (third review, 2026-10-01): the levels hand the section the
 * `dateStart`/`dateEnd` they were given, which its period note compares the calculated window against.
 * Observed through the note's `data-narrowed` alone, as this file reads no text; the window itself and
 * the note's sentences are `AssetSetRiskReturnSection.test.ts`'s. Written red first: the section has no
 * period note yet.
 *
 * **L1° and L3° ask apart** (the developer's decision, 2026-10-02): L1° is measured without the
 * benchmark, and only L3° asks with it — one question per level, each with its own load state and its
 * own retry. Pinned by the last blocks of this file; written red first, against the single question
 * both levels share today.
 *
 * **One notice for the lab** (the developer's decision, 2026-10-05): what came back `partial`, and
 * every warning, is said once by the lab panel's `RiskPartialNotice`, as the Dashboard says it above its
 * levels; each frame keeps only what did not come back at all (`levelErrorHealth`) and no reasons. The
 * panel reads what the levels render through `bind:this`, so the levels publish `qualitySource()`: their
 * six results in page order, `null` where absent, the two VaR horizons' labels, and their two
 * controllers' data-quality issues, L1°'s then L3°'s. Pinned by the final blocks; written red first,
 * against frames that still list a partial result and repeat its warning, and no `qualitySource`.
 *
 * Left elsewhere: the discard and re-ask rules themselves (`riskPanelController.test.ts`), the
 * tables' own cells (`AssetSetLossComparisonSection.test.ts`, `AssetSetRiskReturnSection.test.ts`,
 * `assetSetLevels.test.ts`), and the page end to end (`e2e/portfolio/risk-lab.spec.ts`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import type {z} from 'zod';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());
/** Every controller the levels create, in order. Observed, never replaced. */
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

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {assertEffectsRun, recordReads} from '$test/runes.svelte';
import type {schemas} from '$lib/api';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetComparisonLevels from './AssetSetComparisonLevels.svelte';
import type {AssetSetQualitySource} from './assetSetLevels';
import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE} from './riskAnalysisHelpers';

type VarCvarOutput = z.infer<typeof schemas.RiskAssetSetVarCvarOutput>;
type KpiOutput = z.infer<typeof schemas.RiskAssetSetKpiOutput>;

// Invented: a window, and a selection of two with their names.
const DATE_START = '2021-01-04';
const DATE_END = '2023-12-29';
const HOLDING_A = 12;
const HOLDING_B = 15;
const SELECTION = [HOLDING_A, HOLDING_B];
const LABELS: ReadonlyMap<number, string> = new Map([
    [HOLDING_A, 'Invented holding A'],
    [HOLDING_B, 'Invented holding B'],
]);
/** Invented: the icons the panel would resolve for the two holdings, passed through to both levels. */
const ICONS: ReadonlyMap<number, string> = new Map([
    [HOLDING_A, '/icons/asset-types/etf.png'],
    [HOLDING_B, '/icons/asset-types/stock.png'],
]);
const PROPS = {assetIds: SELECTION, assetLabels: LABELS, assetIcons: ICONS, dateStart: DATE_START, dateEnd: DATE_END, targetCurrency: 'EUR', benchmarkId: null as number | null, refreshVersion: 0};

/** Each level: the prefix its body publishes, and the testid of the frame it sits in. */
const LEVELS = [
    {level: 'l1', frame: 'risk-asset-set-loss'},
    {level: 'l3', frame: 'risk-asset-set-paid'},
] as const;
type Level = (typeof LEVELS)[number]['level'];

function ok(instanceId: string, output: VarCvarOutput): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: 'asset_set_var', status: 'ok', output};
}

/** Invented tails, CVaR ≥ VaR. 740 daily observations; a 30-day month is 21 of them, and compounding over 21 consumes 20. */
const FIGURES: RiskAnalyticResult[] = [
    ok(ASSET_SET_DAILY_VAR_INSTANCE, {
        kind: 'var_cvar_set',
        confidence_level: 0.95,
        horizon_days: 1,
        horizon_observations: 1,
        observations: 740,
        items: [
            {asset_id: HOLDING_A, value_at_risk: 0.024, conditional_value_at_risk: 0.037},
            {asset_id: HOLDING_B, value_at_risk: 0.015, conditional_value_at_risk: 0.022},
        ],
    }),
    ok(ASSET_SET_MONTHLY_VAR_INSTANCE, {
        kind: 'var_cvar_set',
        confidence_level: 0.95,
        horizon_days: 30,
        horizon_observations: 21,
        observations: 720,
        items: [
            {asset_id: HOLDING_A, value_at_risk: 0.094, conditional_value_at_risk: 0.133},
            {asset_id: HOLDING_B, value_at_risk: 0.061, conditional_value_at_risk: 0.084},
        ],
    }),
    // L3°'s figures: the KPI fills its volatility, Sortino and Sharpe cells. Invented: Sharpe is about
    // 0.7 × Sortino — a downside deviation near 70% of the volatility — and the fall is ≤ 0, as the
    // contract requires.
    {
        instance_id: 'base-historical-asset_set_kpi',
        analytic_code: 'asset_set_kpi',
        status: 'ok',
        output: {
            kind: 'kpi_set',
            drawdown_confidence_level: 0.95,
            items: [
                {asset_id: HOLDING_A, volatility: 0.21, max_drawdown: -0.27, max_drawdown_duration_days: 140, sharpe: 0.62, sortino: 0.88},
                {asset_id: HOLDING_B, volatility: 0.14, max_drawdown: -0.16, max_drawdown_duration_days: 95, sharpe: 0.41, sortino: 0.57},
            ],
        } satisfies KpiOutput,
    },
];

/**
 * How every base question is answered, and every question as it was asked.
 *
 *  - `figures`: the answer above;
 *  - `nothing`: an answer with no result in it — nothing failed, nothing measured;
 *  - `reject`: the request throws, as a failed wave does (`loadError`);
 *  - `discard`: `null`, what `queryRisk` returns for an answer that arrived and was discarded. The
 *    controller asks three times in all, and a third `null` is what sets `loadDiscarded`.
 */
type Outcome = 'figures' | 'nothing' | 'reject' | 'discard';
const script = {outcome: 'figures' as Outcome, asked: [] as {request: RiskQueryRequest; force: boolean}[]};

let consoleError: MockInstance<Console['error']>;

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    created.controllers.length = 0;
    script.outcome = 'figures';
    script.asked = [];
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        if (script.outcome === 'reject') throw new Error('invented: the base wave failed');
        if (script.outcome === 'discard') return null;
        return {items: script.outcome === 'figures' ? answerTo(request, FIGURES) : []};
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

/**
 * The results a question asked for, by instance — as the backend answers it: never a result for an
 * analytic another question carried. Today's single question asks for every fixture, so this changes
 * nothing for it; once the levels ask apart, each level gets its own figures and no one else's.
 */
function answerTo(request: RiskQueryRequest, results: RiskAnalyticResult[]): RiskAnalyticResult[] {
    const asked = new Set(request.analytics.map((analytic) => analytic.instance_id));
    return results.filter((result) => asked.has(result.instance_id));
}

function mount(props: typeof PROPS = PROPS) {
    const view = render(AssetSetComparisonLevels, {props});
    expect(created.controllers.length, 'the levels did not create a controller of their own').toBeGreaterThan(0);
    return {view, controllers: [...created.controllers] as RiskPanelController[]};
}

/** A controller's load states, named so that a premise over all of them reads as one: `controllers.every(hasFailed)`. */
const isLoading = (controller: RiskPanelController): boolean => controller.initialLoading;
const hasFailed = (controller: RiskPanelController): boolean => controller.loadError;
const wasDiscarded = (controller: RiskPanelController): boolean => controller.loadDiscarded;
const isBusy = (controller: RiskPanelController): boolean => controller.initialLoading || controller.refreshing;

/** Every controller the levels created has settled the base wave its mount fires. */
async function settled(controllers: RiskPanelController[]): Promise<void> {
    await waitFor(() => expect(controllers.some(isLoading), 'the base wave the mount fires never settled').toBe(false));
}

/** Mounted with the wave failing, and the premise: every controller recorded the failure. */
async function mountFailed(): Promise<RiskPanelController[]> {
    script.outcome = 'reject';
    const {controllers} = mount();
    await waitFor(() => expect(controllers.every(hasFailed), 'the controller never recorded the failure: the path under test did not run').toBe(true));
    expect(controllers.some(wasDiscarded), 'a failure is not a discard').toBe(false);
    return controllers;
}

/** Mounted with every answer discarded, and the premise: each question asked three times in all, and the discard recorded. */
async function mountDiscarded(): Promise<RiskPanelController[]> {
    script.outcome = 'discard';
    const {controllers} = mount();
    await waitFor(() => expect(controllers.every(wasDiscarded), 'the controller never recorded the discard: the path under test did not run').toBe(true));
    expect(script.asked, 'each base question was not asked three times in all — the first attempt and two re-asks').toHaveLength(3 * controllers.length);
    expect(controllers.some(hasFailed), 'a discard is not a failure').toBe(false);
    return controllers;
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A frame's error lines, as the codes they carry. */
function frameCodes(frame: string): string[] {
    return screen.queryAllByTestId(`${frame}-error`).map((line) => line.getAttribute('data-code') ?? '');
}

/** What a block says besides its button — its sentence, if it has one. Checked for presence, never read. */
function sentenceBeside(block: HTMLElement, button: HTMLElement): string {
    const copy = block.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(`[data-testid="${button.getAttribute('data-testid')}"]`).forEach((node) => node.remove());
    return normalize(copy.textContent);
}

/** The level's body block for a load state, which must hold the level's retry button. */
async function blockWithRetry(level: Level, state: 'error' | 'discarded', why: string): Promise<{block: HTMLElement; retry: HTMLElement}> {
    const block = await waitFor(() => {
        const found = screen.queryByTestId(`risk-asset-set-${level}-${state}`);
        expect(found, why).not.toBeNull();
        return found as HTMLElement;
    });
    const retry = within(block).queryByTestId(`risk-asset-set-${level}-retry`);
    expect(retry, `${level}: the ${state} block offers no retry`).not.toBeNull();
    expect(retry?.tagName, `${level}: the retry is not a button`).toBe('BUTTON');
    return {block, retry: retry as HTMLElement};
}

/**
 * An asset's L1 row, found by the asset id it carries — `[data-asset-id]`, walked up to its `tr` —
 * rather than by a row testid: L1° is the project's DataTable, whose rows publish `data-row-id`
 * and whose name cell carries the asset. The table's own structure is pinned in
 * `AssetSetLossComparisonSection.test.ts`; here a row only has to be found.
 */
function l1RowOf(assetId: number): HTMLElement | undefined {
    const carriers = screen.queryByTestId('risk-asset-set-l1-table')?.querySelectorAll<HTMLElement>(`[data-asset-id="${assetId}"]`) ?? [];
    const rows = [...new Set([...carriers].map((carrier) => carrier.closest('tr')))].filter((row): row is HTMLTableRowElement => row !== null);
    return rows.length === 1 ? rows[0] : undefined;
}

/** The barrier of the answer with figures: every selected asset has its L1 row, and its bad day is measured. */
async function expectFigures(): Promise<void> {
    await waitFor(() => {
        for (const assetId of SELECTION) {
            const row = l1RowOf(assetId);
            expect(row, `asset ${assetId} has no L1 row`).toBeDefined();
            expect(within(row as HTMLElement).getByTestId('risk-asset-set-l1-badDay'), `asset ${assetId}: the bad day is a dash — the fixture was rejected, or never arrived`).toHaveAttribute('data-measured', 'true');
        }
    });
}

/**
 * An asset's L3 row, found the way `l1RowOf` finds L1's: by the asset id it carries, walked up to its
 * `tr` — so it finds the row on the hand-written table (`tr[data-asset-id]`) and on the DataTable that
 * replaces it (the name cell carries the id) alike. The table's structure is pinned in
 * `AssetSetRiskReturnSection.test.ts`; here a row only has to be found.
 */
function l3RowOf(assetId: number): HTMLElement | undefined {
    const carriers = screen.queryByTestId('risk-asset-set-l3-table')?.querySelectorAll<HTMLElement>(`[data-asset-id="${assetId}"]`) ?? [];
    const rows = [...new Set([...carriers].map((carrier) => carrier.closest('tr')))].filter((row): row is HTMLTableRowElement => row !== null);
    return rows.length === 1 ? rows[0] : undefined;
}

/**
 * The same barrier for L3°: every selected asset has its L3 row, and its volatility is a figure rather
 * than the dash. Read as "not the blank" rather than through `data-measured`, which only the redesigned
 * cells publish, so that on either table this barrier stands and a red further on is about the case's
 * own subject.
 */
async function expectL3Figures(): Promise<void> {
    await waitFor(() => {
        for (const assetId of SELECTION) {
            const row = l3RowOf(assetId);
            expect(row, `asset ${assetId} has no L3 row`).toBeDefined();
            expect(normalize(within(row as HTMLElement).getByTestId('risk-asset-set-l3-volatility').textContent), `asset ${assetId}: the volatility is a dash — the KPI fixture was rejected, or never arrived`).not.toBe('\u2014');
        }
    });
}

/** None of the load-state chrome in one level: no body block, no retry, and no frame saying an answer was discarded. */
function expectNoLoadChromeIn(level: Level, frame: string, why: string): void {
    for (const part of ['error', 'discarded', 'retry']) {
        expect(screen.queryByTestId(`risk-asset-set-${level}-${part}`), `${why}: ${level} shows risk-asset-set-${level}-${part}`).toBeNull();
    }
    expect(frameCodes(frame), `${why}: the ${level} frame says an answer was discarded`).not.toContain(ANSWER_DISCARDED_CODE);
}

/** None of the load-state chrome, in either level. */
function expectNoLoadChrome(why: string): void {
    for (const {level, frame} of LEVELS) expectNoLoadChromeIn(level, frame, why);
}

/** Press a retry and prove it asked the base question again, past the cache; then let the wave settle. */
async function expectRetryAsksAgain(level: Level, retry: HTMLElement, settledAgain: () => void): Promise<void> {
    const before = script.asked.length;
    await fireEvent.click(retry);

    await waitFor(() => expect(script.asked.length, `${level}: pressing retry asked nothing`).toBeGreaterThan(before));
    expect(
        script.asked.slice(before).every((question) => question.force),
        `${level}: the retry must ask past the cache — controller.loadBase(true)`,
    ).toBe(true);
    await waitFor(settledAgain);
}

describe('AssetSetComparisonLevels — the harness itself', () => {
    it('runs effects, asks one question per base load, and its figures survive the parsers', async () => {
        expect(() => assertEffectsRun()).not.toThrow();

        const {controllers} = mount();
        await settled(controllers);
        expect(script.asked, 'one base load must be one question per controller: the capability gate lets only the asset-set wave through').toHaveLength(controllers.length);
        expect(
            script.asked.flatMap(({request}) => request.analytics.map((analytic) => analytic.analytic_code)),
            'the questions are not the per-asset wave these levels read',
        ).toEqual(expect.arrayContaining(['asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_kpi']));

        // An answer with figures is a complement's barrier below: its fixtures must reach the cells, both levels'.
        await expectFigures();
        await expectL3Figures();
    });
});

describe('AssetSetComparisonLevels — a base wave that fails', () => {
    it('shows, in each level, a sentence and a retry, and nothing of a discard', async () => {
        await mountFailed();

        for (const {level} of LEVELS) {
            const {block, retry} = await blockWithRetry(level, 'error', `${level}: the base wave failed and the level shows its rows of dashes without a word — an empty table reads as "nothing measured", not "ask again"`);
            expect(sentenceBeside(block, retry), `${level}: the error block offers a retry but no sentence saying what failed`).not.toBe('');
            expect(screen.queryByTestId(`risk-asset-set-${level}-discarded`), `${level}: a failed wave is shown as a discarded answer`).toBeNull();
        }
    });

    it.each(LEVELS.map(({level}) => level))('the %s retry asks the base question again, past the cache', async (level) => {
        const controllers = await mountFailed();
        const {retry} = await blockWithRetry(level, 'error', `${level}: the base wave failed and the level offers no way to ask again`);

        await expectRetryAsksAgain(level, retry, () => expect(controllers.every(hasFailed), 'the re-asked wave never settled').toBe(true));
    });
});

describe('AssetSetComparisonLevels — a base answer discarded three times running', () => {
    it("is said once in each level's frame, as answer_discarded, and each body offers the retry and nothing else", async () => {
        await mountDiscarded();

        for (const {level, frame} of LEVELS) {
            await waitFor(() => expect(frameCodes(frame), `${level}: the controller recorded a discarded answer and the level's frame does not say so`).toEqual([ANSWER_DISCARDED_CODE]));
            expect(normalize(screen.getByTestId(`${frame}-error`).textContent), `${level}: the frame's line carries no sentence`).not.toBe('');

            const {block, retry} = await blockWithRetry(level, 'discarded', `${level}: the answer was discarded and the level offers no way to ask again`);
            expect(sentenceBeside(block, retry), `${level}: the discarded block carries a sentence of its own — the frame's line already says it, once`).toBe('');
            expect(screen.queryByTestId(`risk-asset-set-${level}-error`), `${level}: a discarded answer is shown as a failed wave`).toBeNull();
        }
    });

    it.each(LEVELS.map(({level}) => level))('the %s retry asks the base question again, past the cache', async (level) => {
        const controllers = await mountDiscarded();
        const {retry} = await blockWithRetry(level, 'discarded', `${level}: the answer was discarded and the level offers no way to ask again`);
        const before = script.asked.length;

        // Discarded again, and re-asked by the controller itself until its third attempt: three more questions.
        await expectRetryAsksAgain(level, retry, () => {
            expect(script.asked.length, 'the re-asked wave never settled').toBe(before + 3);
            expect(controllers.every(wasDiscarded)).toBe(true);
        });
    });

    it('after an answer with figures, keeps them: the frames say the new answer was lost, and both levels keep their tables', async () => {
        const {view, controllers} = mount();
        await settled(controllers);
        await expectFigures();
        await expectL3Figures();

        // An accepted sync re-reads the base, and its answer is discarded three times running.
        const before = script.asked.length;
        script.outcome = 'discard';
        view.rerender({refreshVersion: 1});
        await waitFor(() => expect(controllers.every(wasDiscarded), 'the refreshed answer was never recorded as discarded').toBe(true));
        expect(script.asked.length - before, 'the refresh was not asked three times in all, question by question').toBe(3 * controllers.length);

        // The discard kept the answer on screen, and says it lost the new one.
        await expectFigures();
        await expectL3Figures();
        for (const {level, frame} of LEVELS) {
            await waitFor(() => expect(frameCodes(frame), `${level}: an answer was discarded and the level's frame does not say so`).toEqual([ANSWER_DISCARDED_CODE]));
            expect(screen.queryByTestId(`risk-asset-set-${level}-discarded`), `${level} has figures: the discarded block is for a level with none, not a replacement for the table`).toBeNull();
            expect(screen.queryByTestId(`risk-asset-set-${level}-error`), `${level}: a discarded answer is shown as a failed wave`).toBeNull();
        }
    });
});

describe('AssetSetComparisonLevels — an answer: nothing failed, nothing discarded', () => {
    it('with figures, shows none of it', async () => {
        const {controllers} = mount();
        await settled(controllers);
        await expectFigures();

        expectNoLoadChrome('an answer with figures');
    });

    it('that measured nothing, shows none of it either: a blank is not a failure', async () => {
        script.outcome = 'nothing';
        const {controllers} = mount();
        await settled(controllers);
        expect(controllers.some(hasFailed)).toBe(false);
        expect(controllers.some(wasDiscarded)).toBe(false);

        // The barrier: both tables drawn, a row per selected asset, nothing measured — the very
        // picture a failed or discarded wave used to leave behind.
        await waitFor(() => {
            expect(screen.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(SELECTION.length));
            expect(screen.getByTestId('risk-asset-set-l3-table')).toHaveAttribute('data-row-count', String(SELECTION.length));
        });
        for (const cell of screen.getAllByTestId('risk-asset-set-l1-badDay')) expect(cell).toHaveAttribute('data-measured', 'false');

        expectNoLoadChrome('an answer that measured nothing');
    });
});

/**
 * Each level's column toggle — the project's `ColumnVisibilityToggle`, in the level frame's header
 * just before its manual icon (`RiskLevelSection`'s `actions`), bound to the level's table through
 * the section's bindable `tableRef`: L1° (`risk-asset-set-loss`) reads the loss table, and — since the
 * developer's review of 30/09 gave L3° the same table — L3° (`risk-asset-set-paid`) reads its own.
 *
 * It exists only while its table does: a toggle beside no table opens onto nothing, or onto the
 * columns of a table the reader cannot see. So it is absent while the first answer is in flight,
 * after a failed wave, and after an answer discarded with nothing to keep — and each of those
 * cases then brings the table and proves the toggle arrives with it, which is what keeps the
 * absence from passing about a page that has no toggle at all. Wherever the table is drawn it is
 * there: with figures, with an answer that measured nothing (a row of dashes per selected asset
 * is still a table), and when a later answer is discarded and the figures stay. One toggle per
 * level table: two on the page.
 *
 * Found by testid; the menu is read by its items' testids, never by their labels. Switching a
 * column off and on is the E2E's (`risk-lab.spec.ts`): here the table only has to be the one the
 * menu reads — its own level's, and not the other's.
 */

/** Each level's table: the frame its toggle sits in, the value columns its menu lists, and its figures barrier. */
const TABLE_LEVELS = [
    {name: 'L1°', level: 'l1', frame: 'risk-asset-set-loss', columns: ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak'], figures: expectFigures},
    {name: 'L3°', level: 'l3', frame: 'risk-asset-set-paid', columns: ['volatility', 'expectedReturn', 'sortino', 'sharpe'], figures: expectL3Figures},
] as const;

/** A frame's column toggle, if it has one. */
function toggleIn(frame: HTMLElement): HTMLElement | null {
    return within(frame).queryByTestId('column-visibility-toggle');
}

/** Whether `first` comes before `second` in document order, `second` not inside it. */
function precedes(first: Node, second: Node): boolean {
    return !first.contains(second) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** A level's toggle, waited for: the barrier of every case in which its table is drawn. */
async function expectToggle(frame: string, why: string): Promise<HTMLElement> {
    return waitFor(() => {
        const toggle = toggleIn(screen.getByTestId(frame));
        expect(toggle, why).not.toBeNull();
        return toggle as HTMLElement;
    });
}

/**
 * No toggle in a level's frame — asserted with the frame's header drawn, its title and its manual
 * icon, and with no table, which is the state's own premise: the absence is about the toggle.
 */
function expectNoToggle(level: Level, frame: string, why: string): void {
    const section = screen.getByTestId(frame);
    within(section).getByTestId(`${frame}-title`);
    within(section).getByTestId(`${frame}-docs`);
    expect(screen.queryByTestId(`risk-asset-set-${level}-table`), `${why} — premise: this state draws no table`).toBeNull();
    expect(toggleIn(section), why).toBeNull();
}

/**
 * Hold every base question in flight until the test releases it with the figures. The harness's
 * own answers settle at once, which leaves the skeleton on screen for no moment a test could rely
 * on. One test's scope: `beforeEach` installs the ordinary answers again.
 */
function holdAnswers(): () => void {
    const held: {request: RiskQueryRequest; resolve: (answer: {items: RiskAnalyticResult[]}) => void}[] = [];
    queryRisk.mockImplementation((request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        return new Promise((resolve) => held.push({request, resolve}));
    });
    return () => {
        for (const {request, resolve} of held.splice(0)) resolve({items: answerTo(request, FIGURES)});
    };
}

/** Press a retry with figures to answer it, and end on the level's figures: its table arrives. */
async function retryIntoFigures(retry: HTMLElement, figures: () => Promise<void>): Promise<void> {
    script.outcome = 'figures';
    await fireEvent.click(retry);
    await figures();
}

for (const {name, level, frame, columns, figures} of TABLE_LEVELS) {
    describe(`AssetSetComparisonLevels — ${name}'s column toggle, in its frame beside the manual icon`, () => {
        it("with figures: in its own frame's header, after the title and before the manual icon", async () => {
            const {controllers} = mount();
            await settled(controllers);
            await figures();
            const toggle = await expectToggle(frame, `${name} shows its figures and its frame offers no column toggle`);

            const section = screen.getByTestId(frame);
            expect(within(section).getByTestId(`${frame}-body`).contains(toggle), `the toggle is in ${name}'s body: it belongs to the frame's header`).toBe(false);
            expect(precedes(within(section).getByTestId(`${frame}-title`), toggle), `the toggle does not come after ${name}'s title, or sits inside it`).toBe(true);
            expect(precedes(toggle, within(section).getByTestId(`${frame}-docs`)), `the toggle does not come before ${name}'s manual icon`).toBe(true);
            expect(within(section).getAllByTestId('column-visibility-toggle'), `${name}'s frame carries one toggle, its own table's`).toHaveLength(1);
        });

        it("opening it lists this level's columns and none of the other's: the menu reads its own table", async () => {
            const {controllers} = mount();
            await settled(controllers);
            await figures();
            await fireEvent.click(await expectToggle(frame, `${name} shows its figures and its frame offers no column toggle`));

            const menu = await waitFor(() => within(screen.getByTestId(frame)).getByTestId('column-visibility-dropdown'));
            for (const column of columns) {
                expect(within(menu).queryByTestId(`column-visibility-item-${column}`), `the menu does not offer ${column}: the toggle is not reading ${name}'s table`).not.toBeNull();
            }
            const others = TABLE_LEVELS.filter((other) => other.level !== level).flatMap((other) => [...other.columns]);
            for (const column of others) {
                expect(within(menu).queryByTestId(`column-visibility-item-${column}`), `${name}'s menu offers ${column}: it is reading the other level's table`).toBeNull();
            }
        });

        it('is not there while the first answer is in flight, and arrives with the table', async () => {
            const release = holdAnswers();
            const {controllers} = mount();
            await waitFor(() => expect(script.asked, 'the base questions were never asked: nothing is in flight').toHaveLength(controllers.length));
            expect(controllers.every(isLoading), 'premise: the first answer is still loading').toBe(true);
            await waitFor(() => expect(screen.queryByTestId(`risk-asset-set-${level}-loading`), `${name} is not drawing its skeleton`).not.toBeNull());
            expectNoToggle(level, frame, 'a column toggle beside a skeleton');

            release();
            await figures();
            await expectToggle(frame, 'the table arrived without its toggle');
        });

        it('is not there after a failed wave, and arrives with the table a retry brings', async () => {
            await mountFailed();
            const {retry} = await blockWithRetry(level, 'error', `${name} shows no error block: the state under test is not on screen`);
            expectNoToggle(level, frame, 'a column toggle beside a failed wave');

            await retryIntoFigures(retry, figures);
            await expectToggle(frame, 'the retry brought the table without its toggle');
        });

        it('is not there after an answer discarded with nothing to keep, and arrives with the table a retry brings', async () => {
            await mountDiscarded();
            const {retry} = await blockWithRetry(level, 'discarded', `${name} shows no discarded block: the state under test is not on screen`);
            expectNoToggle(level, frame, 'a column toggle beside a discarded answer');

            await retryIntoFigures(retry, figures);
            await expectToggle(frame, 'the retry brought the table without its toggle');
        });

        it('is there with an answer that measured nothing: a row of dashes per selected asset is still a table', async () => {
            script.outcome = 'nothing';
            const {controllers} = mount();
            await settled(controllers);
            await waitFor(() => expect(screen.getByTestId(`risk-asset-set-${level}-table`)).toHaveAttribute('data-row-count', String(SELECTION.length)));

            await expectToggle(frame, `${name} draws its table and its frame offers no column toggle`);
        });

        it('stays when a later answer is discarded: the figures stay, and so does their toggle', async () => {
            const {view, controllers} = mount();
            await settled(controllers);
            await figures();
            await expectToggle(frame, `${name} shows its figures and its frame offers no column toggle`);

            script.outcome = 'discard';
            view.rerender({refreshVersion: 1});
            await waitFor(() => expect(controllers.every(wasDiscarded), 'the refreshed answer was never recorded as discarded').toBe(true));
            await figures();
            expect(toggleIn(screen.getByTestId(frame)), 'the figures stayed and their toggle went: it follows the table, not the load state').not.toBeNull();
        });
    });
}

describe('AssetSetComparisonLevels — one column toggle per level table', () => {
    it('with figures: two toggles on the page, one in each frame', async () => {
        const {controllers} = mount();
        await settled(controllers);
        await expectFigures();
        await expectL3Figures();

        for (const {name, frame} of TABLE_LEVELS) await expectToggle(frame, `${name} draws its table and its frame offers no column toggle`);
        expect(screen.getAllByTestId('column-visibility-toggle'), 'the levels carry one column toggle per table, L1° and L3°').toHaveLength(TABLE_LEVELS.length);
    });
});

/**
 * The icons the panel resolved (`assetIcons`) reach both tables' asset columns — the same map, handed
 * to each level, drawn by the same asset cell under each level's testids.
 */
describe('AssetSetComparisonLevels — the icons reach both tables', () => {
    for (const {name, level, figures} of TABLE_LEVELS) {
        it(`${name}: every asset cell draws the icon the panel resolved for it`, async () => {
            const {controllers} = mount();
            await settled(controllers);
            await figures();

            for (const assetId of SELECTION) {
                const cells = screen.getByTestId(`risk-asset-set-${level}-table`).querySelectorAll<HTMLElement>(`[data-testid="risk-asset-set-${level}-name"][data-asset-id="${assetId}"]`);
                expect(cells, `asset ${assetId}: no ${name} asset cell of its own`).toHaveLength(1);
                const icons = within(cells[0]).queryAllByTestId(`risk-asset-set-${level}-icon`);
                expect(icons, `asset ${assetId}: ${name} draws no icon — the levels did not hand it assetIcons`).toHaveLength(1);
                expect(icons[0].getAttribute('src'), `asset ${assetId}: ${name}'s icon is not the one the panel resolved`).toBe(ICONS.get(assetId));
            }
        });
    }
});

/**
 * The same answer under three selections: the window is the answer's, so only the comparison against
 * the toolbar's period moves — the selection itself, one that opens months before the first common
 * price, one that closes months after the last. A level that dropped either date would leave the
 * section comparing against nothing, and could not tell the last two from the first.
 */
describe("AssetSetComparisonLevels — the toolbar's period reaches L3°'s period note", () => {
    /**
     * Invented, and coherent with `DATE_START`…`DATE_END` for assets with history before it: the
     * baseline price on Sunday 3 January 2021 — the day before the selection opens, carried from the
     * last quote before it — the first return on Monday the 4th, the last on Friday 29 December 2023:
     * 1090 days from the baseline, over the 740 daily returns the VaR fixture counts. So the window is
     * the selection itself, its 1090 days both ends counted. Attached to every result of the answer, as
     * the API does.
     */
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
        algorithm_version: 'invented-asset-set',
        computed_at: '2026-10-01T09:00:00+00:00',
    } satisfies z.infer<typeof schemas.RiskResultMetadata>;
    const WINDOWED: RiskAnalyticResult[] = FIGURES.map((result) => ({...result, metadata: WINDOW}));

    it.each([
        {selection: 'equal to the window', dateStart: DATE_START, dateEnd: DATE_END, narrowed: false},
        {selection: 'opening months before it', dateStart: '2020-06-01', dateEnd: DATE_END, narrowed: true},
        {selection: 'closing months after it', dateStart: DATE_START, dateEnd: '2024-06-28', narrowed: true},
    ])('a selection $selection: narrowed $narrowed', async ({dateStart, dateEnd, narrowed}) => {
        queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
            script.asked.push({request, force: force === true});
            return {items: WINDOWED};
        });
        const {controllers} = mount({...PROPS, dateStart, dateEnd});
        await settled(controllers);
        await expectL3Figures();

        const note = await waitFor(() => screen.getByTestId('risk-asset-set-l3-period'));
        // The window is the answer's whatever the selection: only its comparison with the toolbar moves.
        expect(note).toHaveAttribute('data-start', DATE_START);
        expect(note).toHaveAttribute('data-end', DATE_END);
        expect(note).toHaveAttribute('data-days', '1090');
        expect(note, `against ${dateStart}…${dateEnd}: the levels did not hand L3° the toolbar's period`).toHaveAttribute('data-narrowed', String(narrowed));
    });
});

/**
 * L1° and L3° ask apart (the developer's decision, 2026-10-02). L1° — «How much did each of these
 * hurt?» — is measured without the benchmark; only L3° — «What did each of these pay for its risk?» —
 * asks with it. One question shared by both had the backend prepare a single joint window with the
 * benchmark inside, so a benchmark with stale prices turned L1° «Partial» for a reason L1° never asks
 * about. So each level has its own question: L1°'s carries the loss family and nothing of the
 * benchmark, L3°'s the paid family and, when a benchmark applies, the comparison against it. Changing
 * the benchmark re-asks L3° alone, and each level's loading, failure, discard and retry are its own.
 *
 * A question belongs to a level by the analytics it carries — never by its position, nor by which
 * controller sent it. Written red first: today one controller asks both levels' analytics in a single
 * question, so every case below goes red where it first needs two.
 */

/** The analytics that attribute a question to a level. `correlation` rides in every historical wave and attributes nothing. */
const LEVEL_CODES: Record<Level, readonly string[]> = {
    l1: ['asset_set_var', 'asset_set_drawdown'],
    l3: ['asset_set_kpi', 'asset_set_risk_return', 'asset_set_comparison'],
};
const LEVEL_NAMES: Record<Level, string> = {l1: 'L1°', l3: 'L3°'};

/** Invented benchmarks, outside the selection. Neither number occurs anywhere else in a question — not as an id, a horizon or a rate — so finding one means the benchmark is in it. */
const BENCHMARK = 47;
const OTHER_BENCHMARK = 53;

function otherThan(level: Level): Level {
    return level === 'l1' ? 'l3' : 'l1';
}

function codesOf(request: RiskQueryRequest): string[] {
    return request.analytics.map((analytic) => analytic.analytic_code);
}

/** Whether a question carries any of a level's analytics. */
function carries(request: RiskQueryRequest, level: Level): boolean {
    return codesOf(request).some((code) => LEVEL_CODES[level].includes(code));
}

/** The other level's analytics a question carries: none, once the levels ask apart. */
function foreignCodes(request: RiskQueryRequest, level: Level): string[] {
    return codesOf(request).filter((code) => LEVEL_CODES[otherThan(level)].includes(code));
}

/** Every question asked so far that carries a level's analytics. */
function questionsOf(level: Level): RiskQueryRequest[] {
    return script.asked.map(({request}) => request).filter((request) => carries(request, level));
}

/** Every key and every leaf of a question, however deep: where a benchmark would hide. */
function leavesOf(value: unknown): unknown[] {
    if (Array.isArray(value)) return value.flatMap(leavesOf);
    if (value !== null && typeof value === 'object') return Object.entries(value).flatMap(([key, child]) => [key, ...leavesOf(child)]);
    return [value];
}

/** The benchmark a question compares against, when it asks for a comparison. */
function comparedWith(request: RiskQueryRequest): unknown {
    const parameters = request.analytics.find((analytic) => analytic.analytic_code === 'asset_set_comparison')?.parameters as Record<string, unknown> | undefined;
    return parameters?.comparison_asset_id;
}

/** Whether a question asked since `before` compares against `benchmark`. */
function comparedSince(before: number, benchmark: number): boolean {
    return script.asked.slice(before).some(({request}) => comparedWith(request) === benchmark);
}

/** Every controller has settled whatever it was asking: no first load, no refresh in flight. */
async function quiet(controllers: RiskPanelController[]): Promise<void> {
    await waitFor(() => expect(controllers.some(isBusy), 'a base wave never settled').toBe(false));
}

/**
 * The split itself: a question of the level's own, carrying none of the other level's analytics. What
 * every case below first needs, and what today's single question is not.
 */
async function ownQuestion(level: Level): Promise<RiskQueryRequest> {
    const why = `${LEVEL_NAMES[level]} has no question of its own: its analytics still travel with ${LEVEL_NAMES[otherThan(level)]}'s, in one request`;
    return waitFor(() => {
        const own = questionsOf(level).filter((request) => !carries(request, otherThan(level)));
        expect(own.length, why).toBeGreaterThan(0);
        return own[0];
    });
}

/** What was asked since `before`: something, all of it past the cache, and nothing of the other level's. */
function expectAskedAlone(level: Level, before: number, who: string): void {
    const asked = script.asked.slice(before);
    const forced = asked.every(({force}) => force);
    const strays = asked.filter(({request}) => carries(request, otherThan(level))).map(({request}) => codesOf(request));
    expect(asked.length, `${who} asked nothing`).toBeGreaterThan(0);
    expect(forced, `${who} must ask past the cache — controller.loadBase(true)`).toBe(true);
    expect(strays, `${who} asked ${LEVEL_NAMES[otherThan(level)]}'s question too`).toEqual([]);
}

describe('AssetSetComparisonLevels — two questions: L1° is measured without the benchmark, only L3° asks with it', () => {
    it("with a benchmark: L1°'s question carries nothing of it, and L3°'s compares against it", async () => {
        const {controllers} = mount({...PROPS, benchmarkId: BENCHMARK});
        await settled(controllers);

        const loss = questionsOf('l1');
        expect(loss, 'L1° asked no question, or asked it more than once').toHaveLength(1);
        const leaked = "L1°'s question carries asset_set_comparison: the benchmark is prepared inside L1°'s window, so its prices decide whether L1° is Partial";
        expect(codesOf(loss[0]), leaked).not.toContain('asset_set_comparison');
        expect(leavesOf(loss[0]), "L1°'s question names the benchmark: L1° is measured without it").not.toContain(BENCHMARK);
        expect(leavesOf(loss[0]), "L1°'s question carries a comparison parameter: L1° is measured without the benchmark").not.toContain('comparison_asset_id');
        expect(foreignCodes(loss[0], 'l1'), "L1°'s question carries L3°'s analytics").toEqual([]);

        const paid = questionsOf('l3');
        expect(paid, 'L3° asked no question, or asked it more than once').toHaveLength(1);
        expect(foreignCodes(paid[0], 'l3'), "L3°'s question carries L1°'s analytics").toEqual([]);
        expect(comparedWith(paid[0]), "L3°'s question does not compare against the benchmark the panel chose").toBe(BENCHMARK);
        expect(codesOf(paid[0]), "L3°'s question lost its own analytics").toEqual(expect.arrayContaining(['asset_set_kpi', 'asset_set_risk_return']));
    });

    it("changing the benchmark re-asks L3°'s question alone: L1°'s is not asked again", async () => {
        const {view, controllers} = mount({...PROPS, benchmarkId: BENCHMARK});
        await settled(controllers);
        await expectFigures();
        const lossAsked = questionsOf('l1').length;
        const before = script.asked.length;

        await view.rerender({benchmarkId: OTHER_BENCHMARK});
        // The barrier: L3° asked again, against the new benchmark — then every wave settled.
        await waitFor(() => expect(comparedSince(before, OTHER_BENCHMARK), 'L3° never asked against the new benchmark: the change did not reach its question').toBe(true));
        await quiet(controllers);

        expect(questionsOf('l1').length - lossAsked, "changing the benchmark asked L1°'s question again: the benchmark still decides L1°'s window").toBe(0);
        await expectFigures();
    });

    it('without a benchmark: neither question carries a comparison', async () => {
        const {controllers} = mount();
        await settled(controllers);

        for (const level of ['l1', 'l3'] as const) {
            const question = await ownQuestion(level);
            expect(codesOf(question), `${LEVEL_NAMES[level]}'s question asks for a comparison with no benchmark chosen`).not.toContain('asset_set_comparison');
            expect(leavesOf(question), `${LEVEL_NAMES[level]}'s question carries a comparison parameter with no benchmark chosen`).not.toContain('comparison_asset_id');
        }
        const paid = await ownQuestion('l3');
        expect(codesOf(paid), 'without a benchmark L3° still asks what each asset was paid: the KPI and the risk/return').toEqual(expect.arrayContaining(['asset_set_kpi', 'asset_set_risk_return']));
    });
});

/** How a level's questions are answered. Read at call time, so a case can turn a level around before pressing its retry. */
type LevelOutcome = 'figures' | 'reject' | 'discard' | 'hold';

/**
 * Answer each question by the levels whose analytics it carries. A question carrying both — today's
 * single question — takes the outcome that is not an answer: one request cannot half-fail, which is
 * exactly why the levels ask apart. A held question gets its figures on `release()`.
 */
function scriptByLevel(outcomes: Record<Level, LevelOutcome>): () => void {
    const held: {request: RiskQueryRequest; resolve: (answer: {items: RiskAnalyticResult[]}) => void}[] = [];
    queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        const own = LEVELS.filter(({level}) => carries(request, level)).map(({level}) => outcomes[level]);
        if (own.includes('reject')) throw new Error("invented: this level's base wave failed");
        if (own.includes('discard')) return null;
        if (own.includes('hold')) return new Promise((resolve) => held.push({request, resolve}));
        return {items: answerTo(request, FIGURES)};
    });
    return () => {
        for (const {request, resolve} of held.splice(0)) resolve({items: answerTo(request, FIGURES)});
    };
}

/** Both levels answered with their figures, except `level`, answered with `outcome`. */
function allFiguresBut(level: Level, outcome: LevelOutcome): Record<Level, LevelOutcome> {
    const outcomes: Record<Level, LevelOutcome> = {l1: 'figures', l3: 'figures'};
    outcomes[level] = outcome;
    return outcomes;
}

for (const {name, level, frame, figures} of TABLE_LEVELS) {
    const other = TABLE_LEVELS.find((candidate) => candidate.level !== level) as (typeof TABLE_LEVELS)[number];

    describe(`AssetSetComparisonLevels — ${name}'s load state is its own: ${other.name} is untouched`, () => {
        it(`${name}'s question failing shows ${name}'s error and retry, and leaves ${other.name}'s table on screen; the retry asks ${name}'s question alone`, async () => {
            const outcomes = allFiguresBut(level, 'reject');
            scriptByLevel(outcomes);
            mount();
            await ownQuestion(level);
            await ownQuestion(other.level);

            const {retry} = await blockWithRetry(level, 'error', `${name}'s question failed and ${name} shows no error block`);
            await other.figures();
            expectNoLoadChromeIn(other.level, other.frame, `only ${name}'s question failed`);

            const before = script.asked.length;
            outcomes[level] = 'figures';
            await fireEvent.click(retry);
            await figures();
            expectAskedAlone(level, before, `${name}'s retry`);
            await other.figures();
        });

        it(`${name}'s answer discarded twice running is said in ${name}'s frame alone; the retry asks ${name}'s question alone`, async () => {
            const outcomes = allFiguresBut(level, 'discard');
            scriptByLevel(outcomes);
            mount();
            await ownQuestion(level);
            await ownQuestion(other.level);

            await waitFor(() => expect(frameCodes(frame), `${name}'s answer was discarded and its frame does not say so`).toEqual([ANSWER_DISCARDED_CODE]));
            const {retry} = await blockWithRetry(level, 'discarded', `${name}'s answer was discarded and ${name} offers no way to ask again`);
            await other.figures();
            expectNoLoadChromeIn(other.level, other.frame, `only ${name}'s answer was discarded`);

            const before = script.asked.length;
            outcomes[level] = 'figures';
            await fireEvent.click(retry);
            await figures();
            expectAskedAlone(level, before, `${name}'s retry`);
            expect(frameCodes(frame), `${name} was answered on retry and its frame still says the answer was discarded`).not.toContain(ANSWER_DISCARDED_CODE);
        });

        it(`${name}'s question in flight keeps ${name}'s skeleton alone: ${other.name} draws its answer meanwhile`, async () => {
            const release = scriptByLevel(allFiguresBut(level, 'hold'));
            mount();
            await ownQuestion(level);
            await ownQuestion(other.level);

            await other.figures();
            expect(screen.queryByTestId(`risk-asset-set-${level}-loading`), `${name}'s question is still in flight and ${name} shows no skeleton`).not.toBeNull();
            expect(screen.queryByTestId(`risk-asset-set-${other.level}-loading`), `${other.name} has its answer and still shows a skeleton`).toBeNull();

            release();
            await figures();
        });
    });
}

/**
 * ─── One notice for the lab: each frame keeps what did not come back at all ──────────────────
 *
 * The developer's decision of 2026-10-05, the Dashboard's pattern (`RiskLevelsPanel`): the frames of
 * L1–L3 pass `levelErrorHealth(health)` — `unavailable` and `failed`, never `partial` — and no
 * `reasons`, and what came back partial, with every warning, is said once by `RiskPartialNotice`. In
 * the lab that notice is the panel's, fed by what the correlation section, L1° and L3° render. So a
 * level's frame here:
 *
 *   - lists no `partial` result in `{frame}-health`, and shows no `{frame}-reasons` at all — neither a
 *     partial result's warning nor a note on a complete one;
 *   - still lists what did not come back at all, with its error codes: `data-count` is the number of
 *     its `unavailable` and `failed` results, whatever partial result sits beside them.
 *
 * Each frame is read after its body has drawn the figures of the very result under test (the barriers
 * above), so an absence is about where a disclosure lives, never about an answer that had not landed.
 * The warnings are invented and never read: routed, not worded.
 */

/** The instance ids of the results `FIGURES` does not carry, as `buildBaseAnalytics` names them (`base-historical-<code>`). */
const DRAWDOWN_INSTANCE = 'base-historical-asset_set_drawdown';
const RISK_RETURN_INSTANCE = 'base-historical-asset_set_risk_return';
const KPI_INSTANCE = 'base-historical-asset_set_kpi';
const COMPARISON_INSTANCE = 'base-historical-asset_set_comparison';
/** The `correlation` that rides in every historical question — each level's too, though neither level draws it. */
const CORRELATION_INSTANCE = 'base-historical-correlation';

type ResultWarning = NonNullable<RiskAnalyticResult['warnings']>[number];

/** Invented: a warning that degrades the result it rides on, as an excluded asset or a carried price does. */
const PARTIAL_WARNING: ResultWarning = {code: 'invented_carried_price', message: 'Invented: one price was carried forward over a gap.', degrades_result: true};
/** Invented: a note on a result that is whole (`degrades_result: false`) — the case `resultReasons` refuses to hide. */
const NOTE_WARNING: ResultWarning = {code: 'invented_note', message: 'Invented: a note on a figure that is whole.', degrades_result: false};

/** What stops a measurement from coming back at all, by the status it then carries: the codes a frame words under itself. */
const STOPPED_BY = {unavailable: 'insufficient_history', failed: 'execution_failed'} as const;
type Stopped = keyof typeof STOPPED_BY;

/** The fixture of `FIGURES` that answers an instance. */
function figure(instanceId: string): RiskAnalyticResult {
    const found = FIGURES.find((result) => result.instance_id === instanceId);
    if (!found) throw new Error(`FIGURES carries no ${instanceId}`);
    return found;
}

/** A result with figures turned partial by a warning — its output kept, as the backend keeps it. */
function partial(instanceId: string): RiskAnalyticResult {
    return {...figure(instanceId), status: 'partial', warnings: [PARTIAL_WARNING]};
}

/** A complete result with figures that still carries a note. */
function noted(instanceId: string): RiskAnalyticResult {
    return {...figure(instanceId), status: 'ok', warnings: [NOTE_WARNING]};
}

/** A result that did not come back at all: no output, by contract, and the code of what stopped it. */
function stopped(instanceId: string, analyticCode: string, status: Stopped): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: analyticCode, status, output: null, error: {code: STOPPED_BY[status], message: `Invented: ${analyticCode} came back ${status}.`}};
}

function isStopped(result: RiskAnalyticResult): boolean {
    return result.status === 'unavailable' || result.status === 'failed';
}

/** The result each level's barrier reads its figures from: L1°'s bad day, L3°'s KPI (its volatility). */
const BARRIER_INSTANCE: Record<Level, string> = {l1: ASSET_SET_DAILY_VAR_INSTANCE, l3: KPI_INSTANCE};

/** `FIGURES`, with the result of one instance replaced. */
function figuresWith(instanceId: string, replace: (instanceId: string) => RiskAnalyticResult): RiskAnalyticResult[] {
    return FIGURES.map((result) => (result.instance_id === instanceId ? replace(instanceId) : result));
}

/**
 * Each level's three results, every one in a state of its own: the partial one still draws its figures
 * (the barrier), the other two did not come back at all — one `unavailable`, one `failed`. L3°'s
 * comparison is asked only with a benchmark, so a case answering it mounts with one.
 */
const MIXED: Record<Level, RiskAnalyticResult[]> = {
    l1: [partial(ASSET_SET_DAILY_VAR_INSTANCE), stopped(ASSET_SET_MONTHLY_VAR_INSTANCE, 'asset_set_var', 'unavailable'), stopped(DRAWDOWN_INSTANCE, 'asset_set_drawdown', 'failed')],
    l3: [stopped(RISK_RETURN_INSTANCE, 'asset_set_risk_return', 'unavailable'), partial(KPI_INSTANCE), stopped(COMPARISON_INSTANCE, 'asset_set_comparison', 'failed')],
};
const MIXED_ALL: RiskAnalyticResult[] = [...MIXED.l1, ...MIXED.l3];

/** Answer every question with the results it asked for, out of `results`, and keep it. One test's scope: `beforeEach` installs the ordinary answers again. */
function answerWith(results: RiskAnalyticResult[]): void {
    queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        return {items: answerTo(request, results)};
    });
}

for (const {name, level, frame, figures} of TABLE_LEVELS) {
    describe(`AssetSetComparisonLevels — ${name}'s frame keeps only what did not come back at all: the lab's notice says the rest`, () => {
        it(`a partial result carrying a warning is named in neither ${name}'s health nor its reasons`, async () => {
            const instance = BARRIER_INSTANCE[level];
            answerWith(figuresWith(instance, partial));
            const {controllers} = mount();
            await settled(controllers);
            expect(
                controllers.some((controller) => controller.historicalResults.some((result) => result.instance_id === instance && result.status === 'partial')),
                `premise: no controller holds ${name}'s partial result`,
            ).toBe(true);
            // The barrier: the partial result's own figures are in the cells.
            await figures();

            expect(screen.queryByTestId(`${frame}-health`), `${name} still lists a partial result in its frame: the lab's one notice names it, once`).toBeNull();
            expect(screen.queryByTestId(`${frame}-reasons`), `${name} still repeats a partial result's warning in its frame: the lab's one notice says it, once`).toBeNull();
        });

        it(`a note on a complete result is not repeated in ${name}'s frame either: the frame carries no reasons at all`, async () => {
            answerWith(figuresWith(BARRIER_INSTANCE[level], noted));
            const {controllers} = mount();
            await settled(controllers);
            // The barrier: the noted result's own figures are in the cells.
            await figures();

            expect(screen.queryByTestId(`${frame}-reasons`), `${name} still words a warning in its frame: every warning is the lab's notice's, partial or not`).toBeNull();
            expect(screen.queryByTestId(`${frame}-health`), `${name} lists a complete result as degraded`).toBeNull();
        });

        it(`beside a partial result, ${name}'s health still lists what did not come back at all — the unavailable and the failed, not the partial — with their codes`, async () => {
            answerWith(MIXED_ALL);
            const {controllers} = mount({...PROPS, benchmarkId: BENCHMARK});
            await settled(controllers);
            // The barrier: the partial result's own figures are in the cells.
            await figures();

            const health = await waitFor(() => screen.getByTestId(`${frame}-health`));
            const missing = MIXED[level].filter(isStopped);
            expect(health, `${name}'s health must count its ${missing.length} unavailable and failed results, and leave the partial one to the lab's notice`).toHaveAttribute('data-count', String(missing.length));
            expect([...frameCodes(frame)].sort(), `${name}'s error codes are not what stopped its results: what did not come back keeps its cause under its level`).toEqual(missing.map((result) => STOPPED_BY[result.status as Stopped]).sort());
            expect(screen.queryByTestId(`${frame}-reasons`), `${name} still repeats the partial result's warning in its frame`).toBeNull();
        });
    });
}

/**
 * ─── `qualitySource()`: what the lab panel reads through `bind:this` ───────────────────────────
 *
 * The notice is the panel's; the results are the levels'. The panel feeds `partialNotice` with
 * `qualitySource().results` and `.labels`, and merges `.issues` with the correlation section's, so the
 * export hands over exactly what the two frames render — the controllers' own objects, in page order,
 * `null` where the answer had none, whatever their status — and stays reactive: the panel calls it
 * inside a `$derived`, so an effect reading it must re-run when the store answers again.
 *
 * ⚠️ "The objects the store answered" are the controllers' `historicalResults`. A controller keeps its
 * answer in `$state`, which wraps every result in a proxy, so the fixture `queryRisk` returned is never
 * the object a frame reads — `===` against it would fail on any implementation. Identity is checked
 * against the controller's own entry, the one the frame reads; content against the fixture.
 */

/** The six results the two frames render, in page order — L1°'s three, then L3°'s in its frame's order — with the level whose controller holds each. */
const RENDERED: ReadonlyArray<{level: Level; instanceId: string}> = [
    {level: 'l1', instanceId: ASSET_SET_DAILY_VAR_INSTANCE},
    {level: 'l1', instanceId: ASSET_SET_MONTHLY_VAR_INSTANCE},
    {level: 'l1', instanceId: DRAWDOWN_INSTANCE},
    {level: 'l3', instanceId: RISK_RETURN_INSTANCE},
    {level: 'l3', instanceId: KPI_INSTANCE},
    {level: 'l3', instanceId: COMPARISON_INSTANCE},
];

/** The two VaR horizons share an analytic code, so the notice names them by instance — with the keys of their own L1° columns. */
const VAR_LABELS = {
    [ASSET_SET_DAILY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badDay',
    [ASSET_SET_MONTHLY_VAR_INSTANCE]: 'risk.assetSet.levels.l1.columns.badMonth',
};

/** The levels' `qualitySource`, reached through the instance the harness mounted — as the panel reaches it, through `bind:this`. */
function qualitySourceOf(view: {component: unknown}): () => AssetSetQualitySource {
    const read = (view.component as {qualitySource?: unknown}).qualitySource;
    expect(typeof read, 'the levels export no qualitySource(): the lab panel has nothing to read their results and issues through bind:this').toBe('function');
    return read as () => AssetSetQualitySource;
}

/** The entry a controller holds for an instance — the very object its frame reads — or null. */
function heldBy(controller: RiskPanelController, instanceId: string): RiskAnalyticResult | null {
    return controller.historicalResults.find((result) => result.instance_id === instanceId) ?? null;
}

/** The controller whose answer carries a level's own analytics: found by what it holds, never by creation order. */
function controllerOf(controllers: RiskPanelController[], level: Level): RiskPanelController {
    const owners = controllers.filter((controller) => controller.historicalResults.some((result) => LEVEL_CODES[level].includes(result.analytic_code)));
    expect(owners, `premise: not exactly one controller holds ${LEVEL_NAMES[level]}'s analytics`).toHaveLength(1);
    return owners[0];
}

/** What `results` must be: in each slot, the entry its level's controller holds for it, or null. */
function heldResults(controllers: RiskPanelController[]): Array<RiskAnalyticResult | null> {
    const owners: Record<Level, RiskPanelController> = {l1: controllerOf(controllers, 'l1'), l3: controllerOf(controllers, 'l3')};
    return RENDERED.map(({level, instanceId}) => heldBy(owners[level], instanceId));
}

/** Slot by slot: the same instances in the same order, then the very same objects. */
function expectSameResults(actual: ReadonlyArray<RiskAnalyticResult | null>, expected: ReadonlyArray<RiskAnalyticResult | null>, when: string): void {
    expect(
        actual.map((result) => result?.instance_id ?? null),
        `${when}: not the six results the two frames render, in page order`,
    ).toEqual(expected.map((result) => result?.instance_id ?? null));
    actual.forEach((result, index) => expect(result, `${when}: ${RENDERED[index].instanceId} is not the object its controller holds — the notice would read a copy, not what the frame reads`).toBe(expected[index]));
}

/** The latest value an effect read, or the error its read threw. */
function lastRead<T>(values: ReadonlyArray<T | Error>): T {
    const last = values.at(-1);
    if (last === undefined) throw new Error('the effect never read qualitySource()');
    if (last instanceof Error) throw last;
    return last;
}

/** Invented: one data-quality issue per level's answer, different so their order is observable. */
type QualityIssue = NonNullable<z.infer<typeof schemas.DataQualityReport>['issues']>[number];
const LOSS_ISSUE: QualityIssue = {domain: 'asset', code: 'STALE_PRICE', severity: 'warning', message_i18n_key: 'invented.dataQuality.stalePrice', affected_asset_ids: [HOLDING_A]};
const PAID_ISSUE: QualityIssue = {domain: 'forex', code: 'FX_PAIR_PARTIAL_GAP', severity: 'info', message_i18n_key: 'invented.dataQuality.fxGap', affected_fx_pairs: ['USD/EUR']};

/**
 * The `correlation` a level's question carries, with an issue planted in its data quality. It is the
 * one result of an asset-set answer a controller reads `dataQualityIssues` from — `allResults` knows
 * `correlation` and not the per-asset family — and it rides in both levels' questions, so each level's
 * answer carries its own.
 */
function correlationCarrying(issue: QualityIssue): RiskAnalyticResult {
    return {instance_id: CORRELATION_INSTANCE, analytic_code: 'correlation', status: 'ok', output: null, data_quality: {issues: [issue], data_quality_status: 'carried_forward'}};
}

/** Answer each question with its own level's results: routed by the analytics it carries, so the `correlation` both ask for can differ per level. */
function answerPerLevel(byLevel: Record<Level, RiskAnalyticResult[]>): void {
    queryRisk.mockImplementation(async (request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        const own = LEVELS.filter(({level}) => carries(request, level)).flatMap(({level}) => byLevel[level]);
        return {items: answerTo(request, own)};
    });
}

describe('AssetSetComparisonLevels — qualitySource(), what the lab panel reads through bind:this', () => {
    it("returns the six results the two frames render, in page order — the controllers' own, null where the answer had none", async () => {
        const {view, controllers} = mount();
        await settled(controllers);
        await expectFigures();
        await expectL3Figures();

        const {results} = qualitySourceOf(view)();
        const answered = new Set(FIGURES.map((result) => result.instance_id));
        expect(
            results.map((result) => result?.instance_id ?? null),
            'not the bad day, the bad month, the drawdown, then the risk/return, the KPI and the comparison — null where the answer had none',
        ).toEqual(RENDERED.map(({instanceId}) => (answered.has(instanceId) ? instanceId : null)));
        expectSameResults(results, heldResults(controllers), 'the ordinary answer');
    });

    it('with all six answered, whatever their status, returns all six: nothing is filtered, the notice decides what is partial', async () => {
        answerWith(MIXED_ALL);
        const {view, controllers} = mount({...PROPS, benchmarkId: BENCHMARK});
        await settled(controllers);
        await expectFigures();
        await expectL3Figures();

        const {results} = qualitySourceOf(view)();
        expectSameResults(results, heldResults(controllers), 'every result answered');
        results.forEach((result, index) => {
            const {instanceId} = RENDERED[index];
            expect(result, `${instanceId} does not carry what the store answered`).toEqual(MIXED_ALL.find((answered) => answered.instance_id === instanceId));
        });
    });

    it('labels the two VaR horizons by instance, with the keys of their own columns: they share an analytic code', async () => {
        const {view, controllers} = mount();
        await settled(controllers);

        expect(qualitySourceOf(view)().labels, 'the notice would name the bad day and the bad month alike').toEqual(VAR_LABELS);
    });

    it("issues: L1°'s controller's data-quality issues, then L3°'s — concatenated, as the controllers hold them", async () => {
        answerPerLevel({l1: [...FIGURES, correlationCarrying(LOSS_ISSUE)], l3: [...FIGURES, correlationCarrying(PAID_ISSUE)]});
        const {view, controllers} = mount();
        await settled(controllers);
        await expectFigures();
        await expectL3Figures();
        const loss = controllerOf(controllers, 'l1');
        const paid = controllerOf(controllers, 'l3');
        expect(
            loss.dataQualityIssues.map((issue) => issue.code),
            "premise: L1°'s controller does not hold the issue planted in L1°'s answer",
        ).toEqual([LOSS_ISSUE.code]);
        expect(
            paid.dataQualityIssues.map((issue) => issue.code),
            "premise: L3°'s controller does not hold the issue planted in L3°'s answer",
        ).toEqual([PAID_ISSUE.code]);

        const {issues} = qualitySourceOf(view)();
        expect(issues, "not L1°'s controller's issues followed by L3°'s").toEqual([...loss.dataQualityIssues, ...paid.dataQualityIssues]);
        expect(
            issues.map((issue) => issue.code),
            "the order: L1°'s first, then L3°'s",
        ).toEqual([LOSS_ISSUE.code, PAID_ISSUE.code]);
    });

    it('answered again, returns the new results — to a plain call, and to an effect that reads it, as the panel does', async () => {
        const {view, controllers} = mount({...PROPS, benchmarkId: BENCHMARK});
        await settled(controllers);
        await expectFigures();
        const source = qualitySourceOf(view);
        const reads = recordReads(() => source());
        try {
            expectSameResults(lastRead(reads.values).results, heldResults(controllers), 'the first answer, read by an effect');

            // An accepted sync re-reads the base, and the store answers with every result changed.
            answerWith(MIXED_ALL);
            await view.rerender({refreshVersion: 1});
            await waitFor(() => {
                expect(heldBy(controllerOf(controllers, 'l1'), DRAWDOWN_INSTANCE)?.status, 'the second answer never reached L1°').toBe('failed');
                expect(heldBy(controllerOf(controllers, 'l3'), COMPARISON_INSTANCE)?.status, 'the second answer never reached L3°').toBe('failed');
            });
            await quiet(controllers);

            const now = heldResults(controllers);
            expectSameResults(source().results, now, 'a plain call after the second answer');
            await waitFor(() => expectSameResults(lastRead(reads.values).results, now, "an effect reading qualitySource() after the second answer — it never re-ran, so the panel's notice would keep the first"));
        } finally {
            reads.stop();
        }
    });
});
