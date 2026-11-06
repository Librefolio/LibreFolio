// @vitest-environment jsdom
/**
 * ReturnHistogramChart — the wiring the option builder cannot see (F-5; Vitest + jsdom).
 *
 * `returnHistogramChartHelpers.test.ts` pins what is drawn. Here, with ECharts replaced by a recorder:
 *
 * - one chart per mount, drawn from the option the builder made, with the tooltip box in the page's theme;
 * - the tooltip has the size of the other charts' (12 px) and stands beside the pointer on a desktop (`histogramTooltipPosition`);
 *   a `$…$` stretch of a line is typeset as LaTeX (KaTeX), the rest stays text (F8, 06/11/2026);
 * - the tooltip is HTML that ECharts sets as `innerHTML`, written from text the caller supplies: every line is escaped, so a
 *   line holding markup reads as text (the rule of every `*.tooltipEscape.test.ts`);
 * - the heading is the first line and the rest follow it; a datum without a bin says nothing;
 * - going empty disposes the chart instead of leaving it bound to a detached node;
 * - the chart publishes `data-chart-ready`, the signal an E2E waits on.
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

interface FakeChart {
    setOptionCalls: {option: Record<string, unknown>}[];
    disposed: boolean;
}

const {charts, echartsModule} = vi.hoisted(() => {
    const charts: FakeChart[] = [];
    function create(dom: HTMLElement) {
        const state: FakeChart = {setOptionCalls: [], disposed: false};
        const instance = {
            setOption: (option: Record<string, unknown>) => state.setOptionCalls.push({option}),
            getOption: () => ({}),
            on: () => instance,
            off: () => instance,
            resize: () => {},
            getDom: () => dom,
            getWidth: () => 600,
            getHeight: () => 140,
            isDisposed: () => state.disposed,
            dispose: () => {
                state.disposed = true;
            },
            dispatchAction: () => {},
        };
        charts.push(state);
        return instance;
    }
    return {charts, echartsModule: {init: (dom: HTMLElement) => create(dom)}};
});

vi.mock('echarts', () => echartsModule);

import {tick} from 'svelte';

import {cleanup, render, screen, waitFor} from '$test/component';

import {buildTooltipTheme} from './echartsTooltipHelpers';
import {histogramTooltipPosition} from './returnHistogramChartHelpers';
import ReturnHistogramChart from './ReturnHistogramChart.svelte';
import type {HistogramBin} from './returnHistogramChartHelpers';

const BINS: HistogramBin[] = [
    {lowerBound: -2, upperBound: -1, count: 3, holdsCut: false, belowCut: true},
    {lowerBound: -1, upperBound: 0, count: 5, holdsCut: true, belowCut: false},
];
const PAYLOAD = '<img src=x data-pwned onerror=alert(1)>';

function mount(overrides: Record<string, unknown> = {}) {
    const props = {bins: BINS, cut: -0.5, formatAxis: (value: number) => `${value}%`, cutLabel: 'cut', tooltipLines: (bin: HistogramBin) => [`bin ${bin.count}`, 'second line'], testId: 'chart-under-test', ...overrides};
    return render(ReturnHistogramChart, {props});
}

/** The tooltip as ECharts would be asked for it: the formatter of the last option, called with a datum. */
function tooltipFor(binIndex: number | undefined): string {
    const option = charts.at(-1)?.setOptionCalls.at(-1)?.option as {tooltip: {formatter: (params: unknown) => string}} | undefined;
    if (!option) throw new Error('the chart drew nothing');
    return option.tooltip.formatter({data: binIndex === undefined ? undefined : {binIndex}});
}

afterEach(() => {
    cleanup();
    charts.length = 0;
});

describe('ReturnHistogramChart', () => {
    it('draws one chart per mount, from the builder’s option, in the page’s theme box', async () => {
        mount();
        await waitFor(() => expect(charts).toHaveLength(1));
        await waitFor(() => expect(charts[0].setOptionCalls.length).toBeGreaterThan(0));

        const option = charts[0].setOptionCalls.at(-1)!.option as Record<string, unknown> & {series: {type: string; data: unknown[]}[]; tooltip: {backgroundColor: string; confine: boolean}};
        expect(option.series[0].type).toBe('custom');
        expect(option.series[0].data).toHaveLength(2);
        expect(option.tooltip.confine).toBe(true);
        expect(option.tooltip.backgroundColor).toBe(buildTooltipTheme(false, screen.getByTestId('chart-under-test')).bg);
    });

    it('publishes that it is drawing, for a test to wait on', async () => {
        mount();
        await waitFor(() => expect(screen.getByTestId('chart-under-test').getAttribute('data-chart-ready')).not.toBeNull());
    });

    it('draws the tooltip at the size of the other charts, beside the pointer', async () => {
        mount();
        await waitFor(() => expect(charts[0]?.setOptionCalls.length).toBeGreaterThan(0));

        const option = charts[0].setOptionCalls.at(-1)!.option as {tooltip: {textStyle: {fontSize: number}; position: unknown}};
        expect(option.tooltip.textStyle.fontSize).toBe(12);
        expect(option.tooltip.position).toBe(histogramTooltipPosition);
    });

    it('typesets a $…$ stretch as LaTeX and leaves the rest as text', async () => {
        mount({tooltipLines: () => ['$[−1{,}2\\%;\\,−0{,}8\\%)$', '14 days · 5.6%']});
        await waitFor(() => expect(charts[0]?.setOptionCalls.length).toBeGreaterThan(0));

        const holder = document.createElement('div');
        holder.innerHTML = tooltipFor(0);
        expect(holder.querySelector('.katex'), 'the interval was not typeset').not.toBeNull();
        expect(holder.textContent).toContain('14 days · 5.6%');
        expect(holder.textContent).not.toContain('$');
    });

    it('writes the heading first and the other lines after it', async () => {
        mount();
        await waitFor(() => expect(charts[0]?.setOptionCalls.length).toBeGreaterThan(0));

        const html = tooltipFor(1);
        expect(html.indexOf('bin 5')).toBeGreaterThanOrEqual(0);
        expect(html.indexOf('second line')).toBeGreaterThan(html.indexOf('bin 5'));
    });

    it('escapes every line: markup in a line reads as text', async () => {
        mount({tooltipLines: () => [PAYLOAD, PAYLOAD]});
        await waitFor(() => expect(charts[0]?.setOptionCalls.length).toBeGreaterThan(0));

        const holder = document.createElement('div');
        holder.innerHTML = tooltipFor(0);
        expect(holder.querySelector('[data-pwned]'), 'a line of the tooltip became markup').toBeNull();
        expect(holder.textContent).toContain(PAYLOAD);
    });

    it('says nothing for a datum that is no bin', async () => {
        mount();
        await waitFor(() => expect(charts[0]?.setOptionCalls.length).toBeGreaterThan(0));

        expect(tooltipFor(undefined)).toBe('');
        expect(tooltipFor(9)).toBe('');
    });

    it('disposes the chart when the bins go away, and draws a new one when they come back', async () => {
        const {rerender} = mount();
        await waitFor(() => expect(charts).toHaveLength(1));

        await rerender({bins: [], cut: null, formatAxis: (value: number) => `${value}%`, cutLabel: '', tooltipLines: () => [], testId: 'chart-under-test'});
        await tick();
        await waitFor(() => expect(charts[0].disposed).toBe(true));

        await rerender({bins: BINS, cut: -0.5, formatAxis: (value: number) => `${value}%`, cutLabel: 'cut', tooltipLines: () => ['x'], testId: 'chart-under-test'});
        await waitFor(() => expect(charts).toHaveLength(2));
    });
});
