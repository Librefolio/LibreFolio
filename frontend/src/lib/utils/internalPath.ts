/**
 * Internal paths — where the app may send a user after a sign-in, a welcome or a lost session.
 *
 * A destination read from the URL (`?redirect=`, `?returnTo=`) is user input. Only an in-app path is
 * honoured: anything else falls back, so a crafted link can neither leave the app nor make `goto` throw on
 * an external URL. No imports on purpose: the API client uses `loginUrl` too, and the onboarding modules
 * import the client.
 */

const DUMMY_ORIGIN = 'http://librefolio.local';
const CONTROL_CHARACTER = /[\u0000-\u001f\u007f]/;

/**
 * `value` when it is an in-app path, `fallback` otherwise. In-app: one leading `/` (not `//`), no `\`, no
 * control character (the URL parser drops tabs and newlines, so `/\t/host` would turn into `//host`), and
 * still on this origin once resolved.
 */
export function safeInternalPath(value: string | null | undefined, fallback = '/dashboard'): string {
    if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\') || CONTROL_CHARACTER.test(value)) return fallback;
    try {
        return new URL(value, DUMMY_ORIGIN).origin === DUMMY_ORIGIN ? value : fallback;
    } catch {
        return fallback;
    }
}

/** The login page, carrying the page to come back to: `/?redirect=<path and query>`, or plain `/` when there is none. */
export function loginUrl(requested: string | null | undefined): string {
    const target = safeInternalPath(requested, '/');
    return target === '/' ? '/' : `/?redirect=${encodeURIComponent(target)}`;
}
