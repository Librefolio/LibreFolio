/**
 * Asset bulk edit — E2E (lane 65, lot E1).
 *
 * The pencil of the selection toolbar opens «Modifica N asset»: fields → check → summary → one `PATCH /assets`, all or
 * nothing. What this spec proves against the real backend and a real browser, which the component tests cannot:
 * - a type and a benchmark flag chosen once are saved for every selected asset; the modal stays open with the «Saved»
 *   check, the selection stays and the list holds the new values;
 * - «Index» on an asset with transactions is a block: the check names it, «Save» stays off, and nothing is saved — not
 *   even for the other, free asset — until the blocked one is taken out of the edit; then the rest saves;
 * - at 375 px neither the fields nor the summary scroll sideways, and the summary is the card list, not the table;
 * - closing without saving changes nothing and keeps the selection.
 *
 * Data. Every test creates its own assets (and the one broker with a BUY that gives an asset transactions) under a
 * token only it writes, narrows the list to that token, and deletes what it created afterwards. Nothing reads or
 * writes the shared mock data. Selectors are `data-testid` only; the success is read from the `asset.bulk.saved` event
 * (`notify`), never from the toast's text.
 */
import {expect, test} from '../fixtures/playwright';
import type {Page} from '../fixtures/playwright';
import {login, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';
import {API_BASE, goToAssetsPage} from './assets-helpers';
import {deleteOwned, jsonFrom, type Owned} from './asset-events-owned';

type StoredAsset = {id: number; display_name: string; asset_type: string | null; is_benchmark: boolean | null; active: boolean; icon_url?: string | null; user_url?: string | null};

/** Three EUR stocks named after `token` (A, B, C); their ids are recorded for the cleanup first. */
async function createAssets(page: Page, owned: Owned, token: string, letters: string[]): Promise<Array<{id: number; name: string}>> {
    const names = letters.map((letter) => `E2E Bulk ${token} ${letter}`);
    const body = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>}>(
        await page.request.post(`${API_BASE}/assets`, {data: names.map((display_name) => ({display_name, currency: 'EUR', asset_type: 'STOCK'}))}),
        'create the owned assets',
    );
    for (const item of body.results) if (typeof item.asset_id === 'number') owned.assetIds.push(item.asset_id);
    return names.map((name) => {
        const created = body.results.find((item) => item.display_name === name);
        if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
        return {id: created.asset_id, name};
    });
}

/** A BUY on a broker of this test's own: what gives `assetId` transactions. The broker is recorded for the cleanup first. */
async function giveTransactions(page: Page, owned: Owned, assetId: number): Promise<void> {
    const brokerName = `E2E Bulk broker ${uniqueSuffix()}`;
    const brokers = await jsonFrom<{results: Array<{broker_id?: number; name: string; success: boolean}>}>(await page.request.post(`${API_BASE}/brokers`, {data: [{name: brokerName, allow_cash_overdraft: true}]}), 'create the owned broker');
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`The owned broker was not created: ${JSON.stringify(brokers)}`);
    const committed = await jsonFrom<{committed: boolean}>(
        await page.request.post(`${API_BASE}/transactions/commit`, {
            data: {creates: [{broker_id: broker.broker_id, asset_id: assetId, type: 'BUY', date: daysAgoIso(5), quantity: '10', cash: {code: 'EUR', amount: '-100'}}]},
        }),
        'commit the BUY',
    );
    expect(committed.committed, JSON.stringify(committed)).toBe(true);
}

/** The stored state of owned assets, read from the API (never from the page). */
async function storedAssets(page: Page, ids: number[]): Promise<StoredAsset[]> {
    const rows = await jsonFrom<StoredAsset[]>(await page.request.get(`${API_BASE}/assets/query`), 'list the assets');
    return ids.map((id) => {
        const row = rows.find((candidate) => candidate.id === id);
        if (!row) throw new Error(`Asset ${id} is not in /assets/query`);
        return row;
    });
}

/**
 * Narrow the list to this test's token, switch to the table, and wait until it lists exactly the `count` rows this test
 * created. The search is debounced (300 ms) and `data-busy` does not cover it, so the settles can return before the
 * filter lands; when it lands the table re-renders and closes any open row or column menu. The row count is the proof
 * that it has landed: the token is unique, so every row left is one this test owns.
 */
