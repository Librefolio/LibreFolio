/**
 * Asset Modal — E2E Tests
 *
 * Tests the AssetModal: create, edit, search, provider section, distributions.
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {expect, test, type Page} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {API_BASE, goToAssetDetailPage, goToAssetsPage, openCreateAssetModal, openEditAssetModal} from './assets-helpers';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {INSTANCE_CONFIG_PATH} from '../fixtures/instance-config';
import {schemas} from '../../src/lib/api/generated';
import {createOwnedAsset as createEventsAsset, deleteOwned, jsonFrom, linkDividend, seedProviderDividend, type Owned} from './asset-events-owned';

/**
 * Every asset a test saved, by the unique name it gave it: its id once the create response has
 * named it, `null` until then — a save whose answer never came back is still findable by name.
 */
type OwnedAssets = Map<string, number | null>;
type HttpResponse = {status(): number; json(): Promise<unknown>};
type CreateBody = {results?: Array<{asset_id?: number | null; display_name?: string; success?: boolean; message?: string | null}>};
type DeleteBody = {results?: Array<{asset_id: number; success: boolean; message?: string | null}>};

/**
 * Click Save on the open create modal and record the id of the asset it creates, read from the
 * POST /assets response — the moment the asset exists, before anything that follows can fail.
 */
async function saveAndRecordCreated(page: Page, owned: OwnedAssets, name: string, save: () => Promise<void>): Promise<number> {
    owned.set(name, null);
    const [response] = await Promise.all([page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === `${API_BASE}/assets`, {timeout: 15_000}), save()]);
    return recordCreated(response, owned, name);
}

/** A plain EUR stock of the test's own, created over the API and recorded the moment it exists. */
async function createOwnedAsset(page: Page, owned: OwnedAssets, name: string): Promise<number> {
    owned.set(name, null);
    const response = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'STOCK'}]});
    return recordCreated(response, owned, name);
}

/** Read a POST /assets answer: record the id it gives `name`, then require that the create succeeded. */
async function recordCreated(response: HttpResponse, owned: OwnedAssets, name: string): Promise<number> {
    const body = (await response.json().catch(() => null)) as CreateBody | null;
    const result = body?.results?.find((item) => item.display_name === name);
    // Recorded before any assertion can throw: whatever was created gets deleted.
    if (typeof result?.asset_id === 'number') owned.set(name, result.asset_id);
    expect(response.status(), `POST ${API_BASE}/assets creates "${name}": ${JSON.stringify(body)}`).toBe(201);
    if (!result?.success || typeof result.asset_id !== 'number') throw new Error(`"${name}" was not created: ${JSON.stringify(body)}`);
    return result.asset_id;
}

/** The ids of the assets carrying exactly `name` — a unique name, so only ever the test's own. */
async function assetIdsNamed(page: Page, name: string): Promise<number[]> {
    const response = await page.request.get(`${API_BASE}/assets/query?search=${encodeURIComponent(name)}`);
    if (!response.ok()) throw new Error(`asset query answered ${response.status()}: ${await response.text()}`);
    return ((await response.json()) as Array<{id: number; display_name: string}>).filter((asset) => asset.display_name === name).map((asset) => asset.id);
}

/**
 * Delete what the test created, by id: the id each create response named, or — for a save whose
 * answer never arrived — the asset found by the unique name it was given. Every asset is tried
 * whatever happened to the previous one, and every failure is named.
 */
async function deleteOwnedAssets(page: Page, owned: OwnedAssets): Promise<void> {
    const failures: string[] = [];
    for (const [name, recordedId] of owned) {
        try {
            const ids = recordedId !== null ? [recordedId] : await assetIdsNamed(page, name);
            for (const id of ids) {
                const response = await page.request.delete(`${API_BASE}/assets?asset_ids=${id}`);
                const body = (await response.json().catch(() => null)) as DeleteBody | null;
                if (!response.ok() || body?.results?.find((result) => result.asset_id === id)?.success !== true) failures.push(`asset ${id} "${name}": HTTP ${response.status()} ${JSON.stringify(body)}`);
            }
        } catch (error) {
            failures.push(`"${name}": ${String(error)}`);
        }
    }
    expect(failures, 'cleanup deletes every asset this test created').toEqual([]);
}

test.describe('Asset Modal', () => {
    // Tests 4 and 5 each own one asset: its id is recorded the moment it exists, and the
    // afterEach deletes exactly that asset, by id. The other tests save nothing.
    let owned: OwnedAssets = new Map();

    test.beforeEach(async ({page}) => {
        owned = new Map();
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: it runs after a timeout too, while the page can still reach the
    // API, and an error of its own is reported beside the test's instead of replacing it.
    test.afterEach(async ({page}) => {
        await deleteOwnedAssets(page, owned);
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
        // Checked below on this test's own card, never on a count of everyone's assets. Cards are
        // the grid's — the default view, driven to rather than assumed, since the view is remembered.
        await page.getByTestId('view-mode-grid').click();

        await openCreateAssetModal(page);
        const name = `E2E Test Asset ${uniqueSuffix()}`;
        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill(name);

        // Save — the create response names the new asset's id, recorded for the afterEach
        const saveBtn = page.getByTestId('asset-modal-save');
        await expect(saveBtn).toBeEnabled({timeout: 3000});
        const assetId = await saveAndRecordCreated(page, owned, name, () => saveBtn.click());

        // Modal should close
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});

        // Page should still be visible, and list the asset this test created
        await expect(page.getByTestId('assets-page')).toBeVisible();
        await expect(page.getByTestId(`asset-card-${assetId}`), 'the asset this test created must reach the list').toBeVisible({timeout: 15_000});
    });

    // ========================================================================
    // Test 5: Edit modal shows pre-populated fields
    // ========================================================================
    test('edit modal shows pre-populated display name', async ({page}) => {
        // An asset of the test's own, created before the list loads: the card is opened by its
        // id, never by position — a neighbour's asset may sort first — and the name the form
        // must show is the one this test gave it.
        const name = `E2E Prefill ${uniqueSuffix()}`;
        const assetId = await createOwnedAsset(page, owned, name);

        await goToAssetsPage(page);
        // Cards are the grid's: the default view, driven to rather than assumed.
        await page.getByTestId('view-mode-grid').click();
        // Navigate to this test's asset detail
        const card = page.getByTestId(`asset-card-${assetId}`);
        await expect(card).toBeVisible({timeout: 5_000});
        await card.click();
        await expect(page.getByTestId('asset-detail-page')).toBeVisible({timeout: 10_000});

        // Open edit modal
        await page.getByTestId('asset-detail-edit-btn').click();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 5000});

        // Display name should be pre-filled with this asset's name. populateFromEditData() runs
        // inside an $effect after mount, so use a retrying assertion instead of a one-shot
        // inputValue() read (avoids a race with the effect's async timing).
        const nameInput = page.getByTestId('asset-modal-display-name');
        await expect(nameInput).toHaveValue(name, {timeout: 3000});

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

        // The form scrolls in a box capped at 70vh, inside the modal. The box is looked up — the first scroll container
        // from the form up, the form included — not assumed: K step 17 item 15 moved it off the fieldset onto a wrapper.
        const scrollBox = await form.evaluate((el) => {
            let box: Element | null = el;
            while (box && !['auto', 'scroll'].includes(getComputedStyle(box).overflowY)) box = box.parentElement;
            if (!box) return null;
            const modal = el.closest('[data-testid="asset-modal"]');
            const testId = box.getAttribute('data-testid');
            return {element: `<${box.tagName.toLowerCase()}${testId ? ` data-testid="${testId}"` : ''}>`, insideModal: modal !== null && modal !== box && modal.contains(box), maxHeight: getComputedStyle(box).maxHeight, innerHeight: window.innerHeight};
        });
        if (!scrollBox) throw new Error('no scroll container from the form up, the form included: the form cannot scroll');
        expect(scrollBox.insideModal, `the form's scroll box ${scrollBox.element} lies inside [data-testid="asset-modal"]`).toBe(true);
        const capPx = 0.7 * scrollBox.innerHeight;
        expect(Math.abs(parseFloat(scrollBox.maxHeight) - capPx), `the form's scroll box ${scrollBox.element} is capped at 70vh: max-height ${scrollBox.maxHeight}, 0.7 × innerHeight ${scrollBox.innerHeight} = ${capPx.toFixed(1)}px`).toBeLessThanOrEqual(1);

        await page.getByTestId('asset-modal-cancel').click();
    });
});

