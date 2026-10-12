import {type APIRequestContext, expect, type Page, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {type DisposableUser, registerDisposableUser, skipDueFlowsExcept} from '../fixtures/onboarding-accounts';
import {TEST_ADMIN} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

/**
 * Account deletion from Settings → Profile, and the last-owner rule (release 1.2, E2E gap 6).
 *
 * CHANGELOG 1.2: «Deleting your account removes the brokers you alone own.» `DELETE /auth/users/me`
 * applies `BrokerService.leave_broker` to every broker of the account: the last OWNER leaving takes the
 * broker with its transactions and its report files, even when viewers or editors share it; a broker
 * with another OWNER stays with them, minus the leaver's access. The rule itself is proved on four
 * brokers by the backend (`test_account_deletion_api.py`, ACCDEL-001); this spec proves that the dialog
 * a user actually confirms reaches it, and what the other member sees afterwards.
 *
 * Two disposable accounts, A and B, and two brokers created by A:
 * - X: A its only OWNER, shared with B as VIEWER; a DEPOSIT and an uploaded report. Goes with A.
 * - Y: A and B both OWNER; a DEPOSIT. Stays with B, without A.
 *
 * Parallel by default: the test owns both accounts and both brokers, reads nothing it did not create
 * and removes all of it by id in `finally`. Users, brokers and transactions never reuse an id
 * (`sqlite_autoincrement`), so a 404 on X cannot be a neighbour's newer broker.
 */

const API = '/api/v1';
const REPORT_CSV = 'date,description,amount,currency\n2026-01-05,account deletion probe,1000.00,EUR\n';

type Role = 'OWNER' | 'EDITOR' | 'VIEWER';
type Grant = {user_id: number; role: Role};
type Member = {user: DisposableUser; api: APIRequestContext};
/** Everything the test created, recorded the moment it exists: the clean-up never guesses. */
type Owned = {members: Member[]; brokerIds: number[]; reportId?: string};
type Administrator = {session(): Promise<APIRequestContext>; dispose(): Promise<void>};

function byUser(grants: Grant[]): Grant[] {
    return [...grants].sort((left, right) => left.user_id - right.user_id);
}

async function statusOf(api: APIRequestContext, path: string): Promise<number> {
    return (await api.get(`${API}${path}`)).status();
}

/** Open a session for `user` on `api`; `null` when the account no longer exists (the login answers 401). */
async function signIn(api: APIRequestContext, user: DisposableUser): Promise<{id: number; is_superuser: boolean} | null> {
    const response = await api.post(`${API}/auth/login`, {data: {username: user.username, password: user.password}});
    if (response.status() === 401) return null;
    expect(response.status(), `Sign-in of ${user.username}`).toBe(200);
    const {user: me} = (await response.json()) as {user: {id: number; is_superuser: boolean}};
    expect(me.id, 'A session must belong to the account it was opened for').toBe(user.id);
    return me;
}

/** A fresh account, signed in on `api`. It must be an ordinary member: the sole administrator is refused deletion. */
async function registerMember(api: APIRequestContext, tag: string, owned: Owned): Promise<DisposableUser> {
    const user = await registerDisposableUser(api, tag);
    owned.members.push({user, api});
    const me = await signIn(api, user);
    expect(me?.is_superuser, `${user.username} must be an ordinary member, not the instance administrator`).toBe(false);
    return user;
}

async function createBroker(api: APIRequestContext, name: string, owned: Owned): Promise<number> {
    const response = await api.post(`${API}/brokers`, {data: [{name}]});
    expect(response.ok(), `Creating broker ${name}: HTTP ${response.status()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Broker ${name} was not created: ${created?.message ?? 'no result'}`);
    owned.brokerIds.push(created.broker_id);
    return created.broker_id;
}

/** Replace the broker's complete access list. */
async function setAccess(api: APIRequestContext, brokerId: number, grants: Array<Grant & {share_percentage: number}>): Promise<void> {
    const response = await api.put(`${API}/brokers/${brokerId}/access`, {data: grants});
    expect(response.ok(), `Access setup of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
}

/** Who holds which role on the broker, by user id; `null` when the broker does not exist. Any signed-in user may read it. */
async function accessOf(api: APIRequestContext, brokerId: number): Promise<Grant[] | null> {
    const response = await api.get(`${API}/brokers/${brokerId}/access`);
    if (response.status() === 404) return null;
    expect(response.ok(), `Access list of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    const {items} = (await response.json()) as {items: Grant[]};
    return byUser(items.map(({user_id, role}) => ({user_id, role})));
}

/** One DEPOSIT per broker in a single commit; the transaction ids, in the order of `brokerIds`. */
async function deposit(api: APIRequestContext, brokerIds: number[], description: string): Promise<number[]> {
    const creates = brokerIds.map((broker_id) => ({broker_id, type: 'DEPOSIT', date: '2026-01-05', cash: {code: 'EUR', amount: '1000'}, description}));
    const response = await api.post(`${API}/transactions/commit`, {data: {creates}});
    expect(response.ok(), `Deposit commit: HTTP ${response.status()}`).toBe(true);
    const body = (await response.json()) as {committed: boolean; issues: unknown[]; results: Array<{operation: string; index: number; ids: number[]}>};
    expect(body.committed, `Deposit commit rejected: ${JSON.stringify(body.issues)}`).toBe(true);
    return creates.map((_, index) => {
        const ids = body.results.find((result) => result.operation === 'create' && result.index === index)?.ids ?? [];
        if (ids.length !== 1) throw new Error(`Deposit ${index} returned the ids ${JSON.stringify(ids)}`);
        return ids[0];
    });
}

/** The transactions among `ids` the session can read, as {transaction id: broker id}. */
async function readableTransactions(api: APIRequestContext, ids: number[]): Promise<Record<string, number>> {
    const response = await api.get(`${API}/transactions`, {params: new URLSearchParams(ids.map((id) => ['ids', String(id)]))});
    expect(response.ok(), `Reading transactions ${ids.join(', ')}: HTTP ${response.status()}`).toBe(true);
    const rows = (await response.json()) as Array<{id: number; broker_id: number}>;
    return Object.fromEntries(rows.map((row) => [String(row.id), row.broker_id]));
}

async function uploadReport(api: APIRequestContext, brokerId: number, filename: string, owned: Owned): Promise<string> {
    const response = await api.post(`${API}/brokers/import/upload`, {
        multipart: {broker_id: String(brokerId), file: {name: filename, mimeType: 'text/csv', buffer: Buffer.from(REPORT_CSV, 'utf8')}},
    });
    expect(response.ok(), `Uploading ${filename}: HTTP ${response.status()}`).toBe(true);
    const info = (await response.json()) as {file_id: string; target_broker_id: number | null};
    owned.reportId = info.file_id;
    expect(info.target_broker_id, 'The report must belong to the broker it was uploaded to').toBe(brokerId);
    return info.file_id;
}

/** Every broker id the session's broker list mentions: the accessible ones, and the discovery list of the others. */
async function listedBrokers(api: APIRequestContext): Promise<{accessible: number[]; mentioned: number[]}> {
    const response = await api.get(`${API}/brokers`, {params: {include_inaccessible: true}});
    expect(response.ok(), `Broker list: HTTP ${response.status()}`).toBe(true);
    const {items, inaccessible} = (await response.json()) as {items: Array<{id: number}>; inaccessible: Array<{id: number}>};
    const accessible = items.map((item) => item.id);
    return {accessible, mentioned: [...accessible, ...inaccessible.map((item) => item.id)]};
}

/** The instance administrator, signed in only if the clean-up fallback needs it. */
function administrator(open: () => Promise<APIRequestContext>): Administrator {
    let api: APIRequestContext | undefined;
    return {
        async session() {
            if (!api) {
                api = await open();
                const response = await api.post(`${API}/auth/login`, {data: {username: TEST_ADMIN.username, password: TEST_ADMIN.password}});
                expect(response.ok(), `Administrator sign-in for the clean-up fallback: HTTP ${response.status()}`).toBe(true);
            }
            return api;
        },
        async dispose() {
            await api?.dispose();
        },
    };
}

/**
 * Remove, by id, what the test created and still exists, after a red too. Never throws, so it never masks
 * the test's own failure: it returns what it could not remove.
 *
 * Brokers go first, through an account of the test that still owns them. Only a broker none of them owns
 * any more goes through the instance administrator (`as_user_id=all`): that happens only when the rule
 * under test is broken and leaves X ownerless, the very case this spec exists to catch, which must not
 * also leave the lane dirty. A broker's reports go with it; one that outlived it goes the same way. Then
 * the accounts that still exist.
 */
async function cleanUp(owned: Owned, admin: Administrator): Promise<string[]> {
    const failures: string[] = [];
    const attempt = async (what: string, step: () => Promise<void>): Promise<void> => {
        try {
            await step();
        } catch (error) {
            failures.push(`${what}: ${error instanceof Error ? error.message : String(error)}`);
        }
    };
    const live: Member[] = [];
    for (const candidate of owned.members) {
        await attempt(`sign-in of ${candidate.user.username}`, async () => {
            if (await signIn(candidate.api, candidate.user)) live.push(candidate);
        });
    }
    // Any signed-in session may read an access list or a report's status: any live member, else the administrator.
    const reader = async (): Promise<APIRequestContext> => live[0]?.api ?? (await admin.session());
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const grants = await accessOf(await reader(), brokerId);
            if (grants === null) return;
            const owner = live.find((candidate) => grants.some((grant) => grant.user_id === candidate.user.id && grant.role === 'OWNER'));
            const params: Record<string, string | number | boolean> = {ids: brokerId, force: true};
            if (!owner) params.as_user_id = 'all';
            const response = await (owner?.api ?? (await admin.session())).delete(`${API}/brokers`, {params});
            expect(response.ok(), `HTTP ${response.status()}`).toBe(true);
            const {results} = (await response.json()) as {results: Array<{id: number; success: boolean; message?: string}>};
            expect(results.find((result) => result.id === brokerId)).toMatchObject({success: true});
        });
    }
    const reportId = owned.reportId;
    if (reportId) {
        await attempt(`report ${reportId}`, async () => {
            if ((await statusOf(await reader(), `/brokers/import/files/${reportId}`)) === 404) return;
            const removed = await (await admin.session()).delete(`${API}/brokers/import/files/${reportId}`);
            expect(removed.ok(), `HTTP ${removed.status()}`).toBe(true);
        });
    }
    for (const survivor of live) {
        await attempt(`account ${survivor.user.username}`, async () => {
            const removed = await survivor.api.delete(`${API}/auth/users/me`);
            expect(removed.ok(), `HTTP ${removed.status()}`).toBe(true);
        });
    }
    return failures;
}

