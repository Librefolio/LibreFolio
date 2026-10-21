/**
 * Colours computed from a value — the one home for them.
 *
 * They stay functions because their colour is a formula, not a table entry. The KPI timing effect, once a
 * formula here, takes the sign classes of the other KPIs since the designer's round 3 (§1.7).
 *
 * @module lib/theme/chartColorScales
 */

import {CHART_GAIN_LOSS, TREEMAP_COLORS} from './chartTheme';
import {mixOklab} from './chartShades';
import {themed} from './themePair';
import {SERIES_ROLE_VALUES} from './seriesRoles';

/** How far a tile at full strength (±50 %) moves toward the primary text: darker in the light theme, brighter in the dark one. */
const TILE_EMPHASIS = 0.3;

/**
 * The colour of a treemap tile for its P&L percentage: the portfolio's gain or loss colour (the roles `--lf-gain` and
 * `--lf-loss`), moving toward the primary text as the percentage grows, at full strength from ±50 % — darker in the
 * light theme, brighter in the dark one. It was a formula on fixed greens and reds (the loss scale ran the other way
 * in light); on the roles since D-T28, «da rivedere» with the designer.
 */
export function treemapPnlColor(pct: number | null, isDark: boolean): string {
    if (pct == null) return TREEMAP_COLORS.noPnl;
    const intensity = Math.min(Math.abs(pct * 100), 50) / 50;
    const base = themed(pct >= 0 ? CHART_GAIN_LOSS.portfolio.gain : CHART_GAIN_LOSS.portfolio.loss, isDark);
    return mixOklab(base, themed(SERIES_ROLE_VALUES['--lf-text-primary'], isDark), intensity * TILE_EMPHASIS);
}
