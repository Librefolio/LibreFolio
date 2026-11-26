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
import {resultNames} from './model';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerReadyResult} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import t5 from './__fixtures__/rebalancer-t5.json';
import targetFirst from './__fixtures__/rebalancer-t4-target-first.json';
import contribution from './__fixtures__/rebalancer-t4-contribution.json';
import topUp from './__fixtures__/rebalancer-y-top-up.json';
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
    solution.plan_accounts.final_cash = money('58');
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
const KPIS = ['value_today', 'value_after', 'money_lost', 'largest_deviation', 'final_cash', 'orders'];

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
        // TL-5: «Left in cash» is all the cash at the end, a published field; N and its share are no longer a tile.
        expect(value('final_cash')).toBe(formatExactMoneyPlain(solution.plan_accounts.final_cash));
        expect(tile('final_cash')?.querySelectorAll(`[data-testid="${P}-kpi-chip"]`)).toHaveLength(0);
        expect(value('orders')).toBe(String(solution.order_rows.length));
        expect(chip('orders', 'transfers')).toContain(String(solution.transfers.length));
    });

    it('the largest gap names its item, after and before, with its share and its target (X14: published references)', () => {
        // On the G5 answer the engine names the EUR cash of broker:1 before the plan and asset:6 after it. The tile reads the
        // two references and the rows they point to: no gap is computed here.
        const result = structuredClone(browser.result) as Json;
        const solution = mounted(result);
        const names = resultNames(result as unknown as PlannerReadyResult);
        const before = solution.score.largest_deviation_before_item;
        const after = solution.score.largest_deviation_after_item;
        expect([before.kind, after.kind], 'PREMISE: a cash item before, an Asset after').toEqual(['cash', 'asset']);
        const assetRow = solution.asset_rows.find((row: Json) => row.asset_id === after.asset_id);
        const cashRow = solution.cash_rows.find((row: Json) => row.broker_id === before.broker_id && row.currency === before.currency);
        const afterChip = chip('largest_deviation', 'after_item');
        expect(afterChip).toContain(names.asset(after.asset_id));
        expect(afterChip).toContain(formatExactPercent(assetRow.final_weight));
        expect(afterChip).toContain(formatExactPercent(assetRow.target_weight));
        const beforeChip = chip('largest_deviation', 'before');
        expect(beforeChip).toContain(formatExactPoints(solution.score.largest_deviation_before));
        expect(beforeChip).toContain(names.broker(before.broker_id));
        expect(beforeChip).toContain(before.currency);
        expect(beforeChip).toContain(formatExactPercent(cashRow.before_weight));
        expect(beforeChip).toContain(formatExactPercent(cashRow.target_weight));
    });

    it('with no item off its target the gap names none', () => {
        const result = structuredClone(browser.result) as Json;
        result.primary_solution.score.largest_deviation_after_item = null;
        result.primary_solution.score.largest_deviation_before_item = null;
        const solution = mounted(result);
        expect(chip('largest_deviation', 'after_item')).toBeNull();
        expect(chip('largest_deviation', 'before')).toContain(formatExactPoints(solution.score.largest_deviation_before));
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
        for (const kpi of ['value_today', 'value_after', 'money_lost', 'final_cash']) expect(value(kpi), kpi).toContain(PRIVACY_PLACEHOLDER);
        for (const row of cashRows('final_cash')) expect(row.text, row.currency ?? undefined).toContain(PRIVACY_PLACEHOLDER);
        expect(value('largest_deviation')).toContain(formatExactPoints(solution.score.largest_deviation_after));
        expect(value('largest_deviation')).not.toContain(PRIVACY_PLACEHOLDER);
        expect(value('orders')).toBe(String(solution.order_rows.length));
        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(value('value_today')).toBe(formatExactMoneyPlain(solution.plan_accounts.initial_wealth));
    });
});

