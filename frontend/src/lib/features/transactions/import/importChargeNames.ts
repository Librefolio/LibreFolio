/**
 * Linked charges at the import hand-over (project 66, lot P1b).
 *
 * A plugin that knows a FEE or a TAX belongs to a trade names the trade `ref` and the charge `parent_ref` (P1a); the
 * wizard's split names its legs the same way. Those names are the file's, so they repeat in every upload of one
 * statement, exactly as a pair's `link_uuid` does (`importPairs.ts`). At each hand-over to the editor they are renewed
 * under the key of the pairs, file + name, and a name whose other end is not handed over is dropped: a charge whose
 * parent is not chosen stands alone (D10), a parent no chosen charge names needs no name.
 */
import type {TransactionCreateItem} from '$lib/types';
import type {DuplicateStatus, MergedTx} from './importTypes';

/**
 * Index namespace for the legs the user carves out of a source row. A leg is not in the file, so it has no row of its
 * own to be numbered by; keeping it far above the parse counter makes its index stable across re-applies (one leg per
 * parent, replaced in place) and impossible to confuse with a row the plugin actually read.
 */
export const SPLIT_LEG_INDEX_BASE = 1_000_000;
/** The most legs one row can be split into. */
export const MAX_SPLIT_LEGS = 6;

/** One charge of the wizard's split, as the corrections step states it: a magnitude, money leaving. */
interface SplitLeg {
    type: string;
    amount: string;
    description: string;
}

type Names = {ref?: string | null; parent_ref?: string | null; link_uuid?: string | null};

function nameOf(value: string | null | undefined): string | null {
    return value ? value : null;
}

function keyOf(row: Pick<MergedTx, 'sourceFileId'>, name: string): string {
    return `${row.sourceFileId}\u0000${name}`;
}

/**
 * The rows chosen for one hand-over, with their names renewed (see the module's header). Each `ref` that a chosen
 * charge of the same file names gets a fresh name from `newName`, one per file + name, and those charges name it in
 * `parent_ref`; every other `ref` and `parent_ref` is removed. A name used by two rows of one file names the first one
 * only. Rows without names come back as they are; the length and the order are kept; the input is not mutated.
 */
export function completeChargeNames(rows: readonly MergedTx[], newName: () => string): MergedTx[] {
    const parents = new Map<string, number>();
    rows.forEach((row, position) => {
        const ref = nameOf((row.tx as Names).ref);
        if (ref && !parents.has(keyOf(row, ref))) parents.set(keyOf(row, ref), position);
    });
    const named = new Set<string>();
    rows.forEach((row, position) => {
        const parentRef = nameOf((row.tx as Names).parent_ref);
        if (!parentRef) return;
        const parent = parents.get(keyOf(row, parentRef));
        if (parent !== undefined && parent !== position) named.add(keyOf(row, parentRef));
    });

    const fresh = new Map<string, string>();
    const freshFor = (key: string): string => {
        let name = fresh.get(key);
        if (!name) {
            name = newName();
            fresh.set(key, name);
        }
        return name;
    };

    return rows.map((row, position) => {
        const {ref: rawRef, parent_ref: rawParentRef, ...rest} = row.tx as unknown as Names & Record<string, unknown>;
        const ref = nameOf(rawRef);
        const parentRef = nameOf(rawParentRef);
        if (!ref && !parentRef) return row;
        const tx: Record<string, unknown> = {...rest};
        if (ref && named.has(keyOf(row, ref)) && parents.get(keyOf(row, ref)) === position) tx.ref = freshFor(keyOf(row, ref));
        if (parentRef && named.has(keyOf(row, parentRef)) && parents.get(keyOf(row, parentRef)) !== position) tx.parent_ref = freshFor(keyOf(row, parentRef));
        return {...row, tx: tx as unknown as TransactionCreateItem};
    });
}

/**
 * The legs of the wizard's split. `row` is the parent as the corrections step left it, its cash already the trade's
 * share; `legs` the charges the user named. Each leg is a FEE or a TAX of the row's broker, asset and date, quantity 0,
 * money leaving in the row's currency (EUR when it has none), tagged `split_leg`, with no cost, no todo and no
 * duplicate verdict. The legs are born linked to the trade (D10): none copies the trade's `ref` or `link_uuid`, each
 * names the trade in `parent_ref`, and a trade without a name gets the wizard's, `split:<index>`. Returns the trade
 * (named) and at most `MAX_SPLIT_LEGS` legs, in the order given; `row` is not mutated.
 */
export function splitLegRows(row: MergedTx, legs: readonly SplitLeg[]): {parent: MergedTx; legs: MergedTx[]} {
    const parentName = nameOf((row.tx as Names).ref) ?? `split:${row.index}`;
    const parent: MergedTx = {...row, tx: {...row.tx, ref: parentName} as TransactionCreateItem};
    const cash = (row.tx as {cash?: {code: string; amount: string} | null}).cash ?? null;
    const code = cash?.code ?? 'EUR';
    const {ref: _ref, link_uuid: _link, ...shared} = row.tx as unknown as Names & Record<string, unknown>;
    const made = legs.slice(0, MAX_SPLIT_LEGS).map(
        (leg, k): MergedTx => ({
            ...row,
            index: SPLIT_LEG_INDEX_BASE * (k + 1) + row.index,
            tx: {
                ...shared,
                type: leg.type,
                quantity: '0',
                cash: {code, amount: `-${leg.amount}`},
                description: leg.description,
                tags: [...(((row.tx as {tags?: string[]}).tags ?? []) as string[]), 'split_leg'],
                cost_basis_override: null,
                parent_ref: parentName,
            } as unknown as TransactionCreateItem,
            todos: [],
            duplicateStatus: 'unique' as DuplicateStatus,
            dupMatches: [],
        }),
    );
    return {parent, legs: made};
}
