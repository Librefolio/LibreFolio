/**
 * The parse → merge transform, lifted out of `ImportWizardModal.svelte`.
 *
 * `buildMergedTransactions` is the pure heart of Step 4: given the per-file parse
 * responses, the brokers and the ids the bulk editor marked for deletion, it flattens
 * every file's transactions into one indexed list and allocates a **globally-unique**
 * fake asset id per instrument per file (each plugin numbers its fakes from the same
 * base downward, so ids collide across files — remapping keeps a resolution from being
 * shared between two different instruments). It returns the three structures the rest
 * of the step consumes; the component still owns the grouping/duplicate-rebuild passes
 * that mutate reactive `$state`, because those are not pure.
 *
 * Extracting this is what lets the merge be unit-tested without mounting the wizard and
 * driving it through upload → select → analyze first.
 */
import type {TransactionCreateItem, BrimParseResponse} from '$lib/types';
import type {BrimDuplicateMatch} from '$lib/types/files';
import type {ImportTodo} from '$lib/utils/transactions/txPayloadHelpers';
import {isFakeAssetId, FAKE_ASSET_ID_BASE} from '$lib/utils/brim/isFakeAssetId';
import {CONF_ORDER, type DuplicateStatus, type MergedTx, type AssetResolution} from '$lib/utils/transactions/importTypes';
import {duplicateStatusAllowsAutoSelect} from '$lib/utils/transactions/importDedup';

/** The parse-result fields the merge reads — reduced to what the loop touches. */
export interface MergeSourceResult {
    fileId: string;
    brokerId: number;
    status: 'pending' | 'parsing' | 'done' | 'error' | string;
    response: BrimParseResponse | null;
}

/** The broker fields the merge reads, to decide the "before the account opened" cutoff. */
export interface MergeBroker {
    id: number;
    opened_at?: string | null;
}

/** What `buildMergedTransactions` hands back to the component's Step-4 state. */
export interface MergeResult {
    txArr: MergedTx[];
    assetMap: Map<number, AssetResolution>;
    /** Which file each global fake id came from — the grouping layer needs the provenance. */
    fileIdOfFake: Map<number, string>;
}

/** If exactly one candidate is an exact match, its asset id — else null. Used to auto-bind. */
export function uniqueExactCandidateId(candidates: AssetResolution['candidates']): number | null {
    const exact = (candidates ?? []).filter((c) => String(c.match_confidence).toLowerCase() === 'exact');
    return exact.length === 1 ? exact[0].asset_id : null;
}

/** Union two candidate lists, keeping the strongest confidence per asset id, sorted strongest-first. */
export function mergeCandidates(a: AssetResolution['candidates'], b: AssetResolution['candidates']): AssetResolution['candidates'] {
    const byId = new Map<number, AssetResolution['candidates'][number]>();
    for (const candidate of [...a, ...b]) {
        const existing = byId.get(candidate.asset_id);
        if (!existing || (CONF_ORDER[candidate.match_confidence] ?? 9) < (CONF_ORDER[existing.match_confidence] ?? 9)) byId.set(candidate.asset_id, candidate);
    }
    return [...byId.values()].sort((x, y) => (CONF_ORDER[x.match_confidence] ?? 9) - (CONF_ORDER[y.match_confidence] ?? 9));
}

/**
 * Flatten every done parse result into one indexed transaction list plus its asset
 * resolutions, remapping each file's fake asset ids into a globally-unique range.
 *
 * Pure: it reads its arguments and returns fresh structures, cloning each transaction so
 * a re-run after a broker/opening edit never mutates the stored parse response.
 */
