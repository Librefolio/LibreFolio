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
 * a literal against the host's locale. Every expected string is either built with the same
 * `Intl.NumberFormat` or `toLocaleString` call the component makes, so the file passes on any
 * host locale, or pinned as a literal under a locale the case forces. Two kinds of literal are
 * pinned that way on purpose: the U+2212 of the sv-SE cases (D23), where the glyph itself is the
 * subject, and the axis ticks of S7b, where the exact label is the subject.
 *
 * THE AXIS TICKS (S7b: D18, D23, D25). A tick prints the SIGNED amount through one compact
 * `Intl.NumberFormat` call with exact digits: no two ticks share a label, and the minus is the
 * locale's. The two edge ticks sit on the bounds the chart fixes, so their labels are hidden.
 * The last describe pins all three.
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

/** A small loss in a currency with no symbol: the short branch of `shortMoney` through its
 *  no-symbol template, which the EUR effect row does not reach. Only the D23 case mounts it. */
const CHF_EFFECT_NET = -43.21;
const CHF_EFFECT = {description: 'Probe franc adjustment', category: 'Other', period_pnl: decimal(CHF_EFFECT_NET), broker_id: 8, broker_name: 'Probe Bank'};
const CHF_EFFECT_PROPS: ChartProps = {positions: [CHF_ASSET], otherEffects: [CHF_EFFECT], displayCurrency: 'CHF'};

/** A large loss in a currency with a symbol: the compact branch of `shortMoney` with a minus,
 *  through its symbol template. The EUR position is a gain, so no other EUR row reaches it. Only
 *  the D23 compact case mounts it. */
const EUR_LOSS_EFFECT_NET = -3456.78;
const EUR_LOSS_EFFECT = {description: 'Probe write-down', category: 'Other', period_pnl: decimal(EUR_LOSS_EFFECT_NET), broker_id: 7, broker_name: 'Probe Broker'};
const EUR_LOSS_EFFECT_PROPS: ChartProps = {positions: [EUR_ASSET], otherEffects: [EUR_LOSS_EFFECT], displayCurrency: 'EUR'};

// =============================================================================
// What the component prints, rebuilt with the calls it makes
// =============================================================================

/** A sign at the start of a formatted number, bidi marks included: the pattern `shortMoney` and
 *  `maskFormattedNumber` split off and keep outside the mask. */
const LEADING_SIGN = /^[\p{Cf}+\-\u2212]*/u;

interface SignedNumber {
    /** The sign as the locale writes it: `+`, its own minus, or nothing on a zero. */
    sign: string;
    digits: string;
}

function splitSign(formatted: string): SignedNumber {
    const sign = LEADING_SIGN.exec(formatted)?.[0] ?? '';
    return {sign, digits: formatted.slice(sign.length)};
}

/** The real constructor, taken before any case spies on it. The expectations are built through
 *  it, so a spy on `Intl.NumberFormat` can never feed both sides of a comparison. */
const RealNumberFormat = Intl.NumberFormat;

/** A locale whose minus is U+2212 MINUS SIGN, where Node's default locale writes a hyphen. */
const SWEDISH = 'sv-SE';

/**
 * What `axisTickAmount` prints, from the same call: compact, with exact digits, on the SIGNED
 * value (S7b). The sign therefore comes out of the call as the locale writes it (D23), and two
 * ticks never share a label (D18). A negative zero prints as zero. Built through the real
 * constructor, like every expectation here. `locale` forces one; `undefined` is this machine's.
 */
function tickNumber(value: number, locale?: string): string {
    return new RealNumberFormat(locale, {notation: 'compact', maximumSignificantDigits: 15}).format(value === 0 ? 0 : value);
}

/**
 * What `shortMoney` prints for an amount of 1000 or more, from the same call: compact, on the
 * SIGNED value, with `exceptZero`. The sign therefore comes out of the call as the locale writes
 * it (D23), never from a literal here. `locale` forces one.
 */
function compactNet(value: number, locale?: string): SignedNumber {
    if (Math.abs(value) < 1000) throw new Error(`compactNet mirrors only the compact branch of shortMoney, and ${value} takes the other one`);
    return splitSign(new RealNumberFormat(locale, {notation: 'compact', maximumFractionDigits: 1, signDisplay: 'exceptZero'}).format(value));
}

