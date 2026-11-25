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
 *
 * The sign gate (C-76, TP-12, last block). `localProblems` is what the steps show live and what
 * stops the request before it is sent. For the four values the user types whose sign the contract
 * restricts — the cash row's «Amount to use», a manual «Declared liquidity», a contribution, an order
 * step — it checked only «empty» and «not a number».
 *   - The sign table is the contract's. The generated codec takes any sign there (a fixed decimal; a
 *     whole-unit step is any integer), and the backend normalizer decides (`normalize.py`): it refuses
 *     `selected` or `available` below zero, a contribution below zero, a step at or below zero. Zero
 *     is a valid amount to use, declared liquidity or contribution, and never a valid step.
 *   - Each row types one value into one field of a sendable draft and reads every local problem as
 *     `{step, key, entity}`: the field's own problem or none, and nothing else, so a negative is
 *     reported as negative and never also as missing or invalid. It also reads whether the request
 *     is built: a row whose value the gate lets through would travel to the backend as it is.
 *   - An empty field is a positive control: today's problem, with the entity the new one must name.
 *   - A negative declared liquidity is exceeded by any amount to use. As in the backend
 *     (`validate_cash` checks «exceeds» only when neither amount is negative), the gate then reports
 *     the negative alone (developer's decision, C-76).
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
import {buildRequest, capabilityId, feeScheduleId, localProblems, stepOfWirePath, type BuiltRequest} from './request';
import {issueStep} from './issues';
import {sectionCounts} from './review';
import {REBALANCER_PLANNER_PROFILE} from './profile';
import type {PlannerStep} from './types';

const NOW = new Date('2026-09-16T12:00:00Z');
const AS_OF = '2026-09-16';
const codec = toolContractMap.pac_allocator['2.0.0'].input;
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
        expect(draft.data.routes[routeKey(assetKey, brokerKey)]).toMatchObject({enabled: true, priority: '0', minimumIfActive: '', cap: '', marginPercent: '0'});
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

    it('never writes a required minimum, and ignores one an older draft object still carries (M19)', () => {
        const {draft, brokerKey, assetKey} = cashScenario();
        const route = draft.data.routes[routeKey(assetKey, brokerKey)] as unknown as Record<string, unknown>;
        route.requiredMinimum = '5';

        const request = wireOf(build(draft));

        const sent = itemBy(request.order_routes, 'route_id', routeWireId(draft, assetKey, brokerKey));
        expect(keysOf(sent)).not.toContain('required_minimum');
        expect(JSON.stringify(request)).not.toContain('required_minimum');
    });

    it('writes every target as an entry of its kind (contract 2.0.0)', () => {
        const {draft, assetKey} = cashScenario();

        const request = wireOf(build(draft));

        expect(itemBy(request.target_weights, 'asset_id', assetKey)).toMatchObject({kind: 'asset', asset_id: assetKey});
        expect(asList(request.target_weights).every((entry) => entry.kind === 'asset')).toBe(true);
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
        expect(itemBy(request.target_weights, 'asset_id', unweighted.key)).toStrictEqual({kind: 'asset', asset_id: unweighted.key, weight: '0'});
        expect(itemBy(request.target_weights, 'asset_id', assetKey)).toStrictEqual({kind: 'asset', asset_id: assetKey, weight: '1'});
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
        expect(itemBy(resolved.order_routes, 'route_id', route.wireId)).toMatchObject({fee_schedule_id: scheduleId});
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

// ---------------------------------------------------------------------------
// C-76 (TP-12) — the local gate reads the sign of an amount and of an order step
// ---------------------------------------------------------------------------

/** Where a problem on the account's cash row is shown: `cashLabel`, «Broker · currency». */
const CASH_LABEL = 'Bank probe · EUR';
/** Where a problem on the operative Broker's EUR mode is shown: «Broker · currency». */
const MODE_LABEL = 'Broker probe · EUR';
/** Where a problem on the contribution is shown: its label. */
const CONTRIBUTION_LABEL = 'Saving probe';

/** The values the user types whose sign the contract restricts. */
type SignField = 'selected' | 'declared' | 'contribution' | 'wholeStep' | 'amountStep';

interface SignRow {
    field: SignField;
    /** The text typed into the field. */
    value: string;
    /** The one local problem the field owes, or null for none. */
    problem: string | null;
    why: string;
}

/**
 * The sign table, from the contract. The generated codec takes every sign in these fields
 * (`PlannerMoneyInput.amount` is any fixed decimal, `quantity_step` any integer), so the backend normalizer decides
 * (`backend/app/services/pac_allocator/normalize.py`):
 *   - `validate_cash`: `available` or `selected` below zero → `allocation.negative_cash_unsupported`;
 *   - `validate_contribution`: an amount below zero → `allocation.negative_contribution`;
 *   - `validate_capability`: a whole-unit step at or below zero → `allocation.nonpositive_quantity_step`, an amount
 *     step at or below zero → `allocation.nonpositive_order_amount_step`.
 * Zero is a valid amount to use, declared liquidity or contribution; a step must be above zero.
 */
const SIGN_ROWS: SignRow[] = [
    // «Amount to use» (`cash.selected`), next to 100 EUR of declared liquidity
    {field: 'selected', value: '', problem: 'selectedMissing', why: 'control: empty, as today'},
    {field: 'selected', value: 'abc', problem: 'selectedInvalid', why: 'control: not a number, as today'},
    {field: 'selected', value: '-0.01', problem: 'selectedNegative', why: 'negative: refused as negative, and only so'},
    {field: 'selected', value: '-0,01', problem: 'selectedNegative', why: 'negative, typed with a decimal comma: the gate reads the typed text the way the field does'},
    {field: 'selected', value: '0', problem: null, why: 'zero: using nothing is a valid selection'},
    {field: 'selected', value: '-0', problem: null, why: 'zero typed with a minus is zero, not negative'},
    {field: 'selected', value: '0.01', problem: null, why: 'positive'},
    {field: 'selected', value: '100', problem: null, why: 'guard: the whole declared liquidity'},
    {field: 'selected', value: '100.01', problem: 'selectedExceedsAvailable', why: 'guard: above the declared liquidity, still refused as exceeding it'},
    // «Declared liquidity» (`cash.available`, manual cash), with nothing to use
    {field: 'declared', value: '', problem: 'declaredMissing', why: 'control: empty, as today'},
    {field: 'declared', value: '-0.01', problem: 'declaredNegative', why: 'negative: refused as negative, and only so: the amount to use, 0, exceeds it, but as in the backend «exceeds» is not reported on top'},
    {field: 'declared', value: '0', problem: null, why: 'zero: a valid declared liquidity'},
    {field: 'declared', value: '-0', problem: null, why: 'zero typed with a minus is zero, not negative'},
    {field: 'declared', value: '0.01', problem: null, why: 'positive'},
    // The contribution amount
    {field: 'contribution', value: '', problem: 'contributionAmountMissing', why: 'control: empty, as today'},
    {field: 'contribution', value: '-0.01', problem: 'contributionAmountNegative', why: 'negative: refused as negative, and only so'},
    {field: 'contribution', value: '0', problem: null, why: 'zero: a valid contribution'},
    {field: 'contribution', value: '-0', problem: null, why: 'zero typed with a minus is zero, not negative'},
    {field: 'contribution', value: '0.01', problem: null, why: 'positive'},
    // The order step of a whole-unit mode
    {field: 'wholeStep', value: '', problem: 'modeStepMissing', why: 'control: empty, as today'},
    {field: 'wholeStep', value: '-1', problem: 'modeStepNotPositive', why: 'negative: a whole number, refused as not positive, and only so'},
    {field: 'wholeStep', value: '0', problem: 'modeStepNotPositive', why: 'zero: a step must be above zero'},
    {field: 'wholeStep', value: '1', problem: null, why: 'positive'},
    // The order step of an amount mode
    {field: 'amountStep', value: '', problem: 'modeStepMissing', why: 'control: empty, as today'},
    {field: 'amountStep', value: '-0.01', problem: 'modeStepNotPositive', why: 'negative: refused as not positive, and only so'},
    {field: 'amountStep', value: '0', problem: 'modeStepNotPositive', why: 'zero: a step must be above zero'},
    {field: 'amountStep', value: '0.01', problem: null, why: 'positive'},
];

/**
 * A sendable draft with `value` typed into `field`, and where a problem on that field is shown. The cash fields and
 * the steps live in `cashScenario` (100 EUR declared, 50 to use, one operative Broker in whole units); the
 * contribution is the only liquidity of `baseScenario`, as in the cases above.
 */
function signScenario(field: SignField, value: string): {draft: PlannerDraft; step: PlannerStep; entity: string} {
    if (field === 'contribution') {
        const {draft} = baseScenario();
        const contribution = draft.addContribution('EUR', CONTRIBUTION_LABEL);
        draft.contribution(contribution.key)!.amount = value;
        return {draft, step: 'liquidity', entity: CONTRIBUTION_LABEL};
    }
    const {draft, brokerKey, cashKey} = cashScenario();
    if (field === 'selected' || field === 'declared') {
        const cash = draft.cashRow(cashKey);
        if (cash === undefined) throw new Error('unreachable: cashScenario adds this cash row');
        if (field === 'selected') {
            cash.selected = value;
        } else {
            // Nothing to use, so a declared liquidity of zero stays sendable and the row isolates the declared field.
            // A negative one is still exceeded by this 0: the exact list proves «exceeds» is not reported on top of it,
            // while the `selected` 100.01 row proves the key is still raised against a balance that is not negative.
            cash.selected = '0';
            cash.available = value;
        }
        return {draft, step: 'liquidity', entity: CASH_LABEL};
    }
    const mode = eurMode(draft, brokerKey);
    if (field === 'amountStep') mode.kind = 'monetary_amount';
    mode.step = value;
    return {draft, step: 'brokers', entity: MODE_LABEL};
}

/** A row's whole test title: Vitest cuts a `$`-interpolated string at 40 characters. */
function signTitle({field, value, problem, why}: SignRow): string {
    return `${field} «${value}» → ${problem ?? 'no problem'}: ${why}`;
}

describe('localProblems: the sign of an amount and of an order step (C-76, TP-12)', () => {
    it.each(SIGN_ROWS.map((row): [string, SignRow] => [signTitle(row), row]))('%s', (_title, {field, value, problem}) => {
        const {draft, step, entity} = signScenario(field, value);
        const owed = problem === null ? [] : [{step, key: problem, entity}];
        const raised = localProblems(draft).map((item) => ({step: item.step, key: item.key, entity: item.entity}));

        // `built`: no local problem, and the codec takes the body, so the request would be sent as it is.
        expect({problems: raised, built: buildRequest(draft, NOW).ok}).toEqual({problems: owed, built: owed.length === 0});
    });
});

/*
 * F2 of project 67: a minimum and a maximum per Asset, on its value at the end of the plan (contract 2.0.0 §5.2).
 * A limit is typed as text: «500» is an amount in the valuation currency, «35%» a share of the plan's total. An empty
 * field is no limit. The frontend checks the shape and compares two limits only when they are in the same form; every
 * other comparison needs the Tool's reference and is the backend's (`allocation.bound_*` codes).
 */

/**
 * The request of a two-Asset draft (60% / 40%) as today's builder wrote it before limits existed, captured from the
 * code at HEAD `e4a5ae6cb` with the clock fixed at NOW. A draft with no limit must still send exactly these bytes.
 */
const BEFORE_LIMITS = String.raw`{"operation":"plan","snapshot":{"snapshot_id":"draft:1","draft_revision":1,"captured_at":"2026-09-16T12:00:00.000Z"},"as_of":"2026-09-16","valuation_currency":"EUR","provenance":[{"kind":"manual","provenance_id":"manual:manual-asset:3/quote","label":"manual price","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:manual-asset:8/quote","label":"manual price","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:manual-broker:1","label":"manual broker","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:manual-broker:5","label":"manual broker","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:manual-cash:6","label":"manual cash","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:funding:7","label":"funding route","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:route:4","label":"order route","entered_at":"2026-09-16T12:00:00.000Z"},{"kind":"manual","provenance_id":"manual:route:9","label":"order route","entered_at":"2026-09-16T12:00:00.000Z"}],"assets":[{"asset_id":"manual-asset:3","identity":{"kind":"manual_asset","name":"Manual ETF probe","ticker":null,"asset_class":"etf"},"quote":{"amount":"10","currency":"EUR","quote_base_quantity":"1","provenance_id":"manual:manual-asset:3/quote"}},{"asset_id":"manual-asset:8","identity":{"kind":"manual_asset","name":"Second probe","ticker":null,"asset_class":"etf"},"quote":{"amount":"10","currency":"EUR","quote_base_quantity":"1","provenance_id":"manual:manual-asset:8/quote"}}],"brokers":[{"broker_id":"manual-broker:1","identity":{"kind":"manual_broker","name":"Broker probe"},"provenance_id":"manual:manual-broker:1","conversion_mode":"manual","capabilities":[{"kind":"whole_quantity","capability_id":"manual-broker:1/mode:EUR","quantity_unit":"asset_unit","quantity_step":"1"}]},{"broker_id":"manual-broker:5","identity":{"kind":"manual_broker","name":"Bank probe"},"provenance_id":"manual:manual-broker:5","conversion_mode":"manual"}],"existing_cash":[{"cash_id":"manual-cash:6","broker_id":"manual-broker:5","available":{"amount":"100","currency":"EUR"},"selected":{"amount":"50","currency":"EUR"},"provenance_id":"manual:manual-cash:6"}],"funding_routes":[{"funding_route_id":"funding:manual-broker:1/funding:7","source":{"kind":"existing_cash","cash_id":"manual-cash:6"},"broker_id":"manual-broker:1","currency":"EUR","provenance_id":"manual:funding:7"}],"target_weights":[{"kind":"asset","asset_id":"manual-asset:3","weight":"0.6"},{"kind":"asset","asset_id":"manual-asset:8","weight":"0.4"}],"order_routes":[{"route_id":"route:4","asset_id":"manual-asset:3","broker_id":"manual-broker:1","capability_id":"manual-broker:1/mode:EUR","side":"buy","provenance_id":"manual:route:4"},{"route_id":"route:9","asset_id":"manual-asset:8","broker_id":"manual-broker:1","capability_id":"manual-broker:1/mode:EUR","side":"buy","provenance_id":"manual:route:9"}],"policy":"proportional"}`;

/** `cashScenario` with a second Asset: targets 60% and 40%, and the two Asset keys. */
function twoAssetScenario(): Scenario & {secondKey: string} {
    const scenario = cashScenario();
    const second = manualAsset(scenario.draft, 'Second probe');
    scenario.draft.addAsset(second);
    scenario.draft.data.targets[second.key] = '40';
    scenario.draft.data.targets[scenario.assetKey] = '60';
    return {...scenario, secondKey: second.key};
}

function limitProblemsOf(draft: PlannerDraft): {step: PlannerStep; key: string; entity: string | null}[] {
    return localProblems(draft)
        .filter((item) => item.key.startsWith('limit'))
        .map((item) => ({step: item.step, key: item.key, entity: item.entity}));
}

describe('buildRequest: limits on the target entries (F2)', () => {
    it('no limits: the request equals the one built before limits existed', () => {
        vi.useFakeTimers({toFake: ['Date'], now: NOW});
        try {
            const {draft} = twoAssetScenario();
            // The capture predates TL-6 of project 67, when a new Broker read «Converti tu»: set it, the bytes stay the capture's.
            for (const broker of draft.data.brokers) broker.conversionMode = 'manual';
            expect(JSON.stringify(build(draft).request)).toBe(BEFORE_LIMITS);
        } finally {
            vi.useRealTimers();
        }
    });

    it('an empty limit field sends no limit', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '');
        draft.setLimit(assetKey, 'maximum', '   ');
        draft.setLimit(secondKey, 'minimum', '10');
        draft.setLimit(secondKey, 'minimum', '');

        const request = wireOf(build(draft));

        expect(itemBy(request.target_weights, 'asset_id', assetKey)).toStrictEqual({kind: 'asset', asset_id: assetKey, weight: '0.6'});
        expect(itemBy(request.target_weights, 'asset_id', secondKey)).toStrictEqual({kind: 'asset', asset_id: secondKey, weight: '0.4'});
        expect(draft.data.limits).toStrictEqual({});
    });

    it('limits travel as target entries with amount or share', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '500');
        draft.setLimit(assetKey, 'maximum', '35%');
        draft.setLimit(secondKey, 'maximum', '12,5 %');

        const built = build(draft);
        const request = wireOf(built);

        expect(itemBy(request.target_weights, 'asset_id', assetKey)).toStrictEqual({
            kind: 'asset',
            asset_id: assetKey,
            weight: '0.6',
            minimum: {kind: 'amount', amount: {amount: '500', currency: 'EUR'}},
            maximum: {kind: 'share', share: '0.35'},
        });
        expect(itemBy(request.target_weights, 'asset_id', secondKey)).toStrictEqual({kind: 'asset', asset_id: secondKey, weight: '0.4', maximum: {kind: 'share', share: '0.125'}});
        // The codec takes both forms, and the resolved request fills the missing side with «no limit».
        expect(itemBy(resolvedOf(built).target_weights, 'asset_id', secondKey)).toMatchObject({minimum: null, maximum: {kind: 'share', share: '0.125'}});
    });

    it('removing an asset removes its limits', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(secondKey, 'minimum', '5%');
        draft.setLimit(assetKey, 'maximum', '900');

        draft.removeAsset(secondKey);
        draft.data.targets[assetKey] = '100';

        expect(Object.keys(draft.data.limits)).toEqual([assetKey]);
        const request = wireOf(build(draft));
        expect(asList(request.target_weights).map((entry) => entry.asset_id)).toEqual([assetKey]);
        expect(JSON.stringify(request)).not.toContain('"share"');
    });
});

