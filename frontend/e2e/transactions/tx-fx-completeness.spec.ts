/**
 * tx-fx-completeness.spec.ts — FX_CONVERSION dual-form completeness regression.
 *
 * Covers the fix in TransactionFormModal.svelte where the FX "To" broker was
 * tracked on a separate `dualTo.broker_id` field that stayed at its `0`
 * sentinel whenever the user picked a broker *before* switching the type to
 * FX_CONVERSION (single-mode broker field → dual-mode broker field are the
 * same `draft.broker_id`, but the old readiness check read `dualTo.broker_id`
 * instead). The invisible mismatch made `isFormComplete` stay false forever,
 * silently disabling Apply/Validate with no visible cause.
 *
 * The fix introduces `effectiveDualTo` (broker forced from `draft.broker_id`
 * for an editable FX draft) and also tightened `fromTx()` to normalize a
 * paired leg's cash to a positive magnitude — otherwise reopening a staged
 * local FX pair (From leg stored with a negative amount) fed a negative
 * number back into a "positive" sign-hint field and re-blocked Apply on a
 * pair nobody had touched. That normalization is a plain sign-strip
 * (`cash.amount.replace(/^-/, '')`), deliberately not `Math.abs(Number(...))`:
 * the latter round-trips the decimal string through a JS double and silently
 * rounds any amount with more precision than a double can hold. Test 1 uses
 * an 18-significant-digit amount (the exact edge of the DB's `NUMERIC(18,6)`
 * column) specifically because it demonstrates that loss when parsed as a
 * float, and asserts the exact string survives Apply → reopen unchanged.
 *
 * What this file does NOT assume, and checks instead:
 *  - that the From/To date fields are two independent pieces of state, and
 *    DISTINCT dates are a legitimate FX shape, not an error: the collector
 *    has no equal-dates guard (`txPayloadHelpers.ts`: the "to" item's date is
 *    `to.date || from.date`, never forced equal to the "from" date), and
 *    `effectiveDualTo` only ever forces the *broker* from the source draft,
 *    never the date (see `setDate`/`setDateTo` — neither touches the other
 *    side). Test 1 sets two different, non-today dates and asserts they
 *    reach the wire payload distinctly and both round-trip, unmixed, through
 *    Apply → reopen.
 *  - that Apply (`tx-form-save` with `commitOnSave=false`, as BulkModal always
 *    sets) never calls `/transactions/commit` — verified by a live request
 *    listener, not by inference from the UI staying open.
 *  - that a funded commit and an insufficient-funds commit are told apart by
 *    a real backend balance walk (broker created via API, funded via a real
 *    committed DEPOSIT, default `allow_cash_overdraft=false` — never bypassed).
 *
 * Prerequisites: backend test mode (port 6041), mock data populated.
 * Every broker/transaction this file writes is created through the API with
 * a `uniqueSuffix()`-tagged name; every committed transaction id is deleted
 * in a `finally` block. Tests that never reach `/transactions/commit` (1 and
 * 2) leave nothing behind and skip cleanup entirely.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {daysAgoIso, todayIso} from '../fixtures/dates';
import type {TXReadItem} from '../../src/lib/components/transactions/types';

const API = '/api/v1';

test.setTimeout(30_000);

// ---------------------------------------------------------------------------
// Navigation / setup helpers
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('tx-table')).toBeVisible({timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'));
}

/** Open the create flow: BulkModal (intent 'create') auto-opens a nested,
 *  empty FormModal because the grid starts empty. */
async function openCreateFlow(page: Page): Promise<{bulkModal: Locator; formModal: Locator}> {
    await page.getByTestId('tx-add-button').click();
    const bulkModal = page.getByTestId('tx-bulk-modal');
    const formModal = page.getByTestId('tx-form-modal');
    await expect(bulkModal).toBeVisible({timeout: 5_000});
    await expect(formModal).toBeVisible({timeout: 5_000});
    return {bulkModal, formModal};
}

