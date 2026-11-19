/**
 * Link charges from the transactions table, and delete a parent that has charges (lane 66, lot F6).
 * Contract: `66-F6-contract.md` §1–§5 (decisions U, Z, V1; Bulk choice A).
 *
 *   - «Link» in the selection bar (`toolbar-action-link-charges`): one parent (BUY) + its unlinked FEE and TAX →
 *     the panel `tx-charges-modal` (one column per transaction) → «Link» commits `updates[{id, parent_transaction_id}]`;
 *     the BUY then carries the badge `tx-charges-badge-<id>` and the charges fold under it.
 *   - «Link» is off, with the code `data-disabled-reason="otherBroker"`, when the FEE sits on another broker the user
 *     owns; it is not there at all when the selection holds no charge (two parents).
 *   - Deleting the BUY (row trash or selection bar) while its charges are not all selected opens the panel V1:
 *     «Delete all (3)» → the Bulk with the three rows marked delete; «Keep the charges» → the Bulk with the BUY
 *     alone marked delete and the banner `tx-bulk-unlink-hint` naming the charges, which survive unlinked.
 *   - The BUY selected together with all its charges: no panel, the Bulk opens directly (today's behaviour).
 *   - A mixed selection (BUY + its FEE + an unrelated row, the TAX left out): the panel counts what the page's intent
 *     deletes («Delete all (4)», one charge kept), not «parents + their charges» (3 and 2); «Keep» unlinks the TAX alone.
 *
 * Every test works on an account of its own (a disposable user, brokers it owns, funded by its own DEPOSIT), so no
 * other spec sees its rows and no row of another spec reaches its table. Rows are located by
 * `tbody tr[data-row-id="tx-<id>"]`, the Bulk's staged rows by their status code; nothing counts the table's rows.
 * Server state is read back by id (`GET /transactions?ids=…`). The afterEach deletes whatever of its rows is still
 * there, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker, type OwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';

test.setTimeout(60_000);

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;

/** A transaction read back by id, reduced to what this spec checks. */
type TxLink = {id: number; type: string; broker_id: number; parent_transaction_id?: number | null; charges_count?: number};
/** The wire body of a commit, as the page sends it. */
type CommitPayload = {creates?: unknown[]; updates?: Array<{id: number; parent_transaction_id?: number}>; deletes?: number[]};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids: number[]}>};

/** A funded broker with a BUY, a FEE and a TAX on the same asset and date. */
type Seeded = {broker: OwnedBroker; assetId: number; depositId: number; buyId: number; feeId: number; taxId: number};

const sorted = (ids: number[]): number[] => [...ids].sort((a, b) => a - b);

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/** These transactions as the server has them now; an id that no longer exists is simply absent. */
async function readByIds(page: Page, ids: number[]): Promise<TxLink[]> {
    if (ids.length === 0) return [];
    const query = ids.map((id) => `ids=${id}`).join('&');
    return jsonFrom<TxLink[]>(await page.request.get(`${API}/transactions?${query}`), `read transactions ${ids.join(',')}`);
}

