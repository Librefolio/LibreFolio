/**
 * «Unlink the charges» from the broker page's Transactions tab, as on the Transactions page (lane 66, lot TL-9).
 *
 * The Transactions page's half (`../transactions/tx-charges-unlink.spec.ts`) proves the mixed selection and the cancel;
 * this one proves the tab offers the same action and reloads after it, on ONE row: a single linked charge is enough,
 * while «Link» needs two. It also keeps the tab's cold path: the flow never asks for the transaction types
 * (`GET /transactions/types`), which this page does not load by itself (brokers-detail 6b).
 *
 *   A saved BUY with its FEE and TAX, the group open, the TAX alone ticked → «Unlink» (1) → the panel in unlink mode →
 *   confirm → the event `tx.charges.unlinked` names the TAX; the selection bar goes, the page settles, the TAX is a row of
 *   its own; on the server the TAX has no parent, the FEE still has, the BUY counts one; the types were never asked for.
 *
 * RED until TL-9: it stops where the bar must offer «Unlink».
 *
 * testids relied on: broker-detail-page[data-busy] · broker-refresh[data-busy] · broker-tab-transazioni ·
 * broker-transactions-tab · broker-transactions · tx-table · tr[data-row-id="tx-<id>"] · dt-row-checkbox-tx-<id>
 * [data-state] · tx-charges-badge-<id>[data-expanded] · tx-charge-arrow-<id> · selection-toolbar[data-selected-count] ·
 * toolbar-action-delete · toolbar-action-unlink-charges · …-count · tx-charges-modal-content[data-mode] ·
 * tx-charges-modal-table tr[data-row-id="parent"] · tx-charges-modal-confirm.
 * The verdict is the server, read back by id, the event's payload and the requests; never the translated words.
 *
 * The test works on an account of its own (`../fixtures/linked-charges.ts`); the afterEach deletes what of its rows is
 * left, together, then the account.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {cleanupOwnedAccount, emptyOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

/** The wire body of a commit, as the page sends it. */
type CommitPayload = {creates?: unknown[]; updates?: unknown[]; deletes?: number[]};

const TYPES_PATH = '/api/v1/transactions/types';

const txTable = (page: Page) => page.getByTestId('broker-transactions');
const tableRow = (page: Page, id: number) => txTable(page).locator(`tr[data-row-id="tx-${id}"]`);

/** The broker's page loaded from scratch on its Transactions tab, the BUY's group open; ends with its charges on screen, each drawn as a charge (`↳`). */
async function openTabOnGroup(page: Page, brokerId: number, buyId: number, chargeIds: number[]): Promise<void> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-detail-page')).toBeVisible({timeout: 20_000});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 10_000});
    await expect(txTable(page).getByTestId('tx-table')).toBeVisible({timeout: 20_000});
    const badge = tableRow(page, buyId).getByTestId(`tx-charges-badge-${buyId}`);
    await expect(badge).toBeVisible({timeout: 10_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    for (const id of chargeIds) await expect(tableRow(page, id).getByTestId(`tx-charge-arrow-${id}`), `#${id} is drawn under its BUY`).toBeVisible({timeout: 5_000});
}

test.describe('Broker page, Transactions tab — «Unlink the charges» from the selection bar, as on the Transactions page', () => {
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

    test('one linked TAX ticked on the tab: «Unlink» → the panel → confirm; the TAX has no parent, the tab reloads, the types are never asked for', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgv1', 'ChgV');
        // From a blank page: the watches see this document's requests alone, nothing the landing page left in flight.
        await page.goto('about:blank');
        const typesAsked: string[] = [];
        const commits: CommitPayload[] = [];
        page.on('request', (req) => {
            const path = new URL(req.url()).pathname;
            if (path === TYPES_PATH) typesAsked.push(`${req.method()} ${path}`);
            if (req.method() === 'POST' && path === COMMIT_PATH) commits.push(req.postDataJSON() as CommitPayload);
        });

        await openTabOnGroup(page, s.broker.id, s.buyId, [s.feeId, s.taxId]);
        const checkbox = txTable(page).getByTestId(`dt-row-checkbox-tx-${s.taxId}`);
        await expect(checkbox).toBeVisible({timeout: 8_000});
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
        const bar = txTable(page).getByTestId('selection-toolbar');
        await expect(bar).toHaveAttribute('data-selected-count', '1', {timeout: 5_000});
        await expect(bar.getByTestId('toolbar-action-delete')).toBeVisible({timeout: 5_000});
        expect(typesAsked, 'premise: the tab opened and one row was ticked without the transaction types').toEqual([]);

        const unlink = bar.getByTestId('toolbar-action-unlink-charges');
        await expect(unlink, '66 TL-9: the tab offers no «Unlink» for a linked charge').toBeVisible({timeout: 5_000});
        await expect(bar.getByTestId('toolbar-action-unlink-charges-count')).toHaveText('1');
        await expect(unlink).toBeEnabled();
        await unlink.click();

        const content = page.getByTestId('tx-charges-modal-content');
        await expect(content).toBeVisible({timeout: 8_000});
        await expect(content).toHaveAttribute('data-mode', 'unlink');
        await expect(content.getByTestId('tx-charges-modal-table').locator('thead')).toContainText(`#${s.taxId}`);
        await expect(content.locator('[data-testid="tx-charges-modal-table"] tbody tr[data-row-id="parent"]')).toContainText(`#${s.buyId}`);
        const confirm = content.getByTestId('tx-charges-modal-confirm');
        await expect(confirm).toBeEnabled({timeout: 5_000});
        expect(commits, 'nothing is saved before the confirmation').toEqual([]);
        const since = await eventSeq(page);
        await confirm.click();

        const event = await waitForEvent(page, 'tx.charges.unlinked', {since, timeout: 15_000});
        expect(event.detail, 'the event names the TAX alone').toEqual({charges: [s.taxId]});
        expect(
            commits.map((c) => ({updates: c.updates ?? [], creates: c.creates ?? [], deletes: c.deletes ?? []})),
            'one commit, for the TAX alone',
        ).toEqual([{updates: [{id: s.taxId, parent_transaction_id: 0}], creates: [], deletes: []}]);
        await expect(content).toBeHidden({timeout: 8_000});

        // The tab itself reloaded (the root publishes the refresh, `broker-refresh` every load of the page): the selection
        // is cleared, the TAX is a row of its own with no `↳`, and the BUY still folds its FEE.
        await expect(bar, 'the selection is cleared after the unlink').toBeHidden({timeout: 8_000});
        await waitForSettled(page.getByTestId('broker-detail-page'), 20_000);
        await waitForSettled(page.getByTestId('broker-refresh'), 20_000);
        await expect(tableRow(page, s.taxId)).toBeVisible({timeout: 10_000});
        await expect(tableRow(page, s.taxId).getByTestId(`tx-charge-arrow-${s.taxId}`), 'the tab did not reload: the TAX is still drawn as a charge').toHaveCount(0, {timeout: 10_000});
        await expect(tableRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`)).toBeVisible();

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])}`;
        expect(after.get(s.taxId), `the TAX is still there: ${dump}`).toBeDefined();
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE still points at the BUY: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count, `the BUY counts one charge: ${dump}`).toBe(1);
        expect(typesAsked, 'the unlink never asks for the transaction types (the page keeps its cold path)').toEqual([]);
    });
});
