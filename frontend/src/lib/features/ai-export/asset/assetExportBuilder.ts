/**
 * Single-asset AI export builder.
 *
 * Reuses the same portfolio report endpoint and technical context builder as
 * the portfolio-level export (buildAiExport in ../aiExportBuilder.ts) so the
 * two stay methodologically consistent (same 3M technical window, same
 * valuation/WAC policy, same identifiers convention) — just scoped to one asset.
 *
 * Works for assets that are NOT currently held too (holding: null): useful to
 * scout an idea before buying, not only to analyze an existing position.
 */

import {zodiosApi} from '$lib/api';
import {buildMethodology} from '../aiExportBuilder';
import {buildTechnicalContext} from '../technical/technicalExportBuilder';
import {getResponseLanguage} from '../templates/languageMap';
import {buildAssetIdentifiers} from '../assetLabel';
import type {AiAssetDataQuality, AiAssetExport, AiAssetHolding, AiAssetIdentity} from './assetTypes';

export interface AssetExportAssetInfo {
    id: number;
    display_name: string;
    currency: string;
    asset_type?: string | null;
    provider_code?: string | null;
    active: boolean;
    identifier_isin?: string | null;
    identifier_ticker?: string | null;
    identifier_cusip?: string | null;
    identifier_sedol?: string | null;
    identifier_figi?: string | null;
    identifier_uuid?: string | null;
    identifier_other?: string | null;
}

export interface AssetExportInput {
    assetInfo: AssetExportAssetInfo;
    /** Look-through sector composition already loaded on the Asset Detail page (percent values), if any. */
    sectorDistribution?: Record<string, number> | null;
    /** Look-through geographic composition already loaded on the Asset Detail page (percent values), if any. */
    geographicDistribution?: Record<string, number> | null;
    /** Short business description already loaded on the Asset Detail page, if any. */
    shortDescription?: string | null;
}

export interface AssetExportOptions {
    targetCurrency: string;
    locale: string;
}

export async function buildAssetAiExport(input: AssetExportInput, options: AssetExportOptions): Promise<AiAssetExport> {
    const {assetInfo} = input;

    // Portfolio-wide report, unfiltered by broker — same call shape as the
    // portfolio builder — then filtered client-side to this one asset.
    const report = await zodiosApi.get_portfolio_report_api_v1_portfolio_report_post({
        include_summary: true,
        include_history: false,
        include_allocation_history: false,
        include_positions_contribution: true,
        include_breakdown: true,
        target_currency: options.targetCurrency,
    });

    const summary = report.summary as Record<string, any> | null;
    const contribution = report.positions_contribution as Record<string, any> | null;
    const dataQuality = report.data_quality as Record<string, any> | null;

    const identity = buildIdentity(assetInfo, input);
    const holding = buildHolding(assetInfo.id, summary, contribution);
    const dq = buildAssetDataQuality(assetInfo.id, dataQuality, summary);

    // Technical context — always "as of today", independent of any historical
    // range the Asset Detail chart might currently be showing (this export is
    // meant to reflect the asset's *current* status, not a past viewing date).
    const technicalResult = await buildTechnicalContext([
        {
            assetId: assetInfo.id,
            assetName: assetInfo.display_name,
            identifiers: buildAssetIdentifiers(assetInfo),
            currency: assetInfo.currency,
            endDate: new Date().toISOString().slice(0, 10),
            targetCurrency: options.targetCurrency,
        },
    ]);

    return {
        metadata: {
            generated_at: new Date().toISOString(),
            base_currency: options.targetCurrency,
            response_language: getResponseLanguage(options.locale),
            export_purpose: 'single-asset status classification',
        },
        methodology: buildMethodology(),
        identity,
        holding,
        technical: technicalResult.assets[0] ?? null,
        technical_unavailable_reason: technicalResult.assets.length === 0 ? technicalResult.unavailable[0]?.reason : undefined,
        data_quality: dq,
    };
}

function buildIdentity(assetInfo: AssetExportAssetInfo, input: AssetExportInput): AiAssetIdentity {
    return stripUndefined({
        name: assetInfo.display_name,
        identifiers: buildAssetIdentifiers(assetInfo),
        asset_type: assetInfo.asset_type ?? undefined,
        currency: assetInfo.currency,
        active: assetInfo.active,
        provider_code: assetInfo.provider_code ?? undefined,
        short_description: input.shortDescription ?? undefined,
        sector_distribution: input.sectorDistribution ?? undefined,
        geographic_distribution: input.geographicDistribution ?? undefined,
    }) as AiAssetIdentity;
}