describe('localProblems: the limits of a target entry (F2)', () => {
    it('a minimum above the maximum in the same form is a local problem', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '2000');
        draft.setLimit(assetKey, 'maximum', '1000');
        draft.setLimit(secondKey, 'minimum', '30%');
        draft.setLimit(secondKey, 'maximum', '20%');

        expect(limitProblemsOf(draft)).toEqual([
            {step: 'targets', key: 'limitMinAboveMax', entity: 'Manual ETF probe'},
            {step: 'targets', key: 'limitMinAboveMax', entity: 'Second probe'},
        ]);
        expect(buildRequest(draft, NOW).ok).toBe(false);
    });

    it('a minimum equal to the maximum is no problem', () => {
        const {draft, assetKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '1000');
        draft.setLimit(assetKey, 'maximum', '1000.00');

        expect(limitProblemsOf(draft)).toEqual([]);
    });

    it('a minimum above the maximum in different forms is left to the backend', () => {
        const {draft, assetKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '2000');
        draft.setLimit(assetKey, 'maximum', '10%');

        expect(limitProblemsOf(draft)).toEqual([]);
        expect(buildRequest(draft, NOW).ok).toBe(true);
    });

    it('share minimums above 100 are a local problem naming the entries', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', '33.34%');
        draft.setLimit(secondKey, 'minimum', '66.67%');

        const problems = localProblems(draft).filter((item) => item.key === 'limitShareMinimumsAboveHundred');
        expect(problems.map((item) => ({step: item.step, entity: item.entity, values: item.values}))).toEqual([{step: 'targets', entity: null, values: {assets: 'Manual ETF probe, Second probe'}}]);

        // Exactly 100% is allowed: the sum is exact, not a float (33.33 + 66.67).
        draft.setLimit(assetKey, 'minimum', '33.33%');
        expect(limitProblemsOf(draft)).toEqual([]);
        // Amount minimums are never summed here: their total is compared with the reference by the backend.
        draft.setLimit(assetKey, 'minimum', '999999');
        expect(limitProblemsOf(draft)).toEqual([]);
    });

    it('a limit that is not a number, is negative, or a percentage above 100 is a local problem', () => {
        const {draft, assetKey, secondKey} = twoAssetScenario();
        draft.setLimit(assetKey, 'minimum', 'abc');
        draft.setLimit(secondKey, 'maximum', '-5');

        expect(limitProblemsOf(draft)).toEqual([
            {step: 'targets', key: 'limitInvalid', entity: 'Manual ETF probe'},
            {step: 'targets', key: 'limitInvalid', entity: 'Second probe'},
        ]);

        draft.setLimit(assetKey, 'minimum', '');
        draft.setLimit(secondKey, 'maximum', '120%');
        expect(limitProblemsOf(draft)).toEqual([{step: 'targets', key: 'limitShareAboveHundred', entity: 'Second probe'}]);

        // A minimum above 100% is reported once, as itself: it does not also enter the sum of the minimums.
        draft.setLimit(secondKey, 'maximum', '');
        draft.setLimit(secondKey, 'minimum', '120%');
        expect(limitProblemsOf(draft)).toEqual([{step: 'targets', key: 'limitShareAboveHundred', entity: 'Second probe'}]);
    });
});

