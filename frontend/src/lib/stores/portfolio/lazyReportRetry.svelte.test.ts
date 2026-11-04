// @vitest-environment jsdom
//
// The docblock above is load-bearing: the reactive cases read `canAsk` inside an effect, and several assert that the
// effect does NOT run again — under the default `node` environment `$effect` never runs, so those would pass vacuously
// (`$test/runes.svelte`; `assertEffectsRun` turns it into a message).
/**
 * lazyReportRetry — when a page may ask again for a lazy section of the portfolio report that failed (backlog Y-24;
 * contract decided by the coordinator of Y, 17/10/2026).
 *
 * The defect. The P&L candles of the growth chart and the contribution of the positions panel are asked lazily, by the
 * panel's `$effect`, when its view needs them and has none (`GrowthChart.svelte`, `PositionsPanel.svelte`). When
 * `POST /portfolio/report` fails, `requestReport` resolves null, the loader's `finally` turns its `loading` flag back to
 * false, the effect — which read that flag — runs again, and the request leaves again at once: no pause, no end, each
 * one a full report on the server, the OHLC work of the candles included.
 *
 * The contract. `createLazyReportRetry(delaysMs = LAZY_REPORT_RETRY_DELAYS_MS)` — one per lazy section and per page —
 * keeps the failures of one scope (brokers|start|end|currency) and says whether a request for a scope may go now:
 *   - nothing recorded, or failures recorded for another scope: it may;
 *   - `failed(s)`: a scope other than the recorded one starts over (zero failures), then one failure is counted. After
 *     failure n, n ≤ delays.length, the scope may not ask until a timer of `delays[n − 1]` ms fires; then it may, and the
 *     readers are woken. After failure n > delays.length the scope is exhausted: it may not, and no timer runs. With the
 *     defaults (2, 4, 8 s) a scope sends four requests at most: the first and three retries;
 *   - `succeeded(s)`: the failures are forgotten and the timer cancelled;
 *   - `reset()`, the page's Refresh: forgets, cancels, wakes the readers;
 *   - `dispose()`, the page is gone: cancels the timer, and no reader is woken afterwards;
 *   - `canAsk` reads no clock: a scope falls due only when its timer fires, so a fake clock drives everything.
 * `canAsk` is a reactive read: an effect that called it runs again when a retry falls due and after `reset()`, whatever
 * the state it was read in. The broker page needs the first one: its candles loader's `pnlCandlesLoading` is a plain
 * `let` of a legacy component that its template never reads — Svelte 5 makes such a binding a signal only when the
 * template or a `$:` reads it — so nothing runs the chart's effect again after a failure, and the read made before the
 * request, when nothing had failed yet, is the only one there is.
 *
 * Red before the cure: `./lazyReportRetry.svelte` does not exist yet, so the import below fails and the whole file fails
 * with it, no case run (Vitest: «Failed to resolve import "./lazyReportRetry.svelte" … Does the file exist?»).
 *
 * Vitest's fake clock is on in every case: `vi.getTimerCount()` says whether a retry is pending, and no real timer
 * outlives a case. After each case the effect readers are stopped first, then the timers cleared, the spies and the
 * clock restored.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {flushSync} from 'svelte';
import {assertEffectsRun, reactiveBox, recordReads} from '$test/runes.svelte';
import {createLazyReportRetry, LAZY_REPORT_RETRY_DELAYS_MS, type LazyReportRetry} from './lazyReportRetry.svelte';

/** The contract's delays, written out: the spec pins the numbers that were decided, it does not follow the code. */
const DELAYS_MS = [2_000, 4_000, 8_000] as const;
/** Far past the last delay: a scope that has not fallen due by then never will. */
const AN_HOUR_MS = 3_600_000;
/** Two scopes as the Dashboard writes them: brokers|start|end|currency, a period apart. */
const SCOPE = '3,7|2026-07-17|2026-10-17|EUR';
const OTHER_SCOPE = '3,7|2026-04-17|2026-10-17|EUR';

