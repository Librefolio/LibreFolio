// @vitest-environment jsdom
/**
 * PriceChartFull — the conversion lines of an event tooltip in the interface language (T-EN1).
 *
 * An event paid in another currency than the one the chart shows (a dividend in dollars on a chart in euros)
 * is converted, and its tooltip says so in two lines: the original amount with its currency, and the date of
 * the FX rate used — with how many days that rate lags the event when it does. Their words are English
 * written in the component (`orig. …`, `fx @ …`, `(3d back)`) whatever the interface language; the original
 * amount is already written in the interface locale (M-18), the lag is not.
 *
 * The contract. The original-amount line is `chart.tooltip.originalValue` around `formatFixed(value, 4)`,
 * followed by the unchanged currency badge; the FX line is `chart.tooltip.fxRateDate` around the rate's date
 * (the raw ISO date: dates are out of scope), then — only when the lag is positive — a space and
 * `chart.tooltip.fxDaysBack` around `formatFixed(days, 0)`.
 *
 * How it is tested: the real component, with ECharts replaced by a recorder (the `GrowthChart.test.ts`
 * pattern: jsdom has no canvas, and pixels are not the subject). The tooltip is the formatter of the scatter
 * series the component names `Events: <type>`, called with the very point that series holds for the event —
 * what ECharts hands it on a hover at the daily resolution — and its HTML is parsed inert in a `<template>`.
 * A line is what `<br>` separates, and the conversion lines are the event entry's last two: the fixture
 * events carry neither a note nor a comparison asset, which would follow them. Expected text is the
 * catalogue's own (`$_`) around figures Intl writes in the interface locale, never typed.
 *
 * Red today: in Italian and French the FX line reads `fx @ …` and `(3d back)`. The original-amount line reads
 * `orig. …` in all four catalogues, so no language can tell the catalogue from a literal there: a marker locale,
 * where each of the three keys reads as a marker of itself, is what proves the line comes from the catalogue.
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
 * area fill: kept as its arguments.
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
            // A week and a half of daily points over 1200 px keeps the chart at 'daily': one event, one point.
            getWidth: () => 1200,
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
import {addMessages, waitLocale} from 'svelte-i18n';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import type {LineDataPoint} from './LineChart.svelte';
import PriceChartFull, {type EventMarker} from './PriceChartFull.svelte';

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

/** The two conversion lines of `marker`'s tooltip, as the catalogue and Intl write them in `locale`. */
function conversionLines(marker: EventMarker, locale: string): string[] {
    const original = `${catalogue('chart.tooltip.originalValue', {value: fixed(marker.originalValue!, 4, locale)})} (${marker.originalCurrencyFlag} ${marker.originalCurrency})`;
    const rateDate = catalogue('chart.tooltip.fxRateDate', {date: marker.fxRateDate!});
    const lag = marker.fxDaysBack! > 0 ? ` ${catalogue('chart.tooltip.fxDaysBack', {days: fixed(marker.fxDaysBack!, 0, locale)})}` : '';
    return [original, `${rateDate}${lag}`];
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
    expect([backfilled[0], sameDay[0]], 'barrier: each tooltip is the daily one of its event, headed by its date').toEqual([BACKFILLED.date, SAME_DAY.date]);
    return {backfilled, sameDay};
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
    await setupI18n('en');
});

describe('PriceChartFull — a converted event’s tooltip in the interface language (T-EN1)', () => {
    it.each(LANGUAGES)('%s interface: the original amount and the FX rate’s date are worded by the catalogue — with the lag only when there is one — the figures in the interface notation', async (lang) => {
        const locale = await speak(lang);
        expect(locale, `control: a ${lang} interface on jsdom’s en-US browser writes bare ${lang}`).toBe(lang);
        expect(fixed(BACKFILLED.originalValue!, 4, locale), 'premise: the original amount is written another way than in English').not.toBe(fixed(BACKFILLED.originalValue!, 4, 'en-US'));
        mountChart();

        const {backfilled, sameDay} = await bothTooltips();

        expect({backfilled: spelled(backfilled.slice(-2)), sameDay: spelled(sameDay.slice(-2))}, `the conversion lines are not in the ${lang} interface's words: the component writes «orig.», «fx @» and «d back» in English`).toEqual({
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

        expect({backfilled: backfilled.slice(-2), sameDay: sameDay.slice(-2)}, 'a conversion line is not read from its key: the component still writes it').toEqual({
            backfilled: conversionLines(BACKFILLED, locale),
            sameDay: conversionLines(SAME_DAY, locale),
        });
    });

    it('English interface: the conversion lines read exactly as they do today — the English catalogue around figures in the interface notation (guard)', async () => {
        const locale = await speak('en');
        expect(locale, 'control: an English interface on jsdom’s en-US browser writes en-US').toBe('en-US');
        mountChart();

        const {backfilled, sameDay} = await bothTooltips();

        expect({backfilled: backfilled.slice(-2), sameDay: sameDay.slice(-2)}, 'the English conversion lines moved').toEqual({
            backfilled: conversionLines(BACKFILLED, locale),
            sameDay: conversionLines(SAME_DAY, locale),
        });
    });
});
