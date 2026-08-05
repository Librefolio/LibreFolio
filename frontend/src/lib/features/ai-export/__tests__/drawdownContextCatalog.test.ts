import {describe, expect, it} from 'vitest';

import {AI_EXPORT_DATASET_IDS} from '../catalog/shared';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

describe('AI Export drawdown context catalog', () => {
    it('keeps drawdown context inside the 8 autonomous public datasets instead of exposing internal cards', () => {
        expect(AI_EXPORT_DATASET_IDS).toHaveLength(8);
        expect(AI_EXPORT_DATASET_IDS).not.toContain('portfolio.drawdown_context');
        expect(AI_EXPORT_DATASET_IDS).not.toContain('broker.drawdown_context');
        expect(AI_EXPORT_DATASET_IDS).not.toContain('asset.drawdown_context');
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
