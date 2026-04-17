/**
 * Storage Utilities — User-scoped localStorage helpers.
 *
 * Provides helper functions that namespace localStorage keys by userId
 * so that per-user preferences don't collide in multi-user deployments.
 *
 * Pattern: lf_{userId}_{baseKey}
 *
 * @module utils/storage
 */

import {get} from 'svelte/store';
import {currentUser} from '$lib/stores/auth';

/**
 * Build a user-scoped localStorage key.
 * Falls back to 'anon' if no user is logged in.
 *
 * @param baseKey - The base key (e.g., 'assetsViewMode')
 * @returns Scoped key (e.g., 'lf_42_assetsViewMode')
 */
export function getUserStorageKey(baseKey: string): string {
    const user = get(currentUser);
    const userId = user?.id ?? 'anon';
    return `lf_${userId}_${baseKey}`;
}

/**
 * Read a value from user-scoped localStorage.
 * Returns defaultValue if not found, not in browser, or on error.
 */
export function getUserStorage(baseKey: string, defaultValue: string): string {
    if (typeof window === 'undefined') return defaultValue;
    try {
        const key = getUserStorageKey(baseKey);
        const stored = localStorage.getItem(key);
        return stored ?? defaultValue;
    } catch {
        return defaultValue;
    }
}

/**
 * Write a value to user-scoped localStorage.
 */
export function setUserStorage(baseKey: string, value: string): void {
    if (typeof window === 'undefined') return;
    try {
        const key = getUserStorageKey(baseKey);
        localStorage.setItem(key, value);
    } catch {
        // Ignore storage errors (e.g., quota exceeded in private browsing)
    }
}
