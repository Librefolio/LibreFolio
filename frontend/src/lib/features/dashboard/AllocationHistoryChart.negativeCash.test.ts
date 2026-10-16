// @vitest-environment jsdom
/**
 * AllocationHistoryChart.negativeCash.test.ts — decision 49 (workstream Y, lot Y10, backlog 54-1): the negative cash of
 * an overdrawn broker in the allocation history.
 *
 * ## The subject
 *
 * The backend sends the cash as a signed row named `Liquidity`, in the type and sector dimensions only — never in
 * geography (`daily_state.py`, step 4h) — and computes every share on the NET total (`build_allocation_history`,
 * `derived_views.py`). An overdrawn broker therefore yields a `Liquidity` share below zero, and positive shares that add
 * up to more than 100. Decision 49 (approved by the developer): the chart presents those numbers as they come — it
 * computes none of them — and
 *
 * - draws the negative cash BELOW zero: every stacked series declares `stackStrategy: 'samesign'`, the positives stacked
 *   upward from zero and the negatives downward. It is ECharts' own default (`processor/dataStack.js`); written out, the
 *   drawing no longer hangs on a library default;
 * - lets the y axis go past 100 % when the positive stack does, and below 0 for the cash; a history without negative
 *   cash keeps today's axis, 0 to 100;
 * - lists the negative `Liquidity` row in the tooltip — type and sector — with its signed share, never inside
 *   «Remaining».
 *
 * ## How the axis is read
 *
 * ECharts resolves an axis bound from the data extent of the series on it (`coord/scaleRawExtentInfo.js`): a number is
 * kept, a function is called with `{min, max}` of that extent, `'dataMin'`/`'dataMax'` are its own ends, and an absent
 * bound follows the data — across zero, `scale` being unset — before being rounded outward to a tick. The extent is the
 * one of the STACKED values, computed here as ECharts' `calculateStack` computes it, from the series the chart hands over
 * and the strategy each declares. An absent bound is read unrounded: rounding only moves it away from zero, so the
 * unrounded value is a safe witness of "reaches 120" and of "reaches −20"; on the guard's data, [0, 100], ECharts'
 * rounding lands on 0 and 100 themselves.
 *
 * ## What is red today
 *
 * - the axis: `yAxis.max` is the number 100, so a positive stack of 120 is cut at 100. Its lower half is green: `min`
 *   is absent, and ECharts' default follows the cash below zero — it is there against a fix that pins `min: 0`;
 * - the stack: no series sets `stackStrategy`;
 * - the tooltip: rows of value ≤ 0.01 are dropped (`buildFamilyTooltipRows` for the type, the `allItems` filter for the
 *   sector), so the negative cash is not listed at all; and `buildTooltipByThreshold` would put any value under 3 % — a
 *   negative one included — into «Remaining».
 *
 * The guard on the axis (no negative cash: 0 to 100) is green today, and must stay green.
 *
 * ## What is replaced, and what is not asserted
 *
 * The harness of `AllocationHistoryChart.test.ts`, repeated: `echarts` is a recorder that keeps every `setOption`
 * payload (jsdom has no canvas), `$lib/api` answers empty lists (the chart's reference data), and the chart's own
 * container is given a client rect (its visibility guard). The chart's module is imported after asserting the generated
 * client exists, so a missing `./dev.py api sync` is reported, never skipped.
 *
 * Nothing translated is written down: a label is resolved from the shipped catalogue by its key, a share is read as a
 * signed number whatever its format, a type entry by its `data-allocation-family` attribute (D375's markup).
 *
 * @module features/dashboard/AllocationHistoryChart.negativeCash.test
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in. It answers what the chart calls on an instance (`attachChartReady` → `on`, the resolution
 * logic → `getWidth`, `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the zoom listener → `off`/`on`, the
 * teardown → `dispose`) and keeps every `setOption` payload, so a test reads what the component decided to draw.
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
        getDom: () => unknown;
        getWidth: () => number;
        getHeight: () => number;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler?: () => void) => void;
        dispatchAction: (action: unknown) => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option, opts) {
                chart.setOptionCalls.push({option, opts});
            },
            getOption: () => ({}),
            getDom: () => dom,
            // A plausible plot width: with a few dates, every resolution draws day by day.
            getWidth: () => 800,
            getHeight: () => 400,
            on: () => {},
            off: () => {},
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
        echartsModule: {
            init: (dom: unknown) => createFakeChart(dom),
            // The time axis measures its labels with `echarts.format.getTextRect` (plan 52, C1), and `vi.mock` throws on an
            // export the factory leaves out: 7 px a character.
            format: {getTextRect: (text: string) => ({x: 0, y: 0, width: text.length * 7, height: 14})},
        },
    };
});

vi.mock('echarts', () => echartsModule);

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {get} from 'svelte/store';
import {render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {buildTooltipRow} from '$lib/components/charts/echartsTooltipHelpers';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {formatPercent} from '$lib/utils/core/formatPercent';

// =============================================================================
// Fixtures — the backend's numbers, as `POST /allocation-history` sends them
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationHistoryChart.test.ts`). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** The `data-testid` of the chart's container: the one element given a layout below. */
const CHART_CONTAINER_TESTID = 'allocation-history-chart';

