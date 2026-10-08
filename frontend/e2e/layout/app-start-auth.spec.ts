/**
 * The app start and the end of a session — K step 19 (plan-phase00TaxonomySelectStep19AppStartAuth, «Test», lot B).
 *
 * Written RED-FIRST, before the cure. Three contracts, one test each:
 *
 *   1. A slow GET /auth/me is not a sign-out. On a full load of an app page the (app) layout asks /auth/me; when
 *      nothing has answered after 5 s it shows the `server-unreachable` panel (Retry: `server-unreachable-retry`) and
 *      stays on the requested URL; when /auth/me then answers 200 the panel goes and the page loads. At the base
 *      (3a8139c29) the layout raced the check against a 5 s timeout and read the timeout as "not signed in":
 *      `goto('/')`, where the root page routes a signed-in user to /dashboard.
 *   2. Signed out, an app page hands over to the root login carrying itself, `/?redirect=<path+query>`, and signing in
 *      through that form lands on it. At the base: a bare `/`, then /dashboard.
 *   3. A 401 from any API call in the middle of a session (the global axios interceptor) goes to the same login
 *      carrying the page it happened on. At the base: a bare `/`.
 *
 * Holding /auth/me. A route holds every GET /auth/me of the page on a gate until the test opens it, then lets each
 * through to the real backend: "the server has not answered yet", not a faked answer. The layout's own request must
 * reach the gate (a presence control), and the panel is awaited as a condition with a deadline well past the 5 s
 * mark, never as a sleep.
 *
 * Where the page went. Main-frame navigations (`framenavigated`: the document, then every client-side navigation)
 * are recorded from just before the action, like the arrival trail of toolbar-width-sweep.spec.ts. A failure quotes
 * the trail: that is the evidence of where a timeout or a 401 took the page. What precedes the requested page's own
 * commit belongs to the page being left, and is not read.
 *
 * Offline and read-only. Every origin but the app's is refused, and POST /assets/prices/current — which /assets polls
 * on load and every 30 s, asking the live providers and writing today's row on shared seeded assets — is answered
 * empty, as in toolbar-width-sweep.spec.ts. TEST_USER only reads and is grandfathered completed on every onboarding
 * flow (populate_mock_data), read back over the API, so no welcome redirect or tour moves the page. The one session
 * state a test changes is its own browser context's cookie jar. Routes are removed after each test.
 *
 * Desktop project (the runner's default); the 401 test opens the off-canvas sidebar first when run on mobile.
 */
import type {Frame, Route} from '@playwright/test';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

const AUTH_ME = '**/api/v1/auth/me';
/** The layout gives /auth/me 5 s; the rest is the margin of a loaded machine. A condition, not a sleep. */
const PANEL_TIMEOUT_MS = 20_000;
const PAGE_TIMEOUT_MS = 30_000;
const LOGIN_URL_TIMEOUT_MS = 10_000;
/** Two query parameters: the `&` must survive the trip through `redirect`, which only an encoded value lets it do. */
const REQUESTED_WITH_QUERY = '/assets?view=table&probe=app-start-auth';
/** Where a sign-out takes an app page: the root login, then the signed-in user's default page. */
const SIGN_OUT_PATHS: readonly string[] = ['/', '/dashboard'];

// Sign-in, a 5 s wait on /auth/me and the assets page's two load waves exceed the default 30 s on a loaded machine;
// a red must end on its own assertion, not on the test timeout.
test.setTimeout(60_000);

type MarkedWindow = Window & {__lfAppStartAuthRuntime?: true};

/** Path and query of an absolute URL. */
function pathOf(href: string): string {
    const {pathname, search} = new URL(href);
    return pathname + search;
}

/** The path alone, of a path-and-query. */
function pathnameOf(pathAndQuery: string): string {
    return new URL(pathAndQuery, 'http://librefolio.local').pathname;
}

/** The address of the page, read apart: where it is, and the page the root login would return to. */
function loginTarget(page: Page): {path: string; redirect: string | null} {
    const url = new URL(page.url());
    return {path: url.pathname, redirect: url.searchParams.get('redirect')};
}

async function keepOffline(page: Page, origin: string): Promise<void> {
    // Seeded icon and portal URLs point at the internet: refused, the icons fall back to their placeholders.
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => route.abort('blockedbyclient'),
    );
    // Answered empty: the live providers are not asked, and today's price row of the shared seeded assets is not written.
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
}

interface Hop {
    /** ms since the recording started. */
    ms: number;
    /** Path and query. */
    url: string;
}

interface Trail {
    hops: () => Hop[];
    stop: () => void;
}

