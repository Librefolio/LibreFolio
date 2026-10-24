/**
 * Reload the page once when a code chunk fails to load (X-R84, lot H5-2).
 *
 * After an update, or a hiccup of the network, the browser can fail to fetch a chunk of the app («Failed to fetch
 * dynamically imported module»). SvelteKit then shows «500 Internal Error» and the user stays there until they reload by
 * hand. Reloading fetches the page and its chunks afresh, so the app does it once by itself, with a guard against loops:
 * the time of the last automatic reload is kept in `sessionStorage`, and no second reload comes within `windowMs`. A chunk
 * that still fails after the reload shows the error page, as before. Without a usable storage no reload is ever made
 * (nothing could tell a second failure from a first), and the page keeps working.
 *
 * Rune-free and import-free: `hooks.client.ts` loads it before anything else.
 */

/** The messages browsers and Vite give a failed dynamic import: Chrome, Firefox, Safari, and Vite's CSS preload. */
const CHUNK_LOAD_MESSAGES = /failed to fetch dynamically imported module|error loading dynamically imported module|importing a module script failed|unable to preload css/i;

/** The `sessionStorage` key of the last automatic reload, in epoch milliseconds. */
export const CHUNK_RELOAD_KEY = 'lf-chunk-reload-at';

/** How long after an automatic reload another one is refused. */
export const CHUNK_RELOAD_WINDOW_MS = 60_000;

export interface ChunkReloadOptions {
    /** Where the time of the last reload is kept; `window.sessionStorage` by default, read when needed (reading it can throw). */
    storage?: Pick<Storage, 'getItem' | 'setItem'> | null;
    /** The clock, in epoch milliseconds. */
    now?: () => number;
    /** What reloads the page. */
    reload?: () => void;
    /** The least time between two automatic reloads. */
    windowMs?: number;
}

/** Whether an error is a failed dynamic import: an error (or any object) whose own message is one of the browsers'. */
export function isChunkLoadError(error: unknown): boolean {
    if (typeof error !== 'object' || error === null) return false;
    const message = (error as {message?: unknown}).message;
    return typeof message === 'string' && CHUNK_LOAD_MESSAGES.test(message);
}

/** The storage in use: the given one, or the session's. `undefined` when there is none or it cannot be read. */
function usableStorage(options: ChunkReloadOptions): Pick<Storage, 'getItem' | 'setItem'> | undefined {
    if ('storage' in options) return options.storage ?? undefined;
    try {
        return typeof window === 'undefined' ? undefined : window.sessionStorage;
    } catch {
        return undefined;
    }
}

/**
 * Reload the page unless it was reloaded this way less than `windowMs` ago. Returns whether it reloaded. The time is
 * written before the reload, so a reload that fails at once is not repeated either. Never throws.
 */
export function reloadOnceForChunkError(options: ChunkReloadOptions = {}): boolean {
    const storage = usableStorage(options);
    if (!storage) return false;
    const now = (options.now ?? Date.now)();
    const windowMs = options.windowMs ?? CHUNK_RELOAD_WINDOW_MS;
    try {
        const stored = storage.getItem(CHUNK_RELOAD_KEY);
        const last = stored === null ? Number.NaN : Number(stored);
        // Garbage, or nothing stored, is no previous time: a value that is not a time never refuses a reload
        if (Number.isFinite(last) && last > 0 && now - last < windowMs) return false;
        storage.setItem(CHUNK_RELOAD_KEY, String(now));
    } catch {
        return false;
    }
    (options.reload ?? (() => window.location.reload()))();
    return true;
}

/**
 * Listen for Vite's `vite:preloadError` (a dynamic import or its preloaded files failed) and reload once for it. When it
 * reloaded, the event's default is prevented, so Vite does not throw the failure into the page that is going away.
 */
export function installChunkReload(target: Pick<Window, 'addEventListener'> = window, options: ChunkReloadOptions = {}): void {
    target.addEventListener('vite:preloadError', (event: Event) => {
        if (reloadOnceForChunkError(options)) event.preventDefault();
    });
}
