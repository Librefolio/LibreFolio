/**
 * The family of an asset type in the "by type" allocation pie — developer's decision of
 * 24/09/2026 (review R12, option B).
 *
 * The pie groups by **vehicle**: every ETF subtype belongs to the ETF family, and the outer
 * ring says what kind of ETF it is. The inner ring therefore answers one question only —
 * "what instruments do I hold" — whether or not the ETFs have been classified by content.
 *
 * This is deliberately **not** `primaryAssetType` (contract K2), which groups by *content*
 * (an equity ETF rolls up into STOCK) and still drives the allocation history chart.
 *
 * The list of subtypes is K's (`isEtfSubtype`): this module only states which parent the pie
 * uses for them, so there is still one taxonomy and not a second map.
 */
import {getAssetTypeIconUrl, isEtfSubtype, primaryAssetType} from '$lib/utils/assetTypes';

/** Family key, upper-cased like the hierarchy expects: ETF subtypes → `ETF`, everything else → itself. */
export function allocationFamily(type: string | null | undefined): string {
    const raw = (type ?? '').trim().toUpperCase();
    if (raw === '') return 'OTHER';
    return isEtfSubtype(raw) ? 'ETF' : raw;
}

/** The icons a type shows: its vehicle's, plus its content's when that says something more. */
export interface AllocationTypeIcons {
    /** The icon of the type itself — for an ETF subtype, the ETF icon. */
    main: string;
    /** The icon of what an ETF subtype contains (`ETF_STOCK` → stock), or `null` when it would repeat `main`. */
    content: string | null;
}

/**
 * Icons of a type in the allocation tooltip (review of R12, 24/09/2026): an ETF subtype names
 * both its vehicle and its content, like the composite icon of R16 describes — the main icon,
 * with the content one small beside it.
 *
 * Composed from what K already exports, so there is no second map: `getAssetTypeIconUrl` for
 * the vehicle and `primaryAssetType` (contract K2) for the content. When R16 delivers K's own
 * composite icon, the tooltip should consume that instead.
 */
export function allocationTypeIcons(type: string | null | undefined): AllocationTypeIcons {
    const main = getAssetTypeIconUrl(type);
    const content = getAssetTypeIconUrl(primaryAssetType(type));
    return {main, content: content === main ? null : content};
}
