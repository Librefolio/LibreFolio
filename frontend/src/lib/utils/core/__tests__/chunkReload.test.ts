/**
 * chunkReload.test.ts — the cure for «Failed to fetch dynamically imported module» (H5-2, backlog X-R84).
 *
 * After an app update (the old hashed chunks are gone) or a network hiccup, a lazy `import()` fails; SvelteKit
 * shows «500 Internal Error» and the user stays there until they reload by hand. The cure reloads the page ONCE,
 * guarded against loops. Two pure pieces live in `chunkReload.ts`, tested here with everything injected:
 *
 *   - `isChunkLoadError(error)` — does this error look like a browser's dynamic-import failure? Matched on the
 *     error's OWN message only (never `cause`), case-insensitive, for the four wordings browsers and Vite use.
 *   - `reloadOnceForChunkError(options)` — the loop guard. The timestamp of the last automatic reload lives in
 *     sessionStorage under `lf-chunk-reload-at`; inside `windowMs` a second request is refused (a chunk that still
 *     fails after the reload shows the error page — never a loop), and an unreadable/unwritable storage refuses too
 *     (without a guard a reload could loop; the page keeps working).
 *
 * No clock and no storage is real here: `now`, `storage` and `reload` are injected, so the file is deterministic and
 * runs in the node environment (where there is no `window` at all — which is itself a case: no storage, no reload).
 * The defaults (sessionStorage, Date.now, window.location.reload) and the event wiring are the business of
 * `chunkReload.dom.test.ts`; the SvelteKit hook of `src/hooks.client.test.ts`.
 *
 * Red today: `../chunkReload` does not exist, so the import fails and every case below is red.
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {describe, expect, it, vi} from 'vitest';
import {isChunkLoadError, reloadOnceForChunkError} from '../chunkReload';

const STORAGE_KEY = 'lf-chunk-reload-at';
const T0 = 1_700_000_000_000;
const DEFAULT_WINDOW_MS = 60_000;

/** The four wordings a browser (or Vite) gives a failed dynamic import, with a realistic tail. */
const BROWSER_MESSAGES: Record<string, string> = {
    chrome: 'Failed to fetch dynamically imported module: https://folio.example/_app/immutable/nodes/7.4f2a9c1e.js',
    firefox: 'error loading dynamically imported module: https://folio.example/_app/immutable/nodes/7.4f2a9c1e.js',
    safari: 'Importing a module script failed.',
    vite_css: 'Unable to preload CSS for /_app/immutable/assets/7.9b1d2e44.css',
};

class FakeStorage {
    readonly data = new Map<string, string>();
    readonly calls: string[] = [];
    getItem(key: string): string | null {
        this.calls.push(`get:${key}`);
        return this.data.get(key) ?? null;
    }
    setItem(key: string, value: string): void {
        this.calls.push(`set:${key}`);
        this.data.set(key, value);
    }
}

describe('isChunkLoadError — positives', () => {
    for (const [browser, message] of Object.entries(BROWSER_MESSAGES)) {
        it(`recognises the ${browser} message on a TypeError`, () => {
            expect(isChunkLoadError(new TypeError(message))).toBe(true);
        });
        it(`recognises the ${browser} message on a plain Error`, () => {
            expect(isChunkLoadError(new Error(message))).toBe(true);
        });
        it(`recognises the ${browser} message on a non-Error object with a string message`, () => {
            expect(isChunkLoadError({message})).toBe(true);
        });
    }

    it('is case-insensitive', () => {
        expect(isChunkLoadError(new Error(BROWSER_MESSAGES.chrome.toUpperCase()))).toBe(true);
        expect(isChunkLoadError(new Error(BROWSER_MESSAGES.firefox.toLowerCase()))).toBe(true);
        expect(isChunkLoadError(new Error(BROWSER_MESSAGES.safari.toUpperCase()))).toBe(true);
        expect(isChunkLoadError(new Error(BROWSER_MESSAGES.vite_css.toLowerCase()))).toBe(true);
    });

    it('recognises the phrase when something is wrapped around it', () => {
        expect(isChunkLoadError(new Error(`route /assets: ${BROWSER_MESSAGES.chrome} (retry later)`))).toBe(true);
    });
});

