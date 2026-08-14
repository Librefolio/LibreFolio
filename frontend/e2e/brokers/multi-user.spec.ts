import {type Browser, type BrowserContext, expect, type Page, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER, TEST_USER_2} from '../fixtures/test-users';

/**
 * Multi-User Isolation Tests
 *
 * Tests that verify user data isolation:
 * 1. User cannot see brokers created by other users
 * 2. Broker names are globally unique - duplicate names should fail
 */
test.describe('Multi-User Isolation', () => {
    // Serial, and deliberately so: this block owns two browser contexts created
    // in beforeAll and keeps them across tests — one logged in as user 1, the
    // other as user 2. That is a shared resource with an order, not an
    // accident, so it is declared instead of being left to luck. Under
    // fullyParallel the tests land on different workers and the contexts are
    // torn down under their feet ("Target page, context or browser has been
    // closed").
    test.describe.configure({mode: 'serial'});

    let browser: Browser;
    let context1: BrowserContext;
    let context2: BrowserContext;
    let page1: Page;
    let page2: Page;

    test.beforeAll(async ({browser: b}) => {
        browser = b;
        // Create two separate browser contexts (like incognito windows)
        context1 = await browser.newContext();
        context2 = await browser.newContext();
        page1 = await context1.newPage();
        page2 = await context2.newPage();
    });

    test.afterAll(async () => {
        await context1.close();
        await context2.close();
    });

    test('user cannot see other user broker', async () => {
        // User 1 logs in and creates a broker
        await login(page1, TEST_USER);
        await page1.goto('/brokers');
        await page1.getByTestId('add-broker-button').click();
        await expect(page1.getByTestId('broker-modal')).toBeVisible();

        const brokerName = `Private Broker ${Date.now()}`;
        await page1.getByTestId('broker-name-input').fill(brokerName);
        await page1.getByTestId('broker-form-submit').click();
        await expect(page1.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        await expect(page1.getByText(brokerName)).toBeVisible();

        // User 2 logs in - should NOT see user1's broker
        await login(page2, TEST_USER_2);
        await page2.goto('/brokers');
        await expect(page2.getByText(brokerName)).not.toBeVisible();
    });

    test('duplicate broker name is rejected (global uniqueness)', async () => {
        const sharedName = `Unique Broker ${Date.now()}`;

        // Log in explicitly rather than inheriting test 1's session: serial mode
        // guarantees the order, but a test that states its own preconditions can
        // be read (and re-run) on its own.
        await login(page1, TEST_USER);
        await page1.goto('/brokers');
        await page1.getByTestId('add-broker-button').click();
        await expect(page1.getByTestId('broker-modal')).toBeVisible();
        await page1.getByTestId('broker-name-input').fill(sharedName);
        await page1.getByTestId('broker-form-submit').click();
        await expect(page1.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        await expect(page1.getByText(sharedName)).toBeVisible();

        // User 2 tries to use the same name - should FAIL
        await login(page2, TEST_USER_2);
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
