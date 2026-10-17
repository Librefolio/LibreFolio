/**
 * How the import wizard decides that two parsed rows are the same movement.
 *
 * Extracted from `ImportWizardModal.svelte` because it is pure and dense: the identity a
 * row is keyed on, the tolerant comparison of two keys, and the clustering of a batch into
 * cross-file duplicate groups all have branches that the happy-path E2E never reaches — a
 * cash amount that is null on one side only, a per-unit cost override that separates two
 * otherwise-identical adjustment legs, a cluster whose rows all live in one file. Reaching
 * those through Playwright would mean hand-crafting broker files that trigger each; here
 * each is one hand-built `TransactionCreateItem`.
 *
 * Everything here reads its inputs and returns a value — no store, no component state, no
 * i18n. The component owns the reactive arrays; these functions own the arithmetic.
 */
import type {TransactionCreateItem} from '$lib/types';
import {isFakeAssetId} from '$lib/features/transactions/import/isFakeAssetId';
import {AMOUNT_TOLERANCE, QUANTITY_TOLERANCE, type AssetResolution, type DedupKey, type DuplicateGroup, type DuplicateStatus, type DuplicateTier, type MergedTx} from './importTypes';

/** Whether a row with this verdict may be pre-ticked for import. The two firm-duplicate tiers may not. */
export function duplicateStatusAllowsAutoSelect(status: DuplicateStatus): boolean {
    return status !== 'likely' && status !== 'pending_duplicate';
}

/** Whether a *selected* row with this verdict should carry a warning: the user is importing a probable dup. */
export function duplicateStatusIsSelectedWarning(status: DuplicateStatus): boolean {
    return status === 'likely' || status === 'pending_duplicate' || status === 'pending_possible_duplicate';
}

/**
 * Whether the row collides firmly with something outside the batch: a likely database twin or
 * an identical unsaved row in the bulk editor. Such a copy is never the one a cross-file group
 * keeps by default — keeping it would recreate what already exists. Weak verdicts (`possible`,
 * `pending_possible_duplicate`) do not count: they stay selected for review by design.
 */
export function hasFirmOutsideCollision(mt: MergedTx): boolean {
    return mt.dbDuplicateStatus === 'likely' || mt.pendingMatchStatus === 'pending_duplicate';
}

/**
 * A row as the duplicate recheck leaves it, before the in-batch and editor passes run again.
 * The database verdict is replaced, never carried over: a correction can clear a false
 * duplicate, and a stale `likely` would then keep the row out of the resolver's keepers. Every
 * in-batch and editor marker is cleared for the passes that follow, and the selection is
 * recomputed; rows predating the broker's opening date stay out either way.
 */
export function rowAfterRecheck(m: MergedTx, verdict: {status: DuplicateStatus; matches: MergedTx['dupMatches']} | undefined, opts: {beforeOpening: boolean; preserveSelection: boolean}): MergedTx {
    const status: DuplicateStatus = verdict?.status ?? 'unique';
    return {
        ...m,
        duplicateStatus: status,
        dbDuplicateStatus: status === 'likely' || status === 'possible' ? status : undefined,
        pendingMatchStatus: undefined,
        dupMatches: verdict?.matches ?? [],
        dupGroupKey: undefined,
        dupTier: undefined,
        isDupKeeper: undefined,
        dupPendingMatch: undefined,
        selected: (!opts.preserveSelection || m.selected) && !opts.beforeOpening && duplicateStatusAllowsAutoSelect(status),
    };
}

/** The comparison a review-row status badge can open. */
export type CompareTarget = 'db' | 'pending' | 'lot';

/**
 * The comparison a row's status badge opens: always the one the badge claims. A database
 * verdict shown on the badge compares with the database row, even when the row also belongs to
 * a cross-file group; the in-batch comparison is for rows whose badge says "duplicate in batch".
 */
export function compareTargetFor(mt: MergedTx): CompareTarget | null {
    if (mt.duplicateStatus === 'unique') return null;
    if (mt.duplicateStatus === 'likely' || mt.duplicateStatus === 'possible') return mt.dupMatches.length > 0 ? 'db' : null;
    if (mt.dupPendingMatch) return 'pending';
    if (mt.dupGroupKey != null) return 'lot';
    return null;
}

/** Trim + lowercase a code to a comparable token, or null when it carries nothing. */
export function normalizeAssetToken(value: string | null | undefined): string | null {
    const token = String(value ?? '')
        .trim()
        .toLowerCase();
    return token === '' ? null : token;
}

