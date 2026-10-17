// @vitest-environment jsdom
/**
 * PriceChartFull — its tooltips in the interface language: the conversion lines of an event (T-EN1), and every
 * day a tooltip writes (T-ISO); with the header of its candles, `CandlestickChart` (T-ISO).
 *
 * T-EN1. An event paid in another currency than the one the chart shows (a dividend in dollars on a chart in
 * euros) is converted, and its tooltip says so in two lines: the original amount with its currency, and the
 * date of the FX rate used — with how many days that rate lags the event when it does.
 * The contract: the original-amount line is `chart.tooltip.originalValue` around `formatFixed(value, 4)`,
 * followed by the unchanged currency badge; the FX line is `chart.tooltip.fxRateDate` around the rate's day,
 * then — only when the lag is positive — a space and `chart.tooltip.fxDaysBack` around `formatFixed(days, 0)`.
 * The original-amount line reads `orig. …` in all four catalogues, so a marker locale — where each of the three
 * keys reads as a marker of itself — is what proves that line comes from the catalogue.
 * Those cases are about the WORDS: the day inside the FX line and the day heading the tooltip are compared with
 * their notation set aside (`sansDay`, either ISO or the house notation), because how a day is written is
 * T-ISO's, pinned in its own describe — so neither cure holds the other's tests hostage.
 *
 * T-ISO (M-18: every date the user reads is written in the interface language). The house notation of a day in a
 * tooltip is the lot charts' one, `formatAxisDate(uiLocale(), day, true)`: Intl's numeric year, short month and
 * numeric day of the calendar day — `4 mar 2024`, `4 mars 2024`, `Mar 4, 2024` (`houseDay`, the oracle, is Intl
 * itself; a control case ties it to `formatAxisDate`). The contract, after the cure:
 *   - the axis tooltip's header: a daily point is headed by its day; a weekly one by `chart.tooltip.weekRange`
 *     around the week's first and last day; a monthly one by the month (already localized) over
 *     `chart.tooltip.valueAt` around the month's last day;
 *   - its rows: `chart.tooltip.valueAt` around a day (the reference price's, the current price's, an overlay
 *     point's representative), the ↩ line's reference target day, the 💱 line's two FX days (`—` for a missing one);
 *   - an event's tooltip: its heading day, the day of each event listed in an aggregated period, and the day
 *     inside `chart.tooltip.fxRateDate`;
 *   - `CandlestickChart` — PriceChartFull's candles, mounted directly with the props PriceChartFull hands it
 *     (`synthesizeDailyOHLC`, aggregated by `aggregateOHLCV` at a coarser resolution) — heads its tooltip by the
 *     same three rules.
 * Every day is the house notation of the interface locale; every word around it is the catalogue's (`$_`).
 * Red today: each of those days is written as ISO (`2024-03-04`), in English too, where the house notation is
 * `Mar 4, 2024`.
 *
 * C-97c-3 (the describe after T-ISO's): a price in the tooltips keeps its significant digits — an event point's bucket
 * value, an event's value and original value, the axis rows. Its docblock says how.
 *
 * The open week and month (after R-5, lot 51). A weekly or monthly point is dated by its bucket's last data point;
 * in the period still open — a series that stops inside a week and a month, OPEN_DAYS — its tooltip must span up
 * to that day, not to the bucket's theoretical end (`bucketSpanUpTo`). The last describe pins it on the axis
 * tooltip, the candle's, and the tooltip of an event marker sitting on the point; the whole-period cases on
 * WEEK_ENDS and MONTH_ENDS are the guard of what does not change.
 *
 * Y-8 (two describes). A zoom gesture re-aims the arrows of an overlay once it settles, not on every
 * tick — on PriceChartFull and on its candles — and, once the chart has been rebuilt in other colours, the arrows'
 * write-back brings none of the old ones back (a colour guard). Y-25 (the last two describes): a chart without arrow
 * markers reads nothing for them when a zoom settles, and a resize re-aims the arrows once it settles, not on each
 * callback. Their docblocks say how.
 *
 * How it is tested: the real component, with ECharts replaced by a recorder (the `GrowthChart.test.ts`
 * pattern: jsdom has no canvas, and pixels are not the subject). A tooltip is the formatter the component handed
 * ECharts, called with what ECharts hands it on a hover: the axis tooltip with the items under the pointer, an
 * event's with the very point its scatter series (`Events: <type>`) holds. Its HTML is parsed inert in a
 * `<template>`; a line is what `<br>` separates (the candles' header is the tooltip's first blocks). The event
 * fixtures carry neither a note nor a comparison asset, so the conversion lines are an entry's last two.
 * Resolution: it follows the density of points per pixel, so the recorder reports the plot's width — a wide plot
 * keeps a week and a half daily, a narrow one turns five weeks of calendar days (or OPEN_DAYS' two and a half)
 * weekly or monthly; each case proves the resolution it drew at from the x-axis before reading a tooltip.
 *
 * Also stubbed: layout — jsdom measures every box as 0×0 and the chart draws only into a non-empty one, so
 * `getBoundingClientRect` reports a panel-sized box.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`).
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in — a recorder, not a renderer — answering every call the chart and its helpers make on
 * an instance (`getZr()` for the pointer handlers, `getOption()` for the arrow markers, `getWidth()` for the
 * initial resolution), and keeping every `setOption` payload. `graphic.LinearGradient` is the main series'
 * area fill: kept as its arguments. `plot.width` is the width `getWidth()` reports: the resolution knob.
 *
 * For Y-8 it also acts as ECharts does where a zoom and the arrows' re-aim read it. `on` keeps the handlers it is
 * given and `emit` calls them, as ECharts does when the user acts (LineChart.test.ts' pattern; event names compared
 * in lower case); no case emits but the Y-8 and Y-25 ones. The option it holds, it holds as ECharts does: a `setOption`
 * merges into it — an object key by key, anything else, an array included, replaced; a component (`series`,
 * `xAxis`, `dataZoom`…) by its index — unless `notMerge` replaces it whole; `getOption()` answers a deep copy,
 * every component a list, and counts its calls (`getOptionCount`): ECharts deep-clones the whole option on each.
 *
 * Its zoom is LineChart.test.ts' (Y-25 ported it here): a zoom moves the window as ECharts' dataZoom model does — the
 * held `dataZoom[0]`'s `start` and `end`, never a `startValue`/`endValue` beside them — then emits `dataZoom` at once:
 * the chart's own (`dispatchAction({type: 'dataZoom', start, end})`, its event the payload itself under the event's
 * lower-case name, as ECharts emits a non-batch action) or the user's (`userZoom`, its event in 47-1's batch shape).
 * `dispatchAction` records every action (`dispatchedActions`), with how many `setOption` calls came before it.
 * `convertToPixel` maps a `[category, value]` point through the window on screen (`gridPixel`): the categories of the
 * first x-axis that the held `dataZoom[0]` leaves visible — all of them without a window — spread over the plot's width
 * (`plot.width`), and y 400 − value; so an arrow marker's rotation depends on the window and on the plot's width, and is
 * computed and written back as on a screen. `resize` counts its calls (`resizeCount`): the first-render stability pass
 * resizes.
 */
