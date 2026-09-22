import {beforeEach, describe, expect, it, vi} from 'vitest';

// The shared `$app/environment` mock reports `browser: false`, which turns every
// storage path in this store into a no-op. Nothing below would run against it.
// Same override, and same Map-backed `localStorage`, as `chartSettingsStore.test.ts`.
vi.mock('$app/environment', () => ({browser: true}));

import {transitionClientSession} from '$lib/stores/app/clientSession';

import {riskBenchmark} from './riskBenchmarkStore.svelte';

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
