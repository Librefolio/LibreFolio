/**
 * Edit save gate E2E — GitHub issue #58 («Editing transactions asset type does not trigger save button»)
 *
 * The report: edit a stored transaction, change its type (or its asset), press Apply, leave the editor — the editor asks
 * «discard changes?», yet the Save button never became available. Two readings, asked with FIELDS THAT ARE VALID for
 * the new type, so a grey button here is a real defect:
 *
 *  1. A type change inside the swap group (BUY↔SELL, DEPOSIT↔WITHDRAWAL): «Apply» (`tx-form-save`) is enabled, the row
 *     is «edited» in the grid, Save-all (`tx-bulk-commit`) is enabled, and every time the editor asks to discard,
 *     Save-all is enabled (the two answers agree).
 *  2. The asset and the broker: the backend's update has no `asset_id` and no `broker_id`, so a stored row's cannot
 *     change (developer decision, 21/10: lock them, to change one delete and re-create). Both are fixed in the editor's
 *     Form, and still free on a row the user adds in the same editor.
 *
 * Nothing is committed: each test seeds its own rows through the API (a marker in the description), edits them in the
 * editor, discards, and deletes what it made.
 *
 * Prerequisites: backend test mode, mock data populated (TEST_USER is OWNER of «Interactive Brokers»; BTC-USD is a
 * seeded asset).
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {appears, optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

test.setTimeout(45_000);

const API = '/api/v1';
const UI_TIMEOUT = 8_000;

interface OwnedRows {
    marker: string;
    ids: number[];
}

interface CommitBody {
    committed: boolean;
    issues?: unknown[];
    results: Array<{operation: string; index: number; ids?: number[]; status: string}>;
}

interface SeededAsset {
    id: number;
    currency: string;
}

/** POST a batch (`page.request` shares the login cookie). A refused batch still answers 200, so `committed` is checked. */
async function commitViaApi(page: Page, batch: {creates?: unknown[]; deletes?: number[]}, what: string): Promise<CommitBody> {
    const resp = await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes: [], ...batch}});
    expect(resp.ok(), `${what}: HTTP ${resp.status()}`).toBe(true);
    const body = (await resp.json()) as CommitBody;
    expect(body.committed, `${what} rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return body;
}

/** The broker the mock contract makes TEST_USER's OWNER, found by name and checked. */
async function ownedMockBrokerId(page: Page): Promise<number> {
    const resp = await page.request.get(`${API}/brokers`);
    expect(resp.ok(), `GET ${API}/brokers returned ${resp.status()}`).toBe(true);
    const {items} = (await resp.json()) as {items: Array<{id: number; name: string; user_role: string | null}>};
    const broker = items.find((b) => b.name === 'Interactive Brokers');
    expect(broker?.user_role, 'TEST_USER must be OWNER of "Interactive Brokers" — check populate_mock_data.py').toBe('OWNER');
    return broker!.id;
}

/** The seeded asset with this exact ticker — read, never assumed. */
async function seededAsset(page: Page, ticker: string): Promise<SeededAsset> {
    const resp = await page.request.get(`${API}/assets/query?ticker=${encodeURIComponent(ticker)}`);
    expect(resp.ok(), `look up the ${ticker} asset: HTTP ${resp.status()}`).toBe(true);
    const assets = (await resp.json()) as SeededAsset[];
    if (assets.length !== 1) throw new Error(`Expected exactly one asset with ticker ${ticker}, found ${assets.length} — check populate_mock_data.py`);
    return assets[0];
}

/** Delete what the test owns: the ids it recorded plus every row carrying its marker. Fails loud. */
async function deleteOwnedRows(page: Page, owned: OwnedRows): Promise<void> {
    const resp = await page.request.get(`${API}/transactions`);
    expect(resp.ok(), `cleanup: GET ${API}/transactions returned ${resp.status()}`).toBe(true);
    const rows = (await resp.json()) as Array<{id: number; description: string | null}>;
    const ids = new Set(owned.ids);
    const deletes = rows.filter((r) => ids.has(r.id) || (r.description ?? '').includes(owned.marker)).map((r) => r.id);
    if (deletes.length > 0) await commitViaApi(page, {deletes}, `cleanup of rows ${deletes.join(', ')}`);
}

/** What the tests seed: a tiny funded BUY of Bitcoin and a plain cash DEPOSIT, a day apart far below the table's top. */
interface Seeded {
    buy: {id: number; description: string};
    deposit: {id: number; description: string};
    bitcoin: SeededAsset;
}

async function seedRows(page: Page, owned: OwnedRows): Promise<Seeded> {
    const brokerId = await ownedMockBrokerId(page);
    const bitcoin = await seededAsset(page, 'BTC-USD');
    const currency = bitcoin.currency;
    const funding = `${owned.marker} funding`;
    const purchase = `${owned.marker} buy`;
    const standalone = `${owned.marker} deposit`;
    const creates = [
        {broker_id: brokerId, type: 'DEPOSIT', date: daysAgoIso(305), quantity: '0', cash: {code: currency, amount: '50'}, tags: [], description: funding},
        {broker_id: brokerId, asset_id: bitcoin.id, type: 'BUY', date: daysAgoIso(304), quantity: '0.0001', cash: {code: currency, amount: '-5'}, tags: [], description: purchase},
        {broker_id: brokerId, type: 'DEPOSIT', date: daysAgoIso(303), quantity: '0', cash: {code: currency, amount: '2'}, tags: [], description: standalone},
    ];
    const setup = await commitViaApi(page, {creates}, 'setup commit');
    owned.ids.push(...setup.results.flatMap((r) => r.ids ?? []));
    const idOf = (index: number): number => {
        const id = setup.results.find((r) => r.operation === 'create' && r.index === index)?.ids?.[0];
        if (id == null) throw new Error(`setup commit reported no id for create #${index}: ${JSON.stringify(setup.results)}`);
        return id;
    };
    return {buy: {id: idOf(1), description: purchase}, deposit: {id: idOf(2), description: standalone}, bitcoin};
}

