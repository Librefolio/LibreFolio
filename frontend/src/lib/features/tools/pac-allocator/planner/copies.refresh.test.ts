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
import {applyAwaitingFxRates, applyLiquidityCopy, newCopyRecord, refreshCopiedFacts, refreshPlan, refreshQuery, type RefreshPlan} from './copies';
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
        brokers: [
            {
                broker_id: BROKER_ID,
                source_broker_id: OWNER,
                name: 'Broker Seven probe',
                icon_url: null,
                portal_url: null,
                default_import_plugin: null,
                access_role: 'OWNER',
                ownership_share: '1',
                observed_currencies: ['USD'],
                active: true,
                allow_cash_overdraft: false,
                allow_asset_shorting: false,
                execution_profile_status: 'not_available',
                provenance_id: 'source:broker-domain',
            },
        ],
        holdings: [],
        cash_balances: [{cash_id: `cash:${BROKER_ID}:USD`, broker_id: BROKER_ID, currency: 'USD', custody_amount: '2500', ownership_share: '1', economic_amount: '2500', provenance_id: 'source:portfolio-ledger'}],
        prices: [],
        classifications: [],
        fx_quotes: [{fx_quote_id: quoteId(fx.date), pair: PAIR, rate: fx.rate, reference_date: fx.date, source: 'ECB', days_before_requested: daysBetween(fx.date, asOf), provenance_id: 'source:saved-fx'}],
        current_distribution: null,
        issues: issues.map(wire),
    };
}

/** One read through the real parser: the endpoint answers `raw`, `fetchPlannerSource` maps it. */
async function read(query: SourceQuery, raw: ReturnType<typeof response>): Promise<PlannerSource> {
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
