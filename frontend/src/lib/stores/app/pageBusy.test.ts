// @vitest-environment jsdom
//
// The docblock above is load-bearing: the reactivity cases read `busy` inside an effect, and the last block asserts that
// an effect does NOT run again — under the default `node` environment `$effect` never runs, so that would pass vacuously
// (`$test/runes.svelte`; `assertEffectsRun` turns it into a message).
/**
 * pageBusy — what the Refresh button of a page waits for (Y11, developer decision 48 / P3; contract approved 16/10/2026).
 *
 * The button spins while the «big» requests of the page are in flight: the first load, a Refresh, a change of period,
 * scope, filter or tab, the load of a panel. Never the live-price poller, never a background reload. Each such request
 * holds a token from `begin` (or `track`) until `end`, well or badly; a token that never comes back is dropped at its
 * timeout — for the button only, the request is not cancelled — with one console warning naming it; a route change
 * drops them all (`reset`). The button and the pages are wired in later steps of Y11: this file pins the store alone.
 *
 * `join` (N55) is for a load that completes what the page is already doing — the P&L candles and the contribution a
 * panel asks again once the page's report has dropped them: on a busy page it holds a token of its own until its work
 * settles, on an idle page (a reload in background has landed, or the user switched the view) the work runs alone and
 * holds nothing. The choice is made at the call, from the pending list read untracked.
 *
 * The pages call `track` / `begin` from inside the `$effect` of a period, a currency or a filter, and the panels call
 * `join` from theirs. That effect must not start depending on the store: every other token that begins or ends would
 * run it again, and an effect that begins on every run would loop. The effect blocks call each writer — `begin`,
 * `track`, `join`, `end`, `reset` — from inside an effect, on its first run only, and count its runs while other
 * requests come and go; a change of the effect's own dependency then proves it was alive all along.
 *
 * The store is a module singleton: after each case its effect readers are stopped, then `reset()`, then the fake clock
 * (on in every case, so no real two-minute timer outlives one) and the `console.warn` spy are restored.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi, type MockInstance} from 'vitest';
import {flushSync} from 'svelte';
import {assertEffectsRun, reactiveBox, recordReads} from '$test/runes.svelte';
import {PAGE_BUSY_TIMEOUT_MS, pageBusy, type BusyToken} from './pageBusy.svelte';

/** A custom timeout, short enough to read at a glance; the default one is pinned on its own. */
const SHORT_TIMEOUT_MS = 1_000;

let warn: MockInstance<Console['warn']>;

/** Teardowns of the effect roots a case opened: run before the store is reset, so the reset re-runs no reader. */
const stops: Array<() => void> = [];

/** Every value of `pageBusy.busy` an effect has read, the first one included — the way a component reads it. */
function busyAsReadByAnEffect(): Array<boolean | Error> {
    const reads = recordReads(() => pageBusy.busy);
    stops.push(reads.stop);
    return reads.values;
}

/** What the `call`-th `console.warn` printed: its arguments joined, a non-string one as its JSON. */
function warned(call: number): string {
    return (warn.mock.calls[call] ?? []).map((arg) => (typeof arg === 'string' ? arg : JSON.stringify(arg))).join(' ');
}

/** A promise the case settles by hand: a request still in flight. */
function deferred<T>() {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((settle) => {
        resolve = settle;
    });
    return {promise, resolve};
}

/**
 * An effect shaped like a page's period effect: it reads the page's period and calls `act` — the store's writer under
 * test — on its first run only, so that a regression shows as a count, not as a loop. Each entry of `runs` is one run,
 * holding the period that run read.
 */
function pagePeriodEffect(act: () => void): {page: {period: string}; runs: Array<string | Error>} {
    const page = reactiveBox({period: '1M'});
    let calls = 0;
    const reads = recordReads(() => {
        const period = page.period;
        if (calls++ === 0) act();
        return period;
    });
    stops.push(reads.stop);
    return {page, runs: reads.values};
}

/**
 * Other requests of the page come and go — a begin, a second one, an end, a timeout — each flushed as a component
 * would be. Returns the pending labels after each step: the case asserts them, so an effect that did not run again
 * cannot owe it to a list that never changed.
 */