/** Teardowns of the effect roots a case opened: run before the timers are cleared, so no reader is woken by the cleanup. */
const stops: Array<() => void> = [];

/** Every value `read` returned, the first included, read from inside an effect — the way a panel's effect reads `canAsk`. */
function readsOf<T>(read: () => T): Array<T | Error> {
    const reads = recordReads(read);
    stops.push(reads.stop);
    return reads.values;
}

/** Moves the fake clock by `ms`, then flushes what a fired timer woke, as a component would be flushed. */
function advance(ms: number): void {
    vi.advanceTimersByTime(ms);
    flushSync();
}

/** The scope fails three times, each retry falling due: the fourth request — the last the defaults allow — may go. */
function failUntilLastRetry(retry: LazyReportRetry, scope: string): void {
    for (const delay of DELAYS_MS) {
        retry.failed(scope);
        advance(delay);
    }
}

beforeEach(() => {
    vi.useFakeTimers();
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
    vi.clearAllTimers();
    vi.restoreAllMocks();
    vi.useRealTimers();
});

describe('lazyReportRetry — the delays', () => {
    it('waits 2, 4 and 8 seconds by default: LAZY_REPORT_RETRY_DELAYS_MS', () => {
        expect([...LAZY_REPORT_RETRY_DELAYS_MS]).toEqual([...DELAYS_MS]);
    });

    it('lets the first request of any scope go: asking starts no timer and changes nothing', () => {
        const retry = createLazyReportRetry();

        expect(retry.canAsk(SCOPE)).toBe(true);
        expect(retry.canAsk(SCOPE), 'asking twice').toBe(true);
        expect(retry.canAsk(OTHER_SCOPE)).toBe(true);
        expect(vi.getTimerCount(), 'canAsk started a timer').toBe(0);
    });

    it('after failure n the scope waits the n-th delay — 2, then 4, then 8 s —, not a millisecond less, and may ask again at it', () => {
        const retry = createLazyReportRetry();

        for (const [index, delay] of DELAYS_MS.entries()) {
            const failure = index + 1;
            retry.failed(SCOPE);
            expect(retry.canAsk(SCOPE), `just after failure ${failure}`).toBe(false);
            expect(vi.getTimerCount(), `the retry timer of failure ${failure}`).toBe(1);

            advance(delay - 1);
            expect(retry.canAsk(SCOPE), `${delay - 1} ms after failure ${failure}`).toBe(false);

            advance(1);
            expect(retry.canAsk(SCOPE), `${delay} ms after failure ${failure}`).toBe(true);
            expect(vi.getTimerCount(), `a timer still pending once failure ${failure} fell due`).toBe(0);
        }
    });

    it('is exhausted by the failure after the last delay: no timer runs, and the scope never asks again, however long the page waits', () => {
        const retry = createLazyReportRetry();
        failUntilLastRetry(retry, SCOPE);
        expect(retry.canAsk(SCOPE), 'precondition: the third retry fell due').toBe(true);

        retry.failed(SCOPE);

        expect(retry.canAsk(SCOPE), 'just after the fourth failure').toBe(false);
        expect(vi.getTimerCount(), 'an exhausted scope keeps a timer').toBe(0);
        advance(AN_HOUR_MS);
        expect(retry.canAsk(SCOPE), 'an hour after the fourth failure').toBe(false);
    });

    it('with the defaults, a page that asks whenever it may, and always fails, sends four requests: at 0, 2, 6 and 14 s', () => {
        const retry = createLazyReportRetry();
        const start = Date.now();
        const sentAt: number[] = [];

        for (let elapsed = 0; elapsed <= 120_000; elapsed += 500) {
            if (retry.canAsk(SCOPE)) {
                sentAt.push(Date.now() - start);
                retry.failed(SCOPE);
            }
            advance(500);
        }

        expect(sentAt).toEqual([0, 2_000, 6_000, 14_000]);
    });

    it('honours custom delays: [100, 300] waits 100 ms, then 300 ms, and the third failure exhausts the scope', () => {
        const retry = createLazyReportRetry([100, 300]);

        retry.failed(SCOPE);
        advance(99);
        expect(retry.canAsk(SCOPE), '99 ms after failure 1').toBe(false);
        advance(1);
        expect(retry.canAsk(SCOPE), '100 ms after failure 1').toBe(true);

        retry.failed(SCOPE);
        advance(299);
        expect(retry.canAsk(SCOPE), '299 ms after failure 2').toBe(false);
        advance(1);
        expect(retry.canAsk(SCOPE), '300 ms after failure 2').toBe(true);

        retry.failed(SCOPE);
        expect(retry.canAsk(SCOPE), 'just after failure 3').toBe(false);
        expect(vi.getTimerCount(), 'an exhausted scope keeps a timer').toBe(0);
        advance(AN_HOUR_MS);
        expect(retry.canAsk(SCOPE), 'an hour after failure 3').toBe(false);
    });
});

