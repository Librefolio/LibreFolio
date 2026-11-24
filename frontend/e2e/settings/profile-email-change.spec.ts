/**
 * A change of address asked from Profile, verified from the new mailbox (release 1.4, project 71, block 2, step 2.11).
 *
 * With email working the profile does not change the address at once: the server keeps it, emails a link to the new one,
 * and the account shows the change it waits for (`user.pending_email_change`). The lane has no SMTP server and must keep
 * none, so — as the other email specs (`email-send-link`, `instance-email.ts`) — every route of the flow is answered per
 * test with `page.route` (removed with the page at the end of the test): the real response with one field changed where a
 * real one exists, a simulated answer where it does not, each checked against the generated schema before it is served.
 * The fixture user's address is never changed for real: `PUT /auth/profile` and the confirmation never reach the server.
 *
 * - PEC-E-01: saving a new address → the event `settings.profile.email.pending`, an info toast, the box with the address
 *   in full; the field shows the account's address again; one `PUT` carrying the address and the password.
 * - PEC-E-02: «Send again» → one `POST …/email-change/resend` and the event `settings.profile.email.resent`; «Cancel the
 *   request» → one `DELETE …/email-change`, `settings.profile.email.cancelled`, and the box goes.
 * - PEC-E-03: on a 375 px phone the box's buttons are under its text.
 * - PEC-E-04: an administrator sees the badge on the account and revokes its open link from «Account links»: one `DELETE
 *   /users/account-links/{id}`, the event `accounts.link.revoked`, and the badge goes with the reload.
 * - The link page (D10; lots E1–E3, the developer's test of 13/11/2026). The lane cannot mint a real link (no SMTP), so
 *   `simulateLinkServer` answers the check and the confirmation as the server does, from the browser's REAL session
 *   (`GET /auth/me`): none → `signin` / 403 `EMAIL_CHANGE_SIGN_IN_REQUIRED`; another account → `other_account` / 403
 *   `EMAIL_CHANGE_OTHER_ACCOUNT`; the link's account → `ready` / 200 `{session_kept: true}`. That the server really keeps
 *   the confirming session and ends the others is pinned in-process by the API test PEC-020b.
 * - PEC-E-05 (E2): signed out (a private window): the page asks to sign in AT ONCE, with no confirm button; its button
 *   opens the sign-in with the way back; signed in, the page is back, ready, and ONE click confirms the same token (kept in
 *   the tab, never in the address); then the Profile opens, still signed in (E1).
 * - PEC-E-06 (D10, plan §8.1): ANOTHER account signed in in that browser: the page shows `otheraccount` at once (the link
 *   belongs to another account, never which), its button signs the other account out first, so the sign-in form shows
 *   instead of a bounce back, and the right account then finds the page ready.
 * - PEC-E-07 (E1): already signed in with the link's account: ready at once, one click, then the Profile, still signed in;
 *   nothing left for the sign-in page.
 * - PEC-E-08 (E3): a link the server does not know, read by the REAL check: the page says so at once, with no confirm
 *   button and the way back to the sign-in.
 * - PEC-E-09 (E5): at 1280, 1024, 820, 640 and 375 px, editing the address never narrows its field: the field keeps its width once a
 *   new address is typed and the password field shows, it is as wide as that password field under it (measured before the
 *   fix: 228 px over 288 px at every width from 640 to 1440, the address cut), and the save and undo buttons are drawn
 *   beside or under it, never over it.
 *
 * Shared lane: nothing is written but sign-ins and sign-outs of the fixture users' own sessions. Every assertion reads a test id, a published state, an event or a request — never a
 * translated text.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const ME_PATH = `${API}/auth/me`;
const PROFILE_PATH = `${API}/auth/profile`;
const CANCEL_PATH = `${API}/auth/profile/email-change`;
const RESEND_PATH = `${API}/auth/profile/email-change/resend`;
const USERS_PATH = `${API}/users`;
const LINKS_PATH = `${API}/users/account-links`;
const CONFIRM_PATH = `${API}/email/email-change/confirm`;
const CHECK_PATH = `${API}/email/email-change/check`;

// Budgets: deadlines, never delays.
/** From a navigation to a settled tab. */
const LOAD_MS = 20_000;
/** An action's round trip, and what follows it. */
const ACTION_MS = 15_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

type Pending = {email: string; expires_at: string};

/** The change the simulated server keeps for the fixture account, and every request it answered. */
interface ProfileServer {
    pending: Pending | null;
    puts: unknown[];
    resends: number;
    cancels: number;
    /** Why a request could not be answered as asked: a test asserts it empty. */
    problems: string[];
}

