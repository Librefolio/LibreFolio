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
import {deleteOwned, jsonFrom, type Owned} from './asset-events-owned';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';
import {t} from '../fixtures/i18n-data';
import {daysAgoIso, localIso} from '../fixtures/dates';
import {describeShown, isStoredPoint, overwriteCounts, overwriteWarningSentence, pageLanguage, recordSyncRequests, storedAssetPrices, type SyncPeriod} from '../fixtures/sync-overwrite';
import {chooseTheme} from '../fixtures/galleryFiles';
import {parkPointer} from '../fixtures/galleryRiskLab';
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

/** The test ids ConfirmModal carries on the header of the list's two delete confirmations (X-R20). */
type DeleteConfirmId = 'asset-delete-confirm' | 'asset-bulk-delete-confirm';

/**
 * One of the list's two delete confirmations: the dialog its header belongs to. ConfirmModal is generic — every
 * confirmation on the page has the same `confirm-modal-*` buttons — so a button is this confirmation's only when it is
 * found inside it (X-R20).
 */
function deleteConfirm(page: Page, testId: DeleteConfirmId): Locator {
    return page.getByRole('dialog').filter({has: page.getByTestId(testId)});
}

/**
 * Opens a row's single delete from the list view's row actions. Ends on the single delete's own confirmation on screen,
 * and returns it: whether it asks (`confirm-modal-confirm`) or shows a refusal is the caller's to assert (X-R18).
 */
async function openSingleDelete(page: Page, assetId: number): Promise<Locator> {
    await page.getByTestId('view-mode-list').click();
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    await page.getByTestId(`row-actions-${assetId}`).click();
    await page.getByTestId('context-menu-action-delete').click();
    await expect(page.getByTestId('asset-delete-confirm'), 'the single delete opens its own confirmation').toBeVisible();
    return deleteConfirm(page, 'asset-delete-confirm');
}

/** Opens the bulk delete of the selected rows from the selection toolbar. Ends on its own confirmation on screen, and returns it. */
async function openBulkDelete(page: Page): Promise<Locator> {
    await page.getByTestId('toolbar-action-delete').click();
    await expect(page.getByTestId('asset-bulk-delete-confirm'), 'the bulk delete opens its own confirmation').toBeVisible();
    return deleteConfirm(page, 'asset-bulk-delete-confirm');
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

            // The bulk delete's own confirmation (X-R20): its buttons are looked up inside it, never page-wide.
            const dialog = await openBulkDelete(page);
            await expect(dialog.getByTestId('confirm-modal-message')).toBeVisible();
            await dialog.getByTestId('confirm-modal-confirm').click();

            // The dialog switches to results mode (a Close button) once the delete
            // has run — that transition is the signal the API call completed.
            await expect(dialog.getByTestId('confirm-modal-close')).toBeVisible({timeout: 15_000});
            await dialog.getByTestId('confirm-modal-close').click();
            await expect(page.getByTestId('asset-bulk-delete-confirm'), 'Close closes the bulk confirmation').toHaveCount(0);

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

        const dialog = await openSingleDelete(page, asset.id);
        // The list row counts no transaction (tx_count 0), so the dialog asks first (X-R18); the backend still decides,
        // and its refusal lands in the same dialog.
        await expect(dialog.getByTestId('confirm-modal-confirm')).toBeVisible();
        await dialog.getByTestId('confirm-modal-confirm').click();

        const link = dialog.getByTestId('asset-delete-transactions-link');
        await expect(link).toBeVisible();
        await expect(link).toHaveAttribute('href', `/transactions?asset_id=${asset.id}`);
        await expect(dialog.getByTestId('asset-delete-transactions-link-detail')).toContainText('(17)');
        // The link's own label must be the real transactions.title catalogue entry —
        // never the missing `nav.transactions` key, and never a raw key at all
        // (svelte-i18n renders a missing key as the literal key string, so this
        // check catches that regression by construction rather than by name).
        await expect(link).toHaveText(t('en', 'transactions.title'));
        await expect(link).not.toContainText('nav.transactions');
        await expect(link).not.toContainText('transactions.title');
        await expect(dialog.getByTestId('confirm-modal-close')).toBeVisible();
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

        const dialog = await openSingleDelete(page, asset.id);
        await expect(dialog.getByTestId('confirm-modal-confirm')).toBeVisible();
        await dialog.getByTestId('confirm-modal-confirm').click();

        // Closed: the confirmation itself is gone — not only its Delete, which its results mode lacks too.
        await expect(page.getByTestId('asset-delete-confirm')).toHaveCount(0);
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
        const dialog = await openBulkDelete(page);
        await dialog.getByTestId('confirm-modal-confirm').click();

        for (const {asset, count} of blocked) {
            const testId = `asset-bulk-delete-transactions-${asset.id}`;
            const link = dialog.getByTestId(testId);
            await expect(link).toHaveAttribute('href', `/transactions?asset_id=${asset.id}`);
            await expect(dialog.getByTestId(`${testId}-detail`)).toContainText(`(${count})`);
            // Same catalogue-key contract as the single-delete case, checked once
            // per row so a per-asset action never falls back to a raw key either.
            await expect(link).toHaveText(t('en', 'transactions.title'));
            await expect(link).not.toContainText('transactions.title');
        }
        await expect(dialog.getByTestId('confirm-modal-close')).toBeVisible();
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
        const dialog = await openBulkDelete(page);
        await dialog.getByTestId('confirm-modal-confirm').click();

        await expect(dialog.getByTestId('confirm-modal-close')).toBeVisible();
        await expect(dialog.getByTestId(`asset-bulk-delete-transactions-${asset.id}`)).toHaveCount(0);
        // The raw backend message is shown as-is (no synthesized count suffix).
        await expect(dialog.getByText('Deletion refused by a non-transaction constraint')).toBeVisible();
        await expect(dialog.getByText('Deletion refused by a non-transaction constraint (', {exact: false})).toHaveCount(0);
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
// Each card's Δ over the range is the backend's (workstream Y, lot X-R59 A)
// ============================================================================

/** An asset of a period-changes request (`FAPeriodChangesQueryItem`), with the first day of the range it asks the Δ over. */
type AssetRangeChangesQuery = AssetPeriodChangesQuery & {range_start?: string | null};

/** An asset's Δ over the range as a stub answers it (`FARangeChange`): decimal strings, null where the backend has none. */
type AssetRangeChange = {change_abs: string | null; change_ratio: string | null};

/** +42.42 % over the range, +12.34 in the asset's currency: an asset of the test's own has no price, so no browser could compute them. */
const STUBBED_RANGE_CHANGE: AssetRangeChange = {change_abs: '12.34', change_ratio: '0.4242'};

/** A Δ over the range the backend could not compute: every field null. */
const NO_RANGE_CHANGE: AssetRangeChange = {change_abs: null, change_ratio: null};

/** The first day the backend values (`EARLIEST_RANGE_START`): it refuses an earlier `range_start`, and the whole request with it. */
const EARLIEST_RANGE_START = '1900-01-01';

/** What `routeAssetRangeChanges` saw: every item asked, what went wrong, how many requests it answered. */
type AssetRangeChangesLog = {asked: AssetRangeChangesQuery[]; failures: string[]; answered: number};

/**
 * The asset period changes, routed through the backend: every request is recorded, and each answer goes back with the
 * `range_change` of the assets `stubs` names replaced, every other item as the backend gave it. A non-OK answer is a
 * failure, passed on as it came.
 */
async function routeAssetRangeChanges(page: Page, stubs: ReadonlyMap<number, AssetRangeChange>): Promise<AssetRangeChangesLog> {
    const log: AssetRangeChangesLog = {asked: [], failures: [], answered: 0};
    await page.route(ASSET_PERIOD_CHANGES, async (route) => {
        try {
            log.asked.push(...((route.request().postDataJSON() as AssetRangeChangesQuery[] | null) ?? []));
            const response = await route.fetch();
            if (!response.ok()) {
                log.failures.push(`HTTP ${response.status()}: ${await response.text()}`);
                await route.fulfill({response});
                return;
            }
            const answer = (await response.json()) as {items?: Array<{asset_id: number; range_change?: Record<string, unknown> | null}>};
            const items = (answer.items ?? []).map((item) => {
                const stub = stubs.get(item.asset_id);
                return stub ? {...item, range_change: {...(item.range_change ?? {}), ...stub}} : item;
            });
            await route.fulfill({response, json: {...answer, items}});
        } catch (error) {
            // Nobody awaits a route callback, so what it throws would land on whatever runs next: recorded, and the
            // request let through, for the test to fail on its own assertions.
            log.failures.push(String(error));
            await route.continue().catch(() => undefined);
        } finally {
            log.answered += 1;
        }
    });
    return log;
}

/** An asset of this test's own, in euros and with no price: whatever Δ its card shows can only come from an answer. */
async function createOwnAsset(page: Page, displayName: string): Promise<number> {
    const response = await page.request.post('/api/v1/assets', {data: [{display_name: displayName, currency: 'EUR', asset_type: 'STOCK'}]});
    const text = await response.text();
    expect(response.ok(), `create the asset ${displayName}: HTTP ${response.status()} ${text}`).toBe(true);
    const created = (JSON.parse(text) as {results?: Array<{display_name?: string; success?: boolean; asset_id?: number | null}>}).results?.find((result) => result.display_name === displayName);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`the asset ${displayName} was not created: ${text}`);
    return created.asset_id;
}

