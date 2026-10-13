/**
 * Transaction Split & Promote E2E Tests — Plan D2 Step F14
 *
 * Covers:
 * 1. Split from Main Table → confirm modal appears
 * 2. Guard: split hidden on standalone
 * 3. Guard: promote hidden on paired
 * 4. Promote from Main Table → select 2 promote-test rows
 * 5. BulkModal open after page refresh (NR-1 non-regression for F6)
 * 6. C3: split + edit in the BulkModal → commit payload (on a pair the test owns)
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Mock data contract: populate_mock_data.py creates, among others:
 * - "[Asym-a] …": an AAPL TRANSFER pair IB (OWNER) ↔ Directa (EDITOR), tagged "access-test" —
 *   a pair e2e_test_user can edit on both sides, so its menu offers split;
 * - "Initial EUR funding from bank": a standalone DEPOSIT on IB (OWNER);
 * - "promote-test" tag on standalone DEPOSIT/WITHDRAWAL for promote candidates
 *   (Coinbase/EDITOR + IB/OWNER — both editable by e2e_test_user)
 * - "promote-test-access-fail" tag on DEPOSIT/WITHDRAWAL where one broker is VIEWER
 *
 * Tests 1-5 only read mock data, and never by position: each finds its rows through the API
 * by the marker the seed gives them, checks the state it needs (linked, standalone, editable)
 * and opens the table narrowed to those ids. C3 commits — a real split and a real edit — so it
 * never touches a mock row: it builds its own pair on a disposable account (two brokers the
 * account owns, the seeded Ethereum as the asset; fixtures/owned-pair.ts) and deletes the
 * account afterwards, its brokers and every row on them included.
 *
 * DOM patterns (DataTable + TransactionsTable):
 * - Table wrapper: [data-testid="tx-table"]
 * - Row: tr[data-row-id="tx-{id}"] or tr[data-row-id="ghost-{id}"]
 * - Checkbox: [data-testid="dt-row-checkbox-{row-id}"], data-state checked|unchecked
 * - Link indicator: [data-testid="tx-link-icon-{id}"]
 * - Row actions: kebab button [data-testid="row-actions-{row-id}"] → opens context menu with
 *   items at [data-testid="context-menu-action-{id}"] (e.g. "split", "edit", "view").
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {canEdit, cleanupOwnedAccount, emptyOwnedAccount, listBrokers, openAccountWithPair, readTransactions, seededPair, seededRow, type TxRow} from '../fixtures/owned-pair';

test.setTimeout(30_000);

/** The seeded pair the read-only tests borrow: e2e_test_user can edit both of its sides. */
const EDITABLE_PAIR = '[Asym-a]';
/** The seeded standalone row they borrow, on a broker e2e_test_user owns. */
const EDITABLE_STANDALONE = 'Initial EUR funding from bank';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page, query = '?page_size=200') {
    await navigateTo(page, `/transactions${query}`);
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/** The table row of transaction `id`. */
function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/**
 * Open the table narrowed to these transactions (`id_min`/`id_max`) and wait for each of their
 * rows. The narrowed table holds nothing but that range, so no neighbour's row moves them and no
 * page boundary hides them.
 */
async function goToRows(page: Page, ids: number[]) {
    await goToTransactions(page, `?id_min=${Math.min(...ids)}&id_max=${Math.max(...ids)}`);
    for (const id of ids) await expect(txRow(page, id), `transaction ${id} is in the narrowed table`).toBeVisible({timeout: 8_000});
}

/**
 * Tick a row's checkbox and wait for the state it publishes. Each row toggles on its own —
 * ticking one half of a pair leaves its partner as it was — so a caller that needs an exact
 * selection asserts the toolbar's count itself.
 */
async function selectRow(page: Page, rowId: string) {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-${rowId}`);
    await expect(checkbox).toBeVisible({timeout: 2_000});
    // A checkbox is a toggle: read its state, and click only an unticked one.
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    // The toolbar is drawn only while something is selected, and publishes how many rows it holds.
    await expect(page.getByTestId('selection-toolbar')).not.toHaveAttribute('data-selected-count', '0');
}

/** Open the row menu of transaction `id` and return the menu, on screen. */
async function openRowMenu(page: Page, id: number): Promise<Locator> {
    const row = txRow(page, id);
    await row.hover();
    // Every row offers "view", so every row has its kebab: asserted, not probed.
    const kebab = row.getByTestId(`row-actions-tx-${id}`);
    await expect(kebab).toBeVisible({timeout: 2_000});
    await kebab.click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: 3_000});
    return menu;
}

/**
 * The seeded promote candidates, read and checked rather than assumed: the WITHDRAWAL and the
 * DEPOSIT tagged exactly "promote-test" (the access-fail rows carry another tag), both linked to
 * nothing, on two different brokers this user can edit, answering each other in one currency.
 * The tag also marks the Coinbase pre-funding deposit, which sits on the withdrawal's own broker
 * and so is no candidate.
 */
async function promoteCandidates(page: Page): Promise<{withdrawal: TxRow; deposit: TxRow}> {
    const tagged = (await readTransactions(page, {tags: 'promote-test'})).filter((tx) => (tx.tags ?? []).includes('promote-test') && tx.related_transaction_id == null);
    const withdrawals = tagged.filter((tx) => tx.type === 'WITHDRAWAL');
    expect(
        withdrawals.map((tx) => tx.id),
        'premise: one standalone WITHDRAWAL tagged promote-test — check populate_mock_data.py',
    ).toHaveLength(1);
    const [withdrawal] = withdrawals;
    const deposits = tagged.filter((tx) => tx.type === 'DEPOSIT' && tx.broker_id !== withdrawal.broker_id && tx.cash?.code === withdrawal.cash?.code && Number(tx.cash?.amount) === -Number(withdrawal.cash?.amount));
    expect(
        deposits.map((tx) => tx.id),
        `premise: one standalone DEPOSIT tagged promote-test answers withdrawal #${withdrawal.id} from another broker — check populate_mock_data.py`,
    ).toHaveLength(1);
    const [deposit] = deposits;
    const brokers = new Map((await listBrokers(page)).map((broker) => [broker.id, broker]));
    for (const tx of [withdrawal, deposit]) expect(canEdit(brokers.get(tx.broker_id)), `premise: #${tx.id} sits on a broker this user can edit`).toBe(true);
    return {withdrawal, deposit};
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Split & Promote', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    // -----------------------------------------------------------------------
    // SPLIT TESTS
    // -----------------------------------------------------------------------

    test('Guard: split action hidden on standalone TX', async ({page}) => {
        // A standalone row on a broker this user owns, read through the API and checked.
        const standalone = await seededRow(page, EDITABLE_STANDALONE);
        await goToRows(page, [standalone.id]);

        // Split action should NOT be offered (its visible function filters paired-only).
        // The menu is this user's full one — edit is there — so the absence is about split alone.
        const menu = await openRowMenu(page, standalone.id);
        await expect(menu.getByTestId('context-menu-action-edit')).toBeVisible();
        await expect(menu.getByTestId('context-menu-action-split')).toHaveCount(0);
    });

    test('Split from Main Table → confirm modal appears', async ({page}) => {
        // A linked pair on two brokers this user can edit: being linked with full access is what
        // makes a row splittable. Checked through the API, then asserted in the menu itself.
        const {giver, receiver} = await seededPair(page, EDITABLE_PAIR);
        await goToRows(page, [giver.id, receiver.id]);

        const menu = await openRowMenu(page, giver.id);
        await menu.getByTestId('context-menu-action-split').click();

        // A confirmation modal should appear (TransactionActionModal testId="tx-action-modal")
        const modal = page.getByTestId('tx-action-modal');
        await expect(modal).toBeVisible({timeout: 3_000});

        // Verify sticky structure: header, scrollable body, footer all visible
        await expect(modal.getByTestId('tx-action-modal-content')).toBeVisible();

        // Footer buttons always visible (sticky)
        await expect(modal.getByTestId('tx-action-modal-confirm')).toBeVisible();
        await expect(modal.getByTestId('tx-action-modal-cancel')).toBeVisible();

        // Quantity cells show 📈 / 📉 by sign, or — for zero: one cell per half of this pair.
        const beforeTable = modal.getByTestId('tx-action-before');
        for (const half of [giver, receiver]) {
            const quantity = Number(half.quantity);
            await expect(beforeTable, `the quantity of #${half.id} (${half.quantity}) shows its sign`).toContainText(quantity > 0 ? '📈' : quantity < 0 ? '📉' : '—');
        }

        // Tag badges are coloured through --badge-bg: every badge of every tag the pair carries,
        // found by the tag it names — data from the seed, not translated text.
        const badgesPerTag = new Map<string, number>();
        for (const half of [giver, receiver]) for (const tag of half.tags ?? []) badgesPerTag.set(tag, (badgesPerTag.get(tag) ?? 0) + 1);
        expect(badgesPerTag.size, `premise: the ${EDITABLE_PAIR} pair carries tags — check populate_mock_data.py`).toBeGreaterThan(0);
        for (const [tag, count] of badgesPerTag) {
            const badges = beforeTable.getByText(tag, {exact: true});
            await expect(badges, `one "${tag}" badge per half that carries it`).toHaveCount(count);
            await expect(badges.and(beforeTable.locator('[style*="--badge-bg:"]')), `every "${tag}" badge has the badge-bg CSS variable`).toHaveCount(count);
        }
    });

    // -----------------------------------------------------------------------
    // PROMOTE TESTS
    // -----------------------------------------------------------------------

    test('Guard: promote toolbar hidden when paired row is selected', async ({page}) => {
        const {giver, receiver} = await seededPair(page, EDITABLE_PAIR);
        await goToRows(page, [giver.id, receiver.id]);
        await selectRow(page, `tx-${giver.id}`);
        // Absence is only a fact once the toolbar has actually rendered FOR THIS
        // selection — one row, with the actions every selection gets. Without this
        // barrier the next assertion is satisfied by "the toolbar hasn't caught up
        // yet", which is not what the test claims.
        const toolbar = page.getByTestId('selection-toolbar');
        await expect(toolbar).toHaveAttribute('data-selected-count', '1');
        await expect(toolbar.getByTestId('toolbar-action-clone')).toBeVisible();
        // The promote/link button should NOT appear for paired rows
        await expect(toolbar.getByTestId('toolbar-action-promote')).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // BULKMODAL NON-REGRESSION (F6 / NR-1)
    // -----------------------------------------------------------------------

    test('NR-1: BulkModal renders correctly after page refresh', async ({page}) => {
        // A standalone row on a broker this user owns: its menu offers edit, so the edit below is
        // asserted, never probed.
        const standalone = await seededRow(page, EDITABLE_STANDALONE);
        await goToRows(page, [standalone.id]);

        // Refresh the page: the URL keeps the narrowing, and the table loads again from nothing.
        await page.reload();
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
        // The table being settled does not mean THIS row has been re-rendered into it.
        await expect(txRow(page, standalone.id)).toBeVisible({timeout: 8_000});

        const menu = await openRowMenu(page, standalone.id);
        await menu.getByTestId('context-menu-action-edit').click();

        // A single-row edit opens the BulkModal on that one row and auto-opens its FormModal.
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 5_000});
        await expect(bulkModal.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]'), 'the workspace holds the edited row').toHaveCount(1);
        await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
    });

    // -----------------------------------------------------------------------
    // PROMOTE from promote-test MOCK DATA
    // -----------------------------------------------------------------------

    test('Promote: select 2 promote-test WITHDRAWAL+DEPOSIT rows → toolbar shows link button', async ({page}) => {
        // These should be: Coinbase(EDITOR) WITHDRAWAL -500 EUR + IB(OWNER) DEPOSIT +500 EUR
        const {withdrawal, deposit} = await promoteCandidates(page);
        await goToRows(page, [withdrawal.id, deposit.id]);

        // Select both
        await selectRow(page, `tx-${withdrawal.id}`);
        await selectRow(page, `tx-${deposit.id}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');

        // The toolbar should show the promote/link button
        await expect(page.getByTestId('toolbar-action-promote')).toBeVisible({timeout: 3_000});
    });
});

// ---------------------------------------------------------------------------
// C3 — the one test here that commits, on a pair of its own
// ---------------------------------------------------------------------------

// Same title as the block above, so the test keeps its full name. A block of its own
// because the TEST_USER login above must not run for it: it signs in as the disposable
// account that owns its pair.
//
// Why not a seeded pair: a committed split rewrites both rows in place — same ids, new
// types, no link — so nothing short of a repopulate puts them back (the tx-hygiene net
// drops new ids, or repopulates when an id is missing: neither happens here), and other
// specs look the seeded pairs up afterwards (tx-bulk-suggest-ux, tx-delete, tx-crud-full).
test.describe('Split & Promote', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    // -----------------------------------------------------------------------
    // C3 REGRESSION: Split + Edit → commit includes splits AND updates (no type in update)
    // -----------------------------------------------------------------------

    test('C3: Split + edit quantity → commit payload has splits + updates without type', async ({page, request}, testInfo) => {
        // The account goes through the real welcome flow before the split itself.
        test.setTimeout(60_000);
        const pair = await openAccountWithPair(page, request, owned, `c3_${testInfo.project.name}`);
        await goToTransactions(page);

        // Select both halves of this test's own pair — by the ids it created, never by
        // position — and open the BulkModal via the Edit toolbar. With two rows selected
        // the workspace opens no FormModal by itself (with one it does, and may open it
        // again after it has been dismissed), so the grid is reachable directly.
        await selectRow(page, `tx-${pair.fromId}`);
        await selectRow(page, `tx-${pair.toId}`);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2');
        const editBtn = page.getByTestId('toolbar-action-edit');
        await expect(editBtn).toBeVisible({timeout: 2_000});
        await editBtn.click();

        // BulkModal should be open
        const bulkModal = page.getByTestId('tx-bulk-modal');
        await expect(bulkModal).toBeVisible({timeout: 3_000});

        // The pair arrives as one row, its receiver hidden behind it. Found by the giver's
        // broker — a name only this account has — not by position: before the split and
        // after it, that row is the giver's.
        const giverRow = bulkModal.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: pair.giver.name});
        await expect(giverRow).toHaveCount(1, {timeout: 5_000});

        // Click Split on the row — need to hover to reveal row actions
        await giverRow.hover();
        const rowActions = giverRow.getByTestId(/^row-actions-/);
        await expect(rowActions).toBeVisible({timeout: 2_000});
        await rowActions.click();
        await page.getByTestId('context-menu-action-split').click();

        // Verify split-queued badge appears in the header summary
        const splitBadge = bulkModal.getByTestId('split-queued-badge');
        await expect(splitBadge).toBeVisible({timeout: 2_000});

        // Double-click the giver row to open FormModal (triggers handleEditRowClick)
        await giverRow.dblclick();

        // FormModal should open
        const formModal = page.getByTestId('tx-form-modal');
        await expect(formModal).toBeVisible({timeout: 3_000});

        // Change quantity value in the FormModal (keep negative to preserve TRANSFER 'from' side)
        const qtyInput = formModal.getByTestId('tx-form-quantity');
        await expect(qtyInput).toBeVisible({timeout: 2_000});
        await qtyInput.fill('-0.002');
        await expect(qtyInput).toHaveValue('-0.002');

        // Save the FormModal
        await formModal.getByTestId('tx-form-save').click();

        // FormModal should close
        await expect(formModal).not.toBeVisible({timeout: 2_000});

        // Now intercept the commit request and verify payload
        const commitPromise = page.waitForResponse((res) => res.url().includes('/api/v1/transactions/commit') && res.request().method() === 'POST', {timeout: 10_000});

        // Click Commit
        const commitBtn = bulkModal.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeVisible({timeout: 2_000});
        await commitBtn.click();

        const response = await commitPromise;
        const requestBody = JSON.parse(response.request().postData() ?? '{}');
        const responseBody = await response.json();

        // CRITICAL ASSERTIONS:
        // 1. Payload must include splits
        expect(requestBody.splits, 'Payload must include splits[]').toBeDefined();
        expect(requestBody.splits.length).toBeGreaterThan(0);

        // 2. Payload must include updates with description change
        expect(requestBody.updates, 'Payload must include updates[]').toBeDefined();
        expect(requestBody.updates.length).toBeGreaterThan(0);

        // 3. Updates must NOT include 'type' field (split handles type change)
        for (const upd of requestBody.updates) {
            expect(upd.type, `Update for id=${upd.id} must NOT have type — split handles it`).toBeUndefined();
        }

        // 4. Update should contain the quantity we set
        const qtyUpdate = requestBody.updates.find((u: any) => u.quantity != null);
        expect(qtyUpdate, 'Should find our quantity update').toBeTruthy();

        // 5. Backend should accept it (no type error, no balance error on the funded giver)
        expect(responseBody.committed, `Commit should succeed. Issues: ${JSON.stringify(responseBody.issues)}`).toBe(true);

        // 6. ...and all of it is about this test's own pair: the split is that pair, the edit its giver
        const ownPair = [pair.fromId, pair.toId].sort((a, b) => a - b);
        const splitPairs = requestBody.splits.map((s: {id_a: number; id_b: number}) => [s.id_a, s.id_b].sort((a, b) => a - b));
        expect(splitPairs, 'The split must be this test’s own pair').toEqual([ownPair]);
        expect(qtyUpdate.id, 'The quantity edit must land on the giver this test double-clicked').toBe(pair.fromId);
    });
});
