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
 *  - The main pages (Brokers, Transactions, Assets, FX) show their ← only while `canGoBack` is true:
 *    there is a page below the current one, i.e. the user came from an in-app link. A sidebar click
 *    (`resetNavDepth()`) or a direct address (`enter`) leaves one entry, and ← would lead nowhere.
 *  - `beforeNavigate()` in the same layout calls `syncCurrentLocation()`: the page being left may have
 *    changed its URL behind SvelteKit's back (`history.replaceState`), and ← must bring it back as it
 *    was left, with its filters and period.
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
import {writable} from 'svelte/store';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

let stack: string[] = [];

/** `canGoBack` writes here, after every change of the stack. */
const canGoBackState = writable(false);

/** Whether a page is stacked below the current one: the reactive twin of `hasPreviousPage()`. */
export const canGoBack = {subscribe: canGoBackState.subscribe};

function publishCanGoBack() {
    canGoBackState.set(stack.length > 1);
}

/** Whether ← has a page to return to (the user arrived from an in-app link), not just a fallback. */
export function hasPreviousPage(): boolean {
    return stack.length > 1;
}

/**
 * Pathname of a navigation announced as a replacement (`expectReplaceNavigation`): when the next
 * tracked navigation goes there, it takes the place of the top entry instead of stacking on it.
 */
let expectedReplacePathname: string | null = null;

/**
 * Track a navigation event from afterNavigate().
 *
 * @param navigationType - `nav.type` from SvelteKit ('enter', 'link', 'goto', 'form', 'popstate')
 * @param fullUrl - `nav.to?.url.pathname + nav.to?.url.search` from SvelteKit (path + query)
 */
export function trackNavigation(navigationType: string | undefined, fullUrl: string | undefined) {
    if (!fullUrl) return;
    applyNavigation(navigationType, fullUrl);
    publishCanGoBack();
}

function applyNavigation(navigationType: string | undefined, fullUrl: string) {
    // An announced replacement covers the next navigation only, wherever it goes.
    const replacePathname = expectedReplacePathname;
    expectedReplacePathname = null;
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
        if (currentPathname === newPathname || (stack.length > 0 && newPathname === replacePathname)) {
            // Same page, different query params (e.g. filter change via replaceState)
            // → update in place instead of pushing. Likewise an announced replacement
            // (prev/next between assets): Back must skip it, not return to it.
            stack[stack.length - 1] = fullUrl;
        } else {
            stack.push(fullUrl);
        }
    }
}

/**
 * Announce that the next navigation to `url` replaces the current page rather than going deeper —
 * the caller navigates with `goto(url, {replaceState: true})`. Without this the stack would push it,
 * and `goBack()` would return to the page it replaced. Consumed by the next tracked navigation,
 * whatever its destination; `popstate`, `enter` and `resetNavDepth()` drop it too.
 */
export function expectReplaceNavigation(url: string) {
    expectedReplacePathname = url.split('?')[0];
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
        publishCanGoBack();
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
    expectedReplacePathname = null;
    publishCanGoBack();
}

/**
 * Record where the current page really is, just before it is left. A page may change its own URL (period,
 * filters) with a bare `history.replaceState`, which SvelteKit does not report: the top entry would still
 * hold the address the page was entered with, and ← would bring back the page without its period.
 * Only the same page is updated: `fullUrl` must have the pathname of the top entry.
 *
 * @param fullUrl - `window.location.pathname + window.location.search`
 */
export function syncCurrentLocation(fullUrl: string | undefined) {
    if (!fullUrl || stack.length === 0) return;
    const top = stack.length - 1;
    if (stack[top].split('?')[0] === fullUrl.split('?')[0]) stack[top] = fullUrl;
}

registerClientSessionReset('navigationStore', resetNavDepth);
