// @vitest-environment jsdom
/**
 * RefreshNotice: the re-read before «Calcola» lists the source's issues under its summary (Vitest + jsdom).
 *
 * RED until X-R45b-ui.
 *
 * Subject. X-R45b (backend 292d7e55e): when the latest saved rate of a pair is 0 or not finite,
 * `POST /portfolio/allocation-source` quotes the previous valid one and adds the warning
 * `allocation.saved_fx_skipped` (params pair, skipped_date, used_date). The re-read before «Calcola» copies that
 * older rate into an Auto pair, and `RefreshNotice` (props `summary`, `asOf`, `testid`) says what it changed. It has
 * no place for the source's issues, so the warning never reaches the user.
 *
 * The cure (X-R45b-ui). `RefreshSummary.issues` holds the re-read source's issues minus the structural
 * `allocation.broker_execution_profile_unsupported` (see `../copies.refresh.test.ts`). `RefreshNotice` gains two
 * props, `draft` and `source`, and lists `summary.issues` under its summary through `presentSourceIssues` +
 * `listIssue` + `IssueList`, testid `<testid>-issues`: items `<testid>-issues-item`, with `data-code` and
 * `data-severity`. The tests are written against that interface: today the props are ignored and `issues` is not
 * read.
 *
 * Expectations. The message an item must show is the catalogue's own sentence for the issue key, with the
 * issue's params, looked up here after `setupI18n`: never hand-typed. A control checks that the sentence carries
 * the pair and both dates, so the comparison cannot pass on a catalogue that did not load.
 *
 * Source. The re-read snapshot is the API response as the backend serialises it, mapped by the real parser: the
 * API client is mocked and `fetchPlannerSource` maps its answer (as in `../source.test.ts`), on a real tool session.
 * The summary's issue is the parsed one. Nothing here talks to a server.
 *
 * Absence. The no-issue case asserts after a presence barrier: the notice itself, with its counts and its stamp.
 *
 * Tests.
 *   - RED until X-R45b-ui: the skipped-rate warning is one item of the notice's issue list, with its code, its
 *     severity and the catalogue sentence naming the pair and both dates. Today there is no list.
 *   - GUARD (green today and after): a summary with no issue shows no issue list.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';

const allocationSource = vi.hoisted(() => vi.fn());

// source.ts, the tool client and the planner formatter import the API client. Nothing here talks to a server:
// the allocation-source endpoint answers the queued snapshot, and any other call resolves to nothing.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: (_target, key) => (key === 'get_portfolio_allocation_source_api_v1_portfolio_allocation_source_post' ? allocationSource : vi.fn(async () => undefined))}),
    axiosInstance: {get: vi.fn(), post: vi.fn()},
}));

import {cleanup, render, screen, setupI18n, within} from '$test/component';
import {_} from '$lib/i18n';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import type {RefreshSummary} from '../copies';
import {PlannerDraft} from '../draft.svelte';
import {fetchPlannerSource, type PlannerSource, type SourceIssue} from '../source';
import RefreshNotice from './RefreshNotice.svelte';

const NOTICE_ID = 'pac-planner-refresh-notice';
const PAIR = 'EUR/USD';
const SKIPPED_CODE = 'allocation.saved_fx_skipped';
/** The message key of the issue (C3): `tools.pacAllocator.planner.issues.<code>`. */
const SKIPPED_KEY = `tools.pacAllocator.planner.issues.${SKIPPED_CODE}`;
const SKIPPED_DATE = '2026-01-05';
const USED = {rate: '1.0950', date: '2026-01-02'};
const AS_OF = '2026-01-07';
/** `fx_key` of the backend: `fx:<pair>:<reference date>:<sha256(source)[:12]>`; `61683d66d785` is the token of `ECB`. */
const QUOTE_ID = `fx:${PAIR}:${USED.date}:61683d66d785`;

/** `allocation.saved_fx_skipped` as `fx_quotes.py` builds it: on the quote actually used. */
const SKIPPED: SourceIssue = {
    code: SKIPPED_CODE,
    kind: 'invalid',
    severity: 'warning',
    path: {kind: 'field', section: 'fx_quotes', entity_kind: 'fx_quote', entity_id: QUOTE_ID, field: 'rate'},
    params: [
        {kind: 'text', name: 'pair', value: PAIR},
        {kind: 'date', name: 'skipped_date', value: SKIPPED_DATE},
        {kind: 'date', name: 'used_date', value: USED.date},
    ],
};

