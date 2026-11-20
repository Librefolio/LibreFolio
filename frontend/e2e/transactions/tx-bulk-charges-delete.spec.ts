/**
 * «Delete» on a saved parent inside the Bulk opens the panel V1 before marking anything (lane 66, lot F7-c2).
 * Contract: `66-F7-contract.md` §12, §17 corrected by §18.
 *
 *   (a) A saved BUY with its FEE and TAX, opened in the Bulk; ⋮ → «Delete» on the BUY → the panel
 *       (`tx-charges-modal-content`, `data-mode="deleteParent"`), the BUY not «del» while it is open; «Cancel» → nothing
 *       changed; «Delete» again → «Keep» → «Save all» → on the server the BUY is gone, the FEE and the TAX stay with no
 *       parent.
 *   (b) The same, «Delete all» → all three are gone.
 *   (c) On a phone (375 × 812, touch): the panel opens and «Keep» works by tap; the server says so.
 *
 * testids relied on: dt-row-checkbox-tx-<id> · toolbar-action-edit · tx-bulk-modal · tx-bulk-modal-root · tx-bulk-body ·
 * tx-bulk-row-status[data-status] · tx-bulk-charges-toggle-<rowId>[data-charges-count] · row-actions-<rowId> ·
 * context-menu-action-mark-delete · tx-charges-modal · tx-charges-modal-content[data-mode] · tx-charges-modal-keep ·
 * tx-charges-modal-all · tx-charges-modal-cancel · tx-bulk-commit · tx-form-modal · tx-form-cancel.
 * A Bulk row is found by the `#<id>` its ID cell shows. The verdict is the server, read back by id.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {cleanupOwnedAccount, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy, type CommitBody, type LinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** Press a control: a tap on a touch screen, a click otherwise. */
async function press(target: Locator, touch: boolean): Promise<void> {
    if (touch) await target.tap();
    else await target.click();
}

/** The Bulk row of transaction `id`, found by the `#id` its ID cell shows. */
function bulkRow(bulk: Locator, id: number): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** Open the BUY alone in the Bulk from the table; close the Form it opens on; end on its charges read (the chip). */
async function openBuyInBulk(page: Page, s: LinkedBuy, touch: boolean): Promise<Locator> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${s.buyId}`);
    await expect(checkbox).toBeVisible({timeout: 8_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
    await press(form.getByTestId('tx-form-cancel'), touch);
    await expect(form).toBeHidden({timeout: 8_000});
    const buyRow = bulkRow(bulk, s.buyId);
    await expect(buyRow).toBeVisible({timeout: 8_000});
    const chip = bulk.getByTestId(`tx-bulk-charges-toggle-${await buyRow.getAttribute('data-row-id')}`);
    await expect(chip, 'the BUY’s two charges are read').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    return bulk;
}

/** ⋮ → «Delete» on the BUY; ends on the panel open in deleteParent mode. */
async function deleteBuy(page: Page, bulk: Locator, s: LinkedBuy, touch: boolean): Promise<Locator> {
    const rowId = await bulkRow(bulk, s.buyId).getAttribute('data-row-id');
    await press(bulk.getByTestId(`row-actions-${rowId}`), touch);
    const del = page.getByTestId('context-menu-action-mark-delete');
    await expect(del).toBeVisible({timeout: 5_000});
    await press(del, touch);
    const content = page.getByTestId('tx-charges-modal-content');
    await expect(content, '«Delete» on a parent with charges opened no panel').toBeVisible({timeout: 8_000});
    await expect(content).toHaveAttribute('data-mode', 'deleteParent');
    return content;
}

/** «Save all»; the commit must succeed. */
async function saveAll(page: Page, bulk: Locator, touch: boolean): Promise<{body: CommitBody; payload: unknown}> {
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

/** The flow of (a) and (c): Cancel first, then «Keep», «Save all», and the server's verdict. */
async function cancelThenKeep(page: Page, s: LinkedBuy, touch: boolean): Promise<void> {
    const bulk = await openBuyInBulk(page, s, touch);
    const buyStatus = bulkRow(bulk, s.buyId).getByTestId('tx-bulk-row-status');

    let content = await deleteBuy(page, bulk, s, touch);
    await expect(buyStatus, 'the BUY is not «del» while the panel is open').toHaveAttribute('data-status', 'original');
    await press(content.getByTestId('tx-charges-modal-cancel'), touch);
    await expect(content).toBeHidden({timeout: 5_000});
    await expect(buyStatus, '«Cancel» changes nothing').toHaveAttribute('data-status', 'original');
    await expect(bulk, 'the Bulk stays open').toBeVisible();

    content = await deleteBuy(page, bulk, s, touch);
    await press(content.getByTestId('tx-charges-modal-keep'), touch);
    await expect(content).toBeHidden({timeout: 5_000});
    await expect(buyStatus).toHaveAttribute('data-status', 'delete');
    const {payload} = await saveAll(page, bulk, touch);

    const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
    const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
    expect(after.has(s.buyId), `the BUY is gone: ${dump}`).toBe(false);
    expect(after.has(s.feeId), `the FEE stays: ${dump}`).toBe(true);
    expect(after.has(s.taxId), `the TAX stays: ${dump}`).toBe(true);
    expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE has no parent: ${dump}`).toBeNull();
    expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
}

test.describe('Bulk — «Delete» on a parent with charges asks first (V1)', () => {
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

    test('(a) «Delete» on the BUY opens the panel; «Cancel» changes nothing; «Keep» → Save all: the BUY goes, its charges stay with no parent', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgd1', 'ChgD');
        await cancelThenKeep(page, s, false);
    });

    test('(b) «Delete all» → Save all: the BUY and both its charges are gone', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgd2', 'ChgD');
        const bulk = await openBuyInBulk(page, s, false);

        const content = await deleteBuy(page, bulk, s, false);
        await content.getByTestId('tx-charges-modal-all').click();
        await expect(content).toBeHidden({timeout: 5_000});
        const {payload} = await saveAll(page, bulk, false);

        const after = await readByIds(page, [s.depositId, s.buyId, s.feeId, s.taxId]);
        expect([...after.keys()], `the batch deletes the BUY and its two charges, nothing else — payload ${JSON.stringify(payload)}`).toEqual([s.depositId]);
    });

    // On a phone: a context of its own (375 × 812, a touch screen), nested so it keeps this block's cleanup.
    test.describe('on a phone', () => {
        test.use({viewport: {width: 375, height: 812}, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'isMobile and the touch screen are Chromium emulation here');

        test('(c) the panel opens and «Keep» works by tap: the BUY goes, its charges stay with no parent', async ({page, request}) => {
            const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgd3', 'ChgD');
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            await cancelThenKeep(page, s, true);
        });
    });
});
