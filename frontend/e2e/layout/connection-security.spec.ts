/**
 * The connection-security indicator in a real browser — plan 36 (§2.2–§2.3 and «Fatto quando»).
 *
 * Written RED-FIRST against the stubs of step 2. What a user sees, on the runner's desktop AND mobile projects:
 *
 *   1. On the lane's own baseURL (localhost) the sidebar line is secure, for the reason `localhost`, once the server has
 *      answered (`data-server-checked="true"`); its details link the user page at its root, in the UI language (English,
 *      read back as a precondition), in a new tab; on a phone the burger carries no dot.
 *   2. Under other names. Chromium maps two names onto the loopback (`--host-resolver-rules`), so the lane's own backend
 *      answers under a host the browser classifies differently. Cookies are per host, so each test signs in through the
 *      login form served under its own host (`login()` would start over on the baseURL, whose cookie is another host's):
 *        - `lf-e2e.lan` → local / lan: a LAN name, and a client the server does not see as public; no dot;
 *        - `lf-e2e.example` → local / uncertain: a public name, but the server sees the loopback; no dot;
 *        - the same name with a public `X-Forwarded-For` (203.0.113.9: the server reads the last value) → insecure /
 *          internet, and on a phone the red dot on the burger. The case before is its control: same host, same
 *          backend, only the header differs.
 *   3. Not here: the admin warning. It needs HTTPS in the browser and a session cookie the server does not mark Secure;
 *      the lane serves plain HTTP, so `cookieWarning` cannot arise in this browser. ConnectionSecurityIndicator.test.ts
 *      covers it.
 *
 * Waiting: on the attributes the line publishes — `data-server-checked`, then `data-level` and `data-reason` — never on
 * the clock, never on text. The dot is read before the sidebar opens, on the burger the user sees.
 *
 * Offline and read-only: every origin but the app's own is refused, and TEST_USER only reads (the line's GET), so the one
 * state a test changes is its own browser context: cookies and extra headers. Routes are removed after each test.
 *
 * Why `test.use` sits at the top of the file and not in the describe of the mapped names: `launchOptions` is a
 * worker-scoped option, and Playwright refuses one inside a describe ("Cannot use({ launchOptions }) in a describe
 * group, because it forces a new worker"). The rules map the two names above and nothing else, so the localhost case is
 * untouched by them; the config's own launch options are kept.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_USER} from '../fixtures/test-users';

const LAN_NAME = 'lf-e2e.lan';
const PUBLIC_NAME = 'lf-e2e.example';
/** Chromium resolves the two names to the loopback, where the lane's backend listens. */
const HOST_RESOLVER_RULES = `--host-resolver-rules=MAP ${LAN_NAME} 127.0.0.1, MAP ${PUBLIC_NAME} 127.0.0.1`;
/** A public source address (TEST-NET-3): public to the server's classifier. */
const PUBLIC_CLIENT = '203.0.113.9';
/** The user page, at its root, in English. */
const DOCS_HREF_EN = '/mkdocs/user/connection-security/';

/** Sign-in and the post-login routing on a loaded machine. */
const PAGE_TIMEOUT_MS = 30_000;
/** The line asks the server once it has mounted: one GET, on a loaded machine. */
const VERDICT_TIMEOUT_MS = 15_000;

test.setTimeout(60_000);

test.use({
    launchOptions: async ({launchOptions}, use) => {
        await use({...launchOptions, args: [...(launchOptions.args ?? []), HOST_RESOLVER_RULES]});
    },
});

/** The runner's baseURL: every verdict below is that of a plain-HTTP page. */
function laneBaseURL(baseURL: string | undefined): URL {
    if (!baseURL) throw new Error('This spec needs the runner-provided baseURL');
    const url = new URL(baseURL);
    expect(url.protocol, 'precondition: the lane serves plain HTTP, and the verdicts below are those of an http: page').toBe('http:');
    return url;
}

/** The lane's origin under another host name: the same protocol and port as the baseURL. */
function originUnder(base: URL, hostname: string): string {
    const url = new URL(base.href);
    url.hostname = hostname;
    return url.origin;
}

