/**
 * Bulk editor — «fill from price history» for imported rewards (project 79, STK-4b).
 *
 * A REWARD whose file gave no value arrives in the bulk editor with the blocking todo `reward_value` on its cost basis
 * (the generic CSV always adds it, STK-4a). The editor counts those rows in its own info banner and offers to fill them
 * from the stored price history: the backend answers, per row, the asset's close of THAT very day (never the day before
 * or after), per unit, in the price's currency. The contract, from the file to the grid:
 *
 *   - the banner `tx-bulk-reward-fill` publishes `data-pending` (rows waiting for a value) and `data-state`
 *     (`idle` | `running`); its button `tx-bulk-reward-fill-button` starts the fill;
 *   - the outcome `tx-bulk-reward-fill-result` publishes `data-filled`, `data-no-price`, `data-no-history`, `data-failed`,
 *     and the editor records the event `tx.bulk.rewards.filled` with the same counts;
 *   - the row whose day has a close holds it, in Manual (its form shows the amount and the currency); the row whose day
 *     has none — though the day before has one — stays empty, its todo open, so the banner still counts it.
 *
 * The data is the real thing, end to end: a generic CSV of this test's own (two REWARD rows of one invented ticker, on D1
 * and D2), parsed by the real plugin, its ticker resolved in the review to an asset this test created with closes on D1
 * and D3 but not D2. The premises are checked on the wire (the parse's todos, the stored closes). Nothing is saved: the
 * editor is closed through its unsaved-changes guard.
 *
 * Owned data (parallel-safe): a disposable user, its own EUR asset with its closes, its own broker (generic CSV as
 * default plugin, opened before the file's dates), its own uploaded file under a unique name; afterEach deletes the file,
 * the broker (force), the asset (its prices go with it) and the user.
 *
 * For the developer, a screenshot of the banner after the fill is written under `test-results/` (its path is logged).
 *
 * Key data-testids: tx-import-button · import-wizard-stepper · import-wizard-step1 · import-wizard-next · import-wizard-parse ·
 * import-wizard-step4 · import-wizard-resolve-section · asset-select-trigger / -search · search-select-option-<id> ·
 * identifier-prompt-skip · import-wizard-unresolved-count · import-wizard-import · tx-bulk-modal-root · tx-bulk-body ·
 * tx-bulk-reward-fill / -button / -result (new) · tx-bulk-cost-basis-manual · row-actions-<rowId> ·
 * context-menu-action-edit-single · tx-form-modal · tx-form-cost-basis-input-amount / -currency · tx-form-cancel ·
 * tx-bulk-close · confirm-modal-confirm.
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {continueToReview, deleteOwnedReports, parseSelectedFile, selectBrokerFile, type OwnedReport, type ParseResponse} from '../fixtures/import-wizard';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const GENERIC = 'broker_generic_csv';
/** D1 has a close, D2 none (the day before, D1, has one: a backward fill would answer), D3 a close (a forward fill would). */
const D1 = '2024-03-04';
const D2 = '2024-03-05';
const D3 = '2024-03-06';
const CLOSE_D1 = '61.25';
const CLOSE_D3 = '70';
const CURRENCY = 'EUR';
const UI_TIMEOUT = 10_000;

test.setTimeout(120_000);

type Owned = {id: number; name: string};
type ParsedTodo = {tx_index: number; field: string; severity: string; reason_code: string};
type ParsedFile = Pick<ParseResponse, 'file_id' | 'broker_id'> & {plugin_code: string; transactions: Array<{type?: string; description?: string | null}>; field_todos?: ParsedTodo[]};
type FillEventDetail = {filled: number; noPrice: number; noHistory: number};

/** What the running test created, emptied by afterEach. Module state on purpose: a worker runs one test at a time. */
const ownedReports: OwnedReport[] = [];
const ownedAssetIds: number[] = [];
const ownedBrokerIds: number[] = [];

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

