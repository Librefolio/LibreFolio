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
 * 3. **A large family must stay separable too — measured with a perceptual ruler.**
 *    By vehicle the pie's ETF family holds seven members, more than a one-sided
 *    lightness walk keeps apart: it clamps to white or black. Rule B, the
 *    developer's choice of 01/10/2026, spreads a family of four or more on both
 *    sides of its base inside L [10, 90] and halves the saturation of every even
 *    depth. Its criterion is perceptual rather than a ΔL: every pair at least as
 *    far apart in CIEDE2000 as the closest pair the pie already draws today
 *    (groups of two and three), every member within 3° of its family's hue. The
 *    ruler is this file's own, proven on published reference data before it
 *    measures anything. Groups of up to three, and the default with no group
 *    size, are pinned byte for byte, so the history chart and every other caller
 *    stay where they are. And rule B itself is pinned shade by shade where the
 *    criterion is blind — the gap capped at `step`, ties going to the first k —
 *    on values captured from the implementation the developer approved.
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
import {hexToHsl, hslToHex} from '$lib/utils/colors';

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
 * The pie's two themes: the only chart that groups by vehicle. Module-level, not inside the block
 * measuring K's families: the floor and the synthetic families of rule B are measured on it too.
 */
const PIE_PALETTES: ReadonlyArray<readonly [string, readonly string[]]> = [
    ['AllocationPieChart PALETTE_LIGHT', PIE_PALETTE_LIGHT],
    ['AllocationPieChart PALETTE_DARK', PIE_PALETTE_DARK],
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

/** Hue distance on the circle: 359.9° and 0.1° are 0.2° apart, not 359.8°. */
function hueDistance(a: string, b: string): number {
    const delta = Math.abs(hueOf(a) - hueOf(b));
    return Math.min(delta, 360 - delta);
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
// The ruler — CIEDE2000, proven on published data before it measures anything
// =============================================================================

/** A colour in CIELAB, D65 white: `[L*, a*, b*]`. */
type Lab = readonly [number, number, number];

/**
 * `#rrggbb` → CIELAB (D65): the sRGB transfer function (IEC 61966-2-1), the sRGB → XYZ matrix in its
 * seven-digit form — whose rows sum to the D65 white it divides by, so white lands on L* 100 with
 * a* = b* = 0 — then CIE 1976 L*a*b* with the exact ε = 216/24389 and κ = 24389/27.
 *
 * Throws on anything else: a ruler returning NaN compares false with every floor, and a family
 * measured with it would pass in silence.
 */
function labOf(hex: string): Lab {
    const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex);
    if (!match) throw new Error(`labOf: ${hex} is not #rrggbb`);
    const [r, g, b] = match.slice(1).map((channel) => {
        const c = parseInt(channel, 16) / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
    });
    const x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b;
    const y = 0.2126729 * r + 0.7151522 * g + 0.072175 * b;
    const z = 0.0193339 * r + 0.119192 * g + 0.9503041 * b;
    const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
    const [fx, fy, fz] = [f(x / 0.95047), f(y), f(z / 1.08883)];
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/**
 * CIEDE2000 (CIE 142-2001), kL = kC = kH = 1, written out as Sharma, Wu & Dalal (2005) write it —
 * with the two conventions their test data exists to catch: the hue of a neutral colour is 0 (and
 * so is Δh' beside one), and the mean of two hues more than 180° apart is taken across 0°/360°.
 */
function ciede2000([L1, a1, b1]: Lab, [L2, a2, b2]: Lab): number {
    const rad = Math.PI / 180;
    const meanC7 = ((Math.hypot(a1, b1) + Math.hypot(a2, b2)) / 2) ** 7;
    const G = 0.5 * (1 - Math.sqrt(meanC7 / (meanC7 + 25 ** 7)));
    const a1p = (1 + G) * a1;
    const a2p = (1 + G) * a2;
    const C1p = Math.hypot(a1p, b1);
    const C2p = Math.hypot(a2p, b2);
    const hueAngle = (b: number, ap: number) => (b === 0 && ap === 0 ? 0 : (Math.atan2(b, ap) / rad + 360) % 360);
    const h1p = hueAngle(b1, a1p);
    const h2p = hueAngle(b2, a2p);

    let dhp = 0;
    if (C1p * C2p !== 0) {
        dhp = h2p - h1p;
        if (dhp > 180) dhp -= 360;
        else if (dhp < -180) dhp += 360;
    }
    const dLp = L2 - L1;
    const dCp = C2p - C1p;
    const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * rad);

    const meanLp = (L1 + L2) / 2;
    const meanCp = (C1p + C2p) / 2;
    let meanHp: number;
    if (C1p * C2p === 0) meanHp = h1p + h2p;
    else if (Math.abs(h1p - h2p) <= 180) meanHp = (h1p + h2p) / 2;
    else meanHp = h1p + h2p < 360 ? (h1p + h2p + 360) / 2 : (h1p + h2p - 360) / 2;

    const T = 1 - 0.17 * Math.cos((meanHp - 30) * rad) + 0.24 * Math.cos(2 * meanHp * rad) + 0.32 * Math.cos((3 * meanHp + 6) * rad) - 0.2 * Math.cos((4 * meanHp - 63) * rad);
    const meanCp7 = meanCp ** 7;
    const RT = -2 * Math.sqrt(meanCp7 / (meanCp7 + 25 ** 7)) * Math.sin(60 * Math.exp(-(((meanHp - 275) / 25) ** 2)) * rad);
    const SL = 1 + (0.015 * (meanLp - 50) ** 2) / Math.sqrt(20 + (meanLp - 50) ** 2);
    const SC = 1 + 0.045 * meanCp;
    const SH = 1 + 0.015 * meanCp * T;
    return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}

/** The perceptual distance between two `#rrggbb` colours. */
function deltaE00(a: string, b: string): number {
    return ciede2000(labOf(a), labOf(b));
}

/**
 * Rows of the test data published with the formula's implementation notes — G. Sharma, W. Wu and
 * E. N. Dalal, "The CIEDE2000 color-difference formula: implementation notes, supplementary test
 * data, and mathematical observations", Color Research & Application 30(1), 2005, table 1 — one per
 * branch an implementation gets wrong, with the published ΔE00 to four decimals.
 */
const SHARMA_PAIRS: ReadonlyArray<{pair: number; first: Lab; second: Lab; deltaE: number; branch: string}> = [
    {pair: 1, first: [50, 2.6772, -79.7751], second: [50, 0, -82.7485], deltaE: 2.0425, branch: 'blues near 275°, where the rotation term R_T acts'},
    {pair: 7, first: [50, 0, 0], second: [50, -1, 2], deltaE: 2.3669, branch: "a neutral colour: its hue is 0, and so is Δh'"},
    {pair: 10, first: [50, 2.49, -0.001], second: [50, -2.49, 0.001], deltaE: 7.1792, branch: 'two hues 180° apart, their mean on one side of 0°/360°'},
    {pair: 11, first: [50, 2.49, -0.001], second: [50, -2.49, 0.0011], deltaE: 7.2195, branch: 'the same, 0.0001 away, on the other side — the branch most implementations get wrong'},
    {pair: 17, first: [50, 2.5, 0], second: [73, 25, -18], deltaE: 27.1492, branch: 'a large difference, its lightness weighted by S_L away from L* 50'},
];

/**
 * CIELAB (D65) of a few sRGB colours. White, black and mid grey are exact by construction — a
 * neutral colour has a* = b* = 0, and #808080 has L* 53.585 from the transfer function alone; the
 * primaries are the values Lindbloom's reference equations give, the ones colour libraries test
 * their converters against.
 */
const SRGB_LAB: ReadonlyArray<{hex: string; lab: Lab}> = [
    {hex: '#ffffff', lab: [100, 0, 0]},
    {hex: '#000000', lab: [0, 0, 0]},
    {hex: '#808080', lab: [53.585, 0, 0]},
    {hex: '#ff0000', lab: [53.2408, 80.0925, 67.2032]},
    {hex: '#0000ff', lab: [32.297, 79.1875, -107.8602]},
];

describe('the ruler — CIEDE2000, checked against published data before it measures anything', () => {
    it.each(SHARMA_PAIRS)('reproduces pair $pair of Sharma, Wu & Dalal (2005), ΔE00 $deltaE — $branch', ({first, second, deltaE}) => {
        // Both orders: the formula is symmetric, an implementation that reads one hue twice is not.
        expect(Math.abs(ciede2000(first, second) - deltaE), 'first → second').toBeLessThanOrEqual(1e-4);
        expect(Math.abs(ciede2000(second, first) - deltaE), 'second → first').toBeLessThanOrEqual(1e-4);
    });

    it.each(SRGB_LAB)('converts $hex to its published CIELAB (D65) coordinates', ({hex, lab}) => {
        const measured = labOf(hex);
        lab.forEach((expected, axis) => expect(Math.abs(measured[axis] - expected), `${hex} ${['L*', 'a*', 'b*'][axis]}`).toBeLessThanOrEqual(1e-3));
    });
});

// =============================================================================
// The floor — the closest pair the pie draws today
// =============================================================================

/**
 * The floor every family of rule B is held to: the closest pair the pie already draws. Today's
 * groups of two and three — the pure entry, `shadeForDepth(base, 1)` and `shadeForDepth(base, 2)`,
 * default step and no group size — on every slot of both pie palettes, every pair inside a group,
 * measured with the ruler above: the smallest distance found, and where.
 *
 * Why this and not a lightness gap: the parked criterion, 15 lightness points between members,
 * cannot be met by seven members on one hue — inside a usable band lightness alone reaches about
 * 11.5 points (the developer's measurement, R5 plan, 01/10/2026). What a reader tells apart is the
 * perceptual distance, and the families the pie has drawn since D71 set the bar.
 */
function closestPairOfTodaysSmallGroups(palettes: ReadonlyArray<readonly [string, readonly string[]]>): {deltaE: number; pair: string; pairsMeasured: number} {
    let closest = {deltaE: Infinity, pair: 'none', pairsMeasured: 0};
    for (const [name, palette] of palettes) {
        palette.forEach((base, slot) => {
            for (const size of [2, 3]) {
                const group = Array.from({length: size}, (_, depth) => shadeForDepth(base, depth));
                for (let i = 0; i < size; i++) {
                    for (let j = i + 1; j < size; j++) {
                        const deltaE = deltaE00(group[i], group[j]);
                        closest.pairsMeasured++;
                        if (deltaE < closest.deltaE) closest = {...closest, deltaE, pair: `${name} slot ${slot}, a group of ${size}: ${group[i]} (depth ${i}) and ${group[j]} (depth ${j})`};
                    }
                }
            }
        });
    }
    return closest;
}

const FLOOR = closestPairOfTodaysSmallGroups(PIE_PALETTES);

describe('the floor — the closest pair the pie draws today', () => {
    it(`premise: today's groups of two and three on the pie palettes are never closer than ΔE00 ${FLOOR.deltaE.toFixed(2)}, and that is above 5`, () => {
        // Anti-vacuous: one pair per group of two and three per group of three, on every slot — the
        // minimum over nothing is +∞, and +∞ is above 5.
        expect(FLOOR.pairsMeasured, 'the floor was not measured on every slot of both pie palettes').toBe(4 * (PIE_PALETTE_LIGHT.length + PIE_PALETTE_DARK.length));
        expect(Number.isFinite(FLOOR.deltaE), `the floor is not a finite distance: ${FLOOR.deltaE}`).toBe(true);
        expect(FLOOR.deltaE, `the closest pair today — ${FLOOR.pair} — is no longer above 5: a floor this low would pass families a reader cannot tell apart`).toBeGreaterThan(5);
    });
});

// =============================================================================
// Families on every slot — what the family blocks below share
// =============================================================================

/** Heavier singleton fillers push the family to slot `index`; its weights descend in the order given, so the depth follows it. */
function familyAtPaletteIndex(index: number, members: readonly string[]) {
    const fillers = Array.from({length: index}, (_, j) => entry(`FILLER_${j}`, 1000 - j));
    return [...fillers, ...members.map((key, rank) => entry(key, 10 * (members.length - rank)))];
}

/**
 * The family's rows at slot `index`, through the real builder — after the barrier proving they are
 * the rows meant: the whole family, at this slot, in the order it was built, its pure member on the
 * palette entry verbatim.
 */
function familyRowsAtSlot(palette: readonly string[], index: number, members: readonly string[], resolve: (key: string) => string, family: string) {
    const actual = buildAllocationHierarchy(familyAtPaletteIndex(index, members), {resolvePrimary: resolve, palette});
    expect(actual).toHaveLength(index + members.length);
    const rows = actual.slice(index);

    expect(rows.map((row) => row.key)).toEqual([...members]);
    expect(rows.map((row) => row.primary)).toEqual(members.map(() => family));
    expect(rows.map((row) => row.groupSize)).toEqual(members.map(() => members.length));
    expect(rows.map((row) => row.depth)).toEqual(members.map((_, depth) => depth));
    expect(rows[0].color).toBe(palette[index]);
    return rows;
}

/** Rule B's band: a shaded member's HSL lightness stays inside it, off black and off white. */
const LIGHTNESS_BAND = [10, 90] as const;

/**
 * What the hex round trip may move a lightness by: each channel is rounded to 1/255, so the
 * brightest and the darkest — whose mean the lightness is — move by half a step at most.
 */
const HEX_LIGHTNESS_QUANTUM = (0.5 / 255) * 100;

/** How far a member's hue may stray from its family's. Rule B keeps the hue; the hex quantisation of a halved saturation moves it by up to 2.2° (measured on both pie palettes). */
const HUE_TOLERANCE = 3;

/**
 * What breaks rule B's criterion in one family, one phrase per problem — empty when nothing does:
 * two members sharing a colour; two closer than `floor` in CIEDE2000 (`null`: not asserted, past the
 * documented limit); a shaded member more than 3° off the hue of depth 0, or outside L [10, 90].
 */
function perceptualProblems(members: ReadonlyArray<{label: string; color: string; depth: number}>, floor: number | null): string[] {
    const pure = members.find((member) => member.depth === 0);
    if (!pure) return ['no member at depth 0 to hold the hue against'];

    const problems: string[] = [];
    for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
            const [first, second] = [members[i], members[j]];
            if (first.color.toLowerCase() === second.color.toLowerCase()) {
                problems.push(`${first.label} and ${second.label} share ${first.color}`);
                continue;
            }
            if (floor === null) continue;
            const deltaE = deltaE00(first.color, second.color);
            // Negated on purpose: a NaN distance is a problem, not a pass.
            if (!(deltaE >= floor)) problems.push(`${first.label}/${second.label} ΔE00 ${deltaE.toFixed(2)}`);
        }
    }
    for (const member of members) {
        if (member.depth === 0) continue;
        const deltaH = hueDistance(member.color, pure.color);
        if (deltaH > HUE_TOLERANCE) problems.push(`${member.label} Δh ${deltaH.toFixed(1)}°`);
        const lightness = lightnessOf(member.color);
        if (lightness < LIGHTNESS_BAND[0] - HEX_LIGHTNESS_QUANTUM || lightness > LIGHTNESS_BAND[1] + HEX_LIGHTNESS_QUANTUM) problems.push(`${member.label} L ${lightness.toFixed(1)}`);
    }
    return problems;
}

