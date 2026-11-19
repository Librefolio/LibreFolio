/**
 * «Link» inside the Bulk (U3) and «Open» from a charge to its parent (lane 66, lot F7-d).
 * Contract: `66-F7-contract.md` §20.4, §20.5, §20.7, corrected by §21 and §22.
 *
 *   (a) In the Bulk, a new BUY and a new FEE written on their own (same broker and asset), both selected → «Link»
 *       (`tx-bulk-link-charges`) → the panel (`tx-charges-modal-content`, `data-mode="link"`) → confirm → «Save all»:
 *       on the server the FEE's `parent_transaction_id` is the BUY.
 *   (b) A saved BUY and a saved FEE linked to nothing, same broker and asset, opened in the Bulk from the table, linked
 *       there and saved: on the server the FEE points at the BUY.
 *   (c) A linked FEE opened alone in the Bulk (its BUY is not a row of it): «Open» in the FEE's form, on its parent
 *       (`tx-form-parent-open`) → the form shows the BUY, the FEE highlighted, and the BUY is now a row of the Bulk.
 *   (d) On a phone (375 × 812, touch): (b) by tap.
 *
 * testids relied on: tx-add-button · tx-bulk-modal · tx-bulk-modal-root · tx-bulk-body · tx-bulk-add-row ·
 * dt-row-checkbox-<rowId> · tx-bulk-link-charges · tx-charges-modal-content[data-mode] · tx-charges-modal-confirm ·
 * tx-bulk-commit · tx-form-modal · tx-form-type · tx-form-broker-wrap · tx-form-asset-trigger · tx-form-asset-search ·
 * search-select-option-<value> · tx-form-quantity · tx-form-cash-wrap · tx-form-optional-toggle · tx-form-description ·
 * tx-form-save · tx-form-cancel · tx-form-parent[data-parent-id][data-state] · tx-form-parent-open · tx-form-charges ·
 * tx-form-charge-row[data-charge-id][data-highlighted] · tx-bulk-row-label[data-charge-of] · tx-table ·
 * dt-row-checkbox-tx-<id> · toolbar-action-edit.
 * A saved Bulk row is found by the `#<id>` its ID cell shows, a new one by the description this test typed. The
 * verdict is the server, read back by id.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {cleanupOwnedAccount, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, seedBuyAndFreeFee, seedLinkedBuy, type BuyAndFreeFee, type CommitBody} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** Press a control: a tap on a touch screen, a click otherwise. */
async function press(target: Locator, touch: boolean): Promise<void> {
    if (touch) await target.tap();
    else await target.click();
}

/** The Bulk row of saved transaction `id`, found by the `#id` its ID cell shows. */
function bulkRow(page: Page, id: number): Locator {
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

/** Tick a Bulk row's checkbox; ends checked. */
async function tickBulkRow(row: Locator, touch: boolean): Promise<void> {
    await expect(row).toHaveCount(1, {timeout: 8_000});
    const rowId = await row.getAttribute('data-row-id');
    const box = row.getByTestId(`dt-row-checkbox-${rowId}`);
    await expect(box).toBeVisible({timeout: 5_000});
    if ((await box.getAttribute('data-state')) !== 'checked') await press(box, touch);
    await expect(box).toHaveAttribute('data-state', 'checked');
}

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
async function fillDescription(page: Page, form: Locator, text: string): Promise<void> {
    const details = form.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: 5_000});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await form.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = form.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

type NewRow = {type: 'BUY' | 'FEE'; brokerId: number; brokerName: string; assetId: number; quantity?: string; cash: string; description: string};

