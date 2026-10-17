/**
 * Asset List Page — E2E Tests
 *
 * Tests the Assets list page: card rendering, filtering, navigation, and basic actions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {IntlMessageFormat} from 'intl-messageformat';
import {expect, test} from '../fixtures/playwright';
import type {Locator, Page, Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToAssetsPage} from './assets-helpers';
import {uniqueToken} from '../fixtures/unique';
import {t} from '../fixtures/i18n-data';
import {daysAgoIso, localIso} from '../fixtures/dates';
import {describeShown, isStoredPoint, overwriteCounts, overwriteWarningSentence, pageLanguage, recordSyncRequests, storedAssetPrices, type SyncPeriod} from '../fixtures/sync-overwrite';
import {schemas} from '../../src/lib/api/generated';

type SyntheticAsset = {
    id: number;
    display_name: string;
    currency: string;
    asset_type: 'STOCK';
    active: boolean;
    has_metadata: boolean;
    provider_code: null;
    tx_count: number;
    tx_count_own: number;
    held_by_me: boolean;
    held_by_others: boolean;
};

type SyntheticAssetOptions = {
    displayName?: string;
    active?: boolean;
    heldByMe?: boolean;
    heldByOthers?: boolean;
};

function syntheticAsset(id: number, txCount = 0, txCountOwn = 0, options: SyntheticAssetOptions = {}): SyntheticAsset {
    return {
        id,
        display_name: options.displayName ?? `Synthetic asset ${id}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active: options.active ?? true,
        has_metadata: false,
        provider_code: null,
        tx_count: txCount,
        tx_count_own: txCountOwn,
        held_by_me: options.heldByMe ?? false,
        held_by_others: options.heldByOthers ?? false,
    };
}

async function mockAssets(page: Page, assets: SyntheticAsset[]) {
    await page.route('**/api/v1/assets/query*', async (route) => {
        await route.fulfill({json: assets});
    });
    await page.route('**/api/v1/assets/prices/query', async (route) => {
        const requested = (route.request().postDataJSON() as Array<{asset_id: number}> | null) ?? [];
        await route.fulfill({
            json: {
                items: requested.map(({asset_id}) => ({
                    asset_id,
                    prices: [],
                    events: [],
                    errors: [],
                    signals: [],
                })),
            },
        });
    });
    await page.route('**/api/v1/assets/prices/current', async (route) => {
        await route.fulfill({json: {results: [], success_count: 0, errors: []}});
    });
}

async function goToMockedAssets(page: Page, assets: SyntheticAsset[]) {
    await mockAssets(page, assets);
    // Irrelevant source-page filters are deliberate: result actions must build
    // a fresh transaction URL rather than inheriting them.
    await navigateTo(page, '/assets?broker_id=88001&date_start=1999-01-01');
    await expect(page.getByTestId('assets-page')).toHaveAttribute('data-busy', 'false', {timeout: 20_000});
}

