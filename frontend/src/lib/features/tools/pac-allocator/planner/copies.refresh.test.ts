// @vitest-environment jsdom
/**
 * refreshCopiedFacts: the re-read before «Calcola» reports the source's issues (Vitest + jsdom).
 *
 * RED until X-R45b-ui.
 *
 * Subject. X-R45b (backend 292d7e55e): `POST /portfolio/allocation-source`, section `fx_quotes`, skips the
 * latest saved rate of a pair when it is 0 or not finite and quotes the previous valid one. It says so with a
 * source issue, `allocation.saved_fx_skipped` (warning; params pair, skipped_date, used_date), on the `rate`
 * field of the quote it used.
 *   - Before «Calcola» the planner reads again every copied fact the user has not changed
 *     (`refreshPlan` → `refreshQuery` → the source → `refreshCopiedFacts`). An Auto FX pair is one of them.
 *   - `refreshCopiedFacts` copies the older rate into the pair, but its `RefreshSummary` has no field for the
 *     source's issues: the warning is dropped there, and `RefreshNotice` can never show it.
 *
 * The cure (X-R45b-ui). `RefreshSummary.issues`: the re-read source's `issues` minus the structural
 * `allocation.broker_execution_profile_unsupported`, as `CopyNotice` does after an explicit copy. The backend adds
 * that issue for every Broker it reads, and the re-read reads the Broker of every copied cash row.
 *
 * Scenario. Valuation EUR. USD cash copied from Broker 7, so the scenario needs EUR/USD; the Auto pair EUR/USD
 * filled by the FX step's read (`applyAwaitingFxRates`) and left unchanged. The re-read asks for Brokers, cash and
 * FX, as `refreshQuery` builds it. Its snapshot quotes EUR/USD at the rate of 2026-01-02, because the rate of
 * 2026-01-05 was skipped, and carries the skipped-rate warning plus the structural issue of Broker 7.
 *
 * Snapshots. Each one is the API response as the backend serialises it (`message_key` included), mapped by the
 * real parser: the API client is mocked and `fetchPlannerSource` maps its answer, as in `source.test.ts`. The tool
 * session is a real one (`transitionClientSession`). Nothing here talks to a server or reads translated text.
 *
 * Environment. jsdom is here for the compile target, not for the DOM: in the node environment Vitest compiles
 * `draft.svelte.ts` for the server, where a `$derived` is computed on first read and never again (see
 * `request.test.ts`). The FX closure behind `refreshPlan` must stay live while the copies fill the draft.
 *
 * Tests.
 *   - GUARD (green today and after): the re-read puts the older quoted rate into the pair and counts it as
 *     updated. It proves the scenario is the defect's: the draft now holds the rate of the used date.
 *   - RED until X-R45b-ui: `summary.issues` is exactly the skipped-rate warning; the structural issue is not
 *     there. Today `RefreshSummary` has no `issues`, so the field is undefined.
 *
 * The review of X-R45b-ui (D1) adds the last block: the issues of a Broker the user owns but the plan does not use are
 * left out of `summary.issues`.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());

// source.ts and the tool client import the API client. Nothing here talks to a server: the allocation-source
// endpoint answers the snapshot each read queues.
vi.mock('$lib/api', () => ({
    zodiosApi: {get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post: allocationSource},
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {applyAwaitingFxRates, applyLiquidityCopy, draftAssetFromInfo, newCopyRecord, refreshCopiedFacts, refreshPlan, refreshQuery, type RefreshPlan} from './copies';
import {PlannerDraft, daysBetween, rateIsCopied} from './draft.svelte';
import {fetchPlannerSource, type PlannerSource, type SourceIssue, type SourceQuery} from './source';

const OWNER = 7;
const BROKER_ID = `broker:${OWNER}`;
const PAIR = 'EUR/USD';
const SKIPPED_CODE = 'allocation.saved_fx_skipped';
const PROFILE_CODE = 'allocation.broker_execution_profile_unsupported';
/** `fx_key` of the backend is `fx:<pair>:<reference date>:<sha256(source)[:12]>`; `61683d66d785` is the token of `ECB`. */
const ECB_TOKEN = '61683d66d785';
/** The rate the FX step's read copied, and the snapshot it came from. */
const COPIED = {rate: '1.0900', date: '2025-12-31'};
const COPY_AS_OF = '2026-01-01';
/** The latest saved rate is 0 or not finite: the backend skips it. */
const SKIPPED_DATE = '2026-01-05';
/** The previous valid rate, which the re-read quotes instead. */
const USED = {rate: '1.0950', date: '2026-01-02'};
const REREAD_AS_OF = '2026-01-07';

