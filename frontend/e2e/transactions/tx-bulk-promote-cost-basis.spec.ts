/**
 * tx-bulk-promote-cost-basis.spec.ts — the bulk editor's side of a promote that leaves the
 * receiving side of an asset TRANSFER without a cost basis (d7c148564).
 *
 * `validate_cost_basis` (`backend/app/services/transaction_batch_stages.py`) checks promoted
 * pairs: once two ADJUSTMENTs are promoted into a TRANSFER, the receiving side (quantity > 0)
 * needs a cost basis like any other receiver, unless it is in Auto mode. A promoted NEW row is
 * checked as the create it is — `{operation: 'create', index: <its create index>}` — and a
 * promoted SAVED row on the promote that paired it — `{operation: 'promote', index: <promote
 * index>, ref_id: <its id>}` (`_check_promoted_saved_cost_basis`). The whole batch is refused.
 * The editor maps the issue onto its rows with `resolveBulkIssueRows`
 * (`$lib/utils/transactions/bulkDisplay.ts`): `create:<i>` names the new row, `promote:<i>` both
 * rows of that promote, and the jump lands on the one row the pair is shown as (the other half
 * is its hidden partner).
 *
 *   PC1  a NEW incoming ADJUSTMENT, Manual with an empty cost basis, promoted with a SAVED
 *        outgoing one through the selection toolbar → one `create` issue on its create index;
 *   PC2  a SAVED incoming ADJUSTMENT without a cost basis, promoted with a NEW outgoing one
 *        through the banner's link → one `promote` issue whose `ref_id` is the saved row;
 *   PC3  PC1's pair merged by the banner's «Merge all» together with a valid cash pair → the one
 *        `create` issue, and the jump lands on PC1's pair, not on the other one;
 *   PC4  (the banner, not the save) a new +5 beside a saved −3 and a saved −5 of the same asset:
 *        the banner offers one merge only, the −5's, never the crossed −3 / +5 the backend's
 *        promote rule refuses (`assetQuantitiesCancel`, `$lib/utils/transactions/promoteSuggest.ts`).
 *
 * PC1–PC3 each prove three things: the commit's answer, read against the request the editor
 * actually sent (indexes are looked up there by id and link_uuid, never assumed); that nothing
 * was written (the owned ledger is exactly as it was before the save); and that the refused-save
 * banner's issue (`tx-bulk-error` → `tx-bulk-issue`, i.e. `jumpToIssue`) highlights the pair's
 * row — `data-highlighted`, published by DataTable's `navigateToRowId` — and no other. An
 * unrelated saved row of an earlier date sits first in every grid, so "the first row" is never
 * the right answer by accident.
 *
 * ## PC2's saved receiver: why it is linked to a SPLIT event
 *
 * A saved incoming ADJUSTMENT without a cost basis cannot be created plainly through the public
 * API: a create without one is refused with `costBasisRequired` itself (backend test B2.8); Auto
 * mode stores the computed average cost (0 for an empty pool) or refuses with `wacFxUnavailable`;
 * an update cannot clear a cost basis (`None` there means "not sent"); and the promote's
 * `resolved_fields: {cost_basis_override: null}`, which does clear one, is API-only — the editor's
 * merge modal resolves description and tags, never a cost basis. The one public path is the row
 * the app itself stores without one: an ADJUSTMENT linked to a SPLIT asset event and saved in Auto
 * mode, whose cost the engines derive from the split ratio (`_compute_wac_for_auto_items`,
 * `is_split_linked`; backend test
 * `test_forward_split_relabelled_as_price_adjustment_becomes_an_unknown_cost_acquisition` asserts
 * `cost_basis_override is None`). The form saves the same row whenever a positive ADJUSTMENT is
 * linked to a split. PC2 creates it that way, verifies the precondition, then promotes it. In the
 * editor that row stays the pair's hidden half (the positive leg always is): it travels in the
 * promote only, never as an update, and nothing fills its cost basis — saved rows load in Manual,
 * and Auto only ever writes rows that are in Auto.
 *
 * ## The save gate
 *
 * Save opens `tx-bulk-unseen-suggestions` instead of committing while a merge suggestion is still
 * on offer and unseen: the banner's pairs until the banner is touched, the 💡's saved
 * counterparts until it is opened. Every test here merges every suggested pair before saving —
 * the banner, first seen on screen, is then asserted gone — and the 💡 could only offer saved
 * rows of the owned asset outside the editor, of which there are none. So Save must reach the
 * commit: `saveExpectingRefusal` waits for the refused-save banner OR the gate, and fails by name
 * if it is the gate, rather than clicking past it.
 *
 * ## Owned data, parallel-safe
 *
 * Each test creates its own asset and two brokers (PC2 also a SPLIT event) through the API and
 * writes only there, so no neighbour can add a balance, an average-cost input or a promote
 * candidate. Cleanup force-deletes the two brokers with every row on them, then the event, then
 * the asset — ids this test created, nothing else. The day is the browser's own (the form's
 * default date for a new row), so a new row and its saved counterpart share the banner's window.
 *
 * Runs on the desktop project, like every transactions spec the runner registers.
 */
