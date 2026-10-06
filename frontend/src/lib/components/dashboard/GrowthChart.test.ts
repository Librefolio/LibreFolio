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
 * THE REST OF THE FILE. Eight smaller subjects share the same recorder: privacy masking
 * of the axis and tooltip formatters (S2a), the one form of every signed tooltip amount in
 * the locale's glyphs (D23, D23b), persistence of the mode and the P&L submode (S5), the
 * synthetic-candle caption (S9), the grid's left inset (developer review, 2026-09-29), the
 * ladder x axis of the Candles and Income submodes (S7) — calendar buckets (06/10/2026), the
 * partial and in-progress ones, the rung offer at measured plot widths — with the rung the ladder
 * opens on (B12: k4 G2, Income on 1M), the money axis ticks: distinct, in the locale's glyphs, with the edge the
 * chart fixes left unlabelled and blank, so the grid does not measure it (S7b: D18, D23, D25, k4 G1),
 * and the purchase value of the Income submode: one name for its two halves, their total in
 * the tooltip, each half in its Abs colour (S8: R11, D26).
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
const {chartInstances, echartsModule, fakeGeometry, DEFAULT_PLOT_WIDTH_PX} = vi.hoisted(() => {
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
     * stays offered. Off by default and reset after every case. On, the grid is a plot of
     * `plotWidthPx` at x 40 of the 1200 px chart: 527 px unless a case sets one of the widths
     * measured on the dashboard (the S7 offer cases), so 40 px of room on the left and the rest
     * of the 1160 on the right.
     */
    const DEFAULT_PLOT_WIDTH_PX = 527;
    const fakeGeometry = {measured: false, plotWidthPx: DEFAULT_PLOT_WIDTH_PX};
    const MEASURED_GRID: GridRect = {x: 40, y: 20, width: DEFAULT_PLOT_WIDTH_PX, height: 300};

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
            chart.getModel = () => ({getComponent: (type: string) => (type === 'grid' ? {coordinateSystem: {getRect: () => ({...MEASURED_GRID, width: fakeGeometry.plotWidthPx})}} : undefined)});
        }

        chartInstances.push(chart);
        return chart;
    }

    return {
        chartInstances,
        echartsModule: {init: (dom: unknown) => createFakeChart(dom)},
        fakeGeometry,
        DEFAULT_PLOT_WIDTH_PX,
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
 * The calendar period a day falls in on a rung of the candle-width ladder, as a key, by the suffix
 * of the rung's test id (`growth-candle-width-1w` → `1w`).
 *
 * The ladder's buckets are calendar periods (developer's decision of 06/10/2026, which replaced
 * D16-ii's plain day counts): `1w` an ISO week from Monday, `2w` a pair of weeks counted from
 * Monday 1969-12-29, `3d` a run of three days counted from 1970-01-01, `1m`, `3m`, `6m` and `1y` a
 * month, a quarter, a half and a year. Written here from that rule with the calendar's own fields
 * (`getUTCDay`, `getUTCMonth`), never through the component's bucket module, so a count it gives
 * is an independent oracle.
 *
 * The Income submode is driven by the ladder: a bar is a SUM over its bucket, not one day, so
 * how many bars the 40 days make depends on the rung Income opens on. k4 G2 decides that rung:
 * 1M, where it used to be 1W, the lowest rung offered (every entry into Income opens on 1M,
 * clamped into the offered rungs — and jsdom reports no plot width, so every rung stays
 * offered). The memo cases are not about that rule, so they count the bars of the rung ON
 * SCREEN: they hold whichever rung Income opens on, and B12 (S7) pins the opening itself.
 *
 * Derived rather than written down: hard-coding 2 would pin one opening rule and say nothing
 * about where the number came from, so a change of rule would leave a number that is wrong
 * without being obviously wrong.
 */
function calendarPeriodKey(iso: string, rung: string): string {
    const date = new Date(`${iso}T00:00:00Z`);
    const day = date.getTime() / 86_400_000;
    // Whole weeks from Monday 1969-12-29 (day -3) to the Monday of this day's week.
    const week = (day - ((date.getUTCDay() + 6) % 7) + 3) / 7;
    const year = date.getUTCFullYear();
    const month0 = date.getUTCMonth();
    const keys: Record<string, string> = {
        '1d': iso,
        '3d': `triple ${Math.floor(day / 3)}`,
        '1w': `week ${week}`,
        '2w': `pair ${Math.floor(week / 2)}`,
        '1m': `${year} month ${month0}`,
        '3m': `${year} quarter ${Math.floor(month0 / 3)}`,
        '6m': `${year} half ${Math.floor(month0 / 6)}`,
        '1y': `${year}`,
    };
    const key = keys[rung];
    if (key === undefined) throw new Error(`${rung} is not a rung of the ladder`);
    return key;
}

/** How many buckets the 40 days make at the rung pressed on screen: the calendar periods they touch. Fails unless exactly one rung of the ladder is pressed. */
function bucketsAtPressedRung(): number {
    const pressed = screen
        .queryAllByTestId(/^growth-candle-width-/)
        .filter((button) => button.getAttribute('aria-pressed') === 'true')
        .map((button) => (button.getAttribute('data-testid') ?? '').replace('growth-candle-width-', ''));
    expect(pressed, 'exactly one rung of the ladder is pressed').toHaveLength(1);
    return new Set(DATES.map((date) => calendarPeriodKey(date, pressed[0]))).size;
}

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
 * - 40 days (Thu 2026-01-01..Mon 02-09): the existing instances, reused as they are. 1W gives seven
 *   calendar weeks: the week of Mon Dec 29, cut at Jan 1 (4 of 7 days), five whole ones, and the week
 *   of Feb 9, one day in when read on Feb 9.
 * - 730 days (2024-10-01..2026-09-30): long enough for a measured 527 px plot to drop the narrow
 *   rungs, and for the 1M window [18..23] (April to September 2026) and its 2W and 3M counterparts.
 * - 90 days (2026-01-01..03-31): three whole calendar months at 1M, no partial bucket.
 * - 93 days (2026-01-01..04-03): four months at 1M, April covering 3 of 30 days — partial once April
 *   is over, the month in progress before.
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

/** ECharts calls an axis label formatter as `formatter(value, index)`, index 0 the lowest tick (k4 G1); most cases pass the value alone, as before. */
type AxisFormatter = (value: number, index?: number) => string;
type TooltipFormatter = (params: Array<{dataIndex: number}>) => string;

/**
 * The part of a full rebuild that the privacy, persistence, caption and axis cases read. `min`
 * stays `unknown`: it is a callback in most views and an explicit `undefined` in Income (D25),
 * so a case proves which before it calls it.
 */
interface FullOption {
    yAxis: {min?: unknown; axisLabel: {formatter: AxisFormatter; showMinLabel?: boolean}};
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

/**
 * The number a money axis label prints before its k/M suffix, from the same call the axis
 * formatter makes on the SCALED value: -5000 prints as `-5`, then `k` (S7b). A negative zero
 * prints as zero, which is the contract, not a detail of the call. The expected sign of an axis
 * label comes from here, never from a literal (D23). `locale` forces one; `undefined` is this
 * machine's.
 */
const axisNumber = (scaled: number, locale?: string) => (scaled === 0 ? 0 : scaled).toLocaleString(locale, {maximumSignificantDigits: 15});

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

/**
 * The label of one half of the Income purchase value, as the user reads it: `↳ `, then the key's
 * text (S8, R11). WHY a helper: the halves are indented under the purchase value, so their row
 * no longer reads as their key alone, and every case must build that label the same way.
 */
const subRowLabel = (labelKey: string) => htmlText(`↳ ${get(_)(labelKey)}`);

/**
 * The value of the one row labelled by `labelKey`, with the label resolved through i18n as the
 * component resolves it. `readAs` builds a label that is more than the key's text, such as
 * `subRowLabel` (S8).
 */
function rowValue(rows: TooltipRow[], labelKey: string, readAs: (key: string) => string = (key) => htmlText(get(_)(key))): string {
    const label = readAs(labelKey);
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
    /** How many real (non-sentinel) values the input should put on the chart, given the Income buckets on screen (the other submodes ignore them). */
    expectedRealValues: (incomeBuckets: number) => number;
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
        // One candle per day: Candles open on their lowest rung, 1D (B12).
        expectedRealValues: () => DAY_COUNT,
        countRealValues: (series) => realCandleQuads(series[0]),
    },
    {
        prop: 'brokerPnlHistory',
        submode: 'line',
        // Fixed slots: total-positive, total-negative, dashed reference. Broker lines are
        // appended after them, so while the prop is absent there are exactly three.
        seriesWhileAbsent: 3,
        arrival: {brokerPnlHistory: BROKER_PNL_HISTORY},
        expectedRealValues: () => 2 * DAY_COUNT,
        countRealValues: (series) => brokerSeries(series).reduce((total, entry) => total + nonNullPoints(entry), 0),
    },
    {
        prop: 'incomeHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {incomeHistory: INCOME_HISTORY},
        // Two series (dividend, interest), each one bar per bucket.
        expectedRealValues: (buckets) => 2 * buckets,
        // Slots 0 and 1 of the income submode's fixed 6-slot order: dividend, interest.
        countRealValues: (series) => nonZeroPoints(series[0]) + nonZeroPoints(series[1]),
    },
    {
        prop: 'costHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {costHistory: COST_HISTORY},
        expectedRealValues: (buckets) => buckets,
        // Slot 2: costs (FEE+TAX, signed negative).
        countRealValues: (series) => nonZeroPoints(series[2]),
    },
    {
        prop: 'depositHistory',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {depositHistory: DEPOSIT_HISTORY},
        expectedRealValues: (buckets) => buckets,
        // Slot 3: deposit size.
        countRealValues: (series) => nonZeroPoints(series[3]),
    },
    {
        prop: 'acquisitionFunding',
        submode: 'income',
        seriesWhileAbsent: 6,
        arrival: {acquisitionFunding: ACQUISITION_FUNDING},
        // Two series (new capital, reinvested), each one bar per bucket.
        expectedRealValues: (buckets) => 2 * buckets,
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
    // WHY: the measured grid and its width are opt-in per case (S7), and a case that installed fake
    // timers or pinned the day, and failed before its own `finally`, must not hand them to the next one.
    fakeGeometry.measured = false;
    fakeGeometry.plotWidthPx = DEFAULT_PLOT_WIDTH_PX;
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
        //    while it did not exist. In Income, one value per bar of the rung on screen, and
        //    every series draws exactly those bars.
        const incomeBuckets = submode === 'income' ? bucketsAtPressedRung() : 0;
        if (submode === 'income') expect(renderedSeries().map((entry) => entry.data.length)).toEqual(renderedSeries().map(() => incomeBuckets));
        expect(countRealValues(renderedSeries())).toBe(expectedRealValues(incomeBuckets));

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

    /**
     * What every money axis label must print with privacy on: the mask, and on a loss the
     * locale's minus kept outside it (D8, D23). This machine's minus comes from the same call the
     * axis formatter makes. The Swedish one is the glyph D23 is about, so it is a literal, under
     * a forced locale.
     */
    function expectMaskedMoneyAxis(format: AxisFormatter) {
        const values = [20_000, -5_000, 0];
        // Preconditions: this machine's locale writes a minus on a loss, so the masked loss is
        // about one; and this Node has Swedish locale data and writes U+2212 there, so the forced
        // locale cannot fall back to a hyphen in silence.
        const hostMinus = leadingSign(axisNumber(-5));
        expect(hostMinus).toMatch(/[-\u2212]/);
        expect(leadingSign(axisNumber(-5, SWEDISH))).toBe('\u2212');
        const labels = {host: values.map((value) => format(value)), swedish: inLocale(SWEDISH, () => values.map((value) => format(value)))};
        expect(labels).toEqual({
            host: [PRIVACY_PLACEHOLDER, `${hostMinus}${PRIVACY_PLACEHOLDER}`, PRIVACY_PLACEHOLDER],
            swedish: [PRIVACY_PLACEHOLDER, `\u2212${PRIVACY_PLACEHOLDER}`, PRIVACY_PLACEHOLDER],
        });
        // The property itself, whatever the placeholder looks like: no digit and no k/M
        // suffix, because `•••k` would still reveal the order of magnitude (D8).
        for (const label of [...labels.host, ...labels.swedish]) expect(label).not.toMatch(/[0-9kM]/);
    }

    it("masks the money axis labels in Abs and P&L line: no digit, no k/M suffix, the locale's minus kept outside", async () => {
        // WHY: with privacy on, the axis ticks are the one place a masked chart would still
        // print the scale of the portfolio (20k, 1.3M). Catches the mask dropped from the
        // compact label, or the suffix moving outside it (`mask(n) + 'k'`). Catches too a minus
        // written by hand in front of the mask instead of the locale's own (D23): in Node's
        // default locale both are a hyphen, so only the forced sv-SE labels tell them apart.
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

        // The axis labels format their number through the locale (S7b), so their literals are
        // pinned under a forced en-US, never against this machine's locale. These four print as
        // they always did; the labels S7b changed (`1.5k`, `1M`) are pinned in its own describe.
        const axis = absOption.yAxis.axisLabel.formatter;
        expect(inLocale('en-US', () => [-5_000, 1_300_000, 0, -0].map((value) => axis(value)))).toEqual(['-5k', '1.3M', '0', '0']);

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
     *  value, and new capital one, which is what brings in the purchase-value group: the bold
     *  purchase value, then its two `↳` halves (new capital, reinvested). */
    function incomeRows(): AmountRow[] {
        const dividend = barSum(MONEY_INCOME.points, (point) => point.dividend);
        const interest = barSum(MONEY_INCOME.points, (point) => point.interest);
        // Why (re-pin, S8): R11 heads the two acquisition rows with the purchase value, their
        // sum, and indents them under it as `↳ ` rows, so the bar prints 8 rows instead of 7. The
        // rows still pin every Income amount in its one signed form, the exact zero of nothing
        // reinvested included.
        const newCapital = barSum(MONEY_ACQUISITION.points, (point) => point.from_new_capital);
        const reinvested = barSum(MONEY_ACQUISITION.points, (point) => point.from_reinvested);
        return [
            {label: labelOf('transactions.types.DIVIDEND'), amount: dividend, signed: true},
            {label: labelOf('transactions.types.INTEREST'), amount: interest, signed: true},
            {label: labelOf('assets.distribution.total'), amount: dividend + interest, signed: true},
            {label: labelOf('dashboard.feesAndTaxes'), amount: barSum(MONEY_COSTS.points, (point) => point.cost), signed: true},
            {label: labelOf('transactions.types.DEPOSIT'), amount: barSum(MONEY_DEPOSITS.points, (point) => point.deposit), signed: true},
            {label: labelOf('dashboard.bookValue'), amount: newCapital + reinvested, signed: true},
            {label: subRowLabel('dashboard.pnlAcqNewCapital'), amount: newCapital, signed: true},
            {label: subRowLabel('dashboard.pnlAcqReinvested'), amount: reinvested, signed: true},
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
        // Why (re-pin, S8): R11 indents the reinvested half under the purchase value, so its row
        // reads `↳ ` before the key's text and both reads below go through `subRowLabel`. The case
        // still proves that an exact zero and a float residue that print alike are painted alike.
        expect(rowValue(tooltipRows(html), 'dashboard.pnlAcqReinvested', subRowLabel)).toBe(zero);

        /** The colour of a row's value: its `<b>`'s own, which jsdom normalises (`#…` reads back as `rgb(…)`). */
        const colourOf = (labelKey: string, readAs: (key: string) => string = labelOf) => {
            const matching = tooltipRowElements(html).filter(({label}) => label.textContent === readAs(labelKey));
            expect(matching, `exactly one tooltip row labelled ${labelKey}`).toHaveLength(1);
            return matching[0].value.style.color;
        };
        const neutral = colourOf('dashboard.pnlAcqReinvested', subRowLabel);
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
 * Under the candle-width ladder a bucket is a CALENDAR period (developer's decision of 06/10/2026, which
 * replaces D16-ii's day counts anchored at the last day): `1W` an ISO week from Monday, `1M` a month from
 * the 1st, `3M`, `6M` and `1Y` a quarter, a half and a year; `3D` and `2W` fixed runs counted from
 * 1970-01-01 and from Monday 1969-12-29, so their edges never move. A bucket is one period the series
 * touches, and its category on the axis — its closing date — is the last day of it the series holds.
 *
 * Two kinds of bucket are not like the others. A period that is over and that the series covers only in
 * part — cut at the start of the range, or at the end of a range that ended in the past — is `partial`:
 * drawn translucent, its tooltip saying how many of its days it holds. The period that has not ended by
 * today is `current`: drawn whole, because its missing days are the future, its tooltip saying how far it
 * has got — except a one-day period, which has nothing in progress to report. A period cut at the start
 * that is also current is partial. Both submodes sit on one category
 * axis whose labels and separators the planner (`growthLadderAxis.ts`) decides, and the user's window
 * survives a zoom, a rung change and a redraw of the same period.
 *
 * TODAY IS PINNED. Which period is current depends on the day the chart is read (`todayIso()`, the user's
 * local calendar), so every case states its today — by default the fixture's last day, the day the
 * dashboard would serve that window. `pinToday` fakes `Date` alone, never the timers `waitFor` polls on,
 * at local noon, which is that calendar day whatever the timezone; the file's `afterEach`
 * (`vi.useRealTimers()`) undoes it. B13 moves the day mid-case, past a period's end, to prove the
 * component's ladder memo is keyed on it.
 *
 * The two explanations are translations inside the tooltip's HTML, so they reach the user as written,
 * never as markup (the S7 XSS rule): the B5 escape block swaps in a markup-looking catalogue message for
 * each of them.
 *
 * Every expected value is derived by hand from the fixtures' per-day formulas and the calendar, and was
 * cross-checked with an independent computation outside this repository; none comes from running the
 * planner or the bucket module. The label strings (`Jan 4`, `Apr 30`) are the planner's Part A contract in
 * the file's locale (en) on this machine's ICU, which `growthLadderAxis.test.ts` checks first (A0): they are
 * dates this file chose, not UI translations.
 *
 * The rung offer (B7, B8) is pinned where the developer's table of 06/10/2026 fixes it: the dashboard's
 * preset windows on that day, at the plot widths measured on the dashboard that day — 484, 573 and 734 px
 * at 1280, 1440 and 1728 px windows, 279 px on a 390 px phone. Income needs three bars of 4.5 px in a
 * bucket, with 30% of the slot between buckets and 10% of a bar between its columns; a candle body 2.5 px;
 * both at least three buckets, counted on the calendar.
 *
 * Opening pick (k4 G2): Candles open on the lowest rung the geometry can draw. Every entry into
 * Income — mounted on it, switched to it from the line, from Candles or from another view — opens on
 * 1M, clamped into the offered rungs (if 1M is not offered, the offered rung nearest it), and a rung
 * the user picks there holds until Income is left. Without the measured grid every rung is offered,
 * so Candles open on 1D and Income on 1M. B12 pins that rule; every other case that names a rung
 * presses it and waits for it to read as pressed, so no case but B12 depends on the opening pick.
 */
// WHY the 30 s budget: a case chains several 5 s waits, and a red `waitFor` must be able to exhaust
// its own timeout and rethrow the case's assertion instead of dying on the test timeout.
describe('GrowthChart ladder x axis (S7)', {timeout: 30_000}, () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case (as S2a does).
    afterEach(() => setPrivacyEnabled(false));

    /** The two submodes on the ladder, and the rungs (the test-id suffixes). WHY: a typo in a case is a type error, not a 5 s timeout. */
    type Submode = 'candles' | 'income';
    type Rung = '1d' | '3d' | '1w' | '2w' | '1m' | '3m' | '6m' | '1y';

    /** Both ladder submodes. WHY: every defect shows on both, and a fix on one alone must stay red. */
    const SUBMODES: Array<{title: string; submode: Submode}> = [
        {title: 'Candles', submode: 'candles'},
        {title: 'Income', submode: 'income'},
    ];

    /** How many series each submode draws, from its frame. WHY: "no bucket marked" is stated per series, independently of what rendered. */
    const SERIES_COUNT: Record<Submode, number> = {candles: FRAME.candles.length, income: FRAME.income.length};

    /**
     * The 40 days (Thu 2026-01-01 .. Mon 02-09) at 1W: seven ISO weeks. Bucket 0 is the week of Mon Dec 29, cut
     * at Jan 1 (4 of 7 days); 1..5 are whole; 6 is the week of Mon Feb 9, in progress on Feb 9 (1 of 7 days).
     * WHY a literal: the calendar, counted by hand, is the oracle.
     */
    const WEEK_CLOSINGS_40 = ['2026-01-04', '2026-01-11', '2026-01-18', '2026-01-25', '2026-02-01', '2026-02-08', '2026-02-09'];
    const WEEK_BUCKETS_40 = WEEK_CLOSINGS_40.length;
    /** 1M on the 40 days: January (whole) and February (in progress on the 9th). */
    const MONTH_BUCKETS_40 = 2;
    /** 2W on the 40 days: the pairs from Mon Dec 29 (cut at Jan 1), Jan 12, Jan 26, and Feb 9 (in progress). */
    const PAIR_BUCKETS_40 = 4;

    /** 730 days (2024-10-01 .. 2026-09-30) at 1M: 24 calendar months, October 2024 to September 2026. */
    const MONTH_BUCKETS_730 = 24;
    /** The window the B9–B11 cases zoom to: buckets 18..23, April to September 2026, each closing on its month's last day. WHY a literal: the calendar is the oracle. */
    const MONTH_WINDOW_FIRST = 18;
    const MONTH_WINDOW_CLOSINGS = ['2026-04-30', '2026-05-31', '2026-06-30', '2026-07-31', '2026-08-31', '2026-09-30'];
    /** The zoom start whose left edge is bucket 18 of 0..23. WHY: ECharts rounds `pct / 100 × (n − 1)` to a bucket, so this is the window [18..23]. */
    const MONTH_WINDOW_START = (MONTH_WINDOW_FIRST / (MONTH_BUCKETS_730 - 1)) * 100;

    /**
     * The dashboard's preset windows on 2026-10-06, the day of the developer's offer table, each ending that
     * day. WHY built once: `GrowthChart` resets its caches whenever the history array changes identity.
     */
    const WINDOW_FIXTURES = {
        '1M': buildLadderFixture(isoDays(2026, 8, 6, 31)),
        '3M': buildLadderFixture(isoDays(2026, 6, 6, 93)),
        '6M': buildLadderFixture(isoDays(2026, 3, 6, 184)),
        '9M': buildLadderFixture(isoDays(2026, 0, 6, 274)),
        YTD: buildLadderFixture(isoDays(2026, 0, 1, 279)),
        '1Y': buildLadderFixture(isoDays(2025, 9, 6, 366)),
    } as const;
    type PresetWindow = keyof typeof WINDOW_FIXTURES;

    /** The GrowthChart plot widths measured on the dashboard (P&L) on 06/10/2026, by viewport. WHY: the offer is a function of the plot, so these are the widths the developer's table speaks of. */
    const MEASURED_PLOT_PX = {desktop1280: 484, desktop1440: 573, desktop1728: 734, phone390: 279} as const;

    /** What a missing callback reads as in a failure diff. WHY: a named sentinel keeps the red on the assertion, not on a TypeError. */
    const NOT_A_FUNCTION = 'not a function';

    /** The last day of a fixture. WHY: the dashboard serves a window that ends today, so that is the today a case reads on unless it says otherwise. */
    const lastDayOf = (fixture: LadderFixture) => fixture.history[fixture.history.length - 1].date;

    /**
     * Pins the day `todayIso()` reads to `iso`: `Date` alone is faked, at local noon. WHY: which period is
     * current is a function of today; faking only `Date` leaves the timers `waitFor` polls on real, and noon is
     * the same calendar day in every timezone. The precondition reads the local day the way the component does.
     */
    function pinToday(iso: string) {
        vi.useFakeTimers({toFake: ['Date']});
        vi.setSystemTime(new Date(`${iso}T12:00:00`));
        const now = new Date();
        const localDay = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        expect(localDay, `precondition: the clock reads ${iso} in the local calendar`).toBe(iso);
    }

    /**
     * Runs `body` with `setTimeout` faked as well, today still pinned. WHY: a zoom's 200 ms debounce is driven on
     * the fake clock, and the case's day must not fall back to the real one halfway through (vitest carries the
     * faked now into the new clock, and back).
     */
    async function onFakeTimeouts(body: () => Promise<void>) {
        vi.useFakeTimers({toFake: ['Date', 'setTimeout', 'clearTimeout']});
        try {
            await body();
        } finally {
            vi.useFakeTimers({toFake: ['Date']});
        }
    }

    /** Pins today, mounts on `fixture` and walks into a ladder submode (Abs, then P&L, then the submode). WHY: the path a user takes, one full frame at a time, on a stated day. */
    async function enterLadderView(fixture: LadderFixture, submode: Submode, today = lastDayOf(fixture)) {
        pinToday(today);
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

    /** Enters `submode` on `fixture` on `today`, presses `rung` and waits for its `buckets`. WHY: the common opening, settled on facts the case states. */
    async function openRung(fixture: LadderFixture, submode: Submode, rung: Rung, buckets: number, today = lastDayOf(fixture)) {
        const view = await enterLadderView(fixture, submode, today);
        await pressRung(rung);
        await waitForBuckets(buckets);
        return view;
    }

    /** True when a datum is drawn faded: an `itemStyle.opacity` strictly between 0 and 1. WHY: translucent is the decided look of a partial bucket. */
    function isMarkedPartial(datum: unknown): boolean {
        if (datum == null || typeof datum !== 'object' || Array.isArray(datum)) return false;
        const opacity = (datum as {itemStyle?: {opacity?: unknown}}).itemStyle?.opacity;
        return typeof opacity === 'number' && opacity > 0 && opacity < 1;
    }

    /** The indices of the buckets a series draws faded. WHY: a list makes "bucket 0 and no other" one assertion. */
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

    /** A key the file resolves through i18n, as the user reads it. WHY: the rung letters are translations; an unresolved key must fail here, not as a confusing diff. */
    function resolved(key: string): string {
        const text = htmlText(get(_)(key));
        expect(text, `${key} resolves in the file locale`).not.toBe(key);
        return text;
    }

    /** The two lines a ladder bucket can carry under its header. WHY: a typo in a key is a type error. */
    type BucketLineKey = 'chart.tooltip.partialBucket' | 'chart.tooltip.currentBucket';
    const PARTIAL_LINE: BucketLineKey = 'chart.tooltip.partialBucket';
    const CURRENT_LINE: BucketLineKey = 'chart.tooltip.currentBucket';

    /**
     * A bucket line as the user reads it, resolved through i18n with the values the component must pass, never a
     * literal. WHY `htmlText`: the component escapes these lines, so the user reads the resolved text as written,
     * and `htmlText` returns that same text while the catalogue entry holds no markup or entities, as in all four
     * locales today. The markup case is B5's escape block (`withBucketMessage`).
     */
    function bucketLine(key: BucketLineKey, days: number, total: number): string {
        const text = get(_)(key, {values: {days, total}});
        if (text === key) throw new Error(`${key} does not resolve in the file locale`);
        return htmlText(text);
    }

    /** Any line of `key`, whatever its numbers. WHY: an absence check must not be defeated by a line carrying other numbers. Built through `htmlText`, as `bucketLine` is. */
    function bucketLinePattern(key: BucketLineKey): RegExp {
        const text = htmlText(get(_)(key, {values: {days: 'DAYSSLOT', total: 'TOTALSLOT'}}));
        if (!text.includes('DAYSSLOT') || !text.includes('TOTALSLOT')) throw new Error(`${key} did not take its values: ${text}`);
        const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp(`^${escaped.replace('DAYSSLOT', '\\d+').replace('TOTALSLOT', '\\d+')}$`);
    }

    /** The lines of `key` under the header of bucket `index`. WHY: "once" and "never" are then counts on one list. */
    function linesAt(index: number, key: BucketLineKey): string[] {
        const pattern = bucketLinePattern(key);
        return topLevelDivTexts(ladderTooltip(index)).filter((text) => pattern.test(text));
    }

    /** Both lines of every bucket in `indices`. WHY: one assertion states the whole ladder, so a line on the wrong bucket shows beside the missing one. */
    function bucketLines(indices: number[]): Array<{partial: string[]; current: string[]}> {
        return indices.map((index) => ({partial: linesAt(index, PARTIAL_LINE), current: linesAt(index, CURRENT_LINE)}));
    }

    /** `0 .. count − 1`. */
    const indicesTo = (count: number) => Array.from({length: count}, (_unused, index) => index);

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

    /** The x axis of one option, object or array. WHY: ECharts accepts both, and the component may send either. */
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

    /** `value` when it is a function, else null. WHY: an axis may carry a number or nothing where the planner puts a callback. */
    function fn<T>(value: unknown): T | null {
        return typeof value === 'function' ? (value as T) : null;
    }

    /** Calls `call`, turning a throw into a labelled value. WHY: a callback not written for these arguments must show in the diff, not replace it. */
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

    /** B9's zoom onto buckets [18..23], without its call counts. WHY: the opening of B10 and B11 must not assert what B9 pins. */
    async function zoomToMonthWindow() {
        await onFakeTimeouts(() => zoomOnFakeClock(MONTH_WINDOW_START, 100));
    }

    /** Measured grid, 730 days at 1M (24 buckets), window [18..23]. WHY: the one state B10 and B11 start from. */
    async function openMonthWindow(submode: Submode) {
        fakeGeometry.measured = true;
        const view = await openRung(FIXTURE_730, submode, '1m', MONTH_BUCKETS_730);
        await zoomToMonthWindow();
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

    /** The rungs the ladder offers, by test id. WHY: an offered rung is a button; a rung the geometry cannot draw is removed, not disabled. */
    function rungsOffered(): string[] {
        return screen.queryAllByTestId(/^growth-candle-width-/).map((button) => button.getAttribute('data-testid') ?? '');
    }

    /** Test ids of `rungs`, in ladder order. */
    const rungIds = (rungs: readonly Rung[]) => rungs.map((rung) => `growth-candle-width-${rung}`);

    // --- B1-B3: a bucket is a calendar period ---------------------------------------------------

    it('B1 Candles, 40 days, 1W: each candle spans its calendar week — bucket 0 Thu Jan 1..Sun Jan 4, bucket 5 Feb 2..8, bucket 6 the week in progress, Feb 9 alone', async () => {
        // WHY: decision (a), a week runs Monday to Sunday whatever day the series starts or ends on. The quads come by hand
        // from open 500+100i, close 540+100i, low 480+100i, high 560+100i: first open, last close, lowest low, highest high.
        await openRung(FIXTURE_40, 'candles', '1w', WEEK_BUCKETS_40);
        const [candles] = renderedSeries();
        expect([0, 5, 6].map((index) => quadOf(candles.data[index]))).toEqual([
            [500, 840, 480, 860],
            [3700, 4340, 3680, 4360],
            [4400, 4440, 4380, 4460],
        ]);
    });

    it('B2 Income, 40 days, 1W: each bar sums the days its calendar week holds, on each of the six series', async () => {
        // WHY: decision (a) on sums: bucket 0 adds days 0..3 (dividend 4 × 12 + 0+1+2+3 = 54), bucket 5 days 32..38
        // (7 × 12 + 245 = 329), bucket 6 day 39 alone (12 + 39 = 51) — the week in progress holds what has happened.
        await openRung(FIXTURE_40, 'income', '1w', WEEK_BUCKETS_40);
        // Fixed slot order: dividend, interest, costs, deposit, new capital, reinvested.
        expect(renderedSeries().map((entry) => [0, 5, 6].map((index) => pointValue(entry.data[index])))).toEqual([
            [54, 329, 51],
            [18, 266, 42],
            [-22, -273, -43],
            [606, 1295, 189],
            [366, 875, 129],
            [186, 560, 84],
        ]);
    });

    it.each(SUBMODES)('B3 $title, 40 days, 1W: the tooltip header names the rung and the calendar week, days the series lacks included', async ({submode}) => {
        // WHY: decision (d), the header is the period the bucket stands for: bucket 0 is the week of Mon Dec 29 although
        // the series starts on Jan 1, and bucket 6 the week of Feb 9 to 15 although today is its first day.
        await openRung(FIXTURE_40, submode, '1w', WEEK_BUCKETS_40);
        const week = resolved('datePicker.granularity.weeksShort');
        expect([0, 5, 6].map((index) => tooltipHeaderText(ladderTooltip(index)))).toEqual([`1${week} - 2025-12-29 → 2026-01-04`, `1${week} - 2026-02-02 → 2026-02-08`, `1${week} - 2026-02-09 → 2026-02-15`]);
    });

    it.each(SUBMODES)('B3 $title, 40 days, 1M: the header is the calendar month — February to its 28th, although the series stops on the 9th', async ({submode}) => {
        // WHY: decision (d) on the rung users read most: a month is named by its own edges, not by the days with data.
        await openRung(FIXTURE_40, submode, '1m', MONTH_BUCKETS_40);
        const month = resolved('datePicker.granularity.monthsShort');
        expect([0, 1].map((index) => tooltipHeaderText(ladderTooltip(index)))).toEqual([`1${month} - 2026-01-01 → 2026-01-31`, `1${month} - 2026-02-01 → 2026-02-28`]);
    });

    it('B3 Candles, 40 days, 1W: "value at" names the last day with data — Feb 9 for the week in progress, never a day still to come', async () => {
        // WHY: decision (d), a closing level exists only on a day with data. The week of bucket 6 runs to Feb 15, which
        // has not happened; the cut week of bucket 0 ends on a day the series holds.
        await openRung(FIXTURE_40, 'candles', '1w', WEEK_BUCKETS_40);
        const valueAt = (date: string) => htmlText(get(_)('chart.tooltip.valueAt', {values: {date}}));
        const slot = valueAt('DATESLOT');
        if (!slot.includes('DATESLOT')) throw new Error(`chart.tooltip.valueAt did not take its date: ${slot}`);
        const anyValueAt = new RegExp(`^${slot.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace('DATESLOT', '\\d{4}-\\d{2}-\\d{2}')}$`);
        expect([0, 6].map((index) => topLevelDivTexts(ladderTooltip(index)).filter((text) => anyValueAt.test(text)))).toEqual([[valueAt('2026-01-04')], [valueAt('2026-02-09')]]);
    });

    it('B3 Candles, 40 days, 1D: a one-day bucket keeps its plain date as the header', async () => {
        // WHY: decision (d), a day has no span to print; the period form is for wider rungs.
        await openRung(FIXTURE_40, 'candles', '1d', DAY_COUNT);
        expect([0, DAY_COUNT - 1].map((index) => tooltipHeaderText(ladderTooltip(index)))).toEqual(['2026-01-01', '2026-02-09']);
    });

    // --- B4-B5: a partial period is marked and explained; the period in progress is not marked ---

    it('B4 Candles, 40 days: no candle marked at 1D; at 1W only bucket 0, the week cut at Jan 1 — not bucket 6, the week in progress', async () => {
        // WHY: decision (a). A period that is over and cut is not comparable, so it is faded; the week in progress misses
        // only the future, so it is drawn whole. At 1D every day is whole: none is cut, today's included.
        await openRung(FIXTURE_40, 'candles', '1d', DAY_COUNT);
        expect(renderedSeries().map(markedBuckets), '1D: no candle marked').toEqual(Array.from({length: SERIES_COUNT.candles}, () => []));
        await pressRung('1w');
        await waitForBuckets(WEEK_BUCKETS_40);
        expect(renderedSeries().map(markedBuckets), '1W: bucket 0 marked, no other').toEqual(Array.from({length: SERIES_COUNT.candles}, () => [0]));
    });

    it('B4 Income, 40 days, 1W: bucket 0 is marked on each of the six series, the week in progress on none', async () => {
        // WHY: every bar of the cut week under-counts, so every series must say so; the week in progress is not weak, it is unfinished.
        await openRung(FIXTURE_40, 'income', '1w', WEEK_BUCKETS_40);
        expect(renderedSeries().map(markedBuckets)).toEqual(Array.from({length: SERIES_COUNT.income}, () => [0]));
    });

    it.each(SUBMODES)('B4 $title, 1M, ranges read on 2026-05-15: nothing marked on 90 days (three whole months, all over); on 93 days only bucket 3, April, over and cut on the 3rd', async ({submode}) => {
        // WHY: decision (a), the mark follows the calendar and today. A range that ended in the past cuts its last month,
        // and once that month is over the cut is a gap in the series, not the future.
        const view = await openRung(FIXTURE_90, submode, '1m', 3, '2026-05-15');
        expect(renderedSeries().map(markedBuckets), '90 days: every month whole').toEqual(Array.from({length: SERIES_COUNT[submode]}, () => []));

        // One deferred render per effect run: wait for it before pressing, so the press acts on the 93 days.
        const since = setOptionCount();
        await view.rerender(ladderProps(FIXTURE_93));
        await waitFor(() => expect(chartInstances[0].setOptionCalls.slice(since).some((call) => Array.isArray(call.option.series))).toBe(true), {timeout: 5_000});
        await pressRung('1m');
        await waitForBuckets(4);
        expect(renderedSeries().map(markedBuckets), '93 days: bucket 3 marked, no other').toEqual(Array.from({length: SERIES_COUNT[submode]}, () => [3]));
    });

    it.each(SUBMODES)('B4 $title, 93 days, 1M, read on 2026-04-03, its last day: April is the month in progress, and nothing is marked', async ({submode}) => {
        // WHY: decision (a), `current` follows today, not the last day with data: the same three days of April are a whole
        // bucket while April runs. Catches a mark decided by the series alone.
        await openRung(FIXTURE_93, submode, '1m', 4, '2026-04-03');
        expect(renderedSeries().map(markedBuckets)).toEqual(Array.from({length: SERIES_COUNT[submode]}, () => []));
    });

    it.each(SUBMODES)('B4 $title, 9M window on 2026-10-06, 1Y: the year in progress is cut at Jan 6, so it is partial — faded, its line saying 274 of 365 days, not in progress', async ({submode}) => {
        // WHY: decision (a)'s tie-break. The days of 2026 before the window are history the chart does not hold, not the
        // future: the bucket is not comparable although its year is still running, so the partial mark and line win over
        // the in-progress ones. (Without the measured grid every rung is offered, 1Y's single bucket included.)
        await openRung(WINDOW_FIXTURES['9M'], submode, '1y', 1);
        expect({marked: renderedSeries().map(markedBuckets), lines: bucketLines([0])}).toEqual({marked: Array.from({length: SERIES_COUNT[submode]}, () => [0]), lines: [{partial: [bucketLine(PARTIAL_LINE, 274, 365)], current: []}]});
    });

    /** The lines of the seven weeks of the 40 days: the cut week says 4 of 7, the week in progress 1 of 7, the whole weeks nothing. */
    const weekLines40 = () => indicesTo(WEEK_BUCKETS_40).map((index) => ({partial: index === 0 ? [bucketLine(PARTIAL_LINE, 4, 7)] : [], current: index === WEEK_BUCKETS_40 - 1 ? [bucketLine(CURRENT_LINE, 1, 7)] : []}));

    it('B5 Candles, 40 days: at 1D no line on any day, today included; at 1W the cut week says 4 of 7 days and the week in progress 1 of 7, once each', async () => {
        // WHY: the tooltip is where the user learns why a candle is short or unfinished: once, with the bucket's own
        // counts, and never on a whole bucket. A one-day period has nothing in progress to report, so today's 1D candle
        // carries no line (developer, 06/10/2026: «Togli la riga per 1D»); the 1W half is the positive control, the line
        // still on the wider period in progress.
        await openRung(FIXTURE_40, 'candles', '1d', DAY_COUNT);
        expect(bucketLines(indicesTo(DAY_COUNT)), '1D: no line on any day, today included').toEqual(indicesTo(DAY_COUNT).map(() => ({partial: [], current: []})));

        await pressRung('1w');
        await waitForBuckets(WEEK_BUCKETS_40);
        expect(bucketLines(indicesTo(WEEK_BUCKETS_40)), '1W').toEqual(weekLines40());
    });

    it('B5 Income, 40 days, 1W: the cut week says 4 of 7 days and the week in progress 1 of 7, once each; the whole weeks say nothing', async () => {
        // WHY: the Income header drops "value at" (a bar is a sum), so these lines are the one place the two odd weeks are explained.
        await openRung(FIXTURE_40, 'income', '1w', WEEK_BUCKETS_40);
        expect(bucketLines(indicesTo(WEEK_BUCKETS_40))).toEqual(weekLines40());
    });

    it.each(
        SUBMODES.flatMap(({title, submode}) => [
            {title, submode, today: '2026-05-15', state: 'over', partial: true},
            {title, submode, today: '2026-04-03', state: 'in progress', partial: false},
        ]),
    )('B5 $title, 93 days, 1M, read on $today: April ($state) says 3 of 30 days once, on the line of its state, and no other bucket says anything', async ({submode, today, partial}) => {
        // WHY: the counts are the bucket's own (3 days of a 30-day month), and which line carries them is decided by
        // today: the same April is a partial month once it is over, and the month in progress before.
        await openRung(FIXTURE_93, submode, '1m', 4, today);
        const april = bucketLine(partial ? PARTIAL_LINE : CURRENT_LINE, 3, 30);
        expect(bucketLines(indicesTo(4))).toEqual([...indicesTo(3).map(() => ({partial: [], current: []})), {partial: partial ? [april] : [], current: partial ? [] : [april]}]);
    });

    /** The plain word that opens a swapped-in message. WHY: it finds the line whatever the component did to the rest of it, so a red shows what the user read. */
    const LINE_MARKER = 'S7-ESCAPE-LOCK';

    /** A bucket line that is markup if read as HTML: an entity and a tag around the two values. WHY: a translation is data, so both must reach the user as the characters written here. */
    const MARKUP_LOOKING_LINE = `${LINE_MARKER} &lt;b&gt; {days}/{total} <i>x</i>`;

    /**
     * Runs `body` while the current locale's `key` reads `message`, then puts the catalogue's own text back and
     * proves it. WHY: the catalogue is module state shared by every case in the file, so whoever swaps a message
     * restores it, whatever the outcome of the case (as with the privacy flag); `body` is synchronous, so no
     * scheduled render can run while the swap is in place.
     */
    function withBucketMessage(key: BucketLineKey, message: string, body: () => void) {
        const localeCode = get(locale);
        if (!localeCode) throw new Error('no current locale: setupI18n() has not run');
        const leaf = key.split('.')[2];
        // The catalogue's own leaf, read along the same nested path the swap writes.
        const source = () => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), get(dictionary)[localeCode]);
        const resolvedText = () => get(_)(key, {values: {days: 5, total: 7}});
        const original = source();
        if (typeof original !== 'string') throw new Error(`${key} is not a string in the ${localeCode} catalogue`);
        const before = resolvedText();
        addMessages(localeCode, {chart: {tooltip: {[leaf]: message}}});
        try {
            body();
        } finally {
            addMessages(localeCode, {chart: {tooltip: {[leaf]: original}}});
            expect({source: source(), resolved: resolvedText()}, `the ${localeCode} catalogue is restored`).toEqual({source: original, resolved: before});
        }
    }

    it.each(
        SUBMODES.flatMap(({title, submode}) => [
            {title, submode, key: PARTIAL_LINE, index: 0, days: 4},
            {title, submode, key: CURRENT_LINE, index: WEEK_BUCKETS_40 - 1, days: 1},
        ]),
    )('B5 $title, 40 days, 1W: the $key line of bucket $index shows its translation as written, never as markup', async ({submode, key, index, days}) => {
        // WHY: the tooltip is HTML handed to ECharts and a translation is data, so an entity or a tag in either line must
        // reach the user as text, on both return paths of the ladder header (Candles add "value at", Income does not).
        await openRung(FIXTURE_40, submode, '1w', WEEK_BUCKETS_40);
        withBucketMessage(key, MARKUP_LOOKING_LINE, () => {
            const written = get(_)(key, {values: {days, total: 7}});
            expect(written, 'precondition: the swapped-in message resolves, values in, markup untouched').toBe(MARKUP_LOOKING_LINE.replace('{days}', String(days)).replace('{total}', '7'));
            expect(
                topLevelDivTexts(ladderTooltip(index)).filter((text) => text.includes(LINE_MARKER)),
                'exactly one line, shown as written',
            ).toEqual([written]);
        });
    });

    // --- B6-B8: one category axis, labelled by the planner, and an honest offer ----------------

    it('B6 Income, 40 days, measured, 1W: the category axis carries the seven closings, labels each one and draws each separator', async () => {
        // WHY: defects 2 and 3, the axis must name the buckets it draws — Sundays, then Feb 9, the last day of the week
        // in progress. The label strings are the planner's Part A contract on this ICU (A0), dates chosen here, not UI translations.
        fakeGeometry.measured = true;
        await openRung(FIXTURE_40, 'income', '1w', WEEK_BUCKETS_40);
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
                    labels: ['Jan 4', 'Jan 11', 'Jan 18', 'Jan 25', 'Feb 1', 'Feb 8', 'Feb 9'],
                    labelShown: WEEK_CLOSINGS_40.map(() => true),
                    separatorShown: WEEK_CLOSINGS_40.map(() => true),
                });
            },
            {timeout: 5_000},
        );
    });

    it('B7 Income full option: a category axis; dividend, interest and costs in one stack, deposit alone, the two funding series in another; 30% between buckets, 10% between the columns of one', async () => {
        // WHY: defects 3 and 4, and decision (c) of 06/10/2026: bars on a time axis change width with every zoom step, and
        // gaps that are all alike make the columns of neighbouring buckets run together («se sono tutte attaccate non si
        // capisce nulla»), so the gap between buckets is three times the gap between the columns of one.
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
            barCategoryGap: Array.from({length: SERIES_COUNT.income}, () => '30%'),
        });
    });

    it.each([
        {plotWidthPx: 843, barPx: 4.498, offered: ['2w', '1m', '3m'] as Rung[]},
        {plotWidthPx: 844, barPx: 4.503, offered: ['1w', '2w', '1m', '3m'] as Rung[]},
    ])('B7 Income, YTD on 2026-10-06 (41 calendar weeks), measured $plotWidthPx px: the declared gaps make a weekly bar $barPx px, and the offer draws the line at 4.5 px', async ({plotWidthPx, barPx, offered}) => {
        // WHY: decision (c), the offer's arithmetic is the drawing's. A bar is slot × (1 − category gap) / (3 + 2 × bar gap),
        // with the gaps read from the six series as ECharts will, and a rung is offered while that bar is at least 4.5 px:
        // the 41 ISO weeks of YTD (2025-12-29 to 2026-10-11) cross that line between 843 and 844 px. Catches an offer that
        // assumes other gaps than the series declare, another minimum bar, or day counts (ceil(279 / 7) = 40 weeks would
        // offer 1W at 843 px, 4.61 px a bar).
        fakeGeometry.measured = true;
        fakeGeometry.plotWidthPx = plotWidthPx;
        await enterLadderView(WINDOW_FIXTURES.YTD, 'income');
        const percent = (value: unknown) => (typeof value === 'string' && /^\d+%$/.test(value) ? Number(value.slice(0, -1)) / 100 : Number.NaN);
        await waitFor(
            () => {
                const series = (latestFullOption() as unknown as {series: Array<{barGap?: unknown; barCategoryGap?: unknown}>}).series;
                const weeklyBar = ((plotWidthPx / 41) * (1 - percent(series[0]?.barCategoryGap))) / (3 + 2 * percent(series[0]?.barGap));
                // The offer is complete once it reflects the measured plot: 6M and 1Y (two and one buckets) are gone.
                expect({weeklyBarPx: Math.round(weeklyBar * 1000) / 1000, offered: rungsOffered()}).toEqual({weeklyBarPx: barPx, offered: rungIds(offered)});
            },
            {timeout: 5_000},
        );
    });

    /**
     * The developer's table of 06/10/2026: the Income rungs offered on each preset window at each measured plot.
     * WHY literals: they are the decision's own figures — three bars of 4.5 px in a bucket (a slot of at least
     * 20.57 px) and at least three buckets, counted on the calendar. The finest offered rung is the table's
     * "minimum Income rung".
     */
    const INCOME_OFFER_TABLE: Array<{preset: PresetWindow; plot: keyof typeof MEASURED_PLOT_PX; offered: Rung[]}> = [
        {preset: '1M', plot: 'desktop1280', offered: ['1w', '2w']},
        {preset: '1M', plot: 'desktop1440', offered: ['1w', '2w']},
        {preset: '1M', plot: 'desktop1728', offered: ['1w', '2w']},
        {preset: '1M', plot: 'phone390', offered: ['1w', '2w']},
        {preset: '3M', plot: 'desktop1280', offered: ['1w', '2w', '1m']},
        {preset: '3M', plot: 'desktop1440', offered: ['1w', '2w', '1m']},
        {preset: '3M', plot: 'desktop1728', offered: ['1w', '2w', '1m']},
        {preset: '3M', plot: 'phone390', offered: ['2w', '1m']},
        {preset: '6M', plot: 'desktop1280', offered: ['2w', '1m', '3m']},
        {preset: '6M', plot: 'desktop1440', offered: ['1w', '2w', '1m', '3m']},
        {preset: '6M', plot: 'desktop1728', offered: ['1w', '2w', '1m', '3m']},
        {preset: '6M', plot: 'phone390', offered: ['1m', '3m']},
        {preset: '9M', plot: 'desktop1280', offered: ['2w', '1m', '3m']},
        {preset: '9M', plot: 'desktop1440', offered: ['2w', '1m', '3m']},
        {preset: '9M', plot: 'desktop1728', offered: ['2w', '1m', '3m']},
        {preset: '9M', plot: 'phone390', offered: ['1m', '3m']},
        {preset: 'YTD', plot: 'desktop1280', offered: ['2w', '1m', '3m']},
        {preset: 'YTD', plot: 'desktop1440', offered: ['2w', '1m', '3m']},
        {preset: 'YTD', plot: 'desktop1728', offered: ['2w', '1m', '3m']},
        {preset: 'YTD', plot: 'phone390', offered: ['1m', '3m']},
        {preset: '1Y', plot: 'desktop1280', offered: ['1m', '3m', '6m']},
        {preset: '1Y', plot: 'desktop1440', offered: ['2w', '1m', '3m', '6m']},
        {preset: '1Y', plot: 'desktop1728', offered: ['2w', '1m', '3m', '6m']},
        {preset: '1Y', plot: 'phone390', offered: ['1m', '3m', '6m']},
    ];

    it.each(INCOME_OFFER_TABLE.map((row) => ({...row, px: MEASURED_PLOT_PX[row.plot], finest: row.offered[0]})))('B8 Income, $preset window on 2026-10-06, $plot plot ($px px): offers $offered, the finest $finest, and presses one of them', async ({preset, px, offered}) => {
        // WHY: decision (c) at the geometries it was taken on. At nine months 1W makes 40 bars of 12–18 px, too narrow, and
        // 2W 21 of 23–35 px (desktop) — «a 9 mesi, 2S mi paiono strette ma sono più accettabili»; on a phone only months fit.
        // Which offered rung opens is B12's subject, so here exactly one of them is pressed.
        fakeGeometry.measured = true;
        fakeGeometry.plotWidthPx = px;
        await enterLadderView(WINDOW_FIXTURES[preset], 'income');
        await waitFor(() => expect({offered: rungsOffered(), pressed: pressedAmong(rungsOffered()).length}).toEqual({offered: rungIds(offered), pressed: 1}), {timeout: 5_000});
    });

    it.each([
        {title: 'Income', submode: 'income' as Submode, offered: ['1m', '3m', '6m', '1y'] as Rung[]},
        {title: 'Candles', submode: 'candles' as Submode, offered: ['1w', '2w', '1m', '3m', '6m', '1y'] as Rung[]},
    ])('B8 $title, 730 days, measured 527 px plot: offers $offered — 1Y draws three calendar years, 2024, 2025 and 2026', async ({submode, offered}) => {
        // WHY: the offer counts the buckets the ladder draws. 2024-10-01..2026-09-30 touches three calendar years, so 1Y has
        // its three bodies; 730 / 365 days made two. Candle bodies need 2.5 px (3D: 244 bodies of 2.16 px), Income bars
        // 4.5 px (2W: 53 buckets, bars of 2.17 px).
        fakeGeometry.measured = true;
        await enterLadderView(FIXTURE_730, submode);
        await waitFor(() => expect({offered: rungsOffered(), pressed: pressedAmong(rungsOffered()).length}).toEqual({offered: rungIds(offered), pressed: 1}), {timeout: 5_000});
    });

    it('B8 Candles, 9M window on 2026-10-06, 1440 px plot (573 px): offers 3D to 3M — 274 daily bodies of 2.09 px do not fit, 92 triples do', async () => {
        // WHY: the candles keep their own floor, 2.5 px a body, on the same calendar counts: 1D is the only rung below it
        // here, and 6M and 1Y (two halves, one year) are under three bodies.
        fakeGeometry.measured = true;
        fakeGeometry.plotWidthPx = MEASURED_PLOT_PX.desktop1440;
        await enterLadderView(WINDOW_FIXTURES['9M'], 'candles');
        await waitFor(() => expect({offered: rungsOffered(), pressed: pressedAmong(rungsOffered()).length}).toEqual({offered: rungIds(['3d', '1w', '2w', '1m', '3m']), pressed: 1}), {timeout: 5_000});
    });

    // --- B9-B11: the user's window is kept ------------------------------------------------------

    it.each(SUBMODES)('B9 $title, 730 days, measured, 1M: a zoom re-plans the labels once, as an {xAxis}-only update, and the same zoom again does not', async ({submode}) => {
        // WHY: defects 2 and 6, the labels must follow the visible window [18..23], April to September 2026; the update
        // must not carry dataZoom (it would fight the gesture), and an unchanged plan must not redraw.
        fakeGeometry.measured = true;
        await openRung(FIXTURE_730, submode, '1m', MONTH_BUCKETS_730);
        expect(chartInstances).toHaveLength(1);
        const chart = chartInstances[0];
        await onFakeTimeouts(async () => {
            const before = chart.setOptionCalls.length;
            await zoomOnFakeClock(MONTH_WINDOW_START, 100);
            expect(vi.getTimerCount(), 'no timer pending 1000 ms after the zoom').toBe(0);
            const added = chart.setOptionCalls.slice(before);
            expect(added, 'exactly one new setOption call after the zoom').toHaveLength(1);
            const format = fn<LabelFormatter>(xAxisOf(added[0].option)?.axisLabel?.formatter);
            expect({
                keys: Object.keys(added[0].option),
                labels: MONTH_WINDOW_CLOSINGS.map((date, offset) => (format ? attempt(() => format(date, MONTH_WINDOW_FIRST + offset)) : NOT_A_FUNCTION)),
            }).toEqual({keys: ['xAxis'], labels: ['Apr 30', 'May 31', 'Jun 30', 'Jul 31', 'Aug 31', 'Sep 30']});

            const afterFirst = chart.setOptionCalls.length;
            await zoomOnFakeClock(MONTH_WINDOW_START, 100);
            expect(vi.getTimerCount(), 'no timer pending 1000 ms after the repeated zoom').toBe(0);
            expect(chart.setOptionCalls.slice(afterFirst), 'no new setOption call for the same window').toHaveLength(0);
        });
    });

    it.each([
        {title: 'Candles', submode: 'candles' as Submode, rung: '2w' as Rung, lastIndex: 52, startBucket: 39},
        {title: 'Income', submode: 'income' as Submode, rung: '3m' as Rung, lastIndex: 7, startBucket: 6},
    ])('B10 $title, 730 days, measured: from 1M on [18..23], pressing $rung puts the window on the bucket that holds its first day, 2026-04-01', async ({submode, rung, lastIndex, startBucket}) => {
        // WHY: defect 6, a rung change must keep what the user was looking at. The window starts on April 1, which 2W holds
        // in the pair of Mar 23..Apr 5 (bucket 39 of 0..52) and 3M in the second quarter (bucket 6 of 0..7). Income cannot
        // draw 2W on this plot (53 bars of 2.2 px, decision (c)), so it presses the quarter.
        await openMonthWindow(submode);
        const since = setOptionCount();
        await pressRung(rung);
        expect(zoomBucket(await firstZoomAfter(since), lastIndex)).toEqual({startBucket, end: 100});
    });

    /** Runs `trigger` on the [18..23] window and checks that the redraw keeps it, in the call and in the chart. WHY: the one check the three B11 triggers share. */
    async function expectWindowKeptAcross(trigger: () => unknown) {
        expect(chartInstances).toHaveLength(1);
        const chart = chartInstances[0];
        const lastIndex = MONTH_BUCKETS_730 - 1;
        expect(zoomBucket(firstZoomOf(chart.getOption().dataZoom), lastIndex), 'precondition: the window is [18..23]').toEqual({startBucket: MONTH_WINDOW_FIRST, end: 100});
        const since = chart.setOptionCalls.length;
        await trigger();
        const call = zoomBucket(await firstZoomAfter(since), lastIndex);
        expect({call, chart: zoomBucket(firstZoomOf(chart.getOption().dataZoom), lastIndex)}).toEqual({call: {startBucket: MONTH_WINDOW_FIRST, end: 100}, chart: {startBucket: MONTH_WINDOW_FIRST, end: 100}});
    }

    it('B11 Income, 730 days, 1M on [18..23]: the privacy toggle keeps the window', async () => {
        // WHY: defect 6, the privacy toggle redraws the whole option, and that redraw threw the user's window away.
        await openMonthWindow('income');
        await expectWindowKeptAcross(() => setPrivacyEnabled(true));
    });

    it('B11 Income, 730 days, 1M on [18..23]: a re-fetch of the same period keeps the window', async () => {
        // WHY: defect 6, a sync hands a NEW history array with the same dates: the period (first|last date) is unchanged, so the window must be too.
        const view = await openMonthWindow('income');
        await expectWindowKeptAcross(() => view.rerender({history: FIXTURE_730.history.map((point) => ({...point}))}));
    });

    it('B11 Income, 730 days, 1M on [18..23]: a locale change keeps the window', async () => {
        // WHY: defect 6, switching the UI language redraws the labels, and must not move the window.
        await openMonthWindow('income');
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

    it('B11 control, Income, 730 days, 1M on [18..23]: a history of another period resets the window to the whole range', async () => {
        // WHY: gives the three B11 cases their teeth: a new period must NOT keep the old window, so "kept" cannot come from a component that never resets.
        const view = await openMonthWindow('income');
        const since = setOptionCount();
        await view.rerender({history: FIXTURE_730.history.slice(30)});
        const zoom = await firstZoomAfter(since);
        expect({start: zoom?.start, end: zoom?.end}).toEqual({start: 0, end: 100});
    });

    // --- B12: the rung the ladder opens on (k4 G2) ----------------------------------------------

    /** Waits until `rung` is the one rung pressed and every series draws `buckets` buckets. WHY both: the pressed button is what the user reads, the buckets what the chart draws. */
    async function expectOnRung(rung: Rung, buckets: number) {
        await waitFor(
            () => {
                const series = renderedSeries();
                expect(series.length, 'a series array was drawn').toBeGreaterThan(0);
                expect({pressed: pressedAmong(rungsOffered()), buckets: series.map((entry) => entry.data.length)}).toEqual({pressed: [`growth-candle-width-${rung}`], buckets: series.map(() => buckets)});
            },
            {timeout: 5_000},
        );
    }

    it('B12 Income, 40 days, entered from the line: opens on 1M, which every rung being offered leaves unclamped', async () => {
        // WHY: k4 G2 (developer, 05/10/2026: «facciamo che il bucket di default è 1M»). A week of personal cash
        // flow is mostly empty bars; a month is the bucket a reader compares. Catches the ladder's own opening
        // rule, the lowest offered rung (1W here), left on Income.
        await enterLadderView(FIXTURE_40, 'income');
        // Precondition: 1M is offered, so no clamp is in play.
        expect(rungsOffered()).toContain('growth-candle-width-1m');
        await expectOnRung('1m', MONTH_BUCKETS_40);
    });

    it('B12 Income, 40 days, entered from Candles: opens on 1M on every entry, whichever rung the candles were on', async () => {
        // WHY: k4 G2, "every entry into Income". Switching Candles ↔ Income keeps the width today, so Income
        // inherits the candles' rung: climbed from their 1D to its 1W floor, or kept as it was from 3M. Catches
        // the width carried over, and a floor raised to 1M instead of an opening (3M sits above it and would
        // be kept).
        const view = await enterLadderView(FIXTURE_40, 'candles');
        await fireEvent.click(view.getByTestId('growth-pnl-submode-income'));
        await waitForFrame(FRAME.income);
        await expectOnRung('1m', MONTH_BUCKETS_40);

        await fireEvent.click(view.getByTestId('growth-pnl-submode-candles'));
        await waitForFrame(FRAME.candles);
        await pressRung('3m');
        await waitForBuckets(1);
        await fireEvent.click(view.getByTestId('growth-pnl-submode-income'));
        await waitForFrame(FRAME.income);
        await expectOnRung('1m', MONTH_BUCKETS_40);
    });

    it('B12 Income, 40 days, restored from the persisted submode: opens on 1M from its first frame', async () => {
        // WHY: k4 G2, "mounting on Income". The persisted submode (S5) brings a user straight into Income,
        // and the first frame must already be the month: weeks first would flash, then jump. Catches the
        // opening applied on a click only, or only after a first draw.
        storage.set(MODE_KEY, 'pnl');
        storage.set(SUBMODE_KEY, 'income');
        pinToday(lastDayOf(FIXTURE_40));
        render(GrowthChart, {props: ladderProps(FIXTURE_40)});
        await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        await expectOnRung('1m', MONTH_BUCKETS_40);
        const [first] = fullOptionsSince(0) as unknown as Array<{series: SeriesUpdate[]}>;
        expect(
            first.series.map((entry) => entry.data.length),
            'the first frame draws the 1M buckets',
        ).toEqual(first.series.map(() => MONTH_BUCKETS_40));
    });

    it('B12 Income, 40 days, re-entered from another view: opens on 1M again, not on the rung it was left on', async () => {
        // WHY: k4 G2, "or from another mode". Leaving P&L for Abs leaves Income, so coming back is a new entry.
        // Catches the rung kept across the round trip, which the ladder does today because it reconciles only
        // while it is on screen.
        const view = await enterLadderView(FIXTURE_40, 'income');
        await pressRung('3m');
        await waitForBuckets(1);
        await fireEvent.click(view.getByTestId('growth-toggle-eur'));
        await waitForFrame(FRAME.abs);
        await fireEvent.click(view.getByTestId('growth-toggle-pnl'));
        await waitForFrame(FRAME.income);
        // Precondition: P&L comes back on Income, the submode the user left it on.
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        await expectOnRung('1m', MONTH_BUCKETS_40);
    });

    it('B12 Income, 40 days, measured 527 px plot: 1M makes two bars, under three, so it is not offered, and Income opens on 2W, the offered rung nearest it', async () => {
        // WHY: k4 G2's clamp. A short history cannot draw three monthly bars and the ladder never offers what it
        // cannot draw (B8), so the opening takes the offered rung nearest 1M: the offered rungs are contiguous,
        // so here the highest below it. Catches the ladder's own opening (1W, the lowest offered), and a 1M
        // drawn although it is not offered.
        fakeGeometry.measured = true;
        await enterLadderView(FIXTURE_40, 'income');
        // Precondition: the measured plot offers 1W and 2W only (1M: 2 bars; 3M and up: 1).
        await waitFor(() => expect(rungsOffered()).toEqual(rungIds(['1w', '2w'])), {timeout: 5_000});
        await expectOnRung('2w', PAIR_BUCKETS_40);
    });

    it('B12 Income, 1M window on 2026-10-06, 1440 px plot (573 px): September and October are two months, under three, so Income opens on 2W, the offered rung nearest 1M', async () => {
        // WHY: the developer's table on the shortest preset — «1M → 1W everywhere, Income opens on 2W there» — and
        // the clamp on calendar counts: 2026-09-06..10-06 touches two months but four pairs of weeks.
        fakeGeometry.measured = true;
        fakeGeometry.plotWidthPx = MEASURED_PLOT_PX.desktop1440;
        await enterLadderView(WINDOW_FIXTURES['1M'], 'income');
        await waitFor(() => expect(rungsOffered()).toEqual(rungIds(['1w', '2w'])), {timeout: 5_000});
        await expectOnRung('2w', 4);
    });

    it.each([
        {title: 'Candles open on their finest drawable rung, 3D (92 triples)', submode: 'candles' as Submode, rung: '3d' as Rung, buckets: 92},
        {title: 'Income opens on 1M (ten months), above 2W, its finest', submode: 'income' as Submode, rung: '1m' as Rung, buckets: 10},
    ])('B12 9M window on 2026-10-06, 1440 px plot (573 px): $title', async ({submode, rung, buckets}) => {
        // WHY: both opening rules on the measured offer of B8 — Candles from 3D, Income from 2W, 1M drawable in both.
        // Catches Income opening on its lowest drawable rung (2W), and Candles moved off theirs.
        fakeGeometry.measured = true;
        fakeGeometry.plotWidthPx = MEASURED_PLOT_PX.desktop1440;
        await enterLadderView(WINDOW_FIXTURES['9M'], submode);
        await expectOnRung(rung, buckets);
    });

    it('B12 Candles, 40 days: open on their lowest offered rung, 1D without the measured grid', async () => {
        // WHY: k4 G2 moves Income's opening only; Candles keep theirs, the finest detail the geometry can
        // honour. Catches the 1M opening applied to every entry into the ladder.
        await enterLadderView(FIXTURE_40, 'candles');
        await expectOnRung('1d', DAY_COUNT);
    });

    it('B12 Income, 40 days: a rung the user picks holds across redraws — the privacy toggle, a re-fetch of the same period — while Income stays on screen', async () => {
        // WHY: k4 G2 opens Income on 1M and stops there: inside Income the user's pick holds until they leave
        // it. Catches an opening that fires on every draw rather than on an entry: the full rebuild of the
        // privacy toggle, or a re-fetch (a new history array of the same period), would throw the pick away.
        const view = await enterLadderView(FIXTURE_40, 'income');
        await pressRung('2w');
        await expectOnRung('2w', PAIR_BUCKETS_40);

        const beforePrivacy = setOptionCount();
        setPrivacyEnabled(true);
        await fullOptionAfter(beforePrivacy);
        await expectOnRung('2w', PAIR_BUCKETS_40);

        const beforeRefetch = setOptionCount();
        await view.rerender({history: FIXTURE_40.history.map((point) => ({...point}))});
        await waitFor(() => expect(chartInstances[0].setOptionCalls.slice(beforeRefetch).some((call) => Array.isArray(call.option.series))).toBe(true), {timeout: 5_000});
        await expectOnRung('2w', PAIR_BUCKETS_40);
    });

    // --- B13: the ladder memo knows the day -----------------------------------------------------

    /** Mon 2026-09-07 .. Sun 10-04: four whole ISO weeks, the last one ending on a Sunday. WHY built once: B13 must redraw on the very same inputs. */
    const FOUR_WEEKS_TO_SUNDAY = buildLadderFixture(isoDays(2026, 8, 7, 28));

    /** What the last bucket shows: its line under the header (`null` for none), and whether it is drawn faded. */
    interface LastBucketShows {
        line: {key: BucketLineKey; days: number; total: number} | null;
        faded: boolean;
    }

    const B13_CASES: Array<{title: string; submode: Submode; fixture: LadderFixture; rung: Rung; buckets: number; yesterday: string; today: string; before: LastBucketShows; after: LastBucketShows}> = [
        {
            title: 'Candles, 1W, four weeks to Sun Oct 4, read on that Sunday and then on Monday Oct 5: the week Sep 28..Oct 4 drops «In progress: 7 of 7 days» and stays unfaded, a whole week now over',
            submode: 'candles',
            fixture: FOUR_WEEKS_TO_SUNDAY,
            rung: '1w',
            buckets: 4,
            yesterday: '2026-10-04',
            today: '2026-10-05',
            before: {line: {key: CURRENT_LINE, days: 7, total: 7}, faded: false},
            after: {line: null, faded: false},
        },
        {
            title: 'Income, 1M, the 93 days to Apr 3, read on Apr 30 and then on May 1: April turns from «In progress: 3 of 30 days», unfaded, to «Partial: 3 of 30 days», faded',
            submode: 'income',
            fixture: FIXTURE_93,
            rung: '1m',
            buckets: 4,
            yesterday: '2026-04-30',
            today: '2026-05-01',
            before: {line: {key: CURRENT_LINE, days: 3, total: 30}, faded: false},
            after: {line: {key: PARTIAL_LINE, days: 3, total: 30}, faded: true},
        },
    ];

    it.each(B13_CASES)('B13 $title', async ({submode, fixture, rung, buckets, yesterday, today, before, after}) => {
        // WHY: whether a period is in progress is a function of the day, and the ladder memo answers a redraw on the same
        // inputs from its cache. A page left open past midnight redraws — a privacy toggle, a resize, a rung press — with no
        // new history; a memo keyed on the inputs alone kept yesterday's «In progress» line, and withheld the mark a cut
        // period earns once it is over.
        await openRung(fixture, submode, rung, buckets, yesterday);
        const last = buckets - 1;
        const shows = () => ({lines: bucketLines([last]), faded: renderedSeries().map((series) => markedBuckets(series).includes(last))});
        const expected = ({line, faded}: LastBucketShows) => {
            const text = line === null ? [] : [bucketLine(line.key, line.days, line.total)];
            return {lines: [{partial: line?.key === PARTIAL_LINE ? text : [], current: line?.key === CURRENT_LINE ? text : []}], faded: Array.from({length: SERIES_COUNT[submode]}, () => faded)};
        };
        expect(shows(), `precondition, on ${yesterday}: the last bucket is the period in progress`).toEqual(expected(before));

        // Midnight passes; the inputs stay the very same object. The redraw must read the new day.
        pinToday(today);
        const since = setOptionCount();
        setPrivacyEnabled(true);
        await fullOptionAfter(since);
        expect(
            renderedSeries().map((entry) => entry.data.length),
            'the redraw drew the same buckets',
        ).toEqual(renderedSeries().map(() => buckets));
        expect(shows(), `on ${today}`).toEqual(expected(after));
    });
});

// =============================================================================
// S7b — the money axis ticks: distinct, in the locale's glyphs, the fixed edge unlabelled
// =============================================================================

/**
 * Every money view (Abs, P&L line, Candles, Income) labels its y axis through one formatter,
 * chosen when the full option is built. Three decisions shape it, and each has its cases.
 *
 * D18, distinct ticks. ECharts can space ticks half a thousand apart, and a formatter that
 * rounded the scaled value to whole thousands printed `5k 6k 6k 7k 7k 8k 8k`. Two ticks shared
 * each label, so the scale seemed to jump. A label prints the scaled value exactly (`5.5k`,
 * `1.25M`), and a whole value with no decimals (`2k`, `1M`).
 *
 * D23, the locale's glyphs. The number and its minus come from `toLocaleString`, so a Swedish
 * axis writes `−1,5k`, with U+2212 and a decimal comma. A minus written by hand is a hyphen in
 * every locale, and in Node's default locale the locale's own minus is a hyphen too. So the
 * Swedish cases force the call to a locale whose minus differs, and pin that glyph as a literal:
 * the glyph is the subject. Every other literal here is pinned under a forced en-US.
 *
 * D25, the edge the chart fixes. The axis `min` is a callback that leaves 8% of the range below
 * the data, and ECharts labels that edge with its raw value: exact formatting would print it as
 * `-4.152k`. Decision B hides that one label and keeps the edge where it is. Income draws bars,
 * so it keeps ECharts' default instead: an axis that includes zero, like any bar chart, and no
 * hidden label. Its two keys are present and `undefined`, never omitted. The full rebuild
 * replaces `series` and `xAxis` but MERGES `yAxis` into the previous one, so an omitted key would
 * keep the line's callback and hidden label after a switch to Income.
 *
 * k4 G1 (developer review, 05/10/2026), the edge measured anyway. Hidden is not enough:
 * `grid.containLabel` still measures the hidden edge label, and D18 prints the raw edge in full
 * (`55,588k` where a tick reads `55k`), so the Abs and P&L plots started further right than their
 * labels needed — 82 px instead of 55 on real ECharts 6 at 800×300. ECharts calls the formatter as
 * `formatter(value, index)`, the lowest tick at index 0, so in every view with the computed edge
 * that label is blank, masked or not, while every other tick, and a call with the value alone (as
 * the S2a cases make), print as before. Income keeps its index-0 label: there it is a real tick.
 */
// WHY the 30 s budget: a case walks several views, each behind a 5 s wait, and a red `waitFor`
// must be able to exhaust its own timeout and rethrow the case's assertion instead of dying on
// the test timeout (as S7 does).
describe('GrowthChart money axis ticks (S7b: D18, D23, D25)', {timeout: 30_000}, () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case (as S2a does).
    afterEach(() => setPrivacyEnabled(false));

    /** Tick sequences ECharts lays out on a money axis, with what each must print in en-US. WHY literals: the exact labels are the subject, under a forced locale. */
    const TICKS_EN = [
        {values: [5_000, 5_500, 6_000, 6_500, 7_000, 7_500, 8_000], labels: ['5k', '5.5k', '6k', '6.5k', '7k', '7.5k', '8k']},
        {values: [1_000, 1_500, 2_000, 2_500], labels: ['1k', '1.5k', '2k', '2.5k']},
        {values: [900, 950, 1_000, 1_050], labels: ['900', '950', '1k', '1.05k']},
        {values: [1_000_000, 1_250_000, 1_500_000, 1_750_000, 2_000_000], labels: ['1M', '1.25M', '1.5M', '1.75M', '2M']},
        {values: [-3_000, -1_500, 0, 1_500, 3_000], labels: ['-3k', '-1.5k', '0', '1.5k', '3k']},
    ];

    /** What `format` prints for each sequence in en-US, and whether those labels are distinct. WHY both: the literals pin this formatting, the property holds for any that replaces it. */
    function readTicks(format: AxisFormatter, sequences: Array<{values: number[]}>) {
        return inLocale('en-US', () =>
            sequences.map(({values}) => {
                const labels = values.map((value) => format(value));
                return {labels, distinct: new Set(labels).size === labels.length};
            }),
        );
    }

    /** `-0` as written. WHY: `String(-0)` is `'0'`, which would hide which zero a line of the diff is about. */
    const show = (value: number) => (Object.is(value, -0) ? '-0' : String(value));

    /** What ECharts hands an axis `min` callback: the extent of the data on that axis. */
    type AxisMin = (extent: {min: number; max: number}) => number;

    /** The extent the edge cases hand the callback. WHY: data from -3200 to 8700 leaves an edge no tick lands on. */
    const EXTENT = {min: -3_200, max: 8_700};

    /** What a callback edge reads as in a failure diff. WHY: a named sentinel keeps the red on the assertion, not on a TypeError. */
    const NOT_A_CALLBACK = 'not a callback';

    /** The lower edge of the y axis on one full rebuild: whether `min` is a callback, where it puts the edge on `EXTENT`, and whether that edge is labelled. */
    function lowerEdgeOf(option: FullOption) {
        const {min, axisLabel} = option.yAxis;
        return {
            minIsCallback: typeof min === 'function',
            edge: typeof min === 'function' ? (min as AxisMin)(EXTENT) : NOT_A_CALLBACK,
            showMinLabel: axisLabel.showMinLabel,
        };
    }

    /** The lower edge every view but Income must keep. WHY a literal: floor(-3200 - 11900 × 0.08) = -4152, counted by hand, is the oracle that the edge did not move. */
    const FIXED_EDGE = {minIsCallback: true, edge: -4_152, showMinLabel: false};

    it('D18: prints every tick of a money axis exactly, so no two ticks share a label, in Abs and in the P&L line', async () => {
        // WHY: D18. `toFixed(0)` on thousands printed `5k 6k 6k 7k 7k 8k 8k` for ticks half a
        // thousand apart, and `toFixed(1)` on millions printed `1.3M` for 1.25M: the axis
        // repeated labels, and the ones it kept sat at the wrong values. Catches any rounding of
        // the scaled value to a fixed number of decimals. The P&L line is a separate full
        // rebuild: one sequence proves it hands ECharts the same money formatter, not an older
        // one.
        expect(isPrivacyEnabled()).toBe(false);
        const {getByTestId} = render(GrowthChart, {props: {history: HISTORY}});

        const absOption = await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        const abs = readTicks(absOption.yAxis.axisLabel.formatter, TICKS_EN);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        const lineOption = await waitForFrame(FRAME.pnlLine);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        const pnlLine = readTicks(lineOption.yAxis.axisLabel.formatter, TICKS_EN.slice(0, 1));

        const expected = TICKS_EN.map(({labels}) => ({labels, distinct: true}));
        expect({abs, pnlLine}).toEqual({abs: expected, pnlLine: expected.slice(0, 1)});
    });

    it('D18: prints a whole scaled value with no decimals (2k, 20k, 1M, 900), and a zero or a negative zero as 0', async () => {
        // WHY: exact formatting must not swing to the other extreme. `1.0M` pads a label that
        // reads no differently without it, and a negative zero printed `-0` invents a loss on the
        // zero line. Catches `toFixed(1)` kept on the millions, a fixed minimum of decimals, and
        // a zero test that lets `-0` through to `toLocaleString`.
        expect(isPrivacyEnabled()).toBe(false);
        render(GrowthChart, {props: {history: HISTORY}});
        const axis = (await waitForFrame(FRAME.abs)).yAxis.axisLabel.formatter;

        const singles = inLocale('en-US', () => [2_000, 20_000, 1_000_000, 1_300_000, 900, -5_000, 0, -0].map((value) => `${show(value)} → ${axis(value)}`));
        expect(singles).toEqual(['2000 → 2k', '20000 → 20k', '1000000 → 1M', '1300000 → 1.3M', '900 → 900', '-5000 → -5k', '0 → 0', '-0 → 0']);
    });

    it("D23: writes the locale's minus and decimal comma on the money axis, in the clear and masked: U+2212 in sv-SE", async () => {
        // WHY: D23 on the axis. A minus written by hand is a hyphen in every locale, and in Node's
        // default locale the locale's own minus is a hyphen too, so no host-locale case can tell
        // the two apart. Forcing the call the formatter makes, `Number.prototype.toLocaleString`,
        // to a locale whose minus is U+2212 can. Catches a hand-written `-` in the clear label
        // and in front of the mask, and a decimal point written by hand where the locale writes
        // a comma. The glyphs are literals on purpose: they are the subject.
        // Precondition: this Node has Swedish locale data and writes U+2212 there. Without it the
        // forced locale would fall back in silence and the check would prove nothing.
        expect(leadingSign(axisNumber(-5, SWEDISH))).toBe('\u2212');
        expect(isPrivacyEnabled()).toBe(false);
        render(GrowthChart, {props: {history: HISTORY}});
        const clearAxis = (await waitForFrame(FRAME.abs)).yAxis.axisLabel.formatter;
        const clear = inLocale(SWEDISH, () => [-5_000, -1_500, 1_500, -0].map((value) => clearAxis(value)));

        const beforeOn = setOptionCount();
        setPrivacyEnabled(true);
        const maskedAxis = (await fullOptionAfter(beforeOn)).yAxis.axisLabel.formatter;
        const masked = inLocale(SWEDISH, () => [-5_000, 1_500, 0].map((value) => maskedAxis(value)));

        expect({clear, masked}).toEqual({
            clear: ['\u22125k', '\u22121,5k', '1,5k', '0'],
            masked: [`\u2212${PRIVACY_PLACEHOLDER}`, PRIVACY_PLACEHOLDER, PRIVACY_PLACEHOLDER],
        });
    });

    it('D25: keeps the lower edge where it was and hides its label, in Abs, P&L line, Candles and %', async () => {
        // WHY: D25, decision B. ECharts labels the edge a `min` callback fixes with its raw
        // value, which the exact labels of D18 would print as `-4.152k` under a round scale.
        // Catches that label left shown in any of the four views. Catches too the opposite fix,
        // the callback dropped or changed, which would move the edge: the axis would start from
        // a nice number, or hug the data. One builder serves all four views, so walking them all
        // catches a condition that hides the label in some views only. Income, the one view whose
        // edge goes, is the next case.
        expect(isPrivacyEnabled()).toBe(false);
        const {getByTestId} = render(GrowthChart, {props: ladderProps(FIXTURE_40)});

        const abs = lowerEdgeOf(await waitForFrame(FRAME.abs));
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        const pnlLine = lowerEdgeOf(await waitForFrame(FRAME.pnlLine));
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);

        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        const candles = lowerEdgeOf(await waitForFrame(FRAME.candles));
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-candles']);

        // % comes last: it draws three lines, the P&L line's frame, so entering it from the
        // candles leaves no earlier option it could be mistaken for. Its barrier is its own
        // formatter, whose label reads the same in every locale.
        expect(getByTestId('growth-toggle-pct')).toBeEnabled();
        await fireEvent.click(getByTestId('growth-toggle-pct'));
        await waitFor(() => expect(latestFullOption().yAxis.axisLabel.formatter(12.3)).toBe('12.3%'), {timeout: 5_000});
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-pct']);
        const pct = lowerEdgeOf(latestFullOption());

        expect({abs, pnlLine, candles, pct}).toEqual({abs: FIXED_EDGE, pnlLine: FIXED_EDGE, candles: FIXED_EDGE, pct: FIXED_EDGE});
    });

    it("D25: Income hands ECharts min and showMinLabel present as undefined, so the yAxis merge cannot keep the line's edge, and the line gets both back", async () => {
        // WHY: D25 for bars. Bars stand on zero, so Income keeps ECharts' default axis, which
        // includes zero. The trap is the merge: the full rebuild merges `yAxis` into the previous
        // option, so an Income option that merely OMITS `min` and `showMinLabel` keeps the
        // line's callback and hidden label in the chart. On real ECharts 6, line then bars gave an
        // extent of [-888, 12000] with the keys omitted, and [0, 12000] with them set to
        // `undefined`. The recorder merges shallowly and cannot show that, so the guard is on the
        // recorded option itself: both keys PRESENT, with the value `undefined`. A bare
        // `toBeUndefined()` would pass on the omitted keys, the very defect. The walk enters
        // Income from the line, the path where the merge leaks, then returns to the line, which
        // must get its callback and hidden label back.
        expect(isPrivacyEnabled()).toBe(false);
        const {getByTestId} = render(GrowthChart, {props: ladderProps(FIXTURE_40)});
        await waitForFrame(FRAME.abs);

        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        const line = await waitForFrame(FRAME.pnlLine);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        // Precondition: the view Income is entered from has a callback the merge could keep.
        expect(typeof line.yAxis.min).toBe('function');

        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        const income = await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        // Soft, so one red names both keys.
        expect.soft(income.yAxis).toHaveProperty('min', undefined);
        expect.soft(income.yAxis.axisLabel).toHaveProperty('showMinLabel', undefined);

        await fireEvent.click(getByTestId('growth-pnl-submode-line'));
        const back = await waitForFrame(FRAME.pnlLine);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-line']);
        expect(lowerEdgeOf(back)).toEqual(FIXED_EDGE);
    });

    // --- k4 G1: the edge label is blank, so containLabel measures nothing there -----------------

    /** Privacy off, then on. WHY: the blank must hold over the mask too, and the mask must not leak past it. */
    const PRIVACY = [
        {title: 'in the clear', masked: false},
        {title: 'masked', masked: true},
    ];

    /** Edges a computed `min` can hand the label: below zero, a large raw value D18 prints in full (`55.588M`), zero, and a return. */
    const EDGES = [-4_152, 55_588_000, 0, 12.3];

    /** What a masked money label prints in en-US: the minus outside the mask (D8), nothing else. */
    const maskedMoney = (value: number) => (value < 0 ? `-${PRIVACY_PLACEHOLDER}` : PRIVACY_PLACEHOLDER);

    /**
     * The y-axis formatter of each view whose axis has the computed edge — Abs, P&L line, Candles, % —
     * walked as the D25 case walks them, with the edge proven a callback in each. WHY: one walk per mount,
     * so the privacy flag set before the mount is the one every formatter is built under.
     */
    async function edgeFormatters(): Promise<Array<{view: string; format: AxisFormatter}>> {
        const {getByTestId} = render(GrowthChart, {props: ladderProps(FIXTURE_40)});
        const views: Array<{view: string; format: AxisFormatter}> = [];
        const take = (view: string, option: FullOption) => {
            // Barrier: this view's axis has the computed edge, the one whose label is the subject.
            expect(typeof option.yAxis.min, `${view}: the lower edge is a callback`).toBe('function');
            views.push({view, format: option.yAxis.axisLabel.formatter});
        };
        take('Abs', await waitForFrame(FRAME.abs));
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        take('P&L line', await waitForFrame(FRAME.pnlLine));
        await fireEvent.click(getByTestId('growth-pnl-submode-candles'));
        take('Candles', await waitForFrame(FRAME.candles));
        // % last, as in D25: its frame is the P&L line's, so its own formatter is its barrier.
        await fireEvent.click(getByTestId('growth-toggle-pct'));
        await waitFor(() => expect(latestFullOption().yAxis.axisLabel.formatter(12.3)).toBe('12.3%'), {timeout: 5_000});
        take('%', latestFullOption());
        return views;
    }

    it.each(PRIVACY)('k4 G1: prints nothing at tick index 0, the edge, in Abs, P&L line, Candles and % — $title', async ({masked}) => {
        // WHY: developer review, 05/10/2026: an empty band left of the Abs and P&L plots. D25 hides the edge
        // label, but containLabel still measures it, at its full D18 width; a label blank at index 0 measures
        // nothing, whatever the edge. Catches the edge still formatted at index 0, in any of the four views,
        // in the clear or masked — the mask (`-•••`) is as wide as a label that is not empty.
        setPrivacyEnabled(masked);
        const views = await edgeFormatters();
        const read = Object.fromEntries(views.map(({view, format}) => [view, inLocale('en-US', () => EDGES.map((edge) => format(edge, 0)))]));
        expect(read).toEqual(Object.fromEntries(views.map(({view}) => [view, EDGES.map(() => '')])));
    });

    it.each(PRIVACY)('k4 G1: prints every tick from index 1 on exactly as before — $title (green today and after the fix)', async ({masked}) => {
        // WHY: the blank is the edge's alone; every other tick keeps D18's exact label, D23's glyphs and D8's
        // mask. Catches a rule that blanks more than index 0 (`index <= 1`, an inverted test), or that formats
        // the other ticks another way.
        setPrivacyEnabled(masked);
        const views = await edgeFormatters();
        const PCT_TICKS = [-0.6, 0, 1.2, 12.3];
        const sequencesOf = (view: string) => (view === '%' ? [PCT_TICKS] : TICKS_EN.map(({values}) => values));
        const read = Object.fromEntries(views.map(({view, format}) => [view, inLocale('en-US', () => sequencesOf(view).map((values) => values.map((value, offset) => format(value, offset + 1))))]));
        const money = masked ? TICKS_EN.map(({values}) => values.map(maskedMoney)) : TICKS_EN.map(({labels}) => labels);
        expect(read).toEqual({Abs: money, 'P&L line': money, Candles: money, '%': [['-0.6%', '0.0%', '1.2%', '12.3%']]});
    });

    it.each(PRIVACY)('k4 G1: a call with the value alone prints the edge as before — $title (green today and after the fix)', async ({masked}) => {
        // WHY: the index is ECharts' second argument, and the older callers — the S2a and S7b cases among them
        // — pass the value alone. Catches an index that defaults to 0 and blanks every such call.
        setPrivacyEnabled(masked);
        const views = await edgeFormatters();
        const VALUES = [-4_152, 55_588_000, 0];
        const read = Object.fromEntries(views.map(({view, format}) => [view, inLocale('en-US', () => VALUES.map((value) => format(value)))]));
        const money = masked ? VALUES.map(maskedMoney) : ['-4.152k', '55.588M', '0'];
        expect(read).toEqual({Abs: money, 'P&L line': money, Candles: money, '%': ['-4152.0%', '55588000.0%', '0.0%']});
    });

    it.each(PRIVACY)('k4 G1: Income keeps the label of its tick index 0, a real tick on an axis that stands on zero — $title (green today and after the fix)', async ({masked}) => {
        // WHY: Income has no computed edge (D25): its lowest tick is a round value — zero, or the deepest cost
        // bar — and a reader needs it. Catches the blank applied to every view.
        setPrivacyEnabled(masked);
        const {getByTestId} = render(GrowthChart, {props: ladderProps(FIXTURE_40)});
        await waitForFrame(FRAME.abs);
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await waitForFrame(FRAME.pnlLine);
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        const income = await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        // Barrier: Income's axis has no computed edge, so its index 0 is not the edge G1 blanks.
        expect(income.yAxis).toHaveProperty('min', undefined);
        const VALUES = [0, -30, -5_000, 1_500];
        const labels = inLocale('en-US', () => VALUES.map((value) => income.yAxis.axisLabel.formatter(value, 0)));
        expect(labels).toEqual(masked ? VALUES.map(maskedMoney) : ['0', '-30', '-5k', '1.5k']);
    });
});

// =============================================================================
// S8 — the purchase value in the Income submode (R11, D26)
// =============================================================================

/**
 * The Income submode's acquisition column is the purchase value, the KPI card's own figure
 * (`dashboard.bookValue`), split by the money that paid for it: new capital, then reinvested
 * returns (R11, D2 = A).
 *
 * One name. Both halves carry the purchase value's name, so the legend lists it once and one
 * click on it hides or shows both, as the P&L line's two halves share one total. Neither half's
 * own label reaches the legend.
 *
 * One total. The tooltip prints the purchase value in bold, then each half under it as a `↳ `
 * row, every amount signed like the rest of Income (D23b). The total is the sum of what the two
 * bars draw.
 *
 * One colour per kind of money (D26). Each half is painted in the colour its money has in the
 * Abs view: new capital in the KPI blue of the purchase cost (`dashboard.assetsAtCost`), the
 * reinvested returns in the colour of `dashboard.cashFromGeneratedReturns`. The colours are read
 * from the Abs option of the same mount, never written down: the palette is the component's to
 * choose, and the agreement of the two views is the contract.
 *
 * WHY names are asserted here, where the file header says they are not: the shared name IS the
 * subject. Every name is the `get(_)` of its key in the locale the component renders in, never
 * English text. Series names and legend entries are compared raw, as ECharts receives them, and
 * tooltip labels as the user reads them, through `htmlText`.
 */
// WHY the 30 s budget: a case chains several 5 s waits, and a red `waitFor` must be able to
// exhaust its own timeout and rethrow the case's assertion instead of dying on the test timeout
// (as S7 and S7b do).
describe('GrowthChart Income purchase value (S8: R11, D26)', {timeout: 30_000}, () => {
    /**
     * New capital and reinvested returns on two of the three money days, so the one Income bar is
     * a sum on both halves: 500 + 400 and 100 + 200. Whole amounts, none of them zero, and the two
     * halves differ, so a swap cannot pass: the subject is the total and which half is which, not
     * the sign of a zero (D23 covers that, on `MONEY_ACQUISITION`, which stays as it is).
     */
    const PURCHASE_FUNDING: PortfolioAcquisitionFundingSeries = {
        points: [
            {date: DATES[0], from_new_capital: eur(500), from_reinvested: eur(100)},
            {date: DATES[2], from_new_capital: eur(400), from_reinvested: eur(200)},
        ],
    };
    /** What the one bar sums each half to, and the two together, counted by hand from `PURCHASE_FUNDING`. */
    const NEW_CAPITAL = 900;
    const REINVESTED = 300;
    const PURCHASE_VALUE = 1_200;

    /** The parts of a full rebuild this describe reads. WHY local: the shared `FullOption` has no stack, colour or legend, and only S8 reads them. */
    interface PurchaseValueOption extends Omit<FullOption, 'series'> {
        series: Array<{type?: string; name?: string; stack?: string; itemStyle?: {color?: string}; data?: unknown[]}>;
        legend?: {data?: unknown[]};
    }

    const labelOf = (key: string) => htmlText(get(_)(key));

    /** A colour as jsdom reads it back from a `style`, where `#rrggbb` becomes `rgb(…)`. WHY: a tooltip row's colour reads back normalised and an option's as written, so both sides go through here. */
    function cssColour(colour: string | undefined): string {
        const probe = document.createElement('div');
        probe.style.color = colour ?? '';
        return probe.style.color;
    }

    /**
     * Mounts the three money days with `PURCHASE_FUNDING`, opens on Abs, walks to P&L, then to
     * Income, and returns the full rebuild of each end. Every step waits for its own frame and
     * reads its toggle as pressed, so neither option can be mistaken for the other.
     */
    async function openIncome(): Promise<{abs: PurchaseValueOption; income: PurchaseValueOption}> {
        // The amounts are read in the clear. The flag is module state, and the cases that switch it on switch it off.
        expect(isPrivacyEnabled()).toBe(false);
        const {getByTestId} = render(GrowthChart, {
            props: {history: MONEY_HISTORY, incomeHistory: MONEY_INCOME, costHistory: MONEY_COSTS, depositHistory: MONEY_DEPOSITS, acquisitionFunding: PURCHASE_FUNDING, baseCurrency: BASE_CURRENCY},
        });
        const abs: PurchaseValueOption = await waitForFrame(FRAME.abs);
        expect(pressedAmong(MODE_TOGGLES)).toEqual(['growth-toggle-eur']);
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await waitForFrame(FRAME.pnlLine);
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        const income: PurchaseValueOption = await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        return {abs, income};
    }

    /** The options that carry a series array, recorded from call `since` onwards: full rebuilds and partial updates alike. */
    function seriesCallsSince(since: number): Array<Record<string, unknown>> {
        expect(chartInstances).toHaveLength(1);
        return chartInstances[0].setOptionCalls
            .slice(since)
            .map((call) => call.option)
            .filter((option) => Array.isArray(option.series));
    }

    /** The one tooltip row labelled `label`, as elements: its label `<span>`, and the `<div>` that carries the row's colour. */
    function rowOf(html: string, label: string): {span: Element; row: HTMLElement} {
        const matching = tooltipRowElements(html).filter((entry) => entry.label.textContent === label);
        expect(matching, `exactly one tooltip row labelled ${label}`).toHaveLength(1);
        const row = matching[0].label.parentElement;
        if (row == null) throw new Error(`the row labelled ${label} has no element around it`);
        return {span: matching[0].label, row};
    }

    it('names both acquisition halves after the purchase value, in the one acquisition stack, on the full rebuild', async () => {
        // WHY: R11. The two halves are one quantity, the purchase value, split by where its money
        // came from, so both carry its name. Catches a half that keeps its own label, which also
        // lists it in the legend apart from the other, and a half that leaves the acquisition
        // stack, which would draw it as a column of its own. `openIncome` waits for the Income
        // frame, so slots 4 and 5 are the last two of six bars.
        const {income} = await openIncome();
        const purchaseValue = get(_)('dashboard.bookValue');
        expect(income.series.slice(4).map(({name, stack}) => ({name, stack}))).toEqual([
            {name: purchaseValue, stack: 'acquisition'},
            {name: purchaseValue, stack: 'acquisition'},
        ]);
    });

    it('keeps the shared name on the partial update that draws funding arriving after Income is on screen', async () => {
        // WHY: R11 on the other path. Data that arrives in the view on screen is drawn by the
        // partial update, which sends every slot's name with its data and is built apart from the
        // full rebuild. Catches that path still naming the halves apart, so the bars would carry
        // names the legend does not list. The funding arrives after Income is drawn, as the
        // dashboard's lazy fetch delivers it, which is what makes the update partial.
        const {getByTestId, rerender} = render(GrowthChart, {props: {history: HISTORY}});
        await waitFor(() => expect(chartInstances).toHaveLength(1), {timeout: 5_000});
        await fireEvent.click(getByTestId('growth-toggle-pnl'));
        await fireEvent.click(getByTestId('growth-pnl-submode-income'));
        await waitForFrame(FRAME.income);
        expect(pressedAmong(SUBMODE_TOGGLES)).toEqual(['growth-pnl-submode-income']);
        // Presence barrier: the six slots are drawn, and the acquisition ones carry nothing yet.
        const drawnBefore = renderedSeries();
        expect(drawnBefore).toHaveLength(6);
        expect(nonZeroPoints(drawnBefore[4]) + nonZeroPoints(drawnBefore[5]), 'no funding before it arrives').toBe(0);

        // Sampled BEFORE the arrival, so the update read below is one recorded after it.
        const before = setOptionCount();
        await rerender({acquisitionFunding: ACQUISITION_FUNDING});
        let update: SeriesUpdate[] = [];
        await waitFor(
            () => {
                const calls = seriesCallsSince(before);
                expect(calls.length, 'a series update after the arrival').toBeGreaterThan(0);
                const latest = calls[calls.length - 1];
                // Partial: series without the axis and the tooltip that only a full rebuild carries.
                expect(latest.yAxis, 'a partial update: no y axis').toBeUndefined();
                expect(latest.tooltip, 'a partial update: no tooltip').toBeUndefined();
                update = latest.series as SeriesUpdate[];
                expect(update).toHaveLength(6);
                expect(nonZeroPoints(update[4]), 'new capital arrived').toBeGreaterThan(0);
                expect(nonZeroPoints(update[5]), 'reinvested arrived').toBeGreaterThan(0);
            },
            {timeout: 5_000},
        );

        const purchaseValue = get(_)('dashboard.bookValue');
        expect(update.slice(4).map((series) => series.name)).toEqual([purchaseValue, purchaseValue]);
    });

    it('lists the purchase value once in the Income legend, after the other four columns, and neither half under its own label', async () => {
        // WHY: R11 with the legend code left as it is. The legend lists each distinct series name
        // in slot order, so the shared name is what makes the purchase value one entry, which
        // hides or shows both halves at once. Catches a half named apart, which lists its own
        // label and toggles alone, and an acquisition slot moved ahead of the other columns.
        const {income} = await openIncome();
        const legend = income.legend?.data;
        expect(legend).toEqual(['transactions.types.DIVIDEND', 'transactions.types.INTEREST', 'dashboard.feesAndTaxes', 'transactions.types.DEPOSIT', 'dashboard.bookValue'].map((key) => get(_)(key)));
        expect(
            legend?.filter((entry) => entry === get(_)('dashboard.bookValue')),
            'the purchase value, once',
        ).toHaveLength(1);
        expect(legend).not.toContain(get(_)('dashboard.pnlAcqNewCapital'));
        expect(legend).not.toContain(get(_)('dashboard.pnlAcqReinvested'));
    });

    it('prints the purchase value in bold as the total of its halves, then new capital and reinvested under it, all signed', async () => {
        // WHY: R11 in the tooltip. The purchase value is the figure a user compares with the KPI
        // card, so it is printed whole, in bold like the income total, with each half under it as
        // a `↳ ` row. Catches a missing total, a total of one half only, the halves swapped or
        // printed away from their total, a half printed unsigned, and a total set like its halves.
        const {income} = await openIncome();
        const html = income.tooltip.formatter([{dataIndex: 0}]);
        const rows = tooltipRows(html);
        const purchaseValue = labelOf('dashboard.bookValue');
        expect(
            rows.filter((row) => row.label === purchaseValue),
            'exactly one purchase-value row',
        ).toHaveLength(1);
        const head = rows.findIndex((row) => row.label === purchaseValue);
        expect(rows.slice(head, head + 3), 'the purchase value, then its two halves, in a row').toEqual([
            {label: purchaseValue, value: expectedAmount(PURCHASE_VALUE, {signed: true})},
            {label: subRowLabel('dashboard.pnlAcqNewCapital'), value: expectedAmount(NEW_CAPITAL, {signed: true})},
            {label: subRowLabel('dashboard.pnlAcqReinvested'), value: expectedAmount(REINVESTED, {signed: true})},
        ]);

        /** How a row's label is set: the tags right under its `<span>`, and the text of the first. */
        const setting = (label: string) => {
            const {span} = rowOf(html, label);
            return {tags: Array.from(span.children, (child) => child.tagName), text: span.firstElementChild?.textContent ?? null};
        };
        // Precondition: the income total is set as one bold label, the form the purchase value takes.
        const total = labelOf('assets.distribution.total');
        expect(setting(total), 'the income total is bold').toEqual({tags: ['B'], text: total});
        expect(setting(purchaseValue), 'the purchase value is bold, like the income total').toEqual({tags: ['B'], text: purchaseValue});
        expect(setting(subRowLabel('dashboard.pnlAcqNewCapital')), 'new capital is not').toEqual({tags: [], text: null});
        expect(setting(subRowLabel('dashboard.pnlAcqReinvested')), 'reinvested is not').toEqual({tags: [], text: null});
    });

    it('prints as the purchase value the sum of the two acquisition bars it draws', async () => {
        // WHY: the tooltip and the bars must tell one story. The total is checked against the
        // values the recorder received for the two acquisition bars, not against the fixture, so
        // it holds whatever the bucketing makes of the days. Catches a total folded from other
        // values than the bars draw, or from one bar only.
        const {income} = await openIncome();
        const [drawnNew, drawnReinvested] = income.series.slice(4).map((series, index) => {
            expect(series.data, `slot ${4 + index}: the three days are one Income bar`).toHaveLength(1);
            return pointValue(series.data?.[0]);
        });
        if (drawnNew == null || drawnReinvested == null) throw new Error('an acquisition bar carries no value');
        // Preconditions: both halves draw something, so neither alone can pass for the sum.
        expect(drawnNew, 'new capital is drawn').not.toBe(0);
        expect(drawnReinvested, 'reinvested is drawn').not.toBe(0);

        const rows = tooltipRows(income.tooltip.formatter([{dataIndex: 0}]));
        expect(rowValue(rows, 'dashboard.bookValue')).toBe(expectedAmount(drawnNew + drawnReinvested, {signed: true}));
    });

    it('paints each half in the colour its money has in Abs, on its bar and on its tooltip row (D26)', async () => {
        // WHY: D26. The purchase value has one colour across the app, the KPI blue, so the new
        // capital that paid for it keeps that blue, and the reinvested returns keep the colour the
        // returns have in Abs. Catches new capital left in the contributed-capital colour, the two
        // colours swapped, and a tooltip row painted apart from its bar.
        const {abs, income} = await openIncome();
        /** The colour of the one Abs series named after `labelKey`. */
        const absColour = (labelKey: string) => {
            const matching = abs.series.filter((series) => series.name === get(_)(labelKey));
            expect(matching, `exactly one Abs series named ${labelKey}`).toHaveLength(1);
            return matching[0].itemStyle?.color ?? '';
        };
        const purchaseCost = absColour('dashboard.assetsAtCost');
        const returns = absColour('dashboard.cashFromGeneratedReturns');
        // Preconditions: two real colours, and different ones. One colour everywhere would pass every check below.
        expect(purchaseCost, 'the purchase cost has a colour in Abs').not.toBe('');
        expect(returns, 'the returns have a colour in Abs').not.toBe('');
        expect(purchaseCost, 'two different colours').not.toBe(returns);

        const bars = income.series.slice(4).map((series) => series.itemStyle?.color);
        expect(bars, 'new capital in the purchase-cost blue, then reinvested in the returns colour').toEqual([purchaseCost, returns]);

        // Each `↳` row in its bar's colour. The row reads back normalised, so the bar's colour goes through `cssColour` too.
        const html = income.tooltip.formatter([{dataIndex: 0}]);
        const barColours = bars.map((colour) => cssColour(colour));
        expect(
            barColours.every((colour) => colour !== ''),
            'the bar colours read back as CSS colours',
        ).toBe(true);
        expect(['dashboard.pnlAcqNewCapital', 'dashboard.pnlAcqReinvested'].map((key) => rowOf(html, subRowLabel(key)).row.style.color)).toEqual(barColours);
    });
});
