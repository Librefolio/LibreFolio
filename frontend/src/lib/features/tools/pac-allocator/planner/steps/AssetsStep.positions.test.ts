// @vitest-environment jsdom
/**
 * The Assets step and the positions (F3a of project 67, step 5): under the Rebalancer's profile each Asset's card shows
 * its positions table; under the PAC's it never does, whatever the draft holds. Mounted below a Tool wrapper in miniature
 * (`../../__tests__/ProfileHarness.svelte`). The Asset is a manual one, so the step reads nothing from LibreFolio; the
 * asset catalogue answers empty. Driven through test ids.
 */
import {flushSync} from 'svelte';
import {writable} from 'svelte/store';
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));
vi.mock('$lib/stores/reference/assetStore', () => ({
    assetStoreVersion: writable(0),
    ensureAssetsLoaded: vi.fn(async () => undefined),
    getAllAssets: () => [],
    getAssetInfo: () => undefined,
}));

import {cleanup, render, screen, setupI18n} from '$test/component';
import ProfileHarness from '../../__tests__/ProfileHarness.svelte';
import {PlannerDraft, type DraftAsset} from '../draft.svelte';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from '../profile';
import AssetsStep from './AssetsStep.svelte';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => cleanup());

function draftWithAPosition(profile: PlannerProfile): PlannerDraft {
    const draft = new PlannerDraft('EUR', 'proportional', profile);
    const asset: DraftAsset = {
        key: 'asset:probe',
        origin: 'manual',
        sourceAssetId: null,
        name: 'Probe Asset',
        ticker: 'PRB',
        assetClass: 'STOCK',
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
        enteredAt: '2026-11-14T10:00:00Z',
    };
    draft.addAsset(asset);
    draft.data.positions.push({
        key: 'holding:probe:broker:7',
        assetKey: asset.key,
        brokerKey: 'broker:7',
        sourceBrokerId: 7,
        brokerName: 'Broker probe',
        brokerIconUrl: null,
        custody: '20',
        ownershipShare: '1',
        quantity: '20',
        copiedQuantity: '20',
        accessRole: 'OWNER',
        stamp: {copyId: 'copy:1', provenanceId: 'source:portfolio-ledger'},
        enteredAt: '2026-11-14T10:00:00Z',
    });
    return draft;
}

function mount(profile: PlannerProfile | null): void {
    render(ProfileHarness, {props: {profile, child: AssetsStep, childProps: {draft: draftWithAPosition(profile ?? PAC_PLANNER_PROFILE), accountGeneration: 0}}});
    flushSync();
}

describe('the Assets step and the positions', () => {
    it('the Rebalancer shows the positions under the Asset', () => {
        mount(REBALANCER_PLANNER_PROFILE);

        expect(screen.getByTestId('rebalancer-planner-asset')).toBeTruthy();
        expect(screen.getByTestId('rebalancer-planner-positions').getAttribute('data-asset-key')).toBe('asset:probe');
    });

    it('the PAC never shows a positions table', () => {
        mount(null);

        expect(screen.getByTestId('pac-planner-asset')).toBeTruthy();
        expect(screen.queryByTestId('pac-planner-positions')).toBeNull();
    });
});
