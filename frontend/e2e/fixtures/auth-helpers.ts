import {expect, test, type BrowserContext, type Page} from './playwright';
import {type Language, TEST_USER} from './test-users';

/**
 * Where a sign-in ends: the screens the app renders once its post-login routing is over. Mutually exclusive by
 * construction — `app-shell` and `welcome-shell` are branches of `(app)/+layout.svelte`, while
 * `onboarding-bootstrap-blocked` is the root page (`+page.svelte`) staying on `/` because the bootstrap could not load.
 */
const ARRIVALS = ['app-shell', 'welcome-shell', 'onboarding-bootstrap-blocked'] as const;
/** The screens a sign-in passes through on its way there: never a place login() stops, named only when it never arrives. */
const ON_THE_WAY = ['login-page', 'auth-loading', 'app-auth-checking', 'app-bootstrap-loading', 'onboarding-redirecting', 'server-unreachable'] as const;
/** What {@link screenOnView} reads once the sign-in has arrived: `app-shell at /dashboard`. */
const ARRIVED = new RegExp(`^(?:${ARRIVALS.join('|')}) at `);
/**
 * From the form gone to the arrival: the bootstrap's three reads, then the destination's code and its first render. On a
 * loaded lane (four workers, an instrumented backend) this has run past the 3–5 s its callers used to give it (V-27).
 * A deadline, never a delay.
 */
const ARRIVAL_MS = 30_000;

/** The session cookie of the app (`SESSION_COOKIE_NAME`, `backend/app/api/v1/auth.py`). */
const SESSION_COOKIE = 'session';

type SessionCookie = Awaited<ReturnType<BrowserContext['cookies']>>[number];

/**
 * The session of each user this worker process has signed in through the form: `username → session cookie` (project 71,
 * step 3.15, decision D7). A module of a Playwright worker lives as long as the worker, so the map does too, and is never
 * shared between workers. The cookie is the one the real sign-in set — a JWT carrying the account's id and session
 * version — so it stays valid exactly as long as the server would keep that session: a change of password, a «sign out
 * everywhere», a repopulated database or a restarted server end it, and the next `login()` of that user goes through the
 * form again and keeps the new one.
 */
const SESSIONS = new Map<string, SessionCookie>();

/**
 * Test aid (LR-03, LR-06): make the next `login()` of `username` meet a session it cannot use, without touching the
 * shared user: `forget` drops it, `break` keeps a cookie the server refuses, `swap` keeps the session of `other` under
 * `username` — what a repopulated database can do when it gives a user another account's former id.
 */
export function forgetOrBreakLogin(username: string, how: 'forget' | 'break' | 'swap', other?: string): void {
    const kept = SESSIONS.get(username);
    if (how === 'forget' || !kept) {
        SESSIONS.delete(username);
        return;
    }
    if (how === 'break') SESSIONS.set(username, {...kept, value: `${kept.value}broken`});
    else if (other && SESSIONS.has(other)) SESSIONS.set(username, SESSIONS.get(other)!);
}

/**
 * How a sign-in got in, published on the running test (project 71, steps 3.14 and 3.15, decision D7): `login-path` —
 * `form`, `reused` (the worker's kept session of that user) or `already` (the page was signed in before the call) — and
 * `login-ms`, the milliseconds the call took. Playwright's
 * JSON report carries both per test, so a run can sum what signing in costs. Published state, not a stopwatch to switch
 * on: always written, at the cost of one clock read. Outside a running test (`test.info()` throws) nothing is written.
 */
function annotateLogin(path: 'form' | 'reused' | 'already', startedAt: number): void {
    try {
        const {annotations} = test.info();
        annotations.push({type: 'login-path', description: path});
        annotations.push({type: 'login-ms', description: String(Math.max(1, Math.round(performance.now() - startedAt)))});
    } catch {
        // Called outside a test (a setup script): there is nowhere to publish.
    }
}

/** Path and query of the page on view. */
function pathOnView(page: Page): string {
    const {pathname, search} = new URL(page.url());
    return pathname + search;
}

/** The known screen on view and its path, e.g. `auth-loading at /`. One-shot reads: login() polls them. */
async function screenOnView(page: Page): Promise<string> {
    for (const testId of [...ARRIVALS, ...ON_THE_WAY]) {
        if (await page.getByTestId(testId).isVisible()) return `${testId} at ${pathOnView(page)}`;
    }
    return `none of [${[...ARRIVALS, ...ON_THE_WAY].join(', ')}] at ${pathOnView(page)}`;
}

