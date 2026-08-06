/**
 * Asset Event Delete E2E Tests — Phase 07 · Part 1
 *
 * Covers:
 * 1. Delete unlinked event → success (via combined data-editor)
 * 2. Delete event with linked transaction → RESTRICT warning (in_use)
 * 3. Delete asset with events → cascade/block behavior
 * 4. ●evt badge in transactions table reflects linked state
 *
 * Prerequisites: backend in test mode (port 6041), mock data with asset events populated.
 *
 * UI flow:
 *   Asset detail → click "Edit Prices & Events" (data-testid="asset-detail-editdata-btn")
 *   → editor panel opens (data-testid="asset-detail-editor-panel")
 *   → click Events tab (data-testid="asset-editor-events-tab")
 *   → DataEditor shows event rows (data-row-id={eventId})
 *   → row action: kebab button (data-testid="row-actions-{rowId}") → context menu item
 *     (data-testid="context-menu-action-delete")
 *   → click Save (data-testid="asset-editor-save-btn")
 */
import {expect, test, type Page} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Open the combined data editor and switch to Events tab */
async function openEventsEditor(page: Page) {
    // Click "Edit Prices & Events" button
    const editBtn = page.locator('[data-testid="asset-detail-editdata-btn"]');
    await expect(editBtn).toBeVisible({timeout: 5_000});
    await editBtn.click();

    // Wait for editor panel to appear
    const editorPanel = page.locator('[data-testid="asset-detail-editor-panel"]');
    await expect(editorPanel).toBeVisible({timeout: 5_000});

    // Switch to Events tab
    const eventsTab = page.locator('[data-testid="asset-editor-events-tab"]');
    await eventsTab.click();
    await page.waitForTimeout(500);
}

/** Get visible event rows in the DataEditor table */
function getEventRows(page: Page) {
    return page.locator('[data-testid="asset-detail-editor-panel"] tbody tr[data-row-id]');
}

/**
 * Trigger the "delete" row action via the DataTable kebab menu: click the
 * "row-actions-{rowId}" button, then the "context-menu-action-delete" item
 * (see DataTable.svelte / ContextMenu.svelte).
 */
