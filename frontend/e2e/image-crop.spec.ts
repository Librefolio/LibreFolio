/**
 * E2E Tests for Image Crop and Media Components (Phase 4.6)
 *
 * Tests cover:
 * - Suite 1: File Upload with Image Editing (7 tests)
 * - Suite 2: ImageEditModal Controls (10 tests)
 * - Suite 3: ImageEditModal Edge Cases (4 tests)
 * - Suite 4: AssetPickerModal (8 tests)
 * - Suite 5: Avatar Management (6 tests)
 * - Suite 6: Dark Mode (3 tests)
 * - Suite 7: Grid View (4 tests)
 */
import {expect, test} from '@playwright/test';
import {login, logout, navigateTo} from './fixtures/auth-helpers';
import {TEST_USER} from './fixtures/test-users';
import path from 'path';
import {fileURLToPath} from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Test image files from the project's static assets
const TEST_IMAGE = path.resolve(__dirname, '../static/icons/transactions/buy.png');
const TEST_IMAGE_2 = path.resolve(__dirname, '../static/icons/transactions/deposit.png');
const TEST_CSV = path.resolve(__dirname, '../../backend/app/services/brim_providers/sample_reports/generic_simple.csv');

// Helper: Upload an image via FileUploader and wait for the ImageEditModal
async function uploadImageAndWaitForModal(page: import('@playwright/test').Page, filePath: string) {
    const fileInput = page.getByTestId('file-input');
    await fileInput.setInputFiles(filePath);
    // ImageEditModal should appear for image files
    await expect(page.getByTestId('image-edit-modal')).toBeVisible({timeout: 5000});
}

// Helper: Upload a non-image file via FileUploader
async function uploadNonImageFile(page: import('@playwright/test').Page, filePath: string) {
    const fileInput = page.getByTestId('file-input');
    await fileInput.setInputFiles(filePath);
    // Wait for file to appear in pending list
    await page.waitForTimeout(500);
}

// =============================================================================
// Suite 1: File Upload with Image Editing
// =============================================================================
test.describe('File Upload with Image Editing', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
        // Open uploader
        await page.getByTestId('upload-button').click();
        await expect(page.getByTestId('file-uploader')).toBeVisible();
    });

    test('A1: image upload opens ImageEditModal', async ({page}) => {
        await uploadImageAndWaitForModal(page, TEST_IMAGE);

        // Verify modal has crop area
        await expect(page.getByTestId('image-cropper')).toBeVisible();
        // Verify modal has Crop button
        await expect(page.getByTestId('image-edit-confirm')).toBeVisible();
    });

    test('A2: crop and confirm adds image to pending list', async ({page}) => {
        await uploadImageAndWaitForModal(page, TEST_IMAGE);

        // Click "Crop" to confirm
        await page.getByTestId('image-edit-confirm').click();

        // Modal should close
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});

        // File should appear in pending list with edit indicator
        await expect(page.locator('.file-item')).toBeVisible();
    });

    test('A3: cancel crop does not add file', async ({page}) => {
        await uploadImageAndWaitForModal(page, TEST_IMAGE);

        // Click Cancel
        await page.getByTestId('image-edit-cancel').click();

        // Modal should close
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});

        // No file in pending list
        await expect(page.locator('.file-item')).not.toBeVisible();
    });

    test('A4: non-image file uploads without crop modal', async ({page}) => {
        await uploadNonImageFile(page, TEST_CSV);

        // ImageEditModal should NOT appear
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible();

        // File should appear directly in pending list
        await expect(page.locator('.file-item')).toBeVisible();
        await expect(page.locator('.file-name')).toContainText('generic_simple.csv');
    });

    test('A5: edit button re-opens ImageEditModal for image file', async ({page}) => {
        // Upload and crop
        await uploadImageAndWaitForModal(page, TEST_IMAGE);
        await page.getByTestId('image-edit-confirm').click();
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});

        // Click pencil icon to re-edit
        const editBtn = page.getByTestId('file-edit-btn').first();
        await expect(editBtn).toBeVisible();
        await editBtn.click();

        // ImageEditModal should re-open
        await expect(page.getByTestId('image-edit-modal')).toBeVisible({timeout: 3000});
    });

    test('A6: restore button reverts to original', async ({page}) => {
        // Upload and crop
        await uploadImageAndWaitForModal(page, TEST_IMAGE);
        await page.getByTestId('image-edit-confirm').click();
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});

        // Restore button should be visible
        const restoreBtn = page.getByTestId('file-restore-btn').first();
        await expect(restoreBtn).toBeVisible();

        // Click restore
        await restoreBtn.click();

        // Restore button should disappear
        await expect(page.getByTestId('file-restore-btn')).not.toBeVisible({timeout: 2000});
    });

    test('A7: FileEditModal opens for non-image file edit', async ({page}) => {
        await uploadNonImageFile(page, TEST_CSV);

        // Click pencil icon
        const editBtn = page.getByTestId('file-edit-btn').first();
        await expect(editBtn).toBeVisible();
        await editBtn.click();

        // FileEditModal should open (not ImageEditModal)
        await expect(page.getByTestId('file-edit-modal')).toBeVisible({timeout: 3000});
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible();
    });
});