describe('isChunkLoadError — negatives', () => {
    it('is false for an API 500 error', () => {
        expect(isChunkLoadError(new Error('Request failed with status code 500'))).toBe(false);
        expect(isChunkLoadError(new Error('Internal Error'))).toBe(false);
    });

    it('is false for an ordinary TypeError', () => {
        expect(isChunkLoadError(new TypeError("Cannot read properties of undefined (reading 'x')"))).toBe(false);
        expect(isChunkLoadError(new TypeError('x is undefined'))).toBe(false);
    });

    it('is false for a network failure that is not a module import', () => {
        expect(isChunkLoadError(new TypeError('Failed to fetch'))).toBe(false);
        expect(isChunkLoadError(new TypeError('NetworkError when attempting to fetch resource.'))).toBe(false);
    });

    it('is false for a ZodiosError-shaped error', () => {
        class ZodiosError extends Error {
            constructor(message: string) {
                super(message);
                this.name = 'ZodiosError';
            }
        }
        expect(isChunkLoadError(new ZodiosError('Zodios: Invalid response from endpoint "get /assets"'))).toBe(false);
    });

    it('is false for a string, even one holding a browser message', () => {
        expect(isChunkLoadError(BROWSER_MESSAGES.chrome)).toBe(false);
        expect(isChunkLoadError('boom')).toBe(false);
    });

    it('is false for null, undefined and other primitives', () => {
        expect(isChunkLoadError(null)).toBe(false);
        expect(isChunkLoadError(undefined)).toBe(false);
        expect(isChunkLoadError(0)).toBe(false);
        expect(isChunkLoadError(true)).toBe(false);
    });

    it('is false for an object without a string message', () => {
        expect(isChunkLoadError({})).toBe(false);
        expect(isChunkLoadError({message: 42})).toBe(false);
        expect(isChunkLoadError({message: null})).toBe(false);
        expect(isChunkLoadError({msg: BROWSER_MESSAGES.chrome})).toBe(false);
    });

    it('reads only the error’s own message: a chunk failure in `cause` does not count', () => {
        const wrapped = new Error('navigation failed', {cause: new TypeError(BROWSER_MESSAGES.chrome)});
        expect(isChunkLoadError(wrapped)).toBe(false);
    });

    it('is false for an empty message', () => {
        expect(isChunkLoadError(new Error(''))).toBe(false);
    });
});

