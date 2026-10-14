/**
 * Asset Data Editor — E2E Tests
 *
 * Tests the data editor panel in the Asset detail page:
 * - Opening the editor panel
 * - Two tabs (Prices / Events) with switching
 * - CSV import modals for both prices and events
 * - Save/Cancel bar visibility
 * - CSV import with valid/invalid data
 * - Stale rows toggle
 * - Event writes: a retyped event is updated in place, the events export imports
 *   back, a new row deleted before saving sends no delete
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated with at least one asset with prices
 */

import type {Route} from '@playwright/test';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {expectChartCanvas} from '../fixtures/charts';
import {TEST_USER} from '../fixtures/test-users';
import {waitForChart, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE, goToAssetsPage, navigateToAssetByName} from './assets-helpers';

test.describe('Asset Data Editor', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
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
        // Active tab has border-libre-green class (check for text color)
        await expect(pricesTab).toHaveClass(/text-libre-green|text-emerald/);
    });

    // ========================================================================
    // Test 4: Switch to events tab
    // ========================================================================
    test('switch to events tab works', async ({page}) => {
        await openDataEditor(page);
        const eventsTab = page.getByTestId('asset-editor-events-tab');
        await eventsTab.click();
        // Events tab should now be active
        await expect(eventsTab).toHaveClass(/text-libre-green|text-emerald/);
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
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeVisible();
        await expect(saveBtn).toBeDisabled();
        // Cancel button
        const cancelBtn = panel.locator('button:has-text("Cancel")');
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
        await panel.locator('button:has-text("✕")').click();
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
        const saveBtn = panel.locator('button:has-text("Save")');
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
        // Prices tab badge should show 1
        const pricesTab = page.getByTestId('asset-editor-prices-tab');
        await expect(pricesTab.locator('span.rounded-full')).toHaveText('1');
        // Switch to events tab and back
        await page.getByTestId('asset-editor-events-tab').click();
        await pricesTab.click();
        // Save button should still be enabled
        const saveBtn = panel.locator('button:has-text("Save")');
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
        await panel.locator('button:has-text("Cancel")').click();
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

        // Import button should show "Import (3)" for 3 valid rows
        const importBtn = modal.locator('button', {hasText: /Import \(3\)/});
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
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
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

        // Error indicators (✗) should be visible
        const errorIndicators = modal.locator('.text-red-500');
        await expect(errorIndicators.first()).toBeVisible();

        // Import button should NOT show 3 valid rows (some are invalid)
        const importBtnAll = modal.locator('button', {hasText: /Import \(3\)/});
        await expect(importBtnAll).not.toBeVisible();
    });

    // ========================================================================
    // Test 17: Price CSV import — importing adds rows to table
    // ========================================================================
    test('price CSV import: imported rows appear in data editor', async ({page}) => {
        const modal = await openPriceImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;close;open;high;low;volume\n2019-01-15;USD;99.99;;;;\n2019-01-16;USD;100.50;;;;');

        // Click Import button
        const importBtn = modal.locator('button', {hasText: /Import \(2\)/});
        await expect(importBtn).toBeVisible();
        await importBtn.click();

        // Modal should be closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled (dirty rows from import)
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();

        // Dirty count should include imported rows
        await expect(saveBtn).toHaveText(/Save \(\d+\)/);
    });

    // ========================================================================
    // Test 18: Event CSV import — valid data shows correct row count
    // ========================================================================
    test('event CSV import: valid data shows Import button with row count', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2020-03-15;USD;DIVIDEND;1.25;Q1 payout\n2020-06-01;;SPLIT;2;2:1 split');

        // Import button should show "Import (2)" for 2 valid rows
        const importBtn = modal.locator('button', {hasText: /Import \(2\)/});
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
        const errorIndicators = modal.locator('.text-red-500');
        await expect(errorIndicators.first()).toBeVisible();
    });

    // ========================================================================
    // Test 20: Event CSV import — importing adds rows to events table
    // ========================================================================
    test('event CSV import: imported rows appear in events editor', async ({page}) => {
        const modal = await openEventImportModal(page);

        const textarea = modal.locator('textarea');
        await textarea.fill('date;currency;type;amount;notes\n2019-12-15;USD;DIVIDEND;0.75;test dividend');

        // Click Import
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
        await expect(importBtn).toBeVisible();
        await importBtn.click();

        // Modal closed
        await expect(modal).not.toBeVisible();

        // Save button should be enabled
        const panel = page.getByTestId('asset-detail-editor-panel');
        const saveBtn = panel.locator('button:has-text("Save")');
        await expect(saveBtn).toBeEnabled();
    });

    // ========================================================================
    // Test 21: Stale toggle is visible when stale rows exist
    // ========================================================================
    test('stale toggle is visible in toolbar', async ({page}) => {
        await openDataEditor(page);
        // The stale toggle (switch) should be visible if there are stale rows
        const staleToggle = page.getByTestId('data-editor-stale-toggle');
        // It may or may not be visible depending on data — check it doesn't crash
        if (await staleToggle.isVisible({timeout: 3000}).catch(() => false)) {
            await expect(staleToggle).toBeVisible();
            // Toggle should contain the amber counter
            const counter = staleToggle.locator('span.text-amber-600, span.text-amber-400');
            await expect(counter.first()).toBeVisible();
        }
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
        const importBtn = modal.locator('button', {hasText: /Import \(1\)/});
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
        const importBtn = modal.locator('button', {hasText: /Import \(5\)/});
        await expect(importBtn).toBeVisible();
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
            await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
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

        /** Delete every event this test may have left behind, by id. Never throws. */
        async function cleanUp(page: Page, assetId: number, date: string, marker: string, knownIds: number[]): Promise<void> {
            const found = await markerEvents(page, assetId, date, marker).catch((): StoredEvent[] => []);
            const ids = [...new Set([...knownIds, ...found.map((e) => e.id)])];
            if (ids.length === 0) return;
            await page.request.delete(`${EVENTS_URL}?${ids.map((id) => `ids=${id}`).join('&')}`).catch(() => undefined);
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
                await saveButton.click();
                expect((await upsert).status(), 'the events upsert must succeed').toBe(200);
                // The page closes the editor only once every write has been answered.
                await expect(panel).toBeHidden({timeout: 15_000});

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
            // DELETE /assets/events?ids=2026, on an endpoint not scoped by asset.
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

            // Every DELETE the page sends from here on is recorded and answered here, never
            // by the backend: unfixed, it would delete whichever event has the year as its
            // id. Every other request falls through to the routes and network as before.
            const deletes: string[] = [];
            const isApi = (url: URL) => url.pathname.startsWith(`${API_BASE}/`);
            const handler = async (route: Route) => {
                if (route.request().method() === 'DELETE') {
                    deletes.push(route.request().url());
                    await route.fulfill({status: 200, json: {results: [], deleted_count: 0, not_found_count: 0, in_use_count: 0}});
                } else {
                    await route.fallback();
                }
            };
            await page.route(isApi, handler);
            try {
                // The kept new row is blank: it keeps Save available however the deleted
                // row is handled, and Save skips it instead of writing it.
                const saveButton = panel.getByTestId('asset-editor-save-btn');
                await expect(saveButton).toBeEnabled();
                await saveButton.click();
                // The page closes the editor only once every write has been answered.
                await expect(panel).toBeHidden({timeout: 15_000});
                expect(deletes, 'a row that was never saved must not reach the server').toEqual([]);
            } finally {
                await page.unroute(isApi, handler);
            }
        });
    });
});
