/**
 * Allocation rings — the two-level reading of an asset-type pie (decision D72).
 *
 * `buildAllocationHierarchy` (D71) shows a subtype as a *shade* inside the mass of
 * its primary type. That works while the pure member sits next to it, and fails in
 * the most common case of an ETF investor: an `ETF_STOCK` with no direct `STOCK` is
 * a group of one, and a group of one is never shaded — so it is drawn as a pure,
 * unrelated colour, with nothing saying it is equity (review R12, 22/09/2026). A
 * shade says "related to" only when the relative is on screen.
 *
 * So the relation gets its own geometry instead of a colour:
 *
 * - the **base** ring holds one arc per primary type — the answer to "what do I
 *   own", summed over the whole family;
 * - the **outer** ring splits the families that contain a subtype into their
 *   members — the answer to "through what";
 * - a family with no subtype is not split: it gets a **filler** on the outer ring,
 *   which the caller draws invisibly so the slice reads as one piece at full
 *   thickness (developer's decision, 23/09/2026).
 *
 * Every family owns exactly one base arc and a run of outer arcs that sum to it, so
 * the two rings stay aligned by construction — provided the caller draws them with
 * the same angular padding, which is why this layout exists as data and not as a
 * rendering detail.
 *
 * Families are not assumed to have two members. A primary can gain several
 * subtypes (a `CROWDFUND_REAL_ESTATE` rolling up into `REAL_ESTATE` next to
 * `ETF_REAL_ESTATE` makes three), so each subtype gets its own shade step.
 *
 * Pure, no runes, and `resolvePrimary` stays upstream in the hierarchy it consumes:
 * nothing here imports the generated client.
 */
import {shadeForDepth, type AllocationHierarchyResult} from './allocationHierarchy';

export type AllocationRingRole = 'base' | 'member' | 'filler';

export interface AllocationRingItem<T> {
    /** Raw key: the primary for `base`/`filler`, the member's own key for `member`. */
    key: string;
    /** The family this arc belongs to, as resolved by the hierarchy. */
    primary: string;
    role: AllocationRingRole;
    /** Magnitude of this arc, in the caller's unit. */
    weight: number;
    /** Summed weight of the whole family. */
    primaryTotal: number;
    /** 6-digit hex. Fillers carry the base colour; drawing them invisibly is the caller's choice. */
    color: string;
    /** `member` only: the unspecialised member of its family. */
    pure: boolean;
    /** Whether the family is split on the outer ring. */
    split: boolean;
    /** How many members the family has on screen. */
    memberCount: number;
    /** Caller payloads: every member for `base`/`filler`, the one member for `member`. */
    items: T[];
}

export interface AllocationRingsLayout<T> {
    /** `false` when no family has a subtype: the caller keeps drawing the single ring. */
    rings: boolean;
    /** One arc per family, in hierarchy order. */
    base: AllocationRingItem<T>[];
    /** Members of the split families and fillers for the others, in the same order. */
    outer: AllocationRingItem<T>[];
}

export interface AllocationRingsOptions<T> {
    /** Magnitude of a member. Only relative sizes matter. */
    weightOf: (item: T) => number;
    /** Lightness points between consecutive subtypes; defaults to the hierarchy's step. */
    shadeStep?: number;
}

/** Case-insensitive, because `by_type` mixes enum casing with the synthetic `"Liquidity"` bucket. */
function sameKey(a: string, b: string): boolean {
    return a.toUpperCase() === b.toUpperCase();
}

export function buildAllocationRings<T>(hierarchy: readonly AllocationHierarchyResult<T>[], opts: AllocationRingsOptions<T>): AllocationRingsLayout<T> {
    const {weightOf, shadeStep} = opts;

    // The hierarchy already emits each family contiguously, pure member first and
    // subtypes by weight; keep that order rather than re-deriving it.
    const families: {primary: string; members: AllocationHierarchyResult<T>[]}[] = [];
    for (const entry of hierarchy) {
        const last = families[families.length - 1];
        if (last && last.primary === entry.primary) last.members.push(entry);
        else families.push({primary: entry.primary, members: [entry]});
    }

    const base: AllocationRingItem<T>[] = [];
    const outer: AllocationRingItem<T>[] = [];

    for (const {primary, members} of families) {
        // Depth 0 is always the verbatim palette entry, whichever member holds it.
        const baseColor = members[0].color;
        const weights = members.map((member) => weightOf(member.item));
        const total = weights.reduce((sum, weight) => sum + weight, 0);
        const split = members.some((member) => !sameKey(member.key, primary));
        const items = members.map((member) => member.item);

        const shared = {primary, primaryTotal: total, split, memberCount: members.length};

        base.push({...shared, key: primary, role: 'base', weight: total, color: baseColor, pure: false, items});

        if (!split) {
            outer.push({...shared, key: primary, role: 'filler', weight: total, color: baseColor, pure: false, items});
            continue;
        }

        // Shade by rank among the subtypes, not by position in the family: when the
        // pure member is absent the first subtype would otherwise inherit the base
        // colour and vanish into the base arc — the very defect this layout exists for.
        let subtypeRank = 0;
        members.forEach((member, index) => {
            const pure = sameKey(member.key, primary);
            const color = pure ? baseColor : shadeForDepth(baseColor, ++subtypeRank, shadeStep);
            outer.push({...shared, key: member.key, role: 'member', weight: weights[index], color, pure, items: [member.item]});
        });
    }

    return {rings: base.some((arc) => arc.split), base, outer};
}
