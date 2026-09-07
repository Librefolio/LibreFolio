/**
 * One ResizeObserver, correctly re-pointed when the element changes.
 *
 * Eight components had their own `setupResizeObserver`, and they were the same
 * three lines each — except for one. `GrowthChart` also checked whether it was
 * already observing *this* element and disconnected first if not:
 *
 * ```ts
 * if (resizeObserver && observedContainer === chartContainer) return;
 * resizeObserver?.disconnect();
 * ```
 *
 * The other seven guarded only on `resizeObserver` being set, so once the
 * container node was replaced — which Svelte does whenever the element is inside
 * a keyed block that re-renders — they kept watching a detached node and stopped
 * resizing altogether. The chart then froze at its old size until the page was
 * reloaded, silently.
 *
 * That guard is now everyone's. What differs between callers is the callback,
 * which each one passes.
 *
 * Most callers only need "something resized, re-measure me" and pass a
 * zero-argument function. One — `LotComparisonChart` — reads the new box out of
 * the `ResizeObserverEntry` itself, to threshold sub-pixel jitter and resize the
 * chart to an explicit size instead of letting ECharts re-measure. So the first
 * entry is forwarded to `onResize`. This is opt-in and costs the other seven
 * nothing: a `() => void` ignores the argument, exactly as before. The `?.`
 * matters — a caller-side ResizeObserver always delivers a non-empty array, but
 * a hand-driven test double may invoke the callback with none.
 */
export interface ResizeWatcher {
    /** Start (or re-point) the observation. Safe to call repeatedly. */
    observe(el: Element | null | undefined): void;
    /** Stop observing and release the observer. */
    disconnect(): void;
}

export function createResizeWatcher(onResize: (entry?: ResizeObserverEntry) => void): ResizeWatcher {
    let observer: ResizeObserver | null = null;
    let observed: Element | null = null;

    return {
        observe(el) {
            if (!el) return;
            if (observer && observed === el) return;
            observer?.disconnect();
            observer = new ResizeObserver((entries) => onResize(entries?.[0]));
            observer.observe(el);
            observed = el;
        },
        disconnect() {
            observer?.disconnect();
            observer = null;
            observed = null;
        },
    };
}