/** An EUR asset of this test's own. The page keeps its assets in a session cache: create it before the page loads them. */
async function createOwnedAsset(page: Page): Promise<Owned> {
    const name = `STK-4b reward fill ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/assets`, {data: [{display_name: name, currency: CURRENCY, asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/** The closes of D1 and D3, stored and read back: D1 and D3 hold them, D2 holds no stored close (at most a backward fill). */
async function storeClosesAroundTheGap(page: Page, assetId: number): Promise<void> {
    const stored = await page.request.post(`${API}/assets/prices`, {
        data: [
            {
                asset_id: assetId,
                prices: [
                    {date: D1, close: CLOSE_D1, currency: CURRENCY},
                    {date: D3, close: CLOSE_D3, currency: CURRENCY},
                ],
            },
        ],
    });
    expect(stored.ok(), `store the closes: HTTP ${stored.status()} ${await stored.text()}`).toBe(true);
    const read = await page.request.post(`${API}/assets/prices/query`, {data: [{asset_id: assetId, date_range: {start: D1, end: D3}}]});
    expect(read.ok(), `read the closes back: HTTP ${read.status()}`).toBe(true);
    const body = (await read.json()) as {items?: Array<{asset_id: number; prices?: Array<{date: string; close: string | number | null; backward_fill_info?: unknown}>}>};
    const prices = body.items?.find((item) => item.asset_id === assetId)?.prices ?? [];
    const storedRows = prices.filter((point) => point.backward_fill_info == null);
    expect(
        storedRows.map((point) => [point.date, Number(point.close)]),
        'precondition: stored closes on D1 and D3 only, none on D2',
    ).toEqual([
        [D1, Number(CLOSE_D1)],
        [D3, Number(CLOSE_D3)],
    ]);
}

/** A broker of this test's own with the generic CSV plugin as default, opened long before the file's dates. */
async function createOwnedBroker(page: Page): Promise<Owned> {
    const name = `STK-4b reward broker ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', allow_cash_overdraft: true, default_import_plugin: GENERIC}]});
    expect(response.ok(), `create the owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = results.find((result) => result.name === name);
    if (typeof created?.broker_id === 'number') ownedBrokerIds.push(created.broker_id);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The owned broker ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.broker_id, name};
}

/** This test's own generic CSV — a REWARD on D1 and one on D2 of `ticker`, each with its own description — uploaded to `broker`. */
async function uploadOwnedFile(page: Page, broker: Owned, ticker: string, descriptions: {d1: string; d2: string}): Promise<OwnedReport> {
    const fileName = `reward-fill-${uniqueSuffix()}.csv`;
    const csv = ['date,type,quantity,asset,description', `${D1},reward,0.5,${ticker},${descriptions.d1}`, `${D2},reward,0.25,${ticker},${descriptions.d2}`].join('\n') + '\n';
    const response = await page.request.post(`${API}/brokers/import/upload`, {
        multipart: {broker_id: String(broker.id), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}},
    });
    expect(response.ok(), `upload ${fileName}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const uploaded = (await response.json()) as {file_id: string; filename: string; target_broker_id: number | null};
    const own: OwnedReport = {brokerId: broker.id, fileId: uploaded.file_id, fileName};
    ownedReports.push(own);
    expect(uploaded, `${fileName} lands on "${broker.name}" under its own name`).toMatchObject({filename: fileName, target_broker_id: broker.id});
    return own;
}

async function deleteOwnedBrokers(page: Page): Promise<string[]> {
    const failures: string[] = [];
    for (const id of ownedBrokerIds.splice(0)) {
        const response = await page.request.delete(`${API}/brokers?ids=${id}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || body?.results?.find((result) => result.id === id)?.success !== true) failures.push(`broker ${id}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    }
    return failures;
}

async function deleteOwnedAssets(page: Page): Promise<string[]> {
    const failures: string[] = [];
    for (const id of ownedAssetIds.splice(0)) {
        const response = await page.request.delete(`${API}/assets?asset_ids=${id}`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
        if (!response.ok() || body?.results?.find((result) => result.asset_id === id)?.success !== true) failures.push(`asset ${id}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    }
    return failures;
}

// ---------------------------------------------------------------------------
// Wizard
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** The wizard, opened from the toolbar and settled on step 1; then Next (the file is already uploaded), to step 2. */
async function openWizardAndAdvance(page: Page) {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: 5_000});
    await waitForSettled(step1, 15_000);
    await page.getByTestId('import-wizard-next').click();
}

/** The option list `trigger` controls is open and has finished loading. */
async function optionListReady(trigger: Locator) {
    await expect(trigger, 'the select is open').toHaveAttribute('aria-expanded', 'true', {timeout: 5_000});
    const listId = await trigger.getAttribute('aria-controls');
    if (!listId) throw new Error('The select names no option list it controls (aria-controls)');
    const list = trigger.page().locator(`[id="${listId}"]`);
    await expect(list).toBeVisible({timeout: 5_000});
    await expect(list).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
}

