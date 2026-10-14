// @vitest-environment node
import {describe, expect, it} from 'vitest';
import {buildBulkOperationIndex, buildBulkRowLabels, createBulkDateComparator, resolveBulkIssueRows, serializeOps, settleBulkIssueSnapshot, type BulkBatchResult, type BulkDisplayRow, type BulkIssue, type BulkIssueRow, type BulkIssueSnapshotEntry, type IdentifiedBulkOp} from './bulkDisplay';

const displayRow = (tempId: string, date: string, extra: Partial<BulkDisplayRow> = {}): BulkDisplayRow => ({
    tempId,
    fields: {date},
    ...extra,
});

const issueRow = (
    tempId: string,
    overrides: Partial<Omit<BulkIssueRow, 'tempId' | 'fields'>> & {
        broker_id?: number;
        asset_id?: number | null;
        type?: string;
        date?: string;
        quantity?: string;
        cash?: {code: string; amount: string} | null;
        inaccessible?: boolean;
    } = {},
): BulkIssueRow => ({
    tempId,
    pairedWith: overrides.pairedWith,
    txId: overrides.txId,
    inaccessible: overrides.inaccessible,
    fields: {
        broker_id: overrides.broker_id ?? 1,
        asset_id: overrides.asset_id ?? null,
        type: overrides.type ?? 'BUY',
        date: overrides.date ?? '2024-01-01',
        quantity: overrides.quantity ?? '1',
        cash: overrides.cash ?? null,
    },
});

const byTempId = <T extends {tempId: string}>(rows: readonly T[]) => new Map(rows.map((row) => [row.tempId, row] as const));

