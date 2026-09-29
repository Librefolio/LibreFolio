/**
 * allocationRings.test.ts — Unit tests for `buildAllocationRings()` (decision D72) and
 * `buildAllocationRingData()`, plus one source contract on the component that draws them,
 * `AllocationPieChart.svelte`.
 *
 * ## Why the rings exist
 *
 * Decision D71 draws an asset-type subtype as a *shade* of its family. A shade says "related
 * to" only while its relative is on screen, so `buildAllocationHierarchy` never shades a group
 * of one (`allocationHierarchy.test.ts`, "never shades a singleton group"). Review R12
 * (22/09/2026) found exactly that group on the developer's own Dashboard: a lone `ETF_STOCK`
 * in a pure, unrelated colour, with nothing saying what it was related to. D72 moves the
 * relation from colour to geometry: a base ring with one arc per family, and an outer ring
 * that splits only the families holding a subtype.
 *
 * ## Which family: the vehicle, since 24/09/2026
 *
 * The first two-ring donut grouped by *content* — contract K2, `ETF_STOCK` under STOCK. The
 * developer reviewed it on 24/09 and chose option B, **by vehicle**: every ETF subtype belongs
 * to the ETF family, and a thinner, separate outer ring says what kind of ETF it is — "ETF
 * generico" + "ETF azionario". Since K's taxonomy landed, the vehicle is K's own container view,
 * `assetTypeFamily` — which also files real-estate crowdfunding under CROWDFUND — and that the
 * pie really draws those families is pinned on the mounted component, in
 * `AllocationPieChart.test.ts`. The first block below replays the **review case** — synthetic
 * numbers with the shape of the portfolio the review was made on — after proving that on the
 * same numbers the content grouping draws the picture the review turned down.
 *
 * The builder itself takes families as given — nothing in it depends on that choice — but the
 * tests resolve them the way the product does: K's `assetTypeFamily` for the pie's grouping and
 * K's `primaryAssetType` (K2) for the content grouping, both called for real rather than copied,
 * so a copy cannot drift from K in silence. The hierarchy is always the real one, so every test
 * goes through the handoff the component performs. One test keeps the content grouping on
 * purpose: the family of three K2 makes of REAL_ESTATE, ETF_REAL_ESTATE and
 * CROWDFUND_REAL_ESTATE, which shows the builder does not care which grouping produced its
 * families.
 *
 * ## The claims — each tested as a claim rather than as a snapshot
 *
 * 1. **A subtype is shaded by its rank among the subtypes, not by its position in the
 *    family.** With the generic member absent, position 0 is the subtype itself, and
 *    `shadeForDepth(base, 0)` hands back the base colour verbatim — R12 again, one layer up.
 *    So a lone subtype is held to a *measured* lightness distance from its family colour, not
 *    merely to a different hex string, which a one-digit drift would satisfy.
 * 2. **A family may have N members.** By vehicle the ETF family holds the generic ETF and up to
 *    six subtypes, and the CROWDFUND family its generic member and real-estate crowdfunding; one
 *    scenario draws five members at once.
 * 3. **The rings line up by construction.** Each family owns one base arc and one contiguous
 *    run of outer arcs summing to it, in the same order — checked down to the prefix sum at
 *    each family boundary, the angle at which the eye would see a misalignment.
 * 4. **A legend click hides a family on both rings.** ECharts filters the data items *by name*
 *    in every series, so every arc of both rings carries its family's label, and hiding any
 *    family leaves the two rings summing alike.
 * 5. **A caption says what its arc is**: the family on base arcs and fillers, the member's own
 *    label for a subtype, and a *generic* caption for the unspecialised member of a split
 *    family — never the bare family label, which beside "ETF azionario" would read as the
 *    whole family.
 * 6. **One rounding for a member and its family.** R12d: a member and its family were printed
 *    at two different precisions — two roundings of one quantity, read as two quantities.
 *
 * No fixture holds a real portfolio figure: every weight and amount below is synthetic (rule of
 * 24/09 — no real financial value of the developer in a versioned file). The review case keeps
 * only the *shape* of the portfolio the review was made on.
 *
 * The labels are this file's own (`TYPE_LABELS`), shaped like the developer's Italian screen.
 * The product catalogue is never loaded, so asserting on them asserts the naming rules, not a
 * translation.
 *
 * ## Why the component's fast path is pinned by reading its source
 *
 * A test of the pure module cannot see how the chart *refreshes*. `AllocationPieChart` has a
 * data-only path — chart already drawn, same theme, same set of types — that calls
 * `setOption({series: …})` without rebuilding the option. With two rings it must address both
 * series by id. The trap was written down before D72 was built (mandate G §6,
 * `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/G-frontend-colori-allocazione.md`):
 * a `series: [{data}]` that refreshes the base ring and leaves the outer one on stale numbers —
 * no error, no symptom, and only on the second render of a mounted chart, a sequence no test of
 * the pure module performs. The block is isolated by brace matching with comments dropped, and
 * a positive control proves the check fails on the historical payload even when both ids appear
 * elsewhere in the text.
 *
 * D72 first shipped three series; the redesign of 24/09 dropped the third, `alloc-base-labels`.
 * The same contract asserts it is gone: a series still drawn by `ringSeries()` but missing from
 * the fast path would be the same stale ring, by omission.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module components/charts/__tests__/allocationRings.test
 */
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {beforeAll, describe, expect, it} from 'vitest';

import {PALETTE_SLOTS, paletteDefects, readSourcePalette} from '$test/sourcePalettes';

import {buildAllocationHierarchy, shadeForDepth} from '../allocationHierarchy';
import {buildAllocationRingData, buildAllocationRings, type AllocationRingDatum, type AllocationRingItem, type AllocationRingsLayout} from '../allocationRings';
import {hexToHsl} from '$lib/utils/colors';

// =============================================================================
// Fixtures
// =============================================================================

/** The only chart that draws rings. Its palettes are read from it, by name, not copied. */
const PIE_CHART = new URL('../AllocationPieChart.svelte', import.meta.url);

/** `PALETTE_LIGHT` in `AllocationPieChart.svelte`. */
const PIE_PALETTE_LIGHT = readSourcePalette(PIE_CHART, 'PALETTE_LIGHT');
/** `PALETTE_DARK` in `AllocationPieChart.svelte`. */
const PIE_PALETTE_DARK = readSourcePalette(PIE_CHART, 'PALETTE_DARK');

/** Both themes of that chart. */
const PIE_PALETTES: ReadonlyArray<readonly [string, readonly string[]]> = [
    ['PALETTE_LIGHT', PIE_PALETTE_LIGHT],
    ['PALETTE_DARK', PIE_PALETTE_DARK],
];

type Resolver = (key: string) => string;

/** `__tests__` → `charts` → `components` → `lib`, then `api/generated.ts`. */
const GENERATED_TS = fileURLToPath(new URL('../../../api/generated.ts', import.meta.url));

