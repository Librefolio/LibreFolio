/**
 * Whether the hosting provider blocked this instance: the first `423 instance_blocked` from the API turns it on.
 *
 * - `lib/api/zodios-client.ts` calls `markBlocked()` from its response interceptor. This module imports nothing from
 *   the API, so the interceptor can import it without a cycle.
 * - The `(app)` layout shows `InstanceBlockedPage` instead of the app while `blocked` is on: the app shell never starts,
 *   so its requests never pile up refusals.
 * - A change of account clears it (`registerClientSessionReset`).
 *
 * The backend answers 423 only to a signed-in user (`backend/app/api/v1/instance_block.py`); anyone else gets the 401
 * of any protected route, and the login.
 */
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

/** The status and the `detail.code` of the API's refusal on a blocked instance. */
export const INSTANCE_BLOCKED_STATUS = 423;
export const INSTANCE_BLOCKED_CODE = 'instance_blocked';

let blocked = $state(false);

/** Whether an API error is the refusal of a blocked instance: status 423 and `detail.code` `instance_blocked`. */
export function isInstanceBlockedError(status: number | undefined, data: unknown): boolean {
    if (status !== INSTANCE_BLOCKED_STATUS || typeof data !== 'object' || data === null) return false;
    const detail = (data as {detail?: unknown}).detail;
    return typeof detail === 'object' && detail !== null && (detail as {code?: unknown}).code === INSTANCE_BLOCKED_CODE;
}

export const instanceBlock = {
    get blocked(): boolean {
        return blocked;
    },
    markBlocked(): void {
        blocked = true;
    },
    clear(): void {
        blocked = false;
    },
};

registerClientSessionReset('instanceBlock', () => instanceBlock.clear());