const {chartInstances, echartsModule, plot} = vi.hoisted(() => {
    type Handler = (params?: unknown) => void;
    type ChartOption = Record<string, unknown>;

    interface FakeChart {
        setOptionCalls: Array<{option: ChartOption}>;
        /** `setOption(option)`, `setOption(option, notMerge)` or `setOption(option, {notMerge, lazyUpdate})`. */
        setOption: (option: ChartOption, opts?: unknown) => void;
        getOption: () => ChartOption;
        /** How many times `getOption()` was called (Y-8). */
        getOptionCount: number;
        /** How many times `resize()` was called (Y-8). */
        resizeCount: number;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        getZr: () => {on: () => void; off: () => void};
        /** `on(event, handler)` or `on(event, query, handler)`: the handler is the last argument. */
        on: (event: string, ...rest: unknown[]) => void;
        off: (event: string, handler?: unknown) => void;
        /** Calls every handler registered for `event` with `params` (Y-8). */
        emit: (event: string, params?: unknown) => void;
        /** How many handlers are registered for `event`: the precondition that an emitted event reaches the chart (Y-8). */
        handlerCount: (event: string) => number;
        /**
         * `dispatchAction(action)` or `dispatchAction(action, silent | {silent})`: recorded; a `dataZoom` with a numeric
         * `start` and `end` moves the held window and, unless silent, emits `dataZoom` with the payload at once (Y-25).
         */
        dispatchAction: (action: ChartOption, opt?: unknown) => void;
        /** Every action dispatched, in order, with how many `setOption` calls came before it (`atCall`) (Y-25). */
        dispatchedActions: Array<{action: ChartOption; atCall: number}>;
        /** A user's zoom to `window` (Y-25): the held window moves, then `dataZoom` is emitted in 47-1's batch shape. Not a dispatch of the chart's own. */
        userZoom: (window: {start: number; end: number}) => void;
        resize: () => void;
        containPixel: () => boolean;
        convertFromPixel: () => null;
        /** A `[category, value]` point in px, through the window on screen (`gridPixel` on the held first x-axis and `dataZoom[0]`) (Y-25). */
        convertToPixel: (finder: unknown, value: unknown) => number[] | null;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];
    /** The plot's width in px, as `getWidth()` reports it and `gridPixel` spreads the categories over; set per case before mounting (see `beforeEach`). */
    const plot = {width: 1200};

    /** ECharts' component types: `getOption()` answers each as a list, and a merge matches them by index. */
    const COMPONENTS = new Set(['grid', 'xAxis', 'yAxis', 'dataZoom', 'series', 'tooltip', 'legend', 'title', 'visualMap', 'toolbox', 'graphic', 'dataset', 'axisPointer', 'polar', 'radiusAxis', 'angleAxis', 'singleAxis', 'parallel', 'parallelAxis', 'geo', 'calendar', 'brush', 'timeline', 'aria']);
    /** The plot's height (`getHeight()`): y grows downwards. */
    const PLOT_HEIGHT = 400;

    const isPlain = (value: unknown): value is ChartOption => value !== null && typeof value === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(value));

    /**
     * The categories a zoom window leaves on screen — the first, and how many — as the charts count them
     * (`visiblePointCountFromZoom`): the window's percentages over the axis's steps, the first rounded down and the last
     * up. Without a numeric `start` and `end`, the whole axis.
     */
    function visibleCategories(categoryCount: number, zoom: unknown): {first: number; count: number} {
        const steps = Math.max(categoryCount - 1, 0);
        const window = isPlain(zoom) ? zoom : {};
        const start = typeof window.start === 'number' ? window.start : 0;
        const end = typeof window.end === 'number' ? window.end : 100;
        const first = Math.floor((start / 100) * steps);
        return {first, count: Math.ceil((end / 100) * steps) - first + 1};
    }

    /**
     * A `[category, value]` point in px on an x-axis of `categories` zoomed to `zoom`: x spreads the visible categories
     * over the plot's width — a category's index in the window times the plot's width over their count — and y is the
     * plot's height minus the value. Null for a category not on the axis, or a value that is not a number.
     */
    function gridPixel(point: unknown, categories: unknown[], zoom?: unknown): number[] | null {
        if (!Array.isArray(point)) return null;
        const [category, amount] = point;
        const index = typeof category === 'number' ? category : categories.indexOf(category);
        if (index < 0 || typeof amount !== 'number') return null;
        const {first, count} = visibleCategories(categories.length, zoom);
        return [(index - first) * (plot.width / count), PLOT_HEIGHT - amount];
    }

    /** A deep copy of the plain objects and arrays in `value`; anything else — a function, a gradient — is shared, as ECharts' clone shares a function. */
    function copy(value: unknown): unknown {
        if (Array.isArray(value)) return value.map((entry) => copy(entry));
        if (isPlain(value)) return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, copy(entry)]));
        return value;
    }

    /** `patch` merged into `target` as ECharts merges an option: an object key by key, anything else — an array too — replaced. */
    function mergeInto(target: ChartOption, patch: ChartOption): void {
        for (const [key, value] of Object.entries(patch)) {
            const current = target[key];
            if (isPlain(value) && isPlain(current)) mergeInto(current, value);
            else target[key] = copy(value);
        }
    }

    function createFakeChart(dom: unknown): FakeChart {
        let held: ChartOption = {};
        let disposed = false;
        const handlers = new Map<string, Handler[]>();

        /**
         * The window ECharts' dataZoom model takes on a zoom (`setRawRange`): the held `dataZoom[0]`'s `start` and `end`,
         * each pair set whole — so no `startValue`/`endValue` is left beside them. Nothing without a dataZoom.
         */
        function takeWindow(start: number, end: number): void {
            const zoom = Array.isArray(held.dataZoom) ? held.dataZoom[0] : undefined;
            if (!isPlain(zoom)) return;
            Object.assign(zoom, {start, end});
            delete zoom.startValue;
            delete zoom.endValue;
        }

        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option, opts) {
                chart.setOptionCalls.push({option});
                if (opts === true || (isPlain(opts) && opts.notMerge === true)) held = {};
                for (const [key, value] of Object.entries(option)) {
                    if (!COMPONENTS.has(key)) {
                        held[key] = copy(value);
                        continue;
                    }
                    const existing = held[key];
                    const list: unknown[] = Array.isArray(existing) ? existing : [];
                    const entries: unknown[] = Array.isArray(value) ? value : value === undefined ? [] : [value];
                    entries.forEach((entry, index) => {
                        const current = list[index];
                        if (isPlain(entry) && isPlain(current)) mergeInto(current, entry);
                        else list[index] = copy(entry);
                    });
                    held[key] = list;
                }
            },
            getOption() {
                chart.getOptionCount += 1;
                return copy(held) as ChartOption;
            },
            getOptionCount: 0,
            resizeCount: 0,
            // The density of points per pixel decides the resolution: a week and a half of daily points over
            // 1200 px keeps the chart at 'daily' (one event, one point); a narrow plot turns it weekly or monthly.
            getWidth: () => plot.width,
            getHeight: () => PLOT_HEIGHT,
            getDom: () => dom,
            getZr: () => ({on: () => {}, off: () => {}}),
            on(event, ...rest) {
                const handler = rest[rest.length - 1];
                if (typeof handler !== 'function') return;
                const name = event.toLowerCase();
                handlers.set(name, [...(handlers.get(name) ?? []), handler as Handler]);
            },
            off(event, handler) {
                const name = event.toLowerCase();
                handlers.set(name, handler === undefined ? [] : (handlers.get(name) ?? []).filter((entry) => entry !== handler));
            },
            emit(event, params) {
                // A copy: a handler that unregisters itself must not make its neighbour skip.
                for (const handler of [...(handlers.get(event.toLowerCase()) ?? [])]) handler(params);
            },
            handlerCount: (event) => handlers.get(event.toLowerCase())?.length ?? 0,
            dispatchAction(action, opt) {
                chart.dispatchedActions.push({action: copy(action) as ChartOption, atCall: chart.setOptionCalls.length});
                if (action.type !== 'dataZoom' || typeof action.start !== 'number' || typeof action.end !== 'number') return;
                takeWindow(action.start, action.end);
                // At once, as ECharts emits it outside a draw: a non-batch action's event is the payload itself, under the event's lower-case name.
                if (!(opt === true || (isPlain(opt) && opt.silent === true))) chart.emit('dataZoom', {...action, type: 'datazoom'});
            },
            dispatchedActions: [],
            userZoom({start, end}) {
                takeWindow(start, end);
                chart.emit('dataZoom', {type: 'datazoom', batch: [{start, end}]});
            },
            resize() {
                chart.resizeCount += 1;
            },
            containPixel: () => false,
            convertFromPixel: () => null,
            convertToPixel(_finder, value) {
                const axis = Array.isArray(held.xAxis) ? held.xAxis[0] : undefined;
                const categories: unknown[] = isPlain(axis) && Array.isArray(axis.data) ? axis.data : [];
                return gridPixel(value, categories, Array.isArray(held.dataZoom) ? held.dataZoom[0] : undefined);
            },
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    class LinearGradient {
        readonly stops: unknown[];
        constructor(...stops: unknown[]) {
            this.stops = stops;
        }
    }

    return {chartInstances, plot, echartsModule: {init: (dom: unknown) => createFakeChart(dom), graphic: {LinearGradient}}};
});

vi.mock('echarts', () => echartsModule);

import type {ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {addMessages, waitLocale} from 'svelte-i18n';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import type {RenderedSignal} from '$lib/charts/signals';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {CHART_GAIN_LOSS, PRICE_SERIES} from '$lib/theme/chartTheme';
import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
import CandlestickChart from './CandlestickChart.svelte';
import type {LineDataPoint} from './LineChart.svelte';
import PriceChartFull, {type EventMarker} from './PriceChartFull.svelte';
import {synthesizeDailyOHLC, type CalendarReturnPointContext} from './priceChartHelpers';
import {aggregateOHLCV, type ChartResolution} from './timeSeriesAggregation';

type UiLanguage = 'en' | 'it' | 'fr';
const LANGUAGES = ['it', 'fr'] as const;

/** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
const MARKER_LOCALE = 'qaa';

/** A week and a half of prices, in euros. */
const DATA: LineDataPoint[] = ['2024-02-26', '2024-02-27', '2024-02-28', '2024-02-29', '2024-03-01', '2024-03-04', '2024-03-05', '2024-03-06'].map((date, index) => ({date, value: 100 + index}));

/** A dividend paid in dollars on a Monday, shown in euros at the rate of the Friday before: three days back. */
const BACKFILLED: EventMarker = {
    date: '2024-03-04',
    type: 'DIVIDEND',
    value: 1137.25,
    currency: 'EUR',
    currencyFlag: '🇪🇺',
    originalValue: 1234.56789,
    originalCurrency: 'USD',
    originalCurrencyFlag: '🇺🇸',
    fxRateDate: '2024-03-01',
    fxDaysBack: 3,
};

/** A dividend paid in dollars, shown in euros at the rate of its own day: no lag to tell. */
const SAME_DAY: EventMarker = {
    date: '2024-03-06',
    type: 'DIVIDEND',
    value: 9.43,
    currency: 'EUR',
    currencyFlag: '🇪🇺',
    originalValue: 10.25,
    originalCurrency: 'USD',
    originalCurrencyFlag: '🇺🇸',
    fxRateDate: '2024-03-06',
    fxDaysBack: 0,
};

/** A plot wide enough to stay daily: DATA's 8 points — or CALENDAR_DAYS' 35 — are far below 1.3 points a pixel. */
const DAILY_PLOT_WIDTH = 1200;
/** CALENDAR_DAYS over 10 px: 3.5 days a pixel turns it weekly, and its 5 weeks (0.5 a pixel) keep it there; OPEN_DAYS too (1.7 days, 0.3 weeks a pixel). */
const WEEKLY_PLOT_WIDTH = 10;
/** CALENDAR_DAYS over 3 px: even its 5 weeks are 1.7 a pixel, so it turns monthly and stays there. */
const MONTHLY_PLOT_WIDTH = 3;

/**
 * Every calendar day from Monday 26 February to Sunday 31 March 2024: five whole weeks, the end of February and
 * all of March. A point on every day — weekends included — puts each week's and each month's last day on the
 * axis, which is where the chart places a period's events.
 */
const CALENDAR_DAYS: LineDataPoint[] = Array.from({length: 35}, (_unused, index) => ({date: new Date(Date.UTC(2024, 1, 26 + index)).toISOString().slice(0, 10), value: 100 + index}));

/** CALENDAR_DAYS' x-axis drawn weekly — one point per week, on its last day — and monthly. */
const WEEK_ENDS = ['2024-03-03', '2024-03-10', '2024-03-17', '2024-03-24', '2024-03-31'];
const MONTH_ENDS = ['2024-02-29', '2024-03-31'];

/**
 * CALENDAR_DAYS cut on Wednesday 13 March 2024: a series that stops inside a week and inside a month, drawn as the
 * read path draws one — every calendar day up to its last. Its last week (11–17 March) and its month are still
 * open: their points sit on the 13th, while the buckets' theoretical ends are Sunday 17 and the 31st.
 */
const OPEN_LAST_DAY = '2024-03-13';
const OPEN_DAYS: LineDataPoint[] = CALENDAR_DAYS.filter((point) => point.date <= OPEN_LAST_DAY);
/** The Monday the open week starts on. */
const OPEN_WEEK_MONDAY = '2024-03-11';
/** OPEN_DAYS' x-axis drawn weekly and monthly: the open week's and the open month's points on its last day. */
const OPEN_WEEK_ENDS = ['2024-03-03', '2024-03-10', OPEN_LAST_DAY];
const OPEN_MONTH_ENDS = ['2024-02-29', OPEN_LAST_DAY];
/** OPEN_DAYS over 2 px: its 3 weeks are 1.5 a pixel, so it turns monthly (over 3 px they are 1.0, and it stays weekly). */
const OPEN_MONTHLY_PLOT_WIDTH = 2;
/** A dividend on Tuesday 12 March, inside the open week and the open month: its marker sits on their point, the 13th (R-5). */
const OPEN_DIVIDEND: EventMarker = {date: '2024-03-12', type: 'DIVIDEND', value: 1.5, currency: 'EUR', currencyFlag: '🇪🇺'};

/** Two dividends in the first week of CALENDAR_DAYS (26 February – 3 March): one weekly point lists both. */
const WEEK_DIVIDENDS: EventMarker[] = [
    {date: '2024-02-27', type: 'DIVIDEND', value: 1.25, currency: 'EUR', currencyFlag: '🇪🇺'},
    {date: '2024-02-29', type: 'DIVIDEND', value: 2.5, currency: 'EUR', currencyFlag: '🇪🇺'},
];

/**
 * The calendar return's context of Monday 4 March 2024: a year back is Saturday 4 March 2023, priced on the
 * Friday before; today's price is Friday's too, converted at Friday's rate; the year-back rate is missing.
 */
const CALENDAR_CONTEXT: CalendarReturnPointContext = {
    status: 'available',
    referenceTargetDate: '2023-03-04',
    referencePriceDate: '2023-03-03',
    currentPriceDate: '2024-03-01',
    currentFxDate: '2024-03-01',
    referenceFxDate: null,
};

/** An overlay whose point of Monday 4 March stands for Friday's observation: its row says so with chart.tooltip.valueAt. */
const PEER: RenderedSignal = {
    id: 'peer',
    label: 'Peer',
    data: [{date: '2024-03-04', value: 1.5, representativeDate: '2024-03-01'}],
    color: '#ff7f0e',
    lineWidth: 1,
    lineType: 'solid',
    markerStart: null,
    markerEnd: null,
    yAxisIndex: 0,
    aggregationProfile: 'last_with_range',
};

type Formatter = (params: unknown) => string;

interface EventPoint {
    value: [string, number];
    marker?: EventMarker;
    markers?: EventMarker[];
}

interface EventSeries {
    name: string;
    type: string;
    data: EventPoint[];
    tooltip: {formatter: Formatter};
}

/** The event series of the last draw: the scatter series the component names `Events: <type>`. */
function eventSeries(): EventSeries[] {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const option = [...calls].reverse().find((call) => Array.isArray(call.option.series))?.option;
    const series = (option?.series ?? []) as EventSeries[];
    return series.filter((entry) => entry.type === 'scatter' && String(entry.name).startsWith('Events: '));
}

/** A tooltip's lines — what `<br>` separates — as text, the spaces of the markup collapsed. */
function tooltipLines(html: string): string[] {
    const template = document.createElement('template');
    template.innerHTML = html;
    const lines = [''];
    const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (node.nodeName === 'BR') lines.push('');
        else if (node.nodeType === Node.TEXT_NODE) lines[lines.length - 1] += node.textContent ?? '';
    }
    // Only the markup's own spaces: a no-break space Intl writes inside a figure is part of the contract.
    return lines.map((line) => line.replace(/[ \t\r\n]+/g, ' ').trim());
}

