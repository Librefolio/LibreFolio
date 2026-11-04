/**
 * The Settings tab registry — `settingsTabs.ts` (workstream A: plan A3, and the «Administration» group of lot A8b).
 *
 * The Settings page wrote its four tabs by hand (`routes/(app)/settings/+page.svelte`): a `TabId` union, an `isTabId`
 * guard, a list of `{id, icon, labelKey}`, an `{#if}` chain choosing the body, `canEdit={isSuperuser}` on the admin body
 * and an inline `className: 'sm:ml-auto'` pushing the admin tab to the right. Plan A3.1 (`plan-phase01Accounts` §4.2)
 * moved the tabs into this registry, so that a workstream adds a tab with one entry and the admin-only tabs are not even
 * shown to everyone else. With users, backup, email and now security an administrator has nine tabs, more than a phone
 * shows: lot A8b (decision P13 b, contract C7, «A8b — Contratto») gathers the administrators' tabs under one entry of the
 * bar, «Administration», and lists its members in a second bar. The approved contract:
 *   - `SettingsTab` = `{id, labelKey, icon, order, component, visible?(ctx), props?(ctx), alignEnd?, group?, badge?(ctx),
 *     prefetch?(ctx)}`, where the context is `{isSuperuser}`; `id` is both the `?tab=` value and the suffix of the
 *     `settings-tab-{id}` test id, `visible` absent means visible to everyone, `props` are spread on the body, `alignEnd`
 *     starts the right-hand side on a wide screen, `group` names the group of `SETTINGS_TAB_GROUPS` the tab belongs to,
 *     `badge(ctx)` is the number its entry shows (0: none), `prefetch(ctx)` what the page starts loading before the tab
 *     is opened — so that the badge can count;
 *   - `SETTINGS_TAB_GROUPS`: `SettingsTabGroup` = `{id, labelKey, icon, alignEnd?}`, one group today: `administration`,
 *     labelled `settings.administration`, drawn with `Shield`, with `alignEnd` — the right-hand side is the group now,
 *     and no tab carries `alignEnd`. A group's id is a `?tab=` value and a test-id suffix too (`settings-tab-
 *     administration`), so it is URL-safe and no tab's id;
 *   - `SETTINGS_TABS`: profile, preferences, plugins and about in no group; admin, users, backup, email and security, in
 *     that order, the members of `administration`. Plugins is everyone's: each user's own plugin settings, the
 *     instance's read-only unless an administrator (the API says which field each caller may write, so the tab takes no
 *     props). Admin is labelled `settings.globalSettings` and drawn with `Settings2`: the group took its label and its
 *     icon. Since N69-2 (decision D4 a) it is for administrators only, like every other member of its group (`visible:
 *     ctx => ctx.isSuperuser`), so a user's bar has no «Administration» at all; it keeps `props: ctx => ({canEdit:
 *     ctx.isSuperuser})`, whose read-only branch no user reaches any more. Users, backup and email are
 *     administrators-only and take no props, as before. Security is new —
 *     administrators only, `settings.security`, `ShieldCheck`, the body of `security/SecurityTab.svelte`, no props — and
 *     the only tab with a badge and a prefetch, both delegated to the security checks' store
 *     (`security/securityChecks.svelte`, the singleton `securityChecks`): the badge is its `attentionCount`, the prefetch
 *     its `ensureLoaded()` for an administrator, nothing for a user;
 *   - `visibleSettingsTabs(tabs, ctx)`: the tabs whose `visible(ctx)` is not false, sorted by `order`. It takes the list
 *     explicitly, so that a test can hand it one of its own, and it leaves that list as it was;
 *   - `settingsBar(tabs, groups, ctx)`: the entries of the top bar — the visible tabs, as `visibleSettingsTabs` gives
 *     them, where every visible member of a group is replaced by ONE `{kind: 'group', group, members}` entry, in the
 *     place of its first (lowest-order) visible member, `members` its visible members by order; every other tab a
 *     `{kind: 'tab', tab}` entry; a group with no visible member has no entry; the lists it is given are left as they
 *     were. Pure, so it is pinned here on lists of its own; the page that draws it has `page.tabs.test.ts`.
 *
 * The `order` numbers are not the contract, only their sequence: the cases compare ids in the order the helpers give
 * them, never a number — save one. Users takes 110, the slot plan A6b.1 gives it so that the admin tabs of several
 * workstreams land without a tie (backup 120, email 130 and security 140 took the next ones), and STAB-02 holds it
 * there. The `TODAY` table below is the registry's content; a workstream that adds a tab adds its row there, its id to
 * the `CONTEXTS` and `BARS` lists of those who see it and, when the tab joins the administration group, to
 * `ADMINISTRATION`, in the same change.
 *
 * Why the tab modules are mocked. Each tab body imports the API client, the stores and their own children, so importing
 * the real modules would make this file depend on everything they reach (and on whatever any of them does at import
 * time) while it asks one thing of them: which module each tab points at. Each module is replaced, by its path, with a
 * function of its own, and the registry's `component` must be that very function — which holds only if the registry
 * imported the default export of that path. The security checks' store is replaced the same way, by its path: the
 * registry only hands its count to the bar and asks it to load, and the store has tests of its own
 * (`security/*.test.ts`); here it is an object whose count a case sets and whose `ensureLoaded` a case watches. The
 * lucide icons are the real ones: the registry's `icon` is compared with the export the bar will draw.
 *
 * Labels — the tabs' and the groups' — are checked against the four generated catalogues (`$lib/i18n/<lang>.json`,
 * built from their sources before every Vitest run), as in `stores/app/auth.test.ts`: a key one catalogue lacks is drawn
 * as the key itself in that language.
 *
 * Written red-first three times. In A3 the module did not exist, and the whole file failed on its import. In A6b the
 * registry had no users row, and the cases naming it failed. In A8b the registry has no group, no badge, no prefetch and
 * no security tab, and admin still carries its old label, its old icon and `alignEnd`: every case marked `red until
 * A8b` fails on its own expectation, and the others stay green. `SETTINGS_TAB_GROUPS` and `settingsBar` are read off the
 * module namespace (`settingsTabsModule`): a named import of an export that does not exist yet would take the whole file
 * down with it, and the type check does not wait for A8b either — the A8b shapes are written out below (`GroupedTab`,
 * `TabGroup`, `BarEntry`). `SecurityTab.svelte` and the store are mocked by their paths, so their absence alone breaks
 * nothing.
 *
 * And a fourth time in N69-2 (decision D4 a: «Administration» for administrators only). The admin entry has no
 * `visible`, so a user still sees Global Settings, read-only, and the group with it: every case marked `red until
 * N69-2` — a user's tabs and bar (`CONTEXTS`, `BARS`), admin's visibility, STAB-14 — fails on its own expectation, and
 * the others stay green.
 */