/** The answer to a re-read of EUR/USD, as the backend serialises it (`message_key` included; the parser drops it). */
function response(issues: readonly SourceIssue[]) {
    const generatedAt = `${AS_OF}T09:30:00Z`;
    return {
        snapshot: {as_of: AS_OF, target_currency: 'EUR', generated_at: generatedAt},
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
        fx_quotes: [{fx_quote_id: QUOTE_ID, pair: PAIR, rate: USED.rate, reference_date: USED.date, source: 'ECB', days_before_requested: 5, provenance_id: 'source:saved-fx'}],
        current_distribution: null,
        issues: issues.map((issue) => ({...issue, message_key: issue.code})),
    };
}

/** The re-read source through the real parser. */
async function reread(issues: readonly SourceIssue[]): Promise<PlannerSource> {
    allocationSource.mockResolvedValueOnce(response(issues));
    return fetchPlannerSource({asOf: AS_OF, targetCurrency: 'EUR', sections: ['fx_quotes'], brokerIds: [7], assetIds: [], fxPairs: [PAIR]}, getClientSessionGeneration());
}

/** What the re-read of one Auto pair reports: its rate changed; `issues` as the cure fills it. */
function summaryWith(source: PlannerSource, issues: SourceIssue[]): RefreshSummary {
    return {readAt: source.generatedAt, prices: 0, fx: 1, cash: 0, unchanged: 0, missing: [], issues};
}

/** Mounted as `PacPlannerTool` will mount it: the summary, the draft's date, the draft and the re-read source. */
async function mount(summary: RefreshSummary, draft: PlannerDraft, source: PlannerSource): Promise<void> {
    render(RefreshNotice, {summary, asOf: draft.data.asOf, draft, source});
    flushSync();
    await tick();
}

/** The catalogue's sentence for the skipped-rate warning, with the issue's own params. */
function skippedSentence(): string {
    const sentence = get(_)(SKIPPED_KEY, {values: {pair: PAIR, skipped_date: SKIPPED_DATE, used_date: USED.date}});
    expect(sentence, 'control: the catalogue has the key').not.toBe(SKIPPED_KEY);
    for (const value of [PAIR, SKIPPED_DATE, USED.date]) expect(sentence, `control: the sentence carries ${value}`).toContain(value);
    return sentence;
}

let nextUser = 80;

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    allocationSource.mockReset();
    transitionClientSession(++nextUser);
});

afterEach(() => {
    cleanup();
});

describe('RefreshNotice — issues of the re-read (X-R45b-ui)', () => {
    it('RED until X-R45b-ui: the skipped-rate warning is listed under the summary, with its code, its severity, the pair and both dates', async () => {
        const source = await reread([SKIPPED]);
        const [skipped] = source.issues;
        expect(skipped, 'barrier: the parser kept the warning').toEqual(SKIPPED);
        const expected = skippedSentence();

        await mount(summaryWith(source, [skipped]), new PlannerDraft('EUR'), source);

        const notice = screen.getByTestId(NOTICE_ID);
        const list = within(notice).getByTestId(`${NOTICE_ID}-issues`);
        const items = within(list).getAllByTestId(`${NOTICE_ID}-issues-item`);
        expect(items, 'one issue in the summary, one item').toHaveLength(1);
        const [item] = items;
        expect(item).toHaveAttribute('data-code', SKIPPED_CODE);
        expect(item).toHaveAttribute('data-severity', 'warning');
        expect(item.textContent).toContain(expected);
    });

    it('GUARD: a summary with no issue shows no issue list', async () => {
        const source = await reread([]);

        await mount(summaryWith(source, []), new PlannerDraft('EUR'), source);

        const notice = screen.getByTestId(NOTICE_ID);
        expect(notice, 'barrier: the notice is rendered, with its counts').toHaveAttribute('data-fx', '1');
        expect(within(notice).getByTestId(`${NOTICE_ID}-stamp`), 'barrier: and its stamp').toBeInTheDocument();
        expect(screen.queryByTestId(`${NOTICE_ID}-issues`)).toBeNull();
        expect(screen.queryAllByTestId(`${NOTICE_ID}-issues-item`)).toHaveLength(0);
    });
});
