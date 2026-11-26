/**
 * The Bulk shows a parent's linked charges grouped under it (lane 66, lot F7-c1, grid BK2).
 * Contract: `66-F7-contract.md` §13 (F7-c1 part), corrected by §14.
 *
 *   (a) A saved BUY with its FEE and TAX, opened alone in the Bulk (edit): the Bulk reads its charges on entry; the BUY
 *       row carries the chip `tx-bulk-charges-toggle-<rowId>` with `data-charges-count="2"`, closed; the chip opens
 *       the group: two indented rows (`↳`, `data-charge-of` = the BUY's row), each with its own selection checkbox
 *       (66 TL-4, P-2 = C: was «no selection checkbox»).
 *   (b) BUY, FEE and TAX selected together in the table and opened: the group comes open.
 *   (c) A double-click on an indented row opens the charge's own Form (its parent section names the BUY).
 *   (d) Paging at 5 rows: a parent whose open group crosses the page boundary keeps the group on its page; the row
 *       after it starts the next page.
 *   (e) A TAX unlinked in the BUY's Form is a top-level row of the Bulk with the state «unlink».
 *   (f) On a phone (375 × 812, touch): a tap on the chip opens the group; the FEE's ⋮ → «Delete» marks the FEE alone;
 *       the TAX's ⋮ → «Edit row» opens the TAX's Form.
 *
 * testids relied on: dt-row-checkbox-tx-<id> · toolbar-action-edit · tx-charges-badge-<id> · tx-bulk-modal ·
 * tx-bulk-modal-root · tx-bulk-body · tx-bulk-row-label[data-charge-of] · tx-bulk-charges-toggle-<rowId>
 * [aria-expanded][data-charges-count] · tx-bulk-charge-state[data-state] · dt-row-checkbox-<rowId> · tx-form-modal ·
 * tx-form-cancel · tx-form-save · tx-form-charges[data-state] · tx-form-charge-row[data-charge-id] ·
 * tx-form-charge-unlink-<key> · tx-form-parent[data-parent-id] · pagination-size-trigger · pagination-size-option-5 ·
 * pagination-next.
 * A Bulk row is found by the `#<id>` its ID cell shows (its own row id is a tempId the test cannot know); the chip by
 * the BUY row's `data-row-id`, read from the page. Nothing counts the grid's rows; the order checks of (d) ask which
 * page holds which row.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns, funded by its own DEPOSIT), so no
 * other spec sees its rows. The seed comes from `../fixtures/linked-charges.ts`, shared with `tx-charges-write.spec.ts`
 * (Playwright does not let a spec import another one). Nothing
 * is saved from the Bulk: the seed is read back by id as the premise, and the afterEach deletes whatever of the test's
 * rows is still there, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy, type LinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** A BUY with its FEE and TAX on an account of the test's own (`../fixtures/linked-charges.ts`). */
type Seeded = LinkedBuy;