/** What this file reads from K's `assetTypes.ts`. */
interface Taxonomy {
    assetTypeFamily: Resolver;
    primaryAssetType: Resolver;
}

let taxonomy: Taxonomy | null = null;

/**
 * K's taxonomy, imported once for the whole file: every test below resolves families through it.
 *
 * `assetTypes.ts` reads the generated Zodios schemas (`$lib/api/generated`, gitignored, written by
 * `./dev.py api sync`) at module load. As in `assetTypeTables.test.ts` the import is dynamic and
 * follows a check that the file exists, so a missing client fails every test with the command that
 * fixes it rather than an unresolvable import — a missing file is reported, never skipped: in a
 * summary line a skipped check and a satisfied one are the same absence of red.
 */
beforeAll(async () => {
    expect(existsSync(GENERATED_TS), "src/lib/api/generated.ts is absent, so K's assetTypes.ts cannot be imported and no family can be resolved the way the pie resolves it. Run `./dev.py api sync`.").toBe(true);
    const assetTypes = await import('$lib/utils/assetTypes');
    taxonomy = {assetTypeFamily: assetTypes.assetTypeFamily, primaryAssetType: assetTypes.primaryAssetType};
});

function loadedTaxonomy(): Taxonomy {
    if (taxonomy === null) throw new Error("K's taxonomy was not loaded: the beforeAll of this file failed, see its message");
    return taxonomy;
}

/**
 * The pie's grouping, by **vehicle**: K's `assetTypeFamily`, called for real. The six ETF
 * subtypes belong to `ETF`, real-estate crowdfunding to `CROWDFUND`, every other type to itself
 * upper-cased — so the synthetic `"Liquidity"` bucket comes back as `"LIQUIDITY"`.
 */
const resolveByVehicle: Resolver = (key) => loadedTaxonomy().assetTypeFamily(key);

/**
 * Grouping by **content** — contract K2, K's `primaryAssetType`, called for real: the pie's until
 * 24/09 and still the allocation history chart's. `ETF_STOCK` rolls up into STOCK, and REAL_ESTATE
 * gathers ETF_REAL_ESTATE and CROWDFUND_REAL_ESTATE into a family of three.
 *
 * Not the pie's grouping: it is used by the review case, to show the picture the review turned
 * down, and by the family of three, which shows that the builder takes families as given.
 */
const resolveByContent: Resolver = (key) => loadedTaxonomy().primaryAssetType(key);

interface Payload {
    id: string;
    /** Raw backend key, casing included — what the component's `memberLabel` translates. */
    key: string;
    /** Percent of the portfolio — what `AllocationPieChart` reads through `weightOf`. */
    value: number;
    /** Absolute amount, read through `amountOf`: a fictitious €100 000 portfolio. */
    amount: number;
}

interface Entry {
    key: string;
    weight: number;
    item: Payload;
}

type Layout = AllocationRingsLayout<Payload>;
type Arc = AllocationRingItem<Payload>;

interface RingData {
    base: AllocationRingDatum[];
    outer: AllocationRingDatum[];
}

function entry(key: string, value: number): Entry {
    return {key, weight: value, item: {id: `item-${key}`, key, value, amount: value * 1000}};
}

/**
 * The review case of R12 (24/09/2026): a large generic ETF, a small equity ETF — the lone subtype
 * of the ETF family — a mid crowdfunding slice, a mid bond slice and a tiny cash bucket, with the
 * backend's keys and casing, in percent, summing to 100.
 *
 * The values are **synthetic**: only the shape comes from the review — which families there are,
 * which one is split, and how their sizes rank (generic ETF > CROWDFUND > BOND > ETF_STOCK >
 * Liquidity > 0, so the content grouping of K2 would rank the equity ETF's family fourth).
 */
const REVIEW_CASE_ENTRIES = [entry('ETF', 56.4), entry('CROWDFUND', 23.7), entry('BOND', 13.9), entry('ETF_STOCK', 5.2), entry('Liquidity', 0.8)];

/** The same case without its generic ETF: the ETF family is then a lone subtype. */
const LONE_SUBTYPE_ENTRIES = [entry('CROWDFUND', 23.7), entry('BOND', 13.9), entry('ETF_STOCK', 5.2), entry('Liquidity', 0.8)];

/** A full family: the subtype outweighs the generic member and is listed first. */
const FULL_FAMILY_ENTRIES = [entry('ETF_STOCK', 70), entry('BOND', 45), entry('ETF', 30)];

/** A family of five, beside two of the base types its subtypes contain, and four unsplit families. */
const EVERY_SHAPE_ENTRIES = [entry('ETF', 24.1), entry('CROWDFUND', 15.35), entry('BOND', 12.4), entry('ETF_BOND', 7.25), entry('ETF_STOCK', 9.8), entry('REAL_ESTATE', 6.5), entry('ETF_REAL_ESTATE', 4.05), entry('ETF_MONETARY', 2.2), entry('Liquidity', 0.6)];

/**
 * The family of three K2 makes of REAL_ESTATE — the property itself, ETF_REAL_ESTATE and
 * CROWDFUND_REAL_ESTATE — under `resolveByContent`. Input order and weight order disagree on
 * purpose: the pure member is neither first nor heaviest, and the subtypes are listed lightest
 * first.
 */
const FAMILY_OF_THREE_ENTRIES = [entry('ETF_REAL_ESTATE', 10), entry('STOCK', 100), entry('REAL_ESTATE', 20), entry('CROWDFUND_REAL_ESTATE', 30)];

/**
 * Labels, one per type key, resolved the way the component resolves both a family and a member:
 * through the same `assets.types.<KEY>` lookup. That is why the generic member's own label *is*
 * its family's ("ETF" and "ETF") — the collision `genericCaption` exists for.
 *
 * They are this file's own, shaped like the developer's Italian screen; the product catalogue is
 * never loaded. A key without a label throws, so a new scenario cannot fall back to its raw key in
 * silence.
 */
const TYPE_LABELS: Readonly<Record<string, string>> = {
    ETF: 'ETF',
    ETF_STOCK: 'ETF azionario',
    ETF_BOND: 'ETF obbligazionario',
    ETF_REAL_ESTATE: 'ETF immobiliare',
    ETF_MONETARY: 'ETF monetario',
    STOCK: 'Azione',
    BOND: 'Obbligazione',
    CROWDFUND: 'Crowdfunding',
    REAL_ESTATE: 'Immobiliare',
    CROWDFUND_REAL_ESTATE: 'Crowdfunding immobiliare',
    LIQUIDITY: 'Liquidità',
};

function typeLabel(key: string): string {
    const label = TYPE_LABELS[key.toUpperCase()];
    if (label === undefined) throw new Error(`no test label for "${key}": add it to TYPE_LABELS`);
    return label;
}

/** The caption of a split family's generic member, shaped like `dashboard.allocationGeneric` in Italian. */
const genericCaption = (familyLabel: string): string => `${familyLabel} generico`;

/** The component's percent rule: two decimals. */
const roundTo2Decimals = (value: number): number => Math.round(value * 100) / 100;

