/**
 * The asset column of Asset Global's comparison tables — L1° ("how much did each of
 * these hurt?") and L3° ("what did each pay for its risk?").
 *
 * One module, so the two tables cannot drift apart: the cell is the Assets list's
 * (`AssetTable`) — the type icon and the name on one line, scrolling when it does not
 * fit — and the order is the matrix's "by name" (`nameComparator`, emoji ignored),
 * ties broken by id. The name is escaped because the DataTable renders HTML cells
 * as they come.
 *
 * The scrolling itself is attached by each table on its own wrapper
 * (`attachOverflowMarqueeToDescendants`): an HTML string cannot carry a `use:` action.
 */
import type {ColumnDef, HtmlCell} from '$lib/components/table/types';
import {escapeHtml} from '$lib/utils/core/escapeHtml';
import {overflowScrollTextClass} from '$lib/utils/overflowScroll';

import {nameComparator} from './correlationHelpers';

/**
 * A figure's cell, in either table. A figure nobody could measure is an em dash, and the
 * dash explains itself in the project's Tooltip — the tables carry no fixed note under them
 * any more (the developer's review, round 4). A measured figure carries no tooltip.
 */
export function figureCell(html: string, measured: boolean, blankExplanation: () => string): HtmlCell {
    return measured ? {type: 'html', html} : {type: 'html', html, tooltip: {text: blankExplanation()}};
}

/** What the asset column reads from a row of either table. */
export interface AssetSetTableRow {
    assetId: number;
    name: string;
}

/**
 * The cell's HTML: `{prefix}-name` carries the asset id, `{prefix}-icon` appears only
 * when there is an icon URL.
 *
 * No cap on the content: both tables that use it are laid out `fixed` (the developer's
 * review, 06/10), so the column is as wide as the reader made it and a name may use all of
 * it, scrolling inside it when it is longer. (An `auto` table needed `max-w-56`, or the
 * longest name set the column's width.)
 */
export function assetNameCellHtml(testIdPrefix: string, row: AssetSetTableRow, iconUrl: string | undefined): string {
    const iconHtml = iconUrl ? `<img src="${escapeHtml(iconUrl)}" alt="" class="h-5 w-5 shrink-0 object-contain" data-testid="${testIdPrefix}-icon" />` : '';
    return `<div class="flex min-w-0 items-center gap-2" data-testid="${testIdPrefix}-name" data-asset-id="${row.assetId}">${iconHtml}<span class="min-w-0 flex-1 text-gray-700 dark:text-gray-200 ${overflowScrollTextClass}">${escapeHtml(row.name)}</span></div>`;
}

const compareNames = nameComparator();

/**
 * The asset column. Not pinned (the developer's review, 06/10: «non li volevo fissi»): the
 * names scroll with their figures. `icons` is read at render time, so a map the caller
 * replaces reaches the cells without rebuilding the column.
 */
export function assetNameColumn<T extends AssetSetTableRow>(header: () => string, icons: () => ReadonlyMap<number, string>, testIdPrefix: string): ColumnDef<T> {
    return {
        id: 'name',
        header,
        type: 'text',
        width: 220,
        minWidth: 140,
        filterable: false,
        sortFn: (left, right) => compareNames(left.name, right.name) || left.assetId - right.assetId,
        cell: (row) => ({type: 'html', html: assetNameCellHtml(testIdPrefix, row, icons().get(row.assetId))}),
    };
}
