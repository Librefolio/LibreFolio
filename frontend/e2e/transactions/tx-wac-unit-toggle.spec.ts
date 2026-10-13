/**
 * E2E Tests for the Cost Basis Override "Total/Per unit" display toggle.
 *
 * Background: `cost_basis_override` is always PER-UNIT at rest (DB, API,
 * FIFO Lot Engine, WAC engine, Portfolio Engine all multiply by quantity
 * wherever a total is needed — see wac_utils.py, lots_analysis_service.py,
 * portfolio_engine.py). This toggle only changes how the amount is
 * displayed/typed in WacPreviewSection — the underlying per-unit contract
 * never changes. Default is "Per unit" (legacy/unchanged behavior); "Total"
 * is opt-in and persisted per-user in localStorage.
 *
 * The critical correctness property tested here: typing a TOTAL while the
 * toggle is on "Total" must persist as total/quantity (per-unit) in the
 * actual commit payload — never the raw typed number.
 */
import {expect, test, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {trackTransactionWrites, type TransactionWriteTracker} from '../fixtures/db-cleanup';

interface CommitPayload {
    creates?: Record<string, unknown>[];
    updates?: Record<string, unknown>[];
    deletes?: unknown[];
    [key: string]: unknown;
}

/** The broker the mock contract makes TEST_USER's OWNER, and an asset it holds (populate_mock_data.py). */
const BROKER_NAME = 'Interactive Brokers';
const ASSET_NAME = 'Apple';

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    // The table being VISIBLE is not the table being LOADED: it renders empty
    // and fills in. The page publishes data-busy, so wait on that instead.
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await Promise.race([page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000}), page.getByTestId('tx-loading').waitFor({state: 'hidden', timeout: 20_000})]).catch(() => {});
}

async function openAdjustmentWithCostBasis(page: Page, quantity: string) {
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: 5_000});

    await page.getByTestId('tx-form-type').click();
    await page.getByTestId('search-select-option-ADJUSTMENT').click();
    // Every SearchSelect uses the same option testid prefix, so clicking `.first()`
    // on the NEXT dropdown while this one is still closing picks from the wrong
    // list. That — not latency — is what the sleeps here were covering.
    await optionsClosed(page);

    // Broker and asset by name. "The first option" is whatever sorts first today: under
    // concurrency that can be a neighbour's broker or asset, gone while this test commits
    // on it — and the commit test below does commit.
    const brokerWrap = page.getByTestId('tx-form-broker-wrap');
    await brokerWrap.locator('button, [role="combobox"]').first().click();
    const brokerOption = page.locator('[data-testid^="search-select-option-"]', {hasText: BROKER_NAME}).first();
    await expect(brokerOption).toBeVisible({timeout: 5_000});
    await brokerOption.click();
    await optionsClosed(page);

    const assetWrap = page.getByTestId('tx-form-asset-wrap');
    await assetWrap.locator('button, [role="combobox"]').first().click();
    // The asset select searches inline: its search box is the open trigger itself.
    const assetSearch = page.getByTestId('tx-form-asset-search');
    await expect(assetSearch).toBeVisible({timeout: 3_000});
    await assetSearch.fill(ASSET_NAME);
    // The list is debounced; the named entry arriving *is* the settle.
    const assetOption = page.locator('[data-testid^="search-select-option-"]', {hasText: ASSET_NAME}).first();
    await expect(assetOption).toBeVisible({timeout: 5_000});
    await assetOption.click();
    await optionsClosed(page);

    const qtyInput = page.getByTestId('tx-form-quantity');
    await qtyInput.fill(quantity);

    await expect(page.getByTestId('tx-form-cost-basis-inline')).toBeVisible({timeout: 3_000});
}

async function applyFormModal(page: Page) {
    const saveBtn = page.getByTestId('tx-form-save');
    await expect(saveBtn).toBeEnabled({timeout: 5_000});
    await saveBtn.click();
    await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 10_000});
}

async function commitBulkModal(page: Page): Promise<{payload: CommitPayload}> {
    const commitBtn = page.getByTestId('tx-bulk-commit');
    await expect(commitBtn).toBeEnabled({timeout: 8_000});
    const commitPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    // The answer is read as well: it carries the id of the row this test now owns,
    // and the tracker can delete only what it has read before the test ends — its
    // own read of this body was issued first, on the response event.
    const answerPromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const req = await commitPromise;
    const payload = req.postDataJSON() as CommitPayload;
    const answer = (await (await answerPromise).json()) as {committed?: boolean; issues?: unknown[]};
    expect(answer.committed, `commit was rolled back: ${JSON.stringify(answer.issues ?? [])}`).toBe(true);
    await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 10_000});
    return {payload};
}