/**
 * Sign `user` in through the login form and open Settings → Profile.
 *
 * A fresh account is gated on /welcome, and its intro tour would make the shell inert: every flow still
 * due is skipped over the API, for this account only, and read back. /welcome forwards to its returnTo
 * only once the re-read progress says it is done, so landing on /settings proves the gate let us in.
 */
async function openProfile(page: Page, user: DisposableUser): Promise<void> {
    await login(page, user);
    await skipDueFlowsExcept(page, []);
    await navigateTo(page, '/welcome?returnTo=%2Fsettings');
    await expect(page).toHaveURL((url) => url.pathname === '/settings', {timeout: 15_000});
    const shell = page.getByTestId('app-shell');
    await expect(shell).toBeVisible();
    await expect(shell).toHaveAttribute('data-guide-inert', 'false');
    const tab = page.getByTestId('settings-tab-profile');
    await tab.click();
    await expect(tab).toHaveAttribute('aria-selected', 'true');
    // The browser is signed in as `user`: the confirmation will ask for exactly this name.
    await expect(page.getByTestId('profile-username')).toHaveValue(user.username);
}

/** Delete the signed-in account through the real dialog; returns once the server has accepted the deletion. */
async function deleteAccountThroughDialog(page: Page, username: string): Promise<void> {
    await page.getByTestId('delete-account-button').click();
    const dialog = page.getByTestId('profile-delete-dialog');
    await expect(dialog).toBeVisible();
    const typed = dialog.getByTestId('profile-delete-confirm-input');
    const confirm = dialog.getByTestId('profile-delete-confirm');
    // Nothing is armed until the exact username is typed.
    await expect(confirm).toBeDisabled();
    await typed.fill(username);
    await expect(typed).toHaveValue(username);
    await expect(confirm).toBeEnabled();
    // The request is the subject here: the confirmation must reach DELETE /auth/users/me, and be accepted.
    const answer = page.waitForResponse((response) => response.request().method() === 'DELETE' && new URL(response.url()).pathname === `${API}/auth/users/me`);
    await confirm.click();
    expect((await answer).status(), 'DELETE /auth/users/me must accept the deletion').toBe(200);
}

