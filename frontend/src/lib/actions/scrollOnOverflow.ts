/**
 * Auto-scrolling "marquee" behavior for single-line text that overflows its container —
 * used for asset/broker names across cards, tables, and the asset detail title.
 *
 * Fully automatic, no interaction required: after a short pause, overflowing text slowly
 * scrolls to the end, pauses there, then jumps straight back to the start (no reverse
 * animation — an instant reset, like a teleport) and the cycle repeats — as long as the
 * element stays mounted and overflowing. Non-overflowing text (the vast majority) is
 * completely unaffected — no visual change, no listeners, no animation loop running.
 *
 * Two entry points, same core logic (`attachOverflowMarquee`):
 * - `scrollOnOverflow` — a Svelte action for template usages: `use:scrollOnOverflow`.
 * - `attachOverflowMarqueeToDescendants` — for table components that build cells as raw
 *   HTML strings (`type: 'html'`, e.g. ExposureTable/ContributionTable/AssetTable/
 *   TransactionsTable), where a `use:` action can't attach to dynamically-injected nodes.
 *   Call this once from the table's own `onMount`, pointing at its outer wrapper element;
 *   it watches for cells (marked with the `overflow-scroll-marquee` class, included in
 *   `overflowScrollTextClass`) being added/removed/re-rendered (sorting, pagination, data
 *   refresh, etc.) and attaches/detaches the same marquee behavior automatically.
 */

const START_DELAY_MS = 2000; // pause before the first (and every repeat) scroll starts
const PAUSE_AT_END_MS = 1200; // pause once fully scrolled, before the instant reset
const PIXELS_PER_SECOND = 28; // constant speed — long names take proportionally longer, not faster

/**
 * Attach the automatic marquee behavior to a single element. Safe to call on any element;
 * genuinely does nothing (beyond observing for future overflow) if the element never
 * overflows.
 *
 * @returns a cleanup function — call it when the element is removed/unmounted.
 */
export function attachOverflowMarquee(node: HTMLElement): () => void {
    let resizeObserver: ResizeObserver | null = null;
    let mutationObserver: MutationObserver | null = null;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let rafId: number | null = null;
    let isOverflowing = false;
    let phase: 'idle' | 'waiting' | 'forward' | 'paused-end' = 'idle';
    let lastTimestamp: number | null = null;
    // Full-precision accumulator — NOT re-read from `node.scrollLeft` each frame. Browsers
    // snap `scrollLeft` to integer pixels, so at ~28px/s (≈0.3-0.5px per animation frame) a
    // `node.scrollLeft += delta` approach reads back the same rounded integer every frame and
    // the tiny fractional increment never accumulates — the animation looks frozen. Tracking
    // the true position separately in JS and only writing the rounded pixel value to the DOM
    // avoids that.
    let scrollPosition = 0;

    const prefersReducedMotion = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    function clearTimer() {
        if (timer) {
            clearTimeout(timer);
            timer = null;
        }
    }

    function clearRaf() {
        if (rafId != null) {
            cancelAnimationFrame(rafId);
            rafId = null;
        }
    }

    function stopLoop() {
        clearTimer();
        clearRaf();
        phase = 'idle';
        lastTimestamp = null;
    }

    function scheduleWait() {
        clearTimer();
        clearRaf();
        phase = 'waiting';
        timer = setTimeout(() => {
            phase = 'forward';
            lastTimestamp = null;
            rafId = requestAnimationFrame(step);
        }, START_DELAY_MS);
    }

    function step(timestamp: number) {
        if (!isOverflowing) {
            stopLoop();
            return;
        }
        const maxScroll = node.scrollWidth - node.clientWidth;
        if (lastTimestamp == null) lastTimestamp = timestamp;
        const deltaSeconds = (timestamp - lastTimestamp) / 1000;
        lastTimestamp = timestamp;

        if (phase === 'forward') {
            scrollPosition += PIXELS_PER_SECOND * deltaSeconds;
            if (scrollPosition >= maxScroll) {
                scrollPosition = maxScroll;
                node.scrollLeft = scrollPosition;
                phase = 'paused-end';
                timer = setTimeout(() => {
                    // Instant reset (no reverse animation) — jump straight back to the
                    // start, then wait the normal pause before scrolling forward again.
                    scrollPosition = 0;
                    node.scrollLeft = 0;
                    scheduleWait();
                }, PAUSE_AT_END_MS);
                return;
            }
            node.scrollLeft = scrollPosition;
        }
        rafId = requestAnimationFrame(step);
    }

    function syncOverflowState() {
        const overflowAmount = node.scrollWidth - node.clientWidth;
        const nowOverflowing = overflowAmount > 1; // >1px tolerance for subpixel rounding
        if (nowOverflowing === isOverflowing) return;
        isOverflowing = nowOverflowing;

        if (isOverflowing) {
            node.setAttribute('data-overflowing', 'true');
            if (!prefersReducedMotion) scheduleWait();
        } else {
            node.removeAttribute('data-overflowing');
            stopLoop();
            scrollPosition = 0;
            node.scrollLeft = 0;
        }
    }

    // ResizeObserver catches container/box size changes (responsive layout, sidebar toggle,
    // etc.) but does NOT reliably fire when only the TEXT CONTENT changes while the element's
    // own box stays the same size (e.g. an in-place rename without remount) — MutationObserver
    // covers that gap.
    resizeObserver = new ResizeObserver(syncOverflowState);
    resizeObserver.observe(node);

    mutationObserver = new MutationObserver(syncOverflowState);
    mutationObserver.observe(node, {characterData: true, childList: true, subtree: true});

    syncOverflowState();

    return () => {
        resizeObserver?.disconnect();
        mutationObserver?.disconnect();
        stopLoop();
    };
}