/** The cash rows of a tile (TL-5): the currency and the text of each, in the order shown. */
function cashRows(kpi: string, prefix = P): {currency: string | null; text: string; unused: string | null}[] {
    const item = document.querySelector(`[data-testid="${prefix}-kpi-item"][data-kpi="${kpi}"]`);
    return [...(item?.querySelectorAll(`[data-testid="${prefix}-kpi-cash-row"]`) ?? [])].map((row) => ({
        currency: row.getAttribute('data-currency'),
        text: row.textContent?.replace(/\s+/g, ' ').trim() ?? '',
        unused: row.querySelector(`[data-testid="${prefix}-kpi-cash-unused"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? null,
    }));
}

const eur = (value: string) => formatExactMoneyPlain({value: {kind: 'finite_decimal', value}, currency: 'EUR'});

/**
 * TL-5 of project 67 (the developer's answers of 24/11, the consultant REB's of the same day): «Left in cash», all the cash
 * at the end in the valuation currency, and under it the cash of every currency in its own, at the start and at the end,
 * with the contributions not used. Every figure is published (`plan_accounts.final_cash`, `cash_by_currency`).
 */
describe('the cash left, currency by currency (TL-5)', () => {
    it('the G5 answer: two currencies, each in its own, the valuation currency first', () => {
        const solution = mounted(structuredClone(browser.result) as Json);
        const published = solution.plan_accounts.cash_by_currency as Json[];
        expect(
            published.map((row) => [row.currency, formatExactMoneyPlain(row.initial), formatExactMoneyPlain(row.final)]),
            'PREMISE: the figures of the consultant’s answer',
        ).toEqual([
            ['EUR', eur('25550'), eur('6582.73')],
            ['USD', formatExactMoneyPlain({value: {kind: 'finite_decimal', value: '5344.53'}, currency: 'USD'}), formatExactMoneyPlain({value: {kind: 'finite_decimal', value: '7012.73'}, currency: 'USD'})],
        ]);
        expect(value('final_cash')).toBe(formatExactMoneyPlain(solution.plan_accounts.final_cash));
        const rows = cashRows('final_cash');
        expect(rows.map((row) => row.currency)).toEqual(['EUR', 'USD']);
        published.forEach((row, index) => {
            expect(rows[index].text).toContain(formatExactMoneyPlain(row.initial));
            expect(rows[index].text).toContain(formatExactMoneyPlain(row.final));
            expect(rows[index].unused, 'every contribution used').toBeNull();
        });
    });

    it('a contribution not deposited stays at the end, and says so', () => {
        const solution = mounted(structuredClone(contribution.result) as Json);
        expect(value('final_cash')).toBe(eur('70'));
        const [row, ...others] = cashRows('final_cash');
        expect(others).toEqual([]);
        expect(row.currency).toBe('EUR');
        expect(row.text).toContain(eur('500'));
        expect(row.text).toContain(eur('70'));
        expect(row.unused).toContain(formatExactMoneyPlain(solution.plan_accounts.cash_by_currency[0].unused_contributions));
    });

    it('a rounding top-up: the cash ends a cent below zero, shown as it is', () => {
        mounted(structuredClone(topUp.result) as Json);
        expect(value('final_cash')).toBe(eur('-0.01'));
        expect(cashRows('final_cash')[0].text).toContain(eur('-0.01'));
    });
});

/**
 * TL-5 in the PAC: its «Not invested» keeps its figure (the shortfall, the name of an objective) and its parts; the cash of
 * every currency goes under them. Mounted with the PAC's profile, on the G5 answer's accounts.
 */
describe('the PAC’s «Not invested» with the cash by currency (TL-5)', () => {
    it('keeps the shortfall, and lists the cash at the start and at the end of each currency', () => {
        const result = structuredClone(browser.result) as Json;
        const solution = result.primary_solution;
        render(ProfileHarness, {props: {profile: PAC_PLANNER_PROFILE, child: KpiCards, childProps: {solution, result: result as unknown as PlannerReadyResult, metrics: METRICS, digits: catalogCurrencyDigits(result.catalogs.currencies)}}});
        flushSync();
        const pac = 'pac-planner';
        const shortfall = document.querySelector(`[data-testid="${pac}-kpi-item"][data-kpi="shortfall"] [data-testid="${pac}-kpi-value"]`)?.textContent?.trim();
        expect(shortfall).toBe(formatExactMoneyPlain(solution.accounting.shortfall));
        expect(cashRows('shortfall', pac).map((row) => row.currency)).toEqual(['EUR', 'USD']);
        expect(document.querySelector(`[data-testid="${pac}-kpi-item"][data-kpi="final_cash"]`), 'the Rebalancer’s tile only').toBeNull();
    });
});

/**
 * F4a of project 67, step 6: the «Calculation» box counts the Rebalancer's objectives, not its tie-breaks. On the G5
 * answer the score closed and the two tie-breaks stopped: one objective of one is closed. Under «Target first» (T4) every
 * stage closed: two of two.
 */
describe('the Rebalancer «Objectives closed»', () => {
    const counted = () => {
        const row = document.querySelector(`[data-testid="${P}-kpi-compute-row"][data-row="objectives"] dd`);
        return [row?.getAttribute('data-closed'), row?.getAttribute('data-total')];
    };

    it('counts the score, not the tie-breaks', () => {
        const result = structuredClone(browser.result) as Json;
        expect(
            result.solver_evidence.stages.map((stage: Json) => stage.status),
            'PREMISE',
        ).toEqual(['finished', 'unfinished', 'unfinished']);
        mounted(result);
        expect(counted()).toEqual(['1', '1']);
    });

    it('counts two objectives under «Target first»', () => {
        mounted(structuredClone(targetFirst.result) as Json);
        expect(counted()).toEqual(['2', '2']);
    });
});