async function openSingleDelete(page: Page, assetId: number) {
    await page.getByTestId('view-mode-list').click();
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    await page.getByTestId(`row-actions-${assetId}`).click();
    await page.getByTestId('context-menu-action-delete').click();
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
}

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

    test('global Abs/% controls update every rendered AssetCard data-view-mode', async ({page}) => {
        await goToAssetsPage(page);
        await page.getByTestId('view-mode-grid').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        const cards = page.locator('[data-testid^="asset-card-"][data-view-mode]');
        await expect.poll(() => cards.count(), {timeout: 10_000}).toBeGreaterThan(0);

        const everyCardUses = async (mode: 'absolute' | 'percentage') => cards.evaluateAll((nodes, expected) => nodes.length > 0 && nodes.every((node) => (node as HTMLElement).dataset.viewMode === expected), mode);

        await page.getByTestId('assets-global-view-absolute').click();
        await expect.poll(() => everyCardUses('absolute'), {timeout: 5_000}).toBe(true);

        await page.getByTestId('assets-global-view-percentage').click();
        await expect.poll(() => everyCardUses('percentage'), {timeout: 5_000}).toBe(true);
    });

    test('one AssetCard can override Abs/% until a later global change', async ({page}) => {
        await goToAssetsPage(page);
        await page.getByTestId('view-mode-grid').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);

        const cards = page.getByTestId(/^asset-card-\d+$/);
        const chosenCard = cards.filter({hasText: 'Apple Inc.'});
        await expect(chosenCard).toHaveCount(1);
        await expect(chosenCard).toHaveAttribute('data-testid', /^asset-card-\d+$/);
        const chosenCardTestId = await chosenCard.getAttribute('data-testid');
        if (!chosenCardTestId) throw new Error('Seeded Apple Inc. card must expose its data-testid.');

        const everyOtherCardUses = async (mode: 'absolute' | 'percentage') =>
            cards.evaluateAll(
                (nodes, expected) => {
                    let foundOtherCard = false;
                    const allOtherCardsUseMode = nodes.every((node) => {
                        if (node.getAttribute('data-testid') === expected.chosenCardTestId) return true;
                        foundOtherCard = true;
                        return (node as HTMLElement).dataset.viewMode === expected.mode;
                    });
                    return foundOtherCard && allOtherCardsUseMode;
                },
                {chosenCardTestId, mode},
            );
        const expectEveryCardToUse = async (mode: 'absolute' | 'percentage') => {
            await expect(chosenCard).toHaveAttribute('data-view-mode', mode);
            await expect.poll(() => everyOtherCardUses(mode), {timeout: 5_000}).toBe(true);
        };

        await page.getByTestId('assets-global-view-absolute').click();
        await expectEveryCardToUse('absolute');

        await chosenCard.getByTestId('asset-card-view-toggle').click();
        await expect(chosenCard).toHaveAttribute('data-view-mode', 'percentage');
        await expect.poll(() => everyOtherCardUses('absolute'), {timeout: 5_000}).toBe(true);

        await page.getByTestId('assets-global-view-percentage').click();
        await expectEveryCardToUse('percentage');

        // Changing again proves the local override was cleared, not merely
        // hidden because it happened to match the first new global mode.
        await page.getByTestId('assets-global-view-absolute').click();
        await expectEveryCardToUse('absolute');
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
    // Test 13: Active and inactive toggles implement all four lifecycle states.
    // ========================================================================
    test('lifecycle toggles cover active, inactive, union, and unfiltered states', async ({page}) => {
        const active = syntheticAsset(910_021, 0, 0, {displayName: 'Lifecycle active'});
        const inactive = syntheticAsset(910_022, 0, 0, {
            displayName: 'Lifecycle inactive',
            active: false,
        });
        await goToMockedAssets(page, [active, inactive]);
        await page.getByTestId('view-mode-grid').click();

        const activeToggle = page.getByTestId('assets-active-toggle');
        const inactiveToggle = page.getByTestId('assets-inactive-toggle');
        const activeCard = page.getByTestId(`asset-card-${active.id}`);
        const inactiveCard = page.getByTestId(`asset-card-${inactive.id}`);

        // Default: active only.
        await expect(activeToggle).toHaveAttribute('aria-pressed', 'true');
        await expect(inactiveToggle).toHaveAttribute('aria-pressed', 'false');
        await expect(activeCard).toBeVisible();
        await expect(inactiveCard).toHaveCount(0);

        // Both selected: the two sets form a union.
        await inactiveToggle.click();
        await expect(inactiveToggle).toHaveAttribute('aria-pressed', 'true');
        await expect(activeCard).toBeVisible();
        await expect(inactiveCard).toBeVisible();

        // Inactive only.
        await activeToggle.click();
        await expect(activeToggle).toHaveAttribute('aria-pressed', 'false');
        await expect(inactiveCard).toBeVisible();
        await expect(activeCard).toHaveCount(0);

        // Neither selected: no lifecycle filter, so both return.
        await inactiveToggle.click();
        await expect(inactiveToggle).toHaveAttribute('aria-pressed', 'false');
        await expect(activeCard).toBeVisible();
        await expect(inactiveCard).toBeVisible();
    });

    test('lifecycle ordering and visual markers apply in every usage panel', async ({page}) => {
        const panels = [
            {
                id: 'own',
                active: syntheticAsset(910_101, 4, 2, {displayName: 'Own active', heldByMe: true}),
                inactive: syntheticAsset(910_102, 5, 3, {
                    displayName: 'Own inactive',
                    active: false,
                    heldByMe: true,
                }),
            },
            {
                id: 'others',
                active: syntheticAsset(910_103, 4, 0, {displayName: 'Others active', heldByOthers: true}),
                inactive: syntheticAsset(910_104, 5, 0, {
                    displayName: 'Others inactive',
                    active: false,
                    heldByOthers: true,
                }),
            },
            {
                id: 'analysis',
                active: syntheticAsset(910_105, 0, 0, {displayName: 'Analysis active'}),
                inactive: syntheticAsset(910_106, 0, 0, {
                    displayName: 'Analysis inactive',
                    active: false,
                }),
            },
        ] as const;

        // Each inactive asset precedes its active peer in the intercepted payload.
        // The UI must reorder by lifecycle without relying on database ordering.
        await goToMockedAssets(
            page,
            panels.flatMap((panel) => [panel.inactive, panel.active]),
        );
        await page.getByTestId('assets-inactive-toggle').click();
        await expect(page.getByTestId('assets-inactive-toggle')).toHaveAttribute('aria-pressed', 'true');
        await page.getByTestId('view-mode-grid').click();

        for (const panel of panels) {
            const section = page.getByTestId(`assets-panel-${panel.id}`);
            const cards = section.locator('[data-testid^="asset-card-"][data-lifecycle]');
            await expect(section).toBeVisible();
            await expect(cards).toHaveCount(2);
            await expect
                .poll(() => cards.evaluateAll((items) => items.map((item) => item.getAttribute('data-testid'))), {
                    timeout: 5_000,
                })
                .toEqual([`asset-card-${panel.active.id}`, `asset-card-${panel.inactive.id}`]);

            // The lifecycle is the state the card publishes, never its surface colour:
            // that is a theme role, and it changes whenever the colours do.
            const activeCard = page.getByTestId(`asset-card-${panel.active.id}`);
            const inactiveCard = page.getByTestId(`asset-card-${panel.inactive.id}`);
            await expect(activeCard).toHaveAttribute('data-lifecycle', 'active');
            await expect(inactiveCard).toHaveAttribute('data-lifecycle', 'inactive');
        }

        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);

        for (const panel of panels) {
            const section = page.getByTestId(`assets-table-panel-${panel.id}`);
            const rows = section.locator('tbody tr[data-row-id]');
            await expect(section).toBeVisible();
            await expect(rows).toHaveCount(2);
            await expect
                .poll(() => rows.evaluateAll((items) => items.map((item) => item.getAttribute('data-row-id'))), {
                    timeout: 5_000,
                })
                .toEqual([String(panel.active.id), String(panel.inactive.id)]);

            const activeRow = section.locator(`tbody tr[data-row-id="${panel.active.id}"]`);
            const inactiveRow = section.locator(`tbody tr[data-row-id="${panel.inactive.id}"]`);
            await expect(activeRow).not.toHaveClass(/asset-row-inactive/);
            await expect(inactiveRow).toHaveClass(/asset-row-inactive/);
        }
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

    test('blocked single delete stays open with the returned global count and a clean transaction link', async ({page}) => {
        const asset = syntheticAsset(910_031);
        await goToMockedAssets(page, [asset]);
        await page.route('**/api/v1/assets?*', async (route) => {
            await route.fulfill({
                json: {
                    results: [
                        {
                            success: false,
                            deleted_count: 0,
                            asset_id: asset.id,
                            display_name: asset.display_name,
                            error_code: 'HAS_TRANSACTIONS',
                            transaction_count: 17,
                            message: '<a href="/backend-link">backend-supplied link</a>',
                        },
                    ],
                    success_count: 0,
                    errors: [],
                },
            });
        });

        await openSingleDelete(page, asset.id);
        await page.getByTestId('confirm-modal-confirm').click();

        const link = page.getByTestId('asset-delete-transactions-link');
        await expect(link).toBeVisible();
        await expect(link).toHaveAttribute('href', `/transactions?asset_id=${asset.id}`);
        await expect(page.getByTestId('asset-delete-transactions-link-detail')).toContainText('(17)');
        // The link's own label must be the real transactions.title catalogue entry —
        // never the missing `nav.transactions` key, and never a raw key at all
        // (svelte-i18n renders a missing key as the literal key string, so this
        // check catches that regression by construction rather than by name).
        await expect(link).toHaveText(t('en', 'transactions.title'));
        await expect(link).not.toContainText('nav.transactions');
        await expect(link).not.toContainText('transactions.title');
        await expect(page.getByTestId('confirm-modal-close')).toBeVisible();
    });

    test('successful single delete closes its confirmation', async ({page}) => {
        const asset = syntheticAsset(910_032);
        await goToMockedAssets(page, [asset]);
        await page.route('**/api/v1/assets?*', async (route) => {
            await route.fulfill({
                json: {
                    results: [
                        {
                            success: true,
                            deleted_count: 1,
                            asset_id: asset.id,
                            display_name: asset.display_name,
                            error_code: null,
                            transaction_count: null,
                            message: null,
                        },
                    ],
                    success_count: 1,
                    errors: [],
                },
            });
        });

        await openSingleDelete(page, asset.id);
        await page.getByTestId('confirm-modal-confirm').click();

        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);
        await expect(page.getByTestId(`dt-row-checkbox-${asset.id}`)).toHaveCount(0);
    });

    test('bulk blocked results keep each returned global count with its own clean transaction link', async ({page}) => {
        const blocked = [
            {asset: syntheticAsset(910_041), count: 23},
            {asset: syntheticAsset(910_042), count: 41},
        ];
        const assets = blocked.map(({asset}) => asset);
        await goToMockedAssets(page, assets);
        await page.route('**/api/v1/assets?*', async (route) => {
            await route.fulfill({
                json: {
                    results: blocked.map(({asset, count}) => ({
                        success: false,
                        deleted_count: 0,
                        asset_id: asset.id,
                        display_name: asset.display_name,
                        error_code: 'HAS_TRANSACTIONS',
                        transaction_count: count,
                        message: null,
                    })),
                    success_count: 0,
                    errors: [],
                },
            });
        });

        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        for (const asset of assets) {
            await page.getByTestId(`dt-row-checkbox-${asset.id}`).click();
        }
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(assets.length));
        await page.getByTestId('toolbar-action-delete').click();
        await page.getByTestId('confirm-modal-confirm').click();

        for (const {asset, count} of blocked) {
            const testId = `asset-bulk-delete-transactions-${asset.id}`;
            const link = page.getByTestId(testId);
            await expect(link).toHaveAttribute('href', `/transactions?asset_id=${asset.id}`);
            await expect(page.getByTestId(`${testId}-detail`)).toContainText(`(${count})`);
            // Same catalogue-key contract as the single-delete case, checked once
            // per row so a per-asset action never falls back to a raw key either.
            await expect(link).toHaveText(t('en', 'transactions.title'));
            await expect(link).not.toContainText('transactions.title');
        }
        await expect(page.getByTestId('confirm-modal-close')).toBeVisible();
    });

    test('bulk delete failure without HAS_TRANSACTIONS omits the transaction link and count', async ({page}) => {
        // B3/F16: a failure that is NOT the HAS_TRANSACTIONS contract (a generic
        // DB error, a permissions error, whatever else the backend may return)
        // must not be dressed up with a transaction link or a "(N)" count it never
        // received — that action and that number are only truthful when error_code
        // really is HAS_TRANSACTIONS.
        const asset = syntheticAsset(910_051);
        await goToMockedAssets(page, [asset]);
        await page.route('**/api/v1/assets?*', async (route) => {
            await route.fulfill({
                json: {
                    results: [
                        {
                            success: false,
                            deleted_count: 0,
                            asset_id: asset.id,
                            display_name: asset.display_name,
                            error_code: null,
                            transaction_count: null,
                            message: 'Deletion refused by a non-transaction constraint',
                        },
                    ],
                    success_count: 0,
                    errors: [],
                },
            });
        });

        await page.getByTestId('view-mode-list').click();
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        await page.getByTestId(`dt-row-checkbox-${asset.id}`).click();
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '1');
        await page.getByTestId('toolbar-action-delete').click();
        await page.getByTestId('confirm-modal-confirm').click();

        await expect(page.getByTestId('confirm-modal-close')).toBeVisible();
        await expect(page.getByTestId(`asset-bulk-delete-transactions-${asset.id}`)).toHaveCount(0);
        // The raw backend message is shown as-is (no synthesized count suffix).
        await expect(page.getByText('Deletion refused by a non-transaction constraint')).toBeVisible();
        await expect(page.getByText('Deletion refused by a non-transaction constraint (', {exact: false})).toHaveCount(0);
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

    // ========================================================================
    // Test 19 (Mandate B, then R17): the taxonomy grew from 9 to 18 values, and
    // every table keyed on it fails *silently* when it misses an entry — a missing
    // PNG_MAP entry draws other.png, a missing filter entry makes the type
    // un-filterable, and nothing throws anywhere. `assetTypeTables.test.ts`
    // proves the tables agree with the Python enum as text; this proves the
    // same thing at runtime and through the backend: a new-taxonomy asset is
    // accepted, comes back with its type intact, draws its own icon, and is
    // offered in the page's type filter.
    //
    // It seeds its own assets first, and that is not a convenience: the filter
    // only lists types the user actually owns (`availableTypes` keeps the ones
    // with typeCounts > 0, in +page.svelte), so a spec that asserted on the
    // dropdown without seeding it would be asserting on whatever the shared
    // database happened to be holding that minute.
    // ========================================================================
    test('new taxonomy types survive the round trip: API, card icon and type filter', async ({page}) => {
        const token = uniqueToken(6);
        const prefix = `E2E Taxonomy ${token}`;
        // COMMODITY and REAL_ESTATE are *primary* types and each owns an icon
        // file — note the hyphen in real-estate.png against the underscore in
        // the enum value, which is precisely the kind of mismatch that ends in
        // a silent other.png. The two subtypes are drawn with composites (R16,
        // decision D52): the icon of their family, whole, with a pastille in the
        // corner saying what they contain. etf-stock.png is the ETF tag with the
        // stock pastille; crowdfunding-real-estate.png, the crowdfunding icon
        // with the real-estate one. Each is a distinct file generated by
        // scripts/compose_asset_type_icons.py, so each subtype now proves its own
        // picture as well as the enum round trip and the filter entry — an
        // ETF_STOCK card falling back to the plain etf.png is a red here.
        const seeds = [
            {type: 'COMMODITY', icon: 'commodity.png'},
            {type: 'REAL_ESTATE', icon: 'real-estate.png'},
            {type: 'ETF_STOCK', icon: 'etf-stock.png'},
            // R17: the first subtype of the second family, CROWDFUND.
            {type: 'CROWDFUND_REAL_ESTATE', icon: 'crowdfunding-real-estate.png'},
            // The control, and the reason there is one: "the type filter really
            // filtered" needs something of this test's own that must DISAPPEAR
            // when COMMODITY is selected. Without it the only proof available
            // would be a count over rows this test does not own.
            {type: 'STOCK', icon: 'stock.png'},
        ] as const;
        const nameFor = (type: string) => `${prefix} ${type}`;
        /** Filled from the create response; every later step identifies rows through it. */
        const seeded: Array<{type: string; icon: string; id: number}> = [];
        /** Everything the backend actually created, asserted or not — this is what `finally` removes. */
        const createdIds: number[] = [];
        const idOf = (type: string) => seeded.find((s) => s.type === type)!.id;

        try {
            // ---- 1. the backend accepts the new enum values at all --------
            // A 422 here is the whole mandate failing at its first step, and it
            // is worth separating from every UI assertion below.
            const createRes = await page.request.post('/api/v1/assets', {
                data: seeds.map(({type}) => ({display_name: nameFor(type), currency: 'EUR', asset_type: type})),
            });
            expect(createRes.ok(), `creating one asset per taxonomy value must succeed: ${await createRes.text()}`).toBeTruthy();
            const created = ((await createRes.json()) as {results: Array<{asset_id: number | null; success: boolean; message: string; display_name: string}>}).results;
            // Register what exists BEFORE asserting anything about it: creates
            // are per-item and partial success is allowed, so a value the enum
            // rejects still leaves its predecessors in a shared database, and
            // the first failing expect below would otherwise leak them.
            for (const row of created) if (row.asset_id != null) createdIds.push(row.asset_id);

            // Keyed on display_name, not on the position in `results`: the two
            // happen to agree today, and relying on that would be exactly the
            // assumption this suite does not make.
            for (const {type, icon} of seeds) {
                const row = created.find((r) => r.display_name === nameFor(type));
                expect(row, `${type}: the create response must carry a result for "${nameFor(type)}"`).toBeTruthy();
                expect(row!.success, `${type} must be a value the backend enum accepts: ${row!.message}`).toBe(true);
                seeded.push({type, icon, id: row!.asset_id!});
            }

            // ---- 2. …and hands each value back unchanged ------------------
            const listed = (await (await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(prefix)}`)).json()) as Array<{id: number; asset_type: string | null}>;
            for (const {type, id} of seeded) {
                const row = listed.find((a) => a.id === id);
                expect(row, `${type}: the asset this test created must come back from /assets/query`).toBeTruthy();
                expect(row!.asset_type, `${type} must not be silently degraded on the way back`).toBe(type);
            }

            // ---- 3. the grid draws each one with its own icon -------------
            await goToAssetsPage(page);
            // Grid is the default view, but ViewModeToggle remembers the last
            // choice per user in localStorage — drive to the end state.
            await page.getByTestId('view-mode-grid').click();
            await page.getByTestId('assets-search-input').fill(prefix);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

            for (const {type, icon, id} of seeded) {
                const card = page.getByTestId(`asset-card-${id}`);
                // Presence barrier for the negative that follows: a card that
                // has not mounted yet satisfies any absence assertion, so "it
                // does not show other.png" only means something once the card
                // and its icon are demonstrably on screen. The search box is
                // debounced and `data-busy` does not cover the debounce, which
                // is why this is a retrying assertion and not a count().
                await expect(card, `${type}: the seeded card must reach the grid`).toBeVisible({timeout: 15_000});
                // `.first()` on an already-filtered locator: a card legitimately
                // paints this src twice (the round avatar and the type badge),
                // and which one arrives first is not this test's business.
                await expect(card.locator(`img[src="/icons/asset-types/${icon}"]`).first(), `${type} must resolve to ${icon}`).toBeVisible();
                // The failure this whole workstream exists to prevent: an enum
                // value PNG_MAP has never heard of is drawn as other.png and
                // nothing complains. `toHaveCount(0)` is the honest matcher here
                // — the fallback is never *hidden* when it happens, it is simply
                // the src that got rendered.
                await expect(card.locator('img[src="/icons/asset-types/other.png"]'), `${type} fell through to the silent other.png fallback`).toHaveCount(0);
            }

            // ---- 4. the page's own type filter offers the new values ------
            // The dropdown used to carry a private nine-entry TYPE_ICON_MAP, so
            // the icon inside the option row is a regression guard in its own
            // right, not decoration.
            await page.getByTestId('assets-type-filter').click();
            for (const {type, icon} of seeded) {
                const option = page.getByTestId(`assets-type-filter-option-${type}`);
                await expect(option, `${type} must be offered in the type filter — this test owns one, so its count is > 0`).toBeVisible();
                await expect(option.locator(`img[src="/icons/asset-types/${icon}"]`), `${type}'s filter row must draw through the shared icon map`).toHaveCount(1);
            }

            // ---- 5. …and selecting one really narrows the list ------------
            await page.getByTestId('assets-type-filter-option-COMMODITY').click();
            // Selecting does not close the fixed-position panel; close it on its
            // own trigger and end on the post-condition rather than leaving an
            // overlay over the grid the next assertions read.
            await page.getByTestId('assets-type-filter').click();
            await expect(page.getByTestId('assets-type-filter-option-COMMODITY')).toHaveCount(0);

            await expect(page.getByTestId(`asset-card-${idOf('COMMODITY')}`), 'the COMMODITY asset must survive its own type filter').toBeVisible();
            await expect(page.getByTestId(`asset-card-${idOf('STOCK')}`), 'the STOCK control must be filtered out — otherwise the type filter is not filtering').toHaveCount(0);
        } finally {
            // Scoped to what this test created: the ids come from its own create
            // response, so nothing here can reach a neighbour's row.
            for (const id of createdIds) {
                await page.request.delete(`/api/v1/assets?asset_ids=${id}`).catch(() => {});
            }
        }
    });
});

