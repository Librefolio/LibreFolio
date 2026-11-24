// @vitest-environment jsdom
/**
 * The Rebalancer's Strategy step (F3a of project 67, step 10b; M29–M33, decisioni-REB §7.3).
 *
 * Two strategies as cards: «Invest only» chosen, «Invest and sell» visible but off, «coming soon» (S1: no draft produces
 * `invest_and_sell` before F3b). The target fidelity as five cards (M29): the three levels («Balanced» the default, with
 * its badge), «Target first», «Custom». «Custom» has one field, in euros, inside its card: the most the user accepts to
 * spend for the reference row; the preview class turns them into the draft's λ on the preview's total, at once on current
 * numbers (R1-F (b) of project 67; the draft keeps λ, never the euros). Empty, zero or negative: an error on the field and
 * a local problem of the step. Without the preview's total (one that cannot be counted yet) the field is off. The table
 * «Maximum acceptable cost» sits under the choices.
 * Both choices are `ChoiceCards` (G6-3): native radios, one group each; a choice is made on its radio. Nothing reads
 * translated text.
 */
import {flushSync, tick} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, within} from '$test/component';
import {setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from '../draft.svelte';
import {defaultPolicy} from '../policies';
import {PlannerPreview, type PreviewReady} from '../preview.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import {localProblems} from '../request';
import RebalancerStrategyStep from './RebalancerStrategyStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

const money = (value: string) => ({value: {kind: 'finite_decimal' as const, value}, currency: 'EUR'});
const number = (value: string) => ({kind: 'finite_decimal' as const, value});

/** A ready preview on 20 000 €: the reference row is 1 000 €, and λ 0.6 accepts 60 € for it. */
function ready(): PreviewReady {
    return {
        operation: 'preview',
        result_state: 'preview_ready',
        availability: 'ready',
        valuation_currency: 'EUR',
        total: money('20000'),
        issues: [],
        limit_problems: [],
        items: [],
        fidelity_level_weights: {cost_aware: number('0.25'), balanced: number('1'), faithful: number('4')},
    };
}

function setup(numbers: PreviewReady | null = ready(), state: PlannerPreview['state'] = 'ready') {
    const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
    const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
    preview.state = state;
    preview.numbers = numbers;
    preview.reason = numbers ? null : 'allocation.price_missing';
    const sent = vi.spyOn(preview, 'setCustomEuros').mockImplementation(() => {});
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerStrategyStep, childProps: {draft, preview}}});
    flushSync();
    return {draft, preview, sent};
}

function choice(name: string): HTMLElement {
    const found = screen.getAllByTestId('rebalancer-planner-fidelity-choice').find((card) => card.getAttribute('data-choice') === name);
    if (!found) throw new Error(`no fidelity choice ${name}`);
    return found;
}

/** A choice is made on its card's radio. */
function pick(name: string): Promise<boolean> {
    return fireEvent.click(within(choice(name)).getByTestId('rebalancer-planner-fidelity-choice-radio'));
}

function chooseCustom(): Promise<boolean> {
    return pick('custom');
}

