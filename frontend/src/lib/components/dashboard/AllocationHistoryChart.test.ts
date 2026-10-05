// @vitest-environment jsdom
/**
 * AllocationHistoryChart.test.ts — what the history chart hands ECharts on the "by type" tab, read off
 * the real component: the order its series are stacked in, and the colour each one is drawn in.
 *
 * ## The subject: one argument, decision D15
 *
 * On the type dimension, `buildChartOption` orders and colours the series with
 * `buildAllocationHierarchy(…, {resolvePrimary, palette})`. Which `resolvePrimary` it passes is the whole
 * question here. D15 of I (20_performanceCharts, round 4 §7) aligns the history chart with the pie, by
 * vehicle: K's `assetTypeFamily` instead of `primaryAssetType`, the content view. `ETF_STOCK` and
 * `ETF_BOND` then belong to ETF and `CROWDFUND_REAL_ESTATE` to CROWDFUND, where by content they sat with
 * STOCK, BOND and REAL_ESTATE.
 *
 * The data are not aggregated: every raw type keeps a series of its own. The resolver decides only which
 * series are adjacent in the stack — every series is on one stack, so the series order is the stacking
 * order — and which palette entry a series is a shade of.
 *
 * ## How the expectation is built
 *
 * With the real `buildAllocationHierarchy`, K's real `assetTypeFamily`, and the palette read from the
 * component by name (`$test/sourcePalettes`), never a copy: what is pinned is which resolver the chart
 * passes, not a list of colours. The weights are chosen so that grouping by content would give another
 * order and other colours, and a barrier says so: without it, the comparison could not tell the two
 * resolvers apart.
 *
 * The history holds a single date, so the average weight the chart orders by is also today's weight.
 * D71 of I (which of the two should decide the colours) is still open, and these tests take no side.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer — jsdom has no canvas. It answers every call the chart and its
 *   helpers make on an instance and keeps every `setOption` payload, as in `AllocationPieChart.test.ts`.
 * - `$lib/api`: the chart's `onMount` loads country and sector reference data through it. The stand-in
 *   answers empty lists, as in `AllocationPanel.test.ts`, so jsdom sends no request.
 * - `getClientRects`, for the chart's own container only: jsdom lays nothing out, so no element has a
 *   client rect, and the chart draws only when its container has one (`isChartVisible`). Every other
 *   element keeps jsdom's answer.
 *
 * Nothing translated is asserted: a series is read by its `id`, which is the raw type key, and by its
 * colour.
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

import {render, setupI18n, waitFor} from '$test/component';
import {parseSourcePalette} from '$test/sourcePalettes';
import {buildAllocationHierarchy, type AllocationHierarchyResult} from '$lib/components/charts/allocationHierarchy';

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

/** The engine's cash bucket in `by_type`: Title Case, and not an `AssetType`. */
const CASH_BUCKET = 'Liquidity';

/** A raw `by_type` key with its weight, in percent. */
type Weight = readonly [key: string, percent: number];

/**
 * The eight keys of D15's case, all weights distinct, summing to 100, chosen so that the two groupings
 * disagree on both order and colour:
 *
 * - by vehicle, ETF holds ETF_STOCK, ETF_BOND and ETF (15 + 12 + 7 = 34) and leads the stack, ahead of the
 *   cash (22) and STOCK (21); CROWDFUND holds CROWDFUND_REAL_ESTATE and CROWDFUND (10 + 2 = 12), then BOND;
 * - by content, STOCK holds STOCK and ETF_STOCK (21 + 15 = 36) and leads, BOND holds ETF_BOND and BOND
 *   (23), and CROWDFUND_REAL_ESTATE sits in REAL_ESTATE, apart from CROWDFUND, with ETF between the two.
 *
 * No two groups weigh the same under either grouping, so no order rests on a tie.
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

/** One component of `by_type` on one date, as `POST /allocation-history` returns it. */
interface AllocationComponent {
    name: string;
    value: string;
    amount: string;
}

/** A series as the chart hands it to ECharts: the fields these tests read. */
interface DrawnSeries {
    /** The raw `by_type` key (`buildChartOption`: `id: name`). */
    id: string;
    stack?: string;
    /** The series colour: legend, tooltip marker, and the value its line and area are drawn from. */
    itemStyle?: {color?: string};
}

/** A series reduced to what D15 decides: its place in the stack (its index) and its colour. */
interface Styled {
    id: string;
    color: string | undefined;
}

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

/** A history of a single date, holding `weights`. */
function historyOf(weights: readonly Weight[]): Array<{date: string; components: AllocationComponent[]}> {
    return [{date: '2025-06-30', components: weights.map(([name, percent]) => ({name, value: String(percent), amount: String(percent * 1000)}))}];
}

/** What `buildAllocationHierarchy` makes of `weights` under `resolvePrimary`, fed as the chart feeds it: heaviest first. */
function hierarchyOf(weights: readonly Weight[], resolvePrimary: (key: string) => string): AllocationHierarchyResult<string>[] {
    const entries = [...weights].sort((left, right) => right[1] - left[1]).map(([key, percent]) => ({key, weight: percent, item: key}));
    return buildAllocationHierarchy(entries, {resolvePrimary, palette});
}

function styledOf(hierarchy: readonly AllocationHierarchyResult<string>[]): Styled[] {
    return hierarchy.map(({key, color}) => ({id: key, color}));
}

/** The series of the last full option the chart handed ECharts, or `undefined` before it drew. */
function lastDrawnSeries(): DrawnSeries[] | undefined {
    const build = [...(chartInstances[0]?.setOptionCalls ?? [])].reverse().find(({option}) => Array.isArray(option.series));
    return build?.option.series as DrawnSeries[] | undefined;
}