function inADay(): string {
    return new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
}

/** The address a simulated link would confirm: the `new_email` of a `ready` check (81 U46), shown on the page as a double check. */
const LINK_ADDRESS = 'pec-link-address@zq-pec.example.com';

function newAddress(tag: string): string {
    return `pec_${tag}_${uniqueSuffix()}@example.com`;
}

/**
 * Answer the Profile routes of the change for this page: `GET /auth/me` is the real answer with `pending_email_change`
 * set from the server's state; `PUT /auth/profile` with an address answers `pending` and starts the wait; resend and
 * cancel answer as the routes of step 2.4 do. Everything else falls through.
 */
async function simulateProfileServer(page: Page, start: Pending | null = null): Promise<ProfileServer> {
    const server: ProfileServer = {pending: start, puts: [], resends: 0, cancels: 0, problems: []};

    const realUser = async (): Promise<Record<string, unknown>> => {
        const response = await page.request.get(ME_PATH);
        if (!response.ok()) throw new Error(`the real GET ${ME_PATH} answered ${response.status()}`);
        return ((await response.json()) as {user: Record<string, unknown>}).user;
    };
    const fulfill = async (route: Route, status: number, json: unknown, schema?: {safeParse: (value: unknown) => {success: boolean; error?: {message: string}}}) => {
        if (schema) {
            const checked = schema.safeParse(json);
            if (!checked.success) server.problems.push(`${route.request().method()} ${new URL(route.request().url()).pathname}: the answer fails the generated schema: ${checked.error?.message}`);
        }
        await route.fulfill({status, json});
    };

    await page.route(
        (url) => url.pathname === ME_PATH,
        async (route) => {
            if (route.request().method() !== 'GET') return route.fallback();
            try {
                const response = await route.fetch();
                const body = (await response.json()) as {user: Record<string, unknown>};
                if (!response.ok()) return route.fulfill({response});
                await fulfill(route, 200, {...body, user: {...body.user, pending_email_change: server.pending}}, schemas.AuthMeResponse);
            } catch (error) {
                server.problems.push(`GET ${ME_PATH}: ${String(error)}`);
                await route.fallback();
            }
        },
    );
    await page.route(
        (url) => url.pathname === PROFILE_PATH,
        async (route) => {
            if (route.request().method() !== 'PUT') return route.fallback();
            const body = route.request().postDataJSON() as {email?: string};
            server.puts.push(body);
            if (!body.email) return route.fallback();
            server.pending = {email: body.email, expires_at: inADay()};
            const user = {...(await realUser()), pending_email_change: server.pending};
            await fulfill(route, 200, {user, message: 'Email change requested: confirm it from the new address', email_change: 'pending'}, schemas.UpdateProfileResponse);
        },
    );
    await page.route(
        (url) => url.pathname === RESEND_PATH,
        async (route) => {
            if (route.request().method() !== 'POST') return route.fallback();
            server.resends += 1;
            if (!server.pending) return fulfill(route, 404, {detail: {error_code: 'EMAIL_CHANGE_NOT_PENDING', message: 'No change of address waits for its link'}});
            server.pending = {...server.pending, expires_at: inADay()};
            await fulfill(route, 200, server.pending, schemas.PendingEmailChangeRead);
        },
    );
    await page.route(
        (url) => url.pathname === CANCEL_PATH,
        async (route) => {
            if (route.request().method() !== 'DELETE') return route.fallback();
            server.cancels += 1;
            server.pending = null;
            await route.fulfill({status: 204, body: ''});
        },
    );
    return server;
}

/** Open Settings › Profile, signed in already; ends on the tab settled. */
async function openProfile(page: Page): Promise<void> {
    await navigateTo(page, '/settings/profile');
    await expect(page.getByTestId('profile-tab'), 'The profile tab settles').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
}

