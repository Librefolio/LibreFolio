/**
 * tx-bulk-promote-split.spec.ts — the sign of a merged pair in the bulk editor, and «Split pair» before the save (J-67).
 *
 * The editor holds the cash of a WITHDRAWAL as its magnitude and lets the type carry the sign (W-B65): a saved row
 * through `fieldsFromTx`, an imported one through `txCreateItemToPendingOp`, a row applied from the form through
 * `applyFormPayload`. `executePromote` (`$lib/features/transactions/bulk/TransactionBulkModal.svelte`) merges two
 * standalone rows into a pair. For two NEW rows it moves the sign into the amount (`applySignRules`) before the type
 * becomes the free-sign target; for two saved rows, and for a saved row with a new one (mixed), it changes the type to
 * CASH_TRANSFER / FX_CONVERSION and the withdrawal goes on holding +X. Three things follow:
 *
 *   facet 1  `collapseIntoPaired` picks the row the pair is shown as by `Number(cash)`: with two magnitudes it keeps
 *            opA — for the banner's suggestion of a mixed pair, the NEW row (`{tempIdA: new, tempIdB: saved}`) —
 *            whichever leg pays. Every dual cell (`renderDualHtml`) writes that row on «From:» and its hidden partner
 *            on «To:»;
 *   facet 2  the cash cell rebuilds a sign from the CURRENT type's rule, free once merged: «+X / +X»;
 *   facet 3  «Split pair» (row action `split`, offered on any row with a hidden partner, so on a merge not saved yet)
 *            takes a mixed pair shown as its new row through Case B/C of `handleSplitRow`, which types the two legs by
 *            the sign of that row's cash: a new WITHDRAWAL held +X becomes a DEPOSIT and the saved DEPOSIT a
 *            WITHDRAWAL; the merge stays in `pendingPromotes`, while the new row's `link_uuid` is cleared.
 *
 * Each test on an account of its own (see «Owned data»):
 *
 *   F3  (RED — the one to run first) a saved DEPOSIT of 731 on B in the editor, a NEW WITHDRAWAL of 731 on A added
 *       from the form, the same day → the banner's merge → «Split pair» on the pair row, then
 *         1. the grid: the new row a WITHDRAWAL again (−731), the saved one a DEPOSIT (+731), unchanged;
 *         2. the commit request: one create, a WITHDRAWAL of −731 on A without a link; no update; no promote;
 *         3. the answer and the account read back: committed; besides the float, the saved deposit untouched and one
 *            new WITHDRAWAL of −731 on A, nothing linked.
 *       Every assertion of the three parts is soft, so one run reports all of them, and every message carries what
 *       was received (the grid's readings, the creates / updates / promotes sent, the status and the issues answered,
 *       the rows read back); the annotation `J-67 F3 verdict` sums it up: REFUSED, WRONG DATA SAVED or RIGHT. Read
 *       from the code, today: the types are swapped in the grid; the save sends the new row as a DEPOSIT of +731 and
 *       the stale promote `{id_a: <the deposit>, link_uuid_b: <a uuid no create carries any more>}`, and leaves the
 *       deposit out (`resolveOps` skips a saved row whose id is promote-queued, and it has no hidden partner left);
 *       the backend cannot resolve that uuid (`promoteRefNotFound`, «Cannot resolve TX B reference») and refuses the
 *       batch. Of the claims, only «the saved deposit is not sent as an update» holds today.
 *   F1  (RED) a saved WITHDRAWAL of 642 on A in the editor, a NEW DEPOSIT of 642 on B added from the form → merged:
 *       the pair is shown as the withdrawal, the leg that pays. Today as the new deposit (opA).
 *   F2  (RED) the same merge: its cash cell has the withdrawal's leg negative, «From: −642 / To: +642». Today
 *       «+642 / +642».
 *   G   (guard, green today and after the cure) two NEW rows, a WITHDRAWAL of 553 on A and a DEPOSIT of 553 on B —
 *       the branch that already moves the sign: merged, the pair is shown as the withdrawal and reads −553 / +553
 *       (the positive control of F1's and F2's readings); split, the legs are a WITHDRAWAL and a DEPOSIT again (the
 *       control of F3's grid readings); saved, two creates, no promote, two unlinked rows. Nothing else pins it:
 *       tx-bulk-promote-exec merges and saves two new rows (PE4, PE6) and never splits them, tx-split-promote (C3)
 *       splits a SAVED pair (Case A).
 *
 * After the cure every test is green.
 *
 * ## What is read where
 *
 *   - The row a pair is shown as: its `tx-bulk-date[data-row-id]` (the shown op's tempId), against the tempId each
 *     leg had before the merge — a leg's row is the one its own add brought, never a position.
 *   - A type: the cell has no testid; DataTable's `td[data-column-id="type"]` and the `src` of its icon,
 *     `/icons/transactions/<type>.png` (`renderTypeHtml`), named after the type code — never the translated label.
 *   - A cash amount: DataTable's `td[data-column-id="cash"]`. The «From:» and «To:» lines of a pair carry nothing of
 *     their own, so the signed amounts are read from the cell's text as `formatCurrencyAmountHtml` writes them with a
 *     sign — `[+-]X[.,]00`, never the labels. The magnitudes stay under 1000 (no grouping separator), and a barrier
 *     first proves the amounts are written in clear (privacy off).
 *   - New or saved, and a saved row unchanged: `tx-bulk-row-status[data-status]` (`new`, `original`, `edited`).
 *   The type, cash and broker cells, and the From/To halves of a dual cell, have no testid of their own.
 *
 * ## The save gate
 *
 * Save opens `tx-bulk-unseen-suggestions` instead of committing while a suggestion is on offer, unseen. The merge
 * touches the banner (its link is clicked inside it), and after the split the banner offers the two legs again,
 * already seen; the 💡 offers nothing: every saved row but the float is in the editor, and the float pairs with no
 * row. A save that sends nothing names the gate.
 *
 * ## Owned data
 *
 * Each test registers a disposable account (`fixtures/owned-pair.ts` over `fixtures/onboarding-accounts.ts`: the
 * welcome hand-off, every onboarding flow skipped), creates two brokers A and B and reads them back — the account sees
 * exactly those, so the banner and the 💡 can only offer the test's own rows. Its rows are committed over the API, in
 * EUR: a float (DEPOSIT 5000 on A, the day before, never in the editor) funds A for a withdrawal; the legs are dated
 * the browser's own day, the date the form gives a new row. Nothing is shared, so the tests run in parallel. Cleanup:
 * leave the page (an unsaved editor goes with it), force-delete the two brokers with every row on them, delete the
 * account.
 *
 * Runs on the desktop project, like every transactions spec the runner registers.
 */
