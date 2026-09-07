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

export const AI_EXPORT_SCHEMA_VERSION = 1;
export const AI_EXPORT_CATALOG_VERSION = 1;
export const AI_EXPORT_SELECTION_VERSION = 1;
export const AI_EXPORT_DETAIL_LEVELS = ['compact', 'standard', 'full'] as const satisfies readonly AiExportDetailLevel[];
export const AI_EXPORT_DEFAULT_DETAIL_LEVEL = 'standard' satisfies AiExportDetailLevel;

/**
 * Resolve the detail level to use for a selection: the default when supported,
 * otherwise the first level the selection declares.
 *
 * Exported as a function rather than as a bare constant so callers adopt the *rule*
 * instead of re-inlining the literal (see audit report 13, DRY orphan M4.1).
 */
export function resolveDefaultDetailLevel(supportedDetailLevels: readonly AiExportDetailLevel[]): AiExportDetailLevel {
    return supportedDetailLevels.includes(AI_EXPORT_DEFAULT_DETAIL_LEVEL) ? AI_EXPORT_DEFAULT_DETAIL_LEVEL : supportedDetailLevels[0];
}
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

export const AI_EXPORT_PUBLIC_CATALOG_CONFIG = [
    {
        group: 'dataset',
        id: 'portfolio.overview_and_history',
        domain: 'portfolio',
        icon: 'layout-dashboard',
        displayI18nKey: 'aiExport.dataset.portfolio.overview_and_history.display',
        descriptionI18nKey: 'aiExport.dataset.portfolio.overview_and_history.description',
    },
    {
        group: 'dataset',
        id: 'portfolio.asset_history',
        domain: 'portfolio',
        icon: 'activity',
        displayI18nKey: 'aiExport.dataset.portfolio.asset_history.display',
        descriptionI18nKey: 'aiExport.dataset.portfolio.asset_history.description',
    },
    {
        group: 'dataset',
        id: 'broker.overview_and_history',
        domain: 'broker',
        icon: 'landmark',
        displayI18nKey: 'aiExport.dataset.broker.overview_and_history.display',
        descriptionI18nKey: 'aiExport.dataset.broker.overview_and_history.description',
    },
    {
        group: 'dataset',
        id: 'broker.asset_history',
        domain: 'broker',
        icon: 'activity',
        displayI18nKey: 'aiExport.dataset.broker.asset_history.display',
        descriptionI18nKey: 'aiExport.dataset.broker.asset_history.description',
    },
    {
        group: 'dataset',
        id: 'asset.position_and_history',
        domain: 'asset',
        icon: 'wallet',
        displayI18nKey: 'aiExport.dataset.asset.position_and_history.display',
        descriptionI18nKey: 'aiExport.dataset.asset.position_and_history.description',
    },
    {
        group: 'dataset',
        id: 'asset.market_history',
        domain: 'asset',
        icon: 'activity',
        displayI18nKey: 'aiExport.dataset.asset.market_history.display',
        descriptionI18nKey: 'aiExport.dataset.asset.market_history.description',
    },
    {
        group: 'dataset',
        id: 'fx.market_and_exposure',
        domain: 'fx',
        icon: 'arrow-left-right',
        displayI18nKey: 'aiExport.dataset.fx.market_and_exposure.display',
        descriptionI18nKey: 'aiExport.dataset.fx.market_and_exposure.description',
    },
    {
        group: 'dataset',
        id: 'fx.market_history',
        domain: 'fx',
        icon: 'activity',
        displayI18nKey: 'aiExport.dataset.fx.market_history.display',
        descriptionI18nKey: 'aiExport.dataset.fx.market_history.description',
    },
    {
        group: 'analysis',
        id: 'portfolio.pac_planning',
        domain: 'portfolio',
        icon: 'calendar-clock',
        displayI18nKey: 'aiExport.analysis.portfolio.pac_planning.display',
        descriptionI18nKey: 'aiExport.analysis.portfolio.pac_planning.description',
    },
    {
        group: 'analysis',
        id: 'portfolio.rebalancing',
        domain: 'portfolio',
        icon: 'scale',
        displayI18nKey: 'aiExport.analysis.portfolio.rebalancing.display',
        descriptionI18nKey: 'aiExport.analysis.portfolio.rebalancing.description',
    },
    {
        group: 'analysis',
        id: 'portfolio.performance_market_drivers',
        domain: 'portfolio',
        icon: 'newspaper',
        displayI18nKey: 'aiExport.analysis.portfolio.performance_market_drivers.display',
        descriptionI18nKey: 'aiExport.analysis.portfolio.performance_market_drivers.description',
    },
    {
        group: 'analysis',
        id: 'portfolio.fiscal_lots',
        domain: 'portfolio',
        icon: 'list-ordered',
        displayI18nKey: 'aiExport.analysis.portfolio.fiscal_lots.display',
        descriptionI18nKey: 'aiExport.analysis.portfolio.fiscal_lots.description',
    },
    {
        group: 'analysis',
        id: 'broker.review',
        domain: 'broker',
        icon: 'landmark',
        displayI18nKey: 'aiExport.analysis.broker.review.display',
        descriptionI18nKey: 'aiExport.analysis.broker.review.description',
    },
    {
        group: 'analysis',
        id: 'broker.performance_market_drivers',
        domain: 'broker',
        icon: 'newspaper',
        displayI18nKey: 'aiExport.analysis.broker.performance_market_drivers.display',
        descriptionI18nKey: 'aiExport.analysis.broker.performance_market_drivers.description',
    },
    {
        group: 'analysis',
        id: 'broker.fiscal_lots',
        domain: 'broker',
        icon: 'list-ordered',
        displayI18nKey: 'aiExport.analysis.broker.fiscal_lots.display',
        descriptionI18nKey: 'aiExport.analysis.broker.fiscal_lots.description',
    },
    {
        group: 'analysis',
        id: 'asset.position_review',
        domain: 'asset',
        icon: 'wallet',
        displayI18nKey: 'aiExport.analysis.asset.position_review.display',
        descriptionI18nKey: 'aiExport.analysis.asset.position_review.description',
    },
    {
        group: 'analysis',
        id: 'asset.market_analysis',
        domain: 'asset',
        icon: 'trending-up',
        displayI18nKey: 'aiExport.analysis.asset.market_analysis.display',
        descriptionI18nKey: 'aiExport.analysis.asset.market_analysis.description',
    },
    {
        group: 'analysis',
        id: 'fx.pair_analysis',
        domain: 'fx',
        icon: 'trending-up',
        displayI18nKey: 'aiExport.analysis.fx.pair_analysis.display',
        descriptionI18nKey: 'aiExport.analysis.fx.pair_analysis.description',
    },
    {
        group: 'analysis',
        id: 'fx.exposure_impact',
        domain: 'fx',
        icon: 'scale',
        displayI18nKey: 'aiExport.analysis.fx.exposure_impact.display',
        descriptionI18nKey: 'aiExport.analysis.fx.exposure_impact.description',
    },
] as const;

type AiExportPublicCatalogConfigEntry = (typeof AI_EXPORT_PUBLIC_CATALOG_CONFIG)[number];
export type AiExportDatasetId = Extract<AiExportPublicCatalogConfigEntry, {group: 'dataset'}>['id'];
export type AiExportAnalysisId = Extract<AiExportPublicCatalogConfigEntry, {group: 'analysis'}>['id'];
export const AI_EXPORT_DATASET_IDS = AI_EXPORT_PUBLIC_CATALOG_CONFIG.filter((entry) => entry.group === 'dataset').map((entry) => entry.id) as readonly AiExportDatasetId[];
export const AI_EXPORT_ANALYSIS_IDS = AI_EXPORT_PUBLIC_CATALOG_CONFIG.filter((entry) => entry.group === 'analysis').map((entry) => entry.id) as readonly AiExportAnalysisId[];
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
