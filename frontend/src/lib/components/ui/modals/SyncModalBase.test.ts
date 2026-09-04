// @vitest-environment jsdom
/**
 * SyncModalBase — component test (Vitest + jsdom).
 *
 * This is the engine behind FxSyncModal, AssetSyncModal and PageSyncModal. It owns
 * everything those three do not: which sections are active, running them in
 * parallel, keeping their results apart, the aggregated tally, the retry paths
 * (one row, all failures, the footer button that changes job) and the reset on
 * reopen. Every one of those decisions hangs off a single injected function —
 * `section.doSyncFn(ids) => Promise<SyncResult[]>` — so a component test can hand
 * it a resolved value, a rejection, or a promise that never settles, and read the
 * consequence. Through Playwright the same ground needs a real provider that fails
 * on demand, which is not a thing that exists.
 *
 * The sections come from `$test/harness/SyncModalBaseHarness.svelte`: a section
 * carries a `resultRow` snippet, and a snippet written with `createRawSnippet`
 * renders once and needs a hand-written effect to follow updates — exactly the
 * updates (failed → ok on retry) these tests watch for. The harness publishes the
 * same row handles as the three production wrappers.
 *
 * What it deliberately does NOT assert:
 *   - translated text. The footer button says Close or Cancel depending on
 *     `isTimeout`, the summary says "Synced 3/4" around a translated verb, the
 *     section titles come from the catalogue. Everything is read from
 *     `data-testid`/`data-*` or from values the test itself injected.
 *   - CSS classes. `allFailuresPartial` only softens the retry button's accent from
 *     red to amber; both of its arms are executed here, neither is asserted, because
 *     a colour is not a contract.
 *   - the elapsed/remaining *rendering*. `formatTime` lives in syncHelpers and has
 *     its own unit test; what is asserted here is `data-remaining`, the number.
 *
 * A few tests below pin behaviour that is deliberate rather than obvious: the
 * timeout is a display and not a limit (it measures the user's patience, not the
 * server's), `onsynced` fires even when every item failed, and closing the modal
 * does not cancel the request — it only makes the modal stop listening. They are
 * written as descriptions of a decision, so that changing the decision shows up
 * here first.
 */