describe('lazyReportRetry — one scope is recorded at a time', () => {
    it('lets another scope ask while one waits', () => {
        const retry = createLazyReportRetry();

        retry.failed(SCOPE);

        expect(retry.canAsk(SCOPE)).toBe(false);
        expect(retry.canAsk(OTHER_SCOPE)).toBe(true);
    });

    it('starts over on a failure of another scope: its first delay, counted from its own failure, whatever the old scope was waiting for — and the old scope may ask again', () => {
        const retry = createLazyReportRetry();
        retry.failed(SCOPE);
        advance(1_000);

        retry.failed(OTHER_SCOPE);

        expect(retry.canAsk(OTHER_SCOPE), 'just after its failure').toBe(false);
        expect(retry.canAsk(SCOPE), 'the failures recorded are another scope’s').toBe(true);
        // Past the 2 s the old scope was waiting for: its timer, had it survived, would make the new scope due a second early.
        advance(DELAYS_MS[0] - 1);
        expect(retry.canAsk(OTHER_SCOPE), `${DELAYS_MS[0] - 1} ms after its failure`).toBe(false);
        advance(1);
        expect(retry.canAsk(OTHER_SCOPE), `${DELAYS_MS[0]} ms after its failure`).toBe(true);
    });

    it('holds nothing back once exhausted: another scope starts over at the first delay, and the exhausted one may ask again once it is no longer the one recorded', () => {
        const retry = createLazyReportRetry();
        failUntilLastRetry(retry, SCOPE);
        retry.failed(SCOPE);
        expect(retry.canAsk(SCOPE), 'precondition: the scope is exhausted').toBe(false);
        expect(retry.canAsk(OTHER_SCOPE), 'another scope, before it fails').toBe(true);

        retry.failed(OTHER_SCOPE);

        expect(retry.canAsk(OTHER_SCOPE), 'just after its first failure').toBe(false);
        expect(vi.getTimerCount(), 'the new scope waits on a timer, it is not exhausted').toBe(1);
        advance(DELAYS_MS[0] - 1);
        expect(retry.canAsk(OTHER_SCOPE), `${DELAYS_MS[0] - 1} ms after its first failure`).toBe(false);
        advance(1);
        expect(retry.canAsk(OTHER_SCOPE), `${DELAYS_MS[0]} ms after its first failure`).toBe(true);
        expect(retry.canAsk(SCOPE), 'the old scope, once the failures recorded are another scope’s').toBe(true);
    });
});

