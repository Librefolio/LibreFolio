/**
 * The risk evidence of today's holdings (78 L8a): `portfolio.risk_concentration` and `portfolio.tail_risk` are version 1
 * components, so they take the generic compact renderer. What this file pins:
 * - every ratio is a percentage under a public name that says what it is («loss» for a loss written as a positive number,
 *   «return» for the worst window, which keeps its sign);
 * - a holding's share of risk and an annualized volatility can pass 100% and are not clipped;
 * - holdings are A# refs, never database ids: in the rows, in the holdings that shortened the window and in those left out;
 * - the internal dataset is not one of the public Export Data choices.
 */
import {describe, expect, it} from 'vitest';

import {AI_EXPORT_DATASET_IDS} from '../catalog/shared';
import {renderSnapshotDataText} from '../templates/snapshotDataRenderer';

const WINDOW = {
    status: 'ok',
    mode: 'current_composition',
    composition_as_of: '2026-11-23',
    requested_start: '2025-11-23',
    requested_end: '2026-11-23',
    analyzed_start: '2026-02-02',
    analyzed_end: '2026-11-23',
    n_observations: 210,
    coverage_ratio: 0.98,
    calculation_currency: 'EUR',
    window_semantics: 'Measured on today’s holdings over the analyzed window.',
    weight_basis: 'Shares of the net worth of the exported scope.',
    warning_codes: ['short_history'],
    window_shortened_by: [{asset_id: 9002}],
    excluded_assets: [{asset_id: 9017, reason: 'no_price_source'}],
};

function sections() {
    return [
        {
            component_id: 'portfolio.risk_concentration',
            component_version: 1,
            schema_id: 'portfolio.risk_concentration',
            schema_version: 1,
            payload: {
                ...WINDOW,
                portfolio_volatility_ratio: 1.25,
                effective_number_of_assets: 2.6,
                diversification_multiple: 1.3,
                cash_weight_ratio: 0.4,
                excluded_weight_ratio: 0.05,
                rows: [
                    {asset_id: 9001, weight_ratio: 0.3, risk_share_ratio: 1.12},
                    {asset_id: 9002, weight_ratio: 0.15, risk_share_ratio: -0.12},
                ],
            },
        },
        {
            component_id: 'portfolio.tail_risk',
            component_version: 1,
            schema_id: 'portfolio.tail_risk',
            schema_version: 1,
            payload: {
                ...WINDOW,
                confidence_level: 0.95,
                horizon_days: 30,
                horizon_observations: 21,
                overlapping_windows: 190,
                value_at_risk_loss_ratio: 0.07,
                expected_shortfall_loss_ratio: 0.09,
                worst_window_return_ratio: -0.12,
                worst_window_start: '2026-03-02',
                worst_window_end: '2026-03-30',
                bad_month_semantics: 'Overlapping 30-day windows.',
            },
        },
    ];
}

function render(): string {
    return renderSnapshotDataText(sections(), {kind: 'portfolio', broker_scope: []}).content;
}

describe('AI Export risk evidence rendering (78 L8a)', () => {
    it('keeps portfolio.risk_evidence out of the public Export Data choices', () => {
        expect(AI_EXPORT_DATASET_IDS).not.toContain('portfolio.risk_evidence');
    });

    it('prints the bad month as named losses and a signed worst-window return', () => {
        const rendered = render();
        expect(rendered).toContain('|value_at_risk_loss_percent|7%|');
        expect(rendered).toContain('|expected_shortfall_loss_percent|9%|');
        expect(rendered).toContain('|worst_window_return_percent|-12%|');
        expect(rendered).toContain('|confidence_level|0.95|');
        expect(rendered).toContain('|overlapping_windows|190|');
    });

    it('prints weights, cash and exclusions as percentages, and neither clips nor rescales a share of risk or a volatility', () => {
        const rendered = render();
        expect(rendered).toContain('|portfolio_volatility_annualized_percent|125%|');
        expect(rendered).toContain('|cash_weight_percent|40%|');
        expect(rendered).toContain('|excluded_weight_percent|5%|');
        expect(rendered).toContain('|coverage_percent|98%|');
        expect(rendered).toContain('|diversification_multiple|1.3|');
        expect(rendered).toContain('112%');
        expect(rendered).toContain('-12%');
        expect(rendered).toContain('weight_percent');
        expect(rendered).toContain('risk_share_percent');
        expect(rendered).not.toMatch(/_ratio\b/);
    });

    it('names every holding by its A# ref and never by its database id', () => {
        const rendered = render();
        for (const id of ['9001', '9002', '9017']) expect(rendered).not.toContain(id);
        expect(rendered).not.toContain('asset_unmapped');
        expect(rendered).toMatch(/\bA1\b/);
        expect(rendered).toMatch(/\bA3\b/);
    });
});
