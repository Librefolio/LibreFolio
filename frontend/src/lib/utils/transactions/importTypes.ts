/**
 * The value objects the import wizard's Step-4 logic passes around.
 *
 * These were defined inline in `ImportWizardModal.svelte`, which meant the pure
 * functions that read and build them — the duplicate matcher, the parse→merge
 * transform, the compare-cell builders — could not be extracted or unit-tested
 * without dragging a 5000-line component into jsdom. Moving the *types* out (no
 * behaviour, no reactive state) is what unlocks moving the *functions* out, in
 * `importDedup.ts`, `importMerge.ts` and `importCompare.ts`.
 *
 * The component still owns the reactive `$state` that holds instances of these;
 * this module owns only their shape.
 */
import type {TransactionCreateItem} from '$lib/types';
import type {BrimDuplicateMatch} from '$lib/types/files';
import type {ImportTodo} from '$lib/utils/transactions/txPayloadHelpers';
import type {AssetGroup, ExtractedAsset, SimilarityLink} from '$lib/utils/assetGrouping';

/** A per-row duplicate verdict. `pending_*` come from the bulk editor's unsaved rows. */
export type DuplicateStatus = 'unique' | 'possible' | 'likely' | 'pending_duplicate' | 'pending_possible_duplicate';

/** How strongly a cross-file duplicate group overlaps: total (`sure`) vs partial (`probable`). */
export type DuplicateTier = 'sure' | 'probable';

/** One parsed transaction as it travels through the review step, with its resolution metadata. */
export interface MergedTx {
    index: number;
    sourceFileId: string;
    tx: TransactionCreateItem;
    selected: boolean;
    duplicateStatus: DuplicateStatus;
    dupMatches: BrimDuplicateMatch[];
    todos: ImportTodo[];
    dupGroupKey?: string;
    dupTier?: DuplicateTier;
    dupKeeperIndex?: number;
    dupKeeperFileName?: string;
    isDupKeeper?: boolean;
    /** For a bulk-modal pending duplicate: the matched unsaved transaction (for side-by-side compare). */
    dupPendingMatch?: TransactionCreateItem;
}

/** A cluster of cross-file duplicate rows the resolver step presents together. */
export interface DuplicateGroup {
    key: string;
    memberIndices: number[];
    tier: DuplicateTier;
}

/**
 * One asset to resolve — after unification, **one per security**, not one per file.
 *
 * The wizard allocates a fake id per instrument per file, so the same BTP read from two
 * layouts used to arrive here twice: two identical entries in every picker, two candidate
 * searches, and two duplicates created at the end. The grouping step folds those members into
 * a single resolution whose `extracted*` fields are the representative's and whose `group*`
 * fields carry the **union** of everything the members knew.
 *
 * The union is provenance-ordered, not preference-ordered: electing which ISIN leads belongs
 * to the second stage, when the group meets a database asset that has its own to defend.
 */
export interface AssetResolution {
    fakeAssetId: number;
    extractedSymbol: string | null;
    extractedIsin: string | null;
    extractedName: string | null;
    candidates: Array<{asset_id: number; symbol?: string | null; isin?: string | null; name: string; match_confidence: string}>;
    resolvedAssetId: number | null;
    txCount: number;
    sourceFiles: string[];
    notices: Array<{kind: string; reason: string}>;
    /** Every code the group carries, representative included. */
    groupIsins: string[];
    groupSymbols: string[];
    groupNames: string[];
    /** The per-file assets folded into this one. A lone asset has exactly one. */
    groupMembers: ExtractedAsset[];
    groupState: AssetGroup['state'];
    groupLinks: SimilarityLink[];
    /** The user already elected the leading code on the unification step: do not ask again. */
    groupPrimaryIsin: boolean;
    groupPrimarySymbol: boolean;
}

/** The identity a row is deduplicated on: the fields two rows must share to be the same movement. */
export interface DedupKey {
    broker: string;
    type: string;
    date: string;
    quantity: number;
    cashCode: string | null;
    cashAmount: number | null;
    costOverride: number | null;
    assetIdentity: string;
}

/** Quantities within this fraction of each other are the same lot size. */
export const QUANTITY_TOLERANCE = 0.0001;

/** Cash amounts within this many currency units are the same countervalue. */
export const AMOUNT_TOLERANCE = 0.01;

/** Match-confidence ranking, strongest first. Unknown tiers sort last (see `?? 9` at call sites). */
export const CONF_ORDER: Record<string, number> = {exact: 0, high: 1, medium: 2, low: 3};
