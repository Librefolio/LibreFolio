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
        test.setTimeout(60_000);
        const name = `E2E enrichers ${uniqueToken(8)}`;
        // ISIN-shaped, under the user-assigned «ZZ» prefix: no real instrument carries it
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_isin: isin}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);

            // Edit mode: «Riconosci» never starts by itself, and the asset has no enricher yet
            const button = page.getByTestId('asset-modal-enrichers');
            await expect(button).toHaveAttribute('data-count', '0');
            await expect(page.getByTestId('asset-modal-enrichers-banner')).toHaveCount(0);

            await button.click();
            const window = page.getByTestId('enrichers-modal');
            await expect(window).toBeVisible();
            // «The others» start open: the toggle says so (`aria-expanded`); act only if it is not there yet
            const toggle = window.getByTestId('enrichers-others-toggle');
            await expect(toggle).toBeVisible();
            if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
            await expect(toggle).toHaveAttribute('aria-expanded', 'true');
            await window.getByTestId('enricher-add-mockenrich').click();
            const identifier = window.getByTestId('enricher-identifier-mockenrich');
            await expect(identifier).toBeVisible();
            if ((await identifier.inputValue()) !== isin) await identifier.fill(isin);
            await expect(identifier).toHaveValue(isin);
            // The field commits at every key (E7c): the button is usable right after typing, without letting the field go
            const apply = window.getByTestId('enrichers-apply');
            await expect(apply, 'the binding is not valid right after typing the identifier').toBeEnabled();
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
                        const rows = (await read.json()) as Array<{asset_id: number; enrichers?: {config?: Record<string, {identifier?: string}>} | null}>;
                        return rows.find((row) => row.asset_id === assetId)?.enrichers?.config?.mockenrich?.identifier ?? null;
                    },
                    {timeout: 10_000, message: 'the binding must be stored with the asset'},
                )
                .toBe(isin);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
