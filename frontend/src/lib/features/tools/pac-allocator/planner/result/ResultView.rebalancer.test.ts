// @vitest-environment jsdom
/**
 * A ready Rebalancer result renders (F4a of project 67, first slice): the guard of the whole lot.
 *
 * Found in the browser at step 10b: every ready Rebalancer plan crashed the result view (`planLookup` read the PAC's
 * `funding_routes`, which the Rebalancer's request does not carry, contract §5.4). The fixtures are engine answers, never
 * edited (generator: the notes folder's `67-F4a-gen_rebalancer_result_fixtures.py`):
 *   - `rebalancer-t5.json`: specification case T5, nothing to do (`ready_no_op`, no plan section);
 *   - `rebalancer-t4.json`: specification case T4, one purchase;
 *   - `rebalancer-t4-contribution.json`: T4 with a contribution, a deposit before the purchase;
 *   - `rebalancer-browser.json`: the G5 browser scenario, transfers, a conversion and purchases. The engine stopped at its
 *     time limit there (`time_limit`, not proven): a new run need not give the same plan, so no test reads a literal of it.
 *   - `rebalancer-y-top-up.json`: the consultant's case Y (lot ZB-b), a plan of the wide model with a 0.01 EUR top-up and
 *     no cash left.
 * Each request is parsed by the Rebalancer's own codec, as the run does, and each result by its output codec. Every section
 * is opened («Expand all»): the exposures, the ledger and the proof render too. Nothing reads translated text.
 *
 * `echarts` is a recorder, not a renderer, as in `ExposureBars.test.ts`: jsdom has no canvas, and the real zrender, given
 * none, rejects outside the test (`setting 'dpr'`, `reading 'clearRect'` of null) once the exposure charts draw. The
 * recorder answers every call the planner's charts make on an instance and keeps the options, so the test can see that
 * the opened exposures did draw.
 */
import {flushSync, tick} from 'svelte';
import {beforeAll, describe, expect, it, vi} from 'vitest';

const {charts, echartsModule} = vi.hoisted(() => {
    const charts: {options: unknown[]}[] = [];
    function fakeChart(dom: unknown) {
        let disposed = false;
        const record = {options: [] as unknown[]};
        charts.push(record);
        return {
            setOption: (option: unknown) => {
                record.options.push(option);
            },
            getOption: () => record.options.at(-1) ?? {},
            getDom: () => dom,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
    }
    return {charts, echartsModule: {init: (dom: unknown) => fakeChart(dom), registerMap: () => {}}};
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {fireEvent, render, screen, setupI18n} from '$test/component';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from '../draft.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {RunOutcome} from '../run.svelte';
import t5 from './__fixtures__/rebalancer-t5.json';
import t4 from './__fixtures__/rebalancer-t4.json';
import t4Deposit from './__fixtures__/rebalancer-t4-contribution.json';
import browser from './__fixtures__/rebalancer-browser.json';
import yTopUp from './__fixtures__/rebalancer-y-top-up.json';
import {formatExactPercent} from '../format';
import {categoryColor} from '$lib/theme/chartCategories';
import ResultView from './ResultView.svelte';

beforeAll(async () => {
    await setupI18n();
});

const contract = toolContractMap.portfolio_rebalancer['2.0.0'];

/** The figures of a run as the Tools API reports them; the result views show them, nothing is computed from them. */
const METRICS = {
    queue_wait_ms: 1,
    startup_ms: 240,
    input_validation_ms: 2,
    compute_ms: 51,
    output_validation_ms: 0,
    serialization_ms: 1,
    execution_ms: 850,
    cleanup_ms: 70,
    total_ms: 920,
    resources: {memory: {mode: 'process_tree_observed', limit_bytes: 1073741824, peak_observed_bytes: 90406912}},
    worker_exit_code: null,
};

function mounted(fixture: {request: unknown; result: unknown}): void {
    // Each case sees its own charts only.
    charts.length = 0;
    const draft = new PlannerDraft('EUR', 'invest_only', REBALANCER_PLANNER_PROFILE);
    const outcome = {
        kind: 'result',
        built: {
            request: fixture.request,
            resolved: contract.input.parse(fixture.request),
            ids: {routes: new Map(), funding: new Map(), capabilities: new Map(), provenance: new Map()},
            revision: 1,
            fingerprint: draft.fingerprint,
            counts: {assets: 0, operativeBrokers: 0, buyRoutes: 0, fxPairs: 0},
        },
        result: contract.output.parse(fixture.result),
        metrics: METRICS,
        batch: {server_processing_ms: 925},
        executionId: null,
    } as unknown as RunOutcome;
    const handlers = {ongoto: vi.fn(), onedit: vi.fn(), oncalculate: vi.fn(), onretry: vi.fn(), ondiscard: vi.fn()};
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: ResultView, childProps: {outcome, draft, apiVersion: '2.0.0', busy: false, ...handlers}}});
    flushSync();
}

