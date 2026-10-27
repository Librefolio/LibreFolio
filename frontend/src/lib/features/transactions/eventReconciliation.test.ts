/**
 * eventReconciliation — unit tests (Vitest, node). Workstream X, lot X5-3 (N68).
 *
 * Why. A currency change deletes an asset's events (but its SPLITs), so the transactions linked to them lose the
 * link (`asset_event_id` NULL). `GET /transactions/event-reconciliation` (zodios alias
 * `event_reconciliation_api_v1_transactions_event_reconciliation_get`) lists the transactions that could link an event and
 * have none, each with the events it could take: same asset, SAME DATE, the type that corresponds. Its `status` is
 * `unique` (one candidate), `none` (no event that day) or `several`. Nothing is linked by the server: this module reads the
 * list, picks the rows that are safe to link by themselves (the unique ones) and links them through the commit the app already
 * uses (`commitTransactions` of `txCommitApi.ts`, `updates: [{id, asset_event_id}]`, atomic: any issue and nothing is linked).
 * `EventReconciliationModal.svelte` is the screen over it (`EventReconciliationModal.test.ts`).
 *
 * Contract.
 *   - `loadEventReconciliation(filters?)` calls the alias ONCE and maps each item from snake_case to
 *     `{transactionId, brokerId, assetId, date, type, status, candidates: [{id, date, type, value, currency, isAuto}]}`
 *     (`distance_days` and the candidate's `asset_id` are not carried). The request carries `queries` ONLY for the filters
 *     given (`broker_id` from `brokerId`, `asset_id` from `assetId`): no filters, no `queries` key at all; an unset filter
 *     is not sent as undefined or null. A missing `candidates` is an empty list. It TRUSTS the server's `status`: it does
 *     not recompute it from the candidates. A failed request rejects (the modal shows its error state).
 *   - `uniqueRows(rows)` keeps the rows whose `status` is `unique` AND that hold exactly one candidate (a defensive double
 *     check: a `unique` row with two candidates, or none, is not safe to link), in the order given.
 *   - `linkUpdates(rows)` is `uniqueRows(rows)` as `{id: transactionId, asset_event_id: candidates[0].id}`; the other rows
 *     (`none`, `several`) never appear in it.
 *   - `linkReconciliation(rows)` sends ONE `commitTransactions({updates: linkUpdates(rows)})` and answers
 *     `{linked, issues}`: `linked` true only when the batch committed; on refusal `linked` is false and the issues are
 *     those of the commit. With nothing to link (an empty list, or no unique row) it sends NO request at all and answers
 *     `linked: false` with no issues — not an error.
 *
 * How. The API facade and the toast store are replaced (offline); `txCommitApi.ts` and `trySave` stay real, so the request
 * seen is the one the app would send. No text is read.
 *
 * Expected. Red before the cure, by absence: `eventReconciliation.ts` does not exist, so the file fails to load.
 * Registered in `scripts/test_runner/_frontend_utility.py` (Vitest list of `front_utility_unit`, action `core-unit`).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

const mocks = vi.hoisted(() => ({
    api: {
        event_reconciliation_api_v1_transactions_event_reconciliation_get: vi.fn(),
        commit_transactions_api_v1_transactions_commit_post: vi.fn(),
    },
}));
vi.mock('$lib/api', () => ({zodiosApi: mocks.api}));
vi.mock('$lib/stores/app/toastStore.svelte', () => ({
    toasts: {success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn()},
}));

import {linkReconciliation, linkUpdates, loadEventReconciliation, uniqueRows, type ReconciliationRow} from './eventReconciliation';

const listCall = mocks.api.event_reconciliation_api_v1_transactions_event_reconciliation_get;
const commitCall = mocks.api.commit_transactions_api_v1_transactions_commit_post;

/** One candidate event as the server lists it. */
function serverCandidate(id: number, over: Record<string, unknown> = {}) {
    return {id, asset_id: 7, date: '2025-03-04', type: 'DIVIDEND', value: '1.25', currency: 'USD', is_auto: false, distance_days: 0, ...over};
}

/** One item as the server lists it. */
function serverItem(transactionId: number, status: 'unique' | 'none' | 'several', candidates: ReturnType<typeof serverCandidate>[], over: Record<string, unknown> = {}) {
    return {transaction_id: transactionId, broker_id: 3, asset_id: 7, date: '2025-03-04', type: 'DIVIDEND', status, candidates, ...over};
}

/** A row as the module hands it on (camelCase), for the pure functions' cases. */
function row(transactionId: number, status: ReconciliationRow['status'], candidateIds: number[]): ReconciliationRow {
    return {
        transactionId,
        brokerId: 3,
        assetId: 7,
        date: '2025-03-04',
        type: 'DIVIDEND',
        status,
        candidates: candidateIds.map((id) => ({id, date: '2025-03-04', type: 'DIVIDEND', value: '1.25', currency: 'USD', isAuto: false})),
    };
}

beforeEach(() => {
    listCall.mockReset();
    commitCall.mockReset();
});