test.describe('Profile — a new address waits for its link (project 71)', () => {
    test('PEC-E-01 saving a new address: the info toast and the box, and the field keeps the account’s address', async ({page}) => {
        await login(page, TEST_USER);
        const server = await simulateProfileServer(page);
        await openProfile(page);
        const address = newAddress('save');

        await page.getByTestId('profile-edit-toggle').click();
        await page.getByTestId('profile-email').fill(address);
        await page.getByTestId('profile-email-password').fill(TEST_USER.password);
        const since = await eventSeq(page);
        await page.getByTestId('profile-save-all').click();

        await waitForEvent(page, 'settings.profile.email.pending', {since, timeout: ACTION_MS});
        await expect(page.getByTestId('toast-info'), 'An info toast, not a «saved» one').toBeVisible({timeout: UI_MS});
        const box = page.getByTestId('profile-email-pending');
        await expect(box).toBeVisible({timeout: ACTION_MS});
        await expect(box.getByTestId('profile-email-pending-address')).toHaveText(address);
        await expect(page.getByTestId('profile-email'), 'The field shows the address the account has').toHaveValue(TEST_USER.email);
        expect(server.puts).toEqual([{email: address, current_password: TEST_USER.password}]);
        expect(server.problems).toEqual([]);
        // The real account, read past the stubs: its address never changed
        const real = (await (await page.request.get(ME_PATH)).json()) as {user: {email: string}};
        expect(real.user.email).toBe(TEST_USER.email);
    });

    test('PEC-E-02 «Send again» and «Cancel the request» call their routes; cancelled, the box goes', async ({page}) => {
        const server = await simulateProfileServer(page, {email: newAddress('wait'), expires_at: inADay()});
        await login(page, TEST_USER);
        await openProfile(page);
        const box = page.getByTestId('profile-email-pending');
        await expect(box).toBeVisible({timeout: LOAD_MS});

        let since = await eventSeq(page);
        await box.getByTestId('profile-email-pending-resend').click();
        await waitForEvent(page, 'settings.profile.email.resent', {since, timeout: ACTION_MS});
        await expect(box, 'The box waits no more').toHaveAttribute('data-busy', 'false', {timeout: UI_MS});
        expect(server.resends).toBe(1);

        since = await eventSeq(page);
        await box.getByTestId('profile-email-pending-cancel').click();
        await waitForEvent(page, 'settings.profile.email.cancelled', {since, timeout: ACTION_MS});
        await expect(box, 'Cancelled, nothing waits').toHaveCount(0, {timeout: ACTION_MS});
        expect(server.cancels).toBe(1);
        expect(server.problems).toEqual([]);
    });

    test('PEC-E-03 on a 375 px phone the buttons go under the text', async ({page}) => {
        await page.setViewportSize({width: 375, height: 812});
        const server = await simulateProfileServer(page, {email: newAddress('phone'), expires_at: inADay()});
        await login(page, TEST_USER);
        await openProfile(page);
        const box = page.getByTestId('profile-email-pending');
        await expect(box).toBeVisible({timeout: LOAD_MS});

        const text = await box.getByTestId('profile-email-pending-expires').boundingBox();
        const resend = await box.getByTestId('profile-email-pending-resend').boundingBox();
        const cancel = await box.getByTestId('profile-email-pending-cancel').boundingBox();
        expect(text && resend && cancel, 'the text and both buttons are drawn').toBeTruthy();
        expect(resend!.y, 'Send again is under the text').toBeGreaterThanOrEqual(text!.y + text!.height);
        expect(cancel!.y, 'Cancel is under the text').toBeGreaterThanOrEqual(text!.y + text!.height);
        const width = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(width, 'the page does not scroll sideways').toBeLessThanOrEqual(1);
        expect(server.problems).toEqual([]);
    });
});