function quoteId(date: string): string {
    return `fx:${PAIR}:${date}:${ECB_TOKEN}`;
}

/** `allocation.saved_fx_skipped` as `fx_quotes.py` builds it, after the parser: on the quote actually used. */
const SKIPPED: SourceIssue = {
    code: SKIPPED_CODE,
    kind: 'invalid',
    severity: 'warning',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(USED.date), field: 'rate'},
    params: [
        {kind: 'text', name: 'pair', value: PAIR},
        {kind: 'date', name: 'skipped_date', value: SKIPPED_DATE},
        {kind: 'date', name: 'used_date', value: USED.date},
    ],
};

/** The structural issue `entities.py` adds for every Broker it reads: LibreFolio stores no fees or order modes. */
const PROFILE: SourceIssue = {
    code: PROFILE_CODE,
    kind: 'unsupported',
    severity: 'error',
    path: {kind: 'field', section: 'brokers', entity_kind: 'broker', entity_id: BROKER_ID, field: 'execution_profile_status'},
    params: [],
};

/** An issue as the backend serialises it: the parser drops `message_key`. */
function wire(issue: SourceIssue) {
    return {...issue, message_key: issue.code};
}

/** One Broker the user owns, as the backend serialises it. */
function brokerRow(id: number, name: string, active = true) {
    return {
        broker_id: `broker:${id}`,
        source_broker_id: id,
        name,
        icon_url: null,
        portal_url: null,
        default_import_plugin: null,
        access_role: 'OWNER',
        ownership_share: '1',
        observed_currencies: ['USD'],
        active,
        allow_cash_overdraft: false,
        allow_asset_shorting: false,
        execution_profile_status: 'not_available',
        provenance_id: 'source:broker-domain',
    };
}

/** One cash balance of a wholly owned Broker, as the backend serialises it. */
function cashRow(brokerId: number, currency: string, amount: string) {
    return {cash_id: `cash:broker:${brokerId}:${currency}`, broker_id: `broker:${brokerId}`, currency, custody_amount: amount, ownership_share: '1', economic_amount: amount, provenance_id: 'source:portfolio-ledger'};
}

/** The answer to a read of Broker 7, its USD cash and EUR/USD, as the backend serialises it. */
function response(asOf: string, fx: {rate: string; date: string}, issues: readonly SourceIssue[]) {
    const generatedAt = `${asOf}T09:30:00Z`;
    return {
        snapshot: {as_of: asOf, target_currency: 'EUR', generated_at: generatedAt},
        provenance: [
            {provenance_id: 'source:portfolio-ledger', kind: 'domain_copy', domain: 'portfolio', source_ref: 'transactions+broker_user_access', source_label: null, captured_at: generatedAt},
            {provenance_id: 'source:broker-domain', kind: 'domain_copy', domain: 'broker', source_ref: 'brokers+broker_user_access+transactions', source_label: null, captured_at: generatedAt},
            {provenance_id: 'source:saved-fx', kind: 'domain_copy', domain: 'fx', source_ref: 'fx_rates', source_label: null, captured_at: generatedAt},
        ],
        assets: [],
        brokers: [brokerRow(OWNER, 'Broker Seven probe')],
        holdings: [],
        cash_balances: [cashRow(OWNER, 'USD', '2500')],
        prices: [],
        classifications: [],
        fx_quotes: [{fx_quote_id: quoteId(fx.date), pair: PAIR, rate: fx.rate, reference_date: fx.date, source: 'ECB', days_before_requested: daysBetween(fx.date, asOf), provenance_id: 'source:saved-fx'}],
        current_distribution: null,
        issues: issues.map(wire),
    };
}

/** One read through the real parser: the endpoint answers `raw`, `fetchPlannerSource` maps it. */
async function read(query: SourceQuery, raw: object): Promise<PlannerSource> {
    allocationSource.mockResolvedValueOnce(raw);
    return fetchPlannerSource(query, getClientSessionGeneration());
}

/**
 * The draft of the defect, built as the wizard builds it: the liquidity copy of Broker 7, then the FX step's read
 * of the pair it makes necessary. Returns the plan of the re-read before «Calcola».
 */
