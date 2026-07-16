/**
 * Single-asset AI export — type definitions.
 *
 * Mirrors the portfolio-level AiPortfolioExport model (see ../types.ts) but
 * scoped to one asset: identity/classification, current holding in the
 * portfolio (nullable — the asset may not be currently owned), and the same
 * 3M technical context used by the portfolio exports (for methodological
 * consistency across the whole AI export feature).
 */

import type {AiMethodology, AiTechnicalAsset} from '../types';

export interface AiAssetIdentity {
    name: string;
    /** All known market identifiers (ISIN/Ticker/CUSIP/...) — for the AI's own web research only, never used as the display label. */
    identifiers?: Record<string, string>;
    asset_type?: string;
    currency: string;
    active: boolean;
    provider_code?: string;
    /** Short business description, when available from asset classification metadata. */
    short_description?: string;
    /** Look-through sector composition (e.g. for a fund/ETF) — percent values, when available. */
    sector_distribution?: Record<string, number>;
    /** Look-through geographic composition — percent values, when available. */
    geographic_distribution?: Record<string, number>;
}

export interface AiAssetHolding {
    quantity: number;
    market_value?: number;
    nav_weight_percent?: number;
    wac?: number;
    cost_basis?: number;
    unrealized_pnl?: number;
    unrealized_pnl_percent?: number;
    period_pnl?: number;
    period_pnl_percent?: number;
    period_income?: number;
    brokers: string[];
}

export interface AiAssetMetadata {
    generated_at: string;
    base_currency: string;
    response_language: string;
    export_purpose: string;
}

export interface AiAssetDataQuality {
    missing_price: boolean;
    stale_price: boolean;
}

export interface AiAssetExport {
    metadata: AiAssetMetadata;
    methodology: AiMethodology;
    identity: AiAssetIdentity;
    /** null when the asset is not currently held in any broker (e.g. scouting a new idea before buying) */
    holding: AiAssetHolding | null;
    /** null when there isn't enough price history for technical signals */
    technical: AiTechnicalAsset | null;
    technical_unavailable_reason?: string;
    data_quality: AiAssetDataQuality;
}
