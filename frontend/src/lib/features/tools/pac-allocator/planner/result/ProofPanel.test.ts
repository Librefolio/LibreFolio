// @vitest-environment jsdom
/**
 * The Rebalancer's proof (F4a of project 67, step 6). Its cascade has one objective, the score `J` (or, under «Target
 * first», two: the distance, then the money lost); the stages after it are tie-breaks, which only choose among plans no
 * worse on the objectives above (B2, D4: «fewer operations», «route priority», then a fixed order).
 *
 * - **«Balanced»** (the engine's G5 answer, `rebalancer-browser.json`): one objective card, the score, with its three
 *   parts (λ, distance/F, money lost: the published `score` fields); the tie-breaks named in order, then the fixed order;
 *   the witness counts the objective, not the tie-breaks.
 * - **«Target first»** (`rebalancer-t4-target-first.json`): two cards, the distance then the money lost.
 * - **A reason of its own** for a plan not proven (`rebalancer-y-top-up.json`, the wide model's plan): the reason is
 *   written on the panel, and every reason the Rebalancer publishes has its text in the catalogue.
 * - **The PAC's path** (the same answer under the PAC's profile): every stage is a card, no tie-break is named.
 *
 * The fixtures are engine answers, untouched. Figures are compared with the planner's own formatters; no translated
 * sentence is read.
 */
import {flushSync} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, setupI18n} from '$test/component';
import en from '$lib/i18n/en.json';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {catalogCurrencyDigits, exactDisplay, formatExactMoneyPlain, formatPlannerPlainDecimal} from '../format';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import {objectiveNameKey} from '../policies';
import type {PlannerReadyResult} from '../types';
import browser from './__fixtures__/rebalancer-browser.json';
import targetFirst from './__fixtures__/rebalancer-t4-target-first.json';
import yTopUp from './__fixtures__/rebalancer-y-top-up.json';
import ProofPanel from './ProofPanel.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

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

function mounted(result: Json, profile: PlannerProfile = REBALANCER_PLANNER_PROFILE): void {
    const digits = catalogCurrencyDigits(result.catalogs.currencies);
    render(ProfileHarness, {props: {profile, child: ProofPanel, childProps: {result: result as unknown as PlannerReadyResult, metrics: METRICS, batch: {server_processing_ms: 925}, digits}}});
    flushSync();
}

const ids = (selector: string, attribute = 'data-objective') => [...document.querySelectorAll(selector)].map((element) => element.getAttribute(attribute));

describe('the Rebalancer proof (F4a step 6)', () => {
    const P = 'rebalancer-planner';
    const cards = () => ids(`[data-testid="${P}-objective"]`);
    const tieBreaks = () => ids(`[data-testid="${P}-proof-tie-break"] [data-objective]`);

    it('single-objective proof names the score parts and the tie-breaks', () => {
        const result = structuredClone(browser.result) as Json;
        mounted(result);
        expect(cards()).toEqual(['plan_score']);
        const score = result.primary_solution.score;
        const digits = catalogCurrencyDigits(result.catalogs.currencies);
        const card = document.querySelector(`[data-testid="${P}-objective"][data-objective="plan_score"]`) as HTMLElement;
        const part = (id: string) => card.querySelector(`[data-part="${id}"]`)?.textContent ?? null;
        expect(ids(`[data-testid="${P}-objective"] [data-part]`, 'data-part')).toEqual(['distance_weight', 'distance_per_wealth', 'wealth_loss']);
        expect(part('distance_weight')).toContain(formatPlannerPlainDecimal(exactDisplay(score.distance_weight).text));
        expect(part('distance_per_wealth')).toContain(formatExactMoneyPlain(score.distance_per_wealth, {digits}));
        expect(part('wealth_loss')).toContain(formatExactMoneyPlain(score.wealth_loss, {digits}));
        expect(tieBreaks()).toEqual(['operation_count', 'route_priority', 'fixed_order']);
        // PREMISE: on this answer the score closed and the two tie-breaks stopped; the witness names the objective only.
        expect(result.proof.witness.objective_codes).toEqual(['plan_score']);
        expect(document.querySelector(`[data-testid="${P}-proof-witness"]`)?.getAttribute('data-closed')).toBe('1');
    });

    it('target_first shows two objective cards', () => {
        const result = structuredClone(targetFirst.result) as Json;
        mounted(result);
        expect(cards()).toEqual(['target_distance', 'wealth_loss']);
        expect(tieBreaks()).toEqual(['operation_count', 'route_priority', 'fixed_order']);
        // Every stage closed: the witness lists four codes, two of them objectives.
        expect(result.proof.witness.objective_codes).toHaveLength(4);
        expect(document.querySelector(`[data-testid="${P}-proof-witness"]`)?.getAttribute('data-closed')).toBe('2');
    });

    it('a plan not proven says its own reason', () => {
        mounted(structuredClone(yTopUp.result) as Json);
        expect(document.querySelector(`[data-testid="${P}-proof-reason"]`)?.getAttribute('data-reason')).toBe('allocation.limits_leave_no_rounding_room');
    });

    it("the Rebalancer's objectives and tie-breaks have their names, the route priority its own", () => {
        const message = (key: string) => key.split('.').reduce((node: Json | undefined, part) => node?.[part], en as Json);
        for (const code of ['plan_score', 'target_distance', 'wealth_loss', 'operation_count', 'route_priority']) expect(typeof message(objectiveNameKey(code, 'rebalancer').key), code).toBe('string');
        // It has no cash sources: its priority is the routes', not the PAC's «Broker and source priority».
        expect(objectiveNameKey('route_priority', 'rebalancer').key).not.toBe(objectiveNameKey('route_priority', 'pac').key);
    });

    it('every reason a plan may be not proven for has its text in the catalogue', () => {
        const reasons = (en as Json).tools.pacAllocator.planner.result.proof.reasons;
        const text = (code: string) => code.split('.').reduce((node: Json | undefined, part) => node?.[part], reasons);
        for (const code of ['allocation.exact_proof_not_established', 'allocation.limits_leave_no_rounding_room', 'allocation.proof_not_confirmed']) expect(typeof text(code), code).toBe('string');
    });
});

describe('the PAC proof keeps its cascade', () => {
    it('every stage is an objective card, and no tie-break is named', () => {
        const result = structuredClone(browser.result) as Json;
        mounted(result, PAC_PLANNER_PROFILE);
        expect(ids('[data-testid="pac-planner-objective"]')).toEqual(result.primary_solution.objectives.stages.map((stage: Json) => stage.objective_code));
        expect(document.querySelectorAll('[data-testid="pac-planner-objective"] [data-part]')).toHaveLength(0);
        expect(document.querySelectorAll('[data-testid="pac-planner-proof-tie-break"] [data-objective]')).toHaveLength(0);
        expect(document.querySelector('[data-testid="pac-planner-proof-witness"]')?.getAttribute('data-closed')).toBe(String(result.proof.witness.objective_codes.length));
    });
});