describe('createBulkDateComparator', () => {
    it('sorts grouped rows by earliest leg, then latest leg, then stable row id without mutating input rows', () => {
        const rows = [
            displayRow('g2', '2024-05-02'),
            displayRow('g1', '2024-05-01'),
            displayRow('g1-partner', '2024-05-04', {pairedWith: 'g1'}),
            displayRow('g3', '2024-05-01'),
            displayRow('g3-partner', '2024-05-04', {pairedWith: 'g3'}),
            displayRow('g2-partner', '2024-05-07', {pairedWith: 'g2'}),
        ] as const;
        const rowsSnapshot = JSON.parse(JSON.stringify(rows)) as typeof rows;
        const visible = [rows[0], rows[1], rows[3]];
        const visibleSnapshot = JSON.parse(JSON.stringify(visible)) as typeof visible;

        const comparator = createBulkDateComparator(rows);
        expect([...visible].sort(comparator).map((row) => row.tempId)).toEqual(['g1', 'g3', 'g2']);
        expect(rows).toEqual(rowsSnapshot);
        expect(visible).toEqual(visibleSnapshot);
    });

    // C4 — creation order. New rows have no txId and a random UUID tempId, so for two new
    // rows on the same date the tempId tie-break is a coin toss. The contract: earliest date
    // → latest date → txId (missing = MAX) → createdSeq (missing = MAX) → tempId.
    // `createdSeq` goes through `extra` with a cast until BulkDisplayRow declares it.
    const seq = (createdSeq: number) => ({createdSeq}) as Partial<BulkDisplayRow>;
    const sortVisible = (rows: readonly BulkDisplayRow[], visible: readonly BulkDisplayRow[] = rows) => [...visible].sort(createBulkDateComparator(rows)).map((row) => row.tempId);

    it('U1: same-date new rows keep their creation order (createdSeq), even when their tempIds sort the other way', () => {
        const zFirst = displayRow('z-first', '2024-05-01', seq(0));
        const aSecond = displayRow('a-second', '2024-05-01', seq(1));

        // Both input orders: the verdict must come from createdSeq, not from where a row sits.
        expect(sortVisible([zFirst, aSecond])).toEqual(['z-first', 'a-second']);
        expect(sortVisible([aSecond, zFirst])).toEqual(['z-first', 'a-second']);
    });

    it('U2a: on the same date a saved row (txId) still precedes a new one, whatever their createdSeq and tempId', () => {
        const saved = displayRow('z-saved', '2024-05-01', {txId: 42, ...seq(7)});
        const fresh = displayRow('a-new', '2024-05-01', seq(0));

        expect(sortVisible([fresh, saved])).toEqual(['z-saved', 'a-new']);
        expect(sortVisible([saved, fresh])).toEqual(['z-saved', 'a-new']);
    });

    it('U2b: rows without createdSeq fall back to tempId, and never jump ahead of rows that have one (missing = MAX)', () => {
        const b = displayRow('b-row', '2024-05-01');
        const a = displayRow('a-row', '2024-05-01');
        expect(sortVisible([b, a])).toEqual(['a-row', 'b-row']);

        const rows = [displayRow('d-noseq', '2024-05-01'), displayRow('b-seq1', '2024-05-01', seq(1)), displayRow('c-noseq', '2024-05-01'), displayRow('a-seq0', '2024-05-01', seq(0))];
        expect(sortVisible(rows)).toEqual(['a-seq0', 'b-seq1', 'c-noseq', 'd-noseq']);
    });

    it("U2c: a pair is placed by its visible row's createdSeq; the hidden partner never enters the comparison", () => {
        // The partner's createdSeq (9) would put the pair last, its visible row's (3) puts it first.
        const pair = displayRow('a-pair', '2024-05-01', seq(3));
        const partner = displayRow('a-pair-leg', '2024-05-01', {pairedWith: 'a-pair', ...seq(9)});
        const single = displayRow('b-single', '2024-05-01', seq(5));
        const rows = [single, partner, pair];

        expect(sortVisible(rows, [single, pair])).toEqual(['a-pair', 'b-single']);
        expect(sortVisible(rows, [pair, single])).toEqual(['a-pair', 'b-single']);
    });

    it('U2d: different dates sort by date whatever the createdSeq (and the tempId) says', () => {
        const late = displayRow('a-late', '2024-05-03', seq(0));
        const early = displayRow('z-early', '2024-05-01', seq(9));

        expect(sortVisible([late, early])).toEqual(['z-early', 'a-late']);
        expect(sortVisible([early, late])).toEqual(['z-early', 'a-late']);
    });

    it('U2e: sorting with createdSeq mutates neither the workspace rows nor the visible rows', () => {
        const rows = [displayRow('n2', '2024-05-01', seq(2)), displayRow('saved', '2024-05-01', {txId: 5, ...seq(0)}), displayRow('n1', '2024-05-01', seq(1)), displayRow('pair', '2024-04-30', seq(3)), displayRow('pair-leg', '2024-05-02', {pairedWith: 'pair', ...seq(4)})] as const;
        const visible = [rows[0], rows[1], rows[2], rows[3]];
        const rowsSnapshot = JSON.parse(JSON.stringify(rows)) as typeof rows;
        const visibleSnapshot = JSON.parse(JSON.stringify(visible)) as typeof visible;

        const comparator = createBulkDateComparator(rows);
        const first = [...visible].sort(comparator).map((row) => row.tempId);
        const second = [...visible].sort(comparator).map((row) => row.tempId);

        expect(first).toEqual(['pair', 'saved', 'n1', 'n2']);
        expect(second).toEqual(first);
        expect(rows).toEqual(rowsSnapshot);
        expect(visible).toEqual(visibleSnapshot);
    });
});

describe('buildBulkRowLabels', () => {
    it('labels visible workspace rows and their hidden partners from workspace order, not source order', () => {
        const rows = [displayRow('partner-a', '2024-02-01', {pairedWith: 'main-a'}), displayRow('main-b', '2024-02-03'), displayRow('main-a', '2024-02-02'), displayRow('partner-b', '2024-02-03', {pairedWith: 'main-b'})] as const;
        const visibleRows = [rows[2], rows[1]];
        const rowsSnapshot = JSON.parse(JSON.stringify(rows)) as typeof rows;
        const visibleSnapshot = JSON.parse(JSON.stringify(visibleRows)) as typeof visibleRows;

        const labels = buildBulkRowLabels(rows, visibleRows);

        expect([...labels.entries()]).toEqual([
            ['main-a', '1a'],
            ['partner-a', '1b'],
            ['main-b', '2a'],
            ['partner-b', '2b'],
        ]);
        expect(rows).toEqual(rowsSnapshot);
        expect(visibleRows).toEqual(visibleSnapshot);
    });
});

