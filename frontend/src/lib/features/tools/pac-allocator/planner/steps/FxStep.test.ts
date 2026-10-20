// @vitest-environment jsdom
/**
 * FxStep: each pair's card lists the issues the Auto read found for that pair (Vitest + jsdom).
 *
 * RED until X-R45b-ui.
 *
 * Subject. X-R45b (backend 292d7e55e): the allocation source skips a saved FX rate of 0 or not finite and quotes the
 * previous valid one, with the warning `allocation.saved_fx_skipped` (pair, skipped_date, used_date). With no valid
 * rate at all the quote has none, with `allocation.saved_fx_invalid`. The FX step reads the stored rates of the pairs
 * it needs when it opens (`onMount` → `FxRateReader.read`), but the read drops the source's issues. A card then shows
 * an older rate without a word about the skipped one, and a refused stored rate as a plain «no rate».
 *
 * The cure (X-R45b-ui, developer's option (a)). In each pair card (`pac-planner-fx-pair`, `data-pair`), after the
 * rate/status block, only in Auto and only when `reader.issues(draft, pair)` is not empty: an `IssueList` with testid
 * `pac-planner-fx-issues` (items `pac-planner-fx-issues-item`, with `data-code` and `data-severity`), built with
 * `presentSourceIssues(issues, draft, source)` + `listIssue`. `allocation.saved_fx_missing` is never listed, because the
 * card already says «no stored rate» (see `../fxRead.test.ts` for the reader's side).
 *
 * Scenario. Valuation USD; contributions in EUR, CHF and GBP make the step show three cards: EUR/USD, CHF/USD and
 * GBP/USD. These are the canonical pairs: `canonicalPair` sorts the two codes, so the pair of CHF and USD is CHF/USD.
 * The snapshot quotes EUR/USD at the rate of 2026-01-02 (the rate of 2026-01-05 skipped, `saved_fx_skipped`), CHF/USD
 * with no rate (`saved_fx_invalid`), GBP/USD with no rate (`saved_fx_missing`), and carries one price issue, which
 * concerns no pair.
 *
 * Mounting. As `PacPlannerTool` mounts it: `<FxStep {draft} {accountGeneration} />`. The step's own reader reads the
 * pending pairs on mount. The tests wait for that read to settle on what it produces, polled with a deadline and never
 * on the clock: the step's `data-busy`, the EUR/USD rate, the «no stored rate» state of CHF/USD and GBP/USD.
 *
 * Mocks. The Broker scope answers one Broker the user owns. The API client answers the allocation-source snapshot as
 * the backend serialises it; the real reader, `SourceLoad` and parser map it, on a real tool session. The FX routes
 * endpoint answers no route, so a pair with no stored rate offers «Add the pair»; the currency catalogue answers empty.
 * Any other call resolves to nothing.
 *
 * Expectations. The message of the EUR/USD item is the catalogue's own sentence for the issue key, with the issue's
 * params, looked up here after `setupI18n`: never hand-typed. A control checks that the sentence carries the pair and
 * both dates.
 *
 * Absence. Every «no list» assertion follows a presence barrier: for GBP/USD its «no rate» status and the EUR/USD list;
 * after the switch to Manual, the card's manual rate field and the CHF/USD list.
 *
 * Tests. Today no card lists an issue, which is the red of every RED test here.
 *   - GUARD (green today and after): the read on mount shows EUR/USD in Auto with the older quoted rate, and CHF/USD
 *     and GBP/USD with their «no rate» status.
 *   - RED until X-R45b-ui: the EUR/USD card lists the skipped-rate warning, with its pair and both dates.
 *   - RED until X-R45b-ui: the CHF/USD card lists one item, the invalid-rate error.
 *   - RED until X-R45b-ui: the GBP/USD card lists nothing (`saved_fx_missing` left out), and keeps its «no rate» status.
 *   - RED until X-R45b-ui: switched to Manual, the EUR/USD card lists nothing.
 *
 * The review of X-R45b-ui (D2) adds the last block: back on the step after «Calcola» read the corrected D2, the card
 * no longer lists the warning about D2.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {get} from 'svelte/store';

const allocationSource = vi.hoisted(() => vi.fn());
const listRoutes = vi.hoisted(() => vi.fn());
/** The Broker scope's answer: one Broker the user owns. */
const OWNED = vi.hoisted(() => ({id: 7, name: 'Broker Seven probe', role: 'OWNER', share: null, active: true, selectable: true, iconUrl: null, portalUrl: null, pluginCode: null}));