test.describe('Users — the administrator sees a pending change and revokes its link (project 71)', () => {
    test('PEC-E-04 the badge on the account, and «Revoke» on its open link', async ({page}) => {
        const problems: string[] = [];
        let open = true;
        let deletes = 0;
        const linkId = 900_000_000 + Math.floor(Math.random() * 1_000_000);
        const address = newAddress('admin');

        await page.route(
            (url) => url.pathname === USERS_PATH,
            async (route) => {
                if (route.request().method() !== 'GET') return route.fallback();
                const response = await route.fetch();
                const body = (await response.json()) as {items: Array<Record<string, unknown>>};
                // Only the two accounts this test reads, so that no paging hides the one it looks for
                const items = body.items.filter((item) => item.username === TEST_USER.username || item.username === TEST_ADMIN.username).map((item) => (item.username === TEST_USER.username ? {...item, pending_email_change: open} : item));
                const json = {...body, items};
                const checked = schemas.AdminUserListResponse.safeParse(json);
                if (!checked.success) problems.push(`GET ${USERS_PATH}: ${checked.error.message}`);
                await route.fulfill({status: 200, json});
            },
        );
        await page.route(
            (url) => url.pathname === LINKS_PATH,
            async (route) => {
                if (route.request().method() !== 'GET') return route.fallback();
                const users = await page.request.get(USERS_PATH);
                const member = ((await users.json()) as {items: Array<{id: number; username: string}>}).items.find((item) => item.username === TEST_USER.username);
                if (!member) problems.push(`${TEST_USER.username} is not in GET ${USERS_PATH}`);
                const now = new Date().toISOString();
                const link = {
                    id: linkId,
                    purpose: 'email_change',
                    state: 'open',
                    revocable: true,
                    user_id: member?.id ?? null,
                    username: TEST_USER.username,
                    email: address,
                    grants_admin: false,
                    created_by_user_id: member?.id ?? null,
                    created_by_username: TEST_USER.username,
                    created_at: now,
                    expires_at: inADay(),
                    used_at: null,
                    used_by_user_id: null,
                    used_by_username: null,
                    revoked_at: null,
                };
                // Only this link: the table needs no paging, and the lane's own links are not this test's
                const json = {items: open ? [link] : []};
                const checked = schemas.AccountLinkListResponse.safeParse(json);
                if (!checked.success) problems.push(`GET ${LINKS_PATH}: ${checked.error.message}`);
                await route.fulfill({status: 200, json});
            },
        );
        await page.route(
            (url) => url.pathname === `${LINKS_PATH}/${linkId}`,
            async (route) => {
                if (route.request().method() !== 'DELETE') return route.fallback();
                deletes += 1;
                open = false;
                await route.fulfill({status: 204, body: ''});
            },
        );

        await login(page, TEST_ADMIN);
        await navigateTo(page, '/settings?tab=users');
        await expect(page.getByTestId('users-tab'), 'The tab settles').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
        const row = page.locator(`[data-testid="users-row"][data-username="${TEST_USER.username}"]`);
        await expect(row).toHaveAttribute('data-pending-email-change', 'true', {timeout: UI_MS});
        await expect(row.getByTestId('users-badge-pending-email-change')).toBeVisible();

        const linkRow = page.getByTestId('users-links-open').locator(`tbody tr[data-row-id="${linkId}"]`);
        await linkRow.getByTestId(`row-actions-${linkId}`).click();
        await page.getByTestId('account-link-revoke').click();
        const header = page.getByTestId('users-confirm');
        await expect(header).toBeVisible({timeout: UI_MS});
        const since = await eventSeq(page);
        await page.getByRole('dialog').filter({has: header}).getByTestId('confirm-modal-confirm').click();
        await waitForEvent(page, 'accounts.link.revoked', {since, timeout: ACTION_MS});
        await expect(page.getByTestId('users-tab'), 'The revocation reloads the tab').toHaveAttribute('data-busy', 'false', {timeout: ACTION_MS});

        expect(deletes).toBe(1);
        await expect(row).toHaveAttribute('data-pending-email-change', 'false', {timeout: UI_MS});
        await expect(row.getByTestId('users-badge-pending-email-change')).toHaveCount(0);
        expect(problems).toEqual([]);
    });
});

/** What the simulated link server was asked, and why it could not answer as asked (a test asserts it empty). */
interface LinkServer {
    checks: unknown[];
    confirms: unknown[];
    problems: string[];
}

/**
 * Answer the link page's check and confirmation for `owner`'s link, as the server does, from the browser's REAL session:
 * none → `signin` / 403 `EMAIL_CHANGE_SIGN_IN_REQUIRED`; another account → `other_account` / 403
 * `EMAIL_CHANGE_OTHER_ACCOUNT`; `owner` → `ready` / 200 with the session kept. Each answer is checked against the generated
 * schema before it is served. Nothing is written on the server.
 */
