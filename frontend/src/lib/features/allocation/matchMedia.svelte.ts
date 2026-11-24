/**
 * A media query as a reactive flag: `true` while the viewport matches (`(min-width: 1024px)`).
 *
 * Used where one panel must be mounted in ONE place or the other (a column on a wide screen, a popover on a narrow one), so
 * its `data-testid`s exist once. Call it while a component initialises; the listener goes with the component.
 *
 * @module features/allocation/matchMedia
 */
export function createMediaQuery(query: string, fallback = true): {readonly matches: boolean} {
    let matches = $state(typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(query).matches : fallback);
    $effect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
        const list = window.matchMedia(query);
        const update = () => (matches = list.matches);
        update();
        list.addEventListener('change', update);
        return () => list.removeEventListener('change', update);
    });
    return {
        get matches() {
            return matches;
        },
    };
}
