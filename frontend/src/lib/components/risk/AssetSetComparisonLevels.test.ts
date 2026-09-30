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
 * **The harness is `AssetSetReplaySection.test.ts`'s.** The controller is the real one, observed
 * through its factory, so every case first states its premise — the controller did record the
 * failure, or the discard — before asserting what the page makes of it. `queryRisk` answers by
 * outcome and keeps every question with its `force` flag. Capabilities are gated the way the
 * backend declares them for an asset set (historical only; the correlation and the per-asset
 * family), so one base load is one question and "asked again" is a count.
 *
 * **No text is asserted.** Testids, `data-code` and `data-measured` are the contract; a sentence
 * is only checked to be there (non-empty) or not there, never read.
 *
 * ⚠️ Every figure and name below is invented, shaped to pass the schemas the levels parse it
 * through (`assetSetLevels.ts`); nothing was read off a running backend. The answer with figures
 * carries L1's two VaR horizons only: an L3 figure has no attribute to be observed by, and two
 * risk/return points would draw the scatter, which needs a canvas jsdom does not have.
 *
 * Left elsewhere: the discard and re-ask rules themselves (`riskPanelController.test.ts`), the
 * tables' own cells (`AssetSetLossComparisonSection.test.ts`, `assetSetLevels.test.ts`), and the
 * page end to end (`e2e/portfolio/risk-lab.spec.ts`).
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
import {assertEffectsRun} from '$test/runes.svelte';
import type {schemas} from '$lib/api';
import type {RiskQueryRequest} from '$lib/risk/riskRequest';
import {ANSWER_DISCARDED_CODE, type RiskPanelController} from '$lib/stores/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import AssetSetComparisonLevels from './AssetSetComparisonLevels.svelte';
import {ASSET_SET_DAILY_VAR_INSTANCE, ASSET_SET_MONTHLY_VAR_INSTANCE} from './riskAnalysisHelpers';

type VarCvarOutput = z.infer<typeof schemas.RiskAssetSetVarCvarOutput>;

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
/** Invented: the icons the panel would resolve for the two holdings, passed through to L1°. */
const ICONS: ReadonlyMap<number, string> = new Map([
    [HOLDING_A, '/icons/asset-types/etf.png'],
    [HOLDING_B, '/icons/asset-types/stock.png'],
]);
const PROPS = {assetIds: SELECTION, assetLabels: LABELS, assetIcons: ICONS, dateStart: DATE_START, dateEnd: DATE_END, targetCurrency: 'EUR', benchmarkId: null, refreshVersion: 0};

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
];

/**
 * How every base question is answered, and every question as it was asked.
 *
 *  - `figures`: the answer above;
 *  - `nothing`: an answer with no result in it — nothing failed, nothing measured;
 *  - `reject`: the request throws, as a failed wave does (`loadError`);
 *  - `discard`: `null`, what `queryRisk` returns for an answer that arrived and was discarded. The
 *    controller re-asks once, and a second `null` is what sets `loadDiscarded`.
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
        return {items: script.outcome === 'figures' ? FIGURES : []};
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

function mount() {
    const view = render(AssetSetComparisonLevels, {props: PROPS});
    expect(created.controllers, 'the levels did not create a controller of their own').toHaveLength(1);
    return {view, controller: created.controllers[0] as RiskPanelController};
}

async function settled(controller: RiskPanelController): Promise<void> {
    await waitFor(() => expect(controller.initialLoading, 'the base wave the mount fires never settled').toBe(false));
}

/** Mounted with the wave failing, and the premise: the controller recorded the failure. */
async function mountFailed(): Promise<RiskPanelController> {
    script.outcome = 'reject';
    const {controller} = mount();
    await waitFor(() => expect(controller.loadError, 'the controller never recorded the failure: the path under test did not run').toBe(true));
    expect(controller.loadDiscarded, 'a failure is not a discard').toBe(false);
    return controller;
}

