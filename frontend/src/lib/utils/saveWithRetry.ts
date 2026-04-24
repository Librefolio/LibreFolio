/**
 * saveWithRetry — unified error handler for save operations in modals.
 *
 * **Problem solved (I-bis #22):** prior to this helper each modal handled
 * save errors inconsistently. Some closed on error, some swallowed the
 * FastAPI ``detail`` payload, some printed only to console. The net effect
 * was that HTTP failures felt like "the app crashed silently" and users
 * lost their draft (the modal closed with dirty state).
 *
 * **Contract:**
 *   - Wraps an async save call and always returns a discriminated union
 *     ``SaveResult<T>`` — never throws.
 *   - On failure: extracts a human-readable message from FastAPI ``detail``
 *     (string or object), Axios ``response.data.detail``, generic ``message``
 *     or a translatable fallback (``fallbackKey`` via ``$t`` passed as arg).
 *   - Optionally fires a toast (``toast: true`` by default for errors).
 *   - **Never** closes the modal: the caller inspects the result and
 *     decides.
 *
 * **Usage pattern:**
 * ```ts
 * const result = await saveWithRetry(
 *     () => zodiosApi.patch_broker_api_v1_brokers__broker_id__patch(payload, ...),
 *     {fallback: $t('brokers.updateFailed')},
 * );
 * if (result.status === 'success') {
 *     dispatch('updated', result.data);
 *     dispatch('close');
 * } else {
 *     // modal stays open, draft preserved, toast already shown
 *     formError = result.message;
 * }
 * ```
 */

import {toasts} from '$lib/stores/toastStore.svelte';

/** Result of a ``saveWithRetry`` call — discriminated union. */
export type SaveResult<T> = {status: 'success'; data: T} | {status: 'error'; message: string; error: unknown; status_code?: number};

export interface SaveWithRetryOptions {
    /**
     * Fallback message shown when the error payload carries no human text.
     * Pass the already-translated string from the caller (``$t(...)``) so
     * this helper stays i18n-agnostic.
     */
    fallback?: string;

    /**
     * Whether to fire a ``toasts.error(...)`` on failure. Default ``true``.
     * Set ``false`` when the caller wants to render the error inline
     * (e.g. banner, form-level message) without a transient toast.
     */
    toast?: boolean;

    /**
     * Optional prefix for the toast/error message (e.g. asset name):
     * ``"Save failed for Apple Inc.: <detail>"``.
     */
    prefix?: string;

    /**
     * If provided, called with the raw error BEFORE the toast/message
     * extraction. Useful for custom handling (e.g. 409 → destructive modal).
     * Return ``true`` to short-circuit — the helper will skip the toast
     * and return ``{status: 'error', message: '<handled>'}`` so the caller
     * knows the error was consumed. Return ``false`` / ``undefined`` to
     * fall through to the default handling.
     */
    onError?: (err: unknown) => boolean | void;
}

/**
 * Extract the best-effort human-readable message from an unknown error.
 *
 * Priority:
 *   1. Axios response → ``err.response.data.detail`` (FastAPI).
 *      - string → used as-is.
 *      - object with ``.message`` → used.
 *      - array (Pydantic validation errors) → first ``msg`` field.
 *   2. ``err.response.statusText`` + status code.
 *   3. ``err.message`` (native Error).
 *   4. ``String(err)``.
 */
export function extractErrorMessage(err: unknown, fallback: string = 'Operation failed'): string {
    if (!err) return fallback;
    // Axios-style error
    const anyErr = err as any;
    const detail = anyErr?.response?.data?.detail;
    if (detail) {
        if (typeof detail === 'string') return detail;
        if (Array.isArray(detail)) {
            // Pydantic validation error array: [{msg, loc, type, ...}, ...]
            const first = detail[0];
            if (first && typeof first === 'object') {
                const msg = first.msg ?? first.message;
                if (msg) return typeof msg === 'string' ? msg : String(msg);
            }
        }
        if (typeof detail === 'object') {
            const msg = detail.message ?? detail.error ?? detail.detail;
            if (msg) return typeof msg === 'string' ? msg : String(msg);
        }
    }
    const status = anyErr?.response?.status;
    const statusText = anyErr?.response?.statusText;
    if (status && statusText) return `HTTP ${status} — ${statusText}`;
    if (anyErr?.message && typeof anyErr.message === 'string') return anyErr.message;
    try {
        return String(err);
    } catch {
        return fallback;
    }
}

/**
 * Extract the HTTP status code from an Axios-like error, if any.
 */
export function extractStatusCode(err: unknown): number | undefined {
    return (err as any)?.response?.status;
}

/**
 * Wrap an async save call with unified error handling.
 *
 * @param call    the async function to run (typically a ``zodiosApi.xxx(...)`` call)
 * @param options see ``SaveWithRetryOptions``
 */
export async function saveWithRetry<T>(call: () => Promise<T>, options: SaveWithRetryOptions = {}): Promise<SaveResult<T>> {
    const {fallback = 'Operation failed', toast: showToast = true, prefix, onError} = options;
    try {
        const data = await call();
        return {status: 'success', data};
    } catch (err: unknown) {
        // Custom pre-handler: if it returns true, consider the error consumed.
        const consumed = onError?.(err) === true;
        const rawMessage = extractErrorMessage(err, fallback);
        const message = prefix ? `${prefix}: ${rawMessage}` : rawMessage;
        const status_code = extractStatusCode(err);
        if (!consumed && showToast) {
            toasts.error(message);
        }
        // Always log to console — the ``debug`` helper in toastStore is
        // toast-only; save errors deserve a stack-trace in DevTools even
        // when the toast is suppressed.
        // eslint-disable-next-line no-console
        console.error('[saveWithRetry]', message, err);
        return {status: 'error', message, error: err, status_code};
    }
}