import {beforeEach, describe, expect, it, vi} from 'vitest';
import type {Component, ComponentType} from 'svelte';
import {DatabaseBackup, Info, Mail, Puzzle, Settings2, Shield, ShieldCheck, Sliders, User, Users} from 'lucide-svelte';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

/** One function per tab module, each standing for that module's default export. */
const bodies = vi.hoisted(() => {
    const body = (module: string) => Object.assign(() => undefined, {module});
    return {
        profile: body('ProfileTab.svelte'),
        preferences: body('PreferencesTab.svelte'),
        about: body('AboutTab.svelte'),
        admin: body('GlobalSettingsTab.svelte'),
        users: body('UsersTab.svelte'),
        backup: body('BackupTab.svelte'),
        email: body('EmailSettingsTab.svelte'),
        plugins: body('PluginSettingsTab.svelte'),
        security: body('SecurityTab.svelte'),
    };
});

/** The security checks' store, as the registry sees it: how many findings need attention, and the load. */
const checks = vi.hoisted(() => ({attentionCount: 0, ensureLoaded: vi.fn(async () => undefined)}));

vi.mock('$lib/features/settings/tabs/ProfileTab.svelte', () => ({default: bodies.profile}));
vi.mock('$lib/features/settings/tabs/PreferencesTab.svelte', () => ({default: bodies.preferences}));
vi.mock('$lib/features/settings/tabs/AboutTab.svelte', () => ({default: bodies.about}));
vi.mock('$lib/features/settings/tabs/GlobalSettingsTab.svelte', () => ({default: bodies.admin}));
vi.mock('$lib/features/settings/tabs/UsersTab.svelte', () => ({default: bodies.users}));
vi.mock('$lib/features/backup/BackupTab.svelte', () => ({default: bodies.backup}));
vi.mock('$lib/features/email/EmailSettingsTab.svelte', () => ({default: bodies.email}));
vi.mock('$lib/features/plugin-settings/PluginSettingsTab.svelte', () => ({default: bodies.plugins}));
// A8b: the Security tab and the store its badge and its prefetch delegate to. Neither exists yet: a mock of a path
// nobody imports changes nothing.
vi.mock('$lib/features/settings/security/SecurityTab.svelte', () => ({default: bodies.security}));
vi.mock('$lib/features/settings/security/securityChecks.svelte', () => ({securityChecks: checks}));

import {SETTINGS_TABS, visibleSettingsTabs, type SettingsTab, type SettingsTabContext} from './settingsTabs';
// A8b: the module itself too, so that what A8b adds is read as properties: a named import of an export that does not
// exist yet would fail every case of this file, not only theirs.
import * as settingsTabsModule from './settingsTabs';

/**
 * A tab as A8b defines it: today's `SettingsTab` and the three fields it gains, written out until `settingsTabs.ts`
 * declares them. `group` is any id here: the synthetic groups of `settingsBar`'s cases are none of the registry's.
 */
