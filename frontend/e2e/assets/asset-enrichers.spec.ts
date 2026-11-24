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
});
