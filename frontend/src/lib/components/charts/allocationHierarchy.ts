/**
 * Allocation hierarchy — subtypes as shades inside the mass of their primary type.
 *
 * This module answers two questions at once, because neither works without the other:
 *
 * 1. **What order?** Parents by total, children immediately after their parent.
 *    Ordered by value alone, two members of the same family land on opposite sides
 *    of the circle — and two similar colours that are not adjacent are *worse* than
 *    no shading at all, because the eye reads them as an accident.
 * 2. **What colour?** The family's own (GR1 of the designer's round 2, D-T17): a colour
 *    per key, never per rank, so `ETF` is the same blue in the pie and in the history,
 *    in every portfolio and period. The caller passes it as `colorOf`, read through the
 *    one read point of the category colours (`categoryColor`, `lib/theme/chartCategories`).
 *    The unspecialised member keeps that colour verbatim; a subtype gets the shade of
 *    its rank (GR4, `familyShade` in `lib/theme/chartShades`), passed as `shade` because
 *    the shade of the dark theme reads the card it is drawn on.
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
 *   family order and the family colours.
 *
 * GR4 gives six shades, three toward one pole and three toward the other, so a family of
 * seven is the most it separates; between its members CIEDE2000 falls to 3.2–6.0 at worst,
 * a known limit sent back to the designer (round 3).
 *
 * ## Scope
 *
 * Callers must apply this only where categories *are* asset types. The sector and
 * geography dimensions share the same components, with colours of their own.
 */

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
    /** The fixed colour of a group, by its primary key (GR1): `categoryColor('type', primary, dark)`. */
    colorOf: (primary: string) => string;
    /** The colour of the member of rank `rank` (1…) of a group whose colour is `base` (GR4): `familyShade`. */
    shade: (base: string, rank: number) => string;
}

export interface AllocationHierarchyResult<T> {
    key: string;
    item: T;
    /** 6-digit hex: the history chart's area fill appends its alpha to it (`withHexAlpha(color, '88')`). */
    color: string;
    /** The group this entry belongs to, as returned by `resolvePrimary`. */
    primary: string;
    /** `0` = the group's own colour, `1..n` = shaded subtype. */
    depth: number;
    /** How many entries share this primary. `1` means the entry is the whole group. */
    groupSize: number;
    /** Summed weight of the whole group — the number the shading makes visual. */
    primaryTotal: number;
}

/** Case-insensitive, because `by_type` mixes enum casing with the synthetic `"Liquidity"` bucket. */
function sameKey(a: string, b: string): boolean {
    return a.toUpperCase() === b.toUpperCase();
}

/**
 * Group, order and colour allocation entries so that subtypes sit inside the mass
 * of their primary type.
 *
 * Guarantees, in order of importance:
 *
 * - a group's colour is its own, whatever its rank: the same family is the same colour
 *   in every chart and portfolio;
 * - a group's unspecialised member keeps that colour **verbatim**, never a shade of it;
 * - a lone member is never shaded: a shade only carries meaning next to the colour
 *   it is derived from;
 * - groups come by total, largest first, and ties keep the order the entries came in.
 */
export function buildAllocationHierarchy<T>(entries: readonly AllocationHierarchyEntry<T>[], opts: AllocationHierarchyOptions): AllocationHierarchyResult<T>[] {
    const {resolvePrimary, colorOf, shade} = opts;

    // Group by primary, keeping first-seen order so the stable sort below keeps
    // ties in the order the entries came in.
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
    const sortedGroups = [...order].sort((left, right) => totalOf(right) - totalOf(left));

    const result: AllocationHierarchyResult<T>[] = [];

    for (const groupKey of sortedGroups) {
        const base = colorOf(groupKey);
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
                color: depth === 0 ? base : shade(base, depth),
                primary: groupKey,
                depth,
                groupSize: members.length,
                primaryTotal,
            });
        });
    }

    return result;
}
