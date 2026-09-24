/**
 * allocationRings.test.ts — Unit tests for `buildAllocationRings()` (decision D72), plus
 * one source contract on the component that draws it, `AllocationPieChart.svelte`.
 *
 * ## Why the rings exist
 *
 * Decision D71 draws an asset-type subtype as a *shade* of its primary type. A shade says
 * "related to" only while its relative is on screen, so `buildAllocationHierarchy` never
 * shades a group of one (`allocationHierarchy.test.ts`, "never shades a singleton group")
 * — and the commonest ETF portfolio is exactly that group: an `ETF_STOCK` held with no
 * direct `STOCK`. Review R12 found it on the developer's own Dashboard: a pure, unrelated
 * colour next to "ETF", "Crowdfunding" and "Bonds", with nothing saying it was equity. The
 * first block replays those real numbers.
 *
 * D72 moves the relation from colour to geometry: a base ring with one arc per family, and
 * an outer ring that splits only the families holding a subtype. Three claims follow, and
 * each is tested as a claim rather than as a snapshot:
 *
 * 1. **A subtype is shaded by its rank among the subtypes, not by its position in the
 *    family.** With the pure member absent, position 0 is the subtype itself, and
 *    `shadeForDepth(base, 0)` hands back the base colour verbatim — R12 again, one layer
 *    up. So the lone subtype is held to a *measured* lightness distance from its family
 *    colour, not merely to a different hex string, which a one-digit drift would satisfy.
 * 2. **A family may have N members.** Today's five ETF subtypes have five distinct
 *    parents, but the taxonomy grows: a crowdfunding real-estate type rolling up into
 *    `REAL_ESTATE` beside `ETF_REAL_ESTATE` makes three. That key is fictitious here and
 *    mapped by the injected resolver alone, so the test keeps its meaning whether or not
 *    the enum ever gains it.
 * 3. **The rings line up by construction.** Each family owns one base arc and one
 *    contiguous run of outer arcs summing to it, in the same order. The invariant is
 *    checked on every scenario of this file, down to the prefix sum at each family
 *    boundary — the angle at which the eye would see a misalignment.
 *
 * ## Why the component's fast path is pinned by reading its source
 *
 * A test of the pure module cannot see how the chart *refreshes*. `AllocationPieChart`
 * has a data-only path — chart already drawn, same theme, same set of types — that calls
 * `setOption({series: …})` without rebuilding the option. With two rings it must address
 * all three series by id. The trap was written down before D72 was built (mandate G §6,
 * `LibreFolio_developer_journal/Release_2/Phase_0/02_riskfolioIntegration/implementation/G-frontend-colori-allocazione.md`):
 * a `series: [{data}]` that refreshes the base ring and leaves the outer one on stale
 * numbers — no error, no symptom, and only on the second render of a mounted chart, a
 * sequence no test of the pure module performs. The block is isolated by brace matching
 * with comments dropped, and a positive control proves the check fails on the historical
 * payload even when the three ids appear elsewhere in the text.
 *
 * `resolvePrimary` is a stub, as in the sibling test: the real `primaryAssetType` reads
 * the generated Zodios schemas at module load. The hierarchy itself is the real one, so
 * every test goes through the same handoff the component performs.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module components/charts/__tests__/allocationRings.test
 */
import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

import {buildAllocationHierarchy, shadeForDepth} from '../allocationHierarchy';
import {buildAllocationRings, type AllocationRingItem, type AllocationRingsLayout} from '../allocationRings';
import {hexToHsl} from '$lib/utils/colors';

// =============================================================================
// Fixtures
// =============================================================================

/** Verbatim copy of `PALETTE_LIGHT` in `AllocationPieChart.svelte` — the only chart that draws rings. */
const PIE_PALETTE_LIGHT = ['#1a4031', '#2563eb', '#7c3aed', '#dc2626', '#d97706', '#0d9488', '#be185d', '#4f46e5', '#059669', '#ea580c', '#6366f1', '#0891b2', '#ca8a04', '#9333ea'];
/** Verbatim copy of `PALETTE_DARK` in `AllocationPieChart.svelte`. */
const PIE_PALETTE_DARK = ['#4ade80', '#60a5fa', '#a78bfa', '#f87171', '#fbbf24', '#2dd4bf', '#f472b6', '#818cf8', '#34d399', '#fb923c', '#a5b4fc', '#22d3ee', '#facc15', '#c084fc'];