/**
 * The review's one resolve card (the file's invented ticker, no candidate) is bound to `asset`: its name searched, the
 * option carrying its id clicked, the identifier prompt skipped — the asset holds no ticker and the file names one, so
 * picking it always raises the prompt (`checkAndPromptIdentifier`).
 */
async function resolveToOwnedAsset(page: Page, step4: Locator, asset: Owned) {
    const section = step4.getByTestId('import-wizard-resolve-section');
    await expect(section, 'the file has one unresolved asset').toBeVisible({timeout: 5_000});
    const trigger = section.getByTestId('asset-select-trigger');
    await expect(trigger, 'one card: the file holds one ticker').toHaveCount(1, {timeout: 5_000});
    await trigger.click();
    await optionListReady(trigger);
    const search = section.getByTestId('asset-select-search');
    await search.fill(asset.name);
    await expect(search).toHaveValue(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 10_000});
    const skip = page.getByTestId('identifier-prompt-skip');
    await expect(skip).toBeVisible({timeout: 5_000});
    await skip.click();
    await expect(skip).toHaveCount(0, {timeout: 5_000});
    await waitForSettled(step4, 20_000);
    await expect(step4.getByTestId('import-wizard-unresolved-count'), 'no asset is left unresolved').toHaveCount(0);
}

/** Own broker and file → wizard → review (the parse checked on the wire) → the ticker resolved → Import → the editor, settled. */
async function importIntoEditor(page: Page, asset: Owned, descriptions: {d1: string; d2: string}): Promise<Locator> {
    const broker = await createOwnedBroker(page);
    const own = await uploadOwnedFile(page, broker, uniqueToken(5), descriptions);
    await goToTransactions(page);
    await openWizardAndAdvance(page);
    await selectBrokerFile(page, own);
    const parsed = (await parseSelectedFile(page, own.fileId)) as ParsedFile;

    // The premise, on the wire: the real generic CSV plugin read two REWARDs, each asking for its value.
    expect(parsed.plugin_code, 'the broker default plugin parsed the file').toBe(GENERIC);
    expect(
        parsed.transactions.map((tx) => [tx.type, tx.description]),
        'two REWARD rows, in file order',
    ).toEqual([
        ['REWARD', descriptions.d1],
        ['REWARD', descriptions.d2],
    ]);
    const rewardTodos = (parsed.field_todos ?? []).filter((todo) => todo.reason_code === 'reward_value');
    expect(rewardTodos.map((todo) => [todo.tx_index, todo.field, todo.severity]).sort(), 'each REWARD carries the blocking reward_value todo on its cost basis').toEqual([
        [0, 'cost_basis_override', 'blocker'],
        [1, 'cost_basis_override', 'blocker'],
    ]);

    const step4 = await continueToReview(page, parsed);
    await resolveToOwnedAsset(page, step4, asset);
    const importButton = page.getByTestId('import-wizard-import');
    await expect(importButton).toBeEnabled({timeout: 15_000});
    await importButton.click();
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 15_000});
    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(root, 30_000);
    return root;
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

/** The editor row holding `description` (this test's own marker, not a translation): exactly one. */
async function editorRow(root: Locator, description: string): Promise<Locator> {
    const row = root.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: description});
    await expect(row, `one editor row carries "${description}"`).toHaveCount(1, {timeout: UI_TIMEOUT});
    return row;
}

/** Hover an editor row and run one of its actions through its kebab menu. */
async function rowAction(page: Page, row: Locator, actionId: string): Promise<void> {
    await expect(row, 'the row is on the page shown').toBeVisible({timeout: UI_TIMEOUT});
    const rowId = await row.getAttribute('data-row-id');
    expect(rowId, 'an editor row carries its op tempId as data-row-id').toBeTruthy();
    await row.hover();
    const kebab = row.getByTestId(`row-actions-${rowId}`);
    await expect(kebab).toBeVisible({timeout: UI_TIMEOUT});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: UI_TIMEOUT});
    await action.click();
    await expect(action, 'the row menu closes on its action').toBeHidden({timeout: UI_TIMEOUT});
}

