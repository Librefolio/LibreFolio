/**
 * The transactions table folds a parent's linked charges under it (lane 66, lot F5).
 * Contract: `66-F5-contract.md` (decisions R, S, T).
 *
 * A BUY committed with a FEE and a TAX linked to it (`ref` / `parent_ref`). On /transactions:
 *   - folded by default: the BUY row carries the badge `tx-charges-badge-<id>` (`data-expanded="false"`) and the
 *     charge rows are not in the table; a filter that is not on the type (the account's own broker) keeps the fold;
 *   - a click on the badge shows the two charges, each with its arrow `tx-charge-arrow-<id>`; a second click hides them;
 *   - a type filter = FEE (`types=FEE` in the URL, what the column filter writes) shows the FEE as a row of its own,
 *     with its arrow, and neither the BUY nor the TAX; its 🔗 opens the hidden BUY read-only in the form modal;
 *   - a sort (the cash column) makes the table flat: the three rows are there, and the BUY has no toggle 🔗.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns funded by its own DEPOSIT), so no
 * other spec sees its rows and no row of another spec reaches its table. Rows are located by
 * `tbody tr[data-row-id="tx-<id>"]`; nothing counts the table's rows. It deletes its three rows together, then the
 * account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';

test.setTimeout(60_000);

const COMMIT_PATH = '/api/v1/transactions/commit';

type Charged = {brokerId: number; buyId: number; feeId: number; taxId: number};

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/** Open a disposable account with a funded broker, then commit a BUY with a FEE and a TAX linked to it. */
async function seedChargedBuy(page: Page, request: Parameters<typeof openOwnedAccount>[1], owned: OwnedAccount, committed: number[]): Promise<Charged> {
    const marker = `ChgT ${uniqueSuffix()}`;
    await openOwnedAccount(page, request, owned, 'chgt');
    const broker = await createOwnedBroker(page, 'chgt', owned.brokerIds);
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
                    {...charged, parent_ref: 'p', type: 'FEE', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`},
                    {...charged, parent_ref: 'p', type: 'TAX', cash: {code: 'USD', amount: '-2'}, description: `Tax ${marker}`},
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
    const [buyId, feeId, taxId] = [idAt(0), idAt(1), idAt(2)];
    committed.push(buyId, feeId, taxId);
    return {brokerId: broker.id, buyId, feeId, taxId};
}

/** Open /transactions at `query` and wait until every load wave is in. */
async function openTable(page: Page, query: string): Promise<void> {
    await navigateTo(page, `/transactions${query}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** The charges are folded: the BUY row (presence barrier) carries a closed badge, the charge rows are not drawn. */
async function expectFolded(page: Page, c: Charged): Promise<void> {
    const buy = txRow(page, c.buyId);
    await expect(buy).toBeVisible({timeout: 8_000});
    const badge = buy.getByTestId(`tx-charges-badge-${c.buyId}`);
    await expect(badge).toBeVisible({timeout: 5_000});
    await expect(badge).toHaveAttribute('data-expanded', 'false');
    await expect(txRow(page, c.feeId)).toHaveCount(0);
    await expect(txRow(page, c.taxId)).toHaveCount(0);
}

test.describe('Transactions table — linked charges folded under their parent', () => {
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

    test('the BUY shows a badge, its charges are hidden; the badge opens and closes them', async ({page, request}) => {
        const c = await seedChargedBuy(page, request, owned, committedIds);

        await openTable(page, '');
        await expectFolded(page, c);

        const badge = txRow(page, c.buyId).getByTestId(`tx-charges-badge-${c.buyId}`);
        await badge.click();

        await expect(badge).toHaveAttribute('data-expanded', 'true');
        await expect(txRow(page, c.feeId)).toBeVisible({timeout: 5_000});
        await expect(txRow(page, c.taxId)).toBeVisible();
        await expect(txRow(page, c.feeId).getByTestId(`tx-charge-arrow-${c.feeId}`)).toBeVisible();
        await expect(txRow(page, c.taxId).getByTestId(`tx-charge-arrow-${c.taxId}`)).toBeVisible();

        await badge.click();

        await expect(badge).toHaveAttribute('data-expanded', 'false');
        await expect(txRow(page, c.feeId)).toHaveCount(0);
        await expect(txRow(page, c.taxId)).toHaveCount(0);
        await expect(txRow(page, c.buyId)).toBeVisible();
    });

    test('a filter that is not on the type (the broker) keeps the charges folded', async ({page, request}) => {
        const c = await seedChargedBuy(page, request, owned, committedIds);

        await openTable(page, `?broker_id=${c.brokerId}`);
        await expectFolded(page, c);

        await txRow(page, c.buyId).getByTestId(`tx-charges-badge-${c.buyId}`).click();
        await expect(txRow(page, c.feeId)).toBeVisible({timeout: 5_000});
        await expect(txRow(page, c.taxId)).toBeVisible();
    });

    test('a type filter = FEE shows the FEE as a row of its own, with the arrow', async ({page, request}) => {
        const c = await seedChargedBuy(page, request, owned, committedIds);

        await openTable(page, '?types=FEE');

        const fee = txRow(page, c.feeId);
        await expect(fee).toBeVisible({timeout: 8_000});
        await expect(fee.getByTestId(`tx-charge-arrow-${c.feeId}`)).toBeVisible();
        await expect(txRow(page, c.buyId)).toHaveCount(0);
        await expect(txRow(page, c.taxId)).toHaveCount(0);

        // The FEE's 🔗 leads to its parent; the type filter hides the BUY, so the page opens it read-only in the form.
        await fee.getByTestId(`tx-link-icon-${c.feeId}`).click();
        const form = page.getByTestId('tx-form-modal');
        await expect(form).toBeVisible({timeout: 8_000});
        // The BUY, identified by its own two charges (a charge's view shows `tx-form-parent` instead of this section).
        const charges = form.getByTestId('tx-form-charges');
        await expect(charges).toBeVisible({timeout: 8_000});
        await expect(charges.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${c.feeId}"]`)).toHaveAttribute('data-charge-type', 'FEE', {timeout: 8_000});
        await expect(charges.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${c.taxId}"]`)).toHaveAttribute('data-charge-type', 'TAX');
        await expect(form.getByTestId('tx-form-parent')).toHaveCount(0);
        // Read-only: no save button.
        await expect(form.getByTestId('tx-form-save')).toHaveCount(0);
    });

    test('a sort makes the table flat: the three rows are there, the BUY has no toggle', async ({page, request}) => {
        const c = await seedChargedBuy(page, request, owned, committedIds);

        await openTable(page, '');
        await expectFolded(page, c);

        const header = page.getByTestId('tx-table').getByTestId('dt-header-cash');
        await expect(header).toHaveAttribute('data-sort', 'none');
        await page.getByTestId('tx-table').getByTestId('dt-sort-cash').click();
        await expect(header).not.toHaveAttribute('data-sort', 'none');

        await expect(txRow(page, c.buyId)).toBeVisible({timeout: 5_000});
        await expect(txRow(page, c.feeId)).toBeVisible();
        await expect(txRow(page, c.taxId)).toBeVisible();
        await expect(txRow(page, c.feeId).getByTestId(`tx-charge-arrow-${c.feeId}`)).toBeVisible();
        // Flat: the badge stays as a label, the parent has no 🔗 to open or close anything.
        await expect(txRow(page, c.buyId).getByTestId(`tx-charges-badge-${c.buyId}`)).toBeVisible();
        await expect(txRow(page, c.buyId).locator('[data-tx-charges-toggle]')).toHaveCount(0);
    });
});
