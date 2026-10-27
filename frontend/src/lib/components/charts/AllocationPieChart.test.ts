// @vitest-environment jsdom
/**
 * AllocationPieChart.test.ts — what the "by type" pie hands ECharts, read off the real component:
 * the family every asset type is drawn in, the icon that titles each arc's tooltip, and the palette
 * its arcs are drawn from.
 *
 * ## Why the component, and not the pure modules
 *
 * `buildAllocationHierarchy` and `buildAllocationRings` take their families as given, and
 * `allocationRings.test.ts` tests them that way. *Which* families the pie draws is one argument
 * inside the component — the `resolvePrimary` it passes to the hierarchy — and the tooltip is a
 * closure built inside `renderChart()`. Neither has a pure seam, and a test that rebuilt either by
 * hand would check a copy of the component rather than the component. So the pie is mounted in
 * jsdom with ECharts replaced by a recorder, as in `GrowthChart.test.ts`: real props, real runes,
 * the real hierarchy and rings, and the option the component decided to draw — its series data,
 * and its tooltip formatter called the way ECharts calls it when an arc is hovered.
 *
 * ## The families are K's
 *
 * The pie groups by **vehicle** (R12, option B, 24/09/2026), and since K's taxonomy landed the
 * vehicle is K's own container view, `assetTypeFamily`: every ETF subtype sits in ETF, and
 * real-estate crowdfunding — `CROWDFUND_REAL_ESTATE`, one of K's types — in CROWDFUND. A family
 * that holds a subtype is split on the outer ring, where its generic member is captioned as the
 * generic one (`dashboard.allocationGeneric`), so that it does not read as the whole family.
 * The expected family of every type is K's function itself, so these tests say "the pie draws
 * what K files", never a list of their own; the spellings `assetTypeFamily` accepts (case,
 * surrounding spaces, blanks) are pinned where K defines it, in `assetTypeTables.test.ts`. The one
 * spelling pinned here is the one the pie actually receives besides the enum: the engine's
 * Title Case cash bucket `"Liquidity"`.
 *
 * ## One icon per arc, the type's own
 *
 * Every subtype now has a composite icon of its own — its family's, with a pastille of what it
 * holds (K, `PNG_MAP`). The tooltip therefore shows exactly one icon, `getAssetTypeIconUrl(type)`.
 * The overlay drawn while subtypes still wore their family's icon (content icon beside the main
 * one) would now show the content twice; the second test of that block proves the composites are
 * really there, so "one icon" cannot hold because every subtype has fallen back to its family's
 * picture.
 *
 * ## Every category in its own colour (GR1), the sector emoji from the sector store
 *
 * The designer's round 2 (D-T17) gives every category a colour of its own, by key and never by rank:
 * a family is `categoryColor('type', family)` on its arc whatever its rank, a subtype the GR4 shade
 * of it (`familyShade`), a sector `categoryColor('sector', key)`. Which colour a key has is pinned
 * by the theme's own tests; what is pinned here is that the mounted pie draws through those
 * functions — compared with them, never with copied hex values — in both themes, with the dark
 * theme's shades taking the card the pie sits on, read from its own element through the sRGB
 * bridge (`chartRoles`), and that no option hands ECharts a `color` list to paint by index.
 *
 * The sector names carry their emoji from the sector store, which loads the backend's one map
 * (GET /utilities/sectors, mocked below with invented emoji, so a drawn emoji can only come from it):
 * none until the list arrives, then a full rebuild. A Designer Lab edit (contract C4,
 * `notifyChartColorsChange`) rebuilds the whole option too, never the data-only update.
 *
 * ## What is not asserted
 *
 * No translated word: labels and the generic caption are resolved from the shipped catalogue,
 * through the same `$_` and the same keys the component calls. A sector name is read only for the
 * emoji in front of it. Every value and amount is synthetic.
 *
 * ## Why the imports are dynamic
 *
 * The pie imports K's `assetTypes.ts`, which reads the generated Zodios schemas
 * (`$lib/api/generated`, gitignored, written by `./dev.py api sync`) at module load. As in the
 * other chart tests, the modules are imported after asserting the generated file exists, so a
 * missing client is reported with the command that fixes it — never skipped.
 *
 * @module components/charts/AllocationPieChart.test
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: a recorder, not a renderer — jsdom has no canvas, and pixels are not the
 * subject.
 *
 * It answers every call the pie and its helpers make on an instance (`attachChartReady` → `on`,
 * `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the resize watcher → `resize`, the
 * teardown → `dispose`) and keeps every `setOption` payload, so a test can read what the component
 * decided to draw.
 */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
        opts: unknown;
    }

    interface FakeChart {
        setOptionCalls: SetOptionCall[];
        setOption: (option: Record<string, unknown>, opts?: unknown) => void;
        getDom: () => unknown;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler: () => void) => void;
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
            getDom: () => dom,
            on: () => {},
            off: () => {},
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

/**
 * GET /utilities/sectors, the one call the pie makes through `$lib/api`: the sector store loads its
 * emoji from it, once per module. Every other endpoint answers an empty list, so jsdom sends no
 * request (the pattern of `AllocationHistoryChart.test.ts`). Not `importOriginal`: the real module
 * re-exports the generated client, whose absence the `beforeAll` below reports with its fix.
 */