// ============================================================================
// The sync dialog's warning before it replaces stored prices (C-66, F-094)
// ============================================================================

/**
 * The last full weekend at least two weeks back, on the local calendar `daysAgoIso` reads: its Saturday and Sunday as
 * the period, with the Friday before and the Monday after. Computed from today, never a fixed date.
 */
function pastWeekend(): {friday: string; period: SyncPeriod; monday: string} {
    const today = new Date();
    // Fourteen days back is today's weekday again; `getDay()` days further back (Sunday 0 … Saturday 6) is a Sunday.
    const sundayBack = 14 + today.getDay();
    const daysBack = (days: number): string => {
        const date = new Date(today);
        date.setDate(date.getDate() - days);
        return localIso(date);
    };
    return {friday: daysBack(sundayBack + 2), period: {start: daysBack(sundayBack + 1), end: daysBack(sundayBack)}, monday: daysBack(sundayBack - 1)};
}

/**
 * What the list will show of each of the test's own assets over `period`, read as `storedAssetPrices` reads every asset
 * «Sync all» syncs — from the endpoint the page reads its prices from: the points inside the period, and of those the
 * stored rows (`isStoredPoint`, the page's rule).
 */
async function ownAssetPrices(page: Page, assetIds: number[], period: SyncPeriod): Promise<Map<number, {shown: number; stored: number}>> {
    const items = assetIds.map((assetId) => schemas.FAPriceQueryItem.parse({asset_id: assetId, date_range: period}));
    const queried = await page.request.post('/api/v1/assets/prices/query', {data: items});
    expect(queried.ok(), `POST /api/v1/assets/prices/query over ${period.start} → ${period.end}: HTTP ${queried.status()} ${await queried.text()}`).toBe(true);
    const answer = schemas.FAPriceQueryResponse.parse(await queried.json());
    return new Map(
        assetIds.map((assetId): [number, {shown: number; stored: number}] => {
            const points = ((answer.items ?? []).find((item) => item.asset_id === assetId)?.prices ?? []).filter((point) => point.date >= period.start && point.date <= period.end);
            return [assetId, {shown: points.length, stored: points.filter(isStoredPoint).length}];
        }),
    );
}

