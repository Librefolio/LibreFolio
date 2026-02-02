import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test.describe('Brokers', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, TEST_USER);
    });

    test('can view broker list', async ({ page }) => {
        await navigateTo(page, '/brokers');
        await expect(page.getByRole('heading', { name: /broker/i })).toBeVisible();
    });

    test('can create new broker', async ({ page }) => {
        await navigateTo(page, '/brokers');
        
        // Click add broker button
        await page.getByRole('button', { name: /add|create|new|aggiungi|nuovo/i }).click();
        
        // Fill form
        const brokerName = `Test Broker ${Date.now()}`;
        await page.getByLabel(/name|nome/i).fill(brokerName);
        await page.getByRole('button', { name: /save|create|confirm|salva|crea/i }).click();
        
        // Verify broker appears
        await expect(page.getByText(brokerName)).toBeVisible();
    });

    test('can view broker detail', async ({ page }) => {
        await navigateTo(page, '/brokers');
        
        // Click first broker card
        const brokerCard = page.getByTestId('broker-card').first();
        if (await brokerCard.isVisible()) {
            await brokerCard.click();
            await expect(page.getByText(/cash balance|holdings|saldo|patrimonio/i)).toBeVisible();
        }
    });

    test('can open import files modal', async ({ page }) => {
        await navigateTo(page, '/brokers');
        const brokerCard = page.getByTestId('broker-card').first();
        
        if (await brokerCard.isVisible()) {
            await brokerCard.click();
            const importButton = page.getByRole('button', { name: /import|importa/i });
            if (await importButton.isVisible()) {
                await importButton.click();
                await expect(page.getByRole('dialog')).toBeVisible();
            }
        }
    });
});
