/**
 * The import todos of a bulk-editor row that still wait for an answer.
 *
 * An import hands rows to the editor with field todos: a field the importer could not fill or
 * wants the user to check. Applying the row's form answers a todo when its field now holds a
 * value. A missing cost basis has a second answer: Auto mode, where the cost is the weighted
 * average the backend computes, so no value is ever written in the field itself.
 */

/** The todo fields this helper reads. */
export interface FieldTodoLike {
    field: string;
}

/** The row fields this helper reads: any field a todo can name, plus the cost-basis mode. */
export type TodoAnswerFields = {cost_basis_mode?: 'auto' | 'manual' | null} & Record<string, unknown>;

/** The todos still open after the row's form was applied, in their order. The input list is not changed. */
export function remainingTodos<T extends FieldTodoLike>(todos: ReadonlyArray<T>, fields: object): T[] {
    const values = fields as TodoAnswerFields;
    return todos.filter((todo) => {
        if (todo.field === 'cost_basis_override' && values.cost_basis_mode === 'auto') return false;
        const value = values[todo.field];
        return value == null || value === '';
    });
}