async function openList(page: Page, token: string, count: number): Promise<void> {
    await goToAssetsPage(page);
    await page.getByTestId('assets-search-input').fill(token);
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    await page.getByTestId('view-mode-list').click();
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    await expect(page.locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(count, {timeout: 10_000});
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
}

/** The fixed panel's four actions sit inside the screen and inside the panel's card, at this width. */
async function expectActionsInside(page: Page, width: number): Promise<void> {
    const bar = page.getByTestId('selection-toolbar');
    await expect(bar.getByTestId('toolbar-action-sync')).toBeVisible();
    const card = await bar.boundingBox();
    if (!card) throw new Error('The panel must be on screen to be measured.');
    for (const id of ['edit', 'sync', 'refresh', 'delete']) {
        const box = await bar.getByTestId(`toolbar-action-${id}`).boundingBox();
        expect(box, `«${id}» is drawn (${width} px)`).not.toBeNull();
        expect(box!.x, `«${id}» inside the screen on the left (${width} px)`).toBeGreaterThanOrEqual(0);
        expect(box!.x + box!.width, `«${id}» inside the screen on the right (${width} px)`).toBeLessThanOrEqual(width);
        expect(box!.x + box!.width, `«${id}» inside the panel (${width} px)`).toBeLessThanOrEqual(card.x + card.width + 0.5);
        const dot = await bar.getByTestId(`toolbar-action-${id}-count`).boundingBox();
        expect(dot, `the number of «${id}» is drawn (${width} px)`).not.toBeNull();
        expect(dot!.x + dot!.width, `the number of «${id}» inside the screen (${width} px)`).toBeLessThanOrEqual(width);
        expect(dot!.x + dot!.width, `the number of «${id}» inside the panel (${width} px)`).toBeLessThanOrEqual(card.x + card.width + 0.5);
    }
}

/** Open the filtered table, select every row and open the bulk edit. */
async function openBulkEdit(page: Page, token: string, count: number): Promise<void> {
    await openList(page, token, count);
    // The list is split by usage (own, others, watched): the rows of this test sit in one or two of those tables, and
    // each table has its own select-all. Select every table that holds some.
    for (const panel of ['own', 'others', 'analysis']) {
        const table = page.getByTestId(`assets-table-panel-${panel}`);
        if ((await table.locator('[data-testid^="dt-row-checkbox-"]').count()) > 0) await table.getByTestId('dt-select-all').click();
    }
    await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(count));
    await page.getByTestId('toolbar-action-edit').click();
    await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-selected', String(count));
    await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-step', 'fields');
}

async function chooseType(page: Page, type: string): Promise<void> {
    await page.getByTestId('asset-bulk-type-button').click();
    await page.getByTestId(`asset-type-tree-option-${type}`).click();
    await expect(page.getByTestId('asset-bulk-field-asset_type')).toHaveAttribute('data-modified', 'true');
}

/** «Continue to summary» and wait for the step: the check runs by itself on the way. */
async function toSummary(page: Page): Promise<void> {
    await page.getByTestId('asset-bulk-continue').click();
    await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-step', 'summary', {timeout: 15_000});
}

