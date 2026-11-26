/**
 * «Aggiorna» and «Configura» of the «Profilo» tab (plan 68, E6c):
 * - an asset with enrichers shows «Aggiorna» beside «Modifica i dati», with the last read in its hint; a click reads the
 *   enrichers of that asset again (`POST /assets/profile/refresh` with its id) and never touches the prices;
 * - E6c2 (PROF 19/11): with only enrichers this instance cannot use, «Aggiorna» stays, and says nothing was read
 *   (`enrichers_read` 0 in the event), never «nothing changed»;
 * - an asset without enrichers shows the box «Nessun arricchitore configurato»: its «Configura» opens the asset window
 *   with the enrichers' window on top, for that opening only;
 * - 87 A5: the Assets list's «Sync All» window calls the enrichers of every asset that has some, with its own button.
 *
 * The lane serves only `mockenrich` (`./dev.py server --test`, E8a): no step reaches a real site. Each asset is the
 * test's own (a unique name and ISIN under the user-assigned «ZZ» prefix), created over the API and deleted by id. Read
 * through test ids, data attributes, events and the API, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {eventSeq, waitForEvent} from '../fixtures/app-events';
import {API_BASE, goToAssetDetailPage, openEditAssetModal} from './assets-helpers';

type AssetRow = {asset_id: number; enrichers?: {state?: Record<string, {read_at?: string | null}>} | null};

async function createEtf(page: import('@playwright/test').Page, name: string, isin: string, enrichers?: Record<string, unknown>): Promise<number> {
    const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_isin: isin, ...(enrichers ? {enrichers} : {})}]});
    expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
    return ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
}

test.describe('«Aggiorna» and «Configura» on the Profilo tab (plan 68, E6c)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('«Aggiorna» reads the enrichers of this asset again, says the last read, and leaves the prices alone', async ({page}) => {
        test.setTimeout(60_000);
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        const assetId = await createEtf(page, `E2E profile refresh ${uniqueToken(8)}`, isin, {mockenrich: {identifier_type: 'ISIN', identifier: isin}});
        try {
            // The creation starts a read in the background: wait until the asset says it was read
            let readDay = '';
            await expect
                .poll(
                    async () => {
                        const read = await page.request.get(`${API_BASE}/assets?asset_ids=${assetId}`);
                        const row = ((await read.json()) as AssetRow[]).find((item) => item.asset_id === assetId);
                        readDay = String(row?.enrichers?.state?.mockenrich?.read_at ?? '').slice(0, 10);
                        return readDay;
                    },
                    {timeout: 15_000, message: 'the read in the background after the creation'},
                )
                .not.toBe('');

            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            const tab = page.getByTestId('asset-profile-tab');
            await expect(tab).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            await expect(page.getByTestId('asset-profile-no-enrichers')).toHaveCount(0);
            const button = page.getByTestId('asset-profile-refresh');
            await expect(button).toHaveAttribute('data-last-read', readDay);
            await expect(button).toHaveAttribute('data-state', 'idle');

            const paths: string[] = [];
            page.on('request', (request) => paths.push(`${request.method()} ${new URL(request.url()).pathname}`));
            const since = await eventSeq(page);
            const [refresh] = await Promise.all([page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === `${API_BASE}/assets/profile/refresh`), button.click()]);
            expect(refresh.postDataJSON(), 'the refresh asks for this asset only').toEqual([assetId]);
            const event = await waitForEvent(page, 'asset.profile.refreshed', {since});
            expect((event.detail as {asset_id: number}).asset_id).toBe(assetId);
            await expect(button).toHaveAttribute('data-state', 'idle', {timeout: 10_000});
            await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            expect(
                paths.filter((path) => path.includes('/prices') || path.endsWith('/sync')),
                'no price call',
            ).toEqual([]);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('without enrichers, «Configura» opens the asset window with the enrichers window on top, for that opening only', async ({page}) => {
        test.setTimeout(60_000);
        const assetId = await createEtf(page, `E2E profile configure ${uniqueToken(8)}`, `ZZ${uniqueToken(9)}0`.toUpperCase());
        try {
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            await expect(page.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            await expect(page.getByTestId('asset-profile-refresh')).toHaveCount(0);

            await page.getByTestId('asset-profile-configure').click();
            await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 10_000});
            await expect(page.getByTestId('enrichers-modal')).toBeVisible({timeout: 10_000});

            // Closed without changes, then opened from the header: the asset window alone
            await page.getByTestId('enrichers-cancel').click();
            await expect(page.getByTestId('enrichers-modal')).toBeHidden();
            await page.getByTestId('asset-modal-cancel').click();
            await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: 10_000});
            await openEditAssetModal(page);
            await expect(page.getByTestId('asset-modal-enrichers')).toBeVisible();
            await expect(page.getByTestId('enrichers-modal')).toHaveCount(0);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('with only enrichers this instance cannot use, «Aggiorna» says nothing was read (E6c2)', async ({page}) => {
        test.setTimeout(60_000);
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        // An enricher code this instance does not have: the binding is kept (B2), the refresh skips it
        const assetId = await createEtf(page, `E2E profile refresh none ${uniqueToken(8)}`, isin, {notinstalled: {identifier_type: 'ISIN', identifier: isin}});
        try {
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            await expect(page.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            const button = page.getByTestId('asset-profile-refresh');
            await expect(button, 'the button stays: the asset has a binding').toHaveAttribute('data-state', 'idle');

            const since = await eventSeq(page);
            await button.click();
            const event = await waitForEvent(page, 'asset.profile.refreshed', {since});
            expect(event.detail as Record<string, unknown>).toMatchObject({asset_id: assetId, enrichers_read: 0, written: []});
            await expect(button).toHaveAttribute('data-state', 'idle', {timeout: 10_000});
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('«Sync All» calls the enrichers of the assets that have some, apart from the prices, and lists what came of it (87 A5)', async ({page}) => {
        test.setTimeout(60_000);
        const isin = `ZZ${uniqueToken(9)}0`.toUpperCase();
        // No price provider: the profiles' list is not the prices'
        const assetId = await createEtf(page, `E2E profile bulk ${uniqueToken(8)}`, isin, {mockenrich: {identifier_type: 'ISIN', identifier: isin}});
        try {
            // The window's read of who has enrichers, cut to this test's asset: the others are their neighbours' to refresh
            await page.route(
                (url) => url.pathname === `${API_BASE}/assets` && url.searchParams.has('asset_ids'),
                async (route) => {
                    const response = await route.fetch();
                    const rows = (await response.json()) as AssetRow[];
                    await route.fulfill({response, json: rows.map((row) => (row.asset_id === assetId ? row : {...row, enrichers: null}))});
                },
            );
            await page.goto('/assets');
            await page.waitForSelector('[data-testid="assets-page"][data-busy="false"]', {timeout: 20_000});
            const paths: string[] = [];
            page.on('request', (request) => paths.push(`${request.method()} ${new URL(request.url()).pathname}`));
            await page.getByTestId('assets-sync-all-button').click();
            const section = page.getByTestId('asset-sync-profile');
            await expect(section).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(section).toHaveAttribute('data-count', '1');

            const since = await eventSeq(page);
            const [refresh] = await Promise.all([page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === `${API_BASE}/assets/profile/refresh`), page.getByTestId('asset-sync-profile-start').click()]);
            expect(refresh.postDataJSON()).toEqual([assetId]);
            const event = await waitForEvent(page, 'asset.profiles.refreshed', {since});
            expect(event.detail as Record<string, unknown>).toMatchObject({assets: 1, read: 1, failed: 0});
            await expect(section).toHaveAttribute('data-run', 'done');
            await expect(section.getByTestId('asset-sync-profile-row')).toHaveAttribute('data-outcome', /^(written|unchanged)$/);
            expect(
                paths.filter((path) => path.endsWith('/prices/sync')),
                'the prices start by their own button',
            ).toEqual([]);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
