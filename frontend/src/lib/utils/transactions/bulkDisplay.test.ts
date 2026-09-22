// @vitest-environment node
import {describe, expect, it} from 'vitest';
import {buildBulkOperationIndex, buildBulkRowLabels, createBulkDateComparator, resolveBulkIssueRows, settleBulkIssueSnapshot, type BulkBatchResult, type BulkDisplayRow, type BulkIssue, type BulkIssueRow, type BulkIssueSnapshotEntry, type IdentifiedBulkOp} from './bulkDisplay';

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