/** Open the table narrowed to the owned rows through the `id_min`/`id_max` URL filter, ending with the target on screen. */
async function goToOwnedRow(page: Page, owned: OwnedRows, rowId: number): Promise<void> {
    await navigateTo(page, `/transactions?id_min=${Math.min(...owned.ids)}&id_max=${Math.max(...owned.ids)}`);
    await waitForSettled(page.getByTestId('transactions-page'));
    await expect(page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${rowId}"]`)).toBeVisible({timeout: UI_TIMEOUT});
}

/** Select the one row and open the editor: a single selected row auto-opens its Form over the grid. */
async function openSingleEdit(page: Page, rowId: number): Promise<{bulk: Locator; form: Locator}> {
    const checkbox = page.getByTestId(`dt-row-checkbox-tx-${rowId}`);
    await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const editBtn = page.getByTestId('toolbar-action-edit');
    await expect(editBtn).toBeEnabled({timeout: UI_TIMEOUT});
    await editBtn.click();
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: UI_TIMEOUT});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: UI_TIMEOUT});
    return {bulk, form};
}

async function selectType(page: Page, typeCode: string): Promise<void> {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

/**
 * The two readings of the report, after the change in the Form:
 *  1. Apply is enabled (the fields are valid for what the row now is);
 *  2. pressed, the Form closes, the row is «edited» and Save-all is enabled;
 *  3. leaving the editor asks to discard — and Save-all was enabled when it asked.
 */
async function expectApplyThenSaveAllEnabled(page: Page, form: Locator, rowDescription: string): Promise<void> {
    const apply = page.getByTestId('tx-form-save');
    await expect(apply, '1. Form: type/asset changed, fields valid → Apply is enabled').toBeEnabled({timeout: UI_TIMEOUT});
    await apply.click();
    await expect(form, 'Apply pushes the draft into the grid and closes the Form').toBeHidden({timeout: UI_TIMEOUT});

    const row = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: rowDescription});
    await expect(row).toHaveCount(1);
    await expect(row.getByTestId('tx-bulk-row-status'), '2. Bulk: the row is edited').toHaveAttribute('data-status', 'edited', {timeout: UI_TIMEOUT});
    const saveAll = page.getByTestId('tx-bulk-commit');
    await expect(saveAll, '2. Bulk: row edited, fields valid → Save-all is enabled').toBeEnabled({timeout: UI_TIMEOUT});

    await page.getByTestId('tx-bulk-cancel').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, '3. leaving the edited editor asks to discard').toBeVisible({timeout: UI_TIMEOUT});
    await expect(saveAll, '3. the editor asked to discard, so Save-all must be enabled (same truth)').toBeEnabled();
    await discard.click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: UI_TIMEOUT});
}

