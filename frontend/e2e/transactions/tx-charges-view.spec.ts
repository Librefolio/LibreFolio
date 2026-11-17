/**
 * Linked charges in the transaction form, read-only (lane 66, lot F2b).
 *
 * A BUY committed with a FEE and a TAX linked to it (`ref` / `parent_ref`) is opened from the
 * transactions table in VIEW mode. The «Linked charges» section must list the two charges
 * (id, type, note), offer no «+ Fee» / «+ Tax» button (view is read-only) and show the total
 * charged: 100 + 5 + 2 = 107.
 *
 * testids relied on: tx-table · tbody tr[data-row-id="tx-<id>"] · row-actions-tx-<id> ·
 * context-menu-action-view · tx-form-modal · tx-form-charges · tx-form-charge-row
 * [data-charge-id][data-charge-type] · tx-form-charges-add-FEE · tx-form-charges-total
 * [data-direction] · tx-form-charges-total-<CODE>.
 *
 * The test works on an account of its own (a broker it owns, funded by its own DEPOSIT), so no
 * other spec sees its rows. It deletes the three rows together, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, seededAssetId} from '../fixtures/owned-pair';

test.setTimeout(60_000);

const COMMIT_PATH = '/api/v1/transactions/commit';

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

test.describe('Transaction form — linked charges (view)', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. The three charged rows go together
    // (a parent deleted without its charges is refused), then the account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (committedIds.length > 0) {
                await page.request.post(COMMIT_PATH, {data: {deletes: committedIds}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('a BUY with a FEE and a TAX shows them read-only, with the total charged', async ({page, request}) => {
        const marker = `Chg ${uniqueSuffix()}`;
        await openOwnedAccount(page, request, owned, 'chg');
        const broker = await createOwnedBroker(page, 'chg', owned.brokerIds);
        const assetId = await seededAssetId(page, 'ETH-USD');

        // Fund the broker first: the BUY and its charges take 107 USD out of the cash.
        await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`}], 'fund the broker');

        const date = daysAgoIso(5);
        const charged = {broker_id: broker.id, asset_id: assetId, date, quantity: '0'};
        const body = await jsonFrom<{committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>}>(
            await page.request.post(COMMIT_PATH, {
                data: {
                    creates: [
                        {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
                        {...charged, parent_ref: 'p', type: 'FEE', cash: {code: 'USD', amount: '-5'}, description: `Tobin ${marker}`},
                        {...charged, parent_ref: 'p', type: 'TAX', cash: {code: 'USD', amount: '-2'}, description: `Stamp ${marker}`},
                        // A FEE of the same broker and asset that belongs to no parent: the section must not list it
                        // (it proves the form asks for this parent's charges, not every charge of the user).
                        {...charged, type: 'FEE', cash: {code: 'USD', amount: '-9'}, description: `Unlinked ${marker}`},
                    ],
                },
            }),
            'commit the BUY with its linked charges',
        );
        expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
        const idAt = (index: number): number => {
            const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids[0];
            if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
            return id;
        };
        const [buyId, feeId, taxId, looseId] = [idAt(0), idAt(1), idAt(2), idAt(3)];
        committedIds = [buyId, feeId, taxId, looseId];

        // The table narrowed to the BUY: nothing else moves it, no page hides it.
        await navigateTo(page, `/transactions?id_min=${buyId}&id_max=${buyId}`);
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        const row = txRow(page, buyId);
        await expect(row).toBeVisible({timeout: 8_000});

        // Open it in view mode: every row offers «view» in its kebab menu.
        await row.hover();
        const kebab = row.getByTestId(`row-actions-tx-${buyId}`);
        await expect(kebab).toBeVisible({timeout: 2_000});
        await kebab.click();
        const viewAction = page.getByTestId('context-menu-action-view');
        await expect(viewAction).toBeVisible({timeout: 2_000});
        await viewAction.click();

        const form = page.getByTestId('tx-form-modal');
        await expect(form).toBeVisible({timeout: 5_000});

        const section = form.getByTestId('tx-form-charges');
        await expect(section).toBeVisible({timeout: 8_000});

        // Two charges, identified by id and type — never by position.
        const rows = section.getByTestId('tx-form-charge-row');
        await expect(rows).toHaveCount(2, {timeout: 8_000});
        const feeRowExact = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${feeId}"]`);
        const taxRowExact = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${taxId}"]`);
        await expect(feeRowExact).toHaveAttribute('data-charge-type', 'FEE');
        await expect(taxRowExact).toHaveAttribute('data-charge-type', 'TAX');

        // The FEE row shows its note (the TAX row's too, as plain text: read-only has no input).
        await expect(feeRowExact).toContainText('Tobin');
        await expect(taxRowExact).toContainText('Stamp');

        // View is read-only: nothing to add.
        await expect(section.getByTestId('tx-form-charges-add-FEE')).toHaveCount(0);
        await expect(section.getByTestId('tx-form-charges-add-TAX')).toHaveCount(0);

        // Total charged: 100 + 5 + 2, one amount per currency, an outgoing direction.
        const total = section.getByTestId('tx-form-charges-total');
        await expect(total).toBeVisible();
        await expect(total).toHaveAttribute('data-direction', 'out');
        await expect(total.getByTestId('tx-form-charges-total-USD')).toContainText('107');
    });
});