import {expect, test, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForSettled} from '../fixtures/app-events';
import {createOwnedBroker, type OwnedBroker} from '../fixtures/onboarding-accounts';
import {cleanupOwnedAccount, commitCreates, emptyOwnedAccount, listBrokers, openOwnedAccount, readTransactions, type OwnedAccount, type TxRow} from '../fixtures/owned-pair';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';

const COMMIT_PATH = '/api/v1/transactions/commit';
const UI_TIMEOUT = 10_000;
/** A save first lets the editor's validation settle, then waits for the commit. */
const SAVE_TIMEOUT = 20_000;
/** A's float: it funds a withdrawal on A, the day before. Never in the editor, and its amount is no leg's: it pairs with nothing. */
const FLOAT = 5000;
/** A row of the editor while it is new: its status cell says so. */
const NEW_ROW = '[data-testid="tx-bulk-row-status"][data-status="new"]';

type Brokers = {a: OwnedBroker; b: OwnedBroker};
type Money = {code: string; amount: string | number};
type CreateItem = {broker_id?: number; type?: string; date?: string; cash?: Money | null; description?: string | null; link_uuid?: string | null};
type CommitRequest = {creates?: CreateItem[]; updates?: Array<Record<string, unknown>>; deletes?: number[]; splits?: unknown[]; promotes?: Array<Record<string, unknown>>};
type Issue = {operation?: string; index?: number; ref_id?: number | null; code?: string | null; field?: string | null; error?: string | null};
type CommitBody = {committed?: boolean; issues?: Issue[]};
/** One Save: the request the editor sent, and the answer whatever it says. */
type SaveExchange = {request: CommitRequest; status: number; body: CommitBody | null; text: string};
type CreateFacts = {broker_id: number | null; type: string | null; cash: {code: string; amount: number} | null; link_uuid: string | null};
type SentFacts = {creates: CreateFacts[]; updates: Array<Record<string, unknown>>; deletes: number[]; splits: unknown[]; promotes: Array<Record<string, unknown>>};
type AnswerFacts = {status: number; committed: boolean | null; issues: Issue[]; text?: string};
/** A row of the account as the assertions compare it: `row` names the rows the test saved, `new` any other. */
type LedgerFact = {row: string; broker: string; type: string; amount: number; linked: number | null};
/** What a grid row shows, for the messages and the annotations: read once the row is known to be drawn. */
type GridFacts = {rowId: string | null; type: string | null; cash: string | null; status: string | null; partnerDate: string | null};

const byNumber = (a: number, b: number) => a - b;

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

/** The same facts in one order, whatever order they were read in. */
function canonical<T>(facts: T[]): T[] {
    return [...facts].sort((x, y) => JSON.stringify(x).localeCompare(JSON.stringify(y)));
}

// ---------------------------------------------------------------------------
// The account and its rows (API)
// ---------------------------------------------------------------------------

/**
 * A disposable account past the onboarding, with two brokers of its own, read back: the account sees exactly these.
 * Every id is recorded in `owned` before anything about it is checked. Returns the brokers and the browser's day.
 */
