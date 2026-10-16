// @vitest-environment jsdom
/**
 * PriceChartFull.tooltipEscape.test.ts — K-15: the price chart's axis tooltip escapes the currencies its rows name.
 *
 * ## What it protects (K-15)
 *
 * The axis tooltip of `PriceChartFull` is HTML that ECharts sets as `innerHTML`. Each row names its series and, in
 * brackets, a currency with its flag. Every text interpolated there must be escaped, or a value that holds markup becomes
 * markup. The verdict, on a payload whose markup carries a marker (`PAYLOAD`): parsed into a detached element, the
 * tooltip holds no `[data-pwned]` element, and its text holds the payload verbatim — escaped markup reads as text.
 *
 * ## Why it is red today
 *
 * `PriceChartFull.svelte`, the rows of the axis tooltip (:1003–:1037):
 * - an overlay signal's row: `sigInfo.currencyFlag` is interpolated raw, beside `sigInfo.currency`, which is escaped
 *   (:1013). `sigInfo` is the `overlaySignalInfoMap` prop (:138), which the asset and FX pages build with
 *   `buildOverlaySignalInfoMap(overlaySignals)` from signals that carry `currencyFlag` (`ChartSignal.ts:269`, filled by
 *   `AssetComparisonSignal.ts:83–98` from `getCurrencyInfo(code).flag_emoji`); this file builds it the same way;
 * - the main series with FX conversion active (`conversionActive`, :972 — original values in the data, a display
 *   currency and its flag): `displayCurrencyFlag` and `displayCurrencyProp` raw (:1022);
 * - the main series without conversion: `mainCurrencyFlagProp` and `mainCurrencyProp` raw (:1025).
 * The props are declared at :152–:158. The escaped neighbours are the green guards: the overlay's currency code (:1013)
 * and the main label, which goes through `signalLabelToHtml` (:1029).
 *
 * The codes are tested as well as the flags: in this component they reach only the tooltip strings (and the
 * pass-through to `CandlestickChart`), never an `Intl` call, so a markup code cannot crash the render.
 *
 * ## How
 *
 * The real component in jsdom, ECharts replaced by the recorder of `PriceChartFull.test.ts`. The tooltip is the formatter
 * the chart handed ECharts, called with the items under the pointer, as ECharts calls an axis tooltip. Layout is
 * stubbed: jsdom measures every box as 0×0 and the chart draws only into a non-empty one; the recorder reports a plot
 * 1200 px wide, so the week and a half of data stays daily. The chart imports `assetTypes.ts` (through
 * `signalLabel.ts`), which reads the generated client at module load, so the modules are imported after asserting the
 * generated file exists.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/** The ECharts stand-in of `PriceChartFull.test.ts`: it answers every call the chart and its helpers make, and keeps every `setOption` payload. */
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
            // A week and a half of daily points over 1200 px keeps the chart at the daily resolution.
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

import type {ComponentProps} from 'svelte';
import {cleanup, render, setupI18n, waitFor} from '$test/component';
import type {RenderedSignal} from '$lib/charts/signals';
import type {LineDataPoint} from './LineChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** Markup whose element carries a marker: present after parsing only if it was interpolated unescaped. */
const PAYLOAD = '<b data-pwned="1">X</b>';

/** A week and a half of daily prices, synthetic. */
const DAYS = ['2024-02-26', '2024-02-27', '2024-02-28', '2024-02-29', '2024-03-01', '2024-03-04', '2024-03-05', '2024-03-06'];
const DATA: LineDataPoint[] = DAYS.map((date, index) => ({date, value: 100 + index}));
/** The same prices, converted: each point keeps its value in its own currency, so the chart draws the ghost of the originals. */
const CONVERTED: LineDataPoint[] = DATA.map((point) => ({...point, originalValue: point.value * 1.1, originalCurrency: 'USD', originalCurrencyFlag: '🇺🇸'}));
const HOVERED_DAY = '2024-03-04';

/** The main series' label, given explicitly so that its row is found by name. */
const MAIN_LABEL = 'Invented asset';
/** The overlay signal's label: the key of its entry in `overlaySignalInfoMap`, and its row's series name. */
const PEER_LABEL = 'Peer';