/** Fill the open form with a new row and «Apply» it into the Bulk; ends on the form closed and the row in the grid. */
async function writeRow(page: Page, row: NewRow): Promise<void> {
    const form = page.getByTestId('tx-form-modal');
    await expect(form).toBeVisible({timeout: 8_000});
    await pickOption(page, form.getByTestId('tx-form-type'), row.type);
    await pickOption(page, form.getByTestId('tx-form-broker-wrap').getByRole('combobox'), row.brokerId);
    await expect(form.getByTestId('tx-form-broker-wrap')).toContainText(row.brokerName);
    // The FEE gets the BUY's asset too: without it «Link» is off with the reason noAsset.
    await expect(form.getByTestId('tx-form-asset-trigger')).toBeVisible({timeout: 5_000});
    await form.getByTestId('tx-form-asset-trigger').click();
    const assetSearch = page.getByTestId('tx-form-asset-search');
    await expect(assetSearch).toBeVisible({timeout: 5_000});
    await assetSearch.fill('Ethereum');
    const assetOption = page.getByTestId(`search-select-option-${row.assetId}`);
    await expect(assetOption).toBeVisible({timeout: 8_000});
    await assetOption.click();
    await optionsClosed(page);
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
    await fillDescription(page, form, row.description);
    const apply = form.getByTestId('tx-form-save');
    await expect(apply, `the ${row.type} form is not complete`).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
    await expect(newBulkRow(page, row.description)).toHaveCount(1, {timeout: 8_000});
}

/** «Link» in the Bulk toolbar → the panel in link mode → confirm; ends on the charge under the parent. */
async function linkInBulk(page: Page, parentRow: Locator, chargeRow: Locator, touch: boolean): Promise<void> {
    await tickBulkRow(parentRow, touch);
    await tickBulkRow(chargeRow, touch);
    const link = page.getByTestId('tx-bulk-link-charges');
    await expect(link, 'the Bulk offers no «Link» for a parent and a charge selected').toBeVisible({timeout: 8_000});
    await expect(link).not.toHaveAttribute('aria-disabled', 'true');
    await press(link, touch);
    const content = page.getByTestId('tx-charges-modal-content');
    await expect(content).toBeVisible({timeout: 8_000});
    await expect(content).toHaveAttribute('data-mode', 'link');
    await press(content.getByTestId('tx-charges-modal-confirm'), touch);
    await expect(content).toBeHidden({timeout: 5_000});
    const parentRowId = await parentRow.getAttribute('data-row-id');
    await expect(chargeRow.getByTestId('tx-bulk-row-label'), 'the charge sits under its parent').toHaveAttribute('data-charge-of', parentRowId ?? '<none>', {timeout: 5_000});
}

/** «Save all»; the commit must succeed. */
async function saveAll(page: Page, touch: boolean): Promise<{body: CommitBody; payload: unknown}> {
    const bulk = page.getByTestId('tx-bulk-modal');
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await press(commit, touch);
    const payload = (await requestPromise).postDataJSON() as unknown;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(payload)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return {body, payload};
}

