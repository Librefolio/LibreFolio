/**
 * Colours computed from a value — the one home for them.
 *
 * Each function was moved verbatim from the chart that computed it, so the same input still gave the same colour
 * string; `timingEffectColor` has since moved onto the gain and loss roles (TD-2). They stay functions because their
 * colour is a formula, not a table entry.
 *
 * @module lib/theme/chartColorScales
 */

import {TREEMAP_COLORS} from './chartTheme';

/**
 * The colour of a treemap tile for its P&L percentage: the portfolio's gain or loss colour, stronger as the percentage
 * grows, at full strength from ±50 %. In the light theme the loss scale runs the other way from the gain scale — bigger
 * losses get lighter — as it always did, for the designer to decide.
 */
export function treemapPnlColor(pct: number | null, isDark: boolean): string {
    if (pct == null) return TREEMAP_COLORS.noPnl;
    if (pct >= 0) {
        const intensity = Math.min(pct * 100, 50) / 50;
        return isDark ? `rgb(${34 + intensity * 40}, ${197 + intensity * 40}, ${94 + intensity * 40})` : `rgb(${22 - intensity * 10}, ${163 - intensity * 30}, ${74 + intensity * 20})`;
    }
    const intensity = Math.min(Math.abs(pct * 100), 50) / 50;
    return isDark ? `rgb(${248}, ${113 - intensity * 40}, ${113 - intensity * 40})` : `rgb(${220 + intensity * 20}, ${38 + intensity * 20}, ${38 + intensity * 20})`;
}

/**
 * The KPI card's timing-effect text, for an inline `style`: the gain role when favourable, the loss role otherwise, its
 * strength in `alpha` (0–1). A CSS `color-mix()` over the role variable, so it follows the theme like a class does; a
 * canvas cannot read it — a chart takes its roles from `roleColors`.
 */
export function timingEffectColor(favorable: boolean, alpha: number): string {
    const pct = Number((Math.min(Math.max(alpha, 0), 1) * 100).toFixed(2));
    return favorable ? `color-mix(in oklab, var(--lf-gain) ${pct}%, transparent)` : `color-mix(in oklab, var(--lf-loss) ${pct}%, transparent)`;
}
