/**
 * The reward lots group of the Lots table (project 79, STK-2c; mockup approved by the developer, P-25; rules Q-5 of the
 * domain consultant). Pure logic, so the table only draws it:
 *
 * - the lots a REWARD opened (`opening_kind = REWARD`) at one broker become one group row when there are at least two;
 *   one alone stays a normal row. The table shows what the panel shows as lots of their own: with the rewards spread
 *   over the lots (MERGED) only the rewards that found no lot remain lots, so the same rule groups only those;
 * - the group sorts as one row (by its own values, its date = the first reward) and its lots stay together under it,
 *   in the same order, shown only while the group is open;
 * - selecting the group selects its lots; part of them is the mixed state;
 * - the table's totals count each lot once: never the group row beside its own lots.
 *
 * The group's figures are column sums of the backend's lots (declared frontend exception D-MF6(b), as the totals row).
 */

/** The fields of a table row this module reads. */
export interface GroupableRow {
    rowId: string;
    lotId: number;
    openingBrokerId: number;
    openingDate: string;
}

/** The id of a group row: one per broker (the panel shows one asset). Never a number, so never a lot id. */
export const REWARD_GROUP_PREFIX = 'reward-group:';
export function rewardGroupId(brokerId: number): string {
    return `${REWARD_GROUP_PREFIX}${brokerId}`;
}
export function isRewardGroupId(rowId: string): boolean {
    return rowId.startsWith(REWARD_GROUP_PREFIX);
}

/** The groups of reward lots, by group id, each with its lots in opening order (date, then lot id). Fewer than 2: no group. */
export function groupRewardLots<R extends GroupableRow>(rows: readonly R[], isRewardLot: (row: R) => boolean): Map<string, R[]> {
    const byBroker = new Map<number, R[]>();
    for (const row of rows) {
        if (!isRewardLot(row)) continue;
        const list = byBroker.get(row.openingBrokerId) ?? [];
        list.push(row);
        byBroker.set(row.openingBrokerId, list);
    }
    const groups = new Map<string, R[]>();
    for (const [brokerId, members] of [...byBroker.entries()].sort(([a], [b]) => a - b)) {
        if (members.length < 2) continue;
        members.sort((a, b) => a.openingDate.localeCompare(b.openingDate) || a.lotId - b.lotId);
        groups.set(rewardGroupId(brokerId), members);
    }
    return groups;
}

/**
 * The rows of the table, in display order: the top-level rows (every lot outside a group, and one head per group) sorted by
 * `compare` (none: their order as given, stable), each open group's lots right after its head, sorted the same way.
 */
export function arrangeRows<R extends {rowId: string}>(top: readonly R[], groups: ReadonlyMap<string, readonly R[]>, expanded: ReadonlySet<string>, compare?: (a: R, b: R) => number): R[] {
    const ordered = compare ? [...top].sort(compare) : [...top];
    const out: R[] = [];
    for (const row of ordered) {
        out.push(row);
        const members = groups.get(row.rowId);
        if (members && expanded.has(row.rowId)) out.push(...(compare ? [...members].sort(compare) : members));
    }
    return out;
}

/** The lot rows behind some table rows, each lot once: a head stands for its lots, a lot already listed is not repeated. */
export function lotRowsOf<R extends {rowId: string; lotId: number}>(rows: readonly R[], groups: ReadonlyMap<string, readonly R[]>): R[] {
    const seen = new Set<number>();
    const out: R[] = [];
    for (const row of rows) {
        for (const lotRow of groups.get(row.rowId) ?? [row]) {
            if (seen.has(lotRow.lotId)) continue;
            seen.add(lotRow.lotId);
            out.push(lotRow);
        }
    }
    return out;
}

/**
 * The lots selected after the table's selection changed from `before` to `after` (row ids): a head checked or unchecked
 * takes all its lots, a lot row only itself; the lots of the previous selection that no row shows stay as they were.
 */