import {beforeAll, describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {tick} from 'svelte';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import type {SyncResult, SyncStatus} from '$lib/utils/sync/syncHelpers';
import Harness from '$test/harness/SyncModalBaseHarness.svelte';

// =========================================================================
// Fixtures
// =========================================================================

/** A result with the two point counters filled in — the ordinary case. */
function result(id: string, status: SyncStatus, fetched = 0, changed = 0): SyncResult {
    return {id, status, points_fetched: fetched, points_changed: changed};
}

/** A `doSyncFn` that answers every requested id with the same status. */
function answersWith(status: SyncStatus, fetched = 0, changed = 0): Mock {
    return vi.fn(async (ids: string[]) => ids.map((id) => result(id, status, fetched, changed)));
}

/** A `doSyncFn` that answers from a fixed id → status table, per call. */
function answersFrom(...tables: Record<string, SyncStatus>[]): Mock {
    let call = 0;
    return vi.fn(async (ids: string[]) => {
        const table = tables[Math.min(call++, tables.length - 1)];
        return ids.filter((id) => id in table).map((id) => result(id, table[id], 1, 1));
    });
}

/** A promise the test decides when — and whether — to settle. */
function deferred<T>() {
    let resolve!: (v: T) => void;
    let reject!: (e: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

interface Spec {
    id: string;
    targetIds: string[];
    doSyncFn: (ids: string[]) => Promise<SyncResult[]>;
}

function mount(specs: Spec[], props: Record<string, unknown> = {}) {
    const onsynced = vi.fn();
    const onclose = vi.fn();
    return {onsynced, onclose, ...render(Harness, {specs, onsynced, onclose, ...props})};
}

// =========================================================================
// Readers — everything addressed by id, never by position
// =========================================================================

function rowOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-result-row"][data-row-id="${id}"]`);
    if (!el) throw new Error(`no result row for id ${id}; present: ${rowIds().join(', ') || '(none)'}`);
    return el;
}

function rowIds(scope: ParentNode = document): string[] {
    return [...scope.querySelectorAll<HTMLElement>('[data-testid="sync-result-row"]')].map((r) => r.getAttribute('data-row-id') ?? '');
}

function statusOf(id: string): string | null {
    return rowOf(id).getAttribute('data-status');
}

function sectionOf(id: string): HTMLElement {
    const el = document.querySelector<HTMLElement>(`[data-testid="sync-section"][data-section-id="${id}"]`);
    if (!el) throw new Error(`no rendered section ${id}`);
    return el;
}

function num(el: Element | null, attr: string): number {
    return Number(el?.getAttribute(attr));
}

/** The five tallies of the summary banner, as numbers. */
function summary() {
    const el = screen.getByTestId('sync-modal-results');
    return {success: num(el, 'data-success'), total: num(el, 'data-total'), failed: num(el, 'data-failed'), fetched: num(el, 'data-fetched'), changed: num(el, 'data-changed')};
}

/** The summary banner's variant, which InfoBanner publishes in its own testid. */
function summaryVariant(): string {
    const banner = within(screen.getByTestId('sync-modal-results')).getByRole(/* success/warning render as status, error as alert */ 'status', {hidden: true});
    return banner.getAttribute('data-testid') ?? '';
}

/** The standalone error banner — the one outside the summary block. */
function errorBanner(): HTMLElement | null {
    return [...document.querySelectorAll<HTMLElement>('[data-testid="info-banner-error"]')].find((el) => !el.closest('[data-testid="sync-modal-results"]')) ?? null;
}

const startButton = () => screen.getByTestId('sync-modal-start');
const bodyState = (attr: string) => screen.getByTestId('sync-modal-body').getAttribute(attr);

/** Results land through two awaits and an effect flush; wait for the summary. */
async function settled() {
    await waitFor(() => expect(screen.queryByTestId('sync-modal-results')).not.toBeNull());
}

/**
 * Waits for the run to be *over*, which is not the same as the first result
 * being on screen: a retry that changes nothing visible still has a beginning
 * and an end, and `data-busy` is the only thing that says so.
 */
async function idle() {
    await waitFor(() => expect(bodyState('data-busy')).toBe('false'));
}

/**
 * Drains the microtask queue and flushes effects, without touching the clock.
 * Used where the thing under test is an *absence* — a stale answer that must not
 * land — so there is nothing to wait *for*, only a queue to exhaust.
 */
async function flush(times = 5) {
    for (let i = 0; i < times; i++) await tick();
}

beforeAll(async () => {
    // Before any fake timer is installed: register() resolves the catalogues
    // through dynamic import, and a faked clock is not the place to await one.
    await setupI18n();
});

// =========================================================================
// Which sections exist at all
// =========================================================================

describe('SyncModalBase — active sections', () => {
    it('hides a section with no targets and leaves it out of the aggregate count', async () => {
        const alpha = answersWith('ok');
        const beta = answersWith('ok');
        mount([
            {id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: alpha},
            {id: 'beta', targetIds: [], doSyncFn: beta},
        ]);

        // Two sections in, one active: the count bar reports the survivor only.
        expect(num(screen.getByTestId('sync-modal-count'), 'data-section-count')).toBe(1);
        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(2);

        await fireEvent.click(startButton());
        await settled();

        // The empty section is never asked to sync, and never rendered.
        expect(alpha).toHaveBeenCalledTimes(1);
        expect(beta).not.toHaveBeenCalled();
        expect(sectionOf('alpha')).toBeInTheDocument();
        expect(document.querySelector('[data-testid="sync-section"][data-section-id="beta"]')).toBeNull();
    });

    it('disables the start button when every section is empty', async () => {
        const never = answersWith('ok');
        mount([{id: 'alpha', targetIds: [], doSyncFn: never}]);

        expect(num(screen.getByTestId('sync-modal-count'), 'data-item-count')).toBe(0);
        expect(startButton()).toBeDisabled();
        // Nothing to report yet, so the modal is still in its pre-sync shape.
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();
    });

    it('floors the timeout at 20s and raises it to the item count when there are more items', async () => {
        const many = Array.from({length: 45}, (_, i) => `id${i}`);
        const {unmount} = mount([{id: 'alpha', targetIds: many, doSyncFn: answersWith('ok')}]);

        // timeoutSec = Math.max(20, itemCount)
        expect(screen.getByTestId('sync-modal-timeout')).toHaveValue(45);
        unmount();

        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersWith('ok')}]);
        expect(screen.getByTestId('sync-modal-timeout')).toHaveValue(20);
    });
});

// =========================================================================
// Parallelism and result ownership
// =========================================================================

