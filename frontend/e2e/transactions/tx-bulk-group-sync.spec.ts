/**
 * An all-new group keeps broker and asset in step inside the Bulk (lane 66, lot TL-3b, developer's rule).
 *
 * A group is a parent row and the linked charges under it. When every row of the group is new, a broker or an asset
 * changed in the Form of ANY of its rows («Apply») is written on the parent and on every charge; a group holding a saved
 * row is not synced (today's behaviour: the Bulk flags the charge that differs, «Save all» is refused). The Form of a row
 * of a synced group shows a help line under the broker field (`tx-form-group-sync-hint`).
 *
 *   (a) Page «Clona» on a BUY with a FEE and a TAX → an all-new group. The FEE copy's own Form: the help line is shown;
 *       its asset changed, applied → the BUY copy and the TAX copy take it; «Save all» passes, every new row on the
 *       other asset, each charge on its own date, the originals unchanged.
 *   (b) The consultant's case: a FEE born in the BUY copy's Form (charges section «add»), then its asset changed in its
 *       own Form → the BUY copy and the two other charge copies take it, and the FEE keeps it (today the change is lost:
 *       the row still follows its parent when its own Form is applied). «Save all» passes, four rows on the other asset.
 *   (c) Guard (mixed group): a new BUY with a saved FEE linked under it (picked in its Form). Its Form shows no help
 *       line; its asset changed → the saved FEE is not moved, the Bulk flags it (`chargeAssetMismatch`) and «Save all» is
 *       refused, nothing saved.
 *
 * testids relied on: transactions-page · tx-table · row-actions-* · context-menu-action-{clone,edit-single} ·
 * dt-row-checkbox-tx-<id> · toolbar-action-edit · tx-bulk-modal · tx-bulk-modal-root[data-busy] · tx-bulk-body ·
 * tx-bulk-row-label[data-charge-of] · tx-bulk-row-status[data-status] · tx-bulk-charge-state[data-state] ·
 * tx-bulk-charges-toggle-<rowId>[data-charges-count] · tx-bulk-add-row · tx-bulk-commit · tx-bulk-issues-header ·
 * tx-bulk-issue[data-code] · tx-form-modal · tx-form-cancel · tx-form-save · tx-form-type · tx-form-broker-wrap ·
 * tx-form-group-sync-hint · tx-form-asset(-trigger[data-disabled][aria-expanded]/-search) · search-select-option-<id> ·
 * tx-form-quantity · tx-form-cash-wrap · tx-form-optional-toggle · tx-form-description · tx-form-charges[data-state] ·
 * tx-form-charges-add-FEE · tx-form-charge-row[data-charge-key][data-charge-id] · tx-form-charge-cash-<key>-amount ·
 * tx-form-charge-note-<key> · tx-form-charges-link-existing · tx-picker-modal · tx-picker-add.
 * A saved Bulk row is found by the `#<id>` its ID cell shows; a new one by the description it carries (and, for a
 * copy, the status «new»). The grid shows no asset id: the verdict is the batch sent and the server, read back.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns, funded by its own DEPOSIT): every row
 * on that broker is the test's, so the afterEach deletes them all, then the account.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, emptyOwnedAccount, jsonFrom, readTransactions, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedBuyAndFreeFee, type ChargeTx, type CommitBody, type FundedAccount} from '../fixtures/linked-charges';

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// Seed: a BUY with a FEE and a TAX, each on a day of its own
// ---------------------------------------------------------------------------

type ChargeSpec = {key: 'fee' | 'tax'; type: 'FEE' | 'TAX'; amount: string; label: string; days: number};
type SeededCharge = ChargeSpec & {id: number; date: string; description: string};
type Seeded = FundedAccount & {buyId: number; buyDate: string; buyDescription: string; charges: Record<'fee' | 'tax', SeededCharge>; ids: number[]};

const TWO_CHARGES: ChargeSpec[] = [
    {key: 'fee', type: 'FEE', amount: '-5', label: 'Fee A', days: 4},
    {key: 'tax', type: 'TAX', amount: '-2', label: 'Tax', days: 3},
];
const BUY_DAYS = 6;

/** The seeded asset the group is moved to: same currency as the BUY's Ethereum, so only the asset differs. */
const OTHER_ASSET = {ticker: 'BTC-USD', search: 'Bitcoin'};

