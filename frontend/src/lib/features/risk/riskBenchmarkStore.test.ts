import {beforeEach, describe, expect, it, vi} from 'vitest';

// The shared `$app/environment` mock reports `browser: false`, which turns every
// storage path in this store into a no-op. Nothing below would run against it.
// Same override, and same Map-backed `localStorage`, as `chartSettingsStore.test.ts`.
vi.mock('$app/environment', () => ({browser: true}));

/**
 * The asset cache `resolveRiskBenchmark()` consults, reduced to the two facts its
 * contract reads: which ids exist, and whether the list has arrived.
 *
 * `getAssetInfo` answers null until `ensureAssetsLoaded()` has really loaded, as the
 * real store does ("Returns null if the cache hasn't loaded the id yet"), which gives
 * the "await" in the contract its teeth: a resolution that judged before the list was
 * in would answer `unknown` for a benchmark that exists. A load can fail two ways, and
 * both leave the cache unloaded: it rejects (`failure`), or — what `entityStore`
 * actually does — it resolves anyway and only logs (`silent`, "Fail silently"). Either
 * way "the asset is gone" cannot be told from "the list did not come", which is why
 * neither may cost the reader the choice they stored.
 */
const assetCache = vi.hoisted(() => ({
    ids: new Set<number>(),
    loaded: false,
    failure: null as Error | null,
    silent: false,
}));

vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => {
    const actual = await importOriginal<typeof import('$lib/stores/reference/assetStore')>();
    const info = (id: number) => (assetCache.loaded && assetCache.ids.has(id) ? {id, display_name: `Synthetic asset ${id}`, currency: 'EUR', active: true} : null);
    return {
        ...actual,
        ensureAssetsLoaded: vi.fn(async () => {
            // One real hop, as a network round trip would take: a caller that does not
            // await sees the cache still unloaded.
            await Promise.resolve();
            if (assetCache.failure) throw assetCache.failure;
            if (assetCache.silent) return;
            assetCache.loaded = true;
        }),
        getAssetInfo: vi.fn((id: number) => info(id)),
        getAllAssets: vi.fn(() => (assetCache.loaded ? [...assetCache.ids].map((id) => info(id)) : [])),
    };
});

import {transitionClientSession} from '$lib/stores/app/clientSession';
import {ensureAssetsLoaded} from '$lib/stores/reference/assetStore';

import {resolveRiskBenchmark, riskBenchmark} from './riskBenchmarkStore.svelte';

/**
 * The benchmark L3 measures against — one choice for every scope.
 *
 * The store keeps its value at module level and re-reads storage only when the
 * resolved account changes, so each test claims a fresh account: that is the
 * store's own re-hydration trigger, not a back door.
 */

let backing = new Map<string, string>();
let userSeq = 0;

function storageKeyFor(userId: string): string {
    return `lf_${userId}_risk_benchmark_asset`;
}

function freshUser(): string {
    const userId = `risk-benchmark-u${++userSeq}`;
    transitionClientSession(userId);
    return userId;
}

beforeEach(() => {
    backing = new Map();
    Object.defineProperty(globalThis, 'localStorage', {
        configurable: true,
        writable: true,
        value: {
            getItem: (key: string) => backing.get(key) ?? null,
            setItem: (key: string, value: string) => void backing.set(key, value),
            removeItem: (key: string) => void backing.delete(key),
            clear: () => backing.clear(),
        },
    });
});