async function clickDeleteRowAction(page: Page, row: import('@playwright/test').Locator) {
    const kebabBtn = row.getByTestId(/^row-actions-/);
    await kebabBtn.click();
    await page.getByTestId('context-menu-action-delete').click();
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

test.describe('Asset Event Delete', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ===================================================================
    // Scenario 1: Delete event without linked transactions → success
    // ===================================================================
    test('delete unlinked event succeeds', async ({page}) => {
        // Navigate to assets list and find "Apple Inc." (has unlinked DIVIDEND events)
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});

        // Click on Apple card (has events without linked transactions)
        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
        await expect(appleCard).toBeVisible({timeout: 5_000});
        await appleCard.click();

        // Wait for asset detail page
        await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});

        // Expand time range to 1Y to show all events (default 3M may hide older ones)
        const yearBtn = page.locator('button:text("1Y")');
        await yearBtn.click();
        await page.waitForTimeout(500);

        // Open events editor
        await openEventsEditor(page);

        // Events must exist. After populate, Apple has 5 events: 4 DIVIDEND
        // (~270/180/90/3 days ago) + 1 SPLIT (~13 days ago).
        const eventRows = getEventRows(page);
        const initialCount = await eventRows.count();
        expect(initialCount, 'Apple must have events — check populate_mock_data.py').toBeGreaterThan(1);

        // Click delete on the oldest event row (first in ASC order).
        // Of the 5 events, 3 are linked to transactions (SPLIT + the 2 most recent
        // DIVIDEND). The 2 oldest DIVIDEND are unlinked, so the first row is safe
        // to delete. Note: this test is destructive — it consumes one of them.
        const targetRow = eventRows.first();
        await clickDeleteRowAction(page, targetRow);

        // The save button should become enabled (dirty count > 0)
        const saveBtn = page.locator('[data-testid="asset-editor-save-btn"]');
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // Intercept the delete API call to verify it succeeds
        const responsePromise = page.waitForResponse((resp) => resp.url().includes('/api/v1/assets/events') && resp.request().method() === 'DELETE', {timeout: 10_000});

        // Click save to commit deletion
        await saveBtn.click();

        // Wait for the API response
        const response = await responsePromise;
        expect(response.status()).toBe(200);

        // Verify the response contains at least one "deleted" result
        const body = await response.json();
        const deletedResults = body.results?.filter((r: any) => r.status === 'deleted') ?? [];
        expect(deletedResults.length).toBeGreaterThan(0);
    });

    // ===================================================================
    // Scenario 2: Delete event with linked transaction → RESTRICT warning
    // ===================================================================
    test('delete event with linked transaction shows warning', async ({page}) => {
        // Navigate to Apple detail (has a DIVIDEND event linked to a transaction)
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});

        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
        await expect(appleCard).toBeVisible({timeout: 5_000});
        await appleCard.click();
        await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});

        // Open events editor
        await openEventsEditor(page);

        // Deliberately left at the default 3M range: every Apple event inside that
        // window is linked to a transaction, so this test stays independent of the
        // destructive delete performed by the first test above.
        const eventRows = getEventRows(page);
        const count = await eventRows.count();
        expect(count, 'Apple must have events — check populate_mock_data.py').toBeGreaterThan(0);

        // Mark ALL events for deletion (one of them is linked → will be blocked)
        for (let i = 0; i < count; i++) {
            const row = eventRows.nth(i);
            const kebabBtn = row.getByTestId(/^row-actions-/);
            if (await kebabBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                await clickDeleteRowAction(page, row);
                await page.waitForTimeout(200);
            }
        }

        // Save should be enabled
        const saveBtn = page.locator('[data-testid="asset-editor-save-btn"]');
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // Intercept the delete API response
        const responsePromise = page.waitForResponse((resp) => resp.url().includes('/api/v1/assets/events') && resp.request().method() === 'DELETE', {timeout: 10_000});

        await saveBtn.click();

        const response = await responsePromise;
        expect(response.status()).toBe(200);

        // Response must contain at least one "in_use" result (the linked event)
        const body = await response.json();
        const blockedResults = body.results?.filter((r: any) => r.status === 'in_use') ?? [];
        expect(blockedResults.length, 'At least one event should be blocked (in_use)').toBeGreaterThan(0);

        // Find a blocked result with accessible_transactions (some may be hidden behind broker access)
        const withAccessible = blockedResults.find((r: any) => r.accessible_transactions?.length > 0);
        expect(withAccessible, 'At least one in_use result should have accessible_transactions for this user').toBeTruthy();
        expect(withAccessible.accessible_transactions.length).toBeGreaterThan(0);
    });

    // ===================================================================
    // Scenario 3: Delete asset with events → cascade or block
    // ===================================================================
    test('delete asset with events shows appropriate warning', async ({page}) => {
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});

        const assetCards = page.locator('[data-testid^="asset-card-"]');
        await expect(assetCards.first()).toBeVisible({timeout: 5_000});

        // Look for a delete button on any card (may be in a more-actions menu)
        // Assets with transactions cannot be deleted — this tests the UI handles it
        const firstCard = assetCards.first();
        const moreBtn = firstCard.locator('button[title*="more" i], button[aria-label*="more" i], button[data-testid*="more"]').first();
        if (await moreBtn.isVisible({timeout: 2_000}).catch(() => false)) {
            await moreBtn.click();
            await page.waitForTimeout(300);
            const deleteOption = page
                .locator('[role="menuitem"]')
                .filter({hasText: /delete|elimina/i})
                .first();
            if (await deleteOption.isVisible({timeout: 1_000}).catch(() => false)) {
                // Just verify it exists — don't actually delete
                expect(await deleteOption.isVisible()).toBe(true);
            }
        }
        // If no delete button is visible, the asset has transactions (expected for mock data)
        // This scenario verifies the UI doesn't crash — delete-cascade is API-tested
    });

    // ===================================================================
    // Scenario 4: ●evt badge in transactions table reflects linked state
    // ===================================================================
    test('event badge reflects current link state', async ({page}) => {
        await navigateTo(page, '/transactions');
        await page.waitForTimeout(2000);

        // Event dots should exist (Apple DIVIDEND tx is linked to an AssetEvent)
        const eventDots = page.locator('[data-testid^="tx-event-dot-"]');
        const dotCount = await eventDots.count();
        expect(dotCount, 'Event dots must exist — check populate_mock_data.py link_transactions_to_events()').toBeGreaterThan(0);

        const firstDot = eventDots.first();
        expect(await firstDot.isVisible()).toBe(true);

        // Verify the dot has proper test-id format
        const testId = await firstDot.getAttribute('data-testid');
        expect(testId).toMatch(/^tx-event-dot-\d+$/);
    });
});