/** The engine's cash bucket, in `by_type` and `by_sector` alike: Title Case. Its type family is `LIQUIDITY`. */
const CASH_BUCKET = 'Liquidity';

/** A raw allocation key with its share of the NET total, in percent: negative for an overdrawn cash. */
type Weight = readonly [key: string, percent: number];

/** The chart's three dimensions, as the allocation panel passes them. */
type Dimension = 'type' | 'sector' | 'geo';

/** One date of the history and the shares it holds. */
interface Day {
    date: string;
    weights: readonly Weight[];
}

/**
 * An overdrawn broker, by type. Day 1: positions 90, cash 10 — a funded day. Day 2: positions 120 — STOCK 70, and the
 * ETF family 50 (ETF 20, ETF_STOCK 30, summed by the chart into one series, D375) — and cash −20. The positive stack
 * tops out at 120, the cash reaches −20.
 */
const TYPE_OVERDRAWN: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['STOCK', 60],
            ['ETF', 30],
            [CASH_BUCKET, 10],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['STOCK', 70],
            ['ETF', 20],
            ['ETF_STOCK', 30],
            [CASH_BUCKET, -20],
        ],
    },
];

/** The same overdraft by sector: the cash is a sector bucket too. Positives up to 120, the cash down to −20. */
const SECTOR_OVERDRAWN: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['Technology', 60],
            ['Financials', 30],
            [CASH_BUCKET, 10],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['Technology', 70],
            ['Financials', 50],
            [CASH_BUCKET, -20],
        ],
    },
];

/** A funded portfolio by type: every day sums to 100, the cash positive. Integer shares, so no sum drifts off 100. */
const TYPE_FUNDED: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['STOCK', 60],
            ['ETF', 30],
            [CASH_BUCKET, 10],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['STOCK', 55],
            ['ETF', 25],
            ['ETF_BOND', 10],
            [CASH_BUCKET, 10],
        ],
    },
];

/** A funded portfolio by sector: every day sums to 100. */
const SECTOR_FUNDED: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['Technology', 60],
            ['Financials', 30],
            [CASH_BUCKET, 10],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['Technology', 55],
            ['Financials', 35],
            [CASH_BUCKET, 10],
        ],
    },
];

/** Geography never holds the cash: its shares are taken on the positions alone, so they sum to 100 even when overdrawn. */
const GEO_DAYS: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['USA', 60],
            ['ITA', 40],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['USA', 55],
            ['ITA', 45],
        ],
    },
];

/**
 * One overdrawn day by type, for the tooltip: seven positive families — ETF 31, STOCK 25, BOND 20, CRYPTO 15,
 * COMMODITY 12, REAL_ESTATE 10, CROWDFUND 7, adding up to 120 — and the cash at −20. Seven families are more than six,
 * so D375's rule leaves some to «Remaining»: the row the negative cash must stay out of. No two families tie.
 */
