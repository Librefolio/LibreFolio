/**
 * selectionGuards.ts — which rows of a selection the user may edit (FB-17).
 *
 * The Transactions page and the broker page's Transactions tab open the bulk workspace from a selection (Edit, Clone,
 * Delete). A row on a broker the user can only read is left out, with a word to say so; a selection with nothing left to
 * edit opens nothing. One rule for both pages, so they cannot drift apart.
 */

/** The two messages a guard can raise: some rows were left out, or all of them. */
export interface SelectionNotify {
    warning(message: string): void;
    error(message: string): void;
}

/** The UI translator, as the pages hold it (`$_`). */
export type SelectionTranslate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** The rows of `rows` the user can edit, and the ones they cannot (`canEdit` is `txStoreCanEdit`: a pair needs both brokers). */
export function splitEditableRows<T extends {id: number}>(rows: readonly T[], canEdit: (id: number) => boolean): {editable: T[]; skipped: T[]} {
    const editable: T[] = [];
    const skipped: T[] = [];
    for (const row of rows) (canEdit(row.id) ? editable : skipped).push(row);
    return {editable, skipped};
}

/**
 * The editable rows of a selection, or `null` when there are none. A warning counts the rows left out when some stay; an
 * error says that nothing can be edited when none does.
 */
export function guardEditableRows<T extends {id: number}>(rows: readonly T[], canEdit: (id: number) => boolean, notify: SelectionNotify, t: SelectionTranslate): T[] | null {
    const {editable, skipped} = splitEditableRows(rows, canEdit);
    if (skipped.length > 0 && editable.length > 0) notify.warning(t('transactions.bulk.skippedViewerOnly', {values: {n: skipped.length}}));
    if (editable.length === 0) {
        notify.error(t('transactions.bulk.allViewerOnly'));
        return null;
    }
    return editable;
}
