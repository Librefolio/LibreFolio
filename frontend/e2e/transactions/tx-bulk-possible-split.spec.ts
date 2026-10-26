/**
 * Bulk editor — a stock split an import flagged `possible_split` (W-B87, block 3 «Bulk»).
 *
 * The Revolut plugin enters a `STOCK SPLIT` row as an incoming ADJUSTMENT at no cost and attaches a warning todo
 * `{field: 'asset_event_id', reason_code: 'possible_split', context: {ticker, added_quantity, ...}}`. Until now the editor
 * showed it as one line of the generic «fields to verify» banner. The contract, from the wizard's end to the grid:
 *
 *   - the review step says, before the import, that the editor will ask to link the split
 *     (`import-review-possible-split-note`);
 *   - the editor lists the row in its own banner, `tx-bulk-possible-split`, one `possible-split-row` per row
 *     (`data-row-id` is the grid row's), and the generic banner (`tx-bulk-todo-warnings`) does not carry it;
 *   - SC1 «create the SPLIT event and link it» (`possible-split-create`): the mini modal opens on SPLIT, whose amount is a
 *     RATIO (new shares per old share); a ratio typed and created writes a real SPLIT event on the asset and links it to
 *     the row: the row leaves the banner and the event column of its grid row shows the event;
 *   - SC2 «link an existing event» (`possible-split-link`): an inline picker lists the asset's events around the row's date;
 *     the SPLIT created before through the API is picked, and the row leaves the banner the same way.
 *
 * The data is the real thing, end to end: the file is `fixtures/revolut-invest-possible-split.csv` (invented ticker, a BUY of
 * 1.5 shares and the split adding 3 more: a 3 for 1), parsed by the real Revolut plugin, never a mocked parse. The premise
 * is checked on the parse response itself, so a backend that stopped flagging the split fails the corridor by name instead of
 * the banner by absence. Nothing is saved as a transaction: the editor is closed through its unsaved-changes guard.
 *
 * Owned data (parallel-safe): every test creates its own USD asset (the invented ticker is resolved to it in the review),
 * its own broker (Revolut as default plugin, opened before every date of the file, overdraft allowed), uploads its own copy
 * of the file under a unique name, and — SC2 — its own SPLIT event on that asset. afterEach leaves the page, deletes the
 * uploaded file, the broker (force) and the asset (its events go with it). The wording of the SPLIT label is read from the
 * catalogue in the language of the page, never typed.
 *
 * Key data-testids: tx-import-button · import-wizard-stepper · import-wizard-next · import-wizard-parse · import-wizard-step4 ·
 * import-wizard-resolve-section · asset-select-trigger / -search · search-select-option-<id> · identifier-prompt-skip ·
 * import-wizard-import · import-review-possible-split-note (new) · tx-bulk-modal-root · tx-bulk-body ·
 * tx-bulk-possible-split / possible-split-row / possible-split-create / possible-split-link / possible-split-goto (new) ·
 * tx-bulk-todo-warnings · tx-form-event-picker-trigger / -dropdown · event-create-mini-modal / event-create-type-button /
 * event-create-ratio-hint (new) / event-create-amount / event-create-submit · tx-bulk-close · confirm-modal-confirm.
 */

import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {t as catalogueText} from '../fixtures/i18n-data';
import {continueToReview, deleteOwnedReports, parseSelectedFile, selectBrokerFile, type OwnedReport} from '../fixtures/import-wizard';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';
import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const REVOLUT = 'broker_revolut';
const TEMPLATE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../fixtures/revolut-invest-possible-split.csv');
const TICKER_PLACEHOLDER = '__TICKER__';
/** The day of the split row in the file, and the ratio its 1.5 held shares + 3 added make: (1.5 + 3) / 1.5. */
const SPLIT_DATE = '2024-06-03';
const SPLIT_RATIO = '3';
const UI_TIMEOUT = 10_000;

test.setTimeout(120_000);

type Owned = {id: number; name: string};
type ParsedTodo = {tx_index: number; field: string; severity: string; reason_code: string; context?: Record<string, unknown>};
type ParsedFile = {plugin_code: string; transactions: unknown[]; field_todos?: ParsedTodo[]};

/** What the running test created, emptied by afterEach. Module state on purpose: a worker runs one test at a time. */
const ownedReports: OwnedReport[] = [];
const ownedAssetIds: number[] = [];
const ownedBrokerIds: number[] = [];

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

