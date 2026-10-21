/**
 * Settings → Users, the administrators' tab (release 1.3, workstream A, accounts lot A6b; plan A6b.1, test E1).
 *
 * An administrator manages the accounts of the instance from one tab: deactivates and reactivates them, promotes and
 * demotes them, issues a password-reset link or an invitation, signs an account out everywhere, restarts its guides,
 * deletes it after a preview of what goes with it. A link comes through `LinkShare`, whose address is editable and, once
 * edited, checked: a nonce of this instance (`POST /users/address-probe`), then the load of an image,
 * `GET <address>/api/v1/auth/address-probe.png?nonce=…` (H-55 v2: under the enforced `connect-src` a `fetch` to another
 * origin is blocked, an image is not), which only this very instance draws 1×1 — any other draws it 2×1.
 *
 * Covered, through the real tab and the lane's real backend, `e2e_test_admin` acting through the UI:
 *   AUSR-E-01  only an administrator has the tab, and it settles; a member has none, and `?tab=users` opens Profile;
 *   AUSR-E-02  the administrator's own row: marked as its own, a way to the profile, no action at all;
 *   AUSR-E-03  deactivate (confirmed), then reactivate;
 *   AUSR-E-04  promote and demote (confirmed), and no deletion of an administrator before its demotion;
 *   AUSR-E-05  a password-reset link, live for that very account;
 *   AUSR-E-06  an invitation: created with an address, listed, revoked (confirmed);
 *   AUSR-E-07  the address check: the lane's other loopback origin (`match`: the image drawn 1×1, its size readable across origins), a closed port
 *              (`unverifiable`), not http (`invalid`, no copy), a stubbed stranger (`mismatch`), the prefill (`idle`);
 *   AUSR-E-08  a deletion: the preview of the broker that goes, the username typed, the broker gone with the account;
 *   AUSR-E-09  signed out everywhere (confirmed): the account's open session is refused, the account stays active;
 *   AUSR-E-10  guides restarted (confirmed): every flow the account had skipped is pending again.
 * Every action is asserted on what the page publishes — `data-*` attributes and the app events of `notify` — then read
 * back on the server: through the administrator's own API session, or the account's for its session and its guides.
 * Not here, left to the Vitest of plan A6b.1: the usage line, the limit banner and the billing link, an invitation
 * refused by a closed registration or a full instance, the error codes (LAST_ADMIN, ACCOUNT_PROTECTED…), the copy itself
 * and `accounts.link.copied` (a clipboard is a browser permission), `accounts.address.checked`.
 *
 * The Users tab is a member of «Administration» (decision P13 b, lot A8b): an administrator opens the group in the top
 * bar, then Users in its second bar (`settings-subtabs`, through `openSettingsTab` of fixtures/settings-tabs.ts), or goes
 * straight to it with `?tab=users`, which opens it inside its group. A member has no «Administration» at all (N69-2,
 * decision D4 a): no group, no second bar, and no `settings-tab-users` anywhere.
 *
 * Ownership. `e2e_test_admin` only acts: no test changes its role or state, nor those of any other fixture user. Each
 * test registers its own disposable accounts anonymously (the lane registers openly: checked first, and no spec changes
 * it) and writes its own unique invitation addresses, each recorded before the request that creates it goes. The `users`
 * fixture removes them after the test, red or green: every pending invitation carrying one of its addresses is revoked
 * (found through `GET /users/invites`); every account still alive deletes itself (`DELETE /auth/users/me`, signed in as
 * that very account, its identity checked), reactivated first when the test left it deactivated, since a deactivated
 * account cannot sign in. The broker AUSR-E-08 creates goes with its account, its last owner. Rows are found by id or by
 * address, never by position, and nothing counts a list it did not fill. Parallel by default: no test depends on another.
 *
 * Registered in scripts/test_runner/_frontend_utility.py, action `admin-users` of front-utility.
 */
