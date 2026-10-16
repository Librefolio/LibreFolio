/**
 * activePolling — unit tests (Vitest, node, fake timers).
 *
 * `startActivePolling` is the cadence the Assets pages use to ask for live prices (Z1, F26, decision 31): one run
 * every `intervalMs` while somebody is there, paused after `idleMs` without input or while the tab is hidden, resumed
 * by the next input or by the return to the tab. Every rule of the contract is driven here on a clock the test owns,
 * through a tracker the test owns: `fakeTracker` behaves like the real one (an input, or the return to the tab, marks
 * activity *now*, then signals it), so a red in this file is about the cadence and nothing else.
 *
 * Conventions that run through the file:
 *   - time is moved with the *async* advance only. A run returns a promise, and the poller learns that the run is
 *     over in a promise callback; the async advance lets those callbacks run between two timers, exactly as a
 *     browser does. With the synchronous advance a finished run would still look in flight at the next tick.
 *   - every run starts from a timer — at start, on resume and on `pollNow()` alike — never inside the call that
 *     asked for it: each "at once" is asserted as "not yet" right after the call, and "now" after advancing 0 ms.
 *   - tests that are not about idleness pass `LONG_IDLE_MS`, so the pause for inactivity cannot interfere with them,
 *     and none of them depends on `idleMs: 0` (rule 11 has its own test).
 *
 * Contract rules → tests: 1 `start`, 2 `cadence`, 3 `no overlap`, 4 `idleness`, 5 `hidden tab`, 6 `resume`,
 * 7 `pollNow`, 8 `stop`, 9 `errors`, 10 `onstatechange`, 11 `idleMs 0`; the numbers of decision 31 in `cadence.ts`.
 *
 * Z7c (decision 34, D-Z7-1, D-Z7-2): a run may hand back an outcome, `{ok?, notBefore?}`. A run that throws, rejects or
 * answers `ok: false` is a failure, anything else a success. After k failures in a row the next run waits
 * `max(intervalMs, min(intervalMs × 2^k, maxBackoffMs))` — the cap defaults to `LIVE_UPDATES_MAX_BACKOFF_MS`, ten
 * minutes — and the first success restores `intervalMs`. The next run starts at `lastStart + wait`, never before the
 * finite `notBefore` of the latest outcome; a run that lands later than `lastStart + wait` is followed at the first
 * later step `lastStart + n × wait` (landing late buys no extra run, as Z1's `no overlap` says). A resume starts at
 * once when `max(lastStart + wait, notBefore)` has passed, else at that time, with no rounding to a step. `pollNow()`
 * ignores both the wait and `notBefore`, and its outcome counts like any other. A `pollNow()` while a run is in flight
 * starts nothing and restarts the cadence from the click only until that run lands: then rule 5 applies, from that
 * run's start and outcome.
 * Z1's `errors` (rule 9) asserted that a failed run changes nothing: it is rewritten to the doubled wait. Every other
 * Z1 case is unchanged, and they are Z7c's rule 8 — what Z7c leaves as it was.
 *
 * Z7c rules → tests: 1 `the outcome of a run`, 2 `backoff`, 3 `notBefore`, 4 `reset`, 5 `late landing`,
 * 6 `resume after a pause`, 7 `pollNow during a backoff`, 5 and 7 together `pollNow while a run is in flight`, 8 the Z1
 * cases, 9 `stop with a run in flight` and the landings during a pause in `resume after a pause`; the cap in
 * `cadence.ts`.
 * These tests read the start of every run off the fake clock (`scriptedRun`), so a red prints the whole sequence of
 * starts — the gaps a wrong backoff produced — rather than a count. The cap is written out (`CAP_MS`): the spec pins the
 * number that was decided, and the constant of `cadence.ts` is checked against it once.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {startActivePolling} from './activePolling';
import type {ActivePolling, ActivePollingOptions, ActivePollingState, PollOutcome} from './activePolling';
import type {ActivitySignal, ActivityTracker} from './activityTracker';
import {ASSET_DETAIL_LIVE_INTERVAL_MS, ASSET_LIST_LIVE_INTERVAL_MS, LIVE_UPDATES_IDLE_MS, LIVE_UPDATES_MAX_BACKOFF_MS} from './cadence';

/** Any fixed instant: every time below is an offset from it. */
const T0 = new Date('2026-03-02T09:00:00Z').getTime();

/** Keeps the pause for inactivity out of the tests that are not about it. */
const LONG_IDLE_MS = 60 * 60_000;

interface FakeTracker {
    /** What the poller sees. `touch` is a spy: the poller marks activity when it starts and on `pollNow()`. */
    tracker: ActivityTracker & {touch: Mock<() => void>};
    /** A user input (pointer, keyboard…): marks activity now, then signals it — what the real tracker does. */
    input(): void;
    /** The tab goes to the background. */
    hide(): void;
    /** The tab comes back: it counts as activity, then it is signalled. */
    show(): void;
}

function fakeTracker(options: {visible?: boolean} = {}): FakeTracker {
    let lastActivity = Date.now();
    let visible = options.visible ?? true;
    const listeners = new Set<(signal: ActivitySignal) => void>();
    const emit = (signal: ActivitySignal): void => {
        for (const listener of [...listeners]) listener(signal);
    };
    const tracker = {
        lastActivityAt: () => lastActivity,
        isVisible: () => visible,
        touch: vi.fn(() => {
            lastActivity = Date.now();
        }),
        subscribe(listener: (signal: ActivitySignal) => void) {
            listeners.add(listener);
            return () => {
                listeners.delete(listener);
            };
        },
        dispose() {
            listeners.clear();
        },
    };
    return {
        tracker,
        input() {
            lastActivity = Date.now();
            emit('activity');
        },
        hide() {
            visible = false;
            emit('hidden');
        },
        show() {
            visible = true;
            lastActivity = Date.now();
            emit('visible');
        },
    };
}

