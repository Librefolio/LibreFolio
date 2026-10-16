/**
 * The open-registration warning (accounts A7b, decision §10.4): an administrator of an instance anyone may register on,
 * who reached it through a host outside the local network, is told so in an instance notice.
 *
 * - `openRegistrationNoticeFor()` decides, and nothing else: the notice, or null. With the mode pinned by
 *   `LIBREFOLIO_REGISTRATION` the notice names the variable and links nowhere: no setting in the app can change it.
 * - `startOpenRegistrationNotice()` watches the signed-in user, the public configuration of the instance and the host
 *   of the page, and shows or hides the notice in the instance notices. The app bootstrap starts it at every load
 *   (`appBootstrap.load()`); only the first start watches. While the warning holds it only ever calls `show()`: a
 *   `hide()` would forget that the user closed it.
 */
import {untrack} from 'svelte';
import {fromStore} from 'svelte/store';
import {currentUser} from '$lib/stores/app/auth';
import {instanceConfig, type InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import {instanceNotices, type InstanceNotice} from '$lib/features/instance/instanceNotices.svelte';
import {isLocalHost} from './localHost';

export const OPEN_REGISTRATION_NOTICE_ID = 'accounts.openRegistration';

export interface OpenRegistrationNoticeState {
    isAdmin: boolean;
    registrationMode: string;
    registrationLocked: boolean;
    /** The host the browser reached the instance through, as `location.hostname` writes it. */
    hostname: string;
}

export function openRegistrationNoticeFor({isAdmin, registrationMode, registrationLocked, hostname}: OpenRegistrationNoticeState): InstanceNotice | null {
    if (!isAdmin || registrationMode !== 'open' || isLocalHost(hostname)) return null;
    if (registrationLocked) {
        return {id: OPEN_REGISTRATION_NOTICE_ID, severity: 'warning', dismissible: true, messageKey: 'auth.notices.openRegistrationLocked'};
    }
    return {
        id: OPEN_REGISTRATION_NOTICE_ID,
        severity: 'warning',
        dismissible: true,
        messageKey: 'auth.notices.openRegistration',
        action: {labelKey: 'auth.notices.openRegistrationAction', href: '/settings?tab=admin'},
    };
}

export interface OpenRegistrationNoticeDependencies {
    /** The signed-in user, null when nobody is. */
    user?: () => {is_superuser?: boolean | null} | null;
    /** The public configuration of the instance, null while it is unknown. */
    config?: () => InstanceConfig | null;
    hostname?: () => string;
    notices?: Pick<typeof instanceNotices, 'show' | 'hide'>;
}

let stopWatching: (() => void) | null = null;

/** The auth store's user, read so that an effect follows it. */
function signedInUser(): () => {is_superuser?: boolean | null} | null {
    const tracked = fromStore(currentUser);
    return () => tracked.current;
}

/** Starts watching, and returns the function that stops it. A second start changes nothing: its dependencies are ignored. */
export function startOpenRegistrationNotice(dependencies: OpenRegistrationNoticeDependencies = {}): () => void {
    if (stopWatching) return () => {};
    const user = dependencies.user ?? signedInUser();
    // Before `/system/instance` answers, the configuration in force is the default one, which is open: an invite-only
    // instance would warn for nothing until the answer lands
    const config = dependencies.config ?? (() => (instanceConfig.loaded ? instanceConfig.config : null));
    const hostname = dependencies.hostname ?? (() => (typeof window === 'undefined' ? '' : window.location.hostname));
    const notices = dependencies.notices ?? instanceNotices;

    const cleanup = $effect.root(() => {
        $effect(() => {
            const accounts = config()?.accounts;
            const notice = openRegistrationNoticeFor({
                isAdmin: user()?.is_superuser === true,
                registrationMode: accounts?.registration_mode ?? '',
                registrationLocked: accounts?.registration_locked === true,
                hostname: hostname(),
            });
            // Untracked: `show()` and `hide()` read the registry's own state, so a tracked call would re-run on its own write
            untrack(() => (notice ? notices.show(notice) : notices.hide(OPEN_REGISTRATION_NOTICE_ID)));
        });
    });
    const stop = (): void => {
        if (stopWatching !== stop) return;
        stopWatching = null;
        cleanup();
    };
    stopWatching = stop;
    return stop;
}