describe('riskBenchmark', () => {
    it('gives every scope the same benchmark', () => {
        // The Dashboard and a broker page are two mounts of one component. Were the
        // benchmark component state they would drift apart, and "vs" would quietly
        // mean something different on each page.
        freshUser();
        riskBenchmark.set(42);

        expect(riskBenchmark.assetId).toBe(42);
    });

    it('survives a reload', () => {
        const user = freshUser();
        riskBenchmark.set(42);

        expect(backing.get(storageKeyFor(user))).toBe('42');
    });

    it('scopes the choice to the reader', () => {
        const first = freshUser();
        riskBenchmark.set(42);

        freshUser();
        // A benchmark is a personal choice; the next account must not inherit it.
        expect(riskBenchmark.assetId).toBeNull();

        transitionClientSession(first);
        expect(riskBenchmark.assetId).toBe(42);
    });

    it('clears the choice rather than persisting an empty one', () => {
        const user = freshUser();
        riskBenchmark.set(42);
        riskBenchmark.set(null);

        expect(riskBenchmark.assetId).toBeNull();
        expect(backing.has(storageKeyFor(user))).toBe(false);
    });

    it('refuses a stored value that is not an asset id', () => {
        // Trusting one would send a nonsense `comparison_asset_id` to the backend,
        // and the answer would come back looking perfectly ordinary.
        //
        // The payload is seeded under an account's key *before* that account becomes
        // current: re-transitioning to the account already in hand would leave
        // `hydratedKey` matching and the store would never re-read, so the assertion
        // would pass without the guard ever being consulted.
        for (const corrupt of ['0', '-3', '4.5', 'MSCI World', '']) {
            const pending = `risk-benchmark-corrupt${++userSeq}`;
            backing.set(storageKeyFor(pending), corrupt);
            transitionClientSession(pending);

            expect(riskBenchmark.assetId).toBeNull();
        }
    });

    it('accepts a stored value that is an asset id — the guard is not a blanket refusal', () => {
        const pending = `risk-benchmark-valid${++userSeq}`;
        backing.set(storageKeyFor(pending), '42');
        transitionClientSession(pending);

        expect(riskBenchmark.assetId).toBe(42);
    });

    it('refuses to be set to something that is not an asset id', () => {
        freshUser();
        riskBenchmark.set(42);
        riskBenchmark.set(0);
        expect(riskBenchmark.assetId).toBeNull();

        riskBenchmark.set(42);
        riskBenchmark.set(2.5);
        expect(riskBenchmark.assetId).toBeNull();
    });

    it('still agrees across scopes when storage is unavailable', () => {
        // A browser with storage disabled is not a broken app: it is an app without
        // persistence, and the two pages must still show the same benchmark.
        freshUser();
        Object.defineProperty(globalThis, 'localStorage', {
            configurable: true,
            writable: true,
            value: {
                getItem: () => {
                    throw new Error('storage disabled');
                },
                setItem: () => {
                    throw new Error('storage disabled');
                },
                removeItem: () => {
                    throw new Error('storage disabled');
                },
            },
        });

        expect(() => riskBenchmark.set(42)).not.toThrow();
        expect(riskBenchmark.assetId).toBe(42);
    });
});

/**
 * `resolveRiskBenchmark()` — what "the current benchmark" means once assets can disappear.
 *
 * Every picker opens on the shared choice, and is empty only when nothing is set
 * (developer decision, 01/10/2026). A stored id is therefore confirmed against the asset
 * list before anyone uses it — but the answer is a *reading*, never a correction:
 *
 *   - nothing stored → `{state: 'none', assetId: null}`, and the list is not loaded for nothing;
 *   - a stored id the list holds → `{state: 'set', assetId: id}`;
 *   - a stored id the list does not hold → `{state: 'unknown', assetId: null}` — and that
 *     covers a deleted asset *and* a load that failed, which `ensureLoaded()` cannot tell
 *     apart: it resolves even when the request fails ("Fail silently").
 *
 * And in every case **the store is left as it was**: the stored id and its user-scoped
 * key are never written. Clearing an id that merely could not be confirmed would destroy
 * a valid choice on one failed request — and would not even close the window it aims at,
 * since `assets.id` is an INTEGER PRIMARY KEY without AUTOINCREMENT and SQLite may hand a
 * deleted id to the next asset (decision of 01/10/2026). Each case below snapshots the
 * whole storage and spies on `riskBenchmark.set`, so a write by either road is caught.
 */