/** A `run` whose every call stays in flight until the test settles it. */
function deferredRun() {
    const calls: Array<{resolve: () => void; reject: (reason: unknown) => void}> = [];
    let inFlight = 0;
    let maxInFlight = 0;
    const run = vi.fn(
        () =>
            new Promise<void>((resolve, reject) => {
                inFlight += 1;
                maxInFlight = Math.max(maxInFlight, inFlight);
                calls.push({
                    resolve: () => {
                        inFlight -= 1;
                        resolve();
                    },
                    reject: (reason) => {
                        inFlight -= 1;
                        reject(reason);
                    },
                });
            }),
    );
    return {run, calls, maxInFlight: () => maxInFlight};
}

/** Every state the poller reports, in order. */
function stateLog() {
    const states: ActivePollingState[] = [];
    return {states, onstatechange: (state: ActivePollingState) => void states.push(state)};
}

const pollers: ActivePolling[] = [];

function start(options: ActivePollingOptions): ActivePolling {
    const poller = startActivePolling(options);
    pollers.push(poller);
    return poller;
}

async function advance(ms: number): Promise<void> {
    await vi.advanceTimersByTimeAsync(ms);
}

/** Move the clock to `T0 + offsetMs`. */
async function advanceTo(offsetMs: number): Promise<void> {
    const now = Date.now();
    expect(T0 + offsetMs, 'the test only moves time forward').toBeGreaterThanOrEqual(now);
    await vi.advanceTimersByTimeAsync(T0 + offsetMs - now);
}

const throwing = (): never => {
    throw new Error('the provider is down');
};
const rejecting = (): Promise<never> => Promise.reject(new Error('the provider is down'));

// ── Z7c helpers ──────────────────────────────────────────────────────────────────────────────────────────────────────

/** D-Z7-1, written out: the longest wait that failures in a row can put between two runs. */
const CAP_MS = 600_000;

/** What one call of `run` hands back to the poller: a value, or a promise of one. */
type RunAnswer = ReturnType<ActivePollingOptions['run']>;

/** Hands `outcome` back at once, as a plain value. */
function answer(outcome?: PollOutcome): () => RunAnswer {
    return () => outcome;
}

/** Hands `outcome` back through a promise that is already settled. */
function answerAsync(outcome?: PollOutcome): () => RunAnswer {
    return () => Promise.resolve(outcome);
}

/** Hands back a value the type does not admit: `run` may be untyped code, and the poller must still read it (rule 1). */
function answerLoose(value: unknown): () => RunAnswer {
    return () => value as RunAnswer;
}

/** A success with nothing to say, as every run of Z1. */
const SUCCEEDED = answer();
/** A failure the run reports itself. */
const FAILED = answer({ok: false});

/**
 * A `run` that answers its calls in order — call n gets `answers[n]`, the last answer repeats — and stamps the start of
 * every call in ms after T0. The clock is the fake one: a stamp is the instant the poller invoked the run.
 */
function scriptedRun(...answers: Array<() => RunAnswer>) {
    const startedAt: number[] = [];
    const run = vi.fn((): RunAnswer => {
        const call = startedAt.length;
        startedAt.push(Date.now() - T0);
        return answers[Math.min(call, answers.length - 1)]();
    });
    return {run, startedAt};
}

/** One call that stays in flight until the test lands it — with an outcome, or with nothing — or fails it. */
function held() {
    let settle: {resolve: (outcome?: PollOutcome) => void; reject: (reason: unknown) => void} | null = null;
    const started = () => {
        if (!settle) throw new Error('the held call has not started yet');
        return settle;
    };
    return {
        answer: (): RunAnswer =>
            new Promise<PollOutcome | void>((resolve, reject) => {
                settle = {resolve, reject};
            }),
        land(outcome?: PollOutcome) {
            started().resolve(outcome);
        },
        fail() {
            started().reject(new Error('the provider is down'));
        },
    };
}

/** The gaps between consecutive starts. */
function gapsOf(startedAt: number[]): number[] {
    return startedAt.slice(1).map((at, index) => at - startedAt[index]);
}

/** The starts of a first run at 0 followed by these gaps. */
function startsAfter(gaps: number[]): number[] {
    return gaps.reduce((starts, gap) => [...starts, starts[starts.length - 1] + gap], [0]);
}

beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0);
});

afterEach(() => {
    for (const poller of pollers.splice(0)) poller.stop();
    vi.useRealTimers();
});

describe('cadence.ts (decision 31)', () => {
    it('holds the three numbers the developer decided', () => {
        expect(LIVE_UPDATES_IDLE_MS).toBe(120_000);
        expect(ASSET_LIST_LIVE_INTERVAL_MS).toBe(60_000);
        expect(ASSET_DETAIL_LIVE_INTERVAL_MS).toBe(30_000);
    });
});

describe('cadence.ts — the cap of the backoff (Z7c, D-Z7-1)', () => {
    it('caps the wait after failures at ten minutes', () => {
        expect(LIVE_UPDATES_MAX_BACKOFF_MS).toBe(CAP_MS);
        expect(CAP_MS).toBe(600_000);
    });
});

