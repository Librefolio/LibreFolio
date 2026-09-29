/**
 * tx-selection-after-bulk.spec.ts — K step 12a: the Transactions page's selection once an
 * operation on it is over.
 *
 * The page keeps two selections that have to agree:
 *   - `selectedRows`, page state: the header toolbar (`selection-toolbar`, with
 *     `data-selected-count`) is rendered only while it is non-empty;
 *   - the DataTable's own row selection: the checkboxes `dt-row-checkbox-tx-{id}`,
 *     `data-state="checked|unchecked"`.
 *
 * Contract (developer decisions D-a1 and D-a2, plan step 12 section a):
 *   - after ANY executed operation — edit, clone, delete, add, link, unlink — the selection is
 *     empty: no toolbar, no checkbox checked, and the next single click selects exactly one
 *     row. Import is not driven here: its rows are saved by the same bulk-editor commit and
 *     reach the page through the same `onCommitted` handler as Add, which E4 covers;
 *   - after a CANCELLED one — editor closed untouched, editor discarded through its confirm,
 *     link cancelled, unlink cancelled — the selection is exactly what it was, and the next
 *     click adds to it.
 *
 * Every verdict reads both selections at once — the toolbar count and the checkbox of every
 * row the test owns — so a red prints the whole observed state, not its first symptom. The
 * two verdicts of a test are soft: a red after the operation still lets the "next click"
 * verdict run and report what the user would then see. Each verdict follows a barrier proving
 * the operation landed (commit answered, modal gone, the reloaded table showing the result),
 * and every absence it asserts sits beside a presence: the owned rows are on screen.
 *
 * Owned data: every test creates two brokers (unique names) and its rows through the API,
 * opens `/transactions?broker_ids=<a>,<b>` so the table shows nothing else, and in its cleanup
 * deletes by id every row found on its two brokers — clones and adds made through the UI
 * included — then the brokers. Rows are identified by id, or by a description only the test
 * knows; nothing global is read or counted.
 *
 * The transactions guides are not under test, and their coachmarks can sit over the controls
 * clicked here, so the page gets a terminal onboarding view (the
 * `tx-broker-icon-hydration.spec.ts` pattern): page-scoped, it never writes TEST_USER's
 * onboarding rows.
 *
 * Runs on the desktop project, like every transactions spec the runner registers.
 *
 * Key data-testids used:
 *   transactions-page [data-busy]                    — the page's own "every load wave is in"
 *   selection-toolbar [data-selected-count]          — the page selection (absent when empty)
 *   dt-row-checkbox-tx-{id} [data-state]             — the table selection
 *   toolbar-action-edit|clone|delete|promote         — the toolbar actions
 *   tx-add-button, tx-form-*                         — a new row through the bulk editor's form
 *   tx-bulk-modal, tx-bulk-body, tx-bulk-commit      — the bulk editor and its Save All
 *   tx-bulk-close, tx-bulk-cancel                    — closing the bulk editor
 *   confirm-modal-confirm                            — the editor's discard confirm (C2)
 *   confirm-modal-confirm / confirm-modal-cancel     — "Link as pair" confirm (identical fields)
 *   row-actions-tx-{id} → context-menu-action-split  — unlink a pair from its row
 *   tx-action-modal, tx-action-modal-confirm|-cancel — the unlink confirm
 *   tx-desc-{id}, tx-link-icon-{id}                  — the reloaded table shows the result
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
/** The subject verdicts come after barriers that already waited for the operation to land. */
const VERDICT_TIMEOUT = 5_000;
const FUND_DATE = '2024-01-02';
const PAIR_DATE = '2024-01-03';