// The reader, the FX setup and the currency codes import the API client. Nothing here talks to a server: the
// allocation-source endpoint answers the queued snapshot, the FX routes endpoint answers no route, the currency
// catalogue answers empty (the codes show bare, as before a catalogue loads), any other call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get: (_target, key) => {
                if (key === 'get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post') return allocationSource;
                if (key === 'list_routes_api_v1_fx_providers_routes_get') return listRoutes;
                if (key === 'list_currencies_api_v1_utilities_currencies_get') return async () => ({items: []});
                return vi.fn(async () => undefined);
            },
        },
    ),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

// The scope reads the Broker store; here it answers one owned Broker. `selectableIds` is the real one.
vi.mock('../scope', async (importOriginal) => ({
    ...(await importOriginal<typeof import('../scope')>()),
    loadCopyScope: vi.fn(async () => [OWNED]),
}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_} from '$lib/i18n';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {refreshCopiedFacts, refreshPlan, refreshQuery} from '../copies';
import {PlannerDraft} from '../draft.svelte';
import {formatPlannerFxRate} from '../format';
import {fetchPlannerSource, type SourceIssue} from '../source';
import FxStep from './FxStep.svelte';

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
const SKIPPED_CODE = 'allocation.saved_fx_skipped';
const INVALID_CODE = 'allocation.saved_fx_invalid';
/** The message key of an issue (C3): `tools.pacAllocator.planner.issues.<code>`. */
const SKIPPED_KEY = `tools.pacAllocator.planner.issues.${SKIPPED_CODE}`;

function quoteId(pair: string, date: string, token = ECB_TOKEN): string {
    return `fx:${pair}:${date}:${token}`;
}

/** `allocation.saved_fx_skipped` as `fx_quotes.py` builds it: on the quote actually used. */
const SKIPPED: SourceIssue = {
    code: SKIPPED_CODE,
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
    code: INVALID_CODE,
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

const CHF_USD_ROW = quoteRow(CHF_USD, null, SKIPPED_DATE, quoteId(CHF_USD, SKIPPED_DATE));
const EUR_USD_ROW = quoteRow(EUR_USD, USED.rate, USED.date, quoteId(EUR_USD, USED.date));
const GBP_USD_ROW = quoteRow(GBP_USD, null, null, quoteId(GBP_USD, AS_OF, MISSING_TOKEN));

/** An answer to a read of the FX quotes, as the backend serialises it: the parser drops `message_key`. By default, the step's read of the three pairs. */
function response(quotes: readonly ReturnType<typeof quoteRow>[] = [CHF_USD_ROW, EUR_USD_ROW, GBP_USD_ROW], issues: readonly SourceIssue[] = [SKIPPED, INVALID, MISSING, PRICE]) {
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
        fx_quotes: [...quotes],
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

/** The card of `pair`: exactly one. */
function card(pair: string): HTMLElement {
    const cards = screen.getAllByTestId('pac-planner-fx-pair').filter((element) => element.dataset.pair === pair);
    expect(cards, `one card for ${pair}`).toHaveLength(1);
    return cards[0];
}

/** The issue items listed in the card of `pair`. */
function listedIn(pair: string): HTMLElement[] {
    const list = within(card(pair)).getByTestId('pac-planner-fx-issues');
    return within(list).getAllByTestId('pac-planner-fx-issues-item');
}

/** Mounts the step as `PacPlannerTool` does, then waits for the read it starts on mount to settle on what it produces. */
async function mountAndRead(): Promise<void> {
    const draft = scenario();
    allocationSource.mockResolvedValueOnce(response());
    render(FxStep, {draft, accountGeneration: getClientSessionGeneration()});
    await waitFor(
        () => {
            expect(allocationSource, 'the read loaded its snapshot').toHaveBeenCalledTimes(1);
            expect(screen.getByTestId('pac-planner-fx')).toHaveAttribute('data-busy', 'false');
            expect(card(EUR_USD)).toHaveAttribute('data-rate', 'set');
            expect(card(CHF_USD)).toHaveAttribute('data-read', 'not-stored');
            expect(card(GBP_USD)).toHaveAttribute('data-read', 'not-stored');
        },
        {timeout: 3_000},
    );
}

/** The catalogue's sentence for the skipped-rate warning, with the issue's own params. */
function skippedSentence(): string {
    const sentence = get(_)(SKIPPED_KEY, {values: {pair: EUR_USD, skipped_date: SKIPPED_DATE, used_date: USED.date}});
    expect(sentence, 'control: the catalogue has the key').not.toBe(SKIPPED_KEY);
    for (const value of [EUR_USD, SKIPPED_DATE, USED.date]) expect(sentence, `control: the sentence carries ${value}`).toContain(value);
    return sentence;
}

let nextUser = 100;

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    allocationSource.mockReset();
    listRoutes.mockReset();
    listRoutes.mockResolvedValue({items: []});
    transitionClientSession(++nextUser);
});

afterEach(() => {
    cleanup();
});

describe('FxStep — the issues of the Auto read, in each pair card (X-R45b-ui)', () => {
    it('GUARD: the read on mount shows EUR/USD in Auto with the older quoted rate, CHF/USD and GBP/USD with their «no rate» status', async () => {
        await mountAndRead();

        const [body] = allocationSource.mock.calls[0];
        expect([...body.fx_pairs].sort(), 'the read covered the three pairs').toEqual([CHF_USD, EUR_USD, GBP_USD]);
        expect(card(EUR_USD)).toHaveAttribute('data-mode', 'auto');
        expect(within(card(EUR_USD)).getByTestId('pac-planner-fx-rate-value').textContent).toContain(formatPlannerFxRate(USED.rate));
        for (const pair of [CHF_USD, GBP_USD]) {
            expect(card(pair)).toHaveAttribute('data-mode', 'auto');
            expect(within(card(pair)).getByTestId('pac-planner-fx-no-rate'), `${pair} keeps its «no rate» status`).toBeInTheDocument();
        }
    });

    it('RED until X-R45b-ui: the EUR/USD card lists the skipped-rate warning, with its pair and both dates', async () => {
        await mountAndRead();
        const expected = skippedSentence();

        const items = listedIn(EUR_USD);

        expect(items, 'one issue for EUR/USD, one item').toHaveLength(1);
        const [item] = items;
        expect(item).toHaveAttribute('data-code', SKIPPED_CODE);
        expect(item).toHaveAttribute('data-severity', 'warning');
        expect(item.textContent).toContain(expected);
    });

    it('RED until X-R45b-ui: the CHF/USD card lists one item, the invalid-rate error', async () => {
        await mountAndRead();

        const items = listedIn(CHF_USD);

        expect(items, 'one issue for CHF/USD, one item').toHaveLength(1);
        const [item] = items;
        expect(item).toHaveAttribute('data-code', INVALID_CODE);
        expect(item).toHaveAttribute('data-severity', 'error');
    });

    it('RED until X-R45b-ui: the GBP/USD card lists nothing — saved_fx_missing is left out — and keeps its «no rate» status', async () => {
        await mountAndRead();
        expect(within(card(GBP_USD)).getByTestId('pac-planner-fx-no-rate'), 'barrier: the «no rate» status of GBP/USD').toBeInTheDocument();
        expect(listedIn(EUR_USD), 'barrier: the step lists the issues of another pair').toHaveLength(1);

        expect(within(card(GBP_USD)).queryByTestId('pac-planner-fx-issues')).toBeNull();
    });

    it('RED until X-R45b-ui: switched to Manual, the EUR/USD card lists nothing', async () => {
        await mountAndRead();
        expect(listedIn(EUR_USD), 'barrier: in Auto the card lists its warning').toHaveLength(1);

        await fireEvent.click(within(card(EUR_USD)).getByTestId('pac-planner-fx-mode-manual'));

        expect(card(EUR_USD), 'barrier: the card switched to Manual').toHaveAttribute('data-mode', 'manual');
        expect(within(card(EUR_USD)).getByTestId('pac-planner-fx-rate-manual'), 'barrier: and shows the manual rate field').toBeInTheDocument();
        expect(listedIn(CHF_USD), 'barrier: the CHF/USD card, still in Auto, keeps its list').toHaveLength(1);
        expect(within(card(EUR_USD)).queryByTestId('pac-planner-fx-issues')).toBeNull();
    });
});

// -- The review of X-R45b-ui, D2: back on the step after «Calcola» ----------------------------------------------------

/*
 * D2 on screen, the reviewer's scenario.
 *   - The step's read finds CHF/USD's latest saved rate D2 (2026-01-05) not valid and quotes D1 (2026-01-02): the card
 *     lists «D2 skipped, D1 used».
 *   - The user corrects D2 in LibreFolio and presses «Calcola»: `refreshCopiedFacts` reads the corrected D2 into the
 *     pair, as `PacPlannerTool.refreshCopies` does (`refreshPlan`, `refreshQuery` for the owned Broker, one load).
 *   - Back on the step, the card shows D2's rate beside the warning about D2: the re-read never touched what the step
 *     remembers of the pair (`FxRateReader.issues`, kept per draft).
 *
 * The cure: the re-read replaces what is remembered of every pair it reads again (see `../fxRead.test.ts`, D2).
 *
 * Leaving the step is an unmount and coming back a new mount, as when `PacPlannerTool` shows the result and the user
 * returns to the step. Every pair has been read once by then, so the new mount reads nothing: what it lists is memory.
 *
 * Absence. EUR/USD has the same skip at both reads, still true after «Calcola»: its list, before and after the cure, is
 * the presence barrier of the CHF/USD list that must be gone.
 */

/** CHF/USD: D2, its latest saved rate, and D1, the previous valid one. */
const CHF_D1 = {rate: '1.1250', date: USED.date};
const CHF_D2 = {rate: '1.1310', date: SKIPPED_DATE};
const CHF_AT_D1 = quoteRow(CHF_USD, CHF_D1.rate, CHF_D1.date, quoteId(CHF_USD, CHF_D1.date));
const CHF_AT_D2 = quoteRow(CHF_USD, CHF_D2.rate, CHF_D2.date, quoteId(CHF_USD, CHF_D2.date));

/** `saved_fx_skipped` of CHF/USD: D2 skipped, D1 used, on the quote of D1. */
const CHF_SKIPPED: SourceIssue = {
    code: SKIPPED_CODE,
    kind: 'invalid',
    severity: 'warning',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: quoteId(CHF_USD, CHF_D1.date), field: 'rate'},
    params: [
        {kind: 'text', name: 'pair', value: CHF_USD},
        {kind: 'date', name: 'skipped_date', value: CHF_D2.date},
        {kind: 'date', name: 'used_date', value: CHF_D1.date},
    ],
};

