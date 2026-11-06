// @vitest-environment jsdom
/**
 * L1HowMuchItHurts — one shape for every loss card (F-6, F8; Vitest + jsdom).
 *
 * Developer's decision of 06/11/2026: the four cards («a bad day», «thirty bad days», «the worst fall», «below the peak, today») have
 * the same shape — a short title, a subtitle that says what the parentheses of the title used to say, the number with its amount, a
 * rule, and detail rows that are always a label on the left and a value on the right — and they say which day, which stretch, which
 * fall it was. The figures are the backend's and do not change; this file pins the presentation.
 *
 * Pinned, on test ids and data attributes, never on translated text:
 *
 * - all four cards use the figure layout, and every detail is a row with a label and a value (`<id>-value`);
 * - the dates are written the way the language writes them, not as ISO (`formatDay`, `formatDayRange`), while the ISO dates stay in
 *   `data-from` / `data-to` for a test to read;
 * - each card says which one it was: the day its worst day and when, the month its worst 30 days and their stretch, the worst fall its
 *   stretch, how long it lasted, what recovers it, and the two tail measures;
 * - a detail the payload does not carry is absent, never an empty row;
 * - the worst fall's subtitle is built from the glossary's own name for the measure.
 */
import {beforeAll, describe, expect, it} from 'vitest';
import {get} from 'svelte/store';

import {_} from '$lib/i18n';
import type {RiskAnalyticResult} from '$lib/features/risk/riskStore.svelte';
import {formatDay, formatDayRange} from '$lib/utils/core/formatAxisDate';
import {render, screen, setupI18n, within} from '$test/component';

import {DAILY_VAR_INSTANCE, MONTHLY_VAR_INSTANCE} from '../riskAnalysisHelpers';
import L1HowMuchItHurts from './L1HowMuchItHurts.svelte';

function ok(analyticCode: string, output: Record<string, unknown>, instanceId = `base-historical-${analyticCode}`): RiskAnalyticResult {
    return {analytic_code: analyticCode, instance_id: instanceId, status: 'ok', output} as unknown as RiskAnalyticResult;
}

const VAR_BASE = {kind: 'var_cvar', confidence_level: 0.95, horizon_observations: 1, observations: 60, value_at_risk: 0.021, conditional_value_at_risk: 0.031};

const RESULTS: RiskAnalyticResult[] = [
    ok('historical_var', {...VAR_BASE, horizon_days: 1}, DAILY_VAR_INSTANCE),
    ok('historical_var', {...VAR_BASE, horizon_days: 30, conditional_value_at_risk: 0.094, worst_horizon: {compounded_return: -0.121, start_date: '2023-11-14', end_date: '2023-12-14'}}, MONTHLY_VAR_INSTANCE),
    ok('historical_kpi', {worst_realization: -0.038, worst_realization_date: '2023-11-21', drawdown_confidence_level: 0.95, drawdown_at_risk: -0.04, conditional_drawdown_at_risk: -0.06}),
    ok('drawdown_summary', {
        maximum_drawdown: -0.087,
        maximum_drawdown_peak_date: '2023-11-14',
        maximum_drawdown_trough_date: '2023-12-03',
        maximum_drawdown_duration_days: 19,
        maximum_drawdown_trough_to_peak_ratio: 0.087 / 0.913,
        current_drawdown: -0.032,
        current_peak_date: '2024-02-05',
        remaining_to_peak_ratio: 0.033,
    }),
];

beforeAll(async () => {
    await setupI18n('en');
});

const say = (key: string, values: Record<string, string | number> = {}) => get(_)(key, {values});

function mount(results: RiskAnalyticResult[] = RESULTS) {
    return render(L1HowMuchItHurts, {props: {historicalResults: results, currency: 'EUR'}});
}

const value = (id: string) => screen.getByTestId(`${id}-value`).textContent ?? '';

