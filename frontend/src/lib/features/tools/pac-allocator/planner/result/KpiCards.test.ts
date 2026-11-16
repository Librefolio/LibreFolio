// @vitest-environment jsdom
/**
 * The Rebalancer's key figures (F4a of project 67, step 4; contract §6.1, X14): «Worth today», «Worth after», «Money
 * lost» with its entries, «Largest gap from target» after and before, «Uninvested», «Orders».
 *
 * Every figure is a published field. The test proves it on a variant built here from the engine's G5 answer
 * (`rebalancer-browser.json`, the file untouched): today's value, the value after, the money lost and its entries, the two
 * deviations and the uninvested are set so that none can be rebuilt from the others. The entries do not add up to the
 * total, the value after is not today's less the loss, and no row's gap is the largest deviation. A tile that showed a sum,
 * a difference or a maximum would differ from its field. The variant is passed to the component as it is, never through
 * the codec, which would refuse it.
 *
 * Also: on the T5 answer (nothing to do) all six tiles are there, with their zeros; money is masked in privacy mode and
 * unmasked again, while points and counts stay public. Figures are compared with the planner's own formatters; no
 * translated sentence is read.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {catalogCurrencyDigits, formatExactMoneyPlain, formatExactPercent, formatExactPoints} from '../format';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerReadyResult} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import t5 from './__fixtures__/rebalancer-t5.json';
import KpiCards from './KpiCards.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const P = 'rebalancer-planner';
const METRICS = {
    queue_wait_ms: 1,
    startup_ms: 240,
    input_validation_ms: 2,
    compute_ms: 51,
    output_validation_ms: 0,
    serialization_ms: 1,
    execution_ms: 850,
    cleanup_ms: 70,
    total_ms: 920,
    resources: {memory: {mode: 'process_tree_observed', limit_bytes: 1073741824, peak_observed_bytes: 90406912}},
    worker_exit_code: null,
};

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
const money = (value: string) => ({value: {kind: 'finite_decimal', value}, currency: 'EUR'});
const share = (value: string) => ({kind: 'finite_decimal', value});

/** The G5 answer with every key figure set apart from the others (module docstring). */
function unrelated(): Json {
    const result = structuredClone(browser.result) as Json;
    const solution = result.primary_solution;
    solution.plan_accounts.initial_wealth = money('1000');
    solution.plan_accounts.final_wealth = money('900');
    solution.plan_accounts.uninvested = money('42');
    for (const key of Object.keys(solution.plan_accounts.money_lost)) solution.plan_accounts.money_lost[key] = money('0');
    solution.plan_accounts.money_lost.buy_fees = money('7');
    solution.plan_accounts.money_lost.rounding = money('0.5');
    solution.score.wealth_loss = money('3');
    solution.score.largest_deviation_before = share('0.4321');
    solution.score.largest_deviation_after = share('0.0123');
    solution.uninvested_row.final_weight = share('0.0042');
    solution.accounting.current_invested = money('600');
    solution.accounting.selected_funding = money('350');
    return result;
}

function mounted(result: Json): Json {
    const solution = result.primary_solution;
    render(ProfileHarness, {
        props: {
            profile: REBALANCER_PLANNER_PROFILE,
            child: KpiCards,
            childProps: {solution, result: result as unknown as PlannerReadyResult, metrics: METRICS, digits: catalogCurrencyDigits(result.catalogs.currencies)},
        },
    });
    flushSync();
    return solution;
}

const tile = (kpi: string) => document.querySelector(`[data-testid="${P}-kpi-item"][data-kpi="${kpi}"]`) as HTMLElement | null;
const value = (kpi: string) => tile(kpi)?.querySelector(`[data-testid="${P}-kpi-value"]`)?.textContent?.trim() ?? null;
const chip = (kpi: string, id: string) => tile(kpi)?.querySelector(`[data-testid="${P}-kpi-chip"][data-chip="${id}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? null;
const KPIS = ['value_today', 'value_after', 'money_lost', 'largest_deviation', 'uninvested', 'orders'];

describe('the Rebalancer key figures', () => {
    it('key figures read published fields, largest deviation included', () => {
        const solution = mounted(unrelated());
        expect([...document.querySelectorAll(`[data-testid="${P}-kpi-item"]`)].map((item) => item.getAttribute('data-kpi'))).toEqual(KPIS);
        expect(value('value_today')).toBe(formatExactMoneyPlain(solution.plan_accounts.initial_wealth));
        expect(chip('value_today', 'assets')).toContain(formatExactMoneyPlain(solution.accounting.current_invested));
        expect(chip('value_today', 'cash')).toContain(formatExactMoneyPlain(solution.accounting.selected_funding));
        expect(value('value_after')).toBe(formatExactMoneyPlain(solution.plan_accounts.final_wealth));
        // The total is the score's F − W, not the sum of the entries (7 + 0.5).
        expect(value('money_lost')).toBe(formatExactMoneyPlain(solution.score.wealth_loss));
        expect(chip('money_lost', 'buy_fees')).toContain(formatExactMoneyPlain(solution.plan_accounts.money_lost.buy_fees));
        expect(chip('money_lost', 'rounding')).toContain(formatExactMoneyPlain(solution.plan_accounts.money_lost.rounding));
        expect(chip('money_lost', 'sell_fees')).toBeNull();
        // The deviation is the score's, after the plan as the value, before it as an entry.
        expect(value('largest_deviation')).toContain(formatExactPoints(solution.score.largest_deviation_after));
        expect(chip('largest_deviation', 'before')).toContain(formatExactPoints(solution.score.largest_deviation_before));
        expect(value('uninvested')).toBe(formatExactMoneyPlain(solution.plan_accounts.uninvested));
        expect(chip('uninvested', 'share')).toContain(formatExactPercent(solution.uninvested_row.final_weight));
        expect(value('orders')).toBe(String(solution.order_rows.length));
        expect(chip('orders', 'transfers')).toContain(String(solution.transfers.length));
    });

    it('a plan with nothing to do still shows every figure', () => {
        const solution = mounted(structuredClone(t5.result) as Json);
        expect([...document.querySelectorAll(`[data-testid="${P}-kpi-item"]`)].map((item) => item.getAttribute('data-kpi'))).toEqual(KPIS);
        expect(value('money_lost')).toBe(formatExactMoneyPlain(solution.score.wealth_loss));
        expect(chip('money_lost', 'none')).not.toBeNull();
        expect(value('orders')).toBe('0');
    });

    it('money is masked in privacy mode and unmasked again; points and counts stay public', async () => {
        const solution = mounted(unrelated());
        setPrivacyEnabled(true);
        flushSync();
        await tick();
        for (const kpi of ['value_today', 'value_after', 'money_lost', 'uninvested']) expect(value(kpi), kpi).toContain(PRIVACY_PLACEHOLDER);
        expect(value('largest_deviation')).toContain(formatExactPoints(solution.score.largest_deviation_after));
        expect(value('largest_deviation')).not.toContain(PRIVACY_PLACEHOLDER);
        expect(value('orders')).toBe(String(solution.order_rows.length));
        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(value('value_today')).toBe(formatExactMoneyPlain(solution.plan_accounts.initial_wealth));
    });
});