// ============================================================================
// Non-regression tests — QA bug report 2026-06-25
// ============================================================================

test.describe('NR — Currency default from userSettings (Bug G)', () => {
    const API = '/api/v1';

    // The user's base currency is GBP in this browser only: `GET /settings/user` is fetched from the backend and its
    // `base_currency` rewritten before the page sees it; any other method on that URL goes through untouched. Nothing is
    // written to the server, so nothing needs restoring. The block used to `PUT` GBP on TEST_USER, whom every worker
    // shares, and restore EUR afterwards — tolerable only while no neighbour read the base currency. Every page now
    // starts from it (R2 / N), so a neighbour's Dashboard opened in that window would have started in GBP.

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('create modal defaults currency to user base_currency', async ({page}) => {
        // Registered before the navigation, so the settings load of the page under test is answered here.
        await page.route(`**${API}/settings/user`, async (route, request) => {
            if (request.method() !== 'GET') {
                await route.fallback();
                return;
            }
            // Nobody awaits a route callback, so it must not throw: `route.fetch()` rejects once the context closes, and
            // the rejection would land on whatever runs next. A read left unanswered fails this test on the wait below.
            try {
                const response = await route.fetch();
                if (!response.ok()) {
                    await route.fulfill({response});
                    return;
                }
                const body = (await response.json()) as Record<string, unknown>;
                await route.fulfill({response, json: {...body, base_currency: 'GBP'}});
            } catch (error) {
                console.warn(`[asset-modal] left ${request.method()} ${request.url()} unanswered: ${String(error)}`);
            }
        });

        // The browser still holds the settings cached at login (`auth.ts` → `userSettings.setDirect`); the full load
        // reads them again, through the route above, and the modal reads the currency once when it opens. Armed before
        // the navigation, a GBP answer proves the route above is what answered that read.
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

    // ========================================================================
    // Switching away from a parametric provider must warn *before* destroying
    // (X5-1: the counts are the server's dry run, one dialog for every provider change)
    //
    // A parametric series is invented from provider_params; under a market provider it
    // is not history, so the backend discards it ("provider changed" in
    // services/assets/provider_management.py). That is correct — but silent destruction is not, and the
    // warning has to be able to say *how much* it is about to destroy, otherwise it
    // is decoration. Both branches are driven: cancelling must leave the series
    // untouched, confirming must remove it.
    // ========================================================================
    test('switching away from a parametric provider warns with real counts, and only destroys on confirm', async ({page}) => {
        const label = `E2E Param ${uniqueToken(6)}`;
        let assetId: number | null = null;

        // The stretch of calendar the invented series occupies. It is not decoration:
        // every assertion about the series being present or gone is scoped to it, because
        // it is the one window no other worker can write into (see the stub comment below).
        const SERIES_START = '2024-01-15';
        const SERIES_END = '2026-01-15';

        // That scoping argument holds only while the window is entirely in the past: the
        // single row a foreign context can create is *today's*. Verify it rather than infer
        // it — whoever moves these dates forward has to be told why it matters.
        const today = new Date().toISOString().slice(0, 10);
        expect(today > SERIES_END, `the invented window must end before today (${SERIES_END} vs ${today}), or a foreign OHLC write-back can land inside it`).toBe(true);

        // Seed through the API *before* installing any route, so the seeding calls
        // reach the real backend: the test needs a genuine invented series to count.
        const createRes = await page.request.post('/api/v1/assets', {
            data: [{display_name: label, currency: 'EUR', asset_type: 'BOND'}],
        });
        expect(createRes.ok(), `asset create must succeed: ${await createRes.text()}`).toBeTruthy();
        assetId = ((await createRes.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;

        try {
            const assignRes = await page.request.post('/api/v1/assets/provider', {
                data: [
                    {
                        asset_id: assetId,
                        provider_code: 'scheduled_investment',
                        identifier: '',
                        identifier_type: 'AUTO_GENERATED',
                        provider_params: {
                            initial_value: {code: 'EUR', amount: 10000},
                            interest_type: 'SIMPLE',
                            day_count: 'ACT/365',
                            schedule: [{start_date: SERIES_START, end_date: SERIES_END, annual_rate: 0.035, maturation_frequency: 'MONTHLY', generate_interest: true}],
                        },
                    },
                ],
            });
            expect(assignRes.ok(), `parametric assignment must succeed: ${await assignRes.text()}`).toBeTruthy();

            const syncRes = await page.request.post('/api/v1/assets/prices/sync', {
                data: [{asset_id: assetId, date_range: {start: SERIES_START, end: SERIES_END}}],
            });
            expect(syncRes.ok(), 'parametric sync must succeed').toBeTruthy();

            // Stored rows, not the width of a query window: the price-query endpoint
            // backward-fills every calendar day in the requested range, so it answers with
            // the size of the question. Two reads, because there are two questions:
            //
            //  * `countPrices()` — the summary counter, i.e. the *global* total of stored
            //    rows for this asset. That is the number the modal quotes, so it is the
            //    right read for the warning's text and the wrong one for "is it gone".
            //  * `inventedDates()` — the rows this test authored, identified by their date.
            //    The backup stream is the only read that returns stored rows verbatim, one
            //    per (asset_id, date) and with no backfill, so the window filter applies to
            //    real stored dates. Same mechanism `fx-destructive.spec.ts` uses.
            const marketData = async () => {
                const res = await page.request.get(`/api/v1/assets/${assetId}/market-data/summary`);
                return (await res.json()) as {prices: number; events_provider: number; events_manual: number};
            };
            const countPrices = async () => (await marketData()).prices;
            const inventedDates = async (): Promise<string[]> => {
                const res = await page.request.get(`/api/v1/backup/asset/${assetId}/prices?format=json`);
                expect(res.ok(), `the price export must answer: ${res.status()} ${await res.text()}`).toBeTruthy();
                const rows = ((await res.json()) as {rows: Array<{date: string}>}).rows;
                return rows.map((r) => r.date).filter((d) => d >= SERIES_START && d <= SERIES_END);
            };

            // Presence barrier for the absence assertion at the end: a wipe can only be
            // proved on a series that demonstrably existed.
            const inventedBefore = await inventedDates();
            expect(inventedBefore.length, 'the seeded parametric asset must actually have an invented series').toBeGreaterThan(0);

            // Pick a real non-parametric provider rather than hardcoding one.
            const providers = (await (await page.request.get('/api/v1/assets/provider')).json()) as Array<{code: string}>;
            const target = providers.find((p) => p.code !== 'mockprov' && p.code !== 'scheduled_investment');
            expect(target, 'a non-parametric provider must exist').toBeTruthy();

            // Keep the switch offline: the probe only has to satisfy the Save gate.
            await page.route('**/api/v1/assets/provider/probe', async (route) => {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        provider_code: target!.code,
                        identifier: 'E2E-PARAM',
                        total_execution_time_ms: 2,
                        current_price: {success: true, execution_time_ms: 1, value: '100.00', currency: 'EUR', as_of_date: '2024-01-02'},
                        history: {success: true, execution_time_ms: 1, points_count: 2, date_range: '2024-01-01 → 2024-01-02'},
                    }),
                });
            });
            // The post-save sync is fire-and-forget; stub it so the assertion measures the
            // wipe rather than whatever the new provider manages to fetch.
            await page.route('**/api/v1/assets/prices/sync', async (route) => {
                await route.fulfill({status: 200, contentType: 'application/json', body: '[]'});
            });
            // Same reason, second writer — and this one is not obvious. Fetching a current
            // price is not a read: `get_current_prices_bulk` documents an OHLC write-back
            // (F.2/F.3) that creates today's row on every successful provider fetch. So a
            // detail page *adds* a price row simply by displaying the asset, and a fetch
            // still in flight when the wipe commits lands after it — leaving exactly one
            // survivor that no later poll would ever remove.
            //
            // Stubbing it silences this browser context. It does **not** silence the suite,
            // and the earlier version of this comment claimed it did. `Asset` and
            // `PriceHistory` carry no `user_id`: the asset created above is global, visible
            // to every worker, while `page.route()` only binds the context that installs it.
            // Any other worker that renders the asset list or a detail page fetches current
            // prices for *all* assets — this one included — and writes today's row through a
            // context this test cannot intercept. The backend log of the failing full run
            // says it plainly: 217 commits of "14 row(s) written/updated", fourteen being
            // every asset in the database.
            //
            // So no assertion here may speak about the *total*: that number has several
            // authors. What this test owns is the window [SERIES_START, SERIES_END], which
            // lies in the past, whereas a foreign write-back can only ever create today's
            // row. That is why the wipe is asserted through `inventedDates()` and never
            // through `countPrices()`.
            await page.route('**/api/v1/assets/prices/current*', async (route) => {
                await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({results: [], success_count: 0, errors: []})});
            });

            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);

            const selectNewProvider = async () => {
                const providerHeader = page.getByTestId('asset-modal-provider-header');
                if ((await providerHeader.getAttribute('data-expanded')) !== 'true') {
                    await providerHeader.click();
                }
                await page.getByTestId('provider-code-select-button').click();
                await page.getByTestId(`provider-option-${target!.code}`).click();
                const identifier = page.getByTestId('provider-identifier');
                if (await identifier.isVisible().catch(() => false)) {
                    await identifier.fill('E2E-PARAM');
                }
                await page.getByTestId('provider-test-config').click();
                await expect(page.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', 'passed', {timeout: 20_000});
            };

            await selectNewProvider();
            // Two reads, two purposes. `inventedAtSave` is what the wipe must destroy and
            // what the cancel branch must find intact. `pricesAtSave` is the global total,
            // read here only to prove that nothing deletes before the confirm.
            const inventedAtSave = (await inventedDates()).length;
            expect(inventedAtSave, 'the series must still be there when the switch is attempted').toBeGreaterThan(0);
            const pricesAtSave = await countPrices();

            // X5-1: the count the dialog quotes is the server's dry run (POST /assets/provider/impact),
            // not a second read of the market-data summary. The response is awaited from the click, so
            // the figure the dialog must say is the very one the server answered.
            const impactResponse = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === `${API_BASE}/assets/provider/impact`, {timeout: 15_000});
            await page.getByTestId('asset-modal-save').click();
            type ImpactBody = {results: Array<{asset_id: number; action: string; reason: string; prices_deleted: number; events_deleted: number; transactions_unlinked: number; blocking_splits?: unknown[]}>};
            const impact = ((await (await impactResponse).json()) as ImpactBody).results.find((result) => result.asset_id === assetId);
            expect(impact, 'the dry run answers for the asset being saved').toBeTruthy();
            expect(impact!.action).toBe('assign');
            expect(impact!.reason, 'leaving a parametric provider for a market one').toBe('provider_changed');
            expect(impact!.blocking_splits ?? [], 'no split with an adjustment to refuse the change').toEqual([]);
            // The series this test authored is part of what the server says it will delete; the total
            // is global and may hold a foreign write-back, so the claim is a lower bound.
            expect(impact!.prices_deleted, 'the dry run counts at least the invented series').toBeGreaterThanOrEqual(inventedAtSave);
            // The dialog writes the figure with the language's own number format; below a thousand that is its digits.
            expect(impact!.prices_deleted, 'a figure of three digits or fewer is written without a group separator').toBeLessThan(1000);

            // Branch 1 — the warning appears, and it can say how much it is about to destroy.
            await expect(page.getByTestId('asset-parametric-switch-confirm')).toBeVisible({timeout: 15_000});
            // Nothing deletes before the confirm, so the total can only grow.
            const pricesAtWarning = await countPrices();
            expect(pricesAtWarning, 'nothing may delete rows before the confirm').toBeGreaterThanOrEqual(pricesAtSave);
            await expect(page.getByTestId('confirm-modal-message')).toContainText(new RegExp(`\\b${impact!.prices_deleted}\\b`));

            await page.getByTestId('confirm-modal-cancel').click();
            await expect(page.getByTestId('asset-parametric-switch-confirm')).not.toBeVisible({timeout: 5000});
            // Exact rather than `>=`: inside the window this test is the only author, so
            // "nothing was destroyed" means the same rows are still there, not "at least
            // as many as before".
            expect((await inventedDates()).length, 'cancelling must not destroy anything').toBe(inventedAtSave);

            // Branch 2 — confirming goes through and the invented series is gone.
            await page.getByTestId('asset-modal-save').click();
            await expect(page.getByTestId('asset-parametric-switch-confirm')).toBeVisible({timeout: 15_000});
            await page.getByTestId('confirm-modal-confirm').click();
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 20_000});

            // Empty *inside the window*. Today's row may or may not be there, depending on
            // what the rest of the suite was doing with the asset list while this ran; a row
            // dated between 2024-01-15 and 2026-01-15 can only be a survivor of the wipe.
            // Polling the dates rather than a count also makes the failure name them.
            await expect.poll(async () => await inventedDates(), {message: 'confirming the switch must discard the invented series', timeout: 20_000}).toEqual([]);
        } finally {
            if (assetId !== null) {
                await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
            }
        }
    });

    // ========================================================================
    // X5-1 (C-65a + W-B2 + X-R69): removing a provider is no longer refused for the transactions
    // linked to the events it generated. A dialog says how many prices, events and linked
    // transactions are lost (the transactions are kept, only unlinked); confirm goes through.
    //
    // Data: an asset of the test's own, a scheduled_investment assignment whose planned DIVIDEND a
    // price sync stores under it (is_auto), and a DIVIDEND on a broker of the test's own that
    // realises that event. Nothing shared is read or written; the broker (with its transaction) and
    // the asset go afterwards, whatever the outcome.
    // ========================================================================
    test('X5-1: removing a provider whose generated dividend a transaction is linked to asks first, then removes it and only unlinks the transaction', async ({page}) => {
        test.setTimeout(90_000);
        const own: Owned = {assetIds: [], brokerIds: []};
        try {
            const asset = await createEventsAsset(page, own, {label: 'E2E X5-1 remove'});
            const eventId = await seedProviderDividend(page, asset.id, 5, `x5-1 ${uniqueSuffix()}`, '0.80');
            const txId = await linkDividend(page, own, asset.id, eventId, daysAgoIso(5));

            // Verified, not inferred: the DIVIDEND realises the generated event, and the provider is assigned.
            const readTransaction = async () => {
                const rows = await jsonFrom<Array<{id: number; asset_event_id?: number | null}>>(await page.request.get(`${API_BASE}/transactions`, {params: {ids: txId}}), `read transaction ${txId}`);
                const row = rows.find((candidate) => candidate.id === txId);
                if (!row) throw new Error(`Transaction ${txId} is not stored: ${JSON.stringify(rows)}`);
                return row;
            };
            const assignmentsOf = async () => jsonFrom<Array<{asset_id: number; provider_code: string}>>(await page.request.get(`${API_BASE}/assets/provider/assignments`, {params: {asset_ids: asset.id}}), `read the assignment of asset ${asset.id}`);
            expect((await readTransaction()).asset_event_id, 'the DIVIDEND realises the provider event').toBe(eventId);
            expect(
                (await assignmentsOf()).filter((assignment) => assignment.asset_id === asset.id).map((assignment) => assignment.provider_code),
                'the asset is priced by the scheduled provider',
            ).toEqual(['scheduled_investment']);

            // Nothing here is about live prices: the detail page's OHLC write-back is answered locally.
            await page.route('**/api/v1/assets/prices/current*', async (route) => {
                await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({results: [], success_count: 0, errors: []})});
            });
            await goToAssetDetailPage(page, String(asset.id));
            await openEditAssetModal(page);

            const noProvider = page.getByTestId('asset-modal-no-provider');
            await expect(noProvider).toBeVisible();
            await noProvider.check();
            await expect(noProvider).toBeChecked();

            // Save: the dry run goes first, the dialog follows, and nothing has been removed yet.
            const impactResponse = page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === `${API_BASE}/assets/provider/impact`, {timeout: 15_000});
            await page.getByTestId('asset-modal-save').click();
            type ImpactBody = {results: Array<{asset_id: number; action: string; reason: string; events_deleted: number; transactions_unlinked: number; blocking_splits?: unknown[]}>};
            const impact = ((await (await impactResponse).json()) as ImpactBody).results.find((result) => result.asset_id === asset.id);
            expect(impact, 'the dry run answers for the asset being saved').toBeTruthy();
            expect(impact!.action).toBe('remove');
            expect(impact!.reason).toBe('provider_removed');
            expect(impact!.events_deleted, 'the generated DIVIDEND is among what is lost').toBeGreaterThanOrEqual(1);
            expect(impact!.transactions_unlinked, 'the one DIVIDEND this test linked loses its link').toBe(1);
            expect(impact!.blocking_splits ?? [], 'a DIVIDEND is no split: nothing refuses the removal').toEqual([]);

            await expect(page.getByTestId('asset-provider-remove-confirm')).toBeVisible({timeout: 15_000});
            expect(
                (await assignmentsOf()).some((assignment) => assignment.asset_id === asset.id),
                'nothing is removed before the confirm',
            ).toBe(true);
            expect((await readTransaction()).asset_event_id, 'the link is intact before the confirm').toBe(eventId);

            await page.getByTestId('confirm-modal-confirm').click();
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 20_000});

            // The provider is gone, and the transaction is still there — unlinked, not deleted.
            await expect.poll(async () => (await assignmentsOf()).some((assignment) => assignment.asset_id === asset.id), {message: 'the confirmed removal takes the provider away', timeout: 15_000}).toBe(false);
            const kept = await readTransaction();
            expect(kept.id, 'the transaction is kept').toBe(txId);
            expect(kept.asset_event_id ?? null, 'but it no longer realises the deleted event').toBeNull();
        } finally {
            await deleteOwned(page, own);
        }
    });

    // ========================================================================
    // Discard-confirm guard: cancelling a create modal that has unsaved edits
    // must open the discard confirmation, and "continue editing" must keep the
    // form open. Exercises AssetModal's isDirty → showDiscardConfirm branch in
    // handleClose, which no test entered. Nothing is ever saved → no cleanup.
    // ========================================================================
    test('cancelling a dirty create modal asks to confirm before discarding', async ({page}) => {
        await goToAssetsPage(page);
        await openCreateAssetModal(page);

        // Make the form dirty so handleClose routes through the discard confirm
        // instead of closing outright (displayName is the first snapshot field).
        const name = page.getByTestId('asset-modal-display-name');
        await name.fill(`E2E Discard ${uniqueToken(6)}`);
        await expect(name).toHaveValue(/^E2E Discard/);

        // Cancel → the discard confirmation appears rather than closing.
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-message')).toBeVisible();

        // "Continue editing" dismisses the confirm and keeps the form open.
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-message')).toHaveCount(0);
        await expect(page.getByTestId('asset-modal-form')).toBeVisible();

        // Cancel again, this time confirm the discard → the modal closes.
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 10_000});
    });

    // ========================================================================
    // Mandate B: the benchmark switch. `assets.is_benchmark` is a new column,
    // and the only thing that makes it real for a user is that the switch they
    // flipped is still flipped the next time they open the asset.
    //
    // The two directions are asserted separately on purpose. "The flag reached
    // the database" and "the flag came back into the form" are different
    // failures with different fixes, and a single end-to-end assertion cannot
    // tell them apart — it would just say "the toggle is off" and leave the
    // reader to guess which half broke.
    //
    // The switch is a role="switch" with aria-checked, so its state is readable
    // without touching a CSS class or a translated label, and toHaveAttribute
    // retries — no probe, no sleep.
    // ========================================================================
    test('the benchmark toggle reaches the backend and comes back', async ({page}) => {
        const name = `E2E Benchmark ${uniqueToken(6)}`;
        let assetId: number | null = null;

        try {
            // ---- create through the modal, with the switch on -------------
            await goToAssetsPage(page);
            await openCreateAssetModal(page);
            const nameInput = page.getByTestId('asset-modal-display-name');
            await nameInput.fill(name);
            await expect(nameInput).toHaveValue(name);

            const toggle = page.getByTestId('asset-benchmark-toggle');
            // Assert the starting state instead of assuming it: on a toggle, a
            // blind click is only a *change*, and if a create ever opened with
            // the flag already on, the click below would be turning it off and
            // everything after it would be testing the opposite claim.
            await expect(toggle, 'a create must start from "not a benchmark"').toHaveAttribute('aria-checked', 'false');
            await toggle.click();
            await expect(toggle).toHaveAttribute('aria-checked', 'true');

            const saveBtn = page.getByTestId('asset-modal-save');
            await expect(saveBtn).toBeEnabled();
            await saveBtn.click();
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 15_000});

            // ---- half one: the flag reached the database ------------------
            // Found by the unique name this test owns, never by position: the
            // query is a shared surface and a neighbour may have written to it
            // between the save and this read.
            const res = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(name)}`);
            expect(res.ok(), `the asset query must answer: ${res.status()} ${await res.text()}`).toBeTruthy();
            const row = ((await res.json()) as Array<{id: number; display_name: string; is_benchmark?: boolean}>).find((a) => a.display_name === name);
            expect(row, 'the asset the modal just created must be queryable by its unique name').toBeTruthy();
            assetId = row!.id;
            expect(row!.is_benchmark, 'the create payload must carry is_benchmark all the way to the database').toBe(true);

            // ---- half two: …and comes back on a fresh load ----------------
            // goToAssetDetailPage() is a real page.goto(), so nothing survives
            // from the create above except what the backend stored.
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);
            await expect(
                page.getByTestId('asset-benchmark-toggle'),
                'the edit form must reopen with the stored flag. AssetModal.loadAssetData() already reads `data.is_benchmark`, so an "off" here means the CALLER never put the field into editData — neither buildEditData() in routes/(app)/assets/[id]/+page.svelte nor loadAssetEditData() in lib/components/assets/assetEditData.ts copies it. That is not cosmetic: saveEdit() sends `is_benchmark: isBenchmark` on every PATCH, so editing anything at all about a benchmark asset silently un-benchmarks it.',
            ).toHaveAttribute('aria-checked', 'true');
        } finally {
            // The id is only known once half one has read it back, so a failure
            // before that point would otherwise leave the row behind. Resolve it
            // by the unique name instead — still scoped to what this test wrote.
            if (assetId === null) {
                assetId = await page.request
                    .get(`/api/v1/assets/query?search=${encodeURIComponent(name)}`)
                    .then(async (r) => (r.ok() ? (((await r.json()) as Array<{id: number; display_name: string}>).find((a) => a.display_name === name)?.id ?? null) : null))
                    .catch(() => null);
            }
            if (assetId !== null) await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
        }
    });
});

// ============================================================================
// O-20: one creation, one price sync.
//
// Creating an asset with a provider from the list page asks for its prices TWICE: the modal fires a background
// full-history sync as it closes (AssetModal.svelte, saveCreate), and the list page's `oncreated` reloads the
// assets and syncs the new one again (assets/+page.svelte, handleSyncAsset). The direction is one sync, owned by
// the modal — but this test pins the count only, never which of the two survives.
//
// Offline: the dropdown cannot offer `mockprov` (the backend hides test-only providers and
// ProviderAssignmentSection filters it), so the UI path picks a live provider as Bug K does, and every
// provider-facing call of this page — probe, sync, current prices — is answered here; cross-origin requests
// (provider icons) are refused.
// ============================================================================

type SyncItem = {asset_id: number; date_range: {start: string; end: string}};
type ProbeBody = {provider_code: string; identifier: string; operations?: string[]};
type ProviderInfo = {code: string; kind?: string; accepted_identifier_types?: string[]; params_schema?: Array<{required?: boolean}>};

/** A sync that reached no provider: nothing fetched, nothing written, and said so — never a fabricated success. */
function offlineSyncAnswer(items: SyncItem[]) {
    return {
        results: items.map(({asset_id}) => ({asset_id, status: 'failed', provider_used: null, points_fetched: 0, points_changed: 0, inserted_count: 0, updated_count: 0, events_fetched: 0, events_changed: 0, changed_points: null, errors: ['Synthetic offline boundary: no sync performed']})),
        success_count: 0,
        errors: [],
        total_points_changed: 0,
    };
}

/** The connection test only has to open the Save gate: a passing price and history, nothing for metadata. */
function offlineProbeAnswer(request: ProbeBody) {
    const operations = request.operations ?? [];
    return {
        provider_code: request.provider_code,
        identifier: request.identifier,
        total_execution_time_ms: 0,
        ...(operations.includes('current_price') ? {current_price: {success: true, execution_time_ms: 0, value: '100.00', currency: 'EUR', as_of_date: todayIso()}} : {}),
        ...(operations.includes('history') ? {history: {success: true, execution_time_ms: 0, points_count: 2, date_range: `${daysAgoIso(1)} → ${todayIso()}`}} : {}),
        ...(operations.includes('metadata') ? {metadata: {success: false, execution_time_ms: 0, error_code: 'NO_DATA', error: 'Synthetic offline boundary: no metadata'}} : {}),
    };
}

/** The list's live poll: no quote, hence no write-back of today's price. */
function offlineCurrentPricesAnswer(assetIds: number[]) {
    return {results: assetIds.map((asset_id) => ({asset_id, value: null, currency: null, as_of_date: null, source: null, error: 'Synthetic offline boundary: no current quote requested'})), success_count: 0, errors: []};
}

test.describe('NR — One price sync per asset creation (O-20)', () => {
    let owned: OwnedAssets = new Map();

    test.beforeEach(async ({page}) => {
        owned = new Map();
        await login(page, TEST_USER);
    });

    // Routes first, so a callback racing the page's teardown cannot report an error of its own; then the asset, by id.
    test.afterEach(async ({page}) => {
        await page.unrouteAll({behavior: 'ignoreErrors'});
        await deleteOwnedAssets(page, owned);
    });

    test('creating an asset with a provider from the list page posts exactly one price sync for it', async ({page, baseURL}) => {
        // Two load waves of the list (before and after the save) plus the modal: more than the default 30 s under load.
        test.setTimeout(60_000);
        const name = `E2E O20 ${uniqueSuffix()}`;
        // ISIN-shaped, under the user-assigned "ZZ" prefix: no real instrument carries it.
        const identifier = `ZZ${uniqueToken(10)}`;

        // Schema-checked here, once: nobody awaits a route callback, so a stub that drifted from the generated
        // schema must fail at this line, not as a request left unanswered.
        schemas.FABulkRefreshResponse.parse(offlineSyncAnswer([{asset_id: 1, date_range: {start: 'resume', end: todayIso()}}]));
        schemas.FAProviderProbeResponse.parse(offlineProbeAnswer({provider_code: 'any', identifier, operations: ['current_price', 'history', 'metadata']}));
        schemas.FACurrentPriceResponse.parse(offlineCurrentPricesAnswer([1]));

        // A provider the form settles on by itself — the default TICKER, or its only identifier type — with no
        // required parameter and no parametric series (that kind skips the sync on purpose). Today: borsa_italiana.
        const providersResponse = await page.request.get(`${API_BASE}/assets/provider`);
        expect(providersResponse.ok(), `GET ${API_BASE}/assets/provider answered ${providersResponse.status()}`).toBeTruthy();
        const providers = (await providersResponse.json()) as ProviderInfo[];
        const provider = providers.find((p) => {
            const types = p.accepted_identifier_types ?? [];
            return p.code !== 'mockprov' && p.kind === 'online_scraper' && (types.includes('TICKER') || (types.length === 1 && types[0] !== 'AUTO_GENERATED')) && !(p.params_schema ?? []).some((field) => field.required);
        });
        if (!provider) throw new Error(`no market provider the form can assign without extra parameters: ${JSON.stringify(providers.map((p) => ({code: p.code, kind: p.kind, types: p.accepted_identifier_types})))}`);

        // ---- offline boundary: the catch-all first, since routes registered after it are tried before it ----
        if (!baseURL) throw new Error('the project must set use.baseURL');
        const origin = new URL(baseURL).origin;
        await page.route('**/*', async (route) => {
            const url = new URL(route.request().url());
            if (['http:', 'https:'].includes(url.protocol) && url.origin !== origin) await route.abort('blockedbyclient');
            else await route.fallback();
        });
        await page.route(`**${API_BASE}/assets/provider/probe`, async (route) => {
            await route.fulfill({json: offlineProbeAnswer(route.request().postDataJSON() as ProbeBody)});
        });
        await page.route(`**${API_BASE}/assets/prices/current`, async (route) => {
            await route.fulfill({json: offlineCurrentPricesAnswer(route.request().postDataJSON() as number[])});
        });
        // The subject: every sync this page posts, recorded before it is answered.
        const syncs: SyncItem[][] = [];
        await page.route(`**${API_BASE}/assets/prices/sync`, async (route) => {
            const items = route.request().postDataJSON() as SyncItem[];
            syncs.push(items);
            await route.fulfill({json: offlineSyncAnswer(items)});
        });

        // ---- create through the modal, from the list page ----
        await goToAssetsPage(page);
        // Cards are the grid's: the default view, driven to rather than assumed (the view is remembered).
        await page.getByTestId('view-mode-grid').click();
        await openCreateAssetModal(page);
        const form = page.getByTestId('asset-modal-form');
        await expect(form).toHaveAttribute('data-snapshot-ready', 'true');

        const nameInput = page.getByTestId('asset-modal-display-name');
        await nameInput.fill(name);
        await expect(nameInput).toHaveValue(name);

        // A toggle: ask for its state, act only if it is not there yet.
        const providerHeader = page.getByTestId('asset-modal-provider-header');
        if ((await providerHeader.getAttribute('data-expanded')) !== 'true') await providerHeader.click();
        await expect(providerHeader).toHaveAttribute('data-expanded', 'true');

        const providerSelect = page.getByTestId('provider-code-select-button');
        await providerSelect.click();
        await page.getByTestId(`provider-option-${provider.code}`).click();
        await expect(providerSelect).toHaveAttribute('aria-expanded', 'false');

        // Choosing a provider clears the identifier, so it is typed after; the field is always drawn for a typed identifier.
        const identifierInput = page.getByTestId('provider-identifier');
        await expect(identifierInput).toBeVisible();
        await identifierInput.fill(identifier);
        await expect(identifierInput).toHaveValue(identifier);

        // Save is gated on a passing connection test once a provider is set: driven, and answered offline above.
        await page.getByTestId('provider-test-config').click();
        await expect(page.getByTestId('asset-modal-provider-status')).toHaveAttribute('data-status', 'passed', {timeout: 10_000});

        const saveBtn = page.getByTestId('asset-modal-save');
        await expect(saveBtn).toBeEnabled();
        const assetId = await saveAndRecordCreated(page, owned, name, () => saveBtn.click());
        await expect(form).toBeHidden({timeout: 15_000});

        // Precondition, verified rather than inferred: the provider is really assigned — without it no sync is owed.
        const assignmentsResponse = await page.request.get(`${API_BASE}/assets/provider/assignments?asset_ids=${assetId}`);
        expect(assignmentsResponse.ok(), `provider assignments of asset ${assetId} answered ${assignmentsResponse.status()}`).toBeTruthy();
        const assignment = ((await assignmentsResponse.json()) as Array<{asset_id: number; provider_code: string}>).find((a) => a.asset_id === assetId);
        expect(assignment?.provider_code, `asset ${assetId} must carry the provider chosen in the modal`).toBe(provider.code);

        // ---- barrier: the page has finished what it does after a creation ----
        // The modal's sync leaves as the modal closes; the page's, if any, only after the second wave (prices) of its
        // reload. The end of that wave (`data-busy` false) and the page marking the asset as syncing land in one
        // microtask run, so from here a page sync shows as the card's sync control disabled, until the sync is
        // answered and the prices reloaded. That control has no test id: it is the card's only button that can be
        // disabled, and with a provider assigned (checked above) disabled means "syncing".
        const card = page.getByTestId(`asset-card-${assetId}`);
        await expect(card, 'the asset this test created must reach the grid').toBeVisible({timeout: 20_000});
        await waitForSettled(page.getByTestId('assets-page'), 20_000);
        // Presence barrier for the absence below: the card's footer, where the sync control lives, is drawn.
        await expect(card.getByTestId('asset-card-merge')).toBeVisible();
        await expect(card.getByRole('button', {disabled: true}), 'the card must stop syncing: its sync control stays disabled while the page syncs the asset').toHaveCount(0, {timeout: 20_000});

        // ---- the claim ----
        const syncsOfAsset = () => syncs.filter((items) => items.some((item) => item.asset_id === assetId));
        // Presence first (the modal's sync is fire-and-forget), then the count, read once the page is done.
        await expect.poll(() => syncsOfAsset().length, {message: `creating asset ${assetId} with a provider must ask for its prices`, timeout: 10_000}).toBeGreaterThanOrEqual(1);
        const requests = syncsOfAsset();
        expect(requests, `one creation, one POST ${API_BASE}/assets/prices/sync for asset ${assetId}; the page sent ${requests.length}: ${JSON.stringify(requests)}`).toHaveLength(1);
        expect(
            requests[0].map((item) => item.asset_id),
            'the sync asks for the asset just created, and only for it',
        ).toEqual([assetId]);
    });
});

// ============================================================================
// R14–R16: the type field is a two-level searchable select (TreeSelect). A
// subtype is chosen inside its family, stored as itself, and drawn everywhere
// with its composite icon — the ETF tag with the stock pastille — which is what
// the select previewed. `AssetTypeSelect.test.ts` pins the component; this is
// the path a user takes, through the dialog, the API and the grid.
//
// Everything is read from test ids, ARIA state and image `src`: no label of the
// select is ever read, so the locale of the run does not matter.
// ============================================================================
test.describe('Asset type select (R14–R16)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('an ETF subtype is picked inside its family, stored as such, and drawn with its composite icon', async ({page}) => {
        const name = `E2E Type Tree ${uniqueToken(6)}`;
        const composite = '/icons/asset-types/etf-stock.png';
        let assetId: number | null = null;

        try {
            await goToAssetsPage(page);
            await openCreateAssetModal(page);
            const nameInput = page.getByTestId('asset-modal-display-name');
            await nameInput.fill(name);
            await expect(nameInput).toHaveValue(name);

            // ---- pick ETF_STOCK inside the ETF family ---------------------
            // Rows are looked up inside the field: TreeSelect renders its dropdown
            // within its own container, and `asset-type-tree-*` names a kind of row.
            const field = page.getByTestId('asset-modal-type');
            const trigger = page.getByTestId('asset-modal-type-button');
            // Presence barrier for the negative below: the closed field shows *a*
            // type's picture — and not yet the one this test is about to pick,
            // or the post-condition would prove nothing.
            await expect(trigger.locator('img').first()).toBeVisible();
            await expect(trigger.locator(`img[src="${composite}"]`)).toHaveCount(0);

            await trigger.click();
            await expect(trigger).toHaveAttribute('aria-expanded', 'true');
            const etfFamily = field.getByTestId('asset-type-tree-group-ETF');
            await expect(etfFamily).toBeVisible();
            // A group row is a toggle, and it opens by itself when the value is
            // already an ETF: ask for its state, act only if it is not there yet.
            if ((await etfFamily.getAttribute('aria-expanded')) !== 'true') await etfFamily.click();
            await expect(etfFamily).toHaveAttribute('aria-expanded', 'true');

            const etfStock = field.getByTestId('asset-type-tree-option-ETF_STOCK');
            await expect(etfStock.locator(`img[src="${composite}"]`), 'the row must preview the composite the rest of the app will draw').toBeVisible();
            await etfStock.click();

            // The helper-style post-condition: the dropdown is gone, and the
            // closed field now shows the composite of the chosen subtype.
            await expect(trigger).toHaveAttribute('aria-expanded', 'false');
            await expect(etfStock).toHaveCount(0);
            await expect(trigger.locator(`img[src="${composite}"]`)).toBeVisible();

            // ---- save: the create response names the row this test owns ---
            const saveBtn = page.getByTestId('asset-modal-save');
            await expect(saveBtn).toBeEnabled();
            const createResponse = page.waitForResponse((r) => r.url().endsWith('/api/v1/assets') && r.request().method() === 'POST');
            await saveBtn.click();
            const created = (await (await createResponse).json()) as {results?: Array<{asset_id?: number | null; display_name?: string}>};
            assetId = created.results?.find((r) => r.display_name === name)?.asset_id ?? null;
            expect(assetId, `the create response must carry the id of "${name}"`).not.toBeNull();
            await expect(page.getByTestId('asset-modal-form')).not.toBeVisible({timeout: 15_000});

            // ---- the backend stored the subtype, not its family -----------
            const res = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(name)}`);
            expect(res.ok(), `the asset query must answer: ${res.status()} ${await res.text()}`).toBeTruthy();
            const stored = ((await res.json()) as Array<{id: number; asset_type: string | null}>).find((a) => a.id === assetId);
            expect(stored, 'the asset the dialog just created must come back from /assets/query').toBeTruthy();
            expect(stored!.asset_type, 'the dialog must save the subtype picked inside the family — not the family, not the default').toBe('ETF_STOCK');

            // ---- the card of this very asset draws the composite ----------
            await goToAssetsPage(page);
            // Grid is the default view, but ViewModeToggle remembers the last
            // choice per user in localStorage — drive to the end state.
            await page.getByTestId('view-mode-grid').click();
            await page.getByTestId('assets-search-input').fill(name);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            const card = page.getByTestId(`asset-card-${assetId}`);
            // Retrying on purpose: the search box is debounced and `data-busy`
            // does not cover the debounce.
            await expect(card, 'the asset this test created must reach the grid').toBeVisible({timeout: 15_000});
            // `.first()` on a locator already scoped to this card: the card paints
            // the type picture twice (round avatar and type badge).
            await expect(card.locator(`img[src="${composite}"]`).first(), 'ETF_STOCK must be drawn with its composite, etf-stock.png').toBeVisible();
            await expect(card.locator('img[src="/icons/asset-types/other.png"]'), 'ETF_STOCK fell through to the silent other.png fallback').toHaveCount(0);
        } finally {
            // Scoped to what this test wrote: by the id of its own create response,
            // or — if the run died before reading it — by its unique name.
            if (assetId === null) {
                assetId = await page.request
                    .get(`/api/v1/assets/query?search=${encodeURIComponent(name)}`)
                    .then(async (r) => (r.ok() ? (((await r.json()) as Array<{id: number; display_name: string}>).find((a) => a.display_name === name)?.id ?? null) : null))
                    .catch(() => null);
            }
            if (assetId !== null) await page.request.delete(`/api/v1/assets?asset_ids=${assetId}`).catch(() => {});
        }
    });
});