const sectorsEndpoint = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, name) {
                return name === 'list_sectors_api_v1_utilities_sectors_get' ? sectorsEndpoint : vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {flushSync, tick, type ComponentProps} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';

import {render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {getSectorEmoji, sectorEmojiVersion} from '$lib/stores/reference/sectorStore';
import {categoryColor, CATEGORY_SEQUENCE, sequenceColor} from '$lib/theme/chartCategories';
import {familyShade, shadePoles} from '$lib/theme/chartShades';
import {chartRoles, setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';

// =============================================================================
// Fixtures
// =============================================================================

/**
 * The generated client, from the frontend root vitest runs in, as the other jsdom tests of the tree
 * resolve their files (`layout.gate.test.ts`). Not `new URL(…, import.meta.url)`: under jsdom the
 * global `URL` is jsdom's, and `fileURLToPath` refuses what it builds.
 */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** The engine's cash bucket in `by_type`: Title Case, and not an `AssetType`. */
const CASH_BUCKET = 'Liquidity';

/** One slice of `allocation_by_type`, as the Dashboard's allocation panel hands it to the pie. */
interface Slice {
    name: string;
    /** Percent of the portfolio. */
    value: number;
    /** Absolute amount, synthetic. */
    amount: number;
}

const slice = (name: string, value: number): Slice => ({name, value, amount: value * 100});

/**
 * Plain crowdfunding and real-estate crowdfunding — one family by vehicle — beside a bond slice.
 * The family (31.5 + 24 = 55.5) outweighs the bond (44.5), and its subtype is listed last, after
 * the neighbour: only the resolver can bring the two together.
 */
const CROWDFUND_CASE: Slice[] = [slice('CROWDFUND', 31.5), slice('BOND', 44.5), slice('CROWDFUND_REAL_ESTATE', 24)];

/** An arc as the pie hands it to ECharts: the fields the legend, the tooltip and these tests read. */
interface DrawnArc {
    name: string;
    value: number;
    amount: number;
    /** The type the arc stands for: the family on inner arcs and fillers, the member itself on the outer ring, the slice's own type on a single ring. */
    rawName: string;
    /** The family the arc belongs to, as the pie resolved it. */
    primaryKey: string;
    /** Rings only. */
    caption?: string;
    ringRole?: 'base' | 'member' | 'filler';
    /** Set on the outer fillers, which ECharts never shows a tooltip for. */
    tooltip?: {show?: boolean};
    /** The arc's own fill. */
    itemStyle?: {color?: string};
}

interface Drawing {
    /** Whether the pie drew the two rings of D72 or its single ring. */
    rings: boolean;
    /** The inner ring — or the only one. */
    inner: DrawnArc[];
    /** The outer ring; empty when there is only one. */
    outer: DrawnArc[];
    /** What the inner ring writes inside `arc`: the sector's emoji, or the type's icon token. */
    insideLabelOf: (arc: DrawnArc) => string;
    /** The HTML the tooltip shows when `arc` is hovered. */
    tooltipOf: (arc: DrawnArc) => string;
}

/**
 * GET /utilities/sectors as the sector store reads it. The emoji are **invented** — no table written
 * by hand gives Technology a DNA helix — so an emoji drawn on a slice can only have come from here.
 */
const SECTOR_LIST = {
    items: [
        {key: 'Technology', emoji: '🧬'},
        {key: 'Health Care', emoji: '🧪'},
        {key: 'Financials', emoji: '🪙'},
        {key: 'Energy', emoji: '🔋'},
    ],
    buckets: [
        {key: 'Liquidity', emoji: '🫙'},
        {key: 'Unknown', emoji: '🫥'},
    ],
    fallback_emoji: '🫧',
};

/** The emoji SECTOR_LIST gives `key`: its entry, a bucket's, or the fallback. */
function listedEmoji(key: string): string {
    return [...SECTOR_LIST.items, ...SECTOR_LIST.buckets].find((entry) => entry.key === key)?.emoji ?? SECTOR_LIST.fallback_emoji;
}

/** The two themes, as the pie reads them off the `dark` class of <html> when it draws. */
const THEMES = [
    {theme: 'light', dark: false},
    {theme: 'dark', dark: true},
] as const;

/** The GR4 poles the pie shades with in `dark`: the card read through the sRGB bridge — the stand-in under jsdom, unless a reader is injected. */
function polesFor(dark: boolean) {
    return shadePoles(dark, chartRoles(dark).color('--lf-surface-card'));
}

type PieComponent = typeof import('./AllocationPieChart.svelte').default;
type Taxonomy = typeof import('$lib/utils/assetTypes');

let AllocationPieChart: PieComponent;
let K: Taxonomy;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the pie that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    K = await import('$lib/utils/assetTypes');
    AllocationPieChart = (await import('./AllocationPieChart.svelte')).default;
    sectorsEndpoint.mockResolvedValue(SECTOR_LIST);
});

beforeEach(() => {
    chartInstances.length = 0;
});

afterEach(() => {
    // Module-level state every test of the file shares: the role reader and the theme class.
    setRoleReader(null);
    document.documentElement.classList.remove('dark');
});

/** Every asset type of the generated enum, plus the cash bucket, each with a synthetic share. */
function everyType(): Slice[] {
    const types = [...K.ASSET_TYPES] as string[];
    return [...types.map((type) => slice(type, 5)), slice(CASH_BUCKET, 10)];
}

/** The label the component reads for a type, from the shipped catalogue; fails when the key does not resolve. */
function typeLabel(type: string): string {
    const key = `assets.types.${type.toUpperCase()}`;
    const label = get(_)(key);
    expect(label, `${key} does not resolve: the catalogue is not loaded, or the key is gone`).not.toBe(key);
    return label;
}

/** The caption of a split family's generic member, as the component words it: `dashboard.allocationGeneric` around the family label. */
function genericCaptionOf(type: string): string {
    const family = typeLabel(type);
    const caption = get(_)('dashboard.allocationGeneric', {values: {type: family}});
    // Barrier: the sentence resolved, carries the family, and is not the bare family label — the
    // collision it exists to avoid, which would make the check below pass on the wrong caption.
    expect(caption, 'dashboard.allocationGeneric does not resolve').not.toBe('dashboard.allocationGeneric');
    expect(caption, `the generic caption does not name the family "${family}"`).toContain(family);
    expect(caption, 'the generic caption is the bare family label').not.toBe(family);
    return caption;
}

/** Mount the pie as the Dashboard's allocation panel does, and read its first full build. */
async function drawPie(data: Slice[], mode: 'type' | 'sector' = 'type') {
    const view = render(AllocationPieChart, {props: {data, mode, legendPosition: 'bottom', currency: 'EUR'}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});
    return Object.assign(drawing(), {view});
}

/** The last full build the pie handed ECharts — the one that carries the tooltip. */
function drawing(): Drawing {
    expect(chartInstances, 'the pie did not create exactly one chart').toHaveLength(1);
    const build = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.tooltip !== undefined);
    if (!build) throw new Error('the pie never handed ECharts a full option');

    const series = build.option.series as Array<{id?: string; data: DrawnArc[]; label?: {formatter?: unknown}}>;
    const formatter = (build.option.tooltip as {formatter: (params: unknown) => string}).formatter;
    const tooltipOf = (arc: DrawnArc) => formatter({componentType: 'series', seriesType: 'pie', name: arc.name, value: arc.value, data: arc});
    const insideLabelOf = (arc: DrawnArc) => {
        const label = series[0].label?.formatter;
        if (typeof label !== 'function') throw new Error('the inner ring carries no label formatter');
        return (label as (params: unknown) => string)({componentType: 'series', seriesType: 'pie', name: arc.name, value: arc.value, data: arc});
    };

    if (series.some((entry) => entry.id === 'alloc-base')) {
        expect(series.map((entry) => entry.id)).toEqual(['alloc-base', 'alloc-outer']);
        return {rings: true, inner: series[0].data, outer: series[1].data, insideLabelOf, tooltipOf};
    }
    expect(series, 'a pie without rings draws exactly one series').toHaveLength(1);
    return {rings: false, inner: series[0].data, outer: [], insideLabelOf, tooltipOf};
}