/** Both themes of that chart. */
const PIE_PALETTES: ReadonlyArray<readonly [string, readonly string[]]> = [
    ['PALETTE_LIGHT', PIE_PALETTE_LIGHT],
    ['PALETTE_DARK', PIE_PALETTE_DARK],
];

/**
 * Stub for contract K2 (`primaryAssetType`), faithful on every key this file uses.
 *
 * The five ETF subtypes fold onto their parent. Everything else maps to **itself,
 * upper-cased**: the plain `ETF` (the residual for mixed content), `ETF_MONETARY` (a
 * money-market fund has no base type to roll into) and the synthetic `"Liquidity"` bucket,
 * which comes back as `"LIQUIDITY"`.
 */
const SUBTYPE_PARENT: Record<string, string> = {
    ETF_STOCK: 'STOCK',
    ETF_BOND: 'BOND',
    ETF_COMMODITY: 'COMMODITY',
    ETF_REAL_ESTATE: 'REAL_ESTATE',
    ETF_CRYPTO: 'CRYPTO',
};

type Resolver = (key: string) => string;

const resolvePrimary: Resolver = (key) => SUBTYPE_PARENT[key.toUpperCase()] ?? key.toUpperCase();

/**
 * The same stub plus one **fictitious** subtype. `CROWDFUND_REAL_ESTATE` is mapped here and
 * nowhere else: whether the real enum ever gains it belongs to another workstream, and the
 * family-of-three tests must not change meaning with that decision.
 */
const resolveWithThirdRealEstate: Resolver = (key) => (key.toUpperCase() === 'CROWDFUND_REAL_ESTATE' ? 'REAL_ESTATE' : resolvePrimary(key));

interface Payload {
    id: string;
    /** Percent of the portfolio — what `AllocationPieChart` reads through `weightOf`. */
    value: number;
}

interface Entry {
    key: string;
    weight: number;
    item: Payload;
}

type Layout = AllocationRingsLayout<Payload>;
type Arc = AllocationRingItem<Payload>;

function entry(key: string, value: number): Entry {
    return {key, weight: value, item: {id: `item-${key}`, value}};
}

/** The developer's `by_type` when R12 was reported, in percent, with the backend's casing. */
const R12_ENTRIES = [entry('ETF', 49.79), entry('CROWDFUND', 30.55), entry('BOND', 16.13), entry('ETF_STOCK', 3.53), entry('Liquidity', 0.01)];

/**
 * The component's own handoff: the real hierarchy first, the rings on top of it, and the
 * weight read back from the payload exactly as `AllocationPieChart` reads it.
 */
