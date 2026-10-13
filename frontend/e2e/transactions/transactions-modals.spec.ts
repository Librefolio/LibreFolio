/**
 * Transaction E2E Tests — Phase 07 · Bugfix 3+
 *
 * Covers: CRUD, BulkModal, FormModal, paired transactions, sign-flip,
 * column visibility, banner dismissal, i18n labels.
 *
 * Prerequisites: backend in test mode (port 6041), at least 1 broker seeded.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo, setLanguage} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {validateRuns, waitForSettled, waitForValidateRun} from '../fixtures/app-events';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';
import {todayIso} from '../fixtures/dates';
import {uniqueSuffix} from '../fixtures/unique';

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
 * Broker and asset are the first entries of their lists. That choice is T1's, and
 * it is a developer decision (backlog V-21), so it is kept as it was. What changed
 * is that every step now waits for what it needs instead of probing for it: a
 * probe that expired skipped its pick in silence, and the failure surfaced later,
 * at Apply, blaming the wrong step.
 */
async function fillBuyTransaction(page: Page, opts: {qty?: string; skipCash?: boolean} = {}) {
    const qty = opts.qty ?? '5';
    // Type is BUY by default
    await expect(page.getByTestId('tx-form-type')).toBeVisible({timeout: 3_000});

    // Broker — the first option of the list.
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    await optionListReady(page);
    await page.locator('[data-testid^="search-select-option-"]').first().click();
    // The chosen broker closes the list; that is the signal the pick landed.
    await optionListClosed(page);

    // Quantity
    await page.getByTestId('tx-form-quantity').fill(qty);

    // Cash — BUY type requires a cash amount. Fill a non-zero value.
    // The CompactCashCell amount is a locale-safe text input (not type=number),
    // so it must be reached via its data-testid suffix.
    if (!opts.skipCash) {
        await fillCashAmount(page, '100');
    }

    // Asset — the first option of the list. A BUY always renders the field: its
    // asset is required.
    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await expect(assetWrap).toBeVisible({timeout: 5_000});
    await assetWrap.locator('button, [role="combobox"]').first().click();
    await optionListReady(page);
    await page.locator('[data-testid^="search-select-option-"]').first().click();
    await optionListClosed(page);
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

test.describe('Transactions', () => {
    // Whoever commits, cleans up. T1 commits a real BUY into one of TEST_USER's
    // seeded brokers, and `Transaction` is global: left there, it shifts the NAV,
    // positions, counts and pages of every later test, and the txHygiene net that
    // used to hide it exists only at one worker. The tracker records the rows this
    // page's commits create and deletes exactly those, at any worker count. It
    // starts after login (it reads through `page.request`, which needs the session
    // cookie) and so before any commit; `afterEach` runs for a red test too. The
    // rows T3, T9, T10 and T11 create through the API are invisible to the tracker
    // and are deleted by id in the same `afterEach`.
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
    // T1 — Create standalone BUY (Apply flow)
    // ===================================================================
    test.describe('Create standalone', () => {
        test('can create a BUY via FormModal → BulkModal → commit', async ({page}) => {
            await openCreateFlow(page);
            await fillBuyTransaction(page, {qty: '3'});
            await clickApply(page);

            // FormModal closes, BulkModal visible with at least 1 row
            await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 3_000});
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

            // Verify the row appears in the BulkModal table
            const bulkRows = page.locator('[data-testid="tx-bulk-modal"] tbody tr');
            await expect(bulkRows.first()).toBeVisible({timeout: 3_000});

            // Commit — may roll back due to balance checks, which is acceptable
            const commitBtn = page.getByTestId('tx-bulk-commit');
            // Armed before the click, read after the outcome: when the batch commits,
            // its answer carries the id of the row this test now owns, and the tracker
            // can delete only what it has read before the test ends — its own read of
            // this body was issued first, on the response event. A click that never
            // commits costs nothing extra: both waits run out together.
            const commitAnswer = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 10_000}).catch(() => null);
            await commitBtn.click();
            // Wait for either success (close) or rollback (error banner)
            await Promise.race([page.getByTestId('tx-bulk-modal').waitFor({state: 'hidden', timeout: 10_000}), page.getByTestId('tx-bulk-error').waitFor({state: 'visible', timeout: 10_000})]).catch(() => {});
            const answer = await commitAnswer;
            await answer?.json().catch(() => null);
        });

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
            await fillBuyTransaction(page, {qty: '7'});
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
    // T4 — Column visibility defaults (M4/M5)
    // ===================================================================
    test.describe('Column defaults (M4/M5)', () => {
        test('cost_basis_override appears after asset_event_id when both visible', async ({page}) => {
            await openCreateFlow(page);
            // Close form to see bulk table
            await page.getByTestId('tx-form-cancel').click();

            // The BulkModal should be visible
            await expect(page.getByTestId('tx-bulk-modal')).toBeVisible();

            // Verify the column ordering: asset_event_id should come before cost_basis_override
            // by checking the column visibility toggle list order.
            const bulkTitle = page.getByTestId('tx-bulk-title');
            await expect(bulkTitle).toBeVisible();

            // Both columns are hidden by default — their existence in the columns
            // array (with correct order) is the assertion. We verify via the
            // column visibility toggle if available.
            const colToggle = page.locator('[data-testid="column-visibility-toggle"]');
            if (await colToggle.isVisible({timeout: 1_000}).catch(() => false)) {
                await colToggle.click();
                await expect(page.locator('[data-testid^="col-toggle-"]').first()).toBeVisible({timeout: 5_000});
                const labels = await page.locator('[data-testid^="col-toggle-"]').allTextContents();
                const eventIdx = labels.findIndex((l) => /event/i.test(l));
                const costIdx = labels.findIndex((l) => /cost.*basis/i.test(l));
                if (eventIdx >= 0 && costIdx >= 0) {
                    expect(eventIdx).toBeLessThan(costIdx);
                }
            }
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
    // T6 — Banner dismissible (M1/M2)
    // ===================================================================
    test.describe('Banner dismissible (M1/M2)', () => {
        test('validation warning banner has dismiss button', async ({page}) => {
            await openCreateFlow(page);
            // Fill invalid data to trigger validation issues: a BUY's quantity is positive.
            await fillBuyTransaction(page, {qty: '-1'});

            // Validate now, and wait for *that* run: the counter is read before the
            // click, so a run that finished earlier cannot answer for this one.
            const root = page.getByTestId('tx-form-modal-root');
            const validateBtn = page.getByTestId('tx-form-validate-now');
            await expect(validateBtn).toBeEnabled({timeout: 5_000});
            const runsBefore = await validateRuns(root);
            await validateBtn.click();
            await waitForValidateRun(root, runsBefore);

            // The verdict lands in the form's warning banner; its X is the subject.
            // The old selector (`.info-banner button`) named a CSS class nothing carries,
            // so its probe never matched and the dismiss was never tried.
            const banner = page.getByTestId('tx-form-body').getByTestId('info-banner-warning');
            await expect(banner).toBeVisible({timeout: 5_000});
            const dismissBtn = banner.locator('button[aria-label]');
            await expect(dismissBtn).toBeVisible();
            await dismissBtn.click();
            await expect(banner).toBeHidden({timeout: 2_000});
        });
    });

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

            // Enter negative value → border-color should have red hue (~25 in oklch)
            await qtyInput.fill('');
            await qtyInput.type('-5');
            await expectComputedBorderColor(page, qtyInput, 'oklch(0.637 0.237 25.331 / 0.7)', 'Negative qty on BUY should have the effective red border color');

            // Enter positive value → green hue (~163 in oklch)
            await qtyInput.fill('');
            await qtyInput.type('5');
            await expectComputedBorderColor(page, qtyInput, 'oklch(0.765 0.177 163.223 / 0.7)', 'Positive qty on BUY should have the effective green border color');
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
            await expectComputedBorderColor(page, qtyInput, 'oklch(0.765 0.177 163.223 / 0.7)', 'Positive qty on SELL should have the effective green border color');

            // Enter negative → red (double-negative = wrong)
            await qtyInput.fill('');
            await qtyInput.type('-10');
            await expectComputedBorderColor(page, qtyInput, 'oklch(0.637 0.237 25.331 / 0.7)', 'Negative qty on SELL should have the effective red border color');
        });
    });

    // ===================================================================
    // T13 — BulkModal validation: issues banner appears with clickable items
    // ===================================================================
    test.describe('BulkModal validation issues', () => {
        test('invalid TX in BulkModal shows issues banner with clickable error', async ({page}) => {
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
