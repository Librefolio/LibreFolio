/**
 * Navigation history store for smart back-navigation.
 *
 * Tracks SPA navigation depth so that goBack() can use history.back()
 * when there IS previous SPA history, or fall back to a parent path
 * when the user arrived via direct link / bookmark.
 */
import { goto } from '$app/navigation';

let depth = 0;

/**
 * Call this inside afterNavigate() in the app layout.
 * Only counts navigations that are NOT popstate (back/forward) events.
 */
export function trackNavigation(navigationType: string | undefined) {
    if (navigationType === 'popstate') {
        // User pressed back/forward — decrement depth
        depth = Math.max(0, depth - 1);
    } else {
        // link, goto, form, etc. — increment depth
        depth++;
    }
}

/**
 * Navigate back using browser history if available, otherwise goto fallbackPath.
 *
 * @param fallbackPath - The parent route to navigate to if there's no SPA history
 *                       (e.g. '/assets' for asset detail, '/fx' for FX detail)
 */
export function goBack(fallbackPath: string) {
    if (depth > 1) {
        history.back();
    } else {
        goto(fallbackPath);
    }
}

/**
 * Reset navigation depth. Call this when navigating via sidebar (top-level navigation)
 * to avoid stale depth from previous deep-link chains.
 */
export function resetNavDepth() {
    depth = 0;
}