const TYPE_CROWDED_DAY: Day = {
    date: '2025-06-30',
    weights: [
        ['ETF', 31],
        ['STOCK', 25],
        ['BOND', 20],
        ['CRYPTO', 15],
        ['COMMODITY', 12],
        ['REAL_ESTATE', 10],
        ['CROWDFUND', 7],
        [CASH_BUCKET, -20],
    ],
};

/**
 * One overdrawn day by sector, for the tooltip: three sectors over the tooltip's 3 % threshold, three under it — the
 * «Remaining» row — and the cash at −20, itself "under 3" for a threshold that reads it as a number. The positives add
 * up to 120.
 */
const SECTOR_THRESHOLD_DAY: Day = {
    date: '2025-06-30',
    weights: [
        ['Technology', 50],
        ['Financials', 40],
        ['Health Care', 25],
        ['Energy', 2.5],
        ['Utilities', 1.5],
        ['Real Estate', 1],
        [CASH_BUCKET, -20],
    ],
};

// =============================================================================
// Mounting
// =============================================================================

type ChartComponent = typeof import('./AllocationHistoryChart.svelte').default;
type Taxonomy = typeof import('$lib/utils/assetTypes');

let AllocationHistoryChart: ChartComponent;
let K: Taxonomy;
let restoreLayout: (() => void) | undefined;

/** jsdom lays nothing out: the chart's own container gets the client rect it has on screen, every other element keeps jsdom's answer. */
function layOutChartContainer(): () => void {
    const jsdomGetClientRects = Element.prototype.getClientRects;
    const spy = vi.spyOn(Element.prototype, 'getClientRects').mockImplementation(function (this: Element): DOMRectList {
        if (this.getAttribute('data-testid') !== CHART_CONTAINER_TESTID) return jsdomGetClientRects.call(this);
        return [{x: 0, y: 0, top: 0, left: 0, width: 800, height: 400, right: 800, bottom: 400}] as unknown as DOMRectList;
    });
    return () => spy.mockRestore();
}

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the chart that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    K = await import('$lib/utils/assetTypes');
    AllocationHistoryChart = (await import('./AllocationHistoryChart.svelte')).default;
    restoreLayout = layOutChartContainer();
});

afterAll(() => {
    restoreLayout?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

/** The chart's `data` prop for `days`: the backend's decimal strings. The amounts are synthetic: the chart draws the shares. */
function historyOf(days: readonly Day[]): Array<{date: string; components: Array<{name: string; value: string; amount: string}>}> {
    return days.map(({date, weights}) => ({date, components: weights.map(([name, percent]) => ({name, value: String(percent), amount: String(percent * 100)}))}));
}

/** Mounts the chart on `days`, as the allocation panel does, and waits for its first full option. */
async function mountChart(days: readonly Day[], dimension: Dimension): Promise<void> {
    render(AllocationHistoryChart, {props: {data: historyOf(days), dimension, height: '400px'}});
    await waitFor(() => expect(lastFullOption(), 'the chart never handed ECharts a full option').toBeDefined(), {timeout: 5_000});
    expect(chartInstances, 'the chart did not create exactly one ECharts instance').toHaveLength(1);
}

// =============================================================================
// Reading what the chart handed ECharts
// =============================================================================

/** A series as the chart hands it to ECharts: the fields this file reads. */
interface DrawnSeries {
    id: string;
    name?: string;
    stack?: string;
    stackStrategy?: string;
    data?: unknown[];
    itemStyle?: {color?: string};
}

/** A full option: what one draw hands ECharts. */
interface DrawnOption {
    series: DrawnSeries[];
    tooltip: {formatter: (params: unknown) => string};
    yAxis?: unknown;
}

/** A full option carries series and the tooltip; a clearing call (D375) carries an empty series list and nothing else. */
function lastFullOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series) && option.series.length > 0 && option.tooltip != null);
    return call?.option as unknown as DrawnOption | undefined;
}

