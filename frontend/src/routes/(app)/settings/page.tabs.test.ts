// @vitest-environment jsdom
/**
 * Settings page — the runtime of the tab registry (workstream A: plan A3, and the «Administration» group of lot A8b).
 *
 * The page wrote its four tabs by hand: a `TabId` union and its guard, a list of `{id, icon, labelKey}`, an `{#if}` chain
 * choosing the body, `canEdit={isSuperuser}` on the admin body and an inline `className: 'sm:ml-auto'` on the admin tab.
 * Plan A3 moved the tabs into a registry (`$lib/features/settings/settingsTabs`, pinned by its own `settingsTabs.test.ts`)
 * and made the page, in Svelte 5 runes, its runtime. Lot A8b (decision P13 b, contract C7, «A8b — Contratto») gathers
 * the administrators' tabs under one entry of the bar, so that nine tabs fit a phone: a tab may name a `group` of
 * `SETTINGS_TAB_GROUPS`, and carry a `badge(ctx)` and a `prefetch(ctx)`. The approved contract:
 *   - the context is `{isSuperuser: $auth.user?.is_superuser ?? false}`, from `$lib/stores/app/auth`;
 *   - the top bar (one TabBar, `scrollable`, labels hidden on a phone) draws `settingsBar(SETTINGS_TABS,
 *     SETTINGS_TAB_GROUPS, ctx)`: a tab entry as before — test id `settings-tab-{id}`, label `$_(labelKey)`, its icon —,
 *     and, for a group with a visible member, ONE entry in the place of its first visible member — test id
 *     `settings-tab-{groupId}`, label `$_(group.labelKey)`, the group's icon; `sm:ml-auto` on an entry whose tab or group
 *     has `alignEnd`, and on no other;
 *   - badges: a tab entry's is `badge(ctx)`, a group entry's the sum of its visible members'; TabBar draws none for 0;
 *   - the active tab is always a real tab — a member or an ungrouped tab — and the top bar selects the group of an
 *     active member. A second TabBar (`scrollable`), inside `settings-subtabs`, lists the visible members of the active
 *     tab's group — each with its own test id, label, icon and badge, the active one selected — and is drawn only when
 *     that group has two visible members or more: with one (a user's Administration holds the global settings alone)
 *     there is no second bar and no button of the member's own, and the group's entry opens it directly;
 *   - clicking a group opens its first visible member, unless one of its members is open already: then nothing changes;
 *     clicking a member of the second bar opens it;
 *   - the body is the active tab's `component` with `props(ctx)` spread on it, and only that body; the heading a phone
 *     shows names the active tab — a member, never its group;
 *   - the active tab is the first visible one, unless `?tab=` (the `page` store of `$app/stores`) names a visible tab —
 *     a member too: then that one, already at the first render (the default body is never mounted, not even for an
 *     instant), and again whenever `?tab=` changes; `?tab=` naming a group opens its first visible member. An unknown
 *     id, or the id of a tab this user cannot see, is ignored. A value is applied once: after the user picked another
 *     tab, a page update that keeps the same `?tab=` does not take the tab back (`appliedTabParam`); a value naming a tab
 *     this user cannot see yet is applied as soon as it appears;
 *   - `prefetch(ctx)` runs for every visible tab that has one, once at the start and again whenever the context changes;
 *     never for a tab this context does not show, and never again for anything else — a change of tab or of `?tab=`, or
 *     of the state a prefetch reads (it reads the state it fills);
 *   - a tab with `visible: ctx => ctx.isSuperuser` is absent for a user and appears as soon as the auth store's user
 *     becomes an administrator.
 *
 * Held still:
 *   - `settingsTabs` is the real module with `SETTINGS_TABS` and `SETTINGS_TAB_GROUPS` replaced (`importOriginal` keeps the
 *     real `visibleSettingsTabs` and `settingsBar`): the page takes its lists from the registry and hands them to the
 *     helpers, so the lists given here are what it must render. The synthetic registry is out of order on purpose — the
 *     bar follows `order`, not positions:
 *       - alpha (10), beta (20: a badge of its count and of the context, a prefetch), gamma (30, `alignEnd`: the registry
 *         gives no tab one any more, but the page still honours a tab's, so the class is pinned on both kinds of entry)
 *         and staff (40, administrators only, as A3 had it) belong to no group;
 *       - crew: echo (50, administrators only, a badge), delta (55, a badge), foxtrot (60) — three members, two for a
 *         user, whose first visible one is therefore delta, echo for an administrator;
 *       - office (`alignEnd`): omega (100, `props`), sigma (110, administrators only), tau (120, administrators only, a
 *         badge, a prefetch) — the stand-in for Administration: a user sees omega alone, as the global settings;
 *   - each synthetic body is `SettingsTabProbe`, and each icon `SettingsIconProbe` (`src/__tests__/harness`), told which
 *     tab or group it stands for; a body is handed the props object the page passed, and each call of a body is one
 *     mount, logged in `mounts`;
 *   - the counts the badges read sit in a reactive box (`reactiveBox`), as the security checks' store is reactive: a
 *     count arriving after the first render is what the page must show. The prefetches are spies; beta's reads beta's
 *     count, as the checks' `ensureLoaded()` reads the state it fills;
 *   - the real tab modules are no-ops: the real registry imports them, as the page did, and they reach the API client
 *     and the stores, none of which is the subject; so are the Security tab and the checks' store of A8b;
 *   - the `page` store and the auth store are writables the test holds; `$_` marks what it translated, `⟦key⟧`, so a
 *     label is proven to have gone through the translator without naming any language;
 *   - `TabBar` is the real one: what the page hands it is observed as TabBar draws it.
 *
 * Assertions read test ids, `aria-selected`, the probes' attributes, the level-1 heading, the number on a badge — TabBar
 * gives the badge no test id: it is the only text of a tab made of digits alone, the label being `⟦key⟧` — and two
 * class tokens that are the contract here: `sm:ml-auto`, and `hidden sm:inline` as `TabBar.test.ts` reads it (jsdom
 * loads no Tailwind, so the token is what can be observed).
 *
 * Written red-first twice. In A3 the page drew its tabs by hand and never read the registry: every case was red. In
 * A8b the page draws every visible tab flat and knows no group, no badge and no prefetch: the cases marked `red until
 * A8b` fail on their own expectation — the entries of the top bar, a group's entry and its second bar, `?tab=` naming
 * a member or a group, the badges, the prefetches, `sm:ml-auto` on a group —, and the A3 cases, which open ungrouped
 * tabs or reach omega through `?tab=` (a member is a `?tab=` value before A8b and after), stay green.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type Component, type ComponentType} from 'svelte';
import type {SettingsTab, SettingsTabContext} from '$lib/features/settings/settingsTabs';

/**
 * A registry tab as A8b defines it — `SettingsTab` and the three fields it gains —, written out until settingsTabs.ts
 * declares them: the type check does not wait for A8b. `group` is any id: the synthetic groups are none of the registry's.
 */
