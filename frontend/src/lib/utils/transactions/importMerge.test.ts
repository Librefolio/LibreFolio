import {describe, it, expect} from 'vitest';
import {FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import type {BrimParseResponse} from '$lib/types';
import {buildMergedTransactions, mergeCandidates, uniqueExactCandidateId, type MergeSourceResult, type MergeBroker} from './importMerge';
import type {AssetResolution} from './importTypes';

const FAKE = FAKE_ASSET_ID_BASE;

type Candidates = AssetResolution['candidates'];
const cand = (asset_id: number, match_confidence: string): Candidates[number] => ({asset_id, name: `asset ${asset_id}`, match_confidence});

/** Assemble a "done" parse result around a loose response body. */
const src = (fileId: string, brokerId: number, response: Record<string, unknown>): MergeSourceResult => ({
    fileId,
    brokerId,
    status: 'done',
    response: response as unknown as BrimParseResponse,
});

describe('uniqueExactCandidateId', () => {
    it('returns the id when exactly one candidate is exact', () => {
        expect(uniqueExactCandidateId([cand(1, 'high'), cand(2, 'exact')])).toBe(2);
    });
    it('is case-insensitive about the confidence label', () => {
        expect(uniqueExactCandidateId([cand(9, 'EXACT')])).toBe(9);
    });
    it('returns null with no exact match or with an ambiguous pair of them', () => {
        expect(uniqueExactCandidateId([cand(1, 'high')])).toBeNull();
        expect(uniqueExactCandidateId([cand(1, 'exact'), cand(2, 'exact')])).toBeNull();
        expect(uniqueExactCandidateId([])).toBeNull();
    });
});

describe('mergeCandidates', () => {
    it('unions by asset id, keeping the strongest confidence, sorted strongest-first', () => {
        const merged = mergeCandidates([cand(1, 'medium'), cand(2, 'low')], [cand(1, 'exact'), cand(3, 'high')]);
        expect(merged.map((c) => c.asset_id)).toEqual([1, 3, 2]);
        expect(merged.find((c) => c.asset_id === 1)?.match_confidence).toBe('exact');
    });
    it('sorts an unknown confidence tier last', () => {
        const merged = mergeCandidates([cand(1, 'mystery')], [cand(2, 'high')]);
        expect(merged.map((c) => c.asset_id)).toEqual([2, 1]);
    });
});

describe('buildMergedTransactions — flattening', () => {
    it('concatenates every done file into one globally-indexed list', () => {
        const results = [src('fileA', 1, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: 10}]}), src('fileB', 1, {transactions: [{type: 'SELL', date: '2024-05-02', quantity: 2, asset_id: 11}]})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr.map((t) => t.index)).toEqual([0, 1]);
        expect(txArr.map((t) => t.sourceFileId)).toEqual(['fileA', 'fileB']);
    });

    it('processes only done results that carry a response', () => {
        const results: MergeSourceResult[] = [
            {fileId: 'pending', brokerId: 1, status: 'pending', response: null},
            {fileId: 'err', brokerId: 1, status: 'error', response: {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: 1}]} as unknown as BrimParseResponse},
            src('done', 1, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: 1}]}),
        ];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr).toHaveLength(1);
        expect(txArr[0].sourceFileId).toBe('done');
    });

    it('leaves a real asset id untouched and records no resolution for it', () => {
        const {txArr, assetMap} = buildMergedTransactions([src('f', 1, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: 42}]})], [{id: 1}], []);
        expect(txArr[0].tx.asset_id).toBe(42);
        expect(assetMap.size).toBe(0);
    });
});

describe('buildMergedTransactions — fake id remapping', () => {
    const twoFilesSameFake = () => [
        src('fileA', 1, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: FAKE}], asset_mappings: [{fake_asset_id: FAKE, extracted_isin: 'IT0001', candidates: [], selected_asset_id: null}]}),
        src('fileB', 1, {transactions: [{type: 'BUY', date: '2024-05-02', quantity: 1, asset_id: FAKE}], asset_mappings: [{fake_asset_id: FAKE, extracted_isin: 'IT0002', candidates: [], selected_asset_id: null}]}),
    ];

    it('gives each file its own global fake id so two instruments never share a resolution', () => {
        const {txArr, assetMap, fileIdOfFake} = buildMergedTransactions(twoFilesSameFake(), [{id: 1}], []);
        // The two colliding plugin ids are remapped to distinct globals.
        expect(txArr[0].tx.asset_id).not.toBe(txArr[1].tx.asset_id);
        expect(assetMap.size).toBe(2);
        // Provenance is recorded per global id.
        expect(fileIdOfFake.get(txArr[0].tx.asset_id as number)).toBe('fileA');
        expect(fileIdOfFake.get(txArr[1].tx.asset_id as number)).toBe('fileB');
        // Each resolution keeps its own extracted code.
        expect(assetMap.get(txArr[0].tx.asset_id as number)?.extractedIsin).toBe('IT0001');
        expect(assetMap.get(txArr[1].tx.asset_id as number)?.extractedIsin).toBe('IT0002');
    });

    it('reuses one global id for repeats of the same plugin fake within a file', () => {
        const results = [
            src('fileA', 1, {
                transactions: [
                    {type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: FAKE},
                    {type: 'SELL', date: '2024-05-03', quantity: 1, asset_id: FAKE},
                ],
                asset_mappings: [{fake_asset_id: FAKE, extracted_isin: 'IT0001', candidates: [], selected_asset_id: null}],
            }),
        ];
        const {txArr, assetMap} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr[0].tx.asset_id).toBe(txArr[1].tx.asset_id);
        expect(assetMap.size).toBe(1);
    });

    it('auto-binds a lone exact candidate but lets an explicit selection win', () => {
        const results = [
            src('auto', 1, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: FAKE}], asset_mappings: [{fake_asset_id: FAKE, candidates: [cand(99, 'exact')], selected_asset_id: null}]}),
            src('explicit', 2, {transactions: [{type: 'BUY', date: '2024-05-01', quantity: 1, asset_id: FAKE}], asset_mappings: [{fake_asset_id: FAKE, candidates: [cand(99, 'exact')], selected_asset_id: 77}]}),
        ];
        const {txArr, assetMap} = buildMergedTransactions(results, [{id: 1}, {id: 2}], []);
        expect(assetMap.get(txArr[0].tx.asset_id as number)?.resolvedAssetId).toBe(99);
        expect(assetMap.get(txArr[1].tx.asset_id as number)?.resolvedAssetId).toBe(77);
    });
});