function ringsFor(entries: readonly Entry[], {palette = PIE_PALETTE_LIGHT, resolve = resolvePrimary}: {palette?: readonly string[]; resolve?: Resolver} = {}) {
    const hierarchy = buildAllocationHierarchy(entries, {resolvePrimary: resolve, palette});
    const layout = buildAllocationRings(hierarchy, {weightOf: (item) => item.value});
    return {hierarchy, layout};
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
// R12 — the lone subtype, on the developer's real data
// =============================================================================

describe('buildAllocationRings — a lone subtype (R12)', () => {
    it.each(PIE_PALETTES)('draws a lone ETF_STOCK as a shade of the STOCK family, never as its pure colour, on %s', (_name, palette) => {
        const {hierarchy, layout} = ringsFor(R12_ENTRIES, {palette});

        // Barrier: this really is the R12 input. Under D71 alone the lone ETF_STOCK is a
        // group of one, painted with the verbatim palette entry — the defect itself.
        const underD71 = hierarchy.find((row) => row.key === 'ETF_STOCK');
        expect(underD71, 'ETF_STOCK must survive the hierarchy').toBeDefined();
        expect(underD71!.groupSize).toBe(1);
        expect(underD71!.depth).toBe(0);
        expect(underD71!.color).toBe(palette[3]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['ETF', 'CROWDFUND', 'BOND', 'STOCK', 'LIQUIDITY']);

        // The family is named after its primary, although no STOCK is held directly.
        const family = baseArcOf(layout, 'STOCK');
        expect(family.key).toBe('STOCK');
        expect(family.role).toBe('base');
        expect(family.split).toBe(true);
        expect(family.memberCount).toBe(1);
        expect(family.weight).toBeCloseTo(3.53, 9);
        expect(family.color).toBe(palette[3]);
        expect(family.items.map((item) => item.id)).toEqual(['item-ETF_STOCK']);

        const members = outerArcsOf(layout, 'STOCK');
        expect(members).toHaveLength(1);
        const [lone] = members;
        expect(lone.role).toBe('member');
        expect(lone.key).toBe('ETF_STOCK');
        expect(lone.pure).toBe(false);
        expect(lone.weight).toBeCloseTo(3.53, 9);

        // The fix, stated three ways. A colour other than the family's — under D71 it was
        // the same one …
        expect(lone.color).not.toBe(family.color);
        // … at a distance the eye can use, on the same hue, so it still reads as equity …
        expect(Math.abs(lightnessOf(lone.color) - lightnessOf(family.color)), `${family.color} → ${lone.color} ΔL`).toBeGreaterThanOrEqual(15);
        expect(hueDistance(lone.color, family.color), `${family.color} → ${lone.color} Δh`).toBeLessThanOrEqual(1);
        // … because it is the family's first *subtype* shade, whatever its position.
        expect(lone.color).toBe(shadeForDepth(family.color, 1));

        // Every other family stays in one piece: a filler on the outer ring.
        expect(layout.outer.map((arc) => `${arc.role}:${arc.key}`)).toEqual(['filler:ETF', 'filler:CROWDFUND', 'filler:BOND', 'member:ETF_STOCK', 'filler:LIQUIDITY']);
        for (const primary of ['ETF', 'CROWDFUND', 'BOND', 'LIQUIDITY']) {
            const arcs = outerArcsOf(layout, primary);
            expect(arcs, `outer arcs of ${primary}`).toHaveLength(1);
            expect(arcs[0].role, primary).toBe('filler');
            expect(arcs[0].split, primary).toBe(false);
            expect(baseArcOf(layout, primary).split, primary).toBe(false);
        }
    });
});

// =============================================================================
// Split families — pure member first, one shade step per subtype
// =============================================================================

describe('buildAllocationRings — split families', () => {
    it('splits a full family into [pure member in the family colour, subtype shaded], pure first', () => {
        // The subtype outweighs the pure member and is listed first: neither may decide the order.
        const {hierarchy, layout} = ringsFor([entry('ETF_STOCK', 70), entry('BOND', 50), entry('STOCK', 30)]);

        expect(layout.rings).toBe(true);
        const family = baseArcOf(layout, 'STOCK');
        expect(family.color).toBe(PIE_PALETTE_LIGHT[0]);
        expect(family.memberCount).toBe(2);
        expect(family.weight).toBeCloseTo(100, 9);

        const members = outerArcsOf(layout, 'STOCK');
        expect(members).toHaveLength(2);
        expect(members.map((arc) => arc.role)).toEqual(['member', 'member']);
        expect(members.map((arc) => arc.key)).toEqual(['STOCK', 'ETF_STOCK']);
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
        expect(pure.items.map((item) => item.id)).toEqual(['item-STOCK']);
        expect(subtype.items.map((item) => item.id)).toEqual(['item-ETF_STOCK']);
        expect(family.items.map((item) => item.id)).toEqual(['item-STOCK', 'item-ETF_STOCK']);
    });

    it.each(PIE_PALETTES)('splits a family of three into three distinct colours, pure first then subtypes by weight, on %s', (_name, palette) => {
        // Barrier: the third member exists only through the injected resolver.
        expect(resolvePrimary('CROWDFUND_REAL_ESTATE')).toBe('CROWDFUND_REAL_ESTATE');
        expect(resolveWithThirdRealEstate('CROWDFUND_REAL_ESTATE')).toBe('REAL_ESTATE');

        // Input order and weight order disagree on purpose: the pure member is neither first
        // nor heaviest, and the subtypes are listed lightest first.
        const entries = [entry('ETF_REAL_ESTATE', 10), entry('STOCK', 100), entry('REAL_ESTATE', 20), entry('CROWDFUND_REAL_ESTATE', 30)];
        const {layout} = ringsFor(entries, {palette, resolve: resolveWithThirdRealEstate});

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
        const {layout} = ringsFor([entry('STOCK', 50), entry('ETF_STOCK', 25), bond]);
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
        const {layout} = ringsFor([entry('STOCK', 50), entry('ETF_STOCK', 20), liquidity]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['STOCK', 'LIQUIDITY']);

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
        expect(baseArcOf(layout, 'STOCK').memberCount).toBe(2);
        expect(layout.outer.filter((arc) => arc.role === 'member').map((arc) => arc.key)).toEqual(['STOCK', 'ETF_STOCK']);
    });

    it.each(['ETF', 'ETF_MONETARY'])('keeps %s as its own family — it resolves to itself — drawn as a filler', (key) => {
        // Both sit next to a real split family, so a rule keyed on the "ETF" prefix, or on an
        // underscore, would have somewhere to put them.
        const {layout} = ringsFor([entry('ETF', 40), entry('ETF_MONETARY', 25), entry('STOCK', 20), entry('ETF_STOCK', 15)]);

        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.primary)).toEqual(['ETF', 'STOCK', 'ETF_MONETARY']);

        const family = baseArcOf(layout, key);
        expect(family.memberCount).toBe(1);
        expect(family.split).toBe(false);
        expect(family.items.map((item) => item.id)).toEqual([`item-${key}`]);

        const outer = outerArcsOf(layout, key);
        expect(outer).toHaveLength(1);
        expect(outer[0].role).toBe('filler');
        expect(outer[0].key).toBe(key);
        expect(outer[0].weight).toBe(family.weight);

        // STOCK keeps exactly its own members.
        expect(outerArcsOf(layout, 'STOCK').map((arc) => arc.key)).toEqual(['STOCK', 'ETF_STOCK']);
    });
});