/** A funded account with a BUY and its FEE and TAX committed linked in one batch; the link and the dates read back. */
async function seedBuyWithCharges(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<Seeded> {
    const funded = await openFundedAccount(page, request, owned, [], tag, 'TL3b');
    const {broker, assetId, marker} = funded;
    const buyDate = daysAgoIso(BUY_DAYS);
    const buyDescription = `Buy ${marker}`;
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date: buyDate, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: buyDescription},
                    ...TWO_CHARGES.map((c) => ({broker_id: broker.id, asset_id: assetId, type: c.type, date: daysAgoIso(c.days), quantity: '0', cash: {code: 'USD', amount: c.amount}, description: `${c.label} ${marker}`, parent_ref: 'p'})),
                ],
            },
        }),
        'commit the BUY with its linked charges',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const buyId = idAt(0);
    const charges = {} as Record<'fee' | 'tax', SeededCharge>;
    TWO_CHARGES.forEach((c, at) => {
        charges[c.key] = {...c, id: idAt(at + 1), date: daysAgoIso(c.days), description: `${c.label} ${marker}`};
    });
    const ids = [funded.depositId, buyId, charges.fee.id, charges.tax.id];

    const back = await readByIds(page, ids);
    for (const c of Object.values(charges)) {
        expect(back.get(c.id)?.parent_transaction_id, `premise: ${c.label} is linked to the BUY`).toBe(buyId);
        expect(back.get(c.id)?.date, `premise: ${c.label} keeps its own date`).toBe(c.date);
    }
    const listed = new Set((await readTransactions(page, {broker_id: broker.id})).map((tx) => tx.id));
    expect(
        ids.filter((id) => !listed.has(id)),
        'premise: the broker listing returns every seeded row',
    ).toEqual([]);
    return {...funded, buyId, buyDate, buyDescription, charges, ids};
}

/** Every row on this broker, as the server has it now. */
async function brokerRows(page: Page, brokerId: number): Promise<ChargeTx[]> {
    return (await readTransactions(page, {broker_id: brokerId})) as unknown as ChargeTx[];
}

/** The rows of the test's broker that the seed did not write: what the Bulk saved. */
async function newRowsOnBroker(page: Page, brokerId: number, seededIds: readonly number[]): Promise<ChargeTx[]> {
    const seeded = new Set(seededIds);
    return (await brokerRows(page, brokerId)).filter((tx) => !seeded.has(tx.id));
}

/** The single row of `rows` with this type and description. */
function only(rows: ChargeTx[], type: string, description: string, dump: string): ChargeTx {
    const found = rows.filter((tx) => tx.type === type && tx.description === description);
    expect(found, `exactly one new ${type} «${description}»: ${dump}`).toHaveLength(1);
    return found[0];
}

/** The originals are as seeded: each charge on the BUY, on its own date, on the BUY's asset. */
async function expectOriginalsUnchanged(page: Page, s: Seeded): Promise<void> {
    const back = await readByIds(page, s.ids);
    for (const c of Object.values(s.charges)) {
        expect(back.get(c.id)?.parent_transaction_id, `the original ${c.label} still points at the original BUY`).toBe(s.buyId);
        expect(back.get(c.id)?.date).toBe(c.date);
    }
    expect(
        [s.buyId, s.charges.fee.id, s.charges.tax.id].map((id) => back.get(id)?.asset_id),
        'the originals keep their asset',
    ).toEqual([s.assetId, s.assetId, s.assetId]);
    expect(back.get(s.buyId)?.charges_count, 'the original BUY’s charges').toBe(2);
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

async function openTable(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** ⋮ on a table row → the action `actionId`. */
async function tableRowAction(page: Page, id: number, actionId: string): Promise<void> {
    const row = page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
    await expect(row).toBeVisible({timeout: 8_000});
    await row.hover();
    const kebab = row.getByTestId(/^row-actions-/);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: 5_000});
    await action.click();
}

