import {schemas} from '$lib/api';

import {reconcileAiExportCatalog, type AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {
    AI_EXPORT_ANALYSIS_IDS,
    AI_EXPORT_CATALOG_VERSION,
    AI_EXPORT_DATASET_IDS,
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

function domainOf(id: string): AiExportDomain {
    return id.split('.')[0] as AiExportDomain;
}

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
        'portfolio.pac_planning': [suggestion('portfolio.technical', 'deeperTechnical', '3m', 'standard')],
        'portfolio.rebalancing': [suggestion('portfolio.technical', 'deeperTechnical', '1y', 'compact'), suggestion('portfolio.fifo', 'fifoDetail', '1y', 'standard')],
        'portfolio.performance_attribution': [suggestion('portfolio.fifo', 'fifoDetail', '1y', 'standard')],
        'portfolio.fifo_review': [suggestion('portfolio.performance_flows', 'performanceContext', '1y', 'standard')],
        'portfolio.technical_breadth': [suggestion('portfolio.technical', 'deeperTechnical', '3m', 'standard'), suggestion('portfolio.performance_flows', 'performanceContext', '1y', 'standard')],
        'portfolio.description': [suggestion('portfolio.technical', 'deeperTechnical', '3m', 'standard'), suggestion('portfolio.fifo', 'fifoDetail', '1y', 'compact')],
        'broker.review': [suggestion('broker.technical', 'deeperTechnical', '3m', 'standard')],
        'broker.cost_efficiency': [suggestion('broker.fifo', 'fifoDetail', '1y', 'standard')],
        'broker.concentration_context': [suggestion('broker.asset_comparison', 'deeperTechnical', '3m', 'standard')],
        'broker.fifo_review': [suggestion('broker.performance_flows', 'performanceContext', '1y', 'standard')],
        'asset.trend_analysis': [suggestion('asset.position_performance', 'positionContext', '1y', 'standard')],
        'asset.position_review': [suggestion('asset.market_technical', 'deeperTechnical', '1y', 'standard')],
        'fx.trend_review': [suggestion('fx.direct_exposure', 'directExposure', '3m', 'standard')],
        'fx.conversion_timing': [suggestion('fx.direct_exposure', 'directExposure', '3m', 'standard')],
        'fx.exposure_impact': [suggestion('fx.market_technical', 'deeperTechnical', '1y', 'compact')],
    };
    return values[id] ?? [];
}

function analysisDatasetIds(id: AiExportAnalysisId): {required: readonly AiExportDatasetId[]; optional: readonly AiExportDatasetId[]} {
    const mapping: Record<AiExportAnalysisId, {required: readonly AiExportDatasetId[]; optional: readonly AiExportDatasetId[]}> = {
        'portfolio.pac_planning': {required: ['portfolio.overview', 'portfolio.performance_flows'], optional: ['portfolio.asset_snapshot', 'portfolio.drawdown_context']},
        'portfolio.rebalancing': {required: ['portfolio.overview'], optional: ['portfolio.performance_flows', 'portfolio.asset_comparison', 'portfolio.drawdown_context']},
        'portfolio.performance_attribution': {required: ['portfolio.overview', 'portfolio.performance_flows'], optional: []},
        'portfolio.income_review': {required: ['portfolio.overview', 'portfolio.performance_flows', 'portfolio.income_evidence'], optional: []},
        'portfolio.fifo_review': {required: ['portfolio.overview', 'portfolio.fifo'], optional: []},
        'portfolio.technical_breadth': {required: ['portfolio.overview', 'portfolio.technical_summary'], optional: []},
        'portfolio.description': {required: ['portfolio.overview'], optional: ['portfolio.performance_flows', 'portfolio.technical_summary']},
        'broker.review': {required: ['broker.overview', 'broker.performance_flows'], optional: ['broker.asset_comparison', 'broker.fifo', 'broker.drawdown_context', 'broker.concentration_evidence']},
        'broker.cost_efficiency': {required: ['broker.overview', 'broker.performance_flows', 'broker.cost_efficiency_evidence'], optional: []},
        'broker.concentration_context': {required: ['broker.overview', 'broker.concentration_evidence'], optional: ['broker.technical_summary']},
        'broker.fifo_review': {required: ['broker.overview', 'broker.fifo'], optional: []},
        'asset.trend_analysis': {required: ['asset.overview', 'asset.market_technical'], optional: []},
        'asset.position_review': {required: ['asset.overview', 'asset.position_performance'], optional: ['asset.position_context', 'asset.drawdown_context']},
        'fx.trend_review': {required: ['fx.overview', 'fx.market_technical'], optional: []},
        'fx.conversion_timing': {required: ['fx.overview', 'fx.market_technical', 'fx.conversion_timing_context'], optional: ['fx.direct_exposure']},
        'fx.exposure_impact': {required: ['fx.overview', 'fx.direct_exposure'], optional: ['fx.market_context']},
    };
    return mapping[id];
}

export function backendCatalogFixture(): AiExportBackendCatalogResponse {
    return schemas.AiExportCatalogResponse.parse({
        schema_version: AI_EXPORT_SCHEMA_VERSION,
        catalog_version: AI_EXPORT_CATALOG_VERSION,
        datasets: AI_EXPORT_DATASET_IDS.map((id) => ({
            kind: 'dataset',
            id,
            version: AI_EXPORT_SELECTION_VERSION,
            domain: domainOf(id),
            display_i18n_key: `aiExport.dataset.${id}.display`,
            description_i18n_key: `aiExport.dataset.${id}.description`,
            icon: 'database',
            applicability_code: 'always_applicable',
            applicable_pages: [pageOf(domainOf(id))],
            supported_detail_levels: ['compact', 'standard', 'full'],
            period_semantics: id.endsWith('.overview') ? 'as_of' : 'aggregated',
            required_component_ids: [`${domainOf(id)}.summary`],
            optional_component_ids: [],
        })),
        analyses: AI_EXPORT_ANALYSIS_IDS.map((id) => {
            const instruction = findAiExportAnalysisInstruction(id);
            const response = findAiExportResponseContract(id);
            return {
                kind: 'analysis',
                id,
                version: AI_EXPORT_SELECTION_VERSION,
                domain: domainOf(id),
                display_i18n_key: `aiExport.analysis.${id}.display`,
                description_i18n_key: `aiExport.analysis.${id}.description`,
                icon: 'activity',
                applicability_code: 'always_applicable',
                applicable_pages: [pageOf(domainOf(id))],
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
                    dataset_id: `${selection.domain}.overview`,
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