describe('SyncModalBase — several sections at once', () => {
    it('runs every active section and files each result under the section that produced it', async () => {
        const alpha = answersWith('ok', 3, 1);
        const beta = answersWith('ok', 5, 2);
        mount([
            {id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: alpha},
            {id: 'beta', targetIds: ['b1'], doSyncFn: beta},
        ]);

        await fireEvent.click(startButton());
        await settled();

        expect(alpha).toHaveBeenCalledWith(['a1', 'a2']);
        expect(beta).toHaveBeenCalledWith(['b1']);
        // Each section shows its own rows and only its own.
        expect(rowIds(sectionOf('alpha')).sort()).toEqual(['a1', 'a2']);
        expect(rowIds(sectionOf('beta'))).toEqual(['b1']);
        // …and the tally is the sum across both: 3+3+5 fetched, 1+1+2 changed.
        expect(summary()).toMatchObject({success: 3, total: 3, fetched: 11, changed: 4});
    });

    it('shows a pending marker in the section that has not reported yet', async () => {
        const slow = deferred<SyncResult[]>();
        mount([
            {id: 'alpha', targetIds: ['a1'], doSyncFn: answersWith('ok')},
            {id: 'beta', targetIds: ['b1'], doSyncFn: () => slow.promise},
        ]);

        await fireEvent.click(startButton());
        // alpha resolves first, which is what makes the result area visible at all;
        // beta is still in flight, so its group stands in for itself.
        await waitFor(() => expect(document.querySelector('[data-testid="sync-section"][data-section-id="beta"]')).not.toBeNull());
        expect(within(sectionOf('beta')).getByTestId('sync-section-pending')).toBeInTheDocument();
        expect(within(sectionOf('alpha')).queryByTestId('sync-section-pending')).toBeNull();
        // The row snippet is told the modal is busy — that is what hides the
        // per-row retry control in the production wrappers.
        expect(rowOf('a1')).toHaveAttribute('data-syncing', 'true');

        slow.resolve([result('b1', 'ok')]);
        await settled();
        await waitFor(() => expect(bodyState('data-busy')).toBe('false'));
        expect(within(sectionOf('beta')).queryByTestId('sync-section-pending')).toBeNull();
        expect(rowOf('a1')).toHaveAttribute('data-syncing', 'false');
    });
});

// =========================================================================
// The four per-row outcomes and the aggregate they produce
// =========================================================================

describe('SyncModalBase — outcomes', () => {
    it('renders one row per result carrying its own status', async () => {
        const mixed = vi.fn(async () => [result('ok1', 'ok', 4, 2), result('part1', 'partial', 1, 0), result('fail1', 'failed'), result('skip1', 'skipped')]);
        mount([{id: 'alpha', targetIds: ['ok1', 'part1', 'fail1', 'skip1'], doSyncFn: mixed}]);

        await fireEvent.click(startButton());
        await settled();

        expect(statusOf('ok1')).toBe('ok');
        expect(statusOf('part1')).toBe('partial');
        expect(statusOf('fail1')).toBe('failed');
        expect(statusOf('skip1')).toBe('skipped');
        // `failedItems` counts partial as a failure (it is retryable); skipped is not.
        expect(summary()).toMatchObject({success: 1, total: 4, failed: 2, fetched: 5, changed: 2});
    });

    it('reports success only when every result is ok', async () => {
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersWith('ok', 2, 1)}]);
        await fireEvent.click(startButton());
        await settled();

        expect(summaryVariant()).toBe('info-banner-success');
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
        // Nothing left to do: the start/retry control is gone entirely.
        expect(screen.queryByTestId('sync-modal-start')).toBeNull();
    });

    it('reports a warning when some succeeded and an error when none did', async () => {
        const {unmount} = mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersFrom({a1: 'ok', a2: 'failed'})}]);
        await fireEvent.click(startButton());
        await settled();
        expect(summaryVariant()).toBe('info-banner-warning');
        unmount();

        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersWith('failed')}]);
        await fireEvent.click(startButton());
        await settled();
        // Zero successes: the summary itself is the error banner.
        expect(within(screen.getByTestId('sync-modal-results')).getByRole('alert')).toHaveAttribute('data-testid', 'info-banner-error');
    });

    it('treats absent point counters as zero rather than NaN', async () => {
        // The three wrappers normalise with `?? 0` before handing results over, so
        // this arm of the base is defensive — but `doSyncFn` is an injected
        // interface, and a section that omits the counters must not poison the sum.
        const sparse = vi.fn(async () => [{id: 'a1', status: 'ok'} as unknown as SyncResult, result('a2', 'ok', 7, 3)]);
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: sparse}]);

        await fireEvent.click(startButton());
        await settled();

        expect(summary()).toMatchObject({fetched: 7, changed: 3, success: 2, total: 2});
    });
});

// =========================================================================
// Failure of the call itself, as opposed to a failed result
// =========================================================================