/** The lines of `marker`'s tooltip, from the formatter of the series that holds its point, called with that point. */
async function tooltipOf(marker: EventMarker): Promise<string[]> {
    await waitFor(() => expect(eventSeries().length, 'barrier: the chart drew its event series').toBeGreaterThan(0), {timeout: 5_000});
    for (const series of eventSeries()) {
        const point = series.data.find((candidate) => candidate.marker?.date === marker.date && candidate.marker?.type === marker.type);
        if (point) return tooltipLines(series.tooltip.formatter({data: point}));
    }
    throw new Error(`No event series holds a point of its own for the ${marker.type} of ${marker.date}: the chart is not at the daily resolution`);
}

/** A catalogue message with its values, as the interface language words it. */
function catalogue(key: string, values: Record<string, string>): string {
    return get(_)(key, {values});
}

/** `value` with exactly `digits` decimals, as Intl writes it in `locale`. */
function fixed(value: number, digits: number, locale: string): string {
    return new Intl.NumberFormat(locale, {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value);
}

/**
 * The calendar day `iso` (`YYYY-MM-DD`) in the house notation of a tooltip day, as Intl writes it in `locale`:
 * numeric year, short month, numeric day — `4 mar 2024`, `4 mars 2024`, `Mar 4, 2024`. The oracle of every
 * T-ISO expectation, never a typed date; the control case below ties it to the lot charts' `formatAxisDate`.
 */
function houseDay(iso: string, locale: string): string {
    const [year, month, day] = iso.split('-').map(Number);
    return new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(year, month - 1, day));
}

/** The month of the day `iso` as Intl writes it in `locale` — `febbraio 2024`: the monthly header's first line, localized already. */
function monthOf(iso: string, locale: string): string {
    return new Intl.DateTimeFormat(locale, {month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(`${iso}T00:00:00Z`));
}

/** Where a day stands in a T-EN1 line once its notation is set aside. */
const DAY = '⟨day⟩';

/**
 * `line` with the day `iso` replaced by `DAY`, whether written as ISO or in the house notation of the interface
 * locale. T-EN1's cases are about the words around a day; how the day itself is written is T-ISO's (below).
 */
function sansDay(line: string, iso: string): string {
    return line.split(houseDay(iso, uiLocale())).join(DAY).split(iso).join(DAY);
}

/** The two conversion lines of `marker`'s tooltip, as the catalogue and Intl write them in `locale` — the rate's day set aside (`DAY`). */
function conversionLines(marker: EventMarker, locale: string): string[] {
    // Four decimals: since C-97c-3 an amount shows as many as its first four significant digits need, four at least;
    // the amounts T-EN1 reads (1234.56789, 10.25) show exactly four before and after that cure.
    const original = `${catalogue('chart.tooltip.originalValue', {value: fixed(marker.originalValue!, 4, locale)})} (${marker.originalCurrencyFlag} ${marker.originalCurrency})`;
    const rateDate = catalogue('chart.tooltip.fxRateDate', {date: DAY});
    const lag = marker.fxDaysBack! > 0 ? ` ${catalogue('chart.tooltip.fxDaysBack', {days: fixed(marker.fxDaysBack!, 0, locale)})}` : '';
    return [original, `${rateDate}${lag}`];
}

/** The conversion lines of `marker`'s tooltip as the chart wrote them — its last two — with the rate's day set aside. */
function writtenConversionLines(lines: string[], marker: EventMarker): string[] {
    return lines.slice(-2).map((line) => sansDay(line, marker.fxRateDate!));
}

/** Lines with their no-break spaces spelled out, so a failure tells U+00A0 and U+202F from a space. */
function spelled(lines: string[]): string[] {
    return lines.map((line) => line.replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`));
}

/** Switch the interface language in place, as the language selector does; answer the locale it now writes figures in. */
async function speak(lang: UiLanguage): Promise<string> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    return uiLocale();
}

/** The chart, both converted dividends on it, drawn in the current interface language. */
function mountChart(): void {
    render(PriceChartFull, {props: {data: DATA, currency: 'EUR', eventMarkers: [BACKFILLED, SAME_DAY]}});
}

/** The tooltips of both dividends, each checked to be the daily tooltip of its own event. */
async function bothTooltips(): Promise<{backfilled: string[]; sameDay: string[]}> {
    const backfilled = await tooltipOf(BACKFILLED);
    const sameDay = await tooltipOf(SAME_DAY);
    expect([sansDay(backfilled[0], BACKFILLED.date), sansDay(sameDay[0], SAME_DAY.date)], 'barrier: each tooltip is the daily one of its event, headed by its day (in either notation: how the day is written is T-ISO’s)').toEqual([DAY, DAY]);
    return {backfilled, sameDay};
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    chartInstances.length = 0;
    plot.width = DAILY_PLOT_WIDTH;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 400, width: 800, height: 400, toJSON: () => ({})} as DOMRect);
});

afterEach(async () => {
    cleanup();
    vi.restoreAllMocks();
    // The language is module-level state shared by every case of the file.
    await speak('en');
    await setupI18n('en');
});

describe('PriceChartFull — a converted event’s tooltip in the interface language (T-EN1)', () => {
    it.each(LANGUAGES)('%s interface: the original amount and the FX rate’s date are worded by the catalogue — with the lag only when there is one — the figures in the interface notation', async (lang) => {
        const locale = await speak(lang);
        expect(locale, `control: a ${lang} interface on jsdom’s en-US browser writes bare ${lang}`).toBe(lang);
        expect(fixed(BACKFILLED.originalValue!, 4, locale), 'premise: the original amount is written another way than in English').not.toBe(fixed(BACKFILLED.originalValue!, 4, 'en-US'));
        mountChart();

        const {backfilled, sameDay} = await bothTooltips();

        expect({backfilled: spelled(writtenConversionLines(backfilled, BACKFILLED)), sameDay: spelled(writtenConversionLines(sameDay, SAME_DAY))}, `the conversion lines are not in the ${lang} interface's words: the component writes «orig.», «fx @» and «d back» in English`).toEqual({
            backfilled: spelled(conversionLines(BACKFILLED, locale)),
            sameDay: spelled(conversionLines(SAME_DAY, locale)),
        });
    });

    it('the three lines are read from their keys: in a marker locale — where chart.tooltip.originalValue, fxRateDate and fxDaysBack read as markers of themselves — no English is left', async () => {
        // The four catalogues word the original amount alike (`orig. {value}`), so only a locale whose words
        // are markers can tell a line read from the catalogue from a literal left in the component. The
        // language store stays English: the figures are written in en-US, the words are the markers'.
        addMessages(MARKER_LOCALE, {
            'chart.tooltip.originalValue': '⟦chart.tooltip.originalValue value={value}⟧',
            'chart.tooltip.fxRateDate': '⟦chart.tooltip.fxRateDate date={date}⟧',
            'chart.tooltip.fxDaysBack': '⟦chart.tooltip.fxDaysBack days={days}⟧',
        });
        await setupI18n(MARKER_LOCALE);
        const locale = uiLocale();
        expect(catalogue('chart.tooltip.fxDaysBack', {days: '3'}), 'control: the marker locale is live').toBe('⟦chart.tooltip.fxDaysBack days=3⟧');
        mountChart();

        const {backfilled, sameDay} = await bothTooltips();

        expect({backfilled: writtenConversionLines(backfilled, BACKFILLED), sameDay: writtenConversionLines(sameDay, SAME_DAY)}, 'a conversion line is not read from its key: the component still writes it').toEqual({
            backfilled: conversionLines(BACKFILLED, locale),
            sameDay: conversionLines(SAME_DAY, locale),
        });
    });

    it('English interface: the conversion lines read exactly as they do today — the English catalogue around figures in the interface notation, the rate’s day aside (guard)', async () => {
        const locale = await speak('en');
        expect(locale, 'control: an English interface on jsdom’s en-US browser writes en-US').toBe('en-US');
        mountChart();

        const {backfilled, sameDay} = await bothTooltips();

        expect({backfilled: writtenConversionLines(backfilled, BACKFILLED), sameDay: writtenConversionLines(sameDay, SAME_DAY)}, 'the English conversion lines moved').toEqual({
            backfilled: conversionLines(BACKFILLED, locale),
            sameDay: conversionLines(SAME_DAY, locale),
        });
    });
});

// =========================================================================
// T-ISO — every day a tooltip writes, in the house notation of the interface locale
// =========================================================================

/** What ECharts hands an axis tooltip for one series under the pointer. */
interface AxisItem {
    seriesName: string;
    value: number | number[];
    seriesType?: string;
}