/** Mount the chart on the type tab, as the allocation panel does, and read the series it drew. */
async function drawSeries(weights: readonly Weight[]): Promise<DrawnSeries[]> {
    expect(document.documentElement.classList.contains('dark'), 'precondition: the light theme, whose palette the expectation reads').toBe(false);
    render(AllocationHistoryChart, {props: {data: historyOf(weights), dimension: 'type', height: '400px'}});
    await waitFor(() => expect(lastDrawnSeries(), 'the chart never handed ECharts a series').toBeDefined(), {timeout: 5_000});
    expect(chartInstances, 'the chart did not create exactly one ECharts instance').toHaveLength(1);

    const drawn = lastDrawnSeries() ?? [];
    // Barriers: the premises under every order assertion below.
    const stacks = [...new Set(drawn.map((series) => series.stack))];
    expect(stacks, 'the series are not all on one stack, so their order is not the stacking order').toHaveLength(1);
    expect(stacks[0], 'the series are not stacked').toEqual(expect.any(String));
    expect(drawn.map((series) => series.id).sort(), 'the chart does not draw exactly one series per raw type: D15 changes the grouping, never the data').toEqual(weights.map(([key]) => key).sort());
    return drawn;
}

function styledDrawn(drawn: readonly DrawnSeries[]): Styled[] {
    return drawn.map(({id, itemStyle}) => ({id, color: itemStyle?.color}));
}

// =============================================================================
// D15 — the history chart groups asset types by family
// =============================================================================

describe('AllocationHistoryChart — the type dimension groups asset types by family (D15, assetTypeFamily)', () => {
    it('stacks and colours its series exactly as buildAllocationHierarchy does with assetTypeFamily: one series per raw type, grouped by vehicle', async () => {
        const byFamily = hierarchyOf(D15_WEIGHTS, K.assetTypeFamily);
        const byContent = hierarchyOf(D15_WEIGHTS, K.primaryAssetType);
        // Barrier: the weights tell the two resolvers apart, on order and on colour, or the comparison below proves nothing.
        expect(
            byFamily.map(({key}) => key),
            'precondition: grouping by content would stack these weights in the same order',
        ).not.toEqual(byContent.map(({key}) => key));
        expect(Object.fromEntries(byFamily.map(({key, color}) => [key, color])), 'precondition: grouping by content would draw these weights in the same colours').not.toEqual(Object.fromEntries(byContent.map(({key, color}) => [key, color])));

        const drawn = await drawSeries(D15_WEIGHTS);

        expect(styledDrawn(drawn), 'the series are not stacked and coloured by family: the chart does not pass assetTypeFamily to buildAllocationHierarchy').toEqual(styledOf(byFamily));
    });

    it('stacks ETF_STOCK beside ETF and not beside STOCK, and CROWDFUND_REAL_ESTATE beside CROWDFUND', async () => {
        const ids = (await drawSeries(D15_WEIGHTS)).map((series) => series.id);
        const neighboursOf = (key: string): string[] => {
            const at = ids.indexOf(key);
            expect(at, `${key} is not drawn`).toBeGreaterThanOrEqual(0);
            return [ids[at - 1], ids[at + 1]].filter((id): id is string => id !== undefined);
        };

        expect(neighboursOf('ETF_STOCK'), 'the equity ETF is not stacked beside the generic ETF of its family').toContain('ETF');
        expect(neighboursOf('ETF_STOCK'), 'the equity ETF is still stacked beside the shares it holds, as grouping by content stacks it').not.toContain('STOCK');
        expect(neighboursOf('CROWDFUND_REAL_ESTATE'), 'real-estate crowdfunding is not stacked beside the crowdfunding of its family').toContain('CROWDFUND');
    });

    it('stacks every asset type of the generated enum, and the cash bucket, in the family assetTypeFamily gives it — each family on a palette slot of its own', async () => {
        const keys = [...(K.ASSET_TYPES as readonly string[]), CASH_BUCKET];
        // Anti-vacuous: the enum was read, with the subtypes whose family is not their content.
        expect(keys).toEqual(expect.arrayContaining(['ETF_STOCK', 'ETF_BOND', 'ETF_REAL_ESTATE', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE']));
        // Powers of two, scaled to 100: every key weighs differently, and so does every group — a sum of
        // distinct powers of two belongs to one set of members only — so no order below rests on a tie.
        const total = 2 ** keys.length - 1;
        const weights: Weight[] = keys.map((key, index) => [key, (2 ** index * 100) / total]);

        const byFamily = hierarchyOf(weights, K.assetTypeFamily);
        expect(styledOf(byFamily), 'precondition: grouping by content would stack and colour the enum the same way').not.toEqual(styledOf(hierarchyOf(weights, K.primaryAssetType)));

        const drawn = await drawSeries(weights);

        expect(styledDrawn(drawn), 'the series are not stacked and coloured by family: the chart does not pass assetTypeFamily to buildAllocationHierarchy').toEqual(styledOf(byFamily));

        // Within the palette: the first series of each family is its unshaded base, and no two families
        // share one. The equality above cannot see this — the helper wraps past the last slot, and its
        // expectation would wrap the same way.
        const baseColourOf = new Map<string, string | undefined>();
        for (const {id, itemStyle} of drawn) {
            const family = K.assetTypeFamily(id);
            if (!baseColourOf.has(family)) baseColourOf.set(family, itemStyle?.color);
        }
        expect(baseColourOf.size, `${baseColourOf.size} families for ${palette.length} palette slots: one would wear the colour of another`).toBeLessThanOrEqual(palette.length);
        expect(new Set(baseColourOf.values()).size, 'two families are drawn in the same palette colour').toBe(baseColourOf.size);
    });
});
