import {Browser, BrowserContext, expect, Page, test} from '@playwright/test';
import {login} from './fixtures/auth-helpers';
import {TEST_USER, TEST_USER_2} from './fixtures/test-users';

/**
 * Multi-User Isolation Tests
 *
 * Tests that verify user data isolation:
 * 1. User cannot see brokers created by other users
 * 2. Broker names are globally unique - duplicate names should fail
 */
test.describe('Multi-User Isolation', () => {
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

        // User 1 creates a broker (already logged in from test 1)
        await page1.goto('/brokers');
        await page1.getByTestId('add-broker-button').click();
        await expect(page1.getByTestId('broker-modal')).toBeVisible();
        await page1.getByTestId('broker-name-input').fill(sharedName);
        await page1.getByTestId('broker-form-submit').click();
        await expect(page1.getByTestId('broker-modal')).not.toBeVisible({timeout: 5000});
        await expect(page1.getByText(sharedName)).toBeVisible();

        // User 2 tries to use the same name - should FAIL
        await page2.goto('/brokers');
        await page2.getByTestId('add-broker-button').click();
        await expect(page2.getByTestId('broker-modal')).toBeVisible();
        await page2.getByTestId('broker-name-input').fill(sharedName);
        await page2.getByTestId('broker-form-submit').click();

        // Modal should stay open and show an error (name already taken)
        // Either error message appears OR modal stays visible
        await page2.waitForTimeout(1000);
        const hasError = await page2.locator('.bg-red-50, .text-red-700, [class*="error"]').isVisible().catch(() => false);
        const modalStillOpen = await page2.getByTestId('broker-modal').isVisible();

        // Success: error shown OR modal didn't close (submission failed)
        expect(hasError || modalStillOpen).toBeTruthy();
    });
});
