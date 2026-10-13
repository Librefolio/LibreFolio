/**
 * tx-event-picker.spec.ts — Event Picker E2E Tests
 *
 * Tests the AssetEventSelect component within the FormModal:
 * - Card-style dropdown with emoji, date, amount
 * - Delta display when cash is filled
 * - Slider range updates
 * - Hidden for non-linkable types (BUY)
 * - Selection persists across validate
 *
 * Prerequisites: backend test mode, mock data populated.
 * Mock data contract:
 *   - Apple (ticker AAPL) has DIVIDEND event at today-3 (within ±7 default range)
 *   - e2e_test_user has OWNER on Interactive Brokers
 * Both are looked up through the API — the broker by its exact name, Apple by its exact
 * ticker — and picked in the form by the option carrying their id, never by position.
 *
 * The inline-create test writes an asset event, so it never writes one on Apple: it
 * creates a manual asset of its own, creates the event there, and deletes the asset —
 * the event with it — afterwards. Its transaction form is never saved.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(45_000);

/** An asset the form is to pick, by the id its option carries and the name its search finds. */
type PickableAsset = {id: number; name: string};

/** The seeded broker the DIVIDEND form books on, and the ticker of the seeded asset it books for. */
const BROKER_NAME = 'Interactive Brokers';
const APPLE_TICKER = 'AAPL';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** The id of the seeded broker named exactly `name` — read, never assumed. */
async function seededBrokerId(page: Page, name: string): Promise<number> {
    const response = await page.request.get('/api/v1/brokers');
    expect(response.ok(), `list the brokers: HTTP ${response.status()}`).toBe(true);
    const {items} = (await response.json()) as {items: Array<{id: number; name: string}>};
    const matches = items.filter((broker) => broker.name === name);
    if (matches.length !== 1) throw new Error(`Expected exactly one broker named "${name}" visible to this user, found ${matches.length} — check populate_mock_data.py`);
    return matches[0].id;
}

/** The seeded asset with this exact ticker, with the name its search finds — read, never assumed. */
async function seededAsset(page: Page, ticker: string): Promise<PickableAsset> {
    const response = await page.request.get(`/api/v1/assets/query?ticker=${encodeURIComponent(ticker)}`);
    expect(response.ok(), `look up the ${ticker} asset: HTTP ${response.status()}`).toBe(true);
    const assets = (await response.json()) as Array<{id: number; display_name: string}>;
    if (assets.length !== 1) throw new Error(`Expected exactly one asset with ticker ${ticker}, found ${assets.length} — check populate_mock_data.py`);
    return {id: assets[0].id, name: assets[0].display_name};
}

