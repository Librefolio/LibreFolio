// @vitest-environment jsdom
/**
 * HowItMoves — «How does it move?», the four green twins of «How much can it hurt?» (RN-18, Q21 c, Q22 a; Vitest + jsdom).
 *
 * The block draws the figures `moveFigures.ts` reads (pinned there) in L1's card shape: the best day, thirty good days,
 * the largest rally, and what the days were like. Pinned here, on test ids and data attributes; a translated sentence is
 * compared only with the catalogue's own text for the key:
 *
 * - four cards on the figure layout, with their detail rows (when, the average day ±, the streak, positive days,
 *   semi-deviation, below the peak on average, extreme days);
 * - the tone follows the value: the best 30 days can be a loss, and a rally of zero is a measured zero with no dates and
 *   no tone;
 * - a blank figure says why, with the backend's own warning;
 * - the money is on the value the page states (`amountOnValue`), signed, absent without a value, and masked by privacy
 *   both ways while the block stays mounted.
 */
import {afterEach, beforeAll, describe, expect, it} from 'vitest';
import {flushSync} from 'svelte';
import {get} from 'svelte/store';

import {_} from '$lib/i18n';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {formatDay, formatDayRange} from '$lib/utils/core/formatAxisDate';
import {fireEvent, render, screen, setupI18n} from '$test/component';

import type {ScopeMoveFigures} from '../moveFigures';
import HowItMoves from './HowItMoves.svelte';

const FIGURES: ScopeMoveFigures = {
    volatility: 0.139,
    bestDay: 0.034,
    bestDayDate: '2026-04-09',
    bestMonth: {gain: 0.116, from: '2026-04-22', to: '2026-05-21'},
    rally: {gain: 0.246, from: '2026-04-21', to: '2026-11-04', days: 197},
    omega: 1.25,
    positiveShare: 0.54,
    downsideDeviation: 0.098,
    meanUp: 0.007,
    meanDown: -0.006,
    streak: {days: 9, from: '2026-06-03', to: '2026-06-13'},
    averageDrawdown: -0.021,
    extremeDays: 2.4,
    reasons: {},
};

beforeAll(async () => {
    await setupI18n('en');
});

afterEach(() => setPrivacyEnabled(false));

const say = (key: string, values: Record<string, string | number> = {}) => get(_)(key, {values});
const norm = (value: string) => value.replace(/\s+/g, ' ').trim();
const text = (testId: string) => norm(screen.getByTestId(testId).textContent ?? '');

function mount(figures: ScopeMoveFigures | null = FIGURES, scopeValue: number | null = null, perimeterDiffers = true) {
    return render(HowItMoves, {props: {figures, scopeValue, currency: 'EUR', perimeterDiffers}});
}

