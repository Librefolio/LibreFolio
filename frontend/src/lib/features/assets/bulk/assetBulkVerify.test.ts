// @vitest-environment node
/**
 * assetBulkVerify — unit test (Vitest, node). Lane 65, lot F4.
 *
 * The answer of `POST /assets/validate` for the bulk edit, organised for the banners of the modal: blocks (`issues`)
 * before warnings, each grouped by code, the blocking codes in a fixed order (`indexWithTransactions` first), the
 * entries of a group in the order of the payload, with the asset's name. `blockedFields` says, per field of the modal,
 * how many distinct assets are blocked on it (the chip «blocked» and the line «Not allowed for N of M»).
 *
 * Contract.
 * - An entry whose asset is not in the selection is dropped (the asset was removed after the check, or is unknown).
 * - A group is `block` for an issue and `warning` for a warning; the same code in both lists is two groups.
 * - `blockedFields[field]` counts distinct assets of the issues whose `field` is one of the modal's fields; an issue
 *   with another field (`display_name`) or none marks no field.
 * - `affectedIds(group)` are the distinct asset ids of its entries, in order: what «Remove from the edit» removes.
 * - `hasBlocks(view)` is what turns the later «Save» off.
 */
import {describe, expect, it} from 'vitest';
import {affectedIds, hasBlocks, organizeVerify} from './assetBulkVerify';
import type {AssetPatchIssue} from '../assetPatchResult';
import type {BulkAsset} from './assetBulkEdit';

const asset = (id: number): BulkAsset => ({id, display_name: `Name ${id}`, asset_type: 'ETF', active: true});
const SELECTION = [asset(1), asset(2), asset(3), asset(4), asset(5)];
const issue = (code: string, assetId: number, index: number, over: Partial<AssetPatchIssue> = {}): AssetPatchIssue => ({asset_id: assetId, index, code, message: `English ${code}`, params: null, field: null, ...over});

describe('organizeVerify', () => {
    it('is empty for an answer with no problem', () => {
        const view = organizeVerify({committed: false, issues: [], warnings: []}, SELECTION);
        expect(view).toEqual({blocks: [], warnings: [], blockedFields: {}});
        expect(hasBlocks(view)).toBe(false);
    });

    it('groups the blocks by code, the index block first, and the entries by payload order with the asset names', () => {
        const view = organizeVerify(
            {
                issues: [issue('assetNotFound', 5, 4), issue('indexWithTransactions', 3, 2, {field: 'asset_type', params: {tx_count: 3}}), issue('indexWithTransactions', 1, 0, {field: 'asset_type', params: {tx_count: 12}})],
                warnings: [],
            },
            SELECTION,
        );
        expect(view.blocks.map((g) => [g.kind, g.code])).toEqual([
            ['block', 'indexWithTransactions'],
            ['block', 'assetNotFound'],
        ]);
        expect(view.blocks[0].entries.map((e) => [e.assetId, e.name, e.issue.index])).toEqual([
            [1, 'Name 1', 0],
            [3, 'Name 3', 2],
        ]);
        expect(hasBlocks(view)).toBe(true);
    });

    it('puts the warnings in their own groups and never among the blocks', () => {
        const view = organizeVerify({issues: [], warnings: [issue('assetFamilyChange', 4, 3, {field: 'asset_type', params: {from: 'CROWDFUND_REAL_ESTATE', to: 'ETF_STOCK'}})]}, SELECTION);
        expect(view.blocks).toEqual([]);
        expect(view.warnings).toHaveLength(1);
        expect(view.warnings[0]).toMatchObject({kind: 'warning', code: 'assetFamilyChange'});
        expect(hasBlocks(view)).toBe(false);
    });

    it('an unknown code is a group of its own, after the known ones', () => {
        const view = organizeVerify({issues: [issue('somethingNew', 2, 1), issue('patchFailed', 3, 2), issue('assetNameTaken', 1, 0)], warnings: []}, SELECTION);
        expect(view.blocks.map((g) => g.code)).toEqual(['assetNameTaken', 'patchFailed', 'somethingNew']);
    });

    it('drops the entries of assets that are not in the selection', () => {
        const view = organizeVerify({issues: [issue('indexWithTransactions', 1, 0, {field: 'asset_type'}), issue('indexWithTransactions', 99, 1, {field: 'asset_type'})], warnings: [issue('assetFamilyChange', 98, 2)]}, SELECTION);
        expect(view.blocks[0].entries.map((e) => e.assetId)).toEqual([1]);
        expect(view.warnings).toEqual([]);
    });

    it('a group with no entry left disappears', () => {
        expect(organizeVerify({issues: [issue('assetNotFound', 99, 0)], warnings: []}, SELECTION).blocks).toEqual([]);
    });

    it('counts, per field of the modal, the distinct blocked assets', () => {
        const view = organizeVerify(
            {
                issues: [
                    issue('indexWithTransactions', 1, 0, {field: 'asset_type'}),
                    issue('indexWithTransactions', 2, 1, {field: 'asset_type'}),
                    issue('indexWithTransactions', 2, 1, {field: 'asset_type'}),
                    issue('assetNameTaken', 3, 2, {field: 'display_name'}),
                    issue('assetNotFound', 4, 3, {field: null}),
                ],
                warnings: [issue('assetFamilyChange', 5, 4, {field: 'asset_type'})],
            },
            SELECTION,
        );
        expect(view.blockedFields).toEqual({asset_type: 2});
    });

    it('reads a field that is not a string as no field', () => {
        const view = organizeVerify({issues: [issue('patchFailed', 1, 0, {field: ['asset_type'] as unknown as string})], warnings: []}, SELECTION);
        expect(view.blockedFields).toEqual({});
    });

    it('affectedIds lists the distinct ids of a group, in order', () => {
        const view = organizeVerify({issues: [issue('assetNotFound', 3, 0), issue('assetNotFound', 1, 1), issue('assetNotFound', 3, 2)], warnings: []}, SELECTION);
        expect(affectedIds(view.blocks[0])).toEqual([3, 1]);
    });

    it('tolerates an answer with no lists', () => {
        expect(organizeVerify({}, SELECTION)).toEqual({blocks: [], warnings: [], blockedFields: {}});
    });
});
