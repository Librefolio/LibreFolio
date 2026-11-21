/**
 * No pair-promote for a row that still has linked charges, and «scollega e promuovi» saved (lane 66, lot C21).
 * Contract: `66-C21-promote-contract.md` §4.5 (the model is PC2 of `tx-bulk-promote-cost-basis.spec.ts`).
 *
 * A saved DEPOSIT on broker A with a FEE linked to it, and a saved WITHDRAWAL on broker B that cancels it (a
 * CASH_TRANSFER pair: two brokers, one currency, opposite amounts), both legs with the same note so the merge opens no
 * dialog. Rule 6 of the plan: the DEPOSIT is refused as a leg while it has the FEE, so the Bulk offers nothing; after
 * «scollega» on the FEE (in the DEPOSIT's Form) the editor asks the search again and the banner offers the pair; the
 * merge and «Save all» send the unlink and the promote in one batch (the backend accepts both, 66-R4-R5), and the server
 * holds the pair linked and the FEE with no parent.
 *
 * Red today on its first premise only (soft, so the rest of the flow still runs and reports): the banner offers the
 * merge while the DEPOSIT still holds the FEE. The re-asked search is soft too: today the DEPOSIT is in every request,
 * so whether a request follows the unlink depends on what else changed; after C21 it must.
 *
 * testids relied on: transactions-page · tx-table · dt-row-checkbox-tx-<id> · selection-toolbar[data-selected-count] ·
 * toolbar-action-edit · tx-bulk-modal · tx-bulk-modal-root[data-busy] · tx-bulk-body · tx-bulk-charges-toggle-<rowId>
 * [data-charges-count] · row-actions-<rowId> · context-menu-action-edit-single · tx-form-modal · tx-form-charges
 * [data-state] · tx-form-charge-row[data-charge-id] · tx-form-charge-unlink-<key> · tx-form-save ·
 * tx-bulk-charge-state[data-state] · promote-suggest-banner · promote-suggest-item-<n> · promote-suggest-link-<n> ·
 * promote-merge-modal · tx-bulk-unseen-suggestions · tx-bulk-commit.
 * A Bulk row is found by the `#<id>` its ID cell shows; a promote-suggest request by the ids in its body. The verdict is
 * the server, read back by id.
 *
 * The test works on an account of its own (a disposable user and two brokers it owns): no other spec sees its rows, and
 * no other row of the user can be a candidate of the search. The afterEach deletes the brokers (`force`: their rows go
 * with them), then the account.
 */
import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker, type OwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, emptyOwnedAccount, jsonFrom, openOwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, readByIds, type CommitBody} from '../fixtures/linked-charges';

test.setTimeout(90_000);

const SUGGEST_PATH = '/api/v1/transactions/promote-suggest';
const UI_TIMEOUT = 10_000;
/** A promote-suggest search leaves 500 ms after the change that asks it (debounced): ten debounces bound the wait. */
const SEARCH_TIMEOUT = 5_000;

type SuggestInput = {id: number; type: string};
type PromoteItem = {id_a?: number; id_b?: number};
type CommitRequest = {updates?: Array<Record<string, unknown>>; promotes?: PromoteItem[]; deletes?: number[]};
/** What this test seeds: the DEPOSIT with its FEE on A, the WITHDRAWAL on B, the float that funds B. */
type Seeded = {a: OwnedBroker; b: OwnedBroker; depositId: number; feeId: number; withdrawalId: number; marker: string};

function isSuggestRequest(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === SUGGEST_PATH;
}

function isCommitRequest(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMMIT_PATH;
}

/** The ids a promote-suggest request asks about. */
function askedIds(request: Request): number[] {
    return ((request.postDataJSON() as SuggestInput[] | null) ?? []).map((input) => input.id);
}

