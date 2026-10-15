/**
 * The address check of the share dialogs (decision D-A3): does *this* instance answer at the address an administrator
 * typed? The dialog asks its own instance for a signed nonce (`POST /users/address-probe`), then sends it to
 * `GET <address>/api/v1/auth/address-probe`, which answers `{match: true}` only on the instance that issued it.
 *
 * The check must be a CORS simple request — a `GET` with no header and no credentials — because the backend's
 * `CORSMiddleware` refuses any preflight. A browser can still refuse it (mixed content, a local-network permission, an
 * address that does not answer): that reads as «cannot verify», never as «no».
 */

export type ProbeVerdict = 'match' | 'mismatch' | 'unverifiable';

export const PROBE_PATH = '/api/v1/auth/address-probe';
export const PROBE_TIMEOUT_MS = 8000;

/** `input` as a base to share links at: an absolute http(s) URL without credentials, query or fragment, and without trailing slashes; `null` otherwise. */
export function normalizeBase(input: string): string | null {
    const text = input.trim();
    if (!text || text.includes('?') || text.includes('#')) {
        return null;
    }
    let parsed: URL;
    try {
        parsed = new URL(text);
    } catch {
        return null;
    }
    if ((parsed.protocol !== 'http:' && parsed.protocol !== 'https:') || parsed.username || parsed.password || !parsed.host) {
        return null;
    }
    return `${parsed.protocol}//${parsed.host}${parsed.pathname.replace(/\/+$/, '')}`;
}

/** The URL of the public half of the check at `base`. */
export function probeUrl(base: string, nonce: string): string {
    return `${base}${PROBE_PATH}?nonce=${encodeURIComponent(nonce)}`;
}

interface CheckOptions {
    /** A nonce of this instance (`POST /users/address-probe`). */
    issueNonce: () => Promise<string>;
    /** The fetch to use; the global one, read at call time, when absent. */
    fetchImpl?: typeof fetch;
    timeoutMs?: number;
}

/** Whether this instance answers at `base`. Never throws: whatever cannot be read is `'unverifiable'`. */
export async function checkAddress(base: string, {issueNonce, fetchImpl, timeoutMs = PROBE_TIMEOUT_MS}: CheckOptions): Promise<ProbeVerdict> {
    let nonce: string;
    try {
        nonce = await issueNonce();
    } catch {
        return 'unverifiable';
    }
    const send = fetchImpl ?? ((input: RequestInfo | URL, init?: RequestInit) => globalThis.fetch(input, init));
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timedOut = new Promise<ProbeVerdict>((resolve) => {
        timer = setTimeout(() => {
            controller.abort();
            resolve('unverifiable');
        }, timeoutMs);
    });
    const attempt = async (): Promise<ProbeVerdict> => {
        try {
            // A simple request: no `headers`, no `body`, no `mode`, no credentials (see the module comment)
            const response = await send(probeUrl(base, nonce), {method: 'GET', credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', signal: controller.signal});
            if (!response.ok) {
                return 'unverifiable';
            }
            const body: unknown = await response.json();
            const match = body !== null && typeof body === 'object' ? (body as {match?: unknown}).match : undefined;
            return match === true ? 'match' : match === false ? 'mismatch' : 'unverifiable';
        } catch {
            return 'unverifiable';
        }
    };
    try {
        return await Promise.race([attempt(), timedOut]);
    } finally {
        clearTimeout(timer);
    }
}
