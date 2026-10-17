/**
 * «Send by email» in the share dialogs E2E (workstream E, lot E4b): Settings › Users, the invitation and the
 * password-reset dialogs, where E's action is registered in A's `LINK_SHARE_ACTIONS`.
 *
 * Through the real tab and the lane's real backend — the invitation and the reset link are really issued — with two
 * reads of the page simulated (`page.route`, owned by each test and removed by it):
 *   - `GET /api/v1/system/instance`: the real answer with `email` replaced (`fixtures/instance-email.ts`), links ready
 *     or not; the lane itself has no SMTP server;
 *   - `POST /api/v1/email/links`: a simulated server that records what it is asked and answers the email sent — in the
 *     language the request asked for, `en` (standing for the instance's default) without one, checked against the
 *     generated `EmailLinkResponse` — or a refusal. The real route — which would answer 409, email being off on the
 *     lane — is never reached, and nothing is sent.
 * Covered:
 *   ESL-E-01  an invitation, links ready: the action in the link step, prefilled with the invitation's address; left on
 *             the instance's language, it posts {purpose: invite, the token of the link shown, to} with no `language`
 *             key at all, and says «sent» with the address the server answered and its language (`data-language`);
 *             `email.link.sent` recorded with the purpose and the language;
 *   ESL-E-02  a reset link, links ready: no address to type and no language to choose, the account's own address said
 *             instead; it posts {purpose: password_reset, the token} without `to` or `language`; «sent» with the
 *             language answered, and `email.link.sent`;
 *   ESL-E-03  an invitation, the simulated server refuses with 429 EMAIL_RATE_LIMITED: «failed», the wait recorded in
 *             `email.link.sendFailed`, the action still offered;
 *   ESL-E-04  an invitation, email available but links not: the link step without the action — `LinkShare` drawn with
 *             its copy button and its actions row, so the absence is of the action alone;
 *   ESL-E-05  an invitation in Italiano (lot E-8, decision N69): `it` chosen in the action's language select; it posts
 *             exactly {purpose: invite, token, to, language: it}; «sent» with `data-language="it"`, the language the
 *             server answered, and `email.link.sent` {purpose: invite, language: it}.
 * Assertions read test ids, `data-*`, the request bodies and the events, never a translated text (the address in the
 * outcome is data, not a translation).
 *
 * Ownership, as admin-users.spec.ts (workstream A) does it, reduced to what this spec creates: every invitation address
 * and every disposable account is recorded before the request that creates it goes; after the test, red or green, every
 * pending invitation carrying one of those addresses is revoked and every disposable account deletes itself. No
 * fixture user changes; the lane registers openly (checked first, changed by no spec). Parallel by default.
 *
 * Prerequisites: test users created (`e2e_test_admin` an administrator); no SMTP server on the lane.
 * Registered in scripts/test_runner/_frontend_utility.py, action `email-send-link` of front-utility.
 */
