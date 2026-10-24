/**
 * Settings › Security, the administrators' tab (release 1.3, workstream A, lot A8b), inside the «Administration» group of
 * the tab bar (decision P13 b).
 *
 * The tab lists the configuration checks of the instance (`GET /api/v1/security/checks`, administrators only) and the
 * browser's own: what asks for attention first, most severe first (`security-finding`, with `data-check-id` and
 * `data-severity`), the passed checks folded below (`security-passed`). It publishes its read on its root, `security-tab`
 * (`data-status` idle | loading | ready | error, `data-busy`). The page reads the checks when it opens (the registry's
 * `prefetch`), before the tab is: the tab's badge — its errors and warnings — and the group's, the sum of its members',
 * show without opening anything.
 *
 * The lane: its server runs with `LIBREFOLIO_LOGIN_LIMIT=off` (`dev.py server --test` sets it unless the variable is set),
 * so `accounts.login_limit` is a warning there — the finding this spec leans on, read first from the API as a
 * precondition, as test_security_checks_api.py pins it on the backend. Other checks may change while the run goes on:
 * `platform.client_address` turns into a warning once a request with forwarding headers has reached the server
 * (connection-security.spec.ts sends one). So nothing here holds the findings to a number of its own: a badge is read
 * from its tab, and compared only with what the same page lists.
 *
 * Covered, through the real page and the lane's real backend:
 *   ASEC-E-01  an administrator: «Administration» shows a badge of at least 1 before anything of the group is opened;
 *              Security, opened through the group, settles ready — `accounts.login_limit` listed as a warning, the passed
 *              checks folded below, not «all clear» —; its own badge counts the errors and warnings it lists, and the
 *              group's includes it;
 *   ASEC-E-02  `?tab=security` opens Security inside its group; «check again» reads the checks again — the request held
 *              until the tab has been seen loading, the last checks still listed meanwhile —, then ready, the login-limit
 *              warning still there;
 *   ASEC-E-03  a member has no «Administration» group (N69-2, decision D4 a) — no Security tab, no badge, no read of
 *              the checks —, and `?tab=security` opens Profile without mounting the tab;
 *   ASEC-E-04  the login-limit warning has a «Guide» button (N69d) that opens the guide's page on its anchor in a new tab.
 *
 * Read-only, parallel by default: GET requests, and the sign-ins of the two fixture users of `populate_mock_data.py`,
 * whose roles are checked, never changed; no setting is touched. The one route (ASEC-E-02) is the page's own, removed by
 * its test.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `security-tab` of front-utility.
 */