describe('HowItMoves — four green twins', () => {
    it('draws the four cards on the figure layout, each with its own figure', () => {
        mount();

        expect(text('risk-move-card-bestDay-value')).toBe('+3.4%');
        expect(text('risk-move-card-bestMonth-value')).toBe('+11.6%');
        expect(text('risk-move-card-rally-value')).toBe('+24.6%');
        expect(text('risk-move-card-days-value')).toBe('1.25×');
        for (const card of ['bestDay', 'bestMonth', 'rally', 'days']) expect(screen.getByTestId(`risk-move-card-${card}`)).toHaveAttribute('data-sentiment', card === 'days' ? 'neutral' : 'positive');
    });

    it('says which day and which stretch, and what the days were like', () => {
        mount();

        expect(text('risk-move-best-day-date-value')).toBe(norm(formatDay('2026-04-09')));
        expect(text('risk-move-mean-up-down-value')).toBe(say('risk.levels.move.rows.meanUpDownValue', {up: '+0.7%', down: '−0.6%'}));
        expect(screen.getByTestId('risk-move-best-month-period')).toHaveAttribute('data-from', '2026-04-22');
        expect(text('risk-move-best-month-period-value')).toBe(norm(formatDayRange('2026-04-22', '2026-05-21')));
        expect(text('risk-move-rally-period-value')).toBe(norm(formatDayRange('2026-04-21', '2026-11-04')));
        expect(text('risk-move-rally-duration-value')).toBe(say('risk.levels.l1.daysCount', {days: 197}));
        expect(text('risk-move-streak-value')).toContain(norm(formatDayRange('2026-06-03', '2026-06-13')));
        expect(text('risk-move-card-days-caption')).toBe(say('risk.levels.move.omegaCaption', {value: '1.25'}));
        expect(text('risk-move-positive-share-value')).toBe('54.0%');
        // Q23 a, the consultant (17/11): the semi-deviation beside the swing it is compared with, from the same series.
        expect(text('risk-move-semi-deviation-value')).toBe(say('risk.levels.move.rows.semiDeviationValue', {down: '9.8%', swing: '13.9%'}));
        expect(text('risk-move-average-drawdown-value')).toBe('−2.1%');
        expect(text('risk-move-extreme-days-value')).toBe(say('risk.levels.move.rows.extremeDaysValue', {value: '2.4'}));
    });

    it('takes the tone from the value: a best 30 days that lost is a loss, a rally of zero is a zero with no dates', () => {
        mount({...FIGURES, bestMonth: {gain: -0.021, from: '2026-04-22', to: '2026-05-21'}, rally: {gain: 0, from: null, to: null, days: 0}});

        expect(text('risk-move-card-bestMonth-value')).toBe('−2.1%');
        expect(screen.getByTestId('risk-move-card-bestMonth')).toHaveAttribute('data-sentiment', 'negative');
        expect(text('risk-move-card-rally-value')).toBe('0.0%');
        expect(screen.getByTestId('risk-move-card-rally')).toHaveAttribute('data-sentiment', 'neutral');
        expect(screen.queryByTestId('risk-move-rally-period'), 'a rally of zero has no stretch').toBeNull();
    });

    it('says why a figure is blank, with the backend’s own warning', () => {
        mount({
            ...FIGURES,
            omega: null,
            bestDay: null,
            bestDayDate: null,
            meanUp: null,
            reasons: {omega: 'risk.warnings.omega_undefined', bestDay: 'risk.warnings.best_realization_undefined', meanUp: 'risk.warnings.best_realization_undefined'},
        });

        expect(text('risk-move-card-days-value')).toBe('—');
        expect(text('risk-move-card-days-caption')).toBe(say('risk.warnings.omega_undefined'));
        expect(text('risk-move-card-bestDay-value')).toBe('—');
        expect(text('risk-move-card-bestDay-caption')).toBe(say('risk.warnings.best_realization_undefined'));
        expect(screen.queryByTestId('risk-move-best-day-date')).toBeNull();
    });

    // Q20: every blank says why, rows too — the lab's table does it for each cell (RN-19). On a card the reason is a line
    // under the row, readable on a phone where a tooltip is not.
    it('keeps a blank row with its dash and says why: the average down day, the streak, the extreme days', () => {
        mount({
            ...FIGURES,
            meanDown: null,
            streak: null,
            extremeDays: null,
            reasons: {meanDown: 'risk.warnings.average_loss_undefined', streak: 'risk.warnings.best_realization_undefined', extremeDays: 'risk.warnings.extreme_day_ratio_undefined'},
        });

        expect(text('risk-move-mean-up-down-value')).toBe(say('risk.levels.move.rows.meanUpDownValue', {up: '+0.7%', down: '\u2014'}));
        expect(text('risk-move-mean-up-down-reason')).toBe(say('risk.warnings.average_loss_undefined'));
        expect(text('risk-move-streak-value')).toBe('\u2014');
        expect(text('risk-move-streak-reason')).toBe(say('risk.warnings.best_realization_undefined'));
        expect(text('risk-move-extreme-days-value')).toBe('\u2014');
        expect(text('risk-move-extreme-days-reason')).toBe(say('risk.warnings.extreme_day_ratio_undefined'));
    });

    it('draws no reason line under a row that has its figure', () => {
        mount();

        for (const row of ['risk-move-mean-up-down', 'risk-move-streak', 'risk-move-extreme-days']) expect(screen.queryByTestId(`${row}-reason`), row).toBeNull();
    });

    it('writes the semi-deviation alone when the swing it is compared with is missing', () => {
        mount({...FIGURES, volatility: null});

        expect(text('risk-move-semi-deviation-value')).toBe('9.8%');
    });

    it('says the block is unavailable when nothing answered', () => {
        mount(null);

        expect(screen.getByTestId('risk-move-empty')).toBeInTheDocument();
        expect(screen.queryByTestId('risk-move-cards')).toBeNull();
    });
});

describe('HowItMoves — the money on the value the page states', () => {
    it('signs each amount, says the rally is the same rise on today’s value, and writes none for the days', () => {
        mount(FIGURES, 10_000);

        expect(text('risk-move-card-bestDay-caption')).toBe('+€340.00');
        expect(text('risk-move-card-bestMonth-caption')).toBe('+€1,160.00');
        expect(text('risk-move-card-rally-caption')).toBe(say('risk.levels.move.sameRiseToday', {amount: '+€2,460.00'}));
        expect(text('risk-move-card-days-caption')).toBe(say('risk.levels.move.omegaCaption', {value: '1.25'}));
    });

    it('writes no amount without a value: not owned, or not valued', () => {
        mount(FIGURES, null);

        expect(text('risk-move-card-bestDay-caption')).toBe('');
        expect(text('risk-move-card-rally-caption')).toBe('');
    });

    it('masks the amounts with privacy, and shows them again when it is turned off, without remounting', () => {
        mount(FIGURES, 10_000);

        setPrivacyEnabled(true);
        flushSync();
        expect(text('risk-move-card-bestDay-caption')).toBe(`+€${PRIVACY_PLACEHOLDER}`);
        setPrivacyEnabled(false);
        flushSync();
        expect(text('risk-move-card-bestDay-caption')).toBe('+€340.00');
    });
});

// RN-18b (the developer's «C, ovunque»; the consultant's texts, 17/11/2026): every figure says its perimeter. On a
// portfolio the swing beside the semi-deviation is the period's, and L3's table is on today's holdings, so their
// volatilities can differ: the row's tooltip says so. On one asset the two are the same series: the usual help.
describe('HowItMoves — the semi-deviation says its perimeter', () => {
    async function tooltipOf(row: string): Promise<string> {
        await fireEvent.click(screen.getByTestId(`${row}-help`));
        return norm(screen.getByTestId('tooltip-content').textContent ?? '');
    }

    it('when L3 measures today’s holdings and the block the period, says so', async () => {
        mount(FIGURES, null, true);

        expect(text('risk-move-semi-deviation-value')).toBe(say('risk.levels.move.rows.semiDeviationValue', {down: '9.8%', swing: '13.9%'}));
        expect(await tooltipOf('risk-move-semi-deviation')).toBe(norm(say('risk.levels.move.rows.semiDeviationPerimeter')));
    });

    it('when both read one series (one asset, a backtest, L3 on the history), keeps the usual help', async () => {
        mount(FIGURES, null, false);

        expect(await tooltipOf('risk-move-semi-deviation')).toBe(norm(say('risk.assetSet.levels.move.columnHelp.downsideDeviation')));
    });
});
