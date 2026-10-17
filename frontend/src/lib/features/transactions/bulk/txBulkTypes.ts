/**
 * The types of TransactionBulkModal's state, shared by the modal and its section components
 * (features/transactions/bulk/). Cut from TransactionBulkModal.svelte (FE8a).
 */
import type {TransactionTypeCode} from '$lib/features/transactions/transactionTypeStore';
import type {ImportTodo} from '$lib/features/transactions/txPayloadHelpers';

/** Fields displayed & editable in the grid — pure data, no metadata. */
export interface DraftFields {
    broker_id: number;
    asset_id: number | null;
    type: TransactionTypeCode;
    date: string;
    quantity: string;
    cash: {code: string; amount: string} | null;
    tags: string[];
    description: string;
    asset_event_id: number | null;
    cost_basis_override: {code: string; amount: string} | null;
    /** UI-only: tracks whether cost_basis is auto-calculated, manual, or not applicable.
     *  null = field not applicable for this type/side (forbidden).
     *  'auto' = WAC will be calculated automatically.
     *  'manual' = user provided explicit value. */
    cost_basis_mode: 'auto' | 'manual' | null;
}

/** Pending operation — one per row in the BulkModal (visible + hidden partners).
 *  Tagged union: 'create' for new rows, 'edit' for existing DB rows.
 *  If `pairedWith` is set, this op is the hidden partner of a paired row.
 *  `link_uuid` is the shared pairing UUID for backend payloads (WAC, commit). */
export type PendingOp = ({op: 'create'} | {op: 'edit'; txId: number; markedDelete: boolean; addedViaPicker?: boolean}) & {
    tempId: string;
    /** Stamped at creation (`nextCreatedSeq`): keeps new rows of the same day in the order they were added. */
    createdSeq: number;
    fields: DraftFields;
    pairedWith?: string;
    link_uuid?: string | null;
    /** W4b: partner on inaccessible broker — read-only sentinel */ inaccessible?: boolean;
    /**
     * Type this row had before a *mixed* promote reassigned it.
     *
     * A mixed promote (one saved row + one new one) is executed by the backend,
     * which expects both halves in their pre-promote types and derives the target
     * itself. The grid, however, must already show the promoted type. The two
     * therefore diverge for exactly one row, and this remembers the wire value.
     *
     * Unset for create+create promotes: those carry no backend promote at all —
     * the pair is formed by a shared link_uuid — so the target type is what must
     * be sent.
     */
    promoteFromType?: TransactionTypeCode | null;
    /** Cached WAC result from validate — transient, not sent to backend */ _wacCache?: WacResultEntry | null;
    /** Currency hint for WAC target — null = backend decides */ wacCurrencyHint?: string | null;
    /** BRIM import field todos — blocker severity prevents commit until resolved */ todos?: ImportTodo[];
};

/** Single source of truth: WAC results per auto-op (keyed by tempId).
 *  Contains full details (qualifying_txs) for FormModal display. */
export type WacResultEntry = {
    wac: {code: string; amount: string} | null;
    qualifying_txs: Array<Record<string, any>>;
    missing_pairs: string[];
};

/** Minimal suggest entry — all display data is read live from ops[].
 *  This is future-proof: if fields change in ops, suggestions auto-update. */
export type SuggestEntry = {tempIdA: string; tempIdB: string; targetType: string; isDB?: boolean; dbCandidateId?: number};
