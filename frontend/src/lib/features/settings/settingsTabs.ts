/**
 * The tabs of the Settings page, as a registry.
 *
 * `routes/(app)/settings/[...path]/+page.svelte` draws its tab bars and the active tab's body from this list,
 * so adding a tab is one entry here, plus the import of its body:
 *   - `id` is the suffix of its `settings-tab-{id}` test id, and the `?tab=` value that opened it in 1.2 (still read, and
 *     turned into the tab's address);
 *   - `path` is its address, from `settingsPaths.ts` (lot B10): opening it opens the tab, choosing the tab writes it;
 *   - `order` places it in the bar, left to right; the numbers leave gaps, so a new tab slots in
 *     without renumbering the others;
 *   - `visible(ctx)` hides it from whoever may not see it (absent: everyone sees it). An
 *     administrators-only tab is `visible: (ctx) => ctx.isSuperuser`;
 *   - `props(ctx)` are spread on the body, and follow the context while it is on screen;
 *   - `group` puts it in a group of `SETTINGS_TAB_GROUPS` (decision P13 b): the bar shows the group
 *     as one tab, where its first member would be, and a second bar shows the members while one of
 *     them is open — when the group has at least two visible members. A member's `path` sits under
 *     its group's;
 *   - `badge(ctx)` is the number its tab shows (0: none); a group shows the sum of its members';
 *   - `prefetch(ctx)` runs when the page opens, and again when the context changes, for every visible
 *     tab that has one: what the badge needs is read before the tab is opened;
 *   - `alignEnd` starts the right-hand group on a wide screen: that tab and every tab after it sit
 *     on the right. One tab, or one group, carries it.
 */
import type {Component, ComponentType} from 'svelte';
import {DatabaseBackup, Info, Mail, Puzzle, Settings2, Shield, ShieldCheck, Sliders, User, Users} from 'lucide-svelte';
import ProfileTab from '$lib/features/settings/tabs/ProfileTab.svelte';
import PreferencesTab from '$lib/features/settings/tabs/PreferencesTab.svelte';
import AboutTab from '$lib/features/settings/tabs/AboutTab.svelte';
import GlobalSettingsTab from '$lib/features/settings/tabs/GlobalSettingsTab.svelte';
import UsersTab from '$lib/features/settings/tabs/UsersTab.svelte';
import SecurityTab from '$lib/features/settings/security/SecurityTab.svelte';
import {securityChecks} from '$lib/features/settings/security/securityChecks.svelte';
import {SETTINGS_GROUP_PATHS, SETTINGS_ROOT, SETTINGS_TAB_PATHS} from '$lib/features/settings/settingsPaths';
import BackupTab from '$lib/features/backup/BackupTab.svelte';
import EmailSettingsTab from '$lib/features/email/EmailSettingsTab.svelte';
import PluginSettingsTab from '$lib/features/plugin-settings/PluginSettingsTab.svelte';

/** What a tab may depend on: who is signed in. */
export interface SettingsTabContext {
    isSuperuser: boolean;
}

export type SettingsTabGroupId = 'administration';

export interface SettingsTabGroup {
    id: SettingsTabGroupId;
    labelKey: string;
    icon: ComponentType;
    /** Its address: it opens the group's first visible member. */
    path: string;
    alignEnd?: boolean;
}

export interface SettingsTab {
    id: string;
    labelKey: string;
    icon: ComponentType;
    /** Its address (`settingsPaths.ts`). */
    path: string;
    order: number;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- each body has props of its own
    component: Component<any>;
    visible?: (ctx: SettingsTabContext) => boolean;
    props?: (ctx: SettingsTabContext) => Record<string, unknown>;
    group?: SettingsTabGroupId;
    badge?: (ctx: SettingsTabContext) => number;
    prefetch?: (ctx: SettingsTabContext) => void;
    alignEnd?: boolean;
}

/** An entry of the top bar: a tab, or a group standing for its visible members. */
export type SettingsBarEntry = {kind: 'tab'; tab: SettingsTab} | {kind: 'group'; group: SettingsTabGroup; members: SettingsTab[]};

export const SETTINGS_TAB_GROUPS: readonly SettingsTabGroup[] = [
    // The instance's settings and its administration, on the right (decision P13 b, the designer's point 33)
    {id: 'administration', labelKey: 'settings.administration', icon: Shield, path: SETTINGS_GROUP_PATHS.administration, alignEnd: true},
];

