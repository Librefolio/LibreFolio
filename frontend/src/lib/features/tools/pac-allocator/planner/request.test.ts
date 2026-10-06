// @vitest-environment jsdom
/**
 * buildRequest: the compact wire and the resolved request (Vitest + jsdom).
 *
 * Subject. The PAC planner contract has schema defaults (plan-phase00PacContractCompaction §1-§3).
 * The builder sends the *compact* body:
 *   - it leaves out every value equal to its schema default;
 *   - the withdrawn fields are gone (`quote.reference_date`, `quote.freshness`, the cash `source_kind`);
 *   - a BUY mode whose fees are all zero sends no fee schedule, and its route sends no
 *     `fee_schedule_id`;
 *   - a mode with fees sends its schedule without the zero fields, so a rate-only schedule has
 *     no currency at all (F1-extended, §3).
 * `BuiltRequest.resolved` is the codec's parsed output for that body, with the defaults filled.
 * The result views read it.
 *
 * Expectations.
 *   - Wire objects are compared as exact own-key sets: an extra default fails, and so does a
 *     missing required value.
 *   - Every wire body must survive a JSON round trip unchanged. The tool client refuses an
 *     `undefined` value (`clonePlainJson`), so leaving the key out is the only way to omit it.
 *   - `resolved` is checked against the generated codec itself (`codec.parse(request)`) and
 *     against the default values the schema declares.
 *   - Some values look like defaults but are required: a `null` ticker, a zero target weight
 *     (§2.4, §5). They stay on the wire. That case is a guard, and it is green before the
 *     compaction too.
 *
 * Drafts. Every scenario is built through the real `PlannerDraft` API, as the wizard builds it.
 * Edits go through `draft.data` and its lookups, which return the `$state` proxies; the objects
 * returned by the `add*` methods are not used for edits. Nothing here reads translated text:
 * a local problem is reported by its id.
 *
 * Environment. jsdom is here for the compile target, not for the DOM.
 *   - In the node environment Vitest compiles `draft.svelte.ts` for the server.
 *   - There a `$derived` is computed on first read and never again
 *     (`svelte/internal/server` `derived` = `once(fn)`).
 *   - `operativeBrokers`, `targetTotal`, the FX closure and the fingerprint would then stay
 *     frozen at their first read. The client build keeps them live.
 */
import {describe, expect, it, vi} from 'vitest';

// source.ts and the tool client import the API client. Nothing here talks to a server.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {toolContractMap} from '$lib/api/tool-contract-map.generated';
import {draftAssetFromInfo} from './copies';
import {PlannerDraft, priceIsCopied, routeKey, type DraftAsset, type DraftFunding, type DraftMode} from './draft.svelte';
import {buildRequest, capabilityId, feeScheduleId, type BuiltRequest} from './request';

const NOW = new Date('2026-09-16T12:00:00Z');
const AS_OF = '2026-09-16';
const codec = toolContractMap.pac_allocator['1.0.0'].input;
/** The `none` variant every minimum, route cap and variable fee cap defaults to. */
const NONE = {kind: 'none'};

type WireObject = Record<string, unknown>;

function asObject(value: unknown): WireObject {
    expect(value !== null && typeof value === 'object' && !Array.isArray(value)).toBe(true);
    return value as WireObject;
}

function asList(value: unknown): WireObject[] {
    expect(Array.isArray(value)).toBe(true);
    return value as WireObject[];
}

/** Own keys, sorted: the exact shape of one wire object. */
function keysOf(value: unknown): string[] {
    return Object.keys(asObject(value)).sort();
}

/** The one item of `list` whose `field` is `id`: found by identity, never by position. */
function itemBy(list: unknown, field: string, id: string): WireObject {
    const matches = asList(list).filter((item) => item[field] === id);
    expect(matches).toHaveLength(1);
    return matches[0];
}

/** The one funding route fed by the cash row or the contribution `sourceKey`. */
function fundingFrom(list: unknown, sourceKey: string): WireObject {
    const matches = asList(list).filter((item) => {
        const source = asObject(item.source);
        return source.cash_id === sourceKey || source.contribution_id === sourceKey;
    });
    expect(matches).toHaveLength(1);
    return matches[0];
}

function build(draft: PlannerDraft): BuiltRequest {
    const outcome = buildRequest(draft, NOW);
    expect(outcome.ok ? [] : outcome.problems.map((problem) => problem.id)).toEqual([]);
    if (!outcome.ok) throw new Error('unreachable: the local problems were asserted empty above');
    return outcome.built;
}

/** The body the client sends: plain JSON, with no `undefined` anywhere, because the client refuses one. */
function wireOf(built: BuiltRequest): WireObject {
    const request = asObject(built.request);
    expect(JSON.parse(JSON.stringify(request))).toStrictEqual(request);
    return request;
}

