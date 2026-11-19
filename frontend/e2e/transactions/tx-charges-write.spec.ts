/**
 * Write the linked charges of a parent from the transaction form the Bulk hosts (lane 66, lot F7-b).
 * Contract: `66-F7-contract.md` §10–§11.
 *
 * The form of a BUY has a «Linked charges» section (`tx-form-charges`). Opened from the Bulk it is editable
 * (`allowChargeEdits`), and the Bulk saves what it hands back (`_charges`): new charges become creates linked to the
 * parent, a changed note an update, «unlink» an update to `parent_transaction_id: 0`, the trash a delete.
 *
 *   1. Create: «+ New» → a BUY, plus a FEE and a TAX added in its section → «Apply» → «Save all»: the three rows exist,
 *      the two charges point at the BUY and take its broker, asset and date.
 *   2. Reopen: a saved BUY+FEE+TAX, the BUY edited from the table; the FEE's note changed in the section → saved: the
 *      FEE has the new note and is still linked, the BUY is unchanged.
 *   3. Unlink: same seed; the TAX unlinked in the section → saved: the TAX exists with no parent, the FEE still linked.
 *   4. Delete: same seed; the FEE trashed in the section → saved: the FEE is gone, the TAX still linked.
 *   («Open» parent → charge → parent inside the Bulk is F7-d, not here.)
 *
 * testids relied on: tx-add-button · tx-form-modal · tx-form-type · tx-form-broker-wrap · tx-form-asset-trigger ·
 * tx-form-asset-search · search-select-option-<value> · tx-form-quantity · tx-form-cash-wrap · tx-form-save ·
 * tx-form-charges[data-state] · tx-form-charges-add-FEE|TAX · tx-form-charge-row[data-charge-id][data-charge-type] ·
 * tx-form-charge-cash-<key>-amount · tx-form-charge-note-<key> · tx-form-charge-unlink-<key> ·
 * tx-form-charge-remove-<key> · dt-row-checkbox-tx-<id> · toolbar-action-edit · tx-charges-badge-<id> ·
 * tx-bulk-modal · tx-bulk-modal-root · tx-bulk-commit.
 * A charge row is found by its id (saved) or by its type with an empty id (new), never by its key: the key's format
 * is the form's business (`saved-<id>`, `new-<n>`, and the Bulk's own keys from F7-b). Inside a row the controls are
 * matched by testid prefix.
 *
 * Every test works on an account of its own (a disposable user, a broker it owns, funded by its own DEPOSIT), so no
 * other spec sees its rows. The verdict is the server, read back by id (`GET /transactions?ids=…`); the Bulk's grid
 * is not counted (which rows it shows for the charges moves between lots, §11.1). The afterEach deletes whatever of
 * the test's rows is still there, then the account.
 */
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {daysAgoIso} from '../fixtures/dates';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {createOwnedBroker, type OwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, jsonFrom, openOwnedAccount, seededAssetId, type OwnedAccount} from '../fixtures/owned-pair';

test.setTimeout(90_000);

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;

/** A transaction read back by id, reduced to what this spec checks. */
type Tx = {
    id: number;
    type: string;
    broker_id: number;
    asset_id?: number | null;
    date: string;
    quantity: string;
    cash?: {code: string; amount: string} | null;
    description?: string | null;
    parent_transaction_id?: number | null;
    charges_count?: number;
};
type CommitResult = {operation: string; index: number; ids?: number[]; status?: string};
type CommitBody = {committed?: boolean; issues?: unknown[]; results?: CommitResult[]};

/** A funded broker with a BUY and its FEE and TAX, linked, on one asset and date. */
type Seeded = {broker: OwnedBroker; assetId: number; marker: string; buyId: number; feeId: number; taxId: number};

/** These transactions as the server has them now; an id that no longer exists is simply absent. */
async function readByIds(page: Page, ids: number[]): Promise<Map<number, Tx>> {
    if (ids.length === 0) return new Map();
    const query = ids.map((id) => `ids=${id}`).join('&');
    const rows = await jsonFrom<Tx[]>(await page.request.get(`${API}/transactions?${query}`), `read transactions ${ids.join(',')}`);
    return new Map(rows.map((tx) => [tx.id, tx] as const));
}

