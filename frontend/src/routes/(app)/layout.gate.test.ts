// @vitest-environment jsdom
/**
 * `(app)` layout — two behaviours of workstream J: the onboarding route gate follows the bootstrap
 * when it settles, and a client-side route change restores the default window title.
 *
 * The gate. The layout is a legacy component, and it reads `appBootstrap` in two ways that do not react
 * alike. Its template tracks it: the compiler wraps each `{#if}` condition in
 * `$.deep_read_state(appBootstrap)`, which calls the object's enumerable getters inside the
 * block's effect. Its `$:` statements do not: a `$:` re-runs only on the identifiers it names,
 * and an imported object is not a signal. Before the fix, `onboardingDestination` and
 * `onboardingRouteReady` read `appBootstrap.ready` directly, so when `ready` flipped the template
 * left `app-bootstrap-loading` while `onboardingRouteReady` kept the `true` it had computed during
 * loading, and the requested page's `app-shell` painted until the owned settlement's redirect
 * landed (measured live: `onboarding-redirecting` mounted in 0 of 40 runs). The fix reads `ready`
 * through `toStore`, and `$bootstrapReady` is a dependency a `$:` does track.
 *
 * The window title (user-reported, also in v1.1.0). Svelte 5 applies a page's
 * `<svelte:head><title>` by assigning `document.title` in an effect, and never restores it when
 * the page unmounts. Only Files and Tools set a title of their own, so after Files every page
 * without one kept "Files - LibreFolio". The layout resets the title to the app.html default in
 * an `onNavigate` callback: SvelteKit runs those after load and before `root.$set` mounts the
 * next page, so a page with a title of its own sets it again on mount (a reset in `afterNavigate`
 * would clobber it). A same-route navigation — a query change, another `tool_code` — remounts
 * nothing that would set the title again, so it must reset nothing. The specs invoke the
 * registered callback the way the router does, with an `OnNavigate` object, and read the default
 * from `src/app.html` instead of importing it from the layout, so the two cannot drift apart
 * unnoticed. Bug and fix exist only on client-side navigation (a full load re-reads app.html):
 * the browser half, mount ordering included, is `e2e/layout/document-title.spec.ts`.
 *
 * Only the gate and the title reset are under test, so everything around them is held still:
 *   - `appBootstrap` is a fake with the real object's shape, enumerable getters over `$state`
 *     (`reactiveBox`), which is exactly what `deep_read_state` reads. The spec flips its state and
 *     flushes with `tick()`; `resolveDestination` is scripted per test.
 *   - `$app/environment` reports `browser: false`. The gate reads nothing from it, and it keeps
 *     both navigation paths inert: `onMount`'s auth race (a real 5 s timer) and the owned
 *     settlement never start, and the reactive redirect `$:` is guarded by `browser`. `goto` and
 *     the settlement are mocks too, and every gate test asserts that neither ran, so a branch
 *     change can only have come from the template gate.
 *   - `onNavigate` from `$app/navigation` is a spy that records the callback the layout registers
 *     at init. The title specs assert that exactly one was registered before they invoke it, so
 *     neither can pass because nothing ran.
 *   - every child component is a no-op, and every store or API the layout touches is a stub. None
 *     of them is the subject, and each would otherwise start network, storage or observer work.
 *
 * Assertions read `data-testid` only: the stubbed `$_` returns keys, and nothing reads text.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {tick} from 'svelte';
import type {NavigationTarget, OnNavigate} from '@sveltejs/kit';
import type {AppBootstrapState} from '$lib/features/onboarding/appBootstrap.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    return {
        bootstrap: reactiveBox<{state: AppBootstrapState}>({state: 'loading'}),
        resolveDestination: vi.fn<(path: string) => string>(),
        goto: vi.fn(() => Promise.resolve()),
        // Records the callback the layout registers at init; the title specs invoke it as the router would.
        onNavigate: vi.fn<(callback: (navigation: OnNavigate) => unknown) => void>(),
        // Never settles: were it ever started, it still could not navigate behind the assertions.
        runOwnedSettlement: vi.fn(() => new Promise<void>(() => {})),
        noopComponent: () => {},
    };
});

vi.mock('$app/environment', () => ({browser: false, dev: true, building: false, version: 'test'}));
vi.mock('$app/navigation', () => ({goto: mocks.goto, afterNavigate: vi.fn(), onNavigate: mocks.onNavigate, preloadCode: vi.fn(() => Promise.resolve())}));
vi.mock('$app/stores', async () => {
    const {readable} = await import('svelte/store');
    return {page: readable({route: {id: '/(app)/dashboard'}, url: new URL('http://librefolio.test/dashboard')})};
});
vi.mock('$lib/i18n', async () => {
    const {readable} = await import('svelte/store');
    return {_: readable((key: string) => key), i18nLoading: readable(false), initI18n: vi.fn()};
});
vi.mock('$lib/stores/app/auth', async () => {
    const {readable} = await import('svelte/store');
    return {
        auth: {checkAuth: vi.fn(() => new Promise<boolean>(() => {})), logout: vi.fn(() => Promise.resolve())},
        isAuthenticated: readable(true),
        isAuthInitialized: readable(true),
    };
});
// ⚠️ Fragile by construction: this fake must keep the real `appBootstrap`'s SHAPE — a plain object
// whose state is exposed through enumerable getters over `$state` (`reactiveBox`). A legacy template
// tracks it only through `$.deep_read_state`, a `for…in` over those getters. If production turns
// `appBootstrap` into a class instance (prototype getters) or a Proxy, this fake stops mirroring how
// the real object is tracked, and the test can pass or fail for a reason that is not the gate:
// change the fake with the object, and re-run the negative control (pre-fix `$:` lines → red).
vi.mock('$lib/features/onboarding/appBootstrap.svelte', () => ({
    appBootstrap: {
        get state() {
            return mocks.bootstrap.state;
        },
        get error() {
            return null;
        },
        get loadedUserId() {
            return 'gate-user';
        },
        get ready() {
            return mocks.bootstrap.state === 'ready' || mocks.bootstrap.state === 'degraded';
        },
        load: vi.fn(() => new Promise<AppBootstrapState>(() => {})),
        resolveDestination: mocks.resolveDestination,
        reset: vi.fn(),
    },
}));
vi.mock('$lib/features/onboarding/onboardingRouteSettlement', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/features/onboarding/onboardingRouteSettlement')>()),
    runOwnedOnboardingRouteSettlement: mocks.runOwnedSettlement,
}));
vi.mock('$lib/features/onboarding/onboardingGuide.svelte', () => ({onboardingGuide: {active: null, maybeStartIntro: vi.fn()}}));
vi.mock('$lib/stores/app/navigationStore', () => ({trackNavigation: vi.fn()}));
vi.mock('$lib/stores/dateRangeStore.svelte', () => ({seedFromUrl: vi.fn()}));
vi.mock('$lib/stores/app/language', () => ({currentLanguage: {init: vi.fn()}}));
vi.mock('$lib/debug', () => ({debug: {log: vi.fn(), warn: vi.fn(), error: vi.fn(), info: vi.fn()}, isDebugEnabled: () => false}));
vi.mock('$lib/utils/storage', () => ({getUserStorage: vi.fn(() => 'false')}));
vi.mock('$lib/stores/app/donationPopupStore.svelte', () => ({donationPopup: {forceShow: vi.fn()}}));
vi.mock('$lib/features/update-check/updateCheckStore.svelte', () => ({updateAvailable: {show: vi.fn()}}));
vi.mock('$lib/features/update-check/updateCheck', () => ({checkForNewerRelease: vi.fn(() => Promise.resolve(null))}));
vi.mock('$lib/api', () => ({zodiosApi: {get_system_info_api_v1_system_info_get: vi.fn(() => new Promise(() => {}))}}));
vi.mock('$lib/components/layout/Sidebar.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/layout/Header.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/ui/feedback/ToastContainer.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/onboarding/OnboardingBootstrapBlock.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/onboarding/OnboardingBootstrapBanner.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/onboarding/OnboardingOverlayHost.svelte', () => ({default: mocks.noopComponent}));
vi.mock('$lib/components/onboarding/DeferredAppPopups.svelte', () => ({default: mocks.noopComponent}));

import {cleanup, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import AppLayoutGateHarness from '$test/harness/AppLayoutGateHarness.svelte';

const REQUESTED_PATH = '/dashboard';
const WELCOME_REDIRECT = '/welcome?returnTo=%2Fdashboard';

/** Mount at `/dashboard` while the bootstrap is still loading, and prove the gate is holding. */
async function mountWhileLoading(): Promise<void> {
    render(AppLayoutGateHarness);
    await tick();
    expect(screen.getByTestId('app-bootstrap-loading')).toBeInTheDocument();
    expect(screen.queryByTestId('app-shell')).toBeNull();
    // Not ready yet: the gate has not asked where to go, it holds the requested path.
    expect(mocks.resolveDestination).not.toHaveBeenCalled();
}