/** Seeded icon and portal URLs point at the internet: refused, the icons fall back to their placeholders. */
async function keepOffline(page: Page, origin: string): Promise<void> {
    await page.route(
        (url) => (url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== origin,
        (route) => route.abort('blockedbyclient'),
    );
}

/** Signs in with the shared helper, then waits for the root's post-login routing to leave `/`: the app shell is up. */
async function signInOnBaseURL(page: Page): Promise<void> {
    await login(page, TEST_USER);
    await page.waitForURL((url) => url.pathname !== '/', {timeout: PAGE_TIMEOUT_MS});
    await expect(page.getByTestId('app-shell'), 'the app shell is up after the post-login routing').toBeVisible({timeout: PAGE_TIMEOUT_MS});
}

/**
 * Signs TEST_USER in through the login form served under `origin`, then waits for the app shell, still under `origin`.
 * No onboarding read-back here: `page.request` resolves names in Node, not through Chromium's rules, and these cases
 * click nothing once signed in.
 */
async function signInUnder(page: Page, origin: string): Promise<void> {
    await page.goto(`${origin}/`);
    await expect(page.getByTestId('login-page'), `${origin} has no session of its own yet: its login shows`).toBeVisible({timeout: PAGE_TIMEOUT_MS});
    await expect(page.getByTestId('login-form')).toBeVisible();
    await page.getByTestId('login-username').fill(TEST_USER.username);
    await page.getByTestId('login-password').fill(TEST_USER.password);
    await page.getByTestId('login-submit').click();
    await expect(page.getByTestId('login-page'), 'the sign-in went through').toBeHidden({timeout: PAGE_TIMEOUT_MS});
    await expect(page.getByTestId('app-shell'), 'the app shell is up after the post-login routing').toBeVisible({timeout: PAGE_TIMEOUT_MS});
    expect(new URL(page.url()).origin, `precondition: the app stayed under ${origin}`).toBe(origin);
}

/** Precondition, read back: no onboarding flow is due, so no guide or tour overlay competes for the clicks. */
async function expectNoOnboardingDue(page: Page): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `precondition: ${TEST_USER.username} is grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
}

/** Precondition, read back: the UI speaks English — `<html lang>`, and its dictionary is in. */
async function expectEnglishUi(page: Page): Promise<void> {
    await expect
        .poll(() => page.evaluate(() => ({lang: document.documentElement.lang, ready: document.documentElement.dataset.i18nReady ?? null})), {
            message: `precondition: the UI of ${TEST_USER.username} is English (its language setting)`,
        })
        .toEqual({lang: 'en', ready: 'true'});
}

/** The sidebar line, once the server has answered it: its level and its reason. */
async function expectVerdict(page: Page, level: string, reason: string): Promise<void> {
    const line = page.getByTestId('connection-security');
    await expect(line, 'the server answered the line (GET /api/v1/system/connection)').toHaveAttribute('data-server-checked', 'true', {timeout: VERDICT_TIMEOUT_MS});
    await expect(line, `level ${level}`).toHaveAttribute('data-level', level);
    await expect(line, `reason ${reason}`).toHaveAttribute('data-reason', reason);
}

/** On a phone: the burger the user sees before opening the menu, with the red dot or without. Read with the sidebar closed. */
async function expectMenuDot(page: Page, shown: boolean): Promise<void> {
    await expect(page.getByTestId('app-header'), 'precondition: the sidebar is closed, so the burger is what the user sees').toHaveAttribute('data-sidebar-open', 'false');
    const burger = page.getByTestId('mobile-menu-toggle');
    await expect(burger, 'presence barrier: the burger is on screen').toBeVisible();
    const dot = burger.getByTestId('mobile-menu-security-dot');
    if (shown) await expect(dot, 'an insecure connection marks the burger').toBeVisible();
    else await expect(dot, 'only an insecure connection marks the burger').toBeHidden();
}

/** On a phone the sidebar is off-canvas: the burger opens it. */
async function openSidebar(page: Page): Promise<void> {
    const header = page.getByTestId('app-header');
    await expect(header).toHaveAttribute('data-sidebar-open', 'false');
    await page.getByTestId('mobile-menu-toggle').click();
    await expect(header, 'the burger opened the sidebar').toHaveAttribute('data-sidebar-open', 'true');
}

test.describe('Connection security on the lane’s own baseURL (localhost)', () => {
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    test('secure for the reason localhost; the details link the English user page in a new tab; no dot on the burger', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        await signInOnBaseURL(page);
        await expectNoOnboardingDue(page);
        await expectEnglishUi(page);

        await expectVerdict(page, 'secure', 'localhost');
        if (mobile) await expectMenuDot(page, false);

        if (mobile) await openSidebar(page);
        const toggle = page.getByTestId('connection-security-toggle');
        await expect(toggle, 'the details start closed').toHaveAttribute('aria-expanded', 'false');
        await toggle.click();
        await expect(toggle).toHaveAttribute('aria-expanded', 'true');
        const details = page.getByTestId('connection-security-details');
        await expect(details, 'a click opens the details').toBeVisible();
        const link = details.getByTestId('connection-security-docs-link');
        await expect(link, 'the details link the user page, at its root, in English').toHaveAttribute('href', DOCS_HREF_EN);
        await expect(link, 'in a new tab').toHaveAttribute('target', '_blank');
        await expect(link, 'without a window.opener').toHaveAttribute('rel', /(^|\s)noopener(\s|$)/);
    });
});

test.describe('Connection security under other host names (--host-resolver-rules)', () => {
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    test(`http://${LAN_NAME}: local network — a LAN name, a client the server does not see as public; no dot`, async ({page, baseURL}, testInfo) => {
        const origin = originUnder(laneBaseURL(baseURL), LAN_NAME);
        await keepOffline(page, origin);
        await signInUnder(page, origin);

        await expectVerdict(page, 'local', 'lan');
        if (testInfo.project.name === 'mobile') await expectMenuDot(page, false);
    });

    test(`http://${PUBLIC_NAME}: uncertain — a public name, but the server sees the loopback; no dot`, async ({page, baseURL}, testInfo) => {
        const origin = originUnder(laneBaseURL(baseURL), PUBLIC_NAME);
        await keepOffline(page, origin);
        await signInUnder(page, origin);

        await expectVerdict(page, 'local', 'uncertain');
        if (testInfo.project.name === 'mobile') await expectMenuDot(page, false);
    });

    test(`http://${PUBLIC_NAME} with a public X-Forwarded-For: not secure, and the red dot on the burger`, async ({page, context, baseURL}, testInfo) => {
        const origin = originUnder(laneBaseURL(baseURL), PUBLIC_NAME);
        // Every request of this context carries it, the line's GET included: the server classifies the last value.
        await context.setExtraHTTPHeaders({'X-Forwarded-For': PUBLIC_CLIENT});
        await keepOffline(page, origin);
        await signInUnder(page, origin);

        await expectVerdict(page, 'insecure', 'internet');
        if (testInfo.project.name === 'mobile') await expectMenuDot(page, true);
    });
});
