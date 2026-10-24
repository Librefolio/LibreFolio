/**
 * asset-currency-change.spec.ts — N68 (lot X5-3): changing an asset's currency is no longer blocked.
 *
 * Developer decision 19/10/2026. `PATCH /assets/patch` always succeeds on a currency change and, in the same call, deletes
 * the asset's prices and every event that is not a SPLIT, and disconnects (`asset_event_id` NULL) the transactions linked to
 * a deleted event; it KEEPS the SPLIT events and the transactions linked to them (a costless ADJUSTMENT stays linked to its
 * SPLIT, so the position math is unchanged). The asset modal therefore asks the server's dry run first
 * (`GET /assets/{id}/market-data/summary`) and, when something would be lost, opens the confirm modal
 * (`currency-change-modal`) BEFORE any write: its lines (`-summary-prices|events|linkedtx`) say what goes and a new one,
 * `currency-change-summary-splits`, says that splits stay. Cancel leaves everything as it was; confirm sends ONE PATCH.
 *
 * Contract (what the test below pins, end to end, through the API after each step):
 *   - save with a changed currency → the dry run is read (GET summary), the confirm modal shows with the splits line,
 *     and no PATCH has been sent;
 *   - cancel → no mutation at all; currency, prices, events and links are as seeded;
 *   - save again and confirm → exactly one PATCH; afterwards the currency is the new one, the prices are gone, the DIVIDEND
 *     event is gone and its transaction is unlinked (and still there), the SPLIT event and its ADJUSTMENT are still linked.
 *
 * Data. A disposable account (fixtures/owned-pair.ts) with a broker it owns, so no other spec sees these rows; a manual USD
 * asset of its own with two closes (`createOwnedAsset`); a funded BUY of 15, a SPLIT event with a costless ADJUSTMENT of 15 linked
 * to it, and a DIVIDEND event with its DIVIDEND transaction. `afterEach` deletes the broker (`force`), then the asset, then the
 * account.
 *
 * Key data-testids: asset-detail-edit-btn, asset-modal-form, asset-modal-currency-group, asset-modal-save,
 * currency-change-modal|-summary-prices|-summary-events|-summary-linkedtx|-summary-splits|-cancel|-confirm.
 *
 * Expected. Red before the cure: the save PATCHes at once (and the PATCH then refuses with the old token / 409), so the
 * dry run is never read and the modal does not open with the splits line.
 */