/** A list row's selection box, driven to `selected`: its state is asked first, never a blind click on a toggle. */
async function selectRow(page: Page, assetId: number, selected: boolean): Promise<void> {
    const box = page.getByTestId(`dt-row-checkbox-${assetId}`);
    const state = selected ? 'checked' : 'unchecked';
    if ((await box.getAttribute('data-state')) !== state) await box.click();
    await expect(box).toHaveAttribute('data-state', state);
}

/**
 * The list's sync dialog syncs assets with a provider over the page's period — «Sync all» every one of them, the
 * selection's Sync the selected ones — and a sync replaces the prices stored in that period with the provider's, manual
 * edits included. Before the start the dialog says so, in one warning for its one section:
 * `asset-sync-modal-overwrite-warning`, `data-existing` of its `data-total` assets storing a price in the period. A day
 * the page shows filled backward from an earlier price is not a stored row of the period, so it is never counted.
 *
 * Neither test assumes what its period holds: each reads it through the endpoint the page reads its prices from —
 *   · «Sync all» over the 30 days up to yesterday, where some asset it syncs stores prices (`storedAssetPrices`);
 *   · the selection's Sync over a past weekend, between the only two prices an asset of the test's own stores — the
 *     Friday before and the Monday after: the page shows both days filled backward from the Friday and must not count
 *     them — the negative is the rule, not an empty period. A second asset of the test's own, storing the Saturday
 *     too, is the control: selected with the first, it is the one counted.
 *
 * Neither test starts the dialog: no sync request may leave the page, so no provider is ever called.
 */
