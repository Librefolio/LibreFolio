// @vitest-environment jsdom
/**
 * CandlestickChart.tooltipEscape.test.ts — K-15: the candles' tooltip header escapes the currencies it names.
 *
 * ## What it protects (K-15)
 *
 * The axis tooltip of `CandlestickChart` is HTML that ECharts sets as `innerHTML`. Its header names the main series and,
 * in brackets, a currency with its flag. Every text interpolated there must be escaped, or a value that holds markup
 * becomes markup. The verdict, on a payload whose markup carries a marker (`PAYLOAD`): parsed into a detached element, the
 * tooltip holds no `[data-pwned]` element, and its text holds the payload verbatim — escaped markup reads as text.
 *
 * ## Why it is red today
 *
 * `CandlestickChart.svelte`, `tooltipHeaderHtml` (:518–:527), from the props of :84–:90, renamed at :120–:123:
 * - with FX conversion active (`displayCurrency` given and different from `mainCurrency`) the suffix interpolates
 *   `displayCurrencyFlag` and `displayCurrencyProp` raw (:522);
 * - otherwise `mainCurrencyFlagProp` and `mainCurrencyProp` raw (:524).
 * The label goes through `signalLabelToHtml`, which escapes it (:526): the green guard of the harness and the verdict.
 *
 * The realistic vector is the flag: it comes from currency metadata (`getCurrencyInfo(code).flag_emoji`). The codes are
 * tested too: in this component they reach only the header string — no `Intl` call formats an amount with them — so a
 * markup code cannot crash the render.
 *
 * ## How
 *
 * The real component in jsdom, ECharts replaced by a recorder — the fake of `PriceChartFull.test.ts`, which already
 * mounts `CandlestickChart`. The tooltip is the formatter the chart handed ECharts, called with what ECharts hands an axis
 * tooltip: the items under the pointer. Layout is stubbed: jsdom measures every box as 0×0 and the chart draws only into
 * a non-empty one. The chart imports `assetTypes.ts` (through `signalLabel.ts`), which reads the generated client at
 * module load, so it is imported after asserting the generated file exists.
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
import type {LineDataPoint} from './LineChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** Markup whose element carries a marker: present after parsing only if it was interpolated unescaped. */
const PAYLOAD = '<b data-pwned="1">X</b>';

/** Three daily candles, synthetic. */
const DAYS = ['2024-03-04', '2024-03-05', '2024-03-06'];
const CANDLES: LineDataPoint[] = DAYS.map((date, index) => ({date, value: 101 + index, open: 100 + index, high: 103 + index, low: 99 + index, close: 101 + index}));
const HOVERED_DAY = DAYS[1];

type CandlestickComponent = typeof import('./CandlestickChart.svelte').default;
type CandlestickProps = ComponentProps<CandlestickComponent>;
type Formatter = (params: unknown) => string;

let CandlestickChart: CandlestickComponent;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the chart that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n('en');
    CandlestickChart = (await import('./CandlestickChart.svelte')).default;
    // The dynamic import compiles the component tree inside this hook: a budget of its own under a loaded machine.
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

/** The axis tooltip's formatter of the last full draw, if the chart has drawn. */
function lastFormatter(): Formatter | undefined {
    const calls = chartInstances.at(-1)?.setOptionCalls ?? [];
    const draw = [...calls].reverse().find((call) => typeof (call.option.tooltip as {formatter?: unknown} | undefined)?.formatter === 'function');
    return (draw?.option.tooltip as {formatter: Formatter} | undefined)?.formatter;
}

/** The candles drawn with `props`, and the tooltip's HTML with the pointer on a candle. */
async function candleTooltip(props: Partial<CandlestickProps>): Promise<string> {
    render(CandlestickChart, {props: {data: CANDLES, resolution: 'daily', currency: 'EUR', ...props}});
    await waitFor(() => expect(lastFormatter(), 'barrier: the chart drew, with its tooltip').toBeTypeOf('function'), {timeout: 5_000});
    const formatter = lastFormatter() as Formatter;
    return formatter([{axisValue: HOVERED_DAY, seriesName: 'EUR', seriesType: 'candlestick', value: [1, 101, 102, 100, 103], color: '#2563eb'}]);
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

// =============================================================================
// K-15 — the header escapes the currencies it names
// =============================================================================

describe('CandlestickChart — the tooltip header escapes what it interpolates (K-15)', {timeout: 20_000}, () => {
    it('guard — the label goes through signalLabelToHtml, which escapes it (:526)', async () => {
        expectEscaped(await candleTooltip({mainSeriesLabel: PAYLOAD}), 'header label');
    });

    it('control — with conversion the header names the display currency in brackets: the path of :522 is the one the cases below take', async () => {
        const text = parse(await candleTooltip({displayCurrency: 'USD', displayCurrencyFlag: '🇺🇸', mainCurrency: 'EUR', mainCurrencyFlag: '🇪🇺'})).textContent ?? '';

        expect(text, 'with conversion the header does not name the display currency').toContain('(🇺🇸 USD)');
    });

    it('control — without conversion the header names the main currency in brackets: the path of :524 is the one the cases below take', async () => {
        const text = parse(await candleTooltip({mainCurrency: 'EUR', mainCurrencyFlag: '🇪🇺'})).textContent ?? '';

        expect(text, 'without conversion the header does not name the main currency').toContain('(🇪🇺 EUR)');
    });

    it('FX conversion active: displayCurrencyFlag is escaped (:522)', async () => {
        expectEscaped(await candleTooltip({displayCurrency: 'USD', displayCurrencyFlag: PAYLOAD, mainCurrency: 'EUR', mainCurrencyFlag: '🇪🇺'}), 'header, display currency flag');
    });

    it('FX conversion active: displayCurrency is escaped (:522)', async () => {
        expectEscaped(await candleTooltip({displayCurrency: PAYLOAD, displayCurrencyFlag: '🇺🇸', mainCurrency: 'EUR', mainCurrencyFlag: '🇪🇺'}), 'header, display currency code');
    });

    it('no conversion: mainCurrencyFlag is escaped (:524)', async () => {
        expectEscaped(await candleTooltip({mainCurrency: 'EUR', mainCurrencyFlag: PAYLOAD}), 'header, main currency flag');
    });

    it('no conversion: mainCurrency is escaped (:524)', async () => {
        expectEscaped(await candleTooltip({mainCurrency: PAYLOAD, mainCurrencyFlag: '🇪🇺'}), 'header, main currency code');
    });
});