function otherRequestsComeAndGo(): string[][] {
    const seen: string[][] = [];
    const refresh = pageBusy.begin('refresh');
    flushSync();
    seen.push([...pageBusy.labels]);
    pageBusy.begin('panel-load', {timeoutMs: SHORT_TIMEOUT_MS});
    flushSync();
    seen.push([...pageBusy.labels]);
    pageBusy.end(refresh);
    flushSync();
    seen.push([...pageBusy.labels]);
    vi.advanceTimersByTime(SHORT_TIMEOUT_MS);
    flushSync();
    seen.push([...pageBusy.labels]);
    return seen;
}

/** The labels `otherRequestsComeAndGo` sees step by step, over the tokens `base` already pending. */
function comingAndGoingOver(base: string[]): string[][] {
    return [[...base, 'refresh'], [...base, 'refresh', 'panel-load'], [...base, 'panel-load'], base];
}

beforeEach(() => {
    vi.useFakeTimers();
    warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
    while (stops.length > 0) stops.pop()?.();
    pageBusy.reset();
    vi.useRealTimers();
    vi.restoreAllMocks();
});

describe('pageBusy — the pending tokens', () => {
    it('starts idle: not busy, no labels', () => {
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });

    it('begin hands back a token carrying its label and makes the page busy; ending it makes the page idle again', () => {
        const token = pageBusy.begin('first-load');

        expect(token).toMatchObject({id: expect.any(Number), label: 'first-load'});
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);

        pageBusy.end(token);

        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });

    it('stays busy until every pending token has ended, listing the pending labels in begin order', () => {
        const first = pageBusy.begin('first-load');
        const refresh = pageBusy.begin('refresh');
        const panel = pageBusy.begin('panel-load');
        expect(pageBusy.labels).toEqual(['first-load', 'refresh', 'panel-load']);

        pageBusy.end(refresh);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load', 'panel-load']);

        pageBusy.end(first);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['panel-load']);

        pageBusy.end(panel);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });

    it('ends by token, not by label: two pending requests of the same kind end one at a time', () => {
        const left = pageBusy.begin('panel-load');
        const right = pageBusy.begin('panel-load');

        pageBusy.end(left);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['panel-load']);

        pageBusy.end(right);
        expect(pageBusy.busy).toBe(false);
    });

    it('end is idempotent: ending a token again neither throws nor ends another pending token', () => {
        const first = pageBusy.begin('first-load');
        const panel = pageBusy.begin('panel-load');

        pageBusy.end(first);
        expect(() => pageBusy.end(first)).not.toThrow();
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['panel-load']);

        pageBusy.end(panel);
        expect(() => pageBusy.end(panel)).not.toThrow();
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });

    it('ending a token it never handed out does nothing, even when a pending token carries the same label', () => {
        // An id the store never hands out.
        const forged: BusyToken = {id: -1, label: 'refresh'};
        expect(() => pageBusy.end(forged)).not.toThrow();
        expect(pageBusy.busy).toBe(false);

        pageBusy.begin('refresh');
        expect(() => pageBusy.end(forged)).not.toThrow();
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['refresh']);
    });

    it('reset drops every pending token, and a token begun before it and ended after it does not end a token begun after it', () => {
        const stale = pageBusy.begin('first-load');
        pageBusy.begin('panel-load');

        pageBusy.reset();
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);

        // The new page starts its own first load; then the request of the old page comes back late.
        const current = pageBusy.begin('first-load');
        expect(current.id).not.toBe(stale.id);
        expect(() => pageBusy.end(stale)).not.toThrow();
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);

        pageBusy.end(current);
        expect(pageBusy.busy).toBe(false);
    });

    it('never hands out the same id twice, across ends, timeouts and resets', () => {
        const ids: number[] = [];
        for (let round = 0; round < 3; round++) {
            const ended = pageBusy.begin('refresh');
            pageBusy.end(ended);
            const expired = pageBusy.begin('panel-load', {timeoutMs: SHORT_TIMEOUT_MS});
            vi.advanceTimersByTime(SHORT_TIMEOUT_MS);
            const dropped = pageBusy.begin('first-load');
            pageBusy.reset();
            ids.push(ended.id, expired.id, dropped.id);
        }

        expect(new Set(ids).size).toBe(ids.length);
    });
});