/** The data of the series the pie last handed ECharts, full build or data-only update alike: what is on screen now. */
function latestSeriesData(): DrawnArc[][] {
    const call = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => Array.isArray(option.series));
    if (!call) throw new Error('the pie never handed ECharts a series');
    return (call.option.series as Array<{data: DrawnArc[]}>).map((entry) => entry.data);
}

/** Every `setOption` call that hands ECharts a `color` list: the palette it would paint an arc by its index with. */
function callsWithAColourList(): string[] {
    return chartInstances.flatMap((chart, index) => chart.setOptionCalls.filter(({option}) => 'color' in option).map(({option}) => `chart ${index}: ${JSON.stringify(option.color)}`));
}

function describeArc(arc: DrawnArc): string {
    return `${arc.ringRole ?? 'slice'} ${arc.rawName} in ${arc.primaryKey}`;
}

/**
 * The arc a reader hovers to read `type` itself: its member arc on the outer ring, or — for a
 * family that holds no subtype, which is not split — the family's inner arc; on a single ring,
 * its slice. Fails unless there is exactly one.
 */
function sliceOf({rings, inner, outer}: Drawing, type: string): DrawnArc {
    const same = (arc: DrawnArc) => arc.rawName.toUpperCase() === type.toUpperCase();
    const members = outer.filter((arc) => arc.ringRole === 'member');
    const found = rings ? [...members.filter(same), ...inner.filter((arc) => same(arc) && !members.some((member) => member.primaryKey === arc.primaryKey))] : inner.filter(same);
    expect(found.map(describeArc), `arcs drawn for ${type}`).toHaveLength(1);
    return found[0];
}