async function startOnOwnAccount(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string): Promise<{brokers: Brokers; today: string}> {
    await openOwnedAccount(page, request, owned, tag);
    const a = await createOwnedBroker(page, `${tag}-a`, owned.brokerIds);
    const b = await createOwnedBroker(page, `${tag}-b`, owned.brokerIds);
    const seen = (await listBrokers(page)).map((broker) => broker.id).sort(byNumber);
    expect(seen, 'premise: the account sees exactly the two brokers this test created').toEqual([a.id, b.id].sort(byNumber));
    return {brokers: {a, b}, today: await browserToday(page)};
}

/** A cash row as the API takes it, in EUR: a withdrawal's amount negative, a deposit's positive. */
function cashRow(broker: OwnedBroker, type: 'DEPOSIT' | 'WITHDRAWAL', date: string, magnitude: number, description: string): Record<string, unknown> {
    return {broker_id: broker.id, type, date, quantity: '0', cash: {code: 'EUR', amount: type === 'WITHDRAWAL' ? `-${magnitude}` : `${magnitude}`}, description};
}

/** Every row of the account, on its two brokers, as the assertions compare them; `names` labels the rows the test saved. */
async function readLedger(page: Page, brokers: Brokers, names: Record<number, string>): Promise<LedgerFact[]> {
    const rows: TxRow[] = [];
    for (const broker of [brokers.a, brokers.b]) rows.push(...(await readTransactions(page, {broker_id: broker.id})));
    const letter = (id: number) => (id === brokers.a.id ? 'A' : id === brokers.b.id ? 'B' : `broker ${id}`);
    return canonical(rows.map((tx) => ({row: names[tx.id] ?? 'new', broker: letter(tx.broker_id), type: tx.type, amount: Number(tx.cash?.amount ?? Number.NaN), linked: tx.related_transaction_id ?? null})));
}

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

/** The editor rows carrying a text only this test wrote. */
function bulkRowsWith(page: Page, text: string): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: text});
}

/** One editor row, by the tempId it publishes. */
function bulkRow(page: Page, rowId: string): Locator {
    return page.getByTestId('tx-bulk-body').locator(`tbody tr[data-row-id="${rowId}"]`);
}

/** The tempId of ONE row (call it on a locator proven to hold one). */
async function rowIdOf(row: Locator, label: string): Promise<string> {
    const rowId = await row.getAttribute('data-row-id');
    if (!rowId) throw new Error(`${label} carries no data-row-id`);
    return rowId;
}

function statusOf(row: Locator): Locator {
    return row.getByTestId('tx-bulk-row-status');
}

/** The type icon of a row (`renderTypeHtml`): named after the type code. The type cell has no testid of its own. */
function typeIcon(row: Locator): Locator {
    return row.locator('td[data-column-id="type"] img[src*="/icons/transactions/"]');
}

function iconOf(type: string): RegExp {
    return new RegExp(`/icons/transactions/${type.toLowerCase().replace(/_/g, '-')}\\.png$`);
}

/** The cash cell of a row. A pair's «From:» and «To:» lines carry no testid: the amounts are read from its text. */
function cashCell(row: Locator): Locator {
    return row.locator('td[data-column-id="cash"]');
}

/** An amount as the grid writes it (`formatCurrencyAmountHtml`, with a sign): ASCII sign, two decimals, either decimal separator. */
function signed(sign: '+' | '-', magnitude: number): string {
    return `${sign === '+' ? '\\+' : '-'}${magnitude}[.,]00`;
}

function shownAmount(sign: '+' | '-', magnitude: number): RegExp {
    return new RegExp(signed(sign, magnitude));
}

/** A dual cell: its «From:» line, then its «To:» line. */
function shownFromTo(from: '+' | '-', to: '+' | '-', magnitude: number): RegExp {
    return new RegExp(`${signed(from, magnitude)}[\\s\\S]*${signed(to, magnitude)}`);
}

/** `times` amounts of `magnitude`, whatever their sign: the barrier that proves the cell writes them in clear. */
function shownInClear(magnitude: number, times: 1 | 2): RegExp {
    return new RegExp(Array.from({length: times}, () => `[+-]${magnitude}[.,]00`).join('[\\s\\S]*'));
}

/** What a row shows, read once: for messages and annotations, never for a decision. */
async function gridFacts(row: Locator): Promise<GridFacts> {
    const read = <T>(value: Promise<T>): Promise<T | null> => value.catch(() => null);
    const src = await read(typeIcon(row).getAttribute('src', {timeout: 2_000}));
    const cash = await read(cashCell(row).textContent({timeout: 2_000}));
    return {
        rowId: await read(row.getAttribute('data-row-id', {timeout: 2_000})),
        type: src ? (/\/icons\/transactions\/([a-z-]+)\.png$/.exec(src)?.[1].toUpperCase().replace(/-/g, '_') ?? src) : null,
        cash: cash === null ? null : cash.replace(/\s+/g, ' ').trim(),
        status: await read(statusOf(row).getAttribute('data-status', {timeout: 2_000})),
        partnerDate: await read(row.getByTestId('tx-bulk-date').getAttribute('data-partner-date', {timeout: 2_000})),
    };
}

