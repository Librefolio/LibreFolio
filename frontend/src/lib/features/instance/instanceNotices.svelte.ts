/**
 * Instance notices (Svelte 5 runes): messages about this instance, shown above every page of the (app) layout.
 *
 * A feature that needs to tell the users something about the instance registers its own notice here, and
 * `InstanceNotices.svelte` shows it: nobody edits the layout to add one. The registering code decides who sees a notice
 * (it knows the user and their role) and removes it when the condition is gone.
 *
 * - `show()` adds a notice, or replaces the one with the same id in place.
 * - `hide()` removes it; a notice hidden and shown again is visible again, even if the user had closed it.
 * - `dismiss()` is the user closing a dismissible notice: it stays closed until the next page load, unless it is shown
 *   again as not dismissible.
 * - Signing out clears every notice (`registerClientSessionReset`).
 *
 * Usage:
 *   import {instanceNotices} from '$lib/features/instance/instanceNotices.svelte';
 *   instanceNotices.show({id: 'assets.disallowedProviders', severity: 'warning', messageKey: 'assets.notices.disallowed', params: {count: 3}});
 *   instanceNotices.hide('assets.disallowedProviders');
 */

import {registerClientSessionReset} from '$lib/stores/app/clientSession';

export type InstanceNoticeSeverity = 'info' | 'warning' | 'danger';

export interface InstanceNoticeAction {
    /** i18n key of the link's label. */
    labelKey: string;
    /** Path inside the app. */
    href: string;
}

export interface InstanceNotice {
    /** Stable and unique: start it with the owner's area, such as `assets.disallowedProviders`. */
    id: string;
    severity: InstanceNoticeSeverity;
    /** i18n key of the message, and its ICU parameters. */
    messageKey: string;
    params?: Record<string, string | number>;
    /** The user may close it, until the next page load. */
    dismissible?: boolean;
    /** An optional link after the message. */
    action?: InstanceNoticeAction;
}

/** Most severe first; within a severity, the order the notices were first shown. */
const SEVERITY_RANK: Record<InstanceNoticeSeverity, number> = {danger: 0, warning: 1, info: 2};

let notices = $state<InstanceNotice[]>([]);
let dismissed = $state<string[]>([]);

function show(notice: InstanceNotice): void {
    const index = notices.findIndex((existing) => existing.id === notice.id);
    if (index >= 0) notices[index] = notice;
    else notices.push(notice);
}

function hide(id: string): void {
    notices = notices.filter((notice) => notice.id !== id);
    dismissed = dismissed.filter((dismissedId) => dismissedId !== id);
}

function dismiss(id: string): void {
    const notice = notices.find((existing) => existing.id === id);
    if (!notice?.dismissible || dismissed.includes(id)) return;
    dismissed.push(id);
}

function clear(): void {
    notices = [];
    dismissed = [];
}

export const instanceNotices = {
    /** The notices to show, most severe first, then in the order they were first shown. A dismissal hides a notice
     * only while it is dismissible: one shown again as not dismissible (escalated) is visible again. */
    get list(): InstanceNotice[] {
        return notices.filter((notice) => !(notice.dismissible && dismissed.includes(notice.id))).sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
    },
    show,
    hide,
    dismiss,
    clear,
};

registerClientSessionReset('instanceNotices', clear);
