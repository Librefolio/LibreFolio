// @vitest-environment jsdom
/**
 * The pointer of the growth chart rests on days (Y2 FB-2, applied to the main chart by Y).
 *
 * The time axis of the chart sets `axisPointer.snap: false`, so ECharts leaves the pointer line wherever the mouse is. `attachDaySnap`
 * (`components/charts/dayPointerSnap`) moves it to the nearest day; the chart must hand it its instance, as the other step charts do.
 *
 * ECharts is replaced by a recorder (jsdom has no canvas), as in `GrowthChart.steps.test.ts`.
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

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
        dispatchAction: (payload: Record<string, unknown>) => void;
        dispatched: Array<Record<string, unknown>>;
        getZr: () => {on: () => void};
        convertToPixel: (finder: unknown, value: number) => number;
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
            dispatched: [],
            dispatchAction: (payload) => {
                chart.dispatched.push(payload);
            },
            getZr: () => ({on: () => {}}),
            convertToPixel: (_finder, value) => value / 1_000_000,
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

import {cleanup, render, setupI18n, waitFor} from '$test/component';
import type {PortfolioHistoryPoint} from '$lib/stores/portfolio/portfolioStore.svelte';
import GrowthChart from './GrowthChart.svelte';

const eur = (amount: number) => ({code: 'EUR', amount: amount.toFixed(2)});

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

/** A local midnight, the way a day is a point of the time axis. */
const localMidnightMs = (iso: string): number => new Date(`${iso}T00:00:00`).getTime();

const HISTORY = [step('2026-01-01', '2026-01-10', 1), step('2026-01-11', '2026-02-19', 3), step('2026-02-20', '2026-03-01', 6)];

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    chartInstances.length = 0;
});
afterEach(() => {
    cleanup();
});

describe('the pointer of the growth chart', () => {
    it('is moved to the nearest day when it rests between two', async () => {
        render(GrowthChart, {props: {history: HISTORY, range: {start: '2026-01-01', end: '2026-03-01'}, mwrrLine: []}});
        await waitFor(() => expect(chartInstances.length).toBeGreaterThan(0), {timeout: 5_000});
        const chart = chartInstances.at(-1)!;
        await waitFor(() => expect(chart.handlers.get('updateAxisPointer')?.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});

        const midnight = localMidnightMs('2026-01-20');
        const betweenDays = midnight + 5 * 3_600_000;
        for (const handler of chart.handlers.get('updateAxisPointer') ?? []) handler({axesInfo: [{axisDim: 'x', axisIndex: 0, value: betweenDays}]});

        const moved = chart.dispatched.filter((payload) => payload.type === 'updateAxisPointer');
        expect(moved, 'the pointer is dispatched again, on the nearest day').toHaveLength(1);
        expect((moved[0].axesInfo as Array<{value: number}>)[0].value).toBe(midnight);
    });

    it('is left alone when it already rests on a day', async () => {
        render(GrowthChart, {props: {history: HISTORY, range: {start: '2026-01-01', end: '2026-03-01'}, mwrrLine: []}});
        await waitFor(() => expect(chartInstances.length).toBeGreaterThan(0), {timeout: 5_000});
        const chart = chartInstances.at(-1)!;
        await waitFor(() => expect(chart.handlers.get('updateAxisPointer')?.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});

        for (const handler of chart.handlers.get('updateAxisPointer') ?? []) handler({axesInfo: [{axisDim: 'x', axisIndex: 0, value: localMidnightMs('2026-01-20')}]});

        expect(chart.dispatched.filter((payload) => payload.type === 'updateAxisPointer')).toHaveLength(0);
    });
});
