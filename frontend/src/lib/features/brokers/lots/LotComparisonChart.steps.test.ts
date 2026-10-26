// @vitest-environment jsdom
/**
 * LotComparisonChart on steps (D-P4, Y5-3): the value and return histories of the selected lots are one point per stretch without news,
 * each holding from its `date` to its `through`.
 *
 * The chart takes them as the points of their witness days (`lotStepRows.ts`), so its sums by date, its resolution cascade and its zoom run as
 * they always did on a few dates instead of one per day. What these cases pin:
 *   - the daily resolution is the steps themselves: a point on each witness day, every line drawn with `step: 'end'`;
 *   - a lot has a point only while it exists (the sum by date follows the lots that are there);
 *   - the tooltip lists what each line says on the day the pointer is on, not at the drawn point nearest to it.
 *
 * ECharts is a recorder (jsdom has no canvas): it keeps every `setOption` payload and the handlers `on` was given.
 */
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
        getZr: () => {on: () => void; off: () => void};
        dispatchAction: (action: unknown) => void;
        resize: () => void;
        clear: () => void;
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
            getWidth: () => 1200,
            getHeight: () => 400,
            on: (event, handler) => {
                chart.handlers.set(event, [...(chart.handlers.get(event) ?? []), handler]);
            },
            off: (event) => {
                chart.handlers.delete(event);
            },
            getZr: () => ({on: () => {}, off: () => {}}),
            dispatchAction: () => {},
            resize: () => {},
            clear: () => {},
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
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import LotComparisonChart from './LotComparisonChart.svelte';

const value = (lot_id: number, date: string, through: string, open_value: number) => ({lot_id, date, through, open_value: String(open_value), proceeds: '0', total_value: String(open_value), original_cost: '100', pnl: String(open_value - 100)});
const ret = (lot_id: number, date: string, through: string, total_return: number) => ({lot_id, date, through, total_return: String(total_return), relative_return: String(total_return)});

/** Lot 1 holds 100 to 10 January, 120 to 31 January. Lot 2 opens on 11 January at 50 and is sold out after 20 January. */
const VALUE = [value(1, '2026-01-02', '2026-01-10', 100), value(1, '2026-01-11', '2026-01-31', 120), value(2, '2026-01-11', '2026-01-20', 50)];
const RETURN = [ret(1, '2026-01-02', '2026-01-10', 0), ret(1, '2026-01-11', '2026-01-31', 0.2), ret(2, '2026-01-11', '2026-01-20', -0.5)];
const RANGE = {start: '2026-01-02', end: '2026-01-31'};
const LOTS = [
    {lot_id: 1, direction: 'LONG', opening_date: '2026-01-02', value_source: 'MARKET_PRICE'},
    {lot_id: 2, direction: 'LONG', opening_date: '2026-01-11', value_source: 'MARKET_PRICE'},
];

interface Drawn {
    id?: string;
    name?: string;
    type?: string;
    step?: unknown;
    data?: Array<{value?: [string | number, number | null]} | [string | number, number | null]>;
}
interface DrawnOption {
    series: Drawn[];
    tooltip: {formatter: (params: unknown) => string};
    xAxis: {axisPointer?: {snap: boolean}};
}

function lastOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series) && option.tooltip != null);
    return call?.option as unknown as DrawnOption | undefined;
}

const xOf = (datum: NonNullable<Drawn['data']>[number]): string | number => (Array.isArray(datum) ? datum[0] : (datum.value as [string | number, number | null])[0]);
const yOf = (datum: NonNullable<Drawn['data']>[number]): number | null => (Array.isArray(datum) ? datum[1] : (datum.value as [string | number, number | null])[1]);

let restoreRects: (() => void) | undefined;
beforeAll(async () => {
    await setupI18n();
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, top: 0, left: 0, width: 1200, height: 400, right: 1200, bottom: 400}] as unknown as DOMRectList);
    restoreRects = () => spy.mockRestore();
});
afterAll(() => restoreRects?.());
beforeEach(() => {
    chartInstances.length = 0;
});

async function mountChart(): Promise<DrawnOption> {
    render(LotComparisonChart, {props: {selectedLots: LOTS, valueHistory: VALUE, returnHistory: RETURN, range: RANGE, brokers: [], currency: 'EUR', xAxisRange: null} as never});
    await waitFor(() => expect(lastOption()).toBeDefined(), {timeout: 5_000});
    return lastOption()!;
}

const residual = (option: DrawnOption): Drawn => option.series.find((series) => series.id === 'value-residual')!;

describe('the daily resolution is the steps', () => {
    it('draws every line with step end', async () => {
        const option = await mountChart();
        const lines = option.series.filter((series) => series.type === 'line');
        expect(lines.length).toBeGreaterThan(0);
        expect(lines.every((series) => series.step === 'end')).toBe(true);
    });

    it('has a point on the witness days only, not a point per day', async () => {
        const option = await mountChart();
        const days = residual(option).data!.map(xOf);
        expect(days.length).toBeLessThan(15);
        expect(days).toContain('2026-01-02');
        expect(days).toContain('2026-01-11');
        expect(days).toContain('2026-01-31');
        expect(days).not.toContain('2026-01-05');
    });

    it('sums the lots that exist on each day: lot 2 stops counting after its last day', async () => {
        const option = await mountChart();
        const byDay = new Map(residual(option).data!.map((datum) => [xOf(datum), yOf(datum)]));
        expect(byDay.get('2026-01-02')).toBe(100);
        expect(byDay.get('2026-01-11')).toBe(170);
        expect(byDay.get('2026-01-20')).toBe(170);
        expect(byDay.get('2026-01-25')).toBe(120);
        expect(byDay.get('2026-01-31')).toBe(120);
    });

    it('reads the axis pointer with `snap: false`', async () => {
        const option = await mountChart();
        expect(option.xAxis.axisPointer?.snap).toBe(false);
    });
});

describe('the tooltip of a step line', () => {
    function pointAt(day: string): void {
        const [year, month, date] = day.split('-').map(Number);
        const handlers = chartInstances[0].handlers.get('updateAxisPointer') ?? [];
        expect(handlers.length, 'the chart listens to the axis pointer').toBeGreaterThan(0);
        for (const handler of handlers) handler({axesInfo: [{axisDim: 'x', value: new Date(year, month - 1, date).getTime()}]});
    }
    const money = (amount: number) => formatCurrencyAmountPlain(amount, 'EUR');

    /** What ECharts hands the formatter: the residual line's point nearest to the pointer. */
    function nearestParam(option: DrawnOption, day: string): Record<string, unknown> {
        const series = residual(option);
        const index = series.data!.findIndex((datum) => xOf(datum) === day);
        const datum = series.data![index];
        return {seriesId: 'value-residual', seriesIndex: option.series.indexOf(series), seriesName: series.name, dataIndex: index, data: datum, value: Array.isArray(datum) ? datum : datum.value, axisValue: Date.parse(day), color: '#123456'};
    }

    it('lists what the line says on the pointed day, not at the drawn point nearest to it', async () => {
        const option = await mountChart();
        // 10 January, the day before lot 2 opens: the nearest drawn point is the 11th (170), the line says 100.
        pointAt('2026-01-10');
        const html = option.tooltip.formatter([nearestParam(option, '2026-01-11')]);
        expect(html).toContain(money(100));
        expect(html).not.toContain(money(170));
    });

    it('lists the nearest drawn point when nothing was pointed', async () => {
        const option = await mountChart();
        const html = option.tooltip.formatter([nearestParam(option, '2026-01-11')]);
        expect(html).toContain(money(170));
    });
});
