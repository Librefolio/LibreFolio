// @vitest-environment jsdom
//
// The docblock above is load-bearing. Under the default `node` environment `$effect` never runs, and every "it showed
// nothing" below would pass on a watcher that never looked (`$test/runes.svelte`). `freshGraph()` runs
// `assertEffectsRun()` before any case relies on an effect.
/**
 * The open-registration warning (accounts lot A7b, C4): an administrator of an instance anyone may register on, who
 * reached it through a host outside the local network, is told so in an instance notice.
 *
 * The contract under test (approved by the coordinator, 16/10 20:30; the keys are the auth subsystem's):
 *   1. `OPEN_REGISTRATION_NOTICE_ID` is `accounts.openRegistration`: an id in the registry, not an i18n key.
 *   2. `openRegistrationNoticeFor({isAdmin, registrationMode, registrationLocked, hostname})` is pure, and null unless
 *      the user is an admin, the mode is `open` and `isLocalHost(hostname)` is false. Then the notice is `{id,
 *      severity: 'warning', dismissible: true, messageKey: 'auth.notices.openRegistration', action: {labelKey:
 *      'auth.notices.openRegistrationAction', href: '/settings?tab=admin'}}` — and, when `LIBREFOLIO_REGISTRATION` pins
 *      the mode (`registrationLocked`), `messageKey: 'auth.notices.openRegistrationLocked'` and no action: nothing in
 *      the app can change a pinned mode.
 *   3. `startOpenRegistrationNotice(deps?)` watches `user()`, `config()` and `hostname()` reactively and, at each
 *      evaluation, calls `notices.show(notice)` when (2) gives a notice and `notices.hide(OPEN_REGISTRATION_NOTICE_ID)`
 *      when it gives null. So it never hides the notice while the warning holds: `hide()` would forget the user's
 *      dismissal and bring the notice back. It returns its stop function, after which nothing is shown or hidden. A
 *      second call is a no-op: no second watcher, and the dependencies it passes are ignored.
 *   4. The defaults are the app's: the auth store's `currentUser` (`is_superuser`), `instanceConfig.config`
 *      (`accounts.registration_mode`, `accounts.registration_locked`), `window.location.hostname` as the browser writes
 *      it (an IPv6 literal in brackets) and `instanceNotices`.
 *   5. The three keys are sentences in en, it, fr and es, and the locked message names `LIBREFOLIO_REGISTRATION` in each
 *      language: the environment variable is the one place where a pinned mode changes.
 *
 * How the cases drive it. Rule 2 is called directly, from the static import. Every case of rules 3 and 4 takes a freshly
 * imported module graph (`vi.resetModules()` + `import()`): "already started" is module-level state, so no case may
 * inherit its neighbour's watcher; and `flushSync`, the rune helpers and the app's stores come from the same graph, so
 * that the watcher's effect tracks the signals the case moves. The world the watcher reads is a `reactiveBox` the case
 * owns — `user`, `config`, `hostname` —, handed over as getters; the registry is a fake that records `show` and `hide`,
 * or the app's own, read through `instanceNotices.list`. A case moves the box, `flushSync()` runs what the move
 * scheduled, then the case reads what the registry was told: no clock. Every watcher a case starts is stopped after it.
 * For the defaults the stores are the real ones of the graph: the auth store signed in and out through its own seam
 * (`checkAuth()` against a programmed `GET /auth/me`, `logout()`), `instanceConfig` answered by a forced `load()` with
 * the case's `fetchConfig`, and jsdom pointed at the page (`jsdom.reconfigure({url})`) so that `window.location` is
 * that page. `$lib/api` is mocked: nothing reaches the network. The auth store's `currentUser` emits the same account
 * again on every update of the store (a `svelte/store` `derived` of an object: `isLoading` going up during a sign-out
 * is one), so a watcher on it evaluates more often than the account changes; the cases on the auth store and on
 * `instanceConfig` therefore read what the registry would list — the fake keeps the notice last shown until it is
 * hidden —, never a count of calls.
 *
 * The cases with the app's registry also guard a trap: `show()` and `hide()` read the registry's own `$state`, so a
 * watcher that calls them tracked, from inside its effect, re-runs on its own write until Svelte stops it
 * (`effect_update_depth_exceeded`). The calls must not be tracked (`untrack`).
 *
 * Not pinned, either way: what the watcher shows before `/system/instance` has answered (`DEFAULT_INSTANCE_CONFIG` is
 * `open`, so an admin of an invite-only instance reached from outside may see the warning until the answer lands);
 * whether a start after `stop()` watches again; what `stop()` does to a notice on show.
 *
 * Red until A7b: `frontend/src/lib/features/auth/openRegistrationNotice.svelte.ts` does not exist yet, the import fails
 * and the whole file is red.
 */