async function simulateLinkServer(page: Page, owner: {username: string}): Promise<LinkServer> {
    const server: LinkServer = {checks: [], confirms: [], problems: []};
    const whoIsHere = async (): Promise<'nobody' | 'owner' | 'other'> => {
        const me = await page.request.get(ME_PATH);
        if (me.status() === 401) return 'nobody';
        if (!me.ok()) throw new Error(`the real GET ${ME_PATH} answered ${me.status()}`);
        return ((await me.json()) as {user: {username: string}}).user.username === owner.username ? 'owner' : 'other';
    };
    const checked = (path: string, schema: {safeParse: (value: unknown) => {success: boolean; error?: {message: string}}}, json: unknown): unknown => {
        const result = schema.safeParse(json);
        if (!result.success) server.problems.push(`POST ${path}: the answer fails the generated schema: ${result.error?.message}`);
        return json;
    };
    await page.route(
        (url) => url.pathname === CHECK_PATH,
        async (route) => {
            if (route.request().method() !== 'POST') return route.fallback();
            server.checks.push(route.request().postDataJSON());
            const here = await whoIsHere();
            const status = here === 'nobody' ? 'signin' : here === 'other' ? 'other_account' : 'ready';
            // The address comes only with `ready` (81 U46)
            await route.fulfill({status: 200, json: checked(CHECK_PATH, schemas.EmailChangeCheckResponse, status === 'ready' ? {status, new_email: LINK_ADDRESS} : {status})});
        },
    );
    await page.route(
        (url) => url.pathname === CONFIRM_PATH,
        async (route) => {
            if (route.request().method() !== 'POST') return route.fallback();
            server.confirms.push(route.request().postDataJSON());
            const here = await whoIsHere();
            if (here === 'nobody') return route.fulfill({status: 403, json: {detail: {error_code: 'EMAIL_CHANGE_SIGN_IN_REQUIRED', message: 'Sign in to the account that asked for this change to confirm it'}}});
            if (here === 'other') return route.fulfill({status: 403, json: {detail: {error_code: 'EMAIL_CHANGE_OTHER_ACCOUNT', message: 'This link belongs to another account'}}});
            await route.fulfill({status: 200, json: checked(CONFIRM_PATH, schemas.EmailChangeConfirmResponse, {username: owner.username, session_kept: true})});
        },
    );
    return server;
}

/** Sign in through the form the link page opened, which must come back to the link page. */
async function signInOnTheWayBack(page: Page, user: {username: string; password: string}): Promise<void> {
    await expect(page.getByTestId('login-form')).toBeVisible({timeout: LOAD_MS});
    expect(new URL(page.url()).search).toBe('?redirect=%2Fconfirm-email-change');
    await page.getByTestId('login-username').fill(user.username);
    await page.getByTestId('login-password').fill(user.password);
    await page.getByTestId('login-submit').click();
    await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_MS}).toBe('/confirm-email-change');
}

/** One click on «confirm» from a ready card: the event says the session was kept, the Profile opens, still signed in. */
async function confirmAndStayIn(page: Page): Promise<void> {
    const card = page.getByTestId('email-change-status');
    await expect(card).toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
    await expect(card.getByTestId('email-change-address'), 'the page shows the address the click would confirm (81 U46)').toHaveText(LINK_ADDRESS);
    const since = await eventSeq(page);
    await card.getByTestId('email-change-confirm').click();
    const event = await waitForEvent(page, 'email.change.confirmed', {since, timeout: ACTION_MS});
    expect(event.detail).toEqual({sessionKept: true});
    await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_MS}).toBe('/settings/profile');
    // Raised on the link page, shown by the app's container once the Profile mounts: read at once, before the page settles
    await expect(page.getByTestId('toast-success'), 'A success toast says the address changed').toBeVisible({timeout: UI_MS});
    await expect(page.getByTestId('profile-tab'), 'The Profile opens, signed in').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
    expect((await page.request.get(ME_PATH)).status(), 'still signed in').toBe(200);
}