describe('a ready Rebalancer result renders', () => {
    it.each([
        ['T5, nothing to do', t5, 'ready_no_op'],
        ['T4, one purchase', t4, 'ready_incumbent'],
        ['T4 with a contribution: a deposit, then the purchase', t4Deposit, 'ready_incumbent'],
        ['the browser scenario: transfers, a conversion, purchases', browser, 'ready_incumbent'],
        ['a wide plan that needs a top-up and leaves no cash (lot ZB-b, case Y)', yTopUp, 'ready_incumbent'],
    ])('%s', async (_name, fixture, state) => {
        expect(() => mounted(fixture)).not.toThrow();
        const root = screen.getByTestId('rebalancer-planner-result');
        expect(root.getAttribute('data-state')).toBe(state);
        // Every section open: none throws.
        const errors: unknown[] = [];
        // Closed sections draw nothing; the charts below come from opening them.
        expect(charts.filter((chart) => chart.options.length > 0)).toHaveLength(0);
        const onError = (event: ErrorEvent) => errors.push(event.error);
        window.addEventListener('error', onError);
        try {
            await fireEvent.click(screen.getByTestId('rebalancer-planner-result-toggle-all'));
            flushSync();
            await tick();
        } finally {
            window.removeEventListener('error', onError);
        }
        expect(errors).toEqual([]);
        // The opened exposures drew, in this case: at least one chart was given its option.
        expect(charts.some((chart) => chart.options.length > 0)).toBe(true);
        const sections = screen.getAllByTestId('rebalancer-planner-result-section');
        expect(sections.length).toBeGreaterThan(1);
        expect(sections.map((section) => section.querySelector('[data-testid="rebalancer-planner-result-section-toggle"]')?.getAttribute('aria-expanded'))).toEqual(sections.map(() => 'true'));
    });
});

/**
 * The plan section (F4a step 2, contract §6.3). The browser answer has two transfers, one exchange and five purchases: the
 * section counts all eight steps. A plan of transfers only is still a plan: that variant is derived here from the
 * browser answer by emptying its purchases and exchanges (the fixture file stays the engine's, untouched); the codec
 * still accepts it.
 */
describe('the Rebalancer allocation (F4a step 3)', () => {
    it('shows the Rebalancer table, with Assets, cash entries and the uninvested row’s two parts, not the PAC one', () => {
        mounted(browser);
        expect(screen.getByTestId('rebalancer-planner-allocation-table')).toBeTruthy();
        expect(screen.queryByTestId('rebalancer-planner-assets-table')).toBeNull();
        const ids = [...document.querySelectorAll('[data-testid="rebalancer-planner-allocation-table"] tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id'));
        expect(ids.slice(-2)).toEqual(['untargeted_cash', 'costs']);
        expect(ids.filter((id) => id?.startsWith('cash:'))).toHaveLength(browser.result.primary_solution.cash_rows.length);
    });
});