test.describe('Asset bulk edit', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test('a type and a benchmark flag chosen once are saved for all three assets', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C']);
            const ids = assets.map((asset) => asset.id);
            await openBulkEdit(page, token, 3);

            await chooseType(page, 'BOND');
            await page.getByTestId('asset-bulk-is_benchmark-yes').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-modified', '2');
            await toSummary(page);

            // One row per asset, each with its type and benchmark cells changing.
            await expect(page.getByTestId('asset-bulk-summary')).toHaveAttribute('data-changing', '3');
            for (const id of ids) await expect(page.locator(`[data-testid="asset-bulk-summary-row"][data-asset-id="${id}"]`)).toHaveCount(1);
            await expect(page.getByTestId('asset-bulk-save')).toBeEnabled();

            const since = await eventSeq(page);
            await page.getByTestId('asset-bulk-save').click();
            const saved = await waitForEvent(page, 'asset.bulk.saved', {since, timeout: 20_000});
            expect(saved.detail?.count).toBe(3);
            expect(saved.detail?.fields).toEqual(['asset_type', 'is_benchmark']);

            // U1: the modal stays open on the summary with the «Saved» check, the rows stay selected and the list reloaded.
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-saved', 'true');
            await expect(page.getByTestId('asset-bulk-saved')).toBeVisible();
            await expect(page.getByTestId('asset-bulk-save')).toBeDisabled();
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            await expect(page.getByTestId('asset-bulk-summary')).toHaveAttribute('data-changing', '3');
            await page.getByTestId('asset-bulk-cancel').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '3');

            for (const row of await storedAssets(page, ids)) {
                expect(row.asset_type, `type of ${row.display_name}`).toBe('BOND');
                expect(row.is_benchmark, `benchmark of ${row.display_name}`).toBe(true);
                expect(row.active, `active of ${row.display_name} is not touched`).toBe(true);
            }
        } finally {
            await deleteOwned(page, owned);
        }
    });

    test('«Index» on an asset with transactions is a block: nothing is saved until it is taken out of the edit', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const [withTx, free] = await createAssets(page, owned, token, ['A', 'B']);
            await giveTransactions(page, owned, withTx.id);
            await openBulkEdit(page, token, 2);

            await chooseType(page, 'INDEX');
            await page.getByTestId('asset-bulk-verify').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-verify', 'done', {timeout: 15_000});

            // The block names the asset with transactions and only that one; the field carries the chip.
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-blocked', '1');
            const rows = page.getByTestId('asset-bulk-block-indexWithTransactions-rows').getByRole('listitem');
            await expect(rows).toHaveCount(1);
            await expect(rows.first()).toHaveAttribute('data-asset-id', String(withTx.id));
            await expect(page.getByTestId('asset-bulk-asset_type-blocked')).toBeVisible();
            // The free asset changes family (STOCK → INDEX): a warning, never a block.
            await expect(page.getByTestId('asset-bulk-warning-assetFamilyChange-rows').getByRole('listitem')).toHaveCount(1);

            // «Continue» moves on with the block standing, and «Save» is off.
            await toSummary(page);
            await expect(page.getByTestId('asset-bulk-save')).toBeDisabled();
            await expect(page.locator(`[data-testid="asset-bulk-summary-row"][data-asset-id="${withTx.id}"]`)).toHaveAttribute('data-state', 'blocked');

            // Nothing was saved, not even the free asset.
            for (const row of await storedAssets(page, [withTx.id, free.id])) expect(row.asset_type, `type of ${row.display_name}`).toBe('STOCK');

            // Taking the blocked asset out re-checks the rest by itself and turns «Save» on.
            await page.getByTestId('asset-bulk-block-indexWithTransactions-remove').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-verify', 'done', {timeout: 15_000});
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-blocked', '0');
            await expect(page.getByTestId('asset-bulk-save')).toBeEnabled();
            await expect(page.getByTestId('asset-bulk-summary')).toHaveAttribute('data-changing', '1');
            // «Back» shows the fields again, where the removed asset stays among the chips, marked as removed, and
            // «Continue» checks once more and returns to the summary.
            await page.getByTestId('asset-bulk-back').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-step', 'fields');
            await expect(page.locator(`[data-testid="asset-bulk-selected-chip"][data-asset-id="${withTx.id}"]`)).toHaveAttribute('data-removed', 'true');
            await expect(page.locator(`[data-testid="asset-bulk-selected-chip"][data-asset-id="${free.id}"]`)).toHaveAttribute('data-removed', 'false');
            await toSummary(page);
            await expect(page.getByTestId('asset-bulk-save')).toBeEnabled();

            const since = await eventSeq(page);
            await page.getByTestId('asset-bulk-save').click();
            await waitForEvent(page, 'asset.bulk.saved', {since, timeout: 20_000});

            const [blockedAfter, freeAfter] = await storedAssets(page, [withTx.id, free.id]);
            expect(blockedAfter.asset_type, 'the asset with transactions stays what it was').toBe('STOCK');
            expect(freeAfter.asset_type, 'the free asset became an index').toBe('INDEX');
        } finally {
            await deleteOwned(page, owned);
        }
    });

    test('at 375 px neither the fields nor the summary scroll sideways, and the summary is the card list', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        await page.setViewportSize({width: 375, height: 812});
        /** How far something sticks out sideways: the page, and the modal's own box. */
        const overflow = () =>
            page.evaluate(() => {
                const modal = document.querySelector('[data-testid="asset-bulk-edit"]');
                return {
                    page: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth),
                    modal: modal ? Math.max(0, modal.scrollWidth - modal.clientWidth) : -1,
                };
            });
        try {
            await createAssets(page, owned, token, ['A', 'B', 'C']);
            await openBulkEdit(page, token, 3);

            expect(await overflow(), 'the fields step fits 375 px').toEqual({page: 0, modal: 0});

            await chooseType(page, 'BOND');
            await page.getByTestId('asset-bulk-is_benchmark-yes').click();
            await toSummary(page);

            await expect(page.getByTestId('asset-bulk-summary-cards')).toBeVisible();
            await expect(page.getByTestId('asset-bulk-summary-table')).toBeHidden();
            await expect(page.getByTestId('asset-bulk-summary-card')).toHaveCount(3);
            expect(await overflow(), 'the summary step fits 375 px').toEqual({page: 0, modal: 0});
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // U9: rows selected in two tables (the asset with a position is «yours», the two without are «watched»); the modal is
    // opened and closed with nothing changed; the «n selected» chip must still clear every table.
    test('the «n selected» chip clears the selection of every table after the modal was opened and closed', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C']);
            await giveTransactions(page, owned, assets[2].id);
            await openBulkEdit(page, token, 3);
            await expect(page.getByTestId('assets-table-panel-own').locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(1);
            await expect(page.getByTestId('assets-table-panel-analysis').locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(2);

            await page.getByTestId('asset-bulk-cancel').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '3');

            await page.getByTestId('selection-toolbar-clear').click();
            await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
            await expect(page.locator('[data-testid^="dt-row-checkbox-"][data-state="checked"]')).toHaveCount(0);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // U3 + U4: «Type» sits under «User URL» on one column; «Now: …» is under the field it describes; the Undo of a field
    // is on the row of its control, not of its title. Geometry only: no text is read.
    test('the fields are on one grid: Type under User URL, «Now» under the control, Undo on the control row', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        await page.setViewportSize({width: 1280, height: 900});
        try {
            await createAssets(page, owned, token, ['A', 'B', 'C']);
            await openBulkEdit(page, token, 3);
            await page.getByTestId('asset-bulk-user-url').fill('https://example.test/bulk');
            await chooseType(page, 'BOND');
            await page.getByTestId('asset-bulk-active-no').click();
            await page.getByTestId('asset-bulk-icon-pick').scrollIntoViewIfNeeded();

            const box = async (testId: string) => {
                const found = await page.getByTestId(testId).boundingBox();
                if (!found) throw new Error(`${testId} has no box`);
                return found;
            };
            const url = await box('asset-bulk-user-url');
            const type = await box('asset-bulk-type-button');
            expect(type.y, 'Type is under User URL').toBeGreaterThanOrEqual(url.y + url.height);
            expect(Math.abs(type.x - url.x), 'Type and User URL share the left edge').toBeLessThanOrEqual(1);
            expect(Math.abs(type.width - url.width), 'Type and User URL share the width').toBeLessThanOrEqual(1);

            const controls: Array<[string, string]> = [
                ['user_url', 'asset-bulk-user-url'],
                ['asset_type', 'asset-bulk-type-button'],
                ['active', 'asset-bulk-active'],
            ];
            for (const [field, controlId] of controls) {
                const control = await box(controlId);
                const undo = await box(`asset-bulk-reset-${field}`);
                const undoCentre = undo.y + undo.height / 2;
                expect(undoCentre, `the Undo of ${field} is on the row of its control`).toBeGreaterThanOrEqual(control.y);
                expect(undoCentre, `the Undo of ${field} is on the row of its control`).toBeLessThanOrEqual(control.y + control.height);
                const now = await box(`asset-bulk-${field}-now`);
                expect(now.y, `«Now» of ${field} is under its control`).toBeGreaterThanOrEqual(control.y + control.height - 1);
            }
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // 81 U45 (testlist 9.3): the first segment of Active and Benchmark said «Leave as is» and was cut («Lascia c…»). It says the
    // state in one short word now; read in the browser, in the four languages, on a phone and wide: no segment is cut.
    test('the segments of Active and Benchmark are not cut, in the four languages, at 390 px and wide', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            await createAssets(page, owned, token, ['A', 'B', 'C']);
            // Every cut is collected and said at the end: the report is the table the width is chosen from.
            const cuts: string[] = [];
            for (const language of ['en', 'it', 'fr', 'es'] as const) {
                await setLanguage(page, language);
                for (const width of [390, 1280]) {
                    await page.setViewportSize({width, height: 900});
                    await openBulkEdit(page, token, 3);
                    await page.getByTestId('asset-bulk-active').scrollIntoViewIfNeeded();
                    for (const field of ['active', 'is_benchmark']) {
                        for (const option of ['leave', 'yes', 'no']) {
                            const cut = await page.getByTestId(`asset-bulk-${field}-${option}`).evaluate((element) => Math.round(element.scrollWidth - element.clientWidth));
                            if (cut > 0) cuts.push(`${language}@${width} ${field}/${option}: ${cut}px`);
                        }
                    }
                    await page.keyboard.press('Escape');
                    await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
                }
            }
            expect(cuts, `segments cut by this many pixels: ${cuts.join(' · ')}`).toEqual([]);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // 81 U44 (testlist of 23/11, the developer's photo): the icon block — the label, the round «pick» button, «Remove icon» and its
    // «Now» line — is centred: on a wide window vertically against the two fields beside it (User URL and Type), on every width
    // on one vertical axis, which on a phone, where the block sits above the fields, is the middle of the window.
    test('the icon block is centred: against User URL and Type on a wide window, on one axis (the window’s middle on a phone)', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C']);
            const patched = await page.request.patch(`${API_BASE}/assets`, {
                data: [
                    {asset_id: assets[0].id, icon_url: 'https://example.test/a.png'},
                    {asset_id: assets[2].id, icon_url: 'https://example.test/c.png'},
                ],
            });
            expect(patched.ok(), 'give A and C an icon, so «Remove icon» is offered').toBe(true);
            await openBulkEdit(page, token, 3);
            await expect(page.getByTestId('asset-bulk-icon-remove'), 'premise: «Remove icon» is offered').toBeVisible();

            // One evaluate: the boxes are read in the same frame, whatever reflows between two awaited reads.
            const measure = () =>
                page.evaluate(() => {
                    const rect = (selector: string) => {
                        const element = document.querySelector<HTMLElement>(selector);
                        if (!element) throw new Error(`${selector} is not on the page`);
                        const box = element.getBoundingClientRect();
                        return {top: box.top, bottom: box.bottom, centreX: box.left + box.width / 2};
                    };
                    const label = rect('#asset-bulk-icon-label');
                    const pick = rect('[data-testid="asset-bulk-icon-pick"]');
                    const remove = rect('[data-testid="asset-bulk-icon-remove"]');
                    const now = rect('[data-testid="asset-bulk-icon_url-now"]');
                    const cell = rect('[data-testid="asset-bulk-field-icon_url"]');
                    const urlHead = rect('label[for="asset-bulk-user-url"]');
                    const typeNow = rect('[data-testid="asset-bulk-asset_type-now"]');
                    return {
                        axis: [label.centreX, pick.centreX, remove.centreX, now.centreX],
                        cellCentreX: cell.centreX,
                        blockCentreY: (label.top + now.bottom) / 2,
                        fieldsCentreY: (urlHead.top + typeNow.bottom) / 2,
                    };
                });

            await page.setViewportSize({width: 1280, height: 1000});
            await page.getByTestId('asset-bulk-icon-pick').scrollIntoViewIfNeeded();
            await expect
                .poll(
                    async () => {
                        const m = await measure();
                        return Math.abs(m.blockCentreY - m.fieldsCentreY);
                    },
                    {message: 'wide: the icon block is not centred against User URL and Type', timeout: 5_000},
                )
                .toBeLessThanOrEqual(3);
            await expect
                .poll(
                    async () => {
                        const {axis} = await measure();
                        return Math.max(...axis) - Math.min(...axis);
                    },
                    {message: 'wide: the label, the pick button, «Remove icon» and «Now» are not on one axis', timeout: 5_000},
                )
                .toBeLessThanOrEqual(2);

            await page.setViewportSize({width: 375, height: 812});
            await page.getByTestId('asset-bulk-icon-pick').scrollIntoViewIfNeeded();
            await expect
                .poll(
                    async () => {
                        const {axis, cellCentreX} = await measure();
                        return Math.max(...axis.map((x) => Math.abs(x - cellCentreX)));
                    },
                    {message: 'phone: the icon block is not centred in the window', timeout: 5_000},
                )
                .toBeLessThanOrEqual(2);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // U5: the body of the window has no scrollbar of its own while the window fits; below that, the body scrolls and the
    // header and the footer stay in view.
    test('the window grows with its content: no inner scrollbar when it fits, the body scrolls at 600 px with header and footer in view', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        // The fullest case (a block banner, a warning banner and five assets) is about 1120 px with its header and footer:
        // 90% of 1400 px holds it, so there the body must not need a scrollbar of its own.
        await page.setViewportSize({width: 1280, height: 1400});
        const bodyScroll = () => page.getByTestId('asset-bulk-body').evaluate((el) => ({scroll: el.scrollHeight, client: el.clientHeight, overflowY: getComputedStyle(el).overflowY}));
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C', 'D', 'E']);
            await giveTransactions(page, owned, assets[0].id);
            await openBulkEdit(page, token, 5);
            await chooseType(page, 'INDEX');
            await page.getByTestId('asset-bulk-verify').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-verify', 'done', {timeout: 15_000});
            await expect(page.getByTestId('asset-bulk-block-indexWithTransactions')).toBeVisible();
            await expect(page.getByTestId('asset-bulk-warning-assetFamilyChange')).toBeVisible();

            const roomy = await bodyScroll();
            expect(roomy.scroll, 'the body shows all its content, no scrollbar of its own').toBeLessThanOrEqual(roomy.client);

            await page.setViewportSize({width: 1280, height: 600});
            await expect.poll(async () => (await bodyScroll()).scroll > (await bodyScroll()).client, {timeout: 5_000}).toBe(true);
            // The scrollbar is hidden (the shared utility), the scroll is not: the body takes no width for a bar, and the keyboard and the
            // wheel still move it.
            const bar = await page.getByTestId('asset-bulk-body').evaluate((el: HTMLElement) => ({width: el.offsetWidth - el.clientWidth, scrollbarWidth: getComputedStyle(el).scrollbarWidth}));
            expect(bar.scrollbarWidth, 'the bar is hidden').toBe('none');
            expect(bar.width, 'no gutter for a bar').toBe(0);
            await page.getByTestId('asset-bulk-body').focus();
            await page.keyboard.press('PageDown');
            await expect.poll(() => page.getByTestId('asset-bulk-body').evaluate((el) => el.scrollTop), {message: 'PageDown scrolls the body', timeout: 5_000}).toBeGreaterThan(0);
            const afterKey = await page.getByTestId('asset-bulk-body').evaluate((el) => el.scrollTop);
            await page.getByTestId('asset-bulk-body').hover();
            await page.mouse.wheel(0, 200);
            await expect.poll(() => page.getByTestId('asset-bulk-body').evaluate((el) => el.scrollTop), {message: 'the wheel scrolls the body', timeout: 5_000}).toBeGreaterThan(afterKey);
            const viewport = page.viewportSize()!;
            for (const part of ['asset-bulk-title', 'asset-bulk-footer-fields']) {
                const found = await page.getByTestId(part).boundingBox();
                expect(found, `${part} is drawn`).not.toBeNull();
                expect(found!.y, `${part} is inside the viewport`).toBeGreaterThanOrEqual(0);
                expect(found!.y + found!.height, `${part} is inside the viewport`).toBeLessThanOrEqual(viewport.height);
            }
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // U7: «Remove icon» and «Remove URL» take the value away from the assets that hold it, in one save; an asset that holds
    // neither has nothing to remove and is not touched.
    test('«Remove icon» and «Remove URL» clear them for the assets that hold them', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C']);
            const [a, , c] = assets;
            const patched = await page.request.patch(`${API_BASE}/assets`, {
                data: [
                    {asset_id: a.id, icon_url: 'https://example.test/a.png', user_url: 'https://example.test/a'},
                    {asset_id: c.id, icon_url: 'https://example.test/c.png'},
                ],
            });
            expect(patched.ok(), 'give A an icon and a URL, C an icon').toBe(true);
            await openBulkEdit(page, token, 3);

            await page.getByTestId('asset-bulk-icon-remove').click();
            await page.getByTestId('asset-bulk-user-url-remove').click();
            await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-modified', '2');
            await toSummary(page);
            await expect(page.getByTestId('asset-bulk-summary')).toHaveAttribute('data-changing', '2');
            await expect(page.locator(`[data-testid="asset-bulk-summary-row"][data-asset-id="${assets[1].id}"]`)).toHaveCount(0);

            const since = await eventSeq(page);
            await page.getByTestId('asset-bulk-save').click();
            await waitForEvent(page, 'asset.bulk.saved', {since, timeout: 20_000});

            const [after, untouched, afterC] = await storedAssets(
                page,
                assets.map((asset) => asset.id),
            );
            expect(after.icon_url ?? null, 'A lost its icon').toBeNull();
            expect(after.user_url ?? null, 'A lost its URL').toBeNull();
            expect(afterC.icon_url ?? null, 'C lost its icon').toBeNull();
            expect(untouched.icon_url ?? null, 'B had none and still has none').toBeNull();
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // U10: the table row has its own «Edit»: the editor of the asset opens in place (complete, as in the detail page) and a
    // rename shows in the list, without ever leaving it.
    test('the row action «Edit» opens the asset editor in the list and a rename shows in the table', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const [asset] = await createAssets(page, owned, token, ['A']);
            await openList(page, token, 1);

            await page.getByTestId(`row-actions-${asset.id}`).click();
            await page.getByTestId('asset-table-edit-action').click();
            await expect(page.getByTestId('asset-modal-form')).toBeVisible({timeout: 10_000});
            const nameInput = page.getByTestId('asset-modal-display-name');
            await expect(nameInput).toHaveValue(asset.name, {timeout: 5_000});
            await expect(page, 'the list page stays: no detail page').toHaveURL(/\/assets(\?|$)/);

            const renamed = `${asset.name} renamed`;
            await nameInput.fill(renamed);
            await page.getByTestId('asset-modal-save').click();
            await expect(page.getByTestId('asset-modal-form')).toHaveCount(0, {timeout: 15_000});
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

            const stored = await storedAssets(page, [asset.id]);
            expect(stored[0].display_name).toBe(renamed);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // 77 SEL-B: the page's fixed panel follows the rule of every table. «Sync» takes the assets with a provider only — the
    // assets made here have none, so it is not there (Q-SEL-17); the others say how many assets they act on; «Reload» asks the
    // prices of the selected assets only (Q-SEL-10), never the whole list.
    test('the fixed panel counts each action’s assets, hides Sync without a provider, and Reload asks the selected assets only', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B']);
            await openList(page, token, 2);
            for (const asset of assets) await page.getByTestId(`dt-row-checkbox-${asset.id}`).click();
            const bar = page.getByTestId('selection-toolbar');
            await expect(bar).toHaveAttribute('data-selected-count', '2');
            await expect(bar).toHaveAttribute('data-variant', 'floating');
            await expect(page.getByTestId('toolbar-action-edit-count')).toHaveText('2');
            await expect(page.getByTestId('toolbar-action-refresh-count')).toHaveText('2');
            await expect(page.getByTestId('toolbar-action-delete-count')).toHaveText('2');
            await expect(page.getByTestId('toolbar-action-sync')).toHaveCount(0);

            const asked: number[] = [];
            page.on('request', (request) => {
                if (request.method() !== 'POST' || new URL(request.url()).pathname !== '/api/v1/assets/prices/query') return;
                for (const item of (request.postDataJSON() as Array<{asset_id: number; include_price: boolean}>) ?? []) if (item.include_price) asked.push(item.asset_id);
            });
            await page.getByTestId('toolbar-action-refresh').click();
            await expect.poll(() => asked.length, {message: 'Reload asks prices again', timeout: 15_000}).toBeGreaterThan(0);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            const ids = assets.map((asset) => asset.id);
            expect(
                asked.every((id) => ids.includes(id)),
                `only the selected assets are asked again, asked ${JSON.stringify(asked)}`,
            ).toBe(true);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    // 77 SEL-B: on a phone the fixed panel, with all four actions and their numbers, stays inside the screen. The assets made
    // here get a provider in the list's answer (only theirs), so «Sync» is there too: the widest panel the page draws.
    test('on a phone the fixed panel holds all four actions, with their numbers, inside the screen', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        const width = 375;
        await page.setViewportSize({width, height: 812});
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B']);
            const ids = assets.map((asset) => asset.id);
            await page.route('**/api/v1/assets/query*', async (route) => {
                const response = await route.fetch();
                const rows = (await response.json()) as Array<{id: number; provider_code?: string | null}>;
                await route.fulfill({response, json: rows.map((row) => (ids.includes(row.id) ? {...row, provider_code: 'mockprov'} : row))});
            });
            await openList(page, token, 2);
            for (const asset of assets) await page.getByTestId(`dt-row-checkbox-${asset.id}`).click();
            const bar = page.getByTestId('selection-toolbar');
            await expect(bar).toHaveAttribute('data-variant', 'floating');
            for (const id of ['edit', 'sync', 'refresh', 'delete']) {
                const action = bar.getByTestId(`toolbar-action-${id}`);
                await expect(bar.getByTestId(`toolbar-action-${id}-count`)).toHaveText('2');
                const box = await action.boundingBox();
                expect(box, `«${id}» is drawn`).not.toBeNull();
                expect(box!.x, `«${id}» inside the screen on the left`).toBeGreaterThanOrEqual(0);
                expect(box!.x + box!.width, `«${id}» inside the screen on the right`).toBeLessThanOrEqual(width);
            }
        } finally {
            await page.unroute('**/api/v1/assets/query*');
            await deleteOwned(page, owned);
        }
    });

    // 77 SEL-B (Q-SEL-7): a table of the list that pages keeps its pager above the fixed panel, on a wide screen and on a
    // phone; and the panel's four actions fit a phone with two-digit numbers (a page of 25) and with three (all 125 rows
    // shown and selected) on a 320 px screen, where the number is a dot on the icon's corner and the button's name says it
    // (the designer, 20/11). The test makes 125 assets and gives them a provider in the list's answer, so «Sync» is there.
    test('a table that pages keeps its pager above the fixed panel, and the numbers fit a phone, up to three digits at 320 px', async ({page}) => {
        // 125 assets are created in one call but deleted one by one in the cleanup: room for a busy machine, so a timeout
        // never stops halfway and leaves them in the shared database. While it runs, the list holds 125 more rows.
        test.setTimeout(90_000);
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const letters = Array.from({length: 125}, (_, i) => `P${String(i + 1).padStart(3, '0')}`);
            const assets = await createAssets(page, owned, token, letters);
            const ids = assets.map((asset) => asset.id);
            await page.route('**/api/v1/assets/query*', async (route) => {
                const response = await route.fetch();
                const rows = (await response.json()) as Array<{id: number; provider_code?: string | null}>;
                await route.fulfill({response, json: rows.map((row) => (ids.includes(row.id) ? {...row, provider_code: 'mockprov'} : row))});
            });
            await goToAssetsPage(page);
            await page.getByTestId('assets-search-input').fill(token);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            await page.getByTestId('view-mode-list').click();
            await waitForSettled(page.getByTestId('assets-page'), 20_000);
            // The token is unique: the one table holding rows is this test's, and it pages.
            const table = page.locator('[data-testid^="assets-table-panel-"]').filter({has: page.locator('[data-testid^="dt-row-checkbox-"]')});
            await expect(table).toHaveCount(1, {timeout: 10_000});
            await expect(table.locator('[data-testid^="dt-row-checkbox-"]:not([data-testid="dt-row-checkbox-all"])')).toHaveCount(25, {timeout: 10_000});
            const pager = table.getByTestId('data-table-pagination');
            await expect(pager).toBeVisible();
            await table.getByTestId('dt-select-all').click();
            const bar = page.getByTestId('selection-toolbar');
            await expect(bar).toHaveAttribute('data-variant', 'floating');
            expect(Number(await bar.getAttribute('data-selected-count')), 'two-digit numbers').toBeGreaterThanOrEqual(10);

            for (const [width, height] of [
                [1280, 800],
                [375, 812],
            ] as const) {
                await page.setViewportSize({width, height});
                // The table's top at the window's top: its 25 rows run on below the window, so the pager sticks to the
                // window's bottom, the one place where only its lift keeps it above the panel (at the end of the page it
                // sits in the flow, above the room the page keeps, and would pass without the lift).
                await table.evaluate((element) => element.scrollIntoView({block: 'start'}));
                await expect(bar.getByTestId('toolbar-action-sync')).toBeVisible();
                const barBox = await bar.boundingBox();
                const pagerBox = await pager.boundingBox();
                if (!barBox || !pagerBox) throw new Error('The panel and the pager must be on screen to be measured.');
                expect(pagerBox.y + pagerBox.height, `the pager is stuck inside the window (${width} px)`).toBeLessThanOrEqual(height);
                expect(pagerBox.y + pagerBox.height, `the pager is stuck near the window's bottom (${width} px)`).toBeGreaterThan(height - 200);
                expect(pagerBox.y + pagerBox.height, `the pager ends above the panel (${width} px)`).toBeLessThanOrEqual(barBox.y + 1);
                await expectActionsInside(page, width);
            }

            // Every row shown and selected: three digits, on the narrowest phone.
            await page.setViewportSize({width: 1280, height: 800});
            await table.getByTestId('pagination-size-trigger').click();
            await table.getByTestId('pagination-size-option-0').click();
            await expect(table.locator('[data-testid^="dt-row-checkbox-"]:not([data-testid="dt-row-checkbox-all"])')).toHaveCount(125, {timeout: 10_000});
            await table.getByTestId('dt-select-all').click();
            await expect(bar).toHaveAttribute('data-selected-count', '125');
            await expect(bar.getByTestId('toolbar-action-delete-count')).toHaveText('125');
            await expect(bar.getByTestId('toolbar-action-delete')).toHaveAttribute('aria-label', /, 125$/);
            await page.setViewportSize({width: 320, height: 700});
            await expectActionsInside(page, 320);
        } finally {
            await page.unroute('**/api/v1/assets/query*');
            await deleteOwned(page, owned);
        }
    });

    // U8: the selection bar floats at the bottom of the content, only while rows are selected, and stays after the save.
    for (const [width, height] of [
        [1280, 800],
        [375, 812],
    ] as const) {
        test(`the selection bar floats at the bottom (${width} px): only with a selection, and it stays after the save`, async ({page}) => {
            const owned: Owned = {assetIds: [], brokerIds: []};
            const token = uniqueToken(6);
            await page.setViewportSize({width, height});
            const bar = page.getByTestId('selection-toolbar');
            const reserved = () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--lf-selbar-space').trim());
            try {
                const assets = await createAssets(page, owned, token, ['A', 'B']);
                await openList(page, token, 2);

                // No selection, no bar, no room kept at the bottom.
                await expect(bar).toHaveCount(0);
                expect(await reserved()).toBe('');

                for (const asset of assets) await page.getByTestId(`dt-row-checkbox-${asset.id}`).click();
                await expect(bar).toHaveAttribute('data-selected-count', '2');
                await expect(bar).toHaveAttribute('data-variant', 'floating');
                const box = await bar.boundingBox();
                expect(box, 'the bar is drawn').not.toBeNull();
                expect(box!.x, 'inside the viewport on the left').toBeGreaterThanOrEqual(0);
                expect(box!.x + box!.width, 'inside the viewport on the right').toBeLessThanOrEqual(width);
                expect(box!.y + box!.height, 'at the bottom of the viewport').toBeLessThanOrEqual(height);
                expect(box!.y + box!.height, 'close to the bottom of the viewport').toBeGreaterThanOrEqual(height - 48);
                expect(await reserved(), 'the page keeps room for the bar').not.toBe('');
                // The words show on a wide screen only; the icon button is always there.
                if (width >= 1024) await expect(page.getByTestId('toolbar-action-edit-label')).toBeVisible();
                else await expect(page.getByTestId('toolbar-action-edit-label')).toBeHidden();

                // Open the bulk edit, save, close: the bar is still there with the same rows.
                await page.getByTestId('toolbar-action-edit').click();
                await expect(page.getByTestId('asset-bulk-edit')).toHaveAttribute('data-selected', '2');
                await page.getByTestId('asset-bulk-is_benchmark-yes').click();
                await toSummary(page);
                const since = await eventSeq(page);
                await page.getByTestId('asset-bulk-save').click();
                await waitForEvent(page, 'asset.bulk.saved', {since, timeout: 20_000});
                await page.getByTestId('asset-bulk-cancel').click();
                await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
                await expect(bar).toHaveAttribute('data-selected-count', '2');

                // Esc inside the bar deselects.
                await page.getByTestId('toolbar-action-edit').focus();
                await page.keyboard.press('Escape');
                await expect(bar).toHaveCount(0);
                expect(await reserved()).toBe('');
            } finally {
                await deleteOwned(page, owned);
            }
        });
    }

    // The page holds its three tables through refs (column menu, width mirror): with rows in two tables the column menu must act on
    // both. A check made after the finding of U9, where those refs were empty.
    test('the column menu acts on every table of the list', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B', 'C']);
            await giveTransactions(page, owned, assets[2].id);
            await openList(page, token, 3);
            const own = page.getByTestId('assets-table-panel-own');
            const watched = page.getByTestId('assets-table-panel-analysis');
            await expect(own.getByTestId('dt-header-lastPrice')).toHaveCount(1);
            await expect(watched.getByTestId('dt-header-lastPrice')).toHaveCount(1);

            await page.getByTestId('column-visibility-toggle').click();
            await page.getByTestId('column-visibility-item-lastPrice').click();
            await expect(own.getByTestId('dt-header-lastPrice'), 'hidden in the «yours» table').toHaveCount(0);
            await expect(watched.getByTestId('dt-header-lastPrice'), 'hidden in the «watched» table too').toHaveCount(0);
        } finally {
            await deleteOwned(page, owned);
        }
    });

    test('closing without saving changes nothing and keeps the selection', async ({page}) => {
        const owned: Owned = {assetIds: [], brokerIds: []};
        const token = uniqueToken(6);
        try {
            const assets = await createAssets(page, owned, token, ['A', 'B']);
            await openBulkEdit(page, token, 2);

            await page.getByTestId('asset-bulk-is_benchmark-yes').click();
            await toSummary(page);
            await page.getByTestId('asset-bulk-cancel').click();

            await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
            await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');
            for (const row of await storedAssets(
                page,
                assets.map((asset) => asset.id),
            ))
                expect(row.is_benchmark, `benchmark of ${row.display_name}`).toBe(false);
        } finally {
            await deleteOwned(page, owned);
        }
    });
});
