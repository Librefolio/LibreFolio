/**
 * «Clona» carries the linked-charges structure (lane 66, lot TL-3, FEE consultant).
 *
 * Today «Clona» copies a row (and for a pair its other half); the linked charges of a parent are not copied, and the copy
 * of a charge is born free. TL-3:
 *
 *   (1) Transactions page, «Clona» on a BUY with two linked charges → the Bulk holds the BUY copy and one copy of each
 *       charge, under it (`data-charge-of`), the group open, each copy on its original's date; saved → the new BUY has
 *       the two new charges, the originals are unchanged.
 *   (2) Page, «Clona» on a linked FEE alone → its copy is linked to the same parent; saved → that parent has one more.
 *   (3) Page, the BUY and one of its charges selected together → the charge copied once, under the BUY copy, the other
 *       charge read and copied too.
 *   (4) Page, the read of the parent's charges fails (GET …/transactions?parent_ids=… → 500, injected) → the BUY copy
 *       alone, event `tx.bulk.clone.charges-read-failed` and a warning toast.
 *   (5) Bulk, «Clona riga» on a charge under its parent → the copy appears under the same parent.
 *   (6) Bulk, a charge under a parent «del» («Delete all», so the charge is «del» too) → «Clona riga» → the copy is free
 *       (top-level), event `tx.bulk.clone.charge-free` with `detail.reason === 'deleted'`, and a warning toast.
 *   (7) Bulk, «Clona riga» on a parent whose group holds one charge «del», one «scollega» and one linked → only the
 *       linked one is copied.
 *   (8) Bulk (📌 consultant, to confirm visually), trash on the parent copy → its untouched charge copies leave with it;
 *       a copy whose amount was changed first stays, a free row.
 *   (9) Page, a linked FEE cloned alone, the copy's asset changed in its Form (row 5 of the lot's table) → the Form keeps
 *       the link (rule 3 is the backend's); the Bulk's validation flags `chargeAssetMismatch`; «Save all» is refused
 *       whole (`committed: false`, the issue on the copy), the Bulk stays open with the refusal, nothing is saved.
 *  (10) Page, a BUY cloned with its two charges, the BUY copy's asset changed in its Form → the charge copies stay under
 *       it with their own asset (rule 5, no magic); both flagged `chargeAssetMismatch`, «Save all» refused whole (the
 *       issues on the two charge copies, none on the BUY copy), nothing saved half-way.
 *
 * testids relied on: transactions-page · tx-table · tx-charges-badge-<id>[data-expanded] · dt-row-checkbox-tx-<id> ·
 * row-actions-* · context-menu-action-{clone,mark-delete,edit-single} · selection-toolbar[data-selected-count] ·
 * toolbar-action-{clone,edit} · tx-bulk-modal · tx-bulk-modal-root[data-busy] · tx-bulk-body · tx-bulk-row-label
 * [data-charge-of] · tx-bulk-row-status[data-status] · tx-bulk-charge-state[data-state] · tx-bulk-date[data-date] ·
 * tx-bulk-charges-toggle-<rowId>[aria-expanded][data-charges-count] · dt-row-checkbox-<rowId> · tx-bulk-commit ·
 * tx-charges-modal-content[data-mode] · tx-charges-modal-all · tx-form-modal · tx-form-cancel · tx-form-save ·
 * tx-form-parent[data-parent-id] · tx-form-charges[data-state] · tx-form-charge-row[data-charge-id] ·
 * tx-form-charge-unlink-* · tx-form-cash-wrap · toast-warning · tx-form-asset(-trigger[data-disabled][aria-expanded]
 * /-search) · search-select-option-<id> · tx-form-parent[data-state] · tx-bulk-issues-header · tx-bulk-error ·
 * tx-bulk-issue[data-code].
 * A saved Bulk row is found by the `#<id>` its ID cell shows; a copy by the description it shares with its original AND
 * the status «new» (`data-status="new"`): the copy of a row is never told apart by position. The verdict is the server:
 * the rows of the test's own broker, read back after the save.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns, funded by its own DEPOSIT): every
 * row on that broker is the test's, so the afterEach deletes them all, then the account. The charges are seeded on days
 * of their own, apart from the BUY's (rule 4: a charge's date is free) and from today, so «the copy keeps its original's
 * date» cannot be told apart from «it took the parent's» or «it was reset to today».
 *
 * A single row cloned from the page opens its Form on top of the Bulk today (`autoForm: 'create'`): the tests that
 * clone one row assert it and close it — they pin that behaviour; the grid is their subject.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {daysAgoIso} from '../fixtures/dates';
import {cleanupOwnedAccount, emptyOwnedAccount, jsonFrom, readTransactions, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';
import {COMMIT_PATH, openFundedAccount, readByIds, type ChargeTx, type CommitBody, type FundedAccount} from '../fixtures/linked-charges';

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// Seed: a BUY with linked charges on days of their own
// ---------------------------------------------------------------------------

type ChargeSpec = {key: string; type: 'FEE' | 'TAX'; amount: string; label: string; days: number};
type SeededCharge = ChargeSpec & {id: number; date: string; description: string};
type Seeded = FundedAccount & {buyId: number; buyDate: string; buyDescription: string; charges: Record<string, SeededCharge>; ids: number[]};

/** FEE and TAX on their own days (neither the BUY's nor today). */
const TWO_CHARGES: ChargeSpec[] = [
    {key: 'fee', type: 'FEE', amount: '-5', label: 'Fee A', days: 4},
    {key: 'tax', type: 'TAX', amount: '-2', label: 'Tax', days: 3},
];
/** (7): a second FEE beside them. */
const THREE_CHARGES: ChargeSpec[] = [...TWO_CHARGES, {key: 'feeB', type: 'FEE', amount: '-1', label: 'Fee B', days: 2}];
const BUY_DAYS = 6;

