/**
 * tx-reward-form.spec.ts — a REWARD created through the transaction form (project 79, STK-2a)
 *
 * A REWARD brings units of an asset in, with no cash; its cost basis is its value on receipt, which is also its income,
 * and it is never the pool's average cost (rule 12c, `cost_basis_auto: false` in the type table). In the form:
 *
 *   - the value field (`tx-form-cost-basis-inline`) shows once the quantity is positive, without the Auto/Manual toggle
 *     (`tx-form-cost-basis-toggle` is not rendered at all for such a type);
 *   - an empty value is filled from the asset's stored close of the day, and the note
 *     `tx-form-reward-value-from-history` says so; with no stored price the field stays empty and the warning
 *     `tx-form-cost-basis-warning` shows until the user types a value;
 *   - Apply hands the row to the editor, the commit saves it, and the row is a REWARD carrying that value.
 *
 * Data. Every test works on an EUR asset of its own (an asset is a global row) with prices it stores itself, and on the
 * seeded broker TEST_USER owns. The transactions it commits are deleted by the tracker (ids from its own commit
 * responses), then the asset, its prices with it. The page is loaded after the asset exists: it keeps its assets in a
 * session cache.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {daysAgoIso} from '../fixtures/dates';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';

test.setTimeout(60_000);

const API = '/api/v1';
/** The seeded broker the REWARD lands on (TEST_USER is its OWNER). */
const BROKER_NAME = 'Interactive Brokers';

type OwnedAsset = {id: number; name: string};
type StoredTx = {id: number; type: string; asset_id: number | null; quantity: string | number; cash: unknown; cost_basis_override: {code: string; amount: string | number} | null};

// ---------------------------------------------------------------------------
// API helpers — every row these write belongs to this test
// ---------------------------------------------------------------------------