import type {Route} from '@playwright/test';
import {schemas} from '../../src/lib/api/generated';
import {expect, test as base, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {INSTANCE_CONFIG_PATH} from '../fixtures/instance-config';
import {serveInstanceEmail, type InstanceEmailStub} from '../fixtures/instance-email';
import {TEST_ADMIN} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const LINKS_PATH = `${API}/email/links`;
const isLinks = (url: URL): boolean => url.pathname === LINKS_PATH;

// Budgets: deadlines, never delays.
/** From a navigation to a settled tab: the SPA's load, the auth check, then GET /users and GET /users/invites. */
const LOAD_MS = 20_000;
/** An action's round trip, and the reload of the tab that follows it. */
const ACTION_MS = 15_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

/** The password of every disposable account: eight characters or more, upper and lower case, a digit, a special one. */
const PASSWORD = 'Esl-Pass123!';

type EmailLinkResponse = ReturnType<typeof schemas.EmailLinkResponse.parse>;

/** A disposable account. `id`: null until the registration answers. */
type Account = {id: number | null; username: string; email: string; password: string};
type Registered = Account & {id: number};
/** What a test created, recorded the moment it exists — or just before: the clean-up never guesses. */
type Created = {accounts: Account[]; inviteEmails: string[]};

/** What a test may ask for. Everything it creates through these is removed after it. */
type Owned = {
    /** A disposable ordinary member, registered anonymously. */
    register(tag: string): Promise<Registered>;
    /** A unique invitation address, recorded for the clean-up before anything is sent with it. */
    inviteAddress(tag: string): string;
};

/** Precondition, verified: the lane registers accounts openly. No E2E spec changes it. */
async function expectRegistrationOpen(api: APIRequestContext): Promise<void> {
    const response = await api.get(INSTANCE_CONFIG_PATH);
    expect(response.status(), `GET ${INSTANCE_CONFIG_PATH}: ${await response.text()}`).toBe(200);
    const mode = ((await response.json()) as {accounts?: {registration_mode?: unknown}}).accounts?.registration_mode;
    expect(mode, `The lane must register accounts openly: this spec registers its disposable account anonymously and invites through the tab. The lane answered ${JSON.stringify(mode)}`).toBe('open');
}

async function signInAdministrator(admin: APIRequestContext): Promise<void> {
    const response = await admin.post(`${API}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    expect(response.status(), `Sign-in of ${TEST_ADMIN.username}, whose API session cleans up after the test`).toBe(200);
}

/** The account deletes itself, signed in on its own context. Returns why it could not, or null. */
async function deleteItself(session: APIRequestContext, account: Account): Promise<string | null> {
    const signedIn = await session.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
    if (signedIn.status() === 401 && account.id === null) return null;
    if (signedIn.status() !== 200) return `account ${account.username}: the sign-in answered ${signedIn.status()}, so it cannot remove itself`;
    const {user} = (await signedIn.json()) as {user: {id: number; username: string}};
    if (user.username !== account.username) return `account ${account.username}: the session opened is ${user.username}, not the account to remove`;
    const removed = await session.delete(`${API}/auth/users/me`);
    return removed.ok() ? null : `account ${account.username}: DELETE /auth/users/me answered ${removed.status()}`;
}

/** Remove what the test created. Never throws, so it never masks the test's own failure: it returns what it could not remove. */
async function cleanUp(admin: APIRequestContext, open: () => Promise<APIRequestContext>, created: Created): Promise<string[]> {
    const failures: string[] = [];
    if (created.inviteEmails.length > 0) {
        try {
            const response = await admin.get(`${API}/users/invites`);
            if (response.status() !== 200) {
                failures.push(`GET /users/invites answered ${response.status()}`);
            } else {
                const mine = new Set(created.inviteEmails);
                const {items} = (await response.json()) as {items: Array<{id: number; email: string | null}>};
                for (const invite of items) {
                    if (invite.email === null || !mine.has(invite.email.toLowerCase())) continue;
                    const revoked = await admin.delete(`${API}/users/invites/${invite.id}`);
                    // 204: it was still pending, and is revoked now. 404: it no longer was.
                    if (revoked.status() !== 204 && revoked.status() !== 404) failures.push(`invitation ${invite.id} (${invite.email}): DELETE answered ${revoked.status()}`);
                }
            }
        } catch (error) {
            failures.push(`invitations: ${String(error)}`);
        }
    }
    for (const account of created.accounts) {
        try {
            const failure = await deleteItself(await open(), account);
            if (failure) failures.push(failure);
        } catch (error) {
            failures.push(`account ${account.username}: ${String(error)}`);
        }
    }
    return failures;
}

const test = base.extend<{owned: Owned}>({
    owned: async ({playwright, baseURL}, use) => {
        const contexts: APIRequestContext[] = [];
        const open = async (): Promise<APIRequestContext> => {
            const context = await playwright.request.newContext({baseURL});
            contexts.push(context);
            return context;
        };
        const created: Created = {accounts: [], inviteEmails: []};
        let admin: APIRequestContext | undefined;
        let failures: string[] = [];
        try {
            admin = await open();
            await expectRegistrationOpen(admin);
            await signInAdministrator(admin);
            await use({
                async register(tag) {
                    const username = `esl_${tag}_${uniqueSuffix()}`;
                    const account: Account = {id: null, username, email: `${username}@example.com`, password: PASSWORD};
                    // Recorded before the request goes: an account whose registration answer is lost is still removed.
                    created.accounts.push(account);
                    const response = await (await open()).post(`${API}/auth/register`, {data: {username, email: account.email, password: PASSWORD}});
                    expect(response.status(), `Registration is open on the lane (checked first), yet POST /auth/register answered: ${await response.text()}`).toBe(201);
                    account.id = ((await response.json()) as {user: {id: number}}).user.id;
                    return account as Registered;
                },
                inviteAddress(tag) {
                    const email = `esl_${tag}_${uniqueSuffix()}@example.com`;
                    created.inviteEmails.push(email);
                    return email;
                },
            });
        } finally {
            if (admin) failures = await cleanUp(admin, open, created);
            await Promise.all(contexts.map((context) => context.dispose()));
        }
        expect(failures, 'The clean-up must revoke every invitation carrying an address of this test and remove every account it registered').toEqual([]);
    },
});

/** How the simulated `POST /api/v1/email/links` answers: the email sent, or a refusal (a plain `detail` error). */
interface LinkAnswer {
    status: number;
    body: EmailLinkResponse | {detail: Record<string, unknown>};
    headers?: Record<string, string>;
}

/** A fixed answer, or one built from the JSON body of the request it answers. */
type LinkReply = LinkAnswer | ((requested: unknown) => LinkAnswer);

/**
 * The email sent, as the route answers it: in the language the request asked for, else in `en`, standing for the
 * instance's default language — checked against the generated schema, as the client checks it on arrival. A language
 * the schema refuses throws, and the simulated server records why instead of answering it.
 */
function sentAnswer(purpose: EmailLinkResponse['purpose'], to: string): LinkReply {
    return (requested) => {
        const asked = (requested as {language?: unknown} | null)?.language;
        return {status: 200, body: schemas.EmailLinkResponse.parse({purpose, to, language: asked ?? 'en'})};
    };
}

interface LinkServer {
    /** Every request the path received, its method and JSON body: answered when `POST`, fallen back otherwise. */
    requests: Array<{method: string; body: unknown}>;
    /** Why a `POST` could not be answered as asked — no answer could be built from it —: a test asserts it empty. */
    problems: string[];
    unroute: () => Promise<void>;
}

/** Answer `POST /api/v1/email/links` from a simulated server — that path and that method only — with `reply`. */
async function simulateLinkServer(page: Page, reply: LinkReply): Promise<LinkServer> {
    const requests: LinkServer['requests'] = [];
    const problems: string[] = [];
    const handler = async (route: Route) => {
        const request = route.request();
        const post = request.method() === 'POST';
        const body: unknown = post ? request.postDataJSON() : null;
        requests.push({method: request.method(), body});
        if (!post) return route.fallback();
        let answer: LinkAnswer;
        try {
            answer = typeof reply === 'function' ? reply(body) : reply;
        } catch (error) {
            // Nobody awaits a route callback: recorded instead, and answered, so that the page does not wait forever.
            problems.push(`no answer could be built for ${JSON.stringify(body)}: ${String(error)}`);
            answer = {status: 500, body: {detail: {error_code: 'SIMULATION_FAILED'}}};
        }
        await route.fulfill({status: answer.status, headers: answer.headers, json: answer.body});
    };
    await page.route(isLinks, handler);
    return {requests, problems, unroute: () => page.unroute(isLinks, handler)};
}

/** The instance read as asked, at least once, by this page: the precondition of every presence and absence below. */
function expectServed(instance: InstanceEmailStub, links: boolean): void {
    expect(instance.problems, 'the simulated GET /system/instance answered as asked').toEqual([]);
    expect(instance.served.length, 'the page read the instance configuration through the stub').toBeGreaterThan(0);
    const asAsked = instance.served.every((email) => email.links === links);
    expect(asAsked, `every read said email.links ${links}`).toBe(true);
}

/** Sign the administrator in and open Settings › Users by its address; ends on the tab settled. */
async function openUsersTab(page: Page): Promise<void> {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings?tab=users');
    await expect(page.getByTestId('settings-tab-users'), '?tab=users opens it').toHaveAttribute('aria-selected', 'true', {timeout: LOAD_MS});
    await expect(page.getByTestId('users-tab'), 'The tab settles: GET /users and GET /users/invites are in').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
}

/** Invite `email` through the tab's dialog; ends on the link step, the link shown. */
async function inviteThroughDialog(page: Page, email: string): Promise<{dialog: Locator; share: Locator}> {
    const button = page.getByTestId('users-invite-button');
    await expect(button, 'Invite is enabled: registration is open on the lane, which sets no user limit').toBeEnabled({timeout: UI_MS});
    await button.click();
    const dialog = page.getByTestId('users-invite-dialog');
    await expect(dialog).toBeVisible({timeout: UI_MS});
    const field = dialog.getByTestId('users-invite-email');
    await field.fill(email);
    await expect(field).toHaveValue(email, {timeout: UI_MS});
    const since = await eventSeq(page);
    await dialog.getByTestId('users-invite-create').click();
    await waitForEvent(page, 'accounts.invite.created', {since, timeout: ACTION_MS});
    const share = dialog.getByTestId('link-share');
    await expect(share, 'The link step follows the invitation').toHaveAttribute('data-purpose', 'invite', {timeout: UI_MS});
    await expect(share.getByTestId('link-share-link')).toHaveValue(/\/invite#token=/, {timeout: UI_MS});
    return {dialog, share};
}

/** Issue a reset link for `account` through its row's dialog; ends on the link step, the link shown. */
async function resetThroughDialog(page: Page, account: Registered): Promise<{dialog: Locator; share: Locator}> {
    const row = page.locator(`[data-testid="users-row"][data-user-id="${account.id}"]`);
    await expect(row, `The tab lists ${account.username}, registered before it loaded`).toBeVisible({timeout: LOAD_MS});
    await expect(page.getByTestId('users-tab'), 'No reload in flight, which could redraw the row under the click').toHaveAttribute('data-busy', 'false', {timeout: ACTION_MS});
    const toggle = row.getByTestId('users-row-toggle');
    await expect(toggle).toBeVisible({timeout: UI_MS});
    // Asked first: a panel may already be open, and a blind click would close it.
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true', {timeout: UI_MS});
    const reset = row.getByTestId('users-action-reset-link');
    await expect(reset).toBeEnabled({timeout: UI_MS});
    await reset.click();
    const dialog = page.getByTestId('users-reset-dialog');
    await expect(dialog).toBeVisible({timeout: UI_MS});
    const since = await eventSeq(page);
    await dialog.getByTestId('users-reset-create').click();
    await waitForEvent(page, 'accounts.reset-link.created', {since, timeout: ACTION_MS});
    const share = dialog.getByTestId('link-share');
    await expect(share, 'The link step follows').toHaveAttribute('data-purpose', 'password_reset', {timeout: UI_MS});
    await expect(share.getByTestId('link-share-link')).toHaveValue(/\/reset-password#token=/, {timeout: UI_MS});
    return {dialog, share};
}

/** The token the link shown carries in its fragment. */
async function tokenShown(share: Locator): Promise<string> {
    const link = await share.getByTestId('link-share-link').inputValue();
    const token = new URLSearchParams(new URL(link).hash.slice(1)).get('token');
    if (!token) throw new Error(`The link ${link} carries no token in its fragment`);
    return token;
}

// A test signs in through the form (login() alone may take 70 s on a loaded lane: auth.spec.ts), loads the tab and
// issues a link: a budget below the waits it contains would end a slow red on the test timeout, which names nothing.
test.setTimeout(180_000);

test.describe('«Send by email» in the share dialogs — links ready', () => {
    test('ESL-E-01: an invitation — prefilled with its address; on the instance’s language posts {purpose, token, to} and no language; «sent» with the address and the language answered, and the event', async ({page, owned}) => {
        const email = owned.inviteAddress('sent');
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateLinkServer(page, sentAnswer('invite', email));
        try {
            await openUsersTab(page);
            const {dialog, share} = await inviteThroughDialog(page, email);
            const token = await tokenShown(share);
            expectServed(instance, true);
            const action = dialog.getByTestId('send-link-email');
            await expect(action, '«send by email» is offered in the link step').toBeVisible({timeout: UI_MS});
            await expect(action).toHaveAttribute('data-purpose', 'invite');
            await expect(action.getByTestId('send-link-email-to'), 'prefilled with the address written in the invitation').toHaveValue(email);

            const since = await eventSeq(page);
            await action.getByTestId('send-link-email-button').click();

            // The round trip first, then what it carried: a wrong body is then named, instead of an event never seen.
            const outcome = action.getByTestId('send-link-email-outcome');
            await expect(outcome, 'the request is answered').toHaveAttribute('data-outcome', /^(sent|failed)$/, {timeout: ACTION_MS});
            expect(server.requests, 'one request: the token of the link shown and the address, nothing else').toEqual([{method: 'POST', body: {purpose: 'invite', token, to: email}}]);
            expect(server.requests[0].body, 'left on the instance’s language: no language key at all, the backend decides').not.toHaveProperty('language');
            expect(server.problems, 'the simulated server answered as asked').toEqual([]);
            await expect(outcome).toHaveAttribute('data-outcome', 'sent');
            await expect(outcome, 'the language the server answered: the instance’s default, en on the simulated server').toHaveAttribute('data-language', 'en');
            await expect(outcome, 'the outcome names where the email went, as the server answered it').toContainText(email);
            const sent = await waitForEvent(page, 'email.link.sent', {since, timeout: ACTION_MS});
            expect(sent.detail, 'the event names the purpose and the language the email went in').toEqual({purpose: 'invite', language: 'en'});
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });

    test('ESL-E-02: a reset link — no address to type nor language to choose, the account’s own address said; posts {purpose, token} without to or language; «sent», and the event', async ({page, owned}) => {
        const account = await owned.register('reset');
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateLinkServer(page, sentAnswer('password_reset', account.email));
        try {
            await openUsersTab(page);
            const {dialog, share} = await resetThroughDialog(page, account);
            const token = await tokenShown(share);
            expectServed(instance, true);
            const action = dialog.getByTestId('send-link-email');
            await expect(action, '«send by email» is offered in the link step').toBeVisible({timeout: UI_MS});
            await expect(action).toHaveAttribute('data-purpose', 'password_reset');
            await expect(action.getByTestId('send-link-email-target'), 'a reset link goes to its account’s own address, said instead of a field').toBeVisible();
            await expect(action.getByTestId('send-link-email-to'), 'no address to type for a reset link').toHaveCount(0);
            await expect(action.getByTestId('send-link-email-language'), 'no language to choose: a reset link’s email goes in its account’s language').toHaveCount(0);

            const since = await eventSeq(page);
            await action.getByTestId('send-link-email-button').click();

            const sent = await waitForEvent(page, 'email.link.sent', {since, timeout: ACTION_MS});
            expect(sent.detail).toEqual({purpose: 'password_reset', language: 'en'});
            const outcome = action.getByTestId('send-link-email-outcome');
            await expect(outcome).toHaveAttribute('data-outcome', 'sent');
            await expect(outcome, 'the language the server answered').toHaveAttribute('data-language', 'en');
            expect(server.requests, 'one request: the token alone, no address, no language').toEqual([{method: 'POST', body: {purpose: 'password_reset', token}}]);
            expect(server.problems, 'the simulated server answered as asked').toEqual([]);
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });

    test('ESL-E-03: a 429 EMAIL_RATE_LIMITED — «failed», the wait recorded in the event, the action still offered', async ({page, owned}) => {
        const email = owned.inviteAddress('limit');
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateLinkServer(page, {
            status: 429,
            headers: {'Retry-After': '1800'},
            body: {detail: {error_code: 'EMAIL_RATE_LIMITED', retry_after: 1800, message: 'The hourly email limit of the instance is reached'}},
        });
        try {
            await openUsersTab(page);
            const {dialog} = await inviteThroughDialog(page, email);
            const action = dialog.getByTestId('send-link-email');
            await expect(action).toBeVisible({timeout: UI_MS});

            const since = await eventSeq(page);
            await action.getByTestId('send-link-email-button').click();

            const failed = await waitForEvent(page, 'email.link.sendFailed', {since, timeout: ACTION_MS});
            expect(failed.detail, 'read from the refusal as the generated client raises it, the wait included').toEqual({purpose: 'invite', errorCode: 'EMAIL_RATE_LIMITED', retryAfter: 1800});
            await expect(action.getByTestId('send-link-email-outcome')).toHaveAttribute('data-outcome', 'failed');
            await expect(action.getByTestId('send-link-email-button'), 'still offered: the wait is the server’s to enforce').toBeEnabled();
            const methods = server.requests.map(({method}) => method);
            expect(methods, 'one request').toEqual(['POST']);
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });

    test('ESL-E-05: an invitation in Italiano — chosen in its language select; posts exactly {purpose, token, to, language: it}; «sent» in the language answered, and the event', async ({page, owned}) => {
        const email = owned.inviteAddress('lang');
        const instance = await serveInstanceEmail(page, {available: true, links: true});
        const server = await simulateLinkServer(page, sentAnswer('invite', email));
        try {
            await openUsersTab(page);
            const {dialog, share} = await inviteThroughDialog(page, email);
            const token = await tokenShown(share);
            expectServed(instance, true);
            const action = dialog.getByTestId('send-link-email');
            await expect(action, '«send by email» is offered in the link step').toBeVisible({timeout: UI_MS});
            await expect(action).toHaveAttribute('data-purpose', 'invite');

            const trigger = action.getByTestId('send-link-email-language-button');
            await expect(trigger, 'an invitation offers the language of its email').toBeEnabled({timeout: UI_MS});
            await trigger.click();
            const list = action.getByTestId('send-link-email-language-dropdown');
            await expect(list, 'the select opens its list').toBeVisible({timeout: UI_MS});
            await expect(list.getByTestId('send-link-email-language-option-instance'), 'the instance’s language is chosen by default').toHaveAttribute('aria-selected', 'true');
            await list.getByTestId('send-link-email-language-option-it').click();
            await expect(list, 'a choice closes the list').toHaveCount(0, {timeout: UI_MS});

            const since = await eventSeq(page);
            await action.getByTestId('send-link-email-button').click();

            // The round trip first, then what it carried: a wrong body is then named, instead of an event never seen.
            const outcome = action.getByTestId('send-link-email-outcome');
            await expect(outcome, 'the request is answered').toHaveAttribute('data-outcome', /^(sent|failed)$/, {timeout: ACTION_MS});
            expect(server.requests, 'one request: the token of the link shown, the address and the language chosen, nothing else').toStrictEqual([{method: 'POST', body: {purpose: 'invite', token, to: email, language: 'it'}}]);
            expect(server.problems, 'the simulated server answered as asked').toEqual([]);
            await expect(outcome).toHaveAttribute('data-outcome', 'sent');
            await expect(outcome, 'the language the server answered, which echoes the one asked for').toHaveAttribute('data-language', 'it');
            const sent = await waitForEvent(page, 'email.link.sent', {since, timeout: ACTION_MS});
            expect(sent.detail, 'the event names the purpose and the language the email went in').toEqual({purpose: 'invite', language: 'it'});
        } finally {
            await server.unroute();
            await instance.dispose();
        }
    });
});

test.describe('«Send by email» in the share dialogs — links not ready', () => {
    test('ESL-E-04: email available but no links — the link step is drawn, its copy button and actions row there, and no «send by email»', async ({page, owned}) => {
        const email = owned.inviteAddress('hidden');
        const instance = await serveInstanceEmail(page, {available: true, links: false});
        try {
            await openUsersTab(page);
            const {dialog, share} = await inviteThroughDialog(page, email);
            expectServed(instance, false);
            // Presence first: the link step and its siblings are there, so the absence below is of the action alone.
            await expect(share.getByTestId('link-share-copy')).toBeVisible({timeout: UI_MS});
            await expect(share.getByTestId('link-share-actions')).toBeAttached();
            await expect(dialog.getByTestId('send-link-email')).toHaveCount(0);
        } finally {
            await instance.dispose();
        }
    });
});