/** Mounted with every answer discarded, and the premise: asked, re-asked once, and the discard recorded. */
async function mountDiscarded(): Promise<RiskPanelController> {
    script.outcome = 'discard';
    const {controller} = mount();
    await waitFor(() => expect(controller.loadDiscarded, 'the controller never recorded the discard: the path under test did not run').toBe(true));
    expect(script.asked, 'the base question was not asked and then re-asked exactly once').toHaveLength(2);
    expect(controller.loadError, 'a discard is not a failure').toBe(false);
    return controller;
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

/** None of the load-state chrome: no body block, no retry, and no frame saying an answer was discarded. */
function expectNoLoadChrome(why: string): void {
    for (const {level, frame} of LEVELS) {
        for (const part of ['error', 'discarded', 'retry']) {
            expect(screen.queryByTestId(`risk-asset-set-${level}-${part}`), `${why}: ${level} shows risk-asset-set-${level}-${part}`).toBeNull();
        }
        expect(frameCodes(frame), `${why}: the ${level} frame says an answer was discarded`).not.toContain(ANSWER_DISCARDED_CODE);
    }
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

        const {controller} = mount();
        await settled(controller);
        expect(script.asked, 'one base load must be one question: the capability gate lets only the asset-set wave through').toHaveLength(1);
        expect(
            script.asked[0].request.analytics.map((analytic) => analytic.analytic_code),
            'the question is not the per-asset wave these levels read',
        ).toEqual(expect.arrayContaining(['asset_set_var', 'asset_set_drawdown', 'asset_set_risk_return', 'asset_set_kpi']));

        // An answer with figures is a complement's barrier below: its fixtures must reach the cells.
        await expectFigures();
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
        const controller = await mountFailed();
        const {retry} = await blockWithRetry(level, 'error', `${level}: the base wave failed and the level offers no way to ask again`);

        await expectRetryAsksAgain(level, retry, () => expect(controller.loadError, 'the re-asked wave never settled').toBe(true));
    });
});

describe('AssetSetComparisonLevels — a base answer discarded twice running', () => {
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
        const controller = await mountDiscarded();
        const {retry} = await blockWithRetry(level, 'discarded', `${level}: the answer was discarded and the level offers no way to ask again`);
        const before = script.asked.length;

        // Discarded again, and re-asked again by the controller itself: two more questions.
        await expectRetryAsksAgain(level, retry, () => {
            expect(script.asked.length, 'the re-asked wave never settled').toBe(before + 2);
            expect(controller.loadDiscarded).toBe(true);
        });
    });

    it('after an answer with figures, keeps them: the frames say the new answer was lost, and L1 keeps its table', async () => {
        const {view, controller} = mount();
        await settled(controller);
        await expectFigures();

        // An accepted sync re-reads the base, and its answer is discarded twice running.
        const before = script.asked.length;
        script.outcome = 'discard';
        view.rerender({refreshVersion: 1});
        await waitFor(() => expect(controller.loadDiscarded, 'the refreshed answer was never recorded as discarded').toBe(true));
        expect(script.asked.length - before, 'the refresh was not asked and then re-asked exactly once').toBe(2);

        // The discard kept the answer on screen, and says it lost the new one.
        await expectFigures();
        for (const {level, frame} of LEVELS) {
            await waitFor(() => expect(frameCodes(frame), `${level}: an answer was discarded and the level's frame does not say so`).toEqual([ANSWER_DISCARDED_CODE]));
        }
        expect(screen.queryByTestId('risk-asset-set-l1-discarded'), 'L1 has figures: the discarded block is for a level with none, not a replacement for the table').toBeNull();
        expect(screen.queryByTestId('risk-asset-set-l1-error'), 'a discarded answer is shown as a failed wave').toBeNull();
    });
});