type GroupedTab = Omit<SettingsTab, 'group' | 'badge' | 'prefetch'> & {group?: string; badge?: (ctx: SettingsTabContext) => number; prefetch?: (ctx: SettingsTabContext) => void};

/** A group of tabs (`SettingsTabGroup`), written out until `settingsTabs.ts` exports it. */
interface TabGroup {
    id: string;
    labelKey: string;
    icon: ComponentType;
    alignEnd?: boolean;
}

/** One entry of the top bar (`SettingsBarEntry`): a tab on its own, or a group with its visible members. */
type BarEntry = {kind: 'tab'; tab: GroupedTab} | {kind: 'group'; group: TabGroup; members: GroupedTab[]};

/** A signed-in user who is not an administrator. */
const USER: SettingsTabContext = {isSuperuser: false};
/** An administrator. */
const ADMIN: SettingsTabContext = {isSuperuser: true};
/** Who is signed in, the ids of the tabs they see, by order, and their context. */
const CONTEXTS: [string, string[], SettingsTabContext][] = [
    // red until N69-2: admin, an administrator's like the rest of its group
    ['a user', ['profile', 'preferences', 'plugins', 'about'], USER],
    // red until A8b: security, the administrators' new tab
    ['an administrator', ['profile', 'preferences', 'plugins', 'about', 'admin', 'users', 'backup', 'email', 'security'], ADMIN],
];
/** Who is signed in, the entries of their top bar — a tab's id, or a group's id with its members' — and their context. */
const BARS: [string, string[], SettingsTabContext][] = [
    // red until N69-2: a user sees no member of Administration, so the group has no entry
    ['a user', ['profile', 'preferences', 'plugins', 'about'], USER],
    ['an administrator', ['profile', 'preferences', 'plugins', 'about', 'administration[admin,users,backup,email,security]'], ADMIN],
];
/** The members of the administration group, by order. */
const ADMINISTRATION = ['admin', 'users', 'backup', 'email', 'security'];

/** Today's tabs, by order as an administrator sees them: the id, the catalogue key of the label, the lucide icon and the tab module. */
const TODAY = [
    {id: 'profile', labelKey: 'settings.profile', icon: User, component: bodies.profile},
    {id: 'preferences', labelKey: 'settings.preferences', icon: Sliders, component: bodies.preferences},
    {id: 'plugins', labelKey: 'pluginSettings.tab.label', icon: Puzzle, component: bodies.plugins},
    {id: 'about', labelKey: 'settings.about', icon: Info, component: bodies.about},
    // red until A8b: «Global settings» with Settings2 — the group took «Administration» and the Shield
    {id: 'admin', labelKey: 'settings.globalSettings', icon: Settings2, component: bodies.admin},
    {id: 'users', labelKey: 'settings.users', icon: Users, component: bodies.users},
    {id: 'backup', labelKey: 'backup.tab', icon: DatabaseBackup, component: bodies.backup},
    {id: 'email', labelKey: 'email.tab.label', icon: Mail, component: bodies.email},
    // red until A8b: the new tab
    {id: 'security', labelKey: 'settings.security', icon: ShieldCheck, component: bodies.security},
];

/** What an id must look like to be a `?tab=` value and a test-id suffix as it is. */
const URL_SAFE_ID = /^[a-z][a-z0-9-]*$/;

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** The leaf behind a dotted key, read from the catalogue file itself. */
function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The labels of these tabs or groups that are not a sentence in every catalogue, as `id: key in locale`. */
function missingSentences(labelled: readonly {id: string; labelKey: string}[]): string[] {
    return labelled.flatMap((entry) =>
        Object.entries(CATALOGUES)
            .filter(([, catalogue]) => {
                const sentence = leaf(catalogue, entry.labelKey);
                return typeof sentence !== 'string' || sentence.trim() === '';
            })
            .map(([locale]) => `${entry.id}: ${entry.labelKey} in ${locale}`),
    );
}

/** The registry's tab with this id: its absence fails here, naming it. */
function registryTab(id: string): SettingsTab {
    const tab = SETTINGS_TABS.find((candidate) => candidate.id === id);
    expect(tab, `the registry has a tab with id ${id}`).toBeDefined();
    return tab as SettingsTab;
}

/** The registry's groups, read off the module namespace: their absence fails the case that asks, naming the export. */
function registryGroups(): readonly TabGroup[] {
    const groups = (settingsTabsModule as unknown as {SETTINGS_TAB_GROUPS?: unknown}).SETTINGS_TAB_GROUPS;
    expect(Array.isArray(groups), 'settingsTabs.ts exports SETTINGS_TAB_GROUPS, the groups of the bar (A8b)').toBe(true);
    return groups as readonly TabGroup[];
}