// =============================================================================
// Alignment — the reason the two rings line up
// =============================================================================

/** Every shape at once: a lone subtype, a full family, a family of three, four unsplit families. */
const EVERY_SHAPE_ENTRIES = [entry('ETF', 24.1), entry('CROWDFUND', 15.35), entry('BOND', 12.4), entry('ETF_BOND', 7.25), entry('ETF_STOCK', 9.8), entry('REAL_ESTATE', 6.5), entry('ETF_REAL_ESTATE', 4.05), entry('CROWDFUND_REAL_ESTATE', 3.3), entry('ETF_MONETARY', 2.2), entry('Liquidity', 0.05)];

const ALIGNMENT_SCENARIOS: ReadonlyArray<readonly [string, readonly Entry[], Resolver]> = [
    ['R12 real data', R12_ENTRIES, resolvePrimary],
    ['a full family', [entry('ETF_STOCK', 70), entry('BOND', 50), entry('STOCK', 30)], resolvePrimary],
    ['a family of three', [entry('ETF_REAL_ESTATE', 10), entry('STOCK', 100), entry('REAL_ESTATE', 20), entry('CROWDFUND_REAL_ESTATE', 30)], resolveWithThirdRealEstate],
    ['no subtype at all', [entry('STOCK', 40), entry('BOND', 35), entry('Liquidity', 25)], resolvePrimary],
    ['every shape at once', EVERY_SHAPE_ENTRIES, resolveWithThirdRealEstate],
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
        // Realistic, and deliberately tempting: a Title Case bucket and an ETF_ key that
        // resolves to itself, neither of which is a subtype.
        const plain = [entry('STOCK', 40), entry('BOND', 25), entry('ETF', 20), entry('CROWDFUND', 9.99), entry('ETF_MONETARY', 5), entry('Liquidity', 0.01)];
        const {layout} = ringsFor(plain);

        // Barrier: a non-empty layout, so "nothing is split" is not vacuous.
        expect(layout.base).toHaveLength(6);
        expect(layout.rings).toBe(false);
        expect(layout.base.map((arc) => arc.split)).toEqual([false, false, false, false, false, false]);
        expect(layout.outer.map((arc) => arc.role)).toEqual(['filler', 'filler', 'filler', 'filler', 'filler', 'filler']);

        // Control: one subtype more and the same portfolio switches — so the `false` above was
        // about the subtypes, not a constant.
        expect(ringsFor([...plain, entry('ETF_BOND', 1)]).layout.rings).toBe(true);
    });
});

// =============================================================================
// Degenerate palette
// =============================================================================