const TERMINAL_ONBOARDING_AT = '2026-01-01T00:00:00Z';
const TERMINAL_ONBOARDING_FLOW_STEPS = [
    {flow: 'welcome', steps: []},
    {
        flow: 'intro_tour',
        steps: ['intro.scene', 'intro.navigation', 'intro.dashboard', 'intro.transactions_nav', 'intro.brokers_nav', 'intro.fx_nav', 'intro.assets_nav', 'intro.tools_nav', 'intro.settings_nav'],
    },
    {flow: 'transactions_page_guide', steps: ['transactions.page.overview', 'transactions.page.add', 'transactions.page.import', 'transactions.page.columns']},
    {flow: 'transaction_create_guide', steps: ['transaction.create.basics', 'transaction.create.amounts', 'transaction.create.details', 'transaction.create.save']},
    {flow: 'transaction_bulk_guide', steps: ['transaction.bulk.workspace', 'transaction.bulk.validation', 'transaction.bulk.selection', 'transaction.bulk.save']},
    {flow: 'import_guide', steps: ['import.upload', 'import.select', 'import.analyze', 'import.assets', 'import.fix', 'import.duplicates', 'import.review', 'import.bulk']},
    {flow: 'broker_page_guide', steps: ['broker.page.overview', 'broker.page.currency', 'broker.page.views', 'broker.page.add']},
    {flow: 'broker_guide', steps: ['broker.overview', 'broker.plugin', 'broker.icon']},
    {flow: 'broker_detail_guide', steps: ['broker.detail.header', 'broker.detail.overview', 'broker.detail.positions', 'broker.detail.transactions', 'broker.detail.info']},
    {flow: 'fx_page_guide', steps: ['fx.page.overview', 'fx.page.filters', 'fx.page.sync', 'fx.page.add']},
    {flow: 'fx_guide', steps: ['fx.currencies', 'fx.providers']},
    {flow: 'fx_detail_guide', steps: ['fx.detail.header', 'fx.detail.provider', 'fx.detail.chart', 'fx.detail.editor']},
    {flow: 'asset_page_guide', steps: ['asset.page.overview', 'asset.page.filters', 'asset.page.sync', 'asset.page.add']},
    {flow: 'asset_guide', steps: ['asset.search', 'asset.identity', 'asset.provider']},
    {flow: 'asset_detail_guide', steps: ['asset.detail.header', 'asset.detail.chart', 'asset.detail.editor', 'asset.detail.metadata', 'asset.detail.risk']},
] as const;
const TERMINAL_ONBOARDING_PROGRESS = {
    flows: TERMINAL_ONBOARDING_FLOW_STEPS.map(({flow, steps}) => ({
        flow,
        status: 'completed',
        version: 1,
        current_version: 1,
        update_available: false,
        created_at: TERMINAL_ONBOARDING_AT,
        updated_at: TERMINAL_ONBOARDING_AT,
        completed_at: TERMINAL_ONBOARDING_AT,
        ...(steps.length > 0
            ? {
                  steps: steps.map((stepId) => ({
                      step_id: stepId,
                      status: 'completed',
                      version: 1,
                      current_version: 1,
                      update_available: false,
                      created_at: TERMINAL_ONBOARDING_AT,
                      updated_at: TERMINAL_ONBOARDING_AT,
                      completed_at: TERMINAL_ONBOARDING_AT,
                  })),
              }
            : {}),
    })),
} as const;

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CommitResult = {operation: string; index?: number; ids?: number[]; status?: string};
type CommitBody = {committed: boolean; issues?: unknown[]; results?: CommitResult[]};

type Owned = {
    suffix: string;
    brokerIds: number[];
    /** POSTs to the commit endpoint sent by the page itself (API setup does not go through the page). */
    browserCommits: number;
};
type Brokers = {a: number; b: number};
/** A row the test owns: the label names it in every verdict, the id finds it. */
type Tracked = {label: string; id: number; description: string};
type NewRow = {label: string; broker: number; type: 'DEPOSIT' | 'WITHDRAWAL'; date: string; amount: string; description: string};
/** Both selections at one instant: the toolbar's count (or `absent`) and each owned row's checkbox. */
type SelectionSnapshot = {toolbar: string; checkboxes: Record<string, string>};

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

/** The ids a committed batch reports for one operation, successful items only. */
function succeeded(body: CommitBody, operation: string): number[] {
    return (body.results ?? []).filter((result) => result.operation === operation && result.status === 'success').flatMap((result) => result.ids ?? []);
}

/** Installed before login, so the app's very first onboarding read already sees a terminal state. */
async function installTerminalOnboardingProgress(page: Page): Promise<void> {
    await page.route(
        (url) => url.pathname === `${API}/settings/onboarding` && url.search === '',
        async (route) => {
            if (route.request().method() !== 'GET') {
                await route.continue();
                return;
            }
            await route.fulfill({status: 200, contentType: 'application/json', json: TERMINAL_ONBOARDING_PROGRESS});
        },
    );
}

