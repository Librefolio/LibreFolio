/**
 * allocationHierarchy.test.ts — Unit tests for `buildAllocationHierarchy()` and
 * `shadeForDepth()`.
 *
 * Two things are being protected here, and they pull in opposite directions:
 *
 * 1. **Nothing may move that did not have to move.** When no two categories share
 *    a primary type — every sector chart, every geography chart, every
 *    single-type portfolio — the output must be *member for member* what the old
 *    index-based code produced. That is the `legacy pin` block, and it is the
 *    reason the group sort has to be stable.
 * 2. **A subtype must read as a shade of its parent, and still be separable.**
 *    That is a measurable claim, so it is measured: the ΔL between a parent and
 *    its child is asserted as a number, for every entry of all four real
 *    palettes. A "looks related" assertion that never computes the distance
 *    would pass under a rule that makes the two indistinguishable. "Real" is
 *    literal: the palettes are read from the components that declare them,
 *    through `$test/sourcePalettes`, not copied — a copy agrees with itself.
 *
 * `resolvePrimary` is a **stub** on purpose. The real `primaryAssetType` lives in
 * `$lib/utils/assetTypes`, which reads the generated Zodios schemas at module
 * load — importing it would drag a gitignored build artifact into a unit test.
 * The module under test takes the function as an option precisely so this file
 * does not have to. The one exception is the block that measures whole
 * families: the family K's taxonomy makes of REAL_ESTATE is built through K2
 * itself, imported for real, and the stub is checked against K2 there.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module components/charts/__tests__/allocationHierarchy.test
 */
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

import {PALETTE_SLOTS, paletteDefects, readSourcePalette} from '$test/sourcePalettes';

import {buildAllocationHierarchy, shadeForDepth} from '../allocationHierarchy';
import {hexToHsl} from '$lib/utils/colors';

// =============================================================================
// Fixtures
// =============================================================================

const PIE_CHART = new URL('../AllocationPieChart.svelte', import.meta.url);
const HISTORY_CHART = new URL('../../dashboard/AllocationHistoryChart.svelte', import.meta.url);

/** `PALETTE_LIGHT` in `AllocationPieChart.svelte`. */
const PIE_PALETTE_LIGHT = readSourcePalette(PIE_CHART, 'PALETTE_LIGHT');
/** `PALETTE_DARK` in `AllocationPieChart.svelte`. */
const PIE_PALETTE_DARK = readSourcePalette(PIE_CHART, 'PALETTE_DARK');
/** `PALETTE_LIGHT` in `AllocationHistoryChart.svelte`. */
const HISTORY_PALETTE_LIGHT = readSourcePalette(HISTORY_CHART, 'PALETTE_LIGHT');
/** `PALETTE_DARK` in `AllocationHistoryChart.svelte`. */
const HISTORY_PALETTE_DARK = readSourcePalette(HISTORY_CHART, 'PALETTE_DARK');

/** Both themes, both charts. "In both themes" means all four of these. */
const ALL_PALETTES: ReadonlyArray<readonly [string, readonly string[]]> = [
    ['AllocationPieChart PALETTE_LIGHT', PIE_PALETTE_LIGHT],
    ['AllocationPieChart PALETTE_DARK', PIE_PALETTE_DARK],
    ['AllocationHistoryChart PALETTE_LIGHT', HISTORY_PALETTE_LIGHT],
    ['AllocationHistoryChart PALETTE_DARK', HISTORY_PALETTE_DARK],
];

/** Each chart's two themes, paired slot by slot (the comment above the constants in `AllocationHistoryChart.svelte`). */
const THEME_PAIRS: ReadonlyArray<readonly [string, readonly string[], readonly string[]]> = [
    ['AllocationPieChart', PIE_PALETTE_LIGHT, PIE_PALETTE_DARK],
    ['AllocationHistoryChart', HISTORY_PALETTE_LIGHT, HISTORY_PALETTE_DARK],
];