describe('start (rule 1)', () => {
    it('starts running, marks activity, and runs first from a timer — never inside the call', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        expect(poller.state).toBe('running');
        expect(tracker.touch).toHaveBeenCalled();
        expect(run).not.toHaveBeenCalled();

        await advance(0);
        expect(run).toHaveBeenCalledTimes(1);
    });

    it('waits initialDelayMs for the first run, then keeps the cadence from it', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, initialDelayMs: 5_000, tracker});

        await advanceTo(4_999);
        expect(run).not.toHaveBeenCalled();
        await advanceTo(5_000);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(34_999);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(35_000);
        expect(run).toHaveBeenCalledTimes(2);
    });

    it('counts the idle time from the start, not from an input long gone', async () => {
        const {tracker} = fakeTracker();
        await advanceTo(10 * 60_000); // ten quiet minutes before the page opens
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker});

        await advance(0);
        expect(run).toHaveBeenCalledTimes(1);
        expect(poller.state).toBe('running');
    });

    it('starts paused in a hidden tab and runs nothing until the tab is visible', async () => {
        const fake = fakeTracker({visible: false});
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        expect(poller.state).toBe('paused-hidden');
        await advanceTo(5 * 60_000);
        expect(run).not.toHaveBeenCalled();
        expect(poller.state).toBe('paused-hidden');

        fake.show();
        expect(run).not.toHaveBeenCalled();
        await advance(0);
        expect(run).toHaveBeenCalledTimes(1);
        expect(poller.state).toBe('running');
    });
});

describe('cadence (rule 2)', () => {
    it('starts a run every intervalMs, measured from the start of the previous run', async () => {
        const {tracker} = fakeTracker();
        const {run, calls} = deferredRun();
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        // The first run lasts ten seconds: the next one is still due 30 s after the first one *started*.
        await advanceTo(10_000);
        calls[0].resolve();
        await advanceTo(29_999);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(30_000);
        expect(run).toHaveBeenCalledTimes(2);

        calls[1].resolve();
        await advanceTo(59_999);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(60_000);
        expect(run).toHaveBeenCalledTimes(3);
    });
});

describe('no overlap (rule 3)', () => {
    it('skips a tick while a run is in flight, keeps the cadence, and runs nothing extra when the run lands', async () => {
        const {tracker} = fakeTracker();
        const {run, calls, maxInFlight} = deferredRun();
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(65_000); // the ticks at 30 s and 60 s found the first run still in flight
        expect(run).toHaveBeenCalledTimes(1);

        calls[0].resolve();
        await advance(0);
        expect(run).toHaveBeenCalledTimes(1); // landing late buys no extra run
        await advanceTo(89_999);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(90_000); // the cadence went on: 30, 60, 90
        expect(run).toHaveBeenCalledTimes(2);
        expect(maxInFlight()).toBe(1);
    });
});

describe('idleness (rule 4)', () => {
    it('runs at 0, 30, 60 and 90 s and pauses at 120 s when no input arrives', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker, onstatechange: log.onstatechange});

        for (const [at, runs] of [
            [0, 1],
            [30_000, 2],
            [60_000, 3],
            [90_000, 4],
        ] as const) {
            await advanceTo(at);
            expect(run, `runs by ${at / 1000} s`).toHaveBeenCalledTimes(runs);
        }
        await advanceTo(119_999);
        expect(poller.state).toBe('running');

        await advanceTo(120_000);
        expect(run).toHaveBeenCalledTimes(4);
        expect(poller.state).toBe('paused-idle');
        expect(log.states.at(-1)).toBe('paused-idle');

        await advanceTo(30 * 60_000);
        expect(run).toHaveBeenCalledTimes(4);
        expect(poller.state).toBe('paused-idle');
    });

    it('turns paused-idle at the threshold itself, even between two ticks', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 45_000, idleMs: 120_000, tracker});

        await advanceTo(90_000);
        expect(run).toHaveBeenCalledTimes(3); // 0, 45 and 90 s
        await advanceTo(119_999);
        expect(poller.state).toBe('running');
        await advanceTo(120_000);
        expect(poller.state).toBe('paused-idle');
        await advanceTo(135_000); // the tick due at 135 s does not start
        expect(run).toHaveBeenCalledTimes(3);
    });

    it('lets an input before the threshold postpone the pause', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(100_000);
        expect(run).toHaveBeenCalledTimes(4); // 0, 30, 60 and 90 s
        fake.input(); // the threshold moves to 220 s
        await advance(0);
        expect(run).toHaveBeenCalledTimes(4); // an input while running asks for nothing by itself

        await advanceTo(210_000);
        expect(run).toHaveBeenCalledTimes(8); // 120, 150, 180 and 210 s
        await advanceTo(219_999);
        expect(poller.state).toBe('running');
        await advanceTo(220_000);
        expect(poller.state).toBe('paused-idle');
        await advanceTo(300_000);
        expect(run).toHaveBeenCalledTimes(8);
    });

    it('defaults idleMs to LIVE_UPDATES_IDLE_MS', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, tracker});

        await advanceTo(LIVE_UPDATES_IDLE_MS - 1);
        expect(poller.state).toBe('running');
        await advanceTo(LIVE_UPDATES_IDLE_MS);
        expect(poller.state).toBe('paused-idle');
        expect(run).toHaveBeenCalledTimes(LIVE_UPDATES_IDLE_MS / 30_000);
    });
});

describe('hidden tab (rule 5)', () => {
    it('pauses at once, runs nothing while hidden, and lets the run in flight land without starting another', async () => {
        const fake = fakeTracker();
        const {run, calls} = deferredRun();
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(10_000);
        fake.hide();
        expect(poller.state).toBe('paused-hidden');

        await advanceTo(20_000);
        calls[0].resolve(); // the answer in flight comes back while the tab is hidden
        await advanceTo(5 * 60_000);
        expect(run).toHaveBeenCalledTimes(1);
        // Two minutes without input went by in the background: the state still names the reason that came first.
        expect(poller.state).toBe('paused-hidden');
        expect(log.states).toEqual(['running', 'paused-hidden']);
    });
});

