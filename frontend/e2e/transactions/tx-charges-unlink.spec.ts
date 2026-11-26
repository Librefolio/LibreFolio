/**
 * «Unlink the charges» from the Transactions page's selection bar (lane 66, lot TL-9): the sibling of «Link the charges»
 * (`tx-charges-link-delete.spec.ts`). It saves at once, so the panel `TxChargesActionModal mode="unlink"` asks first. The
 * Bulk has its own «Scollega», staged until «Save all» (`tx-bulk-charges-unlink.spec.ts`).
 *
 *   (a) A saved BUY with its FEE and TAX, the group open, the TAX ticked together with the BUY → «Unlink» with the number
 *       1 (a ticked parent drags none of its charges) → the panel in unlink mode: one column, the TAX, its «parent» row
 *       naming the BUY; cancel → nothing saved, the selection kept; again → confirm → ONE commit, the event
 *       `tx.charges.unlinked` names the TAX alone, the selection is empty, the TAX is a row of its own; and on the server
 *       the TAX has no parent, the FEE still has, the BUY counts one charge.
 *   (b) A BUY and a free FEE ticked: no «Unlink» (the bar is drawn and settled on «Link» for these two rows).
 *   (c) On a phone (375 × 812, touch): a BUY and the TAX of ANOTHER BUY ticked → «Link» off (`linked`) and «Unlink» (1)
 *       together in the bar; the page does not scroll sideways, «Unlink» is wholly on screen, its tap opens the panel in
 *       unlink mode; cancel saves nothing (66 TL-11, from TL-9: the code was there, the phone was not proved).
 *
 * RED until TL-9: (a) stops where the bar must offer «Unlink». (b) is a guard, green before and after.
 *
 * testids relied on: transactions-page[data-busy] · tx-table · tr[data-row-id="tx-<id>"] · dt-row-checkbox-tx-<id>
 * [data-state] · tx-charges-badge-<id>[data-expanded] · tx-charge-arrow-<id> · selection-toolbar[data-selected-count] ·
 * toolbar-action-delete · toolbar-action-link-charges · toolbar-action-unlink-charges · …-count · tx-charges-modal-content
 * [data-mode] · tx-charges-modal-table tr[data-row-id="parent"] · tx-charges-modal-target · tx-charges-modal-cancel ·
 * tx-charges-modal-confirm.
 * The verdict is the server, read back by id, the event's payload and what went on the wire; never the translated words.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, together, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedBuyAndFreeFee, seedLinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** The wire body of a commit, as the page sends it. */
type CommitPayload = {creates?: unknown[]; updates?: unknown[]; deletes?: number[]};

/** The table row of transaction `id`. */
const txRow = (page: Page, id: number): Locator => page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);

