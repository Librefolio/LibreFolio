// @vitest-environment jsdom
/**
 * PerformanceChart: privacy masking of the amounts the chart paints (S2b).
 *
 * WHAT IS UNDER TEST. With privacy on, every personal amount the chart shows becomes the
 * placeholder, and nothing else changes. That covers the x-axis ticks (`axisTickAmount`), the
 * net P&L label drawn at the end of each row (the `net-labels` custom series, through
 * `netValueText` and `shortMoney`), and the tooltip (`buildTooltip`, through
 * `formatCurrencyAmountPlain`). The sign, the currency symbol or code and the `(±x.x%)` return
 * stay readable: decision D8 keeps the sign outside the mask, and a percentage is not wealth.
 * The compact suffix goes INSIDE the mask, because `€•••K` would still disclose the order of
 * magnitude. The axis zero is masked too (D12: one rule; the centre stays visible through the
 * zero line).
 *
 * WHY A COMPONENT TEST. ECharts paints to a canvas, so an axis tick or a net label has no DOM an
 * E2E could read. The formatters are closures inside the option the component hands to ECharts,
 * and that option is exactly what ECharts calls when it paints. The `moneyRenderSites` gate
 * cannot see `axisTickAmount` either, because its line carries no currency token, so this file
 * is the only guard of the axis.
 *
 * WHAT IS MOCKED, AND WHY. Three things, each for a gap of the environment:
 *   - `echarts`: a recorder that keeps every `setOption` payload. jsdom has no canvas, and pixels
 *     are not the subject. It follows the same pattern as `GrowthChart.test.ts`.
 *   - `getCurrencyInfo`: the real store is a session cache filled by `GET /currencies`, empty
 *     here, and its fallback reports `symbol = code`. The `€` branch of `shortMoney` would be
 *     unreachable, so EUR gets its real symbol. Every other code keeps the fallback, which is what
 *     sends CHF down the "no symbol" branch (`-••• CHF`).
 *   - the canvas 2D context: see the `beforeAll` below.
 * Everything else is real: the component, its runes and `$derived` rows, the privacy store,
 * `maskable`, `formatCurrencyAmountPlain`, `escapeHtml` and svelte-i18n.
 *
 * WHAT IS DELIBERATELY NOT ASSERTED. Translated text: the labels, the section header, the status
 * badge and the tooltip captions all change with EN/IT/FR/ES. Rows are found by the asset name or
 * the effect description this file passes in as props. No locale-formatted number is written as
 * a literal. Every expected string is built with the same `Intl.NumberFormat` or `toLocaleString`
 * call the component makes, so the file passes on any host locale.
 *
 * THE FLAG. `enabled` in the privacy store is module state shared by every case in this file.
 * Every case sets it or checks it at the start. The `afterEach` switches it back off whatever the
 * outcome.
 */
import type {ComponentProps} from 'svelte';
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: a recorder, not a renderer.
 *
 * It answers every call `PerformanceChart` and its chart helpers make on an instance.
 * `attachChartReady` and `setupRowHighlightEvents` call `on`, `setupTooltipAutoHide` calls
 * `dispatchAction`, `scheduleFirstRenderStabilityFix` calls `isDisposed` and `resize`, and
 * `renderChart` calls `getDom` and `setOption`. It keeps every `setOption` payload, so a case can
 * read what the component decided to draw.
 *
 * `getDom()` returns the element `init()` was given. That keeps `renderChart` on its normal path:
 * it disposes and re-inits only when the instance's DOM no longer matches the bound container.
 * One mount therefore means exactly one instance.
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
            getOption: () => merged,
            getWidth: () => 1200,
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

/** EUR as `GET /currencies` describes it. Shared by the mock and by the expectations, so the two
 *  cannot drift apart. */
const {EUR_INFO} = vi.hoisted(() => ({
    EUR_INFO: {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [] as string[], country_names: [] as string[]},
}));