/** The icons a tooltip shows, in order — whichever quotes the markup uses. */
function iconsOf(html: string): string[] {
    return [...html.matchAll(/<img\b[^>]*?\bsrc=(["'])(.*?)\1/g)].map((match) => match[2]);
}

function sumOf(arcs: readonly DrawnArc[]): number {
    return arcs.reduce((sum, arc) => sum + arc.value, 0);
}

// =============================================================================
// The families are K's
// =============================================================================

describe("AllocationPieChart — the pie's families are K's (assetTypeFamily)", () => {
    it('draws real-estate crowdfunding inside the Crowdfund family: one inner arc with the sum, both members on the outer ring, and a legend entry that hides both', async () => {
        const drawn = await drawPie(CROWDFUND_CASE);

        // The family the reader sees it in — first, because it is the reason for everything below.
        expect(sliceOf(drawn, 'CROWDFUND_REAL_ESTATE').primaryKey, 'CROWDFUND_REAL_ESTATE is drawn as a family of its own, apart from the crowdfunding K files it under').toBe('CROWDFUND');

        expect(drawn.rings, 'a family holding a subtype is split on a second ring').toBe(true);
        expect(drawn.inner.map((arc) => arc.primaryKey)).toEqual(['CROWDFUND', 'BOND']);

        // One inner arc for the family, weighing both of its members.
        const [family] = drawn.inner;
        expect(family.rawName).toBe('CROWDFUND');
        expect(family.value).toBeCloseTo(55.5, 9);
        expect(family.amount).toBeCloseTo(5550, 9);

        // Both members on the outer ring: the generic one first, captioned as the generic one — its
        // own label is the family's — then the subtype under its own label.
        const members = drawn.outer.filter((arc) => arc.primaryKey === 'CROWDFUND');
        expect(members.map((arc) => `${arc.ringRole}:${arc.rawName}`)).toEqual(['member:CROWDFUND', 'member:CROWDFUND_REAL_ESTATE']);
        expect(members.map((arc) => arc.value)).toEqual([31.5, 24]);
        expect(members.map((arc) => arc.caption)).toEqual([genericCaptionOf('CROWDFUND'), typeLabel('CROWDFUND_REAL_ESTATE')]);

        // The legend lists the family once: every arc of it, on both rings, carries its label, and
        // no other arc does — so one click hides the inner arc and both members together …
        const label = typeLabel('CROWDFUND');
        expect([...drawn.inner, ...drawn.outer].filter((arc) => arc.name === label).map(describeArc)).toEqual(['base CROWDFUND in CROWDFUND', 'member CROWDFUND in CROWDFUND', 'member CROWDFUND_REAL_ESTATE in CROWDFUND']);

        // … and what is left still lines up: ECharts drops, in every series, the items named after the clicked entry.
        const inner = drawn.inner.filter((arc) => arc.name !== label);
        const outer = drawn.outer.filter((arc) => arc.name !== label);
        expect(inner.map((arc) => arc.primaryKey)).toEqual(['BOND']);
        expect(sumOf(outer), 'outer ring against inner ring, the family hidden').toBeCloseTo(sumOf(inner), 9);
    });

    it('draws every asset type of the generated enum in the family K files it under — every ETF subtype in ETF, real-estate crowdfunding in Crowdfund — and the cash bucket in a family of its own', async () => {
        const types = [...K.ASSET_TYPES] as string[];
        // Anti-vacuous: the enum was read, with both families' members and the base type both subtypes contain.
        expect(types).toEqual(expect.arrayContaining(['ETF', 'ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND', 'CROWDFUND_REAL_ESTATE', 'REAL_ESTATE', 'STOCK']));

        const drawn = await drawPie(everyType());
        expect(drawn.rings).toBe(true);

        const misfiled = [...types, CASH_BUCKET].filter((type) => sliceOf(drawn, type).primaryKey !== K.assetTypeFamily(type)).map((type) => `${type}: drawn in ${sliceOf(drawn, type).primaryKey}, K files it under ${K.assetTypeFamily(type)}`);
        expect(misfiled, 'asset types the pie draws outside the family assetTypeFamily() gives them').toEqual([]);

        // Named from K's list rather than through the function above, so a resolver that sent the
        // subtypes elsewhere *and* a K that agreed with it could not pass together.
        expect(K.ETF_SUBTYPES.filter((type) => sliceOf(drawn, type).primaryKey !== 'ETF')).toEqual([]);

        // The inner ring holds K's families, each exactly once — the cash bucket among them, upper-cased like every family key.
        const families = [...new Set([...types, CASH_BUCKET].map((type) => K.assetTypeFamily(type)))];
        expect(families).toContain('LIQUIDITY');
        expect(drawn.inner.map((arc) => arc.primaryKey).sort()).toEqual(families.sort());
    });

    it("keeps each family's generic member as its generic member — the plain ETF and the plain Crowdfund, captioned as the generic one", async () => {
        const types = [...K.ASSET_TYPES] as string[];
        // The containers are read off K: the families that hold a member other than themselves.
        const containers = [...new Set(types.map((type) => K.assetTypeFamily(type)))].filter((family) => types.some((type) => type !== family && K.assetTypeFamily(type) === family));
        expect(containers).toEqual(expect.arrayContaining(['ETF', 'CROWDFUND']));

        const drawn = await drawPie(everyType());

        const problems = containers.flatMap((family) => {
            const arc = sliceOf(drawn, family);
            if (arc.ringRole !== 'member' || arc.primaryKey !== family) return [`${family}: drawn as ${describeArc(arc)}, not as the generic member of its family`];
            const expected = genericCaptionOf(family);
            return arc.caption === expected ? [] : [`${family}: captioned "${arc.caption}", expected "${expected}"`];
        });
        expect(problems).toEqual([]);
    });
});

// =============================================================================
// The tooltip — one icon, the type's own
// =============================================================================

describe("AllocationPieChart — the tooltip titles each arc with the type's own icon", () => {
    it('shows exactly one icon on every arc a reader can hover, the one getAssetTypeIconUrl() gives its type — for every asset type of the generated enum and the cash bucket', async () => {
        const types = [...K.ASSET_TYPES] as string[];
        const drawn = await drawPie(everyType());
        const hoverable = [...drawn.inner, ...drawn.outer].filter((arc) => arc.tooltip?.show !== false);

        // Barrier: every type is titled by at least one hoverable arc, so no type below is checked on nothing.
        const titled = new Set(hoverable.map((arc) => arc.rawName.toUpperCase()));
        expect(
            [...types, CASH_BUCKET.toUpperCase()].filter((type) => !titled.has(type)),
            'types no hoverable arc stands for',
        ).toEqual([]);

        const wrong = hoverable
            .map((arc) => ({arc, icons: iconsOf(drawn.tooltipOf(arc))}))
            .filter(({arc, icons}) => icons.length !== 1 || icons[0] !== K.getAssetTypeIconUrl(arc.rawName))
            .map(({arc, icons}) => `${describeArc(arc)}: shows ${JSON.stringify(icons)}, expected ["${K.getAssetTypeIconUrl(arc.rawName)}"]`);
        expect(wrong, "tooltips that do not show their type's own icon, once").toEqual([]);
    });

    it("titles every subtype with a picture of its own — never its family's, never the fallback — so the single icon above still says what the subtype holds", async () => {
        const types = [...K.ASSET_TYPES] as string[];
        const subtypes = types.filter((type) => K.assetTypeFamily(type) !== type);
        // Anti-vacuous: both families' subtypes are here, the one K2 keeps as itself included.
        expect(subtypes).toEqual(expect.arrayContaining(['ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE']));

        const drawn = await drawPie(everyType());
        const fallback = K.getAssetTypeIconUrl('NOT_AN_ASSET_TYPE');
        const familyArc = (family: string) => {
            const found = drawn.inner.filter((arc) => arc.primaryKey === family);
            expect(found.map(describeArc), `inner arcs of ${family}`).toHaveLength(1);
            return found[0];
        };

        const problems = subtypes.flatMap((type) => {
            const own = iconsOf(drawn.tooltipOf(sliceOf(drawn, type)));
            const family = iconsOf(drawn.tooltipOf(familyArc(K.assetTypeFamily(type))));
            if (own.length === 0) return [`${type}: its tooltip shows no icon`];
            if (own.includes(fallback)) return [`${type}: its tooltip shows the fallback icon ${fallback}`];
            const shared = own.filter((icon) => family.includes(icon));
            return shared.length === 0 ? [] : [`${type}: its tooltip shows ${JSON.stringify(shared)}, the icon of its family ${K.assetTypeFamily(type)}`];
        });
        expect(problems, "subtypes whose tooltip picture is their family's or the fallback: the composite that carries what they hold is missing").toEqual([]);
    });
});

// =============================================================================
// GR1 and GR4 — every family in its own colour, every subtype a shade of it
// =============================================================================

/** Four families with no subtype, heaviest first: one ring, every family a group of one. */
const SINGLETONS: Slice[] = [slice('STOCK', 40), slice('BOND', 30), slice('CRYPTO', 20), slice('COMMODITY', 10)];

/** The ETF family split by two subtypes (60 in all), beside a plain family and the engine's cash bucket: two rings. */
const ETF_FAMILY: Slice[] = [slice('ETF', 30), slice('BOND', 25), slice('ETF_STOCK', 20), slice(CASH_BUCKET, 15), slice('ETF_BOND', 10)];

/** The fill of every arc, with what it stands for: one line each, so a red names the arc. */
function fills(arcs: readonly DrawnArc[]): string[] {
    return arcs.map((arc) => `${arc.ringRole ?? 'slice'} ${arc.rawName} ${arc.itemStyle?.color}`);
}

describe('AllocationPieChart — every family in its own colour (GR1), every subtype a shade of it (GR4)', () => {
    it.each(THEMES)('$theme theme, one ring: each arc in categoryColor of its type — by key, so a re-ranking through the data-only update moves no colour', async ({dark}) => {
        document.documentElement.classList.toggle('dark', dark);
        const drawn = await drawPie(SINGLETONS);
        expect(drawn.rings, 'families without a subtype are drawn on one ring').toBe(false);
        expect(fills(drawn.inner)).toEqual(SINGLETONS.map(({name}) => `slice ${name} ${categoryColor('type', name, dark)}`));

        // The same families ranked the other way round, on the same chart: the data-only update (same
        // theme, locale and set of types).
        const reversed = SINGLETONS.map(({name}, index) => slice(name, SINGLETONS[SINGLETONS.length - 1 - index].value));
        const [chart] = chartInstances;
        const before = chart.setOptionCalls.length;
        await drawn.view.rerender({data: reversed});
        await waitFor(() => expect(chart.setOptionCalls.length, 'the pie did not redraw the new data').toBeGreaterThan(before));
        const [now] = latestSeriesData();
        // Barrier: the ranks really moved, so a colour handed out by rank would have moved with them.
        expect(now.map((arc) => arc.rawName)).toEqual([...SINGLETONS].reverse().map(({name}) => name));
        expect(fills(now)).toEqual([...SINGLETONS].reverse().map(({name}) => `slice ${name} ${categoryColor('type', name, dark)}`));

        expect(callsWithAColourList(), 'an option handing ECharts a palette to paint an arc by its index').toEqual([]);
    });

    it.each(THEMES)('$theme theme, two rings: base arcs and the generic member in categoryColor of their family, each subtype the familyShade of its rank, fillers transparent', async ({dark}) => {
        document.documentElement.classList.toggle('dark', dark);
        const drawn = await drawPie(ETF_FAMILY);
        expect(drawn.rings, 'a family holding a subtype is split on a second ring').toBe(true);

        const etf = categoryColor('type', 'ETF', dark);
        const poles = polesFor(dark);
        expect(fills(drawn.inner)).toEqual(['ETF', 'BOND', 'LIQUIDITY'].map((family) => `base ${family} ${categoryColor('type', family, dark)}`));
        expect(fills(drawn.outer)).toEqual([`member ETF ${etf}`, `member ETF_STOCK ${familyShade(etf, 1, poles)}`, `member ETF_BOND ${familyShade(etf, 2, poles)}`, 'filler BOND transparent', 'filler LIQUIDITY transparent']);
        // The engine spells the cash bucket in Title Case; its family wears the Liquidity colour.
        expect(drawn.inner.find((arc) => arc.primaryKey === 'LIQUIDITY')?.itemStyle?.color).toBe(categoryColor('type', CASH_BUCKET, dark));

        expect(callsWithAColourList(), 'an option handing ECharts a palette to paint an arc by its index').toEqual([]);
    });

    it("dark theme: the shades take the card the pie is drawn on, read through the bridge from the pie's own element", async () => {
        const standInCard = chartRoles(true).color('--lf-surface-card');
        // A card of its own, answered only for the pie's element: a shade made from any other read — <html>, a
        // stand-in, a literal — would differ.
        const CARD = '#2a1f3d';
        const scopes: Array<Element | null> = [];
        setRoleReader((role, scope) => {
            scopes.push(scope);
            return role === '--lf-surface-card' && scope !== null && scope === chartInstances[0]?.getDom() ? CARD : '';
        });
        document.documentElement.classList.add('dark');

        const drawn = await drawPie(ETF_FAMILY);

        // The ETF's colour is a role since DV-11: read on the pie's element, as the pie reads it.
        const etf = categoryColor('type', 'ETF', true, chartInstances[0].getDom() as Element);
        const shadesOn = (card: string) => [1, 2].map((rank) => familyShade(etf, rank, shadePoles(true, card)));
        // Control: this card moves the shades, so the comparison below cannot pass on the stand-in.
        expect(shadesOn(CARD)).not.toEqual(shadesOn(standInCard));
        expect(drawn.outer.filter((arc) => arc.ringRole === 'member' && arc.rawName !== 'ETF').map((arc) => arc.itemStyle?.color)).toEqual(shadesOn(CARD));
        expect(scopes.length, 'the pie never read a role').toBeGreaterThan(0);
        expect(
            scopes.filter((scope) => scope !== chartInstances[0].getDom()).map((scope) => scope?.nodeName ?? 'null'),
            "roles read from another element than the pie's own",
        ).toEqual([]);
    });
});

// =============================================================================
// The sector pie — its colours by key, its emoji from the sector store
// =============================================================================

/**
 * Why: the header, "Every category in its own colour (GR1), the sector emoji from the sector store".
 *
 * Order matters in this block, and the first test says so: the sector store loads once per module,
 * so the first sector pie of the file is the only one that can see it arrive. It checks that it is.
 */
describe('AllocationPieChart — the sector pie: each sector in its own colour, its emoji from the sector store', () => {
    /** Listed sectors, the cash bucket and a key the list does not name, in no particular order. */
    const SECTORS_AND_BUCKETS: Slice[] = [slice('Health Care', 20), slice('Technology', 35), slice(CASH_BUCKET, 10), slice('Quantum Computing', 5), slice('Energy', 30)];

    it('draws first without emoji, then rebuilds in full when the sector list arrives: each name led by the emoji the list gives its key', async () => {
        // Premise: the store has never loaded, and nobody has asked for the list yet.
        expect(sectorsEndpoint, 'precondition: the sector list was requested before this test, which must run before any other sector pie of the file').not.toHaveBeenCalled();
        expect(sectorEmojiVersion(), 'precondition: the sector store has already loaded').toBe(0);
        expect(getSectorEmoji('Technology'), 'precondition: an emoji is known before the list arrived').toBe('');

        let release: (list: typeof SECTOR_LIST) => void = () => {};
        sectorsEndpoint.mockImplementationOnce(() => new Promise((resolve) => (release = resolve)));

        const first = await drawPie(SECTORS_AND_BUCKETS, 'sector');
        expect(sectorsEndpoint, 'the sector pie did not ask for the sector list').toHaveBeenCalledTimes(1);
        // Before the list: no emoji in front of a name, none drawn inside a slice.
        expect(first.inner.filter((arc) => first.insideLabelOf(arc) !== '').map((arc) => arc.name)).toEqual([]);
        expect(first.inner.filter((arc) => [...SECTOR_LIST.items, ...SECTOR_LIST.buckets].some(({emoji}) => arc.name.includes(emoji))).map((arc) => arc.name)).toEqual([]);
        const names = new Map(first.inner.map((arc) => [arc.rawName, arc.name]));

        const [chart] = chartInstances;
        const before = chart.setOptionCalls.length;
        release(SECTOR_LIST);

        // The list redraws the pie in full: its names change, so the data-only update would not do.
        await waitFor(() => expect(chart.setOptionCalls.slice(before).filter(({option}) => option.tooltip !== undefined && option.legend !== undefined).length, 'no full build followed the sector list').toBeGreaterThan(0));
        const after = drawing();
        expect(after.inner.map((arc) => arc.name)).toEqual(after.inner.map((arc) => `${listedEmoji(arc.rawName)} ${names.get(arc.rawName)}`));
        expect(after.inner.map((arc) => after.insideLabelOf(arc))).toEqual(after.inner.map((arc) => listedEmoji(arc.rawName)));
        expect(chartInstances, 'the list made a new chart').toHaveLength(1);
    });

    it('takes each emoji from the sector list, never from the data: slices that bring an emoji of their own still wear the list’s', async () => {
        // The data used to carry an emoji (`AllocationEntry.emoji`, removed): a pie still reading it would draw 🦄.
        const withOwnEmoji = SECTORS_AND_BUCKETS.map((entry) => ({...entry, emoji: '🦄'}));
        await drawPie(withOwnEmoji, 'sector');

        // The list may still be on its way when this test runs alone: wait for the build it brings.
        await waitFor(() => expect(drawing().inner.map((arc) => arc.name.split(' ')[0])).toEqual(drawing().inner.map((arc) => listedEmoji(arc.rawName))));
        const drawn = drawing();
        expect(drawn.inner.map((arc) => drawn.insideLabelOf(arc))).toEqual(drawn.inner.map((arc) => listedEmoji(arc.rawName)));
        // Barrier: the bucket and the unlisted key are among them — their own emoji and the list's fallback.
        expect(drawn.inner.map((arc) => arc.rawName)).toEqual(expect.arrayContaining([CASH_BUCKET, 'Quantum Computing']));
        expect(JSON.stringify(chartInstances[0].setOptionCalls.map(({option}) => option.series)), 'the data’s own emoji reached the chart').not.toContain('🦄');
    });

    it.each(THEMES)('$theme theme: every slice in categoryColor("sector", its key), sorted by value — the cash bucket and an unlisted key included', async ({dark}) => {
        document.documentElement.classList.toggle('dark', dark);
        const drawn = await drawPie(SECTORS_AND_BUCKETS, 'sector');

        const byValue = [...SECTORS_AND_BUCKETS].sort((left, right) => right.value - left.value);
        expect(fills(drawn.inner)).toEqual(byValue.map(({name}) => `slice ${name} ${categoryColor('sector', name, dark)}`));
        expect(callsWithAColourList(), 'an option handing ECharts a palette to paint a slice by its index').toEqual([]);
    });
});

// =============================================================================
// Redrawn in full when its colours change (C4) or its theme does
// =============================================================================

describe('AllocationPieChart — redrawn in full when its colours change (C4) or its theme does', () => {
    it('notifyChartColorsChange() hands ECharts the whole option — legend and tooltip, never the data-only update — with the roles read again', async () => {
        const standInCard = chartRoles(true).color('--lf-surface-card');
        const FIRST_CARD = '#2a1f3d';
        const NEXT_CARD = '#1f3d2a';
        let card = FIRST_CARD;
        setRoleReader((role, scope) => (role === '--lf-surface-card' && scope !== null && scope === chartInstances[0]?.getDom() ? card : ''));
        document.documentElement.classList.add('dark');

        await drawPie(ETF_FAMILY);
        const [chart] = chartInstances;
        const etf = categoryColor('type', 'ETF', true);
        const shadesOn = (onCard: string) => [1, 2].map((rank) => familyShade(etf, rank, shadePoles(true, onCard)));
        const drawnShades = () =>
            drawing()
                .outer.filter((arc) => arc.ringRole === 'member' && arc.rawName !== 'ETF')
                .map((arc) => arc.itemStyle?.color);
        // Control: the two cards and the stand-in give three different pairs of shades.
        expect(new Set([FIRST_CARD, NEXT_CARD, standInCard].map((onCard) => shadesOn(onCard).join(' '))).size).toBe(3);
        expect(drawnShades()).toEqual(shadesOn(FIRST_CARD));

        card = NEXT_CARD;
        const before = chart.setOptionCalls.length;
        // Nothing redraws by itself: a role is read when the option is built, and only the signal says it changed.
        flushSync();
        await tick();
        expect(chart.setOptionCalls.length, 'the pie redrew without being told its colours changed').toBe(before);

        notifyChartColorsChange();

        const since = chart.setOptionCalls.slice(before);
        expect(since.length, 'no setOption followed the notification').toBeGreaterThan(0);
        expect(
            since.map(({option}) => ['legend', 'tooltip'].filter((key) => key in option).join('+')),
            'a call after the notification that is not a full option: the data-only update',
        ).toEqual(since.map(() => 'legend+tooltip'));
        expect(drawnShades(), 'the shades of the new card').toEqual(shadesOn(NEXT_CARD));
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
    });

    it('a theme switch on <html> redraws in full, each family now in its colour for the other theme', async () => {
        const drawn = await drawPie(SINGLETONS);
        expect(fills(drawn.inner)).toEqual(SINGLETONS.map(({name}) => `slice ${name} ${categoryColor('type', name, false)}`));
        const [chart] = chartInstances;
        const before = chart.setOptionCalls.length;

        document.documentElement.classList.add('dark');

        await waitFor(() =>
            expect(
                chart.setOptionCalls.slice(before).some(({option}) => option.tooltip !== undefined),
                'no full build followed the theme switch',
            ).toBe(true),
        );
        expect(fills(drawing().inner)).toEqual(SINGLETONS.map(({name}) => `slice ${name} ${categoryColor('type', name, true)}`));
    });
});

// =============================================================================
// M-18 — redrawn in the interface language
// =============================================================================

/**
 * M-18 CP2: a switch of the UI language redraws the pie, and the figures it writes follow it.
 *
 * ECharts runs a formatter only while painting, and paints only when it is handed an option: a pie
 * that is not redrawn keeps everything it was drawn with. The render effect tracks the data alone,
 * so a language switch hands ECharts nothing. Every figure is written in the interface language (the
 * developer's decision M-18, 2026-10-12), and every effect that calls `setOption` reads `uiLocale()`,
 * so a switch redraws the pie on the same instance.
 *
 * The amount under each arc's name in the tooltip (`formatCurrencyAmountPlain`) follows the interface
 * language too: after a switch to Italian, `12.345,67` where English writes `12,345.67`.
 *
 * The percentages the pie prints by interpolating the number — an arc's in its tooltip, sector or type,
 * the family line `↳ …` under a member, the outer ring's captions — become `formatPercent(value,
 * {digits: 2, signed: false, trim: true})`: the decimals the figure has, up to two, in the interface
 * locale. `44.5%` and `24%` in English, as today; `44,5%` and `24%` in Italian.
 *
 * And the switch rebuilds the pie in full. A data-only update (the fast path, for an unchanged theme
 * and type set) hands ECharts the Italian names but keeps the legend formatter of the English build,
 * whose name lookup misses them and falls back to a key of its own: `assets.types.OBBLIGAZIONI`.
 *
 * Read: the `setOption` calls on the one instance; the tooltip of the latest full build, called as
 * ECharts calls it on hover; the outer captions and the legend through the formatters ECharts paints
 * with. A legend is painted when ECharts is handed an option — svelte-i18n's `$_` answers in the
 * language current when it is called, so a formatter called later would say what ECharts never
 * painted. Expectations come from `Intl` in an explicit locale, and labels from the catalogue.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set`, which also drives svelte-i18n —
 * with both dictionaries loaded; the `afterEach` puts English back.
 */
describe('AllocationPieChart — redrawn in the interface language (M-18)', {timeout: 15_000}, () => {
    /** Two types with no subtype — one ring — whose amounts are above ten thousand, so both separators are read in both languages. */
    const SLICES: Slice[] = [
        {name: 'BOND', value: 44.5, amount: 12_345.67},
        {name: 'STOCK', value: 55.5, amount: 15_396.21},
    ];
    const BOND_AMOUNT = 12_345.67;

    /** Two sectors, one ring: the sector tooltip's own template. */
    const SECTORS: Slice[] = [
        {name: 'Technology', value: 44.5, amount: 12_345.67},
        {name: 'Health Care', value: 55.5, amount: 15_396.21},
    ];

    /** The UI languages read, with the interface locale each gives on jsdom's en-US browser. Titles stay short: Vitest cuts `$title` at 40 characters. */
    const LANGUAGES = [
        {lang: 'en', locale: 'en-US'},
        {lang: 'it', locale: 'it'},
    ] as const;

    /** The amount's digits as the currency format writes them in `localeTag`: two decimals. */
    const digitsIn = (amount: number, localeTag: string) => amount.toLocaleString(localeTag, {minimumFractionDigits: 2, maximumFractionDigits: 2});

    /** A percentage as the pie must write it in `localeTag`: the decimals it has, up to two, after `toFixed(2)` — `formatPercent` with `trim`. */
    const percentIn = (value: number, localeTag: string) => new Intl.NumberFormat(localeTag, {style: 'percent', minimumFractionDigits: 0, maximumFractionDigits: 2}).format(Number(value.toFixed(2)) / 100);

    /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
    async function switchLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    /** Mount the sector pie as the Asset Detail page does, and read its first full build. */
    async function drawSectorPie(data: Slice[]): Promise<Drawing> {
        render(AllocationPieChart, {props: {data, mode: 'sector', legendPosition: 'bottom', currency: 'EUR'}});
        await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});
        return drawing();
    }

    /** The latest `setOption` call carrying `key`, newest first. */
    function latestCallWith(key: 'legend' | 'series' | 'tooltip') {
        expect(chartInstances, 'the pie did not create exactly one chart').toHaveLength(1);
        return [...chartInstances[0].setOptionCalls].reverse().find(({option}) => (key === 'series' ? Array.isArray(option.series) : option[key] !== undefined));
    }

    /** The caption the outer ring draws beside `arc`, through the label formatter of the latest full build. */
    function outerCaptionOf(arc: DrawnArc): string {
        const series = latestCallWith('tooltip')?.option.series as Array<{id?: string; label?: {formatter?: unknown}}> | undefined;
        const formatter = series?.find((entry) => entry.id === 'alloc-outer')?.label?.formatter;
        if (typeof formatter !== 'function') throw new Error('the outer ring carries no caption formatter');
        return (formatter as (params: unknown) => string)({componentType: 'series', seriesType: 'pie', name: arc.name, value: arc.value, data: arc});
    }

    /** The percentage an arc's tooltip prints after the arc's name: what follows `: ` up to the `%`. */
    function arcPercentIn(html: string): string {
        return /: ([^<]*%)/.exec(html)?.[1] ?? `(no percentage after the arc's name in ${html})`;
    }

    /**
     * What the legend shows now: each name the latest series data carries, through the legend formatter of
     * the latest build that carried one — what ECharts paints after merging the last option it was handed.
     * The rich-text token in front (`{img_BOND|}`) draws the icon; the text after it is what a reader reads.
     */
    function legendNow(): {raw: string[]; visible: string[]} {
        const formatter = (latestCallWith('legend')?.option.legend as {formatter?: unknown} | undefined)?.formatter;
        if (typeof formatter !== 'function') throw new Error('the type legend carries no formatter');
        const data = (latestCallWith('series')?.option.series as Array<{data?: Array<{name: string}>}> | undefined)?.[0]?.data ?? [];
        const raw = data.map(({name}) => (formatter as (name: string) => string)(name));
        return {raw, visible: raw.map((text) => text.replace(/\{[^{}|]*\|[^{}]*\}/g, '').trim()).sort()};
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; Italian joins it, so a switch never waits on a loader.
        await waitLocale('it');
        // Controls: this runtime has Italian data, so the Italian amount and percentage are not the English ones.
        expect(digitsIn(BOND_AMOUNT, 'it'), 'Italian differs from English').not.toBe(digitsIn(BOND_AMOUNT, 'en-US'));
        expect(percentIn(44.5, 'it'), 'an Italian percentage differs from English').not.toBe(percentIn(44.5, 'en-US'));
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('a switch of the UI language redraws the pie: setOption is called again after the switch, on the same instance', async () => {
        await drawPie(SLICES);
        const [chart] = chartInstances;
        const before = chart.setOptionCalls.length;

        await switchLanguage('it');
        // A redraw is one `tick()` away: two seconds are generous, and shorter than the case's budget,
        // so a missing redraw fails on this assertion rather than on the test timeout.
        await waitFor(() => expect(chart.setOptionCalls.length, 'no setOption followed the switch to Italian').toBeGreaterThan(before), {timeout: 2_000});
        expect(chartInstances, 'the switch redrew the same chart').toHaveLength(1);
    });

    it('after a switch to Italian, the amount its tooltip writes is Italian', async () => {
        const drawn = await drawPie(SLICES);
        // Control: drawn under the English UI, the amount reads as en-US writes it.
        expect(drawn.tooltipOf(sliceOf(drawn, 'BOND'))).toContain(digitsIn(BOND_AMOUNT, 'en-US'));

        await switchLanguage('it');
        const after = drawing();
        const html = after.tooltipOf(sliceOf(after, 'BOND'));
        expect(html, 'the amount in Italian notation').toContain(digitsIn(BOND_AMOUNT, 'it'));
        expect(html, 'no English amount left').not.toContain(digitsIn(BOND_AMOUNT, 'en-US'));
    });

    it.each(LANGUAGES)('$lang UI: the type pie’s percentages — an arc’s, its family’s, an outer caption’s — in $locale, with the decimals they have', async ({lang, locale: localeTag}) => {
        // WHY: the pie interpolates its percentages (`${params.value}%`), so they carry a point in every
        // language. Catches each of the three sites left raw: an arc's tooltip, the `↳` family line under a
        // member of a split family, and the outer ring's caption. The English UI is the control: today's
        // text, which is also the trimmed text of the rule.
        await switchLanguage(lang);
        const drawn = await drawPie(CROWDFUND_CASE);
        // Precondition: the family holding a subtype is split on a second ring, so all three sites are drawn.
        expect(drawn.rings, 'a family holding a subtype is split on a second ring').toBe(true);
        const generic = sliceOf(drawn, 'CROWDFUND');
        const subtypeTooltip = drawn.tooltipOf(sliceOf(drawn, 'CROWDFUND_REAL_ESTATE'));

        const read = {
            arc: arcPercentIn(drawn.tooltipOf(sliceOf(drawn, 'BOND'))),
            family: /↳ ([^<]*)</.exec(subtypeTooltip)?.[1] ?? `(no family line in ${subtypeTooltip})`,
            caption: outerCaptionOf(generic),
        };
        // BOND weighs 44.5, the Crowdfund family 31.5 + 24 = 55.5, its generic member 31.5.
        expect(read).toEqual({
            arc: percentIn(44.5, localeTag),
            family: `${typeLabel('CROWDFUND')} ${percentIn(55.5, localeTag)}`,
            caption: `${generic.caption}\n${percentIn(31.5, localeTag)}`,
        });
    });

    it.each(LANGUAGES)('$lang UI: the sector pie’s tooltip percentage in $locale, with the decimals it has', async ({lang, locale: localeTag}) => {
        // WHY: the sector tooltip is a template of its own (`${name}: ${params.value}%`), so a cure of the
        // type tooltip alone leaves it with a point.
        await switchLanguage(lang);
        const drawn = await drawSectorPie(SECTORS);
        const technology = drawn.inner.filter((arc) => arc.rawName === 'Technology');
        expect(technology, 'one arc for Technology').toHaveLength(1);

        expect(arcPercentIn(drawn.tooltipOf(technology[0]))).toBe(percentIn(44.5, localeTag));
    });

    it('after a switch to Italian, the pie is rebuilt in full: its legend reads the Italian names, never a raw key', async () => {
        // WHY: a pie not redrawn keeps the English legend ECharts painted; a data-only update hands ECharts
        // the Italian names and keeps the English build's legend formatter, which misses them and paints a
        // key it derives, `assets.types.OBBLIGAZIONI`. Only a full rebuild gives the legend a formatter that
        // knows the names it is handed. Catches both: the switch must end with the legend in Italian.
        await drawPie(SLICES);
        const [chart] = chartInstances;
        const english = ['BOND', 'STOCK'].map(typeLabel).sort();
        const painted = legendNow();
        expect(painted.visible, 'control: drawn in English, the English names').toEqual(english);

        const before = chart.setOptionCalls.length;
        await switchLanguage('it');
        const italian = ['BOND', 'STOCK'].map(typeLabel).sort();
        expect(italian, 'control: the Italian names differ from the English ones').not.toEqual(english);

        await waitFor(
            () => {
                // ECharts paints a legend when it is handed an option: with none since the switch, the
                // legend still shows what it was painted with.
                const shown = chart.setOptionCalls.length > before ? legendNow() : painted;
                expect(shown.raw.join(' | '), 'a raw catalogue key in the legend').not.toContain('assets.types.');
                expect(shown.visible, 'the legend after the switch to Italian').toEqual(italian);
            },
            {timeout: 2_000},
        );
    });
});

// =============================================================================
// The asset pie (Y5-2, #48) — one slice per asset, coloured by the asset's weight rank
// =============================================================================

/**
 * The «By Asset» tab of the allocation panel draws this pie in `mode="asset"`: one ring, one slice per asset, sorted by
 * value, the name as the backend sent it (an asset's name is nobody's translation key: `ETF` and `ETF_STOCK` here are
 * assets, not types, and must neither be translated nor folded into a family with a second ring).
 *
 * The colour of an asset is not a function of its name but of its rank (`colorRanks`, asset id -> 0 for the heaviest
 * held asset): the rank-th colour of the designer's sequence, `sequenceColor(CATEGORY_SEQUENCE, rank, …)`, so the pie, the
 * history and the lines of the Dashboard agree. The cash slice (`Liquidity`, no id) keeps the type colour of the cash.
 * The expectations call the same exported colour functions as the component, with the pie's own element as scope.
 */
describe('AllocationPieChart — the asset pie: one ring, the asset names as sent, each slice in the colour of its rank', () => {
    /** An entry of the asset pie: `id` is the asset's; the cash slice has none. */
    interface AssetSlice extends Slice {
        id?: number | null;
    }
    const assetSlice = (name: string, value: number, id: number | null): AssetSlice => ({...slice(name, value), id});

    /** An asset named like a type, a subtype of it, a sector and the cash, listed out of value order. Value order: ETF, ETF_STOCK, Technology, Liquidity. */
    const ASSETS: AssetSlice[] = [assetSlice('Technology', 20, 33), assetSlice('ETF_STOCK', 30, 32), assetSlice(CASH_BUCKET, 10, null), assetSlice('ETF', 40, 31)];
    /** Ranks that follow neither the list order nor the value order, so a colour handed out by position would show. */
    const RANKS = new Map<number, number>([
        [31, 2],
        [32, 0],
        [33, 5],
    ]);

    async function drawAssetPie(data: AssetSlice[], colorRanks: ReadonlyMap<number, number> = RANKS) {
        const props = {data, mode: 'asset', legendPosition: 'bottom', currency: 'EUR', colorRanks} as unknown as ComponentProps<PieComponent>;
        const view = render(AllocationPieChart, {props});
        await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});
        return Object.assign(drawing(), {view});
    }

    /** The pie's own element, which the colours are read on. */
    const container = (): Element => chartInstances[0].getDom() as Element;
    const poles = (dark: boolean) => shadePoles(dark, chartRoles(dark, container()).color('--lf-surface-card'));
    const rankColour = (rank: number, dark: boolean) => sequenceColor(CATEGORY_SEQUENCE, rank, dark, poles(dark), container());

    it('draws one ring, sorted by value, the names, values and amounts as sent — an asset named ETF or ETF_STOCK is neither translated nor split into rings', async () => {
        const drawn = await drawAssetPie(ASSETS);

        expect(drawn.rings, 'a pie of assets has a single ring').toBe(false);
        expect(drawn.inner.map(({name, value, amount}) => ({name, value, amount}))).toEqual([
            {name: 'ETF', value: 40, amount: 4000},
            {name: 'ETF_STOCK', value: 30, amount: 3000},
            {name: 'Technology', value: 20, amount: 2000},
            {name: CASH_BUCKET, value: 10, amount: 1000},
        ]);
    });

    it.each(THEMES)('$theme theme: an asset takes the colour of its rank in the designer’s sequence, not of its position; the cash keeps the colour of the Liquidity type', async ({dark}) => {
        document.documentElement.classList.toggle('dark', dark);
        const drawn = await drawAssetPie(ASSETS);
        const colourOf = new Map(drawn.inner.map((arc) => [arc.name, arc.itemStyle?.color]));

        expect({ETF: colourOf.get('ETF'), ETF_STOCK: colourOf.get('ETF_STOCK'), Technology: colourOf.get('Technology')}).toEqual({ETF: rankColour(2, dark), ETF_STOCK: rankColour(0, dark), Technology: rankColour(5, dark)});
        expect(colourOf.get(CASH_BUCKET)).toBe(categoryColor('type', 'Liquidity', dark, container()));
        // Control: the three ranks are three colours, so "by rank" cannot pass as "one colour for all".
        expect(new Set([2, 0, 5].map((rank) => rankColour(rank, dark))).size).toBe(3);
        expect(callsWithAColourList(), 'an option handing ECharts a palette to paint a slice by its index').toEqual([]);
    });

    it('ranks 0 to 7 are categoryColor of the sequence’s eight types; the ranks past it are the sequence one shade further, never a repeat', async () => {
        const ranks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];
        const many = ranks.map((rank) => assetSlice(`Asset ${rank}`, 50 - rank, 100 + rank));
        const drawn = await drawAssetPie(many, new Map(ranks.map((rank) => [100 + rank, rank])));
        const colours = drawn.inner.map((arc) => arc.itemStyle?.color);

        expect(CATEGORY_SEQUENCE).toHaveLength(8);
        expect(colours.slice(0, 8)).toEqual(CATEGORY_SEQUENCE.map(({kind, key}) => categoryColor(kind, key, false, container())));
        expect(colours.slice(8)).toEqual([rankColour(8, false), rankColour(9, false)]);
        expect(new Set(colours).size, 'two assets in one colour').toBe(ranks.length);
    });
});