/**
 * Stub for contract K2 (`primaryAssetType`), reproducing its **real** semantics.
 *
 * Five ETF subtypes and real-estate crowdfunding fold onto the base type they
 * contain. Everything else — known enum member, unknown key, or the synthetic
 * `"Liquidity"` bucket — maps to **itself upper-cased**, never to `OTHER`: the
 * real implementation upper-cases *before* the lookup and returns that normalised
 * value even when the lookup misses, so `"Liquidity"` comes back as `"LIQUIDITY"`.
 * Only `null`, `undefined` and blank fall back to `OTHER`.
 *
 * K2 now ships as K's `primaryAssetType`, and the builder tests of this file stay
 * on this stub so that they do not import the generated client. A copy can drift,
 * so the block measuring whole families, which imports K for real, checks the
 * stub against it on every type the history chart can receive: a green test that
 * misstates its own contract misinforms with more authority than prose.
 */
const SUBTYPE_PARENT: Record<string, string> = {
    ETF_STOCK: 'STOCK',
    ETF_BOND: 'BOND',
    ETF_COMMODITY: 'COMMODITY',
    ETF_REAL_ESTATE: 'REAL_ESTATE',
    ETF_CRYPTO: 'CRYPTO',
    CROWDFUND_REAL_ESTATE: 'REAL_ESTATE',
};

const resolvePrimary = (key: string | null | undefined): string => {
    const raw = (key ?? '').trim().toUpperCase();
    if (!raw) return 'OTHER';
    return SUBTYPE_PARENT[raw] ?? raw;
};

interface Payload {
    id: string;
}

function entry(key: string, weight: number): {key: string; weight: number; item: Payload} {
    return {key, weight, item: {id: `item-${key}`}};
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

// =============================================================================
// The palettes under test — what was read, so no loop below can pass on nothing
// =============================================================================

describe('the palettes under test', () => {
    it.each(ALL_PALETTES)(`%s is ${PALETTE_SLOTS} distinct #rrggbb colours`, (_name, palette) => {
        expect(paletteDefects(palette), `the palette the chart draws with is not ${PALETTE_SLOTS} distinct colours: two slices would share one, or a slot is missing`).toEqual([]);
    });

    it.each(THEME_PAIRS)('%s pairs its light and dark palettes slot by slot', (_name, light, dark) => {
        expect(dark.length, 'the two themes are not the same length: a slot would change colour family when the theme changes').toBe(light.length);
    });
});

// =============================================================================
// The legacy pin — the guarantee that lets this ship at all
// =============================================================================

describe('buildAllocationHierarchy — legacy pin (no shared primaries)', () => {
    // Deliberately includes a three-way tie at 50: the old code used
    // `sort((a, b) => b.value - a.value)`, whose result for equal weights is
    // *insertion order*. If the new grouping sort were unstable, these three
    // would shuffle and the chart would repaint for no reason.
    const entries = [entry('STOCK', 100), entry('BOND', 50), entry('CRYPTO', 50), entry('CASH', 50), entry('COMMODITY', 20)];

    /** Verbatim transcription of the behaviour being replaced. */
    function legacy(input: typeof entries, palette: readonly string[]) {
        return [...input].sort((a, b) => b.weight - a.weight).map((e, i) => ({key: e.key, item: e.item, color: palette[i]}));
    }

    it.each(ALL_PALETTES)('reproduces the old order and colours member for member on %s', (_name, palette) => {
        const expected = legacy(entries, palette);
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette});

        // Positive barrier: a bug returning `[]` would satisfy every
        // element-wise check below by iterating zero times.
        expect(actual).toHaveLength(entries.length);
        expect(expected).toHaveLength(entries.length);

        expect(actual.map((r) => r.key)).toEqual(expected.map((r) => r.key));
        expect(actual.map((r) => r.color)).toEqual(expected.map((r) => r.color));
        expect(actual.map((r) => r.item)).toEqual(expected.map((r) => r.item));
    });

    it('spells the pinned order out, so the comparison cannot drift with the helper', () => {
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'BOND', 'CRYPTO', 'CASH', 'COMMODITY']);
        // Slots of the palette the chart really uses, spelled out without `legacy()`:
        // a literal copy of their colours would go red on a palette edit, not on the builder.
        expect(actual.map((r) => r.color)).toEqual([0, 1, 2, 3, 4].map((slot) => PIE_PALETTE_LIGHT[slot]));
    });

    it('breaks ties by input order, not by name — reversing the tied inputs reverses the output', () => {
        const reordered = [entry('STOCK', 100), entry('CASH', 50), entry('CRYPTO', 50), entry('BOND', 50), entry('COMMODITY', 20)];
        const actual = buildAllocationHierarchy(reordered, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(5);
        // Had the sort been alphabetical, or unstable-but-canonical, this would
        // still read BOND, CRYPTO, CASH as in the test above.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'CASH', 'CRYPTO', 'BOND', 'COMMODITY']);
        expect(actual.map((r) => r.color)).toEqual(legacy(reordered, PIE_PALETTE_LIGHT).map((r) => r.color));
    });

    it('leaves every entry unshaded when each one is its own group', () => {
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(5);
        expect(actual.map((r) => r.depth)).toEqual([0, 0, 0, 0, 0]);
        expect(actual.map((r) => r.groupSize)).toEqual([1, 1, 1, 1, 1]);
        // Verbatim palette entries — no hex → HSL → hex round trip.
        for (const [i, row] of actual.entries()) {
            expect(row.color).toBe(PIE_PALETTE_LIGHT[i]);
        }
    });
});

