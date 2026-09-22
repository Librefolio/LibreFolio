import type {ResolvedOp} from './txPayloadHelpers';

export interface BulkDisplayRow {
    tempId: string;
    pairedWith?: string;
    txId?: number;
    inaccessible?: boolean;
    fields: {date: string};
}

export interface BulkIssueRow extends BulkDisplayRow {
    fields: {
        broker_id: number;
        asset_id: number | null;
        type: string;
        date: string;
        quantity: string;
        cash: {code: string; amount: string} | null;
    };
}

export interface IdentifiedBulkOp extends ResolvedOp {
    tempId: string;
    partnerTempId?: string;
}

export type BulkOperationIndex = Map<string, string[]>;

export interface BulkIssue {
    operation: string;
    index: number;
    ref_id?: number | null;
    code?: string | null;
    params?: Record<string, unknown> | null;
}

export interface BulkIssueSnapshotEntry {
    before: BulkIssueRow | null;
    after: BulkIssueRow | null;
    /** State before an atomic split/promote, if this row also has a CUD operation. */
    ordinaryAfter?: BulkIssueRow | null;
    /** Atomic-only state when a queued update failed (e.g. split succeeded, edit failed). */
    atomicFallback?: BulkIssueRow | null;
    draft: BulkIssueRow;
    operationKeys: string[];
}

export interface BulkBatchResult {
    operation?: string;
    index?: number;
    status?: string;
}

function compareText(a: string, b: string): number {
    return a < b ? -1 : a > b ? 1 : 0;
}

/** A pair is one display group: earliest leg first, latest leg second, stable ID last.
 *  The comparator never changes ledger order or the From/To orientation inside a group. */
export function createBulkDateComparator<T extends BulkDisplayRow>(rows: readonly T[]): (a: T, b: T) => number {
    const dates = new Map<string, string[]>();
    for (const row of rows) {
        const id = row.pairedWith ?? row.tempId;
        const group = dates.get(id) ?? [];
        if (row.fields.date) group.push(row.fields.date);
        dates.set(id, group);
    }
    const bounds = new Map(
        [...dates].map(([id, group]) => {
            const ordered = [...group].sort(compareText);
            return [id, [ordered[0] ?? '', ordered[ordered.length - 1] ?? '']] as const;
        }),
    );
    return (a, b) => {
        const aDates = bounds.get(a.tempId) ?? ['', ''];
        const bDates = bounds.get(b.tempId) ?? ['', ''];
        return compareText(aDates[0], bDates[0]) || compareText(aDates[1], bDates[1]) || (a.txId ?? Number.MAX_SAFE_INTEGER) - (b.txId ?? Number.MAX_SAFE_INTEGER) || compareText(a.tempId, b.tempId);
    };
}

/** Numbers belong to the sorted workspace, not an API array, file or current page.
 *  Filters may leave gaps; each visible group and its hidden legs retain the same label. */
export function buildBulkRowLabels(rows: readonly BulkDisplayRow[], visibleRows: readonly BulkDisplayRow[]): Map<string, string> {
    const partners = new Map<string, BulkDisplayRow[]>();
    for (const row of rows) {
        if (!row.pairedWith) continue;
        const group = partners.get(row.pairedWith) ?? [];
        group.push(row);
        partners.set(row.pairedWith, group);
    }
    const labels = new Map<string, string>();
    visibleRows.forEach((row, index) => {
        const children = partners.get(row.tempId) ?? [];
        labels.set(row.tempId, `${index + 1}${children.length > 0 ? 'a' : ''}`);
        children.forEach((child, childIndex) => labels.set(child.tempId, `${index + 1}${String.fromCharCode(98 + childIndex)}`));
    });
    return labels;
}

/** Mirror buildBatchPayload's actual emissions, not another traversal of the workspace.
 *  Partner-only updates and mixed promotes must consume exactly the indices they send. */
