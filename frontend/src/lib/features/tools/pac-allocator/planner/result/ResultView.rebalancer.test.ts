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