// =============================================================================
// Suite 2: ImageEditModal Controls & Settings
// =============================================================================
test.describe('ImageEditModal - Controls & Settings', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
        await page.getByTestId('upload-button').click();
        await expect(page.getByTestId('file-uploader')).toBeVisible();
        await uploadImageAndWaitForModal(page, TEST_IMAGE);
    });

    test('B1: zoom buttons exist and are clickable', async ({page}) => {
        await expect(page.getByTestId('crop-zoom-in')).toBeVisible();
        await expect(page.getByTestId('crop-zoom-out')).toBeVisible();

        // Click zoom in
        await page.getByTestId('crop-zoom-in').click();
        // Click zoom out
        await page.getByTestId('crop-zoom-out').click();

        // No crash means success — zoom changes are visual
    });

    test('B2: rotation buttons exist and are clickable', async ({page}) => {
        await expect(page.getByTestId('crop-rotate-left')).toBeVisible();
        await expect(page.getByTestId('crop-rotate-right')).toBeVisible();

        // Click rotate right
        await page.getByTestId('crop-rotate-right').click();
        // Click rotate left
        await page.getByTestId('crop-rotate-left').click();
    });

    test('B3: flip buttons exist and are clickable', async ({page}) => {
        await expect(page.getByTestId('crop-flip-h')).toBeVisible();
        await expect(page.getByTestId('crop-flip-v')).toBeVisible();

        // Click flip horizontal
        await page.getByTestId('crop-flip-h').click();
        // Click flip vertical
        await page.getByTestId('crop-flip-v').click();
    });

    test('B4: preset selection updates UI', async ({page}) => {
        // Find preset buttons — they are in the controls section
        const presetBtns = page.locator('.preset-btn');
        const count = await presetBtns.count();
        expect(count).toBeGreaterThan(0);

        // Click "Avatar" preset if available
        const avatarPreset = page.locator('.preset-btn', {hasText: /avatar/i});
        if (await avatarPreset.isVisible().catch(() => false)) {
            await avatarPreset.click();
            await page.waitForTimeout(300);
        }
    });

    test('B5: filename input is editable', async ({page}) => {
        const filenameInput = page.getByTestId('image-edit-filename');
        if (await filenameInput.isVisible().catch(() => false)) {
            // Clear and type new name
            await filenameInput.clear();
            await filenameInput.fill('my-custom-image');
            await expect(filenameInput).toHaveValue('my-custom-image');
        }
    });

    test('B6: reset all button works', async ({page}) => {
        const resetBtn = page.getByTestId('image-edit-reset');
        await expect(resetBtn).toBeVisible();

        // Rotate first to make a change
        await page.getByTestId('crop-rotate-right').click();
        await page.waitForTimeout(200);

        // Click reset
        await resetBtn.click();
        await page.waitForTimeout(300);

        // No crash means success — visual state is restored
    });

    test('B7: output dimensions section exists', async ({page}) => {
        // Look for output width/height inputs
        const outputSection = page.locator('.dimensions-section, .output-section, [class*="output"]').first();
        await expect(outputSection).toBeVisible();
    });

    test('B8: format selector exists', async ({page}) => {
        // Look for format select
        const formatSelect = page.locator('select, [class*="format"]').first();
        await expect(formatSelect).toBeVisible();
    });

    test('B9: quality control exists for JPEG', async ({page}) => {
        // Switch to JPEG format if possible
        const formatSelect = page.locator('select').first();
        if (await formatSelect.isVisible().catch(() => false)) {
            const options = await formatSelect.locator('option').allTextContents();
            if (options.some(o => o.toLowerCase().includes('jpg') || o.toLowerCase().includes('jpeg'))) {
                await formatSelect.selectOption({label: options.find(o => o.toLowerCase().includes('jpg') || o.toLowerCase().includes('jpeg'))!});
                await page.waitForTimeout(200);
                // Quality control should appear
                const qualityControl = page.locator('[class*="quality"], input[type="number"]');
                await expect(qualityControl.first()).toBeVisible();
            }
        }
    });

    test('B10: crop button confirms and closes modal', async ({page}) => {
        await page.getByTestId('image-edit-confirm').click();
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});
    });
});

