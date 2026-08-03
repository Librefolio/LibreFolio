import {schemas} from '$lib/api';
import type {z} from 'zod';

export type AiExportDomain = z.output<typeof schemas.AiExportDomain>;
export type AiExportDetailLevel = z.output<typeof schemas.AiExportDetailLevel>;
export type AiExportDatasetCatalogEntry = z.output<typeof schemas.AiExportDatasetCatalogEntry>;
export type AiExportAnalysisCatalogEntry = z.output<typeof schemas.AiExportAnalysisCatalogEntry>;
export type AiExportBackendCatalogResponse = z.output<typeof schemas.AiExportCatalogResponse>;
type GeneratedAiExportSnapshotResponse = z.output<typeof schemas.AiExportSnapshotResponse>;
type GeneratedAiExportSnapshotMeta = GeneratedAiExportSnapshotResponse['meta'];
export interface AiExportTechnicalSamplingManifest {
    readonly detail_level: AiExportDetailLevel;
    readonly price_policy?: z.output<typeof schemas.AiExportPriceSamplingPolicy> | null;
    readonly indicator_policies: readonly z.output<typeof schemas.AiExportIndicatorSamplingPolicy>[];
    readonly indicator_history_row_limit: number | null;
}
export interface AiExportEntityDirectory {
    readonly assets: readonly z.output<typeof schemas.AiExportAssetDirectoryEntry>[];
    readonly brokers: readonly z.output<typeof schemas.AiExportBrokerDirectoryEntry>[];
    readonly fx_pairs: readonly z.output<typeof schemas.AiExportFxPairDirectoryEntry>[];
}
export type AiExportSnapshotResponse = Omit<GeneratedAiExportSnapshotResponse, 'analysis_contract' | 'technical_sampling' | 'event_selection' | 'entity_directory' | 'meta'> & {
    analysis_contract?: z.output<typeof schemas.AiExportAnalysisContract> | null;
    technical_sampling?: AiExportTechnicalSamplingManifest | null;
    event_selection?: z.output<typeof schemas.AiExportEventSelectionManifest> | null;
    entity_directory: AiExportEntityDirectory;
    meta: Omit<GeneratedAiExportSnapshotMeta, 'history_coverage'> & {
        history_coverage?: z.output<typeof schemas.AiExportHistoryCoverage> | null;
    };
};
export type AiExportSelectionKind = 'dataset' | 'analysis';
export type AiExportCatalogEntry = AiExportDatasetCatalogEntry | AiExportAnalysisCatalogEntry;

export const AI_EXPORT_SCHEMA_VERSION = 2;
export const AI_EXPORT_CATALOG_VERSION = 2;
export const AI_EXPORT_SELECTION_VERSION = 2;
export const AI_EXPORT_DETAIL_LEVELS = ['compact', 'standard', 'full'] as const satisfies readonly AiExportDetailLevel[];
export const AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard' satisfies AiExportDetailLevel;
export const AI_EXPORT_DOMAIN_ORDER = ['portfolio', 'broker', 'asset', 'fx'] as const satisfies readonly AiExportDomain[];
export const AI_EXPORT_PAGE_LABEL_KEYS: Readonly<Record<string, string>> = {
    dashboard: 'nav.dashboard',
    broker: 'brokers.title',
    asset: 'common.assets',
    fx: 'fx.title',
};
export const AI_EXPORT_PAGE_FEATURE_LABEL_KEYS: Readonly<Record<string, string>> = {
    dashboard: 'dashboard.aiExport',
    broker: 'dashboard.aiExport',
    asset: 'assetDetail.aiExport',
    fx: 'fxDetail.aiExport',
};

export const AI_EXPORT_DATASET_IDS = [
    'portfolio.overview',
    'portfolio.performance_flows',
    'portfolio.technical_summary',
    'portfolio.asset_snapshot',
    'portfolio.asset_comparison',
    'portfolio.drawdown_context',
    'portfolio.income_evidence',
    'portfolio.technical',
    'portfolio.fifo',
    'portfolio.all_data',
    'broker.overview',
    'broker.performance_flows',
    'broker.technical_summary',
    'broker.asset_comparison',
    'broker.drawdown_context',
    'broker.concentration_evidence',
    'broker.cost_efficiency_evidence',
    'broker.technical',
    'broker.fifo',
    'broker.all_data',
    'asset.overview',
    'asset.position_performance',
    'asset.position_context',
    'asset.drawdown_context',
    'asset.market_technical',
    'asset.all_data',
    'fx.overview',
    'fx.market_context',
    'fx.conversion_timing_context',
    'fx.market_technical',
    'fx.direct_exposure',
    'fx.all_data',
] as const;