/** «Clona» on the seeded BUY from the page: the Bulk opens with the BUY copy and its two charge copies under it; the
 *  Form a single clone opens on top is closed. Ends on the three copies in the grid. */
async function cloneBuy(page: Page, s: Seeded): Promise<{bulk: Locator; buyCopy: Locator; feeCopy: Locator; taxCopy: Locator}> {
    await openTable(page);
    await tableRowAction(page, s.buyId, 'clone');
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'a single row cloned opens its Form').toBeVisible({timeout: 8_000});
    await form.getByTestId('tx-form-cancel').click();
    await expect(form).toBeHidden({timeout: 8_000});

    const buyCopy = copyRows(bulk, s.buyDescription);
    await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
    const feeCopy = copyRows(bulk, s.charges.fee.description);
    const taxCopy = copyRows(bulk, s.charges.tax.description);
    await expectUnder(feeCopy, buyCopy, 'the FEE copy');
    await expectUnder(taxCopy, buyCopy, 'the TAX copy');
    return {bulk, buyCopy, feeCopy, taxCopy};
}

/** Tick these rows in the transactions table and «Edit»: the Bulk opens on them (several rows: no Form). */
async function editInBulk(page: Page, ids: number[]): Promise<Locator> {
    await navigateTo(page, `/transactions?id_min=${Math.min(...ids)}&id_max=${Math.max(...ids)}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    for (const id of ids) {
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    for (const id of ids) await expect(savedBulkRow(bulk, id), `premise: #${id} is a row of the Bulk`).toHaveCount(1, {timeout: 8_000});
    return bulk;
}

// ---------------------------------------------------------------------------
// The Bulk
// ---------------------------------------------------------------------------

/** The Bulk row of saved transaction `id`, by the `#id` its ID cell shows. */
function savedBulkRow(bulk: Locator, id: number): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** The Bulk rows carrying this description. */
function describedRows(bulk: Locator, description: string): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="description"]', {hasText: description})});
}

/** The new rows of the Bulk carrying this description. */
function copyRows(bulk: Locator, description: string): Locator {
    return describedRows(bulk, description).filter({has: bulk.page().locator('[data-testid="tx-bulk-row-status"][data-status="new"]')});
}

async function rowIdOf(row: Locator): Promise<string> {
    await expect(row).toHaveCount(1, {timeout: 10_000});
    const id = await row.getAttribute('data-row-id');
    if (!id) throw new Error('the Bulk row publishes no data-row-id');
    return id;
}