describe('resume (rule 6)', () => {
    it('resumes on input while paused-idle, with one run at once when an interval has passed', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(200_000);
        expect(poller.state).toBe('paused-idle');
        expect(run).toHaveBeenCalledTimes(4);

        fake.input();
        expect(run).toHaveBeenCalledTimes(4); // from a timer, not inside the input
        await advance(0);
        expect(run).toHaveBeenCalledTimes(5);
        expect(poller.state).toBe('running');

        // The cadence goes on from that run.
        await advanceTo(229_999);
        expect(run).toHaveBeenCalledTimes(5);
        await advanceTo(230_000);
        expect(run).toHaveBeenCalledTimes(6);
    });

    it('resumes on input while paused-idle, but waits for the interval when the last run is recent', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 60_000, idleMs: 100_000, tracker: fake.tracker});

        await advanceTo(100_000);
        expect(run).toHaveBeenCalledTimes(2); // 0 and 60 s
        expect(poller.state).toBe('paused-idle');

        await advanceTo(110_000);
        fake.input();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(run).toHaveBeenCalledTimes(2); // only 50 s since the last run started
        await advanceTo(119_999);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(120_000);
        expect(run).toHaveBeenCalledTimes(3);
    });

    it('resumes when the tab is visible again, with one run at once when an interval has passed', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(5_000);
        expect(run).toHaveBeenCalledTimes(1);
        fake.hide();
        await advanceTo(300_000);
        expect(run).toHaveBeenCalledTimes(1);

        fake.show();
        expect(run).toHaveBeenCalledTimes(1); // from a timer, not inside the signal
        await advance(0);
        expect(run).toHaveBeenCalledTimes(2);
        expect(poller.state).toBe('running');

        await advanceTo(329_999);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(330_000);
        expect(run).toHaveBeenCalledTimes(3);
    });

    it('resumes when the tab is visible again, but not before an interval from the last run', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(20_000);
        fake.show();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(run).toHaveBeenCalledTimes(1);

        await advanceTo(29_999);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(30_000);
        expect(run).toHaveBeenCalledTimes(2);
    });
});

describe('pollNow (rule 7)', () => {
    it('runs once from a 0 ms timer and restarts the cadence from that run', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        expect(run).toHaveBeenCalledTimes(1);
        poller.pollNow();
        expect(run).toHaveBeenCalledTimes(1); // not inside the call
        await advance(0);
        expect(run).toHaveBeenCalledTimes(2);

        await advanceTo(39_999); // the old schedule (30 s) is gone
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(40_000);
        expect(run).toHaveBeenCalledTimes(3);
    });

    it('marks activity: the pause for inactivity is counted from it', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker});

        await advanceTo(100_000);
        const touches = tracker.touch.mock.calls.length;
        poller.pollNow();
        await advance(0);
        expect(tracker.touch.mock.calls.length).toBeGreaterThan(touches);

        await advanceTo(219_999);
        expect(poller.state).toBe('running');
        expect(run).toHaveBeenCalledTimes(8); // 0, 30, 60, 90; 100 (pollNow), 130, 160, 190
        await advanceTo(220_000);
        expect(poller.state).toBe('paused-idle');
        expect(run).toHaveBeenCalledTimes(8);
    });

    it('starts no second run while one is in flight', async () => {
        const {tracker} = fakeTracker();
        const {run, calls, maxInFlight} = deferredRun();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        expect(run).toHaveBeenCalledTimes(1);
        poller.pollNow();
        await advance(0);
        expect(run).toHaveBeenCalledTimes(1);

        // Whatever the poller does once the run lands, two runs are never in flight together.
        calls[0].resolve();
        await advance(0);
        expect(maxInFlight()).toBe(1);
    });

    it('resumes a poller paused for inactivity', async () => {
        const {tracker} = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker});

        await advanceTo(200_000);
        expect(poller.state).toBe('paused-idle');
        poller.pollNow();
        expect(run).toHaveBeenCalledTimes(4);
        await advance(0);
        expect(run).toHaveBeenCalledTimes(5);
        expect(poller.state).toBe('running');
    });
});

describe('stop (rule 8)', () => {
    it('stops for good: no run, no reaction to the tracker or to pollNow, and a second stop is harmless', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        poller.stop();
        expect(poller.state).toBe('stopped');

        await advanceTo(10 * 60_000);
        fake.input();
        fake.hide();
        fake.show();
        poller.pollNow();
        await advanceTo(20 * 60_000);
        expect(run).toHaveBeenCalledTimes(1);
        expect(poller.state).toBe('stopped');

        expect(() => poller.stop()).not.toThrow();
        expect(poller.state).toBe('stopped');
        expect(log.states).toEqual(['running', 'stopped']);
    });

    it.each(['resolves', 'rejects'] as const)('changes nothing when a run in flight %s after stop', async (outcome) => {
        const fake = fakeTracker();
        const {run, calls} = deferredRun();
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        poller.stop();
        if (outcome === 'resolves') calls[0].resolve();
        else calls[0].reject(new Error('the answer came back after stop'));
        await advanceTo(5 * 60_000);

        expect(run).toHaveBeenCalledTimes(1);
        expect(poller.state).toBe('stopped');
        expect(log.states).toEqual(['running', 'stopped']);
    });
});

