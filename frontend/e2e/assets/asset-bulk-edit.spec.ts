/**
 * Asset bulk edit — E2E (lane 65, lot E1).
 *
 * The pencil of the selection toolbar opens «Modifica N asset»: fields → check → summary → one `PATCH /assets`, all or
 * nothing. What this spec proves against the real backend and a real browser, which the component tests cannot:
 * - a type and a benchmark flag chosen once are saved for every selected asset, the modal closes, the selection is
 *   cleared and the list holds the new values;
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
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';
import {API_BASE, goToAssetsPage} from './assets-helpers';
import {deleteOwned, jsonFrom, type Owned} from './asset-events-owned';

type StoredAsset = {id: number; display_name: string; asset_type: string | null; is_benchmark: boolean | null; active: boolean};

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

/** Narrow the list to this test's token, switch to the table, select every row and open the bulk edit. */
async function openBulkEdit(page: Page, token: string, count: number): Promise<void> {
    await goToAssetsPage(page);
    await page.getByTestId('assets-search-input').fill(token);
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    await page.getByTestId('view-mode-list').click();
    await waitForSettled(page.getByTestId('assets-page'), 20_000);
    // The list is split by usage (own, others, watched): the rows of this test sit in one or two of those tables, and
    // each table has its own select-all. Wait for all the rows, then select every table that holds some.
    await expect(page.locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(count);
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

            // The modal is gone, the selection is cleared and the list reloaded.
            await expect(page.getByTestId('asset-bulk-edit')).toHaveCount(0);
            await expect(page.getByTestId('selection-toolbar')).toHaveCount(0);
            await waitForSettled(page.getByTestId('assets-page'), 20_000);

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