/** Records every main-frame navigation — the document, then each client-side one — until `stop()`. */
function recordMainFrame(page: Page): Trail {
    const started = Date.now();
    const hops: Hop[] = [];
    const onNavigated = (frame: Frame): void => {
        if (frame === page.mainFrame()) hops.push({ms: Date.now() - started, url: pathOf(frame.url())});
    };
    page.on('framenavigated', onNavigated);
    return {hops: () => [...hops], stop: () => page.off('framenavigated', onNavigated)};
}

function describeHops(hops: Hop[]): string {
    return hops.map(({ms, url}) => `+${ms} ms ${url}`).join(' → ') || 'no navigation';
}

/** The hops from the requested page's own commit on: whatever precedes it belongs to the page being left. */
function hopsFrom(trail: Trail, path: string): Hop[] {
    const hops = trail.hops();
    const first = hops.findIndex((hop) => pathnameOf(hop.url) === path);
    if (first < 0) throw new Error(`precondition: the main frame committed ${path}; it went ${describeHops(hops)}`);
    return hops.slice(first);
}

/** The hops that went where a sign-out goes. */
function signOutHops(trail: Trail, from: string): Hop[] {
    return hopsFrom(trail, from).filter((hop) => SIGN_OUT_PATHS.includes(pathnameOf(hop.url)));
}

/** Runs `check`; when it fails, the failure also says where the main frame went, where the page is now, and `extra`. */
async function withTrail(page: Page, trail: Trail, check: () => Promise<unknown>, extra: () => string = () => ''): Promise<void> {
    try {
        await check();
    } catch (error: unknown) {
        const message = error instanceof Error ? error.message : String(error);
        const lines = [`main frame since the action: ${describeHops(trail.hops())}`, `the page is now at ${pathOf(page.url())}`, extra()].filter(Boolean);
        throw new Error(`${message}\n\n${lines.join('\n')}`);
    }
}

/**
 * Holds every GET /auth/me of the page on a gate until `open()`, then lets each through to the backend. A request the
 * page has abandoned in the meantime cannot be continued; whatever waited on it fails on its own assertion.
 */
async function holdAuthMe(page: Page): Promise<{held: () => number; open: () => void}> {
    let release = (): void => {};
    const opened = new Promise<void>((resolve) => {
        release = resolve;
    });
    let held = 0;
    await page.route(AUTH_ME, async (route: Route) => {
        held += 1;
        await opened;
        await route.continue().catch(() => undefined);
    });
    return {held: () => held, open: () => release()};
}

/** Signs in with the shared helper, then waits for the root's post-login routing to leave `/`: the app shell is up. */
async function signIn(page: Page): Promise<void> {
    await login(page, TEST_USER);
    // login() returns once the login form is gone, while the root page still loads the bootstrap and routes away.
    await page.waitForURL((url) => url.pathname !== '/', {timeout: PAGE_TIMEOUT_MS});
    await expect(page.getByTestId('app-shell'), 'the app shell is up after the post-login routing').toBeVisible({timeout: PAGE_TIMEOUT_MS});
}

/** Precondition, read back: no onboarding flow is due, so no welcome redirect or tour moves the page. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `precondition: ${TEST_USER.username} is grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/** The assets page has loaded: its root is visible and its data-busy says both load waves are in. */
async function expectAssetsReady(page: Page): Promise<void> {
    const assetsPage = page.getByTestId('assets-page');
    await expect(assetsPage, 'the assets page renders').toBeVisible({timeout: PAGE_TIMEOUT_MS});
    await waitForSettled(assetsPage, PAGE_TIMEOUT_MS);
}