test.describe('The link page — knows on opening what the link can do, and stays signed in (project 71, D10, lot E)', () => {
    test('PEC-E-05 signed out: the sign-in is asked at once; after it, one click confirms and the Profile opens, signed in', async ({page}) => {
        const token = `pec-token-${uniqueSuffix()}`;
        const server = await simulateLinkServer(page, TEST_USER);

        await page.goto(`/confirm-email-change#token=${token}`);
        const card = page.getByTestId('email-change-status');
        await expect(card, 'The sign-in is asked before any click').toHaveAttribute('data-status', 'signin', {timeout: LOAD_MS});
        expect(page.url(), 'the token leaves the address bar').not.toContain(token);
        await expect(card.getByTestId('email-change-confirm'), 'No confirm button before the sign-in').toHaveCount(0);
        await expect(card.getByTestId('email-change-address'), 'No address is shown before the sign-in (81 U46)').toHaveCount(0);
        await expect(card.getByTestId('email-change-goto-login'), 'One way to the sign-in, not two').toHaveCount(0);

        await card.getByTestId('email-change-signin-action').click();
        await signInOnTheWayBack(page, TEST_USER);
        expect(page.url(), 'the kept token never reaches the address bar').not.toContain(token);
        await confirmAndStayIn(page);

        expect(server.checks).toEqual([{token}, {token}]);
        expect(server.confirms, 'one click, one confirmation').toEqual([{token}]);
        expect(server.problems).toEqual([]);
    });

    test('PEC-E-06 another account signed in here: said at once, its button signs it out, the right account finds the page ready', async ({page}) => {
        const token = `pec-token-${uniqueSuffix()}`;
        const server = await simulateLinkServer(page, TEST_USER);
        await login(page, TEST_ADMIN);

        await page.goto(`/confirm-email-change#token=${token}`);
        const card = page.getByTestId('email-change-status');
        await expect(card, 'Said before any click').toHaveAttribute('data-status', 'otheraccount', {timeout: LOAD_MS});
        await expect(card.getByTestId('email-change-confirm')).toHaveCount(0);
        await card.getByTestId('email-change-switch-account').click();

        // Signed out first: the sign-in page shows its form, instead of jumping back to the link page with the admin's session
        await expect(page.getByTestId('login-form')).toBeVisible({timeout: LOAD_MS});
        expect((await page.request.get(ME_PATH)).status(), 'the administrator’s session is gone from this browser').toBe(401);
        await signInOnTheWayBack(page, TEST_USER);
        await confirmAndStayIn(page);

        expect(server.confirms).toEqual([{token}]);
        expect(server.problems).toEqual([]);
    });

    test('PEC-E-07 already signed in with the link’s account: ready at once, one click, the Profile, still signed in', async ({page}) => {
        const token = `pec-token-${uniqueSuffix()}`;
        const server = await simulateLinkServer(page, TEST_USER);
        await login(page, TEST_USER);

        await page.goto(`/confirm-email-change#token=${token}`);
        await confirmAndStayIn(page);

        expect(server.checks).toEqual([{token}]);
        expect(server.confirms).toEqual([{token}]);
        expect(server.problems).toEqual([]);
    });

    test('PEC-E-08 a link the server does not know (the real check): said at once, no confirm button', async ({page}) => {
        let confirms = 0;
        await page.route(
            (url) => url.pathname === CONFIRM_PATH,
            async (route) => {
                confirms += 1;
                await route.fallback();
            },
        );

        await page.goto(`/confirm-email-change#token=pec-unknown-${uniqueSuffix()}`);
        const card = page.getByTestId('email-change-status');
        await expect(card).toHaveAttribute('data-status', 'unknown', {timeout: LOAD_MS});
        await expect(card.getByTestId('email-change-confirm')).toHaveCount(0);
        await expect(card.getByTestId('email-change-goto-login')).toBeVisible();
        expect(confirms, 'nothing was spent').toBe(0);
    });
});

for (const width of [1280, 1024, 820, 640, 375]) {
    test(`PEC-E-09 editing the address keeps its field’s width, ${width} px`, async ({page}) => {
        await page.setViewportSize({width, height: 900});
        await login(page, TEST_USER);
        const server = await simulateProfileServer(page);
        await openProfile(page);

        await page.getByTestId('profile-edit-toggle').click();
        const field = page.getByTestId('profile-email');
        await expect(field).toBeEnabled({timeout: UI_MS});
        const before = await field.boundingBox();
        await field.fill(newAddress('width'));
        await expect(page.getByTestId('profile-email-password'), 'A new address asks for the password').toBeVisible({timeout: UI_MS});
        const after = await field.boundingBox();

        expect(before && after, 'the field is drawn').toBeTruthy();
        test.info().annotations.push({type: 'PEC-E-09 field width', description: `${width}px: ${before!.width.toFixed(1)} → ${after!.width.toFixed(1)}`});
        expect(after!.width, 'the field does not narrow while it is edited').toBeGreaterThanOrEqual(before!.width - 1);
        const password = (await page.getByTestId('profile-email-password').boundingBox())!;
        expect(after!.width, 'the field is as wide as the password field under it').toBeGreaterThanOrEqual(password.width - 1);
        for (const id of ['profile-email-save', 'profile-email-undo']) {
            const button = page.getByTestId(id).filter({visible: true});
            await expect(button, `${id} is drawn`).toHaveCount(1);
            const box = (await button.boundingBox())!;
            const overlaps = box.x < after!.x + after!.width && box.x + box.width > after!.x && box.y < after!.y + after!.height && box.y + box.height > after!.y;
            expect(overlaps, `${id} is beside or under the field, never over it`).toBe(false);
        }
        const sideways = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
        expect(sideways, 'the page does not scroll sideways').toBeLessThanOrEqual(1);
        expect(server.problems).toEqual([]);
    });
}