async function copiedAutoPair(): Promise<{draft: PlannerDraft; plan: RefreshPlan}> {
    const draft = new PlannerDraft('EUR');
    const query: SourceQuery = {asOf: COPY_AS_OF, targetCurrency: 'EUR', sections: ['brokers', 'cash_balances', 'fx_quotes'], brokerIds: [OWNER], assetIds: [], fxPairs: [PAIR]};
    const first = await read(query, response(COPY_AS_OF, COPIED, [PROFILE]));
    applyLiquidityCopy(draft, first, newCopyRecord(draft, 'liquidity', first), [OWNER]);
    expect(draft.requiredPairs, 'precondition: the USD cash makes the scenario need EUR/USD').toEqual([PAIR]);
    const filled = applyAwaitingFxRates(draft, first, newCopyRecord(draft, 'fx', first), [PAIR]);
    expect(filled.applied, 'precondition: the FX read filled the pair').toBe(1);

    const fx = draft.fx(PAIR);
    if (!fx) throw new Error('unreachable: the FX read filled the pair (asserted above)');
    expect(fx.manual, 'precondition: the pair is Auto').toBe(false);
    expect(fx.rate, 'precondition: the pair holds the copied rate').toBe(COPIED.rate);
    expect(rateIsCopied(fx), 'precondition: the copied rate is unchanged').toBe(true);

    const plan = refreshPlan(draft);
    expect(plan, 'precondition: the re-read plans the cash of Broker 7 and the pair').toEqual({assetIds: [], cashBrokerIds: [OWNER], fxPairs: [PAIR]});
    if (!plan) throw new Error('unreachable: the plan was asserted above');
    return {draft, plan};
}

/** The re-read before «Calcola», with the query `refreshQuery` builds for the plan. */
async function reread(draft: PlannerDraft, plan: RefreshPlan): Promise<PlannerSource> {
    const query = refreshQuery(draft, plan, [OWNER]);
    expect(query.sections, 'precondition: the re-read reads the Broker of the cash, so the structural issue comes with it').toEqual(['brokers', 'cash_balances', 'fx_quotes']);
    expect(query.fxPairs).toEqual([PAIR]);
    return read(query, response(REREAD_AS_OF, USED, [PROFILE, SKIPPED]));
}

let nextUser = 70;

beforeEach(() => {
    allocationSource.mockReset();
    transitionClientSession(++nextUser);
});

describe('refreshCopiedFacts — the skipped saved FX rate (X-R45b-ui)', () => {
    it('GUARD: the re-read puts the older quoted rate into the Auto pair and counts it as updated', async () => {
        const {draft, plan} = await copiedAutoPair();
        const source = await reread(draft, plan);

        const summary = refreshCopiedFacts(draft, source, plan);

        expect(summary).toMatchObject({prices: 0, fx: 1, cash: 0, unchanged: 1, missing: []});
        const fx = draft.fx(PAIR);
        expect(fx?.rate, 'the pair now holds the rate of the used date').toBe(USED.rate);
        expect(fx?.referenceDate).toBe(USED.date);
        expect(fx !== undefined && rateIsCopied(fx), 'the pair stays an unchanged copy (Auto)').toBe(true);
    });

    it('RED until X-R45b-ui: summary.issues holds the skipped-rate warning and drops the structural Broker issue', async () => {
        const {draft, plan} = await copiedAutoPair();
        const source = await reread(draft, plan);
        expect(source.issues, 'barrier: the parser kept both issues of the re-read').toEqual([PROFILE, SKIPPED]);

        const summary = refreshCopiedFacts(draft, source, plan);

        expect(summary.issues, 'RefreshSummary.issues: the issues of the re-read, minus broker_execution_profile_unsupported').toEqual([SKIPPED]);
    });
});

// -- The review of X-R45b-ui, D1: the Brokers outside the plan ---------------------------------------------------------

/*
 * D1 — the re-read shows Broker warnings outside the plan.
 *   - `refreshQuery` asks every Broker the user owns, so that one no longer owned is refused (403) instead of dropped
 *     in silence; with copied cash it also reads the sections `brokers` and `cash_balances`.
 *   - `refreshCopiedFacts` puts in `RefreshSummary.issues` every issue but the execution-profile note.
 *   - So the issues of a Broker the plan does not use (inactive, a negative balance, a currency code that is not valid)
 *     reach `RefreshNotice` and turn it to the warning tone. The explicit Broker and Liquidity copies filter them with
 *     `selectedBrokerIssues(source, brokerIds)`.
 *
 * The cure: `summary.issues` = `selectedBrokerIssues(source, plan.cashBrokerIds)` minus the execution-profile note.
 *   - An issue whose entity names `broker:N` (`broker:N`, `cash:broker:N:CCY`) stays when N is in `plan.cashBrokerIds`.
 *   - An issue that names no Broker (`fx:<pair>:…`, `price:asset:…`, an Asset, a section) always stays.
 *
 * Scenario: the plan of `copiedAutoPair` (Broker 7's USD cash, the Auto pair EUR/USD) plus an Asset added from
 * LibreFolio whose price was never read, so the re-read reads prices too (R8.3). The user also owns Broker 9 and never
 * copied from it. The re-read asks Brokers 7 and 9, and its snapshot carries, in the backend's order:
 *   - Brokers: both deactivated since the copy (`broker_inactive`), each with its execution-profile note;
 *   - cash: Broker 9's USD balance is negative (`negative_cash_unsupported`, on the cash row), and one more balance of
 *     Broker 9 has a currency code that is not valid (`currency_spec_missing`, on the Broker; the row is dropped);
 *   - prices: none for the Asset (`price_missing`);
 *   - FX: EUR/USD's latest saved rate skipped (`saved_fx_skipped`).
 *
 * Tests.
 *   - GUARD (green before and after): each issue of the plan stays — Broker 7's, EUR/USD's, the Asset's.
 *   - RED until the X-R45b-ui review (D1): each of Broker 9's three issues is left out. Today all three reach the
 *     summary. Each red asserts its absence after a presence barrier: the summary does list the issues of the plan.
 */