type SyntheticTab = Omit<SettingsTab, 'group' | 'badge' | 'prefetch'> & {group?: string; badge?: (ctx: SettingsTabContext) => number; prefetch?: (ctx: SettingsTabContext) => void};

/** A group of tabs as A8b defines it (`SettingsTabGroup`), written out until settingsTabs.ts exports it. */
interface SyntheticGroup {
    id: string;
    labelKey: string;
    icon: ComponentType;
    alignEnd?: boolean;
}

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    const {default: SettingsTabProbe} = await import('$test/harness/SettingsTabProbe.svelte');
    const {default: SettingsIconProbe} = await import('$test/harness/SettingsIconProbe.svelte');
    const {reactiveBox} = await import('$test/runes.svelte');

    /** The synthetic tab of every body mounted, in order: a body never shown has no entry. */
    const mounts: string[] = [];

    /**
     * The body of one synthetic tab: the probe, told which tab it stands for. A Svelte 5 component is a function of an
     * anchor and a props object, so this one mounts the probe in its place, logging the mount and passing the page's own
     * props object on, read through a getter so it stays live.
     */
    function probeBody(name: string): Component<Record<string, unknown>> {
        const mountProbe = SettingsTabProbe as unknown as (anchor: unknown, props: object) => unknown;
        return ((anchor: unknown, props: Record<string, unknown>) => {
            mounts.push(name);
            return mountProbe(anchor, {
                probe: name,
                get received() {
                    return props;
                },
            });
        }) as unknown as Component<Record<string, unknown>>;
    }

    /** The icon of one synthetic tab or group: the icon probe, told what it stands for, mounted as a body is. */
    function probeIcon(name: string): ComponentType {
        const mountIcon = SettingsIconProbe as unknown as (anchor: unknown, props: object) => unknown;
        return ((anchor: unknown, props: Record<string, unknown>) =>
            mountIcon(anchor, {
                icon: name,
                get size() {
                    return props.size;
                },
            })) as unknown as ComponentType;
    }

    /** The counts the synthetic badges read: reactive, as the security checks' store is. */
    const badges = reactiveBox({beta: 0, delta: 0, echo: 0, tau: 0});

    /** The prefetches. Beta's reads beta's count, as the checks' `ensureLoaded()` reads the state it fills. */
    const prefetches = {
        beta: vi.fn((_ctx: SettingsTabContext) => {
            void badges.beta;
        }),
        tau: vi.fn((_ctx: SettingsTabContext) => undefined),
    };

    const staffOnly = (ctx: SettingsTabContext) => ctx.isSuperuser;

    function syntheticTab(id: string, order: number, extra: Partial<SyntheticTab> = {}): SyntheticTab {
        return {id, labelKey: `test.settingsTabs.${id}`, icon: probeIcon(id), order, component: probeBody(id), ...extra};
    }

    const tabs: SyntheticTab[] = [
        syntheticTab('gamma', 30, {alignEnd: true}),
        syntheticTab('omega', 100, {group: 'office', props: (ctx) => ({canEdit: ctx.isSuperuser})}),
        syntheticTab('alpha', 10),
        syntheticTab('echo', 50, {group: 'crew', visible: staffOnly, badge: () => badges.echo}),
        syntheticTab('tau', 120, {group: 'office', visible: staffOnly, badge: () => badges.tau, prefetch: prefetches.tau}),
        syntheticTab('staff', 40, {visible: staffOnly}),
        syntheticTab('delta', 55, {group: 'crew', badge: () => badges.delta}),
        syntheticTab('beta', 20, {badge: (ctx) => badges.beta + (ctx.isSuperuser ? 100 : 0), prefetch: prefetches.beta}),
        syntheticTab('sigma', 110, {group: 'office', visible: staffOnly}),
        syntheticTab('foxtrot', 60, {group: 'crew'}),
    ];

    const groups: SyntheticGroup[] = [
        {id: 'office', labelKey: 'test.settingsTabs.office', icon: probeIcon('office'), alignEnd: true},
        {id: 'crew', labelKey: 'test.settingsTabs.crew', icon: probeIcon('crew')},
    ];

    return {
        tabs,
        groups,
        mounts,
        badges,
        prefetches,
        page: writable({url: new URL('http://librefolio.test/settings')}),
        auth: writable<{user: {is_superuser: boolean} | null}>({user: {is_superuser: false}}),
        noopComponent: () => {},
    };
});

