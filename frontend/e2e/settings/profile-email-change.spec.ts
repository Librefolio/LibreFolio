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
 * - PEC-E-05 (D10): the link page answered 403 `EMAIL_CHANGE_SIGN_IN_REQUIRED` shows `signin`; its button opens the sign-in
 *   with the way back; once the fixture user signs in, the page is back on `/confirm-email-change`, ready, and its click
 *   sends the same token (kept in the tab, never in the address); the confirmation stays simulated.
 * - PEC-E-06 (D10, plan §8.1): the same with ANOTHER account signed in in that browser: the button signs it out first, so
 *   the sign-in form shows instead of a bounce back to the same 403, and the right account then finds the page ready.
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

test.describe('The link page — sign in to confirm (project 71, D10)', () => {
    test('PEC-E-05 a 403 asks to sign in; after the sign-in the page is back, ready, with the same token', async ({page}) => {
        const token = `pec-token-${uniqueSuffix()}`;
        const confirms: unknown[] = [];
        const problems: string[] = [];
        await page.route(
            (url) => url.pathname === CONFIRM_PATH,
            async (route) => {
                if (route.request().method() !== 'POST') return route.fallback();
                confirms.push(route.request().postDataJSON());
                if (confirms.length === 1) {
                    await route.fulfill({status: 403, json: {detail: {error_code: 'EMAIL_CHANGE_SIGN_IN_REQUIRED', message: 'Sign in to the account that asked for this change to confirm it'}}});
                    return;
                }
                const json = {username: TEST_USER.username};
                const checked = schemas.EmailChangeConfirmResponse.safeParse(json);
                if (!checked.success) problems.push(`POST ${CONFIRM_PATH}: ${checked.error.message}`);
                await route.fulfill({status: 200, json});
            },
        );

        await page.goto(`/confirm-email-change#token=${token}`);
        const card = page.getByTestId('email-change-status');
        await expect(card).toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        expect(page.url(), 'the token leaves the address bar').not.toContain(token);
        await card.getByTestId('email-change-confirm').click();
        await expect(card).toHaveAttribute('data-status', 'signin', {timeout: ACTION_MS});
        await expect(card.getByTestId('email-change-goto-login'), 'One way to the sign-in, not two').toHaveCount(0);

        await card.getByTestId('email-change-signin-action').click();
        await expect.poll(() => new URL(page.url()).search, {timeout: ACTION_MS}).toBe('?redirect=%2Fconfirm-email-change');
        await expect(page.getByTestId('login-form')).toBeVisible({timeout: LOAD_MS});
        await page.getByTestId('login-username').fill(TEST_USER.username);
        await page.getByTestId('login-password').fill(TEST_USER.password);
        await page.getByTestId('login-submit').click();

        await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_MS}).toBe('/confirm-email-change');
        await expect(card, 'Back from the sign-in, ready for the click').toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        expect(page.url(), 'the kept token never reaches the address bar').not.toContain(token);
        await card.getByTestId('email-change-confirm').click();
        await expect.poll(() => confirms.length, {timeout: ACTION_MS}).toBe(2);
        expect(confirms).toEqual([{token}, {token}]);
        expect(problems).toEqual([]);
    });

    test('PEC-E-06 another account signed in here: the button signs it out, the sign-in form shows, the right account finds the page ready', async ({page}) => {
        const token = `pec-token-${uniqueSuffix()}`;
        const confirms: unknown[] = [];
        await page.route(
            (url) => url.pathname === CONFIRM_PATH,
            async (route) => {
                if (route.request().method() !== 'POST') return route.fallback();
                confirms.push(route.request().postDataJSON());
                // The administrator's session is not the account of the link: 403, as the route answers it (PEC-021)
                if (confirms.length === 1) return route.fulfill({status: 403, json: {detail: {error_code: 'EMAIL_CHANGE_SIGN_IN_REQUIRED', message: 'Sign in'}}});
                await route.fulfill({status: 200, json: {username: TEST_USER.username}});
            },
        );
        await login(page, TEST_ADMIN);

        await page.goto(`/confirm-email-change#token=${token}`);
        const card = page.getByTestId('email-change-status');
        await card.getByTestId('email-change-confirm').click({timeout: LOAD_MS});
        await expect(card).toHaveAttribute('data-status', 'signin', {timeout: ACTION_MS});
        await card.getByTestId('email-change-signin-action').click();

        // Signed out first: the sign-in page shows its form, instead of jumping back to the link page with the admin's session
        await expect(page.getByTestId('login-form')).toBeVisible({timeout: LOAD_MS});
        expect(new URL(page.url()).search).toBe('?redirect=%2Fconfirm-email-change');
        const me = await page.request.get(ME_PATH);
        expect(me.status(), 'the administrator’s session is gone from this browser').toBe(401);
        await page.getByTestId('login-username').fill(TEST_USER.username);
        await page.getByTestId('login-password').fill(TEST_USER.password);
        await page.getByTestId('login-submit').click();

        await expect.poll(() => new URL(page.url()).pathname, {timeout: LOAD_MS}).toBe('/confirm-email-change');
        await expect(card).toHaveAttribute('data-status', 'ready', {timeout: LOAD_MS});
        await card.getByTestId('email-change-confirm').click();
        await expect.poll(() => confirms.length, {timeout: ACTION_MS}).toBe(2);
        expect(confirms).toEqual([{token}, {token}]);
    });
});
