/**
 * The roles the chart series, states and signs of `chartTheme.ts` stand on (DV-10, C2, D-T28 of 21/10/2026).
 *
 * A series used to be a hand-written pair of hex values. It is now the nearest role of tokens.css, so a series follows
 * the palette the designer tunes, in both themes. The tables of `chartTheme.ts` keep their names and their shape
 * (`{light, dark}` pairs, plain strings), because the charts read them as such; what changed is where the value comes
 * from.
 *
 * - **Static, with a parity gate.** A pair is a value taken when the module loads, so a role is held here as tokens.css
 *   resolves it, per theme (`SERIES_ROLE_VALUES`, the same job as the stand-ins of `roleColors.ts`).
 *   `seriesRoles.test.ts` keeps every row equal to tokens.css: its red says to update the row. The live read of a role,
 *   on the chart's own element, stays `chartRoles` (`./roleColors`), used for the neutrals; moving the series to it
 *   needs the chart components to build their options with it, and is outside this table's reach.
 * - **A plain string, the same in both themes,** is a getter that reads the active theme at each access
 *   ({@link roleNow}): a chart that draws after a theme switch reads the new theme's colour, and its callers, which take
 *   a `string`, did not change. The getter also calls `trackTheme` (`./themeTick.svelte`), so a `$derived`, an `$effect` or
 *   a template that reads it runs again on a theme switch. A caller that copies the string once (a module constant, a
 *   prop fallback Svelte caches) keeps the theme it read: `seriesRoles.test.ts` lists those.
 * - **The mapping is the nearest role, «da rivedere» with the designer (D-T27, D-T28).** A role whose meaning differs
 *   from the series' (a state used as a series, a category used as a hue) is named in `chartTheme.ts` where it is used.
 *
 * @module lib/theme/seriesRoles
 */

import {toRgba} from './colorAlpha';
import {isDarkTheme} from './themeMode';
import {themed, type ThemePair} from './themePair';
import {trackTheme} from './themeTick.svelte';

/** The roles the series stand on, each with its value in both themes: tokens.css, resolved. Kept equal by the parity gate. */
export const SERIES_ROLE_VALUES = {
    '--lf-focus': {light: '#236b4d', dark: '#429e79'},
    '--lf-checked': {light: '#236b4d', dark: '#429e79'},
    '--lf-gain': {light: '#18794e', dark: '#5ed69a'},
    '--lf-loss': {light: '#c82838', dark: '#ff7a86'},
    '--lf-info': {light: '#155eef', dark: '#3f86fa'},
    '--lf-info-on-soft': {light: '#1e40af', dark: '#93c5fd'},
    '--lf-warning': {light: '#ae4e00', dark: '#f59e0b'},
    '--lf-cat-crypto': {light: '#b87916', dark: '#e8bd69'},
    '--lf-cat-commodity': {light: '#b85e45', dark: '#e99a82'},
    '--lf-cat-stock': {light: '#7041c6', dark: '#b69af0'},
    '--lf-cat-liquidity': {light: '#3f628c', dark: '#639bc0'},
    '--lf-cat-other': {light: '#727b87', dark: '#a9b0bb'},
    '--lf-cat-hold': {light: '#5d687b', dark: '#c6d0e0'},
    '--lf-cat-hold-on-soft': {light: '#5c677a', dark: '#c6d0e0'},
    '--lf-border-input': {light: '#7e8984', dark: '#606f6a'},
    '--lf-text-primary': {light: '#1c2420', dark: '#edf2f0'},
    '--lf-text-secondary': {light: '#4a5550', dark: '#9ba8a2'},
    '--lf-text-muted': {light: '#616d67', dark: '#7f8c87'},
    '--lf-action': {light: '#1b4334', dark: '#215240'},
    '--lf-on-overlay': {light: '#ffffff', dark: '#ffffff'},
    '--lf-surface-overlay': {light: 'rgba(13,17,16,0.6)', dark: 'rgba(13,17,16,0.6)'},
} as const satisfies Record<string, ThemePair>;

/** A role a series can stand on. */
export type SeriesRole = keyof typeof SERIES_ROLE_VALUES;

/** The role in each theme: its light value in `light`, its dark value in `dark`. */
export function rolePair(role: SeriesRole): ThemePair {
    const values = SERIES_ROLE_VALUES[role];
    return {light: values.light, dark: values.dark};
}

/**
 * Two roles in one pair: the light theme's from one, the dark theme's from the other. For a series that needs a fill dark
 * enough for white text in both themes, which no single role gives (the status badges, the tile with no P&L).
 */
export function rolePairSplit(light: SeriesRole, dark: SeriesRole): ThemePair {
    return {light: SERIES_ROLE_VALUES[light].light, dark: SERIES_ROLE_VALUES[dark].dark};
}

/** The role in each theme at the given opacities (0–1): a band, a halo, a glow. */
export function rolePairAlpha(role: SeriesRole, light: number, dark: number = light): ThemePair {
    const values = SERIES_ROLE_VALUES[role];
    return {light: toRgba(values.light, light), dark: toRgba(values.dark, dark)};
}

/**
 * Whether the active theme is dark; the light theme where there is no page (unit tests, server rendering). It reads
 * {@link trackTheme} first, so a `$derived`, an `$effect` or a template that reads a getter follows a theme switch.
 */
function activeDark(): boolean {
    if (typeof document === 'undefined') return false;
    trackTheme();
    return isDarkTheme();
}

/** The member of `pair` for the active theme, read now: what a getter of a «same in both themes» string returns. */
export function pairNow(pair: ThemePair): string {
    return themed(pair, activeDark());
}

/** The colour of `role` in the active theme, read now. */
export function roleNow(role: SeriesRole): string {
    return pairNow(rolePair(role));
}

/** The colour of `role` in the active theme at `alpha` (0–1), read now. */
export function roleNowAlpha(role: SeriesRole, alpha: number): string {
    return toRgba(roleNow(role), alpha);
}
