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
 *
 * THE REST OF THE FILE. Six smaller subjects share the same recorder: privacy masking
 * of the axis and tooltip formatters (S2a), the one form of every signed tooltip amount in
 * the locale's glyphs (D23, D23b), persistence of the mode and the P&L submode (S5), the
 * synthetic-candle caption (S9), the grid's left inset (developer review, 2026-09-29), and
 * the ladder x axis of the Candles and Income submodes (S7).
 * Each describe states its own reasons.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

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
const {chartInstances, echartsModule, fakeGeometry} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
        opts: unknown;
    }

    interface GridRect {
        x: number;
        y: number;
        width: number;
        height: number;
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
        /** Calls every handler registered with `on(event, …)`, as ECharts does when the user acts (S7). */
        emit: (event: string) => void;
        /** Puts a window in the chart's own state, where ECharts keeps it after a user zoom (S7). */
        setZoom: (start: number, end: number) => void;
        /** Present only while `fakeGeometry.measured` is on: the laid-out grid `syncPlotGeometry` reads. */
        getModel?: () => {getComponent: (type: string) => {coordinateSystem: {getRect: () => GridRect}} | undefined};
    }

    const chartInstances: FakeChart[] = [];

    /** Plot width reported to the resolution ladder. 40 daily buckets over 1200px is a
     *  density of 0.033 bucket/px, far under the 1.3 high-density threshold, so the
     *  chart stays at 'daily' and one bucket means one day — no aggregation tier in the
     *  middle of an assertion about aggregation inputs. */
    const PLOT_WIDTH_PX = 1200;

    /**
     * The laid-out grid, OPT-IN (S7). WHY: every other case keeps today's fake, with no `getModel`,
     * so `syncPlotGeometry` reads nothing, the plot width stays 0 and every rung of the ladder
     * stays offered. Off by default and reset after every case. On, the grid is a 527 px plot at
     * x 40 of the 1200 px chart: 40 px of room on the left, 633 on the right.
     */
    const fakeGeometry = {measured: false};
    const MEASURED_GRID: GridRect = {x: 40, y: 20, width: 527, height: 300};

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
            emit(event) {
                // A copy: a handler that unregisters itself must not make its neighbour skip.
                for (const handler of [...(handlers.get(event) ?? [])]) handler();
            },
            setZoom(start, end) {
                merged = {...merged, dataZoom: [{start, end}]};
            },
        };

        if (fakeGeometry.measured) {
            chart.getModel = () => ({getComponent: (type: string) => (type === 'grid' ? {coordinateSystem: {getRect: () => ({...MEASURED_GRID})}} : undefined)});
        }

        chartInstances.push(chart);
        return chart;
    }

    return {
        chartInstances,
        echartsModule: {init: (dom: unknown) => createFakeChart(dom)},
        fakeGeometry,
    };
});

vi.mock('echarts', () => echartsModule);

import {tick} from 'svelte';
import {get} from 'svelte/store';
import {addMessages, dictionary, waitLocale} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {OVERFLOW_MARQUEE_SELECTOR} from '$lib/actions/scrollOnOverflow';
import {_, locale} from '$lib/i18n';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import type {PortfolioAcquisitionFundingSeries, PortfolioBrokerPnlHistory, PortfolioCostHistorySeries, PortfolioDepositHistorySeries, PortfolioHistoryPoint, PortfolioIncomeHistorySeries, PortfolioPnlCandlePoint, PortfolioPnlCandleSeries} from '$lib/stores/portfolio/portfolioStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import GrowthChart from './GrowthChart.svelte';

/**
 * An in-memory `localStorage`, the same shape as ExposureTable.test.ts.
 *
 * Without it the persistence cases would prove nothing. Node 26 leaves the global unusable
 * unless the process runs with `--localstorage-file`, and `getUserStorage` swallows that and
 * returns the default. The component reads the keys at mount, not at import, so installing
 * the stub here, after the imports, is early enough.
 *
 * `storageWrites` is the call log. Part of the contract is WHEN a key is written (on a click,
 * never on mount), and the final content cannot show that.
 */
const storage = new Map<string, string>();
const storageWrites: Array<[key: string, value: string]> = [];
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => {
        storageWrites.push([key, value]);
        storage.set(key, value);
    },
    removeItem: (key: string) => void storage.delete(key),
});

/**
 * The two keys, written out as the literals that live in users' browsers.
 *
 * They are deliberately NOT rebuilt through `getUserStorageKey()`. Dashboard and Broker detail
 * share each key, and real browsers already hold values under it, so a rename would silently
 * drop every saved preference. A test that derived the key from the same code would follow the
 * rename and stay green. The scope is `anon` because jsdom has no logged-in user.
 */
const MODE_KEY = 'lf_anon_dashboard-growth-mode';
const SUBMODE_KEY = 'lf_anon_dashboard-growth-pnl-submode';

// =============================================================================
// Fixtures
// =============================================================================

const DAY_COUNT = 40;
/**
 * Days that one Income bar covers, and how many bars that leaves.
 *
 * The Income submode is driven by the candle-width ladder: a bar is a SUM over its
 * bucket, not one day. `1W` is the ladder's floor for Income — a single day of personal
 * cash flow is almost always empty — and it is what the component opens on here, because
 * jsdom reports no plot width so every rung stays offered and the lowest is taken.
 *
 * Derived rather than written down: hard-coding 6 would pin today's arithmetic and say
 * nothing about where it came from, so a change of floor would leave a number that is
 * wrong without being obviously wrong.
 */
const INCOME_BUCKET_DAYS = 7;
const INCOME_BUCKET_COUNT = Math.ceil(DAY_COUNT / INCOME_BUCKET_DAYS);

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

/** HISTORY with every return value removed, which the % toggle reads as "no % data". A new
 *  array is fine here, because no case that uses it depends on the memo's identity check. */
const NO_PCT_HISTORY: PortfolioHistoryPoint[] = HISTORY.map((point) => ({...point, twrr: null, mwrr_cumulative: null, roi: null}));

/** Passed explicitly as a prop: the currency code is a value this file supplies, not UI text. */
const BASE_CURRENCY = 'EUR';

/** Every data prop the candle-width ladder reads, for one period: the S7 cases mount them together. */
interface LadderFixture {
    history: PortfolioHistoryPoint[];
    pnlCandles: PortfolioPnlCandleSeries;
    incomeHistory: PortfolioIncomeHistorySeries;
    costHistory: PortfolioCostHistorySeries;
    depositHistory: PortfolioDepositHistorySeries;
    acquisitionFunding: PortfolioAcquisitionFundingSeries;
}

/** `count` consecutive ISO days from a UTC date: WHY, the S7 closings are counted by hand on this calendar. */
function isoDays(year: number, month0: number, day1: number, count: number): string[] {
    return Array.from({length: count}, (_day, index) => new Date(Date.UTC(year, month0, day1 + index)).toISOString().slice(0, 10));
}

/** The 40-day fixtures' per-day formulas over another calendar. WHY: every sum an S7 case expects stays derivable by hand from them. */
function buildLadderFixture(dates: string[]): LadderFixture {
    return {
        history: dates.map((date, index) => ({
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
        })),
        pnlCandles: {
            hypothetical: true,
            points: dates.map((date, index) => ({date, open: eur(500 + index * 100), high: eur(560 + index * 100), low: eur(480 + index * 100), close: eur(540 + index * 100)})),
        },
        incomeHistory: {points: dates.map((date, index) => ({date, dividend: eur(12 + index), interest: eur(3 + index)})), missing_fx_pairs: []},
        costHistory: {points: dates.map((date, index) => ({date, cost: eur(-(4 + index))})), missing_fx_pairs: []},
        depositHistory: {points: dates.map((date, index) => ({date, deposit: eur(150 + index)})), missing_fx_pairs: []},
        acquisitionFunding: {points: dates.map((date, index) => ({date, from_new_capital: eur(90 + index), from_reinvested: eur(45 + index)}))},
    };
}

/**
 * The S7 periods. Each is ONE shared instance, built once, for the reason the `HISTORY` docblock
 * gives: `GrowthChart` resets its caches and its window exactly when `history !== lastHistoryRef`,
 * so an accidental new array would be a trigger of its own.
 *
 * - 40 days (2026-01-01..02-09): the existing instances, reused as they are. 1W gives six buckets
 *   and, end-anchored, a short OLDEST one (Jan 1..5, 5 of 7 days).
 * - 730 days (2024-10-01..2026-09-30): long enough for a measured 527 px plot to drop the narrow
 *   rungs, and for the 1M window [19..24] and its 2W counterpart.
 * - 90 days (2026-01-01..03-31): three whole 30-day buckets at 1M, no partial bucket.
 * - 93 days (2026-01-01..04-03): four buckets at 1M, the oldest covering 3 of 30 days.
 */
const FIXTURE_40: LadderFixture = {history: HISTORY, pnlCandles: PNL_CANDLES, incomeHistory: INCOME_HISTORY, costHistory: COST_HISTORY, depositHistory: DEPOSIT_HISTORY, acquisitionFunding: ACQUISITION_FUNDING};
const FIXTURE_730 = buildLadderFixture(isoDays(2024, 9, 1, 730));
const FIXTURE_90 = buildLadderFixture(isoDays(2026, 0, 1, 90));
const FIXTURE_93 = buildLadderFixture(isoDays(2026, 0, 1, 93));

/** The props of one mount on `fixture`. WHY: the currency is a value this file supplies, never left to a default. */
const ladderProps = (fixture: LadderFixture) => ({...fixture, baseCurrency: BASE_CURRENCY});

/**
 * Three days for the privacy cases.
 *
 * Every amount has two decimals, and none of them could appear inside a date header
 * (`2026-01-01`), so the header can neither satisfy nor defeat a check that a formatted amount
 * is ABSENT. Day 0 is a gain and day 1 a loss, so the P&L-total row carries a sign on both
 * sides of zero. Day 0's NAV, 1234.56, needs both a grouping separator and two decimals. The
 * figures agree with each other (NAV = cash + market value, cash = the two pools,
 * P&L = NAV − baseline), so no amount looks like a special case.
 */
const MONEY_HISTORY: PortfolioHistoryPoint[] = [
    {date: DATES[0], cash_value: eur(358.02), market_value: eur(876.54), nav_value: eur(1_234.56), capital_baseline: eur(1_000.25), book_asset_like: eur(876.54), cash_from_contributed_capital: eur(210.87), cash_from_generated_returns: eur(147.15), total_pnl: eur(234.31)},
    {date: DATES[1], cash_value: eur(346.91), market_value: eur(1_998.76), nav_value: eur(2_345.67), capital_baseline: eur(3_702.91), book_asset_like: eur(1_998.76), cash_from_contributed_capital: eur(246.8), cash_from_generated_returns: eur(100.11), total_pnl: eur(-1_357.24)},
    {date: DATES[2], cash_value: eur(412.33), market_value: eur(2_087.45), nav_value: eur(2_499.78), capital_baseline: eur(3_702.91), book_asset_like: eur(2_087.45), cash_from_contributed_capital: eur(246.8), cash_from_generated_returns: eur(165.53), total_pnl: eur(-1_203.13)},
];

/**
 * Candles for the same three days. Day 1 opens and peaks above zero, then closes and bottoms
 * below it.
 *
 * Day 0 opens at `-0.00`. That is a real serialisation: a Decimal that rounds a tiny loss to
 * zero keeps its sign. It is written as a literal because `eur(-0)` would print `'0.00'`
 * (`toFixed` drops the sign of a negative zero).
 */
