// @vitest-environment jsdom
/**
 * The Rebalancer's allocation table (F4a of project 67, step 3; contract §6.2): before, target and after for every Asset,
 * every cash entry and the «uninvested» row.
 *
 * The fixtures are engine answers, never edited:
 *   - `rebalancer-browser.json`, the G5 browser scenario: seven Assets, two cash entries with a target, no limit;
 *   - `rebalancer-t11-limits.json`, specification case T11 with a minimum on the Asset and a maximum on the cash.
 * Every cell is a published field, compared with the planner's own formatter: nothing is computed and no translated
 * sentence is read. The minimum and maximum columns exist only when an entry carries a limit.
 */
import {flushSync} from 'svelte';
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {render, screen, setupI18n} from '$test/component';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from '../draft.svelte';
import {catalogCurrencyDigits, formatExactMoneyPlain, formatExactPercent} from '../format';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerReadyResult, RebalancerSolution} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import t11 from './__fixtures__/rebalancer-t11-limits.json';
import {resultNames} from './model';
import RebalancerAllocationTable from './RebalancerAllocationTable.svelte';

beforeAll(async () => {
    await setupI18n();
});

const contract = toolContractMap.portfolio_rebalancer['2.0.0'];

function mounted(fixture: {result: unknown}): RebalancerSolution {
    const result = contract.output.parse(fixture.result) as unknown as PlannerReadyResult;
    const solution = (result as unknown as {primary_solution: RebalancerSolution}).primary_solution;
    const draft = new PlannerDraft('EUR', 'invest_only', REBALANCER_PLANNER_PROFILE);
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerAllocationTable, childProps: {solution, names: resultNames(result), digits: catalogCurrencyDigits(result.catalogs.currencies), draft}}});
    flushSync();
    return solution;
}

const cellText = (rowId: string, column: string) => document.querySelector(`tr[data-row-id="${rowId}"] td[data-column-id="${column}"]`)?.textContent?.trim() ?? null;

describe('the Rebalancer allocation table', () => {
    it('one row per Asset, per cash entry, then the uninvested row’s two parts (TL-5)', () => {
        const solution = mounted(browser);
        expect(screen.getByTestId('rebalancer-planner-allocation-table')).toBeTruthy();
        const ids = [...document.querySelectorAll('tbody tr[data-row-id]')].map((row) => row.getAttribute('data-row-id'));
        expect(ids).toEqual([...solution.asset_rows.map((row) => row.asset_id), ...solution.cash_rows.map((row) => `cash:${row.broker_id}:${row.currency}`), 'untargeted_cash', 'costs']);
        expect([...document.querySelectorAll('[data-testid="rebalancer-planner-allocation-uninvested-note"]')].map((note) => note.getAttribute('data-kind'))).toEqual(['untargeted_cash', 'costs']);
    });

    it('before, target and after are the published fields, for an Asset, a cash entry and the uninvested row’s parts', () => {
        const solution = mounted(browser);
        const asset = solution.asset_rows[0];
        expect(cellText(asset.asset_id, 'beforeShare')).toBe(formatExactPercent(asset.before_weight));
        expect(cellText(asset.asset_id, 'beforeValue')).toBe(formatExactMoneyPlain(asset.before_value));
        expect(cellText(asset.asset_id, 'target')).toBe(formatExactPercent(asset.target_weight));
        expect(cellText(asset.asset_id, 'targetValue')).toBe(formatExactMoneyPlain(asset.target_value));
        expect(cellText(asset.asset_id, 'finalValue')).toBe(formatExactMoneyPlain(asset.final_value));
        expect(cellText(asset.asset_id, 'bought')).toBe(formatExactMoneyPlain(asset.buy_mid_value));
        const cash = solution.cash_rows[0];
        const cashId = `cash:${cash.broker_id}:${cash.currency}`;
        expect(cellText(cashId, 'beforeValue')).toBe(formatExactMoneyPlain(cash.before_value));
        expect(cellText(cashId, 'finalValue')).toBe(formatExactMoneyPlain(cash.final_value));
        expect(cellText(cashId, 'residual')).toBe(formatExactMoneyPlain(cash.residual, {signed: true}));
        // TL-5: the cash with no target (8 200,00 € → 321,73 € in the G5 answer) and the costs (0 → 0,02 €), each its published part.
        for (const kind of ['untargeted_cash', 'costs'] as const) {
            const part = solution.uninvested_row[kind];
            expect(cellText(kind, 'beforeShare'), kind).toBe(formatExactPercent(part.before_weight));
            expect(cellText(kind, 'beforeValue'), kind).toBe(formatExactMoneyPlain(part.before_value));
            expect(cellText(kind, 'finalValue'), kind).toBe(formatExactMoneyPlain(part.final_value));
            expect(cellText(kind, 'final'), kind).toBe(formatExactPercent(part.final_weight));
            // No target: the target cells are empty, never a computed zero.
            expect(cellText(kind, 'target'), kind).toBe('');
            expect(cellText(kind, 'targetValue'), kind).toBe('');
            expect(cellText(kind, 'residual'), kind).toBe('');
        }
        expect(formatExactMoneyPlain(solution.uninvested_row.untargeted_cash.before_value), 'PREMISE: the figures of the developer’s answer').toBe(formatExactMoneyPlain({value: {kind: 'finite_decimal', value: '8200'}, currency: 'EUR'}));
        expect(formatExactMoneyPlain(solution.uninvested_row.untargeted_cash.final_value)).toBe(formatExactMoneyPlain({value: {kind: 'finite_decimal', value: '321.73'}, currency: 'EUR'}));
    });

    it('the minimum and maximum columns appear only when an entry carries a limit', () => {
        mounted(browser);
        expect(screen.queryByTestId('dt-header-minimum')).toBeNull();
        expect(screen.queryByTestId('dt-header-maximum')).toBeNull();
    });

    it('a limit on an Asset and on a cash entry shows in its column', () => {
        document.body.innerHTML = '';
        const solution = mounted(t11);
        const asset = solution.asset_rows[0];
        const cash = solution.cash_rows[0];
        expect(screen.getByTestId('dt-header-minimum')).toBeTruthy();
        expect(screen.getByTestId('dt-header-maximum')).toBeTruthy();
        expect(cellText(asset.asset_id, 'minimum')).toBe(formatExactMoneyPlain(asset.minimum!));
        expect(cellText(`cash:${cash.broker_id}:${cash.currency}`, 'maximum')).toBe(formatExactMoneyPlain(cash.maximum!));
        expect(cellText(asset.asset_id, 'maximum')).toBe('');
    });
});
