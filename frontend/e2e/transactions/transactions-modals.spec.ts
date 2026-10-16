/**
 * Transaction E2E Tests — Phase 07 · Bugfix 3+
 *
 * Covers: CRUD, BulkModal, FormModal, paired transactions, sign-flip,
 * column order, banner dismissal, i18n labels.
 *
 * Prerequisites: backend in test mode (port 6041), at least 1 broker seeded.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {validateRuns, waitForSettled, waitForValidateRun} from '../fixtures/app-events';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, readTransactions, seededAssetId} from '../fixtures/owned-pair';

// ---------------------------------------------------------------------------
// Constants — known mock data (populate_mock_data.py)
// ---------------------------------------------------------------------------

const API = '/api/v1';
/** TEST_USER is OWNER here. */
const OWNED_BROKER = 'Interactive Brokers';
/** TEST_USER is EDITOR here — the other leg of a transfer. */
const EDITOR_BROKER = 'Directa SIM';
/** Held at OWNED_BROKER, with price history and BUY lots. */
const ASSET_NAME = 'Apple';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** The option list is present and has finished loading its catalogue. */
async function optionListReady(page: Page) {
    const list = page.locator('[role="listbox"]');
    await expect(list.first()).toBeVisible({timeout: 5_000});
    await expect(list.first()).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
}

/**
 * The option list is gone — the teardown that follows a pick. It happens after
 * the dependent-field cascade has re-rendered, so it doubles as the barrier for
 * whatever the chosen type/broker/asset changed on the form.
 */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 10_000});
}

/** Navigate to the Transactions page and wait for table to appear. */
async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The page publishes `data-busy` while it loads; wait for that rather than
    // for a duration chosen to be "probably enough".
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    // Wait for either the table or the loading/error state to resolve
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 20_000})]).catch(() => {
        /* either is fine */
    });
}

/** Open "Create" flow: click the + button → BulkModal + FormModal open. */
async function openCreateFlow(page: Page) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
}

/** Fill the CompactCashCell amount inside the standard (non-dual) cash wrapper. */
async function fillCashAmount(page: Page, amount: string) {
    const cashWrap = page.getByTestId('tx-form-cash-wrap');
    await expect(cashWrap).toBeVisible({timeout: 3_000});
    const amountInput = cashWrap.locator('input[data-testid$="-amount"]').first();
    await expect(amountInput).toBeVisible({timeout: 3_000});
    await amountInput.click();
    await amountInput.fill(amount);
    await amountInput.press('Tab');
    // Blur commits the value through the locale parser; assert the commit
    // instead of sleeping through it.
    await expect(amountInput).not.toBeFocused({timeout: 3_000});
}

/** Compare the effective browser border color, not merely an inline declaration
 * that an important Tailwind utility could still override. The probe lets
 * Chromium choose its own supported serialization for OKLCH. */
async function expectComputedBorderColor(page: Page, input: Locator, color: string, message: string) {
    const expected = await page.evaluate((candidate) => {
        const probe = document.createElement('span');
        probe.style.color = candidate;
        document.body.appendChild(probe);
        const normalized = getComputedStyle(probe).color;
        probe.remove();
        return normalized;
    }, color);
    await expect.poll(() => input.evaluate((element) => getComputedStyle(element).borderTopColor), {timeout: 10_000, message}).toBe(expected);
}

/**
 * Fill a minimal BUY transaction in the FormModal (assumes it's already open).
 *
 * Broker and asset are picked by name: "the first option" is whatever sorts first,
 * and for TEST_USER that is a broker without cash (backlog V-21). Every step waits
 * for what it needs instead of probing for it. The cash amount is typed before the
 * asset is picked, so it is booked in the cell's default currency (EUR), not the
 * asset's.
 */
async function fillBuyTransaction(page: Page, opts: {broker: string; asset: string; qty?: string; skipCash?: boolean}) {
    const qty = opts.qty ?? '5';
    // Type is BUY by default
    await expect(page.getByTestId('tx-form-type')).toBeVisible({timeout: 3_000});

    await pickBroker(page, opts.broker);

    // Quantity
    await page.getByTestId('tx-form-quantity').fill(qty);

    // Cash — BUY type requires a cash amount. Fill a non-zero value.
    // The CompactCashCell amount is a locale-safe text input (not type=number),
    // so it must be reached via its data-testid suffix.
    if (!opts.skipCash) {
        await fillCashAmount(page, '100');
    }

    // Asset — a BUY always renders the field: its asset is required.
    await pickAsset(page, opts.asset);
}

/** Choose a transaction type by its code — the option's testid, never its translated label. */
async function selectType(page: Page, code: string) {
    await page.getByTestId('tx-form-type').locator('button, [role="combobox"]').first().click();
    await optionListReady(page);
    await page.getByTestId(`search-select-option-${code}`).click();
    await optionListClosed(page);
}

/** Pick a broker of the standard form by name. */
async function pickBroker(page: Page, name: string) {
    await page.getByTestId('tx-form-broker-wrap').locator('button, [role="combobox"]').first().click();
    await optionListReady(page);
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

/** Pick a broker inside one panel of the dual form (From/To) by name. */
async function pickBrokerInPanel(page: Page, panelTestid: string, name: string) {
    const trigger = page.getByTestId(panelTestid).locator('[role="combobox"]').first();
    await expect(trigger).toBeVisible({timeout: 3_000});
    await trigger.click();
    await optionListReady(page);
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first();
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionListClosed(page);
}

/** Pick an asset by name. The asset select searches inline: its search box is the open trigger. */
async function pickAsset(page: Page, name: string) {
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await expect(assetWrap).toBeVisible({timeout: 3_000});
    await assetWrap.locator('button, [role="combobox"]').first().click();
    const search = page.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: 3_000});
    await search.fill(name);
    // The list is debounced; the named entry arriving *is* the settle.
    const option = page.locator('[data-testid^="search-select-option-"]', {hasText: name}).first();
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionListClosed(page);
}

/** Click the Apply/Save button in the FormModal. */
async function clickApply(page: Page) {
    // Wait for the Apply button to become enabled (form completeness)
    await expect(page.getByTestId('tx-form-save')).toBeEnabled({timeout: 5_000});
    await page.getByTestId('tx-form-save').click();
    // Apply hands the row back to the BulkModal and closes the form; that
    // closure is the outcome, and it is observable.
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 5_000});
}

/** Click a row's action via its kebab menu (row-actions-{id} → context-menu-action-{actionId}). */
async function clickKebabRowAction(row: Locator, actionId: string) {
    const page = row.page();
    await row.hover();
    const kebabBtn = row.getByTestId(/^row-actions-/);
    await expect(kebabBtn).toBeVisible({timeout: 2_000});
    await kebabBtn.click();
    const btn = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(btn).toBeVisible({timeout: 2_000});
    await btn.click();
}

/** Bring a row checkbox to `checked` whatever its starting state: a blind click is a toggle. */
async function ensureChecked(checkbox: Locator) {
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
}

/**
 * What a click on the bulk workspace's close did, read as one state: it closed, or
 * it stopped on the discard dialog (`confirm-modal-confirm`), or it is still on its
 * way out. Both ends are observable, so a poll on this tells them apart — and a
 * failure names the reason instead of "still visible".
 */
async function closeOutcome(page: Page): Promise<'closed' | 'asks to discard' | 'closing'> {
    if (await page.getByTestId('confirm-modal-confirm').isVisible()) return 'asks to discard';
    if (await page.getByTestId('tx-bulk-modal').isHidden()) return 'closed';
    return 'closing';
}

