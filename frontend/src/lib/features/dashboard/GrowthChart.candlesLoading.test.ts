// @vitest-environment jsdom
/**
 * Y6-4 (Y-18) — the candles have a loading indicator of their own.
 *
 * `GrowthChart` has the skeleton of the history (`loading`), which says nothing about the candles: they are asked on the
 * first activation of the Candles submode, so a user who goes straight to them waits on an empty chart. The Dashboard and the
 * broker page hand `pnlCandlesLoading` down; while it is on, and no candle has arrived, the chart says so.
 *
 * ECharts is replaced by a recorder (jsdom has no canvas), as in `GrowthChart.steps.test.ts`.
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

// `localStorage` of Node is unusable without `--localstorage-file`: the submode is chosen by a click, as the user does.
const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {cleanup, fireEvent, render, setupI18n, waitFor} from '$test/component';
import type {PortfolioHistoryPoint, PortfolioPnlCandleSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
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

const HISTORY = [step('2026-01-01', '2026-01-10', 1), step('2026-01-11', '2026-02-19', 3), step('2026-02-20', '2026-03-01', 6)];
const RANGE = {start: '2026-01-01', end: '2026-03-01'};
const CANDLES = {hypothetical: true, points: []} as unknown as PortfolioPnlCandleSeries;
const LOADING = 'growth-pnl-candles-loading';

type Props = ComponentProps<typeof GrowthChart>;

async function mountOnCandles(props: Partial<Props>) {
    const view = render(GrowthChart, {props: {history: HISTORY, range: RANGE, mwrrLine: [], ...props}});
    await waitFor(() => expect(chartInstances.length).toBeGreaterThan(0), {timeout: 5_000});
    await fireEvent.click(view.getByTestId('growth-toggle-pnl'));
    await fireEvent.click(view.getByTestId('growth-pnl-submode-candles'));
    return view;
}

beforeAll(async () => {
    await setupI18n();
});
beforeEach(() => {
    chartInstances.length = 0;
    storage.clear();
});
afterEach(() => {
    cleanup();
});

describe('the candles loading indicator', () => {
    it('shows while the candles are asked and none has arrived', async () => {
        const view = await mountOnCandles({pnlCandles: null, pnlCandlesLoading: true});
        expect(view.getByTestId(LOADING)).toBeTruthy();
    });

    it('lets the pointer through to the controls under it: the user can leave Candles while they load', async () => {
        const view = await mountOnCandles({pnlCandles: null, pnlCandlesLoading: true});
        // The skeleton covers the chart, the submode buttons included: it must not take their clicks (a held request must not hold the user).
        expect(view.getByTestId(LOADING).className).toContain('pointer-events-none');
    });

    it('is not there when nothing is asked', async () => {
        const view = await mountOnCandles({pnlCandles: null, pnlCandlesLoading: false});
        expect(view.queryByTestId(LOADING)).toBeNull();
    });

    it('goes away when the candles arrive, even if a refresh is still running', async () => {
        const view = await mountOnCandles({pnlCandles: CANDLES, pnlCandlesLoading: true});
        expect(view.queryByTestId(LOADING)).toBeNull();
    });

    it('belongs to the Candles submode only', async () => {
        const view = await mountOnCandles({pnlCandles: null, pnlCandlesLoading: true});
        await fireEvent.click(view.getByTestId('growth-pnl-submode-line'));
        expect(view.queryByTestId(LOADING)).toBeNull();
    });

    it('turns on and off with the request', async () => {
        const view = await mountOnCandles({pnlCandles: null, pnlCandlesLoading: false});
        await view.rerender({pnlCandlesLoading: true});
        expect(view.queryByTestId(LOADING)).not.toBeNull();
        await view.rerender({pnlCandlesLoading: false});
        expect(view.queryByTestId(LOADING)).toBeNull();
    });
});
