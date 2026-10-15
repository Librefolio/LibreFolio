/**
 * The page's theme mode, as components read it (plan 55, workstream R, W8 — developer's decision D4).
 *
 * The theme is the `dark` class of `<html>`, which the theme store writes. Charts read it when they draw and redraw
 * when it changes. These two helpers are the only place that knows how; the helpers of `themePair.ts` pick the value.
 */

/** Whether the page shows the dark theme: the `dark` class on `<html>`. */
export function isDarkTheme(): boolean {
    return document.documentElement.classList.contains('dark');
}

/**
 * Calls `onChange` after every change of the `class` attribute of `<html>`, with no arguments. Any class counts, not
 * only `dark`: the charts redraw on every change of it, and keep doing so on purpose (D4).
 *
 * Returns the observer, already observing: `disconnect()` it when the component goes away.
 */
export function onThemeClassChange(onChange: () => void): MutationObserver {
    const observer = new MutationObserver(() => onChange());
    observer.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
    return observer;
}
