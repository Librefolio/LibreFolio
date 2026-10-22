/**
 * The address check of the share dialogs (decision D-A3): does *this* instance answer at the address an administrator
 * typed? The dialog asks its own instance for a signed nonce (`POST /users/address-probe`), then loads
 * `<address>/api/v1/auth/address-probe.png?nonce=…` as an image: 1×1 on the instance that issued the nonce, 2×1
 * anywhere else (lot H-55 v2).
 *
 * An image, not a `fetch`: the Content-Security-Policy LibreFolio enforces on its pages limits `connect-src` to its own
 * origins, while images stay free, and a browser reads the natural size of an image from any origin without CORS. A
 * browser can still refuse it (mixed content, a local-network permission, an address that does not answer, a blocked
 * instance's 401): that reads as «cannot verify», never as «no».
 */

export type ProbeVerdict = 'match' | 'mismatch' | 'unverifiable';

export const PROBE_IMAGE_PATH = '/api/v1/auth/address-probe.png';
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

/** The URL of the public half of the check at `base`: an image, 1×1 on the instance that issued `nonce`, 2×1 elsewhere. */
export function probeImageUrl(base: string, nonce: string): string {
    return `${base}${PROBE_IMAGE_PATH}?nonce=${encodeURIComponent(nonce)}`;
}

/** The natural size of a loaded image. */
export interface ImageSize {
    naturalWidth: number;
    naturalHeight: number;
}

/** Loads `url` as an image, until `signal` aborts it. */
export type ImageLoader = (url: string, signal: AbortSignal) => Promise<ImageSize>;

/**
 * The default loader: an `Image` with no referrer and no `crossOrigin` (the size of an image is readable from any
 * origin without CORS), its handlers set before its `src`. It resolves on `load` with the natural size, rejects on
 * `error`, and on abort clears `src`, so the browser stops loading it.
 */
export const loadImage: ImageLoader = (url, signal) =>
    new Promise<ImageSize>((resolve, reject) => {
        const image = new Image();
        image.referrerPolicy = 'no-referrer';
        image.onload = () => resolve({naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight});
        image.onerror = () => reject(new Error('the probe image did not load'));
        const abort = () => {
            image.src = '';
            reject(new Error('the probe image was aborted'));
        };
        if (signal.aborted) {
            abort();
            return;
        }
        signal.addEventListener('abort', abort, {once: true});
        image.src = url;
    });

interface CheckOptions {
    /** A nonce of this instance (`POST /users/address-probe`). */
    issueNonce: () => Promise<string>;
    /** The image loader to use; `loadImage` when absent. */
    loadImage?: ImageLoader;
    timeoutMs?: number;
}

/** Whether this instance answers at `base`. Never throws: whatever cannot be read is `'unverifiable'`. */
export async function checkAddress(base: string, {issueNonce, loadImage: load = loadImage, timeoutMs = PROBE_TIMEOUT_MS}: CheckOptions): Promise<ProbeVerdict> {
    let nonce: string;
    try {
        nonce = await issueNonce();
    } catch {
        return 'unverifiable';
    }
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
            const size = await load(probeImageUrl(base, nonce), controller.signal);
            const width = size?.naturalWidth;
            const height = size?.naturalHeight;
            if (height === 1 && width === 1) {
                return 'match';
            }
            return height === 1 && width === 2 ? 'mismatch' : 'unverifiable';
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
