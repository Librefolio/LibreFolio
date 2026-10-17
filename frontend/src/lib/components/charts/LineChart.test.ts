// @vitest-environment jsdom
/**
 * LineChart — the days its tooltip writes, in the house notation of the interface locale (T-ISO, M-18).
 *
 * LineChart is the line chart of the compact price chart (`PriceChartCompact`), of the chart settings' preview
 * and of the risk charts (`UnderwaterChart`, `L4Simulation`, the legacy risk panel). Its axis tooltip is headed by
 * the point's category and, on an overlay whose point stands for another day's observation, says which with
 * `chart.tooltip.valueAt`. Both days are written as ISO today (`2024-03-04`), whatever the interface language.
 *
 * The contract, after the cure: a category that is a calendar day (`YYYY-MM-DD`) heads the tooltip in the house
 * notation of a tooltip day — the lot charts' `formatAxisDate(uiLocale(), day, true)`: Intl's numeric year, short
 * month and numeric day (`4 mar 2024`, `4 mars 2024`, `Mar 4, 2024`) — and so does the representative day inside
 * `chart.tooltip.valueAt`. A category that is not a calendar day stays exactly as it came: a count, a year, a
 * label. `new Date()` reads `1` as 1 January 2001 and `2025` as 1 January 2025, so a cure that formats whatever
 * `Date` can parse would turn such categories into days; the guard says it must not.
 *
 * How it is tested: the real component, with ECharts replaced by a recorder (the `PriceChartFull.test.ts`
 * pattern: jsdom has no canvas, and pixels are not the subject). The tooltip is the formatter the component handed
 * ECharts, called with the items ECharts hands it when the pointer is on a category; its HTML is parsed inert in a
 * `<template>`, and a line is what `<br>` separates. Expected days come from Intl (`houseDay`), words from the
 * catalogue (`$_`); nothing is typed.
 *
 * Red today: in Italian and French the header and the representative day are ISO. Green today, and after: the
 * categories that are not days.
 *
 * C-97c-3 (the describe after T-ISO's): a price in the tooltip keeps its significant digits, while the y-axis labels
 * stay compact. Its docblock says how.
 *
 * Also stubbed: layout — jsdom measures every box as 0×0 and the chart draws only into a non-empty one, so
 * `getBoundingClientRect` reports a panel-sized box.
 *
 * Registered in `front_component_unit` (`scripts/test_runner/_frontend_utility.py`, action `component-unit`), next
 * to `PriceChartFull.test.ts`.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in — a recorder, not a renderer — answering every call the chart and its helpers make on an
 * instance, and keeping every `setOption` payload. `graphic.LinearGradient` is the main series' fill: kept as its
 * arguments. `on` keeps the handlers it is given and `emit` calls them, as ECharts does when the user acts (47-1);
 * event names are compared in lower case, as ECharts registers them. No case emits but the 47-1 and Y-8 ones.
 *
 * The option it holds, it holds as ECharts does (Y-8): a `setOption` merges into it — an object key by key, anything
 * else, an array included, replaced; a component (`series`, `xAxis`, `dataZoom`…) by its index — unless `notMerge`
 * replaces it whole; `getOption()` answers a deep copy, every component a list, and counts its calls
 * (`getOptionCount`): ECharts deep-clones the whole option on each. A zoom moves the window as ECharts' dataZoom model
 * does — the held `dataZoom[0]`'s `start` and `end`, never a `startValue`/`endValue` beside them — then emits
 * `dataZoom` at once: the chart's own zoom (`dispatchAction({type: 'dataZoom', start, end})`, its event the payload
 * itself under the event's lower-case name, as ECharts emits a non-batch action) or the user's (`userZoom`, its event
 * in 47-1's batch shape). `dispatchAction` records every action (`dispatchedActions`), with how many `setOption` calls
 * came before it. `convertToPixel` maps a `[category, value]` point through the window on screen (`gridPixel`): the
 * categories of the first x-axis that the held `dataZoom[0]` leaves visible — all of them without a window — spread
 * over the plot's width (`plot.width`, 800 px unless a case resizes it; `getWidth()` reports it), and y 400 − value; so
 * an arrow marker's rotation depends on the window and on the plot's width, and is computed and written back as on a
 * screen. `resize` counts its calls (`resizeCount`): the first-render stability pass resizes.
 */