/** Never Save All: close the editor through its unsaved-changes guard and discard. */
async function closeEditorWithoutSaving(page: Page, root: Locator) {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor — imported rewards filled from the price history (79 STK-4b)', () => {
    /** The account the running test writes with: its own, so its broker, asset and file are seen by no other spec. */
    let account: DisposableUser | null = null;

    test.beforeEach(async ({page, request}) => {
        account = await registerDisposableUser(request, 'rwf');
        await prepareOnboardingAccount(page, account, []);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page, request}) => {
        try {
            if (ownedReports.length === 0 && ownedBrokerIds.length === 0 && ownedAssetIds.length === 0) return;
            await page.goto('about:blank');
            const failures: string[] = [];
            try {
                await deleteOwnedReports(page, ownedReports);
            } catch (error) {
                failures.push(String(error));
            }
            failures.push(...(await deleteOwnedBrokers(page)), ...(await deleteOwnedAssets(page)));
            expect(failures, 'cleanup removes the file, the broker and the asset this test created').toEqual([]);
        } finally {
            if (account) await deleteDisposableUser(request, account);
            account = null;
        }
    });

    test('the close of the day fills its row; a day without a close stays open, even with a close the day before', async ({page}, testInfo) => {
        const asset = await createOwnedAsset(page);
        await storeClosesAroundTheGap(page, asset.id);
        const mark = uniqueSuffix();
        const descriptions = {d1: `reward-d1-${mark}`, d2: `reward-d2-${mark}`};
        const root = await importIntoEditor(page, asset, descriptions);

        // Before: both REWARDs wait for a value, and the banner offers to fill them.
        const banner = root.getByTestId('tx-bulk-reward-fill');
        await expect(banner, 'the editor offers to fill the imported rewards').toBeVisible({timeout: UI_TIMEOUT});
        await expect(banner).toHaveAttribute('data-pending', '2');
        await expect(banner).toHaveAttribute('data-state', 'idle');
        await expect(banner.getByTestId('tx-bulk-reward-fill-result'), 'no fill has run yet').toHaveCount(0);
        const rowD1 = await editorRow(root, descriptions.d1);
        const rowD2 = await editorRow(root, descriptions.d2);
        await expect(rowD1.getByTestId('tx-bulk-cost-basis-manual'), 'premise: the D1 reward has no value yet').toHaveCount(0);

        // The fill: one click, one outcome, one event with the same counts.
        const since = await eventSeq(page);
        const button = banner.getByTestId('tx-bulk-reward-fill-button');
        await expect(button).toBeEnabled();
        await button.click();
        const result = banner.getByTestId('tx-bulk-reward-fill-result');
        await expect(result).toBeVisible({timeout: 15_000});
        await expect(result).toHaveAttribute('data-failed', 'false');
        await expect(result).toHaveAttribute('data-filled', '1');
        await expect(result).toHaveAttribute('data-no-price', '1');
        await expect(result).toHaveAttribute('data-no-history', '0');
        await expect(banner).toHaveAttribute('data-state', 'idle');
        const event = await waitForEvent(page, 'tx.bulk.rewards.filled', {since});
        expect(event.detail as FillEventDetail, 'the event carries the outcome').toEqual({filled: 1, noPrice: 1, noHistory: 0});

        // The D1 row holds its value; the D2 row does not, and still waits — the banner counts it alone now.
        await expect(rowD1.getByTestId('tx-bulk-cost-basis-manual'), 'the D1 reward now holds a value written in Manual').toBeVisible({timeout: UI_TIMEOUT});
        await expect(rowD2, 'presence barrier: the D2 row is on screen').toBeVisible();
        await expect(rowD2.getByTestId('tx-bulk-cost-basis-manual'), 'no close on D2: nothing is filled, never the close of D1 or D3').toHaveCount(0);
        await expect(banner, 'the D2 reward still waits for a value').toHaveAttribute('data-pending', '1');

        const shot = testInfo.outputPath('reward-fill-banner.png');
        await banner.screenshot({path: shot});
        console.log(`[tx-reward-fill] banner after the fill: ${shot}`);

        // The value itself, read where it is exact: the row's own form shows the close of D1, per unit, in its currency.
        await rowAction(page, rowD1, 'edit-single');
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'the D1 row opens in its form').toBeVisible({timeout: UI_TIMEOUT});
        await expect(form.getByTestId('tx-form-cost-basis-input-amount'), 'the close of D1').toHaveValue(CLOSE_D1, {timeout: UI_TIMEOUT});
        await expect(form.getByTestId('tx-form-cost-basis-input-currency'), 'in the price currency').toHaveText(CURRENCY);
        await form.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: UI_TIMEOUT});

        await closeEditorWithoutSaving(page, root);
    });
});