describe('loadEventReconciliation', () => {
    it('with no filters asks the list once, with no queries key at all', async () => {
        listCall.mockResolvedValue([]);

        await loadEventReconciliation();

        expect(listCall).toHaveBeenCalledTimes(1);
        // Nothing, or an object that carries no `queries`: an unset filter must not travel as undefined or null.
        const config = listCall.mock.calls[0]?.[0] as {queries?: unknown} | undefined;
        expect(config === undefined || !('queries' in config)).toBe(true);
    });

    it('an empty filter object is the same as no filters', async () => {
        listCall.mockResolvedValue([]);

        await loadEventReconciliation({});

        const config = listCall.mock.calls[0]?.[0] as {queries?: unknown} | undefined;
        expect(config === undefined || !('queries' in config)).toBe(true);
    });

    it('sends broker_id and asset_id as queries when both are given', async () => {
        listCall.mockResolvedValue([]);

        await loadEventReconciliation({brokerId: 3, assetId: 7});

        expect(listCall).toHaveBeenCalledWith({queries: {broker_id: 3, asset_id: 7}});
    });

    it('sends only the filter that is given: the other key is absent, not undefined', async () => {
        listCall.mockResolvedValue([]);
        await loadEventReconciliation({brokerId: 3});
        await loadEventReconciliation({assetId: 7});

        const first = listCall.mock.calls[0][0] as {queries: Record<string, unknown>};
        const second = listCall.mock.calls[1][0] as {queries: Record<string, unknown>};
        expect(Object.keys(first.queries)).toEqual(['broker_id']);
        expect(first.queries.broker_id).toBe(3);
        expect(Object.keys(second.queries)).toEqual(['asset_id']);
        expect(second.queries.asset_id).toBe(7);
    });

    it('a filter that is 0 is still a filter (an id is not a truthiness test)', async () => {
        listCall.mockResolvedValue([]);

        await loadEventReconciliation({brokerId: 0});

        expect(listCall).toHaveBeenCalledWith({queries: {broker_id: 0}});
    });

    it('maps every field from snake_case to camelCase, one row per item, in the order the server gave', async () => {
        listCall.mockResolvedValue([
            serverItem(11, 'unique', [serverCandidate(501, {date: '2025-03-04', type: 'DIVIDEND', value: '1.25', currency: 'USD', is_auto: true, distance_days: 0})], {broker_id: 3, asset_id: 7, date: '2025-03-04', type: 'DIVIDEND'}),
            serverItem(12, 'none', [], {broker_id: 4, asset_id: 8, date: '2025-04-05', type: 'INTEREST'}),
        ]);

        const rows = await loadEventReconciliation();

        expect(rows).toEqual([
            {transactionId: 11, brokerId: 3, assetId: 7, date: '2025-03-04', type: 'DIVIDEND', status: 'unique', candidates: [{id: 501, date: '2025-03-04', type: 'DIVIDEND', value: '1.25', currency: 'USD', isAuto: true}]},
            {transactionId: 12, brokerId: 4, assetId: 8, date: '2025-04-05', type: 'INTEREST', status: 'none', candidates: []},
        ]);
    });

    it('keeps every candidate of a several row, in order, with their own values', async () => {
        listCall.mockResolvedValue([serverItem(13, 'several', [serverCandidate(601, {value: '1.00', is_auto: false}), serverCandidate(602, {value: '2.50', is_auto: true, currency: 'EUR'})])]);

        const [only] = await loadEventReconciliation();

        expect(only.status).toBe('several');
        expect(only.candidates.map((c) => c.id)).toEqual([601, 602]);
        expect(only.candidates.map((c) => c.isAuto)).toEqual([false, true]);
        expect(only.candidates.map((c) => c.currency)).toEqual(['USD', 'EUR']);
    });

    it('a value that is a number stays a number: the module formats nothing', async () => {
        listCall.mockResolvedValue([serverItem(14, 'unique', [serverCandidate(701, {value: 3.5})])]);

        const [only] = await loadEventReconciliation();

        expect(only.candidates[0].value).toBe(3.5);
    });

    it('a missing candidates field is an empty list', async () => {
        const item: Record<string, unknown> = serverItem(15, 'none', []);
        delete item.candidates;
        listCall.mockResolvedValue([item]);

        const [only] = await loadEventReconciliation();

        expect(only.candidates).toEqual([]);
    });

    it('trusts the server’s status: it is not recomputed from the number of candidates', async () => {
        listCall.mockResolvedValue([serverItem(16, 'unique', []), serverItem(17, 'none', [serverCandidate(801)]), serverItem(18, 'several', [serverCandidate(802)])]);

        const rows = await loadEventReconciliation();

        expect(rows.map((r) => r.status)).toEqual(['unique', 'none', 'several']);
    });

    it('an empty list is an empty list', async () => {
        listCall.mockResolvedValue([]);

        expect(await loadEventReconciliation()).toEqual([]);
    });

    it('rejects when the request fails — the screen shows its error state', async () => {
        const failure = new Error('boom');
        listCall.mockRejectedValue(failure);

        await expect(loadEventReconciliation()).rejects.toBe(failure);
    });
});

