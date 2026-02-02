import { test, expect, Browser, BrowserContext, Page } from '@playwright/test';
import { login } from './fixtures/auth-helpers';
import { TEST_USER, TEST_USER_2 } from './fixtures/test-users';

test.describe('Multi-User Isolation', () => {
    let browser: Browser;
    let context1: BrowserContext;
    let context2: BrowserContext;
    let page1: Page;
    let page2: Page;

    test.beforeAll(async ({ browser: b }) => {
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
        await page1.getByRole('button', { name: /add|create/i }).click();
        const brokerName = `Private Broker ${Date.now()}`;
        await page1.getByLabel(/name/i).fill(brokerName);
        await page1.getByRole('button', { name: /save|create/i }).click();
        await expect(page1.getByText(brokerName)).toBeVisible();

        // User 2 logs in - should NOT see the broker
        await login(page2, TEST_USER_2);
        await page2.goto('/brokers');
        await expect(page2.getByText(brokerName)).not.toBeVisible();
    });

    test('duplicate broker name allowed for different users', async () => {
        const sharedName = `Shared Name Broker ${Date.now()}`;
        
        // User 1 creates broker
        await login(page1, TEST_USER);
        await page1.goto('/brokers');
        await page1.getByRole('button', { name: /add|create/i }).click();
        await page1.getByLabel(/name/i).fill(sharedName);
        await page1.getByRole('button', { name: /save|create/i }).click();
        await expect(page1.getByText(sharedName)).toBeVisible();

        // User 2 can also use same name (different user)
        await login(page2, TEST_USER_2);
        await page2.goto('/brokers');
        await page2.getByRole('button', { name: /add|create/i }).click();
        await page2.getByLabel(/name/i).fill(sharedName);
        await page2.getByRole('button', { name: /save|create/i }).click();
        
        // Should succeed - each user can have their own broker with same name
        await expect(page2.getByText(sharedName)).toBeVisible();
    });
});