// =============================================================================
// Parent / child adjacency and shared hue
// =============================================================================

describe('buildAllocationHierarchy — subtype sits inside its parent', () => {
    it('places ETF_STOCK immediately after STOCK, sharing its hue', () => {
        const entries = [entry('BOND', 90), entry('ETF_STOCK', 40), entry('CASH', 80), entry('STOCK', 60)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(4);
        // Ordering is by *group* total, not by individual weight:
        // STOCK+ETF_STOCK = 100 > BOND = 90 > CASH = 80. Note that ETF_STOCK (40)
        // is individually the lightest entry and still lands second — that is the
        // whole point of grouping.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'BOND', 'CASH']);

        const [parent, child] = actual;
        expect(parent.primary).toBe('STOCK');
        expect(child.primary).toBe('STOCK');
        expect(parent.depth).toBe(0);
        expect(child.depth).toBe(1);

        // The parent keeps the palette entry verbatim; the child is derived.
        expect(parent.color).toBe(PIE_PALETTE_LIGHT[0]);
        expect(child.color).not.toBe(parent.color);

        // Same hue — measured, not assumed.
        expect(Math.abs(hueOf(child.color) - hueOf(parent.color))).toBeLessThanOrEqual(1);
    });

    it('keeps the pure member first even when the subtype outweighs it', () => {
        const entries = [entry('ETF_STOCK', 900), entry('STOCK', 1)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(2);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1]);
    });

    it('orders several subtypes of one parent by weight after the pure member', () => {
        const entries = [entry('ETF_STOCK', 30), entry('STOCK', 10)];
        const withExtra = [...entries, {key: 'STOCK_OPTION', weight: 50, item: {id: 'item-STOCK_OPTION'}}];
        const resolveWithExtra = (key: string) => (key === 'STOCK_OPTION' ? 'STOCK' : resolvePrimary(key));

        const actual = buildAllocationHierarchy(withExtra, {resolvePrimary: resolveWithExtra, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'STOCK_OPTION', 'ETF_STOCK']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1, 2]);
        // Each level is farther from the base than the one before it.
        const l0 = lightnessOf(actual[0].color);
        const l1 = lightnessOf(actual[1].color);
        const l2 = lightnessOf(actual[2].color);
        expect(Math.abs(l2 - l0)).toBeGreaterThan(Math.abs(l1 - l0));
    });
});

// =============================================================================
// Measured contrast — the bullet that kills the naive "always lighten" rule
// =============================================================================

