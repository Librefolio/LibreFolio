// @vitest-environment jsdom
/**
 * PositionsReturnChart on steps (D-P4, Y5-3, #48): every line (the positions' and the portfolio's) is a stepped line, and the tooltip
 * lists what each line says on the day the pointer is on.
 *
 * On a time axis ECharts hands each series the data point nearest to the pointer, so in the right half of a step a line would show the
 * next step's value while the line says another. The chart keeps the pointed day (`updateAxisPointer`, `snap: false`) and lists, for
 * every drawn line, the point holding it (`lineOnDay`); a line that does not exist that day (before its first point, after its last)
 * is not listed.
 *
 * Same harness as `PositionsReturnChart.test.ts`: `echarts` is a recorder (here it also keeps the handlers `on` was given) and every
 * element answers with a client rect.
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
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatDay} from '$lib/utils/core/formatAxisDate';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import PositionsReturnChart from './PositionsReturnChart.svelte';
import type {PositionLine} from './positionsSeries';

const stepped = (id: string, label: string, points: Array<[string, number | null]>, kind: PositionLine['kind'] = 'position'): PositionLine => ({id, label, points: points.map(([date, value]) => ({date, value})), closedOn: null, complete: true, kind, stepped: true});

/** A: 100 to 10 January, -50 to 20 January, held to 31 January. B: 10 from 11 to 25 January (it did not exist before). Portfolio: 0 to 31 January. */
const A = () =>
    stepped('12-3', 'Alpha', [
        ['2026-01-02', 100],
        ['2026-01-11', -50],
        ['2026-01-21', 0],
        ['2026-01-31', 0],
    ]);
const B = () =>
    stepped('7-0', 'Beta', [
        ['2026-01-11', 10],
        ['2026-01-25', 10],
    ]);
const PORTFOLIO = () =>
    stepped(
        'portfolio',
        'Portfolio',
        [
            ['2026-01-02', 0],
            ['2026-01-31', 0],
        ],
        'portfolio',
    );

const money = (value: number) => escapeHtml(formatCurrencyAmountPlain(value, 'EUR', {showSign: true}));

interface DrawnOption {
    series: Array<{id: string; step?: unknown}>;
    tooltip: {formatter: (params: unknown) => string; axisPointer: {snap: boolean}};
    xAxis: {axisPointer: {snap: boolean}};
}

function lastOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series) && option.tooltip != null);
    return call?.option as unknown as DrawnOption | undefined;
}

let restoreRects: (() => void) | undefined;
beforeAll(async () => {
    await setupI18n();
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(() => [{x: 0, y: 0, top: 0, left: 0, width: 800, height: 400, right: 800, bottom: 400}] as unknown as DOMRectList);
    restoreRects = () => spy.mockRestore();
});
afterAll(() => restoreRects?.());
beforeEach(() => {
    chartInstances.length = 0;
});

async function mountChart(lines: PositionLine[]): Promise<DrawnOption> {
    render(PositionsReturnChart, {props: {lines, view: 'absolute' as const, colorOf: () => 'rgb(1, 2, 3)', currency: 'EUR'}});
    await waitFor(() => expect(lastOption()).toBeDefined(), {timeout: 5_000});
    return lastOption()!;
}

function pointAt(day: string): void {
    const [year, month, date] = day.split('-').map(Number);
    const handlers = chartInstances[0].handlers.get('updateAxisPointer') ?? [];
    expect(handlers.length, 'the chart listens to the axis pointer').toBeGreaterThan(0);
    for (const handler of handlers) handler({axesInfo: [{value: new Date(year, month - 1, date).getTime()}]});
}

describe('the lines are steps', () => {
    it('draws every stepped line with step end', async () => {
        const option = await mountChart([PORTFOLIO(), A(), B()]);
        expect(option.series.filter((series) => series.id !== undefined).map((series) => series.step)).toEqual(['end', 'end', 'end']);
    });

    it('reads the axis pointer with `snap: false`', async () => {
        const option = await mountChart([A()]);
        expect(option.tooltip.axisPointer.snap).toBe(false);
        expect(option.xAxis.axisPointer.snap).toBe(false);
    });
});

describe('the tooltip lists each line on the pointed day', () => {
    it('reads the step holding the day, not the drawn point nearest to it', async () => {
        const option = await mountChart([PORTFOLIO(), A(), B()]);
        // 19 January: one day from A's step on the 21st (value 0), eight from the one on the 11th (-50): ECharts says the 21st.
        pointAt('2026-01-19');
        const html = option.tooltip.formatter([{seriesId: '12-3', value: ['2026-01-21', 0]}]);
        expect(html).toContain(money(-50));
        expect(html).toContain(money(10));
        expect(html).toContain('Alpha');
        expect(html).toContain('Beta');
        expect(html).toContain(escapeHtml(formatDay('2026-01-19')));
    });

    it('does not list a line that does not exist that day', async () => {
        const option = await mountChart([PORTFOLIO(), A(), B()]);
        pointAt('2026-01-05');
        const html = option.tooltip.formatter([{seriesId: '12-3', value: ['2026-01-02', 100]}]);
        expect(html).toContain('Alpha');
        expect(html).not.toContain('Beta');
        pointAt('2026-01-28');
        const later = option.tooltip.formatter([{seriesId: '12-3', value: ['2026-01-31', 0]}]);
        expect(later).not.toContain('Beta');
    });

    it('lists the lines highest first', async () => {
        const option = await mountChart([PORTFOLIO(), A(), B()]);
        pointAt('2026-01-12');
        const html = option.tooltip.formatter([{seriesId: '12-3', value: ['2026-01-11', -50]}]);
        expect(html.indexOf('Beta')).toBeLessThan(html.indexOf('Portfolio'));
        expect(html.indexOf('Portfolio')).toBeLessThan(html.indexOf('Alpha'));
    });

    it('control: without a pointed day it lists the points ECharts handed over', async () => {
        const option = await mountChart([A()]);
        const html = option.tooltip.formatter([{seriesId: '12-3', value: ['2026-01-21', 0]}]);
        expect(html).toContain('Alpha');
        expect(html).toContain(money(0));
        expect(html).not.toContain(money(-50));
    });
});
