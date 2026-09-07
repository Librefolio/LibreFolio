/**
 * Asset Classification — E2E Tests
 *
 * Tests the distribution editor round-trip: add geo/sector entries → save → reopen → verify persistence.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {goToAssetsPage, openCreateAssetModal} from './assets-helpers';

/** Helper: create asset, return to detail page, open edit modal */
async function createAssetAndOpenEdit(page: import('@playwright/test').Page, name: string) {
    await goToAssetsPage(page);
    await openCreateAssetModal(page);

    // Fill name
    const nameInput = page.getByTestId('asset-modal-display-name');
    await nameInput.fill(name);

    // Save
    const saveBtn = page.getByTestId('asset-modal-save');
    await expect(saveBtn).toBeEnabled({timeout: 5000});
    await saveBtn.click();
    await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

    // Navigate to the new asset via search
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    const searchInput = page.getByTestId('assets-search-input');
    if (await searchInput.isVisible({timeout: 3000}).catch(() => false)) {
        await searchInput.fill(name);
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
    }

    // Click *our* card, not whatever happens to be first: other workers create
    // assets too, and the search filter is debounced, so `.first()` can still be
    // showing the unfiltered list. Matching on the (unique) name is both the
    // ownership guarantee and the barrier — it retries until the list catches up.
    const card = page.locator('[data-testid^="asset-card-"]').filter({hasText: name}).first();
    await expect(card).toBeVisible({timeout: 15_000});
    await card.click();
    await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

    // Open edit modal
    await page.getByTestId('asset-detail-edit-btn').click();
    await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
}

/** Helper: ensure the "More Info" section is expanded (it is a toggle, not a button). */
async function expandMoreInfo(page: import('@playwright/test').Page) {
    // AssetModal opens this section by itself when the asset already carries
    // identifiers (`moreInfoExpanded = identifierRows.length > 0`), so clicking
    // unconditionally would *close* it. Ask for the end state, not the click.
    const editor = page.getByTestId('distribution-editor-geographic');
    if (await editor.isVisible({timeout: 1500}).catch(() => false)) return;
    await page.getByTestId('asset-modal-more-info').click();
    await expect(editor).toBeVisible({timeout: 5000});
}

test.describe('Asset Classification Round-Trip', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Set geographic distribution → save → reopen → present
    // ========================================================================
    test('geo distribution persists after save and reopen', async ({page}) => {
        const assetName = `E2E Geo Test ${Date.now()}`;
        await createAssetAndOpenEdit(page, assetName);

        // Expand More Info
        await expandMoreInfo(page);

        // Add geographic entry
        const addGeoBtn = page.getByTestId('distribution-add-geographic');
        await addGeoBtn.click();

        // The new entry should appear in the distribution editor
        const geoEditor = page.getByTestId('distribution-editor-geographic');
        await expect(geoEditor).toBeVisible();

        // Verify total badge is visible (entry was added)
        const geoTotal = page.getByTestId('distribution-total-geographic');
        await expect(geoTotal).toBeVisible({timeout: 10_000});

        // Save
        await page.getByTestId('asset-modal-save').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Reopen edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Expand More Info again
        await expandMoreInfo(page);

        // Verify that the geographic distribution is still present
        const geoTotalAfter = page.getByTestId('distribution-total-geographic');
        await expect(geoTotalAfter).toBeVisible({timeout: 3000});

        // Close modal
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 2: Set sector distribution → save → reopen → present
    // ========================================================================
    test('sector distribution persists after save and reopen', async ({page}) => {
        const assetName = `E2E Sector Test ${Date.now()}`;
        await createAssetAndOpenEdit(page, assetName);

        // Expand More Info
        await expandMoreInfo(page);

        // Add sector entry
        const addSectorBtn = page.getByTestId('distribution-add-sector');
        await addSectorBtn.click();

        // Verify total badge appears
        const sectorTotal = page.getByTestId('distribution-total-sector');
        await expect(sectorTotal).toBeVisible({timeout: 10_000});

        // Save
        await page.getByTestId('asset-modal-save').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Reopen
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Expand More Info
        await expandMoreInfo(page);

        // Verify sector distribution still present
        const sectorTotalAfter = page.getByTestId('distribution-total-sector');
        await expect(sectorTotalAfter).toBeVisible({timeout: 3000});

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 3: Clear distribution → save → reopen → empty
    // ========================================================================
    test('clearing distribution persists after save', async ({page}) => {
        const assetName = `E2E Clear Test ${Date.now()}`;
        await createAssetAndOpenEdit(page, assetName);

        // Expand More Info
        await expandMoreInfo(page);

        // Add geo entry. The button's handler is async — it loads the country list on
        // first use — so the row does not exist when the click resolves. Saving before
        // the row lands saves nothing, and the test then blames the reopen. Wait for
        // the total badge, which only renders once there is an entry.
        const addGeoBtn = page.getByTestId('distribution-add-geographic');
        await addGeoBtn.click();
        await expect(page.getByTestId('distribution-total-geographic')).toBeVisible({timeout: 10_000});

        // Save with entry
        await page.getByTestId('asset-modal-save').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Reopen
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
        await expandMoreInfo(page);

        // Confirm entry exists (total badge visible)
        await expect(page.getByTestId('distribution-total-geographic')).toBeVisible({timeout: 3000});

        // Delete the entry via row action. DataTable rows expose a "row-actions-{id}" kebab
        // button that opens a ContextMenu with "context-menu-action-{actionId}" items (see
        // DataTable.svelte / ContextMenu.svelte; same pattern as brokers-detail.spec.ts).
        const geoEditor = page.getByTestId('distribution-editor-geographic');
        const rowActionsBtn = geoEditor.getByTestId(/^row-actions-/).first();
        if (await rowActionsBtn.isVisible({timeout: 2000}).catch(() => false)) {
            await rowActionsBtn.click();
            await page.getByTestId('context-menu-action-delete').click();
        }

        // Save (now empty)
        await page.getByTestId('asset-modal-save').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Reopen one more time
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});
        await expandMoreInfo(page);

        // Verify geo distribution is empty (no total badge)
        const geoTotalFinal = page.getByTestId('distribution-total-geographic');
        await expect(geoTotalFinal).not.toBeVisible({timeout: 3000});

        await page.getByTestId('asset-modal-cancel').click();
    });
});