const MONEY_CANDLES: PortfolioPnlCandleSeries = {
    hypothetical: true,
    points: [
        {date: DATES[0], open: {code: 'EUR', amount: '-0.00'}, high: eur(250.75), low: eur(-10.5), close: eur(234.31)},
        {date: DATES[1], open: eur(123.45), high: eur(234.56), low: eur(-98.76), close: eur(-12.34)},
        {date: DATES[2], open: eur(-12.34), high: eur(60.02), low: eur(-20.48), close: eur(56.78)},
    ],
};

/** One broker point per day, point `i` on day `i`, so a tooltip reads a broker by the day's index. */
const brokerPoints = (totals: Array<{code: string; amount: string}>) => totals.map((total_pnl, index) => ({date: DATES[index], total_pnl}));

/**
 * Two brokers under the same three days: the overlay needs at least two. Their P&L adds up to the
 * portfolio's on every day, and between them they carry every sign a signed row can print. Broker A
 * gains on days 0 and 2 and sits at `-0.00` on day 1, the same real serialisation as the candle's
 * open. Broker B loses on every day.
 */
const MONEY_BROKER_PNL: PortfolioBrokerPnlHistory[] = [
    {broker_id: 11, broker_name: 'Money Broker A', points: brokerPoints([eur(312.5), {code: 'EUR', amount: '-0.00'}, eur(45.67)])},
    {broker_id: 12, broker_name: 'Money Broker B', points: brokerPoints([eur(-78.19), eur(-1_357.24), eur(-1_248.8)])},
];

/** Their names, in overlay order: values this file supplies, not UI text. */
const MONEY_BROKER_NAMES = MONEY_BROKER_PNL.map((broker) => broker.broker_name);

/**
 * The Income submode's flows over the same three days. Its floor is a week, so the three days are
 * ONE bar, and every row it prints is a sum.
 *
 * Between them the rows print every outcome of a signed amount: gains (dividend, deposit, new
 * capital), a loss (a fee on day 1), an exact zero (nothing reinvested, printed because new capital
 * was), and a zero that exists only after rounding. Interest is 0.10 + 0.20 − 0.30, which binary
 * floating point sums to 5.55e-17, not 0: a sign decided on the raw value would print it `+0.00`.
 */
const MONEY_INCOME: PortfolioIncomeHistorySeries = {
    points: [
        {date: DATES[0], dividend: eur(12.34), interest: eur(0.1)},
        {date: DATES[1], dividend: eur(0), interest: eur(0.2)},
        {date: DATES[2], dividend: eur(5), interest: eur(-0.3)},
    ],
    missing_fx_pairs: [],
};
const MONEY_COSTS: PortfolioCostHistorySeries = {points: [{date: DATES[1], cost: eur(-4.56)}], missing_fx_pairs: []};
const MONEY_DEPOSITS: PortfolioDepositHistorySeries = {points: [{date: DATES[2], deposit: eur(150)}], missing_fx_pairs: []};
const MONEY_ACQUISITION: PortfolioAcquisitionFundingSeries = {points: [{date: DATES[0], from_new_capital: eur(90), from_reinvested: eur(0)}]};

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

/**
 * The number a line/bar datum carries. On the time axis a datum is a `SeriesPoint`,
 * `{value: [date, number | null], …}`. WHY widened (S7): on the ladder's category axis it may be
 * a plain number, `[date, n]` or `{value: n, …}`, and the cases read the value, not the shape, so
 * one reader serves the code before and after the fix.
 */
function pointValue(datum: unknown): number | null {
    if (typeof datum === 'number') return datum;
    if (Array.isArray(datum)) return datum.length === 2 ? ((datum[1] as number | null) ?? null) : null;
    if (datum == null || typeof datum !== 'object') return null;
    const value = (datum as {value?: unknown}).value;
    if (typeof value === 'number') return value;
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

/**
 * A candle's `[open, close, low, high]` quad, or null. WHY: today a candle is a flat quad; the S7
 * fix may wrap it as `{value: quad, itemStyle}` to mark a partial bucket, and the cases read the
 * quad, not the wrapper.
 */
function quadOf(datum: unknown): number[] | null {
    const raw = Array.isArray(datum) ? datum : datum != null && typeof datum === 'object' ? (datum as {value?: unknown}).value : undefined;
    return Array.isArray(raw) && raw.length === 4 && raw.every((component) => typeof component === 'number' && Number.isFinite(component)) ? (raw as number[]) : null;
}

/** A candlestick datum is either a real `[open, close, low, high]` quad (flat, or wrapped in
 *  `{value}`) or ECharts' `'-'` empty-value sentinel, which is exactly what the stale entry was
 *  full of. */
function realCandleQuads(series: SeriesUpdate | undefined): number {
    return (series?.data ?? []).filter((datum) => quadOf(datum) != null).length;
}

function brokerSeries(series: SeriesUpdate[]): SeriesUpdate[] {
    return series.filter((entry) => (BROKER_NAMES as readonly string[]).includes(entry.name));
}

// =============================================================================
// Reading the full option: the formatters, and what they print
// =============================================================================

type AxisFormatter = (value: number) => string;
type TooltipFormatter = (params: Array<{dataIndex: number}>) => string;

/** The part of a full rebuild that the privacy, persistence and caption cases read. */
interface FullOption {
    yAxis: {axisLabel: {formatter: AxisFormatter}};
    tooltip: {formatter: TooltipFormatter};
    series: Array<{type?: string; name?: string}>;
}

/**
 * The full rebuilds recorded from call `since` onwards.
 *
 * `applyFullOption` issues the only `setOption` that carries both `yAxis` and `tooltip`. The
 * partial data update sends `{name, data}` series, and the resize path sends `xAxis` alone.
 * The full rebuild is also where the formatters live. Read them from the call log, never from
 * `getOption()`: the fake merges shallowly, so the merged view cannot tell which call installed
 * what.
 */
function fullOptionsSince(since: number): FullOption[] {
    expect(chartInstances).toHaveLength(1);
    return chartInstances[0].setOptionCalls
        .slice(since)
        .map((call) => call.option)
        .filter((option) => option.yAxis != null && option.tooltip != null) as unknown as FullOption[];
}

function latestFullOption(): FullOption {
    const options = fullOptionsSince(0);
    if (options.length === 0) throw new Error('GrowthChart never handed a full option to ECharts');
    return options[options.length - 1];
}

function seriesTypes(option: FullOption): Array<string | undefined> {
    return option.series.map((entry) => entry.type);
}

/**
 * What each view draws on a full rebuild, listed by series type. The shape tells the views
 * apart without reading a translated series name. The P&L line here is its three fixed slots,
 * with no broker overlay; with one, wait through `waitForPnlLineWithBrokers` instead.
 */
const FRAME = {
    abs: ['line', 'line', 'line', 'line', 'line'],
    pnlLine: ['line', 'line', 'line'],
    candles: ['candlestick'],
    income: ['bar', 'bar', 'bar', 'bar', 'bar', 'bar'],
};

/** Waits until the latest full rebuild draws `frame`, and returns it. */
async function waitForFrame(frame: string[]): Promise<FullOption> {
    await waitFor(() => expect(seriesTypes(latestFullOption())).toEqual(frame), {timeout: 5_000});
    return latestFullOption();
}

/** Waits for a full rebuild recorded after call `since`, and returns the latest one. */
async function fullOptionAfter(since: number): Promise<FullOption> {
    await waitFor(() => expect(fullOptionsSince(since).length).toBeGreaterThan(0), {timeout: 5_000});
    const options = fullOptionsSince(since);
    return options[options.length - 1];
}

/**
 * Waits for the P&L line with its broker overlay, and returns it.
 *
 * The overlay appends one line per broker after the three fixed slots, so two brokers make five
 * lines: the Abs frame too. The broker names, which this file supplies, tell the two apart.
 */
async function waitForPnlLineWithBrokers(names: readonly string[]): Promise<FullOption> {
    const frame = [...FRAME.pnlLine, ...names.map(() => 'line')];
    await waitFor(
        () => {
            const option = latestFullOption();
            expect(seriesTypes(option)).toEqual(frame);
            expect(option.series.slice(FRAME.pnlLine.length).map((entry) => entry.name)).toEqual(names);
        },
        {timeout: 5_000},
    );
    return latestFullOption();
}

interface AmountFormat {
    /** As `fmtCurrency(v, true)`: `+` on a gain, and no sign on anything that rounds to zero. */
    signed?: boolean;
    /** A forced locale. `undefined` is this machine's, as it is for the component. */
    locale?: string;
}

/**
 * The tooltip's number format, produced by the same call `fmtCurrency` makes. The expected string
 * therefore follows the locale instead of hard-coding one, sign included: the sign is whatever
 * that locale writes. A negative zero prints as zero, which is the contract, not a detail of the
 * call.
 */
const formatAmount = (value: number, {signed = false, locale}: AmountFormat = {}) => (value === 0 ? 0 : value).toLocaleString(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: signed ? 'exceptZero' : 'auto'});

/** A sign at the start of a formatted number, bidi marks included: the part `maskFormattedNumber` keeps outside the mask. */
const LEADING_SIGN = /^[\p{Cf}+\-\u2212]*/u;
const leadingSign = (formatted: string) => LEADING_SIGN.exec(formatted)?.[0] ?? '';

/** What one tooltip amount prints: the currency, then the number. With privacy on only the digits
 *  go; the currency and the sign stay readable (D8). */
function expectedAmount(value: number, {masked = false, ...format}: AmountFormat & {masked?: boolean} = {}): string {
    const formatted = formatAmount(value, format);
    return `${BASE_CURRENCY} ${masked ? `${leadingSign(formatted)}${PRIVACY_PLACEHOLDER}` : formatted}`;
}

/** A locale whose minus is U+2212 MINUS SIGN, where Node's default locale writes a hyphen. */
const SWEDISH = 'sv-SE';

/**
 * Runs `read` with every `Number.prototype.toLocaleString` call forced to `locale`, the
 * component's own included. `undefined` leaves this machine's locale in place.
 *
 * Synchronous on purpose: the spy comes off before anything else runs, so nothing outside `read`
 * ever formats a number in the forced locale.
 */
function inLocale<T>(locale: string | undefined, read: () => T): T {
    if (locale === undefined) return read();
    const original = Number.prototype.toLocaleString;
    const spy = vi.spyOn(Number.prototype, 'toLocaleString').mockImplementation(function (this: number, _locales?: unknown, options?: Intl.NumberFormatOptions) {
        return original.call(this, locale, options);
    });
    try {
        return read();
    } finally {
        spy.mockRestore();
    }
}

interface TooltipRow {
    label: string;
    value: string;
}

/** Text as a user reads it from HTML the component builds with raw `$_()` output (row labels, headers):
 *  an expected label goes through the same parser as the tooltip it is compared with. A translation the
 *  component escapes, such as the partial-bucket line, reads as written instead. */
function htmlText(html: string): string {
    const host = document.createElement('div');
    host.innerHTML = html;
    return host.textContent ?? '';
}

/**
 * The label/value rows of a tooltip, as elements.
 *
 * Every amount row GrowthChart emits has the shape `<div><span>label</span><b>value</b></div>`,
 * whether it comes from `buildTooltipRow` or from the inline P&L rows. The header, the formula
 * hint and the dividers do not have that shape. Parsing rows instead of matching substrings
 * stops a check on one row from being satisfied by another.
 */
function tooltipRowElements(html: string): Array<{label: Element; value: HTMLElement}> {
    const host = document.createElement('div');
    host.innerHTML = html;
    return Array.from(host.children).flatMap((row) => {
        const [label, value] = Array.from(row.children);
        return row.children.length === 2 && label.tagName === 'SPAN' && value instanceof HTMLElement && value.tagName === 'B' ? [{label, value}] : [];
    });
}