async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** Select a transaction type via SearchSelect. */
async function selectType(page: Page, typeCode: string) {
    const typeButton = page.getByTestId('tx-form-type');
    await typeButton.click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

/** Pick the broker named exactly `brokerName`, by the option carrying its id. */
async function pickBroker(page: Page, brokerName: string) {
    const brokerId = await seededBrokerId(page, brokerName);
    // The broker field holds one select, so its combobox is the trigger: no position needed.
    await page.getByTestId('tx-form-broker-wrap').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

/**
 * Pick exactly the asset with this id: search its name, then click the option carrying its
 * id — never the first option of whatever the search left. The select searches inline, so
 * its search input is always there: asserted, never probed.
 */
async function pickAsset(page: Page, asset: PickableAsset) {
    await page.getByTestId('tx-form-asset-trigger').click();
    const searchInput = page.getByTestId('tx-form-asset-search');
    await expect(searchInput).toBeVisible({timeout: 3_000});
    await searchInput.fill(asset.name);
    await expect(searchInput).toHaveValue(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

/** Open the "Optional" disclosure if not already open. */
async function openOptionalSection(page: Page) {
    const toggle = page.getByTestId('tx-form-optional-toggle');
    // Click to open the <details> if closed
    const details = toggle.locator('..');
    const isOpen = await details.getAttribute('open');
    if (isOpen === null) {
        await toggle.click();
        // <details open> is the element itself reporting the state the click asked for.
        await expect(details).toHaveAttribute('open', '', {timeout: 3_000});
    }
}

/**
 * Setup common DIVIDEND form with Apple on Interactive Brokers.
 * Date defaults to today (which covers the today-3 DIVIDEND event).
 */
async function setupDividendForm(page: Page) {
    const apple = await seededAsset(page, APPLE_TICKER);
    await openCreateFlow(page);
    await selectType(page, 'DIVIDEND');
    await pickBroker(page, BROKER_NAME);
    await pickAsset(page, apple);
    // Date is auto-set to today by FormModal
}

/**
 * A manual asset of this spec's own — where the inline modal's new event lands.
 *
 * Not Apple: an asset is a global row, so an event created on it is every other spec's
 * input — the picker offers it to every DIVIDEND on Apple, and a DIVIDEND committed on
 * Apple could link to it. Deleting it afterwards would not make Apple safe either: an
 * event saved without an id is matched on (date, type) and updated IN PLACE, so on a
 * day Apple already carries a DIVIDEND the "new" event would overwrite that one, and
 * its cleanup would delete a row this spec never created. On an asset of its own the
 * event can only be its own.
 *
 * The id is recorded for cleanup before anything about the result is checked.
 */
async function createOwnedAsset(page: Page, ownedAssetIds: number[]): Promise<PickableAsset> {
    const name = `E2E event picker ${uniqueSuffix()}`;
    const response = await page.request.post('/api/v1/assets', {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `Owned asset setup: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Owned asset setup returned no id for ${name}: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/** Delete the assets this spec created; their events go with them (asset_events cascade on the asset). */
async function deleteOwnedAssets(page: Page, ownedAssetIds: readonly number[]): Promise<void> {
    if (ownedAssetIds.length === 0) return;
    try {
        // Unmount the form first, so nothing on the page queries the asset while it goes.
        await page.goto('about:blank');
    } finally {
        for (const id of ownedAssetIds) {
            const response = await page.request.delete(`/api/v1/assets?asset_ids=${id}`);
            expect(response.ok(), `Delete owned asset ${id}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
            const body = (await response.json()) as {results: Array<{asset_id: number; success: boolean; message?: string}>};
            const result = body.results.find((item) => item.asset_id === id);
            expect(result?.success, `Owned asset ${id} and its events are deleted: ${result?.message ?? 'missing result'}`).toBe(true);
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Event Picker', () => {
    /** Assets created by the running test; deleted after it, whatever its outcome. */
    let ownedAssetIds: number[] = [];

    test.beforeEach(async ({page}) => {
        ownedAssetIds = [];
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page}) => {
        await deleteOwnedAssets(page, ownedAssetIds);
    });

    test('picker hidden for BUY type', async ({page}) => {
        const apple = await seededAsset(page, APPLE_TICKER);
        await openCreateFlow(page);
        await selectType(page, 'BUY');
        await pickBroker(page, BROKER_NAME);
        await pickAsset(page, apple);

        // Optional section should NOT contain event picker for BUY. The picker lives in that
        // section, which starts folded — so it is opened first, and a control it always holds
        // (the description) proves it is on screen: without both, "not visible" would also be
        // true of a DIVIDEND, whose picker is merely folded away.
        await openOptionalSection(page);
        await expect(page.getByTestId('tx-form-description')).toBeVisible({timeout: 3_000});
        await expect(page.getByTestId('tx-form-event-select')).toHaveCount(0);
    });

    test('picker visible for DIVIDEND with asset', async ({page}) => {
        await setupDividendForm(page);

        // Open the optional section to see the event picker
        await openOptionalSection(page);

        // Event picker should be visible
        const eventSelect = page.getByTestId('tx-form-event-select');
        await expect(eventSelect).toBeVisible({timeout: 5_000});
    });

    test('slider is visible with max=30', async ({page}) => {
        await setupDividendForm(page);
        await openOptionalSection(page);

        // Open the picker dropdown to see the slider
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger).toBeVisible({timeout: 5_000});
        await trigger.click();

        // Slider should be visible inside the dropdown header
        const slider = page.getByTestId('tx-form-event-slider');
        await expect(slider).toBeVisible({timeout: 3_000});

        // The range input inside should have max=30
        const rangeInput = slider.locator('input[type="range"]');
        await expect(rangeInput).toBeVisible();
        await expect(rangeInput).toHaveAttribute('max', '30');
    });

    test('event options show card-style format with emoji', async ({page}) => {
        await setupDividendForm(page);
        await openOptionalSection(page);

        // Wait for event select
        const eventSelect = page.getByTestId('tx-form-event-select');
        await expect(eventSelect).toBeVisible({timeout: 5_000});

        // Open the dropdown — click on the trigger button
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await trigger.click();

        // Should show the 💰 emoji (DIVIDEND) in at least one option of THIS dropdown — the
        // card's icon is not translated text, and a filtered collection makes .first() an
        // instance, not a position.
        const dividendOption = page.getByTestId('tx-form-event-picker-dropdown').getByRole('option').filter({hasText: '💰'});
        await expect(dividendOption.first()).toBeVisible({timeout: 5_000});
    });

    test('create new event via inline modal', async ({page}) => {
        // The event lands on an asset of this test's own (see createOwnedAsset). The page
        // keeps its assets in a session cache loaded before the asset existed: load it again.
        const asset = await createOwnedAsset(page, ownedAssetIds);
        await goToTransactions(page);

        // The same DIVIDEND form on Interactive Brokers, on the owned asset. Never saved.
        await openCreateFlow(page);
        await selectType(page, 'DIVIDEND');
        await pickBroker(page, BROKER_NAME);
        await pickAsset(page, asset);
        await openOptionalSection(page);

        // Open event picker dropdown
        const trigger = page.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger).toBeVisible({timeout: 5_000});
        await trigger.click();

        // Click "+ New event" button in footer
        const createBtn = page.getByTestId('tx-form-event-create-new');
        await expect(createBtn).toBeVisible({timeout: 3_000});
        await createBtn.click();

        // Mini modal should appear
        const modal = page.getByTestId('event-create-mini-modal');
        await expect(modal).toBeVisible({timeout: 3_000});

        // Type should default to DIVIDEND. The select shows the type's icon beside its
        // label: 💰 is DIVIDEND's, and unlike the label it is not translated text.
        const typeSelect = page.getByTestId('event-create-type');
        await expect(typeSelect).toContainText('💰', {timeout: 3_000});

        // Fill amount
        const amountInput = page.getByTestId('event-create-amount');
        await amountInput.fill('1.50');
        await expect(amountInput).toHaveValue('1.50');

        // Fill notes — a marker only this test writes
        const note = `E2E test event ${uniqueSuffix()}`;
        const notesInput = page.getByTestId('event-create-notes');
        await notesInput.fill(note);
        await expect(notesInput).toHaveValue(note);

        // Submit
        const submitBtn = page.getByTestId('event-create-submit');
        await submitBtn.click();

        // Modal should close and event should be auto-selected
        await expect(modal).not.toBeVisible({timeout: 10_000});

        // The trigger should now show the newly created event (with 💰 emoji) — this
        // test's own, by the note only it wrote
        await expect(trigger).toContainText('💰', {timeout: 5_000});
        await expect(trigger).toContainText(note);
    });
});