/** `resolved` is the codec's own output for the body that is sent. */
function resolvedOf(built: BuiltRequest): WireObject {
    expect(built.resolved).toEqual(codec.parse(built.request));
    return asObject(built.resolved);
}

function manualAsset(draft: PlannerDraft, name: string): DraftAsset {
    return {
        key: draft.nextId('manual-asset'),
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
        enteredAt: NOW.toISOString(),
    };
}

interface Scenario {
    draft: PlannerDraft;
    brokerKey: string;
    assetKey: string;
}

/** One manual Broker with the mode the wizard gives it (EUR, whole units, every fee zero) and one manual Asset priced in EUR. */
function baseScenario(): Scenario {
    const draft = new PlannerDraft('EUR', 'proportional');
    draft.data.asOf = AS_OF;
    const brokerKey = draft.addManualBroker('Broker probe').key;
    const asset = manualAsset(draft, 'Manual ETF probe');
    draft.addAsset(asset);
    draft.data.targets[asset.key] = '100';
    return {draft, brokerKey, assetKey: asset.key};
}

/** `baseScenario` funded by a manual account: manual cash on a funding-only Broker, with an empty transfer cap. */
function cashScenario(): Scenario & {cashKey: string; accountBrokerKey: string} {
    const scenario = baseScenario();
    const cash = scenario.draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
    return {...scenario, cashKey: cash.key, accountBrokerKey: cash.brokerKey};
}

/** The Broker's EUR mode, as the live `$state` proxy. */
function eurMode(draft: PlannerDraft, brokerKey: string): DraftMode {
    const modes = draft.broker(brokerKey)?.modes.filter((mode) => mode.currency === 'EUR') ?? [];
    expect(modes).toHaveLength(1);
    return modes[0];
}

/** The Broker's funding entry for one cash row or contribution, as the live `$state` proxy. */
function fundingEntry(draft: PlannerDraft, brokerKey: string, sourceKey: string): DraftFunding {
    const entries = (draft.broker(brokerKey)?.funding ?? []).filter((item) => (item.source.kind === 'cash' ? item.source.cashKey : item.source.contributionKey) === sourceKey);
    expect(entries).toHaveLength(1);
    return entries[0];
}

function routeWireId(draft: PlannerDraft, assetKey: string, brokerKey: string): string {
    const route = draft.data.routes[routeKey(assetKey, brokerKey)];
    expect(route).toBeDefined();
    return route.wireId;
}

