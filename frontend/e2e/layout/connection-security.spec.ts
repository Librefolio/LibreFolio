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
 *   4. An administrator's security dot (N69-1, lot N69b; decisions D1 a, D2 a, D3 a), written RED-FIRST in its turn: today
 *      the root publishes neither attribute below and no administrator gets a dot. For an administrator the line reads
 *      `GET /api/v1/security/checks` — once per page load, into the store Settings › Security shares — and publishes on
 *      its root `data-security-attention`, the errors and warnings (an `info` is listed by the tab, never counted), and
 *      `data-security-severity`: `error` with an error among them, else `warning`, `none` with nothing. With attention:
 *      a dot on its icon (`connection-security-attention-dot`, `data-severity`), the sidebar expanded or collapsed; after
 *      the reason in its details, a link to Settings › Security (`connection-security-attention-link`) that closes them;
 *      on a phone the burger's dot too, of the same severity on a secure connection. Under a loopback name the browser
 *      adds no finding of its own (the open-registration warning is for hosts outside the local network,
 *      `openRegistrationNoticeFor`), so the server's checks are the whole count:
 *        - the lane as it is: `accounts.login_limit` is a warning on every lane (`dev.py server --test` sets
 *          LIBREFOLIO_LOGIN_LIMIT=off), read first through the administrator's own session as a precondition, so the
 *          dot is always drawn there and its link followed. The exact count is taken from the read the page itself made,
 *          not from the test's: `platform.client_address` reports the forwarding headers a uvicorn process has met —
 *          this file's X-Forwarded-For case sends some, which turns it into a warning (security-tab.spec.ts) — and each
 *          process keeps its own, one per two browser workers on a lane: two reads a moment apart may disagree on it
 *          (security-tab.spec.ts, for the same reason, compares a badge only with what its own page lists);
 *        - stubbed in the page (`page.route`, nothing reaches the server): one error and two warnings, an info and an
 *          ok besides → 3, error; warnings only → 1, warning; every check ok → 0, none. Before its answer the line says
 *          0 as well, so that zero is read only once Settings › Security, which reads the same store, has settled on
 *          the stubbed answer (`data-status="ready"`, all clear);
 *        - a member (TEST_USER): 0, none, no dot, and no read of the checks through a sign-in, a page load and a
 *          navigation.
 *      Each administrator's sign-in document is closed (`about:blank`) before a recorder or a stub is armed: the one
 *      read a page load owes is counted on that load alone, never mixed with a read still in flight from the sign-in.
 *
 * Waiting: on the attributes the line publishes — `data-server-checked`, then `data-level` and `data-reason` — never on
 * the clock, never on text. The dot is read before the sidebar opens, on the burger the user sees.
 *
 * Offline and read-only: every origin but the app's own is refused, and TEST_USER only reads (the line's GET), as does
 * TEST_ADMIN (the checks are a GET too, and a stub answers them in the page's own context), so the one state a test
 * changes is its own browser context: cookies, extra headers, routes and, once, the sidebar's collapsed flag in its
 * local storage. Routes are removed after each test.
 *
 * Why `test.use` sits at the top of the file and not in the describe of the mapped names: `launchOptions` is a
 * worker-scoped option, and Playwright refuses one inside a describe ("Cannot use({ launchOptions }) in a describe
 * group, because it forces a new worker"). The rules map the two names above and nothing else, so the localhost case is
 * untouched by them; the config's own launch options are kept.
 */
import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {readOnboardingProgress} from '../fixtures/onboarding-accounts';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';

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

/** Signs `user` in with the shared helper, then waits for the root's post-login routing to leave `/`: the app shell is up. */
async function signInOnBaseURL(page: Page, user: typeof TEST_USER = TEST_USER): Promise<void> {
    await login(page, user);
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
async function expectNoOnboardingDue(page: Page, user: typeof TEST_USER = TEST_USER): Promise<void> {
    const due = (await readOnboardingProgress(page)).filter((item) => item.status === 'pending' || item.version < item.current_version).map((item) => item.flow);
    expect(due, `precondition: ${user.username} is grandfathered completed on every onboarding flow (populate_mock_data _grandfather_onboarding_for_test_users)`).toEqual([]);
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

// ── N69-1: the security-attention dot of an administrator (item 4 of the header) ─────────────────────────────────────

const CHECKS_PATH = '/api/v1/security/checks';
const isChecksUrl = (url: URL): boolean => url.pathname === CHECKS_PATH;
/** Off on every lane (`dev.py server --test` sets LIBREFOLIO_LOGIN_LIMIT=off): a warning, in every server process. */
const LOGIN_LIMIT = 'accounts.login_limit';
/** Where the details' link leads: Settings › Security. */
const SECURITY_TAB_HREF = '/settings?tab=security';
/** Loopback names: local hosts for the open-registration finding (`isLocalHost`), which the browser then never adds. */
const LOOPBACK_HOST = /^(?:localhost|127(?:\.\d{1,3}){3}|\[::1\])$/;
/** From a page load to the line's word on the checks: the bootstrap, the line's mount, then one GET, on a loaded lane. */
const CHECKS_TIMEOUT_MS = 20_000;

type CheckSeverity = 'ok' | 'info' | 'warning' | 'error';
/** A check as `GET /api/v1/security/checks` lists it (`SecurityCheckRead`, backend/app/schemas/security.py). */
type SecurityCheck = {check_id: string; severity: CheckSeverity; i18n_key: string; detail: Record<string, string | number>};
/** What the line says of the checks, on its root: `data-security-attention` and `data-security-severity`. */
type AttentionSeverity = 'error' | 'warning' | 'none';
type Attention = {count: number; severity: AttentionSeverity};
/** An answer to the page's reads of the checks, and what the line owes an administrator for it under a loopback name. */
type ChecksStub = {items: SecurityCheck[]; attention: Attention};
/** What the page was answered when it read the checks: the status, and the list once its body is parsed. */
type ChecksAnswer = {status: number; items: SecurityCheck[] | null; problem: string | null};

const NO_ATTENTION: Attention = {count: 0, severity: 'none'};

/** One error and two warnings; an info, which the tab lists and the count leaves out, and an ok besides. */
const STUB_ERROR: ChecksStub = {
    items: [
        {check_id: 'platform.instance_key', severity: 'error', i18n_key: 'instance.checks.instanceKey.unusable', detail: {source: 'generated', reason: 'an E2E stub'}},
        {check_id: 'platform.session_cookie', severity: 'warning', i18n_key: 'instance.checks.sessionCookie.never', detail: {}},
        {check_id: LOGIN_LIMIT, severity: 'warning', i18n_key: 'auth.checks.loginLimit.off', detail: {}},
        {check_id: 'platform.log_level', severity: 'info', i18n_key: 'instance.checks.logLevel.verbose', detail: {log_level: 'DEBUG'}},
        {check_id: 'platform.jwt_secret', severity: 'ok', i18n_key: 'instance.checks.jwtSecret.ok', detail: {}},
    ],
    attention: {count: 3, severity: 'error'},
};

/** Warnings only — one —, and an ok. */
const STUB_WARNING: ChecksStub = {
    items: [
        {check_id: LOGIN_LIMIT, severity: 'warning', i18n_key: 'auth.checks.loginLimit.off', detail: {}},
        {check_id: 'platform.jwt_secret', severity: 'ok', i18n_key: 'instance.checks.jwtSecret.ok', detail: {}},
    ],
    attention: {count: 1, severity: 'warning'},
};

/** Every check ok: nothing asks for the administrator. */
const STUB_ALL_OK: ChecksStub = {
    items: [
        {check_id: 'platform.jwt_secret', severity: 'ok', i18n_key: 'instance.checks.jwtSecret.ok', detail: {}},
        {check_id: 'platform.session_cookie', severity: 'ok', i18n_key: 'instance.checks.sessionCookie.ok', detail: {}},
        {check_id: LOGIN_LIMIT, severity: 'ok', i18n_key: 'auth.checks.loginLimit.ok', detail: {}},
    ],
    attention: NO_ATTENTION,
};

/**
 * What the line owes an administrator for `checks` under a loopback name: the errors and the warnings — an info is listed
 * by the tab and never counted —, with the severity `error` if one of them is an error, else `warning`; `none` with zero.
 */
function attentionOf(checks: readonly SecurityCheck[]): Attention {
    const errors = checks.filter((check) => check.severity === 'error').length;
    const count = errors + checks.filter((check) => check.severity === 'warning').length;
    return {count, severity: errors > 0 ? 'error' : count > 0 ? 'warning' : 'none'};
}

/** `check_id:severity` of each check, in order: what a failure message shows of a list of checks. */
function describeChecks(checks: readonly SecurityCheck[]): string {
    return JSON.stringify(checks.map((check) => `${check.check_id}:${check.severity}`));
}

/** The account the browser is signed in as, through the page's own cookies. */
async function signedInAs(page: Page): Promise<{username: string; is_superuser: boolean}> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.status(), 'GET /auth/me through the browser session').toBe(200);
    return ((await response.json()) as {user: {username: string; is_superuser: boolean}}).user;
}

/** Precondition, read back: the page is served under a loopback name, so the browser adds no finding of its own. */
function expectLocalHost(page: Page): void {
    const host = new URL(page.url()).hostname;
    expect(host, 'precondition: the lane is reached under a loopback name, a local host for the open-registration finding (openRegistrationNoticeFor): the server’s checks are the whole count').toMatch(LOOPBACK_HOST);
}

/**
 * Signs TEST_ADMIN in on the baseURL and reads back what the expectations rest on: an administrator, nothing of
 * onboarding due, a loopback host. Then it closes the sign-in's document (`about:blank`): a read of the checks it still
 * had in flight can reach neither a recorder nor a stub armed next, which see the next page load alone.
 */
async function signInAdmin(page: Page): Promise<void> {
    await signInOnBaseURL(page, TEST_ADMIN);
    expect(await signedInAs(page), `${TEST_ADMIN.username} must be an administrator`).toMatchObject({username: TEST_ADMIN.username, is_superuser: true});
    await expectNoOnboardingDue(page, TEST_ADMIN);
    expectLocalHost(page);
    await page.goto('about:blank');
}

/** The checks as the lane's server evaluates them now, read through the page's own session: an administrator's. */
async function laneChecks(page: Page): Promise<SecurityCheck[]> {
    const response = await page.request.get(CHECKS_PATH);
    expect(response.status(), `GET ${CHECKS_PATH} as ${TEST_ADMIN.username}: ${await response.text()}`).toBe(200);
    return ((await response.json()) as {items: SecurityCheck[]}).items;
}

/**
 * Records, from now on, every read of the checks the page makes — the method of each request — and the answer of each,
 * its body parsed as soon as it is in. `stop()` detaches the listeners.
 */
function recordChecksReads(page: Page): {requests: string[]; answers: Promise<ChecksAnswer>[]; stop: () => void} {
    const requests: string[] = [];
    const answers: Promise<ChecksAnswer>[] = [];
    const onRequest = (request: Request): void => {
        if (isChecksUrl(new URL(request.url()))) requests.push(request.method());
    };
    const onResponse = (response: Response): void => {
        if (!isChecksUrl(new URL(response.url()))) return;
        answers.push(
            response.json().then(
                (body: {items?: unknown}): ChecksAnswer => ({status: response.status(), items: Array.isArray(body.items) ? (body.items as SecurityCheck[]) : null, problem: null}),
                (error: unknown): ChecksAnswer => ({status: response.status(), items: null, problem: String(error)}),
            ),
        );
    };
    page.on('request', onRequest);
    page.on('response', onResponse);
    return {
        requests,
        answers,
        stop: () => {
            page.off('request', onRequest);
            page.off('response', onResponse);
        },
    };
}

/**
 * Answers every read of the checks the page makes with `stub`, in the API's shape (`SecurityChecksResponse`), and counts
 * them. In the page's own context: nothing reaches the server, nothing is written; the describe's afterEach removes it.
 */
async function stubChecks(page: Page, stub: ChecksStub): Promise<() => number> {
    let served = 0;
    await page.route(isChecksUrl, async (route) => {
        served += 1;
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({items: stub.items})});
    });
    return () => served;
}