/** Valuation USD; a contribution in CHF and one in EUR: CHF/USD and EUR/USD, both waiting for their first rate. */
function chfAndEur(): PlannerDraft {
    const draft = new PlannerDraft('USD');
    for (const currency of ['CHF', 'EUR']) draft.addContribution(currency, `${currency} savings`);
    expect(draft.requiredPairs, 'precondition: the scenario needs CHF/USD and EUR/USD').toEqual([CHF_USD, EUR_USD]);
    return draft;
}

/** The codes the card of `pair` lists. */
function codesIn(pair: string): (string | undefined)[] {
    return listedIn(pair).map((item) => item.dataset.code);
}

describe('FxStep — back on the step after the re-read before «Calcola» (X-R45b-ui review, D2)', () => {
    it('RED until the X-R45b-ui review (D2): the CHF/USD card shows the corrected D2 rate and no longer the warning about D2', async () => {
        const accountGeneration = getClientSessionGeneration();
        const draft = chfAndEur();

        // The step opens and reads: D2 skipped for D1 on CHF/USD, and the same on EUR/USD.
        allocationSource.mockResolvedValueOnce(response([CHF_AT_D1, EUR_USD_ROW], [CHF_SKIPPED, SKIPPED]));
        const step = render(FxStep, {draft, accountGeneration});
        await waitFor(
            () => {
                expect(allocationSource, 'the step’s read loaded its snapshot').toHaveBeenCalledTimes(1);
                expect(screen.getByTestId('pac-planner-fx')).toHaveAttribute('data-busy', 'false');
                expect(card(CHF_USD)).toHaveAttribute('data-rate', 'set');
                expect(card(EUR_USD)).toHaveAttribute('data-rate', 'set');
            },
            {timeout: 3_000},
        );
        expect(codesIn(CHF_USD), 'barrier: before «Calcola» the CHF/USD card lists the skip of D2').toEqual([SKIPPED_CODE]);

        // The user leaves the step, corrects D2 in LibreFolio and presses «Calcola»: the copied rates are read again.
        step.unmount();
        const plan = refreshPlan(draft);
        expect(plan?.fxPairs, 'precondition: both copied rates are read again').toEqual([CHF_USD, EUR_USD]);
        if (!plan) throw new Error('unreachable: the plan was asserted above');
        allocationSource.mockResolvedValueOnce(response([CHF_AT_D2, EUR_USD_ROW], [SKIPPED]));
        const source = await fetchPlannerSource(refreshQuery(draft, plan, [OWNED.id]), accountGeneration);
        refreshCopiedFacts(draft, source, plan);
        expect(draft.fx(CHF_USD), 'barrier: the re-read put the corrected D2 into the pair, still Auto').toMatchObject({rate: CHF_D2.rate, referenceDate: CHF_D2.date, manual: false});

        // The user comes back to the step.
        render(FxStep, {draft, accountGeneration});
        expect(screen.getByTestId('pac-planner-fx'), 'barrier: the step reads nothing on its own, every pair was read').toHaveAttribute('data-busy', 'false');
        expect(allocationSource, 'barrier: no third load').toHaveBeenCalledTimes(2);
        expect(card(CHF_USD)).toHaveAttribute('data-mode', 'auto');
        expect(within(card(CHF_USD)).getByTestId('pac-planner-fx-rate-value').textContent, 'the card shows the rate of D2').toContain(formatPlannerFxRate(CHF_D2.rate));
        expect(codesIn(EUR_USD), 'barrier: the EUR/USD card, whose skip is still true, lists it').toEqual([SKIPPED_CODE]);

        expect(within(card(CHF_USD)).queryByTestId('pac-planner-fx-issues')).toBeNull();
    });
});