import type {Route} from '@playwright/test';
import {expect, type Locator, type Page, type Request, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {openSettingsTab} from '../fixtures/settings-tabs';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';

const CHECKS_PATH = '/api/v1/security/checks';
const isChecks = (url: URL): boolean => url.pathname === CHECKS_PATH;
/** Off on the lane: a warning, which the badges count. */
const LOGIN_LIMIT = 'accounts.login_limit';
/** The one check that may change during the run: ok until a request with forwarding headers reaches the server. */
const CLIENT_ADDRESS = 'platform.client_address';

// Budgets: deadlines, never delays.
/** From a navigation to a settled tab: the SPA's load, the auth check and the bootstrap, then GET /security/checks. */
const LOAD_MS = 20_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

/** A check as `GET /api/v1/security/checks` lists it (`SecurityCheck`, securityChecksApi.ts). */
type SecurityCheck = {check_id: string; severity: 'ok' | 'info' | 'warning' | 'error'; i18n_key: string; detail: Record<string, unknown>};

// A sign-in on a loaded lane can take most of 30 s by itself (login()'s ARRIVAL_MS, V-27); a test then loads the page
// once or twice and waits for a read of the checks.
test.setTimeout(90_000);

/** The account the browser is signed in as, through the page's own cookies. */
async function signedInAs(page: Page): Promise<{username: string; is_superuser: boolean}> {
    const response = await page.request.get('/api/v1/auth/me');
    expect(response.status(), 'GET /auth/me through the browser session').toBe(200);
    return ((await response.json()) as {user: {username: string; is_superuser: boolean}}).user;
}

/** The checks as the lane's server evaluates them now, read through the page's own session: an administrator's. */
async function laneChecks(page: Page): Promise<SecurityCheck[]> {
    const response = await page.request.get(CHECKS_PATH);
    expect(response.status(), `GET ${CHECKS_PATH} as ${TEST_ADMIN.username}: ${await response.text()}`).toBe(200);
    return ((await response.json()) as {items: SecurityCheck[]}).items;
}

/**
 * The number a tab's badge shows: `data-badge` of the badge TabBar draws inside the tab's button
 * (`data-testid="tab-badge"`); 0 when the tab draws none — TabBar leaves the element out when there is nothing to count.
 * A one-shot read, for `expect.poll` to retry. A badge that breaks that contract — two in one tab, or a `data-badge` that
 * is not a count — throws, and ends a poll around it at once: no wait would mend it.
 */
async function tabBadge(tab: Locator): Promise<number> {
    const values = await tab.getByTestId('tab-badge').evaluateAll((badges) => badges.map((badge) => badge.getAttribute('data-badge')));
    if (values.length === 0) return 0;
    const [value] = values;
    if (values.length > 1 || value === null || !/^\d+$/.test(value)) throw new Error(`A tab draws at most one tab-badge, whose data-badge is its count: found the data-badge values ${JSON.stringify(values)}`);
    return Number(value);
}

/** The findings `body` lists, as `check_id:severity`, in their order on screen. */
async function listedFindings(body: Locator): Promise<string[]> {
    return body.getByTestId('security-finding').evaluateAll((items) => items.map((item) => `${item.getAttribute('data-check-id')}:${item.getAttribute('data-severity')}`));
}

/** The listed findings that ask for the administrator, errors and warnings: what the badge counts (an `info` never is). */
function attentionFindings(body: Locator): Locator {
    return body.locator('[data-testid="security-finding"][data-severity="error"], [data-testid="security-finding"][data-severity="warning"]');
}

/** The finding of check `checkId` in `body`. */
function finding(body: Locator, checkId: string): Locator {
    return body.locator(`[data-testid="security-finding"][data-check-id="${checkId}"]`);
}

test.describe('Settings › Security — an administrator', () => {
    test('ASEC-E-01: «Administration» shows the badge before anything is opened; Security, opened through the group, lists the login-limit warning and folds the passed checks', async ({page}) => {
        await login(page, TEST_ADMIN);
        expect(await signedInAs(page), `${TEST_ADMIN.username} must be an administrator`).toMatchObject({username: TEST_ADMIN.username, is_superuser: true});
        // The preconditions, read from the lane's server before anything on screen.
        const checks = await laneChecks(page);
        const seen = JSON.stringify(checks.map((check) => `${check.check_id}:${check.severity}`));
        expect(checks.find((check) => check.check_id === LOGIN_LIMIT)?.severity, `precondition: the lane's server runs with LIBREFOLIO_LOGIN_LIMIT=off (dev.py server --test sets it unless the variable is set), so ${LOGIN_LIMIT} is a warning: ${seen}`).toBe('warning');
        const passing = checks.filter((check) => check.severity === 'ok' && check.check_id !== CLIENT_ADDRESS).map((check) => check.check_id);
        expect(passing, `precondition: at least one check of the lane passes for the whole run (${CLIENT_ADDRESS} aside, which may turn): ${seen}`).not.toEqual([]);

        await navigateTo(page, '/settings');
        const group = page.getByTestId('settings-tab-administration');
        await expect(group, 'the top bar holds «Administration»').toBeVisible({timeout: LOAD_MS});
        await expect(page.getByTestId('settings-tab-profile'), 'precondition: /settings opens on Profile, nothing of the group open').toHaveAttribute('aria-selected', 'true');
        await expect(group).toHaveAttribute('aria-selected', 'false');

        // The page reads the checks as it opens: the group's badge shows before Security is opened.
        await expect.poll(() => tabBadge(group), {message: '«Administration» shows a badge of at least 1 — the login-limit warning — before anything of the group is opened', timeout: LOAD_MS}).toBeGreaterThanOrEqual(1);
        await expect(page.getByTestId('security-tab'), 'the badge came from the page, not from the tab: its body is not mounted').toHaveCount(0);

        await openSettingsTab(page, 'security');
        const own = page.getByTestId('settings-subtabs').getByTestId('settings-tab-security');
        await expect(own, 'Security is the open tab of the second bar').toHaveAttribute('aria-selected', 'true');
        await expect(group, 'its group stays the selected entry of the top bar').toHaveAttribute('aria-selected', 'true');

        const body = page.getByTestId('security-tab');
        await expect(body, 'the tab settles: GET /security/checks is in').toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        await expect(body).toHaveAttribute('data-busy', 'false');
        await expect(finding(body, LOGIN_LIMIT), 'the login limit, off on the lane, asks for attention as a warning').toHaveAttribute('data-severity', 'warning');
        await expect(body.getByTestId('security-passed'), 'the passed checks are folded below the findings').toBeVisible();
        // Folded: listed, inside a closed <details>, so attached rather than visible.
        await expect(body.locator(`[data-testid="security-passed-check"][data-check-id="${passing[0]}"]`), `${passing[0]}, ok on the lane, is among them`).toBeAttached();
        // The warning above is the presence barrier of the absences: something is listed, so not «all clear», and the
        // read did not fail.
        await expect(body.getByTestId('security-all-clear')).toHaveCount(0);
        await expect(body.getByTestId('security-load-error')).toHaveCount(0);

        // The badges, each read from its tab: Security's counts the errors and warnings it lists, and the group's — the sum
        // of its members' — includes it.
        await expect
            .poll(async () => (await tabBadge(own)) - (await attentionFindings(body).count()), {
                message: "Security's badge less the errors and warnings it lists: the badge counts exactly those",
                timeout: UI_MS,
            })
            .toBe(0);
        expect(await tabBadge(group), "«Administration»'s badge, the sum of its members', includes Security's").toBeGreaterThanOrEqual(await tabBadge(own));
    });

    test('ASEC-E-02: ?tab=security opens Security inside its group; «check again» reads the checks again, the last ones listed meanwhile', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings?tab=security');
        await expect(page.getByTestId('settings-tab-administration'), '?tab=security selects its group in the top bar').toHaveAttribute('aria-selected', 'true', {timeout: LOAD_MS});
        await expect(page.getByTestId('settings-subtabs').getByTestId('settings-tab-security'), '?tab=security opens Security, in the second bar').toHaveAttribute('aria-selected', 'true', {timeout: UI_MS});
        const body = page.getByTestId('security-tab');
        await expect(body, 'the tab settles: GET /security/checks is in').toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        const loginLimit = finding(body, LOGIN_LIMIT);
        await expect(loginLimit, 'precondition: the login limit is off on the lane, a warning (see the header)').toHaveAttribute('data-severity', 'warning');
        const before = await listedFindings(body);

        // The next read is held until the tab has been seen reading: a state the test controls, not a moment it races.
        const reads: string[] = [];
        let release: () => void = () => undefined;
        const released = new Promise<void>((resolve) => {
            release = () => resolve();
        });
        const hold = async (route: Route) => {
            reads.push(route.request().method());
            await released;
            await route.continue();
        };
        await page.route(isChecks, hold);
        try {
            const refresh = page.getByTestId('security-refresh');
            await expect(refresh).toBeEnabled();
            await refresh.click();

            await expect.poll(() => [...reads], {message: '«check again» reads GET /security/checks again', timeout: UI_MS}).toEqual(['GET']);
            await expect(body, 'reading: the tab says so').toHaveAttribute('data-status', 'loading');
            await expect(body).toHaveAttribute('data-busy', 'true');
            await expect(refresh, 'one read at a time').toBeDisabled();
            // The last checks stay listed while it reads: the same findings, and no placeholder in their place.
            await expect.poll(() => listedFindings(body), {message: 'while it reads, the tab keeps listing the last checks', timeout: UI_MS}).toEqual(before);
            await expect(body.getByTestId('security-loading')).toHaveCount(0);
            release();

            await expect(body, 'the second read lands').toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
            await expect(body).toHaveAttribute('data-busy', 'false');
            await expect(refresh).toBeEnabled();
            await expect(loginLimit, 'the login-limit warning is listed again').toHaveAttribute('data-severity', 'warning');
            await expect(body.getByTestId('security-load-error')).toHaveCount(0);
            expect(reads, 'one read for one click').toEqual(['GET']);
        } finally {
            release();
            await page.unroute(isChecks, hold);
        }
    });
    test("ASEC-E-04: the login-limit warning has a «Guide» button — a book — that opens the page of the administrator's guide on its anchor, in a new tab", async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings?tab=security');
        const body = page.getByTestId('security-tab');
        await expect(body, 'the tab settles: GET /security/checks is in').toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        const loginLimit = finding(body, LOGIN_LIMIT);
        await expect(loginLimit, 'precondition: the login limit is off on the lane, a warning (see the header)').toHaveAttribute('data-severity', 'warning');

        const guide = loginLimit.getByTestId('security-guide');
        await expect(guide, 'the finding carries its guide next to its message').toBeVisible({timeout: UI_MS});
        // `window.open(…, 'noopener')`: the new tab belongs to the context, not to this page
        const opened = page.context().waitForEvent('page');
        await guide.click();
        const tab = await opened;
        try {
            const url = new URL(tab.url());
            // The user's language precedes the path unless it is English; the anchor is the English page's, whatever the language
            expect(url.pathname, 'the page of the guide that explains the login limit').toMatch(/^\/mkdocs\/(?:(?:it|fr|es)\/)?admin\/configuration_accounts\/$/);
            expect(url.hash, 'on its anchor').toBe('#login-limit');
        } finally {
            await tab.close();
        }
        await expect(page.getByTestId('security-tab'), 'the Settings tab stays where it was').toBeVisible();
    });
});

