// @vitest-environment jsdom
/**
 * GrowthChart — a lazily-arriving input must never be answered from a memo built
 * before that input existed (regression, G1b family).
 *
 * WHAT BROKE. `getResolutionData()` memoises the whole per-resolution aggregation in
 * `resolutionCache`, keyed by `resolution` — ONE dimension — while the value it stores
 * depends on eleven reactive inputs. Invalidation happened only through
 * `if (history !== lastHistoryRef) resetResolutionState()`. Several of those inputs are
 * fetched lazily and therefore land AFTER the first render:
 *
 *   1. the user switches to P&L → candles;
 *   2. `getResolutionData()` runs while `pnlCandles` is still undefined and caches an
 *      entry whose candle points are all `'-'` gap sentinels;
 *   3. the fetch lands and the render effect wakes (it does depend on `pnlCandles`);
 *   4. `getResolutionData()` returns the SAME cached entry — 93 gaps, forever, surviving
 *      every re-entry into the submode.
 *
 * WHY THIS TEST IS SHAPED THE WAY IT IS. The defect is invisible to any test that sets
 * up its final state: render with `pnlCandles` already present and the broken code passes.
 * What has to be encoded is ARRIVAL ORDER, so every case below mounts with the input
 * ABSENT, proves the memo was populated in that state (`0` real values against a series
 * array of the expected shape — a negative with a presence barrier in front of it, never
 * a bare "nothing rendered"), delivers the input, proves a render actually followed, and
 * only then asserts the aggregated output carries real data.
 *
 * WHY IT IS PARAMETERISED. `pnlCandles` is the instance; the defect is the class. Every
 * member of `aggregationInputs` that the caller fills in asynchronously is exposed to the
 * same stale entry, so all six are driven through the same arrival sequence. A seventh
 * lazily-fetched prop added tomorrow belongs in the table, not in a new file.
 *
 * WHAT IS MOCKED, AND WHAT IS NOT. Only the ECharts module, replaced by a recorder that
 * captures the options handed to it (jsdom has no canvas, and rendering pixels is not the
 * subject). The component under test is the real `GrowthChart`: real props, real runes,
 * real `$derived` bundle, real memo, real render effect, real aggregation helpers. The
 * assertion reads GrowthChart's own output — the series data it hands to the chart — which
 * is precisely what the stale entry corrupted.
 *
 * WHAT IS DELIBERATELY NOT ASSERTED. Series NAMES for the built-in dimensions: they come
 * from `$_(...)` and the UI ships in EN/IT/FR/ES. The fixed-slot ORDER of
 * `buildChartUpdateSeries` is the contract those tests use instead (it documents itself as
 * "Fixed 6-slot order matches buildFullSeries's matching index reads exactly"). Broker
 * series ARE matched by name, because those names are values this test supplied as props.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: a recorder, not a renderer.
 *
 * It answers every call `GrowthChart` and its chart helpers make on an instance
 * (`attachChartReady` → `on`, `setupTooltipAutoHide` → `dispatchAction`,
 * `attachDataZoomTouchPan` → `getOption`, `scheduleFirstRenderStabilityFix` →
 * `isDisposed`/`resize`, `renderChart` → `getDom`/`getWidth`) and keeps every `setOption`
 * payload so a test can read what the component decided to draw.
 *
 * `getDom()` returns the element `init()` was handed, which is what keeps `renderChart`
 * on its normal path: it disposes and re-inits only when the instance's DOM no longer
 * matches the bound container. One mount therefore means exactly one instance, and the
 * tests assert that.
 */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
        opts: unknown;
    }

    interface FakeChart {
        setOptionCalls: SetOptionCall[];
        setOption: (option: Record<string, unknown>, opts?: unknown) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler: () => void) => void;
        dispatchAction: () => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    /** Plot width reported to the resolution ladder. 40 daily buckets over 1200px is a
     *  density of 0.033 bucket/px, far under the 1.3 high-density threshold, so the
     *  chart stays at 'daily' and one bucket means one day — no aggregation tier in the
     *  middle of an assertion about aggregation inputs. */
    const PLOT_WIDTH_PX = 1200;

    function createFakeChart(dom: unknown): FakeChart {
        const handlers = new Map<string, Set<() => void>>();
        let merged: Record<string, unknown> = {};
        let disposed = false;

        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option, opts) {
                chart.setOptionCalls.push({option, opts});
                merged = {...merged, ...option};
            },
            // ECharts normalises a single dataZoom object into an array; `getZoomPercent()`
            // reads `option.dataZoom?.[0]`, so the stand-in has to normalise it too.
            getOption: () => {
                const zoom = merged.dataZoom;
                return {...merged, dataZoom: zoom == null ? [] : Array.isArray(zoom) ? zoom : [zoom]};
            },
            getWidth: () => PLOT_WIDTH_PX,
            getHeight: () => 360,
            getDom: () => dom,
            on(event, handler) {
                const bucket = handlers.get(event) ?? new Set<() => void>();
                bucket.add(handler);
                handlers.set(event, bucket);
            },
            off(event, handler) {
                handlers.get(event)?.delete(handler);
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
        echartsModule: {init: (dom: unknown) => createFakeChart(dom)},
    };
});

