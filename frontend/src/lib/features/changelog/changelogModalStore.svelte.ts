/**
 * The changelog window, one for the whole app (A-CL1).
 *
 * The Sidebar mounts the only `ChangelogModal` and binds it to this state. Every entry point opens that same window:
 * the version under the sidebar and the version in Settings → About. The Sidebar closes it when it unmounts, so the
 * window lives as long as the app shell.
 *
 * Usage:
 *   import {changelogModal} from '$lib/features/changelog/changelogModalStore.svelte';
 *   changelogModal.show();  // an entry point
 *   changelogModal.open;    // read by the Sidebar's ChangelogModal
 *   changelogModal.close(); // the window's onClose, and the Sidebar's teardown
 */

let open = $state(false);

function show(): void {
    open = true;
}

function close(): void {
    open = false;
}

export const changelogModal = {
    /** Whether the changelog window is open. */
    get open(): boolean {
        return open;
    },
    show,
    close,
};
