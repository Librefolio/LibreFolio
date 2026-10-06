// @vitest-environment jsdom
/**
 * AllocationHistoryChart.test.ts — what the history chart hands ECharts, read off the real component: the
 * series it stacks and the order it stacks them in, their colours, what it does to ECharts' series list
 * when that order changes, and the tooltip of a day.
 *
 * ## The subject: D15, then D375
 *
 * D15 of I (20_performanceCharts, round 4 §7) groups the type dimension by vehicle, as the pie does: K's
 * `assetTypeFamily`, never `primaryAssetType`, the content view. `ETF_STOCK` and `ETF_BOND` belong to ETF
 * and `CROWDFUND_REAL_ESTATE` to CROWDFUND, where by content they would sit with STOCK, BOND and
 * REAL_ESTATE.
 *
 * D375 (developer, 05/10/2026: «Una sola area per famiglia (ETF = somma di tutti), con i sottotipi solo nel
 * tooltip») turns that grouping into the data. The type dimension draws ONE series per family:
 *
 * - its `id` is the family key, upper-cased — the engine's synthetic `Liquidity` cash bucket is a family of
 *   its own, `LIQUIDITY` — and its `name` the family's display name (`assets.types.{FAMILY}`);
 * - on every date it holds the sum of the values its members have on that date;
 * - the families are stacked by summed average weight, heaviest first: the group order of
 *   `buildAllocationHierarchy`;
 * - each is drawn in `palette[rank]`, verbatim. No shade anywhere: no subtype series is left to shade, and
 *   the tooltip shows none either.
 *
 * The subtypes live in the tooltip only. It lists one entry per family, ranked by that day's value; more
 * than six families give the top five and «Remaining», today's rule. A family whose one member present that
 * day (value > 0.01) is its own pure key is a single row. Any other family is its row, the sum, followed by
 * its members present that day, indented: the generic (pure) member first, captioned with
 * `dashboard.allocationGeneric`, then the subtypes by value, each with its own type label. Family entries
 * carry `data-allocation-family="<FAMILY>"` and member rows `data-allocation-member="<RAW KEY>"`: the
 * observable these tests parse, in jsdom, for order and nesting.
 *
 * D375 also fixes the stacking order of a redraw, a defect verified on ECharts 6. The chart applies its
 * option with `replaceMerge: ['series']`, under which ECharts keeps every series whose `id` it already holds
 * at the index it had at the first draw: a series that appears later lands on top, and a re-rank never
 * re-stacks. So, on every dimension, when the ordered list of series ids differs from the last one applied,
 * the chart first clears the series — `setOption({series: []}, {replaceMerge: ['series']})` — and then
 * applies the new option. When the order holds, it does not clear.
 *
 * Sector and geography are otherwise untouched: one series per raw category, ranked by weight, coloured by
 * index, and today's tooltip.
 *
 * ## How the expectations are built
 *
 * Families, sums and ranks are counted in the test, from the fixture's weights and K's real
 * `assetTypeFamily`; the palette is read from the component by name (`$test/sourcePalettes`), never copied.
 * Every type fixture is chosen so that grouping by content would draw something else, and a barrier says
 * so: without it, the comparison could not tell the two resolvers apart. No order rests on a tie. The
 * shades D375 removes are the ones `buildAllocationHierarchy` hands the subtypes of the same weights —
 * what the chart drew before D375 — so "no shade" is checked against colours that really were drawn.
 *
 * Nothing translated is written down. A label is resolved from the shipped catalogue by its key
 * (`assets.types.*`, `dashboard.allocationGeneric`, `common.remaining`), with or without the type's emoji
 * in front; a tooltip value is read as a number, whatever its format; a series is read by its `id` and a
 * tooltip row by its data attribute.
 *
 * Sector and geography are pinned against today's chart: the same tooltip helpers (`buildTooltipHeader`,
 * `buildTooltipByThreshold`) fed with the series the chart handed ECharts.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer — jsdom has no canvas. It answers every call the chart and its
 *   helpers make on an instance and keeps every `setOption` payload with the options it came with, as in
 *   `AllocationPieChart.test.ts`. The options are what tell a clearing call (`replaceMerge`) from the full
 *   option that follows it.
 * - `$lib/api`: the chart's `onMount` loads country and sector reference data through it. The stand-in
 *   answers empty lists, as in `AllocationPanel.test.ts`, so jsdom sends no request.
 * - `getClientRects`, for the chart's own container only: jsdom lays nothing out, so no element has a
 *   client rect, and the chart draws only when its container has one (`isChartVisible`). Every other
 *   element keeps jsdom's answer.
 *
 * ## Why the imports are dynamic
 *
 * The chart imports K's `assetTypes.ts`, which reads the generated Zodios schemas (`$lib/api/generated`,
 * gitignored, written by `./dev.py api sync`) at module load. As in the pie's test, the modules are
 * imported after asserting the generated file exists, so a missing client is reported with the command
 * that fixes it — never skipped.
 *
 * @module components/dashboard/AllocationHistoryChart.test
 */
