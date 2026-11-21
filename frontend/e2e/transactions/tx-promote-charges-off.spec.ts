/**
 * «Link as pair» on the Transactions page, off with its reason when a leg has linked charges (lane 66, lot C22).
 * Contract: `66-C22-contract.md` §1.3 and §2.3 (`66-C21-promote-contract.md` §5.1: the merge off in the Bulk and on the
 * page). The Bulk's twin is a component test: `TransactionBulkModal.test.ts`, describe «66 C22».
 *
 * Two saved rows that make a CASH_TRANSFER pair (a DEPOSIT on broker A, the WITHDRAWAL on broker B that cancels it, same
 * note so the page goes straight to its plain confirmation). With a FEE linked to the DEPOSIT (`charges_count` 1 on the
 * page's row) rule 6 refuses the merge: the page must say so before the user asks, not leave it to the backend
 * (`chargesBlockParentType`). `promoteMatch` is unchanged; the action `promote` of the selection bar is drawn off, the
 * F7-a way (`aria-disabled`, the shared Tooltip, `data-disabled-reason`), with the reason
 * `transactions.promote.chargesBlock` naming the DEPOSIT by its ref (`#<id>`).
 *
 * Red today on the first test only: the page offers «Link as pair» on, and its click opens the confirmation. The second
 * test is a guard, green before and after: without a charge the action is on and opens the confirmation (Cancel).
 *
 * testids relied on: transactions-page[data-busy] · tx-table · dt-row-checkbox-tx-<id> · selection-toolbar
 * [data-selected-count] · toolbar-action-promote[aria-disabled][data-disabled-reason] · toolbar-action-delete ·
 * tooltip-content · confirm-modal-confirm · confirm-modal-cancel · promote-merge-modal.
 * The reason is told from other tooltips by the ref it names (`#<id>`), never by its translated words.
 *
 * Each test works on an account of its own (a disposable user and two brokers it owns), and seeds the rows it reads.
 * The afterEach deletes the account and its brokers (`force`: their rows go with them). Nothing here commits a merge.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, openOwnedAccount} from '../fixtures/owned-pair';
import {readByIds} from '../fixtures/linked-charges';

test.setTimeout(60_000);

const UI_TIMEOUT = 10_000;

/** The rows a test seeded: the two legs, and the FEE of the DEPOSIT when it has one. */
type Seeded = {depositId: number; withdrawalId: number; feeId: number | null};

/**
 * Seed in one batch on two brokers of the account: B's float (so the WITHDRAWAL never overdraws), the DEPOSIT on A —
 * with a FEE linked to it (`ref` / `parent_ref`) when `withFee` — and the WITHDRAWAL on B that cancels it, same note.
 * Reads the premise back from the server rather than inferring it.
 */
async function seed(page: Page, brokers: {a: number; b: number}, withFee: boolean): Promise<Seeded> {
    const marker = `C22 ${uniqueSuffix()}`;
    const date = daysAgoIso(5);
    const creates: Array<Record<string, unknown>> = [
        {broker_id: brokers.b, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '500'}, description: `Float ${marker}`},
        {...(withFee ? {ref: 'p'} : {}), broker_id: brokers.a, type: 'DEPOSIT', date, cash: {code: 'USD', amount: '100'}, description: `Transfer ${marker}`},
        {broker_id: brokers.b, type: 'WITHDRAWAL', date, cash: {code: 'USD', amount: '-100'}, description: `Transfer ${marker}`},
        ...(withFee ? [{broker_id: brokers.a, type: 'FEE', date, quantity: '0', cash: {code: 'USD', amount: '-1'}, parent_ref: 'p', description: `Fee ${marker}`}] : []),
    ];
    const ids = await commitCreates(page, creates, 'seed the two legs');
    const s: Seeded = {depositId: ids[1], withdrawalId: ids[2], feeId: withFee ? ids[3] : null};

    const back = await readByIds(page, [s.depositId, s.withdrawalId, ...(s.feeId !== null ? [s.feeId] : [])]);
    expect([back.get(s.depositId)?.type, back.get(s.withdrawalId)?.type], 'premise: two standalone legs').toEqual(['DEPOSIT', 'WITHDRAWAL']);
    expect(back.get(s.depositId)?.charges_count ?? 0, 'premise: the DEPOSIT counts its charges').toBe(withFee ? 1 : 0);
    if (s.feeId !== null) expect(back.get(s.feeId)?.parent_transaction_id ?? null, 'premise: the FEE is linked to the DEPOSIT').toBe(s.depositId);
    return s;
}

