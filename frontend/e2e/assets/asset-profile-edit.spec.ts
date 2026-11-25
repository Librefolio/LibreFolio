/**
 * The profile's data from the asset window (plan 68, E8b2): the «Dati del profilo» row opens the profile window over the
 * asset window; «Tieni le modifiche» hands the changes back without saving, the row counts them, and «Salva Modifiche»
 * sends them with the asset. From the «Profilo» tab of the asset page (E9b2), «Modifica i dati» opens the same window in
 * save mode: «Salva Tutto» writes the profile alone, and the tab reads it again.
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

    test('«Modifica i dati» of the Profilo tab saves on its own, and the tab reads the profile again (E9b2)', async ({page}) => {
        test.setTimeout(60_000);
        const name = `E2E profile tab ${uniqueToken(8)}`;
        // A profile from the start: the tab shows its data, and «Modifica i dati» with them
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {description: 'A fund of the test'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            const tab = page.getByTestId('asset-profile-tab');
            await expect(tab).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            await tab.getByTestId('asset-profile-edit').click();
            const window = page.getByTestId('profile-edit-modal');
            await expect(window).toBeVisible({timeout: 10_000});

            // A row for the TER, typed in percent: 0.19 % is the fraction 0.0019
            await window.getByTestId('profile-edit-add-row').click();
            await window.getByTestId('profile-row-voice-row-1-button').click();
            await page.getByTestId('profile-row-voice-row-1-option-ter').click();
            const value = window.locator('tr[data-row-id="row-1"] td[data-column-id="value"] input');
            await value.fill('0.19');
            await value.blur();
            await expect(window.getByTestId('profile-edit-validity')).toHaveAttribute('data-valid', 'true');

            // «Salva Tutto»: the window writes the profile alone, then closes
            const [patch] = await Promise.all([page.waitForRequest((request) => request.method() === 'PATCH' && new URL(request.url()).pathname === `${API_BASE}/assets`), window.getByTestId('profile-edit-save').click()]);
            expect(patch.postDataJSON()).toEqual([{asset_id: assetId, profile: {ter: '0.0019'}}]);
            await expect(window).toBeHidden({timeout: 15_000});

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
            // The tab read the profile again, and is done reading
            await expect(tab).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(tab).toHaveAttribute('data-busy', 'false');
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});

/**
 * The selection bar in a narrow section head (plan 77, SEL-D2). In the profile window the sectors and the countries sit
 * side by side, and their heads are about 450 px wide at 1440 (280 px at 390): the whole bar («2 sélectionnés ×»,
 * «Équilibrer 2», «Supprimer 2») does not fit beside the title and the section's buttons. So the bar takes its compact
 * form («2 ×», each action an icon with its number), the title gives it its place while rows are ticked (visually hidden,
 * kept for screen readers), and the head keeps its height. A bar never covers a control of the head: the check reads
 * the boxes, in a long language (French), at 1440 and 390. The compact form is a container query on the head: only a
 * browser measures it. The keyboard reaches each icon's name: its tooltip opens on focus.
 */
for (const width of [1440, 390]) {
    test.describe(`The selection bar in a narrow section head, French, ${width} px (77 SEL-D2)`, () => {
        test.use({viewport: {width, height: 900}, isMobile: false, hasTouch: false});

        test.beforeEach(async ({page}) => {
            await page.addInitScript(() => {
                try {
                    localStorage.setItem('librefolio-locale', 'fr');
                } catch {
                    // a context without storage keeps the default language; the checks below hold in any language
                }
            });
            await login(page, TEST_USER);
        });

        test('ticking two sectors keeps the head’s height: the bar is compact, and its icons name themselves on focus', async ({page}) => {
            test.setTimeout(60_000);
            const name = `E2E profile head ${uniqueToken(8)}`;
            const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF'}]});
            expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
            const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
            try {
                await goToAssetDetailPage(page, String(assetId));
                await openEditAssetModal(page);
                await page.getByTestId('asset-modal-profile-row').click();
                const window = page.getByTestId('profile-edit-modal');
                const sector = window.getByTestId('distribution-editor-sector');
                await expect(sector).toBeVisible({timeout: 15_000});

                // Three sectors of the test's own asset; the first at 50 %, so the total is short and «Bilancia» is offered
                for (let i = 0; i < 3; i++) await window.getByTestId('distribution-add-sector').click();
                const rows = sector.locator('tbody tr[data-row-id]');
                await expect(rows).toHaveCount(3);
                const weight = rows.nth(0).locator('td input').last();
                await weight.fill('50');
                await weight.blur();
                await expect(sector.getByTestId('distribution-total-sector')).toHaveAttribute('data-state', 'missing');

                const head = sector.getByTestId('distribution-head-sector');
                const heightOf = async () => Math.round((await head.boundingBox())?.height ?? -1);
                const before = await heightOf();
                await rows.nth(1).locator('[data-testid^="dt-row-checkbox-"]').click();
                await rows.nth(2).locator('[data-testid^="dt-row-checkbox-"]').click();

                const bar = head.getByTestId('selection-toolbar');
                await expect(bar).toHaveAttribute('data-in-head', 'true');
                await expect(page.locator('html')).toHaveAttribute('lang', 'fr');
                await expect(bar.getByTestId('toolbar-action-balance-count')).toHaveText('2');
                await expect(bar.getByTestId('toolbar-action-balance-label')).toBeHidden();
                expect(await heightOf(), 'the head keeps its height with the bar').toBe(before);
                // A height alone can hide a bar drawn over the section's buttons: none of them meets the bar, all stay inside
                const clash = await head.evaluate((el) => {
                    const toolbar = el.querySelector('[data-testid="selection-toolbar"]');
                    if (!toolbar) return 'no bar';
                    const b = toolbar.getBoundingClientRect();
                    const h = el.getBoundingClientRect();
                    const found: string[] = [];
                    for (const button of el.querySelectorAll('button')) {
                        if (toolbar.contains(button)) continue;
                        const o = button.getBoundingClientRect();
                        if (o.left < b.right - 1 && o.right > b.left + 1 && o.top < b.bottom && o.bottom > b.top) found.push(`${button.dataset.testid} under the bar`);
                        if (o.right > h.right + 1) found.push(`${button.dataset.testid} outside the head by ${Math.round(o.right - h.right)} px (head ${Math.round(h.width)} px, bar ${Math.round(b.width)} px, button ${Math.round(o.width)} px)`);
                    }
                    return found.join(', ');
                });
                expect(clash, 'the bar covers none of the section’s buttons').toBe('');

                // An icon names itself: the accessible name carries the number, and the tooltip opens on keyboard focus
                const balance = bar.getByTestId('toolbar-action-balance');
                await expect(balance).toHaveAttribute('aria-label', /, 2$/);
                await balance.focus();
                await expect(page.getByTestId('tooltip-content')).toBeVisible();
            } finally {
                await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
            }
        });
    });
}
