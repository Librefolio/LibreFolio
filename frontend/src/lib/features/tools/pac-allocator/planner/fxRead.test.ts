// @vitest-environment jsdom
/**
 * FxRateReader: the FX step's Auto read keeps, per pair, the source issues that concern it (Vitest + jsdom).
 *
 * RED until X-R45b-ui.
 *
 * Subject. X-R45b (backend 292d7e55e): `POST /portfolio/allocation-source`, section `fx_quotes`, skips the latest
 * saved rate of a pair when it is 0 or not finite and quotes the previous valid one, with the warning
 * `allocation.saved_fx_skipped`. With no valid rate at all the quote has none, with `allocation.saved_fx_invalid`;
 * with no saved rate, `allocation.saved_fx_missing`.
 *   - The FX step reads the stored rate of every pair still waiting for one: `FxRateReader.read` →
 *     `applyAwaitingFxRates`.
 *   - The reader remembers per draft what a read learned (`attempted`, `missed`, `ownerless`) but drops the
 *     source's issues. The step cannot say that the rate it shows is an older one, nor why a stored rate was refused.
 *
 * The cure (X-R45b-ui, developer's option (a)).
 *   - The per-draft memory keeps the issues of the last read, per pair: `issues(draft, pair): SourceIssue[]`.
 *   - `read()` clears, at its start, the issues of every pair it is given, as it clears `missed` and `ownerless`.
 *   - After `applyAwaitingFxRates` each wanted pair keeps the issues of `outcome.issues` that concern it: a field path
 *     with `entity_kind === 'fx_quote'` whose quote id names the pair (`fx:<pair>:<date>:<token>`), except
 *     `allocation.saved_fx_missing`: the card already says «no stored rate».
 *
 * Scenario. Valuation USD; contributions in EUR, CHF and GBP make the scenario need EUR/USD, CHF/USD and GBP/USD. These
 * are canonical pairs: `canonicalPair` sorts the two codes, so the pair of CHF and USD is CHF/USD, never USD/CHF. The
 * snapshot of the read:
 *   - EUR/USD quoted at the rate of 2026-01-02, the rate of 2026-01-05 skipped: `saved_fx_skipped` (warning);
 *   - CHF/USD with no usable rate: its quote has `rate: null`, with `saved_fx_invalid` (error);
 *   - GBP/USD with no saved rate: `saved_fx_missing` (error), which the cure leaves out;
 *   - a price issue, of another section and another entity: it concerns no pair.
 *
 * Mocks. The Broker scope answers one Broker the user owns (`loadCopyScope`; `selectableIds` stays the real one). The
 * API client answers the allocation-source snapshot as the backend serialises it (`message_key` included); the real
 * `SourceLoad` and parser map it, on a real tool session. Nothing here talks to a server or reads translated text.
 *
 * Environment. jsdom is here for the compile target, not for the DOM: the reader's `$state` and the draft's FX closure
 * must stay live (see `request.test.ts`).
 *
 * Tests. Today `FxRateReader` has no `issues` method, which is the red of every RED test here.
 *   - GUARD (green today and after): the read fills EUR/USD with the older quoted rate and finds no stored rate for
 *     CHF/USD and GBP/USD.
 *   - RED until X-R45b-ui: EUR/USD keeps exactly the skipped-rate warning, CHF/USD exactly the invalid-rate error.
 *   - RED until X-R45b-ui: GBP/USD keeps none, because `saved_fx_missing` is left out.
 *   - RED until X-R45b-ui: a second read of EUR/USD, whose source carries no issue, clears its warning. EUR/USD holds
 *     a rate by then, so the read loads nothing for it: the clearing at the start of `read()` is what empties it.
 *   - RED until X-R45b-ui: a later read of CHF/USD, after its rates were downloaded (the step's «read again»), clears
 *     its issue and leaves the EUR/USD warning: a read clears only the pairs it is given.
 *
 * The review of X-R45b-ui (D2) adds the last block: the re-read before «Calcola» replaces what this memory holds for
 * every pair it reads again.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const allocationSource = vi.hoisted(() => vi.fn());
/** The Broker scope's answer: one Broker the user owns. */
const OWNED = vi.hoisted(() => ({id: 7, name: 'Broker Seven probe', role: 'OWNER', share: null, active: true, selectable: true, iconUrl: null, portalUrl: null, pluginCode: null}));