/** The option of the last full draw: the last `setOption` that carries the axis tooltip. */
function lastDraw(): Record<string, unknown> {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const draw = [...calls].reverse().find((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function');
    return draw?.option ?? {};
}

/** The days on the last draw's x-axis: one per bucket, so they tell the resolution it drew at. */
function axisDays(): string[] {
    const xAxis = lastDraw().xAxis;
    const axis = (Array.isArray(xAxis) ? xAxis[0] : xAxis) as {data?: string[]} | undefined;
    return axis?.data ?? [];
}

/** Waits for the last draw's x-axis to hold `days`: the barrier that the chart drew at the resolution a case reads. */
async function drawnOver(days: string[], resolution: ChartResolution): Promise<void> {
    await waitFor(() => expect(axisDays(), `barrier: the chart drew ${resolution}, one point per bucket`).toEqual(days), {timeout: 5_000});
}

/** The axis tooltip's HTML with the pointer on `day` over `items`, from the formatter the chart handed ECharts. */
function axisTooltipHtml(day: string, items: AxisItem[]): string {
    const formatter = (lastDraw().tooltip as {formatter: Formatter}).formatter;
    return formatter(items.map((item) => ({axisValue: day, seriesType: 'line', color: '#2563eb', ...item})));
}

/** What a line says in its last brackets — `(…)` closing it — or undefined when it closes on none. */
function lastBrackets(line: string | undefined): string | undefined {
    return /\(([^()]*)\)$/.exec(line ?? '')?.[1];
}

/** The one coarse point that lists `markers` — their period — with the day it sits on (`value[0]`) and its tooltip's lines, from the formatter of the series that holds it. */
async function periodPointOf(markers: EventMarker[]): Promise<{day: string; lines: string[]}> {
    const days = markers.map((marker) => marker.date).join(',');
    await waitFor(() => expect(eventSeries().length, 'barrier: the chart drew its event series').toBeGreaterThan(0), {timeout: 5_000});
    for (const series of eventSeries()) {
        const point = series.data.find((candidate) => candidate.markers?.map((marker) => marker.date).join(',') === days);
        if (point) return {day: point.value[0], lines: tooltipLines(series.tooltip.formatter({data: point}))};
    }
    throw new Error(`No event point lists the period of ${days}: the chart is not at a coarser resolution, or the period's last day is not on its axis`);
}

/** The tooltip of the one coarse point that lists `markers` — their period. */
async function periodTooltipOf(markers: EventMarker[]): Promise<string[]> {
    return (await periodPointOf(markers)).lines;
}

/** The day each listed event is dated by: the line before each line that names an event of `type`. */
function eventDaysIn(lines: string[], type: string): string[] {
    return lines.flatMap((line, index) => (index > 0 && line === type ? [lines[index - 1]] : []));
}

/** PriceChartFull over `props` (DATA in euros by default), in the current interface language, on a plot `width` px wide. */
function mountPriceChart(props: Partial<ComponentProps<typeof PriceChartFull>>, width = DAILY_PLOT_WIDTH): void {
    plot.width = width;
    render(PriceChartFull, {props: {data: DATA, currency: 'EUR', ...props}});
}

describe('PriceChartFull — every day its tooltips write, in the house notation of the interface locale (T-ISO)', () => {
    it('control: the oracle writes a day as the lot charts’ tooltips do — formatAxisDate(locale, day, true) — and never as ISO, in it, fr and en-US', () => {
        const written = ['it', 'fr', 'en-US'].flatMap((locale) => ['2024-03-04', '2024-02-29', '2023-03-03'].map((day) => ({locale, day, oracle: houseDay(day, locale), lots: formatAxisDate(locale, day, true)})));

        expect(
            written.filter(({oracle, lots}) => oracle !== lots),
            'the oracle and the lot charts’ formatter disagree',
        ).toEqual([]);
        expect(
            written.filter(({oracle, day}) => oracle === day),
            'a locale writes a day as ISO: no red could tell the cure',
        ).toEqual([]);
    });

    it.each(['it', 'fr', 'en'] as const)('%s interface: a daily point’s axis tooltip is headed by its day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({});
        await drawnOver(
            DATA.map((point) => point.date),
            'daily',
        );

        const [header] = tooltipLines(axisTooltipHtml('2024-03-04', [{seriesName: 'EUR', value: 105}]));

        expect(header, `the daily header is not the day in the ${lang} interface’s notation (${locale}): the tooltip writes the ISO day`).toBe(houseDay('2024-03-04', locale));
    });

    it.each(LANGUAGES)('%s interface: a weekly point’s axis tooltip is headed by chart.tooltip.weekRange around the week’s first and last day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: CALENDAR_DAYS}, WEEKLY_PLOT_WIDTH);
        await drawnOver(WEEK_ENDS, 'weekly');

        const [header] = tooltipLines(axisTooltipHtml('2024-03-03', [{seriesName: 'EUR', value: 106}]));

        expect(header, `the week is not bounded by days in the ${lang} interface’s notation: weekRange gets the ISO days`).toBe(catalogue('chart.tooltip.weekRange', {start: houseDay('2024-02-26', locale), end: houseDay('2024-03-03', locale)}));
    });

    it.each(LANGUAGES)('%s interface: a monthly point’s axis tooltip is headed by its month, over chart.tooltip.valueAt around the month’s last day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: CALENDAR_DAYS}, MONTHLY_PLOT_WIDTH);
        await drawnOver(MONTH_ENDS, 'monthly');

        const [month, valueAt] = tooltipLines(axisTooltipHtml('2024-02-29', [{seriesName: 'EUR', value: 103}]));

        expect({month, valueAt}, `the month’s «value at» day is not in the ${lang} interface’s notation: valueAt gets the ISO day (the month above it is localized already)`).toEqual({
            month: catalogue('chart.tooltip.monthLabel', {month: monthOf('2024-02-29', locale)}),
            valueAt: catalogue('chart.tooltip.valueAt', {date: houseDay('2024-02-29', locale)}),
        });
    });

    it.each(LANGUAGES)('%s interface: the calendar return’s rows — ↩ the reference day · valueAt its price’s day, 📅 valueAt the current price’s day, 💱 the two FX days with — for a missing one — and an overlay’s valueAt its representative day: every day in the house notation', async (lang) => {
        const locale = await speak(lang);
        // As the asset page draws the calendar return: percentages, no delta, the context of each point.
        mountPriceChart({valueUnit: 'percentage', showMainDelta: false, mainPointContext: new Map([['2024-03-04', CALENDAR_CONTEXT]]), overlaySignals: [PEER]});
        await drawnOver(
            DATA.map((point) => point.date),
            'daily',
        );

        const lines = tooltipLines(
            axisTooltipHtml('2024-03-04', [
                {seriesName: 'EUR', value: 4},
                {seriesName: PEER.label, value: 1.5},
            ]),
        );

        expect(
            {
                reference: lines.find((line) => line.startsWith('↩')),
                currentPrice: lines.find((line) => line.startsWith('📅')),
                fx: lines.find((line) => line.startsWith('💱')),
                representative: lastBrackets(lines.find((line) => line.startsWith(`${PEER.label}:`))),
            },
            `the rows’ days are not in the ${lang} interface’s notation: ↩, 📅, 💱 and the overlay’s «value at» write ISO days`,
        ).toEqual({
            reference: `↩ ${houseDay('2023-03-04', locale)} · ${catalogue('chart.tooltip.valueAt', {date: houseDay('2023-03-03', locale)})}`,
            currentPrice: `📅 ${catalogue('chart.tooltip.valueAt', {date: houseDay('2024-03-01', locale)})}`,
            fx: `💱 ${houseDay('2024-03-01', locale)} / —`,
            representative: catalogue('chart.tooltip.valueAt', {date: houseDay('2024-03-01', locale)}),
        });
    });

    it.each(LANGUAGES)('%s interface: a daily event’s tooltip is headed by its day, and its FX line is chart.tooltip.fxRateDate around the rate’s day — both in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({eventMarkers: [BACKFILLED]});

        const lines = await tooltipOf(BACKFILLED);

        expect({heading: lines[0], fx: lines.at(-1)}, `the event’s days are not in the ${lang} interface’s notation: its heading and fxRateDate write ISO days`).toEqual({
            heading: houseDay(BACKFILLED.date, locale),
            fx: `${catalogue('chart.tooltip.fxRateDate', {date: houseDay(BACKFILLED.fxRateDate!, locale)})} ${catalogue('chart.tooltip.fxDaysBack', {days: fixed(BACKFILLED.fxDaysBack!, 0, locale)})}`,
        });
    });

    it.each(LANGUAGES)('%s interface: a weekly event tooltip lists the events of its period, each dated in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: CALENDAR_DAYS, eventMarkers: WEEK_DIVIDENDS}, WEEKLY_PLOT_WIDTH);
        await drawnOver(WEEK_ENDS, 'weekly');

        const lines = await periodTooltipOf(WEEK_DIVIDENDS);
        expect(lines, 'barrier: the tooltip lists the events of its period').toContain(catalogue('chart.tooltip.eventsInPeriod', {}));

        expect(eventDaysIn(lines, 'DIVIDEND'), `the period’s events are not dated in the ${lang} interface’s notation: each entry writes its ISO day`).toEqual(WEEK_DIVIDENDS.map((marker) => houseDay(marker.date, locale)));
    });
});

// =========================================================================
// C-97c-3 — a price in a tooltip keeps its significant digits
// =========================================================================

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10): a price on screen keeps its significant digits. Four of the
 * chart's tooltip figures are written with four fixed decimals, `formatFixed(…, 4)`: the bucket value an event point
 * sits on (the 💰 line under its heading), the event's value (💰 and its currency badge), its original value inside
 * `chart.tooltip.originalValue`, and the value of each row of the axis tooltip. On an asset priced in millionths each
 * reads `0.0000`. The contract: `formatPrice(…, {minDecimals: 4})` — four decimals at least, as many as the first four
 * significant digits need (`priceFractionDigits`, formatFixed.ts): 0.0000034573 reads 0.000003457, while 1.0834 stays
 * 1.0834 and 65000.1234 stays 65,000.1234. The FX lag beside the rate's day is a count of days, not a price: T-EN1 reads
 * it, and it does not move.
 *
 * Reds: a dividend of 0.0000034573 EUR converted from 0.0000037512 USD, paid on a day priced 0.0000034573 — its bucket
 * value, its value, its original value — and the axis row of that price. Guards, green today and after: the same lines
 * for a dividend of 65000.1234 EUR converted from 1.0834 USD on a day priced 1.0834, and the axis rows of both figures.
 *
 * Reading, as the T-EN1 and T-ISO cases read: an event's lines from the formatter its scatter series hands ECharts,
 * called with its point; the axis rows from the axis formatter, called with the series under the pointer. A line is told
 * apart by what the code writes around its figure — the 💰 of a value, the currency badge of the event's value and of
 * the original value, the series name of a row — and the figure is matched as a whole number token; the original
 * value's line is compared whole, its words from the catalogue. The axis is drawn with `showMainDelta: false`: the Δ
 * suffix is `buildDeltaHtml`'s, read in priceChartHelpers.test.ts. English UI on jsdom's en-US browser, checked before
 * each case: the digits are typed.
 */
