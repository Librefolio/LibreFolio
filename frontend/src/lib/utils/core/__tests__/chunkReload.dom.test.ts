// @vitest-environment jsdom
//
// The docblock above is load-bearing: the defaults of `reloadOnceForChunkError` (sessionStorage, Date.now,
// window.location.reload) and `installChunkReload` (a `window` to listen on) need a window. jsdom provides one;
// the real navigation never happens — `location` is replaced by a stub that only counts calls to `reload`.
/**
 * chunkReload.dom.test.ts — the defaults and the event wiring of `chunkReload.ts` (H5-2, backlog X-R84).
 *
 * `chunkReload.test.ts` proves the guard with everything injected. Here, the half it cannot reach:
 *
 *   - **The defaults.** With no options, `reloadOnceForChunkError` reads sessionStorage LAZILY, inside the call
 *     (merely reading `window.sessionStorage` can throw — a blocked-storage browser), uses the real clock, and calls
 *     `window.location.reload()`. The clock is not mocked: stored times are seeded relative to the real `Date.now()`
 *     and the written one is bracketed by two reads of it.
 *   - **The wiring.** `installChunkReload(target?, options?)` registers ONE listener for `vite:preloadError`
 *     (Vite's event for a failed preload, fired before it rethrows) on the target (default `window`). When the
 *     guard let a reload happen, the listener calls `event.preventDefault()` so Vite does not rethrow; when the
 *     guard refused, it leaves the event alone (the error then surfaces and the error page shows).
 *
 * Red today: `../chunkReload` does not exist, so the import fails and every case below is red.
 * Registered in `front_utility_unit` (`scripts/test_runner/_frontend_utility.py`, action `core-unit`).
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {installChunkReload, reloadOnceForChunkError} from '../chunkReload';

const STORAGE_KEY = 'lf-chunk-reload-at';
const EVENT = 'vite:preloadError';
const T0 = 1_700_000_000_000;

let reloadStub: ReturnType<typeof vi.fn>;
let registered: Array<[string, EventListenerOrEventListenerObject]>;

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
});

afterEach(() => {
    // Remove every listener this file's installs put on the shared jsdom window: a later case must not see them.
    for (const [type, listener] of registered) window.removeEventListener(type, listener);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
});

function preloadError(): Event {
    return new Event(EVENT, {cancelable: true});
}

describe('reloadOnceForChunkError — defaults', () => {
    it('with no options: reloads through window.location.reload and writes a real timestamp under the key', () => {
        const before = Date.now();
        expect(reloadOnceForChunkError()).toBe(true);
        const after = Date.now();
        expect(reloadStub).toHaveBeenCalledTimes(1);
        const stored = Number(window.sessionStorage.getItem(STORAGE_KEY));
        expect(Number.isFinite(stored)).toBe(true);
        expect(stored).toBeGreaterThanOrEqual(before);
        expect(stored).toBeLessThanOrEqual(after);
    });

    it('with no options: the second call (a chunk that still fails after the reload) does not reload', () => {
        expect(reloadOnceForChunkError()).toBe(true);
        expect(reloadOnceForChunkError()).toBe(false);
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('with no options: a time stored a few seconds ago refuses; one stored over a minute ago allows', () => {
        window.sessionStorage.setItem(STORAGE_KEY, String(Date.now() - 5_000));
        expect(reloadOnceForChunkError()).toBe(false);
        expect(reloadStub).not.toHaveBeenCalled();

        window.sessionStorage.setItem(STORAGE_KEY, String(Date.now() - 61_000));
        expect(reloadOnceForChunkError()).toBe(true);
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('with no options: a garbage value in sessionStorage allows the reload', () => {
        window.sessionStorage.setItem(STORAGE_KEY, 'not-a-time');
        expect(reloadOnceForChunkError()).toBe(true);
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('only some options given: the rest stay at their defaults', () => {
        const reload = vi.fn();
        expect(reloadOnceForChunkError({reload})).toBe(true);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(reloadStub).not.toHaveBeenCalled();
        expect(window.sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();

        window.sessionStorage.clear();
        expect(reloadOnceForChunkError({now: () => T0})).toBe(true);
        expect(window.sessionStorage.getItem(STORAGE_KEY)).toBe(String(T0));
        expect(reloadStub).toHaveBeenCalledTimes(1);
    });

    it('reading window.sessionStorage throws (blocked storage): no reload, false, and it does not throw', () => {
        const descriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
        Object.defineProperty(window, 'sessionStorage', {
            configurable: true,
            get() {
                throw new DOMException('The operation is insecure.', 'SecurityError');
            },
        });
        try {
            let result: boolean | undefined;
            expect(() => {
                result = reloadOnceForChunkError();
            }).not.toThrow();
            expect(result).toBe(false);
            expect(reloadStub).not.toHaveBeenCalled();
        } finally {
            if (descriptor) Object.defineProperty(window, 'sessionStorage', descriptor);
            else delete (window as unknown as Record<string, unknown>).sessionStorage;
        }
    });

    it('does not read sessionStorage until it is called (the read is lazy)', () => {
        const descriptor = Object.getOwnPropertyDescriptor(window, 'sessionStorage');
        const read = vi.fn(() => window.localStorage);
        Object.defineProperty(window, 'sessionStorage', {configurable: true, get: read});
        try {
            installChunkReload();
            expect(read).not.toHaveBeenCalled();
        } finally {
            if (descriptor) Object.defineProperty(window, 'sessionStorage', descriptor);
            else delete (window as unknown as Record<string, unknown>).sessionStorage;
        }
    });
});

describe('installChunkReload — against a fake target', () => {
    function install(options: Parameters<typeof installChunkReload>[1]) {
        const addEventListener = vi.fn();
        installChunkReload({addEventListener}, options);
        return addEventListener;
    }

    it('registers exactly one listener, for vite:preloadError', () => {
        const addEventListener = install({storage: {getItem: () => null, setItem: () => {}}, reload: vi.fn(), now: () => T0});
        expect(addEventListener).toHaveBeenCalledTimes(1);
        expect(addEventListener.mock.calls[0][0]).toBe(EVENT);
        expect(typeof addEventListener.mock.calls[0][1]).toBe('function');
    });

    it('does not reload at install time', () => {
        const reload = vi.fn();
        install({storage: {getItem: () => null, setItem: () => {}}, reload, now: () => T0});
        expect(reload).not.toHaveBeenCalled();
    });

    it('when the guard lets a reload happen: reloads and calls preventDefault', () => {
        const reload = vi.fn();
        const stored = new Map<string, string>();
        const storage = {getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => void stored.set(k, v)};
        const addEventListener = install({storage, reload, now: () => T0});
        const listener = addEventListener.mock.calls[0][1] as (event: {preventDefault: () => void}) => void;

        const event = {preventDefault: vi.fn()};
        listener(event);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(event.preventDefault).toHaveBeenCalledTimes(1);
    });

    it('when the guard refuses (second event inside the window): no reload, preventDefault not called', () => {
        const reload = vi.fn();
        const stored = new Map<string, string>();
        const storage = {getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => void stored.set(k, v)};
        const addEventListener = install({storage, reload, now: () => T0});
        const listener = addEventListener.mock.calls[0][1] as (event: {preventDefault: () => void}) => void;

        listener({preventDefault: vi.fn()});
        const second = {preventDefault: vi.fn()};
        listener(second);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(second.preventDefault).not.toHaveBeenCalled();
    });

    it('when the storage is unusable: no reload and the event is left alone', () => {
        const reload = vi.fn();
        const storage = {
            getItem: () => {
                throw new Error('denied');
            },
            setItem: vi.fn(),
        };
        const addEventListener = install({storage, reload, now: () => T0});
        const listener = addEventListener.mock.calls[0][1] as (event: {preventDefault: () => void}) => void;

        const event = {preventDefault: vi.fn()};
        expect(() => listener(event)).not.toThrow();
        expect(reload).not.toHaveBeenCalled();
        expect(event.preventDefault).not.toHaveBeenCalled();
    });

    it('with an old stored time: a later update in the same tab reloads and prevents again', () => {
        const reload = vi.fn();
        const stored = new Map<string, string>();
        const clock = {t: T0};
        const storage = {getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => void stored.set(k, v)};
        const addEventListener = install({storage, reload, now: () => clock.t});
        const listener = addEventListener.mock.calls[0][1] as (event: {preventDefault: () => void}) => void;

        listener({preventDefault: vi.fn()});
        clock.t = T0 + 61_000;
        const later = {preventDefault: vi.fn()};
        listener(later);
        expect(reload).toHaveBeenCalledTimes(2);
        expect(later.preventDefault).toHaveBeenCalledTimes(1);
    });
});

describe('installChunkReload — on the real window', () => {
    it('the default target is window', () => {
        installChunkReload();
        const ours = registered.filter(([type]) => type === EVENT);
        expect(ours).toHaveLength(1);
    });

    it('a dispatched vite:preloadError reloads once and is cancelled; a second one is not', () => {
        installChunkReload();

        const first = preloadError();
        window.dispatchEvent(first);
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(first.defaultPrevented).toBe(true);

        const second = preloadError();
        window.dispatchEvent(second);
        expect(reloadStub).toHaveBeenCalledTimes(1);
        expect(second.defaultPrevented).toBe(false);
    });

    it('options reach the listener: injected storage, clock and reload replace the defaults', () => {
        const reload = vi.fn();
        const stored = new Map<string, string>();
        const storage = {getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => void stored.set(k, v)};
        installChunkReload(window, {storage, reload, now: () => T0});

        const event = preloadError();
        window.dispatchEvent(event);
        expect(reload).toHaveBeenCalledTimes(1);
        expect(reloadStub).not.toHaveBeenCalled();
        expect(stored.get(STORAGE_KEY)).toBe(String(T0));
        expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
        expect(event.defaultPrevented).toBe(true);
    });

    it('other events are ignored: nothing but vite:preloadError reaches the guard', () => {
        installChunkReload();
        window.dispatchEvent(new Event('error', {cancelable: true}));
        window.dispatchEvent(new Event('unhandledrejection', {cancelable: true}));
        expect(reloadStub).not.toHaveBeenCalled();
        expect(window.sessionStorage.getItem(STORAGE_KEY)).toBeNull();
    });
});
