/**
 * Which flagged rows the correction step owns, and what happens to their todos as the
 * user settles and re-opens them.
 *
 * Extracted from `ImportWizardModal` because the rules are pure and one of them is
 * subtle enough to have shipped a defect: a row that had been settled and was then
 * re-opened matched neither half of the membership test and disappeared from under the
 * user mid-edit.
 */

/** The shape of a plugin todo, reduced to what these rules read. */
export interface FixTodoLike {
    severity: string;
    field: string;
    context?: unknown;
}

/**
 * Fields whose value decides the duplicate comparison: type, date, quantity, asset and
 * the cash leg. Only a blocker on one of these belongs in the correction step.
 *
 * A missing cost basis, by contrast, blocks the *import* but not the *comparison* — it
 * is handled later, in the bulk editor, which has the per-unit tooling for it. Dragging
 * it here would turn the step into a wall the editor cannot open.
 */
export const DUP_RELEVANT_FIELDS = new Set(['type', 'date', 'quantity', 'asset_id', 'cash', 'cash.amount', 'cash.code']);

/** A blocker on a field the database comparison keys on. */
export function isDupRelevantBlocker(td: FixTodoLike): boolean {
    return td.severity === 'blocker' && DUP_RELEVANT_FIELDS.has(td.field);
}

/**
 * A charge or an income the plugin could not attach to an instrument. Not a blocker —
 * the file may genuinely never name it — but just as anomalous as a misread trade, and
 * this is the one screen where the user can still fix it while the context is on screen.
 */
export function isUnallocatedAssetWarning(td: FixTodoLike): boolean {
    return td.severity === 'warning' && td.field === 'asset_id';
}

/**
 * The file gave one amount where several things happened at once — a bond bought on the
 * secondary market pays price, accrued interest and commissions in a single debit. The
 * plugin will not invent the breakdown, but the user has it on their contract note, so
 * the correction step offers to split the row once they type the net countervalue.
 */
export function isCashSplitWarning(td: FixTodoLike): boolean {
    return td.severity === 'warning' && (td.context as {split_hint?: string} | undefined)?.split_hint !== undefined;
}

/** Every todo the correction step can actually act on. */
export function isFixStepTodo(td: FixTodoLike): boolean {
    return isDupRelevantBlocker(td) || isUnallocatedAssetWarning(td) || isCashSplitWarning(td);
}

/**
 * Whether a row belongs to the correction step.
 *
 * Two ways in, and both are needed. A row is there because it still carries something to
 * fix, *or* because it was already settled — settling retires the todos, and a settled
 * row must stay visible, badged and editable, rather than vanish the moment it is dealt
 * with.
 *
 * @param todos The row's live todos.
 * @param decision `null`/`undefined` when the row is still pending.
 */
export function rowStaysInFixStep(todos: ReadonlyArray<FixTodoLike>, decision: string | null | undefined): boolean {
    return todos.some(isFixStepTodo) || decision != null;
}

/**
 * The todos a row keeps once it is settled: the step's own are retired, everything else
 * survives. Retiring them is what lets the bulk editor accept the row.
 */
export function todosAfterSettle<T extends FixTodoLike>(todos: ReadonlyArray<T>): T[] {
    return todos.filter((td) => !isFixStepTodo(td));
}

/**
 * The todos a row gets back when its decision is withdrawn.
 *
 * The snapshot taken at settling time is restored, on top of whatever non-step todos the
 * row has now. Without this the row carried no step todos *and* no decision, matched
 * neither half of `rowStaysInFixStep`, and disappeared — recoverable only by reloading
 * the page.
 *
 * @param current The row's todos as they stand, after settling stripped the step's.
 * @param snapshot What the row carried before it was settled; `undefined` if never taken.
 */
export function todosAfterReopen<T extends FixTodoLike>(current: ReadonlyArray<T>, snapshot: ReadonlyArray<T> | undefined): T[] {
    if (!snapshot) return [...current];
    return [...current.filter((td) => !isFixStepTodo(td)), ...snapshot];
}