describe('errors (rule 9)', () => {
    // Rewritten for Z7c: Z1 asserted that a failed run changes nothing (runs at 0, 30 and 60 s). A run that throws or
    // rejects is now a failure (Z7c rule 1), and failures in a row double the wait (Z7c rule 2). The state still says
    // nothing of it.
    it.each([
        ['throws', throwing],
        ['rejects', rejecting],
    ] as const)('counts a run that %s as a failure: the next waits twice the interval, then four times, and the state stays running', async (_outcome, failure) => {
        const {tracker} = fakeTracker();
        const run = vi.fn(failure);
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(59_999); // Z1 ran again at 30 s
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(60_000);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(179_999);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(180_000);
        expect(run).toHaveBeenCalledTimes(3);
        expect(poller.state).toBe('running');
        expect(log.states).toEqual(['running']);
    });
});

describe('onstatechange (rule 10)', () => {
    it('reports the initial state once at start, then every change once', async () => {
        const fake = fakeTracker();
        const log = stateLog();
        const poller = start({run: vi.fn(), intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker, onstatechange: log.onstatechange});
        expect(log.states).toEqual(['running']);

        await advanceTo(5_000);
        fake.input(); // already running: nothing to report
        fake.hide();
        fake.hide(); // the same state twice is reported once
        await advanceTo(10_000);
        fake.show();
        fake.show();
        await advance(0);
        await advanceTo(130_000); // two minutes after the return to the tab
        fake.input();
        await advance(0);
        poller.stop();
        poller.stop();

        expect(log.states).toEqual(['running', 'paused-hidden', 'running', 'paused-idle', 'running', 'stopped']);
    });

    it('reports paused-hidden as the initial state in a hidden tab', () => {
        const fake = fakeTracker({visible: false});
        const log = stateLog();
        start({run: vi.fn(), intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker, onstatechange: log.onstatechange});

        expect(log.states).toEqual(['paused-hidden']);
    });
});

describe('idleMs 0 (rule 11)', () => {
    it('never pauses for inactivity, but still pauses in a hidden tab', async () => {
        const fake = fakeTracker();
        const run = vi.fn();
        const poller = start({run, intervalMs: 30_000, idleMs: 0, tracker: fake.tracker});

        await advanceTo(10 * 60_000);
        expect(poller.state).toBe('running');
        expect(run).toHaveBeenCalledTimes(21); // 0, 30 s, …, 600 s

        fake.hide();
        expect(poller.state).toBe('paused-hidden');
        await advanceTo(20 * 60_000);
        expect(run).toHaveBeenCalledTimes(21);
    });
});

// =====================================================================================================================
// Z7c — the outcome of a run, the backoff, notBefore, late landings
// =====================================================================================================================

describe('the outcome of a run (Z7c rule 1)', () => {
    it.each<[string, () => RunAnswer]>([
        ['throws', () => throwing()],
        ['rejects', () => rejecting()],
        ['returns {ok: false}', answer({ok: false})],
        ['resolves {ok: false}', answerAsync({ok: false})],
    ])('a run that %s is a failure: the next run waits twice the interval', async (_label, failure) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(failure, SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(59_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(60_000);
        expect(startedAt).toEqual([0, 60_000]);
    });

    it.each<[string, () => RunAnswer]>([
        ['returns nothing', answer()],
        ['resolves nothing', answerAsync()],
        ['returns {}', answer({})],
        ['returns {ok: true}', answer({ok: true})],
        ['resolves {ok: true}', answerAsync({ok: true})],
        ['returns {ok: undefined}', answer({ok: undefined})],
        ['returns null', answerLoose(null)],
        ['returns a number', answerLoose(42)],
        ['returns a string', answerLoose('done')],
        ['returns false — a value, not {ok: false}', answerLoose(false)],
    ])('a run that %s is a success: the next run comes one interval later', async (_label, success) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(success);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(29_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(60_000);
        expect(startedAt).toEqual([0, 30_000, 60_000]);
    });
});

describe('backoff (Z7c rule 2)', () => {
    it.each([
        {page: 'the asset list', intervalMs: ASSET_LIST_LIVE_INTERVAL_MS, gaps: [60_000, 120_000, 240_000, 480_000, 600_000, 600_000]},
        {page: 'one asset', intervalMs: ASSET_DETAIL_LIVE_INTERVAL_MS, gaps: [30_000, 60_000, 120_000, 240_000, 480_000, 600_000, 600_000]},
    ])('$page: after a success, failures in a row double the wait up to the ten-minute cap, which then holds', async ({intervalMs, gaps}) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(SUCCEEDED, FAILED);
        start({run, intervalMs, idleMs: LONG_IDLE_MS, tracker});

        const starts = startsAfter(gaps);
        const last = starts[starts.length - 1];
        await advanceTo(last + CAP_MS - 1);
        expect(gapsOf(startedAt)).toEqual(gaps);
        await advanceTo(last + CAP_MS);
        expect(gapsOf(startedAt)).toEqual([...gaps, CAP_MS]);
    });

    it('takes maxBackoffMs as the cap when it is given', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        start({run, intervalMs: 1_000, maxBackoffMs: 5_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(20_999); // runs at 0, 2, 6, 11 and 16 s
        expect(gapsOf(startedAt)).toEqual([2_000, 4_000, 5_000, 5_000]);
        await advanceTo(21_000);
        expect(gapsOf(startedAt)).toEqual([2_000, 4_000, 5_000, 5_000, 5_000]);
    });

    it.each([
        {label: '5 s over a 4 s cap', intervalMs: 5_000, maxBackoffMs: 4_000},
        {label: '15 minutes over the default cap', intervalMs: 15 * 60_000, maxBackoffMs: undefined},
    ])('never shortens an interval longer than the cap: $label', async ({intervalMs, maxBackoffMs}) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        start({run, intervalMs, ...(maxBackoffMs === undefined ? {} : {maxBackoffMs}), idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(4 * intervalMs - 1);
        expect(gapsOf(startedAt)).toEqual([intervalMs, intervalMs, intervalMs]);
    });

    it('holds the cap through sixty failures in a row and one more: every wait finite, none shorter, none longer', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 1_000, maxBackoffMs: 8_000, idleMs: LONG_IDLE_MS, tracker});

        // The waits after failures 1 … 60: 2 s, 4 s, then the cap. 2^60 overflows no double, but a shift (1 << k) wraps
        // from k = 31, and a timer delay past 2^31 − 1 ms, or NaN, fires at once.
        const waits = [2_000, 4_000, ...Array<number>(58).fill(8_000)];
        const starts = startsAfter(waits);
        const last = starts[starts.length - 1];
        await advanceTo(last + 8_000 - 1);
        expect(gapsOf(startedAt)).toEqual(waits);
        await advanceTo(last + 8_000);
        expect(gapsOf(startedAt)).toEqual([...waits, 8_000]);
        expect(poller.state).toBe('running');
    });
});