// source.ts and the tool client import the API client. Nothing here talks to a server: the allocation-source endpoint
// answers the snapshot each read queues.
vi.mock('$lib/api', () => ({
    zodiosApi: {get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post: allocationSource},
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

// The scope reads the Broker store; here it answers one owned Broker. `selectableIds` is the real one.
vi.mock('./scope', async (importOriginal) => ({
    ...(await importOriginal<typeof import('./scope')>()),
    loadCopyScope: vi.fn(async () => [OWNED]),
}));

import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {refreshCopiedFacts, refreshPlan, refreshQuery, setRateManual, type RefreshPlan} from './copies';
import {PlannerDraft} from './draft.svelte';
import {FxRateReader} from './fxRead.svelte';
import {fetchPlannerSource, type SourceIssue} from './source';

const EUR_USD = 'EUR/USD';
const CHF_USD = 'CHF/USD';
const GBP_USD = 'GBP/USD';
const AS_OF = '2026-01-07';
/** Tokens of the backend's `fx_key` (`sha256(source)[:12]`): `ECB` for a saved rate, `missing` for none. */
const ECB_TOKEN = '61683d66d785';
const MISSING_TOKEN = 'ffa63583dfa6';
/** The latest saved rates, 0 or not finite. */
const SKIPPED_DATE = '2026-01-05';
/** The previous valid EUR/USD rate, quoted instead. */
const USED = {rate: '1.0950', date: '2026-01-02'};
/** The CHF/USD rate downloaded later, read again by the step. */
const DOWNLOADED = {rate: '1.1300', date: '2026-01-06'};

function quoteId(pair: string, date: string, token = ECB_TOKEN): string {
    return `fx:${pair}:${date}:${token}`;
}

/** `allocation.saved_fx_skipped` as `fx_quotes.py` builds it, after the parser: on the quote actually used. */
const SKIPPED: SourceIssue = {
    code: 'allocation.saved_fx_skipped',
    kind: 'invalid',
    severity: 'warning',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(EUR_USD, USED.date), field: 'rate'},
    params: [
        {kind: 'text', name: 'pair', value: EUR_USD},
        {kind: 'date', name: 'skipped_date', value: SKIPPED_DATE},
        {kind: 'date', name: 'used_date', value: USED.date},
    ],
};

/** The latest CHF/USD rate is unusable and no valid one precedes it: the quote keeps its date and has no rate. */
const INVALID: SourceIssue = {
    code: 'allocation.saved_fx_invalid',
    kind: 'invalid',
    severity: 'error',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(CHF_USD, SKIPPED_DATE), field: 'rate'},
    params: [{kind: 'text', name: 'pair', value: CHF_USD}],
};

/** No saved GBP/USD rate: the quote id carries the requested date and the `missing` token. */
const MISSING: SourceIssue = {
    code: 'allocation.saved_fx_missing',
    kind: 'missing',
    severity: 'error',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(GBP_USD, AS_OF, MISSING_TOKEN), field: 'rate'},
    params: [{kind: 'text', name: 'pair', value: GBP_USD}],
};

/** An issue of another section and another entity: it concerns no pair. */
const PRICE: SourceIssue = {
    code: 'allocation.price_missing',
    kind: 'missing',
    severity: 'error',
    path: {kind: 'field', section: 'prices', entity_kind: 'price', entity_id: `price:asset:11:${AS_OF}`, field: 'amount'},
    params: [],
};

/** One `fx_quotes` row, as the backend serialises it. */
function quoteRow(pair: string, rate: string | null, date: string | null, id: string) {
    return {fx_quote_id: id, pair, rate, reference_date: date, source: date === null ? null : 'ECB', days_before_requested: date === null ? null : 1, provenance_id: 'source:saved-fx'};
}

const EUR_USD_ROW = quoteRow(EUR_USD, USED.rate, USED.date, quoteId(EUR_USD, USED.date));
const CHF_USD_ROW = quoteRow(CHF_USD, null, SKIPPED_DATE, quoteId(CHF_USD, SKIPPED_DATE));
const GBP_USD_ROW = quoteRow(GBP_USD, null, null, quoteId(GBP_USD, AS_OF, MISSING_TOKEN));

