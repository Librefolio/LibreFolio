// @vitest-environment jsdom
/**
 * EventReconciliationModal — component test (Vitest + jsdom). Workstream X, lot X5-3 (N68).
 *
 * After a currency change deletes an asset's events, the transactions that were linked to them have no event any more.
 * This modal (opened from the Transactions page, `tx-reconcile-events-button`) lists them with what the server found for
 * each (`GET /transactions/event-reconciliation`, read by `eventReconciliation.ts`): `unique` (exactly one event the same
 * day, of the corresponding type), `none` (no event that day) or `several`. The user links the unique ones — one by one
 * or all at once — through the commit the app already uses (`updates: [{id, asset_event_id}]`, atomic). Nothing is linked
 * on its own, and a `several` row is never guessed.
 *
 * Contract. Props `{open (bindable), onclose?, onlinked?}` (+ optional `filters`, handed to the load). On open it loads.
 * Test ids: `event-reconciliation-modal`; `-loading` (while the list is read); `-empty` (no rows); `-error` (the list failed
 * to load, or a link was refused); one row per transaction `event-reconciliation-row-{transactionId}` carrying
 * `data-status="unique|none|several"` and `data-candidate-count`; `event-reconciliation-link-{transactionId}` only on
 * unique rows; `event-reconciliation-link-all` (disabled or absent when no row is unique; links every unique row with ONE
 * commit); `event-reconciliation-close`. Linking a row removes it from the list (a re-read or a local removal: the test
 * does not tell which) and calls `onlinked`. A commit that reports issues, or fails, leaves every row and shows
 * `event-reconciliation-error`: nothing was linked, `onlinked` is not called.
 *
 * How. The API facade and the toast store are replaced; `eventReconciliation.ts` and `txCommitApi.ts` stay real, so what is
 * asserted is the request the app would send. The server is a small state machine: the list answers the rows still
 * unlinked, a committed link removes its transaction from them — so a modal that re-reads and one that removes locally
 * both end in the same list. No text is read.
 *
 * Expected. Red before the cure, by absence: `EventReconciliationModal.svelte` does not exist, so the file fails to load.
 * Registered in `scripts/test_runner/_frontend_utility.py` (Vitest list of `front_component_unit`, action `component-unit`).
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

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

import EventReconciliationModal from './EventReconciliationModal.svelte';

const listCall = mocks.api.event_reconciliation_api_v1_transactions_event_reconciliation_get;
const commitCall = mocks.api.commit_transactions_api_v1_transactions_commit_post;

type ServerItem = ReturnType<typeof item>;

function candidate(id: number) {
    return {id, asset_id: 7, date: '2025-03-04', type: 'DIVIDEND', value: '1.25', currency: 'USD', is_auto: false, distance_days: 0};
}

/** One item as the server lists it: the candidates follow the status unless a case gives them. */
function item(transactionId: number, status: 'unique' | 'none' | 'several', candidateIds?: number[]) {
    const ids = candidateIds ?? (status === 'unique' ? [transactionId + 1000] : status === 'several' ? [transactionId + 1000, transactionId + 2000] : []);
    return {transaction_id: transactionId, broker_id: 3, asset_id: 7, date: '2025-03-04', type: 'DIVIDEND', status, candidates: ids.map(candidate)};
}

/** The rows the fake server still lists. */
let pending: ServerItem[] = [];

/** Make the fake server answer `rows`; a committed link takes its transactions off the list. */
function serve(rows: ServerItem[]) {
    pending = [...rows];
    listCall.mockImplementation(async () => pending.map((row) => structuredClone(row)));
    commitCall.mockImplementation(async (body: {updates?: Array<{id: number; asset_event_id: number}>}) => {
        const linked = new Set((body.updates ?? []).map((update) => update.id));
        pending = pending.filter((row) => !linked.has(row.transaction_id));
        return {committed: true, issues: [], results: []};
    });
}