import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;
/** A save first lets the editor's validate round trip settle, then waits for the commit. */
const SAVE_TIMEOUT = 20_000;
/** The issue `_append_cost_basis_issue` writes, whatever the operation it names. */
const COST_BASIS_REQUIRED = {code: 'costBasisRequired', field: 'cost_basis_override'} as const;

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Money = {code: string; amount: string};
type CreateItem = {
    broker_id: number;
    asset_id?: number;
    type: string;
    date: string;
    quantity: string;
    cash?: Money;
    description?: string;
    link_uuid?: string | null;
    cost_basis_override?: Money | null;
    cost_basis_mode?: string | null;
    asset_event_id?: number;
};
type PromoteItem = {id_a?: number; id_b?: number; link_uuid_a?: string; link_uuid_b?: string; resolved_fields?: Record<string, unknown>};
type CommitRequest = {creates?: CreateItem[]; updates?: Array<{id: number}>; deletes?: number[]; splits?: unknown[]; promotes?: PromoteItem[]};
type Issue = {operation: string; index: number; ref_id?: number | null; code?: string | null; field?: string | null};
type CommitBody = {committed: boolean; issues?: Issue[]; results?: Array<{operation: string; index?: number; ids?: number[]; status?: string}>};
type LedgerRow = {id: number; broker_id: number; type: string; quantity: string; related_transaction_id: number | null; cost_basis_override: Money | null; asset_event_id: number | null};

type Owned = {
    suffix: string;
    /** The browser's calendar day: the date the form gives a new row. */
    today: string;
    brokerIds: number[];
    assetIds: number[];
    eventIds: number[];
};
type Broker = {id: number; name: string};
type Brokers = {a: Broker; b: Broker};
type Asset = {id: number; name: string};
/** A row saved through the API: the label names it in messages, the id and the description find it. */
type Saved = {label: string; id: number; description: string};

// ---------------------------------------------------------------------------
// Owned data (API)
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

function isCommitRequest(request: {method(): string; url(): string}): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMMIT_PATH;
}

const byId = (a: number, b: number) => a - b;

/** The day before an ISO date, on the calendar: no clock involved. */
function dayBefore(isoDate: string): string {
    const day = new Date(`${isoDate}T00:00:00Z`);
    day.setUTCDate(day.getUTCDate() - 1);
    return day.toISOString().slice(0, 10);
}

/** The app's `todayIso()`, computed where the app computes it: in the browser. */
async function browserToday(page: Page): Promise<string> {
    return page.evaluate(() => {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    });
}

/** One EUR asset and two brokers only this test knows; every id is recorded for cleanup before anything can fail. */
async function ownAssetAndBrokers(page: Page, owned: Owned): Promise<{asset: Asset; brokers: Brokers}> {
    const assetName = `PCB asset ${owned.suffix}`;
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [{display_name: assetName, currency: 'EUR', asset_type: 'ETF'}]}), 'create the owned asset');
    const created = assets.results.find((item) => item.display_name === assetName);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);
    owned.assetIds.push(created.asset_id);

    const names = [`PCB broker A ${owned.suffix}`, `PCB broker B ${owned.suffix}`];
    const brokers = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: names.map((name) => ({name, opened_at: '2020-01-01'}))}), 'create the owned brokers');
    for (const item of brokers.results) {
        if (item.success && typeof item.broker_id === 'number' && names.includes(item.name)) owned.brokerIds.push(item.broker_id);
    }
    const [a, b] = names.map((name): Broker => {
        const id = brokers.results.find((item) => item.name === name && item.success)?.broker_id;
        if (typeof id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);
        return {id, name};
    });
    return {asset: {id: created.asset_id, name: assetName}, brokers: {a, b}};
}

