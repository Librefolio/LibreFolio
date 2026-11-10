/**
 * Whether the instance is over its plan of users: the plain state behind `userLimit.svelte.ts` (A5-7).
 *
 * - `lib/api/zodios-client.ts` calls `markExceeded()` from its response interceptor on the first
 *   `423 user_limit_exceeded`. This module uses no runes and imports nothing from the API, so the client imports it
 *   without a cycle.
 * - `userLimit.svelte.ts` is its reactive face for the `(app)` layout.
 * - A change of account clears it (`registerClientSessionReset`, registered here only).
 *
 * The backend answers 423 only to a signed-in user (`backend/app/api/v1/user_limit.py`); anyone else gets the 401 of any
 * protected route, and the login.
 */
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

/** The status and the `detail.code` of the API's refusal while the accounts outnumber the plan. */
export const USER_LIMIT_STATUS = 423;
export const USER_LIMIT_CODE = 'user_limit_exceeded';

/** Whether an API error is the refusal of an instance over its plan of users: status 423 and `detail.code` `user_limit_exceeded`. */
export function isUserLimitError(status: number | undefined, data: unknown): boolean {
    if (status !== USER_LIMIT_STATUS || typeof data !== 'object' || data === null) return false;
    const detail = (data as {detail?: unknown}).detail;
    return typeof detail === 'object' && detail !== null && (detail as {code?: unknown}).code === USER_LIMIT_CODE;
}

let exceeded = false;
const listeners = new Set<() => void>();

function setExceeded(value: boolean): void {
    if (exceeded === value) return;
    exceeded = value;
    for (const listener of [...listeners]) listener();
}

export const userLimitState = {
    get exceeded(): boolean {
        return exceeded;
    },
    markExceeded(): void {
        setExceeded(true);
    },
    clear(): void {
        setExceeded(false);
    },
    /** Calls `listener` after every change, synchronously. Returns the function that stops it. */
    subscribe(listener: () => void): () => void {
        listeners.add(listener);
        return () => {
            listeners.delete(listener);
        };
    },
};

registerClientSessionReset('userLimit', () => userLimitState.clear());
