/**
 * Asset Data Editor — E2E Tests
 *
 * Tests the data editor panel in the Asset detail page:
 * - Opening the editor panel
 * - Two tabs (Prices / Events) with switching
 * - CSV import modals for both prices and events
 * - Save/Cancel bar visibility
 * - CSV import with valid/invalid data
 * - Stale rows toggle, on an asset of the test's own with a gap in its prices
 * - Event writes: a retyped event is updated in place, the events export imports
 *   back, a new row deleted before saving sends no delete
 * - What a save says (O-8): every save is published as `assets.data.saved` with its
 *   counts, a refused one as `assets.data.saveFailed` with its cause. The toast's
 *   words are translated, so a test reads the event, the toast variant and the
 *   editor's error state (`asset-editor-error`), never a message
 * - What a refused price save says (X-R46): the server's facts — the day refused,
 *   the last storable day, the currencies — never Axios's sentence; a save taken in
 *   part counts what the server kept, and is told as a warning
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with at least one asset with prices
 */

import type {Route} from '@playwright/test';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {eventSeq, waitForChart, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE, goToAssetsPage, navigateToAssetByName} from './assets-helpers';
import {createOwnedAsset, deleteOwned, type Owned} from './asset-events-owned';

test.describe('Asset Data Editor', () => {
    /** What the running test created through the API (test 21's asset); deleted after it, whatever its outcome. */
    let owned: Owned = {assetIds: [], brokerIds: []};

    test.beforeEach(async ({page}) => {
        owned = {assetIds: [], brokerIds: []};
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        // A no-op for the tests that create nothing; the asset goes with its prices.
        await deleteOwned(page, owned);
    });

    // ========================================================================
    // Helper: Navigate to Apple Inc (known to have mock price data)
    // ========================================================================
    async function goToAssetWithPrices(page: import('@playwright/test').Page) {
        await goToAssetsPage(page);
        await navigateToAssetByName(page, 'Apple');
    }

    // ========================================================================
    // Helper: Open data editor panel
    // ========================================================================
    async function openDataEditor(page: import('@playwright/test').Page) {
        await goToAssetWithPrices(page);
        // Wait for chart to render — the edit button only appears when lineData.length > 0.
        // Scoped to the asset chart on purpose: an unscoped waitForSelector('canvas')
        // would be satisfied by any canvas on the page (report 16, finding A5).
        await expectChartCanvas(page, 'asset-detail-chart', 10_000);
        await waitForChart(page, 20_000);
        // The edit data button is inside {:else if lineData.length > 0} — check it exists
        const editDataBtn = page.getByTestId('asset-detail-editdata-btn');
        await expect(editDataBtn).toBeVisible({timeout: 5_000});
        await editDataBtn.click();
        await expect(page.getByTestId('asset-detail-editor-panel')).toBeVisible();
    }

    // ========================================================================
    // Helper: Open the price CSV import modal
    // ========================================================================
    async function openPriceImportModal(page: import('@playwright/test').Page) {
        await openDataEditor(page);
        await page.getByTestId('fx-data-import-btn').click();
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        return modal;
    }

    // ========================================================================
    // Helper: Open the event CSV import modal
    // ========================================================================
    async function openEventImportModal(page: import('@playwright/test').Page) {
        await openDataEditor(page);
        await page.getByTestId('asset-editor-events-tab').click();
        await page.getByTestId('fx-data-import-btn').click();
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        return modal;
    }

    // ========================================================================
    // Helper: Get the CSV textarea content
    // ========================================================================
    async function getCsvText(modal: import('@playwright/test').Locator) {
        return modal.locator('textarea').inputValue();
    }

    // ========================================================================
    // Helper: Open the price editor of an asset of the test's own, on [start, end]
    // ========================================================================
    async function openOwnPricesEditor(page: Page, assetId: number, start: string, end: string): Promise<Locator> {
        // A full page load: the range in the URL is read once, when the app starts.
        await navigateTo(page, `/assets/${assetId}?start=${start}&end=${end}`);
        // The editor is handed the prices the page loaded: it is only as ready as the page.
        await waitForSettled(page.getByTestId('asset-detail-page'), 30_000);
        const editButton = page.getByTestId('asset-detail-editdata-btn');
        await expect(editButton).toBeVisible({timeout: 10_000});
        await editButton.click();
        const panel = page.getByTestId('asset-detail-editor-panel');
        await expect(panel).toBeVisible();
        await expect(panel.getByTestId('asset-editor-prices-tab')).toHaveAttribute('aria-selected', 'true');
        return panel;
    }

    // ========================================================================
    // Helper: The rows the price editor lists, by id (a price row is keyed by its date), sorted
    // ========================================================================
    async function priceRowIds(panel: Locator): Promise<string[]> {
        const ids = await panel.locator('tbody tr[data-row-id]').evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id') ?? ''));
        return ids.sort();
    }

    // ========================================================================
    // Helper: The names of the app events recorded after `since`, in order
    // ========================================================================
    async function eventNamesSince(page: Page, since: number): Promise<string[]> {
        // The ring of notify.svelte.ts is a state: once an event is in it, every earlier one of the same page is too.
        return page.evaluate((s) => ((window as unknown as {__lf?: {events?: Array<{seq: number; name: string}>}}).__lf?.events ?? []).filter((e) => e.seq > s).map((e) => e.name), since);
    }

    // ========================================================================
    // Test 1: Edit data button opens the editor panel
    // ========================================================================
    test('edit data button opens the editor panel', async ({page}) => {
        await openDataEditor(page);
        await expect(page.getByTestId('asset-detail-editor-panel')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Editor shows two tabs (Prices and Events)
    // ========================================================================
    test('editor shows prices and events tabs', async ({page}) => {
        await openDataEditor(page);
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        const eventsTab = page.getByTestId('asset-editor-events-tab');
        await expect(pricesTab).toBeVisible();
        await expect(eventsTab).toBeVisible();
    });

    // ========================================================================
    // Test 3: Prices tab is active by default
    // ========================================================================
    test('prices tab is active by default', async ({page}) => {
        await openDataEditor(page);
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        // The active tab is the selected one: the state TabBar publishes (aria-selected), not the colour it draws
        await expect(pricesTab).toHaveAttribute('aria-selected', 'true');
    });

    // ========================================================================
    // Test 4: Switch to events tab
    // ========================================================================
    test('switch to events tab works', async ({page}) => {
        await openDataEditor(page);
        const eventsTab = page.getByTestId('asset-editor-events-tab');
        await eventsTab.click();
        // Events tab should now be active
        await expect(eventsTab).toHaveAttribute('aria-selected', 'true');
    });

    // ========================================================================
    // Test 5: Prices tab shows DataEditor with Import CSV and Add Row
    // ========================================================================
    test('prices tab has import CSV and add row buttons', async ({page}) => {
        await openDataEditor(page);
        // Import CSV button
        const importBtn = page.getByTestId('fx-data-import-btn');
        await expect(importBtn).toBeVisible();
        // Add Row button
        const addRowBtn = page.getByTestId('fx-data-add-row-btn');
        await expect(addRowBtn).toBeVisible();
    });

    // ========================================================================
    // Test 6: Events tab also shows DataEditor with Import CSV
    // ========================================================================
    test('events tab has import CSV and add row buttons', async ({page}) => {
        await openDataEditor(page);
        // Switch to events tab
        await page.getByTestId('asset-editor-events-tab').click();
        // Import CSV button
        const importBtn = page.getByTestId('fx-data-import-btn');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 7: Import CSV opens price import modal with correct header
    // ========================================================================
    test('import CSV opens price import modal', async ({page}) => {
        const modal = await openPriceImportModal(page);
        // Header should contain 'date;currency;close'
        const csvText = await getCsvText(modal);
        expect(csvText).toContain('date;currency;close');
    });

    // ========================================================================
    // Test 8: Import CSV opens event import modal when on events tab
    // ========================================================================
    test('import CSV opens event import modal on events tab', async ({page}) => {
        const modal = await openEventImportModal(page);
        // Header should contain event-specific columns
        const csvText = await getCsvText(modal);
        expect(csvText).toContain('date;currency;type;amount');
    });

    // ========================================================================
    // Test 9: Save/Cancel bar is visible
    // ========================================================================
    test('save and cancel buttons are visible', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Save button (initially disabled since no changes)
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeVisible();
        await expect(saveBtn).toBeDisabled();
        // Cancel button
        const cancelBtn = panel.getByTestId('asset-editor-cancel-btn');
        await expect(cancelBtn).toBeVisible();
    });

    // ========================================================================
    // Test 10: Close editor via ✕ button
    // ========================================================================
    test('close button hides the editor panel', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        await expect(panel).toBeVisible();
        // Click close button
        await panel.getByTestId('asset-detail-editor-close').click();
        await expect(panel).not.toBeVisible();
    });

    // ========================================================================
    // Test 11: Add row in prices tab enables save button
    // ========================================================================
    test('add row enables save button', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Click Add Row
        await page.getByTestId('fx-data-add-row-btn').click();
        // Save button should now show dirty count
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 12: Switch tabs preserves dirty state
    // ========================================================================
    test('switching tabs preserves dirty state', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Add row in prices tab
        await page.getByTestId('fx-data-add-row-btn').click();
        // Prices tab badge should show 1 (TabBar publishes the count as data-badge)
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        await expect(pricesTab.getByTestId('tab-badge')).toHaveAttribute('data-badge', '1');
        // Switch to events tab and back
        await page.getByTestId('asset-editor-events-tab').click();
        await pricesTab.click();
        // Save button should still be enabled
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 13: Cancel resets dirty state
    // ========================================================================
    test('cancel resets dirty state and closes editor', async ({page}) => {
        await openDataEditor(page);
        const panel = page.getByTestId('asset-detail-editor-panel');
        // Add row
        await page.getByTestId('fx-data-add-row-btn').click();
        // Click cancel
        await panel.getByTestId('asset-editor-cancel-btn').click();
        // Editor should be hidden
        await expect(panel).not.toBeVisible();
    });

    // ========================================================================
    // Test 14: Price CSV import — valid data shows correct row count
    // ========================================================================
    test('price CSV import: valid data shows Import button with row count', async ({page}) => {
        const modal = await openPriceImportModal(page);

        // Type valid price CSV data (must use full header with all columns)
        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;;;;\n2020-06-11;USD;151.30;;;;\n2020-06-12;EUR;148.90;;;;');

        // The Import button counts 3 valid rows (data-valid-rows: the number its label shows, in any language)
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '3');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 15: Price CSV import — extended format with optional columns
    // ========================================================================
    test('price CSV import: extended format accepted', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;149.00;151.00;148.50;1200000');

        // Should show 1 valid row
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '1');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 16: Price CSV import — invalid data shows errors
    // ========================================================================
    test('price CSV import: invalid rows show error indicators', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        // Missing close price (required), bad date, non-numeric close
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;;;;;\nnot-a-date;USD;100;;;;\n2020-06-11;USD;abc;;;;');

        // Each of the three data lines is marked ✗ in the gutter: a glyph and a state, no words.
        // The status-bar badge carries data-state="invalid" too, so a row mark is told by its ✗.
        const rowMarks = modal.locator('[data-state="invalid"]', {hasText: '✗'});
        await expect(rowMarks).toHaveCount(3);
        for (const mark of await rowMarks.all()) await expect(mark).toBeVisible();
        // ...and the error badge is the one invalid mark without a ✗.
        await expect(modal.locator('[data-state="invalid"]', {hasNotText: '✗'})).toBeVisible();

        // None of the three rows is offered for import: the Import button counts no valid row, and is disabled.
        // The ✗ marks above are the barrier: 0 is also the count before the text is parsed.
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '0');
        await expect(importBtn).toBeDisabled();
    });

    // ========================================================================
    // Test 17: Price CSV import — importing adds rows to table
    // ========================================================================
    test('price CSV import: imported rows appear in data editor', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2019-01-15;USD;99.99;;;;\n2019-01-16;USD;100.50;;;;');

        // Click Import button, once it counts the 2 valid rows
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '2');
        await expect(importBtn).toBeVisible();
        await importBtn.click();

        // Modal should be closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled (dirty rows from import)
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeEnabled();

        // Dirty count should include imported rows: the prices tab's badge is that count (priceDirtyCount). The
        // editor opened clean, and each imported day is either appended or merged into the row of its date
        // (DataEditor.handleImport): exactly the 2 imported rows are dirty.
        await expect(panel.getByTestId('asset-editor-prices-tab').getByTestId('tab-badge')).toHaveAttribute('data-badge', '2');
    });

    // ========================================================================
    // Test 18: Event CSV import — valid data shows correct row count
    // ========================================================================
    test('event CSV import: valid data shows Import button with row count', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2020-03-15;USD;DIVIDEND;1.25;Q1 payout\n2020-06-01;;SPLIT;2;2:1 split');

        // The Import button counts 2 valid rows
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '2');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 19: Event CSV import — invalid event type shows error
    // ========================================================================
    test('event CSV import: missing required fields show errors', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        // Missing amount (required), and empty type (required)
        await textarea.fill('date;currency;type;amount;notes\n2020-03-15;USD;;1.25;test\n2020-06-01;USD;DIVIDEND;;test');

        // Error indicators should be visible
        const errorIndicators = modal.locator('[data-state="invalid"]');
        await expect(errorIndicators.first()).toBeVisible();
    });

    // ========================================================================
    // Test 20: Event CSV import — importing adds rows to events table
    // ========================================================================
    test('event CSV import: imported rows appear in events editor', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2019-12-15;USD;DIVIDEND;0.75;test dividend');

        // Click Import, once it counts the valid row
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '1');
        await expect(importBtn).toBeVisible();
        await importBtn.click();

        // Modal closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.getByTestId('asset-editor-save-btn');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 21: Stale toggle is visible when stale rows exist — and only then
    // ========================================================================
    test('stale toggle is visible in toolbar', async ({page}) => {
        // Two page loads: the range is read from the URL once, when the app starts.
        test.setTimeout(60_000);
        // An asset of this test's own, with closes on D and D+3 only. The price query answers one
        // row per calendar day of the range: a day without a close after the first one carries the
        // last close forward, with backward_fill_info.days_back = the days it reaches back, which
        // the editor reads as the row's staleDays (days before the first close are skipped). So on
        // [D, D+3] the rows are D, D+1 (1 day back), D+2 (2 days back) and D+3: two stale rows.
        // Signals may load earlier days to warm up, but the answer is sliced back to the range.
        const [d0, d1, d2, d3] = [daysAgoIso(20), daysAgoIso(19), daysAgoIso(18), daysAgoIso(17)];
        const asset = await createOwnedAsset(page, owned, {
            label: 'E2E stale rows',
            closes: [
                {date: d0, close: 10},
                {date: d3, close: 11},
            ],
        });
        // The page polls POST /assets/prices/current, which may ask live providers and write
        // today's price into the shared database. Nothing here is about live prices.
        await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));

        const panel = await openOwnPricesEditor(page, asset.id, d0, d3);
        await expect.poll(() => priceRowIds(panel), {message: 'one editor row per calendar day of [D, D+3]', timeout: 10_000}).toEqual([d0, d1, d2, d3]);
        const staleToggle = panel.getByTestId('data-editor-stale-toggle');
        await expect(staleToggle).toBeVisible();
        // The counter reads "⚠️ {staleCount}": the only number in it is the count, no words.
        await expect(staleToggle.getByTestId('data-editor-stale-count')).toHaveText(/^\D*2\D*$/);

        // The guard, same asset: on [D+3, D+3] the only row is a stored close, nothing is stale,
        // and the toggle is not drawn. Its absence is read once the editor holds its row and its
        // toolbar is drawn, so a slow editor cannot pass for one without stale rows.
        const guard = await openOwnPricesEditor(page, asset.id, d3, d3);
        await expect.poll(() => priceRowIds(guard), {message: 'the only editor row of [D+3, D+3]', timeout: 10_000}).toEqual([d3]);
        await expect(guard.getByTestId('fx-data-import-btn')).toBeVisible();
        await expect(guard.getByTestId('data-editor-stale-toggle')).toHaveCount(0);
    });

    // ========================================================================
    // Test 22: Price CSV import — partial skip with ;; for optional columns
    // ========================================================================
    test('price CSV import: partial columns with ;; accepted', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        // Use extended header but skip open,high,low with ;;
        await textarea.fill('date;currency;close;open;high;low;volume\n2020-06-10;USD;150.25;;;;1500000');

        // Should accept as 1 valid row (optional columns skipped)
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '1');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 23: Event CSV import — all event types accepted
    // ========================================================================
    test('event CSV import: all event types are valid', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n' + '2020-01-01;USD;DIVIDEND;1.00;\n' + '2020-02-01;EUR;INTEREST;0.50;\n' + '2020-03-01;;SPLIT;2;\n' + '2020-04-01;USD;PRICE_ADJUSTMENT;-5.00;\n' + '2020-05-01;USD;MATURITY_SETTLEMENT;100;final');

        // All 5 event types should be valid
        const importBtn = modal.getByTestId('data-import-confirm');
        await expect(importBtn).toHaveAttribute('data-valid-rows', '5');
        await expect(importBtn).toBeVisible();
    });

    // ========================================================================
    // Test 24: A price save the server refuses, then the retry (O-8)
    // ========================================================================
    test('a refused price save is published as a failure and keeps the edits; the retry is published with what it did', async ({page}) => {
        // One page load, two saves.
        test.setTimeout(60_000);
        // O-8. The editor wrote what a save did, and why one failed, in English whatever the
        // interface language. Both now come from the catalogue, and both are published:
        // `assets.data.saved` with the save's counts, `assets.data.saveFailed` with its cause.
        // The words are translated, so this reads the events, the toast variant and the
        // editor's error state by its handle.
        //
        // An asset of this test's own, with closes on two consecutive days: its editor lists
        // those two rows and nothing else. What the retry writes goes with the asset afterwards.
        const [d0, d1] = [daysAgoIso(20), daysAgoIso(19)];
        // The days of the two rows the test adds: one imported before the stored closes, and
        // the blank one Add Row appends on the day after the last of them.
        const [importedDay, blankDay] = [daysAgoIso(22), daysAgoIso(18)];
        const asset = await createOwnedAsset(page, owned, {
            label: 'E2E price save',
            closes: [
                {date: d0, close: 10},
                {date: d1, close: 11},
            ],
        });
        // The page polls POST /assets/prices/current, which may ask live providers and write
        // today's price into the shared database. Nothing here is about live prices.
        await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));

        const panel = await openOwnPricesEditor(page, asset.id, d0, d1);
        await expect.poll(() => priceRowIds(panel), {message: 'the two stored closes', timeout: 10_000}).toEqual([d0, d1]);

        // A price to save: a new day with a valid close, through the CSV import.
        await panel.getByTestId('fx-data-import-btn').click();
        const modal = page.getByTestId('data-import-modal');
        await expect(modal).toBeVisible();
        const csv = `date;currency;close;open;high;low;volume\n${importedDay};USD;12;;;;`;
        const input = modal.getByTestId('csv-editor-input');
        await input.fill(csv);
        await expect(input).toHaveValue(csv);
        const confirm = modal.getByTestId('data-import-confirm');
        await expect(confirm, 'the line is a valid price row').toHaveAttribute('data-valid-rows', '1');
        await confirm.click();
        await expect(modal).toBeHidden();
        // A price to delete: the first stored close.
        await panel.getByTestId(`row-actions-${d0}`).click();
        const deleteAction = page.getByTestId('context-menu-action-delete');
        await deleteAction.click();
        await expect(deleteAction).toBeHidden();
        // A price to skip: a new row left blank, without the close a price needs.
        await panel.getByTestId('fx-data-add-row-btn').click();
        await expect.poll(() => priceRowIds(panel), {message: 'the stored closes, the imported day and the blank day', timeout: 10_000}).toEqual([importedDay, d0, d1, blankDay]);

        // The server refuses the save: the upsert of the prices — POST on this exact path — is
        // answered 500 here, so nothing reaches the database. The delete shares the path, not
        // the method: it falls through, and the editor sends it only once the upsert is answered.
        const pricesPath = `${API_BASE}/assets/prices`;
        const isPricesPath = (url: URL) => url.pathname === pricesPath;
        const refuse = async (route: Route) => {
            if (route.request().method() !== 'POST') {
                await route.fallback();
                return;
            }
            await route.fulfill({status: 500, json: {detail: 'refused by the spec'}});
        };
        await page.route(isPricesPath, refuse);
        const saveButton = panel.getByTestId('asset-editor-save-btn');
        await expect(saveButton).toBeEnabled();
        const refused = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === pricesPath, {timeout: 15_000});
        const beforeFailure = await eventSeq(page);
        await saveButton.click();
        expect((await refused).status(), 'the price upsert reached the refusal').toBe(500);

        const failed = await waitForEvent(page, 'assets.data.saveFailed', {since: beforeFailure, timeout: 5_000});
        const cause = failed.detail?.error;
        expect(typeof cause === 'string' && cause.length > 0, `the failure carries its cause: ${JSON.stringify(failed.detail)}`).toBe(true);
        // The editor's error state, by its handle and by the cause it names — never by its words.
        const errorState = panel.getByTestId('asset-editor-error');
        await expect(errorState, 'the editor shows the failure').toBeVisible();
        await expect(errorState, 'naming its cause').toContainText(String(cause));
        await expect(page.getByTestId('toast-error'), 'the user is told').toBeVisible();
        expect(await eventNamesSince(page, beforeFailure), 'a refused save is not also published as saved').not.toContain('assets.data.saved');
        // Nothing is lost: the editor stays open on its edits, ready to save again.
        await expect(panel).toBeVisible();
        await expect(saveButton).toBeEnabled();

        // The retry reaches the server. Its counts prove the three edits outlived the failure.
        await page.unroute(isPricesPath, refuse);
        const beforeRetry = await eventSeq(page);
        await saveButton.click();
        // The page closes the editor only once every write has been answered.
        await expect(panel).toBeHidden({timeout: 15_000});
        const saved = await waitForEvent(page, 'assets.data.saved', {since: beforeRetry, timeout: 5_000});
        expect(saved.detail, 'the imported close saved, the first stored one deleted, the blank row skipped, none refused').toEqual({pricesSaved: 1, pricesDeleted: 1, pricesSkipped: 1, pricesRefused: 0, eventsDeleted: 0, eventsSaved: 0});
    });

    // ========================================================================
    // What a refused price save says (X-R46)
    // ========================================================================
    /**
     * X-R46, the asset side of the FX editor's defect:
     * - a price save the server refuses (a 422) put Axios's generic `e.message` — «Request
     *   failed with status code 422» — in the editor's error state and in its toast, instead of
     *   what the server answered: which day it refused, and why;
     * - a save the server takes in part (a 200 whose `results[0].rejected` lists a day) counted
     *   every row sent as saved: `results[0].count` was never read, and the success toast
     *   announced the refused day as saved.
     *
     * Each test owns an asset with two stored closes, imports its lines through the CSV modal
     * and answers the price save (POST on this exact path) at the network edge with what the
     * server answers to those prices: nothing is written, and the asset goes afterwards. The
     * answers carry the refused day only where the editor must read it (`items`, `rejected`).
     *
     * Read without words: the error state by `asset-editor-error`, a toast by its variant, the
     * save by its events; text only for ISO days, currency codes and the absence of Axios's
     * sentence, which is English whatever the interface language.
     */
    test.describe('server refusals (X-R46)', () => {
        // A red lists every missing fact at once (soft assertions, two seconds each, behind a
        // barrier): the budget is for that report — green, a test takes a fraction of it.
        test.describe.configure({timeout: 60_000});

        const PRICES_PATH = `${API_BASE}/assets/prices`;
        /** Axios's own sentence for any answer outside 2xx: English, and none of the server's facts in it. */
        const AXIOS_GENERIC = 'Request failed with status code';

        /** The prices of each asset, as the editor sends them. */
        type SentPrices = Array<{asset_id: number; prices: Array<{date: string}>}>;

        /**
         * An asset of the test's own with closes on D and D+1, its price editor open on them, and
         * `lines` (`[day, 'currency;close;open;high;low;volume']`) imported through the CSV modal.
         */
        async function editorWithImported(page: Page, label: string, lines: Array<[string, string]>): Promise<{assetId: number; panel: Locator}> {
            const [d0, d1] = [daysAgoIso(20), daysAgoIso(19)];
            const asset = await createOwnedAsset(page, owned, {
                label,
                closes: [
                    {date: d0, close: 10},
                    {date: d1, close: 11},
                ],
            });
            // The page polls POST /assets/prices/current, which may ask live providers and write
            // today's price into the shared database. Nothing here is about live prices.
            await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
            const panel = await openOwnPricesEditor(page, asset.id, d0, d1);
            await expect.poll(() => priceRowIds(panel), {message: 'the two stored closes', timeout: 10_000}).toEqual([d0, d1]);

            await panel.getByTestId('fx-data-import-btn').click();
            const modal = page.getByTestId('data-import-modal');
            await expect(modal).toBeVisible();
            const csv = ['date;currency;close;open;high;low;volume', ...lines.map(([day, rest]) => `${day};${rest}`)].join('\n');
            const input = modal.getByTestId('csv-editor-input');
            await input.fill(csv);
            await expect(input).toHaveValue(csv);
            const confirm = modal.getByTestId('data-import-confirm');
            await expect(confirm, 'every line is a valid price row').toHaveAttribute('data-valid-rows', String(lines.length));
            await confirm.click();
            await expect(modal).toBeHidden();
            await expect.poll(() => priceRowIds(panel), {message: 'the stored closes and the imported days', timeout: 10_000}).toEqual([d0, d1, ...lines.map(([day]) => day)].sort());
            return {assetId: asset.id, panel};
        }

        /**
         * Answer every price save (POST on this exact path) of the page with `answer(sent)` — the
         * server's answer to the prices sent — and keep what each save sent. No save reaches the
         * server; the delete, which shares the path, and every other request do.
         */
        async function answerSaves(page: Page, answer: (sent: SentPrices) => {status: number; json: unknown}): Promise<SentPrices[]> {
            const saves: SentPrices[] = [];
            const isPricesPath = (url: URL) => url.pathname === PRICES_PATH;
            await page.route(isPricesPath, async (route: Route) => {
                if (route.request().method() !== 'POST') {
                    await route.fallback();
                    return;
                }
                const sent = route.request().postDataJSON() as SentPrices;
                saves.push(sent);
                await route.fulfill(answer(sent));
            });
            return saves;
        }

        /** What each save sent: per asset, its days, sorted. */
        function sentPrices(saves: SentPrices[]): Array<Array<{asset_id: number; dates: string[]}>> {
            return saves.map((sent) => sent.map((item) => ({asset_id: item.asset_id, dates: item.prices.map((price) => price.date).sort()})));
        }

        /** Click Save; return the status of the answer once the save has been answered, and the event counter read before the click. */
        async function save(page: Page, panel: Locator): Promise<{status: number; since: number}> {
            const saveButton = panel.getByTestId('asset-editor-save-btn');
            await expect(saveButton).toBeEnabled();
            const answered = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === PRICES_PATH, {timeout: 15_000});
            const since = await eventSeq(page);
            await saveButton.click();
            return {status: (await answered).status(), since};
        }

        /**
         * `told` — a toast, or the error state — is shown, holds every one of `facts` and not
         * Axios's sentence. Soft, so a red lists every missing fact; the wait is short, the text
         * being final once `told` is shown.
         */
        async function expectTold(told: Locator, what: string, facts: string[]): Promise<void> {
            await expect(told, `${what} is shown`).toBeVisible();
            for (const fact of facts) await expect.soft(told, `${what} holds ${fact}`).toContainText(fact, {timeout: 2_000});
            await expect.soft(told, `${what} says what the server said, not Axios's sentence`).not.toContainText(AXIOS_GENERIC, {timeout: 2_000});
        }

        test("a price dated after the last storable day is told refused with that day and the last storable day, not with Axios's sentence", async ({page}) => {
            // Pins: a 422 `date_out_of_range` is told, by the error state and by the error toast,
            // with the day refused and the last storable day the server gave (`params.max`), in
            // ISO; the save is published as a failure alone, and the editor stays open on the
            // price, ready to be corrected.
            // Red on HEAD (X-R46): the error state and the toast read «… Request failed with status code 422».
            // Red until N83's revision (19/10) reaches `writeRefusal.ts`: it reads no
            // `date_out_of_range` detail without `params.min`, so the error state and the toast
            // fall back to the server's message, which names the last storable day and not the day
            // refused.
            const refused = daysAgoIso(-30);
            const max = daysAgoIso(-1);
            const {assetId, panel} = await editorWithImported(page, 'E2E price out of range', [[refused, 'USD;12;;;;']]);
            // The server's answer to a day after tomorrow (X-R65): the whole save refused. A stored
            // price has no first day since N83's revision, so `params` holds the last storable day
            // alone, tomorrow, and the day refused lies after it. The message says that last day,
            // never the day refused — that is in `items`.
            const saves = await answerSaves(page, () => ({
                status: 422,
                json: {detail: {code: 'date_out_of_range', message: `Dates must lie on or before ${max}: 1 does not`, params: {max}, items: [{asset_id: assetId, dates: [refused]}], count: 1}},
            }));

            const {status, since} = await save(page, panel);
            expect(status, 'the save reached the refusal').toBe(422);
            expect(sentPrices(saves), 'one save, of the imported price alone').toEqual([[{asset_id: assetId, dates: [refused]}]]);

            // The barrier: the failure is published in the step that sets the error state and raises the toast.
            await waitForEvent(page, 'assets.data.saveFailed', {since, timeout: 5_000});
            await expectTold(panel.getByTestId('asset-editor-error'), 'the error state', [refused, max]);
            await expectTold(page.getByTestId('toast-error'), 'the error toast', [refused, max]);
            expect(await eventNamesSince(page, since), 'a refused save is not also published as saved').not.toContain('assets.data.saved');
            // Nothing is lost: the editor stays open on the imported price, ready to save again.
            await expect(panel).toBeVisible();
            await expect(panel.getByTestId('asset-editor-save-btn')).toBeEnabled();
        });

        test("a price in a currency other than the asset's is told refused with the day and both currencies, not with Axios's sentence", async ({page}) => {
            // Pins: a 422 `price_currency_mismatch` is told by the error state with the day refused,
            // the asset's currency and the one found, as ISO codes, and by the toast without
            // Axios's sentence; the editor stays open.
            // Red on HEAD: the error state and the toast read «… Request failed with status code 422».
            const refused = daysAgoIso(22);
            // A line written in EUR, for an asset in USD: the server refuses the whole save (X-R71).
            const {assetId, panel} = await editorWithImported(page, 'E2E price currency', [[refused, 'EUR;12;;;;']]);
            // The server's message names neither the day nor a currency: they are in `items`.
            const saves = await answerSaves(page, () => ({
                status: 422,
                json: {detail: {code: 'price_currency_mismatch', message: "Prices must be in their asset's currency: 1 are not", items: [{asset_id: assetId, expected: 'USD', found: ['EUR'], dates: [refused]}], count: 1}},
            }));

            const {status, since} = await save(page, panel);
            expect(status, 'the save reached the refusal').toBe(422);
            expect(sentPrices(saves), 'one save, of the imported price alone').toEqual([[{asset_id: assetId, dates: [refused]}]]);

            await waitForEvent(page, 'assets.data.saveFailed', {since, timeout: 5_000});
            await expectTold(panel.getByTestId('asset-editor-error'), 'the error state', [refused, 'USD', 'EUR']);
            await expectTold(page.getByTestId('toast-error'), 'the error toast', []);
            await expect(panel).toBeVisible();
        });

        test('a save the server takes in part counts only the prices it kept, and is told as a warning naming the refused day', async ({page}) => {
            // Pins: a 200 whose `results[0].rejected` lists a day is no full success:
            // `assets.data.saved` counts the `results[0].count` prices the server kept, and the
            // toast is a warning naming the day refused, in ISO.
            // Red on HEAD: `results[0].count` is never read — both prices are counted as saved —
            // and the toast is a success, announcing the refused day as saved.
            const [kept, refused] = [daysAgoIso(22), daysAgoIso(21)];
            // The second line closes above its high: the server keeps the first and refuses the second.
            const {assetId, panel} = await editorWithImported(page, 'E2E price partial', [
                [kept, 'USD;12;;;;'],
                [refused, 'USD;13;;12;11;'],
            ]);
            // The server's message lists the day too; this one stops short of it, or a toast
            // echoing the message would pass for one built from `rejected`.
            const saves = await answerSaves(page, () => ({
                status: 200,
                json: {
                    results: [{asset_id: assetId, count: 1, message: 'Upserted 1 prices; rejected 1 date(s) with impossible OHLC (close outside [low, high])', rejected: [{date: refused, reason: 'ohlc_inconsistent'}]}],
                    success_count: 1,
                    errors: [],
                    inserted_count: 1,
                    updated_count: 0,
                },
            }));

            const {status, since} = await save(page, panel);
            expect(status, 'the save was answered').toBe(200);
            expect(sentPrices(saves), 'one save, of the two imported prices').toEqual([[{asset_id: assetId, dates: [kept, refused].sort()}]]);

            // The barrier: the save is published in the step that raises its toast.
            const saved = await waitForEvent(page, 'assets.data.saved', {since, timeout: 5_000});
            expect.soft(saved.detail?.pricesSaved, `the prices counted as saved are those the server kept: ${JSON.stringify(saved.detail)}`).toBe(1);
            const toast = page.getByTestId(/^toast-(success|warning|error|info)$/);
            await expect(toast, 'the save is told').toBeVisible();
            await expect.soft(toast, 'as a warning, not as a success: one of the two days was refused').toHaveAttribute('data-testid', 'toast-warning', {timeout: 2_000});
            await expect.soft(toast, `naming the day refused, ${refused}`).toContainText(refused, {timeout: 2_000});
        });
    });

    // ========================================================================
    // Event writes — each test owns the events it writes and deletes them by id
    // ========================================================================
    test.describe('event writes', () => {
        const EVENTS_URL = `${API_BASE}/assets/events`;

        interface StoredEvent {
            id: number;
            type: string;
            notes: string | null;
        }

        test.beforeEach(async ({page}) => {
            // The detail page polls POST /assets/prices/current, which asks the live
            // providers and writes today's price into the shared database. Nothing here
            // is about live prices, so it is answered locally instead.
            await page.route('**/api/v1/assets/prices/current*', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
        });

        /** Apple's id, looked up by exact name: these tests need it before they navigate. */
        async function appleAssetId(page: Page): Promise<number> {
            const resp = await page.request.get(`${API_BASE}/assets/query?search=${encodeURIComponent('Apple Inc.')}`);
            expect(resp.ok(), `asset lookup failed: HTTP ${resp.status()}`).toBeTruthy();
            const apple = ((await resp.json()) as Array<{id: number; display_name: string}>).filter((a) => a.display_name === 'Apple Inc.');
            expect(apple, 'exactly one seeded "Apple Inc." is expected').toHaveLength(1);
            return apple[0].id;
        }

        /** The events on `date` that carry `marker`: ours, whatever else shares that date. */
        async function markerEvents(page: Page, assetId: number, date: string, marker: string): Promise<StoredEvent[]> {
            const resp = await page.request.post(`${EVENTS_URL}/query`, {data: [{asset_id: assetId, date_range: {start: date, end: date}}]});
            // A plain error rather than an assertion: this also runs from `finally`.
            if (!resp.ok()) throw new Error(`event query failed: HTTP ${resp.status()}`);
            const body = (await resp.json()) as {items?: Array<{asset_id: number; events?: StoredEvent[]}>};
            const item = (body.items ?? []).find((i) => i.asset_id === assetId);
            return (item?.events ?? []).filter((e) => e.notes === marker);
        }

        /** Create a manual DIVIDEND that carries `marker` and return its id. */
        async function createMarkerEvent(page: Page, assetId: number, date: string, marker: string): Promise<number> {
            const resp = await page.request.post(EVENTS_URL, {
                data: [{asset_id: assetId, events: [{date, type: 'DIVIDEND', value: {amount: 0.42, code: 'USD'}, notes: marker}]}],
            });
            expect(resp.ok(), `creating the marker event failed: HTTP ${resp.status()}`).toBeTruthy();
            const mine = await markerEvents(page, assetId, date, marker);
            expect(mine, `exactly one event must carry ${marker}`).toHaveLength(1);
            return mine[0].id;
        }

        /** Delete every event this test may have left behind, by id, on its asset (the delete is scoped by asset: decision 21). Never throws. */
        async function cleanUp(page: Page, assetId: number, date: string, marker: string, knownIds: number[]): Promise<void> {
            const found = await markerEvents(page, assetId, date, marker).catch((): StoredEvent[] => []);
            const ids = [...new Set([...knownIds, ...found.map((e) => e.id)])];
            if (ids.length === 0) return;
            await page.request.delete(`${EVENTS_URL}?asset_id=${assetId}&${ids.map((id) => `ids=${id}`).join('&')}`).catch(() => undefined);
        }

        /** Open the editor of the asset page already loaded, on its Events tab. */
        async function openEventsEditor(page: Page) {
            // The editor is handed the events the page loaded: it is only as ready as the page.
            await waitForSettled(page.getByTestId('asset-detail-page'), 30_000);
            const editButton = page.getByTestId('asset-detail-editdata-btn');
            await expect(editButton).toBeVisible({timeout: 10_000});
            await editButton.click();
            const panel = page.getByTestId('asset-detail-editor-panel');
            await expect(panel).toBeVisible();
            const eventsTab = panel.getByTestId('asset-editor-events-tab');
            await eventsTab.click();
            await expect(eventsTab).toHaveAttribute('aria-selected', 'true');
            return panel;
        }

        test('changing the type of a saved event updates that event instead of adding another', async ({page}) => {
            // F1. Save used to send rows without their id, and the endpoint upserts on
            // (date, type): retyping an event inserted a second one beside the original.
            const assetId = await appleAssetId(page);
            // Outside the default 3M window on purpose: asset-event-delete marks every
            // event inside it for deletion. The page is opened on a range that holds it.
            const date = daysAgoIso(128);
            const marker = `e2e-event-retype-${uniqueSuffix()}`;
            let eventId: number | undefined;
            try {
                eventId = await createMarkerEvent(page, assetId, date, marker);
                // A full page load: the range in the URL is read once, when the app starts.
                await navigateTo(page, `/assets/${assetId}?start=${daysAgoIso(140)}&end=${todayIso()}`);
                const panel = await openEventsEditor(page);

                const row = panel.locator(`tbody tr[data-row-id="${eventId}"]`);
                await expect(row, 'the event this test created must be listed').toBeVisible({timeout: 15_000});
                const saveButton = panel.getByTestId('asset-editor-save-btn');
                await expect(saveButton).toBeDisabled();

                // The Type cell is the row's only select; its options carry the event type in
                // their id, which does not depend on the UI language.
                const typeSelect = row.getByRole('combobox');
                const listboxId = await typeSelect.getAttribute('aria-controls');
                expect(listboxId, 'the type select names its listbox').toBeTruthy();
                await typeSelect.click();
                const listbox = page.locator(`[id="${listboxId}"]`);
                await expect(listbox).toBeVisible();
                await listbox.locator(`[role="option"][id="${listboxId}-option-INTEREST"]`).click();
                await expect(listbox).toBeHidden();
                await expect(saveButton).toBeEnabled();

                const upsert = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === EVENTS_URL, {timeout: 15_000});
                const beforeSave = await eventSeq(page);
                await saveButton.click();
                expect((await upsert).status(), 'the events upsert must succeed').toBe(200);
                // The page closes the editor only once every write has been answered.
                await expect(panel).toBeHidden({timeout: 15_000});
                // O-8: the save is published with what it did, in counts — the toast's words are
                // translated, never read. Having something to report, it tells the user too.
                const saved = await waitForEvent(page, 'assets.data.saved', {since: beforeSave, timeout: 5_000});
                expect(saved.detail, 'one event saved, nothing else').toEqual({pricesSaved: 0, pricesDeleted: 0, pricesSkipped: 0, pricesRefused: 0, eventsDeleted: 0, eventsSaved: 1});
                await expect(page.getByTestId('toast-success'), 'a save with something to report is told').toBeVisible();

                const stored = (await markerEvents(page, assetId, date, marker)).map(({id, type}) => ({id, type})).sort((a, b) => a.id - b.id);
                expect(stored, 'the same event, now INTEREST, and no second one').toEqual([{id: eventId, type: 'INTEREST'}]);
            } finally {
                await cleanUp(page, assetId, date, marker, eventId === undefined ? [] : [eventId]);
            }
        });

        test('a file written by the events export imports back into the events editor', async ({page}) => {
            // F3. The export names the amount column `value`, which the import modal did
            // not know: a file LibreFolio had just written was rejected on its header.
            const assetId = await appleAssetId(page);
            // Outside the default 3M window, for the same reason as above.
            const date = daysAgoIso(143);
            const marker = `e2e-event-roundtrip-${uniqueSuffix()}`;
            let eventId: number | undefined;
            try {
                eventId = await createMarkerEvent(page, assetId, date, marker);

                const exported = await page.request.get(`${API_BASE}/backup/asset/${assetId}/events?format=csv`);
                expect(exported.ok(), `events export failed: HTTP ${exported.status()}`).toBeTruthy();
                const [header, ...records] = (await exported.text()).split(/\r?\n/);
                expect(header, 'the header the export writes').toMatch(/^date;type;value;/);
                // Only our own line: the asset's other events belong to the fixture and to
                // concurrent specs, and the import refuses two lines on one date.
                const ours = records.filter((line) => line.includes(marker));
                expect(ours, `exactly one exported line must carry ${marker}`).toHaveLength(1);
                const csv = `${header}\n${ours[0]}`;

                await navigateTo(page, `/assets/${assetId}`);
                const panel = await openEventsEditor(page);
                await panel.getByTestId('fx-data-import-btn').click();
                const modal = page.getByTestId('data-import-modal');
                await expect(modal).toBeVisible();

                const input = modal.getByTestId('csv-editor-input');
                await input.fill(csv);
                await expect(input).toHaveValue(csv);

                const confirm = modal.getByTestId('data-import-confirm');
                await expect(confirm, 'the exported line must be a valid import row').toHaveAttribute('data-valid-rows', '1');
                await expect(confirm).toHaveAttribute('data-error-count', '0');
                await expect(confirm).toBeEnabled();

                // Leave without importing anything: Escape asks to discard the typed text,
                // then the editor is closed unsaved.
                await input.press('Escape');
                await page.getByTestId('confirm-modal-confirm').click();
                await expect(modal).toBeHidden();
                await panel.getByTestId('asset-editor-cancel-btn').click();
                await expect(panel).toBeHidden();
            } finally {
                await cleanUp(page, assetId, date, marker, eventId === undefined ? [] : [eventId]);
            }
        });

        test('a new event row deleted before saving sends no delete to the server', async ({page}) => {
            // S1. A new row deleted before it was ever saved stayed dirty, and Save read
            // its rowId — the row's date — as an event id: "2026-09-20" became
            // DELETE /assets/events?ids=2026, on an endpoint then not scoped by asset. Since
            // decision 21 (I-12a) it is, so the same bug would hit this asset's event 2026.
            const assetId = await appleAssetId(page);
            await navigateTo(page, `/assets/${assetId}`);
            const panel = await openEventsEditor(page);

            // Until it is saved a new row is keyed by its date; saved rows by their id.
            const newRowIds = () => panel.locator('tbody tr[data-row-id]').evaluateAll((rows) => rows.map((r) => r.getAttribute('data-row-id') ?? '').filter((id) => /^\d{4}-\d{2}-\d{2}/.test(id)));
            const addRow = panel.getByTestId('fx-data-add-row-btn');
            await addRow.click();
            await expect.poll(newRowIds).toHaveLength(1);
            const [keptId] = await newRowIds();
            await addRow.click();
            await expect.poll(newRowIds).toHaveLength(2);
            const deletedId = (await newRowIds()).find((id) => id !== keptId);
            expect(deletedId, 'the second new row has an id of its own').toBeTruthy();

            await panel.getByTestId(`row-actions-${deletedId}`).click();
            const deleteAction = page.getByTestId('context-menu-action-delete');
            await deleteAction.click();
            await expect(deleteAction).toBeHidden();

            // Every write the page sends from here on is recorded, and none that could delete
            // reaches the backend: unfixed, it would delete this asset's event whose id is the
            // year, if it has one. A DELETE is answered here. Since E1b a save deletes through
            // the POST's `delete_ids` (no DELETE at all): a POST carrying any is answered here
            // too, writing nothing. Every other request falls through to the routes and network.
            const deletes: string[] = [];
            const sentDeleteIds: number[] = [];
            const isApi = (url: URL) => url.pathname.startsWith(`${API_BASE}/`);
            const handler = async (route: Route) => {
                const request = route.request();
                if (request.method() === 'DELETE') {
                    deletes.push(request.url());
                    await route.fulfill({status: 200, json: {results: [], deleted_count: 0, not_found_count: 0, in_use_count: 0}});
                    return;
                }
                if (request.method() === 'POST' && new URL(request.url()).pathname === EVENTS_URL) {
                    const ids = (request.postDataJSON() as Array<{delete_ids?: number[]}>).flatMap((item) => item.delete_ids ?? []);
                    if (ids.length > 0) {
                        sentDeleteIds.push(...ids);
                        await route.fulfill({status: 200, json: {results: [{asset_id: assetId, count: 0, message: 'answered by the spec', event_ids: [], deleted_ids: []}], success_count: 0}});
                        return;
                    }
                }
                await route.fallback();
            };
            await page.route(isApi, handler);
            try {
                // The kept new row is blank: it keeps Save available however the deleted
                // row is handled, and Save skips it instead of writing it. Since E1b an item
                // with neither events nor deletions is a 422: with nothing to write the save
                // must send no item at all, or the editor stays open below.
                const saveButton = panel.getByTestId('asset-editor-save-btn');
                await expect(saveButton).toBeEnabled();
                const beforeSave = await eventSeq(page);
                await saveButton.click();
                // The page closes the editor only once every write has been answered.
                await expect(panel).toBeHidden({timeout: 15_000});
                expect(deletes, 'a row that was never saved must not reach the server').toEqual([]);
                expect(sentDeleteIds, 'nor travel in a save as an id taken from its date (the year)').toEqual([]);
                // O-8: a save with nothing to report is published all the same, every count zero —
                // the blank row is no event, the deleted one was never saved — and raises no toast.
                // The event is the barrier: once it is recorded, the toast has been decided.
                const saved = await waitForEvent(page, 'assets.data.saved', {since: beforeSave, timeout: 5_000});
                expect(saved.detail, 'nothing saved, deleted, skipped or refused').toEqual({pricesSaved: 0, pricesDeleted: 0, pricesSkipped: 0, pricesRefused: 0, eventsDeleted: 0, eventsSaved: 0});
                await expect(page.getByTestId('toast-success'), 'nothing to report: no success toast').toHaveCount(0);
            } finally {
                await page.unroute(isApi, handler);
            }
        });
    });
});