test.describe('Cost Basis Override — Total/Per unit toggle', () => {
    // Whoever commits, cleans up. The commit-payload test writes a real ADJUSTMENT
    // into one of TEST_USER's seeded brokers, and `Transaction` is global: left
    // there, it shifts the positions, counts and pages of every later test, and the
    // txHygiene net that used to hide it exists only at one worker. The tracker
    // records the rows this page's commits create and deletes exactly those, at any
    // worker count. It starts after login (it reads through `page.request`, which
    // needs the session cookie) and so before any commit; `afterEach` runs for a red
    // test too.
    let txWrites: TransactionWriteTracker | undefined;

    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        txWrites = await trackTransactionWrites(page);
        await goToTransactions(page);
    });

    test.afterEach(async () => {
        const tracker = txWrites;
        txWrites = undefined;
        await tracker?.cleanup();
    });

    test('toggle is visible with "Per unit" selected by default', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '5');

        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle')).toBeVisible();
        const unitBtn = page.getByTestId('tx-form-cost-basis-unit-toggle-unit');
        const totalBtn = page.getByTestId('tx-form-cost-basis-unit-toggle-total');
        await expect(unitBtn).toBeVisible();
        await expect(totalBtn).toBeVisible();
        // Default state: "Per unit" is the pressed half. aria-pressed is the component
        // saying which mode it is in; the old `bg-gray-200` was a guess about how it looks.
        await expect(unitBtn).toHaveAttribute('aria-pressed', 'true');
        await expect(totalBtn).toHaveAttribute('aria-pressed', 'false');
    });

    test('manual entry round-trips correctly between Total and Per unit for a qty=5 lot', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '5');
        await page.getByTestId('tx-form-cost-basis-toggle-manual').click();

        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await cbInput.fill('100');
        // The conversion below reads this value, so it has to have landed. Note the
        // second half of this same test already fills and toggles with no sleep —
        // the sleep here was never the thing making it work.
        await expect(cbInput).toHaveValue('100');

        // Switch to Total — per-unit 100 x qty 5 = 500
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        await expect(cbInput).toHaveValue('500');

        // Type a new TOTAL (600) then switch back to Per unit — expect 120 (600 / 5)
        await cbInput.fill('600');
        await page.getByTestId('tx-form-cost-basis-unit-toggle-unit').click();
        await expect(cbInput).toHaveValue('120');
    });

    test('typing a Total for a qty=4 ADJUSTMENT persists the per-unit value in the commit payload', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '4');
        await page.getByTestId('tx-form-cost-basis-toggle-manual').click();
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        // The toggle rewrites the field; filling it before that lands would be
        // overwritten by the conversion. aria-pressed is the component saying which
        // mode it is in — a CSS class is a guess about how it looks.
        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle-total')).toHaveAttribute('aria-pressed', 'true');

        // Total cost basis for the whole 4-unit adjustment: 200 → per-unit must be 50.
        const cbInput = page.getByTestId('tx-form-cost-basis-input-amount');
        await cbInput.fill('200');
        await expect(cbInput).toHaveValue('200');

        await applyFormModal(page);
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});

        const {payload} = await commitBulkModal(page);
        const creates = payload.creates as Record<string, unknown>[];
        expect(creates?.length).toBeGreaterThanOrEqual(1);

        const withCostBasis = creates.find((c) => c.cost_basis_override != null && typeof c.cost_basis_override === 'object');
        expect(withCostBasis, 'A create item should carry a cost_basis_override object').toBeTruthy();
        const cbo = withCostBasis?.cost_basis_override as {code: string; amount: string};
        // Persisted amount must be per-unit (200 / 4 = 50), never the raw typed total (200).
        expect(Number(cbo.amount)).toBeCloseTo(50, 5);
    });

    test('toggle choice persists across closing and reopening the form (localStorage)', async ({page}) => {
        await openAdjustmentWithCostBasis(page, '3');
        await page.getByTestId('tx-form-cost-basis-unit-toggle-total').click();
        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle-total')).toHaveAttribute('aria-pressed', 'true');

        // Cancel the form (discards this draft). Type, broker, asset and quantity were
        // filled, so the draft differs from the one the form opened with and the form
        // always asks first: confirm it. (Probing for it turned "slow" into "absent".)
        await page.getByTestId('tx-form-cancel').click();
        const discardConfirm = page.getByTestId('confirm-modal-confirm');
        await expect(discardConfirm).toBeVisible({timeout: 5_000});
        await discardConfirm.click();
        await expect(page.getByTestId('tx-form-modal')).not.toBeVisible({timeout: 5_000});
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 5_000});
        // Nothing was ever applied to the workspace, so it closes without asking: an
        // untouched editor that asks to discard would be a regression, and the
        // assertion below would catch it instead of clicking it away.
        await page.getByTestId('tx-bulk-close').click();
        await expect(page.getByTestId('tx-bulk-modal')).not.toBeVisible({timeout: 5_000});

        // A completely fresh FormModal: the choice comes back from localStorage.
        await openAdjustmentWithCostBasis(page, '3');
        await expect(page.getByTestId('tx-form-cost-basis-unit-toggle-total')).toHaveAttribute('aria-pressed', 'true');
    });
});