/**
 * The identity token the dedup key uses for a row's asset.
 *
 * A resolved binding (real asset id) is authoritative. An unresolved fake id falls back to
 * the strongest extracted code it has — ISIN, then symbol, then name — so two files' rows
 * for the same still-unbound security dedup together; failing all three it stays distinct
 * by its fake id, so unrelated unresolved rows are never merged.
 */
export function resolveDedupAssetIdentity(tx: TransactionCreateItem, resolutionsByFake: Map<number, AssetResolution>): string {
    const assetId = typeof tx.asset_id === 'number' ? tx.asset_id : null;
    if (assetId === null) return 'asset:null';
    if (!isFakeAssetId(assetId)) return `asset:${assetId}`;

    const res = resolutionsByFake.get(assetId);
    if (res?.resolvedAssetId != null) return `asset:${res.resolvedAssetId}`;
    const isin = normalizeAssetToken(res?.extractedIsin);
    if (isin) return `isin:${isin}`;
    const symbol = normalizeAssetToken(res?.extractedSymbol);
    if (symbol) return `symbol:${symbol}`;
    const name = normalizeAssetToken(res?.extractedName);
    if (name) return `name:${name}`;
    return `fake:${assetId}`;
}

/** A decimal read exactly: `coefficient / 10^scale`, its trailing zeros removed (`12.50` is 125 at scale 1). */
interface ExactDecimal {
    coefficient: bigint;
    scale: number;
}

/** A plain decimal text: an optional sign, digits, an optional point (`+5`, `.5`, `5.`); never an exponent. */
const PLAIN_DECIMAL = /^([+-]?)(\d*)(?:\.(\d*))?$/;

/** A finite number as JavaScript writes it: the shortest decimal that reads back as that number, maybe with an exponent (`1.5e-7`). */
const NUMBER_TEXT = /^(-?)(\d+)(?:\.(\d+))?(?:e([+-]\d+))?$/;

/** `sign integer.fraction × 10^exponent`, exactly, its trailing zeros removed. */
function exactDecimal(sign: string, integer: string, fraction: string, exponent: number): ExactDecimal {
    let coefficient = BigInt(`${integer || '0'}${fraction}`);
    let scale = fraction.length - exponent;
    if (scale < 0) {
        coefficient *= 10n ** BigInt(-scale);
        scale = 0;
    }
    while (scale > 0 && coefficient % 10n === 0n) {
        coefficient /= 10n;
        scale -= 1;
    }
    return {coefficient: sign === '-' ? -coefficient : coefficient, scale};
}

/**
 * A decimal read exactly (W-B81): a plain decimal text, or a finite number as JavaScript writes it, its exponent expanded;
 * null for anything else (`'n/a'`, `'Infinity'`, `'1e400'`, `''`): a parse report writes plain decimals only (`SafeDecimal`).
 */
function readExactDecimal(value: unknown): ExactDecimal | null {
    if (typeof value === 'number') {
        const match = Number.isFinite(value) ? NUMBER_TEXT.exec(String(value)) : null;
        return match ? exactDecimal(match[1], match[2], match[3] ?? '', Number(match[4] ?? 0)) : null;
    }
    const match = typeof value === 'string' ? PLAIN_DECIMAL.exec(value.trim()) : null;
    if (!match || (match[2] === '' && (match[3] ?? '') === '')) return null;
    return exactDecimal(match[1], match[2], match[3] ?? '', 0);
}

/** A field of the payload read exactly, where a field left empty (missing, or blanks only) is `0`, the payload's default. */
function readFieldDecimal(value: unknown): ExactDecimal | null {
    return readExactDecimal(value === undefined || value === null || (typeof value === 'string' && value.trim() === '') ? '0' : value);
}

/** The exact text of a decimal, trailing zeros removed, in plain notation: what a key holds and a group is addressed by. */
function exactText({coefficient, scale}: ExactDecimal): string {
    const negative = coefficient < 0n;
    const digits = (negative ? -coefficient : coefficient).toString().padStart(scale + 1, '0');
    const text = scale === 0 ? digits : `${digits.slice(0, -scale)}.${digits.slice(-scale)}`;
    return negative ? `-${text}` : text;
}

/** The coefficient of `value` at `target` decimals: exact when `target` is finer, rounded half-up (away from zero) when coarser. */
function atScale({coefficient, scale}: ExactDecimal, target: number): bigint {
    if (target >= scale) return coefficient * 10n ** BigInt(target - scale);
    const divisor = 10n ** BigInt(scale - target);
    const magnitude = coefficient < 0n ? -coefficient : coefficient;
    const quotient = magnitude / divisor + ((magnitude % divisor) * 2n >= divisor ? 1n : 0n);
    return coefficient < 0n ? -quotient : quotient;
}

