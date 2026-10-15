/**
 * The address bar of a link page: the bare path replaces the address that carried the token.
 *
 * SvelteKit's `replaceState` keeps its router in step; before the router has started it refuses, and the browser's
 * own history does the same job.
 */

import {replaceState} from '$app/navigation';

export function replaceAddress(path: string): void {
    try {
        replaceState(path, {});
    } catch {
        history.replaceState(history.state, '', path);
    }
}