/**
 * The component's own handoff: the real hierarchy first, the rings on top of it, and the
 * weight read back from the payload exactly as `AllocationPieChart` reads it.
 */
function ringsFor(entries: readonly Entry[], {palette = PIE_PALETTE_LIGHT, resolve = resolveByVehicle}: {palette?: readonly string[]; resolve?: Resolver} = {}) {
    const hierarchy = buildAllocationHierarchy(entries, {resolvePrimary: resolve, palette});
    const layout = buildAllocationRings(hierarchy, {weightOf: (item) => item.value});
    return {hierarchy, layout};
}

/** The same handoff down to the arcs the pie draws, with this file's labels. */
function ringDataFor(entries: readonly Entry[], {resolve = resolveByVehicle, round = roundTo2Decimals}: {resolve?: Resolver; round?: (value: number) => number} = {}): {layout: Layout; data: RingData} {
    const {layout} = ringsFor(entries, {resolve});
    const data = buildAllocationRingData(layout, {
        familyLabel: typeLabel,
        memberLabel: (item) => typeLabel(item.key),
        genericCaption,
        amountOf: (item) => item.amount,
        round,
    });
    return {layout, data};
}

/** The one base arc of a family; fails when there is none, or more than one. */
function baseArcOf(layout: Layout, primary: string): Arc {
    const arcs = layout.base.filter((arc) => arc.primary === primary);
    expect(arcs, `base arcs of ${primary}`).toHaveLength(1);
    return arcs[0];
}

/** A family's arcs on the outer ring, in drawing order. */
function outerArcsOf(layout: Layout, primary: string): Arc[] {
    return layout.outer.filter((arc) => arc.primary === primary);
}

/** The one datum of a family on the base ring. */
function baseDatumOf(data: RingData, primaryKey: string): AllocationRingDatum {
    const found = data.base.filter((datum) => datum.primaryKey === primaryKey);
    expect(found, `base data of ${primaryKey}`).toHaveLength(1);
    return found[0];
}

/** The one datum drawn on the outer ring for a raw key. */
function outerDatumOf(data: RingData, rawName: string): AllocationRingDatum {
    const found = data.outer.filter((datum) => datum.rawName === rawName);
    expect(found, `outer data of ${rawName}`).toHaveLength(1);
    return found[0];
}

/** What a ring adds up to, in the values ECharts is handed. */
function sumOfValues(data: readonly AllocationRingDatum[]): number {
    return data.reduce((sum, datum) => sum + datum.value, 0);
}

/** Measured lightness of a hex colour. Fails loudly rather than returning NaN. */
function lightnessOf(hex: string): number {
    const hsl = hexToHsl(hex);
    expect(hsl, `expected ${hex} to be parseable hex`).not.toBeNull();
    return hsl!.l;
}

/** Measured hue of a hex colour. */
function hueOf(hex: string): number {
    const hsl = hexToHsl(hex);
    expect(hsl, `expected ${hex} to be parseable hex`).not.toBeNull();
    return hsl!.h;
}

/** Hue distance on the circle: 359.9° and 0.1° are 0.2° apart, not 359.8°. */
function hueDistance(a: string, b: string): number {
    const delta = Math.abs(hueOf(a) - hueOf(b));
    return Math.min(delta, 360 - delta);
}

// =============================================================================
// The palettes under test — what was read, so no loop below can pass on nothing
// =============================================================================

describe('the palettes under test', () => {
    it.each(PIE_PALETTES)(`AllocationPieChart %s is ${PALETTE_SLOTS} distinct #rrggbb colours`, (_name, palette) => {
        expect(paletteDefects(palette), `the palette the rings draw with is not ${PALETTE_SLOTS} distinct colours: two families would share one, or a slot is missing`).toEqual([]);
    });

    it('pairs the light and dark palettes slot by slot', () => {
        expect(PIE_PALETTE_DARK.length, 'the two themes are not the same length: a family would change colour when the theme changes').toBe(PIE_PALETTE_LIGHT.length);
    });
});

// =============================================================================
// R12, option B — the review case, grouped by vehicle
// =============================================================================

describe('the pie groups by vehicle — the review case (R12, option B)', () => {
    it.each(PIE_PALETTES)('splits the ETF family alone, into ETF generico + ETF azionario, on %s', (_name, palette) => {
        // Barrier: this is the input on which the two groupings disagree. By content — K2, the
        // pie's until 24/09 and still the history chart's — the same numbers put the equity ETF in
        // a family of its own, "Azione", apart from the generic ETF: the picture the review turned down.
        const byContent = ringsFor(REVIEW_CASE_ENTRIES, {palette, resolve: resolveByContent}).layout;
        expect(byContent.base.map((arc) => arc.primary)).toEqual(['ETF', 'CROWDFUND', 'BOND', 'STOCK', 'LIQUIDITY']);
        expect(baseArcOf(byContent, 'ETF').split).toBe(false);
        expect(outerArcsOf(byContent, 'STOCK').map((arc) => arc.key)).toEqual(['ETF_STOCK']);

        const {layout} = ringsFor(REVIEW_CASE_ENTRIES, {palette, resolve: resolveByVehicle});
        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['ETF', 'CROWDFUND', 'BOND', 'LIQUIDITY']);

        // One family for both ETFs, weighing their sum: 56.4 + 5.2.
        const family = baseArcOf(layout, 'ETF');
        expect(family.key).toBe('ETF');
        expect(family.role).toBe('base');
        expect(family.split).toBe(true);
        expect(family.memberCount).toBe(2);
        expect(family.weight).toBeCloseTo(61.6, 9);
        expect(family.color).toBe(palette[0]);
        expect(family.items.map((item) => item.id)).toEqual(['item-ETF', 'item-ETF_STOCK']);

        // Its members on the outer ring: ETF generico — the pure member — then ETF azionario.
        const members = outerArcsOf(layout, 'ETF');
        expect(members.map((arc) => arc.role)).toEqual(['member', 'member']);
        expect(members.map((arc) => arc.key)).toEqual(['ETF', 'ETF_STOCK']);
        expect(members.map((arc) => arc.pure)).toEqual([true, false]);
        const [generic, equity] = members;
        expect(generic.weight).toBeCloseTo(56.4, 9);
        expect(equity.weight).toBeCloseTo(5.2, 9);

        // ETF generico wears the family colour verbatim; ETF azionario the family's first shade — at
        // a distance the eye can use, on the same hue, so it still reads as an ETF.
        expect(generic.color).toBe(family.color);
        expect(equity.color).toBe(shadeForDepth(family.color, 1));
        expect(Math.abs(lightnessOf(equity.color) - lightnessOf(family.color)), `${family.color} → ${equity.color} ΔL`).toBeGreaterThanOrEqual(15);
        expect(hueDistance(equity.color, family.color), `${family.color} → ${equity.color} Δh`).toBeLessThanOrEqual(1);

        // Only ETF is split: every other family is exactly one filler under its base arc.
        expect(layout.base.filter((arc) => arc.split).map((arc) => arc.primary)).toEqual(['ETF']);
        expect(layout.outer.map((arc) => `${arc.role}:${arc.key}`)).toEqual(['member:ETF', 'member:ETF_STOCK', 'filler:CROWDFUND', 'filler:BOND', 'filler:LIQUIDITY']);
        for (const primary of ['CROWDFUND', 'BOND', 'LIQUIDITY']) {
            const arcs = outerArcsOf(layout, primary);
            expect(arcs, `outer arcs of ${primary}`).toHaveLength(1);
            expect(arcs[0].role, primary).toBe('filler');
            expect(arcs[0].weight, primary).toBe(baseArcOf(layout, primary).weight);
        }
    });
});