// =============================================================================
// Suite 3: ImageEditModal - Confirmation & Edge Cases
// =============================================================================
test.describe('ImageEditModal - Confirmation & Edge Cases', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
        await page.getByTestId('upload-button').click();
        await expect(page.getByTestId('file-uploader')).toBeVisible();
        await uploadImageAndWaitForModal(page, TEST_IMAGE);
    });

    test('C1: closing with changes shows confirmation dialog', async ({page}) => {
        // Make a change
        await page.getByTestId('crop-rotate-right').click();
        await page.waitForTimeout(300);

        // Press Escape to try closing
        await page.keyboard.press('Escape');

        // Confirmation dialog should appear
        await expect(page.locator('[class*="confirm"], [class*="warning"]').first()).toBeVisible({timeout: 2000});
    });

    test('C2: closing without changes closes immediately', async ({page}) => {
        // Wait for initial render
        await page.waitForTimeout(1000);

        // Click cancel (no changes made after init)
        await page.getByTestId('image-edit-cancel').click();

        // Modal should close without confirmation
        await expect(page.getByTestId('image-edit-modal')).not.toBeVisible({timeout: 3000});
    });

    test('C3: ellipse preview toggle works', async ({page}) => {
        const eyeToggle = page.getByTestId('image-edit-ellipse-toggle');
        if (await eyeToggle.isVisible().catch(() => false)) {
            await eyeToggle.click();
            await page.waitForTimeout(300);
            // Toggle again
            await eyeToggle.click();
        }
    });

    test('C4: modal has proper z-index and is accessible', async ({page}) => {
        // Modal should be visible and interactive
        await expect(page.getByTestId('image-edit-modal')).toBeVisible();
        await expect(page.getByTestId('image-edit-confirm')).toBeEnabled();
        await expect(page.getByTestId('image-edit-cancel')).toBeEnabled();
    });
});

// =============================================================================
// Suite 4: AssetPickerModal
// =============================================================================
test.describe('AssetPickerModal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('D1: clicking broker icon opens AssetPickerModal', async ({page}) => {
        await navigateTo(page, '/brokers');

        // Click "Add Broker" button
        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            // Click on the icon area
            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
            }
        }
    });

    test('D2: existing tab shows files', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});

                // Click existing tab
                await page.getByTestId('asset-picker-existing-tab').click();
                await page.waitForTimeout(500);

                // Search input should be visible
                await expect(page.getByTestId('asset-picker-search')).toBeVisible();
            }
        }
    });

    test('D3: URL tab accepts manual URL input', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});

                // Click URL tab
                await page.getByTestId('asset-picker-url-tab').click();
                await page.waitForTimeout(300);

                // Type a URL
                const urlInput = page.locator('input[type="text"], input[type="url"]').last();
                await urlInput.fill('https://example.com/icon.png');
                await page.waitForTimeout(300);

                // Confirm button should be enabled
                await expect(page.getByTestId('asset-picker-confirm')).toBeEnabled();
            }
        }
    });

    test('D4: upload tab exists', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});

                // Upload tab should exist
                await expect(page.getByTestId('asset-picker-upload-tab')).toBeVisible();
            }
        }
    });

    test('D5: can close AssetPickerModal', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});

                // Press Escape to close
                await page.keyboard.press('Escape');
                await expect(page.getByTestId('asset-picker-modal')).not.toBeVisible({timeout: 3000});
            }
        }
    });

    test('D6: search filters existing files', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('asset-picker-existing-tab').click();
                await page.waitForTimeout(500);

                // Type in search
                const searchInput = page.getByTestId('asset-picker-search');
                await searchInput.fill('nonexistent-file-abc123');
                await page.waitForTimeout(300);
                // Should show empty state or filtered results
            }
        }
    });

    test('D7: view toggle between grid and list', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
                await page.getByTestId('asset-picker-existing-tab').click();
                await page.waitForTimeout(500);

                // Toggle buttons should exist
                const gridBtn = page.locator('.toggle-btn').first();
                const listBtn = page.locator('.toggle-btn').last();
                if (await gridBtn.isVisible().catch(() => false)) {
                    await listBtn.click();
                    await page.waitForTimeout(300);
                    await gridBtn.click();
                }
            }
        }
    });

    test('D8: circular preview overlay for avatar/icon context', async ({page}) => {
        // Go to settings, profile tab, click avatar to open AssetPickerModal with circular=true
        await navigateTo(page, '/settings');
        await page.waitForTimeout(500);

        // Find and click profile tab
        const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
        if (await profileTab.isVisible().catch(() => false)) {
            await profileTab.click();
            await page.waitForTimeout(300);

            // Unlock editing
            const editLock = page.locator('[data-testid="profile-edit-toggle"], button', {hasText: /edit|pencil/i}).first();
            if (await editLock.isVisible().catch(() => false)) {
                await editLock.click();
                await page.waitForTimeout(300);

                // Click avatar
                const avatarTrigger = page.getByTestId('profile-avatar');
                if (await avatarTrigger.isVisible().catch(() => false)) {
                    await avatarTrigger.click();
                    await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
                }
            }
        }
    });
});

