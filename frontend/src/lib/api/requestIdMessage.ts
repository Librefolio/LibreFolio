/**
 * The error code in a message the user sees (lot H-60r, decision D3): one helper for every surface.
 *
 * A user who meets a generic error quotes its code, and the administrator finds the request in the server log with it.
 * The code is the request id of the failed call (`X-Request-Id`, `requestIdOf`), and it is shown only for a server
 * error (5xx): that is the failure whose id the server log always holds (lot H-60, one line for every 5xx). A 4xx
 * writes no server line, so its id would lead nowhere; a network failure has no answer, so no id; a 5xx answered by a
 * proxy carries no LibreFolio id.
 *
 * The message stays whole, and the code follows it, in parentheses, at the end, on the same line:
 * `common.errorWithRequestId`, «{message} (code: {requestId})». Use it where the interface shows a generic failure, never
 * instead of a message that tells the user what to do. Pass the caught error as it is: an Axios or Zodios error, or a
 * wrapper that keeps it in `cause` (the standard `Error` cause) or `originalError` (the AI Export client errors).
 */
import {requestIdOf} from './apiErrorConsole';

/** svelte-i18n's `$_`/`get(_)`, `AiExportTranslate` and the `Translate` aliases of `lib/api/` are all assignable to it. */
export type RequestIdTranslate = (key: string, options?: {values?: Record<string, string>}) => string;

/** The message, then the code: «{message} (code: {requestId})», in the four languages of `base`. */
export const REQUEST_ID_MESSAGE_KEY = 'common.errorWithRequestId';

/** The most links followed, through `originalError` or `cause`, before the failed answer is found. */
const MAX_LINKS = 8;

type Loose = Record<string, unknown>;

function loose(value: unknown): Loose | null {
    return typeof value === 'object' && value !== null ? (value as Loose) : null;
}

/** `error`, or the first object reached from it through `originalError` or `cause`, that holds a failed HTTP answer. */
function holderOfAnswer(error: unknown): Loose | null {
    const seen = new Set<unknown>();
    let current = loose(error);
    for (let links = 0; current && links <= MAX_LINKS && !seen.has(current); links += 1) {
        if (loose(current.response)) return current;
        seen.add(current);
        current = loose(current.originalError) ?? loose(current.cause);
    }
    return null;
}

/** The request id of a server error (5xx) that `error` is or wraps; null for anything else. */
export function serverErrorRequestId(error: unknown): string | null {
    try {
        const holder = holderOfAnswer(error);
        const status = loose(holder?.response)?.status;
        if (typeof status !== 'number' || status < 500 || status > 599) return null;
        return requestIdOf(holder);
    } catch {
        return null;
    }
}

/** `message`, followed by the code of the server error `error` is or wraps; `message` unchanged when there is none. */
export function withRequestId(t: RequestIdTranslate, message: string, error: unknown): string {
    const requestId = serverErrorRequestId(error);
    return requestId ? t(REQUEST_ID_MESSAGE_KEY, {values: {message, requestId}}) : message;
}