// =============================================================================
// Split families — pure member first, one shade step per subtype
// =============================================================================

describe('buildAllocationRings — split families', () => {
    it.each(PIE_PALETTES)('shades a lone subtype by its rank among the subtypes, not by its position — its generic member absent, on %s', (_name, palette) => {
        const {hierarchy, layout} = ringsFor(LONE_SUBTYPE_ENTRIES, {palette});

        // Barrier: this is the R12 shape. Under D71 alone the lone ETF_STOCK is a group of one,
        // painted with the verbatim palette entry — the defect itself.
        const underD71 = hierarchy.find((row) => row.key === 'ETF_STOCK');
        expect(underD71, 'ETF_STOCK must survive the hierarchy').toBeDefined();
        expect(underD71!.groupSize).toBe(1);
        expect(underD71!.depth).toBe(0);
        expect(underD71!.color).toBe(palette[2]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['CROWDFUND', 'BOND', 'ETF', 'LIQUIDITY']);

        // The family is named after its vehicle, although no generic ETF is held.
        const family = baseArcOf(layout, 'ETF');
        expect(family.key).toBe('ETF');
        expect(family.role).toBe('base');
        expect(family.split).toBe(true);
        expect(family.memberCount).toBe(1);
        expect(family.weight).toBeCloseTo(5.2, 9);
        expect(family.color).toBe(palette[2]);
        expect(family.items.map((item) => item.id)).toEqual(['item-ETF_STOCK']);

        const members = outerArcsOf(layout, 'ETF');
        expect(members).toHaveLength(1);
        const [lone] = members;
        expect(lone.role).toBe('member');
        expect(lone.key).toBe('ETF_STOCK');
        expect(lone.pure).toBe(false);
        expect(lone.weight).toBeCloseTo(5.2, 9);

        // The fix, stated three ways. A colour other than the family's — under D71 it was the
        // same one …
        expect(lone.color).not.toBe(family.color);
        // … at a distance the eye can use, on the same hue, so it still reads as that family …
        expect(Math.abs(lightnessOf(lone.color) - lightnessOf(family.color)), `${family.color} → ${lone.color} ΔL`).toBeGreaterThanOrEqual(15);
        expect(hueDistance(lone.color, family.color), `${family.color} → ${lone.color} Δh`).toBeLessThanOrEqual(1);
        // … because it is the family's first *subtype* shade, whatever its position.
        expect(lone.color).toBe(shadeForDepth(family.color, 1));
    });

    it('splits a full family into [pure member in the family colour, subtype shaded], pure first', () => {
        // The subtype outweighs the pure member and is listed first: neither may decide the order.
        const {hierarchy, layout} = ringsFor(FULL_FAMILY_ENTRIES);

        expect(layout.rings).toBe(true);
        const family = baseArcOf(layout, 'ETF');
        expect(family.color).toBe(PIE_PALETTE_LIGHT[0]);
        expect(family.memberCount).toBe(2);
        expect(family.weight).toBeCloseTo(100, 9);

        const members = outerArcsOf(layout, 'ETF');
        expect(members).toHaveLength(2);
        expect(members.map((arc) => arc.role)).toEqual(['member', 'member']);
        expect(members.map((arc) => arc.key)).toEqual(['ETF', 'ETF_STOCK']);
        expect(members.map((arc) => arc.pure)).toEqual([true, false]);
        expect(members.map((arc) => arc.weight)).toEqual([30, 70]);
        expect(members.map((arc) => arc.memberCount)).toEqual([2, 2]);

        const [pure, subtype] = members;
        // Verbatim palette entry — no hex → HSL → hex round trip.
        expect(pure.color).toBe(family.color);
        expect(subtype.color).not.toBe(family.color);
        expect(subtype.color).toBe(shadeForDepth(family.color, 1));
        // Where D71 already worked, the outer ring repaints nothing: the hierarchy's own shade.
        expect(subtype.color).toBe(hierarchy.find((row) => row.key === 'ETF_STOCK')!.color);

        // A member arc carries its own payload only; the base arc carries the whole family.
        expect(pure.items.map((item) => item.id)).toEqual(['item-ETF']);
        expect(subtype.items.map((item) => item.id)).toEqual(['item-ETF_STOCK']);
        expect(family.items.map((item) => item.id)).toEqual(['item-ETF', 'item-ETF_STOCK']);
    });

    it.each(PIE_PALETTES)('splits a family of three into three distinct colours, pure first then subtypes by weight, on %s', (_name, palette) => {
        // Barrier: the family of three exists only by content, through K2. The pie's own grouping —
        // by vehicle — scatters it: real-estate crowdfunding is a crowdfunding, ETF_REAL_ESTATE is
        // an ETF, and REAL_ESTATE stays on its own.
        expect(resolveByVehicle('CROWDFUND_REAL_ESTATE')).toBe('CROWDFUND');
        expect(resolveByVehicle('ETF_REAL_ESTATE')).toBe('ETF');
        expect(resolveByVehicle('REAL_ESTATE')).toBe('REAL_ESTATE');
        expect(resolveByContent('CROWDFUND_REAL_ESTATE')).toBe('REAL_ESTATE');
        expect(resolveByContent('ETF_REAL_ESTATE')).toBe('REAL_ESTATE');

        const {layout} = ringsFor(FAMILY_OF_THREE_ENTRIES, {palette, resolve: resolveByContent});

        expect(layout.rings).toBe(true);
        const family = baseArcOf(layout, 'REAL_ESTATE');
        expect(family.memberCount).toBe(3);
        expect(family.weight).toBeCloseTo(60, 9);
        expect(family.color).toBe(palette[1]);

        const members = outerArcsOf(layout, 'REAL_ESTATE');
        expect(members).toHaveLength(3);
        expect(members.map((arc) => arc.key)).toEqual(['REAL_ESTATE', 'CROWDFUND_REAL_ESTATE', 'ETF_REAL_ESTATE']);
        expect(members.map((arc) => arc.pure)).toEqual([true, false, false]);
        expect(members.map((arc) => arc.weight)).toEqual([20, 30, 10]);
        expect(members.map((arc) => arc.memberCount)).toEqual([3, 3, 3]);

        // One shade step per subtype, by rank: a rule that assumed two members would give both
        // subtypes the same shade.
        const colors = members.map((arc) => arc.color);
        expect(new Set(colors).size).toBe(3);
        expect(colors).toEqual([family.color, shadeForDepth(family.color, 1), shadeForDepth(family.color, 2)]);

        // Distinct is measured, pairwise: three hex strings one digit apart would satisfy the Set.
        let pairsChecked = 0;
        for (let i = 0; i < colors.length; i++) {
            for (let j = i + 1; j < colors.length; j++) {
                expect(Math.abs(lightnessOf(colors[i]) - lightnessOf(colors[j])), `${colors[i]} vs ${colors[j]} ΔL`).toBeGreaterThanOrEqual(15);
                pairsChecked++;
            }
        }
        expect(pairsChecked).toBe(3);
    });
});

