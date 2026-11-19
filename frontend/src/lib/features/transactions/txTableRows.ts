/**
 * The rows of the transactions table (`TransactionsTable.svelte`) and their pages, as pure functions.
 *
 * The table builds its display rows (pairs adjacent, ghost partners), folds the linked charges under their parent
 * (project 66, lot F5) and slices them into pages here, so the rules can be tested without mounting the table.
 */
import type {TXReadItem} from './types';

/** Display row = TXReadItem + decoration metadata for adjacency rendering. */
export interface DisplayRow {
    tx: TXReadItem;
    /** True when partner is rendered for context (not in main filter set). */
    isGhost: boolean;
    /** True when this row is the receiver half of a linked pair. */
    isReceiver: boolean;
    /** Pair anchor id (giver tx id). null when not part of a pair. */
    pairAnchorId: number | null;
    /** Bug7-fix: stable sort index for flat mode — preserves date-desc order
     *  while keeping paired rows adjacent (giver then receiver). */
    sortIndex: number;
    /** A parent's linked charges in the list (F5); 0 for any other row. */
    chargeCount?: number;
    /** A charge shown under its open parent: the parent's id; `null` for any other row. */
    chargeOfId?: number | null;
    /** A FEE or TAX linked to a parent: it carries `↳` and 🔗. */
    isChargeRow?: boolean;
    /** The parent of a charge shown under it: the filters read it, so the charge follows its parent. */
    followTx?: TXReadItem | null;
}

/** How `foldCharges` folds. */
export interface FoldOptions {
    /** Folded (no sort, no filter on the type): the charges sit under their parent. */
    folded: boolean;
    /** The parents shown open. */
    expandedIds: ReadonlySet<number>;
    /** The active filters, read on a parent or a row on its own; always true without filters. */
    passes: (row: DisplayRow) => boolean;
}

/** The parent a row is linked to, when it is a charge. */
function parentIdOf(row: DisplayRow): number | null {
    const id = row.tx.parent_transaction_id ?? 0;
    return id > 0 ? id : null;
}

/**
 * Fold the linked charges under their parent (F5), after the pairs are built.
 *  - Flat (`folded: false`): every row stays, in its order; charges are marked and parents count their charges.
 *  - Folded: the filters read the parents and the rows on their own; a charge follows its parent, shown right after it
 *    only while the parent is open. A charge whose parent fails the filters is a row on its own when it passes them.
 */
export function foldCharges(rows: DisplayRow[], {folded, expandedIds, passes}: FoldOptions): DisplayRow[] {
    const present = new Map<number, DisplayRow>();
    for (const row of rows) if (!row.isGhost) present.set(row.tx.id, row);
    const byParent = new Map<number, DisplayRow[]>();
    for (const row of rows) {
        const parentId = parentIdOf(row);
        if (parentId === null || !present.has(parentId)) continue;
        const list = byParent.get(parentId);
        if (list) list.push(row);
        else byParent.set(parentId, [row]);
    }
    const plain = (row: DisplayRow): DisplayRow => ({...row, isChargeRow: parentIdOf(row) !== null, chargeCount: byParent.get(row.tx.id)?.length ?? 0, chargeOfId: null, followTx: null});
    if (!folded) return rows.map(plain);

    const verdict = new Map<DisplayRow, boolean>();
    const ok = (row: DisplayRow): boolean => {
        let value = verdict.get(row);
        if (value === undefined) {
            value = passes(row);
            verdict.set(row, value);
        }
        return value;
    };
    const out: DisplayRow[] = [];
    for (const row of rows) {
        const parentId = parentIdOf(row);
        const parent = parentId === null ? undefined : present.get(parentId);
        if (parent) {
            if (!ok(parent) && ok(row)) out.push(plain(row));
            continue;
        }
        if (!ok(row)) continue;
        out.push(plain(row));
        const charges = byParent.get(row.tx.id);
        if (charges && expandedIds.has(row.tx.id)) {
            for (const charge of charges) out.push({...charge, isChargeRow: true, chargeCount: 0, chargeOfId: row.tx.id, followTx: row.tx});
        }
    }
    return out;
}

/** A row that never opens a page: the receiver of a pair, or a charge under its open parent. */
function follows(row: DisplayRow): boolean {
    return row.isReceiver || row.chargeOfId != null;
}

/**
 * Slice the rows into pages.
 *  - Grouped mode (`grouped`): a page closes only before a row that does not follow the previous one, so the receiver
 *    half of a pair stays with its giver even when the page is full (that page holds `pageSize + 1` rows).
 *  - Flat mode: standard fixed-size pagination — every row is independent
 *    and ordering wins over pair coupling. `pageSize <= 0` ⇒ single page.
 * In both, a charge shown under its open parent never opens a page: it stays with its group, overflowing like a
 * receiver (F5).
 */
export function paginateRows(rows: DisplayRow[], pageSize: number, grouped: boolean): DisplayRow[][] {
    const result: DisplayRow[][] = [];
    if (!grouped) {
        if (pageSize <= 0) return rows.length > 0 ? [rows] : [[]];
        let page: DisplayRow[] = [];
        for (const row of rows) {
            if (page.length >= pageSize && row.chargeOfId == null) {
                result.push(page);
                page = [];
            }
            page.push(row);
        }
        if (page.length > 0) result.push(page);
        if (result.length === 0) result.push([]);
        return result;
    }
    // Grouped mode — pair-never-split paginator.
    let buf: DisplayRow[] = [];
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const isPair = row.pairAnchorId != null;
        const nextIsPartner = isPair && i + 1 < rows.length && rows[i + 1].pairAnchorId === row.pairAnchorId && !row.isReceiver;
        const wouldExceed = buf.length >= pageSize;
        const wouldSplitPair = nextIsPartner && buf.length + 1 > pageSize;
        if ((wouldExceed && !follows(row)) || wouldSplitPair) {
            result.push(buf);
            buf = [];
        }
        buf.push(row);
    }
    if (buf.length > 0) result.push(buf);
    if (result.length === 0) result.push([]);
    return result;
}