/** Aggregates this asset's holding(s) across all brokers into a single blended line, or null if not held. */
function buildHolding(assetId: number, summary: Record<string, any> | null, contribution: Record<string, any> | null): AiAssetHolding | null {
    const holdings: any[] = (summary?.holdings ?? []).filter((h: any) => h.asset_id === assetId && (parseNum(h.quantity) ?? 0) > 0.0001);
    if (holdings.length === 0) return null;

    const contribPositions: any[] = contribution?.positions ?? [];
    const contribMap = new Map<string, any>();
    for (const cp of contribPositions) {
        contribMap.set(`${cp.asset_id}|${cp.broker_id}`, cp);
    }

    let quantity = 0;
    let marketValue = 0;
    let navWeightPercent = 0;
    let costBasis = 0;
    let unrealizedPnl = 0;
    let periodPnl = 0;
    let periodIncome = 0;
    const brokers = new Set<string>();
    let hasCostBasis = false;

    for (const h of holdings) {
        const qty = parseNum(h.quantity) ?? 0;
        quantity += qty;
        marketValue += parseCurrency(h.current_value) ?? 0;
        navWeightPercent += parseNum(h.nav_weight_percent) ?? 0;
        unrealizedPnl += parseCurrency(h.gain_loss) ?? 0;
        brokers.add(h.broker_name ?? `Broker #${h.broker_id}`);

        const wac = parseNum(h.wac_per_unit);
        if (wac != null && qty > 0) {
            costBasis += wac * qty;
            hasCostBasis = true;
        }

        const cp = contribMap.get(`${h.asset_id}|${h.broker_id}`);
        periodPnl += parseNum(cp?.period_pnl) ?? 0;
        periodIncome += parseNum(cp?.period_income) ?? 0;
    }

    const blendedWac = hasCostBasis && quantity > 0 ? costBasis / quantity : undefined;
    const unrealizedPnlPercent = hasCostBasis && costBasis > 0 ? Math.round((unrealizedPnl / costBasis) * 10000) / 100 : undefined;
    const periodPnlPercent = marketValue > 0 ? Math.round((periodPnl / marketValue) * 10000) / 100 : undefined;

    return stripUndefined({
        quantity: Math.round(quantity * 1e8) / 1e8,
        market_value: Math.round(marketValue * 100) / 100,
        nav_weight_percent: Math.round(navWeightPercent * 100) / 100,
        wac: blendedWac != null ? Math.round(blendedWac * 100) / 100 : undefined,
        cost_basis: hasCostBasis ? Math.round(costBasis * 100) / 100 : undefined,
        unrealized_pnl: Math.round(unrealizedPnl * 100) / 100,
        unrealized_pnl_percent: unrealizedPnlPercent,
        period_pnl: Math.round(periodPnl * 100) / 100,
        period_pnl_percent: periodPnlPercent,
        period_income: Math.round(periodIncome * 100) / 100,
        brokers: Array.from(brokers),
    }) as AiAssetHolding;
}

function buildAssetDataQuality(assetId: number, dq: Record<string, any> | null, summary: Record<string, any> | null): AiAssetDataQuality {
    const missingIds = new Set<number>();
    const staleIds = new Set<number>();

    for (const mp of dq?.missing_price_assets ?? []) missingIds.add(mp.asset_id);
    for (const mp of summary?.missing_price_assets ?? []) missingIds.add(mp.asset_id);
    for (const sp of dq?.stale_prices ?? []) staleIds.add(sp.asset_id);

    return {
        missing_price: missingIds.has(assetId),
        stale_price: staleIds.has(assetId),
    };
}

function parseCurrency(val: any): number | undefined {
    if (val == null) return undefined;
    if (typeof val === 'number') return val;
    if (typeof val === 'string') {
        const n = parseFloat(val);
        return Number.isNaN(n) ? undefined : n;
    }
    if (typeof val === 'object' && val.amount != null) {
        const n = parseFloat(val.amount);
        return Number.isNaN(n) ? undefined : n;
    }
    return undefined;
}

function parseNum(val: any): number | undefined {
    if (val == null) return undefined;
    if (typeof val === 'number') return val;
    const n = parseFloat(String(val));
    return Number.isNaN(n) ? undefined : n;
}

/** Remove undefined values from an object */
function stripUndefined<T extends Record<string, any>>(obj: T): T {
    const result = {} as T;
    for (const [k, v] of Object.entries(obj)) {
        if (v !== undefined) (result as any)[k] = v;
    }
    return result;
}