// =============================================================================
// Unsplit families — one piece at full thickness
// =============================================================================

describe('buildAllocationRings — unsplit families', () => {
    it('gives a family without subtypes one filler, with its base weight and colour', () => {
        const bond = entry('BOND', 40);
        // A split family beside it, so the outer ring is really drawn.
        const {layout} = ringsFor([entry('ETF', 55), entry('ETF_STOCK', 25), bond]);
        expect(layout.rings).toBe(true);

        const family = baseArcOf(layout, 'BOND');
        expect(family.split).toBe(false);
        expect(family.memberCount).toBe(1);
        expect(family.weight).toBeCloseTo(40, 9);

        const outer = outerArcsOf(layout, 'BOND');
        expect(outer).toHaveLength(1);
        const [filler] = outer;
        expect(filler.role).toBe('filler');
        expect(filler.key).toBe('BOND');
        expect(filler.split).toBe(false);
        expect(filler.memberCount).toBe(1);
        expect(filler.weight).toBe(family.weight);
        // The base colour travels with it; drawing it transparent is the component's call.
        expect(filler.color).toBe(family.color);
        expect(filler.items).toHaveLength(1);
        expect(filler.items[0]).toBe(bond.item);
    });

    it('keeps the synthetic "Liquidity" bucket as its own family, drawn as a filler', () => {
        const liquidity = entry('Liquidity', 30);
        const {layout} = ringsFor([entry('ETF', 55), entry('ETF_STOCK', 20), liquidity]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['ETF', 'LIQUIDITY']);

        const family = baseArcOf(layout, 'LIQUIDITY');
        // Its own weight and nothing else: not folded into any other family.
        expect(family.memberCount).toBe(1);
        expect(family.weight).toBeCloseTo(30, 9);
        // Title Case against its upper-cased primary is still the pure member, not a subtype of
        // itself: the comparison is case-insensitive.
        expect(family.split).toBe(false);

        const outer = outerArcsOf(layout, 'LIQUIDITY');
        expect(outer).toHaveLength(1);
        expect(outer[0].role).toBe('filler');
        expect(outer[0].split).toBe(false);
        expect(outer[0].color).toBe(family.color);
        // The payload keeps the backend's casing.
        expect(outer[0].items[0]).toBe(liquidity.item);

        // And the neighbouring family holds exactly its own two members.
        expect(baseArcOf(layout, 'ETF').memberCount).toBe(2);
        expect(layout.outer.filter((arc) => arc.role === 'member').map((arc) => arc.key)).toEqual(['ETF', 'ETF_STOCK']);
    });

    it.each(['REAL_ESTATE', 'BOND'])('keeps %s in one piece beside the ETF that contains it — by vehicle, what an ETF holds is not its family', (key) => {
        // Each base type sits next to the ETF subtype that holds it, and ETF_MONETARY — the subtype
        // K2 keeps as itself — is here too. By content BOND and REAL_ESTATE would each be split and
        // ETF_MONETARY left on its own; by vehicle the three subtypes are ETF. A rule keyed on an
        // underscore would still have REAL_ESTATE to get wrong.
        const {layout} = ringsFor([entry('ETF', 30), entry('REAL_ESTATE', 25), entry('ETF_REAL_ESTATE', 15), entry('BOND', 12), entry('ETF_BOND', 10), entry('ETF_MONETARY', 8)]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['ETF', 'REAL_ESTATE', 'BOND']);

        const family = baseArcOf(layout, key);
        expect(family.memberCount).toBe(1);
        expect(family.split).toBe(false);
        expect(family.items.map((item) => item.id)).toEqual([`item-${key}`]);

        const outer = outerArcsOf(layout, key);
        expect(outer).toHaveLength(1);
        expect(outer[0].role).toBe('filler');
        expect(outer[0].key).toBe(key);
        expect(outer[0].weight).toBe(family.weight);

        // ETF holds exactly its own members: the generic one first, then the subtypes by weight.
        expect(outerArcsOf(layout, 'ETF').map((arc) => arc.key)).toEqual(['ETF', 'ETF_REAL_ESTATE', 'ETF_BOND', 'ETF_MONETARY']);
    });
});

// =============================================================================
// Alignment — the reason the two rings line up
// =============================================================================

const ALIGNMENT_SCENARIOS: ReadonlyArray<readonly [string, readonly Entry[], Resolver]> = [
    ['the review case', REVIEW_CASE_ENTRIES, resolveByVehicle],
    ['a lone subtype, its generic member absent', LONE_SUBTYPE_ENTRIES, resolveByVehicle],
    ['a full family', FULL_FAMILY_ENTRIES, resolveByVehicle],
    ['a family of five, beside the base types it holds', EVERY_SHAPE_ENTRIES, resolveByVehicle],
    ['a family of three, by content', FAMILY_OF_THREE_ENTRIES, resolveByContent],
    ['no subtype at all', [entry('STOCK', 40), entry('BOND', 35), entry('Liquidity', 25)], resolveByVehicle],
];

describe('buildAllocationRings — alignment invariant', () => {
    it.each(ALIGNMENT_SCENARIOS)('%s: each family owns one base arc and one contiguous run of outer arcs that sums to it', (_name, entries, resolve) => {
        const {layout} = ringsFor(entries, {resolve});

        // Positive barrier: every check below iterates over these families.
        expect(layout.base.length).toBeGreaterThan(0);
        expect(new Set(layout.base.map((arc) => arc.primary)).size).toBe(layout.base.length);

        // Run-length encode the outer ring by family, noting where each run starts.
        const runs: {primary: string; start: number; weight: number}[] = [];
        let outerCursor = 0;
        for (const arc of layout.outer) {
            const last = runs[runs.length - 1];
            if (last && last.primary === arc.primary) last.weight += arc.weight;
            else runs.push({primary: arc.primary, start: outerCursor, weight: arc.weight});
            outerCursor += arc.weight;
        }

        // Contiguous and in base order at once: a family broken into two runs would be listed twice.
        expect(runs.map((run) => run.primary)).toEqual(layout.base.map((arc) => arc.primary));

        let baseCursor = 0;
        layout.base.forEach((family, index) => {
            // Same start angle on both rings, and the same extent.
            expect(runs[index].start, `${family.primary} starts at the same angle on both rings`).toBeCloseTo(baseCursor, 9);
            expect(runs[index].weight, `${family.primary} outer arcs sum to its base arc`).toBeCloseTo(family.weight, 9);
            baseCursor += family.weight;
        });

        expect(outerCursor, 'total outer weight equals total base weight').toBeCloseTo(baseCursor, 9);
    });
});

