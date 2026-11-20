// @vitest-environment jsdom
/**
 * The Review of the Rebalancer (F3a of project 67, step 13): counts and facts.
 *
 * Counts and labels only, never a sum (B16). Under the Rebalancer's profile the Review also counts:
 *   - the positions the request carries (`holdings`), and the Brokers that only hold them («positions only»);
 *   - the target entries: the Assets and the cash entries (a cash entry can carry a target), with the limits on all rows;
 *   - the strategy («Invest only») and the target fidelity;
 * and lists every position among the facts: «Asset · Broker», its quantity, copied until the user changes it. The draft's
 * fact counts (the side panel) count the same rows. The PAC's counts do not move. Real `PlannerDraft` and copies; nothing
 * reads translated text.
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
import ProfileHarness from '../__tests__/ProfileHarness.svelte';
import {applyOwnedPositions, newCopyRecord, ownedAssets} from './copies';
import {PlannerDraft, type DraftAsset} from './draft.svelte';
import {defaultPolicy} from './policies';
import {PAC_PLANNER_PROFILE, REBALANCER_PLANNER_PROFILE, type PlannerProfile} from './profile';
import {sectionCounts, snapshotFacts} from './review';
import SummaryPanel from './shell/SummaryPanel.svelte';
import type {PlannerSource} from './source';
import ReviewStep from './steps/ReviewStep.svelte';
import type {PlannerStep} from './types';

const AS_OF = '2026-11-14';

beforeAll(async () => {
    await setupI18n();
});

afterEach(() => {
    cleanup();
    setPrivacyEnabled(false);
});

function asset(draft: PlannerDraft, key: string, name: string): DraftAsset {
    const item: DraftAsset = {
        key,
        origin: 'manual',
        sourceAssetId: null,
        name,
        ticker: '',
        assetClass: 'etf',
        iconUrl: null,
        active: true,
        price: {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: AS_OF},
        priceManual: false,
        copiedPrice: null,
        priceStamp: null,
        priceSource: null,
        exposures: [],
        copiedExposures: null,
        exposureStamp: null,
        enteredAt: `${AS_OF}T10:00:00.000Z`,
    };
    draft.addAsset(item);
    return item;
}

function heldSource(): PlannerSource {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        asOf: AS_OF,
        targetCurrency: 'EUR',
        generatedAt,
        provenance: [
            {provenance_id: 'source:portfolio-ledger', domain: 'portfolio', source_ref: 'transactions', source_label: null, captured_at: generatedAt},
            {provenance_id: 'source:broker-domain', domain: 'broker', source_ref: 'brokers', source_label: null, captured_at: generatedAt},
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
        holdings: [{holding_id: 'holding:asset:11:broker:9', asset_id: 'asset:11', broker_id: 'broker:9', provenance_id: 'source:portfolio-ledger', quantity: {custody: '12', ownershipShare: '0.5', economic: '6'}}],
        cash: [],
        prices: [],
        classifications: [],
        fxQuotes: [],
        currentDistribution: null,
        issues: [],
    };
}

/** A manual Broker, two manual Assets with targets, the user's position at a Broker outside the scenario, a cash entry. */
function scenario(profile: PlannerProfile) {
    const draft = new PlannerDraft('EUR', defaultPolicy(profile), profile);
    draft.data.asOf = AS_OF;
    const broker = draft.addManualBroker('Broker probe');
    const first = asset(draft, 'asset:first', 'First probe');
    asset(draft, 'asset:second', 'Second probe');
    draft.data.targets[first.key] = '90';
    if (profile.positions) {
        const source = heldSource();
        applyOwnedPositions(draft, source, newCopyRecord(draft, 'positions', source), ownedAssets(source).rows);
        const entry = draft.addCashEntry(broker.key, 'EUR');
        draft.data.targets[entry.key] = '10';
        draft.setLimit(entry.key, 'maximum', '20%');
    }
    return draft;
}

