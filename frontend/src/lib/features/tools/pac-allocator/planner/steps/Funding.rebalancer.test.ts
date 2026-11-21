// @vitest-environment jsdom
/**
 * No funding sources in the Rebalancer (F3a of project 67, step 6; contract §5.4, specification §15 n. 2 and n. 4).
 *
 * The PAC lets the user choose which cash and contributions pay for a Broker's purchases, with a priority and a cap
 * (`DraftBroker.funding`, kept by `syncFunding`). The Rebalancer declares none: every cash reaches every Broker, and the
 * backend generates the deposits and transfers. So under the Rebalancer's profile the draft keeps no funding entry, the
 * Brokers step shows no «Usable liquidity», and the «Configure …» window no liquidity section; a cash-only account is a
 * Broker with its cash, not a «funding» source. Under the PAC's profile all of it stays. Mounted below a Tool wrapper in
 * miniature (`../../__tests__/ProfileHarness.svelte`); driven through test ids.
 */
import {flushSync} from 'svelte';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft} from '../draft.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import BrokerEditor from './BrokerEditor.svelte';
import BrokersStep from './BrokersStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

/** One operative manual Broker, a manual account (a cash-only Broker) and a contribution. */
function scenario(profile: PlannerProfile): {draft: PlannerDraft; brokerKey: string} {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const brokerKey = draft.addManualBroker('Broker probe').key;
    draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
    draft.addContribution('EUR', 'Salary probe');
    return {draft, brokerKey};
}

describe('funding sources by Tool', () => {
    it('the Rebalancer draft keeps no funding entry; the PAC draft keeps one per source', () => {
        expect(scenario(REBALANCER_PLANNER_PROFILE).draft.data.brokers.flatMap((broker) => broker.funding)).toEqual([]);
        const pac = scenario(PAC_PLANNER_PROFILE);
        expect(
            pac.draft
                .broker(pac.brokerKey)
                ?.funding.map((item) => item.source.kind)
                .sort(),
        ).toEqual(['cash', 'contribution']);
    });

    it('the Rebalancer Brokers step shows no usable liquidity, and a cash-only account as a cash account', () => {
        const {draft} = scenario(REBALANCER_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: BrokersStep, childProps: {draft, accountGeneration: 0}}});
        flushSync();

        expect(screen.getByTestId('rebalancer-planner-broker')).toBeTruthy();
        expect(screen.queryByTestId('rebalancer-planner-broker-funding')).toBeNull();
        expect(screen.getByTestId('rebalancer-planner-broker-funding-only').getAttribute('data-kind')).toBe('cash-only');
    });

    it('the PAC Brokers step keeps its usable liquidity', () => {
        const {draft} = scenario(PAC_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: null, child: BrokersStep, childProps: {draft, accountGeneration: 0}}});
        flushSync();

        expect(screen.getByTestId('pac-planner-broker-funding')).toBeTruthy();
        expect(screen.getByTestId('pac-planner-broker-funding-only').getAttribute('data-kind')).toBe('funding-only');
    });

    it('the Rebalancer «Configure …» window has no liquidity section, and opening it adds no funding entry', () => {
        const {draft, brokerKey} = scenario(REBALANCER_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: BrokerEditor, childProps: {draft, brokerKey, onclose: vi.fn()}}});
        flushSync();

        expect(screen.getByTestId('rebalancer-planner-broker-editor-profile')).toBeTruthy();
        expect(screen.queryByTestId('rebalancer-planner-broker-editor-funding')).toBeNull();
        expect(screen.queryAllByTestId('rebalancer-planner-funding')).toHaveLength(0);
        screen.getByTestId('rebalancer-planner-broker-editor-apply').click();
        expect(draft.broker(brokerKey)?.funding).toEqual([]);
    });

    it('the PAC «Configure …» window keeps its liquidity section', () => {
        const {draft, brokerKey} = scenario(PAC_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: null, child: BrokerEditor, childProps: {draft, brokerKey, onclose: vi.fn()}}});
        flushSync();

        expect(screen.getByTestId('pac-planner-broker-editor-funding')).toBeTruthy();
        expect(screen.getAllByTestId('pac-planner-funding')).toHaveLength(2);
    });
});