test.describe('Settings › Security — a member of the instance', () => {
    test('ASEC-E-03: a member has no «Administration» group — no Security tab, no badge, no read of the checks —, and ?tab=security opens Profile', async ({page}) => {
        await login(page, TEST_USER);
        expect(await signedInAs(page), `${TEST_USER.username} must be an ordinary member`).toMatchObject({username: TEST_USER.username, is_superuser: false});

        // Every read of the checks this page would make: the page asks for them only for an administrator.
        const checkReads: string[] = [];
        const recordCheckRead = (request: Request) => {
            if (isChecks(new URL(request.url()))) checkReads.push(request.method());
        };
        page.on('request', recordCheckRead);
        try {
            await navigateTo(page, '/settings');
            // Presence first: the top bar is drawn, up to About, the last tab every account sees, and /settings opens
            // on Profile. The bar's entries come from one derivation, and a member's context never turns administrator:
            // an «Administration» entry would be drawn with them, or never.
            await expect(page.getByTestId('settings-tab-about'), 'the top bar is drawn for the member, up to About').toBeVisible({timeout: LOAD_MS});
            await expect(page.getByTestId('settings-tab-profile'), 'precondition: /settings opens on Profile').toHaveAttribute('aria-selected', 'true');
            // Then the absences, left out of the page rather than hidden in it: «Administration» and every member of
            // it are an administrator's alone (N69-2, decision D4 a).
            await expect(page.getByTestId('settings-tab-administration'), 'a member has no «Administration» group').toHaveCount(0);
            await expect(page.getByTestId('settings-tab-security'), 'so no Security tab anywhere').toHaveCount(0);
            await expect(page.getByTestId('settings-subtabs'), 'and no second bar').toHaveCount(0);
            // A badge is drawn with its tab, in the same update, and only the checks could fill one later: the recorder
            // below proves they are never read. No settings body holds a tab bar: a badge here could only be a tab's.
            await expect(page.getByTestId('settings-page').getByTestId('tab-badge'), "no tab of a member's Settings draws a badge: what Security's counts, the checks, is the administrators'").toHaveCount(0);

            await navigateTo(page, '/settings?tab=security');
            const profile = page.getByTestId('settings-tab-profile');
            await expect(profile, '?tab=security names no tab of a member: the first one, Profile, opens').toHaveAttribute('aria-selected', 'true', {timeout: LOAD_MS});
            await expect(page.getByTestId('profile-tab')).toBeVisible({timeout: UI_MS});
            // Presence above — Profile selected, its body drawn —; so the absences below are the page's choice, not a
            // late render.
            await expect(page.getByTestId('settings-tab-administration'), 'no «Administration» entry ?tab=security could select').toHaveCount(0);
            await expect(page.getByTestId('security-tab'), 'the body of Security never mounts').toHaveCount(0);
            await expect(page.getByTestId('settings-subtabs')).toHaveCount(0);
            await expect(page.getByTestId('settings-tab-security')).toHaveCount(0);
            expect(checkReads, "a member's page never asks for the administrators' checks").toEqual([]);
        } finally {
            page.off('request', recordCheckRead);
        }
    });
});