/** `settingsBar(tabs, groups, ctx)`, read off the module namespace: its absence fails the case that asks, naming the export. */
function settingsBar(tabs: readonly GroupedTab[], groups: readonly TabGroup[], ctx: SettingsTabContext): BarEntry[] {
    const helper = (settingsTabsModule as unknown as {settingsBar?: unknown}).settingsBar;
    expect(typeof helper, 'settingsTabs.ts exports settingsBar(tabs, groups, ctx), the entries of the top bar (A8b)').toBe('function');
    return (helper as (tabs: readonly GroupedTab[], groups: readonly TabGroup[], ctx: SettingsTabContext) => BarEntry[])(tabs, groups, ctx);
}

/** An entry as the cases compare it: a tab's id, or a group's id with the ids of its members — `administration[admin,users]`. */
function describeEntry(entry: BarEntry): string {
    if (entry.kind === 'tab') return entry.tab.id;
    if (entry.kind === 'group') return `${entry.group.id}[${entry.members.map((member) => member.id).join(',')}]`;
    return `an entry of no known kind: ${JSON.stringify(entry)}`;
}

describe('SETTINGS_TABS — today’s tabs, and nothing else', () => {
    it('every id is unique and URL-safe: it is the ?tab= value and the suffix of settings-tab-{id}', () => {
        const ids = SETTINGS_TABS.map((tab) => tab.id);

        expect(new Set(ids).size, `no id is carried twice: ${ids.join(', ')}`).toBe(ids.length);
        expect(
            ids.filter((id) => !URL_SAFE_ID.test(id)),
            'an id is lowercase letters, digits and dashes, starting with a letter',
        ).toEqual([]);
    });

    it('every order is a unique finite number: the bar never has to break a tie', () => {
        const orders = SETTINGS_TABS.map((tab) => tab.order);

        expect(
            orders.filter((order) => !Number.isFinite(order)),
            'an order is a finite number',
        ).toEqual([]);
        expect(new Set(orders).size, `no order is carried twice: ${orders.join(', ')}`).toBe(orders.length);
    });

    // red until A8b: security
    it('holds exactly the tabs of TODAY: a new tab adds its row there', () => {
        expect(SETTINGS_TABS.map((tab) => tab.id).sort(), 'the registry is today’s tabs: a tab added (or lost) on the way changes what users see').toEqual(TODAY.map((tab) => tab.id).sort());
    });

    // red until A8b: the administrator's row (security); red until N69-2: the user's row (admin)
    it.each(CONTEXTS)('%s sees %j, in this order', (_label, expected, ctx) => {
        expect(
            visibleSettingsTabs(SETTINGS_TABS, ctx).map((tab) => tab.id),
            'today’s tabs, by order: plugins is visible to everyone, admin, users, backup, email and security to administrators only',
        ).toEqual(expected);
    });

    // red until A8b: the admin row (its label and its icon) and the security row
    it.each(TODAY)('$id: labelled $labelKey, drawn with its lucide icon, rendering its own tab module', ({id, labelKey, icon, component}) => {
        const tab = registryTab(id);

        expect(tab.labelKey, `${id} is labelled by ${labelKey}`).toBe(labelKey);
        expect(tab.icon, `${id} draws the lucide icon of TODAY`).toBe(icon);
        expect(tab.component, `${id} renders the default export of its tab module (${component.module})`).toBe(component);
    });

    it('every label is a sentence in en, it, fr and es', () => {
        expect(missingSentences(SETTINGS_TABS), 'a label one catalogue lacks is drawn as its key in that language').toEqual([]);
    });

    // red until N69-2: the visibility half (decision D4 a) — until then admin was everyone's, read-only for a user
    it('admin is for administrators only — hidden from a user, shown to an administrator — and editable by them: {canEdit: isSuperuser}', () => {
        const admin = registryTab('admin');

        expect(admin.visible, 'admin says who may see it: without visible() every signed-in user gets the global settings, read-only').toBeTypeOf('function');
        expect(admin.visible?.(USER) ?? true, 'a user is not shown the global settings of the instance').toBe(false);
        expect(admin.visible?.(ADMIN) ?? true, 'an administrator is').toBe(true);
        expect(admin.props?.(USER), 'the props stay {canEdit: isSuperuser}: false for a user, a branch the page no longer reaches').toEqual({canEdit: false});
        expect(admin.props?.(ADMIN), 'an administrator may change them').toEqual({canEdit: true});
    });

    it('backup is for administrators only: no props, no alignEnd of its own, after admin', () => {
        const backup = registryTab('backup');

        expect(backup.visible, 'backup says who may see it: without visible() every user would').toBeTypeOf('function');
        expect(backup.visible?.(USER) ?? true, 'a user does not see the backup tab: the archive holds every user’s data').toBe(false);
        expect(backup.visible?.(ADMIN) ?? true, 'an administrator sees the backup tab').toBe(true);
        expect(backup.props, 'backup is rendered with no props').toBeUndefined();
        expect(backup.alignEnd, 'backup pushes nothing to the right: the right-hand side is not its to start').toBeFalsy();

        const ids = visibleSettingsTabs(SETTINGS_TABS, ADMIN).map((tab) => tab.id);
        const adminAt = ids.indexOf('admin');
        expect(adminAt, `premise: an administrator sees admin: ${ids.join(', ')}`).toBeGreaterThanOrEqual(0);
        expect(ids.indexOf('backup'), `backup comes after admin: ${ids.join(', ')}`).toBeGreaterThan(adminAt);
    });

    it('email is visible to administrators only and takes no props', () => {
        const email = registryTab('email');

        expect(email.visible?.(USER) ?? true, 'a user does not see the email tab').toBe(false);
        expect(email.visible?.(ADMIN) ?? true, 'an administrator sees it').toBe(true);
        expect(email.props, 'the email tab is rendered with no props').toBeUndefined();
    });

    it('plugins is everyone’s, takes no props and carries no alignEnd (workstream X, CP11b)', () => {
        const plugins = registryTab('plugins');

        expect(plugins.visible, 'no visible(): every signed-in user has plugin settings of their own').toBeUndefined();
        expect(plugins.props, 'no props: the API says which field each caller may write (D-X15)').toBeUndefined();
        expect(plugins.alignEnd, 'plugins sits with the personal tabs, on the left').toBeFalsy();
    });

    it('only admin takes props: every other tab is rendered with none', () => {
        expect(
            SETTINGS_TABS.filter((tab) => tab.props !== undefined).map((tab) => tab.id),
            'profile, preferences and about as before, users, backup, email and security as planned',
        ).toEqual(['admin']);
    });

    it('STAB-01: users is for administrators only — hidden from a user, shown to an administrator', () => {
        const users = registryTab('users');

        expect(users.visible, 'users says who may see it: without visible() every signed-in user would get the tab').toBeTypeOf('function');
        expect(users.visible?.(USER), 'a user is not shown the accounts of the instance').toBe(false);
        expect(users.visible?.(ADMIN), 'an administrator is').toBe(true);
        expect(
            visibleSettingsTabs(SETTINGS_TABS, USER).map((tab) => tab.id),
            'the bar of a user has no users tab',
        ).not.toContain('users');
        expect(
            visibleSettingsTabs(SETTINGS_TABS, ADMIN).map((tab) => tab.id),
            'the bar of an administrator has it',
        ).toContain('users');
    });

    // red until A8b: the group (until A8b admin started the right-hand side with alignEnd; the group does now)
    it('STAB-02: users takes order 110 and sits after admin, both members of the administration group', () => {
        const users: GroupedTab = registryTab('users');
        const admin: GroupedTab = registryTab('admin');
        const ids = visibleSettingsTabs(SETTINGS_TABS, ADMIN).map((tab) => tab.id);

        expect(users.order, 'order 110, the slot plan A6b.1 gives users: the admin tabs of other workstreams take the next ones').toBe(110);
        expect(ids.indexOf('users'), `users is drawn after admin: ${ids.join(', ')}`).toBeGreaterThan(ids.indexOf('admin'));
        expect(admin.group, 'admin opens the administration group').toBe('administration');
        expect(users.group, 'users sits in it with admin: the right-hand side is the group now').toBe('administration');
    });
});