describe('SyncModalBase — a rejected doSyncFn', () => {
    it('turns the rejection into a failed row per requested id and shows the detail from the response', async () => {
        const boom = vi.fn(async () => {
            throw {response: {data: {detail: 'provider refused the request'}}};
        });
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: boom}]);

        await fireEvent.click(startButton());
        await settled();

        // Every id the call was made for comes back failed — none are lost.
        expect(rowIds().sort()).toEqual(['a1', 'a2']);
        expect(statusOf('a1')).toBe('failed');
        // The banner text is the string this test injected, not a catalogue entry.
        expect(errorBanner()).toHaveTextContent('provider refused the request');
        expect(bodyState('data-timeout')).toBe('false');
    });

    it('falls back to the error message, then to a generic one, when there is no response detail', async () => {
        const {unmount} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: vi.fn().mockRejectedValue(new Error('socket hang up'))}]);
        await fireEvent.click(startButton());
        await settled();
        expect(errorBanner()).toHaveTextContent('socket hang up');
        unmount();

        // A rejection with neither detail nor message still has to say something.
        mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: vi.fn().mockRejectedValue({})}]);
        await fireEvent.click(startButton());
        await settled();
        expect(errorBanner()).not.toBeNull();
        expect(statusOf('a1')).toBe('failed');
        expect(bodyState('data-timeout')).toBe('false');
    });

    it('recognises an aborted request as a timeout, by code or by message', async () => {
        const {unmount} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: vi.fn().mockRejectedValue({code: 'ECONNABORTED', message: 'aborted'})}]);
        await fireEvent.click(startButton());
        await settled();
        expect(bodyState('data-timeout')).toBe('true');
        // The timeout field stays reachable so the user can raise it and retry.
        expect(screen.getByTestId('sync-modal-timeout')).toBeEnabled();
        unmount();

        // Same branch reached the other way: no axios code, "timeout" in the text.
        mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: vi.fn().mockRejectedValue(new Error('read timeout after 120000ms'))}]);
        await fireEvent.click(startButton());
        await settled();
        expect(bodyState('data-timeout')).toBe('true');
    });
});

// =========================================================================
// Retry
// =========================================================================

