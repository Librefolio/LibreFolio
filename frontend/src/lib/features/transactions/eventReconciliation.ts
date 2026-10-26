/**
 * Link again the transactions that have no asset event (lot X5-3: N68, «Relink events»).
 *
 * A currency change deletes an asset's events (but its SPLITs), so the transactions linked to them lose the link
 * (`asset_event_id` NULL); a dividend or an interest booked before its event was synced has none either.
 * `GET /transactions/event-reconciliation` lists, for the caller, the transactions that could link an asset event and have none,
 * each with the events it could take: the same asset, the SAME DAY, the type that corresponds. Its `status` is `unique` (one
 * candidate), `none` (no event that day) or `several`. The server links nothing: this module reads the list, picks the rows that
 * are safe to link by themselves (the unique ones) and links them through the commit the app already uses (`txCommitApi.ts`,
 * `updates: [{id, asset_event_id}]`, atomic: any issue and nothing is linked). The screen over it is `EventReconciliationModal.svelte`.
 *
 * @module features/transactions/eventReconciliation
 */

import {zodiosApi} from '$lib/api';
import {commitTransactions, type TxValidationIssue} from './txCommitApi';

export type ReconciliationStatus = 'unique' | 'none' | 'several';

/** An asset event a transaction could take. */
export interface ReconciliationCandidate {
    id: number;
    date: string;
    type: string;
    value: string | number;
    currency: string;
    isAuto: boolean;
}

/** A transaction without its event, with the events it could take. */
export interface ReconciliationRow {
    transactionId: number;
    brokerId: number;
    assetId: number;
    date: string;
    type: string;
    status: ReconciliationStatus;
    candidates: ReconciliationCandidate[];
}

export interface ReconciliationFilters {
    brokerId?: number;
    assetId?: number;
}

type ServerCandidate = {id: number; date: string; type: string; value: string | number; currency: string; is_auto: boolean};
type ServerItem = {transaction_id: number; broker_id: number; asset_id: number; date: string; type: string; status: ReconciliationStatus; candidates?: ServerCandidate[]};

/** The transactions that could link an event and have none. Rejects when the request fails. */
export async function loadEventReconciliation(filters: ReconciliationFilters = {}): Promise<ReconciliationRow[]> {
    const queries: Record<string, number> = {};
    if (filters.brokerId !== undefined) queries.broker_id = filters.brokerId;
    if (filters.assetId !== undefined) queries.asset_id = filters.assetId;
    const answer = (await zodiosApi.event_reconciliation_api_v1_transactions_event_reconciliation_get(Object.keys(queries).length > 0 ? {queries} : undefined)) as ServerItem[];
    return answer.map((item) => ({
        transactionId: item.transaction_id,
        brokerId: item.broker_id,
        assetId: item.asset_id,
        date: item.date,
        type: item.type,
        status: item.status,
        candidates: (item.candidates ?? []).map((candidate) => ({id: candidate.id, date: candidate.date, type: candidate.type, value: candidate.value, currency: candidate.currency, isAuto: candidate.is_auto})),
    }));
}

/** The rows safe to link by themselves: marked unique and holding exactly one candidate (a double check of the server's status). */
export function uniqueRows(rows: readonly ReconciliationRow[]): ReconciliationRow[] {
    return rows.filter((row) => row.status === 'unique' && row.candidates.length === 1);
}

/** The commit's `updates` for the unique rows: each transaction takes its one candidate. */
export function linkUpdates(rows: readonly ReconciliationRow[]): Array<{id: number; asset_event_id: number}> {
    return uniqueRows(rows).map((row) => ({id: row.transactionId, asset_event_id: row.candidates[0].id}));
}

/**
 * Link the unique rows in ONE atomic commit. Nothing to link is no request and `linked: false`, not an error; a refusal links
 * nothing (`issues` are the commit's) and is not retried with fewer rows.
 */
export async function linkReconciliation(rows: readonly ReconciliationRow[]): Promise<{linked: boolean; issues: TxValidationIssue[]}> {
    const updates = linkUpdates(rows);
    if (updates.length === 0) return {linked: false, issues: []};
    const result = await commitTransactions({updates});
    return {linked: result.committed, issues: result.issues};
}