describe('buildAllocationHierarchy — measured parent/child contrast', () => {
    /**
     * Push the STOCK group to a chosen group index by prefixing heavier
     * singleton fillers, so every palette slot is exercised through the real
     * builder rather than through `shadeForDepth` alone.
     */
    function entriesForPaletteIndex(index: number) {
        const fillers = Array.from({length: index}, (_, j) => entry(`FILLER_${j}`, 1000 - j));
        return [...fillers, entry('STOCK', 10), entry('ETF_STOCK', 5)];
    }

    it.each(ALL_PALETTES)('keeps ≥15 lightness points between parent and child for every entry of %s', (_name, palette) => {
        expect(palette.length).toBeGreaterThan(0);
        let pairsChecked = 0;

        for (let index = 0; index < palette.length; index++) {
            const actual = buildAllocationHierarchy(entriesForPaletteIndex(index), {resolvePrimary, palette});

            expect(actual).toHaveLength(index + 2);
            const parent = actual[index];
            const child = actual[index + 1];

            // Barrier: prove we are looking at the pair we think we are before
            // measuring anything about their colours.
            expect(parent.key).toBe('STOCK');
            expect(child.key).toBe('ETF_STOCK');
            expect(parent.color).toBe(palette[index]);
            expect(child.depth).toBe(1);

            const deltaL = Math.abs(lightnessOf(child.color) - lightnessOf(parent.color));
            expect(deltaL, `${palette[index]} → ${child.color} ΔL`).toBeGreaterThanOrEqual(15);

            // And the relationship survives: same hue, different lightness.
            expect(Math.abs(hueOf(child.color) - hueOf(parent.color)), `${palette[index]} → ${child.color} Δh`).toBeLessThanOrEqual(1);

            pairsChecked++;
        }

        // Without this the loop could have run zero times and still been green.
        expect(pairsChecked).toBe(palette.length);
    });

    it.each(ALL_PALETTES)('shades away from the nearer extreme on %s, so nothing washes out', (_name, palette) => {
        expect(palette.length).toBeGreaterThan(0);

        for (const base of palette) {
            const baseL = lightnessOf(base);
            const childL = lightnessOf(shadeForDepth(base, 1));

            if (baseL < 50) {
                expect(childL, `${base} (L=${baseL.toFixed(1)}) should lighten`).toBeGreaterThan(baseL);
            } else {
                expect(childL, `${base} (L=${baseL.toFixed(1)}) should darken`).toBeLessThan(baseL);
            }
            // The measured distance, again — a "moved in the right direction"
            // assertion is satisfied by moving one hundredth of a point.
            expect(Math.abs(childL - baseL)).toBeGreaterThanOrEqual(15);
            // Never clamped flat against an extreme.
            expect(childL).toBeGreaterThanOrEqual(0);
            expect(childL).toBeLessThanOrEqual(100);
        }
    });

    it('would have failed under an unconditional "always lighten" rule', () => {
        // #6366f1 sits at L≈67 in the *light* palette. Lightening it by 20 lands
        // at L≈87, which is where a white background eats it. Darkening keeps it
        // separable. This test states the case that motivated the per-colour rule.
        expect([...PIE_PALETTE_LIGHT, ...HISTORY_PALETTE_LIGHT], 'precondition: the motivating base is no longer in a light palette').toContain('#6366f1');
        const base = '#6366f1';
        const baseL = lightnessOf(base);
        expect(baseL).toBeGreaterThan(50);

        const child = shadeForDepth(base, 1);
        expect(lightnessOf(child)).toBeLessThan(baseL);
        expect(lightnessOf(child)).toBeLessThan(80);
    });
});

// =============================================================================
// Measured contrast across a whole family — the families K's taxonomy makes
// =============================================================================

/** `__tests__` → `charts` → `components` → `lib`, then `api/generated.ts`. */
const GENERATED_TS = fileURLToPath(new URL('../../../api/generated.ts', import.meta.url));