/** The label/value rows of a tooltip, as the user reads them. */
function tooltipRows(html: string): TooltipRow[] {
    return tooltipRowElements(html).map(({label, value}) => ({label: label.textContent ?? '', value: value.textContent ?? ''}));
}

/** The value of the one row labelled by `labelKey`, with the label resolved through i18n as the component resolves it. */
function rowValue(rows: TooltipRow[], labelKey: string): string {
    const label = htmlText(get(_)(labelKey));
    const matching = rows.filter((row) => row.label === label);
    expect(matching, `exactly one tooltip row labelled ${labelKey}`).toHaveLength(1);
    return matching[0].value;
}

/** The Abs tooltip rows that print a bare amount, by label key. The P&L-total row also
 *  carries a sign, so it is checked separately. */
const ABS_PLAIN_ROWS = ['dashboard.navValue', 'dashboard.capitalBaselineTooltip', 'dashboard.assetsAtCostTooltip', 'dashboard.cashFromGeneratedReturns', 'dashboard.cashFromContributedCapital'];

/** Every amount the Abs tooltip prints for a day, parsed as the component parses it. */
const absAmounts = (point: PortfolioHistoryPoint) => [point.nav_value, point.capital_baseline, point.total_pnl, point.book_asset_like, point.cash_from_generated_returns, point.cash_from_contributed_capital].map((money) => Number(money.amount));

/** Every amount the candle tooltip prints for a bucket. */
const candleAmounts = (point: PortfolioPnlCandlePoint) => [point.open, point.close, point.high, point.low].map((money) => Number(money.amount));

const MODE_TOGGLES = ['growth-toggle-eur', 'growth-toggle-pct', 'growth-toggle-pnl'];
const SUBMODE_TOGGLES = ['growth-pnl-submode-line', 'growth-pnl-submode-candles', 'growth-pnl-submode-income'];

/** Which buttons of a segmented toggle are pressed. Read from `aria-pressed` (the state a
 *  screen reader announces), never from the active colour class. Returning a list instead of
 *  a boolean makes "exactly this one" a single assertion. */
function pressedAmong(testIds: string[]): string[] {
    return testIds.filter((id) => screen.getByTestId(id).getAttribute('aria-pressed') === 'true');
}

/** The writes made to the two persisted keys, in order. */
function persistedWrites(): Array<[string, string]> {
    return storageWrites.filter(([key]) => key === MODE_KEY || key === SUBMODE_KEY);
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
        // Two series (dividend, interest), each one bar per bucket.
        expectedRealValues: 2 * INCOME_BUCKET_COUNT,
        // Slots 0 and 1 of the income submode's fixed 6-slot order: dividend, interest.
        countRealValues: (series) => nonZeroPoints(series[0]) + nonZeroPoints(series[1]),
    },
    {
        prop: 'costHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {costHistory: COST_HISTORY},
        expectedRealValues: INCOME_BUCKET_COUNT,
        // Slot 2: costs (FEE+TAX, signed negative).
        countRealValues: (series) => nonZeroPoints(series[2]),
    },
    {
        prop: 'depositHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {depositHistory: DEPOSIT_HISTORY},
        expectedRealValues: INCOME_BUCKET_COUNT,
        // Slot 3: deposit size.
        countRealValues: (series) => nonZeroPoints(series[3]),
    },
    {
        prop: 'acquisitionFunding',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {acquisitionFunding: ACQUISITION_FUNDING},
        // Two series (new capital, reinvested), each one bar per bucket.
        expectedRealValues: 2 * INCOME_BUCKET_COUNT,
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
    // Every mount starts from the defaults by construction. The memo cases click the toggles
    // too, and every click is now a real write.
    storage.clear();
    storageWrites.length = 0;
});

afterEach(() => {
    // WHY: the measured grid is opt-in per case (S7), and a case that installed fake timers and
    // failed before its own `finally` must not hand them to the next one.
    fakeGeometry.measured = false;
    vi.useRealTimers();
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

// =============================================================================
// S2a — privacy masking of the axis and tooltip formatters
// =============================================================================

/**
 * The formatters are closures inside the option builder. The only way to reach them is
 * through the option GrowthChart hands to ECharts, and that is also exactly what ECharts calls
 * when it paints an axis label or a tooltip.
 *
 * They read the privacy flag when CALLED, not when built. So "this formatter masks" does not
 * show that the chart redraws on a toggle. The toggle case checks instead that a NEW full
 * option arrives, because ECharts only re-runs a formatter when it is handed an option.
 */
describe('GrowthChart privacy masking (S2a)', () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case.
    afterEach(() => setPrivacyEnabled(false));

    const MASKED_AMOUNT = `${BASE_CURRENCY} ${PRIVACY_PLACEHOLDER}`;
    /** A masked loss on an unsigned row: the currency, the locale's minus, the mask. The minus
     *  comes from the same call the component makes, never from a literal (D23). */
    const MASKED_NEGATIVE = expectedAmount(-1, {masked: true});

    /** What every money axis label must print with privacy on. */
    function expectMaskedMoneyAxis(format: AxisFormatter) {
        expect(format(20_000)).toBe(PRIVACY_PLACEHOLDER);
        expect(format(-5_000)).toBe(`-${PRIVACY_PLACEHOLDER}`);
        expect(format(0)).toBe(PRIVACY_PLACEHOLDER);
        // The property itself, whatever the placeholder looks like: no digit and no k/M
        // suffix, because `•••k` would still reveal the order of magnitude (D8).
        for (const value of [20_000, -5_000, 0]) expect(format(value)).not.toMatch(/[0-9kM]/);
    }

    it('masks the money axis labels in Abs and P&L line: no digit, no k/M suffix, the minus kept outside', async () => {
        // WHY: with privacy on, the axis ticks are the one place a masked chart would still
        // print the scale of the portfolio (20k, 1.3M). Catches `maskable` being dropped
        // from the compact label, or the suffix moving outside it (`maskable(n) + 'k'`).
        setPrivacyEnabled(true);
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});

        const absOption = await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        expectMaskedMoneyAxis(absOption.yAxis.axisLabel.formatter);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        const pnlOption = await waitForFrame(FRAME.pnlLine);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pnl']);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        expectMaskedMoneyAxis(pnlOption.yAxis.axisLabel.formatter);
    });

    it('leaves the % axis labels readable: a return is not an amount', async () => {
        // WHY: over-masking is also a defect. A masked return axis would make the % view
        // useless under privacy without hiding anything personal. Catches `maskable`
        // wrapped around the % branch of the axis formatter.
        setPrivacyEnabled(true);
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});

        // Barrier: privacy really is on in this render, because the money axis is masked.
        const absOption = await waitForFrame(FRAME.abs);
        expect(absOption.yAxis.axisLabel.formatter(20_000)).toBe(PRIVACY_PLACEHOLDER);

        // Precondition: HISTORY carries return series, so the % view can be reached.
        expect(getByTestId('growth-toggle-pct')).toBeEnabled();
        const before = setOptionCount();
        await fireEvent.click(getByTestId('growth-toggle-pct'));
        const pctOption = await fullOptionAfter(before);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pct']);

        // `toFixed`, not `toLocaleString`: the % label does not depend on the locale, so a
        // literal is the honest expectation.
        expect(pctOption.yAxis.axisLabel.formatter(12.3)).toBe('12.3%');
    });

    it('masks every tooltip amount in the Abs, P&L-total and candle rows, keeping the currency and the sign readable', async () => {
        // WHY: the tooltip is where the exact figures are shown. Catches `maskable` dropped
        // from `fmtCurrency`, and any row that formats an amount by another route. The
        // P&L-total row builds its own markup around `fmtCurrency`, which is why it is
        // checked on its own. Decision D8 keeps the sign outside the mask, so the sign is
        // asserted here, not merely tolerated: a mask that swallowed it fails here.
        setPrivacyEnabled(true);
        const {getByTestId} = render(GrowthChart, {props: {history: MONEY_HISTORY, pnlCandles: MONEY_CANDLES, baseCurrency: BASE_CURRENCY}});

        const absOption = await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        // Day 0 is a gain and day 1 a loss. The P&L-total row prints the currency, then the sign,
        // then the mask: `EUR +•••` and `EUR -•••` (D23b). The minus is the locale's (D23), so the
        // sign is taken from the same call the component makes: a literal would pin one locale's
        // glyph. A sign printed before the currency, the old `+EUR •••`, fails here.
        for (const index of [0, 1]) {
            const sign = leadingSign(formatAmount(Number(MONEY_HISTORY[index].total_pnl.amount), {signed: true}));
            // Precondition: the day carries a sign, so the check below is about one.
            expect(sign, `day ${index} is a gain or a loss`).not.toBe('');
            const html = absOption.tooltip.formatter([{dataIndex: index}]);
            const rows = tooltipRows(html);
            expect(rowValue(rows, 'dashboard.totalPnl')).toBe(`${BASE_CURRENCY} ${sign}${PRIVACY_PLACEHOLDER}`);
            for (const key of ABS_PLAIN_ROWS) expect(rowValue(rows, key), key).toBe(MASKED_AMOUNT);
            // The check cannot be "no digit at all": the date header legitimately has digits.
            for (const amount of absAmounts(MONEY_HISTORY[index])) expect(html).not.toContain(formatAmount(Math.abs(amount)));
        }

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        const candleOption = await waitForFrame(FRAME.candles);
        const html = candleOption.tooltip.formatter([{dataIndex: 1}]);
        const rows = tooltipRows(html);
        // Precondition: the locale writes a sign on a loss, so a masked loss is not a masked gain.
        expect(MASKED_NEGATIVE).not.toBe(MASKED_AMOUNT);
        expect(rowValue(rows, 'dataEditor.col.open')).toBe(MASKED_AMOUNT);
        expect(rowValue(rows, 'dataEditor.col.high')).toBe(MASKED_AMOUNT);
        expect(rowValue(rows, 'dataEditor.col.close')).toBe(MASKED_NEGATIVE);
        expect(rowValue(rows, 'dataEditor.col.low')).toBe(MASKED_NEGATIVE);
        for (const amount of candleAmounts(MONEY_CANDLES.points[1])) expect(html).not.toContain(formatAmount(Math.abs(amount)));
    });

    it('with privacy off, prints the amounts as before: compact axis, locale tooltip, no minus on a negative zero', async () => {
        // WHY: masking must be a pure overlay. With the flag off, not one character of
        // today's output may change. Catches a masking change that leaks into the OFF path:
        // a different sign test (`Object.is(v, -0)`, `1 / v < 0`) that prints `-0`, a changed
        // compaction step, or changed `toLocaleString` options. The signed P&L total is pinned
        // in its one form, `EUR +234.31` / `EUR -1,357.24` (D23b), so a sign written by hand
        // again in front of the currency (`+EUR 234.31`) fails here too.
        expect(isPrivacyEnabled()).toBe(false);
        // Precondition: the fixture really carries a negative zero, as the component parses it.
        expect(Object.is(Number(MONEY_CANDLES.points[0].open.amount), -0)).toBe(true);

        const {getByTestId} = render(GrowthChart, {props: {history: MONEY_HISTORY, pnlCandles: MONEY_CANDLES, baseCurrency: BASE_CURRENCY}});
        const absOption = await waitForFrame(FRAME.abs);

        // The axis labels use `toFixed`, not `toLocaleString`, so literals are the honest
        // expectation here.
        const axis = absOption.yAxis.axisLabel.formatter;
        expect([-5_000, 1_300_000, 0, -0].map((value) => axis(value))).toEqual(['-5k', '1.3M', '0', '0']);

        const absRows = tooltipRows(absOption.tooltip.formatter([{dataIndex: 0}]));
        expect(rowValue(absRows, 'dashboard.navValue')).toBe(`${BASE_CURRENCY} ${formatAmount(1_234.56)}`);
        // Day 0 is a gain and day 1 a loss: the P&L total is the currency, then the sign the
        // locale writes, then the digits.
        for (const index of [0, 1]) {
            const pnl = Number(MONEY_HISTORY[index].total_pnl.amount);
            // Precondition: the day carries a sign, so the check below is about one.
            expect(leadingSign(formatAmount(pnl, {signed: true})), `day ${index} is a gain or a loss`).not.toBe('');
            const rows = tooltipRows(absOption.tooltip.formatter([{dataIndex: index}]));
            expect(rowValue(rows, 'dashboard.totalPnl'), `day ${index}`).toBe(expectedAmount(pnl, {signed: true}));
        }

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        const candleOption = await waitForFrame(FRAME.candles);
        const candleRows = tooltipRows(candleOption.tooltip.formatter([{dataIndex: 0}]));
        expect(rowValue(candleRows, 'dataEditor.col.open')).toBe(`${BASE_CURRENCY} ${formatAmount(0)}`);
        // The OHLC rows are unsigned: a loss carries the locale's minus after the currency, a
        // gain carries no `+`.
        const dayOne = tooltipRows(candleOption.tooltip.formatter([{dataIndex: 1}]));
        expect(rowValue(dayOne, 'dataEditor.col.close')).toBe(expectedAmount(Number(MONEY_CANDLES.points[1].close.amount)));
        expect(rowValue(dayOne, 'dataEditor.col.open')).toBe(expectedAmount(Number(MONEY_CANDLES.points[1].open.amount)));
    });

    it('redraws with a new full option when privacy is toggled, in both directions', async () => {
        // WHY: ECharts runs a formatter only while painting, and paints only when it is
        // handed an option. A formatter that reads the flag live is not enough on its own:
        // the labels on screen would stay as they were. Catches the render effect losing its
        // dependency on the flag, or the full-rebuild condition losing its `masked` term. In
        // that case the redraw would be a partial update, which carries no formatter at all.
        render(GrowthChart, {props: {history: HISTORY}});
        const clear = await waitForFrame(FRAME.abs);
        expect(clear.yAxis.axisLabel.formatter(20_000)).toBe('20k');

        const beforeOn = setOptionCount();
        setPrivacyEnabled(true);
        const masked = await fullOptionAfter(beforeOn);
        expect(masked.yAxis.axisLabel.formatter(20_000)).toBe(PRIVACY_PLACEHOLDER);

        const beforeOff = setOptionCount();
        setPrivacyEnabled(false);
        const unmasked = await fullOptionAfter(beforeOff);
        expect(unmasked.yAxis.axisLabel.formatter(20_000)).toBe('20k');
    });
});