describe('resolveRiskBenchmark', () => {
    /**
     * A reader coming back to a choice made on an earlier visit: the id is in storage
     * before the account becomes current, so the store hydrates from it exactly as it
     * would after a reload — not from an in-memory `set()` this session made.
     */
    function returningReader(stored: string): string {
        const userId = `risk-benchmark-returning${++userSeq}`;
        backing.set(storageKeyFor(userId), stored);
        transitionClientSession(userId);
        return userId;
    }

    /** Resolve, and prove the store came out exactly as it went in: same storage, no `set()` call. */
    async function resolveWithoutWriting(): Promise<unknown> {
        const storageBefore = new Map(backing);
        const assetIdBefore = riskBenchmark.assetId;
        const set = vi.spyOn(riskBenchmark, 'set');
        try {
            const answer = await resolveRiskBenchmark();
            expect(set, 'resolveRiskBenchmark() wrote the shared store: it may read the choice, never change it').not.toHaveBeenCalled();
            expect(new Map(backing), 'resolveRiskBenchmark() changed localStorage').toEqual(storageBefore);
            expect(riskBenchmark.assetId, 'resolveRiskBenchmark() changed the stored id').toBe(assetIdBefore);
            return answer;
        } finally {
            set.mockRestore();
        }
    }

    beforeEach(() => {
        assetCache.ids = new Set();
        assetCache.loaded = false;
        assetCache.failure = null;
        assetCache.silent = false;
        vi.mocked(ensureAssetsLoaded).mockClear();
    });

    it('answers none without loading the asset list when nothing is stored', async () => {
        freshUser();
        // A list that *would* confirm an id, so a needless load cannot hide behind an empty one.
        assetCache.ids = new Set([42]);

        expect(await resolveWithoutWriting()).toEqual({state: 'none', assetId: null});

        expect(ensureAssetsLoaded, 'nothing is stored: there is nothing to confirm, so the asset list must not be fetched for it').not.toHaveBeenCalled();
    });

    it('answers set for a stored id the asset list holds, and leaves the store as it was', async () => {
        const user = returningReader('42');
        assetCache.ids = new Set([7, 42]);

        // Confirmable only after the list is in: `getAssetInfo` answers null before that,
        // so a resolution that did not await `ensureAssetsLoaded()` would answer unknown.
        expect(await resolveWithoutWriting()).toEqual({state: 'set', assetId: 42});

        expect(ensureAssetsLoaded).toHaveBeenCalled();
        expect(backing.get(storageKeyFor(user))).toBe('42');
    });

    it('answers unknown for a stored id the asset list does not hold, and leaves it stored', async () => {
        // A neighbouring reader of this browser chose the same id: nothing about either
        // reader's storage may move because one list did not contain it.
        const otherReader = `risk-benchmark-neighbour${++userSeq}`;
        backing.set(storageKeyFor(otherReader), '42');
        const user = returningReader('42');
        assetCache.ids = new Set([7]);

        expect(await resolveWithoutWriting()).toEqual({state: 'unknown', assetId: null});

        expect(ensureAssetsLoaded).toHaveBeenCalled();
        expect(riskBenchmark.assetId, 'an id the list does not hold is still the stored choice').toBe(42);
        expect(backing.get(`lf_${user}_risk_benchmark_asset`), 'lf_<user>_risk_benchmark_asset lost the stored id').toBe('42');
        expect(backing.get(storageKeyFor(otherReader))).toBe('42');
    });

    it('answers unknown when the asset list load rejects — without rejecting itself, and without touching the stored id', async () => {
        const user = returningReader('42');
        assetCache.ids = new Set([42]);
        assetCache.failure = new Error('synthetic: asset list unreachable');

        await expect(resolveWithoutWriting(), 'a failed load must resolve, and resolve as unknown: the picker still has to open, without a guess').resolves.toEqual({state: 'unknown', assetId: null});

        expect(ensureAssetsLoaded).toHaveBeenCalled();
        expect(riskBenchmark.assetId).toBe(42);
        expect(backing.get(storageKeyFor(user)), 'a choice was destroyed on the strength of a failed request').toBe('42');
    });

    it('answers unknown when the asset list load fails silently — the way ensureLoaded() fails — without touching the stored id', async () => {
        const user = returningReader('42');
        // The id would be confirmed by a list that arrived; this one resolves without arriving.
        assetCache.ids = new Set([42]);
        assetCache.silent = true;

        expect(await resolveWithoutWriting()).toEqual({state: 'unknown', assetId: null});

        expect(ensureAssetsLoaded).toHaveBeenCalled();
        expect(riskBenchmark.assetId).toBe(42);
        expect(backing.get(storageKeyFor(user)), 'a choice was destroyed on the strength of a load that never arrived').toBe('42');
    });
});
