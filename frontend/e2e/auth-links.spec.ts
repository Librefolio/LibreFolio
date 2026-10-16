/**
 * The account link pages (release 1.3, workstream A, accounts lots A5b and A7b): `/invite`, `/reset-password` and
 * `/setup`.
 *
 * An administrator issues a single-use link over the API — `POST /users/invites`, `POST /users/{id}/password-reset-link`
 * — and hands its path over: `/invite#token=…`, `/reset-password#token=…`. The token rides in the fragment, which the
 * browser never sends, so it stays out of every request line an access log or a proxy records. The page that opens takes
 * it out of the address bar at once (the URL becomes the page's path alone: no fragment, no query), asks
 * `POST /auth/tokens/inspect` what the token is worth, then either offers the card the link opens — the registration in
 * invite mode, or a new password — or says why it cannot: `link-status`, whose `data-status` is one of checking,
 * expired, consumed, revoked, unknown, missing, closed, error.
 *
 * Covered, through the real pages and the lane's real backend:
 *   - an invitation with an address: the address prefilled and editable, the account it opens signing in as an ordinary
 *     member, and the same link, opened again, spent;
 *   - in that flow and in the reset one, the token in no request line: only in the fragment and in request bodies;
 *   - an invitation that makes an administrator, which says so before anyone registers;
 *   - a revoked invitation;
 *   - a valid invitation on an instance by invitation only, which opens the registration, and on one whose registration
 *     is disabled, which says it is closed: both modes served to that page alone (fixtures/instance-config.ts), the lane
 *     staying open;
 *   - a password-reset link: the account it names, a new password, and afterwards only the new password signs in;
 *   - a token nobody issued; a page opened without a token, which sends no inspection; the way back to the login page;
 *   - the setup link of the initial administrator, `/setup#token=…` (A7b), as a link that cannot be used: a token nobody
 *     issued, inspected for `admin_setup` and unknown, the page staying on `/setup`; no token; a token in the query,
 *     never read.
 * Not here: `expired` (an invitation lives 7 days, a reset link 30 minutes, and no API backdates one) and `error` with
 * its retry — a clock and a failing server are for the pages' unit tests to fake — nor the registration mode pinned by an
 * environment variable, which the plan leaves to Vitest (A5b.1). Nor a setup link that works, nor a blocked instance:
 * only the administrator `LIBREFOLIO_ADMIN_EMAIL` creates at startup, on an instance without accounts, has a setup link,
 * and the lane runs without that variable — those are the setup page's unit tests', against a mocked API
 * (src/routes/setup/page.test.ts).
 *
 * Ownership. Each test creates its own invitations and accounts, and records each one the moment it exists, or, for an
 * account registered through the page, just before. The `links` fixture removes them after the test, red or green:
 * every invitation still pending is revoked (`DELETE /users/invites/{id}`; a 404 is an invitation already spent or
 * revoked), every account deletes itself (`DELETE /auth/users/me`, signed in as that very account, its identity
 * checked first). Nothing reads a list it did not fill, and nothing changes the lane's registration mode, which is open
 * there. The `/setup` tests create nothing: every token they open is one nobody issued. Parallel by default: no test
 * depends on another.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `auth-links` of front-utility.
 */
import {expect, test as base, type APIRequestContext, type Page, type Request, type Response as PageResponse} from './fixtures/playwright';
import {login} from './fixtures/auth-helpers';
import {INSTANCE_CONFIG_PATH, serveRegistrationMode} from './fixtures/instance-config';
import {TEST_ADMIN} from './fixtures/test-users';
import {uniqueSuffix, uniqueToken} from './fixtures/unique';

const API = '/api/v1';
const INSPECT_PATH = `${API}/auth/tokens/inspect`;

// The round trips before a page shows anything — the SPA's first load, the token's inspection, `GET /auth/me` on `/` —
// are the first steps a busy lane delays: the budgets auth.spec.ts gives the same steps. A deadline, never a delay.
const FIRST_PAINT_MS = 20_000;
const SIGN_IN_MS = 20_000;
// After a sign-in: the routing budgets auth.spec.ts gives a new account's arrival on /welcome.
const ROUTED_MS = 15_000;
const LANDED_MS = 10_000;

