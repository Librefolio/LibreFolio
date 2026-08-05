import {describe, expect, it} from 'vitest';

import {AI_EXPORT_ANALYSIS_IDS, AI_EXPORT_DATASET_IDS, AI_EXPORT_PUBLIC_CATALOG_CONFIG} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';
import {findAiExportAnalysisInstruction} from '../templates/sharedInstructions';
import {backendCatalogFixture} from './runtimeFixtures';

describe('AI Export V1 public catalog', () => {
    it('registers exactly 8 Dataset and 11 Analysis entries with approved group, domain, and icon config', () => {
        expect(AI_EXPORT_DATASET_IDS).toEqual(['portfolio.overview_and_history', 'portfolio.asset_history', 'broker.overview_and_history', 'broker.asset_history', 'asset.position_and_history', 'asset.market_history', 'fx.market_and_exposure', 'fx.market_history']);
        expect(AI_EXPORT_ANALYSIS_IDS).toEqual([
            'portfolio.pac_planning',
            'portfolio.rebalancing',
            'portfolio.performance_market_drivers',
            'portfolio.fiscal_lots',
            'broker.review',
            'broker.performance_market_drivers',
            'broker.fiscal_lots',
            'asset.position_review',
            'asset.market_analysis',
            'fx.pair_analysis',
            'fx.exposure_impact',
        ]);
        expect(AI_EXPORT_PUBLIC_CATALOG_CONFIG).toHaveLength(19);
        expect(AI_EXPORT_PUBLIC_CATALOG_CONFIG.map(({group, id, domain, icon}) => ({group, id, domain, icon}))).toEqual([
            {group: 'dataset', id: 'portfolio.overview_and_history', domain: 'portfolio', icon: 'layout-dashboard'},
            {group: 'dataset', id: 'portfolio.asset_history', domain: 'portfolio', icon: 'activity'},
            {group: 'dataset', id: 'broker.overview_and_history', domain: 'broker', icon: 'landmark'},
            {group: 'dataset', id: 'broker.asset_history', domain: 'broker', icon: 'activity'},
            {group: 'dataset', id: 'asset.position_and_history', domain: 'asset', icon: 'wallet'},
            {group: 'dataset', id: 'asset.market_history', domain: 'asset', icon: 'activity'},
            {group: 'dataset', id: 'fx.market_and_exposure', domain: 'fx', icon: 'arrow-left-right'},
            {group: 'dataset', id: 'fx.market_history', domain: 'fx', icon: 'activity'},
            {group: 'analysis', id: 'portfolio.pac_planning', domain: 'portfolio', icon: 'calendar-clock'},
            {group: 'analysis', id: 'portfolio.rebalancing', domain: 'portfolio', icon: 'scale'},
            {group: 'analysis', id: 'portfolio.performance_market_drivers', domain: 'portfolio', icon: 'newspaper'},
            {group: 'analysis', id: 'portfolio.fiscal_lots', domain: 'portfolio', icon: 'list-ordered'},
            {group: 'analysis', id: 'broker.review', domain: 'broker', icon: 'landmark'},
            {group: 'analysis', id: 'broker.performance_market_drivers', domain: 'broker', icon: 'newspaper'},
            {group: 'analysis', id: 'broker.fiscal_lots', domain: 'broker', icon: 'list-ordered'},
            {group: 'analysis', id: 'asset.position_review', domain: 'asset', icon: 'wallet'},
            {group: 'analysis', id: 'asset.market_analysis', domain: 'asset', icon: 'trending-up'},
            {group: 'analysis', id: 'fx.pair_analysis', domain: 'fx', icon: 'trending-up'},
            {group: 'analysis', id: 'fx.exposure_impact', domain: 'fx', icon: 'scale'},
        ]);
    });

    it('uses backend-owned V1 composition and Additional Data suggestions', () => {
        const catalog = backendCatalogFixture();
        const analysisById = new Map(catalog.analyses.map((entry) => [entry.id, entry]));

        expect(analysisById.get('portfolio.pac_planning')?.required_dataset_ids).toEqual(['portfolio.overview_and_history']);
        expect(analysisById.get('portfolio.fiscal_lots')?.required_dataset_ids).toEqual(['portfolio.overview_and_history', 'portfolio.fifo']);
        expect(analysisById.get('broker.fiscal_lots')?.required_dataset_ids).toEqual(['broker.overview_and_history', 'broker.fifo']);
        expect(analysisById.get('asset.market_analysis')?.required_dataset_ids).toEqual(['asset.market_history']);
        expect(analysisById.get('portfolio.performance_market_drivers')?.additional_export_suggestions).toEqual([
            {
                dataset_id: 'portfolio.asset_history',
                reason_i18n_key: 'aiExport.additionalData.reason.deeperTechnical',
                recommended_period: '3m',
                recommended_detail: 'standard',
                necessity: 'optional',
            },
        ]);
    });
});