/** What `shortMoney` prints for an amount under 1000, from the same call. `locale` forces one. */
function plainNet(value: number, locale?: string): SignedNumber {
    const abs = Math.abs(value);
    if (abs >= 1000) throw new Error(`plainNet mirrors only the short branch of shortMoney, and ${value} takes the compact one`);
    return splitSign((value === 0 ? 0 : value).toLocaleString(locale, {minimumFractionDigits: abs % 1 === 0 ? 0 : 2, maximumFractionDigits: 2, signDisplay: 'exceptZero'}));
}

/**
 * Runs `read` with every `Number.prototype.toLocaleString` call forced to `locale`, the
 * component's own included. Synchronous on purpose: the spy comes off before anything else runs.
 */
function inLocale<T>(locale: string, read: () => T): T {
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
 * Runs `read` with every `new Intl.NumberFormat(undefined, …)` forced to `locale`: the call the
 * compact branch of `shortMoney` makes, which the spy of `inLocale` does not reach. A call that
 * names its locale passes through untouched. Returns what `read` returned and the options of
 * every call that asked for the default locale, so a case can prove which branch it reached.
 * Synchronous like `inLocale`, and restored whatever the outcome.
 */
function inNumberFormatLocale<T>(locale: string, read: () => T): {value: T; defaultLocaleCalls: Intl.NumberFormatOptions[]} {
    const defaultLocaleCalls: Intl.NumberFormatOptions[] = [];
    // The component calls it with `new`, and the spy forwards `new` to the implementation, so the
    // implementation must be a constructor: a `function`, never an arrow. A constructor that
    // returns an object makes that object the result: the component gets a real `NumberFormat`.
    const spy = vi.spyOn(Intl, 'NumberFormat').mockImplementation(function (...args: ConstructorParameters<typeof Intl.NumberFormat>) {
        const [locales, options] = args;
        if (locales !== undefined) return new RealNumberFormat(locales, options);
        defaultLocaleCalls.push({...options});
        return new RealNumberFormat(locale, options);
    });
    try {
        return {value: read(), defaultLocaleCalls};
    } finally {
        spy.mockRestore();
    }
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
    xAxis: {min?: number; max?: number; axisLabel: {formatter: AxisFormatter; showMinLabel?: boolean; showMaxLabel?: boolean}};
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
        it("masks the x-axis ticks, zero included, and keeps the locale's minus outside the mask", async () => {
            // WHY: the ticks print the scale of the chart (-2K … 2K). A clear tick reveals the
            // size of the largest mover even when every label is masked, and the gate cannot
            // see `axisTickAmount`. Catches the mask dropped from zero (D12) or from any other
            // tick, the compact suffix left outside the mask, or the minus moved inside it. The
            // minus kept outside is the locale's (D23). On this machine it comes from the same
            // call the tick makes. Under a forced sv-SE it must be U+2212, which a minus written
            // by hand in front of the mask never is.
            // Preconditions: this machine's locale writes a minus on a loss, so the masked loss
            // is about one; and this Node has Swedish locale data and writes U+2212 there.
            const hostMinus = splitSign(tickNumber(-1500)).sign;
            expect(hostMinus).toMatch(/[-\u2212]/);
            expect(splitSign(tickNumber(-1500, SWEDISH)).sign).toBe('\u2212');
            setPrivacyEnabled(true);
            const chart = await mountChart(EUR_PROPS);

            const axisTick = latestFullOption(chart).xAxis.axisLabel.formatter;
            expect([1500, -1500, 0].map((value) => axisTick(value))).toEqual([PRIVACY_PLACEHOLDER, `${hostMinus}${PRIVACY_PLACEHOLDER}`, PRIVACY_PLACEHOLDER]);

            const swedish = inNumberFormatLocale(SWEDISH, () => axisTick(-1500));
            // Guard: the tick asked the default locale for a compact number, so the forced locale
            // reached it.
            expect(
                swedish.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
                'the masked tick never asked the default locale for a compact number',
            ).toBe(true);
            expect(swedish.value).toBe(`\u2212${PRIVACY_PLACEHOLDER}`);
        });

        it('masks a EUR net label as +€•••: sign and symbol readable, compact suffix inside the mask, return kept', async () => {
            // WHY: the net label is the amount painted on every row without hovering. Catches
            // `maskable` dropped from the symbol branch of `shortMoney`, the compact suffix left
            // outside the mask (`€•••K`), the sign or the symbol swallowed by it (D8), and the
            // return masked or dropped. Only exact equality refuses `€•••K`.
            setPrivacyEnabled(true);
            const chart = await mountChart(EUR_PROPS);

            const {sign} = compactNet(EUR_POSITION.net);
            // Precondition: a gain carries a sign, so the check below is about one.
            expect(sign).not.toBe('');
            expect(netLabelOf(latestFullOption(chart), EUR_ASSET.asset_name)).toBe(`${sign}${EUR_INFO.symbol}${PRIVACY_PLACEHOLDER}${labelSuffix(EUR_POSITION.net, EUR_POSITION.start)}`);
        });

        it('masks a CHF net label as -••• CHF: a currency without a symbol keeps its code after the mask', async () => {
            // WHY: the same label through the other branch of `shortMoney`, a separate template
            // literal, so masking one branch does not mask the other. Catches `maskable` dropped
            // from the no-symbol branch only, or the minus or the code swallowed by the mask. The
            // minus is the one the locale writes (D23), taken from the component's own call.
            setPrivacyEnabled(true);
            const chart = await mountChart(CHF_PROPS);

            const {sign} = compactNet(CHF_POSITION.net);
            // Precondition: a loss carries a minus, whichever glyph the locale writes.
            expect(sign).toMatch(/[-\u2212]/);
            expect(netLabelOf(latestFullOption(chart), CHF_ASSET.asset_name)).toBe(`${sign}${PRIVACY_PLACEHOLDER} CHF${labelSuffix(CHF_POSITION.net, CHF_POSITION.start)}`);
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
        // The net label takes its sign from the same Intl call as its digits (D23), so its
        // expectation takes the sign from that call too, in whatever glyph the locale writes; the
        // sv-SE cases below pin the glyph itself. The axis tick takes its sign from the same call
        // as its digits too (S7b, D23), so its expectation is built by that call; the S7b
        // describe pins its sv-SE glyphs. The tooltip's ASCII sign is the convention of
        // `formatCurrencyAmountPlain` (`currencyFormat.ts`), tracked outside this workstream.
        expect(isPrivacyEnabled()).toBe(false);
        const eur = latestFullOption(await mountChart(EUR_PROPS));

        const axisTick = eur.xAxis.axisLabel.formatter;
        expect(axisTick(1500)).toBe(tickNumber(1500));
        expect(axisTick(-1500)).toBe(tickNumber(-1500));
        // Zero is a formatted number like any other tick, so its literal is pinned under a forced
        // en-US, never against this machine's locale.
        expect(inNumberFormatLocale('en-US', () => axisTick(0)).value).toBe('0');

        const eurNet = compactNet(EUR_POSITION.net);
        // Precondition: the net carries a sign, so the check below is about one.
        expect(eurNet.sign).not.toBe('');
        expect(netLabelOf(eur, EUR_ASSET.asset_name)).toBe(`${eurNet.sign}${EUR_INFO.symbol}${eurNet.digits}${labelSuffix(EUR_POSITION.net, EUR_POSITION.start)}`);
        // The other-effect row goes through the short branch, and carries no return.
        const effectNet = plainNet(EUR_EFFECT_NET);
        expect(effectNet.sign).not.toBe('');
        expect(netLabelOf(eur, EUR_EFFECT.description)).toBe(`${effectNet.sign}${EUR_INFO.symbol}${effectNet.digits}`);

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
        const chfNet = compactNet(CHF_POSITION.net);
        expect(chfNet.sign).not.toBe('');
        expect(netLabelOf(chf, CHF_ASSET.asset_name)).toBe(`${chfNet.sign}${chfNet.digits} CHF${labelSuffix(CHF_POSITION.net, CHF_POSITION.start)}`);
    });
});