describe('buildMergedTransactions — selection and duplicates', () => {
    const buy = (asset_id: number, date = '2024-05-01') => ({type: 'BUY', date, quantity: 1, asset_id});

    it('auto-selects unique rows and never a likely duplicate', () => {
        const results = [src('f', 1, {transactions: [buy(1), buy(2)], duplicates: {tx_likely_duplicates: [{tx_row_index: 1, tx_existing_matches: [{existing_tx_id: 500}]}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr[0].duplicateStatus).toBe('unique');
        expect(txArr[0].selected).toBe(true);
        expect(txArr[1].duplicateStatus).toBe('likely');
        expect(txArr[1].selected).toBe(false);
    });

    it('does not select a row dated before the broker opened', () => {
        const results = [src('f', 1, {transactions: [buy(1, '2024-05-01')]})];
        const {txArr} = buildMergedTransactions(results, [{id: 1, opened_at: '2024-06-01'}], []);
        expect(txArr[0].selected).toBe(false);
    });

    it('drops a duplicate whose only DB match is being deleted, restoring auto-select', () => {
        const results = [src('f', 1, {transactions: [buy(1)], duplicates: {tx_likely_duplicates: [{tx_row_index: 0, tx_existing_matches: [{existing_tx_id: 500}]}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], [500]);
        expect(txArr[0].duplicateStatus).toBe('unique');
        expect(txArr[0].selected).toBe(true);
        expect(txArr[0].dupMatches).toEqual([]);
    });

    it('keeps the tier but prunes the deleted match when others survive', () => {
        const results = [src('f', 1, {transactions: [buy(1)], duplicates: {tx_likely_duplicates: [{tx_row_index: 0, tx_existing_matches: [{existing_tx_id: 500}, {existing_tx_id: 501}]}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], [500]);
        expect(txArr[0].duplicateStatus).toBe('likely');
        expect(txArr[0].dupMatches).toHaveLength(1);
        expect(txArr[0].dupMatches[0].existing_tx_id).toBe(501);
    });

    it('marks a possible duplicate, which still auto-selects', () => {
        const results = [src('f', 1, {transactions: [buy(1)], duplicates: {tx_possible_duplicates: [{tx_row_index: 0, tx_existing_matches: []}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr[0].duplicateStatus).toBe('possible');
        expect(txArr[0].selected).toBe(true);
    });
});

describe('mergeCandidates — unknown confidence tiers on both sides', () => {
    it('sorts several unknown tiers to the end without treating either operand specially', () => {
        // Three distinct ids, two of them with confidences absent from CONF_ORDER: the
        // comparator hits the `?? 9` fallback on both operands across its passes.
        const merged = mergeCandidates([cand(1, 'mystery'), cand(2, 'enigma')], [cand(3, 'high')]);
        expect(merged[0].asset_id).toBe(3);
        expect(
            merged
                .slice(1)
                .map((c) => c.asset_id)
                .sort((a, b) => a - b),
        ).toEqual([1, 2]);
    });

    it('replaces a colliding id whose stored confidence is unknown with a known-stronger one', () => {
        // Same id in both lists: existing tier is unknown (→ 9), incoming 'high' (< 9) wins.
        const merged = mergeCandidates([cand(1, 'mystery')], [cand(1, 'high')]);
        expect(merged).toHaveLength(1);
        expect(merged[0].match_confidence).toBe('high');
    });

    it('keeps the stored candidate when a colliding one is weaker, even if its tier is unknown', () => {
        // id 1 seen first as 'high' (1); the colliding 'mystery' scores 9 (≥ 1) so the guard's
        // else-branch fires and nothing is replaced. Exercises the unknown `?? 9` on the incoming
        // operand and the "don't replace" path of the merge guard together.
        const merged = mergeCandidates([cand(1, 'high')], [cand(1, 'mystery')]);
        expect(merged).toHaveLength(1);
        expect(merged[0].match_confidence).toBe('high');
    });
});

describe('uniqueExactCandidateId — nullish input', () => {
    it('treats a null candidate list as empty', () => {
        expect(uniqueExactCandidateId(null as unknown as Candidates)).toBeNull();
    });
});

describe('buildMergedTransactions — todos, sparse rows and mapping edges', () => {
    const buy = (asset_id?: number) => ({type: 'BUY', date: '2024-05-01', quantity: 1, asset_id});

    it('attaches field todos per row and tolerates missing evidence/context', () => {
        const results = [
            src('f', 1, {
                transactions: [buy(10), buy(11)],
                field_todos: [
                    {tx_index: 0, field: 'quantity', severity: 'warn', reason_code: 'A', message: 'm1', evidence: ['e1'], context: {k: 1}},
                    {tx_index: 0, field: 'cash_amount', severity: 'error', reason_code: 'B', message: 'm2'},
                ],
            }),
        ];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        // Row 0 gathers both todos (second reuses the list built by the first → both branches of `?? []`).
        expect(txArr[0].todos).toHaveLength(2);
        expect(txArr[0].todos[0].evidence).toEqual(['e1']);
        expect(txArr[0].todos[0].context).toEqual({k: 1});
        // A todo with no evidence/context falls back to [] / undefined.
        expect(txArr[0].todos[1].evidence).toEqual([]);
        expect(txArr[0].todos[1].context).toBeUndefined();
        // Row 1 has no todos → the `?? []` fallback at push time.
        expect(txArr[1].todos).toEqual([]);
    });

    it('drops a possible duplicate whose only DB match is being deleted', () => {
        const results = [src('f', 1, {transactions: [buy(1)], duplicates: {tx_possible_duplicates: [{tx_row_index: 0, tx_existing_matches: [{existing_tx_id: 700}]}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], [700]);
        // hadMatches true, no survivor → `continue` → the row reverts to unique/auto-select.
        expect(txArr[0].duplicateStatus).toBe('unique');
        expect(txArr[0].selected).toBe(true);
    });

    it('keeps a possible duplicate that carries no matches array at all', () => {
        const results = [src('f', 1, {transactions: [buy(1)], duplicates: {tx_possible_duplicates: [{tx_row_index: 0}]}})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        // `tx_existing_matches ?? []` → empty, hadMatches false → stays possible with no matches.
        expect(txArr[0].duplicateStatus).toBe('possible');
        expect(txArr[0].dupMatches).toEqual([]);
    });

    it('emits no rows for a done file whose response has no transactions array', () => {
        const results = [src('empty', 1, {})];
        const {txArr} = buildMergedTransactions(results, [{id: 1}], []);
        expect(txArr).toEqual([]);
    });

    it('auto-selects a dateless row despite a broker opening date, and leaves a non-numeric asset id untouched', () => {
        const results = [src('f', 1, {transactions: [{type: 'DEPOSIT', quantity: 1}]})];
        const {txArr} = buildMergedTransactions(results, [{id: 1, opened_at: '2024-06-01'}], []);
        // No date → the opening cutoff cannot apply, so the row stays auto-selected.
        expect(txArr[0].selected).toBe(true);
        // asset_id absent → origAssetId null → never remapped.
        expect(txArr[0].tx.asset_id).toBeUndefined();
    });

    it('remaps a fake asset id even when the file omits asset_mappings, recording no resolution', () => {
        const results = [src('f', 1, {transactions: [buy(FAKE)]})];
        const {txArr, assetMap} = buildMergedTransactions(results, [{id: 1}], []);
        // The fake id is remapped (first allocation reuses FAKE_ASSET_ID_BASE) but no mapping exists.
        expect(txArr[0].tx.asset_id).toBe(FAKE);
        expect(assetMap.size).toBe(0);
    });

    it('records a resolution with empty candidates and normalises notice kind/reason', () => {
        const results = [
            src('f', 1, {
                transactions: [buy(FAKE)],
                asset_mappings: [{fake_asset_id: FAKE, notices: [{kind: 'ambiguous', reason: 'many'}, {}], selected_asset_id: null}],
            }),
        ];
        const {txArr, assetMap} = buildMergedTransactions(results, [{id: 1}], []);
        const resolvedId = txArr[0].tx.asset_id as number;
        const resolution = assetMap.get(resolvedId)!;
        // `candidates ?? []` with no candidates key, and no exact match to auto-bind.
        expect(resolution.candidates).toEqual([]);
        expect(resolution.resolvedAssetId).toBeNull();
        // Notices are string-normalised; the empty `{}` notice becomes {kind:'', reason:''}.
        expect(resolution.notices).toEqual([
            {kind: 'ambiguous', reason: 'many'},
            {kind: '', reason: ''},
        ]);
    });
});