describe('the Rebalancer plan section', () => {
    const planSection = () => screen.getAllByTestId('rebalancer-planner-result-section').find((section) => section.getAttribute('data-section') === 'plan') ?? null;

    it('counts every step: transfers and exchanges as well as purchases', () => {
        mounted(browser);
        const solution = browser.result.primary_solution;
        const steps = solution.funding_actions.length + solution.conversions.length + solution.transfers.length + solution.order_rows.length;
        const toggle = planSection()?.querySelector('[data-testid="rebalancer-planner-result-section-toggle"]');
        expect(toggle?.textContent).toContain(`(${steps})`);
    });

    it('a plan of transfers only still has its section', () => {
        const transfersOnly = structuredClone(browser);
        transfersOnly.result.primary_solution.order_rows = [];
        transfersOnly.result.primary_solution.conversions = [];
        mounted(transfersOnly);
        expect(planSection()).not.toBeNull();
    });
});

/**
 * Lot SE of project 67: SCIP failed inside a stage after a plan was held. The result carries the warning
 * `allocation.solver_numerical_error` on the `proof` section, beside the «time limit» notice. The notes list it, as a
 * warning, with no «go to» link: nothing in the configuration causes it, and a link to Review would point at the user's
 * inputs. The variant is the browser answer with the note added (the fixture file untouched); the codec accepts it.
 */
describe('a solver numerical error is a note of its own', () => {
    it('lists the warning, without a link to a step', () => {
        const result = structuredClone(browser.result) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
        result.stop_reason = 'time_limit';
        result.issues = [{code: 'allocation.solver_numerical_error', severity: 'warning', kind: 'proof', path: {kind: 'section', section: 'proof'}, message_key: 'allocation.solver_numerical_error', params: []}];
        mounted({request: browser.request, result});
        const item = screen.getAllByTestId('rebalancer-planner-notes-list-item').find((node) => node.getAttribute('data-code') === 'allocation.solver_numerical_error');
        expect(item).toBeTruthy();
        expect(item!.getAttribute('data-severity')).toBe('warning');
        expect(item!.getAttribute('data-step')).toBe('');
        expect(item!.querySelector('[data-testid="rebalancer-planner-notes-list-goto"]')).toBeNull();
        expect(screen.getByTestId('rebalancer-planner-state').getAttribute('data-state')).toBe('limit');
    });
});

/**
 * Lot ZB-b of project 67, the consultant's case Y (`rebalancer-y-top-up.json`, the engine's answer): a plan of the wide
 * model spends the cash to the last cent and asks one more for its rounding. The result shows the top-up on its Broker
 * and Rebalancer's cash item at its posted value, below zero; nothing in the view throws on a negative share.
 */
describe('a plan with a rounding top-up', () => {
    it('shows the top-up on its Broker, and the cash item below zero', () => {
        mounted(yTopUp);
        const rows = screen.getAllByTestId('rebalancer-planner-top-up-row');
        expect(rows.map((row) => row.getAttribute('data-broker'))).toEqual(yTopUp.result.primary_solution.rounding_top_ups.map((row) => row.broker_id));
        const rowsShown = [...document.querySelectorAll('[data-testid="rebalancer-planner-allocation-table"] tbody tr[data-row-id]')];
        const cashRows = rowsShown.filter((row) => row.getAttribute('data-row-id')?.startsWith('cash:'));
        expect(cashRows).toHaveLength(yTopUp.result.primary_solution.cash_rows.length);
        // The cash item's final share is below zero (−0.01 € on F): the row shows the formatter's own output for it, no NaN.
        const [item] = yTopUp.result.primary_solution.cash_rows;
        const shown = cashRows[0].textContent ?? '';
        expect(shown).toContain(formatExactPercent(item.final_weight as Parameters<typeof formatExactPercent>[0]));
        expect(shown).not.toContain('NaN');
    });
});

/**
 * F4a of project 67, step 5: the balances carry the transfers between Brokers as their own columns. On the engine's G5
 * answer Broker 1 receives what Broker 2 sends: each column shows a cell per row, the published amounts.
 */
describe('the Rebalancer balances', () => {
    it('show the transfers in and out, one cell per Broker and currency', async () => {
        mounted(browser);
        const section = screen.getAllByTestId('rebalancer-planner-result-section').find((item) => item.getAttribute('data-section') === 'ledger');
        await fireEvent.click(section?.querySelector('[data-testid="rebalancer-planner-result-section-toggle"]') as HTMLElement);
        flushSync();
        const ledger = screen.getByTestId('rebalancer-planner-ledger');
        const rows = browser.result.primary_solution.ledger_rows;
        for (const field of ['transfer_in', 'transfer_out']) expect(ledger.querySelectorAll(`[data-testid="rebalancer-planner-ledger-${field}"]`)).toHaveLength(rows.length);
    });
});

