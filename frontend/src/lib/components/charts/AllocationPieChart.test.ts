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
 * ## The palette is the one its colour tests measure
 *
 * `colors.test.ts`, `allocationHierarchy.test.ts` and `allocationRings.test.ts` measure the pie's
 * colours on `ALLOCATION_PIE_PALETTE`, imported from `$lib/theme/chartPalettes`. Their measures are
 * about this chart only while it draws that palette — a copy back in the component, or the other
 * theme's list, would leave all three green — so one block here mounts the pie in each theme and
 * compares what it hands ECharts with the palette of that theme.
 *
 * ## What is not asserted
 *
 * No translated word: labels and the generic caption are resolved from the shipped catalogue,
 * through the same `$_` and the same keys the component calls. Colours beyond the palette binding
 * are the subject of `allocationRings.test.ts` and `allocationHierarchy.test.ts`. Every value and
 * amount is synthetic.
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

import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {locale, waitLocale} from 'svelte-i18n';

import {render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {ALLOCATION_PIE_PALETTE} from '$lib/theme/chartPalettes';

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
    /** The option's `color`: the list ECharts paints an arc that carries no fill of its own with. */
    color: unknown;
    /** The HTML the tooltip shows when `arc` is hovered. */
    tooltipOf: (arc: DrawnArc) => string;
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
});

beforeEach(() => {
    chartInstances.length = 0;
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
async function drawPie(data: Slice[]): Promise<Drawing> {
    render(AllocationPieChart, {props: {data, mode: 'type', legendPosition: 'bottom', currency: 'EUR'}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0).toBeGreaterThan(0), {timeout: 5_000});
    return drawing();
}

/** The last full build the pie handed ECharts — the one that carries the tooltip. */
function drawing(): Drawing {
    expect(chartInstances, 'the pie did not create exactly one chart').toHaveLength(1);
    const build = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.tooltip !== undefined);
    if (!build) throw new Error('the pie never handed ECharts a full option');

    const series = build.option.series as Array<{id?: string; data: DrawnArc[]}>;
    const formatter = (build.option.tooltip as {formatter: (params: unknown) => string}).formatter;
    const tooltipOf = (arc: DrawnArc) => formatter({componentType: 'series', seriesType: 'pie', name: arc.name, value: arc.value, data: arc});
    const color = build.option.color;

    if (series.some((entry) => entry.id === 'alloc-base')) {
        expect(series.map((entry) => entry.id)).toEqual(['alloc-base', 'alloc-outer']);
        return {rings: true, inner: series[0].data, outer: series[1].data, color, tooltipOf};
    }
    expect(series, 'a pie without rings draws exactly one series').toHaveLength(1);
    return {rings: false, inner: series[0].data, outer: [], color, tooltipOf};
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
// The palette — the one the colour tests measure
// =============================================================================

/**
 * Why: the header, "The palette is the one its colour tests measure".
 *
 * Mounted on families without a subtype: one ring, every family a group of one, so each arc wears the palette entry
 * of its rank verbatim (the hierarchy's legacy pin). Read: each arc's fill, and the option's `color` — the list
 * ECharts paints an arc without a fill of its own with, every arc of the sector pie — whole.
 */
describe('AllocationPieChart — draws ALLOCATION_PIE_PALETTE, the palette its colour tests measure', () => {
    /** Four families with no subtype, heaviest first: the order their arcs take. */
    const SINGLETONS: Slice[] = [slice('STOCK', 40), slice('BOND', 30), slice('CRYPTO', 20), slice('COMMODITY', 10)];

    it.each([
        ['light', ALLOCATION_PIE_PALETTE.light],
        ['dark', ALLOCATION_PIE_PALETTE.dark],
    ] as const)('%s theme: each arc in the entry of its rank in that theme’s list, and the whole list handed to ECharts', async (theme, palette) => {
        // Control: the two lists differ on the slots drawn, so a pie deaf to the theme fails one of the two rows.
        expect(ALLOCATION_PIE_PALETTE.dark.slice(0, SINGLETONS.length)).not.toEqual(ALLOCATION_PIE_PALETTE.light.slice(0, SINGLETONS.length));

        // The pie reads the theme off the `dark` class of <html> when it draws.
        document.documentElement.classList.toggle('dark', theme === 'dark');
        try {
            const drawn = await drawPie(SINGLETONS);
            expect(drawn.rings, 'families without a subtype are drawn on one ring').toBe(false);
            expect(drawn.inner.map((arc) => arc.rawName)).toEqual(SINGLETONS.map(({name}) => name));

            expect(
                drawn.inner.map((arc) => arc.itemStyle?.color),
                'the fill of each arc, by rank',
            ).toEqual(palette.slice(0, SINGLETONS.length));
            expect(drawn.color, 'the list ECharts paints an arc without a fill of its own with').toEqual(palette);
        } finally {
            document.documentElement.classList.remove('dark');
        }
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
