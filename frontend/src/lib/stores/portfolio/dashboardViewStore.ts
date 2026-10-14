/**
 * dashboardViewStore — the Dashboard's currency and broker filter, for the session (page cache,
 * phase 1, decision E3), as `dateRangeStore` already keeps the period.
 *
 * Without it a return (the ‹ arrow, the sidebar) restarts from the base currency and every broker,
 * asks a report under another key, and the cache cannot serve it.
 *
 * Persisted in sessionStorage per user: a reload in the same tab finds it again, another account
 * never reads it, and a logout clears it. No sessionStorage (SSR) answers the defaults.
 *
 * @module stores/portfolio/dashboardViewStore
 */

import {getClientSessionUserId, registerClientSessionReset} from '$lib/stores/app/clientSession';

export interface DashboardView {
    /** The currency the user chose; null = the base currency. */
    targetCurrency: string | null;
    /** The brokers the filter keeps; empty = every owned broker. */
    brokerIds: number[];
}

const STORAGE_PREFIX = 'librefolio_dashboardView:';

function defaults(): DashboardView {
    return {targetCurrency: null, brokerIds: []};
}

function sessionStore(): Storage | null {
    try {
        return typeof sessionStorage === 'undefined' ? null : sessionStorage;
    } catch {
        return null;
    }
}

function storageKey(): string | null {
    const userId = getClientSessionUserId();
    return userId == null ? null : `${STORAGE_PREFIX}${userId}`;
}

function normalized(value: unknown): DashboardView {
    const view = value !== null && typeof value === 'object' ? (value as Record<string, unknown>) : {};
    const currency = view.targetCurrency;
    const brokerIds = Array.isArray(view.brokerIds) ? view.brokerIds.filter((id): id is number => Number.isInteger(id) && (id as number) > 0) : [];
    return {
        targetCurrency: typeof currency === 'string' && currency.trim() !== '' ? currency.trim() : null,
        brokerIds: [...new Set(brokerIds)],
    };
}

/** The current user's view; the defaults when nothing was chosen, nothing is stored, or it is unreadable. */
export function readDashboardView(): DashboardView {
    const store = sessionStore();
    const key = storageKey();
    if (!store || !key) return defaults();
    try {
        const raw = store.getItem(key);
        return raw ? normalized(JSON.parse(raw)) : defaults();
    } catch {
        return defaults();
    }
}

/** Merge a choice into the current user's view and persist it. */
export function writeDashboardView(patch: Partial<DashboardView>): void {
    const store = sessionStore();
    const key = storageKey();
    if (!store || !key) return;
    try {
        store.setItem(key, JSON.stringify(normalized({...readDashboardView(), ...patch})));
    } catch {
        // Storage full or disabled: the view simply does not last.
    }
}

/** Forget every user's view (logout or account change). */
export function resetDashboardView(): void {
    const store = sessionStore();
    if (!store) return;
    try {
        const keys: string[] = [];
        for (let index = 0; index < store.length; index += 1) {
            const key = store.key(index);
            if (key?.startsWith(STORAGE_PREFIX)) keys.push(key);
        }
        for (const key of keys) store.removeItem(key);
    } catch {
        // Nothing stored, nothing to forget.
    }
}

registerClientSessionReset('dashboardViewStore', resetDashboardView);