describe('the Rebalancer Strategy step', () => {
    it('«Invest only» is the strategy; «Invest and sell» is shown, off, coming soon', async () => {
        const {draft} = setup();
        const cards = screen.getAllByTestId('rebalancer-planner-strategy-card');
        expect(cards.map((card) => [card.getAttribute('data-strategy'), card.getAttribute('data-selected')])).toEqual([
            ['invest_only', 'true'],
            ['invest_and_sell', 'false'],
        ]);
        const sell = within(cards[1]).getByTestId('rebalancer-planner-strategy-radio') as HTMLInputElement;
        expect(sell.disabled).toBe(true);
        expect(cards[1].getAttribute('data-disabled')).toBe('true');
        expect(within(cards[1]).getByTestId('rebalancer-planner-strategies-badge')).toBeTruthy();
        await fireEvent.click(sell);
        expect(draft.data.policy).toBe('invest_only');
    });

    it('five fidelity choices, «Balanced» the default with its badge; a choice goes to the draft', async () => {
        const {draft} = setup();
        expect(screen.getAllByTestId('rebalancer-planner-fidelity-choice').map((card) => card.getAttribute('data-choice'))).toEqual(['cost_aware', 'balanced', 'faithful', 'target_first', 'custom']);
        expect(choice('balanced').getAttribute('data-selected')).toBe('true');
        expect(choice('balanced').querySelector('[data-testid="rebalancer-planner-fidelity-choices-default"]')).not.toBeNull();
        // One radio group: the arrow keys move the choice (M6).
        const radios = screen.getAllByTestId('rebalancer-planner-fidelity-choice-radio') as HTMLInputElement[];
        expect(new Set(radios.map((radio) => radio.name)).size).toBe(1);
        expect(radios.map((radio) => radio.checked)).toEqual([false, true, false, false, false]);
        expect(choice('target_first').querySelector('[data-tone="warning"]')).not.toBeNull();

        await pick('faithful');
        expect(draft.data.fidelity).toEqual({kind: 'level', level: 'faithful'});
        await pick('target_first');
        expect(draft.data.fidelity).toEqual({kind: 'target_first'});
        expect(choice('target_first').getAttribute('data-selected')).toBe('true');
    });

    it('«Custom»: the euros go to the preview class; empty or zero is an error on the field and a problem of the step', async () => {
        const {draft, sent} = setup();
        await chooseCustom();
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
        const field = screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement;
        expect(field.disabled).toBe(false);
        // The field sits in «Custom»'s card, outside its radio's label; its unit in the project's form (G6-5).
        expect(field.closest('label')).toBeNull();
        expect(field.closest('[data-testid="rebalancer-planner-fidelity-choice"]')).toBe(choice('custom'));
        expect(screen.getByTestId('rebalancer-planner-fidelity-custom-unit').getAttribute('data-currency')).toBe('EUR');

        await fireEvent.input(field, {target: {value: '60'}});
        expect(sent).toHaveBeenLastCalledWith(draft, '60');
        expect(screen.queryByTestId('rebalancer-planner-fidelity-custom-error')).toBeNull();

        await fireEvent.input(field, {target: {value: '0'}});
        expect(screen.getByTestId('rebalancer-planner-fidelity-custom-error')).toBeTruthy();
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
        expect(localProblems(draft).map((problem) => `${problem.step}:${problem.key}`)).toContain('strategy:fidelityCustomMissing');
    });

    it("typing new euros clears the draft's λ until they are converted; a cleared field drops the euros waiting", async () => {
        const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
        draft.data.fidelity = {kind: 'custom', lambda: '0.6'};
        const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
        preview.state = 'ready';
        preview.numbers = ready();
        const sent = vi.spyOn(preview, 'setCustomEuros').mockImplementation(() => {});
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerStrategyStep, childProps: {draft, preview}}});
        flushSync();
        const field = screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement;

        // The λ of 60 must not travel with 600 on screen.
        await fireEvent.input(field, {target: {value: '600'}});
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
        expect(sent).toHaveBeenLastCalledWith(draft, '600');

        await fireEvent.input(field, {target: {value: ''}});
        expect(sent).toHaveBeenLastCalledWith(draft, '');
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: ''});
    });

    it('«Custom» with a λ shows its euros on the preview total; the table is under the choices', () => {
        const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
        draft.data.fidelity = {kind: 'custom', lambda: '0.6'};
        const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
        preview.state = 'ready';
        preview.numbers = ready();
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerStrategyStep, childProps: {draft, preview}}});
        flushSync();
        expect((screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement).value).toBe('60');
        expect(screen.getByTestId('rebalancer-planner-fidelity')).toBeTruthy();
        expect(localProblems(draft).map((problem) => problem.key)).not.toContain('fidelityCustomMissing');
    });

    it('a figure typed on current numbers is λ at once: the field keeps the figure, the column shows it (R1-F b)', async () => {
        const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
        const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
        preview.state = 'ready';
        preview.numbers = ready();
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerStrategyStep, childProps: {draft, preview}}});
        flushSync();
        await chooseCustom();
        const field = screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement;
        await fireEvent.input(field, {target: {value: '80'}});
        flushSync();
        // 80·20 000/(2·1 000²) = 0.8.
        expect(draft.data.fidelity).toEqual({kind: 'custom', lambda: '0.8'});
        expect(field.value).toBe('80');
        const custom = screen.getAllByTestId('rebalancer-planner-fidelity-cell').filter((cell) => cell.getAttribute('data-level') === 'custom');
        expect(custom).toHaveLength(4);
        expect(localProblems(draft).map((problem) => problem.key)).not.toContain('fidelityCustomMissing');
    });

    it('without the preview total (one that cannot be counted yet) the «Custom» field is off', async () => {
        setup(null, 'error');
        await chooseCustom();
        expect((screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement).disabled).toBe(true);
        expect(screen.getByTestId('rebalancer-planner-fidelity-reason')).toBeTruthy();
    });

    it('in privacy mode the «Custom» figures are masked, the field gives way to its mask; back again when privacy is off', async () => {
        const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
        draft.data.fidelity = {kind: 'custom', lambda: '0.6'};
        const preview = new PlannerPreview({call: vi.fn(), blocked: () => false});
        preview.state = 'ready';
        preview.numbers = ready();
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: RebalancerStrategyStep, childProps: {draft, preview}}});
        flushSync();
        const card = () => choice('custom');

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(screen.queryByTestId('rebalancer-planner-fidelity-custom-input')).toBeNull();
        expect(screen.getByTestId('rebalancer-planner-fidelity-custom-masked').textContent).toContain(PRIVACY_PLACEHOLDER);
        // The reference row's figure in the sentence is masked too.
        expect(card().textContent).not.toMatch(/1[.,]?000/);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect((screen.getByTestId('rebalancer-planner-fidelity-custom-input') as HTMLInputElement).value).toBe('60');
        expect(card().textContent).toMatch(/1[.,]?000/);
    });
});