/**
 * Svelte action wrapper for template usages: `<span use:scrollOnOverflow class={overflowScrollTextClass}>{name}</span>`
 */
export function scrollOnOverflow(node: HTMLElement) {
    const dispose = attachOverflowMarquee(node);
    return {destroy: dispose};
}

/** Marker class (included in `overflowScrollTextClass`) identifying elements that should get
 *  the marquee behavior when rendered as raw HTML strings — see `attachOverflowMarqueeToDescendants`. */
export const OVERFLOW_MARQUEE_SELECTOR = '.overflow-scroll-marquee';

/**
 * For table components that build cells as raw HTML strings (`type: 'html'`, e.g.
 * ExposureTable/ContributionTable/AssetTable/TransactionsTable), where a Svelte `use:` action
 * can't attach to dynamically re-rendered/injected nodes. Call once from the table's own
 * `onMount`/`$effect`, pointing at its outer wrapper element (must stay mounted for the
 * lifetime of the table). Watches for matching cells being added/removed (sorting,
 * pagination, filtering, data refresh, etc.) and attaches/detaches the marquee automatically.
 *
 * @returns a cleanup function — call it when the table itself is unmounted.
 */
export function attachOverflowMarqueeToDescendants(container: HTMLElement): () => void {
    const attached = new WeakMap<Element, () => void>();

    function attachAll() {
        const matches = container.querySelectorAll<HTMLElement>(OVERFLOW_MARQUEE_SELECTOR);
        for (const el of matches) {
            if (attached.has(el)) continue;
            attached.set(el, attachOverflowMarquee(el));
        }
    }

    function detach(el: Element) {
        attached.get(el)?.();
        attached.delete(el);
    }

    attachAll();

    // Re-scan whenever the table's DOM subtree changes (new rows rendered, cells replaced on
    // sort/page/filter/refresh) — detach stale entries no longer in the DOM, attach new ones.
    const mutationObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const removed of mutation.removedNodes) {
                if (!(removed instanceof Element)) continue;
                if (removed.matches(OVERFLOW_MARQUEE_SELECTOR)) detach(removed);
                removed.querySelectorAll?.(OVERFLOW_MARQUEE_SELECTOR).forEach(detach);
            }
        }
        attachAll();
    });
    mutationObserver.observe(container, {childList: true, subtree: true});

    return () => {
        mutationObserver.disconnect();
        container.querySelectorAll<HTMLElement>(OVERFLOW_MARQUEE_SELECTOR).forEach(detach);
    };
}