/**
 * The transactions page → tick one saved row → Edit. One selected row is an edit of that row: the editor opens its form
 * on top of the grid, closed here untouched. Returns the tempId of the row in the editor.
 */
async function openEditorOn(page: Page, saved: {label: string; id: number; description: string}): Promise<string> {
    await navigateTo(page, '/transactions');
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    const checkbox = transactionsPage.getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${saved.id}`);
    await expect(checkbox, `${saved.label} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const toolbar = transactionsPage.getByTestId('selection-toolbar');
    await expect(toolbar).toHaveAttribute('data-selected-count', '1');
    await toolbar.getByTestId('toolbar-action-edit').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'one row opens its own form').toBeVisible({timeout: UI_TIMEOUT});
    await form.getByTestId('tx-form-cancel').click();
    await expect(form, 'closed untouched').toBeHidden({timeout: UI_TIMEOUT});
    const row = bulkRowsWith(page, saved.description);
    await expect(row, `${saved.label} is in the editor`).toHaveCount(1, {timeout: UI_TIMEOUT});
    return rowIdOf(row, saved.label);
}

async function selectType(page: Page, typeCode: string): Promise<void> {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, broker: OwnedBroker): Promise<void> {
    const trigger = page.getByTestId('tx-form-broker-wrap').getByRole('combobox');
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const option = page.getByTestId(`search-select-option-${broker.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(broker.name);
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
 * `+ Add row` → the form → one EUR cash row pushed into the grid, today (the form's date), with no tags. A withdrawal is
 * typed as its magnitude too: the form signs it on the way out, and the editor holds it as the magnitude (W-B65).
 */
async function addCashRow(page: Page, row: {type: 'DEPOSIT' | 'WITHDRAWAL'; broker: OwnedBroker; magnitude: number; description: string}): Promise<void> {
    await page.getByTestId('tx-bulk-add-row').click();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, row.type);
    await pickBroker(page, row.broker);
    const amount = page.getByTestId('tx-form-cash-amount');
    await expect(amount).toBeVisible({timeout: UI_TIMEOUT});
    await amount.fill(String(row.magnitude));
    await amount.blur();
    await expect(amount).toHaveValue(String(row.magnitude));
    // The saved legs are in EUR, and a cash transfer needs one currency on both sides.
    await expect(page.getByTestId('tx-form-cash-currency')).toHaveText('EUR');
    await fillDescription(page, row.description);
    await applyForm(page);
}

/** The tempId of the row an add just brought: among the rows carrying `description`, the one not `known` before. */
async function addedRowId(page: Page, description: string, known: string[], label: string): Promise<string> {
    await expect(bulkRowsWith(page, description), `${label} joins the editor`).toHaveCount(known.length + 1, {timeout: UI_TIMEOUT});
    const added = page
        .getByTestId('tx-bulk-body')
        .locator(`tbody tr[data-row-id]${known.map((id) => `:not([data-row-id="${id}"])`).join('')}`)
        .filter({hasText: description});
    await expect(added, `one row is ${label}`).toHaveCount(1);
    return rowIdOf(added, label);
}

/**
 * The banner offers the one pair the editor holds — the two rows carrying `description` — and its link merges it at once:
 * one description, no tags on either leg, so no merge dialog. Returns the pair row.
 */
async function mergeTheOfferedPair(page: Page, description: string): Promise<Locator> {
    const rows = bulkRowsWith(page, description);
    await expect(rows, 'the two legs stand apart').toHaveCount(2, {timeout: UI_TIMEOUT});
    const banner = page.getByTestId('promote-suggest-banner');
    await expect(banner, 'the banner offers the pair').toBeVisible({timeout: UI_TIMEOUT});
    await expect(banner.getByTestId('promote-suggest-item-0')).toBeVisible();
    await expect(banner.getByTestId('promote-suggest-item-1'), 'and nothing else: the account holds no other pair').toHaveCount(0);
    await banner.getByTestId('promote-suggest-link-0').click();
    await expect(rows, 'merged at once into one pair row (one description, no tags: no merge dialog)').toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('promote-merge-confirm'), 'no merge dialog').toHaveCount(0);
    await expect(rows.getByTestId('tx-bulk-date'), 'the pair row carries its partner').toHaveAttribute('data-partner-date', /^\d{4}-\d{2}-\d{2}$/);
    await expect(banner, 'the merged pair was the only suggestion').toBeHidden();
    return rows;
}

/** «Split pair» from the pair row's menu (`row-actions-<tempId>` → `context-menu-action-split`). */
async function splitThePair(page: Page, pairRow: Locator): Promise<void> {
    const rowId = await rowIdOf(pairRow, 'the pair row');
    await pairRow.hover();
    const kebab = pairRow.getByTestId(`row-actions-${rowId}`);
    await expect(kebab).toBeVisible({timeout: UI_TIMEOUT});
    await kebab.click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    const split = menu.getByTestId('context-menu-action-split');
    await expect(split, 'a row with a hidden partner offers «Split pair», a merge not saved yet included').toBeVisible();
    await split.click();
    await expect(menu, 'the menu closes on its action').toBeHidden({timeout: UI_TIMEOUT});
}

/**
 * F1 and F2's start: a saved WITHDRAWAL of `magnitude` on A in the editor (A funded the day before), a NEW DEPOSIT of
 * `magnitude` on B added from the form, merged by the banner. Returns the pair row and the tempId each leg had before.
 */
async function mergeNewDepositIntoSavedWithdrawal(page: Page, request: APIRequestContext, owned: OwnedAccount, tag: string, label: string, magnitude: number): Promise<{pairRow: Locator; withdrawalTempId: string; depositTempId: string}> {
    const {brokers, today} = await startOnOwnAccount(page, request, owned, tag);
    const transfer = `J67 ${label} transfer ${uniqueSuffix()}`;
    const [float, withdrawal] = await commitCreates(page, [cashRow(brokers.a, 'DEPOSIT', dayBefore(today), FLOAT, `J67 ${label} float ${uniqueSuffix()}`), cashRow(brokers.a, 'WITHDRAWAL', today, magnitude, transfer)], 'save the float and the withdrawal on A');
    const expected = canonical([
        {row: 'float', broker: 'A', type: 'DEPOSIT', amount: FLOAT, linked: null},
        {row: 'saved withdrawal', broker: 'A', type: 'WITHDRAWAL', amount: -magnitude, linked: null},
    ]);
    expect(await readLedger(page, brokers, {[float]: 'float', [withdrawal]: 'saved withdrawal'}), 'premise: the float and the withdrawal on A, both standalone').toEqual(expected);

    const withdrawalTempId = await openEditorOn(page, {label: 'the saved withdrawal', id: withdrawal, description: transfer});
    await addCashRow(page, {type: 'DEPOSIT', broker: brokers.b, magnitude, description: transfer});
    const depositTempId = await addedRowId(page, transfer, [withdrawalTempId], 'the new deposit');
    await expect(statusOf(bulkRow(page, depositTempId)), 'premise: the deposit is a new row').toHaveAttribute('data-status', 'new');
    await expect(statusOf(bulkRow(page, withdrawalTempId)), 'premise: the withdrawal is the saved row, unchanged').toHaveAttribute('data-status', 'original');
    await expect(typeIcon(bulkRow(page, withdrawalTempId)), 'premise: a WITHDRAWAL').toHaveAttribute('src', iconOf('WITHDRAWAL'));
    const pairRow = await mergeTheOfferedPair(page, transfer);
    return {pairRow, withdrawalTempId, depositTempId};
}

// ---------------------------------------------------------------------------
// The save
// ---------------------------------------------------------------------------

function isCommitRequest(request: {method(): string; url(): string}): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMMIT_PATH;
}

/**
 * Save All once the editor has settled; returns the request the editor sent and the answer, whatever it says — the
 * callers assert it. A save that sends nothing names the unseen-suggestions gate if that is what stands in the way.
 */
async function saveCapturing(page: Page): Promise<SaveExchange> {
    const root = page.getByTestId('tx-bulk-modal-root');
    await waitForSettled(root, SAVE_TIMEOUT);
    const save = root.getByTestId('tx-bulk-commit');
    await expect(save, 'Save is enabled: the batch holds a change').toBeEnabled({timeout: UI_TIMEOUT});
    const answered = page.waitForResponse((response) => isCommitRequest(response.request()), {timeout: SAVE_TIMEOUT});
    // Handled below; this keeps a rejection from surfacing as unhandled before it is awaited.
    void answered.catch(() => undefined);
    await save.click();
    const response = await answered.catch(async (error: unknown): Promise<never> => {
        await expect(page.getByTestId('tx-bulk-unseen-suggestions'), 'Save opened the unseen-suggestions gate instead of committing: a suggestion was still on offer, unseen').toHaveCount(0);
        throw error;
    });
    const text = await response.text();
    let body: CommitBody | null = null;
    try {
        body = JSON.parse(text) as CommitBody;
    } catch {
        body = null;
    }
    return {request: response.request().postDataJSON() as CommitRequest, status: response.status(), body, text};
}

function sentFacts(request: CommitRequest): SentFacts {
    const createFacts = (create: CreateItem): CreateFacts => ({
        broker_id: create.broker_id ?? null,
        type: create.type ?? null,
        cash: create.cash ? {code: create.cash.code, amount: Number(create.cash.amount)} : null,
        link_uuid: create.link_uuid ?? null,
    });
    return {creates: (request.creates ?? []).map(createFacts), updates: request.updates ?? [], deletes: request.deletes ?? [], splits: request.splits ?? [], promotes: request.promotes ?? []};
}

function answerFacts(exchange: SaveExchange): AnswerFacts {
    const issues = (exchange.body?.issues ?? []).map(({operation, index, ref_id, code, field, error}) => ({operation, index, ref_id, code, field, error}));
    return {status: exchange.status, committed: exchange.body?.committed ?? null, issues, ...(exchange.body ? {} : {text: exchange.text.slice(0, 500)})};
}

/** F3 in one line: what the save did with the split rows. */
function f3Verdict(answer: AnswerFacts, before: LedgerFact[], after: LedgerFact[], expected: LedgerFact[]): string {
    const same = (x: LedgerFact[], y: LedgerFact[]) => JSON.stringify(x) === JSON.stringify(y);
    if (answer.committed === true && same(after, expected)) return 'RIGHT: committed — the new withdrawal saved as a WITHDRAWAL on A, the deposit untouched, nothing linked';
    if (answer.committed !== true && same(after, before)) return `REFUSED, nothing written: HTTP ${answer.status}, issues ${JSON.stringify(answer.issues.map((issue) => `${issue.operation}#${issue.index} ${issue.code ?? issue.error}`))}`;
    return `WRONG DATA SAVED: HTTP ${answer.status}, committed ${answer.committed}, the account holds ${JSON.stringify(after)}`;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor — the sign of a merged pair, and «Split pair» before the save (J-67)', () => {
    test.setTimeout(90_000);

    let owned: OwnedAccount = emptyOwnedAccount();

    test.beforeEach(() => {
        owned = emptyOwnedAccount();
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page, request}) => {
        await cleanupOwnedAccount(page, request, owned);
    });

    test('F3: «Split pair» right after merging a new withdrawal with a saved deposit gives each leg back — saved as a WITHDRAWAL −731 on A, the deposit untouched, no promote', async ({page, request}, testInfo) => {
        const X = 731;
        const {brokers, today} = await startOnOwnAccount(page, request, owned, `j67f3_${testInfo.project.name}`);
        const transfer = `J67 F3 transfer ${uniqueSuffix()}`;
        const [float, deposit] = await commitCreates(page, [cashRow(brokers.a, 'DEPOSIT', dayBefore(today), FLOAT, `J67 F3 float ${uniqueSuffix()}`), cashRow(brokers.b, 'DEPOSIT', today, X, transfer)], 'save the float on A and the deposit on B');
        const names = {[float]: 'float', [deposit]: 'saved deposit'};
        const before = await readLedger(page, brokers, names);
        const premise = canonical([
            {row: 'float', broker: 'A', type: 'DEPOSIT', amount: FLOAT, linked: null},
            {row: 'saved deposit', broker: 'B', type: 'DEPOSIT', amount: X, linked: null},
        ]);
        expect(before, 'premise: the float on A and the deposit on B, both standalone').toEqual(premise);

        // The saved deposit in the editor; the new withdrawal from the form — same day, description and (no) tags.
        const savedTempId = await openEditorOn(page, {label: 'the saved deposit', id: deposit, description: transfer});
        await addCashRow(page, {type: 'WITHDRAWAL', broker: brokers.a, magnitude: X, description: transfer});
        const newTempId = await addedRowId(page, transfer, [savedTempId], 'the new withdrawal');
        await expect(statusOf(bulkRow(page, newTempId)), 'premise: the withdrawal is a new row').toHaveAttribute('data-status', 'new');
        await expect(typeIcon(bulkRow(page, newTempId)), 'premise: the form pushed a WITHDRAWAL').toHaveAttribute('src', iconOf('WITHDRAWAL'));
        await expect(statusOf(bulkRow(page, savedTempId)), 'premise: the deposit is the saved row, unchanged').toHaveAttribute('data-status', 'original');

        // The banner merges the pair; «Split pair» undoes the merge before anything is saved.
        const pairRow = await mergeTheOfferedPair(page, transfer);
        const pairShownAs = await rowIdOf(pairRow, 'the pair row');
        await splitThePair(page, pairRow);
        const rows = bulkRowsWith(page, transfer);
        await expect(rows, '«Split pair» gives the two legs back as two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        // Found by what they are, never by tempId: a cure may rebuild a row from the store.
        const newRow = rows.filter({has: page.locator(NEW_ROW)});
        const savedRow = rows.filter({hasNot: page.locator(NEW_ROW)});
        await expect(newRow, 'one of them is the new row').toHaveCount(1);
        await expect(savedRow, 'the other the saved one').toHaveCount(1);
        for (const row of [newRow, savedRow]) {
            await expect(row.getByTestId('tx-bulk-date'), 'each a row of its own').toHaveAttribute('data-partner-date', '');
            await expect(cashCell(row), 'barrier: the amount is written in clear').toHaveText(shownInClear(X, 1));
        }

        // 1. The grid gives each leg its type back.
        const grid = {tempIds: {new: newTempId, saved: savedTempId, pairShownAs}, new: await gridFacts(newRow), saved: await gridFacts(savedRow)};
        const gridText = JSON.stringify(grid);
        await expect.soft(typeIcon(newRow), `1. the new row is a WITHDRAWAL again — grid: ${gridText}`).toHaveAttribute('src', iconOf('WITHDRAWAL'));
        await expect.soft(cashCell(newRow), `1. paying −${X} — grid: ${gridText}`).toHaveText(shownAmount('-', X));
        await expect.soft(typeIcon(savedRow), `1. the saved row is a DEPOSIT again — grid: ${gridText}`).toHaveAttribute('src', iconOf('DEPOSIT'));
        await expect.soft(cashCell(savedRow), `1. receiving +${X} — grid: ${gridText}`).toHaveText(shownAmount('+', X));
        await expect.soft(statusOf(savedRow), `1. and unchanged: nothing left to save on it — grid: ${gridText}`).toHaveAttribute('data-status', 'original');

        // 2. What the save sends.
        const exchange = await saveCapturing(page);
        const sent = sentFacts(exchange.request);
        const sentText = JSON.stringify(sent);
        expect.soft(sent.creates, `2. one create: the new row as a WITHDRAWAL of −${X} EUR on A (broker ${brokers.a.id}), without a link — sent: ${sentText}`).toEqual([{broker_id: brokers.a.id, type: 'WITHDRAWAL', cash: {code: 'EUR', amount: -X}, link_uuid: null}]);
        expect.soft(sent.updates, `2. no update: the saved deposit #${deposit} is as it was — sent: ${sentText}`).toEqual([]);
        expect.soft(sent.promotes, `2. no promote: the merge was undone — sent: ${sentText}`).toEqual([]);
        expect.soft({deletes: sent.deletes, splits: sent.splits}, `2. nothing deleted, no saved pair split — sent: ${sentText}`).toEqual({deletes: [], splits: []});

        // 3. What the backend answers, and what the account holds.
        const answer = answerFacts(exchange);
        const after = await readLedger(page, brokers, names);
        const expected = canonical([...premise, {row: 'new', broker: 'A', type: 'WITHDRAWAL', amount: -X, linked: null}]);
        const verdict = f3Verdict(answer, before, after, expected);
        testInfo.annotations.push({type: 'J-67 F3 verdict', description: verdict});
        testInfo.annotations.push({type: 'J-67 F3 detail', description: JSON.stringify({ids: {float, deposit, brokerA: brokers.a.id, brokerB: brokers.b.id}, grid, sent, answer, ledger: {before, after}})});
        expect.soft({status: answer.status, committed: answer.committed}, `3. the save goes through — ${verdict} — answer: ${JSON.stringify(answer)}`).toEqual({status: 200, committed: true});
        expect.soft(after, `3. besides the float, the saved deposit untouched and one new WITHDRAWAL of −${X} on A, nothing linked — ${verdict} — read back: ${JSON.stringify(after)}`).toEqual(expected);
    });

    test('F1: after merging a new deposit with a saved withdrawal, the pair is shown as the paying leg — the withdrawal on «From:», not the new deposit', async ({page, request}, testInfo) => {
        const {pairRow, withdrawalTempId, depositTempId} = await mergeNewDepositIntoSavedWithdrawal(page, request, owned, `j67f1_${testInfo.project.name}`, 'F1', 642);
        // Every dual cell writes the row the pair is shown as on «From:», its hidden partner on «To:» (`renderDualHtml`).
        const tempIds = JSON.stringify({withdrawal: withdrawalTempId, deposit: depositTempId});
        const shownAsWithdrawal = `the pair is shown as the withdrawal, the leg that pays, on «From:» — today as the new deposit, the banner's opA (tempIds: ${tempIds})`;
        await expect(pairRow.getByTestId('tx-bulk-date'), shownAsWithdrawal).toHaveAttribute('data-row-id', withdrawalTempId);
    });

    test('F2: the merged pair of a new deposit and a saved withdrawal reads −642 on the withdrawal’s leg — «From: −642 / To: +642», not «+642 / +642»', async ({page, request}, testInfo) => {
        const X = 642;
        const {pairRow, withdrawalTempId, depositTempId} = await mergeNewDepositIntoSavedWithdrawal(page, request, owned, `j67f2_${testInfo.project.name}`, 'F2', X);
        const cash = cashCell(pairRow);
        await expect(cash, 'barrier: the pair row’s cash cell writes both legs in clear').toHaveText(shownInClear(X, 2));
        const shownAs = await pairRow.getByTestId('tx-bulk-date').getAttribute('data-row-id');
        const seen = JSON.stringify({shownAs: shownAs === withdrawalTempId ? 'the withdrawal' : shownAs === depositTempId ? 'the new deposit' : shownAs, cell: ((await cash.textContent()) ?? '').replace(/\s+/g, ' ').trim()});
        // The deposit's leg reads +X in every version: a −X anywhere is the withdrawal's, whichever row the pair is shown as.
        await expect.soft(cash, `the withdrawal's leg is negative: −${X} — ${seen}`).toHaveText(shownAmount('-', X));
        await expect.soft(cash, `«From: −${X} / To: +${X}»: the paying leg first — ${seen}`).toHaveText(shownFromTo('-', '+', X));
    });

    test('G (guard): two new rows merged then split are a WITHDRAWAL and a DEPOSIT again — saved as two creates, no promote', async ({page, request}, testInfo) => {
        const X = 553;
        const {brokers, today} = await startOnOwnAccount(page, request, owned, `j67g_${testInfo.project.name}`);
        const floatText = `J67 G float ${uniqueSuffix()}`;
        const transfer = `J67 G transfer ${uniqueSuffix()}`;
        const [float] = await commitCreates(page, [cashRow(brokers.a, 'DEPOSIT', dayBefore(today), FLOAT, floatText)], 'save the float on A');
        // The editor opens on the float (left as it is, so never sent); the two legs come from the form.
        await openEditorOn(page, {label: 'the float', id: float, description: floatText});
        await addCashRow(page, {type: 'WITHDRAWAL', broker: brokers.a, magnitude: X, description: transfer});
        const withdrawalTempId = await addedRowId(page, transfer, [], 'the new withdrawal');
        await addCashRow(page, {type: 'DEPOSIT', broker: brokers.b, magnitude: X, description: transfer});
        const depositTempId = await addedRowId(page, transfer, [withdrawalTempId], 'the new deposit');

        // Merged: two new rows have the sign moved first — the positive control of F1's and F2's readings.
        const pairRow = await mergeTheOfferedPair(page, transfer);
        await expect(pairRow.getByTestId('tx-bulk-date'), 'the pair is shown as the withdrawal, the leg that pays').toHaveAttribute('data-row-id', withdrawalTempId);
        await expect(cashCell(pairRow), `«From: −${X} / To: +${X}»`).toHaveText(shownFromTo('-', '+', X));

        // Split: each leg back — the positive control of F3's grid readings.
        await splitThePair(page, pairRow);
        await expect(bulkRowsWith(page, transfer), '«Split pair» gives the two legs back as two rows').toHaveCount(2, {timeout: UI_TIMEOUT});
        const withdrawalRow = bulkRow(page, withdrawalTempId);
        const depositRow = bulkRow(page, depositTempId);
        for (const row of [withdrawalRow, depositRow]) await expect(row.getByTestId('tx-bulk-date'), 'each a row of its own').toHaveAttribute('data-partner-date', '');
        await expect(typeIcon(withdrawalRow), 'the withdrawal is a WITHDRAWAL again').toHaveAttribute('src', iconOf('WITHDRAWAL'));
        await expect(cashCell(withdrawalRow), `paying −${X}`).toHaveText(shownAmount('-', X));
        await expect(typeIcon(depositRow), 'the deposit is a DEPOSIT again').toHaveAttribute('src', iconOf('DEPOSIT'));
        await expect(cashCell(depositRow), `receiving +${X}`).toHaveText(shownAmount('+', X));

        // Saved: two creates without a link, nothing else.
        const exchange = await saveCapturing(page);
        const sent = sentFacts(exchange.request);
        const answer = answerFacts(exchange);
        const described = JSON.stringify({sent, answer});
        testInfo.annotations.push({type: 'J-67 G commit', description: described});
        const legs = canonical([
            {broker_id: brokers.a.id, type: 'WITHDRAWAL', cash: {code: 'EUR', amount: -X}, link_uuid: null},
            {broker_id: brokers.b.id, type: 'DEPOSIT', cash: {code: 'EUR', amount: X}, link_uuid: null},
        ]);
        expect(canonical(sent.creates), `two creates, a WITHDRAWAL −${X} on A and a DEPOSIT +${X} on B, unlinked — ${described}`).toEqual(legs);
        expect({updates: sent.updates, deletes: sent.deletes, splits: sent.splits, promotes: sent.promotes}, `nothing else: the float untouched, no promote — ${described}`).toEqual({updates: [], deletes: [], splits: [], promotes: []});
        expect({status: answer.status, committed: answer.committed}, `the batch is saved — ${described}`).toEqual({status: 200, committed: true});
        await expect(page.getByTestId('tx-bulk-modal'), 'a saved batch closes the editor').toBeHidden({timeout: UI_TIMEOUT});

        const ledger = canonical([
            {row: 'float', broker: 'A', type: 'DEPOSIT', amount: FLOAT, linked: null},
            {row: 'new', broker: 'A', type: 'WITHDRAWAL', amount: -X, linked: null},
            {row: 'new', broker: 'B', type: 'DEPOSIT', amount: X, linked: null},
        ]);
        expect(await readLedger(page, brokers, {[float]: 'float'}), 'the float, a WITHDRAWAL on A and a DEPOSIT on B, nothing linked').toEqual(ledger);
    });
});