/** Who the page's session belongs to, from `GET /auth/me` through the page's own cookies; null without one. */
async function signedInAs(page: Page): Promise<string | null> {
    const answer = await page.request.get('/api/v1/auth/me');
    if (!answer.ok()) return null;
    return ((await answer.json()) as {user?: {username?: string}}).user?.username ?? null;
}

/** Wait until the app has arrived on one of {@link ARRIVALS} or shows the sign-in: one wait for the two outcomes. */
async function arrivedOrSignIn(page: Page, user: {username: string}): Promise<'arrived' | 'signin'> {
    let outcome: 'arrived' | 'signin' = 'signin';
    await expect
        .poll(
            async () => {
                const screen = await screenOnView(page);
                if (ARRIVED.test(screen)) outcome = 'arrived';
                else if (screen.startsWith('login-page at ')) outcome = 'signin';
                else return screen;
                return 'settled';
            },
            {message: `login(${user.username}): the app arrives on ${ARRIVALS.join(' | ')} or shows the sign-in — received: the screen on view`, timeout: ARRIVAL_MS, intervals: [100, 250]},
        )
        .toBe('settled');
    return outcome;
}

/** The form part of a sign-in: fill it, submit it, wait for the arrival, and keep the session the server set. */
async function signInThroughForm(page: Page, user: {username: string; password: string}): Promise<void> {
    const loginPage = page.getByTestId('login-page');
    await expect(page.getByTestId('login-form')).toBeVisible();

    // Fill and submit using data-testid
    await page.getByTestId('login-username').fill(user.username);
    await page.getByTestId('login-password').fill(user.password);
    await page.getByTestId('login-submit').click();

    // The sign-in went through: the form is gone, and the root page shows `auth-loading` while it loads the bootstrap.
    await expect(loginPage).not.toBeVisible({timeout: 20_000});
    await page.waitForLoadState('domcontentloaded');

    // Signed in, not yet arrived: the root page still reads the bootstrap, then routes on (or stops on `/` when it is
    // blocked). Each caller used to wait for that on a short budget of its own; it is awaited here, once.
    await expect
        .poll(() => screenOnView(page), {
            message: `login(${user.username}): the app arrives on ${ARRIVALS.join(' | ')} — received: the screen on view`,
            timeout: ARRIVAL_MS,
            // An inline literal on purpose: expect.poll consumes the array it is given.
            intervals: [100, 250],
        })
        .toMatch(ARRIVED);

    const cookie = (await page.context().cookies()).find((candidate) => candidate.name === SESSION_COOKIE);
    if (cookie) SESSIONS.set(user.username, cookie);
}

/** Drop the page's session cookie and open `/` again, which then shows the sign-in. */
async function startSignedOut(page: Page): Promise<void> {
    await page.context().clearCookies({name: SESSION_COOKIE});
    await page.goto('/');
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: ARRIVAL_MS});
}

/**
 * Sign `user` in, and return once the app has arrived.
 *
 * With a session of `user` kept by this worker (an earlier sign-in through the form, in any test of the worker), the
 * cookie is put in the page's context before `/` opens, and the app arrives without the form — after one check that the
 * session is really `user`'s (a repopulated database can give a user another account's former id). Without one, or when
 * the kept session no longer works, through the login form, and the new session is kept. Already signed in (as anyone)
 * and nothing kept for `user`: as before, the call returns where the app arrived.
 *
 * On return exactly one of {@link ARRIVALS} is visible:
 * - `app-shell`: the page the root routed the user to — `/dashboard` for an account with nothing due;
 * - `welcome-shell`: `/welcome`, for an account whose Welcome is still due (a newly registered user);
 * - `onboarding-bootstrap-blocked`: still on `/`, because the bootstrap could not load — a stop by design, for the
 *   caller to assert.
 * Arrived is not loaded: the page inside the shell still fetches its own data, so a caller that needs it waits for the
 * page's own state (`data-busy`). A sign-in that does not arrive within {@link ARRIVAL_MS} fails here, naming the screen
 * on view and its path. The test is annotated with how the sign-in got in and what it took ({@link annotateLogin}).
 *
 * What the sign-in's own answer carries — the saved language and theme, the donation popup — comes only through the form:
 * a spec about those signs in with {@link loginWithForm}.
 */
export async function login(page: Page, user = TEST_USER) {
    const startedAt = performance.now();
    const kept = SESSIONS.get(user.username);
    if (kept) await page.context().addCookies([kept]);
    await page.goto('/');

    if ((await arrivedOrSignIn(page, user)) === 'arrived') {
        if (!kept) {
            // Already signed in before the call, and nothing kept for this user: as before, it stays where it arrived.
            annotateLogin('already', startedAt);
            return;
        }
        if ((await signedInAs(page)) === user.username) {
            annotateLogin('reused', startedAt);
            return;
        }
        // The kept session belongs to someone else now: forget it, and sign in through the form.
        SESSIONS.delete(user.username);
        await startSignedOut(page);
    } else if (kept) {
        // The kept session ended (a new password, a sign-out everywhere, a repopulated database): the form, as before.
        SESSIONS.delete(user.username);
    }
    await signInThroughForm(page, user);
    annotateLogin('form', startedAt);
}