/**
 * The line's word on the administrator's checks, on its root (N69-1). The first read waits for the answer: before it, as
 * for a member, the line says 0. A positive count is its own presence barrier; a zero needs one from the caller.
 */
async function expectAttention(page: Page, expected: Attention): Promise<void> {
    const line = page.getByTestId('connection-security');
    await expect(line, `the line publishes on its root how many security checks ask for attention: data-security-attention="${expected.count}" (N69-1)`).toHaveAttribute('data-security-attention', String(expected.count), {timeout: CHECKS_TIMEOUT_MS});
    await expect(line, `and the severity of the worst of them: data-security-severity="${expected.severity}"`).toHaveAttribute('data-security-severity', expected.severity);
}

/** The dot on the line's icon, the sidebar expanded or collapsed: drawn with the severity it carries, or — `none` — not drawn. */
async function expectLineDot(page: Page, severity: AttentionSeverity): Promise<void> {
    const toggle = page.getByTestId('connection-security-toggle');
    await expect(toggle, 'presence barrier: the line is drawn').toBeVisible();
    const dot = toggle.getByTestId('connection-security-attention-dot');
    if (severity === 'none') {
        await expect(dot, 'nothing asks for attention: no dot on the line').toBeHidden();
        return;
    }
    await expect(dot, 'the checks ask for the administrator: a dot on the line’s icon (N69-1)').toBeVisible();
    await expect(dot, `in the severity of the worst of them: data-severity="${severity}"`).toHaveAttribute('data-severity', severity);
    await expect(dot, 'a dot, not a number (D3 a)').toHaveText('');
}

