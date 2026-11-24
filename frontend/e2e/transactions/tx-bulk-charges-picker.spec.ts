/**
 * «Link an existing charge…» of a parent's form inside the Bulk sees the Bulk's rows (lane 66, lot TL-2, FEE consultant).
 *
 * Today the picker reads only the database (`GET /transactions?without_parent=true&broker_id=…`): a new charge of the
 * Bulk, not saved yet, cannot appear, and a saved charge unlinked or deleted in the Bulk is offered as the database has
 * it. Inside the Bulk the candidates are read on the Bulk's current state (`bulkChargeCandidates`):
 *
 *   (1) a new BUY and a new free FEE (same broker and asset), both rows of the Bulk: the BUY's form offers the FEE, its
 *       ID cell naming it by its row reference (no `#`); picked → Apply → the FEE sits under the BUY, the group open,
 *       still one FEE row; «Save all» → on the server the FEE's parent is the new BUY (exactly one FEE created).
 *   (2) the FEE a row, the BUY still in its first «Add transaction» form (never applied): the picker offers the FEE;
 *       picked → Apply → the FEE goes under the new BUY row.
 *   (3) a saved free FEE marked «del» in the Bulk is not offered; a saved FEE unlinked here («scollega» in its parent's
 *       form) is, and picked under another BUY saves with the new parent.
 *   (4) guard (green today): a saved free FEE that is not a row of the Bulk is offered (the database path), and a saved
 *       free FEE that is also a row of the Bulk is offered once.
 *   (5) a saved BUY P1 with a saved linked FEE, deleted in the Bulk with «Keep the charges» (the FEE stays under P1,
 *       unlinked, `byParentChoice`): another saved BUY P2 (same broker and asset) is offered the FEE; picked, Apply → the
 *       FEE under P2; «Save all» → on the server P1 is gone, the FEE's parent is P2, the TAX stays with no parent.
 *
 * testids relied on: tx-add-button · tx-bulk-modal · tx-bulk-modal-root · tx-bulk-body · tx-bulk-add-row ·
 * tx-bulk-row-label[data-charge-of] · tx-bulk-row-status[data-status] · tx-bulk-charge-state[data-state] ·
 * tx-bulk-charges-toggle-<rowId>[aria-expanded][data-charges-count] · row-actions-<rowId> ·
 * context-menu-action-{edit-single,mark-delete} · tx-charges-modal-content[data-mode] · tx-charges-modal-keep ·
 * tx-bulk-commit · tx-form-modal · tx-form-type · tx-form-broker-wrap · tx-form-asset-trigger · tx-form-asset-search ·
 * search-select-option-<value> · tx-form-quantity · tx-form-cash-wrap · tx-form-optional-toggle · tx-form-description ·
 * tx-form-charges[data-state] · tx-form-charges-link-existing · tx-form-charge-row[data-charge-id][data-charge-key] ·
 * tx-form-charge-unlink-<key> · tx-form-save · tx-form-cancel · tx-picker-modal · tx-picker-add · tx-picker-cancel ·
 * dt-row-checkbox-tx-<id> · tx-table · toolbar-action-edit · transactions-page.
 * The picker's table names its rows `tx-<id>` (`tr[data-row-id]`); a new row of the Bulk is offered under a synthetic
 * negative id, so `tr[data-row-id^="tx--"]` are the Bulk's new rows (the Bulk holds only this test's rows). A saved Bulk
 * row is found by the `#<id>` its ID cell shows, a new one by the description this test typed. The verdict is the
 * server, read back by id.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedBuyAndFreeFee, seedLinkedBuy, type CommitBody} from '../fixtures/linked-charges';

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// The Bulk
// ---------------------------------------------------------------------------

/** The Bulk row of saved transaction `id`, found by the `#id` its ID cell shows. */
function savedBulkRow(page: Page, id: number): Locator {
    return page
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** The Bulk row of a new transaction, found by the description this test typed. */
function newBulkRow(page: Page, description: string): Locator {
    return page
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="description"]', {hasText: description})});
}

async function rowIdOf(row: Locator): Promise<string> {
    await expect(row).toHaveCount(1, {timeout: 10_000});
    const id = await row.getAttribute('data-row-id');
    if (!id) throw new Error('the Bulk row publishes no data-row-id');
    return id;
}