const {chartInstances, echartsModule, gridPixel, plot} = vi.hoisted(() => {
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
        /** Calls every handler registered for `event` with `params` (47-1). */
        emit: (event: string, params?: unknown) => void;
        /** How many handlers are registered for `event`: the precondition that an emitted event reaches the chart (47-1). */
        handlerCount: (event: string) => number;
        /**
         * `dispatchAction(action)` or `dispatchAction(action, silent | {silent})`: recorded; a `dataZoom` with a numeric
         * `start` and `end` moves the held window and, unless silent, emits `dataZoom` with the payload at once (Y-8).
         */
        dispatchAction: (action: ChartOption, opt?: unknown) => void;
        /** Every action dispatched, in order, with how many `setOption` calls came before it (`atCall`) (Y-8). */
        dispatchedActions: Array<{action: ChartOption; atCall: number}>;
        /** A user's zoom to `window` (Y-8): the held window moves, then `dataZoom` is emitted in 47-1's batch shape. Not a dispatch of the chart's own. */
        userZoom: (window: {start: number; end: number}) => void;
        resize: () => void;
        containPixel: () => boolean;
        convertFromPixel: () => null;
        /** A `[category, value]` point in px, through the window on screen (`gridPixel` on the held first x-axis and `dataZoom[0]`) (Y-8). */
        convertToPixel: (finder: unknown, value: unknown) => number[] | null;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    /** ECharts' component types: `getOption()` answers each as a list, and a merge matches them by index. */
    const COMPONENTS = new Set(['grid', 'xAxis', 'yAxis', 'dataZoom', 'series', 'tooltip', 'legend', 'title', 'visualMap', 'toolbox', 'graphic', 'dataset', 'axisPointer', 'polar', 'radiusAxis', 'angleAxis', 'singleAxis', 'parallel', 'parallelAxis', 'geo', 'calendar', 'brush', 'timeline', 'aria']);
    /** The plot `convertToPixel` maps onto: its width, as `getWidth()` reports it — a case that resizes the chart sets it (Y-25), `beforeEach` puts it back to 800 — and its height (`getHeight()`), y growing downwards. */
    const plot = {width: 800};
    const PLOT_HEIGHT = 400;

    const isPlain = (value: unknown): value is ChartOption => value !== null && typeof value === 'object' && [Object.prototype, null].includes(Object.getPrototypeOf(value));

    /**
     * The categories a zoom window leaves on screen — the first, and how many — as the chart counts them
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
     * A `[category, value]` point in px on an x-axis of `categories` zoomed to `zoom` (Y-8): x spreads the visible
     * categories over the plot's width — a category's index in the window times the plot's width over their count — and
     * y is the plot's height minus the value. Null for a category not on the axis, or a value that is not a number.
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

    return {chartInstances, gridPixel, plot, echartsModule: {init: (dom: unknown) => createFakeChart(dom), graphic: {LinearGradient}}};
});

vi.mock('echarts', () => echartsModule);

import type {ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import type {RenderedSignal} from '$lib/charts/signals';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {formatAxisDate} from '$lib/utils/core/formatAxisDate';
import LineChart, {type LineDataPoint} from './LineChart.svelte';

type UiLanguage = 'en' | 'it' | 'fr';
const LANGUAGES = ['it', 'fr'] as const;

type Formatter = (params: unknown) => string;

/** A week and a half of prices, in euros. */
const DATA: LineDataPoint[] = ['2024-02-26', '2024-02-27', '2024-02-28', '2024-02-29', '2024-03-01', '2024-03-04', '2024-03-05', '2024-03-06'].map((date, index) => ({date, value: 100 + index}));

/** An overlay whose point of Monday 4 March stands for Friday's observation: its row says so with chart.tooltip.valueAt. */
const PEER: RenderedSignal = {
    id: 'peer',
    label: 'Peer',
    data: [{date: '2024-03-04', value: 50, representativeDate: '2024-03-01'}],
    color: '#ff7f0e',
    lineWidth: 1,
    lineType: 'solid',
    markerStart: null,
    markerEnd: null,
    yAxisIndex: 0,
    aggregationProfile: 'last_with_range',
};

/** Categories that are not calendar days: a count, a year, a label — the first two are days to a lax `new Date()`. */
const NOT_DAYS = ['1', '2025', 'Q1'];

/** The option of the last full draw: the last `setOption` that carries the axis tooltip. */
function lastDraw(): Record<string, unknown> {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const draw = [...calls].reverse().find((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function');
    return draw?.option ?? {};
}

/** The categories on the last draw's x-axis. */
function axisCategories(): string[] {
    const xAxis = lastDraw().xAxis;
    const axis = (Array.isArray(xAxis) ? xAxis[0] : xAxis) as {data?: string[]} | undefined;
    return axis?.data ?? [];
}

/** Waits for the last draw's x-axis to hold `categories`: the barrier that the chart drew the data a case reads. */
async function drawnOver(categories: string[]): Promise<void> {
    await waitFor(() => expect(axisCategories(), 'barrier: the chart drew one point per category').toEqual(categories), {timeout: 5_000});
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

/** The axis tooltip's lines with the pointer on `category` over `items`, from the formatter the chart handed ECharts. */
function axisTooltipAt(category: string, items: Array<{seriesName: string; value: number}>): string[] {
    const formatter = (lastDraw().tooltip as {formatter: Formatter}).formatter;
    return tooltipLines(formatter(items.map((item) => ({axisValue: category, seriesType: 'line', color: '#2563eb', ...item}))));
}

/** What a line says in its last brackets — `(…)` closing it — or undefined when it closes on none. */
function lastBrackets(line: string | undefined): string | undefined {
    return /\(([^()]*)\)$/.exec(line ?? '')?.[1];
}

/** A catalogue message with its values, as the interface language words it. */
function catalogue(key: string, values: Record<string, string>): string {
    return get(_)(key, {values});
}

/** The calendar day `iso` in the house notation of a tooltip day, as Intl writes it in `locale`: numeric year, short month, numeric day. */
function houseDay(iso: string, locale: string): string {
    const [year, month, day] = iso.split('-').map(Number);
    return new Intl.DateTimeFormat(locale, {year: 'numeric', month: 'short', day: 'numeric'}).format(new Date(year, month - 1, day));
}

/** Switch the interface language in place, as the language selector does; answer the locale it now writes figures in. */
async function speak(lang: UiLanguage): Promise<string> {
    currentLanguage.set(lang);
    await waitLocale(lang);
    return uiLocale();
}

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    chartInstances.length = 0;
    plot.width = 800;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 400, width: 800, height: 400, toJSON: () => ({})} as DOMRect);
});

afterEach(async () => {
    cleanup();
    vi.restoreAllMocks();
    // The language is module-level state shared by every case of the file.
    await speak('en');
});

describe('LineChart — the days its tooltip writes, in the house notation of the interface locale (T-ISO)', () => {
    it.each(LANGUAGES)('%s interface: the tooltip is headed by its day, and an overlay’s representative day reads inside chart.tooltip.valueAt — both in the house notation', async (lang) => {
        const locale = await speak(lang);
        expect(houseDay('2024-03-04', locale), 'control: the oracle is the lot charts’ tooltip day').toBe(formatAxisDate(locale, '2024-03-04', true));
        render(LineChart, {props: {data: DATA, currency: 'EUR', overlaySignals: [PEER]}});
        await drawnOver(DATA.map((point) => point.date));

        const lines = axisTooltipAt('2024-03-04', [
            {seriesName: 'EUR', value: 105},
            {seriesName: PEER.label, value: 50},
        ]);

        expect({header: lines[0], representative: lastBrackets(lines.find((line) => line.startsWith(`${PEER.label}:`)))}, `the tooltip’s days are not in the ${lang} interface’s notation: the header and valueAt write ISO days`).toEqual({
            header: houseDay('2024-03-04', locale),
            representative: catalogue('chart.tooltip.valueAt', {date: houseDay('2024-03-01', locale)}),
        });
    });

    it('a category that is not a calendar day heads the tooltip exactly as it came — a count, a year, a label — in an Italian interface too (guard)', async () => {
        const locale = await speak('it');
        expect(
            NOT_DAYS.filter((category) => formatAxisDate(locale, category, true) !== category),
            'premise: a formatter that reads whatever new Date() parses would turn the count and the year into days',
        ).toEqual(['1', '2025']);
        render(LineChart, {props: {data: NOT_DAYS.map((category, index) => ({date: category, value: 10 + index})), currency: 'EUR'}});
        await drawnOver(NOT_DAYS);

        const headers = NOT_DAYS.map((category) => axisTooltipAt(category, [{seriesName: 'EUR', value: 10}])[0]);

        expect(headers, 'a category that is not a day was rewritten as a day').toEqual(NOT_DAYS);
    });
});

// =========================================================================
// C-97c-3 — a price in the tooltip keeps its significant digits; the y-axis labels stay compact
// =========================================================================

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10): a price on screen keeps its significant digits. The axis
 * tooltip writes each row's value with four fixed decimals, `formatFixed(Number(value), 4)`, and so does the line under
 * a band signal's row — `chart.tooltip.upper` and `chart.tooltip.lower` around the band's two bounds: on a price in
 * millionths every one of them reads `0.0000`. The contract: `formatPrice(…, {minDecimals: 4})` — four decimals at least,
 * as many as the first four significant digits need (`priceFractionDigits`, formatFixed.ts). The y-axis labels are a
 * scale, not a price on show: they stay compact — `k` from 1,000, two decimals from 1, at most four (trimmed) below — and
 * do not move.
 *
 * Reds: the rows of a price and of a band's middle in millionths, and the band's two bounds (today `0.0000` each).
 * Guards, green today and after: the same lines at 65000.1234 and around 1.08, and the y-axis labels of 1234.5, 1.234,
 * 0.1234 and 0.0000034573 (`1.2k`, `1.23`, `0.1234`, `0`) — the second and the last would move if the axis took
 * `formatPrice`.
 *
 * Reading, as the T-ISO cases read: the tooltip from the formatter the chart handed ECharts, called with the series under
 * the pointer; the y-axis label from the formatter of the last draw's first y-axis. A row is told apart by the series
 * name it opens with, the bounds' line by the catalogue's `chart.tooltip.upper`; a row's figure is matched as a whole
 * number token, the bounds' line compared whole, its words from the catalogue. English UI on jsdom's en-US browser,
 * checked before each case: the digits are typed.
 */
