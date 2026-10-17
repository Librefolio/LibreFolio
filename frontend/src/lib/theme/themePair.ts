/**
 * A colour for each theme, and the one place that picks between them.
 *
 * Charts draw on a canvas from options built in TypeScript, so a chart colour cannot follow the `dark:` classes the
 * rest of the interface uses: it is a value, chosen for the active theme. Before `lib/theme`, every chart chose with its
 * own `isDark ? '#…' : '#…'`. The tables in this folder now hold the pairs, and {@link themed} does the choosing.
 *
 * The colours that became roles did not come through here: the neutrals of the charts are read from tokens.css at each
 * draw by `chartNeutrals` (`./chartTheme`, B4) through `./roleColors`. What `themed` still picks is what the tables
 * kept — series, categories, states and signs — until the designer gives them roles too.
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