describe('reloadOnceForChunkError — the loop guard', () => {
    function lane(overrides: {now?: () => number; windowMs?: number} = {}) {
        const storage = new FakeStorage();
        const reload = vi.fn();
        const clock = {t: T0};
        const options = {storage, reload, now: overrides.now ?? (() => clock.t), ...(overrides.windowMs === undefined ? {} : {windowMs: overrides.windowMs})};
        return {storage, reload, clock, options};
    }

    it('the first time: reloads, returns true, and stores the timestamp under the agreed key', () => {
        const {storage, reload, options} = lane();
        expect(reloadOnceForChunkError(options)).toBe(true);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(storage.data.get(STORAGE_KEY)).toBe(String(T0));
    });

    it('reads the stored time from the agreed key', () => {
        const {storage, options} = lane();
        reloadOnceForChunkError(options);
        expect(storage.calls).toContain(`get:${STORAGE_KEY}`);
        expect(storage.calls).toContain(`set:${STORAGE_KEY}`);
    });

    it('writes the timestamp BEFORE it calls reload', () => {
        const {storage, options} = lane();
        const seenAtReload: Array<string | null> = [];
        const reload = vi.fn(() => seenAtReload.push(storage.data.get(STORAGE_KEY) ?? null));
        expect(reloadOnceForChunkError({...options, reload})).toBe(true);
        expect(seenAtReload).toEqual([String(T0)]);
    });

    it('a second request inside the window does not reload and leaves the stored time alone', () => {
        const {storage, reload, clock, options} = lane();
        expect(reloadOnceForChunkError(options)).toBe(true);
        clock.t = T0 + DEFAULT_WINDOW_MS - 1;
        expect(reloadOnceForChunkError(options)).toBe(false);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(storage.data.get(STORAGE_KEY)).toBe(String(T0));
    });

    it('a request in the same instant is refused too', () => {
        const {reload, options} = lane();
        expect(reloadOnceForChunkError(options)).toBe(true);
        expect(reloadOnceForChunkError(options)).toBe(false);
        expect(reload).toHaveBeenCalledTimes(1);
    });

    it('after the window (a later update in the same tab) it reloads again and stores the new time', () => {
        const {storage, reload, clock, options} = lane();
        expect(reloadOnceForChunkError(options)).toBe(true);
        clock.t = T0 + DEFAULT_WINDOW_MS + 1;
        expect(reloadOnceForChunkError(options)).toBe(true);
        expect(reload).toHaveBeenCalledTimes(2);
        expect(storage.data.get(STORAGE_KEY)).toBe(String(T0 + DEFAULT_WINDOW_MS + 1));
    });

    it('the window is 60 seconds by default and can be set', () => {
        const short = lane({windowMs: 1_000});
        expect(reloadOnceForChunkError(short.options)).toBe(true);
        short.clock.t = T0 + 999;
        expect(reloadOnceForChunkError(short.options)).toBe(false);
        short.clock.t = T0 + 1_001;
        expect(reloadOnceForChunkError(short.options)).toBe(true);

        const dflt = lane();
        expect(reloadOnceForChunkError(dflt.options)).toBe(true);
        dflt.clock.t = T0 + 30_000;
        expect(reloadOnceForChunkError(dflt.options)).toBe(false);
        dflt.clock.t = T0 + 120_000;
        expect(reloadOnceForChunkError(dflt.options)).toBe(true);
    });

    it('a time stored by an earlier run, inside the window, refuses the first call of this one', () => {
        const {storage, reload, options} = lane();
        storage.data.set(STORAGE_KEY, String(T0 - 5_000));
        expect(reloadOnceForChunkError(options)).toBe(false);
        expect(reload).not.toHaveBeenCalled();
    });

    it('a time stored by an earlier run, outside the window, allows the reload', () => {
        const {storage, reload, options} = lane();
        storage.data.set(STORAGE_KEY, String(T0 - DEFAULT_WINDOW_MS - 5_000));
        expect(reloadOnceForChunkError(options)).toBe(true);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(storage.data.get(STORAGE_KEY)).toBe(String(T0));
    });

    for (const garbage of ['abc', '', 'NaN', 'null', 'undefined', '{"at":1}']) {
        it(`a garbage stored value (${JSON.stringify(garbage)}) counts as «no stored time»: reload allowed`, () => {
            const {storage, reload, options} = lane();
            storage.data.set(STORAGE_KEY, garbage);
            expect(reloadOnceForChunkError(options)).toBe(true);
            expect(reload).toHaveBeenCalledTimes(1);
            expect(storage.data.get(STORAGE_KEY)).toBe(String(T0));
        });
    }

    it('a storage whose getItem throws: no reload, false, and it does not throw', () => {
        const reload = vi.fn();
        const storage = {
            getItem: () => {
                throw new DOMException('denied', 'SecurityError');
            },
            setItem: vi.fn(),
        };
        let result: boolean | undefined;
        expect(() => {
            result = reloadOnceForChunkError({storage, reload, now: () => T0});
        }).not.toThrow();
        expect(result).toBe(false);
        expect(reload).not.toHaveBeenCalled();
    });

    it('a storage whose setItem throws (quota, private mode): no reload, false, and it does not throw', () => {
        const reload = vi.fn();
        const storage = {
            getItem: () => null,
            setItem: () => {
                throw new DOMException('quota', 'QuotaExceededError');
            },
        };
        let result: boolean | undefined;
        expect(() => {
            result = reloadOnceForChunkError({storage, reload, now: () => T0});
        }).not.toThrow();
        expect(result).toBe(false);
        expect(reload).not.toHaveBeenCalled();
    });

    it('a missing storage (undefined, null, no window at all): no reload, false, and it does not throw', () => {
        const reload = vi.fn();
        expect(reloadOnceForChunkError({storage: undefined, reload, now: () => T0})).toBe(false);
        expect(reloadOnceForChunkError({storage: null as never, reload, now: () => T0})).toBe(false);
        expect(reloadOnceForChunkError({reload, now: () => T0})).toBe(false);
        expect(reloadOnceForChunkError({reload})).toBe(false);
        expect(reload).not.toHaveBeenCalled();
    });
});