/** Open a disposable account with one broker it owns, funded by its own DEPOSIT. */
async function openFundedAccount(page: Page, request: Parameters<typeof openOwnedAccount>[1], owned: OwnedAccount, committed: number[], tag: string): Promise<{broker: OwnedBroker; assetId: number; marker: string}> {
    const marker = `ChgW ${uniqueSuffix()}`;
    await openOwnedAccount(page, request, owned, tag);
    const broker = await createOwnedBroker(page, tag, owned.brokerIds);
    const assetId = await seededAssetId(page, 'ETH-USD');
    // Fund the broker first: a BUY and its charges take cash out of it.
    const [depositId] = await commitCreates(page, [{broker_id: broker.id, type: 'DEPOSIT', date: daysAgoIso(10), cash: {code: 'USD', amount: '1000'}, description: `Deposit ${marker}`}], 'fund the broker');
    committed.push(depositId);
    return {broker, assetId, marker};
}

/** A funded account with a BUY and a FEE and a TAX committed linked to it (`ref` / `parent_ref`), the link read back. */
async function seedLinkedBuy(page: Page, request: Parameters<typeof openOwnedAccount>[1], owned: OwnedAccount, committed: number[], tag: string): Promise<Seeded> {
    const {broker, assetId, marker} = await openFundedAccount(page, request, owned, committed, tag);
    const date = daysAgoIso(5);
    const charge = {broker_id: broker.id, asset_id: assetId, date, quantity: '0', parent_ref: 'p'};
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {
                creates: [
                    {ref: 'p', broker_id: broker.id, asset_id: assetId, type: 'BUY', date, quantity: '10', cash: {code: 'USD', amount: '-100'}, description: `Buy ${marker}`},
                    {...charge, type: 'FEE', cash: {code: 'USD', amount: '-5'}, description: `Fee ${marker}`},
                    {...charge, type: 'TAX', cash: {code: 'USD', amount: '-2'}, description: `Tax ${marker}`},
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
    const [buyId, feeId, taxId] = [idAt(0), idAt(1), idAt(2)];
    committed.push(buyId, feeId, taxId);

    // The premise, read back rather than inferred: both charges point at the BUY, which counts two.
    const back = await readByIds(page, [buyId, feeId, taxId]);
    expect([back.get(feeId)?.parent_transaction_id ?? null, back.get(taxId)?.parent_transaction_id ?? null], 'premise: the FEE and the TAX are linked to the BUY').toEqual([buyId, buyId]);
    expect(back.get(buyId)?.charges_count, 'premise: the BUY counts two charges').toBe(2);
    return {broker, assetId, marker, buyId, feeId, taxId};
}

/** Pick the option `value` in the select opened by `trigger`, and prove the list is gone (option testids are shared). */
async function pickOption(page: Page, trigger: Locator, value: string | number): Promise<void> {
    await expect(trigger).toBeVisible({timeout: 5_000});
    await trigger.click();
    const option = page.getByTestId(`search-select-option-${value}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionsClosed(page);
}

/** Open the table narrowed to the BUY, check the BUY row carries its charges' badge, select it alone and edit it:
 *  one selected row opens the Bulk with its form on top. */
async function editFromTable(page: Page, s: Seeded): Promise<Locator> {
    await navigateTo(page, `/transactions?id_min=${s.buyId}&id_max=${s.buyId}`);
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    const row = page.getByTestId('tx-table').locator(`tbody tr[data-row-id="tx-${s.buyId}"]`);
    await expect(row).toBeVisible({timeout: 8_000});
    // Setup barrier: the page sees the BUY as a parent with charges.
    await expect(row.getByTestId(`tx-charges-badge-${s.buyId}`)).toBeVisible({timeout: 8_000});

    const checkbox = page.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${s.buyId}`);
    await expect(checkbox).toBeVisible({timeout: 5_000});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const editBtn = page.getByTestId('toolbar-action-edit');
    await expect(editBtn).toBeEnabled({timeout: 5_000});
    await editBtn.click();

    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'one selected row auto-opens its Form').toBeVisible({timeout: 8_000});
    return form;
}

/** The charges section of `form`, loaded, listing the saved FEE and TAX of the seed. */
async function loadedCharges(form: Locator, s: Seeded): Promise<Locator> {
    const section = form.getByTestId('tx-form-charges');
    await expect(section, 'the BUY form shows no linked-charges section').toBeVisible({timeout: 8_000});
    await expect(section).toHaveAttribute('data-state', 'ready', {timeout: 8_000});
    await expect(savedCharge(section, s.feeId)).toHaveAttribute('data-charge-type', 'FEE', {timeout: 8_000});
    await expect(savedCharge(section, s.taxId)).toHaveAttribute('data-charge-type', 'TAX');
    return section;
}

/** What «the BUY is unchanged» means: its own fields and its charge count, not timestamps or derived values. */
function unchangedFields(tx: Tx | undefined): Partial<Tx> {
    if (!tx) throw new Error('the BUY is missing on the server');
    const {type, broker_id, asset_id, date, quantity, cash, description, parent_transaction_id, charges_count} = tx;
    return {type, broker_id, asset_id, date, quantity, cash, description, parent_transaction_id, charges_count};
}

/** The row of the saved charge `id` in the section. */
function savedCharge(section: Locator, id: number): Locator {
    return section.locator(`[data-testid="tx-form-charge-row"][data-charge-id="${id}"]`);
}

/** The row of the one new charge of `type` in the section (a new row has no id yet). */
function newCharge(section: Locator, type: 'FEE' | 'TAX'): Locator {
    return section.locator(`[data-testid="tx-form-charge-row"][data-charge-id=""][data-charge-type="${type}"]`);
}

/** The editable note of a charge row: an `<input>`. Read-only, the same testid is a `<p>`. */
function noteInput(row: Locator): Locator {
    return row.locator('input[data-testid^="tx-form-charge-note-"]');
}

/** «Apply» in the form: it hands the draft back to the Bulk and closes. */
async function applyForm(page: Page, form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: 8_000});
    await apply.click();
    await expect(form).toBeHidden({timeout: 8_000});
}

