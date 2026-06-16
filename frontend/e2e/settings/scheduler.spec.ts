/**
 * Scheduler Settings E2E Tests
 *
 * Tests the scheduler configuration modal, log modal, and status row
 * in the Global Settings (Admin) tab. Also includes regression test
 * for fetch_interval removal from provider assignment forms.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py db populate --test)
 *
 * Test IDs: FSCH-001..FSCH-010
 */

import {expect, test} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN} from '../fixtures/test-users';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Navigate to Settings → Admin tab → Global Settings with sync category visible.
 * Waits for the scheduler rows to be present.
 */
async function goToSchedulerSettings(page: import('@playwright/test').Page) {
    await login(page, TEST_ADMIN);
    await navigateTo(page, '/settings');
    await page.getByTestId('settings-tab-admin').click();
    await expect(page.getByTestId('global-settings-tab')).toBeVisible({timeout: 10_000});

    // Click the "Scheduler & Upload" category to filter settings so scheduler rows are visible
    await page.getByTestId('global-settings-tab').getByRole('button', {name: 'Scheduler & Upload'}).click();

    // Wait for scheduler rows
    await expect(page.getByTestId('scheduler-status-row')).toBeVisible({timeout: 10_000});
}

// ---------------------------------------------------------------------------
// FSCH-001: Scheduler status row visible for admin
// ---------------------------------------------------------------------------

test.describe('Scheduler — Visibility', () => {
    test('FSCH-001: scheduler status row is visible for admin', async ({page}) => {
        await goToSchedulerSettings(page);
        await expect(page.getByTestId('scheduler-status-row')).toBeVisible();
    });

    test('FSCH-002: scheduler config row is visible for admin', async ({page}) => {
        await goToSchedulerSettings(page);
        await expect(page.getByTestId('scheduler-config-row')).toBeVisible();
    });
});

// ---------------------------------------------------------------------------
// FSCH-003..004: Log modal open / close
// ---------------------------------------------------------------------------

test.describe('Scheduler — Log Modal', () => {
    test.beforeEach(async ({page}) => {
        await goToSchedulerSettings(page);
    });

    test('FSCH-003: click status row opens log modal', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});
    });

    test('FSCH-004: log modal closes on close button', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});

        await page.getByTestId('scheduler-log-close').click();
        await expect(page.getByTestId('scheduler-log-entries')).not.toBeVisible({timeout: 3_000});
    });

    test('FSCH-004b: log modal closes on Escape key', async ({page}) => {
        await page.getByTestId('scheduler-status-row').click();
        await expect(page.getByTestId('scheduler-log-entries')).toBeVisible({timeout: 5_000});

        await page.keyboard.press('Escape');
        await expect(page.getByTestId('scheduler-log-entries')).not.toBeVisible({timeout: 3_000});
    });
});

// ---------------------------------------------------------------------------
// FSCH-005..009: Config modal
// ---------------------------------------------------------------------------

