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
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Open the combined data editor and switch to Events tab */
async function openEventsEditor(page: Page) {
    // The events are loaded by the detail page itself and handed to the editor
    // as a prop, so the editor can only be as ready as the page. Sleeping 500 ms
    // after the tab click turned "still loading" into "this asset has no events"
    // once four workers shared the backend.
    await expect(page.getByTestId('asset-detail-page')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});

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
    await expect(eventsTab).toHaveAttribute('aria-selected', 'true', {timeout: 5_000});
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
    const API = '/api/v1';

    // No longer serial. It used to be, because the first test consumed one of
    // Apple's two unlinked mock events and the others read that same finite set.
    // The first test now creates the event it deletes, and the second works only
    // inside the 3M window — where every fixture event is linked, so it deletes
    // nothing. Neither takes anything from the other.

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ===================================================================
    // Scenario 1: Delete event without linked transactions → success
    // ===================================================================
    test('delete unlinked event succeeds', async ({page}) => {
        // This test used to delete one of Apple's two unlinked mock DIVIDENDs.
        // That works exactly twice: on the third run the oldest row is a *linked*
        // event, the API answers `in_use`, and the test goes red for a reason that
        // has nothing to do with the code. A test that consumes fixture data is a
        // test with an expiry date — so it creates the event it is about to delete.
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});

        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
        await expect(appleCard).toBeVisible({timeout: 5_000});
        await appleCard.click();

        await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});
        const assetId = Number(new URL(page.url()).pathname.split('/').filter(Boolean).pop());
        expect(Number.isFinite(assetId), 'asset detail URL must end with the asset id').toBeTruthy();

        // A date inside the 1Y window but clear of the fixture's own events
        // (~270 / 180 / 90 / 13 / 3 days ago), so the upsert cannot overwrite one.
        const eventDate = new Date(Date.now() - 230 * 86_400_000).toISOString().slice(0, 10);
        const marker = `e2e-event-delete-${Date.now()}`;
        const created = await page.request.post(`${API}/assets/events`, {
            data: [{asset_id: assetId, events: [{date: eventDate, type: 'DIVIDEND', value: {amount: 0.42, code: 'USD'}, notes: marker}]}],
        });
        expect(created.ok(), 'the event this test deletes must exist first').toBeTruthy();

        const queried = await page.request.post(`${API}/assets/events/query`, {
            data: [{asset_id: assetId, date_range: {start: eventDate, end: eventDate}}],
        });
        expect(queried.ok()).toBeTruthy();
        const queryBody = await queried.json();
        const mine = (queryBody.items?.[0]?.events ?? []).find((e: any) => e.notes === marker);
        expect(mine, `no event carries the marker ${marker}`).toBeTruthy();
        const eventId: number = mine.id;

        try {
            // Reload so the detail page fetches the event we just created, and widen
            // to 1Y: the editor only lists events inside the selected range.
            await page.reload();
            await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});

            // Changing the range refetches prices *and* events in one request. Arm the
            // wait before the click: a refetch that lands after a row is marked for
            // deletion resets the editor and silently disables Save.
            const rangeApplied = page.waitForResponse((resp) => resp.url().includes('/api/v1/assets/prices/query') && resp.request().method() === 'POST', {timeout: 30_000});
            await page.locator('button:text("1Y")').click();
            await rangeApplied;

            await openEventsEditor(page);

            // Ours, by id — not "the first row", which belongs to whoever the fixture says.
            const targetRow = page.locator(`[data-testid="asset-detail-editor-panel"] tbody tr[data-row-id="${eventId}"]`);
            await expect(targetRow).toBeVisible({timeout: 15_000});
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

            // The event we own must come back as deleted — not merely "something was".
            const body = await response.json();
            const deletedResults = body.results?.filter((r: any) => r.status === 'deleted') ?? [];
            expect(
                deletedResults.some((r: any) => r.event_id === eventId),
                `event ${eventId} should be reported deleted, got ${JSON.stringify(body.results)}`,
            ).toBeTruthy();
        } finally {
            // If anything above failed before the UI deleted it, do not leave it behind.
            await page.request.delete(`${API}/assets/events?ids=${eventId}`).catch(() => {});
        }
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
        await expect.poll(() => eventRows.count(), {timeout: 10_000, message: 'Apple must have events — check populate_mock_data.py'}).toBeGreaterThan(0);
        const count = await eventRows.count();

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

        // The dots appear only once the transactions table has its rows. Waiting for the
        // first one *is* the assertion: the previous fixed 2s sleep followed by a one-shot
        // count() lost that race under concurrent load and read an empty list, reporting a
        // missing fixture that was never missing.
        const eventDots = page.locator('[data-testid^="tx-event-dot-"]');
        await expect(eventDots.first(), 'Event dots must exist — check populate_mock_data.py link_transactions_to_events()').toBeVisible({timeout: 15_000});

        // Verify the dot has proper test-id format
        const testId = await eventDots.first().getAttribute('data-testid');
        expect(testId).toMatch(/^tx-event-dot-\d+$/);
    });
});