describe('buildBulkOperationIndex', () => {
    it('indexes only the payloads and deletions that were actually emitted, plus explicit split/promote ids', () => {
        const resolved: IdentifiedBulkOp[] = [
            {intent: 'create', tempId: 'create-main', payload: {main: true}, partnerTempId: 'create-partner', partnerPayload: {partner: true}},
            {intent: 'update', tempId: 'update-main', partnerTempId: 'update-partner', partnerPayload: {partnerOnly: true}},
            {intent: 'delete', tempId: 'delete-main', deleteId: 10, partnerTempId: 'delete-partner', partnerDeleteId: 11},
            {intent: 'create', tempId: 'promote-child', payload: {child: true}},
        ];
        const snapshot = JSON.parse(JSON.stringify(resolved)) as typeof resolved;

        const index = buildBulkOperationIndex(resolved, {
            splits: [['split-left', 'split-right']],
            promotes: [['promote-child']],
        });

        expect([...index.entries()]).toEqual([
            ['create:0', ['create-main']],
            ['create:1', ['create-partner']],
            ['update:0', ['update-partner']],
            ['delete:0', ['delete-main']],
            ['delete:1', ['delete-partner']],
            ['create:2', ['promote-child']],
            ['split:0', ['split-left', 'split-right']],
            ['promote:0', ['promote-child']],
        ]);
        expect(resolved).toEqual(snapshot);
    });
});

describe('settleBulkIssueSnapshot', () => {
    it('keeps successful and simulated ordinary operations, drops failed creates and deleted rows, and falls back to the saved row on failed edits/deletes', () => {
        const entries: BulkIssueSnapshotEntry[] = [
            {
                before: null,
                after: issueRow('create-ok', {type: 'BUY', date: '2024-06-01'}),
                draft: issueRow('create-ok', {type: 'BUY', date: '2024-06-01'}),
                operationKeys: ['create:0'],
            },
            {
                before: null,
                after: issueRow('create-fail', {type: 'SELL', date: '2024-06-01'}),
                draft: issueRow('create-fail', {type: 'SELL', date: '2024-06-01'}),
                operationKeys: ['create:1'],
            },
            {
                before: issueRow('update-ok-before', {type: 'BUY', date: '2024-06-02'}),
                after: issueRow('update-ok-after', {type: 'SELL', date: '2024-06-02'}),
                ordinaryAfter: issueRow('update-ok-after', {type: 'SELL', date: '2024-06-02'}),
                draft: issueRow('update-ok-after', {type: 'SELL', date: '2024-06-02'}),
                operationKeys: ['update:0'],
            },
            {
                before: issueRow('update-fail-before', {type: 'DIVIDEND', date: '2024-06-03'}),
                after: issueRow('update-fail-after', {type: 'WITHDRAWAL', date: '2024-06-03'}),
                ordinaryAfter: issueRow('update-fail-after', {type: 'WITHDRAWAL', date: '2024-06-03'}),
                draft: issueRow('update-fail-after', {type: 'WITHDRAWAL', date: '2024-06-03'}),
                operationKeys: ['update:1'],
            },
            {
                before: issueRow('delete-ok', {type: 'DEPOSIT', date: '2024-06-04'}),
                after: null,
                ordinaryAfter: null,
                draft: issueRow('delete-ok', {type: 'DEPOSIT', date: '2024-06-04'}),
                operationKeys: ['delete:0'],
            },
            {
                before: issueRow('delete-fail', {type: 'CASH_TRANSFER', date: '2024-06-05'}),
                after: null,
                ordinaryAfter: null,
                draft: issueRow('delete-fail', {type: 'CASH_TRANSFER', date: '2024-06-05'}),
                operationKeys: ['delete:1'],
            },
        ];
        const results: BulkBatchResult[] = [
            {operation: 'create', index: 0, status: 'success'},
            {operation: 'update', index: 0, status: 'simulated'},
            {operation: 'delete', index: 0, status: 'success'},
        ];

        const settled = settleBulkIssueSnapshot(entries, results);
        const rows = byTempId(settled);

        expect([...rows.keys()]).toEqual(['create-ok', 'update-ok-after', 'update-fail-before', 'delete-fail']);
        expect(rows.get('create-ok')?.fields.type).toBe('BUY');
        expect(rows.get('update-ok-after')?.fields.type).toBe('SELL');
        expect(rows.get('update-fail-before')?.fields.type).toBe('DIVIDEND');
        expect(rows.get('delete-fail')?.fields.type).toBe('CASH_TRANSFER');
    });

    it('uses the atomic split fallback when the split succeeds but the paired edit does not', () => {
        const entries: BulkIssueSnapshotEntry[] = [
            {
                before: issueRow('split-row', {type: 'CASH_TRANSFER', quantity: '0', cash: {code: 'USD', amount: '-12'}, date: '2024-07-01'}),
                after: issueRow('split-row', {type: 'DEPOSIT', quantity: '0', cash: {code: 'USD', amount: '-12'}, date: '2024-07-01'}),
                ordinaryAfter: issueRow('split-row', {type: 'DEPOSIT', quantity: '0', cash: {code: 'USD', amount: '-12'}, date: '2024-07-01'}),
                atomicFallback: issueRow('split-row', {type: 'WITHDRAWAL', quantity: '0', cash: {code: 'USD', amount: '-12'}, date: '2024-07-01'}),
                draft: issueRow('split-row', {type: 'DEPOSIT', quantity: '0', cash: {code: 'USD', amount: '-12'}, date: '2024-07-01'}),
                operationKeys: ['update:0', 'split:0'],
            },
        ];
        const results: BulkBatchResult[] = [{operation: 'split', index: 0, status: 'success'}];

        const settled = settleBulkIssueSnapshot(entries, results);
        expect(settled).toHaveLength(1);
        expect(settled[0].fields.type).toBe('WITHDRAWAL');
    });
});

