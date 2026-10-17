/**
 * Whether the hosting provider blocked this instance, as the `(app)` layout reads it: the reactive face (Svelte 5
 * runes) of `instanceBlockState.ts` (Z-20).
 *
 * - The state lives in `instanceBlockState.ts`, without runes, which `lib/api/zodios-client.ts` marks from its response
 *   interceptor on the first `423 instance_blocked`: the API client imports no Svelte-compiled module.
 * - This module reads the value when it loads, so a block marked before the layout loaded shows at once, and follows
 *   every change through `subscribe()`, synchronously: its `$state` is written there only. `markBlocked()` and
 *   `clear()` are the plain module's.
 * - The `(app)` layout shows `InstanceBlockedPage` instead of the app while `blocked` is on: the app shell never starts,
 *   so its requests never pile up refusals.
 * - A change of account clears it: `instanceBlockState.ts` registers the reset.
 *
 * The backend answers 423 only to a signed-in user (`backend/app/api/v1/instance_block.py`); anyone else gets the 401
 * of any protected route, and the login.
 */
import {instanceBlockState} from '$lib/features/instance/instanceBlockState';

export {INSTANCE_BLOCKED_CODE, INSTANCE_BLOCKED_STATUS, isInstanceBlockedError} from '$lib/features/instance/instanceBlockState';

let blocked = $state(instanceBlockState.blocked);

const stopFollowing = instanceBlockState.subscribe(() => {
    blocked = instanceBlockState.blocked;
});

// Development only (Z-22): a hot update of this file evaluates a new copy, while `instanceBlockState` keeps the old
// copy's listener. Vite calls `dispose()` only on the module an update is accepted through (here the `(app)` layout,
// never this file), so each copy stops the one before it through `import.meta.hot.data`. A build drops the block, and
// Vitest's stand-in for `import.meta.hot` has no `data`.
if (import.meta.hot?.data) {
    import.meta.hot.data.stopFollowing?.();
    import.meta.hot.data.stopFollowing = stopFollowing;
}

export const instanceBlock = {
    get blocked(): boolean {
        return blocked;
    },
    markBlocked: instanceBlockState.markBlocked,
    clear: instanceBlockState.clear,
};