// =============================================================================
// The switch — two rings only when a family is split
// =============================================================================

describe('buildAllocationRings — when to draw two rings', () => {
    it('reports rings === false when no family holds a subtype, and true as soon as one does', () => {
        // Realistic, and deliberately tempting: a Title Case bucket, the generic ETF and a base
        // type with an underscore — none of which is a subtype.
        const plain = [entry('STOCK', 40), entry('BOND', 25), entry('ETF', 20), entry('CROWDFUND', 9.4), entry('REAL_ESTATE', 5), entry('Liquidity', 0.6)];
        const {layout} = ringsFor(plain);

        // Barrier: a non-empty layout, so "nothing is split" is not vacuous.
        expect(layout.base).toHaveLength(6);
        expect(layout.rings).toBe(false);
        expect(layout.base.map((arc) => arc.split)).toEqual([false, false, false, false, false, false]);
        expect(layout.outer.map((arc) => arc.role)).toEqual(['filler', 'filler', 'filler', 'filler', 'filler', 'filler']);

        // Control: one subtype more and the same portfolio switches — so the `false` above was
        // about the subtypes, not a constant. ETF_MONETARY, which K2 keeps as itself, splits the
        // ETF family by vehicle.
        expect(ringsFor([...plain, entry('ETF_MONETARY', 1)]).layout.rings).toBe(true);
    });
});

// =============================================================================
// Degenerate palette
// =============================================================================

