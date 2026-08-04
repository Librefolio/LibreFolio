import {describe, expect, it} from 'vitest';

import {AI_EXPORT_ANALYSIS_IDS, AI_EXPORT_DATASET_IDS, AI_EXPORT_PUBLIC_CATALOG_CONFIG} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';
import {AI_EXPORT_SCENARIO_THESIS_RULE, findAiExportAnalysisInstruction} from '../templates/sharedInstructions';
import {backendCatalogFixture} from './runtimeFixtures';

function contractText(analysisId: Parameters<typeof findAiExportResponseContract>[0]): string {
    return findAiExportResponseContract(analysisId)
        .sections.flatMap((section) => [section.title, ...section.requirements])
        .join(' ');
}

function instructionText(analysisId: Parameters<typeof findAiExportAnalysisInstruction>[0]): string {
    const instruction = findAiExportAnalysisInstruction(analysisId);
    return [instruction.objective, ...instruction.steps].join(' ');
}

describe('AI Export V3 public catalog', () => {
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

    it('uses backend-owned V3 composition and Additional Data suggestions', () => {
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

describe('AI Export V3 prompt contracts', () => {
    it('defines canonical V3 objective and response identities for all 11 analyses', () => {
        for (const analysisId of AI_EXPORT_ANALYSIS_IDS) {
            const instruction = findAiExportAnalysisInstruction(analysisId);
            const response = findAiExportResponseContract(analysisId);
            expect(instruction).toMatchObject({
                id: `${analysisId}.instructions`,
                version: 3,
                analysisId,
            });
            expect(instruction.objective.length).toBeGreaterThan(40);
            expect(instruction.steps.length).toBeGreaterThan(2);
            expect(response).toMatchObject({
                id: `${analysisId}.response`,
                version: 3,
                analysisId,
            });
            expect(response.sections.length).toBeGreaterThan(3);
        }
    });

    it('shares one conditional Scenario Thesis rule and makes it mandatory for approved tasks', () => {
        expect(AI_EXPORT_SCENARIO_THESIS_RULE).toContain('horizon');
        expect(AI_EXPORT_SCENARIO_THESIS_RULE).toContain('trigger conditions');
        expect(AI_EXPORT_SCENARIO_THESIS_RULE).toContain('invalidation conditions');
        expect(AI_EXPORT_SCENARIO_THESIS_RULE).toContain('conditional');

        const mandatory = ['portfolio.pac_planning', 'portfolio.rebalancing', 'portfolio.fiscal_lots', 'broker.fiscal_lots'] as const;
        for (const analysisId of mandatory) {
            const scenario = findAiExportResponseContract(analysisId).sections.find((entry) => entry.title === 'Scenario Thesis');
            expect(scenario, `${analysisId} requires Scenario Thesis`).toBeDefined();
            expect(scenario!.requirements.join(' ')).toContain('mandatory');
        }
    });

    it('enforces the PAC immediate/staged/conditional-waiting gate and user timing preference', () => {
        const text = `${instructionText('portfolio.pac_planning')} ${contractText('portfolio.pac_planning')}`;
        expect(text).toContain('immediate');
        expect(text).toContain('staged');
        expect(text).toContain('conditional waiting');
        expect(text).toContain('broad, persistent decline');
        expect(text).toContain('isolated Asset weakness');
        expect(text).toContain('single indicator');
        expect(text).toContain('Ask the user');
        expect(text).toContain('timing preference');
    });

    it.each(['portfolio.performance_market_drivers', 'broker.performance_market_drivers'] as const)('requires dated research, per-Asset short/long theses, source quality, and qualified causality for %s', (analysisId) => {
        const text = `${instructionText(analysisId)} ${contractText(analysisId)}`;
        for (const required of ['every held Asset', 'short-horizon thesis', 'long-horizon thesis', 'publisher', 'URL', 'publication date', 'access date', 'source quality', 'chronology', 'correlation', 'causality']) {
            expect(text).toContain(required);
        }
        for (const confidence of ['supported', 'plausible', 'inferred', 'speculative', 'unexplained']) {
            expect(text).toContain(confidence);
        }
        expect(text).toContain('primary issuer');
        expect(text).toContain('lower-quality secondary');
        expect(text).toContain('never proves causation');
    });

    it.each(['portfolio.fiscal_lots', 'broker.fiscal_lots'] as const)('centers tax-loss offsets, official inventory, expiries, and conditional strategies for %s', (analysisId) => {
        const text = `${instructionText(analysisId)} ${contractText(analysisId)}`.toLowerCase();
        for (const required of [
            'tax-loss carryforwards',
            'country of tax residence',
            'jurisdiction',
            'tax regime',
            'cassetto fiscale',
            'original amount',
            'remaining usable amount',
            'already used or reserved',
            'origin date',
            'expiry date',
            'eligible gain categories',
            'multiple brokers',
            'legally be pooled or transferred',
            'expected or planned realizable gains',
            'taking no tax-driven action',
            'realizing legally eligible gains before expiry',
            'staged realization',
            'loss harvesting',
            'never recommend a trade solely for tax reasons',
        ]) {
            expect(text).toContain(required);
        }
        expect(text).toContain('do not state a definitive tax liability');
        expect(text).toContain('scenario thesis');
    });

    it('keeps remaining analyses aligned with their approved scope', () => {
        const expectations = {
            'broker.review': ['selected broker scope', 'whole portfolio', 'economic FIFO'],
            'asset.position_review': ['broker distribution', 'portfolio-role weight basis', 'focused market context'],
            'asset.market_analysis': ['OHLC', 'drawdown', 'dated state transitions'],
            'fx.pair_analysis': ['quote currency per one unit of base currency', 'Never invert the pair silently'],
            'fx.exposure_impact': ['cash, trading-currency, and valuation-currency links', 'No Look-Through Inference'],
        } as const;

        for (const [analysisId, fragments] of Object.entries(expectations) as [keyof typeof expectations, readonly string[]][]) {
            const text = `${instructionText(analysisId)} ${contractText(analysisId)}`;
            for (const fragment of fragments) expect(text).toContain(fragment);
        }
    });
});

describe('AI Export V3 public rendering', () => {
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