vi.mock('$lib/stores/reference/currencyStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/currencyStore')>()),
    getCurrencyInfo: (code: string) => (code === EUR_INFO.code ? EUR_INFO : {code, name: code, symbol: code, flag_emoji: '🏳️', country_codes: [], country_names: []}),
}));

import {render, setupI18n, waitFor} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import PerformanceChart from './PerformanceChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

type ChartProps = ComponentProps<typeof PerformanceChart>;

/** Decimals travel as strings in the API contract (`period_pnl: '2299.21'`). */
const decimal = (value: number) => value.toFixed(2);

/**
 * One EUR position whose four components add up to its net, plus one other period effect, so the
 * chart draws both row kinds (and the section row between them).
 *
 * The amounts are distinctive on purpose. No formatted amount is a substring of another one, or
 * of one of the `(±x.x%)` returns printed beside it. So "this amount is printed" and "this amount
 * is absent" can be neither satisfied nor broken by a neighbour. The net is above 1000, so its
 * clear label carries a compact suffix (`2.3K` in English) that the mask has to swallow.
 */
const EUR_POSITION = {unrealized: 1234.56, realized: 789.01, income: 321.47, feesTaxes: 45.83, net: 2299.21, start: 4321.98, end: 6621.19};
const EUR_EFFECT_NET = -67.89;

const EUR_ASSET = {
    asset_id: 4101,
    asset_name: 'Privacy Probe Equity',
    asset_type: 'STOCK',
    broker_id: 7,
    broker_name: 'Probe Broker',
    period_unrealized_delta: decimal(EUR_POSITION.unrealized),
    period_realized_gain_loss: decimal(EUR_POSITION.realized),
    period_income: decimal(EUR_POSITION.income),
    period_fees_taxes: decimal(EUR_POSITION.feesTaxes),
    period_pnl: decimal(EUR_POSITION.net),
    start_value: decimal(EUR_POSITION.start),
    end_value: decimal(EUR_POSITION.end),
    is_fully_sold: false,
};

const EUR_EFFECT = {description: 'Probe reconciliation', category: 'Other', period_pnl: decimal(EUR_EFFECT_NET), broker_id: 7, broker_name: 'Probe Broker'};

/** Every amount the asset row's tooltip prints: the net, the four components, the start value
 *  and the end value. */
const EUR_ASSET_AMOUNTS = [EUR_POSITION.net, EUR_POSITION.unrealized, EUR_POSITION.realized, EUR_POSITION.income, EUR_POSITION.feesTaxes, EUR_POSITION.start, EUR_POSITION.end];

/** A losing position in a currency with no symbol of its own. */
const CHF_POSITION = {net: -1876.54, start: 9876.12, end: 7999.58};

const CHF_ASSET = {
    asset_id: 4202,
    asset_name: 'Privacy Probe Bond',
    asset_type: 'BOND',
    broker_id: 8,
    broker_name: 'Probe Bank',
    period_unrealized_delta: decimal(CHF_POSITION.net),
    period_realized_gain_loss: decimal(0),
    period_income: decimal(0),
    period_fees_taxes: decimal(0),
    period_pnl: decimal(CHF_POSITION.net),
    start_value: decimal(CHF_POSITION.start),
    end_value: decimal(CHF_POSITION.end),
    is_fully_sold: false,
};

const EUR_PROPS: ChartProps = {positions: [EUR_ASSET], otherEffects: [EUR_EFFECT], displayCurrency: 'EUR'};
const CHF_PROPS: ChartProps = {positions: [CHF_ASSET], otherEffects: [], displayCurrency: 'CHF'};

// =============================================================================
// What the component prints, rebuilt with the calls it makes
// =============================================================================

/** The number `axisTickAmount` prints, from the same `Intl.NumberFormat` call. */
function tickNumber(abs: number): string {
    return new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: abs < 10 ? 2 : abs < 100 ? 1 : 0}).format(abs);
}