describe('SyncModalBase — retry', () => {
    it('retries a single row with only that id and replaces just that result', async () => {
        const fn = answersFrom({a1: 'failed', a2: 'ok'}, {a1: 'ok'});
        const {onsynced} = mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        expect(statusOf('a1')).toBe('failed');

        await fireEvent.click(within(rowOf('a1')).getByTestId('sync-retry-row'));
        await waitFor(() => expect(statusOf('a1')).toBe('ok'));

        expect(fn).toHaveBeenNthCalledWith(2, ['a1']);
        // The untouched row keeps its result rather than being re-fetched.
        expect(statusOf('a2')).toBe('ok');
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
        expect(onsynced).toHaveBeenCalledTimes(2);
    });

    it('ignores a retry for a row no active section owns any more', async () => {
        // `targetIds` is `$derived` in all three wrappers, so the set can shrink
        // under an open modal — unassign a provider and the asset leaves the list
        // while its result row stays on screen. `findSectionForId` then finds
        // nothing and the retry has to be a no-op rather than a crash.
        const fn = answersWith('failed');
        const {rerender} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: fn}]);
        await fireEvent.click(startButton());
        await settled();

        await rerender({specs: [{id: 'alpha', targetIds: ['other'], doSyncFn: fn}]});
        await tick();
        expect(rowOf('a1')).toBeInTheDocument();

        await fireEvent.click(within(rowOf('a1')).getByTestId('sync-retry-row'));
        await tick();
        expect(fn).toHaveBeenCalledTimes(1); // no second request
        expect(statusOf('a1')).toBe('failed');
    });

    it('skips an orphaned failure when retrying all of them', async () => {
        // Same shrinking set, bulk path: a2 is no longer owned by any section, so
        // it is dropped from the grouping instead of being sent to the wrong one.
        const fn = answersFrom({a1: 'failed', a2: 'failed'}, {a1: 'ok'});
        const {rerender} = mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);
        await fireEvent.click(startButton());
        await settled();
        expect(summary().failed).toBe(2);

        await rerender({specs: [{id: 'alpha', targetIds: ['a1'], doSyncFn: fn}]});
        await tick();
        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));
        await waitFor(() => expect(statusOf('a1')).toBe('ok'));

        expect(fn).toHaveBeenNthCalledWith(2, ['a1']);
        expect(statusOf('a2')).toBe('failed');
    });

    /**
     * The three production rows hide their retry control while a run is in
     * flight, and for a finger that is enough: two presses are ~100 ms apart and
     * the second lands on nothing. It is not enough within one tick, before the
     * DOM has flushed — and the server would be asked twice for the same id. So
     * the refusal lives in the handler, not in the markup, and it is tested here
     * on the base's own terms: the harness offers the control throughout, which
     * is exactly what makes the same-tick case expressible.
     */
    it('refuses a second request for a row while one is already in flight', async () => {
        const held = deferred<SyncResult[]>();
        let call = 0;
        const fn = vi.fn((ids: string[]) => {
            call += 1;
            return call === 1 ? Promise.resolve(ids.map((id) => result(id, 'failed'))) : held.promise;
        });
        mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await waitFor(() => expect(statusOf('a1')).toBe('failed'));

        // The retry is pressed and held open, so the modal is busy…
        const retry = within(rowOf('a1')).getByTestId('sync-retry-row');
        await fireEvent.click(retry);
        await tick();
        expect(bodyState('data-busy')).toBe('true');

        // …and pressing it again asks nobody anything.
        await fireEvent.click(retry);
        await flush();
        expect(fn).toHaveBeenCalledTimes(2);

        held.resolve([result('a1', 'ok')]);
        await held.promise;
        await idle();
        expect(statusOf('a1')).toBe('ok');
    });

    it('retries every failure across sections, each with only its own ids', async () => {
        const alpha = answersFrom({a1: 'failed', a2: 'partial', a3: 'ok'}, {a1: 'ok', a2: 'ok'});
        const beta = answersFrom({b1: 'failed'}, {b1: 'ok'});
        mount([
            {id: 'alpha', targetIds: ['a1', 'a2', 'a3'], doSyncFn: alpha},
            {id: 'beta', targetIds: ['b1'], doSyncFn: beta},
        ]);

        await fireEvent.click(startButton());
        await settled();
        // Three retryable rows (a failed, a partial, a failed in the other section)
        // is what makes the bulk control appear.
        expect(summary().failed).toBe(3);

        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));
        await waitFor(() => expect(summary().failed).toBe(0));

        expect(alpha).toHaveBeenNthCalledWith(2, ['a1', 'a2']);
        expect(beta).toHaveBeenNthCalledWith(2, ['b1']);
        expect(summary()).toMatchObject({success: 4, total: 4});
    });

    it('offers the bulk control only above one failure', async () => {
        const {unmount} = mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersFrom({a1: 'failed', a2: 'ok'})}]);
        await fireEvent.click(startButton());
        await settled();
        // One failure: the footer button already covers it, the banner-level one
        // would be a duplicate.
        expect(screen.queryByTestId('sync-modal-retry-failed')).toBeNull();
        expect(startButton()).toBeEnabled();
        unmount();

        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: answersWith('partial')}]);
        await fireEvent.click(startButton());
        await settled();
        expect(screen.getByTestId('sync-modal-retry-failed')).toBeInTheDocument();
    });

    it('changes the footer button from "sync everything" to "retry the failures"', async () => {
        const fn = answersFrom({a1: 'failed', a2: 'ok'}, {a1: 'ok'});
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();

        // Second press of the same control: it now carries handleRetryFailed, so it
        // asks for the one failure rather than the whole set again.
        await fireEvent.click(startButton());
        await waitFor(() => expect(statusOf('a1')).toBe('ok'));
        expect(fn).toHaveBeenNthCalledWith(2, ['a1']);
    });

    it('hides the retry controls while a retry is in flight', async () => {
        const slow = deferred<SyncResult[]>();
        let call = 0;
        const fn = vi.fn(async (ids: string[]) => {
            if (call++ === 0) return ids.map((id) => result(id, 'failed'));
            return slow.promise;
        });
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));

        await waitFor(() => expect(bodyState('data-busy')).toBe('true'));
        // The bulk control is gone and the footer one is disabled: no second
        // request can be started on top of the first.
        expect(screen.queryByTestId('sync-modal-retry-failed')).toBeNull();
        expect(startButton()).toBeDisabled();
        expect(screen.getByTestId('sync-modal-timeout')).toBeDisabled();

        slow.resolve([result('a1', 'ok'), result('a2', 'ok')]);
        await waitFor(() => expect(bodyState('data-busy')).toBe('false'));
    });
});

// =========================================================================
// Reopening
// =========================================================================

describe('SyncModalBase — reopening', () => {
    it('drops the previous run when the modal is closed and opened again', async () => {
        const fn = answersWith('failed');
        const {rerender} = mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        expect(summary().failed).toBe(2);
        expect(errorBanner()).toBeNull(); // failed results, but the call itself succeeded

        await rerender({open: false});
        await rerender({open: true});
        await tick();

        // A fresh open is a fresh sheet: no rows, no summary, no timeout flag, and
        // the footer offers a full sync again rather than a retry.
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();
        expect(rowIds()).toEqual([]);
        expect(bodyState('data-timeout')).toBe('false');
        await fireEvent.click(startButton());
        await settled();
        expect(fn).toHaveBeenNthCalledWith(2, ['a1', 'a2']);
    });

    it('recomputes the timeout floor from the item count of the new run', async () => {
        const {rerender} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: answersWith('ok')}]);
        expect(screen.getByTestId('sync-modal-timeout')).toHaveValue(20);

        await rerender({open: false});
        await rerender({open: true, specs: [{id: 'alpha', targetIds: Array.from({length: 30}, (_, i) => `id${i}`), doSyncFn: answersWith('ok')}]});
        await tick();

        expect(screen.getByTestId('sync-modal-timeout')).toHaveValue(30);
    });
});