export const SETTINGS_TABS: readonly SettingsTab[] = [
    {id: 'profile', labelKey: 'settings.profile', icon: User, path: SETTINGS_TAB_PATHS.profile, order: 10, component: ProfileTab},
    {id: 'preferences', labelKey: 'settings.preferences', icon: Sliders, path: SETTINGS_TAB_PATHS.preferences, order: 20, component: PreferencesTab},
    // Everyone: their own plugin settings, and the instance's read-only unless an administrator (workstream X, CP11, D-X15).
    {id: 'plugins', labelKey: 'pluginSettings.tab.label', icon: Puzzle, path: SETTINGS_TAB_PATHS.plugins, order: 25, component: PluginSettingsTab},
    {id: 'about', labelKey: 'settings.about', icon: Info, path: SETTINGS_TAB_PATHS.about, order: 30, component: AboutTab},
    // Administrators only (N69-2): a user has no Administration group at all. The props keep the read-only branch of the
    // tab, no longer reached from the UI, until a cleanup.
    {id: 'admin', labelKey: 'settings.globalSettings', icon: Settings2, path: SETTINGS_TAB_PATHS.admin, order: 100, component: GlobalSettingsTab, props: (ctx) => ({canEdit: ctx.isSuperuser}), visible: (ctx) => ctx.isSuperuser, group: 'administration'},
    // Administrators only: the accounts and the open invitations (decision D-A10).
    {id: 'users', labelKey: 'settings.users', icon: Users, path: SETTINGS_TAB_PATHS.users, order: 110, component: UsersTab, visible: (ctx) => ctx.isSuperuser, group: 'administration'},
    // Administrators only: the archive holds every user's data.
    {id: 'backup', labelKey: 'backup.tab', icon: DatabaseBackup, path: SETTINGS_TAB_PATHS.backup, order: 120, component: BackupTab, visible: (ctx) => ctx.isSuperuser, group: 'administration'},
    // Administrators only: the state of the instance's email and a test email (workstream E).
    {id: 'email', labelKey: 'email.tab.label', icon: Mail, path: SETTINGS_TAB_PATHS.email, order: 130, component: EmailSettingsTab, visible: (ctx) => ctx.isSuperuser, group: 'administration'},
    // Administrators only: the configuration checks of the instance, the badge counting what asks for attention (lot A8b).
    {
        id: 'security',
        labelKey: 'settings.security',
        icon: ShieldCheck,
        path: SETTINGS_TAB_PATHS.security,
        order: 140,
        component: SecurityTab,
        visible: (ctx) => ctx.isSuperuser,
        group: 'administration',
        badge: () => securityChecks.attentionCount,
        prefetch: (ctx) => {
            if (ctx.isSuperuser) void securityChecks.ensureLoaded();
        },
    },
];

/** The tabs this context may see, by ascending `order`, as a new array: `tabs` is left as it was. */
export function visibleSettingsTabs(tabs: readonly SettingsTab[], ctx: SettingsTabContext): SettingsTab[] {
    return tabs.filter((tab) => tab.visible?.(ctx) ?? true).sort((a, b) => a.order - b.order);
}

/**
 * The entries of the top bar for this context: the visible tabs by `order`, each group's visible members replaced by
 * the group, once, where its first member would be. A group with no visible member is left out. Nothing is mutated.
 */
export function settingsBar(tabs: readonly SettingsTab[], groups: readonly SettingsTabGroup[], ctx: SettingsTabContext): SettingsBarEntry[] {
    const entries: SettingsBarEntry[] = [];
    const placed = new Map<SettingsTabGroupId, SettingsTab[]>();
    for (const tab of visibleSettingsTabs(tabs, ctx)) {
        const group = tab.group ? groups.find((candidate) => candidate.id === tab.group) : undefined;
        if (!group) {
            entries.push({kind: 'tab', tab});
            continue;
        }
        const members = placed.get(group.id);
        if (members) {
            members.push(tab);
            continue;
        }
        const first = [tab];
        placed.set(group.id, first);
        entries.push({kind: 'group', group, members: first});
    }
    return entries;
}

/** What an address of the Settings page names: the page itself, a tab, a group, or nothing the registry knows. */
export type SettingsPlace = {kind: 'root'} | {kind: 'tab'; id: string} | {kind: 'group'; id: SettingsTabGroupId} | {kind: 'unknown'};

/**
 * The place a pathname names (lot B10), whoever may see it: `/settings` the page, a tab's `path` that tab, a group's `path`
 * that group, any other address under `/settings` nothing. A trailing slash is ignored. Pure: the lists are given.
 */
export function settingsPlaceOf(pathname: string, tabs: readonly SettingsTab[], groups: readonly SettingsTabGroup[]): SettingsPlace {
    const path = pathname.length > 1 ? pathname.replace(/\/+$/, '') : pathname;
    if (path === SETTINGS_ROOT) return {kind: 'root'};
    const tab = tabs.find((candidate) => candidate.path === path);
    if (tab) return {kind: 'tab', id: tab.id};
    const group = groups.find((candidate) => candidate.path === path);
    return group ? {kind: 'group', id: group.id} : {kind: 'unknown'};
}
