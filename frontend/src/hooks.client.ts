/**
 * Client Hooks
 *
 * Reload the page once when a code chunk fails to load (X-R84): after an update, or a hiccup of the network, a dynamic
 * import fails and SvelteKit would show «500 Internal Error» until the user reloads by hand.
 * - `vite:preloadError`, which Vite emits for a failed import or preload, reloads once (`installChunkReload`).
 * - `handleError` catches the same failure when SvelteKit meets it first, while loading a page.
 */
import type {HandleClientError} from '@sveltejs/kit';
import {installChunkReload, isChunkLoadError, reloadOnceForChunkError} from '$lib/utils/core/chunkReload';

installChunkReload();

export const handleError: HandleClientError = ({error, message}) => {
    // A chunk that failed to load: the page reloads, and the failure is not an error worth a line in the console
    if (isChunkLoadError(error) && reloadOnceForChunkError()) return {message};
    // What SvelteKit does when there is no handleError: the console has the error, the page the default message
    console.error(error);
    return {message};
};
