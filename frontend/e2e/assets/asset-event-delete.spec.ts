/**
 * Asset Event Delete E2E Tests — Phase 07 · Part 1, retargeted for release 1.3 (W E1b)
 *
 * Covers:
 * 1. Delete unlinked event → success (via combined data-editor)
 * 2. Delete event with linked transaction → the save is refused whole (409 EVENT_IN_USE): nothing
 *    deleted, an error toast. Before E1b: the delete went out apart, came back `in_use` per row with
 *    a warning toast, and any unlinked row beside it was deleted anyway.
 * 3. Delete an asset with an event → the confirmation names the asset; cancelled, the asset and its
 *    event are still stored. The page gives no event-specific warning (what it does show: the scenario).
 * 4. ●evt dot in the transactions table follows the link: drawn on a DIVIDEND that realises an event,
 *    gone once that DIVIDEND is unlinked.
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
 * events — whatever the outcome. Scenarios 3 and 4 (W-B42) own their data the same way: scenario 3
 * an asset with one event, scenario 4 an asset, its event and the DIVIDEND that realises it. They used
 * to read the mock data and take "the first" card or dot, and scenario 3 could pass asserting nothing.
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
import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE} from './assets-helpers';
import {createOwnedAsset, deleteOwned, eventRow, EVENTS_PATH, jsonFrom, linkDividend, markDeleted, openEventsEditor, seedEvents, snapshot, storedEvents, type Owned, type OwnedAsset} from './asset-events-owned';

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
// Scenario 3: the assets list
// ---------------------------------------------------------------------------

/** The assets list, answered offline, once it has settled. */
async function openAssetsList(page: Page): Promise<Locator> {
    // The list polls POST /assets/prices/current for every listed asset, which may ask live providers and
    // write today's price into the shared database. Nothing here is about live prices: answered locally.
    await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    await navigateTo(page, '/assets');
    const assetsPage = page.getByTestId('assets-page');
    // The cards render first and are re-rendered when the bulk price request lands. Clicking during that
    // window aims at a node Svelte is about to replace — which took this scenario red at load average 22.
    await waitForSettled(assetsPage, 30_000);
    return assetsPage;
}

/**
 * Narrow the list view to one asset by its unique name, and wait until it holds that row and no other.
 * The search is debounced: a row acted on before it lands can be redrawn under the pointer.
 */
async function narrowListTo(page: Page, assetsPage: Locator, asset: OwnedAsset): Promise<void> {
    const search = page.getByTestId('assets-search-input');
    await search.fill(asset.name);
    await expect(search).toHaveValue(asset.name);
    await expect
        .poll(() => assetsPage.locator('tbody tr[data-row-id]').evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id'))), {
            message: `the search narrows the list view to asset ${asset.id} alone`,
            timeout: 10_000,
        })
        .toEqual([String(asset.id)]);
}

/** The asset as the server has it — id and name — or nothing once it is deleted. */
async function storedAssets(page: Page, assetId: number): Promise<Array<{asset_id: number; display_name: string}>> {
    const found = await jsonFrom<Array<{asset_id: number; display_name: string}>>(await page.request.get(`${API_BASE}/assets`, {params: {asset_ids: assetId}}), `read asset ${assetId}`);
    return found.map(({asset_id, display_name}) => ({asset_id, display_name}));
}

// ---------------------------------------------------------------------------
// Scenario 4: the transactions table
// ---------------------------------------------------------------------------

/** What scenario 4 reads of a stored transaction. */
type StoredTransaction = {id: number; broker_id: number; type: string; asset_event_id?: number | null};

/** One transaction as the server has it. */
async function storedTransaction(page: Page, txId: number): Promise<StoredTransaction> {
    const rows = await jsonFrom<StoredTransaction[]>(await page.request.get(`${API_BASE}/transactions`, {params: {ids: txId}}), `read transaction ${txId}`);
    const tx = rows.find((row) => row.id === txId);
    if (!tx) throw new Error(`Transaction ${txId} is not stored: ${JSON.stringify(rows)}`);
    return tx;
}

/**
 * The transactions page narrowed by its URL to one broker — a full load, so the table reads the
 * transactions afresh — and, once settled, the row of `txId`, found by its id and drawn.
 */
