/**
 * The Settings tab registry — `settingsTabs.ts` (workstream A, plan A3).
 *
 * The Settings page wrote its four tabs by hand (`routes/(app)/settings/+page.svelte`): a `TabId`
 * union, an `isTabId` guard, a list of `{id, icon, labelKey}`, an `{#if}` chain choosing the body,
 * `canEdit={isSuperuser}` on the admin body and an inline `className: 'sm:ml-auto'` pushing the admin
 * tab to the right. Workstreams B and X each need a tab of their own, and the coming admin-only tabs
 * (Users, Security) must not even be shown to everyone else: with the page as it was, each of them
 * would have edited the union, the guard, the list and the chain. The approved design (plan A3.1,
 * `plan-phase01Accounts` §4.2) moves the tabs into a registry, `lib/features/settings/settingsTabs.ts`:
 *   - `SettingsTab` = `{id, labelKey, icon, order, component, visible?(ctx), props?(ctx), alignEnd?}`,
 *     where the context is `{isSuperuser}`; `id` is both the `?tab=` value and the suffix of the
 *     `settings-tab-{id}` test id, `visible` absent means visible to everyone, `props` are spread on
 *     the body, `alignEnd` starts the right-hand group on a wide screen;
 *   - `SETTINGS_TABS`: today's tabs and nothing else — profile, preferences, about, admin and, since plan
 *     A6b.1, users. Admin stays visible to everyone and editable only by an administrator (`props: ctx =>
 *     ({canEdit: ctx.isSuperuser})`), and `alignEnd` takes the place of the inline class. Users is shown to
 *     administrators only (`visible: ctx => ctx.isSuperuser`) and sits after admin, in the right-hand group;
 *   - `visibleSettingsTabs(tabs, ctx)`: the tabs whose `visible(ctx)` is not false, sorted by
 *     `order`. It takes the list explicitly, so that a test can hand it one of its own, and it leaves
 *     that list as it was.
 *
 * The `order` numbers are not the contract, only their sequence: the cases compare ids in the order
 * the helper gives them, never a number — save one. Users takes 110, the slot plan A6b.1 gives it so
 * that the admin tabs of several workstreams land without a tie (the next slots are theirs), and
 * STAB-02 holds it there. The `TODAY` table below is the registry's content; a workstream that adds a
 * tab adds its row there, in the same change, marked `adminOnly` when only an administrator sees it.
 *
 * Why the tab modules are mocked. Each tab body imports the API client, the stores and their own
 * children, so importing the real modules would make this file depend on everything they reach (and
 * on whatever any of them does at import time) while it asks one thing of them: which module each tab
 * points at. Each module is replaced, by its path, with a function of its own, and the registry's
 * `component` must be that very function — which holds only if the registry imported the default
 * export of that path. The lucide icons are the real ones: the registry's `icon` is compared with the
 * export the bar will draw.
 *
 * Labels are checked against the four generated catalogues (`$lib/i18n/<lang>.json`, built from their
 * sources before every Vitest run), as in `stores/app/auth.test.ts`: a key one catalogue lacks is drawn
 * as the key itself in that language.
 *
 * Written red-first twice. In A3 the module did not exist, and the whole file failed on its import. In
 * A6b the registry has no users row yet: the cases that name it fail — the set of ids, what an
 * administrator sees, the users row of TODAY, STAB-01 and STAB-02 — and every other case stays green
 * (`UsersTab.svelte` is mocked by its path, so its absence alone breaks nothing).
 */
import {describe, expect, it, vi} from 'vitest';
import type {Component} from 'svelte';
import {Info, Shield, Sliders, User, Users} from 'lucide-svelte';
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
    };
});

vi.mock('$lib/features/settings/tabs/ProfileTab.svelte', () => ({default: bodies.profile}));
vi.mock('$lib/features/settings/tabs/PreferencesTab.svelte', () => ({default: bodies.preferences}));
vi.mock('$lib/features/settings/tabs/AboutTab.svelte', () => ({default: bodies.about}));
vi.mock('$lib/features/settings/tabs/GlobalSettingsTab.svelte', () => ({default: bodies.admin}));
vi.mock('$lib/features/settings/tabs/UsersTab.svelte', () => ({default: bodies.users}));

import {SETTINGS_TABS, visibleSettingsTabs, type SettingsTab, type SettingsTabContext} from './settingsTabs';

/** A signed-in user who is not an administrator. */
const USER: SettingsTabContext = {isSuperuser: false};
/** An administrator. */
const ADMIN: SettingsTabContext = {isSuperuser: true};
const CONTEXTS: [string, SettingsTabContext][] = [
    ['a user', USER],
    ['an administrator', ADMIN],
];

/**
 * Today's tabs, left to right as an administrator sees them: the id, the catalogue key of the label, the lucide icon,
 * the tab module, and `adminOnly` on a tab only an administrator sees.
 */
