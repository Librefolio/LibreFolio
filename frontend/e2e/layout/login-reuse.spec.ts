/**
 * How `login()` (`e2e/fixtures/auth-helpers.ts`) signs a user in, and how long it takes (project 71, block 3, C5 — decision D7).
 *
 * Why. `login()` is called 372 times in 136 specs, and every call goes through the sign-in form: a page load, the form, a
 * POST, the bootstrap's reads. Step 3.15 lets a worker reuse the session of a user it has already signed in. To know what
 * that saves, every call first says how it got in and what it cost: two annotations on the test, `login-path` and
 * `login-ms`, which Playwright's JSON report carries per test. They are published state, not a stopwatch to switch on:
 * always there, at no cost.
 *
 *   - LR-01 after `login(page)` the test carries `login-path: form` and `login-ms`, a number above zero.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

/** The annotations of the running test, of one type. */
function annotations(type: string): string[] {
    return test
        .info()
        .annotations.filter((annotation) => annotation.type === type)
        .map((annotation) => annotation.description ?? '');
}

test.describe('LR, login() says how it got in and what it cost', () => {
    test('LR-01 a sign-in through the form is annotated form, with its milliseconds', async ({page}) => {
        await login(page, TEST_USER);

        expect(annotations('login-path')).toEqual(['form']);
        const [ms] = annotations('login-ms');
        expect(Number(ms), `login-ms: ${ms}`).toBeGreaterThan(0);
    });
});