describe('pageBusy — the timeout of a token', () => {
    it('drops a token at its own timeoutMs, not a millisecond before, and warns once, naming it', () => {
        pageBusy.begin('lots-panel-load', {timeoutMs: SHORT_TIMEOUT_MS});

        vi.advanceTimersByTime(SHORT_TIMEOUT_MS - 1);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['lots-panel-load']);
        expect(warn).not.toHaveBeenCalled();

        vi.advanceTimersByTime(1);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warned(0)).toContain('lots-panel-load');

        // Once: nothing fires later, not even at the default timeout.
        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).toHaveBeenCalledTimes(1);
    });

    it('uses PAGE_BUSY_TIMEOUT_MS, 120 000 ms, when begun without timeoutMs', () => {
        expect(PAGE_BUSY_TIMEOUT_MS).toBe(120_000);
        pageBusy.begin('first-load');

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS - 1);
        expect(pageBusy.busy).toBe(true);
        expect(warn).not.toHaveBeenCalled();

        vi.advanceTimersByTime(1);
        expect(pageBusy.busy).toBe(false);
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warned(0)).toContain('first-load');
    });

    it('drops only the expired token: the others stay pending, and its late end touches nothing, not even a new token of its kind', () => {
        const lost = pageBusy.begin('fx-history-load', {timeoutMs: SHORT_TIMEOUT_MS});
        const kept = pageBusy.begin('first-load');

        vi.advanceTimersByTime(SHORT_TIMEOUT_MS);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warned(0)).toContain('fx-history-load');

        // The page asks again; then the lost request comes back after all.
        const again = pageBusy.begin('fx-history-load');
        expect(() => pageBusy.end(lost)).not.toThrow();
        expect(pageBusy.labels).toEqual(['first-load', 'fx-history-load']);
        expect(warn).toHaveBeenCalledTimes(1);

        pageBusy.end(kept);
        pageBusy.end(again);
        expect(pageBusy.busy).toBe(false);
    });

    it('clears the timer of a token ended in time: no warning follows, however long one waits', () => {
        const baseline = vi.getTimerCount();
        const token = pageBusy.begin('lots-panel-load', {timeoutMs: SHORT_TIMEOUT_MS});
        expect(vi.getTimerCount(), 'precondition: the token armed its timer').toBeGreaterThan(baseline);

        vi.advanceTimersByTime(SHORT_TIMEOUT_MS / 2);
        pageBusy.end(token);
        expect(vi.getTimerCount(), 'no timer left behind by the ended token').toBe(baseline);

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
        expect(pageBusy.busy).toBe(false);
    });

    it('clears every timer on reset: no warning follows', () => {
        const baseline = vi.getTimerCount();
        pageBusy.begin('lots-panel-load', {timeoutMs: SHORT_TIMEOUT_MS});
        pageBusy.begin('first-load');
        expect(vi.getTimerCount(), 'precondition: the tokens armed their timers').toBeGreaterThan(baseline);

        pageBusy.reset();
        expect(vi.getTimerCount(), 'no timer left behind by reset').toBe(baseline);

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });
});