describe('buildAllocationHierarchy — measured contrast across a whole family (K)', () => {
    /**
     * The pair rule above, stated for a whole family. A family is no longer `{pure, one subtype}`:
     * by **content** — `primaryAssetType`, the history chart's grouping — REAL_ESTATE gathers
     * ETF_REAL_ESTATE and CROWDFUND_REAL_ESTATE, and that family is measured here, on the palettes of
     * the chart that draws it and nowhere else: a family no chart draws is not a claim about the
     * product. By **vehicle** the pie's ETF family holds up to seven members, more than lightness
     * shading can keep apart; that is the known limit recorded in `allocationHierarchy.ts` ("How many
     * members a group holds"), and its measurement returns with the shading fix.
     *
     * The members are read off the enum through K2 itself, imported for real — so a subtype K adds
     * tomorrow joins its family here without anyone touching this file — and pushed to every palette
     * slot through the real builder, as the pair test does.
     *
     * `assetTypes.ts` reads the generated client at module load, so the import is dynamic, local to
     * this block, and follows a check that the file exists: a missing client is reported with the
     * command that fixes it, never skipped.
     */
    async function importTaxonomy() {
        expect(existsSync(GENERATED_TS), "src/lib/api/generated.ts is absent, so assetTypes.ts cannot be imported and K's families cannot be built. Run `./dev.py api sync`.").toBe(true);
        const assetTypes = await import('$lib/utils/assetTypes');
        return {primaryAssetType: assetTypes.primaryAssetType, ASSET_TYPES: [...assetTypes.ASSET_TYPES] as string[]};
    }

    /** The history chart's two themes: the chart that groups by content. */
    const HISTORY_PALETTES: ReadonlyArray<readonly [string, readonly string[]]> = [
        ['AllocationHistoryChart PALETTE_LIGHT', HISTORY_PALETTE_LIGHT],
        ['AllocationHistoryChart PALETTE_DARK', HISTORY_PALETTE_DARK],
    ];

    /** The members of `family` under `resolve`, read off the enum: its pure member first, then the others in enum order. */
    function membersOf(types: readonly string[], resolve: (key: string) => string, family: string): string[] {
        const members = types.filter((type) => resolve(type) === family);
        return [...members.filter((type) => type === family), ...members.filter((type) => type !== family)];
    }

    /** Heavier singleton fillers push the family to slot `index`; its weights descend in the order given, so the depth follows it. */
    function familyAtPaletteIndex(index: number, members: readonly string[]) {
        const fillers = Array.from({length: index}, (_, j) => entry(`FILLER_${j}`, 1000 - j));
        return [...fillers, ...members.map((key, rank) => entry(key, 10 * (members.length - rank)))];
    }

    /**
     * The pair rule, applied to every pair of a family on every slot of `palette`: two members never
     * share a colour and stay at least 15 lightness points apart — the threshold of the pair test —
     * and every member keeps the hue of the pure member (within 1°). One line per slot that breaks
     * it, with every member's colour and lightness, so a red says what the reader would see.
     */
    function familyDefects(palette: readonly string[], members: readonly string[], resolve: (key: string) => string, family: string) {
        const defects: string[] = [];
        let slotsChecked = 0;

        for (let index = 0; index < palette.length; index++) {
            const actual = buildAllocationHierarchy(familyAtPaletteIndex(index, members), {resolvePrimary: resolve, palette});
            expect(actual).toHaveLength(index + members.length);
            const rows = actual.slice(index);

            // Barrier: the whole family, at this slot, in the order it was built, before anything is
            // measured about its colours.
            expect(rows.map((row) => row.key)).toEqual([...members]);
            expect(rows.map((row) => row.primary)).toEqual(members.map(() => family));
            expect(rows.map((row) => row.groupSize)).toEqual(members.map(() => members.length));
            expect(rows.map((row) => row.depth)).toEqual(members.map((_, depth) => depth));
            expect(rows[0].color).toBe(palette[index]);

            const lightness = rows.map((row) => lightnessOf(row.color));
            const hue = rows.map((row) => hueOf(row.color));
            const problems: string[] = [];
            for (let i = 0; i < rows.length; i++) {
                for (let j = i + 1; j < rows.length; j++) {
                    const deltaL = Math.abs(lightness[i] - lightness[j]);
                    if (rows[i].color === rows[j].color) problems.push(`${rows[i].key} and ${rows[j].key} share ${rows[i].color}`);
                    else if (deltaL < 15) problems.push(`${rows[i].key}/${rows[j].key} ΔL ${deltaL.toFixed(1)}`);
                }
            }
            for (let depth = 1; depth < rows.length; depth++) {
                const deltaH = Math.abs(hue[depth] - hue[0]);
                if (deltaH > 1) problems.push(`${rows[depth].key} Δh ${deltaH.toFixed(1)}`);
            }
            if (problems.length > 0) defects.push(`slot ${index} ${palette[index]} → ${rows.map((row, depth) => `${row.key} ${row.color} (L ${lightness[depth].toFixed(0)})`).join(', ')}: ${problems.join('; ')}`);
            slotsChecked++;
        }

        return {defects, slotsChecked};
    }

    it('checks the K2 stub of the tests above against primaryAssetType, on every type the history chart can receive', async () => {
        const {primaryAssetType, ASSET_TYPES} = await importTaxonomy();

        // `by_type` carries the enum values and the synthetic cash bucket, in the engine's spelling.
        const domain = [...ASSET_TYPES, 'Liquidity'];
        // Anti-vacuous: the enum was read, with the subtypes that move and the one K2 keeps as itself.
        expect(domain).toEqual(expect.arrayContaining(['STOCK', 'ETF_STOCK', 'ETF_MONETARY', 'CROWDFUND_REAL_ESTATE', 'Liquidity']));

        const disagreements = domain.filter((type) => resolvePrimary(type) !== primaryAssetType(type)).map((type) => `${type}: stub ${resolvePrimary(type)}, primaryAssetType ${primaryAssetType(type)}`);
        expect(disagreements, 'the K2 stub of this file no longer mirrors primaryAssetType: the builder tests above would check a grouping no chart draws').toEqual([]);
    });

    it.each(HISTORY_PALETTES)('by content, REAL_ESTATE holds REAL_ESTATE, ETF_REAL_ESTATE and CROWDFUND_REAL_ESTATE — one separable shade each, on its hue, for every entry of %s', async (_name, palette) => {
        const {primaryAssetType, ASSET_TYPES} = await importTaxonomy();
        const members = membersOf(ASSET_TYPES, primaryAssetType, 'REAL_ESTATE');
        // Anti-vacuous: K2 really makes this family, with the pure member leading.
        expect(members).toEqual(expect.arrayContaining(['REAL_ESTATE', 'ETF_REAL_ESTATE', 'CROWDFUND_REAL_ESTATE']));
        expect(members[0]).toBe('REAL_ESTATE');

        const {defects, slotsChecked} = familyDefects(palette, members, primaryAssetType, 'REAL_ESTATE');
        expect(slotsChecked, 'the loop ran on fewer slots than the palette holds').toBe(palette.length);
        expect(defects, `members of the ${members.length}-member REAL_ESTATE family the history chart cannot tell apart, or that leave its hue`).toEqual([]);
    });
});