vi.mock('echarts', () => echartsModule);

import {fireEvent, render, setupI18n, waitFor} from '$test/component';
import type {PortfolioAcquisitionFundingSeries, PortfolioBrokerPnlHistory, PortfolioCostHistorySeries, PortfolioDepositHistorySeries, PortfolioHistoryPoint, PortfolioIncomeHistorySeries, PortfolioPnlCandleSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
import GrowthChart from './GrowthChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

const DAY_COUNT = 40;

const DATES: string[] = Array.from({length: DAY_COUNT}, (_, index) => new Date(Date.UTC(2026, 0, 1 + index)).toISOString().slice(0, 10));

const eur = (amount: number) => ({code: 'EUR', amount: amount.toFixed(2)});

/**
 * ONE array instance, shared by every render in this file, and never rebuilt.
 *
 * This is load-bearing rather than tidy: `GrowthChart` clears `resolutionCache` exactly
 * when `history !== lastHistoryRef`. Handing it a fresh array on the arrival step would
 * reset the cache as a side effect, the stale entry would never be consulted, and the
 * whole file would pass against the broken code while proving nothing.
 */
const HISTORY: PortfolioHistoryPoint[] = DATES.map((date, index) => ({
    date,
    cash_value: eur(1_000 + index),
    market_value: eur(10_000 + index * 100),
    nav_value: eur(11_000 + index * 100),
    capital_baseline: eur(10_500),
    book_asset_like: eur(9_000 + index * 50),
    cash_from_contributed_capital: eur(800),
    cash_from_generated_returns: eur(200 + index),
    total_pnl: eur(500 + index * 100),
    twrr: (index * 0.001).toFixed(6),
    mwrr_cumulative: (index * 0.0012).toFixed(6),
    roi: (index * 0.0009).toFixed(6),
}));

const PNL_CANDLES: PortfolioPnlCandleSeries = {
    hypothetical: true,
    points: DATES.map((date, index) => ({
        date,
        open: eur(500 + index * 100),
        high: eur(560 + index * 100),
        low: eur(480 + index * 100),
        close: eur(540 + index * 100),
    })),
};

const BROKER_NAMES = ['Lazy Broker A', 'Lazy Broker B'] as const;

const BROKER_PNL_HISTORY: PortfolioBrokerPnlHistory[] = BROKER_NAMES.map((broker_name, brokerIndex) => ({
    broker_id: brokerIndex + 1,
    broker_name,
    points: DATES.map((date, index) => ({date, total_pnl: eur(200 + brokerIndex * 100 + index * 10)})),
}));

const INCOME_HISTORY: PortfolioIncomeHistorySeries = {
    points: DATES.map((date, index) => ({date, dividend: eur(12 + index), interest: eur(3 + index)})),
    missing_fx_pairs: [],
};

const COST_HISTORY: PortfolioCostHistorySeries = {
    points: DATES.map((date, index) => ({date, cost: eur(-(4 + index))})),
    missing_fx_pairs: [],
};

const DEPOSIT_HISTORY: PortfolioDepositHistorySeries = {
    points: DATES.map((date, index) => ({date, deposit: eur(150 + index)})),
    missing_fx_pairs: [],
};

const ACQUISITION_FUNDING: PortfolioAcquisitionFundingSeries = {
    points: DATES.map((date, index) => ({date, from_new_capital: eur(90 + index), from_reinvested: eur(45 + index)})),
};

// =============================================================================
// Reading what GrowthChart decided to draw
// =============================================================================

interface SeriesUpdate {
    name: string;
    data: unknown[];
}

/** The series array of the most recent `setOption` that carried one — the full rebuild
 *  on a mode switch and the partial `{name, data}` update on a data change both do. */
function renderedSeries(): SeriesUpdate[] {
    expect(chartInstances).toHaveLength(1);
    const call = [...chartInstances[0].setOptionCalls].reverse().find((entry) => Array.isArray(entry.option.series));
    if (!call) throw new Error('GrowthChart never handed a series array to ECharts');
    return call.option.series as SeriesUpdate[];
}

function setOptionCount(): number {
    expect(chartInstances).toHaveLength(1);
    return chartInstances[0].setOptionCalls.length;
}

/** A line/bar datum is a `SeriesPoint`: `{value: [date, number | null], …}`. */
function pointValue(datum: unknown): number | null {
    const value = (datum as {value?: unknown})?.value;
    return Array.isArray(value) ? ((value[1] as number | null) ?? null) : null;
}

function nonNullPoints(series: SeriesUpdate | undefined): number {
    return (series?.data ?? []).filter((datum) => pointValue(datum) != null).length;
}

/** For the sparse flow dimensions (income, costs, deposits, acquisition) a date with no
 *  data is rendered as 0 — that 0 is this family's gap sentinel, so "arrived" means
 *  "carries a value that is neither null nor 0". */
function nonZeroPoints(series: SeriesUpdate | undefined): number {
    return (series?.data ?? []).filter((datum) => {
        const value = pointValue(datum);
        return value != null && value !== 0;
    }).length;
}

/** A candlestick datum is either a real `[open, close, low, high]` quad or ECharts'
 *  `'-'` empty-value sentinel, which is exactly what the stale entry was full of. */
function realCandleQuads(series: SeriesUpdate | undefined): number {
    return (series?.data ?? []).filter((datum) => Array.isArray(datum) && datum.length === 4 && datum.every((component) => typeof component === 'number' && Number.isFinite(component))).length;
}

function brokerSeries(series: SeriesUpdate[]): SeriesUpdate[] {
    return series.filter((entry) => (BROKER_NAMES as readonly string[]).includes(entry.name));
}

// =============================================================================
// The class of lazily-arriving inputs
// =============================================================================

interface LazyInputCase {
    /** The prop, named as the component declares it. */
    prop: string;
    /** The P&L submode that renders this input. */
    submode: 'line' | 'candles' | 'income';
    /** Series count in that submode while the input is still absent — the presence
     *  barrier that makes the "0 real values" assertion mean something. */
    seriesWhileAbsent: number;
    /** The props update that delivers the input. */
    arrival: Record<string, unknown>;
    /** How many real (non-sentinel) values the input should put on the chart. */
    expectedRealValues: number;
    /** Reads that count out of the rendered series. */
    countRealValues: (series: SeriesUpdate[]) => number;
}

const LAZY_INPUTS: LazyInputCase[] = [
    {
        prop: 'pnlCandles',
        submode: 'candles',
        // Candlestick only: the broker overlay needs >= 2 brokers, and this case has none.
        seriesWhileAbsent: 1,
        arrival: {pnlCandles: PNL_CANDLES},
        expectedRealValues: DAY_COUNT,
        countRealValues: (series) => realCandleQuads(series[0]),
    },
    {
        prop: 'brokerPnlHistory',
        submode: 'line',
        // Fixed slots: total-positive, total-negative, dashed reference. Broker lines are
        // appended after them, so while the prop is absent there are exactly three.
        seriesWhileAbsent: 3,
        arrival: {brokerPnlHistory: BROKER_PNL_HISTORY},
        expectedRealValues: 2 * DAY_COUNT,
        countRealValues: (series) => brokerSeries(series).reduce((total, entry) => total + nonNullPoints(entry), 0),
    },
    {
        prop: 'incomeHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {incomeHistory: INCOME_HISTORY},
        expectedRealValues: 2 * DAY_COUNT,
        // Slots 0 and 1 of the income submode's fixed 6-slot order: dividend, interest.
        countRealValues: (series) => nonZeroPoints(series[0]) + nonZeroPoints(series[1]),
    },
    {
        prop: 'costHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {costHistory: COST_HISTORY},
        expectedRealValues: DAY_COUNT,
        // Slot 2: costs (FEE+TAX, signed negative).
        countRealValues: (series) => nonZeroPoints(series[2]),
    },
    {
        prop: 'depositHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {depositHistory: DEPOSIT_HISTORY},
        expectedRealValues: DAY_COUNT,
        // Slot 3: deposit size.
        countRealValues: (series) => nonZeroPoints(series[3]),
    },
    {
        prop: 'acquisitionFunding',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {acquisitionFunding: ACQUISITION_FUNDING},
        expectedRealValues: 2 * DAY_COUNT,
        // Slots 4 and 5: the new-capital / reinvested funding split.
        countRealValues: (series) => nonZeroPoints(series[4]) + nonZeroPoints(series[5]),
    },
];

// =============================================================================

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    chartInstances.length = 0;
});