vi.mock('$lib/features/settings/settingsTabs', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/settings/settingsTabs')>()),
    SETTINGS_TABS: mocks.tabs,
    SETTINGS_TAB_GROUPS: mocks.groups,
}));
vi.mock('$lib/features/settings/tabs/ProfileTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/PreferencesTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/AboutTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/GlobalSettingsTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/UsersTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/email/EmailSettingsTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/backup/BackupTab.svelte', () => ({default: mocks.noopComponent}));
// Workstream X (CP11b): reached through the real registry like the others; unmocked, its form's date formatter would
// load the language store, which reads constants the `$lib/i18n` mock below does not provide, and the file would fail
// on its import.
vi.mock('$lib/features/plugin-settings/PluginSettingsTab.svelte', () => ({default: mocks.noopComponent}));
// A8b: the real registry imports the Security tab and the security checks' store; unmocked, they would reach the API
// client and the stores. Neither exists yet: a mock of a path nobody imports changes nothing.
vi.mock('$lib/features/settings/security/SecurityTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/security/securityChecks.svelte', () => ({securityChecks: {attentionCount: 0, ensureLoaded: async () => undefined}}));
vi.mock('$app/stores', () => ({page: {subscribe: mocks.page.subscribe}}));
vi.mock('$lib/stores/app/auth', () => ({auth: {subscribe: mocks.auth.subscribe}}));
vi.mock('$lib/i18n', async () => {
    const {readable} = await import('svelte/store');
    return {_: readable((key: string) => `⟦${key}⟧`)};
});

