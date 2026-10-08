// @vitest-environment jsdom
/**
 * `(app)` layout — starting the app: only a 401 goes to the login, and a slow or failing server shows a
 * retry panel instead of signing the user out (K, step 19).
 *
 * Before: `onMount` raced `auth.checkAuth()` against a 5 s timer and sent anything but `true` to
 * `goto('/')`, and so did the reactive redirect. A slow server, a 5xx or a timeout logged the user out of
 * the page they had asked for, and the login then forgot that page, because `/` carried no destination.
 * The approved change: `checkAuth()` answers one of four outcomes, and the layout acts on each —
 *   - `authenticated`   → the start of today: the onboarding bootstrap, observed here through the
 *     settlement mock (`runOwnedOnboardingRouteSettlement`), which the layout starts and which never settles;
 *   - `unauthenticated` → `goto(loginUrl(path + query))`, i.e. `/?redirect=<encoded path and query>`;
 *   - `unreachable`     → the `server-unreachable` panel, whose Retry runs the check again;
 *   - `superseded`      → nothing: a newer auth operation owns the answer.
 * The 5 s timer stays, but it only shows the panel while the check goes on; a late `authenticated`
 * removes the panel and starts the app. The reactive redirect (the store turning initialized and signed
 * out later in the session) goes to `loginUrl` as well — unless the sign-out was requested: `auth.logout()`
 * flips the store the same way, and a sign-out the user asked for (`isSignOutRequested()`) goes to the bare
 * `/`, so that the next person to sign in does not land on the previous user's page.
 *
 * Held still as in `layout.gate.test.ts`, except that `$app/environment` reports `browser: true` here:
 * the subject is exactly the `onMount` path that file keeps inert.
 *   - `auth.checkAuth` returns, per call, a promise the test settles by hand. `isAuthenticated` and
 *     `isAuthInitialized` are writables. An `authenticated` answer flips both to true before it
 *     resolves, as the real store sets the user before it returns; every other answer leaves them alone.
 *     In particular `unauthenticated` does not flip them, so a navigation in that case can only come from
 *     the outcome handling — the reactive redirect has its own case. `isSignOutRequested` answers `false`
 *     unless a case says otherwise: the store was not asked to sign out;
 *   - timers are fake: the 5 s mark is reached with `advanceTimersByTimeAsync`, never waited for;
 *   - the page is `/assets/34?tab=risk`, mounted through `AppLayoutGateHarness`, which fills the slot;
 *   - every child component is a no-op and every store or API the layout touches is a stub — except
 *     `$lib/utils/internalPath` (real: the URLs below are literal) and the new `ServerUnreachable` panel
 *     (real: its test ids are the contract).
 *
 * Assertions read `data-testid`, `data-busy`, the disabled state and the `goto` targets — never text.
 * `app-auth-checking` (the «Checking authentication» state) is new markup. Where it is the presence
 * barrier for an absence assertion it is checked with `expect.soft`, so that today the case still reaches,
 * and reports, the behaviour that is wrong, instead of stopping at the missing attribute. The last case
 * is a guard, green today by design: a check answered in time must leave no 5 s timer behind.
 */
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import type {AppBootstrapState} from '$lib/features/onboarding/appBootstrap.svelte';

type AuthCheckOutcome = 'authenticated' | 'unauthenticated' | 'unreachable' | 'superseded';

const mocks = await vi.hoisted(async () => {
    const {reactiveBox} = await import('$test/runes.svelte');
    const {writable} = await import('svelte/store');
    return {
        bootstrap: reactiveBox<{state: AppBootstrapState}>({state: 'idle'}),
        isAuthenticated: writable(false),
        isAuthInitialized: writable(false),
        checkAuth: vi.fn<() => Promise<AuthCheckOutcome>>().mockName('auth.checkAuth'),
        isSignOutRequested: vi.fn<() => boolean>(() => false).mockName('isSignOutRequested'),
        goto: vi.fn((_target: string, _options?: unknown) => Promise.resolve()).mockName('goto'),
        // Never settles: the authenticated start is observed by its call, and can navigate nowhere behind the assertions.
        runOwnedSettlement: vi.fn(() => new Promise<void>(() => {})).mockName('runOwnedOnboardingRouteSettlement'),
        noopComponent: () => {},
    };
});