describe('lazyReportRetry — succeeded, reset and dispose', () => {
    it('succeeded forgets the failures and cancels the timer: the scope may ask at once, and its next failure waits the first delay again', () => {
        const retry = createLazyReportRetry();
        retry.failed(SCOPE);
        advance(DELAYS_MS[0]);
        retry.failed(SCOPE);
        expect(vi.getTimerCount(), 'precondition: the second retry is pending').toBe(1);

        retry.succeeded(SCOPE);

        expect(retry.canAsk(SCOPE), 'just after the success').toBe(true);
        expect(vi.getTimerCount(), 'the pending retry was not cancelled').toBe(0);
        retry.failed(SCOPE);
        advance(DELAYS_MS[0] - 1);
        expect(retry.canAsk(SCOPE), `${DELAYS_MS[0] - 1} ms after the failure that followed the success`).toBe(false);
        advance(1);
        expect(retry.canAsk(SCOPE), `${DELAYS_MS[0]} ms after the failure that followed the success`).toBe(true);
    });

    it('reset forgets the failures and cancels the timer: a waiting scope may ask at once, and its next failure waits the first delay again', () => {
        const retry = createLazyReportRetry();
        retry.failed(SCOPE);
        advance(DELAYS_MS[0]);
        retry.failed(SCOPE);
        expect(vi.getTimerCount(), 'precondition: the second retry is pending').toBe(1);

        retry.reset();

        expect(retry.canAsk(SCOPE), 'just after reset').toBe(true);
        expect(vi.getTimerCount(), 'the pending retry was not cancelled').toBe(0);
        retry.failed(SCOPE);
        advance(DELAYS_MS[0] - 1);
        expect(retry.canAsk(SCOPE), `${DELAYS_MS[0] - 1} ms after the failure that followed reset`).toBe(false);
        advance(1);
        expect(retry.canAsk(SCOPE), `${DELAYS_MS[0]} ms after the failure that followed reset`).toBe(true);
    });

    it('reset lets an exhausted scope ask again, and its next failure waits the first delay', () => {
        const retry = createLazyReportRetry();
        failUntilLastRetry(retry, SCOPE);
        retry.failed(SCOPE);
        expect(retry.canAsk(SCOPE), 'precondition: the scope is exhausted').toBe(false);

        retry.reset();

        expect(retry.canAsk(SCOPE), 'just after reset').toBe(true);
        retry.failed(SCOPE);
        expect(vi.getTimerCount(), 'the failure after reset waits on a timer, the scope is not exhausted any more').toBe(1);
        advance(DELAYS_MS[0]);
        expect(retry.canAsk(SCOPE), `${DELAYS_MS[0]} ms after the failure that followed reset`).toBe(true);
    });

    it('dispose cancels the pending timer', () => {
        const retry = createLazyReportRetry();
        retry.failed(SCOPE);
        expect(vi.getTimerCount(), 'precondition: the first retry is pending').toBe(1);

        retry.dispose();

        expect(vi.getTimerCount()).toBe(0);
    });

    it('two retries share nothing: one failing leaves the other free to ask, and each waits on its own timer', () => {
        const candles = createLazyReportRetry();
        const contribution = createLazyReportRetry();

        candles.failed(SCOPE);
        expect(contribution.canAsk(SCOPE), 'the contribution, while the candles wait').toBe(true);
        advance(1_000);
        contribution.failed(SCOPE);
        expect(vi.getTimerCount(), 'one timer each').toBe(2);

        advance(1_000);
        expect(candles.canAsk(SCOPE), 'the candles, 2 s after their failure').toBe(true);
        expect(contribution.canAsk(SCOPE), 'the contribution, 1 s after its failure').toBe(false);
        advance(1_000);
        expect(contribution.canAsk(SCOPE), 'the contribution, 2 s after its failure').toBe(true);
    });
});

