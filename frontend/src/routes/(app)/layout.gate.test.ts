// @vitest-environment jsdom
/**
 * `(app)` layout — the onboarding route gate of workstream J follows the bootstrap when it settles.
 *
 * The layout is a legacy component, and it reads `appBootstrap` in two ways that do not react
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
 * The window-title reset this file also tested is dead code under the rule that no page changes
 * the browser tab title (K, step 12c); that rule is guarded by `src/routes/documentTitle.guard.test.ts`
 * and `e2e/layout/document-title.spec.ts`.
 *
 * Only the gate is under test, so everything around it is held still:
 *   - `appBootstrap` is a fake with the real object's shape, enumerable getters over `$state`
 *     (`reactiveBox`), which is exactly what `deep_read_state` reads. The spec flips its state and
 *     flushes with `tick()`; `resolveDestination` is scripted per test.
 *   - `$app/environment` reports `browser: false`. The gate reads nothing from it, and it keeps
 *     both navigation paths inert: `onMount`'s auth race (a real 5 s timer) and the owned
 *     settlement never start, and the reactive redirect `$:` is guarded by `browser`. `goto` and
 *     the settlement are mocks too, and every gate test asserts that neither ran, so a branch
 *     change can only have come from the template gate.
 *   - every child component is a no-op, and every store or API the layout touches is a stub. None
 *     of them is the subject, and each would otherwise start network, storage or observer work.
 *   - `i18nLoading` is a writable that every case starts at `false` (the dictionary is ready); only
 *     the workstream O case below flips it, to stand for a later catalogue load.
 *
 * Assertions read `data-testid` only: the stubbed `$_` returns keys, and nothing reads text.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import type {AppBootstrapState} from '$lib/features/onboarding/appBootstrap.svelte';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const {writable} = await import('svelte/store');
    return {
        bootstrap: reactiveBox<{state: AppBootstrapState}>({state: 'loading'}),
        i18nLoading: writable(false),
        resolveDestination: vi.fn<(path: string) => string>(),
        goto: vi.fn(() => Promise.resolve()),
        // Never settles: were it ever started, it still could not navigate behind the assertions.
        runOwnedSettlement: vi.fn(() => new Promise<void>(() => {})),
        noopComponent: () => {},
    };
});

vi.mock('$app/environment', () => ({browser: false, dev: true, building: false, version: 'test'}));
vi.mock('$app/navigation', () => ({goto: mocks.goto, afterNavigate: vi.fn(), preloadCode: vi.fn(() => Promise.resolve())}));
vi.mock('$app/stores', async () => {
    const {readable} = await import('svelte/store');
    return {page: readable({route: {id: '/(app)/dashboard'}, url: new URL('http://librefolio.test/dashboard')})};
});
vi.mock('$lib/i18n', async () => {
    const {readable} = await import('svelte/store');
    return {_: readable((key: string) => key), i18nLoading: mocks.i18nLoading, initI18n: vi.fn()};
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
    mocks.i18nLoading.set(false);
    mocks.resolveDestination.mockReset();
    mocks.goto.mockClear();
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

// svelte-i18n 4 reports a language switch whose catalogue is still in flight after its 200 ms
// `loadingDelay` as loading. The layout swapped its whole content for the placeholder on every such
// report, so the requested page was torn down and rebuilt, and the rebuild re-read persisted state: a
// language picked in Welcome was lost (`e2e/auth.spec.ts`, 3c). Only the first dictionary may hold
// the app back; this mounts after it, with the dictionary ready.
describe('(app) layout — a later catalogue load keeps the requested page mounted (workstream O)', () => {
    it('keeps the very same requested-page node through a catalogue load that starts after i18n was ready', async () => {
        mocks.resolveDestination.mockImplementation((path) => path);
        mocks.bootstrap.state = 'ready';
        render(AppLayoutGateHarness);
        await tick();
        const requestedPage = within(screen.getByTestId('app-shell')).getByTestId('app-layout-requested-page');

        mocks.i18nLoading.set(true);
        await tick();
        expect(requestedPage, 'a later catalogue load tore the requested page down').toBeInTheDocument();

        mocks.i18nLoading.set(false);
        await tick();
        expect(screen.getByTestId('app-layout-requested-page'), 'the requested page was rebuilt after the load').toBe(requestedPage);
        expectNothingNavigated();
    });
});