// =============================================================================
// D23: the net label writes the locale's minus
// =============================================================================

describe('PerformanceChart net label sign (D23)', () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case.
    afterEach(() => setPrivacyEnabled(false));

    /** `shortMoney` composes the sign in two template literals, one per currency kind. */
    const SYMBOL_TEMPLATE = (sign: string, number: string) => `${sign}${EUR_INFO.symbol}${number}`;
    const CODE_TEMPLATE = (sign: string, number: string) => `${sign}${number} CHF`;

    /** Each template through the short branch of `shortMoney`, under 1000. */
    const TEMPLATES = [
        {title: 'EUR, the symbol template', props: EUR_PROPS, row: EUR_EFFECT.description, net: EUR_EFFECT_NET, compose: SYMBOL_TEMPLATE},
        {title: 'CHF, the no-symbol template', props: CHF_EFFECT_PROPS, row: CHF_EFFECT.description, net: CHF_EFFECT_NET, compose: CODE_TEMPLATE},
    ];

    /** Each template through the compact branch, 1000 or more, on a loss. The CHF row is a
     *  position, so its label ends with its return, which an effect row does not carry. */
    const COMPACT_TEMPLATES = [
        {title: 'EUR, the symbol template', props: EUR_LOSS_EFFECT_PROPS, row: EUR_LOSS_EFFECT.description, net: EUR_LOSS_EFFECT_NET, suffix: '', compose: SYMBOL_TEMPLATE},
        {title: 'CHF, the no-symbol template', props: CHF_PROPS, row: CHF_ASSET.asset_name, net: CHF_POSITION.net, suffix: labelSuffix(CHF_POSITION.net, CHF_POSITION.start), compose: CODE_TEMPLATE},
    ];

    it.each(TEMPLATES)("writes the locale's own minus in the net label, in the clear and masked, U+2212 in sv-SE: $title", async ({props, row, net, compose}) => {
        // WHY: in Node's default locale the minus is a hyphen, the very character a hand-written
        // sign would use, so the cases above cannot tell the two apart. Forcing the one call the
        // label's short branch makes, `Number.prototype.toLocaleString`, to a locale whose minus
        // is U+2212 can. Catches a sign written by hand again (`amount < 0 ? '-' : ''`) in either
        // template, and a mask that swallows it. The glyph is a literal here on purpose: it is
        // the subject. The compact branch builds its own `Intl.NumberFormat`, which this spy does
        // not reach: the next case forces that constructor instead.
        // Precondition: this Node has Swedish locale data and writes U+2212 there. Without it the
        // locale would fall back in silence and the check would prove nothing.
        expect(plainNet(-1, SWEDISH).sign).toBe('\u2212');
        expect(isPrivacyEnabled()).toBe(false);
        const chart = await mountChart(props);

        const clear = inLocale(SWEDISH, () => netLabelOf(latestFullOption(chart), row));
        expect(clear).toBe(compose('\u2212', plainNet(net, SWEDISH).digits));

        const beforeOn = chart.setOptionCalls.length;
        setPrivacyEnabled(true);
        const masked = await fullOptionAfter(chart, beforeOn);
        expect(inLocale(SWEDISH, () => netLabelOf(masked, row))).toBe(compose('\u2212', PRIVACY_PLACEHOLDER));
    });

    it.each(COMPACT_TEMPLATES)("writes the locale's own minus in a compact net label, in the clear and masked, U+2212 in sv-SE: $title", async ({props, row, net, suffix, compose}) => {
        // WHY: the compact branch prints the label most real rows show (`+€1.2K`), and it builds
        // its own `Intl.NumberFormat`, out of reach of the `toLocaleString` spy above. In Node's
        // default locale its minus is a hyphen too, so a sign written by hand in this branch,
        // `(amount < 0 ? '-' : '') + format(abs)`, passes every host-locale case. Forcing the
        // default-locale constructor to a locale whose minus is U+2212 tells the two apart: the
        // digits turn Swedish either way, the sign only if it comes out of the same call. Catches
        // that hand-written sign in either template, a mask that swallows the sign, and a mask
        // that leaks the compact suffix. Swedish writes its thousands as a word (`tn`) after a
        // no-break space, and a word left outside the mask discloses the order of magnitude just
        // as `€•••K` would. The glyph is a literal here on purpose: it is the subject. The return
        // after a position's label goes through `toLocaleString`, which this spy leaves alone, so
        // it keeps the host's form.
        const swedish = compactNet(net, SWEDISH);
        // Preconditions, through the real constructor with an explicit locale. This Node has
        // Swedish locale data and writes U+2212 in a compact number there: without it the forced
        // locale would fall back in silence and prove nothing. And the Swedish compact suffix
        // carries a word, so its absence from the masked label is about something.
        expect(swedish.sign).toBe('\u2212');
        const suffixWord = /\p{L}+/u.exec(swedish.digits)?.[0] ?? '';
        expect(suffixWord, `the Swedish compact number "${swedish.digits}" carries no word suffix`).not.toBe('');
        expect(isPrivacyEnabled()).toBe(false);
        const chart = await mountChart(props);

        const clear = inNumberFormatLocale(SWEDISH, () => netLabelOf(latestFullOption(chart), row));
        // Guard: the label asked the default locale for a compact number, so it took the compact
        // branch and its locale was the forced one.
        expect(
            clear.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
            'the clear label never asked the default locale for a compact number',
        ).toBe(true);
        expect(clear.value).toBe(`${compose('\u2212', swedish.digits)}${suffix}`);

        const beforeOn = chart.setOptionCalls.length;
        setPrivacyEnabled(true);
        const maskedOption = await fullOptionAfter(chart, beforeOn);
        const masked = inNumberFormatLocale(SWEDISH, () => netLabelOf(maskedOption, row));
        expect(
            masked.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
            'the masked label never asked the default locale for a compact number',
        ).toBe(true);
        expect(masked.value).toBe(`${compose('\u2212', PRIVACY_PLACEHOLDER)}${suffix}`);
        expect(masked.value).not.toContain(suffixWord);
    });
});