/** Open a disposable account with one broker it owns, funded by its own DEPOSIT. */
async function openFundedAccount(page: Page, request: Parameters<typeof openOwnedAccount>[1], owned: OwnedAccount, committed: number[], tag: string): Promise<{broker: OwnedBroker; assetId: number; depositId: number; marker: string}> {
    const marker = `ChgL ${uniqueSuffix()}`;
    await openOwnedAccount(page, request, owned, tag);
    const broker = await createOwnedBroker(page, tag, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');
    // Fund the broker first: the BUY and its charges take 107 USD out of the cash.
    const [depositId] = await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`}], 'fund the broker');
    committed.push(depositId);
    return {broker, assetId, depositId, marker};
}

/**
 * A funded account with a BUY, a FEE and a TAX on one broker, asset and date. `linked`: the two charges are committed
 * linked to the BUY (`parent_ref`), and the link is read back; otherwise they are three separate rows.
 */
async function seedBuyWithCharges(page: Page, request: Parameters<typeof openOwnedAccount>[1], owned: OwnedAccount, committed: number[], tag: string, linked: boolean): Promise<Seeded> {
    const {broker, assetId, depositId, marker} = await openFundedAccount(page, request, owned, committed, tag);
    const date = daysAgoIso(5);
    const charge = {broker_id: broker.id, asset_id: assetId, date, quantity: '0', ...(linked ? {parent_ref: 'p'} : {})};
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {...(linked ? {ref: 'p'} : {}), broker_id: broker.id, asset_id: assetId, type: 'BUY', date, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
                    {...charge, type: 'FEE', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`},
                    {...charge, type: 'TAX', cash: {code: 'USD', amount: '-2'}, description: `Tax ${marker}`},
                ],
            },
        }),
        'commit the BUY with its charges',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const [buyId, feeId, taxId] = [idAt(0), idAt(1), idAt(2)];
    committed.push(buyId, feeId, taxId);

    // The premise, read back rather than inferred: the charges point at the BUY, or at nothing.
    const parentOf = new Map((await readByIds(page, [feeId, taxId])).map((tx) => [tx.id, tx.parent_transaction_id ?? null] as const));
    const expected = linked ? buyId : null;
    expect([parentOf.get(feeId) ?? null, parentOf.get(taxId) ?? null], `premise: the FEE and the TAX are ${linked ? 'linked to the BUY' : 'unlinked'}`).toEqual([expected, expected]);
    return {broker, assetId, depositId, buyId, feeId, taxId};
}

/** Open /transactions at `query` and wait until every load wave is in. */
async function openTable(page: Page, query = ''): Promise<void> {
    await navigateTo(page, `/transactions${query}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Bring the row checkbox of transaction `id` to `checked`, whatever state it starts in. */
async function ensureChecked(page: Page, id: number): Promise<void> {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
}

/** Bring the row checkbox of transaction `id` to `unchecked`. */
async function ensureUnchecked(page: Page, id: number): Promise<void> {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'unchecked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'unchecked', {timeout: 5_000});
}

/** The selection bar, proved to hold exactly the `n` rows this test ticked. */
async function expectSelection(page: Page, n: number): Promise<Locator> {
    const bar = page.getByTestId('selection-toolbar');
    await expect(bar).toBeVisible({timeout: 5_000});
    await expect(bar).toHaveAttribute('data-selected-count', String(n), {timeout: 5_000});
    return bar;
}

/** Open the BUY row's kebab menu and pick «delete» (the row trash). */
async function deleteFromRow(page: Page, id: number): Promise<void> {
    const row = txRow(page, id);
    await row.hover();
    const kebab = row.getByTestId(`row-actions-tx-${id}`);
    await expect(kebab).toBeVisible({timeout: 3_000});
    await kebab.click();
    const action = page.getByTestId('context-menu-action-delete');
    await expect(action).toBeVisible({timeout: 3_000});
    await action.click();
}

/** The panel V1 for the BUY: its table names the BUY and its two charges, and it offers the two ways out. */
async function expectDeletePanel(page: Page, s: Seeded, all = 3): Promise<Locator> {
    const modal = page.getByTestId('tx-charges-modal');
    await expect(modal, 'the panel «delete a parent with charges» did not open').toBeVisible({timeout: 8_000});
    const table = modal.getByTestId('tx-charges-modal-table');
    await expect(table).toBeVisible({timeout: 5_000});
    for (const id of [s.buyId, s.feeId, s.taxId]) await expect(table).toContainText(`#${id}`);
    await expect(modal.getByTestId('tx-charges-modal-keep')).toBeVisible();
    // «Delete all (N)»: N counts what the choice deletes (the BUY and its two charges, plus any other selected row).
    // A number, never the label.
    await expect(modal.getByTestId('tx-charges-modal-all')).toContainText(new RegExp(`\\b${all}\\b`));
    return modal;
}

/** The Bulk workspace, open and settled (it validates on open; sampling it mid-validation is a race). */
async function expectBulkOpen(page: Page): Promise<Locator> {
    const modal = page.getByTestId('tx-bulk-modal');
    await expect(modal).toBeVisible({timeout: 8_000});
    await waitForSettled(modal.getByTestId('tx-bulk-modal-root'));
    return modal;
}

/** The Bulk's staged rows marked delete, read from the code each row publishes in its status cell. */
function bulkDeletedRows(page: Page): Locator {
    return page.locator('[data-testid="tx-bulk-body"] tr[data-row-id]').filter({has: page.locator('[data-testid="tx-bulk-row-status"][data-status="delete"]')});
}

/** Press «Save all» and return what went on the wire and whether the batch committed. The commit is the subject. */
async function commitBulk(page: Page): Promise<{payload: CommitPayload; committed: boolean}> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const payload = (await requestPromise).postDataJSON() as CommitPayload;
    const body = (await (await responsePromise).json()) as {committed?: boolean};
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});
    return {payload, committed: body.committed === true};
}