/** The list over `range`, as cards, narrowed by `token` to the assets of this test. */
async function openOwnCards(page: Page, range: {start: string; end: string}, token: string): Promise<Locator> {
    await goToAssetsPage(page, range);
    const assetsPage = page.getByTestId('assets-page');
    await page.getByTestId('view-mode-grid').click();
    await page.getByTestId('assets-search-input').fill(token);
    await waitForSettled(assetsPage, 20_000);
    return assetsPage;
}

/**
 * A card's Δ in percent as any of the four languages writes it, matched whole: the arrow of its sign (▲, ▼), then the
 * percentage as `percentCell` reads it.
 */
function arrowedPercent(figure: string): RegExp {
    return new RegExp(`^\\s*${figure.startsWith('-') ? '▼' : '▲'}${percentCell(figure).source.slice(1)}`);
}

/**
 * A card's absolute Δ as any of the four languages writes it, matched whole: the arrow of its sign, the signed figure
 * with two decimals and either mark (a minus may be `-` or `−`), then the currency.
 */
function arrowedAmount(figure: string, currency: string): RegExp {
    const parts = /^([+-])(\d+)\.(\d{2})$/.exec(figure);
    if (!parts) throw new Error(`arrowedAmount: ${figure} is not a signed decimal with two digits such as +12.34`);
    const up = parts[1] === '+';
    return new RegExp(`^\\s*${up ? '▲' : '▼'}\\s*${up ? '\\+' : '[-\\u2212]'}${parts[2]}[.,]${parts[3]}\\s*${currency}\\s*$`);
}

/**
 * Each card of the Assets list shows its Δ over the range on screen (X-R59, lot A): the change from the first to the last
 * day of the range, which the backend computes — the `range_change` of `POST /assets/prices/period-changes`, asked with
 * the first day of the range (`range_start`) in every item, raised to 1900-01-01, the first day the backend values, for a
 * range that starts before it. The card shows it in percent (`data-mode="percentage"`), in the asset's currency once
 * switched to absolute values (`data-mode="absolute"`), and draws no Δ where the backend has none. The browser computes
 * none.
 *
 * Observed through the network, as in X-R53: the real answer is fetched and only this test's assets are changed in it,
 * with figures their prices could never give — they have none, created here and deleted at the end. The range is about
 * two months ending on a known day in the past, so no live quote is asked. The range before 1900 is drawn on a synthetic
 * list whose prices the browser answers, so no price series is walked back over a century; its period changes still
 * reach the backend, which says whether it takes the first day asked.
 *
 * Red before the cure of lot A: the request asks no `range_start`, and the card computes its Δ from the prices it loaded
 * — none for an asset of this test's own.
 */