/** The Transactions page on the two legs, both ticked; ends on the selection bar holding exactly them. */
async function selectLegs(page: Page, s: Seeded): Promise<Locator> {
    const ids = [s.depositId, s.withdrawalId].sort((x, y) => x - y);
    await navigateTo(page, `/transactions?id_min=${ids[0]}&id_max=${ids[1]}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await waitForSettled(transactionsPage, 20_000);
    for (const id of ids) {
        const checkbox = transactionsPage.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
        await expect(checkbox, `#${id} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const bar = transactionsPage.getByTestId('selection-toolbar');
    await expect(bar).toHaveAttribute('data-selected-count', '2', {timeout: UI_TIMEOUT});
    // The barrier: the bar answers this selection (its «Delete» is there) before any presence or absence is read.
    await expect(bar.getByTestId('toolbar-action-delete')).toBeVisible({timeout: UI_TIMEOUT});
    return bar;
}

test.describe('Transactions page — «Link as pair» off when a leg has linked charges (C22)', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too. The brokers go with `force`, their rows with them.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('a DEPOSIT with a linked FEE and the WITHDRAWAL that cancels it: «Link as pair» is off (hasCharges); a click opens its reason, naming the DEPOSIT, and no dialog', async ({page, request}) => {
        await openOwnedAccount(page, request, owned, 'c22p');
        const a = await createOwnedBroker(page, 'c22p-a', owned.brokerIds);
        const b = await createOwnedBroker(page, 'c22p-b', owned.brokerIds);
        const s = await seed(page, {a: a.id, b: b.id}, true);
        const bar = await selectLegs(page, s);

        const promote = bar.getByTestId('toolbar-action-promote');
        await expect(promote, 'the two rows match a promote rule: the action is drawn').toBeVisible({timeout: UI_TIMEOUT});
        // Off but reachable (F7-a): `aria-disabled`, not the native `disabled`; the code says why.
        await expect(promote, 'C22: «Link as pair» is offered on while the DEPOSIT holds a linked FEE').toHaveAttribute('aria-disabled', 'true');
        await expect(promote).not.toHaveAttribute('disabled');
        await expect(promote).toHaveAttribute('data-disabled-reason', 'hasCharges');

        // The reason names the DEPOSIT (the first row with charges) by its ref; tooltips are portaled to the body and all
        // named `tooltip-content`, so it is filtered by that ref.
        const reason = page.getByTestId('tooltip-content').filter({hasText: new RegExp(`#${s.depositId}\\b`)});
        // `force`: Playwright's click waits for an enabled element and counts `aria-disabled` as disabled; the hover
        // (which does not wait) proves first that the pointer lands on the action.
        await promote.hover();
        await expect.poll(() => promote.evaluate((el) => el.matches(':hover')), {message: 'the disabled «Link as pair» is not the hover target'}).toBe(true);
        await promote.click({force: true});
        await expect(reason, 'a click on the disabled «Link as pair» opened no reason').toBeVisible({timeout: 5_000});
        // The barrier is the open reason: the click was handled, and the page opens its dialogs synchronously from it.
        await expect(page.getByTestId('confirm-modal-confirm'), 'a click on the disabled «Link as pair» opened the confirmation').toHaveCount(0);
        await expect(page.getByTestId('promote-merge-modal'), 'and no merge dialog').toBeHidden();

        // Nothing changed on the server: still two standalone legs.
        const after = await readByIds(page, [s.depositId, s.withdrawalId]);
        expect([after.get(s.depositId)?.type, after.get(s.withdrawalId)?.type], 'nothing merged').toEqual(['DEPOSIT', 'WITHDRAWAL']);
    });

    test('guard: the same pair without a charge — «Link as pair» is on (no reason) and opens the confirmation', async ({page, request}) => {
        await openOwnedAccount(page, request, owned, 'c22q');
        const a = await createOwnedBroker(page, 'c22q-a', owned.brokerIds);
        const b = await createOwnedBroker(page, 'c22q-b', owned.brokerIds);
        const s = await seed(page, {a: a.id, b: b.id}, false);
        const bar = await selectLegs(page, s);

        const promote = bar.getByTestId('toolbar-action-promote');
        await expect(promote, 'the two rows match a promote rule').toBeVisible({timeout: UI_TIMEOUT});
        await expect(promote).not.toHaveAttribute('aria-disabled', 'true');
        await expect(promote).not.toHaveAttribute('data-disabled-reason', /.+/);
        await promote.click();
        const confirm = page.getByTestId('confirm-modal-confirm');
        await expect(confirm, 'same notes: the plain confirmation opens').toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirm).toHaveCount(0, {timeout: UI_TIMEOUT});
    });
});
