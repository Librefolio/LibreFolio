/**
 * The watcher of the selection panel (plan 77, SEL-A; the developer's Q-SEL-13 of 19/11/2026): a table's bulk actions sit
 * in the bar at its top, and come down into the dock at its bottom only while that top is out of view — so the same
 * actions are never on screen twice.
 *
 * The top is watched against the element that really scrolls it: a dialog's body, a section that scrolls, or the page
 * (null: the viewport). Without IntersectionObserver the top counts as in view: the actions stay at the top, always
 * reachable.
 */

const SCROLLING = new Set(['auto', 'scroll', 'overlay']);

/** The nearest ancestor of `el` that scrolls vertically, or null when the page itself does. */
export function scrollRootOf(el: Element): Element | null {
    for (let parent = el.parentElement; parent && parent !== document.body && parent !== document.documentElement; parent = parent.parentElement) {
        if (SCROLLING.has(getComputedStyle(parent).overflowY)) return parent;
    }
    return null;
}

/** Report whether `el` is in view of its scroll root, now and at each change; the returned function stops watching. */
export function watchInView(el: Element, onChange: (inView: boolean) => void): () => void {
    if (typeof IntersectionObserver === 'undefined') {
        onChange(true);
        return () => {};
    }
    const observer = new IntersectionObserver(
        (entries) => {
            const entry = entries[entries.length - 1];
            if (entry) onChange(entry.isIntersecting);
        },
        {root: scrollRootOf(el), threshold: 0},
    );
    observer.observe(el);
    return () => observer.disconnect();
}