/**
 * On a phone: the burger's dot, read with the sidebar closed, the burger being what the user sees. On the lane's secure
 * loopback its severity is the attention's (an insecure connection would make it `error`); `none`: no dot.
 */
async function expectMenuAttentionDot(page: Page, severity: AttentionSeverity): Promise<void> {
    await expect(page.getByTestId('app-header'), 'precondition: the sidebar is closed, so the burger is what the user sees').toHaveAttribute('data-sidebar-open', 'false');
    const burger = page.getByTestId('mobile-menu-toggle');
    await expect(burger, 'presence barrier: the burger is on screen').toBeVisible();
    const dot = burger.getByTestId('mobile-menu-security-dot');
    if (severity === 'none') {
        await expect(dot, 'a secure connection, and nothing asks for attention: no dot on the burger').toBeHidden();
        return;
    }
    await expect(dot, 'the administrator’s checks ask for attention: the burger carries the dot too (N69-1, D2 a)').toBeVisible();
    await expect(dot, `in the severity of the worst of them: data-severity="${severity}"`).toHaveAttribute('data-severity', severity);
    await expect(dot, 'a dot, not a number (D3 a)').toHaveText('');
}

/** Opens the line's details — on a phone the burger opens the sidebar first — and returns them, their reason drawn. */
async function openDetails(page: Page, mobile: boolean): Promise<Locator> {
    if (mobile) await openSidebar(page);
    const toggle = page.getByTestId('connection-security-toggle');
    await expect(toggle, 'the details start closed').toHaveAttribute('aria-expanded', 'false');
    await toggle.click();
    await expect(toggle, 'a click opens the details').toHaveAttribute('aria-expanded', 'true');
    const details = page.getByTestId('connection-security-details');
    await expect(details).toBeVisible();
    await expect(details.getByTestId('connection-security-reason'), 'presence barrier: the reason, first in the details, is drawn').toBeVisible();
    return details;
}

