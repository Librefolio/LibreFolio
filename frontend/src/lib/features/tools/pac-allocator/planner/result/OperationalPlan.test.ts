// @vitest-environment jsdom
/**
 * The Rebalancer's operational plan (F4a of project 67, step 2; contract §6.3, M12).
 *
 * The fixture is the engine's answer to the G5 browser scenario (`rebalancer-browser.json`, never edited): two transfers
 * between Brokers (1, 2), a currency exchange (3), then five purchases (4–8). The plan shows the numbered
 * steps in the backend's counter, transfers as steps of their own, and the purchases in one «Purchases on {broker}»
 * section per Broker, each order keeping its counter number. Figures are compared with the planner's own formatter and the
 * heading with the catalogue at its key: nothing reads a translated sentence.
 */
import {get} from 'svelte/store';
import {flushSync} from 'svelte';
import {beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {render, screen, setupI18n, within} from '$test/component';
import {t} from '$lib/i18n';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from '../draft.svelte';
import {catalogCurrencyDigits, formatPlannerMoneyPlain} from '../format';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerReadyResult, PlannerResolvedRequest, RebalancerSolution} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import {planLookup, resultNames} from './model';
import OperationalPlan from './OperationalPlan.svelte';

beforeAll(async () => {
    await setupI18n();
});

const contract = toolContractMap.portfolio_rebalancer['2.0.0'];
const P = 'rebalancer-planner';

function mounted(): {solution: RebalancerSolution; names: ReturnType<typeof resultNames>} {
    const result = contract.output.parse(browser.result) as unknown as PlannerReadyResult;
    const request = contract.input.parse(browser.request) as unknown as PlannerResolvedRequest;
    const solution = (result as unknown as {primary_solution: RebalancerSolution}).primary_solution;
    const names = resultNames(result);
    const lookup = planLookup(result, request, names);
    const draft = new PlannerDraft('EUR', 'invest_only', REBALANCER_PLANNER_PROFILE);
    render(ProfileHarness, {
        props: {
            profile: REBALANCER_PLANNER_PROFILE,
            child: OperationalPlan,
            childProps: {solution, names, lookup, digits: catalogCurrencyDigits(result.catalogs.currencies), draft, onorder: vi.fn()},
        },
    });
    flushSync();
    return {solution, names};
}

describe('the Rebalancer operational plan', () => {
    it('numbers the steps on the backend counter, transfers as steps of their own', () => {
        const {solution} = mounted();
        const steps = screen.getAllByTestId(`${P}-plan-step`);
        expect(steps.map((step) => [step.getAttribute('data-kind'), step.getAttribute('data-sequence')])).toEqual([
            ['transfer', '1'],
            ['transfer', '2'],
            ['conversion', '3'],
        ]);
        // A transfer says where the money goes, and how much, through the planner's formatter.
        const first = solution.transfers.find((transfer) => transfer.sequence === 1)!;
        const sentence = within(steps[0]).getByTestId(`${P}-plan-sentence`);
        expect(sentence.getAttribute('data-broker')).toBe(first.destination_broker_id);
        expect(sentence.getAttribute('data-source-broker')).toBe(first.source_broker_id);
        expect(sentence.getAttribute('data-currency')).toBe(first.amount.currency);
        expect(within(steps[0]).getByTestId(`${P}-plan-amount`).textContent).toBe(formatPlannerMoneyPlain(first.amount.amount, first.amount.currency));
    });

    it('orders are grouped in a buys section per broker, each keeping its counter number', () => {
        const {solution, names} = mounted();
        const sections = screen.getAllByTestId(`${P}-plan-orders`);
        const brokers = [...new Set(solution.order_rows.map((order) => order.broker_id))];
        expect(sections.map((section) => section.getAttribute('data-broker'))).toEqual(brokers);
        for (const section of sections) {
            const brokerId = section.getAttribute('data-broker')!;
            const title = within(section).getByTestId(`${P}-plan-orders-title`).textContent?.trim() ?? '';
            expect(title).toBe(get(t)('tools.portfolioRebalancer.planner.result.plan.buysAt', {values: {broker: names.broker(brokerId)}}));
            // Not the raw key on both sides: the catalogue resolved it, with the Broker's name in it.
            expect(title).toContain(names.broker(brokerId));
            expect(title).not.toContain('buysAt');
            const cells = within(section).getAllByTestId(`${P}-plan-order`);
            const expected = solution.order_rows.filter((order) => order.broker_id === brokerId).sort((a, b) => a.sequence - b.sequence);
            expect(cells.map((cell) => cell.getAttribute('data-order'))).toEqual(expected.map((order) => order.order_id));
            expect(cells.map((cell) => cell.textContent?.trim().split(/\s/)[0])).toEqual(expected.map((order) => String(order.sequence)));
        }
    });
});