/** The pages a link opens, and the container each one renders. */
const LINK_PAGES = {
    invite: {path: '/invite', testId: 'invite-page'},
    reset: {path: '/reset-password', testId: 'reset-password-page'},
    setup: {path: '/setup', testId: 'setup-page'},
} as const;
type LinkPage = keyof typeof LINK_PAGES;

// Every password meets the app's five rules: eight characters, an upper case, a lower case, a digit, a special one.
const INVITED_PASSWORD = 'Invite-Pass123!';
const OLD_PASSWORD = 'Before-Reset123!';
const NEW_PASSWORD = 'After-Reset456!';

/** A single-use link as the administrator receives it: the token, and the path of the page that takes it, the token in its fragment. */
type Link = {token: string; path: string};
type Invite = Link & {id: number; email: string | null; grantsAdmin: boolean};
/** An account a test creates. `passwords`: every password it may hold, the current one first; `id`: null until known. */
type Account = {id: number | null; username: string; email: string; passwords: string[]};
type SignedIn = {id: number; username: string; email: string; is_superuser: boolean};
type Owned = {invites: Invite[]; accounts: Account[]};

/** What a test may ask of the administrator, every row it creates recorded for the clean-up. */
type Links = {
    /** An invitation, recorded for the clean-up the moment it exists. */
    invite(options?: {email?: string; grantsAdmin?: boolean}): Promise<Invite>;
    /** Revoke an invitation that must still be pending: a 204, or the test fails. */
    revoke(invite: Invite): Promise<void>;
    /** A disposable account registered over the public API, recorded before the request goes. */
    registerAccount(tag: string, password: string): Promise<Account>;
    /** Record an account the test is about to create through a page, before it exists, so that a red still removes it. */
    track(account: Account): Account;
    /** A password-reset link for `account`. */
    resetLink(account: Account): Promise<Link>;
};

