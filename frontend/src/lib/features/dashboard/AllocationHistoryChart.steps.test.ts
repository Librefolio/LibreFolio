// @vitest-environment jsdom
/**
 * AllocationHistoryChart on a history of steps (D-P4, Y5-3): one point per stretch without news, each holding from its `date`
 * to its `through`.
 *
 * The chart builds its rows from the steps (`allocationHistorySteps.ts`): the rows of the witness days, so its resolution
 * cascade, its aggregation and its zoom run as they always did on a few rows instead of one per day. What these cases pin:
 *   - the daily resolution is the steps themselves: a row per step and the last day of the range, each stacked series drawn with
 *     `step: 'end'` on the same dates, so the areas stack;
 *   - dense steps (more rows than the plot takes) are the weekly line they always were, not stepped;
 *   - a history that starts in the year 1 is drawn from its steps, without a row per day;
 *   - the tooltip lists the step holding the day the pointer is on, not the drawn row nearest to it.
 *
 * Same harness as `AllocationHistoryChart.negativeCash.test.ts`: `echarts` is a recorder that keeps every `setOption` payload and
 * the handlers `on` was given, `$lib/api` answers empty lists, and the chart's container is given a client rect.
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        handlers: Map<string, Array<(event: unknown) => void>>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getDom: () => unknown;
        getWidth: () => number;
        getHeight: () => number;
        on: (event: string, handler: (event: unknown) => void) => void;
        off: (event: string) => void;
        dispatchAction: (action: unknown) => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }
    const chartInstances: FakeChart[] = [];
    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            handlers: new Map(),
            setOption(option) {
                chart.setOptionCalls.push({option});
            },
            getOption: () => ({}),
            getDom: () => dom,
            getWidth: () => 800,
            getHeight: () => 400,
            on: (event, handler) => {
                chart.handlers.set(event, [...(chart.handlers.get(event) ?? []), handler]);
            },
            off: (event) => {
                chart.handlers.delete(event);
            },
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
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {render, setupI18n, waitFor} from '$test/component';
import {formatPercent} from '$lib/utils/core/formatPercent';
import {addDays} from '$lib/utils/dateOnly';

const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');
const CHART_CONTAINER_TESTID = 'allocation-history-chart';

type ChartComponent = typeof import('./AllocationHistoryChart.svelte').default;
let AllocationHistoryChart: ChartComponent;
let restoreLayout: (() => void) | undefined;

function layOutChartContainer(): () => void {
    const jsdomGetClientRects = Element.prototype.getClientRects;
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(function (this: Element): DOMRectList {
        if (this.getAttribute('data-testid') !== CHART_CONTAINER_TESTID) return jsdomGetClientRects.call(this);
        return [{x: 0, y: 0, top: 0, left: 0, width: 800, height: 400, right: 800, bottom: 400}] as unknown as DOMRectList;
    });
    return () => spy.mockRestore();
}

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    AllocationHistoryChart = (await import('./AllocationHistoryChart.svelte')).default;
    restoreLayout = layOutChartContainer();
});
afterAll(() => restoreLayout?.());
beforeEach(() => {
    chartInstances.length = 0;
});

const component = (name: string, value: number) => ({name, value: String(value), amount: String(value * 100)});
const step = (date: string, through: string, weights: Array<[string, number]>) => ({date, through, components: weights.map(([name, value]) => component(name, value))});

/** Alpha 60 / Beta 40 to 10 January, Alpha 50 / Beta 30 / Gamma 20 to 19 February, Alpha 70 / Gamma 30 to 1 March. */
const STEPS = [
    step('2026-01-01', '2026-01-10', [
        ['Alpha', 60],
        ['Beta', 40],
    ]),
    step('2026-01-11', '2026-02-19', [
        ['Alpha', 50],
        ['Beta', 30],
        ['Gamma', 20],
    ]),
    step('2026-02-20', '2026-03-01', [
        ['Alpha', 70],
        ['Gamma', 30],
    ]),
];

interface DrawnSeries {
    id: string;
    step?: unknown;
    stack?: string;
    data: Array<{name: string; value: [string, number]}>;
}
interface DrawnOption {
    series: DrawnSeries[];
    tooltip: {formatter: (params: unknown) => string; axisPointer: {snap: boolean}};
    xAxis: {axisPointer: {snap: boolean}};
}

function lastFullOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series) && option.series.length > 0 && option.tooltip != null);
    return call?.option as unknown as DrawnOption | undefined;
}

