/**
 * A live update that runs only while someone is using the page: one helper for every poll of the app (F26, decision 31).
 *
 * It runs `run` every `intervalMs`, and pauses while the tab is hidden and after `idleMs` without input (two minutes by
 * default). It resumes by itself as soon as the tab is visible again or the user moves the mouse: if a whole interval
 * has passed since the last poll it polls at once, otherwise when the next one was due. A paused poll sends nothing, so
 * a tab left open stops costing requests to the server and to the price providers, and a cloud instance can sleep.
 *
 * Every poll starts from a timer, never inside the call that starts or nudges the poller: a page creates the poller in
 * an `$effect`, and the synchronous head of a poll would subscribe that effect to everything it reads. A poll still in
 * flight when the next is due makes that tick skip; a poll that fails changes nothing, the next one runs on time.
 *
 * Usage:
 *   const poller = startActivePolling({run: refresh, intervalMs: 60_000, onstatechange: (s) => (state = s)});
 *   poller.pollNow(); // a refresh the user asked for: the cadence restarts from it
 *   poller.stop();    // in the effect's cleanup
 *
 * @module lib/features/live-updates/activePolling
 */

import {getActivityTracker, type ActivitySignal, type ActivityTracker} from './activityTracker';
import {LIVE_UPDATES_IDLE_MS} from './cadence';

export type ActivePollingState = 'running' | 'paused-idle' | 'paused-hidden' | 'stopped';

export interface ActivePollingOptions {
    /** One poll. Its errors are its own business: the cadence goes on. */
    run: () => unknown | Promise<unknown>;
    /** Between the starts of two polls. */
    intervalMs: number;
    /** No input for this long pauses the polls; 0 never pauses for that. Default: two minutes. */
    idleMs?: number;
    /** Delay of the first poll. Default 0: at once, from a timer. */
    initialDelayMs?: number;
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

export function startActivePolling(options: ActivePollingOptions): ActivePolling {
    const tracker = options.tracker ?? getActivityTracker();
    const intervalMs = options.intervalMs;
    const idleMs = options.idleMs ?? LIVE_UPDATES_IDLE_MS;

    let state: ActivePollingState | null = null;
    let pollTimer: Timer | null = null;
    let idleTimer: Timer | null = null;
    let inFlight = false;
    let lastStartAt: number | null = null;

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
    }

    function schedulePoll(delayMs: number): void {
        if (pollTimer !== null) clearTimeout(pollTimer);
        pollTimer = setTimeout(onPollDue, Math.max(0, delayMs));
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
        schedulePoll(intervalMs);
        if (!inFlight) void runOnce();
    }

    async function runOnce(): Promise<void> {
        inFlight = true;
        lastStartAt = Date.now();
        try {
            await options.run();
        } catch {
            // A failed poll changes nothing: the next one runs on time.
        } finally {
            inFlight = false;
        }
    }

    function resume(): void {
        setState('running');
        scheduleIdleCheck();
        const sinceLast = lastStartAt === null ? Infinity : Date.now() - lastStartAt;
        schedulePoll(sinceLast >= intervalMs ? 0 : intervalMs - sinceLast);
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
            // Asked for: no visibility or idle check for this one; the cadence after it applies them again.
            if (pollTimer !== null) clearTimeout(pollTimer);
            pollTimer = setTimeout(() => {
                pollTimer = null;
                if (state === 'stopped') return;
                schedulePoll(intervalMs);
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