async function openSearchSelect(trigger: Locator): Promise<void> {
    await expect(async () => {
        if ((await trigger.getAttribute('aria-expanded')) !== 'true') {
            await trigger.click();
        }
        expect(await trigger.getAttribute('aria-expanded')).toBe('true');
    }).toPass({timeout: 3_000});
}

/** Pick a specific broker by id — BrokerSearchSelect's option testid is the
 *  numeric broker id itself (`search-select-option-{id}`), so this is exact,
 *  never a text match. */
async function pickBroker(page: Page, brokerId: number): Promise<void> {
    const wrap = page.getByTestId('tx-form-broker-wrap');
    await openSearchSelect(wrap.getByRole('combobox'));
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

async function selectFxType(page: Page): Promise<void> {
    await openSearchSelect(page.getByTestId('tx-form-type').getByRole('combobox'));
    const option = page.getByTestId('search-select-option-FX_CONVERSION');
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
    await expect(page.getByTestId('tx-form-dual-split')).toBeVisible({timeout: 3_000});
}

/** Fill a CompactCashCell's amount and commit it with Tab (fires blur, which
 *  normalizes the decimal separator/format — this is the behaviour under test
 *  for the comma-decimal case, so callers assert the resulting value themselves). */
async function fillCashAmount(page: Page, testid: string, raw: string): Promise<void> {
    const input = page.getByTestId(`${testid}-amount`);
    await expect(input).toBeVisible({timeout: 2_000});
    await input.fill(raw);
    await input.press('Tab');
}

/** SingleDatePicker renders its input with the SAME default testid
 *  ("single-date-picker") whether it is the From or the To side — the
 *  component only guarantees uniqueness when a caller passes an explicit
 *  `testid`, which TransactionFormModal does not for either dual-date field.
 *  So every date lookup here is scoped to its own panel (tx-form-dual-from /
 *  tx-form-dual-to), never a bare page-level getByTestId. */
function dualDateInput(panel: Locator): Locator {
    return panel.getByTestId('single-date-picker-root').getByRole('textbox');
}

/** Type an ISO date and commit with Enter — Enter both calls `commitTyped()`
 *  and closes the calendar popover in one step, unlike Tab (which commits but
 *  leaves the popover open as a stray overlay for later interactions). */
async function setDualDate(panel: Locator, iso: string): Promise<void> {
    const input = dualDateInput(panel);
    await expect(input).toBeVisible({timeout: 2_000});
    await input.fill(iso);
    await input.press('Enter');
    await expect(input).toHaveValue(iso);
}

async function selectCurrency(page: Page, cashTestid: string, code: string): Promise<void> {
    const wrap = page.getByTestId(cashTestid);
    await openSearchSelect(wrap.getByRole('combobox'));
    const listbox = page.getByRole('listbox');
    await expect(listbox).toBeVisible({timeout: 3_000});
    await expect(listbox).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
    const searchInput = wrap.getByRole('combobox').getByRole('textbox');
    await expect(searchInput).toBeVisible({timeout: 3_000});
    await searchInput.fill(code);
    const option = page.getByTestId(`search-select-option-${code}`);
    await expect(option).toBeVisible({timeout: 3_000});
    await option.click();
    await optionsClosed(page);
}

// ---------------------------------------------------------------------------
// API helpers — real broker + real funding, no overdraft bypass
// ---------------------------------------------------------------------------

async function createOwnedBroker(page: Page, label: string): Promise<number> {
    const suffix = uniqueSuffix();
    const resp = await page.request.post(`${API}/brokers`, {data: [{name: `TXFX-${label}-${suffix}`}]});
    expect(resp.ok(), `broker setup failed (HTTP ${resp.status()})`).toBeTruthy();
    const body = await resp.json();
    return body.results[0].broker_id as number;
}

const ownedBrokerIds = new WeakMap<Page, number[]>();

function rememberOwnedBroker(page: Page, brokerId: number): void {
    const ids = ownedBrokerIds.get(page) ?? [];
    ids.push(brokerId);
    ownedBrokerIds.set(page, ids);
}

async function cleanupOwnedBrokers(page: Page): Promise<void> {
    const ids = ownedBrokerIds.get(page) ?? [];
    ownedBrokerIds.delete(page);
    for (const brokerId of ids) {
        const resp = await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`);
        expect(resp.ok(), `cleanup broker ${brokerId} failed (HTTP ${resp.status()})`).toBeTruthy();
        const body = (await resp.json()) as {results?: Array<{id: number; success: boolean}>};
        expect(body.results?.find((result) => result.id === brokerId)?.success, `cleanup broker ${brokerId} was not successful`).toBe(true);
    }
}

/** Fund a broker with a real, committed DEPOSIT in EUR — the source currency
 *  for every FX conversion below. `allow_cash_overdraft` is left at its
 *  schema default (`false`): the balance guard is never disabled, only
 *  legitimately satisfied. Returns the deposit's transaction id (for cleanup). */
async function fundBrokerEur(page: Page, brokerId: number, amount: string, label: string): Promise<number> {
    const resp = await page.request.post(`${API}/transactions/commit`, {
        data: {creates: [{broker_id: brokerId, type: 'DEPOSIT', date: todayIso(), cash: {code: 'EUR', amount}, description: `TXFX seed ${label}`}]},
    });
    const body = await resp.json();
    expect(body.committed, `funding deposit rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return body.results[0].ids[0] as number;
}

async function deleteTx(page: Page, ids: number[]): Promise<void> {
    const real = ids.filter((id) => Number.isInteger(id) && id > 0);
    if (real.length === 0) return;
    await page.request.post(`${API}/transactions/commit`, {data: {deletes: real}});
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('FX_CONVERSION dual-form completeness', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
    });

    test.afterEach(async ({page}) => {
        await cleanupOwnedBrokers(page);
    });

    test('broker chosen before FX type, decimal formats normalize, and Apply stages a linked local pair with no network commit', async ({page}) => {
        const brokerId = await createOwnedBroker(page, 'first');
        rememberOwnedBroker(page, brokerId);

        await goToTransactions(page);

        let commitCalls = 0;
        page.on('request', (req) => {
            if (req.method() === 'POST' && req.url().includes('/transactions/commit')) commitCalls++;
        });

        const {bulkModal, formModal} = await openCreateFlow(page);

        // Regression scenario: broker picked while the form is still in
        // single-mode (default type BUY), THEN the type is switched to
        // FX_CONVERSION. Before the fix, `dualTo.broker_id` (a separate field
        // from `draft.broker_id`) never got synced in this order, so the FX
        // "To" side silently had an unset (0) broker even though the visible
        // shared-broker field showed the correct one.
        await pickBroker(page, brokerId);
        await selectFxType(page);

        const fromPanel = page.getByTestId('tx-form-dual-from');
        const toPanel = page.getByTestId('tx-form-dual-to');
        const saveBtn = page.getByTestId('tx-form-save');
        const validateBtn = page.getByTestId('tx-form-validate-now');

        // Canonical decimal on the From leg (currency defaults to EUR).
        // 18 significant digits (12 integer + 6 fraction — the exact edge of
        // the DB's NUMERIC(18,6) column) deliberately exceeds what a JS double
        // can round-trip: `String(Math.abs(Number('-123456789012.123456')))`
        // collapses to `'123456789012.12346'`, silently dropping precision.
        // `fromTx()` must never go through Number() for this — only a plain
        // sign-strip preserves every digit through Apply → reopen below.
        const FROM_AMOUNT = '123456789012.123456';
        await fillCashAmount(page, 'tx-form-cash-from', FROM_AMOUNT);
        await expect(page.getByTestId('tx-form-cash-from-amount')).toHaveValue(FROM_AMOUNT);

        // To leg still untouched — no amount, no currency committed yet. Both
        // gates must stay closed: this is the "missing leg" case, not a guess.
        await expect(saveBtn).toBeDisabled();
        await expect(validateBtn).toBeDisabled();

        // Comma decimal on the To leg (currency defaults to USD) — normalizes
        // to canonical dot form on blur.
        await fillCashAmount(page, 'tx-form-cash-to', '2200,75');
        await expect(page.getByTestId('tx-form-cash-to-amount')).toHaveValue('2200.75');

        // Both legs complete, broker resolved from the source (not a stale
        // separate field), both currencies present and different → the fixed
        // readiness gate opens.
        await expect(validateBtn).toBeEnabled({timeout: 3_000});
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // Distinct FX dates are a legitimate shape, not an error: the
        // collector has no equal-dates guard (txPayloadHelpers.ts — the "to"
        // item's date is `to.date || from.date`, never forced equal to it),
        // and `effectiveDualTo` only ever forces the *broker* from the source
        // draft, never the date. Each date editor is independent state (see
        // setDate/setDateTo), and the fix only made both of them *required*.
        const fromDate = daysAgoIso(5);
        const toDate = daysAgoIso(2);
        await setDualDate(fromPanel, fromDate);
        await setDualDate(toPanel, toDate);
        await expect(saveBtn).toBeEnabled(); // still complete: both distinct dates are present, that's all that's required
        await expect(validateBtn).toBeEnabled();

        // The wire payload must carry each leg's own date — captured from the
        // real /validate call the completeness gate enables, not inferred
        // from the UI. Index 0/1 is exact here: this is the only row in an
        // otherwise-empty grid, and buildDualCreatePayloads always returns
        // [fromItem, toItem] in that order.
        const validateRequest = page.waitForRequest((r) => r.method() === 'POST' && r.url().includes('/transactions/validate'));
        await validateBtn.click();
        const req = await validateRequest;
        const validateBody = req.postDataJSON() as {creates?: Array<{date?: string}>};
        expect(validateBody.creates?.[0]?.date, 'the From leg must keep its own date on the wire').toBe(fromDate);
        expect(validateBody.creates?.[1]?.date, 'the To leg must keep its own date on the wire, not the From date').toBe(toDate);

        await saveBtn.click();
        await expect(formModal).not.toBeVisible({timeout: 5_000});
        await expect(bulkModal).toBeVisible();

        // Apply staged exactly the one row this test created — never a commit.
        const appendedRows = bulkModal.locator('tbody tr[data-row-id]');
        await expect(appendedRows).toHaveCount(1, {timeout: 5_000});
        const appended = appendedRows.first();
        await expect(appended).toBeVisible({timeout: 5_000});
        const appendedRowId = await appended.getAttribute('data-row-id');
        expect(appendedRowId, 'the staged FX row must have a row id').toBeTruthy();
        expect(commitCalls, 'Apply (commitOnSave=false) must never reach /transactions/commit').toBe(0);

        // Reopen the local pair: `fromTx()` must hand back a POSITIVE magnitude
        // for the From leg (it is stored internally as a negative amount), or
        // the "positive" sign guard would re-block Apply on a pair nobody edited.
        // It must ALSO hand back the exact digits it was given — the tightened
        // fix (`cash.amount.replace(/^-/, '')`) never round-trips through a JS
        // Number, unlike the old `String(Math.abs(Number(cash.amount)))`.
        await appended.hover();
        const kebab = appended.getByTestId(`row-actions-${appendedRowId}`);
        await expect(kebab).toBeVisible({timeout: 2_000});
        await kebab.click();
        await page.getByTestId('context-menu-action-edit-single').click();
        await expect(formModal).toBeVisible({timeout: 5_000});

        // Exact string match, not just numeric equality: a reopened value of
        // '123456789012.12346' would also satisfy `Number(x) === Number(FROM_AMOUNT)`
        // to float precision, but it is not the value the user typed.
        await expect(page.getByTestId('tx-form-cash-from-amount')).toHaveValue(FROM_AMOUNT);
        await expect(page.getByTestId('tx-form-cash-to-amount')).toHaveValue('2200.75');
        // Each leg's distinct date must round-trip on its own side — no
        // silent overwrite by the other leg, and no collapse to a shared date.
        await expect(dualDateInput(fromPanel)).toHaveValue(fromDate);
        await expect(dualDateInput(toPanel)).toHaveValue(toDate);
        await expect(page.getByTestId('tx-form-save')).toBeEnabled();
        await expect(page.getByTestId('tx-form-validate-now')).toBeEnabled();

        // Nothing was edited after reopening — Cancel must close directly,
        // no "discard changes?" prompt, no commit anywhere in this test.
        await page.getByTestId('tx-form-cancel').click();
        await expect(formModal).not.toBeVisible({timeout: 3_000});
        expect(commitCalls).toBe(0);
    });

    test('FX guard rails: a missing leg, equal currencies, and a negative or zero amount all keep Apply blocked', async ({page}) => {
        const brokerId = await createOwnedBroker(page, 'second');
        rememberOwnedBroker(page, brokerId);

        await goToTransactions(page);
        await openCreateFlow(page);

        await pickBroker(page, brokerId);
        await selectFxType(page);

        const saveBtn = page.getByTestId('tx-form-save');
        const validateBtn = page.getByTestId('tx-form-validate-now');
        const dualError = page.getByTestId('tx-form-dual-error');

        await fillCashAmount(page, 'tx-form-cash-from', '1000');

        // 1) To leg untouched: missing amount AND currency.
        await expect(saveBtn).toBeDisabled();
        await expect(validateBtn).toBeDisabled();

        await fillCashAmount(page, 'tx-form-cash-to', '1050');
        await expect(validateBtn).toBeEnabled({timeout: 3_000});
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // 2) Equal currencies: force the To side onto the From side's currency.
        await selectCurrency(page, 'tx-form-cash-to', 'EUR');
        await expect(dualError).toBeVisible({timeout: 3_000});
        await expect(saveBtn).toBeDisabled();

        // Restore distinct currencies before the next sub-case.
        await selectCurrency(page, 'tx-form-cash-to', 'USD');
        await expect(dualError).not.toBeVisible({timeout: 3_000});
        await expect(saveBtn).toBeEnabled({timeout: 3_000});

        // 3) Negative To amount: finite and non-zero, so isFormComplete alone
        // would allow it — Validate stays enabled, but the receiver-negatives
        // sign guard specifically blocks Save.
        await fillCashAmount(page, 'tx-form-cash-to', '-50');
        await expect(validateBtn).toBeEnabled();
        await expect(saveBtn).toBeDisabled();

        // 4) Zero To amount: isFormComplete itself rejects a zero amount —
        // both gates close together.
        await fillCashAmount(page, 'tx-form-cash-to', '0');
        await expect(validateBtn).toBeDisabled();
        await expect(saveBtn).toBeDisabled();
    });

    test('SaveAll commits a funded FX pair for real, and GET readback proves the linked DB pair', async ({page}) => {
        const label = `c${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, label);
        rememberOwnedBroker(page, brokerId);
        const depositId = await fundBrokerEur(page, brokerId, '500', label);
        let createdIds: number[] = [];

        try {
            await goToTransactions(page);
            const {bulkModal, formModal} = await openCreateFlow(page);

            await pickBroker(page, brokerId);
            await selectFxType(page);

            await fillCashAmount(page, 'tx-form-cash-from', '200');
            await fillCashAmount(page, 'tx-form-cash-to', '220');

            const saveBtn = page.getByTestId('tx-form-save');
            await expect(saveBtn).toBeEnabled({timeout: 3_000});
            await saveBtn.click();
            await expect(formModal).not.toBeVisible({timeout: 5_000});

            const commitBtn = page.getByTestId('tx-bulk-commit');
            await expect(commitBtn).toBeEnabled({timeout: 5_000});
            const commitResponse = page.waitForResponse((r) => r.request().method() === 'POST' && r.url().includes('/transactions/commit'));
            await commitBtn.click();
            const resp = await commitResponse;
            const body = await resp.json();
            expect(body.committed, `funded FX commit rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);

            createdIds = (body.results as Array<{operation: string; ids: number[]}>).filter((r) => r.operation === 'create').flatMap((r) => r.ids);
            expect(createdIds.length, 'a paired FX create must resolve to exactly two rows').toBe(2);

            // A real commit closes the workspace — this is the app's own signal
            // that the batch actually landed, not an assumption on our part.
            await expect(bulkModal).not.toBeVisible({timeout: 10_000});

            const readback = await page.request.get(`${API}/transactions?ids=${createdIds[0]}&ids=${createdIds[1]}`);
            expect(readback.ok()).toBeTruthy();
            const rows = (await readback.json()) as TXReadItem[];
            expect(rows.length).toBe(2);
            for (const row of rows) {
                expect(row.broker_id).toBe(brokerId);
                expect(row.type).toBe('FX_CONVERSION');
            }
            const [a, b] = rows;
            expect(a.date).toBe(b.date);
            expect(a.related_transaction_id).toBe(b.id);
            expect(b.related_transaction_id).toBe(a.id);

            const amounts = rows.map((r) => Number(r.cash?.amount ?? 0)).sort((x, y) => x - y);
            expect(amounts[0], 'the funding-side leg must be negative').toBeLessThan(0);
            expect(amounts[1], 'the receiving-side leg must be positive').toBeGreaterThan(0);
            const codes = new Set(rows.map((r) => r.cash?.code));
            expect(codes.has('EUR') && codes.has('USD')).toBe(true);
        } finally {
            await deleteTx(page, [...createdIds, depositId]);
        }
    });

    test('insufficient funds blocks the commit — no partial rows are created', async ({page}) => {
        const label = `u${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, label);
        rememberOwnedBroker(page, brokerId);
        const depositId = await fundBrokerEur(page, brokerId, '10', label);

        try {
            await goToTransactions(page);
            const {bulkModal, formModal} = await openCreateFlow(page);

            await pickBroker(page, brokerId);
            await selectFxType(page);

            // Far beyond the 10 EUR funded. Apply itself does not see balances
            // (only SaveAll's server-side walk does), so this must reach the
            // grid and only be rejected at commit time.
            await fillCashAmount(page, 'tx-form-cash-from', '5000');
            await fillCashAmount(page, 'tx-form-cash-to', '5400');

            const saveBtn = page.getByTestId('tx-form-save');
            await expect(saveBtn).toBeEnabled({timeout: 3_000});
            await saveBtn.click();
            await expect(formModal).not.toBeVisible({timeout: 5_000});

            const commitBtn = page.getByTestId('tx-bulk-commit');
            await expect(commitBtn).toBeEnabled({timeout: 5_000});
            const commitResponse = page.waitForResponse((r) => r.request().method() === 'POST' && r.url().includes('/transactions/commit'));
            await commitBtn.click();
            const resp = await commitResponse;
            const body = await resp.json();
            expect(body.committed, 'an overdraft must never be silently committed').toBe(false);

            // The workspace stays open with a persistent error banner — this
            // is the product's own contract for a rolled-back batch.
            await expect(bulkModal).toBeVisible();
            await expect(page.getByTestId('tx-bulk-error')).toBeVisible({timeout: 3_000});

            const readback = await page.request.get(`${API}/transactions?broker_id=${brokerId}`);
            expect(readback.ok()).toBeTruthy();
            const rows = (await readback.json()) as Array<{type: string}>;
            expect(
                rows.some((r) => r.type === 'FX_CONVERSION'),
                'a rejected commit must not leave a partial FX row behind',
            ).toBe(false);
        } finally {
            await deleteTx(page, [depositId]);
        }
    });
});