describe('PriceChartFull — a price in its tooltips keeps its significant digits (C-97c-3, D-C97c-1)', () => {
    /** The day the dividends are paid: DATA's Monday 4 March. */
    const PAY_DAY = '2024-03-04';
    /** A price in millionths, a dividend of the same size and its original amount in dollars. */
    const TINY = {price: 0.0000034573, value: 0.0000034573, original: 0.0000037512};
    /** A rate-sized price and original amount, and a dividend with a thousands separator. */
    const PLAIN = {price: 1.0834, value: 65000.1234, original: 1.0834};

    /** DATA's days, priced at `price` on PAY_DAY and a little below on the others. */
    function pricedAt(price: number): LineDataPoint[] {
        return DATA.map(({date}) => ({date, value: date === PAY_DAY ? price : price * 0.97}));
    }

    /** A dividend paid on PAY_DAY in dollars, shown in euros at that day's rate (no lag). */
    function dividendOf(value: number, original: number): EventMarker {
        return {date: PAY_DAY, type: 'DIVIDEND', value, currency: 'EUR', currencyFlag: '🇪🇺', originalValue: original, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸', fxRateDate: PAY_DAY, fxDaysBack: 0};
    }

    /** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** The price lines of `marker`'s tooltip: the bucket value (💰 alone), the event's value (💰 and the 🇪🇺 EUR badge), the original value (closed by the 🇺🇸 USD badge). */
    async function eventPriceLines(marker: EventMarker): Promise<{bucket: string; value: string; original: string}> {
        const lines = await tooltipOf(marker);
        const values = lines.filter((line) => line.startsWith('💰'));
        const found = {
            bucket: values.filter((line) => !line.includes('(')),
            value: values.filter((line) => line.includes('(🇪🇺 EUR)')),
            original: lines.filter((line) => line.endsWith('(🇺🇸 USD)')),
        };
        expect(Object.fromEntries(Object.entries(found).map(([name, matches]) => [name, matches.length])), 'barrier: the tooltip holds one bucket value, one event value with its badge, one original value with its own').toEqual({bucket: 1, value: 1, original: 1});
        return {bucket: found.bucket[0], value: found.value[0], original: found.original[0]};
    }

    /** The axis tooltip's row of the main series — named after the currency — with the pointer on PAY_DAY at `value`. */
    function axisRowAt(value: number): string {
        const rows = tooltipLines(axisTooltipHtml(PAY_DAY, [{seriesName: 'EUR', value}])).filter((line) => line.includes('EUR:'));
        expect(rows, 'barrier: one row for the main series').toHaveLength(1);
        return rows[0];
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the tooltips are written en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('an event on an asset priced in millionths: its bucket value, its value and its original value read their four significant digits, not 0.0000', async () => {
        const marker = dividendOf(TINY.value, TINY.original);
        mountPriceChart({data: pricedAt(TINY.price), eventMarkers: [marker]});

        const {bucket, value, original} = await eventPriceLines(marker);

        expect.soft(bucket, 'the bucket value, the price the event sits on (today 💰 0.0000)').toMatch(numberToken('0.000003457'));
        expect.soft(value, 'the event’s value (today 💰 0.0000 and its badge)').toMatch(numberToken('0.000003457'));
        expect.soft(original, 'the original value, inside chart.tooltip.originalValue (today 0.0000)').toBe(`${catalogue('chart.tooltip.originalValue', {value: '0.000003751'})} (🇺🇸 USD)`);
    });

    it('guard: an event at 1.0834 and 65000.1234 keeps its four decimals — the bucket value 1.0834, the value 65,000.1234, the original 1.0834', async () => {
        const marker = dividendOf(PLAIN.value, PLAIN.original);
        mountPriceChart({data: pricedAt(PLAIN.price), eventMarkers: [marker]});

        const {bucket, value, original} = await eventPriceLines(marker);

        expect.soft(bucket, 'the bucket value').toMatch(numberToken('1.0834'));
        expect.soft(value, 'the event’s value').toMatch(numberToken('65,000.1234'));
        expect.soft(original, 'the original value').toBe(`${catalogue('chart.tooltip.originalValue', {value: '1.0834'})} (🇺🇸 USD)`);
    });

    it('the axis row of a price in millionths reads 0.000003457, not 0.0000', async () => {
        mountPriceChart({data: pricedAt(TINY.price), showMainDelta: false});
        await drawnOver(
            DATA.map((point) => point.date),
            'daily',
        );

        expect(axisRowAt(TINY.price), 'the main series’ row (today EUR: 0.0000)').toMatch(numberToken('0.000003457'));
    });

    it('guard: the axis rows of 1.0834 and of 65000.1234 keep their four decimals', async () => {
        mountPriceChart({data: pricedAt(PLAIN.price), showMainDelta: false});
        await drawnOver(
            DATA.map((point) => point.date),
            'daily',
        );

        expect.soft(axisRowAt(1.0834), 'the row of 1.0834').toMatch(numberToken('1.0834'));
        expect.soft(axisRowAt(65000.1234), 'the row of 65000.1234').toMatch(numberToken('65,000.1234'));
    });
});

/** CandlestickChart as PriceChartFull mounts it: `synthesizeDailyOHLC` of the daily data, aggregated at a coarser resolution. */
function mountCandles(daily: LineDataPoint[], resolution: ChartResolution): void {
    const candles = synthesizeDailyOHLC(daily);
    render(CandlestickChart, {props: {data: resolution === 'daily' ? candles : aggregateOHLCV(candles, resolution), resolution, currency: 'EUR'}});
}

/** The candles' tooltip header with the pointer on `day`: its first `blocks` blocks — the day or the week, or the month over its valueAt. */
function candleHeader(day: string, blocks: number): string[] {
    const template = document.createElement('template');
    template.innerHTML = axisTooltipHtml(day, [{seriesName: 'EUR', seriesType: 'candlestick', value: [0, 100, 101, 99, 102]}]);
    return [...template.content.children].slice(0, blocks).map((block) => (block.textContent ?? '').replace(/[ \t\r\n]+/g, ' ').trim());
}

describe('CandlestickChart — the price chart’s candles: the tooltip’s header in the house notation (T-ISO)', () => {
    it.each(LANGUAGES)('%s interface: a daily candle’s tooltip is headed by its day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountCandles(DATA, 'daily');
        await drawnOver(
            DATA.map((point) => point.date),
            'daily',
        );

        expect(candleHeader('2024-03-04', 1), `the candle’s day is not in the ${lang} interface’s notation: the header writes the ISO day`).toEqual([houseDay('2024-03-04', locale)]);
    });

    it.each(LANGUAGES)('%s interface: a weekly candle’s tooltip is headed by chart.tooltip.weekRange around the week’s first and last day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountCandles(CALENDAR_DAYS, 'weekly');
        await drawnOver(WEEK_ENDS, 'weekly');

        expect(candleHeader('2024-03-03', 1), `the candle’s week is not bounded by days in the ${lang} interface’s notation: weekRange gets the ISO days`).toEqual([catalogue('chart.tooltip.weekRange', {start: houseDay('2024-02-26', locale), end: houseDay('2024-03-03', locale)})]);
    });

    it.each(LANGUAGES)('%s interface: a monthly candle’s tooltip is headed by its month, over chart.tooltip.valueAt around the month’s last day in the house notation', async (lang) => {
        const locale = await speak(lang);
        mountCandles(CALENDAR_DAYS, 'monthly');
        await drawnOver(MONTH_ENDS, 'monthly');

        expect(candleHeader('2024-02-29', 2), `the candle’s «value at» day is not in the ${lang} interface’s notation: valueAt gets the ISO day (the month above it is localized already)`).toEqual([
            catalogue('chart.tooltip.monthLabel', {month: monthOf('2024-02-29', locale)}),
            catalogue('chart.tooltip.valueAt', {date: houseDay('2024-02-29', locale)}),
        ]);
    });
});

describe('the open week and month: a coarse tooltip spans up to the day its point sits on (after R-5)', () => {
    /*
     * A weekly or monthly point — a line point or a candle — is dated by its bucket's last data point, while
     * `bucketEnd` keeps the bucket's theoretical end. In a whole period the two are one day (the whole-period cases
     * above, on WEEK_ENDS and MONTH_ENDS, are the guard of what does not change). In the open one — the period still
     * running, or a series that stops inside it, here OPEN_DAYS through Wednesday 13 March — the point sits on its
     * last data day, and a header spanning to `bucketEnd` names Sunday 17 or the 31st: a day with no data, or still
     * to come.
     *
     * The contract, after the cure (`bucketSpanUpTo`): every coarse header of such a point spans up to the point's
     * own day — a weekly one is `chart.tooltip.weekRange` from the week's Monday to that day, a monthly one the
     * same `chart.tooltip.monthLabel` over `chart.tooltip.valueAt` of that day — on the axis tooltip, on the
     * candle's, and on the tooltip of an event marker sitting on the point (its scatter `value[0]`, R-5): the
     * header and the point name the same day. Days in the house notation, words from the catalogue.
     */

    it.each(LANGUAGES)('%s interface: the open week’s point — its axis tooltip spans the week from its Monday up to the point’s own day, not to the Sunday', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: OPEN_DAYS}, WEEKLY_PLOT_WIDTH);
        await drawnOver(OPEN_WEEK_ENDS, 'weekly');

        const [header] = tooltipLines(axisTooltipHtml(OPEN_LAST_DAY, [{seriesName: 'EUR', value: 116}]));

        expect(header, 'the open week’s header runs to its Sunday, a day with no data: weekRange must end on the point’s own day').toBe(catalogue('chart.tooltip.weekRange', {start: houseDay(OPEN_WEEK_MONDAY, locale), end: houseDay(OPEN_LAST_DAY, locale)}));
    });

    it.each(LANGUAGES)('%s interface: the open month’s point — its axis tooltip is its month over chart.tooltip.valueAt of the point’s own day, not of the month’s last day', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: OPEN_DAYS}, OPEN_MONTHLY_PLOT_WIDTH);
        await drawnOver(OPEN_MONTH_ENDS, 'monthly');

        const [month, valueAt] = tooltipLines(axisTooltipHtml(OPEN_LAST_DAY, [{seriesName: 'EUR', value: 116}]));

        expect({month, valueAt}, 'the open month’s «value at» names its last day, a day with no data: it must name the point’s own day').toEqual({
            month: catalogue('chart.tooltip.monthLabel', {month: monthOf(OPEN_LAST_DAY, locale)}),
            valueAt: catalogue('chart.tooltip.valueAt', {date: houseDay(OPEN_LAST_DAY, locale)}),
        });
    });

    it.each(LANGUAGES)('%s interface: an event of the open week (weekly) — its marker’s tooltip is headed by the week up to the day its point sits on', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: OPEN_DAYS, eventMarkers: [OPEN_DIVIDEND]}, WEEKLY_PLOT_WIDTH);
        await drawnOver(OPEN_WEEK_ENDS, 'weekly');

        const {day, lines} = await periodPointOf([OPEN_DIVIDEND]);
        expect(day, 'barrier: the marker sits on the open week’s point, its last data day (R-5)').toBe(OPEN_LAST_DAY);

        expect(lines[0], 'the marker’s header and the point it sits on name two different days: the week runs to its Sunday').toBe(catalogue('chart.tooltip.weekRange', {start: houseDay(OPEN_WEEK_MONDAY, locale), end: houseDay(day, locale)}));
    });

    it.each(LANGUAGES)('%s interface: an event of the open month (monthly) — its marker’s tooltip is its month over chart.tooltip.valueAt of the day its point sits on', async (lang) => {
        const locale = await speak(lang);
        mountPriceChart({data: OPEN_DAYS, eventMarkers: [OPEN_DIVIDEND]}, OPEN_MONTHLY_PLOT_WIDTH);
        await drawnOver(OPEN_MONTH_ENDS, 'monthly');

        const {day, lines} = await periodPointOf([OPEN_DIVIDEND]);
        expect(day, 'barrier: the marker sits on the open month’s point, its last data day (R-5)').toBe(OPEN_LAST_DAY);

        expect(lines.slice(0, 2), 'the marker’s header and the point it sits on name two different days: «value at» names the month’s last day').toEqual([catalogue('chart.tooltip.monthLabel', {month: monthOf(day, locale)}), catalogue('chart.tooltip.valueAt', {date: houseDay(day, locale)})]);
    });

    it.each(LANGUAGES)('%s interface: the open week’s candle is headed by the week from its Monday up to its own day', async (lang) => {
        const locale = await speak(lang);
        mountCandles(OPEN_DAYS, 'weekly');
        await drawnOver(OPEN_WEEK_ENDS, 'weekly');

        expect(candleHeader(OPEN_LAST_DAY, 1), 'the open week’s candle runs to its Sunday, a day with no data: weekRange must end on the candle’s own day').toEqual([catalogue('chart.tooltip.weekRange', {start: houseDay(OPEN_WEEK_MONDAY, locale), end: houseDay(OPEN_LAST_DAY, locale)})]);
    });

    it.each(LANGUAGES)('%s interface: the open month’s candle is its month over chart.tooltip.valueAt of its own day', async (lang) => {
        const locale = await speak(lang);
        mountCandles(OPEN_DAYS, 'monthly');
        await drawnOver(OPEN_MONTH_ENDS, 'monthly');

        expect(candleHeader(OPEN_LAST_DAY, 2), 'the open month’s candle names its last day, a day with no data: «value at» must name the candle’s own day').toEqual([
            catalogue('chart.tooltip.monthLabel', {month: monthOf(OPEN_LAST_DAY, locale)}),
            catalogue('chart.tooltip.valueAt', {date: houseDay(OPEN_LAST_DAY, locale)}),
        ]);
    });
});

