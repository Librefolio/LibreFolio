/**
 * Whether the instance is over its plan of users, as the `(app)` layout reads it: the reactive face (Svelte 5 runes) of
 * `userLimitState.ts` (A5-7). The same shape as `instanceBlock.svelte.ts`: a `$state` read from the plain state when this
 * module loads and kept in step by a synchronous subscription.
 *
 * The `(app)` layout shows `UserLimitPage` instead of the app while `exceeded` is on: the app shell never starts, so its
 * requests never pile up refusals.
 */
import {userLimitState} from '$lib/features/instance/userLimitState';

export {USER_LIMIT_CODE, USER_LIMIT_STATUS, isUserLimitError} from '$lib/features/instance/userLimitState';

let exceeded = $state(userLimitState.exceeded);

const stopFollowing = userLimitState.subscribe(() => {
    exceeded = userLimitState.exceeded;
});

// Development only: a hot update of this file evaluates a new copy while the plain state keeps the old copy's listener
// (see `instanceBlock.svelte.ts`): each copy stops the one before it.
if (import.meta.hot?.data) {
    import.meta.hot.data.stopFollowing?.();
    import.meta.hot.data.stopFollowing = stopFollowing;
}

export const userLimit = {
    get exceeded(): boolean {
        return exceeded;
    },
    markExceeded: userLimitState.markExceeded,
    clear: userLimitState.clear,
};