import {afterEach, beforeEach, describe, expect, it, vi, type Mock} from 'vitest';
import type {InstanceConfig} from '$lib/features/instance/instanceConfig.svelte';
import type {InstanceNotice} from '$lib/features/instance/instanceNotices.svelte';
import type {SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';

const api = vi.hoisted(() => ({
    me: vi.fn(),
    logout: vi.fn(),
}));

// `$lib/api`: the two operations of the auth store's seam, and an inert spy for any other a transitive import may touch
// — pending forever, so that nothing it starts (an `instanceConfig.load()` without `fetchConfig`) can settle behind the
// assertions or reach the network. The shape of `ConnectionSecurityIndicator.test.ts`.
vi.mock('$lib/api', () => {
    const programmed: Record<string, unknown> = {
        get_me_api_v1_auth_me_get: api.me,
        logout_api_v1_auth_logout_post: api.logout,
    };
    const inert = new Map<string, unknown>();
    const pending = () => new Promise(() => {});
    const zodiosApi = new Proxy(
        {},
        {
            get(_target, operation) {
                if (typeof operation !== 'string' || operation === 'then') return undefined;
                if (operation in programmed) return programmed[operation];
                if (!inert.has(operation)) inert.set(operation, vi.fn(pending));
                return inert.get(operation);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

import {OPEN_REGISTRATION_NOTICE_ID, openRegistrationNoticeFor} from './openRegistrationNotice.svelte';

// --- The contract's literals, never read from the module under test --------------------------------------------------

const NOTICE_ID = 'accounts.openRegistration';

/** The warning: an admin, an instance open to registration, a host outside the local network. */
const OPEN_NOTICE: InstanceNotice = {
    id: NOTICE_ID,
    severity: 'warning',
    dismissible: true,
    messageKey: 'auth.notices.openRegistration',
    action: {labelKey: 'auth.notices.openRegistrationAction', href: '/settings?tab=admin'},
};

/** The same with the mode pinned by `LIBREFOLIO_REGISTRATION`: no link to a setting nothing in the app can change. */
const LOCKED_NOTICE: InstanceNotice = {
    id: NOTICE_ID,
    severity: 'warning',
    dismissible: true,
    messageKey: 'auth.notices.openRegistrationLocked',
};

const NOTICE_KEYS = ['auth.notices.openRegistration', 'auth.notices.openRegistrationLocked', 'auth.notices.openRegistrationAction'];

type Mode = 'open' | 'invite' | 'disabled';
const MODES: Mode[] = ['open', 'invite', 'disabled'];

/** A public configuration in `mode`, pinned by `LIBREFOLIO_REGISTRATION` when `locked`. */
function config(mode: Mode, locked = false): InstanceConfig {
    return {profile: 'selfhosted', accounts: {registration_mode: mode, registration_locked: locked}};
}

/** A host outside the local network, and one inside it. */
const EXTERNAL_HOST = 'librefolio.example.com';
const LOCAL_HOST = '192.168.1.10';

/** The user, as the watcher reads it. */
type WatchedUser = {is_superuser: boolean} | null;
const admin = (): WatchedUser => ({is_superuser: true});
const member = (): WatchedUser => ({is_superuser: false});

/** An account, as `GET /auth/me` answers it. */
function account(id: number, isSuperuser: boolean) {
    return {id, username: `user-${id}`, email: `user-${id}@example.com`, is_active: true, is_superuser: isSuperuser, created_at: '2026-10-16T00:00:00Z'};
}

const ADMIN_ACCOUNT = account(1, true);
const MEMBER_ACCOUNT = account(2, false);

// --- Rule 2: the truth table -----------------------------------------------------------------------------------------

interface NoticeState {
    isAdmin: boolean;
    registrationMode: string;
    registrationLocked: boolean;
    hostname: string;
}

/** Every combination of the four inputs, each labelled. */
function everyState(): Array<[label: string, state: NoticeState]> {
    const states: Array<[label: string, state: NoticeState]> = [];
    for (const isAdmin of [true, false]) {
        for (const registrationMode of MODES) {
            for (const registrationLocked of [false, true]) {
                for (const hostname of [EXTERNAL_HOST, LOCAL_HOST]) {
                    const label = `${isAdmin ? 'an admin' : 'not an admin'} · ${registrationMode}${registrationLocked ? ', pinned' : ''} · ${hostname === EXTERNAL_HOST ? 'an external' : 'a local'} host (${hostname})`;
                    states.push([label, {isAdmin, registrationMode, registrationLocked, hostname}]);
                }
            }
        }
    }
    return states;
}

/** All but the two that warn: an admin, `open`, an external host, pinned or not. */
const SILENT_STATES = everyState().filter(([, state]) => !(state.isAdmin && state.registrationMode === 'open' && state.hostname === EXTERNAL_HOST));

/** Hosts judged through `isLocalHost`, as the browser writes them. */
const LOCAL_HOSTS: Array<[host: string, why: string]> = [
    ['localhost', 'the loopback name'],
    ['127.0.0.1', 'the IPv4 loopback'],
    ['[::1]', 'the IPv6 loopback, in the brackets location.hostname keeps'],
    ['10.0.0.5', 'a private address'],
    ['100.101.102.103', 'a Tailscale address'],
    ['[fd7a:115c:a1e0::1]', 'a Tailscale IPv6 address'],
    ['nas', 'a single-label name'],
    ['nas.local', 'an mDNS name'],
];

const EXTERNAL_HOSTS: Array<[host: string, why: string]> = [
    ['librefolio.example.com', 'a public name'],
    ['nas.tail1234.ts.net', 'a Tailscale name, which Funnel can publish'],
    ['203.0.113.7', 'a public address'],
    ['[2001:db8::1]', 'a public IPv6 address'],
];

describe('OPEN_REGISTRATION_NOTICE_ID', () => {
    // red until A7b
    it('is accounts.openRegistration: an id in the registry, not an i18n key', () => {
        expect(OPEN_REGISTRATION_NOTICE_ID).toBe(NOTICE_ID);
    });
});

describe('openRegistrationNoticeFor — the truth table', () => {
    // red until A7b
    it('an admin · open · an external host: the warning, with the link to the setting', () => {
        expect(openRegistrationNoticeFor({isAdmin: true, registrationMode: 'open', registrationLocked: false, hostname: EXTERNAL_HOST})).toEqual(OPEN_NOTICE);
    });

    // red until A7b
    it('an admin · open, pinned by LIBREFOLIO_REGISTRATION · an external host: the locked message, and no action', () => {
        const notice = openRegistrationNoticeFor({isAdmin: true, registrationMode: 'open', registrationLocked: true, hostname: EXTERNAL_HOST});

        expect(notice).toEqual(LOCKED_NOTICE);
        expect(notice?.action, 'nothing in the app can change a pinned mode: no link to a setting that would refuse').toBeUndefined();
    });

    // red until A7b
    it.each(SILENT_STATES)('no notice: %s', (_label, state) => {
        expect(openRegistrationNoticeFor(state)).toBeNull();
    });

    // red until A7b
    it.each(LOCAL_HOSTS)('an admin of an open instance reached through %s (%s): no notice', (hostname) => {
        expect(openRegistrationNoticeFor({isAdmin: true, registrationMode: 'open', registrationLocked: false, hostname})).toBeNull();
    });

    // red until A7b
    it.each(EXTERNAL_HOSTS)('an admin of an open instance reached through %s (%s): the warning', (hostname) => {
        expect(openRegistrationNoticeFor({isAdmin: true, registrationMode: 'open', registrationLocked: false, hostname})).toEqual(OPEN_NOTICE);
    });
});

// --- Rules 3 and 4: the watcher --------------------------------------------------------------------------------------

/** The dependencies of the contract, every one optional. */
interface WatcherDeps {
    user?: () => WatchedUser;
    config?: () => InstanceConfig;
    hostname?: () => string;
    notices?: {show(notice: InstanceNotice): void; hide(id: string): void};
}

/** A registry that records what it is told. */
interface Registry {
    show: Mock<(notice: InstanceNotice) => void>;
    hide: Mock<(id: string) => void>;
}

/** A fake registry, which also keeps what it would list. */
interface FakeRegistry extends Registry {
    /** The notice last shown, until it is hidden: what the app would list now. */
    listed(): InstanceNotice | null;
}

/** What a watcher reads, as reactive state the case owns. */
interface World {
    user: WatchedUser;
    config: InstanceConfig;
    hostname: string;
}

/** The JSDOM instance vitest exposes in this environment: its URL is the page's `window.location`. */
const dom = (globalThis as unknown as {jsdom: {reconfigure(settings: {url: string}): void}}).jsdom;
const INITIAL_URL = window.location.href;

/** A page load at `url`: `window.location` now reads it. Before `freshGraph()`, so that even a module that read the host at import would read this one. */
function loadPageAt(url: string): void {
    dom.reconfigure({url});
    expect(window.location.href, 'premise: jsdom serves the page at this address').toBe(new URL(url).href);
}

/** The module of a page load that has just begun, with `flushSync`, the rune helpers and the app's stores of the same module graph. */
async function freshGraph() {
    vi.resetModules();
    const notice = await import('./openRegistrationNotice.svelte');
    const runes = await import('$test/runes.svelte');
    const {flushSync} = await import('svelte');
    const {auth} = await import('$lib/stores/app/auth');
    const {instanceConfig} = await import('$lib/features/instance/instanceConfig.svelte');
    const {instanceNotices} = await import('$lib/features/instance/instanceNotices.svelte');
    runes.assertEffectsRun();
    return {...notice, ...runes, flushSync, auth, instanceConfig, instanceNotices};
}

type Graph = Awaited<ReturnType<typeof freshGraph>>;

/** The stop functions of the watchers the current case started; each runs once after the case, whatever its outcome. */
let watchers: Array<() => void> = [];

/** Starts the graph's watcher — without arguments when `deps` is absent, as the app does — and returns its stop function, which works once. */
function start(graph: Graph, deps?: WatcherDeps): () => void {
    const stop = deps === undefined ? graph.startOpenRegistrationNotice() : graph.startOpenRegistrationNotice(deps);
    expect(stop, 'startOpenRegistrationNotice returns its stop function').toBeTypeOf('function');
    let stopped = false;
    const once = (): void => {
        if (stopped) return;
        stopped = true;
        stop();
    };
    watchers.push(once);
    return once;
}

/** The world that warns — an admin, an open instance, an external host —, changed by `initial`. */
function world(graph: Graph, initial: Partial<World> = {}): World {
    return graph.reactiveBox<World>({user: admin(), config: config('open'), hostname: EXTERNAL_HOST, ...initial});
}

function fakeNotices(): FakeRegistry {
    let listed: InstanceNotice | null = null;
    const show = (notice: InstanceNotice): void => {
        listed = notice;
    };
    const hide = (id: string): void => {
        if (listed?.id === id) listed = null;
    };
    return {show: vi.fn(show).mockName('notices.show'), hide: vi.fn(hide).mockName('notices.hide'), listed: () => listed};
}

/** The app's registry of the graph, each call recorded. */
function recordedRegistry(graph: Graph): Registry {
    return {
        show: vi.fn((notice: InstanceNotice) => graph.instanceNotices.show(notice)).mockName('instanceNotices.show'),
        hide: vi.fn((id: string) => graph.instanceNotices.hide(id)).mockName('instanceNotices.hide'),
    };
}

/** Every dependency injected: the watcher reads `state` and tells `notices`. */
function injected(state: World, notices: Registry): WatcherDeps {
    return {user: () => state.user, config: () => state.config, hostname: () => state.hostname, notices};
}

/** What the app's registry lists under the notice's id. */
function registered(graph: Graph): InstanceNotice[] {
    return graph.instanceNotices.list.filter((listed) => listed.id === NOTICE_ID);
}

/** Signs `signedIn` in through the auth store's own seam: `checkAuth()` against a programmed `GET /auth/me`. */
async function signIn(graph: Graph, signedIn: ReturnType<typeof account>): Promise<void> {
    api.me.mockResolvedValueOnce({user: signedIn});
    expect(await graph.auth.checkAuth(), 'premise: the auth store signed the account in').toBe('authenticated');
}

beforeEach(() => {
    api.me.mockReset();
    api.logout.mockReset();
    api.logout.mockResolvedValue(undefined);
});

afterEach(() => {
    const started = watchers;
    watchers = [];
    for (const stop of started) stop();
    dom.reconfigure({url: INITIAL_URL});
});

/** A start with nothing to warn about, and what makes it so. */
const NOTHING_TO_WARN: Array<[label: string, initial: Partial<World>]> = [
    ['not an admin', {user: member()}],
    ['nobody signed in', {user: null}],
    ['an invite-only instance', {config: config('invite')}],
    ['a closed instance', {config: config('disabled')}],
    ['a local host', {hostname: LOCAL_HOST}],
];

/** The admin leaving: the user the watcher reads next. */
const ADMIN_LEAVES: Array<[label: string, next: WatchedUser]> = [
    ['the sign-out', null],
    ['a switch to an account that is not an admin', member()],
];

describe('startOpenRegistrationNotice — the watcher', () => {
    // red until A7b
    it('shows the warning once for an admin of an open instance reached from outside, and hides nothing', async () => {
        const graph = await freshGraph();
        const notices = fakeNotices();

        start(graph, injected(world(graph), notices));
        graph.flushSync();

        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show).toHaveBeenCalledWith(OPEN_NOTICE);
        expect(notices.hide, 'nothing to hide while the warning holds').not.toHaveBeenCalled();
    });

    // red until A7b
    it('with the mode pinned by LIBREFOLIO_REGISTRATION: the locked message, and no action', async () => {
        const graph = await freshGraph();
        const notices = fakeNotices();

        start(graph, injected(world(graph, {config: config('open', true)}), notices));
        graph.flushSync();

        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show).toHaveBeenCalledWith(LOCKED_NOTICE);
        expect(notices.show.mock.calls[0][0].action, 'a pinned mode: no link to the setting').toBeUndefined();
    });

    // red until A7b
    it.each(NOTHING_TO_WARN)('nothing to warn about at the start (%s): it hides the notice, and never shows it', async (_label, initial) => {
        const graph = await freshGraph();
        const notices = fakeNotices();

        start(graph, injected(world(graph, initial), notices));
        graph.flushSync();

        expect(notices.hide, 'evaluated, and found nothing to warn about').toHaveBeenCalledWith(NOTICE_ID);
        expect(notices.show).not.toHaveBeenCalled();
    });

    // red until A7b
    it.each(['invite', 'disabled'] as const)('the mode leaving open (%s) hides it', async (mode) => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = fakeNotices();
        start(graph, injected(state, notices));
        graph.flushSync();
        expect(notices.show, 'premise: the warning is shown').toHaveBeenCalledTimes(1);

        state.config = config(mode);
        graph.flushSync();

        expect(notices.hide).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE_ID);
        expect(notices.show, 'shown once, at the start').toHaveBeenCalledTimes(1);
    });

    // red until A7b
    it.each(ADMIN_LEAVES)('%s hides it', async (_label, next) => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = fakeNotices();
        start(graph, injected(state, notices));
        graph.flushSync();
        expect(notices.show, 'premise: the warning is shown').toHaveBeenCalledTimes(1);

        state.user = next;
        graph.flushSync();

        expect(notices.hide).toHaveBeenCalledTimes(1);
        expect(notices.hide).toHaveBeenCalledWith(NOTICE_ID);
        expect(notices.show).toHaveBeenCalledTimes(1);
    });

    // red until A7b
    it('an admin signing in after the start is warned: the watcher outlives a sign-out', async () => {
        const graph = await freshGraph();
        const state = world(graph, {user: null});
        const notices = fakeNotices();
        start(graph, injected(state, notices));
        graph.flushSync();
        expect(notices.show, 'premise: nobody to warn yet').not.toHaveBeenCalled();

        state.user = admin();
        graph.flushSync();

        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show).toHaveBeenCalledWith(OPEN_NOTICE);
    });

    // red until A7b
    it('never hides the notice while the warning holds: the user’s dismissal survives every evaluation', async () => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = recordedRegistry(graph);
        start(graph, injected(state, notices));
        graph.flushSync();
        expect(registered(graph), 'premise: the warning is listed').toEqual([OPEN_NOTICE]);
        graph.instanceNotices.dismiss(NOTICE_ID);
        expect(registered(graph), 'premise: the user closed it').toEqual([]);

        state.config = config('open'); // the server answered again, the same
        state.user = admin(); // the session was checked again: the same admin
        graph.flushSync();

        expect(notices.hide, 'a hide() while the warning holds forgets the dismissal and brings the notice back').not.toHaveBeenCalled();
        expect(registered(graph), 'closed by the user, it stays closed until the next page load').toEqual([]);
    });

    // red until A7b
    it('two starts, one watcher: one show or one hide per change', async () => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = fakeNotices();
        const deps = injected(state, notices);

        start(graph, deps);
        expect(graph.startOpenRegistrationNotice(deps), 'a second call still returns a stop function').toBeTypeOf('function');
        graph.flushSync();
        expect(notices.show, 'the start').toHaveBeenCalledTimes(1);

        state.config = config('invite');
        graph.flushSync();
        expect(notices.hide, 'the mode leaves open').toHaveBeenCalledTimes(1);

        state.config = config('open');
        graph.flushSync();
        expect(notices.show, 'open again').toHaveBeenCalledTimes(2);

        state.user = null;
        graph.flushSync();
        expect(notices.hide, 'the sign-out').toHaveBeenCalledTimes(2);
    });

    // red until A7b
    it('a second start changes nothing: the watcher keeps the dependencies of the first, and the second’s are ignored', async () => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = fakeNotices();
        const otherState = world(graph, {user: null});
        const otherNotices = fakeNotices();

        start(graph, injected(state, notices));
        graph.startOpenRegistrationNotice(injected(otherState, otherNotices));
        graph.flushSync();
        expect(notices.show, 'the first watcher warns').toHaveBeenCalledTimes(1);

        state.user = null;
        otherState.user = admin();
        graph.flushSync();

        expect(notices.hide, 'and follows its own world').toHaveBeenCalledTimes(1);
        expect(otherNotices.show, 'the second call started nothing').not.toHaveBeenCalled();
        expect(otherNotices.hide).not.toHaveBeenCalled();
    });

    // red until A7b
    it('its stop function ends the watching: after it, no change shows or hides anything', async () => {
        const graph = await freshGraph();
        const state = world(graph);
        const notices = fakeNotices();
        const stop = start(graph, injected(state, notices));
        graph.flushSync();
        state.config = config('invite');
        graph.flushSync();
        expect(notices.hide, 'premise: the watcher follows a change').toHaveBeenCalledTimes(1);

        stop();
        notices.show.mockClear();
        notices.hide.mockClear();
        state.config = config('open');
        graph.flushSync();
        state.user = null;
        graph.flushSync();

        expect(notices.show, 'stopped: nothing shown').not.toHaveBeenCalled();
        expect(notices.hide, 'stopped: nothing hidden').not.toHaveBeenCalled();
    });
});

