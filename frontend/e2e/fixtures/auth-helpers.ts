import {expect, type Page} from './playwright';
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

/**
 * Sign `user` in through the login form at `/`, and return once the app has arrived.
 *
 * On return exactly one of {@link ARRIVALS} is visible:
 * - `app-shell`: the page the root routed the user to — `/dashboard` for an account with nothing due;
 * - `welcome-shell`: `/welcome`, for an account whose Welcome is still due (a newly registered user);
 * - `onboarding-bootstrap-blocked`: still on `/`, because the bootstrap could not load — a stop by design, for the
 *   caller to assert.
 * Arrived is not loaded: the page inside the shell still fetches its own data, so a caller that needs it waits for the
 * page's own state (`data-busy`). Already signed in, it returns as soon as the sidebar's sign-out control shows, which
 * lives in the app shell. A sign-in that does not arrive within {@link ARRIVAL_MS} fails here, naming the screen on view
 * and its path.
 */
export async function login(page: Page, user = TEST_USER) {
    await page.goto('/');

    // Wait for auth check to complete — either login form appears or we're already logged in
    const loginPage = page.getByTestId('login-page');
    const appLayout = page.getByTestId('logout-button');

    // Race: login page vs app layout (already authenticated)
    const visible = await Promise.race([loginPage.waitFor({state: 'visible', timeout: 10_000}).then(() => 'login' as const), appLayout.waitFor({state: 'visible', timeout: 10_000}).then(() => 'app' as const)]).catch(() => 'timeout' as const);

    if (visible === 'app') {
        // Already logged in — nothing to do
        return;
    }

    if (visible === 'timeout') {
        // Neither appeared — force a retry with a fresh context
        await page.goto('/');
        await expect(loginPage).toBeVisible({timeout: 10_000});
    }

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