import {cleanup, fireEvent, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import SettingsPage from './+page.svelte';

const SETTINGS_URL = 'http://librefolio.test/settings';

/** The ungrouped tabs a user sees, by order. */
const USER_UNGROUPED = ['alpha', 'beta', 'gamma'];

/** What the marking translator draws for a key. */
const marked = (key: string): string => `⟦${key}⟧`;

/** The synthetic tab with this id. */
function synthetic(id: string): SyntheticTab {
    const tab = mocks.tabs.find((candidate) => candidate.id === id);
    if (!tab) throw new Error(`test bug: no synthetic tab ${id}`);
    return tab;
}

/** The synthetic group with this id. */
function syntheticGroup(id: string): SyntheticGroup {
    const group = mocks.groups.find((candidate) => candidate.id === id);
    if (!group) throw new Error(`test bug: no synthetic group ${id}`);
    return group;
}

/** The id behind a `settings-tab-{id}` test id. */
function idOf(button: HTMLElement): string {
    return (button.getAttribute('data-testid') ?? '').replace(/^settings-tab-/, '');
}

const isSelected = (button: HTMLElement): boolean => button.getAttribute('aria-selected') === 'true';

/** The second bar — the members of the open group —, or null when the page draws none. */
function subtabs(): HTMLElement | null {
    const bars = screen.queryAllByTestId('settings-subtabs');
    expect(bars.length, 'the page draws one second bar at most').toBeLessThanOrEqual(1);
    return bars[0] ?? null;
}

/** The tabs of the top bar: every tab outside the second bar. */
function topTabs(): HTMLElement[] {
    return screen.queryAllByRole('tab').filter((button) => button.closest('[data-testid="settings-subtabs"]') === null);
}

/** The ids of the top bar's entries, left to right. */
function topIds(): string[] {
    return topTabs().map(idOf);
}

/** The ids of the top bar's selected entries: one, when the page works. */
function topSelected(): string[] {
    return topTabs().filter(isSelected).map(idOf);
}

/** The ids of the second bar's tabs, left to right, or null when there is no second bar. */
function subIds(): string[] | null {
    const bar = subtabs();
    return bar ? within(bar).queryAllByRole('tab').map(idOf) : null;
}

/** The ids of the second bar's selected tabs: none without a second bar. */
function subSelected(): string[] {
    const bar = subtabs();
    return bar ? within(bar).queryAllByRole('tab').filter(isSelected).map(idOf) : [];
}

/** The ids of every selected tab, in both bars. */
function selected(): string[] {
    return screen.queryAllByRole('tab').filter(isSelected).map(idOf);
}

/** The button of the tab or group with this id: its absence fails here, naming it. */
function tabButton(id: string): HTMLElement {
    const button = screen.queryByTestId(`settings-tab-${id}`);
    expect(button, `the page has a settings-tab-${id} button (top bar: ${topIds().join(', ')}; second bar: ${subIds()?.join(', ') ?? 'none'})`).not.toBeNull();
    return button as HTMLElement;
}

/** The tab or group an entry's icon stands for. */
function iconOf(button: HTMLElement): string | null {
    const icons = within(button).queryAllByTestId('settings-icon-probe');
    expect(icons.length, `${button.getAttribute('data-testid')} draws one icon`).toBe(1);
    return icons[0].getAttribute('data-icon');
}

/**
 * The number on the badge of the tab or group with this id, or null when TabBar draws none — it draws none for 0. TabBar
 * gives the badge no test id: it is the only text of the button made of digits alone, the label being `⟦key⟧`.
 */
function badgeOf(id: string): number | null {
    const numbers = within(tabButton(id)).queryAllByText(/^\d+$/);
    expect(numbers.length, `settings-tab-${id} draws one badge at most`).toBeLessThanOrEqual(1);
    return numbers.length === 0 ? null : Number(numbers[0].textContent?.trim());
}

/** The body on screen — the synthetic tab it stands for and the props it was given — or null when none is drawn. */
function body(): {tab: string | null; received: unknown} | null {
    const probes = screen.queryAllByTestId('settings-tab-probe');
    expect(probes.length, 'the page draws the body of the active tab, and no other').toBeLessThanOrEqual(1);
    if (probes.length === 0) return null;
    return {tab: probes[0].getAttribute('data-probe'), received: JSON.parse(probes[0].getAttribute('data-received') ?? 'null')};
}

/** The level-1 heading: the title a phone shows in place of the hidden tab labels. */
function heading(): string | undefined {
    return screen.queryByRole('heading', {level: 1})?.textContent?.trim();
}

/** The contexts a synthetic prefetch was called with, as their `isSuperuser`, in order. */
function prefetched(id: 'beta' | 'tau'): boolean[] {
    return mocks.prefetches[id].mock.calls.map(([ctx]) => ctx.isSuperuser);
}

/** Mounts the page at /settings with this query, for a user or an administrator, and lets it settle. */
async function mountPage({query = '', isSuperuser = false}: {query?: string; isSuperuser?: boolean} = {}): Promise<void> {
    mocks.page.set({url: new URL(`${SETTINGS_URL}${query}`)});
    mocks.auth.set({user: {is_superuser: isSuperuser}});
    render(SettingsPage);
    await tick();
}

/** What a client-side navigation does to the page store: a new page value, here with this query. */
async function navigate(query: string): Promise<void> {
    mocks.page.set({url: new URL(`${SETTINGS_URL}${query}`)});
    await tick();
}

/** The signed-in user becomes an administrator, in the auth store, while the page is open. */
async function becomeAdministrator(): Promise<void> {
    mocks.auth.set({user: {is_superuser: true}});
    await tick();
}

beforeEach(() => {
    // "Never mounted" and "never prefetched" below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
    mocks.mounts.length = 0;
    Object.assign(mocks.badges, {beta: 0, delta: 0, echo: 0, tau: 0});
    mocks.prefetches.beta.mockClear();
    mocks.prefetches.tau.mockClear();
});

afterEach(() => {
    cleanup();
});

describe('Settings page — the bar and the body come from the registry', () => {
    it('draws each visible ungrouped tab, by ascending order, with its own icon and its label through the translator, hidden on a phone', async () => {
        await mountPage();

        expect(
            topIds().filter((id) => USER_UNGROUPED.includes(id)),
            'the ungrouped tabs a user sees follow their order, not their place in the registry',
        ).toEqual(USER_UNGROUPED);
        for (const id of USER_UNGROUPED) {
            const button = tabButton(id);
            const label = within(button).queryByText(marked(synthetic(id).labelKey));
            expect(iconOf(button), `${id} draws its own icon`).toBe(id);
            expect(label, `${id} is labelled $_(labelKey)`).not.toBeNull();
            expect(label, `${id}: the label is hidden on a phone, where the heading names the active tab`).toHaveClass('hidden', 'sm:inline');
        }
    });

    // red until A8b: the office group's entry (until A8b alignEnd sat on the admin tab; it sits on Administration now)
    it('SPAGE-01: puts sm:ml-auto on an entry whose tab or group has alignEnd, and on no other — gamma, and the office group', async () => {
        await mountPage();

        expect(
            topIds().filter((id) => tabButton(id).classList.contains('sm:ml-auto')),
            'alignEnd is the only way an entry gets sm:ml-auto: a tab’s own (gamma), or its group’s (office, the stand-in for Administration)',
        ).toEqual(['gamma', 'office']);
    });

    it('opens on the first visible tab, its body drawn with no props, the heading naming it', async () => {
        await mountPage();

        expect(selected(), 'the first visible tab is the default').toEqual(['alpha']);
        expect(body(), 'its body is drawn, and a tab without props(ctx) passes none').toEqual({tab: 'alpha', received: {}});
        expect(heading(), 'the heading names the active tab through the translator').toBe(marked('test.settingsTabs.alpha'));
    });

    it('reads a store without a user (not loaded yet) as not an administrator', async () => {
        mocks.page.set({url: new URL(SETTINGS_URL)});
        mocks.auth.set({user: null});
        render(SettingsPage);
        await tick();

        expect(screen.queryByTestId('settings-tab-staff'), '$auth.user?.is_superuser ?? false: no user is no administrator, and no crash').toBeNull();
        expect(body(), 'the default body is drawn').toEqual({tab: 'alpha', received: {}});
    });

    it('shows the body of the tab the user clicks, and the bar and the heading follow', async () => {
        await mountPage();
        expect(body(), 'premise: the default body is on screen').toEqual({tab: 'alpha', received: {}});

        await fireEvent.click(tabButton('gamma'));

        expect(selected(), 'the clicked tab is selected').toEqual(['gamma']);
        expect(body(), 'its body replaces the previous one').toEqual({tab: 'gamma', received: {}});
        expect(heading(), 'the heading names the clicked tab').toBe(marked('test.settingsTabs.gamma'));
    });

    // omega is reached through ?tab=, which names it before A8b and after: a user's office holds it alone, and then it has
    // no button of its own (SPAGE-08 opens it through its group).
    it.each([
        ['a user', false],
        ['an administrator', true],
    ])('spreads props(ctx) on the body of a tab that has them, for %s', async (_label, isSuperuser) => {
        await mountPage({query: '?tab=omega', isSuperuser});

        expect(body(), 'the body receives props(ctx), computed on the page’s context').toEqual({tab: 'omega', received: {canEdit: isSuperuser}});
    });

    it('keeps the spread props in step with the auth store while the body is on screen', async () => {
        await mountPage({query: '?tab=omega'});
        expect(body(), 'premise: a user may not edit').toEqual({tab: 'omega', received: {canEdit: false}});

        await becomeAdministrator();

        expect(body(), 'the user became an administrator: the body is told so, as canEdit followed $auth before').toEqual({tab: 'omega', received: {canEdit: true}});
    });
});

describe('Settings page — ?tab= selects a visible tab', () => {
    it('selects the tab ?tab= names at the first render: no other body is ever mounted, not even the default for an instant', async () => {
        await mountPage({query: '?tab=gamma'});

        expect(selected(), 'the tab ?tab= names is selected').toEqual(['gamma']);
        expect(body(), 'and its body drawn').toEqual({tab: 'gamma', received: {}});
        expect(mocks.mounts, 'premise: the body of the tab ?tab= names was mounted').toContain('gamma');
        expect(
            mocks.mounts.filter((tab) => tab !== 'gamma'),
            'no flash of the default tab: the page chose before it drew, and mounted no other body',
        ).toEqual([]);
    });

    it('selects the tab a later ?tab= names, each time it changes', async () => {
        await mountPage();
        expect(body()?.tab, 'premise: the default tab is open').toBe('alpha');

        await navigate('?tab=beta');
        expect(selected(), 'a new ?tab= selects its tab').toEqual(['beta']);
        expect(body()?.tab, 'and draws its body').toBe('beta');

        await navigate('?tab=gamma');
        expect(selected(), 'and so does the next one').toEqual(['gamma']);
        expect(body()?.tab, 'and draws its body').toBe('gamma');
    });

    it.each([
        ['an unknown id', '?tab=nope'],
        ['the id of a tab this user cannot see', '?tab=staff'],
        ['an empty value', '?tab='],
    ])('ignores ?tab= with %s at the first render: the first visible tab opens', async (_label, query) => {
        await mountPage({query});

        expect(screen.queryByTestId('settings-tab-staff'), 'premise: this user does not see the administrators’ tab').toBeNull();
        expect(selected(), 'a value that names no visible tab selects nothing of its own').toEqual(['alpha']);
        expect(body(), 'the default body is drawn').toEqual({tab: 'alpha', received: {}});
    });

    it('leaves the current tab when a later ?tab= names no visible tab', async () => {
        await mountPage({query: '?tab=beta'});
        expect(body()?.tab, 'premise: ?tab=beta opened beta').toBe('beta');

        await navigate('?tab=nope');
        expect(selected(), 'an unknown id changes nothing').toEqual(['beta']);

        await navigate('?tab=staff');
        expect(selected(), 'nor does the id of a tab this user cannot see').toEqual(['beta']);
        expect(body()?.tab, 'the body stays').toBe('beta');
    });

    it('applies a ?tab= value once: after the user picked another tab, a page update keeping it does not take the tab back', async () => {
        await mountPage({query: '?tab=beta'});
        expect(selected(), 'premise: ?tab=beta opened beta').toEqual(['beta']);
        await fireEvent.click(tabButton('gamma'));
        expect(selected(), 'premise: the user picked gamma').toEqual(['gamma']);

        await navigate('?tab=beta');
        expect(selected(), 'the same URL again: the value was applied already').toEqual(['gamma']);

        await navigate('?tab=beta&from=elsewhere');
        expect(selected(), 'another URL with the same ?tab=: still applied already').toEqual(['gamma']);
        expect(body()?.tab, 'the body the user picked stays').toBe('gamma');
    });
});

describe('Settings page — a tab only an administrator sees', () => {
    it('is absent for a user, and takes its place in the bar once the store’s user becomes an administrator', async () => {
        await mountPage();
        expect(topIds(), 'a user does not see it').not.toContain('staff');

        await becomeAdministrator();

        const ids = topIds();
        const gammaAt = ids.indexOf('gamma');
        expect(ids.slice(gammaAt, gammaAt + 2), `an administrator does, in its order, right after gamma: ${ids.join(', ')}`).toEqual(['gamma', 'staff']);
        expect(selected(), 'a tab appearing does not take the selection').toEqual(['alpha']);
        expect(body()?.tab, 'the body stays').toBe('alpha');
    });

    it('opens at the first render for an administrator whose ?tab= names it', async () => {
        await mountPage({query: '?tab=staff', isSuperuser: true});

        expect(topIds(), 'premise: the bar is the administrator’s').toContain('staff');
        expect(selected(), '?tab= names a tab this administrator sees').toEqual(['staff']);
        expect(body(), 'its body is drawn').toEqual({tab: 'staff', received: {}});
        expect(
            mocks.mounts.filter((tab) => tab !== 'staff'),
            'no other body was mounted first',
        ).toEqual([]);
    });

    it('applies a pending ?tab= that names it as soon as it appears', async () => {
        await mountPage({query: '?tab=staff'});
        expect(selected(), 'premise: a user cannot open it, so the default tab opens').toEqual(['alpha']);

        await becomeAdministrator();

        expect(topIds(), 'premise: the tab appeared').toContain('staff');
        expect(selected(), 'the ?tab= that waited for it is applied now').toEqual(['staff']);
        expect(body(), 'and its body drawn').toEqual({tab: 'staff', received: {}});
    });
});

describe('Settings page — a group of tabs: one entry above, its members in a second bar (A8b)', () => {
    // red until A8b
    it.each([
        {who: 'a user', isSuperuser: false, expected: ['alpha', 'beta', 'gamma', 'crew', 'office']},
        {who: 'an administrator', isSuperuser: true, expected: ['alpha', 'beta', 'gamma', 'staff', 'crew', 'office']},
    ])('SPAGE-02: for $who, the top bar is settingsBar: the ungrouped tabs and one entry per group with a visible member, by order', async ({isSuperuser, expected}) => {
        await mountPage({isSuperuser});

        expect(topIds(), 'crew sits where its first visible member would, office where omega would; no member has an entry of its own up there').toEqual(expected);
    });

    // red until A8b
    it.each(['crew', 'office'])('SPAGE-03: the %s group’s entry: settings-tab-{groupId}, the group’s own icon, its label through the translator, hidden on a phone', async (groupId) => {
        await mountPage();
        const button = tabButton(groupId);
        const label = within(button).queryByText(marked(syntheticGroup(groupId).labelKey));

        expect(iconOf(button), 'the group’s own icon, not one of its members’').toBe(groupId);
        expect(label, 'labelled $_(group.labelKey)').not.toBeNull();
        expect(label, 'hidden on a phone, like every label of the top bar').toHaveClass('hidden', 'sm:inline');
    });

    // red until A8b
    it.each([
        {groupId: 'crew', who: 'a user', isSuperuser: false, members: ['delta', 'foxtrot']},
        {groupId: 'crew', who: 'an administrator', isSuperuser: true, members: ['echo', 'delta', 'foxtrot']},
        {groupId: 'office', who: 'an administrator', isSuperuser: true, members: ['omega', 'sigma', 'tau']},
    ])('SPAGE-04: clicking $groupId, for $who, opens its first visible member — the group selected above, a second bar of its visible members, the member selected there', async ({groupId, isSuperuser, members}) => {
        await mountPage({isSuperuser});
        expect(subtabs(), 'premise: no group is open, so there is no second bar').toBeNull();

        await fireEvent.click(tabButton(groupId));

        const first = members[0];
        expect(topSelected(), 'the top bar selects the group').toEqual([groupId]);
        expect(subIds(), 'the second bar lists the group’s visible members, by order').toEqual(members);
        expect(subSelected(), 'and selects the first of them: the active tab is a real tab, never the group').toEqual([first]);
        expect(body()?.tab, 'its body is drawn').toBe(first);
        expect(heading(), 'the heading a phone shows names the member, not the group').toBe(marked(synthetic(first).labelKey));
    });

    // red until A8b
    it('SPAGE-05: a member in the second bar keeps its own test id, its own icon and its label through the translator; the second bar scrolls sideways', async () => {
        await mountPage({isSuperuser: true});
        await fireEvent.click(tabButton('crew'));
        expect(subIds(), 'premise: crew’s second bar is open').toEqual(['echo', 'delta', 'foxtrot']);

        expect(within(subtabs() as HTMLElement).queryByTestId('tab-bar-scroller'), 'the second TabBar is scrollable, as the top one is: five members do not fit a phone either').not.toBeNull();
        for (const id of ['echo', 'delta', 'foxtrot']) {
            const button = within(subtabs() as HTMLElement).getByTestId(`settings-tab-${id}`);
            expect(iconOf(button), `${id} draws its own icon`).toBe(id);
            expect(within(button).queryByText(marked(synthetic(id).labelKey)), `${id} is labelled $_(labelKey)`).not.toBeNull();
        }
    });

    // red until A8b
    it('SPAGE-06: clicking a member of the second bar opens it — its group stays selected above, the heading names it', async () => {
        await mountPage();
        await fireEvent.click(tabButton('crew'));
        expect(subSelected(), 'premise: crew opened on delta').toEqual(['delta']);

        await fireEvent.click(tabButton('foxtrot'));

        expect(subSelected(), 'the clicked member is selected').toEqual(['foxtrot']);
        expect(topSelected(), 'its group stays selected above').toEqual(['crew']);
        expect(body(), 'its body replaces the previous one').toEqual({tab: 'foxtrot', received: {}});
        expect(heading(), 'the heading names the member').toBe(marked(synthetic('foxtrot').labelKey));
    });

    // red until A8b
    it('SPAGE-07: clicking the group of the open member changes nothing — the member stays, its body is not mounted again', async () => {
        await mountPage();
        await fireEvent.click(tabButton('crew'));
        await fireEvent.click(tabButton('foxtrot'));
        expect(subSelected(), 'premise: foxtrot is open').toEqual(['foxtrot']);
        const mountsBefore = [...mocks.mounts];

        await fireEvent.click(tabButton('crew'));

        expect(subSelected(), 'still foxtrot, not the group’s first member').toEqual(['foxtrot']);
        expect(topSelected(), 'the group stays selected').toEqual(['crew']);
        expect(body()?.tab, 'the body stays').toBe('foxtrot');
        expect(mocks.mounts, 'no body was mounted: nothing changed').toEqual(mountsBefore);
    });

    // red until A8b
    it('SPAGE-08: a group with one visible member — office, for a user — has no second bar: its entry opens the member directly, and the member has no button of its own', async () => {
        await mountPage();

        await fireEvent.click(tabButton('office'));

        expect(topSelected(), 'the group is selected').toEqual(['office']);
        expect(subtabs(), 'one member: no second bar').toBeNull();
        expect(screen.queryByTestId('settings-tab-omega'), 'and no settings-tab-omega anywhere').toBeNull();
        expect(body(), 'the member’s body, with its props').toEqual({tab: 'omega', received: {canEdit: false}});
        expect(heading(), 'the heading names the member, not the group').toBe(marked(synthetic('omega').labelKey));
    });

    // red until A8b
    it('SPAGE-09: an ungrouped tab closes the second bar, and the group opens on its first visible member again', async () => {
        await mountPage();
        await fireEvent.click(tabButton('crew'));
        await fireEvent.click(tabButton('foxtrot'));
        expect(subSelected(), 'premise: foxtrot is open').toEqual(['foxtrot']);

        await fireEvent.click(tabButton('alpha'));
        expect(subtabs(), 'no group open: no second bar').toBeNull();
        expect(selected(), 'alpha is the active tab').toEqual(['alpha']);
        expect(body()?.tab, 'and its body is drawn').toBe('alpha');

        await fireEvent.click(tabButton('crew'));
        expect(subSelected(), 'a group not open opens on its first visible member, not on the member left last').toEqual(['delta']);
    });

    // red until A8b
    it('SPAGE-10: the open group gets its second bar as soon as the context shows it a second member', async () => {
        await mountPage();
        await fireEvent.click(tabButton('office'));
        expect(subtabs(), 'premise: a user’s office holds omega alone').toBeNull();

        await becomeAdministrator();

        expect(topSelected(), 'office stays selected').toEqual(['office']);
        expect(subIds(), 'its members, for an administrator').toEqual(['omega', 'sigma', 'tau']);
        expect(subSelected(), 'omega stays open').toEqual(['omega']);
        expect(body(), 'with the administrator’s props').toEqual({tab: 'omega', received: {canEdit: true}});
    });
});

describe('Settings page — ?tab= and a group (A8b)', () => {
    // red until A8b
    it.each([
        {query: '?tab=foxtrot', who: 'a user', isSuperuser: false, member: 'foxtrot', groupId: 'crew', members: ['delta', 'foxtrot']},
        {query: '?tab=omega', who: 'a user', isSuperuser: false, member: 'omega', groupId: 'office', members: null},
        {query: '?tab=sigma', who: 'an administrator', isSuperuser: true, member: 'sigma', groupId: 'office', members: ['omega', 'sigma', 'tau']},
    ])('SPAGE-11: $query, for $who, opens that member at the first render — its group selected above, the second bar when the group has two visible members or more', async ({query, isSuperuser, member, groupId, members}) => {
        await mountPage({query, isSuperuser});

        expect(topSelected(), 'the top bar selects the member’s group').toEqual([groupId]);
        expect(subIds(), 'the second bar of its visible members, or none for a group of one').toEqual(members);
        expect(subSelected(), 'the member is selected there, when there is a second bar').toEqual(members ? [member] : []);
        expect(body()?.tab, 'its body is drawn').toBe(member);
        expect(
            mocks.mounts.filter((tab) => tab !== member),
            'no other body was mounted first, not the default and not the group’s first member',
        ).toEqual([]);
    });

    // red until A8b
    it.each([
        {query: '?tab=crew', who: 'a user', isSuperuser: false, groupId: 'crew', member: 'delta'},
        {query: '?tab=crew', who: 'an administrator', isSuperuser: true, groupId: 'crew', member: 'echo'},
        {query: '?tab=office', who: 'a user', isSuperuser: false, groupId: 'office', member: 'omega'},
    ])('SPAGE-12: $query, for $who, opens the group on its first visible member — $member — at the first render', async ({query, isSuperuser, groupId, member}) => {
        await mountPage({query, isSuperuser});

        expect(topSelected(), 'the group is selected').toEqual([groupId]);
        expect(body()?.tab, 'the body of its first visible member is drawn').toBe(member);
        expect(heading(), 'the heading names the member').toBe(marked(synthetic(member).labelKey));
        expect(
            mocks.mounts.filter((tab) => tab !== member),
            'no other body was mounted first',
        ).toEqual([]);
    });

    // red until A8b
    it('SPAGE-13: a later ?tab= naming a member or a group switches to it, and each value is applied once', async () => {
        await mountPage();

        await navigate('?tab=foxtrot');
        expect(topSelected(), 'a member: its group above').toEqual(['crew']);
        expect(subSelected(), 'the member in the second bar').toEqual(['foxtrot']);

        await navigate('?tab=office');
        expect(topSelected(), 'a group: that group').toEqual(['office']);
        expect(body()?.tab, 'on its first visible member').toBe('omega');

        await fireEvent.click(tabButton('alpha'));
        await navigate('?tab=office&from=elsewhere');
        expect(selected(), 'the same ?tab= again: applied already, the tab the user picked stays').toEqual(['alpha']);
        expect(body()?.tab, 'and its body').toBe('alpha');
    });

    // red until A8b
    it('SPAGE-14: ?tab= naming a member this user cannot see waits, and opens it in its group once it appears', async () => {
        await mountPage({query: '?tab=sigma'});
        expect(selected(), 'premise: a user cannot open sigma, so the default tab opens').toEqual(['alpha']);

        await becomeAdministrator();

        expect(topSelected(), 'the member’s group above').toEqual(['office']);
        expect(subIds(), 'its second bar').toEqual(['omega', 'sigma', 'tau']);
        expect(subSelected(), 'the member ?tab= waited for').toEqual(['sigma']);
        expect(body(), 'and its body').toEqual({tab: 'sigma', received: {}});
    });
});

describe('Settings page — badges (A8b)', () => {
    // red until A8b
    it.each([
        {who: 'a user', isSuperuser: false, expected: 3},
        {who: 'an administrator', isSuperuser: true, expected: 103},
    ])('SPAGE-15: an ungrouped tab draws badge(ctx) of the page’s context — beta, for $who: $expected', async ({isSuperuser, expected}) => {
        mocks.badges.beta = 3;
        await mountPage({isSuperuser});

        expect(badgeOf('beta'), 'beta’s badge is its count, a hundred more for an administrator: the page passed its own context').toBe(expected);
    });

    // red until A8b
    it('SPAGE-16: a badge follows what its function reads — nothing for 0, the count that arrives after the first render, nothing again at 0', async () => {
        await mountPage();
        expect(badgeOf('beta'), 'a badge of 0: TabBar draws nothing').toBeNull();

        mocks.badges.beta = 2;
        await tick();
        expect(badgeOf('beta'), 'the count arrived after the first render (as the security checks do, after the prefetch): it is drawn').toBe(2);

        mocks.badges.beta = 0;
        await tick();
        expect(badgeOf('beta'), 'back to 0: nothing is drawn').toBeNull();
    });

    // red until A8b
    it.each([
        {who: 'a user', isSuperuser: false, crew: 2, office: null},
        {who: 'an administrator', isSuperuser: true, crew: 7, office: 4},
    ])('SPAGE-17: a group draws the sum of its visible members’ badges — for $who, crew $crew and office $office: a member this user cannot see adds nothing', async ({isSuperuser, crew, office}) => {
        Object.assign(mocks.badges, {delta: 2, echo: 5, tau: 4});
        await mountPage({isSuperuser});

        expect(badgeOf('crew'), 'delta’s 2, plus echo’s 5 for an administrator only').toBe(crew);
        expect(badgeOf('office'), 'tau’s 4 for an administrator only; omega has no badge, and a sum of 0 draws nothing').toBe(office);
    });

    // red until A8b
    it('SPAGE-18: in the second bar each member draws its own badge', async () => {
        Object.assign(mocks.badges, {delta: 2, echo: 5, tau: 4});
        await mountPage({isSuperuser: true});

        await fireEvent.click(tabButton('crew'));
        expect(subIds(), 'premise: crew’s second bar').toEqual(['echo', 'delta', 'foxtrot']);
        expect(
            ['echo', 'delta', 'foxtrot'].map((id) => badgeOf(id)),
            'echo 5, delta 2, foxtrot none',
        ).toEqual([5, 2, null]);

        await fireEvent.click(tabButton('office'));
        expect(subIds(), 'premise: office’s second bar').toEqual(['omega', 'sigma', 'tau']);
        expect(
            ['omega', 'sigma', 'tau'].map((id) => badgeOf(id)),
            'tau 4, the others none',
        ).toEqual([null, null, 4]);
    });
});

describe('Settings page — prefetch (A8b)', () => {
    // red until A8b
    it.each([
        {who: 'a user', isSuperuser: false, tau: []},
        {who: 'an administrator', isSuperuser: true, tau: [true]},
    ])('SPAGE-19: at the start, for $who, prefetch(ctx) runs once for every visible tab that has one, with the page’s context — never for a tab this user cannot see', async ({isSuperuser, tau}) => {
        await mountPage({isSuperuser});

        expect(prefetched('beta'), 'beta, an ungrouped tab everyone sees: once, with the page’s context').toEqual([isSuperuser]);
        expect(prefetched('tau'), 'tau, a member only an administrator sees: once for an administrator, never for a user').toEqual(tau);
    });

    // red until A8b
    it('SPAGE-20: and again whenever the context changes — becoming an administrator prefetches with the new context, the member that has just appeared included', async () => {
        await mountPage();
        expect(prefetched('beta'), 'premise: beta was prefetched once, for a user').toEqual([false]);
        expect(prefetched('tau'), 'premise: tau was not, a user cannot see it').toEqual([]);

        await becomeAdministrator();

        expect(prefetched('beta'), 'beta again, with the administrator’s context').toEqual([false, true]);
        expect(prefetched('tau'), 'tau, which has just appeared, with it').toEqual([true]);
    });

    // red until A8b
    it('SPAGE-21: nothing else prefetches again — not a change of tab, of group or of ?tab=, nor a change of the state a prefetch reads', async () => {
        await mountPage({isSuperuser: true});
        expect(prefetched('beta'), 'premise: beta was prefetched at the start').toEqual([true]);
        expect(prefetched('tau'), 'premise: and so was tau').toEqual([true]);

        await fireEvent.click(tabButton('crew'));
        await fireEvent.click(tabButton('foxtrot'));
        await fireEvent.click(tabButton('office'));
        await navigate('?tab=gamma');
        // Beta's prefetch reads this count, as the checks' ensureLoaded() reads the state it fills: a prefetch tracked by
        // the page would run again on every change of it, in a loop when the load keeps failing.
        mocks.badges.beta = 6;
        await tick();

        expect(prefetched('beta'), 'still once').toEqual([true]);
        expect(prefetched('tau'), 'still once').toEqual([true]);
    });
});
