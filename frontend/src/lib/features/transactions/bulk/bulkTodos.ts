/**
 * The import todos of a bulk-editor row that still wait for an answer.
 *
 * An import hands rows to the editor with field todos: a field the importer could not fill or
 * wants the user to check. Applying the row's form answers a todo when its field now holds a
 * value. A cost basis todo that only warns has a second answer: Auto mode, where the cost is the
 * weighted average the backend computes, so no value is ever written in the field itself. A
 * blocking one does not: the importer knows the cost is missing (a gap-fix position, a demerger, a
 * corporate action), Auto has nothing true to average there, and only a value written by hand —
 * 0 included — answers it (developer decision Q-J57-1 (c), 19/10; it supersedes D6 for blockers).
 */

/** The todo fields this helper reads. */
export interface FieldTodoLike {
    field: string;
    severity?: string;
}

/** The row fields this helper reads: any field a todo can name, plus the cost-basis mode. */
export type TodoAnswerFields = {cost_basis_mode?: 'auto' | 'manual' | null} & Record<string, unknown>;

const COST_BASIS_FIELD = 'cost_basis_override';

/** A cost basis written by hand: an amount that is not empty. In Auto the form stores a currency sentinel
 *  (`{code, amount: '0'}`), never a cost, so a row in Auto has none. */
function hasManualCost(values: TodoAnswerFields): boolean {
    if (values.cost_basis_mode === 'auto') return false;
    const cost = values[COST_BASIS_FIELD] as {amount?: unknown} | null | undefined;
    return cost != null && typeof cost === 'object' && String(cost.amount ?? '').trim() !== '';
}

/** The todos still open after the row's form was applied, in their order. The input list is not changed. */
export function remainingTodos<T extends FieldTodoLike>(todos: ReadonlyArray<T>, fields: object): T[] {
    const values = fields as TodoAnswerFields;
    return todos.filter((todo) => {
        if (todo.field === COST_BASIS_FIELD && todo.severity === 'blocker') return !hasManualCost(values);
        if (todo.field === COST_BASIS_FIELD && values.cost_basis_mode === 'auto') return false;
        const value = values[todo.field];
        return value == null || value === '';
    });
}

/** Whether the row waits for a cost basis written by hand: it opens in Manual, the field empty (Q-J57-1 (c)). */
export function hasBlockingCostTodo(todos: ReadonlyArray<FieldTodoLike>): boolean {
    return todos.some((todo) => todo.field === COST_BASIS_FIELD && todo.severity === 'blocker');
}

/** What an imported row hands the editor, about its cost basis. */
export interface ImportedCostBasis {
    /** The mode the plugin sent, if any. */
    mode: 'auto' | 'manual' | null;
    /** The cost the plugin wrote, if any. */
    cost: {code?: string; amount?: string} | null;
    /** Whether the row's type, on its side, takes a cost basis at all. */
    costAllowed: boolean;
}

/**
 * The cost-basis mode an imported row starts with in the editor. The plugin's own mode stays; a type that takes no cost
 * has none; a cost the plugin wrote — 0 included, a gift — is Manual, and so is a blocking cost todo, which only a cost
 * written by hand answers (Q-J57-1 (c)). Any other row starts in Auto: a row the plugin could not cost is never left
 * without a mode (developer decision Q-J57-5 (a), 19/10), so the hand-over's validation costs it at the average, or
 * refuses it when there is nothing to average.
 */
export function initialCostBasisMode(row: ImportedCostBasis, todos: ReadonlyArray<FieldTodoLike>): 'auto' | 'manual' | null {
    if (row.mode !== null) return row.mode;
    if (!row.costAllowed) return null;
    if (row.cost != null && String(row.cost.amount ?? '').trim() !== '') return 'manual';
    if (hasBlockingCostTodo(todos)) return 'manual';
    return 'auto';
}

/**
 * The «may be a stock split» todo (W-B87): a broker's split row the importer turned into an incoming adjustment at no cost.
 * It waits on `asset_event_id`, so `remainingTodos` retires it when a SPLIT event is linked; the bulk editor shows it in its own
 * banner, apart from the generic «fields to verify».
 */
export const POSSIBLE_SPLIT_REASON = 'possible_split';
export function isPossibleSplitTodo(todo: {field: string; reasonCode?: string}): boolean {
    return todo.field === 'asset_event_id' && todo.reasonCode === POSSIBLE_SPLIT_REASON;
}
export function withoutPossibleSplit<T extends {field: string; reasonCode?: string}>(todos: ReadonlyArray<T>): T[] {
    return todos.filter((todo) => !isPossibleSplitTodo(todo));
}
/** One row of the possible-split banner: what the importer knew (ticker, shares, and the ratio when it could read the holding). */
export interface PossibleSplitEntry {
    tempId: string;
    rowId: string;
    rowNumber: string;
    assetId: number | null;
    date: string;
    ticker: string;
    addedQuantity: string;
    isin: string | null;
    ratio: string | null;
    suggestedRatio: string | null;
    roundingDelta: string | null;
    heldBefore: string | null;
}
const text = (v: unknown): string | null => (v === undefined || v === null || v === '' ? null : String(v));
/** The rows that still carry a possible-split todo, in the grid's order; a row once linked has no todo and drops out. */
export function possibleSplitEntries(
    ops: ReadonlyArray<{tempId: string; pairedWith?: string; fields: {asset_id: number | null; date: string; asset_event_id: number | null}; todos?: Array<{field: string; reasonCode?: string; context?: Record<string, unknown>}>}>,
    rowLabel: (tempId: string) => string,
): PossibleSplitEntry[] {
    const entries: PossibleSplitEntry[] = [];
    for (const op of ops) {
        const todo = (op.todos ?? []).find(isPossibleSplitTodo);
        if (!todo) continue;
        const context = todo.context ?? {};
        const delta = text(context.rounding_delta);
        entries.push({
            tempId: op.tempId,
            rowId: op.pairedWith ?? op.tempId,
            rowNumber: rowLabel(op.tempId),
            assetId: op.fields.asset_id,
            date: op.fields.date,
            ticker: String(context.ticker ?? ''),
            addedQuantity: String(context.added_quantity ?? ''),
            isin: context.isin ? String(context.isin) : null,
            ratio: text(context.ratio),
            suggestedRatio: text(context.suggested_ratio),
            roundingDelta: delta !== null && Number(delta) !== 0 ? delta : null,
            heldBefore: text(context.held_before),
        });
    }
    return entries;
}
