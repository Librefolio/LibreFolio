// @vitest-environment jsdom
/**
 * A Broker that only holds positions (F3a of project 67, Q-F3a-5b, the consultant's (a)).
 *
 * The portfolio counts everything the user owns; the plan acts only where the user chose. A position at a Broker that is
 * not among the scenario's Brokers makes that Broker a «positions only» Broker: the Brokers step shows it with its label
 * and «Add to the plan», which reads the Broker from LibreFolio and copies it as any copied Broker, operating profile
 * included (P3). Until then no route and no transfer touch it (`request.rebalancer.test.ts`). Mounted below a Tool wrapper
 * in miniature; the allocation source answers as the backend serialises it.
 */
import {flushSync} from 'svelte';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: (_target, key) => (key === 'get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post' ? allocationSource : vi.fn(async () => undefined))}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {applyOwnedPositions, domainBrokerKey, newCopyRecord, ownedAssets} from '../copies';
import {PlannerDraft} from '../draft.svelte';
import {REBALANCER_PLANNER_PROFILE} from '../profile';
import type {PlannerSource} from '../source';
import BrokersStep from './BrokersStep.svelte';

const GENERATED = '2026-11-14T09:30:00Z';

const PROFILE = {
    profile_version: 1,
    order_modes: [{currency: 'EUR', capability: {kind: 'whole_quantity', capability_id: 'mode:EUR', quantity_unit: 'asset_unit', quantity_step: '1'}, fees: []}],
    conversion_mode: 'automatic',
};

/** Broker 9 as the backend serialises it, with its operating profile. */
function brokerResponse() {
    return {
        snapshot: {as_of: '2026-11-14', target_currency: 'EUR', generated_at: GENERATED},
        provenance: [{provenance_id: 'source:broker-domain', kind: 'domain_copy', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: GENERATED}],
        assets: [],
        brokers: [
            {
                broker_id: 'broker:9',
                source_broker_id: 9,
                name: 'Held broker probe',
                icon_url: null,
                portal_url: null,
                default_import_plugin: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['EUR'],
                active: true,
                allow_cash_overdraft: false,
                allow_asset_shorting: false,
                operating_profile_status: 'available',
                operating_profile: PROFILE,
                provenance_id: 'source:broker-domain',
            },
        ],
        holdings: [],
        cash_balances: [],
        prices: [],
        classifications: [],
        fx_quotes: [],
        current_distribution: null,
        issues: [],
    };
}

/** The user's position in a held Asset at Broker 9, copied from «Your Assets». */
function heldSource(): PlannerSource {
    return {
        asOf: '2026-11-14',
        targetCurrency: 'EUR',
        generatedAt: GENERATED,
        provenance: [
            {provenance_id: 'source:portfolio-ledger', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: GENERATED},
            {provenance_id: 'source:broker-domain', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: GENERATED},
        ],
        assets: [{asset_id: 'asset:11', source_asset_id: 11, name: 'Held probe', ticker: null, asset_class: 'etf', icon_url: null, active: true, provenance_id: 'source:portfolio-ledger'}],
        brokers: [
            {
                broker_id: 'broker:9',
                source_broker_id: 9,
                name: 'Held broker probe',
                icon_url: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['EUR'],
                active: true,
                operating_profile_status: 'not_available',
                operating_profile: null,
                provenance_id: 'source:broker-domain',
            },
        ],
        holdings: [{holding_id: 'holding:asset:11:broker:9', asset_id: 'asset:11', broker_id: 'broker:9', provenance_id: 'source:portfolio-ledger', quantity: {custody: '12', ownershipShare: '1', economic: '12'}}],
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

beforeAll(async () => {
    await setupI18n();
});

let nextUser = 700;

beforeEach(() => {
    allocationSource.mockReset();
    allocationSource.mockResolvedValue(brokerResponse());
    transitionClientSession(++nextUser);
});

afterEach(() => cleanup());

function mount(): PlannerDraft {
    const draft = new PlannerDraft('EUR', 'invest_only', REBALANCER_PLANNER_PROFILE);
    draft.addManualBroker('Broker probe');
    const source = heldSource();
    applyOwnedPositions(draft, source, newCopyRecord(draft, 'positions', source), ownedAssets(source).rows);
    render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: BrokersStep, childProps: {draft, accountGeneration: getClientSessionGeneration()}}});
    flushSync();
    return draft;
}

describe('a Broker with positions only', () => {
    it('shows as «positions only», outside the scenario Brokers', () => {
        const draft = mount();

        expect(draft.positionOnlyBrokers.map((broker) => broker.brokerKey)).toEqual([domainBrokerKey(9)]);
        const card = screen.getByTestId('rebalancer-planner-broker-positions-only');
        expect(card.getAttribute('data-broker-key')).toBe(domainBrokerKey(9));
        expect(draft.broker(domainBrokerKey(9))).toBeUndefined();
    });

    it('«Add to the plan» copies it with its operating profile', async () => {
        const draft = mount();

        await fireEvent.click(screen.getByTestId('rebalancer-planner-broker-positions-only-add'));
        await waitFor(() => expect(draft.broker(domainBrokerKey(9))).toBeDefined());
        flushSync();

        expect(allocationSource.mock.calls[0][0]).toMatchObject({requested_sections: ['brokers'], broker_ids: [9]});
        const broker = draft.broker(domainBrokerKey(9))!;
        expect(broker.modes.map((mode) => mode.currency)).toEqual(['EUR']);
        expect(broker.conversionMode).toBe('automatic');
        expect(draft.positionOnlyBrokers).toEqual([]);
        expect(screen.queryByTestId('rebalancer-planner-broker-positions-only')).toBeNull();
    });

    it('a failed read adds nothing and says so', async () => {
        allocationSource.mockRejectedValue(new Error('read probe'));
        const draft = mount();

        await fireEvent.click(screen.getByTestId('rebalancer-planner-broker-positions-only-add'));
        await waitFor(() => expect(screen.getByTestId('rebalancer-planner-broker-positions-only-error')).toBeTruthy());

        expect(draft.broker(domainBrokerKey(9))).toBeUndefined();
    });

    it('a Broker without an operating profile is added as «Copy from a Broker» adds it: default modes, the same quiet notice', async () => {
        const response = brokerResponse();
        response.brokers[0] = {...response.brokers[0], operating_profile_status: 'not_available', operating_profile: null as never};
        response.issues = [
            {
                code: 'allocation.broker_execution_profile_unsupported',
                kind: 'unsupported',
                severity: 'error',
                path: {kind: 'field', section: 'brokers', entity_kind: 'broker', entity_id: 'broker:9', field: 'operating_profile_status'},
                params: [],
                message_key: 'allocation.broker_execution_profile_unsupported',
            } as never,
        ];
        allocationSource.mockResolvedValue(response);
        const draft = mount();

        await fireEvent.click(screen.getByTestId('rebalancer-planner-broker-positions-only-add'));
        await waitFor(() => expect(draft.broker(domainBrokerKey(9))).toBeDefined());
        flushSync();

        // The default mode of each observed currency (D11: no profile, as before P3).
        expect(draft.broker(domainBrokerKey(9))!.modes.map((mode) => mode.currency)).toEqual(['EUR']);
        expect(draft.broker(domainBrokerKey(9))!.copiedModes).toBeNull();
        // The Brokers step shows its copy notice «quiet»: as for «Copy from a Broker», the missing profile is not a line here.
        expect(screen.queryByTestId('rebalancer-planner-brokers-notice')).toBeNull();
    });
});