// ============================================================================
// Workstream X, sub-lot 3 — premium sources first (F21), «Can’t find it? Let us know» (P20).
//
// Search Online in the create dialog, in a real browser and offline. Three reads of the page are answered here, each
// on its exact path and for GET only; anything else goes through:
// - `GET /system/instance`: the backend's own answer with `support_url` set per test — and `profile`, when a test asks —
//   so the report's channel is the test's, not the lane's;
// - `GET /assets/provider`: the backend's own list, one searchable provider made premium (the first in code order,
//   mockprov aside — the dropdown never shows it), every other one community at the default priority;
// - `GET /assets/provider/search/stream`: a canned stream, as services/assets/search.py sends it — one event per
//   provider the search asked, then `done`. No provider is reached.
// The component test (AssetSearchAutocomplete.test.ts, blocks F21 and P20) pins the cases; this pins the path through
// the dialog, the real provider list and the real link — read and decoded, never followed. Nothing is written: the
// dialog is cancelled, and the routes go with the test's page.
// ============================================================================

const PROVIDER_LIST_PATH = `${API_BASE}/assets/provider`;
const SEARCH_STREAM_PATH = `${API_BASE}/assets/provider/search/stream`;

/** What the routes of one test chose, and what they served. */
interface SearchBoundary {
    /** The provider made premium: the first searchable one in code order, mockprov aside. */
    premium: string;
    /** The provider whose result fills the community section: the next one. */
    community: string;
    /** Each answer the page read the instance configuration with, as served. */
    instance: Array<Record<string, unknown>>;
    /** The providers each streamed search asked, in its order. */
    searches: string[][];
}

