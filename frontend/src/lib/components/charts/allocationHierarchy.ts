/**
 * Allocation hierarchy — subtypes as shades inside the mass of their primary type.
 *
 * Both allocation charts colour their categories **by index**: the Nth slice gets
 * the Nth palette entry. That is fine while every category is unrelated, and wrong
 * as soon as the asset-type taxonomy grows subtypes: `ETF_STOCK` is equity, and it
 * should read as equity, not as "the fourth thing".
 *
 * This module answers two questions at once, because neither works without the
 * other:
 *
 * 1. **What order?** Parents by total, children immediately after their parent.
 *    Ordered by value alone, two members of the same family land on opposite sides
 *    of the circle — and two similar colours that are not adjacent are *worse* than
 *    no shading at all, because the eye reads them as an accident.
 * 2. **What colour?** The unspecialised member keeps the pure palette entry; a
 *    subtype gets a lightness-shifted variant of it.
 *
 * ## Why the shade direction is decided per colour, not per theme
 *
 * The obvious rule — "light theme, so shade lighter" — was measured and rejected.
 * Converting both palettes of both charts to HSL gives:
 *
 * ```text
 * PIE_LIGHT   L 18→67 (8/14 below 50)      PIE_DARK   L 50→82 (0/14 below 50)
 * HIST_LIGHT  L 18→67 (4/12 below 50)      HIST_DARK  L 50→83 (0/12 below 50)
 * ```
 *
 * The dark palettes really are uniformly light. The light palettes are **not**
 * uniformly dark: `#1a4031` (L=18) is the outlier, not the representative, while
 * `#6366f1` sits at L=67 — lighter than half the dark palette. A per-theme rule
 * would wash those entries out against white.
 *
 * So the direction is chosen **per base colour**: move away from the nearer
 * extreme. That guarantees `max(L, 100-L)` ≥ **50** lightness points of headroom
 * for every entry of all four palettes, where the per-theme rule guarantees 17.
 *
 * ## How many members a group holds
 *
 * It depends on the resolver:
 *
 * - by **content** (`primaryAssetType`), a group holds its pure type and the subtypes
 *   that contain it — up to **three** today, `REAL_ESTATE` with `ETF_REAL_ESTATE` and
 *   `CROWDFUND_REAL_ESTATE`. No chart groups this way since I's D15;
 * - by **vehicle** (`assetTypeFamily`), the allocation pie: the ETF family holds the generic
 *   ETF and every ETF subtype — up to **seven** — and Crowdfund holds two. The allocation
 *   history chart groups by the same families but draws each one as a single area, with no
 *   shades and its subtypes in the tooltip only (D375): from this module it takes only the
 *   family order and the base colours.
 *
 * Groups of up to three walk lightness `step` points at a time away from the nearer
 * extreme, as they always have. From four members on that walk clamps to black or
 * white after two to four steps (measured on every slot of the pie's palettes, 01/10/2026),
 * so a larger group spreads its shades on **both sides** of the base within lightness
 * [10, 90], as far apart as the band allows (never more than `step`), and halves the
 * saturation of every other shade (the developer's rule "B"). Lightness alone cannot
 * separate seven members: about 11.5 points apart at best, while the saturation keeps
 * every pair of a 4–7-member family at least as far apart (CIEDE2000 ≥ 5.8) as the
 * closest pair of today's groups of two or three (5.4).
 *
 * **Known limit**: from eight members on the shades stay distinct but closer (CIEDE2000
 * about 3) — the band holds only so many separable steps of one hue.
 *
 * ## Scope
 *
 * Callers must apply this only where categories *are* asset types. The sector and
 * geography dimensions share the same components — and `AllocationPieChart` also
 * serves the (out-of-scope) Asset Detail page — so an unconditional change would
 * repaint charts this has no business touching.
 */
import {hexToHsl, hslToHex} from '$lib/utils/colors';
import {debug} from '$lib/debug';