/** A USD asset of this test's own, never a seeded one. The page keeps its assets in a session cache: create it before the page loads them. */
async function createOwnedAsset(page: Page): Promise<Owned> {
    const name = `W-B87 split asset ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/assets`, {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/** A broker of this test's own with the Revolut plugin as default, opened long before the file's dates, overdraft allowed (the file has no deposit). */
async function createOwnedBroker(page: Page): Promise<Owned> {
    const name = `W-B87 split broker ${uniqueSuffix()}`;
    const response = await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', allow_cash_overdraft: true, default_import_plugin: REVOLUT}]});
    expect(response.ok(), `create the owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = results.find((result) => result.name === name);
    if (typeof created?.broker_id === 'number') ownedBrokerIds.push(created.broker_id);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The owned broker ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.broker_id, name};
}

/** This test's own copy of the Revolut file, its placeholder replaced by `ticker`, uploaded to `broker` under a unique name. */
async function uploadOwnedFile(page: Page, broker: Owned, ticker: string): Promise<OwnedReport> {
    const fileName = `revolut-possible-split-${uniqueSuffix()}.csv`;
    const csv = readFileSync(TEMPLATE, 'utf8').split(TICKER_PLACEHOLDER).join(ticker);
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

/** A SPLIT event of ratio `amount` on `assetId` at `date`, created through the API; returns its id. It goes with the asset. */
async function createSplitEvent(page: Page, assetId: number, date: string, amount: string): Promise<number> {
    const response = await page.request.post(`${API}/assets/events`, {data: [{asset_id: assetId, mode: 'create', events: [{date, type: 'SPLIT', value: {code: 'USD', amount}}]}]});
    expect(response.ok(), `create the SPLIT event: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{event_ids?: number[]}>};
    const id = body.results[0]?.event_ids?.[0];
    if (typeof id !== 'number') throw new Error(`The SPLIT event got no id: ${JSON.stringify(body)}`);
    return id;
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
 * The review's one resolve card (the file's invented ticker, no candidate) is bound to `asset`: its name searched, the option
 * carrying its id clicked, the identifier prompt skipped (the asset holds no ticker, so picking it always raises it).
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

/**
 * Own data → editor: the broker, the asset, the file, the wizard walked to the review (the parse checked), the ticker
 * resolved to the owned asset, Import clicked. Returns what the test needs of the editor; the review has been shown first, and the
 * note that announces the split is checked softly on the way.
 */
async function importIntoEditor(page: Page, asset: Owned): Promise<{root: Locator; parsed: ParsedFile}> {
    const broker = await createOwnedBroker(page);
    const ticker = uniqueToken(5);
    const own = await uploadOwnedFile(page, broker, ticker);
    await goToTransactions(page);
    await openWizardAndAdvance(page);
    await selectBrokerFile(page, own);
    const parsed = (await parseSelectedFile(page, own.fileId)) as ParsedFile;

    // The premise, on the wire: the real Revolut plugin read the file and flagged exactly one split.
    expect(parsed.plugin_code, 'the broker default plugin parsed the file').toBe(REVOLUT);
    expect(parsed.transactions, 'a BUY and the split').toHaveLength(2);
    const splitTodos = (parsed.field_todos ?? []).filter((todo) => todo.reason_code === 'possible_split');
    expect(splitTodos, 'the plugin flags the split').toHaveLength(1);
    expect(splitTodos[0]).toMatchObject({field: 'asset_event_id', severity: 'warning'});
    expect(splitTodos[0].context, 'with its ticker and the shares added').toMatchObject({ticker, added_quantity: '3'});

    const step4 = await continueToReview(page, parsed);
    await resolveToOwnedAsset(page, step4, asset);
    // Soft: a missing note must not hide what the editor does afterwards — one red run reports every missing piece.
    const reviewNote = step4.getByTestId('import-review-possible-split-note');
    await expect.soft(reviewNote, 'the review announces that the editor will ask to link the split').toBeVisible({timeout: UI_TIMEOUT});

    await page.getByTestId('import-wizard-import').click();
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 15_000});
    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(root, 30_000);
    return {root, parsed};
}

/** Never Save All: close the editor through its unsaved-changes guard and discard. */
async function closeEditorWithoutSaving(page: Page, root: Locator) {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: UI_TIMEOUT});
}

/** The catalogue's wording of `key` in the language the page is drawn in (`<html lang>`), never typed in the spec. */
async function catalogueWording(page: Page, key: string): Promise<string> {
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-i18n-ready', 'true');
    const lang = ((await html.getAttribute('lang')) ?? '').split('-')[0];
    const wording = catalogueText(lang, key);
    expect(wording, `the "${lang}" catalogue has no message for ${key}`).not.toBe(key);
    return wording;
}

/** The banner's one row, and the grid row it names: the row is found by the id it carries, never by position. */
async function splitBannerRow(root: Locator): Promise<{bannerRow: Locator; rowId: string; gridRow: Locator}> {
    const banner = root.getByTestId('tx-bulk-possible-split');
    await expect(banner, 'the editor lists the split in its own banner').toBeVisible({timeout: UI_TIMEOUT});
    const bannerRow = banner.getByTestId('possible-split-row');
    await expect(bannerRow, 'one row: the file holds one split').toHaveCount(1);
    const rowId = await bannerRow.getAttribute('data-row-id');
    expect(rowId, 'a banner row names the grid row it stands for').toBeTruthy();
    const gridRow = root.getByTestId('tx-bulk-body').locator(`tr[data-row-id="${rowId}"]`);
    await expect(gridRow, 'the grid has that row').toHaveCount(1, {timeout: UI_TIMEOUT});
    return {bannerRow, rowId: rowId!, gridRow};
}

