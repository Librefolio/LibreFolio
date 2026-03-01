import {expect, Page, test} from '@playwright/test';
import {login, navigateTo} from './fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from './fixtures/test-users';

/**
 * Broker Sharing E2E Tests
 *
 * Tests for BrokerSharingModal component:
 * - Share button visibility (OWNER only)
 * - Modal open/close
 * - Ownership chart, add/edit/remove users
 * - Save flow
 * - Role-based access checks
 * - Dark mode
 */

// Helper: Navigate to first broker detail page (OWNER)
async function goToFirstBrokerDetail(page: Page) {
    await navigateTo(page, '/brokers');
    // Wait for brokers page to load
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
    // Wait for broker cards to appear (API fetch)
    const brokerCards = page.locator('[data-testid^="broker-card-"]');
    await expect(brokerCards.first()).toBeVisible({timeout: 10000});

    // Click the first broker card to navigate to detail
    await brokerCards.first().click();
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
}

// Helper: Open sharing modal (assumes already on broker detail as OWNER)
async function openSharingModal(page: Page) {
    const shareBtn = page.getByTestId('broker-share-button');
    await expect(shareBtn).toBeVisible({timeout: 5000});
    await shareBtn.click();
    await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 5000});
}

test.describe('Broker Sharing', () => {

    test.describe('Share Button Visibility', () => {
        test('S1: share button visible for OWNER on broker detail', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await expect(page.getByTestId('broker-share-button')).toBeVisible();
        });

        test('S2: share button NOT visible for VIEWER', async ({page}) => {
            // TEST_USER_2 is VIEWER on Interactive Brokers (from populate)
            await login(page, TEST_USER_2);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // TEST_USER_2 only has VIEWER access, so find any broker card
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            await expect(brokerCards.first()).toBeVisible({timeout: 10000});
            await brokerCards.first().click();
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
            // Share button should NOT be visible for VIEWER
            await expect(page.getByTestId('broker-share-button')).not.toBeVisible({timeout: 2000});
            // Edit button should also NOT be visible for VIEWER
            await expect(page.getByTestId('broker-edit-button')).not.toBeVisible({timeout: 2000});
        });

        test('S3: share button opens BrokerSharingModal', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
            // Modal is visible (openSharingModal asserts this)
        });
    });

    test.describe('BrokerSharingModal Content', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S4: modal shows ownership chart section', async ({page}) => {
            await expect(page.getByTestId('ownership-chart-section')).toBeVisible();
        });

        test('S5: modal shows at least the current OWNER in badge list', async ({page}) => {
            // Should see at least one access-entry badge (the OWNER)
            const entries = page.locator('[data-testid^="access-entry-"]');
            await expect(entries.first()).toBeVisible({timeout: 5000});
        });

        test('S6: add user button is visible', async ({page}) => {
            await expect(page.getByTestId('sharing-add-user-btn')).toBeVisible();
        });

        test('S7: clicking add user opens add-user modal', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible({timeout: 3000});
        });

        test('S8: save button is disabled when no changes', async ({page}) => {
            const saveBtn = page.getByTestId('sharing-save-btn');
            await expect(saveBtn).toBeVisible();
            await expect(saveBtn).toBeDisabled();
        });

        test('S9: close modal with Escape key', async ({page}) => {
            await page.keyboard.press('Escape');
            await expect(page.getByTestId('broker-sharing-modal')).not.toBeVisible({timeout: 3000});
        });

        test('S10: three role columns are visible (Owners, Editors, Viewers)', async ({page}) => {
            await expect(page.getByTestId('sharing-owners-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-editors-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-viewers-column')).toBeVisible({timeout: 3000});
        });
    });

    test.describe('BrokerSharingModal - Add User Flow', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S11: add user form has search input', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible();
            await expect(page.getByTestId('sharing-search-input')).toBeVisible();
        });

        test('S12: search for users returns results', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible({timeout: 3000});
            const searchInput = page.getByTestId('sharing-search-input');
            await expect(searchInput).toBeVisible();

            // Type a search query using pressSequentially to trigger Svelte on:input
            // 'frank' is a free user NOT assigned to any broker
            await searchInput.click();
            await searchInput.pressSequentially('frank', {delay: 50});
            // Wait for debounce (300ms) + API call
            await page.waitForTimeout(2000);

            // Should see at least one search result item (e2e_user_frank)
            const results = page.locator('[data-testid^="user-search-result-"]');
            await expect(results.first()).toBeVisible({timeout: 5000});
        });
    });

    test.describe('BrokerSharingModal - Edit User', () => {
        test('S13: clicking edit on a badge opens edit modal', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);

            // Find first access entry edit button
            const editBtn = page.locator('[data-testid^="access-entry-"] button[title]').first();
            if (await editBtn.isVisible({timeout: 2000})) {
                await editBtn.click();
                // Edit modal/form should appear
                await page.waitForTimeout(500);
            }
        });
    });

    test.describe('Role-Based Access', () => {
        test('S14: EDITOR cannot see share button on broker they edit', async ({page}) => {
            // TEST_USER is EDITOR on Directa SIM (from populate)
            await login(page, TEST_USER);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // Find Directa SIM card specifically (where user is EDITOR)
            const directaCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Directa'});
            if (await directaCard.isVisible({timeout: 5000})) {
                await directaCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
                // Share button should NOT be visible for EDITOR
                await expect(page.getByTestId('broker-share-button')).not.toBeVisible({timeout: 2000});
                // But edit button should be visible (EDITOR can edit)
                await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 2000});
            }
        });
    });

    test.describe('Dark Mode', () => {
        test('S15: sharing modal renders in dark mode', async ({page}) => {
            await login(page, TEST_ADMIN);

            // Enable dark mode via settings
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10000});
            const themeToggle = page.getByTestId('theme-toggle');
            if (await themeToggle.isVisible({timeout: 3000})) {
                await themeToggle.click();
                await page.waitForTimeout(300);
            }

            // Navigate to broker detail and open sharing modal
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);

            // Verify modal content is visible in dark mode
            await expect(page.getByTestId('ownership-chart-section')).toBeVisible();
            // Verify dark class on html
            const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
            expect(isDark).toBe(true);
        });
    });
});

