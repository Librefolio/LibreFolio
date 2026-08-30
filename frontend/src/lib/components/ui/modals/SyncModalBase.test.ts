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
 * Several tests below pin behaviour that is arguably wrong (a timeout that times
 * nothing out, results that vanish when the backend returns fewer rows than were
 * asked for). They are written as descriptions of what the code does today, and
 * flagged in the report, because changing them changes what the user sees.
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
     * ⚠ Product defect, pinned rather than fixed — see the report.
     *
     * `timeoutSec` drives the countdown and nothing else: there is no timer that
     * aborts, and the wrappers pass a hardcoded 120s to axios regardless of what
     * the user typed. Past the deadline the counter sits at 0, the bar is full, and
     * the modal stays busy for as long as the backend cares to take.
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
// Pinned defects — behaviour described, not endorsed (see the report)
// =========================================================================

describe('SyncModalBase — pinned defects', () => {
    /**
     * ⚠ The denominator of the summary is "results received", not "items asked
     * for". A backend that answers about fewer ids than were requested makes the
     * missing ones disappear without a word, and the banner reads as a clean run.
     */
    it('silently drops ids the section did not report on, and still calls the run complete', async () => {
        const partialAnswer = vi.fn(async () => [result('a1', 'ok', 5, 5)]);
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: partialAnswer}]);

        await fireEvent.click(startButton());
        await settled();

        expect(partialAnswer).toHaveBeenCalledWith(['a1', 'a2']);
        expect(rowIds()).toEqual(['a1']); // a2 has no row at all
        // The only surviving trace of the request is the section's own counters.
        expect(num(sectionOf('alpha'), 'data-result-count')).toBe(1);
        expect(num(sectionOf('alpha'), 'data-target-count')).toBe(2);
        // …while the summary says the run was a complete success.
        expect(summary()).toMatchObject({success: 1, total: 1, failed: 0});
        expect(summaryVariant()).toBe('info-banner-success');
    });

    /**
     * ⚠ Same mechanism, worse consequence: an empty answer to a retry erases the
     * failure it was meant to fix, and with the last failure gone the modal
     * withdraws the retry control too. The user is left with no failure and no
     * way to try again.
     */
    it('erases a failed row when the retry answers with nothing', async () => {
        let call = 0;
        const fn = vi.fn(async (ids: string[]) => (call++ === 0 ? ids.map((id) => result(id, 'failed')) : []));
        mount([{id: 'alpha', targetIds: ['a1', 'a2'], doSyncFn: fn}]);

        await fireEvent.click(startButton());
        await settled();
        expect(summary().failed).toBe(2);

        await fireEvent.click(screen.getByTestId('sync-modal-retry-failed'));
        await waitFor(() => expect(rowIds()).toEqual([]));

        // No rows, no failures, and no control left to start anything.
        expect(screen.queryByTestId('sync-modal-results')).toBeNull();
        expect(screen.queryByTestId('sync-modal-start')).not.toBeNull(); // back to "sync all"
        expect(fn).toHaveBeenNthCalledWith(2, ['a1', 'a2']);
    });

    /**
     * ⚠ `handleSyncAll` and `handleRetryFailed` both clear `isTimeout`;
     * `handleRetrySingle` clears `error` and forgets it. A per-row retry that
     * succeeds therefore leaves the modal claiming the previous attempt timed
     * out — which is what decides the footer label (Close instead of Cancel).
     */
    it('leaves the timeout flag set after a successful single-row retry', async () => {
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

        // The run succeeded, the error banner is gone — and the flag is still up.
        expect(errorBanner()).toBeNull();
        expect(bodyState('data-timeout')).toBe('true');
    });

    /**
     * ⚠ Closing the modal neither cancels the request nor stops the countdown, and
     * `onsynced` fires into a parent that has already dismissed the dialog. Reopen
     * before it lands and the reset effect wipes the results while `syncing` stays
     * true, so the new session opens stuck on the old request's progress bar.
     */
    it('keeps an in-flight sync running across a close, and reopens busy on it', async () => {
        const slow = deferred<SyncResult[]>();
        const {onsynced, rerender} = mount([{id: 'alpha', targetIds: ['a1'], doSyncFn: () => slow.promise}]);

        await fireEvent.click(startButton());
        await waitFor(() => expect(bodyState('data-busy')).toBe('true'));

        await rerender({open: false});
        expect(screen.queryByTestId('sync-modal-body')).toBeNull(); // dialog is gone

        await rerender({open: true});
        await tick();
        // A brand-new open, already busy on a request the user cannot see.
        expect(bodyState('data-busy')).toBe('true');
        expect(startButton()).toBeDisabled();

        slow.resolve([result('a1', 'ok')]);
        await settled();
        // The stale answer lands in the fresh session, and the parent is told to
        // refresh as if the user had asked for it here.
        expect(statusOf('a1')).toBe('ok');
        expect(onsynced).toHaveBeenCalledTimes(1);
    });
});
