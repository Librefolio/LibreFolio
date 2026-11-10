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
import {normalizeDecimalInput} from '$lib/utils/core/parseDecimalInput';
import {eventTypesForTx} from './events/eventTypes';
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
    /** The transaction's cash delta (positive = received) and its currency (null without cash), and its asset delta (FB-19). */
    amount: string;
    currency: string | null;
    quantity: string;
}

export interface ReconciliationFilters {
    brokerId?: number;
    assetId?: number;
}

type ServerCandidate = {id: number; date: string; type: string; value: string | number; currency: string; is_auto: boolean};
type ServerItem = {transaction_id: number; broker_id: number; asset_id: number; date: string; type: string; status: ReconciliationStatus; candidates?: ServerCandidate[]; amount: string | number; currency?: string | null; quantity: string | number};

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
        amount: String(item.amount),
        currency: item.currency ?? null,
        quantity: String(item.quantity),
    }));
}

/**
 * The event types a row's event can have (FB-19): the one of its transaction's type, or, for an adjustment, a split or a
 * price adjustment — more than one means the user chooses when creating it.
 */
export function eventTypesOfRow(row: Pick<ReconciliationRow, 'type'>): readonly string[] {
    return row.type === 'ADJUSTMENT' ? eventTypesForTx('ADJUSTMENT') : [row.type];
}

/**
 * The event type to name on a row: the one the server found (the first candidate), else the one its transaction's type
 * asks for; `null` for an adjustment with no event yet, which may become a split or a price adjustment.
 */
export function eventTypeToShow(row: Pick<ReconciliationRow, 'type' | 'candidates'>): string | null {
    if (row.candidates.length > 0) return row.candidates[0].type;
    const types = eventTypesOfRow(row);
    return types.length === 1 ? types[0] : null;
}

/**
 * The value to suggest for the event a row misses (FB-19), as the transaction form suggests it: the transaction's cash, as
 * an unsigned amount, when it is in the asset's currency. Nothing for a row without cash (an adjustment) or in another
 * currency: the user types it.
 */
export function suggestedEventAmount(row: Pick<ReconciliationRow, 'type' | 'amount' | 'currency'>, assetCurrency: string | undefined): string {
    if (row.type === 'ADJUSTMENT' || !row.currency || !assetCurrency || row.currency !== assetCurrency) return '';
    const plain = row.amount.replace(/^-/, '');
    return /[1-9]/.test(plain) ? plain : '';
}

/** What a new event holds: a plain unsigned decimal of at most six decimals (``AssetEvent.value`` keeps six), or `null`. */
export function plainEventAmount(text: string): string | null {
    const raw = normalizeDecimalInput(text.trim());
    if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(raw) || !/[1-9]/.test(raw)) return null;
    return (raw.split('.')[1] ?? '').replace(/0+$/, '').length > 6 ? null : raw;
}

/** One event to create: the row it is for, its type, and its value (a plain decimal text) in the asset's currency. */
export interface NewEventEntry {
    row: ReconciliationRow;
    type: string;
    amount: string;
    currency: string;
}

/**
 * Create the events some rows miss, in ONE request (`POST /assets/events`, mode `create`, one item per asset; all or nothing).
 * The event is on the transaction's day, with the asset's currency. Rejects with the request's error (`eventSaveErrorMessage` words it):
 * nothing was created then. Nothing is linked: the caller reads the list again, and the rows now have an event.
 */
export async function createMissingEvents(entries: readonly NewEventEntry[]): Promise<void> {
    if (entries.length === 0) return;
    const byAsset = new Map<number, NewEventEntry[]>();
    for (const entry of entries) byAsset.set(entry.row.assetId, [...(byAsset.get(entry.row.assetId) ?? []), entry]);
    await zodiosApi.upsert_events_bulk_api_v1_assets_events_post(
        // A new event never overwrites another (decision 20): `create`; the value goes as its digits, never through a float (C-97b)
        [...byAsset].map(([assetId, list]) => ({
            asset_id: assetId,
            mode: 'create' as const,
            events: list.map((entry) => ({date: entry.row.date, type: entry.type, value: {code: entry.currency, amount: entry.amount}})),
        })),
    );
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
