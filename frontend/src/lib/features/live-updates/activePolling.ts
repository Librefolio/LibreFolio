/**
 * A live update that runs only while someone is using the page: one helper for every poll of the app (F26, decision 31).
 *
 * It runs `run` every `intervalMs`, and pauses while the tab is hidden and after `idleMs` without input (two minutes by
 * default). It resumes by itself as soon as the tab is visible again or the user moves the mouse: if the next poll is
 * already due it polls at once, otherwise when it is due. A paused poll sends nothing, so a tab left open stops costing
 * requests to the server and to the price providers, and a cloud instance can sleep.
 *
 * Every poll starts from a timer, never inside the call that starts or nudges the poller: a page creates the poller in
 * an `$effect`, and the synchronous head of a poll would subscribe that effect to everything it reads. A poll still in
 * flight when the next is due makes that tick skip.
 *
 * A poll that fails — `run` throws, or returns `{ok: false}` — makes the next one wait longer: twice the interval, then
 * four times and so on, up to `maxBackoffMs` (ten minutes by default); the first success restores the interval (Z7,
 * D-Z7-1). A poll can also return `notBefore`, a time before which the next one does not start: the end of a provider's
 * pause, or the server's `Retry-After`. A resume waits for both; `pollNow` ignores them, and its outcome counts.
 *
 * Usage:
 *   const poller = startActivePolling({run: refresh, intervalMs: 60_000, onstatechange: (s) => (state = s)});
 *   poller.pollNow(); // a refresh the user asked for: the cadence restarts from it
 *   poller.stop();    // in the effect's cleanup
 *
 * @module lib/features/live-updates/activePolling
 */

import {getActivityTracker, type ActivitySignal, type ActivityTracker} from './activityTracker';
import {LIVE_UPDATES_IDLE_MS, LIVE_UPDATES_MAX_BACKOFF_MS} from './cadence';

export type ActivePollingState = 'running' | 'paused-idle' | 'paused-hidden' | 'stopped';

/** What a poll tells the next one. Anything that is not an object with `ok: false` is a success. */
export interface PollOutcome {
    /** `false`: the poll failed, and the next one waits longer. */
    ok?: boolean;
    /** A `Date.now()` time before which the next poll does not start. */
    notBefore?: number;
}

export interface ActivePollingOptions {
    /** One poll. Throwing is a failure, like returning `{ok: false}`. */
    run: () => PollOutcome | void | Promise<PollOutcome | void>;
    /** Between the starts of two polls. */
    intervalMs: number;
    /** No input for this long pauses the polls; 0 never pauses for that. Default: two minutes. */
    idleMs?: number;
    /** Delay of the first poll. Default 0: at once, from a timer. */
    initialDelayMs?: number;
    /** The longest wait after failures in a row; never shorter than `intervalMs`. Default: ten minutes. */
    maxBackoffMs?: number;
    /** The initial state, then every change. */
    onstatechange?: (state: ActivePollingState) => void;
    /** Default: the page's tracker. */
    tracker?: ActivityTracker;
}

export interface ActivePolling {
    readonly state: ActivePollingState;
    /** A poll now, for a refresh the user asked for; the cadence restarts from it, and a pause ends. */
    pollNow(): void;
    /** No poll after this, and no listener left. */
    stop(): void;
}

type Timer = ReturnType<typeof setTimeout>;

/** Past this many failures in a row the wait is the cap anyway; the bound keeps `2 ** n` finite. */
const MAX_DOUBLINGS = 30;

function isFailure(outcome: unknown): boolean {
    return outcome !== null && typeof outcome === 'object' && (outcome as PollOutcome).ok === false;
}

function notBeforeOf(outcome: unknown): number | null {
    if (outcome === null || typeof outcome !== 'object') return null;
    const notBefore = (outcome as PollOutcome).notBefore;
    return typeof notBefore === 'number' && Number.isFinite(notBefore) ? notBefore : null;
}

