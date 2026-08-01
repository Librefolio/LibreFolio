import {describe, expect, it} from 'vitest';

import enJson from '../../../i18n/en.json';
import esJson from '../../../i18n/es.json';
import frJson from '../../../i18n/fr.json';
import itJson from '../../../i18n/it.json';
import {AI_EXPORT_DATASET_IDS} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';
import {backendCatalogFixture} from './runtimeFixtures';

const LOCALES = {en: enJson, es: esJson, fr: frJson, it: itJson} as Record<string, Record<string, unknown>>;

const REMEDIATION_DATASET_IDS = ['portfolio.income_evidence', 'broker.concentration_evidence', 'broker.cost_efficiency_evidence', 'fx.conversion_timing_context'] as const;

function lookup(bundle: Record<string, unknown>, dottedKey: string): unknown {
    return dottedKey.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), bundle);
}

function contractText(analysisId: Parameters<typeof findAiExportResponseContract>[0]): string {
    return findAiExportResponseContract(analysisId)
        .sections.flatMap((section) => [section.title, ...section.requirements])
        .join(' ');
}

describe('AI Export adequacy remediation datasets', () => {
    it('registers the four evidence/context datasets and keeps 32 total', () => {
        expect(AI_EXPORT_DATASET_IDS).toHaveLength(32);
        for (const id of REMEDIATION_DATASET_IDS) {
            expect(AI_EXPORT_DATASET_IDS).toContain(id);
        }
    });
});

describe('AI Export adequacy remediation analysis mappings', () => {
    const catalog = backendCatalogFixture();
    const analysisById = new Map(catalog.analyses.map((entry) => [entry.id, entry]));

    it.each([
        ['portfolio.income_review', 'portfolio.income_evidence', 'required'],
        ['broker.concentration_context', 'broker.concentration_evidence', 'required'],
        ['broker.cost_efficiency', 'broker.cost_efficiency_evidence', 'required'],
        ['fx.conversion_timing', 'fx.conversion_timing_context', 'required'],
        ['portfolio.technical_breadth', 'portfolio.technical_summary', 'required'],
        ['broker.review', 'broker.concentration_evidence', 'optional'],
    ] as const)('maps %s to %s as %s', (analysisId, datasetId, role) => {
        const entry = analysisById.get(analysisId);
        expect(entry, `${analysisId} must be present`).toBeDefined();
        const bucket = role === 'required' ? entry!.required_dataset_ids : entry!.optional_dataset_ids;
        expect(bucket).toContain(datasetId);
    });

    it('keeps full technical out of technical breadth requirements and offers it as Additional Data', () => {
        const entry = analysisById.get('portfolio.technical_breadth');
        expect(entry!.required_dataset_ids).not.toContain('portfolio.technical');
        expect((entry!.additional_export_suggestions ?? []).map((suggestion) => suggestion.dataset_id)).toContain('portfolio.technical');
    });
});

describe('AI Export adequacy remediation response contracts', () => {
    it('income review requires a dated recorded income timeline without forecasts', () => {
        const text = contractText('portfolio.income_review');
        expect(text).toContain('Recorded Income Timeline');
        expect(text).toContain('conversion coverage');
        expect(text.toLowerCase()).toContain('forecast');
        expect(text).toContain('coupons');
    });

    it('broker concentration exposes dimensions, an optional comparator, and discloses unknown coverage', () => {
        const text = contractText('broker.concentration_context');
        for (const dimension of ['position', 'asset type', 'sector', 'geography', 'currency']) {
            expect(text).toContain(dimension);
        }
        expect(text).toContain('whole-portfolio comparator');
        expect(text.toLowerCase()).toContain('liquidity');
        expect(text.toLowerCase()).toContain('coverage');
    });

    it('cost efficiency keeps missing distinct from zero and gates ratios on denominators', () => {
        const text = contractText('broker.cost_efficiency');
        expect(text).toContain('share-adjusted gross traded amount');
        expect(text).toContain('recorded zero');
        expect(text).toContain('not applicable');
        expect(text).toContain('formula');
        expect(text.toLowerCase()).toContain('denominator');
    });

    it('PAC asks only material missing user inputs, grouped and typed as indispensable or optional', () => {
        const text = contractText('portfolio.pac_planning');
        for (const category of ['Capital and cadence', 'Goals and horizon', 'Risk preferences', 'Operational constraints']) {
            expect(text).toContain(category);
        }
        expect(text).toContain('REQUIRED WHEN MISSING');
        expect(text).toContain('OPTIONAL WHEN MATERIAL');
        expect(text).toContain('indispensable');
        expect(text).toContain('conditional');
        expect(text).toContain('never invent');
        expect(text).toContain('Drawdown is historical');
        expect(text).toContain('standalone reason to buy');
    });

    it('fx conversion timing uses observed range position, not percentiles, and lists missing inputs', () => {
        const text = contractText('fx.conversion_timing');
        expect(text).toContain('observed range position');
        expect(text.toLowerCase()).toContain('never as a percentile');
        expect(text).toContain('realized volatility');
        expect(text).toContain('amount, deadline, spread, and fees');
        expect(text.toLowerCase()).toContain('forecast');
    });

    it('technical breadth stays aggregate and defers raw per-asset history to Additional Data', () => {
        const text = contractText('portfolio.technical_breadth');
        expect(text).toContain('Aggregate Coverage and Event Digest');
        expect(text).toContain('raw per-asset history');
        expect(text).toContain('Additional Data');
        expect(text).not.toContain('drawdown');
        expect(text).not.toContain('VaR');
    });

    it('asset position review acknowledges the portfolio-role weight basis and keeps drawdown context', () => {
        const contract = findAiExportResponseContract('asset.position_review');
        const text = contract.sections.flatMap((section) => [section.title, ...section.requirements]).join(' ');
        expect(text).toContain('portfolio-role weight basis');
        expect(contract.sections.some((section) => section.title === 'Drawdown Context')).toBe(true);
    });
});

describe('AI Export adequacy remediation i18n', () => {
    it.each(['en', 'it', 'fr', 'es'])('has dataset labels + descriptions in %s', (locale) => {
        const bundle = LOCALES[locale];
        for (const datasetId of REMEDIATION_DATASET_IDS) {
            expect(lookup(bundle, `aiExport.dataset.${datasetId}.display`), `${locale} ${datasetId}.display`).toBeTruthy();
            expect(lookup(bundle, `aiExport.dataset.${datasetId}.description`), `${locale} ${datasetId}.description`).toBeTruthy();
        }
    });
});

describe('AI Export adequacy remediation public rendering', () => {
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
