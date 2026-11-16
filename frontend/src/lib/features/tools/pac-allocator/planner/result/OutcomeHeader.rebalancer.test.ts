// @vitest-environment jsdom
/**
 * The Rebalancer's result header (F4a of project 67, step 4; contract §6.6): the score the plan minimizes, read from the
 * published `score`.
 *   - A weighted fidelity («Balanced» on G5, `rebalancer-browser.json`): one badge, the score `J`.
 *   - «Target first» (`rebalancer-t4-target-first.json`, the engine's answer to T4 with that fidelity): two badges, the
 *     distance over the whole portfolio, then the money lost; no score, which the result does not publish.
 * The notes badge is there in both. The PAC's badges (`fixed_l2`, `shortfall`) are not. Figures are compared with the
 * planner's formatter; no translated sentence is read.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {catalogCurrencyDigits, formatExactMoneyPlain, formatPlannerPlainDecimal} from '../format';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerReadyResult, RebalancerSolution} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import targetFirst from './__fixtures__/rebalancer-t4-target-first.json';
import OutcomeHeader from './OutcomeHeader.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
    vi.useRealTimers();
});

const contract = toolContractMap.portfolio_rebalancer['2.0.0'];
const P = 'rebalancer-planner';

function mounted(fixture: {result: unknown}, parse = true): RebalancerSolution['score'] {
    const result = (parse ? contract.output.parse(fixture.result) : fixture.result) as unknown as PlannerReadyResult;
    render(ProfileHarness, {
        props: {
            profile: REBALANCER_PLANNER_PROFILE,
            child: OutcomeHeader,
            childProps: {result, revision: 1, apiVersion: '2.0.0', digits: catalogCurrencyDigits(result.catalogs.currencies), disabled: false, onedit: vi.fn(), oncalculate: vi.fn(), ongotoproof: vi.fn()},
        },
    });
    flushSync();
    return (result as unknown as {primary_solution: RebalancerSolution}).primary_solution.score;
}

const objectives = () => [...document.querySelectorAll(`[data-testid="${P}-outcome-objective"]`)].map((item) => item.getAttribute('data-objective'));
const objective = (code: string) => document.querySelector(`[data-testid="${P}-outcome-objective"][data-objective="${code}"]`)?.textContent?.trim() ?? '';

describe('the Rebalancer result header', () => {
    it('a weighted fidelity shows the score it minimizes', () => {
        const score = mounted(browser);
        expect(objectives()).toEqual(['plan_score']);
        expect(objective('plan_score')).toContain(formatExactMoneyPlain(score.plan_score!));
        expect(screen.getByTestId(`${P}-outcome-notes`)).toBeTruthy();
    });

    it('«Target first» shows the distance, then the money lost, and no score', () => {
        document.body.innerHTML = '';
        const score = mounted(targetFirst);
        expect(score.plan_score).toBeNull();
        expect(objectives()).toEqual(['target_distance', 'wealth_loss']);
        expect(objective('target_distance')).toContain(formatExactMoneyPlain(score.distance_per_wealth));
        expect(objective('wealth_loss')).toContain(formatExactMoneyPlain(score.wealth_loss));
        expect(screen.getByTestId(`${P}-outcome-notes`)).toBeTruthy();
    });

    it('the score badge names its three parts: λ, distance/F and money lost', async () => {
        vi.useFakeTimers();
        const result = structuredClone(browser.result) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
        // λ that is not 1, so the tip shows it (the variant goes to the component directly, not through the codec).
        result.primary_solution.score.distance_weight = {kind: 'finite_decimal', value: '0.25'};
        const score = mounted({result}, false);
        const badge = document.querySelector(`[data-testid="${P}-outcome-objective"][data-objective="plan_score"] span`) as HTMLElement;
        // mouseenter does not bubble: aimed at the tooltip's wrapper, the badge's parent.
        await fireEvent.mouseEnter(badge.parentElement as HTMLElement);
        vi.advanceTimersByTime(600);
        flushSync();
        await tick();
        const tip = screen.getByTestId('tooltip-content').textContent ?? '';
        expect(tip).toContain(formatPlannerPlainDecimal('0.25'));
        expect(tip).toContain(formatExactMoneyPlain(score.distance_per_wealth));
        expect(tip).toContain(formatExactMoneyPlain(score.wealth_loss));
    });

    it('in privacy mode the money of the header is masked and unmasked in place', async () => {
        const score = mounted(browser);
        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(objective('plan_score')).toContain(PRIVACY_PLACEHOLDER);
        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(objective('plan_score')).toContain(formatExactMoneyPlain(score.plan_score!));
        expect(objective('plan_score')).not.toContain(PRIVACY_PLACEHOLDER);
    });
});
