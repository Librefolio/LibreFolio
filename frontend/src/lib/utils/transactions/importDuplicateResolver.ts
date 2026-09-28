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
import {hasFirmOutsideCollision, normalizeDedupDescription} from './importDedup';
import type {DuplicateGroup, MergedTx} from './importTypes';

export interface GroupPartition {
    primaryIndex: number;
    memberIndices: number[];
    crossFile: boolean;
}

/**
 * Partition a duplicate group by normalized description. Each partition is a set of rows
 * that share the numeric/fixed key AND the (whitespace-insensitive) description. The primary
 * is the partition member from the highest-priority file (`priorityIds` order) among those
 * that do not collide firmly with the database or the bulk editor; when every member does,
 * it is the highest-priority member, for display only. The rest are exact cross-file twins.
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
        const eligible = part.filter((mt) => !hasFirmOutsideCollision(mt));
        const pool = eligible.length > 0 ? eligible : part;
        const primary = pool.reduce((best, mt) => (rank(mt) < rank(best) ? mt : best), pool[0]);
        const files = new Set(part.map((mt) => mt.sourceFileId));
        return {primaryIndex: primary.index, memberIndices: part.map((mt) => mt.index), crossFile: files.size >= 2};
    });
}

/**
 * Keep exactly one primary per description-partition (highest file priority). A cross-file
 * duplicate keeps a single copy; genuinely-distinct rows that only share the numeric key
 * (different descriptions) are each their own partition primary, so all are kept. A partition
 * whose every copy already exists — in the database or in the bulk editor — keeps none.
 */
export function defaultKeeperIndices(group: DuplicateGroup, txArr: MergedTx[], priorityIds: string[]): Set<number> {
    const byIndex = new Map(txArr.map((mt) => [mt.index, mt] as const));
    const primaries = groupPartitions(group, txArr, priorityIds).map((p) => p.primaryIndex);
    return new Set(
        primaries.filter((idx) => {
            const row = byIndex.get(idx);
            return row !== undefined && !hasFirmOutsideCollision(row);
        }),
    );
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

/** The user's explicit choices in the resolver: the groups they touched, and the keep flag per row. */
export interface ResolverChoices {
    touchedKeys: Set<string>;
    selections: Record<number, boolean>;
}

/** Choices carried onto a new duplicate report, plus the groups the user has not seen in their current form. */
export interface CarriedResolverChoices extends ResolverChoices {
    /** New or changed groups of the new report, in its order. Their choices are not carried. */
    changed: DuplicateGroup[];
}

/** The identity of a group across two reports: its members, whatever their order. */
function memberSignature(group: DuplicateGroup): string {
    return [...group.memberIndices].sort((a, b) => a - b).join(',');
}

/**
 * Carry the resolver's explicit choices from one duplicate report to the next.
 *
 * A group is recognised by its members, not by its key: the key embeds the asset identity, which
 * turns from an extracted code into a database id when the user binds an unresolved asset — the
 * very change that triggers a recheck — while the members stay the same. A touched group found
 * again keeps its choices under its new key; an untouched one keeps nothing and recomputes its
 * defaults. A group with no same-member predecessor is `changed`: the user never arbitrated it in
 * this form.
 *
 * With the rows of both reports, a touched group is also `changed` when one of its copies started
 * or stopped colliding firmly with the database or the bulk editor. The database match narrows to
 * the bound asset only once the asset is resolved, so binding a group to another asset can turn a
 * unique copy into a stored duplicate — and a choice made before that would import it.
 */
export function carryResolverChoices(previousGroups: DuplicateGroup[], previous: ResolverChoices, nextGroups: DuplicateGroup[], rows?: {previousRows: MergedTx[]; nextRows: MergedTx[]}): CarriedResolverChoices {
    const previousBySignature = new Map(previousGroups.map((group) => [memberSignature(group), group] as const));
    const before = new Map((rows?.previousRows ?? []).map((row) => [row.index, row] as const));
    const after = new Map((rows?.nextRows ?? []).map((row) => [row.index, row] as const));
    const verdictChanged = (index: number): boolean => {
        const was = before.get(index);
        const now = after.get(index);
        return was !== undefined && now !== undefined && hasFirmOutsideCollision(was) !== hasFirmOutsideCollision(now);
    };

    const touchedKeys = new Set<string>();
    const selections: Record<number, boolean> = {};
    const changed: DuplicateGroup[] = [];
    for (const group of nextGroups) {
        const predecessor = previousBySignature.get(memberSignature(group));
        if (!predecessor) {
            changed.push(group);
            continue;
        }
        if (!previous.touchedKeys.has(predecessor.key)) continue;
        if (group.memberIndices.some(verdictChanged)) {
            changed.push(group);
            continue;
        }
        touchedKeys.add(group.key);
        for (const index of group.memberIndices) {
            const kept = previous.selections[index];
            if (kept !== undefined) selections[index] = kept;
        }
    }
    return {touchedKeys, selections, changed};
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
