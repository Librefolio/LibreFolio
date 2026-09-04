/**
 * Asset List Page — E2E Tests
 *
 * Tests the Assets list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToAssetsPage} from './assets-helpers';
import {uniqueToken} from '../fixtures/unique';

test.describe('Asset List Page', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Navigation to Assets page
    // ========================================================================
    test('can navigate to Assets page', async ({page}) => {
        await goToAssetsPage(page);
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 2: Asset cards or table are visible
    // ========================================================================
    test('asset cards or table are visible with mock data', async ({page}) => {
        await goToAssetsPage(page);
        // Wait for either card grid or table view
        const cards = page.locator('[data-testid^="asset-card-"]');
        const table = page.locator('[data-testid="assets-table"]');
        const cardCount = await cards.count();
        const tableVisible = await table.isVisible().catch(() => false);
        expect(cardCount > 0 || tableVisible).toBeTruthy();
    });

    // ========================================================================
    // Test 3: Count badge is visible
    // ========================================================================
    test('count badge shows asset count', async ({page}) => {
        await goToAssetsPage(page);
        const badge = page.getByTestId('assets-count-badge');
        await expect(badge).toBeVisible();
        const text = await badge.textContent();
        expect(parseInt(text || '0')).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 4: Search narrows the grid to matching assets (positive filter).
    //
    // Was: fill "Apple", then assert only that `assets-page` is still visible —
    // i.e. it never checked that filtering happened at all. It now asserts the
    // matching card survives and the grid actually shrinks. The negative case
    // (a query that matches nothing) is covered separately below.
    // ========================================================================
    test('search filter narrows the grid to matching assets', async ({page}) => {
        await goToAssetsPage(page);
        const cards = page.locator('[data-testid^="asset-card-"]');
        const totalBefore = await cards.count();
        expect(totalBefore, 'mock data must have assets to filter').toBeGreaterThan(0);

        const searchInput = page.getByTestId('assets-search-input');
        await expect(searchInput).toBeVisible();
        await searchInput.fill('Apple');
        // The list republishes data-busy while it refilters (debounced); wait on
        // that instead of a fixed pause.
        await waitForSettled(page.getByTestId('assets-page'), 20_000);

        // The seeded Apple card (identified by content, not position) survives...
        await expect(cards.filter({hasText: /Apple/i}).first()).toBeVisible();
        // ...and the grid is strictly smaller — the mock always has non-Apple
        // assets, and a filter can never grow the set.
        await expect.poll(() => cards.count(), {timeout: 5_000}).toBeLessThan(totalBefore);
    });

    // ========================================================================
    // Test 5: Type filter dropdown visible
    // ========================================================================
    test('type filter dropdown is visible', async ({page}) => {
        await goToAssetsPage(page);
        const typeFilter = page.getByTestId('assets-type-filter');
        await expect(typeFilter).toBeVisible();
    });

    // ========================================================================
    // Test 6: The view-mode toggle switches between the card grid and the data
    // table. Written to make no assumption about the initial view (localStorage
    // may remember it): it drives list → grid and asserts each end state.
    //
    // Was: click `assets-active-toggle` then assert only that the page is still
    // visible — no effect verified. The active/all toggle's real effect (the
    // badge count and its aria-pressed state) is covered by the dedicated test
    // further down, so this slot now covers the previously-untested list view.
    // ========================================================================
    test('view-mode toggle switches between card grid and data table', async ({page}) => {
        await goToAssetsPage(page);

        // → List view: the three usage-panel tables render (F15 round-2: one
        // DataTable per panel — own/others/analysis), each with its own select-all,
        // and the cards disappear. Scoping matters: `dt-select-all` exists once PER
        // PANEL, so a bare getByTestId is a strict-mode violation waiting to happen.
        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        for (const panelId of ['own', 'others', 'analysis'] as const) {
            const panel = page.getByTestId(`assets-table-panel-${panelId}`);
            await expect(panel, `panel ${panelId} must render in list mode (mock data puts assets in each — see populate_mock_data.py)`).toBeVisible();
            await expect(panel.getByTestId('dt-select-all')).toBeVisible();
        }
        await expect(page.locator('[data-testid^="asset-card-"]')).toHaveCount(0);

        // → Grid view: the seeded Apple card is back and the table controls are gone.
        await page.getByTestId('view-mode-grid').click();
        await expect(page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first()).toBeVisible();
        await expect(page.locator('[data-testid="dt-select-all"]')).toHaveCount(0);
    });

    // ========================================================================
    // Test 7: Add button is visible
    // ========================================================================
    test('add asset button is visible', async ({page}) => {
        await goToAssetsPage(page);
        const addBtn = page.getByTestId('assets-add-button');
        await expect(addBtn).toBeVisible();
    });

    // ========================================================================
    // Test 8: Clicking an asset card navigates to its detail page.
    //
    // Was: `firstCard = ...first(); if (firstCard.isVisible().catch(()=>false))
    // { click; assert }`. Two defects in three lines — an unfiltered `.first()`
    // (whichever card a neighbour worker inserted ahead) and a silent guard that
    // let the whole assertion be skipped if that card was merely slow. Now it
    // targets the seeded Apple card by content and navigates unconditionally.
    // ========================================================================
    test('clicking an asset card navigates to its detail page', async ({page}) => {
        await goToAssetsPage(page);
        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first();
        await expect(appleCard).toBeVisible({timeout: 10_000});
        await appleCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});
        await expect(page.getByTestId('asset-detail-header')).toBeVisible();
    });

    // ========================================================================
    // Test 9: Date range picker visible
    // ========================================================================
    test('date range picker is visible', async ({page}) => {
        await goToAssetsPage(page);
        const dateRange = page.getByTestId('assets-date-range');
        await expect(dateRange).toBeVisible();
    });

    // ========================================================================
    // Test 10: The chosen view mode persists across a reload. ViewModeToggle
    // writes `assetsViewMode` to per-user localStorage and restores it in a
    // mount `$effect` — a branch no test covered.
    //
    // Was: a loose "grid/table toggle" test that clicked buttons located by
    // aria-label and asserted a disjunction (`tableVisible || cards===0 ||
    // cards!==before`) that is true for almost any outcome, with a silent
    // `.isVisible().catch(()=>false)`. The plain grid↔list switch is now covered
    // deterministically by the view-mode toggle test above, so this slot takes
    // the persistence path instead.
    // ========================================================================
    test('selected view mode persists across a reload', async ({page}) => {
        await goToAssetsPage(page);

        // Switch to the table view and confirm it took effect. The list view is
        // three per-panel tables (F15 round-2), so the check is scoped to one
        // panel — a bare `dt-select-all` matches all three.
        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        await expect(page.getByTestId('assets-table-panel-own').getByTestId('dt-select-all')).toBeVisible();

        // Reload: the mount effect must restore list view from localStorage.
        await page.reload();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        await expect(page.getByTestId('assets-table-panel-own').getByTestId('dt-select-all')).toBeVisible();
        await expect(page.locator('[data-testid^="asset-card-"]')).toHaveCount(0);
    });

    test('column menu stays compact and lists daily delta after price', async ({page}) => {
        await goToAssetsPage(page);
        await page.getByTestId('view-mode-list').click();

        await page.getByTestId('column-visibility-toggle').click();
        const dropdown = page.getByTestId('column-visibility-dropdown');
        await expect(dropdown).toBeVisible();
        const box = await dropdown.boundingBox();
        const viewport = page.viewportSize();
        if (!box || !viewport) throw new Error('Column visibility dropdown must have measurable viewport bounds.');
        expect(box.width).toBeLessThan(320);
        expect(box.x).toBeGreaterThanOrEqual(7);
        expect(box.x + box.width).toBeLessThanOrEqual(viewport.width - 7);

        const priceItem = page.getByTestId('column-visibility-item-lastPrice');
        const dailyItem = page.getByTestId('column-visibility-item-delta_1D');
        await expect(dailyItem).toBeVisible();
        expect(await priceItem.evaluate((element) => element.compareDocumentPosition(document.querySelector('[data-testid="column-visibility-item-delta_1D"]')!) & Node.DOCUMENT_POSITION_FOLLOWING)).toBeTruthy();
    });

    // ========================================================================
    // Test 11: Type filter dropdown can be opened and has options
    // ========================================================================
    test('type filter dropdown opens with checkboxes', async ({page}) => {
        await goToAssetsPage(page);
        const typeFilter = page.getByTestId('assets-type-filter');
        await expect(typeFilter).toBeVisible();

        // Click to open dropdown (custom multi-checkbox with role="listbox")
        await typeFilter.click();

        // Should show a listbox with checkbox items
        const listbox = page.locator('[role="listbox"]');
        await expect(listbox).toBeVisible();
    });

    // ========================================================================
    // Test 12: Search filter hides non-matching cards
    // ========================================================================
    test('search filter hides non-matching cards', async ({page}) => {
        await goToAssetsPage(page);
        const cards = page.locator('[data-testid^="asset-card-"]');
        const totalCards = await cards.count();

        if (totalCards < 2) {
            throw new Error('Need at least 2 assets — check populate_mock_data.py');
        }

        // Search for a string that won't match any asset
        const searchInput = page.getByTestId('assets-search-input');
        await searchInput.fill('zzzzz_nonexistent_12345');

        // Visible cards should shrink. expect.poll retries; the bare count() that
        // used to follow a 500ms sleep did not, so the sleep was the only thing
        // keeping this honest — and it had to outlast a debounced filter.
        await expect.poll(() => cards.count(), {timeout: 5_000}).toBeLessThan(totalCards);
    });

    // ========================================================================
    // Test 13: Active/All toggle changes badge count
    // ========================================================================
    test('active/all toggle changes displayed count', async ({page}) => {
        await goToAssetsPage(page);
        const badge = page.getByTestId('assets-count-badge');
        const activeBadge = await badge.textContent();

        // Toggle to show all (including inactive)
        const toggle = page.getByTestId('assets-active-toggle');
        await toggle.click();
        // aria-pressed is the toggle telling us it flipped. Comparing the badges
        // before that is comparing a number with itself.
        await expect(toggle).toHaveAttribute('aria-pressed', 'false');

        const allBadge = await badge.textContent();
        // Count should be same or greater (all >= active)
        expect(parseInt(allBadge || '0')).toBeGreaterThanOrEqual(parseInt(activeBadge || '0'));
    });

    test('loads all asset cards through exactly one bulk price request', async ({page}) => {
        const bulkRequests: Array<{postData: unknown}> = [];
        page.on('request', (request) => {
            if (request.method() !== 'POST') return;
            if (new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return;
            bulkRequests.push({postData: request.postDataJSON()});
        });

        await goToAssetsPage(page);
        await expect(page.getByTestId('assets-page')).toBeVisible({timeout: 8_000});
        await page.waitForLoadState('networkidle');

        expect(bulkRequests).toHaveLength(1);
        expect(Array.isArray(bulkRequests[0].postData)).toBe(true);
        expect((bulkRequests[0].postData as unknown[]).length).toBeGreaterThan(0);
    });

    // ========================================================================
    // Test 14: The Assets ↔ Correlation tab switch. `activeTab === 'correlation'`
    // swaps the whole list body for the asset-set risk panel — a branch of the
    // page no test had ever entered. No data is mutated.
    // ========================================================================
    test('correlation tab mounts the asset-set risk panel and returns to the list', async ({page}) => {
        await goToAssetsPage(page);
        const appleCard = page.locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i});
        await expect(appleCard.first()).toBeVisible();

        await page.getByTestId('assets-tab-correlation').click();
        await expect(page.getByTestId('asset-global-risk-panel')).toBeVisible({timeout: 15_000});
        // The correlation tab replaces the list body, so the card grid is gone.
        await expect(page.locator('[data-testid^="asset-card-"]')).toHaveCount(0);

        await page.getByTestId('assets-tab-list').click();
        await expect(appleCard.first()).toBeVisible();
        await expect(page.getByTestId('asset-global-risk-panel')).toHaveCount(0);
    });

    // ========================================================================
    // Test 15: List-view bulk delete. Owns its data end to end: it creates two
    // assets tagged with a unique token, filters the list to just those two,
    // selects them, deletes them through the toolbar's confirm dialog, and
    // asserts the rows are gone. The `finally` removes them over the API in case
    // a step fails before the UI delete lands. This is the first test to reach
    // the DataTable selection, the DataTableToolbar and the bulk-delete confirm.
    // ========================================================================
    test('list-view bulk delete removes the selected rows', async ({page}) => {
        const token = uniqueToken(6);
        const names = [`E2E BulkDel ${token} A`, `E2E BulkDel ${token} B`];
        let ids: number[] = [];
        try {
            const createRes = await page.request.post('/api/v1/assets', {
                data: names.map((display_name) => ({display_name, currency: 'EUR', asset_type: 'STOCK'})),
            });
            expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
            ids = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results.map((r) => r.asset_id);
            expect(ids).toHaveLength(2);

            await goToAssetsPage(page);
            // Narrow the whole list (grid and table share filteredAssets) to just
            // the two rows this test owns, so select-all selects exactly them and
            // nothing a neighbour worker created.
            await page.getByTestId('assets-search-input').fill(token);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

            await page.getByTestId('view-mode-list').click();
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

            for (const id of ids) {
                await expect(page.getByTestId(`dt-row-checkbox-${id}`)).toBeVisible();
            }
            // No foreign rows leaked into the filtered view.
            await expect(page.locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(2);

            await page.getByTestId('dt-select-all').click();
            const toolbar = page.getByTestId('selection-toolbar');
            await expect(toolbar).toHaveAttribute('data-selected-count', '2');

            await page.getByTestId('toolbar-action-delete').click();
            await expect(page.getByTestId('confirm-modal-message')).toBeVisible();
            await page.getByTestId('confirm-modal-confirm').click();

            // The dialog switches to results mode (a Close button) once the delete
            // has run — that transition is the signal the API call completed.
            await expect(page.getByTestId('confirm-modal-close')).toBeVisible({timeout: 15_000});
            await page.getByTestId('confirm-modal-close').click();

            // Both owned rows are gone from the still-filtered table.
            for (const id of ids) {
                await expect(page.getByTestId(`dt-row-checkbox-${id}`)).toHaveCount(0);
            }
        } finally {
            for (const id of ids) {
                await page.request.delete(`/api/v1/assets?asset_ids=${id}`).catch(() => {});
            }
        }
    });

    // ========================================================================
    // Test 16 (F15 round-2): the list view is THREE stacked tables, one per
    // usage scope. The bucketing contract is the txCount badge palette (own →
    // emerald, others → blue, analysis → gray — the class IS the feature here,
    // as sanctioned for the AssetTable component test): every row of a panel
    // must carry that panel's badge, and the seeded Apple position (transacted
    // on Interactive Brokers, which TEST_USER owns at 30%) must land in "own".
    // ========================================================================
    test('list view buckets every row into its usage panel', async ({page}) => {
        await goToAssetsPage(page);
        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);

        const panels = [
            {id: 'own', badge: 'bg-emerald-100'},
            {id: 'others', badge: 'bg-blue-100'},
            {id: 'analysis', badge: 'bg-gray-100'},
        ] as const;

        for (const {id, badge} of panels) {
            const panel = page.getByTestId(`assets-table-panel-${id}`);
            await expect(panel, `panel "${id}" empty or missing — the mock data puts assets in all three (populate_mock_data.py)`).toBeVisible();
            // Retry until rows are painted; a bare count() would read mid-render.
            await expect.poll(async () => panel.locator('tbody tr[data-row-id]').count(), {timeout: 10_000}).toBeGreaterThan(0);
            const rowCount = await panel.locator('tbody tr[data-row-id]').count();
            // font-mono pins the txCount badge specifically — other cells can share
            // the palette token (a provider chip also uses blue, e.g.).
            const badgeCount = await panel.locator(`tbody tr[data-row-id] span.font-mono[class*="${badge}"]`).count();
            expect(badgeCount, `panel "${id}": every row must carry the ${badge} scope badge`).toBe(rowCount);
        }

        // Placement proof, not just palette: the seeded Apple row sits in "own".
        const appleRow = page.getByTestId('assets-table-panel-own').locator('tbody tr', {hasText: /Apple/i});
        await expect(appleRow.first(), 'seeded Apple (tx on a broker TEST_USER owns) must bucket into "own" — populate_mock_data.py').toBeVisible();
    });

    // ========================================================================
    // Test 17 (F15 round-2): selection made in ANY panel feeds the one shared
    // bulk toolbar. Picks one row from "analysis" (a brand-new asset this test
    // owns, identifiable by id) and one from "own" (identity irrelevant — the
    // subject is the plumbing), and checks the toolbar aggregates both.
    // ========================================================================
    test('bulk selection from different panels aggregates into the shared toolbar', async ({page}) => {
        const token = uniqueToken(6);
        let createdId: number | null = null;
        try {
            const createRes = await page.request.post('/api/v1/assets', {
                data: [{display_name: `E2E CrossSel ${token}`, currency: 'EUR', asset_type: 'STOCK'}],
            });
            expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
            createdId = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;

            await goToAssetsPage(page);
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

            // Row 1 — the created asset, unused anywhere → the analysis panel.
            const analysisPanel = page.getByTestId('assets-table-panel-analysis');
            const createdCheckbox = analysisPanel.getByTestId(`dt-row-checkbox-${createdId}`);
            await expect(createdCheckbox, 'newly created asset (0 tx) must bucket into "analysis"').toBeVisible({timeout: 10_000});
            await createdCheckbox.click();

            // Row 2 — any row of the own panel (seeded by mock data).
            const ownPanel = page.getByTestId('assets-table-panel-own');
            const ownRowCheckbox = ownPanel.locator('tbody tr[data-row-id] [data-testid^="dt-row-checkbox-"]').first();
            await expect(ownRowCheckbox, 'no own-panel rows — check populate_mock_data.py').toBeVisible();
            await ownRowCheckbox.click();

            // One shared toolbar, two panels' selections summed.
            const toolbar = page.getByTestId('selection-toolbar');
            await expect(toolbar).toHaveAttribute('data-selected-count', '2');

            // Restore: deselect both — the toolbar unmounts at zero (the page only
            // renders it with a non-empty selection).
            await createdCheckbox.click();
            await ownRowCheckbox.click();
            await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
        } finally {
            if (createdId != null) await page.request.delete(`/api/v1/assets?asset_ids=${createdId}`).catch(() => {});
        }
    });

    // ========================================================================
    // Test 18 (F15): the GRID view got the same three usage panels in round 1 —
    // as card sections, not tables. No spec had looked at them yet.
    // ========================================================================
    test('grid view renders the three usage panels with the seeded cards bucketed', async ({page}) => {
        await goToAssetsPage(page);
        // Grid is the default view, but localStorage may remember list from a
        // previous test in this context — drive to the end state explicitly.
        await page.getByTestId('view-mode-grid').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);

        for (const panelId of ['own', 'others', 'analysis'] as const) {
            const panel = page.getByTestId(`assets-panel-${panelId}`);
            await expect(panel, `grid panel "${panelId}" empty or missing — populate_mock_data.py seeds all three scopes`).toBeVisible();
            await expect.poll(async () => panel.locator('[data-testid^="asset-card-"]').count(), {timeout: 10_000}).toBeGreaterThan(0);
        }

        // Same placement rule as the table: Apple is used on a broker TEST_USER owns.
        await expect(page.getByTestId('assets-panel-own').locator('[data-testid^="asset-card-"]').filter({hasText: /Apple/i}).first()).toBeVisible();
    });
});
