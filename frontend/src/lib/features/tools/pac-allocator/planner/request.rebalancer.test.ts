// @vitest-environment jsdom
/**
 * The Rebalancer's request, «Invest only» (F3a of project 67, step 11; contract 2.0.0 §5.2, §5.4; Vitest + jsdom).
 *
 * Subject. Under the Rebalancer's profile `buildRequest` writes the request of `portfolio_rebalancer`, checked by its own
 * compiled codec:
 *   - `policy: invest_only` always (S1: no draft produces `invest_and_sell` before F3b) and the target fidelity (a level,
 *     `custom` with the λ the draft keeps, or `target_first`; «Balanced» by default);
 *   - the user's positions as `holdings` (custody, share, planning quantity); a copied position the user changed travels
 *     as manual;
 *   - the targets as entries: the Assets and the cash entries (weight, minimum, maximum in both forms);
 *   - **no funding route**, whatever the draft holds (contract §5.4);
 *   - a Broker that only holds positions (not among the scenario's Brokers) travels with its identity and no order mode:
 *     it can hold, it cannot buy (Q-F3a-5b, the consultant's (a)); no route touches it;
 *   - no `tax` section (F3b).
 * The PAC's request is unchanged (its own tests, `request.test.ts`). A holding issue belongs to the Assets step.
 *
 * Drafts are built through the real `PlannerDraft` API and the real copies; nothing reads translated text.
 */