describe('resolveBulkIssueRows', () => {
    it('collects same-broker same-day cash rows for the requested currency, including positive hidden FX legs, and excludes other brokers, days, currencies, zero rows, and inaccessible rows', () => {
        const rows = [
            issueRow('usd-negative', {broker_id: 4, date: '2024-08-01', cash: {code: 'USD', amount: '-10'}, quantity: '1'}),
            issueRow('usd-positive', {broker_id: 4, date: '2024-08-01', cash: {code: 'USD', amount: '7'}, quantity: '1'}),
            issueRow('usd-zero', {broker_id: 4, date: '2024-08-01', cash: {code: 'USD', amount: '0'}, quantity: '1'}),
            issueRow('eur-row', {broker_id: 4, date: '2024-08-01', cash: {code: 'EUR', amount: '-8'}, quantity: '1'}),
            issueRow('other-broker', {broker_id: 9, date: '2024-08-01', cash: {code: 'USD', amount: '-9'}, quantity: '1'}),
            issueRow('next-day', {broker_id: 4, date: '2024-08-02', cash: {code: 'USD', amount: '-9'}, quantity: '1'}),
            issueRow('inaccessible', {broker_id: 4, date: '2024-08-01', cash: {code: 'USD', amount: '-9'}, quantity: '1', inaccessible: true}),
        ];
        const issue: BulkIssue = {operation: 'update', index: 0, code: 'balanceCashNegative', params: {brokerId: 4, date: '2024-08-01', currency: 'USD'}};

        expect(resolveBulkIssueRows(issue, rows, new Map()).map((row) => row.tempId)).toEqual(['usd-negative', 'usd-positive']);
    });

    it('groups asset-negative rows by asset id, not by row index, and keeps both negative and positive legs from the same workspace group', () => {
        const rows = [
            issueRow('asset-negative', {broker_id: 5, date: '2024-08-03', asset_id: 77, quantity: '-5', cash: null}),
            issueRow('asset-positive', {broker_id: 5, date: '2024-08-03', asset_id: 77, quantity: '2', cash: null}),
            issueRow('asset-zero', {broker_id: 5, date: '2024-08-03', asset_id: 77, quantity: '0', cash: null}),
            issueRow('other-asset', {broker_id: 5, date: '2024-08-03', asset_id: 88, quantity: '3', cash: null}),
            issueRow('other-broker', {broker_id: 9, date: '2024-08-03', asset_id: 77, quantity: '-3', cash: null}),
            issueRow('next-day', {broker_id: 5, date: '2024-08-04', asset_id: 77, quantity: '-3', cash: null}),
            issueRow('inaccessible', {broker_id: 5, date: '2024-08-03', asset_id: 77, quantity: '-3', cash: null, inaccessible: true}),
        ];
        const issue: BulkIssue = {operation: 'update', index: 0, code: 'balanceAssetNegative', params: {brokerId: 5, date: '2024-08-03', assetId: 77}};

        expect(resolveBulkIssueRows(issue, rows, new Map()).map((row) => row.tempId)).toEqual(['asset-negative', 'asset-positive']);
    });

    it('returns no balance rows for malformed balance metadata instead of guessing an index', () => {
        const rows = [issueRow('usd-negative', {broker_id: 4, date: '2024-08-01', cash: {code: 'USD', amount: '-10'}, quantity: '1'})];
        const issue: BulkIssue = {operation: 'update', index: 0, code: 'balanceCashNegative', params: {brokerId: 4, date: '2024-08', currency: 'USD'}};

        expect(resolveBulkIssueRows(issue, rows, new Map())).toEqual([]);
    });

    it('uses the emitted operation index first for non-balance issues, then the ref_id fallback when no opmap entry exists', () => {
        const rows = [issueRow('mapped-main', {txId: 71, date: '2024-09-01'}), issueRow('mapped-partner', {txId: 72, date: '2024-09-01'}), issueRow('by-ref', {txId: 500, date: '2024-09-01'})];
        const issue: BulkIssue = {operation: 'update', index: 3, ref_id: 500, code: 'someOtherIssue', params: null};
        const opMap = new Map<string, readonly string[]>([['update:3', ['mapped-main', 'mapped-partner']]]);

        expect(resolveBulkIssueRows(issue, rows, opMap).map((row) => row.tempId)).toEqual(['mapped-main', 'mapped-partner']);
        expect(resolveBulkIssueRows({...issue, index: 4}, rows, new Map()).map((row) => row.tempId)).toEqual(['by-ref']);
    });
});