/** The answer to an FX read, as the backend serialises it: the parser drops `message_key`. */
function response(quotes: readonly ReturnType<typeof quoteRow>[], issues: readonly SourceIssue[]) {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        snapshot: {as_of: AS_OF, target_currency: 'USD', generated_at: generatedAt},
        provenance: [
            {provenance_id: 'source:portfolio-ledger', kind: 'domain_copy', domain: 'portfolio', source_ref: 'transactions+broker_user_access', source_label: null, captured_at: generatedAt},
            {provenance_id: 'source:saved-fx', kind: 'domain_copy', domain: 'fx', source_ref: 'fx_rates', source_label: null, captured_at: generatedAt},
        ],
        assets: [],
        brokers: [],
        holdings: [],
        cash_balances: [],
        prices: [],
        classifications: [],
        fx_quotes: quotes,
        current_distribution: null,
        issues: issues.map((issue) => ({...issue, message_key: issue.code})),
    };
}

/** Valuation USD; a contribution in EUR, one in CHF and one in GBP: three pairs, all waiting for their first rate. */
function scenario(): PlannerDraft {
    const draft = new PlannerDraft('USD');
    for (const currency of ['EUR', 'CHF', 'GBP']) draft.addContribution(currency, `${currency} savings`);
    expect(draft.requiredPairs, 'precondition: the scenario needs the three canonical pairs').toEqual([CHF_USD, EUR_USD, GBP_USD]);
    return draft;
}

/** The FX step's first read of the three pairs, answered by the snapshot of the scenario. */
async function firstRead(): Promise<{draft: PlannerDraft; reader: FxRateReader}> {
    const draft = scenario();
    const reader = new FxRateReader();
    allocationSource.mockResolvedValueOnce(response([CHF_USD_ROW, EUR_USD_ROW, GBP_USD_ROW], [SKIPPED, INVALID, MISSING, PRICE]));
    await reader.read(draft, [EUR_USD, CHF_USD, GBP_USD], getClientSessionGeneration());
    expect(allocationSource, 'barrier: the read loaded one snapshot').toHaveBeenCalledTimes(1);
    expect(reader.error, 'barrier: the read did not fail').toBeNull();
    return {draft, reader};
}

/** `FxRateReader.issues(draft, pair)`, the accessor of the cure: its absence is today's red. */
function issuesOf(reader: FxRateReader, draft: PlannerDraft, pair: string): SourceIssue[] {
    expect(typeof reader.issues, 'FxRateReader.issues(draft, pair) (X-R45b-ui)').toBe('function');
    return reader.issues(draft, pair);
}

let nextUser = 90;

beforeEach(() => {
    allocationSource.mockReset();
    transitionClientSession(++nextUser);
});

describe('FxRateReader — the issues of the Auto read, per pair (X-R45b-ui)', () => {
    it('GUARD: the read fills EUR/USD with the older quoted rate and finds no stored rate for CHF/USD and GBP/USD', async () => {
        const {draft, reader} = await firstRead();

        const [body] = allocationSource.mock.calls[0];
        expect(body).toMatchObject({requested_sections: ['fx_quotes'], broker_ids: [OWNED.id]});
        expect([...body.fx_pairs].sort()).toEqual([CHF_USD, EUR_USD, GBP_USD]);
        expect(draft.fx(EUR_USD)).toMatchObject({rate: USED.rate, referenceDate: USED.date, manual: false});
        expect(reader.notStored(draft, EUR_USD)).toBe(false);
        expect(reader.notStored(draft, CHF_USD)).toBe(true);
        expect(reader.notStored(draft, GBP_USD)).toBe(true);
    });

    it('RED until X-R45b-ui: EUR/USD keeps exactly the skipped-rate warning, CHF/USD exactly the invalid-rate error', async () => {
        const {draft, reader} = await firstRead();

        expect(issuesOf(reader, draft, EUR_USD)).toEqual([SKIPPED]);
        expect(issuesOf(reader, draft, CHF_USD)).toEqual([INVALID]);
    });

    it('RED until X-R45b-ui: GBP/USD keeps no issue — saved_fx_missing is left out, the card already says «no stored rate»', async () => {
        const {draft, reader} = await firstRead();
        expect(reader.notStored(draft, GBP_USD), 'barrier: the read found no stored GBP/USD rate').toBe(true);
        expect(issuesOf(reader, draft, EUR_USD), 'barrier: the same read kept the issue of another pair').toEqual([SKIPPED]);

        expect(issuesOf(reader, draft, GBP_USD)).toEqual([]);
    });

    it('RED until X-R45b-ui: a second read of EUR/USD, whose source carries no issue, clears its warning', async () => {
        const {draft, reader} = await firstRead();
        expect(issuesOf(reader, draft, EUR_USD), 'barrier: the first read kept the warning').toEqual([SKIPPED]);

        allocationSource.mockResolvedValueOnce(response([EUR_USD_ROW], []));
        await reader.read(draft, [EUR_USD], getClientSessionGeneration());

        expect(reader.error).toBeNull();
        expect(issuesOf(reader, draft, EUR_USD)).toEqual([]);
    });

    it('RED until X-R45b-ui: a later read of CHF/USD, its rates downloaded, clears its issue and leaves the EUR/USD warning', async () => {
        const {draft, reader} = await firstRead();
        expect(issuesOf(reader, draft, CHF_USD), 'barrier: the first read kept the invalid-rate error').toEqual([INVALID]);

        allocationSource.mockResolvedValueOnce(response([quoteRow(CHF_USD, DOWNLOADED.rate, DOWNLOADED.date, quoteId(CHF_USD, DOWNLOADED.date))], []));
        await reader.read(draft, [CHF_USD], getClientSessionGeneration());
        expect(allocationSource, 'barrier: the second read loaded its snapshot').toHaveBeenCalledTimes(2);
        expect(draft.fx(CHF_USD)?.rate, 'barrier: the downloaded rate was read').toBe(DOWNLOADED.rate);

        expect(issuesOf(reader, draft, CHF_USD)).toEqual([]);
        expect(issuesOf(reader, draft, EUR_USD), 'a read clears only the pairs it is given').toEqual([SKIPPED]);
    });
});