/**
 * F4a of project 67, step 8: the Rebalancer's exposures are bullet charts in the three dimensions — types, sectors, then
 * the countries — with their legend once above them; the PAC's bars and maps are not drawn here. The accessible list
 * keeps one entry per published row, the cash included.
 */
describe('the Rebalancer exposures', () => {
    it('colour a sector by the name its id carries, whatever its label says', async () => {
        // A variant of the G5 answer whose sector labels are not the sector names (the fixture file untouched): the colour
        // must come from the id (`enc:Real_20Estate` is «Real Estate»), never from the label.
        const relabelled = structuredClone(browser);
        for (const row of relabelled.result.primary_solution.exposure_rows as {dimension: string; kind: string; label?: string}[]) if (row.dimension === 'sector' && row.kind === 'category') row.label = `Label of ${row.label}`;
        mounted(relabelled);
        const section = screen.getAllByTestId('rebalancer-planner-result-section').find((item) => item.getAttribute('data-section') === 'exposures');
        await fireEvent.click(section?.querySelector('[data-testid="rebalancer-planner-result-section-toggle"]') as HTMLElement);
        flushSync();
        await tick();
        const drawn = new Set(charts.flatMap((chart) => ((chart.options.at(-1) as {series?: {id?: string; data?: {itemStyle?: {color?: string}}[]}[]} | undefined)?.series ?? []).filter((series) => series.id === 'after').flatMap((series) => (series.data ?? []).map((item) => item.itemStyle?.color))));
        for (const name of ['Real Estate', 'Consumer Discretionary', 'Energy']) expect(drawn, name).toContain(categoryColor('sector', name, false));
    });

    it('are three bullet charts, the legend once, no bars; the countries also on the two maps, above their bullets (TL-5)', async () => {
        mounted(browser);
        const section = screen.getAllByTestId('rebalancer-planner-result-section').find((item) => item.getAttribute('data-section') === 'exposures');
        await fireEvent.click(section?.querySelector('[data-testid="rebalancer-planner-result-section-toggle"]') as HTMLElement);
        flushSync();
        await tick();
        const exposures = screen.getByTestId('rebalancer-planner-exposures');
        expect([...exposures.querySelectorAll('[data-testid="rebalancer-planner-exposures-bullets"]')].map((chart) => chart.getAttribute('data-dimension'))).toEqual(['asset_type', 'sector', 'geography']);
        expect(exposures.querySelectorAll('[data-testid="rebalancer-planner-exposures-legend"]')).toHaveLength(1);
        expect(exposures.querySelectorAll('[data-testid="rebalancer-planner-exposures-bars"]')).toHaveLength(0);
        // R1-C/D of project 67: the two maps, target and after the plan, in the geography block only; TL-5 (the developer,
        // 23/11: «prima la mappa e poi i grafici a barre»): before its bullets.
        const maps = [...exposures.querySelectorAll('[data-testid="rebalancer-planner-exposures-maps"]')];
        expect(maps).toHaveLength(1);
        const geography = exposures.querySelector('[data-testid="rebalancer-planner-exposures-dimension"][data-dimension="geography"]') as HTMLElement;
        expect(geography.contains(maps[0])).toBe(true);
        const bullets = geography.querySelector('[data-testid="rebalancer-planner-exposures-bullets"]') as HTMLElement;
        expect(maps[0].compareDocumentPosition(bullets) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
        // The cash is no place: it stays in the bullets, never in the maps nor in their list of what is not on them.
        const offMap = geography.querySelector('[data-testid="rebalancer-planner-exposures-off-map"]');
        expect(offMap?.textContent ?? '').not.toContain('Cash');
        expect(exposures.querySelectorAll('[data-testid="rebalancer-planner-exposures-row"]')).toHaveLength(browser.result.primary_solution.exposure_rows.length);
    });
});