describe('reset (Z7c rule 4)', () => {
    it('restores the interval at the first success, counted from its start, and doubles again from there', async () => {
        const {tracker} = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(FAILED, FAILED, FAILED, slow.answer, FAILED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(420_000); // three failures: 60, 120 and 240 s apart
        expect(startedAt).toEqual([0, 60_000, 180_000, 420_000]);
        await advanceTo(425_000);
        slow.land(); // a success that took 5 s
        await advanceTo(449_999);
        expect(startedAt).toEqual([0, 60_000, 180_000, 420_000]);
        await advanceTo(450_000); // 30 s after it started — not after it landed (455 s)
        expect(startedAt).toEqual([0, 60_000, 180_000, 420_000, 450_000]);
        await advanceTo(509_999);
        expect(startedAt).toEqual([0, 60_000, 180_000, 420_000, 450_000]);
        await advanceTo(510_000); // a failure again: twice the interval, the count started over
        expect(startedAt).toEqual([0, 60_000, 180_000, 420_000, 450_000, 510_000]);
    });
});

describe('notBefore (Z7c rule 3)', () => {
    it('is a minimum: a notBefore after the next run holds it back, and the interval runs again from the run it held', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 100_000}), SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(99_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(100_000);
        expect(startedAt).toEqual([0, 100_000]);
        await advanceTo(130_000);
        expect(startedAt).toEqual([0, 100_000, 130_000]);
    });

    it.each<[string, number]>([
        ['in the past', T0 - 5_000],
        ['before the next run', T0 + 10_000],
        ['at the next run', T0 + 30_000],
    ])('changes nothing when it falls %s', async (_when, notBefore) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore}), SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(29_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(30_000);
        expect(startedAt).toEqual([0, 30_000]);
    });

    it('has no cap: a notBefore twenty minutes ahead holds the next run twenty minutes', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 2 * CAP_MS}), SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(2 * CAP_MS - 1);
        expect(startedAt).toEqual([0]);
        await advanceTo(2 * CAP_MS);
        expect(startedAt).toEqual([0, 2 * CAP_MS]);
    });

    it.each<[string, number, number]>([
        ['after the doubled wait', T0 + 300_000, 300_000],
        ['before the doubled wait', T0 + 45_000, 60_000],
    ])('holds a failure too: a notBefore %s', async (_when, notBefore, next) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: false, notBefore}), SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(next - 1);
        expect(startedAt).toEqual([0]);
        await advanceTo(next);
        expect(startedAt).toEqual([0, next]);
    });

    it.each<[string, PollOutcome, number]>([
        ['NaN, on a success', {ok: true, notBefore: Number.NaN}, 30_000],
        ['Infinity, on a success', {ok: true, notBefore: Number.POSITIVE_INFINITY}, 30_000],
        ['-Infinity, on a success', {ok: true, notBefore: Number.NEGATIVE_INFINITY}, 30_000],
        ['Infinity, on a failure', {ok: false, notBefore: Number.POSITIVE_INFINITY}, 60_000],
    ])('ignores a notBefore that is not finite: %s', async (_label, outcome, next) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer(outcome), SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(next - 1);
        expect(startedAt).toEqual([0]);
        await advanceTo(next);
        expect(startedAt).toEqual([0, next]);
    });

    it.each<[string, () => RunAnswer, number]>([
        ['a success without one', SUCCEEDED, 40_000],
        ['a success with one that is not finite', answer({ok: true, notBefore: Number.NaN}), 40_000],
        ['a success with an earlier one', answer({ok: true, notBefore: T0 + 50_000}), 50_000],
        ['a failure without one', FAILED, 70_000],
    ])('follows the latest outcome only: %s replaces an earlier notBefore', async (_label, latest, next) => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 300_000}), latest, SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        poller.pollNow(); // asked for: notBefore does not hold it (rule 7), and its outcome becomes the latest
        await advance(0);
        expect(startedAt).toEqual([0, 10_000]);
        await advanceTo(next - 1); // the notBefore of the first run (300 s) no longer holds anything
        expect(startedAt).toEqual([0, 10_000]);
        await advanceTo(next);
        expect(startedAt).toEqual([0, 10_000, next]);
    });
});