/**
 * Answer this page's `GET <path>` — that path only; any other method falls through — with the backend's own answer,
 * rewritten. The headers that describe the body in transit go: the backend gzips from 1 KB up, and a kept
 * `content-encoding` would have the browser decode plain JSON (fixtures/instance-config.ts). Nobody awaits a route
 * callback, so it never throws (Bug G above): a read it leaves unanswered fails the test on its own assertions.
 */
async function serveRewritten(page: Page, path: string, rewrite: (body: unknown) => unknown): Promise<void> {
    await page.route(
        (url) => url.pathname === path,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            try {
                const response = await route.fetch();
                const headers = {...response.headers()};
                delete headers['content-encoding'];
                delete headers['content-length'];
                await route.fulfill({status: response.status(), headers, ...(response.ok() ? {json: rewrite(await response.json())} : {body: await response.body()})});
            } catch (error) {
                console.warn(`[asset-modal] left GET ${request.url()} unanswered: ${String(error)}`);
            }
        },
    );
}

/** A search result as the backend sends it, under `provider`: checked against the generated schema. */
function searchHit(provider: string, identifier: string) {
    return schemas.FAProviderSearchResultItem.parse({identifier, identifier_type: 'TICKER', display_name: `E2E search ${identifier}`, provider_code: provider, currency: 'EUR', asset_type: 'ETF', provider_url: null, provider_params: null, via_web: false});
}

