/**
 * Entity Store Factory — Generic session-level cache for "list-bounded" entities.
 *
 * Pattern shared across asset / broker / (future) similar collections that:
 *  - have a finite, user-scoped list fetched once via a single endpoint
 *  - are looked up frequently by id from many components
 *  - mutate via modals (create / edit / delete) that must keep the cache fresh
 *
 * Each instance owns:
 *  - a Map<Id, T> of normalized entries
 *  - a `loaded` flag + in-flight `loadPromise` (concurrent ensureLoaded sharing)
 *  - a reactive `version` writable (subscribe to retrigger derived expressions)
 *
 * **Invariant — `invalidate` resets `loaded`**: when an entry is evicted, the
 * next `ensureLoaded()` MUST re-fetch (otherwise the cache silently keeps a
 * partial view). This was the root cause of the `assetStore` icon-stale bug.
 *
 * **Merge semantics**: `merge(items)` upserts partial payloads into existing
 * entries (preserving fields not present in the patch) and only enforces the
 * `requiredFields` guard for **new** entries — so it can be safely called
 * with a PATCH request body (FE knows the new field values even when the BE
 * response only carries `{success, id}`).
 *
 * @module stores/entityStore
 */

import {writable, type Readable} from 'svelte/store';

// ============================================================================
// TYPES
// ============================================================================

export interface EntityStoreOptions<T extends object, Id> {
    /** Async loader that returns the full list of raw items. */
    loader: () => Promise<unknown[]>;
    /** Extract the id from a normalized item. */
    getId: (item: T) => Id;
    /** Transform a raw API item into the canonical T shape. */
    normalize: (raw: Record<string, unknown>) => T;
    /**
     * Required fields that MUST be present (truthy / non-empty) for a *new*
     * entry to be merged. Existing entries can be partially upserted.
     */
    requiredFields?: ReadonlyArray<keyof T>;
}

export interface EntityStore<T extends object, Id> {
    /** Lazy load — idempotent, concurrent-safe. */
    ensureLoaded: () => Promise<void>;
    /** Force discard + reload. */
    refreshAll: () => Promise<void>;
    /** Sync lookup. Returns `null` if id is null/undefined or not cached. */
    get: (id: Id | null | undefined) => T | null;
    /** Snapshot of all cached entries. */
    getAll: () => T[];
    /** True after the first successful load. */
    isLoaded: () => boolean;
    /**
     * Upsert items into the cache. Each raw item is normalized; for existing
     * entries the new fields are merged on top of the cached ones. New entries
     * are skipped if they fail the `requiredFields` guard.
     */
    merge: (items: ReadonlyArray<Record<string, unknown> | Partial<T>>) => void;
    /**
     * Remove entries by id and reset `loaded` so the next `ensureLoaded()`
     * re-fetches. No network call by itself.
     */
    invalidate: (idOrIds: Id | ReadonlyArray<Id>) => void;
    /** Reactive version counter — bumped on every cache mutation. */
    version: Readable<number>;
}

// ============================================================================
// FACTORY
// ============================================================================

export function createEntityStore<T extends object, Id = number>(opts: EntityStoreOptions<T, Id>): EntityStore<T, Id> {
    const map = new Map<Id, T>();
    let loaded = false;
    let loadPromise: Promise<void> | null = null;

    const versionStore = writable(0);
    const bump = (): void => versionStore.update((v) => v + 1);

    async function ensureLoaded(): Promise<void> {
        if (loaded) return;
        if (loadPromise) return loadPromise;
        loadPromise = (async () => {
            try {
                const items = (await opts.loader()) as Array<Record<string, unknown>>;
                map.clear();
                for (const it of items) {
                    const info = opts.normalize(it);
                    map.set(opts.getId(info), info);
                }
                loaded = true;
                bump();
            } catch (e) {
                // Fail silently — get() returns null for unknown ids.
                // eslint-disable-next-line no-console
                console.error('[entityStore] Failed to load:', e);
            } finally {
                loadPromise = null;
            }
        })();
        return loadPromise;
    }

    async function refreshAll(): Promise<void> {
        loaded = false;
        loadPromise = null;
        map.clear();
        bump();
        return ensureLoaded();
    }

    function get(id: Id | null | undefined): T | null {
        if (id == null) return null;
        return map.get(id) ?? null;
    }

    function getAll(): T[] {
        return Array.from(map.values());
    }

    function isLoaded(): boolean {
        return loaded;
    }

    function merge(items: ReadonlyArray<Record<string, unknown> | Partial<T>>): void {
        let changed = false;
        for (const raw of items) {
            if (raw == null) continue;
            const info = opts.normalize(raw as Record<string, unknown>);
            const id = opts.getId(info);
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            if (id == null || (id as any) === '') continue;

            const existing = map.get(id);
            if (!existing) {
                // New entry — enforce required fields if declared.
                if (opts.requiredFields) {
                    const missing = opts.requiredFields.some((f) => {
                        const v = info[f];
                        return v == null || v === '';
                    });
                    if (missing) continue;
                }
                map.set(id, info);
                changed = true;
            } else {
                // Existing entry — partial upsert: only overwrite keys explicitly
                // set in `info` (skip undefined). `null` is meaningful (clears).
                const merged: T = {...existing};
                for (const k of Object.keys(info) as Array<keyof T>) {
                    const v = info[k];
                    if (v !== undefined) {
                        (merged as Record<string, unknown>)[k as string] = v as unknown;
                    }
                }
                map.set(id, merged);
                changed = true;
            }
        }
        if (changed) bump();
    }

    function invalidate(idOrIds: Id | ReadonlyArray<Id>): void {
        const ids = Array.isArray(idOrIds) ? (idOrIds as ReadonlyArray<Id>) : [idOrIds as Id];
        let changed = false;
        for (const id of ids) {
            if (map.delete(id)) changed = true;
        }
        if (changed) {
            // INVARIANT: invalidate must reset `loaded` so next `ensureLoaded`
            // re-fetches the missing entries (otherwise the cache silently
            // serves a partial view forever).
            loaded = false;
            bump();
        }
    }

    return {
        ensureLoaded,
        refreshAll,
        get,
        getAll,
        isLoaded,
        merge,
        invalidate,
        version: {subscribe: versionStore.subscribe},
    };
}