/** Settle the bootstrap the way `load()` does, then flush: a flush, not a clock wait. */
async function settleBootstrap(): Promise<void> {
    mocks.bootstrap.state = 'ready';
    await tick();
}

/** Isolation: nothing navigated, so whatever the DOM shows was chosen by the template gate. */
function expectNothingNavigated(): void {
    expect(mocks.goto).not.toHaveBeenCalled();
    expect(mocks.runOwnedSettlement).not.toHaveBeenCalled();
}

beforeEach(() => {
    // Negative assertions below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
    mocks.bootstrap.state = 'loading';
    mocks.resolveDestination.mockReset();
    mocks.goto.mockClear();
    mocks.onNavigate.mockClear();
    mocks.runOwnedSettlement.mockClear();
});

afterEach(() => {
    cleanup();
});

describe('(app) layout route gate — the bootstrap settling re-runs the gate (workstream J)', () => {
    it('shows onboarding-redirecting, not the requested page, when the settled bootstrap resolves a redirect', async () => {
        mocks.resolveDestination.mockImplementation((path) => (path === REQUESTED_PATH ? WELCOME_REDIRECT : path));
        await mountWhileLoading();

        await settleBootstrap();

        expect(screen.queryByTestId('app-shell'), 'the requested page shell painted while a redirect is due').toBeNull();
        expect(screen.getByTestId('onboarding-redirecting')).toBeInTheDocument();
        expect(screen.queryByTestId('app-bootstrap-loading')).toBeNull();
        expect(screen.queryByTestId('app-layout-requested-page')).toBeNull();
        expect(mocks.resolveDestination).toHaveBeenCalledWith(REQUESTED_PATH);
        expectNothingNavigated();
    });

    it('control: paints the requested page when the settled bootstrap resolves the same path', async () => {
        mocks.resolveDestination.mockImplementation((path) => path);
        await mountWhileLoading();

        await settleBootstrap();

        expect(screen.queryByTestId('onboarding-redirecting')).toBeNull();
        expect(screen.queryByTestId('app-bootstrap-loading')).toBeNull();
        const shell = screen.getByTestId('app-shell');
        expect(within(shell).getByTestId('app-layout-requested-page')).toBeInTheDocument();
        // The page is let through because the gate asked and got the same path back, not because it never re-ran.
        expect(mocks.resolveDestination).toHaveBeenCalledWith(REQUESTED_PATH);
        expectNothingNavigated();
    });
});