test.describe('An administrator: the security dot (N69-1)', () => {
    // A sign-in on a loaded lane can take most of 30 s by itself (login()'s ARRIVAL_MS); then a page load, the checks, and
    // in ADOT-E-01 a second page: security-tab.spec.ts's budget.
    test.describe.configure({timeout: 90_000});

    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
    });

    test('ADOT-E-01: the lane as it is — the line counts the errors and warnings of the one read the page made, the dot of the worst on its icon; its link opens Settings › Security and closes the details', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        await signInAdmin(page);
        // The precondition, through the administrator's own session before anything on screen: the lane asks for
        // attention, so here the dot is drawn and its link followed. The branch without attention is ADOT-E-03's.
        const lane = await laneChecks(page);
        expect(lane.find((check) => check.check_id === LOGIN_LIMIT)?.severity, `precondition: every lane runs with LIBREFOLIO_LOGIN_LIMIT=off (dev.py server --test), so ${LOGIN_LIMIT} is a warning: ${describeChecks(lane)}`).toBe('warning');

        const reads = recordChecksReads(page);
        try {
            await navigateTo(page, '/dashboard');
            await expectVerdict(page, 'secure', 'localhost');
            await expect(page.getByTestId('connection-security'), 'an administrator’s line publishes how many checks ask for attention: data-security-attention, at least 1 on the lane (N69-1)').toHaveAttribute('data-security-attention', /^[1-9]\d*$/, {
                timeout: CHECKS_TIMEOUT_MS,
            });

            // The exact expectation comes from the read the page made (see the header): one, for this page load.
            await expect.poll(() => reads.answers.length, {message: 'the read of the checks the line asked for is answered', timeout: CHECKS_TIMEOUT_MS}).toBeGreaterThan(0);
            expect(reads.requests, 'the line reads the administrator’s checks once per page load').toEqual(['GET']);
            const answer = await reads.answers[0];
            expect(answer, `the page's read of ${CHECKS_PATH}: a 200 with a list of checks`).toMatchObject({status: 200, problem: null});
            const items = answer.items ?? [];
            expect(items.find((check) => check.check_id === LOGIN_LIMIT)?.severity, `the page's read agrees with the precondition: ${describeChecks(items)}`).toBe('warning');
            const expected = attentionOf(items);
            await expectAttention(page, expected);

            if (mobile) await expectMenuAttentionDot(page, expected.severity);
            const details = await openDetails(page, mobile);
            await expectLineDot(page, expected.severity);
            const link = details.getByTestId('connection-security-attention-link');
            await expect(link, 'with attention, the details link Settings › Security after the reason').toBeVisible();
            await expect(link).toHaveAttribute('href', SECURITY_TAB_HREF);

            await link.click();
            await expect(page, 'the link opens Settings').toHaveURL((url) => url.pathname === '/settings', {timeout: CHECKS_TIMEOUT_MS});
            await expect(page.getByTestId('settings-tab-administration'), '… inside «Administration»').toHaveAttribute('aria-selected', 'true', {timeout: CHECKS_TIMEOUT_MS});
            await expect(page.getByTestId('settings-subtabs').getByTestId('settings-tab-security'), '… on Security').toHaveAttribute('aria-selected', 'true', {timeout: CHECKS_TIMEOUT_MS});
            const body = page.getByTestId('security-tab');
            await expect(body, 'the tab settles').toHaveAttribute('data-status', 'ready', {timeout: CHECKS_TIMEOUT_MS});
            await expect(body).toHaveAttribute('data-busy', 'false');
            await expect(page.getByTestId('connection-security-toggle'), 'the link closed the details').toHaveAttribute('aria-expanded', 'false');
            await expect(page.getByTestId('connection-security-details')).toBeHidden();
            // One read for the whole page: the tab lists the very checks the line counted, and nothing read them again.
            const attentionListed = body.locator('[data-testid="security-finding"][data-severity="error"], [data-testid="security-finding"][data-severity="warning"]');
            await expect.poll(() => attentionListed.count(), {message: 'the tab lists as many errors and warnings as the line counted: the same read', timeout: CHECKS_TIMEOUT_MS}).toBe(expected.count);
            expect(reads.requests, 'still one read: the Settings page and its tab took the line’s').toEqual(['GET']);
        } finally {
            reads.stop();
        }
    });

    test('ADOT-E-02: stubbed, one error and two warnings (an info and an ok besides) — 3 and error: the dot on the line, expanded and collapsed, and on a phone’s burger; the details link Settings › Security', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        await signInAdmin(page);
        const served = await stubChecks(page, STUB_ERROR);
        await navigateTo(page, '/dashboard');
        await expectVerdict(page, 'secure', 'localhost');
        await expectAttention(page, STUB_ERROR.attention);

        if (mobile) await expectMenuAttentionDot(page, 'error');
        const details = await openDetails(page, mobile);
        await expectLineDot(page, 'error');
        const link = details.getByTestId('connection-security-attention-link');
        await expect(link, 'with attention, the details link Settings › Security after the reason').toBeVisible();
        await expect(link).toHaveAttribute('href', SECURITY_TAB_HREF);

        if (!mobile) {
            // Collapsed, the line is its icon alone: the dot stays on it.
            const label = page.getByTestId('connection-security-label');
            await expect(label, 'precondition: the sidebar is expanded, the line shows its label').toBeVisible();
            await page.getByTestId('sidebar-collapse-toggle').click();
            await expect(page.getByTestId('connection-security-toggle'), 'presence barrier: collapsed, the line is still drawn').toBeVisible();
            await expect(label, 'the sidebar collapsed: the line is its icon alone').toHaveCount(0);
            await expectLineDot(page, 'error');
        }
        expect(served(), 'one read of the checks for the page load, answered by the stub').toBe(1);
    });

    test('ADOT-E-03: stubbed, every check ok — 0 and none once Settings › Security has the same answer: no dot on the line nor on a phone’s burger, no link in the details', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        await signInAdmin(page);
        const served = await stubChecks(page, STUB_ALL_OK);
        await navigateTo(page, SECURITY_TAB_HREF);
        // The barrier: before its answer the line says 0 too, so its zero means something only once the answer is in.
        // The tab reads the same store, and says so: ready, and all clear.
        const body = page.getByTestId('security-tab');
        await expect(body, 'Settings › Security settles on the stubbed answer').toHaveAttribute('data-status', 'ready', {timeout: CHECKS_TIMEOUT_MS});
        await expect(body.getByTestId('security-all-clear'), 'every check ok: the tab says all clear').toBeVisible();
        await expectVerdict(page, 'secure', 'localhost');
        await expectAttention(page, STUB_ALL_OK.attention);

        if (mobile) await expectMenuAttentionDot(page, 'none');
        const details = await openDetails(page, mobile);
        await expectLineDot(page, 'none');
        await expect(details.getByTestId('connection-security-docs-link'), 'presence barrier: the details are drawn, down to the user page').toBeVisible();
        await expect(details.getByTestId('connection-security-attention-link'), 'nothing asks for the administrator: no link to Settings › Security').toBeHidden();
        expect(served(), 'one read of the checks for the page load — the line, the page and its tab share it —, answered by the stub').toBe(1);
    });

    test('ADOT-E-04: stubbed, warnings only — 1 and warning: the dot on the line and, on a phone, on the burger, data-severity warning', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        await signInAdmin(page);
        const served = await stubChecks(page, STUB_WARNING);
        await navigateTo(page, '/dashboard');
        await expectVerdict(page, 'secure', 'localhost');
        await expectAttention(page, STUB_WARNING.attention);

        if (mobile) {
            await expectMenuAttentionDot(page, 'warning');
            await openSidebar(page);
        }
        await expectLineDot(page, 'warning');
        expect(served(), 'one read of the checks for the page load, answered by the stub').toBe(1);
    });

    test('ADOT-E-05: a member — 0 and none, no dot on the line nor on a phone’s burger, and no read of the checks through a sign-in, a page load and a navigation', async ({page, baseURL}, testInfo) => {
        const mobile = testInfo.project.name === 'mobile';
        await keepOffline(page, laneBaseURL(baseURL).origin);
        // Every read of the checks from the first page on: the line asks for them for an administrator only.
        const reads = recordChecksReads(page);
        try {
            await signInOnBaseURL(page);
            expect(await signedInAs(page), `${TEST_USER.username} must be an ordinary member`).toMatchObject({username: TEST_USER.username, is_superuser: false});
            await expectNoOnboardingDue(page);

            await navigateTo(page, '/dashboard');
            // Presence first: the line has mounted and the server answered it — by then an administrator's line has
            // asked for the checks too.
            await expectVerdict(page, 'secure', 'localhost');
            await expectAttention(page, NO_ATTENTION);
            if (mobile) {
                await expectMenuAttentionDot(page, 'none');
                await openSidebar(page);
            }
            await expectLineDot(page, 'none');

            // A navigation inside the app, to the page that reads the checks for an administrator.
            await page.getByTestId('nav-settings').click();
            await expect(page, 'the sidebar link opens Settings').toHaveURL((url) => url.pathname === '/settings', {timeout: PAGE_TIMEOUT_MS});
            await expect(page.getByTestId('settings-tab-about'), 'presence: the member’s Settings is drawn, up to About').toBeVisible({timeout: PAGE_TIMEOUT_MS});
            await expectAttention(page, NO_ATTENTION);
            await expectLineDot(page, 'none');
            if (mobile) await expectMenuAttentionDot(page, 'none');
            expect(reads.requests, 'a member’s app never reads the administrators’ checks').toEqual([]);
        } finally {
            reads.stop();
        }
    });
});