describe('pageBusy.track', () => {
    it('keeps the page busy while the work is pending, then resolves with the value of the work and ends the token', async () => {
        const answer = deferred<{rows: number}>();
        const result = pageBusy.track('first-load', () => answer.promise);

        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);

        const payload = {rows: 3};
        answer.resolve(payload);
        await expect(result).resolves.toBe(payload);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);

        // Ended, not merely dropped: its timer went with it.
        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('ends the token when the work rejects, and rethrows the same error', async () => {
        const failure = new Error('502 from the backend');

        await expect(pageBusy.track('refresh', () => Promise.reject(failure))).rejects.toBe(failure);
        expect(pageBusy.busy).toBe(false);

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('ends the token when the work throws synchronously, and the error still reaches the caller', async () => {
        const failure = new Error('thrown before the request left');
        let caught: unknown;
        try {
            // A synchronous throw or a rejection: the contract allows either, this catches both.
            await pageBusy.track('refresh', () => {
                throw failure;
            });
        } catch (error) {
            caught = error;
        }

        expect(caught).toBe(failure);
        expect(pageBusy.busy).toBe(false);

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('passes timeoutMs on: past it the token is dropped with its warning, but the work is not cancelled and its value still arrives', async () => {
        const answer = deferred<string>();
        const result = pageBusy.track('slow-panel-load', () => answer.promise, {timeoutMs: SHORT_TIMEOUT_MS});

        vi.advanceTimersByTime(SHORT_TIMEOUT_MS);
        expect(pageBusy.busy).toBe(false);
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warned(0)).toContain('slow-panel-load');

        // The page asks again; then the first answer lands after all, and its late end touches nothing.
        const again = pageBusy.begin('slow-panel-load');
        answer.resolve('late answer');
        await expect(result).resolves.toBe('late answer');
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['slow-panel-load']);
        expect(warn).toHaveBeenCalledTimes(1);

        pageBusy.end(again);
        expect(pageBusy.busy).toBe(false);
    });
});

describe('pageBusy.busy — reactive, as the Refresh button reads it', () => {
    beforeAll(() => {
        assertEffectsRun();
    });

    it('an effect reading busy runs again when a token begins, and again when it ends', () => {
        const seen = busyAsReadByAnEffect();

        const token = pageBusy.begin('first-load');
        flushSync();
        pageBusy.end(token);
        flushSync();

        expect(seen).toEqual([false, true, false]);
    });

    it('an effect reading busy runs again when the last pending token times out', () => {
        const seen = busyAsReadByAnEffect();

        pageBusy.begin('lots-panel-load', {timeoutMs: SHORT_TIMEOUT_MS});
        flushSync();
        vi.advanceTimersByTime(SHORT_TIMEOUT_MS);
        flushSync();

        expect(seen).toEqual([false, true, false]);
    });

    it('an effect reading busy runs again on reset', () => {
        const seen = busyAsReadByAnEffect();

        pageBusy.begin('first-load');
        pageBusy.begin('panel-load');
        flushSync();
        pageBusy.reset();
        flushSync();

        expect(seen).toEqual([false, true, false]);
    });
});

describe('pageBusy — called from inside an effect, as the pages call it', () => {
    beforeAll(() => {
        assertEffectsRun();
    });

    it('an effect that begins a token does not run again when other tokens begin, end or time out, nor when its own token ends', () => {
        let own!: BusyToken;
        const effect = pagePeriodEffect(() => {
            own = pageBusy.begin('period');
        });
        expect(effect.runs).toEqual(['1M']);
        expect(pageBusy.labels).toEqual(['period']);

        expect(otherRequestsComeAndGo()).toEqual(comingAndGoingOver(['period']));
        expect(effect.runs).toEqual(['1M']);

        pageBusy.end(own);
        flushSync();
        expect(pageBusy.busy).toBe(false);
        expect(effect.runs).toEqual(['1M']);

        // The presence barrier: the effect was alive all along — it runs again when what it does read changes.
        effect.page.period = '3M';
        flushSync();
        expect(effect.runs).toEqual(['1M', '3M']);
    });

    it('an effect that calls track does not run again when other tokens come and go, on reset, nor when its own work settles', async () => {
        const answer = deferred<string>();
        let work!: Promise<string>;
        const effect = pagePeriodEffect(() => {
            work = pageBusy.track('period', () => answer.promise);
        });
        expect(effect.runs).toEqual(['1M']);
        expect(pageBusy.labels).toEqual(['period']);

        expect(otherRequestsComeAndGo()).toEqual(comingAndGoingOver(['period']));
        expect(effect.runs).toEqual(['1M']);

        // The route changes while the work is in flight; then the work lands, and `track` ends a token already dropped.
        pageBusy.reset();
        flushSync();
        expect(pageBusy.busy).toBe(false);
        expect(effect.runs).toEqual(['1M']);

        answer.resolve('loaded');
        await expect(work).resolves.toBe('loaded');
        flushSync();
        expect(effect.runs).toEqual(['1M']);

        effect.page.period = '3M';
        flushSync();
        expect(effect.runs).toEqual(['1M', '3M']);
    });

    it.each<{writer: string; act: (previous: BusyToken) => void}>([
        {writer: 'end', act: (previous) => pageBusy.end(previous)},
        {writer: 'reset', act: () => pageBusy.reset()},
    ])('an effect that calls $writer does not start depending on the store either', ({act}) => {
        const previous = pageBusy.begin('first-load');
        const effect = pagePeriodEffect(() => act(previous));
        expect(effect.runs).toEqual(['1M']);
        expect(pageBusy.busy, 'precondition: the call inside the effect took the token off the list').toBe(false);

        expect(otherRequestsComeAndGo()).toEqual(comingAndGoingOver([]));
        expect(effect.runs).toEqual(['1M']);

        effect.page.period = '3M';
        flushSync();
        expect(effect.runs).toEqual(['1M', '3M']);
    });
});

describe('pageBusy.join — a load that completes what the page is already doing (N55)', () => {
    it('on an idle page runs the work alone: started at the call, no token and no timer while it runs, and it resolves with the value of the work', async () => {
        const baseline = vi.getTimerCount();
        const answer = deferred<{rows: number}>();
        let started = 0;
        const result = pageBusy.join(
            'panel',
            () => {
                started += 1;
                return answer.promise;
            },
            {timeoutMs: SHORT_TIMEOUT_MS},
        );

        expect(started, 'the work starts at the call').toBe(1);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
        expect(vi.getTimerCount(), 'no token, so no timer either').toBe(baseline);

        const payload = {rows: 3};
        answer.resolve(payload);
        await expect(result).resolves.toBe(payload);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);

        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('on a busy page holds a token of its own, after the request it joined, until its work settles: the page stays busy once that request has ended', async () => {
        const first = pageBusy.begin('first-load');
        const answer = deferred<string>();
        const result = pageBusy.join('panel', () => answer.promise);

        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load', 'panel']);

        pageBusy.end(first);
        expect(pageBusy.busy, 'the joined work is still pending').toBe(true);
        expect(pageBusy.labels).toEqual(['panel']);

        answer.resolve('loaded');
        await expect(result).resolves.toBe('loaded');
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);

        // Ended, not merely dropped: its timer went with it.
        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('on a busy page, a joined work that settles before the request it joined ends its own token only', async () => {
        const first = pageBusy.begin('first-load');
        const answer = deferred<string>();
        const result = pageBusy.join('panel', () => answer.promise);
        expect(pageBusy.labels).toEqual(['first-load', 'panel']);

        answer.resolve('loaded');
        await expect(result).resolves.toBe('loaded');
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);

        pageBusy.end(first);
        expect(pageBusy.busy).toBe(false);
    });

    it('decides at the call: a work started alone takes no token when the page turns busy meanwhile, and its end leaves the later token pending', async () => {
        const answer = deferred<string>();
        const result = pageBusy.join('panel', () => answer.promise);
        expect(pageBusy.busy, 'precondition: the page was idle at the call').toBe(false);

        const refresh = pageBusy.begin('refresh');
        expect(pageBusy.labels, 'only the later request is pending').toEqual(['refresh']);

        answer.resolve('loaded');
        await expect(result).resolves.toBe('loaded');
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['refresh']);

        pageBusy.end(refresh);
        expect(pageBusy.busy).toBe(false);
    });

    it('joined: a rejection releases its token, and the same error reaches the caller', async () => {
        const first = pageBusy.begin('first-load');
        const failure = new Error('502 from the backend');
        const result = pageBusy.join('panel', () => Promise.reject(failure));
        expect(pageBusy.labels, 'precondition: the work joined the pending request').toEqual(['first-load', 'panel']);

        await expect(result).rejects.toBe(failure);
        expect(pageBusy.busy).toBe(true);
        expect(pageBusy.labels).toEqual(['first-load']);

        pageBusy.end(first);
        expect(pageBusy.busy).toBe(false);
        vi.advanceTimersByTime(PAGE_BUSY_TIMEOUT_MS);
        expect(warn).not.toHaveBeenCalled();
    });

    it('alone: a rejection reaches the caller, and nothing is pending', async () => {
        const failure = new Error('502 from the backend');

        await expect(pageBusy.join('panel', () => Promise.reject(failure))).rejects.toBe(failure);
        expect(pageBusy.busy).toBe(false);
        expect(pageBusy.labels).toEqual([]);
    });

    it.each<{page: string; pendingBefore: () => string[]}>([
        {page: 'an idle', pendingBefore: () => []},
        {
            page: 'a busy',
            pendingBefore: () => {
                pageBusy.begin('first-load');
                return ['first-load'];
            },
        },
    ])('on $page page, a work that throws synchronously makes a rejected promise, not a throw at the call, and leaves only what was pending before', async ({pendingBefore}) => {
        const before = pendingBefore();
        const failure = new Error('thrown before the request left');
        let result!: Promise<unknown>;

        expect(() => {
            result = pageBusy.join('panel', () => {
                throw failure;
            });
        }).not.toThrow();

        await expect(result).rejects.toBe(failure);
        expect(pageBusy.labels).toEqual(before);
    });

    it('joined: passes timeoutMs on to its token — past it the token is dropped with its warning, and the value of the work still arrives', async () => {
        const first = pageBusy.begin('first-load');
        const answer = deferred<string>();
        const result = pageBusy.join('slow-panel-load', () => answer.promise, {timeoutMs: SHORT_TIMEOUT_MS});
        pageBusy.end(first);

        vi.advanceTimersByTime(SHORT_TIMEOUT_MS - 1);
        expect(pageBusy.labels).toEqual(['slow-panel-load']);
        expect(warn).not.toHaveBeenCalled();

        vi.advanceTimersByTime(1);
        expect(pageBusy.busy).toBe(false);
        expect(warn).toHaveBeenCalledTimes(1);
        expect(warned(0)).toContain('slow-panel-load');

        answer.resolve('late answer');
        await expect(result).resolves.toBe('late answer');
        expect(pageBusy.busy).toBe(false);
        expect(warn).toHaveBeenCalledTimes(1);
    });
});

describe('pageBusy.join — called from inside an effect, as the panels call it', () => {
    beforeAll(() => {
        assertEffectsRun();
    });

    it('an effect that joins a busy page does not run again when other tokens come and go, when the request it joined ends, nor when its own work settles', async () => {
        const first = pageBusy.begin('first-load');
        const answer = deferred<string>();
        let work!: Promise<string>;
        const effect = pagePeriodEffect(() => {
            work = pageBusy.join('panel', () => answer.promise);
        });
        expect(effect.runs).toEqual(['1M']);
        expect(pageBusy.labels, 'precondition: the call inside the effect joined the pending request').toEqual(['first-load', 'panel']);

        expect(otherRequestsComeAndGo()).toEqual(comingAndGoingOver(['first-load', 'panel']));
        expect(effect.runs).toEqual(['1M']);

        pageBusy.end(first);
        flushSync();
        expect(pageBusy.labels).toEqual(['panel']);
        expect(effect.runs).toEqual(['1M']);

        answer.resolve('loaded');
        await expect(work).resolves.toBe('loaded');
        flushSync();
        expect(pageBusy.busy).toBe(false);
        expect(effect.runs).toEqual(['1M']);

        // The presence barrier: the effect was alive all along — it runs again when what it does read changes.
        effect.page.period = '3M';
        flushSync();
        expect(effect.runs).toEqual(['1M', '3M']);
    });

    it('an effect that calls join on an idle page does not run again when tokens begin, end or time out afterwards, nor when its work settles', async () => {
        const answer = deferred<string>();
        let work!: Promise<string>;
        const effect = pagePeriodEffect(() => {
            work = pageBusy.join('panel', () => answer.promise);
        });
        expect(effect.runs).toEqual(['1M']);
        expect(pageBusy.busy, 'precondition: the call inside the effect ran the work alone').toBe(false);

        expect(otherRequestsComeAndGo()).toEqual(comingAndGoingOver([]));
        expect(effect.runs).toEqual(['1M']);

        answer.resolve('loaded');
        await expect(work).resolves.toBe('loaded');
        flushSync();
        expect(pageBusy.busy).toBe(false);
        expect(effect.runs).toEqual(['1M']);

        effect.page.period = '3M';
        flushSync();
        expect(effect.runs).toEqual(['1M', '3M']);
    });
});