import {expect, test, type APIRequestContext, type Page} from '../fixtures/playwright';
import {daysAgoIso} from '../fixtures/dates';
import {optionsClosed} from '../fixtures/probe';
import {commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, cleanupOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {createOwnedAsset, deleteOwned, seedEvents, storedEvents, type Owned} from './asset-events-owned';
import {API_BASE, goToAssetDetailPage, openEditAssetModal} from './assets-helpers';

const UI_TIMEOUT = 10_000;
const NEW_CURRENCY = 'EUR';
const OLD_CURRENCY = 'USD';

// A disposable account goes through the real welcome hand-off before the page is even opened.
test.setTimeout(90_000);

type World = {
    assetId: number;
    brokerId: number;
    splitEvent: number;
    dividendEvent: number;
    buyTx: number;
    adjustmentTx: number;
    dividendTx: number;
};
type StoredTx = {id: number; asset_event_id: number | null};

let account: OwnedAccount;
let owned: Owned;

test.beforeEach(() => {
    account = emptyOwnedAccount();
    // The same array as the account's: a broker is recorded once, deleted once.
    owned = {assetIds: [], brokerIds: account.brokerIds};
});

test.afterEach(async ({page, request}) => {
    if (!account.user) return;
    // Brokers first (`force` takes their transactions), then the assets with their prices and events; the account last.
    await deleteOwned(page, owned);
    account.brokerIds.length = 0;
    await cleanupOwnedAccount(page, request, account);
});

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

async function seedWorld(page: Page, request: APIRequestContext): Promise<World> {
    await openOwnedAccount(page, request, account, 'ccy');
    const broker = await createOwnedBroker(page, 'ccy', account.brokerIds);
    const asset = await createOwnedAsset(page, owned, {label: 'E2E currency change'});

    const buyDay = daysAgoIso(25);
    const splitDay = daysAgoIso(20);
    const dividendDay = daysAgoIso(15);
    const [splitEvent, dividendEvent] = await seedEvents(page, asset.id, [
        {date: splitDay, type: 'SPLIT', amount: '2', notes: 'ccy-split'},
        {date: dividendDay, type: 'DIVIDEND', amount: '1', notes: 'ccy-dividend'},
    ]);
    const [, buyTx, adjustmentTx, dividendTx] = await commitCreates(
        page,
        [
            // The broker allows no overdraft: the BUY is funded first.
            {broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(26), cash: {code: OLD_CURRENCY, amount: '2000'}},
            {broker_id: broker.id, asset_id: asset.id, type: 'BUY', date: buyDay, quantity: '15', cash: {code: OLD_CURRENCY, amount: '-1500'}},
            // Costless: the cost basis is derived from the split, never typed.
            {broker_id: broker.id, asset_id: asset.id, type: 'ADJUSTMENT', date: splitDay, quantity: '15', asset_event_id: splitEvent, cost_basis_mode: 'auto'},
            {broker_id: broker.id, asset_id: asset.id, type: 'DIVIDEND', date: dividendDay, cash: {code: OLD_CURRENCY, amount: '15'}, asset_event_id: dividendEvent},
        ],
        'commit the funding, the BUY, the SPLIT adjustment and the DIVIDEND',
    );
    const world: World = {assetId: asset.id, brokerId: broker.id, splitEvent, dividendEvent, buyTx, adjustmentTx, dividendTx};

    // The premises, read back rather than inferred.
    expect(await currencyOf(page, world.assetId), 'premise: the asset starts in the old currency').toBe(OLD_CURRENCY);
    expect((await storedPrices(page, world.assetId)).length, 'premise: the asset has prices').toBeGreaterThan(0);
    expect((await storedEvents(page, world.assetId)).map((event) => event.id).sort(), 'premise: a SPLIT and a DIVIDEND').toEqual([splitEvent, dividendEvent].sort());
    expect(await links(page, world), 'premise: the two events are linked to their transactions').toEqual({adjustment: splitEvent, dividend: dividendEvent});
    return world;
}

async function currencyOf(page: Page, assetId: number): Promise<string> {
    const items = await jsonFrom<Array<{asset_id: number; currency: string}>>(await page.request.get(`${API_BASE}/assets?asset_ids=${assetId}`), 'read the asset');
    const item = items.find((candidate) => candidate.asset_id === assetId);
    if (!item) throw new Error(`Asset ${assetId} is missing from the metadata endpoint`);
    return item.currency;
}

async function storedPrices(page: Page, assetId: number) {
    const backup = await jsonFrom<{rows: Array<{date: string; close: string | number}>}>(await page.request.get(`${API_BASE}/backup/asset/${assetId}/prices?format=json`), 'read the stored prices');
    return backup.rows;
}

/** The event id each transaction of the world is linked to now, or null. */
async function links(page: Page, world: World): Promise<{adjustment: number | null; dividend: number | null}> {
    const ids = [world.buyTx, world.adjustmentTx, world.dividendTx];
    const rows = await jsonFrom<StoredTx[]>(await page.request.get(`${API_BASE}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`), 'read the transactions');
    const eventOf = (id: number): number | null => {
        const row = rows.find((candidate) => candidate.id === id);
        if (!row) throw new Error(`Transaction ${id} is gone: a currency change must never delete a transaction`);
        return row.asset_event_id;
    };
    expect(eventOf(world.buyTx), 'the BUY never had an event').toBeNull();
    return {adjustment: eventOf(world.adjustmentTx), dividend: eventOf(world.dividendTx)};
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

/** Pick a currency in the open asset modal and end on the closed trigger showing it. */
async function chooseCurrency(page: Page, currency: string): Promise<void> {
    await optionsClosed(page);
    const group = page.getByTestId('asset-modal-currency-group');
    await group.getByRole('combobox').click();
    await expect(group.getByRole('listbox')).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
    await group.getByRole('textbox').fill(currency);
    await page.getByTestId(`search-select-option-${currency}`).click();
    await optionsClosed(page);
    await expect(group.getByRole('combobox')).toHaveAttribute('aria-expanded', 'false');
    // An ISO code is data, not translated copy; the closed trigger holds only the chosen currency.
    await expect(group.getByRole('combobox')).toContainText(currency);
}

// ---------------------------------------------------------------------------
// Test
// ---------------------------------------------------------------------------

test.describe('Asset currency change (N68)', () => {
    test('the dry run and the confirm come before any write; cancel changes nothing; confirm keeps the split and its adjustment, deletes the rest', async ({page, request}) => {
        const world = await seedWorld(page, request);
        const patches: string[] = [];
        page.on('request', (req) => {
            if (req.method() === 'PATCH' && new URL(req.url()).pathname === `${API_BASE}/assets`) patches.push(req.url());
        });
        const summaryPath = `${API_BASE}/assets/${world.assetId}/market-data/summary`;
        await goToAssetDetailPage(page, String(world.assetId));
        await openEditAssetModal(page);
        await chooseCurrency(page, NEW_CURRENCY);

        // Save: the dry run is read, the confirm modal shows what goes and what stays, and nothing was written.
        const [summaryResponse] = await Promise.all([page.waitForResponse((response) => new URL(response.url()).pathname === summaryPath && response.request().method() === 'GET', {timeout: UI_TIMEOUT}), page.getByTestId('asset-modal-save').click()]);
        const summary = await jsonFrom<{prices: number; splits_kept: number; dry_run: boolean}>(summaryResponse, 'the currency change dry run');
        expect(summary.dry_run).toBe(true);
        expect(summary.splits_kept, 'the dry run counts the SPLIT that stays').toBe(1);
        const modal = page.getByTestId('currency-change-modal');
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        await expect(modal.getByTestId('currency-change-summary-prices')).toBeVisible();
        await expect(modal.getByTestId('currency-change-summary-events')).toBeVisible();
        await expect(modal.getByTestId('currency-change-summary-linkedtx')).toBeVisible();
        await expect(modal.getByTestId('currency-change-summary-splits')).toBeVisible();
        expect(patches, 'no PATCH before the confirm').toEqual([]);

        // Cancel: the modal closes, the form stays, and nothing changed.
        await modal.getByTestId('currency-change-cancel').click();
        await expect(modal).toBeHidden({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('asset-modal-form')).toBeVisible();
        expect(patches, 'cancel emits no mutation').toEqual([]);
        expect(await currencyOf(page, world.assetId)).toBe(OLD_CURRENCY);
        expect((await storedPrices(page, world.assetId)).length).toBeGreaterThan(0);
        expect((await storedEvents(page, world.assetId)).map((event) => event.id).sort()).toEqual([world.splitEvent, world.dividendEvent].sort());
        expect(await links(page, world)).toEqual({adjustment: world.splitEvent, dividend: world.dividendEvent});

        // Save again and confirm: ONE PATCH.
        await page.getByTestId('asset-modal-save').click();
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        const [patchResponse] = await Promise.all([page.waitForResponse((response) => new URL(response.url()).pathname === `${API_BASE}/assets` && response.request().method() === 'PATCH', {timeout: UI_TIMEOUT}), modal.getByTestId('currency-change-confirm').click()]);
        const patched = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(patchResponse, 'the currency PATCH');
        expect(patched.results.find((item) => item.asset_id === world.assetId)?.success).toBe(true);
        await expect(modal).toBeHidden({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: UI_TIMEOUT});
        expect(patches, 'the confirm is one PATCH: the interface no longer wipes first').toHaveLength(1);

        // Read back: the currency changed, the prices and the DIVIDEND went, the SPLIT and its adjustment stayed linked.
        expect(await currencyOf(page, world.assetId)).toBe(NEW_CURRENCY);
        expect(await storedPrices(page, world.assetId), 'the prices are gone').toEqual([]);
        expect(
            (await storedEvents(page, world.assetId)).map((event) => event.id),
            'only the SPLIT stays',
        ).toEqual([world.splitEvent]);
        expect(await links(page, world), 'the dividend’s transaction is unlinked (and still there); the adjustment is still linked to its split').toEqual({adjustment: world.splitEvent, dividend: null});
    });
});
