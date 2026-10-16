/**
 * Palettes and colour scales of the charts that are not categories with a key — the one home for them.
 *
 * The categories with a fixed colour (asset types, sectors) and the sequences of the charts that colour by order (the
 * owners of the semi-donut, the countries of the geography history) live in `./chartCategories`, the designer's round 2
 * (GR1–GR5, D-T17). What stays here are the lists still read as they are, the signals' default line colours (S9, after
 * the 1.3 moves) and the world maps' scale (GR5.1), and the broker lines of the Growth chart (GR5), read through
 * `categoryColor` at each draw.
 *
 * A pair is read with `themed(pair, dark)` (`./themePair`).
 *
 * @module lib/theme/chartPalettes
 */

import {CATEGORY_SEQUENCE, categoryColor} from './chartCategories';
import type {ThemePair} from './themePair';

/** Default line colours of a new chart signal; `registry.ts` picks the one farthest in hue from those in use. The same in both themes. */
export const SIGNAL_DEFAULT_PALETTE: string[] = ['#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

/** World maps, from no weight to the most: the brand's sage and forest greens, a scale per theme (GR5.1). */
export const GEO_CHOROPLETH_SCALE: ThemePair<string[]> = {
    light: ['#E6F2ED', '#C2E0D3', '#94C7B2', '#62AB8E', '#378567', '#1B4334'],
    dark: ['#182923', '#1F3B30', '#275241', '#316B54', '#3D876A', '#4FB38B'],
};

/**
 * The colour of the Growth chart's P&L broker line `index`: the first eight asset types of the designer's table, in its
 * order, cycled (GR5: «devono tutte seguire la nuova famiglia cromatica»). Read at each draw through `categoryColor`, so
 * a Designer Lab edit of a category reaches the lines (C1, TD-1b).
 */
export function growthBrokerColor(index: number, dark: boolean): string {
    return categoryColor('type', CATEGORY_SEQUENCE[index % CATEGORY_SEQUENCE.length], dark);
}