/** The pages of a page load, by the host the browser was pointed at. */
const WARNING_PAGES: Array<[url: string, why: string]> = [
    ['https://librefolio.example.com/dashboard', 'a public name'],
    ['https://nas.tail1234.ts.net/', 'a Tailscale name, which Funnel can publish'],
];

const SILENT_PAGES: Array<[url: string, why: string]> = [
    ['http://localhost:5173/', 'localhost'],
    ['http://192.168.1.10:8000/dashboard', 'a private address'],
    ['http://[::1]:8000/', 'the IPv6 loopback, which location.hostname keeps in brackets'],
    ['http://nas.local/', 'an mDNS name'],
];

describe('startOpenRegistrationNotice — the defaults are the app’s', () => {
    // red until A7b
    it('without user, it follows the account the auth store signs in: an admin is warned, the sign-out hides it, a member is never warned, an admin again is', async () => {
        const graph = await freshGraph();
        const state = graph.reactiveBox<{config: InstanceConfig; hostname: string}>({config: config('open'), hostname: EXTERNAL_HOST});
        const notices = fakeNotices();
        await signIn(graph, ADMIN_ACCOUNT);

        start(graph, {config: () => state.config, hostname: () => state.hostname, notices});
        graph.flushSync();
        expect(notices.listed(), 'the admin signed in').toEqual(OPEN_NOTICE);

        await graph.auth.logout();
        graph.flushSync();
        expect(notices.listed(), 'the sign-out empties currentUser: the warning goes').toBeNull();

        notices.show.mockClear();
        await signIn(graph, MEMBER_ACCOUNT);
        graph.flushSync();
        expect(notices.show, 'a member is never warned').not.toHaveBeenCalled();

        await signIn(graph, ADMIN_ACCOUNT);
        graph.flushSync();
        expect(notices.listed(), 'the admin who signs in again is warned again, by the same watcher').toEqual(OPEN_NOTICE);
    });

    // red until A7b
    it('without config, it follows instanceConfig: each answer of the server', async () => {
        const graph = await freshGraph();
        await graph.instanceConfig.load({force: true, fetchConfig: async () => config('open')});
        const state = graph.reactiveBox<{user: WatchedUser; hostname: string}>({user: admin(), hostname: EXTERNAL_HOST});
        const notices = fakeNotices();

        start(graph, {user: () => state.user, hostname: () => state.hostname, notices});
        graph.flushSync();
        expect(notices.listed(), 'the server answered open').toEqual(OPEN_NOTICE);

        await graph.instanceConfig.load({force: true, fetchConfig: async () => config('invite')});
        graph.flushSync();
        expect(notices.listed(), 'the server now answers invite').toBeNull();

        await graph.instanceConfig.load({force: true, fetchConfig: async () => config('open', true)});
        graph.flushSync();
        expect(notices.listed(), 'open again, now pinned by LIBREFOLIO_REGISTRATION').toEqual(LOCKED_NOTICE);
    });

    // red until A7b
    it.each(WARNING_PAGES)('without hostname, it reads the host of the page: %s (%s) is warned about', async (url) => {
        loadPageAt(url);
        const graph = await freshGraph();
        const state = graph.reactiveBox<{user: WatchedUser; config: InstanceConfig}>({user: admin(), config: config('open')});
        const notices = fakeNotices();

        start(graph, {user: () => state.user, config: () => state.config, notices});
        graph.flushSync();

        expect(notices.show).toHaveBeenCalledTimes(1);
        expect(notices.show).toHaveBeenCalledWith(OPEN_NOTICE);
    });

    // red until A7b
    it.each(SILENT_PAGES)('without hostname, it reads the host of the page: %s (%s) is not warned about', async (url) => {
        loadPageAt(url);
        const graph = await freshGraph();
        const state = graph.reactiveBox<{user: WatchedUser; config: InstanceConfig}>({user: admin(), config: config('open')});
        const notices = fakeNotices();

        start(graph, {user: () => state.user, config: () => state.config, notices});
        graph.flushSync();

        expect(notices.hide, 'evaluated, and found the host local').toHaveBeenCalledWith(NOTICE_ID);
        expect(notices.show).not.toHaveBeenCalled();
    });

    // red until A7b
    it('start() without arguments, as the app bootstrap calls it: the warning in the app’s registry, gone with the sign-out, back with the next sign-in', async () => {
        loadPageAt('https://librefolio.example.com/dashboard');
        const graph = await freshGraph();
        await graph.instanceConfig.load({force: true, fetchConfig: async () => config('open')});
        await signIn(graph, ADMIN_ACCOUNT);

        start(graph);
        graph.flushSync();
        expect(registered(graph), 'an admin, an open instance, a public host').toEqual([OPEN_NOTICE]);

        await graph.auth.logout();
        graph.flushSync();
        expect(registered(graph), 'signed out: no warning').toEqual([]);

        await signIn(graph, ADMIN_ACCOUNT);
        graph.flushSync();
        expect(registered(graph), 'the same watcher warns the admin who signs in again').toEqual([OPEN_NOTICE]);
    });
});

// --- Rule 5: the keys ------------------------------------------------------------------------------------------------

describe('the keys of the notice — sentences in all four catalogues', () => {
    const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

    /** The leaf behind a dotted key, read from the catalogue file itself. */
    function leaf(catalogue: unknown, key: string): unknown {
        return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    }

    // red until A7b
    it.each(NOTICE_KEYS)('%s is a sentence in en, it, fr and es', (key) => {
        const missing = Object.entries(CATALOGUES)
            .filter(([, catalogue]) => {
                const sentence = leaf(catalogue, key);
                return typeof sentence !== 'string' || sentence.trim() === '';
            })
            .map(([locale]) => locale);

        expect(missing, `${key} is drawn as the key itself in a catalogue that lacks it`).toEqual([]);
    });

    // red until A7b
    it('the locked message names LIBREFOLIO_REGISTRATION in every language: the one place where a pinned mode changes', () => {
        const silent = Object.entries(CATALOGUES)
            .filter(([, catalogue]) => {
                const sentence = leaf(catalogue, LOCKED_NOTICE.messageKey);
                return typeof sentence !== 'string' || !sentence.includes('LIBREFOLIO_REGISTRATION');
            })
            .map(([locale]) => locale);

        expect(silent).toEqual([]);
    });
});