export function buildMergedTransactions(parseResults: MergeSourceResult[], brokers: MergeBroker[], pendingDeleteTxIds: number[]): MergeResult {
    const txArr: MergedTx[] = [];
    const assetMap = new Map<number, AssetResolution>();
    /** Which file each global fake id came from — the grouping layer needs the provenance. */
    const fileIdOfFake = new Map<number, string>();
    let globalIndex = 0;
    // Global unique fake-id allocator. Each source file's plugin emits fake ids from the
    // same FAKE_ASSET_ID_BASE downward, so ids collide across files. Re-map every file's
    // fake ids to a globally-unique fake id (kept within the isFakeAssetId range) so a
    // resolution is never shared between two different instruments from different files.
    let nextFakeId = FAKE_ASSET_ID_BASE;
    // DB ids the user marked for deletion in the bulk editor — excluded from DB dup matching.
    const pendingDeleteSet = new Set<number>(pendingDeleteTxIds);

    for (const result of parseResults.filter((r) => r.status === 'done' && r.response)) {
        const resp = result.response!;
        // Per-file map: original plugin fake id → globally-unique fake id.
        const fakeRemap = new Map<number, number>();
        // Build todos map by tx_index
        const todosMap = new Map<number, ImportTodo[]>();
        for (const ft of resp.field_todos ?? []) {
            const idx = (ft as any).tx_index as number;
            const list = todosMap.get(idx) ?? [];
            list.push({field: (ft as any).field, severity: (ft as any).severity, reasonCode: (ft as any).reason_code, message: (ft as any).message, evidence: (ft as any).evidence ?? [], context: (ft as any).context ?? undefined});
            todosMap.set(idx, list);
        }

        // Build duplicate sets (by tx_row_index) and match details map.
        // DB matches against transactions the user has marked for deletion in the bulk
        // editor are dropped: a re-imported row whose only DB match is a to-be-deleted
        // row is no longer a duplicate (status stays 'unique', auto-selectable). A row
        // with some surviving matches keeps its tier with the reduced match list.
        const dups = resp.duplicates;
        const likelyEntries = (dups && !Array.isArray(dups) ? (dups.tx_likely_duplicates ?? []) : []) as any[];
        const possibleEntries = (dups && !Array.isArray(dups) ? (dups.tx_possible_duplicates ?? []) : []) as any[];
        const likelySet = new Set<number>();
        const possibleSet = new Set<number>();
        const dupMatchesMap = new Map<number, BrimDuplicateMatch[]>();
        const survivingMatches = (entry: any): {matches: BrimDuplicateMatch[]; hadMatches: boolean} => {
            const raw = (entry.tx_existing_matches ?? []) as BrimDuplicateMatch[];
            if (raw.length === 0) return {matches: raw, hadMatches: false};
            return {matches: raw.filter((m) => !pendingDeleteSet.has(m.existing_tx_id)), hadMatches: true};
        };
        for (const d of likelyEntries) {
            const {matches, hadMatches} = survivingMatches(d);
            if (hadMatches && matches.length === 0) continue; // all DB matches deleted → not a duplicate
            likelySet.add(d.tx_row_index as number);
            dupMatchesMap.set(d.tx_row_index as number, matches);
        }
        for (const d of possibleEntries) {
            const {matches, hadMatches} = survivingMatches(d);
            if (hadMatches && matches.length === 0) continue; // all DB matches deleted → not a duplicate
            possibleSet.add(d.tx_row_index as number);
            dupMatchesMap.set(d.tx_row_index as number, matches);
        }

        for (const [txIdx, tx] of (resp.transactions ?? []).entries()) {
            let dupStatus: DuplicateStatus = 'unique';
            if (likelySet.has(txIdx)) dupStatus = 'likely';
            else if (possibleSet.has(txIdx)) dupStatus = 'possible';
            const openedAt = brokers.find((b) => b.id === result.brokerId)?.opened_at ?? null;
            // The second `tx.date ?? ''` can never take its nullish branch: reaching this third
            // conjunct requires the middle one (`String(tx.date ?? '') !== ''`) to be true, which
            // already rules out a nullish date. Istanbul flags that `?? ''` as a half-covered
            // branch; it is dead by short-circuit, not an untested state. Left intentionally.
            const beforeOpening = openedAt != null && String(tx.date ?? '') !== '' && String(tx.date ?? '') < openedAt;

            // Clone so re-mapping the fake asset id never mutates the stored parse result
            // (mergeAllTransactions may run again after a broker/opening edit).
            const txClone = {...(tx as TransactionCreateItem)} as TransactionCreateItem;
            const origAssetId = typeof txClone.asset_id === 'number' ? txClone.asset_id : null;
            if (origAssetId !== null && isFakeAssetId(origAssetId)) {
                let globalFakeId = fakeRemap.get(origAssetId);
                if (globalFakeId === undefined) {
                    globalFakeId = nextFakeId--;
                    fakeRemap.set(origAssetId, globalFakeId);
                    fileIdOfFake.set(globalFakeId, result.fileId);
                    const mapping = (resp.asset_mappings ?? []).find((m: any) => m.fake_asset_id === origAssetId);
                    if (mapping) {
                        const candidates = (mapping.candidates ?? []) as AssetResolution['candidates'];
                        const selected = typeof mapping.selected_asset_id === 'number' ? (mapping.selected_asset_id as number) : null;
                        assetMap.set(globalFakeId, {
                            fakeAssetId: globalFakeId,
                            extractedSymbol: (mapping.extracted_symbol as string | null) ?? null,
                            extractedIsin: (mapping.extracted_isin as string | null) ?? null,
                            extractedName: (mapping.extracted_name as string | null) ?? null,
                            candidates,
                            // Auto-bind an exact-ISIN match even if the backend left it unselected.
                            resolvedAssetId: selected ?? uniqueExactCandidateId(candidates),
                            txCount: 0,
                            sourceFiles: [],
                            notices: ((mapping.notices ?? []) as Array<{kind?: string; reason?: string}>).map((n) => ({kind: String(n.kind ?? ''), reason: String(n.reason ?? '')})),
                            groupIsins: [],
                            groupSymbols: [],
                            groupNames: [],
                            groupMembers: [],
                            groupState: 'single',
                            groupLinks: [],
                            groupPrimaryIsin: false,
                            groupPrimarySymbol: false,
                        });
                    }
                }
                (txClone as {asset_id?: number | null}).asset_id = globalFakeId;
            }

            txArr.push({
                index: globalIndex++,
                sourceFileId: result.fileId,
                tx: txClone,
                selected: !beforeOpening && duplicateStatusAllowsAutoSelect(dupStatus),
                duplicateStatus: dupStatus,
                dupMatches: dupMatchesMap.get(txIdx) ?? [],
                todos: todosMap.get(txIdx) ?? [],
            });
        }
    }

    return {txArr, assetMap, fileIdOfFake};
}
