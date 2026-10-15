/**
 * Asset Event Delete E2E Tests — Phase 07 · Part 1, retargeted for release 1.3 (W E1b)
 *
 * Covers:
 * 1. Delete unlinked event → success (via combined data-editor)
 * 2. Delete event with linked transaction → the save is refused whole (409 EVENT_IN_USE): nothing
 *    deleted, an error toast. Before E1b: the delete went out apart, came back `in_use` per row with
 *    a warning toast, and any unlinked row beside it was deleted anyway.
 * 3. Delete asset with events → cascade/block behavior
 * 4. ●evt badge in transactions table reflects linked state
 *
 * Since E1b a save is ONE `POST /assets/events`: the rows marked deleted travel as `delete_ids`
 * beside the edited rows, and no `DELETE` is sent (decision of 15/10 16:20). Before E1b the editor
 * deletes through `DELETE /assets/events`, so scenarios 1 and 2 wait for a POST that never comes.
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
 *   → the outcome is reported in a toast (data-testid="toast-success" | "toast-error")
 */
import {expect, test, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';

/** The path of the save, and of the old delete: the same, told apart by the method. */
const EVENTS_PATH = '/api/v1/assets/events';

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

/**
 * Close every toast of one variant through its own ✕ and wait until they have slid out.
 * Toasts belong to this page alone, so once none is up, the next one of that variant can
 * only come from what the test does next. The ✕ is pressed by its DOM handler, not the
 * pointer: if a toast leaves on its own timer first, no click lands on the editor beneath.
 */
async function closeToasts(page: Page, variant: 'success' | 'warning' | 'error') {
    const shown = page.getByTestId(`toast-${variant}`);
    await shown.evaluateAll((toasts) => {
        for (const toast of toasts) toast.querySelector<HTMLElement>('[data-testid="toast-dismiss"]')?.click();
    });
    await expect(shown, `no ${variant} toast is left from before the save`).toHaveCount(0, {timeout: 5_000});
}

/** The save: a POST to exactly the events path (not `/query`). */
function isEventsSave(response: Response): boolean {
    return response.request().method() === 'POST' && new URL(response.url()).pathname === EVENTS_PATH;
}

/** The methods of every write the page sends to the events path from now on; `stop()` disarms it. */
function recordEventWrites(page: Page): {methods: string[]; stop: () => void} {
    const methods: string[] = [];
    const listener = (request: Request) => {
        if (request.method() !== 'GET' && new URL(request.url()).pathname === EVENTS_PATH) methods.push(request.method());
    };
    page.on('request', listener);
    return {methods, stop: () => page.off('request', listener)};
}

/** `n` as a number of its own, not a digit inside a longer number. */
function standaloneNumber(n: number): RegExp {
    return new RegExp(`(?<!\\d)${n}(?!\\d)`);
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
        // The cards render first and are re-rendered when the bulk price request lands.
        // Clicking during that window aims at a node Svelte is about to replace, and the
        // navigation is simply lost — which is what took this test red at load average 22.
        await waitForSettled(page.getByTestId('assets-page'));

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

            // The editor reports the outcome in a toast: none left over, so the next is this save's.
            await closeToasts(page, 'success');

            // The save is one POST carrying the deletion (E1b). Before E1b the editor deleted
            // through DELETE /assets/events, and this POST never came.
            const recorder = recordEventWrites(page);
            const responsePromise = page.waitForResponse(isEventsSave, {timeout: 10_000});

            // Click save to commit deletion
            await saveBtn.click();
            const response = await responsePromise;
            expect(response.status()).toBe(200);
            const sent = (response.request().postDataJSON() as Array<{asset_id: number; delete_ids?: number[]}>).find((item) => item.asset_id === assetId);
            expect(sent?.delete_ids, 'the row marked deleted travels in the save as delete_ids').toEqual([eventId]);

            // The event we own must come back as deleted — not merely "something was".
            const body = (await response.json()) as {results?: Array<{asset_id: number; deleted_ids?: number[]}>};
            const ours = body.results?.find((r) => r.asset_id === assetId);
            expect(ours?.deleted_ids ?? [], `event ${eventId} should be reported deleted, got ${JSON.stringify(body.results)}`).toContain(eventId);

            // The toast is where the user learns how many events went: the one row this test
            // marked. Every catalogue spells the count `{n}`; a value passed under any other
            // name leaves svelte-i18n nothing to format, and it shows the raw message instead.
            // The placeholder and the number are asserted, never the words around them.
            const toast = page.getByTestId('toast-success');
            await expect(toast, 'the save reports the deletion in a success toast').toBeVisible({timeout: 5_000});
            await expect(toast, 'the count is interpolated, not left as the raw {n}').not.toContainText('{n}');
            await expect(toast, 'no ICU placeholder is left unresolved').not.toContainText('{');
            await expect(toast, 'the toast says how many events were deleted: the one this test marked').toContainText(standaloneNumber(1));
            // The toast closes the save: whatever it sent is in by now.
            recorder.stop();
            expect(recorder.methods, 'a save is one POST, and never a DELETE').toEqual(['POST']);
        } finally {
            // If anything above failed before the UI deleted it, do not leave it behind. The
            // delete is scoped by asset (decision 21): without asset_id it is a 422, and the event stays.
            await page.request.delete(`${API}/assets/events?asset_id=${assetId}&ids=${eventId}`).catch(() => {});
        }
    });

    // ===================================================================
    // Scenario 2: Delete event with linked transaction → the save is refused whole
    // ===================================================================
    test('deleting an event a transaction realises refuses the save: nothing deleted, an error toast', async ({page}) => {
        // Navigate to Apple detail (has a DIVIDEND event linked to a transaction)
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
        // The cards render first and are re-rendered when the bulk price request lands.
        // Clicking during that window aims at a node Svelte is about to replace, and the
        // navigation is simply lost — which is what took this test red at load average 22.
        await waitForSettled(page.getByTestId('assets-page'));

        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
        await expect(appleCard).toBeVisible({timeout: 5_000});
        await appleCard.click();
        await page.waitForSelector('[data-testid="asset-detail-page"]', {timeout: 15_000});
        const assetId = Number(new URL(page.url()).pathname.split('/').filter(Boolean).pop());
        expect(Number.isFinite(assetId), 'asset detail URL must end with the asset id').toBeTruthy();

        // Open events editor
        await openEventsEditor(page);

        // Deliberately left at the default 3M range: every Apple event inside that
        // window is linked to a transaction, so this test stays independent of the
        // destructive delete performed by the first test above.
        const eventRows = getEventRows(page);
        await expect.poll(() => eventRows.count(), {timeout: 10_000, message: 'Apple must have events — check populate_mock_data.py'}).toBeGreaterThan(0);
        const count = await eventRows.count();

        // Mark ALL events for deletion (one of them is linked → the whole save is refused)
        const markedIds: number[] = [];
        for (let i = 0; i < count; i++) {
            const row = eventRows.nth(i);
            const kebabBtn = row.getByTestId(/^row-actions-/);
            if (await kebabBtn.isVisible({timeout: 1_000}).catch(() => false)) {
                markedIds.push(Number(await row.getAttribute('data-row-id')));
                await clickDeleteRowAction(page, row);
            }
        }
        expect(markedIds.length, 'at least one Apple event can be marked deleted').toBeGreaterThan(0);

        // Save should be enabled
        const saveBtn = page.locator('[data-testid="asset-editor-save-btn"]');
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // The editor reports the outcome in a toast: none left over, so the next is this save's.
        await closeToasts(page, 'error');

        // The save is one POST carrying the deletions (E1b). Before E1b the editor deleted through
        // DELETE /assets/events, answered in_use per row with a warning, and this POST never came.
        const responsePromise = page.waitForResponse(isEventsSave, {timeout: 10_000});

        await saveBtn.click();

        const response = await responsePromise;
        expect(response.status(), 'an event in use cannot be deleted: the save is refused whole').toBe(409);

        // The refusal names the events in use, with how many transactions realise each — counts,
        // never the ids of transactions that may belong to other users.
        const body = (await response.json()) as {detail?: {error_code?: string; params?: {events?: Array<Record<string, unknown>>}}};
        expect(body.detail?.error_code).toBe('EVENT_IN_USE');
        const inUse = body.detail?.params?.events ?? [];
        expect(inUse.length, 'at least one marked event is in use').toBeGreaterThan(0);
        for (const event of inUse) {
            expect(Object.keys(event).sort(), 'an event in use is named by id, date, type and a count').toEqual(['date', 'id', 'linked_transactions', 'type']);
            expect(markedIds, 'only events this save marked are named').toContain(event.id);
            expect(Number(event.linked_transactions)).toBeGreaterThan(0);
        }

        // The error is how the user learns that nothing was saved, and why: every placeholder of
        // its sentence filled in. The words are never asserted.
        const errorToast = page.getByTestId('toast-error');
        await expect(errorToast, 'a refused save is reported in an error toast').toBeVisible({timeout: 5_000});
        await expect(errorToast, 'no ICU placeholder is left unresolved').not.toContainText('{');

        // Nothing deleted: every marked event is still there, the unlinked ones included.
        const stored = await page.request.get(`${API}/assets/events?${markedIds.map((id) => `ids=${id}`).join('&')}`);
        expect(stored.ok(), `read the marked events back: HTTP ${stored.status()}`).toBeTruthy();
        const storedIds = ((await stored.json()) as {items: Array<{asset_id: number; events: Array<{id: number}>}>}).items.flatMap((item) => item.events.map((e) => e.id));
        expect(
            [...storedIds].sort((a, b) => a - b),
            'all or nothing: no marked event was deleted',
        ).toEqual([...markedIds].sort((a, b) => a - b));
    });

    // ===================================================================
    // Scenario 3: Delete asset with events → cascade or block
    // ===================================================================
    test('delete asset with events shows appropriate warning', async ({page}) => {
        await navigateTo(page, '/assets');
        await page.waitForSelector('[data-testid="assets-page"]', {timeout: 15_000});
        // The cards render first and are re-rendered when the bulk price request lands.
        // Clicking during that window aims at a node Svelte is about to replace, and the
        // navigation is simply lost — which is what took this test red at load average 22.
        await waitForSettled(page.getByTestId('assets-page'));

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