// ---------------------------------------------------------------------------
// serializeOps — the key the close guard compares
// ---------------------------------------------------------------------------

/** An editor row's fields (`DraftFields`, local to TransactionBulkModal). */
type GuardFields = {
    broker_id: number;
    asset_id: number | null;
    type: string;
    date: string;
    quantity: string;
    cash: {code: string; amount: string} | null;
    tags: string[];
    description: string;
    asset_event_id: number | null;
    cost_basis_override: {code: string; amount: string} | null;
    cost_basis_mode: 'auto' | 'manual' | null;
};

/** An editor row as the close guard receives it: the shape of `PendingOp`, also local to the component. */
type GuardRow = ({op: 'create'} | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}) & {
    tempId: string;
    createdSeq: number;
    fields: GuardFields;
    pairedWith?: string;
    link_uuid?: string | null;
};

const fxLeg = (code: string, amount: string): GuardFields => ({
    broker_id: 7,
    asset_id: null,
    type: 'FX_CONVERSION',
    date: '2024-01-03',
    quantity: '0',
    cash: {code, amount},
    tags: ['fx', 'q1'],
    description: 'EUR to USD',
    asset_event_id: null,
    cost_basis_override: null,
    cost_basis_mode: null,
});

const cashIn = (amount: string, description: string): GuardFields => ({...fxLeg('EUR', amount), type: 'DEPOSIT', tags: [], description});

/** A saved row as `editOpFromTx` builds it: `addedViaPicker` is always there, set or not. */
const savedRow = (txId: number, tempId: string, createdSeq: number, fields: GuardFields): GuardRow => ({op: 'edit', tempId, createdSeq, txId, fields, markedDelete: false, addedViaPicker: undefined});

/** A new row as `createOpEmpty` builds it. */
const newRow = (tempId: string, createdSeq: number, fields: GuardFields): GuardRow => ({op: 'create', tempId, createdSeq, fields, link_uuid: null});

/** A saved FX pair as `collapsePairedOps` leaves it: the paying leg visible, the receiving leg hidden and pointing at it, one link_uuid on both. */
function savedPair(txIds: [number, number], tempIds: [string, string], createdSeq: number, link: string): GuardRow[] {
    return [
        {...savedRow(txIds[0], tempIds[0], createdSeq, fxLeg('EUR', '-400')), link_uuid: link},
        {...savedRow(txIds[1], tempIds[1], createdSeq + 1, fxLeg('USD', '440')), pairedWith: tempIds[0], link_uuid: link},
    ];
}

