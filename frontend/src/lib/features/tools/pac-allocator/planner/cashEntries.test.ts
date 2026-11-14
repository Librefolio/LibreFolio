// @vitest-environment jsdom
/**
 * Cash entries in the targets (F3a of project 67, step 7; contract §5.2, M12; Vitest + jsdom).
 *
 * Subject. The Rebalancer's targets are a list of entries of two kinds: an Asset, and a Broker's cash in one currency. A
 * cash entry has a target and the limits of F2, kept in the same maps as an Asset's (`targets`, `limits`) under the
 * entry's own key. The user adds it, choosing among the Broker × currency pairs the scenario has: a cash row of the
 * Liquidity step, or a currency an operative Broker buys in. The total of the control percentages counts Assets **and**
 * cash entries. Removing an entry, or its Broker, takes its target and limits with it. The PAC has no cash entry in F3a
 * (its limits-only cash rows come with step 14).
 *
 * Environment. jsdom for the compile target, not for the DOM (see `request.test.ts`).
 */
import {describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {PlannerDraft, cashEntryKey, type DraftAsset, type DraftBroker} from './draft.svelte';
import {limitProblems} from './request';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE} from './profile';

function manualAsset(draft: PlannerDraft, name: string): DraftAsset {
    const asset: DraftAsset = {
        key: draft.nextId('manual-asset'),
        origin: 'manual',
        sourceAssetId: null,
        name,
        ticker: '',
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: '2026-11-14'},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: '2026-11-14T10:00:00.000Z',
    };
    draft.addAsset(asset);
    return asset;
}

/** An operative Broker buying in EUR and USD, a manual account in CHF, one Asset. */
function scenario(profile = REBALANCER_PLANNER_PROFILE) {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const broker = draft.addManualBroker('Broker probe');
    draft.broker(broker.key)!.modes = [...draft.defaultModes(['EUR', 'USD'])];
    const account = draft.addManualAccount({name: 'Bank probe', currency: 'CHF', available: '100', selected: '50'});
    const asset = manualAsset(draft, 'ETF probe');
    return {draft, brokerKey: broker.key, accountKey: account.brokerKey, asset};
}

describe('cash entries in the targets', () => {
    it('the choices are the scenario cash rows and the currencies an operative Broker buys in', () => {
        const {draft, brokerKey, accountKey} = scenario();

        expect(draft.cashEntryChoices.map((choice) => [choice.brokerKey, choice.currency])).toEqual([
            [brokerKey, 'EUR'],
            [brokerKey, 'USD'],
            [accountKey, 'CHF'],
        ]);

        draft.addCashEntry(brokerKey, 'USD');
        // A pair already an entry is not offered again, and adding it twice adds nothing.
        expect(draft.cashEntryChoices.map((choice) => choice.currency)).toEqual(['EUR', 'CHF']);
        draft.addCashEntry(brokerKey, 'USD');
        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([cashEntryKey(brokerKey, 'USD')]);
    });

    it('the total counts the Assets and the cash entries', () => {
        const {draft, brokerKey, asset} = scenario();
        const entry = draft.addCashEntry(brokerKey, 'EUR');

        draft.data.targets[asset.key] = '90';
        draft.data.targets[entry.key] = '10';

        expect(draft.targetTotal).toBe('100');
        expect(draft.targetRows.map((row) => [row.kind, row.key])).toEqual([
            ['asset', asset.key],
            ['cash', entry.key],
        ]);
    });

    it('a cash entry takes the limits of F2, checked with the Assets', () => {
        const {draft, brokerKey} = scenario();
        const entry = draft.addCashEntry(brokerKey, 'EUR');

        draft.setLimit(entry.key, 'minimum', '3000');
        draft.setLimit(entry.key, 'maximum', '2000');

        expect(limitProblems(draft).map((problem) => [problem.key, problem.assetKey])).toEqual([['limitMinAboveMax', entry.key]]);
    });

    it('removing an entry, or its Broker, removes its target and limits', () => {
        const {draft, brokerKey, accountKey} = scenario();
        const first = draft.addCashEntry(brokerKey, 'EUR');
        const second = draft.addCashEntry(accountKey, 'CHF');
        draft.data.targets[first.key] = '5';
        draft.setLimit(first.key, 'maximum', '2000');
        draft.data.targets[second.key] = '5';

        draft.removeCashEntry(first.key);
        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([second.key]);
        expect(draft.data.targets).not.toHaveProperty(first.key);
        expect(draft.data.limits).not.toHaveProperty(first.key);

        draft.removeBroker(accountKey);
        expect(draft.data.cashEntries).toEqual([]);
        expect(draft.data.targets).not.toHaveProperty(second.key);
    });

    it('the PAC offers cash rows too, with limits only: their figure never counts in the total (step 14, U8)', () => {
        const {draft, brokerKey, asset} = scenario(PAC_PLANNER_PROFILE);
        draft.data.targets[asset.key] = '100';

        expect(draft.cashEntryChoices.map((choice) => choice.currency)).toContain('EUR');
        const entry = draft.addCashEntry(brokerKey, 'EUR');
        expect(draft.targetRows.map((row) => row.kind)).toContain('cash');
        draft.data.targets[entry.key] = '5';
        expect(draft.targetTotal).toBe('100');
    });

    it('an entry whose pair leaves the scenario goes with it', () => {
        const {draft, brokerKey, accountKey} = scenario();
        const usd = draft.addCashEntry(brokerKey, 'USD');
        const eur = draft.addCashEntry(brokerKey, 'EUR');
        const chf = draft.addCashEntry(accountKey, 'CHF');
        draft.data.targets[usd.key] = '5';

        // «Configure …» drops the USD block: no USD mode and no USD cash at that Broker any more.
        const next = JSON.parse(JSON.stringify(draft.broker(brokerKey))) as DraftBroker;
        next.modes = next.modes.filter((mode) => mode.currency !== 'USD');
        draft.replaceBroker(next);
        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([eur.key, chf.key]);
        expect(draft.data.targets).not.toHaveProperty(usd.key);

        // The manual account's only cash card is removed in Liquidity.
        draft.removeCash(draft.data.cash.find((cash) => cash.brokerKey === accountKey)!.key);
        expect(draft.data.cashEntries.map((entry) => entry.key)).toEqual([eur.key]);
    });

    it('the Broker removal confirmation lists its cash entries', () => {
        const {draft, brokerKey} = scenario();
        const eur = draft.addCashEntry(brokerKey, 'EUR');

        expect(draft.brokerRemovalImpact(brokerKey).cashEntries?.map((entry) => entry.key)).toEqual([eur.key]);
    });
});