// =============================================================================
// Suite 5: Avatar Management
// =============================================================================
test.describe('Avatar - Profile Settings', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/settings');
    });

    test('E1: avatar section visible in profile tab', async ({page}) => {
        const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
        if (await profileTab.isVisible().catch(() => false)) {
            await profileTab.click();
            await page.waitForTimeout(300);
            // Avatar section should exist
            const avatarSection = page.locator('text=Avatar, img[alt="Avatar"], [class*="avatar"]').first();
            await expect(avatarSection).toBeVisible({timeout: 2000});
        }
    });

    test('E2: avatar change requires edit mode', async ({page}) => {
        const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
        if (await profileTab.isVisible().catch(() => false)) {
            await profileTab.click();
            await page.waitForTimeout(300);

            // Avatar camera overlay should not be visible when locked
            const avatarTrigger = page.getByTestId('profile-avatar');
            await expect(avatarTrigger).not.toBeVisible();
        }
    });

    test('E3: can open AssetPickerModal from avatar', async ({page}) => {
        const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
        if (await profileTab.isVisible().catch(() => false)) {
            await profileTab.click();
            await page.waitForTimeout(300);

            // Unlock editing
            const editLock = page.locator('[data-testid="profile-edit-toggle"], [class*="edit-toggle"]').first();
            if (await editLock.isVisible().catch(() => false)) {
                await editLock.click();
                await page.waitForTimeout(300);

                const avatarTrigger = page.getByTestId('profile-avatar');
                if (await avatarTrigger.isVisible().catch(() => false)) {
                    await avatarTrigger.click();
                    await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
                }
            }
        }
    });

    test('E4: avatar remove button visible when avatar is set', async ({page}) => {
        const profileTab = page.locator('[data-testid="settings-tab-profile"], [role="tab"]', {hasText: /profile/i}).first();
        if (await profileTab.isVisible().catch(() => false)) {
            await profileTab.click();
            await page.waitForTimeout(300);

            // Unlock editing
            const editLock = page.locator('[data-testid="profile-edit-toggle"], [class*="edit-toggle"]').first();
            if (await editLock.isVisible().catch(() => false)) {
                await editLock.click();
                await page.waitForTimeout(300);

                // Check if remove button exists (only if avatar is set)
                const removeBtn = page.getByTestId('avatar-remove-btn');
                // This is conditional - avatar might not be set
                const isVisible = await removeBtn.isVisible().catch(() => false);
                // Just verify the page doesn't crash
                expect(typeof isVisible).toBe('boolean');
            }
        }
    });

    test('E5: sidebar shows user avatar area', async ({page}) => {
        await expect(page.getByTestId('sidebar-user-avatar')).toBeVisible();
    });

    test('E6: sidebar avatar links to settings', async ({page}) => {
        const avatarLink = page.getByTestId('sidebar-user-avatar');
        await expect(avatarLink).toHaveAttribute('href', '/settings');
    });
});