describe('the Review of the Rebalancer', () => {
    it('counts the positions, the positions-only Brokers, the target entries and the fidelity', () => {
        const counts = sectionCounts(scenario(REBALANCER_PLANNER_PROFILE));
        expect(counts.assets.positions).toBe(1);
        expect(counts.brokers.positionsOnly).toBe(1);
        // Three Assets (the held one included) and one cash entry; two of them have a target, the cash entry a limit.
        expect(counts.targets).toEqual({entries: 4, count: 2, limited: 1});
        expect(counts.strategy).toEqual({policy: 'invest_only', fidelity: {kind: 'level', level: 'balanced'}});
    });

    it('the PAC counts as before: no position, no positions-only Broker, no fidelity, the Assets as entries', () => {
        const counts = sectionCounts(scenario(PAC_PLANNER_PROFILE));
        expect([counts.assets.positions, counts.brokers.positionsOnly, counts.strategy.fidelity]).toEqual([0, 0, null]);
        expect(counts.targets).toEqual({entries: 2, count: 1, limited: 0});
    });

    it('lists every position among the facts, copied until the user changes it, and the fact counts follow', () => {
        const draft = scenario(REBALANCER_PLANNER_PROFILE);
        const position = draft.data.positions[0];
        const fact = () => snapshotFacts(draft).find((item) => item.kind === 'position');
        expect(fact()).toMatchObject({
            id: `position|${position.key}`,
            step: 'assets',
            entity: 'Held probe · Held broker probe',
            subject: {type: 'position', assetKey: 'asset:11', brokerKey: 'broker:9'},
            origin: 'copied',
            modified: false,
            value: {kind: 'quantity', quantity: '6'},
        });
        const before = draft.factCounts;

        position.quantity = '5';
        expect(fact()).toMatchObject({modified: true, value: {kind: 'quantity', quantity: '5'}});
        expect([draft.factCounts.copied, draft.factCounts.modified]).toEqual([before.copied - 1, before.modified + 1]);
    });

    it('the PAC lists no position', () => {
        expect(snapshotFacts(scenario(PAC_PLANNER_PROFILE)).some((item) => item.kind === 'position')).toBe(false);
    });
});

/** The side panel's rows at `step`: each row's id, and its value where `withValues` names it. */
function summaryRows(profile: PlannerProfile, step: PlannerStep, withValues: readonly string[] = []): string[] {
    const draft = scenario(profile);
    render(ProfileHarness, {props: {profile: profile === PAC_PLANNER_PROFILE ? null : profile, child: SummaryPanel, childProps: {draft, step, apiVersion: '2.0.0', uiVersion: '1.0.0'}}});
    flushSync();
    const rows = screen.getAllByTestId(`${profile.testIdPrefix}-summary-row`).map((row) => {
        const id = row.getAttribute('data-row') ?? '';
        return withValues.includes(id) ? `${id}=${row.querySelector('dd')?.textContent?.trim()}` : id;
    });
    cleanup();
    return rows;
}

function mountReview(profile: PlannerProfile, draft: PlannerDraft): void {
    render(ProfileHarness, {
        props: {profile: profile === PAC_PLANNER_PROFILE ? null : profile, child: ReviewStep, childProps: {draft, problems: [], busy: false, hasResult: false, ongoto: vi.fn(), oncalculate: vi.fn(), onshowresult: vi.fn()}},
    });
    flushSync();
}