test.describe('App start: only a 401 signs out, and the login keeps the page (K step 19)', () => {
    test.beforeEach(async ({page, baseURL}) => {
        if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
        await keepOffline(page, new URL(baseURL).origin);
    });

    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    test('GET /auth/me silent past 5 s: the server-unreachable panel shows on the requested page, and the late answer loads it', async ({page}) => {
        await signIn(page);
        await expectNoOnboardingDue(page);

        const gate = await holdAuthMe(page);
        const trail = recordMainFrame(page);
        try {
            await page.goto('/assets');
            await expect.poll(gate.held, {message: "precondition: the layout's GET /auth/me reached the gate, which holds it"}).toBeGreaterThan(0);

            const panel = page.getByTestId('server-unreachable');
            const heldNote = (): string => `GET /auth/me requests held by the gate: ${gate.held()} (1 is the layout's own; a 2nd is the root page asking again after a redirect)`;
            await withTrail(
                page,
                trail,
                () =>
                    expect
                        .poll(async () => ({panel: await panel.isVisible(), at: pathOf(page.url())}), {
                            message: 'GET /auth/me silent for 5 s is not a sign-out: the layout shows server-unreachable and stays on /assets',
                            timeout: PANEL_TIMEOUT_MS,
                        })
                        .toEqual({panel: true, at: '/assets'}),
                heldNote,
            );
            await expect(panel.getByTestId('server-unreachable-retry'), 'the panel offers Retry').toBeVisible();
            expect(signOutHops(trail, '/assets'), `while /auth/me is silent the main frame never goes to / or /dashboard: ${describeHops(trail.hops())}`).toEqual([]);

            gate.open();
            await expect(panel, 'the late 200 of /auth/me removes the panel').toBeHidden({timeout: PAGE_TIMEOUT_MS});
            await withTrail(page, trail, () => expectAssetsReady(page));
            expect(pathOf(page.url()), 'the page that loads is the one requested').toBe('/assets');
            expect(signOutHops(trail, '/assets'), `from the load to the loaded page the main frame never went to / or /dashboard: ${describeHops(trail.hops())}`).toEqual([]);
        } finally {
            gate.open();
            trail.stop();
        }
    });

    test('signed out, an app page hands over to the login carrying its path and query, and signing in there lands on it', async ({page}) => {
        const trail = recordMainFrame(page);
        try {
            await page.goto(REQUESTED_WITH_QUERY);
            await expect(page.getByTestId('login-page'), 'without a session the app page hands over to the root login').toBeVisible({timeout: PAGE_TIMEOUT_MS});
            await withTrail(page, trail, () =>
                expect
                    .poll(() => loginTarget(page), {
                        message: `the login carries the requested page, path and query: /?redirect=${encodeURIComponent(REQUESTED_WITH_QUERY)}`,
                        timeout: LOGIN_URL_TIMEOUT_MS,
                    })
                    .toEqual({path: '/', redirect: REQUESTED_WITH_QUERY}),
            );

            // Through this very form: login() would start over from a bare `/` and lose the redirect.
            await expect(page.getByTestId('login-form')).toBeVisible();
            await page.getByTestId('login-username').fill(TEST_USER.username);
            await page.getByTestId('login-password').fill(TEST_USER.password);
            await page.getByTestId('login-submit').click();
            await expect(page.getByTestId('login-page'), 'the sign-in went through').toBeHidden({timeout: PAGE_TIMEOUT_MS});
            await expectNoOnboardingDue(page);

            await withTrail(page, trail, () => expect.poll(() => pathOf(page.url()), {message: 'signing in on that login lands on the page that was asked for, query included', timeout: PAGE_TIMEOUT_MS}).toBe(REQUESTED_WITH_QUERY));
            await expectAssetsReady(page);
            expect(pathOf(page.url()), 'and stays there once it has loaded').toBe(REQUESTED_WITH_QUERY);
        } finally {
            trail.stop();
        }
    });

    test('a 401 in the middle of a session goes to the login carrying the page it happened on', async ({page, context}, testInfo) => {
        await signIn(page);
        await expectNoOnboardingDue(page);
        await navigateTo(page, '/assets');
        await expectAssetsReady(page);
        // Mark the running app: the login must come from inside it — the 401 interceptor — not from a fresh start.
        await page.evaluate(() => {
            (window as MarkedWindow).__lfAppStartAuthRuntime = true;
        });

        await context.clearCookies();
        expect(await context.cookies(), "precondition: this context's session cookie is gone, so its next API call answers 401").toEqual([]);

        const trail = recordMainFrame(page);
        try {
            // A client-side hop whose page calls the API on mount (/brokers loads its list).
            if (testInfo.project.name === 'mobile') await page.getByTestId('mobile-menu-toggle').click();
            await page.getByTestId('nav-brokers').click();
            await expect(page.getByTestId('login-page'), 'the 401 hands over to the root login').toBeVisible({timeout: PAGE_TIMEOUT_MS});
            expect(await page.evaluate(() => (window as MarkedWindow).__lfAppStartAuthRuntime === true), 'the app runtime survived: the login came from the running app, not from a full load').toBe(true);
            expect(hopsFrom(trail, '/brokers')[0].url, 'precondition: the client-side hop reached /brokers, whose API call answered 401').toBe('/brokers');
            await withTrail(page, trail, () =>
                expect
                    .poll(() => loginTarget(page), {
                        message: 'the login carries the page the 401 happened on: /?redirect=%2Fbrokers',
                        timeout: LOGIN_URL_TIMEOUT_MS,
                    })
                    .toEqual({path: '/', redirect: '/brokers'}),
            );
        } finally {
            trail.stop();
        }
    });
});