// =============================================================================
// D23, D23b — one form for every signed tooltip amount, in the locale's glyphs
// =============================================================================

/**
 * Every signed tooltip amount has ONE form: the currency, then the sign, then the digits, with
 * the sign coming out of the same Intl call as the digits (D23b). `EUR +234.31`,
 * `EUR -1,357.24`, and `EUR 0.00` for anything that prints as zero, a negative zero or a float
 * residue included. With privacy on only the digits go: `EUR +•••`, `EUR -•••`, `EUR •••` (D8).
 *
 * Four row families print a signed amount, each with its own markup: the Abs P&L total, the
 * P&L line (the total and one row per broker), the broker rows under a candle, and every row of
 * the Income submode. The OHLC rows under a candle print the same kind of amount unsigned. Each
 * case walks all of them on one mount, so a family that builds its sign by another route cannot
 * hide behind one that does not.
 *
 * The minus is the locale's (D23). In Node's default locale it is a hyphen, the very character a
 * hand-written sign would use, so on this machine alone a hard-coded `-` would pass unseen. The
 * Swedish cases force the one call `fmtCurrency` makes, `Number.prototype.toLocaleString`, to a
 * locale whose minus is U+2212, and pin that glyph as a literal: the glyph is the subject of
 * D23, not a translated text.
 */
describe('GrowthChart signed tooltip amounts (D23, D23b)', () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case.
    afterEach(() => setPrivacyEnabled(false));

    /** One amount row a tooltip must print. */
    interface AmountRow {
        /** The label as the user reads it: an i18n label resolved as the component resolves it, or a broker name. */
        label: string;
        amount: number;
        /** Printed through `fmtCurrency(v, true)`: `+` on a gain, no sign on a zero. */
        signed: boolean;
    }

    interface View {
        title: string;
        /** The forced locale. None keeps this machine's. */
        locale?: string;
        /** The minus that locale writes, as a literal, when the case pins the glyph. */
        minus?: string;
        masked: boolean;
    }

    const VIEWS: View[] = [
        {title: 'host locale, in the clear', masked: false},
        {title: 'host locale, masked', masked: true},
        {title: 'sv-SE (U+2212), in the clear', locale: SWEDISH, minus: '\u2212', masked: false},
        {title: 'sv-SE (U+2212), masked', locale: SWEDISH, minus: '\u2212', masked: true},
    ];

    const labelOf = (key: string) => htmlText(get(_)(key));
    const money = (field: {amount: string}) => Number(field.amount);
    /** Whether an amount prints as zero at two decimals, whatever its sign. A signed row prints it with no sign. */
    const printsAsZero = (amount: number) => formatAmount(Math.abs(amount)) === formatAmount(0);

    /** One Income bar: a sparse daily series summed over the three days in date order, as the component folds it. */
    function barSum<P extends {date: string}>(points: P[], read: (point: P) => {amount: string}): number {
        return MONEY_HISTORY.reduce((sum, {date}) => {
            const point = points.find((entry) => entry.date === date);
            return sum + (point ? money(read(point)) : 0);
        }, 0);
    }

    /**
     * Precondition of the Income checks, measured on the sum the component drew: the interest bar
     * is not zero, yet it prints as zero. It is the row that a sign or a colour decided on the raw
     * value, instead of on what the row prints, would treat as a gain.
     */
    function expectDrawnInterestResidue(): void {
        const interestBars = renderedSeries().filter((series) => series.name === get(_)('transactions.types.INTEREST'));
        expect(interestBars, 'one interest series').toHaveLength(1);
        expect(interestBars[0].data, 'the three days are one Income bar').toHaveLength(1);
        const interest = pointValue(interestBars[0].data[0]);
        if (interest == null) throw new Error('the interest bar carries no value');
        expect(interest, 'the drawn interest is a float residue, not an exact zero').not.toBe(0);
        expect(printsAsZero(interest), `interest ${interest} prints as zero`).toBe(true);
    }

    /** The Abs tooltip of one day: the signed P&L total among five unsigned amounts. */
    const absRows = (point: PortfolioHistoryPoint): AmountRow[] => [
        {label: labelOf('dashboard.navValue'), amount: money(point.nav_value), signed: false},
        {label: labelOf('dashboard.capitalBaselineTooltip'), amount: money(point.capital_baseline), signed: false},
        {label: labelOf('dashboard.totalPnl'), amount: money(point.total_pnl), signed: true},
        {label: labelOf('dashboard.assetsAtCostTooltip'), amount: money(point.book_asset_like), signed: false},
        {label: labelOf('dashboard.cashFromGeneratedReturns'), amount: money(point.cash_from_generated_returns), signed: false},
        {label: labelOf('dashboard.cashFromContributedCapital'), amount: money(point.cash_from_contributed_capital), signed: false},
    ];

    /** The broker rows of one day: signed, each labelled by its broker's name. */
    const brokerRows = (index: number): AmountRow[] => MONEY_BROKER_PNL.map((broker) => ({label: broker.broker_name, amount: money(broker.points[index].total_pnl), signed: true}));

    /** The P&L line tooltip of one day: the total, then the brokers. */
    const pnlLineRows = (index: number): AmountRow[] => [{label: labelOf('dashboard.totalPnl'), amount: money(MONEY_HISTORY[index].total_pnl), signed: true}, ...brokerRows(index)];

    /** The candle tooltip of one day: open, close, high and low unsigned, then the brokers signed. */
    function candleRows(index: number): AmountRow[] {
        const candle = MONEY_CANDLES.points[index];
        return [
            {label: labelOf('dataEditor.col.open'), amount: money(candle.open), signed: false},
            {label: labelOf('dataEditor.col.close'), amount: money(candle.close), signed: false},
            {label: labelOf('dataEditor.col.high'), amount: money(candle.high), signed: false},
            {label: labelOf('dataEditor.col.low'), amount: money(candle.low), signed: false},
            ...brokerRows(index),
        ];
    }

    /** The Income tooltip of the one bar, every row signed. The fixtures give costs and deposit a
     *  value, and new capital one, which is what brings in both acquisition rows. */
    function incomeRows(): AmountRow[] {
        const dividend = barSum(MONEY_INCOME.points, (point) => point.dividend);
        const interest = barSum(MONEY_INCOME.points, (point) => point.interest);
        return [
            {label: labelOf('transactions.types.DIVIDEND'), amount: dividend, signed: true},
            {label: labelOf('transactions.types.INTEREST'), amount: interest, signed: true},
            {label: labelOf('assets.distribution.total'), amount: dividend + interest, signed: true},
            {label: labelOf('dashboard.feesAndTaxes'), amount: barSum(MONEY_COSTS.points, (point) => point.cost), signed: true},
            {label: labelOf('transactions.types.DEPOSIT'), amount: barSum(MONEY_DEPOSITS.points, (point) => point.deposit), signed: true},
            {label: labelOf('dashboard.pnlAcqNewCapital'), amount: barSum(MONEY_ACQUISITION.points, (point) => point.from_new_capital), signed: true},
            {label: labelOf('dashboard.pnlAcqReinvested'), amount: barSum(MONEY_ACQUISITION.points, (point) => point.from_reinvested), signed: true},
        ];
    }

    /**
     * Checks one tooltip against the rows it must print, and nothing else.
     *
     * The rows are compared whole, label and value, with values derived from the same call the
     * component makes. Then the sign is checked as characters: none on a zero, `+` only on a
     * signed gain, and the literal minus where the case pins one. That second half does not go
     * through the helper that builds the expectation, so a defect shared by the helper and the
     * component cannot hide there.
     */
    function expectTooltip(html: string, rows: AmountRow[], view: View, where: string) {
        const printed = tooltipRows(html);
        const wanted = rows.map((row) => ({label: row.label, value: expectedAmount(row.amount, {signed: row.signed, locale: view.locale, masked: view.masked})}));
        expect(printed, where).toEqual(expect.arrayContaining(wanted));
        expect(printed, `${where}: no row beyond these`).toHaveLength(wanted.length);

        const minus = view.minus ?? leadingSign(formatAmount(-1, {locale: view.locale}));
        for (const row of rows) {
            const value = printed.find((entry) => entry.label === row.label)?.value ?? '';
            const what = `${where}, ${row.label}`;
            if (printsAsZero(row.amount)) {
                expect(value, `${what}: a zero carries no sign`).toBe(`${BASE_CURRENCY} ${view.masked ? PRIVACY_PLACEHOLDER : formatAmount(0, {locale: view.locale})}`);
                continue;
            }
            const head = `${BASE_CURRENCY} ${row.amount < 0 ? minus : row.signed ? '+' : ''}`;
            if (view.masked) {
                expect(value, `${what}: the currency, the sign, the mask`).toBe(`${head}${PRIVACY_PLACEHOLDER}`);
                expect(html, `${what}: no digits under the mask`).not.toContain(formatAmount(Math.abs(row.amount), {locale: view.locale}));
            } else {
                expect(value.slice(0, head.length), `${what}: the currency, then the sign`).toBe(head);
                expect(value.slice(head.length), `${what}: the digits right after the sign`).toMatch(/^\d/);
            }
        }
    }

    it.each(VIEWS)('prints every signed row as currency, sign, digits, and every OHLC row unsigned: $title', async (view) => {
        // WHY: D23b gives the four signed families one form, and D23 gives the sign to the
        // locale. Catches, family by family: the sign moved back in front of the currency; a
        // hand-written ASCII `-` (the Swedish cases) or a hard-coded U+2212 (this machine's) in
        // place of the locale's minus; a `+` or `-` on a zero, whether a negative zero or a
        // float residue whose sign was decided before rounding; `-0.00` on an unsigned row; a
        // signed row printed unsigned, or an OHLC row printed signed; and, masked, a mask that
        // swallows the sign or the currency.
        if (view.minus !== undefined) {
            // Precondition: this Node has the forced locale's data and writes its minus. Without
            // it the locale would fall back in silence and the glyph checks would prove nothing.
            expect(leadingSign(formatAmount(-1, {locale: view.locale})), `${view.locale} writes its own minus`).toBe(view.minus);
        }
        setPrivacyEnabled(view.masked);
        const {getByTestId} = render(GrowthChart, {
            props: {history: MONEY_HISTORY, brokerPnlHistory: MONEY_BROKER_PNL, pnlCandles: MONEY_CANDLES, incomeHistory: MONEY_INCOME, costHistory: MONEY_COSTS, depositHistory: MONEY_DEPOSITS, acquisitionFunding: MONEY_ACQUISITION, baseCurrency: BASE_CURRENCY},
        });

        const walked: AmountRow[] = [];
        /** Reads the tooltip of one bucket in the case's locale, and checks it against `rows`. */
        const expectBucket = (option: FullOption, dataIndex: number, rows: AmountRow[], where: string) => {
            expectTooltip(
                inLocale(view.locale, () => option.tooltip.formatter([{dataIndex}])),
                rows,
                view,
                where,
            );
            walked.push(...rows);
        };

        // (a) Abs: the P&L total, one bucket per day.
        const absOption = await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        MONEY_HISTORY.forEach((point, index) => expectBucket(absOption, index, absRows(point), `Abs, day ${index}`));

        // (b) P&L line: the total and one row per broker.
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        const lineOption = await waitForPnlLineWithBrokers(MONEY_BROKER_NAMES);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pnl']);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        for (const index of MONEY_HISTORY.keys()) expectBucket(lineOption, index, pnlLineRows(index), `P&L line, day ${index}`);

        // (c) Candles, one per day at the ladder's lowest rung: the brokers under the OHLC rows.
        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        const candleOption = await waitForFrame(FRAME.candles);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-candles']);
        for (const index of MONEY_CANDLES.points.keys()) expectBucket(candleOption, index, candleRows(index), `candles, day ${index}`);

        // (d) Income: the three days are one bar, and every row of it is signed.
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        const incomeOption = await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        // The interest row is the one a sign decided before rounding would print `+0.00`.
        expectDrawnInterestResidue();
        expectBucket(incomeOption, 0, incomeRows(), 'Income');

        // The walk met every outcome a row can print, so none of the checks above was vacuous.
        const signed = walked.filter((row) => row.signed);
        expect(
            signed.some((row) => row.amount > 0 && !printsAsZero(row.amount)),
            'a signed gain',
        ).toBe(true);
        expect(
            signed.some((row) => row.amount < 0 && !printsAsZero(row.amount)),
            'a signed loss',
        ).toBe(true);
        expect(
            signed.some((row) => printsAsZero(row.amount)),
            'a signed zero',
        ).toBe(true);
        expect(
            walked.some((row) => !row.signed && row.amount < 0 && !printsAsZero(row.amount)),
            'an unsigned loss',
        ).toBe(true);
    });

    it('paints a row that prints as zero in the neutral colour, a float residue like an exact zero, never as a gain', async () => {
        // WHY: a row that prints `EUR 0.00` with no sign is neither a gain nor a loss, and its
        // colour must not say otherwise. The Income bar's interest is a float residue (5.55e-17):
        // it prints as zero, so it must be painted like the exact zero next to it (nothing
        // reinvested), not in the colour of a gain. Catches the colour decided on the raw value
        // again (`v === 0`), which paints `EUR 0.00` green. The colours are compared with one
        // another, never with a literal: the palette is the component's to choose. Neither the
        // mask nor the locale enters the colour, so one render in the clear is enough.
        expect(isPrivacyEnabled()).toBe(false);
        const {getByTestId} = render(GrowthChart, {
            props: {history: MONEY_HISTORY, incomeHistory: MONEY_INCOME, costHistory: MONEY_COSTS, depositHistory: MONEY_DEPOSITS, acquisitionFunding: MONEY_ACQUISITION, baseCurrency: BASE_CURRENCY},
        });
        await waitForFrame(FRAME.abs);
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await waitForFrame(FRAME.pnlLine);
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        const option = await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);

        expectDrawnInterestResidue();
        expect(
            barSum(MONEY_ACQUISITION.points, (point) => point.from_reinvested),
            'nothing reinvested: an exact zero',
        ).toBe(0);
        const html = option.tooltip.formatter([{dataIndex: 0}]);
        // Both rows print the same zero, so only their colour can still tell them apart.
        const zero = expectedAmount(0, {signed: true});
        expect(rowValue(tooltipRows(html), 'transactions.types.INTEREST')).toBe(zero);
        expect(rowValue(tooltipRows(html), 'dashboard.pnlAcqReinvested')).toBe(zero);

        /** The colour of a row's value: its `<b>`'s own, which jsdom normalises (`#…` reads back as `rgb(…)`). */
        const colourOf = (labelKey: string) => {
            const matching = tooltipRowElements(html).filter(({label}) => label.textContent === labelOf(labelKey));
            expect(matching, `exactly one tooltip row labelled ${labelKey}`).toHaveLength(1);
            return matching[0].value.style.color;
        };
        const neutral = colourOf('dashboard.pnlAcqReinvested');
        const gain = colourOf('transactions.types.DIVIDEND');
        const loss = colourOf('dashboard.feesAndTaxes');
        // Preconditions: three real colours, all different. A palette that painted every row
        // alike would otherwise pass the check below without deciding anything.
        expect(neutral, 'the exact zero has a colour').not.toBe('');
        expect(neutral, 'the zero colour is not the gain colour').not.toBe(gain);
        expect(neutral, 'the zero colour is not the loss colour').not.toBe(loss);
        expect(gain, 'the gain colour is not the loss colour').not.toBe(loss);

        expect(colourOf('transactions.types.INTEREST'), 'a float residue that prints EUR 0.00 is painted as a zero, not as a gain').toBe(neutral);
    });
});