// ---------------------------------------------------------------------------
// Document title — a client-side route change restores the app.html default
// ---------------------------------------------------------------------------

type OnNavigateCallback = (navigation: OnNavigate) => unknown;
type RouteId = NonNullable<NavigationTarget['route']['id']>;

/** What the Files page leaves behind: `{$t('uploads.title')} - LibreFolio`, through a key-returning i18n like the one stubbed here. */
const FILES_LEFTOVER_TITLE = 'uploads.title - LibreFolio';

/** The window title `src/app.html` ships, read from the source of truth rather than imported from the layout. */
function readAppHtmlTitle(): string {
    // The runner and a direct `vitest run` both start from `frontend/`.
    const appHtmlPath = join(process.cwd(), 'src', 'app.html');
    const title = /<title>([^<]*)<\/title>/.exec(readFileSync(appHtmlPath, 'utf8'))?.[1]?.trim();
    if (!title) throw new Error(`No <title> in ${appHtmlPath}: the default window title has no source of truth`);
    return title;
}

function navigationTarget(routeId: RouteId, href: string): NavigationTarget {
    return {params: {}, route: {id: routeId}, url: new URL(href, 'http://librefolio.test')};
}

/** A sidebar link click, shaped the way the router hands it to `onNavigate`. */
function linkNavigation(from: NavigationTarget, to: NavigationTarget): OnNavigate {
    return {type: 'link', from, to, willUnload: false, complete: Promise.resolve(), event: new PointerEvent('click')};
}

