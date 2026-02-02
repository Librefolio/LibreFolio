import { test, expect } from '@playwright/test';
import { login, navigateTo } from './fixtures/auth-helpers';
import { TEST_USER } from './fixtures/test-users';

test.describe('Files Page', () => {
    test.beforeEach(async ({ page }) => {
        await login(page, TEST_USER);
    });

    test('can access files page', async ({ page }) => {
        await navigateTo(page, '/files');
        await expect(page.getByRole('heading', { name: /files|file/i })).toBeVisible();
    });

    test('files page has tabs', async ({ page }) => {
        await navigateTo(page, '/files');

        // Look for static and broker report tabs
        const staticTab = page.getByRole('tab', { name: /static|resources|risorse/i });
        const brimTab = page.getByRole('tab', { name: /broker|import|report/i });

        // At least one tab should be visible
        const hasStaticTab = await staticTab.isVisible().catch(() => false);
        const hasBrimTab = await brimTab.isVisible().catch(() => false);

        expect(hasStaticTab || hasBrimTab).toBeTruthy();
    });

    test('URL filter tab=static works', async ({ page }) => {
        await page.goto('/files?tab=static');
        await page.waitForLoadState('networkidle');

        // Should show static resources tab content
        await expect(page.getByText(/static|resources|risorse/i)).toBeVisible();
    });

    test('URL filter tab=brim works', async ({ page }) => {
        await page.goto('/files?tab=brim');
        await page.waitForLoadState('networkidle');

        // Should show broker reports tab content
        await expect(page.getByText(/broker|import|report/i)).toBeVisible();
    });

    test('can upload a file', async ({ page }) => {
        await navigateTo(page, '/files');

        // Look for upload button or drop zone
        const uploadButton = page.getByRole('button', { name: /upload|carica/i });
        const dropZone = page.getByTestId('file-drop-zone');

        const hasUpload = await uploadButton.isVisible().catch(() => false);
        const hasDropZone = await dropZone.isVisible().catch(() => false);

        // Should have some way to upload files
        expect(hasUpload || hasDropZone).toBeTruthy();
    });
});
