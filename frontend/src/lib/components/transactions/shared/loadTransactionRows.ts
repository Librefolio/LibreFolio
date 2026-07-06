/**
 * loadTransactionRows.ts — Shared data-loading helpers for pages that mount
 * `<TransactionsTable>`.
 *
 * `TransactionsTable` is a pure presentational component (see its own
 * docstring: "this component does not perform navigation or open modals on
 * its own") — it never fetches data itself. Every consuming page is
 * responsible for supplying `mainRows`/`partnerRows`/`eventTooltipMap`.
 *
 * `loadPartnerRows` and `loadEventTooltipMap` were originally written inline
 * in `/transactions/+page.svelte` (server-side unfiltered: `mainRows` already
 * contains virtually every transaction, so partners are almost always
 * present). Extracted here so that pages filtering server-side (e.g. the
 * broker detail page, which fetches only one broker's transactions) can
 * reuse the exact same logic instead of duplicating it — a paired partner on
 * a different broker would otherwise be missing from the main set.
 *
 * @module components/transactions/shared/loadTransactionRows
 */

import {zodiosApi} from '$lib/api';
import type {AssetEvent, TXReadItem} from '../types';

/**
 * Fetch any transactions referenced via `related_transaction_id` that are
 * NOT already present in `main` (e.g. the other leg of a paired transaction
 * sitting on a different broker, filtered out of a broker-scoped fetch).
 */
export async function loadPartnerRows(main: TXReadItem[]): Promise<TXReadItem[]> {
    const mainIds = new Set(main.map((r) => r.id));
    const missing = new Set<number>();
    for (const r of main) {
        const partner = r.related_transaction_id;
        if (partner != null && !mainIds.has(partner)) missing.add(partner);
    }
    if (missing.size === 0) return [];
    try {
        const res = (await zodiosApi.query_transactions_api_v1_transactions_get({queries: {ids: [...missing]}} as never)) as TXReadItem[];
        return res ?? [];
    } catch (e) {
        console.warn('Failed to load partner rows:', e);
        return [];
    }
}

/** Build a `Map<eventId, AssetEvent>` for every linked-event tooltip needed by `rows`. */
export async function loadEventTooltipMap(rows: TXReadItem[]): Promise<Map<number, AssetEvent>> {
    const ids = [...new Set(rows.map((r) => r.asset_event_id).filter((id): id is number => id != null))];
    if (ids.length === 0) return new Map();
    try {
        const res = await zodiosApi.get_events_by_ids_api_v1_assets_events_get({queries: {ids}});
        const map = new Map<number, AssetEvent>();
        for (const item of res.items ?? []) {
            for (const ev of item.events ?? []) {
                if (ev.id != null) {
                    map.set(ev.id, {
                        id: ev.id,
                        asset_id: item.asset_id,
                        type: ev.type,
                        date: ev.date,
                        value: typeof ev.value === 'object' ? ev.value.amount : String(ev.value),
                        currency: typeof ev.value === 'object' ? ev.value.code : '',
                        is_auto: ev.is_auto ?? false,
                        notes: (Array.isArray(ev.notes) ? ev.notes.join(', ') : ev.notes) ?? null,
                    });
                }
            }
        }
        return map;
    } catch (e) {
        console.warn('Failed to load event tooltips:', e);
        return new Map();
    }
}