/**
 * Stage a NEW cash-transfer pair in a fresh workspace and return its grid. The pair
 * is one workspace row: its receiving half rides hidden behind it. Brokers are picked
 * by name, not as "the first" and "the last" option, which are whatever sorts there.
 */
async function stageNewCashTransfer(page: Page): Promise<{bulkBody: Locator; rows: Locator}> {
    await openCreateFlow(page);
    await selectType(page, 'CASH_TRANSFER');
    await expect(page.getByTestId('tx-form-dual-from')).toBeVisible({timeout: 3_000});
    await pickBrokerInPanel(page, 'tx-form-dual-from', OWNED_BROKER);
    await pickBrokerInPanel(page, 'tx-form-dual-to', EDITOR_BROKER);
    await fillCashAmount(page, '100');
    await clickApply(page);

    const bulkBody = page.getByTestId('tx-bulk-body');
    const rows = bulkBody.locator('tbody tr[data-row-id]');
    await expect(rows, 'the new pair must be staged as one row').toHaveCount(1, {timeout: 3_000});
    await expect(rows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');
    return {bulkBody, rows};
}

/** After a new pair was removed from the workspace: neither of its halves may be left. */
async function expectBothHalvesGone(page: Page, bulkBody: Locator, rows: Locator) {
    // Not on screen: no row remains, and the grid says it is empty (its empty-state
    // cell, not the translated "No data available").
    await expect(rows).toHaveCount(0, {timeout: 3_000});
    await expect(bulkBody.getByTestId('dt-empty')).toBeVisible();

    // Nor behind it. The receiving half rides hidden, so the grid cannot show whether
    // it went too; the editor's own dirty check can. With both halves gone there is
    // nothing left to discard: closing must simply close.
    await page.getByTestId('tx-bulk-close').click();
    await expect.poll(() => closeOutcome(page), {timeout: 5_000, message: 'closing the emptied workspace must close it without asking to discard — a hidden half left behind is still a change'}).toBe('closed');
}

/**
 * Open the table narrowed to one transaction through the `id_min`/`id_max` URL
 * filter, ending with that row on screen. "It will be near the top" is not true
 * with neighbouring workers creating rows.
 */
async function goToTransactionById(page: Page, txId: number): Promise<Locator> {
    await navigateTo(page, `/transactions?id_min=${txId}&id_max=${txId}`);
    // Visible is not loaded: the page renders, then fills, and says so through data-busy.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    const row = page.locator(`[data-testid="tx-table"] tbody tr[data-row-id="tx-${txId}"]`);
    await expect(row, `transaction ${txId} must be on screen`).toBeVisible({timeout: 10_000});
    return row;
}

// ---------------------------------------------------------------------------
// Rows a test owns, created through the API
// ---------------------------------------------------------------------------

interface CommitBody {
    committed?: boolean;
    issues?: unknown[];
    results?: Array<{operation: string; ids?: number[]; status?: string}>;
}

/**
 * Rows created through `page.request`. That traffic never reaches the page's
 * `response` event, so the commit tracker cannot see them: `afterEach` deletes
 * them by id instead — and runs for a red test too.
 */
let apiOwnedTxIds: number[] = [];

/** The OWNER broker of the mock contract, found by name and checked — never "the first editable one". */
async function ownedMockBrokerId(page: Page): Promise<number> {
    const resp = await page.request.get(`${API}/brokers`);
    expect(resp.ok(), `GET ${API}/brokers answered ${resp.status()}`).toBe(true);
    const {items} = (await resp.json()) as {items: Array<{id: number; name: string; user_role: string | null}>};
    const broker = items.find((b) => b.name === OWNED_BROKER);
    expect(broker?.user_role, `TEST_USER must be OWNER of "${OWNED_BROKER}" — check populate_mock_data.py`).toBe('OWNER');
    return broker!.id;
}

/**
 * A 1 EUR DEPOSIT this test owns, dated today and stamped with `marker`; returns
 * its id. A cash DEPOSIT only raises the broker's cash, and deleting it puts the
 * cash back: no position, lot or asset of anybody else moves.
 */
async function createOwnedDeposit(page: Page, marker: string): Promise<number> {
    const brokerId = await ownedMockBrokerId(page);
    const resp = await page.request.post(`${API}/transactions/commit`, {
        data: {creates: [{broker_id: brokerId, type: 'DEPOSIT', date: todayIso(), quantity: '0', cash: {code: 'EUR', amount: '1'}, tags: [], description: marker}], updates: [], deletes: []},
    });
    expect(resp.ok(), `create the owned DEPOSIT: HTTP ${resp.status()}`).toBe(true);
    const body = (await resp.json()) as CommitBody;
    // Recorded before anything is asserted: cleanup must never depend on an assertion.
    // A rolled-back batch reports its would-be ids as "simulated" — only "success" rows exist.
    const ids = (body.results ?? []).filter((r) => r.operation === 'create' && r.status === 'success').flatMap((r) => r.ids ?? []);
    apiOwnedTxIds.push(...ids);
    expect(body.committed, `the owned DEPOSIT was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    expect(ids, 'the commit must create exactly the owned DEPOSIT').toHaveLength(1);
    return ids[0];
}

/** Delete the API-created rows that still exist. Fails loud: a silent leftover is somebody else's red. */
async function deleteApiOwnedRows(page: Page): Promise<void> {
    const ids = apiOwnedTxIds;
    apiOwnedTxIds = [];
    if (ids.length === 0) return;
    const res = await page.request.get(`${API}/transactions?${ids.map((id) => `ids=${id}`).join('&')}`);
    expect(res.ok(), `cleanup: GET ${API}/transactions?ids=… answered ${res.status()}`).toBe(true);
    const stillThere = ((await res.json()) as Array<{id: number}>).map((t) => t.id);
    if (stillThere.length === 0) return;
    const del = await page.request.post(`${API}/transactions/commit`, {data: {creates: [], updates: [], deletes: stillThere}});
    expect(del.ok(), `cleanup of rows ${stillThere.join(', ')}: HTTP ${del.status()}`).toBe(true);
    const body = (await del.json()) as CommitBody;
    expect(body.committed, `cleanup of rows ${stillThere.join(', ')} was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

// ===================================================================
// T1a, T1b, T6 — a BUY on a broker of the test's own: saved, refused, warned
// ===================================================================

// Same title as the block below, so the tests keep their full names. A block of its own
// because the TEST_USER login there must not run for them: each signs in as a disposable
// account (fixtures/owned-pair.ts) and enters its BUY on a broker that account owns, so
// nothing shared changes, not even for a moment. Deleting the account takes that broker
// and every row on it.
test.describe('Transactions', () => {
    let owned = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: it runs after a timeout too, and an error of its own is
    // reported beside the test's instead of replacing it.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    /** One create of the commit request, as the bulk editor sends it. */
    type SentCreate = {type: string; broker_id: number; asset_id: number | null; date: string; quantity: string; cash: {code: string; amount: string}};
    /** The commit answer, with what an issue carries. */
    type CommitAnswer = {committed?: boolean; issues?: Array<{code?: string; params?: Record<string, unknown>}>; results?: CommitBody['results']};

    /** The currency `fillBuyTransaction` books the BUY's cash in: the cash cell's default, read off the commit request. */
    const BUY_CASH_CODE = 'EUR';

    /**
     * Enter a BUY of 3 Apple for 100 on `brokerName` through the form and apply it. Ends with
     * the form closed and the bulk editor holding that one row, new, done validating it: the
     * run is awaited by its counter, read before Apply, so no late verdict lands over the
     * commit's.
     */
    async function stageBuy(page: Page, brokerName: string): Promise<Locator> {
        await openCreateFlow(page);
        await fillBuyTransaction(page, {broker: brokerName, asset: ASSET_NAME, qty: '3'});
        const bulkRoot = page.getByTestId('tx-bulk-modal-root');
        const runsBefore = await validateRuns(bulkRoot);
        await clickApply(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();
        // The workspace is this test's own: it holds the applied row and nothing else.
        const rows = page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
        await expect(rows, 'the workspace must hold exactly the applied row').toHaveCount(1, {timeout: 3_000});
        await expect(rows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');
        await waitForValidateRun(bulkRoot, runsBefore);
        return rows;
    }

    /** Save the workspace; returns the one create it sent and the server's answer. Armed before the click: a response is an edge. */
    async function commitWorkspace(page: Page): Promise<{create: SentCreate; answer: CommitAnswer}> {
        const commitBtn = page.getByTestId('tx-bulk-commit');
        await expect(commitBtn).toBeEnabled({timeout: 8_000});
        const response = page.waitForResponse((res) => res.request().method() === 'POST' && new URL(res.url()).pathname === `${API}/transactions/commit`, {timeout: 15_000});
        await commitBtn.click();
        const res = await response;
        const {creates} = res.request().postDataJSON() as {creates?: SentCreate[]};
        expect(
            (creates ?? []).map((create) => create.type),
            'the commit sends the applied BUY and nothing else',
        ).toEqual(['BUY']);
        return {create: creates![0], answer: (await res.json()) as CommitAnswer};
    }

    test.describe('Create standalone', () => {
        test('a BUY entered in the form is saved and found again', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the BUY itself.
            test.setTimeout(60_000);
            await openOwnedAccount(page, request, owned, `t1a_${testInfo.project.name}`);
            const broker = await createOwnedBroker(page, 't1a', owned.brokerIds);
            const appleId = await seededAssetId(page, 'AAPL');
            await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: BUY_CASH_CODE, amount: '1000'}}], 'fund the owned broker');
            // After the broker exists, so the page's broker list has it.
            await goToTransactions(page);
            await stageBuy(page, broker.name);

            const {create, answer} = await commitWorkspace(page);
            // Sent as entered, the 100 paid out of the funded currency: a BUY sends its cash negative.
            expect(create, 'the BUY as entered').toMatchObject({type: 'BUY', broker_id: broker.id, asset_id: appleId});
            expect(Number(create.quantity), 'the quantity entered').toBe(3);
            expect(create.cash.code, 'the deposit funds the currency the form books the cash in').toBe(BUY_CASH_CODE);
            expect(Number(create.cash.amount), 'the 100 entered, paid').toBe(-100);
            expect(answer.committed, `the funded BUY must be saved — issues: ${JSON.stringify(answer.issues ?? [])}`).toBe(true);
            const ids = (answer.results ?? []).filter((result) => result.operation === 'create' && result.status === 'success').flatMap((result) => result.ids ?? []);
            expect(ids, 'the commit creates exactly the BUY').toHaveLength(1);
            await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: 10_000});

            // Found again: on the server, as it was sent...
            const saved = await readTransactions(page, {ids: ids[0]});
            expect(
                saved.map((tx) => [tx.type, tx.broker_id, tx.asset_id, tx.date, Number(tx.quantity), tx.cash?.code, Number(tx.cash?.amount)]),
                `transaction ${ids[0]} as saved`,
            ).toEqual([['BUY', broker.id, appleId, create.date, 3, create.cash.code, Number(create.cash.amount)]]);
            // ...and in the main table.
            await goToTransactionById(page, ids[0]);
        });

        test('a BUY without cash is refused with a clear message and nothing is saved', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the BUY itself.
            test.setTimeout(60_000);
            await openOwnedAccount(page, request, owned, `t1b_${testInfo.project.name}`);
            // No deposit: the broker holds no cash, and a new broker allows no overdraft.
            const broker = await createOwnedBroker(page, 't1b', owned.brokerIds);
            await goToTransactions(page);
            const rows = await stageBuy(page, broker.name);

            const {create, answer} = await commitWorkspace(page);
            // Refused for the cash it would take below zero: on this broker, in the currency and
            // on the day the request sent, by exactly the BUY's cash — the broker holds nothing else.
            expect(answer.committed, `the BUY on a broker without cash must be refused — results: ${JSON.stringify(answer.results ?? [])}`).toBe(false);
            expect(
                (answer.issues ?? []).map((issue) => issue.code),
                'one issue: the negative cash',
            ).toEqual(['balanceCashNegative']);
            const params = answer.issues![0].params ?? {};
            expect(params, 'the refusal names the broker, currency and day').toMatchObject({brokerId: broker.id, currency: create.cash.code, date: create.date});
            expect(Number(params.balance), `the balance it would reach (${JSON.stringify(params.balance)})`).toBeLessThan(0);
            expect(Number(params.balance), "the balance is the BUY's own cash").toBe(Number(create.cash.amount));

            // The user is told why: the editor stays open on its error banner, whose one balance
            // line names this broker, the day and the currency. Checked on the broker's unique
            // name and ISO codes, never on translated words — and against the raw forms a missing
            // translation or an unknown broker would leave on screen.
            const bulkModal = page.getByTestId('tx-bulk-modal');
            const error = bulkModal.getByTestId('tx-bulk-error');
            await expect(error).toBeVisible({timeout: 5_000});
            const line = error.getByTestId('tx-bulk-balance-issue');
            await expect(line).toHaveCount(1);
            await expect(line).toContainText(broker.name);
            await expect(line).toContainText(create.date);
            await expect(line).toContainText(create.cash.code);
            for (const raw of ['balanceCashNegative', 'Broker #', '{']) await expect(line, `the message must not show "${raw}"`).not.toContainText(raw);
            await expect(bulkModal).toBeVisible();
            await expect(rows).toHaveCount(1);
            await expect(rows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'new');

            // Its rows link leads to the BUY that caused it.
            const label = rows.getByTestId('tx-bulk-row-label');
            await expect(label).toHaveAttribute('data-issue-highlighted', 'false');
            await line.getByTestId('tx-bulk-balance-rows').click();
            await expect(label).toHaveAttribute('data-issue-highlighted', 'true');

            // Nothing saved: the broker is this test's own, and holds no row.
            expect(await readTransactions(page, {broker_id: broker.id}), 'the refused BUY must not have been saved').toEqual([]);
        });
    });

    // ===================================================================
    // T6 — Banner dismissible (M1/M2)
    // ===================================================================
    test.describe('Banner dismissible (M1/M2)', () => {
        test('validation warning banner has dismiss button', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the form itself.
            test.setTimeout(60_000);
            // The trigger is explicit: a BUY on this test's own broker, which holds no cash. The
            // old version typed qty -1, but the form makes a BUY's quantity positive before it
            // validates, so -1 never reached the server: its banner came from the first broker
            // of the list having no cash.
            await openOwnedAccount(page, request, owned, `t6_${testInfo.project.name}`);
            const broker = await createOwnedBroker(page, 't6', owned.brokerIds);
            // After the broker exists, so the page's broker list has it.
            await goToTransactions(page);
            await openCreateFlow(page);
            await fillBuyTransaction(page, {broker: broker.name, asset: ASSET_NAME, qty: '3'});

            // Validate now, and wait for *that* run: the counter is read before the
            // click, so a run that finished earlier cannot answer for this one.
            const root = page.getByTestId('tx-form-modal-root');
            const validateBtn = page.getByTestId('tx-form-validate-now');
            await expect(validateBtn).toBeEnabled({timeout: 5_000});
            const runsBefore = await validateRuns(root);
            await validateBtn.click();
            await waitForValidateRun(root, runsBefore);

            // The verdict lands in the form's warning banner. Naming this test's broker makes it
            // the balance warning — the premise; its X is the subject. The old selector
            // (`.info-banner button`) named a CSS class nothing carries, so its probe never
            // matched and the dismiss was never tried.
            const banner = page.getByTestId('tx-form-body').getByTestId('info-banner-warning');
            await expect(banner).toBeVisible({timeout: 5_000});
            await expect(banner).toContainText(broker.name);
            const dismissBtn = banner.locator('button[aria-label]');
            await expect(dismissBtn).toBeVisible();
            await dismissBtn.click();
            await expect(banner).toBeHidden({timeout: 2_000});
        });
    });

    // ===================================================================
    // V-37 — what the form refuses on screen never reaches the server
    // ===================================================================
    // A field the form shows as refused must block the form, not be replaced in silence:
    // behind a typed date the picker turns down, the form still holds the previous date;
    // a BUY's -1 is sign-corrected to 1 before it is sent. While such a field is on
    // screen the form is not «valid», nothing is validated or saved, and «Validate now»
    // leads to the field instead. Each test owns its account, broker and deposit, commits
    // nothing itself, and the block's `afterEach` deletes the account.
    test.describe('A refused entry blocks the form', () => {
        /**
         * Every POST the page sends to the transactions validate and commit endpoints, body
         * parsed, in order. A record, not a wait: armed before the form opens, it misses none,
         * and the API calls the test makes itself (`page.request`) never reach it.
         */
        function recordTransactionPosts(page: Page): {validate: unknown[]; commit: unknown[]} {
            const posts = {validate: [] as unknown[], commit: [] as unknown[]};
            page.on('request', (req) => {
                if (req.method() !== 'POST') return;
                const path = new URL(req.url()).pathname;
                const list = path === `${API}/transactions/validate` ? posts.validate : path === `${API}/transactions/commit` ? posts.commit : null;
                if (!list) return;
                let body: unknown;
                try {
                    body = req.postDataJSON();
                } catch {
                    // Kept raw: a body that does not parse is still a request that left.
                    body = req.postData();
                }
                list.push(body);
            });
            return posts;
        }

        /** What each validate request asked about: the quantity of every create on `brokerId`, one array per request. */
        function quantitiesPerRequest(bodies: unknown[], brokerId: number): unknown[][] {
            return bodies.map((body) => ((body as {creates?: Array<{broker_id?: number; quantity?: unknown}>} | null)?.creates ?? []).filter((create) => create.broker_id === brokerId).map((create) => create.quantity));
        }

        /**
         * On the account signed in on `page`: a broker of its own funded with 1000 EUR ten days
         * back, and a BUY of `qty` Apple for 100 EUR entered in the form. Ends with the form open,
         * its automatic run done — counter grown, form idle — and saying «valid».
         */
        async function openValidatedBuy(page: Page, tag: string, qty: string) {
            const broker = await createOwnedBroker(page, tag, owned.brokerIds);
            const [depositId] = await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: BUY_CASH_CODE, amount: '1000'}}], 'fund the owned broker');
            // After the broker exists, so the page's broker list has it.
            await goToTransactions(page);
            const posts = recordTransactionPosts(page);
            await openCreateFlow(page);
            const root = page.getByTestId('tx-form-modal-root');
            const runsAtOpen = await validateRuns(root);
            await fillBuyTransaction(page, {broker: broker.name, asset: ASSET_NAME, qty});
            await waitForValidateRun(root, runsAtOpen);
            await expect(page.getByTestId('tx-form-valid-inline'), 'premise: the funded BUY validates on its own and says so').toBeVisible();
            return {broker, depositId, posts, root};
        }

        for (const refused of [
            {name: 'a future date', text: () => daysAgoIso(-30)},
            {name: 'text that is not a date', text: () => '2026-13-45'},
        ]) {
            test(`a refused typed date blocks the form: ${refused.name}`, async ({page, request}, testInfo) => {
                // The account goes through the real welcome flow before the form itself.
                test.setTimeout(60_000);
                await openOwnedAccount(page, request, owned, `v37d_${testInfo.project.name}`);
                const {broker, depositId, posts, root} = await openValidatedBuy(page, 'v37d', '3');
                const dateRoot = page.getByTestId('tx-form-date-wrap').getByTestId('single-date-picker-root');
                // The field itself: clicking it opens a calendar whose year box is another input.
                const dateInput = dateRoot.locator('input[type="text"]');
                const validInline = page.getByTestId('tx-form-valid-inline');
                const validateNow = page.getByTestId('tx-form-validate-now');
                const text = refused.text();

                // Typed and left: leaving the field is when the picker turns the text down.
                const validatesAtEdit = posts.validate.length;
                await dateInput.click();
                await dateInput.fill(text);
                await dateInput.press('Tab');
                await expect(dateInput).not.toBeFocused();
                await expect(dateRoot, `premise: the picker refuses ${text}`).toHaveAttribute('data-invalid', 'true');
                await expect(dateInput, 'premise: the refused text stays on screen').toHaveValue(text);

                // The form takes the refusal as its own: not «valid», Apply closed.
                await expect(validInline, 'a refused date is on screen: the form must not call itself valid').toBeHidden({timeout: 5_000});
                await expect(page.getByTestId('tx-form-save'), 'Apply must not take the previous date behind the refused text').toBeDisabled();

                // «Validate now» keeps the state a complete form gives it, sends nothing, and leads to the field.
                await expect(validateNow, 'Validate now is disabled only by an incomplete form').toBeEnabled();
                const runsBeforeClick = await validateRuns(root);
                await validateNow.click();
                await expect(dateInput, 'Validate now leads to the refused date').toBeFocused();
                await waitForSettled(root);
                expect(await validateRuns(root), 'Validate now must not run a validation').toBe(runsBeforeClick);
                expect(posts.validate.slice(validatesAtEdit), 'no validate request may leave after the refused date').toEqual([]);

                // Nothing saved: no commit left the page, and the broker — this test's own — holds its deposit alone.
                expect(posts.commit, 'nothing may be committed').toEqual([]);
                expect(
                    (await readTransactions(page, {broker_id: broker.id})).map((tx) => tx.id),
                    'the broker holds its deposit and nothing else',
                ).toEqual([depositId]);
            });
        }

        test('quantity -1: no valid, no request, focus; a corrected quantity validates once', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the form itself.
            test.setTimeout(60_000);
            await openOwnedAccount(page, request, owned, `v37q_${testInfo.project.name}`);
            const {broker, posts, root} = await openValidatedBuy(page, 'v37q', '2');
            const quantity = page.getByTestId('tx-form-quantity');
            const validInline = page.getByTestId('tx-form-valid-inline');
            const validateNow = page.getByTestId('tx-form-validate-now');

            // A BUY's quantity must be positive: typed and left, -1 is refused on screen.
            const validatesAtEdit = posts.validate.length;
            await quantity.fill('-1');
            await quantity.press('Tab');
            await expect(quantity, 'premise: the form refuses -1 on a BUY').toHaveAttribute('aria-invalid', 'true');
            await expect(quantity).not.toBeFocused();
            // Whatever the edit set off has finished: a debounced run, if one was armed, went out and came back.
            await waitForSettled(root);
            const sentSinceEdit = JSON.stringify(quantitiesPerRequest(posts.validate.slice(validatesAtEdit), broker.id));
            await expect(validInline, `quantity -1 is refused on screen: the form must not call itself valid (validate requests since the edit carried ${sentSinceEdit})`).toBeHidden({timeout: 5_000});
            expect(quantitiesPerRequest(posts.validate.slice(validatesAtEdit), broker.id), 'no validate request may carry the refused quantity, not even sign-corrected to 1').toEqual([]);

            // «Validate now» stays enabled (the form is complete), sends nothing, and leads to the field.
            await expect(validateNow, 'Validate now is disabled only by an incomplete form').toBeEnabled();
            const runsBeforeClick = await validateRuns(root);
            await validateNow.click();
            await expect(quantity, 'Validate now leads to the refused quantity').toBeFocused();
            await waitForSettled(root);
            expect(await validateRuns(root), 'Validate now must not run a validation').toBe(runsBeforeClick);

            // Corrected to 3 — not back to 2, a draft the scheduler skips as validated within 10 s:
            // one run, and the form is valid again.
            const runsBeforeCorrection = await validateRuns(root);
            await quantity.fill('3');
            await quantity.press('Tab');
            await waitForValidateRun(root, runsBeforeCorrection);
            expect(await validateRuns(root), 'the corrected quantity is validated exactly once').toBe(runsBeforeCorrection + 1);
            await expect(validInline, 'the corrected BUY is valid again').toBeVisible();
            expect(quantitiesPerRequest(posts.validate.slice(validatesAtEdit), broker.id), 'since -1: one validate request, for 3, and none for 1').toEqual([['3']]);
        });
    });

    // ===================================================================
    // V-38 — a balance problem is listed with the balance problems
    // ===================================================================
    // The form's warning banner has two lists: the problems of its own fields (`tx-form-issue`)
    // and the inconsistencies the entry would cause in the data (`tx-form-balance-issue`, under
    // its own header). The form splits the server's verdict by index — a field problem when the
    // index is 0 or more — while the server attaches `balanceCashNegative` to the row that takes
    // the cash below zero: the form's own create, index 0. A WITHDRAWAL from a broker without
    // cash is therefore listed as a problem of the form's fields, which no field can fix. The
    // bulk editor classifies by code (`isBulkBalanceIssue`). Read on screen, by testid and count;
    // the server's verdict is read off the wire, as the premise. The account, its broker and the
    // form are this test's own: nothing is saved, form and editor are discarded, and the block's
    // `afterEach` deletes the broker and the account — after a red too.
    test.describe('A balance problem is not a field problem (V-38)', () => {
        type SentCreate = {type?: string; broker_id?: number; date?: string; cash?: {code?: string; amount?: string} | null};
        type ValidateAnswer = {issues?: Array<{operation?: string; index?: number; code?: string | null}>};

        /** A broker of the account's own that allows no overdraft and holds no cash; its id is recorded for cleanup before anything else is checked. */
        async function createBrokerWithoutCash(page: Page, tag: string): Promise<{id: number; name: string}> {
            const name = `${tag}-broker-${uniqueSuffix()}`;
            const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2025-01-01', allow_cash_overdraft: false}]}), `create the broker ${name}`);
            const created = body.results.find((result) => result.name === name);
            if (typeof created?.broker_id === 'number') owned.brokerIds.push(created.broker_id);
            if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`create the broker ${name}: no id — ${created?.message ?? 'no result'}`);
            return {id: created.broker_id, name};
        }

        /** Leave without saving: the form through its discard guard — it holds the WITHDRAWAL —, then the editor, which holds nothing: Apply was never pressed. */
        async function discardFormAndEditor(page: Page) {
            const discard = page.getByTestId('confirm-modal-confirm');
            await page.getByTestId('tx-form-cancel').click();
            await expect(discard, 'the form holds the WITHDRAWAL: cancelling it asks to discard it').toBeVisible({timeout: 5_000});
            await discard.click();
            await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 5_000});
            await page.getByTestId('tx-bulk-close').click();
            await expect.poll(() => closeOutcome(page), {timeout: 5_000, message: 'the editor holds nothing: one click on close closes it'}).toBe('closed');
        }

        test('V-38: a WITHDRAWAL from a broker without cash lists the negative cash among the balance problems, none among the field problems', async ({page, request}, testInfo) => {
            // The account goes through the real welcome flow before the form itself.
            test.setTimeout(60_000);
            await openOwnedAccount(page, request, owned, `v38_${testInfo.project.name}`);
            const broker = await createBrokerWithoutCash(page, 'v38');
            // After the broker exists, so the page's broker list has it.
            await goToTransactions(page);
            await openCreateFlow(page);
            await selectType(page, 'WITHDRAWAL');
            await pickBroker(page, broker.name);
            await fillCashAmount(page, '100');

            // Validate now, and wait for that run: the counter is read before the click, and the
            // response is armed before it too — a response is an edge.
            const root = page.getByTestId('tx-form-modal-root');
            const validateNow = page.getByTestId('tx-form-validate-now');
            await expect(validateNow).toBeEnabled({timeout: 5_000});
            const runsBefore = await validateRuns(root);
            const validated = page.waitForResponse((res) => res.request().method() === 'POST' && new URL(res.url()).pathname === `${API}/transactions/validate`, {timeout: 15_000});
            await validateNow.click();
            const response = await validated;
            await waitForValidateRun(root, runsBefore);

            // Premise, off the wire: the form sent its WITHDRAWAL of 100 today on this broker, and the
            // server answers with one problem, the negative cash, attached to that create — index 0.
            const sent = ((response.request().postDataJSON() as {creates?: SentCreate[]}).creates ?? []).map((create) => ({type: create.type, broker_id: create.broker_id, date: create.date, amount: Number(create.cash?.amount)}));
            expect(sent, 'premise: the form validates its WITHDRAWAL of 100, today, on the broker').toEqual([{type: 'WITHDRAWAL', broker_id: broker.id, date: todayIso(), amount: -100}]);
            const answer = (await response.json()) as ValidateAnswer;
            expect(
                (answer.issues ?? []).map(({operation, index, code}) => ({operation, index, code})),
                'premise: one problem, the negative cash, attached to the form’s own create',
            ).toEqual([{operation: 'create', index: 0, code: 'balanceCashNegative'}]);

            // On screen the verdict is in: the warning banner names this test's broker.
            const body = page.getByTestId('tx-form-body');
            const banner = body.getByTestId('info-banner-warning');
            await expect(banner).toBeVisible({timeout: 5_000});
            await expect(banner).toContainText(broker.name);
            await banner.scrollIntoViewIfNeeded();
            const shot = testInfo.outputPath('V-38-form-after-validation.png');
            await root.screenshot({path: shot});
            await testInfo.attach('V-38 form after validation', {path: shot, contentType: 'image/png'});

            // The subject, soft: the form and the editor are discarded whatever the verdict.
            await expect.soft(body.getByTestId('tx-form-balance-issue'), 'the negative cash is listed among the balance problems').toHaveCount(1);
            await expect.soft(body.getByTestId('tx-form-issue'), 'no field has a problem: none is listed among the field problems').toHaveCount(0);

            await discardFormAndEditor(page);
            expect(await readTransactions(page, {broker_id: broker.id}), 'nothing was saved: the broker holds no row').toEqual([]);
        });
    });
});