/** A 2:1 SPLIT event on the owned asset, recorded the way the providers record one; returns its id. */
async function ownSplitEvent(page: Page, owned: Owned, asset: Asset, date: string): Promise<number> {
    const notes = `PCB split ${owned.suffix}`;
    await jsonFrom(await page.request.post(`${API}/assets/events`, {data: [{asset_id: asset.id, events: [{date, type: 'SPLIT', value: {code: 'EUR', amount: '2'}, notes}]}]}), 'create the owned SPLIT event');
    const queried = await jsonFrom<{items: Array<{asset_id: number; events: Array<{id: number; type: string; notes?: string | null}>}>}>(await page.request.post(`${API}/assets/events/query`, {data: [{asset_id: asset.id, date_range: {start: date, end: date}}]}), 'read the owned SPLIT event back');
    const event = queried.items.find((item) => item.asset_id === asset.id)?.events.find((candidate) => candidate.type === 'SPLIT' && candidate.notes === notes);
    if (!event) throw new Error(`The owned SPLIT event was not found: ${JSON.stringify(queried)}`);
    owned.eventIds.push(event.id);
    return event.id;
}

function adjustment(broker: Broker, asset: Asset, date: string, quantity: string, description: string, extra: Partial<CreateItem> = {}): CreateItem {
    return {broker_id: broker.id, asset_id: asset.id, type: 'ADJUSTMENT', date, quantity, description, ...extra};
}

function cashRow(broker: Broker, type: 'DEPOSIT' | 'WITHDRAWAL', date: string, amount: string, description: string): CreateItem {
    return {broker_id: broker.id, type, date, quantity: '0', cash: {code: 'EUR', amount}, description};
}