describe('SETTINGS_TAB_GROUPS — the administration group, and what its tabs carry (A8b)', () => {
    beforeEach(() => {
        checks.attentionCount = 0;
        checks.ensureLoaded.mockClear();
    });

    // red until A8b
    it('STAB-03: SETTINGS_TAB_GROUPS holds the administration group alone — labelled settings.administration, drawn with Shield, on the right', () => {
        const groups = registryGroups();

        expect(
            groups.map((group) => group.id),
            'one group today',
        ).toEqual(['administration']);
        const [administration] = groups;
        expect(administration.labelKey, 'labelled «Administration»').toBe('settings.administration');
        expect(administration.icon, 'drawn with the Shield admin drew until now').toBe(Shield);
        expect(administration.alignEnd, 'the group starts the right-hand side on a wide screen, as admin did until now').toBe(true);
    });

    // red until A8b
    it('STAB-04: every group id is unique, URL-safe and no tab’s id: it is a ?tab= value and the suffix of settings-tab-{id} too', () => {
        const ids = registryGroups().map((group) => group.id);
        const tabIds = SETTINGS_TABS.map((tab) => tab.id);

        expect(new Set(ids).size, `no group id is carried twice: ${ids.join(', ')}`).toBe(ids.length);
        expect(
            ids.filter((id) => !URL_SAFE_ID.test(id)),
            'a group id is lowercase letters, digits and dashes, starting with a letter',
        ).toEqual([]);
        expect(
            ids.filter((id) => tabIds.includes(id)),
            'a group id that is also a tab id would make settings-tab-{id} and ?tab={id} name two things',
        ).toEqual([]);
    });

    // red until A8b: SETTINGS_TAB_GROUPS, and settings.administration in the four catalogues
    it('STAB-05: every group label is a sentence in en, it, fr and es', () => {
        expect(missingSentences(registryGroups()), 'a label one catalogue lacks is drawn as its key in that language').toEqual([]);
    });

    // red until A8b
    it('STAB-06: admin, users, backup, email and security make the administration group; profile, preferences, plugins and about belong to none', () => {
        const tabs: readonly GroupedTab[] = SETTINGS_TABS;

        expect(Object.fromEntries(tabs.map((tab) => [tab.id, tab.group ?? null])), 'the administrators’ tabs — the global settings among them — gather under Administration; a personal tab stays on the bar').toEqual(
            Object.fromEntries(TODAY.map(({id}) => [id, ADMINISTRATION.includes(id) ? 'administration' : null])),
        );
    });

    // red until A8b
    it('STAB-07: every group a tab names is one of SETTINGS_TAB_GROUPS, and every group has a member', () => {
        const groupIds = registryGroups().map((group) => group.id);
        const tabs: readonly GroupedTab[] = SETTINGS_TABS;

        expect(
            tabs.filter((tab) => tab.group !== undefined && !groupIds.includes(tab.group)).map((tab) => `${tab.id}: ${tab.group}`),
            'a tab naming a group nobody declared would have no entry to sit under',
        ).toEqual([]);
        expect(
            groupIds.filter((id) => !tabs.some((tab) => tab.group === id)),
            'a group no tab names is drawn nowhere',
        ).toEqual([]);
    });

    // red until A8b
    it('STAB-08: no tab carries alignEnd: the administration group starts the right-hand side', () => {
        expect(
            SETTINGS_TABS.filter((tab) => tab.alignEnd).map((tab) => tab.id),
            'alignEnd moved from admin to its group: the group’s entry is what sits on the right',
        ).toEqual([]);
    });

    // red until A8b
    it('STAB-09: security is for administrators only, takes no props, and comes after email', () => {
        const security = registryTab('security');

        expect(security.visible, 'security says who may see it: without visible() every user would').toBeTypeOf('function');
        expect(security.visible?.(USER) ?? true, 'a user is not shown the security checks of the instance').toBe(false);
        expect(security.visible?.(ADMIN) ?? true, 'an administrator is').toBe(true);
        expect(security.props, 'security is rendered with no props').toBeUndefined();

        const ids = visibleSettingsTabs(SETTINGS_TABS, ADMIN).map((tab) => tab.id);
        expect(ids.indexOf('security'), `security comes after email, the last of the administration group: ${ids.join(', ')}`).toBeGreaterThan(ids.indexOf('email'));
    });

    // red until A8b
    it('STAB-10: security’s badge is the security checks’ attentionCount, read each time the bar asks', () => {
        const security: GroupedTab = registryTab('security');
        expect(security.badge, 'security has a badge').toBeTypeOf('function');

        checks.attentionCount = 0;
        expect(security.badge?.(ADMIN), 'nothing needs attention: 0, which the bar does not draw').toBe(0);
        checks.attentionCount = 3;
        expect(security.badge?.(ADMIN), 'the count of the store as it is now, not as it was when the registry was loaded').toBe(3);
    });

    // red until A8b
    it('STAB-11: security’s prefetch loads the security checks for an administrator, and nothing for a user', () => {
        const security: GroupedTab = registryTab('security');
        expect(security.prefetch, 'security has a prefetch').toBeTypeOf('function');

        security.prefetch?.(USER);
        expect(checks.ensureLoaded, 'a user may not read the checks: nothing is loaded').not.toHaveBeenCalled();
        security.prefetch?.(ADMIN);
        expect(checks.ensureLoaded, 'an administrator’s bar loads them, once, so that the badge counts before the tab is opened').toHaveBeenCalledTimes(1);
    });

    // red until A8b
    it('STAB-12: security is the only tab with a badge and a prefetch', () => {
        const tabs: readonly GroupedTab[] = SETTINGS_TABS;

        expect(
            tabs.filter((tab) => tab.badge !== undefined).map((tab) => tab.id),
            'no other tab counts anything',
        ).toEqual(['security']);
        expect(
            tabs.filter((tab) => tab.prefetch !== undefined).map((tab) => tab.id),
            'no other tab loads anything before it is opened',
        ).toEqual(['security']);
    });

    // red until A8b; red until N69-2: the user's row
    it.each(BARS)('STAB-13: settingsBar on the registry — %s sees %j', (_label, expected, ctx) => {
        expect(settingsBar(SETTINGS_TABS, registryGroups(), ctx).map(describeEntry), 'the personal tabs, then — for an administrator only — Administration with every administrators’ tab').toEqual(expected);
    });

    // red until N69-2: the user's half (decision D4 a)
    it('STAB-14: settingsBar on the registry — a user’s bar has no administration entry, nor any member of the group; an administrator’s has the entry, admin first among its members', () => {
        const groups = registryGroups();
        const isAdministration = (entry: BarEntry) => entry.kind === 'group' && entry.group.id === 'administration';
        const tabIdsOf = (entry: BarEntry) => (entry.kind === 'tab' ? [entry.tab.id] : entry.members.map((member) => member.id));
        const userBar = settingsBar(SETTINGS_TABS, groups, USER);

        expect(userBar.length, 'premise: a user’s bar has entries').toBeGreaterThan(0);
        expect(userBar.filter(isAdministration).map(describeEntry), 'a user sees no member of Administration, so the group has no entry in the bar').toEqual([]);
        expect(
            userBar.flatMap(tabIdsOf).filter((id) => ADMINISTRATION.includes(id)),
            'and no member of it stands anywhere else in the bar',
        ).toEqual([]);

        const administration = settingsBar(SETTINGS_TABS, groups, ADMIN).filter(isAdministration);
        expect(administration.map(describeEntry), 'an administrator’s bar has the administration entry, once').toHaveLength(1);
        const [entry] = administration;
        expect(entry.kind === 'group' ? entry.members[0]?.id : undefined, 'admin — Global Settings — is its first member: the group opens on it').toBe('admin');
    });
});

