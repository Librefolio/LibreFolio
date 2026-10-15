// @vitest-environment jsdom
/**
 * Settings page — the runtime of the tab registry (workstream A, plan A3).
 *
 * The page wrote its four tabs by hand: a `TabId` union and its guard, a list of `{id, icon, labelKey}`,
 * an `{#if}` chain choosing the body, `canEdit={isSuperuser}` on the admin body and an inline
 * `className: 'sm:ml-auto'` on the admin tab. The tabs now live in a registry
 * (`$lib/features/settings/settingsTabs`, pinned by its own `settingsTabs.test.ts`), and the page is
 * rewritten in Svelte 5 runes as its runtime, with the same markup and classes. The approved contract:
 *   - the context is `{isSuperuser: $auth.user?.is_superuser ?? false}`, from `$lib/stores/app/auth`;
 *   - the bar is `visibleSettingsTabs(SETTINGS_TABS, ctx)`: one TabBar tab per visible registry tab, in
 *     registry order (ascending `order`), test id `settings-tab-{id}`, label `$_(labelKey)`, the tab's
 *     icon, labels hidden on a phone (`hideLabelOnMobile`), and `sm:ml-auto` on the button of the tab
 *     with `alignEnd` and on no other;
 *   - the body is the active tab's `component` with `props(ctx)` spread on it, and only that body; the
 *     heading a phone shows names the active tab;
 *   - the active tab is the first visible one, unless `?tab=` (the `page` store of `$app/stores`) names
 *     a visible tab: then that one, already at the first render — the default body is never mounted,
 *     not even for an instant — and again whenever `?tab=` changes. An unknown id, or the id of a tab
 *     this user cannot see, is ignored. A value is applied once: after the user picked another tab, a
 *     page update that keeps the same `?tab=` does not take the tab back (today's `appliedTabParam`);
 *   - a tab with `visible: ctx => ctx.isSuperuser` is absent for a user and appears as soon as the auth
 *     store's user becomes an administrator; a pending `?tab=` naming it is applied then.
 *
 * Held still:
 *   - `settingsTabs` is the real module with `SETTINGS_TABS` replaced (`importOriginal` keeps the real
 *     `visibleSettingsTabs`): the page takes its list from the registry and hands it to the helper, so
 *     the list given here is what it must render. The synthetic tabs are out of order on purpose — the
 *     bar follows `order`, not positions — and two of them stand for the cases the real four will meet:
 *     `staff`, which only an administrator sees (the coming Users and Security tabs), and `omega`, with
 *     `props` and `alignEnd` (admin);
 *   - each synthetic body is `SettingsTabProbe` (`src/__tests__/harness`), told which tab it stands for
 *     and handed the props object the page passed; each call of a body is one mount, logged in `mounts`;
 *   - the real tab modules are no-ops: the real registry imports them, as the page did, and they
 *     reach the API client and the stores, none of which is the subject;
 *   - the `page` store and the auth store are writables the test holds; `$_` marks what it translated,
 *     `⟦key⟧`, so a label is proven to have gone through the translator without naming any language;
 *   - `TabBar` is the real one: what the page hands it is observed as TabBar draws it.
 *
 * Assertions read test ids, `aria-selected`, the probe's attributes, the level-1 heading and two class
 * tokens that are the contract here: `sm:ml-auto`, and `hidden sm:inline` as `TabBar.test.ts` reads it
 * (jsdom loads no Tailwind, so the token is what can be observed).
 *
 * Today the page draws profile, preferences, about and admin by hand and never reads the registry, which
 * does not exist yet: no synthetic tab and no synthetic body is drawn, and every case is red on that.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type Component} from 'svelte';
import type {SettingsTab} from '$lib/features/settings/settingsTabs';

const mocks = await vi.hoisted(async () => {
    const {writable} = await import('svelte/store');
    const {default: SettingsTabProbe} = await import('$test/harness/SettingsTabProbe.svelte');
    const {Info, Shield, Sliders, User, Users} = await import('lucide-svelte');

    /** The synthetic tab of every body mounted, in order: a body never shown has no entry. */
    const mounts: string[] = [];

    /**
     * The body of one synthetic tab: the probe, told which tab it stands for. A Svelte 5 component is a
     * function of an anchor and a props object, so this one mounts the probe in its place, logging the
     * mount and passing the page's own props object on, read through a getter so it stays live.
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

    const tabs: SettingsTab[] = [
        {id: 'gamma', labelKey: 'test.settingsTabs.gamma', icon: Info, order: 30, component: probeBody('gamma')},
        {id: 'alpha', labelKey: 'test.settingsTabs.alpha', icon: User, order: 10, component: probeBody('alpha')},
        {id: 'omega', labelKey: 'test.settingsTabs.omega', icon: Shield, order: 50, component: probeBody('omega'), props: (ctx) => ({canEdit: ctx.isSuperuser}), alignEnd: true},
        {id: 'staff', labelKey: 'test.settingsTabs.staff', icon: Users, order: 40, component: probeBody('staff'), visible: (ctx) => ctx.isSuperuser},
        {id: 'beta', labelKey: 'test.settingsTabs.beta', icon: Sliders, order: 20, component: probeBody('beta')},
    ];

    return {
        tabs,
        mounts,
        page: writable({url: new URL('http://librefolio.test/settings')}),
        auth: writable<{user: {is_superuser: boolean} | null}>({user: {is_superuser: false}}),
        noopComponent: () => {},
    };
});

vi.mock('$lib/features/settings/settingsTabs', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/settings/settingsTabs')>()),
    SETTINGS_TABS: mocks.tabs,
}));
vi.mock('$lib/features/settings/tabs/ProfileTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/PreferencesTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/AboutTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/GlobalSettingsTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/settings/tabs/UsersTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/email/EmailSettingsTab.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/features/backup/BackupTab.svelte', () => ({default: mocks.noopComponent}));
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

/** The bar of a user, left to right: every synthetic tab but `staff`, by ascending order. */
const USER_BAR = ['alpha', 'beta', 'gamma', 'omega'];
/** The bar of an administrator: `staff` too, in its place. */
const ADMIN_BAR = ['alpha', 'beta', 'gamma', 'staff', 'omega'];

