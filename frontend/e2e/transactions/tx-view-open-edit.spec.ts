/**
 * The edit pencil of a transaction reached with «Open» in the view window of the Transactions page (lane 66, TL-1c).
 *
 * The view window (`TransactionFormModal mode="view"`) offers «Open» on a charge of a parent and on the parent of a charge
 * (F3, `handleFormOpenTransaction` of `routes/(app)/transactions/+page.svelte`): the same window then shows that
 * transaction, taken from the page's list or, when the list does not hold it, fetched by id. The view's pencil
 * (`onSwitchToEdit` → `handleEditRow` → `openBulk({action: 'edit', txIds: [id]})`) opens the bulk workspace, which resolves
 * its rows only from the client store (`txStore`, filled by the page's load). A row fetched by id is not in the store:
 * the workspace opens without it. TL-1b fixed the same on the broker's tab (`PortfolioTransactionsTab.switchViewToEdit`
 * adds the shown row with `txStoreAddExtras` first); `../brokers/broker-tx-view-edit.spec.ts` (e) is its mirror.
 *
 * How a row shown by «Open» can be missing from this page's list. The broker's tab loads a period, so an old parent is
 * outside it. This page does not: `loadMainRows()` asks `GET /transactions` with no filter, no period and no paging — the
 * whole ledger the user sees — and filters, sorts and pages on the client. A row is missing from the list only when it was
 * saved after the page loaded (another tab, an import, the API). So:
 *
 *   (a) red — the page loaded with a BUY and its FEE and TAX; then a second FEE is saved linked to that BUY (through
 *       the API, as another tab or an import would). The page's list does not hold it: the BUY's charges unfolded show
 *       the first FEE and no row of the late one (the premise, read on the page; with no filter, nothing else could hide
 *       it). The BUY double-clicked → its view reads its charges from the server (`GET ?parent_ids`, asked only when the
 *       row counts charges — why the BUY has some before the load) and lists the late FEE → «Open» on it → the same
 *       window shows it, fetched by id → the pencil → a tap → the late FEE must be open in edit in the workspace (Save
 *       offered, the form a charge of the BUY, its description its own), not an empty workspace.
 *   (b) guard — a BUY with its FEE, both in the list. The FEE (unfolded under the BUY) double-clicked → «Open» on its
 *       parent → the view of the BUY, a row of the list → the pencil → the BUY is open in edit in the workspace.
 *
 * The parent direction of the defect (a FEE in the list, its parent outside it) needs a parent the list does not hold
 * while it holds its charge; on this page a parent saved before the load is loaded with it, so the charge direction (a)
 * is the one a user meets here.
 *
 * testids relied on: transactions-page[data-busy] · tx-table · tbody tr[data-row-id="tx-<id>"] · tx-desc-<id> ·
 * tx-charges-badge-<id>[data-expanded] · tx-form-modal · tx-form-modal-root[data-busy] · tx-form-charges ·
 * tx-form-charge-open-saved-<id> · tx-form-parent[data-parent-id] · tx-form-parent-open · tx-form-description ·
 * tx-form-switch-edit · tx-form-save · tx-form-close · tx-bulk-modal-root · tx-bulk-body tr[data-row-id] with
 * td[data-column-id="id"] reading `#<id>`. Never the translated words.
 *
 * Every test works on an account of its own (`../fixtures/linked-charges.ts`): a disposable user, a broker it owns, a
 * funding DEPOSIT, a BUY and its FEE and TAX ((a): plus the late FEE). Nothing is saved from the edit form. The afterEach
 * deletes what of its rows is left, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, type OwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, seedLinkedBuy} from '../fixtures/linked-charges';

test.setTimeout(90_000);

const txRow = (page: Page, id: number) => page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);

/** The workspace's row of the saved transaction `id`: its id cell reads `#<id>` (a number, not a translated word). */
const savedBulkRow = (page: Page, id: number) =>
    page
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});

/** The Transactions page, loaded (its first load over); ends with the row `anchorId` on screen. */
async function openTransactionsPage(page: Page, anchorId: number): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: 20_000});
    await expect(txRow(page, anchorId), `the row #${anchorId} is on the page`).toBeVisible({timeout: 10_000});
}

/** Unfold the BUY's charges (only if folded); ends with the FEE row on screen, a row of the page's list. */
async function unfoldCharges(page: Page, buyId: number, feeId: number): Promise<void> {
    const badge = txRow(page, buyId).getByTestId(`tx-charges-badge-${buyId}`);
    await expect(badge, 'the BUY carries its charges badge').toBeVisible({timeout: 10_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    await expect(txRow(page, feeId), 'the open badge shows the FEE under the BUY').toBeVisible({timeout: 5_000});
}

/** Double-click a row open; ends on the form in view mode, loaded (nothing to save, the root settled). */
async function openInView(page: Page, row: Locator, txId: number): Promise<void> {
    await row.getByTestId(`tx-desc-${txId}`).dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 8_000});
    await waitForSettled(page.getByTestId('tx-form-modal-root'), 15_000);
    await expect(page.getByTestId('tx-form-close'), 'the view is on screen').toBeVisible();
    await expect(page.getByTestId('tx-form-save'), 'view mode: nothing to save').toBeHidden();
}

/** Tap the view's pencil, which the page offers to who can edit the row's broker. */
async function tapPencil(page: Page, what: string): Promise<void> {
    const pencil = page.getByTestId('tx-form-switch-edit');
    await expect(pencil, `the view of ${what} offers the edit pencil`).toBeVisible({timeout: 5_000});
    await pencil.click();
}