/**
 * Rule B's criterion, applied to one family on every slot of `palette` through the real builder,
 * one line per slot that breaks it, with every member's colour — so a red says what the reader sees.
 *
 * Before measuring, the wiring: every member is shaded as one of a group of `members.length`. Today
 * `shadeForDepth` has no fourth parameter and ignores the argument, so that holds trivially; it binds
 * the moment the parameter exists.
 */
function perceptualFamilyDefects(palette: readonly string[], members: readonly string[], resolve: (key: string) => string, family: string, floor: number | null) {
    const defects: string[] = [];
    let slotsChecked = 0;

    for (let index = 0; index < palette.length; index++) {
        const rows = familyRowsAtSlot(palette, index, members, resolve, family);
        expect(
            rows.map((row) => row.color),
            `slot ${index}: the builder does not shade the family as a group of ${members.length}`,
        ).toEqual(rows.map((row) => shadeForDepth(palette[index], row.depth, undefined, members.length)));

        const problems = perceptualProblems(
            rows.map((row) => ({label: row.key, color: row.color, depth: row.depth})),
            floor,
        );
        if (problems.length > 0) defects.push(`slot ${index} ${palette[index]} → ${rows.map((row) => `${row.key} ${row.color}`).join(', ')}: ${problems.join('; ')}`);
        slotsChecked++;
    }

    return {defects, slotsChecked};
}