// =========================================================================
// The countdown
// =========================================================================

describe('SyncModalBase — countdown', () => {
    it('runs down while the request is in flight and disappears when it settles', async () => {
        vi.useFakeTimers();
        try {
            const slow = deferred<SyncResult[]>();
            mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: () => slow.promise}]);

            await fireEvent.click(startButton());
            expect(screen.getByTestId('sync-modal-progress')).toHaveAttribute('data-remaining', '20');

            await vi.advanceTimersByTimeAsync(3_000);
            await tick();
            expect(screen.getByTestId('sync-modal-progress')).toHaveAttribute('data-remaining', '17');

            slow.resolve([result('a1', 'ok')]);
            await vi.advanceTimersByTimeAsync(150);
            await tick();

            // The bar is gone and the interval with it: further time changes nothing.
            expect(screen.queryByTestId('sync-modal-progress')).toBeNull();
            expect(bodyState('data-busy')).toBe('false');
        } finally {
            vi.useRealTimers();
        }
    });

    /**
     * Deliberate, and pinned so that changing it has to be a decision.
     *
     * `timeoutSec` drives the countdown and nothing else: there is no timer that
     * aborts, and the wrappers pass a hardcoded 120s to axios regardless of what
     * the user typed. Past the deadline the counter sits at 0, the bar is full, and
     * the modal stays busy for as long as the backend cares to take — because the
     * number measures the user's patience, not the server's.
     */
    it('keeps waiting after the countdown reaches zero: the timeout is a display, not a limit', async () => {
        vi.useFakeTimers();
        try {
            const never = deferred<SyncResult[]>();
            const {onsynced} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: () => never.promise}]);

            await fireEvent.click(startButton());
            await vi.advanceTimersByTimeAsync(60_000); // three times the 20s deadline
            await tick();

            expect(screen.getByTestId('sync-modal-progress')).toHaveAttribute('data-remaining', '0');
            expect(bodyState('data-busy')).toBe('true');
            expect(bodyState('data-timeout')).toBe('false'); // never flagged
            expect(onsynced).not.toHaveBeenCalled();

            never.resolve([result('a1', 'ok')]);
            await vi.advanceTimersByTimeAsync(150);
            await tick();
            // …and it is still accepted, a minute past the stated timeout.
            expect(statusOf('a1')).toBe('ok');
        } finally {
            vi.useRealTimers();
        }
    });
});

// =========================================================================
// What the ticker must not outlive
// =========================================================================

/**
 * Repeating timers still alive, once every one-shot has had its chance to fire.
 *
 * A `setTimeout` that has not fired yet is a pending timer too, and opening the
 * modal schedules a few, so a raw count says nothing. Advance the clock far
 * enough and only a *repeating* timer can still be there — and the component has
 * exactly one, the 100 ms countdown ticker.
 *
 * Counting timers is a strange thing for a component test to do, and it is the
 * right thing here: an orphaned ticker writes to a `$state` that nothing renders
 * any more, so it has no shape in the DOM at all. There is nothing else to look
 * at. It simply keeps waking the machine ten times a second.
 */
async function tickersAlive(): Promise<number> {
    await vi.advanceTimersByTimeAsync(2_000);
    await flush();
    return vi.getTimerCount();
}

/**
 * A third test used to live here: that starting a second run over a first does
 * not lose the first ticker — the reference is a single variable, so overwriting
 * it puts the old interval beyond the reach of any later `stopCountdown()`. It
 * was a real condition, reachable through `handleRetrySingle`, which did not
 * gate on `syncing` and so let two runs overlap. It is gone because the path is:
 * `handleRetrySingle` now returns early while a run is in flight, and it was the
 * only door — `handleSyncAll` and `handleRetryFailed` are not exported, the
 * footer button is disabled while syncing, and a reopened modal has no rows to
 * retry from. The `stopCountdown()` that now opens `startCountdown()` is what
 * remains: a net under a condition nobody can create today, kept for the day the
 * guard moves. It has no test because it can no longer be provoked, and this
 * paragraph is the reason rather than an oversight.
 */