/** ⋮ on a Bulk row → the action `actionId`. */
async function bulkRowAction(page: Page, row: Locator, actionId: string): Promise<void> {
    const rowId = await rowIdOf(row);
    await page.getByTestId('tx-bulk-modal').getByTestId(`row-actions-${rowId}`).click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action, `the row menu offers no «${actionId}»`).toBeVisible({timeout: 5_000});
    await action.click();
}

/** `row` sits under the parent row `parentRow` (its label names it) and is the only row of its kind. */
async function expectUnder(row: Locator, parentRow: Locator, what: string): Promise<void> {
    const parentId = await rowIdOf(parentRow);
    await expect(row, `${what}: one row, never a second copy`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is not under its parent`).toHaveAttribute('data-charge-of', parentId, {timeout: 10_000});
    await expect(pageOf(row).getByTestId(`tx-bulk-charges-toggle-${parentId}`), `${what}: the parent's group is open`).toHaveAttribute('aria-expanded', 'true');
}

const pageOf = (locator: Locator): Page => locator.page();

/** «Save all»; the commit must succeed and the Bulk close. */
async function saveAll(p: Page): Promise<{body: CommitBody; payload: unknown}> {
    const bulk = p.getByTestId('tx-bulk-modal');
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = p.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = p.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const payload = (await requestPromise).postDataJSON() as unknown;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(payload)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return {body, payload};
}

/** Tick these rows in the transactions table and «Edit»: the Bulk opens on them (several rows: no form). */
async function editInBulk(p: Page, ids: number[]): Promise<void> {
    await navigateTo(p, `/transactions?id_min=${Math.min(...ids)}&id_max=${Math.max(...ids)}`);
    await waitForSettled(p.getByTestId('transactions-page'), 20_000);
    for (const id of ids) {
        const checkbox = p.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const edit = p.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    const bulk = p.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    for (const id of ids) await expect(savedBulkRow(p, id), `premise: #${id} is a row of the Bulk`).toHaveCount(1, {timeout: 8_000});
}

// ---------------------------------------------------------------------------
// The form
// ---------------------------------------------------------------------------

/** Pick the option `value` in the select opened by `trigger`, and prove the list is gone (option testids are shared). */
async function pickOption(p: Page, trigger: Locator, value: string | number): Promise<void> {
    await expect(trigger).toBeVisible({timeout: 5_000});
    await trigger.click();
    const option = p.getByTestId(`search-select-option-${value}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionsClosed(p);
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

type NewRow = {type: 'BUY' | 'FEE'; brokerId: number; brokerName: string; assetId: number; quantity?: string; cash: string; description: string};

/** Fill the open form with a new row; ends on «Apply» enabled, the form still open. */
async function fillRow(p: Page, row: NewRow): Promise<Locator> {
    const form = p.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await pickOption(p, form.getByTestId('tx-form-type'), row.type);
    await pickOption(p, form.getByTestId('tx-form-broker-wrap').getByRole('combobox'), row.brokerId);
    await expect(form.getByTestId('tx-form-broker-wrap')).toContainText(row.brokerName);
    await expect(form.getByTestId('tx-form-asset-trigger')).toBeVisible({timeout: 5_000});
    await form.getByTestId('tx-form-asset-trigger').click();
    const assetSearch = p.getByTestId('tx-form-asset-search');
    await expect(assetSearch).toBeVisible({timeout: 5_000});
    await assetSearch.fill('Ethereum');
    const assetOption = p.getByTestId(`search-select-option-${row.assetId}`);
    await expect(assetOption).toBeVisible({timeout: 8_000});
    await assetOption.click();
    await optionsClosed(p);
    if (row.quantity !== undefined) {
        const quantity = form.getByTestId('tx-form-quantity');
        await quantity.fill(row.quantity);
        await quantity.blur();
        await expect(quantity).not.toHaveValue('');
    }
    const cash = form.getByTestId('tx-form-cash-wrap').locator('input[data-testid$="-amount"]');
    await expect(cash).toBeVisible({timeout: 5_000});
    await cash.fill(row.cash);
    await cash.blur();
    await expect(cash).not.toHaveValue('');
    await fillDescription(form, row.description);
    await expect(form.getByTestId('tx-form-save'), `the ${row.type} form is not complete`).toBeEnabled({timeout: 8_000});
    return form;
}

/** «Apply» in a form open on top of the Bulk; ends on the form closed. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
}

/** Fill the open form with a new row and «Apply» it into the Bulk; ends on the row in the grid. */
async function writeRow(p: Page, row: NewRow): Promise<void> {
    await applyForm(await fillRow(p, row));
    await expect(newBulkRow(p, row.description)).toHaveCount(1, {timeout: 8_000});
}

/** ⋮ → «Edit row» on a Bulk parent: its form, with its charges section ready. */
async function openParentForm(p: Page, row: Locator): Promise<Locator> {
    await bulkRowAction(p, row, 'edit-single');
    const form = p.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-charges')).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
    return form;
}

// ---------------------------------------------------------------------------
// The picker
// ---------------------------------------------------------------------------

/** «Link an existing charge…» in the form → the picker open. */
async function openChargesPicker(form: Locator): Promise<Locator> {
    const link = form.getByTestId('tx-form-charges-link-existing');
    await expect(link, 'the parent’s form offers «Link an existing charge…»').toBeVisible({timeout: 8_000});
    await link.click();
    const picker = pageOf(form).getByTestId('tx-picker-modal');
    await expect(picker).toBeVisible({timeout: 8_000});
    return picker;
}

/** The picker's row of transaction `id` (saved). */
function pickerRow(picker: Locator, id: number): Locator {
    return picker.locator(`tr[data-row-id="tx-${id}"]`);
}

/** The picker's rows that are new rows of the Bulk (a synthetic negative id). */
function pickerNewRows(picker: Locator): Locator {
    return picker.locator('tr[data-row-id^="tx--"]');
}

/** Tick one picker row, «Add»; ends on the picker closed. */
async function pickAndAdd(picker: Locator, row: Locator): Promise<void> {
    await expect(row).toHaveCount(1, {timeout: 8_000});
    const box = row.locator('[data-testid^="dt-row-checkbox-tx-"]');
    await expect(box).toBeVisible({timeout: 5_000});
    if ((await box.getAttribute('data-state')) !== 'checked') await box.click();
    await expect(box).toHaveAttribute('data-state', 'checked');
    const add = picker.getByTestId('tx-picker-add');
    await expect(add).toBeEnabled({timeout: 5_000});
    await add.click();
    await expect(picker).toBeHidden({timeout: 8_000});
}

/** The section's rows that are new charges (no saved id). */
function newChargeRows(form: Locator): Locator {
    return form.locator('[data-testid="tx-form-charge-row"][data-charge-id=""]');
}

// ---------------------------------------------------------------------------

test.describe('Bulk — the charges picker of a parent’s form sees the Bulk’s rows (66 TL-2)', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together, then the
    // account and its brokers.
    test.afterEach(async ({page: p, request}) => {
        try {
            if (owned.user && committedIds.length > 0) {
                const left = [...(await readByIds(p, committedIds)).keys()];
                if (left.length > 0) await p.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(p, request, owned);
        }
    });

    test('(1) a new FEE row of the Bulk is offered in a new BUY’s form by its row reference; picked, it goes under the BUY and saves linked', async ({page: p, request}) => {
        const {broker, assetId, marker} = await openFundedAccount(p, request, owned, committedIds, 'chgp1', 'ChgP');
        await navigateTo(p, '/transactions');
        await waitForSettled(p.getByTestId('transactions-page'), 20_000);
        await p.getByTestId('tx-add-button').click();
        await expect(p.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});

        await writeRow(p, {type: 'BUY', brokerId: broker.id, brokerName: broker.name, assetId, quantity: '10', cash: '100', description: `Buy ${marker}`});
        await p.getByTestId('tx-bulk-add-row').click();
        await writeRow(p, {type: 'FEE', brokerId: broker.id, brokerName: broker.name, assetId, cash: '5', description: `Fee ${marker}`});
        const feeLabel = newBulkRow(p, `Fee ${marker}`).getByTestId('tx-bulk-row-label');
        await expect(feeLabel, 'premise: the FEE is a row of its own').not.toHaveAttribute('data-charge-of', /.+/);
        await expect(feeLabel).toHaveText(/\d/);
        const feeRef = ((await feeLabel.textContent()) ?? '').trim();

        const form = await openParentForm(p, newBulkRow(p, `Buy ${marker}`));
        const picker = await openChargesPicker(form);

        // TL-2: the Bulk's new FEE is offered, named by its row reference, never as `#<id>`.
        const offered = pickerNewRows(picker);
        await expect(offered, 'the picker offers the Bulk’s new FEE').toHaveCount(1, {timeout: 8_000});
        const idCell = offered.locator('td[data-column-id="id"]');
        await expect(idCell).toContainText(feeRef);
        await expect(idCell).not.toContainText('#');

        await pickAndAdd(picker, offered);
        await expect(newChargeRows(form), 'the FEE joins the section as the Bulk’s row').toHaveCount(1);
        await applyForm(form);

        await expectUnder(newBulkRow(p, `Fee ${marker}`), newBulkRow(p, `Buy ${marker}`), 'the FEE');

        const {body, payload} = await saveAll(p);
        const createdIds = (body.results ?? []).filter((r) => r.operation === 'create').flatMap((r) => r.ids ?? []);
        committedIds.push(...createdIds);
        const created = [...(await readByIds(p, createdIds)).values()];
        const dump = `created ${JSON.stringify(created)} — payload ${JSON.stringify(payload)}`;
        const buys = created.filter((tx) => tx.type === 'BUY');
        const fees = created.filter((tx) => tx.type === 'FEE');
        expect(buys, `one BUY: ${dump}`).toHaveLength(1);
        expect(fees, `one FEE, never a copy: ${dump}`).toHaveLength(1);
        expect(fees[0].parent_transaction_id, `the FEE points at the BUY: ${dump}`).toBe(buys[0].id);
    });

    test('(2) a new BUY still in its first form (never applied) is offered the Bulk’s FEE; picked, the FEE goes under the new BUY row', async ({page: p, request}) => {
        const {broker, assetId, marker} = await openFundedAccount(p, request, owned, committedIds, 'chgp2', 'ChgP');
        await navigateTo(p, '/transactions');
        await waitForSettled(p.getByTestId('transactions-page'), 20_000);
        await p.getByTestId('tx-add-button').click();
        await expect(p.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});

        await writeRow(p, {type: 'FEE', brokerId: broker.id, brokerName: broker.name, assetId, cash: '5', description: `Fee ${marker}`});
        await p.getByTestId('tx-bulk-add-row').click();
        const form = await fillRow(p, {type: 'BUY', brokerId: broker.id, brokerName: broker.name, assetId, quantity: '10', cash: '100', description: `Buy ${marker}`});
        await expect(newBulkRow(p, `Buy ${marker}`), 'premise: the BUY is not a row yet').toHaveCount(0);

        const picker = await openChargesPicker(form);
        const offered = pickerNewRows(picker);
        await expect(offered, 'the picker of a BUY being created offers the Bulk’s new FEE').toHaveCount(1, {timeout: 8_000});

        await pickAndAdd(picker, offered);
        await expect(newChargeRows(form)).toHaveCount(1);
        await applyForm(form);

        await expect(newBulkRow(p, `Buy ${marker}`)).toHaveCount(1, {timeout: 8_000});
        await expectUnder(newBulkRow(p, `Fee ${marker}`), newBulkRow(p, `Buy ${marker}`), 'the FEE');
    });

    test('(3) a saved FEE «del» in the Bulk is not offered; a saved FEE unlinked here is, and picked under another BUY saves with it', async ({page: p, request}) => {
        const s = await seedLinkedBuy(p, request, owned, committedIds, 'chgp3', 'ChgP');
        const date = daysAgoIso(5);
        const [buy2Id, feeDelId, feeOkId] = await commitCreates(
            p,
            [
                {broker_id: s.broker.id, asset_id: s.assetId, type: 'BUY', date, quantity: '5', cash: {code: 'USD', amount: '-50'}, description: `Buy2 ${s.marker}`},
                {broker_id: s.broker.id, asset_id: s.assetId, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-3'}, description: `FeeDel ${s.marker}`},
                {broker_id: s.broker.id, asset_id: s.assetId, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-4'}, description: `FeeOk ${s.marker}`},
            ],
            'commit a second BUY and two free FEEs',
        );
        committedIds.push(buy2Id, feeDelId, feeOkId);

        await editInBulk(p, [s.buyId, buy2Id, feeDelId]);

        // «del» on the free FEE.
        await bulkRowAction(p, savedBulkRow(p, feeDelId), 'mark-delete');
        await expect(savedBulkRow(p, feeDelId).getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'delete', {timeout: 5_000});

        // «scollega» of the linked FEE in its BUY's form.
        const form1 = await openParentForm(p, savedBulkRow(p, s.buyId));
        const feeChip = form1.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`);
        const unlink = feeChip.locator('[data-testid^="tx-form-charge-unlink-"]');
        await expect(unlink).toBeVisible({timeout: 8_000});
        await unlink.click();
        await expect(feeChip).toHaveCount(0);
        await applyForm(form1);
        await expect(savedBulkRow(p, s.feeId).getByTestId('tx-bulk-charge-state'), 'premise: the FEE is unlinked here').toHaveAttribute('data-state', 'unlink', {timeout: 8_000});

        // The other BUY's picker.
        const form2 = await openParentForm(p, savedBulkRow(p, buy2Id));
        const picker = await openChargesPicker(form2);
        await expect(pickerRow(picker, feeOkId), 'barrier: the free FEE outside the Bulk is offered').toHaveCount(1, {timeout: 8_000});
        await expect(pickerRow(picker, s.feeId), 'the FEE unlinked here is offered').toHaveCount(1);
        await expect(pickerRow(picker, feeDelId), 'the FEE marked «del» here is not offered').toHaveCount(0);
        await expect(pickerRow(picker, s.taxId), 'the TAX still linked to its BUY is not offered').toHaveCount(0);

        await pickAndAdd(picker, pickerRow(picker, s.feeId));
        await expect(form2.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`)).toHaveCount(1);
        await applyForm(form2);
        await expectUnder(savedBulkRow(p, s.feeId), savedBulkRow(p, buy2Id), 'the unlinked FEE');

        const {payload} = await saveAll(p);
        const after = await readByIds(p, [s.buyId, s.feeId, s.taxId, buy2Id, feeDelId, feeOkId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE points at the second BUY: ${dump}`).toBe(buy2Id);
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX stays on its BUY: ${dump}`).toBe(s.buyId);
        expect(after.has(feeDelId), `the FEE marked «del» is deleted: ${dump}`).toBe(false);
        expect(after.get(feeOkId)?.parent_transaction_id ?? null, `the free FEE outside the Bulk is untouched: ${dump}`).toBeNull();
    });

    test('(4) guard: a saved free FEE outside the Bulk is offered, and one that is also a Bulk row is offered once', async ({page: p, request}) => {
        const s = await seedBuyAndFreeFee(p, request, owned, committedIds, 'chgp4', 'ChgP');
        const [fee2Id] = await commitCreates(p, [{broker_id: s.broker.id, asset_id: s.assetId, type: 'FEE', date: daysAgoIso(5), quantity: '0', cash: {code: 'USD', amount: '-2'}, description: `Fee2 ${s.marker}`}], 'commit a second free FEE');
        committedIds.push(fee2Id);

        await editInBulk(p, [s.buyId, fee2Id]);
        await expect(savedBulkRow(p, s.feeId), 'premise: the first FEE is not a row of the Bulk').toHaveCount(0);

        const form = await openParentForm(p, savedBulkRow(p, s.buyId));
        const picker = await openChargesPicker(form);
        await expect(pickerRow(picker, s.feeId), 'the free FEE outside the Bulk is offered (database)').toHaveCount(1, {timeout: 8_000});
        await expect(pickerRow(picker, fee2Id), 'the free FEE that is also a Bulk row is offered once').toHaveCount(1);
        await expect(pickerRow(picker, s.feeId).locator('td[data-column-id="id"]'), 'the picker’s ID cell names a saved row #id').toContainText(`#${s.feeId}`);
        await expect(pickerRow(picker, fee2Id).locator('td[data-column-id="id"]')).toContainText(`#${fee2Id}`);

        await picker.getByTestId('tx-picker-cancel').click();
        await expect(picker).toBeHidden({timeout: 5_000});
    });

    test('(5) a FEE kept under its BUY «del» («Keep the charges») is offered in another BUY’s form; picked, it saves under that BUY', async ({page: p, request}) => {
        const s = await seedLinkedBuy(p, request, owned, committedIds, 'chgp5', 'ChgP');
        const [buy2Id] = await commitCreates(p, [{broker_id: s.broker.id, asset_id: s.assetId, type: 'BUY', date: daysAgoIso(5), quantity: '5', cash: {code: 'USD', amount: '-50'}, description: `Buy2 ${s.marker}`}], 'commit a second BUY');
        committedIds.push(buy2Id);

        await editInBulk(p, [s.buyId, buy2Id]);
        const bulk = p.getByTestId('tx-bulk-modal');
        const p1Row = savedBulkRow(p, s.buyId);
        const p1RowId = await rowIdOf(p1Row);
        // «Delete» on a parent waits for its charges to be read: the menu would refuse in silence before.
        await expect(bulk.getByTestId(`tx-bulk-charges-toggle-${p1RowId}`), 'premise: P1’s two charges are read').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
        await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);

        // P1 «del», «Keep the charges».
        await bulkRowAction(p, p1Row, 'mark-delete');
        const panel = p.getByTestId('tx-charges-modal-content');
        await expect(panel, '«Delete» on a parent with charges opened no panel').toBeVisible({timeout: 8_000});
        await expect(panel).toHaveAttribute('data-mode', 'deleteParent');
        await panel.getByTestId('tx-charges-modal-keep').click();
        await expect(panel).toBeHidden({timeout: 5_000});
        await expect(p1Row.getByTestId('tx-bulk-row-status'), 'premise: P1 is «del»').toHaveAttribute('data-status', 'delete', {timeout: 5_000});
        await expect(savedBulkRow(p, s.feeId).getByTestId('tx-bulk-charge-state'), 'premise: the FEE stays under P1, unlinked').toHaveAttribute('data-state', 'unlink', {timeout: 8_000});

        // P2's picker offers the FEE kept by P1's choice.
        const form = await openParentForm(p, savedBulkRow(p, buy2Id));
        const picker = await openChargesPicker(form);
        await expect(pickerRow(picker, s.feeId), 'the FEE kept under P1 «del» is offered').toHaveCount(1, {timeout: 8_000});

        await pickAndAdd(picker, pickerRow(picker, s.feeId));
        await expect(form.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`)).toHaveCount(1);
        await applyForm(form);
        await expectUnder(savedBulkRow(p, s.feeId), savedBulkRow(p, buy2Id), 'the FEE');
        await expect(savedBulkRow(p, s.feeId).getByTestId('tx-bulk-charge-state'), 'the FEE is linked under P2, no longer «unlink»').toHaveAttribute('data-state', 'linked');

        // «Save all», captured whole: a refusal is reported with its issues and the payload, never read as a pass.
        await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
        const commit = bulk.getByTestId('tx-bulk-commit');
        await expect(commit).toBeEnabled({timeout: 10_000});
        const requestPromise = p.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
        const responsePromise = p.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
        await commit.click();
        const payload = (await requestPromise).postDataJSON() as unknown;
        const response = await responsePromise;
        const raw = await response.text();
        const after = await readByIds(p, [s.buyId, s.feeId, s.taxId, buy2Id]);
        const dump = `status ${response.status()} — response ${raw} — payload ${JSON.stringify(payload)} — server ${JSON.stringify([...after.values()])}`;
        const body = JSON.parse(raw) as CommitBody;
        expect(body.committed, `the batch rolled back: ${dump}`).toBe(true);
        await expect(bulk).toBeHidden({timeout: 10_000});

        expect(after.has(s.buyId), `P1 is gone: ${dump}`).toBe(false);
        expect(after.has(buy2Id), `P2 stays: ${dump}`).toBe(true);
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE points at P2: ${dump}`).toBe(buy2Id);
        expect(after.has(s.taxId), `the TAX stays: ${dump}`).toBe(true);
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
    });
});
