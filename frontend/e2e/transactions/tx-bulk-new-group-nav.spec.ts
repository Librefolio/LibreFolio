/**
 * Inside the Bulk, moving between a NEW parent and its charges and unlinking them, from both Forms (lane 66, lot TL-11).
 *
 * A new row has no id: in the Form it is named by its row reference and reached by its key (`op-<row id>`, the grid's
 * `data-row-id`). With a saved parent nothing changes (`tx-bulk-charges-link.spec.ts`, «Open» by id).
 *
 *   (a) A new BUY with a FEE born in its Form, nothing saved. The FEE's own Form shows the BUY by its row label, not by an
 *       id, and offers no other parent; «Open» → the BUY's Form with the FEE highlighted; «Open» on the FEE → back in the
 *       FEE's Form; «Unlink» + «Apply» → the FEE is a top-level row. «Save all» → on the server the FEE has no parent, on
 *       the BUY's broker, asset and date.
 *   (b) The same group, unlinked from the BUY's Form: the FEE's row leaves the section, «Apply» → a top-level row; saved
 *       with no parent, on the BUY's broker, asset and date.
 *   (c) A SAVED free FEE linked under a new BUY: its own Form shows the BUY; «Unlink» + «Apply» → top-level again; «Save
 *       all» sends nothing about the FEE's parent, and on the server it is still free.
 *
 * RED until TL-11: (a) and (c) stop where the FEE's Form must show the new BUY, (b) where the BUY's Form must offer «Unlink».
 *
 * testids relied on: transactions-page · tx-table · dt-row-checkbox-tx-<id> · toolbar-action-edit · tx-add-button ·
 * tx-bulk-modal · tx-bulk-modal-root[data-busy] · tx-bulk-body · tx-bulk-row-label[data-charge-of] ·
 * tx-bulk-row-status[data-status] · tx-bulk-add-row · tx-bulk-commit · row-actions-<row id> ·
 * context-menu-action-edit-single · tx-form-modal · tx-form-type · tx-form-broker-wrap · tx-form-asset(-trigger/-search) ·
 * search-select-option-<id> · tx-form-quantity · tx-form-cash-wrap · tx-form-optional-toggle · tx-form-description ·
 * tx-form-save · tx-form-charges[data-state] · tx-form-charges-add-FEE · tx-form-charges-link-existing ·
 * tx-form-charge-row[data-charge-key][data-charge-id][data-highlighted] · tx-form-charge-{open,unlink,remove}-<key> ·
 * tx-form-charge-cash-<key>-amount · tx-form-charge-note-<key> · tx-form-parent[data-state][data-parent-key]
 * [data-parent-id] · tx-form-parent-{summary,open,unlink,unlinked,link} · tx-picker-modal · tx-picker-add.
 * Rows are found by the description the test gave them (new) or by the `#<id>` of their ID cell (saved). The verdict is
 * the batch sent and the server, read back by id; never the translated words.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`): every row on its broker is the test's, so
 * the afterEach deletes them all, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {cleanupOwnedAccount, emptyOwnedAccount, readTransactions} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedBuyAndFreeFee, type ChargeTx, type CommitBody, type FundedAccount} from '../fixtures/linked-charges';

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// The Bulk
// ---------------------------------------------------------------------------

/** The new rows of the Bulk carrying this description. */
function newRow(bulk: Locator, description: string): Locator {
    const page = bulk.page();
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="description"]', {hasText: description})})
        .filter({has: page.locator('[data-testid="tx-bulk-row-status"][data-status="new"]')});
}

/** The Bulk row of saved transaction `id`. */
function savedRow(bulk: Locator, id: number): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

async function rowIdOf(row: Locator): Promise<string> {
    await expect(row).toHaveCount(1, {timeout: 10_000});
    const id = await row.getAttribute('data-row-id');
    if (!id) throw new Error('the Bulk row publishes no data-row-id');
    return id;
}