describe('buildRequest: an all-default scenario', () => {
    it('sends the compact wire: no default, no withdrawn field, no all-zero fee schedule', () => {
        const {draft, brokerKey, assetKey, cashKey, accountBrokerKey} = cashScenario();
        // Precondition: every value below is the default the wizard starts from.
        const mode = eurMode(draft, brokerKey);
        expect(mode).toMatchObject({kind: 'whole_quantity', fixedFee: '0', ratePercent: '0', floor: '0', cap: ''});
        expect(draft.data.routes[routeKey(assetKey, brokerKey)]).toMatchObject({enabled: true, priority: '0', minimumIfActive: '', requiredMinimum: '', cap: '', marginPercent: '0'});
        expect(fundingEntry(draft, brokerKey, cashKey)).toMatchObject({enabled: true, priority: '0', cap: ''});
        expect(draft.data.fxSpreadPercent).toBe('0');
        expect(draft.requiredPairs).toEqual([]);

        const request = wireOf(build(draft));
        expect(keysOf(request)).toEqual(['as_of', 'assets', 'brokers', 'existing_cash', 'funding_routes', 'operation', 'order_routes', 'policy', 'provenance', 'snapshot', 'target_weights', 'valuation_currency']);

        const asset = itemBy(request.assets, 'asset_id', assetKey);
        expect(keysOf(asset)).toEqual(['asset_id', 'identity', 'quote']);
        expect(asset.identity).toStrictEqual({kind: 'manual_asset', name: 'Manual ETF probe', ticker: null, asset_class: 'etf'});
        expect(keysOf(asset.quote)).toEqual(['amount', 'currency', 'provenance_id', 'quote_base_quantity']);

        const broker = itemBy(request.brokers, 'broker_id', brokerKey);
        expect(keysOf(broker)).toEqual(['broker_id', 'capabilities', 'conversion_mode', 'identity', 'provenance_id']);
        expect(asList(broker.capabilities).map((capability) => capability.capability_id)).toEqual([capabilityId(brokerKey, mode)]);
        expect(keysOf(itemBy(request.brokers, 'broker_id', accountBrokerKey))).toEqual(['broker_id', 'conversion_mode', 'identity', 'provenance_id']);

        expect(keysOf(itemBy(request.existing_cash, 'cash_id', cashKey))).toEqual(['available', 'broker_id', 'cash_id', 'provenance_id', 'selected']);

        const funding = fundingFrom(request.funding_routes, cashKey);
        expect(keysOf(funding)).toEqual(['broker_id', 'currency', 'funding_route_id', 'provenance_id', 'source']);
        expect(funding.source).toStrictEqual({kind: 'existing_cash', cash_id: cashKey});

        const route = itemBy(request.order_routes, 'route_id', routeWireId(draft, assetKey, brokerKey));
        expect(keysOf(route)).toEqual(['asset_id', 'broker_id', 'capability_id', 'provenance_id', 'route_id', 'side']);
        expect(route.side).toBe('buy');
    });

    it('resolves every omitted value to its schema default, and invents no fee schedule', () => {
        const {draft, brokerKey, assetKey, cashKey, accountBrokerKey} = cashScenario();
        const resolved = resolvedOf(build(draft));

        expect(resolved.fx_rates).toStrictEqual({});
        expect(resolved.fx_spread_rate).toBe('0');
        expect(resolved.contributions).toStrictEqual([]);
        expect(itemBy(resolved.assets, 'asset_id', assetKey).exposures).toStrictEqual([]);

        expect(itemBy(resolved.brokers, 'broker_id', brokerKey).fee_schedules).toStrictEqual([]);
        const account = itemBy(resolved.brokers, 'broker_id', accountBrokerKey);
        expect(account.capabilities).toStrictEqual([]);
        expect(account.fee_schedules).toStrictEqual([]);

        // No transfer cap: the backend moves the whole selected amount of the source.
        expect(fundingFrom(resolved.funding_routes, cashKey)).toMatchObject({priority: 0, transfer_cap: null});
        expect(itemBy(resolved.order_routes, 'route_id', routeWireId(draft, assetKey, brokerKey))).toMatchObject({
            priority: 0,
            minimum_if_active: NONE,
            required_minimum: NONE,
            cap: NONE,
            execution_margin_rate: '0',
            fee_schedule_id: null,
        });
    });

    it('keeps the required values that look like defaults: a null ticker and a zero target weight', () => {
        const {draft, assetKey} = cashScenario();
        const unweighted = manualAsset(draft, 'Unweighted probe');
        draft.addAsset(unweighted);
        // Precondition: no target typed for the second Asset, and the total is still 100%.
        expect(draft.data.targets[unweighted.key]).toBeUndefined();
        expect(draft.targetTotal).toBe('100');

        const request = wireOf(build(draft));
        expect(itemBy(request.target_weights, 'asset_id', unweighted.key)).toStrictEqual({asset_id: unweighted.key, weight: '0'});
        expect(itemBy(request.target_weights, 'asset_id', assetKey)).toStrictEqual({asset_id: assetKey, weight: '1'});
        expect(asObject(itemBy(request.assets, 'asset_id', unweighted.key).identity)).toHaveProperty('ticker', null);
    });
});

describe('buildRequest: a copied price', () => {
    it('keeps its date in the draft only, and leaves out a missing source label', () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        draft.data.asOf = AS_OF;
        draft.addManualBroker('Broker probe');
        const copy = draft.registerCopy('prices', AS_OF, '2026-09-16T08:00:00Z', [{provenance_id: 'quote-source-probe', domain: 'market_data', source_ref: 'asset:7/price', source_label: null, captured_at: '2026-09-16T08:00:00Z'}]);
        const asset = draftAssetFromInfo({id: 7, display_name: 'Copied ETF probe', identifier_ticker: 'CETF', asset_type: 'ETF', icon_url: null, active: true});
        const price = {amount: '10', currency: 'EUR', quoteBaseQuantity: '1', referenceDate: '2026-09-10'};
        asset.price = {...price};
        asset.copiedPrice = {...price};
        asset.priceStamp = {copyId: copy.copyId, provenanceId: 'quote-source-probe'};
        draft.addAsset(asset);
        draft.data.targets[asset.key] = '100';
        const contribution = draft.addContribution('EUR', 'Saving probe');
        draft.contribution(contribution.key)!.amount = '50';
        // Precondition: the price is still the copy, six days old, and the draft still says so (plan §5).
        expect(priceIsCopied(draft.asset(asset.key)!)).toBe(true);
        expect(draft.factCounts.stale).toBe(1);

        const built = build(draft);
        const request = wireOf(built);
        const quote = asObject(itemBy(request.assets, 'asset_id', asset.key).quote);
        expect(keysOf(quote)).toEqual(['amount', 'currency', 'provenance_id', 'quote_base_quantity']);
        const provenanceId = String(quote.provenance_id);
        const source = itemBy(request.provenance, 'provenance_id', provenanceId);
        expect(source.kind).toBe('domain_copy');
        expect(keysOf(source)).toEqual(['captured_at', 'domain', 'kind', 'provenance_id', 'source_ref']);

        const resolved = resolvedOf(built);
        expect(keysOf(itemBy(resolved.assets, 'asset_id', asset.key).quote)).toEqual(['amount', 'currency', 'provenance_id', 'quote_base_quantity']);
        expect(itemBy(resolved.provenance, 'provenance_id', provenanceId)).toMatchObject({kind: 'domain_copy', source_label: null});
    });
});

