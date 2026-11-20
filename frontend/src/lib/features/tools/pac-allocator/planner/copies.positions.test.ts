// @vitest-environment jsdom
/**
 * The user's positions in the draft (F3a of project 67, step 5; Vitest + jsdom).
 *
 * Subject. The Rebalancer works on what the user holds. «Your Assets» reads the holdings with their quantities
 * (`SourceReadOptions.positions`) and, besides the Assets, copies one position per Asset × Broker: the quantity in
 * custody, the user's share, and the planning quantity, proposed from the user's part (`economic`) and editable. The
 * model of `copiedPrice`: the position keeps its copied quantity, so the user's edit reads «modified» and a second copy
 * updates the copy, never what the user wrote. A removed Asset takes its positions with it. The PAC's read keeps no
 * quantity (`quantity: null`): it copies no position.
 *
 * Environment. jsdom for the compile target, not for the DOM (see `request.test.ts`).
 */
import {describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {applyOwnedPositions, domainAssetKey, domainBrokerKey, newCopyRecord, ownedAssets, refreshCopiedFacts, refreshPlan, refreshQuery} from './copies';
import {PlannerDraft, positionIsCopied} from './draft.svelte';
import {REBALANCER_PLANNER_PROFILE} from './profile';
import type {PlannerSource, SourceHoldingQuantity} from './source';

const AS_OF = '2026-11-14';

function source(quantities: Record<number, SourceHoldingQuantity | null>): PlannerSource {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        asOf: AS_OF,
        targetCurrency: 'EUR',
        generatedAt,
        provenance: [{provenance_id: 'source:portfolio-ledger', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: generatedAt}],
        assets: [{asset_id: 'asset:11', source_asset_id: 11, name: 'Apple', ticker: 'AAPL', asset_class: 'STOCK', icon_url: null, active: true, provenance_id: 'source:asset-domain'}],
        brokers: Object.keys(quantities).map((id) => ({
            broker_id: `broker:${id}`,
            source_broker_id: Number(id),
            name: `Broker ${id}`,
            icon_url: null,
            access_role: 'OWNER',
            ownership_share: '1',
            observed_currencies: ['EUR'],
            active: true,
            operating_profile_status: 'not_available' as const,
            operating_profile: null,
            provenance_id: 'source:broker-domain',
        })),
        holdings: Object.entries(quantities).map(([id, quantity]) => ({holding_id: `holding:asset:11:broker:${id}`, asset_id: 'asset:11', broker_id: `broker:${id}`, provenance_id: 'source:portfolio-ledger', quantity})),
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

function copy(draft: PlannerDraft, snapshot: PlannerSource): number {
    const owned = ownedAssets(snapshot);
    return applyOwnedPositions(draft, snapshot, newCopyRecord(draft, 'positions', snapshot), owned.rows);
}

const ASSET = domainAssetKey(11);

describe('the user positions in the draft', () => {
    it('a first copy takes one position per Broker, the planning quantity from the user part', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        const added = copy(
            draft,
            source({
                7: {custody: '20', ownershipShare: '1', economic: '20'},
                8: {custody: '12', ownershipShare: '0.5', economic: '6'},
            }),
        );

        expect(added).toBe(2);
        expect(draft.asset(ASSET)).toBeDefined();
        const positions = draft.positionsOf(ASSET);
        expect(positions.map((item) => [item.brokerKey, item.brokerName, item.custody, item.ownershipShare, item.quantity, item.copiedQuantity])).toEqual([
            [domainBrokerKey(7), 'Broker 7', '20', '1', '20', '20'],
            [domainBrokerKey(8), 'Broker 8', '12', '0.5', '6', '6'],
        ]);
        expect(positions.every((item) => positionIsCopied(item) && item.stamp !== null)).toBe(true);
        expect(Object.keys(draft.data.copies)).toHaveLength(1);
    });

    it('an edited quantity reads modified; a second copy updates the copy only', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        copy(draft, source({7: {custody: '20', ownershipShare: '1', economic: '20'}}));
        const position = draft.positionsOf(ASSET)[0];
        position.quantity = '15';
        expect(positionIsCopied(draft.positionsOf(ASSET)[0])).toBe(false);

        // The same value written another way is still the copy.
        draft.positionsOf(ASSET)[0].quantity = '20.0';
        expect(positionIsCopied(draft.positionsOf(ASSET)[0])).toBe(true);
        draft.positionsOf(ASSET)[0].quantity = '15';

        const added = copy(draft, source({7: {custody: '25', ownershipShare: '1', economic: '25'}}));

        expect(added).toBe(0);
        expect(draft.positionsOf(ASSET).map((item) => [item.custody, item.quantity, item.copiedQuantity])).toEqual([['25', '15', '25']]);
        // One copy record left: the old one is pruned once no fact names it.
        expect(Object.keys(draft.data.copies)).toHaveLength(1);
    });

    it('a removed Asset takes its positions with it', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        copy(draft, source({7: {custody: '20', ownershipShare: '1', economic: '20'}}));

        draft.removeAsset(ASSET);

        expect(draft.data.positions).toEqual([]);
    });

    it('the PAC read keeps no quantity, so no position is copied', () => {
        const draft = new PlannerDraft('EUR', 'proportional');

        const added = copy(draft, source({7: null}));

        expect(added).toBe(0);
        expect(draft.data.positions).toEqual([]);
        expect(draft.asset(ASSET)).toBeDefined();
    });

    // Q-F3a-5c: before «Calculate» the positions are read again by the rule of the prices: only a quantity still equal to
    // its copy follows the source; one the user changed stays the user's; one the source no longer has keeps its copy.
    it('the re-read before «Calculate» updates the copied positions only', () => {
        const draft = new PlannerDraft('EUR', 'proportional', REBALANCER_PLANNER_PROFILE);
        copy(
            draft,
            source({
                7: {custody: '20', ownershipShare: '1', economic: '20'},
                8: {custody: '12', ownershipShare: '0.5', economic: '6'},
            }),
        );
        draft.positionsOf(ASSET).find((item) => item.sourceBrokerId === 8)!.quantity = '4';

        const plan = refreshPlan(draft);
        expect(plan?.positionKeys).toEqual(['holding:asset:11:broker:7']);
        const query = refreshQuery(draft, plan!, [7, 8]);
        expect(query.sections).toEqual(expect.arrayContaining(['holdings', 'assets', 'brokers']));
        expect(query.assetIds).toContain(11);

        const reread = source({7: {custody: '25', ownershipShare: '1', economic: '25'}, 8: {custody: '12', ownershipShare: '0.5', economic: '6'}});
        const summary = refreshCopiedFacts(draft, reread, plan!);

        expect(summary.positions).toBe(1);
        expect(draft.positionsOf(ASSET).map((item) => [item.sourceBrokerId, item.quantity, item.copiedQuantity])).toEqual([
            [7, '25', '25'],
            [8, '4', '6'],
        ]);
    });

    // Q-F3a-11 (a): for a holding, absence means zero: a copied, unedited position the source no longer has is closed.
    it("a copied position the re-read no longer finds goes to 0, an edited one stays the user's", () => {
        const draft = new PlannerDraft('EUR', 'proportional', REBALANCER_PLANNER_PROFILE);
        copy(
            draft,
            source({
                7: {custody: '20', ownershipShare: '1', economic: '20'},
                8: {custody: '12', ownershipShare: '0.5', economic: '6'},
            }),
        );
        draft.positionsOf(ASSET).find((item) => item.sourceBrokerId === 8)!.quantity = '4';
        const plan = refreshPlan(draft)!;

        const summary = refreshCopiedFacts(draft, {...source({}), holdings: []}, plan);

        expect(summary.closedPositions).toBe(1);
        expect(summary.positions).toBe(0);
        expect(summary.missing).toEqual([]);
        expect(draft.positionsOf(ASSET).map((item) => [item.sourceBrokerId, item.custody, item.quantity, item.copiedQuantity])).toEqual([
            [7, '0', '0', '0'],
            [8, '12', '4', '6'],
        ]);
        expect(draft.asset(ASSET)).toBeDefined();
    });
});