export interface AllocationHierarchyEntry<T> {
    /** Raw backend category key, e.g. `ETF_STOCK`, `STOCK`, `Liquidity`. */
    key: string;
    /** Magnitude used for ordering. Only the ordering matters, not the unit. */
    weight: number;
    /** Caller payload, carried through untouched. */
    item: T;
}

export interface AllocationHierarchyOptions {
    /**
     * Maps a raw key to its group — contract **K2**. Both allocation charts pass
     * `assetTypeFamily` (the vehicle); `primaryAssetType` (the content) fits it too.
     *
     * Injected rather than imported: `assetTypes.ts` reads the generated Zodios
     * schemas at module load, so importing it would drag `$lib/api/generated` —
     * a gitignored build artifact — into every consumer, including unit tests.
     */
    resolvePrimary: (key: string) => string;
    /** Theme palette, in priority order. */
    palette: readonly string[];
    /** Lightness points between consecutive levels. */
    shadeStep?: number;
}

export interface AllocationHierarchyResult<T> {
    key: string;
    item: T;
    /** 6-digit hex, so the existing `color + '88'` alpha concatenation keeps working. */
    color: string;
    /** The group this entry belongs to, as returned by `resolvePrimary`. */
    primary: string;
    /** `0` = pure palette colour, `1..n` = shaded subtype. */
    depth: number;
    /** How many entries share this primary. `1` means the entry is the whole group. */
    groupSize: number;
    /** Summed weight of the whole group — the number the shading makes visual. */
    primaryTotal: number;
}

const DEFAULT_SHADE_STEP = 20;
/** Groups up to this size keep the one-sided walk, which is what they have always looked like. */
const ONE_SIDED_GROUP_SIZE = 3;
/** The lightness band a larger group spreads over: beyond it a shade reads as black or white. */
const SPREAD_MIN_LIGHTNESS = 10;
const SPREAD_MAX_LIGHTNESS = 90;
/** Saturation of every other shade in a larger group: lightness alone cannot separate seven members. */
const SPREAD_SATURATION_FACTOR = 0.5;

/** Case-insensitive, because `by_type` mixes enum casing with the synthetic `"Liquidity"` bucket. */
function sameKey(a: string, b: string): boolean {
    return a.toUpperCase() === b.toUpperCase();
}

/**
 * Derive a related colour for a group member.
 *
 * Without `groupSize`, or for a group of up to three, lightness moves `step` points
 * per depth away from the nearer extreme — today's shading. A larger group spreads its
 * shades on both sides of the base (see "How many members a group holds" above).
 * Falls back to the base colour when it is not parseable hex — a slice keeping its
 * parent's colour is a far better failure than a black one.
 */
export function shadeForDepth(base: string, depth: number, step: number = DEFAULT_SHADE_STEP, groupSize?: number): string {
    if (depth <= 0) return base;

    const hsl = hexToHsl(base);
    if (!hsl) return base;

    const direction = hsl.l < 50 ? 1 : -1;
    if (groupSize === undefined || groupSize <= ONE_SIDED_GROUP_SIZE) {
        const lightness = Math.min(100, Math.max(0, hsl.l + direction * step * depth));
        return hslToHex(hsl.h, hsl.s, lightness);
    }

    const far = direction > 0 ? SPREAD_MAX_LIGHTNESS : SPREAD_MIN_LIGHTNESS;
    const near = direction > 0 ? SPREAD_MIN_LIGHTNESS : SPREAD_MAX_LIGHTNESS;
    const roomFar = Math.abs(far - hsl.l);
    const roomNear = Math.abs(hsl.l - near);
    const shades = groupSize - 1;
    // k shades on the far side, the rest on the near one, spaced as widely as the band allows.
    let farCount = 1;
    let gap = -1;
    for (let k = 1; k <= shades; k++) {
        const nearCount = shades - k;
        const candidate = Math.min(roomFar / k, nearCount > 0 ? roomNear / nearCount : Infinity, step);
        if (candidate > gap) {
            gap = candidate;
            farCount = k;
        }
    }
    const lightness = depth <= farCount ? hsl.l + direction * gap * depth : hsl.l - direction * gap * (depth - farCount);
    const saturation = depth % 2 === 0 ? hsl.s * SPREAD_SATURATION_FACTOR : hsl.s;
    return hslToHex(hsl.h, saturation, lightness);
}