describe('uniqueRows', () => {
    it('keeps the unique rows with exactly one candidate, in the order given, and nothing else', () => {
        const rows = [row(1, 'none', []), row(2, 'unique', [20]), row(3, 'several', [30, 31]), row(4, 'unique', [40])];

        expect(uniqueRows(rows).map((r) => r.transactionId)).toEqual([2, 4]);
    });

    it('drops a row marked unique that holds two candidates, and one marked unique that holds none (defensive double check)', () => {
        const rows = [row(1, 'unique', [10, 11]), row(2, 'unique', []), row(3, 'unique', [30])];

        expect(uniqueRows(rows).map((r) => r.transactionId)).toEqual([3]);
    });

    it('drops a row with one candidate whose status is not unique', () => {
        expect(uniqueRows([row(1, 'several', [10]), row(2, 'none', [20])])).toEqual([]);
    });

    it('does not mutate the list it is given', () => {
        const rows = [row(1, 'unique', [10]), row(2, 'none', [])];
        const copy = structuredClone(rows);

        uniqueRows(rows);

        expect(rows).toEqual(copy);
    });
});

describe('linkUpdates', () => {
    it('maps each unique row to {id: transactionId, asset_event_id: the candidate’s id}, in order', () => {
        const rows = [row(1, 'unique', [101]), row(2, 'none', []), row(3, 'several', [31, 32]), row(4, 'unique', [104])];

        expect(linkUpdates(rows)).toEqual([
            {id: 1, asset_event_id: 101},
            {id: 4, asset_event_id: 104},
        ]);
    });

    it('never links a several row to its first candidate', () => {
        expect(linkUpdates([row(3, 'several', [31, 32])])).toEqual([]);
    });

    it('is empty for an empty list and for a list without a unique row', () => {
        expect(linkUpdates([])).toEqual([]);
        expect(linkUpdates([row(1, 'none', []), row(2, 'several', [20, 21])])).toEqual([]);
    });

    it('carries exactly id and asset_event_id — the commit rejects other fields', () => {
        const [update] = linkUpdates([row(1, 'unique', [101])]);

        expect(Object.keys(update).sort()).toEqual(['asset_event_id', 'id']);
    });
});

describe('linkReconciliation', () => {
    it('sends ONE commit with every unique row’s update and nothing for the others', async () => {
        commitCall.mockResolvedValue({committed: true, issues: [], results: []});
        const rows = [row(1, 'unique', [101]), row(2, 'none', []), row(3, 'several', [31, 32]), row(4, 'unique', [104])];

        const outcome = await linkReconciliation(rows);

        expect(commitCall).toHaveBeenCalledTimes(1);
        expect(commitCall).toHaveBeenCalledWith({
            updates: [
                {id: 1, asset_event_id: 101},
                {id: 4, asset_event_id: 104},
            ],
        });
        expect(outcome.linked).toBe(true);
        expect(outcome.issues).toEqual([]);
    });

    it('one row is one commit with one update', async () => {
        commitCall.mockResolvedValue({committed: true, issues: []});

        await linkReconciliation([row(9, 'unique', [909])]);

        expect(commitCall).toHaveBeenCalledTimes(1);
        expect(commitCall).toHaveBeenCalledWith({updates: [{id: 9, asset_event_id: 909}]});
    });

    it('no request at all for an empty list, and not an error', async () => {
        const outcome = await linkReconciliation([]);

        expect(commitCall).not.toHaveBeenCalled();
        expect(outcome.linked).toBe(false);
        expect(outcome.issues).toEqual([]);
    });

    it('no request at all when no row is unique', async () => {
        const outcome = await linkReconciliation([row(1, 'none', []), row(2, 'several', [20, 21]), row(3, 'unique', [30, 31])]);

        expect(commitCall).not.toHaveBeenCalled();
        expect(outcome.linked).toBe(false);
    });

    it('a commit that reports issues links nothing: linked false and the issues of the commit', async () => {
        const issue = {operation: 'update', index: 1, error: 'cannot link', code: 'event_asset_mismatch'};
        commitCall.mockResolvedValue({committed: false, issues: [issue]});

        const outcome = await linkReconciliation([row(1, 'unique', [101]), row(2, 'unique', [102])]);

        expect(commitCall).toHaveBeenCalledTimes(1);
        expect(outcome.linked).toBe(false);
        expect(outcome.issues).toEqual([expect.objectContaining({index: 1, code: 'event_asset_mismatch'})]);
    });

    it('a request that fails does not throw: linked false', async () => {
        commitCall.mockRejectedValue(Object.assign(new Error('Network Error'), {response: undefined}));

        const outcome = await linkReconciliation([row(1, 'unique', [101])]);

        expect(outcome.linked).toBe(false);
    });

    it('does not retry a refused batch with fewer rows: one refusal, one request', async () => {
        commitCall.mockResolvedValue({committed: false, issues: [{operation: 'update', index: 0, error: 'x', code: 'y'}]});

        await linkReconciliation([row(1, 'unique', [101]), row(2, 'unique', [102])]);

        expect(commitCall).toHaveBeenCalledTimes(1);
    });
});
