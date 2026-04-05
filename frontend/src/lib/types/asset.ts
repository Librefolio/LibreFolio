/**
 * Asset Types
 *
 * Types for financial assets (stocks, ETFs, bonds, crypto, etc.).
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// TYPES DERIVED FROM ZOD SCHEMAS
// =============================================================================

/**
 * Asset metadata response.
 */
export type AssetMetadata = z.infer<typeof schemas.FAAssetMetadataResponse>;

/**
 * Asset info response (from GET /assets).
 */
export type AssetInfo = z.infer<typeof schemas.FAinfoResponse>;

/**
 * Request body for creating an asset.
 */
export type AssetCreateItem = z.infer<typeof schemas.FAAssetCreateItem>;

/**
 * Request body for patching an asset.
 */
export type AssetPatchItem = z.infer<typeof schemas.FAAssetPatchItem>;

/**
 * Asset provider information.
 */
export type AssetProviderInfo = z.infer<typeof schemas.FAProviderInfo>;

/**
 * Price point (OHLC data) - input format.
 */
export type PricePointInput = z.infer<typeof schemas.FAPricePoint_Input>;

/**
 * Price point (OHLC data) - output format.
 */
export type PricePoint = z.infer<typeof schemas.FAPricePoint_Output>;

/**
 * Provider assignment for an asset.
 */
export type ProviderAssignment = z.infer<typeof schemas.FAProviderAssignmentReadItem>;

// =============================================================================
// FRONTEND-ONLY TYPES
// =============================================================================

/**
 * Simplified asset info for dropdowns and references.
 */
export interface AssetBasicInfo {
    id: number;
    name: string;
    symbol?: string;
    isin?: string;
}

/**
 * Asset with UI state for interactive components.
 */
export interface AssetWithUIState extends AssetBasicInfo {
    isSelected?: boolean;
    isLoading?: boolean;
}