// =============================================================================
// S5 — persistence of the mode and the P&L submode
// =============================================================================

/**
 * The Abs/%/P&L mode and the P&L submode survive a reload through two per-user localStorage
 * keys. They are written when the user clicks and read once, at mount. Every case mounts from
 * an empty stub (cleared in the file-level `beforeEach`), so the defaults are the defaults by
 * construction, not by the order the cases happen to run in.
 */
describe('GrowthChart mode persistence (S5)', () => {
    it('draws the restored P&L Income submode on the very first frame', async () => {
        // WHY: a restore that lands after the first render shows the user a line chart that
        // then jumps to bars. Catches a submode that starts at its default and is restored
        // only after the first frame, or not at all.
        storage.set(MODE_KEY, 'pnl');
        storage.set(SUBMODE_KEY, 'income');
        render(GrowthChart, {props: {history: HISTORY}});

        await waitFor(() => expect(setOptionCount()).toBeGreaterThan(0), {timeout: 5_000});
        const [first] = chartInstances[0].setOptionCalls;
        // The first call is a full rebuild: it is the frame the user sees first.
        expect(fullOptionsSince(0)[0]).toBe(first.option);
        expect(seriesTypes(first.option as unknown as FullOption)).toEqual(FRAME.income);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pnl']);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
    });

    it('falls back to Abs and to the line submode when the stored values are not recognised', async () => {
        // WHY: the keys live in users' browsers and outlive the code that wrote them. A value
        // from an older build, or a hand-edited one, must land on the defaults and not on a
        // view nothing can draw. Catches the loss of the whitelist in readStoredMode or
        // readStoredSubmode.
        storage.set(MODE_KEY, 'garbage');
        storage.set(SUBMODE_KEY, 'garbage');
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});

        // The drawn frame and the pressed button must agree: both say Abs.
        await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await waitForFrame(FRAME.pnlLine);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
    });

    it('shows Abs for a restored % view whose history has no % data, without overwriting the stored choice', async () => {
        // WHY: the % button is disabled without % data, so a restored % view would stay
        // selected on a disabled button, over a chart with nothing to draw. But the choice
        // belongs to the user, and it must come back when a history with returns does.
        // Catches the fallback being dropped, or being done through selectMode, which
        // persists.
        storage.set(MODE_KEY, 'pct');
        const {getByTestId, rerender} = render(GrowthChart, {props: {history: [], loading: true}});
        // Barrier: the stored % really was restored. Otherwise "Abs after the load" would be
        // the default, not a fallback.
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pct']);

        // The Dashboard's own shape: `loading` clears together with the history arriving.
        await rerender({history: NO_PCT_HISTORY, loading: false});
        await waitForFrame(FRAME.abs);
        // Precondition: the component itself sees no % data in this history.
        expect(getByTestId('growth-toggle-pct')).toBeDisabled();
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        expect(storage.get(MODE_KEY)).toBe('pct');
        expect(persistedWrites()).toEqual([]);
    });

    it('keeps a mode the user clicked while loading, even when the restored % view had no data', async () => {
        // WHY: the % fallback runs once, after the first completed load. A user who has
        // already chosen by then must not be overruled by it. Catches selectMode no longer
        // disarming the pending check.
        storage.set(MODE_KEY, 'pct');
        const {getByTestId, rerender} = render(GrowthChart, {props: {history: [], loading: true}});
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pct']);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pnl']);

        await rerender({history: NO_PCT_HISTORY, loading: false});
        await fullOptionAfter(0);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pnl']);
        expect(seriesTypes(latestFullOption())).toEqual(FRAME.pnlLine);
    });

    it('writes the per-user keys on click only, never on mount', async () => {
        // WHY: the stored value must be the user's last explicit choice. A mount that writes
        // would turn a default, or the display-only % fallback, into a saved preference.
        // Catches a renamed key (which silently drops every saved preference), persistence
        // moved into an effect (which writes on mount), or a click that no longer persists.
        storage.set(SUBMODE_KEY, 'income');
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});

        await waitForFrame(FRAME.abs);
        expect(persistedWrites()).toEqual([]);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        // The restored submode is live, so the empty log above means "restored and not
        // rewritten", not "never read".
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        expect(storage.get(MODE_KEY)).toBe('pnl');

        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        expect(storage.get(SUBMODE_KEY)).toBe('candles');
        expect(persistedWrites()).toEqual([
            [MODE_KEY, 'pnl'],
            [SUBMODE_KEY, 'candles'],
        ]);
    });
});

// =============================================================================
// S9 — the synthetic-candle caption
// =============================================================================