/** Whether `a` and `b` lie within `bound` of each other, computed exactly. */
function withinExact(a: ExactDecimal, b: ExactDecimal, bound: ExactDecimal): boolean {
    const scale = Math.max(a.scale, b.scale, bound.scale);
    const gap = atScale(a, scale) - atScale(b, scale);
    return (gap < 0n ? -gap : gap) <= atScale(bound, scale);
}

const QUANTITY_BOUND = readExactDecimal(QUANTITY_TOLERANCE) as ExactDecimal;
const AMOUNT_BOUND = readExactDecimal(AMOUNT_TOLERANCE) as ExactDecimal;

/**
 * Whether two quantities (or two per-unit costs) are the same movement's: the rule of the backend's duplicate check (W-B51,
 * decision D-W51-1), here for the wizard (W-B81). Equal once both are rounded half-up to the decimals of the less precise
 * one, and never more than `QUANTITY_TOLERANCE` apart: a report that rounds (`0.00015`) still meets the value another states
 * (`0.000153`), two crypto buys of one day (`0.00015123`, `0.00015098`) stay apart, and so do `10` and `10.4`. False when
 * either is no plain finite decimal.
 */
export function sameDedupQuantity(a: unknown, b: unknown): boolean {
    const left = readExactDecimal(a);
    const right = readExactDecimal(b);
    if (!left || !right || !withinExact(left, right, QUANTITY_BOUND)) return false;
    const scale = Math.min(left.scale, right.scale);
    return atScale(left, scale) === atScale(right, scale);
}

/** Whether two cash amounts are the same countervalue: within `AMOUNT_TOLERANCE`, exactly. False when either is unreadable. */
function sameDedupAmount(a: string, b: string): boolean {
    const left = readExactDecimal(a);
    const right = readExactDecimal(b);
    return !!left && !!right && withinExact(left, right, AMOUNT_BOUND);
}

/**
 * Normalise a currency leg (possibly wrapped in an array) to `{code, amount}`, the amount as its exact text, an empty amount
 * as `0`; null when unusable.
 */
export function getDedupCurrency(raw: unknown): {code: string; amount: string} | null {
    const cur = Array.isArray(raw) ? raw.find((entry) => entry && typeof entry === 'object') : raw;
    if (!cur || typeof cur !== 'object') return null;
    const code = String((cur as {code?: unknown}).code ?? '')
        .trim()
        .toUpperCase();
    const amount = readFieldDecimal((cur as {amount?: unknown}).amount);
    if (!code || !amount) return null;
    return {code, amount: exactText(amount)};
}

/** The cash leg of a transaction, normalised for comparison. */
export function getDedupCash(tx: TransactionCreateItem): {code: string; amount: string} | null {
    return getDedupCurrency(tx.cash);
}

/**
 * Build the dedup identity of a row, or null when its quantity is no plain finite decimal. An empty quantity reads as `0`,
 * the payload's default: a cash row whose quantity was cleared still meets its pending twin.
 */
export function buildDedupKey(tx: TransactionCreateItem, resolutionsByFake: Map<number, AssetResolution>): DedupKey | null {
    const quantity = readFieldDecimal(tx.quantity);
    if (!quantity) return null;
    const cash = getDedupCash(tx);
    return {
        broker: String(tx.broker_id ?? ''),
        type: String(tx.type ?? ''),
        date: String(tx.date ?? '').slice(0, 10),
        quantity: exactText(quantity),
        cashCode: cash?.code ?? null,
        cashAmount: cash?.amount ?? null,
        costOverride: getDedupCurrency((tx as {cost_basis_override?: unknown}).cost_basis_override)?.amount ?? null,
        assetIdentity: resolveDedupAssetIdentity(tx, resolutionsByFake),
    };
}