const MAIN = 0;
const PARTNER = 1;
const NEW = 2;

/**
 * One opening of the editor: the saved pair 101 (visible) + 102 (its hidden partner), then a row the user added.
 * The parameters are what a reset regenerates on the saved rows; the new row it never touches.
 */
function workspace({main = 'main-1', partner = 'partner-1', createdSeq = 0, link = 'link-1'} = {}): GuardRow[] {
    return [...savedPair([101, 102], [main, partner], createdSeq, link), newRow('new-1', 2, cashIn('50', 'top-up'))];
}

/** `rows` with the row at `index` swapped for `change(row)`; the input is never mutated. */
const replaceRow = (rows: readonly GuardRow[], index: number, change: (row: GuardRow) => GuardRow): GuardRow[] => rows.map((row, i) => (i === index ? change(row) : row));

/**
 * The hidden partner as Pass 2 of `collapsePairedOps` writes it — `{op, txId, markedDelete, tempId, createdSeq,
 * fields, pairedWith, link_uuid}` — plus the `addedViaPicker` key `editOpFromTx` gives it: the same keys and
 * values, in another order.
 */
function inPass2Order(row: GuardRow): GuardRow {
    if (row.op !== 'edit') throw new Error('Pass 2 rebuilds saved partners only');
    return {op: 'edit', txId: row.txId, markedDelete: row.markedDelete, tempId: row.tempId, createdSeq: row.createdSeq, fields: row.fields, pairedWith: row.pairedWith, link_uuid: row.link_uuid, addedViaPicker: row.addedViaPicker};
}

/** The same value with every object's keys inserted in reverse order, at every depth; arrays keep their order. */
function reverseKeyOrder<T>(value: T): T {
    if (Array.isArray(value)) return value.map((item: unknown) => reverseKeyOrder(item)) as T;
    if (value === null || typeof value !== 'object') return value;
    return Object.fromEntries(
        Object.entries(value)
            .reverse()
            .map(([name, item]) => [name, reverseKeyOrder(item)]),
    ) as T;
}

const guardKey = (rows: readonly GuardRow[]): string => serializeOps(rows);