async function expectUnder(row: Locator, parentRowId: string, what: string): Promise<void> {
    await expect(row, `${what}: one row`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is not under its parent`).toHaveAttribute('data-charge-of', parentRowId, {timeout: 10_000});
}

async function expectTopLevel(row: Locator, what: string): Promise<void> {
    await expect(row, `${what}: one row`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId('tx-bulk-row-label')).toBeVisible();
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is still under a parent`).not.toHaveAttribute('data-charge-of', /.*/);
}

/** The label of a new row: how the Bulk's texts name it (`row <label>`). */
async function labelOf(row: Locator): Promise<string> {
    const label = row.getByTestId('tx-bulk-row-label');
    await expect(label).toHaveText(/\d/);
    return ((await label.textContent()) ?? '').trim();
}

/** ⋮ → «Edit row»: the row's Form on top of the Bulk, its broker field on screen. */
async function openRowForm(bulk: Locator, row: Locator): Promise<Locator> {
    const rowId = await rowIdOf(row);
    await bulk.getByTestId(`row-actions-${rowId}`).click();
    const action = bulk.page().getByTestId('context-menu-action-edit-single');
    await expect(action).toBeVisible({timeout: 5_000});
    await action.click();
    const form = bulk.page().getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await expect(form.getByTestId('tx-form-broker-wrap')).toBeVisible({timeout: 8_000});
    return form;
}

type SentRow = {id?: number; type?: string; description?: string; parent_transaction_id?: number; parent_ref?: string; ref?: string};
type Sent = {creates?: SentRow[]; updates?: SentRow[]; deletes?: number[]};

/** «Save all»; the batch must pass. Returns what was sent and the ids it created. */
async function saveAll(bulk: Locator): Promise<{sent: Sent; createdIds: number[]}> {
    const page = bulk.page();
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const sent = (await requestPromise).postDataJSON() as Sent;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(sent)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return {sent, createdIds: (body.results ?? []).filter((r) => r.operation === 'create').flatMap((r) => r.ids ?? [])};
}

// ---------------------------------------------------------------------------
// The Form
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

/** Fill the Form open on a new row with a BUY of 10 for 100; ends complete, the Form still open. */
async function fillBuy(page: Page, s: FundedAccount, description: string): Promise<Locator> {
    const form = page.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await pickOption(page, form.getByTestId('tx-form-type'), 'BUY');
    await pickOption(page, form.getByTestId('tx-form-broker-wrap').getByRole('combobox'), s.broker.id);
    await expect(form.getByTestId('tx-form-broker-wrap')).toContainText(s.broker.name);
    await form.getByTestId('tx-form-asset-trigger').click();
    const search = form.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: 5_000});
    await search.fill('Ethereum');
    const option = form.getByTestId('tx-form-asset').getByTestId(`search-select-option-${s.assetId}`);
    await expect(option).toBeVisible({timeout: 8_000});
    await option.click();
    await optionsClosed(page);
    const quantity = form.getByTestId('tx-form-quantity');
    await quantity.fill('10');
    await quantity.blur();
    await expect(quantity).not.toHaveValue('');
    const cash = form.getByTestId('tx-form-cash-wrap').locator('input[data-testid$="-amount"]');
    await cash.fill('100');
    await cash.blur();
    await expect(cash).not.toHaveValue('');
    await fillDescription(form, description);
    await expect(form.getByTestId('tx-form-save'), 'the BUY form is not complete').toBeEnabled({timeout: 8_000});
    return form;
}

/** «Apply»; ends on the Form closed. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
}

/** The row of the section with this key. */
function chargeRow(form: Locator, key: string): Locator {
    return form.locator(`[data-testid="tx-form-charge-row"][data-charge-key="${key}"]`);
}