// -- The review of X-R45b-ui, D2: the re-read and the step's memory ---------------------------------------------------

/*
 * D2 — the FX card keeps an old warning after the re-read.
 *   - The step's read remembers, per draft, what the source said about each pair (`FxRateReader.issues`, a module
 *     WeakMap keyed by the draft). Only a new `FxRateReader.read` resets it.
 *   - The re-read before «Calcola» (`refreshCopiedFacts`) rewrites the pair's rate, copy, stamp, date and source, but
 *     not that memory.
 *   - So once «Calcola» has read the corrected D2, the card still warns that D2 was skipped; and a skip only the re-read
 *     found never reaches the card.
 *
 * The cure: `refreshCopiedFacts`, for every pair of `plan.fxPairs` it reads again, replaces the remembered issues with
 * what the re-read said about that pair: its `fx_quote` issues but `saved_fx_missing`, the reader's own filter. Nothing
 * about the pair clears it.
 *   - It reads again the pairs still copied or still waiting: not those its first `continue` skips.
 *   - A pair outside the plan (a Manual one) keeps its memory.
 *
 * Observed through the existing public API only: `refreshCopiedFacts`, and the `issues` of a *fresh* `FxRateReader`,
 * which reads the per-draft memory as the step does when the user comes back. The cure may move the memory to another
 * module, so nothing new is imported: every red fails on an assertion.
 *
 * Scenario: valuation USD, a contribution in CHF and one in EUR, so the step shows CHF/USD and EUR/USD. For CHF/USD, D2
 * (2026-01-05) is the latest saved rate and D1 (2026-01-02) the previous valid one. The re-read runs as
 * `PacPlannerTool.refreshCopies` runs it: `refreshPlan`, `refreshQuery` for the owned Broker, one load,
 * `refreshCopiedFacts`.
 *
 * Tests.
 *   - RED until the X-R45b-ui review (D2):
 *       (a) the re-read of the corrected D2 clears the skip warning the step remembered;
 *       (b) a skip only the re-read found is remembered for its pair;
 *       (e) a pair still waiting, which the re-read finds with no saved rate at all, forgets its invalid-rate error.
 *           It is read again but stops at the second `continue` (no rate): the replacement must not depend on a rate.
 *   - GUARD (green before and after):
 *       (c) a Manual pair, outside the plan, keeps its memory;
 *       (c2) a pair switched to Manual while the re-read runs (its first `continue`) keeps its memory;
 *       (d) an issue the re-read reports for EUR/USD does not land on CHF/USD.
 */