/** Open /transactions and wait until every load wave is in. */
async function openTable(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/** Bring the table row checkbox of transaction `id` to `checked`, whatever state it starts in. */
async function ensureChecked(page: Page, id: number): Promise<void> {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 8_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
}

/** Open the table's fold of the BUY so its charges are rows that can be ticked. */
async function openTableFold(page: Page, s: Seeded): Promise<void> {
    const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
    await expect(badge).toBeVisible({timeout: 8_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    await expect(txRow(page, s.feeId)).toBeVisible({timeout: 5_000});
    await expect(txRow(page, s.taxId)).toBeVisible();
}

/** «Edit» on the selection: the Bulk opens. Ends on the Bulk visible and its validation settled. */
async function editSelection(page: Page, n: number): Promise<Locator> {
    const bar = page.getByTestId('selection-toolbar');
    await expect(bar).toHaveAttribute('data-selected-count', String(n), {timeout: 5_000});
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    return bulk;
}

/** The Bulk row of transaction `id`, found by the `#id` its ID cell shows. */
function bulkRow(bulk: Locator, id: number): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** The chip of the parent `row`, by the row id the page gives it. */
async function chipOf(bulk: Locator, row: Locator): Promise<Locator> {
    await expect(row).toBeVisible({timeout: 8_000});
    const rowId = await row.getAttribute('data-row-id');
    if (!rowId) throw new Error('the parent row publishes no data-row-id');
    return bulk.getByTestId(`tx-bulk-charges-toggle-${rowId}`);
}

/** Expect `row` indented under the parent row `parentRow`: `data-charge-of` names it, `↳` stands for the number, and it
 *  has its own selection checkbox (66 TL-4, P-2 = C: was «no selection checkbox»). */
async function expectIndentedUnder(row: Locator, parentRow: Locator): Promise<void> {
    const parentRowId = await parentRow.getAttribute('data-row-id');
    const label = row.getByTestId('tx-bulk-row-label');
    await expect(label).toHaveAttribute('data-charge-of', parentRowId ?? '<none>', {timeout: 8_000});
    await expect(label).toContainText('↳');
    await expect(row.locator('[data-testid^="dt-row-checkbox-"]'), 'TL-4: an indented charge has its own checkbox').toHaveCount(1);
}

test.describe('Bulk — linked charges grouped under their parent (BK2)', () => {
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

    test('(a) a saved BUY opened alone: its charges are read, the chip counts 2, closed; the chip opens two indented rows', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg1', 'ChgG');

        await openTable(page);
        await ensureChecked(page, s.buyId);
        const bulk = await editSelection(page, 1);
        // One selected row opens its Form on top of the Bulk: close it, the grid is the subject.
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
        await form.getByTestId('tx-form-cancel').click();
        await expect(form).toBeHidden({timeout: 8_000});

        const buyRow = bulkRow(bulk, s.buyId);
        const chip = await chipOf(bulk, buyRow);
        // The chip counting the two charges is the post-condition of the read: the barrier for every absence below.
        await expect(chip, 'the BUY row carries no chip counting its two charges').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
        await expect(chip, 'charges read by the Bulk itself: the group starts closed').toHaveAttribute('aria-expanded', 'false');
        await expect(bulkRow(bulk, s.feeId)).toHaveCount(0);
        await expect(bulkRow(bulk, s.taxId)).toHaveCount(0);
        await expect(buyRow.locator('[data-testid^="dt-row-checkbox-"]'), 'a top-level row keeps its checkbox').toHaveCount(1);

        await chip.click();

        await expect(chip).toHaveAttribute('aria-expanded', 'true');
        for (const id of [s.feeId, s.taxId]) {
            await expect(bulkRow(bulk, id)).toBeVisible({timeout: 5_000});
            await expectIndentedUnder(bulkRow(bulk, id), buyRow);
            await expect(bulkRow(bulk, id).getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'linked');
        }
        await expect(form, 'the chip opens no Form').toBeHidden();
    });

    test('(b) BUY, FEE and TAX selected together in the table: the group comes open in the Bulk', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg2', 'ChgG');

        await openTable(page);
        await openTableFold(page, s);
        for (const id of [s.buyId, s.feeId, s.taxId]) await ensureChecked(page, id);
        const bulk = await editSelection(page, 3);

        const buyRow = bulkRow(bulk, s.buyId);
        const chip = await chipOf(bulk, buyRow);
        await expect(chip).toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
        await expect(chip, 'charges brought with their parent: the group is open').toHaveAttribute('aria-expanded', 'true');
        for (const id of [s.feeId, s.taxId]) await expectIndentedUnder(bulkRow(bulk, id), buyRow);
    });

    test('(c) a double-click on an indented row opens that charge’s Form', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg3', 'ChgG');

        await openTable(page);
        await openTableFold(page, s);
        for (const id of [s.buyId, s.feeId, s.taxId]) await ensureChecked(page, id);
        const bulk = await editSelection(page, 3);
        const buyRow = bulkRow(bulk, s.buyId);
        await expectIndentedUnder(bulkRow(bulk, s.feeId), buyRow);

        await bulkRow(bulk, s.feeId).dblclick();

        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'the double-click opened no Form').toBeVisible({timeout: 8_000});
        // The charge's Form, not its parent's: its parent section names the BUY.
        await expect(form.getByTestId('tx-form-parent')).toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
    });

    test('(d) at 5 rows a page, an open group crossing the boundary stays on its page; the next row starts the next page', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg4', 'ChgG');
        // Three more deposits before the BUY (with the funding one, four rows before it) and one after: in date order
        // D D D D BUY FEE TAX D-after. Page 1 is the first five rows plus the BUY's two charges; page 2 the last deposit.
        const before = await commitCreates(
            page,
            [9, 8, 7].map((days) => ({broker_id: s.broker.id, type: 'DEPOSIT', date: daysAgoIso(days), cash: {code: 'USD', amount: '10'}, description: `Deposit ${days} ${s.marker}`})),
            'three deposits before the BUY',
        );
        const [afterId] = await commitCreates(page, [{broker_id: s.broker.id, type: 'DEPOSIT', date: daysAgoIso(3), cash: {code: 'USD', amount: '10'}, description: `Deposit after ${s.marker}`}], 'a deposit after the BUY');
        committedIds.push(...before, afterId);
        const all = [s.depositId, ...before, s.buyId, s.feeId, s.taxId, afterId];

        await openTable(page);
        await openTableFold(page, s);
        for (const id of all) await ensureChecked(page, id);
        const bulk = await editSelection(page, all.length);
        const buyRow = bulkRow(bulk, s.buyId);
        const chip = await chipOf(bulk, buyRow);
        await expect(chip, 'premise: the group is open').toHaveAttribute('aria-expanded', 'true', {timeout: 10_000});

        await bulk.getByTestId('pagination-size-trigger').click();
        await bulk.getByTestId('pagination-size-option-5').click();
        // Page 1: the four deposits before the BUY, the BUY and both its charges, though that is seven rows.
        for (const id of [s.depositId, ...before, s.buyId, s.feeId, s.taxId]) await expect(bulkRow(bulk, id), `#${id} is not on page 1`).toBeVisible({timeout: 8_000});
        await expect(bulkRow(bulk, afterId), 'the deposit after the BUY is on page 2').toHaveCount(0);

        await bulk.getByTestId('pagination-next').click();

        await expect(bulkRow(bulk, afterId), 'page 2 does not start at the deposit after the BUY').toBeVisible({timeout: 8_000});
        for (const id of [s.buyId, s.feeId, s.taxId]) await expect(bulkRow(bulk, id), `#${id} spilled onto page 2`).toHaveCount(0);
        await expect(bulk.getByTestId('pagination-next'), 'two pages, not three').toBeDisabled();
    });

    test('(e) a TAX unlinked in the BUY’s Form is a top-level row of the Bulk, with the state «unlink»', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg5', 'ChgG');

        await openTable(page);
        await ensureChecked(page, s.buyId);
        const bulk = await editSelection(page, 1);
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
        const section = form.getByTestId('tx-form-charges');
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        const taxRow = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.taxId}"]`);
        const unlink = taxRow.locator('[data-testid^="tx-form-charge-unlink-"]');
        await expect(unlink).toBeVisible({timeout: 8_000});
        await unlink.click();
        await expect(taxRow).toHaveCount(0);
        const apply = form.getByTestId('tx-form-save');
        await expect(apply).toBeEnabled({timeout: 8_000});
        await apply.click();
        await expect(form).toBeHidden({timeout: 8_000});

        const tax = bulkRow(bulk, s.taxId);
        await expect(tax, 'the unlinked TAX is not a row of the grid').toBeVisible({timeout: 8_000});
        await expect(tax.getByTestId('tx-bulk-row-label'), 'top-level: under no parent').not.toHaveAttribute('data-charge-of');
        await expect(tax.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'unlink');
        await expect(tax.locator('[data-testid^="dt-row-checkbox-"]'), 'a top-level row can be selected').toHaveCount(1);
        // The BUY keeps the FEE alone under it.
        await expect(await chipOf(bulk, bulkRow(bulk, s.buyId))).toHaveAttribute('data-charges-count', '1');
    });

    // On a phone (consultant's decision, 19/11): the indented row's ⋮ menu is the way in — «Delete» marks the charge alone,
    // «Edit row» opens its Form. A context of its own (375 × 812, a touch screen), nested so it keeps this block's cleanup;
    // every interaction in the Bulk is a real tap.
    test.describe('on a phone', () => {
        test.use({viewport: {width: 375, height: 812}, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'isMobile and the touch screen are Chromium emulation here');

        test('(f) a tap on the chip opens the group; ⋮ → «Delete» on the FEE marks it alone; ⋮ → «Edit row» on the TAX opens its Form', async ({page, request}) => {
            const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgg6', 'ChgG');

            await openTable(page);
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints, phone: window.matchMedia('(max-width: 639px)').matches}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            expect(device.phone, 'the page must be drawn at phone width, below 640 px').toBe(true);
            await ensureChecked(page, s.buyId);
            const bulk = await editSelection(page, 1);
            const form = page.getByTestId('tx-form-modal');
            await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
            await form.getByTestId('tx-form-cancel').tap();
            await expect(form).toBeHidden({timeout: 8_000});

            const buyRow = bulkRow(bulk, s.buyId);
            const chip = await chipOf(bulk, buyRow);
            await expect(chip, 'the BUY row carries no chip counting its two charges').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
            await expect(chip, 'premise: closed').toHaveAttribute('aria-expanded', 'false');

            await chip.tap();

            await expect(chip, 'a tap on the chip opens the group').toHaveAttribute('aria-expanded', 'true');
            const feeRow = bulkRow(bulk, s.feeId);
            const taxRow = bulkRow(bulk, s.taxId);
            await expectIndentedUnder(feeRow, buyRow);
            await expectIndentedUnder(taxRow, buyRow);

            // ⋮ on the FEE → «Delete»: the FEE alone is marked.
            const feeRowId = await feeRow.getAttribute('data-row-id');
            await bulk.getByTestId(`row-actions-${feeRowId}`).tap();
            const del = page.getByTestId('context-menu-action-mark-delete');
            await expect(del).toBeVisible({timeout: 5_000});
            await expect(page.getByTestId('context-menu-action-edit-single'), 'the menu of an indented row offers «Edit row» too').toBeVisible();
            await del.tap();
            await expect(feeRow.getByTestId('tx-bulk-charge-state'), 'the FEE is marked «del»').toHaveAttribute('data-state', 'del', {timeout: 5_000});
            await expect(taxRow.getByTestId('tx-bulk-charge-state'), 'the TAX is untouched').toHaveAttribute('data-state', 'linked');
            await expect(buyRow.getByTestId('tx-bulk-row-status'), 'the parent is untouched').toHaveAttribute('data-status', 'original');

            // ⋮ on the TAX → «Edit row»: the TAX's own Form.
            const taxRowId = await taxRow.getAttribute('data-row-id');
            await bulk.getByTestId(`row-actions-${taxRowId}`).tap();
            const edit = page.getByTestId('context-menu-action-edit-single');
            await expect(edit).toBeVisible({timeout: 5_000});
            await edit.tap();

            await expect(form, '«Edit row» opened no Form').toBeVisible({timeout: 8_000});
            await expect(form.getByTestId('tx-form-parent'), 'a charge’s Form: its parent section names the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
            await expect(form.getByTestId('tx-form-description'), 'the TAX’s, not the FEE’s').toHaveValue(`Tax ${s.marker}`);
        });
    });
});