describe('LineChart — a price in its tooltip keeps its significant digits, its y-axis labels stay compact (C-97c-3, D-C97c-1)', () => {
    /** The day under the pointer: DATA's Monday 4 March. */
    const DAY = '2024-03-04';

    interface Figures {
        /** The main series' value under the pointer. */
        price: number;
        /** The band's middle, its row's value, and its two bounds. */
        middle: number;
        upper: number;
        lower: number;
    }

    /** A price and a band in millionths. */
    const TINY: Figures = {price: 0.0000034573, middle: 0.0000034573, upper: 0.0000037512, lower: 0.0000031634};
    /** A price with a thousands separator, and a band around 1.08. */
    const PLAIN: Figures = {price: 65000.1234, middle: 1.0834, upper: 1.0912, lower: 1.0756};

    /** A band signal — a Bollinger-like confidence band — with one point, on DAY. */
    function bandOf({middle, upper, lower}: Figures): RenderedSignal {
        return {
            id: 'band',
            label: 'Band',
            data: [{date: DAY, value: middle}],
            seriesType: 'band',
            bandData: {upper: [upper], middle: [middle], lower: [lower]},
            color: '#9467bd',
            lineWidth: 1,
            lineType: 'solid',
            markerStart: null,
            markerEnd: null,
            yAxisIndex: 0,
            aggregationProfile: 'last_with_range',
        };
    }

    /** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** The one line of `lines` that opens with `prefix`. */
    function lineOpening(lines: string[], prefix: string): string {
        const found = lines.filter((line) => line.startsWith(prefix));
        expect(found, `barrier: one line opens with ${prefix}`).toHaveLength(1);
        return found[0];
    }

    /** The chart over DATA with the band of `figures`; its tooltip on DAY, the main series (EUR) at `figures.price` and the band at its middle: the main row, the band's row and the bounds' line. */
    async function tooltipOf(figures: Figures): Promise<{main: string; band: string; bounds: string}> {
        const band = bandOf(figures);
        render(LineChart, {props: {data: DATA, currency: 'EUR', overlaySignals: [band]}});
        await drawnOver(DATA.map((point) => point.date));

        const lines = axisTooltipAt(DAY, [
            {seriesName: 'EUR', value: figures.price},
            {seriesName: band.label, value: figures.middle},
        ]);
        return {main: lineOpening(lines, 'EUR:'), band: lineOpening(lines, `${band.label}:`), bounds: lineOpening(lines, `${catalogue('chart.tooltip.upper', {})}:`)};
    }

    /** The bounds' line as the catalogue words it, around `upper` and `lower` as written. */
    function boundsLine(upper: string, lower: string): string {
        return `${catalogue('chart.tooltip.upper', {})}: ${upper} · ${catalogue('chart.tooltip.lower', {})}: ${lower}`;
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the tooltip is written en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('a price in millionths: the main row and the band’s row read 0.000003457, and the band’s bounds 0.000003751 and 0.000003163, not 0.0000', async () => {
        const {main, band, bounds} = await tooltipOf(TINY);

        expect.soft(main, 'the main series’ row (today EUR: 0.0000)').toMatch(numberToken('0.000003457'));
        expect.soft(band, 'the band’s row (today Band: 0.0000)').toMatch(numberToken('0.000003457'));
        expect.soft(bounds, 'the band’s bounds (today 0.0000 both)').toBe(boundsLine('0.000003751', '0.000003163'));
    });

    it('guard: 65000.1234 and a band around 1.08 keep their four decimals', async () => {
        const {main, band, bounds} = await tooltipOf(PLAIN);

        expect.soft(main, 'the main series’ row').toMatch(numberToken('65,000.1234'));
        expect.soft(band, 'the band’s row').toMatch(numberToken('1.0834'));
        expect.soft(bounds, 'the band’s bounds').toBe(boundsLine('1.0912', '1.0756'));
    });

    it('guard: the y-axis labels stay compact — 1.2k, 1.23, 0.1234, and 0 for a tick in millionths', async () => {
        render(LineChart, {props: {data: DATA, currency: 'EUR'}});
        await drawnOver(DATA.map((point) => point.date));
        const yAxis = lastDraw().yAxis as Array<{axisLabel?: {formatter?: (value: number) => string}}>;
        const label = yAxis[0]?.axisLabel?.formatter;
        expect(typeof label, 'barrier: the first y-axis has a label formatter').toBe('function');

        expect(Object.fromEntries([1234.5, 1.234, 0.1234, 0.0000034573].map((value) => [String(value), label!(value)]))).toEqual({'1234.5': '1.2k', '1.234': '1.23', '0.1234': '0.1234', '0.0000034573': '0'});
    });
});

/**
 * 47-1 — the category labels follow the zoomed window.
 *
 * A full-size LineChart sizes its compact x labels on every point: on an 800 px panel a year of daily prices is labelled
 * one point in 34 (`interval` 33). Zoomed to about a month, the same interval leaves the window with its two forced edge
 * labels and nothing between, because the chart's `dataZoom` handler only re-aims its arrows. After the fix, once a zoom
 * settles (debounced), the chart reads the window off the event's own params and sets the window's labels:
 * `setOption({xAxis: {axisLabel: policy.axisLabel}})` with the window's compact policy, or
 * `{xAxis: {axisLabel: {interval: 'auto', formatter}}}` when the window is not compact.
 *
 * Driven through the recorder: the case emits the event ECharts emits for a user's zoom, then advances fake timers past
 * any debounce. Fake timers are installed only after the first draw, which the barrier awaits on real ones.
 */
describe('LineChart — the category labels follow the zoomed window (47-1)', () => {
    /** The 365 days of 2025, one price a day. */
    const YEAR: LineDataPoint[] = Array.from({length: 365}, (_day, index) => ({date: new Date(Date.UTC(2025, 0, 1 + index)).toISOString().slice(0, 10), value: 100 + (index % 17)}));

    afterEach(() => {
        vi.useRealTimers();
    });

    /** The `xAxis.axisLabel` a `setOption` payload carries, the axis given as an object or as the first of an array. */
    function xAxisLabelOf(option: Record<string, unknown>): Record<string, unknown> | undefined {
        const xAxis = option.xAxis;
        const axis = (Array.isArray(xAxis) ? xAxis[0] : xAxis) as {axisLabel?: Record<string, unknown>} | undefined;
        return axis?.axisLabel;
    }

    /** Mounts a full-size LineChart over YEAR on an 800 px panel, and waits for its first draw. */
    async function mountYear() {
        // The panel is 800 px wide however the chart measures it: its box (file-level beforeEach), its client and offset
        // widths here, the instance's `getWidth()` in the recorder.
        vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(800);
        vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(800);
        render(LineChart, {props: {data: YEAR, currency: 'EUR'}});
        await drawnOver(YEAR.map((point) => point.date));
        const chart = chartInstances.at(-1);
        if (!chart) throw new Error('LineChart never created its chart');
        // Precondition: the first draw labels the whole year, compact, one point in 34 (ceil(364 / 11) − 1).
        expect(xAxisLabelOf(lastDraw())?.interval, 'precondition: 365 points on 800 px are labelled one every 34').toBe(33);
        // Precondition: the chart listens to dataZoom, so the event a case emits reaches it.
        expect(chart.handlerCount('dataZoom'), 'precondition: the chart registered a dataZoom handler').toBeGreaterThan(0);
        return chart;
    }

    /** Zooms as ECharts reports a user's zoom, then lets it settle: a second of fake time, well past any debounce. */
    async function zoomAndSettle(chart: (typeof chartInstances)[number], params: unknown): Promise<void> {
        vi.useFakeTimers();
        chart.emit('dataZoom', params);
        await vi.advanceTimersByTimeAsync(1_000);
    }

    /** The x-axis labels the chart set after call `since`: the last one is what the user reads. */
    const labelsSetSince = (chart: (typeof chartInstances)[number], since: number) =>
        chart.setOptionCalls
            .slice(since)
            .map(({option}) => xAxisLabelOf(option))
            .filter((label) => label !== undefined);

    it('relabels the axis at the window’s interval once a zoom to 34 of the 365 days settles: one label every 3 points (interval 2)', async () => {
        // Why: the reported defect. 0–9 % of 364 steps is indices 0..33, 34 points: 736 / 34 ≈ 21.6 px a point, still
        // compact, and the 12-label budget over 34 points gives ceil(33 / 11) − 1 = 2.
        const chart = await mountYear();
        const since = chart.setOptionCalls.length;

        await zoomAndSettle(chart, {batch: [{start: 0, end: 9}]});

        expect(labelsSetSince(chart, since).at(-1)?.interval, 'the x labels the chart set once the zoom settled').toBe(2);
    });

    it('hands the labels back to ECharts once a zoom to 20 of the 365 days settles: the window is not compact (interval auto, with a formatter)', async () => {
        // Why: the other branch. 0–5 % of 364 steps is indices 0..19, 20 points: 736 / 20 = 36.8 px a point, so ECharts may
        // place the labels itself, named by the policy's formatter.
        const chart = await mountYear();
        const since = chart.setOptionCalls.length;

        await zoomAndSettle(chart, {batch: [{start: 0, end: 5}]});

        const last = labelsSetSince(chart, since).at(-1);
        expect({interval: last?.interval, formatter: typeof last?.formatter}, 'the x labels the chart set once the zoom settled').toEqual({interval: 'auto', formatter: 'function'});
    });
});

// =========================================================================
// Y-8 — the arrows a zoom re-aims: once the gesture settles, not on every tick
// =========================================================================

type FakeChart = (typeof chartInstances)[number];
type ChartOption = Record<string, unknown>;

/** The 365 days of 2025, one price a day: 47-1's year, long enough to zoom into. */
const YEAR_2025: LineDataPoint[] = Array.from({length: 365}, (_day, index) => ({date: new Date(Date.UTC(2025, 0, 1 + index)).toISOString().slice(0, 10), value: 100 + (index % 17)}));

/**
 * A trend over the year's last 60 days with an arrow at each end (`markerStart`/`markerEnd: 'arrow'`): the markers a
 * zoom re-aims. It rises half a unit a day, so each arrow has a slope to follow.
 */
const TREND: RenderedSignal = {
    id: 'trend',
    label: 'Trend',
    data: YEAR_2025.slice(-60).map((point, index) => ({date: point.date, value: 90 + index / 2})),
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

/** The window of a chart nobody zoomed: the whole x-axis. */
const WHOLE_AXIS: ZoomWindow = {start: 0, end: 100};

/**
 * One zoom gesture: the five windows its ticks close in on, around the year's middle. Each is played as a user's zoom
 * (`userZoom`): the held window moves, then `dataZoom` is emitted in 47-1's shape — so the window the gesture settles
 * on is the one the chart reads, and the arrows' angles change with it (Y-25).
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

/**
 * A full-size LineChart over YEAR_2025 with TREND's arrows on an 800 px panel — `props` on top — once its first draw and
 * the stability pass after it are in. Checks what the Y-8 cases stand on: the draw carries both arrows, unrotated as
 * built; the chart listens to `dataZoom`; and the harness really aims them — after the draw, a series write-back whose
 * arrows the recorder's pixel grid turned — or every count after it would be vacuous. Answers the chart's recorder, and
 * the render's `rerender` for a case that redraws on a prop change.
 */
async function mountTrend(props: Partial<ComponentProps<typeof LineChart>> = {}) {
    // 800 px however the chart measures it, as in 47-1: its box (file-level beforeEach), its client and offset widths.
    vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(800);
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(800);
    const {rerender} = render(LineChart, {props: {data: YEAR_2025, currency: 'EUR', overlaySignals: [TREND], ...props}});
    await drawnOver(YEAR_2025.map((point) => point.date));
    const chart = chartInstances.at(-1);
    if (!chart) throw new Error('LineChart never created its chart');
    expect(arrowsIn(lastDraw()), 'precondition: the draw carries TREND’s two arrows, on its first and last day, unrotated as built').toEqual(TREND_ENDS.map((day) => ({series: TREND.label, day, rotate: 0})));
    expect(chart.handlerCount('dataZoom'), 'precondition: the chart registered a dataZoom handler').toBeGreaterThan(0);
    await stabilityPassOver(chart);
    expect(aimOf(seriesPayloadsSince(chart, lastDrawIndex(chart) + 1)), 'precondition: the harness aims the arrows — after the draw, a series write-back carrying both, turned by the recorder’s pixel grid').toContainEqual(TREND_ENDS.map((day) => ({day, aimed: true})));
    return {chart, rerender};
}

/**
 * Y-8 — a zoom gesture re-aims the arrows once it settles, not on every tick.
 *
 * What it protects: the cost of a zoom. An overlay signal may end in an arrow (`markerStart`/`markerEnd: 'arrow'`), a
 * `markPoint` whose rotation follows the line's slope on screen; a zoom changes the aspect, so the arrows are re-aimed
 * (`updateArrowRotations`). A re-aim reads `getOption()` — ECharts deep-clones the whole option, every series' data
 * included — and writes every series back (`setOption({series}, false)`). The chart's `dataZoom` handler runs one on
 * every tick, up to ~60 a second while a wheel or a pinch moves: over years of daily prices, the stutter PriceChartFull's
 * own note warns of. The contract, after the cure: a tick reads no `getOption()` and writes no series; once the gesture
 * pauses, the 47-1 settle timer (`ZOOM_LABEL_SETTLE_MS`) re-aims the arrows once — one `getOption()`, one series
 * write-back.
 *
 * Red today: each of the five ticks reads `getOption()` and writes the series back, and the settle re-aims nothing.
 *
 * How it is tested: through the recorder, which holds the option as ECharts does and maps a point to pixels (`gridPixel`),
 * so a re-aim is computed and written back as on a screen (`mountTrend` proves it). The case plays five ticks back to
 * back, as one gesture does, with no time between them, counts what they read and wrote, then advances fake timers past
 * any debounce and counts again. The ticks are real zooms (`userZoom`, Y-25): each moves the held window, so the window
 * the gesture settles on gives the arrows new angles — since Y-25 a re-aim that turns no arrow writes nothing back, and
 * a settle on a window that never moved would leave the «one write-back» below vacuous, or red for the wrong reason.
 * Green before Y-25's cure and after it. Fake timers go in after the first draw and its stability pass, which the
 * barriers await on real ones. The counts of the ticks and of the settle are soft: one red run reports all three.
 */
describe('LineChart — a zoom re-aims the arrows once the gesture settles, not on every tick (Y-8)', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('five zoom ticks read no getOption() and write no series back; once the gesture settles, the arrows are re-aimed once', async () => {
        const {chart} = await mountTrend();

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

/** TREND on YEAR_2025's axis, as the chart lines an overlay up: its value on each of its days, null on the others. */
const TREND_ON_AXIS: Array<number | null> = YEAR_2025.map((point) => TREND.data.find((trendPoint) => trendPoint.date === point.date)?.value ?? null);

/**
 * The rotation `updateArrowRotations` gives TREND's arrow on `day` with the x-axis zoomed to `zoom`, worked out here: on
 * the recorder's pixels (`gridPixel`), towards the neighbour it picks — the nearest point before the arrow within 20,
 * else after it — by its own formula, the arrow pointing away from that neighbour, 0° up and anti-clockwise.
 */
function rotationOf(day: string, zoom: ZoomWindow): number {
    const categories = YEAR_2025.map((point) => point.date);
    const at = categories.indexOf(day);
    const steps = Array.from({length: 20}, (_unused, index) => index + 1);
    const neighbour = [...steps.map((step) => at - step), ...steps.map((step) => at + step)].find((index) => index >= 0 && index < categories.length && TREND_ON_AXIS[index] !== null);
    const marker = gridPixel([day, TREND_ON_AXIS[at]], categories, zoom);
    const near = neighbour === undefined ? null : gridPixel([categories[neighbour], TREND_ON_AXIS[neighbour]], categories, zoom);
    if (!marker || !near) throw new Error(`the oracle cannot aim TREND’s arrow on ${day}: TREND has no point there, or none within 20 of it`);
    return (Math.atan2(-(near[1] - marker[1]), near[0] - marker[0]) * 180) / Math.PI + 90;
}

/** What each arrow of a payload is aimed on — `zoom`'s window or the whole axis, by `rotationOf` on each — or, on neither, its rotation as written. */
function aimedOn(option: ChartOption | undefined, zoom: ZoomWindow): Array<{day: unknown; aimedOn: unknown}> {
    return arrowsIn(option ?? {}).map(({day, rotate}) => {
        const on = (window: ZoomWindow) => typeof rotate === 'number' && Math.abs(rotate - rotationOf(String(day), window)) < 1e-9;
        return {day, aimedOn: on(zoom) ? 'the window' : on(WHOLE_AXIS) ? 'the whole axis' : rotate};
    });
}

/** The windows of the `dataZoom` actions the chart dispatched after call `since`: the zoom it restored. */
const restoresSince = (chart: FakeChart, since: number): Array<{start: unknown; end: unknown}> => chart.dispatchedActions.filter(({action, atCall}) => atCall > since && action.type === 'dataZoom').map(({action}) => ({start: action.start, end: action.end}));

/**
 * Y-8 — a full redraw of a zoomed chart aims its arrows on the window it restores.
 *
 * What it protects: the arrows of a zoomed chart across a full redraw — a theme switch, a prop change, new data. The
 * redraw's `setOption(option, true)` drops the zoom, and the chart puts the user's window back right after it with a
 * `dataZoom` action (the restore at the end of `renderChart()`). It re-aims the arrows once a draw
 * (`updateArrowRotations`): aimed before the restore, they are aimed on the whole axis. Until Y-8 the restore's own
 * `dataZoom` event re-aimed them at once, in the handler; since Y-8 the handler only schedules the settle
 * (`ZOOM_LABEL_SETTLE_MS`), so the arrows point wrong until it fires. The contract: a redraw restores the window first and
 * re-aims after — as `CandlestickChart` does — so its own write-back aims the arrows on the window.
 *
 * Red today: `renderChart()` re-aims the arrows, then restores the zoom.
 *
 * How it is tested: the recorder plays a zoom as ECharts does — the user's (`userZoom`) and the chart's restore
 * (`dispatchAction`) move the held window, then emit `dataZoom` at once — and maps a point through the window on screen
 * (`gridPixel`), so an arrow's rotation depends on the window. The oracle is that mapping under `updateArrowRotations`'
 * own formula (`rotationOf`), on the window and on the whole axis, which a precondition proves apart. The case zooms to
 * the year's last 30 % — both arrows inside — and lets it settle; then a prop change redraws the chart. Fake timers,
 * installed after the first draw, keep pending the settle the restore schedules; the barriers prove the redraw drew,
 * restored the window after its draw and re-aimed, and that the settle has not fired. Then the case reads the redraw's
 * own write-back — the first series write-back after its draw — before any timer fires.
 */
describe('LineChart — a full redraw of a zoomed chart aims its arrows on the window it restores (Y-8)', () => {
    /** The year's last 30 %, as a user zooms to it: TREND's two arrows inside. */
    const WINDOW: ZoomWindow = {start: 70, end: 100};

    afterEach(() => {
        vi.useRealTimers();
    });

    it('a prop change redraws a zoomed chart: its own write-back aims the arrows on the restored window, not on the whole axis, before the settle', async () => {
        expect(
            TREND_ENDS.map((day) => ({day, apart: Math.abs(rotationOf(day, WINDOW) - rotationOf(day, WHOLE_AXIS)) > 1})),
            'precondition: on the recorder’s pixels each arrow points another way on the window than on the whole axis — or the case could not tell them apart',
        ).toEqual(TREND_ENDS.map((day) => ({day, apart: true})));
        const {chart, rerender} = await mountTrend();

        vi.useFakeTimers();
        const zoomedAt = chart.setOptionCalls.length;
        chart.userZoom(WINDOW);
        await vi.advanceTimersByTimeAsync(1_000);
        expect(aimedOn(seriesPayloadsSince(chart, zoomedAt).at(-1), WINDOW), 'precondition: once the zoom settled, the arrows are aimed on its window').toEqual(TREND_ENDS.map((day) => ({day, aimedOn: 'the window'})));

        const drawnBefore = lastDrawIndex(chart);
        await rerender({showGridLines: false});
        // The redraw runs on Svelte's tick: a zero advance — one turn of the event loop, the fake clock moved by nothing —
        // lets it in, and cannot fire the settle the restore schedules, 120 ms away.
        await vi.advanceTimersByTimeAsync(0);
        const draw = lastDrawIndex(chart);
        expect(draw, 'barrier: the prop change redrew the chart — a new full draw').toBeGreaterThan(drawnBefore);
        expect(restoresSince(chart, draw), 'barrier: after its draw, the chart restored the zoom — a dataZoom dispatch with the saved window').toEqual([WINDOW]);
        expect(seriesPayloadsSince(chart, draw + 1).length, 'barrier: the redraw re-aimed its arrows — a series write-back after its draw').toBeGreaterThan(0);
        expect(vi.getTimerCount(), 'barrier: the settle the restore scheduled has not fired').toBeGreaterThan(0);

        expect(aimedOn(seriesPayloadsSince(chart, draw + 1)[0], WINDOW), 'Y-8: a full redraw of a zoomed chart aimed its arrows on the whole axis, before restoring the zoom — they point wrong until the settle').toEqual(TREND_ENDS.map((day) => ({day, aimedOn: 'the window'})));
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
 * Y-8, colour guard — after a rebuild, the arrows' write-back carries the rebuild's colours.
 *
 * What it protects: the cure of Y-8 moves the arrows' re-aim to the settle; a next saving would be to keep the option
 * between zoom steps rather than read `getOption()` afresh. Such a cache must not outlive a rebuild: the arrows'
 * write-back (`setOption({series}, false)`) carries every series, colours included, so an option kept from before a
 * theme switch (`onThemeClassChange`) or a Designer Lab colour edit (`onChartColorsChange`, contract C4) paints the old
 * colours back over the new ones at the next zoom. The contract: once the chart is rebuilt, every series write-back a
 * zoom brings carries the new colours, or none at all.
 *
 * Green today, and after the cure, by construction: `updateArrowRotations` reads `getOption()` afresh on each call. A
 * variant that keeps the first `getOption()` of a chart and never drops it on a rebuild turns both cases red.
 *
 * How it is tested: built, then rebuilt — in dark (the `dark` class on `<html>`, as the theme store writes it), or on
 * `notifyChartColorsChange()` with one role colour changed (`setRoleReader`: the dashed baseline's role) — then one zoom
 * step, its settle included (fake timers, after the barriers). The step is a real zoom (`zoomOneStep`): it moves the
 * window, so its settle turns the arrows and writes every series back, which a step that moved nothing would no longer
 * do once Y-25 writes back only a turned arrow. Green before Y-25's cure and after it. A colour is found in any notation
 * the chart writes it: the hex, or `toRgba`'s `rgba(r,g,b,a)` at any alpha, a gradient stop included. At least one
 * write-back must come, or the guard reads nothing. The `dark` class and the role reader are reset after each case.
 */
describe('LineChart — after a rebuild, the arrows’ write-back carries the rebuild’s colours (Y-8, colour guard)', () => {
    /** The price line, light and dark (`lineColor`, `darkLineColor`): colours the chart would never pick by itself. */
    const LINE: Repaint = {before: '#0b1d2f', after: '#d4c3b2'};
    /** The role of the dashed baseline (`chartNeutrals(…).price.baseline`), and its colour before and after the edit. */
    const BASELINE_ROLE = '--lf-border-input';
    const BASELINE: Repaint = {before: '#2f1d0b', after: '#b2c3d4'};
    /** The price line's series — one, with its baseline colouring off — and the baseline's. */
    const priceLine = (series: ChartOption) => series.name === 'EUR' && series.type === 'line';
    const baseline = (series: ChartOption) => series.name === '__baseline__';

    beforeEach(() => {
        document.documentElement.classList.remove('dark');
    });

    afterEach(() => {
        vi.useRealTimers();
        // Module-level state every case of the file shares: the theme of <html>, and how the roles are read.
        document.documentElement.classList.remove('dark');
        setRoleReader(null);
    });

    it('built in light, rebuilt in dark, one zoom step: every series write-back carries the dark price line, never the light one', async () => {
        const {chart} = await mountTrend({lineColor: LINE.before, darkLineColor: LINE.after, colorByBaseline: false});
        expect(paintOf(lastDraw(), priceLine, LINE), 'precondition: the price line is drawn in its light colour').toBe('before');

        document.documentElement.classList.add('dark');
        await waitFor(() => expect(paintOf(lastDraw(), priceLine, LINE), 'barrier: the theme switch rebuilt the chart, the price line in its dark colour').toBe('after'), {timeout: 5_000});

        const writeBacks = await zoomOneStep(chart);

        expect(writeBacks.length, 'the zoom step brought no series write-back: the guard has nothing to read').toBeGreaterThan(0);
        expect(stalePaints(writeBacks, priceLine, LINE), 'Y-8 guard: a series write-back after the zoom brought the light price line back over the dark rebuild — an option kept from before the theme switch').toEqual([]);
    });

    it('rebuilt on notifyChartColorsChange() with the baseline’s role colour changed, one zoom step: every series write-back carries the new colour, never the old one', async () => {
        setRoleReader((role) => (role === BASELINE_ROLE ? BASELINE.before : ''));
        const {chart} = await mountTrend();
        expect(paintOf(lastDraw(), baseline, BASELINE), 'precondition: the baseline is drawn in its role’s colour').toBe('before');

        setRoleReader((role) => (role === BASELINE_ROLE ? BASELINE.after : ''));
        notifyChartColorsChange();
        await waitFor(() => expect(paintOf(lastDraw(), baseline, BASELINE), 'barrier: the colour change rebuilt the chart, the baseline in its role’s new colour').toBe('after'), {timeout: 5_000});

        const writeBacks = await zoomOneStep(chart);

        expect(writeBacks.length, 'the zoom step brought no series write-back: the guard has nothing to read').toBeGreaterThan(0);
        expect(stalePaints(writeBacks, baseline, BASELINE), 'Y-8 guard: a series write-back after the zoom brought the baseline’s old colour back over the rebuild — an option kept from before notifyChartColorsChange()').toEqual([]);
    });
});

// =========================================================================
// Y-25 — what is left of the arrows' cost: a chart without arrows, and a resize
// =========================================================================

/** TREND without its arrows (`markerStart`/`markerEnd: null`): an overlay like most, with no marker to aim. */
const FLAT: RenderedSignal = {...TREND, id: 'flat', label: 'Flat', markerStart: null, markerEnd: null};

/**
 * A full-size LineChart over YEAR_2025 with FLAT on an 800 px panel, once its first draw and the stability pass after it
 * are in. Checks what the case stands on: the draw carries the overlay, and no arrow; the chart listens to `dataZoom`.
 */
async function mountFlat(): Promise<FakeChart> {
    vi.spyOn(Element.prototype, 'clientWidth', 'get').mockReturnValue(800);
    vi.spyOn(HTMLElement.prototype, 'offsetWidth', 'get').mockReturnValue(800);
    render(LineChart, {props: {data: YEAR_2025, currency: 'EUR', overlaySignals: [FLAT]}});
    await drawnOver(YEAR_2025.map((point) => point.date));
    const chart = chartInstances.at(-1);
    if (!chart) throw new Error('LineChart never created its chart');
    expect({overlay: seriesIn(lastDraw()).some((series) => series.name === FLAT.label), arrows: arrowsIn(lastDraw())}, 'precondition: the draw carries the overlay, and no arrow').toEqual({overlay: true, arrows: []});
    expect(chart.handlerCount('dataZoom'), 'precondition: the chart registered a dataZoom handler').toBeGreaterThan(0);
    await stabilityPassOver(chart);
    return chart;
}

/**
 * Y-25 (d) — a chart without arrow markers reads nothing for them when a zoom settles.
 *
 * What it protects: the cost of the arrows on a chart that has none — most of them. Every re-aim reads `getOption()`, a
 * deep copy of the whole option, before it finds out there is nothing to aim: after each draw, twice in the stability
 * pass that follows the first, and at the settle of every zoom (Y-8). The contract, after the cure: the chart notes,
 * right after its full render, that its option has no arrow (`noteArrowMarkers(chartInstance, option)`), and
 * `updateArrowRotations` skips it before `getOption()` — so a zoom gesture and its settle read nothing.
 *
 * Red today: the settle's re-aim reads `getOption()` once, for nothing.
 *
 * How it is tested: as Y-8's gesture — five real zooms back to back (`userZoom`), then fake timers past the settle — on
 * a chart whose overlay has no marker. Only the gesture is counted: the first draw's three reads (the draw and the two
 * stability resizes) come before it, and are out of the count by construction (`getOptionCount` is reset after them).
 * Fake timers go in after the first draw and its stability pass, which the barriers await on real ones.
 */
describe('LineChart — a chart without arrow markers reads no getOption() for them when a zoom settles (Y-25)', () => {
    afterEach(() => {
        vi.useRealTimers();
    });

    it('one zoom gesture and its settle read no getOption() on a chart without arrows', async () => {
        const chart = await mountFlat();

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
 * Y-25 (b) — a resize re-aims the arrows once it settles, not on each callback.
 *
 * What it protects: the cost of a resize — Y-8's, on the other path that re-aims. A resize changes the plot's aspect, so
 * the arrows are re-aimed; `resizeChartOnly()`, the ResizeObserver's work on a full-size chart (and on a compact one that
 * keeps its resolution), re-aims them at once on every callback: a `getOption()` deep copy and every series written back,
 * as often as the browser reports the box changing while a window is dragged or a panel slides. The contract, after the
 * cure: a callback reads no `getOption()` and writes no series; it re-arms the settle
 * (`scheduleZoomedAxisLabels(lastZoomEvent)`), whose timer re-aims the arrows once the resize pauses — one read, one
 * write-back.
 *
 * Red today: each of the five callbacks reads `getOption()` and writes the series back, and nothing re-aims once the
 * resize settles.
 *
 * How it is tested: the harness's ResizeObserver is inert on purpose, so this case puts one in that keeps its callback
 * (`captureResizeObservers`) and fires the chart's as a browser would (`resized`). The plot narrows first (`plot.width`,
 * 800 → 600 px), so the arrows' angles really change and their re-aim shows as a write-back. Five callbacks back to back,
 * counted, then fake timers past any debounce, counted again. Fake timers go in after the first draw and its stability
 * pass. The counts of the burst and of the settle are soft: one red run reports all three.
 */
describe('LineChart — a resize re-aims the arrows once it settles, not on each callback (Y-25)', () => {
    beforeEach(() => {
        captureResizeObservers();
    });

    afterEach(() => {
        vi.useRealTimers();
        // Global state the cases of the file share: the ResizeObserver, and the observers this one kept.
        vi.unstubAllGlobals();
        observers.length = 0;
    });

    it('five resize callbacks read no getOption() and write no series back; once the resize settles, the arrows are re-aimed once', async () => {
        const {chart} = await mountTrend();

        vi.useFakeTimers();
        chart.getOptionCount = 0;
        const since = chart.setOptionCalls.length;
        const resizesBefore = chart.resizeCount;
        plot.width = 600;
        for (let callback = 0; callback < 5; callback++) resized(chart);
        expect(chart.resizeCount - resizesBefore, 'barrier: each callback reached the chart — it resized it').toBe(5);

        expect
            .soft({getOptionReads: chart.getOptionCount, seriesWriteBacks: seriesPayloadsSince(chart, since).length}, 'Y-25: a resize callback re-aimed the arrows at once — getOption(), a deep copy of the whole option, and every series written back — on each callback of one resize')
            .toEqual({getOptionReads: 0, seriesWriteBacks: 0});

        const afterBurst = chart.setOptionCalls.length;
        await vi.advanceTimersByTimeAsync(1_000);

        expect.soft(aimOf(seriesPayloadsSince(chart, afterBurst)), 'Y-25: once the resize settled, the arrows were not re-aimed exactly once — one series write-back, carrying both arrows, aimed').toEqual([TREND_ENDS.map((day) => ({day, aimed: true}))]);
        expect(chart.getOptionCount, 'Y-25: one resize — its five callbacks and its settle — read getOption() more than once: the arrows need one read, once it settles').toBeLessThanOrEqual(1);
    });
});