/** The number `shortMoney` prints for an amount of 1000 or more, from the same call. */
function compactNet(abs: number): string {
    if (abs < 1000) throw new Error(`compactNet mirrors only the compact branch of shortMoney, and ${abs} takes the other one`);
    return new Intl.NumberFormat(undefined, {notation: 'compact', maximumFractionDigits: 1}).format(abs);
}

/** `formatSignedPercent` applied to the return on the opening value: `+53.2%`. */
function returnPct(value: number, opening: number): string {
    const pct = (value / opening) * 100;
    return `${pct > 0 ? '+' : ''}${pct.toLocaleString(undefined, {minimumFractionDigits: 1, maximumFractionDigits: 1})}%`;
}

/** The suffix `openingPctPlainSuffix` appends to a net label: ` (+53.2%)`. */
const labelSuffix = (value: number, opening: number) => ` (${returnPct(value, opening)})`;

/** The number `formatCurrencyAmountPlain` prints in the tooltip: absolute value, two decimals. */
function plainAmount(value: number): string {
    return Math.abs(value).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

/** What `formatCurrencyAmountPlain` appends for EUR under the currency mock: symbol, flag, code. */
const EUR_TAIL = ` ${EUR_INFO.symbol} ${EUR_INFO.flag_emoji} ${EUR_INFO.code}`;

// =============================================================================
// Reading what the component handed to ECharts
// =============================================================================

type FakeChart = (typeof chartInstances)[number];
type AxisFormatter = (value: number) => string;
type TooltipFormatter = (params: Array<{dataIndex: number}>) => string;
type NetLabelDatum = [number, number];

/** The `api` a custom series' `renderItem` receives, reduced to the two calls the net label makes. */
interface RenderItemApi {
    value: (dimension: number) => number;
    coord: (point: [number, number]) => [number, number];
}

type RenderItem = (params: {coordSys: {x: number; width: number}}, api: RenderItemApi) => {style?: {text?: unknown}} | null;

/** The parts of a full option that the cases read. */
interface FullOption {
    xAxis: {axisLabel: {formatter: AxisFormatter}};
    yAxis: {data: number[]; axisLabel: {formatter: AxisFormatter}};
    tooltip: {formatter: TooltipFormatter};
    series: Array<{name?: string; data?: NetLabelDatum[]; renderItem?: RenderItem}>;
}

/**
 * `renderChart` hands ECharts a full option on every render (`setOption(buildOption(…), true)`).
 * The only other `setOption` the component issues is the mobile row highlight, a `{series}` patch
 * with neither axis nor tooltip. So a full option is one that carries all three.
 */
function isFullOption(option: Record<string, unknown>): boolean {
    return option.xAxis != null && option.tooltip != null && Array.isArray(option.series);
}

function fullOptionsSince(chart: FakeChart, since: number): FullOption[] {
    return chart.setOptionCalls
        .slice(since)
        .filter((call) => isFullOption(call.option))
        .map((call) => call.option as unknown as FullOption);
}

/** The option ECharts is painting right now: the last full one it was given. */
function latestFullOption(chart: FakeChart): FullOption {
    const options = fullOptionsSince(chart, 0);
    if (options.length === 0) throw new Error('PerformanceChart never handed ECharts a full option');
    return options[options.length - 1];
}

/** Waits for a full option recorded after call `since`, and returns the latest one. */
async function fullOptionAfter(chart: FakeChart, since: number): Promise<FullOption> {
    await waitFor(() => expect(fullOptionsSince(chart, since).length).toBeGreaterThan(0), {timeout: 5_000});
    const options = fullOptionsSince(chart, since);
    return options[options.length - 1];
}

/** The one chart instance mounted inside `container`. */
function chartIn(container: HTMLElement): FakeChart {
    const charts = chartInstances.filter((chart) => container.contains(chart.getDom() as Node));
    if (charts.length !== 1) throw new Error(`expected one chart instance in this render, found ${charts.length}`);
    return charts[0];
}

/** Mounts the chart and waits for its first full option. */
async function mountChart(props: ChartProps): Promise<FakeChart> {
    const {container} = render(PerformanceChart, {props});
    const chart = await waitFor(() => chartIn(container), {timeout: 5_000});
    await fullOptionAfter(chart, 0);
    return chart;
}

/**
 * The display row labelled `name`, an asset name or an effect description this file passed in.
 * It is found through the y-axis label formatter, never by position: the order belongs to the
 * component (largest mover first, then the section row, then the effects).
 */
function rowIndexOf(option: FullOption, name: string): number {
    const matches = option.yAxis.data.filter((value) => option.yAxis.axisLabel.formatter(value).includes(name));
    if (matches.length !== 1) throw new Error(`expected one y-axis row labelled "${name}", found ${matches.length} (a mobile layout prints no y-axis label)`);
    return matches[0];
}

/** The net label that the `net-labels` custom series draws for row `name`, through its own `renderItem`. */
function netLabelOf(option: FullOption, name: string): string {
    const rowIndex = rowIndexOf(option, name);
    const series = option.series.find((entry) => entry.name === 'net-labels');
    if (!series?.renderItem || !series.data) throw new Error('the option carries no net-labels custom series');
    const datum = series.data.find((entry) => entry[0] === rowIndex);
    if (!datum) throw new Error(`net-labels carries no datum for row ${rowIndex}`);
    // A fake grid: 40 px per row, and the plot from x = 260 to x = 660 (the desktop grid). These
    // only position the text. The text depends on the width left after the plot, which in jsdom
    // (no layout, clientWidth 0) is the component's fixed 82 px.
    const api: RenderItemApi = {value: (dimension) => datum[dimension], coord: ([x, y]) => [x, y * 40]};
    const drawn = series.renderItem({coordSys: {x: 260, width: 400}}, api);
    const text = drawn?.style?.text;
    if (typeof text !== 'string') throw new Error(`net-labels drew no text for row ${rowIndex}`);
    return text;
}

/** The tooltip ECharts would show when the user hovers row `name`. */
function tooltipOf(option: FullOption, name: string): string {
    return option.tooltip.formatter([{dataIndex: rowIndexOf(option, name)}]);
}

// =============================================================================
// Harness
// =============================================================================

let restoreCanvas: () => void = () => {};

beforeAll(async () => {
    await setupI18n();
    // jsdom has no canvas: `getContext('2d')` logs "Not implemented" and returns null. The
    // component measures each net label to decide whether its `(±x.x%)` suffix fits. Without a
    // context it falls back to an estimate (0.6 em per character) that leaves no label of this
    // file with its suffix. These cases are about what the label says when the suffix fits, so
    // the context measures one pixel per character, and every label here fits the 82 px. The
    // component caches the context per instance (`netLabelMeasureCtx`), so the stub goes in
    // before the first mount and stays for the whole file.
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({font: '', measureText: (text: string) => ({width: text.length})} as never);
    restoreCanvas = () => getContext.mockRestore();
});

afterAll(() => restoreCanvas());

beforeEach(() => {
    chartInstances.length = 0;
});

// =============================================================================
// S2b: privacy masking of the axis ticks, the net labels and the tooltip
// =============================================================================

describe('PerformanceChart privacy masking (S2b)', () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case.
    afterEach(() => setPrivacyEnabled(false));

    describe('with privacy on', () => {
        it('masks the x-axis ticks, zero included, and keeps the minus outside the mask', async () => {
            // WHY: the ticks print the scale of the chart (-2K … 2K). A clear tick reveals the
            // size of the largest mover even when every label is masked, and the gate cannot
            // see `axisTickAmount`. Catches `maskable` dropped from the zero branch (D12) or
            // the compact branch, the suffix left outside the mask, or the minus moved inside it.
            setPrivacyEnabled(true);
            const chart = await mountChart(EUR_PROPS);

            const axisTick = latestFullOption(chart).xAxis.axisLabel.formatter;
            expect(axisTick(1500)).toBe(PRIVACY_PLACEHOLDER);
            expect(axisTick(-1500)).toBe(`-${PRIVACY_PLACEHOLDER}`);
            expect(axisTick(0)).toBe(PRIVACY_PLACEHOLDER);
        });

        it('masks a EUR net label as +€•••: sign and symbol readable, compact suffix inside the mask, return kept', async () => {
            // WHY: the net label is the amount painted on every row without hovering. Catches
            // `maskable` dropped from the symbol branch of `shortMoney`, the compact suffix left
            // outside the mask (`€•••K`), the sign or the symbol swallowed by it (D8), and the
            // return masked or dropped. Only exact equality refuses `€•••K`.
            setPrivacyEnabled(true);
            const chart = await mountChart(EUR_PROPS);

            expect(netLabelOf(latestFullOption(chart), EUR_ASSET.asset_name)).toBe(`+${EUR_INFO.symbol}${PRIVACY_PLACEHOLDER}${labelSuffix(EUR_POSITION.net, EUR_POSITION.start)}`);
        });

        it('masks a CHF net label as -••• CHF: a currency without a symbol keeps its code after the mask', async () => {
            // WHY: the same label through the other branch of `shortMoney`, a separate template
            // literal, so masking one branch does not mask the other. Catches `maskable` dropped
            // from the no-symbol branch only, or the minus or the code swallowed by the mask.
            setPrivacyEnabled(true);
            const chart = await mountChart(CHF_PROPS);

            expect(netLabelOf(latestFullOption(chart), CHF_ASSET.asset_name)).toBe(`-${PRIVACY_PLACEHOLDER} CHF${labelSuffix(CHF_POSITION.net, CHF_POSITION.start)}`);
        });

        it('prints no tooltip amount in the clear, on an asset row or an other-effect row', async () => {
            // WHY: the tooltip shows the exact figures, to the cent. Catches an amount routed
            // around the mask of `formatCurrencyAmountPlain`: `sensitivity: 'public'` at one of
            // its call sites, or a row formatted another way. The other-effect row has its own
            // branch in `buildTooltip`, so it is checked separately. The check cannot be "no
            // digit at all", because the `(±x.x%)` returns legitimately stay.
            expect(isPrivacyEnabled()).toBe(false);
            const chart = await mountChart(EUR_PROPS);

            // Barrier: with privacy off, every needle is really printed. So its absence below
            // cannot pass because a needle was built differently from the component's number.
            const clear = latestFullOption(chart);
            const assetClear = tooltipOf(clear, EUR_ASSET.asset_name);
            for (const amount of EUR_ASSET_AMOUNTS) expect(assetClear).toContain(plainAmount(amount));
            expect(tooltipOf(clear, EUR_EFFECT.description)).toContain(plainAmount(EUR_EFFECT_NET));

            // The formatter reads the flag when it is called, which is when ECharts calls it on
            // hover. Whether a redraw follows the toggle is the subject of the toggle case.
            setPrivacyEnabled(true);
            const masked = latestFullOption(chart);

            const assetMasked = tooltipOf(masked, EUR_ASSET.asset_name);
            expect(assetMasked).toContain(EUR_ASSET.asset_name);
            expect(assetMasked).toContain(PRIVACY_PLACEHOLDER);
            for (const amount of EUR_ASSET_AMOUNTS) expect(assetMasked, plainAmount(amount)).not.toContain(plainAmount(amount));

            const effectMasked = tooltipOf(masked, EUR_EFFECT.description);
            expect(effectMasked).toContain(EUR_EFFECT.description);
            expect(effectMasked).toContain(PRIVACY_PLACEHOLDER);
            expect(effectMasked).not.toContain(plainAmount(EUR_EFFECT_NET));
        });
    });

    it('pushes a new full option when privacy is toggled, in both directions', async () => {
        // WHY: ECharts runs a formatter only while painting, and paints only when it is handed an
        // option. A formatter that reads the flag live is not enough: the ticks and labels
        // already on screen would stay as they are. Catches the render effect losing its
        // dependency on the flag (`void shouldMaskAmount()` deleted, or the read moved into
        // `renderChart`, which runs inside `tick().then`, where a read registers nothing).
        expect(isPrivacyEnabled()).toBe(false);
        const chart = await mountChart(EUR_PROPS);
        expect(latestFullOption(chart).xAxis.axisLabel.formatter(1500)).toBe(tickNumber(1500));

        // OFF to ON is the direction that leaks. ON to OFF is checked too, so a component that
        // redraws only once cannot pass.
        const beforeOn = chart.setOptionCalls.length;
        setPrivacyEnabled(true);
        const masked = await fullOptionAfter(chart, beforeOn);
        expect(masked.xAxis.axisLabel.formatter(1500)).toBe(PRIVACY_PLACEHOLDER);

        const beforeOff = chart.setOptionCalls.length;
        setPrivacyEnabled(false);
        const unmasked = await fullOptionAfter(chart, beforeOff);
        expect(unmasked.xAxis.axisLabel.formatter(1500)).toBe(tickNumber(1500));
    });

    it('with privacy off, prints exactly what it printed before masking existed', async () => {
        // WHY: masking must be a pure overlay. With the flag off, not one character of today's
        // output may change. Catches `maskable` made unconditional, a changed compaction step or
        // sign rule, a different composition of sign, symbol and number, or a dropped return.
        // Today the component prefixes an ASCII `-` to the formatted absolute value, and the
        // expectations mirror that. On a locale whose minus is U+2212 (sv-SE), that already
        // differs from `format(-x)`. It is a known follow-up, pinned here as it stands.
        expect(isPrivacyEnabled()).toBe(false);
        const eur = latestFullOption(await mountChart(EUR_PROPS));

        const axisTick = eur.xAxis.axisLabel.formatter;
        expect(axisTick(1500)).toBe(tickNumber(1500));
        expect(axisTick(-1500)).toBe(`-${tickNumber(1500)}`);
        // `'0'` is a literal in the component too, not a formatted number.
        expect(axisTick(0)).toBe('0');

        expect(netLabelOf(eur, EUR_ASSET.asset_name)).toBe(`+${EUR_INFO.symbol}${compactNet(EUR_POSITION.net)}${labelSuffix(EUR_POSITION.net, EUR_POSITION.start)}`);

        // The net and the four components carry a sign and their return. Costs are shown
        // negative. The start and end values carry neither.
        const assetTooltip = tooltipOf(eur, EUR_ASSET.asset_name);
        for (const value of [EUR_POSITION.net, EUR_POSITION.unrealized, EUR_POSITION.realized, EUR_POSITION.income, -EUR_POSITION.feesTaxes]) {
            expect(assetTooltip).toContain(`${value > 0 ? '+' : '-'}${plainAmount(value)}${EUR_TAIL}`);
            expect(assetTooltip).toContain(`(${returnPct(value, EUR_POSITION.start)})`);
        }
        expect(assetTooltip).toContain(`${plainAmount(EUR_POSITION.start)}${EUR_TAIL}`);
        expect(assetTooltip).toContain(`${plainAmount(EUR_POSITION.end)}${EUR_TAIL}`);
        expect(assetTooltip).not.toContain(PRIVACY_PLACEHOLDER);

        const effectTooltip = tooltipOf(eur, EUR_EFFECT.description);
        expect(effectTooltip).toContain(`-${plainAmount(EUR_EFFECT_NET)}${EUR_TAIL}`);
        expect(effectTooltip).not.toContain(PRIVACY_PLACEHOLDER);

        const chf = latestFullOption(await mountChart(CHF_PROPS));
        expect(netLabelOf(chf, CHF_ASSET.asset_name)).toBe(`-${compactNet(Math.abs(CHF_POSITION.net))} CHF${labelSuffix(CHF_POSITION.net, CHF_POSITION.start)}`);
    });
});