async function mountChart(data: Array<ReturnType<typeof step>>, dimension: 'type' | 'sector' | 'geo' | 'asset' = 'sector'): Promise<DrawnOption> {
    render(AllocationHistoryChart, {props: {data, dimension, height: '400px'}});
    await waitFor(() => expect(lastFullOption()).toBeDefined(), {timeout: 5_000});
    return lastFullOption()!;
}

describe('the daily resolution is the steps', () => {
    it('draws a row per step and the last day of the range, every area stepped, all on the same dates', async () => {
        const option = await mountChart(STEPS);
        expect(option.series.map((series) => series.step)).toEqual(option.series.map(() => 'end'));
        const dates = option.series.map((series) => series.data.map((datum) => datum.value[0]));
        for (const list of dates) expect(list).toEqual(['2026-01-01', '2026-01-11', '2026-02-20', '2026-03-01']);
    });

    it('gives each date the shares of its step, and 0 where the step does not have the category', async () => {
        const option = await mountChart(STEPS);
        const valuesOf = (id: string) => option.series.find((series) => series.id === id)!.data.map((datum) => datum.value[1]);
        expect(valuesOf('Alpha')).toEqual([60, 50, 70, 70]);
        expect(valuesOf('Beta')).toEqual([40, 30, 0, 0]);
        expect(valuesOf('Gamma')).toEqual([0, 20, 30, 30]);
    });
});

describe('dense steps are the weekly line they always were', () => {
    it('draws a row a week, joined (no step), when the steps are more than the plot takes', async () => {
        // 1 200 one-day steps at a width of 800: more than 1.3 points a pixel (1 040), so the chart goes weekly.
        const dense = Array.from({length: 1_200}, (_, index) => {
            const day = addDays('2022-01-01', index);
            return step(day, day, [
                ['Alpha', 50 + (index % 7)],
                ['Beta', 50 - (index % 7)],
            ]);
        });
        render(AllocationHistoryChart, {props: {data: dense, dimension: 'sector', height: '400px'}});
        await waitFor(
            () => {
                const option = lastFullOption();
                expect(option?.series[0]?.data.length).toBeLessThan(300);
            },
            {timeout: 5_000},
        );
        const option = lastFullOption()!;
        expect(option.series.every((series) => series.step === undefined)).toBe(true);
        expect(option.series[0].data.length).toBeGreaterThan(150);
    });
});

describe('a history that starts in the year 1', () => {
    it('is drawn from its steps: a handful of rows', async () => {
        const typo = [step('0001-01-01', '2025-12-31', [['Alpha', 100]]), ...STEPS];
        const started = performance.now();
        const option = await mountChart(typo);
        expect(option.series[0].data.length).toBeLessThan(12);
        expect(option.series[0].data[0].value[0]).toBe('0001-01-01');
        expect(performance.now() - started).toBeLessThan(5_000);
    });
});

describe('the tooltip of a step area', () => {
    function pointAt(day: string): void {
        const [year, month, date] = day.split('-').map(Number);
        const handlers = chartInstances[0].handlers.get('updateAxisPointer') ?? [];
        expect(handlers.length, 'the chart listens to the axis pointer').toBeGreaterThan(0);
        for (const handler of handlers) handler({axesInfo: [{value: new Date(year, month - 1, date).getTime()}]});
    }
    const share = (value: number) => formatPercent(value, {digits: 1, signed: false});

    it('lists the step holding the pointed day, not the row nearest to it', async () => {
        const option = await mountChart(STEPS);
        // 18 February is two days from the row on the 20th and 38 from the one on the 11th: ECharts says index 2.
        pointAt('2026-02-18');
        const html = option.tooltip.formatter([{dataIndex: 2}]);
        expect(html).toContain(share(30)); // Beta 30 and Gamma 20 on the second step
        expect(html).toContain(share(20));
        expect(html).not.toContain(share(70));
    });

    it('lists the nearest drawn row when nothing was pointed', async () => {
        const option = await mountChart(STEPS);
        const html = option.tooltip.formatter([{dataIndex: 2}]);
        expect(html).toContain(share(70));
    });

    it('reads the axis pointer with `snap: false`', async () => {
        const option = await mountChart(STEPS);
        expect(option.tooltip.axisPointer.snap).toBe(false);
        expect(option.xAxis.axisPointer.snap).toBe(false);
    });
});
