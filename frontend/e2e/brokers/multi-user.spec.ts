import {type Browser, type BrowserContext, expect, type Page, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {deleteDisposableUser, registerDisposableUser, skipDueFlowsExcept, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix} from '../fixtures/unique';

// Scoped to the broker list's cards, never page-wide text: the creation toast and the "other existing brokers" discovery card also name the broker.
const brokerCard = (page: Page, name: string) => page.locator('[data-testid^="broker-card-"]').filter({hasText: name});

/**
 * Multi-User Isolation Tests
 *
 * Tests that verify user data isolation:
 * 1. User cannot see brokers created by other users
 * 2. Broker names are globally unique - duplicate names should fail
 *
 * The two users are disposable accounts this block registers, not the canonical E2E users: the brokers user 1
 * creates are its own, and afterAll deletes them by id, then both accounts. Broker names stay global, which is
 * what test 2 checks, so every name carries a suffix unique to the run.
 */
test.describe('Multi-User Isolation', () => {
    // Serial, and deliberately so: this block owns two browser contexts created
    // in beforeAll and keeps them across tests — one logged in as user 1, the
    // other as user 2 — with the two disposable accounts behind them and the ids
    // of the brokers user 1 creates, which afterAll deletes. That is a shared
    // resource with an order, not an accident, so it is declared instead of being
    // left to luck. Under fullyParallel the tests land on different workers and
    // the contexts are torn down under their feet ("Target page, context or
    // browser has been closed").
    test.describe.configure({mode: 'serial'});
    // Each test signs in fresh accounts, whose sign-in also skips their guides over the API.
    test.setTimeout(60_000);

    let browser: Browser;
    // A third context, never signed in by a page: it registers the two accounts, and deletes them.
    let accounts: BrowserContext;
    let context1: BrowserContext;
    let context2: BrowserContext;
    let page1: Page;
    let page2: Page;
    let user1: DisposableUser;
    let user2: DisposableUser;
    // The brokers user 1 created, by id, for afterAll.
    const user1BrokerIds: number[] = [];

    test.beforeAll(async ({browser: b}) => {
        browser = b;
        accounts = await browser.newContext();
        user1 = await registerDisposableUser(accounts.request, 'multi1');
        user2 = await registerDisposableUser(accounts.request, 'multi2');
        // Create two separate browser contexts (like incognito windows)
        context1 = await browser.newContext();
        context2 = await browser.newContext();
        page1 = await context1.newPage();
        page2 = await context2.newPage();
    });

    test.afterAll(async () => {
        // Every step is attempted and every failure reported: one step failing must not leave the others' rows behind.
        const failures: unknown[] = [];
        const attempt = async (step: () => Promise<unknown>) => {
            try {
                await step();
            } catch (error) {
                failures.push(error);
            }
        };
        // The pages go first, so nothing reloads a broker while it is deleted.
        if (context1) await attempt(() => context1.close());
        if (context2) await attempt(() => context2.close());
        // Deleting an account also deletes the brokers it was the last owner of: user 2's, should the duplicate ever
        // go through, and any of user 1's whose id was never read.
        if (user1) await attempt(() => deleteDisposableUser(accounts.request, user1, user1BrokerIds));
        if (user2) await attempt(() => deleteDisposableUser(accounts.request, user2));
        if (accounts) await attempt(() => accounts.close());
        if (failures.length > 0) throw new AggregateError(failures, 'Multi-User Isolation could not delete everything it created');
    });

    /** Sign a page in as a disposable account, past onboarding: every guide is skipped over the API, for that account only. */
    async function signIn(page: Page, user: DisposableUser) {
        await login(page, user);
        await skipDueFlowsExcept(page, []);
    }

    /** Submit user 1's broker modal; once it has closed, record for afterAll the broker its `broker.created` event names. */
    async function submitAndRecord() {
        const since = await eventSeq(page1);
        await page1.getByTestId('broker-form-submit').click();
        await expect(page1.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        const created = await waitForEvent(page1, 'broker.created', {since});
        const brokerId = created.detail?.brokerId;
        if (typeof brokerId !== 'number') throw new Error(`broker.created carries no broker id: ${JSON.stringify(created.detail)}`);
        user1BrokerIds.push(brokerId);
    }

    test('user cannot see other user broker', async () => {
        // User 1 logs in and creates a broker
        await signIn(page1, user1);
        await page1.goto('/brokers');
        await page1.getByTestId('add-broker-button').click();
        await expect(page1.getByTestId('broker-modal')).toBeVisible();

        const brokerName = `Private Broker ${uniqueSuffix()}`;
        await page1.getByTestId('broker-name-input').fill(brokerName);
        await submitAndRecord();
        await expect(brokerCard(page1, brokerName)).toBeVisible({timeout: 5000});

        // User 2 logs in - should NOT see user1's broker among their own brokers
        await signIn(page2, user2);
        await page2.goto('/brokers');
        // Barrier for the zero below: the list has loaded and does show the broker, but only as a
        // name-only "other existing brokers" discovery card — user 2 has no access to it.
        await waitForSettled(page2.getByTestId('brokers-page'));
        await expect(page2.locator('[data-testid^="broker-discovery-card-"]').filter({hasText: brokerName})).toBeVisible();
        await expect(brokerCard(page2, brokerName)).toHaveCount(0);
    });

    test('duplicate broker name is rejected (global uniqueness)', async () => {
        const sharedName = `Unique Broker ${uniqueSuffix()}`;

        // Log in explicitly rather than inheriting test 1's session: serial mode
        // guarantees the order, but a test that states its own preconditions can
        // be read (and re-run) on its own.
        await signIn(page1, user1);
        await page1.goto('/brokers');
        await page1.getByTestId('add-broker-button').click();
        await expect(page1.getByTestId('broker-modal')).toBeVisible();
        await page1.getByTestId('broker-name-input').fill(sharedName);
        await submitAndRecord();
        await expect(brokerCard(page1, sharedName)).toBeVisible({timeout: 5000});

        // User 2 tries to use the same name - should FAIL
        await signIn(page2, user2);
        await page2.goto('/brokers');
        await page2.getByTestId('add-broker-button').click();
        await expect(page2.getByTestId('broker-modal')).toBeVisible();
        await page2.getByTestId('broker-name-input').fill(sharedName);
        await page2.getByTestId('broker-form-submit').click();

        // The contract is "the submission did not go through". Two observable
        // consequences, both asserted: the modal stays open and the error banner
        // appears. Sleeping a second and then sampling two CSS classes asked a
        // weaker question and answered it on a guess.
        await expect(page2.getByTestId('broker-modal').getByTestId('info-banner-error')).toBeVisible({timeout: 5000});
        await expect(page2.getByTestId('broker-modal')).toBeVisible();
    });
});