/** Seed in one batch: B's float, then the DEPOSIT on A with its FEE (`ref` / `parent_ref`), the WITHDRAWAL on B. */
async function seed(page: Page, a: OwnedBroker, b: OwnedBroker): Promise<Omit<Seeded, 'a' | 'b'>> {
    const marker = `C21 ${uniqueSuffix()}`;
    const date = daysAgoIso(5);
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {broker_id: b.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '500'}, description: `Float ${marker}`},
                    {ref: 'p', broker_id: a.id, type: 'DEPOSIT', date, cash: {code: 'USD', amount: '100'}, description: `Transfer ${marker}`},
                    {broker_id: a.id, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-1'}, parent_ref: 'p', description: `Fee ${marker}`},
                    {broker_id: b.id, type: 'WITHDRAWAL', date, cash: {code: 'USD', amount: '-100'}, description: `Transfer ${marker}`},
                ],
            },
        }),
        'seed the DEPOSIT with its FEE and the WITHDRAWAL',
    );
    expect(body.committed, `seed rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const [depositId, feeId, withdrawalId] = [idAt(1), idAt(2), idAt(3)];

    // The premise, read back rather than inferred: the FEE points at the DEPOSIT, which counts one charge; no pair yet.
    const back = await readByIds(page, [depositId, feeId, withdrawalId]);
    expect(back.get(feeId)?.parent_transaction_id ?? null, 'premise: the FEE is linked to the DEPOSIT').toBe(depositId);
    expect(back.get(depositId)?.charges_count, 'premise: the DEPOSIT counts one charge').toBe(1);
    expect([back.get(depositId)?.type, back.get(withdrawalId)?.type], 'premise: two standalone legs').toEqual(['DEPOSIT', 'WITHDRAWAL']);
    return {depositId, feeId, withdrawalId, marker};
}

/** The Bulk row of saved transaction `id`, found by the `#id` its ID cell shows. */
function bulkRow(page: Page, id: number): Locator {
    return page
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** The chip of a parent row, by the row id the page gives it. */
async function chipOf(page: Page, row: Locator): Promise<Locator> {
    await expect(row).toBeVisible({timeout: UI_TIMEOUT});
    const rowId = await row.getAttribute('data-row-id');
    if (!rowId) throw new Error('the parent row publishes no data-row-id');
    return page.getByTestId(`tx-bulk-charges-toggle-${rowId}`);
}

/** A row's own action, through its ⋮ menu. */
async function rowAction(page: Page, row: Locator, actionId: string): Promise<void> {
    await expect(row).toBeVisible({timeout: UI_TIMEOUT});
    const rowId = await row.getAttribute('data-row-id');
    expect(rowId, 'a Bulk row carries its tempId as data-row-id').toBeTruthy();
    await row.hover();
    const kebab = row.getByTestId(`row-actions-${rowId}`);
    await expect(kebab).toBeVisible({timeout: UI_TIMEOUT});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: UI_TIMEOUT});
    await action.click();
    await expect(action, 'the row menu closes on its action').toBeHidden({timeout: UI_TIMEOUT});
}

