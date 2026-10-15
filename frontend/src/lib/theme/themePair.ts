/**
 * A colour for each theme, and the one place that picks between them.
 *
 * Charts draw on a canvas from options built in TypeScript, so a chart colour cannot follow the `dark:` classes the
 * rest of the interface uses: it is a value, chosen for the active theme. Before `lib/theme`, every chart chose with its
 * own `isDark ? '#…' : '#…'`. The tables in this folder now hold the pairs, and {@link themed} does the choosing — so
 * the day the colours become theme tokens, this is the function that changes, not the charts.
 *
 * @module lib/theme/themePair
 */

/** The same role in the light and the dark theme. */
export interface ThemePair<T = string> {
    readonly light: T;
    readonly dark: T;
}

/** The member of `pair` for the active theme. */
export function themed<T>(pair: ThemePair<T>, dark: boolean): T {
    return dark ? pair.dark : pair.light;
}