/**
 * `visibleSettingsTabs` on a list of its own: the helper reads `visible` and `order` and nothing else,
 * so the synthetic tabs carry a body nobody renders. The list is out of order on purpose, and holds a
 * tab whose `visible` says yes, one that follows the context, one that always says no and two without
 * `visible` at all.
 */
describe('visibleSettingsTabs — keeps what the context may see, sorted by order, and leaves its input alone', () => {
    const NO_BODY = (() => undefined) as unknown as Component;

    function tab(id: string, order: number, extra: Partial<SettingsTab> = {}): SettingsTab {
        return {id, labelKey: `test.settingsTabs.${id}`, icon: Info, order, component: NO_BODY, ...extra};
    }

    function unsorted(): SettingsTab[] {
        return [tab('c', 30), tab('a', 10, {visible: () => true}), tab('staff', 20, {visible: (ctx) => ctx.isSuperuser}), tab('never', 5, {visible: () => false}), tab('b', 15)];
    }

    it.each([
        ['a user', USER, ['a', 'b', 'c']],
        ['an administrator', ADMIN, ['a', 'b', 'staff', 'c']],
    ] as const)('for %s: the tabs without visible() and those whose visible(ctx) is true, by ascending order', (_label, ctx, expected) => {
        expect(
            visibleSettingsTabs(unsorted(), ctx).map((kept) => kept.id),
            'a tab whose visible(ctx) is false is left out, every other one is kept, sorted by order',
        ).toEqual(expected);
    });

    it('asks each visible() about the context it was given', () => {
        const visible = vi.fn((ctx: SettingsTabContext) => ctx.isSuperuser);
        const ctx: SettingsTabContext = {isSuperuser: true};

        visibleSettingsTabs([tab('a', 10), tab('staff', 20, {visible})], ctx);

        expect(visible, 'visible() decides on the context of the page, not on one of its own').toHaveBeenCalledWith(ctx);
    });

    it('leaves the list it is given as it was, and answers a new array', () => {
        const input = unsorted();
        const before = [...input];

        const kept = visibleSettingsTabs(input, ADMIN);

        expect(kept, 'premise: the helper sorted and filtered').toHaveLength(4);
        expect(
            input.map((given) => given.id),
            'the input keeps its order and its length: SETTINGS_TABS is shared by every render of the page',
        ).toEqual(before.map((given) => given.id));
        input.forEach((given, index) => expect(given, `input[${index}] is the tab it was`).toBe(before[index]));
        expect(kept, 'the answer is a new array, not the input sorted in place').not.toBe(input);
    });
});

