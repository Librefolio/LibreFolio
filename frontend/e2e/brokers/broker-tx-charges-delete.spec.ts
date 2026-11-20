/**
 * The broker page's Transactions tab deletes a parent with charges the way the Transactions page does (lane 66, lot
 * F7-d). Contract: `66-F7-contract.md` §20.1 (corrected by §21.5), closing §18.6.
 *
 * Until F7-d the tab opened the Bulk with the delete intent and no question: the charges ended «unlink», a silent
 * «Keep». Now «Delete» from the tab goes through the shared flow (`chargesDeleteFlow.svelte.ts`): the panel V1
 * (`tx-charges-modal-content`, `data-mode="deleteParent"`) opens before the Bulk.
 *
 *   (a) The row menu → «Delete» on a BUY with a FEE and a TAX → the panel, no Bulk yet → «Keep» → the Bulk → «Save all»
 *       → on the server the BUY is gone, the FEE and the TAX stay with no parent.
 *   (b) The selection bar → «Delete» on the BUY → the panel → «Delete all» → «Save all» → all three are gone.
 *
 * testids relied on: broker-detail-page · broker-tab-transazioni · broker-transactions-tab · broker-transactions ·
 * tx-table · tr[data-row-id="tx-<id>"] · row-actions-tx-<id> · context-menu · context-menu-action-delete ·
 * dt-row-checkbox-tx-<id> · selection-toolbar · toolbar-action-delete · tx-charges-modal ·
 * tx-charges-modal-content[data-mode] · tx-charges-modal-keep · tx-charges-modal-all · tx-bulk-modal ·
 * tx-bulk-modal-root · tx-bulk-commit.
 * The verdict is the server, read back by id.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`): a disposable user, a broker it owns, a
 * funding DEPOSIT and the BUY with its two charges. The afterEach deletes what of its rows is left, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {cleanupOwnedAccount, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy, type CommitBody, type LinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

const txTable = (page: Page) => page.getByTestId('broker-transactions');
const tableRow = (page: Page, id: number) => txTable(page).locator(`tr[data-row-id="tx-${id}"]`);

/** The broker's page on the Transactions tab; ends with the BUY on screen. */
async function openTransactionsTab(page: Page, s: LinkedBuy): Promise<void> {
    await navigateTo(page, `/brokers/${s.broker.id}`);
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 10_000});
    await expect(txTable(page).getByTestId('tx-table')).toBeVisible({timeout: 20_000});
    await expect(tableRow(page, s.buyId), 'the BUY is on the tab').toBeVisible({timeout: 10_000});
}

/** The panel V1 is open in deleteParent mode, and the Bulk is not: the question comes first. */
async function expectPanelBeforeBulk(page: Page): Promise<Locator> {
    const content = page.getByTestId('tx-charges-modal-content');
    await expect(content, '«Delete» on a parent with charges opened no panel: the tab went straight to the Bulk').toBeVisible({timeout: 8_000});
    await expect(content).toHaveAttribute('data-mode', 'deleteParent');
    await expect(page.getByTestId('tx-bulk-modal'), 'the Bulk waits for the choice').toHaveCount(0);
    return content;
}

/** «Save all» in the Bulk; the commit must succeed. */
async function saveAll(page: Page): Promise<unknown> {
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
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

test.describe('Broker page, Transactions tab — «Delete» on a parent with charges asks first (V1)', () => {
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

    test('(a) row menu «Delete» on the BUY: the panel before the Bulk; «Keep» → Save all: the BUY goes, its charges stay with no parent', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgb1', 'ChgB');
        await openTransactionsTab(page, s);

        await txTable(page).getByTestId(`row-actions-tx-${s.buyId}`).click();
        const menu = page.getByTestId('context-menu');
        await expect(menu).toBeVisible({timeout: 5_000});
        await menu.getByTestId('context-menu-action-delete').click();

        const content = await expectPanelBeforeBulk(page);
        await content.getByTestId('tx-charges-modal-keep').click();
        await expect(content).toBeHidden({timeout: 5_000});
        const payload = await saveAll(page);

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.has(s.buyId), `the BUY is gone: ${dump}`).toBe(false);
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE stays, with no parent: ${dump}`).toBeNull();
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX stays, with no parent: ${dump}`).toBeNull();
        expect(after.has(s.feeId) && after.has(s.taxId), `both charges stay: ${dump}`).toBe(true);
    });

    test('(b) selection bar «Delete» on the BUY: the panel before the Bulk; «Delete all» → Save all: all three are gone', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgb2', 'ChgB');
        await openTransactionsTab(page, s);

        const checkbox = txTable(page).getByTestId(`dt-row-checkbox-tx-${s.buyId}`);
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
        const bar = txTable(page).getByTestId('selection-toolbar');
        await expect(bar).toHaveAttribute('data-selected-count', '1', {timeout: 5_000});
        await bar.getByTestId('toolbar-action-delete').click();

        const content = await expectPanelBeforeBulk(page);
        await content.getByTestId('tx-charges-modal-all').click();
        await expect(content).toBeHidden({timeout: 5_000});
        const payload = await saveAll(page);

        const after = await readByIds(page, [s.depositId, s.buyId, s.feeId, s.taxId]);
        expect([...after.keys()], `the batch deletes the BUY and its two charges, nothing else — payload ${JSON.stringify(payload)}`).toEqual([s.depositId]);
    });
});