describe('late landing (Z7c rule 5)', () => {
    it.each<[string, (slow: ReturnType<typeof held>) => void]>([
        ['fails', (slow) => slow.fail()],
        ['answers {ok: false}', (slow) => slow.land({ok: false})],
    ])('a run started at 0 that %s when it lands at 65 s: the wait is 60 s, its steps 60 and 120 s, the next run at 120 s', async (_label, failIt) => {
        const {tracker} = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(65_000); // the ticks at 30 and 60 s found it in flight
        expect(startedAt).toEqual([0]);
        failIt(slow);
        await advance(0);
        expect(startedAt).toEqual([0]); // landing late buys no run
        await advanceTo(119_999); // and the steps count from its start: not 65 + 60 s, not the old 90 s
        expect(startedAt).toEqual([0]);
        await advanceTo(120_000);
        expect(startedAt).toEqual([0, 120_000]);
        await advanceTo(150_000); // that one succeeds: the interval is back
        expect(startedAt).toEqual([0, 120_000, 150_000]);
    });

    it('a run that succeeds 130 s after its start, after two failures: the wait is back to 30 s, the next run 150 s after its start', async () => {
        const {tracker} = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(FAILED, FAILED, slow.answer, SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(180_000); // two failures, 60 then 120 s apart: this run starts at 180 s
        expect(startedAt).toEqual([0, 60_000, 180_000]);
        await advanceTo(310_000); // 130 s after its start; the tick due at 300 s found it in flight
        expect(startedAt).toEqual([0, 60_000, 180_000]);
        slow.land();
        await advance(0);
        expect(startedAt).toEqual([0, 60_000, 180_000]);
        await advanceTo(329_999); // steps of 30 s from 180 s: … 300, 330 — not 420 (the old wait), not 340 (landing + 30)
        expect(startedAt).toEqual([0, 60_000, 180_000]);
        await advanceTo(330_000);
        expect(startedAt).toEqual([0, 60_000, 180_000, 330_000]);
    });

    it.each<[string, PollOutcome, number]>([
        ['after the step', {ok: true, notBefore: T0 + 100_000}, 100_000],
        ['before the step', {ok: true, notBefore: T0 + 70_000}, 90_000],
        ['already past when it lands', {ok: true, notBefore: T0 + 40_000}, 90_000],
        ['after the step of a failure', {ok: false, notBefore: T0 + 130_000}, 130_000],
    ])('never before notBefore: a run started at 0 that lands at 65 s with a notBefore %s', async (_label, outcome, next) => {
        const {tracker} = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, SUCCEEDED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(65_000);
        slow.land(outcome);
        await advance(0);
        expect(startedAt).toEqual([0]);
        await advanceTo(next - 1);
        expect(startedAt).toEqual([0]);
        await advanceTo(next);
        expect(startedAt).toEqual([0, next]);
    });
});

describe('resume after a pause (Z7c rule 6)', () => {
    it('a tab shown again before the doubled wait is over: nothing at once, the next run when the wait ends', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(30_000);
        fake.show(); // a whole interval since the run started: Z1 ran at once here
        await advance(0);
        expect(poller.state).toBe('running');
        expect(startedAt).toEqual([0]);
        await advanceTo(59_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(60_000);
        expect(startedAt).toEqual([0, 60_000]);
    });

    it('a tab shown again after the doubled wait: one run at once, from a timer, and the backoff goes on from it', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(90_000);
        fake.show();
        expect(startedAt).toEqual([0]); // not inside the signal
        await advance(0);
        expect(startedAt).toEqual([0, 90_000]);
        await advanceTo(209_999); // the second failure in a row: 120 s
        expect(startedAt).toEqual([0, 90_000]);
        await advanceTo(210_000);
        expect(startedAt).toEqual([0, 90_000, 210_000]);
    });

    it('a tab shown again before notBefore: the next run at notBefore', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 200_000}), SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(100_000);
        fake.show();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(startedAt).toEqual([0]);
        await advanceTo(199_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(200_000);
        expect(startedAt).toEqual([0, 200_000]);
    });

    it('input after the idle pause, before the doubled wait is over: nothing at once, the next run when the wait ends', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(120_000); // two failures, 60 s apart: the next is due at 180 s, and nobody is there
        expect(startedAt).toEqual([0, 60_000]);
        expect(poller.state).toBe('paused-idle');
        await advanceTo(150_000);
        fake.input();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(startedAt).toEqual([0, 60_000]);
        await advanceTo(179_999);
        expect(startedAt).toEqual([0, 60_000]);
        await advanceTo(180_000);
        expect(startedAt).toEqual([0, 60_000, 180_000]);
    });

    it('input after the idle pause, past the doubled wait: one run at once, from a timer', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(200_000);
        expect(poller.state).toBe('paused-idle');
        expect(startedAt).toEqual([0, 60_000]);
        fake.input();
        expect(startedAt).toEqual([0, 60_000]); // not inside the input
        await advance(0);
        expect(startedAt).toEqual([0, 60_000, 200_000]);
    });

    it('input after the idle pause, before notBefore: the next run at notBefore', async () => {
        const fake = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 200_000}), SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(120_000);
        expect(poller.state).toBe('paused-idle');
        await advanceTo(150_000);
        fake.input();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(startedAt).toEqual([0]);
        await advanceTo(199_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(200_000);
        expect(startedAt).toEqual([0, 200_000]);
    });

    it('a run that fails while the tab is hidden schedules nothing; shown again before its doubled wait is over, the next run when the wait ends', async () => {
        const fake = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, FAILED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(20_000);
        slow.fail(); // lands while hidden
        await advanceTo(40_000);
        fake.show();
        await advance(0);
        expect(startedAt).toEqual([0]);
        await advanceTo(59_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(60_000);
        expect(startedAt).toEqual([0, 60_000]);
    });

    it('a run that fails while the tab is hidden schedules nothing; shown again after its doubled wait, one run at once — no rounding to a step', async () => {
        const fake = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, FAILED);
        start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker});

        await advanceTo(10_000);
        fake.hide();
        await advanceTo(20_000);
        slow.fail(); // lands while hidden
        await advanceTo(70_000);
        expect(startedAt).toEqual([0]); // nothing while hidden, not at 60 s either
        fake.show();
        expect(startedAt).toEqual([0]); // not inside the signal
        await advance(0);
        expect(startedAt).toEqual([0, 70_000]); // a step of the 60 s wait would have said 120 s
    });

    it('a run that lands during the idle pause schedules nothing; input before its notBefore waits for it', async () => {
        const fake = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: 120_000, tracker: fake.tracker});

        await advanceTo(120_000);
        expect(poller.state).toBe('paused-idle'); // with the run still in flight
        await advanceTo(150_000);
        slow.land({ok: false, notBefore: T0 + 400_000});
        await advanceTo(300_000);
        expect(startedAt).toEqual([0]); // nothing during the pause
        fake.input();
        await advance(0);
        expect(poller.state).toBe('running');
        expect(startedAt).toEqual([0]);
        await advanceTo(399_999);
        expect(startedAt).toEqual([0]);
        await advanceTo(400_000);
        expect(startedAt).toEqual([0, 400_000]);
    });
});