/** The Form shows the new BUY as the charge's parent: by its key and its row label, never by an id, with no other parent offered. */
async function expectNewParent(form: Locator, buyRowId: string, buyLabel: string): Promise<Locator> {
    const parent = form.getByTestId('tx-form-parent');
    await expect(parent).toBeVisible({timeout: 8_000});
    await expect(parent, '66 TL-11: the Form of a charge under a new parent does not show it').toHaveAttribute('data-state', 'ready', {timeout: 5_000});
    await expect(parent).toHaveAttribute('data-parent-key', `op-${buyRowId}`);
    await expect(parent).toHaveAttribute('data-parent-id', '');
    const summary = parent.getByTestId('tx-form-parent-summary');
    await expect(summary, `the BUY is named by its row label (${buyLabel})`).toHaveText(new RegExp(`(^|\\s)${buyLabel}(\\s|$)`));
    await expect(summary, 'a new row has no id').not.toContainText('#');
    await expect(parent.getByTestId('tx-form-parent-link'), 'no other parent is offered').toHaveCount(0);
    return parent;
}

/** A new BUY with a FEE born in its Form, applied into the Bulk, nothing saved. */
async function newBuyWithNewFee(page: Page, s: FundedAccount): Promise<{bulk: Locator; buy: Locator; fee: Locator; buyRowId: string; feeRowId: string; buyLabel: string}> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-add-button').click();
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    const [buyDescription, feeDescription] = [`NewBuy ${s.marker}`, `NewFee ${s.marker}`];
    const form = await fillBuy(page, s, buyDescription);

    const section = form.getByTestId('tx-form-charges');
    await section.getByTestId('tx-form-charges-add-FEE').click();
    const added = section.locator('[data-testid="tx-form-charge-row"][data-charge-id=""]');
    await expect(added, 'the FEE this test added').toHaveCount(1);
    const amount = added.locator('input[data-testid^="tx-form-charge-cash-"][data-testid$="-amount"]');
    await amount.fill('3');
    await amount.blur();
    await expect(amount).not.toHaveValue('');
    const note = added.locator('input[data-testid^="tx-form-charge-note-"]');
    await note.fill(feeDescription);
    await expect(note).toHaveValue(feeDescription);
    await applyForm(form);

    const [buy, fee] = [newRow(bulk, buyDescription), newRow(bulk, feeDescription)];
    const buyRowId = await rowIdOf(buy);
    await expectUnder(fee, buyRowId, 'the new FEE');
    return {bulk, buy, fee, buyRowId, feeRowId: await rowIdOf(fee), buyLabel: await labelOf(buy)};
}

/** On the server: the new FEE has no parent and is on the new BUY's broker, asset and date; the BUY counts no charge. */
async function expectFeeSavedFree(page: Page, s: FundedAccount, sent: Sent, createdIds: number[]): Promise<void> {
    const feeSent = (sent.creates ?? []).filter((row) => row.type === 'FEE');
    const wire = `payload ${JSON.stringify(sent)}`;
    expect(feeSent, wire).toHaveLength(1);
    expect(feeSent[0], `the FEE is sent with no parent: ${wire}`).not.toHaveProperty('parent_ref');
    expect(feeSent[0], `the FEE is sent with no parent: ${wire}`).not.toHaveProperty('parent_transaction_id');

    const created = [...(await readByIds(page, createdIds)).values()];
    const dump = `created ${JSON.stringify(created)} — ${wire}`;
    const of = (type: string): ChargeTx[] => created.filter((tx) => tx.type === type);
    expect([of('BUY').length, of('FEE').length], `one BUY and one FEE: ${dump}`).toEqual([1, 1]);
    const [buy, fee] = [of('BUY')[0], of('FEE')[0]];
    expect(fee.parent_transaction_id ?? null, `the FEE has no parent: ${dump}`).toBeNull();
    expect(buy.charges_count ?? 0, `the BUY counts no charge: ${dump}`).toBe(0);
    expect([buy.broker_id, buy.asset_id], dump).toEqual([s.broker.id, s.assetId]);
    expect({broker_id: fee.broker_id, asset_id: fee.asset_id, date: fee.date}, `the FEE keeps the BUY’s broker, asset and date: ${dump}`).toEqual({broker_id: buy.broker_id, asset_id: buy.asset_id, date: buy.date});
    expect(Number(fee.cash?.amount), dump).toBe(-3);
}

