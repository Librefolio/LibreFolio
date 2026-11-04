/**
 * The page's theme mode, as components read it (plan 55, workstream R, W8 — developer's decision D4), and the signal
 * that the chart colours changed without it (contract C4 with the Designer Lab, DV).
 *
 * The theme is the `dark` class of `<html>`, which the theme store writes. Charts read it when they draw and redraw
 * when it changes. These helpers are the only place that knows how; the helpers of `themePair.ts` pick the value.
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

/** The event that tells the charts their colours changed while the theme did not (contract C4 with the Designer Lab). */
const CHART_COLORS_EVENT = 'lf:chart-colors-change';

/**
 * Calls `onChange` each time the chart colours change without a theme switch: the Designer Lab sends it at every edit
 * and when it loads a state (contract C4). A chart that hears it rebuilds its whole option, never a data-only update:
 * the category colours (`categoryColor`) and the roles read through `roleColor` are read again.
 *
 * Returns a handle: `disconnect()` it when the component goes away.
 */
export function onChartColorsChange(onChange: () => void): {disconnect: () => void} {
    const listener = () => onChange();
    document.addEventListener(CHART_COLORS_EVENT, listener);
    return {disconnect: () => document.removeEventListener(CHART_COLORS_EVENT, listener)};
}

/** Tells every chart on the page that its colours changed (see {@link onChartColorsChange}). */
export function notifyChartColorsChange(): void {
    document.dispatchEvent(new Event(CHART_COLORS_EVENT));
}