describe('buildAllocationRings — short palette', () => {
    it('never hands out an undefined colour when families outnumber the palette', () => {
        const palette = ['#1a4031', '#2563eb'];
        // Six families on two colours, the split one past the wrap point: the ETF family — two
        // subtypes, no generic ETF — is shaded from a wrapped entry.
        const entries = [entry('STOCK', 30), entry('BOND', 26), entry('ETF_REAL_ESTATE', 12), entry('ETF_STOCK', 8), entry('CROWDFUND', 15), entry('REAL_ESTATE', 8), entry('Liquidity', 1)];
        const {layout} = ringsFor(entries, {palette});

        // Barrier: really more families than colours, really two rings, and the split family
        // really past the wrap point.
        expect(layout.base.length).toBeGreaterThan(palette.length);
        expect(layout.rings).toBe(true);
        expect(layout.base.findIndex((arc) => arc.split)).toBeGreaterThanOrEqual(palette.length);
        expect(layout.base.map((arc) => arc.color)).toEqual(['#1a4031', '#2563eb', '#1a4031', '#2563eb', '#1a4031', '#2563eb']);

        // A 6-digit hex on every arc of both rings, as the ring item contract promises.
        for (const arc of [...layout.base, ...layout.outer]) {
            expect(arc.color, `${arc.role} ${arc.key}`).toMatch(/^#[0-9a-f]{6}$/i);
        }
    });
});

// =============================================================================
// The arcs the pie draws — legend
// =============================================================================

const LEGEND_SCENARIOS: ReadonlyArray<readonly [string, readonly Entry[], Resolver]> = [
    ['the review case', REVIEW_CASE_ENTRIES, resolveByVehicle],
    ['a lone subtype, its generic member absent', LONE_SUBTYPE_ENTRIES, resolveByVehicle],
    ['a family of five', EVERY_SHAPE_ENTRIES, resolveByVehicle],
    ['a family of three, by content', FAMILY_OF_THREE_ENTRIES, resolveByContent],
];

describe('buildAllocationRingData — a legend click hides a family on both rings', () => {
    it.each(LEGEND_SCENARIOS)('%s: every arc of both rings is named after its family', (_name, entries, resolve) => {
        const {data} = ringDataFor(entries, {resolve});

        // Barrier: two rings with members on the outer one — a naming rule checked only on
        // fillers would be checked where it cannot fail.
        expect(data.base.length).toBeGreaterThan(1);
        expect(data.outer.filter((datum) => datum.ringRole === 'member').length).toBeGreaterThan(0);

        const misnamed = [...data.base, ...data.outer].filter((datum) => datum.name !== typeLabel(datum.primaryKey)).map((datum) => `${datum.ringRole} ${datum.rawName} named "${datum.name}"`);
        expect(misnamed, 'arcs not named after their family').toEqual([]);

        // So the legend lists the families and nothing else: no outer arc brings a name of its own.
        expect([...new Set(data.outer.map((datum) => datum.name))]).toEqual(data.base.map((datum) => datum.name));
    });

    it.each(LEGEND_SCENARIOS)('%s: hiding any one family leaves the two rings with the same sum', (_name, entries, resolve) => {
        const {data} = ringDataFor(entries, {resolve});
        const families = data.base.map((datum) => datum.name);

        // Barrier: one legend entry per family, and the rings agree before any click.
        expect(new Set(families).size, 'two families share a label: one click would hide both').toBe(families.length);
        expect(sumOfValues(data.outer)).toBeCloseTo(sumOfValues(data.base), 9);

        for (const hidden of families) {
            const family = data.base.find((datum) => datum.name === hidden)!.primaryKey;
            // What the click does: every series drops the data items that carry the clicked name.
            const base = data.base.filter((datum) => datum.name !== hidden);
            const outer = data.outer.filter((datum) => datum.name !== hidden);

            // The family is gone from both rings — its one base arc and every one of its outer arcs …
            expect(data.base.length - base.length, `"${hidden}": base arcs hidden`).toBe(1);
            expect(
                [...base, ...outer].filter((datum) => datum.primaryKey === family).map((datum) => `${datum.ringRole} ${datum.rawName}`),
                `"${hidden}": arcs of the family still drawn`,
            ).toEqual([]);
            // … so what is left still lines up.
            expect(sumOfValues(outer), `"${hidden}" hidden: outer ring against base ring`).toBeCloseTo(sumOfValues(base), 9);
        }
    });
});

// =============================================================================
// The arcs the pie draws — captions
// =============================================================================

describe('buildAllocationRingData — captions', () => {
    it('captions the review case: the family on base arcs and fillers, ETF generico and ETF azionario on the outer ring', () => {
        const {data} = ringDataFor(REVIEW_CASE_ENTRIES);

        // Base ring: every arc is a family, and says so.
        expect(data.base.map((datum) => [datum.rawName, datum.caption])).toEqual([
            ['ETF', typeLabel('ETF')],
            ['CROWDFUND', typeLabel('CROWDFUND')],
            ['BOND', typeLabel('BOND')],
            ['LIQUIDITY', typeLabel('LIQUIDITY')],
        ]);

        // Outer ring, fillers: the family they stand under.
        expect(data.outer.filter((datum) => datum.filler).map((datum) => [datum.rawName, datum.caption])).toEqual([
            ['CROWDFUND', typeLabel('CROWDFUND')],
            ['BOND', typeLabel('BOND')],
            ['LIQUIDITY', typeLabel('LIQUIDITY')],
        ]);

        // Outer ring, members. The subtype says what it is …
        const equity = outerDatumOf(data, 'ETF_STOCK');
        expect(equity.ringRole).toBe('member');
        expect(equity.caption).toBe(typeLabel('ETF_STOCK'));

        // … and the generic member says it is the generic one. Its own label *is* the family's
        // ("ETF"), which beside "ETF azionario" would read as the whole family.
        const generic = outerDatumOf(data, 'ETF');
        expect(generic.ringRole).toBe('member');
        expect(typeLabel(generic.rawName), "barrier: the generic member's own label is its family's").toBe(typeLabel(generic.primaryKey));
        expect(generic.caption).toBe(genericCaption(typeLabel('ETF')));
        expect(generic.caption).not.toBe(typeLabel('ETF'));

        // In the review's words — with this file's labels, not the product catalogue.
        expect(data.outer.filter((datum) => !datum.filler).map((datum) => datum.caption)).toEqual(['ETF generico', 'ETF azionario']);
    });

    it('captions a lone subtype with its own label — without a generic member, no generic caption', () => {
        const {data} = ringDataFor(LONE_SUBTYPE_ENTRIES);

        // Barrier: the ETF family is split, and its only member is the subtype.
        const members = data.outer.filter((datum) => datum.primaryKey === 'ETF');
        expect(members.map((datum) => `${datum.ringRole}:${datum.rawName}`)).toEqual(['member:ETF_STOCK']);

        expect(members[0].caption).toBe(typeLabel('ETF_STOCK'));
        expect(baseDatumOf(data, 'ETF').caption).toBe(typeLabel('ETF'));
        expect([...data.base, ...data.outer].map((datum) => datum.caption)).not.toContain(genericCaption(typeLabel('ETF')));
    });
});

// =============================================================================
// The arcs the pie draws — one rounding for a member and its family
// =============================================================================

/**
 * The review case at four decimals — synthetic, like every weight in this file: ETF azionario
 * 5.2137 in a family of 61.5863, summing to 100 with the other slices. Chosen so that two
 * decimals and one decimal print both the member and the family differently.
 */
const UNROUNDED_ENTRIES = [entry('ETF', 56.3726), entry('CROWDFUND', 23.7), entry('BOND', 13.9), entry('ETF_STOCK', 5.2137), entry('Liquidity', 0.8137)];

/** The rule the review turned down for a family beside its member: one decimal. */
const roundTo1Decimal = (value: number): number => Math.round(value * 10) / 10;

describe('buildAllocationRingData — rounding', () => {
    it('rounds ETF azionario to 5.21 and its family to 61.59 under a two-decimal rule — never 5.2 beside 61.6', () => {
        const {layout, data} = ringDataFor(UNROUNDED_ENTRIES, {round: roundTo2Decimals});

        // Barrier: the raw figures really need rounding, and one decimal would print the member and
        // the family differently from two — otherwise a one-decimal total would pass unseen.
        const rawFamily = baseArcOf(layout, 'ETF').weight;
        const rawMember = outerArcsOf(layout, 'ETF').find((arc) => arc.key === 'ETF_STOCK')!.weight;
        expect(rawFamily).toBeCloseTo(61.5863, 9);
        expect(rawMember).toBeCloseTo(5.2137, 9);
        expect(roundTo1Decimal(rawFamily)).not.toBe(roundTo2Decimals(rawFamily));
        expect(roundTo1Decimal(rawMember)).not.toBe(roundTo2Decimals(rawMember));

        const equity = outerDatumOf(data, 'ETF_STOCK');
        expect(equity.value).toBe(5.21);
        expect(equity.primaryTotal).toBe(61.59);

        const generic = outerDatumOf(data, 'ETF');
        expect(generic.value).toBe(56.37);
        expect(generic.primaryTotal).toBe(61.59);

        const family = baseDatumOf(data, 'ETF');
        expect(family.value).toBe(61.59);
        expect(family.primaryTotal).toBe(61.59);

        // Every arc of both rings quotes its family's total exactly as the family's own arc shows it.
        const disagreeing = [...data.base, ...data.outer].filter((datum) => datum.primaryTotal !== baseDatumOf(data, datum.primaryKey).value).map((datum) => `${datum.ringRole} ${datum.rawName}: ${datum.primaryTotal} vs ${baseDatumOf(data, datum.primaryKey).value}`);
        expect(disagreeing).toEqual([]);
    });

    it("applies the caller's rule to both fields, whatever the rule", () => {
        // Whole percent — a rule no built-in precision could guess.
        const {data} = ringDataFor(UNROUNDED_ENTRIES, {round: Math.round});

        const equity = outerDatumOf(data, 'ETF_STOCK');
        expect(equity.value).toBe(5);
        expect(equity.primaryTotal).toBe(62);
        expect(baseDatumOf(data, 'ETF').value).toBe(62);
    });
});

// =============================================================================
// AllocationPieChart — the data-only fast path, pinned by source
// =============================================================================

/** The guard of the data-only update in `AllocationPieChart.svelte`. */
const FAST_PATH_HEADER = /if\s*\(\s*chartFullyInitialized\s*&&\s*lastDark\s*===\s*isDark\s*&&\s*sameTypeSet\s*\)\s*\{/;

/** The two series of D72 since the redesign of 24/09, as `ringSeries()` names them. */
const RING_SERIES_IDS = ['alloc-base', 'alloc-outer'];

/** The third series of D72's first version, removed on 24/09: a silent ring carrying the base icons. */
const REMOVED_RING_SERIES_ID = 'alloc-base-labels';

interface Block {
    /** The text between the braces, verbatim. */
    raw: string;
    /** The same text without comments — what actually runs. */
    code: string;
}

/**
 * Body of the block opened by `header`, closed by *brace matching* rather than by a lazy
 * regex, so a nested object literal cannot end it early. Comments are skipped while
 * matching and dropped from `code` — a comment naming a series refreshes nothing — and
 * string literals are copied whole, so a brace inside one cannot unbalance the count.
 */
function extractBlock(source: string, header: RegExp): Block | null {
    const match = header.exec(source);
    if (!match) return null;

    const start = match.index + match[0].length;
    let depth = 1;
    let code = '';
    let i = start;
    while (i < source.length) {
        const pair = source.slice(i, i + 2);
        if (pair === '//') {
            const eol = source.indexOf('\n', i);
            i = eol === -1 ? source.length : eol;
            continue;
        }
        if (pair === '/*') {
            const close = source.indexOf('*/', i + 2);
            if (close === -1) return null;
            i = close + 2;
            continue;
        }
        const char = source[i];
        if (char === "'" || char === '"' || char === '`') {
            let j = i + 1;
            while (j < source.length && source[j] !== char) j += source[j] === '\\' ? 2 : 1;
            if (j >= source.length) return null;
            code += source.slice(i, j + 1);
            i = j + 1;
            continue;
        }
        if (char === '{') depth++;
        else if (char === '}' && --depth === 0) return {raw: source.slice(start, i), code};
        code += char;
        i++;
    }
    return null;
}

/** The object literal around `index`: the nearest unmatched `{` before it, up to its `}`. */
function enclosingObjectLiteral(code: string, index: number): string | null {
    let depth = 0;
    let open = -1;
    for (let i = index; i >= 0; i--) {
        if (code[i] === '}') depth++;
        else if (code[i] === '{') {
            if (depth === 0) {
                open = i;
                break;
            }
            depth--;
        }
    }
    if (open === -1) return null;

    depth = 0;
    for (let i = open; i < code.length; i++) {
        if (code[i] === '{') depth++;
        else if (code[i] === '}' && --depth === 0) return code.slice(open, i + 1);
    }
    return null;
}

/**
 * The ring series a piece of code refreshes: those named as the exact quoted `id` of an
 * object literal that also carries `data`. The closing quote matters — `alloc-base` is a
 * prefix of the removed `alloc-base-labels`, and of any id a later series might take, so a
 * substring test for the base ring could be satisfied by another series alone — and so does
 * `data`: `{id: 'alloc-outer'}` on its own is a merge that changes nothing, the very stale
 * ring this contract exists to prevent.
 */
function refreshedRingIds(code: string): string[] {
    return RING_SERIES_IDS.filter((id) => {
        const idProperty = new RegExp(`\\bid\\s*:\\s*(['"\`])${id}\\1`, 'g');
        return [...code.matchAll(idProperty)].some((found) => {
            const literal = enclosingObjectLiteral(code, found.index ?? 0);
            return literal !== null && /\bdata\s*[:,}]/.test(literal);
        });
    });
}

function expectEveryRingSeriesRefreshed(code: string): void {
    expect(refreshedRingIds(code), 'ring series refreshed by the fast path').toEqual(RING_SERIES_IDS);
}

/** Every `alloc-*` series id a piece of code declares or addresses, sorted and deduplicated. */
function declaredRingIds(code: string): string[] {
    return [...new Set([...code.matchAll(/\bid\s*:\s*(['"`])(alloc-[\w-]+)\1/g)].map((found) => found[2]))].sort();
}

/** The component names the two ring series and no other — a third would be drawn and never refreshed. */
function expectOnlyTheTwoRingSeries(code: string): void {
    expect(declaredRingIds(code), 'ring series ids named anywhere in the component').toEqual([...RING_SERIES_IDS].sort());
}

/**
 * The historical trap, with decoys: both ids appear in a comment inside the fast path and in
 * a `ringSeries()` after it, so only a correct isolation *and* the comment stripping can make
 * the check fail here.
 */
const SINGLE_SERIES_FAST_PATH = `
        if (chartFullyInitialized && lastDark === isDark && sameTypeSet) {
            // was: {id: 'alloc-base', data: baseRingData}, {id: 'alloc-outer', data: outerRingData}
            chartInstance.setOption({series: [{data: chartData}]});
            return;
        }
        lastRawTypeKeys = currentRawTypeKeys;

        function ringSeries(): echarts.PieSeriesOption[] {
            return [
                {...shared, id: 'alloc-base', radius: [pieRadius[0], innerEnd], data: baseRingData},
                {...shared, id: 'alloc-outer', radius: [outerStart, pieRadius[1]], data: outerRingData},
            ];
        }
`;

/** `ringSeries()` as D72 first shipped it (23/09), with the third series the redesign removed. */
const THREE_SERIES_RING_SERIES = `
        function ringSeries(): echarts.PieSeriesOption[] {
            return [
                {...shared, id: 'alloc-base', radius: pieRadius, data: baseRingData},
                {...shared, id: 'alloc-outer', radius: [splitRadius, pieRadius[1]], data: outerRingData},
                {...shared, id: 'alloc-base-labels', radius: [pieRadius[0], splitRadius], silent: true, data: baseLabelData},
            ];
        }
`;

describe('AllocationPieChart — data-only fast path (source contract)', () => {
    it('refreshes both ring series by id, not only the first — and no third series is left behind', () => {
        const source = readFileSync(new URL('../AllocationPieChart.svelte', import.meta.url), 'utf8');

        // Barrier: exactly one fast path, so the block below is the one the chart runs.
        expect(source.match(new RegExp(FAST_PATH_HEADER.source, 'g')), 'fast-path guard').toHaveLength(1);
        const block = extractBlock(source, FAST_PATH_HEADER);
        expect(block, 'fast-path block not found — did its guard change?').not.toBeNull();

        // Barrier: it is the data-only update — it calls setOption and returns early — and the
        // extraction stopped at its closing brace instead of running on into `ringSeries()`,
        // which names both ids and would satisfy the check by itself.
        expect(block!.code).toMatch(/\.setOption\(/);
        expect(block!.code).toMatch(/\breturn\s*;/);
        expect(block!.code, 'extraction ran past the fast path').not.toContain('ringSeries');

        expectEveryRingSeriesRefreshed(block!.code);

        // The third series of D72's first version is gone, from the code and from the text: a
        // series still drawn by `ringSeries()` but absent from the fast path would be the same
        // stale ring, by omission.
        expect(source, `${REMOVED_RING_SERIES_ID} is back in AllocationPieChart.svelte: the fast path above refreshes only ${RING_SERIES_IDS.join(' and ')}`).not.toContain(REMOVED_RING_SERIES_ID);
        expectOnlyTheTwoRingSeries(source);
    });

    it('positive control: the same checks fail on the historical `series: [{data: chartData}]` and on a three-series `ringSeries()`', () => {
        const block = extractBlock(SINGLE_SERIES_FAST_PATH, FAST_PATH_HEADER);

        // The extraction found the block and stopped at its end: the failure below is about
        // the payload, not about a search that matched nothing.
        expect(block, 'control block not found').not.toBeNull();
        expect(block!.code).toContain('series: [{data: chartData}]');
        expect(block!.code).not.toContain('ringSeries');

        expect(refreshedRingIds(block!.code)).toEqual([]);
        expect(() => expectEveryRingSeriesRefreshed(block!.code)).toThrow();

        // The decoys are live: the whole text, or the block with its comment kept, would pass.
        expect(refreshedRingIds(SINGLE_SERIES_FAST_PATH)).toEqual(RING_SERIES_IDS);
        expect(refreshedRingIds(block!.raw)).toEqual(RING_SERIES_IDS);

        // The scan for a third series sees one when there is one, and passes a text that has only two.
        expect(declaredRingIds(THREE_SERIES_RING_SERIES)).toEqual(['alloc-base', 'alloc-base-labels', 'alloc-outer']);
        expect(() => expectOnlyTheTwoRingSeries(THREE_SERIES_RING_SERIES)).toThrow();
        expect(() => expectOnlyTheTwoRingSeries(SINGLE_SERIES_FAST_PATH)).not.toThrow();
    });
});