test.describe('Scheduler — Config Modal', () => {
    test.beforeEach(async ({page}) => {
        await goToSchedulerSettings(page);
    });

    test('FSCH-005: click Configure opens config modal', async ({page}) => {
        // The Configure button is inside scheduler-config-row
        const configureBtn = page.getByTestId('scheduler-config-row').getByRole('button', {name: 'Configure'});

        // If locked, unlock first
        const lockBtn = page.getByTestId('global-settings-tab').locator('button[title="Click to unlock and edit"]');
        if (await lockBtn.isVisible()) {
            await lockBtn.click();
            await page.waitForTimeout(200);
        }

        await configureBtn.click();
        await expect(page.getByTestId('scheduler-config-frequency')).toBeVisible({timeout: 5_000});
    });

    test('FSCH-006: config modal saves frequency change via PATCH /global/bulk', async ({page}) => {
        // Unlock
        const lockBtn = page.getByTestId('global-settings-tab').locator('button[title="Click to unlock and edit"]');
        if (await lockBtn.isVisible()) {
            await lockBtn.click();
            await page.waitForTimeout(200);
        }

        // Open config modal
        await page.getByTestId('scheduler-config-row').getByRole('button', {name: 'Configure'}).click();
        await expect(page.getByTestId('scheduler-config-frequency')).toBeVisible({timeout: 5_000});

        // Change frequency value
        const freqInput = page.getByTestId('scheduler-config-frequency').locator('input');
        await freqInput.fill('15');

        // Intercept the PATCH request
        const patchPromise = page.waitForRequest((req) => req.method() === 'PATCH' && req.url().includes('/settings/global/bulk'), {timeout: 5_000});

        // Save
        await page.getByTestId('scheduler-config-save').click();

        const patchReq = await patchPromise;
        const body = JSON.parse(patchReq.postData() || '{}');

        // Verify the PATCH payload contains the frequency key with new value
        const items: Array<{key: string; value: string}> = body.items || [];
        const freqItem = items.find((i) => i.key === 'scheduler_current_price_frequency_minutes');
        expect(freqItem).toBeDefined();
        expect(freqItem?.value).toBe('15');
    });

    test('FSCH-007: Cancel discards changes without PATCH request', async ({page}) => {
        // Unlock
        const lockBtn = page.getByTestId('global-settings-tab').locator('button[title="Click to unlock and edit"]');
        if (await lockBtn.isVisible()) {
            await lockBtn.click();
            await page.waitForTimeout(200);
        }

        // Open config modal
        await page.getByTestId('scheduler-config-row').getByRole('button', {name: 'Configure'}).click();
        await expect(page.getByTestId('scheduler-config-frequency')).toBeVisible({timeout: 5_000});

        // Change frequency value
        await page.getByTestId('scheduler-config-frequency').locator('input').fill('99');

        // Track whether PATCH was called
        let patchCalled = false;
        page.on('request', (req) => {
            if (req.method() === 'PATCH' && req.url().includes('/settings/global/bulk')) {
                patchCalled = true;
            }
        });

        // Cancel
        await page.getByTestId('scheduler-config-cancel').click();
        await page.waitForTimeout(500);

        expect(patchCalled).toBe(false);
        // Modal should be closed
        await expect(page.getByTestId('scheduler-config-frequency')).not.toBeVisible();
    });

    test('FSCH-008: add time slot appears in the list', async ({page}) => {
        // Unlock
        const lockBtn = page.getByTestId('global-settings-tab').locator('button[title="Click to unlock and edit"]');
        if (await lockBtn.isVisible()) {
            await lockBtn.click();
            await page.waitForTimeout(200);
        }

        // Open config modal
        await page.getByTestId('scheduler-config-row').getByRole('button', {name: 'Configure'}).click();
        await expect(page.getByTestId('scheduler-config-times')).toBeVisible({timeout: 5_000});

        // Time slots are rendered as <span class="rounded-full"> badge elements (not <li>)
        const timesSection = page.getByTestId('scheduler-config-times');
        const initialSlots = await timesSection.locator('span.rounded-full').count();

        // Add a new time slot
        await page.getByTestId('scheduler-config-time-input').fill('12:00');
        await page.getByTestId('scheduler-config-time-add').click();
        await page.waitForTimeout(300);

        // Slot count should have increased
        const newSlots = await timesSection.locator('span.rounded-full').count();
        expect(newSlots).toBeGreaterThan(initialSlots);
    });

    test('FSCH-009: delete time slot removes it from list', async ({page}) => {
        // Unlock
        const lockBtn = page.getByTestId('global-settings-tab').locator('button[title="Click to unlock and edit"]');
        if (await lockBtn.isVisible()) {
            await lockBtn.click();
            await page.waitForTimeout(200);
        }

        // Open config modal
        await page.getByTestId('scheduler-config-row').getByRole('button', {name: 'Configure'}).click();
        await expect(page.getByTestId('scheduler-config-times')).toBeVisible({timeout: 5_000});

        const timesSection = page.getByTestId('scheduler-config-times');

        // Time slots are <span class="rounded-full"> (not <li>)
        let initialCount = await timesSection.locator('span.rounded-full').count();

        if (initialCount < 2) {
            // Need at least 2 to delete one — add a slot first
            await page.getByTestId('scheduler-config-time-input').fill('14:00');
            await page.getByTestId('scheduler-config-time-add').click();
            await page.waitForTimeout(300);
            initialCount = await timesSection.locator('span.rounded-full').count();
        }

        // Delete first slot via its remove button (the <button> inside the span badge)
        const firstSlotDeleteBtn = timesSection.locator('span.rounded-full button').first();
        await firstSlotDeleteBtn.click();
        await page.waitForTimeout(300);

        const afterCount = await timesSection.locator('span.rounded-full').count();
        expect(afterCount).toBeLessThan(initialCount);
    });
});

// ---------------------------------------------------------------------------
// FSCH-010: Regression — no fetch_interval field in provider assignment forms
// ---------------------------------------------------------------------------

test.describe('Scheduler — Regression (fetch_interval removed)', () => {
    test('FSCH-010: provider assignment form has no fetch_interval field', async ({page}) => {
        await login(page, TEST_ADMIN);
        await navigateTo(page, '/assets');

        // Open the first asset in the list
        const firstAssetRow = page.locator('[data-testid="asset-table"] tbody tr').first();
        if (!(await firstAssetRow.isVisible({timeout: 5_000}))) {
            // Fallback: no assets — check via card view
            const firstCard = page.locator('[data-testid^="asset-card-"]').first();
            if (!(await firstCard.isVisible({timeout: 3_000}))) {
                test.skip(true, 'No assets found in test database — skipping fetch_interval regression test');
                return;
            }
            await firstCard.click();
        } else {
            await firstAssetRow.click();
        }

        // Open the edit modal (pencil icon / Edit button)
        const editBtn = page.locator('button[data-testid="asset-edit-button"], button[title*="Edit"], button[aria-label*="edit"]').first();
        if (await editBtn.isVisible({timeout: 3_000})) {
            await editBtn.click();
        }

        // There must be no input with name/id/placeholder related to fetch_interval
        const fetchIntervalInput = page.locator('input[name="fetch_interval"], input[id*="fetch_interval"], input[placeholder*="fetch interval" i]');
        await expect(fetchIntervalInput).not.toBeVisible();
    });
});
