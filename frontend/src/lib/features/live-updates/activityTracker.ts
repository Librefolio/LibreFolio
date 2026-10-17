/**
 * Whether someone is using the page: the time of the last input, and whether the tab is visible.
 *
 * One tracker per page (`getActivityTracker()`), shared by every live update: it listens once to input on `window` and
 * to `visibilitychange` on `document`. Returning to the tab counts as input. The pollers subscribe to its signals to
 * pause and resume (`activePolling.ts`).
 *
 * An input event only stores a timestamp — `pointermove` fires many times a second — and is passed on only while
 * someone subscribed. Scroll is not input here: the app scrolls the page itself (guides, `scrollIntoView`), and the
 * wheel or a touch already tells a user's scroll.
 *
 * @module lib/features/live-updates/activityTracker
 */

export type ActivitySignal = 'activity' | 'visible' | 'hidden';

/** The events that count as someone using the page. */
export const ACTIVITY_EVENTS = ['pointermove', 'pointerdown', 'keydown', 'wheel', 'touchstart'] as const;

export interface ActivityEnvironment {
    /** Receives the input events: `window` in the app. */
    target: Pick<EventTarget, 'addEventListener' | 'removeEventListener'>;
    /** Receives `visibilitychange` and tells the visibility of the tab: `document` in the app. */
    document: Pick<EventTarget, 'addEventListener' | 'removeEventListener'> & {readonly visibilityState: string};
    /** Milliseconds: `Date.now` in the app. */
    now: () => number;
}

export interface ActivityTracker {
    /** When the last input arrived — or the tracker was created, or the tab became visible again. */
    lastActivityAt(): number;
    /** Whether the tab is visible. */
    isVisible(): boolean;
    /** Counts as input now: a page that starts to poll follows a user's navigation. */
    touch(): void;
    /** Hears the signals; returns the function that stops hearing them. */
    subscribe(listener: (signal: ActivitySignal) => void): () => void;
    /** Removes every listener it added to the page; afterwards it hears nothing. */
    dispose(): void;
}

const LISTENER_OPTIONS: AddEventListenerOptions = {capture: true, passive: true};

export function createActivityTracker(env: ActivityEnvironment): ActivityTracker {
    let lastActivity = env.now();
    let disposed = false;
    const listeners = new Set<(signal: ActivitySignal) => void>();

    function emit(signal: ActivitySignal): void {
        for (const listener of [...listeners]) listener(signal);
    }

    function onInput(): void {
        lastActivity = env.now();
        if (listeners.size > 0) emit('activity');
    }

    function onVisibilityChange(): void {
        if (env.document.visibilityState === 'hidden') {
            emit('hidden');
            return;
        }
        lastActivity = env.now();
        emit('visible');
    }

    for (const type of ACTIVITY_EVENTS) env.target.addEventListener(type, onInput, LISTENER_OPTIONS);
    env.document.addEventListener('visibilitychange', onVisibilityChange);

    return {
        lastActivityAt: () => lastActivity,
        isVisible: () => env.document.visibilityState !== 'hidden',
        touch() {
            if (!disposed) lastActivity = env.now();
        },
        subscribe(listener) {
            if (disposed) return () => {};
            listeners.add(listener);
            return () => {
                listeners.delete(listener);
            };
        },
        dispose() {
            if (disposed) return;
            disposed = true;
            for (const type of ACTIVITY_EVENTS) env.target.removeEventListener(type, onInput, LISTENER_OPTIONS);
            env.document.removeEventListener('visibilitychange', onVisibilityChange);
            listeners.clear();
        },
    };
}

let pageTracker: ActivityTracker | null = null;

/** The tracker of this page, created on first use. Browser only. */
export function getActivityTracker(): ActivityTracker {
    pageTracker ??= createActivityTracker({target: window, document, now: () => Date.now()});
    return pageTracker;
}