/**
 * Sign `user` in through the login form, always: never with a session this worker kept, never «already signed in» — a
 * session in the page is dropped first. For the specs about the sign-in itself (what its answer carries: the saved
 * language and theme, the donation popup; a POST they intercept). The new session is kept for the next `login()`.
 */
export async function loginWithForm(page: Page, user = TEST_USER) {
    const startedAt = performance.now();
    await startSignedOut(page);
    await signInThroughForm(page, user);
    annotateLogin('form', startedAt);
}

/**
 * Logout current user
 */
export async function logout(page: Page) {
    // Sidebar is visible on desktop, click logout button directly
    await page.getByTestId('logout-button').click();
    // The click POSTs /auth/logout and only then routes to `/`, whose page asks GET /auth/me again before it shows the
    // login: round trips a busy lane delays, which the 3 s expect default bets against. Each is awaited as the state
    // the app publishes once it is over — the URL, then the login page — with the budgets login() gives a sign-in.
    await expect(page).toHaveURL('/', {timeout: 20_000});
    await expect(page.getByTestId('login-page')).toBeVisible({timeout: 20_000});
}

/**
 * The budget of each wait in setLanguage(). A switch waits for the chosen dictionary, a ~290 KB chunk fetched on first
 * use, and for the page to redraw in it: a round trip the 3 s expect default bets against, and lost at load 60
 * (toolbar-width-sweep, French on screen a moment later). 15 s, as navigateTo() gives the same `data-i18n-ready`.
 * A deadline, never a delay.
 */
const LANGUAGE_SWITCH_MS = 15_000;

/**
 * Change UI language
 */
export async function setLanguage(page: Page, lang: Language) {
    // Wait for language selector to be visible (needs longer timeout for SvelteKit hydration after fresh navigation)
    await expect(page.getByTestId('language-selector-button')).toBeVisible({timeout: LANGUAGE_SWITCH_MS});
    await page.getByTestId('language-selector-button').click();

    // Click the menu item specifically (not any element with that text)
    const langNames: Record<Language, string> = {
        en: 'English',
        it: 'Italiano',
        fr: 'Français',
        es: 'Español',
    };
    // Use role='menuitem' to be specific and avoid conflicts with other dropdowns
    await page.getByRole('menuitem', {name: new RegExp(langNames[lang])}).click();
    // The app publishes both halves: `lang` flips to the chosen language, and
    // data-i18n-ready goes true only once that dictionary has actually landed.
    // Asserting both is what makes this helper's promise ("when I return, the UI
    // speaks `lang`") true instead of merely likely.
    await expect(page.locator('html')).toHaveAttribute('lang', lang, {timeout: LANGUAGE_SWITCH_MS});
    await expect(page.locator('html')).toHaveAttribute('data-i18n-ready', 'true', {timeout: LANGUAGE_SWITCH_MS});
}

/**
 * Open mobile menu (burger) if on mobile viewport
 */
export async function openMobileMenu(page: Page) {
    const burger = page.getByTestId('mobile-menu-toggle');
    if (await burger.isVisible()) {
        await burger.click();
        // No sleep for the slide-in animation: Playwright's click() already refuses
        // to act on an element that is still moving, so whatever is clicked next
        // waits for the sidebar to settle on its own.
    }
}

/**
 * Navigate to a route, handling mobile menu if needed
 */
export async function navigateTo(page: Page, route: string, menuItem?: string) {
    // If menuItem provided, use sidebar navigation
    if (menuItem) {
        await openMobileMenu(page);
        await page.getByRole('link', {name: new RegExp(menuItem, 'i')}).click();
    } else {
        await page.goto(route);
    }
    // Wait for page to be fully loaded.
    await page.waitForLoadState('domcontentloaded');
    // `data-i18n-ready` is written by the root +layout, so the attribute does not
    // exist at all until the client has hydrated — waiting for it IS the hydration
    // barrier, and it also guarantees the translations are in. This replaced a flat
    // 100ms "buffer for Svelte hydration" which, at 112 call sites, was both ~11s of
    // dead time and a guess that got worse under parallel load.
    await page.waitForSelector('html[data-i18n-ready="true"]', {timeout: 15_000});
}
