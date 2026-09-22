/**
 * privacyStore — hydration, persistence, and the write that fails.
 *
 * The store keeps its preference in module-level `$state` hydrated once at
 * import, so every test here takes a **freshly imported instance**
 * (`vi.resetModules()` + a dynamic `import()`), exactly as
 * chartSettingsStore.test.ts re-reads storage by claiming a new account. That is
 * the store's own initialisation path, not a back door — and it means no test
 * inherits its neighbour's flag, in any order.
 *
 * The load-bearing case is the last one. A write that throws leaves the
 * preference on in memory and absent on disk: the session masks, the reload does
 * not, and the user believes in a protection that is not there. `persisted` is
 * the only way that fact leaves the store, so it is asserted together with what
 * a subsequent reload actually sees.
 *
 * Every "it is not there" assertion is paired with the working-storage case that
 * shows the same check seeing it there.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';

// The shared `$app/environment` mock reports `browser: false`, which makes every
// storage path in this store a no-op: nothing below would run against it. The
// server behaviour is pinned separately, in privacyStoreSsr.test.ts.
vi.mock('$app/environment', () => ({browser: true}));

let backing = new Map<string, string>();
let getItem = vi.fn((key: string) => backing.get(key) ?? null);
let setItem = vi.fn((key: string, value: string) => void backing.set(key, value));

// Installed before the first import below, deliberately. The store hydrates at
// module init, so an instance imported while `localStorage` is still undefined
// would hydrate off a ReferenceError swallowed by its own try/catch — "off" for
// a reason that has nothing to do with an absent key, and a default-value test
// that passes without ever exercising the read.
Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {
        getItem: (key: string) => getItem(key),
        setItem: (key: string, value: string) => setItem(key, value),
        removeItem: (key: string) => void backing.delete(key),
        clear: () => backing.clear(),
    },
});

type PrivacyStore = typeof import('./privacyStore.svelte');

/** A store instance that has just hydrated from whatever `backing` holds. */
async function loadStore(): Promise<PrivacyStore> {
    vi.resetModules();
    return await import('./privacyStore.svelte');
}

const {PRIVACY_STORAGE_KEY} = await loadStore();

/** Write a raw payload under the store's key *before* the store reads it. */
function seed(raw: string): void {
    backing.set(PRIVACY_STORAGE_KEY, raw);
}

function stored(): string | undefined {
    return backing.get(PRIVACY_STORAGE_KEY);
}

beforeEach(() => {
    backing = new Map();
    getItem = vi.fn((key: string) => backing.get(key) ?? null);
    setItem = vi.fn((key: string, value: string) => void backing.set(key, value));
});

describe('privacyStore — hydration', () => {
    it('is off when the key has never been written', async () => {
        const store = await loadStore();

        expect(store.isPrivacyEnabled()).toBe(false);
        // The off above is the answer to a real lookup that missed, not a guard
        // that skipped the read: without this line the assertion would hold just
        // as well on a store that never consulted storage at all.
        expect(getItem).toHaveBeenCalledWith(PRIVACY_STORAGE_KEY);
    });

    it('reads a stored "1" at module init', async () => {
        seed('1');
        const store = await loadStore();

        expect(store.isPrivacyEnabled()).toBe(true);
        expect(getItem).toHaveBeenCalledWith(PRIVACY_STORAGE_KEY);
    });

    it('reads a stored "0" as off', async () => {
        seed('0');

        expect((await loadStore()).isPrivacyEnabled()).toBe(false);
    });

    it('treats only the exact "1" as on', async () => {
        for (const raw of ['0', '', ' 1', '1 ', 'true', 'yes', 'on']) {
            backing = new Map();
            seed(raw);
            expect((await loadStore()).isPrivacyEnabled()).toBe(false);
        }

        // Control: the same loop machinery, with the one payload that does mean
        // on. Without it, every case above would also pass on a store hardwired
        // to false.
        backing = new Map();
        seed('1');
        expect((await loadStore()).isPrivacyEnabled()).toBe(true);
    });

    it('survives a browser that refuses to read storage at all', async () => {
        // Safari private browsing throws on access rather than returning null.
        getItem.mockImplementation(() => {
            throw new DOMException('SecurityError');
        });
        seed('1');

        const store = await loadStore();
        expect(store.isPrivacyEnabled()).toBe(false);
        expect(getItem).toHaveBeenCalled();
    });
});