test.describe('Assets list — each card shows the backend’s Δ over the range (X-R59)', () => {
    // A ceiling, never a delay: assets are created, then the list loads its waves — rows, prices, period changes — and
    // settles once more, narrowed to them.
    test.describe.configure({timeout: 60_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('every asset asks the first day of the range on screen; the card shows the answer’s Δ in percent, and in its currency once absolute', async ({page}) => {
        const token = uniqueToken(6);
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const ownIds: number[] = [];
        try {
            const ownId = await createOwnAsset(page, `E2E RangeChange ${token}`);
            ownIds.push(ownId);
            const log = await routeAssetRangeChanges(page, new Map([[ownId, STUBBED_RANGE_CHANGE]]));

            await openOwnCards(page, range, token);
            const card = page.getByTestId(`asset-card-${ownId}`);
            await expect(card, 'the own asset is listed as a card').toBeVisible({timeout: 10_000});
            await expect(card, 'premise: a card opens in percent, the list’s default').toHaveAttribute('data-view-mode', 'percentage');

            // Asked and answered — the page holds `data-busy` until the period changes are in; the poll is a deadline.
            await expect.poll(() => log.answered, {message: 'the Assets list never asked POST /assets/prices/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'the own asset asks its Δ from the first day of the range on screen to the last').toContainEqual(expect.objectContaining({asset_id: ownId, as_of: range.end, range_start: range.start}));
            expect([...new Set(log.asked.map((item) => item.range_start))], 'every asset asks its Δ from the first day of the range on screen').toEqual([range.start]);

            const delta = card.getByTestId('asset-range-delta');
            await expect(delta, 'the card shows the answer’s change_ratio 0.4242 as a percentage').toHaveText(arrowedPercent('+42.42'), {timeout: 10_000});
            await expect(delta).toHaveAttribute('data-mode', 'percentage');

            // The card's own Abs/% switch: the same answer, its change_abs in the asset's currency.
            await card.getByTestId('asset-card-view-toggle').click();
            await expect(card, 'the card shows absolute values').toHaveAttribute('data-view-mode', 'absolute');
            await expect(delta, 'the card shows the answer’s change_abs 12.34, in euros').toHaveText(arrowedAmount('+12.34', 'EUR'));
            await expect(delta).toHaveAttribute('data-mode', 'absolute');
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
            for (const id of ownIds) await page.request.delete(`/api/v1/assets?asset_ids=${id}`).catch(() => {});
        }
    });

    test('an answer with every field null draws no Δ on the card, in percent or absolute', async ({page}) => {
        const token = uniqueToken(6);
        const range = {start: daysAgoIso(70), end: daysAgoIso(10)};
        const ownIds: number[] = [];
        try {
            // The subject is answered with no Δ; the witness with the stub, so its Δ on screen says the answer reached the
            // cards — both are in the same answer.
            const subjectId = await createOwnAsset(page, `E2E RangeChange none ${token}`);
            ownIds.push(subjectId);
            const witnessId = await createOwnAsset(page, `E2E RangeChange witness ${token}`);
            ownIds.push(witnessId);
            const log = await routeAssetRangeChanges(
                page,
                new Map([
                    [subjectId, NO_RANGE_CHANGE],
                    [witnessId, STUBBED_RANGE_CHANGE],
                ]),
            );

            const assetsPage = await openOwnCards(page, range, token);
            const subject = page.getByTestId(`asset-card-${subjectId}`);
            const witness = page.getByTestId(`asset-card-${witnessId}`);
            await expect(subject, 'the subject is listed as a card').toBeVisible({timeout: 10_000});
            await expect(witness, 'the witness is listed as a card').toBeVisible();

            // Presence first: the answer reached the cards — the witness shows its Δ — and the page waits for no other.
            await expect(witness.getByTestId('asset-range-delta'), 'the witness shows the answer’s change_ratio 0.4242').toHaveText(arrowedPercent('+42.42'), {timeout: 10_000});
            await waitForSettled(assetsPage, 20_000);
            expect(log.failures, 'the period changes reached the page').toEqual([]);
            expect(log.asked, 'premise: the subject asks its Δ over the range on screen').toContainEqual(expect.objectContaining({asset_id: subjectId, as_of: range.end, range_start: range.start}));

            // The subject's card is drawn, its own controls with it, and holds no Δ: in percent, then in euros.
            const subjectDelta = subject.getByTestId('asset-range-delta');
            const subjectToggle = subject.getByTestId('asset-card-view-toggle');
            await expect(subject, 'premise: the subject opens in percent').toHaveAttribute('data-view-mode', 'percentage');
            await expect(subjectToggle).toBeVisible();
            await expect(subjectDelta, 'every field of range_change is null: no Δ in percent').toHaveCount(0);

            await subjectToggle.click();
            await expect(subject, 'the subject shows absolute values').toHaveAttribute('data-view-mode', 'absolute');
            await expect(subjectDelta, 'every field of range_change is null: no Δ in the asset’s currency either').toHaveCount(0);
        } finally {
            await page.unrouteAll({behavior: 'ignoreErrors'}).catch(() => undefined);
            for (const id of ownIds) await page.request.delete(`/api/v1/assets?asset_ids=${id}`).catch(() => {});
        }
    });

    test('a range that starts before 1900 asks every Δ from 1900-01-01, which the backend takes', async ({page}) => {
        // A month before the first day the backend values: sent as is, the backend would refuse the whole request.
        const range = {start: '1899-12-01', end: daysAgoIso(10)};
        const asset = syntheticAsset(910_591, 0, 0, {displayName: 'Synthetic range before 1900'});
        try {
            // A synthetic list whose prices the browser answers, empty: no price series is walked back over a century. Its
            // period changes still reach the backend, which says whether it takes the first day asked.
            await mockAssets(page, [asset]);
            const log = await routeAssetRangeChanges(page, new Map([[asset.id, STUBBED_RANGE_CHANGE]]));

            await goToAssetsPage(page, range);
            await page.getByTestId('view-mode-grid').click();
            const card = page.getByTestId(`asset-card-${asset.id}`);
            await expect(card, 'the synthetic asset is listed as a card').toBeVisible({timeout: 10_000});

            await expect.poll(() => log.answered, {message: 'the Assets list never asked POST /assets/prices/period-changes', timeout: 10_000}).toBeGreaterThan(0);
            expect(log.failures, 'the backend took every request: none asks a day before the first it values').toEqual([]);
            expect(log.asked, `the asset asks its Δ from ${EARLIEST_RANGE_START} to the last day of the range`).toContainEqual(expect.objectContaining({asset_id: asset.id, as_of: range.end, range_start: EARLIEST_RANGE_START}));
            expect([...new Set(log.asked.map((item) => item.range_start))], `every asset asks its Δ from ${EARLIEST_RANGE_START}, never from ${range.start}`).toEqual([EARLIEST_RANGE_START]);
            await expect(card.getByTestId('asset-range-delta'), 'the Δ over the range still reaches the card').toHaveText(arrowedPercent('+42.42'), {timeout: 10_000});
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

// ============================================================================
// A delete that transactions block opens already blocked (workstream X, lot X-R18)
// ============================================================================

/** The delete of assets, single or bulk — `DELETE /api/v1/assets?asset_ids=…` — whatever its query. */
function isAssetDelete(request: Request): boolean {
    return request.method() === 'DELETE' && new URL(request.url()).pathname === '/api/v1/assets';
}

/**
 * Every asset delete the page sends from now on, by URL. Only the page's own requests: what the test sends through
 * `page.request` — its setup, its cleanup — never reaches this listener.
 */
function recordAssetDeletes(page: Page): string[] {
    const sent: string[] = [];
    page.on('request', (request) => {
        if (isAssetDelete(request)) sent.push(request.url());
    });
    return sent;
}

/**
 * A broker of this test's own and, on it, one BUY of `assetId`: the asset's only transaction. The broker is recorded in
 * `owned` before its result is checked, so `deleteOwned` takes it — and, with `force`, the BUY — whatever fails after.
 * The broker may overdraw, so the BUY needs no deposit before it.
 */
async function buyOnOwnBroker(page: Page, owned: Owned, assetId: number): Promise<void> {
    const brokerName = `E2E DeleteBlocked broker ${uniqueSuffix()}`;
    const brokers = await jsonFrom<{results: Array<{broker_id?: number | null; name: string; success: boolean}>}>(await page.request.post('/api/v1/brokers', {data: [{name: brokerName, allow_cash_overdraft: true}]}), 'create the owned broker');
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`the owned broker ${brokerName} was not created: ${JSON.stringify(brokers)}`);
    const committed = await jsonFrom<{committed: boolean}>(
        await page.request.post('/api/v1/transactions/commit', {
            data: {creates: [{broker_id: broker.broker_id, asset_id: assetId, type: 'BUY', date: daysAgoIso(20), quantity: '2', cash: {code: 'EUR', amount: '-20'}, description: `${brokerName} BUY`}]},
        }),
        'commit the BUY of the owned asset',
    );
    expect(committed.committed, `the BUY of asset ${assetId} is committed: ${JSON.stringify(committed)}`).toBe(true);
}

/** The asset as the list loads it — `GET /assets/query`, the page's own source — with the `tx_count` its delete opens on. */
async function listedAsset(page: Page, assetId: number, search: string): Promise<{id: number; tx_count?: number}> {
    const rows = await jsonFrom<Array<{id: number; tx_count?: number}>>(await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(search)}`), `list the assets named after ${search}`);
    const row = rows.find((item) => item.id === assetId);
    if (!row) throw new Error(`asset ${assetId} is not among the assets named after ${search}: ${JSON.stringify(rows)}`);
    return row;
}

/** Opens an asset's single delete from its card, through the card's bin (X-R20). Ends on that confirmation on screen, and returns it. */
async function openCardDelete(page: Page, assetId: number): Promise<Locator> {
    const bin = page.getByTestId(`asset-card-${assetId}`).getByTestId('asset-card-delete-btn');
    await expect(bin, `the bin on the card of asset ${assetId}`).toBeVisible({timeout: 10_000});
    await bin.click();
    await expect(page.getByTestId('asset-delete-confirm'), 'the single delete opens its own confirmation').toBeVisible();
    return deleteConfirm(page, 'asset-delete-confirm');
}

/** A range in the past, as in X-R53: the list polls no live price over it, so no provider is asked and nothing is written. */
function pastRange(): {start: string; end: string} {
    return {start: daysAgoIso(70), end: daysAgoIso(10)};
}

/**
 * A delete the backend would refuse opens already refused (X-R18). The backend refuses to delete an asset that any
 * transaction uses, on any broker, and the list row already counts them: its `tx_count`. Above 0, the single delete opens
 * straight on the outcome that refusal would give — the blocked row with its link to the asset's transactions
 * (`asset-delete-transactions-link`), and a Close — with no Delete to press (`confirm-modal-confirm`) and no request
 * sent. At 0 it opens the usual confirmation and the backend still decides: the two single-delete tests of «Asset List
 * Page» take that path to both of its outcomes, a refusal and a delete.
 *
 * Each test owns its data, created through the API: an asset and, for the blocked case, a broker of the test's own with
 * one BUY of it — the asset's one transaction — read back through `GET /assets/query`, the endpoint the list loads, as
 * the premise. Both ways into the delete are taken: the card's bin hands the page the card's own fields, the list row its
 * table row, and neither carries `tx_count`. The asset delete is watched with `page.on('request')` from before the page
 * loads. Afterwards `deleteOwned` removes the broker first (`force` takes the BUY), then the asset.
 *
 * Red today: the dialog opens on its confirmation, with Delete, and the link comes only once the backend has refused —
 * and, until X-R20, neither the card's bin nor the dialog has a test id to be found by.
 */
test.describe('Assets list — a delete that transactions block opens already blocked (X-R18)', () => {
    // A ceiling, never a delay: the data is created through the API, then the list loads its waves and settles, narrowed
    // to the test's own asset.
    test.describe.configure({timeout: 60_000});

    /** What the running test created; deleted after it, whatever its outcome. */
    let owned: Owned = {assetIds: [], brokerIds: []};

    test.beforeEach(async ({page}) => {
        owned = {assetIds: [], brokerIds: []};
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        await deleteOwned(page, owned);
    });

    for (const entry of ['card', 'list row'] as const) {
        test(`an asset with a transaction: its delete from its ${entry} opens on the blocked row and its transactions link — no Delete, no request`, async ({page}) => {
            const token = uniqueToken(6);
            const assetId = await createOwnAsset(page, `E2E DeleteBlocked ${token}`);
            owned.assetIds.push(assetId);
            await buyOnOwnBroker(page, owned, assetId);
            expect((await listedAsset(page, assetId, token)).tx_count, 'premise: the list row counts the one transaction of the asset').toBe(1);

            // Watched from before the page loads: no asset delete may leave it.
            const deletes = recordAssetDeletes(page);
            await openOwnCards(page, pastRange(), token);
            const dialog = entry === 'card' ? await openCardDelete(page, assetId) : await openSingleDelete(page, assetId);

            // Its header is on screen, and ConfirmModal draws its footer with it: no Delete to press…
            await expect(dialog.getByTestId('confirm-modal-confirm'), 'a delete the backend would refuse offers no Delete').toHaveCount(0);
            // …but the blocked row, with its link filtered on this asset and the count of the list row…
            const link = dialog.getByTestId('asset-delete-transactions-link');
            await expect(link, 'the link to the asset’s transactions is there as the dialog opens, with no Delete pressed').toBeVisible();
            await expect(link).toHaveAttribute('href', `/transactions?asset_id=${assetId}`);
            await expect(dialog.getByTestId('asset-delete-transactions-link-detail'), 'the count of the list row: one transaction').toContainText('(1)');
            // …and a Close.
            await expect(dialog.getByTestId('confirm-modal-close')).toBeVisible();
            expect(deletes, 'opening the dialog sends no DELETE /api/v1/assets').toEqual([]);

            // Closed from there: the asset is still listed, and still nothing was sent.
            await dialog.getByTestId('confirm-modal-close').click();
            await expect(page.getByTestId('asset-delete-confirm')).toHaveCount(0);
            const listed = entry === 'card' ? page.getByTestId(`asset-card-${assetId}`) : page.locator(`tbody tr[data-row-id="${assetId}"]`);
            await expect(listed, 'the asset is still listed').toBeVisible();
            expect(deletes, 'closing it sends none either').toEqual([]);
        });
    }

    test('guard: an asset with no transaction opens the usual confirmation from its card — Delete offered, nothing sent by opening', async ({page}) => {
        const token = uniqueToken(6);
        const assetId = await createOwnAsset(page, `E2E DeleteFree ${token}`);
        owned.assetIds.push(assetId);
        expect((await listedAsset(page, assetId, token)).tx_count, 'premise: the list row counts no transaction').toBe(0);

        const deletes = recordAssetDeletes(page);
        await openOwnCards(page, pastRange(), token);
        const dialog = await openCardDelete(page, assetId);

        await expect(dialog.getByTestId('confirm-modal-confirm'), 'no transaction: the usual Delete, for the backend to decide on').toBeVisible();
        await expect(dialog.getByTestId('confirm-modal-message')).toBeVisible();
        await expect(dialog.getByTestId('asset-delete-transactions-link'), 'and no blocked row').toHaveCount(0);
        expect(deletes, 'opening the dialog sends nothing: only Delete asks the backend').toEqual([]);

        await dialog.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('asset-delete-confirm')).toHaveCount(0);
        await expect(page.getByTestId(`asset-card-${assetId}`), 'the asset is still listed').toBeVisible();
        expect(deletes, 'cancelling sends none either').toEqual([]);
    });
});

// ============================================================================
// The table's fixed columns keep the colour of their row, opaque, in every row state (DataTable, 19/10)
// ============================================================================

/** Each theme is a test of its own: a red names the theme it belongs to. */
const FIXED_COLUMN_THEMES = ['light', 'dark'] as const;

/**
 * Where a cell is read: this many CSS pixels in from its top-left corner. That is inside the padding DataTable gives every
 * cell (`td`: 0.625rem = 10 px above, 0.5rem = 8 px on the left), 3 px clear of the 1 px border of the row above, and clear
 * of whatever the cell holds — text, a badge, the checkbox, the ⋮ button all sit lower, centred in the row. So the pixel
 * read is the cell's background and nothing else.
 */
const CELL_INSET = 4;

/**
 * Two pixels painted from the same layers agree within this, per channel (0–255). On the fix a fixed cell paints exactly
 * what its row paints — the card, and the state's tint over it — so only rasterisation separates the two pixels: Chromium
 * draws a pinned cell (sticky, z-index 5) in a layer of its own and blends the tint there, and two 8-bit blends of one
 * colour may round 1 apart. The defect lies far outside the margin: a tint drawn twice moves some channel by 7 at the least
 * (the 6 % hover tint of a clickable row, dark theme) and by 23 for the selection in light (223,233,228 in a data cell,
 * 200,218,209 in a fixed one, measured 19/10); the deeper tint of a pulse's beat moves some channel by 10 or more from the
 * row at rest, in both themes.
 */
const SAME_PAINT = 2;

/** The five rows of the measurement, one per state, all in the analysis panel (no transaction, held by nobody). */
const FIXED_PLAIN = syntheticAsset(910_201, 0, 0, {displayName: 'Fixed columns plain'});
const FIXED_SELECTED = syntheticAsset(910_202, 0, 0, {displayName: 'Fixed columns selected'});
const FIXED_INACTIVE = syntheticAsset(910_203, 0, 0, {displayName: 'Fixed columns inactive', active: false});
const FIXED_ANALYZED = syntheticAsset(910_204, 0, 0, {displayName: 'Fixed columns analyzed'});
const FIXED_HIGHLIGHTED = syntheticAsset(910_205, 0, 0, {displayName: 'Fixed columns highlighted'});
const FIXED_COLUMN_ROWS = [FIXED_PLAIN, FIXED_SELECTED, FIXED_INACTIVE, FIXED_ANALYZED, FIXED_HIGHLIGHTED];

/** A colour on screen: its sRGB channels, 0–255. */
type Rgb = readonly [number, number, number];
type ScreenPoint = {x: number; y: number};

/** The two fixed cells of a DataTable row, by the handles DataTable publishes: the selection cell pinned left, the actions cell pinned right. */
const FIXED_CELLS = [
    {name: 'selection', side: 'left', testId: (rowId: number) => `dt-select-cell-${rowId}`},
    {name: 'actions', side: 'right', testId: (rowId: number) => `dt-actions-cell-${rowId}`},
] as const;

/** One fixed cell, read in the state its row is in. */
interface FixedCellReading {
    cell: (typeof FIXED_CELLS)[number]['name'];
    /** The fixed cell's computed `background-color`, as Chrome serialises it. */
    css: string;
    /** Its alpha (0–1) as a canvas paints it; null when the canvas refuses the text. */
    alpha: number | null;
    /** What the screen shows inside the fixed cell's padding. */
    fixed: Rgb;
    /** What the screen shows inside the padding of an ordinary data cell of the same row, at the same moment. */
    normal: Rgb;
    /** That data cell's column. */
    column: string;
}

/** Where one fixed cell is read, beside an ordinary data cell of the same row that is on screen with it. */
interface FixedCellProbe {
    fixed: ScreenPoint;
    normal: ScreenPoint;
    column: string;
    /** Where the pointer rests to hover the row: the same data cell's bottom padding, away from both pixels read. */
    pointer: ScreenPoint;
    /** The fixed cell's computed `position`. */
    position: string;
    /** The table runs on beyond the fixed cell on its pinned side: there is scrolled content under the cell. */
    overScrolledTable: boolean;
}

/** The largest gap between two colours, over their three channels. */
function channelGap(a: Rgb, b: Rgb): number {
    return Math.max(...a.map((value, index) => Math.abs(value - b[index])));
}

function rgb(colour: Rgb): string {
    return `rgb(${colour.join(', ')})`;
}

/** One class of a row, matched whole. */
function rowClass(name: string): RegExp {
    return new RegExp(`(?:^|\\s)${name}(?:\\s|$)`);
}

/**
 * The alpha (0–1) of a CSS colour as a canvas paints it, run in the page. Chrome serialises a computed colour in the notation
 * it was written in — `rgb()`, `rgba()`, `oklab(… / a)` for a mix, `color(srgb …)` — and a canvas paints them all as the
 * colours they are: the text is set as the fill style (twice, from two different values: a text the canvas refuses leaves
 * each in place), one pixel is filled and its alpha byte read back. Null for a text the canvas refuses.
 */
const PAINTED_ALPHA = (css: string): number | null => {
    const canvas = document.createElement('canvas');
    canvas.width = 1;
    canvas.height = 1;
    const context = canvas.getContext('2d', {willReadFrequently: true});
    if (!context) return null;
    context.fillStyle = '#000000';
    context.fillStyle = css;
    const first = String(context.fillStyle);
    context.fillStyle = '#ffffff';
    context.fillStyle = css;
    if (String(context.fillStyle) !== first) return null;
    context.clearRect(0, 0, 1, 1);
    context.fillRect(0, 0, 1, 1);
    return context.getImageData(0, 0, 1, 1).data[3] / 255;
};

/**
 * The colour the screen shows at one CSS pixel: what is painted, not what is computed. A 1×1 screenshot there, decoded in
 * the page — the e2e dependencies hold no PNG decoder — through `createImageBitmap`: no fetch (so no CSP), and no colour
 * conversion, so the bytes read are the bytes the screenshot holds. A screenshot moves no pointer, and with
 * `animations: 'allow'` it leaves a held animation where it is (`'disabled'` would play the pulse to its end); `caret:
 * 'initial'` spares the page the style Playwright injects to hide the caret.
 */
async function screenPixel(page: Page, point: ScreenPoint): Promise<Rgb> {
    const png = await page.screenshot({clip: {x: point.x, y: point.y, width: 1, height: 1}, scale: 'css', animations: 'allow', caret: 'initial'});
    return page.evaluate(async (base64) => {
        const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0));
        const bitmap = await createImageBitmap(new Blob([bytes], {type: 'image/png'}), {colorSpaceConversion: 'none', premultiplyAlpha: 'none'});
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const context = canvas.getContext('2d', {willReadFrequently: true});
        if (!context) throw new Error('no 2D canvas to decode the screenshot on');
        context.drawImage(bitmap, 0, 0);
        bitmap.close();
        const [red, green, blue] = context.getImageData(Math.floor(canvas.width / 2), Math.floor(canvas.height / 2), 1, 1).data;
        return [red, green, blue] as const;
    }, png.toString('base64'));
}

/**
 * The row has stopped changing colour: every transition of its own — the 0.15 s fade from one state to the next, of
 * `--dt-row-tint` on the fix and of `background` before it — has ended, so the screen shows the state and not a frame of
 * the fade. A condition, not a delay: `getAnimations()` brings the row's style up to date first, so the fade the last
 * pointer move, class or theme change started is among those awaited, and one a later change replaced is read again. CSS
 * animations are left alone: the only one a row runs is the highlight's pulse, which the highlighted reads hold themselves.
 */
async function rowFadesEnded(row: Locator): Promise<void> {
    await row.evaluate(async (element) => {
        const fading = () => element.getAnimations().filter((animation) => animation instanceof CSSTransition && animation.playState === 'running');
        for (let running = fading(); running.length > 0; running = fading()) {
            await Promise.all(running.map((animation) => animation.finished.catch(() => undefined)));
        }
    });
}

/**
 * Where one fixed cell of the row is read. The row is brought to the middle of the screen through its own `scrollIntoView`:
 * a row is wider than the table's scroll area, so `inline: 'nearest'` leaves the sideways scroll alone — the cell's own
 * would not, where it is pinned: a scroll aimed at a sticky box aims at its unshifted place (CSS Positioned Layout 3,
 * §3.4.1), and the table would lose the half-way scroll it was given. A cell that scrolls with the table (phone width) is
 * then brought into view on its own. Its point is checked to be on screen and to be the cell's own (`elementFromPoint`: no
 * header, toolbar or other cell lies over it); the ordinary data cell beside it is the first of the row whose point — and
 * pointer spot — pass the same check, which rules out a cell scrolled out of the table's view or passing under a pinned one.
 */
async function fixedCellProbe(row: Locator, testId: string, side: 'left' | 'right', pinned: boolean): Promise<FixedCellProbe> {
    const cell = row.getByTestId(testId);
    await expect(cell, `the row draws its ${testId}`).toHaveCount(1);
    await row.evaluate((element) => element.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'}));
    if (!pinned) await cell.evaluate((element) => element.scrollIntoView({block: 'nearest', inline: 'nearest', behavior: 'instant'}));
    const probe = await row.evaluate(
        (tr, {id, pinSide, inset}) => {
            const fixedCell = tr.querySelector<HTMLElement>(`[data-testid="${id}"]`);
            const table = tr.closest('table');
            if (!fixedCell || !table) return `the row has no ${id} inside a table`;
            const shows = (element: Element, point: {x: number; y: number}) => {
                const hit = document.elementFromPoint(point.x, point.y);
                return hit !== null && element.contains(hit);
            };
            const box = fixedCell.getBoundingClientRect();
            const fixed = {x: Math.round(box.left + inset), y: Math.round(box.top + inset)};
            if (!shows(fixedCell, fixed)) return `${id}: at (${fixed.x}, ${fixed.y}) the screen shows ${document.elementFromPoint(fixed.x, fixed.y)?.outerHTML.slice(0, 160) ?? 'nothing'}, not the cell`;
            const tableBox = table.getBoundingClientRect();
            const overScrolledTable = pinSide === 'left' ? tableBox.left < box.left - 1 : tableBox.right > box.right + 1;
            for (const dataCell of tr.querySelectorAll<HTMLElement>('td.td-data:not(.td-fixed)')) {
                const dataBox = dataCell.getBoundingClientRect();
                const normal = {x: Math.round(dataBox.left + inset), y: Math.round(dataBox.top + inset)};
                const pointer = {x: normal.x, y: Math.round(dataBox.bottom - inset - 1)};
                if (shows(dataCell, normal) && shows(dataCell, pointer)) {
                    return {fixed, normal, column: dataCell.dataset.columnId ?? '(no column id)', pointer, position: getComputedStyle(fixedCell).position, overScrolledTable};
                }
            }
            return `${id}: no ordinary data cell of the row is on screen beside it`;
        },
        {id: testId, pinSide: side, inset: CELL_INSET},
    );
    if (typeof probe === 'string') throw new Error(probe);
    return probe;
}

/**
 * Both fixed cells of the row, read in the state the row is in, with the pointer on the row or away from it. For each: where
 * the pins are on, the cell is pinned and sits over the table scrolled beneath it (preconditions, hard); the pointer is
 * placed and the row's `:hover` read back; the row's fades end; then the cell's computed background and the two pixels.
 */
async function readFixedCells(page: Page, row: Locator, rowId: number, how: {what: string; hovered: boolean; pinned: boolean}): Promise<FixedCellReading[]> {
    const readings: FixedCellReading[] = [];
    for (const fixedCell of FIXED_CELLS) {
        const testId = fixedCell.testId(rowId);
        const probe = await fixedCellProbe(row, testId, fixedCell.side, how.pinned);
        if (how.pinned) {
            expect(probe.position, `${how.what}: above 768 px the ${fixedCell.name} cell is pinned`).toBe('sticky');
            expect(probe.overScrolledTable, `${how.what}: the ${fixedCell.name} cell sits over the table scrolled beneath it, as in the report`).toBe(true);
        }
        // The pointer on the row (an ordinary cell's bottom padding: a screenshot does not move it, so the row stays hovered
        // while it is read), or parked where nothing reacts to it.
        if (how.hovered) await page.mouse.move(probe.pointer.x, probe.pointer.y);
        else await parkPointer(page);
        await expect.poll(() => row.evaluate((element) => element.matches(':hover')), {message: `${how.what}: ${how.hovered ? 'the pointer is on the row' : 'no pointer is on the row'}`}).toBe(how.hovered);
        await rowFadesEnded(row);
        const css = await row.getByTestId(testId).evaluate((element) => getComputedStyle(element).backgroundColor);
        const alpha = await page.evaluate(PAINTED_ALPHA, css);
        const fixed = await screenPixel(page, probe.fixed);
        const normal = await screenPixel(page, probe.normal);
        readings.push({cell: fixedCell.name, css, alpha, fixed, normal, column: probe.column});
    }
    return readings;
}

/**
 * The two verdicts of a state, for each fixed cell, soft so that one run lists every state that fails: (1) opaque — the
 * computed background has alpha 1, so nothing scrolled under the cell can show through; (2) no seam — the screen shows
 * the cell in the colour it shows an ordinary cell of the row, within {@link SAME_PAINT}.
 */
function expectFixedCellsLikeTheRow(readings: FixedCellReading[], what: string): void {
    for (const reading of readings) {
        expect.soft(reading.alpha, `${what}: the ${reading.cell} cell is opaque, so nothing scrolled under it shows through — its computed background-color is ${reading.css}`).toBe(1);
        expect.soft(channelGap(reading.fixed, reading.normal), `${what}: the ${reading.cell} cell shows the colour of its row — it shows ${rgb(reading.fixed)} where the row's ${reading.column} cell shows ${rgb(reading.normal)}`).toBeLessThanOrEqual(SAME_PAINT);
    }
}

/** Reads both fixed cells of the row in its present state and gives the verdicts; returns the readings. */
async function expectRowState(page: Page, row: Locator, rowId: number, how: {what: string; hovered: boolean; pinned: boolean}): Promise<FixedCellReading[]> {
    const readings = await readFixedCells(page, row, rowId, how);
    expectFixedCellsLikeTheRow(readings, how.what);
    return readings;
}

/**
 * The fixed columns of the asset table — the selection cell pinned left, the actions cell (⋮) pinned right — are opaque and
 * the colour of their row, whatever the row's state, in both themes; and the highlight pulses (DataTable, 19/10).
 *
 * The defect (reported 19/10, on this page's table): under the pointer the pinned Actions column turned transparent, and the
 * row's content scrolling under it showed through instead of the ⋮. Since 77bfa6a39 the row states are translucent colour
 * roles — `--lf-selected`, the focus green at 12 %; a clickable row's hover at 6 %; an analyzed row's hover at 20 % — and
 * `.td-fixed { background: inherit }` copied the translucent colour. A fixed cell also paints its row's background behind
 * itself, so it showed the tint twice: a darker strip down every hovered or selected row. And the highlight pulse
 * (`tr.highlighted`, 3 × 0.6 s) never ran: the row's `background: … !important` beat the animation, 12/07–19/10.
 *
 * The fix: a row paints the card and, over it, the tint of its state (`--dt-row-tint`, a registered colour) as one image
 * layer, so the row is opaque; a fixed cell inherits both layers and paints what its row paints. A state sets the tint
 * only, the pulse animates it, and AssetTable's inactive row sets it too.
 *
 * ## What is read: for each fixed cell, in each state, in each theme
 *
 * 1. Opaque: the fixed cell's computed `background-color` has alpha 1 ({@link PAINTED_ALPHA}).
 * 2. No seam: the colour the SCREEN shows inside the fixed cell's padding is the colour it shows inside an ordinary data
 *    cell of the same row, at the same moment, within {@link SAME_PAINT} per channel ({@link screenPixel}). The painted
 *    pixels, because the defect is in the painting: the computed colours of the two cells say nothing of the row's
 *    background drawn behind the fixed one.
 * 3. The pulse, on the highlighted row: the class starts a CSS animation; held at the middle of a beat, the row is deeper
 *    than once the pulse has ended, and the fixed cells are the colour of the row at that moment too.
 *
 * Positive controls keep the readers honest: a row at rest reads the same in both cells on any code (the points read are
 * backgrounds), a selected row reads apart from a row at rest (the pixel reader sees a tint), and the selection role reads
 * translucent (the alpha reader sees a translucency).
 *
 * ## The states
 *
 * Reached as a user reaches them: a row under the pointer (asset rows open their asset, so DataTable makes them `clickable`:
 * `tr.clickable:hover`); a selected row, its checkbox ticked, at rest and under the pointer; an inactive asset's row
 * (`asset-row-inactive`), at rest and under the pointer. Two states of DataTable the asset table never sets are put on rows
 * of this same table the way their consumers put them: `row-analyzed`, what the dashboard tables' `getRowClass` returns, and
 * `highlighted`, what `navigateToRowId` adds (a real highlight also writes `data-highlighted`, which no style reads). Sound:
 * Svelte (5.48, `set_class`) rewrites a row's class attribute only when the class string it computes changes, and nothing
 * here changes it for those rows — no selection, no click on them, and `getRowClass` reads only `active`. Each is checked
 * to still be on its row after its reads, so a redraw would be a red, not the reading of another state.
 *
 * ## Where the cells are pinned
 *
 * The runner runs this action on the desktop project only (1280 px): there the cells are pinned, and the list's columns
 * (1,022 px at the least: 48 + 220 + 60 + 70 + 90 + 150 + 80 + 240 + 64, more with each Δ period) are wider than its scroll
 * area beside the open sidebar (about 974 px), so the table is scrolled half way and both pinned cells sit over table
 * scrolled beneath them, as in the report — checked at every read. At phone width (768 px or less, D-Y17) the pins are off:
 * the cells scroll with the table and each is brought into view to be read; 1 and 2 hold there too, the pinning is not asked.
 *
 * Red on the code before the fix: the translucent states fail 1 (alpha 0.06, 0.12, 0.2; 0.5 for the inactive row under the
 * pointer) and 2 (the tint drawn twice), and the pulse fails 3 (no change: it never ran). A row at rest and an inactive row
 * at rest were opaque already: they pass on both codes, and guard the fix.
 *
 * Nothing is written: the list is mocked (`goToMockedAssets`), and the theme toggle keeps its choice in this browser
 * context's localStorage, never in the user's settings. No clock: a read waits for the row's `:hover` state and for its own
 * fades to end (`getAnimations()`), and the pulse is held and moved with the Web Animations API.
 */
test.describe('Assets list — the table’s fixed columns stay opaque and the colour of their row, in every row state (19/10)', () => {
    // A ceiling, never a delay: the list loads, then eleven states are read, two cells each, every read waiting for the
    // row's own fade.
    test.describe.configure({timeout: 90_000});

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    for (const theme of FIXED_COLUMN_THEMES) {
        test(`${theme} theme: in every row state the selection and actions cells are opaque and the colour of their row, and the highlight pulses`, async ({page}) => {
            const what = (state: string) => `${theme} theme, ${state}`;
            await goToMockedAssets(page, FIXED_COLUMN_ROWS);
            const assetsPage = page.getByTestId('assets-page');
            // The list shows active assets only until the inactive toggle joins the inactive ones in.
            const inactiveToggle = page.getByTestId('assets-inactive-toggle');
            await inactiveToggle.click();
            await expect(inactiveToggle).toHaveAttribute('aria-pressed', 'true');
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(assetsPage, 20_000);
            // Through the header's toggle, before anything scrolls the header away.
            await chooseTheme(page, theme);

            const panel = page.getByTestId('assets-table-panel-analysis');
            const rowOf = (asset: SyntheticAsset) => panel.locator(`tbody tr[data-row-id="${asset.id}"]`);
            for (const asset of FIXED_COLUMN_ROWS) await expect(rowOf(asset), `${asset.display_name} is a row of the analysis panel's table`).toBeVisible({timeout: 10_000});

            // The highlight pulses only for a browser that asks for no reduced motion (DataTable's `prefers-reduced-motion`).
            expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches), 'the browser asks for no reduced motion').toBe(false);
            // Positive control of the alpha reader: the selection role, translucent by design, reads translucent.
            const selectionRole = await page.evaluate(() => {
                const probe = document.body.appendChild(document.createElement('div'));
                probe.style.setProperty('background-color', 'var(--lf-selected)');
                try {
                    return getComputedStyle(probe).backgroundColor;
                } finally {
                    probe.remove();
                }
            });
            expect(await page.evaluate(PAINTED_ALPHA, selectionRole), `positive control: the alpha reader reads the selection role, ${selectionRole}, as translucent`).toBeLessThan(1);

            // The selected row, ticked as a user ticks it (the checkbox stops the click: the row does not open its asset).
            await panel.getByTestId(`dt-row-checkbox-${FIXED_SELECTED.id}`).click();
            await expect(rowOf(FIXED_SELECTED)).toHaveAttribute('data-selected', 'true');

            // The table scrolled half way: content runs under both pinned cells, as in the report. At phone width each cell is
            // brought into view to be read instead, and this position does not last.
            const pinned = await page.evaluate(() => !matchMedia('(max-width: 768px)').matches);
            const scrollArea = panel.getByTestId('dt-scroll');
            await expect(scrollArea, 'the analysis panel draws one table').toHaveCount(1);
            const overflow = await scrollArea.evaluate((element) => element.scrollWidth - element.clientWidth);
            expect(overflow, 'the table is wider than its scroll area: it scrolls sideways, under its pinned cells').toBeGreaterThan(2 * CELL_INSET);
            await scrollArea.evaluate((element) => {
                element.scrollLeft = Math.round((element.scrollWidth - element.clientWidth) / 2);
            });

            // A row at rest: the card, on any code — the positive control of the points read.
            const plain = rowOf(FIXED_PLAIN);
            await expect(plain, 'asset rows open their asset: DataTable makes them clickable').toHaveClass(rowClass('clickable'));
            await expect(plain).toHaveAttribute('data-selected', 'false');
            const atRest = await expectRowState(page, plain, FIXED_PLAIN.id, {what: what('a row at rest'), hovered: false, pinned});
            await expectRowState(page, plain, FIXED_PLAIN.id, {what: what('a row under the pointer (tr.clickable:hover)'), hovered: true, pinned});

            // A selected row, at rest and under the pointer.
            const selected = rowOf(FIXED_SELECTED);
            const selectedAtRest = await expectRowState(page, selected, FIXED_SELECTED.id, {what: what('a selected row'), hovered: false, pinned});
            // Positive control of the pixel reader: it sees a tint — the ordinary cells of a selected row read apart from those
            // of a row at rest, on any code.
            for (const [index, reading] of selectedAtRest.entries()) {
                expect(channelGap(reading.normal, atRest[index].normal), `positive control: the pixel reader sees the selection tint — beside the ${reading.cell} cell a selected row reads ${rgb(reading.normal)}, a row at rest ${rgb(atRest[index].normal)}`).toBeGreaterThan(SAME_PAINT);
            }
            await expectRowState(page, selected, FIXED_SELECTED.id, {what: what('a selected row under the pointer'), hovered: true, pinned});
            await expect(selected, 'the row stayed selected through its reads').toHaveAttribute('data-selected', 'true');

            // An inactive asset's row: AssetTable's warning tint, at rest and under the pointer. The class is the subject here:
            // it is what AssetTable's getRowClass hands DataTable, and what its style keys on.
            const inactive = rowOf(FIXED_INACTIVE);
            await expect(inactive, 'an inactive asset’s row carries AssetTable’s state').toHaveClass(rowClass('asset-row-inactive'));
            await expectRowState(page, inactive, FIXED_INACTIVE.id, {what: what('an inactive asset’s row'), hovered: false, pinned});
            await expectRowState(page, inactive, FIXED_INACTIVE.id, {what: what('an inactive asset’s row under the pointer'), hovered: true, pinned});

            // An analyzed row (row-analyzed), put on as the dashboard tables' getRowClass puts it, at rest and under the pointer.
            const analyzed = rowOf(FIXED_ANALYZED);
            await analyzed.evaluate((element) => element.classList.add('row-analyzed'));
            await expect(analyzed).toHaveClass(rowClass('row-analyzed'));
            await expectRowState(page, analyzed, FIXED_ANALYZED.id, {what: what('an analyzed row (row-analyzed)'), hovered: false, pinned});
            await expectRowState(page, analyzed, FIXED_ANALYZED.id, {what: what('an analyzed row (row-analyzed) under the pointer'), hovered: true, pinned});
            await expect(analyzed, 'row-analyzed stayed on the row through its reads: nothing redrew it').toHaveClass(rowClass('row-analyzed'));
            await analyzed.evaluate((element) => element.classList.remove('row-analyzed'));

            // A highlighted row, put on as navigateToRowId puts it, with no pointer on it. The class starts the pulse, which is
            // held at once — in the same task, before a frame of it is drawn — so that no speed of the machine decides which
            // beat is read.
            const highlighted = rowOf(FIXED_HIGHLIGHTED);
            await parkPointer(page);
            await expect.poll(() => highlighted.evaluate((element) => element.matches(':hover')), {message: 'no pointer is on the row to highlight'}).toBe(false);
            await rowFadesEnded(highlighted);
            const pulse = await highlighted.evaluate((element) => {
                element.classList.add('highlighted');
                const started = element.getAnimations().filter((animation): animation is CSSAnimation => animation instanceof CSSAnimation);
                const [first] = started;
                const playState = first?.playState;
                for (const animation of started) animation.pause();
                return first ? {name: first.animationName, playState, duration: Number(first.effect?.getComputedTiming().duration)} : null;
            });
            await expect(highlighted).toHaveClass(rowClass('highlighted'));
            expect.soft(pulse, `${what('a highlighted row')}: the class starts a CSS animation, the pulse`).not.toBeNull();
            let beat: FixedCellReading[] | null = null;
            if (pulse) {
                expect.soft(pulse.playState, `${what('a highlighted row')}: its pulse (${pulse.name}) runs as the class lands`).toBe('running');
                expect(pulse.duration, `${what('a highlighted row')}: its pulse (${pulse.name}) beats over a finite time`).toBeGreaterThan(0);
                // The middle of one beat: the deeper tint of the 50 % keyframe (each keyframe's easing ends exactly on it).
                await highlighted.evaluate((element, time) => {
                    for (const animation of element.getAnimations()) if (animation instanceof CSSAnimation) animation.currentTime = time;
                }, pulse.duration / 2);
                beat = await expectRowState(page, highlighted, FIXED_HIGHLIGHTED.id, {what: what('a highlighted row, its pulse held at the middle of a beat'), hovered: false, pinned});
                // Then the pulse is over: played to its end, the row back on its steady tint.
                await highlighted.evaluate((element) => {
                    for (const animation of element.getAnimations()) if (animation instanceof CSSAnimation) animation.finish();
                });
            }
            const steady = await expectRowState(page, highlighted, FIXED_HIGHLIGHTED.id, {what: what('a highlighted row once its pulse has ended'), hovered: false, pinned});
            if (beat) {
                for (const [index, reading] of beat.entries()) {
                    expect
                        .soft(channelGap(reading.normal, steady[index].normal), `${what('a highlighted row')}: the pulse changes the row's colour — at the middle of a beat its ${reading.column} cell shows ${rgb(reading.normal)}, once the pulse has ended ${rgb(steady[index].normal)}`)
                        .toBeGreaterThan(SAME_PAINT);
                }
            }
            await expectRowState(page, highlighted, FIXED_HIGHLIGHTED.id, {what: what('a highlighted row under the pointer'), hovered: true, pinned});
            await expect(highlighted, 'highlighted stayed on the row through its reads: nothing redrew it').toHaveClass(rowClass('highlighted'));
            await highlighted.evaluate((element) => element.classList.remove('highlighted'));
        });
    }
});
