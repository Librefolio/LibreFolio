/**
 * Palettes and colour scales of the charts that are not categories with a key — the one home for them.
 *
 * The categories with a fixed colour (asset types, sectors) and the sequences of the charts that colour by order (the
 * owners of the semi-donut, the countries of the geography history) live in `./chartCategories`. What stays here are
 * the lists still read as they are: the signals' default line colours (S9, after the 1.3 moves), and the designer's
 * round-3 scales (§1.6) — the world maps' and the correlation matrix's; and the broker lines of the Growth chart (GR5),
 * read through `categoryColor` at each draw.
 *
 * A pair is read with `themed(pair, dark)` (`./themePair`).
 *
 * @module lib/theme/chartPalettes
 */

import {CATEGORY_SEQUENCE, categoryColor, sequenceColor} from './chartCategories';
import {shadePoles, type ShadePoles} from './chartShades';
import {chartRoles} from './roleColors';
import type {ThemePair} from './themePair';

/** Default line colours of a new chart signal; `registry.ts` picks the one farthest in hue from those in use. The same in both themes. */
export const SIGNAL_DEFAULT_PALETTE: string[] = ['#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

/**
 * World maps, from little weight to the most: six steps of blue, a scale per theme (round 3, §1.6), the same for the
 * Dashboard, the asset page and the PAC planner. The countries with no data: `GEO_MAP_COLORS.land` (`./chartTheme`).
 */
export const GEO_CHOROPLETH_SCALE: ThemePair<string[]> = {
    light: ['#E9EFF8', '#C8D7EF', '#A1BCE4', '#7798D0', '#4E72B3', '#2B477F'],
    dark: ['#202A3A', '#293B57', '#36527B', '#456BA2', '#5D85C2', '#82A8E2'],
};

/**
 * The correlation matrix, from −1 through 0 to +1: a red, a grey-blue, the cobalt of the ETF (round 3, §1.6). Values of
 * its own, no longer the danger, panel and info roles; ECharts interpolates between them in sRGB.
 */
export const CORRELATION_SCALE: ThemePair<readonly [string, string, string]> = {
    light: ['#C43D4D', '#8795A8', '#2459B8'],
    dark: ['#FF8995', '#526174', '#82ACF8'],
};

/**
 * The value in a correlation cell: whichever of pure black and pure white reads best on it (§1.6). At least 4.5:1 on the
 * whole scale, in both themes (4.59:1 at worst, near r = +0.52 in light and −0.32 in dark).
 */
export const CORRELATION_CELL_TEXT: readonly [string, string] = ['#000000', '#FFFFFF'];

/**
 * The colour of the Growth chart's P&L broker line `index`: the first eight asset types of the designer's table, in its
 * order, then the same eight one shade further at each round, never a silent repeat (GR5, `sequenceColor`; DV-8). Read
 * at each draw through `categoryColor`, so a Designer Lab edit of a category reaches the lines (C1, TD-1b).
 *
 * `poles` are the GR4 poles of the chart's theme. By default those of the page's card (`chartRoles` on `<html>`), read
 * only from the ninth line on, where a shade is needed: the Growth chart sits on the page's card, in no forced theme.
 */
export function growthBrokerColor(index: number, dark: boolean, poles?: ShadePoles): string {
    if (index < CATEGORY_SEQUENCE.length) {
        const {kind, key} = CATEGORY_SEQUENCE[index];
        return categoryColor(kind, key, dark);
    }
    return sequenceColor(CATEGORY_SEQUENCE, index, dark, poles ?? shadePoles(dark, chartRoles(dark).color('--lf-surface-card')));
}