describe('SyncModalBase — the ticker outlives neither the modal nor the run', () => {
    /**
     * The abandoned run cannot stop its own ticker: its `finally` only cleans up
     * while its epoch is still on screen, and by then it is not — that is the
     * whole point of the session guard. So the close has to do it, and the close
     * is the moment to do it: the countdown is a display, and nobody is looking.
     */
    it('stops ticking the moment the user walks away, without waiting for the answer', async () => {
        vi.useFakeTimers();
        try {
            const inflight = deferred<SyncResult[]>();
            const {rerender} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: () => inflight.promise}]);

            await fireEvent.click(startButton());
            await vi.advanceTimersByTimeAsync(3_000);
            await tick();
            // Precondition, verified rather than assumed: it really is ticking —
            // the number on screen moved…
            expect(screen.getByTestId('sync-modal-progress')).toHaveAttribute('data-remaining', '17');
            // …and there is exactly one repeating timer behind it.
            expect(await tickersAlive()).toBe(1);

            await rerender({open: false});
            expect(await tickersAlive()).toBe(0);

            // The request is still out there — closing does not cancel it, which
            // is deliberate — so its answer lands on a session nobody is watching.
            // That must not bring anything back to life either.
            inflight.resolve([result('a1', 'ok')]);
            await inflight.promise;
            expect(await tickersAlive()).toBe(0);
        } finally {
            vi.useRealTimers();
        }
    });

    /**
     * `open` is never set to false here. That is the `{#if}` case —
     * TransactionFormModal drops the whole component rather than closing it — so
     * the effect's close branch never runs, and the destroy hook is the only
     * thing left between a ticker and the life of the page.
     */
    it('stops ticking when the modal is destroyed, which is a close the effect never sees', async () => {
        vi.useFakeTimers();
        try {
            const inflight = deferred<SyncResult[]>();
            const {unmount} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: () => inflight.promise}]);

            await fireEvent.click(startButton());
            await tick();
            expect(screen.getByTestId('sync-modal-progress')).toBeInTheDocument();
            expect(await tickersAlive()).toBe(1);

            unmount();
            expect(await tickersAlive()).toBe(0);
        } finally {
            vi.useRealTimers();
        }
    });
});

// =========================================================================
// Callbacks out
// =========================================================================

describe('SyncModalBase — callbacks', () => {
    it('reaches onclose from both the header dismiss and the footer button', async () => {
        const {onclose, onsynced} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: answersWith('ok')}]);

        await fireEvent.click(screen.getByTestId('sync-modal-dismiss'));
        await fireEvent.click(screen.getByTestId('sync-modal-close'));

        expect(onclose).toHaveBeenCalledTimes(2);
        expect(onsynced).not.toHaveBeenCalled();
    });

    it('announces the sync even when every single item failed', async () => {
        // Deliberate: `doSyncSection` swallows the error into failed rows, so the
        // parent is still told to refresh. Pinned because a caller that assumes
        // "onsynced ⇒ something changed" would be wrong.
        const {onsynced} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: vi.fn().mockRejectedValue(new Error('down'))}]);

        await fireEvent.click(startButton());
        await settled();
        expect(onsynced).toHaveBeenCalledTimes(1);
    });
});

// =========================================================================
// Silence is an outcome — an item asked about never leaves without one
// =========================================================================

