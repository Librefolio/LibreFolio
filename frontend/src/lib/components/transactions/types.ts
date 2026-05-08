/**
 * Shared transaction types — single source of truth for TXReadItem and related interfaces.
 *
 * Previously duplicated across: +page.svelte, TransactionsTable, TransactionBulkModal,
 * TransactionFormModal, TransactionDeleteModal, TransactionPickerModal, BulkDeleteLinkedPairModal.
 *
 * Plan C — Phase 07 Part 4 Round 6 (post-completion polish).
 */

export interface TXReadItem {
    id: number;
    broker_id: number;
    asset_id?: number | null;
    type: string;
    date: string;
    quantity: string;
    cash?: {code: string; amount: string} | null;
    related_transaction_id?: number | null;
    partner_broker_id?: number | null;
    tags?: string[] | null;
    description?: string | null;
    cost_basis_override?: string | null;
    asset_event_id?: number | null;
    created_at?: string;
    updated_at?: string;
}

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

export interface AssetEvent {
    id: number;
    asset_id: number;
    type: string;
    date: string;
    value: string;
    currency: string;
    is_auto: boolean;
    notes?: string | null;
}