/** A `goto()`: what the Files tab bar does to rewrite `?tab=` in place (`replaceState`). */
function gotoNavigation(from: NavigationTarget, to: NavigationTarget): OnNavigate {
    return {type: 'goto', from, to, willUnload: false, complete: Promise.resolve()};
}

/**
 * Mount the layout and hand back the one `onNavigate` callback it registered. Asserted before
 * anything else, so a title spec cannot pass because nothing ran. The callback is registered at
 * init whatever branch the gate picks, so the bootstrap stays in its default state.
 */
async function mountAndCaptureOnNavigate(): Promise<OnNavigateCallback> {
    render(AppLayoutGateHarness);
    await tick();
    expect(mocks.onNavigate, 'the mounted layout must register exactly one onNavigate callback').toHaveBeenCalledTimes(1);
    return mocks.onNavigate.mock.calls[0][0];
}

describe('(app) layout document title — a client-side route change restores the app.html default (workstream J)', () => {
    let titleBefore = '';

    beforeEach(() => {
        titleBefore = document.title;
    });

    afterEach(() => {
        document.title = titleBefore;
    });

    it('restores the app.html title when leaving Files for a route that sets none (Files → Dashboard)', async () => {
        const defaultTitle = readAppHtmlTitle();
        expect(defaultTitle, 'the leftover must differ from the default, or a reset could not be observed').not.toBe(FILES_LEFTOVER_TITLE);
        const onNavigateCallback = await mountAndCaptureOnNavigate();
        document.title = FILES_LEFTOVER_TITLE;

        // Awaited, as the router awaits every onNavigate callback before `root.$set`: what is on
        // `document.title` now is what the next page mounts over.
        await onNavigateCallback(linkNavigation(navigationTarget('/(app)/files', '/files'), navigationTarget('/(app)/dashboard', '/dashboard')));

        expect(document.title, 'the Files title outlived the Files page').toBe(defaultTitle);
    });

    it('control: keeps the title on a same-route navigation, which remounts nothing to set it again (Files → Files?tab=brim)', async () => {
        const onNavigateCallback = await mountAndCaptureOnNavigate();
        document.title = FILES_LEFTOVER_TITLE;

        await onNavigateCallback(gotoNavigation(navigationTarget('/(app)/files', '/files'), navigationTarget('/(app)/files', '/files?tab=brim')));

        expect(document.title, 'a query change on the same page must not wipe the title that page set').toBe(FILES_LEFTOVER_TITLE);
    });
});