// =========================================================================
// Y-8 — the arrows a zoom re-aims: once the gesture settles, not on every tick
// =========================================================================

type FakeChart = (typeof chartInstances)[number];
type ChartOption = Record<string, unknown>;

/**
 * A trend over CALENDAR_DAYS' last two weeks with an arrow at each end (`markerStart`/`markerEnd: 'arrow'`): the
 * markers a zoom re-aims. It rises a unit a day, so each arrow has a slope to follow.
 */
const TREND: RenderedSignal = {
    id: 'trend',
    label: 'Trend',
    data: CALENDAR_DAYS.slice(-14).map((point, index) => ({date: point.date, value: 120 + index})),
    color: '#ff7f0e',
    lineWidth: 2,
    lineType: 'solid',
    markerStart: 'arrow',
    markerEnd: 'arrow',
    yAxisIndex: 0,
    aggregationProfile: 'last_with_range',
};

/** The days TREND's arrows sit on: its first and its last. */
const TREND_ENDS = [TREND.data[0].date, TREND.data[TREND.data.length - 1].date];

/** A dataZoom window: its start and end, in percent of the x-axis. */
interface ZoomWindow {
    start: number;
    end: number;
}

/**
 * One zoom gesture: the five windows its ticks close in on, around the period's middle. Each is played as a user's zoom
 * (`userZoom`): the held window moves, then `dataZoom` is emitted in 47-1's shape — CandlestickChart reads the window off
 * the event (47-1); PriceChartFull's handler takes none, and reads the settled window through `getOption()`. Either way
 * the window the gesture settles on is the one the chart reads, and the arrows' angles change with it (Y-25).
 */
const GESTURE: ZoomWindow[] = [10, 20, 30, 40, 45].map((inset) => ({start: inset, end: 100 - inset}));

/** The series a `setOption` payload carries, as a list. */
function seriesIn(option: ChartOption): ChartOption[] {
    const series = option.series;
    return (Array.isArray(series) ? series : series ? [series] : []) as ChartOption[];
}

/** The arrow markers a payload carries — each `markPoint` item drawn as an arrow — with its series, its day and its rotation. */
function arrowsIn(option: ChartOption): Array<{series: string; day: unknown; rotate: unknown}> {
    return seriesIn(option).flatMap((series) => {
        const items = ((series.markPoint as {data?: unknown[]} | undefined)?.data ?? []) as Array<{symbol?: unknown; coord?: unknown[]; symbolRotate?: unknown}>;
        return items.filter((item) => item.symbol === 'arrow').map((item) => ({series: String(series.name), day: item.coord?.[0], rotate: item.symbolRotate}));
    });
}

/** Whether an arrow is aimed: a finite rotation other than the 0 a draw builds it with — what the recorder's pixel grid gives. */
const aimed = (rotate: unknown): boolean => typeof rotate === 'number' && Number.isFinite(rotate) && rotate !== 0;

/** The arrows of each payload, by day, aimed or not. */
const aimOf = (options: ChartOption[]) => options.map((option) => arrowsIn(option).map(({day, rotate}) => ({day, aimed: aimed(rotate)})));

/** The payloads from call `since` on that carry `series`: an arrows' write-back (`setOption({series}, false)`), or a full draw. */
const seriesPayloadsSince = (chart: FakeChart, since: number): ChartOption[] =>
    chart.setOptionCalls
        .slice(since)
        .map(({option}) => option)
        .filter((option) => 'series' in option);

/** The payloads from call `since` on that set the x-axis and no series: the labels a settled zoom re-spaces (47-1). */
const labelPatchesSince = (chart: FakeChart, since: number): ChartOption[] =>
    chart.setOptionCalls
        .slice(since)
        .map(({option}) => option)
        .filter((option) => 'xAxis' in option && !('series' in option));

