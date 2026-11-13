// @vitest-environment jsdom
/**
 * «Your Assets» under each Tool's profile (F3a of project 67, step 5): the Rebalancer copies the positions, the PAC never.
 *
 * Mounted below a Tool wrapper in miniature (`../../__tests__/ProfileHarness.svelte`), as `profileContext.test.ts` does.
 * The Broker scope answers one owned Broker; the allocation source answers one Asset held there, as the backend
 * serialises it (quantities included: the backend always sends them). Under the Rebalancer's profile «Add» leaves the
 * Asset and its position in the draft; under the PAC's, the Asset only. Driven through test ids.
 */
import {flushSync} from 'svelte';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: (_target, key) => (key === 'get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post' ? allocationSource : vi.fn(async () => undefined))}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));
vi.mock('../scope', () => ({
    loadCopyScope: vi.fn(async () => [{id: 7, name: 'Broker probe', role: 'OWNER', share: null, active: true, selectable: true, iconUrl: null, portalUrl: null, pluginCode: null}]),
    selectableIds: (scope: {id: number; selectable: boolean}[]) => scope.filter((broker) => broker.selectable).map((broker) => broker.id),
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';
import {transitionClientSession, getClientSessionGeneration} from '$lib/stores/app/clientSession';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {draftAssetFromInfo} from '../copies';
import {PlannerDraft} from '../draft.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import OwnedAssetsDialog from './OwnedAssetsDialog.svelte';

const GENERATED = '2026-11-14T09:30:00Z';

function response() {
    return {
        snapshot: {as_of: '2026-11-14', target_currency: 'EUR', generated_at: GENERATED},
        provenance: [
            {provenance_id: 'source:portfolio-ledger', kind: 'domain_copy', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: GENERATED},
            {provenance_id: 'source:broker-domain', kind: 'domain_copy', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: GENERATED},
            {provenance_id: 'source:asset-domain', kind: 'domain_copy', domain: 'asset', source_ref: 'assets', source_label: null, captured_at: GENERATED},
        ],
        assets: [{asset_id: 'asset:11', source_asset_id: 11, name: 'Apple', ticker: 'AAPL', asset_class: 'STOCK', icon_url: null, active: true, provenance_id: 'source:asset-domain'}],
        brokers: [
            {
                broker_id: 'broker:7',
                source_broker_id: 7,
                name: 'Broker probe',
                icon_url: null,
                portal_url: null,
                default_import_plugin: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['EUR'],
                active: true,
                allow_cash_overdraft: false,
                allow_asset_shorting: false,
                operating_profile_status: 'not_available',
                operating_profile: null,
                provenance_id: 'source:broker-domain',
            },
        ],
        holdings: [{holding_id: 'holding:asset:11:broker:7', asset_id: 'asset:11', broker_id: 'broker:7', custody_quantity: '20', ownership_share: '1', economic_quantity: '20', quantity_unit: 'asset_unit', provenance_id: 'source:portfolio-ledger'}],
        cash_balances: [],
        prices: [],
        classifications: [],
        fx_quotes: [],
        current_distribution: null,
        issues: [],
    };
}

beforeAll(async () => {
    await setupI18n();
});

let nextUser = 300;

beforeEach(() => {
    allocationSource.mockReset();
    allocationSource.mockResolvedValue(response());
    transitionClientSession(++nextUser);
});

afterEach(() => cleanup());

async function addAll(profile: PlannerProfile | null, prepare: (draft: PlannerDraft) => void = () => {}): Promise<PlannerDraft> {
    const draft = new PlannerDraft('EUR', 'proportional', profile ?? PAC_PLANNER_PROFILE);
    prepare(draft);
    const prefix = (profile ?? PAC_PLANNER_PROFILE).testIdPrefix;
    const onclose = vi.fn();
    render(ProfileHarness, {props: {profile, child: OwnedAssetsDialog, childProps: {draft, accountGeneration: getClientSessionGeneration(), onadded: vi.fn(), onclose}}});
    await waitFor(() => expect(screen.getByTestId(`${prefix}-owned-assets-body`).getAttribute('data-state')).toBe('ready'));
    flushSync();
    const apply = screen.getByTestId(`${prefix}-owned-assets-apply`) as HTMLButtonElement;
    if (apply.disabled) return draft;
    await fireEvent.click(apply);
    expect(onclose).toHaveBeenCalledOnce();
    expect(allocationSource.mock.calls[0][0].requested_sections).toContain('holdings');
    return draft;
}

describe('«Your Assets» and the positions', () => {
    it('the Rebalancer copies the Asset and its position', async () => {
        const draft = await addAll(REBALANCER_PLANNER_PROFILE);

        expect(draft.asset('asset:11')).toBeDefined();
        expect(draft.data.positions.map((item) => [item.key, item.brokerKey, item.quantity, item.copiedQuantity])).toEqual([['holding:asset:11:broker:7', 'broker:7', '20', '20']]);
        expect(Object.values(draft.data.copies).map((copy) => copy.kind)).toEqual(['positions']);
    });

    it('the PAC copies the Asset only', async () => {
        const draft = await addAll(null);

        expect(draft.asset('asset:11')).toBeDefined();
        expect(draft.data.positions).toEqual([]);
        expect(draft.data.copies).toEqual({});
    });

    // Q-F3a-5a (a): the Rebalancer must see the portfolio as it is, so an Asset already in the plan gets its positions too.
    const inPlan = (draft: PlannerDraft) => draft.addAsset(draftAssetFromInfo({id: 11, display_name: 'Apple', identifier_ticker: 'AAPL', asset_type: 'STOCK', icon_url: null, active: true}));

    it('the Rebalancer lists an Asset already in the plan, marked, and copies its positions', async () => {
        const draft = await addAll(REBALANCER_PLANNER_PROFILE, inPlan);

        expect(screen.queryByTestId('rebalancer-planner-owned-assets-in-plan')).toBeNull(); // closed after «Add»
        expect(draft.data.positions.map((item) => item.key)).toEqual(['holding:asset:11:broker:7']);
        expect(draft.data.assets).toHaveLength(1);
    });

    it('the PAC keeps an Asset already in the plan locked', async () => {
        const draft = await addAll(null, inPlan);

        const row = screen.getByTestId('pac-planner-owned-assets-asset');
        expect(row.getAttribute('data-in-plan')).toBe('true');
        expect((screen.getByTestId('pac-planner-owned-assets-check') as HTMLInputElement).disabled).toBe(true);
        expect((screen.getByTestId('pac-planner-owned-assets-apply') as HTMLButtonElement).disabled).toBe(true);
        expect(draft.data.positions).toEqual([]);
    });
});