describe('the Review and the side panel on screen', () => {
    it('the side panel counts positions, positions-only Brokers, entries and the fidelity; the PAC keeps its rows', () => {
        // An external account (a manual account in Liquidity) the Rebalancer has too; no funding route.
        expect(summaryRows(REBALANCER_PLANNER_PROFILE, 'brokers', ['positions-only'])).toEqual(['operative', 'positions-only=1', 'funding-only', 'modes']);
        expect(summaryRows(REBALANCER_PLANNER_PROFILE, 'assets', ['positions'])).toEqual(['assets', 'positions=1', 'prices', 'stale', 'exposures']);
        expect(summaryRows(REBALANCER_PLANNER_PROFILE, 'targets', ['entries', 'limits'])).toEqual(['entries=4', 'total', 'limits=1']);
        expect(summaryRows(REBALANCER_PLANNER_PROFILE, 'strategy')).toEqual(['policy', 'fidelity']);
        expect(summaryRows(PAC_PLANNER_PROFILE, 'brokers')).toEqual(['operative', 'funding-only', 'modes', 'funding-routes']);
        expect(summaryRows(PAC_PLANNER_PROFILE, 'assets')).toEqual(['assets', 'prices', 'stale', 'exposures']);
        expect(summaryRows(PAC_PLANNER_PROFILE, 'targets')).toEqual(['assets', 'total', 'limits']);
        expect(summaryRows(PAC_PLANNER_PROFILE, 'strategy')).toEqual(['policy']);
    });

    it('the strategy is named, never shown as its wire code; the Review and the panel say the same', () => {
        const draft = scenario(REBALANCER_PLANNER_PROFILE);
        render(ProfileHarness, {props: {profile: REBALANCER_PLANNER_PROFILE, child: SummaryPanel, childProps: {draft, step: 'strategy', apiVersion: '2.0.0', uiVersion: '1.0.0'}}});
        flushSync();
        const panel = screen.getByTestId('rebalancer-planner-summary');
        expect(panel.textContent).not.toMatch(/invest_only|balanced|cost_aware/);
        const value = (id: string) => panel.querySelector(`[data-row="${id}"] dd`)?.textContent?.trim() ?? '';
        const [strategy, fidelity] = [value('policy'), value('fidelity')];
        expect([strategy, fidelity].every((text) => text !== '' && text !== '—')).toBe(true);
        cleanup();

        mountReview(REBALANCER_PLANNER_PROFILE, draft);
        const section = screen.getAllByTestId('rebalancer-planner-review-section').find((cell) => cell.getAttribute('data-step') === 'strategy');
        expect(section).toBeDefined();
        const text = section!.closest('tr')!.textContent ?? '';
        expect(text).not.toMatch(/invest_only|balanced/);
        expect(text).toContain(strategy);
        expect(text).toContain(fidelity);
    });

    it('the PAC Review renders as before: its sections, its facts, no position', async () => {
        const draft = scenario(PAC_PLANNER_PROFILE);
        mountReview(PAC_PLANNER_PROFILE, draft);
        expect(screen.getAllByTestId('pac-planner-review-section').map((cell) => cell.getAttribute('data-step'))).toEqual(['scenario', 'liquidity', 'brokers', 'assets', 'routing', 'targets', 'strategy']);
        await fireEvent.click(screen.getByTestId('pac-planner-review-facts-toggle'));
        flushSync();
        const kinds = screen.getAllByTestId('pac-planner-review-fact').map((cell) => cell.getAttribute('data-kind'));
        expect(kinds.length).toBeGreaterThan(0);
        expect(kinds).not.toContain('position');
    });

    it('a position is a fact of the Review, its quantity masked in privacy mode, both ways', async () => {
        const draft = scenario(REBALANCER_PLANNER_PROFILE);
        mountReview(REBALANCER_PLANNER_PROFILE, draft);
        await fireEvent.click(screen.getByTestId('rebalancer-planner-review-facts-toggle'));
        flushSync();
        const fact = screen.getAllByTestId('rebalancer-planner-review-fact').find((cell) => cell.getAttribute('data-kind') === 'position');
        expect(fact).toBeDefined();
        expect(fact!.getAttribute('data-origin')).toBe('librefolio');
        const row = () =>
            screen
                .getAllByTestId('rebalancer-planner-review-fact')
                .find((cell) => cell.getAttribute('data-kind') === 'position')!
                .closest('tr')!;

        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(row().textContent).toContain(PRIVACY_PLACEHOLDER);

        setPrivacyEnabled(false);
        flushSync();
        await tick();
        expect(row().textContent).not.toContain(PRIVACY_PLACEHOLDER);
        expect(row().textContent).toContain('6');
    });
});
