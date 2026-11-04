// @vitest-environment jsdom
//
// The docblock above is load-bearing: `hooks.client.ts` installs a listener on `window` when it loads, and the
// loop guard reads `window.sessionStorage`. jsdom gives both; `location` is replaced by a stub that counts calls
// to `reload`, so nothing ever navigates.
/**
 * hooks.client.test.ts — SvelteKit's client hooks, wired to the chunk-reload cure (H5-2, backlog X-R84).
 *
 * `hooks.client.ts` does two things:
 *
 *   1. at module load it calls `installChunkReload()`, so a failed Vite preload (`vite:preloadError`) reloads the
 *      page once instead of surfacing «500 Internal Error»;
 *   2. it exports `handleError: HandleClientError` for the failures that reach SvelteKit itself (a route's lazy
 *      `import()` rejecting during navigation). For a chunk-load error whose reload the guard allowed, it returns
 *      `{message}` quietly — the page is already on its way out, a console error would be noise. Otherwise it does
 *      what SvelteKit does when an app has no `handleError`: `console.error(error)`; and in every case it returns
 *      `{message}`, the one SvelteKit passes in.
 *
 * The module is imported fresh (`vi.resetModules()`) per case, so its load-time side effect is observable; the
 * listeners it leaves on the shared jsdom window are removed afterwards.
 *
 * Red today: `./hooks.client` does not exist, so the import fails and every case below is red.
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';

const STORAGE_KEY = 'lf-chunk-reload-at';
const EVENT = 'vite:preloadError';

const CHUNK_MESSAGE = 'Failed to fetch dynamically imported module: https://folio.example/_app/immutable/nodes/7.4f2a9c1e.js';

let reloadStub: ReturnType<typeof vi.fn>;
let registered: Array<[string, EventListenerOrEventListenerObject]>;
let consoleError: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
    reloadStub = vi.fn();
    vi.stubGlobal('location', {reload: reloadStub});
    window.sessionStorage.clear();
    registered = [];
    const original = window.addEventListener.bind(window);
    vi.spyOn(window, 'addEventListener').mockImplementation(((type: string, listener: EventListenerOrEventListenerObject, opts?: unknown) => {
        registered.push([type, listener]);
        original(type, listener, opts as never);
    }) as never);
    consoleError = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.resetModules();
});

afterEach(() => {
    for (const [type, listener] of registered) window.removeEventListener(type, listener);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
});

async function loadHooks() {
    return await import('./hooks.client');
}

/** The input SvelteKit hands to a client `handleError`. */
function input(error: unknown, message = 'Internal Error') {
    return {error, event: {} as never, status: 500, message};
}

describe('hooks.client — module load', () => {
    it('registers a vite:preloadError listener on window', async () => {
        await loadHooks();
        const ours = registered.filter(([type]) => type === EVENT);
        expect(ours).toHaveLength(1);
        expect(typeof ours[0][1]).toBe('function');
    });

    it('does not reload anything just by loading', async () => {
        await loadHooks();
        expect(reloadStub).not.toHaveBeenCalled();
        expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    });

    it('exports handleError', async () => {
        const hooks = await loadHooks();
        expect(typeof hooks.handleError).toBe('function');
    });

    it('a vite:preloadError reloads the page once and is cancelled; the next one is left alone', async () => {
        await loadHooks();

        const first = new Event(EVENT, {cancelable: true});
        window.dispatchEvent(first);
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(first.defaultPrevented).toBe(true);

        const second = new Event(EVENT, {cancelable: true});
        window.dispatchEvent(second);
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(second.defaultPrevented).toBe(false);
    });
});

describe('hooks.client — handleError', () => {
    it('a chunk-load error, reload allowed: reloads, returns {message}, logs nothing', async () => {
        const {handleError} = await loadHooks();
        const result = await handleError(input(new TypeError(CHUNK_MESSAGE), 'Internal Error'));
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(consoleError).not.toHaveBeenCalled();
        expect(result).toEqual({message: 'Internal Error'});
    });

    it('a chunk-load error, guard refuses (reloaded a moment ago): logs the error and returns {message}', async () => {
        window.sessionStorage.setItem(STORAGE_KEY, String(Date.now()));
        const {handleError} = await loadHooks();
        const error = new TypeError(CHUNK_MESSAGE);
        const result = await handleError(input(error, 'Internal Error'));
        expect(reloadStub).not.toHaveBeenCalled();
        expect(consoleError).toHaveBeenCalledTimes(1);
        expect(consoleError).toHaveBeenCalledWith(error);
        expect(result).toEqual({message: 'Internal Error'});
    });

    it('two chunk-load errors in a row: the first reloads quietly, the second is logged', async () => {
        const {handleError} = await loadHooks();
        const error = new TypeError(CHUNK_MESSAGE);
        await handleError(input(error));
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(consoleError).not.toHaveBeenCalled();

        await handleError(input(error));
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(consoleError).toHaveBeenCalledTimes(1);
    });

    it('a chunk-load error with an unusable sessionStorage: logs and returns {message}, never throws, never reloads', async () => {
        const descriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
        const {handleError} = await loadHooks();
        Object.defineProperty(window, 'sessionStorage', {
            configurable: true,
            get() {
                throw new DOMException('The operation is insecure.', 'SecurityError');
            },
        });
        try {
            const error = new TypeError(CHUNK_MESSAGE);
            const result = await handleError(input(error, 'Internal Error'));
            expect(reloadStub).not.toHaveBeenCalled();
            expect(consoleError).toHaveBeenCalledWith(error);
            expect(result).toEqual({message: 'Internal Error'});
        } finally {
            if (descriptor) Object.defineProperty(window, 'sessionStorage', descriptor);
            else delete (window as unknown as Record<string, unknown>).sessionStorage;
        }
    });

    it('an ordinary error: logs it, returns {message}, and neither reloads nor touches the guard', async () => {
        const {handleError} = await loadHooks();
        const error = new Error('Request failed with status code 500');
        const result = await handleError(input(error, 'Internal Error'));
        expect(consoleError).toHaveBeenCalledTimes(1);
        expect(consoleError).toHaveBeenCalledWith(error);
        expect(reloadStub).not.toHaveBeenCalled();
        expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
        expect(result).toEqual({message: 'Internal Error'});
    });

    it('a thrown non-Error value (a string, null) is logged as it came', async () => {
        const {handleError} = await loadHooks();
        await handleError(input('boom'));
        await handleError(input(null));
        expect(consoleError).toHaveBeenNthCalledWith(1, 'boom');
        expect(consoleError).toHaveBeenNthCalledWith(2, null);
        expect(reloadStub).not.toHaveBeenCalled();
    });

    it('the returned message is the one SvelteKit passed in, not a text of its own', async () => {
        const {handleError} = await loadHooks();
        const a = await handleError(input(new Error('x'), 'message A'));
        const b = await handleError(input(new TypeError(CHUNK_MESSAGE), 'message B'));
        expect(a).toEqual({message: 'message A'});
        expect(b).toEqual({message: 'message B'});
    });
});

describe('hooks.client — the server hooks stay as they are', () => {
    it('hooks.server.ts does not mention the chunk reload', async () => {
        const {readFileSync} = await import('node:fs');
        const {join} = await import('node:path');
        const server = readFileSync(join(process.cwd(), 'src/hooks.server.ts'), 'utf8');
        expect(server).not.toMatch(/chunkReload/);
        expect(server).not.toMatch(/preloadError/);
    });
});
