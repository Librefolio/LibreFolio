/**
 * The profile's data of a new asset (plan 68, E8b2): a whole ISIN in the identifiers starts «Riconosci» by itself;
 * once it is done the automatic «Chiedi» reads the enrichers it found and fills the empty voices «dalla fonte». The
 * «Dati del profilo» row counts the fills, and «Crea Asset» sends them as `{from, seen}`, so the profile is written in
 * the source's name.
 *
 * The lane serves only `mockenrich` (`./dev.py server --test`, E8a): it finds any ISIN and, for a stock, gives its own
 * description. The asset is the test's own (a unique name and ISIN under the user-assigned «ZZ» prefix), deleted by
 * id. Read through test ids, data attributes and the API, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {todayIso} from '../fixtures/dates';
import {API_BASE, goToAssetsPage, openCreateAssetModal} from './assets-helpers';

test.describe('Profile data of a new asset (plan 68, E8b2)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a whole ISIN fills the profile from the enricher, and the creation writes it in the source name', async ({page}) => {
        // The list page loads cold, then the asset window, «Riconosci» and «Chiedi»: more than the default 30 s
        test.setTimeout(60_000);
        const name = `E2E profile create ${uniqueToken(8)}`;
        // ISIN-shaped, under the user-assigned «ZZ» prefix: no real instrument carries it
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        let assetId: number | null = null;
        try {
            await goToAssetsPage(page);
            await openCreateAssetModal(page);
            const nameInput = page.getByTestId('asset-modal-display-name');
            await nameInput.fill(name);
            await expect(nameInput).toHaveValue(name);

            const row = page.getByTestId('asset-modal-profile-row');
            await expect(row).toHaveAttribute('data-count', '0');

            // The identifiers live in «Ulteriori Info», closed on a new asset: open it, only if it is not open yet
            const moreInfo = page.getByTestId('asset-modal-more-info');
            if ((await moreInfo.getAttribute('data-expanded')) !== 'true') await moreInfo.click();
            await expect(moreInfo).toHaveAttribute('data-expanded', 'true');

            // The new asset has no identifier yet: the row added is the first free type, the ISIN
            const identifiers = page.getByTestId('asset-modal-identifiers');
            await identifiers.getByTestId('asset-modal-add-identifier').click();
            const value = identifiers.locator('td[data-column-id="value"] input');
            await expect(value).toHaveCount(1);
            await value.fill(isin);
            await value.blur();

            // «Riconosci» finds the mock, then the automatic «Chiedi» fills the empty voices: the row counts them
            await expect(page.getByTestId('asset-modal-enrichers')).toHaveAttribute('data-count', '1', {timeout: 15_000});
            await expect(row).not.toHaveAttribute('data-count', '0', {timeout: 15_000});

            const [post] = await Promise.all([page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === `${API_BASE}/assets`), page.getByTestId('asset-modal-save').click()]);
            // The id first, so the finally deletes the asset even when a check below fails
            const response = await post.response();
            const created = (await response!.json()) as {results?: Array<{asset_id?: number | null}>};
            assetId = created.results?.[0]?.asset_id ?? null;
            expect(assetId, 'the create response must carry the new asset id').not.toBeNull();
            const sent = (post.postDataJSON() as Array<Record<string, unknown>>)[0];
            expect(sent.enrichers, 'the list «Riconosci» proposed leaves with the asset').toMatchObject({mockenrich: {identifier: isin}});
            expect(sent.profile, 'the fills leave in the source name').toMatchObject({description: {from: 'mockenrich'}});
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 15_000});

            // Created: the profile of today holds the description, written by the enricher
            await expect
                .poll(
                    async () => {
                        const read = await page.request.post(`${API_BASE}/assets/profile/query`, {data: [{asset_id: assetId, date_range: {start: todayIso()}, keys: ['description']}]});
                        const body = (await read.json()) as {items: Array<{voices?: Record<string, Array<{value: unknown; source: string}>>}>};
                        const step = body.items[0]?.voices?.description?.at(-1);
                        return step ? `${String(step.value)} | ${step.source}` : null;
                    },
                    {timeout: 10_000, message: 'the description must be stored in the profile, by the enricher'},
                )
                .toBe(`Mock description of ${isin} | mockenrich`);
        } finally {
            if (assetId !== null) await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