describe('AI Export V1 prompt contract identities', () => {
    it('defines matching V1 instruction and response identities', () => {
        for (const analysisId of AI_EXPORT_ANALYSIS_IDS) {
            const instruction = findAiExportAnalysisInstruction(analysisId);
            const response = findAiExportResponseContract(analysisId);
            expect(instruction).toMatchObject({
                id: `${analysisId}.instructions`,
                version: 1,
                analysisId,
            });
            expect(response).toMatchObject({
                id: `${analysisId}.response`,
                version: 1,
                analysisId,
            });
        }
    });
});

describe('AI Export V1 public rendering', () => {
    it('renders FX conversion timing ratios as bounded and unbounded percentages', () => {
        const rendered = renderSnapshotDataText(
            [
                {
                    component_id: 'fx.conversion_timing_context',
                    component_version: 1,
                    schema_id: 'fx.conversion_timing_context',
                    schema_version: 1,
                    payload: {
                        observed_range: {
                            range_position_ratio: 0.42,
                            distance_to_min_ratio: 1.5,
                            distance_to_max_ratio: 0.087,
                        },
                    },
                },
            ],
            {kind: 'fx_pair', base_currency: 'USD', quote_currency: 'EUR'},
            {assets: [], brokers: [], fx_pairs: [{base_currency: 'USD', quote_currency: 'EUR'}]},
        ).content;

        expect(rendered).toContain('range_position_percent');
        expect(rendered).toContain('42%');
        expect(rendered).toContain('distance_to_min_percent');
        expect(rendered).toContain('150%');
        expect(rendered).toContain('distance_to_max_percent');
        expect(rendered).toContain('8.7%');
        expect(rendered).not.toContain('range_position_ratio');
        expect(rendered).not.toContain('distance_to_min_ratio');
        expect(rendered).not.toContain('distance_to_max_ratio');
    });

    it('renders nested cost-efficiency ratio values as public percentages preserving reason codes', () => {
        const rendered = renderSnapshotDataText(
            [
                {
                    component_id: 'broker.cost_efficiency_evidence',
                    component_version: 1,
                    schema_id: 'broker.cost_efficiency_evidence',
                    schema_version: 1,
                    payload: {
                        fees_to_turnover_ratio: {status: 'recorded', value_ratio: 0.0125, reason_code: null},
                        fees_to_invested_ratio: {status: 'unavailable', value_ratio: null, reason_code: 'denominator_unavailable'},
                    },
                },
            ],
            {kind: 'broker', broker_id: 1},
            {assets: [], brokers: [{broker_id: 1, display_name: 'Fixture Broker'}], fx_pairs: []},
        ).content;

        expect(rendered).toContain('fees_to_turnover_ratio.value_percent');
        expect(rendered).toContain('1.25%');
        expect(rendered).toContain('denominator_unavailable');
        expect(rendered).not.toContain('value_ratio');
    });

    it('does not double-convert already-scaled prefixed concentration percentages', () => {
        const rendered = renderSnapshotDataText(
            [
                {
                    component_id: 'broker.concentration_comparison',
                    component_version: 1,
                    schema_id: 'broker.concentration_comparison',
                    schema_version: 1,
                    payload: {
                        broker_largest_position_weight_percent: 15.02,
                        portfolio_largest_position_weight_percent: 11.74,
                        largest_position_weight_delta_percent: 3.28,
                        broker_share_of_portfolio_market_value_percent: 79.433,
                    },
                },
            ],
            {kind: 'broker', broker_id: 1},
            {assets: [], brokers: [{broker_id: 1, display_name: 'Fixture Broker'}], fx_pairs: []},
        ).content;

        expect(rendered).toContain('|broker_largest_position_weight_percent|15.02%|');
        expect(rendered).toContain('|portfolio_largest_position_weight_percent|11.74%|');
        expect(rendered).toContain('|largest_position_weight_delta_percent|3.28%|');
        expect(rendered).toContain('|broker_share_of_portfolio_market_value_percent|79.433%|');
        expect(rendered).not.toContain('1502%');
        expect(rendered).not.toContain('7943.3%');
    });
});
