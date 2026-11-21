// @vitest-environment jsdom
/**
 * An Asset added by search brings its positions under the Rebalancer (F3a of project 67, Q-F3a-5a (a)).
 *
 * After an Asset is added from the database, `AddedAssetFacts` reads its stored price and composition. A reader made for
 * a Tool that works on positions (`{positions: true}`, the Rebalancer) asks for the holdings too and copies the user's
 * positions in that Asset; the PAC's reader asks for no holding. The Broker scope answers one owned Broker; the source
 * answers as the backend serialises it.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: (_target, key) => (key === 'get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post' ? allocationSource : vi.fn(async () => undefined))}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));
vi.mock('./scope', () => ({
    loadCopyScope: vi.fn(async () => [{id: 7, name: 'Broker probe', role: 'OWNER', share: null, active: true, selectable: true, iconUrl: null, portalUrl: null, pluginCode: null}]),
    selectableIds: (scope: {id: number; selectable: boolean}[]) => scope.filter((broker) => broker.selectable).map((broker) => broker.id),
}));

import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {AddedAssetFacts} from './assetRead.svelte';
import {draftAssetFromInfo} from './copies';
import {PlannerDraft} from './draft.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE} from './profile';

const GENERATED = '2026-11-14T09:30:00Z';

function response() {
    return {
        snapshot: {as_of: '2026-11-14', target_currency: 'EUR', generated_at: GENERATED},
        provenance: [
            {provenance_id: 'source:portfolio-ledger', kind: 'domain_copy', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: GENERATED},
            {provenance_id: 'source:asset-domain', kind: 'domain_copy', domain: 'asset', source_ref: 'assets', source_label: null, captured_at: GENERATED},
            {provenance_id: 'source:broker-domain', kind: 'domain_copy', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: GENERATED},
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

let nextUser = 500;

beforeEach(() => {
    allocationSource.mockReset();
    allocationSource.mockResolvedValue(response());
    transitionClientSession(++nextUser);
});

async function addBySearch(positions: boolean): Promise<PlannerDraft> {
    const draft = new PlannerDraft('EUR', 'proportional', positions ? REBALANCER_PLANNER_PROFILE : PAC_PLANNER_PROFILE);
    draft.addAsset(draftAssetFromInfo({id: 11, display_name: 'Apple', identifier_ticker: 'AAPL', asset_type: 'STOCK', icon_url: null, active: true}));
    await new AddedAssetFacts({positions}).read(draft, [11], getClientSessionGeneration());
    return draft;
}

describe('an Asset added by search', () => {
    it('brings its positions under the Rebalancer', async () => {
        const draft = await addBySearch(true);

        expect(allocationSource.mock.calls[0][0].requested_sections).toEqual(expect.arrayContaining(['holdings', 'brokers']));
        expect(draft.data.positions.map((item) => [item.key, item.quantity])).toEqual([['holding:asset:11:broker:7', '20']]);
    });

    it('brings none under the PAC, which asks for no holding', async () => {
        const draft = await addBySearch(false);

        expect(allocationSource.mock.calls[0][0].requested_sections).not.toContain('holdings');
        expect(draft.data.positions).toEqual([]);
    });
});