export function lotsAfterTableSelection(previous: readonly number[], before: readonly string[], after: readonly string[], groups: ReadonlyMap<string, readonly GroupableRow[]>): number[] {
    const selected = new Set(previous);
    const was = new Set(before);
    const now = new Set(after);
    const lotsOf = (rowId: string): number[] => (groups.get(rowId) ?? []).map((row) => row.lotId);
    const lotOf = (rowId: string): number | null => {
        if (rowId.trim() === '') return null;
        const id = Number(rowId);
        return Number.isInteger(id) ? id : null;
    };
    for (const rowId of now) {
        if (was.has(rowId)) continue;
        if (isRewardGroupId(rowId)) lotsOf(rowId).forEach((id) => selected.add(id));
        else if (lotOf(rowId) != null) selected.add(lotOf(rowId) as number);
    }
    for (const rowId of was) {
        if (now.has(rowId)) continue;
        if (isRewardGroupId(rowId)) lotsOf(rowId).forEach((id) => selected.delete(id));
        else if (lotOf(rowId) != null) selected.delete(lotOf(rowId) as number);
    }
    return [...selected].sort((a, b) => a - b);
}

/** Whether a group is fully, partly or not at all selected. */
export type GroupSelection = 'checked' | 'partial' | 'unchecked';
export function groupSelection(members: readonly GroupableRow[], selected: ReadonlySet<number>): GroupSelection {
    const count = members.filter((row) => selected.has(row.lotId)).length;
    return count === 0 ? 'unchecked' : count === members.length ? 'checked' : 'partial';
}

/** The row ids the table shows as selected for `lotIds`: every shown lot row selected, and each head whose lots all are. */
export function tableRowIdsFor(lotIds: readonly number[], shown: readonly GroupableRow[], groups: ReadonlyMap<string, readonly GroupableRow[]>): string[] {
    const selected = new Set(lotIds);
    const ids: string[] = [];
    for (const row of shown) {
        if (isRewardGroupId(row.rowId)) {
            if (groupSelection(groups.get(row.rowId) ?? [], selected) === 'checked') ids.push(row.rowId);
        } else if (selected.has(row.lotId)) {
            ids.push(row.rowId);
        }
    }
    return ids;
}

// ---------------------------------------------------------------------------
// The rewards that entered a lot (86, D-22) — the «Rewards in lots» view
// ---------------------------------------------------------------------------

/** A reward spread over the lots its broker held the day before: the units one lot took (a `REWARD_MERGE` row of `lot_events`). */
export interface RewardEntry {
    transactionId: number;
    date: string;
    quantity: number | null;
}

/** The fields of a lot event this module reads. */
export interface RewardEventRow {
    lot_id: number;
    kind: string;
    transaction_id: number;
    date: string;
    quantity: unknown;
}

/** The rewards that entered each lot, by lot id, in date order. Empty unless the rewards join the lots. */
export function rewardEntriesByLot(events: readonly RewardEventRow[], toNumber: (value: unknown) => number | null): Map<number, RewardEntry[]> {
    const byLot = new Map<number, RewardEntry[]>();
    for (const event of events) {
        if (event.kind !== 'REWARD_MERGE') continue;
        const list = byLot.get(event.lot_id) ?? [];
        list.push({transactionId: event.transaction_id, date: event.date, quantity: toNumber(event.quantity)});
        byLot.set(event.lot_id, list);
    }
    for (const list of byLot.values()) list.sort((a, b) => a.date.localeCompare(b.date) || a.transactionId - b.transactionId);
    return byLot;
}

/** The id of an entry's row: never a number, so never a lot id, and never a group id. */
export function rewardEntryRowId(lotId: number, transactionId: number): string {
    return `reward-entry:${lotId}:${transactionId}`;
}

/** The rows in display order with, right after each open lot, the rows of the rewards that entered it, in date order. */
export function withRewardEntries<R extends {rowId: string}>(rows: readonly R[], entriesOf: (row: R) => readonly R[], expanded: ReadonlySet<string>): R[] {
    return rows.flatMap((row) => (expanded.has(row.rowId) ? [row, ...entriesOf(row)] : [row]));
}