vi.mock('$app/environment', () => ({browser: true, dev: true, building: false, version: 'test'}));
vi.mock('$app/navigation', () => ({goto: mocks.goto, afterNavigate: vi.fn(), preloadCode: vi.fn(() => Promise.resolve())}));
vi.mock('$app/stores', async () => {
    const {readable} = await import('svelte/store');
    return {page: readable({route: {id: '/(app)/assets/[id]'}, url: new URL('http://librefolio.test/assets/34?tab=risk')})};
});
vi.mock('$lib/i18n', async () => {
    const {readable} = await import('svelte/store');
    return {_: readable((key: string) => key), i18nLoading: readable(false), initI18n: vi.fn()};
});
vi.mock('$lib/stores/app/auth', async () => {
    const {readable} = await import('svelte/store');
    return {
        // A store still: the authenticated start reads `get(auth).user` once its bootstrap settles (here, never).
        auth: {subscribe: readable({user: null}).subscribe, checkAuth: mocks.checkAuth, logout: vi.fn(() => Promise.resolve())},
        isAuthenticated: mocks.isAuthenticated,
        isAuthInitialized: mocks.isAuthInitialized,
        isSignOutRequested: mocks.isSignOutRequested,
    };
});
// Same shape as the real `appBootstrap` (enumerable getters over `$state`): see the note in `layout.gate.test.ts`.
vi.mock('$lib/features/onboarding/appBootstrap.svelte', () => ({
    appBootstrap: {
        get state() {
            return mocks.bootstrap.state;
        },
        get error() {
            return null;
        },
        get loadedUserId() {
            return 'auth-gate-user';
        },
        get ready() {
            return mocks.bootstrap.state === 'ready' || mocks.bootstrap.state === 'degraded';
        },
        load: vi.fn(() => new Promise<AppBootstrapState>(() => {})),
        resolveDestination: vi.fn((path: string) => path),
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

import {cleanup, fireEvent, render, screen, within} from '$test/component';
import {assertEffectsRun} from '$test/runes.svelte';
import AppLayoutGateHarness from '$test/harness/AppLayoutGateHarness.svelte';

/** `loginUrl('/assets/34?tab=risk')`: the login page, carrying the page that was asked for. */
const LOGIN_URL = '/?redirect=%2Fassets%2F34%3Ftab%3Drisk';

/** The resolvers of every auth check the layout started, in order. */
let checks: Array<(outcome: AuthCheckOutcome) => void> = [];

/** Every place the layout navigated to, in order (options, if any, are not the subject). */
function gotoTargets(): string[] {
    return mocks.goto.mock.calls.map(([target]) => target);
}

/** The retry panel, if it is on screen. */
function panel(): HTMLElement | null {
    return screen.queryByTestId('server-unreachable');
}

/** Lets every promise continuation and every Svelte update queued so far run: a flush, not a clock wait. */
async function settle(): Promise<void> {
    await vi.advanceTimersByTimeAsync(0);
    await tick();
}

/** Mounts the layout at /assets/34?tab=risk and returns once its first auth check is in flight. */
async function mountApp(): Promise<void> {
    render(AppLayoutGateHarness);
    await settle();
    expect(mocks.checkAuth, 'premise: mounting the layout starts one auth check').toHaveBeenCalledTimes(1);
}

/** Answers the auth check started `index`-th, as the real store does: `authenticated` has already set the user when it resolves. */
async function answerCheck(index: number, outcome: AuthCheckOutcome): Promise<void> {
    const resolve = checks[index];
    expect(resolve, `premise: auth check #${index + 1} was started`).toBeTypeOf('function');
    if (outcome === 'authenticated') {
        mocks.isAuthenticated.set(true);
        mocks.isAuthInitialized.set(true);
    }
    resolve(outcome);
    await settle();
}

beforeEach(() => {
    // Negative assertions below would pass vacuously in an environment where effects never run.
    assertEffectsRun();
    vi.useFakeTimers();
    mocks.bootstrap.state = 'idle';
    mocks.isAuthenticated.set(false);
    mocks.isAuthInitialized.set(false);
    checks = [];
    mocks.checkAuth.mockClear();
    mocks.checkAuth.mockImplementation(
        () =>
            new Promise<AuthCheckOutcome>((resolve) => {
                checks.push(resolve);
            }),
    );
    mocks.goto.mockClear();
    mocks.runOwnedSettlement.mockClear();
    mocks.isSignOutRequested.mockClear();
    mocks.isSignOutRequested.mockReturnValue(false);
});

afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
});

describe('(app) layout — the auth check at start: only a 401 is a sign-out (K, step 19)', () => {
    it('unauthenticated → goes to the login carrying the requested path and query, once', async () => {
        await mountApp();

        await answerCheck(0, 'unauthenticated');

        expect(gotoTargets(), 'a 401 at start goes to the login with the page that was asked for, not to a bare /').toEqual([LOGIN_URL]);
        expect(mocks.runOwnedSettlement, 'a signed-out start does not start the app').not.toHaveBeenCalled();
    });

    it('unreachable → the retry panel and no navigation; Retry checks again, and an authenticated answer removes the panel and starts the app', async () => {
        await mountApp();

        await answerCheck(0, 'unreachable');

        const shown = panel();
        expect(shown, 'an unreachable server shows the retry panel').not.toBeNull();
        expect(gotoTargets(), 'an unreachable server is not a sign-out: the requested page stays').toEqual([]);
        expect(mocks.runOwnedSettlement, 'the app does not start on an unanswered check').not.toHaveBeenCalled();
        expect(shown, 'no check in flight').toHaveAttribute('data-busy', 'false');
        const retry = within(shown as HTMLElement).getByTestId('server-unreachable-retry');
        expect(retry, 'no check in flight: Retry is available').toBeEnabled();

        await fireEvent.click(retry);
        await settle();

        expect(mocks.checkAuth, 'Retry runs the auth check again').toHaveBeenCalledTimes(2);
        expect(panel(), 'the panel stays while the new check is in flight').toHaveAttribute('data-busy', 'true');
        expect(within(panel() as HTMLElement).getByTestId('server-unreachable-retry'), 'a check in flight: Retry is disabled').toBeDisabled();

        await answerCheck(1, 'authenticated');

        expect(mocks.runOwnedSettlement, 'an authenticated answer to Retry starts the app').toHaveBeenCalledTimes(1);
        expect(panel(), 'the panel goes once the server has answered').toBeNull();
        expect(gotoTargets(), 'and nothing navigated, to / or anywhere').toEqual([]);
    });

    it('a check slower than 5 s shows the panel without navigating, and its late authenticated answer removes the panel and starts the app', async () => {
        await mountApp();

        await vi.advanceTimersByTimeAsync(4_999);
        await tick();

        expect.soft(screen.queryByTestId('app-auth-checking'), 'while the check is pending the layout shows its checking state (new markup: app-auth-checking)').not.toBeNull();
        expect(panel(), 'before the 5 s mark there is no panel').toBeNull();
        expect(gotoTargets(), 'before the 5 s mark nothing navigates').toEqual([]);

        await vi.advanceTimersByTimeAsync(2);
        await tick();

        expect(gotoTargets(), 'a slow check is not a sign-out: past 5 s the requested page stays').toEqual([]);
        expect(panel(), 'past 5 s the retry panel shows, while the check goes on').not.toBeNull();

        await answerCheck(0, 'authenticated');

        expect(mocks.runOwnedSettlement, 'the late authenticated answer starts the app').toHaveBeenCalledTimes(1);
        expect(panel(), 'the late authenticated answer removes the panel').toBeNull();
        expect(gotoTargets(), 'and nothing navigated, to / or anywhere').toEqual([]);
    });

    it('superseded → nothing: no navigation, no panel and no start, because a newer auth operation owns the answer', async () => {
        await mountApp();

        await answerCheck(0, 'superseded');

        expect.soft(screen.queryByTestId('app-auth-checking'), 'the layout is still in its checking state (new markup: app-auth-checking)').not.toBeNull();
        expect(gotoTargets(), 'a superseded answer navigates nowhere').toEqual([]);
        expect(panel(), 'a superseded answer shows no panel').toBeNull();
        expect(mocks.runOwnedSettlement, 'a superseded answer does not start the app either').not.toHaveBeenCalled();
    });

    it('reactive redirect: a session that ends later (the store turns initialized and signed out) goes to the login with the current path and query', async () => {
        await mountApp();
        await answerCheck(0, 'authenticated');
        expect(mocks.runOwnedSettlement, 'premise: the app started').toHaveBeenCalledTimes(1);
        expect(gotoTargets(), 'premise: nothing has navigated yet').toEqual([]);

        // What the store does on a 401 later in the session: the user goes, the store stays initialized, and
        // no sign-out was requested.
        mocks.isSignOutRequested.mockReturnValue(false);
        mocks.isAuthenticated.set(false);
        await settle();

        expect(gotoTargets(), 'the reactive redirect keeps the page that was open, as the start does').toEqual([LOGIN_URL]);
    });

    it('reactive redirect: a sign-out the user asked for (auth.logout()) goes to the bare login, carrying no page for the next person to sign in', async () => {
        await mountApp();
        await answerCheck(0, 'authenticated');
        expect(mocks.runOwnedSettlement, 'premise: the app started').toHaveBeenCalledTimes(1);
        expect(gotoTargets(), 'premise: nothing has navigated yet').toEqual([]);

        // What `auth.logout()` does: the sign-out is marked as requested first, then the user goes and the
        // store stays initialized — the same flip as a 401.
        mocks.isSignOutRequested.mockReturnValue(true);
        mocks.isAuthenticated.set(false);
        await settle();

        expect(
            gotoTargets().filter((target) => target.includes('redirect')),
            'a requested sign-out carries no page to the login',
        ).toEqual([]);
        expect(gotoTargets(), 'a requested sign-out goes to the bare login').toEqual(['/']);
    });

    it('guard — a check answered before the 5 s mark leaves no timer behind: past 5 s there is still no panel and no navigation', async () => {
        await mountApp();
        await answerCheck(0, 'authenticated');
        expect(mocks.runOwnedSettlement, 'premise: the app started').toHaveBeenCalledTimes(1);

        await vi.advanceTimersByTimeAsync(10_000);
        await tick();

        expect(screen.queryByTestId('app-bootstrap-loading'), 'the started app is still on screen').not.toBeNull();
        expect(panel(), 'no panel appears after a check that was answered in time').toBeNull();
        expect(gotoTargets(), 'and nothing navigated').toEqual([]);
    });
});