/** Commit the owned rows in one batch; returns them in the order given, each with its id. */
async function commitOwnedRows(page: Page, rows: Array<{label: string; create: CreateItem}>): Promise<Saved[]> {
    const body = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates: rows.map((row) => row.create)}}), 'commit the owned rows');
    expect(body.committed, `owned rows rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return rows.map((row, index) => {
        const id = body.results?.find((result) => result.operation === 'create' && result.index === index && result.status === 'success')?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`Owned row "${row.label}" got no id: ${JSON.stringify(body.results)}`);
        return {label: row.label, id, description: row.create.description ?? ''};
    });
}

/** Every row on the two owned brokers, by id. */
async function readOwnedLedger(page: Page, brokers: Brokers): Promise<LedgerRow[]> {
    const rows: LedgerRow[] = [];
    for (const broker of [brokers.a, brokers.b]) {
        rows.push(...(await jsonFrom<LedgerRow[]>(await page.request.get(`${API}/transactions`, {params: {broker_id: broker.id}}), `read the rows of ${broker.name}`)));
    }
    return rows.sort((x, y) => byId(x.id, y.id));
}

function ledgerShape(rows: LedgerRow[]) {
    return rows.map((row) => ({id: row.id, broker_id: row.broker_id, type: row.type, quantity: Number(row.quantity), related_transaction_id: row.related_transaction_id, cost_basis_override: row.cost_basis_override}));
}

/** The refused batch wrote nothing: same rows, each still of its own type, unlinked, with the same cost basis. */
async function expectLedgerUntouched(page: Page, brokers: Brokers, before: LedgerRow[]): Promise<void> {
    expect(ledgerShape(await readOwnedLedger(page, brokers)), 'the refused batch wrote nothing: the owned ledger is exactly as it was before the save').toEqual(ledgerShape(before));
}

/** Force-delete the owned brokers with every row on them, then the event, then the asset. */
async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Leave the page first: an editor still open on these rows goes with it, unsaved.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    // The brokers first: `force` deletes every row on them (a linked half included), and only then
    // will the event and the asset go — both refuse while a transaction still points at them.
    if (owned.brokerIds.length > 0) {
        await attempt(`brokers ${owned.brokerIds.join(', ')}`, async () => {
            const query = new URLSearchParams([...owned.brokerIds.map((id) => ['ids', String(id)]), ['force', 'true']]);
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?${query}`), 'delete the owned brokers');
            for (const id of owned.brokerIds) expect(result.results.find((item) => item.id === id)?.success, `broker ${id} deleted`).toBe(true);
        });
    }
    for (const eventId of owned.eventIds) {
        await attempt(`event ${eventId}`, async () => {
            const result = await jsonFrom<{results: Array<{event_id: number; status: string}>}>(await page.request.delete(`${API}/assets/events?ids=${eventId}`), 'delete the owned event');
            expect(result.results.find((item) => item.event_id === eventId)?.status).toBe('deleted');
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`These checks write owned rows and may only run against the local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `pcb${testInfo.workerIndex}-${uniqueSuffix()}`, today: '', brokerIds: [], assetIds: [], eventIds: []};
        try {
            await login(page, TEST_USER);
            owned.today = await browserToday(page);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(90_000);

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

function bulkRows(page: Page): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
}

/** The editor rows carrying a description only this test wrote. */
function bulkRowsWith(page: Page, description: string): Locator {
    return bulkRows(page).filter({hasText: description});
}

/**
 * The transactions page on the two owned brokers only → tick the saved rows → Edit. Ends with
 * every one of them in the editor's grid and no form on top of it (two rows or more never
 * auto-open the form).
 */
async function openEditorOn(page: Page, brokers: Brokers, rows: Saved[]): Promise<void> {
    await navigateTo(page, `/transactions?${new URLSearchParams({broker_ids: `${brokers.a.id},${brokers.b.id}`})}`);
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    const table = transactionsPage.getByTestId('tx-table');
    for (const row of rows) {
        const checkbox = table.getByTestId(`dt-row-checkbox-tx-${row.id}`);
        await expect(checkbox, `${row.label} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    const toolbar = transactionsPage.getByTestId('selection-toolbar');
    await expect(toolbar).toHaveAttribute('data-selected-count', String(rows.length));
    await toolbar.getByTestId('toolbar-action-edit').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    for (const row of rows) await expect(bulkRowsWith(page, row.description), `${row.label} is in the editor`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('tx-form-modal')).toBeHidden();
}

async function selectType(page: Page, typeCode: string): Promise<void> {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, broker: Broker): Promise<void> {
    const trigger = page.getByTestId('tx-form-broker-wrap').getByRole('combobox');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const option = page.getByTestId(`search-select-option-${broker.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(broker.name);
}

/** The asset select searches inline: narrow it to the owned asset's unique name, then pick it by id. */
async function pickAsset(page: Page, asset: Asset): Promise<void> {
    const trigger = page.getByTestId('tx-form-asset-trigger');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const search = page.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: UI_TIMEOUT});
    await search.fill(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(asset.name);
}

async function fillQuantity(page: Page, quantity: string): Promise<void> {
    const input = page.getByTestId('tx-form-quantity');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(quantity);
    await input.blur();
    await expect(input).toHaveValue(quantity);
}

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(page: Page, text: string): Promise<void> {
    const details = page.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: UI_TIMEOUT});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await page.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = page.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

/** Push the form's draft into the grid. */
async function applyForm(page: Page): Promise<void> {
    const apply = page.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: UI_TIMEOUT});
    await apply.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: UI_TIMEOUT});
}

/**
 * `+ Add row` → the form → one ADJUSTMENT pushed into the grid.
 *
 * `withoutCostBasis` is the receiver under test, NOT in Auto mode: Manual is chosen first, before
 * the form is complete enough to validate (Auto is the form's default for a positive ADJUSTMENT,
 * and an Auto validate writes the computed cost into the field), and the field is then left alone,
 * as by a user who skips it. The form's own warning (`tx-form-cost-basis-warning`: positive
 * quantity, not Auto, no amount) proves the draft is in exactly that state when it is applied.
 */
async function addAdjustment(page: Page, row: {broker: Broker; asset: Asset; quantity: string; description: string; withoutCostBasis?: boolean}): Promise<void> {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, 'ADJUSTMENT');
    const manual = page.getByTestId('tx-form-cost-basis-toggle-manual');
    if (row.withoutCostBasis) {
        await expect(manual).toBeVisible({timeout: UI_TIMEOUT});
        await manual.click();
        await expect(manual).toHaveAttribute('aria-pressed', 'true');
    }
    await pickBroker(page, row.broker);
    await pickAsset(page, row.asset);
    await fillQuantity(page, row.quantity);
    await fillDescription(page, row.description);
    if (row.withoutCostBasis) {
        await expect(manual, 'the receiver stays in Manual mode').toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('tx-form-cost-basis-input-amount'), 'with no cost basis typed').toHaveValue('');
        await expect(page.getByTestId('tx-form-cost-basis-warning'), 'the form says it: Manual, positive quantity, no amount').toBeVisible();
    }
    await applyForm(page);
}

/** `+ Add row` → the form → one EUR DEPOSIT pushed into the grid. */
async function addDeposit(page: Page, row: {broker: Broker; amount: string; description: string}): Promise<void> {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, 'DEPOSIT');
    await pickBroker(page, row.broker);
    const amount = page.getByTestId('tx-form-cash-amount');
    await expect(amount).toBeVisible({timeout: UI_TIMEOUT});
    await amount.fill(row.amount);
    await amount.blur();
    await expect(amount).toHaveValue(row.amount);
    // The saved half is in EUR, and a cash transfer needs one currency on both sides.
    await expect(page.getByTestId('tx-form-cash-currency')).toHaveText('EUR');
    await fillDescription(page, row.description);
    await applyForm(page);
}

/** Bring the checkbox of every row of an ALREADY-FILTERED locator to `checked`, whatever state it starts in. */
async function selectBulkRows(rows: Locator, count: number): Promise<void> {
    await expect(rows).toHaveCount(count, {timeout: UI_TIMEOUT});
    for (let i = 0; i < count; i++) {
        const checkbox = rows.nth(i).locator('[data-testid^="dt-row-checkbox-"]');
        await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
        if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
}

/** The banner offers the pairs this test built, and nothing else: items 0..count-1, no item `count`. */
async function expectBannerOffers(page: Page, count: number): Promise<Locator> {
    const banner = page.getByTestId('promote-suggest-banner');
    await expect(banner).toBeVisible({timeout: UI_TIMEOUT});
    for (let i = 0; i < count; i++) await expect(banner.getByTestId(`promote-suggest-item-${i}`)).toBeVisible();
    await expect(banner.getByTestId(`promote-suggest-item-${count}`)).toHaveCount(0);
    return banner;
}

/**
 * Save All on a batch the backend must refuse; returns the request the editor sent and the answer.
 *
 * The save gate is handled explicitly (see the header): with every suggested pair merged, Save
 * must reach the commit. Whichever comes first — the refused-save banner or the
 * `tx-bulk-unseen-suggestions` gate — is waited for, and the gate fails the test by name.
 */
async function saveExpectingRefusal(page: Page): Promise<{request: CommitRequest; body: CommitBody}> {
    await waitForSettled(page.getByTestId('tx-bulk-modal-root'), SAVE_TIMEOUT);
    const save = page.getByTestId('tx-bulk-commit');
    await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
    const answered = page.waitForResponse((response) => isCommitRequest(response.request()), {timeout: SAVE_TIMEOUT});
    // If the gate opens nothing is ever sent: the assertion below says so, and this wait must not
    // outlive the test as an unhandled rejection.
    void answered.catch(() => undefined);
    await save.click();
    const gate = page.getByTestId('tx-bulk-unseen-suggestions');
    const refused = page.getByTestId('tx-bulk-error');
    await expect(gate.or(refused), 'Save answers with the refused-save banner (or, wrongly, with the unseen-suggestions gate)').toBeVisible({timeout: SAVE_TIMEOUT});
    await expect(gate, 'Save opened the unseen-suggestions gate: a merge suggestion was still on offer, and nothing was committed').toHaveCount(0);
    const response = await answered;
    return {request: response.request().postDataJSON() as CommitRequest, body: await jsonFrom<CommitBody>(response, 'Save All')};
}

/** The index, among the creates the editor sent, of the one new row a promote consumes by link_uuid. */
function consumedCreateIndex(request: CommitRequest, promote: PromoteItem): number {
    const uuids = [promote.link_uuid_a, promote.link_uuid_b].filter((uuid): uuid is string => !!uuid);
    const indices = (request.creates ?? []).flatMap((create, index) => (create.link_uuid && uuids.includes(create.link_uuid) ? [index] : []));
    expect(indices, `exactly one create carries the promote's link_uuid: ${JSON.stringify(request)}`).toHaveLength(1);
    return indices[0];
}

const BALANCE_CODES = new Set(['balanceCashNegative', 'balanceAssetNegative']);

/**
 * The commit's answer next to what the editor sent, with this test's ids named: what a red has to
 * print, and what the report keeps on a green (`commit answer` annotation).
 */
function describeAnswer(request: CommitRequest, body: CommitBody, ids: Record<string, number>): string {
    const answer = JSON.stringify({ids, committed: body.committed, issues: body.issues ?? [], results: body.results ?? [], sent: {creates: request.creates ?? [], updates: request.updates ?? [], promotes: request.promotes ?? []}});
    test.info().annotations.push({type: 'commit answer', description: answer});
    return answer;
}

/** The refused-save banner's one issue jumps to `pairRow`, and only there. */
async function expectIssueJumpsTo(page: Page, pairRow: Locator, otherRows: Locator[]): Promise<void> {
    const issue = page.getByTestId('tx-bulk-error').getByTestId('tx-bulk-issue');
    await expect(issue, 'the refused-save banner lists the one issue').toHaveCount(1);
    await expect(pairRow, 'the pair is one row on screen').toHaveCount(1);
    for (const row of [pairRow, ...otherRows]) await expect(row).toHaveAttribute('data-highlighted', 'false');
    await issue.click();
    await expect(pairRow, 'the issue jumps to the row the pair is shown as').toHaveAttribute('data-highlighted', 'true');
    for (const row of otherRows) await expect(row, 'and to no other row').toHaveAttribute('data-highlighted', 'false');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor — a promoted receiver without a cost basis is refused', () => {
    test('PC1: a new receiver, Manual with no cost basis, promoted with a saved sender → create issue, pointed at the pair', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const transfer = `PCB transfer ${owned.suffix}`;
        // A: the position (+10, with its cost) and, the next day, the outgoing −5 that will be promoted.
        const [fund, sender] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'sender', create: adjustment(brokers.a, asset, owned.today, '-5', transfer)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, sender.id].sort(byId));

        await openEditorOn(page, brokers, [fund, sender]);
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: transfer, withoutCostBasis: true});
        const pairRows = bulkRowsWith(page, transfer);
        await expect(pairRows).toHaveCount(2, {timeout: UI_TIMEOUT});

        // The banner offers the pair — the presence behind the absence asserted once it is merged —
        // and the selection toolbar merges it, as tx-bulk-promote-exec PE5 does for a new + saved pair.
        const banner = await expectBannerOffers(page, 1);
        await selectBulkRows(pairRows, 2);
        await page.getByTestId('promote-toolbar-confirm').click();
        await expect(pairRows, 'the two rows collapse into one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'the merged pair was the only suggestion').toBeHidden();

        const {request, body} = await saveExpectingRefusal(page);
        const answer = describeAnswer(request, body, {fund: fund.id, sender: sender.id});
        expect(body.committed, `the batch must be refused — ${answer}`).toBe(false);
        const promote = (request.promotes ?? []).find((item) => item.id_a === sender.id || item.id_b === sender.id);
        expect(promote, `the saved sender is promoted — ${answer}`).toBeTruthy();
        const receiverIndex = consumedCreateIndex(request, promote!);
        const receiver = request.creates![receiverIndex];
        expect(receiver, `the new receiver is the create the promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, asset_id: asset.id, type: 'ADJUSTMENT', description: transfer});
        expect(Number(receiver.quantity), answer).toBe(5);
        expect(receiver.cost_basis_override ?? null, `the receiver is sent without a cost basis — ${answer}`).toBeNull();
        expect(receiver.cost_basis_mode ?? null, `and not in Auto mode — ${answer}`).toBeNull();
        expect(body.issues, `one issue: the new receiver, checked as the create it is — ${answer}`).toEqual([expect.objectContaining({...COST_BASIS_REQUIRED, operation: 'create', index: receiverIndex})]);
        expect(body.issues![0].ref_id ?? null, answer).toBeNull();

        await expectIssueJumpsTo(page, pairRows, [bulkRowsWith(page, fund.description)]);
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC2: a saved receiver without a cost basis, promoted with a new sender → promote issue naming it, pointed at the pair', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const split = await ownSplitEvent(page, owned, asset, owned.today);
        const transfer = `PCB transfer ${owned.suffix}`;
        const [fund, receiver] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            // Auto on a SPLIT-linked ADJUSTMENT: the one public path to a saved receiver with no cost basis (see the header).
            {label: 'receiver', create: adjustment(brokers.b, asset, owned.today, '5', transfer, {asset_event_id: split, cost_basis_mode: 'auto'})},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, receiver.id].sort(byId));
        const savedReceiver = before.find((row) => row.id === receiver.id);
        expect(savedReceiver, 'precondition: an incoming ADJUSTMENT, standalone, saved WITHOUT a cost basis').toMatchObject({broker_id: brokers.b.id, type: 'ADJUSTMENT', related_transaction_id: null, cost_basis_override: null, asset_event_id: split});
        expect(Number(savedReceiver!.quantity)).toBe(5);

        await openEditorOn(page, brokers, [fund, receiver]);
        await addAdjustment(page, {broker: brokers.a, asset, quantity: '-5', description: transfer});
        const pairRows = bulkRowsWith(page, transfer);
        await expect(pairRows).toHaveCount(2, {timeout: UI_TIMEOUT});

        // Merged from the banner's own link, as tx-bulk-promote-exec PE6 does: a click inside the banner.
        const banner = await expectBannerOffers(page, 1);
        await banner.getByTestId('promote-suggest-link-0').click();
        await expect(pairRows, 'the two rows collapse into one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'the merged pair was the only suggestion').toBeHidden();

        const {request, body} = await saveExpectingRefusal(page);
        const answer = describeAnswer(request, body, {fund: fund.id, receiver: receiver.id});
        expect(body.committed, `the batch must be refused — ${answer}`).toBe(false);
        // The saved receiver must travel in the promote only. Sent as an update too, the backend would
        // check it as an update and skip it on the promote (`_check_promoted_saved_cost_basis`), so it
        // is the one row that must not be among the updates. Other saved rows may be: today the
        // untouched fund is, re-sent as a no-op update because the editor compares a cost basis by
        // reference (`fieldEq('cost_basis_override', …)`). That is reported apart and deliberately
        // not asserted here, either way.
        const updatedIds = (request.updates ?? []).map((item) => item.id);
        expect(updatedIds, `the saved receiver is not sent as an update — ${answer}`).not.toContain(receiver.id);
        const promoteIndex = (request.promotes ?? []).findIndex((item) => item.id_a === receiver.id || item.id_b === receiver.id);
        expect(promoteIndex, `the saved receiver is promoted — ${answer}`).toBeGreaterThanOrEqual(0);
        const promote = request.promotes![promoteIndex];
        expect('cost_basis_override' in (promote.resolved_fields ?? {}), `nor given a cost basis by the promote — ${answer}`).toBe(false);
        const sender = request.creates![consumedCreateIndex(request, promote)];
        expect(sender, `the new sender is the create the promote consumes — ${answer}`).toMatchObject({broker_id: brokers.a.id, asset_id: asset.id, type: 'ADJUSTMENT', description: transfer});
        expect(Number(sender.quantity), answer).toBe(-5);
        // The subject, soft: whatever the answer is, the run goes on to show where the editor points it.
        expect.soft(body.issues, `one issue: the saved receiver, on the promote that paired it — ${answer}`).toEqual([expect.objectContaining({...COST_BASIS_REQUIRED, operation: 'promote', index: promoteIndex, ref_id: receiver.id})]);

        // The core: the refusal, whatever its code, is one row issue and it jumps to the pair's row.
        const rowIssues = (body.issues ?? []).filter((issue) => !BALANCE_CODES.has(issue.code ?? ''));
        expect(rowIssues, `the refusal is one row issue — ${answer}`).toHaveLength(1);
        await expectIssueJumpsTo(page, pairRows, [bulkRowsWith(page, fund.description)]);
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC3: «Merge all» of two pairs → the one create issue points at the asset pair, not at the cash pair', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const transfer = `PCB transfer ${owned.suffix}`;
        const wire = `PCB wire ${owned.suffix}`;
        // The second pair is a cash one on purpose: a WITHDRAWAL and a DEPOSIT can only meet each other,
        // so the pairs «Merge all» takes do not depend on how the banner matches asset quantities —
        // which PC4 checks on its own (the selection toolbar still matches them on opposite signs only).
        const [fund, float, sender, withdrawal] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'float', create: cashRow(brokers.a, 'DEPOSIT', dayBefore(owned.today), '1000', `PCB float ${owned.suffix}`)},
            {label: 'sender', create: adjustment(brokers.a, asset, owned.today, '-5', transfer)},
            {label: 'withdrawal', create: cashRow(brokers.a, 'WITHDRAWAL', owned.today, '-173', wire)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, float.id, sender.id, withdrawal.id].sort(byId));

        await openEditorOn(page, brokers, [fund, sender, withdrawal]);
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: transfer, withoutCostBasis: true});
        await addDeposit(page, {broker: brokers.b, amount: '173', description: wire});
        const transferRows = bulkRowsWith(page, transfer);
        const wireRows = bulkRowsWith(page, wire);
        await expect(transferRows).toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(wireRows).toHaveCount(2, {timeout: UI_TIMEOUT});

        // Two pairs on offer, which is what makes «Merge all» appear at all.
        const banner = await expectBannerOffers(page, 2);
        await banner.getByTestId('promote-suggest-merge-all').click();
        const mergeAll = page.getByTestId('promote-all-modal');
        await expect(mergeAll).toBeVisible({timeout: UI_TIMEOUT});
        await mergeAll.getByTestId('promote-all-confirm').click();
        await expect(mergeAll).toBeHidden({timeout: UI_TIMEOUT});
        await expect(transferRows, 'the asset pair is one row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(wireRows, 'the cash pair is one row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(banner, 'both suggestions are merged').toBeHidden();

        const {request, body} = await saveExpectingRefusal(page);
        const answer = describeAnswer(request, body, {fund: fund.id, float: float.id, sender: sender.id, withdrawal: withdrawal.id});
        expect(body.committed, `the batch must be refused — ${answer}`).toBe(false);
        const promotes = request.promotes ?? [];
        expect(promotes, `«Merge all» sends one promote per pair — ${answer}`).toHaveLength(2);
        const transferPromote = promotes.find((item) => item.id_a === sender.id || item.id_b === sender.id);
        const wirePromote = promotes.find((item) => item.id_a === withdrawal.id || item.id_b === withdrawal.id);
        expect(transferPromote, `the saved sender is promoted — ${answer}`).toBeTruthy();
        expect(wirePromote, `the saved withdrawal is promoted — ${answer}`).toBeTruthy();
        const receiverIndex = consumedCreateIndex(request, transferPromote!);
        const depositIndex = consumedCreateIndex(request, wirePromote!);
        const receiver = request.creates![receiverIndex];
        expect(receiver, `the new receiver is the create the asset promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, asset_id: asset.id, type: 'ADJUSTMENT', description: transfer});
        expect(Number(receiver.quantity), answer).toBe(5);
        expect(receiver.cost_basis_override ?? null, `the receiver is sent without a cost basis — ${answer}`).toBeNull();
        expect(receiver.cost_basis_mode ?? null, `and not in Auto mode — ${answer}`).toBeNull();
        expect(request.creates![depositIndex], `the new deposit is the create the cash promote consumes — ${answer}`).toMatchObject({broker_id: brokers.b.id, type: 'DEPOSIT', description: wire, cash: {code: 'EUR'}});
        expect(body.issues, `one issue: the asset receiver; the cash pair is valid — ${answer}`).toEqual([expect.objectContaining({...COST_BASIS_REQUIRED, operation: 'create', index: receiverIndex})]);

        await expectIssueJumpsTo(page, transferRows, [bulkRowsWith(page, fund.description), wireRows]);
        await expectLedgerUntouched(page, brokers, before);
    });

    test('PC4: the banner offers a new +5 the saved −5 it cancels, never the saved −3 beside it', async ({page, owned}) => {
        const {asset, brokers} = await ownAssetAndBrokers(page, owned);
        const exact = `PCB exact ${owned.suffix}`;
        const short = `PCB short ${owned.suffix}`;
        // A: the position, then two saved outgoing legs of the same asset on the same day, −3 and −5.
        const [fund, shortLeg, exactLeg] = await commitOwnedRows(page, [
            {label: 'fund', create: adjustment(brokers.a, asset, dayBefore(owned.today), '10', `PCB fund ${owned.suffix}`, {cost_basis_override: {code: 'EUR', amount: '50'}})},
            {label: 'saved −3', create: adjustment(brokers.a, asset, owned.today, '-3', short)},
            {label: 'saved −5', create: adjustment(brokers.a, asset, owned.today, '-5', exact)},
        ]);
        const before = await readOwnedLedger(page, brokers);
        expect(before.map((row) => row.id)).toEqual([fund.id, shortLeg.id, exactLeg.id].sort(byId));

        await openEditorOn(page, brokers, [fund, shortLeg, exactLeg]);
        // The banner derives from the rows on screen, synchronously: with the saved rows alone — all on
        // broker A — there is nothing to offer.
        const banner = page.getByTestId('promote-suggest-banner');
        await expect(banner, 'the saved rows alone pair with nothing').toBeHidden();
        // A new +5 on B, with the −5's description: taking the −5's merge then needs no merge modal.
        await addAdjustment(page, {broker: brokers.b, asset, quantity: '5', description: exact});
        const exactRows = bulkRowsWith(page, exact);
        const shortRow = bulkRowsWith(page, short);
        await expect(exactRows, 'the saved −5 and the new +5 are two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        await expect(shortRow).toHaveCount(1);

        // Both saved legs are opposite in sign to the new +5, and only the −5 cancels it: one merge on
        // offer, so nothing for «Merge all» either. A banner item names its rows only in translated text,
        // so which pair it is gets proven by taking it.
        await expectBannerOffers(page, 1);
        await expect(banner.getByTestId('promote-suggest-merge-all'), 'one pair: no «Merge all»').toHaveCount(0);
        await banner.getByTestId('promote-suggest-link-0').click();
        await expect(exactRows, 'the offered merge was the −5 one: the +5 joined it into one pair row').toHaveCount(1, {timeout: UI_TIMEOUT});
        await expect(exactRows.getByTestId('tx-bulk-date'), 'the −5 row now carries its partner').toHaveAttribute('data-partner-date', /^\d{4}-\d{2}-\d{2}$/);
        await expect(shortRow.getByTestId('tx-bulk-date'), 'the −3 is still on its own').toHaveAttribute('data-partner-date', '');
        await expect(banner, 'and nothing is offered for the −3').toBeHidden();

        // Nothing was saved: the editor is left open and discarded by the cleanup.
        await expectLedgerUntouched(page, brokers, before);
    });
});
