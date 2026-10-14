/**
 * Update Available Store (Svelte 5 Runes) — F14.
 *
 * Holds the release to prompt the admin about, if any. Triggered from
 * routes/(app)/+layout.svelte after a successful auth check (admins only).
 * "Skip this version" is persisted via updateCheck.dismissVersion; the plain
 * close just hides the modal until the next login/probe.
 *
 * Usage:
 *   import {updateAvailable} from '$lib/features/update-check/updateCheckStore.svelte';
 *   updateAvailable.show(release);          // after checkForNewerRelease() found one
 *   updateAvailable.show(release, {requested: true}); // the user asked (manual check)
 *   updateAvailable.close();                // "later" — prompts again next login
 *   updateAvailable.skipVersion();          // never prompt for this version again
 *
 * `requested` separates the two ways a release reaches the prompt. An automatic
 * find is an interruption, and DeferredAppPopups holds it until no modal and no
 * guide is on screen. A manual check is the answer to a question the user just
 * asked from inside the changelog modal: holding it until that modal closes made
 * the answer appear only afterwards, which read as a modal opening underneath.
 */

import type {NewerRelease} from './updateCheck';
import {dismissVersion} from './updateCheck';
import {debug} from '$lib/debug';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

let release = $state<NewerRelease | null>(null);
let requested = $state(false);

function show(r: NewerRelease, options: {requested?: boolean} = {}) {
    debug.log('UpdateCheck', 'prompting for release', r);
    release = r;
    requested = options.requested === true;
}

function close() {
    release = null;
    requested = false;
}

function skipVersion() {
    if (release) dismissVersion(release.version);
    release = null;
    requested = false;
}

export const updateAvailable = {
    get release() {
        return release;
    },
    /** Whether the current prompt answers a manual check rather than an automatic find. */
    get requested() {
        return requested;
    },
    show,
    close,
    skipVersion,
};

registerClientSessionReset('updateAvailable', close);