// =============================================================================
// Grouping semantics
// =============================================================================

describe('buildAllocationHierarchy — grouping', () => {
    it('groups REAL_ESTATE with ETF_REAL_ESTATE, and never produces "REAL"', () => {
        const entries = [entry('ETF_REAL_ESTATE', 30), entry('REAL_ESTATE', 70), entry('BOND', 20)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['REAL_ESTATE', 'ETF_REAL_ESTATE', 'BOND']);

        // Positive form first: the primary is the *whole* underscored key.
        expect(actual[0].primary).toBe('REAL_ESTATE');
        expect(actual[1].primary).toBe('REAL_ESTATE');
        expect(actual[0].groupSize).toBe(2);
        expect(actual[1].groupSize).toBe(2);

        // Then the guard against a future `key.split('_')[0]`, which would
        // bucket these under "REAL" — and quietly sweep in any other
        // REAL_-prefixed type.
        expect(actual.map((r) => r.primary)).not.toContain('REAL');
    });

    it('maps an unknown key to itself, forming its own group — never to OTHER', () => {
        const entries = [entry('WIDGETS', 50), entry('STOCK', 80), entry('ETF_STOCK', 10)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(3);

        const widgets = actual.find((r) => r.key === 'WIDGETS');
        expect(widgets, 'WIDGETS must survive the grouping').toBeDefined();
        expect(widgets!.primary).toBe('WIDGETS');
        expect(widgets!.groupSize).toBe(1);
        expect(widgets!.depth).toBe(0);
        expect(widgets!.primaryTotal).toBe(50);

        expect(actual.map((r) => r.primary)).not.toContain('OTHER');
    });

    it('groups the synthetic "Liquidity" bucket on its own, unshaded', () => {
        // `portfolio_engine.py` emits this Title Case key alongside the
        // SCREAMING_CASE enum members. It must be a first-class group, not a
        // subtype of anything and not a shaded straggler.
        const entries = [entry('Liquidity', 40), entry('STOCK', 90), entry('ETF_STOCK', 20)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'Liquidity']);

        const liquidity = actual[2];
        expect(liquidity.key).toBe('Liquidity'); // original casing preserved
        expect(liquidity.primary).toBe('LIQUIDITY'); // group key is upper-cased
        expect(liquidity.groupSize).toBe(1);
        expect(liquidity.depth).toBe(0);
        expect(liquidity.color).toBe(PIE_PALETTE_LIGHT[1]); // verbatim, not shaded
        expect(liquidity.primaryTotal).toBe(40);
    });

    it('case-folds "Liquidity" and "LIQUIDITY" into one bucket, with neither demoted for its casing', () => {
        // Pinning the *documented* behaviour: `sameKey()` is deliberately
        // case-insensitive, and the group key is upper-cased, so a Title Case
        // key is recognised as its group's pure member instead of being pushed
        // behind a differently-cased sibling. The two do not become rival
        // groups, and neither is dropped.
        const entries = [entry('LIQUIDITY', 15), entry('Liquidity', 40)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(2);
        expect(new Set(actual.map((r) => r.primary))).toEqual(new Set(['LIQUIDITY']));
        expect(actual.map((r) => r.groupSize)).toEqual([2, 2]);
        expect(actual.map((r) => r.primaryTotal)).toEqual([55, 55]);
        // Both are "pure" by sameKey(), so the tie-break is weight — casing
        // never decides the order.
        expect(actual.map((r) => r.key)).toEqual(['Liquidity', 'LIQUIDITY']);
        expect(actual.map((r) => r.depth)).toEqual([0, 1]);
    });
});

// =============================================================================
// groupSize / primaryTotal
// =============================================================================

describe('buildAllocationHierarchy — group metadata', () => {
    it('reports the summed group weight and member count on every row', () => {
        const entries = [entry('STOCK', 60), entry('ETF_STOCK', 40), entry('BOND', 70), entry('ETF_BOND', 5), entry('CASH', 30)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(5);
        // Group totals: STOCK 100 > BOND 75 > CASH 30.
        expect(actual.map((r) => r.key)).toEqual(['STOCK', 'ETF_STOCK', 'BOND', 'ETF_BOND', 'CASH']);

        expect(actual.map((r) => r.primaryTotal)).toEqual([100, 100, 75, 75, 30]);
        expect(actual.map((r) => r.groupSize)).toEqual([2, 2, 2, 2, 1]);

        // A singleton reports 1 and its own weight.
        const cash = actual[4];
        expect(cash.key).toBe('CASH');
        expect(cash.groupSize).toBe(1);
        expect(cash.primaryTotal).toBe(30);
    });

    it('carries the caller payload through untouched', () => {
        const stock = entry('STOCK', 10);
        const etf = entry('ETF_STOCK', 5);
        const actual = buildAllocationHierarchy([stock, etf], {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(2);
        expect(actual[0].item).toBe(stock.item);
        expect(actual[1].item).toBe(etf.item);
    });

    it('never shades a singleton group, even the one at palette index 0', () => {
        const actual = buildAllocationHierarchy([entry('STOCK', 10)], {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(1);
        expect(actual[0].depth).toBe(0);
        expect(actual[0].groupSize).toBe(1);
        expect(actual[0].color).toBe(PIE_PALETTE_LIGHT[0]);
    });
});

// =============================================================================
// Degenerate inputs
// =============================================================================

describe('buildAllocationHierarchy — degenerate inputs', () => {
    it('wraps a short palette with % instead of handing out undefined', () => {
        const palette = ['#1a4031', '#2563eb'];
        const entries = [entry('STOCK', 50), entry('BOND', 40), entry('CASH', 30), entry('CRYPTO', 20), entry('COMMODITY', 10)];

        let actual: ReturnType<typeof buildAllocationHierarchy<Payload>> = [];
        expect(() => {
            actual = buildAllocationHierarchy(entries, {resolvePrimary, palette});
        }).not.toThrow();

        expect(actual).toHaveLength(5);
        expect(actual.map((r) => r.color)).toEqual(['#1a4031', '#2563eb', '#1a4031', '#2563eb', '#1a4031']);
        for (const row of actual) {
            expect(row.color).toBeTypeOf('string');
        }
    });

    it('returns [] for empty entries', () => {
        expect(buildAllocationHierarchy([], {resolvePrimary, palette: PIE_PALETTE_LIGHT})).toEqual([]);
    });

    it('returns [] for an empty palette', () => {
        const entries = [entry('STOCK', 10), entry('ETF_STOCK', 5)];
        // The same entries against a real palette are non-empty, so the [] above
        // is the palette's doing and not an inert input.
        expect(buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT})).toHaveLength(2);
        expect(buildAllocationHierarchy(entries, {resolvePrimary, palette: []})).toEqual([]);
    });

    it('accepts zero and negative weights without reordering into nonsense', () => {
        const entries = [entry('STOCK', 0), entry('BOND', 0), entry('CASH', 5)];
        const actual = buildAllocationHierarchy(entries, {resolvePrimary, palette: PIE_PALETTE_LIGHT});

        expect(actual).toHaveLength(3);
        expect(actual.map((r) => r.key)).toEqual(['CASH', 'STOCK', 'BOND']);
    });
});

// =============================================================================
// shadeForDepth in isolation
// =============================================================================

describe('shadeForDepth', () => {
    it('returns the base verbatim at depth 0 and below', () => {
        expect(shadeForDepth('#1a4031', 0)).toBe('#1a4031');
        expect(shadeForDepth('#1a4031', -1)).toBe('#1a4031');
    });

    it('lightens a dark base and darkens a light one', () => {
        const dark = '#1a4031'; // L ≈ 18
        const light = '#a5b4fc'; // L ≈ 82
        expect(lightnessOf(dark)).toBeLessThan(50);
        expect(lightnessOf(light)).toBeGreaterThan(50);

        expect(lightnessOf(shadeForDepth(dark, 1))).toBeGreaterThan(lightnessOf(dark));
        expect(lightnessOf(shadeForDepth(light, 1))).toBeLessThan(lightnessOf(light));
    });

    it('darkens at exactly L=50, where the rule is `l < 50 → lighten`', () => {
        const base = '#ff0000'; // L is exactly 50
        expect(lightnessOf(base)).toBe(50);
        expect(lightnessOf(shadeForDepth(base, 1))).toBeCloseTo(30, 4);
        expect(shadeForDepth(base, 1)).toBe('#990000');
    });

    it('defaults to a 20-point step', () => {
        expect(shadeForDepth('#1a4031', 1)).toBe(shadeForDepth('#1a4031', 1, 20));
        expect(lightnessOf(shadeForDepth('#1a4031', 1))).toBeCloseTo(lightnessOf('#1a4031') + 20, 1);
    });

    it('scales the step with depth', () => {
        const base = '#1a4031';
        expect(lightnessOf(shadeForDepth(base, 2))).toBeCloseTo(lightnessOf(base) + 40, 1);
        expect(lightnessOf(shadeForDepth(base, 1, 10))).toBeCloseTo(lightnessOf(base) + 10, 1);
    });

    it('clamps to [0, 100] instead of overflowing', () => {
        expect(shadeForDepth('#1a4031', 1, 500)).toBe('#ffffff');
        expect(shadeForDepth('#a5b4fc', 1, 500)).toBe('#000000');
        expect(lightnessOf(shadeForDepth('#1a4031', 1, 500))).toBe(100);
        expect(lightnessOf(shadeForDepth('#a5b4fc', 1, 500))).toBe(0);
    });

    it('preserves hue and saturation, moving only lightness', () => {
        const base = '#0d9488';
        const shaded = shadeForDepth(base, 1);
        const before = hexToHsl(base)!;
        const after = hexToHsl(shaded)!;

        expect(shaded).not.toBe(base); // something actually happened
        expect(after.h).toBeCloseTo(before.h, 0);
        expect(after.s).toBeCloseTo(before.s, 0);
        expect(Math.abs(after.l - before.l)).toBeGreaterThanOrEqual(15);
    });

    it('returns an unparseable base unchanged rather than black', () => {
        for (const bad of ['nope', '', '#12345', 'rgb(1,2,3)', 'var(--chart-1)']) {
            expect(shadeForDepth(bad, 1)).toBe(bad);
            expect(shadeForDepth(bad, 1)).not.toBe('#000000');
        }
        // …while a good base in the same breath really does change, so the
        // block above is not passing because shading is a no-op everywhere.
        expect(shadeForDepth('#0d9488', 1)).not.toBe('#0d9488');
    });

    it('handles achromatic bases without producing NaN', () => {
        // #a3a3a3 is a real HISTORY_PALETTE_LIGHT entry: s = 0, hue undefined. Checked, not
        // assumed — the palette is read from the chart, so this can go stale only loudly.
        expect(HISTORY_PALETTE_LIGHT, 'precondition: the achromatic base is no longer a real palette entry').toContain('#a3a3a3');
        const shaded = shadeForDepth('#a3a3a3', 1);
        expect(hexToHsl(shaded)).not.toBeNull();
        expect(Number.isNaN(lightnessOf(shaded))).toBe(false);
        expect(Math.abs(lightnessOf(shaded) - lightnessOf('#a3a3a3'))).toBeGreaterThanOrEqual(15);
        expect(shaded).toMatch(/^#[0-9a-f]{6}$/);
    });
});