/** A funded account with a BUY and these charges committed linked to it in one batch (`ref` / `parent_ref`). The link
 *  and the dates are read back by id as the premise. */
async function seedBuyWithCharges(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string, specs: ChargeSpec[]): Promise<Seeded> {
    const funded = await openFundedAccount(page, request, owned, [], tag, 'TL3');
    const {broker, assetId, marker} = funded;
    const buyDate = daysAgoIso(BUY_DAYS);
    const buyDescription = `Buy ${marker}`;
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date: buyDate, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: buyDescription},
                    ...specs.map((c) => ({broker_id: broker.id, asset_id: assetId, type: c.type, date: daysAgoIso(c.days), quantity: '0', cash: {code: 'USD', amount: c.amount}, description: `${c.label} ${marker}`, parent_ref: 'p'})),
                ],
            },
        }),
        'commit the BUY with its linked charges',
    );
    expect(body.committed, `rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const idAt = (index: number): number => {
        const id = body.results?.find((item) => item.operation === 'create' && item.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`no id for create #${index}: ${JSON.stringify(body.results)}`);
        return id;
    };
    const buyId = idAt(0);
    const charges: Record<string, SeededCharge> = {};
    specs.forEach((c, at) => {
        charges[c.key] = {...c, id: idAt(at + 1), date: daysAgoIso(c.days), description: `${c.label} ${marker}`};
    });
    const ids = [funded.depositId, buyId, ...Object.values(charges).map((c) => c.id)];

    // The premise, read back rather than inferred: every charge points at the BUY, on its own date; the BUY counts them.
    const back = await readByIds(page, ids);
    for (const c of Object.values(charges)) {
        expect(back.get(c.id)?.parent_transaction_id, `premise: ${c.label} is linked to the BUY`).toBe(buyId);
        expect(back.get(c.id)?.date, `premise: ${c.label} keeps its own date`).toBe(c.date);
        expect(c.date, 'premise: a charge is not on the BUY’s day').not.toBe(buyDate);
    }
    expect(back.get(buyId)?.charges_count, 'premise: the BUY counts its charges').toBe(specs.length);
    // The verdict and the cleanup read the broker's listing: it must return every seeded row, the charges included.
    const listed = new Set((await readTransactions(page, {broker_id: broker.id})).map((tx) => tx.id));
    expect(
        ids.filter((id) => !listed.has(id)),
        'premise: the broker listing returns every seeded row, charges included',
    ).toEqual([]);
    return {...funded, buyId, buyDate, buyDescription, charges, ids};
}

/** Every row on the test's own broker, as the server has it now. */
async function brokerRows(page: Page, s: Seeded): Promise<ChargeTx[]> {
    return (await readTransactions(page, {broker_id: s.broker.id})) as unknown as ChargeTx[];
}

/** The rows of the test's broker that the seed did not write: what the Bulk saved. */
async function newRowsOnBroker(page: Page, s: Seeded): Promise<ChargeTx[]> {
    const seeded = new Set(s.ids);
    return (await brokerRows(page, s)).filter((tx) => !seeded.has(tx.id));
}

// ---------------------------------------------------------------------------
// The page
// ---------------------------------------------------------------------------

async function openTable(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

function txRow(page: Page, id: number): Locator {
    return page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${id}"]`);
}

/** Open the table's fold of the BUY so its charges are rows of the table. */
async function openTableFold(page: Page, s: Seeded): Promise<void> {
    const badge = txRow(page, s.buyId).getByTestId(`tx-charges-badge-${s.buyId}`);
    await expect(badge).toBeVisible({timeout: 8_000});
    if ((await badge.getAttribute('data-expanded')) !== 'true') await badge.click();
    await expect(badge).toHaveAttribute('data-expanded', 'true');
    for (const c of Object.values(s.charges)) await expect(txRow(page, c.id)).toBeVisible({timeout: 5_000});
}

async function ensureChecked(page: Page, id: number): Promise<void> {
    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
    await expect(checkbox).toBeVisible({timeout: 8_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
}

/** ⋮ on a table row → the action `actionId`. */
async function tableRowAction(page: Page, id: number, actionId: string): Promise<void> {
    const row = txRow(page, id);
    await expect(row).toBeVisible({timeout: 8_000});
    await row.hover();
    const kebab = row.getByTestId(/^row-actions-/);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: 5_000});
    await action.click();
}

/** The Bulk is open; ends on it visible. */
async function bulkOpened(page: Page): Promise<Locator> {
    const bulk = page.getByTestId('tx-bulk-modal');
    await expect(bulk).toBeVisible({timeout: 8_000});
    return bulk;
}

/** One row cloned from the page opens its Form on top of the Bulk (`autoForm: 'create'`): assert it, close it. */
async function closeCloneForm(page: Page): Promise<Locator> {
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'a single row cloned opens its Form').toBeVisible({timeout: 8_000});
    await form.getByTestId('tx-form-cancel').click();
    await expect(form).toBeHidden({timeout: 8_000});
    return form;
}