/**
 * Group, order and colour allocation entries so that subtypes sit inside the mass
 * of their primary type.
 *
 * Guarantees, in order of importance:
 *
 * - when no entry resolves to a primary shared with another entry, the returned
 *   order and colours are **identical** to the previous index-based behaviour —
 *   this is what keeps the sector/geography dimensions and single-type portfolios
 *   pixel-stable;
 * - a group's unspecialised member keeps the palette entry **verbatim**, never a
 *   `hex → HSL → hex` round trip, which would drift by a digit or two;
 * - a lone member is never shaded: a shade only carries meaning next to the colour
 *   it is derived from.
 */
export function buildAllocationHierarchy<T>(entries: readonly AllocationHierarchyEntry<T>[], opts: AllocationHierarchyOptions): AllocationHierarchyResult<T>[] {
    const {resolvePrimary, palette, shadeStep = DEFAULT_SHADE_STEP} = opts;
    if (palette.length === 0) return [];

    // Group by primary, keeping first-seen order so the stable sort below can
    // reproduce the legacy ordering exactly when every group is a singleton.
    const order: string[] = [];
    const groups = new Map<string, AllocationHierarchyEntry<T>[]>();

    for (const entry of entries) {
        // `.toUpperCase()` is redundant against contract K2, which already upper-cases
        // before its lookup and returns the normalised value even when it misses. It is
        // kept as a cheap guard against contract drift, not because any test needs it —
        // that invariant belongs to the resolver (`assetTypeFamily`, like
        // `primaryAssetType`), so it is pinned in `assetTypeTables.test.ts` rather
        // than duplicated here.
        const groupKey = resolvePrimary(entry.key).toUpperCase();
        const bucket = groups.get(groupKey);
        if (bucket) {
            bucket.push(entry);
        } else {
            groups.set(groupKey, [entry]);
            order.push(groupKey);
        }
    }

    const totalOf = (key: string) => (groups.get(key) ?? []).reduce((sum, entry) => sum + entry.weight, 0);
    // Stable sort: ties keep insertion order, which is what makes the legacy
    // comparison `b.value - a.value` reproducible member-for-member.
    const sortedGroups = [...order].sort((left, right) => totalOf(right) - totalOf(left));

    // `groupIndex % palette.length` wraps instead of signalling: past the last slot
    // a group silently repeats an earlier group's colour, keeping its own correct
    // name, which reads as a design choice rather than a defect. The caller's own
    // count is not a constant, so this cannot be ruled out by arithmetic here.
    if (sortedGroups.length > palette.length) {
        debug.warn('allocationHierarchy', `palette exhausted: ${sortedGroups.length} primary groups for ${palette.length} colours — ` + `${sortedGroups.length - palette.length} will repeat an earlier colour`);
    }

    const result: AllocationHierarchyResult<T>[] = [];

    sortedGroups.forEach((groupKey, groupIndex) => {
        const base = palette[groupIndex % palette.length];
        const members = [...(groups.get(groupKey) ?? [])];
        const primaryTotal = totalOf(groupKey);

        // The unspecialised member leads — it is the "grade zero" of the scale,
        // not a special case. Everything else follows by weight.
        members.sort((left, right) => {
            const leftPure = sameKey(left.key, groupKey);
            const rightPure = sameKey(right.key, groupKey);
            if (leftPure !== rightPure) return leftPure ? -1 : 1;
            return right.weight - left.weight;
        });

        const singleton = members.length === 1;

        members.forEach((entry, memberIndex) => {
            const depth = singleton ? 0 : memberIndex;
            result.push({
                key: entry.key,
                item: entry.item,
                color: depth === 0 ? base : shadeForDepth(base, depth, shadeStep, members.length),
                primary: groupKey,
                depth,
                groupSize: members.length,
                primaryTotal,
            });
        });
    });

    return result;
}
