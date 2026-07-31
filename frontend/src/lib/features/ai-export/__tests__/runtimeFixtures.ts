import {schemas} from '$lib/api';

import {reconcileAiExportCatalog, type AiExportCatalogCompatibilityResult} from '../catalog/compatibility';
import {AI_EXPORT_ANALYSIS_IDS, AI_EXPORT_DATASET_IDS, normalizeAiExportSnapshotResponse, type AiExportAnalysisId, type AiExportBackendCatalogResponse, type AiExportCompatibleSelection, type AiExportDatasetId, type AiExportDomain, type AiExportSnapshotResponse} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {findAiExportAnalysisInstruction} from '../templates/sharedInstructions';

function domainOf(id: string): AiExportDomain {
    return id.split('.')[0] as AiExportDomain;
}

export function backendCatalogFixture(): AiExportBackendCatalogResponse {
    return schemas.AiExportCatalogResponse.parse({
        schema_version: 1,
        catalog_version: 1,
        datasets: AI_EXPORT_DATASET_IDS.map((id) => ({
            kind: 'dataset',
            id,
            version: 1,
            domain: domainOf(id),
            display_i18n_key: `aiExport.dataset.${id}.display`,
            description_i18n_key: `aiExport.dataset.${id}.description`,
            icon: 'database',
            applicability_code: 'always_applicable',
            applicable_pages: [domainOf(id)],
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
                version: 1,
                domain: domainOf(id),
                display_i18n_key: `aiExport.analysis.${id}.display`,
                description_i18n_key: `aiExport.analysis.${id}.description`,
                icon: 'activity',
                applicability_code: 'always_applicable',
                applicable_pages: [domainOf(id)],
                supported_detail_levels: ['compact', 'standard', 'full'],
                required_dataset_ids: [`${domainOf(id)}.overview`],
                optional_dataset_ids: [],
                instruction_template_id: instruction.id,
                instruction_template_version: instruction.version,
                response_contract_id: response.id,
                response_contract_version: response.version,
                supports_user_notes: true,
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
                    ? {kind: 'dataset', id: selection.id, version: 1}
                    : {
                          kind: 'analysis',
                          id: selection.id,
                          version: 1,
                          instruction_template_id: analysis?.instruction_template_id,
                          instruction_template_version: 1,
                          response_contract_id: analysis?.response_contract_id,
                          response_contract_version: 1,
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
                schema_version: 1,
                catalog_version: 1,
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
                    dataset_version: 1,
                    role: selection.kind === 'dataset' ? 'selected' : 'required',
                },
            ],
            analysis_contract: analysis
                ? {
                      instruction_template_id: analysis.instruction_template_id,
                      instruction_template_version: 1,
                      response_contract_id: analysis.response_contract_id,
                      response_contract_version: 1,
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
                estimated_tokens: 125,
                token_estimation_method: 'chars_div_4_v1',
            },
        }),
    );
}
