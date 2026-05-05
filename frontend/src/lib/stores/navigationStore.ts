/**
 * Navigation history store for smart back-navigation.
 *
 * Maintains an explicit stack of visited paths so that goBack() can navigate
 * deterministically to the previous page (independent of browser history
 * which can be corrupted by replaceState calls elsewhere).
 *
 * Contract:
 *  - afterNavigate() in `(app)/+layout.svelte` calls `trackNavigation(nav.type, pathname)`
 *    on every navigation (enter, link, goto, form, popstate).
 *  - Sidebar top-level buttons call `resetNavDepth()` on click to clear stale
 *    deep-link chains (the user wants to jump to a root section).
 *  - Detail pages call `goBack(fallbackPath)` from the back button.
 *
 * Why an explicit stack (and not just history.back()):
 *  - Various pages use `history.replaceState(...)` to sync URL query params
 *    (date range, filters, etc.). Those do NOT create a new browser history
 *    entry, but they DO change window.location.pathname+search. Relying on
 *    history.back() in that context is non-deterministic.
 *  - `goto(..., {replaceState:true})` similarly replaces the top entry.
 *  - A navigated-by-us stack guarantees the previous logical page regardless
 *    of how many replaceState calls happened in between.
 */
import {goto} from '$app/navigation';

let stack: string[] = [];

/**
 * Track a navigation event from afterNavigate().
 *
 * @param navigationType - `nav.type` from SvelteKit ('enter', 'link', 'goto', 'form', 'popstate')
 * @param fullUrl - `nav.to?.url.pathname + nav.to?.url.search` from SvelteKit (path + query)
 */
export function trackNavigation(navigationType: string | undefined, fullUrl: string | undefined) {
    if (!fullUrl) return;

    if (navigationType === 'popstate') {
        // User pressed back/forward. Pop the top entry if it matches where
        // we were; otherwise trust the browser and re-anchor the stack.
        stack.pop();
        // Edge case: if pop emptied the stack but we're actually at a known
        // location, seed it so subsequent goBack() has a floor.
        if (stack.length === 0) stack = [fullUrl];
    } else if (navigationType === 'enter') {
        // First navigation (page load / refresh) — stack starts fresh.
        stack = [fullUrl];
    } else {
        // link / goto / form — push (avoid duplicate consecutive entries,
        // which would happen when goto replaces URL query params via
        // replaceState of the same pathname).
        // Compare pathnames only to avoid duplicate pushes from replaceState
        // query param updates on the same page.
        const currentPathname = stack.length > 0 ? stack[stack.length - 1].split('?')[0] : '';
        const newPathname = fullUrl.split('?')[0];
        if (currentPathname === newPathname) {
            // Same page, different query params (e.g. filter change via replaceState)
            // → update in place instead of pushing.
            stack[stack.length - 1] = fullUrl;
        } else {
            stack.push(fullUrl);
        }
    }
}

/**
 * Navigate back to the previous page in our explicit stack.
 * Falls back to fallbackPath if the stack is empty (direct link / bookmark).
 *
 * @param fallbackPath - e.g. '/assets' for asset detail, '/fx' for FX detail.
 */
export function goBack(fallbackPath: string) {
    if (stack.length > 1) {
        // Remove current page, goto the previous one explicitly.
        stack.pop();
        const prev = stack[stack.length - 1];
        // Use goto (push) rather than history.back() for determinism. A new
        // history entry is cheap; browser Back still works because SvelteKit
        // maintains the real history underneath.
        goto(prev);
    } else {
        goto(fallbackPath);
    }
}

/**
 * Reset the stack. Called from sidebar top-level buttons so that deep-link
 * chains accumulated in a previous section don't leak into the next one.
 */
export function resetNavDepth() {
    stack = [];
}

/**
 * Debug helper — snapshot of the current stack.
 * Remove or expose via `window.__navStack` only in dev builds.
 */
export function _debugStack(): string[] {
    return [...stack];
}
