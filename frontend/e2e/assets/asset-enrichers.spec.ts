/**
 * The enrichers of an asset, from the asset window (plan 68, E8a): the «Arricchitori» button beside «Chiedi al
 * Provider» opens the enrichers' window over the asset window; the list it hands back is saved with the asset.
 *
 * The lane serves only `mockenrich` (`./dev.py server --test`, E8a): no step here reaches a real site. The asset is
 * the test's own (a unique name and ISIN under the user-assigned «ZZ» prefix), created over the API and deleted by id.
 * Read through test ids and the API, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {API_BASE, goToAssetDetailPage, openEditAssetModal} from './assets-helpers';

test.describe('Asset enrichers from the asset window (plan 68, E8a)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('an enricher chosen in the window is saved with the asset, in its binding', async ({page}) => {
        // The detail page loads cold, then the asset window, then the enrichers' window: more than the default 30 s
        test.setTimeout(120_000);
        const name = `E2E enrichers ${uniqueToken(8)}`;
        // ISIN-shaped, under the user-assigned «ZZ» prefix: no real instrument carries it
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_isin: isin}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);

            // The asset has no enricher yet, and no creation banner (that one is for a new asset)
            const button = page.getByTestId('asset-modal-enrichers');
            await expect(button).toHaveAttribute('data-count', '0');
            await expect(page.getByTestId('asset-modal-enrichers-banner')).toHaveCount(0);

            // In edit mode «Riconosci» starts when the window opens, with the ISIN the asset already holds (ENR-1, R1)
            await button.click();
            const window = page.getByTestId('enrichers-modal');
            await expect(window).toBeVisible();
            await expect(window.getByTestId('enrichers-recognition')).toHaveAttribute('data-state', 'found', {timeout: 20_000});
            // Found, the enricher enters the list by itself (R2), already bound: nothing to type
            const row = window.getByTestId('enricher-row-mockenrich');
            await expect(row).toBeVisible();
            await expect(window.getByTestId('enricher-other-mockenrich')).toHaveCount(0);
            const apply = window.getByTestId('enrichers-apply');
            await expect(apply).toBeEnabled();
            await apply.click();
            await expect(window).toBeHidden();
            await expect(button).toHaveAttribute('data-count', '1');

            const [patch] = await Promise.all([page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === `${API_BASE}/assets`), page.getByTestId('asset-modal-save').click()]);
            const sent = (patch.postDataJSON() as Array<Record<string, unknown>>)[0];
            expect(sent.enrichers, 'the asset window sends the list the window handed back').toMatchObject({mockenrich: {identifier: isin}});
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 15_000});

            // Saved: the asset's enrichers, as GET /assets answers them
            await expect
                .poll(
                    async () => {
                        const read = await page.request.get(`${API_BASE}/assets?asset_ids=${assetId}`);
                        const rows = (await read.json()) as Array<{asset_id: number; enrichers?: {config?: Record<string, {identifier?: string; identifier_type?: string}>} | null}>;
                        const binding = rows.find((row) => row.asset_id === assetId)?.enrichers?.config?.mockenrich;
                        return binding ? `${binding.identifier_type}:${binding.identifier}` : null;
                    },
                    {timeout: 10_000, message: 'the binding must be stored with the asset'},
                )
                .toBe(`ISIN:${isin}`);

            // Again: the asset has the enricher now, so nothing adopts; 🗑 sends it to «Non in elenco» and «+» puts it back
            // already bound (it keeps its binding), the row closed: nothing to type
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);
            await page.getByTestId('asset-modal-enrichers').click();
            const again = page.getByTestId('enrichers-modal');
            await expect(again).toBeVisible();
            await expect(again.getByTestId('enrichers-recognition')).toHaveAttribute('data-state', /^(found|none)$/, {timeout: 20_000});
            await expect(again.getByTestId('enricher-row-mockenrich')).toBeVisible();
            await again.getByTestId('enricher-remove-mockenrich').click();
            await expect(again.getByTestId('enricher-row-mockenrich')).toHaveCount(0);
            await again.getByTestId('enricher-add-mockenrich').click();
            const back = again.getByTestId('enricher-row-mockenrich');
            await expect(back).toBeVisible();
            await expect(back).toHaveAttribute('data-expanded', 'false');
            await expect(back).not.toHaveAttribute('data-issue', /.+/);
            await back.getByTestId('enricher-edit-mockenrich').click();
            await expect(back.getByTestId('enricher-identifier-mockenrich')).toHaveValue(isin);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
    /** An asset of this test with NO identifier at all (so «Riconosci» has nothing to start from), created over the API. */
    async function createBareAsset(page: import('@playwright/test').Page, name: string): Promise<number> {
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF'}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        return ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
    }

    /** The asset's mockenrich binding as GET /assets answers it, `TYPE:identifier`, null while there is none. */
    async function readBinding(page: import('@playwright/test').Page, assetId: number): Promise<string | null> {
        const read = await page.request.get(`${API_BASE}/assets?asset_ids=${assetId}`);
        const rows = (await read.json()) as Array<{asset_id: number; enrichers?: {config?: Record<string, {identifier?: string; identifier_type?: string}>} | null}>;
        const binding = rows.find((row) => row.asset_id === assetId)?.enrichers?.config?.mockenrich;
        return binding ? `${binding.identifier_type}:${binding.identifier}` : null;
    }

    test('«Cerca online» adds an enricher from a result, the search stays open, and the binding is saved (ENR-3)', async ({page}) => {
        test.setTimeout(120_000);
        const name = `E2E enrichers search ${uniqueToken(8)}`;
        // What mockenrich's search binds: the typed text upper-cased, a TICKER when it is not ISIN-shaped
        const typed = `srch ${uniqueToken(6)}`;
        const assetId = await createBareAsset(page, name);
        try {
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);
            const button = page.getByTestId('asset-modal-enrichers');
            await expect(button).toHaveAttribute('data-count', '0');
            await button.click();
            const window = page.getByTestId('enrichers-modal');
            await expect(window).toBeVisible();

            const search = window.getByTestId('enrichers-search');
            const input = window.getByTestId('enrichers-search-input');
            const pill = window.getByTestId('enrichers-search-pill-mockenrich');
            await expect(pill).toBeVisible();
            await input.fill(typed);
            await expect(input).toHaveValue(typed);
            await expect(search).toHaveAttribute('data-status', 'done', {timeout: 20_000});

            // The row of this enricher (found by what it is, not where it is), then its «+»
            const row = window.locator('[data-testid^="enrichers-search-row-"][data-code="mockenrich"]');
            await expect(row).toBeVisible();
            await row.locator('[data-testid^="enrichers-search-add-"]').click();

            // It is in «Scelti», the search is still there with its text, and the pill is gone
            await expect(window.getByTestId('enricher-row-mockenrich')).toBeVisible();
            await expect(search).toBeVisible();
            await expect(input).toHaveValue(typed);
            await expect(pill).toHaveCount(0);
            await expect(row).toHaveCount(0);

            await window.getByTestId('enrichers-apply').click();
            await expect(window).toBeHidden();
            await expect(button).toHaveAttribute('data-count', '1');
            const [patch] = await Promise.all([page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === `${API_BASE}/assets`), page.getByTestId('asset-modal-save').click()]);
            const sent = (patch.postDataJSON() as Array<Record<string, unknown>>)[0];
            expect(sent.enrichers, 'the asset window sends the list the window handed back').toMatchObject({mockenrich: {identifier_type: 'TICKER', identifier: typed.toUpperCase()}});
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 15_000});
            await expect.poll(() => readBinding(page, assetId), {timeout: 10_000, message: 'the binding must be stored with the asset'}).toBe(`TICKER:${typed.toUpperCase()}`);

            // Again: 🗑 on the enricher brings its pill back
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);
            await page.getByTestId('asset-modal-enrichers').click();
            const again = page.getByTestId('enrichers-modal');
            await expect(again).toBeVisible();
            await expect(again.getByTestId('enricher-row-mockenrich')).toBeVisible();
            await expect(again.getByTestId('enrichers-search-pill-mockenrich')).toHaveCount(0);
            await again.getByTestId('enricher-remove-mockenrich').click();
            await expect(again.getByTestId('enricher-row-mockenrich')).toHaveCount(0);
            await expect(again.getByTestId('enrichers-search-pill-mockenrich')).toBeVisible();
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('«Cerca online» fits a phone: the «+» of a result is inside the screen and the page does not scroll sideways (ENR-3)', async ({page}) => {
        test.setTimeout(120_000);
        const name = `E2E enrichers phone ${uniqueToken(8)}`;
        const typed = `phone ${uniqueToken(6)}`;
        const assetId = await createBareAsset(page, name);
        try {
            await page.setViewportSize({width: 390, height: 844});
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);
            await page.getByTestId('asset-modal-enrichers').click();
            const window = page.getByTestId('enrichers-modal');
            await expect(window).toBeVisible();

            await window.getByTestId('enrichers-search-input').fill(typed);
            await expect(window.getByTestId('enrichers-search')).toHaveAttribute('data-status', 'done', {timeout: 20_000});
            const row = window.locator('[data-testid^="enrichers-search-row-"][data-code="mockenrich"]');
            await expect(row).toBeVisible();
            const add = row.locator('[data-testid^="enrichers-search-add-"]');
            await add.scrollIntoViewIfNeeded();
            await expect(add).toBeVisible();

            const inside = async () => {
                const box = await add.boundingBox();
                const viewport = page.viewportSize();
                if (!box || !viewport) return false;
                return box.x >= 0 && box.x + box.width <= viewport.width && box.y >= 0 && box.y + box.height <= viewport.height;
            };
            await expect.poll(inside, {message: 'the «+» is inside the viewport'}).toBe(true);
            await expect.poll(() => page.evaluate(() => (document.scrollingElement?.scrollWidth ?? 0) <= (document.scrollingElement?.clientWidth ?? 0)), {message: 'no horizontal scroll'}).toBe(true);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
