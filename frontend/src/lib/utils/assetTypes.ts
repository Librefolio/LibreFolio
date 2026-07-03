/**
 * Asset Types — Centralized utility for asset type constants, icon mapping, and option builders.
 *
 * Replaces duplicated ASSET_TYPE_PNG_MAP in AssetIcon, AssetModal, AssetTable, ProviderAssignmentSection.
 * Single source of truth for asset type enums, identifier types, and their UI representation.
 * Enum values are derived from Zod schemas in generated.ts (auto-generated from backend).
 *
 * @module utils/assetTypes
 */

import {schemas} from '$lib/api/generated';

// =============================================================================
// ASSET TYPES — derived from backend enum via Zod schema
// =============================================================================

export const ASSET_TYPES = schemas.AssetType.options;

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
    LIQUIDITY: 'liquidity',
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
    return ASSET_TYPES.map((at) => ({
        value: at,
        label: t(`assets.types.${at}`) || at,
        icon: getAssetTypeIconUrl(at),
    }));
}

// =============================================================================
// IDENTIFIER TYPES — derived from backend enum via Zod schema
// =============================================================================

export const IDENTIFIER_TYPES = schemas.IdentifierType.options;

/**
 * Map IdentifierType enum value to a human-readable label.
 * Upper-case acronyms stay as-is; multi-word → Title Case.
 */
function identifierLabel(type: string): string {
    const ACRONYMS = new Set(['ISIN', 'CUSIP', 'SEDOL', 'FIGI', 'UUID']);
    if (ACRONYMS.has(type)) return type;
    return type.charAt(0) + type.slice(1).toLowerCase(); // TICKER → Ticker, OTHER → Other
}

/**
 * Build a list of [label, value] pairs for non-empty identifiers on an asset.
 * Derives field names from the IdentifierType enum to stay in sync with backend.
 *
 * @example buildIdentifiersList(asset) → [['ISIN', 'IE00B4L5Y983'], ['Ticker', 'VWCE']]
 */
export function buildIdentifiersList(asset: Record<string, unknown>): [string, string][] {
    return IDENTIFIER_TYPES.map((type) => [identifierLabel(type), asset[`identifier_${type.toLowerCase()}`]]).filter((e): e is [string, string] => typeof e[1] === 'string' && e[1].length > 0);
}

// =============================================================================
// SECTOR KEYS — loaded from backend via GET /utilities/sectors
// =============================================================================

import {getSectorKeys} from '$lib/stores/reference/sectorStore';

/**
 * Static fallback used before sectorStore is loaded.
 * Matches the backend FinancialSector enum — kept in sync manually
 * as a safety net for the brief window before the API call completes.
 */
const SECTOR_KEYS_FALLBACK: readonly string[] = ['Industrials', 'Technology', 'Financials', 'Consumer Discretionary', 'Health Care', 'Real Estate', 'Basic Materials', 'Energy', 'Consumer Staples', 'Telecommunication', 'Utilities', 'Other'];

/**
 * Get the standard financial sector keys.
 *
 * Returns data from the sectorStore (loaded from backend API) when available,
 * otherwise falls back to a static list. Components using sector selects
 * should call `ensureSectorsLoaded()` early to populate the store.
 */
export function getSectorKeysList(): readonly string[] {
    const keys = getSectorKeys();
    return keys.length > 0 ? keys : SECTOR_KEYS_FALLBACK;
}

/**
 * Convert a backend sector key (e.g. "Consumer Discretionary") to
 * the corresponding i18n key (e.g. "ConsumerDiscretionary").
 *
 * Convention: strip spaces → PascalCase.
 * Single-word keys like "Technology" pass through unchanged.
 */
export function sectorI18nKey(backendKey: string): string {
    return backendKey.replaceAll(' ', '');
}
