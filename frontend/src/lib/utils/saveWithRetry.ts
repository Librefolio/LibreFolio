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
            // Use the centralized extractor so callers get loc-aware summaries.
            const issues = extractValidationIssues(err);
            if (issues.length > 0) return formatValidationIssues(issues);
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
 * Pydantic / FastAPI 422 validation issue, normalized for UI display.
 *
 * `loc` is the dot-joined path of the field that failed (e.g.
 * `"body.creates.0.asset_id"`). `msg` is the error message stripped of the
 * leading `"Value error, "` prefix.
 */
export interface ValidationIssueExtracted {
    loc: string;
    msg: string;
    type?: string;
    /** Structured error code from PydanticCustomError (e.g. 'assetRequired'). */
    code?: string;
    /** Structured params from PydanticCustomError ctx (e.g. {type: 'BUY'}). */
    params?: Record<string, any>;
}

/**
 * Extract Pydantic 422 validation issues from an Axios-like error.
 *
 * **Safety net only** — with the Unified Batch Pipeline, /validate and /commit
 * accept `List[dict]` so Pydantic 422 should never fire for per-row schema
 * errors. This function remains as a defensive fallback for edge cases
 * (e.g. network serialization failures, future schema-level `extra="forbid"` on
 * the outer TXMixedBatch wrapper).
 *
 * Returns an empty array if the error is not a 422 with a `detail[]` array.
 */
export function extractValidationIssues(err: unknown): ValidationIssueExtracted[] {
    const detail = (err as any)?.response?.data?.detail;
    if (!Array.isArray(detail)) return [];
    const out: ValidationIssueExtracted[] = [];
    for (const item of detail) {
        if (!item || typeof item !== 'object') continue;
        const loc = Array.isArray(item.loc) ? item.loc.join('.') : String(item.loc ?? '');

        // Handle packed multi-error from model_validator:
        // type="multipleBusinessRuleErrors" carries all business-rule errors
        // inside ctx.errors[]. Expand them as separate issues sharing the same loc.
        if (item.type === 'multipleBusinessRuleErrors' && Array.isArray(item.ctx?.errors)) {
            for (const sub of item.ctx.errors) {
                const subMsg = String(sub.msg ?? '').trim();
                out.push({
                    loc,
                    msg: subMsg,
                    type: sub.code,
                    code: sub.code,
                    params: sub.ctx && typeof sub.ctx === 'object' ? sub.ctx : undefined,
                });
            }
            continue;
        }

        let msg = String(item.msg ?? item.message ?? '').trim();
        // Pydantic v2 prefixes value-error msg with "Value error, " — strip it
        // for compactness ("Value error, BUY requires asset_id" → "BUY requires asset_id").
        if (msg.toLowerCase().startsWith('value error, ')) {
            msg = msg.slice('value error, '.length);
        }
        out.push({loc, msg, type: item.type, code: item.type, params: item.ctx && typeof item.ctx === 'object' ? item.ctx : undefined});
    }
    return out;
}

/**
 * Format a list of validation issues as a single readable string suitable
 * for an inline banner. Issues are joined with `" · "` and prefixed with
 * the leaf segment of `loc` when present (e.g.
 * `"asset_id: BUY requires asset_id · quantity: must be > 0"`).
 *
 * Pass `maxIssues` to truncate long lists (default 5; remainder is summed
 * up as `"… +N more"`).
 */
export function formatValidationIssues(issues: ValidationIssueExtracted[], maxIssues = 5): string {
    if (issues.length === 0) return '';
    const head = issues.slice(0, maxIssues).map((iss) => {
        // Try to extract the most informative leaf:
        //   body.creates.0.asset_id    → "asset_id"
        //   body.creates.0             → "row 1"  (Pydantic stops at the row index)
        //   body.updates.2.cash.amount → "cash.amount"
        const parts = iss.loc.split('.').filter(Boolean);
        // strip leading "body" and the operation segment ("creates"/"updates"/"deletes")
        let tail = parts;
        if (tail[0] === 'body') tail = tail.slice(1);
        if (tail[0] === 'creates' || tail[0] === 'updates' || tail[0] === 'deletes') tail = tail.slice(1);
        let leaf = '';
        if (tail.length === 0) leaf = '';
        else if (tail.length === 1 && /^\d+$/.test(tail[0])) leaf = `row ${Number(tail[0]) + 1}`;
        else leaf = tail.filter((p) => !/^\d+$/.test(p)).join('.');
        return leaf ? `${leaf}: ${iss.msg}` : iss.msg;
    });
    const remainder = issues.length - head.length;
    return remainder > 0 ? `${head.join(' · ')} · … +${remainder} more` : head.join(' · ');
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
