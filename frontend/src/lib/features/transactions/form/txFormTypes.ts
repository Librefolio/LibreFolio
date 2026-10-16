/**
 * The types of TransactionFormModal's state, shared by the modal and its section components
 * (features/transactions/form/). Cut from TransactionFormModal.svelte (FE8a).
 */
import type {TransactionTypeCode} from '$lib/features/transactions/transactionTypeStore';

/** One issue of POST /transactions/validate, as the form reads it. */
export interface ValidationIssue {
    operation: 'create' | 'update' | 'delete';
    index: number;
    ref_id?: number | null;
    error: string;
    code?: string | null;
    params?: Record<string, any> | null;
    field?: string | null;
    /** Pydantic loc path (e.g. "body.creates.0.broker_id"). */
    loc?: string;
}

/** The form's editable row: the "From" side when the type is paired. */
export interface FormDraft {
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
    link_uuid: string | null;
}

/** Dual-form "To" side state — only used when pairLayout !== null. */
export interface DualDraftTo {
    /** For transfer_asset / transfer_cash: the "To" broker. */
    broker_id: number;
    /** For fx: the "To" cash (different currency). */
    cash: {code: string; amount: string} | null;
    /** Destination date, which may differ from the source date. */
    date: string;
    /** Quantity for the "To" side (transfer_asset: receiver qty). */
    quantity?: string;
    /** Cost basis override for the receiver (transfer_asset only). */
    cost_basis_override?: {code: string; amount: string} | null;
}

/** The weighted average cost the WAC preview shows: from the BulkModal, or from the form's own validation. */
export interface TxFormWacResult {
    wac: {code: string; amount: string} | null;
    qualifying_txs: Array<Record<string, any>>;
    missing_pairs: string[];
}
