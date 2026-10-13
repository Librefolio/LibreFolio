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
 * arguments.
 */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface FakeChart {
        setOptionCalls: Array<{option: Record<string, unknown>}>;
        setOption: (option: Record<string, unknown>) => void;
        getOption: () => Record<string, unknown>;
        getWidth: () => number;
        getHeight: () => number;
        getDom: () => unknown;
        getZr: () => {on: () => void; off: () => void};
        on: () => void;
        off: () => void;
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
            on: () => {},
            off: () => {},
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