describe('buildRequest: values the user changed', () => {
    it('sends a changed order route and funding route in full, and a fixed fee without the zero fields', () => {
        const {draft, brokerKey, assetKey} = baseScenario();
        const contribution = draft.addContribution('EUR', 'Saving probe');
        draft.contribution(contribution.key)!.amount = '100';
        const mode = eurMode(draft, brokerKey);
        mode.fixedFee = '1.50';
        const route = draft.data.routes[routeKey(assetKey, brokerKey)];
        route.priority = '2';
        route.minimumIfActive = '1';
        route.cap = '10';
        route.marginPercent = '0.5';
        const funding = fundingEntry(draft, brokerKey, contribution.key);
        funding.priority = '1';
        funding.cap = '30';

        const built = build(draft);
        const request = wireOf(built);
        expect(keysOf(request)).toEqual(['as_of', 'assets', 'brokers', 'contributions', 'funding_routes', 'operation', 'order_routes', 'policy', 'provenance', 'snapshot', 'target_weights', 'valuation_currency']);

        const scheduleId = feeScheduleId(brokerKey, mode);
        const schedule = {fee_schedule_id: scheduleId, capability_id: capabilityId(brokerKey, mode), side: 'buy', fixed_fee: {amount: '1.5', currency: 'EUR'}};
        expect(itemBy(request.brokers, 'broker_id', brokerKey).fee_schedules).toStrictEqual([schedule]);
        expect(itemBy(request.order_routes, 'route_id', route.wireId)).toStrictEqual({
            route_id: route.wireId,
            asset_id: assetKey,
            broker_id: brokerKey,
            capability_id: capabilityId(brokerKey, mode),
            side: 'buy',
            priority: 2,
            minimum_if_active: {kind: 'whole_quantity', quantity: '1', unit: 'asset_unit'},
            cap: {kind: 'quantity', quantity: '10', unit: 'asset_unit'},
            execution_margin_rate: '0.005',
            fee_schedule_id: scheduleId,
            provenance_id: expect.any(String),
        });
        expect(fundingFrom(request.funding_routes, contribution.key)).toStrictEqual({
            funding_route_id: expect.any(String),
            source: {kind: 'contribution', contribution_id: contribution.key},
            broker_id: brokerKey,
            currency: 'EUR',
            priority: 1,
            transfer_cap: {amount: '30', currency: 'EUR'},
            provenance_id: expect.any(String),
        });

        const resolved = resolvedOf(built);
        expect(resolved.existing_cash).toStrictEqual([]);
        expect(itemBy(resolved.brokers, 'broker_id', brokerKey).fee_schedules).toStrictEqual([{...schedule, rate: '0', variable_floor: null, variable_cap: NONE}]);
        expect(itemBy(resolved.order_routes, 'route_id', route.wireId)).toMatchObject({required_minimum: NONE, fee_schedule_id: scheduleId});
    });

    it.each([
        {
            name: 'a rate alone, so the schedule carries no currency',
            fees: {ratePercent: '0.19'},
            sent: {rate: '0.0019'},
            filled: {fixed_fee: null, variable_floor: null, variable_cap: NONE},
        },
        {
            name: 'a rate with floor and cap in the mode currency',
            fees: {ratePercent: '0.19', floor: '2', cap: '5'},
            sent: {rate: '0.0019', variable_floor: {amount: '2', currency: 'EUR'}, variable_cap: {kind: 'amount', amount: {amount: '5', currency: 'EUR'}}},
            filled: {fixed_fee: null},
        },
    ])('sends only the fee fields that are not zero: $name', ({fees, sent, filled}) => {
        const {draft, brokerKey, assetKey} = cashScenario();
        const mode = eurMode(draft, brokerKey);
        Object.assign(mode, fees);

        const built = build(draft);
        const request = wireOf(built);
        const scheduleId = feeScheduleId(brokerKey, mode);
        const identity = {fee_schedule_id: scheduleId, capability_id: capabilityId(brokerKey, mode), side: 'buy'};
        expect(itemBy(request.brokers, 'broker_id', brokerKey).fee_schedules).toStrictEqual([{...identity, ...sent}]);
        expect(itemBy(request.order_routes, 'route_id', routeWireId(draft, assetKey, brokerKey)).fee_schedule_id).toBe(scheduleId);

        const resolved = resolvedOf(built);
        expect(itemBy(resolved.brokers, 'broker_id', brokerKey).fee_schedules).toStrictEqual([{...identity, ...sent, ...filled}]);
    });
});