/** «Save all» in the Bulk; the commit must succeed. Returns the ids each create produced, by index. */
async function saveAll(page: Page): Promise<{body: CommitBody; payload: unknown}> {
    const bulk = page.getByTestId('tx-bulk-modal');
    await waitForSettled(bulk.getByTestId('tx-bulk-modal-root'), 20_000);
    const commitBtn = bulk.getByTestId('tx-bulk-commit');
    await expect(commitBtn, '«Save all» stays off: the Bulk holds nothing to save').toBeEnabled({timeout: 10_000});
    const requestPromise = page.waitForRequest((req) => req.url().includes('/transactions/commit') && req.method() === 'POST', {timeout: 15_000});
    const responsePromise = page.waitForResponse((resp) => resp.url().includes('/transactions/commit') && resp.request().method() === 'POST', {timeout: 15_000});
    await commitBtn.click();
    const payload = (await requestPromise).postDataJSON() as unknown;
    const body = (await (await responsePromise).json()) as CommitBody;
    expect(body.committed, `the batch rolled back: ${JSON.stringify(body.issues ?? [])} — payload ${JSON.stringify(payload)}`).toBe(true);
    await expect(bulk).toBeHidden({timeout: 10_000});
    return {body, payload};
}

test.describe('Transaction form in the Bulk — write the linked charges', () => {
    let owned = emptyOwnedAccount();
    let committedIds: number[] = [];

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
        committedIds = [];
    });

    // afterEach, not `finally`: it runs after a timeout too. Only the rows still there are deleted, together
    // (a parent deleted without its charges is refused), then the account and its brokers.
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

    test('Create: a new BUY with a FEE and a TAX added in its form is saved as one parent with its two charges', async ({page, request}) => {
        const {broker, assetId, marker} = await openFundedAccount(page, request, owned, committedIds, 'chgw1');

        await navigateTo(page, '/transactions');
        await waitForSettled(page.getByTestId('transactions-page'), 20_000);
        await page.getByTestId('tx-add-button').click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: 8_000});
        const form = page.getByTestId('tx-form-modal');
        await expect(form, '«+ New» auto-opens the form').toBeVisible({timeout: 8_000});

        // The BUY: type, broker and asset picked by value (the broker's and the asset's id), quantity, cash.
        await pickOption(page, form.getByTestId('tx-form-type'), 'BUY');
        await pickOption(page, form.getByTestId('tx-form-broker-wrap').getByRole('combobox'), broker.id);
        await expect(form.getByTestId('tx-form-broker-wrap')).toContainText(broker.name);
        await expect(form.getByTestId('tx-form-asset-trigger')).toBeVisible({timeout: 5_000});
        await form.getByTestId('tx-form-asset-trigger').click();
        const assetSearch = page.getByTestId('tx-form-asset-search');
        await expect(assetSearch).toBeVisible({timeout: 5_000});
        await assetSearch.fill('Ethereum');
        const assetOption = page.getByTestId(`search-select-option-${assetId}`);
        await expect(assetOption).toBeVisible({timeout: 8_000});
        await assetOption.click();
        await optionsClosed(page);
        const quantity = form.getByTestId('tx-form-quantity');
        await quantity.fill('10');
        await quantity.blur();
        await expect(quantity).not.toHaveValue('');
        const cash = form.getByTestId('tx-form-cash-wrap').locator('input[data-testid$="-amount"]');
        await expect(cash).toBeVisible({timeout: 5_000});
        await cash.fill('100');
        await cash.blur();
        await expect(cash).not.toHaveValue('');
        // Setup barrier: the BUY alone is complete. What fails after this line is the charges section.
        await expect(form.getByTestId('tx-form-save'), 'the BUY form is not complete').toBeEnabled({timeout: 8_000});

        // Its charges: «+ Fee» and «+ Tax», each with an amount (a magnitude: the type gives the sign) and a note.
        const section = form.getByTestId('tx-form-charges');
        await expect(section.getByTestId('tx-form-charges-add-FEE'), 'the charges section is not editable in the form the Bulk hosts').toBeVisible({timeout: 8_000});
        await section.getByTestId('tx-form-charges-add-FEE').click();
        await expect(newCharge(section, 'FEE')).toHaveCount(1);
        await section.getByTestId('tx-form-charges-add-TAX').click();
        await expect(newCharge(section, 'TAX')).toHaveCount(1);
        for (const [type, amount] of [
            ['FEE', '5'],
            ['TAX', '2'],
        ] as const) {
            const row = newCharge(section, type);
            const amountInput = row.locator('input[data-testid^="tx-form-charge-cash-"][data-testid$="-amount"]');
            await amountInput.fill(amount);
            await amountInput.blur();
            // The blur may reformat the number for display; the server read-back below checks the value.
            await expect(amountInput).not.toHaveValue('');
            const note = noteInput(row);
            await note.fill(`${type} ${marker}`);
            await expect(note).toHaveValue(`${type} ${marker}`);
        }

        await applyForm(page, form);
        const {body, payload} = await saveAll(page);
        const createdIds = (body.results ?? []).filter((r) => r.operation === 'create').flatMap((r) => r.ids ?? []);
        committedIds.push(...createdIds);

        // On the server: among what this batch created, one BUY, one FEE and one TAX; the two charges point at the BUY.
        const created = [...(await readByIds(page, createdIds)).values()];
        const ofType = (type: string): Tx[] => created.filter((tx) => tx.type === type);
        const dump = `created ${JSON.stringify(created)} — payload ${JSON.stringify(payload)}`;
        expect(ofType('BUY'), `one BUY: ${dump}`).toHaveLength(1);
        expect(ofType('FEE'), `one FEE: ${dump}`).toHaveLength(1);
        expect(ofType('TAX'), `one TAX: ${dump}`).toHaveLength(1);
        const [buy, fee, tax] = [ofType('BUY')[0], ofType('FEE')[0], ofType('TAX')[0]];
        expect(buy.broker_id).toBe(broker.id);
        expect(buy.asset_id).toBe(assetId);
        for (const [charge, amount] of [
            [fee, -5],
            [tax, -2],
        ] as const) {
            expect(charge.parent_transaction_id, `${charge.type} linked to the BUY: ${dump}`).toBe(buy.id);
            expect({broker_id: charge.broker_id, asset_id: charge.asset_id, date: charge.date}, `${charge.type} takes the BUY's broker, asset and date`).toEqual({broker_id: buy.broker_id, asset_id: buy.asset_id, date: buy.date});
            expect(Number(charge.cash?.amount), `${charge.type} amount`).toBe(amount);
            expect(charge.cash?.code).toBe(buy.cash?.code);
            expect(charge.description).toBe(`${charge.type} ${marker}`);
        }
        const buyBack = (await readByIds(page, [buy.id])).get(buy.id);
        expect(buyBack?.charges_count).toBe(2);
    });

    test('Reopen: the FEE note changed in the BUY form is saved, the FEE stays linked, the BUY is unchanged', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgw2');
        const before = unchangedFields((await readByIds(page, [s.buyId])).get(s.buyId));

        const form = await editFromTable(page, s);
        const section = await loadedCharges(form, s);
        const note = noteInput(savedCharge(section, s.feeId));
        await expect(note, 'the FEE note is read-only in the form the Bulk hosts').toBeVisible({timeout: 8_000});
        const newNote = `Fee edited ${s.marker}`;
        await note.fill(newNote);
        await expect(note).toHaveValue(newNote);

        await applyForm(page, form);
        const {payload} = await saveAll(page);

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.get(s.feeId)?.description, `FEE note: ${dump}`).toBe(newNote);
        expect(after.get(s.feeId)?.parent_transaction_id, `FEE still linked: ${dump}`).toBe(s.buyId);
        expect(after.get(s.taxId)?.parent_transaction_id, `TAX still linked: ${dump}`).toBe(s.buyId);
        expect(unchangedFields(after.get(s.buyId)), `the BUY is unchanged: ${dump}`).toEqual(before);
        expect(before.charges_count).toBe(2);
    });

    test('Unlink: the TAX unlinked in the BUY form survives with no parent, the FEE stays linked', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgw3');

        const form = await editFromTable(page, s);
        const section = await loadedCharges(form, s);
        const unlink = savedCharge(section, s.taxId).locator('[data-testid^="tx-form-charge-unlink-"]');
        await expect(unlink, 'no «unlink» on the TAX: the section is read-only in the form the Bulk hosts').toBeVisible({timeout: 8_000});
        await unlink.click();
        // Unlinked, the TAX leaves the section's list; the FEE stays.
        await expect(savedCharge(section, s.taxId)).toHaveCount(0);
        await expect(savedCharge(section, s.feeId)).toBeVisible();

        await applyForm(page, form);
        const {payload} = await saveAll(page);

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.has(s.taxId), `the TAX still exists: ${dump}`).toBe(true);
        expect(after.get(s.taxId)?.parent_transaction_id ?? null, `the TAX has no parent: ${dump}`).toBeNull();
        expect(after.get(s.feeId)?.parent_transaction_id, `the FEE is still linked: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count).toBe(1);
    });

    test('Delete: the FEE trashed in the BUY form is deleted, the TAX stays linked', async ({page, request}) => {
        const s = await seedLinkedBuy(page, request, owned, committedIds, 'chgw4');

        const form = await editFromTable(page, s);
        const section = await loadedCharges(form, s);
        const trash = savedCharge(section, s.feeId).locator('[data-testid^="tx-form-charge-remove-"]');
        await expect(trash, 'no trash on the FEE: the section is read-only in the form the Bulk hosts').toBeVisible({timeout: 8_000});
        await trash.click();
        await expect(savedCharge(section, s.feeId)).toHaveCount(0);
        await expect(savedCharge(section, s.taxId)).toBeVisible();

        await applyForm(page, form);
        const {payload} = await saveAll(page);

        const after = await readByIds(page, [s.buyId, s.feeId, s.taxId]);
        const dump = `server ${JSON.stringify([...after.values()])} — payload ${JSON.stringify(payload)}`;
        expect(after.has(s.feeId), `the FEE is gone: ${dump}`).toBe(false);
        expect(after.get(s.taxId)?.parent_transaction_id, `the TAX is still linked: ${dump}`).toBe(s.buyId);
        expect(after.get(s.buyId)?.charges_count).toBe(1);
    });
});