describe('pollNow during a backoff (Z7c rule 7)', () => {
    it('ignores the doubled wait: one run at once, from a timer', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000); // the failure at 0 put the next run at 60 s
        poller.pollNow();
        expect(startedAt).toEqual([0]); // not inside the call
        await advance(0);
        expect(startedAt).toEqual([0, 10_000]);
    });

    it('ignores notBefore: one run at once, from a timer', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(answer({ok: true, notBefore: T0 + 300_000}), SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        poller.pollNow();
        expect(startedAt).toEqual([0]); // not inside the call
        await advance(0);
        expect(startedAt).toEqual([0, 10_000]);
    });

    it('counts a failed pollNow: the next run waits four times the interval, from it', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        poller.pollNow();
        await advance(0);
        expect(startedAt).toEqual([0, 10_000]);
        await advanceTo(129_999); // the second failure in a row, counted from the run asked for: 10 + 120 s
        expect(startedAt).toEqual([0, 10_000]);
        await advanceTo(130_000);
        expect(startedAt).toEqual([0, 10_000, 130_000]);
    });

    it('ends the backoff with a successful pollNow: the next run one interval after it', async () => {
        const {tracker} = fakeTracker();
        const {run, startedAt} = scriptedRun(FAILED, FAILED, SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(100_000); // two failures, 60 s apart: the next was due at 180 s
        expect(startedAt).toEqual([0, 60_000]);
        poller.pollNow();
        await advance(0);
        expect(startedAt).toEqual([0, 60_000, 100_000]);
        await advanceTo(129_999);
        expect(startedAt).toEqual([0, 60_000, 100_000]);
        await advanceTo(160_000);
        expect(startedAt).toEqual([0, 60_000, 100_000, 130_000, 160_000]);
    });
});

describe('pollNow while a run is in flight (Z7c rules 5 and 7)', () => {
    // The click starts no second run (Z1, unchanged), and restarts the cadence from itself only while the run is in
    // flight. When the run lands, rule 5 applies from that run's start and outcome: the click's restart is replaced.
    it.each<{label: string; landsAt: number; land: (slow: ReturnType<typeof held>) => void; next: number}>([
        {label: 'lands OK at 15 s: the next at 30 s, from its start — not at 40 s, from the click', landsAt: 15_000, land: (slow) => slow.land(), next: 30_000},
        {label: 'lands with a failure at 15 s: its outcome counts, the wait is 60 s, the next at 60 s', landsAt: 15_000, land: (slow) => slow.fail(), next: 60_000},
        {label: 'lands OK at 45 s: the next at 60 s, the first step of its start after the landing — not at 70 s, a step of the click', landsAt: 45_000, land: (slow) => slow.land(), next: 60_000},
        {label: 'lands OK at 15 s with a notBefore at 50 s: the next at 50 s', landsAt: 15_000, land: (slow) => slow.land({ok: true, notBefore: T0 + 50_000}), next: 50_000},
    ])('a click at 10 s on a run started at 0 starts nothing; the run $label', async ({landsAt, land, next}) => {
        const {tracker} = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, SUCCEEDED);
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker});

        await advanceTo(10_000);
        poller.pollNow();
        await advance(0);
        expect(startedAt).toEqual([0]); // no second run while one is in flight
        await advanceTo(landsAt);
        land(slow);
        await advance(0);
        expect(startedAt).toEqual([0]);
        await advanceTo(next - 1);
        expect(startedAt).toEqual([0]);
        await advanceTo(next);
        expect(startedAt).toEqual([0, next]);
    });
});

describe('stop with a run in flight (Z7c rule 9)', () => {
    it.each<[string, PollOutcome]>([
        ['a failure', {ok: false}],
        ['a notBefore', {ok: true, notBefore: T0 + 10_000}],
        ['a failure with a notBefore', {ok: false, notBefore: T0 + 10_000}],
    ])('schedules nothing when the run lands after stop with %s', async (_label, outcome) => {
        const fake = fakeTracker();
        const slow = held();
        const {run, startedAt} = scriptedRun(slow.answer, SUCCEEDED);
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker: fake.tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        poller.stop();
        slow.land(outcome);
        await advanceTo(10 * 60_000);
        fake.input();
        fake.hide();
        fake.show();
        await advanceTo(20 * 60_000);
        expect(startedAt).toEqual([0]);
        expect(poller.state).toBe('stopped');
        expect(log.states).toEqual(['running', 'stopped']);
    });
});
