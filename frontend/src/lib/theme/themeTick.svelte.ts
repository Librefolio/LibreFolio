/**
 * A reactive read that depends on the theme class of `<html>` (DV-10, C2).
 *
 * The strings of `chartTheme.ts` that are the same in both themes (`RISK_OVERLAY_COLORS.simulation`, `SIGNAL_COLORS.*`…)
 * are getters of the active theme's role. A caller that read a constant once never noticed a theme switch; a caller that
 * reads the getter inside a `$derived`, an `$effect` or a template now does: {@link trackTheme} is called first by the
 * getter, so Svelte records the dependency and runs the reader again when the class changes.
 *
 * It is Svelte's `createSubscriber` over `onThemeClassChange` (`./themeMode`), the one place that observes the theme: the
 * observer starts when a reactive context first reads and is disconnected when the last one stops. Outside a reactive
 * context, and outside a browser, it does nothing.
 *
 * @module lib/theme/themeTick
 */

import {createSubscriber} from 'svelte/reactivity';

import {onThemeClassChange} from './themeMode';

const subscribe = createSubscriber((update) => {
    const observer = onThemeClassChange(update);
    return () => observer.disconnect();
});

/** Makes the reactive context that calls it depend on the theme class; a no-op anywhere else. */
export function trackTheme(): void {
    if (typeof document !== 'undefined') subscribe();
}