/**
 * Install the three routes on this page, before it loads. With `found`, the premium provider answers two results and
 * the community one one result; every other provider the search asks answers none — all of them, without `found`.
 * With `profile`, the instance answers that profile; without it, the backend's own passes through.
 */
async function routeSearchBoundary(page: Page, {supportUrl, found, profile}: {supportUrl: string | null; found: boolean; profile?: 'selfhosted' | 'managed'}): Promise<SearchBoundary> {
    // The real list, through `page.request`, which no page route reaches.
    const listed = await page.request.get(PROVIDER_LIST_PATH);
    expect(listed.ok(), `GET ${PROVIDER_LIST_PATH} answered ${listed.status()}`).toBe(true);
    const searchable = ((await listed.json()) as Array<{code: string; supports_search?: boolean}>)
        .filter((provider) => provider.supports_search === true && provider.code !== 'mockprov')
        .map((provider) => provider.code)
        .sort();
    if (searchable.length < 2) throw new Error(`F21 needs two searchable providers besides mockprov, one made premium and one left community; this backend lists ${JSON.stringify(searchable)}`);
    const [premium, community] = searchable;
    const boundary: SearchBoundary = {premium, community, instance: [], searches: []};
    const hits: Record<string, unknown[]> = found ? {[premium]: [searchHit(premium, 'E2E-F21-P1'), searchHit(premium, 'E2E-F21-P2')], [community]: [searchHit(community, 'E2E-F21-C1')]} : {};

    await serveRewritten(page, INSTANCE_CONFIG_PATH, (body) => {
        const answer = {...(body as Record<string, unknown>), support_url: supportUrl, ...(profile === undefined ? {} : {profile})};
        boundary.instance.push(answer);
        return answer;
    });
    await serveRewritten(page, PROVIDER_LIST_PATH, (body) => (body as Array<{code: string}>).map((provider) => ({...provider, ...(provider.code === premium ? {tier: 'premium', priority: 0} : {tier: 'community', priority: 100})})));
    await page.route(
        (url) => url.pathname === SEARCH_STREAM_PATH,
        async (route, request) => {
            if (request.method() !== 'GET') return route.fallback();
            const asked = (new URL(request.url()).searchParams.get('providers') ?? '').split(',').filter((code) => code !== '');
            boundary.searches.push(asked);
            // The premium provider answers last: its results must lead by their tier, not by their arrival.
            const answers = [...asked.filter((code) => code !== premium), ...asked.filter((code) => code === premium)].map((code) => ({event: 'provider_results', provider_code: code, results: hits[code] ?? []}));
            const done = {event: 'done', total_results: answers.reduce((total, answer) => total + answer.results.length, 0), providers_queried: asked, providers_with_errors: []};
            await route.fulfill({status: 200, contentType: 'text/event-stream', body: [...answers, done].map((event) => `data: ${JSON.stringify(event)}\n\n`).join('')}).catch((error) => console.warn(`[asset-modal] left GET ${request.url()} unanswered: ${String(error)}`));
        },
    );
    return boundary;
}