test.describe('Transactions table — link charges and delete a parent with charges', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together
    // (a batch naming a row a test already deleted would roll back whole), then the account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (owned.user && committedIds.length > 0) {
                const left = (await readByIds(page, committedIds)).map((tx) => tx.id);
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('Link: a BUY, a FEE and a TAX selected in the table become one BUY with its two charges', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl1', false);

        await openTable(page);
        for (const id of [s.buyId, s.feeId, s.taxId]) await expect(txRow(page, id)).toBeVisible({timeout: 8_000});
        // Unlinked: the BUY has no badge yet.
        await expect(txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`)).toHaveCount(0);

        for (const id of [s.buyId, s.feeId, s.taxId]) await ensureChecked(page, id);
        const bar = await expectSelection(page, 3);
        const link = bar.getByTestId('toolbar-action-link-charges');
        await expect(link, 'the selection bar offers no «Link» for one BUY + a FEE + a TAX').toBeVisible({timeout: 5_000});
        await expect(link).toBeEnabled();
        await expect(link).not.toHaveAttribute('data-disabled-reason', /.+/);
        await link.click();

        const modal = page.getByTestId('tx-charges-modal');
        await expect(modal).toBeVisible({timeout: 8_000});
        const table = modal.getByTestId('tx-charges-modal-table');
        await expect(table).toBeVisible({timeout: 5_000});
        for (const id of [s.buyId, s.feeId, s.taxId]) await expect(table).toContainText(`#${id}`);
        await expect(modal.getByTestId('tx-charges-modal-cancel')).toBeVisible();

        const confirm = modal.getByTestId('tx-charges-modal-confirm');
        await expect(confirm).toBeEnabled({timeout: 5_000});
        const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
        const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
        await confirm.click();
        const payload = (await requestPromise).postDataJSON() as CommitPayload;
        const response = (await (await responsePromise).json()) as {committed?: boolean; issues?: unknown[]};
        expect(response.committed, `the link batch rolled back: ${JSON.stringify(response.issues ?? [])}`).toBe(true);

        // One batch, one update per charge, nothing else.
        const updates = [...(payload.updates ?? [])].sort((a, b) => a.id - b.id);
        expect(updates).toEqual(sorted([s.feeId, s.taxId]).map((id) => ({id, parent_transaction_id: s.buyId})));
        expect(payload.creates ?? []).toEqual([]);
        expect(payload.deletes ?? []).toEqual([]);

        // The panel closes, the page reloads and clears the selection.
        await expect(modal).toBeHidden({timeout: 8_000});
        await expect(page.getByTestId('selection-toolbar')).toBeHidden({timeout: 8_000});
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);

        // The BUY now carries the badge (closed) and its charges are folded under it.
        const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
        await expect(badge).toBeVisible({timeout: 8_000});
        await expect(badge).toHaveAttribute('data-expanded', 'false');
        await expect(txRow(page, s.feeId)).toHaveCount(0);
        await expect(txRow(page, s.taxId)).toHaveCount(0);

        // And on the server: both charges point at the BUY, which counts two.
        const after = new Map((await readByIds(page, [s.buyId, s.feeId, s.taxId])).map((tx) => [tx.id, tx] as const));
        expect(after.get(s.feeId)?.parent_transaction_id).toBe(s.buyId);
        expect(after.get(s.taxId)?.parent_transaction_id).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count).toBe(2);
    });

    test('Link: off with reason otherBroker for a FEE on another broker; absent when the selection has no charge', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl2', false);
        // A second broker the user owns, funded too, with a FEE on the same asset and date as the BUY: only the broker differs.
        const other = await createOwnedBroker(page, 'chgl2-b', owned.brokerIds);
        const [otherDeposit, otherFee] = await commitCreates(
            page,
            [
                {broker_id: other.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '100'}, description: `Deposit other ${s.buyId}`},
                {broker_id: other.id, asset_id: s.assetId, type: 'FEE', date: daysAgoIso(5), quantity: '0', cash: {code: 'USD', amount: '-5'}, description: `Fee other ${s.buyId}`},
            ],
            'fund the other broker and add its FEE',
        );
        committedIds.push(otherDeposit, otherFee);

        await openTable(page);
        await expect(txRow(page, s.buyId)).toBeVisible({timeout: 8_000});
        await expect(txRow(page, otherFee)).toBeVisible({timeout: 8_000});

        // BUY (broker A) + FEE (broker B): «Link» is there, off, and says why with a code.
        await ensureChecked(page, s.buyId);
        await ensureChecked(page, otherFee);
        const bar = await expectSelection(page, 2);
        const link = bar.getByTestId('toolbar-action-link-charges');
        await expect(link, 'the selection bar offers no «Link» for a BUY + a FEE').toBeVisible({timeout: 5_000});
        await expect(link).toBeDisabled();
        await expect(link).toHaveAttribute('data-disabled-reason', 'otherBroker');
        // The page's bar is the floating variant: its tooltip is the native `title`, which names the offending FEE
        // by id (the id, never the translated words). Hovering the disabled button lands on it: it is the hover target.
        await expect(link).toHaveAttribute('title', new RegExp(`#${otherFee}\\b`));
        await link.hover();
        await expect.poll(() => link.evaluate((el) => el.matches(':hover')), {message: 'the disabled «Link» is not the hover target'}).toBe(true);

        // BUY + DEPOSIT: two parents and no charge — «Link» is not offered at all. The barrier: the bar is there,
        // holds the two rows and offers «Delete»; only then does the absence of «Link» mean something.
        await ensureUnchecked(page, otherFee);
        await ensureChecked(page, s.depositId);
        const bar2 = await expectSelection(page, 2);
        await expect(bar2.getByTestId('toolbar-action-delete')).toBeVisible({timeout: 5_000});
        await expect(bar2.getByTestId('toolbar-action-link-charges')).toHaveCount(0);
    });

    test('Delete from the row trash: the panel, «Delete all (3)», the Bulk saves and the three rows are gone', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl3', true);

        await openTable(page);
        const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
        await expect(badge).toBeVisible({timeout: 8_000});

        await deleteFromRow(page, s.buyId);
        const panel = await expectDeletePanel(page, s);
        await panel.getByTestId('tx-charges-modal-all').click();
        await expect(panel).toBeHidden({timeout: 5_000});

        await expectBulkOpen(page);
        // The Bulk holds exactly the batch this choice made: the BUY and its two charges, all marked delete.
        await expect(bulkDeletedRows(page)).toHaveCount(3, {timeout: 8_000});
        await expect(page.getByTestId('tx-bulk-unlink-hint')).toHaveCount(0);

        const {payload, committed} = await commitBulk(page);
        expect(committed, `the delete batch rolled back (deletes=${JSON.stringify(payload.deletes ?? [])})`).toBe(true);
        expect(sorted(payload.deletes ?? [])).toEqual(sorted([s.buyId, s.feeId, s.taxId]));

        await expect(txRow(page, s.buyId)).toHaveCount(0, {timeout: 8_000});
        // On the server, asked about these ids: the three are gone, the DEPOSIT nobody staged is still there.
        const left = (await readByIds(page, [s.depositId, s.buyId, s.feeId, s.taxId])).map((tx) => tx.id);
        expect(left, 'the batch deletes the BUY and its two charges, nothing else').toEqual([s.depositId]);
    });

    test('Delete from the selection bar: «Keep the charges», the Bulk names them, the BUY goes and they stay unlinked', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl4', true);

        await openTable(page);
        await expect(txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`)).toBeVisible({timeout: 8_000});

        await ensureChecked(page, s.buyId);
        const bar = await expectSelection(page, 1);
        const del = bar.getByTestId('toolbar-action-delete');
        await expect(del).toBeEnabled({timeout: 5_000});
        await del.click();

        const panel = await expectDeletePanel(page, s);
        await panel.getByTestId('tx-charges-modal-keep').click();
        await expect(panel).toBeHidden({timeout: 5_000});

        await expectBulkOpen(page);
        // The BUY alone is marked delete; the banner names the two charges that stay.
        await expect(bulkDeletedRows(page)).toHaveCount(1, {timeout: 8_000});
        const hint = page.getByTestId('tx-bulk-unlink-hint');
        await expect(hint, 'the Bulk shows no unlink banner for the kept charges').toBeVisible({timeout: 8_000});
        await expect(hint).toContainText(`#${s.feeId}`);
        await expect(hint).toContainText(`#${s.taxId}`);

        const {payload, committed} = await commitBulk(page);
        expect(committed, `the delete-and-unlink batch rolled back (payload=${JSON.stringify(payload)})`).toBe(true);
        expect(payload.deletes ?? []).toEqual([s.buyId]);
        const unlinks = (payload.updates ?? []).filter((u) => u.parent_transaction_id === 0).map((u) => u.id);
        expect(sorted(unlinks), 'the batch unlinks both charges (parent_transaction_id: 0)').toEqual(sorted([s.feeId, s.taxId]));

        await expect(txRow(page, s.buyId)).toHaveCount(0, {timeout: 8_000});
        // On the server: the BUY is gone, the two charges remain, linked to nothing.
        const after = new Map((await readByIds(page, [s.buyId, s.feeId, s.taxId])).map((tx) => [tx.id, tx] as const));
        expect(after.has(s.buyId), 'the BUY is gone').toBe(false);
        expect(after.has(s.feeId), 'the FEE stays').toBe(true);
        expect(after.has(s.taxId), 'the TAX stays').toBe(true);
        expect(after.get(s.feeId)?.parent_transaction_id ?? null).toBeNull();
        expect(after.get(s.taxId)?.parent_transaction_id ?? null).toBeNull();
        // Unlinked, they are rows of their own in the table again.
        await expect(txRow(page, s.feeId)).toBeVisible({timeout: 8_000});
        await expect(txRow(page, s.taxId)).toBeVisible();
    });

    test('Delete a BUY selected with all its charges: no panel, the Bulk opens directly', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl5', true);

        await openTable(page);
        const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
        await expect(badge).toBeVisible({timeout: 8_000});
        // Open the fold so the two charges are rows that can be ticked.
        if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
        await expect(badge).toHaveAttribute('data-expanded', 'true');
        await expect(txRow(page, s.feeId)).toBeVisible({timeout: 5_000});
        await expect(txRow(page, s.taxId)).toBeVisible();

        for (const id of [s.buyId, s.feeId, s.taxId]) await ensureChecked(page, id);
        const bar = await expectSelection(page, 3);
        const del = bar.getByTestId('toolbar-action-delete');
        await expect(del).toBeEnabled({timeout: 5_000});
        await del.click();

        // The Bulk is the barrier: once it is open and settled, a panel that should have come first would be there.
        await expectBulkOpen(page);
        await expect(page.getByTestId('tx-charges-modal')).toHaveCount(0);
        await expect(bulkDeletedRows(page)).toHaveCount(3, {timeout: 8_000});
        await expect(page.getByTestId('tx-bulk-unlink-hint')).toHaveCount(0);

        const {payload, committed} = await commitBulk(page);
        expect(committed, `the delete batch rolled back (deletes=${JSON.stringify(payload.deletes ?? [])})`).toBe(true);
        expect(sorted(payload.deletes ?? [])).toEqual(sorted([s.buyId, s.feeId, s.taxId]));
        const left = (await readByIds(page, [s.depositId, s.buyId, s.feeId, s.taxId])).map((tx) => tx.id);
        expect(left).toEqual([s.depositId]);
    });

    test('Delete a mixed selection (BUY + FEE + an unrelated row, TAX left out): the panel counts 4, «Keep» unlinks the TAX alone', async ({page, request}) => {
        const s = await seedBuyWithCharges(page, request, owned, committedIds, 'chgl6', true);
        // X: an unrelated row on the same broker. Not the funding DEPOSIT: the TAX survives and needs the cash.
        const [xId] = await commitCreates(page, [{broker_id: s.broker.id, type: 'DEPOSIT', date: daysAgoIso(8), cash: {code: 'USD', amount: '50'}, description: `Deposit X ${s.buyId}`}], 'add the unrelated row X');
        committedIds.push(xId);

        await openTable(page);
        const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
        await expect(badge).toBeVisible({timeout: 8_000});
        // Open the fold so the FEE is a row that can be ticked.
        if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
        await expect(badge).toHaveAttribute('data-expanded', 'true');
        await expect(txRow(page, s.feeId)).toBeVisible({timeout: 5_000});
        await expect(txRow(page, s.taxId)).toBeVisible();
        await expect(txRow(page, xId)).toBeVisible({timeout: 8_000});

        for (const id of [s.buyId, s.feeId, xId]) await ensureChecked(page, id);
        // The premise, checked rather than inferred: ticking the parent did not tick its TAX along.
        await expect(page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${s.taxId}`)).toHaveAttribute('data-state', 'unchecked');
        const bar = await expectSelection(page, 3);
        const del = bar.getByTestId('toolbar-action-delete');
        await expect(del).toBeEnabled({timeout: 5_000});
        await del.click();

        // The numbers come from the intent the Bulk receives, not from «parents + their charges»: «Delete all» deletes
        // BUY, FEE, X and the TAX (4, where parents + charges says 3); «Keep» unlinks the TAX alone (1, where it says 2).
        const panel = await expectDeletePanel(page, s, 4);
        await expect(panel.getByTestId('tx-charges-modal-all-after')).toContainText(/\b4\b/);
        // keepAfter is a plural whose singular form prints no digit in any language: with one charge kept the line
        // holds no number, with two it says «2». Barrier first: «Delete all» above already shows the panel's counts.
        const keepAfter = panel.getByTestId('tx-charges-modal-keep-after');
        await expect(keepAfter).toBeVisible();
        await expect(keepAfter, 'the panel counts two kept charges: it ignored the selected FEE').not.toContainText(/\d/);

        await panel.getByTestId('tx-charges-modal-keep').click();
        await expect(panel).toBeHidden({timeout: 5_000});

        await expectBulkOpen(page);
        // BUY, FEE and X marked delete; the banner names the TAX, which stays, and not the FEE, which goes.
        await expect(bulkDeletedRows(page)).toHaveCount(3, {timeout: 8_000});
        const hint = page.getByTestId('tx-bulk-unlink-hint');
        await expect(hint, 'the Bulk shows no unlink banner for the kept TAX').toBeVisible({timeout: 8_000});
        await expect(hint).toContainText(new RegExp(`#${s.taxId}\\b`));
        await expect(hint).not.toContainText(new RegExp(`#${s.feeId}\\b`));

        const {payload, committed} = await commitBulk(page);
        expect(committed, `the delete-and-unlink batch rolled back (payload=${JSON.stringify(payload)})`).toBe(true);
        expect(sorted(payload.deletes ?? [])).toEqual(sorted([s.buyId, s.feeId, xId]));
        const unlinks = (payload.updates ?? []).filter((u) => u.parent_transaction_id === 0).map((u) => u.id);
        expect(unlinks, 'the batch unlinks the TAX alone (parent_transaction_id: 0)').toEqual([s.taxId]);

        for (const id of [s.buyId, s.feeId, xId]) await expect(txRow(page, id)).toHaveCount(0, {timeout: 8_000});
        // On the server: BUY, FEE and X are gone; the funding DEPOSIT and the TAX remain, the TAX linked to nothing.
        const after = new Map((await readByIds(page, [s.depositId, s.buyId, s.feeId, xId, s.taxId])).map((tx) => [tx.id, tx] as const));
        expect(sorted([...after.keys()]), 'the batch deletes BUY, FEE and X, nothing else').toEqual(sorted([s.depositId, s.taxId]));
        expect(after.get(s.taxId)?.parent_transaction_id ?? null).toBeNull();
        // Unlinked, the TAX is a row of its own in the table again.
        await expect(txRow(page, s.taxId)).toBeVisible({timeout: 8_000});
    });
});