test.describe('Issue #58 — Save follows an edited type or asset', () => {
    let owned: OwnedRows | null = null;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // afterEach rather than a `finally`: it also runs after a timeout, with `page.request` still usable.
    test.afterEach(async ({page}) => {
        try {
            if (owned) await deleteOwnedRows(page, owned);
        } finally {
            owned = null;
        }
    });

    async function seed(page: Page, name: string): Promise<{mine: OwnedRows; rows: Seeded}> {
        const mine: OwnedRows = {marker: `E2E-58-${name}-${uniqueSuffix()}`, ids: []};
        owned = mine;
        const rows = await seedRows(page, mine);
        return {mine, rows};
    }

    test('BUY → SELL (swap with a sign flip) keeps Apply and Save-all enabled', async ({page}) => {
        const {mine, rows} = await seed(page, 'buy-sell');
        await goToOwnedRow(page, mine, rows.buy.id);
        const {form} = await openSingleEdit(page, rows.buy.id);
        await selectType(page, 'SELL');
        await expectApplyThenSaveAllEnabled(page, form, rows.buy.description);
    });

    test('DEPOSIT → WITHDRAWAL (cash only) keeps Apply and Save-all enabled', async ({page}) => {
        const {mine, rows} = await seed(page, 'dep-wd');
        await goToOwnedRow(page, mine, rows.deposit.id);
        const {form} = await openSingleEdit(page, rows.deposit.id);
        await selectType(page, 'WITHDRAWAL');
        await expectApplyThenSaveAllEnabled(page, form, rows.deposit.description);
    });

    test('a stored row’s asset and broker are locked in the editor’s Form, a new row’s are not (#58)', async ({page}) => {
        const {mine, rows} = await seed(page, 'asset');
        await goToOwnedRow(page, mine, rows.buy.id);
        const {form} = await openSingleEdit(page, rows.buy.id);
        await expect(page.getByTestId('tx-form-asset-trigger'), 'the asset of a saved BUY is fixed').toHaveAttribute('data-disabled', 'true', {timeout: UI_TIMEOUT});
        await expect(page.getByTestId('tx-form-broker-readonly'), 'the broker of a saved BUY is shown as text, not picked').toBeVisible({timeout: UI_TIMEOUT});

        await page.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: UI_TIMEOUT});
        await page.getByTestId('tx-bulk-add-row').click();
        await expect(form, 'a new row opens its own Form').toBeVisible({timeout: UI_TIMEOUT});
        await selectType(page, 'BUY');
        await expect(page.getByTestId('tx-form-asset-trigger'), 'the asset of a new row is picked').toHaveAttribute('data-disabled', 'false', {timeout: UI_TIMEOUT});
        await expect(page.getByTestId('tx-form-broker-wrap').getByRole('combobox'), 'the broker of a new row is picked').toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: UI_TIMEOUT});

        await page.getByTestId('tx-bulk-cancel').click();
        const discard = page.getByTestId('confirm-modal-confirm');
        if (await appears(discard)) await discard.click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: UI_TIMEOUT});
    });
});
