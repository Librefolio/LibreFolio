/**
 * «Ultime variazioni» on the «Profilo» tab (plan 68, E6a): the panel is folded and closed; opened, it lists the asset's
 * latest changes — each with its kind of sentence and who wrote it — and «Dimentica» takes one out of the history after
 * a confirmation, as if it had never been written: «now» goes back to the value before, and the card shows it.
 *
 * The asset is the test's own (a unique name), created over the API with two values of the TER written by hand, and
 * deleted by id. Read through test ids, data attributes and the API, never through translated text.
 */
import {expect, test} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueToken} from '../fixtures/unique';
import {todayIso} from '../fixtures/dates';
import {API_BASE, goToAssetDetailPage} from './assets-helpers';

type Change = {id: number; key: string; source: string};

test.describe('«Ultime variazioni» on the Profilo tab (plan 68, E6a)', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('lists the changes by hand with their author, and «Dimentica» puts the TER back to the value before', async ({page}) => {
        // The detail page loads cold, then the tab, then the panel's read
        test.setTimeout(60_000);
        const name = `E2E profile changes ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {ter: '0.0022'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            const patched = await page.request.patch(`${API_BASE}/assets`, {data: [{asset_id: assetId, profile: {ter: '0.0019'}}]});
            expect(patched.status(), `PATCH ${API_BASE}/assets: ${await patched.text()}`).toBe(200);
            const read = await page.request.post(`${API_BASE}/assets/profile/query`, {data: [{asset_id: assetId, date_range: {start: todayIso()}, keys: [], changes: {}}]});
            const changes = ((await read.json()) as {items: Array<{changes: {items: Change[]}}>}).items[0].changes.items.filter((change) => change.key === 'ter');
            expect(
                changes.map((change) => change.source),
                'two TER rows by hand',
            ).toEqual(['user', 'user']);
            const [latest, first] = changes;

            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            const tab = page.getByTestId('asset-profile-tab');
            await expect(tab).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            const value = page.getByTestId('profile-key-figure-ter-value');
            const shownBefore = (await value.textContent())?.trim() ?? '';
            expect(shownBefore, 'barrier: the card shows the TER').not.toBe('');

            const panel = page.getByTestId('profile-changes-panel');
            await expect(panel).toHaveAttribute('data-open', 'false');
            await page.getByTestId('profile-changes-toggle').click();
            await expect(panel).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(page.getByTestId(`profile-change-what-${latest.id}`)).toHaveAttribute('data-kind', 'byHand');
            await expect(page.getByTestId(`profile-change-what-${first.id}`)).toHaveAttribute('data-kind', 'firstByHand');
            // «Prima» and «Dopo» in two columns (87 A3): the value before of the latest is the value after of the first
            await expect(page.getByTestId(`profile-change-before-${first.id}`)).toHaveAttribute('data-empty', 'true');
            const firstValue = ((await page.getByTestId(`profile-change-after-${first.id}`).textContent()) ?? '').trim();
            expect(firstValue).not.toBe('');
            await expect(page.getByTestId(`profile-change-before-${latest.id}`)).toHaveText(firstValue);
            const who = page.getByTestId(`profile-change-who-${latest.id}`);
            await expect(who).toHaveAttribute('data-source', 'user');
            // «Chi» stays in sight beside the two values: the columns fit the table, nothing scrolls sideways (87 A3)
            const hidden = await page
                .getByTestId('profile-changes-table')
                .locator('table')
                .evaluate((table) => {
                    let scroller: HTMLElement | null = table.parentElement;
                    while (scroller && !/auto|scroll/.test(getComputedStyle(scroller).overflowX)) scroller = scroller.parentElement;
                    return scroller ? scroller.scrollWidth - scroller.clientWidth : 0;
                });
            expect(hidden, 'the table scrolls sideways').toBeLessThanOrEqual(1);
            await expect(who).toContainText(TEST_USER.username);

            // «Dimentica» on the latest row: it asks first
            await page.getByTestId(`row-actions-${latest.id}`).click();
            await page.getByTestId(`profile-change-forget-${latest.id}`).click();
            await expect(page.getByTestId('profile-changes-confirm')).toBeVisible();
            const [forget] = await Promise.all([page.waitForRequest((request) => request.method() === 'DELETE' && new URL(request.url()).pathname === `${API_BASE}/assets/profile`), page.getByTestId('confirm-modal-confirm').click()]);
            expect((forget.postDataJSON() as Array<{update_ids: number[]}>)[0].update_ids).toEqual([latest.id]);

            // The row is gone, and «now» is the value before: the API says so, and the card shows another value
            await expect(page.getByTestId(`profile-change-what-${latest.id}`)).toHaveCount(0, {timeout: 10_000});
            await expect
                .poll(
                    async () => {
                        const now = await page.request.post(`${API_BASE}/assets/profile/query`, {data: [{asset_id: assetId, date_range: {start: todayIso()}, keys: ['ter']}]});
                        return String(((await now.json()) as {items: Array<{voices?: Record<string, Array<{value: unknown}>>}>}).items[0]?.voices?.ter?.at(-1)?.value ?? '');
                    },
                    {timeout: 10_000, message: 'the TER goes back to the value before'},
                )
                .toBe('0.0022');
            await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            await expect(value).not.toHaveText(shownBefore, {timeout: 10_000});
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('at phone width the open panel stays inside the page: only its table scrolls sideways', async ({page}) => {
        test.setTimeout(60_000);
        await page.setViewportSize({width: 390, height: 844});
        const name = `E2E profile changes phone ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {ter: '0.0022', description: 'A fund of the test, with a description long enough to wrap on a phone.'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            const patched = await page.request.patch(`${API_BASE}/assets`, {data: [{asset_id: assetId, profile: {ter: '0.0019'}}]});
            expect(patched.status(), `PATCH ${API_BASE}/assets: ${await patched.text()}`).toBe(200);
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            await expect(page.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            await page.getByTestId('profile-changes-toggle').click();
            const panel = page.getByTestId('profile-changes-panel');
            await expect(panel).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(panel.locator('[data-testid^="profile-change-what-"]')).toHaveCount(3);
            // On a phone the values carry their day and their author under them (one column, the mock's shot 14)
            await expect(panel.locator('[data-testid^="profile-change-detail-"]')).toHaveCount(3);
            await panel.scrollIntoViewIfNeeded();

            const sizes = await page.evaluate(() => ({page: document.scrollingElement?.scrollWidth ?? 0, viewport: window.innerWidth}));
            expect(sizes.page, `the page must not scroll sideways: ${JSON.stringify(sizes)}`).toBeLessThanOrEqual(sizes.viewport);
            const box = await panel.boundingBox();
            expect(box && box.x >= 0 && box.x + box.width <= 390, `the panel inside the screen: ${JSON.stringify(box)}`).toBe(true);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('the TER card opens its «Storia del dato»: the chart and every row of the voice, and «Dimentica» there puts the card back (E6b)', async ({page}) => {
        test.setTimeout(60_000);
        const name = `E2E profile history ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {ter: '0.0022'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            const patched = await page.request.patch(`${API_BASE}/assets`, {data: [{asset_id: assetId, profile: {ter: '0.0019'}}]});
            expect(patched.status(), `PATCH ${API_BASE}/assets: ${await patched.text()}`).toBe(200);
            const read = await page.request.post(`${API_BASE}/assets/profile/query`, {data: [{asset_id: assetId, date_range: {start: todayIso()}, keys: [], changes: {key: 'ter'}}]});
            const [latest] = ((await read.json()) as {items: Array<{changes: {items: Change[]}}>}).items[0].changes.items;

            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            const tab = page.getByTestId('asset-profile-tab');
            await expect(tab).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            const value = page.getByTestId('profile-key-figure-ter-value');
            const shownBefore = (await value.textContent())?.trim() ?? '';

            await page.getByTestId('profile-key-figure-ter-history').click();
            const history = page.getByTestId('profile-history');
            await expect(history).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(history).toHaveAttribute('data-voice', 'ter');
            // Two values of the same day: one step, the later; the voice's rows are both in the table, without «Dato»
            await expect(page.getByTestId('profile-history-chart')).toHaveAttribute('data-hand-count', '1');
            await expect(history.locator('[data-testid^="profile-change-what-"]')).toHaveCount(2);
            await expect(history.getByTestId('dt-header-voice')).toHaveCount(0);

            await history.getByTestId(`row-actions-${latest.id}`).click();
            await page.getByTestId(`profile-change-forget-${latest.id}`).click();
            await expect(page.getByTestId('profile-changes-confirm')).toBeVisible();
            await page.getByTestId('confirm-modal-confirm').click();

            await expect(history.getByTestId(`profile-change-what-${latest.id}`)).toHaveCount(0, {timeout: 10_000});
            await expect(history).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await page.getByTestId('profile-history-close').click();
            await expect(history).toHaveCount(0);
            await expect(tab).toHaveAttribute('data-busy', 'false', {timeout: 10_000});
            await expect(value).not.toHaveText(shownBefore, {timeout: 10_000});
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('a detail row of a text voice opens its history: the window, no chart, its rows (E6b)', async ({page}) => {
        test.setTimeout(60_000);
        const name = `E2E profile history text ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {index_name: 'FTSE All-World'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            await expect(page.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready', {timeout: 15_000});

            await page.getByTestId('profile-detail-index_name-history').click();
            const history = page.getByTestId('profile-history');
            await expect(history).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
            await expect(history).toHaveAttribute('data-voice', 'index_name');
            await expect(page.getByTestId('profile-history-chart'), 'a text has no chart').toHaveCount(0);
            await expect(history.locator('[data-testid^="profile-change-what-"]')).toHaveCount(1);
            // The identifiers (ISIN, ticker) are no voices of the profile: their rows open no history
            await expect(page.getByTestId('profile-detail-isin')).toBeVisible();
            await expect(page.getByTestId('profile-detail-isin-history')).toHaveCount(0);
            await expect(page.getByTestId('profile-detail-ticker-history')).toHaveCount(0);
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });

    test('the clocks beside the countries and «Descrizione» open their history: the window with only the table (E6b2)', async ({page}) => {
        test.setTimeout(60_000);
        const name = `E2E profile history map ${uniqueToken(8)}`;
        const created = await page.request.post(`${API_BASE}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'ETF', profile: {geography: {USA: '0.6', JPN: '0.4'}, description: 'A fund of the test.'}}]});
        expect(created.status(), `POST ${API_BASE}/assets: ${await created.text()}`).toBe(201);
        const assetId = ((await created.json()) as {results: Array<{asset_id: number}>}).results[0].asset_id;
        try {
            await goToAssetDetailPage(page, String(assetId));
            await page.getByTestId('asset-detail-tab-profile').click();
            await expect(page.getByTestId('asset-profile-tab')).toHaveAttribute('data-status', 'ready', {timeout: 15_000});
            // No sectors written: no clock beside them
            await expect(page.getByTestId('profile-classification-sector-history')).toHaveCount(0);

            const history = page.getByTestId('profile-history');
            for (const [clock, voice] of [
                ['profile-classification-geography-history', 'geography'],
                ['asset-profile-description-history', 'description'],
            ] as const) {
                await page.getByTestId(clock).click();
                await expect(history).toHaveAttribute('data-status', 'ready', {timeout: 10_000});
                await expect(history).toHaveAttribute('data-voice', voice);
                await expect(page.getByTestId('profile-history-chart'), 'a map or a text has no chart').toHaveCount(0);
                await expect(history.locator('[data-testid^="profile-change-what-"]')).toHaveCount(1);
                if (voice === 'description') {
                    // Two columns wide enough to read (87 A3): the text is not squeezed into a strip
                    const columns = await history.evaluate((root) => ['before', 'after'].map((id) => root.querySelector(`[data-testid="dt-header-${id}"]`)?.getBoundingClientRect().width ?? 0));
                    expect(Math.min(...columns), `«Prima» and «Dopo» of a text: ${JSON.stringify(columns)}`).toBeGreaterThanOrEqual(280);
                }
                await page.getByTestId('profile-history-close').click();
                await expect(history).toHaveCount(0);
            }
        } finally {
            await page.request.delete(`${API_BASE}/assets?asset_ids=${assetId}`);
        }
    });
});
