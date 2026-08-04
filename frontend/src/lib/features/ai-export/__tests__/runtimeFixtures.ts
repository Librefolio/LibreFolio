import {schemas} from '$lib/api';

import {reconcileAiExportCatalog, type AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {
    AI_EXPORT_ANALYSIS_IDS,
    AI_EXPORT_CATALOG_VERSION,
    AI_EXPORT_DATASET_IDS,
    AI_EXPORT_PUBLIC_CATALOG_CONFIG,
    AI_EXPORT_SCHEMA_VERSION,
    AI_EXPORT_SELECTION_VERSION,
    normalizeAiExportSnapshotResponse,
    type AiExportAnalysisId,
    type AiExportBackendCatalogResponse,
    type AiExportCompatibleSelection,
    type AiExportDatasetId,
    type AiExportDomain,
    type AiExportSnapshotResponse,
} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {findAiExportAnalysisInstruction} from '../templates/sharedInstructions';

function pageOf(domain: AiExportDomain): string {
    return domain === 'portfolio' ? 'dashboard' : domain;
}

function additionalSuggestions(id: AiExportAnalysisId) {
    const suggestion = (dataset_id: AiExportDatasetId, reason: string, recommended_period: '3m' | '6m' | '1y' | 'maximum_available', recommended_detail: 'compact' | 'standard' | 'full') => ({
        dataset_id,
        reason_i18n_key: `aiExport.additionalData.reason.${reason}`,
        recommended_period,
        recommended_detail,
        necessity: 'optional' as const,
    });
    const values: Partial<Record<AiExportAnalysisId, ReturnType<typeof suggestion>[]>> = {
        'portfolio.pac_planning': [suggestion('portfolio.asset_history', 'deeperTechnical', '3m', 'standard')],
        'portfolio.rebalancing': [suggestion('portfolio.asset_history', 'deeperTechnical', '1y', 'compact')],
        'portfolio.performance_market_drivers': [suggestion('portfolio.asset_history', 'deeperTechnical', '3m', 'standard')],
        'portfolio.fiscal_lots': [suggestion('portfolio.asset_history', 'deeperTechnical', '1y', 'compact')],
        'broker.review': [suggestion('broker.asset_history', 'deeperTechnical', '3m', 'standard')],
        'broker.performance_market_drivers': [suggestion('broker.asset_history', 'deeperTechnical', '3m', 'standard')],
        'broker.fiscal_lots': [suggestion('broker.asset_history', 'deeperTechnical', '1y', 'compact')],
        'asset.position_review': [suggestion('asset.market_history', 'deeperTechnical', '1y', 'standard')],
        'asset.market_analysis': [suggestion('asset.position_and_history', 'positionContext', '1y', 'standard')],
        'fx.pair_analysis': [suggestion('fx.market_and_exposure', 'directExposure', '3m', 'compact')],
        'fx.exposure_impact': [suggestion('fx.market_history', 'deeperTechnical', '1y', 'compact')],
    };
    return values[id] ?? [];
}

function analysisDatasetIds(id: AiExportAnalysisId): {required: readonly string[]; optional: readonly string[]} {
    const mapping: Record<AiExportAnalysisId, {required: readonly string[]; optional: readonly string[]}> = {
        'portfolio.pac_planning': {required: ['portfolio.overview_and_history'], optional: []},
        'portfolio.rebalancing': {required: ['portfolio.overview_and_history'], optional: []},
        'portfolio.performance_market_drivers': {required: ['portfolio.overview_and_history'], optional: []},
        'portfolio.fiscal_lots': {required: ['portfolio.overview_and_history', 'portfolio.fifo'], optional: []},
        'broker.review': {required: ['broker.overview_and_history'], optional: []},
        'broker.performance_market_drivers': {required: ['broker.overview_and_history'], optional: []},
        'broker.fiscal_lots': {required: ['broker.overview_and_history', 'broker.fifo'], optional: []},
        'asset.position_review': {required: ['asset.position_and_history'], optional: []},
        'asset.market_analysis': {required: ['asset.market_history'], optional: []},
        'fx.pair_analysis': {required: ['fx.market_history'], optional: []},
        'fx.exposure_impact': {required: ['fx.market_and_exposure'], optional: []},
    };
    return mapping[id];
}

export function backendCatalogFixture(): AiExportBackendCatalogResponse {
    const configById = new Map(AI_EXPORT_PUBLIC_CATALOG_CONFIG.map((entry) => [entry.id, entry]));
    return schemas.AiExportCatalogResponse.parse({
        schema_version: AI_EXPORT_SCHEMA_VERSION,
        catalog_version: AI_EXPORT_CATALOG_VERSION,
        datasets: AI_EXPORT_DATASET_IDS.map((id) => {
            const config = configById.get(id);
            if (!config || config.group !== 'dataset') throw new Error(`Missing Dataset config for ${id}`);
            return {
                kind: 'dataset',
                id,
                version: AI_EXPORT_SELECTION_VERSION,
                domain: config.domain,
                display_i18n_key: config.displayI18nKey,
                description_i18n_key: config.descriptionI18nKey,
                icon: config.icon,
                applicability_code: 'always_applicable',
                applicable_pages: [pageOf(config.domain)],
                supported_detail_levels: ['compact', 'standard', 'full'],
                period_semantics: 'aggregated',
                required_component_ids: [`${config.domain}.summary`],
                optional_component_ids: [],
            };
        }),
        analyses: AI_EXPORT_ANALYSIS_IDS.map((id) => {
            const config = configById.get(id);
            if (!config || config.group !== 'analysis') throw new Error(`Missing Analysis config for ${id}`);
            const instruction = findAiExportAnalysisInstruction(id);
            const response = findAiExportResponseContract(id);
            return {
                kind: 'analysis',
                id,
                version: AI_EXPORT_SELECTION_VERSION,
                domain: config.domain,
                display_i18n_key: config.displayI18nKey,
                description_i18n_key: config.descriptionI18nKey,
                icon: config.icon,
                applicability_code: 'always_applicable',
                applicable_pages: [pageOf(config.domain)],
                supported_detail_levels: ['compact', 'standard', 'full'],
                required_dataset_ids: analysisDatasetIds(id).required,
                optional_dataset_ids: analysisDatasetIds(id).optional,
                instruction_template_id: instruction.id,
                instruction_template_version: instruction.version,
                response_contract_id: response.id,
                response_contract_version: response.version,
                supports_user_notes: true,
                additional_export_suggestions: additionalSuggestions(id),
            };
        }),
    });
}

export function compatibilityFixture(): AiExportCatalogCompatibilityResult {
    return reconcileAiExportCatalog(backendCatalogFixture());
}

export function selectionFixture(kind: 'dataset', id: AiExportDatasetId): AiExportCompatibleSelection;
export function selectionFixture(kind: 'analysis', id: AiExportAnalysisId): AiExportCompatibleSelection;
export function selectionFixture(kind: 'dataset' | 'analysis', id: AiExportDatasetId | AiExportAnalysisId): AiExportCompatibleSelection {
    const selection = compatibilityFixture().byKey.get(`${kind}:${id}`);
    if (!selection) throw new Error(`Missing fixture selection ${kind}:${id}`);
    return selection;
}

export function snapshotFixture(selection: AiExportCompatibleSelection, detailLevel: 'compact' | 'standard' | 'full' = 'standard', exportedPeriod: {start: string; end: string} = {start: '2026-01-01', end: '2026-03-31'}): AiExportSnapshotResponse {
    const analysis = selection.kind === 'analysis' && selection.entry.kind === 'analysis' ? selection.entry : null;
    return normalizeAiExportSnapshotResponse(
        schemas.AiExportSnapshotResponse.parse({
            domain: selection.domain,
            selection:
                selection.kind === 'dataset'
                    ? {kind: 'dataset', id: selection.id, version: AI_EXPORT_SELECTION_VERSION}
                    : {
                          kind: 'analysis',
                          id: selection.id,
                          version: AI_EXPORT_SELECTION_VERSION,
                          instruction_template_id: analysis?.instruction_template_id,
                          instruction_template_version: analysis!.instruction_template_version,
                          response_contract_id: analysis?.response_contract_id,
                          response_contract_version: analysis!.response_contract_version,
                      },
            detail_level: detailLevel,
            target: selection.domain === 'portfolio' ? {kind: 'portfolio'} : selection.domain === 'broker' ? {kind: 'broker', broker_id: 1} : selection.domain === 'asset' ? {kind: 'asset', asset_id: 7} : {kind: 'fx_pair', base_currency: 'USD', quote_currency: 'EUR'},
            entity_directory:
                selection.domain === 'asset'
                    ? {
                          assets: [
                              {
                                  asset_id: 7,
                                  display_name: 'Fixture Asset',
                                  ticker: 'FIX',
                                  isin: null,
                                  cusip: null,
                                  sedol: null,
                                  figi: null,
                                  other_identifiers: [],
                                  currency: 'EUR',
                                  asset_type: 'ETF',
                                  quote_base_quantity: 1,
                              },
                          ],
                          brokers: [],
                          fx_pairs: [],
                      }
                    : selection.domain === 'broker'
                      ? {
                            assets: [],
                            brokers: [{broker_id: 1, display_name: 'Fixture Broker'}],
                            fx_pairs: [],
                        }
                      : selection.domain === 'fx'
                        ? {
                              assets: [],
                              brokers: [],
                              fx_pairs: [{base_currency: 'USD', quote_currency: 'EUR'}],
                          }
                        : {assets: [], brokers: [], fx_pairs: []},
            meta: {
                schema_version: AI_EXPORT_SCHEMA_VERSION,
                catalog_version: AI_EXPORT_CATALOG_VERSION,
                request_id: 'req-fixture',
                generated_at: '2026-03-31T12:00:00Z',
                snapshot_as_of: '2026-03-31',
                exported_period: exportedPeriod,
                calculation_range: null,
                warmup_policy: 'component_owned',
                earliest_calculation_date: null,
                target_currency: 'EUR',
            },
            dataset_manifest: [
                {
                    dataset_id: selection.kind === 'dataset' ? selection.id : analysis!.required_dataset_ids[0],
                    dataset_version: AI_EXPORT_SELECTION_VERSION,
                    role: selection.kind === 'dataset' ? 'selected' : 'required',
                },
            ],
            analysis_contract: analysis
                ? {
                      instruction_template_id: analysis.instruction_template_id,
                      instruction_template_version: analysis.instruction_template_version,
                      response_contract_id: analysis.response_contract_id,
                      response_contract_version: analysis.response_contract_version,
                  }
                : null,
            sections: [
                {
                    component_id: `${selection.domain}.summary`,
                    component_version: 1,
                    schema_id: `${selection.domain}.summary`,
                    schema_version: 1,
                    payload: {
                        as_of: '2026-03-31',
                        rows: [
                            {
                                bucket_start: '2026-03-01',
                                bucket_end: '2026-03-31',
                                min: {value: -20, date: '2026-03-04'},
                                max: {value: 5, date: '2026-03-20'},
                                last: {value: -3, date: '2026-03-31'},
                            },
                        ],
                    },
                },
            ],
            stats: {
                dataset_count: 1,
                section_count: 1,
                serialized_characters: 500,
                serialized_bytes: 500,
                estimated_tokens: 125,
                token_estimation_method: 'chars_div_4_v1',
            },
        }),
    );
}
