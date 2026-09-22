/**
 * privacyStore with no browser — the SSR guard.
 *
 * Deliberately a separate file from privacyStore.test.ts: the two need opposite
 * values of `browser`, and `vi.mock` is file-scoped, so holding both in one file
 * would mean importing the store twice and reasoning about which module-level
 * `$state` a given call landed on. Vitest isolates files, which is the reason
 * chartSettingsStoreSsr.test.ts exists in the same shape.
 *
 * The shared `$app/environment` mock already reports `browser: false`, which is
 * what SvelteKit gives a load running on the server.
 *
 * The control for "it never read storage" cannot live here — proving the reader
 * works needs `browser: true`, which is the other file. privacyStore.test.ts
 * asserts `getItem` *is* called with this key and that a stored `'1'` hydrates
 * to on; what this file adds is that the same seeded `'1'` is ignored on the
 * server. Together they say the guard is the thing making the difference.
 */
import {describe, expect, it, vi} from 'vitest';

const backing = new Map<string, string>([['librefolio-privacy', '1']]);
const getItem = vi.fn((key: string) => backing.get(key) ?? null);
const setItem = vi.fn();

Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    writable: true,
    value: {getItem, setItem, removeItem: vi.fn(), clear: vi.fn()},
});

const {PRIVACY_STORAGE_KEY, isPrivacyEnabled, isPrivacyPersisted, setPrivacyEnabled, togglePrivacy} = await import('./privacyStore.svelte');

describe('privacyStore on the server', () => {
    it('hydrates off and never touches storage', () => {
        // The seeded payload is the exact one that hydrates to `true` in the
        // browser (privacyStore.test.ts pins that). Off here is therefore the
        // guard, not an empty store.
        expect(backing.get(PRIVACY_STORAGE_KEY)).toBe('1');
        expect(isPrivacyEnabled()).toBe(false);
        expect(getItem).not.toHaveBeenCalled();
    });

    it('accepts a write without throwing and without reaching storage', () => {
        expect(() => setPrivacyEnabled(true)).not.toThrow();

        expect(setItem).not.toHaveBeenCalled();
        // In-memory the value applies — there is no second source of truth —
        // but the store does not claim it was saved, which is the honest answer
        // for a process that has no storage to save it to.
        expect(isPrivacyEnabled()).toBe(true);
        expect(isPrivacyPersisted()).toBe(false);

        expect(() => togglePrivacy()).not.toThrow();
        expect(isPrivacyEnabled()).toBe(false);
        expect(setItem).not.toHaveBeenCalled();
        expect(getItem).not.toHaveBeenCalled();
    });
});