/** The index of the chart's last full draw: its last `setOption` that carries the axis tooltip. */
const lastDrawIndex = (chart: FakeChart): number => chart.setOptionCalls.findLastIndex((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function');

/**
 * Waits for the first-render stability pass to be over (`scheduleFirstRenderStabilityFix`): it resizes the chart — and
 * re-aims its arrows — at once, and once more when the box has held still for two animation frames. On a loaded
 * document, with no font face to await (jsdom has no `document.fonts`), those two are all of it. Fake timers go in only
 * after both: the second would otherwise land inside the gesture a case counts.
 */
async function stabilityPassOver(chart: FakeChart): Promise<void> {
    expect(document.readyState, 'premise: the document has loaded, so the stability pass awaits no load event').toBe('complete');
    await waitFor(() => expect(chart.resizeCount, 'barrier: the stability pass resized the chart twice — at once, and once its box held still').toBeGreaterThanOrEqual(2), {timeout: 5_000});
}

/** An 800 px panel however a chart measures it: its box (file-level `beforeEach`), its client and offset widths — LineChart's 47-1 panel. */
function panel800(): void {
    vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(800);
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(800);
}

/**
 * The last chart, once drawn daily over CALENDAR_DAYS with TREND's arrows, past its stability pass. Checks what the Y-8
 * cases stand on: the draw carries both arrows, unrotated as built; the chart listens to `dataZoom`; and the harness
 * really aims them — after the draw, a series write-back whose arrows the recorder's pixel grid turned — or every count
 * after it would be vacuous.
 */
async function armed(): Promise<FakeChart> {
    await drawnOver(
        CALENDAR_DAYS.map((point) => point.date),
        'daily',
    );
    const chart = chartInstances.at(-1);
    if (!chart) throw new Error('the chart was never created');
    expect(arrowsIn(lastDraw()), 'precondition: the draw carries TREND’s two arrows, on its first and last day, unrotated as built').toEqual(TREND_ENDS.map((day) => ({series: TREND.label, day, rotate: 0})));
    expect(chart.handlerCount('dataZoom'), 'precondition: the chart registered a dataZoom handler').toBeGreaterThan(0);
    await stabilityPassOver(chart);
    expect(aimOf(seriesPayloadsSince(chart, lastDrawIndex(chart) + 1)), 'precondition: the harness aims the arrows — after the draw, a series write-back carrying both, turned by the recorder’s pixel grid').toContainEqual(TREND_ENDS.map((day) => ({day, aimed: true})));
    return chart;
}

/** PriceChartFull over CALENDAR_DAYS with TREND's arrows — `props` on top — daily on a wide plot, armed for a gesture. */
async function mountTrendPriceChart(props: Partial<ComponentProps<typeof PriceChartFull>> = {}): Promise<FakeChart> {
    panel800();
    mountPriceChart({data: CALENDAR_DAYS, overlaySignals: [TREND], ...props}, DAILY_PLOT_WIDTH);
    return armed();
}

/** CandlestickChart as PriceChartFull mounts it at the daily resolution (`synthesizeDailyOHLC`), over CALENDAR_DAYS with TREND's arrows, armed for a gesture. */
async function mountTrendCandles(): Promise<FakeChart> {
    panel800();
    render(CandlestickChart, {props: {data: synthesizeDailyOHLC(CALENDAR_DAYS), resolution: 'daily', currency: 'EUR', overlaySignals: [TREND]}});
    return armed();
}

/**
 * Y-8 — a zoom gesture re-aims the arrows once it settles, not on every tick: PriceChartFull, and its candles.
 *
 * What it protects: the cost of a zoom (LineChart.test.ts tells the whole of it). An overlay's arrow markers are
 * re-aimed on a zoom by `updateArrowRotations`, which reads `getOption()` — a deep clone of the whole option — and
 * writes every series back; both charts' `dataZoom` handlers run it on every tick, up to ~60 a second while a gesture
 * moves, right under PriceChartFull's note never to read `getOption()` there. The contract, after the cure: a tick
 * reads no `getOption()` and writes no series; once the gesture pauses, the settle timer re-aims the arrows once —
 * CandlestickChart's 47-1 timer (`ZOOM_LABEL_SETTLE_MS`), with one read; PriceChartFull's 200 ms debounce, in the
 * branch that keeps the resolution, with two: the settled range it reads by design, and the arrows.
 *
 * Red today: each of the five ticks reads `getOption()` and writes the series back, and the settle re-aims nothing.
 *
 * How it is tested: as in LineChart.test.ts — the recorder holds the option as ECharts does and maps a point to pixels
 * (`gridPixel`), so a re-aim is computed and written back as on a screen (`armed` proves it); five ticks back to back,
 * counted, then fake timers past any debounce, counted again. The ticks are real zooms (`userZoom`, Y-25): each moves the
 * held window, so the window the gesture settles on gives the arrows new angles — since Y-25 a re-aim that turns no
 * arrow writes nothing back, and a settle on a window that never moved would leave the «one write-back» below vacuous,
 * or red for the wrong reason. Green before Y-25's cure and after it. Both charts draw daily: CandlestickChart mounted
 * as PriceChartFull mounts it at that resolution, PriceChartFull on a plot wide enough to stay daily — and its case
 * proves the gesture settled at the resolution it began at (no redraw, the labels re-spaced: the kept-resolution
 * branch, where the cure re-aims). Fake timers go in after the draw and its stability pass, which the barriers await on
 * real ones. The counts of the ticks and of the settle are soft: one red run reports all three.
 */
describe('PriceChartFull and its candles — a zoom re-aims the arrows once the gesture settles, not on every tick (Y-8)', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('PriceChartFull: five zoom ticks read no getOption() and write no series back; once the gesture settles at the daily resolution it began at, the arrows are re-aimed once', async () => {
        const chart = await mountTrendPriceChart();

        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        for (const window of GESTURE) chart.userZoom(window);

        expect
            .soft({getOptionReads: chart.getOptionCount, seriesWriteBacks: seriesPayloadsSince(chart, since).length}, 'Y-8: a zoom tick read getOption(), which deep-clones the whole option, and wrote every series back to re-aim the arrows — on each tick of one gesture')
            .toEqual({getOptionReads: 0, seriesWriteBacks: 0});

        const afterTicks = chart.setOptionCalls.length;
        await vi.advanceTimersByTimeAsync(1_000);
        expect(
            {redrawn: lastDrawIndex(chart) >= since, labelsRespaced: labelPatchesSince(chart, afterTicks).length > 0, axis: axisDays()},
            'barrier: the gesture settled at the resolution it began at — no redraw, the x labels re-spaced on the window (the debounce’s kept-resolution branch), the axis still daily',
        ).toEqual({redrawn: false, labelsRespaced: true, axis: CALENDAR_DAYS.map((point) => point.date)});

        expect.soft(aimOf(seriesPayloadsSince(chart, afterTicks)), 'Y-8: once the gesture settled, the arrows were not re-aimed exactly once — one series write-back, carrying both arrows, aimed').toEqual([TREND_ENDS.map((day) => ({day, aimed: true}))]);
        expect(chart.getOptionCount, 'Y-8: one gesture — its five ticks and its settle — read getOption() more than twice: the settled range, read once by design, and the arrows, once it settles').toBeLessThanOrEqual(2);
    });

    it('CandlestickChart: five zoom ticks read no getOption() and write no series back; once the gesture settles, the arrows are re-aimed once', async () => {
        const chart = await mountTrendCandles();

        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        for (const window of GESTURE) chart.userZoom(window);

        expect
            .soft({getOptionReads: chart.getOptionCount, seriesWriteBacks: seriesPayloadsSince(chart, since).length}, 'Y-8: a zoom tick read getOption(), which deep-clones the whole option, and wrote every series back to re-aim the arrows — on each tick of one gesture')
            .toEqual({getOptionReads: 0, seriesWriteBacks: 0});

        const afterTicks = chart.setOptionCalls.length;
        await vi.advanceTimersByTimeAsync(1_000);
        expect(labelPatchesSince(chart, afterTicks).length, 'barrier: the gesture settled — the 47-1 timer re-spaced the x labels on its window').toBeGreaterThan(0);

        expect.soft(aimOf(seriesPayloadsSince(chart, afterTicks)), 'Y-8: once the gesture settled, the arrows were not re-aimed exactly once — one series write-back, carrying both arrows, aimed').toEqual([TREND_ENDS.map((day) => ({day, aimed: true}))]);
        expect(chart.getOptionCount, 'Y-8: one gesture — its five ticks and its settle — read getOption() more than once: the arrows need one read, once it settles').toBeLessThanOrEqual(1);
    });
});

/** A colour before a rebuild, and after it. */
interface Repaint {
    before: string;
    after: string;
}

/** Whether `value` carries the colour `hex` (`#rrggbb`) anywhere: as the hex itself, or as `rgb()`/`rgba()` of its channels at any alpha — a gradient stop included. */
function carries(value: unknown, hex: string): boolean {
    const written = JSON.stringify(value) ?? '';
    const [r, g, b] = [1, 3, 5].map((at) => parseInt(hex.slice(at, at + 2), 16));
    return written.toLowerCase().includes(hex.toLowerCase()) || new RegExp(`rgba?\\(\\s*${r}\\s*,\\s*${g}\\s*,\\s*${b}\\s*[,)]`).test(written);
}

/** Which of `repaint`'s colours the series of `option` that `pick` selects carry; `absent` when the payload has no such series. */
function paintOf(option: ChartOption, pick: (series: ChartOption) => boolean, repaint: Repaint): 'absent' | 'before' | 'after' | 'both' | 'neither' {
    const picked = seriesIn(option).filter(pick);
    if (picked.length === 0) return 'absent';
    const before = carries(picked, repaint.before);
    const after = carries(picked, repaint.after);
    return before && after ? 'both' : before ? 'before' : after ? 'after' : 'neither';
}

/** The write-backs that bring a colour of before the rebuild back: carrying it anywhere, or with the picked series not in the new colour. */
function stalePaints(writeBacks: ChartOption[], pick: (series: ChartOption) => boolean, repaint: Repaint) {
    return writeBacks.map((option, index) => ({writeBack: index + 1, carriesBefore: carries(option, repaint.before), picked: paintOf(option, pick, repaint)})).filter(({carriesBefore, picked}) => carriesBefore || (picked !== 'absent' && picked !== 'after'));
}

/**
 * One zoom step, its settle included — fake timers from here on — and the series write-backs it brought. A real zoom
 * (`userZoom`): the held window moves to 40–60 %, so the settle's re-aim turns the arrows and writes them back — since
 * Y-25 a re-aim that turns no arrow writes nothing, and a step that moved nothing would leave the guard nothing to read.
 */
async function zoomOneStep(chart: FakeChart): Promise<ChartOption[]> {
    vi.useFakeTimers();
    const since = chart.setOptionCalls.length;
    chart.userZoom({start: 40, end: 60});
    await vi.advanceTimersByTimeAsync(1_000);
    return seriesPayloadsSince(chart, since);
}

/**
 * Y-8, colour guard — after a rebuild, the arrows' write-back carries the rebuild's colours: PriceChartFull, and its
 * candles.
 *
 * What it protects: what LineChart.test.ts' colour guard protects. The arrows' write-back carries every series, colours
 * included, so an option kept between zoom steps across a rebuild — a theme switch (`onThemeClassChange`), a Designer
 * Lab colour edit (`onChartColorsChange`) — would paint the old colours back at the next zoom. The contract: once the
 * chart is rebuilt, every series write-back a zoom brings carries the new colours, or none at all.
 *
 * Green today, and after the cure, by construction: `updateArrowRotations` reads `getOption()` afresh on each call. A
 * variant that keeps the first `getOption()` of a chart and never drops it on a rebuild turns both cases red.
 *
 * How it is tested: built in light, rebuilt in dark (the `dark` class on `<html>`, as the theme store writes it), then
 * one zoom step, its settle included (fake timers, after the barriers). The step is a real zoom (`zoomOneStep`): it
 * moves the window, so its settle turns the arrows and writes every series back, which a step that moved nothing would
 * no longer do once Y-25 writes back only a turned arrow. Green before Y-25's cure and after it. The colours are the
 * theme's own pairs: PriceChartFull's price line, its baseline colouring off (`PRICE_SERIES.line`), and the candles' gain
 * and loss (`CHART_GAIN_LOSS.price`). A colour is found in any notation the chart writes it: the hex, or `toRgba`'s
 * `rgba(r,g,b,a)` at any alpha, a gradient stop included. At least one write-back must come, or the guard reads
 * nothing. The `dark` class is reset after each case.
 */
describe('PriceChartFull and its candles — after a rebuild, the arrows’ write-back carries the rebuild’s colours (Y-8, colour guard)', () => {
    /** PriceChartFull's price line, light and dark, when it is not coloured against the baseline. */
    const LINE: Repaint = {before: PRICE_SERIES.line.light, after: PRICE_SERIES.line.dark};
    /** The candles' gain and loss, light and dark. */
    const GAIN: Repaint = {before: CHART_GAIN_LOSS.price.gain.light, after: CHART_GAIN_LOSS.price.gain.dark};
    const LOSS: Repaint = {before: CHART_GAIN_LOSS.price.loss.light, after: CHART_GAIN_LOSS.price.loss.dark};
    /** The price line's series — one, with its baseline colouring off — and the candles'. */
    const priceLine = (series: ChartOption) => series.name === 'EUR' && series.type === 'line';
    const candles = (series: ChartOption) => series.type === 'candlestick';

    beforeEach(() => {
        document.documentElement.classList.remove('dark');
    });

    afterEach(() => {
        vi.useRealTimers();
        // Module-level state every case of the file shares: the theme of <html>.
        document.documentElement.classList.remove('dark');
    });

    it('PriceChartFull: built in light, rebuilt in dark, one zoom step: every series write-back carries the dark price line, never the light one', async () => {
        const chart = await mountTrendPriceChart({colorByBaseline: false});
        expect(paintOf(lastDraw(), priceLine, LINE), 'precondition: the price line is drawn in its light colour').toBe('before');

        document.documentElement.classList.add('dark');
        await waitFor(() => expect(paintOf(lastDraw(), priceLine, LINE), 'barrier: the theme switch rebuilt the chart, the price line in its dark colour').toBe('after'), {timeout: 5_000});

        const writeBacks = await zoomOneStep(chart);

        expect(writeBacks.length, 'the zoom step brought no series write-back: the guard has nothing to read').toBeGreaterThan(0);
        expect(stalePaints(writeBacks, priceLine, LINE), 'Y-8 guard: a series write-back after the zoom brought the light price line back over the dark rebuild — an option kept from before the theme switch').toEqual([]);
    });

    it('CandlestickChart: built in light, rebuilt in dark, one zoom step: every series write-back carries the dark candles, never the light ones', async () => {
        const chart = await mountTrendCandles();
        expect({gain: paintOf(lastDraw(), candles, GAIN), loss: paintOf(lastDraw(), candles, LOSS)}, 'precondition: the candles are drawn in their light gain and loss').toEqual({gain: 'before', loss: 'before'});

        document.documentElement.classList.add('dark');
        await waitFor(() => expect({gain: paintOf(lastDraw(), candles, GAIN), loss: paintOf(lastDraw(), candles, LOSS)}, 'barrier: the theme switch rebuilt the chart, the candles in their dark gain and loss').toEqual({gain: 'after', loss: 'after'}), {timeout: 5_000});

        const writeBacks = await zoomOneStep(chart);

        expect(writeBacks.length, 'the zoom step brought no series write-back: the guard has nothing to read').toBeGreaterThan(0);
        expect({gain: stalePaints(writeBacks, candles, GAIN), loss: stalePaints(writeBacks, candles, LOSS)}, 'Y-8 guard: a series write-back after the zoom brought the light candles back over the dark rebuild — an option kept from before the theme switch').toEqual({gain: [], loss: []});
    });
});

// =========================================================================
// Y-25 — what is left of the arrows' cost: a chart without arrows, and a resize
// =========================================================================

/** TREND without its arrows (`markerStart`/`markerEnd: null`): an overlay like most, with no marker to aim. */
const FLAT: RenderedSignal = {...TREND, id: 'flat', label: 'Flat', markerStart: null, markerEnd: null};

/**
 * The last chart, once drawn daily over CALENDAR_DAYS with FLAT, past its stability pass. Checks what the Y-25 (d) cases
 * stand on: the draw carries the overlay, and no arrow; the chart listens to `dataZoom`.
 */
async function quiet(): Promise<FakeChart> {
    await drawnOver(
        CALENDAR_DAYS.map((point) => point.date),
        'daily',
    );
    const chart = chartInstances.at(-1);
    if (!chart) throw new Error('the chart was never created');
    expect({overlay: seriesIn(lastDraw()).some((series) => series.name === FLAT.label), arrows: arrowsIn(lastDraw())}, 'precondition: the draw carries the overlay, and no arrow').toEqual({overlay: true, arrows: []});
    expect(chart.handlerCount('dataZoom'), 'precondition: the chart registered a dataZoom handler').toBeGreaterThan(0);
    await stabilityPassOver(chart);
    return chart;
}

/**
 * Y-25 (d) — a chart without arrow markers reads nothing for them when a zoom settles: PriceChartFull, and its candles.
 *
 * What it protects: what LineChart.test.ts' Y-25 (d) protects. Every re-aim reads `getOption()`, a deep copy of the whole
 * option, before it finds out there is no arrow to aim — at every zoom's settle among others. The contract, after the
 * cure: each chart notes, right after its full render, that its option has no arrow (`noteArrowMarkers(chartInstance,
 * option)`), and `updateArrowRotations` skips it before `getOption()`. A zoom gesture and its settle then read nothing
 * on the candles, and once on PriceChartFull: its debounce reads the settled range, by design (Y-8).
 *
 * Red today: the settle's re-aim adds one read, for nothing — 2 on PriceChartFull, 1 on the candles.
 *
 * How it is tested: as Y-8's gesture above — five real zooms back to back (`userZoom`), then fake timers past the
 * settle — on charts drawn daily whose overlay has no marker; PriceChartFull's case proves the gesture settled at the
 * resolution it began at (the kept-resolution branch, where the arrows are re-aimed). Only the gesture is counted: the
 * first draw's reads come before it, out of the count by construction (`getOptionCount` is reset after them).
 */
describe('PriceChartFull and its candles — a chart without arrow markers reads no getOption() for them when a zoom settles (Y-25)', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('PriceChartFull: one zoom gesture and its settle at the daily resolution read getOption() once — the settled range — on a chart without arrows', async () => {
        panel800();
        mountPriceChart({data: CALENDAR_DAYS, overlaySignals: [FLAT]}, DAILY_PLOT_WIDTH);
        const chart = await quiet();

        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        for (const window of GESTURE) chart.userZoom(window);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(
            {redrawn: lastDrawIndex(chart) >= since, labelsRespaced: labelPatchesSince(chart, since).length > 0, axis: axisDays()},
            'barrier: the gesture settled at the resolution it began at — no redraw, the x labels re-spaced on the window (the debounce’s kept-resolution branch), the axis still daily',
        ).toEqual({redrawn: false, labelsRespaced: true, axis: CALENDAR_DAYS.map((point) => point.date)});

        expect(chart.getOptionCount, 'Y-25: a chart without arrow markers read getOption() — a deep copy of the whole option — once more than the settled range, to re-aim arrows it does not have').toBeLessThanOrEqual(1);
    });

    it('CandlestickChart: one zoom gesture and its settle read no getOption() on a chart without arrows', async () => {
        panel800();
        render(CandlestickChart, {props: {data: synthesizeDailyOHLC(CALENDAR_DAYS), resolution: 'daily', currency: 'EUR', overlaySignals: [FLAT]}});
        const chart = await quiet();

        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        for (const window of GESTURE) chart.userZoom(window);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(labelPatchesSince(chart, since).length, 'barrier: the gesture settled — the 47-1 timer re-spaced the x labels on its window').toBeGreaterThan(0);

        expect(chart.getOptionCount, 'Y-25: a chart without arrow markers read getOption() — a deep copy of the whole option — to re-aim arrows it does not have, once its zoom settled').toBe(0);
    });
});