/**
 * `settingsBar` on lists of its own: the helper reads `visible`, `order` and `group` — and hands the groups it is given
 * back in their entries —, so the synthetic tabs carry a body nobody renders. The tabs are out of order on purpose, and
 * so are the groups: an entry's place comes from its members' order, never from where its group sits in the list.
 *   - early: e1 (8, administrators only), e3 (20), e2 (40) — its first visible member is e1 for an administrator,
 *     before the ungrouped `a` (10), and e3 for a user, after it; the ungrouped `b` (30) falls between its members;
 *   - late (alignEnd): l1 (70), l2 (80, administrators only);
 *   - ghost: g1 (50, administrators only) — no visible member for a user;
 *   - empty: no member at all;
 *   - a (10), b (30) and z (90) in no group, and `never` (5), which nobody sees.
 */
describe('settingsBar — the entries of the top bar (A8b)', () => {
    const NO_BODY = (() => undefined) as unknown as Component;
    const staffOnly = (ctx: SettingsTabContext) => ctx.isSuperuser;

    function tab(id: string, order: number, extra: Partial<GroupedTab> = {}): GroupedTab {
        return {id, labelKey: `test.settingsTabs.${id}`, icon: Info, order, component: NO_BODY, ...extra};
    }

    function group(id: string, extra: Partial<TabGroup> = {}): TabGroup {
        return {id, labelKey: `test.settingsTabs.group.${id}`, icon: Shield, ...extra};
    }

    function unsortedTabs(): GroupedTab[] {
        return [
            tab('z', 90),
            tab('l2', 80, {group: 'late', visible: staffOnly}),
            tab('a', 10),
            tab('e2', 40, {group: 'early'}),
            tab('l1', 70, {group: 'late'}),
            tab('never', 5, {visible: () => false}),
            tab('e1', 8, {group: 'early', visible: staffOnly}),
            tab('b', 30),
            tab('g1', 50, {group: 'ghost', visible: staffOnly}),
            tab('e3', 20, {group: 'early'}),
        ];
    }

    function unsortedGroups(): TabGroup[] {
        return [group('late', {alignEnd: true}), group('empty'), group('ghost'), group('early')];
    }

    // red until A8b
    it.each([
        ['a user', USER, ['a', 'early[e3,e2]', 'b', 'late[l1]', 'z']],
        ['an administrator', ADMIN, ['early[e1,e3,e2]', 'a', 'b', 'ghost[g1]', 'late[l1,l2]', 'z']],
    ] as const)('SBAR-01: for %s, the visible tabs by order, the visible members of each group gathered into one entry in the place of the first of them', (_label, ctx, expected) => {
        expect(settingsBar(unsortedTabs(), unsortedGroups(), ctx).map(describeEntry), 'a group sits where its lowest-order visible member would, gathers its later members over the tabs between them, and holds only the members this context sees, by order').toEqual(expected);
    });

    // red until A8b
    it('SBAR-02: a group with no visible member — ghost, for a user — or with no member at all has no entry', () => {
        const groupsOf = (ctx: SettingsTabContext) => settingsBar(unsortedTabs(), unsortedGroups(), ctx).flatMap((entry) => (entry.kind === 'group' ? [entry.group.id] : []));

        expect(groupsOf(USER), 'a user sees no member of ghost, and nobody sees one of empty').toEqual(['early', 'late']);
        expect(groupsOf(ADMIN), 'an administrator sees g1, so ghost has its entry; empty never has one').toEqual(['early', 'ghost', 'late']);
    });

    // red until A8b
    it('SBAR-03: a group’s entry carries the group it was given — its id, label, icon and alignEnd, which the page draws', () => {
        const groups = unsortedGroups();
        const late = groups.find((candidate) => candidate.id === 'late');

        const entry = settingsBar(unsortedTabs(), groups, ADMIN).find((candidate) => candidate.kind === 'group' && candidate.group.id === 'late');

        expect(entry, 'premise: late has an entry').toBeDefined();
        expect(entry?.kind === 'group' ? entry.group : undefined, 'the group as it was given').toEqual(late);
    });

    // red until A8b
    it.each([
        ['a user', USER, ['a', 'b', 'c']],
        ['an administrator', ADMIN, ['a', 'b', 'staff', 'c']],
    ] as const)('SBAR-04: with no group, for %s, the bar is visibleSettingsTabs — one tab entry per visible tab, by order', (_label, ctx, expected) => {
        const entries = settingsBar([tab('c', 30), tab('a', 10, {visible: () => true}), tab('staff', 20, {visible: staffOnly}), tab('never', 5, {visible: () => false}), tab('b', 15)], [], ctx);

        expect(
            entries.map((entry) => entry.kind),
            'every entry is a tab',
        ).toEqual(expected.map(() => 'tab'));
        expect(entries.map(describeEntry), 'the tabs visibleSettingsTabs keeps, in its order').toEqual(expected);
    });

    // red until A8b
    it('SBAR-05: leaves the lists it is given as they were, and answers a new array', () => {
        const tabs = unsortedTabs();
        const groups = unsortedGroups();
        const tabsBefore = [...tabs];
        const groupsBefore = [...groups];

        const entries = settingsBar(tabs, groups, ADMIN);

        expect(entries.length, 'premise: the bar has entries').toBeGreaterThan(0);
        expect(
            tabs.map((given) => given.id),
            'the tabs keep their order and their length: SETTINGS_TABS is shared by every render of the page',
        ).toEqual(tabsBefore.map((given) => given.id));
        tabs.forEach((given, index) => expect(given, `tabs[${index}] is the tab it was`).toBe(tabsBefore[index]));
        expect(
            groups.map((given) => given.id),
            'the groups keep their order and their length: SETTINGS_TAB_GROUPS is shared too',
        ).toEqual(groupsBefore.map((given) => given.id));
        groups.forEach((given, index) => expect(given, `groups[${index}] is the group it was`).toBe(groupsBefore[index]));
        expect(entries, 'the answer is a new array').not.toBe(tabs);
    });
});