/** Two owned brokers; every id is recorded for cleanup before anything can fail. */
async function createOwnedBrokers(page: Page, owned: Owned): Promise<Brokers> {
    const names = [`SEL A ${owned.suffix}`, `SEL B ${owned.suffix}`];
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: names.map((name) => ({name, opened_at: '2020-01-01'}))}), 'create owned brokers');
    for (const item of created.results) {
        if (item.success && typeof item.broker_id === 'number' && names.includes(item.name)) owned.brokerIds.push(item.broker_id);
    }
    const ids = names.map((name) => created.results.find((item) => item.name === name && item.success)?.broker_id);
    if (typeof ids[0] !== 'number' || typeof ids[1] !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    return {a: ids[0], b: ids[1]};
}

/** Commit owned rows in one batch; returns them in the order given, each with its id. */
async function commitOwnedRows(page: Page, rows: NewRow[]): Promise<Tracked[]> {
    const body = await jsonFrom<CommitBody>(
        await page.request.post(COMMIT_PATH, {
            data: {creates: rows.map((row) => ({broker_id: row.broker, type: row.type, date: row.date, cash: {code: 'EUR', amount: row.amount}, description: row.description}))},
        }),
        'commit owned rows',
    );
    expect(body.committed, `owned rows rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return rows.map((row, index) => {
        const id = body.results?.find((result) => result.operation === 'create' && result.index === index && result.status === 'success')?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`Owned row "${row.label}" got no id: ${JSON.stringify(body.results)}`);
        return {label: row.label, id, description: row.description};
    });
}

/** Three standalone DEPOSITs on broker A: two to act on, one to select afterwards. */
async function ownDeposits(page: Page, owned: Owned): Promise<{brokers: Brokers; d1: Tracked; d2: Tracked; d3: Tracked}> {
    const brokers = await createOwnedBrokers(page, owned);
    const deposit = (label: string, amount: string): NewRow => ({label, broker: brokers.a, type: 'DEPOSIT', date: FUND_DATE, amount, description: `SEL ${label} ${owned.suffix}`});
    const [d1, d2, d3] = await commitOwnedRows(page, [deposit('d1', '100'), deposit('d2', '110'), deposit('d3', '120')]);
    return {brokers, d1, d2, d3};
}

/**
 * For the clone: a DEPOSIT and a WITHDRAWAL on broker A, plus a DEPOSIT to select afterwards.
 * Two different types on purpose: the bulk editor gives two same-type clones one shared
 * `link_uuid` and shows them as a single pair row (`TransactionBulkModal.resolveInitialRows`),
 * which is not the subject here.
 */
async function ownCloneRows(page: Page, owned: Owned): Promise<{brokers: Brokers; d1: Tracked; w2: Tracked; d3: Tracked}> {
    const brokers = await createOwnedBrokers(page, owned);
    const [d1, w2, d3] = await commitOwnedRows(page, [
        {label: 'd1', broker: brokers.a, type: 'DEPOSIT', date: FUND_DATE, amount: '100', description: `SEL d1 ${owned.suffix}`},
        {label: 'w2', broker: brokers.a, type: 'WITHDRAWAL', date: PAIR_DATE, amount: '-10', description: `SEL w2 ${owned.suffix}`},
        {label: 'd3', broker: brokers.a, type: 'DEPOSIT', date: FUND_DATE, amount: '120', description: `SEL d3 ${owned.suffix}`},
    ]);
    return {brokers, d1, w2, d3};
}

/**
 * A compatible cash transfer: a WITHDRAWAL on broker A and a DEPOSIT on broker B, same date,
 * amount and currency, same description and no tags — so "Link as pair" goes straight to its
 * plain confirm, never to the merge modal. A funding DEPOSIT on A comes first: the backend
 * refuses a batch that takes a broker's cash below zero.
 */
function transferRows(brokers: Brokers, suffix: string): NewRow[] {
    const transfer = `SEL transfer ${suffix}`;
    return [
        {label: 'fund', broker: brokers.a, type: 'DEPOSIT', date: FUND_DATE, amount: '500', description: `SEL fund ${suffix}`},
        {label: 'withdrawal', broker: brokers.a, type: 'WITHDRAWAL', date: PAIR_DATE, amount: '-100', description: transfer},
        {label: 'deposit', broker: brokers.b, type: 'DEPOSIT', date: PAIR_DATE, amount: '100', description: transfer},
    ];
}

async function ownUnlinkedTransfer(page: Page, owned: Owned): Promise<{brokers: Brokers; fund: Tracked; withdrawal: Tracked; deposit: Tracked}> {
    const brokers = await createOwnedBrokers(page, owned);
    const [fund, withdrawal, deposit] = await commitOwnedRows(page, transferRows(brokers, owned.suffix));
    return {brokers, fund, withdrawal, deposit};
}

/** The same transfer already linked by the backend's own promote, plus one more standalone row on B. */
async function ownLinkedTransfer(page: Page, owned: Owned): Promise<{brokers: Brokers; fund: Tracked; withdrawal: Tracked; deposit: Tracked; other: Tracked}> {
    const brokers = await createOwnedBrokers(page, owned);
    const [fund, withdrawal, deposit, other] = await commitOwnedRows(page, [...transferRows(brokers, owned.suffix), {label: 'other', broker: brokers.b, type: 'DEPOSIT', date: '2024-01-04', amount: '50', description: `SEL other ${owned.suffix}`}]);
    const linked = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {promotes: [{id_a: withdrawal.id, id_b: deposit.id}]}}), 'link the owned transfer');
    expect(linked.committed, `owned transfer not linked: ${JSON.stringify(linked.issues ?? [])}`).toBe(true);
    expect(succeeded(linked, 'promote'), 'the owned transfer is now a linked pair').toEqual(expect.arrayContaining([withdrawal.id, deposit.id]));
    return {brokers, fund, withdrawal, deposit, other};
}

/** Delete every row on the owned brokers (UI-made clones and adds included), then the brokers. */
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
    const transactionIds: number[] = [];
    for (const brokerId of owned.brokerIds) {
        await attempt(`list the rows of broker ${brokerId}`, async () => {
            const rows = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/transactions`, {params: {broker_id: brokerId}}), `list the rows of owned broker ${brokerId}`);
            transactionIds.push(...rows.map((row) => row.id));
        });
    }
    if (transactionIds.length > 0) {
        // One batch: both halves of a linked pair go together.
        await attempt(`transactions ${transactionIds.join(', ')}`, async () => {
            const result = await jsonFrom<CommitBody>(await page.request.post(COMMIT_PATH, {data: {creates: [], updates: [], deletes: transactionIds}}), 'delete owned rows');
            expect(result.committed, JSON.stringify(result.issues ?? [])).toBe(true);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`Selection checks write owned rows and may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `s${testInfo.workerIndex}-${uniqueSuffix()}`, brokerIds: [], browserCommits: 0};
        page.on('request', (request) => {
            if (isCommitRequest(request)) owned.browserCommits += 1;
        });
        try {
            await installTerminalOnboardingProgress(page);
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(90_000);

// ---------------------------------------------------------------------------
// The page and its two selections
// ---------------------------------------------------------------------------

function transactionsPage(page: Page): Locator {
    return page.getByTestId('transactions-page');
}

function tableRow(page: Page, id: number): Locator {
    return transactionsPage(page).getByTestId('tx-table').locator(`tr[data-row-id="tx-${id}"]`);
}

function rowCheckbox(page: Page, id: number): Locator {
    return transactionsPage(page).getByTestId('tx-table').getByTestId(`dt-row-checkbox-tx-${id}`);
}

const snapshotKey = (row: Tracked) => `${row.label} tx-${row.id}`;

/** Read both selections in one go. One-shot by nature: every caller polls it. */
async function readSelection(page: Page, rows: Tracked[]): Promise<SelectionSnapshot> {
    const probes = rows.map((row) => ({key: snapshotKey(row), id: row.id}));
    return page.evaluate((list) => {
        const root = document.querySelector('[data-testid="transactions-page"]');
        const toolbar = root?.querySelector('[data-testid="selection-toolbar"]') ?? null;
        const table = root?.querySelector('[data-testid="tx-table"]') ?? null;
        const checkboxes: Record<string, string> = {};
        for (const probe of list) {
            checkboxes[probe.key] = table?.querySelector(`[data-testid="dt-row-checkbox-tx-${probe.id}"]`)?.getAttribute('data-state') ?? 'missing';
        }
        return {toolbar: toolbar ? (toolbar.getAttribute('data-selected-count') ?? 'no-count') : 'absent', checkboxes};
    }, probes);
}

/** The snapshot a verdict expects: the toolbar as given, `checked` rows checked, `missing` rows gone, the rest unchecked. */
function expectedSelection(toolbar: string, rows: Tracked[], checked: Tracked[] = [], missing: Tracked[] = []): SelectionSnapshot {
    const state = (row: Tracked) => (missing.some((gone) => gone.id === row.id) ? 'missing' : checked.some((on) => on.id === row.id) ? 'checked' : 'unchecked');
    return {toolbar, checkboxes: Object.fromEntries(rows.map((row) => [snapshotKey(row), state(row)]))};
}

/** Open the page on the two owned brokers only; ends with every owned row on screen and nothing selected. */
async function openOwnedTransactions(page: Page, brokers: Brokers, rows: Tracked[]): Promise<void> {
    // The page's own canonical form of the filter (comma encoded): it finds nothing to rewrite in the URL.
    await navigateTo(page, `/transactions?${new URLSearchParams({broker_ids: `${brokers.a},${brokers.b}`})}`);
    await expect(transactionsPage(page)).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage(page), 20_000);
    for (const row of rows) await expect(tableRow(page, row.id), `${row.label} is on screen`).toBeVisible({timeout: UI_TIMEOUT});
    await expect.poll(() => readSelection(page, rows), {message: 'precondition: nothing is selected on arrival', timeout: UI_TIMEOUT}).toEqual(expectedSelection('absent', rows));
}

/** Tick the rows one by one; ends with both selections holding exactly them. */
async function selectRows(page: Page, rows: Tracked[], toSelect: Tracked[]): Promise<void> {
    for (const row of toSelect) {
        const checkbox = rowCheckbox(page, row.id);
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }
    await expect.poll(() => readSelection(page, rows), {message: 'precondition: toolbar and checkboxes hold exactly the rows this test ticked', timeout: UI_TIMEOUT}).toEqual(expectedSelection(String(toSelect.length), rows, toSelect));
}

/**
 * Executed: nothing is selected any more — no toolbar, no checkbox checked — and the next
 * click selects exactly the row clicked. `fresh` is a row that was never selected, so the
 * second verdict also catches a table that silently kept the old ticks.
 */
async function expectSelectionCleared(page: Page, operation: string, rows: Tracked[], fresh: Tracked, gone: Tracked[] = []): Promise<void> {
    await expect.soft.poll(() => readSelection(page, rows), {message: `${operation} executed → the selection is empty: no toolbar, no checkbox checked`, timeout: VERDICT_TIMEOUT}).toEqual(expectedSelection('absent', rows, [], gone));
    await rowCheckbox(page, fresh.id).click();
    await expect.soft.poll(() => readSelection(page, rows), {message: `${operation} executed → a new single selection (${fresh.label}) counts 1`, timeout: VERDICT_TIMEOUT}).toEqual(expectedSelection('1', rows, [fresh], gone));
}

/** Cancelled: the selection is exactly what it was, and the next click adds to it. */
async function expectSelectionKept(page: Page, operation: string, rows: Tracked[], selected: Tracked[], fresh: Tracked): Promise<void> {
    await expect.soft.poll(() => readSelection(page, rows), {message: `${operation} cancelled → the selection is unchanged`, timeout: VERDICT_TIMEOUT}).toEqual(expectedSelection(String(selected.length), rows, selected));
    await rowCheckbox(page, fresh.id).click();
    await expect.soft.poll(() => readSelection(page, rows), {message: `${operation} cancelled → one more click (${fresh.label}) adds to the kept selection`, timeout: VERDICT_TIMEOUT}).toEqual(expectedSelection(String(selected.length + 1), rows, [...selected, fresh]));
}

// ---------------------------------------------------------------------------
// The operations
// ---------------------------------------------------------------------------

async function clickToolbarAction(page: Page, action: 'edit' | 'clone' | 'delete' | 'promote'): Promise<void> {
    const button = transactionsPage(page).getByTestId('selection-toolbar').getByTestId(`toolbar-action-${action}`);
    await expect(button).toBeVisible({timeout: UI_TIMEOUT});
    await button.click();
}

function bulkRows(page: Page): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
}

/** Open the bulk editor from a toolbar action; ends with every expected row in its grid. */
async function openBulkEditor(page: Page, action: 'edit' | 'clone' | 'delete', descriptions: string[]): Promise<void> {
    await clickToolbarAction(page, action);
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    for (const description of descriptions) await expect(bulkRows(page).filter({hasText: description})).toHaveCount(1, {timeout: UI_TIMEOUT});
}

async function selectType(page: Page, typeCode: string): Promise<void> {
    await page.getByTestId('tx-form-type').click();
    const option = page.getByTestId(`search-select-option-${typeCode}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

async function pickBroker(page: Page, brokerId: number): Promise<void> {
    const trigger = page.getByTestId('tx-form-broker-wrap').getByRole('combobox');
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
}

async function fillCash(page: Page, amount: string): Promise<void> {
    const input = page.getByTestId('tx-form-cash-amount');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(amount);
    await input.blur();
    await expect(input).not.toHaveValue('');
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

/** Push the form's draft back to the bulk grid. */
async function applyFormModal(page: Page): Promise<void> {
    const save = page.getByTestId('tx-form-save');
    await expect(save).toBeEnabled({timeout: UI_TIMEOUT});
    await save.click();
    await expect(page.getByTestId('tx-form-modal')).toBeHidden({timeout: UI_TIMEOUT});
}

/** Change one grid row's description through its form; ends with the grid showing the new text. */
async function editDescriptionInGrid(page: Page, from: string, to: string): Promise<void> {
    const row = bulkRows(page).filter({hasText: from});
    await expect(row).toHaveCount(1);
    await row.dblclick();
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await fillDescription(page, to);
    await applyFormModal(page);
    await expect(bulkRows(page).filter({hasText: to})).toHaveCount(1, {timeout: UI_TIMEOUT});
}

/** Add button → the editor opens with an empty form → one DEPOSIT pushed to its grid. */
async function addDepositThroughForm(page: Page, brokerId: number, amount: string, description: string): Promise<void> {
    await transactionsPage(page).getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-bulk-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('tx-form-modal')).toBeVisible({timeout: UI_TIMEOUT});
    await selectType(page, 'DEPOSIT');
    await pickBroker(page, brokerId);
    await fillCash(page, amount);
    await fillDescription(page, description);
    await applyFormModal(page);
    await expect(bulkRows(page).filter({hasText: description})).toHaveCount(1, {timeout: UI_TIMEOUT});
}

/** Save All; ends with the batch committed and the editor closed. */
async function saveAll(page: Page): Promise<CommitBody> {
    const commit = page.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: UI_TIMEOUT});
    const [response] = await Promise.all([page.waitForResponse((candidate) => isCommitRequest(candidate.request()), {timeout: 20_000}), commit.click()]);
    const body = await jsonFrom<CommitBody>(response, 'Save All');
    expect(body.committed, `Save All rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: UI_TIMEOUT});
    return body;
}

/** Toolbar "Link as pair" on a pair with identical fields: the plain confirm opens, not the merge modal. */
async function openLinkConfirm(page: Page): Promise<void> {
    await clickToolbarAction(page, 'promote');
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('promote-merge-modal')).toHaveCount(0);
}

/** A linked row's own menu → "split": ends with the unlink confirm on screen. */
async function openUnlinkConfirm(page: Page, row: Tracked): Promise<Locator> {
    await transactionsPage(page).getByTestId(`row-actions-tx-${row.id}`).click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    await menu.getByTestId('context-menu-action-split').click();
    const modal = page.getByTestId('tx-action-modal');
    await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
    return modal;
}

/** Click a confirm that commits; ends with the committed answer in hand. */
async function confirmAndCommit(page: Page, confirm: Locator, purpose: string): Promise<CommitBody> {
    const [response] = await Promise.all([page.waitForResponse((candidate) => isCommitRequest(candidate.request()), {timeout: 20_000}), confirm.click()]);
    const body = await jsonFrom<CommitBody>(response, purpose);
    expect(body.committed, `${purpose} rolled back: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return body;
}

const byId = (a: number, b: number) => a - b;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Transactions selection — after an executed operation the selection is empty', () => {
    test('E1 edit: after a bulk edit is saved nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, d1, d2, d3} = await ownDeposits(page, owned);
        const rows = [d1, d2, d3];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [d1, d2]);

        await openBulkEditor(page, 'edit', [d1.description, d2.description]);
        const edited = `SEL d1 edited ${owned.suffix}`;
        await editDescriptionInGrid(page, d1.description, edited);
        const body = await saveAll(page);
        expect(succeeded(body, 'update'), 'the edit reached the ledger').toContain(d1.id);
        // Barrier: the reloaded table shows the saved edit.
        await expect(transactionsPage(page).getByTestId(`tx-desc-${d1.id}`)).toHaveText(edited, {timeout: UI_TIMEOUT});

        await expectSelectionCleared(page, 'bulk edit', rows, d3);
    });

    test('E2 clone: after the clones are saved nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, d1, w2, d3} = await ownCloneRows(page, owned);
        const rows = [d1, w2, d3];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [d1, w2]);

        await openBulkEditor(page, 'clone', [d1.description, w2.description]);
        const body = await saveAll(page);
        const cloneIds = succeeded(body, 'create');
        expect(cloneIds, 'the clone commit created exactly the two clones').toHaveLength(2);
        const clones = cloneIds.map((id, index) => ({label: `clone${index + 1}`, id, description: ''}));
        // Barrier: the reloaded table shows both clones.
        for (const clone of clones) await expect(tableRow(page, clone.id), `${clone.label} is on screen`).toBeVisible({timeout: UI_TIMEOUT});

        await expectSelectionCleared(page, 'clone', [...rows, ...clones], d3);
    });

    test('E3 delete: after a bulk delete is saved nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, d1, d2, d3} = await ownDeposits(page, owned);
        const rows = [d1, d2, d3];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [d1, d2]);

        await openBulkEditor(page, 'delete', [d1.description, d2.description]);
        const body = await saveAll(page);
        expect([...succeeded(body, 'delete')].sort(byId), 'the delete reached the ledger').toEqual([d1.id, d2.id].sort(byId));
        // Barrier: the reloaded table has lost both rows and kept the survivor.
        await expect(tableRow(page, d3.id)).toBeVisible();
        await expect(tableRow(page, d1.id)).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(tableRow(page, d2.id)).toHaveCount(0);

        await expectSelectionCleared(page, 'bulk delete', rows, d3, [d1, d2]);
    });

    test('E4 add: after a new transaction is saved nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, d1, d2, d3} = await ownDeposits(page, owned);
        await openOwnedTransactions(page, brokers, [d1, d2, d3]);
        await selectRows(page, [d1, d2, d3], [d1]);

        const description = `SEL added ${owned.suffix}`;
        await addDepositThroughForm(page, brokers.a, '25', description);
        const body = await saveAll(page);
        const createdIds = succeeded(body, 'create');
        expect(createdIds, 'the add created exactly one row').toHaveLength(1);
        const added: Tracked = {label: 'added', id: createdIds[0], description};
        // Barrier: the reloaded table shows the new row.
        await expect(transactionsPage(page).getByTestId(`tx-desc-${added.id}`)).toHaveText(description, {timeout: UI_TIMEOUT});

        await expectSelectionCleared(page, 'add', [d1, d2, d3, added], d3);
    });

    test('E5 link: after the selected pair is linked nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, fund, withdrawal, deposit} = await ownUnlinkedTransfer(page, owned);
        const rows = [withdrawal, deposit, fund];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [withdrawal, deposit]);

        await openLinkConfirm(page);
        const body = await confirmAndCommit(page, page.getByTestId('confirm-modal-confirm'), 'link as pair');
        expect(succeeded(body, 'promote'), 'the link reached the ledger').toEqual(expect.arrayContaining([withdrawal.id, deposit.id]));
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0, {timeout: UI_TIMEOUT});
        // Barrier: the reloaded table shows the link.
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`)).toBeVisible({timeout: UI_TIMEOUT});

        await expectSelectionCleared(page, 'link as pair', rows, fund);
    });

    test('E6 unlink: after a pair is unlinked nothing is selected and one click selects one row', async ({page, owned}) => {
        const {brokers, fund, withdrawal, deposit, other} = await ownLinkedTransfer(page, owned);
        const rows = [withdrawal, deposit, other, fund];
        await openOwnedTransactions(page, brokers, rows);
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`), 'precondition: the owned transfer shows as linked').toBeVisible({timeout: UI_TIMEOUT});
        await selectRows(page, rows, [withdrawal, other]);

        const modal = await openUnlinkConfirm(page, withdrawal);
        const body = await confirmAndCommit(page, modal.getByTestId('tx-action-modal-confirm'), 'unlink');
        expect(succeeded(body, 'split'), 'the unlink reached the ledger').toEqual(expect.arrayContaining([withdrawal.id, deposit.id]));
        await expect(modal).toBeHidden({timeout: UI_TIMEOUT});
        // Barrier: the reloaded table still has the row and no longer its link.
        await expect(tableRow(page, withdrawal.id)).toBeVisible();
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`)).toHaveCount(0, {timeout: UI_TIMEOUT});

        await expectSelectionCleared(page, 'unlink', rows, fund);
    });
});

test.describe('Transactions selection — after a cancelled operation the selection is kept', () => {
    test('C1 edit closed untouched: the selection is unchanged and one click adds to it', async ({page, owned}) => {
        const {brokers, d1, d2, d3} = await ownDeposits(page, owned);
        const rows = [d1, d2, d3];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [d1, d2]);
        const commitsBefore = owned.browserCommits;

        await openBulkEditor(page, 'edit', [d1.description, d2.description]);
        // Settled first, so the close guard judges the rows against the opening snapshot and nothing else.
        await waitForSettled(page.getByTestId('tx-bulk-modal-root'));
        await page.getByTestId('tx-bulk-close').click();
        await expect(page.getByTestId('tx-bulk-modal'), 'an untouched editor closes on the first click').toBeHidden({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0);

        await expectSelectionKept(page, 'closing the untouched editor', rows, [d1, d2], d3);
        expect(owned.browserCommits - commitsBefore, 'closing the editor committed nothing').toBe(0);
    });

    test('C2 edit discarded: the selection is unchanged and one click adds to it', async ({page, owned}) => {
        const {brokers, d1, d2, d3} = await ownDeposits(page, owned);
        const rows = [d1, d2, d3];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [d1, d2]);
        const commitsBefore = owned.browserCommits;

        await openBulkEditor(page, 'edit', [d1.description, d2.description]);
        await editDescriptionInGrid(page, d1.description, `SEL d1 discarded ${owned.suffix}`);
        await page.getByTestId('tx-bulk-cancel').click();
        const discard = page.getByTestId('confirm-modal-confirm');
        await expect(discard, 'a changed editor asks before discarding').toBeVisible({timeout: UI_TIMEOUT});
        await discard.click();
        await expect(page.getByTestId('tx-bulk-modal')).toBeHidden({timeout: UI_TIMEOUT});
        await expect(discard).toHaveCount(0);
        await expect(transactionsPage(page).getByTestId(`tx-desc-${d1.id}`), 'the discarded edit never reached the table').toHaveText(d1.description);

        await expectSelectionKept(page, 'discarding the changed editor', rows, [d1, d2], d3);
        expect(owned.browserCommits - commitsBefore, 'discarding the editor committed nothing').toBe(0);
    });

    test('C3 link cancelled: the selection is unchanged and one click adds to it', async ({page, owned}) => {
        const {brokers, fund, withdrawal, deposit} = await ownUnlinkedTransfer(page, owned);
        const rows = [withdrawal, deposit, fund];
        await openOwnedTransactions(page, brokers, rows);
        await selectRows(page, rows, [withdrawal, deposit]);
        const commitsBefore = owned.browserCommits;

        await openLinkConfirm(page);
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(tableRow(page, withdrawal.id)).toBeVisible();
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`), 'the cancelled link was not made').toHaveCount(0);

        await expectSelectionKept(page, 'cancelling link as pair', rows, [withdrawal, deposit], fund);
        expect(owned.browserCommits - commitsBefore, 'cancelling the link committed nothing').toBe(0);
    });

    test('C4 unlink cancelled: the selection is unchanged and one click adds to it', async ({page, owned}) => {
        const {brokers, fund, withdrawal, deposit, other} = await ownLinkedTransfer(page, owned);
        const rows = [withdrawal, deposit, other, fund];
        await openOwnedTransactions(page, brokers, rows);
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`), 'precondition: the owned transfer shows as linked').toBeVisible({timeout: UI_TIMEOUT});
        await selectRows(page, rows, [withdrawal, other]);
        const commitsBefore = owned.browserCommits;

        const modal = await openUnlinkConfirm(page, withdrawal);
        await modal.getByTestId('tx-action-modal-cancel').click();
        await expect(modal).toBeHidden({timeout: UI_TIMEOUT});
        await expect(transactionsPage(page).getByTestId(`tx-link-icon-${withdrawal.id}`), 'the cancelled unlink left the pair linked').toBeVisible();

        await expectSelectionKept(page, 'cancelling the unlink', rows, [withdrawal, other], fund);
        expect(owned.browserCommits - commitsBefore, 'cancelling the unlink committed nothing').toBe(0);
    });
});