describe('lazyReportRetry — canAsk, read by an effect as the panels read it', () => {
    beforeAll(() => {
        assertEffectsRun();
    });

    it('an effect that read canAsk once, before anything failed, runs again when each retry falls due — once, not a millisecond before — and never once the scope is exhausted (the broker page)', () => {
        const retry = createLazyReportRetry();
        const reads = readsOf(() => retry.canAsk(SCOPE));
        expect(reads).toEqual([true]);

        for (const [index, delay] of DELAYS_MS.entries()) {
            const failure = index + 1;
            retry.failed(SCOPE);
            flushSync();
            // Counted from here: whether `failed` itself wakes the effect is not what the contract says.
            const before = reads.length;
            advance(delay - 1);
            expect(reads.length, `the effect ran again ${delay - 1} ms after failure ${failure}, before its retry fell due`).toBe(before);
            advance(1);
            expect(reads.slice(before), `the runs of the effect when the retry of failure ${failure} fell due`).toEqual([true]);
        }

        retry.failed(SCOPE);
        flushSync();
        const exhausted = reads.length;
        advance(AN_HOUR_MS);
        expect(reads.length, 'the effect ran again after the fourth failure exhausted the scope').toBe(exhausted);
    });

    it('an effect that read canAsk while its scope waited runs again when the retry falls due (the Dashboard: its loading flag runs the effect again after the failure)', () => {
        const retry = createLazyReportRetry();
        const page = reactiveBox({loading: false});
        // The panel's effect as the page's loader guards it: nothing is asked while a request is in flight.
        const reads = readsOf(() => (page.loading ? 'loading' : retry.canAsk(SCOPE)));

        page.loading = true;
        flushSync();
        retry.failed(SCOPE);
        page.loading = false;
        flushSync();
        expect(reads, 'precondition: the effect read the scope while it waited').toEqual([true, 'loading', false]);

        advance(DELAYS_MS[0] - 1);
        expect(reads.length, 'the effect ran again before the retry fell due').toBe(3);
        advance(1);
        expect(reads.slice(3), 'the runs of the effect when the retry fell due').toEqual([true]);
    });

    it('reset wakes an effect reading canAsk, which then may ask: Refresh once the scope is exhausted', () => {
        const retry = createLazyReportRetry();
        const reads = readsOf(() => retry.canAsk(SCOPE));
        failUntilLastRetry(retry, SCOPE);
        retry.failed(SCOPE);
        flushSync();
        expect(retry.canAsk(SCOPE), 'precondition: the scope is exhausted').toBe(false);
        const before = reads.length;

        retry.reset();
        flushSync();

        expect(reads.slice(before), 'the runs of the effect after reset').toEqual([true]);
    });

    it('dispose: the effect is not woken when the cancelled retry would have fallen due, nor ever after', () => {
        const retry = createLazyReportRetry();
        const reads = readsOf(() => retry.canAsk(SCOPE));
        retry.failed(SCOPE);
        flushSync();

        retry.dispose();
        flushSync();
        const disposed = reads.length;
        advance(AN_HOUR_MS);

        expect(reads.length, 'the effect ran again after dispose').toBe(disposed);
    });
});

describe('lazyReportRetry — the timer alone makes a scope due', () => {
    it('canAsk reads no clock: neither Date.now nor performance.now, whatever the state of the scope', () => {
        const retry = createLazyReportRetry();
        const dateNow = vi.spyOn(Date, 'now');
        const performanceNow = vi.spyOn(performance, 'now');
        const ask = (state: string): boolean => {
            dateNow.mockClear();
            performanceNow.mockClear();
            const answer = retry.canAsk(SCOPE);
            expect(dateNow, `canAsk read Date.now ${state}`).not.toHaveBeenCalled();
            expect(performanceNow, `canAsk read performance.now ${state}`).not.toHaveBeenCalled();
            return answer;
        };

        expect(ask('before anything failed')).toBe(true);
        retry.failed(SCOPE);
        expect(ask('while the scope waits')).toBe(false);
        advance(DELAYS_MS[0]);
        expect(ask('once the retry fell due')).toBe(true);
        retry.failed(SCOPE);
        advance(DELAYS_MS[1]);
        retry.failed(SCOPE);
        advance(DELAYS_MS[2]);
        retry.failed(SCOPE);
        expect(ask('once the scope is exhausted')).toBe(false);
    });

    it('a waiting scope stays waiting when the wall clock jumps an hour ahead with no timer fired, and falls due when its timer fires', () => {
        const retry = createLazyReportRetry();
        retry.failed(SCOPE);

        // The system time moves, the timers keep their own due moment: only a clock reading would see it.
        vi.setSystemTime(Date.now() + AN_HOUR_MS);

        expect(retry.canAsk(SCOPE), 'an hour later on the wall clock, its timer not fired').toBe(false);
        advance(DELAYS_MS[0]);
        expect(retry.canAsk(SCOPE), 'once its timer fired').toBe(true);
    });
});
