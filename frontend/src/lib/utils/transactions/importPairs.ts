/**
 * Linked pairs in the import wizard's review step (D3, plan 31_brimDegiro).
 *
 * A plugin emits both legs of a currency conversion with one `link_uuid` (DEGIRO is the first).
 * The bulk editor shows such a pair as one row with From/To lines, and the batch accepts a pair
 * only whole: exactly two creates per `link_uuid`. The review step follows the same rules: one row
 * per pair, both legs selected or neither, and a fresh pairing key per pair at the handoff, so two
 * copies of the same file can never put four legs under one key.
 */
import type {MergedTx} from './importTypes';

export interface ImportPairs {
    /** Row index → its partner's index, both ways. */
    partnerOf: Map<number, number>;
    /** The legs shown through their partner's row: the leg that receives, as the editor's "To". */
    hidden: Set<number>;
}

/** The pairing key of a row: its file and its `link_uuid`; `null` for a row that is not paired. */
export function pairKey(row: Pick<MergedTx, 'sourceFileId' | 'tx'>): string | null {
    const link = (row.tx as {link_uuid?: string | null}).link_uuid;
    return link ? `${row.sourceFileId}\u0000${link}` : null;
}

function amountOf(row: MergedTx): number {
    const cash = row.tx.cash as {amount?: string | number} | null | undefined;
    return Number(cash?.amount ?? 0);
}

/** The pairs among the merged rows: two legs of one file under one `link_uuid` (any other count is no pair). */
export function linkedPairs(rows: readonly MergedTx[]): ImportPairs {
    const byKey = new Map<string, MergedTx[]>();
    for (const row of rows) {
        const key = pairKey(row);
        if (key) byKey.set(key, [...(byKey.get(key) ?? []), row]);
    }
    const partnerOf = new Map<number, number>();
    const hidden = new Set<number>();
    for (const legs of byKey.values()) {
        if (legs.length !== 2) continue;
        const [first, second] = legs;
        partnerOf.set(first.index, second.index);
        partnerOf.set(second.index, first.index);
        // The paying leg is the row ("From"); when both pay or both receive, the first one.
        hidden.add(amountOf(first) >= 0 && amountOf(second) < 0 ? first.index : second.index);
    }
    return {partnerOf, hidden};
}

/** Select or deselect a row together with its partner. */
export function setPairSelected(rows: readonly MergedTx[], index: number, selected: boolean, pairs: ImportPairs): MergedTx[] {
    const partner = pairs.partnerOf.get(index);
    return rows.map((row) => (row.index === index || row.index === partner ? {...row, selected} : row));
}

/** The selected rows without a leg whose partner is not selected: the batch takes a pair only whole. */
export function completePairsOnly<T extends {index: number}>(selected: readonly T[], pairs: ImportPairs): T[] {
    const chosen = new Set(selected.map((row) => row.index));
    return selected.filter((row) => {
        const partner = pairs.partnerOf.get(row.index);
        return partner === undefined || chosen.has(partner);
    });
}

/** A fresh `link_uuid` per pair (file + key), the same for both legs; `null` for a row that is not paired. */
export function freshLinkFor(row: Pick<MergedTx, 'sourceFileId' | 'tx'>, fresh: Map<string, string>, newId: () => string): string | null {
    const key = pairKey(row);
    if (!key) return null;
    let link = fresh.get(key);
    if (!link) {
        link = newId();
        fresh.set(key, link);
    }
    return link;
}