async function openTransactionRow(page: Page, brokerId: number, txId: number): Promise<Locator> {
    await navigateTo(page, `/transactions?broker_id=${brokerId}`);
    await waitForSettled(page.getByTestId('transactions-page'), 30_000);
    const row = page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${txId}"]`);
    await expect(row, `the row of transaction ${txId} is listed`).toBeVisible({timeout: 10_000});
    await expect(row.getByTestId(`tx-id-${txId}`), `the row of transaction ${txId} is drawn`).toBeVisible();
    return row;
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

test.describe('Asset Event Delete', () => {
    // No longer serial, and no longer on Apple. Each scenario owns the asset, the events and
    // (scenarios 2 and 4) the broker it acts on, so none takes anything from another, from the
    // other Playwright project running the same spec, or from the shared mock data.

    /** What the running test created; deleted after it, whatever its outcome. */
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
    // Scenario 3: Delete an asset with an event → the confirmation names it; cancelled, nothing goes
    // ===================================================================
    test('delete asset with events shows appropriate warning', async ({page}) => {
        // Setup and cleanup are API round trips on top of the UI flow, as in scenarios 1 and 2.
        test.setTimeout(60_000);
        // An asset of this test's own with one event (W-B42). The scenario used to open "the first card" of
        // the shared list through visibility probes and a text filter, and could pass asserting nothing.
        //
        // What the page does (read on 16/10): the card's trash and the row's Delete action call the same
        // handler, which opens the confirmation at once — nothing is asked of the server first. It names the
        // asset and carries a fixed warning about provider assignments and price history: nothing about
        // events, no count. Confirmed, an asset with no transaction goes with its events (asset_events has
        // ON DELETE CASCADE); one with any transaction — realising an event or not — is refused afterwards
        // (HAS_TRANSACTIONS, with the count). So no transaction here: the confirmation does not depend on one.
        const asset = await createOwnedAsset(page, owned);
        const [eventId] = await seedEvents(page, asset.id, [{date: daysAgoIso(20), type: 'DIVIDEND', amount: '0.42', notes: `e2e-asset-delete ${uniqueSuffix()}`}]);
        const before = await snapshot(page, asset.id);
        expect(Object.keys(before).map(Number), 'the asset holds the one event this test created').toEqual([eventId]);

        const assetsPage = await openAssetsList(page);
        await expect(page.getByTestId(`asset-card-${asset.id}`), 'the owned asset has its card, found by id').toBeVisible({timeout: 10_000});

        // The card's trash button has no test id (its only handle is a translated title), so the delete is
        // started from the same asset's row in the list view: the same handler, the same confirmation.
        await page.getByTestId('view-mode-list').click();
        await waitForSettled(assetsPage);
        await narrowListTo(page, assetsPage, asset);
        await page.getByTestId(`row-actions-${asset.id}`).click();
        const deleteAction = page.getByTestId('context-menu-action-delete');
        await deleteAction.click();
        await expect(deleteAction).toBeHidden();

        // The confirmation: its one parameter is the asset's name. Its words are never asserted.
        const message = page.getByTestId('confirm-modal-message');
        await expect(message, 'starting the delete asks for a confirmation').toBeVisible({timeout: 5_000});
        await expect(message, 'the confirmation names the asset it would delete').toContainText(asset.name);
        await expect(message, 'no ICU placeholder is left unresolved').not.toContainText('{');
        await expect(page.getByTestId('confirm-modal-confirm'), 'the delete is offered, not run').toBeVisible();

        // Cancelled: the confirmation closes, the asset stays listed, and nothing is deleted.
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(message, 'cancel closes the confirmation').toHaveCount(0);
        await expect(page.getByTestId(`row-actions-${asset.id}`), 'the asset is still listed').toBeVisible();
        expect(await storedAssets(page, asset.id), 'the asset is still stored').toEqual([{asset_id: asset.id, display_name: asset.name}]);
        expect(await snapshot(page, asset.id), 'its event is still stored, unchanged').toEqual(before);
    });

    // ===================================================================
    // Scenario 4: ●evt dot in the transactions table follows the link
    // ===================================================================
    test('event badge reflects current link state', async ({page}) => {
        // Setup and cleanup are API round trips on top of the UI flow, as in scenarios 1 and 2.
        test.setTimeout(60_000);
        // An asset, an event and the DIVIDEND that realises it on a broker, all of this test's own (W-B42).
        // The scenario used to take "the first dot" of the shared table: it read whichever mock transaction
        // populate_mock_data had linked, and never saw a dot go.
        const asset = await createOwnedAsset(page, owned);
        const day = daysAgoIso(21);
        const [eventId] = await seedEvents(page, asset.id, [{date: day, type: 'DIVIDEND', amount: '0.50', notes: `e2e-event-dot ${uniqueSuffix()}`}]);
        const txId = await linkDividend(page, owned, asset.id, eventId, day);

        // Verified, not inferred: the DIVIDEND realises this test's event, on the broker linkDividend created.
        const linked = await storedTransaction(page, txId);
        expect(linked.type).toBe('DIVIDEND');
        expect(linked.asset_event_id, 'the DIVIDEND realises the event this test created').toBe(eventId);
        expect(owned.brokerIds, 'the DIVIDEND sits on the broker this test created').toContain(linked.broker_id);

        // Linked: the row carries the event dot, keyed by the TRANSACTION id (TransactionsTable, links column).
        const linkedRow = await openTransactionRow(page, linked.broker_id, txId);
        await expect(linkedRow.getByTestId(`tx-event-dot-${txId}`), 'a transaction realising an event shows the dot').toBeVisible();

        // Unlinked through the API. In an update `asset_event_id: 0` unlinks, while null leaves the link as it
        // is (TXUpdateItem; the editor sends 0 too). A DIVIDEND realising no event is valid: nothing else moves.
        const unlink = await jsonFrom<{committed: boolean}>(await page.request.post(`${API_BASE}/transactions/commit`, {data: {updates: [{id: txId, asset_event_id: 0}]}}), 'unlink the DIVIDEND from its event');
        expect(unlink.committed, JSON.stringify(unlink)).toBe(true);
        expect((await storedTransaction(page, txId)).asset_event_id ?? null, 'the DIVIDEND realises no event any more').toBeNull();

        // Loaded again: the row is still there with its links cell, and the dot is gone — removed, not hidden.
        const unlinkedRow = await openTransactionRow(page, linked.broker_id, txId);
        await expect(unlinkedRow.locator('td[data-column-id="links"]'), 'the links column is drawn for this row').toHaveCount(1);
        await expect(page.getByTestId(`tx-event-dot-${txId}`), 'an unlinked transaction carries no event dot').toHaveCount(0);
        // Unlinking takes the link, not the event.
        expect(
            (await storedEvents(page, asset.id)).map((e) => e.id),
            'the event itself is still stored',
        ).toEqual([eventId]);
    });
});