describe('GrowthChart aggregation memo', () => {
    it.each(LAZY_INPUTS)('rebuilds the P&L $submode aggregation when $prop arrives after the memo was populated without it', async ({prop, submode, seriesWhileAbsent, arrival, expectedRealValues, countRealValues}) => {
        const onRequestPnlCandles = vi.fn();
        const {getByTestId, rerender} = render(GrowthChart, {
            props: {history: HISTORY, onRequestPnlCandles},
        });

        // 1. Mounted with the lazily-arriving input ABSENT. The first render already
        //    memoises the 'daily' entry — the poisoning happens before any interaction.
        await waitFor(() => expect(chartInstances).toHaveLength(1), {timeout: 5_000});

        // 2. Enter the submode that reads this input, and let the memo answer there too.
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await fireEvent.click(getByTestId(`growth-pnl-submode-${submode}`));
        await waitFor(() => expect(renderedSeries()).toHaveLength(seriesWhileAbsent), {timeout: 5_000});

        //    The series exist and are empty of real values: a negative assertion with the
        //    positive one standing in front of it, so "absent" can never be read off a
        //    chart that simply had not rendered yet.
        expect(countRealValues(renderedSeries())).toBe(0);

        // 3. The fetch lands. Sample the render counter BEFORE delivering it, so the
        //    barrier below proves a render happened AFTER the arrival, not merely that
        //    some render happened at some point.
        const rendersBeforeArrival = setOptionCount();
        await rerender(arrival);
        await waitFor(() => expect(setOptionCount()).toBeGreaterThan(rendersBeforeArrival), {timeout: 5_000});

        // 4. The aggregation must now carry the data that arrived — not the entry cached
        //    while it did not exist.
        expect(countRealValues(renderedSeries())).toBe(expectedRealValues);

        // The lazy-fetch callback is part of the candles contract: activating the submode
        // with no data must ask for it exactly once, which is also what makes step 2 above
        // a faithful reproduction of the user's path into the bug.
        if (prop === 'pnlCandles') expect(onRequestPnlCandles).toHaveBeenCalled();
    });
});
