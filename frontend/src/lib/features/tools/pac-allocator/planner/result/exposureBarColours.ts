/**
 * TD-1: the colours of the PAC's exposure bars, «ideal vs actual» (R9.8).
 *
 * - **The actual weight** is drawn in the colour of its row's category, the one the dashboard gives it (GR1).
 *   - A sector by its key.
 *   - An Asset type by its family. A subtype takes a shade of the family, ranked as in the pie's outer ring (GR4):
 *     the generic member keeps the family's colour, the others take `familyShade` by rank of ideal weight, largest
 *     first, ties by id, and never the family's own colour.
 *   - The uncategorised remainder reads «Non classificato».
 * - **The ideal weight** is a neutral role, {@link idealColour}, so the colour on a row belongs to the actual weight
 *   alone.
 *
 * Pure: the chart reads the roles (`chartRoles`) and hands in the shade poles of its card.
 *
 * @module features/tools/pac-allocator/planner/result/exposureBarColours
 */
import {categoryColor} from '$lib/theme/chartCategories';
import {familyShade, type ShadePoles} from '$lib/theme/chartShades';
import type {ChartRoles} from '$lib/theme/roleColors';
import {assetTypeFamily} from '$lib/utils/assetTypes';
import {compareExact, UNCATEGORISED_CATEGORY_ID, type WeightRow} from './model';

/**
 * The colour of the ideal weight: the secondary text role (TD-1, coordinator, 15/10/2026). It stays at least ΔE00 10
 * from every category colour, with one recorded exception: «Other» in the dark theme, at 9.0.
 */
export function idealColour(roles: ChartRoles): string {
    return roles.color('--lf-text-secondary');
}

/** The engine's bucket the uncategorised remainder reads as, in both tables. */
const UNCLASSIFIED_KEY = 'Unknown';

/**
 * The colour of each row's actual weight, in the order of `rows`. `dimension` is the exposure dimension of the bars:
 * `asset_type` reads the types' table, any other the sectors'.
 */
export function actualColours(rows: readonly WeightRow[], dimension: string, dark: boolean, poles: ShadePoles): string[] {
    if (dimension !== 'asset_type') return rows.map((row) => categoryColor('sector', row.id === UNCATEGORISED_CATEGORY_ID ? UNCLASSIFIED_KEY : row.id, dark));

    const ranks = subtypeRanks(rows);
    return rows.map((row) => {
        if (row.id === UNCATEGORISED_CATEGORY_ID) return categoryColor('type', UNCLASSIFIED_KEY, dark);
        const base = categoryColor('type', assetTypeFamily(row.id), dark);
        const rank = ranks.get(row);
        return rank === undefined ? base : familyShade(base, rank, poles);
    });
}

/** The rank (1…) of every subtype row among the subtypes of its family; the generic members have none. */
function subtypeRanks(rows: readonly WeightRow[]): Map<WeightRow, number> {
    const subtypesByFamily = new Map<string, WeightRow[]>();
    for (const row of rows) {
        if (row.id === UNCATEGORISED_CATEGORY_ID) continue;
        const family = assetTypeFamily(row.id);
        if (row.id.trim().toUpperCase() === family) continue;
        subtypesByFamily.set(family, [...(subtypesByFamily.get(family) ?? []), row]);
    }

    const ranks = new Map<WeightRow, number>();
    for (const subtypes of subtypesByFamily.values()) {
        const ordered = [...subtypes].sort((a, b) => (compareExact(b.target, a.target) ?? 0) || a.id.localeCompare(b.id));
        ordered.forEach((row, index) => ranks.set(row, index + 1));
    }
    return ranks;
}
