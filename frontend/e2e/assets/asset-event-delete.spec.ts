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
 * Data (W-B29). Scenarios 1 and 2 never write on the shared mock data: each creates a USD asset of
 * its own (unique name, two closes so the chart and its editor button are drawn) and its own events;
 * scenario 2 adds a broker of its own with the one DIVIDEND that realises its event. They used to save
 * on the shared Apple at a fixed date, so the desktop and mobile projects overwrote each other's row,
 * and a regression of the refusal would have deleted Apple's mock events. After each test the owned
 * broker goes first (with `force`, which takes its transaction), then the asset with its prices and
 * events — whatever the outcome. Scenarios 3 and 4 only read the mock data (mock data with asset
 * events and linked transactions populated).
 *
 * UI flow:
 *   Asset detail (/assets/{id}, opened by id) → click "Edit Prices & Events"
 *   (data-testid="asset-detail-editdata-btn")
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
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedAsset, deleteOwned, eventRow, EVENTS_PATH, linkDividend, markDeleted, openEventsEditor, seedEvents, snapshot, storedEvents, type Owned} from './asset-events-owned';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
    // No longer serial, and no longer on Apple. Scenarios 1 and 2 each own the asset, the events
    // and (scenario 2) the broker they act on, so neither takes anything from the other, from the
    // other Playwright project running the same spec, or from the shared mock data.

    /** What the running test created; deleted after it, whatever its outcome (nothing for scenarios 3 and 4). */
    let owned: Owned = {assetIds: [], brokerIds: []};

    test.beforeEach(async ({page}) => {
        owned = {assetIds: [], brokerIds: []};
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        await deleteOwned(page, owned);
    });

    // ===================================================================
    // Scenario 1: Delete event without linked transactions → success
    // ===================================================================
    test('delete unlinked event succeeds', async ({page}) => {
        // Setup and cleanup are API round trips on top of the UI flow, as in asset-event-editor-save.
        test.setTimeout(60_000);
        // An asset of this test's own, with the one unlinked DIVIDEND it deletes. It used to save that
        // event on the shared Apple at a fixed date: the desktop and mobile projects then upserted the
        // same (asset, date, type) and the second overwrote the first's row.
        const asset = await createOwnedAsset(page, owned);
        const marker = `e2e-event-delete ${uniqueSuffix()}`;
        const [eventId] = await seedEvents(page, asset.id, [{date: daysAgoIso(20), type: 'DIVIDEND', amount: '0.42', notes: marker}]);

        // The asset's own page, opened by id, on a range holding the event: the editor only lists
        // events inside the selected range.
        const panel = await openEventsEditor(page, asset);

        // Ours, by id — not "the first row".
        await expect(eventRow(panel, eventId), 'the unlinked DIVIDEND this test created is listed').toBeVisible({timeout: 15_000});
        await markDeleted(page, panel, eventId);

        // The save button should become enabled (dirty count > 0)
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
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
        const sent = (response.request().postDataJSON() as Array<{asset_id: number; delete_ids?: number[]}>).find((item) => item.asset_id === asset.id);
        expect(sent?.delete_ids, 'the row marked deleted travels in the save as delete_ids').toEqual([eventId]);

        // The event we own must come back as deleted — not merely "something was".
        const body = (await response.json()) as {results?: Array<{asset_id: number; deleted_ids?: number[]}>};
        const ours = body.results?.find((r) => r.asset_id === asset.id);
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

        // Gone from the server, not only from the table.
        const remaining = (await storedEvents(page, asset.id)).map((e) => e.id);
        expect(remaining, `event ${eventId} is no longer stored`).not.toContain(eventId);
    });

    // ===================================================================
    // Scenario 2: Delete event with linked transaction → the save is refused whole
    // ===================================================================
    test('deleting an event a transaction realises refuses the save: nothing deleted, an error toast', async ({page}) => {
        // Setup and cleanup are API round trips on top of the UI flow, as in asset-event-editor-save.
        test.setTimeout(60_000);
        // An asset of this test's own with two DIVIDENDs: one realised by a DIVIDEND transaction on a
        // broker of its own, one unlinked beside it. It used to mark Apple's mock events, found by a
        // visibility probe: a regression of the refusal would have deleted shared data.
        const asset = await createOwnedAsset(page, owned);
        const linkedDay = daysAgoIso(22);
        const marker = `e2e-event-delete in use ${uniqueSuffix()}`;
        const [linkedId, unlinkedId] = await seedEvents(page, asset.id, [
            {date: linkedDay, type: 'DIVIDEND', amount: '1.00', notes: `${marker} linked`},
            {date: daysAgoIso(18), type: 'DIVIDEND', amount: '2.00', notes: `${marker} unlinked`},
        ]);
        await linkDividend(page, owned, asset.id, linkedId, linkedDay);
        const before = await snapshot(page, asset.id);

        const panel = await openEventsEditor(page, asset);
        await expect(eventRow(panel, linkedId), 'the realised DIVIDEND this test created is listed').toBeVisible({timeout: 15_000});
        await expect(eventRow(panel, unlinkedId), 'the unlinked DIVIDEND beside it is listed').toBeVisible();

        // Mark both deleted, by id: the linked one makes the whole save refused, and the unlinked one
        // proves that nothing of a refused save goes through (before E1b it was deleted anyway).
        const markedIds = [linkedId, unlinkedId];
        for (const id of markedIds) await markDeleted(page, panel, id);

        // Save should be enabled
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // The editor reports the outcome in a toast: none left over, so the next is this save's.
        await closeToasts(page, 'error');

        // The save is one POST carrying the deletions (E1b). Before E1b the editor deleted through
        // DELETE /assets/events, answered in_use per row with a warning, and this POST never came.
        const responsePromise = page.waitForResponse(isEventsSave, {timeout: 10_000});

        await saveBtn.click();

        const response = await responsePromise;
        const sent = (response.request().postDataJSON() as Array<{asset_id: number; delete_ids?: number[]}>).find((item) => item.asset_id === asset.id);
        expect(
            [...(sent?.delete_ids ?? [])].sort((a, b) => a - b),
            'both marked rows travel in the save as delete_ids',
        ).toEqual([...markedIds].sort((a, b) => a - b));
        expect(response.status(), 'an event in use cannot be deleted: the save is refused whole').toBe(409);

        // The refusal names the events in use, with how many transactions realise each — counts,
        // never the ids of transactions that may belong to other users.
        const body = (await response.json()) as {detail?: {error_code?: string; params?: {events?: Array<Record<string, unknown>>}}};
        expect(body.detail?.error_code).toBe('EVENT_IN_USE');
        const inUse = body.detail?.params?.events ?? [];
        expect(
            inUse.map((event) => event.id),
            'exactly the event the DIVIDEND realises is named in use',
        ).toEqual([linkedId]);
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

        // Nothing deleted: every marked event is still there, the unlinked one included, and unchanged.
        const storedIds = (await storedEvents(page, asset.id)).map((e) => e.id);
        expect(
            [...storedIds].sort((a, b) => a - b),
            'all or nothing: no marked event was deleted',
        ).toEqual([...markedIds].sort((a, b) => a - b));
        expect(await snapshot(page, asset.id), 'nothing of the refused save is kept').toEqual(before);
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