export function startActivePolling(options: ActivePollingOptions): ActivePolling {
    const tracker = options.tracker ?? getActivityTracker();
    const intervalMs = options.intervalMs;
    const idleMs = options.idleMs ?? LIVE_UPDATES_IDLE_MS;
    const maxBackoffMs = options.maxBackoffMs ?? LIVE_UPDATES_MAX_BACKOFF_MS;

    let state: ActivePollingState | null = null;
    let pollTimer: Timer | null = null;
    let idleTimer: Timer | null = null;
    let inFlight = false;
    let lastStartAt: number | null = null;
    /** Failed polls in a row; the first success sets it back to 0. */
    let failures = 0;
    /** The latest outcome's `notBefore`. */
    let notBefore: number | null = null;
    /** A `pollNow` waits on `pollTimer`: a poll that ends meanwhile leaves the timer alone. */
    let pollNowPending = false;

    function setState(next: ActivePollingState): void {
        if (next === state) return;
        state = next;
        options.onstatechange?.(next);
    }

    function clearTimers(): void {
        if (pollTimer !== null) clearTimeout(pollTimer);
        if (idleTimer !== null) clearTimeout(idleTimer);
        pollTimer = null;
        idleTimer = null;
        pollNowPending = false;
    }

    function schedulePoll(delayMs: number): void {
        if (pollTimer !== null) clearTimeout(pollTimer);
        pollTimer = setTimeout(onPollDue, Math.max(0, delayMs));
    }

    /** From the start of one poll to the next: the interval, doubled at each failure in a row, up to the cap. */
    function waitMs(): number {
        if (failures === 0) return intervalMs;
        const doubled = intervalMs * 2 ** Math.min(failures, MAX_DOUBLINGS);
        return Math.max(intervalMs, Math.min(doubled, maxBackoffMs));
    }

    /** When the next poll is due: after the wait, and never before the latest `notBefore`. A resume polls at once past it. */
    function dueAt(): number {
        const afterWait = lastStartAt === null ? 0 : lastStartAt + waitMs();
        return notBefore === null ? afterWait : Math.max(afterWait, notBefore);
    }

    /**
     * When the next poll starts, as one lands: a wait after its start or, when it lands later than that, the next step
     * of the same cadence — the ticks it outlived were skipped, and landing late buys no extra run — never before
     * `notBefore`.
     */
    function nextAfterLanding(now: number): number {
        const wait = waitMs();
        const start = lastStartAt ?? now;
        let at = start + wait;
        if (at < now && wait > 0) at = start + (Math.floor((now - start) / wait) + 1) * wait;
        return notBefore === null ? at : Math.max(at, notBefore);
    }

    function isIdle(): boolean {
        return idleMs > 0 && Date.now() - tracker.lastActivityAt() >= idleMs;
    }

    /** One timer at the idle threshold: input in between only moves a timestamp, read when the timer fires. */
    function scheduleIdleCheck(): void {
        if (idleMs <= 0) return;
        if (idleTimer !== null) clearTimeout(idleTimer);
        idleTimer = setTimeout(onIdleCheck, Math.max(0, tracker.lastActivityAt() + idleMs - Date.now()));
    }

    function onIdleCheck(): void {
        idleTimer = null;
        if (state !== 'running') return;
        if (isIdle()) pause('paused-idle');
        else scheduleIdleCheck();
    }

    function pause(next: 'paused-idle' | 'paused-hidden'): void {
        clearTimers();
        setState(next);
    }

    function onPollDue(): void {
        pollTimer = null;
        if (state !== 'running') return;
        if (!tracker.isVisible()) return pause('paused-hidden');
        if (isIdle()) return pause('paused-idle');
        schedulePoll(waitMs());
        if (!inFlight) void runOnce();
    }

    async function runOnce(): Promise<void> {
        inFlight = true;
        lastStartAt = Date.now();
        let outcome: unknown = undefined;
        let failed = true;
        try {
            outcome = await options.run();
            failed = isFailure(outcome);
        } catch {
            // A poll that throws is a failure: the next one waits longer.
        } finally {
            inFlight = false;
        }
        failures = failed ? failures + 1 : 0;
        notBefore = notBeforeOf(outcome);
        // The next poll counts from this one's start and outcome. Paused or stopped, nothing is due; a pending
        // `pollNow` runs first and schedules the next one itself.
        if (state === 'running' && !pollNowPending) {
            const now = Date.now();
            schedulePoll(nextAfterLanding(now) - now);
        }
    }

    function resume(): void {
        setState('running');
        scheduleIdleCheck();
        schedulePoll(dueAt() - Date.now());
    }

    function onSignal(signal: ActivitySignal): void {
        if (state === 'stopped') return;
        if (signal === 'hidden') {
            if (state !== 'paused-hidden') pause('paused-hidden');
        } else if (signal === 'visible') {
            if (state !== 'running') resume();
        } else if (state === 'paused-idle') {
            resume();
        }
    }

    const unsubscribe = tracker.subscribe(onSignal);
    if (tracker.isVisible()) {
        tracker.touch();
        setState('running');
        scheduleIdleCheck();
        schedulePoll(options.initialDelayMs ?? 0);
    } else {
        setState('paused-hidden');
    }

    return {
        get state() {
            return state ?? 'stopped';
        },
        pollNow() {
            if (state === 'stopped') return;
            tracker.touch();
            setState('running');
            scheduleIdleCheck();
            // Asked for: no visibility, idle, wait or `notBefore` check for this one; the cadence after it applies them
            // again, from its start and its outcome.
            if (pollTimer !== null) clearTimeout(pollTimer);
            pollNowPending = true;
            pollTimer = setTimeout(() => {
                pollTimer = null;
                pollNowPending = false;
                if (state === 'stopped') return;
                schedulePoll(waitMs());
                if (!inFlight) void runOnce();
            }, 0);
        },
        stop() {
            if (state === 'stopped') return;
            clearTimers();
            unsubscribe();
            setState('stopped');
        },
    };
}