describe('GrowthChart synthetic-candle caption (S9)', () => {
    const CAPTION = 'growth-pnl-candles-hypothetical-label';

    it('shows the synthetic-candle caption in the candles submode only, as a marquee line carrying the resolved disclosure', async () => {
        // WHY: the candles are synthetic (cross-asset highs and lows are hypothetical), and
        // this caption is their only disclosure, because the tooltip carries none. It must
        // appear with the candles and nowhere else. It must keep the marker the marquee
        // looks for, so that on a narrow screen it scrolls instead of being cut off. Catches
        // the caption dropped, shown in the wrong submode, or losing the marquee marker.
        const expected = get(_)('dashboard.pnlCandlesHypotheticalShort');
        // An unresolved key comes back as the key itself, and two copies of it would match.
        expect(expected).not.toBe('dashboard.pnlCandlesHypotheticalShort');

        const {getByTestId, queryAllByTestId} = render(GrowthChart, {props: {history: HISTORY, pnlCandles: PNL_CANDLES}});
        await waitForFrame(FRAME.abs);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        expect(queryAllByTestId(CAPTION)).toHaveLength(0);

        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-candles']);
        const caption = getByTestId(CAPTION);
        expect(caption.matches(OVERFLOW_MARQUEE_SELECTOR)).toBe(true);
        expect(caption.textContent).toBe(expected);

        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        expect(queryAllByTestId(CAPTION)).toHaveLength(0);
    });
});

// =============================================================================
// The grid's left inset (developer review, 2026-09-29)
// =============================================================================

/**
 * With `containLabel: true`, `grid.left` is the OUTER inset: ECharts draws the y labels inside
 * it. It used to be a 52 px constant shared with the floating overlays, so 52 px stood empty
 * before the labels. The overlays now read the laid-out grid back (`syncPlotGeometry` →
 * `plotLeftPx`), so nothing needs a fixed gutter any more.
 */
describe('GrowthChart grid left inset (developer review, 2026-09-29)', () => {
    /** `FullOption` leaves the grid out: only this describe reads it. */
    type WithGrid = FullOption & {grid?: {left?: unknown; containLabel?: unknown}};

    /** The two properties the decision is about, on one full rebuild. */
    function expectLeftInset(option: FullOption, view: string) {
        const grid = (option as WithGrid).grid;
        expect(grid?.left, `${view}: grid.left`).toBe('3%');
        expect(grid?.containLabel, `${view}: grid.containLabel`).toBe(true);
    }

    it('insets the grid by 3% with containLabel, so the y labels start near the edge, with no fixed px gutter before them', async () => {
        // WHY: developer review, 2026-09-29, from a phone on P&L/Income: too much empty space
        // on the left of the chart. Catches a px constant put back into `grid.left` (the old 52
        // can never be '3%'), or `containLabel` dropped, which would squeeze the labels into the
        // 3% and clip them. Right, top and bottom are not part of that decision: not asserted.
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});
        expectLeftInset(await waitForFrame(FRAME.abs), 'Abs');

        // The view the review was made on.
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        expectLeftInset(await waitForFrame(FRAME.income), 'P&L Income');
    });
});

// =============================================================================
// S7 — the ladder x axis of the Candles and Income submodes
// =============================================================================

/**
 * Under the candle-width ladder a bucket is a fixed number of days. The product decision (D16-ii)
 * anchors the buckets on the LAST day of the period: the newest bucket closes on the last day, and
 * the short bucket, if any, is the OLDEST one, drawn translucent and explained in its tooltip. Both
 * submodes sit on one category axis whose `data` are the closing dates, labelled and separated by
 * the planner (`growthLadderAxis.ts`), and the user's window survives a zoom, a rung change and a
 * redraw of the same period.
 *
 * The explanation is a translation inside the tooltip's HTML, so it reaches the user as written,
 * never as markup (the S7 XSS rule): one B5 block swaps in a markup-looking catalogue message.
 *
 * Every expected value is derived by hand from the fixtures' per-day formulas and the calendar,
 * never by running the planner. The label strings (`Jan 5`, `May 3`) are the planner's Part A
 * contract in the file's locale (en) on this machine's ICU, which `growthLadderAxis.test.ts`
 * checks first (A0): they are dates this file chose, not UI translations.
 *
 * Opening pick: without the measured grid every rung is offered, so Candles open on 1D and Income
 * on 1W, its floor. Every case that names a rung presses it and waits for it to read as pressed,
 * so no case depends on the opening pick.
 */