export const AI_EXPORT_ANALYSIS_IDS = [
    'portfolio.pac_planning',
    'portfolio.rebalancing',
    'portfolio.performance_attribution',
    'portfolio.market_events_review',
    'portfolio.income_review',
    'portfolio.fifo_review',
    'portfolio.technical_breadth',
    'portfolio.description',
    'broker.review',
    'broker.cost_efficiency',
    'broker.concentration_context',
    'broker.fifo_review',
    'asset.trend_analysis',
    'asset.position_review',
    'fx.trend_review',
    'fx.conversion_timing',
    'fx.exposure_impact',
] as const;

export type AiExportDatasetId = (typeof AI_EXPORT_DATASET_IDS)[number];
export type AiExportAnalysisId = (typeof AI_EXPORT_ANALYSIS_IDS)[number];
export type AiExportSelectionId = AiExportDatasetId | AiExportAnalysisId;

export interface AiExportCompatibleSelection {
    readonly kind: AiExportSelectionKind;
    readonly id: AiExportSelectionId;
    readonly domain: AiExportDomain;
    readonly version: 2;
    readonly supportedDetailLevels: readonly AiExportDetailLevel[];
    readonly entry: AiExportCatalogEntry;
}

export function aiExportSelectionKey(kind: AiExportSelectionKind, id: string): string {
    return `${kind}:${id}`;
}

export function isAiExportDatasetId(value: string): value is AiExportDatasetId {
    return AI_EXPORT_DATASET_IDS.some((id) => id === value);
}

export function isAiExportAnalysisId(value: string): value is AiExportAnalysisId {
    return AI_EXPORT_ANALYSIS_IDS.some((id) => id === value);
}

function requireIndicatorHistoryRowLimit(value: number | null | undefined): number | null {
    if (value === undefined) throw new TypeError('AI Export technical_sampling.indicator_history_row_limit is required');
    return value;
}

export function normalizeAiExportSnapshotResponse(response: GeneratedAiExportSnapshotResponse): AiExportSnapshotResponse {
    const analysisContract = response.analysis_contract;
    if (Array.isArray(analysisContract)) throw new TypeError('AI Export analysis_contract must not be an array');
    const technicalSampling = response.technical_sampling;
    if (Array.isArray(technicalSampling)) throw new TypeError('AI Export technical_sampling must not be an array');
    const pricePolicy = technicalSampling?.price_policy;
    if (Array.isArray(pricePolicy)) throw new TypeError('AI Export technical_sampling.price_policy must not be an array');
    const indicatorHistoryRowLimit = technicalSampling?.indicator_history_row_limit;
    if (Array.isArray(indicatorHistoryRowLimit)) throw new TypeError('AI Export technical_sampling.indicator_history_row_limit must not be an array');
    const eventSelection = response.event_selection;
    if (Array.isArray(eventSelection)) throw new TypeError('AI Export event_selection must not be an array');
    const historyCoverage = response.meta.history_coverage;
    if (Array.isArray(historyCoverage)) throw new TypeError('AI Export meta.history_coverage must not be an array');
    const normalizedTechnicalSampling: AiExportTechnicalSamplingManifest | null | undefined = technicalSampling
        ? {
              ...technicalSampling,
              price_policy: pricePolicy,
              indicator_policies: technicalSampling.indicator_policies ?? [],
              indicator_history_row_limit: requireIndicatorHistoryRowLimit(indicatorHistoryRowLimit),
          }
        : technicalSampling;
    return {
        ...response,
        analysis_contract: analysisContract,
        technical_sampling: normalizedTechnicalSampling,
        event_selection: eventSelection,
        meta: {
            ...response.meta,
            history_coverage: historyCoverage,
        },
        entity_directory: {
            assets: response.entity_directory?.assets ?? [],
            brokers: response.entity_directory?.brokers ?? [],
            fx_pairs: response.entity_directory?.fx_pairs ?? [],
        },
    };
}
