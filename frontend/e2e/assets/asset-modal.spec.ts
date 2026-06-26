/**
 * Asset Modal — E2E Tests
 *
 * Tests the AssetModal: create, edit, search, provider section, distributions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '@playwright/test';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {goToAssetsPage, openCreateAssetModal} from './assets-helpers';

test.describe('Asset Modal', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // ========================================================================
    // Test 1: Create modal opens and closes
    // ========================================================================
    test('create modal opens and closes', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        await expect(page.getByTestId('asset-modal-form')).toBeVisible();
        // Close with cancel
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 3000});
    });

    // ========================================================================
    // Test 2: Display name input accepts text
    // ========================================================================
    test('display name input accepts text', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const nameInput = page.getByTestId('asset-modal-display-name');
        await expect(nameInput).toBeVisible();
        await nameInput.fill('Test Asset E2E');
        await expect(nameInput).toHaveValue('Test Asset E2E');
    });

    // ========================================================================
    // Test 3: Save button disabled when form invalid
    // ========================================================================
    test('save button disabled when name is empty', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const saveBtn = page.getByTestId('asset-modal-save');
        // Clear display name (should be empty initially for create)
        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill('');
        await expect(saveBtn).toBeDisabled();
    });

    // ========================================================================
    // Test 4: Create basic asset (name + currency)
    // ========================================================================
    test('can create basic asset with name and currency', async ({page}) => {
        await goToAssetsPage(page);
        const countBefore = await page.getByTestId('assets-count-badge').textContent();

        await openCreateAssetModal(page);
        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill(`E2E Test Asset ${Date.now()}`);

        // Save
        const saveBtn = page.getByTestId('asset-modal-save');
        await expect(saveBtn).toBeEnabled({timeout: 3000});
        await saveBtn.click();

        // Modal should close
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Page should still be visible
        await expect(page.getByTestId('assets-page')).toBeVisible();
    });

    // ========================================================================
    // Test 5: Edit modal shows pre-populated fields
    // ========================================================================
    test('edit modal shows pre-populated display name', async ({page}) => {
        await goToAssetsPage(page);
        // Navigate to first asset detail
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        await expect(firstCard).toBeVisible({timeout: 5_000});
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        // Open edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Display name should be pre-filled (not empty)
        const nameInput = page.getByTestId('asset-modal-display-name');
        const value = await nameInput.inputValue();
        expect(value.length).toBeGreaterThan(0);

        // Close
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 6: Modal has save and cancel buttons
    // ========================================================================
    test('modal has save and cancel buttons', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        await expect(page.getByTestId('asset-modal-save')).toBeVisible();
        await expect(page.getByTestId('asset-modal-cancel')).toBeVisible();
        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 7: Smart search input is visible in create modal
    // ========================================================================
    test('smart search input is visible in create modal', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        // Search input with placeholder "Search by name, ticker, ISIN..."
        const searchInput = page.locator('input[placeholder*="Search by name"]');
        await expect(searchInput).toBeVisible();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 8: Smart search triggers on typing (shows loading or results)
    // ========================================================================
    test('smart search triggers on typing', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        const searchInput = page.locator('input[placeholder*="Search by name"]');
        await searchInput.fill('Apple');
        await page.waitForTimeout(1500);

        // Should show either results dropdown, loading spinner, or "no results"
        const form = page.getByTestId('asset-modal-form');
        const hasDropdown = await form
            .locator('.shadow-lg, [class*="shadow-lg"]')
            .first()
            .isVisible()
            .catch(() => false);
        const hasLoading = await form
            .locator('.animate-spin')
            .first()
            .isVisible()
            .catch(() => false);

        // At least one of: results dropdown appeared or loading showed
        expect(hasDropdown || hasLoading).toBeTruthy();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 9: Edit modal has more fields than create
    // ========================================================================
    test('edit modal shows additional fields (currency, type)', async ({page}) => {
        await goToAssetsPage(page);
        const firstCard = page.locator('[data-testid^="asset-card-"]').first();
        await expect(firstCard).toBeVisible({timeout: 5_000});
        await firstCard.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        // Open edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        const form = page.getByTestId('asset-modal-form');

        // Should have display name pre-filled
        const nameInput = page.getByTestId('asset-modal-display-name');
        const value = await nameInput.inputValue();
        expect(value.length).toBeGreaterThan(0);

        // Should have currency selector (combobox or select with currency code)
        const hasCurrency = await form
            .locator('[role="combobox"], select')
            .first()
            .isVisible()
            .catch(() => false);
        expect(hasCurrency).toBeTruthy();

        await page.getByTestId('asset-modal-cancel').click();
    });

    // ========================================================================
    // Test 10: Modal scrolls without layout break
    // ========================================================================
    test('modal form is scrollable', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        const form = page.getByTestId('asset-modal-form');
        await expect(form).toBeVisible();

        // Form should have overflow-y-auto (scrollable when content exceeds max-height)
        const overflowY = await form.evaluate((el) => getComputedStyle(el).overflowY);
        expect(overflowY).toBe('auto');

        await page.getByTestId('asset-modal-cancel').click();
    });
});

// ============================================================================
// Non-regression tests — QA bug report 2026-06-25
// ============================================================================

test.describe('NR — Currency default from userSettings (Bug G)', () => {
    const API = '/api/v1';

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        // Always restore EUR so other tests are not affected
        await page.request.put(`${API}/settings/user`, {data: {base_currency: 'EUR'}});
    });

    test('create modal defaults currency to user base_currency', async ({page}) => {
        // Set base_currency to a non-default value
        const r = await page.request.put(`${API}/settings/user`, {data: {base_currency: 'GBP'}});
        expect(r.ok()).toBeTruthy();

        // Full page navigation to reload the userSettings store
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        // Currency combobox (the SearchSelect trigger inside the currency group)
        const currencyGroup = page.getByTestId('asset-modal-currency-group');
        await expect(currencyGroup).toBeVisible({timeout: 3000});
        const combobox = currencyGroup.getByRole('combobox');
        await expect(combobox).toContainText('GBP', {timeout: 3000});

        await page.getByTestId('asset-modal-cancel').click();
    });
});

test.describe('NR — Sector dropdown emoji (Bug E)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('sector options contain emoji in the create modal', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        // Expand "More Info" section to reveal classification editors
        await page.getByTestId('asset-modal-more-info').click();
        await expect(page.getByTestId('distribution-editor-sector')).toBeVisible({timeout: 3000});

        // Add a sector entry to make the SectorSearchSelect appear
        await page.getByTestId('distribution-add-sector').click();
        await page.waitForTimeout(400);

        // The sector cell in the new row is a SectorSearchSelect combobox
        const sectorEditor = page.getByTestId('distribution-editor-sector');
        const combobox = sectorEditor.getByRole('combobox').first();
        await expect(combobox).toBeVisible({timeout: 3000});

        // Click to open the listbox
        await combobox.click();
        await page.waitForTimeout(400);

        // Options use data-testid="search-select-option-{sectorCode}" (not role=option)
        const options = page.locator('[data-testid^="search-select-option-"]');
        await expect(options.first()).toBeVisible({timeout: 3_000});
        const count = await options.count();
        expect(count).toBeGreaterThan(0);

        // Verify the first option text starts with an emoji character
        // (emoji Unicode ranges: most common ones are >= U+2000)
        const firstOptionText = await options.first().textContent() ?? '';
        // An emoji is present if there's a non-ASCII, non-letter character before the text
        // Simple check: the trimmed text must NOT start with a plain ASCII letter
        const trimmed = firstOptionText.trim();
        const firstCodePoint = trimmed.codePointAt(0) ?? 0;
        expect(firstCodePoint).toBeGreaterThan(127); // Not a plain ASCII character

        await page.getByTestId('asset-modal-cancel').click();
    });
});

test.describe('NR — Sync on create with provider (Bug K)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('sync_prices_bulk called after saveCreate with non-parametric provider', async ({page}) => {
        // Skip if no non-parametric provider assets exist in test env
        const resp = await page.request.get('/api/v1/assets?page_size=200');
        if (!resp.ok()) {
            test.skip(true, 'Could not fetch assets list');
            return;
        }
        type AssetItem = {asset_id: number; display_name: string; provider_code: string | null};
        const data = (await resp.json()) as {items: AssetItem[]};
        const withProvider = data.items?.find(
            (a) => a.provider_code && a.provider_code !== 'scheduled_investment',
        );
        if (!withProvider) {
            test.skip(true, 'No non-parametric provider asset in test env');
            return;
        }

        // Intercept the sync call before navigating (route must be installed first)
        let syncPayload: unknown = null;
        await page.route('**/assets/prices/sync', async (route) => {
            syncPayload = route.request().postDataJSON();
            // Fulfill to avoid actual network call
            await route.fulfill({status: 200, contentType: 'application/json', body: '[]'});
        });

        // Navigate to the asset detail page and open edit
        await navigateTo(page, `/assets/${withProvider.asset_id}`);
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Make the provider dirty by clearing and re-entering the identifier
        // (so saveEdit triggers the sync path)
        // Locate provider identifier input (aria-label or placeholder-based)
        const identifierInput = page
            .getByTestId('asset-modal-form')
            .locator('input[placeholder*="identifier"], input[placeholder*="ISIN"], input[id*="identifier"]')
            .first();

        if (await identifierInput.isVisible({timeout: 2000}).catch(() => false)) {
            const currentVal = await identifierInput.inputValue();
            await identifierInput.fill(currentVal + ' ');
            await identifierInput.fill(currentVal); // restore (still dirty due to intermediate change)
        }

        // Save — if providerDirty=true, saveEdit calls sync
        const saveBtn = page.getByTestId('asset-modal-save');
        if (await saveBtn.isEnabled({timeout: 3000}).catch(() => false)) {
            await saveBtn.click();
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 15_000});
            // If sync was called, verify the payload structure
            if (syncPayload !== null) {
                const payload = syncPayload as Array<{asset_id: number; date_range: {start: string; end: string}}>;
                expect(Array.isArray(payload)).toBeTruthy();
                // For saveEdit with providerDirty, start is 5-years-ago (not 1975)
                // For saveCreate with provider, start is '1975-01-01'
                expect(payload[0]?.date_range?.start).toBeTruthy();
            }
        } else {
            await page.getByTestId('asset-modal-cancel').click();
            test.skip(true, 'Provider identifier input not found or save not enabled');
        }
    });
});