/** CHF/USD: D2, its latest saved rate, and D1, the previous valid one. */
const CHF_D1 = {rate: '1.1250', date: USED.date};
const CHF_D2 = {rate: '1.1310', date: SKIPPED_DATE};
const CHF_AT_D1 = quoteRow(CHF_USD, CHF_D1.rate, CHF_D1.date, quoteId(CHF_USD, CHF_D1.date));
const CHF_AT_D2 = quoteRow(CHF_USD, CHF_D2.rate, CHF_D2.date, quoteId(CHF_USD, CHF_D2.date));
/** No saved CHF/USD rate at all: the user deleted the one that was not valid. */
const CHF_NONE = quoteRow(CHF_USD, null, null, quoteId(CHF_USD, AS_OF, MISSING_TOKEN));

/** `saved_fx_skipped` of CHF/USD: D2 skipped, D1 used, on the quote of D1. */
const CHF_SKIPPED: SourceIssue = {
    code: 'allocation.saved_fx_skipped',
    kind: 'invalid',
    severity: 'warning',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(CHF_USD, CHF_D1.date), field: 'rate'},
    params: [
        {kind: 'text', name: 'pair', value: CHF_USD},
        {kind: 'date', name: 'skipped_date', value: CHF_D2.date},
        {kind: 'date', name: 'used_date', value: CHF_D1.date},
    ],
};

/** `saved_fx_missing` of CHF/USD: no saved rate. */
const CHF_MISSING: SourceIssue = {
    code: 'allocation.saved_fx_missing',
    kind: 'missing',
    severity: 'error',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(CHF_USD, AS_OF, MISSING_TOKEN), field: 'rate'},
    params: [{kind: 'text', name: 'pair', value: CHF_USD}],
};

type QuoteRow = ReturnType<typeof quoteRow>;

/** Valuation USD; a contribution in CHF and one in EUR: CHF/USD and EUR/USD, both waiting for their first rate. */
function chfAndEur(): PlannerDraft {
    const draft = new PlannerDraft('USD');
    for (const currency of ['CHF', 'EUR']) draft.addContribution(currency, `${currency} savings`);
    expect(draft.requiredPairs, 'precondition: the scenario needs CHF/USD and EUR/USD').toEqual([CHF_USD, EUR_USD]);
    return draft;
}

/** The FX step's read of both pairs, answered by `quotes` and `issues`. */
async function stepRead(draft: PlannerDraft, quotes: readonly QuoteRow[], issues: readonly SourceIssue[]): Promise<void> {
    const reader = new FxRateReader();
    allocationSource.mockResolvedValueOnce(response(quotes, issues));
    await reader.read(draft, draft.requiredPairs, getClientSessionGeneration());
    expect(reader.error, 'barrier: the step’s read did not fail').toBeNull();
}

/** What the step lists for `pair` when the user comes back to it: a fresh reader, the draft's memory. */
function remembered(draft: PlannerDraft, pair: string): SourceIssue[] {
    return new FxRateReader().issues(draft, pair);
}

/**
 * The re-read before «Calcola», as `PacPlannerTool.refreshCopies` runs it: the plan of the copied rates, its query for
 * the owned Broker, one load answered by `quotes` and `issues`, then `refreshCopiedFacts`. `meanwhile` is what the user
 * does while the load is out: after the plan, before the apply.
 */
async function rereadBeforeCalcola(draft: PlannerDraft, quotes: readonly QuoteRow[], issues: readonly SourceIssue[], meanwhile: () => void = () => {}): Promise<RefreshPlan> {
    const plan = refreshPlan(draft);
    expect(plan, 'precondition: the draft has copied rates to read again').not.toBeNull();
    if (!plan) throw new Error('unreachable: the plan was asserted above');
    allocationSource.mockResolvedValueOnce(response(quotes, issues));
    const source = await fetchPlannerSource(refreshQuery(draft, plan, [OWNED.id]), getClientSessionGeneration());
    meanwhile();
    refreshCopiedFacts(draft, source, plan);
    return plan;
}