/** Open /transactions and wait until every load wave is in. */
async function openTable(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Tick a row; ends checked. */
async function ensureChecked(page: Page, id: number): Promise<void> {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
}

/** The selection bar, proved to hold exactly the `n` rows this test ticked and to offer «Delete» (the barrier of an absence). */
async function expectSelection(page: Page, n: number): Promise<Locator> {
    const bar = page.getByTestId('selection-toolbar');
    await expect(bar).toHaveAttribute('data-selected-count', String(n), {timeout: 5_000});
    await expect(bar.getByTestId('toolbar-action-delete')).toBeVisible({timeout: 5_000});
    return bar;
}

/** Open the group of a BUY; ends with its charges on screen, each drawn as a charge (`↳`). */
async function openGroup(page: Page, buyId: number, chargeIds: number[]): Promise<void> {
    const badge = txRow(page, buyId).getByTestId(`tx-charges-badge-${buyId}`);
    await expect(badge).toBeVisible({timeout: 8_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    for (const id of chargeIds) await expect(txRow(page, id).getByTestId(`tx-charge-arrow-${id}`), `#${id} is drawn under its BUY`).toBeVisible({timeout: 5_000});
}

/** «Unlink» in the bar: there, on, with the number of charges it takes. */
async function expectUnlink(bar: Locator, count: number): Promise<Locator> {
    const unlink = bar.getByTestId('toolbar-action-unlink-charges');
    await expect(unlink, '66 TL-9: the selection bar offers no «Unlink» for a linked charge').toBeVisible({timeout: 5_000});
    await expect(bar.getByTestId('toolbar-action-unlink-charges-count')).toHaveText(String(count));
    await expect(unlink).toBeEnabled();
    await expect(unlink).not.toHaveAttribute('data-disabled-reason', /.+/);
    return unlink;
}

/** The panel in unlink mode, for one charge of one parent: the charge is its only column, the parent is named by its `#id`. */
async function expectUnlinkPanel(page: Page, chargeId: number, parentId: number, others: number[]): Promise<Locator> {
    const content = page.getByTestId('tx-charges-modal-content');
    await expect(content).toBeVisible({timeout: 8_000});
    await expect(content).toHaveAttribute('data-mode', 'unlink');
    const table = content.getByTestId('tx-charges-modal-table');
    await expect(table.locator('thead')).toContainText(`#${chargeId}`);
    for (const id of others) await expect(table.locator('thead'), `#${id} is no column of the panel`).not.toContainText(`#${id}`);
    await expect(table.locator('tbody tr[data-row-id="parent"]')).toContainText(`#${parentId}`);
    await expect(content.getByTestId('tx-charges-modal-target')).toBeVisible();
    await expect(content.getByTestId('tx-charges-modal-confirm')).toBeEnabled({timeout: 5_000});
    return content;
}

test.describe('Transactions page — «Unlink the charges» from the selection bar', () => {
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

    test('(a) the TAX ticked with its BUY: «Unlink» takes the TAX alone; cancel saves nothing, confirm unlinks it', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu1', 'ChgU');
        // What the page itself commits (the seed went through `page.request`, which fires no page event).
        const commits: CommitPayload[] = [];
        page.on('request', (req) => {
            if (req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH) commits.push(req.postDataJSON() as CommitPayload);
        });

        await openTable(page);
        await openGroup(page, s.buyId, [s.feeId, s.taxId]);
        await ensureChecked(page, s.buyId);
        await ensureChecked(page, s.taxId);
        const bar = await expectSelection(page, 2);
        await (await expectUnlink(bar, 1)).click();

        // Cancel: the panel closes, nothing is saved, the selection stays.
        const content = await expectUnlinkPanel(page, s.taxId, s.buyId, [s.buyId, s.feeId]);
        await content.getByTestId('tx-charges-modal-cancel').click();
        await expect(content).toBeHidden({timeout: 8_000});
        const kept = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        expect([kept.get(s.feeId)?.parent_transaction_id ?? null, kept.get(s.taxId)?.parent_transaction_id ?? null], 'cancelled: both charges still point at the BUY').toEqual([s.buyId, s.buyId]);
        expect(commits, 'cancelled: the page committed nothing').toEqual([]);
        await expectSelection(page, 2);

        // Again, to the end.
        await (await expectUnlink(bar, 1)).click();
        await expectUnlinkPanel(page, s.taxId, s.buyId, [s.buyId, s.feeId]);
        const since = await eventSeq(page);
        await content.getByTestId('tx-charges-modal-confirm').click();

        const event = await waitForEvent(page, 'tx.charges.unlinked', {since, timeout: 15_000});
        expect(event.detail, 'the event names the TAX alone').toEqual({charges: [s.taxId]});
        expect(
            commits.map((c) => ({updates: c.updates ?? [], creates: c.creates ?? [], deletes: c.deletes ?? []})),
            'one commit, for the TAX alone',
        ).toEqual([{updates: [{id: s.taxId, parent_transaction_id: 0}], creates: [], deletes: []}]);

        // The panel closes, the selection is emptied and the page reloads: the TAX is a row of its own, with no `↳`, and
        // the BUY still folds its FEE.
        await expect(content).toBeHidden({timeout: 8_000});
        await expect(page.getByTestId('selection-toolbar'), 'the selection is cleared').toBeHidden({timeout: 8_000});
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        await expect(txRow(page, s.taxId)).toBeVisible({timeout: 8_000});
        await expect(txRow(page, s.taxId).getByTestId(`tx-charge-arrow-${s.taxId}`), 'the TAX is still drawn as a charge').toHaveCount(0);
        await expect(txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`)).toBeVisible();

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])}`;
        expect(after.get(s.taxId), `the TAX is still there: ${dump}`).toBeDefined();
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE still points at the BUY: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count, `the BUY counts one charge: ${dump}`).toBe(1);
    });

    test('(b) guard: a BUY and a free FEE ticked: no «Unlink»', async ({page, request}) => {
        const s = await seedBuyAndFreeFee(page, request, owned, committedIds, 'chgu2', 'ChgU');

        await openTable(page);
        await expect(txRow(page, s.buyId)).toBeVisible({timeout: 8_000});
        await ensureChecked(page, s.buyId);
        await ensureChecked(page, s.feeId);
        const bar = await expectSelection(page, 2);
        // The barrier: the bar has resolved its actions on these two rows, «Link» among them.
        await expect(bar.getByTestId('toolbar-action-link-charges')).toBeVisible({timeout: 5_000});
        await expect(bar.getByTestId('toolbar-action-unlink-charges')).toHaveCount(0);
    });

    // A context of its own (375 × 812, a touch screen), nested so it keeps this block's cleanup.
    test.describe('on a phone', () => {
        test.use({viewport: {width: 375, height: 812}, isMobile: true, hasTouch: true});
        // Infrastructure, not data: both projects of playwright.config.ts run Chromium, so this never skips there.
        test.skip(({browserName}) => browserName !== 'chromium', 'isMobile and the touch screen are Chromium emulation here');

        test('(c) a BUY and the TAX of another BUY ticked: «Link» off and «Unlink» (1) share the bar, the page does not scroll sideways, «Unlink» is tapped; cancel saves nothing', async ({page, request}) => {
            const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgu3', 'ChgU');
            const [otherBuyId] = await commitCreates(page, [{broker_id: s.broker.id, asset_id: s.assetId, type: 'BUY', date: daysAgoIso(4), quantity: '5', cash: {code: 'USD', amount: '-50'}, description: `Other buy ${s.marker}`}], 'commit another BUY');
            committedIds.push(otherBuyId);
            const commits: CommitPayload[] = [];
            page.on('request', (req) => {
                if (req.method() === 'POST' && new URL(req.url()).pathname === COMMIT_PATH) commits.push(req.postDataJSON() as CommitPayload);
            });

            await openTable(page);
            const device = await page.evaluate(() => ({touchPoints: navigator.maxTouchPoints, phone: window.matchMedia('(max-width: 639px)').matches}));
            expect(device.touchPoints, 'the page must see a touch screen (hasTouch)').toBeGreaterThan(0);
            expect(device.phone, 'the page must be drawn at phone width, below 640 px').toBe(true);
            await openGroup(page, s.buyId, [s.feeId, s.taxId]);
            for (const id of [otherBuyId, s.taxId]) {
                const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
                await expect(checkbox).toHaveAttribute('data-state', 'unchecked', {timeout: 5_000});
                await checkbox.tap();
                await expect(checkbox, 'a tap on its checkbox ticks the row').toHaveAttribute('data-state', 'checked', {timeout: 5_000});
            }

            const bar = await expectSelection(page, 2);
            const link = bar.getByTestId('toolbar-action-link-charges');
            await expect(link, '«Link» is in the bar, off').toBeVisible({timeout: 5_000});
            await expect(link).toHaveAttribute('data-disabled-reason', 'linked');
            const unlink = await expectUnlink(bar, 1);

            // The bar has no overflow control (DataTableToolbar): every action is drawn, so both must fit the screen.
            const doc = await page.evaluate(() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth}));
            expect(doc.scroll, `the page scrolls sideways: scrollWidth ${doc.scroll}, clientWidth ${doc.client}`).toBeLessThanOrEqual(doc.client + 1);
            for (const action of [link, unlink]) await expect(action, 'wholly on screen').toBeInViewport({ratio: 0.99});

            await unlink.tap();
            const content = await expectUnlinkPanel(page, s.taxId, s.buyId, [s.feeId, otherBuyId]);
            const panelDoc = await page.evaluate(() => ({scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth}));
            expect(panelDoc.scroll, `with the panel open the page scrolls sideways: ${JSON.stringify(panelDoc)}`).toBeLessThanOrEqual(panelDoc.client + 1);

            await content.getByTestId('tx-charges-modal-cancel').tap();
            await expect(content).toBeHidden({timeout: 8_000});
            expect(commits, 'cancelled: the page committed nothing').toEqual([]);
            const kept = await readByIds(page, [s.feeId, s.taxId]);
            expect([kept.get(s.feeId)?.parent_transaction_id ?? null, kept.get(s.taxId)?.parent_transaction_id ?? null], 'both charges still point at their BUY').toEqual([s.buyId, s.buyId]);
            await expectSelection(page, 2);
        });
    });
});
