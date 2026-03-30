/**
 * Asset Types — Centralized utility for asset type constants, icon mapping, and option builders.
 *
 * Replaces duplicated ASSET_TYPE_PNG_MAP in AssetIcon, AssetModal, AssetTable, ProviderAssignmentSection.
 * Single source of truth for asset type enums, identifier types, and their UI representation.
 *
 * @module utils/assetTypes
 */

// =============================================================================
// ASSET TYPES
// =============================================================================

export const ASSET_TYPES = [
    'STOCK', 'ETF', 'BOND', 'CRYPTO', 'FUND',
    'HOLD', 'CROWDFUND_LOAN', 'INDEX', 'OTHER',
] as const;

export type AssetTypeCode = typeof ASSET_TYPES[number];

/** Map asset type code → PNG filename in /icons/asset-types/ */
const PNG_MAP: Record<string, string> = {
    STOCK: 'stock',
    ETF: 'etf',
    BOND: 'bond',
    CRYPTO: 'crypto',
    FUND: 'fund',
    HOLD: 'hold',
    CROWDFUND_LOAN: 'crowdfunding',
    INDEX: 'index',
    OTHER: 'other',
};

/**
 * Get the icon URL for an asset type.
 * Falls back to 'other.png' for unknown types.
 */
export function getAssetTypeIconUrl(type: string | null | undefined): string {
    const filename = PNG_MAP[(type ?? '').toUpperCase()] ?? 'other';
    return `/icons/asset-types/${filename}.png`;
}

/**
 * Build SelectOption[] for asset type dropdowns.
 * Each option includes an icon from the PNG map.
 */
export function buildAssetTypeOptions(t: (key: string) => string): Array<{
    value: string;
    label: string;
    icon: string;
}> {
    return ASSET_TYPES.map(at => ({
        value: at,
        label: t(`assets.types.${at}`) || at,
        icon: getAssetTypeIconUrl(at),
    }));
}

// =============================================================================
// IDENTIFIER TYPES
// =============================================================================

export const IDENTIFIER_TYPES = [
    'TICKER', 'ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID', 'OTHER',
] as const;

export type IdentifierTypeCode = typeof IDENTIFIER_TYPES[number];