describe('buildAllocationRings — short palette', () => {
    it('never hands out an undefined colour when families outnumber the palette', () => {
        const palette = ['#1a4031', '#2563eb'];
        // Six families on two colours, with split families past the wrap point: the lone
        // ETF_REAL_ESTATE is shaded from a wrapped entry.
        const entries = [entry('STOCK', 30), entry('ETF_STOCK', 20), entry('BOND', 25), entry('ETF_BOND', 5), entry('CROWDFUND', 15), entry('ETF_REAL_ESTATE', 12), entry('ETF', 8), entry('Liquidity', 1)];
        const {layout} = ringsFor(entries, {palette});

        // Barrier: really more families than colours, and really two rings.
        expect(layout.base.length).toBeGreaterThan(palette.length);
        expect(layout.rings).toBe(true);
        expect(layout.base.map((arc) => arc.color)).toEqual(['#1a4031', '#2563eb', '#1a4031', '#2563eb', '#1a4031', '#2563eb']);

        // A 6-digit hex on every arc of both rings, as the ring item contract promises.
        for (const arc of [...layout.base, ...layout.outer]) {
            expect(arc.color, `${arc.role} ${arc.key}`).toMatch(/^#[0-9a-f]{6}$/i);
        }
    });
});

// =============================================================================
// AllocationPieChart — the data-only fast path, pinned by source
// =============================================================================

/** The guard of the data-only update in `AllocationPieChart.svelte`. */
const FAST_PATH_HEADER = /if\s*\(\s*chartFullyInitialized\s*&&\s*lastDark\s*===\s*isDark\s*&&\s*sameTypeSet\s*\)\s*\{/;

/** The three series of D72, as `ringSeries()` names them. */
const RING_SERIES_IDS = ['alloc-base', 'alloc-outer', 'alloc-base-labels'];

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
 * prefix of `alloc-base-labels`, so a substring test for the base ring would be satisfied
 * by the labels series alone — and so does `data`: `{id: 'alloc-outer'}` on its own is a
 * merge that changes nothing, the very stale ring this contract exists to prevent.
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

/**
 * The historical trap, with decoys: the three ids appear in a comment inside the fast path
 * and in a `ringSeries()` after it, so only a correct isolation *and* the comment stripping
 * can make the check fail here.
 */
const SINGLE_SERIES_FAST_PATH = `
        if (chartFullyInitialized && lastDark === isDark && sameTypeSet) {
            // was: {id: 'alloc-base', data: baseRingData}, {id: 'alloc-outer', data: outerRingData}, {id: 'alloc-base-labels', data: baseLabelData}
            chartInstance.setOption({series: [{data: chartData}]});
            return;
        }
        lastRawTypeKeys = currentRawTypeKeys;

        function ringSeries(): echarts.PieSeriesOption[] {
            return [
                {...shared, id: 'alloc-base', radius: pieRadius, data: baseRingData},
                {...shared, id: 'alloc-outer', radius: [splitRadius, pieRadius[1]], data: outerRingData},
                {...shared, id: 'alloc-base-labels', radius: [pieRadius[0], splitRadius], silent: true, data: baseLabelData},
            ];
        }
`;

describe('AllocationPieChart — data-only fast path (source contract)', () => {
    it('refreshes all three ring series by id, not only the first', () => {
        const source = readFileSync(new URL('../AllocationPieChart.svelte', import.meta.url), 'utf8');

        // Barrier: exactly one fast path, so the block below is the one the chart runs.
        expect(source.match(new RegExp(FAST_PATH_HEADER.source, 'g')), 'fast-path guard').toHaveLength(1);
        const block = extractBlock(source, FAST_PATH_HEADER);
        expect(block, 'fast-path block not found — did its guard change?').not.toBeNull();

        // Barrier: it is the data-only update — it calls setOption and returns early — and the
        // extraction stopped at its closing brace instead of running on into `ringSeries()`,
        // which names all three ids and would satisfy the check by itself.
        expect(block!.code).toMatch(/\.setOption\(/);
        expect(block!.code).toMatch(/\breturn\s*;/);
        expect(block!.code, 'extraction ran past the fast path').not.toContain('ringSeries');

        expectEveryRingSeriesRefreshed(block!.code);
    });

    it('positive control: the same check fails on the historical `series: [{data: chartData}]`', () => {
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
    });
});
