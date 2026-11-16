/**
 * How `login()` (`e2e/fixtures/auth-helpers.ts`) signs a user in, and how long it takes (project 71, block 3, C5 — decision D7).
 *
 * Why. `login()` is called 372 times in 136 specs, and every call goes through the sign-in form: a page load, the form, a
 * POST, the bootstrap's reads. Step 3.15 lets a worker reuse the session of a user it has already signed in. To know what
 * that saves, every call first says how it got in and what it cost: two annotations on the test, `login-path` and
 * `login-ms`, which Playwright's JSON report carries per test. They are published state, not a stopwatch to switch on:
 * always there, at no cost.
 *
 *   - LR-01 after `login(page)` the test carries `login-path` and `login-ms`, a number above zero (`form`, the first time).
 *   - LR-02 (step 3.15) a second `login()` of the same user in a new context of the same worker reuses the kept session:
 *     `reused`, and not one `POST /auth/login` from that page.
 *   - LR-03 a kept session the server refuses: `form`, and the app arrives.
 *   - LR-04 `loginWithForm()` goes through the form whatever the worker keeps.
 *   - LR-05 a user created by the test, its Welcome still due: the second `login()` is `reused` and arrives on
 *     `welcome-shell`, the screen the old «already signed in» branch never waited for.
 *   - LR-06 a kept session that belongs to another account (a repopulated database can give a user another's former id):
 *     the identity check sends it to the form, and the page ends signed in as the user asked.
 */
import {expect, test, type Browser, type Page} from '../fixtures/playwright';
import {forgetOrBreakLogin, login, loginWithForm} from '../fixtures/auth-helpers';
import {deleteDisposableUser, registerDisposableUser} from '../fixtures/onboarding-accounts';
import {TEST_USER, TEST_USER_2} from '../fixtures/test-users';

/** The annotations of the running test, of one type. */
function annotations(type: string): string[] {
    // The last sign-in of the test is the last of its annotations.
    return test
        .info()
        .annotations.filter((annotation) => annotation.type === type)
        .map((annotation) => annotation.description ?? '');
}

test.describe('LR, login() says how it got in and what it cost', () => {
    test('LR-01 a sign-in through the form is annotated form, with its milliseconds', async ({page}) => {
        forgetOrBreakLogin(TEST_USER.username, 'forget');
        await login(page, TEST_USER);

        expect(annotations('login-path')).toEqual(['form']);
        const [ms] = annotations('login-ms');
        expect(Number(ms), `login-ms: ${ms}`).toBeGreaterThan(0);
    });
});

/** A page in a context of its own, in this worker: what the next test of the worker gets. */
async function freshPage(browser: Browser, baseURL: string | undefined): Promise<Page> {
    return (await browser.newContext({baseURL})).newPage();
}

/** Who the page is signed in as, from the app's own answer. */
async function whoAmI(page: Page): Promise<string | undefined> {
    const answer = await page.request.get('/api/v1/auth/me');
    return answer.ok() ? ((await answer.json()) as {user?: {username?: string}}).user?.username : undefined;
}

test.describe('LR, the session of a signed-in user is reused per worker (step 3.15)', () => {
    test('LR-02 the second login() of a user in a new context reuses its session: no POST /auth/login', async ({page, browser, baseURL}) => {
        await login(page, TEST_USER);
        const second = await freshPage(browser, baseURL);
        const posts: string[] = [];
        second.on('request', (request) => {
            if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/auth/login') posts.push(request.url());
        });

        await login(second, TEST_USER);

        expect(annotations('login-path').at(-1)).toBe('reused');
        expect(posts, 'a reused session signs in without the form').toEqual([]);
        expect(await whoAmI(second)).toBe(TEST_USER.username);
        await second.context().close();
    });

    test('LR-03 a kept session the server refuses goes through the form, and arrives', async ({page, browser, baseURL}) => {
        await login(page, TEST_USER);
        forgetOrBreakLogin(TEST_USER.username, 'break');
        const second = await freshPage(browser, baseURL);

        await login(second, TEST_USER);

        expect(annotations('login-path').at(-1)).toBe('form');
        expect(await whoAmI(second)).toBe(TEST_USER.username);
        await second.context().close();
    });

    test('LR-04 loginWithForm() always goes through the form', async ({page, browser, baseURL}) => {
        await login(page, TEST_USER);
        const second = await freshPage(browser, baseURL);
        const posts: string[] = [];
        second.on('request', (request) => {
            if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/v1/auth/login') posts.push(request.url());
        });

        await loginWithForm(second, TEST_USER);

        expect(annotations('login-path').at(-1)).toBe('form');
        expect(posts).toHaveLength(1);
        await second.context().close();
    });

    test('LR-05 a user created by the test, its Welcome due: the second login() is reused and arrives on welcome-shell', async ({page, browser, baseURL, request}) => {
        const user = await registerDisposableUser(request, 'lr05');
        try {
            await login(page, user);
            await expect(page.getByTestId('welcome-shell')).toBeVisible();
            const second = await freshPage(browser, baseURL);

            await login(second, user);

            expect(annotations('login-path').at(-1)).toBe('reused');
            await expect(second.getByTestId('welcome-shell')).toBeVisible();
            await second.context().close();
        } finally {
            forgetOrBreakLogin(user.username, 'forget');
            await deleteDisposableUser(request, user);
        }
    });

    test('LR-06 a kept session that is another account’s is refused by the identity check: form, signed in as the user asked', async ({page, browser, baseURL}) => {
        await login(page, TEST_USER);
        // Another ordinary account: a page of a raw context has none of the fixture's guards, and an administrator's would
        // ask GitHub for the latest release.
        const other = await freshPage(browser, baseURL);
        await login(other, TEST_USER_2);
        forgetOrBreakLogin(TEST_USER.username, 'swap', TEST_USER_2.username);
        const second = await freshPage(browser, baseURL);

        await login(second, TEST_USER);

        expect(annotations('login-path').at(-1)).toBe('form');
        expect(await whoAmI(second)).toBe(TEST_USER.username);
        await Promise.all([other.context().close(), second.context().close()]);
    });
});