const TODAY = [
    {id: 'profile', labelKey: 'settings.profile', icon: User, component: bodies.profile},
    {id: 'preferences', labelKey: 'settings.preferences', icon: Sliders, component: bodies.preferences},
    {id: 'about', labelKey: 'settings.about', icon: Info, component: bodies.about},
    {id: 'admin', labelKey: 'settings.admin', icon: Shield, component: bodies.admin},
    {id: 'users', labelKey: 'settings.users', icon: Users, component: bodies.users, adminOnly: true},
];

/** The ids of TODAY that `ctx` may see, left to right: a row marked `adminOnly` is an administrator's alone. */
function todayFor(ctx: SettingsTabContext): string[] {
    return TODAY.filter((tab) => ctx.isSuperuser || !tab.adminOnly).map((tab) => tab.id);
}

/** What an id must look like to be a `?tab=` value and a test-id suffix as it is. */
const URL_SAFE_ID = /^[a-z][a-z0-9-]*$/;

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** The leaf behind a dotted key, read from the catalogue file itself. */
function leaf(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The registry's tab with this id: its absence fails here, naming it. */
function registryTab(id: string): SettingsTab {
    const tab = SETTINGS_TABS.find((candidate) => candidate.id === id);
    expect(tab, `the registry has a tab with id ${id}`).toBeDefined();
    return tab as SettingsTab;
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

    it('holds exactly profile, preferences, about, admin and users: a new tab adds its row to TODAY', () => {
        expect(SETTINGS_TABS.map((tab) => tab.id).sort(), 'the registry is the tabs of TODAY: a tab added (or lost) on the way changes what every user sees').toEqual(TODAY.map((tab) => tab.id).sort());
    });

    it.each(CONTEXTS)('%s sees the tabs of TODAY meant for them, in this order', (_label, ctx) => {
        expect(
            visibleSettingsTabs(SETTINGS_TABS, ctx).map((tab) => tab.id),
            'today’s tabs, left to right: admin is visible to everyone, users to an administrator only',
        ).toEqual(todayFor(ctx));
    });

    it.each(TODAY)('$id: labelled $labelKey, drawn with its lucide icon, rendering its own tab module', ({id, labelKey, icon, component}) => {
        const tab = registryTab(id);

        expect(tab.labelKey, `${id} is labelled by ${labelKey}`).toBe(labelKey);
        expect(tab.icon, `${id} draws the lucide icon it drew before`).toBe(icon);
        expect(tab.component, `${id} renders the default export of its tab module (${component.module})`).toBe(component);
    });

    it('every label is a sentence in en, it, fr and es', () => {
        const missing = SETTINGS_TABS.flatMap((tab) =>
            Object.entries(CATALOGUES)
                .filter(([, catalogue]) => {
                    const sentence = leaf(catalogue, tab.labelKey);
                    return typeof sentence !== 'string' || sentence.trim() === '';
                })
                .map(([locale]) => `${tab.id}: ${tab.labelKey} in ${locale}`),
        );

        expect(missing, 'a label one catalogue lacks is drawn as its key in that language').toEqual([]);
    });

    it('admin is visible to everyone and editable only by an administrator: {canEdit: isSuperuser}', () => {
        const admin = registryTab('admin');

        expect(admin.visible?.(USER) ?? true, 'a user sees the admin tab, read-only').toBe(true);
        expect(admin.visible?.(ADMIN) ?? true, 'an administrator sees the admin tab').toBe(true);
        expect(admin.props?.(USER), 'a user may read the global settings, not change them').toEqual({canEdit: false});
        expect(admin.props?.(ADMIN), 'an administrator may change them').toEqual({canEdit: true});
    });

    it('only admin takes props, and only admin starts the right-hand group (alignEnd)', () => {
        expect(
            SETTINGS_TABS.filter((tab) => tab.props !== undefined).map((tab) => tab.id),
            'every other tab is rendered with no props: profile, preferences and about as before, users as planned',
        ).toEqual(['admin']);
        expect(
            SETTINGS_TABS.filter((tab) => tab.alignEnd).map((tab) => tab.id),
            'alignEnd takes the place of the inline sm:ml-auto the page gave the admin tab alone',
        ).toEqual(['admin']);
        expect(registryTab('admin').alignEnd, 'admin starts the right-hand group').toBe(true);
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

    it('STAB-02: users takes order 110 and sits after admin, in the right-hand group admin starts', () => {
        const users = registryTab('users');
        const bar = visibleSettingsTabs(SETTINGS_TABS, ADMIN);
        const ids = bar.map((tab) => tab.id);
        const groupStart = bar.findIndex((tab) => tab.alignEnd);

        expect(users.order, 'order 110, the slot plan A6b.1 gives users: the admin tabs of other workstreams take the next ones').toBe(110);
        expect(ids[groupStart], `premise: admin starts the right-hand group of ${ids.join(', ')}`).toBe('admin');
        expect(ids.indexOf('users'), `users is drawn after admin, in the right-hand group: ${ids.join(', ')}`).toBeGreaterThan(groupStart);
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
