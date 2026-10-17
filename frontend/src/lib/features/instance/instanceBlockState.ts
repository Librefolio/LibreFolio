/**
 * Whether the hosting provider blocked this instance: the plain state behind `instanceBlock.svelte.ts` (Z-20).
 *
 * - `lib/api/zodios-client.ts` calls `markBlocked()` from its response interceptor on the first `423 instance_blocked`.
 *   This module uses no runes and imports nothing from the API, so the client imports it without a cycle, and the AI
 *   Export probe's Node bridge loads the client without Svelte's compiler.
 * - `instanceBlock.svelte.ts` is its reactive face for the `(app)` layout: it reads the value when it loads and follows
 *   every change through `subscribe()`, synchronously.
 * - A change of account clears it (`registerClientSessionReset`, registered here only).
 *
 * The backend answers 423 only to a signed-in user (`backend/app/api/v1/instance_block.py`); anyone else gets the 401
 * of any protected route, and the login.
 */
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

/** The status and the `detail.code` of the API's refusal on a blocked instance. */
export const INSTANCE_BLOCKED_STATUS = 423;
export const INSTANCE_BLOCKED_CODE = 'instance_blocked';

/** Whether an API error is the refusal of a blocked instance: status 423 and `detail.code` `instance_blocked`. */
export function isInstanceBlockedError(status: number | undefined, data: unknown): boolean {
    if (status !== INSTANCE_BLOCKED_STATUS || typeof data !== 'object' || data === null) return false;
    const detail = (data as {detail?: unknown}).detail;
    return typeof detail === 'object' && detail !== null && (detail as {code?: unknown}).code === INSTANCE_BLOCKED_CODE;
}

let blocked = false;
const listeners = new Set<() => void>();

function setBlocked(value: boolean): void {
    if (blocked === value) return;
    blocked = value;
    for (const listener of [...listeners]) listener();
}

export const instanceBlockState = {
    get blocked(): boolean {
        return blocked;
    },
    markBlocked(): void {
        setBlocked(true);
    },
    clear(): void {
        setBlocked(false);
    },
    /** Calls `listener` after every change, synchronously. Returns the function that stops it. */
    subscribe(listener: () => void): () => void {
        listeners.add(listener);
        return () => {
            listeners.delete(listener);
        };
    },
};

registerClientSessionReset('instanceBlock', () => instanceBlockState.clear());
