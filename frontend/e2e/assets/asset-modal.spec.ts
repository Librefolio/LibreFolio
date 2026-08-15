/**
 * Asset Modal — E2E Tests
 *
 * Tests the AssetModal: create, edit, search, provider section, distributions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
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

        // Display name should be pre-filled (not empty). populateFromEditData() runs
        // inside an $effect after mount, so use a retrying assertion instead of a
        // one-shot inputValue() read (avoids a race with the effect's async timing).
        const nameInput = page.getByTestId('asset-modal-display-name');
        await expect(nameInput).not.toHaveValue('', {timeout: 3000});

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

        // The dropdown is the one container for every outcome — spinner while
        // searching, rows, "no results", error — so its presence *is* "the
        // search reacted". Sampling two CSS classes 1,5 s after typing asked a
        // different question ("is it in one of these two states right now?"),
        // which under load is false while nothing at all is wrong.
        const results = page.getByTestId('asset-search-results');
        await expect(results).toBeVisible({timeout: 10_000});
        await expect(results).toHaveAttribute('data-state', /searching|results|empty|error/);

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

        // Should have display name pre-filled. Use a retrying assertion since
        // populateFromEditData() runs inside an $effect after mount (see S5 above).
        const nameInput = page.getByTestId('asset-modal-display-name');
        await expect(nameInput).not.toHaveValue('', {timeout: 3000});

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

    // This block mutates a *shared* global: `base_currency` belongs to the test user,
    // and every worker logs in as that same user. It is tolerable only because the
    // window is a few seconds and no neighbour asserts on the base currency — if one
    // ever does, this test needs its own user, not a longer timeout.

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

        // The PUT went through the API context; the browser still holds the value it
        // cached at login (`auth.ts` → `userSettings.setDirect`). A reload refetches it,
        // but the modal reads the currency once when it opens, so opening before the
        // GET lands captures the stale EUR. Arm the wait first, then navigate.
        const settingsReloaded = page.waitForResponse(async (res) => res.url().includes('/settings/user') && res.request().method() === 'GET' && res.ok() && (await res.json().catch(() => ({})))?.base_currency === 'GBP', {timeout: 20_000});
        await goToAssetsPage(page);
        await settingsReloaded;

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

        // The sector cell in the new row is a SectorSearchSelect combobox
        const sectorEditor = page.getByTestId('distribution-editor-sector');
        const combobox = sectorEditor.getByRole('combobox').first();
        await expect(combobox).toBeVisible({timeout: 3000});

        // Click to open the listbox
        await combobox.click();

        // Options use data-testid="search-select-option-{sectorCode}" (not role=option)
        const options = page.locator('[data-testid^="search-select-option-"]');
        await expect(options.first()).toBeVisible({timeout: 3_000});
        const count = await options.count();
        expect(count).toBeGreaterThan(0);

        // Verify the first option text starts with an emoji character
        // (emoji Unicode ranges: most common ones are >= U+2000)
        const firstOptionText = (await options.first().textContent()) ?? '';
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

    // What this must prove: creating an asset with a price provider asks the backend for the
    // provider's WHOLE history, not a recent window. Since the unified sync rule landed, the
    // frontend expresses that as `date_range.start = 'resume'` — "carry on from the last price
    // you have, or fetch everything if you have none". A just-created asset has none, so this
    // IS the full-history request; the resolution simply happens server-side, in one round trip
    // instead of a query-then-decide dance the frontend would have to race.
    //
    // The other half of the chain — that 'resume' with no stored prices resolves to 'min' — is
    // owned by the backend, in test_asset_source_refresh.py::
    // test_resume_falls_back_to_min_without_stored_prices. Neither half is provable here alone.
    //
    // The previous version never executed a line. It was skipped, and behind the skip it
    // queried `GET /assets?page_size=200` (not a route → 422 → the guard fired every time)
    // and tried to dirty the provider by typing a space and deleting it — but `providerDirty`
    // is a $derived value comparison, so restoring the string clears it and Save stays
    // disabled.
    //
    // Why this asserts the request and not the resulting price rows: the only provider that
    // answers without network is `mockprov`, and the UI filters it out of the dropdown on
    // purpose (ProviderAssignmentSection.svelte:144) because it must never be user-selectable.
    // An outcome assertion would therefore need either that filter removed — changing
    // production behaviour to suit a test — or a real network fetch, which is exactly the
    // flakiness the offline suite exists to avoid. So the provider probe and the sync are
    // both intercepted, and the contract checked is the one the frontend actually owns:
    // *which range it asks for, for the asset it just created*.
    test('create with provider asks the backend for the full history, not a recent window', async ({page}) => {
        const assetName = `E2E BugK ${Date.now()}`;
        let assetId: number | null = null;
        let syncPayload: Array<{asset_id: number; date_range: {start: string; end: string}}> | null = null;

        // Keep the whole test offline: the probe only has to satisfy the Save gate, and the
        // sync must not reach a real provider.
        await page.route('**/api/v1/assets/provider/probe', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                // Shape must satisfy the generated Zod schema (FAProviderProbeResponse):
                // the client validates at runtime, and a rejected body lands in the catch
                // that sets testStatus = 'failed'.
                body: JSON.stringify({
                    provider_code: 'e2e',
                    identifier: 'E2E-BUGK',
                    total_execution_time_ms: 2,
                    current_price: {success: true, execution_time_ms: 1, value: '100.00', currency: 'USD', as_of_date: '2024-01-02'},
                    history: {success: true, execution_time_ms: 1, points_count: 2, date_range: '2024-01-01 → 2024-01-02'},
                }),
            });
        });
        await page.route('**/api/v1/assets/prices/sync', async (route) => {
            syncPayload = route.request().postDataJSON();
            await route.fulfill({status: 200, contentType: 'application/json', body: '[]'});
        });

        // Pick whatever real provider the registry offers rather than hardcoding one, so the
        // test survives providers being added or retired.
        const listRes = await page.request.get('/api/v1/assets/provider');
        expect(listRes.ok(), 'provider list must be reachable').toBeTruthy();
        const providers = (await listRes.json()) as Array<{code: string; accepted_identifier_types?: string[]}>;
        const provider = providers.find((p) => p.code !== 'mockprov' && p.code !== 'scheduled_investment');
        expect(provider, 'a non-parametric provider must exist').toBeTruthy();

        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        await page.getByTestId('asset-modal-display-name').fill(assetName);

        const providerHeader = page.getByTestId('asset-modal-provider-header');
        if ((await providerHeader.getAttribute('data-expanded')) !== 'true') {
            await providerHeader.click();
        }
        await page.getByTestId('provider-code-select-button').click();
        await page.getByTestId(`provider-option-${provider!.code}`).click();

        const identifier = page.getByTestId('provider-identifier');
        if (await identifier.isVisible().catch(() => false)) {
            await identifier.fill('E2E-BUGK');
        }

        // Save is gated on a passing connection test whenever a provider is set
        // (AssetModal.svelte:1212), so the gate is driven rather than bypassed.
        await page.getByTestId('provider-test-config').click();
        await expect(page.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', 'passed', {timeout: 20_000});

        const createResponse = page.waitForResponse((r) => r.url().endsWith('/api/v1/assets') && r.request().method() === 'POST');
        await page.getByTestId('asset-modal-save').click();
        const created = (await (await createResponse).json()) as {results?: Array<{asset_id?: number}>};
        assetId = created.results?.[0]?.asset_id ?? null;
        expect(assetId, 'create response must carry the new asset id').not.toBeNull();

        try {
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

            // The sync is deliberately fire-and-forget (`void ….catch(…)`), so it is polled
            // for rather than awaited on the save path.
            await expect.poll(() => syncPayload !== null, {message: 'create with a provider must trigger a price sync', timeout: 15_000}).toBeTruthy();

            const item = syncPayload![0];
            expect(item.asset_id).toBe(assetId);
            // The whole point: for an asset that has no prices yet, 'resume' means "everything
            // the provider has". Any literal date here is a silent truncation — the original
            // code sent '1975-01-01', which would have discarded every earlier year without a
            // word.
            expect(item.date_range.start).toBe('resume');
            expect(item.date_range.end).toBe(new Date().toISOString().slice(0, 10));
        } finally {
            if (assetId !== null) {
                await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
            }
        }
    });
});