/** The event column of a grid row shows an event: not the empty dash, but the event's glyph or, before its details load, its id. */
async function expectLinkedEvent(gridRow: Locator, eventId: number) {
    const cell = gridRow.locator('td[data-column-id="asset_event_id"]');
    await expect(cell, 'the event column of the row shows the linked event').toContainText(new RegExp(`✂|#${eventId}\\b`), {timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor — a possible stock split of an import (W-B87)', () => {
    let owned: Owned | undefined;

    test.beforeEach(async ({page}) => {
        owned = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page}) => {
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
    });

    test('SC1: «create the SPLIT event and link it» opens the mini modal on SPLIT; a ratio creates the event and links it to the row', async ({page}) => {
        owned = await createOwnedAsset(page);
        const {root} = await importIntoEditor(page, owned);

        // The row is in its own banner, and the generic «fields to verify» banner does not carry it.
        const {bannerRow, gridRow} = await splitBannerRow(root);
        await expect(root.getByTestId('tx-bulk-todo-warnings'), 'the split is not a generic field to verify').toHaveCount(0);

        // «Create»: the mini modal opens on SPLIT, whose amount is a ratio.
        await bannerRow.getByTestId('possible-split-create').click();
        const modal = page.getByTestId('event-create-mini-modal');
        await expect(modal).toBeVisible({timeout: 5_000});
        await expect(modal.getByTestId('event-create-type-button'), 'the modal starts on SPLIT').toContainText(await catalogueWording(page, 'assetDetail.eventType.SPLIT'));
        await expect(modal.getByTestId('event-create-ratio-hint'), 'a SPLIT amount is a ratio, and says so').toBeVisible();
        const ratio = modal.getByTestId('event-create-amount');
        await ratio.fill(SPLIT_RATIO);
        await expect(ratio).toHaveValue(SPLIT_RATIO);
        await ratio.blur();
        await expect(ratio, 'the blur keeps the ratio as typed, no 3.00').toHaveValue(SPLIT_RATIO);

        const upsert = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === `${API}/assets/events`, {timeout: 15_000});
        await modal.getByTestId('event-create-submit').click();
        const saved = (await (await upsert).json()) as {results: Array<{event_ids?: number[]}>};
        const eventId = saved.results[0]?.event_ids?.[0];
        expect(eventId, 'the create answered the id of the event it wrote').toBeGreaterThan(0);

        // The event is linked: the row leaves the banner, and its grid row shows the event.
        await expect(modal).toHaveCount(0, {timeout: 10_000});
        await expect(root.getByTestId('tx-bulk-possible-split'), 'the row left the banner').toHaveCount(0, {timeout: UI_TIMEOUT});
        await expectLinkedEvent(gridRow, eventId!);

        // And the event is a real SPLIT of the ratio typed, on the row's asset and day.
        const read = await page.request.get(`${API}/assets/events?ids=${eventId}`);
        expect(read.ok(), `read the event back: HTTP ${read.status()}`).toBe(true);
        const items = ((await read.json()) as {items: Array<{asset_id: number; events: Array<{id: number; type: string; date: string; value: {amount: string}}>}>}).items;
        const event = items.flatMap((item) => item.events).find((candidate) => candidate.id === eventId);
        expect(event, 'the event exists').toBeDefined();
        expect(event).toMatchObject({type: 'SPLIT', date: SPLIT_DATE});
        expect(Number(event!.value.amount), 'the ratio typed').toBe(Number(SPLIT_RATIO));
        expect(items.find((item) => item.events.some((candidate) => candidate.id === eventId))?.asset_id, 'on the asset the row was resolved to').toBe(owned.id);

        await closeEditorWithoutSaving(page, root);
    });

    test('SC2: «link an existing event» lists the asset events in an inline picker; the SPLIT created before is linked and the row leaves the banner', async ({page}) => {
        owned = await createOwnedAsset(page);
        // The event the user already has, on the asset and the day of the split: the picker offers it.
        const existingId = await createSplitEvent(page, owned.id, SPLIT_DATE, SPLIT_RATIO);
        const {root} = await importIntoEditor(page, owned);

        const {bannerRow, gridRow} = await splitBannerRow(root);
        await bannerRow.getByTestId('possible-split-link').click();
        const trigger = bannerRow.getByTestId('tx-form-event-picker-trigger');
        await expect(trigger, 'the picker opens inline, inside the banner row').toBeVisible({timeout: 5_000});
        await trigger.click();
        // The picker fetches its events debounced: until they arrive its only option is «no linked event» (marked by the ∅ glyph, which
        // no event option carries). Wait for the events themselves, not for "an option": that one would match the empty state too.
        const events = page.getByTestId('tx-form-event-picker-dropdown').getByRole('option').filter({hasNotText: '∅'});
        await expect(events, 'the asset is this test’s own: the one event it holds is the one on offer, once the fetch has landed').toHaveCount(1, {timeout: 10_000});
        await events.click();

        await expect(root.getByTestId('tx-bulk-possible-split'), 'the row left the banner').toHaveCount(0, {timeout: UI_TIMEOUT});
        await expectLinkedEvent(gridRow, existingId);

        await closeEditorWithoutSaving(page, root);
    });
});
