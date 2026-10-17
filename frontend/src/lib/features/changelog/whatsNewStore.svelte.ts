/**
 * The «What's new» popup (C-54), reactive: shown on every page load until the user closes it.
 *
 * Pending while the signed-in user's `whats_new` (login and `/auth/me`) names released chapters of the bundled changelog
 * (`whatsNewChapters`). Closing it hides it at once for this page load and tells the server
 * (`POST /api/v1/auth/whats-new/seen`, which records the running release): a request that fails is only logged, and the
 * popup comes back on the next page load. `DeferredAppPopups` shows it, first among the automatic popups.
 *
 * Usage:
 *   import {whatsNew} from '$lib/features/changelog/whatsNewStore.svelte';
 *   whatsNew.shouldShow; // read in a template or a $derived
 *   whatsNew.dismiss();  // every close of the modal
 */
import {fromStore} from 'svelte/store';
import {zodiosApi} from '$lib/api';
import {debug} from '$lib/debug';
import {auth} from '$lib/stores/app/auth';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';
import {changelogChapters, type ChangelogChapter} from './changelog';
import {whatsNewChapters, type WhatsNew} from './whatsNew';

const authState = fromStore(auth);
let dismissed = $state(false);

/** The signed-in user's `whats_new`, narrowed: the generated client widens a nullable field. */
function pending(): WhatsNew | null {
    const value: unknown = authState.current.user?.whats_new;
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return null;
    const {since, release} = value as {since?: unknown; release?: unknown};
    return typeof release === 'string' ? {since: typeof since === 'string' ? since : null, release} : null;
}

function chapters(): ChangelogChapter[] {
    return whatsNewChapters(changelogChapters, pending());
}

function dismiss(): void {
    if (dismissed) return;
    dismissed = true;
    zodiosApi.mark_whats_new_seen_api_v1_auth_whats_new_seen_post(undefined).catch((error: unknown) => {
        debug.warn('WhatsNew', 'POST /auth/whats-new/seen failed: the popup comes back on the next page load', error);
    });
}

export const whatsNew = {
    /** What the server said is new for the signed-in user, or null. */
    get pending(): WhatsNew | null {
        return pending();
    },
    /** The English chapters to show (the modal shows each in the interface language when the bundle translates it). */
    get chapters(): ChangelogChapter[] {
        return chapters();
    },
    get shouldShow(): boolean {
        return !dismissed && authState.current.user !== null && chapters().length > 0;
    },
    dismiss,
};

registerClientSessionReset('whatsNew', () => {
    dismissed = false;
});
