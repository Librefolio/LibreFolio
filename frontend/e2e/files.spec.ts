import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test.describe('Files Page', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, TEST_USER);
    });

    test.describe('Page Access and Navigation', () => {
        test('can access files page', async ({ page }) => {
            await navigateTo(page, '/files');
            await expect(page.getByTestId('files-page')).toBeVisible();
        });

        test('shows both tabs', async ({ page }) => {
            await navigateTo(page, '/files');
            await expect(page.getByTestId('files-tab-static')).toBeVisible();
            await expect(page.getByTestId('files-tab-brim')).toBeVisible();
        });

        test('can switch to BRIM tab', async ({ page }) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
        });

        test('can switch back to static tab', async ({ page }) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();
            await page.getByTestId('files-tab-static').click();
            await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        });
    });

    test.describe('URL Deep-Linking', () => {
        test('URL filter tab=static opens static tab', async ({ page }) => {
            await page.goto('/files?tab=static');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('files-tab-static')).toHaveAttribute('aria-selected', 'true');
        });

        test('URL filter tab=brim opens BRIM tab', async ({ page }) => {
            await page.goto('/files?tab=brim');
            await page.waitForLoadState('networkidle');
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');
        });
    });

    test.describe('Static Files Tab', () => {
        test('shows files table for static resources', async ({ page }) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();
            // FilesTable wrapper has testid files-table-static
            await expect(page.getByTestId('files-table-static')).toBeVisible();
        });

        test('upload button is visible', async ({ page }) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-static').click();
            await expect(page.getByTestId('upload-button')).toBeVisible();
        });
    });

    test.describe('BRIM Tab', () => {
        test('BRIM tab shows table or empty state', async ({ page }) => {
            await navigateTo(page, '/files');
            await page.getByTestId('files-tab-brim').click();

            // Wait for tab to be selected
            await expect(page.getByTestId('files-tab-brim')).toHaveAttribute('aria-selected', 'true');

            // Wait a bit for content to load
            await page.waitForTimeout(500);

            // Either files table is visible OR empty state is shown
            const hasTable = await page.getByTestId('files-table-brim').isVisible().catch(() => false);
            const hasEmptyState = await page.getByTestId('brim-empty-state').isVisible().catch(() => false);

            // If neither, check for loading state
            if (!hasTable && !hasEmptyState) {
                // Maybe still loading - wait more
                await page.waitForTimeout(1000);
                const hasTableRetry = await page.getByTestId('files-table-brim').isVisible().catch(() => false);
                const hasEmptyRetry = await page.getByTestId('brim-empty-state').isVisible().catch(() => false);
                expect(hasTableRetry || hasEmptyRetry).toBeTruthy();
            } else {
                expect(hasTable || hasEmptyState).toBeTruthy();
            }
        });
    });
});