test.describe('Assets list — the sync dialog warns before replacing stored prices (C-66)', () => {
    // A ceiling, never a delay: each test reads prices over its period before loading the list's two waves — every
    // priced asset's, or two assets it first creates; the second also opens the dialog twice — and a describe's timeout
    // also covers the sign-in below: at load, more than the default 30 s leaves the dialog. Only the timeout is set: the
    // file's parallel mode is inherited unchanged.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        // The list polls live prices while its period reaches today: the user's today since Z-3 (`todayIso()`), the
        // local calendar `daysAgoIso` reads too — the config sets no `timezoneId` — so no period below does. A poll would
        // ask the providers and write each fresh quote as today's price of a shared asset: answered here, empty, so that
        // «no provider is called, nothing is written» does not rest on the periods' arithmetic. The warning reads the
        // stored prices, never the live ones.
        await page.route('**/api/v1/assets/prices/current', (route) => route.fulfill({json: {results: [], success_count: 0, errors: []}}));
    });

    test('sync all over a period holding stored prices warns once, counting among the assets it syncs', async ({page}) => {
        const period: SyncPeriod = {start: daysAgoIso(30), end: daysAgoIso(1)};
        const targets = await storedAssetPrices(page, period);
        if (!targets.some((target) => target.stored > 0)) {
            throw new Error(`precondition: no asset with a provider stores a price between ${period.start} and ${period.end} (${describeShown(targets)}) — check populate_mock_data.py (populate_price_history)`);
        }

        const syncRequests = recordSyncRequests(page);
        await goToAssetsPage(page, period);
        await page.getByTestId('assets-sync-all-button').click();

        const modal = page.getByTestId('asset-sync-modal');
        await expect(modal).toBeVisible();
        const scope = modal.getByTestId('sync-modal-count');
        // The dialog syncs the page's period: the one the targets were read over.
        await expect(scope).toContainText(period.start);
        await expect(scope).toContainText(period.end);
        await expect(scope).toHaveAttribute('data-section-count', '1');

        const warning = modal.getByTestId('asset-sync-modal-overwrite-warning');
        await expect(warning, 'one warning: the dialog has one section').toHaveCount(1);
        const {section, existing, total} = await overwriteCounts(warning);
        expect(section).toBe('assets');
        expect(total, 'counted out of every asset the dialog syncs').toBe(Number(await scope.getAttribute('data-item-count')));
        expect(existing, 'some asset the dialog syncs stores a price in the period').toBeGreaterThanOrEqual(1);
        expect(existing, 'only assets the dialog syncs are counted').toBeLessThanOrEqual(total);
        // One section: the sentence alone — the catalogue's, for these counts, in the page's language.
        await expect(warning).toHaveText(overwriteWarningSentence(await pageLanguage(page), existing, total));

        // Still before the start, and closed from there: the dialog is never started.
        await expect(modal.getByTestId('sync-modal-start')).toBeEnabled();
        await expect(modal.getByTestId('sync-modal-results')).toHaveCount(0);
        await modal.getByTestId('sync-modal-close').click();
        await expect(modal).toBeHidden();
        expect(syncRequests, 'no sync request left the page: no provider was called').toEqual([]);
    });

    test('syncing the selection over a past weekend whose prices are all filled backward does not warn', async ({page}) => {
        // The period: a past weekend, between the only two prices an asset of the test's own stores, the Friday before and
        // the Monday after. Not one still to come: every price query ends tomorrow at the latest (X-R55), and a period
        // starting later shows no price at all.
        //
        // The dialog: the selection's Sync, the list narrowed to the test's own assets (`handleBulkSyncAssets`: the same
        // dialog and warning, over the selected rows with a provider). Not «Sync all», which syncs every asset with a
        // provider whatever the list shows (`handleSyncAllAssets`) — and the seed's Bitcoin and Ethereum, both with a
        // provider, store a price every day, weekends included (populate_mock_data.py, populate_price_history); not a
        // row's own Sync, which starts at once, with no dialog. A second asset of the test's own, storing the Saturday
        // too, is the control: the selection's dialog warns, and counts that one, not the first.
        const token = uniqueToken(6);
        const {friday, period, monday} = pastWeekend();
        const names = {filled: `E2E C66 ${token} filled backward`, stored: `E2E C66 ${token} stored Saturday`};
        // The Friday's close of the asset under test: the price the list shows for it over the weekend, written 123.45
        // or 123,45 by the language of the page.
        const fridayClose = {stored: '123.45', shown: /123[.,]45/};
        /** Every asset the backend created, whatever failed after: what `finally` deletes. */
        const ownIds: number[] = [];
        try {
            const created = await page.request.post('/api/v1/assets', {data: Object.values(names).map((display_name) => ({display_name, currency: 'EUR', asset_type: 'STOCK'}))});
            const createdBody = (await created.json().catch(() => null)) as {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean}>} | null;
            for (const result of createdBody?.results ?? []) if (typeof result.asset_id === 'number') ownIds.push(result.asset_id);
            expect(created.ok(), `creating the two assets must succeed: HTTP ${created.status()} ${JSON.stringify(createdBody)}`).toBe(true);
            const idOf = (name: string): number => {
                const result = createdBody?.results?.find((entry) => entry.display_name === name);
                if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(createdBody)}`);
                return result.asset_id;
            };
            const filledId = idOf(names.filled);
            const storedId = idOf(names.stored);

            // A provider makes each a sync target: mockprov, the test-only one, under the one identifier it refuses to
            // quote — a live poll would write nothing back. Assigned first: the prices stored next are all the assets hold.
            const assignments = [filledId, storedId].map((assetId) => ({asset_id: assetId, provider_code: 'mockprov', identifier: 'INVALID_TICKER_12345', identifier_type: 'TICKER', provider_params: null}));
            const assigned = await page.request.post('/api/v1/assets/provider', {data: assignments});
            const assignedBody = (await assigned.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
            expect(assigned.ok(), `POST /api/v1/assets/provider: HTTP ${assigned.status()} ${JSON.stringify(assignedBody)}`).toBe(true);
            for (const assetId of [filledId, storedId]) expect(assignedBody?.results?.find((entry) => entry.asset_id === assetId)?.success, `mockprov assigned to asset ${assetId}: ${JSON.stringify(assignedBody)}`).toBe(true);

            // The Friday and the Monday around the weekend; the control stores the Saturday too.
            const upserts = [
                {
                    asset_id: filledId,
                    prices: [
                        {date: friday, close: fridayClose.stored},
                        {date: monday, close: '130.00'},
                    ],
                },
                {
                    asset_id: storedId,
                    prices: [
                        {date: friday, close: '67.50'},
                        {date: period.start, close: '68.25'},
                        {date: monday, close: '69.00'},
                    ],
                },
            ];
            const stored = await page.request.post('/api/v1/assets/prices', {data: upserts});
            const storedBody = (await stored.json().catch(() => null)) as {results?: Array<{asset_id: number; count: number}>} | null;
            expect(stored.ok(), `POST /api/v1/assets/prices: HTTP ${stored.status()} ${JSON.stringify(storedBody)}`).toBe(true);
            for (const {asset_id, prices} of upserts) expect(storedBody?.results?.find((entry) => entry.asset_id === asset_id)?.count, `every close of asset ${asset_id} is stored`).toBe(prices.length);

            // The preconditions, computed: over the weekend the asset under test shows both days, filled backward from the
            // Friday, and stores none; the control stores the Saturday and shows the Sunday filled backward from it.
            const shown = await ownAssetPrices(page, [filledId, storedId], period);
            expect(shown.get(filledId), `precondition: between ${period.start} and ${period.end} the asset under test shows both days, filled backward from ${friday}, and stores none — check the backward fill of POST /assets/prices/query (price_query.py)`).toEqual({shown: 2, stored: 0});
            expect(shown.get(storedId), `precondition: the control stores ${period.start} and shows ${period.end} filled backward from it`).toEqual({shown: 2, stored: 1});

            const syncRequests = recordSyncRequests(page);
            await goToAssetsPage(page, period);
            const assetsPage = page.getByTestId('assets-page');
            // The list narrowed to the two assets, then shown as a table: the selection lives there.
            await page.getByTestId('assets-search-input').fill(token);
            await waitForSettled(assetsPage, 20_000);
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(assetsPage, 20_000);
            // Retrying, past the search box's debounce: the two rows of this test, and nothing a neighbour created.
            await expect(page.locator('[data-testid^="dt-row-checkbox-"]'), 'the list narrowed to the two assets of this test').toHaveCount(2, {timeout: 10_000});
            // Presence barrier for the absence at the end: the page holds the weekend of the asset under test — its last
            // price is the Friday's close, carried to the Sunday — so the dialog has points to read, and must not count them.
            await expect(page.locator(`tbody tr[data-row-id="${filledId}"] td[data-column-id="lastPrice"]`), 'the list shows the Friday’s close over the weekend').toHaveText(fridayClose.shown);

            const toolbar = page.getByTestId('selection-toolbar');
            const modal = page.getByTestId('asset-sync-modal');
            const scope = modal.getByTestId('sync-modal-count');
            const warning = modal.getByTestId('asset-sync-modal-overwrite-warning');

            // The control: both selected, the selection's dialog warns — counting the asset that stores the Saturday, not
            // the one whose weekend is filled backward.
            await selectRow(page, filledId, true);
            await selectRow(page, storedId, true);
            await expect(toolbar).toHaveAttribute('data-selected-count', '2');
            await toolbar.getByTestId('toolbar-action-sync').click();
            await expect(modal).toBeVisible();
            await expect(scope).toContainText(period.start);
            await expect(scope).toContainText(period.end);
            await expect(scope, 'the dialog syncs the two selected assets').toHaveAttribute('data-item-count', '2');
            await expect(warning, 'one warning: the dialog has one section').toHaveCount(1);
            expect(await overwriteCounts(warning), 'the control is counted; the asset whose weekend is filled backward is not').toEqual({section: 'assets', existing: 1, total: 2});
            await modal.getByTestId('sync-modal-close').click();
            await expect(modal).toBeHidden();

            // The subject: the control deselected, the dialog syncs the asset whose weekend is all filled backward.
            await selectRow(page, storedId, false);
            await expect(toolbar).toHaveAttribute('data-selected-count', '1');
            await toolbar.getByTestId('toolbar-action-sync').click();
            await expect(modal).toBeVisible();
            // Presence barrier: the dialog has drawn its body before the start — this period, the one asset to sync, the
            // controls a start needs — so the absence below is the rule's, not a dialog still on its way.
            await expect(scope).toContainText(period.start);
            await expect(scope).toContainText(period.end);
            await expect(scope, 'the dialog syncs the selected asset').toHaveAttribute('data-item-count', '1');
            await expect(modal.getByTestId('sync-modal-timeout')).toBeVisible();
            await expect(modal.getByTestId('sync-modal-start')).toBeEnabled();
            await expect(warning, 'a price filled backward is not a stored row: the sync would replace nothing in the period').toHaveCount(0);

            await modal.getByTestId('sync-modal-close').click();
            await expect(modal).toBeHidden();
            expect(syncRequests, 'no sync request left the page: no provider was called').toEqual([]);
        } finally {
            // Each asset goes with its prices and its provider assignment: both cascade.
            for (const id of ownIds) await page.request.delete(`/api/v1/assets?asset_ids=${id}`).catch(() => {});
        }
    });
});

// ============================================================================
// The Δ columns are the backend's period changes (workstream X, lot X-R53)
// ============================================================================

/** The asset period changes, whatever their query string. */
const ASSET_PERIOD_CHANGES = /\/api\/v1\/assets\/prices\/period-changes(\?.*)?$/;

/** The backend's fixed periods, in display order: the `key` and `days` of `FAPeriodChange`. */
const PERIOD_DAYS: ReadonlyArray<readonly [string, number]> = [
    ['1D', 1],
    ['1W', 7],
    ['1M', 30],
    ['3M', 91],
    ['6M', 182],
    ['1Y', 365],
    ['2Y', 730],
    ['3Y', 1095],
    ['5Y', 1825],
];

/** What the stub answers for the own asset: +1.25 % over a day, −25 % over a week, null — no figure — over every longer period. */
const STUBBED_RATIOS: Readonly<Record<string, string>> = {'1D': '0.0125', '1W': '-0.25'};

/** One asset of a period-changes request (`FAPeriodChangesQueryItem`). */
type AssetPeriodChangesQuery = {asset_id: number; as_of: string; target_currency?: string | null};

/** A Δ cell of a table row, by the column id DataTable publishes on each cell. */
function deltaCell(row: Locator, key: string): Locator {
    return row.locator(`td[data-column-id="delta_${key}"]`);
}

/**
 * A Δ cell's percentage as any of the four languages writes it, matched whole: `+1.25%` (English), `+1,25%`
 * (Italian), `+1,25 %` (French, Spanish: a no-break space before the sign); a minus may be `-` or `−`. The figure is
 * read, never a translation.
 */
function percentCell(figure: string): RegExp {
    const parts = /^([+-])(\d+)\.(\d+)$/.exec(figure);
    if (!parts) throw new Error(`percentCell: ${figure} is not a signed decimal such as +1.25`);
    return new RegExp(`^\\s*${parts[1] === '+' ? '\\+' : '[-\\u2212]'}${parts[2]}[.,]${parts[3]}\\s?%\\s*$`);
}

/** The empty marker of a Δ cell: a change the backend could not compute (`null`). */
const EMPTY_CELL = /^\s*—\s*$/;

/**
 * The Δ columns of the table — the fixed 1D, and the periods the range holds (1W … 5Y) — are the backend's (MF-P2):
 * the list asks `POST /assets/prices/period-changes` for every asset it lists, up to the end of the range on screen
 * (`as_of`), shows each `change_ratio` × 100, and the empty marker for a change the backend could not compute (`null`).
 * The browser computes none of them.
 *
 * Observed through the network: the real answer is fetched and only this test's asset is changed in it, with figures
 * its prices could never give — it has none, created here and deleted at the end — so a figure on screen comes from the
 * answer or from nowhere. The range is about two months ending on a known day in the past: 1W and 1M fit it, 3M does
 * not, and no live price is asked (that happens only on a range reaching today).
 *
 * Red today: the list never asks the endpoint — the route never fires — and computes its Δ from the prices it loaded,
 * none for this asset.
 */
test.describe('Assets list — the Δ columns are the backend’s period changes (X-R53)', () => {
    // A ceiling, never a delay: an asset is created, then the list loads its waves — rows, prices, period changes — and
    // settles twice more, narrowed to the asset and then as a table.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('the own row shows each change ratio × 100 up to the end of the range, the empty marker where there is none', async ({page}) => {
        const token = uniqueToken(6);
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const asked: AssetPeriodChangesQuery[] = [];
        const failures: string[] = [];
        let answered = 0;
        let assetId: number | null = null;
        try {
            const createRes = await page.request.post('/api/v1/assets', {data: [{display_name: `E2E PeriodChanges ${token}`, currency: 'EUR', asset_type: 'STOCK'}]});
            expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
            const ownId = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
            assetId = ownId;

            await page.route(ASSET_PERIOD_CHANGES, async (route) => {
                try {
                    asked.push(...((route.request().postDataJSON() as AssetPeriodChangesQuery[] | null) ?? []));
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as {items?: Array<{asset_id: number}>};
                    const periods = PERIOD_DAYS.map(([key, days]) => ({key, days, change_ratio: STUBBED_RATIOS[key] ?? null}));
                    const items = (answer.items ?? []).map((item) => (item.asset_id === ownId ? {...item, periods, errors: []} : item));
                    await route.fulfill({response, json: {...answer, items}});
                } catch (error) {
                    // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and
                    // the request let through, for the test to fail on its own assertions.
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                } finally {
                    answered += 1;
                }
            });

            await goToAssetsPage(page, range);
            const assetsPage = page.getByTestId('assets-page');
            // The list narrowed to the own asset, then shown as a table.
            await page.getByTestId('assets-search-input').fill(token);
            await waitForSettled(assetsPage, 20_000);
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(assetsPage, 20_000);
            const row = page.locator(`tbody tr[data-row-id="${ownId}"]`);
            await expect(row, 'the own asset is listed').toBeVisible({timeout: 10_000});

            // Asked and answered — the page holds `data-busy` until the period changes are in; the poll is a deadline.
            await expect.poll(() => answered, {message: 'the Assets list never asked POST /assets/prices/period-changes: its Δ columns are still computed in the browser', timeout: 10_000}).toBeGreaterThan(0);
            expect(failures, 'the period changes reached the page').toEqual([]);
            expect(asked, 'the own asset is asked up to the end of the range on screen').toContainEqual(expect.objectContaining({asset_id: ownId, as_of: range.end}));
            expect([...new Set(asked.map((item) => item.as_of))], 'every asset is asked up to the end of the range on screen').toEqual([range.end]);

            // The period columns of the range: about two months hold 1M (30 days), not 3M (91).
            const table = page.getByTestId('dt-scroll').filter({has: row});
            await expect(table.getByTestId('dt-header-delta_1M'), 'the 1M column, drawn from the periods of the answer').toHaveCount(1, {timeout: 10_000});
            await expect(table.getByTestId('dt-header-delta_3M')).toHaveCount(0);

            await expect(deltaCell(row, '1D'), '1D: change_ratio 0.0125').toHaveText(percentCell('+1.25'));
            await expect(deltaCell(row, '1W'), '1W: change_ratio -0.25').toHaveText(percentCell('-25.00'));
            await expect(deltaCell(row, '1M'), '1M: change_ratio null').toHaveText(EMPTY_CELL);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
            if (assetId != null) await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
        }
    });
});

// ============================================================================
// Which period changes the list keeps, and when it asks them (workstream X, lot X-R60)
// ============================================================================

/** The prices and backend signals of the list, asked in bulk. */
const ASSET_PRICE_QUERY = /\/api\/v1\/assets\/prices\/query(\?.*)?$/;
/** The asset signal catalogue: read as the page mounts, and again by the signals' retry. */
const ASSET_SIGNAL_CATALOG = /\/api\/v1\/assets\/prices\/signals(\?.*)?$/;

/** A backend signal (`SMA`, offered in both domains) as the chart settings keep it. */
function smaSignal(id: string, period: number, color: string) {
    return {id, signalType: 'sma', params: {period}, style: {color, lineWidth: 1, lineType: 'dotted', markerStart: null, markerEnd: null}};
}

/** The signal a settings save keeps, and the one it drops: two backend signal requests per asset before, one after. */
const KEPT_SIGNAL = smaSignal('e2e-xr60-sma-5', 5, '#2563eb');
const DROPPED_SIGNAL = smaSignal('e2e-xr60-sma-10', 10, '#dc2626');

/**
 * The Assets chart settings (`__global_assets__`) seeded with `signals` for the signed-in user. They live in this test's
 * browser storage (`chartSettingsStore`, under the user's id): nothing shared is written, and the next page load reads
 * them.
 */
async function seedAssetSignals(page: Page, signals: ReadonlyArray<ReturnType<typeof smaSignal>>): Promise<void> {
    const me = await page.request.get('/api/v1/auth/me');
    expect(me.ok(), `GET /api/v1/auth/me answered HTTP ${me.status()}`).toBe(true);
    const userId = ((await me.json()) as {user?: {id?: unknown}}).user?.id;
    if (typeof userId !== 'number' || !Number.isSafeInteger(userId)) throw new Error(`GET /api/v1/auth/me gave no user id (${String(userId)}): the chart settings are stored under it`);
    await page.evaluate(
        ({storageKey, seeded}) => {
            const settings = {colorByBaseline: true, areaFill: true, gridLines: true, staleGradient: true, axisScales: {absolute: {mode: 'auto'}, percentage: {mode: 'include0'}, secondary: {}}, signals: [] as unknown[]};
            localStorage.setItem(storageKey, JSON.stringify({version: 3, globalSettings: settings, pairOverrides: [['__global_assets__', {...settings, signals: seeded}]]}));
        },
        {storageKey: `lf_${userId}_chartSettingsStore`, seeded: signals},
    );
}

/** Whether a bulk request asks, for some item, the backend signal `instanceId` alone: the reload after a save that dropped the others. */
function asksOnlySignal(request: Request, instanceId: string): boolean {
    try {
        const body = request.postDataJSON() as Array<{signals?: Array<{instance_id?: string}>}> | null;
        return Array.isArray(body) && body.some((item) => item.signals?.length === 1 && item.signals[0]?.instance_id === instanceId);
    } catch {
        return false;
    }
}

/**
 * Which period changes the Assets list keeps, and when it asks them (MF-P2, after X-R53).
 *
 * The list asks the period changes of every asset it lists as it loads or reloads, and keeps the answers through
 * `PeriodChangesLedger` (`periodChanges.ts`, its rules pinned in `periodChanges.test.ts`). Observed and stubbed through
 * the network:
 *   · a refresh over the same range whose period changes fail keeps the Δ already computed for that day — the own
 *     asset's, created here with the X-R53 figures, and deleted at the end;
 *   · what the Δ do not depend on asks none: a settings save that changes the signals, the retry of the signal
 *     catalogue. Each counter is proven by the load first, and read once the page has settled after the action.
 *
 * The range is about two months ending on a known day in the past, as in X-R53: no live price is asked. The chart
 * settings are this browser's state, never the database's.
 *
 * Red today: a failed request clears every Δ, whatever day it asked; a settings save and the signals' retry reload the
 * period changes along with the prices.
 */
test.describe('Assets list — which period changes the list keeps, and when it asks them (X-R60)', () => {
    // A ceiling, never a delay: each test loads the list's waves — rows, prices, period changes — and reloads some.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a refresh over the same range whose period changes fail keeps the Δ of that day', async ({page}) => {
        const token = uniqueToken(6);
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const failures: string[] = [];
        let refusing = false;
        let refused = 0;
        let assetId: number | null = null;
        try {
            const createRes = await page.request.post('/api/v1/assets', {data: [{display_name: `E2E PeriodChanges kept ${token}`, currency: 'EUR', asset_type: 'STOCK'}]});
            expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
            const ownId = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
            assetId = ownId;

            // The load answers the own asset's period changes with the X-R53 figures; once refusing, every request fails.
            await page.route(ASSET_PERIOD_CHANGES, async (route) => {
                if (refusing) {
                    await route.fulfill({status: 500, json: {detail: 'synthetic: the period changes are unavailable (X-R60)'}}).catch((error: unknown) => failures.push(String(error)));
                    refused += 1;
                    return;
                }
                try {
                    const response = await route.fetch();
                    if (!response.ok()) {
                        failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                        await route.fulfill({response});
                        return;
                    }
                    const answer = (await response.json()) as {items?: Array<{asset_id: number}>};
                    const periods = PERIOD_DAYS.map(([key, days]) => ({key, days, change_ratio: STUBBED_RATIOS[key] ?? null}));
                    const items = (answer.items ?? []).map((item) => (item.asset_id === ownId ? {...item, periods, errors: []} : item));
                    await route.fulfill({response, json: {...answer, items}});
                } catch (error) {
                    // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and
                    // the request let through, for the test to fail on its own assertions.
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            await goToAssetsPage(page, range);
            const assetsPage = page.getByTestId('assets-page');
            // The list narrowed to the own asset, then shown as a table.
            await page.getByTestId('assets-search-input').fill(token);
            await waitForSettled(assetsPage, 20_000);
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(assetsPage, 20_000);
            const row = page.locator(`tbody tr[data-row-id="${ownId}"]`);
            await expect(row, 'the own asset is listed').toBeVisible({timeout: 10_000});
            await expect(deltaCell(row, '1D'), 'the load: change_ratio 0.0125').toHaveText(percentCell('+1.25'), {timeout: 10_000});
            await expect(deltaCell(row, '1W'), 'the load: change_ratio -0.25').toHaveText(percentCell('-25.00'));

            // The page's refresh, over the same range: its period changes fail.
            refusing = true;
            const refresh = page.getByTestId('assets-refresh-button');
            await expect(refresh).toBeEnabled();
            await refresh.click();
            await expect.poll(() => refused, {message: 'the refresh never asked the period changes again', timeout: 10_000}).toBeGreaterThan(0);
            await waitForSettled(assetsPage, 20_000);
            expect(failures, 'the period changes reached the page').toEqual([]);

            await expect(row, 'the own asset is still listed').toBeVisible();
            await expect(deltaCell(row, '1D'), 'the failed refresh asked up to the same day: the Δ computed for it stay, +1.25 %').toHaveText(percentCell('+1.25'));
            await expect(deltaCell(row, '1W'), 'the failed refresh asked up to the same day: the Δ computed for it stay, −25 %').toHaveText(percentCell('-25.00'));
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
            if (assetId != null) await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
        }
    });

    test('a settings save that changes the signals asks no period changes', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        let asked = 0;
        try {
            await seedAssetSignals(page, [KEPT_SIGNAL, DROPPED_SIGNAL]);
            await page.route(ASSET_PERIOD_CHANGES, async (route) => {
                // Counted on arrival, before any answer can reach the page: a page that has settled has been counted.
                asked += 1;
                await route.continue();
            });
            await goToAssetsPage(page, range);
            const assetsPage = page.getByTestId('assets-page');
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(assetsPage, 20_000);
            expect(asked, 'premise: the list asks the period changes as it loads — the counter counts').toBeGreaterThan(0);

            await page.getByTestId('assets-chart-settings-button').click();
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible();
            const kept = modal.getByTestId(`signal-card-${KEPT_SIGNAL.id}`);
            const dropped = modal.getByTestId(`signal-card-${DROPPED_SIGNAL.id}`);
            await expect(kept, 'premise: the seeded signals are the list’s — check the chart settings storage key').toBeVisible();
            await expect(dropped).toBeVisible();
            await modal.getByTestId(`signal-remove-${DROPPED_SIGNAL.id}`).click();
            await expect(dropped).toHaveCount(0);
            await expect(kept).toBeVisible();

            const askedBefore = asked;
            const signalsReloaded = page.waitForResponse((response) => ASSET_PRICE_QUERY.test(response.url()) && asksOnlySignal(response.request(), KEPT_SIGNAL.id), {timeout: 20_000});
            await page.getByTestId('chart-settings-apply').click();
            await expect(modal).toBeHidden();
            // Presence first: the save reloaded the prices and signals, the one signal left.
            expect((await signalsReloaded).ok(), 'the prices and signals, asked again with the signal left').toBe(true);
            await expect(page.getByTestId('assets-refresh-button'), 'the reload the save started is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await waitForSettled(assetsPage, 20_000);

            expect(asked, 'the save asked the period changes again, though they do not depend on the signals').toBe(askedBefore);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });

    test('the retry of the signal catalogue asks no period changes', async ({page}) => {
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        let asked = 0;
        let catalogAsked = 0;
        let catalogDown = true;
        try {
            // The signal catalogue fails as the list loads, so the settings dialog offers its retry.
            await page.route(ASSET_SIGNAL_CATALOG, async (route) => {
                catalogAsked += 1;
                if (catalogDown) await route.fulfill({status: 500, json: {detail: 'synthetic: the asset signal catalogue is unavailable (X-R60)'}});
                else await route.continue();
            });
            await page.route(ASSET_PERIOD_CHANGES, async (route) => {
                // Counted on arrival, before any answer can reach the page: a page that has settled has been counted.
                asked += 1;
                await route.continue();
            });
            await goToAssetsPage(page, range);
            const assetsPage = page.getByTestId('assets-page');
            expect(catalogAsked, 'premise: the list asked the signal catalogue as it loaded').toBeGreaterThan(0);
            expect(asked, 'premise: the list asks the period changes as it loads — the counter counts').toBeGreaterThan(0);

            await page.getByTestId('assets-chart-settings-button').click();
            const modal = page.getByTestId('chart-settings-modal');
            await expect(modal).toBeVisible();
            const unavailable = modal.getByTestId('signal-backend-error');
            await expect(unavailable, 'the catalogue failed: the dialog says so, and offers its retry').toBeVisible();

            catalogDown = false;
            const askedBefore = asked;
            const catalogAskedBefore = catalogAsked;
            // The notice's one button is its retry.
            await unavailable.getByRole('button').click();
            await expect(unavailable, 'the retry read the catalogue again').toBeHidden({timeout: 10_000});
            expect(catalogAsked, 'the retry asked the catalogue').toBeGreaterThan(catalogAskedBefore);
            await expect(page.getByTestId('assets-refresh-button'), 'the retry is over').toHaveAttribute('data-busy', 'false', {timeout: 20_000});
            await waitForSettled(assetsPage, 20_000);

            expect(asked, 'the retry asked the period changes again, though they do not depend on the signals').toBe(askedBefore);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
        }
    });
});

// ============================================================================
// A bulk price request refused as too large says so (workstream X, lot X-R58)
// ============================================================================

/** The catalogue's sentence for a bulk request refused for its items (`bulk_too_many_items`, Z-25). */
const BULK_TOO_MANY_ITEMS_KEY = 'common.bulkRefusal.tooManyItems';

/**
 * The numbers the stubbed refusal carries: an item cap, and a count past it. Five digits rather than the backend's
 * 1,000: whether a four-digit number is grouped depends on the locale's minimum grouping digits in the CLDR data of the
 * runtime (Node's ICU here writes 1000 in Italian and Spanish), so the browser and Node could write it differently;
 * five digits are grouped in the four languages either way.
 */
const REFUSED_ITEMS = {max_items: 10_000, items: 12_345} as const;

/**
 * `key` as the `lang` catalogue words it, formatted with `values` by `intl-messageformat`, the formatter svelte-i18n
 * compiles messages with — the reading of `overwriteWarningSentence` (`fixtures/sync-overwrite.ts`) for any message.
 * A catalogue without the message fails here, by name: a key that resolved to itself would let a toast printing the
 * key pass.
 */
function catalogueSentence(lang: string, key: string, values: Record<string, number>): string {
    const message = t(lang, key);
    expect(message, `the "${lang}" catalogue has a message for ${key}`).not.toBe(key);
    return String(new IntlMessageFormat(message, lang).format(values));
}

/**
 * A bulk price request the backend refuses as too large reaches the user (X-R58). Since Z-25 `POST
 * /assets/prices/query` refuses a request past its caps with a coded 422 (`backend/app/utils/date_range_limits.py`); the
 * list sends its prices through `sendBulkBatches` (Z-27), which never splits a refusal for its items, so the load fails
 * with it. The list then says so in an error toast: the catalogue's `common.bulkRefusal.tooManyItems`, with the cap and
 * the count the refusal carries. Any other failure stays as it was.
 *
 * Observed through the network: every price request is answered with the refusal. The list is loaded over about two
 * months ending on a known day in the past, as in X-R53: prices to ask, and no live price. The test's own asset —
 * created here and deleted at the end — is a row whose prices the list must ask, so the refused request is proven to
 * be the list's load. The sentence is the catalogue's, formatted for the page's language: never a translation written
 * here.
 *
 * Red today: `fetchPriceSeries` only logs the failure (`console.error`) — the cards stay without prices, and nothing
 * tells the user why.
 */
test.describe('Assets list — a bulk price request refused as too large says so (X-R58)', () => {
    // A ceiling, never a delay: an asset is created, then the list loads its waves — rows, refused prices, period changes.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a load refused for its items shows the catalogue’s sentence, with the cap and the count, in an error toast', async ({page}) => {
        const token = uniqueToken(6);
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const asked: Array<Record<string, unknown>> = [];
        const failures: string[] = [];
        let assetId: number | null = null;
        try {
            const createRes = await page.request.post('/api/v1/assets', {data: [{display_name: `E2E BulkRefusal ${token}`, currency: 'EUR', asset_type: 'STOCK'}]});
            expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
            const ownId = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
            assetId = ownId;

            // Every price request is refused for its items: a refusal Z-27 never splits, so the load gives up on it.
            await page.route(ASSET_PRICE_QUERY, async (route) => {
                try {
                    asked.push(...((route.request().postDataJSON() as Array<Record<string, unknown>> | null) ?? []));
                    await route.fulfill({status: 422, json: {detail: {code: 'bulk_too_many_items', message: `A bulk request may hold at most ${REFUSED_ITEMS.max_items} items, not ${REFUSED_ITEMS.items}`, ...REFUSED_ITEMS}}});
                } catch (error) {
                    // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and
                    // the request let through, for the test to fail on its own assertions.
                    failures.push(String(error));
                    await route.continue().catch(() => undefined);
                }
            });

            // The list over the range; `goToAssetsPage` returns once `data-busy` says the load is over, refusal included.
            await goToAssetsPage(page, range);
            expect(failures, 'the refusal reached the page').toEqual([]);
            expect(asked, 'premise: the list asked the own asset’s prices over the range — the request the refusal answered').toContainEqual(expect.objectContaining({asset_id: ownId, include_price: true, date_range: range}));

            // One load, refused once: one error toast, and its words are the catalogue's.
            const errorToasts = page.getByTestId('toast-error');
            await expect(errorToasts, 'the refused load must say so in an error toast — the list only logged it, and the cards stayed without prices').toHaveCount(1, {timeout: 10_000});
            const sentence = catalogueSentence(await pageLanguage(page), BULK_TOO_MANY_ITEMS_KEY, {max: REFUSED_ITEMS.max_items, count: REFUSED_ITEMS.items});
            await expect(errorToasts, 'the catalogue’s sentence, with the cap and the count of the refusal').toHaveText(sentence);
            await expect(errorToasts).toBeVisible();
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
            if (assetId != null) await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
        }
    });
});