describe('SyncModalBase — items the answer does not cover', () => {
    /**
     * The rule: an id that was requested and never reported on gets a row of its
     * own, marked failed. It used to get nothing — no row, and a summary whose
     * denominator was "results received", so a backend answering about one of two
     * ids produced a green "1/1".
     */
    it('gives an id the section never reported on a failed row of its own', async () => {
        const partialAnswer = vi.fn(async () => [result('a1', 'ok', 5, 5)]);
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: partialAnswer}]);

        await fireEvent.click(startButton());
        await idle();

        expect(partialAnswer).toHaveBeenCalledWith(['a1', 'a2']);
        // Both ids are on screen, and the one nobody spoke about is a failure.
        expect(rowIds().sort()).toEqual(['a1', 'a2']);
        expect(statusOf('a1')).toBe('ok');
        expect(statusOf('a2')).toBe('failed');
        // The section's own counters now agree, which is the point.
        expect(num(sectionOf('alpha'), 'data-result-count')).toBe(2);
        expect(num(sectionOf('alpha'), 'data-target-count')).toBe(2);
        // And the run cannot be read as a clean success any more.
        expect(summary()).toMatchObject({success: 1, total: 2, failed: 1});
        expect(summaryVariant()).toBe('info-banner-warning');
    });

    /**
     * The synthetic row is a failure like any other, so it is retryable: the
     * footer button switches to the retry job and asks about the silent id alone.
     */
    it('lets the user retry the id that was never reported on', async () => {
        let call = 0;
        const fn = vi.fn(async (ids: string[]) => (call++ === 0 ? [result('a1', 'ok', 5, 5)] : ids.map((id) => result(id, 'ok', 2, 2))));
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await idle();
        expect(statusOf('a2')).toBe('failed');

        // One failure only, so the bulk control stays away and the footer does it.
        expect(screen.queryByTestId('sync-modal-retry-failed')).toBeNull();
        await fireEvent.click(startButton());
        await waitFor(() => expect(statusOf('a2')).toBe('ok'));

        expect(fn).toHaveBeenNthCalledWith(2, ['a2']);
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
    });

    /**
     * The other half of the same rule: an answer that covers nothing replaces
     * nothing. The failures — and the controls that repair them — survive.
     */
    it('keeps the failed rows, and their retry control, when the retry answers with nothing', async () => {
        let call = 0;
        const fn = vi.fn(async (ids: string[]) => (call++ === 0 ? ids.map((id) => result(id, 'failed')) : []));
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        expect(summary().failed).toBe(2);

        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));
        await waitFor(() => expect(fn).toHaveBeenCalledTimes(2));
        await idle();

        expect(fn).toHaveBeenNthCalledWith(2, ['a1', 'a2']);
        // Nothing was erased, nothing was invented, and the way out is still there.
        expect(rowIds().sort()).toEqual(['a1', 'a2']);
        expect(statusOf('a1')).toBe('failed');
        expect(statusOf('a2')).toBe('failed');
        expect(summary()).toMatchObject({success: 0, total: 2, failed: 2});
        expect(screen.getByTestId('sync-modal-retry-failed')).toBeInTheDocument();
    });

    /**
     * A row that already has an outcome is not overwritten by silence either:
     * the successful half of a first run survives a retry aimed at the failures.
     */
    it('leaves untouched the rows the retry did not ask about', async () => {
        const fn = answersFrom({a1: 'ok', a2: 'failed'}, {a2: 'ok'});
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await idle();
        expect(statusOf('a1')).toBe('ok');

        await fireEvent.click(startButton());
        await waitFor(() => expect(statusOf('a2')).toBe('ok'));

        expect(fn).toHaveBeenNthCalledWith(2, ['a2']);
        expect(statusOf('a1')).toBe('ok');
        expect(rowIds().sort()).toEqual(['a1', 'a2']);
        expect(summary()).toMatchObject({success: 2, total: 2, failed: 0});
    });
});

// =========================================================================
// One session at a time
// =========================================================================

describe('SyncModalBase — sessions', () => {
    /**
     * `handleRetrySingle` was the only one of the three entry points that did not
     * clear `isTimeout`, so a successful per-row retry left the modal claiming the
     * previous attempt had timed out — and that flag is what picks the footer's
     * label.
     */
    it('clears the timeout flag after a successful single-row retry', async () => {
        let call = 0;
        const fn = vi.fn(async (ids: string[]) => {
            if (call++ === 0) throw {code: 'ECONNABORTED', message: 'aborted'};
            return ids.map((id) => result(id, 'ok'));
        });
        mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        expect(bodyState('data-timeout')).toBe('true');

        await fireEvent.click(within(rowOf('a1')).getByTestId('sync-retry-row'));
        await waitFor(() => expect(statusOf('a1')).toBe('ok'));
        await idle();

        expect(errorBanner()).toBeNull();
        expect(bodyState('data-timeout')).toBe('false');
    });

    /**
     * Closing does not cancel: the backend keeps working, deliberately. What
     * changed is that the abandoned run's signals are ignored — reopening gives a
     * clean, idle modal, and the late answer lands nowhere.
     *
     * The absence is only worth asserting next to a presence, so the last act
     * starts a fresh sync in the new session and watches it render: the modal was
     * perfectly able to show a result, it just would not show *that* one.
     */
    it('ignores the answer to a run the user has walked away from', async () => {
        const stale = deferred<SyncResult[]>();
        let answer: () => Promise<SyncResult[]> = () => stale.promise;
        const fn = vi.fn(() => answer());
        const {onsynced, rerender} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await waitFor(() => expect(bodyState('data-busy')).toBe('true'));

        await rerender({open: false});
        expect(screen.queryByTestId('sync-modal-body')).toBeNull();

        await rerender({open: true});
        await tick();
        // A new session: idle, empty, and ready — not stuck on the old progress bar.
        expect(bodyState('data-busy')).toBe('false');
        expect(startButton()).toBeEnabled();
        expect(rowIds()).toEqual([]);
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();

        stale.resolve([result('a1', 'ok', 9, 9)]);
        await stale.promise;
        await flush();

        // The late answer is dropped, and the parent is not told to reload.
        expect(rowIds()).toEqual([]);
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();
        expect(bodyState('data-busy')).toBe('false');
        expect(onsynced).not.toHaveBeenCalled();

        // Presence barrier: the same modal renders a result asked for here.
        answer = async () => [result('a1', 'partial', 3, 3)];
        await fireEvent.click(startButton());
        await idle();
        expect(statusOf('a1')).toBe('partial');
        expect(onsynced).toHaveBeenCalledTimes(1);
    });
});