/** Whether two dedup keys describe the same movement: the quantity and the per-unit cost by `sameDedupQuantity`, the cash within its tolerance. */
export function dedupKeysMatch(a: DedupKey, b: DedupKey): boolean {
    if (a.broker !== b.broker || a.type !== b.type || a.date !== b.date || a.cashCode !== b.cashCode || a.assetIdentity !== b.assetIdentity) return false;
    if (!sameDedupQuantity(a.quantity, b.quantity)) return false;
    if (a.cashAmount === null || b.cashAmount === null) {
        if (a.cashAmount !== b.cashAmount) return false;
    } else if (!sameDedupAmount(a.cashAmount, b.cashAmount)) return false;
    // Per-unit cost override distinguishes cashless ADJUSTMENT legs of the same
    // security acquired at different book prices (e.g. succession transfers).
    if (a.costOverride === null || b.costOverride === null) {
        if (a.costOverride !== b.costOverride) return false;
    } else if (!sameDedupQuantity(a.costOverride, b.costOverride)) return false;
    return true;
}

/**
 * A row's description, lowercased and stripped of all whitespace.
 *
 * Whitespace-insensitive: some brokers (e.g. Crédit Agricole) reformat the SAME
 * transaction's description between two exports by inserting/removing a space
 * (observed: "DTEMISS." vs "DT EMISS."). Collapsing all whitespace lets genuine
 * twins match while distinct rows (different ISIN / movement id) stay distinct.
 */
export function normalizeDedupDescription(tx: TransactionCreateItem): string {
    return String(tx.description ?? '')
        .toLowerCase()
        .replace(/\s+/g, '');
}

/** Whether two matched pending rows share a description (firm dup) or only their key (possible dup). */
export function pendingDuplicateStatusFor(a: TransactionCreateItem, b: TransactionCreateItem): 'pending_duplicate' | 'pending_possible_duplicate' {
    return normalizeDedupDescription(a) === normalizeDedupDescription(b) ? 'pending_duplicate' : 'pending_possible_duplicate';
}

/** A stable string form of a dedup key — the identity a duplicate group is addressed by: the exact text of each number (W-B81), never `toFixed`. */
export function describeDedupKey(key: DedupKey): string {
    const exact = (value: string | null): string => {
        const read = value === null ? null : readExactDecimal(value);
        return read ? exactText(read) : (value ?? '');
    };
    return [key.broker, key.type, key.date, exact(key.quantity), key.cashCode ?? '', exact(key.cashAmount), exact(key.costOverride), key.assetIdentity].join('|');
}

/**
 * Cluster a batch of rows into cross-file duplicate groups.
 *
 * Only clusters whose rows span two or more source files survive — a duplicate within a
 * single file is the plugin's business, not the wizard's. A surviving cluster is `sure`
 * (total overlap) when every description-partition of it is itself cross-file, and
 * `probable` (partial overlap) otherwise: a partition confined to one file is an ambiguous
 * row with no exact twin, and needs a human.
 */
export function buildDuplicateGroups(txArr: MergedTx[], assetMap: Map<number, AssetResolution>): DuplicateGroup[] {
    const clusters: Array<{key: DedupKey; members: MergedTx[]}> = [];
    for (const mt of txArr) {
        const key = buildDedupKey(mt.tx, assetMap);
        if (!key) continue;
        const cluster = clusters.find((c) => dedupKeysMatch(key, c.key));
        if (cluster) cluster.members.push(mt);
        else clusters.push({key, members: [mt]});
    }
    return clusters
        .filter((cluster) => new Set(cluster.members.map((mt) => mt.sourceFileId)).size >= 2)
        .map((cluster) => {
            // Partition the loose cluster by normalized description. A partition whose rows
            // span >=2 source files is a confirmed cross-file duplicate set ("total overlap");
            // a single-file partition is an ambiguous row with no exact twin ("partial").
            const filesByDesc = new Map<string, Set<string>>();
            for (const mt of cluster.members) {
                const d = normalizeDedupDescription(mt.tx);
                const files = filesByDesc.get(d) ?? new Set<string>();
                files.add(mt.sourceFileId);
                filesByDesc.set(d, files);
            }
            const allPartitionsCrossFile = [...filesByDesc.values()].every((files) => files.size >= 2);
            return {
                key: describeDedupKey(cluster.key),
                memberIndices: cluster.members.map((mt) => mt.index),
                tier: (allPartitionsCrossFile ? 'sure' : 'probable') as DuplicateTier,
            };
        });
}

/**
 * A resolved-away in-batch duplicate: a non-keeper member of a duplicate group that the user
 * did not deliberately keep. These are hidden from step 4 entirely (out of table AND payload):
 * only one keeper per group survives by default. Kept secondaries (selected) and bulk-modal
 * duplicates (no dupGroupKey) are never hidden.
 */
export function isResolvedAwayDuplicate(t: MergedTx): boolean {
    return t.dupGroupKey != null && t.isDupKeeper === false && !t.selected;
}
