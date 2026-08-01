import {describe, expect, it} from 'vitest';

import enJson from '../../../i18n/en.json';
import esJson from '../../../i18n/es.json';
import frJson from '../../../i18n/fr.json';
import itJson from '../../../i18n/it.json';
import {AI_EXPORT_DATASET_IDS} from '../catalog/shared';
import {findAiExportResponseContract} from '../templates/responseContracts';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

const LOCALES = {en: enJson, es: esJson, fr: frJson, it: itJson} as Record<string, Record<string, unknown>>;
const DRAWDOWN_DATASET_IDS = ['portfolio.drawdown_context', 'broker.drawdown_context', 'asset.drawdown_context'] as const;

function lookup(bundle: Record<string, unknown>, dottedKey: string): unknown {
    return dottedKey.split('.').reduce<unknown>((node, part) => (node && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), bundle);
}

describe('AI Export drawdown context catalog', () => {
    it('registers the three drawdown context datasets and keeps 32 total', () => {
        expect(AI_EXPORT_DATASET_IDS).toHaveLength(32);
        for (const id of DRAWDOWN_DATASET_IDS) {
            expect(AI_EXPORT_DATASET_IDS).toContain(id);
        }
        // The deferred FX drawdown dataset and asset.drawdown_recovery stay absent.
        expect(AI_EXPORT_DATASET_IDS).not.toContain('fx.drawdown_context');
        expect(AI_EXPORT_DATASET_IDS).not.toContain('asset.drawdown_recovery');
    });
});

describe('AI Export drawdown response contracts', () => {
    it.each(['portfolio.pac_planning', 'portfolio.rebalancing', 'broker.review', 'asset.position_review'] as const)('adds a deterministic drawdown context section to %s', (analysisId) => {
        const contract = findAiExportResponseContract(analysisId);
        const drawdown = contract.sections.find((section) => section.title === 'Drawdown Context');
        expect(drawdown, `${analysisId} must expose a Drawdown Context section`).toBeDefined();
        const text = drawdown!.requirements.join(' ');
        expect(text).toContain('calculation basis');
        expect(text).toContain('data-quality status');
        expect(text).toContain('coverage');
        expect(text.toLowerCase()).toContain('never infer');
        expect(text).toContain('Risk metric');
    });

    it.each(['portfolio.technical_breadth', 'fx.trend_review', 'asset.trend_analysis'] as const)('does not add a drawdown section to unrelated analysis %s', (analysisId) => {
        const contract = findAiExportResponseContract(analysisId);
        expect(contract.sections.some((section) => section.title === 'Drawdown Context')).toBe(false);
    });
});

describe('AI Export drawdown i18n', () => {
    it.each(['en', 'it', 'fr', 'es'])('has dataset labels + risk analytic labels in %s', (locale) => {
        const bundle = LOCALES[locale];
        for (const datasetId of DRAWDOWN_DATASET_IDS) {
            expect(lookup(bundle, `aiExport.dataset.${datasetId}.display`), `${locale} ${datasetId}.display`).toBeTruthy();
            expect(lookup(bundle, `aiExport.dataset.${datasetId}.description`), `${locale} ${datasetId}.description`).toBeTruthy();
        }
        expect(lookup(bundle, 'risk.analytics.drawdownSummary.name'), `${locale} drawdownSummary.name`).toBeTruthy();
        expect(lookup(bundle, 'risk.analytics.drawdownSummary.description'), `${locale} drawdownSummary.description`).toBeTruthy();
    });
});

describe('AI Export drawdown public rendering', () => {
    it('renders drawdown ratios as signed or bounded percentages', () => {
        const rendered = renderSnapshotDataText(
            [
                {
                    component_id: 'portfolio.drawdown_summary',
                    component_version: 1,
                    schema_id: 'portfolio.drawdown_summary',
                    schema_version: 1,
                    payload: {
                        status: 'ok',
                        calculation_basis: 'historical_twrr',
                        return_basis: 'twrr',
                        calculation_currency: 'EUR',
                        data_quality_status: 'ok',
                        current_drawdown_ratio: -0.08,
                        current_peak_date: '2024-10-01',
                        current_drawdown_duration_days: 30,
                        maximum_drawdown_ratio: -0.2,
                        maximum_drawdown_peak_date: '2024-03-01',
                        maximum_drawdown_trough_date: '2024-05-01',
                        maximum_drawdown_recovery_status: 'recovered',
                        maximum_drawdown_recovery_date: '2024-07-01',
                        maximum_drawdown_duration_days: 120,
                        maximum_drawdown_recovered_ratio: 1,
                        remaining_to_peak_ratio: 0.087,
                        available_start: '2024-01-01',
                        available_end: '2024-12-31',
                        n_observations: 250,
                        coverage_ratio: 0.95,
                    },
                },
            ],
            {kind: 'portfolio', broker_scope: []},
        ).content;

        expect(rendered).toContain('|current_drawdown_percent|-8%|');
        expect(rendered).toContain('|maximum_drawdown_percent|-20%|');
        expect(rendered).toContain('|maximum_drawdown_recovered_percent|100%|');
        expect(rendered).toContain('|remaining_to_peak_percent|8.7%|');
        expect(rendered).toContain('|coverage_percent|95%|');
        expect(rendered).not.toContain('drawdown_ratio');
    });
});