function deferred<T = unknown>() {
    let resolve!: (v: T) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

function mount(props: Record<string, unknown> = {}) {
    const onclose = vi.fn();
    const onlinked = vi.fn();
    const utils = render(EventReconciliationModal, {open: true, onclose, onlinked, ...props});
    return {onclose, onlinked, ...utils};
}

const row = (id: number) => screen.queryByTestId(`event-reconciliation-row-${id}`);
const linkButton = (id: number) => screen.queryByTestId(`event-reconciliation-link-${id}`) as HTMLButtonElement | null;

/** Wait until the list is read and shown (the loading state gone). */
async function listed() {
    await waitFor(() => expect(screen.queryByTestId('event-reconciliation-loading')).toBeNull());
}

beforeEach(async () => {
    await setupI18n();
    listCall.mockReset();
    commitCall.mockReset();
    serve([]);
});

describe('EventReconciliationModal — opening and states', () => {
    it('renders nothing while closed and reads nothing', () => {
        serve([item(11, 'unique')]);
        mount({open: false});

        expect(screen.queryByTestId('event-reconciliation-modal')).toBeNull();
        expect(listCall).not.toHaveBeenCalled();
    });

    it('loads when opened and shows the loading state until the list arrives', async () => {
        const gate = deferred<ServerItem[]>();
        listCall.mockReturnValueOnce(gate.promise as never);
        mount();

        await waitFor(() => expect(screen.getByTestId('event-reconciliation-modal')).toBeInTheDocument());
        expect(screen.getByTestId('event-reconciliation-loading')).toBeInTheDocument();
        expect(screen.queryByTestId('event-reconciliation-empty'), 'not «empty» before the answer').toBeNull();
        expect(listCall).toHaveBeenCalledTimes(1);

        gate.resolve([item(11, 'unique')]);
        await listed();
        expect(row(11)).not.toBeNull();
    });

    it('no rows: the empty state, no row and no link-all', async () => {
        serve([]);
        mount();
        await listed();

        expect(screen.getByTestId('event-reconciliation-empty')).toBeInTheDocument();
        expect(screen.queryByTestId('event-reconciliation-error')).toBeNull();
        const all = screen.queryByTestId('event-reconciliation-link-all') as HTMLButtonElement | null;
        expect(all === null || all.disabled, 'link all has nothing to link').toBe(true);
    });

    it('a failed load shows the error state and no rows', async () => {
        listCall.mockRejectedValue(new Error('boom'));
        mount();
        await listed();

        expect(screen.getByTestId('event-reconciliation-error')).toBeInTheDocument();
        expect(screen.queryByTestId('event-reconciliation-empty'), 'a failure is not «nothing to do»').toBeNull();
    });

    it('hands its filters to the load', async () => {
        serve([]);
        mount({filters: {brokerId: 3, assetId: 7}});
        await listed();

        expect(listCall).toHaveBeenCalledWith({queries: {broker_id: 3, asset_id: 7}});
    });

    it('without filters it asks for everything the caller may link', async () => {
        serve([]);
        mount();
        await listed();

        const config = listCall.mock.calls[0]?.[0] as {queries?: unknown} | undefined;
        expect(config === undefined || !('queries' in config)).toBe(true);
    });
});

describe('EventReconciliationModal — the rows', () => {
    it('one row per transaction, with its status and candidate count; a link button on the unique rows only', async () => {
        serve([item(11, 'unique'), item(12, 'none'), item(13, 'several')]);
        mount();
        await listed();

        expect(row(11)).toHaveAttribute('data-status', 'unique');
        expect(row(11)).toHaveAttribute('data-candidate-count', '1');
        expect(row(12)).toHaveAttribute('data-status', 'none');
        expect(row(12)).toHaveAttribute('data-candidate-count', '0');
        expect(row(13)).toHaveAttribute('data-status', 'several');
        expect(row(13)).toHaveAttribute('data-candidate-count', '2');

        expect(linkButton(11), 'the unique row offers the link').not.toBeNull();
        expect(linkButton(12), 'nothing to link on a none row').toBeNull();
        expect(linkButton(13), 'a several row is never guessed: no link button').toBeNull();
        expect(screen.queryByTestId('event-reconciliation-empty')).toBeNull();
    });

    it('link-all is available when there is a unique row', async () => {
        serve([item(11, 'unique'), item(12, 'none')]);
        mount();
        await listed();

        const all = screen.getByTestId('event-reconciliation-link-all') as HTMLButtonElement;
        expect(all).toBeEnabled();
    });

    it('link-all is absent or disabled when no row is unique', async () => {
        serve([item(12, 'none'), item(13, 'several')]);
        mount();
        await listed();

        const all = screen.queryByTestId('event-reconciliation-link-all') as HTMLButtonElement | null;
        expect(all === null || all.disabled).toBe(true);
        expect(row(12)).not.toBeNull();
        expect(row(13)).not.toBeNull();
    });
});

describe('EventReconciliationModal — linking one row', () => {
    it('sends ONE commit with that transaction and its only candidate, removes the row, keeps the others and calls onlinked', async () => {
        serve([item(11, 'unique', [501]), item(12, 'unique', [502]), item(13, 'several')]);
        const {onlinked} = mount();
        await listed();

        await fireEvent.click(linkButton(11) as HTMLButtonElement);

        await waitFor(() => expect(row(11)).toBeNull());
        expect(commitCall).toHaveBeenCalledTimes(1);
        expect(commitCall).toHaveBeenCalledWith({updates: [{id: 11, asset_event_id: 501}]});
        expect(onlinked).toHaveBeenCalled();
        // The others are untouched, and still linkable.
        expect(row(12)).toHaveAttribute('data-status', 'unique');
        expect(row(13)).toHaveAttribute('data-status', 'several');
        expect(linkButton(12)).not.toBeNull();
        expect(screen.queryByTestId('event-reconciliation-error')).toBeNull();
    });

    it('linking the last row leaves the list empty', async () => {
        serve([item(11, 'unique', [501])]);
        mount();
        await listed();

        await fireEvent.click(linkButton(11) as HTMLButtonElement);

        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-empty')).not.toBeNull());
        expect(row(11)).toBeNull();
    });

    it('a second click while the commit is pending sends no second commit', async () => {
        serve([item(11, 'unique', [501])]);
        const gate = deferred();
        commitCall.mockReturnValueOnce(gate.promise as never);
        mount();
        await listed();

        const button = linkButton(11) as HTMLButtonElement;
        await fireEvent.click(button);
        await fireEvent.click(button);

        expect(commitCall).toHaveBeenCalledTimes(1);
        gate.resolve({committed: true, issues: [], results: []});
        await waitFor(() => expect(row(11)).toBeNull());
        expect(commitCall).toHaveBeenCalledTimes(1);
    });

    it('a commit that reports issues links nothing: the row stays, the error shows, onlinked is not called', async () => {
        serve([item(11, 'unique', [501]), item(12, 'unique', [502])]);
        commitCall.mockResolvedValueOnce({committed: false, issues: [{operation: 'update', index: 0, error: 'cannot link', code: 'event_asset_mismatch'}]});
        const {onlinked} = mount();
        await listed();

        await fireEvent.click(linkButton(11) as HTMLButtonElement);

        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-error')).not.toBeNull());
        expect(row(11)).not.toBeNull();
        expect(row(12)).not.toBeNull();
        expect(linkButton(11), 'the user may try again').not.toBeNull();
        expect(onlinked).not.toHaveBeenCalled();
    });

    it('a commit that fails on the network links nothing either', async () => {
        serve([item(11, 'unique', [501])]);
        commitCall.mockRejectedValueOnce(Object.assign(new Error('Network Error'), {response: undefined}));
        const {onlinked} = mount();
        await listed();

        await fireEvent.click(linkButton(11) as HTMLButtonElement);

        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-error')).not.toBeNull());
        expect(row(11)).not.toBeNull();
        expect(onlinked).not.toHaveBeenCalled();
    });

    it('after a refusal, a retry that succeeds links the row and clears the error', async () => {
        serve([item(11, 'unique', [501])]);
        commitCall.mockResolvedValueOnce({committed: false, issues: [{operation: 'update', index: 0, error: 'cannot link', code: 'x'}]});
        const {onlinked} = mount();
        await listed();
        await fireEvent.click(linkButton(11) as HTMLButtonElement);
        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-error')).not.toBeNull());

        await fireEvent.click(linkButton(11) as HTMLButtonElement);

        await waitFor(() => expect(row(11)).toBeNull());
        expect(screen.queryByTestId('event-reconciliation-error')).toBeNull();
        expect(onlinked).toHaveBeenCalled();
        expect(commitCall).toHaveBeenCalledTimes(2);
    });
});

describe('EventReconciliationModal — linking all', () => {
    it('sends ONE commit with every unique row and nothing for the none and several rows; those stay', async () => {
        serve([item(11, 'unique', [501]), item(12, 'none'), item(13, 'several'), item(14, 'unique', [504])]);
        const {onlinked} = mount();
        await listed();

        await fireEvent.click(screen.getByTestId('event-reconciliation-link-all'));

        await waitFor(() => expect(row(11)).toBeNull());
        expect(row(14)).toBeNull();
        expect(commitCall).toHaveBeenCalledTimes(1);
        expect(commitCall).toHaveBeenCalledWith({
            updates: [
                {id: 11, asset_event_id: 501},
                {id: 14, asset_event_id: 504},
            ],
        });
        expect(row(12)).toHaveAttribute('data-status', 'none');
        expect(row(13)).toHaveAttribute('data-status', 'several');
        expect(onlinked).toHaveBeenCalled();
        const all = screen.queryByTestId('event-reconciliation-link-all') as HTMLButtonElement | null;
        expect(all === null || all.disabled, 'nothing unique is left to link').toBe(true);
    });

    it('a refusal links nothing: every row stays, the error shows, onlinked is not called', async () => {
        serve([item(11, 'unique', [501]), item(14, 'unique', [504])]);
        commitCall.mockResolvedValueOnce({committed: false, issues: [{operation: 'update', index: 1, error: 'cannot link', code: 'event_asset_mismatch'}]});
        const {onlinked} = mount();
        await listed();

        await fireEvent.click(screen.getByTestId('event-reconciliation-link-all'));

        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-error')).not.toBeNull());
        expect(row(11)).not.toBeNull();
        expect(row(14)).not.toBeNull();
        expect(commitCall, 'atomic: one request, no row-by-row retry behind the user’s back').toHaveBeenCalledTimes(1);
        expect(onlinked).not.toHaveBeenCalled();
    });
});

describe('EventReconciliationModal — closing', () => {
    it('the close button calls onclose, closes the modal and sends nothing', async () => {
        serve([item(11, 'unique', [501])]);
        const {onclose, onlinked} = mount();
        await listed();

        await fireEvent.click(screen.getByTestId('event-reconciliation-close'));

        expect(onclose).toHaveBeenCalledTimes(1);
        await waitFor(() => expect(screen.queryByTestId('event-reconciliation-modal')).toBeNull());
        expect(commitCall).not.toHaveBeenCalled();
        expect(onlinked).not.toHaveBeenCalled();
    });
});