// =============================================================================
// S7b — the axis ticks: distinct, in the locale's glyphs, the fixed edges unlabelled
// =============================================================================

/**
 * The x axis prints the amount scale of the chart through `axisTickAmount`. Three decisions shape
 * it, and each has its case.
 *
 * D18, distinct ticks. ECharts spaces the ticks evenly between the bounds the chart fixes, often
 * half a thousand apart. A compact number cut to whole thousands printed `-2K -2K -1K … 1K 2K 2K`:
 * two ticks shared each outer label, so the scale seemed to stall. A tick prints the amount
 * exactly (`1.5K`, `12.5K`, `1.25M`), and a whole amount with no decimals (`2K`).
 *
 * D23, the locale's glyphs. The tick formats the SIGNED amount, so its minus comes out of the same
 * call as its digits. In Node's default locale that minus is a hyphen, like one written by hand,
 * so the Swedish case forces the call to a locale whose minus is U+2212 and pins the glyph as a
 * literal: the glyph is the subject. Every other literal here is pinned under a forced en-US.
 *
 * D25, the edges the chart fixes. The axis runs from `-axisBound` to `axisBound`, 5% beyond the
 * widest bar, and ECharts labels both edges with their raw value: exact formatting would print the
 * EUR fixture's edge as `2.462292K`. Decision B hides those two labels and keeps the bounds where
 * they are, so the bars stay as wide as before.
 */