import {describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import {applyOwnedPositions, newCopyRecord, ownedAssets} from './copies';
import {PlannerDraft, cashEntryKey, routeKey, type DraftAsset} from './draft.svelte';
import {defaultPolicy} from './policies';
import {REBALANCER_PLANNER_PROFILE} from './profile';
import {buildRequest, localProblems, stepOfWirePath} from './request';
import type {PlannerSource} from './source';

const NOW = new Date('2026-11-14T12:00:00Z');
const AS_OF = '2026-11-14';
const codec = toolContractMap.portfolio_rebalancer['2.0.0'].input;

type Wire = Record<string, unknown>;

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

/** A source answering one held Asset (asset:11) at Broker 9, which is not among the scenario's Brokers. */
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

/**
 * One operative manual Broker buying in EUR, a manual account and a contribution (sources the PAC would route), two manual
 * Assets at 60 % + 30 %, a cash entry at 10 % with limits, and the user's position in a held Asset at another Broker.
 */
function scenario() {
    const draft = new PlannerDraft('EUR', defaultPolicy(REBALANCER_PLANNER_PROFILE), REBALANCER_PLANNER_PROFILE);
    draft.data.asOf = AS_OF;
    const broker = draft.addManualBroker('Broker probe');
    draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
    const contribution = draft.addContribution('EUR', 'Salary probe');
    draft.contribution(contribution.key)!.amount = '200';
    const first = asset(draft, 'asset:first', 'First probe');
    const second = asset(draft, 'asset:second', 'Second probe');
    const source = heldSource();
    applyOwnedPositions(draft, source, newCopyRecord(draft, 'positions', source), ownedAssets(source).rows);
    draft.asset('asset:11')!.price = {amount: '20', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: AS_OF};
    const entry = draft.addCashEntry(broker.key, 'EUR');
    draft.data.targets[first.key] = '60';
    draft.data.targets[second.key] = '30';
    draft.data.targets[entry.key] = '10';
    draft.setLimit(entry.key, 'minimum', '500');
    draft.setLimit(entry.key, 'maximum', '20%');
    return {draft, brokerKey: broker.key, entryKey: entry.key, first, second};
}

function build(draft: PlannerDraft): Wire {
    const outcome = buildRequest(draft, NOW);
    expect(outcome.ok ? [] : outcome.problems.map((problem) => `${problem.step}:${problem.id}`)).toEqual([]);
    if (!outcome.ok) throw new Error('unreachable');
    expect(outcome.built.resolved).toEqual(codec.parse(outcome.built.request));
    return outcome.built.request as unknown as Wire;
}

describe('the Rebalancer request, «Invest only»', () => {
    it('invest_only sends positions and buy routes, no tax section, and passes its own codec', () => {
        const {draft, first} = scenario();
        const wire = build(draft);

        expect(wire.policy).toBe('invest_only');
        expect(wire).not.toHaveProperty('tax');
        expect(wire.holdings).toEqual([
            {
                holding_id: 'holding:asset:11:broker:9',
                asset_id: 'asset:11',
                broker_id: 'broker:9',
                custody_quantity: '12',
                economic_share: '0.5',
                planning_quantity: '6',
                quantity_unit: 'asset_unit',
                provenance_id: expect.stringMatching(/source:portfolio-ledger$/),
            },
        ]);
        const routes = wire.order_routes as Wire[];
        expect(routes.length).toBeGreaterThan(0);
        expect(routes.every((route) => route.side === 'buy')).toBe(true);
        expect(routes.map((route) => route.asset_id)).toContain(first.key);
    });

    it('the rebalancer request declares no funding routes', () => {
        const {draft} = scenario();
        const wire = build(draft);

        expect(wire).not.toHaveProperty('funding_routes');
        // The sources are still in the request: every cash reaches every Broker.
        expect((wire.existing_cash as Wire[]).length).toBe(1);
        expect((wire.contributions as Wire[]).length).toBe(1);
    });

    it('cash entries carry weight, minimum and maximum', () => {
        const {draft, brokerKey, entryKey} = scenario();
        const wire = build(draft);

        const entries = wire.target_weights as Wire[];
        expect(entries.map((entry) => entry.kind)).toEqual(['asset', 'asset', 'asset', 'cash']);
        expect(entries.find((entry) => entry.kind === 'cash')).toEqual({
            kind: 'cash',
            broker_id: brokerKey,
            currency: 'EUR',
            weight: '0.1',
            minimum: {kind: 'amount', amount: {amount: '500', currency: 'EUR'}},
            maximum: {kind: 'share', share: '0.2'},
        });
        expect(draft.data.limits[entryKey]).toBeDefined();
        // The held Asset has no target typed: it goes with weight 0.
        expect(entries.find((entry) => entry.asset_id === 'asset:11')).toEqual({kind: 'asset', asset_id: 'asset:11', weight: '0'});
    });

    it('targets total counts assets and cash entries', () => {
        const {draft, entryKey} = scenario();
        draft.data.targets[entryKey] = '';

        expect(localProblems(draft).map((problem) => problem.key)).toContain('targetTotalNotHundred');
        draft.data.targets[entryKey] = '10';
        expect(localProblems(draft).map((problem) => problem.key)).not.toContain('targetTotalNotHundred');
    });

    it('fidelity travels as level, custom or target_first; «Balanced» by default', () => {
        const {draft} = scenario();
        expect(build(draft).target_fidelity).toEqual({kind: 'level', level: 'balanced'});

        draft.data.fidelity = {kind: 'level', level: 'cost_aware'};
        expect(build(draft).target_fidelity).toEqual({kind: 'level', level: 'cost_aware'});
        draft.data.fidelity = {kind: 'custom', lambda: '0.0123'};
        expect(build(draft).target_fidelity).toEqual({kind: 'custom', lambda: '0.0123'});
        draft.data.fidelity = {kind: 'target_first'};
        expect(build(draft).target_fidelity).toEqual({kind: 'target_first'});
    });

    it('the rebalancer request is always invest_only before F3b', () => {
        const {draft} = scenario();
        draft.data.policy = 'invest_and_sell';

        expect(build(draft).policy).toBe('invest_only');
    });

    it('a copied position edited by the user travels as manual', () => {
        const {draft} = scenario();
        draft.data.positions[0].quantity = '4';
        const wire = build(draft);

        const holding = (wire.holdings as Wire[])[0];
        expect(holding.planning_quantity).toBe('4');
        expect(holding.custody_quantity).toBe('12');
        const provenance = (wire.provenance as Wire[]).find((item) => item.provenance_id === holding.provenance_id);
        expect(provenance?.kind).toBe('manual');
    });

    it('a Broker with positions only travels without order modes, and no route touches it', () => {
        const {draft} = scenario();
        const wire = build(draft);

        const held = (wire.brokers as Wire[]).find((broker) => broker.broker_id === 'broker:9');
        expect(held).toMatchObject({broker_id: 'broker:9', identity: {kind: 'domain_broker', source_broker_id: '9', name: 'Held broker probe', active: true}, conversion_mode: 'automatic'});
        expect(held).not.toHaveProperty('capabilities');
        expect(held).not.toHaveProperty('fee_schedules');
        expect((wire.order_routes as Wire[]).some((route) => route.broker_id === 'broker:9')).toBe(false);
        expect(draft.data.routes[routeKey('asset:11', 'broker:9')]).toBeUndefined();
    });

    it('a position quantity that is not a number stops the request on the Assets step', () => {
        const {draft} = scenario();
        draft.data.positions[0].quantity = 'abc';

        expect(localProblems(draft).map((problem) => `${problem.step}:${problem.key}`)).toContain('assets:positionQuantityInvalid');
    });

    it('holding issues go to Assets', () => {
        expect(stepOfWirePath(['holdings', 0, 'planning_quantity'])).toBe('assets');
    });

    it('the preview sends «Balanced» whatever the fidelity; the plan sends the draft λ and refuses a «Custom» without one', () => {
        const {draft, entryKey} = scenario();
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        // An incomplete total: the preview builds anyway.
        draft.data.targets[entryKey] = '';

        // R1-F (b): no number of the preview depends on the fidelity, and the page keys it without it.
        for (const fidelity of [{kind: 'custom', lambda: ''}, {kind: 'custom', lambda: '0.0123'}, {kind: 'target_first'}, {kind: 'level', level: 'faithful'}] as const) {
            draft.data.fidelity = fidelity;
            const preview = buildRequest(draft, NOW, {operation: 'preview'});
            expect(preview.ok ? [] : preview.problems.map((problem) => problem.key)).toEqual([]);
            if (!preview.ok) return;
            expect(preview.built.request).toMatchObject({operation: 'preview', target_fidelity: {kind: 'level', level: 'balanced'}});
            expect(preview.built.request).not.toHaveProperty('custom_reference_amount');
        }

        draft.data.targets[entryKey] = '10';
        draft.data.fidelity = {kind: 'custom', lambda: ''};
        const plan = buildRequest(draft, NOW);
        // Step 10b: the plan refuses it as a problem of the Strategy step, the field's (no longer a structure error).
        expect(plan.ok ? [] : plan.problems.map((problem) => `${problem.step}:${problem.key}`)).toEqual(['strategy:fidelityCustomMissing']);
        draft.data.fidelity = {kind: 'custom', lambda: '0.0123'};
        const planned = buildRequest(draft, NOW);
        expect(planned.ok && planned.built.request).toMatchObject({target_fidelity: {kind: 'custom', lambda: '0.0123'}});
    });
});