export function buildBulkOperationIndex(resolved: readonly IdentifiedBulkOp[], commands: {splits?: readonly string[][]; promotes?: readonly string[][]} = {}): BulkOperationIndex {
    const map: BulkOperationIndex = new Map();
    const counters = {create: 0, update: 0, delete: 0};
    for (const op of resolved) {
        const append = (present: boolean, tempId?: string) => {
            if (!present) return;
            const key = `${op.intent}:${counters[op.intent]++}`;
            if (tempId) map.set(key, [tempId]);
        };
        if (op.intent === 'delete') {
            append(op.deleteId != null, op.tempId);
            append(op.partnerDeleteId != null, op.partnerTempId);
        } else {
            append(!!op.payload, op.tempId);
            append(!!op.partnerPayload, op.partnerTempId);
        }
    }
    commands.splits?.forEach((ids, index) => map.set(`split:${index}`, [...ids]));
    commands.promotes?.forEach((ids, index) => map.set(`promote:${index}`, [...ids]));
    return map;
}

/** Failed creates never contributed; failed edits/deletes leave the original ledger row.
 *  A rolled-back commit labels successfully simulated operations as "simulated". */
export function settleBulkIssueSnapshot(entries: readonly BulkIssueSnapshotEntry[], results: readonly BulkBatchResult[]): BulkIssueRow[] {
    const applied = new Set(results.filter((result) => result.status === 'success' || result.status === 'simulated').map((result) => `${result.operation}:${result.index}`));
    return entries.flatMap((entry) => {
        const ordinaryKeys = entry.operationKeys.filter((key) => !key.startsWith('split:') && !key.startsWith('promote:'));
        const ordinaryApplied = ordinaryKeys.some((key) => applied.has(key));
        const atomicApplied = entry.operationKeys.some((key) => (key.startsWith('split:') || key.startsWith('promote:')) && applied.has(key));
        let row = entry.before;
        if (ordinaryApplied) row = entry.ordinaryAfter === undefined ? entry.after : entry.ordinaryAfter;
        if (atomicApplied) {
            row = ordinaryKeys.length === 0 || ordinaryApplied ? entry.after : entry.atomicFallback === undefined ? entry.before : entry.atomicFallback;
        }
        return row ? [row] : [];
    });
}

export function isBulkBalanceIssue(issue: BulkIssue): boolean {
    return issue.code === 'balanceCashNegative' || issue.code === 'balanceAssetNegative';
}

/** A balance index is only the last reducer, not the complete end-of-day group.
 *  Group strictly by the backend's broker/date/dimension; never infer a missing group
 *  from a payload index or include unrelated brokers/currencies on the same day. */
export function resolveBulkIssueRows(issue: BulkIssue, rows: readonly BulkIssueRow[], operationIndex: ReadonlyMap<string, readonly string[]>): BulkIssueRow[] {
    if (isBulkBalanceIssue(issue)) {
        const {brokerId, date, currency, assetId} = issue.params ?? {};
        if (typeof brokerId !== 'number' || typeof date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return [];
        if (issue.code === 'balanceCashNegative' && (typeof currency !== 'string' || !currency)) return [];
        if (issue.code === 'balanceAssetNegative' && typeof assetId !== 'number') return [];
        return rows.filter((row) => {
            if (row.inaccessible || row.fields.broker_id !== brokerId || row.fields.date !== date) return false;
            if (issue.code === 'balanceCashNegative') {
                const amount = Number(row.fields.cash?.amount ?? 0);
                return row.fields.cash?.code === currency && Number.isFinite(amount) && amount !== 0;
            }
            const quantity = Number(row.fields.quantity);
            return row.fields.asset_id === assetId && Number.isFinite(quantity) && quantity !== 0;
        });
    }
    const ids = new Set(operationIndex.get(`${issue.operation}:${issue.index}`) ?? []);
    if (ids.size > 0) return rows.filter((row) => ids.has(row.tempId));
    if (issue.ref_id != null) return rows.filter((row) => row.txId === issue.ref_id);
    return [];
}