describe('PerformanceChart amount axis ticks (S7b: D18, D23, D25)', () => {
    // The flag is module state shared by every case in the file. Whoever switches it on
    // switches it off, whatever the outcome of the case.
    afterEach(() => setPrivacyEnabled(false));

    /** `-0` as written. WHY: `String(-0)` is `'0'`, which would hide which zero a line of the diff is about. */
    const show = (value: number) => (Object.is(value, -0) ? '-0' : String(value));

    it('D18: prints every tick exactly, so no two ticks share a label, and a whole amount or a zero with no decimals', async () => {
        // WHY: D18. A compact number with a fixed number of decimals per magnitude (none from 100
        // up) printed `-2K -2K -1K -500 0 500 1K 2K 2K` for ticks 500 apart, `13K` for 12.5K and
        // `1M` for 1.25M: the axis repeated labels, and the ones it kept sat at the wrong values.
        // Catches any rounding of the compact number to a fixed number of decimals. Exactness
        // must not swing to the other extreme either: catches decimals padded onto a whole
        // amount, and a negative zero let through to the format call, which prints `-0`.
        expect(isPrivacyEnabled()).toBe(false);
        const axisTick = latestFullOption(await mountChart(EUR_PROPS)).xAxis.axisLabel.formatter;

        const read = inNumberFormatLocale('en-US', () => {
            const ticks = [-2_000, -1_500, -1_000, -500, 0, 500, 1_000, 1_500, 2_000].map((value) => axisTick(value));
            const singles = [12_500, 1_250_000, 2.5, 0.75, -0, 2_000].map((value) => `${show(value)} → ${axisTick(value)}`);
            return {ticks, distinct: new Set(ticks).size === ticks.length, singles};
        });
        // Guard: the ticks asked the default locale for a compact number, so the forced locale
        // reached them.
        expect(
            read.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
            'the ticks never asked the default locale for a compact number',
        ).toBe(true);
        expect(read.value).toEqual({
            ticks: ['-2K', '-1.5K', '-1K', '-500', '0', '500', '1K', '1.5K', '2K'],
            distinct: true,
            singles: ['12500 → 12.5K', '1250000 → 1.25M', '2.5 → 2.5', '0.75 → 0.75', '-0 → 0', '2000 → 2K'],
        });
    });

    it("D23: writes the locale's minus and decimal comma on the ticks, in the clear and masked: U+2212 in sv-SE", async () => {
        // WHY: D23 on the axis. A minus written by hand in front of the formatted absolute value
        // is a hyphen in every locale, and in Node's default locale the locale's own minus is a
        // hyphen too, so no host-locale case can tell the two apart. Forcing the default-locale
        // constructor the tick calls to a locale whose minus is U+2212 can: the digits turn
        // Swedish either way, the sign only if it comes out of the same call. Catches that
        // hand-written sign in the clear tick and in front of the mask, and a mask that swallows
        // the sign. The glyphs are literals on purpose: they are the subject.
        // Precondition, through the real constructor with an explicit locale: this Node has
        // Swedish locale data, and writes a compact Swedish amount the way the literals below
        // do. Without it the forced locale would fall back in silence, or the literals would be
        // about another ICU.
        expect(tickNumber(-1500, SWEDISH)).toBe('\u22121,5\u00a0tn');
        expect(isPrivacyEnabled()).toBe(false);
        const chart = await mountChart(EUR_PROPS);
        const clearTick = latestFullOption(chart).xAxis.axisLabel.formatter;
        const clear = inNumberFormatLocale(SWEDISH, () => [-1_500, 1_500, -2_000, 0].map((value) => clearTick(value)));

        const beforeOn = chart.setOptionCalls.length;
        setPrivacyEnabled(true);
        const maskedTick = (await fullOptionAfter(chart, beforeOn)).xAxis.axisLabel.formatter;
        const masked = inNumberFormatLocale(SWEDISH, () => [-1_500, 1_500, 0].map((value) => maskedTick(value)));

        // Guards: both reads asked the default locale for a compact number, so the forced locale
        // reached them.
        expect({
            clear: clear.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
            masked: masked.defaultLocaleCalls.some(({notation}) => notation === 'compact'),
        }).toEqual({clear: true, masked: true});
        expect({clear: clear.value, masked: masked.value}).toEqual({
            clear: ['\u22121,5\u00a0tn', '1,5\u00a0tn', '\u22122\u00a0tn', '0'],
            masked: [`\u2212${PRIVACY_PLACEHOLDER}`, PRIVACY_PLACEHOLDER, PRIVACY_PLACEHOLDER],
        });
    });

    it('D25: hides the labels of the two edges the chart fixes, and keeps the edges symmetric and where they were', async () => {
        // WHY: D25, decision B. ECharts labels the two bounds of the axis with their raw value,
        // and the exact ticks of D18 would print the EUR fixture's bound as `2.462292K`. Catches
        // either edge label left shown. Catches too the fix decision B turned down: a bound moved
        // to a round number so its label reads well. Rounding up shrinks every bar (the
        // component's own comment records a nice-number bound that did), and rounding one side
        // only makes the axis lopsided. So the bounds stay symmetric, 5% beyond the widest bar.
        expect(isPrivacyEnabled()).toBe(false);
        const {xAxis} = latestFullOption(await mountChart(EUR_PROPS));

        // The widest bar of the EUR fixture is the asset's three gains stacked.
        const positiveSide = EUR_POSITION.unrealized + EUR_POSITION.realized + EUR_POSITION.income;
        // Precondition: no other bar is wider (the asset's costs, its net, the other effect's net),
        // so the bound below is about this one.
        expect(positiveSide).toBeGreaterThan(Math.max(EUR_POSITION.feesTaxes, Math.abs(EUR_POSITION.net), Math.abs(EUR_EFFECT_NET)));
        expect(xAxis.max).toBeCloseTo(positiveSide * 1.05, 6);
        expect(xAxis.min).toBe(-(xAxis.max as number));
        expect({showMinLabel: xAxis.axisLabel.showMinLabel, showMaxLabel: xAxis.axisLabel.showMaxLabel}).toEqual({showMinLabel: false, showMaxLabel: false});
    });
});