// ---------------------------------------------------------------------------
// The Bulk
// ---------------------------------------------------------------------------

/** The Bulk row of saved transaction `id`, by the `#id` its ID cell shows. */
function savedBulkRow(bulk: Locator, id: number): Locator {
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: bulk.page().locator('td[data-column-id="id"]', {hasText: new RegExp(`#${id}\\b`)})});
}

/** The new rows of the Bulk carrying this description: the copies of the row that has it. */
function copyRows(bulk: Locator, description: string): Locator {
    const page = bulk.page();
    return bulk
        .getByTestId('tx-bulk-body')
        .locator('tr[data-row-id]')
        .filter({has: page.locator('td[data-column-id="description"]', {hasText: description})})
        .filter({has: page.locator('[data-testid="tx-bulk-row-status"][data-status="new"]')});
}

async function rowIdOf(row: Locator): Promise<string> {
    await expect(row).toHaveCount(1, {timeout: 10_000});
    const id = await row.getAttribute('data-row-id');
    if (!id) throw new Error('the Bulk row publishes no data-row-id');
    return id;
}

/** `row` sits under the parent row `parentRow`: its label names it (`data-charge-of`), and it has no checkbox. */
async function expectUnder(row: Locator, parentRow: Locator, what: string): Promise<void> {
    const parentId = await rowIdOf(parentRow);
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is not under its parent`).toHaveAttribute('data-charge-of', parentId, {timeout: 10_000});
    await expect(row.locator('[data-testid^="dt-row-checkbox-"]')).toHaveCount(0);
}

/** `row` is a top-level row: its label names no parent, and it can be selected. */
async function expectTopLevel(row: Locator, what: string): Promise<void> {
    await expect(row, `${what} is not a row of the Bulk`).toBeVisible({timeout: 10_000});
    await expect(row.getByTestId('tx-bulk-row-label'), `${what} is under a parent`).not.toHaveAttribute('data-charge-of');
    await expect(row.locator('[data-testid^="dt-row-checkbox-"]'), `${what} has no checkbox`).toHaveCount(1);
}

/** The chip of the parent row. */
async function chipOf(bulk: Locator, parentRow: Locator): Promise<Locator> {
    return bulk.getByTestId(`tx-bulk-charges-toggle-${await rowIdOf(parentRow)}`);
}

/** ⋮ on a Bulk row → the action `actionId`. */
async function bulkRowAction(bulk: Locator, row: Locator, actionId: string): Promise<void> {
    const rowId = await rowIdOf(row);
    await bulk.getByTestId(`row-actions-${rowId}`).click();
    const action = bulk.page().getByTestId(`context-menu-action-${actionId}`);
    await expect(action, `the row menu offers no «${actionId}»`).toBeVisible({timeout: 5_000});
    await action.click();
}

/** BUY and all its charges ticked in the table (its fold open) and opened in the Bulk with «Edit»: the group is open. */
async function openAllInBulk(page: Page, s: Seeded): Promise<Locator> {
    await openTable(page);
    await openTableFold(page, s);
    const ids = [s.buyId, ...Object.values(s.charges).map((c) => c.id)];
    for (const id of ids) await ensureChecked(page, id);
    await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', String(ids.length), {timeout: 5_000});
    const edit = page.getByTestId('toolbar-action-edit');
    await expect(edit).toBeEnabled({timeout: 5_000});
    await edit.click();
    const bulk = await bulkOpened(page);
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const chip = await chipOf(bulk, savedBulkRow(bulk, s.buyId));
    await expect(chip, 'premise: the charges brought with their parent open its group').toHaveAttribute('aria-expanded', 'true', {timeout: 10_000});
    return bulk;
}

/** «Save all»; the commit must succeed and the Bulk close. */
async function saveAll(page: Page, bulk: Locator): Promise<unknown> {
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const payload = (await requestPromise).postDataJSON() as unknown;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(payload)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return payload;
}

/** The single row of `rows` with this type and description. */
function only(rows: ChargeTx[], type: string, description: string, dump: string): ChargeTx {
    const found = rows.filter((tx) => tx.type === type && tx.description === description);
    expect(found, `exactly one new ${type} «${description}»: ${dump}`).toHaveLength(1);
    return found[0];
}

/** The originals are as seeded: each charge still on the BUY, on its own date; the BUY counts them. */
async function expectOriginalsUnchanged(page: Page, s: Seeded, extraCharges = 0): Promise<void> {
    const back = await readByIds(page, s.ids);
    for (const c of Object.values(s.charges)) {
        expect(back.get(c.id)?.parent_transaction_id, `the original ${c.label} still points at the original BUY`).toBe(s.buyId);
        expect(back.get(c.id)?.date).toBe(c.date);
    }
    expect(back.get(s.buyId)?.charges_count, 'the original BUY’s charges').toBe(Object.keys(s.charges).length + extraCharges);
}

// ---------------------------------------------------------------------------
// (9)/(10): a copy given another asset, and a save the server refuses
// ---------------------------------------------------------------------------

/** The seeded asset the copies are moved to: same currency as the BUY's Ethereum, so only the asset differs. */
const OTHER_ASSET = {ticker: 'BTC-USD', search: 'Bitcoin'};

/** The Form's asset select, narrowed by name and picked by id; ends on the list closed. */
async function pickAsset(page: Page, form: Locator, assetId: number): Promise<void> {
    const trigger = form.getByTestId('tx-form-asset-trigger');
    await expect(trigger).toHaveAttribute('data-disabled', 'false', {timeout: 8_000});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
    const search = form.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: 5_000});
    await search.fill(OTHER_ASSET.search);
    const option = form.getByTestId('tx-form-asset').getByTestId(`search-select-option-${assetId}`);
    await expect(option).toBeVisible({timeout: 8_000});
    await option.click();
    await optionsClosed(page);
}

/** «Apply» in a Form open on top of the Bulk; ends on the Form closed. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
}

/** `banner` (the pre-save warning `tx-bulk-issues-header` or the refusal `tx-bulk-error`) lists `n` issues, every one
 *  `chargeAssetMismatch`: the Bulk holds only this test's rows, so the count is the test's. */
async function expectIssues(banner: Locator, n: number, what: string): Promise<void> {
    await expect(banner, `${what} is shown`).toBeVisible({timeout: 20_000});
    await expect(banner.locator('[data-testid="tx-bulk-issue"][data-code="chargeAssetMismatch"]'), `${what}: the asset rule`).toHaveCount(n, {timeout: 20_000});
    await expect(banner.getByTestId('tx-bulk-issue'), `${what}: nothing else`).toHaveCount(n);
}

type SentCreate = {type?: string; description?: string; asset_id?: number | null; parent_transaction_id?: number; parent_ref?: string; ref?: string};
type RefusedIssue = {operation?: string; index?: number; code?: string; params?: {assetId?: number; parentAssetId?: number}};

/** «Save all» that the server refuses: the batch goes out, comes back `committed: false`, and the Bulk stays open. */
async function saveRefused(page: Page, bulk: Locator): Promise<{payload: {creates?: SentCreate[]}; body: {committed?: boolean; issues?: RefusedIssue[]}}> {
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commit = bulk.getByTestId('tx-bulk-commit');
    await expect(commit, 'the issues do not lock «Save all»').toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commit.click();
    const payload = (await requestPromise).postDataJSON() as {creates?: SentCreate[]};
    const body = (await (await responsePromise).json()) as {committed?: boolean; issues?: RefusedIssue[]};
    expect(body.committed, `the batch was saved: ${JSON.stringify(body)} — payload ${JSON.stringify(payload)}`).toBe(false);
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    await expect(bulk, 'a refused save keeps the Bulk open').toBeVisible();
    return {payload, body};
}

// ---------------------------------------------------------------------------
// The tests
// ---------------------------------------------------------------------------

test.describe('«Clona» carries the linked charges (TL-3)', () => {
    let owned = emptyOwnedAccount();
    let seeded: Seeded | null = null;

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        seeded = null;
    });

    // afterEach, not `finally`: it runs after a timeout too. Every row on the test's own broker is the test's (seeded or
    // saved by the Bulk): deleted together (a parent with its charges), then the account and its brokers.
    test.afterEach(async ({page, request}) => {
        try {
            if (owned.user && seeded) {
                const left = (await brokerRows(page, seeded)).map((tx) => tx.id);
                if (left.length > 0) await page.request.post(COMMIT_PATH, {data: {deletes: left}});
            }
        } finally {
            await cleanupOwnedAccount(page, request, owned);
        }
    });

    test('(1) page «Clona» on a BUY with two charges: three new rows, the copies under the BUY copy on their own dates; saved, the new BUY has two new charges', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c1', TWO_CHARGES));
        const {fee, tax} = s.charges;

        await openTable(page);
        await tableRowAction(page, s.buyId, 'clone');
        const bulk = await bulkOpened(page);
        await closeCloneForm(page);

        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
        await expect(buyCopy.getByTestId('tx-bulk-date')).toHaveAttribute('data-date', s.buyDate);
        const chip = await chipOf(bulk, buyCopy);
        await expect(chip, 'the BUY copy carries its two charge copies').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
        await expect(chip, 'the copy’s group starts open').toHaveAttribute('aria-expanded', 'true');
        for (const c of [fee, tax]) {
            const copy = copyRows(bulk, c.description);
            await expect(copy, `one copy of ${c.label}`).toHaveCount(1, {timeout: 10_000});
            await expectUnder(copy, buyCopy, `the ${c.label} copy`);
            await expect(copy.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'linked');
            await expect(copy.getByTestId('tx-bulk-date'), `the ${c.label} copy keeps its original’s date`).toHaveAttribute('data-date', c.date);
        }
        // The Bulk holds this clone and nothing else: three rows, a count the test made.
        await expect(bulk.getByTestId('tx-bulk-body').locator('tr[data-row-id]')).toHaveCount(3);

        const payload = await saveAll(page, bulk);

        const fresh = await newRowsOnBroker(page, s);
        const dump = `new rows ${JSON.stringify(fresh)} — payload ${JSON.stringify(payload)}`;
        expect(fresh, dump).toHaveLength(3);
        const newBuy = only(fresh, 'BUY', s.buyDescription, dump);
        const newFee = only(fresh, 'FEE', fee.description, dump);
        const newTax = only(fresh, 'TAX', tax.description, dump);
        expect([newFee.parent_transaction_id, newTax.parent_transaction_id], `the new charges point at the new BUY: ${dump}`).toEqual([newBuy.id, newBuy.id]);
        expect(newBuy.charges_count, dump).toBe(2);
        expect([newBuy.date, newFee.date, newTax.date], 'every copy on its original’s date').toEqual([s.buyDate, fee.date, tax.date]);
        await expectOriginalsUnchanged(page, s);
    });

    test('(2) page «Clona» on a linked FEE alone: the copy is linked to the same BUY; saved, the BUY has one more charge', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c2', TWO_CHARGES));
        const {fee} = s.charges;

        await openTable(page);
        await openTableFold(page, s);
        await tableRowAction(page, fee.id, 'clone');
        const bulk = await bulkOpened(page);
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'a single row cloned opens its Form').toBeVisible({timeout: 8_000});
        await expect(form.getByTestId('tx-form-parent'), 'the copy’s Form names the BUY as its parent').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});
        await closeCloneForm(page);

        const copy = copyRows(bulk, fee.description);
        await expect(copy).toHaveCount(1, {timeout: 10_000});
        await expect(copy.getByTestId('tx-bulk-date')).toHaveAttribute('data-date', fee.date);

        const payload = await saveAll(page, bulk);

        const fresh = await newRowsOnBroker(page, s);
        const dump = `new rows ${JSON.stringify(fresh)} — payload ${JSON.stringify(payload)}`;
        expect(fresh, dump).toHaveLength(1);
        const newFee = only(fresh, 'FEE', fee.description, dump);
        expect(newFee.parent_transaction_id, `the copy is linked to the original BUY: ${dump}`).toBe(s.buyId);
        expect(newFee.date).toBe(fee.date);
        await expectOriginalsUnchanged(page, s, 1);
    });

    test('(3) page: the BUY and its FEE selected together → the FEE copied once, under the BUY copy; the TAX read and copied too', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c3', TWO_CHARGES));
        const {fee, tax} = s.charges;

        await openTable(page);
        await openTableFold(page, s);
        await ensureChecked(page, s.buyId);
        await ensureChecked(page, fee.id);
        await expect(page.getByTestId('selection-toolbar')).toHaveAttribute('data-selected-count', '2', {timeout: 5_000});
        await page.getByTestId('toolbar-action-clone').click();
        const bulk = await bulkOpened(page);

        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
        await expect(await chipOf(bulk, buyCopy), 'the BUY copy carries the FEE copy and the TAX copy').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});
        const feeCopy = copyRows(bulk, fee.description);
        await expect(feeCopy, 'the FEE is copied once, as part of the structure').toHaveCount(1);
        await expectUnder(feeCopy, buyCopy, 'the FEE copy');
        await expectUnder(copyRows(bulk, tax.description), buyCopy, 'the TAX copy');
        await expect(bulk.getByTestId('tx-bulk-body').locator('tr[data-row-id]')).toHaveCount(3);

        const payload = await saveAll(page, bulk);

        const fresh = await newRowsOnBroker(page, s);
        const dump = `new rows ${JSON.stringify(fresh)} — payload ${JSON.stringify(payload)}`;
        expect(fresh, dump).toHaveLength(3);
        const newBuy = only(fresh, 'BUY', s.buyDescription, dump);
        expect(only(fresh, 'FEE', fee.description, dump).parent_transaction_id, dump).toBe(newBuy.id);
        expect(only(fresh, 'TAX', tax.description, dump).parent_transaction_id, dump).toBe(newBuy.id);
        await expectOriginalsUnchanged(page, s);
    });

    test('(4) page: the read of the BUY’s charges fails → the BUY copy alone, the event and a warning toast', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c4', TWO_CHARGES));

        await openTable(page);
        // Installed once the table is settled: only the read of the parent's charges fails, nothing the table needed.
        let hits = 0;
        const isChargesRead = (url: URL): boolean => url.pathname === '/api/v1/transactions' && url.searchParams.has('parent_ids');
        await page.route(isChargesRead, async (route) => {
            if (route.request().method() !== 'GET') return route.continue();
            hits += 1;
            await route.fulfill({status: 500, contentType: 'application/json', body: JSON.stringify({detail: 'injected by tx-clone-charges (4)'})});
        });

        const since = await eventSeq(page);
        await tableRowAction(page, s.buyId, 'clone');
        const event = await waitForEvent(page, 'tx.bulk.clone.charges-read-failed', {since, timeout: 15_000});
        expect(event.name).toBe('tx.bulk.clone.charges-read-failed');
        await expect.poll(() => hits, {message: 'the read of the parent’s charges was attempted'}).toBeGreaterThan(0);
        await expect(page.getByTestId('toast-warning'), 'the user is told the charges were not copied').toBeVisible({timeout: 5_000});

        const bulk = await bulkOpened(page);
        await closeCloneForm(page);
        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy, 'the BUY is copied alone').toHaveCount(1, {timeout: 10_000});
        for (const c of Object.values(s.charges)) await expect(copyRows(bulk, c.description), `no copy of ${c.label}`).toHaveCount(0);
        await expect(bulk.getByTestId('tx-bulk-body').locator('tr[data-row-id]')).toHaveCount(1);
        await page.unroute(isChargesRead);
    });

    test('(5) Bulk «Clona riga» on a charge under its parent: the copy appears under the same parent', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c5', TWO_CHARGES));
        const {fee} = s.charges;
        const bulk = await openAllInBulk(page, s);
        const buyRow = savedBulkRow(bulk, s.buyId);
        await expectUnder(savedBulkRow(bulk, fee.id), buyRow, 'premise: the FEE');

        await bulkRowAction(bulk, savedBulkRow(bulk, fee.id), 'clone');

        const copy = copyRows(bulk, fee.description);
        await expect(copy).toHaveCount(1, {timeout: 10_000});
        await expectUnder(copy, buyRow, 'the FEE copy');
        await expect(copy.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'linked');
        await expect(copy.getByTestId('tx-bulk-date')).toHaveAttribute('data-date', fee.date);
        await expect(await chipOf(bulk, buyRow)).toHaveAttribute('data-charges-count', '3');

        const payload = await saveAll(page, bulk);

        const fresh = await newRowsOnBroker(page, s);
        const dump = `new rows ${JSON.stringify(fresh)} — payload ${JSON.stringify(payload)}`;
        expect(only(fresh, 'FEE', fee.description, dump).parent_transaction_id, dump).toBe(s.buyId);
        await expectOriginalsUnchanged(page, s, 1);
    });

    test('(6) Bulk: a charge under a parent «del» → «Clona riga» → the copy is free, with the event (reason deleted) and a warning toast', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c6', TWO_CHARGES));
        const {fee} = s.charges;
        const bulk = await openAllInBulk(page, s);
        const buyRow = savedBulkRow(bulk, s.buyId);
        const feeRow = savedBulkRow(bulk, fee.id);

        // The BUY «del» with «Delete all»: its charges go «del» with it and stay under it. («Keep» would leave them
        // «scollega», whose copy is free without a toast: another case.)
        await bulkRowAction(bulk, buyRow, 'mark-delete');
        const panel = page.getByTestId('tx-charges-modal-content');
        await expect(panel).toHaveAttribute('data-mode', 'deleteParent', {timeout: 8_000});
        await panel.getByTestId('tx-charges-modal-all').click();
        await expect(panel).toBeHidden({timeout: 5_000});
        await expect(buyRow.getByTestId('tx-bulk-row-status')).toHaveAttribute('data-status', 'delete');
        await expectUnder(feeRow, buyRow, 'premise: the FEE');
        await expect(feeRow.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'del');

        const since = await eventSeq(page);
        await bulkRowAction(bulk, feeRow, 'clone');

        const event = await waitForEvent(page, 'tx.bulk.clone.charge-free', {since, timeout: 10_000});
        expect(event.detail?.reason, 'the copy is free because its parent is «del»').toBe('deleted');
        await expect(page.getByTestId('toast-warning')).toBeVisible({timeout: 5_000});
        const copy = copyRows(bulk, fee.description);
        await expect(copy).toHaveCount(1, {timeout: 10_000});
        await expectTopLevel(copy, 'the FEE copy');
    });

    test('(7) Bulk «Clona riga» on a parent with one charge «del», one «scollega», one linked: only the linked one is copied', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c7', THREE_CHARGES));
        const {fee, tax, feeB} = s.charges;
        const bulk = await openAllInBulk(page, s);
        const buyRow = savedBulkRow(bulk, s.buyId);

        // Fee A «del» on its own row.
        await bulkRowAction(bulk, savedBulkRow(bulk, fee.id), 'mark-delete');
        await expect(savedBulkRow(bulk, fee.id).getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'del', {timeout: 5_000});
        // The TAX «scollega» in the BUY's Form.
        await bulkRowAction(bulk, buyRow, 'edit-single');
        const form = page.getByTestId('tx-form-modal');
        await expect(form).toBeVisible({timeout: 8_000});
        const section = form.getByTestId('tx-form-charges');
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        const taxChip = section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${tax.id}"]`);
        await taxChip.locator('[data-testid^="tx-form-charge-unlink-"]').click();
        await expect(taxChip).toHaveCount(0);
        await expect(form.getByTestId('tx-form-save')).toBeEnabled({timeout: 8_000});
        await form.getByTestId('tx-form-save').click();
        await expect(form).toBeHidden({timeout: 8_000});
        await expect(savedBulkRow(bulk, tax.id).getByTestId('tx-bulk-charge-state'), 'premise: the TAX «scollega»').toHaveAttribute('data-state', 'unlink', {timeout: 8_000});
        await expect(savedBulkRow(bulk, feeB.id).getByTestId('tx-bulk-charge-state'), 'premise: Fee B linked').toHaveAttribute('data-state', 'linked');

        await bulkRowAction(bulk, buyRow, 'clone');

        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
        const feeBCopy = copyRows(bulk, feeB.description);
        await expect(feeBCopy, 'the linked charge is copied').toHaveCount(1, {timeout: 10_000});
        await expectUnder(feeBCopy, buyCopy, 'the Fee B copy');
        await expect(await chipOf(bulk, buyCopy), 'one charge copy under the BUY copy').toHaveAttribute('data-charges-count', '1');
        await expect(copyRows(bulk, fee.description), 'a charge «del» is not copied').toHaveCount(0);
        await expect(copyRows(bulk, tax.description), 'a charge «scollega» is not copied').toHaveCount(0);
    });

    // 📌 consultant, to confirm visually: trash on the parent copy takes the charge copies «Clona» brought while they
    // are untouched; a copy changed first stays, a free row.
    test('(8) Bulk: trash on the BUY copy → the untouched charge copy leaves with it; the copy whose amount changed stays, free', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c8', TWO_CHARGES));
        const {fee, tax} = s.charges;
        const bulk = await openAllInBulk(page, s);

        await bulkRowAction(bulk, savedBulkRow(bulk, s.buyId), 'clone');
        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
        const feeCopy = copyRows(bulk, fee.description);
        const taxCopy = copyRows(bulk, tax.description);
        await expectUnder(feeCopy, buyCopy, 'the FEE copy');
        await expectUnder(taxCopy, buyCopy, 'the TAX copy');
        const buyCopyId = await rowIdOf(buyCopy);
        const taxCopyId = await rowIdOf(taxCopy);

        // The FEE copy's amount changed in its own Form.
        await bulkRowAction(bulk, feeCopy, 'edit-single');
        const form = page.getByTestId('tx-form-modal');
        await expect(form).toBeVisible({timeout: 8_000});
        const cash = form.getByTestId('tx-form-cash-wrap').locator('input[data-testid$="-amount"]');
        await expect(cash).toBeVisible({timeout: 5_000});
        await cash.fill('7');
        await cash.blur();
        await expect(cash).not.toHaveValue('');
        await expect(form.getByTestId('tx-form-save')).toBeEnabled({timeout: 8_000});
        await form.getByTestId('tx-form-save').click();
        await expect(form).toBeHidden({timeout: 8_000});

        await bulkRowAction(bulk, buyCopy, 'mark-delete');

        // Presence first: the changed FEE copy, now a row of its own — the barrier for the absences below.
        await expectTopLevel(copyRows(bulk, fee.description), 'the changed FEE copy');
        const body = bulk.getByTestId('tx-bulk-body');
        await expect(body.locator(`tr[data-row-id="${buyCopyId}"]`), 'the BUY copy left').toHaveCount(0);
        await expect(body.locator(`tr[data-row-id="${taxCopyId}"]`), 'the untouched TAX copy left with it').toHaveCount(0);
    });
    // Row 5 of the lot's table: a cloned charge whose copy gets another asset. Rule 3 (a charge has its parent's asset) is
    // the backend's: the Form keeps the link, the Bulk's validation names the row, and «Save all» is refused whole.
    test('(9) page «Clona» on a linked FEE, the copy’s asset changed in its Form: the link stays; flagged chargeAssetMismatch, «Save all» refused, nothing saved', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c9', TWO_CHARGES));
        const {fee} = s.charges;
        const otherAssetId = await seededAssetId(page, OTHER_ASSET.ticker);
        expect(otherAssetId, 'premise: the other asset is not the BUY’s').not.toBe(s.assetId);

        await openTable(page);
        await openTableFold(page, s);
        await tableRowAction(page, fee.id, 'clone');
        const bulk = await bulkOpened(page);
        const form = page.getByTestId('tx-form-modal');
        await expect(form, 'a single row cloned opens its Form').toBeVisible({timeout: 8_000});
        const parent = form.getByTestId('tx-form-parent');
        await expect(parent, 'premise: the copy is linked to the BUY').toHaveAttribute('data-parent-id', String(s.buyId), {timeout: 8_000});

        await pickAsset(page, form, otherAssetId);
        // The Form neither drops nor blocks the link: still «Linked to» the BUY, and «Apply» stays on.
        await expect(parent, 'the Form keeps the link after the asset changes').toHaveAttribute('data-parent-id', String(s.buyId));
        await expect(parent).toHaveAttribute('data-state', 'ready');
        await applyForm(form);

        const copy = copyRows(bulk, fee.description);
        await expect(copy).toHaveCount(1, {timeout: 10_000});
        // The Bulk's own validation (run on the change, no click) flags the copy: one issue, the asset rule.
        await expectIssues(bulk.getByTestId('tx-bulk-issues-header'), 1, 'the pre-save warning');

        const {payload, body} = await saveRefused(page, bulk);
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(body)}`;
        expect(payload.creates, dump).toHaveLength(1);
        const sent = payload.creates?.[0];
        expect([sent?.type, sent?.asset_id, sent?.parent_transaction_id], `the copy is sent linked to the BUY, with the other asset: ${dump}`).toEqual(['FEE', otherAssetId, s.buyId]);
        expect(
            (body.issues ?? []).map((issue) => [issue.operation, issue.index, issue.code, issue.params?.assetId, issue.params?.parentAssetId]),
            `the server names the copy and the asset rule: ${dump}`,
        ).toEqual([['create', 0, 'chargeAssetMismatch', otherAssetId, s.assetId]]);

        // The refusal is shown, with the issue, and the Bulk keeps the copy for the user to fix.
        await expectIssues(bulk.getByTestId('tx-bulk-error'), 1, 'the refusal');
        await expect(copy).toHaveCount(1);
        // Nothing saved: no new row on the broker, the originals as seeded.
        expect(await newRowsOnBroker(page, s), dump).toEqual([]);
        await expectOriginalsUnchanged(page, s);
    });

    // The parent's copy with another asset: «no magic» (rule 5) — the charge copies keep their own asset, so both break
    // rule 3 and the batch is refused whole, the BUY copy with them.
    test('(10) page «Clona» on a BUY with two charges, the BUY copy’s asset changed in its Form: the copies stay under it; both flagged chargeAssetMismatch, «Save all» refused, nothing saved', async ({page, request}) => {
        const s = (seeded = await seedBuyWithCharges(page, request, owned, 'tl3c10', TWO_CHARGES));
        const {fee, tax} = s.charges;
        const otherAssetId = await seededAssetId(page, OTHER_ASSET.ticker);
        expect(otherAssetId, 'premise: the other asset is not the BUY’s').not.toBe(s.assetId);

        await openTable(page);
        await tableRowAction(page, s.buyId, 'clone');
        const bulk = await bulkOpened(page);
        await closeCloneForm(page);
        const buyCopy = copyRows(bulk, s.buyDescription);
        await expect(buyCopy).toHaveCount(1, {timeout: 10_000});
        const chip = await chipOf(bulk, buyCopy);
        await expect(chip, 'premise: the BUY copy carries its two charge copies').toHaveAttribute('data-charges-count', '2', {timeout: 10_000});

        // The BUY copy's own Form: its two charges listed, its asset changed, applied.
        await bulkRowAction(bulk, buyCopy, 'edit-single');
        const form = page.getByTestId('tx-form-modal');
        await expect(form).toBeVisible({timeout: 8_000});
        const section = form.getByTestId('tx-form-charges');
        await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
        await expect(section.getByTestId('tx-form-charge-row'), 'premise: the Form lists the two charge copies').toHaveCount(2);
        await pickAsset(page, form, otherAssetId);
        await expect(section.getByTestId('tx-form-charge-row'), 'the asset change keeps the charges in the Form').toHaveCount(2);
        await applyForm(form);

        // The grid: both copies still under the BUY copy, linked.
        await expect(chip, 'the BUY copy still carries both copies').toHaveAttribute('data-charges-count', '2');
        for (const c of [fee, tax]) {
            const copy = copyRows(bulk, c.description);
            await expectUnder(copy, buyCopy, `the ${c.label} copy`);
            await expect(copy.getByTestId('tx-bulk-charge-state')).toHaveAttribute('data-state', 'linked');
        }
        // The Bulk's own validation (run on the change, no click): one issue per charge copy, the asset rule.
        await expectIssues(bulk.getByTestId('tx-bulk-issues-header'), 2, 'the pre-save warning');

        const {payload, body} = await saveRefused(page, bulk);
        const dump = `payload ${JSON.stringify(payload)} — answer ${JSON.stringify(body)}`;
        const creates = payload.creates ?? [];
        expect(creates, dump).toHaveLength(3);
        const indexOf = (type: string, description: string): number => {
            const at = creates.findIndex((item) => item.type === type && item.description === description);
            expect(at, `the payload holds the ${type} «${description}»: ${dump}`).toBeGreaterThanOrEqual(0);
            return at;
        };
        const [buyAt, feeAt, taxAt] = [indexOf('BUY', s.buyDescription), indexOf('FEE', fee.description), indexOf('TAX', tax.description)];
        const ref = creates[buyAt].ref;
        expect(ref, `the BUY copy carries a ref: ${dump}`).toBeTruthy();
        expect(creates[buyAt].asset_id, 'the BUY copy is sent with the other asset').toBe(otherAssetId);
        for (const at of [feeAt, taxAt]) {
            expect([creates[at].parent_ref, creates[at].asset_id], `a charge copy is sent under the BUY copy, with its original asset: ${dump}`).toEqual([ref, s.assetId]);
        }
        const issues = (body.issues ?? []).map((issue) => [issue.operation, issue.index, issue.code, issue.params?.assetId, issue.params?.parentAssetId]);
        expect(
            [...issues].sort((a, b) => Number(a[1]) - Number(b[1])),
            `the server names the two charge copies, not the BUY copy: ${dump}`,
        ).toEqual([feeAt, taxAt].sort((a, b) => a - b).map((at) => ['create', at, 'chargeAssetMismatch', s.assetId, otherAssetId]));

        // The refusal is shown with both issues; the Bulk keeps the three copies, the structure intact.
        await expectIssues(bulk.getByTestId('tx-bulk-error'), 2, 'the refusal');
        await expect(chip).toHaveAttribute('data-charges-count', '2');
        // Nothing saved half-way: no new row on the broker, the originals as seeded.
        expect(await newRowsOnBroker(page, s), dump).toEqual([]);
        await expectOriginalsUnchanged(page, s);
    });
});