async function signInAdministrator(admin: APIRequestContext): Promise<void> {
    const response = await admin.post(`${API}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    expect(response.status(), `Sign-in of ${TEST_ADMIN.username}, who issues the links`).toBe(200);
    const {user} = (await response.json()) as {user: SignedIn};
    expect(user.is_superuser, `${TEST_ADMIN.username} must be an administrator: only an administrator issues links`).toBe(true);
}

function linksOf(admin: APIRequestContext, open: () => Promise<APIRequestContext>, owned: Owned): Links {
    const track = (account: Account): Account => {
        owned.accounts.push(account);
        return account;
    };
    return {
        async invite({email, grantsAdmin = false} = {}) {
            const response = await admin.post(`${API}/users/invites`, {data: {grants_admin: grantsAdmin, ...(email === undefined ? {} : {email})}});
            expect(response.status(), `POST /users/invites: ${await response.text()}`).toBe(201);
            const body = (await response.json()) as {invite: {id: number; email: string | null; grants_admin: boolean}; token: string; path: string};
            const invite: Invite = {id: body.invite.id, email: body.invite.email, grantsAdmin: body.invite.grants_admin, token: body.token, path: body.path};
            owned.invites.push(invite);
            return invite;
        },

        async revoke(invite) {
            const response = await admin.delete(`${API}/users/invites/${invite.id}`);
            expect(response.status(), `DELETE /users/invites/${invite.id}: the invitation must still be pending (a 404 is one already spent or revoked)`).toBe(204);
        },

        async registerAccount(tag, password) {
            const suffix = uniqueSuffix();
            const account = track({id: null, username: `lnk_${tag}_${suffix}`, email: `lnk_${tag}_${suffix}@example.com`, passwords: [password]});
            const anonymous = await open();
            const response = await anonymous.post(`${API}/auth/register`, {data: {username: account.username, email: account.email, password}});
            expect(response.status(), `Registration is open on the lane and no E2E spec changes it, yet POST /auth/register answered: ${await response.text()}`).toBe(201);
            const {user} = (await response.json()) as {user: SignedIn};
            account.id = user.id;
            return account;
        },

        track,

        async resetLink(account) {
            if (account.id === null) throw new Error(`${account.username} has no id yet: a reset link needs an account that exists`);
            const response = await admin.post(`${API}/users/${account.id}/password-reset-link`);
            expect(response.status(), `POST /users/${account.id}/password-reset-link: ${await response.text()}`).toBe(201);
            const {token, path} = (await response.json()) as Link;
            return {token, path};
        },
    };
}

/**
 * The account deletes itself: signed in on its own context with the first of its passwords that opens it, once the
 * session is checked to be that very account. Returns why it could not, or null. An account that no password opens was
 * never created — a registration the test did not reach — unless its id is known, and then it is a failure.
 */
async function deleteAccount(api: APIRequestContext, account: Account): Promise<string | null> {
    for (const password of account.passwords) {
        const signedIn = await api.post(`${API}/auth/login`, {data: {username: account.username, password}});
        if (signedIn.status() === 401) continue;
        if (signedIn.status() !== 200) return `account ${account.username}: the sign-in answered ${signedIn.status()}`;
        const {user} = (await signedIn.json()) as {user: SignedIn};
        if (user.username !== account.username || (account.id !== null && user.id !== account.id)) {
            return `account ${account.username}: the session opened is ${user.username} (id ${user.id}), not the account to remove`;
        }
        const removed = await api.delete(`${API}/auth/users/me`);
        return removed.ok() ? null : `account ${account.username}: DELETE /auth/users/me answered ${removed.status()}`;
    }
    return account.id === null ? null : `account ${account.username} (id ${account.id}): none of its passwords signs in, so it cannot remove itself`;
}

/** Remove, by id, what the test created. Never throws, so it never masks the test's own failure: it returns what it could not remove. */
async function cleanUp(admin: APIRequestContext, open: () => Promise<APIRequestContext>, owned: Owned): Promise<string[]> {
    const failures: string[] = [];
    for (const invite of owned.invites) {
        try {
            const response = await admin.delete(`${API}/users/invites/${invite.id}`);
            // 204: it was still pending, and is revoked now. 404: it no longer was — spent, or revoked by the test itself.
            if (response.status() !== 204 && response.status() !== 404) failures.push(`invitation ${invite.id}: DELETE answered ${response.status()}`);
        } catch (error) {
            failures.push(`invitation ${invite.id}: ${String(error)}`);
        }
    }
    for (const account of owned.accounts) {
        try {
            const failure = await deleteAccount(await open(), account);
            if (failure) failures.push(failure);
        } catch (error) {
            failures.push(`account ${account.username}: ${String(error)}`);
        }
    }
    return failures;
}

const test = base.extend<{links: Links}>({
    links: async ({playwright, baseURL}, use) => {
        const contexts: APIRequestContext[] = [];
        const open = async (): Promise<APIRequestContext> => {
            const context = await playwright.request.newContext({baseURL});
            contexts.push(context);
            return context;
        };
        const owned: Owned = {invites: [], accounts: []};
        let admin: APIRequestContext | undefined;
        let failures: string[] = [];
        try {
            admin = await open();
            await signInAdministrator(admin);
            await use(linksOf(admin, open, owned));
        } finally {
            if (admin) failures = await cleanUp(admin, open, owned);
            await Promise.all(contexts.map((context) => context.dispose()));
        }
        expect(failures, 'The clean-up must revoke every invitation still pending and remove every account the test created').toEqual([]);
    },
});

// The longest test opens a link page twice and signs in once: login() alone may take 70 s and the landing 25 s
// (auth.spec.ts), and each link page has a first paint of up to 20 s. A budget below the waits it contains would end a
// slow red on the test timeout, which names nothing, instead of on its own assertion.
test.setTimeout(180_000);

/** Only resolves a relative path, so that its parts can be read. */
const ANY_ORIGIN = 'http://localhost';

/** The token a link path carries in its fragment (`#token=…`), or null. */
function tokenInFragment(path: string): string | null {
    return new URLSearchParams(new URL(path, ANY_ORIGIN).hash.slice(1)).get('token');
}

/** A link built by hand, in the form the backend issues: the page's path, the token in the fragment. */
function handBuiltLink(kind: LinkPage, token: string): Link {
    return {token, path: `${LINK_PAGES[kind].path}#${new URLSearchParams({token})}`};
}

/** Where a token could stay in the address bar: the page's path, its query, its fragment. */
function addressOf(page: Page): {path: string; query: string; fragment: string} {
    const url = new URL(page.url());
    return {path: url.pathname, query: url.search, fragment: url.hash};
}

/**
 * Open a link page from its path, as the person who received the link would: in a new document. A `page.goto` to an
 * address that differs from the current one only by its fragment is a same-document navigation — no reload, so a page
 * that reads its token on load never reads it — hence the stop at about:blank first. Ends once the page is up and has
 * taken the token out of the address bar: no fragment, no query, the page's path alone.
 */
async function openLink(page: Page, kind: LinkPage, link: Link): Promise<void> {
    const {path, testId} = LINK_PAGES[kind];
    // Precondition, verified: the token rides in the fragment, or «the token left the address bar» would hold without the
    // page; and nowhere a server would see it.
    const handedOver = new URL(link.path, ANY_ORIGIN);
    expect(handedOver.pathname, `The link opens ${path}`).toBe(path);
    expect(tokenInFragment(link.path), 'The link carries its token in the fragment').toBe(link.token);
    expect(handedOver.pathname + handedOver.search, 'The token never travels in the path or the query: both reach the server and its logs').not.toContain(link.token);

    await page.goto('about:blank');
    await page.goto(link.path);
    await expect(page.getByTestId(testId)).toBeVisible({timeout: FIRST_PAINT_MS});
    await expect.poll(() => addressOf(page), {message: `${path} takes the token out of the address bar on load: no fragment, no query, the path alone`, timeout: FIRST_PAINT_MS}).toEqual({path, query: '', fragment: ''});
}

/**
 * The request line of every request the page sends from now on — path and query, what an access log or a proxy records —
 * across navigations. Arm it before the first `goto`. A fragment is never sent; it is cut here all the same, so that a
 * line is what the server receives whatever `request.url()` reports.
 */
function recordRequestLines(page: Page): string[] {
    const lines: string[] = [];
    page.on('request', (request: Request) => {
        const sent = request.url().split('#', 1)[0];
        try {
            const {pathname, search} = new URL(sent);
            lines.push(pathname + search);
        } catch {
            lines.push(sent);
        }
    });
    return lines;
}

/** `token` reached the server in request bodies only: no request line carries it. The record is proved live first. */
function expectInNoRequestLine(lines: readonly string[], token: string, pagePath: string): void {
    // Positive controls: the record holds the page's own load and its inspection, so an empty match below means something.
    expect(lines, `The record holds the load of ${pagePath}`).toContain(pagePath);
    expect(lines, `The record holds the page's POST ${INSPECT_PATH}`).toContain(INSPECT_PATH);
    expect(
        lines.filter((line) => line.includes(token)),
        'The token travels in the fragment and in request bodies, never in a request line: access logs and proxies record those',
    ).toEqual([]);
}

/** Every `POST /auth/tokens/inspect` the page sends from now on, by body, across navigations. Arm it before the first `goto`. */
function recordInspections(page: Page): unknown[] {
    const bodies: unknown[] = [];
    page.on('request', (request: Request) => {
        if (request.method() !== 'POST' || new URL(request.url()).pathname !== INSPECT_PATH) return;
        try {
            bodies.push(request.postDataJSON());
        } catch {
            bodies.push(request.postData());
        }
    });
    return bodies;
}

/** The page asked about `token`, for `purpose`: at least once, and never about anything else. */
async function expectAskedOnlyAbout(bodies: unknown[], token: string, purpose: 'invite' | 'password_reset' | 'admin_setup'): Promise<void> {
    await expect.poll(() => bodies.length, {message: `The page never sent POST ${INSPECT_PATH}`, timeout: 5_000}).toBeGreaterThan(0);
    expect(bodies, `Every POST ${INSPECT_PATH} asks about the token of the link, for ${purpose}`).toEqual(bodies.map(() => ({token, purpose})));
}

/** A new account has signed in: the bootstrap routes it to its first Welcome, behind the bare shell (auth.spec.ts). */
async function expectLandedOnWelcome(page: Page): Promise<void> {
    await expect(page).toHaveURL(/\/welcome/, {timeout: ROUTED_MS});
    await expect(page.getByTestId('welcome-shell')).toBeVisible({timeout: LANDED_MS});
}

/** The account the browser is signed in as, through the page's own cookies. */
async function signedInAs(page: Page): Promise<SignedIn> {
    const response = await page.request.get(`${API}/auth/me`);
    expect(response.status(), 'GET /auth/me through the browser session').toBe(200);
    return ((await response.json()) as {user: SignedIn}).user;
}

/** The body of a browser response, for a failure message: it may be gone once the page has moved on, which must not throw. */
async function bodyOf(response: PageResponse): Promise<string> {
    return response.text().catch((error: unknown) => `(body unavailable: ${String(error)})`);
}

test.describe('Invitation links (/invite)', () => {
    test('an invitation with an address: the token leaves the address bar, the address is prefilled and editable, the account signs in as an ordinary member, and the link is spent', async ({page, links}) => {
        const suffix = uniqueSuffix();
        const invite = await links.invite({email: `lnk_inv_${suffix}@example.com`});
        // Precondition, verified: the invitation kept the address the page is about to prefill.
        const invitedEmail = invite.email;
        if (!invitedEmail) throw new Error(`POST /users/invites returned invitation ${invite.id} without the address it was given`);
        const card = page.getByTestId('register-modal');
        const sent = recordRequestLines(page);

        await test.step('the link opens the registration in invite mode', async () => {
            await openLink(page, 'invite', invite);
            await expect(card, 'A valid invitation opens the registration').toBeVisible({timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('register-invite-notice')).toBeVisible();
            await expect(page.getByTestId('register-invite-admin-notice'), 'An invitation that grants no role says nothing about administrators').toBeHidden();
            const emailField = card.getByTestId('register-email');
            await expect(emailField, 'The address of the invitation comes prefilled').toHaveValue(invitedEmail);
            await expect(emailField, 'and stays editable').toBeEditable();
        });

        const account = links.track({id: null, username: `lnk_inv_${suffix}`, email: invitedEmail, passwords: [INVITED_PASSWORD]});
        await test.step('registering through the invitation ends on the login page, with the success message', async () => {
            const username = card.getByTestId('register-username');
            await username.fill(account.username);
            await expect(username).toHaveValue(account.username);
            await card.getByTestId('register-password').fill(INVITED_PASSWORD);
            await card.getByTestId('register-confirm-password').fill(INVITED_PASSWORD);
            // The request is a subject: the token taken out of the address bar is the one the registration spends.
            const registered = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === `${API}/auth/register`, {timeout: SIGN_IN_MS});
            await card.getByTestId('register-submit').click();
            const answer = await registered;
            expect(answer.request().postDataJSON(), 'The registration carries the token of the invitation').toMatchObject({username: account.username, email: invitedEmail, invite_token: invite.token});
            expect(answer.status(), `POST /auth/register: ${await bodyOf(answer)}`).toBe(201);
            await expect(page, 'A registration through an invitation ends on the login page').toHaveURL((url) => url.pathname === '/', {timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('login-success'), 'with the success message the invitation page handed over').toBeVisible({timeout: FIRST_PAINT_MS});
        });

        // Still signed out: what the page shows a returning visitor, not a signed-in one.
        await test.step('the same link, opened again, is spent', async () => {
            await openLink(page, 'invite', invite);
            await expect(page.getByTestId('link-status'), 'An invitation used once is consumed').toHaveAttribute('data-status', 'consumed', {timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
            await expect(page.getByTestId('register-modal'), 'A spent invitation opens no registration').toBeHidden();
        });

        await test.step('the token never travelled in a request line: two loads, an inspection each, a registration', async () => {
            expectInNoRequestLine(sent, invite.token, LINK_PAGES.invite.path);
        });

        await test.step('the new credentials sign in: an ordinary member, on its first Welcome', async () => {
            await login(page, {username: account.username, email: account.email, password: INVITED_PASSWORD});
            await expectLandedOnWelcome(page);
            const me = await signedInAs(page);
            account.id = me.id;
            expect(me, 'The invitation grants no role: the account is an ordinary member, registered with the address of the invitation').toMatchObject({username: account.username, email: invitedEmail, is_superuser: false});
        });
    });

    test('an invitation that makes an administrator says so before anyone registers; without an address, the field starts empty', async ({page, links}) => {
        const invite = await links.invite({grantsAdmin: true});
        expect(invite.grantsAdmin, 'POST /users/invites keeps grants_admin').toBe(true);

        await openLink(page, 'invite', invite);
        const card = page.getByTestId('register-modal');
        await expect(card, 'A valid invitation opens the registration').toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('register-invite-notice')).toBeVisible();
        await expect(page.getByTestId('register-invite-admin-notice'), 'The invitation makes an administrator: the page says so before anyone registers').toBeVisible();
        const emailField = card.getByTestId('register-email');
        await expect(emailField, 'An invitation without an address prefills nothing').toHaveValue('');
        await expect(emailField).toBeEditable();

        // Nobody registers. Opening the page only inspected the link: the invitation is still pending, and goes now.
        await links.revoke(invite);
    });

    test('a revoked invitation says so, and opens no registration', async ({page, links}) => {
        const invite = await links.invite();
        await links.revoke(invite);

        await openLink(page, 'invite', invite);
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'revoked', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
        await expect(page.getByTestId('register-modal'), 'A revoked invitation opens no registration').toBeHidden();
    });
});

// The lane is open, so the two other modes are served to the page alone (fixtures/instance-config.ts) and the lane stays
// open. A valid invitation opens the registration in every mode but disabled («token valido e registrazione non
// `disabled` → RegisterCard», plan A5b.1), and disabled refuses everyone, an invitation included (D-A3). Each invitation
// stays pending: the clean-up revokes it.
test.describe('Invitation links under another registration mode, served to the page alone', () => {
    test('by invitation only, a valid invitation still opens the registration', async ({page, links}) => {
        const invite = await links.invite();
        const stub = await serveRegistrationMode(page, 'invite');
        try {
            await openLink(page, 'invite', invite);
            await expect.poll(() => stub.answered, {message: `The invitation page never read GET ${INSTANCE_CONFIG_PATH}: it cannot know how this instance registers accounts`, timeout: FIRST_PAINT_MS}).toBeGreaterThan(0);
            expect(stub.problems, "The stub could not answer registration_mode 'invite': the precondition is broken, not the page").toEqual([]);

            await expect(page.getByTestId('register-modal'), 'Invitation only is what an invitation is for: the registration opens').toBeVisible({timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('register-invite-notice')).toBeVisible();
        } finally {
            await stub.dispose();
        }
    });

    test('disabled, a valid invitation says registration is closed', async ({page, links}) => {
        const invite = await links.invite();
        const stub = await serveRegistrationMode(page, 'disabled');
        try {
            await openLink(page, 'invite', invite);
            await expect.poll(() => stub.answered, {message: `The invitation page never read GET ${INSTANCE_CONFIG_PATH}: it cannot know that registration is disabled`, timeout: FIRST_PAINT_MS}).toBeGreaterThan(0);
            expect(stub.problems, "The stub could not answer registration_mode 'disabled': the precondition is broken, not the page").toEqual([]);

            await expect(page.getByTestId('link-status'), 'Disabled refuses everyone, an invitation included: the page says so instead of opening a registration the server would refuse').toHaveAttribute('data-status', 'closed', {timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
            await expect(page.getByTestId('register-modal'), 'A closed instance opens no registration').toBeHidden();
        } finally {
            await stub.dispose();
        }
    });
});

test.describe('Password-reset links (/reset-password)', () => {
    test('a reset link names its account and takes a new password; afterwards only the new password signs in', async ({page, links}) => {
        const account = await links.registerAccount('rst', OLD_PASSWORD);
        const link = await links.resetLink(account);
        const card = page.getByTestId('reset-password-modal');
        const sent = recordRequestLines(page);

        await test.step('the link opens the new-password card of that account', async () => {
            await openLink(page, 'reset', link);
            await expect(card, 'A valid reset link opens the new-password card').toBeVisible({timeout: FIRST_PAINT_MS});
            await expect(card.getByTestId('reset-password-account'), 'The card names the account the link resets').toContainText(account.username);
        });

        await test.step('a new password ends on the login page, with the success message', async () => {
            // Recorded before it is set: from the submit on, the clean-up tries it first.
            account.passwords.unshift(NEW_PASSWORD);
            const fresh = card.getByTestId('reset-password-new');
            await fresh.fill(NEW_PASSWORD);
            await expect(fresh).toHaveValue(NEW_PASSWORD);
            const confirmation = card.getByTestId('reset-password-confirm');
            await confirmation.fill(NEW_PASSWORD);
            await expect(confirmation).toHaveValue(NEW_PASSWORD);
            const submit = card.getByTestId('reset-password-submit');
            await expect(submit, 'A password meeting every rule, confirmed: the card lets it through').toBeEnabled();
            // The request is a subject: the token taken out of the address bar is the one the reset spends.
            const reset = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === `${API}/auth/password-reset`, {timeout: SIGN_IN_MS});
            await submit.click();
            const answer = await reset;
            expect(answer.request().postDataJSON(), 'The reset carries the token of the link and the new password, nothing else').toEqual({token: link.token, new_password: NEW_PASSWORD});
            expect(answer.status(), `POST /auth/password-reset: ${await bodyOf(answer)}`).toBe(200);
            await expect(page, 'A reset ends on the login page').toHaveURL((url) => url.pathname === '/', {timeout: FIRST_PAINT_MS});
            await expect(page.getByTestId('login-success'), 'with the success message the reset page handed over').toBeVisible({timeout: FIRST_PAINT_MS});
        });

        await test.step('the token never travelled in a request line: the load, its inspection, the reset', async () => {
            expectInNoRequestLine(sent, link.token, LINK_PAGES.reset.path);
        });

        await test.step('the old password no longer signs in', async () => {
            await page.getByTestId('login-username').fill(account.username);
            await page.getByTestId('login-password').fill(OLD_PASSWORD);
            // The request is the subject: the error below must be the server refusing the old password, not a failure.
            const answer = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === `${API}/auth/login`, {timeout: SIGN_IN_MS});
            await page.getByTestId('login-submit').click();
            expect((await answer).status(), 'The server refuses the old password').toBe(401);
            await expect(page.getByTestId('login-error')).toBeVisible({timeout: SIGN_IN_MS});
        });

        await test.step('the new password signs in', async () => {
            await login(page, {username: account.username, email: account.email, password: NEW_PASSWORD});
            await expectLandedOnWelcome(page);
            expect(await signedInAs(page), 'Signed in as the account the link reset').toMatchObject({id: account.id, username: account.username});
        });
    });
});

test.describe('Links without a usable token', () => {
    test('a token nobody issued is unknown, and the page asked about that very token', async ({page}) => {
        const token = uniqueToken(43);
        const asked = recordInspections(page);

        await openLink(page, 'invite', handBuiltLink('invite', token));
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'unknown', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
        await expect(page.getByTestId('register-modal'), 'An unknown token opens no registration').toBeHidden();
        await expectAskedOnlyAbout(asked, token, 'invite');
    });

    test('a reset page opened without a token says the link is missing, and asks the server nothing', async ({page}) => {
        const asked = recordInspections(page);

        await page.goto('/reset-password');
        await expect(page.getByTestId('reset-password-page')).toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'missing', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
        await expect(page.getByTestId('reset-password-modal'), 'No token, no new-password card').toBeHidden();
        expect(asked, `With no token there is nothing to inspect: no POST ${INSPECT_PATH}`).toEqual([]);

        // The positive control, and the proof that holds: a token nobody issued, opened in the same tab. openLink leaves the
        // page for about:blank first — a change of fragment alone would not even reload it — so the page above is gone,
        // and every request it ever sent is already in the record: a record holding only the control's own inspection
        // means the page without a token sent none, however late.
        const token = uniqueToken(43);
        await openLink(page, 'reset', handBuiltLink('reset', token));
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'unknown', {timeout: FIRST_PAINT_MS});
        await expectAskedOnlyAbout(asked, token, 'password_reset');
    });

    test('the way back from a link page leads to the login page', async ({page}) => {
        await page.goto('/invite');
        await expect(page.getByTestId('invite-page')).toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'missing', {timeout: FIRST_PAINT_MS});

        await page.getByTestId('link-status-goto-login').click();
        await expect(page, 'The way back leads to /').toHaveURL((url) => url.pathname === '/', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('login-page')).toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('login-modal')).toBeVisible();
    });
});

// The setup link of the initial administrator (accounts lot A7b, F02): `/setup#token=…`. Only the administrator that
// `LIBREFOLIO_ADMIN_EMAIL` creates at startup, on an instance without accounts, has one; the lane runs without that
// variable, so it holds no pending administrator and no setup link, and only links that cannot be used are tried here.
// A link that works, the setup itself and a blocked instance are the page's unit tests', against a mocked API
// (src/routes/setup/page.test.ts). Every token opened here is one nobody issued: nothing is created, nothing to clean up.
test.describe('Setup links (/setup)', () => {
    // A7b: the page takes the token out of the address bar, asks the server about it for the setup purpose, and says the
    // link cannot be used — with the setup's own line on where a new link comes from, since no administrator exists yet
    // to send one — without ever drawing the form.
    test('a setup token nobody issued: the token leaves the address bar, the page asks about it for admin_setup, says it is unknown with the setup hint, and stays on /setup', async ({page}) => {
        const token = uniqueToken(43);
        const asked = recordInspections(page);

        await openLink(page, 'setup', handBuiltLink('setup', token));
        expect(page.url(), 'The token left the address bar: the URL no longer carries it').not.toContain(token);
        await expect(page.getByTestId('link-status'), 'A token nobody issued is unknown').toHaveAttribute('data-status', 'unknown', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status-hint'), 'A link that cannot be used says where a new one comes from').toBeVisible();
        await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
        await expect(page.getByTestId('setup-card'), 'An unknown token opens no setup form').toBeHidden();
        await expectAskedOnlyAbout(asked, token, 'admin_setup');
        // A <meta> in the head carries no test id: its name is what the browser reads the referrer policy by, a contract.
        await expect(page.locator('meta[name="referrer"]'), 'The page sends no Referer: its address stays out of any link followed from it').toHaveAttribute('content', 'no-referrer');
        // A link page has no session to lose, so nothing it sends takes the visitor to the login page. Neither request this
        // page sends on the lane (GET /system/instance, the inspection) answers 401: this holds the page to its path — no
        // guard, no redirect — while the client's 401 exemption itself is on trial in zodios-client.test.ts.
        await expect(page, 'The page stays on /setup: it is not sent to the login').toHaveURL((url) => url.pathname === '/setup');
    });

    // A7b: no token, nothing to ask — the link is missing, and the page says where a new one comes from all the same.
    test('a setup page opened without a token says the link is missing, and asks the server nothing', async ({page}) => {
        const asked = recordInspections(page);

        await page.goto('/setup');
        await expect(page.getByTestId('setup-page')).toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'missing', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status-hint')).toBeVisible();
        await expect(page.getByTestId('link-status-goto-login')).toBeVisible();
        await expect(page.getByTestId('setup-card'), 'No token, no setup form').toBeHidden();
        expect(asked, `With no token there is nothing to inspect: no POST ${INSPECT_PATH}`).toEqual([]);

        // The positive control, as on the reset page: a token nobody issued, opened in the same tab. openLink leaves for
        // about:blank first, so the page above is gone with every request it ever sent already recorded: a record holding
        // only the control's inspection means the page without a token sent none, however late.
        const control = uniqueToken(43);
        await openLink(page, 'setup', handBuiltLink('setup', control));
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'unknown', {timeout: FIRST_PAINT_MS});
        await expectAskedOnlyAbout(asked, control, 'admin_setup');
    });

    // A7b: a token in the query has already reached the server in the request line, and its access log with it. No link
    // carries one there, and the page never reads it.
    test('a token in the query is never read: the setup page says the link is missing, and asks the server nothing', async ({page}) => {
        const queried = uniqueToken(43);
        const asked = recordInspections(page);

        await page.goto(`/setup?${new URLSearchParams({token: queried})}`);
        await expect(page.getByTestId('setup-page')).toBeVisible({timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('link-status'), 'A token in the query is no link: the page reads none').toHaveAttribute('data-status', 'missing', {timeout: FIRST_PAINT_MS});
        await expect(page.getByTestId('setup-card'), 'No token read, no setup form').toBeHidden();
        expect(asked, `The token in the query is never inspected: no POST ${INSPECT_PATH}`).toEqual([]);

        // The positive control, as above, with another token nobody issued, in the fragment this time: every inspection
        // in the record is about it, so none was about the token in the query.
        const control = uniqueToken(43);
        await openLink(page, 'setup', handBuiltLink('setup', control));
        await expect(page.getByTestId('link-status')).toHaveAttribute('data-status', 'unknown', {timeout: FIRST_PAINT_MS});
        await expectAskedOnlyAbout(asked, control, 'admin_setup');
    });
});
