/**
 * A checkbox on every charge under its parent, and «Scollega» on the Bulk's selection bar (lane 66, lot TL-4; the
 * developer's P-2 = C and P-19). Spec: `lotti-testlist-20261123-FEE.md`, «TL-4», and the P-19 note under «TL-9».
 *
 *   (a) A saved BUY with its FEE and TAX, opened in the Bulk: the TAX under the BUY is ticked → «Scollega»
 *       (`tx-bulk-unlink-charges`, count 1) → no panel; the TAX is a row of its own with the badge «unlink», the BUY's
 *       chip counts 1, the selection is empty; «Save all» → on the server the TAX has no parent, the FEE still has.
 *   (b) P-19: the FEE already «del»; the BUY, the FEE and the TAX ticked → «Delete selected» → no panel (every charge
 *       ticked); the BUY «del», the FEE still «del» (not restored), the TAX «del»; «Save all» → all three gone.
 *   (c) Select-all with one group open and one closed: the open group's charges are ticked, the closed one's are not;
 *       closing the open group keeps its charges ticked and counted («Scollega» still counts them).
 *   (d) On a phone (375 × 812, touch): a charge under its parent behaves as the other rows — a long press opens its
 *       Form (the Bulk's DataTable has no `enableTouchSelection`: the long press is its double-click; probe of 25/11),
 *       a tap on its checkbox ticks it, and «Scollega» is offered. The spec's «spunta la spesa, come le altre righe»
 *       rested on a premise that is false in the Bulk; the lane kept «come le altre righe» (TL-4 checkpoint, 📌).
 *   (e) «Scollega» on the TAX, then the TAX (now a row of its own) ticked → «Reset selected» → back under the BUY,
 *       linked.
 *
 * RED until TL-4: every case fails where it ticks a charge under its parent (it has no checkbox today), after its own
 * premises (seed read back, chip counts, group open). The tick names TL-4 in its message.
 *
 * testids relied on: tx-table · dt-row-checkbox-tx-<id> · tx-charges-badge-<id>[data-expanded] · selection-toolbar
 * [data-selected-count] · toolbar-action-edit · tx-bulk-modal · tx-bulk-modal-root · tx-bulk-body · tx-bulk-row-label
 * [data-charge-of] · tx-bulk-charges-toggle-<rowId>[aria-expanded][data-charges-count] · tx-bulk-charge-state
 * [data-state] · tx-bulk-row-status[data-status] · dt-row-checkbox-<rowId>[data-state] · dt-select-all ·
 * tx-bulk-unlink-charges · tx-bulk-unlink-charges-count · tx-bulk-delete-selected · tx-bulk-reset-selected ·
 * tx-charges-modal-content · row-actions-<rowId> · context-menu-action-mark-delete · tx-bulk-commit · tx-form-modal ·
 * tx-form-cancel.
 * A Bulk row is found by the `#<id>` its ID cell shows. The Bulk holds only this test's rows, so the selection counts
 * of (c) are counts of rows the test created. The verdict of (a) and (b) is the server, read back by id.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, together, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, emptyOwnedAccount, jsonFrom} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy, type CommitBody, type LinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** Press a control: a tap on a touch screen, a click otherwise. */
async function press(target: Locator, touch: boolean): Promise<void> {
    if (touch) await target.tap();
    else await target.click();
}

