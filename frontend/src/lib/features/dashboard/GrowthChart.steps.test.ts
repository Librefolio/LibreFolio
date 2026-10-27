// @vitest-environment jsdom
/**
 * GrowthChart on a report whose series are steps (D-P4, Y5-3): one point per stretch without news, each holding from its
 * `date` to its `through`.
 *
 * The component builds the pipeline's inputs from the steps (`growthStepInputs.ts`), so the chart's resolution cascade, ladder
 * and zoom run as they always did, on a few dates instead of one per day. What these cases pin is what the user sees of that:
 *   - the daily resolution is the steps themselves, drawn with `step: 'end'`, and has a point per step, not per day;
 *   - a coarser resolution (dense steps) is the linear weekly or monthly line it always was;
 *   - the MWRR line joins its true points, and is not stepped;
 *   - the tooltip lists the step holding the day the pointer is on, not the drawn point nearest to it;
 *   - a history that starts in the year 1 is drawn from its steps, without a bucket per day.
 *
 * ECharts is replaced by a recorder (jsdom has no canvas): it keeps every `setOption` payload and the handlers `on` was given.
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import type {ComponentProps} from 'svelte';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        handlers: Map<string, Array<(event: unknown) => void>>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        on: (name: string, handler: (event: unknown) => void) => void;
        off: () => void;
        dispatchAction: () => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let merged: Record<string, unknown> = {};
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            handlers: new Map(),
            setOption(option) {
                chart.setOptionCalls.push({option});
                merged = {...merged, ...option};
            },
            getOption: () => {
                const zoom = merged.dataZoom;
                return {...merged, dataZoom: zoom == null ? [] : Array.isArray(zoom) ? zoom : [zoom]};
            },
            getWidth: () => 1200,
            getHeight: () => 360,
            getDom: () => dom,
            on: (name, handler) => {
                chart.handlers.set(name, [...(chart.handlers.get(name) ?? []), handler]);
            },
            off: () => {},
            dispatchAction: () => {},
            resize: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    return {
        chartInstances,
        echartsModule: {
            init: (dom: unknown) => createFakeChart(dom),
            format: {getTextRect: (text: string) => ({x: 0, y: 0, width: text.length * 7, height: 14})},
        },
    };
});

vi.mock('echarts', () => echartsModule);

import {cleanup, fireEvent, render, setupI18n, waitFor} from '$test/component';
import type {PortfolioHistoryPoint, PortfolioMwrrLinePoint} from '$lib/stores/portfolio/portfolioStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {addDays} from '$lib/utils/dateOnly';
import GrowthChart from './GrowthChart.svelte';

const eur = (amount: number) => ({code: 'EUR', amount: amount.toFixed(2)});

/** One history step: the amounts follow `k`, so a different `k` is a different step. */
function step(date: string, through: string, k: number): PortfolioHistoryPoint {
    return {
        date,
        through,
        cash_value: eur(k),
        market_value: eur(k * 7),
        nav_value: eur(1_000 + k * 10),
        capital_baseline: eur(1_000),
        book_asset_like: eur(k * 5),
        cash_from_contributed_capital: eur(k * 2),
        cash_from_generated_returns: eur(k),
        total_pnl: eur(k * 5 - 20),
        twrr: (k / 100).toFixed(6),
        roi: (k / 200).toFixed(6),
    };
}

/** Three steps over 60 days: 1 January to 10 January, 11 January to 19 February, 20 February to 1 March. */
const SPARSE: PortfolioHistoryPoint[] = [step('2026-01-01', '2026-01-10', 1), step('2026-01-11', '2026-02-19', 3), step('2026-02-20', '2026-03-01', 6)];
const SPARSE_RANGE = {start: '2026-01-01', end: '2026-03-01'};
const SPARSE_MWRR: PortfolioMwrrLinePoint[] = [
    {date: '2026-01-01', annualized: null, cumulative: null},
    {date: '2026-01-31', annualized: '0.05', cumulative: '0.004000'},
    {date: '2026-03-01', annualized: '0.06', cumulative: '0.009000'},
];

interface Series {
    name: string;
    type?: string;
    step?: unknown;
    connectNulls?: boolean;
    data: Array<{value: [string, number | null]} | unknown>;
}

function lastOption(pick: (option: Record<string, unknown>) => boolean): Record<string, unknown> | null {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    return [...calls].reverse().find((call) => pick(call.option))?.option ?? null;
}

const renderedSeries = (): Series[] => (lastOption((option) => Array.isArray(option.series))?.series ?? []) as Series[];
const dates = (series: Series): string[] => series.data.map((datum) => (datum as {value: [string, number | null]}).value[0]);
const values = (series: Series): Array<number | null> => series.data.map((datum) => (datum as {value: [string, number | null]}).value[1]);

