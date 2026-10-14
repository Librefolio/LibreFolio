import type {ColumnDef} from '$lib/components/table/types';
import {escapeHtml} from '$lib/utils/core/escapeHtml';

// Lucide `circle-question-mark`, the icon of the planner «?» buttons. DataTable shows a
// header tooltip without any visible cue unless the column also has a link, so the cue
// travels inside the header label.
const HELP_ICON =
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" class="text-gray-400 dark:text-gray-500" style="display:inline-block;vertical-align:-2px;margin-left:4px"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>';

const resolve = (value: string | (() => string)): string => (typeof value === 'function' ? value() : value);

/** Adds the «?» cue to every labelled header that carries a tooltip and no custom header markup. */
export function withHelpCues<T>(columns: ColumnDef<T>[]): ColumnDef<T>[] {
    return columns.map((column) => {
        if (!column.headerTooltip || column.headerHtml || column.headerTooltipUrl) return column;
        const header = column.header;
        return {
            ...column,
            headerHtml: () => {
                const label = resolve(header);
                return label ? `${escapeHtml(label)}${HELP_ICON}` : '';
            },
        };
    });
}