describe('AssetSetComparisonLevels — an answer: nothing failed, nothing discarded', () => {
    it('with figures, shows none of it', async () => {
        const {controller} = mount();
        await settled(controller);
        await expectFigures();

        expectNoLoadChrome('an answer with figures');
    });

    it('that measured nothing, shows none of it either: a blank is not a failure', async () => {
        script.outcome = 'nothing';
        const {controller} = mount();
        await settled(controller);
        expect(controller.loadError).toBe(false);
        expect(controller.loadDiscarded).toBe(false);

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
 * L1°'s column toggle — the project's `ColumnVisibilityToggle`, in the L1 frame's header just
 * before its manual icon (`RiskLevelSection`'s `actions`), bound to the loss table
 * (`AssetSetLossComparisonSection`'s bindable `tableRef`).
 *
 * It exists only while the table does: a toggle beside no table opens onto nothing, or onto the
 * columns of a table the reader cannot see. So it is absent while the first answer is in flight,
 * after a failed wave, and after an answer discarded with nothing to keep — and each of those
 * cases then brings the table and proves the toggle arrives with it, which is what keeps the
 * absence from passing about a page that has no toggle at all. Wherever the table is drawn it is
 * there: with figures, with an answer that measured nothing (a row of dashes per selected asset
 * is still a table), and when a later answer is discarded and the figures stay. L3° has none.
 *
 * Found by testid; the menu is read by its items' testids, never by their labels. Switching a
 * column off and on is the E2E's (`risk-lab.spec.ts`): here the table only has to be the one the
 * menu reads.
 */

/** L1°'s value columns, as `AssetSetLossComparisonSection` defines them. */
const L1_VALUE_COLUMNS = ['badDay', 'badMonth', 'worstFall', 'currentFall', 'toPeak'] as const;

const lossFrame = (): HTMLElement => screen.getByTestId('risk-asset-set-loss');
const paidFrame = (): HTMLElement => screen.getByTestId('risk-asset-set-paid');

/** A frame's column toggle, if it has one. */
function toggleIn(frame: HTMLElement): HTMLElement | null {
    return within(frame).queryByTestId('column-visibility-toggle');
}

/** Whether `first` comes before `second` in document order, `second` not inside it. */
function precedes(first: Node, second: Node): boolean {
    return !first.contains(second) && (first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
}

/** L1°'s toggle, waited for: the barrier of every case in which the table is drawn. */
async function expectToggle(why: string): Promise<HTMLElement> {
    return waitFor(() => {
        const toggle = toggleIn(lossFrame());
        expect(toggle, why).not.toBeNull();
        return toggle as HTMLElement;
    });
}

/**
 * No toggle in L1°'s frame — asserted with the frame's header drawn, its title and its manual
 * icon, and with no table, which is the state's own premise: the absence is about the toggle.
 */
function expectNoToggle(why: string): void {
    const frame = lossFrame();
    within(frame).getByTestId('risk-asset-set-loss-title');
    within(frame).getByTestId('risk-asset-set-loss-docs');
    expect(screen.queryByTestId('risk-asset-set-l1-table'), `${why} — premise: this state draws no table`).toBeNull();
    expect(toggleIn(frame), why).toBeNull();
}

/**
 * Hold every base question in flight until the test releases it with the figures. The harness's
 * own answers settle at once, which leaves the skeleton on screen for no moment a test could rely
 * on. One test's scope: `beforeEach` installs the ordinary answers again.
 */
function holdAnswers(): () => void {
    const held: ((answer: {items: RiskAnalyticResult[]}) => void)[] = [];
    queryRisk.mockImplementation((request: RiskQueryRequest, force?: boolean) => {
        script.asked.push({request, force: force === true});
        return new Promise((resolve) => held.push(resolve));
    });
    return () => {
        for (const resolve of held.splice(0)) resolve({items: FIGURES});
    };
}

/** Press a retry with figures to answer it: the table arrives. */
async function retryIntoFigures(retry: HTMLElement): Promise<void> {
    script.outcome = 'figures';
    await fireEvent.click(retry);
    await expectFigures();
}

describe("AssetSetComparisonLevels — L1°'s column toggle, in its frame beside the manual icon", () => {
    it("with figures: in L1°'s header, after the title and before the manual icon — and L3° has none", async () => {
        const {controller} = mount();
        await settled(controller);
        await expectFigures();
        const toggle = await expectToggle('L1° shows its figures and its frame offers no column toggle');

        const frame = lossFrame();
        expect(within(frame).getByTestId('risk-asset-set-loss-body').contains(toggle), "the toggle is in L1°'s body: it belongs to the frame's header").toBe(false);
        expect(precedes(within(frame).getByTestId('risk-asset-set-loss-title'), toggle), "the toggle does not come after L1°'s title, or sits inside it").toBe(true);
        expect(precedes(toggle, within(frame).getByTestId('risk-asset-set-loss-docs')), "the toggle does not come before L1°'s manual icon").toBe(true);

        // L3°'s frame is drawn, its manual icon included, and carries no toggle of its own.
        within(paidFrame()).getByTestId('risk-asset-set-paid-docs');
        expect(toggleIn(paidFrame()), "L3° got a column toggle: only L1°'s table has one").toBeNull();
        expect(screen.getAllByTestId('column-visibility-toggle'), 'the levels carry one column toggle, L1°').toHaveLength(1);
    });

    it("opening it lists L1°'s columns: the menu reads the loss table", async () => {
        const {controller} = mount();
        await settled(controller);
        await expectFigures();
        await fireEvent.click(await expectToggle('L1° shows its figures and its frame offers no column toggle'));

        const menu = await waitFor(() => screen.getByTestId('column-visibility-dropdown'));
        for (const column of L1_VALUE_COLUMNS) {
            expect(within(menu).queryByTestId(`column-visibility-item-${column}`), `the menu does not offer ${column}: the toggle is not reading L1°'s table`).not.toBeNull();
        }
    });

    it('is not there while the first answer is in flight, and arrives with the table', async () => {
        const release = holdAnswers();
        const {controller} = mount();
        await waitFor(() => expect(script.asked, 'the base question was never asked: nothing is in flight').toHaveLength(1));
        expect(controller.initialLoading, 'premise: the first answer is still loading').toBe(true);
        await waitFor(() => expect(screen.queryByTestId('risk-asset-set-l1-loading'), 'L1° is not drawing its skeleton').not.toBeNull());
        expectNoToggle('a column toggle beside a skeleton');

        release();
        await expectFigures();
        await expectToggle('the table arrived without its toggle');
    });

    it('is not there after a failed wave, and arrives with the table a retry brings', async () => {
        await mountFailed();
        const {retry} = await blockWithRetry('l1', 'error', 'L1° shows no error block: the state under test is not on screen');
        expectNoToggle('a column toggle beside a failed wave');

        await retryIntoFigures(retry);
        await expectToggle('the retry brought the table without its toggle');
    });

    it('is not there after an answer discarded with nothing to keep, and arrives with the table a retry brings', async () => {
        await mountDiscarded();
        const {retry} = await blockWithRetry('l1', 'discarded', 'L1° shows no discarded block: the state under test is not on screen');
        expectNoToggle('a column toggle beside a discarded answer');

        await retryIntoFigures(retry);
        await expectToggle('the retry brought the table without its toggle');
    });

    it('is there with an answer that measured nothing: a row of dashes per selected asset is still a table', async () => {
        script.outcome = 'nothing';
        const {controller} = mount();
        await settled(controller);
        await waitFor(() => expect(screen.getByTestId('risk-asset-set-l1-table')).toHaveAttribute('data-row-count', String(SELECTION.length)));

        await expectToggle('L1° draws its table and its frame offers no column toggle');
    });

    it('stays when a later answer is discarded: the figures stay, and so does their toggle', async () => {
        const {view, controller} = mount();
        await settled(controller);
        await expectFigures();
        await expectToggle('L1° shows its figures and its frame offers no column toggle');

        script.outcome = 'discard';
        view.rerender({refreshVersion: 1});
        await waitFor(() => expect(controller.loadDiscarded, 'the refreshed answer was never recorded as discarded').toBe(true));
        await expectFigures();
        expect(toggleIn(lossFrame()), 'the figures stayed and their toggle went: it follows the table, not the load state').not.toBeNull();
    });
});