// =============================================================================
// Measured contrast across a whole family — the families K's taxonomy makes
// =============================================================================

/** `__tests__` → `charts` → `components` → `lib`, then `api/generated.ts`. */
const GENERATED_TS = fileURLToPath(new URL('../../../api/generated.ts', import.meta.url));

describe('buildAllocationHierarchy — measured contrast across a whole family (K)', () => {
    /**
     * The pair rule above, stated for a whole family. A family is no longer `{pure, one subtype}`:
     * by **content** — `primaryAssetType`, the history chart's grouping — REAL_ESTATE gathers
     * ETF_REAL_ESTATE and CROWDFUND_REAL_ESTATE; by **vehicle** — `assetTypeFamily`, the pie's — the
     * ETF family holds the generic ETF and every ETF subtype, seven members today. Each family is
     * measured on the palettes of the chart that draws it and nowhere else: a family no chart draws
     * is not a claim about the product.
     *
     * The family of three keeps the pair rule — 15 lightness points, 1° of hue — which today's
     * one-sided walk meets. The family of seven is beyond it: the walk clamps to white or black after
     * two to four steps (the defect of 28/09, recorded in `allocationHierarchy.ts`, "How many members a
     * group holds"), and 15 points between seven members on one hue are out of reach for any rule. Its
     * measurement is back, red until rule B lands, with the criterion that rule meets: the floor in
     * CIEDE2000, the hue within 3°, every shade inside L [10, 90].
     *
     * The members are read off the enum through K itself, imported for real — so a subtype K adds
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
        return {primaryAssetType: assetTypes.primaryAssetType, assetTypeFamily: assetTypes.assetTypeFamily, ASSET_TYPES: [...assetTypes.ASSET_TYPES] as string[]};
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
            // Barrier inside: the whole family, at this slot, in the order it was built, before
            // anything is measured about its colours.
            const rows = familyRowsAtSlot(palette, index, members, resolve, family);

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

    // Restored 28/09 → 01/10/2026 from the parked block, with rule B's criterion in place of the pair rule.
    it.each(PIE_PALETTES)('by vehicle, the ETF family holds ETF and every one of its subtypes — pairwise distinct, at least the floor apart in CIEDE2000, on its hue and inside L [10, 90], for every entry of %s', async (_name, palette) => {
        const {assetTypeFamily, ASSET_TYPES} = await importTaxonomy();
        const members = membersOf(ASSET_TYPES, assetTypeFamily, 'ETF');
        // Anti-vacuous: K files its subtypes under ETF, the one K2 keeps as itself included, with the
        // generic ETF leading. No count: the list is expected to grow.
        expect(members).toEqual(expect.arrayContaining(['ETF', 'ETF_STOCK', 'ETF_BOND', 'ETF_MONETARY']));
        expect(members[0]).toBe('ETF');
        // …but more than three, or this measures today's rule, not rule B.
        expect(members.length, 'the ETF family by vehicle holds three members or fewer: this no longer measures rule B').toBeGreaterThan(3);

        const {defects, slotsChecked} = perceptualFamilyDefects(palette, members, assetTypeFamily, 'ETF', FLOOR.deltaE);
        expect(slotsChecked, 'the loop ran on fewer slots than the palette holds').toBe(palette.length);
        const pastTheLimit = members.length >= 8 ? ' — from eight members the floor is out of reach by the documented limit: K has grown the family past it' : '';
        expect(defects, `members of the ${members.length}-member ETF family the pie cannot tell apart (closer than ΔE00 ${FLOOR.deltaE.toFixed(2)}, today's closest pair), or that leave its hue, or reach black or white${pastTheLimit}`).toEqual([]);
    });
});

// =============================================================================
// Families larger than three — rule B, for every size the pie can hold
// =============================================================================

/** A synthetic family of `size`: the pure member `FAMILY` first, then `FAMILY_1`, `FAMILY_2`… — the builder sees a size, not a taxonomy. */
function syntheticFamily(size: number): string[] {
    return ['FAMILY', ...Array.from({length: size - 1}, (_, rank) => `FAMILY_${rank + 1}`)];
}

/** The K2 stub of this file, with the synthetic family folded onto `FAMILY`; the fillers stay on their own. */
const resolveSynthetic = (key: string): string => (/^FAMILY(_\d+)?$/.test(key.trim().toUpperCase()) ? 'FAMILY' : resolvePrimary(key));

describe('buildAllocationHierarchy — families larger than three (rule B)', () => {
    /**
     * Rule B on every family size the pie can hold, independent of what K files today: four, five
     * and six members, synthetic, through the real builder on every slot of both pie palettes,
     * held to the same criterion as the ETF family — the developer measured 6.97, 6.10 and 7.84 at
     * the closest pair of those sizes, against a floor of 5.4.
     */
    const MEASURED = [4, 5, 6].flatMap((size) => PIE_PALETTES.map(([name, palette]) => [size, name, palette] as const));

    it.each(MEASURED)('a family of %i on %s: pairwise distinct, at least the floor apart in CIEDE2000, on its hue and inside L [10, 90], on every slot', (size, _name, palette) => {
        const {defects, slotsChecked} = perceptualFamilyDefects(palette, syntheticFamily(size), resolveSynthetic, 'FAMILY', FLOOR.deltaE);
        expect(slotsChecked, 'the loop ran on fewer slots than the palette holds').toBe(palette.length);
        expect(defects, `members of a family of ${size} the pie cannot tell apart (closer than ΔE00 ${FLOOR.deltaE.toFixed(2)}, today's closest pair), or that leave its hue, or reach black or white`).toEqual([]);
    });

    /**
     * The documented limit. From eight members the floor is out of reach: the band holds 80
     * lightness points, and halving the saturation of every other shade buys separation for seven
     * members, not more — ΔE00 ≈ 3.3 at eight and ≈ 2.9 at nine on the dark palette (the developer's
     * measurement, R5 plan, "Le sfumature della torta per le famiglie grandi", 01/10/2026), written in
     * `allocationHierarchy.ts` with the fix. A limit accepted, not a defect: past it the members must
     * still be told apart as colours — distinct, on their hue, off black and white — but how far apart
     * is not asserted, and a red on the floor here would be a red on a decision already taken.
     */
    const PAST_THE_LIMIT = [8, 9, 10].flatMap((size) => PIE_PALETTES.map(([name, palette]) => [size, name, palette] as const));

    it.each(PAST_THE_LIMIT)('a family of %i on %s, past the documented limit: still pairwise distinct, on its hue and inside L [10, 90] on every slot — the floor not asserted', (size, _name, palette) => {
        const {defects, slotsChecked} = perceptualFamilyDefects(palette, syntheticFamily(size), resolveSynthetic, 'FAMILY', null);
        expect(slotsChecked, 'the loop ran on fewer slots than the palette holds').toBe(palette.length);
        expect(defects, `members of a family of ${size} that share a colour, leave its hue, or reach black or white`).toEqual([]);
    });
});

// =============================================================================
// Rule B, pinned shade by shade — what the perceptual criterion cannot see
// =============================================================================

/**
 * The candidates rule B weighs for a group of `n` around `base`, transcribed from the rule as the
 * developer stated it: for each k, k shades on the far side and the rest on the near one, spaced
 * min(far room / k, near room / (n − 1 − k), step) apart. Index `k − 1` holds k's gap. For the
 * premises only — the pins below are values captured from the module, never computed from this.
 */
function spreadCandidates(base: string, n: number, step: number = 20) {
    const lightness = lightnessOf(base);
    const direction = lightness < 50 ? 1 : -1;
    const [low, high] = LIGHTNESS_BAND;
    const roomFar = Math.abs((direction > 0 ? high : low) - lightness);
    const roomNear = Math.abs(lightness - (direction > 0 ? low : high));
    const shades = n - 1;
    const gaps = Array.from({length: shades}, (_, index) => {
        const nearCount = shades - (index + 1);
        return Math.min(roomFar / (index + 1), nearCount > 0 ? roomNear / nearCount : Infinity, step);
    });
    return {lightness, direction, roomFar, roomNear, shades, gaps};
}

/** The case a pinned list exercises, beyond the plain spread: the two parts of rule B the criterion above cannot see. */
type RuleBCase = 'cap, far side only' | 'cap, both sides' | 'tie';

/**
 * Rule B's exact output — `shadeForDepth(base, d, 20, n)` for d = 1 … n − 1 — captured from the
 * implementation the developer approved on 01/10/2026, for groups of four to seven on three bases:
 *
 * - `#1a4031` (slot 0 of both light palettes, L 17.6) — a dark base. At four members the cap binds
 *   from the far side: 72.4 points for three shades would space them 24.1 apart, the step holds
 *   them at 20.
 * - `#ff0000` — **synthetic**, chosen for its lightness: exactly 50 ((1 + 0) / 2, nothing to round),
 *   so the far and the near side hold 40 points each and two k give the widest gap at four members
 *   (k = 1 or 2) and at six (k = 2 or 3). No entry of the four palettes ties exactly for four to seven
 *   members (searched on 01/10/2026; the nearest, `#84cc16` at seven, misses by 0.016), so without a
 *   synthetic base the tie-break would go unpinned.
 * - `#4ade80` (slot 0 of both dark palettes, L 58.0) — a dark-theme entry. At four members it binds
 *   the cap too, from both sides: two shades far and one near would stand 24.0 apart.
 *
 * Why pins at all: the perceptual criterion above admits many rules, and two parts of the one
 * the developer approved visually change the colours drawn without moving it — the gap capped at
 * `step` (uncapped, `#1a4031` would spread to +24.1/+48.2/+72.4 instead of +20/+40/+60) and ties
 * going to the **first** k (to the last, `#ff0000` in a group of four would put two shades on the
 * dark side and one on the light, instead of one and two). Both were mutants that survived it.
 */
const RULE_B_GOLDEN: ReadonlyArray<{base: string; n: number; exercises?: RuleBCase; shades: readonly string[]}> = [
    {base: '#1a4031', n: 4, exercises: 'cap, far side only', shades: ['#378969', '#7caa98', '#aedecb']},
    {base: '#1a4031', n: 5, shades: ['#358263', '#70a28e', '#99d6be', '#e0ebe7']},
    {base: '#1a4031', n: 6, shades: ['#2f7459', '#5e907c', '#72c6a5', '#b3cec3', '#dbf0e8']},
    {base: '#1a4031', n: 7, shades: ['#2c6c52', '#54816f', '#58bb94', '#96baac', '#afdfcc', '#e0ebe7']},
    {base: '#ff0000', n: 4, exercises: 'tie', shades: ['#990000', '#d98c8c', '#ffcccc']},
    {base: '#ff0000', n: 5, shades: ['#990000', '#260d0d', '#ff6666', '#f2d9d9']},
    {base: '#ff0000', n: 6, exercises: 'tie', shades: ['#bb0000', '#591e1e', '#ff4444', '#e1a6a6', '#ffcccc']},
    {base: '#ff0000', n: 7, shades: ['#bb0000', '#591e1e', '#330000', '#d07373', '#ff8888', '#f2d9d9']},
    {base: '#4ade80', n: 4, exercises: 'cap, both sides', shades: ['#1ea44f', '#1e3e2a', '#a0eebd']},
    {base: '#4ade80', n: 5, shades: ['#21b557', '#2b593c', '#082b15', '#a6d4b7']},
    {base: '#4ade80', n: 6, shades: ['#21b557', '#2c593c', '#082c15', '#a6d4b7', '#d4f7e1']},
    {base: '#4ade80', n: 7, shades: ['#24c75f', '#39754f', '#115f2e', '#112217', '#7ee7a4', '#c1e1cd']},
];

/** The pinned lists that exercise `which`. */
function goldenExercising(which: RuleBCase) {
    return RULE_B_GOLDEN.filter((row) => row.exercises === which);
}

/** Each pinned shade's measured lightness minus the base's: where rule B put it, to the hex rounding. */
function lightnessOffsets(base: string, shades: readonly string[]): number[] {
    const baseLightness = lightnessOf(base);
    return shades.map((shade) => lightnessOf(shade) - baseLightness);
}

describe('shadeForDepth — rule B, pinned shade by shade', () => {
    it('premise: the pinned lists exercise both parts of the rule the perceptual criterion cannot see — the cap, from one side and from two, and a tie', () => {
        // An `it.each` over an empty filter registers nothing and reports nothing: the cases are counted here.
        expect(goldenExercising('cap, far side only').length).toBeGreaterThan(0);
        expect(goldenExercising('cap, both sides').length).toBeGreaterThan(0);
        expect(goldenExercising('tie').length).toBeGreaterThan(0);
        // And the table is the one described: three bases, groups of four to seven each.
        expect(RULE_B_GOLDEN.map((row) => `${row.base}/${row.n}`)).toEqual(['#1a4031', '#ff0000', '#4ade80'].flatMap((base) => [4, 5, 6, 7].map((n) => `${base}/${n}`)));
    });

    it.each(goldenExercising('cap, far side only'))('premise: $base in a group of $n binds the cap from the far side — far room / shades is above 20, and the pinned shades step 20 apart', ({base, n, shades}) => {
        const {roomFar, shades: count, gaps, direction} = spreadCandidates(base, n);
        // The user-visible case: all shades on the far side could stand further apart than the step.
        expect(roomFar / count, `${base}: ${roomFar.toFixed(2)} points of far room for ${count} shades`).toBeGreaterThan(20);
        // So the widest gap is the step itself, taken with every shade on the far side…
        expect(Math.max(...gaps)).toBe(20);
        expect(gaps.indexOf(20) + 1, 'the first k reaching the step').toBe(count);
        // …and the pinned list shows it: +20, +40, +60 away from the nearer extreme, to the hex rounding.
        lightnessOffsets(base, shades).forEach((offset, index) => expect(Math.abs(offset - direction * 20 * (index + 1)), `depth ${index + 1}: offset ${offset.toFixed(2)}`).toBeLessThanOrEqual(HEX_LIGHTNESS_QUANTUM));
    });

    it.each(goldenExercising('cap, both sides'))('premise: $base in a group of $n binds the cap on both sides — with shades on each, both rooms would allow more than 20, and the pinned shades step 20 apart', ({base, n, shades}) => {
        const {roomFar, roomNear, shades: count, gaps, direction} = spreadCandidates(base, n);
        // A k with shades on both sides where neither room is the limit: only the step holds them.
        const bothSides = gaps.flatMap((_, index) => (index + 1 < count && roomFar / (index + 1) > 20 && roomNear / (count - index - 1) > 20 ? [index + 1] : []));
        expect(bothSides, `${base}: far room ${roomFar.toFixed(2)}, near room ${roomNear.toFixed(2)}, ${count} shades`).not.toEqual([]);
        expect(Math.max(...gaps)).toBe(20);
        const farCount = gaps.indexOf(20) + 1;
        expect(bothSides, 'the first k reaching the step has shades on both sides').toContain(farCount);
        // The pinned list: farCount shades 20, 40… away from the nearer extreme, the rest 20, 40… towards it.
        const expectedOffsets = Array.from({length: count}, (_, index) => (index + 1 <= farCount ? direction * 20 * (index + 1) : -direction * 20 * (index + 1 - farCount)));
        lightnessOffsets(base, shades).forEach((offset, index) => expect(Math.abs(offset - expectedOffsets[index]), `depth ${index + 1}: offset ${offset.toFixed(2)}`).toBeLessThanOrEqual(HEX_LIGHTNESS_QUANTUM));
    });

    it.each(goldenExercising('tie'))('premise: $base in a group of $n ties — two k give the widest gap, and the pinned list puts the first k on the far side', ({base, n, shades}) => {
        const {lightness, gaps, direction} = spreadCandidates(base, n);
        const widest = Math.max(...gaps);
        const tied = gaps.flatMap((gap, index) => (gap === widest ? [index + 1] : []));
        expect(tied.length, `${base} (L ${lightness}): the widest gap ${widest} is reached by k = ${tied.join(', ')} only`).toBeGreaterThanOrEqual(2);
        // The rule breaks the tie for the first k: that many shades away from the nearer extreme, the rest towards it.
        const onTheFarSide = lightnessOffsets(base, shades).filter((offset) => direction * offset > 0).length;
        expect(onTheFarSide, `shades of the pinned list on the far side, against k = ${tied.join(' or ')}`).toBe(tied[0]);
    });

    it.each(RULE_B_GOLDEN)('$base in a group of $n: shadeForDepth(base, d, 20, $n) for d = 1 … n − 1 is the approved list', ({base, n, shades}) => {
        expect(shades, 'a pinned list holds one shade per depth after the base').toHaveLength(n - 1);
        expect(Array.from({length: n - 1}, (_, index) => shadeForDepth(base, index + 1, 20, n))).toEqual(shades);
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

// =============================================================================
// shadeForDepth across rule B — what must not move
// =============================================================================

/**
 * `shadeForDepth` as it stood before rule B, transcribed: `step` lightness points per depth, away
 * from the nearer extreme, clamped to 0..100. The oracle of "today's output" for the two blocks
 * below, anchored on literal values so that it cannot drift together with the module.
 */
function todaysShade(base: string, depth: number, step: number = 20): string {
    if (depth <= 0) return base;
    const hsl = hexToHsl(base);
    if (!hsl) return base;
    const direction = hsl.l < 50 ? 1 : -1;
    return hslToHex(hsl.h, hsl.s, Math.min(100, Math.max(0, hsl.l + direction * step * depth)));
}

/**
 * Today's output at depths 1 to 6, snapshotted from the code before rule B (HEAD a4375b28e,
 * 01/10/2026), on bases drawn from the four palettes: `#1a4031` (slot 0 of both light palettes)
 * lightens and clamps to white, `#4ade80` (slot 0 of both dark palettes) darkens and clamps to
 * black, `#0d9488` is the base of today's closest pair, `#a3a3a3` the achromatic entry of the history
 * chart; two of them again with a step of their own. Keyed by colour, not by slot: they pin the
 * function, and a palette edit must not turn them red.
 */
const TODAYS_SHADES: ReadonlyArray<{base: string; step: 'default' | number; shades: readonly string[]}> = [
    {base: '#1a4031', step: 'default', shades: ['#378969', '#65c19d', '#aedecb', '#f6fcfa', '#ffffff', '#ffffff']},
    {base: '#4ade80', step: 'default', shades: ['#1ea44f', '#0e4e25', '#000000', '#000000', '#000000', '#000000']},
    {base: '#0d9488', step: 'default', shades: ['#1cebd9', '#7af3e8', '#d7fcf8', '#ffffff', '#ffffff', '#ffffff']},
    {base: '#a3a3a3', step: 'default', shades: ['#707070', '#3d3d3d', '#0a0a0a', '#000000', '#000000', '#000000']},
    {base: '#1a4031', step: 10, shades: ['#29644d', '#378969', '#46ad84', '#65c19d', '#8acfb4', '#aedecb']},
    {base: '#4ade80', step: 35, shades: ['#126330', '#000000', '#000000', '#000000', '#000000', '#000000']},
];

describe('shadeForDepth — a group of up to three is shaded as today, byte for byte', () => {
    /**
     * The guard that lets rule B ship. The history chart groups by content — three members at most —
     * and must not move by one hex digit; neither may a pie family of two or three. With a group size
     * of three or less, `shadeForDepth` is today's one-sided walk exactly: on every slot of all four
     * palettes, against the transcription and against literal values snapshotted before the change.
     * Green today, and it must stay green.
     */
    it.each(ALL_PALETTES)("%s: with a group size of 1, 2 or 3, depths 1 and 2 are today's on every slot", (_name, palette) => {
        let checked = 0;
        for (const base of palette) {
            for (const depth of [1, 2]) {
                const today = todaysShade(base, depth);
                expect(shadeForDepth(base, depth), `${base} at depth ${depth}, no group size`).toBe(today);
                for (const groupSize of [1, 2, 3]) {
                    expect(shadeForDepth(base, depth, 20, groupSize), `${base} at depth ${depth}, a group of ${groupSize}`).toBe(today);
                    checked++;
                }
            }
        }
        // Anti-vacuous: every slot, both depths, every small group size.
        expect(checked).toBe(palette.length * 2 * 3);
    });

    it('…and the literal output of the code before the change, for groups of 2 and 3 at depths 1 and 2', () => {
        const atDefaultStep = TODAYS_SHADES.filter((row) => row.step === 'default');
        expect(atDefaultStep.length).toBeGreaterThan(0);
        for (const {base, shades} of atDefaultStep) {
            for (const depth of [1, 2]) {
                expect(shadeForDepth(base, depth), `${base} at depth ${depth}, no group size`).toBe(shades[depth - 1]);
                for (const groupSize of [2, 3]) {
                    expect(shadeForDepth(base, depth, 20, groupSize), `${base} at depth ${depth}, a group of ${groupSize}`).toBe(shades[depth - 1]);
                }
            }
        }
    });

    it.each(ALL_PALETTES)("%s: through buildAllocationHierarchy, a family of two and a family of three keep today's colours on every slot", (_name, palette) => {
        let familiesChecked = 0;
        for (const size of [2, 3]) {
            const members = syntheticFamily(size);
            for (let index = 0; index < palette.length; index++) {
                const rows = familyRowsAtSlot(palette, index, members, resolveSynthetic, 'FAMILY');
                expect(
                    rows.map((row) => row.color),
                    `slot ${index}, a family of ${size}`,
                ).toEqual(members.map((_, depth) => todaysShade(palette[index], depth)));
                familiesChecked++;
            }
        }
        expect(familiesChecked).toBe(2 * palette.length);
    });
});

describe("shadeForDepth — without a group size, today's output for every other caller", () => {
    /**
     * The other half of an optional parameter: a caller that passes no group size — any caller but
     * the two builders — gets exactly what it got before, at every depth up to 6, the clamped ones
     * included, with the default step and with a step of its own.
     */
    it.each(ALL_PALETTES)("%s: shadeForDepth(base, d) and shadeForDepth(base, d, step) are today's up to depth 6, clamped ones included, on every slot", (_name, palette) => {
        let checked = 0;
        let clamped = 0;
        for (const base of palette) {
            for (let depth = 1; depth <= 6; depth++) {
                expect(shadeForDepth(base, depth), `${base} at depth ${depth}, default step`).toBe(todaysShade(base, depth));
                for (const step of [10, 20, 35]) {
                    const today = todaysShade(base, depth, step);
                    expect(shadeForDepth(base, depth, step), `${base} at depth ${depth}, step ${step}`).toBe(today);
                    if (today === '#ffffff' || today === '#000000') clamped++;
                    checked++;
                }
            }
        }
        expect(checked).toBe(palette.length * 6 * 3);
        // Anti-vacuous: the clamp really is reached on this palette, so "clamped ones included" is measured.
        expect(clamped, 'no depth up to 6 reached the clamp on this palette').toBeGreaterThan(0);
    });

    it.each(TODAYS_SHADES)('the module and its transcription give the literal output of the code before the change for $base (step $step), depths 1 to 6', ({base, step, shades}) => {
        const depths = [1, 2, 3, 4, 5, 6];
        const ownStep = step === 'default' ? undefined : step;
        expect(
            depths.map((depth) => todaysShade(base, depth, ownStep)),
            'the transcription drifted from the snapshot',
        ).toEqual(shades);
        expect(
            depths.map((depth) => (ownStep === undefined ? shadeForDepth(base, depth) : shadeForDepth(base, depth, ownStep))),
            'the module drifted from the snapshot',
        ).toEqual(shades);
    });
});
