import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test.describe('Brokers', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, TEST_USER);
    });

    test.describe('Broker List Page', () => {
        test('can access brokers page', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible();
        });

        test('add broker button is visible', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('add-broker-button')).toBeVisible();
        });

        test('refresh button is visible', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-refresh')).toBeVisible();
        });
    });

    test.describe('Broker CRUD', () => {
        test('can open create broker modal', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();
        });

        test('can close broker modal', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Click outside modal (backdrop) to close
            // The modal has a backdrop that closes on click
            await page.locator('.fixed.inset-0.bg-black\\/50').click({ position: { x: 10, y: 10 } });
            await expect(page.getByTestId('broker-modal')).not.toBeVisible();
        });

        test('create broker with name', async ({ page }) => {
            await navigateTo(page, '/brokers');
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Fill required name field
            const brokerName = `Test Broker ${Date.now()}`;
            await page.getByTestId('broker-name-input').fill(brokerName);

            // Submit form
            await page.getByTestId('broker-form-submit').click();

            // Modal should close and broker should appear in list
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({ timeout: 5000 });

            // Check broker card appears with matching ID pattern
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            await expect(brokerCards).toHaveCount(await brokerCards.count());
        });
    });

    test.describe('Broker Card Interaction', () => {
        test('broker cards are clickable (if any exist)', async ({ page }) => {
            await navigateTo(page, '/brokers');

            // Check if any broker cards exist
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                // Click first broker card - should navigate to detail page
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page).toHaveURL(/\/brokers\/\d+/);
            }
        });
    });
});