/** One series under the pointer, as ECharts hands it to an axis tooltip. */
interface AxisRow {
    seriesName: string;
    value: number;
}

type PriceChartComponent = typeof import('./PriceChartFull.svelte').default;
type PriceChartProps = ComponentProps<PriceChartComponent>;
type Formatter = (params: unknown) => string;

let PriceChartFull: PriceChartComponent;
let helpers: typeof import('./priceChartHelpers');
let signalLabel: typeof import('$lib/charts/signalLabel');

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the chart that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n('en');
    PriceChartFull = (await import('./PriceChartFull.svelte')).default;
    helpers = await import('./priceChartHelpers');
    signalLabel = await import('$lib/charts/signalLabel');
    // The dynamic imports compile the component tree inside this hook: a budget of its own under a loaded machine.
}, 60_000);

beforeEach(() => {
    chartInstances.length = 0;
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({x: 0, y: 0, top: 0, left: 0, right: 800, bottom: 400, width: 800, height: 400, toJSON: () => ({})} as DOMRect);
});

afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
});

// =============================================================================
// Reading the tooltip
// =============================================================================

/** The option of the last full draw: the last `setOption` that carries the axis tooltip. */
function lastDraw(): Record<string, unknown> {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const draw = [...calls].reverse().find((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function');
    return draw?.option ?? {};
}

/** The days on the last draw's x-axis: one per point at the daily resolution. */
function axisDays(): string[] {
    const xAxis = lastDraw().xAxis;
    const axis = (Array.isArray(xAxis) ? xAxis[0] : xAxis) as {data?: string[]} | undefined;
    return axis?.data ?? [];
}

/** The names of the series of the last draw. */
function seriesNames(): string[] {
    return ((lastDraw().series ?? []) as Array<{name?: unknown}>).map((entry) => String(entry.name));
}

/** An overlay signal as the comparison signal renders it: its values, and the currency they are in with its flag. */
function peer(currency: string, currencyFlag: string): RenderedSignal {
    return {
        id: 'peer',
        label: PEER_LABEL,
        data: [{date: HOVERED_DAY, value: 1.5}],
        color: '#ff7f0e',
        lineWidth: 1,
        lineType: 'solid',
        markerStart: null,
        markerEnd: null,
        yAxisIndex: 0,
        aggregationProfile: 'last_with_range',
        currency,
        currencyFlag,
    };
}

/** The overlay props as the asset and FX pages pass them: the signals, and the info map built from them. */
function overlayProps(signal: RenderedSignal): Partial<PriceChartProps> {
    return {overlaySignals: [signal], overlaySignalInfoMap: signalLabel.buildOverlaySignalInfoMap([signal])};
}

/** The chart drawn with `props`, and its axis tooltip's HTML with the pointer on HOVERED_DAY over `rows`. */
async function axisTooltip(props: Partial<PriceChartProps>, rows: AxisRow[]): Promise<string> {
    render(PriceChartFull, {props: {data: DATA, currency: 'EUR', mainSeriesLabel: MAIN_LABEL, ...props}});
    await waitFor(() => expect(axisDays(), 'barrier: the chart drew at the daily resolution, one point per day').toEqual(DAYS), {timeout: 5_000});
    const formatter = (lastDraw().tooltip as {formatter: Formatter}).formatter;
    return formatter(rows.map((row) => ({axisValue: HOVERED_DAY, seriesType: 'line', color: '#2563eb', ...row})));
}

/** Barrier of the conversion cases: the chart draws the ghost series of the original values, so `conversionActive` holds. */
function expectConversionDrawn(): void {
    const ghost = helpers.computeGhostSeries(CONVERTED, false, 'daily', MAIN_LABEL);
    expect(ghost, 'premise: the converted data carries original values').not.toBeNull();
    expect(seriesNames(), 'barrier: the chart does not draw the ghost series of the original values: conversion is not active').toContain(ghost?.label);
}

/** A tooltip's HTML parsed into a detached element, as the browser parses it when ECharts sets it. */
function parse(html: string): HTMLDivElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    return host;
}

/** The verdict on a tooltip that interpolates PAYLOAD: escaped, it injects no element and reads as the payload's own text. */
function expectEscaped(html: string, where: string): void {
    const host = parse(html);
    expect(host.querySelector('[data-pwned]'), `${where}: the payload became an element — it was interpolated unescaped. Tooltip HTML: ${html}`).toBeNull();
    expect(host.textContent ?? '', `${where}: the payload does not read as text — is it on this path at all? Tooltip HTML: ${html}`).toContain(PAYLOAD);
}

const MAIN_ROW: AxisRow = {seriesName: MAIN_LABEL, value: 105};
const PEER_ROW: AxisRow = {seriesName: PEER_LABEL, value: 1.5};

// =============================================================================
// K-15 — the rows escape the currencies they name
// =============================================================================

describe('PriceChartFull — the axis tooltip rows escape what they interpolate (K-15)', {timeout: 20_000}, () => {
    describe('an overlay signal’s row', () => {
        it('control — the row names the signal’s currency in brackets, with its flag: the path of :1013 is the one the flag case takes', async () => {
            const text = parse(await axisTooltip(overlayProps(peer('USD', '🇺🇸')), [PEER_ROW])).textContent ?? '';

            expect(text, 'the overlay row does not name its currency').toContain('(🇺🇸 USD)');
        });

        it('guard — the signal’s currency code is escaped (:1013)', async () => {
            expectEscaped(await axisTooltip(overlayProps(peer(PAYLOAD, '🇺🇸')), [PEER_ROW]), 'overlay row, currency code');
        });

        it('the signal’s currency flag is escaped (:1013)', async () => {
            expectEscaped(await axisTooltip(overlayProps(peer('USD', PAYLOAD)), [PEER_ROW]), 'overlay row, currency flag');
        });
    });

    describe('the main series’ row', () => {
        it('guard — the main label goes through signalLabelToHtml, which escapes it (:1029)', async () => {
            expectEscaped(await axisTooltip({mainSeriesLabel: PAYLOAD}, [{seriesName: PAYLOAD, value: 105}]), 'main row, label');
        });

        it('control — with conversion the row names the display currency in brackets: the path of :1022 is the one the conversion cases take', async () => {
            const html = await axisTooltip({data: CONVERTED, displayCurrency: 'EUR', displayCurrencyFlag: '🇪🇺', mainCurrency: 'USD', mainCurrencyFlag: '🇺🇸'}, [MAIN_ROW]);
            expectConversionDrawn();

            expect(parse(html).textContent ?? '', 'with conversion the main row does not name the display currency').toContain('(🇪🇺 EUR)');
        });

        it('control — without conversion the row names the main currency in brackets: the path of :1025 is the one the native cases take', async () => {
            const text = parse(await axisTooltip({mainCurrency: 'USD', mainCurrencyFlag: '🇺🇸'}, [MAIN_ROW])).textContent ?? '';

            expect(text, 'without conversion the main row does not name the main currency').toContain('(🇺🇸 USD)');
        });

        it('FX conversion active: displayCurrencyFlag is escaped (:1022)', async () => {
            const html = await axisTooltip({data: CONVERTED, displayCurrency: 'EUR', displayCurrencyFlag: PAYLOAD, mainCurrency: 'USD', mainCurrencyFlag: '🇺🇸'}, [MAIN_ROW]);
            expectConversionDrawn();

            expectEscaped(html, 'main row with conversion, display currency flag');
        });

        it('FX conversion active: displayCurrency is escaped (:1022)', async () => {
            const html = await axisTooltip({data: CONVERTED, displayCurrency: PAYLOAD, displayCurrencyFlag: '🇪🇺', mainCurrency: 'USD', mainCurrencyFlag: '🇺🇸'}, [MAIN_ROW]);
            expectConversionDrawn();

            expectEscaped(html, 'main row with conversion, display currency code');
        });

        it('no conversion: mainCurrencyFlag is escaped (:1025)', async () => {
            expectEscaped(await axisTooltip({mainCurrency: 'USD', mainCurrencyFlag: PAYLOAD}, [MAIN_ROW]), 'main row, main currency flag');
        });

        it('no conversion: mainCurrency is escaped (:1025)', async () => {
            expectEscaped(await axisTooltip({mainCurrency: PAYLOAD, mainCurrencyFlag: '🇺🇸'}, [MAIN_ROW]), 'main row, main currency code');
        });
    });
});
