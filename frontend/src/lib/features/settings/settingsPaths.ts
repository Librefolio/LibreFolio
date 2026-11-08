/**
 * The address of every Settings tab (release 1.3, lot B10).
 *
 * Everyone's tabs live at `/settings/<tab>`, the members of the «Administration» group at `/settings/admin/<tab>`; the
 * bare `/settings` opens the first tab. This table is the one place an address is written: the registry
 * (`settingsTabs.ts`) gives each tab its `path` from here, and every link that opens a tab reads it here too. It imports
 * nothing, so a utility can link a tab without pulling the tab bodies in.
 *
 * The keys are the tab ids of the registry (also the `settings-tab-{id}` test ids and the `?tab=` values of 1.2). The
 * Global Settings tab is `admin`, so its address names what it holds: `/settings/admin/global`.
 */

/** The page itself: it opens the first tab. */
export const SETTINGS_ROOT = '/settings';

/** The address of each group: it opens the group's first visible member. */
export const SETTINGS_GROUP_PATHS = {
    administration: '/settings/admin',
} as const;

/** The address of each tab, by tab id. */
export const SETTINGS_TAB_PATHS = {
    profile: '/settings/profile',
    preferences: '/settings/preferences',
    plugins: '/settings/plugins',
    about: '/settings/about',
    admin: '/settings/admin/global',
    users: '/settings/admin/users',
    backup: '/settings/admin/backup',
    email: '/settings/admin/email',
    security: '/settings/admin/security',
} as const;

export type SettingsTabPathId = keyof typeof SETTINGS_TAB_PATHS;

/** The query that brings one field of the Global Settings tab into view: `?setting=<key>`. */
export const SETTINGS_FIELD_PARAM = 'setting';

/** The address of a tab, with an optional query (`{setting: 'storage_limit_mb'}` → `…?setting=storage_limit_mb`). */
export function settingsTabHref(id: SettingsTabPathId, query?: Record<string, string>): string {
    const search = query ? new URLSearchParams(query).toString() : '';
    return search ? `${SETTINGS_TAB_PATHS[id]}?${search}` : SETTINGS_TAB_PATHS[id];
}