// ---------------------------------------------------------------------------

test.describe('Bulk — a new parent and its charges: moving between the two Forms, and «Unlink» from both (66 TL-11)', () => {
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
                const left = (await readTransactions(page, {broker_id: brokerId})).map((tx) => tx.id);
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('(a) from the new FEE’s Form: the new BUY by its row label, «Open» there and back, «Unlink» + «Apply» → a row of its own, saved with no parent', async ({page, request}) => {
        const s = await openFundedAccount(page, request, owned, [], 'tl11n1', 'TL11');
        brokerId = s.broker.id;
        const {bulk, fee, buyRowId, feeRowId, buyLabel} = await newBuyWithNewFee(page, s);

        let form = await openRowForm(bulk, fee);
        await expect(form.getByTestId('tx-form-description'), 'premise: the FEE’s Form').toHaveValue(`NewFee ${s.marker}`);
        const parent = await expectNewParent(form, buyRowId, buyLabel);

        // «Open» → the BUY's Form, the FEE highlighted among its charges.
        await parent.getByTestId('tx-form-parent-open').click();
        form = page.getByTestId('tx-form-modal');
        await expect(form.getByTestId('tx-form-description'), 'the BUY’s Form').toHaveValue(`NewBuy ${s.marker}`, {timeout: 8_000});
        const feeInForm = chargeRow(form, `op-${feeRowId}`);
        await expect(feeInForm).toHaveCount(1, {timeout: 8_000});
        await expect(feeInForm, 'the FEE the user came from is highlighted').toHaveAttribute('data-highlighted', 'true');
        await expect(form.getByTestId('tx-form-parent')).toHaveCount(0);

        // «Open» on the FEE → back.
        await feeInForm.getByTestId(`tx-form-charge-open-op-${feeRowId}`).click();
        await expect(form.getByTestId('tx-form-description'), 'back in the FEE’s Form').toHaveValue(`NewFee ${s.marker}`, {timeout: 8_000});
        const again = await expectNewParent(form, buyRowId, buyLabel);

        await again.getByTestId('tx-form-parent-unlink').click();
        await expect(again).toHaveAttribute('data-state', 'unlinked');
        await expect(again.getByTestId('tx-form-parent-unlinked')).toBeVisible();
        await applyForm(form);
        await expectTopLevel(fee, 'the FEE unlinked');

        const {sent, createdIds} = await saveAll(bulk);
        await expectFeeSavedFree(page, s, sent, createdIds);
    });

    test('(b) from the new BUY’s Form: «Unlink» on the FEE + «Apply» → a row of its own, saved with no parent', async ({page, request}) => {
        const s = await openFundedAccount(page, request, owned, [], 'tl11n2', 'TL11');
        brokerId = s.broker.id;
        const {bulk, buy, fee, feeRowId} = await newBuyWithNewFee(page, s);

        const form = await openRowForm(bulk, buy);
        await expect(form.getByTestId('tx-form-charges')).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        const feeInForm = chargeRow(form, `op-${feeRowId}`);
        await expect(feeInForm, 'premise: the FEE is listed').toHaveCount(1);
        await expect(feeInForm.getByTestId(`tx-form-charge-remove-op-${feeRowId}`), 'the bin stays').toBeVisible();
        const unlink = feeInForm.getByTestId(`tx-form-charge-unlink-op-${feeRowId}`);
        await expect(unlink, '66 TL-11: the BUY’s Form offers no «Unlink» on its new FEE').toBeVisible({timeout: 5_000});
        await unlink.click();
        await expect(feeInForm, 'unlinked, the FEE leaves the section').toHaveCount(0);
        await applyForm(form);
        await expectTopLevel(fee, 'the FEE unlinked');

        const {sent, createdIds} = await saveAll(bulk);
        await expectFeeSavedFree(page, s, sent, createdIds);
    });

    test('(c) a SAVED free FEE linked under a new BUY: its Form shows the BUY; «Unlink» + «Apply» → nothing sent about its parent, still free on the server', async ({page, request}) => {
        const s = await seedBuyAndFreeFee(page, request, owned, [], 'tl11n3', 'TL11');
        brokerId = s.broker.id;
        await navigateTo(page, `/transactions?id_min=${Math.min(s.buyId, s.feeId)}&id_max=${Math.max(s.buyId, s.feeId)}`);
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        // Two rows: the Bulk opens with no Form on top.
        for (const id of [s.buyId, s.feeId]) {
            const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
            await expect(checkbox).toBeVisible({timeout: 8_000});
            if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
            await expect(checkbox).toHaveAttribute('data-state', 'checked');
        }
        await page.getByTestId('toolbar-action-edit').click();
        const bulk = page.getByTestId('tx-bulk-modal');
        await expect(bulk).toBeVisible({timeout: 8_000});
        await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
        const fee = savedRow(bulk, s.feeId);
        await expect(fee, 'premise: the saved FEE is a row').toHaveCount(1, {timeout: 8_000});

        // A new BUY, the saved FEE picked under it in its Form.
        await bulk.getByTestId('tx-bulk-add-row').click();
        const description = `NewBuy ${s.marker}`;
        const addForm = await fillBuy(page, s, description);
        await addForm.getByTestId('tx-form-charges-link-existing').click();
        const picker = page.getByTestId('tx-picker-modal');
        await expect(picker).toBeVisible({timeout: 8_000});
        const pick = picker.locator(`tr[data-row-id="tx-${s.feeId}"]`);
        await expect(pick, 'the saved free FEE is offered').toHaveCount(1, {timeout: 8_000});
        const box = pick.locator('[data-testid^="dt-row-checkbox-tx-"]');
        if ((await box.getAttribute('data-state')) !== 'checked') await box.click();
        await expect(box).toHaveAttribute('data-state', 'checked');
        await picker.getByTestId('tx-picker-add').click();
        await expect(picker).toBeHidden({timeout: 8_000});
        await applyForm(addForm);
        const buy = newRow(bulk, description);
        const buyRowId = await rowIdOf(buy);
        await expectUnder(fee, buyRowId, 'the saved FEE');

        const form = await openRowForm(bulk, fee);
        const parent = await expectNewParent(form, buyRowId, await labelOf(buy));
        await parent.getByTestId('tx-form-parent-unlink').click();
        await expect(parent).toHaveAttribute('data-state', 'unlinked');
        await applyForm(form);
        await expectTopLevel(fee, 'the saved FEE unlinked');

        const {sent, createdIds} = await saveAll(bulk);
        const dump = `payload ${JSON.stringify(sent)}`;
        expect(
            (sent.creates ?? []).map((row) => row.type),
            `the new BUY alone is created: ${dump}`,
        ).toEqual(['BUY']);
        for (const update of (sent.updates ?? []).filter((row) => row.id === s.feeId)) {
            expect(update, `nothing is sent about the FEE’s parent: ${dump}`).not.toHaveProperty('parent_transaction_id');
            expect(update, `nothing is sent about the FEE’s parent: ${dump}`).not.toHaveProperty('parent_ref');
        }
        const back = await readByIds(page, [s.feeId, ...createdIds]);
        const state = `server ${JSON.stringify([...back.values()])} — ${dump}`;
        expect(back.get(s.feeId), `the FEE is still there: ${state}`).toBeDefined();
        expect(back.get(s.feeId)?.parent_transaction_id ?? null, `the FEE is still free: ${state}`).toBeNull();
        expect(createdIds, state).toHaveLength(1);
        expect(back.get(createdIds[0])?.charges_count ?? 0, `the new BUY counts no charge: ${state}`).toBe(0);
    });
});