describe("serializeOps — the close guard's key", () => {
    // The editor asks «Discard changes?» when serializeOps(ops) differs from the key taken when its rows were
    // seeded. A reset rebuilds the saved rows from the ledger under new identities: nothing the user can see
    // changes, so the key must not change either — and every real change must still change it.
    // The contract: per row, tempId and createdSeq dropped; pairedWith read as the row it points at (`tx:<txId>`
    // for a saved row, `new:<tempId>` for a new one, which no reset regenerates); link_uuid read as the sorted
    // references of the rows sharing it, null when absent; object keys sorted at every depth, array order kept.

    describe('rows a reset regenerates: the same content, so the same key', () => {
        it('1: both halves of a saved pair under new tempIds and createdSeq, the partner re-pointed at the new visible row', () => {
            const reset = workspace({main: 'main-2', partner: 'partner-2', createdSeq: 10});
            expect(reset[PARTNER].pairedWith, 'premise: the partner follows its regenerated row').toBe('main-2');

            expect(guardKey(reset)).toBe(guardKey(workspace()));
        });

        it('2: both halves of a saved pair under a fresh link_uuid', () => {
            expect(guardKey(workspace({link: 'link-2'}))).toBe(guardKey(workspace()));
        });

        it('3: the hidden partner rebuilt with its keys in another order (Pass 2 of collapsePairedOps)', () => {
            const opened = workspace();
            const rebuilt = replaceRow(opened, PARTNER, inPass2Order);
            expect(rebuilt[PARTNER], 'premise: the same keys and values').toStrictEqual(opened[PARTNER]);
            expect(Object.keys(rebuilt[PARTNER]), 'premise: in another order').not.toEqual(Object.keys(opened[PARTNER]));

            expect(guardKey(rebuilt)).toBe(guardKey(opened));
        });

        it('3b: keys in another order at every depth, fields and cash included', () => {
            const opened = workspace();
            const reordered = opened.map((row) => reverseKeyOrder(row));
            expect(reordered, 'premise: the same keys and values').toStrictEqual(opened);
            expect(JSON.stringify(reordered), 'premise: in another order').not.toBe(JSON.stringify(opened));

            expect(guardKey(reordered)).toBe(guardKey(opened));
        });

        it('1+2+3: the saved pair as Reset all hands it back, all three at once', () => {
            const reset = replaceRow(workspace({main: 'main-2', partner: 'partner-2', createdSeq: 10, link: 'link-2'}), PARTNER, inPass2Order);

            expect(guardKey(reset)).toBe(guardKey(workspace()));
        });

        it('4 (control): a saved row that is no pair, under a new tempId and createdSeq', () => {
            const single = (tempId: string, createdSeq: number) => savedRow(103, tempId, createdSeq, cashIn('100', 'salary'));

            expect(guardKey([...workspace(), single('single-2', 12)])).toBe(guardKey([...workspace(), single('single-1', 3)]));
        });
    });

    describe('real changes: the key changes', () => {
        const changes: Array<[string, (rows: readonly GuardRow[]) => GuardRow[]]> = [
            ["5: the visible row's description", (rows) => replaceRow(rows, MAIN, (row) => ({...row, fields: {...row.fields, description: 'EUR to USD, corrected'}}))],
            ["5: the hidden partner's cash amount", (rows) => replaceRow(rows, PARTNER, (row) => ({...row, fields: {...row.fields, cash: {code: 'USD', amount: '441'}}}))],
            ["5: the order of the visible row's tags", (rows) => replaceRow(rows, MAIN, (row) => ({...row, fields: {...row.fields, tags: [...row.fields.tags].reverse()}}))],
            ['6: the visible row marked for deletion', (rows) => replaceRow(rows, MAIN, (row) => (row.op === 'edit' ? {...row, markedDelete: true} : row))],
            ['7: a row added', (rows) => [...rows, newRow('new-2', 3, cashIn('75', 'second top-up'))]],
            ['7: a row removed', (rows) => rows.filter((_, index) => index !== NEW)],
            [
                '8: the pair split: no pairedWith, no link_uuid on either half',
                (rows) =>
                    replaceRow(
                        replaceRow(rows, MAIN, (row) => ({...row, link_uuid: null})),
                        PARTNER,
                        (row) => ({...row, pairedWith: undefined, link_uuid: null}),
                    ),
            ],
        ];

        it.each(changes)('%s', (_label, change) => {
            const opened = workspace();

            expect(guardKey(change(opened))).not.toBe(guardKey(opened));
        });

        it('9: the hidden partner paired to a different saved row', () => {
            const opened = [...workspace(), savedRow(103, 'single-1', 3, cashIn('100', 'salary'))];
            const repaired = replaceRow(opened, PARTNER, (row) => ({...row, pairedWith: 'single-1'}));

            expect(guardKey(repaired)).not.toBe(guardKey(opened));
        });

        it("9b: the same link_uuid values on the same rows, in other groups: two saved pairs swap their partners' links", () => {
            const opened = [...savedPair([101, 102], ['main-1', 'partner-1'], 0, 'link-1'), ...savedPair([103, 104], ['main-3', 'partner-3'], 2, 'link-3')];
            const swapped = replaceRow(
                replaceRow(opened, 1, (row) => ({...row, link_uuid: 'link-3'})),
                3,
                (row) => ({...row, link_uuid: 'link-1'}),
            );

            expect(guardKey(swapped)).not.toBe(guardKey(opened));
        });

        it('9c: a new hidden partner paired to a different new row', () => {
            const newPair = (target: string): GuardRow[] => [{...newRow('new-main', 3, fxLeg('EUR', '-50')), link_uuid: 'link-n'}, {...newRow('new-partner', 4, fxLeg('USD', '55')), pairedWith: target, link_uuid: 'link-n'}, newRow('new-other', 5, cashIn('20', 'other'))];

            expect(guardKey([...workspace(), ...newPair('new-other')])).not.toBe(guardKey([...workspace(), ...newPair('new-main')]));
        });
    });

    it('reads the rows without touching them: the same values, in the same key order', () => {
        const rows = replaceRow(workspace(), PARTNER, inPass2Order);
        const values = structuredClone(rows);
        const order = JSON.stringify(rows);

        serializeOps(rows);

        expect(rows).toStrictEqual(values);
        expect(JSON.stringify(rows)).toBe(order);
    });
});
