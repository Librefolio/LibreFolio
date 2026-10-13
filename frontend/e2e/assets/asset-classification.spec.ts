/**
 * Asset Classification — E2E Tests
 *
 * Tests the distribution editor round-trip: add geo/sector entries → save → reopen → verify persistence,
 * and that the editor speaks the UI language (weight column header, total badge).
 *
 * Prerequisites:
 * - Test server running (./dev.py server --test)
 * - Database populated (./dev.py test db populate --force)
 */

import {readFileSync} from 'node:fs';
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {uniqueSuffix} from '../fixtures/unique';
import {API_BASE, goToAssetsPage, openCreateAssetModal} from './assets-helpers';

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
async function saveAndRecordCreated(page: Page, owned: OwnedAssets | undefined, name: string, save: () => Promise<void>): Promise<number> {
    owned?.set(name, null);
    const [response] = await Promise.all([page.waitForResponse((r) => r.request().method() === 'POST' && new URL(r.url()).pathname === `${API_BASE}/assets`, {timeout: 15_000}), save()]);
    return recordCreated(response, owned, name);
}

/** Read a POST /assets answer: record the id it gives `name`, then require that the create succeeded. */
async function recordCreated(response: HttpResponse, owned: OwnedAssets | undefined, name: string): Promise<number> {
    const body = (await response.json().catch(() => null)) as CreateBody | null;
    const result = body?.results?.find((item) => item.display_name === name);
    // Recorded before any assertion can throw: whatever was created gets deleted.
    if (typeof result?.asset_id === 'number') owned?.set(name, result.asset_id);
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

/** Helper: create asset, return to detail page, open edit modal. `owned` records the asset the moment it exists. */
async function createAssetAndOpenEdit(page: import('@playwright/test').Page, name: string, owned?: OwnedAssets) {
    await goToAssetsPage(page);
    await openCreateAssetModal(page);

    // Fill name
    const nameInput = page.getByTestId('asset-modal-display-name');
    await nameInput.fill(name);

    // Save — the create response names the new asset's id, recorded for the afterEach
    const saveBtn = page.getByTestId('asset-modal-save');
    await expect(saveBtn).toBeEnabled({timeout: 5000});
    await saveAndRecordCreated(page, owned, name, () => saveBtn.click());
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
    // Each test creates one asset through the modal: its id is recorded the moment the create
    // response names it, and the afterEach deletes exactly that asset, by id.
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
    // Test 1: Set geographic distribution → save → reopen → present
    // ========================================================================
    test('geo distribution persists after save and reopen', async ({page}) => {
        const assetName = `E2E Geo Test ${uniqueSuffix()}`;
        await createAssetAndOpenEdit(page, assetName, owned);

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
        const assetName = `E2E Sector Test ${uniqueSuffix()}`;
        await createAssetAndOpenEdit(page, assetName, owned);

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
        const assetName = `E2E Clear Test ${uniqueSuffix()}`;
        await createAssetAndOpenEdit(page, assetName, owned);

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

// ============================================================================
// The editor in the UI language: weight column header and total badge
// ============================================================================

/** The catalogue key the weight column header is to be read from. */
const WEIGHT_HEADER_KEY = 'assets.distribution.weightPercent';
/**
 * What DistributionEditor.svelte hard-codes for that header today, in every
 * language. Asserted only as text a French screen must NOT show: it is the
 * defect, never an expectation.
 */
const HARD_CODED_WEIGHT_HEADER = 'Weight %';
/** French notation for a share with two decimals — what the total badge is to print. */
const FRENCH_PERCENT = new Intl.NumberFormat('fr', {style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2});
/** A label renders with its table and nothing loads in between: a short wait is honest, and keeps the soft reds inside the budget. */
const LABEL_MS = 2_000;

/** A string of the catalogue the app ships for `lang`, or `undefined` when the key is absent. */
function catalogueString(lang: 'en' | 'fr', key: string): string | undefined {
    const catalogue: unknown = JSON.parse(readFileSync(new URL(`../../src/lib/i18n/${lang}.json`, import.meta.url), 'utf8'));
    const value = key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
    return typeof value === 'string' ? value : undefined;
}

/**
 * Undo the localisation test: delete the asset it created — found by its
 * unique name, since the id is unknown if setup stopped early — and put the UI
 * back in English. Each step runs on its own and reports softly, so a cleanup
 * failure is listed beside the test's result instead of replacing it, as a
 * throw from `finally` would.
 */
async function releaseLocalisedEdit(page: Page, assetName: string): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, step: () => Promise<void>) => {
        try {
            await step();
        } catch (error) {
            failures.push(`${label}: ${error instanceof Error ? error.message : String(error)}`);
        }
    };
    await attempt('delete the asset', async () => {
        const found = await page.request.get(`/api/v1/assets/query?search=${encodeURIComponent(assetName)}`);
        if (!found.ok()) throw new Error(`asset query answered ${found.status()}: ${await found.text()}`);
        const ids = ((await found.json()) as Array<{id: number; display_name: string}>).filter((asset) => asset.display_name === assetName).map((asset) => asset.id);
        for (const id of ids) {
            const deleted = await page.request.delete(`/api/v1/assets?asset_ids=${id}`);
            const body = (await deleted.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
            if (!deleted.ok() || body?.results?.find((result) => result.asset_id === id)?.success !== true) throw new Error(`asset ${id}: HTTP ${deleted.status()} ${JSON.stringify(body)}`);
        }
    });
    await attempt('restore English', async () => {
        // The edit modal's backdrop covers the header that holds the selector, and the
        // row added by the test must not be saved: leaving the page drops both. The
        // selector writes only this browser context's localStorage, so this is hygiene,
        // not isolation — no other test can see the French.
        await navigateTo(page, '/assets');
        await setLanguage(page, 'en');
    });
    expect.soft(failures, 'cleanup touches only what this test created').toEqual([]);
}

test.describe('Distribution editor in the UI language', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    /**
     * Two defects workstream M found in the French gallery screenshots:
     *
     * 1. the weight column header is the literal 'Weight %' in every language; it is
     *    to be read from `assets.distribution.weightPercent`;
     * 2. the total badge prints `toFixed(2)` and a `%`, so French reads "100.00%" instead of
     *    French notation (decimal comma, no-break space before `%`), which
     *    `formatPercent` is to produce when given the UI language.
     *
     * The positive control is the key column's header, which the same header row
     * already reads from the catalogue: it proves the table is on screen and in
     * French, so an English header beside it is a hard-coded one. Every expected
     * string comes from fr.json or from Intl.
     */
    test('the geographic editor reads its weight header from fr.json and writes the total in French notation', async ({page}) => {
        const assetName = `E2E Geo FR ${uniqueSuffix()}`;
        try {
            await setLanguage(page, 'fr');
            await createAssetAndOpenEdit(page, assetName);
            await expandMoreInfo(page);

            // One entry on a fresh asset; the total badge renders only once it exists.
            const geoEditor = page.getByTestId('distribution-editor-geographic');
            await geoEditor.getByTestId('distribution-add-geographic').click();
            const total = geoEditor.getByTestId('distribution-total-geographic');
            await expect(total).toBeVisible({timeout: 10_000});

            // Positive control: the key column, in the same header row, already speaks French.
            const geoHeader = catalogueString('fr', 'common.geoDistribution');
            if (geoHeader === undefined) throw new Error('fr.json has no common.geoDistribution, which the positive control reads');
            await expect(geoEditor.getByTestId('dt-header-key')).toHaveText(geoHeader);

            // 1 — the weight column header.
            const weightHeader = geoEditor.getByTestId('dt-header-weight');
            await expect(weightHeader).toBeVisible();
            const frWeightHeader = catalogueString('fr', WEIGHT_HEADER_KEY);
            await expect.soft(weightHeader, `weight header = fr.json ${WEIGHT_HEADER_KEY}${frWeightHeader === undefined ? ' (fr.json has no such key)' : ''}`).toHaveText(frWeightHeader ?? `<${WEIGHT_HEADER_KEY} missing from fr.json>`, {timeout: LABEL_MS});
            await expect.soft(weightHeader, 'weight header is not the English literal hard-coded in DistributionEditor.svelte').not.toHaveText(HARD_CODED_WEIGHT_HEADER, {timeout: LABEL_MS});

            // 2 — the total badge, computed from the weight the entry publishes, not an assumed 100.
            const entries = geoEditor.locator('[data-testid^="distribution-entry-geographic-"]');
            await expect(entries, 'one add on a fresh asset makes one entry').toHaveCount(1);
            const weight = Number(await entries.getAttribute('data-weight'));
            expect(weight, 'the new entry publishes its weight').toBeGreaterThan(0);
            const frenchTotal = FRENCH_PERCENT.format(weight / 100);
            expect(frenchTotal, 'this runtime has French ICU data (decimal comma)').toContain(',');
            await expect.soft(total, `total badge in French notation, ${JSON.stringify(frenchTotal)}`).toContainText(frenchTotal, {timeout: LABEL_MS});
        } finally {
            await releaseLocalisedEdit(page, assetName);
        }
    });
});