// WHY the 30 s budget: a case chains several 5 s waits, and a red `waitFor` must be able to exhaust
// its own timeout and rethrow the case's assertion instead of dying on the test timeout.
describe('GrowthChart ladder x axis (S7)', {timeout: 30_000}, () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case (as S2a does).
    afterEach(() => setPrivacyEnabled(false));

    /** The two submodes on the ladder, and the rungs the cases press (the test-id suffixes). WHY: a typo in a case is a type error, not a 5 s timeout. */
    type Submode = 'candles' | 'income';
    type Rung = '1d' | '1w' | '2w' | '1m';

    /** Both ladder submodes. WHY: every defect shows on both, and a fix on one alone must stay red. */
    const SUBMODES: Array<{title: string; submode: Submode}> = [
        {title: 'Candles', submode: 'candles'},
        {title: 'Income', submode: 'income'},
    ];

    /** How many series each submode draws, from its frame. WHY: "no bucket marked" is stated per series, independently of what rendered. */
    const SERIES_COUNT: Record<Submode, number> = {candles: FRAME.candles.length, income: FRAME.income.length};

    /** 40 days at 1W, end-anchored: 2026-02-09 back by 7 days. WHY a literal: the calendar, counted by hand, is the oracle. */
    const WEEK_CLOSINGS_40 = ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26', '2026-02-02', '2026-02-09'];

    /** 730 days at 1M, buckets 19..24: 2026-09-30 back by 30 days. WHY a literal: the calendar, counted by hand, is the oracle. */
    const MONTH_WINDOW_CLOSINGS = ['2026-05-03', '2026-06-02', '2026-07-02', '2026-08-01', '2026-08-31', '2026-09-30'];

    /** The zoom start whose left edge is bucket 19 of 0..24. WHY: ECharts rounds `pct / 100 × (n − 1)` to a bucket, so this is the window [19..24]. */
    const MONTH_WINDOW_START = (19 / 24) * 100;

    /** What a missing callback reads as in a failure diff. WHY: a named sentinel keeps the red on the assertion, not on a TypeError. */
    const NOT_A_FUNCTION = 'not a function';

    /** Mounts on `fixture` and walks into a ladder submode (Abs, then P&L, then the submode). WHY: the path a user takes, one full frame at a time. */
    async function enterLadderView(fixture: LadderFixture, submode: Submode) {
        const view = render(GrowthChart, {props: ladderProps(fixture)});
        await waitForFrame(FRAME.abs);
        await fireEvent.click(view.getByTestId('growth-toggle-pnl'));
        await fireEvent.click(view.getByTestId(`growth-pnl-submode-${submode}`));
        await waitForFrame(submode === 'candles' ? FRAME.candles : FRAME.income);
        return view;
    }

    /** Presses a rung and waits until it reads as pressed. WHY: no case may depend on the rung the chart opened on. */
    async function pressRung(rung: Rung) {
        const id = `growth-candle-width-${rung}`;
        await fireEvent.click(screen.getByTestId(id));
        await waitFor(() => expect(screen.getByTestId(id).getAttribute('aria-pressed')).toBe('true'), {timeout: 5_000});
    }

    /** Waits until every series of the latest rendered series array has `count` buckets. WHY: proves the pressed rung has actually been drawn. */
    async function waitForBuckets(count: number) {
        await waitFor(
            () => {
                const series = renderedSeries();
                expect(series.length).toBeGreaterThan(0);
                expect(series.map((entry) => entry.data.length)).toEqual(series.map(() => count));
            },
            {timeout: 5_000},
        );
    }

    /** Enters `submode` on `fixture`, presses `rung` and waits for its `buckets`. WHY: the common opening, settled on facts true before and after the fix. */
    async function openRung(fixture: LadderFixture, submode: Submode, rung: Rung, buckets: number) {
        const view = await enterLadderView(fixture, submode);
        await pressRung(rung);
        await waitForBuckets(buckets);
        return view;
    }

    /** True when a datum carries the partial mark: an `itemStyle.opacity` strictly between 0 and 1. WHY: translucent is the decided look (D16-ii). */
    function isMarkedPartial(datum: unknown): boolean {
        if (datum == null || typeof datum !== 'object' || Array.isArray(datum)) return false;
        const opacity = (datum as {itemStyle?: {opacity?: unknown}}).itemStyle?.opacity;
        return typeof opacity === 'number' && opacity > 0 && opacity < 1;
    }

    /** The indices of the buckets a series marks as partial. WHY: a list makes "bucket 0 and no other" one assertion. */
    function markedBuckets(series: SeriesUpdate): number[] {
        return series.data.flatMap((datum, index) => (isMarkedPartial(datum) ? [index] : []));
    }

    /** The tooltip of bucket `index`. WHY: the formatter reads live state, so the latest full option answers for the rung on screen. */
    function ladderTooltip(index: number): string {
        return latestFullOption().tooltip.formatter([{dataIndex: index}]);
    }

    /** Tooltip HTML parsed into a detached host. WHY: lines are read as elements, never matched as substrings. */
    function tooltipHost(html: string): HTMLDivElement {
        const host = document.createElement('div');
        host.innerHTML = html;
        return host;
    }

    /** The text of the first top-level element. WHY: `buildTooltipHeader` emits the header as the first `<div>`. */
    function tooltipHeaderText(html: string): string | null {
        return tooltipHost(html).firstElementChild?.textContent ?? null;
    }

    /** The text of every top-level `<div>`. WHY: "exactly one partial line" is then a count on this list. */
    function topLevelDivTexts(html: string): string[] {
        return Array.from(tooltipHost(html).children)
            .filter((child) => child.tagName === 'DIV')
            .map((child) => child.textContent ?? '');
    }

    /** The partial-bucket line as the user reads it. WHY: resolved through i18n with the values the component must pass, never a literal.
     *  The component escapes this line, so the user reads the resolved text as written; `htmlText` returns that same text while the
     *  catalogue entry holds no markup or entities, as in all four locales today. The markup case is B5's escape block (`withPartialBucketMessage`). */
    function partialLine(days: number, total: number): string {
        const resolved = get(_)('chart.tooltip.partialBucket', {values: {days, total}});
        if (resolved === 'chart.tooltip.partialBucket') throw new Error('chart.tooltip.partialBucket does not resolve in the file locale');
        return htmlText(resolved);
    }

    /** Any partial-bucket line, whatever its numbers. WHY: an absence check must not be defeated by a line carrying other numbers.
     *  Built through `htmlText`, so it matches the escaped line only while the catalogue entry holds no markup or entities (see `partialLine`). */
    function partialLinePattern(): RegExp {
        const text = htmlText(get(_)('chart.tooltip.partialBucket', {values: {days: 'DAYSSLOT', total: 'TOTALSLOT'}}));
        if (!text.includes('DAYSSLOT') || !text.includes('TOTALSLOT')) throw new Error(`chart.tooltip.partialBucket did not take its values: ${text}`);
        const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`^${escaped.replace('DAYSSLOT', '\\d+').replace('TOTALSLOT', '\\d+')}$`);
    }

    /** The part of an x axis this describe reads. WHY: `FullOption` leaves the x axis out; only S7 reads it. */
    interface XAxisOption {
        type?: unknown;
        data?: unknown;
        axisLabel?: {formatter?: unknown; interval?: unknown};
        splitLine?: {interval?: unknown};
    }

    /** ECharts' category-axis callbacks: `formatter(value, index)`, `interval(index, value)`. WHY: the cases call them the way ECharts does. */
    type LabelFormatter = (value: string, index: number) => string;
    type IntervalCallback = (index: number, value: string) => boolean;

    /** The x axis of one option, object or array. WHY: ECharts accepts both, and the fix may send either. */
    function xAxisOf(option: Record<string, unknown>): XAxisOption | undefined {
        const axis = option.xAxis;
        return (Array.isArray(axis) ? axis[0] : axis) as XAxisOption | undefined;
    }

    /** The x axis of the latest call whose x axis carries `key`. WHY: the axis arrives in pieces, a full option and then `{xAxis}`-only re-plans. */
    function latestXAxisWith(key: 'axisLabel' | 'data'): XAxisOption | undefined {
        expect(chartInstances).toHaveLength(1);
        const calls = chartInstances[0].setOptionCalls;
        for (let index = calls.length - 1; index >= 0; index -= 1) {
            const axis = xAxisOf(calls[index].option);
            if (axis?.[key] != null) return axis;
        }
        return undefined;
    }

    /** `value` when it is a function, else null. WHY: today's axis may carry a number or nothing where the fix puts a callback. */
    function fn<T>(value: unknown): T | null {
        return typeof value === 'function' ? (value as T) : null;
    }

    /** Calls `call`, turning a throw into a labelled value. WHY: today's callbacks were not written for these arguments, and a throw must show in the diff, not replace it. */
    function attempt<T>(call: () => T): T | string {
        try {
            return call();
        } catch (error) {
            return `threw: ${error instanceof Error ? error.message : String(error)}`;
        }
    }

    /** Zooms the way a user does, on the fake clock. WHY: ECharts' own state first, then the event, then well past the 200 ms debounce. */
    async function zoomOnFakeClock(start: number, end: number) {
        expect(chartInstances).toHaveLength(1);
        chartInstances[0].setZoom(start, end);
        chartInstances[0].emit('dataZoom');
        await vi.advanceTimersByTimeAsync(1_000);
        await tick();
    }

    /** B9's zoom onto buckets [19..24], without its call counts, then real timers again. WHY: the opening of B10 and B11 must not assert what B9 pins. */
    async function zoomToMonthWindow1924() {
        vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout']});
        try {
            await zoomOnFakeClock(MONTH_WINDOW_START, 100);
        } finally {
            vi.useRealTimers();
        }
    }

    /** Measured grid, 730 days at 1M (25 buckets), window [19..24]. WHY: the one state B10 and B11 start from. */
    async function openMonthWindow1924(submode: Submode) {
        fakeGeometry.measured = true;
        const view = await openRung(FIXTURE_730, submode, '1m', 25);
        await zoomToMonthWindow1924();
        return view;
    }

    /** One `dataZoom` entry, fields unknown. WHY: a missing or non-numeric start must show in the diff, not be assumed. */
    interface ZoomEntry {
        start?: unknown;
        end?: unknown;
    }

    /** The first entry of a `dataZoom`, object or array. WHY: `getZoomPercent()` reads `dataZoom[0]`, the window ECharts keeps. */
    function firstZoomOf(raw: unknown): ZoomEntry | undefined {
        return (Array.isArray(raw) ? raw[0] : raw) as ZoomEntry | undefined;
    }

    /** Waits for the first call after `since` that carries a `dataZoom`, and returns its first entry. WHY: the redraw barrier, without which "kept" could be read before the component reacts. */
    async function firstZoomAfter(since: number): Promise<ZoomEntry | undefined> {
        let found: ZoomEntry | undefined;
        await waitFor(
            () => {
                expect(chartInstances).toHaveLength(1);
                const call = chartInstances[0].setOptionCalls.slice(since).find((entry) => entry.option.dataZoom != null);
                expect(call, `a setOption call carrying dataZoom after call ${since}`).toBeDefined();
                found = firstZoomOf(call?.option.dataZoom);
            },
            {timeout: 5_000},
        );
        return found;
    }

    /** A window as the bucket at its left edge, and its right edge. WHY: the cases state windows in buckets, with ECharts' own rounding. */
    function zoomBucket(zoom: ZoomEntry | undefined, lastIndex: number): {startBucket: unknown; end: unknown} {
        return {startBucket: typeof zoom?.start === 'number' ? Math.round((zoom.start / 100) * lastIndex) : zoom?.start, end: zoom?.end};
    }

    // --- B1-B3: the buckets end on the last day ------------------------------------------------

    it('B1 Candles, 40 days, 1W: each candle spans its end-anchored week (bucket 0 = Jan 1..5, bucket 5 = Feb 3..9)', async () => {
        // WHY: defect 1, start-anchored buckets make the newest week the short one; the quads come by hand from open 500+100i, close 540+100i, low 480+100i, high 560+100i.
        await openRung(FIXTURE_40, 'candles', '1w', 6);
        const [candles] = renderedSeries();
        expect([quadOf(candles.data[0]), quadOf(candles.data[5])]).toEqual([
            [500, 940, 480, 960],
            [3800, 4440, 3780, 4460],
        ]);
    });

    it('B2 Income, 40 days, 1W: each bar sums its end-anchored week, on each of the six series', async () => {
        // WHY: defect 1 on sums: today bucket 0 adds days 0..6 (dividend 105); end-anchored it adds days 0..4 (5 × 12 + 0+1+2+3+4 = 70) and bucket 5 days 33..39.
        await openRung(FIXTURE_40, 'income', '1w', 6);
        // Fixed slot order: dividend, interest, costs, deposit, new capital, reinvested.
        expect(renderedSeries().map((entry) => [pointValue(entry.data[0]), pointValue(entry.data[5])])).toEqual([
            [70, 336],
            [25, 273],
            [-30, -280],
            [760, 1302],
            [460, 882],
            [235, 567],
        ]);
    });

    it.each(SUBMODES)('B3 $title, 40 days, 1W: the tooltip header names the rung and the days the bucket really covers', async ({submode}) => {
        // WHY: defect 1 in words: the header must describe the drawn bucket (Jan 1 → Jan 5), not a week the chart does not draw (Jan 1 → Jan 7).
        await openRung(FIXTURE_40, submode, '1w', 6);
        const weekKey = 'datePicker.granularity.weeksShort';
        const week = htmlText(get(_)(weekKey));
        expect(week, `${weekKey} resolves`).not.toBe(weekKey);
        expect([0, 5].map((index) => tooltipHeaderText(ladderTooltip(index)))).toEqual([`1${week} - 2026-01-01 → 2026-01-05`, `1${week} - 2026-02-03 → 2026-02-09`]);
    });

    // --- B4-B5: the short bucket is marked, and explained --------------------------------------

    it('B4 Candles, 40 days: no candle marked at 1D; at 1W the short bucket 0 is marked partial, and no other', async () => {
        // WHY: defect 1, the short bucket is drawn like the others; at 1D every bucket is one whole day, so a mark there would be noise.
        await openRung(FIXTURE_40, 'candles', '1d', DAY_COUNT);
        expect(renderedSeries().map(markedBuckets), '1D: no candle marked').toEqual(Array.from({length: SERIES_COUNT.candles}, () => []));
        await pressRung('1w');
        await waitForBuckets(6);
        expect(renderedSeries().map(markedBuckets), '1W: bucket 0 marked, no other').toEqual(Array.from({length: SERIES_COUNT.candles}, () => [0]));
    });

    it('B4 Income, 40 days, 1W: bucket 0 is marked partial on each of the six series, and no other bucket', async () => {
        // WHY: every bar of the short oldest week under-counts, so every series must say so, and no whole week may.
        await openRung(FIXTURE_40, 'income', '1w', 6);
        expect(renderedSeries().map(markedBuckets)).toEqual(Array.from({length: SERIES_COUNT.income}, () => [0]));
    });

    it.each(SUBMODES)('B4 $title, 1M: nothing marked on 90 days (three whole months), bucket 0 marked on 93 days (3 of 30 days)', async ({submode}) => {
        // WHY: the mark follows the calendar, not the rung: 90 days are three whole 30-day buckets, 93 leave a 3-day oldest one.
        const view = await openRung(FIXTURE_90, submode, '1m', 3);
        expect(renderedSeries().map(markedBuckets), '90 days: every bucket whole').toEqual(Array.from({length: SERIES_COUNT[submode]}, () => []));

        // One deferred render per effect run: wait for it before pressing, so the press acts on the 93 days.
        const since = setOptionCount();
        await view.rerender(ladderProps(FIXTURE_93));
        await waitFor(() => expect(chartInstances[0].setOptionCalls.slice(since).some((call) => Array.isArray(call.option.series))).toBe(true), {timeout: 5_000});
        await pressRung('1m');
        await waitForBuckets(4);
        expect(renderedSeries().map(markedBuckets), '93 days: bucket 0 marked, no other').toEqual(Array.from({length: SERIES_COUNT[submode]}, () => [0]));
    });

    it('B5 Candles, 40 days: no partial line at 1D nor on a whole week; the short week says it covers 5 of 7 days, once', async () => {
        // WHY: the tooltip is where the user learns why the oldest candle is short; it must say so once, with the bucket's own day count, and never on a whole bucket.
        await openRung(FIXTURE_40, 'candles', '1d', DAY_COUNT);
        const anyPartial = partialLinePattern();
        const partialLinesAt = (index: number) => topLevelDivTexts(ladderTooltip(index)).filter((text) => anyPartial.test(text));
        expect(Array.from(Array(DAY_COUNT).keys()).flatMap(partialLinesAt), '1D: no partial line on any day').toEqual([]);

        await pressRung('1w');
        await waitForBuckets(6);
        expect(partialLinesAt(5), '1W: no partial line on the whole week 5').toEqual([]);
        const line = partialLine(5, 7);
        expect(
            topLevelDivTexts(ladderTooltip(0)).filter((text) => text === line),
            '1W: exactly one partial line on bucket 0',
        ).toEqual([line]);
    });

    it('B5 Income, 40 days, 1W: no partial line on a whole week; the short week says it covers 5 of 7 days, once', async () => {
        // WHY: the Income header drops "value at" (a bar is a sum), so the partial line is the one place the short week is explained.
        await openRung(FIXTURE_40, 'income', '1w', 6);
        const anyPartial = partialLinePattern();
        expect(
            topLevelDivTexts(ladderTooltip(5)).filter((text) => anyPartial.test(text)),
            'no partial line on the whole week 5',
        ).toEqual([]);
        const line = partialLine(5, 7);
        expect(
            topLevelDivTexts(ladderTooltip(0)).filter((text) => text === line),
            'exactly one partial line on bucket 0',
        ).toEqual([line]);
    });

    it.each(SUBMODES)('B5 $title, 93 days, 1M: the short oldest month says it covers 3 of 30 days, once', async ({submode}) => {
        // WHY: the day count is the bucket's own, not a constant of the rung: 1M on 93 days leaves 3 of 30.
        await openRung(FIXTURE_93, submode, '1m', 4);
        const line = partialLine(3, 30);
        expect(topLevelDivTexts(ladderTooltip(0)).filter((text) => text === line)).toEqual([line]);
    });

    /** The plain word that opens the swapped-in partial message. WHY: it finds the partial line whatever the component did to the rest of it, so a red shows what the user read. */
    const PARTIAL_MARKER = 'S7-ESCAPE-LOCK';

    /** A partial-bucket message that is markup if read as HTML: an entity and a tag around the two values. WHY: a translation is data, so both must reach the user as the characters written here. */
    const MARKUP_LOOKING_PARTIAL = `${PARTIAL_MARKER} &lt;b&gt; {days}/{total} <i>x</i>`;

    /**
     * Runs `body` while the current locale's `chart.tooltip.partialBucket` reads `message`, then puts the
     * catalogue's own text back and proves it. WHY: the catalogue is module state shared by every case in
     * the file, so whoever swaps a message restores it, whatever the outcome of the case (as with the
     * privacy flag); `body` is synchronous, so no scheduled render can run while the swap is in place.
     */
    function withPartialBucketMessage(message: string, body: () => void) {
        const localeCode = get(locale);
        if (!localeCode) throw new Error('no current locale: setupI18n() has not run');
        // The catalogue's own leaf, read along the same nested path the swap writes.
        const source = () => ['chart', 'tooltip', 'partialBucket'].reduce<unknown>((node, key) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[key] : undefined), get(dictionary)[localeCode]);
        const resolved = () => get(_)('chart.tooltip.partialBucket', {values: {days: 5, total: 7}});
        const original = source();
        if (typeof original !== 'string') throw new Error(`chart.tooltip.partialBucket is not a string in the ${localeCode} catalogue`);
        const before = resolved();
        addMessages(localeCode, {chart: {tooltip: {partialBucket: message}}});
        try {
            body();
        } finally {
            addMessages(localeCode, {chart: {tooltip: {partialBucket: original}}});
            expect({source: source(), resolved: resolved()}, `the ${localeCode} catalogue is restored`).toEqual({source: original, resolved: before});
        }
    }

    it.each(SUBMODES)('B5 $title, 40 days, 1W: the partial line shows its translation as written, never as markup', async ({submode}) => {
        // WHY: the tooltip is HTML handed to ECharts and a translation is data, so an entity or a tag in it must reach the user as text, on both return paths of the ladder header.
        await openRung(FIXTURE_40, submode, '1w', 6);
        withPartialBucketMessage(MARKUP_LOOKING_PARTIAL, () => {
            const written = get(_)('chart.tooltip.partialBucket', {values: {days: 5, total: 7}});
            expect(written, 'precondition: the swapped-in message resolves, values in, markup untouched').toBe(MARKUP_LOOKING_PARTIAL.replace('{days}', '5').replace('{total}', '7'));
            expect(
                topLevelDivTexts(ladderTooltip(0)).filter((text) => text.includes(PARTIAL_MARKER)),
                'exactly one partial line, shown as written',
            ).toEqual([written]);
        });
    });

    // --- B6-B8: one category axis, labelled by the planner, and an honest offer ----------------

    it('B6 Income, 40 days, measured, 1W: the category axis carries the six closings, labels each one and draws each separator', async () => {
        // WHY: defects 2 and 3, the axis must name the buckets it draws; the label strings are the planner's Part A contract on this ICU (A0), dates chosen here, not UI translations.
        fakeGeometry.measured = true;
        await openRung(FIXTURE_40, 'income', '1w', 6);
        await waitFor(
            () => {
                const labelled = latestXAxisWith('axisLabel');
                const format = fn<LabelFormatter>(labelled?.axisLabel?.formatter);
                const showLabel = fn<IntervalCallback>(labelled?.axisLabel?.interval);
                const showSeparator = fn<IntervalCallback>(labelled?.splitLine?.interval);
                expect({
                    data: latestXAxisWith('data')?.data ?? null,
                    labels: WEEK_CLOSINGS_40.map((date, index) => (format ? attempt(() => format(date, index)) : NOT_A_FUNCTION)),
                    labelShown: WEEK_CLOSINGS_40.map((date, index) => (showLabel ? attempt(() => showLabel(index, date)) : NOT_A_FUNCTION)),
                    separatorShown: WEEK_CLOSINGS_40.map((date, index) => (showSeparator ? attempt(() => showSeparator(index, date)) : NOT_A_FUNCTION)),
                }).toEqual({
                    data: WEEK_CLOSINGS_40,
                    labels: ['Jan 5', 'Jan 12', 'Jan 19', 'Jan 26', 'Feb 2', 'Feb 9'],
                    labelShown: WEEK_CLOSINGS_40.map(() => true),
                    separatorShown: WEEK_CLOSINGS_40.map(() => true),
                });
            },
            {timeout: 5_000},
        );
    });

    it('B7 Income full option: a category axis; dividend, interest and costs in one stack, deposit alone, the two funding series in another; 10% gaps', async () => {
        // WHY: defects 3 and 4, bars on a time axis change width with every zoom step, and an unstacked cost column with no gap makes the columns of a bucket touch.
        await enterLadderView(FIXTURE_40, 'income');
        const option = latestFullOption() as unknown as Record<string, unknown> & {series: Array<{stack?: unknown; barGap?: unknown; barCategoryGap?: unknown}>};
        const NONE = 'none';
        expect({
            xAxisType: xAxisOf(option)?.type,
            stack: option.series.map((entry) => entry.stack ?? NONE),
            barGap: option.series.map((entry) => entry.barGap ?? NONE),
            barCategoryGap: option.series.map((entry) => entry.barCategoryGap ?? NONE),
        }).toEqual({
            xAxisType: 'category',
            // Fixed slot order: dividend, interest, costs, deposit, new capital, reinvested.
            stack: ['income', 'income', 'income', NONE, 'acquisition', 'acquisition'],
            barGap: Array.from({length: SERIES_COUNT.income}, () => '10%'),
            barCategoryGap: Array.from({length: SERIES_COUNT.income}, () => '10%'),
        });
    });

    it.each([
        {title: 'Income', submode: 'income' as Submode, offered: ['2w', '1m', '3m', '6m'], pressed: '2w'},
        {title: 'Candles', submode: 'candles' as Submode, offered: ['1w', '2w', '1m', '3m', '6m'], pressed: '1w'},
    ])('B8 $title, 730 days, measured 527 px plot: offers only the rungs it can draw, and presses one of them', async ({submode, offered, pressed}) => {
        // WHY: defects 5 and 8, Income bars need slot × 0.9 / 3.2 ≥ 2 px (1W gives 1.41), candle bodies 2.5 px (3D gives 2.16), both 3 bodies (1Y has 2), and the drawn rung must be offered and pressed.
        fakeGeometry.measured = true;
        await enterLadderView(FIXTURE_730, submode);
        const ids = (rungs: string[]) => rungs.map((rung) => `growth-candle-width-${rung}`).sort();
        await waitFor(
            () => {
                const shown = screen
                    .queryAllByTestId(/^growth-candle-width-/)
                    .map((button) => button.getAttribute('data-testid') ?? '')
                    .sort();
                expect({offered: shown, pressed: pressedAmong(shown)}).toEqual({offered: ids(offered), pressed: ids([pressed])});
            },
            {timeout: 5_000},
        );
    });

    // --- B9-B11: the user's window is kept ------------------------------------------------------

    it.each(SUBMODES)('B9 $title, 730 days, measured, 1M: a zoom re-plans the labels once, as an {xAxis}-only update, and the same zoom again does not', async ({submode}) => {
        // WHY: defects 2 and 6, the labels must follow the visible window [19..24]; the update must not carry dataZoom (it would fight the gesture), and an unchanged plan must not redraw.
        fakeGeometry.measured = true;
        await openRung(FIXTURE_730, submode, '1m', 25);
        expect(chartInstances).toHaveLength(1);
        const chart = chartInstances[0];
        vi.useFakeTimers({toFake: ['setTimeout', 'clearTimeout']});
        try {
            const before = chart.setOptionCalls.length;
            await zoomOnFakeClock(MONTH_WINDOW_START, 100);
            expect(vi.getTimerCount(), 'no timer pending 1000 ms after the zoom').toBe(0);
            const added = chart.setOptionCalls.slice(before);
            expect(added, 'exactly one new setOption call after the zoom').toHaveLength(1);
            const format = fn<LabelFormatter>(xAxisOf(added[0].option)?.axisLabel?.formatter);
            expect({
                keys: Object.keys(added[0].option),
                labels: MONTH_WINDOW_CLOSINGS.map((date, offset) => (format ? attempt(() => format(date, 19 + offset)) : NOT_A_FUNCTION)),
            }).toEqual({keys: ['xAxis'], labels: ['May 3', 'Jun 2', 'Jul 2', 'Aug 1', 'Aug 31', 'Sep 30']});

            const afterFirst = chart.setOptionCalls.length;
            await zoomOnFakeClock(MONTH_WINDOW_START, 100);
            expect(vi.getTimerCount(), 'no timer pending 1000 ms after the repeated zoom').toBe(0);
            expect(chart.setOptionCalls.slice(afterFirst), 'no new setOption call for the same window').toHaveLength(0);
        } finally {
            vi.useRealTimers();
        }
    });

    it.each(SUBMODES)('B10 $title, 730 days, measured: from 1M on [19..24], pressing 2W puts the window on the bucket that holds its first day', async ({submode}) => {
        // WHY: defect 6, a rung change must keep what the user was looking at: the window started on 2026-04-04, which 2W holds in bucket 40 (2026-04-02..04-15).
        await openMonthWindow1924(submode);
        const since = setOptionCount();
        await pressRung('2w');
        expect(zoomBucket(await firstZoomAfter(since), 52)).toEqual({startBucket: 40, end: 100});
    });

    /** Runs `trigger` on the [19..24] window and checks that the redraw keeps it, in the call and in the chart. WHY: the one check the three B11 triggers share. */
    async function expectWindowKeptAcross(trigger: () => unknown) {
        expect(chartInstances).toHaveLength(1);
        const chart = chartInstances[0];
        expect(zoomBucket(firstZoomOf(chart.getOption().dataZoom), 24), 'precondition: the window is [19..24]').toEqual({startBucket: 19, end: 100});
        const since = chart.setOptionCalls.length;
        await trigger();
        const call = zoomBucket(await firstZoomAfter(since), 24);
        expect({call, chart: zoomBucket(firstZoomOf(chart.getOption().dataZoom), 24)}).toEqual({call: {startBucket: 19, end: 100}, chart: {startBucket: 19, end: 100}});
    }

    it('B11 Income, 730 days, 1M on [19..24]: the privacy toggle keeps the window', async () => {
        // WHY: defect 6, the privacy toggle redraws the whole option, and that redraw threw the user's window away.
        await openMonthWindow1924('income');
        await expectWindowKeptAcross(() => setPrivacyEnabled(true));
    });

    it('B11 Income, 730 days, 1M on [19..24]: a re-fetch of the same period keeps the window', async () => {
        // WHY: defect 6, a sync hands a NEW history array with the same dates: the period (first|last date) is unchanged, so the window must be too.
        const view = await openMonthWindow1924('income');
        await expectWindowKeptAcross(() => view.rerender({history: FIXTURE_730.history.map((point) => ({...point}))}));
    });

    it('B11 Income, 730 days, 1M on [19..24]: a locale change keeps the window', async () => {
        // WHY: defect 6, switching the UI language redraws the labels, and must not move the window.
        await openMonthWindow1924('income');
        try {
            await expectWindowKeptAcross(async () => {
                locale.set('it');
                await waitLocale('it');
            });
        } finally {
            locale.set('en');
            await waitLocale('en');
        }
    });

    it('B11 control, Income, 730 days, 1M on [19..24]: a history of another period resets the window to the whole range (green today and after the fix)', async () => {
        // WHY: gives the three B11 cases their teeth: a new period must NOT keep the old window, so "kept" cannot come from a component that never resets.
        const view = await openMonthWindow1924('income');
        const since = setOptionCount();
        await view.rerender({history: FIXTURE_730.history.slice(30)});
        const zoom = await firstZoomAfter(since);
        expect({start: zoom?.start, end: zoom?.end}).toEqual({start: 0, end: 100});
    });
});
