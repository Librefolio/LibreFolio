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
 *   updateAvailable.close();                // "later" — prompts again next login
 *   updateAvailable.skipVersion();          // never prompt for this version again
 */

import type {NewerRelease} from './updateCheck';
import {dismissVersion} from './updateCheck';
import {debug} from '$lib/debug';
import {registerClientSessionReset} from '$lib/stores/app/clientSession';

let release = $state<NewerRelease | null>(null);

function show(r: NewerRelease) {
    debug.log('UpdateCheck', 'prompting for release', r);
    release = r;
}

function close() {
    release = null;
}

function skipVersion() {
    if (release) dismissVersion(release.version);
    release = null;
}

export const updateAvailable = {
    get release() {
        return release;
    },
    show,
    close,
    skipVersion,
};

registerClientSessionReset('updateAvailable', close);