function drawnOption(): DrawnOption {
    const option = lastFullOption();
    if (!option) throw new Error('the chart never handed ECharts a full option');
    return option;
}

/** The series of the last full option, with the premise the stack reading rests on: they are all stacked, on one stack. */
function drawnSeries(): DrawnSeries[] {
    const {series} = drawnOption();
    const stacks = [...new Set(series.map(({stack}) => stack))];
    expect(stacks, 'the series are not all on one stack').toHaveLength(1);
    expect(stacks[0], 'the series are not stacked').toEqual(expect.any(String));
    return series;
}

/** The number a datum carries: `namedPoint` makes it `{name: date, value: [date, n]}`; a pair or a bare number read the same. */
function pointValue(datum: unknown): number | null {
    if (typeof datum === 'number') return datum;
    if (Array.isArray(datum)) return typeof datum[1] === 'number' ? datum[1] : null;
    if (datum == null || typeof datum !== 'object') return null;
    const value = (datum as {value?: unknown}).value;
    if (typeof value === 'number') return value;
    return Array.isArray(value) && typeof value[1] === 'number' ? value[1] : null;
}

/** The date a datum is drawn on. */
function pointDate(datum: unknown): string | null {
    if (Array.isArray(datum)) return typeof datum[0] === 'string' ? datum[0] : null;
    if (datum == null || typeof datum !== 'object') return null;
    const {name, value} = datum as {name?: unknown; value?: unknown};
    if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
    return typeof name === 'string' ? name : null;
}

// =============================================================================
// The y axis, as ECharts would resolve it
// =============================================================================

/** The low and high ends of a set of values. */
interface Extent {
    min: number;
    max: number;
}

/**
 * The extent ECharts gives the y axis: the min and the max of the STACKED values, computed as `calculateStack`
 * (`processor/dataStack.js`) computes them. Each point is added to the nearest point below it, in the same stack, that
 * the series' strategy lets it rest on — `samesign` when unset: a positive on a positive, a negative on a negative. The
 * points line up by index: every series of the chart carries every date, in the same order.
 */
function stackedExtent(series: readonly DrawnSeries[]): Extent {
    const results: number[][] = [];
    series.forEach((target, index) => {
        const strategy = target.stackStrategy ?? 'samesign';
        results[index] = (target.data ?? []).map((datum, dataIndex) => {
            let sum = pointValue(datum) ?? Number.NaN;
            if (Number.isNaN(sum) || target.stack == null) return sum;
            for (let below = index - 1; below >= 0; below -= 1) {
                if (series[below].stack !== target.stack) continue;
                const val = results[below][dataIndex];
                if (strategy === 'all' || (strategy === 'positive' && val > 0) || (strategy === 'negative' && val < 0) || (strategy === 'samesign' && sum >= 0 && val > 0) || (strategy === 'samesign' && sum <= 0 && val < 0)) {
                    sum += val;
                    break;
                }
            }
            return sum;
        });
    });
    const values = results.flat().filter((value) => !Number.isNaN(value));
    return {min: Math.min(...values), max: Math.max(...values)};
}

/**
 * The ends the axis must hold, from the shares the backend sent: the highest sum of positive shares on a day, and the
 * lowest sum of negative ones (0 when there is none). The oracle, counted from the fixture, never read from the chart.
 */
function stackEnds(days: readonly Day[]): Extent {
    const tops = days.map(({weights}) => weights.reduce((total, [, percent]) => total + Math.max(percent, 0), 0));
    const bottoms = days.map(({weights}) => weights.reduce((total, [, percent]) => total + Math.min(percent, 0), 0));
    return {min: Math.min(...bottoms), max: Math.max(...tops)};
}

/** The value axis as the chart hands it over: the fields that decide its ends. */
interface ValueAxis {
    min?: unknown;
    max?: unknown;
    scale?: boolean;
}

function yAxisOf(option: DrawnOption): ValueAxis {
    const axis = Array.isArray(option.yAxis) ? option.yAxis[0] : option.yAxis;
    if (axis == null || typeof axis !== 'object') throw new Error('the chart hands ECharts no y axis');
    return axis as ValueAxis;
}