/** Open /transactions and wait until every load wave is in. */
async function openTable(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Tick these rows in the transactions table and «Edit»: the Bulk opens on them, its validation settled. With one row
 *  its Form opens on top: closed here, the grid is the subject. */
async function editInBulk(page: Page, ids: number[], touch: boolean): Promise<Locator> {
    for (const id of ids) {
        const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await press(checkbox, touch);
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(ids.length), {timeout: 5_000});
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await press(edit, touch);
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    if (ids.length === 1) {
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
        await press(form.getByTestId('tx-form-cancel'), touch);
        await expect(form).toBeHidden({timeout: 8_000});
    }
    return bulk;
}

/** The Bulk row of transaction `id`, found by the `#id` its ID cell shows. */
function bulkRow(bulk: Locator, id: number): Locator {
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

/** The chip of the parent `row`, by the row id the page gives it. */
async function chipOf(bulk: Locator, row: Locator): Promise<Locator> {
    return bulk.getByTestId(`tx-bulk-charges-toggle-${await rowIdOf(row)}`);
}

/** The parent's group open, its `count` charges counted; ends on it open. */
async function openGroup(bulk: Locator, parentRow: Locator, count: number, touch: boolean): Promise<Locator> {
    const chip = await chipOf(bulk, parentRow);
    await expect(chip, `the parent's chip counts ${count} charges`).toHaveAttribute('data-charges-count', String(count), {timeout: 10_000});
    if ((await chip.getAttribute('aria-expanded')) !== 'true') await press(chip, touch);
    await expect(chip).toHaveAttribute('aria-expanded', 'true');
    return chip;
}

/** The checkbox of a Bulk row; TL-4 gives one to a charge under its parent too. */
async function boxOf(row: Locator): Promise<Locator> {
    return row.getByTestId(`dt-row-checkbox-${await rowIdOf(row)}`);
}

/** Tick a Bulk row; ends checked. */
async function tick(row: Locator, what: string, touch: boolean): Promise<void> {
    const box = await boxOf(row);
    await expect(box, `TL-4: ${what} has its own checkbox`).toBeVisible({timeout: 5_000});
    if ((await box.getAttribute('data-state')) !== 'checked') await press(box, touch);
    await expect(box).toHaveAttribute('data-state', 'checked');
}

/** `row` sits under `parentRow` with the badge `state`. */
async function expectUnder(row: Locator, parentRow: Locator, state: string, what: string): Promise<void> {
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is not under its parent`).toHaveAttribute('data-charge-of', await rowIdOf(parentRow), {timeout: 8_000});
    await expect(row.getByTestId('tx-bulk-charge-state'), `${what}: ${state}`).toHaveAttribute('data-state', state);
}

/** «Scollega», on, taking `count` rows; pressed; ends with no panel and the selection empty. */
async function unlinkSelected(bulk: Locator, count: number, touch: boolean): Promise<void> {
    const unlink = bulk.getByTestId('tx-bulk-unlink-charges');
    await expect(unlink, 'TL-4: the selection offers «Scollega»').toBeVisible({timeout: 5_000});
    await expect(bulk.getByTestId('tx-bulk-unlink-charges-count')).toHaveText(String(count));
    await press(unlink, touch);
    await expect(bulk.getByTestId('selection-toolbar'), 'after «Scollega» the selection is empty').toHaveCount(0, {timeout: 5_000});
    await expect(bulk.page().getByTestId('tx-charges-modal-content'), '«Scollega» asks nothing').toHaveCount(0);
}

/** «Save all»; the commit must succeed. Ends on the Bulk closed. */
async function saveAll(page: Page): Promise<unknown> {
    const bulk = page.getByTestId('tx-bulk-modal');
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const payload = (await requestPromise).postDataJSON() as unknown;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(payload)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return payload;
}

/** A second BUY with one FEE committed linked to it, on the seed's broker and asset, a day after the first. */
async function seedSecondLinkedBuy(page: Page, s: LinkedBuy, committed: number[]): Promise<{buyId: number; feeId: number}> {
    const date = daysAgoIso(4);
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {ref: 'q', broker_id: s.broker.id, asset_id: s.assetId, type: 'BUY', date, quantity: '5', cash: {code: 'USD', amount: '-50'}, description: `Buy B ${s.marker}`},
                    {parent_ref: 'q', broker_id: s.broker.id, asset_id: s.assetId, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-1'}, description: `Fee B ${s.marker}`},
                ],
            },
        }),
        'commit a second BUY with its FEE',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const [buyId, feeId] = [idAt(0), idAt(1)];
    committed.push(buyId, feeId);
    const back = await readByIds(page, [buyId, feeId]);
    expect(back.get(feeId)?.parent_transaction_id ?? null, 'premise: the second FEE is linked to the second BUY').toBe(buyId);
    return {buyId, feeId};
}

test.describe('Bulk — a checkbox on the charges under their parent, and «Scollega» on the bar (TL-4)', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together (a parent
    // deleted without its charges is refused), then the account and its brokers.
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

    test('(a) the TAX ticked under its BUY → «Scollega»: a row of its own «unlink», the BUY counts 1, no panel; saved, the TAX has no parent', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu1', 'ChgU');
        await openTable(page);
        const bulk = await editInBulk(page, [s.buyId], false);
        const buyRow = bulkRow(bulk, s.buyId);
        const chip = await openGroup(bulk, buyRow, 2, false);
        await expectUnder(bulkRow(bulk, s.taxId), buyRow, 'linked', 'premise: the TAX');

        await tick(bulkRow(bulk, s.taxId), 'the TAX under its BUY', false);
        await expect(await boxOf(buyRow), 'ticking the TAX does not tick its parent').toHaveAttribute('data-state', 'unchecked');
        await unlinkSelected(bulk, 1, false);

        const tax = bulkRow(bulk, s.taxId);
        await expect(tax.getByTestId('tx-bulk-row-label'), 'the TAX is a row of its own').not.toHaveAttribute('data-charge-of');
        await expect(tax.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'unlink');
        await expect(chip, 'the BUY keeps the FEE alone').toHaveAttribute('data-charges-count', '1');
        await expectUnder(bulkRow(bulk, s.feeId), buyRow, 'linked', 'the FEE, not ticked,');

        const payload = await saveAll(page);
        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE still points at the BUY: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count, `the BUY counts one charge: ${dump}`).toBe(1);
    });

    test('(b) P-19: the FEE already «del», BUY + FEE + TAX ticked → «Delete selected»: no panel; the FEE stays «del»; saved, all three gone', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu2', 'ChgU');
        await openTable(page);
        const bulk = await editInBulk(page, [s.buyId], false);
        const buyRow = bulkRow(bulk, s.buyId);
        await openGroup(bulk, buyRow, 2, false);
        const feeRow = bulkRow(bulk, s.feeId);
        await bulk.getByTestId(`row-actions-${await rowIdOf(feeRow)}`).click();
        const del = page.getByTestId('context-menu-action-mark-delete');
        await expect(del).toBeVisible({timeout: 5_000});
        await del.click();
        await expectUnder(feeRow, buyRow, 'del', 'premise: the FEE');

        for (const [id, what] of [
            [s.buyId, 'the BUY'],
            [s.feeId, 'the FEE «del» under its BUY'],
            [s.taxId, 'the TAX under its BUY'],
        ] as const)
            await tick(bulkRow(bulk, id), what, false);
        await bulk.getByTestId('tx-bulk-delete-selected').click();

        // The positive first, then the absence of the panel.
        await expect(buyRow.getByTestId('tx-bulk-row-status'), 'the BUY goes «del»').toHaveAttribute('data-status', 'delete', {timeout: 5_000});
        await expect(page.getByTestId('tx-charges-modal-content'), 'every charge ticked: no panel').toHaveCount(0);
        await expectUnder(feeRow, buyRow, 'del', 'P-19: the FEE, already «del»,');
        await expectUnder(bulkRow(bulk, s.taxId), buyRow, 'del', 'the TAX');

        const payload = await saveAll(page);
        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        expect([...after.keys()], `the three are deleted — payload ${JSON.stringify(payload)}`).toEqual([]);
    });

    test('(c) select-all ticks the open group’s charges, not the closed one’s; closing the open group keeps its charges ticked and counted', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu3', 'ChgU');
        const b = await seedSecondLinkedBuy(page, s, committedIds);
        await openTable(page);
        const bulk = await editInBulk(page, [s.buyId, b.buyId], false);
        const buyA = bulkRow(bulk, s.buyId);
        const buyB = bulkRow(bulk, b.buyId);
        const chipA = await openGroup(bulk, buyA, 2, false);
        const chipB = await chipOf(bulk, buyB);
        await expect(chipB, 'premise: the second BUY counts its FEE').toHaveAttribute('data-charges-count', '1', {timeout: 10_000});
        await expect(chipB, 'premise: its group is closed').toHaveAttribute('aria-expanded', 'false');
        await expectUnder(bulkRow(bulk, s.feeId), buyA, 'linked', 'premise: the FEE');

        await bulk.getByTestId('dt-select-all').click();

        const bar = bulk.getByTestId('selection-toolbar');
        await expect(bar, 'the two BUYs and the open group’s FEE and TAX').toHaveAttribute('data-selected-count', '4', {timeout: 5_000});
        for (const [id, what] of [
            [s.buyId, 'the first BUY'],
            [s.feeId, 'the FEE of the open group'],
            [s.taxId, 'the TAX of the open group'],
            [b.buyId, 'the second BUY'],
        ] as const)
            await expect(await boxOf(bulkRow(bulk, id)), `TL-4: ${what} ticked by select-all`).toHaveAttribute('data-state', 'checked');

        await chipB.click();
        await expect(chipB).toHaveAttribute('aria-expanded', 'true');
        await expect(await boxOf(bulkRow(bulk, b.feeId)), 'the closed group’s FEE was not ticked').toHaveAttribute('data-state', 'unchecked');
        await expect(bar).toHaveAttribute('data-selected-count', '4');

        await chipA.click();
        await expect(chipA).toHaveAttribute('aria-expanded', 'false');
        await expect(bulkRow(bulk, s.feeId), 'premise: the FEE is out of sight').toHaveCount(0);
        await expect(bar, 'the closed group’s ticked charges still count').toHaveAttribute('data-selected-count', '4');
        await expect(bulk.getByTestId('tx-bulk-unlink-charges-count'), '«Scollega» still takes them').toHaveText('2');
    });

    test('(e) «Scollega» on the TAX, then the TAX ticked → «Reset selected»: back under its BUY, linked', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu5', 'ChgU');
        await openTable(page);
        const bulk = await editInBulk(page, [s.buyId], false);
        const buyRow = bulkRow(bulk, s.buyId);
        const chip = await openGroup(bulk, buyRow, 2, false);
        await tick(bulkRow(bulk, s.taxId), 'the TAX under its BUY', false);
        await unlinkSelected(bulk, 1, false);
        const tax = bulkRow(bulk, s.taxId);
        await expect(tax.getByTestId('tx-bulk-charge-state'), 'premise: the TAX is «unlink»').toHaveAttribute('data-state', 'unlink');

        await tick(tax, 'the TAX unlinked', false);
        const reset = bulk.getByTestId('tx-bulk-reset-selected');
        await expect(reset).toBeVisible({timeout: 5_000});
        await reset.click();

        await expectUnder(tax, buyRow, 'linked', 'the TAX, reset,');
        await expect(chip, 'the BUY counts both again').toHaveAttribute('data-charges-count', '2');
        await expect(tax.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'original');
    });

    // A context of its own (375 × 812, a touch screen), nested so it keeps this block's cleanup.
    test.describe('on a phone', () => {
        test.use({viewport: {width: 375, height: 812}, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'isMobile and the touch screen are Chromium emulation here');

        /**
         * A finger held on the description cell of `row`: a `touchstart` on it now (bubbling to the row, where the table
         * starts its 500 ms long press); the returned function lifts it (`touchend`). Synthetic, on purpose: a CDP
         * `Input.dispatchTouchEvent` hold reached the document but never started the table's long press (probe of
         * 25/11, lane 66 TL-4), while this one did — on a top-level Bulk row it opened that row's Form.
         */
        async function holdFinger(row: Locator): Promise<() => Promise<void>> {
            const cell = row.locator('td[data-column-id="description"]');
            await expect(cell).toBeVisible({timeout: 5_000});
            await cell.scrollIntoViewIfNeeded();
            await expect(cell).toBeInViewport();
            const fire = (type: 'touchstart' | 'touchend') =>
                cell.evaluate((el, eventType) => {
                    const r = el.getBoundingClientRect();
                    const touch = new Touch({identifier: 7, target: el, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2});
                    const touches = eventType === 'touchstart' ? [touch] : [];
                    el.dispatchEvent(new TouchEvent(eventType, {bubbles: true, cancelable: true, touches, targetTouches: touches, changedTouches: [touch]}));
                }, type);
            await fire('touchstart');
            return () => fire('touchend');
        }

        test('(d) a charge under its parent behaves as the other rows: a long press opens its Form; a tap on its checkbox ticks it; «Scollega» is offered', async ({page, request}) => {
            const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu4', 'ChgU');
            await openTable(page);
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints, phone: window.matchMedia('(max-width: 639px)').matches}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            expect(device.phone, 'the page must be drawn at phone width, below 640 px').toBe(true);
            const bulk = await editInBulk(page, [s.buyId], true);
            const buyRow = bulkRow(bulk, s.buyId);
            await openGroup(bulk, buyRow, 2, true);
            const feeRow = bulkRow(bulk, s.feeId);
            await expectUnder(feeRow, buyRow, 'linked', 'premise: the FEE');
            const feeBox = await boxOf(feeRow);
            await expect(feeBox, 'TL-4: the FEE under its BUY has its own checkbox').toBeVisible({timeout: 5_000});
            await expect(feeBox, 'premise: unticked').toHaveAttribute('data-state', 'unchecked');

            const form = page.getByTestId('tx-form-modal');
            const lift = await holdFinger(feeRow);
            try {
                // The table's long press fires after 500 ms of a finger held still: a retrying assertion, no clock wait.
                await expect(form, 'the long press opens the FEE’s Form, as on any Bulk row').toBeVisible({timeout: 5_000});
            } finally {
                await lift();
            }
            await expect(feeBox, 'the long press ticks nothing').toHaveAttribute('data-state', 'unchecked');
            await press(form.getByTestId('tx-form-cancel'), true);
            await expect(form).toBeHidden({timeout: 8_000});

            await press(feeBox, true);
            await expect(feeBox, 'a tap on its checkbox ticks the FEE').toHaveAttribute('data-state', 'checked', {timeout: 5_000});
            await expect(await boxOf(buyRow), 'the parent is not ticked').toHaveAttribute('data-state', 'unchecked');
            await expect(bulk.getByTestId('tx-bulk-unlink-charges'), '«Scollega» is offered').toBeVisible({timeout: 5_000});
            await expect(bulk.getByTestId('tx-bulk-unlink-charges-count')).toHaveText('1');
        });
    });
});
