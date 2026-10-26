/**
 * preFloorDate.ts — the warning for a transaction dated before 1 January 1900 (D-P4, W5-10).
 *
 * A date that early is almost always a typo (`1024` for `2024`, `1925` for `2025`). The backend writes it (D-P4,
 * 26/10/2026: a transaction of 1850, or of the year 1, is stored like any other and replayed from its own day; only the
 * forward ceiling, tomorrow, is still refused), so this is the only protection against the typo: the form, the bulk
 * editor and the import review tell the user, and ask for one confirmation before the save goes on. Nothing here refuses
 * a date; it only asks.
 *
 * Dates are `YYYY-MM-DD` text, compared as text: a four-digit year makes the text order the calendar order.
 */
import type {ImportTodo} from '$lib/features/transactions/txPayloadHelpers';

/** The first day of 1900: a date before it asks for a confirmation (it is no longer a limit of the backend). */
export const PRE_FLOOR_DATE_LIMIT = '1900-01-01';

/** The reason code of the todo the import review puts on such a row. */
export const PRE_FLOOR_DATE_REASON = 'date_before_1900';

const ISO_DAY = /^\d{4}-\d{2}-\d{2}/;

/** Whether `date` (`YYYY-MM-DD`, a time part allowed) is a day before 1 January 1900. A blank or unreadable date is not. */
export function isBeforeDateFloor(date: string | null | undefined): boolean {
    if (!date || !ISO_DAY.test(date)) return false;
    return date.slice(0, 10) < PRE_FLOOR_DATE_LIMIT;
}

/** The distinct dates of the list that are before 1900, oldest first. */
export function preFloorDates(dates: ReadonlyArray<string | null | undefined>): string[] {
    return [...new Set(dates.filter(isBeforeDateFloor).map((date) => String(date).slice(0, 10)))].sort();
}

/** The todo the import review puts on a row dated before 1900: a warning on `date`, the date in its context. */
export function isPreFloorDateTodo(todo: {field: string; reasonCode?: string}): boolean {
    return todo.field === 'date' && todo.reasonCode === PRE_FLOOR_DATE_REASON;
}

/**
 * The row's todos, with the warning for a date before 1900 added when it has one: a `warning` on `date` whose context
 * holds the date, which the review lists on the row and the bulk editor takes over. The plugin's own todos stay; a row
 * already carrying this one is not given a second.
 */
export function withPreFloorDateTodo(todos: ImportTodo[], date: string | null | undefined): ImportTodo[] {
    if (!isBeforeDateFloor(date) || todos.some(isPreFloorDateTodo)) return todos;
    const day = String(date).slice(0, 10);
    return [...todos, {field: 'date', severity: 'warning', reasonCode: PRE_FLOOR_DATE_REASON, message: `The date ${day} is before 1 January 1900: check the year.`, context: {date: day}}];
}

/** One row of the bulk editor's warning: where it is and which date it carries. */
export interface PreFloorEntry {
    tempId: string;
    rowId: string;
    rowNumber: string;
    date: string;
}

/** The rows of the bulk editor dated before 1900, in the grid's order; the two legs of a pair are listed once each by their own date. */
export function preFloorEntries(ops: ReadonlyArray<{tempId: string; pairedWith?: string; fields: {date: string}}>, rowLabel: (tempId: string) => string): PreFloorEntry[] {
    const entries: PreFloorEntry[] = [];
    for (const op of ops) {
        if (!isBeforeDateFloor(op.fields.date)) continue;
        entries.push({tempId: op.tempId, rowId: op.pairedWith ?? op.tempId, rowNumber: rowLabel(op.tempId), date: op.fields.date.slice(0, 10)});
    }
    return entries;
}