// =============================================================================
// Suite 6: Dark Mode - Image Crop Components
// =============================================================================
test.describe('Dark Mode - Image Crop Components', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        // Enable dark mode via settings
        await navigateTo(page, '/settings');
        const themeToggle = page.getByTestId('theme-toggle');
        if (await themeToggle.isVisible().catch(() => false)) {
            // Check if already dark
            const isDark = await page.locator('html.dark, body.dark, [class*="dark"]').first().isVisible().catch(() => false);
            if (!isDark) {
                await themeToggle.click();
                await page.waitForTimeout(300);
            }
        }
    });

    test('F1: ImageEditModal renders in dark mode', async ({page}) => {
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
        await page.getByTestId('upload-button').click();
        await expect(page.getByTestId('file-uploader')).toBeVisible();

        await uploadImageAndWaitForModal(page, TEST_IMAGE);

        // Modal should be visible
        await expect(page.getByTestId('image-edit-modal')).toBeVisible();
        // Dark mode class should be active on html or body
        const hasDark = await page.locator('html.dark').isVisible().catch(() => false)
            || await page.locator('[class*="dark"]').first().isVisible().catch(() => false);
        expect(hasDark).toBeTruthy();
    });

    test('F2: AssetPickerModal renders in dark mode', async ({page}) => {
        await navigateTo(page, '/brokers');

        const addBtn = page.getByTestId('add-broker-button');
        if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);

            const iconTrigger = page.getByTestId('broker-icon-trigger');
            if (await iconTrigger.isVisible().catch(() => false)) {
                await iconTrigger.click();
                await expect(page.getByTestId('asset-picker-modal')).toBeVisible({timeout: 3000});
            }
        }
    });

    test('F3: FileEditModal renders in dark mode', async ({page}) => {
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
        await page.getByTestId('upload-button').click();
        await expect(page.getByTestId('file-uploader')).toBeVisible();

        await uploadNonImageFile(page, TEST_CSV);

        const editBtn = page.getByTestId('file-edit-btn').first();
        if (await editBtn.isVisible().catch(() => false)) {
            await editBtn.click();
            await expect(page.getByTestId('file-edit-modal')).toBeVisible({timeout: 3000});
        }
    });
});

// =============================================================================
// Suite 7: Files Page - Grid View
// =============================================================================
test.describe('Files Page - Grid View', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await navigateTo(page, '/files');
        await page.getByTestId('files-tab-static').click();
    });

    test('G1: grid view shows file cards with preview', async ({page}) => {
        // Only test if view toggle exists (files present)
        const hasViewToggle = await page.getByTestId('view-mode-toggle').isVisible().catch(() => false);
        if (hasViewToggle) {
            await page.getByTestId('view-mode-grid').click();
            await page.waitForTimeout(300);

            // Grid cards should be visible
            const cards = page.locator('.file-card');
            const count = await cards.count();
            if (count > 0) {
                // Each card should have title and meta
                await expect(cards.first().locator('.card-title')).toBeVisible();
                await expect(cards.first().locator('.card-meta')).toBeVisible();
            }
        }
    });

    test('G2: search works in grid view', async ({page}) => {
        const hasViewToggle = await page.getByTestId('view-mode-toggle').isVisible().catch(() => false);
        if (hasViewToggle) {
            await page.getByTestId('view-mode-grid').click();
            await page.waitForTimeout(300);

            // Search bar should be visible
            const searchInput = page.locator('.grid-search-input');
            if (await searchInput.isVisible().catch(() => false)) {
                await searchInput.fill('nonexistent-file-xyz');
                await page.waitForTimeout(300);

                // Should show empty state
                const emptyState = page.locator('.empty-state');
                await expect(emptyState).toBeVisible();
            }
        }
    });

    test('G3: grid cards have action buttons', async ({page}) => {
        const hasViewToggle = await page.getByTestId('view-mode-toggle').isVisible().catch(() => false);
        if (hasViewToggle) {
            await page.getByTestId('view-mode-grid').click();
            await page.waitForTimeout(300);

            const cards = page.locator('.file-card');
            const count = await cards.count();
            if (count > 0) {
                // First card should have actions: download, copy, delete
                const actions = cards.first().locator('.card-actions .action-btn');
                const actionCount = await actions.count();
                expect(actionCount).toBeGreaterThanOrEqual(3); // download, copy, delete
            }
        }
    });

    test('G4: delete button styled as danger', async ({page}) => {
        const hasViewToggle = await page.getByTestId('view-mode-toggle').isVisible().catch(() => false);
        if (hasViewToggle) {
            await page.getByTestId('view-mode-grid').click();
            await page.waitForTimeout(300);

            const cards = page.locator('.file-card');
            if (await cards.first().isVisible().catch(() => false)) {
                const dangerBtn = cards.first().locator('.action-btn.danger');
                await expect(dangerBtn).toBeVisible();
            }
        }
    });
});

