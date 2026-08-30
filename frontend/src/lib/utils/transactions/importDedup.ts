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
import {isFakeAssetId} from '$lib/utils/brim/isFakeAssetId';
import {AMOUNT_TOLERANCE, QUANTITY_TOLERANCE, type AssetResolution, type DedupKey, type DuplicateGroup, type DuplicateStatus, type DuplicateTier, type MergedTx} from './importTypes';

/** Whether a row with this verdict may be pre-ticked for import. The two firm-duplicate tiers may not. */
export function duplicateStatusAllowsAutoSelect(status: DuplicateStatus): boolean {
    return status !== 'likely' && status !== 'pending_duplicate';
}

/** Whether a *selected* row with this verdict should carry a warning: the user is importing a probable dup. */
export function duplicateStatusIsSelectedWarning(status: DuplicateStatus): boolean {
    return status === 'likely' || status === 'pending_duplicate' || status === 'pending_possible_duplicate';
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

/** Normalise a currency leg (possibly wrapped in an array) to `{code, amount}`, or null when unusable. */
export function getDedupCurrency(raw: unknown): {code: string; amount: number} | null {
    const cur = Array.isArray(raw) ? raw.find((entry) => entry && typeof entry === 'object') : raw;
    if (!cur || typeof cur !== 'object') return null;
    const code = String((cur as {code?: unknown}).code ?? '')
        .trim()
        .toUpperCase();
    const amount = Number((cur as {amount?: unknown}).amount ?? 0);
    if (!code || !Number.isFinite(amount)) return null;
    return {code, amount};
}

/** The cash leg of a transaction, normalised for comparison. */
export function getDedupCash(tx: TransactionCreateItem): {code: string; amount: number} | null {
    return getDedupCurrency(tx.cash);
}

/** Build the dedup identity of a row, or null when its quantity is not a finite number. */
export function buildDedupKey(tx: TransactionCreateItem, resolutionsByFake: Map<number, AssetResolution>): DedupKey | null {
    const quantity = Number(tx.quantity ?? 0);
    if (!Number.isFinite(quantity)) return null;
    const cash = getDedupCash(tx);
    return {
        broker: String(tx.broker_id ?? ''),
        type: String(tx.type ?? ''),
        date: String(tx.date ?? '').slice(0, 10),
        quantity,
        cashCode: cash?.code ?? null,
        cashAmount: cash?.amount ?? null,
        costOverride: getDedupCurrency((tx as {cost_basis_override?: unknown}).cost_basis_override)?.amount ?? null,
        assetIdentity: resolveDedupAssetIdentity(tx, resolutionsByFake),
    };
}

/** Whether two dedup keys describe the same movement, within the quantity and amount tolerances. */
export function dedupKeysMatch(a: DedupKey, b: DedupKey): boolean {
    if (a.broker !== b.broker || a.type !== b.type || a.date !== b.date || a.cashCode !== b.cashCode || a.assetIdentity !== b.assetIdentity) return false;
    if (Math.abs(a.quantity - b.quantity) > QUANTITY_TOLERANCE) return false;
    if (a.cashAmount === null || b.cashAmount === null) {
        if (a.cashAmount !== b.cashAmount) return false;
    } else if (Math.abs(a.cashAmount - b.cashAmount) > AMOUNT_TOLERANCE) return false;
    // Per-unit cost override distinguishes cashless ADJUSTMENT legs of the same
    // security acquired at different book prices (e.g. succession transfers).
    if (a.costOverride === null || b.costOverride === null) {
        if (a.costOverride !== b.costOverride) return false;
    } else if (Math.abs(a.costOverride - b.costOverride) > QUANTITY_TOLERANCE) return false;
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

/** A stable string form of a dedup key — the identity a duplicate group is addressed by. */
export function describeDedupKey(key: DedupKey): string {
    return [key.broker, key.type, key.date, key.quantity.toFixed(4), key.cashCode ?? '', key.cashAmount?.toFixed(2) ?? '', key.costOverride?.toFixed(4) ?? '', key.assetIdentity].join('|');
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