import {existsSync, readFileSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in. It answers what the chart calls on an instance (`attachChartReady` → `on`, the
 * resolution logic → `getWidth`, `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the zoom
 * listener → `off`/`on`, a resolution switch → `dispatchAction`, the teardown → `dispose`) and keeps every
 * `setOption` payload, so a test can read what the component decided to draw.
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
            // A plausible plot width. With a single date, every resolution draws the same values.
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

    return {chartInstances, echartsModule: {init: (dom: unknown) => createFakeChart(dom)}};
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
import {parseSourcePalette} from '$test/sourcePalettes';
import {_} from '$lib/i18n';
import {buildAllocationHierarchy} from '$lib/components/charts/allocationHierarchy';
import {buildTooltipByThreshold, buildTooltipHeader, buildTooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {getAssetTypeEmoji} from './allocationTypeEmoji';

// =============================================================================
// Fixtures
// =============================================================================

/**
 * The generated client and the chart's source, from the frontend root vitest runs in, as the pie's test
 * resolves its files. Not `new URL(…, import.meta.url)`: under jsdom the global `URL` is jsdom's, and
 * `fileURLToPath` refuses what it builds.
 */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');
const CHART_SOURCE = join(process.cwd(), 'src', 'lib', 'components', 'dashboard', 'AllocationHistoryChart.svelte');

/** The `data-testid` of the chart's container: the one element given a layout below. */
const CHART_CONTAINER_TESTID = 'allocation-history-chart';

/** The engine's cash bucket in `by_type`: Title Case, and not an `AssetType`. Its family is `LIQUIDITY`. */
const CASH_BUCKET = 'Liquidity';

/** A raw allocation key with its weight, in percent. */
type Weight = readonly [key: string, percent: number];

/** The chart's three dimensions, as the allocation panel passes them. */
type Dimension = 'type' | 'sector' | 'geo';

/** One date of the history and the weights it holds. A key it leaves out is absent that day, as the engine leaves it out. */
interface Day {
    date: string;
    weights: readonly Weight[];
}

/** The date of every one-day history, whose average weight — what the chart ranks by — is that day's weight. */
const ONE_DATE = '2025-06-30';

/** A history of one day. */
const oneDay = (weights: readonly Weight[], date: string = ONE_DATE): Day[] => [{date, weights}];

/**
 * D15's eight keys, all weights distinct, summing to 100, chosen so that the two groupings disagree on the
 * families, their sums and their order:
 *
 * - by vehicle, ETF holds ETF, ETF_STOCK and ETF_BOND (7 + 15 + 12 = 34) and leads, ahead of the cash (22),
 *   STOCK (21), CROWDFUND, which holds CROWDFUND and CROWDFUND_REAL_ESTATE (2 + 10 = 12), and BOND (11):
 *   five series;
 * - by content, STOCK holds STOCK and ETF_STOCK (36) and leads, BOND holds BOND and ETF_BOND (23), and
 *   CROWDFUND_REAL_ESTATE sits in REAL_ESTATE (10), apart from CROWDFUND (2), with ETF (7) between them:
 *   six series.
 *
 * No two families weigh the same under either grouping, so no order rests on a tie.
 */
const D15_WEIGHTS: readonly Weight[] = [
    ['STOCK', 21],
    ['ETF', 7],
    ['ETF_STOCK', 15],
    ['ETF_BOND', 12],
    ['BOND', 11],
    ['CROWDFUND', 2],
    ['CROWDFUND_REAL_ESTATE', 10],
    [CASH_BUCKET, 22],
];

/**
 * Three days of four keys, for the sums date by date. ETF is absent on the second day and ETF_STOCK on the
 * third, so a family series is right only if it adds what is there and counts nothing for what is not.
 * By vehicle: STOCK 50 / 40 / 45 (average 45), ETF 30 / 30 / 25 (28.3), LIQUIDITY 20 / 30 / 30 (26.7). By
 * content STOCK would hold ETF_STOCK too, and the cash would rank above ETF.
 */
const SUM_DAYS: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['ETF', 10],
            ['ETF_STOCK', 20],
            ['STOCK', 50],
            [CASH_BUCKET, 20],
        ],
    },
    {
        date: '2025-06-28',
        weights: [
            ['ETF_STOCK', 30],
            ['STOCK', 40],
            [CASH_BUCKET, 30],
        ],
    },
    {
        date: '2025-06-29',
        weights: [
            ['ETF', 25],
            ['STOCK', 45],
            [CASH_BUCKET, 30],
        ],
    },
];

/**
 * Two days for the tooltip, each summing to 100.
 *
 * Day 0 — ETF 40, STOCK 30, LIQUIDITY 20, CROWDFUND 10. ETF's generic member is the only one of its family
 * present, so ETF is one row, although ETF_STOCK and ETF_BOND hold weight on day 1. CROWDFUND holds its
 * generic member (2) and its subtype (8): the generic is listed first, though it weighs less. BOND is
 * absent.
 *
 * Day 1 — ETF 34, LIQUIDITY 22, STOCK 21, BOND 13, CROWDFUND 10. ETF holds its generic member (7) and two
 * subtypes (15, 12): the generic first again, then the subtypes by value. CROWDFUND's generic member is
 * absent, so its subtype is listed alone under the family row. LIQUIDITY ranks above STOCK that day, while
 * the series stack STOCK above LIQUIDITY (averages 25.5 and 21): the tooltip ranks by the day, not by the
 * stack.
 */
const TOOLTIP_DAYS: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['ETF', 40],
            ['STOCK', 30],
            [CASH_BUCKET, 20],
            ['CROWDFUND_REAL_ESTATE', 8],
            ['CROWDFUND', 2],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['ETF', 7],
            ['ETF_STOCK', 15],
            ['ETF_BOND', 12],
            [CASH_BUCKET, 22],
            ['STOCK', 21],
            ['BOND', 13],
            ['CROWDFUND_REAL_ESTATE', 10],
        ],
    },
];

/**
 * Two days on either side of the «Remaining» rule, each summing to 100.
 *
 * Day 0 — six families, all listed: ETF 20 (generic 8, ETF_BOND 12), STOCK 18, BOND 17, CRYPTO 16,
 * LIQUIDITY 15, CROWDFUND 14 (its subtype alone).
 *
 * Day 1 — eight families: ETF 17 (generic 5, ETF_STOCK 12), STOCK 16, BOND 15, CRYPTO 14 and LIQUIDITY 13
 * are listed; CROWDFUND 11 (subtype 9, generic 2), COMMODITY 8 and REAL_ESTATE 6 go to «Remaining», and
 * CROWDFUND's members with them.
 */
const CROWDED_DAYS: readonly Day[] = [
    {
        date: '2025-06-27',
        weights: [
            ['ETF', 8],
            ['ETF_BOND', 12],
            ['STOCK', 18],
            ['BOND', 17],
            ['CRYPTO', 16],
            [CASH_BUCKET, 15],
            ['CROWDFUND_REAL_ESTATE', 14],
        ],
    },
    {
        date: '2025-06-30',
        weights: [
            ['ETF', 5],
            ['ETF_STOCK', 12],
            ['STOCK', 16],
            ['BOND', 15],
            ['CRYPTO', 14],
            [CASH_BUCKET, 13],
            ['CROWDFUND_REAL_ESTATE', 9],
            ['CROWDFUND', 2],
            ['COMMODITY', 8],
            ['REAL_ESTATE', 6],
        ],
    },
];

/** The dates of the draws of a redraw case. WHY three: each draw is told apart by the date its points carry, never by its order. */
const FIRST_DATE = '2025-04-30';
const SECOND_DATE = '2025-05-31';
const THIRD_DATE = '2025-06-30';

/** A redraw: the weights of the first draw, then of the second, on one dimension. */
interface Redraw {
    title: string;
    dimension: Dimension;
    first: readonly Weight[];
    second: readonly Weight[];
}

/** A redraw whose second draw changes the order, and whose third keeps the second's. */
interface Restack extends Redraw {
    third: readonly Weight[];
}

/**
 * One case per kind of change — a swap, an arrival — across the three dimensions. On type the order is the
 * families': ETF 50, STOCK 40, LIQUIDITY 10 swap into STOCK 60, ETF 25, LIQUIDITY 15; and ETF arrives
 * through ETF_BOND alone, above STOCK and LIQUIDITY. Every arrival leads on purpose: ECharts would append it
 * on top of the stack, the place furthest from the bottom one it ranks for.
 */
const RESTACKS: readonly Restack[] = [
    {
        title: 'type, two families swap ranks',
        dimension: 'type',
        first: [
            ['ETF', 30],
            ['ETF_STOCK', 20],
            ['STOCK', 40],
            [CASH_BUCKET, 10],
        ],
        second: [
            ['ETF', 10],
            ['ETF_STOCK', 15],
            ['STOCK', 60],
            [CASH_BUCKET, 15],
        ],
        third: [
            ['ETF', 12],
            ['ETF_STOCK', 14],
            ['STOCK', 58],
            [CASH_BUCKET, 16],
        ],
    },
    {
        title: 'type, a family appears and leads',
        dimension: 'type',
        first: [
            ['STOCK', 60],
            [CASH_BUCKET, 40],
        ],
        second: [
            ['ETF_BOND', 45],
            ['STOCK', 35],
            [CASH_BUCKET, 20],
        ],
        third: [
            ['ETF_BOND', 44],
            ['STOCK', 36],
            [CASH_BUCKET, 20],
        ],
    },
    {
        title: 'sector, two sectors swap ranks',
        dimension: 'sector',
        first: [
            ['Technology', 60],
            ['Financials', 40],
        ],
        second: [
            ['Financials', 70],
            ['Technology', 30],
        ],
        third: [
            ['Financials', 65],
            ['Technology', 35],
        ],
    },
    {
        title: 'geography, a country appears and leads',
        dimension: 'geo',
        first: [
            ['USA', 70],
            ['ITA', 30],
        ],
        second: [
            ['DEU', 50],
            ['USA', 30],
            ['ITA', 20],
        ],
        third: [
            ['DEU', 48],
            ['USA', 32],
            ['ITA', 20],
        ],
    },
];

/** Redraws that move the values and keep the order, one per dimension. On type the raw keys keep their order too, so the case is about the same order before and after D375. */
const STEADY: readonly Redraw[] = [
    {
        title: 'type',
        dimension: 'type',
        first: [
            ['ETF', 30],
            ['ETF_STOCK', 20],
            ['STOCK', 40],
            [CASH_BUCKET, 10],
        ],
        second: [
            ['ETF', 28],
            ['ETF_STOCK', 24],
            ['STOCK', 38],
            [CASH_BUCKET, 10],
        ],
    },
    {
        title: 'sector',
        dimension: 'sector',
        first: [
            ['Technology', 60],
            ['Financials', 40],
        ],
        second: [
            ['Technology', 55],
            ['Financials', 45],
        ],
    },
    {
        title: 'geography',
        dimension: 'geo',
        first: [
            ['USA', 70],
            ['ITA', 30],
        ],
        second: [
            ['USA', 65],
            ['ITA', 35],
        ],
    },
];

/**
 * The two dimensions D375 leaves alone, each on one day with categories on both sides of the tooltip's 3%
 * threshold, so its «Remaining» row is drawn too. Sector keys are the backend's; geography keys are ISO 3
 * codes, which the reference store (empty here) would name.
 */
const UNTOUCHED: ReadonlyArray<{title: string; dimension: Dimension; weights: readonly Weight[]}> = [
    {
        title: 'sector',
        dimension: 'sector',
        weights: [
            ['Technology', 40],
            ['Financials', 30],
            ['Health Care', 25],
            ['Energy', 2.5],
            ['Utilities', 1.5],
            ['Real Estate', 1],
        ],
    },
    {
        title: 'geography',
        dimension: 'geo',
        weights: [
            ['USA', 55],
            ['ITA', 30],
            ['DEU', 12],
            ['FRA', 2],
            ['ESP', 1],
        ],
    },
];

// =============================================================================
// Mounting
// =============================================================================

type ChartComponent = typeof import('./AllocationHistoryChart.svelte').default;
type Taxonomy = typeof import('$lib/utils/assetTypes');

let AllocationHistoryChart: ChartComponent;
let K: Taxonomy;
/** `PALETTE_LIGHT` of the chart, read by name: jsdom's document carries no `dark` class (checked per mount). */
let palette: string[];
let restoreLayout: (() => void) | undefined;

/**
 * jsdom lays nothing out, so the chart's visibility guard would keep it from ever drawing. The chart's
 * own container gets the one client rect it has on screen; every other element keeps jsdom's answer.
 */
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
    palette = parseSourcePalette(readFileSync(CHART_SOURCE, 'utf8'), 'PALETTE_LIGHT', 'AllocationHistoryChart.svelte');
    restoreLayout = layOutChartContainer();
});

afterAll(() => {
    restoreLayout?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

/** One component of `by_type` (or `by_sector`, `by_country`) on one date, as `POST /allocation-history` returns it. */
interface AllocationComponent {
    name: string;
    value: string;
    amount: string;
}

/** The chart's `data` prop for `days`. The amounts are synthetic: the chart draws the weights. */
function historyOf(days: readonly Day[]): Array<{date: string; components: AllocationComponent[]}> {
    return days.map(({date, weights}) => ({date, components: weights.map(([name, percent]) => ({name, value: String(percent), amount: String(percent * 1000)}))}));
}

/** Mounts the chart on `days`, as the allocation panel does, and waits for its first full option. */
async function mountChart(days: readonly Day[], dimension: Dimension) {
    expect(document.documentElement.classList.contains('dark'), 'precondition: the light theme, whose palette the expectations read').toBe(false);
    const view = render(AllocationHistoryChart, {props: {data: historyOf(days), dimension, height: '400px'}});
    await waitFor(() => expect(lastFullOption(), 'the chart never handed ECharts a full option').toBeDefined(), {timeout: 5_000});
    expect(chartInstances, 'the chart did not create exactly one ECharts instance').toHaveLength(1);
    return view;
}

// =============================================================================
// Reading what the chart handed ECharts
// =============================================================================

/** A `setOption` call, as the recorder keeps it. */
interface RecordedCall {
    option: Record<string, unknown>;
    opts: unknown;
}

/** A series as the chart hands it to ECharts: the fields these tests read. */
interface DrawnSeries {
    id: string;
    name?: string;
    stack?: string;
    data?: unknown[];
    /** The series colour: legend, tooltip marker, and the value its line and area are drawn from. */
    itemStyle?: {color?: string};
}

/** A full option: what one draw hands ECharts. */
interface DrawnOption {
    series: DrawnSeries[];
    tooltip: {formatter: (params: unknown) => string};
}

function recordedCalls(): RecordedCall[] {
    expect(chartInstances, 'the chart did not create exactly one ECharts instance').toHaveLength(1);
    return chartInstances[0].setOptionCalls;
}

/** A full option carries series and the tooltip only a full build carries. WHY both: a clearing call carries an empty series list, and nothing else. */
function isFullOption(call: RecordedCall): boolean {
    const {series, tooltip} = call.option;
    return Array.isArray(series) && series.length > 0 && tooltip != null;
}

function lastFullOption(): DrawnOption | undefined {
    const call = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(isFullOption);
    return call?.option as unknown as DrawnOption | undefined;
}

function drawnOption(): DrawnOption {
    const option = lastFullOption();
    if (!option) throw new Error('the chart never handed ECharts a full option');
    return option;
}

/** The series of the last full option, with the premise every order assertion rests on: they are one stack, so their order is the stacking order. */
function drawnSeries(): DrawnSeries[] {
    const {series} = drawnOption();
    const stacks = [...new Set(series.map(({stack}) => stack))];
    expect(stacks, 'the series are not all on one stack, so their order is not the stacking order').toHaveLength(1);
    expect(stacks[0], 'the series are not stacked').toEqual(expect.any(String));
    return series;
}

/** The series ids of an option, in the order it hands them over. */
function idsOf(option: Record<string, unknown>): string[] {
    const series = option.series;
    return Array.isArray(series) ? (series as DrawnSeries[]).map(({id}) => id) : [];
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
// The expectations: families, labels, shades
// =============================================================================

/** The family K gives a raw key — upper-cased by K itself: `Liquidity` → `LIQUIDITY`. */
const familyOf = (key: string): string => K.assetTypeFamily(key);

/** A family of a history: its key, its sum on every date, and the average the stack ranks it by. */
interface Family {
    family: string;
    perDate: number[];
    average: number;
}

/**
 * The families of `days` under `resolve`, heaviest first by summed average weight. WHY counted here: the
 * order is the contract, so it is computed from the weights, never read from the helper that implements
 * it. Fails on a tie, which would make the order a matter of luck.
 */
function familiesOf(days: readonly Day[], resolve: (key: string) => string = familyOf): Family[] {
    const sums = new Map<string, number[]>();
    days.forEach(({weights}, dayIndex) => {
        for (const [key, percent] of weights) {
            const family = resolve(key).toUpperCase();
            const perDate = sums.get(family) ?? days.map(() => 0);
            perDate[dayIndex] += percent;
            sums.set(family, perDate);
        }
    });
    const ranked = [...sums].map(([family, perDate]) => ({family, perDate, average: perDate.reduce((total, value) => total + value, 0) / perDate.length})).sort((left, right) => right.average - left.average);
    ranked.forEach((entry, index) => {
        if (index > 0) expect(Math.abs(ranked[index - 1].average - entry.average), `fixture: ${ranked[index - 1].family} and ${entry.family} tie`).toBeGreaterThan(1e-9);
    });
    return ranked;
}

/** The raw keys of one day, heaviest first: the order of sector and geography. Fails on a tie. */
function rankedKeys(weights: readonly Weight[]): string[] {
    const ranked = [...weights].sort((left, right) => right[1] - left[1]);
    ranked.forEach(([key, percent], index) => {
        if (index > 0) expect(ranked[index - 1][1], `fixture: ${ranked[index - 1][0]} and ${key} tie`).not.toBe(percent);
    });
    return ranked.map(([key]) => key);
}

/** The order D375 stacks one day of `weights` in, on `dimension`. */
function expectedOrder(dimension: Dimension, weights: readonly Weight[]): string[] {
    return dimension === 'type' ? familiesOf(oneDay(weights)).map(({family}) => family) : rankedKeys(weights);
}

/** Every raw key's average weight over `days`, absent days counting zero: what the chart ranks a raw key by. */
function averageWeights(days: readonly Day[]): Weight[] {
    const totals = new Map<string, number>();
    for (const {weights} of days) for (const [key, percent] of weights) totals.set(key, (totals.get(key) ?? 0) + percent);
    return [...totals].map(([key, total]) => [key, total / days.length] as const);
}

/** `buildAllocationHierarchy` on `weights`, fed as the chart fed it before D375: heaviest first, grouped by family. */
function hierarchyOf(weights: readonly Weight[]) {
    const entries = [...weights].sort((left, right) => right[1] - left[1]).map(([key, percent]) => ({key, weight: percent, item: key}));
    return buildAllocationHierarchy(entries, {resolvePrimary: familyOf, palette});
}

/** The order of the hierarchy's groups: the contract's other word for "by summed weight". */
function hierarchyGroupOrder(weights: readonly Weight[]): string[] {
    return [...new Set(hierarchyOf(weights).map(({primary}) => primary))];
}

/**
 * The shades the hierarchy hands the subtypes of `weights`: what the chart drew before D375, and what may
 * now be drawn nowhere. A shade that happens to equal a palette entry is left out, since the palette is
 * still drawn.
 */
function shadesOf(weights: readonly Weight[]): string[] {
    const verbatim = new Set(palette.map((colour) => colour.toLowerCase()));
    return [
        ...new Set(
            hierarchyOf(weights)
                .filter(({depth}) => depth > 0)
                .map(({color}) => color.toLowerCase()),
        ),
    ].filter((shade) => !verbatim.has(shade));
}

/** The shades of `shades` found in `text`, as `#rrggbb` or as the `rgb(…)` a browser writes back. */
function shadesFoundIn(text: string, shades: readonly string[]): string[] {
    const haystack = text.toLowerCase();
    return shades.filter((shade) => {
        const [red, green, blue] = [1, 3, 5].map((at) => parseInt(shade.slice(at, at + 2), 16));
        return [shade, `rgb(${red}, ${green}, ${blue})`, `rgb(${red},${green},${blue})`].some((form) => haystack.includes(form));
    });
}

/** The label the catalogue gives a type key; fails when the key does not resolve. */
function typeLabel(type: string): string {
    const key = `assets.types.${type.toUpperCase()}`;
    const label = get(_)(key);
    expect(label, `${key} does not resolve: the catalogue is not loaded, or the key is gone`).not.toBe(key);
    return label;
}

/** A drawn name without the type's emoji in front of it, if it carries one: the label is the contract, the emoji the chart's to add. */
function withoutEmoji(name: string | undefined, type: string): string | undefined {
    const emoji = getAssetTypeEmoji(type);
    return emoji && name?.startsWith(`${emoji} `) ? name.slice(emoji.length + 1) : name;
}

/**
 * The captions a family's generic member may carry: `dashboard.allocationGeneric` around the family's
 * label, with or without its emoji in front — the pie passes the bare label.
 */
function genericCaptions(family: string): string[] {
    const label = typeLabel(family);
    const emoji = getAssetTypeEmoji(family);
    return [label, ...(emoji ? [`${emoji} ${label}`] : [])].map((type) => {
        const caption = get(_)('dashboard.allocationGeneric', {values: {type}});
        // Barrier: the sentence resolved, carries the family, and is not the bare family label — the
        // collision it exists to avoid.
        expect(caption, 'dashboard.allocationGeneric does not resolve').not.toBe('dashboard.allocationGeneric');
        expect(caption, `the generic caption does not name the family "${type}"`).toContain(type);
        expect(caption, 'the generic caption is the bare family label').not.toBe(type);
        return caption;
    });
}

/** The «Remaining» label, from the catalogue. */
function remainingLabel(): string {
    const label = get(_)('common.remaining');
    expect(label, 'common.remaining does not resolve').not.toBe('common.remaining');
    return label;
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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

/** Every number in a text, a decimal comma read as a point: a value is checked as a number, whatever its format. */
function numbersIn(text: string): number[] {
    return Array.from(text.matchAll(/\d+(?:[.,]\d+)?/g), (match) => Number(match[0].replace(',', '.')));
}

/** A row of the type tooltip as read: its text, and the numbers in it. */
interface ReadRow {
    text: string;
    numbers: number[];
}

/** A family entry as read: the family's own row — its member rows taken out — then each member row, keyed. */
interface ReadEntry extends ReadRow {
    family: string;
    members: Array<ReadRow & {key: string}>;
}

/** The text of a family entry, its member rows taken out. WHY: an entry may hold its members, and their labels would answer for the family's. */
function ownText(element: Element): string {
    const clone = element.cloneNode(true) as Element;
    for (const member of Array.from(clone.querySelectorAll('[data-allocation-member]'))) member.remove();
    return clone.textContent ?? '';
}

/**
 * The type tooltip, parsed in jsdom. Every element carrying `data-allocation-family` is an entry, every
 * one carrying `data-allocation-member` a member row, in document order — a member belongs to the entry
 * before it, whether the entry wraps its members or is a row followed by them. A member row that sits
 * inside another family's entry, or before any entry, is a nesting defect and fails here.
 */
function readTypeTooltip(html: string): {entries: ReadEntry[]; remaining: boolean} {
    const host = document.createElement('div');
    host.innerHTML = html;
    const entries: ReadEntry[] = [];
    const elementOf = new Map<ReadEntry, Element>();
    const misplaced: string[] = [];
    for (const element of Array.from(host.querySelectorAll('[data-allocation-family], [data-allocation-member]'))) {
        const member = element.getAttribute('data-allocation-member');
        if (member === null) {
            const text = ownText(element);
            const entry: ReadEntry = {family: element.getAttribute('data-allocation-family') ?? '', text, numbers: numbersIn(text), members: []};
            entries.push(entry);
            elementOf.set(entry, element);
            continue;
        }
        const owner = entries.at(-1);
        const enclosing = element.parentElement?.closest('[data-allocation-family]:not([data-allocation-member])');
        const tagged = element.getAttribute('data-allocation-family');
        if (owner === undefined || (enclosing != null && enclosing !== elementOf.get(owner)) || (tagged !== null && tagged !== owner.family)) {
            misplaced.push(member);
            continue;
        }
        const text = element.textContent ?? '';
        owner.members.push({key: member, text, numbers: numbersIn(text)});
    }
    expect(misplaced, 'member rows listed outside the entry of their family').toEqual([]);
    return {entries, remaining: (host.textContent ?? '').includes(remainingLabel())};
}

/** A family as the tooltip must list it on one day: its value, then its member rows — none when it is one row. */
interface ExpectedEntry {
    family: string;
    value: number;
    members: Array<{key: string; value: number}>;
}

/**
 * The tooltip of one day, by D375: the families present (value > 0.01), ranked by the day's value; a
 * family whose one present member is its pure key is one row; otherwise its present members, the generic
 * first, then the subtypes by value. Above six families, the top five, the rest in «Remaining».
 */
function expectedEntries(weights: readonly Weight[]): {shown: ExpectedEntry[]; remaining: ExpectedEntry[]} {
    const byFamily = new Map<string, Array<{key: string; value: number}>>();
    for (const [key, value] of weights) {
        if (!(value > 0.01)) continue;
        const family = familyOf(key);
        byFamily.set(family, [...(byFamily.get(family) ?? []), {key, value}]);
    }
    const entries = [...byFamily]
        .map(([family, members]) => {
            const generic = members.filter(({key}) => key.toUpperCase() === family);
            const subtypes = members.filter(({key}) => key.toUpperCase() !== family).sort((left, right) => right.value - left.value);
            return {family, value: members.reduce((total, {value}) => total + value, 0), members: subtypes.length === 0 ? [] : [...generic, ...subtypes]};
        })
        .sort((left, right) => right.value - left.value);
    entries.forEach((entry, index) => {
        if (index > 0) expect(entries[index - 1].value, `fixture: ${entries[index - 1].family} and ${entry.family} tie`).not.toBe(entry.value);
    });
    return entries.length > 6 ? {shown: entries.slice(0, 5), remaining: entries.slice(5)} : {shown: entries, remaining: []};
}

/**
 * What `readTypeTooltip` must read for one day: each family in its rank, its label and its sum in its own
 * row; each member in its place, the generic one captioned as such, a subtype under its own label, each
 * with its value; and «Remaining» exactly when families were left out.
 */
function expectedReading(weights: readonly Weight[]) {
    const {shown, remaining} = expectedEntries(weights);
    return {
        entries: shown.map(({family, value, members}) => ({
            family,
            text: expect.stringContaining(typeLabel(family)),
            numbers: expect.arrayContaining([expect.closeTo(value, 1)]),
            members: members.map(({key, value: memberValue}) => ({
                key,
                text: key.toUpperCase() === family ? expect.stringMatching(new RegExp(genericCaptions(family).map(escapeRegExp).join('|'))) : expect.stringContaining(typeLabel(key)),
                numbers: expect.arrayContaining([expect.closeTo(memberValue, 1)]),
            })),
        })),
        remaining: remaining.length > 0,
    };
}

// =============================================================================
// Redraws
// =============================================================================

/** `replaceMerge` of a call's options, as a list: ECharts takes a name or a list. */
function replaceMergeOf(opts: unknown): string[] {
    const raw = opts != null && typeof opts === 'object' ? (opts as {replaceMerge?: unknown}).replaceMerge : undefined;
    return Array.isArray(raw) ? raw.map(String) : typeof raw === 'string' ? [raw] : [];
}

/** D375's clearing call: an empty series list, replaced — `setOption({series: []}, {replaceMerge: ['series']})`. */
function isClearingCall(call: RecordedCall): boolean {
    const {series} = call.option;
    return Array.isArray(series) && series.length === 0 && replaceMergeOf(call.opts).includes('series');
}

/** The index of the first full option recorded from call `since` on whose points fall on `date`. */
function fullOptionIndexOn(date: string, since: number): number {
    return recordedCalls().findIndex((call, index) => index >= since && isFullOption(call) && (call.option.series as DrawnSeries[]).some(({data}) => (data ?? []).some((datum) => pointDate(datum) === date)));
}

/** Waits for the first full option on `date` recorded from call `since` on, and returns its index. WHY by date: it tells the redraw from any draw of the data before it. */
async function waitForFullOptionOn(date: string, since: number): Promise<number> {
    let found = -1;
    await waitFor(
        () => {
            found = fullOptionIndexOn(date, since);
            expect(found, `a full option drawn on ${date}`).toBeGreaterThanOrEqual(0);
        },
        {timeout: 5_000},
    );
    return found;
}

/** What a clearing call reads as below. */
const CLEARING_CALL = 'the clearing call: series [], replaceMerge series';

/** The last call before call `index`, back to call `since`, that touches the series list, as a sentence. WHY a sentence: a red names what came instead. */
function seriesCallBefore(index: number, since: number): string {
    const calls = recordedCalls();
    for (let at = index - 1; at >= since; at -= 1) {
        const call = calls[at];
        if (!Array.isArray(call.option.series)) continue;
        if (isClearingCall(call)) return CLEARING_CALL;
        return `a series call [${idsOf(call.option).join(', ')}] with replaceMerge [${replaceMergeOf(call.opts).join(', ')}]`;
    }
    return 'no series call since the redraw began';
}

// =============================================================================
// D375 — the type dimension draws one series per family
// =============================================================================

describe('AllocationHistoryChart — the type dimension draws one series per family (D375, by assetTypeFamily as D15 decided)', () => {
    it('draws one series per family, heaviest first: the family key as id, named after the family, in palette[rank] verbatim, with no shade anywhere', async () => {
        // WHY: D375, "one area per family". Catches a series left per raw type, a family keyed by one
        // of its members or by the cash bucket's Title Case, families ranked by their heaviest member
        // instead of their sum, a family named after a member, and a subtype shade left in the option.
        const byFamily = familiesOf(oneDay(D15_WEIGHTS));
        // Barriers: grouping by content would draw other series, so the comparison tells the two resolvers
        // apart; and the contract's two words for the order — summed weight, the hierarchy's group order —
        // agree on these weights.
        expect(
            byFamily.map(({family}) => family),
            'precondition: grouping by content would draw the same series',
        ).not.toEqual(familiesOf(oneDay(D15_WEIGHTS), K.primaryAssetType).map(({family}) => family));
        expect(
            byFamily.map(({family}) => family),
            'precondition: the summed weights rank the families as buildAllocationHierarchy orders its groups',
        ).toEqual(hierarchyGroupOrder(D15_WEIGHTS));
        const shades = shadesOf(D15_WEIGHTS);
        expect(shades, 'precondition: the hierarchy shades subtypes of these weights, so "no shade" can fail').not.toEqual([]);

        await mountChart(oneDay(D15_WEIGHTS), 'type');
        const drawn = drawnSeries();

        expect(
            drawn.map(({id, name, itemStyle}) => ({id, name: withoutEmoji(name, id), color: itemStyle?.color})),
            'not one series per family, keyed, named, ranked and coloured as D375 says',
        ).toEqual(byFamily.map(({family}, rank) => ({id: family, name: typeLabel(family), color: palette[rank]})));
        expect(shadesFoundIn(JSON.stringify(drawn), shades), 'a subtype shade is still in the option').toEqual([]);
    });

    it('sums the members into their family: ETF_STOCK and ETF_BOND into ETF, CROWDFUND_REAL_ESTATE into CROWDFUND — never into STOCK, BOND or a REAL_ESTATE series', async () => {
        // WHY: D15's barrier, kept under D375. The vehicle decides where a subtype's weight goes: an equity
        // ETF is an ETF, not a share. Catches the content resolver (`primaryAssetType`), under which STOCK
        // would hold 36, BOND 23 and a REAL_ESTATE series 10, and a family that drops a member.
        // Counted by hand: ETF 7 + 15 + 12, STOCK alone, CROWDFUND 2 + 10, BOND alone, no REAL_ESTATE.
        const SUMS = {ETF: 34, STOCK: 21, CROWDFUND: 12, BOND: 11, REAL_ESTATE: undefined};
        const pick = (sums: Record<string, number | null | undefined>) => ({ETF: sums.ETF, STOCK: sums.STOCK, CROWDFUND: sums.CROWDFUND, BOND: sums.BOND, REAL_ESTATE: sums.REAL_ESTATE});
        const sumsBy = (resolve: (key: string) => string) => Object.fromEntries(familiesOf(oneDay(D15_WEIGHTS), resolve).map(({family, perDate}) => [family, perDate[0]]));
        // Preconditions: the hand count is the vehicle's, and grouping by content would give other sums.
        expect(pick(sumsBy(familyOf)), 'the hand count is not what assetTypeFamily groups').toEqual(SUMS);
        expect(pick(sumsBy(K.primaryAssetType)), 'precondition: grouping by content would give the same sums').not.toEqual(SUMS);

        await mountChart(oneDay(D15_WEIGHTS), 'type');
        const drawn = Object.fromEntries(drawnSeries().map((series) => [series.id, pointValue(series.data?.[0])]));

        expect(pick(drawn), 'the families do not hold the sums of their members').toEqual(SUMS);
    });

    it('sums a family date by date, a member absent on a date counting nothing there', async () => {
        // WHY: D375, "data per date = the sum of its members' values that date". Catches a family series
        // that carries one member's line, a sum taken over the whole history instead of per date, and an
        // absent member that leaks another date's value.
        const byFamily = familiesOf(SUM_DAYS);
        expect(
            byFamily.map(({family}) => family),
            'precondition: grouping by content would stack these days the same way',
        ).not.toEqual(familiesOf(SUM_DAYS, K.primaryAssetType).map(({family}) => family));

        await mountChart(SUM_DAYS, 'type');
        const drawn = drawnSeries();

        expect(
            drawn.map(({id, data}) => ({id, values: (data ?? []).map(pointValue)})),
            'a family series does not hold, on every date, the sum of its members on that date',
        ).toEqual(byFamily.map(({family, perDate}) => ({id: family, values: perDate.map((value) => expect.closeTo(value, 9))})));
    });

    it('draws every asset type of the generated enum, and the cash bucket, inside the family assetTypeFamily gives it — each family on a palette slot of its own, verbatim', async () => {
        // WHY: D15 for every type there is, under D375. A new enum value lands in the family K gives it, and
        // no family wears another's colour. Catches a subtype drawn on its own, or in the family of its
        // content, and a family past the palette's slots.
        const keys = [...(K.ASSET_TYPES as readonly string[]), CASH_BUCKET];
        // Anti-vacuous: the enum was read, with the subtypes whose family is not their content.
        expect(keys).toEqual(expect.arrayContaining(['ETF_STOCK', 'ETF_BOND', 'ETF_REAL_ESTATE', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE']));
        // Powers of two, scaled to 100: every key weighs differently, and a family's sum names its members —
        // a sum of distinct powers of two belongs to one set of members only — so the value a series holds
        // proves which keys it holds, and no order rests on a tie.
        const total = 2 ** keys.length - 1;
        const weights: Weight[] = keys.map((key, index) => [key, (2 ** index * 100) / total]);
        const byFamily = familiesOf(oneDay(weights));
        expect(
            byFamily.map(({family}) => family),
            'precondition: grouping by content would stack the enum the same way',
        ).not.toEqual(familiesOf(oneDay(weights), K.primaryAssetType).map(({family}) => family));
        expect(byFamily.length, `${byFamily.length} families for ${palette.length} palette slots: one would wear the colour of another`).toBeLessThanOrEqual(palette.length);
        const shades = shadesOf(weights);
        expect(shades, 'precondition: the hierarchy shades subtypes of these weights, so "no shade" can fail').not.toEqual([]);

        await mountChart(oneDay(weights), 'type');
        const drawn = drawnSeries();

        expect(
            drawn.map(({id, data, itemStyle}) => ({id, sum: pointValue(data?.[0]), color: itemStyle?.color})),
            'not one series per family, holding its members, in palette[rank]',
        ).toEqual(byFamily.map(({family, perDate}, rank) => ({id: family, sum: expect.closeTo(perDate[0], 9), color: palette[rank]})));
        expect(new Set(drawn.map(({itemStyle}) => itemStyle?.color)).size, 'two families are drawn in the same colour').toBe(drawn.length);
        expect(shadesFoundIn(JSON.stringify(drawn), shades), 'a subtype shade is still in the option').toEqual([]);
    });
});

// =============================================================================
// D375 — the subtypes live in the tooltip, under their family
// =============================================================================

describe('AllocationHistoryChart — the type tooltip lists each family, then its members present that day (D375)', () => {
    it("ranks the families by the day's value and lists under each its members present that day, the generic one first; a family holding only its pure key that day is one row", async () => {
        // WHY: D375, "the subtypes only in the tooltip". The tooltip is now the one place a subtype shows.
        // Catches the families listed in the stack's order instead of the day's, a member listed outside
        // its family, the generic member listed by value, a subtype under the generic caption, a family
        // row that is not the sum, and a family split into a row plus its own pure key. No colour is
        // read but the shades: they may appear nowhere.
        await mountChart(TOOLTIP_DAYS, 'type');
        const option = drawnOption();
        // Barrier: on day 1 the tooltip's ranking (LIQUIDITY above STOCK) is not the stack's, so the case
        // tells the two apart.
        const stack = familiesOf(TOOLTIP_DAYS).map(({family}) => family);
        expect(stack.indexOf('STOCK'), 'precondition: STOCK is stacked above LIQUIDITY').toBeLessThan(stack.indexOf('LIQUIDITY'));
        const shades = shadesOf(averageWeights(TOOLTIP_DAYS));
        expect(shades, 'precondition: before D375 these rows wore shades, so "no shade" can fail').not.toEqual([]);

        const html = TOOLTIP_DAYS.map((_day, index) => tooltipOf(option, index));

        expect(Object.fromEntries(TOOLTIP_DAYS.map(({date}, index) => [date, readTypeTooltip(html[index])])), 'the tooltip does not list the families and their members as D375 says').toEqual(Object.fromEntries(TOOLTIP_DAYS.map(({date, weights}) => [date, expectedReading(weights)])));
        expect(
            html.flatMap((day) => shadesFoundIn(day, shades)),
            'a subtype shade is drawn in the tooltip',
        ).toEqual([]);
    });

    it('lists six families whole; from seven on, the top five with their members, then «Remaining» for the rest, their members included', async () => {
        // WHY: D375 keeps today's rule — more than six entries, the top five and «Remaining» — and applies
        // it to families. Catches the rule counted on raw keys (day 0 holds seven keys but six families),
        // a family left out under six, and the members of a family in «Remaining» listed anyway.
        await mountChart(CROWDED_DAYS, 'type');
        const option = drawnOption();
        // Preconditions: day 0 holds more than six raw keys in exactly six families; day 1 more than six families.
        expect(CROWDED_DAYS[0].weights.length, 'precondition: day 0 holds more than six raw keys').toBeGreaterThan(6);
        const [six, eight] = CROWDED_DAYS.map(({weights}) => expectedEntries(weights));
        expect({day0: [six.shown.length, six.remaining.length], day1: [eight.shown.length, eight.remaining.length]}, 'precondition: six families on day 0, five listed and three left on day 1').toEqual({day0: [6, 0], day1: [5, 3]});

        expect(Object.fromEntries(CROWDED_DAYS.map(({date}, index) => [date, readTypeTooltip(tooltipOf(option, index))])), 'the tooltip does not apply the «Remaining» rule to families').toEqual(Object.fromEntries(CROWDED_DAYS.map(({date, weights}) => [date, expectedReading(weights)])));
    });
});

// =============================================================================
// D375 — a redraw that changes the order clears the series first
// =============================================================================

describe('AllocationHistoryChart — a redraw that changes the order of the series clears them first (D375, every dimension)', () => {
    it.each(RESTACKS)('$title: clears the series, then draws the new order; a redraw in that same order does not clear again', async ({dimension, first, second, third}) => {
        // WHY: D375, verified on ECharts 6: under `replaceMerge: ['series']` a series keeps the index of its
        // first draw, so a re-rank never re-stacks and an arrival lands on top. Catches the missing clearing
        // call, a clearing call after the option instead of before it, and — on the third draw — an order
        // compared with the first draw forever instead of the last one applied.
        const orderOf = (weights: readonly Weight[]) => expectedOrder(dimension, weights);
        // Preconditions: the order changes on the second draw, and holds on the third.
        expect(orderOf(second), 'precondition: the second draw changes the order').not.toEqual(orderOf(first));
        expect(orderOf(third), 'precondition: the third draw keeps the order of the second').toEqual(orderOf(second));

        const view = await mountChart(oneDay(first, FIRST_DATE), dimension);

        const sinceSecond = recordedCalls().length;
        await view.rerender({data: historyOf(oneDay(second, SECOND_DATE))});
        const secondIndex = await waitForFullOptionOn(SECOND_DATE, sinceSecond);
        expect({before: seriesCallBefore(secondIndex, sinceSecond), order: idsOf(recordedCalls()[secondIndex].option)}, 'the redraw that changes the order').toEqual({before: CLEARING_CALL, order: orderOf(second)});

        const sinceThird = recordedCalls().length;
        await view.rerender({data: historyOf(oneDay(third, THIRD_DATE))});
        const thirdIndex = await waitForFullOptionOn(THIRD_DATE, sinceThird);
        expect({clearingCalls: recordedCalls().slice(sinceThird).filter(isClearingCall).length, order: idsOf(recordedCalls()[thirdIndex].option)}, 'the redraw that keeps it').toEqual({
            clearingCalls: 0,
            order: orderOf(third),
        });
    });

    it.each(STEADY)('$title: a redraw that keeps the order does not clear the series (green today and after D375)', async ({dimension, first, second}) => {
        // WHY: the clearing call costs ECharts a full rebuild of every series, and an animation from
        // nothing, so it belongs to a change of order only. Catches a chart that clears on every redraw.
        expect(expectedOrder(dimension, second), 'precondition: the redraw keeps the order').toEqual(expectedOrder(dimension, first));

        const view = await mountChart(oneDay(first, FIRST_DATE), dimension);
        const firstOrder = idsOf(drawnOption() as unknown as Record<string, unknown>);

        const since = recordedCalls().length;
        await view.rerender({data: historyOf(oneDay(second, SECOND_DATE))});
        const index = await waitForFullOptionOn(SECOND_DATE, since);

        expect({clearingCalls: recordedCalls().slice(since).filter(isClearingCall).length, order: idsOf(recordedCalls()[index].option)}).toEqual({clearingCalls: 0, order: firstOrder});
    });
});

// =============================================================================
// D375 — sector and geography draw as before
// =============================================================================

describe('AllocationHistoryChart — sector and geography draw as before (D375 leaves them alone)', () => {
    it.each(UNTOUCHED)('$title: one series per raw category, ranked by weight, in palette[index] (green today and after D375)', async ({dimension, weights}) => {
        // WHY: the family is a type notion. Catches the type rules leaking into the other dimensions: a
        // regrouping, a re-ranking, or a palette walked another way.
        await mountChart(oneDay(weights), dimension);

        expect(drawnSeries().map(({id, data, itemStyle}) => ({id, value: pointValue(data?.[0]), color: itemStyle?.color}))).toEqual(rankedKeys(weights).map((key, index) => ({id: key, value: weights.find(([name]) => name === key)?.[1], color: palette[index % palette.length]})));
    });

    it.each(UNTOUCHED)("$title: today's tooltip, every category under 3% grouped in «Remaining» (green today and after D375)", async ({dimension, weights}) => {
        // WHY: the family rows are the type tooltip's alone. Catches them, or the type's top-five rule,
        // reaching the sector or geography tooltip, and any change to its threshold rule.
        await mountChart(oneDay(weights), dimension);
        const option = drawnOption();
        const theme = buildTooltipTheme(false);
        const items = option.series.map(({name, data, itemStyle}) => ({name: name ?? '', value: pointValue(data?.[0]) ?? 0, color: itemStyle?.color ?? ''})).filter(({value}) => value > 0.01);
        // Barrier: the threshold splits the categories, so the «Remaining» row is in the expectation.
        expect(
            items.some(({value}) => value < 3),
            'precondition: a category under 3%',
        ).toBe(true);
        expect(
            items.some(({value}) => value >= 3),
            'precondition: a category over 3%',
        ).toBe(true);

        const html = tooltipOf(option, 0);

        expect(html).toBe(buildTooltipHeader(ONE_DATE, theme.mutedColor) + buildTooltipByThreshold(items, 3, theme, remainingLabel()));
        expect(html).not.toMatch(/data-allocation-(family|member)/);
    });
});
