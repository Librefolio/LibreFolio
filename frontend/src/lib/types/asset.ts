/**
 * Asset Types
 *
 * Types for financial assets (stocks, ETFs, bonds, crypto, etc.).
 * Derived from Zod schemas in generated.ts.
 */

import {z} from 'zod';
import {schemas} from '$lib/api/generated';

// =============================================================================
// UTILITY — Flatten Zod code-gen artifacts (T | T[]) → T
// =============================================================================

/**
 * Resolve Zod union artifacts: extracts scalar type from (T | T[]) unions.
 * API responses always return scalar values; the union-with-array is a code-gen artifact.
 */
type Scalar<T> = T extends (infer U)[] ? U : T;

/** Mapped helper: flatten every field of a type */
type FlattenZodUnions<T> = { [K in keyof T]: Scalar<T[K]> };

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
 * AssetInfo with Zod union artifacts resolved to scalar types.
 * Use in component state where API always returns single values.
 */
export type AssetDetail = FlattenZodUnions<AssetInfo>;

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

/**
 * ProviderAssignment with Zod union artifacts resolved to scalar types.
 */
export type ProviderAssignmentFlat = FlattenZodUnions<ProviderAssignment>;

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
