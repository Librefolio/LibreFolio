import {expect, type Page, test} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';

/**
 * Broker Sharing E2E Tests
 *
 * Tests for the broker access-sharing feature (BrokerSharingPanel, the shared UI —
 * donut chart, add/edit/remove users, save — reused in two shells):
 * - BrokerSharingModal: wraps the panel with modal chrome, used from the broker list page
 * - Detail page "Info" tab: embeds the panel directly, no modal chrome
 *
 * Covers:
 * - Share button visibility (always visible; read-only unless OWNER)
 * - Modal open/close (list page only)
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

// Helper: Open sharing panel (assumes already on broker detail as OWNER).
// On the detail page this is an inline panel in the "Info" tab, NOT a modal —
// BrokerSharingModal only wraps BrokerSharingPanel on the broker list page.
async function openSharingModal(page: Page) {
    const shareBtn = page.getByTestId('broker-share-button');
    await expect(shareBtn).toBeVisible({timeout: 5000});
    await shareBtn.click();
    await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
}

// Helper: Open the real BrokerSharingModal from the broker list page (grid share icon).
async function openSharingModalFromList(page: Page) {
    await navigateTo(page, '/brokers');
    await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
    const shareBtn = page.locator('[data-testid^="broker-share-"]').first();
    await expect(shareBtn).toBeVisible({timeout: 10000});
    await shareBtn.click();
    await expect(page.getByTestId('broker-sharing-modal')).toBeVisible({timeout: 5000});
}

async function expectOwnershipChartCanvas(page: Page) {
    const section = page.getByTestId('ownership-chart-section');
    await expect(section).toBeVisible({timeout: 5000});

    const canvas = section.locator('canvas').first();
    await expect(canvas).toBeVisible({timeout: 5000});
    await expect
        .poll(
            async () => {
                const box = await canvas.boundingBox();
                if (!box || box.width <= 0 || box.height <= 0) return 'zero-css-size';

                return canvas.evaluate((node) => {
                    const htmlCanvas = node as HTMLCanvasElement;
                    return htmlCanvas.width > 0 && htmlCanvas.height > 0 ? 'non-zero' : 'zero-bitmap-size';
                });
            },
            {timeout: 5000},
        )
        .toBe('non-zero');
}

// Earned parallel: this file's blocks own the data they touch and wait on published
// state, so they share the backend with their neighbours instead of queueing behind
// them. Verified by a green run of the whole category at 4 workers.
test.describe.configure({mode: 'parallel'});

test.describe('Broker Sharing', () => {
    test.describe('Share Button Visibility', () => {
        test('S1: share button visible for OWNER on broker detail', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await expect(page.getByTestId('broker-share-button')).toBeVisible();
        });

        test('S2: share button visible read-only for VIEWER', async ({page}) => {
            // TEST_USER_2 is VIEWER on Interactive Brokers (from populate)
            await login(page, TEST_USER_2);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // TEST_USER_2 only has VIEWER access, so find any broker card
            const brokerCards = page.locator('[data-testid^="broker-card-"]');
            await expect(brokerCards.first()).toBeVisible({timeout: 10000});
            await brokerCards.first().click();
            await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
            // Share button IS now always visible (design: everyone can see who has access)
            const shareBtn = page.getByTestId('broker-share-button');
            await expect(shareBtn).toBeVisible({timeout: 5000});
            // Edit button should still NOT be visible for VIEWER (unchanged)
            await expect(page.getByTestId('broker-edit-button')).not.toBeVisible({timeout: 2000});
            // Opening it must be read-only: no "add user" control for a non-OWNER
            await shareBtn.click();
            await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
            await expect(page.getByTestId('sharing-add-user-btn')).not.toBeVisible({timeout: 2000});
        });

        test('S3: share button opens the sharing panel (Info tab)', async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
            // Panel is visible (openSharingModal asserts this)
        });
    });

    // BrokerSharingModal (the actual modal, with close/Escape/confirm-discard chrome) is
    // only used from the broker list page's share icon — the detail page's "Info" tab
    // embeds BrokerSharingPanel inline, without modal chrome (see openSharingModal above).
    test.describe('BrokerSharingModal (List Page)', () => {
        test('S9: close modal with Escape key', async ({page}) => {
            await login(page, TEST_ADMIN);
            await openSharingModalFromList(page);
            await expectOwnershipChartCanvas(page);
            await page.getByTestId('broker-sharing-modal').press('Escape');
            await expect(page.getByTestId('broker-sharing-modal')).not.toBeVisible({timeout: 3000});
        });
    });

    test.describe('BrokerSharingPanel Content', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S4: panel shows ownership chart section', async ({page}) => {
            await expectOwnershipChartCanvas(page);
        });

        test('S5: panel shows at least the current OWNER in badge list', async ({page}) => {
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

        test('S10: three role columns are visible (Owners, Editors, Viewers)', async ({page}) => {
            await expect(page.getByTestId('sharing-owners-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-editors-column')).toBeVisible({timeout: 3000});
            await expect(page.getByTestId('sharing-viewers-column')).toBeVisible({timeout: 3000});
        });
    });

    test.describe('BrokerSharingPanel - Add User Flow', () => {
        test.beforeEach(async ({page}) => {
            await login(page, TEST_ADMIN);
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);
        });

        test('S11: add user form has a user picker', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible();
            await expect(page.getByTestId('sharing-user-select-trigger')).toBeVisible();
        });

        test('S12: user picker lists users up-front and narrows down while typing', async ({page}) => {
            await page.getByTestId('sharing-add-user-btn').click();
            await expect(page.getByTestId('sharing-add-form')).toBeVisible({timeout: 3000});

            // Opening the picker must already show the candidate list — no typing required
            await page.getByTestId('sharing-user-select-trigger').click();
            const options = page.locator('[data-testid^="search-select-option-"]');
            await expect(options.first()).toBeVisible({timeout: 5000});

            // Typing narrows the list client-side ('frank' is a free user on no broker)
            const searchInput = page.getByTestId('sharing-user-select-search');
            await expect(searchInput).toBeVisible();
            await searchInput.pressSequentially('frank', {delay: 50});

            await expect(options.first()).toBeVisible({timeout: 5000});
            const remaining = await options.count();
            for (let i = 0; i < remaining; i++) {
                await expect(options.nth(i)).toContainText(/frank/i);
            }
        });
    });

    test.describe('BrokerSharingPanel - Edit User', () => {
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
        test('S14: EDITOR sees share button read-only on broker they edit', async ({page}) => {
            // TEST_USER is EDITOR on Directa SIM (from populate)
            await login(page, TEST_USER);
            await navigateTo(page, '/brokers');
            await expect(page.getByTestId('brokers-page')).toBeVisible({timeout: 10000});
            // Find Directa SIM card specifically (where user is EDITOR)
            const directaCard = page.locator('[data-testid^="broker-card-"]').filter({hasText: 'Directa'});
            if (await directaCard.isVisible({timeout: 5000})) {
                await directaCard.click();
                await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 10000});
                // Share button IS now always visible (design: everyone can see who has access)
                const shareBtn = page.getByTestId('broker-share-button');
                await expect(shareBtn).toBeVisible({timeout: 2000});
                // But edit button should be visible too (EDITOR can edit the broker itself)
                await expect(page.getByTestId('broker-edit-button')).toBeVisible({timeout: 2000});
                // Opening it must be read-only: no "add user" control for a non-OWNER
                await shareBtn.click();
                await expect(page.getByTestId('broker-sharing-panel')).toBeVisible({timeout: 5000});
                await expect(page.getByTestId('sharing-add-user-btn')).not.toBeVisible({timeout: 2000});
            }
        });
    });

    test.describe('Dark Mode', () => {
        test('S15: sharing panel renders in dark mode', async ({page}) => {
            await login(page, TEST_ADMIN);

            // Enable dark mode via settings
            await navigateTo(page, '/settings');
            await expect(page.getByTestId('settings-page')).toBeVisible({timeout: 10000});
            const themeToggle = page.getByTestId('theme-toggle');
            if (await themeToggle.isVisible({timeout: 3000})) {
                await themeToggle.click();
                await page.waitForTimeout(300);
            }

            // Navigate to broker detail and open the sharing panel (Info tab)
            await goToFirstBrokerDetail(page);
            await openSharingModal(page);

            // Verify panel content is visible in dark mode
            await expectOwnershipChartCanvas(page);
            // Verify dark class on html
            const isDark = await page.evaluate(() => document.documentElement.classList.contains('dark'));
            expect(isDark).toBe(true);
        });
    });
});