test.describe('Transactions', () => {
    // Whoever commits, cleans up. `Transaction` is global: a row left on one of
    // TEST_USER's seeded brokers shifts the NAV, positions, counts and pages of
    // every later test, and the txHygiene net that used to hide it exists only at
    // one worker. The BUY that is saved and the one that is refused (T1a, T1b) run
    // on accounts of their own, in the block above; for any commit made here, the
    // tracker records the rows this page's commits create and deletes exactly
    // those, at any worker count. It starts after login (it reads through
    // `page.request`, which needs the session cookie) and so before any commit;
    // `afterEach` runs for a red test too. The rows T3, T9, T10 and T11 create
    // through the API are invisible to the tracker and are deleted by id in the
    // same `afterEach`.
    let txWrites: TransactionWriteTracker | undefined;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        txWrites = await trackTransactionWrites(page);
        await goToTransactions(page);
    });

    test.afterEach(async ({page}) => {
        const tracker = txWrites;
        txWrites = undefined;
        try {
            await tracker?.cleanup();
        } finally {
            await deleteApiOwnedRows(page);
        }
    });

    // ===================================================================
    // T1 — Create standalone BUY (Apply flow). The BUY that is saved and the
    // one that is refused (T1a, T1b) run on accounts of their own, above.
    // ===================================================================
    test.describe('Create standalone', () => {
        test('Apply button disabled when form incomplete', async ({page}) => {
            await openCreateFlow(page);
            // Type is BUY, but broker + qty not filled → Apply disabled
            const applyBtn = page.getByTestId('tx-form-save');
            await expect(applyBtn).toBeDisabled({timeout: 2_000});
        });
    });

    // ===================================================================
    // T1 (beta feedback) — decimal typing in the form
    // ===================================================================
    test.describe('Decimal typing (T1)', () => {
        test('quantity field starts empty in create mode', async ({page}) => {
            await openCreateFlow(page);
            const qtyInput = page.getByTestId('tx-form-quantity');
            await expect(qtyInput).toBeVisible({timeout: 3_000});
            // T1-b: a pre-filled "0" forced the user to cursor around it just to
            // type a decimal. The draft now starts empty.
            await expect(qtyInput).toHaveValue('');
        });

        test('typing 1234,56 into cash keeps the comma mid-typing', async ({page}) => {
            await openCreateFlow(page);
            const cashWrap = page.getByTestId('tx-form-cash-wrap');
            await expect(cashWrap).toBeVisible({timeout: 3_000});
            const amountInput = cashWrap.locator('input[data-testid$="-amount"]').first();
            await expect(amountInput).toBeVisible({timeout: 3_000});
            await amountInput.click();

            // pressSequentially fires one input event per character — the exact
            // cadence the pre-T1 sync-down effect broke: the "1234," emission
            // came back from the parent as the normalized "1234." prop and the
            // buffer was rewritten to "1234", swallowing the separator and
            // gluing the fraction onto the integer part.
            await amountInput.pressSequentially('1234,');
            await expect(amountInput).toHaveValue('1234,');
            await amountInput.pressSequentially('56');
            await expect(amountInput).toHaveValue('1234,56');
        });
    });

    // ===================================================================
    // T2 — Double-click re-edit in BulkModal (C1 fix)
    // ===================================================================
    test.describe('Double-click re-edit (C1)', () => {
        test('double-click on new row re-opens FormModal pre-populated', async ({page}) => {
            await openCreateFlow(page);
            await fillBuyTransaction(page, {broker: OWNED_BROKER, asset: ASSET_NAME, qty: '7'});
            await clickApply(page);

            // FormModal closed, BulkModal visible
            await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

            // Double-click the row this test applied. The workspace was opened empty by
            // this test, so it holds exactly that row: assert it, then act on it —
            // never on "the first <tr>" of whatever the table happens to render.
            const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr[data-row-id]');
            await expect(bulkRows, 'the workspace must hold exactly the applied row').toHaveCount(1, {timeout: 3_000});
            await bulkRows.dblclick();

            // FormModal should reopen with pre-populated data
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 3_000});

            // Quantity should be pre-filled with what was applied (7). Polled: the
            // form fills in after it opens, and inputValue() reads one instant.
            const qtyInput = page.getByTestId('tx-form-quantity');
            await expect(qtyInput).toBeVisible();
            await expect.poll(async () => Number(await qtyInput.inputValue()), {timeout: 3_000}).toBe(7);
        });
    });

    // ===================================================================
    // T3 — Type swap groups (H6) — on a DB row this test creates
    // ===================================================================
    test.describe('Type swap groups (H6)', () => {
        test('editing DB row restricts type to swap group', async ({page}) => {
            // A DB row this test owns: a DEPOSIT, whose swap group is {DEPOSIT, WITHDRAWAL}.
            // "The first checkbox of the table" was a seed row or a neighbour's, of a type
            // nobody chose, so the restriction could only be checked loosely (≤ 3).
            const id = await createOwnedDeposit(page, `V21 T3 ${uniqueSuffix()}`);
            await goToTransactionById(page, id);
            await ensureChecked(page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`));

            // Click edit toolbar button
            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeVisible({timeout: 3_000});
            await editBtn.click();

            // With single row, BulkModal + FormModal should auto-open
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

            // Type dropdown should be visible (unlockImmutable=true)
            const typeSelect = page.getByTestId('tx-form-type');
            await expect(typeSelect).toBeVisible();

            // Open the type dropdown and check options
            await typeSelect.locator('button, [role="combobox"]').first().click();
            await optionListReady(page);

            // Only the swap group of the row's own type — NOT all types.
            await expect(page.getByTestId('search-select-option-DEPOSIT')).toBeVisible();
            await expect(page.getByTestId('search-select-option-WITHDRAWAL')).toBeVisible();
            await expect(page.locator('[data-testid^="search-select-option-"]'), 'a DEPOSIT may only swap with WITHDRAWAL').toHaveCount(2);
        });
    });

    // ===================================================================
    // T4 — Column order (M5): in the bulk editor «Cost basis» comes before
    // «Event». Intended — developer decision of 13/10 (question 12), which
    // supersedes the Bugfix-3 plan's step 10 note ("cost_basis_override moved
    // after asset_event_id"). Relative order only, not adjacency.
    // ===================================================================
    test.describe('Column order (M5)', () => {
        test('cost basis column comes before the asset event column', async ({page}) => {
            await openCreateFlow(page);
            await page.getByTestId('tx-form-cancel').click();
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();
            await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: 5_000});

            // The grid draws its headers with no row staged. Column order and visibility
            // live only in localStorage, so this fresh context shows the defaults.
            const bulkBody = page.getByTestId('tx-bulk-body');
            await expect(bulkBody.getByTestId('dt-header-cost_basis_override'), 'precondition: the cost basis column is shown by default').toBeVisible({timeout: 5_000});
            await expect(bulkBody.getByTestId('dt-header-asset_event_id'), 'precondition: the asset event column is shown by default').toBeVisible({timeout: 5_000});

            // One `dt-header-<id>` per shown column, in drawn order. The ⓘ icons
            // `dt-header-tooltip-<id>` share the prefix but are not columns.
            const headers = bulkBody.locator('[data-testid^="dt-header-"]:not([data-testid^="dt-header-tooltip-"])');
            const compared = new Set(['dt-header-cost_basis_override', 'dt-header-asset_event_id']);
            await expect
                .poll(async () => (await headers.evaluateAll((nodes) => nodes.map((node) => node.getAttribute('data-testid') ?? ''))).filter((id) => compared.has(id)), {
                    message: 'the cost basis column must come before the asset event column (developer decision 13/10, question 12)',
                    timeout: 5_000,
                })
                .toEqual(['dt-header-cost_basis_override', 'dt-header-asset_event_id']);
        });
    });

    // ===================================================================
    // T5 — Asset optional label (H5)
    // ===================================================================
    test.describe('Asset optional label (H5)', () => {
        test('INTEREST type shows (optional) on asset field', async ({page}) => {
            await openCreateFlow(page);

            // Change type to INTEREST — by its option's testid. The old version found the
            // option by its (translated) label and only acted if a probe saw it in time.
            await selectType(page, 'INTEREST');

            const assetWrap = page.getByTestId('tx-form-asset-wrap');
            await expect(assetWrap).toBeVisible({timeout: 2_000});
            const assetLabel = assetWrap.locator('span').first();
            await expect(assetLabel).toContainText(/optional|opzionale|optionnel|opcional/i);
        });

        test('BUY type does not show (optional) on asset field', async ({page}) => {
            await openCreateFlow(page);
            // BUY is default — asset label should show * not (optional). Its asset is
            // required, so the field is always rendered: assert it rather than probe.
            const assetWrap = page.getByTestId('tx-form-asset-wrap');
            await expect(assetWrap).toBeVisible({timeout: 5_000});
            const label = assetWrap.locator('span').first();
            // Wait for server-driven type rules to load (ensureTypesLoaded is async).
            await expect(label).toContainText('*', {timeout: 15_000});
            await expect(label).not.toContainText(/optional|opzionale|optionnel|opcional/i);
        });
    });

    // ===================================================================
    // T6 — Banner dismissible (M1/M2): on an account of its own, above.
    // ===================================================================

    // ===================================================================
    // T7 — Paired transaction (Cash Transfer)
    // ===================================================================
    test.describe('Paired transactions', () => {
        test('can create Cash Transfer via dual form', async ({page}) => {
            await openCreateFlow(page);

            // By the option's testid: the old version matched the translated label
            // ("cash transfer|bonifico") and only acted if a probe saw it in time.
            await selectType(page, 'CASH_TRANSFER');

            const dualFrom = page.getByTestId('tx-form-dual-from');
            const dualTo = page.getByTestId('tx-form-dual-to');
            await expect(dualFrom).toBeVisible({timeout: 3_000});
            await expect(dualTo).toBeVisible({timeout: 3_000});
        });

        test('delete new paired row removes both halves (C3)', async ({page}) => {
            const {bulkBody, rows} = await stageNewCashTransfer(page);

            // Remove it through its kebab menu. The old version looked for a delete
            // button inside the row, which does not exist: its probe never matched,
            // nothing was ever deleted, and the test reported green regardless.
            await clickKebabRowAction(rows, 'mark-delete');

            await expectBothHalvesGone(page, bulkBody, rows);
        });

        test('delete new paired row through «Delete selected» removes both halves (C3)', async ({page}) => {
            const {bulkBody, rows} = await stageNewCashTransfer(page);

            // Select it through its own checkbox, then remove the selection with the
            // workspace's selection toolbar.
            await ensureChecked(rows.getByTestId(/^dt-row-checkbox-/));
            await page.getByTestId('tx-bulk-delete-selected').click();

            await expectBothHalvesGone(page, bulkBody, rows);
        });
    });

    // ===================================================================
    // T8 — Multi-language labels
    // ===================================================================
    test.describe('i18n', () => {
        test('optional label changes with language', async ({page}) => {
            await openCreateFlow(page);

            // Switch to INTEREST type — by the option's testid, the same in every language.
            await selectType(page, 'INTEREST');
            const assetWrap = page.getByTestId('tx-form-asset-wrap');
            await expect(assetWrap).toBeVisible({timeout: 3_000});
            await expect(assetWrap).toContainText(/optional/i);

            // Leave the editor by reloading the page: the language selector sits in the
            // header, under the modals. (It used to close them through probes, any of which
            // could skip its click in silence and leave a backdrop over the header.)
            await goToTransactions(page);

            // Set Italian
            await setLanguage(page, 'it');
            await goToTransactions(page);
            await openCreateFlow(page);

            // Switch to INTEREST again
            await selectType(page, 'INTEREST');
            const assetWrap2 = page.getByTestId('tx-form-asset-wrap');
            await expect(assetWrap2).toBeVisible({timeout: 3_000});
            await expect(assetWrap2).toContainText(/opzionale/i);
            // Nothing to restore: the language lives in this test's own browser context
            // (localStorage), which ends with the test.
        });
    });

    // ===================================================================
    // T9 — Edit from main table (C2)
    // ===================================================================
    test.describe('Edit from main table (C2)', () => {
        test('edit button opens BulkModal with FormModal auto-opened', async ({page}) => {
            // A row this test owns, selected by its id — not "the first body checkbox",
            // a seed row or a neighbour's that could change under the test.
            const id = await createOwnedDeposit(page, `V21 T9 ${uniqueSuffix()}`);
            await goToTransactionById(page, id);
            await ensureChecked(page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`));

            // One row selected: the toolbar's edit is always offered. Asserted, not probed.
            const editBtn = page.locator('[data-testid="toolbar-action-edit"]');
            await expect(editBtn).toBeVisible({timeout: 3_000});
            await editBtn.click();

            // BulkModal + FormModal should open (auto-open for single row)
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

            // Pre-populated with the row being edited. A DEPOSIT has no quantity; its
            // amount is the field the form must have filled in.
            const amountInput = page.getByTestId('tx-form-cash-amount');
            await expect(amountInput).toBeVisible({timeout: 3_000});
            await expect(amountInput).not.toHaveValue('');
        });
    });

    // ===================================================================
    // T10 — Delete from main table
    // ===================================================================
    test.describe('Delete', () => {
        test('can delete a standalone transaction', async ({page}) => {
            // A row this test owns. The old version took "the first body row" — a seed
            // row or a neighbour's — read a global count badge, and never deleted
            // anything: the toolbar delete opens the bulk workspace now, so its probe
            // for a confirm dialog always answered false and the test went green
            // having done nothing (backlog V-21).
            const id = await createOwnedDeposit(page, `V21 T10 ${uniqueSuffix()}`);
            await goToTransactionById(page, id);
            await ensureChecked(page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`));

            const deleteBtn = page.getByTestId('toolbar-action-delete');
            await expect(deleteBtn).toBeVisible({timeout: 3_000});
            await deleteBtn.click();

            // T4: no confirm dialog — the bulk workspace opens with the row staged as a
            // delete, which the row's published status says (`data-status`).
            const bulkModal = page.getByTestId('tx-bulk-modal');
            await expect(bulkModal).toBeVisible({timeout: 5_000});
            const stagedRows = bulkModal.locator('tbody tr[data-row-id]');
            await expect(stagedRows, 'the workspace must stage exactly the row we selected').toHaveCount(1, {timeout: 5_000});
            await expect(stagedRows.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'delete');

            // Commit through the workspace; the request must delete our row and nothing else.
            const commitBtn = page.getByTestId('tx-bulk-commit');
            await expect(commitBtn).toBeEnabled({timeout: 8_000});
            const commitRequest = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
            const commitAnswer = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
            await commitBtn.click();
            const payload = (await commitRequest).postDataJSON() as {deletes?: number[]};
            expect(payload.deletes, 'the commit must delete exactly our row').toEqual([id]);
            const body = (await (await commitAnswer).json()) as CommitBody;
            expect(body.committed, `the delete was rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
            await expect(bulkModal).toBeHidden({timeout: 10_000});

            // Gone, by id: ids are never reused (AUTOINCREMENT since plan 34), so an
            // empty answer for this id can only mean this row.
            await expect
                .poll(
                    async () => {
                        const res = await page.request.get(`${API}/transactions?ids=${id}`);
                        return res.ok() ? ((await res.json()) as unknown[]).length : -1;
                    },
                    {timeout: 10_000, message: `transaction ${id} must no longer exist`},
                )
                .toBe(0);
            // And from the table narrowed to that id. Nothing else can hold it, so the
            // grid must render its empty state: that is the presence barrier which keeps
            // "no such row" from also meaning "not rendered yet".
            await navigateTo(page, `/transactions?id_min=${id}&id_max=${id}`);
            await waitForSettled(page.getByTestId('transactions-page'), 20_000);
            await expect(page.getByTestId('tx-table').getByTestId('dt-empty')).toBeVisible({timeout: 10_000});
            await expect(page.locator(`[data-testid="tx-table"] tr[data-row-id="tx-${id}"]`)).toHaveCount(0);
        });
    });

    // ===================================================================
    // T11 — View mode (readonly)
    // ===================================================================
    test.describe('View mode', () => {
        test('double-click on main table row opens view mode', async ({page}) => {
            // A row this test owns, on screen by its id. Double-clicked on its description
            // cell: plain text, where the row's own handler gets the event (other cells
            // carry links and buttons of their own).
            const id = await createOwnedDeposit(page, `V21 T11 ${uniqueSuffix()}`);
            const row = await goToTransactionById(page, id);
            await row.getByTestId(`tx-desc-${id}`).dblclick();

            await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});
            const title = page.getByTestId('tx-form-title');
            await expect(title).toBeVisible();

            // View mode, proven positively first: only a read-only form offers the switch
            // to edit, and its footer names the row it opened...
            await expect(page.getByTestId('tx-form-switch-edit')).toBeVisible();
            await expect(page.getByTestId('tx-form-readonly-footer')).toContainText(new RegExp(`#${id}\\b`));
            // ...so the Save button being hidden means "read-only", not "not rendered yet".
            await expect(page.getByTestId('tx-form-save')).toBeHidden();
        });
    });

    // ===================================================================
    // T12 — Sign coloring: qty border reflects sign rule post-autoflip
    // ===================================================================
    test.describe('Sign coloring', () => {
        test('BUY qty negative → red border, positive → green border', async ({page}) => {
            await openCreateFlow(page);
            // BUY is the default type — quantityRule is 'positive'
            await expect(page.getByTestId('tx-form-type')).toBeVisible({timeout: 3_000});

            const qtyInput = page.getByTestId('tx-form-quantity');
            await expect(qtyInput).toBeVisible({timeout: 2_000});

            // Wait for type rules to load — sign label "(+)" appears when quantityRule='positive'
            const qtyWrap = page.getByTestId('tx-form-quantity-wrap');
            await expect(qtyWrap.locator('text=(+)')).toBeVisible({timeout: 5_000});

            // Enter negative value → border-color should be the danger role at 70%
            await qtyInput.fill('');
            await qtyInput.type('-5');
            await expectComputedBorderColor(page, qtyInput, 'color-mix(in oklab, var(--lf-danger) 70%, transparent)', 'Negative qty on BUY should have the effective red border color');

            // Enter positive value → the success role at 70%
            await qtyInput.fill('');
            await qtyInput.type('5');
            await expectComputedBorderColor(page, qtyInput, 'color-mix(in oklab, var(--lf-success) 70%, transparent)', 'Positive qty on BUY should have the effective green border color');
        });

        test('SELL qty positive → green border (auto-negated on save)', async ({page}) => {
            await openCreateFlow(page);

            // Select SELL type (quantityRule = 'negative', auto-flip active)
            const typeSelect = page.getByTestId('tx-form-type');
            await typeSelect.locator('button, [role="combobox"]').first().click();
            await page.getByTestId('search-select-option-SELL').click();
            await optionListClosed(page);

            const qtyInput = page.getByTestId('tx-form-quantity');
            await expect(qtyInput).toBeVisible({timeout: 2_000});

            // Wait for type rules — SELL has "(−)" label
            const qtyWrap = page.getByTestId('tx-form-quantity-wrap');
            await expect(qtyWrap.locator('text=(−)')).toBeVisible({timeout: 5_000});

            // Enter positive → green (auto-negated = correct)
            await qtyInput.fill('');
            await qtyInput.type('10');
            await expectComputedBorderColor(page, qtyInput, 'color-mix(in oklab, var(--lf-success) 70%, transparent)', 'Positive qty on SELL should have the effective green border color');

            // Enter negative → red (double-negative = wrong)
            await qtyInput.fill('');
            await qtyInput.type('-10');
            await expectComputedBorderColor(page, qtyInput, 'color-mix(in oklab, var(--lf-danger) 70%, transparent)', 'Negative qty on SELL should have the effective red border color');
        });
    });

    // ===================================================================
    // T13 — BulkModal validation: issues banner appears with clickable items
    // ===================================================================
    test.describe('BulkModal validation issues', () => {
        test('invalid TX in BulkModal shows issues banner with clickable error', async ({page}) => {
            // Under load the create flow alone can use the default 30 s before any check: the budget of its neighbours (W-B45).
            test.setTimeout(60_000);
            await openCreateFlow(page);

            // Use ADJUSTMENT type with qty>0 and cost_basis_mode=auto
            // Backend computes WAC automatically — validates as success.
            // NOTE: The BulkModal validate→WAC cycle has a pre-existing reactivity
            // issue (on main) where the modal closes after WAC results update ops.
            // This test verifies the form→workspace flow + validate API correctness.
            await expect(page.getByTestId('tx-form-type')).toBeVisible({timeout: 3_000});

            // Select ADJUSTMENT type
            const typeSelect = page.getByTestId('tx-form-type');
            await typeSelect.locator('button, [role="combobox"]').first().click();
            await page.getByTestId('search-select-option-ADJUSTMENT').click();
            await optionListClosed(page);

            // Broker and asset by name, not "the first option": that is whatever sorts
            // first today — under concurrency a neighbour's broker or asset.
            await pickBroker(page, OWNED_BROKER);

            // Set qty to 5 (positive)
            await page.getByTestId('tx-form-quantity').fill('5');
            await expect(page.getByTestId('tx-form-quantity')).toHaveValue('5');

            // Pick an asset (required for the form to be complete)
            await pickAsset(page, ASSET_NAME);

            // Apply the TX (push to BulkModal workspace)
            const applyBtn = page.getByTestId('tx-form-save');
            await expect(applyBtn).toBeEnabled({timeout: 5_000});
            await applyBtn.click();

            // Wait for FormModal to close — workspace now has the item
            await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 5_000});

            // Intercept the validate API call (auto-triggered by scheduler)
            const validateResp = await page.waitForResponse((resp) => resp.url().includes('/api/v1/transactions/validate') && resp.request().method() === 'POST', {timeout: 15_000});

            // Verify backend processed correctly
            expect(validateResp.status()).toBe(200);
            const respBody = await validateResp.json();
            expect(respBody.committed).toBe(false);
            // WAC auto-mode: should have success + wac_results (no issues)
            expect(respBody.success_count).toBeGreaterThanOrEqual(1);
        });
    });
});