/**
 * A bound of `axis` as ECharts resolves it on `extent` (`scaleRawExtentInfo.js`), before any rounding: a number as is,
 * a function called with the extent as ECharts calls it, `'dataMin'`/`'dataMax'` the extent's own ends; absent, the
 * data's own end — across zero unless `scale` is set — which ECharts then rounds outward, away from zero.
 */
function resolvedBound(axis: ValueAxis, side: 'min' | 'max', extent: Extent): number {
    const raw = axis[side];
    if (typeof raw === 'function') return Number((raw as (value: Extent) => unknown)({min: extent.min, max: extent.max}));
    if (typeof raw === 'number') return raw;
    if (raw === 'dataMin') return extent.min;
    if (raw === 'dataMax') return extent.max;
    if (raw == null) {
        if (axis.scale === true) return extent[side];
        return side === 'min' ? Math.min(extent.min, 0) : Math.max(extent.max, 0);
    }
    if (typeof raw === 'string' && raw.trim() !== '' && Number.isFinite(Number(raw))) return Number(raw);
    throw new Error(`y axis ${side}: ${String(raw)} is not a bound this test knows how ECharts resolves`);
}

/** A bound as a failure message names it. */
function describeBound(raw: unknown): string {
    if (typeof raw === 'function') return `a function: ${String(raw)}`;
    return raw === undefined ? 'absent' : JSON.stringify(raw);
}

// =============================================================================
// The tooltip
// =============================================================================

/** What ECharts hands an axis-trigger formatter on a hover: one entry per series, on one date. */
function axisParams(option: DrawnOption, dataIndex: number): unknown[] {
    return option.series.map((series, seriesIndex) => {
        const datum = series.data?.[dataIndex];
        const date = pointDate(datum) ?? '';
        return {
            componentType: 'series',
            componentSubType: 'line',
            seriesType: 'line',
            seriesIndex,
            seriesId: series.id,
            seriesName: series.name,
            dataIndex,
            data: datum,
            value: datum != null && typeof datum === 'object' ? (datum as {value?: unknown}).value : datum,
            color: series.itemStyle?.color,
            axisDim: 'x',
            axisIndex: 0,
            axisType: 'xAxis.time',
            axisValue: Date.parse(`${date}T00:00:00Z`),
            axisValueLabel: date,
        };
    });
}

function tooltipOf(option: DrawnOption, dataIndex: number): string {
    return option.tooltip.formatter(axisParams(option, dataIndex));
}

/** The signed number in a text, whatever its format: a decimal comma read as a point, a typographic minus as a minus, bidi marks ignored. */
function signedNumberIn(text: string): number | null {
    const match = /([-\u2212])?\s*(\d+(?:[.,]\d+)?)/u.exec(text.replace(/\p{Cf}/gu, ''));
    if (!match) return null;
    const magnitude = Number(match[2].replace(',', '.'));
    return match[1] ? -magnitude : magnitude;
}

/** A value row of a tooltip, as `buildTooltipRow` writes it — a `<div>` holding the label `<span>` and the value `<b>` — with where it sits. */
interface ReadRow {
    label: string;
    value: number | null;
    /** The type family entry the row sits in (`data-allocation-family`), if any. */
    family: string | null;
    /** The member row it is (`data-allocation-member`), if any. */
    member: string | null;
}

