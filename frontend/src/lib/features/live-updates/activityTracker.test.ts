/**
 * activityTracker — unit tests (Vitest, node, fake clock).
 *
 * The tracker is the page's answer to "is anybody there?" for the live-price pause (Z1, F26, decision 31): it hears
 * the five input events on the window, the visibility changes on the document, and tells its subscribers. Here the
 * window and the document are plain `EventTarget`s and `now` is `Date.now` under fake timers, so every assertion is
 * exact and nothing depends on a browser.
 *
 * Two contract points are checked structurally rather than inferred from silence:
 *   - the listeners exist from creation (counted with `getEventListeners`, which also sees listeners registered
 *     with an `AbortSignal`);
 *   - `dispose()` leaves none behind on either target. "No signal after dispose" alone would also hold for a
 *     tracker that kept its listeners and ignored them — which is a leak, since one tracker serves the whole page.
 */
import {getEventListeners} from 'node:events';
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {ACTIVITY_EVENTS, createActivityTracker} from './activityTracker';
import type {ActivitySignal, ActivityTracker} from './activityTracker';

/** Any fixed instant: every time below is relative to it. */
const T0 = new Date('2026-03-02T09:00:00Z').getTime();

/** Decision 31: pointer, keyboard, wheel and touch — and nothing else. */
const INPUT_EVENTS = ['pointermove', 'pointerdown', 'keydown', 'wheel', 'touchstart'];

/** Events a page fires all the time that say nothing about a person being there (or that duplicate an input event). */
const OTHER_EVENTS = ['scroll', 'resize', 'focus', 'blur', 'click', 'mousemove', 'keyup'];

interface TestEnv {
    target: EventTarget;
    document: EventTarget & {visibilityState: string};
    now: () => number;
}

function environment(visibilityState = 'visible'): TestEnv {
    return {target: new EventTarget(), document: Object.assign(new EventTarget(), {visibilityState}), now: () => Date.now()};
}

/** A tracker on `env`, with one subscriber recording every signal it receives. */
function track(env: TestEnv): {tracker: ActivityTracker; signals: ActivitySignal[]} {
    const tracker = createActivityTracker(env);
    const signals: ActivitySignal[] = [];
    tracker.subscribe((signal) => signals.push(signal));
    return {tracker, signals};
}

/** What a browser does when the tab changes visibility: the property first, then the event on the document. */
function setVisibility(env: TestEnv, state: 'hidden' | 'visible'): void {
    env.document.visibilityState = state;
    env.document.dispatchEvent(new Event('visibilitychange'));
}

/** Every listener the tracker could have left on either target, for the event types it is meant to hear. */
function domListeners(env: TestEnv): number {
    return [...INPUT_EVENTS, 'visibilitychange'].reduce((sum, type) => sum + getEventListeners(env.target, type).length + getEventListeners(env.document, type).length, 0);
}

describe('activityTracker', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(T0);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('hears exactly the five input events of decision 31', () => {
        expect([...ACTIVITY_EVENTS].sort()).toEqual([...INPUT_EVENTS].sort());
    });

    it('starts its last activity at creation and listens from creation, before anyone subscribes', () => {
        const env = environment();
        const tracker = createActivityTracker(env);

        for (const type of INPUT_EVENTS) expect(getEventListeners(env.target, type).length, `a ${type} listener on the target`).toBeGreaterThan(0);
        expect(getEventListeners(env.document, 'visibilitychange').length, 'a visibilitychange listener on the document').toBeGreaterThan(0);

        vi.advanceTimersByTime(5_000);
        expect(tracker.lastActivityAt()).toBe(T0);
    });

    it.each(INPUT_EVENTS)('marks activity now on %s and signals it', (type) => {
        const env = environment();
        const {tracker, signals} = track(env);

        vi.advanceTimersByTime(10_000);
        env.target.dispatchEvent(new Event(type));

        expect(tracker.lastActivityAt()).toBe(T0 + 10_000);
        expect(signals).toEqual(['activity']);
    });

    it.each(OTHER_EVENTS)('ignores %s', (type) => {
        const env = environment();
        const {tracker, signals} = track(env);

        vi.advanceTimersByTime(10_000);
        env.target.dispatchEvent(new Event(type));
        env.document.dispatchEvent(new Event(type));

        expect(tracker.lastActivityAt()).toBe(T0);
        expect(signals).toEqual([]);
    });

    it('signals hidden when the tab goes to the background, without counting it as activity', () => {
        const env = environment();
        const {tracker, signals} = track(env);
        expect(tracker.isVisible()).toBe(true);

        vi.advanceTimersByTime(10_000);
        setVisibility(env, 'hidden');

        expect(signals).toEqual(['hidden']);
        expect(tracker.isVisible()).toBe(false);
        expect(tracker.lastActivityAt()).toBe(T0);
    });

    it('counts the return to the tab as activity and signals visible', () => {
        const env = environment('hidden');
        const {tracker, signals} = track(env);
        expect(tracker.isVisible()).toBe(false);

        vi.advanceTimersByTime(10_000);
        setVisibility(env, 'visible');

        expect(signals).toEqual(['visible']);
        expect(tracker.isVisible()).toBe(true);
        expect(tracker.lastActivityAt()).toBe(T0 + 10_000);
    });

    it('marks activity now on touch()', () => {
        const {tracker} = track(environment());

        vi.advanceTimersByTime(7_000);
        tracker.touch();

        expect(tracker.lastActivityAt()).toBe(T0 + 7_000);
    });

    it('delivers every signal to every subscriber until it unsubscribes', () => {
        const env = environment();
        const tracker = createActivityTracker(env);
        const first: ActivitySignal[] = [];
        const second: ActivitySignal[] = [];
        const unsubscribeFirst = tracker.subscribe((signal) => first.push(signal));
        tracker.subscribe((signal) => second.push(signal));

        env.target.dispatchEvent(new Event('pointerdown'));
        unsubscribeFirst();
        env.target.dispatchEvent(new Event('keydown'));
        setVisibility(env, 'hidden');

        expect(first).toEqual(['activity']);
        expect(second).toEqual(['activity', 'activity', 'hidden']);
    });

    it('removes every DOM listener on dispose: no signal afterwards, last activity frozen', () => {
        const env = environment();
        const {tracker, signals} = track(env);
        expect(domListeners(env)).toBeGreaterThan(0);

        tracker.dispose();
        expect(domListeners(env)).toBe(0);

        vi.advanceTimersByTime(10_000);
        for (const type of INPUT_EVENTS) env.target.dispatchEvent(new Event(type));
        setVisibility(env, 'hidden');
        setVisibility(env, 'visible');

        expect(signals).toEqual([]);
        expect(tracker.lastActivityAt()).toBe(T0);
    });
});