/** A Broker the user owns and never copied from: outside the plan, yet asked by the re-read. */
const OUTSIDE = 9;
const OUTSIDE_ID = `broker:${OUTSIDE}`;
/** An Asset added from LibreFolio, still waiting for its first price (`priceAwaitsRead`). */
const ASSET = 11;
const ASSET_ID = `asset:${ASSET}`;

/** `allocation.broker_inactive`, as `build_planner_brokers` adds it for an inactive Broker. */
function inactive(brokerId: string): SourceIssue {
    return {code: 'allocation.broker_inactive', kind: 'unsupported', severity: 'warning', path: {kind: 'field', section: 'brokers', entity_kind: 'broker', entity_id: brokerId, field: 'active'}, params: []};
}

/** Broker 7, the Broker of the plan, deactivated since the copy. */
const INACTIVE_IN_PLAN = inactive(BROKER_ID);
const INACTIVE_OUTSIDE = inactive(OUTSIDE_ID);

/** The execution-profile note of Broker 9 (`PROFILE` is Broker 7's): `build_planner_brokers` adds one for every Broker. */
const PROFILE_OUTSIDE: SourceIssue = {
    code: PROFILE_CODE,
    kind: 'unsupported',
    severity: 'error',
    path: {kind: 'field', section: 'brokers', entity_kind: 'broker', entity_id: OUTSIDE_ID, field: 'execution_profile_status'},
    params: [],
};

/** `build_planner_cash_balances`: Broker 9's USD balance is negative; the issue sits on its cash row. */
const NEGATIVE_CASH_OUTSIDE: SourceIssue = {
    code: 'allocation.negative_cash_unsupported',
    kind: 'unsupported',
    severity: 'error',
    path: {kind: 'field', section: 'cash_balances', entity_kind: 'cash_balance', entity_id: `cash:${OUTSIDE_ID}:USD`, field: 'custody_amount'},
    params: [],
};

/** `build_planner_cash_balances`: a balance of Broker 9 whose currency code is not valid; the row is dropped, the issue sits on the Broker. */
const CURRENCY_SPEC_OUTSIDE: SourceIssue = {
    code: 'allocation.currency_spec_missing',
    kind: 'missing',
    severity: 'error',
    path: {kind: 'field', section: 'cash_balances', entity_kind: 'broker', entity_id: OUTSIDE_ID, field: 'currency'},
    params: [],
};

/** `build_planner_prices`: no price for the Asset of the plan; the issue sits on the price of the requested date. */
const PRICE_MISSING: SourceIssue = {
    code: 'allocation.price_missing',
    kind: 'missing',
    severity: 'error',
    path: {kind: 'field', section: 'prices', entity_kind: 'price', entity_id: `price:${ASSET_ID}:${REREAD_AS_OF}`, field: 'amount'},
    params: [],
};

/** The issues of the re-read, in the backend's order: Brokers, cash, prices, FX quotes. */
const EVERY_OWNER_ISSUES: readonly SourceIssue[] = [INACTIVE_IN_PLAN, PROFILE, INACTIVE_OUTSIDE, PROFILE_OUTSIDE, NEGATIVE_CASH_OUTSIDE, CURRENCY_SPEC_OUTSIDE, PRICE_MISSING, SKIPPED];
/** What the cure keeps of them: the issues of Broker 7 and those that name no Broker, without the execution-profile note. */
const PLAN_ISSUES: readonly SourceIssue[] = [INACTIVE_IN_PLAN, PRICE_MISSING, SKIPPED];

