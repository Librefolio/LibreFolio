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
 * event names are compared in lower case, as ECharts registers them. No case emits but the 47-1 ones.
 */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    type Handler = (params?: unknown) => void;

    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
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
        dispatchAction: () => void;
        resize: () => void;
        containPixel: () => boolean;
        convertFromPixel: () => null;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let merged: Record<string, unknown> = {};
        let disposed = false;
        const handlers = new Map<string, Handler[]>();
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option) {
                chart.setOptionCalls.push({option});
                merged = {...merged, ...option};
            },
            getOption: () => merged,
            getWidth: () => 800,
            getHeight: () => 400,
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
            dispatchAction: () => {},
            resize: () => {},
            containPixel: () => false,
            convertFromPixel: () => null,
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

    return {chartInstances, echartsModule: {init: (dom: unknown) => createFakeChart(dom), graphic: {LinearGradient}}};
});

vi.mock('echarts', () => echartsModule);

import {get} from 'svelte/store';
import {waitLocale} from 'svelte-i18n';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import type {RenderedSignal} from '$lib/charts/signals';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
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
