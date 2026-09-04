/**
 * Pure duplicate-resolver logic extracted from `ImportWizardModal.svelte` (step 6).
 *
 * A "duplicate group" is a cluster of rows that share a numeric/fixed dedup key. Within a
 * group the resolver keeps exactly one primary per *description-partition*: rows that share
 * the key AND the (whitespace-insensitive) description are exact cross-file twins and only
 * one survives; rows that share only the key but differ in description are genuinely-distinct
 * and each survive as their own partition primary.
 *
 * These functions take the wizard state they depend on as explicit parameters
 * (`priorityIds`, `manualChoice`, `selections`) so they can be unit-tested directly; the
 * component keeps thin wrappers that inject its reactive `$state`.
 */
import {normalizeDedupDescription} from './importDedup';
import type {DuplicateGroup, MergedTx} from './importTypes';

export interface GroupPartition {
    primaryIndex: number;
    memberIndices: number[];
    crossFile: boolean;
}

/**
 * Partition a duplicate group by normalized description. Each partition is a set of rows
 * that share the numeric/fixed key AND the (whitespace-insensitive) description. The primary
 * is the partition member from the highest-priority file (`priorityIds` order); the rest are
 * exact cross-file twins.
 */
export function groupPartitions(group: DuplicateGroup, txArr: MergedTx[], priorityIds: string[]): GroupPartition[] {
    const members = group.memberIndices.map((idx) => txArr.find((mt) => mt.index === idx)).filter((mt): mt is MergedTx => mt !== undefined);
    if (members.length === 0) return [];
    const priority = new Map(priorityIds.map((id, idx) => [id, idx] as const));
    const rank = (mt: MergedTx) => priority.get(mt.sourceFileId) ?? Number.MAX_SAFE_INTEGER;
    const byDesc = new Map<string, MergedTx[]>();
    for (const mt of members) {
        const d = normalizeDedupDescription(mt.tx);
        const arr = byDesc.get(d) ?? [];
        arr.push(mt);
        byDesc.set(d, arr);
    }
    return [...byDesc.values()].map((part) => {
        const primary = part.reduce((best, mt) => (rank(mt) < rank(best) ? mt : best), part[0]);
        const files = new Set(part.map((mt) => mt.sourceFileId));
        return {primaryIndex: primary.index, memberIndices: part.map((mt) => mt.index), crossFile: files.size >= 2};
    });
}

/**
 * Keep exactly one primary per description-partition (highest file priority). A cross-file
 * duplicate keeps a single copy; genuinely-distinct rows that only share the numeric key
 * (different descriptions) are each their own partition primary, so all are kept.
 */
export function defaultKeeperIndices(group: DuplicateGroup, txArr: MergedTx[], priorityIds: string[]): Set<number> {
    return new Set(groupPartitions(group, txArr, priorityIds).map((p) => p.primaryIndex));
}

/**
 * Whether a given row is selected (kept) in the resolver. When the group has a manual choice
 * the caller-supplied `selections` decides; otherwise the default keeps one primary per
 * description-partition.
 */
export function resolverSelectionFor(group: DuplicateGroup, rowIndex: number, txArr: MergedTx[], priorityIds: string[], manualChoice: boolean, selections: Record<number, boolean>): boolean {
    if (manualChoice) return selections[rowIndex] ?? false;
    return defaultKeeperIndices(group, txArr, priorityIds).has(rowIndex);
}

/** Indices of members whose `keyOf` value is NOT the majority within the group (empty if all equal). */
export function outlierIndexSet(members: MergedTx[], keyOf: (mt: MergedTx) => string): Set<number> {
    const counts = new Map<string, number>();
    for (const mt of members) {
        const k = keyOf(mt);
        counts.set(k, (counts.get(k) ?? 0) + 1);
    }
    if (counts.size <= 1) return new Set();
    let majority = '';
    let best = -1;
    for (const [k, c] of counts) {
        if (c > best) {
            best = c;
            majority = k;
        }
    }
    const out = new Set<number>();
    for (const mt of members) if (keyOf(mt) !== majority) out.add(mt.index);
    return out;
}