/** What the marking translator draws for a key. */
const marked = (key: string): string => `⟦${key}⟧`;

/** The synthetic tab with this id. */
function synthetic(id: string): SettingsTab {
    const tab = mocks.tabs.find((candidate) => candidate.id === id);
    if (!tab) throw new Error(`test bug: no synthetic tab ${id}`);
    return tab;
}

/** The id behind a `settings-tab-{id}` test id. */
function idOf(button: HTMLElement): string {
    return (button.getAttribute('data-testid') ?? '').replace(/^settings-tab-/, '');
}

/** The ids of the bar's tabs, left to right. */
function barIds(): string[] {
    return screen.queryAllByRole('tab').map(idOf);
}

/** The ids of the tabs the bar marks as selected: one, when the page works. */
function selected(): string[] {
    return screen
        .queryAllByRole('tab')
        .filter((button) => button.getAttribute('aria-selected') === 'true')
        .map(idOf);
}

/** The button of the tab with this id: its absence fails here, naming it. */
function tabButton(id: string): HTMLElement {
    const button = screen.queryByTestId(`settings-tab-${id}`);
    expect(button, `the bar has a settings-tab-${id} button (bar: ${barIds().join(', ')})`).not.toBeNull();
    return button as HTMLElement;
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
    // "Never mounted" below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
    mocks.mounts.length = 0;
});

afterEach(() => {
    cleanup();
});

describe('Settings page — the bar and the body come from the registry', () => {
    it('draws one tab per visible registry tab, by ascending order, each with its icon and its label through the translator, hidden on a phone', async () => {
        await mountPage();

        expect(barIds(), 'the bar is visibleSettingsTabs(SETTINGS_TABS, ctx): for a user, every tab but the administrators’, by order').toEqual(USER_BAR);
        for (const id of USER_BAR) {
            const button = tabButton(id);
            const label = within(button).queryByText(marked(synthetic(id).labelKey));
            expect(button.querySelector('svg'), `${id} draws its icon`).not.toBeNull();
            expect(label, `${id} is labelled $_(labelKey)`).not.toBeNull();
            expect(label, `${id}: the label is hidden on a phone, where the heading names the active tab`).toHaveClass('hidden', 'sm:inline');
        }
    });

    it('puts sm:ml-auto on the alignEnd tab alone: it starts the right-hand group on a wide screen', async () => {
        await mountPage();
        expect(barIds(), 'premise: the bar is the user’s').toEqual(USER_BAR);

        expect(
            barIds().filter((id) => tabButton(id).classList.contains('sm:ml-auto')),
            'alignEnd is the only way a tab gets sm:ml-auto',
        ).toEqual(['omega']);
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

        expect(barIds(), '$auth.user?.is_superuser ?? false: no user is no administrator, and no crash').toEqual(USER_BAR);
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

    it.each([
        ['a user', false],
        ['an administrator', true],
    ])('spreads props(ctx) on the body of a tab that has them, for %s', async (_label, isSuperuser) => {
        await mountPage({isSuperuser});

        await fireEvent.click(tabButton('omega'));

        expect(body(), 'the body receives props(ctx), computed on the page’s context').toEqual({tab: 'omega', received: {canEdit: isSuperuser}});
    });

    it('keeps the spread props in step with the auth store while the body is on screen', async () => {
        await mountPage();
        await fireEvent.click(tabButton('omega'));
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

        expect(barIds(), 'premise: the bar is the user’s, without the administrators’ tab').toEqual(USER_BAR);
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
        expect(barIds(), 'a user does not see it').toEqual(USER_BAR);

        await becomeAdministrator();

        expect(barIds(), 'an administrator does, in its order').toEqual(ADMIN_BAR);
        expect(selected(), 'a tab appearing does not take the selection').toEqual(['alpha']);
        expect(body()?.tab, 'the body stays').toBe('alpha');
    });

    it('opens at the first render for an administrator whose ?tab= names it', async () => {
        await mountPage({query: '?tab=staff', isSuperuser: true});

        expect(barIds(), 'premise: the bar is the administrator’s').toEqual(ADMIN_BAR);
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

        expect(barIds(), 'premise: the tab appeared').toEqual(ADMIN_BAR);
        expect(selected(), 'the ?tab= that waited for it is applied now').toEqual(['staff']);
        expect(body(), 'and its body drawn').toEqual({tab: 'staff', received: {}});
    });
});