/** The answer to the re-read of that plan, asked for Brokers 7 and 9, as the backend serialises it. */
function everyOwnerResponse() {
    const base = response(REREAD_AS_OF, USED, EVERY_OWNER_ISSUES);
    return {
        ...base,
        provenance: [...base.provenance, {provenance_id: 'source:market-data', kind: 'domain_copy', domain: 'market_data', source_ref: 'assets+price_history', source_label: null, captured_at: base.snapshot.generated_at}],
        assets: [{asset_id: ASSET_ID, source_asset_id: ASSET, name: 'Asset Eleven probe', ticker: null, asset_class: 'ETF', icon_url: null, active: true, provenance_id: 'source:market-data'}],
        brokers: [brokerRow(OWNER, 'Broker Seven probe', false), brokerRow(OUTSIDE, 'Broker Nine probe', false)],
        cash_balances: [cashRow(OWNER, 'USD', '2500'), cashRow(OUTSIDE, 'USD', '-120')],
        prices: [{price_id: `price:${ASSET_ID}:${REREAD_AS_OF}`, asset_id: ASSET_ID, amount: null, currency: 'USD', quote_base_quantity: '1', reference_date: null, source: null, days_before_requested: null, provenance_id: 'source:market-data'}],
    };
}

/** The plan of D1: `copiedAutoPair`, plus the Asset still waiting for its first price. Broker 9 is nowhere in the draft. */
async function planOfBrokerSeven(): Promise<{draft: PlannerDraft; plan: RefreshPlan}> {
    const {draft} = await copiedAutoPair();
    draft.addAsset(draftAssetFromInfo({id: ASSET, display_name: 'Asset Eleven probe', identifier_ticker: null, asset_type: 'ETF', icon_url: null, active: true}));
    const plan = refreshPlan(draft);
    expect(plan, 'precondition: the plan reads the Asset, the cash of Broker 7 and EUR/USD, nothing of Broker 9').toEqual({assetIds: [ASSET], cashBrokerIds: [OWNER], fxPairs: [PAIR]});
    if (!plan) throw new Error('unreachable: the plan was asserted above');
    return {draft, plan};
}

/** The re-read of that plan, asked as `refreshQuery` asks it: for every Broker the user owns, Broker 9 included. */
async function rereadAskingEveryOwner(draft: PlannerDraft, plan: RefreshPlan): Promise<PlannerSource> {
    const query = refreshQuery(draft, plan, [OWNER, OUTSIDE]);
    expect(query.brokerIds, 'precondition: the re-read asks Broker 9 too').toEqual([OWNER, OUTSIDE]);
    expect(query.sections, 'precondition: and reads Brokers and cash, so the issues of Broker 9 come with them').toEqual(['assets', 'prices', 'brokers', 'cash_balances', 'fx_quotes']);
    const source = await read(query, everyOwnerResponse());
    expect(source.issues, 'barrier: the parser kept every issue of the re-read').toEqual(EVERY_OWNER_ISSUES);
    return source;
}

describe('refreshCopiedFacts — only the issues of the plan’s Brokers (X-R45b-ui review, D1)', () => {
    it.each<[string, SourceIssue]>([
        ['broker_inactive of Broker 7, the Broker of the plan,', INACTIVE_IN_PLAN],
        ['saved_fx_skipped of EUR/USD, a pair of the plan,', SKIPPED],
        ['price_missing of the Asset of the plan, which names no Broker,', PRICE_MISSING],
    ])('GUARD: the %s stays in the summary', async (_what, issue) => {
        const {draft, plan} = await planOfBrokerSeven();
        const source = await rereadAskingEveryOwner(draft, plan);

        const summary = refreshCopiedFacts(draft, source, plan);

        expect(summary.issues).toContainEqual(issue);
    });

    it.each<[string, SourceIssue]>([
        ['broker_inactive', INACTIVE_OUTSIDE],
        ['negative_cash_unsupported on the USD balance', NEGATIVE_CASH_OUTSIDE],
        ['currency_spec_missing', CURRENCY_SPEC_OUTSIDE],
    ])('RED until the X-R45b-ui review (D1): the %s of Broker 9, owned but outside the plan, is left out', async (_what, issue) => {
        const {draft, plan} = await planOfBrokerSeven();
        const source = await rereadAskingEveryOwner(draft, plan);

        const summary = refreshCopiedFacts(draft, source, plan);

        expect(summary.issues, 'barrier: the summary lists the issues of the plan').toEqual(expect.arrayContaining([...PLAN_ISSUES]));
        expect(summary.issues).not.toContainEqual(issue);
    });
});
