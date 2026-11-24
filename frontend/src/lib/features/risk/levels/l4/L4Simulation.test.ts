// @vitest-environment jsdom
/**
 * L4Simulation — component test (Vitest + jsdom), RN-16 (developer's Q4 c, Q5 a and Q6, 16/11/2026).
 *
 * The simulation is estimated on its own history — all the common history, never the page's period — and the block
 * says so, read off the answer: how long that history is, from when to when, how many observations, and whether a
 * longer history was left out; when the request did not fit, how many paths ran instead of the ones asked; and the cone
 * starts where that history ends. Run asks the controller for a simulation with the controls on screen.
 *
 * Sentences are resolved from the shipped catalogue through the same `$_` the component uses, never written here; the
 * chart is a stand-in that publishes the data it was handed (jsdom has no canvas).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';

const fetchRiskCatalog = vi.hoisted(() => vi.fn());
const fetchRiskScenarioCatalog = vi.hoisted(() => vi.fn());
const queryRisk = vi.hoisted(() => vi.fn());
const invalidateRisk = vi.hoisted(() => vi.fn());

vi.mock('$lib/features/risk/riskStore.svelte', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/features/risk/riskStore.svelte')>();
    return {...actual, fetchRiskCatalog, fetchRiskScenarioCatalog, queryRisk, invalidateRisk, hasRiskCapability: () => true};
});
vi.mock('$lib/components/charts/LineChart.svelte', async () => ({default: (await import('$test/LineChartStub.svelte')).default}));

import {fireEvent, render, screen, setupI18n, within} from '$test/component';
import {effectRoot} from '$test/runes.svelte';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {createRiskPanelController, type RiskControllerInputs, type RiskPanelController} from '$lib/features/risk/riskPanelController.svelte';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import type {RiskQueryRequest} from '$lib/features/risk/riskRequest';
import {addDays} from '../../riskAnalysisHelpers';
import {calendarLengthText} from '../../assetSetLevels';
import {dayFormatter} from '../../eligibility';
import L4Simulation from './L4Simulation.svelte';

const PAGE_END = '2026-01-21';
const HISTORY = {start: '2022-09-01', end: '2026-11-13', count: 1050};

const normalize = (text: string | null | undefined): string => (text ?? '').replace(/\s+/g, ' ').trim();
const resolve = (key: string, values: Record<string, string | number> = {}): string => normalize(get(_)(key, {values}));

function simulationResult(output: Record<string, unknown> = {}): RiskAnalyticResult {
    const bands = [0, 1, 2].map((day) => ({day, p05: -0.01 * day, p50: 0.001 * day, p95: 0.01 * day}));
    return {
        instance_id: 'single-simulation',
        analytic_code: 'simulation',
        status: 'ok',
        output: {
            kind: 'simulation',
            process: 'block_bootstrap',
            regime: 'none',
            sampling_method: 'mc',
            horizon_days: 2,
            path_count: 8192,
            block_length_days: 9,
            drift_estimator: 'empirical_resampled',
            covariance_estimator: 'not_estimated_joint_resampling',
            aggregation_policy: 'current_buy_and_hold',
            percentile_bands: bands,
            terminal_mean_return: 0.01,
            terminal_volatility: 0.2,
            probability_of_loss: 0.4,
            requested_path_count: 8192,
            estimation_start: HISTORY.start,
            estimation_end: HISTORY.end,
            estimation_observations: HISTORY.count,
            history_truncated: false,
            ...output,
        },
    } as unknown as RiskAnalyticResult;
}

function controllerInputs(): RiskControllerInputs {
    return {scope: {kind: 'portfolio'}, dateStart: '2026-01-02', dateEnd: PAGE_END, targetCurrency: 'EUR', appliedRiskFreePercent: 0, refreshVersion: 0};
}

const stops: (() => void)[] = [];

function mount(result: RiskAnalyticResult | null = null): RiskPanelController {
    const {value: controller, stop} = effectRoot(() => createRiskPanelController(() => controllerInputs()));
    stops.push(stop);
    flushSync();
    if (result) controller.setResult('simulation', result);
    render(L4Simulation, {props: {controller, dateEnd: PAGE_END}});
    return controller;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    fetchRiskCatalog.mockReset().mockResolvedValue({items: []});
    fetchRiskScenarioCatalog.mockReset().mockResolvedValue({items: []});
    invalidateRisk.mockReset();
    queryRisk.mockReset().mockResolvedValue({items: []});
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
});

describe('L4Simulation — the history it was estimated on (Q4 c)', () => {
    it('says how long the history is, from when to when, and on how many observations', () => {
        mount(simulationResult());

        const formatDay = dayFormatter(uiLocale());
        const length = calendarLengthText(HISTORY.start, HISTORY.end, get(_), get(currentLanguage), HISTORY.count);
        const line = screen.getByTestId('risk-simulation-estimation');
        expect(normalize(line.textContent)).toBe(resolve('risk.simulation.estimation', {length, start: formatDay(HISTORY.start), end: formatDay(HISTORY.end), count: HISTORY.count}));
        expect(line.getAttribute('data-truncated')).toBe('false');
        expect(normalize(line.textContent)).not.toContain(resolve('risk.simulation.estimationTruncated', {count: HISTORY.count}));
    });

    it('adds that a longer common history was left out when only its most recent observations fit', () => {
        mount(simulationResult({history_truncated: true}));

        const line = screen.getByTestId('risk-simulation-estimation');
        expect(line.getAttribute('data-truncated')).toBe('true');
        expect(normalize(line.textContent)).toContain(resolve('risk.simulation.estimationTruncated', {count: HISTORY.count}));
    });

    it('starts the cone where that history ends, not at the end of the page’s period', () => {
        mount(simulationResult());

        expect(screen.getByTestId('stub-line-chart').getAttribute('data-first-date')).toBe(addDays(HISTORY.end, 0));
        expect(screen.getByTestId('stub-line-chart').getAttribute('data-first-date')).not.toBe(PAGE_END);
    });

    it('says nothing of a history for an answer that does not state one, and anchors on the page’s end', () => {
        mount(simulationResult({estimation_start: null, estimation_end: null, estimation_observations: null, requested_path_count: null}));

        // Barrier: the answer parsed, the cone is drawn.
        expect(screen.getByTestId('risk-simulation-terminal')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-simulation-estimation')).toBeNull();
        expect(screen.getByTestId('stub-line-chart').getAttribute('data-first-date')).toBe(PAGE_END);
    });
});

describe('L4Simulation — the paths that ran (Q5 a)', () => {
    it('says how many paths ran instead of the ones asked, when the request did not fit', () => {
        mount(simulationResult({path_count: 4096, requested_path_count: 8192}));

        const line = screen.getByTestId('risk-simulation-paths-reduced');
        expect([line.getAttribute('data-used'), line.getAttribute('data-requested')]).toEqual(['4096', '8192']);
        expect(normalize(line.textContent)).toBe(resolve('risk.simulation.pathsReduced', {used: 4096, requested: 8192}));
    });

    it('says nothing when every path asked ran', () => {
        mount(simulationResult());

        expect(screen.getByTestId('risk-simulation-terminal')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-simulation-paths-reduced')).toBeNull();
    });
});

describe('L4Simulation — Run asks for the simulation on screen', () => {
    it('asks the controller for a current-composition simulation with the horizon and the paths of the controls', async () => {
        mount();

        await fireEvent.click(screen.getByTestId('risk-simulation-run'));

        await vi.waitFor(() => expect(queryRisk.mock.calls.some(([request]) => (request as RiskQueryRequest).analytics.some((item) => item.analytic_code === 'simulation'))).toBe(true));
        const request = queryRisk.mock.calls.map(([asked]) => asked as RiskQueryRequest).find((asked) => asked.analytics.some((item) => item.analytic_code === 'simulation'));
        const analytic = request?.analytics.find((item) => item.analytic_code === 'simulation');
        expect(request?.mode).toBe('current_composition');
        expect(analytic?.parameters).toMatchObject({horizon_days: 365, path_count: 8192});
    });
});

describe('L4Simulation — the period the days are drawn from (RSK-SIM1, P-7)', () => {
    const AVAILABLE = {start: '2016-05-03', end: '2026-11-13'};

    function simulationRequestParameters(): Record<string, unknown> | undefined {
        const request = queryRisk.mock.calls.map(([asked]) => asked as RiskQueryRequest).find((asked) => asked.analytics.some((item) => item.analytic_code === 'simulation'));
        return request?.analytics.find((item) => item.analytic_code === 'simulation')?.parameters as Record<string, unknown> | undefined;
    }

    async function runAndRead(): Promise<Record<string, unknown> | undefined> {
        await fireEvent.click(screen.getByTestId('risk-simulation-run'));
        await vi.waitFor(() => expect(simulationRequestParameters()).toBeDefined());
        return simulationRequestParameters();
    }

    it('draws from all the common history by default, and sends no period', async () => {
        mount();

        expect(screen.getByTestId('risk-simulation-history').getAttribute('data-chosen')).toBe('false');
        expect((screen.getByTestId('risk-simulation-history-all') as HTMLInputElement).checked).toBe(true);
        expect(screen.queryByTestId('risk-simulation-history-period')).toBeNull();
        const parameters = await runAndRead();
        expect(parameters).not.toHaveProperty('history_start');
        expect(parameters).not.toHaveProperty('history_end');
    });

    it('opens a chosen period on the window the last answer stated, and sends it', async () => {
        mount(simulationResult({history_available_start: AVAILABLE.start, history_available_end: AVAILABLE.end}));

        await fireEvent.click(screen.getByTestId('risk-simulation-history-chosen'));
        const period = screen.getByTestId('risk-simulation-history-period');
        expect([period.getAttribute('data-start'), period.getAttribute('data-end')]).toEqual([AVAILABLE.start, AVAILABLE.end]);
        const available = screen.getByTestId('risk-simulation-history-available');
        expect([available.getAttribute('data-start'), available.getAttribute('data-end')]).toEqual([AVAILABLE.start, AVAILABLE.end]);
        expect(normalize(available.textContent)).toBe(resolve('risk.simulation.history.available', {start: dayFormatter(uiLocale())(AVAILABLE.start), end: dayFormatter(uiLocale())(AVAILABLE.end)}));

        const parameters = await runAndRead();
        expect(parameters).toMatchObject({history_start: AVAILABLE.start, history_end: AVAILABLE.end});
    });

    it('before any answer opens on the last year, and going back to all the history sends no period again', async () => {
        mount();

        await fireEvent.click(screen.getByTestId('risk-simulation-history-chosen'));
        const period = screen.getByTestId('risk-simulation-history-period');
        const end = period.getAttribute('data-end') ?? '';
        expect(period.getAttribute('data-start')).toBe(addDays(end, -365));
        expect(screen.queryByTestId('risk-simulation-history-available')).toBeNull();

        await fireEvent.click(screen.getByTestId('risk-simulation-history-all'));
        expect(screen.queryByTestId('risk-simulation-history-period')).toBeNull();
        const parameters = await runAndRead();
        expect(parameters).not.toHaveProperty('history_start');
    });

    it('starts the cone where the data ends, not where a chosen period ends', () => {
        mount(simulationResult({estimation_start: '2020-02-03', estimation_end: '2021-03-31', history_available_start: AVAILABLE.start, history_available_end: AVAILABLE.end, history_chosen: true}));

        expect(screen.getByTestId('stub-line-chart').getAttribute('data-first-date')).toBe(AVAILABLE.end);
    });

    it('keeps a typed start inside the common history, in the state and in the field', async () => {
        mount(simulationResult({history_available_start: AVAILABLE.start, history_available_end: AVAILABLE.end}));
        await fireEvent.click(screen.getByTestId('risk-simulation-history-chosen'));
        const period = screen.getByTestId('risk-simulation-history-period');
        const start = within(period).getByTestId('date-range-input-start') as HTMLInputElement;

        // A start inside the window is kept as typed.
        await fireEvent.focus(start);
        await fireEvent.input(start, {target: {value: '2020-02-03'}});
        await fireEvent.blur(start);
        expect(screen.getByTestId('risk-simulation-history-period').getAttribute('data-start')).toBe('2020-02-03');

        // A start before the common history comes back to it, twice in a row too (the second clamp returns the same day).
        for (const typed of ['2010-01-04', '2009-06-01']) {
            await fireEvent.focus(start);
            await fireEvent.input(start, {target: {value: typed}});
            await fireEvent.blur(start);
            expect(screen.getByTestId('risk-simulation-history-period').getAttribute('data-start')).toBe(AVAILABLE.start);
            await fireEvent.focus(start);
            expect(start.value, `the field shows the clamped day after typing ${typed}`).toBe(AVAILABLE.start);
            await fireEvent.blur(start);
        }
    });

    it('says the history line is a chosen period when the answer says so', () => {
        mount(simulationResult({history_available_start: AVAILABLE.start, history_available_end: AVAILABLE.end, history_chosen: true}));

        const line = screen.getByTestId('risk-simulation-estimation');
        expect(line.getAttribute('data-history-chosen')).toBe('true');
        expect(normalize(line.textContent)).toContain(resolve('risk.simulation.history.chosenNote'));
    });
});

// 81 U30 (testlist of 23/11: «campi di input tutti della stessa larghezza»): on a phone the parameters keep T-4's rows —
// label on the left, field on the right — and every field is of one width; from `sm` up each keeps the width it had.
// `w-full` cannot do it beside a label (the field would take what the label leaves, a width per row), so the one width is
// a shared fixed one. Classes are the contract here (jsdom draws no media query); the measure at 375 px is the E2E's («T-4»).
describe('L4Simulation — the parameter fields on a phone are of one width (81 U30)', () => {
    /** The width class a field has below `sm` (the unprefixed `w-*` tokens) and from `sm` up (`sm:w-*`). */
    function widths(el: Element): {phone: string[]; fromSm: string[]} {
        const list = (el.getAttribute('class') ?? '').split(/\s+/);
        return {phone: list.filter((token) => /^w-/.test(token)), fromSm: list.filter((token) => /^sm:w-/.test(token))};
    }

    it('gives horizon, paths and seed the same width below `sm`', () => {
        mount();
        const phone = ['risk-simulation-horizon', 'risk-simulation-paths', 'risk-simulation-seed'].map((id) => ({id, ...widths(screen.getByTestId(id))}));
        for (const field of phone) expect(field.phone, `${field.id}: one fixed width below sm`).toHaveLength(1);
        expect(new Set(phone.map((field) => field.phone[0])).size, `the fields differ below sm: ${phone.map((field) => `${field.id} ${field.phone[0]}`).join(', ')}`).toBe(1);
    });

    it('gives the sampling select the same width as the inputs below `sm`', async () => {
        mount();
        // The select exists only for the parametric process (`gbm`), the «advanced» mode.
        const advanced = document.querySelector('[data-testid="risk-simulation-mode"][data-mode-id="gbm"] input');
        await fireEvent.click(advanced as Element);
        const input = widths(screen.getByTestId('risk-simulation-paths')).phone[0];
        const sampling = screen.getByTestId('risk-simulation-sampling');
        const own = [sampling, ...sampling.querySelectorAll('*')].map((el) => widths(el).phone).find((list) => list.length > 0);
        expect(own, 'the sampling select carries no width of its own below sm').toEqual([input]);
    });

    it('keeps the width paths had from `sm` up', () => {
        mount();
        expect(widths(screen.getByTestId('risk-simulation-paths')).fromSm).toEqual(['sm:w-24']);
    });
});
