// @vitest-environment jsdom
//
// The docblock above is load-bearing: the cases read a getter inside a `$derived`, and under the default `node`
// environment there is no `<html>` class to switch (`assertEffectsRun` of `$test/runes.svelte` says when effects are
// off).
/**
 * seriesRoles, reactive reads — a getter of `chartTheme.ts` read inside a `$derived` follows a theme switch (DV-10, C2).
 *
 * The strings that are the same in both themes (`RISK_OVERLAY_COLORS.simulation`, `SIGNAL_COLORS.legendBarPreview.up`…)
 * are getters of the active theme's role. `RiskAnalysisPanel` and `L4Simulation` read them in a `$derived` that depends on
 * nothing else of the theme, `SignalVisualLegend` in a template: without `trackTheme` they would keep the colour of the
 * theme they were built in after a switch with no reload.
 *
 * The `<html>` class is switched the way `applyTheme()` does, and `trackTheme` moves on the observer's microtask, so each
 * case awaits one before it reads.
 *
 * @module lib/theme/seriesRoles.reactive.svelte.test
 */
import {afterEach, describe, expect, it} from 'vitest';
import {flushSync} from 'svelte';

import {CHART_GAIN_LOSS, RISK_OVERLAY_COLORS, SIGNAL_COLORS} from './chartTheme';

const html = document.documentElement;

afterEach(() => {
    html.classList.remove('dark');
});

/** Switches the theme class and waits for the class observer (a microtask) and for Svelte to settle. */
async function switchTheme(dark: boolean): Promise<void> {
    html.classList.toggle('dark', dark);
    await Promise.resolve();
    await new Promise((resolve) => setTimeout(resolve, 0));
    flushSync();
}

describe('a getter read inside a $derived follows the theme with no reload', () => {
    it('RISK_OVERLAY_COLORS, as RiskAnalysisPanel reads it', async () => {
        let color = '';
        const dispose = $effect.root(() => {
            const overlay = $derived({color: RISK_OVERLAY_COLORS.simulation, comparison: RISK_OVERLAY_COLORS.comparisonAsset});
            $effect(() => {
                color = `${overlay.color}|${overlay.comparison}`;
            });
        });
        flushSync();
        expect(color, 'built in the light theme').toBe('#155eef|#ae4e00');

        await switchTheme(true);
        expect(color, 'the dark theme after the switch, with no new overlay built').toBe('#3f86fa|#f59e0b');

        await switchTheme(false);
        expect(color, 'and back').toBe('#155eef|#ae4e00');
        dispose();
    });

    it('SIGNAL_COLORS and the tooltip Δ, as the legend and the lines read them', async () => {
        let seen = '';
        const dispose = $effect.root(() => {
            const colors = $derived([SIGNAL_COLORS.legendBarPreview.up, SIGNAL_COLORS.legendBarPreview.down, SIGNAL_COLORS.roles.accent, CHART_GAIN_LOSS.tooltipDelta.gain]);
            $effect(() => {
                seen = colors.join('|');
            });
        });
        flushSync();
        expect(seen).toBe('#18794e|#c82838|#7041c6|#18794e');

        await switchTheme(true);
        expect(seen).toBe('#5ed69a|#ff7a86|#b69af0|#5ed69a');
        dispose();
    });
});