import {deflateSync} from 'node:zlib';
import {expect, test as base, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {eventSeq, waitForEvent, type AppEvent} from '../fixtures/app-events';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {INSTANCE_CONFIG_PATH} from '../fixtures/instance-config';
import {openSettingsTab} from '../fixtures/settings-tabs';
import {TEST_ADMIN, TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
/** Where an instance draws whether it issued a nonce (`answer_address_probe_image`): public, an image of 1×1 for its own nonce, of 2×1 for any other. */
const PROBE_PATH = `${API}/auth/address-probe.png`;

// Budgets: deadlines, never delays.
/** From a navigation to a settled tab: the SPA's load, the auth check and the bootstrap, then GET /users and GET /users/invites. */
const LOAD_MS = 20_000;
/** An action's round trip, and the reload of the tab that follows every action. */
const ACTION_MS = 15_000;
/** An address check: 500 ms without typing, a nonce from this instance, then the probe, aborted after 8 s at the latest. */
const PROBE_MS = 20_000;
/** The reaction to a click on something already on screen. */
const UI_MS = 5_000;

/** The password of every disposable account: eight characters or more, upper and lower case, a digit, a special one. */
const PASSWORD = 'Ausr-Pass123!';
/** An address nothing answers: port 1 is closed, and Chromium refuses it outright as an unsafe port. Either way the probe image fails to load. */
const CLOSED_ADDRESS = 'http://127.0.0.1:1';
/** Not http(s): `normalizeBase` refuses it before any probe. */
const INVALID_ADDRESS = 'ftp://example.invalid';
/** A host that never resolves (`.invalid`, RFC 2606): its probe exists only as the stub this page installs. */
const MISMATCH_ORIGIN = 'http://probe-mismatch.invalid';

/** The CRC-32 of a PNG chunk (ISO 3309), by table. */
const CRC_TABLE = Array.from({length: 256}, (_, n) => {
    let c = n;
    for (let bit = 0; bit < 8; bit += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
});

function crc32(bytes: Buffer): number {
    let c = 0xffffffff;
    for (const byte of bytes) c = CRC_TABLE[(c ^ byte) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type: string, data: Buffer): Buffer {
    const head = Buffer.alloc(8);
    head.writeUInt32BE(data.length, 0);
    head.write(type, 4, 'ascii');
    const crc = Buffer.alloc(4);
    crc.writeUInt32BE(crc32(Buffer.concat([head.subarray(4), data])), 0);
    return Buffer.concat([head, data, crc]);
}

/** A valid PNG of `width`×`height`, one grey level, built here: what the stub of a stranger's instance draws (a 2×1 for a nonce it did not issue). */
function pngOf(width: number, height: number): Buffer {
    const header = Buffer.alloc(13);
    header.writeUInt32BE(width, 0);
    header.writeUInt32BE(height, 4);
    header.set([8, 0, 0, 0, 0], 8); // 8 bits, greyscale, deflate, no filter method, no interlace
    const rows = Buffer.alloc((width + 1) * height); // each row: the filter byte 0, then its pixels, black
    return Buffer.concat([Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]), pngChunk('IHDR', header), pngChunk('IDAT', deflateSync(rows)), pngChunk('IEND', Buffer.alloc(0))]);
}

/** A disposable account. `id`: null until the registration answers. */
type Account = {id: number | null; username: string; email: string; password: string};
type Registered = Account & {id: number};
/** `AdminUserRead`, as `GET /users` lists it. */
type AdminUser = {id: number; username: string; email: string; is_active: boolean; is_superuser: boolean; protected: boolean};
type DeletionPreview = {user_id: number; username: string; brokers_deleted: Array<{id: number; name: string; transactions: number}>; brokers_left: Array<{id: number; name: string; role: string}>; transfers_unpaired: number};
type FlowProgress = {flow: string; status: string; version: number; current_version: number};
type TokenInspection = {status: string; purpose: string; email?: string | null; grants_admin?: boolean | null; username?: string | null};
/** What a test created, recorded the moment it exists — or just before: the clean-up never guesses. */
type Owned = {accounts: Account[]; inviteEmails: string[]};

/** What a test may ask for. Everything it creates through these is removed after it. */
type Users = {
    /** The administrator's API session (`e2e_test_admin`): preconditions and read-backs, never the action under test. */
    admin: APIRequestContext;
    /** A disposable ordinary member, registered anonymously; `tag` short, usernames stop at 50 characters. */
    register(tag: string): Promise<Registered>;
    /** A new API session signed in as `account`, its identity checked. */
    signIn(account: Registered): Promise<APIRequestContext>;
    /** A unique invitation address, recorded for the clean-up before anything is sent with it. */
    inviteAddress(tag: string): string;
};

/** Precondition, verified: the lane registers accounts openly. No E2E spec changes it; this one registers anonymously and invites. */
async function expectRegistrationOpen(api: APIRequestContext): Promise<void> {
    const response = await api.get(INSTANCE_CONFIG_PATH);
    expect(response.status(), `GET ${INSTANCE_CONFIG_PATH}: ${await response.text()}`).toBe(200);
    const mode = ((await response.json()) as {accounts?: {registration_mode?: unknown}}).accounts?.registration_mode;
    expect(mode, `The lane must register accounts openly (accounts.registration_mode 'open'): this spec registers its disposable accounts anonymously and invites through the tab, and no E2E spec changes the mode. The lane answered ${JSON.stringify(mode)}`).toBe('open');
}

async function signInAdministrator(admin: APIRequestContext): Promise<void> {
    const response = await admin.post(`${API}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
    expect(response.status(), `Sign-in of ${TEST_ADMIN.username}, whose API session reads back what the tab did`).toBe(200);
    const {user} = (await response.json()) as {user: {is_superuser: boolean}};
    expect(user.is_superuser, `${TEST_ADMIN.username} must be an administrator: only an administrator manages accounts`).toBe(true);
}

function usersOf(admin: APIRequestContext, open: () => Promise<APIRequestContext>, owned: Owned): Users {
    return {
        admin,

        async register(tag) {
            const username = `ausr_${tag}_${uniqueSuffix()}`;
            const account: Account = {id: null, username, email: `${username}@example.com`, password: PASSWORD};
            // Recorded before the request goes: an account whose registration answer is lost is still removed.
            owned.accounts.push(account);
            const anonymous = await open();
            const response = await anonymous.post(`${API}/auth/register`, {data: {username, email: account.email, password: PASSWORD}});
            expect(response.status(), `Registration is open on the lane (checked first), yet POST /auth/register answered: ${await response.text()}`).toBe(201);
            const {user} = (await response.json()) as {user: {id: number; is_superuser: boolean}};
            expect(user.is_superuser, `${username} starts as an ordinary member`).toBe(false);
            account.id = user.id;
            base.info().annotations.push({type: 'disposable account', description: `${username} (id ${user.id})`});
            return account as Registered;
        },

        async signIn(account) {
            const session = await open();
            const response = await session.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
            expect(response.status(), `Sign-in of ${account.username}: ${await response.text()}`).toBe(200);
            const {user} = (await response.json()) as {user: {id: number}};
            expect(user.id, `The session opened belongs to ${account.username}`).toBe(account.id);
            return session;
        },

        inviteAddress(tag) {
            const email = `ausr_${tag}_${uniqueSuffix()}@example.com`;
            owned.inviteEmails.push(email);
            return email;
        },
    };
}

/** Every account of the instance, as the administrator's `GET /users` lists it. */
async function listAccounts(admin: APIRequestContext): Promise<AdminUser[]> {
    const response = await admin.get(`${API}/users`);
    expect(response.status(), `GET /users: ${await response.text()}`).toBe(200);
    return ((await response.json()) as {items: AdminUser[]}).items;
}

/** Account `id` as the server has it now; undefined once it no longer exists. */
async function accountOnServer(admin: APIRequestContext, id: number): Promise<AdminUser | undefined> {
    return (await listAccounts(admin)).find((user) => user.id === id);
}

/**
 * The account deletes itself: signed in on its own context, once the session is checked to be that very account.
 * Returns why it could not, or null. An account the sign-in does not know, whose id was never read, was never created.
 */
async function deleteItself(session: APIRequestContext, account: Account): Promise<string | null> {
    const signedIn = await session.post(`${API}/auth/login`, {data: {username: account.username, password: account.password}});
    if (signedIn.status() === 401 && account.id === null) return null;
    if (signedIn.status() !== 200) return `account ${account.username}: the sign-in answered ${signedIn.status()}, so it cannot remove itself`;
    const {user} = (await signedIn.json()) as {user: {id: number; username: string}};
    if (user.username !== account.username || (account.id !== null && user.id !== account.id)) {
        return `account ${account.username}: the session opened is ${user.username} (id ${user.id}), not the account to remove`;
    }
    const removed = await session.delete(`${API}/auth/users/me`);
    return removed.ok() ? null : `account ${account.username}: DELETE /auth/users/me answered ${removed.status()}`;
}

/** Remove what the test created. Never throws, so it never masks the test's own failure: it returns what it could not remove. */
async function cleanUp(admin: APIRequestContext, open: () => Promise<APIRequestContext>, owned: Owned): Promise<string[]> {
    const failures: string[] = [];
    if (owned.inviteEmails.length > 0) {
        try {
            const response = await admin.get(`${API}/users/invites`);
            if (response.status() !== 200) {
                failures.push(`GET /users/invites answered ${response.status()}`);
            } else {
                const mine = new Set(owned.inviteEmails);
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
    if (owned.accounts.length === 0) return failures;
    let alive: AdminUser[] | null = null;
    try {
        alive = await listAccounts(admin);
    } catch (error) {
        failures.push(`GET /users: ${String(error)}; every account is tried all the same`);
    }
    for (const account of owned.accounts) {
        try {
            const row = alive?.find((user) => (account.id !== null ? user.id === account.id : user.username === account.username));
            // Not listed: deleted by the test itself, or never registered.
            if (alive !== null && row === undefined) continue;
            if (row !== undefined && !row.is_active) {
                // A deactivated account cannot sign in, so it cannot remove itself: put back as it was registered first.
                const restored = await admin.patch(`${API}/users/${row.id}`, {data: {is_active: true}});
                if (restored.status() !== 200) {
                    failures.push(`account ${account.username}: the reactivation the clean-up needs answered ${restored.status()}`);
                    continue;
                }
            }
            const failure = await deleteItself(await open(), account);
            if (failure) failures.push(failure);
        } catch (error) {
            failures.push(`account ${account.username}: ${String(error)}`);
        }
    }
    return failures;
}

const test = base.extend<{users: Users}>({
    users: async ({playwright, baseURL}, use) => {
        const contexts: APIRequestContext[] = [];
        const open = async (): Promise<APIRequestContext> => {
            const context = await playwright.request.newContext({baseURL});
            contexts.push(context);
            return context;
        };
        const owned: Owned = {accounts: [], inviteEmails: []};
        let admin: APIRequestContext | undefined;
        let failures: string[] = [];
        try {
            admin = await open();
            await expectRegistrationOpen(admin);
            await signInAdministrator(admin);
            await use(usersOf(admin, open, owned));
        } finally {
            if (admin) failures = await cleanUp(admin, open, owned);
            await Promise.all(contexts.map((context) => context.dispose()));
        }
        expect(failures, 'The clean-up must revoke every invitation carrying an address of this test and remove every account it registered').toEqual([]);
    },
});

/** What deleting account `id` would take with it, as the server previews it to an administrator. Nothing is written. */
async function deletionPreview(admin: APIRequestContext, id: number): Promise<DeletionPreview> {
    const response = await admin.get(`${API}/users/${id}/deletion-preview`);
    expect(response.status(), `GET /users/${id}/deletion-preview: ${await response.text()}`).toBe(200);
    return (await response.json()) as DeletionPreview;
}

/** The id of every broker of the instance (`as_user_id=all`, an administrator's view). */
async function brokerIdsOfInstance(admin: APIRequestContext): Promise<number[]> {
    const response = await admin.get(`${API}/brokers`, {params: {as_user_id: 'all'}});
    expect(response.status(), `GET /brokers?as_user_id=all: ${await response.text()}`).toBe(200);
    return ((await response.json()) as {items: Array<{id: number}>}).items.map((broker) => broker.id);
}

/** A broker owned by the account signed in on `session`, with one DEPOSIT: its id. It goes when the account does. */
async function brokerWithDeposit(session: APIRequestContext): Promise<number> {
    const name = `AUSR E2E delete ${uniqueSuffix()}`;
    const created = await session.post(`${API}/brokers`, {data: [{name}]});
    expect(created.ok(), `POST /brokers: HTTP ${created.status()} ${await created.text()}`).toBe(true);
    const {results} = (await created.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const broker = results.find((result) => result.name === name);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker ${name} was not created: ${broker?.message ?? 'no result'}`);
    const brokerId = broker.broker_id;
    const committed = await session.post(`${API}/transactions/commit`, {data: {creates: [{broker_id: brokerId, type: 'DEPOSIT', date: '2026-01-05', cash: {code: 'EUR', amount: '1000'}, description: name}]}});
    expect(committed.ok(), `POST /transactions/commit: HTTP ${committed.status()} ${await committed.text()}`).toBe(true);
    const body = (await committed.json()) as {committed: boolean; issues: unknown[]; results: Array<{operation: string; index: number; ids: number[]}>};
    expect(body.committed, `The deposit was refused: ${JSON.stringify(body.issues)}`).toBe(true);
    expect(body.results.find((result) => result.operation === 'create' && result.index === 0)?.ids, 'One DEPOSIT, one transaction').toHaveLength(1);
    return brokerId;
}

/** The onboarding flows of the account signed in on `session`, with their status. */
async function guidesOf(session: APIRequestContext): Promise<FlowProgress[]> {
    const response = await session.get(`${API}/settings/onboarding`);
    expect(response.status(), `GET /settings/onboarding: ${await response.text()}`).toBe(200);
    return ((await response.json()) as {flows: FlowProgress[]}).flows;
}

/** The account signed in on `session` skips every guide still pending: a restart then has something to show. */
async function skipEveryGuide(session: APIRequestContext): Promise<void> {
    for (const flow of await guidesOf(session)) {
        if (flow.status !== 'pending') continue;
        const skipped = await session.post(`${API}/settings/onboarding/${flow.flow}/skip`, {data: {expected_version: flow.current_version}});
        expect(skipped.ok(), `POST /settings/onboarding/${flow.flow}/skip: HTTP ${skipped.status()}`).toBe(true);
    }
}

/** What a link's token is worth (`POST /auth/tokens/inspect`, public: it answers whoever holds the token). */
async function inspectToken(api: APIRequestContext, token: string, purpose: 'invite' | 'password_reset'): Promise<TokenInspection> {
    const response = await api.post(`${API}/auth/tokens/inspect`, {data: {token, purpose}});
    expect(response.status(), `POST /auth/tokens/inspect: ${await response.text()}`).toBe(200);
    return (await response.json()) as TokenInspection;
}

/** The account the browser is signed in as, through the page's own cookies. */
async function signedInAs(page: Page): Promise<{id: number; username: string; is_superuser: boolean}> {
    const response = await page.request.get(`${API}/auth/me`);
    expect(response.status(), 'GET /auth/me through the browser session').toBe(200);
    return ((await response.json()) as {user: {id: number; username: string; is_superuser: boolean}}).user;
}

/**
 * Sign the administrator in through the login form and open Settings → Users by its address, `?tab=users`. Ends on the
 * tab settled: both of its reads are in. Every action test starts here, so this is where they all stop today.
 */
async function openUsersTab(page: Page): Promise<void> {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings?tab=users');
    const button = page.getByTestId('settings-tab-users');
    await expect(button, `${TEST_ADMIN.username} sees the Users tab: SETTINGS_TABS holds an entry 'users', visible to administrators`).toBeVisible({timeout: LOAD_MS});
    await expect(button, '?tab=users opens it').toHaveAttribute('aria-selected', 'true', {timeout: UI_MS});
    await expect(page.getByTestId('users-tab'), 'The tab settles: GET /users and GET /users/invites are in').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
}

/** The row of account `id`, by its id: never by position. */
function accountRow(page: Page, id: number): Locator {
    return page.locator(`[data-testid="users-row"][data-user-id="${id}"]`);
}

/** The row of a disposable `account` on the settled tab, its precondition verified: an active ordinary member, not one's own row. */
async function memberRow(page: Page, account: Registered): Promise<Locator> {
    const row = accountRow(page, account.id);
    await expect(row, `The tab lists ${account.username}, registered before it loaded`).toBeVisible({timeout: LOAD_MS});
    await expect(row).toHaveAttribute('data-username', account.username, {timeout: UI_MS});
    await expect(row).toHaveAttribute('data-self', 'false', {timeout: UI_MS});
    await expect(row).toHaveAttribute('data-active', 'true', {timeout: UI_MS});
    await expect(row).toHaveAttribute('data-admin', 'false', {timeout: UI_MS});
    await expect(row).toHaveAttribute('data-protected', 'false', {timeout: UI_MS});
    return row;
}

/**
 * Open the actions panel of `row`, asking first: a panel may already be open — a reload that keeps the row keeps it open
 * — and a blind click would close it. Ends on the toggle saying the panel is open.
 */
async function openActions(page: Page, row: Locator): Promise<void> {
    await expect(page.getByTestId('users-tab'), 'No reload in flight, which could redraw the row under the click').toHaveAttribute('data-busy', 'false', {timeout: ACTION_MS});
    const toggle = row.getByTestId('users-row-toggle');
    await expect(toggle).toBeVisible({timeout: UI_MS});
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle, 'The toggle opens the actions panel').toHaveAttribute('aria-expanded', 'true', {timeout: UI_MS});
}

/**
 * The first `name` event recorded after `since`. A red names every `accounts.action.failed` recorded meanwhile — the
 * action and the error code the tab read — instead of a bare timeout.
 */
async function expectAccountEvent(page: Page, name: string, since: number): Promise<AppEvent> {
    try {
        return await waitForEvent(page, name, {since, timeout: ACTION_MS});
    } catch (error) {
        const failed = await page.evaluate((after: number) => ((window as unknown as {__lf?: {events?: AppEvent[]}}).__lf?.events ?? []).filter((event) => event.seq > after && event.name === 'accounts.action.failed').map((event) => event.detail ?? null), since).catch(() => []);
        const reported = failed.length > 0 ? `; the tab reported accounts.action.failed ${JSON.stringify(failed)}` : '';
        throw new Error(`No ${name} after event #${since}${reported}. ${error instanceof Error ? error.message : String(error)}`);
    }
}

/**
 * An action that asks for a confirmation first (`ConfirmModal`, whose `testId="users-confirm"` sits on its header): its
 * event, once the confirmation has closed. The confirm button is the one of that very modal.
 */
async function confirmedAction(page: Page, button: Locator, name: string): Promise<AppEvent> {
    await expect(button, `The action behind ${name} is offered, and enabled`).toBeEnabled({timeout: UI_MS});
    const since = await eventSeq(page);
    await button.click();
    const header = page.getByTestId('users-confirm');
    await expect(header, `${name}: the action asks for a confirmation first`).toBeVisible({timeout: UI_MS});
    await page.getByRole('dialog').filter({has: header}).getByTestId('confirm-modal-confirm').click();
    const event = await expectAccountEvent(page, name, since);
    await expect(header, 'The confirmation closes').toBeHidden({timeout: ACTION_MS});
    return event;
}

/** An action that acts at once, without a confirmation: its event. */
async function immediateAction(page: Page, button: Locator, name: string): Promise<AppEvent> {
    await expect(button, `The action behind ${name} is offered, and enabled`).toBeEnabled({timeout: UI_MS});
    const since = await eventSeq(page);
    await button.click();
    return expectAccountEvent(page, name, since);
}

/**
 * Invite `email` through the tab's dialog, as an ordinary member (the administrator switch left alone). Ends on the link
 * step: the server has issued the invitation, and `LinkShare` shows its link.
 */
async function inviteThroughDialog(page: Page, email: string): Promise<{dialog: Locator; share: Locator; inviteId: number}> {
    const button = page.getByTestId('users-invite-button');
    await expect(button, 'Invite is enabled: registration is open on the lane (checked first), and the lane sets no user limit').toBeEnabled({timeout: UI_MS});
    await button.click();
    const dialog = page.getByTestId('users-invite-dialog');
    await expect(dialog).toBeVisible({timeout: UI_MS});
    const field = dialog.getByTestId('users-invite-email');
    await field.fill(email);
    await expect(field).toHaveValue(email, {timeout: UI_MS});
    const since = await eventSeq(page);
    await dialog.getByTestId('users-invite-create').click();
    const created = await expectAccountEvent(page, 'accounts.invite.created', since);
    const inviteId = created.detail?.invite_id;
    if (typeof inviteId !== 'number') throw new Error(`accounts.invite.created carries no invite_id: ${JSON.stringify(created.detail)}`);
    const share = dialog.getByTestId('link-share');
    await expect(share, 'The link step follows the invitation').toBeVisible({timeout: UI_MS});
    await expect(share).toHaveAttribute('data-purpose', 'invite', {timeout: UI_MS});
    return {dialog, share, inviteId};
}

/** The address `LinkShare` prefilled, read once it is there. */
async function prefilledAddress(share: Locator): Promise<string> {
    const address = share.getByTestId('link-share-address');
    await expect(address, 'LinkShare prefills the address of the server').not.toHaveValue('', {timeout: UI_MS});
    return address.inputValue();
}

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** What `link-share-link` holds: `base`, the page that takes the link, the token in the fragment (`secrets.token_urlsafe`). */
function linkPattern(base: string, pagePath: '/invite' | '/reset-password'): RegExp {
    return new RegExp(`^${escapeRegExp(base)}${escapeRegExp(pagePath)}#token=[A-Za-z0-9_-]+$`);
}

/** The token a link carries in its fragment. */
function tokenOf(link: string): string {
    const token = new URLSearchParams(new URL(link).hash.slice(1)).get('token');
    if (!token) throw new Error(`The link ${link} carries no token in its fragment`);
    return token;
}

/** The other name of the lane's loopback — 127.0.0.1 for localhost and back — with the same scheme and port. */
function otherLoopbackOrigin(baseURL: string | undefined): string {
    if (!baseURL) throw new Error('No baseURL: playwright.config.ts points use.baseURL at the lane');
    const url = new URL(baseURL);
    const swap: Record<string, string | undefined> = {localhost: '127.0.0.1', '127.0.0.1': 'localhost'};
    const other = swap[url.hostname];
    if (!other) throw new Error(`The lane runs on ${url.hostname}: the other-loopback check needs localhost or 127.0.0.1`);
    return `${url.protocol}//${other}${url.port ? `:${url.port}` : ''}`;
}

// The longest test signs in through the form (login() alone may take 70 s on a loaded lane: auth.spec.ts), loads the tab
// and runs several round trips, each followed by a reload. A budget below the waits it contains would end a slow red on
// the test timeout, which names nothing, instead of on its own assertion.
test.setTimeout(180_000);

test.describe('Who has the Users tab', () => {
    test('AUSR-E-01: the administrator opens the Users tab and it settles; a member has no such tab, and ?tab=users opens Profile instead', async ({page}) => {
        // The administrator first: the tab there is what gives the member's «no tab» its meaning — without it, a
        // registry that never draws the tab for anyone would pass the member's half.
        await test.step('the administrator sees the tab, opens it, and it settles', async () => {
            await login(page, TEST_ADMIN);
            expect(await signedInAs(page), `${TEST_ADMIN.username} must be an administrator`).toMatchObject({username: TEST_ADMIN.username, is_superuser: true});
            await navigateTo(page, '/settings');
            // Users is a member of «Administration» (decision P13 b): opened through the group, in its second bar.
            await openSettingsTab(page, 'users');
            const button = page.getByTestId('settings-subtabs').getByTestId('settings-tab-users');
            await expect(button, `${TEST_ADMIN.username} sees the Users tab, in the second bar of «Administration»: SETTINGS_TABS holds an entry 'users', visible to administrators`).toHaveAttribute('aria-selected', 'true', {timeout: UI_MS});
            const tab = page.getByTestId('users-tab');
            await expect(tab).toBeVisible({timeout: UI_MS});
            await expect(tab, 'The tab settles: GET /users and GET /users/invites are in').toHaveAttribute('data-busy', 'false', {timeout: LOAD_MS});
            // Settled, and not merely not started yet: the list holds the accounts, the administrator's own among them.
            await expect(page.locator(`[data-testid="users-row"][data-username="${TEST_ADMIN.username}"]`), 'The tab lists the accounts of the instance').toBeVisible({timeout: LOAD_MS});
        });

        await test.step('a member sees no Users tab, and ?tab=users falls back to Profile', async () => {
            // Signed out by dropping the session cookie: the login form at / opens again.
            await page.context().clearCookies();
            await login(page, TEST_USER);
            expect(await signedInAs(page), `${TEST_USER.username} must be an ordinary member`).toMatchObject({username: TEST_USER.username, is_superuser: false});
            await navigateTo(page, '/settings?tab=users');
            const profile = page.getByTestId('settings-tab-profile');
            // Presence barrier: the tab bar is drawn, up to About, the last tab every account sees. «Administration»
            // and every member of it, Users among them, are an administrator's alone (N69-2, decision D4 a). The bar's
            // entries come from one derivation, and a member's context never turns administrator: the group would be
            // drawn with them, or never.
            await expect(page.getByTestId('settings-tab-about'), 'The tab bar is drawn for the member, up to About').toBeVisible({timeout: LOAD_MS});
            await expect(page.getByTestId('settings-tab-administration'), 'A member has no «Administration» group: the registry does not draw it').toHaveCount(0, {timeout: UI_MS});
            await expect(page.getByTestId('settings-tab-admin')).toHaveCount(0, {timeout: UI_MS});
            await expect(page.getByTestId('settings-tab-users'), 'A member has no Users tab: the registry does not draw it').toHaveCount(0, {timeout: UI_MS});
            await expect(profile, '?tab=users names no tab of a member: the first one, Profile, opens').toHaveAttribute('aria-selected', 'true', {timeout: UI_MS});
            await expect(page.getByTestId('profile-tab')).toBeVisible({timeout: UI_MS});
            await expect(page.getByTestId('users-tab'), 'and the body of the Users tab never mounts').toHaveCount(0, {timeout: UI_MS});
        });
    });

    test("AUSR-E-02: the administrator's own row is marked as its own, and offers a way to the profile instead of actions", async ({page}) => {
        await openUsersTab(page);
        // By attribute: the administrator's row is wherever the list puts it.
        const own = page.locator(`[data-testid="users-row"][data-username="${TEST_ADMIN.username}"]`);
        await expect(own, `The tab lists ${TEST_ADMIN.username}`).toBeVisible({timeout: LOAD_MS});
        await expect(own, 'The row of the signed-in administrator is its own').toHaveAttribute('data-self', 'true', {timeout: UI_MS});
        await expect(own).toHaveAttribute('data-admin', 'true', {timeout: UI_MS});
        await expect(own).toHaveAttribute('data-active', 'true', {timeout: UI_MS});

        await openActions(page, own);
        const hint = own.getByTestId('users-self-hint');
        // Presence barrier for the absence below: the panel is open, and holds the hint.
        await expect(hint, 'The open panel of this row holds the hint').toBeVisible({timeout: UI_MS});
        await expect(hint.locator('a[href*="tab=profile"]'), 'whose link leads to the Profile tab').toBeVisible({timeout: UI_MS});
        await expect(own.locator('[data-testid^="users-action-"]'), 'and no action at all: administrators change their own account from the profile').toHaveCount(0, {timeout: UI_MS});
    });
});

test.describe('Account status and role, on disposable accounts', () => {
    test('AUSR-E-03: deactivate a member, confirmed, then reactivate it', async ({page, users}) => {
        const account = await users.register('act');
        await openUsersTab(page);
        const row = await memberRow(page, account);

        await test.step('deactivate, confirmed', async () => {
            await openActions(page, row);
            const event = await confirmedAction(page, row.getByTestId('users-action-deactivate'), 'accounts.user.deactivated');
            expect(event.detail?.user_id, 'The event names the account').toBe(account.id);
            await expect(row, 'The row reads inactive').toHaveAttribute('data-active', 'false', {timeout: ACTION_MS});
            expect(await accountOnServer(users.admin, account.id), 'The server has the account inactive').toMatchObject({is_active: false});
        });

        await test.step('reactivate, at once', async () => {
            await openActions(page, row);
            const event = await immediateAction(page, row.getByTestId('users-action-reactivate'), 'accounts.user.reactivated');
            expect(event.detail?.user_id, 'The event names the account').toBe(account.id);
            await expect(row, 'The row reads active again').toHaveAttribute('data-active', 'true', {timeout: ACTION_MS});
            expect(await accountOnServer(users.admin, account.id), 'The server has the account active again').toMatchObject({is_active: true});
        });
    });

    test('AUSR-E-04: promote a member, confirmed; an administrator cannot be deleted before its demotion; demote it, confirmed', async ({page, users}) => {
        const account = await users.register('adm');
        await openUsersTab(page);
        const row = await memberRow(page, account);
        const remove = row.getByTestId('users-action-delete');

        await test.step('a member: deleting it is offered', async () => {
            await openActions(page, row);
            await expect(remove, 'The control the administrator state will disable is enabled for a member').toBeEnabled({timeout: UI_MS});
        });

        await test.step('promote, confirmed', async () => {
            await openActions(page, row);
            const event = await confirmedAction(page, row.getByTestId('users-action-promote'), 'accounts.user.promoted');
            expect(event.detail?.user_id, 'The event names the account').toBe(account.id);
            await expect(row, 'The row reads administrator').toHaveAttribute('data-admin', 'true', {timeout: ACTION_MS});
            expect(await accountOnServer(users.admin, account.id), 'The server has the account an administrator').toMatchObject({is_superuser: true});
        });

        await test.step('an administrator: deleting it waits for a demotion', async () => {
            await openActions(page, row);
            await expect(remove, 'An administrator cannot be deleted').toBeDisabled({timeout: UI_MS});
            await expect(remove, 'and the control says why').toHaveAttribute('data-disabled-reason', 'demote-first', {timeout: UI_MS});
        });

        await test.step('demote, confirmed', async () => {
            await openActions(page, row);
            const event = await confirmedAction(page, row.getByTestId('users-action-demote'), 'accounts.user.demoted');
            expect(event.detail?.user_id, 'The event names the account').toBe(account.id);
            await expect(row, 'The row reads member again').toHaveAttribute('data-admin', 'false', {timeout: ACTION_MS});
            expect(await accountOnServer(users.admin, account.id), 'The server has the account a member again').toMatchObject({is_superuser: false});
            await openActions(page, row);
            await expect(remove, 'A member again: deleting it is offered again').toBeEnabled({timeout: UI_MS});
        });
    });
});

test.describe('Links: a password reset, an invitation, and the address they carry', () => {
    test('AUSR-E-05: a password-reset link for a member: issued after its confirmation, shown with its expiry, live for that very account', async ({page, users}) => {
        const account = await users.register('rst');
        await openUsersTab(page);
        const row = await memberRow(page, account);
        await openActions(page, row);
        const reset = row.getByTestId('users-action-reset-link');
        await expect(reset).toBeEnabled({timeout: UI_MS});
        await reset.click();
        const dialog = page.getByTestId('users-reset-dialog');
        await expect(dialog, 'The dialog opens on its confirmation: earlier links stop working').toBeVisible({timeout: UI_MS});

        const since = await eventSeq(page);
        await dialog.getByTestId('users-reset-create').click();
        const event = await expectAccountEvent(page, 'accounts.reset-link.created', since);
        expect(event.detail?.user_id, 'The event names the account').toBe(account.id);
        const share = dialog.getByTestId('link-share');
        await expect(share, 'The link step follows').toBeVisible({timeout: UI_MS});
        await expect(share).toHaveAttribute('data-purpose', 'password_reset', {timeout: UI_MS});
        await expect(share.getByTestId('link-share-expires')).toBeVisible({timeout: UI_MS});
        const base = await prefilledAddress(share);
        const link = share.getByTestId('link-share-link');
        await expect(link, 'The link: the address, the reset page, the token in the fragment').toHaveValue(linkPattern(base, '/reset-password'), {timeout: UI_MS});
        expect(await inspectToken(users.admin, tokenOf(await link.inputValue()), 'password_reset'), 'The link carries a live reset token, for this account').toMatchObject({status: 'valid', username: account.username});

        await dialog.getByTestId('users-reset-close').click();
        await expect(dialog).toBeHidden({timeout: UI_MS});
    });

    test('AUSR-E-06: an invitation with an address: its link, then listed once done, then revoked, confirmed', async ({page, users}) => {
        const email = users.inviteAddress('inv');
        await openUsersTab(page);
        const {dialog, share, inviteId} = await inviteThroughDialog(page, email);
        const base = await prefilledAddress(share);
        const link = share.getByTestId('link-share-link');
        await expect(link, 'The link: the address, the invitation page, the token in the fragment').toHaveValue(linkPattern(base, '/invite'), {timeout: UI_MS});
        const token = tokenOf(await link.inputValue());
        expect(await inspectToken(users.admin, token, 'invite'), 'The link carries a live invitation, with the address written, making no administrator').toMatchObject({status: 'valid', email, grants_admin: false});

        const invitation = page.locator(`[data-testid="users-invite-row"][data-email="${email}"]`);
        await test.step('done: the tab lists the invitation, by its address', async () => {
            await dialog.getByTestId('users-invite-done').click();
            await expect(dialog).toBeHidden({timeout: UI_MS});
            await expect(invitation, 'Done reloads the list, which now holds the invitation').toBeVisible({timeout: ACTION_MS});
            await expect(invitation, 'the very invitation created').toHaveAttribute('data-invite-id', String(inviteId), {timeout: UI_MS});
            await expect(invitation, 'making no administrator').toHaveAttribute('data-admin', 'false', {timeout: UI_MS});
        });

        await test.step('revoke, confirmed', async () => {
            const event = await confirmedAction(page, invitation.getByTestId('users-invite-revoke'), 'accounts.invite.revoked');
            expect(event.detail?.invite_id, 'The event names the invitation').toBe(inviteId);
            await expect(invitation, 'A revoked invitation leaves the list').toHaveCount(0, {timeout: ACTION_MS});
            expect(await inspectToken(users.admin, token, 'invite'), 'and its link no longer opens a registration').toMatchObject({status: 'revoked'});
        });
    });

    test('AUSR-E-07: the address of a link is checked once edited: match on the other loopback origin, unverifiable on a closed port, invalid off http, mismatch on a stranger, idle back on the prefill', async ({page, users, baseURL}) => {
        const other = otherLoopbackOrigin(baseURL);
        const email = users.inviteAddress('addr');
        // The origin of every probe the page sends: a verdict is only worth the address it went to.
        const probedOrigins: string[] = [];
        page.on('request', (request) => {
            try {
                const url = new URL(request.url());
                if (url.pathname === PROBE_PATH) probedOrigins.push(url.origin);
            } catch {
                // Not a URL a probe can have.
            }
        });
        await openUsersTab(page);
        const {dialog, share} = await inviteThroughDialog(page, email);
        const address = share.getByTestId('link-share-address');
        const link = share.getByTestId('link-share-link');
        const probe = share.getByTestId('link-share-probe');
        const copy = share.getByTestId('link-share-copy');
        const initial = await prefilledAddress(share);
        expect(initial, `Precondition: the prefilled address is not already ${other}, or writing it would change nothing to check`).not.toBe(other);
        await expect(probe, 'The prefilled address is not checked').toHaveAttribute('data-state', 'idle', {timeout: UI_MS});
        await expect(link).toHaveValue(linkPattern(initial, '/invite'), {timeout: UI_MS});

        await test.step(`the lane's other loopback origin, ${other}: this very instance answers there, through the real CORS path`, async () => {
            await address.fill(other);
            await expect(address).toHaveValue(other, {timeout: UI_MS});
            await expect(probe, 'Its nonce is verified there: the backend draws the 1×1 image, its size readable across origins').toHaveAttribute('data-state', 'match', {timeout: PROBE_MS});
            expect(probedOrigins, `The verdict is the answer of ${other}: the probe went there`).toContain(other);
            await expect(link, 'The link follows the address').toHaveValue(linkPattern(other, '/invite'), {timeout: UI_MS});
            await expect(copy).toBeEnabled({timeout: UI_MS});
        });

        await test.step(`a closed port, ${CLOSED_ADDRESS}: unverifiable, and still copyable`, async () => {
            await address.fill(CLOSED_ADDRESS);
            await expect(address).toHaveValue(CLOSED_ADDRESS, {timeout: UI_MS});
            await expect(probe, 'Nothing answers: the probe cannot tell').toHaveAttribute('data-state', 'unverifiable', {timeout: PROBE_MS});
            await expect(copy, 'D-A3: an address that cannot be verified does not stop the copy').toBeEnabled({timeout: UI_MS});
        });

        await test.step(`not http(s), ${INVALID_ADDRESS}: invalid, and the copy is off`, async () => {
            await address.fill(INVALID_ADDRESS);
            await expect(address).toHaveValue(INVALID_ADDRESS, {timeout: UI_MS});
            await expect(probe).toHaveAttribute('data-state', 'invalid', {timeout: PROBE_MS});
            await expect(copy, 'An invalid address makes no link to copy').toBeDisabled({timeout: UI_MS});
        });

        await test.step(`an instance that did not issue the nonce, ${MISMATCH_ORIGIN} (stubbed): mismatch`, async () => {
            // Written by the handler itself, so a read after the verdict sees what it did. Bound to this page alone.
            const stranger = pngOf(2, 1);
            expect([stranger.readUInt32BE(16), stranger.readUInt32BE(20)], 'Precondition: the stub’s image is 2×1, the size a stranger draws for a nonce it did not issue').toEqual([2, 1]);
            let answered = 0;
            const refused: string[] = [];
            await page.route(`${MISMATCH_ORIGIN}${PROBE_PATH}**`, async (route) => {
                try {
                    if (route.request().method() !== 'GET') {
                        // The probe is an image load, a GET: anything else is a defect.
                        refused.push(route.request().method());
                        await route.abort();
                        return;
                    }
                    answered += 1;
                    // A stranger answers an image, as the backend does: PNG, no store, and no CORS header — an image needs none.
                    await route.fulfill({status: 200, headers: {'content-type': 'image/png', 'cache-control': 'no-store'}, body: stranger});
                } catch (error) {
                    // Nobody awaits a route handler: recorded, and asserted below.
                    refused.push(`the stub failed: ${String(error)}`);
                }
            });
            await address.fill(MISMATCH_ORIGIN);
            await expect(address).toHaveValue(MISMATCH_ORIGIN, {timeout: UI_MS});
            await expect(probe, 'Something answers there, but not this instance').toHaveAttribute('data-state', 'mismatch', {timeout: PROBE_MS});
            expect(answered, 'The verdict is the answer of the stub: the image was loaded from there').toBeGreaterThan(0);
            expect(refused, 'Only simple GETs reached the stub').toEqual([]);
            await expect(copy, 'D-A3: a mismatch does not stop the copy').toBeEnabled({timeout: UI_MS});
        });

        await test.step('back to the prefilled address: idle again', async () => {
            await address.fill(initial);
            await expect(address).toHaveValue(initial, {timeout: UI_MS});
            await expect(probe, 'The prefilled address is not checked').toHaveAttribute('data-state', 'idle', {timeout: PROBE_MS});
            await expect(link).toHaveValue(linkPattern(initial, '/invite'), {timeout: UI_MS});
            await expect(copy).toBeEnabled({timeout: UI_MS});
        });

        // The invitation stays pending: the clean-up revokes it, by its address.
        await dialog.getByTestId('users-invite-done').click();
        await expect(dialog).toBeHidden({timeout: UI_MS});
    });
});

test.describe('Deleting an account', () => {
    test('AUSR-E-08: delete a member after the preview of the broker that goes with it, its username typed to confirm', async ({page, users}) => {
        const account = await users.register('del');
        const brokerId = await brokerWithDeposit(await users.signIn(account));
        // Preconditions, verified on the server: what the dialog must preview, and the broker it must take along.
        const preview = await deletionPreview(users.admin, account.id);
        expect(
            preview.brokers_deleted.find((broker) => broker.id === brokerId),
            'The server previews the broker going with its only owner, its one deposit with it',
        ).toMatchObject({id: brokerId, transactions: 1});
        expect(await brokerIdsOfInstance(users.admin), 'Presence barrier: the broker exists before the deletion').toContain(brokerId);

        await openUsersTab(page);
        const row = await memberRow(page, account);
        await openActions(page, row);
        const remove = row.getByTestId('users-action-delete');
        await expect(remove, 'A member can be deleted').toBeEnabled({timeout: UI_MS});
        await remove.click();

        const dialog = page.getByTestId('users-delete-dialog');
        await test.step('the dialog previews what goes', async () => {
            await expect(dialog).toBeVisible({timeout: UI_MS});
            await expect(dialog, 'The preview is in: GET /users/{id}/deletion-preview').toHaveAttribute('data-busy', 'false', {timeout: ACTION_MS});
            await expect(dialog.getByTestId('users-delete-deactivate'), 'An active account: deactivating it instead is offered').toBeVisible({timeout: UI_MS});
            await expect(dialog.getByTestId('users-delete-preview')).toBeVisible({timeout: UI_MS});
            const going = dialog.locator(`[data-testid="users-delete-broker-deleted"][data-broker-id="${brokerId}"]`);
            await expect(going, 'The broker it alone owns goes with it').toBeVisible({timeout: UI_MS});
            await expect(going, 'with its one transaction').toHaveAttribute('data-transactions', '1', {timeout: UI_MS});
        });

        const typed = dialog.getByTestId('users-delete-confirm-input');
        const confirm = dialog.getByTestId('users-delete-confirm');
        await test.step('only the username, typed exactly, arms the deletion', async () => {
            await expect(confirm, 'Nothing is armed before the username is typed').toBeDisabled({timeout: UI_MS});
            const partial = account.username.slice(0, -1);
            await typed.fill(partial);
            await expect(typed).toHaveValue(partial, {timeout: UI_MS});
            await expect(confirm, 'nor by a part of it').toBeDisabled({timeout: UI_MS});
            await typed.fill(account.username);
            await expect(typed).toHaveValue(account.username, {timeout: UI_MS});
            await expect(confirm, 'the username exactly arms it').toBeEnabled({timeout: UI_MS});
        });

        await test.step('confirmed: the account goes, its broker with it', async () => {
            const since = await eventSeq(page);
            await confirm.click();
            const event = await expectAccountEvent(page, 'accounts.user.deleted', since);
            expect(event.detail, 'The event names the account, and the brokers that went with it').toMatchObject({user_id: account.id, brokers_deleted: 1});
            await expect(dialog).toBeHidden({timeout: ACTION_MS});
            await expect(row, 'The deleted account leaves the list').toHaveCount(0, {timeout: ACTION_MS});
            expect(await accountOnServer(users.admin, account.id), 'The server no longer has the account').toBeUndefined();
            expect(await brokerIdsOfInstance(users.admin), 'nor its broker').not.toContain(brokerId);
        });
    });
});

test.describe('Sessions and guides, on disposable accounts', () => {
    test('AUSR-E-09: sign a member out everywhere, confirmed: its open session is refused, and the account stays active', async ({page, users}) => {
        const account = await users.register('out');
        const session = await users.signIn(account);
        expect((await session.get(`${API}/auth/me`)).status(), 'Presence barrier: the session of the account works before').toBe(200);

        await openUsersTab(page);
        const row = await memberRow(page, account);
        await openActions(page, row);
        const event = await confirmedAction(page, row.getByTestId('users-action-sign-out'), 'accounts.user.sessions-revoked');
        expect(event.detail?.user_id, 'The event names the account').toBe(account.id);

        expect((await session.get(`${API}/auth/me`)).status(), 'The session opened before is refused at its next request').toBe(401);
        await expect(row, 'Signed out is not deactivated').toHaveAttribute('data-active', 'true', {timeout: ACTION_MS});
        // and the account signs in again: signIn() fails unless a new session opens, as this very account.
        await users.signIn(account);
    });

    test('AUSR-E-10: restart the guides of a member, confirmed: every flow it had skipped is pending again', async ({page, users}) => {
        const account = await users.register('gde');
        const session = await users.signIn(account);
        await skipEveryGuide(session);
        const before = await guidesOf(session);
        expect(before.length, 'The account has guides to restart').toBeGreaterThan(0);
        expect(
            before.filter((flow) => flow.status === 'pending').map((flow) => flow.flow),
            'Precondition: no guide is pending any more, so that a restart shows',
        ).toEqual([]);

        await openUsersTab(page);
        const row = await memberRow(page, account);
        await openActions(page, row);
        const event = await confirmedAction(page, row.getByTestId('users-action-restart-guides'), 'accounts.user.onboarding-reset');
        expect(event.detail?.user_id, 'The event names the account').toBe(account.id);

        const after = await guidesOf(session);
        expect(
            after.filter((flow) => flow.status !== 'pending').map((flow) => `${flow.flow}: ${flow.status}`),
            'Every guide starts again, as for a new account',
        ).toEqual([]);
        expect(after.map((flow) => flow.flow).sort(), 'the same guides as before').toEqual(before.map((flow) => flow.flow).sort());
    });
});