type Formatter = (params: unknown) => string;
function tooltipFormatter(): Formatter {
    const formatter = (lastOption((option) => typeof (option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function')?.tooltip as {formatter: Formatter} | undefined)?.formatter;
    if (!formatter) throw new Error('GrowthChart never handed a tooltip formatter to ECharts');
    return formatter;
}

/** What the tooltip writes for a money amount, as it writes it. */
const money = (amount: number) => amount.toLocaleString(uiLocale(), {minimumFractionDigits: 2, maximumFractionDigits: 2});

async function mount(props: ComponentProps<typeof GrowthChart>) {
    const view = render(GrowthChart, {props});
    await waitFor(() => expect(chartInstances.length).toBeGreaterThan(0), {timeout: 5_000});
    await waitFor(() => expect(renderedSeries().length).toBeGreaterThan(0), {timeout: 5_000});
    return view;
}

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    chartInstances.length = 0;
});
afterEach(() => {
    cleanup();
});

describe('the daily resolution is the steps', () => {
    it('draws a point per step and the ends of the range, not a point per day, and holds each value to the next date', async () => {
        await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        const nav = renderedSeries().find((series) => series.type === 'line' && values(series).includes(1_010));
        expect(nav, 'the NAV line is drawn').toBeDefined();
        // the three steps, the day the MWRR line has a point inside the second step (31 January), and the last day of the range
        expect(dates(nav!)).toEqual(['2026-01-01', '2026-01-11', '2026-01-31', '2026-02-20', '2026-03-01']);
        expect(values(nav!)).toEqual([1_010, 1_030, 1_030, 1_060, 1_060]);
        expect(
            renderedSeries()
                .filter((series) => series.type === 'line')
                .every((series) => series.step === 'end'),
        ).toBe(true);
    });

    it('draws the stacked areas of the Abs view on the same dates, so they stack', async () => {
        await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        const lines = renderedSeries().filter((series) => series.type === 'line');
        const first = dates(lines[0]);
        expect(lines.every((series) => dates(series).join() === first.join())).toBe(true);
    });
});

describe('a history that starts in the year 1', () => {
    const TYPO = [step('0001-01-01', '0001-01-01', 0), step('0001-01-02', '2025-12-31', 1), ...SPARSE];

    it('is drawn from its steps: a handful of points, in a moment', async () => {
        const started = performance.now();
        await mount({history: TYPO, range: {start: '0001-01-01', end: '2026-03-01'}, mwrrLine: []});
        const nav = renderedSeries().find((series) => series.type === 'line' && values(series).includes(1_010));
        expect(nav).toBeDefined();
        expect(nav!.data.length).toBeLessThan(20);
        expect(dates(nav!)[0]).toBe('0001-01-01');
        expect(performance.now() - started).toBeLessThan(5_000);
    });
});

describe('dense steps (more points than the plot takes) are the weekly line they always were', () => {
    /** One-day steps: a width of 1200 takes 1 560 points at 1.3 a pixel, so 1 800 of them are too many and the chart goes weekly. */
    const DAYS = 1_800;
    const FIRST = '2021-01-01';
    const dense: PortfolioHistoryPoint[] = Array.from({length: DAYS}, (_, index) => {
        const day = addDays(FIRST, index);
        return step(day, day, index);
    });
    const range = {start: FIRST, end: addDays(FIRST, DAYS - 1)};

    it('is drawn weekly, linear (no step), with a point a week', async () => {
        await mount({history: dense, range, mwrrLine: []});
        // the first draw is the steps (1 800 of them are more than the plot takes); the cascade then settles on the weekly line
        await waitFor(() => expect(renderedSeries().find((series) => series.type === 'line')?.data.length).toBeLessThan(400), {timeout: 5_000});
        const lines = renderedSeries().filter((series) => series.type === 'line');
        expect(lines.some((series) => series.step === 'end')).toBe(false);
        expect(lines[0].data.length).toBeLessThan(300);
        expect(lines[0].data.length).toBeGreaterThan(200);
    });
});

describe('the % view', () => {
    it('joins the MWRR through its true points and steps TWRR and ROI', async () => {
        const {getByTestId} = await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        await fireEvent.click(getByTestId('growth-toggle-pct'));
        await waitFor(() => expect(renderedSeries()).toHaveLength(3), {timeout: 5_000});
        const [mwrr, twrr, roi] = renderedSeries();
        expect(mwrr.connectNulls).toBe(true);
        expect(mwrr.step).toBe(false);
        expect(twrr.step).toBe('end');
        expect(roi.step).toBe('end');
        // the MWRR has a value only on the three days of its line; the days between are not drawn as zero
        const known = mwrr.data.filter((datum) => (datum as {value: [string, number | null]}).value[1] !== null);
        expect(known.map((datum) => (datum as {value: [string, number | null]}).value[0])).toEqual(['2026-01-31', '2026-03-01']);
    });
});

describe('the tooltip of a step line', () => {
    /** The event ECharts sends when the pointer moves: `axesInfo[0].value` is the pointed day as local-midnight milliseconds. */
    function pointAt(day: string): void {
        const [year, month, date] = day.split('-').map(Number);
        const handlers = chartInstances.at(-1)?.handlers.get('updateAxisPointer') ?? [];
        expect(handlers.length, 'the chart listens to the axis pointer').toBeGreaterThan(0);
        for (const handler of handlers) handler({axesInfo: [{value: new Date(year, month - 1, date).getTime()}]});
    }

    it('lists the step holding the pointed day, not the drawn point nearest to it', async () => {
        await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        // 18 February is one day from the step starting on the 20th and 38 from the one starting on the 11th: ECharts says the 20th.
        pointAt('2026-02-18');
        const html = tooltipFormatter()([{dataIndex: 3}]);
        expect(html).toContain(money(1_030));
        expect(html).not.toContain(money(1_060));
    });

    it('lists the nearest drawn point when nothing was pointed (a touch, the keyboard)', async () => {
        await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        const html = tooltipFormatter()([{dataIndex: 3}]);
        expect(html).toContain(money(1_060));
    });

    it('reads the axis pointer with `snap: false`, so the pointed day is exact', async () => {
        await mount({history: SPARSE, range: SPARSE_RANGE, mwrrLine: SPARSE_MWRR});
        const option = lastOption((candidate) => candidate.tooltip !== undefined) as {tooltip: {axisPointer: {snap: boolean}}; xAxis: {axisPointer: {snap: boolean}}};
        expect(option.tooltip.axisPointer.snap).toBe(false);
        expect(option.xAxis.axisPointer.snap).toBe(false);
    });
});
