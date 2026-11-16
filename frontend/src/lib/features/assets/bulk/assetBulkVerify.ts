/**
 * assetBulkVerify.ts — The answer of `POST /assets/validate`, organised for the banners of the bulk edit (lane 65, F4).
 *
 * `issues` are blocks (the save would be refused and nothing saved), `warnings` never block. The modal shows the blocks
 * first (red), then the warnings (amber), each group by `code`; the translation of a sentence is done by the modal with
 * `patchIssueMessage` (`assetPatchResult.ts`). Pure: no catalogue, no DOM.
 */
import {FIELD_ORDER, type BulkAsset, type BulkFieldKey} from './assetBulkEdit';
import type {AssetPatchAnswer, AssetPatchIssue} from '../assetPatchResult';

export interface VerifyEntry {
    assetId: number;
    name: string;
    issue: AssetPatchIssue;
}

export interface VerifyGroup {
    kind: 'block' | 'warning';
    code: string;
    entries: VerifyEntry[];
}

export interface VerifyView {
    /** Blocking groups: the index block first, the unknown codes last. */
    blocks: VerifyGroup[];
    warnings: VerifyGroup[];
    /** Per field of the modal, how many distinct assets are blocked on it. */
    blockedFields: Partial<Record<BulkFieldKey, number>>;
}

/** The order of the known blocking codes; a code not listed goes after them, in the order it appears. */
const BLOCK_ORDER = ['indexWithTransactions', 'assetNameTaken', 'assetNotFound', 'patchFailed'];

function groupBy(kind: VerifyGroup['kind'], list: readonly AssetPatchIssue[], names: ReadonlyMap<number, string>): VerifyGroup[] {
    const groups = new Map<string, VerifyGroup>();
    for (const issue of [...list].sort((a, b) => a.index - b.index)) {
        const name = names.get(issue.asset_id);
        if (name === undefined) continue; // not in the selection (any more)
        const group = groups.get(issue.code) ?? {kind, code: issue.code, entries: []};
        group.entries.push({assetId: issue.asset_id, name, issue});
        groups.set(issue.code, group);
    }
    const rank = (code: string) => {
        const at = BLOCK_ORDER.indexOf(code);
        return at === -1 ? BLOCK_ORDER.length : at;
    };
    // `Array.prototype.sort` is stable: unknown codes keep their order of appearance.
    return kind === 'block' ? [...groups.values()].sort((a, b) => rank(a.code) - rank(b.code)) : [...groups.values()];
}

/** The answer of the check as the banners need it; entries of assets outside `assets` are dropped. */
export function organizeVerify(answer: AssetPatchAnswer, assets: readonly BulkAsset[]): VerifyView {
    const names = new Map(assets.map((asset) => [asset.id, asset.display_name]));
    const blocks = groupBy('block', answer.issues ?? [], names);
    const warnings = groupBy('warning', answer.warnings ?? [], names);
    const blockedFields: Partial<Record<BulkFieldKey, number>> = {};
    for (const field of FIELD_ORDER) {
        const ids = new Set(blocks.flatMap((group) => group.entries.filter((entry) => entry.issue.field === field).map((entry) => entry.assetId)));
        if (ids.size > 0) blockedFields[field] = ids.size;
    }
    return {blocks, warnings, blockedFields};
}

/** The distinct asset ids of a group, in order: what «Remove from the edit» takes out. */
export function affectedIds(group: VerifyGroup): number[] {
    return [...new Set(group.entries.map((entry) => entry.assetId))];
}

/** True when at least one block stands: the later «Save» stays off. */
export function hasBlocks(view: VerifyView): boolean {
    return view.blocks.length > 0;
}