/** An EUR asset of this test's own. The id is recorded for cleanup before anything about the result is checked. */
async function createOwnedAsset(page: Page, ownedAssetIds: number[]): Promise<OwnedAsset> {
    const name = `E2E reward ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/assets`, {data: [{display_name: name, currency: 'EUR', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/** Store the closes of the owned asset, and check they read back with a currency: without one, no suggestion. */
async function storeCloses(page: Page, assetId: number, closes: Array<{date: string; close: string}>): Promise<void> {
    const stored = await page.request.post(`${API}/assets/prices`, {data: [{asset_id: assetId, prices: closes.map((c) => ({...c, currency: 'EUR'}))}]});
    expect(stored.ok(), `store the closes: HTTP ${stored.status()} ${await stored.text()}`).toBe(true);
    const dates = closes.map((c) => c.date).sort();
    const read = await page.request.post(`${API}/assets/prices/query`, {data: [{asset_id: assetId, date_range: {start: dates[0], end: dates.at(-1)}}]});
    expect(read.ok(), `read the closes back: HTTP ${read.status()}`).toBe(true);
    const body = (await read.json()) as {items?: Array<{asset_id: number; prices?: Array<{date: string; close: string | number | null; currency?: string | null}>}>};
    const prices = body.items?.find((item) => item.asset_id === assetId)?.prices ?? [];
    for (const {date, close} of closes) {
        const point = prices.find((p) => p.date === date);
        expect(point, `precondition: the close of ${date} is stored`).toBeTruthy();
        expect(Number(point!.close), `precondition: the close of ${date}`).toBe(Number(close));
        expect(point!.currency, `precondition: the close of ${date} carries the asset's currency`).toBe('EUR');
    }
}

/** Delete the assets this test created; their prices go with them. Transactions first: the tracker runs before this. */
async function deleteOwnedAssets(page: Page, ownedAssetIds: readonly number[]): Promise<void> {
    if (ownedAssetIds.length === 0) return;
    try {
        // Unmount the page first, so nothing on it queries the asset while it goes.
        await page.goto('about:blank');
    } finally {
        for (const id of ownedAssetIds) {
            const response = await page.request.delete(`${API}/assets?asset_ids=${id}`);
            expect(response.ok(), `delete the owned asset ${id}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
            const result = (await response.json()) as {results: Array<{asset_id: number; success: boolean; message?: string}>};
            const mine = result.results.find((item) => item.asset_id === id);
            expect(mine?.success, `owned asset ${id} is deleted: ${mine?.message ?? 'missing result'}`).toBe(true);
        }
    }
}

/** The id of the seeded broker named exactly `name` — read, never assumed. */
async function seededBrokerId(page: Page, name: string): Promise<number> {
    const response = await page.request.get(`${API}/brokers`);
    expect(response.ok(), `list the brokers: HTTP ${response.status()}`).toBe(true);
    const body = (await response.json()) as {items: Array<{id: number; name: string}>};
    const matches = body.items.filter((broker) => broker.name === name);
    if (matches.length !== 1) throw new Error(`Expected exactly one broker named "${name}" visible to this user, found ${matches.length} — check populate_mock_data.py`);
    return matches[0].id;
}

/** The transactions `ids`, read back from the backend. */
async function readTransactions(page: Page, ids: number[]): Promise<StoredTx[]> {
    const response = await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`);
    expect(response.ok(), `GET /transactions?ids=… answered ${response.status()}`).toBe(true);
    return (await response.json()) as StoredTx[];
}

// ---------------------------------------------------------------------------
// UI helpers — the form, then the editor's commit
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '') {
    await navigateTo(page, `/transactions${query}`);
    // The table being visible is not the table being loaded: the page publishes data-busy.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

async function selectType(page: Page, typeCode: string) {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, brokerName: string) {
    const brokerId = await seededBrokerId(page, brokerName);
    await page.getByTestId('tx-form-broker-wrap').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

/** Pick exactly the asset with this id: search its name, then click the option carrying its id. */
async function pickAsset(page: Page, asset: OwnedAsset) {
    await page.getByTestId('tx-form-asset-trigger').click();
    const searchInput = page.getByTestId('tx-form-asset-search');
    await expect(searchInput).toBeVisible({timeout: 3_000});
    await searchInput.fill(asset.name);
    await expect(searchInput).toHaveValue(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionsClosed(page);
}

/** Date the form, typed as a user types it; Enter commits it and puts the calendar away. */
async function setFormDate(page: Page, date: string) {
    const dateRoot = page.getByTestId('tx-form-date-wrap').getByTestId('single-date-picker-root');
    const dateInput = dateRoot.locator('input[type="text"]');
    await dateInput.click();
    await dateInput.fill(date);
    await dateInput.press('Enter');
    await expect(dateRoot).toHaveAttribute('data-open', 'false');
    await expect(dateRoot).toHaveAttribute('data-invalid', 'false');
    await expect(dateInput).toHaveValue(date);
}

async function fillQuantity(page: Page, qty: string) {
    const qtyInput = page.getByTestId('tx-form-quantity');
    await expect(qtyInput).toBeVisible({timeout: 2_000});
    await qtyInput.fill(qty);
    await qtyInput.blur();
    await expect(qtyInput).toHaveValue(qty);
}

/** The value field is there, usable, and has no Auto/Manual toggle (not rendered for a REWARD, so a count). */
async function expectValueFieldWithoutAuto(page: Page) {
    const inline = page.getByTestId('tx-form-cost-basis-inline');
    await expect(inline).toBeVisible({timeout: 5_000});
    await expect(page.getByTestId('tx-form-cost-basis-input-amount')).toBeVisible();
    await expect(inline.getByTestId('tx-form-cost-basis-toggle')).toHaveCount(0);
    await expect(page.getByTestId('tx-form-cost-basis-toggle-auto')).toHaveCount(0);
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 10_000});
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
}

/** Commit the open editor; returns the ids of the rows the commit created. */
async function commitBulkModal(page: Page): Promise<number[]> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const body = (await (await responsePromise).json()) as {committed?: boolean; results?: Array<{operation: string; ids?: number[]; status?: string}>; issues?: unknown};
    expect(body.committed, `the commit is accepted: ${JSON.stringify(body.issues ?? body)}`).toBe(true);
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});
    return (body.results ?? []).filter((r) => r.operation === 'create' && r.status === 'success').flatMap((r) => r.ids ?? []);
}

/** The one REWARD the commit created on the owned asset, as stored, and its row in the table. */
async function expectCommittedReward(page: Page, createdIds: number[], asset: OwnedAsset, quantity: string): Promise<StoredTx> {
    const rows = (await readTransactions(page, createdIds)).filter((row) => row.asset_id === asset.id);
    expect(rows, `the commit created one row on asset ${asset.id} (created ids: ${createdIds.join(', ')})`).toHaveLength(1);
    const reward = rows[0];
    expect(reward.type).toBe('REWARD');
    expect(Number(reward.quantity)).toBe(Number(quantity));
    expect(reward.cash == null || Number((reward.cash as {amount?: unknown}).amount ?? 0) === 0, 'a REWARD moves no cash').toBe(true);

    // The row on screen, found by its id: the type icon is the REWARD one (its slug, never its translated label).
    await goToTransactions(page, `?id_min=${reward.id}&id_max=${reward.id}`);
    const icon = page.getByTestId(`tx-type-icon-${reward.id}`);
    await expect(icon, 'the committed REWARD is listed').toBeVisible({timeout: 10_000});
    await expect(icon.locator('img')).toHaveAttribute('src', /reward/);
    return reward;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('REWARD through the transaction form (79 STK-2a)', () => {
    let txWrites: TransactionWriteTracker | undefined;
    let ownedAssetIds: number[] = [];

    test.beforeEach(async ({page}) => {
        ownedAssetIds = [];
        await login(page, TEST_USER);
        txWrites = await trackTransactionWrites(page);
    });

    test.afterEach(async ({page}) => {
        const tracker = txWrites;
        txWrites = undefined;
        try {
            await tracker?.cleanup();
        } finally {
            await deleteOwnedAssets(page, ownedAssetIds);
        }
    });

    test('the value is prefilled from the stored close of the day, the note shows, and the REWARD saves with it', async ({page}) => {
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const day = daysAgoIso(10);
        // An earlier close too: the suggestion is the day's own, not the last one stored before it.
        await storeCloses(page, asset.id, [
            {date: daysAgoIso(12), close: '40'},
            {date: day, close: '61.25'},
        ]);

        await goToTransactions(page);
        await openCreateFlow(page);
        await selectType(page, 'REWARD');
        await pickBroker(page, BROKER_NAME);
        await setFormDate(page, day);
        await pickAsset(page, asset);
        await fillQuantity(page, '3');

        await expectValueFieldWithoutAuto(page);
        const amount = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(amount, 'the close of the day, per unit').toHaveValue('61.25', {timeout: 10_000});
        await expect(page.getByTestId('tx-form-reward-value-from-history')).toBeVisible();
        await expect(page.getByTestId('tx-form-cost-basis-warning')).toHaveCount(0);

        await applyFormModal(page);
        const createdIds = await commitBulkModal(page);
        const reward = await expectCommittedReward(page, createdIds, asset, '3');
        expect(reward.cost_basis_override?.code).toBe('EUR');
        expect(Number(reward.cost_basis_override?.amount), 'the value on receipt is the suggested close').toBe(61.25);
    });

    test('with no stored price the field stays empty with the warning; the value the user types is saved', async ({page}) => {
        const asset = await createOwnedAsset(page, ownedAssetIds);

        await goToTransactions(page);
        await openCreateFlow(page);
        await selectType(page, 'REWARD');
        await pickBroker(page, BROKER_NAME);
        await pickAsset(page, asset);
        await fillQuantity(page, '5');

        await expectValueFieldWithoutAuto(page);
        const amount = page.getByTestId('tx-form-cost-basis-input-amount');
        await expect(page.getByTestId('tx-form-cost-basis-warning'), 'an empty value on receipt is flagged').toBeVisible();
        await expect(amount).toHaveValue('');

        await amount.fill('4.2');
        await amount.press('Tab');
        await expect(amount).toHaveValue('4.2');
        await expect(page.getByTestId('tx-form-cost-basis-warning')).toHaveCount(0);
        await expect(page.getByTestId('tx-form-reward-value-from-history'), 'a typed value is not from the price history').toHaveCount(0);

        await applyFormModal(page);
        const createdIds = await commitBulkModal(page);
        const reward = await expectCommittedReward(page, createdIds, asset, '5');
        expect(Number(reward.cost_basis_override?.amount), 'the value the user typed').toBe(4.2);
    });

    test('the suggested value follows the date; a changed one stays, and the link brings back the close of that day', async ({page}) => {
        const asset = await createOwnedAsset(page, ownedAssetIds);
        const first = daysAgoIso(12);
        const second = daysAgoIso(10);
        const noClose = daysAgoIso(8);
        await storeCloses(page, asset.id, [
            {date: first, close: '40'},
            {date: second, close: '61.25'},
        ]);

        await goToTransactions(page);
        await openCreateFlow(page);
        await selectType(page, 'REWARD');
        await pickBroker(page, BROKER_NAME);
        await setFormDate(page, first);
        await pickAsset(page, asset);
        await fillQuantity(page, '3');

        const amount = page.getByTestId('tx-form-cost-basis-input-amount');
        const note = page.getByTestId('tx-form-reward-value-from-history');
        const useClose = page.getByTestId('tx-form-reward-use-close');
        await expect(amount).toHaveValue('40', {timeout: 10_000});
        await expect(note).toHaveAttribute('data-date', first);
        await expect(useClose).toHaveCount(0);

        // Untouched, it follows the day; a day without a close leaves the field empty.
        await setFormDate(page, second);
        await expect(amount).toHaveValue('61.25', {timeout: 10_000});
        await expect(note).toHaveAttribute('data-date', second);
        await setFormDate(page, noClose);
        await expect(amount).toHaveValue('');
        await expect(page.getByTestId('tx-form-cost-basis-warning')).toBeVisible();
        await expect(useClose, 'no close that day, nothing to bring back').toHaveCount(0);

        // Changed, it stays; the link names the day and restores its close.
        await setFormDate(page, second);
        await expect(amount).toHaveValue('61.25', {timeout: 10_000});
        await amount.fill('70');
        await amount.press('Tab');
        await expect(useClose).toHaveAttribute('data-date', second);
        await setFormDate(page, first);
        await expect(useClose).toHaveAttribute('data-date', first, {timeout: 10_000});
        await expect(amount).toHaveValue('70');
        await useClose.click();
        await expect(amount).toHaveValue('40');
        await expect(note).toHaveAttribute('data-date', first);
        await expect(useClose).toHaveCount(0);
    });
});