test.describe('Account deletion: the last-owner rule', () => {
    // Two accounts, two brokers and a sign-in through the UI: more than the default 30 s on a loaded lane.
    test.setTimeout(60_000);

    test('deleting the account from Settings takes the broker A alone owned and leaves the co-owned one to B', async ({page, playwright, baseURL}) => {
        const asA = await playwright.request.newContext({baseURL});
        const asB = await playwright.request.newContext({baseURL});
        const admin = administrator(() => playwright.request.newContext({baseURL}));
        const owned: Owned = {members: [], brokerIds: []};
        let leftovers: string[] = [];
        try {
            // Arrange, over the API.
            const suffix = uniqueSuffix();
            const a = await registerMember(asA, 'accdel_a', owned);
            const b = await registerMember(asB, 'accdel_b', owned);
            const x = await createBroker(asA, `AccDel E2E X ${suffix}`, owned);
            const y = await createBroker(asA, `AccDel E2E Y ${suffix}`, owned);
            await setAccess(asA, x, [
                {user_id: a.id, role: 'OWNER', share_percentage: 1},
                {user_id: b.id, role: 'VIEWER', share_percentage: 0},
            ]);
            await setAccess(asA, y, [
                {user_id: a.id, role: 'OWNER', share_percentage: 0.5},
                {user_id: b.id, role: 'OWNER', share_percentage: 0.5},
            ]);
            const [xDeposit, yDeposit] = await deposit(asA, [x, y], `AccDel E2E ${suffix}`);
            const report = await uploadReport(asA, x, `accdel-e2e-${suffix}.csv`, owned);
            test.info().annotations.push({type: 'owned ids', description: JSON.stringify({a: a.id, b: b.id, x, y, xDeposit, yDeposit, report})});

            // Presence barrier: every «gone» asserted below is a «there» B saw right before the deletion.
            expect(await accessOf(asB, x), 'X: A its only OWNER, B a VIEWER').toEqual(
                byUser([
                    {user_id: a.id, role: 'OWNER'},
                    {user_id: b.id, role: 'VIEWER'},
                ]),
            );
            expect(await accessOf(asB, y), 'Y: A and B both OWNER').toEqual(
                byUser([
                    {user_id: a.id, role: 'OWNER'},
                    {user_id: b.id, role: 'OWNER'},
                ]),
            );
            expect(await statusOf(asB, `/brokers/${x}`), 'B, VIEWER of X, reads X').toBe(200);
            expect(await statusOf(asB, `/brokers/import/files/${report}`), "B, VIEWER of X, reads X's report").toBe(200);
            expect(await readableTransactions(asB, [xDeposit, yDeposit]), 'B reads both deposits').toEqual({[xDeposit]: x, [yDeposit]: y});

            // Act, through the UI: A deletes the account from Settings → Profile.
            await openProfile(page, a);
            await deleteAccountThroughDialog(page, a.username);

            // A is signed out, for good.
            await expect(page).toHaveURL((url) => url.pathname === '/', {timeout: 15_000});
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 15_000});
            expect(await statusOf(page.request, '/auth/me'), 'The browser is no longer signed in').toBe(401);
            expect(await statusOf(asA, '/auth/me'), 'A session opened before the deletion dies with the account').toBe(401);
            const relogin = await asA.post(`${API}/auth/login`, {data: {username: a.username, password: a.password}});
            expect(relogin.status(), 'The deleted account cannot sign in again').toBe(401);

            // What B sees. Soft: a red lists every broken expectation, not only the first.
            expect.soft(await statusOf(asB, `/brokers/${x}`), 'X went with A, its last OWNER, although B could see it').toBe(404);
            expect.soft(await accessOf(asB, x), 'X has no access list left: the broker does not exist').toBeNull();
            expect.soft(await statusOf(asB, `/brokers/import/files/${report}`), "X's report went with X").toBe(404);
            const listed = await listedBrokers(asB);
            expect.soft(listed.mentioned, "B's broker list, accessible or not, no longer mentions X").not.toContain(x);
            expect.soft(listed.accessible, "Y is still among B's brokers").toContain(y);
            expect.soft(await statusOf(asB, `/brokers/${y}`), 'Y stayed with B, its other OWNER').toBe(200);
            expect.soft(await accessOf(asB, y), 'Y: B still its OWNER, A without an access row').toEqual([{user_id: b.id, role: 'OWNER'}]);
            expect.soft(await readableTransactions(asB, [xDeposit, yDeposit]), "X's deposit went with X; Y's stayed").toEqual({[yDeposit]: y});
        } finally {
            leftovers = await cleanUp(owned, admin);
            if (leftovers.length > 0) test.info().annotations.push({type: 'clean-up failure', description: leftovers.join('\n')});
            await Promise.all([asA.dispose(), asB.dispose(), admin.dispose()]);
        }
        expect(leftovers, 'The clean-up must remove every account, broker and report the test created').toEqual([]);
    });
});
