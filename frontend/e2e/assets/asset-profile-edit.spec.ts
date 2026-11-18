/**
 * The profile's data from the asset window (plan 68, E8b2): the «Dati del profilo» row opens the profile window over the
 * asset window; «Tieni le modifiche» hands the changes back without saving, the row counts them, and «Salva Modifiche»
 * sends them with the asset.
 *
 * The asset is the test's own (a unique name), created over the API and deleted by id. Read through test ids, data
 * attributes and the API, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {todayIso} from '../fixtures/dates';
import {API_BASE, goToAssetDetailPage, openEditAssetModal} from './assets-helpers';

test.describe('Profile data from the asset window (plan 68, E8b2)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a value kept in the profile window waits in the asset window and is saved with the asset', async ({page}) => {
        // The detail page loads cold, then the asset window, then the profile window: more than the default 30 s
        test.setTimeout(60_000);
        const name = `E2E profile ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF'}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await openEditAssetModal(page);

            const row = page.getByTestId('asset-modal-profile-row');
            await expect(row).toHaveAttribute('data-count', '0');
            await row.click();
            const window = page.getByTestId('profile-edit-modal');
            await expect(window).toBeVisible();

            // A row for the TER, typed in percent: 0.19 % is the fraction 0.0019
            await window.getByTestId('profile-edit-add-row').click();
            await window.getByTestId('profile-row-voice-row-1-button').click();
            // The voice menu opens at the end of the page, outside the window: its option is looked up on the page
            await page.getByTestId('profile-row-voice-row-1-option-ter').click();
            const value = window.locator('tr[data-row-id="row-1"] td[data-column-id="value"] input');
            await value.fill('0.19');
            await value.blur();
            await expect(window.getByTestId('profile-edit-validity')).toHaveAttribute('data-valid', 'true');
            await window.getByTestId('profile-edit-keep').click();
            await expect(window).toBeHidden({timeout: 10_000});

            // Kept, not saved: the asset window counts it, and sends it with «Salva Modifiche»
            await expect(row).toHaveAttribute('data-count', '1');
            const [patch] = await Promise.all([page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === `${API_BASE}/assets`), page.getByTestId('asset-modal-save').click()]);
            expect((patch.postDataJSON() as Array<Record<string, unknown>>)[0].profile).toEqual({ter: '0.0019'});
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 15_000});

            // Saved: the profile of today holds the TER, written by the user
            await expect
                .poll(
                    async () => {
                        const read = await page.request.post(`${API_BASE}/assets/profile/query`, {data: [{asset_id: assetId, date_range: {start: todayIso()}, keys: ['ter']}]});
                        const body = (await read.json()) as {items: Array<{voices?: Record<string, Array<{value: unknown; source: string}>>}>};
                        const step = body.items[0]?.voices?.ter?.at(-1);
                        return step ? `${String(step.value)} ${step.source}` : null;
                    },
                    {timeout: 10_000, message: 'the TER must be stored in the profile, by the user'},
                )
                .toBe('0.0019 user');
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