describe('L1HowMuchItHurts — one shape for every loss card', () => {
    it('draws the four cards on the figure layout: the number and its amount on one line, the detail rows under a rule', () => {
        mount();

        for (const card of ['day', 'month', 'worst', 'current']) {
            const root = screen.getByTestId(`risk-l1-card-${card}`);
            expect(within(root).getByTestId(`risk-l1-card-${card}-details`), `${card} has no detail rows under a rule`).toBeInTheDocument();
            expect(within(root).getByTestId(`risk-l1-card-${card}-value`).parentElement).toBe(within(root).getByTestId(`risk-l1-card-${card}-caption`).parentElement);
        }
    });

    it('gives every detail the same shape: a label and a value', () => {
        mount();

        const details = screen.getByTestId('risk-l1-cards').querySelectorAll('[data-testid^="risk-l1-"][data-testid$="-value"]');
        // The cards' own values aside, each detail row carries its value under `<id>-value`.
        for (const id of [
            'risk-l1-worst-realization',
            'risk-l1-worst-realization-date',
            'risk-l1-worst-month',
            'risk-l1-period-month',
            'risk-l1-period-worst',
            'risk-l1-duration-worst',
            'risk-l1-recovery-worst',
            'risk-l1-drawdown-at-risk',
            'risk-l1-conditional-drawdown-at-risk',
            'risk-l1-current-since',
            'risk-l1-current-recovery',
        ]) {
            expect(screen.getByTestId(id), id).toBeInTheDocument();
            expect(screen.getByTestId(`${id}-value`).textContent?.trim(), `${id} has no value`).not.toBe('');
        }
        expect(details.length).toBeGreaterThan(8);
    });

    it('writes the dates as the language writes them, and keeps the ISO days for a test', () => {
        mount();

        expect(value('risk-l1-worst-realization-date')).toBe(formatDay('2023-11-21'));
        expect(value('risk-l1-period-month')).toBe(formatDayRange('2023-11-14', '2023-12-14'));
        expect(value('risk-l1-period-worst')).toBe(formatDayRange('2023-11-14', '2023-12-03'));
        expect(value('risk-l1-current-since')).toBe(formatDay('2024-02-05'));
        expect(screen.getByTestId('risk-l1-period-month').getAttribute('data-from')).toBe('2023-11-14');
        expect(screen.getByTestId('risk-l1-period-month').getAttribute('data-to')).toBe('2023-12-14');
        expect(screen.getByTestId('risk-l1-period-worst').getAttribute('data-to')).toBe('2023-12-03');
        // No ISO date in any value: «2023-11-21» is a data format, not a way to write a day.
        for (const id of ['risk-l1-worst-realization-date', 'risk-l1-period-month', 'risk-l1-period-worst', 'risk-l1-current-since']) expect(value(id)).not.toMatch(/\d{4}-\d{2}-\d{2}/);
    });

    it('says how long the fall lasted as a number of days', () => {
        mount();

        expect(value('risk-l1-duration-worst')).toBe(say('risk.levels.l1.daysCount', {days: 19}));
    });

    it('has no row for what the payload does not carry, and no row for the day’s period (the day has its date)', () => {
        mount([RESULTS[0], ok('historical_var', {...VAR_BASE, horizon_days: 30}, MONTHLY_VAR_INSTANCE), RESULTS[3]]);

        expect(screen.queryByTestId('risk-l1-worst-month')).toBeNull();
        expect(screen.queryByTestId('risk-l1-period-month')).toBeNull();
        expect(screen.queryByTestId('risk-l1-worst-realization')).toBeNull();
        expect(screen.queryByTestId('risk-l1-period-day')).toBeNull();
        expect(screen.getByTestId('risk-l1-period-worst')).toBeInTheDocument();
    });

    it('builds the worst fall’s subtitle from «lived through» and the glossary’s own name for the measure', () => {
        mount();

        const subtitle = screen.getByTestId('risk-l1-card-worst-technical').textContent ?? '';
        expect(subtitle).toContain(say('risk.levels.l1.technical.lived'));
        expect(subtitle).toContain(say('risk.levels.l1.technical.worst'));
        expect(screen.getByTestId('risk-l1-card-day-technical').textContent).toBe(say('risk.levels.l1.technical.day'));
    });
});