describe('the PAC cash rows (F3a of project 67, step 14; U8)', () => {
    it('PAC cash rows carry only minimum and maximum', () => {
        const {draft, brokerKey} = cashScenario();
        const limited = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit(limited.key, 'minimum', '100');
        draft.setLimit(limited.key, 'maximum', '20%');
        // A stray figure in the targets never travels: the PAC's cash has no weight (contract §5.2).
        draft.data.targets[limited.key] = '5';
        // A cash row with no limit says nothing: it does not travel.
        draft.addCashEntry(draft.data.cash[0].brokerKey, 'EUR');

        const wire = wireOf(build(draft));
        const cash = asList(wire.target_weights).filter((entry) => entry.kind === 'cash');
        expect(cash).toEqual([{kind: 'cash', broker_id: brokerKey, currency: 'EUR', weight: '0', minimum: {kind: 'amount', amount: {amount: '100', currency: 'EUR'}}, maximum: {kind: 'share', share: '0.2'}}]);
        // The total of the targets is the Assets' alone.
        expect(localProblems(draft).map((problem) => problem.key)).not.toContain('targetTotalNotHundred');
    });
});

describe('the PAC cash rows: problems and the Review (F3a of project 67, step 14)', () => {
    it('a wrong limit on a PAC cash row is a local problem of Targets, named «Broker · currency»', () => {
        const {draft, brokerKey} = cashScenario();
        const row = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit(row.key, 'maximum', '-5');
        expect(limitProblemsOf(draft)).toEqual([{step: 'targets', key: 'limitInvalid', entity: 'Broker probe · EUR'}]);
    });

    it('the Review counts a limited PAC cash row «with a limit»; the entries stay the Assets', () => {
        const {draft, brokerKey} = cashScenario();
        const row = draft.addCashEntry(brokerKey, 'EUR');
        draft.setLimit(row.key, 'minimum', '10');
        expect(sectionCounts(draft).targets).toEqual({entries: 1, count: 1, limited: 1});
    });
});