/** The ResizeObservers created while `captureResizeObservers()` is in force: the element each observes, and how to fire its callback. */
const observers: Array<{target: Element; fire: () => void}> = [];

/** A ResizeObserver that keeps its callback, so a case can fire it as a browser does after a resize. */
class CapturingResizeObserver {
    readonly #callback: ResizeObserverCallback;

    constructor(callback: ResizeObserverCallback) {
        this.#callback = callback;
    }

    observe(target: Element): void {
        observers.push({target, fire: () => this.#callback([], this as unknown as ResizeObserver)});
    }

    unobserve(): void {}

    disconnect(): void {}
}

/**
 * Puts `CapturingResizeObserver` in place of the harness's ResizeObserver, inert on purpose (`src/__tests__/component.ts`:
 * jsdom has no layout, and a stub must never invent a size). Before the chart mounts; `vi.unstubAllGlobals()` undoes it.
 */
function captureResizeObservers(): void {
    vi.stubGlobal('ResizeObserver', CapturingResizeObserver);
}

/** Fires the ResizeObserver callbacks watching `chart`'s element, as a browser does once the box has changed. */
function resized(chart: FakeChart): void {
    const watching = observers.filter(({target}) => target === chart.getDom());
    expect(watching.length, 'barrier: the chart watches its element with a ResizeObserver').toBeGreaterThan(0);
    for (const {fire} of watching) fire();
}

/**
 * Y-25 (b) — a resize re-aims the arrows once it settles, not on each callback: PriceChartFull, and its candles.
 *
 * What it protects: what LineChart.test.ts' Y-25 (b) protects. A resize changes the plot's aspect, so the arrows are
 * re-aimed; both charts' ResizeObserver callbacks re-aim them at once, on every callback — a `getOption()` deep copy and
 * every series written back, as often as the browser reports the box changing. The contract, after the cure: a callback
 * reads no `getOption()` and writes no series. The candles re-arm their settle (`scheduleZoomedAxisLabels(lastZoomEvent)`),
 * whose timer re-aims the arrows once the resize pauses — one read; PriceChartFull already arms its resolution debounce
 * on a resize, which re-aims them in its kept-resolution branch — two reads with the settled range it reads by design.
 *
 * Red today: each of the five callbacks reads `getOption()` and writes the series back — and, on the candles, nothing
 * re-aims once the resize settles.
 *
 * How it is tested: as in LineChart.test.ts — a ResizeObserver that keeps its callback (`captureResizeObservers`), the
 * chart's fired as a browser would (`resized`), the plot narrowed first (`plot.width`, 1200 → 900 px: still daily) so
 * the arrows' angles really change and their re-aim shows as a write-back. Five callbacks back to back, counted, then
 * fake timers past any debounce, counted again; PriceChartFull's case proves the resize settled at the resolution it
 * began at. Fake timers go in after the first draw and its stability pass. The counts of the burst and of the settle
 * are soft: one red run reports all three.
 */
describe('PriceChartFull and its candles — a resize re-aims the arrows once it settles, not on each callback (Y-25)', () => {
    /** The plot after the resize: narrower, and still wide enough for CALENDAR_DAYS to stay daily. */
    const NARROWER_PLOT_WIDTH = 900;

    beforeEach(() => {
        captureResizeObservers();
    });

    afterEach(() => {
        vi.useRealTimers();
        // Global state the cases of the file share: the ResizeObserver, and the observers this one kept.
        vi.unstubAllGlobals();
        observers.length = 0;
    });

    /** Five resize callbacks back to back on the narrowed plot, fake timers on; answers where the burst began and ended in the chart's calls. */
    function resizeBurst(chart: FakeChart): {since: number; afterBurst: number} {
        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        const resizesBefore = chart.resizeCount;
        plot.width = NARROWER_PLOT_WIDTH;
        for (let callback = 0; callback < 5; callback++) resized(chart);
        expect(chart.resizeCount - resizesBefore, 'barrier: each callback reached the chart — it resized it').toBe(5);
        expect
            .soft({getOptionReads: chart.getOptionCount, seriesWriteBacks: seriesPayloadsSince(chart, since).length}, 'Y-25: a resize callback re-aimed the arrows at once — getOption(), a deep copy of the whole option, and every series written back — on each callback of one resize')
            .toEqual({getOptionReads: 0, seriesWriteBacks: 0});
        return {since, afterBurst: chart.setOptionCalls.length};
    }

    it('PriceChartFull: five resize callbacks read no getOption() and write no series back; once the resize settles at the daily resolution it began at, the arrows are re-aimed once', async () => {
        const chart = await mountTrendPriceChart();

        const {since, afterBurst} = resizeBurst(chart);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(
            {redrawn: lastDrawIndex(chart) >= since, labelsRespaced: labelPatchesSince(chart, afterBurst).length > 0, axis: axisDays()},
            'barrier: the resize settled at the resolution it began at — no redraw, the x labels re-spaced (the debounce’s kept-resolution branch), the axis still daily',
        ).toEqual({redrawn: false, labelsRespaced: true, axis: CALENDAR_DAYS.map((point) => point.date)});

        expect.soft(aimOf(seriesPayloadsSince(chart, afterBurst)), 'Y-25: once the resize settled, the arrows were not re-aimed exactly once — one series write-back, carrying both arrows, aimed').toEqual([TREND_ENDS.map((day) => ({day, aimed: true}))]);
        expect(chart.getOptionCount, 'Y-25: one resize — its five callbacks and its settle — read getOption() more than twice: the settled range, read once by design, and the arrows, once it settles').toBeLessThanOrEqual(2);
    });

    it('CandlestickChart: five resize callbacks read no getOption() and write no series back; once the resize settles, the arrows are re-aimed once', async () => {
        const chart = await mountTrendCandles();

        const {afterBurst} = resizeBurst(chart);
        await vi.advanceTimersByTimeAsync(1_000);

        expect.soft(aimOf(seriesPayloadsSince(chart, afterBurst)), 'Y-25: once the resize settled, the arrows were not re-aimed exactly once — one series write-back, carrying both arrows, aimed').toEqual([TREND_ENDS.map((day) => ({day, aimed: true}))]);
        expect(chart.getOptionCount, 'Y-25: one resize — its five callbacks and its settle — read getOption() more than once: the arrows need one read, once it settles').toBeLessThanOrEqual(1);
    });
});
