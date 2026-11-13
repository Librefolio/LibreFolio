/**
 * assetPatchResult.ts — What `PATCH /assets` answers, read by its callers (lane 65).
 *
 * The PATCH is all or nothing: the answer has `committed` (true only when every item was saved), `issues` (blocking
 * problems, any of which saves nothing) and `warnings` (remarks that never block). Each issue carries a `code` that
 * the interface translates, with `params` for the sentence. A caller that sends one item reads this and no longer
 * reads `results[0].success`.
 *
 * Codes: `assetNotFound`, `indexWithTransactions` (`tx_count`), `assetNameTaken` (`name`), `patchFailed`; the warning
 * `assetFamilyChange` (`from`, `to`). A code this module does not know falls back to the English `message` of the issue.
 */

type Translate = (key: string, options?: {values?: Record<string, string | number>}) => string;

/** One issue or warning of the answer, as the backend sends it. */
export interface AssetPatchIssue {
    asset_id: number;
    index: number;
    code: string;
    message: string;
    /** An object in practice (`tx_count`, `name`, `from`, `to`); typed open, as the generated schema types it. */
    params?: unknown;
    /** The patch field that caused it (`display_name`, `asset_type`), none for a whole item; typed open, as the generated schema types it. */
    field?: unknown;
}

/** The part of the PATCH (and `POST /assets/validate`) answer the callers read. */
export interface AssetPatchAnswer {
    committed?: boolean;
    issues?: AssetPatchIssue[];
    warnings?: AssetPatchIssue[];
}

/** The save did not happen: the PATCH answered 200 with `committed=false`. `issues` says why. */
export class AssetPatchRefused extends Error {
    readonly issues: AssetPatchIssue[];

    constructor(message: string, issues: AssetPatchIssue[]) {
        super(message);
        this.name = 'AssetPatchRefused';
        this.issues = issues;
    }
}

/** The sentence's key of each code. Own keys only: a prototype name is no code. */
const SENTENCE_KEYS: Readonly<Record<string, string>> = {
    assetNotFound: 'assets.patchIssue.assetNotFound',
    indexWithTransactions: 'assets.patchIssue.indexWithTransactions',
    assetNameTaken: 'assets.patchIssue.assetNameTaken',
    assetFamilyChange: 'assets.patchIssue.assetFamilyChange',
    patchFailed: 'assets.patchIssue.patchFailed',
};

function text(value: unknown): string {
    return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

/** The sentence of an issue or warning in the interface language; the issue's own English message for an unknown code. */
export function patchIssueMessage(issue: AssetPatchIssue, t: Translate): string {
    if (!Object.prototype.hasOwnProperty.call(SENTENCE_KEYS, issue.code)) return issue.message;
    const params = issue.params && typeof issue.params === 'object' && !Array.isArray(issue.params) ? (issue.params as Record<string, unknown>) : {};
    const values: Record<string, string | number> = {
        name: text(params.name),
        count: Number(params.tx_count) || 0,
        from: text(params.from),
        to: text(params.to),
        id: issue.asset_id,
    };
    return t(SENTENCE_KEYS[issue.code], {values});
}

/**
 * Throws `AssetPatchRefused` unless the answer says `committed`. The message is the sentence of the first issue, or
 * `fallback` when the answer has none (an old or odd answer: nothing says it was saved, so it was not).
 */
export function assertPatchCommitted<T extends AssetPatchAnswer>(answer: T, t: Translate, fallback: string): T {
    if (answer?.committed === true) return answer;
    const issues = Array.isArray(answer?.issues) ? answer.issues : [];
    throw new AssetPatchRefused(issues.length > 0 ? patchIssueMessage(issues[0], t) : fallback, issues);
}