describe('the pre-calculation limit codes go to the Targets step (F2)', () => {
    it('a codec path under the target entries and a backend issue on an entry both open Targets', () => {
        expect(stepOfWirePath(['target_weights', 0, 'minimum', 'share'])).toBe('targets');
        expect(issueStep({section: 'targets', entity_kind: 'asset', entity_id: 'manual-asset:3', field: 'minimum'} as Parameters<typeof issueStep>[0])).toBe('targets');
        expect(issueStep({section: 'targets', entity_kind: 'asset', entity_id: 'manual-asset:3'} as Parameters<typeof issueStep>[0])).toBe('targets');
    });
});

describe('the Rebalancer and its own request (F3a of project 67, step 11)', () => {
    it("a complete draft under the Rebalancer's profile builds the Rebalancer's own request (step 11)", () => {
        const draft = new PlannerDraft('EUR', 'invest_only', REBALANCER_PLANNER_PROFILE);
        draft.data.asOf = AS_OF;
        draft.addManualBroker('Broker probe');
        const asset = manualAsset(draft, 'Manual ETF probe');
        draft.addAsset(asset);
        draft.data.targets[asset.key] = '100';
        draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
        expect(localProblems(draft)).toEqual([]);

        const outcome = buildRequest(draft, NOW);

        // Step 11 builds it, checked by the Rebalancer's codec (`request.rebalancer.test.ts` holds the details).
        expect(outcome.ok ? [] : outcome.problems.map((problem) => problem.key)).toEqual([]);
        if (!outcome.ok) return;
        expect(outcome.built.request).toMatchObject({policy: 'invest_only', target_fidelity: {kind: 'level', level: 'balanced'}});
        expect(outcome.built.request).not.toHaveProperty('funding_routes');
    });

    it("the PAC's preview request: operation preview, built while the targets do not sum to 100 yet", () => {
        const draft = new PlannerDraft('EUR', 'proportional');
        draft.data.asOf = AS_OF;
        draft.addManualBroker('Broker probe');
        const asset = manualAsset(draft, 'Manual ETF probe');
        draft.addAsset(asset);
        draft.data.targets[asset.key] = '40';
        draft.addManualAccount({name: 'Bank probe', currency: 'EUR', available: '100', selected: '50'});
        expect(localProblems(draft).map((problem) => problem.key)).toEqual(['targetTotalNotHundred']);

        const outcome = buildRequest(draft, NOW, {operation: 'preview'});

        expect(outcome.ok ? [] : outcome.problems.map((problem) => problem.key)).toEqual([]);
        if (!outcome.ok) return;
        expect(outcome.built.request).toMatchObject({operation: 'preview', policy: 'proportional'});
        expect(outcome.built.request).not.toHaveProperty('custom_reference_amount');
        // The plan still stops on it.
        expect(buildRequest(draft, NOW).ok).toBe(false);
    });
});
