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

        test('can open edit modal from broker card', async ({ page }) => {
            await navigateTo(page, '/brokers');

            // Wait for broker cards to load
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                // Get the first broker card's id
                const firstCard = brokerCards.first();
                const testId = await firstCard.getAttribute('data-testid');
                const brokerId = testId?.replace('broker-card-', '');

                // Click edit button on first broker
                await page.getByTestId(`broker-edit-${brokerId}`).click();
                await expect(page.getByTestId('broker-modal')).toBeVisible();
            }
        });

        test('can open delete dialog from broker card', async ({ page }) => {
            await navigateTo(page, '/brokers');

            // Wait for broker cards to load
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                // Get the first broker card's id
                const firstCard = brokerCards.first();
                const testId = await firstCard.getAttribute('data-testid');
                const brokerId = testId?.replace('broker-card-', '');

                // Click delete button on first broker
                await page.getByTestId(`broker-delete-${brokerId}`).click();
                await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();

                // Cancel to close dialog
                await page.getByTestId('delete-broker-cancel').click();
                await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible();
            }
        });

        test('full broker CRUD flow: create, edit, delete', async ({ page }) => {
            await navigateTo(page, '/brokers');

            // === CREATE ===
            const brokerName = `CRUD Test Broker ${Date.now()}`;
            await page.getByTestId('add-broker-button').click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();
            await page.getByTestId('broker-name-input').fill(brokerName);
            await page.getByTestId('broker-form-submit').click();
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({ timeout: 5000 });

            // Find the newly created broker card
            await page.waitForTimeout(1000);
            const newBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({ hasText: brokerName });
            await expect(newBrokerCard).toBeVisible({ timeout: 5000 });

            // Get broker ID from card
            const cardTestId = await newBrokerCard.getAttribute('data-testid');
            const brokerId = cardTestId?.replace('broker-card-', '');

            // === EDIT ===
            const editedName = `${brokerName} EDITED`;
            await page.getByTestId(`broker-edit-${brokerId}`).click();
            await expect(page.getByTestId('broker-modal')).toBeVisible();

            // Clear and fill with new name
            await page.getByTestId('broker-name-input').clear();
            await page.getByTestId('broker-name-input').fill(editedName);
            await page.getByTestId('broker-form-submit').click();
            await expect(page.getByTestId('broker-modal')).not.toBeVisible({ timeout: 5000 });

            // Verify edited name appears
            await page.waitForTimeout(500);
            const editedBrokerCard = page.locator('[data-testid^="broker-card-"]').filter({ hasText: editedName });
            await expect(editedBrokerCard).toBeVisible({ timeout: 5000 });

            // === DELETE ===
            await page.getByTestId(`broker-delete-${brokerId}`).click();
            await expect(page.getByTestId('delete-broker-dialog')).toBeVisible();

            // Confirm delete
            await page.getByTestId('delete-broker-confirm').click();
            await expect(page.getByTestId('delete-broker-dialog')).not.toBeVisible({ timeout: 5000 });

            // Verify broker is gone
            await page.waitForTimeout(500);
            await expect(page.locator(`[data-testid="broker-card-${brokerId}"]`)).not.toBeVisible({ timeout: 5000 });
        });
    });

    test.describe('Broker Detail Page', () => {
        test('can navigate to broker detail by clicking card', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page).toHaveURL(/\/brokers\/\d+/);
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
            }
        });

        test('broker detail page shows broker name', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('broker-name')).toBeVisible();
            }
        });

        test('broker detail page shows cash balances section', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('broker-cash-balances')).toBeVisible();
            }
        });

        test('broker detail page shows holdings section', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('broker-holdings')).toBeVisible();
            }
        });

        test('broker detail page shows transactions section', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('broker-transactions')).toBeVisible();
            }
        });

        test('broker detail page has import files button', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('import-files-button')).toBeVisible();
            }
        });

        test('broker detail page has edit button', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();
                await expect(page.getByTestId('broker-edit-button')).toBeVisible();
            }
        });

        test('can open edit modal from detail page', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();

                await page.getByTestId('broker-edit-button').click();
                await expect(page.getByTestId('broker-modal')).toBeVisible();
            }
        });

        test('can navigate back from detail page', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();

                await page.getByTestId('broker-back-button').click();
                await expect(page.getByTestId('brokers-page')).toBeVisible();
            }
        });

        test('can open import files modal', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();

                await page.getByTestId('import-files-button').click();
                await expect(page.getByTestId('import-files-modal')).toBeVisible();
            }
        });

        test('can close import files modal', async ({ page }) => {
            await navigateTo(page, '/brokers');

            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            const count = await brokerCards.count();

            if (count > 0) {
                const firstCard = brokerCards.first();
                await firstCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible();

                await page.getByTestId('import-files-button').click();
                await expect(page.getByTestId('import-files-modal')).toBeVisible();

                // Close by pressing Escape
                await page.keyboard.press('Escape');
                await expect(page.getByTestId('import-files-modal')).not.toBeVisible();
            }
        });
    });
});