test.describe('Bulk — no merge for a leg with linked charges; «scollega» then merge, saved in one batch (C21)', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too. The brokers go with `force`, their rows with them.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('a DEPOSIT with a linked FEE is offered no merge; «scollega» on the FEE brings the offer back; merged and saved: the pair on the server, the FEE with no parent', async ({page, request}) => {
        await openOwnedAccount(page, request, owned, 'c21p');
        const a = await createOwnedBroker(page, 'c21p-a', owned.brokerIds);
        const b = await createOwnedBroker(page, 'c21p-b', owned.brokerIds);
        const s: Seeded = {a, b, ...(await seed(page, a, b))};

        // The table on the two legs; the FEE joins the Bulk through the charges read on entry.
        await navigateTo(page, `/transactions?id_min=${s.depositId}&id_max=${s.withdrawalId}`);
        const transactionsPage = page.getByTestId('transactions-page');
        await waitForSettled(transactionsPage, 20_000);
        for (const id of [s.depositId, s.withdrawalId]) {
            const checkbox = transactionsPage.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
            await expect(checkbox, `#${id} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
            if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
            await expect(checkbox).toHaveAttribute('data-state', 'checked');
        }
        await expect(transactionsPage.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');
        // The opening search, about the WITHDRAWAL (no charge: asked before and after C21), armed before it can leave.
        const openingSearch = page.waitForRequest((req) => isSuggestRequest(req) && askedIds(req).includes(s.withdrawalId), {timeout: 20_000});
        await transactionsPage.getByTestId('toolbar-action-edit').click();
        const bulk = page.getByTestId('tx-bulk-modal');
        await expect(bulk).toBeVisible({timeout: UI_TIMEOUT});
        await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
        await expect(bulkRow(page, s.depositId), 'premise: the DEPOSIT is in the Bulk').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(bulkRow(page, s.withdrawalId), 'premise: the WITHDRAWAL is in the Bulk').toHaveCount(1);
        await expect(await chipOf(page, bulkRow(page, s.depositId)), 'premise: the FEE was read under the DEPOSIT').toHaveAttribute('data-charges-count', '1', {timeout: UI_TIMEOUT});
        await openingSearch;

        // C21: the DEPOSIT holds a linked FEE — no merge offered. Soft: today's red, the flow goes on.
        const banner = page.getByTestId('promote-suggest-banner');
        await expect.soft(banner, 'C21: the banner offers to merge the DEPOSIT while it still holds a linked FEE').toBeHidden();

        // «scollega» on the FEE, in the DEPOSIT's Form; a search that asks about the DEPOSIT must follow the Apply.
        await rowAction(page, bulkRow(page, s.depositId), 'edit-single');
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'the DEPOSIT’s Form').toBeVisible({timeout: UI_TIMEOUT});
        const section = form.getByTestId('tx-form-charges');
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: UI_TIMEOUT});
        const feeRow = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${s.feeId}"]`);
        const unlink = feeRow.locator('[data-testid^="tx-form-charge-unlink-"]');
        await expect(unlink).toBeVisible({timeout: UI_TIMEOUT});
        await unlink.click();
        await expect(feeRow).toHaveCount(0);
        const apply = form.getByTestId('tx-form-save');
        await expect(apply).toBeEnabled({timeout: UI_TIMEOUT});
        // Armed just before the Apply that unlinks: the request it waits for leaves at most one debounce later.
        const reasked = page
            .waitForRequest((req) => isSuggestRequest(req) && askedIds(req).includes(s.depositId), {timeout: SEARCH_TIMEOUT * 2})
            .then(
                () => true,
                () => false,
            );
        await apply.click();
        await expect(form).toBeHidden({timeout: UI_TIMEOUT});
        await expect(bulkRow(page, s.feeId).getByTestId('tx-bulk-charge-state'), 'the FEE is unlinked, a top-level row').toHaveAttribute('data-state', 'unlink', {timeout: UI_TIMEOUT});

        expect.soft(await reasked, 'C21: after «scollega» the editor asks the search again about the DEPOSIT').toBe(true);
        await expect(banner, 'the banner offers the pair').toBeVisible({timeout: UI_TIMEOUT});
        await expect(banner.getByTestId('promote-suggest-item-0')).toBeVisible();
        await expect(banner.getByTestId('promote-suggest-item-1'), 'one pair: the owned account has no other').toHaveCount(0);

        // Merge (same note on both legs: no dialog), then «Save all».
        await banner.getByTestId('promote-suggest-link-0').click();
        await expect(page.getByTestId('promote-merge-modal'), 'same notes: no merge dialog').toBeHidden();
        await expect(banner, 'merged: nothing left to offer').toBeHidden({timeout: UI_TIMEOUT});
        await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
        const commit = bulk.getByTestId('tx-bulk-commit');
        await expect(commit).toBeEnabled({timeout: UI_TIMEOUT});
        const requestPromise = page.waitForRequest(isCommitRequest, {timeout: 20_000});
        const responsePromise = page.waitForResponse((resp) => isCommitRequest(resp.request()), {timeout: 20_000});
        await commit.click();
        // The save reaches the commit, or the save gate opened instead: named, never clicked past.
        const gate = page.getByTestId('tx-bulk-unseen-suggestions');
        const reached = await Promise.race([
            requestPromise.then(() => 'commit' as const),
            gate.waitFor({state: 'visible', timeout: 20_000}).then(
                () => 'gate' as const,
                () => 'neither' as const,
            ),
        ]);
        expect(reached, 'the save gate opened: a suggestion was still on offer after the merge').toBe('commit');
        const payload = (await requestPromise).postDataJSON() as CommitRequest;
        const answer = (await (await responsePromise).json()) as CommitBody;
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(answer)}`;
        expect(answer.committed, `the batch is saved: ${dump}`).toBe(true);
        expect(
            (payload.updates ?? []).filter((update) => update.id === s.feeId),
            `the FEE’s update is its unlink: ${dump}`,
        ).toEqual([{id: s.feeId, parent_transaction_id: 0}]);
        expect(
            (payload.promotes ?? []).map((item) => [item.id_a ?? 0, item.id_b ?? 0].sort((x, y) => x - y)),
            `one promote, the two legs: ${dump}`,
        ).toEqual([[s.depositId, s.withdrawalId].sort((x, y) => x - y)]);
        await expect(bulk, 'a saved batch closes the editor').toBeHidden({timeout: UI_TIMEOUT});

        // The server: the pair linked, the FEE with no parent.
        const after = await readByIds(page, [s.depositId, s.feeId, s.withdrawalId]);
        const server = `server ${JSON.stringify([...after.values()])} — ${dump}`;
        expect(after.get(s.depositId), `the DEPOSIT is a leg of the pair: ${server}`).toMatchObject({type: 'CASH_TRANSFER'});
        expect(after.get(s.withdrawalId), `and so is the WITHDRAWAL: ${server}`).toMatchObject({type: 'CASH_TRANSFER'});
        const legs = await jsonFrom<Array<{id: number; related_transaction_id?: number | null}>>(await page.request.get(`/api/v1/transactions?ids=${s.depositId}&ids=${s.withdrawalId}`), 'read the legs back');
        const linkOf = new Map(legs.map((tx) => [tx.id, tx.related_transaction_id ?? null] as const));
        expect([linkOf.get(s.depositId), linkOf.get(s.withdrawalId)], `the legs point at each other: ${server}`).toEqual([s.withdrawalId, s.depositId]);
        expect(after.get(s.feeId)?.parent_transaction_id ?? null, `the FEE has no parent: ${server}`).toBeNull();
    });
});