/**
 * After the pencil's tap: the view closed and the row is open in edit, alone, in the workspace (the bulk workspace on one
 * row opens its form directly). The workspace must hold the saved row `rowId` first: an empty workspace opens a blank
 * create form, Save and all, so the form alone proves nothing. `parentId` given: the edit form is a charge of that
 * parent; otherwise it is no charge.
 */
async function expectOpenInEdit(page: Page, rowId: number, description: string, parentId?: number): Promise<void> {
    await expect(page.getByTestId('tx-form-switch-edit'), 'edit mode: the pencil is gone').toHaveCount(0, {timeout: 8_000});
    await expect(page.getByTestId('tx-bulk-modal-root'), 'the pencil opens the workspace, as «Edit» on the row').toBeVisible({timeout: 10_000});
    await expect(savedBulkRow(page, rowId), `the workspace holds the saved row #${rowId} the view showed (not an empty workspace)`).toHaveCount(1, {timeout: 10_000});
    await expect(page.getByTestId('tx-form-save'), 'the row is open in edit: Save is offered').toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('tx-form-modal'), 'one form on screen: the view has closed').toHaveCount(1, {timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    if (parentId !== undefined) {
        await expect(form.getByTestId('tx-form-parent'), 'the edit form is a charge of the BUY').toHaveAttribute('data-parent-id', String(parentId), {timeout: 5_000});
    } else {
        // Presence first (Save above, the description below), then the absence: the BUY is no charge.
        await expect(form.getByTestId('tx-form-parent'), 'the edit form is the BUY, no charge').toHaveCount(0);
    }
    await expect(form.getByTestId('tx-form-description'), 'the edit form is the row the view showed').toHaveValue(description);
}

test.describe('Transactions page — the view reached with «Open» offers a pencil that opens that row in edit (66 TL-1c)', () => {
    let owned: OwnedAccount = emptyOwnedAccount();
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

    test("(a) a second FEE saved after the page loaded, reached with «Open» from its BUY's view: the pencil opens it in edit", async ({page, request}) => {
        // The BUY and its first FEE and TAX are saved before the load: the page's BUY counts charges, so its view reads them.
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tvoa', 'TxVO');
        await openTransactionsPage(page, s.buyId);
        await unfoldCharges(page, s.buyId, s.feeId);

        // After the load: a second FEE saved linked to the BUY, as another tab or an import would.
        const [lateId] = await commitCreates(
            page,
            [{broker_id: s.broker.id, asset_id: s.assetId, type: 'FEE', date: daysAgoIso(5), quantity: '0', cash: {code: 'USD', amount: '-3'}, description: `Late fee ${s.marker}`, parent_transaction_id: s.buyId}],
            'save a second FEE linked to the BUY after the page loaded',
        );
        committedIds.push(lateId);
        const back = await readByIds(page, [s.buyId, lateId]);
        expect(back.get(lateId)?.parent_transaction_id ?? null, 'premise: the late FEE is linked to the BUY on the server').toBe(s.buyId);
        expect(back.get(s.buyId)?.charges_count, 'premise: the BUY counts three charges on the server').toBe(3);

        // The premise on the page: its list does not hold the late FEE. No filter is set and the BUY's charges are
        // unfolded (its first FEE on screen beside it), so nothing else hides it.
        await expect(txRow(page, s.feeId), 'the first FEE is a row of the page, unfolded under the BUY').toBeVisible();
        await expect(txRow(page, lateId), "premise: the late FEE is not in the page's list").toHaveCount(0);

        await openInView(page, txRow(page, s.buyId), s.buyId);
        await expect(page.getByTestId('tx-form-description'), 'the view shows the BUY').toHaveValue(`Buy ${s.marker}`);
        // The view reads the BUY's charges from the server: the late FEE is listed though the page does not hold it.
        const openLate = page.getByTestId('tx-form-charges').getByTestId(`tx-form-charge-open-saved-${lateId}`);
        await expect(openLate, "the BUY's charges section offers «Open» on the late FEE").toBeVisible({timeout: 10_000});
        await openLate.click();

        // The same window now shows the late FEE, fetched by id.
        await expect(page.getByTestId('tx-form-parent'), 'the view now shows a charge of the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
        await expect(page.getByTestId('tx-form-description'), 'the view shows the late FEE').toHaveValue(`Late fee ${s.marker}`);
        await expect(page.getByTestId('tx-form-modal'), '«Open» moves inside the same window').toHaveCount(1);
        await expect(txRow(page, lateId), 'premise: the FEE shown is still not a row of the page').toHaveCount(0);

        await tapPencil(page, 'a FEE outside the list, reached with «Open»');
        await expectOpenInEdit(page, lateId, `Late fee ${s.marker}`, s.buyId);
    });

    test('(b) guard — a BUY in the list, reached with «Open» from its FEE: the pencil opens the BUY in edit', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'tvob', 'TxVO');
        await openTransactionsPage(page, s.buyId);

        await unfoldCharges(page, s.buyId, s.feeId);

        await openInView(page, txRow(page, s.feeId), s.feeId);
        await expect(page.getByTestId('tx-form-description'), 'the view shows the FEE').toHaveValue(`Fee ${s.marker}`);
        const parent = page.getByTestId('tx-form-parent');
        await expect(parent, 'the view shows a charge of the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 5_000});
        await parent.getByTestId('tx-form-parent-open').click();

        await expect(page.getByTestId('tx-form-description'), 'the view now shows the BUY').toHaveValue(`Buy ${s.marker}`, {timeout: 8_000});
        await expect(page.getByTestId('tx-form-modal'), '«Open» moves inside the same window').toHaveCount(1);

        await tapPencil(page, 'a BUY of the list, reached with «Open»');
        await expectOpenInEdit(page, s.buyId, `Buy ${s.marker}`);
    });
});