/** The report a link to a new GitHub issue carries: the address it opens, and the lines of the issue's body. */
function githubReport(href: string | null): {issue: string; lines: string[]} {
    const url = new URL(href ?? 'about:blank');
    return {issue: `${url.origin}${url.pathname}`, lines: (url.searchParams.get('body') ?? '').split('\n')};
}

test.describe('Asset search — premium first, «Can’t find it? Let us know» (F21, P20)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('premium results lead in a section of their own, the report row follows it, the community section stays closed until opened; the report is a prefilled GitHub issue', async ({page}) => {
        const boundary = await routeSearchBoundary(page, {supportUrl: null, found: true, profile: 'selfhosted'});
        const {premium, community} = boundary;
        const query = 'E2E F21 world equity';

        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const dialog = page.getByTestId('asset-modal');
        await expect(dialog.getByTestId(`asset-search-provider-${premium}`), 'precondition: Search Online asks the provider made premium').toHaveAttribute('data-selected', 'true', {timeout: 10_000});
        // Its input has no test id: it is the one text field of the search block.
        await dialog.locator('[data-search-autocomplete] input[type="text"]').fill(query);
        const results = dialog.getByTestId('asset-search-results');
        await expect(results, 'the search ends with results').toHaveAttribute('data-state', 'results', {timeout: 15_000});
        expect(boundary.searches, 'one search, which asked the premium provider and the community one').toEqual([expect.arrayContaining([premium, community])]);

        // Premium first, though it answered last: its two results, in a section of their own, under its badge. Every
        // result is this test's own (the stream is routed), so their count is the subject: the closed section draws none.
        const premiumSection = results.getByTestId('asset-search-premium-section');
        await expect(premiumSection.getByTestId('asset-search-premium-badge')).toBeVisible();
        for (const [i, identifier] of ['E2E-F21-P1', 'E2E-F21-P2'].entries()) {
            const row = premiumSection.getByTestId(`asset-search-result-${i}`);
            await expect(row).toHaveAttribute('data-provider', premium);
            await expect(row).toHaveAttribute('data-identifier', identifier);
        }
        await expect(results.locator('[data-testid^="asset-search-result-"]'), 'only the premium results are drawn').toHaveCount(2);

        // Then the report row, outside the Premium section, then the community section's button: closed, counting one.
        const reportRow = results.getByTestId('asset-search-report-row');
        const toggle = results.getByTestId('asset-search-community-toggle');
        await expect(reportRow).toBeVisible();
        await expect(toggle).toHaveAttribute('aria-expanded', 'false');
        await expect(toggle).toHaveAttribute('data-count', '1');
        await expect(results.getByTestId('asset-search-community-warning'), 'closed: no warning yet').toHaveCount(0);
        const placed = await results.evaluate((dropdown) => {
            const [section, row, button] = ['asset-search-premium-section', 'asset-search-report-row', 'asset-search-community-toggle'].map((id) => dropdown.querySelector(`[data-testid="${id}"]`));
            const follows = (a: Element | null, b: Element | null) => a !== null && b !== null && (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
            return {afterPremium: follows(section, row) && !section?.contains(row), beforeCommunity: follows(row, button)};
        });
        expect(placed, 'the report row stands between the Premium section, outside it, and the community one').toEqual({afterPremium: true, beforeCommunity: true});

        // The report: no support address, so a new GitHub issue, in a new tab. Read from its href, never followed.
        const link = reportRow.getByTestId('asset-search-report');
        await expect(link).toHaveAttribute('data-channel', 'github');
        await expect(link).toHaveAttribute('target', '_blank');
        await expect(link).toHaveAttribute('rel', /(^|\s)noopener(\s|$)/);
        await expect(link).toHaveAttribute('rel', /(^|\s)noreferrer(\s|$)/);
        // Who wrote it: the app's version, the profile of the routed answer, the language in force. Polled: the page
        // applies the instance's answer on a schedule of its own.
        await expect.poll(() => boundary.instance.length, {message: 'the page read the instance configuration through the route'}).toBeGreaterThan(0);
        const profile = String(boundary.instance.at(-1)?.profile);
        const language = await page.locator('html').getAttribute('lang');
        await expect.poll(async () => githubReport(await link.getAttribute('href')).lines.find((line) => line.startsWith('LibreFolio ')) ?? '', {message: 'the report names its writer'}).toMatch(new RegExp(`^LibreFolio .+, ${profile}, language ${language}$`));
        const report = githubReport(await link.getAttribute('href'));
        expect(report.issue, 'a new issue of the project').toBe('https://github.com/Librefolio/LibreFolio/issues/new');
        expect(report.lines).toContain(`Search: ${query}`);
        const outcome = (code: string) => (code === premium ? '2 results' : code === community ? '1 result' : '0 results');
        expect(report.lines.filter((line) => line.startsWith('- ')).sort(), 'every provider searched, with what it answered').toEqual(boundary.searches[0].map((code) => `- ${code}: ${outcome(code)}`).sort());

        // Opened: the warning, and the community result, numbered on from the premium ones.
        await toggle.click();
        await expect(toggle).toHaveAttribute('aria-expanded', 'true');
        await expect(results.getByTestId('asset-search-community-warning')).toBeVisible();
        const communityRow = results.getByTestId('asset-search-result-2');
        await expect(communityRow).toHaveAttribute('data-provider', community);
        await expect(communityRow).toHaveAttribute('data-identifier', 'E2E-F21-C1');

        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toBeHidden();
    });

    test('a mailto: support address sends the report by mail; a finished search closed by a click outside comes back on focus, with its report', async ({page}) => {
        const boundary = await routeSearchBoundary(page, {supportUrl: 'mailto:support@example.org', found: false});
        const query = 'E2E P20 nothing like it';

        await goToAssetsPage(page);
        await openCreateAssetModal(page);
        const dialog = page.getByTestId('asset-modal');
        await expect(dialog.getByTestId(`asset-search-provider-${boundary.premium}`), 'precondition: Search Online asks the provider made premium').toHaveAttribute('data-selected', 'true', {timeout: 10_000});
        const input = dialog.locator('[data-search-autocomplete] input[type="text"]');
        await input.fill(query);
        const results = dialog.getByTestId('asset-search-results');
        await expect(results, 'every provider answered nothing').toHaveAttribute('data-state', 'empty', {timeout: 15_000});
        const reportRow = results.getByTestId('asset-search-report-row');
        await expect(reportRow).toBeVisible();

        // The routed support address reached the page: the report is a mail to it, which opens no tab.
        const link = reportRow.getByTestId('asset-search-report');
        await expect(link, 'the support address of the routed answer').toHaveAttribute('data-channel', 'mailto');
        await expect(link, 'a mail opens no tab').not.toHaveAttribute('target');
        const href = (await link.getAttribute('href')) ?? '';
        const mail = /^mailto:support@example\.org\?subject=([^&]*)&body=([^&]*)$/.exec(href);
        if (!mail) throw new Error(`the report is not mailto:support@example.org?subject=…&body=…: ${href}`);
        expect(decodeURIComponent(mail[1])).toBe(`LibreFolio: asset not found — ${query}`);
        expect(mail[2], 'a mail body breaks its lines with CRLF (RFC 6068)').toContain('%0D%0A');
        const body = decodeURIComponent(mail[2]);
        expect(body.replace(/\r\n/g, ''), 'every line break of the body is CRLF').not.toContain('\n');
        expect(body.split('\r\n')).toContain(`Search: ${query}`);

        // A click elsewhere in the dialog (its name field: a click on the overlay would close the dialog itself) closes
        // the dropdown, report row included.
        await dialog.getByTestId('asset-modal-display-name').click();
        await expect(results).toHaveCount(0);
        await expect(dialog.getByTestId('asset-modal-form'), 'the dialog stays open').toBeVisible();

        // Back in the search box: the finished search shows again, with its report row — shown, not searched again.
        await input.focus();
        await expect(results).toHaveAttribute('data-state', 'empty');
        await expect(results.getByTestId('asset-search-report-row')).toBeVisible();
        expect(boundary.searches, 'the focus shows the last search: it does not search again').toHaveLength(1);

        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toBeHidden();
    });

    test('a managed instance with no support address shows no report row: a public GitHub issue would publish the instance and its search (N61)', async ({page}) => {
        const boundary = await routeSearchBoundary(page, {supportUrl: null, found: true, profile: 'managed'});
        const {premium, community} = boundary;
        const query = 'E2E N61 managed world equity';

        await goToAssetsPage(page);
        // Precondition, verified: the page read the instance through the route, and its client takes that answer — the
        // generated schema is the one it validates with (fixtures/instance-config.ts). A refused answer would leave the
        // page on its defaults, never loaded: no row either, for the wrong reason.
        await expect.poll(() => boundary.instance.length, {message: 'the page read the instance configuration through the route'}).toBeGreaterThan(0);
        const served = schemas.InstanceConfigResponse.parse(boundary.instance.at(-1));
        expect(served.profile).toBe('managed');
        expect(served.support_url ?? null).toBeNull();

        await openCreateAssetModal(page);
        const dialog = page.getByTestId('asset-modal');
        await expect(dialog.getByTestId(`asset-search-provider-${premium}`), 'precondition: Search Online asks the provider made premium').toHaveAttribute('data-selected', 'true', {timeout: 10_000});
        await dialog.locator('[data-search-autocomplete] input[type="text"]').fill(query);
        const results = dialog.getByTestId('asset-search-results');
        await expect(results, 'the search ends with results').toHaveAttribute('data-state', 'results', {timeout: 15_000});
        expect(boundary.searches, 'one search, which asked the premium provider and the community one').toEqual([expect.arrayContaining([premium, community])]);

        // The search is over and drawn — its premium results, the community section's button: on a self-hosted instance
        // the report row stands between them by now (the first test of this block). Here there is none.
        await expect(results.getByTestId('asset-search-premium-section').getByTestId('asset-search-result-0')).toHaveAttribute('data-provider', premium);
        const toggle = results.getByTestId('asset-search-community-toggle');
        await expect(toggle).toBeVisible();
        await expect(results.getByTestId('asset-search-report-row')).toHaveCount(0);
        // Nor once the community section is open; and no address of GitHub anywhere in the search block.
        await toggle.click();
        await expect(results.getByTestId('asset-search-community-warning')).toBeVisible();
        await expect(results.getByTestId('asset-search-report-row')).toHaveCount(0);
        await expect(dialog.locator('[data-search-autocomplete] [href*="github.com"]')).toHaveCount(0);

        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toBeHidden();
    });
});