describe('privacyStore — writing the preference', () => {
    it('applies the value and stores "1"', async () => {
        const store = await loadStore();
        expect(store.isPrivacyEnabled()).toBe(false);

        store.setPrivacyEnabled(true);

        expect(store.isPrivacyEnabled()).toBe(true);
        expect(setItem).toHaveBeenCalledWith(PRIVACY_STORAGE_KEY, '1');
        expect(stored()).toBe('1');
    });

    it('stores an explicit "0" rather than clearing the key', async () => {
        const store = await loadStore();
        store.setPrivacyEnabled(true);
        store.setPrivacyEnabled(false);

        expect(store.isPrivacyEnabled()).toBe(false);
        expect(stored()).toBe('0');
    });

    it('flips both the live value and the stored one on toggle', async () => {
        const store = await loadStore();

        store.togglePrivacy();
        expect(store.isPrivacyEnabled()).toBe(true);
        expect(stored()).toBe('1');

        store.togglePrivacy();
        expect(store.isPrivacyEnabled()).toBe(false);
        expect(stored()).toBe('0');
    });

    it('hands the preference to the next load', async () => {
        const first = await loadStore();
        first.setPrivacyEnabled(true);

        // A brand-new instance, reading the storage the previous one wrote:
        // this is the whole contract, and neither half proves it alone.
        expect((await loadStore()).isPrivacyEnabled()).toBe(true);

        const third = await loadStore();
        third.setPrivacyEnabled(false);
        expect((await loadStore()).isPrivacyEnabled()).toBe(false);
    });
});

describe('privacyStore — a write the browser refuses', () => {
    it('reports itself persisted before anything has been written', async () => {
        expect((await loadStore()).isPrivacyPersisted()).toBe(true);
    });

    it('keeps the preference in memory while reporting it unpersisted', async () => {
        setItem.mockImplementation(() => {
            throw new DOMException('QuotaExceededError');
        });
        const store = await loadStore();

        expect(() => store.setPrivacyEnabled(true)).not.toThrow();

        // The user's session is masked…
        expect(store.isPrivacyEnabled()).toBe(true);
        // …and the store says so out loud instead of swallowing it.
        expect(store.isPrivacyPersisted()).toBe(false);
        expect(stored()).toBeUndefined();

        // Positive control, same store, same call: with storage working again
        // the flag clears and the key appears. Without this the three lines
        // above would read identically on a store that never persists anything.
        setItem.mockImplementation((key: string, value: string) => void backing.set(key, value));
        store.setPrivacyEnabled(true);
        expect(store.isPrivacyPersisted()).toBe(true);
        expect(stored()).toBe('1');
    });

    it('does not carry a refused write across a reload', async () => {
        setItem.mockImplementation(() => {
            throw new DOMException('QuotaExceededError');
        });
        const store = await loadStore();
        store.setPrivacyEnabled(true);
        expect(store.isPrivacyEnabled()).toBe(true);

        // This is what `persisted: false` is warning about: the next page load
        // comes back unmasked. The assertion is not a wish, it is the fact the
        // store must be able to tell the user about.
        expect((await loadStore()).isPrivacyEnabled()).toBe(false);

        // Control: the same sequence with storage working survives the reload,
        // so the false above is the refused write and not a reload that always
        // forgets.
        setItem.mockImplementation((key: string, value: string) => void backing.set(key, value));
        const working = await loadStore();
        working.setPrivacyEnabled(true);
        expect((await loadStore()).isPrivacyEnabled()).toBe(true);
    });

    it('leaves a read failure out of the persisted flag', async () => {
        getItem.mockImplementation(() => {
            throw new DOMException('SecurityError');
        });
        const store = await loadStore();

        // A read that fails costs the hydration, not the promise about writes:
        // nothing has been written yet, so there is nothing out of sync.
        expect(store.isPrivacyEnabled()).toBe(false);
        expect(store.isPrivacyPersisted()).toBe(true);
    });
});