/** `row` sits under the parent row `parentRow`: its label names it. */
async function expectUnder(row: Locator, parentRow: Locator, what: string): Promise<void> {
    const parentId = await rowIdOf(parentRow);
    await expect(row, `${what}: one row`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is not under its parent`).toHaveAttribute('data-charge-of', parentId, {timeout: 10_000});
}

/** ⋮ on a Bulk row → the action `actionId`. */
async function bulkRowAction(bulk: Locator, row: Locator, actionId: string): Promise<void> {
    const rowId = await rowIdOf(row);
    await bulk.getByTestId(`row-actions-${rowId}`).click();
    const action = bulk.page().getByTestId(`context-menu-action-${actionId}`);
    await expect(action, `the row menu offers no «${actionId}»`).toBeVisible({timeout: 5_000});
    await action.click();
}

/** ⋮ → «Edit row» on a Bulk row: its Form, open on top of the Bulk, with its broker field on screen. */
async function openRowForm(bulk: Locator, row: Locator): Promise<Locator> {
    await bulkRowAction(bulk, row, 'edit-single');
    const form = bulk.page().getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-broker-wrap')).toBeVisible({timeout: 8_000});
    return form;
}

/** The Form's asset select, narrowed by name and picked by id; ends on the list closed. */
async function pickAsset(page: Page, form: Locator, assetId: number): Promise<void> {
    const trigger = form.getByTestId('tx-form-asset-trigger');
    await expect(trigger).toHaveAttribute('data-disabled', 'false', {timeout: 8_000});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const search = form.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: 5_000});
    await search.fill(OTHER_ASSET.search);
    const option = form.getByTestId('tx-form-asset').getByTestId(`search-select-option-${assetId}`);
    await expect(option).toBeVisible({timeout: 8_000});
    await option.click();
    await optionsClosed(page);
}

/** «Apply» in a Form open on top of the Bulk; ends on the Form closed. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
}

type SentRow = {id?: number; type?: string; description?: string; asset_id?: number | null; parent_transaction_id?: number; parent_ref?: string; ref?: string};
type Sent = {creates?: SentRow[]; updates?: SentRow[]};
type Answer = {committed?: boolean; issues?: Array<{operation?: string; index?: number; code?: string}>};

/** «Save all», the batch and the answer captured as they are: the caller asserts what was sent before whether it was
 *  saved, so a refusal reads as the field that broke it. */
async function saveCaptured(page: Page, bulk: Locator): Promise<{payload: Sent; body: Answer}> {
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const payload = (await requestPromise).postDataJSON() as Sent;
    const body = (await (await responsePromise).json()) as Answer;
    return {payload, body};
}

/** The one create of the batch with this type and description. */
function sentCreate(payload: Sent, type: string, description: string, dump: string): SentRow {
    const found = (payload.creates ?? []).filter((item) => item.type === type && item.description === description);
    expect(found, `the batch holds one ${type} «${description}»: ${dump}`).toHaveLength(1);
    return found[0];
}

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('Bulk — an all-new group keeps broker and asset in step (66 TL-3b)', () => {
    let owned = emptyOwnedAccount();
    let brokerId: number | null = null;

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        brokerId = null;
    });

    // afterEach, not `finally`: it runs after a timeout too. Every row on the test's own broker is the test's: deleted
    // together (a parent with its charges), then the account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (owned.user && brokerId !== null) {
                const left = (await brokerRows(page, brokerId)).map((tx) => tx.id);
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('(a) the asset changed in a charge copy’s Form: the BUY copy and the other charge copy take it; the help line is shown; saved on the other asset, each charge on its own date', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, 'tl3bs1');
        brokerId = s.broker.id;
        const {fee, tax} = s.charges;
        const otherAssetId = await seededAssetId(page, OTHER_ASSET.ticker);
        expect(otherAssetId, 'premise: the other asset is not the BUY’s').not.toBe(s.assetId);
        const {bulk, buyCopy, feeCopy, taxCopy} = await cloneBuy(page, s);

        const form = await openRowForm(bulk, feeCopy);
        // Soft: the sync below is the subject; the line is checked here, while the Form is open, without stopping it.
        await expect.soft(form.getByTestId('tx-form-group-sync-hint'), 'a row of an all-new group shows the help line').toBeVisible({timeout: 5_000});
        await pickAsset(page, form, otherAssetId);
        await applyForm(form);

        // The structure is kept: both charge copies still under the BUY copy, linked.
        await expectUnder(feeCopy, buyCopy, 'the FEE copy');
        await expectUnder(taxCopy, buyCopy, 'the TAX copy');
        await expect(taxCopy.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'linked');

        const {payload, body} = await saveCaptured(page, bulk);
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(body)}`;
        expect(payload.creates, dump).toHaveLength(3);
        const [buySent, feeSent, taxSent] = [sentCreate(payload, 'BUY', s.buyDescription, dump), sentCreate(payload, 'FEE', fee.description, dump), sentCreate(payload, 'TAX', tax.description, dump)];
        expect([buySent.asset_id, feeSent.asset_id, taxSent.asset_id], `the whole group is sent with the asset set on the FEE copy: ${dump}`).toEqual([otherAssetId, otherAssetId, otherAssetId]);
        expect([feeSent.parent_ref, taxSent.parent_ref], `the charge copies are sent under the BUY copy: ${dump}`).toEqual([buySent.ref, buySent.ref]);
        expect(body.committed, `the batch was refused: ${dump}`).toBe(true);
        await expect(bulk).toBeHidden({timeout: 10_000});

        const fresh = await newRowsOnBroker(page, s.broker.id, s.ids);
        const rowsDump = `new rows ${JSON.stringify(fresh)} — ${dump}`;
        expect(fresh, rowsDump).toHaveLength(3);
        const newBuy = only(fresh, 'BUY', s.buyDescription, rowsDump);
        const newFee = only(fresh, 'FEE', fee.description, rowsDump);
        const newTax = only(fresh, 'TAX', tax.description, rowsDump);
        expect([newBuy.asset_id, newFee.asset_id, newTax.asset_id], rowsDump).toEqual([otherAssetId, otherAssetId, otherAssetId]);
        expect([newFee.parent_transaction_id, newTax.parent_transaction_id], rowsDump).toEqual([newBuy.id, newBuy.id]);
        expect([newBuy.date, newFee.date, newTax.date], 'the date never syncs: every copy on its original’s date').toEqual([s.buyDate, fee.date, tax.date]);
        await expectOriginalsUnchanged(page, s);
    });

    test('(b) a FEE born in the BUY copy’s Form, its asset then changed in its own Form: the FEE keeps it and the BUY copy and both charge copies take it; saved on the other asset', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, 'tl3bs2');
        brokerId = s.broker.id;
        const {fee, tax} = s.charges;
        const otherAssetId = await seededAssetId(page, OTHER_ASSET.ticker);
        expect(otherAssetId, 'premise: the other asset is not the BUY’s').not.toBe(s.assetId);
        const {bulk, buyCopy} = await cloneBuy(page, s);
        const addedDescription = `Added ${s.marker}`;

        // The BUY copy's Form: a new FEE added in its charges section, with an amount and a note.
        const parentForm = await openRowForm(bulk, buyCopy);
        const section = parentForm.getByTestId('tx-form-charges');
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        const chargeRows = section.getByTestId('tx-form-charge-row');
        await expect(chargeRows, 'premise: the Form lists the two charge copies').toHaveCount(2);
        const keysBefore = await chargeRows.evaluateAll((rows) => rows.map((row) => row.getAttribute('data-charge-key')));
        await section.getByTestId('tx-form-charges-add-FEE').click();
        await expect(chargeRows, 'the FEE this test added').toHaveCount(3);
        const keysAfter = await chargeRows.evaluateAll((rows) => rows.map((row) => row.getAttribute('data-charge-key')));
        const addedKeys = keysAfter.filter((key) => !keysBefore.includes(key));
        expect(addedKeys, 'one new key: the FEE added').toHaveLength(1);
        const added = section.locator(`[data-testid="tx-form-charge-row"][data-charge-key="${addedKeys[0]}"]`);
        const amount = added.locator('input[data-testid^="tx-form-charge-cash-"][data-testid$="-amount"]');
        await amount.fill('3');
        await amount.blur();
        await expect(amount).not.toHaveValue('');
        const note = added.locator('input[data-testid^="tx-form-charge-note-"]');
        await note.fill(addedDescription);
        await expect(note).toHaveValue(addedDescription);
        await applyForm(parentForm);

        const addedRow = copyRows(bulk, addedDescription);
        await expectUnder(addedRow, buyCopy, 'the FEE added in the parent’s Form');

        // Its own Form: the asset changed, applied.
        const form = await openRowForm(bulk, addedRow);
        await expect.soft(form.getByTestId('tx-form-group-sync-hint'), 'a row of an all-new group shows the help line').toBeVisible({timeout: 5_000});
        await pickAsset(page, form, otherAssetId);
        await applyForm(form);
        await expectUnder(addedRow, buyCopy, 'the FEE added, after its own Form');

        const {payload, body} = await saveCaptured(page, bulk);
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(body)}`;
        expect(payload.creates, dump).toHaveLength(4);
        const sent = [sentCreate(payload, 'FEE', addedDescription, dump), sentCreate(payload, 'BUY', s.buyDescription, dump), sentCreate(payload, 'FEE', fee.description, dump), sentCreate(payload, 'TAX', tax.description, dump)];
        expect(
            sent.map((row) => row.asset_id),
            `the FEE added keeps the asset of its own Form, and the BUY copy and both charge copies take it: ${dump}`,
        ).toEqual([otherAssetId, otherAssetId, otherAssetId, otherAssetId]);
        expect(body.committed, `the batch was refused: ${dump}`).toBe(true);
        await expect(bulk).toBeHidden({timeout: 10_000});

        const fresh = await newRowsOnBroker(page, s.broker.id, s.ids);
        const rowsDump = `new rows ${JSON.stringify(fresh)} — ${dump}`;
        expect(fresh, rowsDump).toHaveLength(4);
        const newBuy = only(fresh, 'BUY', s.buyDescription, rowsDump);
        const newAdded = only(fresh, 'FEE', addedDescription, rowsDump);
        expect(
            fresh.map((tx) => tx.asset_id),
            rowsDump,
        ).toEqual(fresh.map(() => otherAssetId));
        expect(newAdded.parent_transaction_id, `the FEE added points at the new BUY: ${rowsDump}`).toBe(newBuy.id);
        await expectOriginalsUnchanged(page, s);
    });

    test('(c) guard, mixed group: a new BUY with a saved FEE linked under it — no help line; the BUY’s asset changed does not move the saved FEE, flagged, «Save all» refused', async ({page, request}) => {
        const s = await seedBuyAndFreeFee(page, request, owned, [], 'tl3bs3', 'TL3b');
        brokerId = s.broker.id;
        const seededIds = [s.depositId, s.buyId, s.feeId];
        const otherAssetId = await seededAssetId(page, OTHER_ASSET.ticker);
        expect(otherAssetId, 'premise: the other asset is not the seed’s').not.toBe(s.assetId);
        const bulk = await editInBulk(page, [s.buyId, s.feeId]);
        const newDescription = `NewBuy ${s.marker}`;

        // A new BUY row, on the seed's broker and asset.
        await bulk.getByTestId('tx-bulk-add-row').click();
        const addForm = page.getByTestId('tx-form-modal');
        await expect(addForm).toBeVisible({timeout: 8_000});
        await pickOption(page, addForm.getByTestId('tx-form-type'), 'BUY');
        await pickOption(page, addForm.getByTestId('tx-form-broker-wrap').getByRole('combobox'), s.broker.id);
        await expect(addForm.getByTestId('tx-form-broker-wrap')).toContainText(s.broker.name);
        await addForm.getByTestId('tx-form-asset-trigger').click();
        const assetSearch = addForm.getByTestId('tx-form-asset-search');
        await expect(assetSearch).toBeVisible({timeout: 5_000});
        await assetSearch.fill('Ethereum');
        const assetOption = addForm.getByTestId('tx-form-asset').getByTestId(`search-select-option-${s.assetId}`);
        await expect(assetOption).toBeVisible({timeout: 8_000});
        await assetOption.click();
        await optionsClosed(page);
        const quantity = addForm.getByTestId('tx-form-quantity');
        await quantity.fill('5');
        await quantity.blur();
        await expect(quantity).not.toHaveValue('');
        const cash = addForm.getByTestId('tx-form-cash-wrap').locator('input[data-testid$="-amount"]');
        await cash.fill('50');
        await cash.blur();
        await expect(cash).not.toHaveValue('');
        await fillDescription(addForm, newDescription);
        await applyForm(addForm);
        const newBuy = copyRows(bulk, newDescription);
        await expect(newBuy).toHaveCount(1, {timeout: 8_000});

        // Its Form: the saved FEE picked from «Link an existing charge…».
        const linkForm = await openRowForm(bulk, newBuy);
        await expect(linkForm.getByTestId('tx-form-charges')).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        await linkForm.getByTestId('tx-form-charges-link-existing').click();
        const picker = page.getByTestId('tx-picker-modal');
        await expect(picker).toBeVisible({timeout: 8_000});
        const pickRow = picker.locator(`tr[data-row-id="tx-${s.feeId}"]`);
        await expect(pickRow, 'the saved free FEE is offered').toHaveCount(1, {timeout: 8_000});
        const box = pickRow.locator('[data-testid^="dt-row-checkbox-tx-"]');
        if ((await box.getAttribute('data-state')) !== 'checked') await box.click();
        await expect(box).toHaveAttribute('data-state', 'checked');
        await picker.getByTestId('tx-picker-add').click();
        await expect(picker).toBeHidden({timeout: 8_000});
        await expect(linkForm.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`)).toHaveCount(1);
        await applyForm(linkForm);
        await expectUnder(savedBulkRow(bulk, s.feeId), newBuy, 'the saved FEE');

        // The mixed group: no help line in the new BUY's Form (its broker field is the presence barrier).
        const form = await openRowForm(bulk, newBuy);
        await expect(form.getByTestId('tx-form-group-sync-hint'), 'a group holding a saved row is not synced: no help line').toBeHidden();
        await pickAsset(page, form, otherAssetId);
        await applyForm(form);

        // Not synced: the saved FEE keeps its asset; the Bulk flags it.
        const header = bulk.getByTestId('tx-bulk-issues-header');
        await expect(header, 'the pre-save warning is shown').toBeVisible({timeout: 20_000});
        await expect(header.locator('[data-testid="tx-bulk-issue"][data-code="chargeAssetMismatch"]'), 'the asset rule').toHaveCount(1, {timeout: 20_000});

        const {payload, body} = await saveCaptured(page, bulk);
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(body)}`;
        expect(sentCreate(payload, 'BUY', newDescription, dump).asset_id, `the new BUY is sent with the other asset: ${dump}`).toBe(otherAssetId);
        const feeUpdate = (payload.updates ?? []).find((item) => item.id === s.feeId);
        expect(feeUpdate, `the saved FEE is sent (its new parent): ${dump}`).toBeDefined();
        expect(feeUpdate?.asset_id ?? s.assetId, `the saved FEE is not moved to the other asset: ${dump}`).toBe(s.assetId);
        expect(body.committed, `a charge off its parent’s asset is refused: ${dump}`).toBe(false);
        expect(
            (body.issues ?? []).map((issue) => issue.code),
            dump,
        ).toContain('chargeAssetMismatch');

        // Nothing saved: no new row, the FEE as seeded.
        expect(await newRowsOnBroker(page, s.broker.id, seededIds), dump).toEqual([]);
        const back = await readByIds(page, [s.feeId]);
        expect([back.get(s.feeId)?.asset_id, back.get(s.feeId)?.parent_transaction_id ?? null], dump).toEqual([s.assetId, null]);
    });
});

// ---------------------------------------------------------------------------
// The Form of a new row
// ---------------------------------------------------------------------------

/** Pick the option `value` in the select opened by `trigger`, and prove the list is gone (option testids are shared). */
async function pickOption(page: Page, trigger: Locator, value: string | number): Promise<void> {
    await expect(trigger).toBeVisible({timeout: 5_000});
    await trigger.click();
    const option = page.getByTestId(`search-select-option-${value}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionsClosed(page);
}

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(form: Locator, text: string): Promise<void> {
    const details = form.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: 5_000});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await form.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = form.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}
