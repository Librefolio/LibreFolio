/**
 * The room the app header takes, published for whatever sticks under it (81 U38).
 *
 * The header (`Header.svelte`) hides on a scroll down and returns on a scroll up. A box that is `position: sticky` under it
 * (the filter menu of the settings pages) needs to know how far down to stand: the header's height while it shows, 0 while
 * it is hidden. The header publishes both on `:root`, and the CSS of the sticky box reads them:
 *
 *   --lf-header-offset   the height the header occupies right now (its height when shown or pinned, `0px` when hidden)
 *   --lf-header-height   its height always, hidden or not: where a scroll that brings something back must stop, because a
 *                        scroll up shows the header again
 *
 * `HEADER_OFFSET_EVENT` is fired on `window` at every publication, for a reader that works out something from the offset
 * (the stuck state of the phone box) and cannot wait for a scroll.
 */

export const HEADER_OFFSET_VAR = '--lf-header-offset';
export const HEADER_HEIGHT_VAR = '--lf-header-height';
export const HEADER_OFFSET_EVENT = 'lf-header-offset';

/** The gap, in px, between the header and the start of what a scroll brings back (1rem, as the column's own offset). */
export const START_GAP = 16;

/** Publish the header's height and whether it is hidden. Called by the header whenever either changes. */
export function publishHeaderOffset(height: number, hidden: boolean): void {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    const px = Math.max(0, Math.round(height));
    root.style.setProperty(HEADER_HEIGHT_VAR, `${px}px`);
    root.style.setProperty(HEADER_OFFSET_VAR, hidden ? '0px' : `${px}px`);
    window.dispatchEvent(new Event(HEADER_OFFSET_EVENT));
}

/** Take the variables back: there is no header (the page it was on is gone). */
export function clearHeaderOffset(): void {
    if (typeof document === 'undefined') return;
    document.documentElement.style.removeProperty(HEADER_OFFSET_VAR);
    document.documentElement.style.removeProperty(HEADER_HEIGHT_VAR);
    window.dispatchEvent(new Event(HEADER_OFFSET_EVENT));
}

function readPx(name: string): number {
    if (typeof document === 'undefined') return 0;
    const value = Number.parseFloat(document.documentElement.style.getPropertyValue(name));
    return Number.isFinite(value) ? value : 0;
}

/** How far down the header's lower edge stands now: its height while it shows, 0 while it is hidden or absent. */
export function readHeaderOffset(): number {
    return readPx(HEADER_OFFSET_VAR);
}

/** The header's whole height, shown or hidden; 0 without a header. */
export function readHeaderHeight(): number {
    return readPx(HEADER_HEIGHT_VAR);
}

/** Whether the person asked the system for less motion. */
export function prefersReducedMotion(): boolean {
    return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}

/**
 * Bring the start of `anchor` back under the header, when it is above the window; leave the page as it is when it already
 * shows. The stop is the header's WHOLE height plus a gap, even while the header is hidden: the scroll goes up, and a
 * scroll up shows the header again, so a shorter stop would end under it. Smooth, unless the person asked for less motion.
 * A page that cannot scroll is left alone.
 */
export function scrollStartIntoView(anchor: Element | null | undefined, gap = START_GAP): boolean {
    if (!anchor || typeof window === 'undefined') return false;
    const root = document.documentElement;
    if (root.scrollHeight <= window.innerHeight) return false;
    const stop = readHeaderHeight() + gap;
    const top = anchor.getBoundingClientRect().top;
    if (top >= stop) return false;
    window.scrollTo({top: Math.max(0, window.scrollY + top - stop), behavior: prefersReducedMotion() ? 'auto' : 'smooth'});
    return true;
}