/** Every value row of a tooltip, in document order. */
function readRows(html: string): ReadRow[] {
    const host = document.createElement('div');
    host.innerHTML = html;
    const rows: ReadRow[] = [];
    for (const element of Array.from(host.querySelectorAll('div'))) {
        const children = Array.from(element.children);
        const label = children.find((child) => child.tagName === 'SPAN');
        const value = children.find((child) => child.tagName === 'B');
        if (!label || !value) continue;
        rows.push({
            label: (label.textContent ?? '').trim(),
            value: signedNumberIn(value.textContent ?? ''),
            family: element.closest('[data-allocation-family]')?.getAttribute('data-allocation-family') ?? null,
            member: element.closest('[data-allocation-member]')?.getAttribute('data-allocation-member') ?? null,
        });
    }
    return rows;
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** A row label that is `text`, with or without the category's emoji in front: the label is the contract, the emoji the chart's to add. */
function labelled(text: string): RegExp {
    return new RegExp(`^(?:[^\\p{L}\\s]+\\s+)?${escapeRegExp(text)}$`, 'u');
}

/** A label from the shipped catalogue; fails when the key does not resolve. */
function catalogueLabel(key: string): string {
    const label = get(_)(key);
    expect(label, `${key} does not resolve: the catalogue is not loaded, or the key is gone`).not.toBe(key);
    return label;
}

/** The label of a type family, as the chart reads it: `assets.types.{FAMILY}`. */
const typeLabel = (family: string): string => catalogueLabel(`assets.types.${family.toUpperCase()}`);

/** The label of a sector key, as the chart reads it: `sectors.{key without spaces}`. */
const sectorLabel = (key: string): string => catalogueLabel(`sectors.${K.sectorI18nKey(key)}`);

/** How many categories a «Remaining» row stands for — `common.remaining` and its count — or null when `label` is not one. */
function remainingCount(label: string): number | null {
    const match = new RegExp(`^${escapeRegExp(catalogueLabel('common.remaining'))} \\((\\d+)\\)$`).exec(label);
    return match ? Number(match[1]) : null;
}

const sumOf = (values: readonly number[]): number => values.reduce((total, value) => total + value, 0);

/**
 * Positive control of the reading, before a red is blamed on the chart: the cash series is drawn at −20 under the name
 * the chart gives it, that name is one the label matcher accepts, and a negative row written by the product's own row
 * builder — inside a `<div data-allocation-family>` for the type — reads back as that label and −20. So an absent row
 * is the chart's omission, and a fixed chart cannot be failed by the reader.
 */
function expectCashReadable(seriesId: string, label: RegExp, family: string | null): void {
    const cash = drawnOption().series.find(({id}) => id === seriesId);
    expect(pointValue(cash?.data?.[0]), `barrier: the ${seriesId} series is drawn at −20`).toBe(-20);
    expect(cash?.name, `control: the label matcher accepts the chart's own name for ${seriesId}`).toMatch(label);
    const row = buildTooltipRow(escapeHtml(cash?.name ?? ''), formatPercent(-20, {digits: 1, signed: false}), '#000000');
    expect(readRows(family === null ? row : `<div data-allocation-family="${family}">${row}</div>`), 'control: the reader reads a negative row as the product writes one').toEqual([{label: cash?.name, value: -20, family, member: null}]);
}

// =============================================================================
// Decision 49 — the y axis holds the whole stack
// =============================================================================

const OVERDRAWN_CASES = [
    {title: 'type', dimension: 'type' as Dimension, days: TYPE_OVERDRAWN},
    {title: 'sector', dimension: 'sector' as Dimension, days: SECTOR_OVERDRAWN},
];

const FUNDED_CASES = [
    {title: 'type', dimension: 'type' as Dimension, days: TYPE_FUNDED},
    {title: 'sector', dimension: 'sector' as Dimension, days: SECTOR_FUNDED},
];

describe('AllocationHistoryChart — the y axis of an overdrawn portfolio (decision 49)', () => {
    it.each(OVERDRAWN_CASES)('$title: the axis reaches the top of the positive stack (120 %) and the bottom of the negative cash (−20 %)', async ({dimension, days}) => {
        // CONTRACT: decision 49 — the shares come on the net total, so the positive stack tops out above 100 and the
        // cash sits below zero: the axis holds both, whatever form its bounds take. RED TODAY: `yAxis.max` is the
        // number 100 (`buildChartOption`), so everything above 100 is cut off. The `min` half is green today — absent,
        // ECharts follows the data below zero — and catches a fix that pins `min: 0`.
        const ends = stackEnds(days);
        expect(ends, 'fixture: the positives add up to 120 on the overdrawn day, the cash is −20').toEqual({min: -20, max: 120});

        await mountChart(days, dimension);
        const extent = stackedExtent(drawnSeries());
        // Barrier: the stacked data ECharts computes the axis from reach exactly those ends — the cash reached the
        // chart negative, the positives whole — so the axis is judged against the data it must hold.
        expect(extent, 'the extent of the stacked series the chart hands over').toEqual(ends);
        const axis = yAxisOf(drawnOption());

        expect(resolvedBound(axis, 'max', extent), `the y axis max (${describeBound(axis.max)}) ends below the top of the positive stack`).toBeGreaterThanOrEqual(ends.max);
        expect(resolvedBound(axis, 'min', extent), `the y axis min (${describeBound(axis.min)}) starts above the bottom of the negative cash`).toBeLessThanOrEqual(ends.min);
    });

    it.each(FUNDED_CASES)('$title, no negative cash: the axis still runs from 0 to 100 (green today, must stay green)', async ({dimension, days}) => {
        // CONTRACT: decision 49 changes the axis only when the data needs it — a funded portfolio, every day summing to
        // 100, keeps today's 0 to 100. Catches a fix that lets the axis float on every portfolio (a function that pads,
        // a `min` pinned below zero). GREEN TODAY: `max: 100`, `min` absent.
        expect(stackEnds(days), 'fixture: every day sums to 100, no negative share').toEqual({min: 0, max: 100});

        await mountChart(days, dimension);
        const extent = stackedExtent(drawnSeries());
        expect(extent.max, 'barrier: the stacked series top out at 100').toBe(100);
        const axis = yAxisOf(drawnOption());

        expect({min: resolvedBound(axis, 'min', extent), max: resolvedBound(axis, 'max', extent)}, `the y axis (min ${describeBound(axis.min)}, max ${describeBound(axis.max)})`).toEqual({min: 0, max: 100});
    });
});

// =============================================================================
// Decision 49 — the stack says how it stacks
// =============================================================================

const STACKED_CASES = [
    {title: 'type, overdrawn', dimension: 'type' as Dimension, days: TYPE_OVERDRAWN, negative: true},
    {title: 'sector, overdrawn', dimension: 'sector' as Dimension, days: SECTOR_OVERDRAWN, negative: true},
    {title: 'geography, which never holds the cash', dimension: 'geo' as Dimension, days: GEO_DAYS, negative: false},
];

describe('AllocationHistoryChart — every stacked series declares its stack strategy (decision 49)', () => {
    it.each(STACKED_CASES)("$title: every series sets stackStrategy 'samesign'", async ({dimension, days, negative}) => {
        // CONTRACT: decision 49 — the positives stack upward from zero and the negative cash downward from it, on every
        // dimension, by declaration rather than by ECharts' default. RED TODAY: no series sets `stackStrategy`.
        await mountChart(days, dimension);
        const series = drawnSeries();
        // Barrier: on the overdrawn dimensions a series really carries a negative point, the case the strategy decides.
        expect(
            series.some(({data}) => (data ?? []).some((datum) => (pointValue(datum) ?? 0) < 0)),
            'a series carries a negative point',
        ).toBe(negative);

        expect(series.map(({id, stackStrategy}) => `${id}: ${String(stackStrategy)}`)).toEqual(series.map(({id}) => `${id}: samesign`));
    });
});

// =============================================================================
// Decision 49 — the tooltip lists the negative cash on its own row
// =============================================================================

describe('AllocationHistoryChart — the tooltip lists the negative cash on its own row, never in «Remaining» (decision 49)', () => {
    it('type: a LIQUIDITY entry with its negative share, and «Remaining» holding the positive families left out, and nothing else', async () => {
        // CONTRACT: decision 49 — the overdraft is shown where the day is read: the LIQUIDITY family entry (D375's
        // `data-allocation-family` markup), its catalogue label and its signed share. D375's top-five rule still holds
        // for the positives, and «Remaining» sums exactly the positive families not listed: never the cash. RED TODAY:
        // `buildFamilyTooltipRows` keeps only members and families above 0.01, so LIQUIDITY is not listed at all — and
        // with that filter lifted it would rank last and fall into «Remaining».
        const byFamily = new Map<string, number>();
        for (const [key, percent] of TYPE_CROWDED_DAY.weights) byFamily.set(K.assetTypeFamily(key), (byFamily.get(K.assetTypeFamily(key)) ?? 0) + percent);
        const positives = [...byFamily].filter(([, value]) => value > 0);
        expect({families: positives.length, total: sumOf(positives.map(([, value]) => value)), cash: byFamily.get('LIQUIDITY')}, 'fixture: seven positive families adding up to 120, the cash at −20').toEqual({families: 7, total: 120, cash: -20});

        await mountChart([TYPE_CROWDED_DAY], 'type');
        expectCashReadable('LIQUIDITY', labelled(typeLabel('LIQUIDITY')), 'LIQUIDITY');
        const rows = readRows(tooltipOf(drawnOption(), 0));
        const familyRows = rows.filter(({family, member}) => family !== null && member === null);
        const listed = new Set(familyRows.map(({family}) => family));
        const leftOut = positives.filter(([family]) => !listed.has(family));
        // Barrier: D375's rule is unchanged — seven positive families are more than six, so some are left to «Remaining».
        expect(leftOut.length, 'positive families left to «Remaining»').toBeGreaterThan(0);

        expect({
            cash: familyRows.filter(({family}) => family === 'LIQUIDITY').map(({label, value}) => ({label, value})),
            remaining: rows.filter(({family, label}) => family === null && remainingCount(label) !== null).map(({label, value}) => ({count: remainingCount(label), value})),
        }).toEqual({
            cash: [{label: expect.stringMatching(labelled(typeLabel('LIQUIDITY'))), value: expect.closeTo(-20, 1)}],
            remaining: [{count: leftOut.length, value: expect.closeTo(sumOf(leftOut.map(([, value]) => value)), 1)}],
        });
    });

    it('sector: a Liquidity row with its negative share, and «Remaining» holding the positive sectors under the threshold, and nothing else', async () => {
        // CONTRACT: decision 49 — the sector tooltip lists the cash too: a row labelled `sectors.Liquidity` with its
        // signed share. The 3 % threshold still groups the small positive sectors, and «Remaining» sums exactly the
        // positive sectors not listed: never the cash. RED TODAY: rows of value ≤ 0.01 are filtered out before
        // `buildTooltipByThreshold`, so the cash is not listed — and that helper puts every value under 3, a negative
        // one included, into «Remaining».
        const positives = SECTOR_THRESHOLD_DAY.weights.filter(([, percent]) => percent > 0);
        expect({total: sumOf(positives.map(([, percent]) => percent)), cash: SECTOR_THRESHOLD_DAY.weights.find(([key]) => key === CASH_BUCKET)?.[1]}, 'fixture: the positives add up to 120, the cash is −20').toEqual({total: 120, cash: -20});

        await mountChart([SECTOR_THRESHOLD_DAY], 'sector');
        expectCashReadable(CASH_BUCKET, labelled(sectorLabel(CASH_BUCKET)), null);
        const rows = readRows(tooltipOf(drawnOption(), 0));
        const rowsOf = (key: string) => rows.filter(({label}) => labelled(sectorLabel(key)).test(label));
        const leftOut = positives.filter(([key]) => rowsOf(key).length === 0);
        // Barrier: the threshold rule is unchanged — the three sectors under 3 % are not listed on their own.
        expect(leftOut.length, 'positive sectors left to «Remaining»').toBeGreaterThan(0);

        expect({
            cash: rowsOf(CASH_BUCKET).map(({value}) => value),
            remaining: rows.filter(({label}) => remainingCount(label) !== null).map(({label, value}) => ({count: remainingCount(label), value})),
        }).toEqual({
            cash: [expect.closeTo(-20, 1)],
            remaining: [{count: leftOut.length, value: expect.closeTo(sumOf(leftOut.map(([, percent]) => percent)), 1)}],
        });
    });
});
