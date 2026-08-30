/**
 * Pure helpers extracted from LotCustodyModal.svelte.
 *
 * The modal shows a lot's current custody split and its full event chronology.
 * The pure work — unwrapping the OpenAPI scalar-or-array fields, resolving a
 * broker (with a synthetic `#id` placeholder when the list has no match),
 * building the stable per-event key, classifying an event into a timeline marker,
 * grouping custody slices by (type, broker) and summing their quantities, and the
 * history sort order — is lifted here so it can be unit tested without mounting
 * the modal.
 *
 * Note the deliberate divergence from `unifiedLotsTableHelpers.findBroker`: that
 * one returns `null` on a miss (the table then falls back through its icon chain),
 * while {@link getBroker} here returns a synthetic `{id, name: '#<id>'}` so the
 * modal's broker badge always has a label. Same idea, genuinely different
 * post-condition — kept as two functions on purpose.
 *
 * @module brokers/lots/lotCustodyModalHelpers
 */

import type {BrokerLike} from '$lib/utils/broker/brokerColors';
import {safeDecimal} from '$lib/types';

/** The marker kinds the modal's timeline draws. */
export type EventMarkerKind = 'open' | 'transfer' | 'close' | 'split';

/** One aggregated custody position: a broker (or in-transit) holding a quantity. */
export interface CustodyGroup {
    key: string;
    brokerId: number | null;
    custodyType: string;
    broker: BrokerLike | null;
    quantity: number;
}

/** Unwrap the OpenAPI scalar-or-array shape: an array yields its first element (or null), else the value itself. */
export function unwrapScalar<T>(value: T | T[] | null | undefined): T | null | undefined {
    return Array.isArray(value) ? (value[0] ?? null) : value;
}

/**
 * Resolve a broker by id. Returns `null` only when there is no id at all;
 * otherwise a matching broker, or a synthetic `{id, name: '#<id>'}` placeholder
 * so the badge is never blank.
 */
export function getBroker(brokerId: number | (number | null)[] | null | undefined, brokers: ReadonlyArray<BrokerLike>): BrokerLike | null {
    const scalarBrokerId = unwrapScalar<number | null>(brokerId) ?? null;
    if (scalarBrokerId == null) return null;
    return brokers.find((broker) => broker.id === scalarBrokerId) ?? {id: scalarBrokerId, name: `#${scalarBrokerId}`};
}

/** The subset of an event needed to key it stably across renders. */
interface HistoryKeyEvent {
    date: string;
    kind: string;
    transaction_id: number;
    // Widened to absorb the generated client's redundant scalar-or-array union; only ?? '' is applied.
    related_transaction_id?: number | (number | null)[] | null;
    fragment_id?: string | (string | null)[] | null;
}

/** A stable, collision-resistant key for a timeline event (empty parts for absent optional ids). */
export function historyKey(event: HistoryKeyEvent): string {
    return `${event.date}:${event.kind}:${event.transaction_id}:${event.related_transaction_id ?? ''}:${event.fragment_id ?? ''}`;
}

/**
 * Classify an event kind into a timeline marker: buys and inbound adjustments
 * open, transfers are transfers, a split is a split, and everything else
 * (sells, outbound adjustments) closes.
 */
export function eventMarkerKind(event: {kind: string}): EventMarkerKind {
    if (event.kind === 'BUY' || event.kind === 'ADJUSTMENT_IN') return 'open';
    if (event.kind === 'TRANSFER_DEPART' || event.kind === 'TRANSFER_ARRIVE') return 'transfer';
    if (event.kind === 'SPLIT') return 'split';
    return 'close';
}

/** The subset of a custody slice needed to group it. */
interface CustodySlice {
    // Optional to match the generated client (`broker_id?`); the redundant array arm is unwrapped.
    broker_id?: number | (number | null)[] | null;
    custody_type: string;
    quantity: unknown;
}

/**
 * Group custody slices by (custody type, broker), summing quantities. A broker
 * object is resolved only for `BROKER` custody (in-transit stays broker-less).
 * Preserves first-seen order.
 */
export function groupCustodySlices(slices: ReadonlyArray<CustodySlice>, brokers: ReadonlyArray<BrokerLike>): CustodyGroup[] {
    const groups: CustodyGroup[] = [];
    const byKey = new Map<string, CustodyGroup>();
    for (const slice of slices) {
        const brokerId = unwrapScalar<number | null>(slice.broker_id) ?? null;
        const custodyType = slice.custody_type;
        const key = `${custodyType}:${brokerId ?? 'none'}`;
        const quantity = safeDecimal(slice.quantity) ?? 0;
        let group = byKey.get(key);
        if (!group) {
            group = {
                key,
                brokerId,
                custodyType,
                broker: custodyType === 'BROKER' ? getBroker(brokerId, brokers) : null,
                quantity: 0,
            };
            byKey.set(key, group);
            groups.push(group);
        }
        group.quantity += quantity;
    }
    return groups;
}

/** History sort order: by ISO date ascending, breaking ties by transaction id. */
export function compareHistoryEvents(left: {date: string; transaction_id: number}, right: {date: string; transaction_id: number}): number {
    const dateOrder = left.date.localeCompare(right.date);
    if (dateOrder !== 0) return dateOrder;
    return left.transaction_id - right.transaction_id;
}

/** Product of two nullable numbers, or `null` when either is absent (e.g. opening value = qty × price). */
export function multiplyOrNull(a: number | null, b: number | null): number | null {
    return a != null && b != null ? a * b : null;
}