describe('refreshCopiedFacts — what the FX step remembers of each pair (X-R45b-ui review, D2)', () => {
    it('RED until the X-R45b-ui review (D2): (a) the re-read of the corrected D2 clears the skip warning the step remembered', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_AT_D1, EUR_USD_ROW], [CHF_SKIPPED]);
        expect(remembered(draft, CHF_USD), 'barrier: the step remembers «D2 skipped, D1 used»').toEqual([CHF_SKIPPED]);

        const plan = await rereadBeforeCalcola(draft, [CHF_AT_D2, EUR_USD_ROW], []);
        expect(plan.fxPairs, 'precondition: the re-read reads CHF/USD again').toContain(CHF_USD);
        expect(draft.fx(CHF_USD), 'barrier: the pair now holds the corrected D2, still Auto').toMatchObject({rate: CHF_D2.rate, referenceDate: CHF_D2.date, manual: false});

        expect(remembered(draft, CHF_USD)).toEqual([]);
    });

    it('RED until the X-R45b-ui review (D2): (b) a skip only the re-read found is remembered for its pair', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_AT_D1, EUR_USD_ROW], []);
        expect(remembered(draft, CHF_USD), 'barrier: the step read D1, then the latest rate, and had nothing to say').toEqual([]);

        const plan = await rereadBeforeCalcola(draft, [CHF_AT_D1, EUR_USD_ROW], [CHF_SKIPPED]);
        expect(plan.fxPairs, 'precondition: the re-read reads CHF/USD again').toContain(CHF_USD);
        expect(draft.fx(CHF_USD), 'barrier: the pair keeps D1, the rate the re-read quoted').toMatchObject({rate: CHF_D1.rate, referenceDate: CHF_D1.date, manual: false});

        expect(remembered(draft, CHF_USD)).toEqual([CHF_SKIPPED]);
    });

    it('RED until the X-R45b-ui review (D2): (e) a pair still waiting, which the re-read finds with no saved rate at all, forgets its invalid-rate error', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_USD_ROW, EUR_USD_ROW], [INVALID]);
        expect(remembered(draft, CHF_USD), 'barrier: the step remembers that the saved rate is not valid').toEqual([INVALID]);
        expect(draft.fx(CHF_USD), 'barrier: and CHF/USD has no rate').toBeUndefined();

        const plan = await rereadBeforeCalcola(draft, [CHF_NONE, EUR_USD_ROW], [CHF_MISSING]);
        expect(plan.fxPairs, 'precondition: the re-read reads the waiting CHF/USD again').toContain(CHF_USD);
        expect(draft.fx(CHF_USD), 'barrier: still no rate').toBeUndefined();

        expect(remembered(draft, CHF_USD), 'what the re-read said about CHF/USD, but saved_fx_missing: nothing').toEqual([]);
    });

    it('GUARD: (c) a Manual pair, outside the re-read plan, keeps what the step remembered about it', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_AT_D1, EUR_USD_ROW], [CHF_SKIPPED]);
        setRateManual(draft, CHF_USD, true);
        expect(remembered(draft, CHF_USD), 'barrier: the step remembers the skip').toEqual([CHF_SKIPPED]);

        const plan = await rereadBeforeCalcola(draft, [EUR_USD_ROW], []);
        expect(plan.fxPairs, 'precondition: the Manual pair is not in the plan').toEqual([EUR_USD]);

        expect(remembered(draft, CHF_USD)).toEqual([CHF_SKIPPED]);
    });

    it('GUARD: (c2) a pair switched to Manual while the re-read runs is not read again, and keeps its memory', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_AT_D1, EUR_USD_ROW], [CHF_SKIPPED]);
        expect(remembered(draft, CHF_USD), 'barrier: the step remembers the skip').toEqual([CHF_SKIPPED]);

        const plan = await rereadBeforeCalcola(draft, [CHF_AT_D2, EUR_USD_ROW], [], () => setRateManual(draft, CHF_USD, true));
        expect(plan.fxPairs, 'precondition: CHF/USD was in the plan').toContain(CHF_USD);
        expect(draft.fx(CHF_USD), 'barrier: the re-read skipped the Manual pair, which keeps D1').toMatchObject({rate: CHF_D1.rate, manual: true});

        expect(remembered(draft, CHF_USD)).toEqual([CHF_SKIPPED]);
    });

    it('GUARD: (d) an issue the re-read reports for EUR/USD does not land on CHF/USD', async () => {
        const draft = chfAndEur();
        await stepRead(draft, [CHF_AT_D1, EUR_USD_ROW], []);

        const plan = await rereadBeforeCalcola(draft, [CHF_AT_D2, EUR_USD_ROW], [SKIPPED]);
        expect(plan.fxPairs, 'precondition: both pairs are read again').toEqual([CHF_USD, EUR_USD]);
        expect(draft.fx(CHF_USD)?.rate, 'barrier: CHF/USD was read again').toBe(CHF_D2.rate);

        expect(remembered(draft, CHF_USD)).toEqual([]);
    });
});
