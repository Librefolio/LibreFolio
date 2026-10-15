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
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import type {Mock} from 'vitest';
import {startActivePolling} from './activePolling';
import type {ActivePolling, ActivePollingOptions, ActivePollingState} from './activePolling';
import type {ActivitySignal, ActivityTracker} from './activityTracker';
import {ASSET_DETAIL_LIVE_INTERVAL_MS, ASSET_LIST_LIVE_INTERVAL_MS, LIVE_UPDATES_IDLE_MS} from './cadence';

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
    it.each([
        ['throws', throwing],
        ['rejects', rejecting],
    ] as const)('keeps the cadence and the state when a run %s', async (_outcome, failure) => {
        const {tracker} = fakeTracker();
        const run = vi.fn(failure);
        const log = stateLog();
        const poller = start({run, intervalMs: 30_000, idleMs: LONG_IDLE_MS, tracker, onstatechange: log.onstatechange});

        await advanceTo(0);
        expect(run).toHaveBeenCalledTimes(1);
        await advanceTo(30_000);
        expect(run).toHaveBeenCalledTimes(2);
        await advanceTo(60_000);
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
