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
 * - each is drawn in its own colour, `categoryColor('type', family)` — GR1 of the designer's round 2
 *   (D-T17): by key, never by rank, the very colour the pie gives the family. No shade anywhere: no
 *   subtype series is left to shade, and the tooltip shows none either.
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
 * Sector and geography are otherwise untouched by D375: one series per raw category, ranked by weight,
 * and today's tooltip. Their colours follow GR1 and GR5: a sector wears its own,
 * `categoryColor('sector', key)`; a country has none, so it takes the sector sequence by its rank
 * among the classified countries (`sequenceColor` over `KEYLESS_SEQUENCE`), one GR4 shade further at
 * each round past the fourteenth, while the unclassified one (`Unknown`, `Other`) keeps the Unknown
 * grey and takes no rank. A chart-colour change (contract C4, `notifyChartColorsChange`) redraws the
 * whole option, reading the roles again.
 *
 * ## How the expectations are built
 *
 * Families, sums and ranks are counted in the test, from the fixture's weights and K's real
 * `assetTypeFamily`; the colours are those of the theme's own functions — `categoryColor`,
 * `sequenceColor`, `familyShade`, the card read through `chartRoles` — never copied hex values, which
 * the theme's tests pin. Most blocks draw in the light theme, jsdom's default; the ones that read both
 * themes mount the chart under the `dark` class of <html> as well.
 * Every type fixture is chosen so that grouping by content would draw something else, and a barrier says
 * so: without it, the comparison could not tell the two resolvers apart. No order rests on a tie. The
 * shades the history must not draw are the ones the pie gives the subtypes of the same weights —
 * `buildAllocationHierarchy` with `familyShade`, wired as the pie wires it — so "no shade" is checked
 * against colours a chart really draws.
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
 * @module features/dashboard/AllocationHistoryChart.test
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in. It answers what the chart calls on an instance (`attachChartReady` → `on`, the
 * resolution logic → `getWidth`, `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the zoom
 * listener → `off`/`on`, a resolution switch → `dispatchAction`, the teardown → `dispose`) and keeps every
 * `setOption` payload, so a test can read what the component decided to draw.
 */
const {chartInstances, echartsModule, measuredFonts, FAKE_TEXT_PX_PER_CHAR} = vi.hoisted(() => {
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
    /** Width of one character under the fake text measure, in px. */
    const FAKE_TEXT_PX_PER_CHAR = 7;
    /** Every font `format.getTextRect` was asked in, in call order. */
    const measuredFonts: string[] = [];

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

    return {
        chartInstances,
        measuredFonts,
        FAKE_TEXT_PX_PER_CHAR,
        echartsModule: {
            init: (dom: unknown) => createFakeChart(dom),
            // WHY (plan 52, C1): the time axis now measures its labels with `echarts.format.getTextRect` to size its right
            // inset, and `vi.mock` throws on an export the factory leaves out. FAKE_TEXT_PX_PER_CHAR px a character, every
            // font it is asked in kept in `measuredFonts`.
            format: {
                getTextRect(text: string, font: string) {
                    measuredFonts.push(font);
                    return {x: 0, y: 0, width: text.length * FAKE_TEXT_PX_PER_CHAR, height: 14};
                },
            },
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

import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';
import {render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {debug} from '$lib/debug';
import {categoryColor, KEYLESS_SEQUENCE, sequenceColor} from '$lib/theme/chartCategories';
import {familyShade, shadePoles} from '$lib/theme/chartShades';
import {chartRoles, setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {buildAllocationHierarchy} from '$lib/components/charts/allocationHierarchy';
import {buildTooltipByThreshold, buildTooltipHeader, buildTooltipTheme} from '$lib/components/charts/echartsTooltipHelpers';
import {timeAxisGridRight} from '$lib/components/charts/responsiveXAxis';
import {getAssetTypeEmoji} from './allocationTypeEmoji';

// =============================================================================
// Fixtures
// =============================================================================

/**
 * The generated client, from the frontend root vitest runs in, as the pie's test resolves its files. Not
 * `new URL(…, import.meta.url)`: under jsdom the global `URL` is jsdom's, and `fileURLToPath` refuses what it builds.
 */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

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
let restoreLayout: (() => void) | undefined;

/** The colour a family is drawn in (GR1): its key's, through the one read point of the category colours. */
const familyColour = (family: string, dark = false): string => categoryColor('type', family, dark);

/** The GR4 poles in `dark`: the card read through the sRGB bridge — the stand-in under jsdom, unless a reader is injected. */
const polesFor = (dark: boolean) => shadePoles(dark, chartRoles(dark).color('--lf-surface-card'));

/**
 * The colours of countries drawn in the order `keys` gives, by GR5: the n-th classified country takes the
 * sector sequence at rank n — one GR4 shade further at each round of fourteen — and the unclassified
 * (`Unknown`, `Other`) the Unknown grey, without taking a rank. Spelled out here, not read from the chart.
 */
function countryColours(keys: readonly string[], dark = false): string[] {
    const poles = polesFor(dark);
    let rank = 0;
    return keys.map((key) => (key === 'Unknown' || key === 'Other' ? categoryColor('sector', 'Unknown', dark) : sequenceColor('sector', KEYLESS_SEQUENCE, rank++, dark, poles)));
}

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
    restoreLayout = layOutChartContainer();
});

afterAll(() => {
    restoreLayout?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

afterEach(() => {
    // Module-level state every test of the file shares: the role reader and the theme class.
    setRoleReader(null);
    document.documentElement.classList.remove('dark');
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

/** Mounts the chart on `days`, as the allocation panel does, in `theme`, and waits for its first full option. */
async function mountChart(days: readonly Day[], dimension: Dimension, theme: 'light' | 'dark' = 'light') {
    expect(document.documentElement.classList.contains('dark'), `precondition: the ${theme} theme, whose colours the expectations read`).toBe(theme === 'dark');
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

/**
 * `buildAllocationHierarchy` on `weights` as the pie wires it — heaviest first, grouped by family, each
 * family in its own colour and every member after the first a GR4 shade of it — in the light theme.
 */
function hierarchyOf(weights: readonly Weight[]) {
    const entries = [...weights].sort((left, right) => right[1] - left[1]).map(([key, percent]) => ({key, weight: percent, item: key}));
    const poles = polesFor(false);
    return buildAllocationHierarchy(entries, {resolvePrimary: familyOf, colorOf: (family) => familyColour(family), shade: (base, rank) => familyShade(base, rank, poles)});
}

/** The order of the hierarchy's groups: the contract's other word for "by summed weight". */
function hierarchyGroupOrder(weights: readonly Weight[]): string[] {
    return [...new Set(hierarchyOf(weights).map(({primary}) => primary))];
}

/**
 * The shades the pie gives the subtypes of `weights`: what the history may draw nowhere. A shade that
 * happens to equal the colour of a family drawn is left out, since that colour is still drawn.
 */
function shadesOf(weights: readonly Weight[]): string[] {
    const hierarchy = hierarchyOf(weights);
    const verbatim = new Set(hierarchy.map(({primary}) => familyColour(primary).toLowerCase()));
    return [...new Set(hierarchy.filter(({depth}) => depth > 0).map(({color}) => color.toLowerCase()))].filter((shade) => !verbatim.has(shade));
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

/**
 * A calendar day as a tooltip header writes it in `localeTag` (plan 52, C2): short month, numeric day and year, read at
 * LOCAL midnight the way the app reads a calendar day. WHY test-side: an expected date never comes from the formatter
 * under test, so a wrong option or a wrong locale in the product cannot also be in the oracle. WHY at file scope: the
 * C2 header cases and the sector and geography tooltip read one oracle.
 */
function dayIn(iso: string, localeTag: string): string {
    const [year, month, date] = iso.split('-').map(Number);
    return new Date(year, month - 1, date).toLocaleDateString(localeTag, {year: 'numeric', month: 'short', day: 'numeric'});
}

/** A calendar day in the interface locale the chart is drawn in. WHY: the header follows the interface language, never the browser's. */
const uiDay = (iso: string) => dayIn(iso, uiLocale());

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
    it('draws one series per family, heaviest first: the family key as id, named after the family, in its own colour — the line and the area too — with no shade anywhere', async () => {
        // WHY: D375, "one area per family", and GR1, a colour per key. Catches a series left per raw type, a
        // family keyed by one of its members or by the cash bucket's Title Case, families ranked by their
        // heaviest member instead of their sum, a family named after a member, a colour handed out by rank,
        // and a subtype shade left in the option.
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
        expect(shades, 'precondition: the pie shades subtypes of these weights, so "no shade" can fail').not.toEqual([]);

        await mountChart(oneDay(D15_WEIGHTS), 'type');
        const drawn = drawnSeries() as Array<DrawnSeries & {lineStyle?: {color?: string}}>;

        expect(
            drawn.map(({id, name, itemStyle}) => ({id, name: withoutEmoji(name, id), color: itemStyle?.color})),
            'not one series per family, keyed, named, ranked and coloured as D375 and GR1 say',
        ).toEqual(byFamily.map(({family}) => ({id: family, name: typeLabel(family), color: familyColour(family)})));
        expect(
            drawn.map(({id, lineStyle}) => `${id} ${lineStyle?.color}`),
            'a line not in its family’s colour',
        ).toEqual(byFamily.map(({family}) => `${family} ${familyColour(family)}`));
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

    it('draws every asset type of the generated enum, and the cash bucket, inside the family assetTypeFamily gives it — each family in its own colour, no two alike', async () => {
        // WHY: D15 for every type there is, under D375 and GR1. A new enum value lands in the family K gives
        // it, and no family wears another's colour. Catches a subtype drawn on its own, or in the family of
        // its content, and a family drawn in a colour that is not its key's.
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
        const shades = shadesOf(weights);
        expect(shades, 'precondition: the pie shades subtypes of these weights, so "no shade" can fail').not.toEqual([]);

        await mountChart(oneDay(weights), 'type');
        const drawn = drawnSeries();

        expect(
            drawn.map(({id, data, itemStyle}) => ({id, sum: pointValue(data?.[0]), color: itemStyle?.color})),
            'not one series per family, holding its members, in its own colour',
        ).toEqual(byFamily.map(({family, perDate}) => ({id: family, sum: expect.closeTo(perDate[0], 9), color: familyColour(family)})));
        expect(new Set(drawn.map(({itemStyle}) => itemStyle?.color?.toLowerCase())).size, 'two families are drawn in the same colour').toBe(drawn.length);
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

describe('AllocationHistoryChart — sector and geography: grouped as before (D375 leaves them alone), coloured by GR1 and GR5', () => {
    it.each(UNTOUCHED)('$title: one series per raw category, ranked by weight — a sector in its own colour, a country in the sequence colour of its rank', async ({dimension, weights}) => {
        // WHY: the family is a type notion, and a category is coloured by its key — or, for a country, which
        // has none, by its rank in the sequence. Catches the type rules leaking into the other dimensions — a
        // regrouping, a re-ranking — and a colour handed out the wrong way.
        await mountChart(oneDay(weights), dimension);
        const keys = rankedKeys(weights);
        const colours = dimension === 'sector' ? keys.map((key) => categoryColor('sector', key, false)) : countryColours(keys);

        expect(drawnSeries().map(({id, data, itemStyle}) => ({id, value: pointValue(data?.[0]), color: itemStyle?.color}))).toEqual(keys.map((key, index) => ({id: key, value: weights.find(([name]) => name === key)?.[1], color: colours[index]})));
    });

    it.each(UNTOUCHED)("$title: today's tooltip, every category under 3% grouped in «Remaining» (D375 leaves it alone; plan 52 C2 writes its day in the interface language)", async ({dimension, weights}) => {
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

        // WHY (plan 52, C2): the header writes its day in the interface language, never as raw ISO.
        expect(html).toBe(buildTooltipHeader(uiDay(ONE_DATE), theme.mutedColor) + buildTooltipByThreshold(items, 3, theme, remainingLabel()));
        expect(html).not.toMatch(/\d{4}-\d{2}-\d{2}/);
        expect(html).not.toMatch(/data-allocation-(family|member)/);
    });
});

// =============================================================================
// Both themes — every series in its colour for the theme it is drawn in
// =============================================================================

/** The two themes, as the chart reads them off the `dark` class of <html> when it draws. */
const THEMES = [
    {theme: 'light', dark: false},
    {theme: 'dark', dark: true},
] as const;

/** What `dimension` draws `keys` in, in that order, in `dark`: a family's colour, a sector's, the countries' sequence. */
function coloursOf(dimension: Dimension, keys: readonly string[], dark: boolean): string[] {
    if (dimension === 'type') return keys.map((family) => familyColour(family, dark));
    if (dimension === 'sector') return keys.map((key) => categoryColor('sector', key, dark));
    return countryColours(keys, dark);
}

/**
 * Most blocks draw in the light theme, jsdom's default. Here each colouring path — the type dimension's
 * families, the sectors, the countries' sequence — is mounted in both themes, the dark one under the `dark`
 * class of <html>, and compared with the colours of that theme.
 */
describe('AllocationHistoryChart — both themes: every series in its colour for the theme it is drawn in', () => {
    const CASES = [{title: 'type', dimension: 'type' as Dimension, weights: D15_WEIGHTS}, ...UNTOUCHED].flatMap((path) => THEMES.map(({theme, dark}) => ({...path, theme, dark})));

    it.each(CASES)('$title, $theme theme: each series in its colour for that theme', async ({dimension, weights, theme, dark}) => {
        const order = expectedOrder(dimension, weights);
        // Control: the two themes differ on every series drawn, so a chart deaf to the theme fails one of the two rows.
        const [light, darkColours] = [coloursOf(dimension, order, false), coloursOf(dimension, order, true)];
        expect(
            order.filter((_key, index) => light[index] === darkColours[index]),
            'series with one colour in both themes',
        ).toEqual([]);

        document.documentElement.classList.toggle('dark', dark);
        await mountChart(oneDay(weights), dimension, theme);

        expect(drawnSeries().map(({id, itemStyle}) => `${id} ${itemStyle?.color}`)).toEqual(order.map((id, index) => `${id} ${(dark ? darkColours : light)[index]}`));
    });
});

// =============================================================================
// GR5 — the countries take the sector sequence by rank, the unclassified their grey
// =============================================================================

/**
 * Sixteen classified countries, all weights distinct, with `Unknown` third and `Other` last. In the order
 * they rank among the classified ones: USA is rank 0, DEU — right after Unknown — rank 2, IND rank 14, the
 * first of the second round, KOR rank 15.
 */
const RANKED_COUNTRIES = ['USA', 'ITA', 'DEU', 'FRA', 'ESP', 'GBR', 'JPN', 'CHN', 'CAN', 'AUS', 'CHE', 'NLD', 'SWE', 'BRA', 'IND', 'KOR'];
const GEO_WEIGHTS: readonly Weight[] = [
    ['USA', 30],
    ['ITA', 20],
    ['Unknown', 15],
    ['DEU', 10],
    ['FRA', 9],
    ['ESP', 8],
    ['GBR', 7],
    ['JPN', 6],
    ['CHN', 5],
    ['CAN', 4.5],
    ['AUS', 4],
    ['CHE', 3.5],
    ['NLD', 3],
    ['SWE', 2.5],
    ['BRA', 2],
    ['IND', 1.5],
    ['KOR', 1],
    ['Other', 0.5],
];

describe('AllocationHistoryChart — geography: the countries take the sector sequence by rank (GR5), the unclassified keep their grey', () => {
    it.each(THEMES)('$theme theme: Unknown and Other in the Unknown grey, taking no rank; the n-th classified country in the n-th colour of the sequence; rank 14 the first-round shade of the first colour', async ({theme, dark}) => {
        // Premises: one round of the sequence is fourteen colours, and the fixture ranks as described.
        expect(KEYLESS_SEQUENCE).toHaveLength(14);
        expect(rankedKeys(GEO_WEIGHTS).filter((key) => key !== 'Unknown' && key !== 'Other')).toEqual(RANKED_COUNTRIES);

        document.documentElement.classList.toggle('dark', dark);
        await mountChart(oneDay(GEO_WEIGHTS), 'geo', theme);
        const colourOf = new Map(drawnSeries().map(({id, itemStyle}) => [id, itemStyle?.color]));
        const grey = categoryColor('sector', 'Unknown', dark);
        const sequence = (rank: number) => categoryColor('sector', KEYLESS_SEQUENCE[rank % KEYLESS_SEQUENCE.length], dark);

        // The unclassified wear their own grey, wherever they rank.
        expect({Unknown: colourOf.get('Unknown'), Other: colourOf.get('Other')}).toEqual({Unknown: grey, Other: grey});
        // DEU comes right after Unknown in the stack and takes rank 2, not 3: the grey consumed no rank.
        expect(colourOf.get('DEU'), 'DEU, the first country after Unknown').toBe(sequence(2));
        // Round 0: the fourteen colours of the sequence, in its order.
        expect(RANKED_COUNTRIES.slice(0, 14).map((key) => colourOf.get(key))).toEqual(KEYLESS_SEQUENCE.map((_key, rank) => sequence(rank)));
        // Round 1: the first GR4 shade of the first colour — never the first colour again — then of the second.
        const poles = polesFor(dark);
        expect({IND: colourOf.get('IND'), KOR: colourOf.get('KOR')}).toEqual({IND: familyShade(sequence(0), 1, poles), KOR: familyShade(sequence(1), 1, poles)});
        expect(colourOf.get('IND'), 'rank 14 repeats rank 0').not.toBe(colourOf.get('USA'));
        const classified = RANKED_COUNTRIES.map((key) => colourOf.get(key)?.toLowerCase());
        expect(new Set(classified).size, 'two countries in one colour').toBe(RANKED_COUNTRIES.length);
    });

    it('announces a colour coming back — past the 98 the sequence and its six rounds of shades give — and stays silent at 98', async () => {
        // The warning is the chart's own debug channel: spied, not printed.
        const warn = vi.spyOn(debug, 'warn').mockImplementation(() => {});
        try {
            /** `count` classified countries, weights all distinct, and the unclassified bucket, which takes no rank. */
            const countries = (count: number): Weight[] => [...Array.from({length: count}, (_, index) => [`C${String(index).padStart(3, '0')}`, 1000 - index] as const), ['Unknown', 0.5] as const];

            const view = await mountChart(oneDay(countries(98)), 'geo');
            expect(drawnSeries(), 'precondition: 98 countries and the bucket drawn').toHaveLength(99);
            expect(warn, 'a warning with 98 countries: every colour is still distinct').not.toHaveBeenCalled();
            view.unmount();
            chartInstances.length = 0;

            const crowded = await mountChart(oneDay(countries(99)), 'geo');
            expect(drawnSeries(), 'precondition: 99 countries and the bucket drawn').toHaveLength(100);
            expect(warn, 'no warning with 99 countries: the 99th repeats a colour in silence').toHaveBeenCalled();
            expect(warn.mock.calls.map(([component]) => component)).toEqual(warn.mock.calls.map(() => 'AllocationHistoryChart'));
            // Unmounted under the spy: a redraw after the test (the shared afterEach touches <html>) would print it.
            crowded.unmount();
        } finally {
            warn.mockRestore();
        }
    });
});

// =============================================================================
// C4 — a chart-colour change redraws the whole option, the roles read again
// =============================================================================

describe('AllocationHistoryChart — redrawn in full when its colours change (C4)', () => {
    it("notifyChartColorsChange() hands ECharts a full option again, the card read again from the chart's own element: a second-round country follows it", async () => {
        const FIRST_CARD = '#2a1f3d';
        const NEXT_CARD = '#1f3d2a';
        let card = FIRST_CARD;
        const chartElement = () => document.querySelector(`[data-testid="${CHART_CONTAINER_TESTID}"]`);
        // The card answered for the chart's own element only: a shade made from any other read would differ.
        setRoleReader((role, scope) => (role === '--lf-surface-card' && scope !== null && scope === chartElement() ? card : ''));
        document.documentElement.classList.add('dark');

        await mountChart(oneDay(GEO_WEIGHTS), 'geo', 'dark');
        // IND is rank 14: the first-round shade of the first colour, which the dark theme takes toward the card.
        const first = categoryColor('sector', KEYLESS_SEQUENCE[0], true);
        const shadeOn = (onCard: string) => familyShade(first, 1, shadePoles(true, onCard));
        const drawnIND = () => drawnSeries().find(({id}) => id === 'IND')?.itemStyle?.color;
        // Control: the two cards shade the first colour differently.
        expect(shadeOn(FIRST_CARD)).not.toBe(shadeOn(NEXT_CARD));
        expect(drawnIND()).toBe(shadeOn(FIRST_CARD));

        card = NEXT_CARD;
        const before = recordedCalls().length;
        // Nothing redraws by itself: a role is read when the option is built, and only the signal says it changed.
        flushSync();
        await tick();
        expect(recordedCalls().length, 'the chart redrew without being told its colours changed').toBe(before);

        notifyChartColorsChange();

        expect(recordedCalls().slice(before).filter(isFullOption).length, 'no full option followed the notification').toBeGreaterThan(0);
        expect(drawnIND(), 'the shade of the new card').toBe(shadeOn(NEXT_CARD));
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
    });

    it('a notification redraws the type dimension in full as well, each family still in its own colour', async () => {
        await mountChart(oneDay(D15_WEIGHTS), 'type');
        const before = recordedCalls().length;

        notifyChartColorsChange();

        expect(recordedCalls().slice(before).filter(isFullOption).length, 'no full option followed the notification').toBeGreaterThan(0);
        expect(drawnSeries().map(({id, itemStyle}) => `${id} ${itemStyle?.color}`)).toEqual(familiesOf(oneDay(D15_WEIGHTS)).map(({family}) => `${family} ${familyColour(family)}`));
    });
});

// =============================================================================
// M-18 — the y axis and the type tooltip in the interface language
// =============================================================================

/**
 * M-18 CP2: the y axis and the type tooltip in the interface language.
 *
 * The y axis prints its ticks by interpolating the number, `${value}%`, and the type tooltip printed the
 * share of each family and member with `toFixed(1)`: a French reader got `12.5%` and `34.0%` where French
 * writes `12,5 %` and `34,0 %`. Every figure is written in the interface language (the developer's
 * decision M-18, 2026-10-12):
 *
 *   - a y tick: `formatPercent(value, {digits: 2, signed: false, trim: true})`, the decimals the tick has,
 *     up to two — `25 %`, `12,5 %`;
 *   - a share in the type tooltip: `formatPercent(value, {digits: 1, signed: false})`, one decimal always.
 *     This one belongs to the main CP2 cure: its case was written after that cure had landed, so it is
 *     green with it, and red in French against the `toFixed(1)` before it.
 *
 * Read: the y-axis formatter of the last full option, called as ECharts calls it on a tick; the value
 * cell of every row of the type tooltip, found by its `data-allocation-family` or
 * `data-allocation-member` attribute. Expectations from `Intl` in an explicit locale; English is the
 * control, today's text.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set`, which also drives svelte-i18n —
 * before the mount; the `afterEach` puts English back.
 */
describe('AllocationHistoryChart — the y axis and the type tooltip in the interface language (M-18)', () => {
    /** The UI languages read, with the interface locale each gives on jsdom's en-US browser. */
    const LANGUAGES = [
        {lang: 'en', locale: 'en-US'},
        {lang: 'fr', locale: 'fr'},
    ] as const;

    /** Ticks with no decimal, one and two, and the ends of the axis. */
    const TICKS = [0, 12.5, 25, 37.75, 100];

    /** A tick as the y axis must write it in `localeTag`: the decimals it has, up to two, after `toFixed(2)`. */
    const tickIn = (value: number, localeTag: string) => new Intl.NumberFormat(localeTag, {style: 'percent', minimumFractionDigits: 0, maximumFractionDigits: 2}).format(Number(value.toFixed(2)) / 100);

    /** A share as the type tooltip must write it in `localeTag`: exactly one decimal, after `toFixed(1)`. */
    const shareIn = (value: number, localeTag: string) => new Intl.NumberFormat(localeTag, {style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1}).format(Number(value.toFixed(1)) / 100);

    /** `value` as JSON with its no-break spaces spelled out, so a message tells U+00A0 and U+202F from a space. */
    function spelled(value: unknown): string {
        return JSON.stringify(value).replace(/[\u00a0\u202f]/g, (space) => `\\u${space.charCodeAt(0).toString(16).padStart(4, '0')}`);
    }

    /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
    async function switchLanguage(lang: 'en' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    /** The y-axis label formatter of the last full option. */
    function yAxisFormatter(): (value: number) => string {
        const formatter = (drawnOption() as unknown as {yAxis?: {axisLabel?: {formatter?: unknown}}}).yAxis?.axisLabel?.formatter;
        if (typeof formatter !== 'function') throw new Error('the y axis carries no label formatter');
        return formatter as (value: number) => string;
    }

    /** The value cell of every row of a type tooltip, keyed `FAMILY` for a family's own row and `FAMILY › KEY` for a member's. */
    function sharesIn(html: string): Record<string, string> {
        const host = document.createElement('div');
        host.innerHTML = html;
        const shares: Record<string, string> = {};
        for (const entry of Array.from(host.querySelectorAll('[data-allocation-family]'))) {
            const family = entry.getAttribute('data-allocation-family') ?? '';
            const own = Array.from(entry.querySelectorAll('b')).find((cell) => cell.closest('[data-allocation-member]') === null);
            shares[family] = own?.textContent ?? '(no value cell)';
            for (const member of Array.from(entry.querySelectorAll('[data-allocation-member]'))) {
                shares[`${family} › ${member.getAttribute('data-allocation-member')}`] = member.querySelector('b')?.textContent ?? '(no value cell)';
            }
        }
        return shares;
    }

    /** The shares the type tooltip must print for one day, keyed as `sharesIn` reads them, from D375's expected entries. */
    function expectedShares(weights: readonly Weight[], localeTag: string): Record<string, string> {
        const {shown} = expectedEntries(weights);
        return Object.fromEntries(shown.flatMap(({family, value, members}) => [[family, shareIn(value, localeTag)], ...members.map(({key, value: memberValue}) => [`${family} › ${key}`, shareIn(memberValue, localeTag)])]));
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; French joins it, so a switch never waits on a loader.
        await waitLocale('fr');
        // Controls: this runtime has French data, so both shapes of percentage differ from English.
        expect(tickIn(12.5, 'fr'), 'a French tick differs from English').not.toBe(tickIn(12.5, 'en-US'));
        expect(shareIn(34, 'fr'), 'a French share differs from English').not.toBe(shareIn(34, 'en-US'));
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it.each(LANGUAGES)('$lang UI on an en-US browser: the y-axis ticks in $locale, with the decimals they have', async ({lang, locale: localeTag}) => {
        // WHY: the axis interpolates its ticks (`${value}%`), so they carry a point in every language.
        // English is the control: today's text, which is also the trimmed text of the rule.
        await switchLanguage(lang);
        await mountChart(TOOLTIP_DAYS, 'type');
        const format = yAxisFormatter();
        const expected = TICKS.map((value) => tickIn(value, localeTag));

        expect(
            TICKS.map((value) => format(value)),
            spelled(expected),
        ).toEqual(expected);
    });

    it.each(LANGUAGES)('$lang UI on an en-US browser: the type tooltip’s shares in $locale, one decimal each (main cure)', async ({lang, locale: localeTag}) => {
        // WHY: each family's and member's share was `toFixed(1)` and a `%`. Catches a row left on that
        // route, family or member, on either day.
        await switchLanguage(lang);
        await mountChart(TOOLTIP_DAYS, 'type');
        const option = drawnOption();
        const expected = TOOLTIP_DAYS.map(({weights}) => expectedShares(weights, localeTag));

        expect(
            TOOLTIP_DAYS.map((_day, index) => sharesIn(tooltipOf(option, index))),
            spelled(expected),
        ).toEqual(expected);
    });
});

// =============================================================================
// The grid's right inset for the last time label (plan 52, C1)
// =============================================================================

/**
 * `containLabel` reserves the x labels' height, never the half-width a centred label overhangs past the plot's right
 * edge, so on a phone the last time label was cut. The time axis now widens `grid.right` to half its widest label
 * plus 2 px when that beats '4%'. jsdom's container is 0 px wide: a compact axis, and '4%' of it is 0 px.
 */
describe('AllocationHistoryChart — the grid right inset holds the last time label (plan 52, C1)', () => {
    /** The grid and the x-axis formatter of a full option: `DrawnOption` leaves them out, only this describe reads them. */
    type WithTimeAxis = {grid?: {right?: unknown}; xAxis?: {axisLabel?: {formatter?: (value: number, index?: number, extra?: {time?: {level?: number}; level?: number}) => string}}};

    /** Every local midnight from the day before `first` to the day after `last` ('YYYY-MM-DD'): the ticks the axis can label. Stepped by calendar day, so a DST change neither drops nor doubles one. */
    function midnightsAround(first: string, last: string): Date[] {
        const [firstYear, firstMonth, firstDay] = first.split('-').map(Number);
        const [lastYear, lastMonth, lastDay] = last.split('-').map(Number);
        const stop = new Date(lastYear, lastMonth - 1, lastDay + 1).getTime();
        const days: Date[] = [];
        for (let day = new Date(firstYear, firstMonth - 1, firstDay - 1); day.getTime() <= stop; day = new Date(day.getFullYear(), day.getMonth(), day.getDate() + 1)) days.push(day);
        return days;
    }

    beforeEach(() => {
        // The hoisted mock keeps the fonts across the file: each case reads only what its own mount measured.
        measuredFonts.length = 0;
    });

    it('widens grid.right to half of every label the emitted time formatter can draw plus 2px, measured in the 14px axis font (D3)', async () => {
        // WHY: the user-visible defect, as in GrowthChart (D1). The bound comes from the formatter ECharts is handed, not
        // from the helper's own list, and the fake measure is FAKE_TEXT_PX_PER_CHAR px a character.
        await mountChart(SUM_DAYS, 'type');
        const option = drawnOption() as unknown as WithTimeAxis;
        const dates = SUM_DAYS.map(({date}) => date);
        const right = option.grid?.right;
        const formatter = option.xAxis?.axisLabel?.formatter;

        expect(typeof right, 'grid.right is an inset in px, no longer the 4% base').toBe('number');
        if (typeof formatter !== 'function') throw new Error('The time axis carries no label formatter');
        const texts = midnightsAround(dates[0], dates[dates.length - 1])
            .flatMap((day) => [0, 1].map((level) => formatter(day.getTime(), 0, {time: {level}, level})))
            .filter((text) => text !== '');
        expect(texts.length, 'precondition: the formatter names the midnights of the axis').toBeGreaterThan(0);
        for (const text of texts) expect(right as number, `"${text}" overhangs half its width past its tick`).toBeGreaterThanOrEqual(Math.ceil((text.length * FAKE_TEXT_PX_PER_CHAR) / 2) + 2);
        expect(right).toBe(timeAxisGridRight({width: 0, values: dates, locale: uiLocale(), base: '4%', measure: (text) => text.length * FAKE_TEXT_PX_PER_CHAR}));
        expect(measuredFonts.length, 'the labels were measured through echarts.format.getTextRect').toBeGreaterThan(0);
        expect(
            measuredFonts.filter((font) => !font.startsWith('14px ')),
            'fonts other than the 14px axis font',
        ).toEqual([]);
    });
});

// =============================================================================
// Plan 52, C2 — the tooltip header in the interface language, the running week to its last day
// =============================================================================

/**
 * Plan 52, C2: the tooltip header writes its dates in the interface language, and the week still running ends on its
 * last day.
 *
 * `buildAllocationTooltipHeader` prints the ISO days it is handed (defect 3a): `2025-03-05` over a day,
 * `Week 2024-06-03 – 2024-06-09` then `Value at 2024-06-09` over a week, `Value at 2010-06-30` under a month. And the
 * week still running ends on the coming Sunday (`row.bucketEnd`), a day the series has not reached. After C2 every
 * date in the header is written by `formatDay` (short month, numeric day and year, in `uiLocale()`), and a week ends on
 * its last day with data: a closed week on its Sunday, the running one on the series' last day (`row.date`), the rule
 * the price charts already apply (`bucketSpanUpTo`, read for the contract, not imported). Same keys, same lines; the
 * month label is already localized and stays as it is.
 *
 * Resolution. The fake chart is 800 px wide (`getWidth`), and `chooseInitialResolution` climbs a tier while that
 * tier's buckets are more than 1.3 per px (`DENSITY_THRESHOLDS.line`): read here, never changed. It picks once, over
 * the whole history, before the first full option.
 *   - daily: five days, 2025-03-03..07.
 *   - weekly: 1100 consecutive days (Thu 2022-06-23..Thu 2025-06-26), 1.375 per px, over 1.3; their 158 weeks are 0.20
 *     per px, so it stays weekly.
 *   - monthly: one Wednesday a week for 1100 weeks (2000-01-05..2021-01-27), plus every day of June 2010: 1125 days
 *     (1.41 per px) and 1100 weeks (1.375 per px) are both over 1.3, so it climbs to the 253 months (0.32 per px).
 * Each row is found by its date, and the date of its neighbours proves the tier: the day before is a day, the Sunday
 * before is a week, the last Wednesday of May is a month.
 *
 * Closed periods are read in the MIDDLE of the series, every day of them carrying data. The running week is the
 * series' LAST row: the history stops on a Thursday.
 *
 * Expected texts. Every key is resolved through `get(_)` and read as text, every day comes from `dayIn` and the month
 * from `Intl`, both in the test. Each case ends on the negative oracle: no `YYYY-MM-DD` anywhere in the header.
 */
describe('AllocationHistoryChart — the tooltip header writes its dates in the interface language, and the running week ends on its last day (plan 52, C2)', {timeout: 30_000}, () => {
    /** A calendar period, its first and its last day. */
    type Span = {start: string; end: string};

    /** The weights of every day: two sectors. WHY sector: the plain threshold tooltip, its header ahead of its rows. */
    const WEIGHTS: readonly Weight[] = [
        ['Technology', 60],
        ['Financials', 40],
    ];

    /** `count` ISO days from `first`, one every `step` days. WHY UTC arithmetic: no DST change shifts or doubles a date. */
    function isoFrom(first: string, count: number, step = 1): string[] {
        const start = Date.parse(`${first}T00:00:00Z`);
        return Array.from({length: count}, (_day, index) => new Date(start + index * step * 86_400_000).toISOString().slice(0, 10));
    }

    /** One history day per distinct date, in date order, each holding WEIGHTS. */
    const daysOn = (dates: readonly string[]): Day[] => [...new Set(dates)].sort().map((date) => ({date, weights: WEIGHTS}));

    /** The day of the week of an ISO date, Sunday 0. WHY: a fixture's Monday, Thursday and Sunday are checked, not assumed. */
    const weekdayOf = (iso: string) => new Date(`${iso}T00:00:00Z`).getUTCDay();

    /** Five days; the cascade draws them day by day. */
    const DAILY_DAYS = daysOn(isoFrom('2025-03-03', 5));
    /** A day in the middle of DAILY_DAYS. */
    const DAILY_DAY = '2025-03-05';

    /** 1100 consecutive days, Thu 2022-06-23..Thu 2025-06-26. WHY so many: 1.375 days per px of the 800 px fake, over 1.3. */
    const WEEKLY_DAYS = daysOn(isoFrom('2022-06-23', 1100));
    /** A Monday–Sunday week in the middle of WEEKLY_DAYS, two years in. */
    const CLOSED_WEEK: Span = {start: '2024-06-03', end: '2024-06-09'};
    /** The week WEEKLY_DAYS stops in: its Monday, the series' last day (a Thursday) and the Sunday still to come. */
    const RUNNING_WEEK = {start: '2025-06-23', last: '2025-06-26', comingSunday: '2025-06-29'};

    /** One Wednesday a week for 1100 weeks, and every day of June 2010. WHY June day by day: a month whose last calendar day carries data. */
    const MONTHLY_DAYS = daysOn([...isoFrom('2000-01-05', 1100, 7), ...isoFrom('2010-06-01', 30)]);
    /** A calendar month in the middle of MONTHLY_DAYS. */
    const CLOSED_MONTH: Span = {start: '2010-06-01', end: '2010-06-30'};

    /** The interface locale the French UI gives on jsdom's en-US browser (see M-18 above). */
    const FRENCH = 'fr';

    /** An ISO day. WHY: what no header line may hold once C2 is in, the negative oracle. */
    const ISO_DAY = /\d{4}-\d{2}-\d{2}/;

    /** A month as the month label writes it in `localeTag`: long month and year, read in UTC as `formatMonthLabel` reads it. WHY test-side: the oracle never comes from the product. */
    function monthIn(iso: string, localeTag: string): string {
        const [year, month, date] = iso.split('-').map(Number);
        return new Intl.DateTimeFormat(localeTag, {month: 'long', year: 'numeric', timeZone: 'UTC'}).format(new Date(Date.UTC(year, month - 1, date)));
    }

    /** Text as a user reads it from HTML. WHY: the header interpolates raw `$t()` output, so an expected line goes through the same parser. */
    function textOf(html: string): string {
        const host = document.createElement('div');
        host.innerHTML = html;
        return host.textContent ?? '';
    }

    /** A key's text in today's language, as a header line reads. WHY: never a translated literal, and a key that does not resolve fails here instead of matching itself. */
    function keyText(key: string, values: Record<string, string>): string {
        const text = textOf(get(_)(key, {values}));
        expect(text, `${key} does not resolve`).not.toBe(key);
        return text;
    }

    /** The first `count` top-level lines of a tooltip, as read. WHY: the header and its "value at" line are each one top-level `<div>`, ahead of every row. */
    function headerLines(html: string, count: number): string[] {
        const host = document.createElement('div');
        host.innerHTML = html;
        return Array.from(host.children)
            .filter((child) => child.tagName === 'DIV')
            .slice(0, count)
            .map((child) => child.textContent ?? '');
    }

    /** Barrier: every day of `span` carries data in `days`. WHY: a header names the period's own edges only when the series covers it whole. */
    function expectCovered(days: readonly Day[], span: Span): void {
        const first = Date.parse(`${span.start}T00:00:00Z`);
        const count = (Date.parse(`${span.end}T00:00:00Z`) - first) / 86_400_000 + 1;
        expect(
            days.map(({date}) => date).filter((date) => date >= span.start && date <= span.end),
            `fixture: every day of ${span.start}..${span.end} carries data`,
        ).toEqual(isoFrom(span.start, count));
    }

    /** Change the UI language as LanguageSelector does, then flush. WHY a copy: M-18's is local to its describe. */
    async function switchLanguage(lang: 'en' | 'fr'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    /** The dates the first series is drawn on, one per row. WHY the dates: a row is found by what it stands for, never by its position. */
    const drawnDates = (option: DrawnOption) => (option.series[0]?.data ?? []).map(pointDate);

    /**
     * The row drawn on `date`, with the option that draws it, its neighbours proving the tier. WHY: never a position;
     * `before` (and `after`) tell a day from a week and a week from a month, and `last` says whether the row must close the
     * series (the running week) or sit inside it (a closed period).
     */
    async function rowOn(date: string, neighbours: {before: string; after?: string}, last: boolean): Promise<{option: DrawnOption; index: number}> {
        return waitFor(
            () => {
                const option = drawnOption();
                const dates = drawnDates(option);
                const index = dates.indexOf(date);
                expect(index, `a row drawn on ${date}, after the first`).toBeGreaterThan(0);
                expect(dates[index - 1], `the row before ${date}`).toBe(neighbours.before);
                if (last) {
                    expect(index, `${date} closes the series`).toBe(dates.length - 1);
                } else {
                    expect(index, `${date} is not the last row`).toBeLessThan(dates.length - 1);
                    if (neighbours.after) expect(dates[index + 1], `the row after ${date}`).toBe(neighbours.after);
                }
                return {option, index};
            },
            {timeout: 5_000},
        );
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; French joins it, so a switch never waits on a loader.
        await waitLocale(FRENCH);
        // The one literal of this describe: if the oracle does not write en-US as en-US, the environment is wrong, not the product.
        expect(dayIn('2025-12-29', 'en-US'), 'environment: the date oracle writes en-US').toBe('Dec 29, 2025');
        // Control: this runtime has French data, so the French case tells the interface locale from English.
        expect(dayIn(CLOSED_WEEK.start, FRENCH), 'a French day differs from English').not.toBe(dayIn(CLOSED_WEEK.start, 'en-US'));
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('daily: a day in the middle of the series heads its tooltip with the day in the interface language', async () => {
        // WHY: the plainest header, the day itself, was raw ISO.
        await mountChart(DAILY_DAYS, 'sector');
        const {option, index} = await rowOn(DAILY_DAY, {before: '2025-03-04', after: '2025-03-06'}, false);
        const lines = headerLines(tooltipOf(option, index), 1);

        expect(lines).toEqual([uiDay(DAILY_DAY)]);
        expect(lines.join('\n')).not.toMatch(ISO_DAY);
    });

    it('weekly, a closed week: its Monday and its Sunday, and its "value at" Sunday, in the interface language', async () => {
        // WHY: the week range and the "value at" line both carried ISO.
        expect([CLOSED_WEEK.start, CLOSED_WEEK.end].map(weekdayOf), 'fixture: a Monday–Sunday week').toEqual([1, 0]);
        expectCovered(WEEKLY_DAYS, CLOSED_WEEK);
        await mountChart(WEEKLY_DAYS, 'sector');
        const {option, index} = await rowOn(CLOSED_WEEK.end, {before: '2024-06-02', after: '2024-06-16'}, false);
        const lines = headerLines(tooltipOf(option, index), 2);

        expect(lines).toEqual([keyText('chart.tooltip.weekRange', {start: uiDay(CLOSED_WEEK.start), end: uiDay(CLOSED_WEEK.end)}), keyText('chart.tooltip.valueAt', {date: uiDay(CLOSED_WEEK.end)})]);
        expect(lines.join('\n')).not.toMatch(ISO_DAY);
    });

    it('weekly, the week still running: it ends on the series\u2019 last day, a Thursday, and the coming Sunday is nowhere in the header', async () => {
        // WHY: the running week printed the coming Sunday (`row.bucketEnd`), a day the series has not reached.
        expect([RUNNING_WEEK.start, RUNNING_WEEK.last, RUNNING_WEEK.comingSunday].map(weekdayOf), 'fixture: a Monday, a Thursday, a Sunday').toEqual([1, 4, 0]);
        expect(
            WEEKLY_DAYS.map(({date}) => date).filter((date) => date >= RUNNING_WEEK.start),
            'fixture: the history stops on the Thursday',
        ).toEqual(isoFrom(RUNNING_WEEK.start, 4));
        await mountChart(WEEKLY_DAYS, 'sector');
        const {option, index} = await rowOn(RUNNING_WEEK.last, {before: '2025-06-22'}, true);
        const lines = headerLines(tooltipOf(option, index), 2);

        expect(lines).toEqual([keyText('chart.tooltip.weekRange', {start: uiDay(RUNNING_WEEK.start), end: uiDay(RUNNING_WEEK.last)}), keyText('chart.tooltip.valueAt', {date: uiDay(RUNNING_WEEK.last)})]);
        const header = lines.join('\n');
        expect(header, 'the coming Sunday, formatted').not.toContain(uiDay(RUNNING_WEEK.comingSunday));
        expect(header, 'the coming Sunday, ISO').not.toContain(RUNNING_WEEK.comingSunday);
        expect(header).not.toMatch(ISO_DAY);
    });

    it('monthly, a closed month: the month label as today, and its "value at" day, its last, in the interface language', async () => {
        // WHY: the month label was already localized and stays as it is; the "value at" line under it carried ISO.
        expectCovered(MONTHLY_DAYS, CLOSED_MONTH);
        await mountChart(MONTHLY_DAYS, 'sector');
        const {option, index} = await rowOn(CLOSED_MONTH.end, {before: '2010-05-26', after: '2010-07-28'}, false);
        const lines = headerLines(tooltipOf(option, index), 2);

        expect(lines).toEqual([keyText('chart.tooltip.monthLabel', {month: monthIn(CLOSED_MONTH.start, uiLocale())}), keyText('chart.tooltip.valueAt', {date: uiDay(CLOSED_MONTH.end)})]);
        expect(lines.join('\n')).not.toMatch(ISO_DAY);
    });

    it('fr UI on an en-US browser, weekly, a closed week: the dates follow the interface locale, not a hard-coded one', async () => {
        // WHY: an English expectation alone would also pass with en-US hard-coded in the product.
        await switchLanguage(FRENCH);
        expect(uiLocale(), 'control: the interface locale').toBe(FRENCH);
        expectCovered(WEEKLY_DAYS, CLOSED_WEEK);
        await mountChart(WEEKLY_DAYS, 'sector');
        const {option, index} = await rowOn(CLOSED_WEEK.end, {before: '2024-06-02', after: '2024-06-16'}, false);
        const lines = headerLines(tooltipOf(option, index), 2);

        expect(lines).toEqual([keyText('chart.tooltip.weekRange', {start: dayIn(CLOSED_WEEK.start, FRENCH), end: dayIn(CLOSED_WEEK.end, FRENCH)}), keyText('chart.tooltip.valueAt', {date: dayIn(CLOSED_WEEK.end, FRENCH)})]);
        expect(lines.join('\n')).not.toMatch(ISO_DAY);
    });
});
