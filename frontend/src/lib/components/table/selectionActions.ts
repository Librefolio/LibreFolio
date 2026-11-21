/**
 * The rule of the bulk actions, one for every table (plan 77, SEL-A; the developer's Q-SEL-1, Q-SEL-9, Q-SEL-12 and
 * Q-SEL-17 of 19/11/2026, lane 66's `linkSelection`):
 *
 * - **hidden** when no selected row can take the action (`appliesTo`), when it takes fewer than its `minSelection`, or
 *   when on those rows it makes no sense here (`pointless`);
 * - **off with its reason** when it could act but is blocked (`blocked`): the hint is read on hover, focus, tap and a
 *   click attempt (66 F7-a);
 * - **on** otherwise.
 *
 * In every state the action carries the number of rows it acts on (always, Q-SEL-1 and Q-SEL-16), and it acts on those
 * rows only: a mixed selection may show two actions, each on its own part. Pure: the bar and the dock only draw it.
 */
import type {BulkAction} from './types';

export type ResolvedSelectionAction<T> = {state: 'hidden'; action: BulkAction<T>} | {state: 'off'; action: BulkAction<T>; rows: T[]; count: number; hint: string; reason: string} | {state: 'on'; action: BulkAction<T>; rows: T[]; count: number};

/** A resolved action that is drawn: on, or off with its reason. */
export type ShownSelectionAction<T> = Exclude<ResolvedSelectionAction<T>, {state: 'hidden'}>;

function text(value: string | (() => string)): string {
    return typeof value === 'function' ? value() : value;
}

/** What `action` does with the selected rows `selected`. */
export function resolveSelectionAction<T>(action: BulkAction<T>, selected: readonly T[]): ResolvedSelectionAction<T> {
    const rows = action.appliesTo ? selected.filter((row) => action.appliesTo!(row)) : [...selected];
    if (rows.length === 0 || rows.length < (action.minSelection ?? 1)) return {state: 'hidden', action};
    if (action.pointless?.(rows)) return {state: 'hidden', action};
    const block = action.blocked?.(rows) ?? null;
    if (block) return {state: 'off', action, rows, count: rows.length, hint: text(block.hint), reason: block.reason};
    return {state: 'on', action, rows, count: rows.length};
}

/** The actions to draw for `selected`, in their order: the hidden ones are left out. */
export function resolveSelectionActions<T>(actions: readonly BulkAction<T>[], selected: readonly T[]): ShownSelectionAction<T>[] {
    return actions.map((action) => resolveSelectionAction(action, selected)).filter((item): item is ShownSelectionAction<T> => item.state !== 'hidden');
}

/** A button of the selection bar (`DataTableToolbar`), drawn from a resolved action. */
export interface SelectionToolbarAction {
    id: string;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: any;
    label: string | (() => string);
    shortLabel?: string | (() => string);
    variant?: 'default' | 'danger';
    primary?: boolean;
    iconClass?: string;
    count: number;
    disabled: boolean;
    hint?: string;
    reason?: string;
    testid?: string;
    onClick: () => void;
}

/**
 * The bar's buttons for `selected`: each shown action with its number, off with its reason when blocked, and a click on
 * its own rows — through `run` when the caller runs the actions itself (a confirmation first), else its `onClick`. One
 * mapping for the table's panel and a page's own fixed panel (Asset, Q-SEL-7).
 */
export function selectionToolbarActions<T>(actions: readonly BulkAction<T>[], selected: readonly T[], run: (action: BulkAction<T>, rows: T[]) => void = (action, rows) => void action.onClick(rows)): SelectionToolbarAction[] {
    return resolveSelectionActions(actions, selected).map((item) => ({
        id: item.action.id,
        icon: item.action.icon,
        label: item.action.label,
        shortLabel: item.action.shortLabel,
        variant: item.action.variant,
        primary: item.action.primary,
        iconClass: item.action.iconClass,
        count: item.count,
        disabled: item.state === 'off',
        hint: item.state === 'off' ? item.hint : undefined,
        reason: item.state === 'off' ? item.reason : undefined,
        testid: item.action.testid,
        onClick: () => run(item.action, item.rows),
    }));
}
