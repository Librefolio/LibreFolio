import {schemas} from '$lib/api';
import type {z} from 'zod';

export type AiExportDomain = z.output<typeof schemas.AiExportDomain>;
export type AiExportDetailLevel = z.output<typeof schemas.AiExportDetailLevel>;
export type AiExportDatasetCatalogEntry = z.output<typeof schemas.AiExportDatasetCatalogEntry>;
export type AiExportAnalysisCatalogEntry = z.output<typeof schemas.AiExportAnalysisCatalogEntry>;
export type AiExportBackendCatalogResponse = z.output<typeof schemas.AiExportCatalogResponse>;
type GeneratedAiExportSnapshotResponse = z.output<typeof schemas.AiExportSnapshotResponse>;
export type AiExportSnapshotResponse = Omit<GeneratedAiExportSnapshotResponse, 'analysis_contract'> & {
    analysis_contract?: z.output<typeof schemas.AiExportAnalysisContract> | null;
};
export type AiExportSelectionKind = 'dataset' | 'analysis';
export type AiExportCatalogEntry = AiExportDatasetCatalogEntry | AiExportAnalysisCatalogEntry;

export const AI_EXPORT_SCHEMA_VERSION = 1;
export const AI_EXPORT_CATALOG_VERSION = 1;
export const AI_EXPORT_SELECTION_VERSION = 1;
export const AI_EXPORT_DETAIL_LEVELS = ['compact', 'standard', 'full'] as const satisfies readonly AiExportDetailLevel[];
export const AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard' satisfies AiExportDetailLevel;
export const AI_EXPORT_DOMAIN_ORDER = ['portfolio', 'broker', 'asset', 'fx'] as const satisfies readonly AiExportDomain[];

export const AI_EXPORT_DATASET_IDS = [
    'portfolio.overview',
    'portfolio.performance_flows',
    'portfolio.technical',
    'portfolio.fifo',
    'portfolio.all_data',
    'broker.overview',
    'broker.performance_flows',
    'broker.technical',
    'broker.fifo',
    'broker.all_data',
    'asset.overview',
    'asset.position_performance',
    'asset.market_technical',
    'asset.all_data',
    'fx.overview',
    'fx.market_technical',
    'fx.direct_exposure',
    'fx.all_data',
] as const;

export const AI_EXPORT_ANALYSIS_IDS = [
    'portfolio.pac_planning',
    'portfolio.rebalancing',
    'portfolio.performance_attribution',
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
    readonly version: 1;
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

export function normalizeAiExportSnapshotResponse(response: GeneratedAiExportSnapshotResponse): AiExportSnapshotResponse {
    const analysisContract = response.analysis_contract;
    if (Array.isArray(analysisContract)) throw new TypeError('AI Export analysis_contract must not be an array');
    return {
        ...response,
        analysis_contract: analysisContract,
    };
}