/** Tick these rows in the transactions table and «Edit»: the Bulk opens on them (several rows: no form). */
async function editInBulk(page: Page, ids: number[], touch: boolean): Promise<void> {
    for (const id of ids) {
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await press(checkbox, touch);
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await press(edit, touch);
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
}

/** The flow of (b) and (d): the saved BUY and FEE linked in the Bulk, saved, and the server's verdict. */
async function linkSavedPair(page: Page, s: BuyAndFreeFee, touch: boolean): Promise<void> {
    await navigateTo(page, `/transactions?id_min=${Math.min(s.buyId, s.feeId)}&id_max=${Math.max(s.buyId, s.feeId)}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await editInBulk(page, [s.buyId, s.feeId], touch);
    await expect(bulkRow(page, s.buyId)).toHaveCount(1, {timeout: 8_000});
    await expect(bulkRow(page, s.feeId)).toHaveCount(1);

    await linkInBulk(page, bulkRow(page, s.buyId), bulkRow(page, s.feeId), touch);
    const {payload} = await saveAll(page, touch);

    const after = await readByIds(page, [s.buyId, s.feeId]);
    const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
    expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE points at the BUY: ${dump}`).toBe(s.buyId);
    expect(after.get(s.buyId)?.charges_count, `the BUY counts one charge: ${dump}`).toBe(1);
}

test.describe('Bulk — «Link» a parent and its charges, «Open» a parent from its charge', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together, then the
    // account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (owned.user && committedIds.length > 0) {
                const left = [...(await readByIds(page, committedIds)).keys()];
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('(a) a new BUY and a new FEE written apart, linked in the Bulk and saved: the FEE points at the BUY', async ({page, request}) => {
        const {broker, assetId, marker} = await openFundedAccount(page, request, owned, committedIds, 'chgu1', 'ChgU');
        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        await page.getByTestId('tx-add-button').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});

        await writeRow(page, {type: 'BUY', brokerId: broker.id, brokerName: broker.name, assetId, quantity: '10', cash: '100', description: `Buy ${marker}`});
        await page.getByTestId('tx-bulk-add-row').click();
        await writeRow(page, {type: 'FEE', brokerId: broker.id, brokerName: broker.name, assetId, cash: '5', description: `Fee ${marker}`});
        // Setup barrier: two new rows, the FEE on its own (top-level).
        await expect(newBulkRow(page, `Fee ${marker}`).getByTestId('tx-bulk-row-label')).not.toHaveAttribute('data-charge-of', /.+/);

        await linkInBulk(page, newBulkRow(page, `Buy ${marker}`), newBulkRow(page, `Fee ${marker}`), false);
        const {body, payload} = await saveAll(page, false);
        const createdIds = (body.results ?? []).filter((r) => r.operation === 'create').flatMap((r) => r.ids ?? []);
        committedIds.push(...createdIds);

        const created = [...(await readByIds(page, createdIds)).values()];
        const dump = `created ${JSON.stringify(created)} — payload ${JSON.stringify(payload)}`;
        const buys = created.filter((tx) => tx.type === 'BUY');
        const fees = created.filter((tx) => tx.type === 'FEE');
        expect(buys, `one BUY: ${dump}`).toHaveLength(1);
        expect(fees, `one FEE: ${dump}`).toHaveLength(1);
        expect(fees[0].parent_transaction_id, `the FEE points at the BUY: ${dump}`).toBe(buys[0].id);
    });

    test('(b) a saved BUY and a saved free FEE, linked in the Bulk and saved: the FEE points at the BUY', async ({page, request}) => {
        const s = await seedBuyAndFreeFee(page, request, owned, committedIds, 'chgu2', 'ChgU');
        await linkSavedPair(page, s, false);
    });

    test('(c) «Open» from a charge’s form to its parent absent from the Bulk: the form shows the parent, and the parent joins the Bulk', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu3', 'ChgU');
        // The FEE alone: a type filter shows it as a row of its own (F5), the id range keeps the table to it.
        await navigateTo(page, `/transactions?types=FEE&id_min=${s.feeId}&id_max=${s.feeId}`);
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${s.feeId}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
        await page.getByTestId('toolbar-action-edit').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'one selected row auto-opens its form').toBeVisible({timeout: 8_000});
        await expect(bulkRow(page, s.feeId), 'premise: the FEE is a row of the Bulk').toHaveCount(1, {timeout: 8_000});
        await expect(bulkRow(page, s.buyId), 'premise: the BUY is not a row of the Bulk').toHaveCount(0);
        const parent = form.getByTestId('tx-form-parent');
        await expect(parent).toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
        await expect(parent).toHaveAttribute('data-state', 'ready', {timeout: 8_000});

        const open = parent.getByTestId('tx-form-parent-open');
        await expect(open, 'the form in the Bulk offers «Open» on the parent').toBeVisible({timeout: 5_000});
        await open.click();

        await expect(form.getByTestId('tx-form-charges'), 'the form shows the BUY').toBeVisible({timeout: 8_000});
        await expect(form.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`), 'the FEE the user came from is highlighted').toHaveAttribute('data-highlighted', 'true', {timeout: 8_000});
        await form.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: 8_000});
        await expect(bulkRow(page, s.buyId), 'the BUY is a row of the Bulk').toHaveCount(1, {timeout: 8_000});
    });

    // On a phone: a context of its own (375 × 812, a touch screen), nested so it keeps this block's cleanup.
    test.describe('on a phone', () => {
        test.use({viewport: {width: 375, height: 812}, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'isMobile and the touch screen are Chromium emulation here');

        test('(d) a saved BUY and a saved free FEE linked in the Bulk by tap: the FEE points at the BUY', async ({page, request}) => {
            const s = await seedBuyAndFreeFee(page, request, owned, committedIds, 'chgu4', 'ChgU');
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            await linkSavedPair(page, s, true);
        });
    });
});
