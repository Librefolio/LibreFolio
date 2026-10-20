/**
 * J-57 complete (workstream J «Numeri e analisi», LibreFolio 1.3): an Auto cost basis with nothing to average is
 * refused, a cost written by hand — 0 included — is not, and the editor leads the user to the row it refused.
 *
 * The developer's decisions (19/10) these tests pin:
 *
 *   1. J-57 / N88, in the code since 17/10: an Auto cost whose pool holds no units on its date is refused with
 *      `autoCostEmptyPool` (units of unknown cost only: `autoCostUnknownPool`). A cost written by hand stays allowed,
 *      0 included — a gift.
 *   2. Q-J57-1 (c): a BLOCKING import todo on `cost_basis_override` is answered only by a value (Manual with an
 *      amount, 0 included); Auto no longer answers it. A row handed from the import to the editor with such a todo
 *      starts in Manual with the field empty when its type allows a cost, so its form opens in Manual, empty.
 *   3. Q-J57-4: after an EXPLICIT validation — the import hand-over (it runs one validation itself), ⚡ «Validate now»
 *      (`tx-bulk-validate-now`, `scheduler.trigger('manual')`), or a refused Save — the editor pages the grid to the
 *      first row refused for an Auto cost (`autoCostEmptyPool`, `autoCostUnknownPool`, and since Q-J57-6
 *      `autoCostUnreadable`), the oldest by date, as a click on its issue does (`tableRef.navigateToRowId`: the row
 *      `tr[data-row-id=<tempId>]` is on screen with `data-highlighted="true"`). Not after the background validation.
 *   4. The form's issues carry their code: `[data-testid="tx-form-issue"][data-code=<code>]` (`TxFormBanners.svelte`).
 *      The editor's `tx-bulk-issue` already carries `data-code` and `data-row-label`.
 *   5. Q-J57-5 (a), the developer's words: «se il plugin non è in grado di mettere un numero esplicito, allora deve
 *      andare in auto, se poi quel numero esplicito è 0, va bene, ma lasciarlo non selezionato direi che è un bug». At
 *      the hand-over (`onImportBatch`, through `initialCostBasisMode` in `bulk/bulkTodos.ts`) a row whose type takes a
 *      cost and that the plugin leaves without a mode starts in Auto; a cost the plugin wrote, 0 included, or a blocking
 *      cost todo starts it in Manual; the plugin's own mode stays. So the hand-over's validation costs a crypto Receive
 *      at the average, or refuses it when there is nothing to average, and leads to it (3).
 *
 * The tests. RED = fails on the code before the J-57 cure (19/10) and passes with it; CONTROL = green on both.
 *
 *   E1    RED (decision 4) — the single form, inside the editor: an ADJUSTMENT +5 of an asset the broker never held,
 *         cost in Auto. The server refuses it `autoCostEmptyPool` (on the wire: CONTROL, N88) and the form lists one
 *         issue, which carried no `data-code` before the cure. «Save» (the form's Apply, then the editor's Save all)
 *         is refused and writes nothing; the row's form in Manual with 0 saves it, and the API reads a cost of 0.
 *   E2    RED on two counts (decisions 5 and 3) — a CoinTracking report whose crypto «Deposit» (the plugin writes it
 *         ADJUSTMENT +q, no cost, no mode, no todo) comes before any purchase, past the grid's first page. The mode:
 *         the hand-over starts the Receive in Auto, so its validation refuses it `autoCostEmptyPool` and the issue names
 *         its row. The jump: the grid is on that row, highlighted, without any click. Its form in Manual with 0 saves
 *         the whole import; the API reads a cost of 0.
 *   E2-⚡ RED (decisions 5 and 3) — two such Receives, in Auto from the hand-over, both refused (the cascade): a
 *         background validation leaves the grid on page 1 (a guard, green before the cure too); ⚡ from page 1 pages the
 *         grid to the OLDER Receive, highlighted (the report lists the newer one first: the batch's order is not the
 *         dates' order); a refused Save from page 1 does the same. Nothing is saved.
 *   E3    CONTROL (N88) — the cascade: two Receives before any purchase, both in Auto, are both refused; Manual 0 on
 *         the earlier one only lets the later one pass in Auto; both are saved, both at a cost of 0 (free units keep
 *         their 0). It reaches Auto through the rows' forms, so it holds whatever the hand-over did.
 *   E4    RED (decision 2, kept by decision 5) — a Receive carrying a blocking `cost_basis_override` todo (injected into
 *         the parse response, as tx-bulk-import-handoff F1-D4 does): it starts in Manual, so its form opens in Manual
 *         with the field empty (before the cure: Auto). Apply with the field empty leaves the todo listed and Save held;
 *         0 answers it. Nothing is saved.
 *
 * Before the cure — and in the analysis this spec first followed — a plugin row without a cost mode kept none in the
 * editor (`txCreateItemToPendingOp` copies the plugin's): an imported ADJUSTMENT +q reached the hand-over's validation
 * without Auto and was refused `costBasisRequired`, and only its form fell back to Auto (`TransactionFormModal.svelte`:
 * a row without a mode opens in Auto). The developer called that state a bug (decision 5). E2 and E2-⚡ rest on the new
 * rule: their Receives start in Auto at the hand-over. E3 does not: it puts its Receives in Auto through their own forms,
 * which works before the cure and with it. `autoCostUnreadable` (Q-J57-6) needs a stored value that is no number, which
 * the API cannot write: the unit tests of `firstAutoCostRefusalRowId` (`bulkDisplay.test.ts`) cover it, not this spec.
 *
 * Reading a verdict. Up to 50 rows the editor validates by itself after a change, so a hand-over may be followed by a
 * background run: the tests read the issues once the editor has settled, which is the last run's verdict. A background
 * run never moves the grid, so after a hand-over only the hand-over's own validation can have led to a row.
 *
 * Data. Every test registers its own account (fixtures/onboarding-accounts.ts, onboarding skipped over the API), which
 * owns everything it sees: one broker (opened 2020-01-01; for the imports, default plugin `broker_cointracking`) and
 * one asset (EUR; for the imports a CRYPTO asset whose ticker is the report's symbol, a unique `J57…` token, so the
 * wizard's candidate search finds it alone and resolves it — read back from the parse's `asset_mappings`). The reports
 * are synthetic CoinTracking exports written here — the sample `cointracking-export.csv` would bring trades, staking,
 * a withdrawal and fees, on a BTC matched against whatever the lane holds: not this test's to control — uploaded over
 * the API under a unique name; invented dates in 2024, invented amounts. Fiat «Deposit» rows
 * (DEPOSIT EUR) put the Receives past the editor's first page and fund the purchase. Rows are found by their ISO date
 * (`tx-bulk-date[data-date]`, every row of a report has its own) or by a unique description — data, never a
 * translation.
 *
 * Waits are states: `data-busy` (`waitForSettled`), the editor's `data-validate-runs` sampled before the action that
 * validates, the commit and validate answers armed before the click, the pagination's own input value.
 *
 * Cleanup (fixture, whatever the outcome): leave the page, delete the uploaded files, the broker (force: its rows go
 * with it), the asset, then the account. Nothing global is read or written: the tests run beside anything.
 *
 * Key data-testids: tx-add-button · tx-import-button · tx-bulk-modal / tx-bulk-modal-root [data-busy]
 * [data-validate-runs] · tx-bulk-body · tbody tr[data-row-id][data-highlighted] · tx-bulk-date[data-date] ·
 * tx-bulk-row-label · row-actions-<rowId> · context-menu-action-edit-single / -clone · data-table-pagination ·
 * tx-bulk-issue[data-code][data-row-label] · tx-bulk-error · tx-bulk-valid · tx-bulk-validate-now · tx-bulk-commit ·
 * tx-bulk-close · confirm-modal-confirm · tx-bulk-todo-blockers / -toggle · tx-bulk-todo-goto[data-row-id] ·
 * tx-bulk-cost-basis-auto[data-state] · tx-form-modal / tx-form-modal-root · tx-form-type · tx-form-broker-wrap ·
 * tx-form-asset(-trigger/-search) · tx-form-quantity · tx-form-optional-toggle · tx-form-description ·
 * tx-form-cost-basis-toggle(-auto/-manual)[aria-pressed] · tx-form-cost-basis-input-amount / -currency ·
 * tx-form-cost-basis-warning · tx-form-issue[data-code] · tx-form-save · import-wizard-* (fixtures/import-wizard.ts).
 *
 * Plan: `LibreFolio_developer_journal/Release_2/Phase_1/05_numbersAnalysis/plan-phase01NumbersAnalysis.prompt.md`,
 * «Analisi di J-57 completa» (§6, E1–E3), «J-57 completa — piano breve del lotto», «J-57 completo — esecuzione» and
 * the decisions on Q-J57-5 and Q-J57-6 (19/10 ~17:45).
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {validateRuns, waitForSettled, waitForValidateRun} from '../fixtures/app-events';
import {navigateTo} from '../fixtures/auth-helpers';
import {continueToReview, parseSelectedFile, selectBrokerFile} from '../fixtures/import-wizard';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const VALIDATE_PATH = `${API}/transactions/validate`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const PARSE_PATH = /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/;
const COINTRACKING = 'broker_cointracking';
/** N88: an Auto cost whose pool holds no units on its date. */
const EMPTY_POOL = 'autoCostEmptyPool';
const UI_TIMEOUT = 15_000;
const STEP_TIMEOUT = 30_000;
/** Before every date of the reports: no row is held back as dated before the broker's opening. */
const BROKER_OPENED_AT = '2020-01-01';
/** Mirror of the editor grid's `defaultPageSize` (TransactionBulkModal.svelte), in a fresh browser context. */
const EDITOR_PAGE_SIZE = 25;

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Broker = {id: number; name: string};
type Asset = {id: number; name: string};
type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]; fileIds: string[]};
type Money = {code: string; amount: string};
type BatchIssue = {operation: string; index: number; code?: string | null; field?: string | null};
type BatchAnswer = {committed?: boolean; issues?: BatchIssue[]};
type SentCreate = Record<string, unknown> & {description?: string; cost_basis_mode?: string};
type TransactionRead = {id: number; broker_id: number; type: string; date: string; quantity: string; description?: string | null; cost_basis_override?: Money | null};
type SavedAdjustment = {date: string; quantity: number; description: string | null; code: string | null; amount: number | null};
type IssueEntry = {code: string; label: string};

/** One line of a synthetic CoinTracking export. */
type CtRow = {kind: 'cash'; date: string; amount: string} | {kind: 'receive'; date: string; quantity: string} | {kind: 'buy'; date: string; quantity: string; cost: string};
type CtTransaction = {type: string; date: string; quantity: string; asset_id?: number | null; cost_basis_override?: Money | null};
type CtParse = {
    plugin_code: string;
    transactions: CtTransaction[];
    field_todos?: Array<{tx_index: number; field: string; severity: string; reason_code: string}>;
    asset_mappings?: Array<{fake_asset_id: number; selected_asset_id: number | null}>;
};
type ImportSeed = {broker: Broker; asset: Asset; symbol: string};
/** A blocking cost todo, written into the parse response on the Receive of `date`. */
type InjectedTodo = {date: string; reason_code: string; message: string};

/**
 * A wait armed before the action and awaited later. If the test fails in between, the pending wait would reject
 * unobserved when the page closes; awaiting the returned promise still throws as usual.
 */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

function isCommit(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMMIT_PATH;
}

function isValidate(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === VALIDATE_PATH;
}

function sentCreates(request: Request): SentCreate[] {
    return ((request.postDataJSON() as {creates?: SentCreate[]} | null)?.creates ?? []) as SentCreate[];
}

/** The issues of one operation of a batch answer, reduced to what the tests compare. */
function issuesOf(answer: BatchAnswer, operation: string, index: number): Array<{code: string | null; field: string | null}> {
    return (answer.issues ?? []).filter((issue) => issue.operation === operation && issue.index === index).map((issue) => ({code: issue.code ?? null, field: issue.field ?? null}));
}

function codesOf(answer: BatchAnswer): string[] {
    return (answer.issues ?? []).map((issue) => issue.code ?? '').sort();
}

/** `YYYY-MM-DD` plus `days`, on the calendar of the dates written in the reports (no clock, no time zone). */
function isoPlusDays(iso: string, days: number): string {
    return new Date(Date.parse(`${iso}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Owned data: the account, its broker, its asset, its uploads
// ---------------------------------------------------------------------------

/** A fresh account, welcomed, every guide skipped over the API: it owns everything the test will see. */
async function openDisposableAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<void> {
    const user = await registerDisposableUser(request, tag);
    owned.user = user;
    await prepareOnboardingAccount(page, user, []);
}

/** A broker of the account; its id is recorded for cleanup before anything about it is checked. */
async function createBroker(page: Page, owned: Owned, name: string, extra: Record<string, unknown> = {}): Promise<Broker> {
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: BROKER_OPENED_AT, ...extra}]}), `create the owned broker ${name}`);
    const created = body.results.find((item) => item.name === name);
    if (typeof created?.broker_id === 'number') owned.brokerIds.push(created.broker_id);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(body)}`);
    return {id: created.broker_id, name};
}

/** A manual asset in EUR; `ticker` is what the import's candidate search matches the report's symbol against. */
async function createAsset(page: Page, owned: Owned, spec: {name: string; ticker: string; assetType: 'CRYPTO' | 'ETF'}): Promise<Asset> {
    const item = {display_name: spec.name, currency: 'EUR', asset_type: spec.assetType, identifier_ticker: spec.ticker, quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const body = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [item]}), `create the owned asset ${spec.name}`);
    const created = body.results.find((result) => result.display_name === spec.name);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(body)}`);
    return {id: created.asset_id, name: spec.name};
}

async function ledgerOf(page: Page, broker: Broker): Promise<TransactionRead[]> {
    return jsonFrom<TransactionRead[]>(await page.request.get(`${API}/transactions`, {params: {broker_id: broker.id}}), `read the rows of ${broker.name}`);
}

/** The ADJUSTMENT rows of a ledger, oldest first, with their cost basis as numbers: what the decisions are about. */
function savedAdjustments(ledger: TransactionRead[]): SavedAdjustment[] {
    // `+ 0` folds a stored "-0" into 0: Object.is, which toEqual uses, tells them apart.
    return ledger
        .filter((row) => row.type === 'ADJUSTMENT')
        .map((row) => ({
            date: row.date,
            quantity: Number(row.quantity),
            description: row.description ?? null,
            code: row.cost_basis_override?.code ?? null,
            amount: row.cost_basis_override == null ? null : Number(row.cost_basis_override.amount) + 0,
        }))
        .sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Delete in dependency order, each step scoped to an id this test recorded: the page is unmounted first, so nothing
 * reloads while the rows go; the uploaded files; the brokers with `force`, which takes every row saved on them; the
 * asset; the account last, through the standalone `request` context, which signs in on its own.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    await attempt('unmount the page', async () => {
        await page.goto('about:blank');
    });
    for (const fileId of owned.fileIds) {
        await attempt(`BRIM file ${fileId}`, async () => {
            const result = await jsonFrom<{success?: boolean; file_id?: string}>(await page.request.delete(`${API}/brokers/import/files/${fileId}`), `delete the uploaded report ${fileId}`);
            expect(result).toMatchObject({success: true, file_id: fileId});
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const body = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete an owned broker and its rows');
            expect(body.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const body = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete the owned asset');
            expect(body.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    const user = owned.user;
    if (user) {
        await attempt(`account ${user.username}`, async () => {
            await deleteDisposableUser(request, user);
        });
    }
    expect(failures, 'every cleanup step is scoped to what this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page, request}, use) => {
        const owned: Owned = {user: null, brokerIds: [], assetIds: [], fileIds: []};
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, request, owned);
        }
    },
});

// Registration, the welcome hand-off, the wizard's corridor and up to three saves: the 30 s default is a fraction of it.
test.setTimeout(180_000);

// ---------------------------------------------------------------------------
// The single form
// ---------------------------------------------------------------------------

/** «+» on the transactions page opens the editor with a new row's form on top: the user's way to the single form. */
async function openNewTransactionForm(page: Page): Promise<Locator> {
    await navigateTo(page, '/transactions');
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    await page.getByTestId('tx-add-button').click();
    await expect(page.getByTestId('tx-bulk-modal'), 'the editor opens').toBeVisible({timeout: UI_TIMEOUT});
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'with the form of a new row on top of it').toBeVisible({timeout: UI_TIMEOUT});
    return form;
}

/** The SearchSelect trigger inside `scope`: the one element with an explicit combobox role that opens a listbox. */
function selectTrigger(scope: Locator): Locator {
    return scope.locator('[role="combobox"][aria-haspopup="listbox"]');
}

/** Open a SearchSelect only if it is closed — never a blind click on a toggle. */
async function openSelect(trigger: Locator): Promise<void> {
    await expect(trigger).toBeVisible({timeout: UI_TIMEOUT});
    if ((await trigger.getAttribute('aria-expanded')) !== 'true') await trigger.click();
    await expect(trigger).toHaveAttribute('aria-expanded', 'true');
}

async function chooseAdjustment(page: Page, form: Locator): Promise<void> {
    const select = form.getByTestId('tx-form-type');
    await openSelect(selectTrigger(select));
    const option = select.getByTestId('search-select-option-ADJUSTMENT');
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(form.getByTestId('tx-form-cost-basis-inline'), 'an ADJUSTMENT carries its cost basis in the required section').toBeVisible({timeout: UI_TIMEOUT});
}

/** Pick an owned broker by id; selecting is a setter, so the broker the form may have preset is picked again, harmlessly. */
async function pickBroker(page: Page, scope: Locator, broker: Broker): Promise<void> {
    const trigger = selectTrigger(scope);
    await openSelect(trigger);
    const option = scope.getByTestId(`search-select-option-${broker.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(broker.name);
}

/** The asset select searches inline: narrow it to the owned asset's unique name, then pick it by id. */
async function pickAsset(page: Page, form: Locator, asset: Asset): Promise<void> {
    const trigger = form.getByTestId('tx-form-asset-trigger');
    await openSelect(trigger);
    const search = form.getByTestId('tx-form-asset-search');
    await expect(search).toBeVisible({timeout: UI_TIMEOUT});
    await search.fill(asset.name);
    const option = form.getByTestId('tx-form-asset').getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(asset.name);
}

async function fillQuantity(form: Locator, quantity: string): Promise<void> {
    const input = form.getByTestId('tx-form-quantity');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(quantity);
    await input.blur();
    await expect(input, 'the form keeps the quantity typed').toHaveValue(quantity);
}

/** The description lives in the collapsible optional `<details>`: read its real `open` state, never click blind. */
async function fillDescription(form: Locator, text: string): Promise<void> {
    const details = form.locator('details:has([data-testid="tx-form-optional-toggle"])');
    await expect(details).toBeVisible({timeout: UI_TIMEOUT});
    if (!(await details.evaluate((element) => (element as HTMLDetailsElement).open))) await form.getByTestId('tx-form-optional-toggle').click();
    await expect(details).toHaveAttribute('open', '');
    const description = form.getByTestId('tx-form-description');
    await description.fill(text);
    await expect(description).toHaveValue(text);
}

function costToggle(form: Locator, mode: 'auto' | 'manual'): Locator {
    return form.getByTestId(`tx-form-cost-basis-toggle-${mode}`);
}

/** The Auto | Manual toggle of WacPreviewSection set to Manual: read the state, press only if it is not there. */
async function chooseManual(form: Locator): Promise<void> {
    const manual = costToggle(form, 'manual');
    await expect(manual).toBeVisible({timeout: UI_TIMEOUT});
    if ((await manual.getAttribute('aria-pressed')) !== 'true') await manual.click();
    await expect(manual, 'the cost basis is in Manual').toHaveAttribute('aria-pressed', 'true');
    await expect(costToggle(form, 'auto'), 'and no longer in Auto').toHaveAttribute('aria-pressed', 'false');
}

/** Type a Manual cost; returns the currency the field holds it in (`-currency`, the field's own code), for the read-back. */
async function typeCost(form: Locator, amount: string): Promise<string> {
    const input = form.getByTestId('tx-form-cost-basis-input-amount');
    await input.fill(amount);
    await expect(input, 'the cost field keeps the amount typed').toHaveValue(amount);
    const currency = form.getByTestId('tx-form-cost-basis-input-currency');
    await expect(currency, 'the cost field holds a currency').toHaveText(/^[A-Z]{3}$/);
    return ((await currency.textContent()) ?? '').trim();
}

/** Manual, then `amount`: the user's way to a cost written by hand. */
async function enterManualCost(form: Locator, amount: string): Promise<string> {
    await chooseManual(form);
    return typeCost(form, amount);
}

/** The form's Save — «Apply» in the editor: the draft goes into the grid and the form closes, in one handler. */
async function applyForm(form: Locator): Promise<void> {
    const apply = form.getByTestId('tx-form-save');
    await expect(apply).toBeEnabled({timeout: UI_TIMEOUT});
    await apply.click();
    await expect(form).toBeHidden({timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

function editorRoot(page: Page): Locator {
    return page.getByTestId('tx-bulk-modal-root');
}

function gridRows(root: Locator): Locator {
    return root.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
}

/** The grid row of the given ISO date, on the page shown: every row of a report here has a date of its own. */
function rowByDate(root: Locator, date: string): Locator {
    return gridRows(root).filter({has: root.page().locator(`[data-testid="tx-bulk-date"][data-date="${date}"]`)});
}

/** The rows of the page shown that carry the editor's highlight: `navigateToRowId` sets it on one row at a time. */
function highlightedRows(root: Locator): Locator {
    return root.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id][data-highlighted="true"]');
}

/** The grid's current-page input: its value is the page shown. */
function gridPageInput(root: Locator): Locator {
    return root.getByTestId('tx-bulk-body').getByTestId('data-table-pagination').getByRole('textbox');
}

/** Show page `n` of the grid through its own page input (a setter), and end on it. */
async function showGridPage(root: Locator, n: number): Promise<void> {
    const input = gridPageInput(root);
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill(String(n));
    await input.press('Enter');
    await expect(input, `the grid shows page ${n}`).toHaveValue(String(n));
}

/** The page of the date-sorted grid that holds its `position`-th row (1-based). */
function pageOf(position: number): number {
    return Math.ceil(position / EDITOR_PAGE_SIZE);
}

async function rowLabel(row: Locator): Promise<string> {
    const label = ((await row.getByTestId('tx-bulk-row-label').textContent()) ?? '').trim();
    expect(label, 'an editor row carries its row number').toMatch(/^\d+$/);
    return label;
}

/** Every entry of the editor's issue list: its code and the row number it names. */
async function issueEntries(root: Locator): Promise<IssueEntry[]> {
    const entries = await root.locator('[data-testid="tx-bulk-issue"]').evaluateAll((items) => items.map((item) => ({code: item.getAttribute('data-code') ?? '', label: item.getAttribute('data-row-label') ?? ''})));
    return entries.sort((a, b) => `${a.code}|${a.label}`.localeCompare(`${b.code}|${b.label}`));
}

async function issueCodes(root: Locator): Promise<string[]> {
    return (await issueEntries(root)).map((entry) => entry.code);
}

/** Run one action of a row's menu (kebab) on a row that is on screen; ends with the menu gone. */
async function rowAction(page: Page, row: Locator, actionId: string): Promise<void> {
    await expect(row, 'the row is on the page shown').toBeVisible({timeout: UI_TIMEOUT});
    const rowId = await row.getAttribute('data-row-id');
    expect(rowId, 'an editor row carries its op tempId as data-row-id').toBeTruthy();
    await row.hover();
    const kebab = row.getByTestId(`row-actions-${rowId}`);
    await expect(kebab).toBeVisible({timeout: UI_TIMEOUT});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: UI_TIMEOUT});
    await action.click();
    await expect(action, 'the row menu closes on its action').toBeHidden({timeout: UI_TIMEOUT});
}

/** A row's own form («Edit row»), ending on its cost basis toggle: an ADJUSTMENT +q always has one. */
async function openRowForm(page: Page, row: Locator): Promise<Locator> {
    await rowAction(page, row, 'edit-single');
    const form = page.getByTestId('tx-form-modal');
    await expect(form, 'the row opens in its form').toBeVisible({timeout: UI_TIMEOUT});
    await expect(form.getByTestId('tx-form-cost-basis-toggle'), 'an ADJUSTMENT +q shows the Auto | Manual toggle of its cost basis').toBeVisible({timeout: UI_TIMEOUT});
    return form;
}

/** ⚡ «Validate now», then the run it started: the counter is sampled before the click (rule 16). */
async function validateNow(root: Locator): Promise<void> {
    await waitForSettled(root, STEP_TIMEOUT);
    const before = await validateRuns(root);
    await root.getByTestId('tx-bulk-validate-now').click();
    await waitForValidateRun(root, before, STEP_TIMEOUT);
}

/** Save all, and the commit's answer, captured as it comes back: the commit is the subject here. */
async function saveAll(page: Page): Promise<BatchAnswer> {
    const root = editorRoot(page);
    await waitForSettled(root, STEP_TIMEOUT);
    const save = root.getByTestId('tx-bulk-commit');
    await expect(save, 'Save all is offered').toBeEnabled({timeout: UI_TIMEOUT});
    const answer = armed(page.waitForResponse((response) => isCommit(response.request()), {timeout: 60_000}));
    await save.click();
    return jsonFrom<BatchAnswer>(await answer, 'the commit answer');
}

/** Never Save all: close the editor through its unsaved-changes guard, then prove nothing reached the owned broker. */
async function discardEditor(page: Page, root: Locator, broker: Broker): Promise<void> {
    await root.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: UI_TIMEOUT});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: UI_TIMEOUT});
    expect(await ledgerOf(page, broker), 'discarding the editor saved nothing on the owned broker').toEqual([]);
}

// ---------------------------------------------------------------------------
// The import: a synthetic CoinTracking export, through the wizard, to the editor
// ---------------------------------------------------------------------------

const CT_HEADER = ['Type', 'Buy', 'Cur.', 'Sell', 'Cur.', 'Fee', 'Cur.', 'Exchange', 'Group', 'Comment', 'Date', 'Tx-ID'];
const CT_EXCHANGE = 'J57 exchange';
/** The purchase every import report here ends with: after its Receives, so none of them has a unit to average. */
const PURCHASE: CtRow = {kind: 'buy', date: '2024-03-01', quantity: '2', cost: '100.00'};

/** `count` fiat «Deposit» rows (DEPOSIT EUR), one a day from 2024-01-01: before every Receive, past the first page. */
function cashRows(count: number): CtRow[] {
    return Array.from({length: count}, (_, i): CtRow => ({kind: 'cash', date: isoPlusDays('2024-01-01', i), amount: '1000.00'}));
}

/**
 * The export, in CoinTracking's own format (`broker_cointracking/plugin.py`: the exact 12-column header, read by
 * index). A «Deposit» of `symbol` — a crypto, no ISO code — is a Receive: the plugin writes it ADJUSTMENT +q, without
 * cash, cost or todo. A «Deposit» of EUR is a DEPOSIT; a «Trade» of `symbol` against EUR is a BUY. No fee: no FEE row.
 */
function cointrackingCsv(symbol: string, rows: CtRow[]): string {
    const line = (cells: string[]) => cells.map((cell) => `"${cell}"`).join(',');
    const body = rows.map((row, i) => {
        const when = `${row.date} 10:00:00`;
        const txId = `j57-${i + 1}`;
        if (row.kind === 'cash') return line(['Deposit', row.amount, 'EUR', '', '', '', '', CT_EXCHANGE, '', '', when, txId]);
        if (row.kind === 'receive') return line(['Deposit', row.quantity, symbol, '', '', '', '', CT_EXCHANGE, '', '', when, txId]);
        return line(['Trade', row.quantity, symbol, row.cost, 'EUR', '', '', CT_EXCHANGE, '', '', when, txId]);
    });
    return [line(CT_HEADER), ...body].join('\n') + '\n';
}

/** What the plugin must read each row as: type, date, quantity. */
function expectedReading(row: CtRow): string {
    if (row.kind === 'cash') return `DEPOSIT ${row.date} 0`;
    if (row.kind === 'receive') return `ADJUSTMENT ${row.date} ${Number(row.quantity)}`;
    return `BUY ${row.date} ${Number(row.quantity)}`;
}

/** An account for an import test: its broker reads CoinTracking by default, its asset is the report's crypto. */
async function seedImportAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<ImportSeed> {
    await openDisposableAccount(page, request, owned, tag);
    const suffix = uniqueSuffix();
    const symbol = `J57${uniqueToken(7)}`;
    const broker = await createBroker(page, owned, `j57-${tag}-${suffix}`, {default_import_plugin: COINTRACKING});
    const asset = await createAsset(page, owned, {name: `J57 ${tag} ${suffix}`, ticker: symbol, assetType: 'CRYPTO'});
    expect(await ledgerOf(page, broker), 'premise: the owned broker never held anything').toEqual([]);
    return {broker, asset, symbol};
}

/**
 * Write a blocking cost todo into the parse response of this page, on the Receive dated `todo.date` — the F1-D4
 * injection of tx-bulk-import-handoff.spec.ts. A field the corrections step does not own: it travels to the editor.
 */
async function injectBlockingCostTodo(page: Page, todo: InjectedTodo): Promise<void> {
    await page.route(
        (url) => PARSE_PATH.test(url.pathname),
        async (route) => {
            const response = await route.fetch();
            if (!response.ok()) {
                await route.fulfill({response});
                return;
            }
            const body = (await response.json()) as CtParse;
            const txIndex = body.transactions.findIndex((tx) => tx.type === 'ADJUSTMENT' && tx.date === todo.date);
            const added = txIndex < 0 ? [] : [{tx_index: txIndex, field: 'cost_basis_override', severity: 'blocker', reason_code: todo.reason_code, message: todo.message}];
            // A new body, so not the original headers: their content-length is the old body's.
            await route.fulfill({status: response.status(), contentType: 'application/json', body: JSON.stringify({...body, field_todos: [...(body.field_todos ?? []), ...added]})});
        },
    );
}

/**
 * The report, from upload to the editor: upload it to the owned broker over the API (unique name), open the wizard
 * from the transactions page, select the file in step 2 and parse it — CoinTracking reads every row as written, without
 * a cost, a mode or a todo (but the one `injectedTodo` writes into the response), the crypto resolves to the owned
 * asset — walk to the review with every row selected, Import, then wait for a validation run since the click (the
 * counter sampled before it) and for the editor to settle: the verdict on screen is then the last run's (see «Reading a
 * verdict» in the header). Returns the editor root and the parse response.
 */
async function importReport(page: Page, owned: Owned, seed: ImportSeed, report: {tag: string; rows: CtRow[]; injectedTodo?: InjectedTodo}): Promise<{root: Locator; parsed: CtParse}> {
    const injected = report.injectedTodo;
    if (injected) await injectBlockingCostTodo(page, injected);
    const fileName = `j57-${report.tag}-${uniqueSuffix()}.csv`;
    const uploaded = await jsonFrom<{file_id: string; target_broker_id: number | null; compatible_plugins?: string[]}>(
        await page.request.post(UPLOAD_PATH, {multipart: {broker_id: String(seed.broker.id), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(cointrackingCsv(seed.symbol, report.rows), 'utf8')}}}),
        `upload ${fileName}`,
    );
    owned.fileIds.push(uploaded.file_id);
    expect(uploaded.target_broker_id, 'the report lands on the owned broker').toBe(seed.broker.id);
    expect(uploaded.compatible_plugins ?? [], 'CoinTracking reads the report').toContain(COINTRACKING);

    await navigateTo(page, '/transactions');
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: UI_TIMEOUT});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1, STEP_TIMEOUT);
    // Nothing to upload in step 1: the report is already on the broker.
    await page.getByTestId('import-wizard-next').click();
    await selectBrokerFile(page, {brokerId: seed.broker.id, fileId: uploaded.file_id});
    const response = await parseSelectedFile(page, uploaded.file_id);
    const parsed = response as unknown as CtParse;

    expect(parsed.plugin_code, "the broker's default plugin reads the report").toBe(COINTRACKING);
    expect(parsed.transactions.map((tx) => `${tx.type} ${tx.date} ${Number(tx.quantity)}`).sort(), 'CoinTracking reads every row as written: a crypto Deposit is an ADJUSTMENT +q').toEqual(report.rows.map(expectedReading).sort());
    const adjustments = parsed.transactions.filter((tx) => tx.type === 'ADJUSTMENT');
    expect(
        adjustments.map((tx) => tx.cost_basis_override ?? null),
        'the plugin writes a Receive without a cost',
    ).toEqual(adjustments.map(() => null));
    const todos = (parsed.field_todos ?? []).map(({tx_index, field, severity, reason_code}) => ({tx_index, field, severity, reason_code}));
    if (injected) {
        const receiveIndex = parsed.transactions.findIndex((tx) => tx.type === 'ADJUSTMENT' && tx.date === injected.date);
        expect(receiveIndex, `premise: the report has a Receive dated ${injected.date}`).toBeGreaterThanOrEqual(0);
        expect(todos, 'premise: the page received one blocking cost todo, on the Receive').toEqual([{tx_index: receiveIndex, field: 'cost_basis_override', severity: 'blocker', reason_code: injected.reason_code}]);
    } else {
        expect(todos, 'the plugin writes its rows without a todo').toEqual([]);
    }
    const assetRows = parsed.transactions.filter((tx) => tx.type !== 'DEPOSIT');
    const resolved = assetRows.map((tx) => parsed.asset_mappings?.find((mapping) => mapping.fake_asset_id === tx.asset_id)?.selected_asset_id ?? null);
    expect(resolved, "the report's crypto resolves to the owned asset, the only one with its ticker").toEqual(assetRows.map(() => seed.asset.id));

    const review = await continueToReview(page, response);
    await expect(review, 'every row of the report is selected in the review').toHaveAttribute('data-selected-count', String(report.rows.length), {timeout: UI_TIMEOUT});
    const root = editorRoot(page);
    await expect(root, 'the editor is open beneath the wizard').toBeAttached();
    const before = await validateRuns(root);
    const importButton = page.getByTestId('import-wizard-import');
    await expect(importButton, 'Import is offered: every row selected, none waits for an asset').toBeEnabled({timeout: STEP_TIMEOUT});
    await importButton.click();
    await expect(page.getByTestId('import-wizard-stepper'), 'the wizard hands over and closes').toHaveCount(0, {timeout: STEP_TIMEOUT});
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    // Every hand-over runs one validation (F1-D5); `waitForValidateRun` also waits out a background run that may follow it.
    await waitForValidateRun(root, before, STEP_TIMEOUT);
    return {root, parsed};
}

/**
 * A Receive's form opens in Auto and is applied as it is. Auto is the mode the hand-over gives a row without a blocking
 * cost todo (decision 5); before the cure, the form's own fallback for a row without a mode: either way the form opens
 * in Auto, and Apply leaves the row in Auto.
 */
async function applyInAuto(page: Page, row: Locator, what: string): Promise<void> {
    const form = await openRowForm(page, row);
    await expect(costToggle(form, 'auto'), `${what}, without a blocking cost todo, opens in Auto`).toHaveAttribute('aria-pressed', 'true');
    await applyForm(form);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('J-57 · the single form refuses an Auto cost with nothing to average; a cost by hand, 0 included, saves', () => {
    /**
     * RED before the cure (decision 4): the form listed the refusal, but its `tx-form-issue` carried no `data-code`
     * (`TxFormBanners.svelte`). Everything else is CONTROL, green before the cure and with it: the server's refusal on
     * the wire (N88), the refused Save that writes nothing, the Manual 0 that saves, the cost of 0 read back.
     *
     * In the app the single form lives inside the editor: its «Save» is «Apply», which hands the row to the editor,
     * whose «Save all» is the save the server answers. Both are exercised.
     */
    test('E1 · an ADJUSTMENT +5 in Auto on a broker that never held the asset: the form shows autoCostEmptyPool by code, Save is refused; Manual 0 saves at cost 0', async ({page, request, owned}) => {
        const {broker, asset, marker} = await test.step('seed: an account with a broker that never held anything, and an asset of its own', async () => {
            await openDisposableAccount(page, request, owned, 'j57e1');
            const suffix = uniqueSuffix();
            const broker = await createBroker(page, owned, `j57-form-${suffix}`);
            const asset = await createAsset(page, owned, {name: `J57 form asset ${suffix}`, ticker: `J57F${uniqueToken(8)}`, assetType: 'ETF'});
            expect(await ledgerOf(page, broker), 'premise: the broker never held anything').toEqual([]);
            return {broker, asset, marker: `J57 E1 ${suffix}`};
        });

        const form = await openNewTransactionForm(page);

        await test.step('the form: an ADJUSTMENT +5 of the asset on the broker, the cost basis left in Auto', async () => {
            await chooseAdjustment(page, form);
            await pickBroker(page, form.getByTestId('tx-form-broker-wrap'), broker);
            await pickAsset(page, form, asset);
            await fillQuantity(form, '5');
            await expect(costToggle(form, 'auto'), 'the cost basis is in Auto, the default, untouched').toHaveAttribute('aria-pressed', 'true');
            await expect(costToggle(form, 'manual')).toHaveAttribute('aria-pressed', 'false');
        });

        await test.step('the verdict of the form: autoCostEmptyPool on the wire (CONTROL), on screen with its code (RED)', async () => {
            // Armed before the last edit: the validation that carries the description is the one of the final draft.
            const verdictResponse = armed(page.waitForResponse((response) => isValidate(response.request()) && sentCreates(response.request()).some((create) => create.description === marker), {timeout: STEP_TIMEOUT}));
            await fillDescription(form, marker);
            const answered = await verdictResponse;
            const sent = sentCreates(answered.request());
            const own = sent.findIndex((create) => create.description === marker);
            expect(sent[own]?.cost_basis_mode, 'the form sends the row in Auto').toBe('auto-detail');
            const verdict = await jsonFrom<BatchAnswer>(answered, 'the validation of the form');
            expect(issuesOf(verdict, 'create', own), 'N88: an Auto cost on a broker that never held the asset is refused autoCostEmptyPool, on the cost basis').toEqual([{code: EMPTY_POOL, field: 'cost_basis_override'}]);

            await expect(form.getByTestId('tx-form-issue'), 'the form lists the refusal: one issue, its own row').toHaveCount(1, {timeout: UI_TIMEOUT});
            await expect(form.locator(`[data-testid="tx-form-issue"][data-code="${EMPTY_POOL}"]`), 'decision 4: the issue of the form carries its code (data-code on tx-form-issue, TxFormBanners.svelte; missing before the cure)').toBeVisible({timeout: UI_TIMEOUT});
        });

        const root = editorRoot(page);
        const row = gridRows(root).filter({hasText: marker});

        await test.step('Save: the form hands the row to the editor, whose Save all is refused — nothing is written', async () => {
            await applyForm(form);
            await expect(row, 'the editor holds the row of the form').toHaveCount(1, {timeout: UI_TIMEOUT});
            const refused = await saveAll(page);
            expect(refused.committed, 'the save of an Auto cost with nothing to average is refused').toBe(false);
            expect(issuesOf(refused, 'create', 0), `the refusal is autoCostEmptyPool on the cost basis — answered ${JSON.stringify(refused.issues ?? [])}`).toEqual([{code: EMPTY_POOL, field: 'cost_basis_override'}]);
            const error = root.getByTestId('tx-bulk-error');
            await expect(error, 'the editor says the save was cancelled').toBeVisible({timeout: UI_TIMEOUT});
            await expect(error.locator(`[data-testid="tx-bulk-issue"][data-code="${EMPTY_POOL}"]`), 'and why, by code').toHaveCount(1);
            expect(await ledgerOf(page, broker), 'the refused save wrote nothing').toEqual([]);
        });

        const currency = await test.step('Manual: the row opens in its form in Auto; Manual, empty and flagged; 0 is a cost; Save all saves it', async () => {
            const rowForm = await openRowForm(page, row);
            await expect(costToggle(rowForm, 'auto'), 'the row was applied in Auto: its form opens in Auto').toHaveAttribute('aria-pressed', 'true');
            await chooseManual(rowForm);
            await expect(rowForm.getByTestId('tx-form-cost-basis-input-amount'), 'Auto wrote no cost on the row: Manual starts empty').toHaveValue('');
            await expect(rowForm.getByTestId('tx-form-cost-basis-warning'), 'an empty Manual cost says it is required').toBeVisible();
            const code = await typeCost(rowForm, '0');
            await expect(rowForm.getByTestId('tx-form-cost-basis-warning'), '0 is a cost: the warning goes').toBeHidden();
            await applyForm(rowForm);
            const saved = await saveAll(page);
            expect(saved.committed, `a cost of 0 written by hand is allowed (a gift) — answered ${JSON.stringify(saved.issues ?? [])}`).toBe(true);
            await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes on a successful save').toBeHidden({timeout: UI_TIMEOUT});
            return code;
        });

        await test.step('the saved row, read from the API: the ADJUSTMENT +5, its cost basis 0', async () => {
            expect(savedAdjustments(await ledgerOf(page, broker))).toEqual([{date: expect.any(String), quantity: 5, description: marker, code: currency, amount: 0}]);
        });
    });
});

test.describe('J-57 · an import whose Receive has nothing to average: the editor refuses it and leads to it', () => {
    /**
     * RED before the cure, on two counts. The mode (decision 5): the Receive reached the editor without a cost mode, so
     * the hand-over's validation refused it `costBasisRequired`, not `autoCostEmptyPool`. The jump (decision 3): the
     * grid stayed on page 1, nothing highlighted. Green once the hand-over starts the Receive in Auto
     * (`initialCostBasisMode`) and its own validation pages the grid to the row it refused. The save at a cost of 0 after
     * it is CONTROL (N88: a cost by hand stays allowed).
     *
     * The two counts are two steps, so a red names its count. With 32 rows a background run may follow the hand-over;
     * the verdict is read once the editor has settled, and a background run never moves the grid: only the hand-over's
     * own validation can have led to the Receive.
     */
    test('E2 · after the hand-over the Receive is refused autoCostEmptyPool, the issue names its row and the grid is on it without a click; Manual 0 saves the import, cost 0', async ({page, request, owned}) => {
        const RECEIVE: CtRow = {kind: 'receive', date: '2024-02-10', quantity: '5'};
        const rows: CtRow[] = [...cashRows(30), RECEIVE, PURCHASE];
        /** By date the Receive is the 31st row: the 30 fiat deposits come first. */
        const receivePosition = 31;
        expect(pageOf(receivePosition), 'premise: the Receive is past the first page of the grid').toBeGreaterThan(1);

        const seed = await seedImportAccount(page, request, owned, 'j57e2');
        const {root} = await test.step('the report, through the wizard, to the editor, and the validation of its hand-over', async () => importReport(page, owned, seed, {tag: 'handover', rows}));
        const receive = rowByDate(root, RECEIVE.date);

        await test.step('the mode: the Receive starts in Auto, and the verdict refuses it for its Auto cost, nothing else', async () => {
            await expect
                .poll(() => issueCodes(root), {
                    message: 'decision 5: the Receive starts in Auto at the hand-over, so it is refused autoCostEmptyPool, and nothing else. A costBasisRequired here means initialCostBasisMode did not run at the hand-over: the row reached the editor without a cost mode (the plugin sends none)',
                    timeout: UI_TIMEOUT,
                })
                .toEqual([EMPTY_POOL]);
        });

        await test.step('the jump: the grid is on the refused row, highlighted, without any click', async () => {
            await expect(
                receive,
                "decision 3: the hand-over's own validation pages the grid to the row it refused for an Auto cost. If the refusal is listed but the grid is still on page 1, the verdict on screen is likely a background run's, which never moves the grid: the hand-over's own answer dropped as stale (validateFn reads lastDraftKey before the editor's $effect has moved it to the imported rows)",
            ).toBeVisible({timeout: UI_TIMEOUT});
            await expect(gridPageInput(root), "the grid is on the Receive's page").toHaveValue(String(pageOf(receivePosition)));
            await expect(receive, 'highlighted, as a click on its issue does').toHaveAttribute('data-highlighted', 'true');
            await expect(highlightedRows(root), 'and only that row').toHaveCount(1);
            const label = await rowLabel(receive);
            await expect(root.locator(`[data-testid="tx-bulk-issue"][data-code="${EMPTY_POOL}"]`), 'the refusal names that row').toHaveAttribute('data-row-label', label);
            await expect(receive.getByTestId('tx-bulk-cost-basis-auto'), 'decision 5 in the grid: its cost cell is the Auto one, with nothing proposed').toHaveAttribute('data-state', 'empty');
        });

        const currency = await test.step('Manual 0 in its form, Apply, Save all: the whole import is saved', async () => {
            const form = await openRowForm(page, receive);
            const code = await enterManualCost(form, '0');
            await applyForm(form);
            const saved = await saveAll(page);
            expect(saved.committed, `the import with its Receive at a cost of 0 is saved — answered ${JSON.stringify(saved.issues ?? [])}`).toBe(true);
            await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes on a successful save').toBeHidden({timeout: UI_TIMEOUT});
            return code;
        });

        await test.step('read back from the API: every row of the report, the Receive at a cost of 0', async () => {
            const ledger = await ledgerOf(page, seed.broker);
            expect(ledger, 'every row of the report is saved').toHaveLength(rows.length);
            expect(savedAdjustments(ledger).map(({date, quantity, code, amount}) => ({date, quantity, code, amount}))).toEqual([{date: RECEIVE.date, quantity: 5, code: currency, amount: 0}]);
        });
    });

    /**
     * RED before the cure (decisions 5 and 3): the Receives arrived without a cost mode and were refused
     * `costBasisRequired`, and ⚡ and a refused Save left the grid where it was. With the cure both Receives start in
     * Auto at the hand-over, so its verdict refuses both — the cascade: each leaves the other, not yet costed, out of
     * its pool. Where the hand-over left the grid is not this test's subject (E2's): every step below starts from page 1,
     * which the test shows and checks itself. The report lists the newer Receive first, so the batch — the editor's rows
     * in import order, the creates of every validation — does not follow the dates: the jump must still go to the OLDER
     * one (the batch's own refusals come in pool-date order, so the newer row is neither the first of the rows nor the
     * target). The background-validation guard (a clone, no explicit validation, the grid stays on page 1) was green
     * before the cure and must stay green. Nothing is saved.
     */
    test('E2 · ⚡ Validate now and a refused Save page the grid to the oldest row refused for an Auto cost; a background validation does not', async ({page, request, owned}) => {
        const OLDER: CtRow = {kind: 'receive', date: '2024-02-10', quantity: '3'};
        const NEWER: CtRow = {kind: 'receive', date: '2024-02-20', quantity: '7'};
        /** A deposit on the first page, cloned to make the editor validate in the background. */
        const CLONED_DATE = '2024-01-05';
        const deposits = cashRows(30);
        expect(
            deposits.map((row) => row.date),
            'premise: the deposit to clone is in the report',
        ).toContain(CLONED_DATE);
        // Newest first, as exports often are: the order of the batch is not the order of the dates.
        const rows: CtRow[] = [PURCHASE, NEWER, OLDER, ...deposits];

        const seed = await seedImportAccount(page, request, owned, 'j57e2v');
        const {root} = await test.step('the report, through the wizard, to the editor', async () => importReport(page, owned, seed, {tag: 'validate-now', rows}));
        const older = rowByDate(root, OLDER.date);
        const newer = rowByDate(root, NEWER.date);
        const cloned = rowByDate(root, CLONED_DATE);
        /** By date: 30 deposits, then the clone of one of them, then the older Receive. */
        const olderPosition = 32;

        await test.step('the hand-over: both Receives start in Auto (decision 5), and the verdict refuses both — the cascade', async () => {
            await expect
                .poll(() => issueCodes(root), {
                    message: 'decision 5: the Receives start in Auto at the hand-over, and each leaves the other, not yet costed, out of its pool: both are refused. costBasisRequired here means initialCostBasisMode did not run at the hand-over',
                    timeout: UI_TIMEOUT,
                })
                .toEqual([EMPTY_POOL, EMPTY_POOL]);
        });

        await test.step('a background validation (a clone of a deposit) refuses both, and leaves the grid on page 1', async () => {
            await showGridPage(root, 1);
            await expect(cloned, 'the deposit to clone is on page 1').toHaveCount(1, {timeout: UI_TIMEOUT});
            await expect(older, 'the Receives are not on page 1').toHaveCount(0);
            const before = await validateRuns(root);
            await rowAction(page, cloned, 'clone');
            await expect(cloned, 'the clone sits beside its source').toHaveCount(2, {timeout: UI_TIMEOUT});
            await waitForValidateRun(root, before, STEP_TIMEOUT);
            await expect.poll(() => issueCodes(root), {message: 'the background run refuses both Receives: the cascade', timeout: UI_TIMEOUT}).toEqual([EMPTY_POOL, EMPTY_POOL]);
            await expect(gridPageInput(root), 'a background validation leaves the grid where the user is').toHaveValue('1');
            await expect(older).toHaveCount(0);
        });

        await test.step('⚡ Validate now from page 1: the grid goes to the older Receive, highlighted', async () => {
            await validateNow(root);
            await expect.poll(() => issueCodes(root), {message: '⚡ refuses both Receives', timeout: UI_TIMEOUT}).toEqual([EMPTY_POOL, EMPTY_POOL]);
            await expect(older, 'decision 3: ⚡ pages the grid to the first row refused for an Auto cost (before the cure the grid stayed on page 1)').toBeVisible({timeout: UI_TIMEOUT});
            await expect(gridPageInput(root)).toHaveValue(String(pageOf(olderPosition)));
            await expect(older, 'the oldest by date, highlighted — not the newer one, which comes first in the batch').toHaveAttribute('data-highlighted', 'true');
            await expect(highlightedRows(root), 'one row highlighted').toHaveCount(1);
            const labels = [await rowLabel(older), await rowLabel(newer)];
            expect(await issueEntries(root), 'the two refusals name the two Receives').toEqual(labels.map((label) => ({code: EMPTY_POOL, label})).sort((a, b) => `${a.code}|${a.label}`.localeCompare(`${b.code}|${b.label}`)));
            // Both on this page now: decision 5 seen in the grid, each cost cell the Auto one, with nothing proposed.
            await expect(older.getByTestId('tx-bulk-cost-basis-auto'), 'the older Receive is in Auto').toHaveAttribute('data-state', 'empty');
            await expect(newer.getByTestId('tx-bulk-cost-basis-auto'), 'the newer Receive is in Auto').toHaveAttribute('data-state', 'empty');
        });

        await test.step('a refused Save from page 1: the grid goes to the older Receive again', async () => {
            await showGridPage(root, 1);
            await expect(cloned, 'page 1 is drawn').toHaveCount(2, {timeout: UI_TIMEOUT});
            await expect(older).toHaveCount(0);
            const refused = await saveAll(page);
            expect(refused.committed, 'the save is refused: both Receives are Auto costs with nothing to average').toBe(false);
            expect(codesOf(refused)).toEqual([EMPTY_POOL, EMPTY_POOL]);
            await expect(older, 'decision 3: a refused Save pages the grid to the first row refused for an Auto cost (before the cure the grid stayed on page 1)').toBeVisible({timeout: UI_TIMEOUT});
            await expect(older).toHaveAttribute('data-highlighted', 'true');
            await expect(highlightedRows(root)).toHaveCount(1);
        });

        await discardEditor(page, root, seed.broker);
    });

    /**
     * CONTROL (N88), green before the cure and with it: two Auto Receives on an empty pool are both refused; Manual 0 on
     * the earlier one lets the later one pass in Auto, at the 0 of the free units before it; both are saved at a cost
     * of 0. The Receives reach Auto through their own forms, applied as they are: with the cure they already start in
     * Auto (decision 5) and the form opens there; before it, the form fell back to Auto. Either way ⚡ then validates
     * two Auto rows — the cascade is checked whatever the hand-over did. On one page, the jump of ⚡ (decision 3) only
     * highlights a row already on screen: nothing here reads it.
     */
    test('E3 · the cascade: two Receives in Auto are both refused; Manual 0 on the earlier lets the later pass in Auto; both saved at cost 0', async ({page, request, owned}) => {
        const EARLIER: CtRow = {kind: 'receive', date: '2024-02-10', quantity: '3'};
        const LATER: CtRow = {kind: 'receive', date: '2024-02-20', quantity: '7'};

        const seed = await seedImportAccount(page, request, owned, 'j57e3');
        const {root} = await test.step('the report, through the wizard, to the editor', async () => importReport(page, owned, seed, {tag: 'cascade', rows: [EARLIER, LATER]}));
        const earlier = rowByDate(root, EARLIER.date);
        const later = rowByDate(root, LATER.date);

        await test.step('both Receives in Auto, through their forms applied as they are: ⚡ refuses both autoCostEmptyPool, each named', async () => {
            await applyInAuto(page, earlier, 'the earlier Receive');
            await applyInAuto(page, later, 'the later Receive');
            await validateNow(root);
            const labels = [await rowLabel(earlier), await rowLabel(later)];
            await expect
                .poll(() => issueEntries(root), {message: 'each Receive leaves the other, not yet costed, out of its pool: both are refused', timeout: UI_TIMEOUT})
                .toEqual(labels.map((label) => ({code: EMPTY_POOL, label})).sort((a, b) => `${a.code}|${a.label}`.localeCompare(`${b.code}|${b.label}`)));
        });

        const currency = await test.step('Manual 0 on the earlier only: the later passes in Auto', async () => {
            const form = await openRowForm(page, earlier);
            const code = await enterManualCost(form, '0');
            await applyForm(form);
            await validateNow(root);
            await expect(root.getByTestId('tx-bulk-valid'), 'nothing is refused any more').toBeVisible({timeout: UI_TIMEOUT});
            await expect(root.locator('[data-testid="tx-bulk-issue"]')).toHaveCount(0);
            await expect(later.getByTestId('tx-bulk-cost-basis-auto'), 'the later Receive got an Auto cost').toHaveAttribute('data-state', 'ready', {timeout: UI_TIMEOUT});
            return code;
        });

        await test.step('Save all, then the API: both Receives saved at a cost of 0', async () => {
            const saved = await saveAll(page);
            expect(saved.committed, `free units keep their 0 — answered ${JSON.stringify(saved.issues ?? [])}`).toBe(true);
            await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes on a successful save').toBeHidden({timeout: UI_TIMEOUT});
            expect(savedAdjustments(await ledgerOf(page, seed.broker)).map(({date, quantity, code, amount}) => ({date, quantity, code, amount}))).toEqual([
                {date: EARLIER.date, quantity: 3, code: currency, amount: 0},
                {date: LATER.date, quantity: 7, code: currency, amount: 0},
            ]);
        });
    });

    /**
     * RED before the cure (decision 2, kept by decision 5): the row arrived without a cost mode, so its form opened in
     * Auto — the fallback — and Auto answered the todo. With the cure the hand-over starts it in Manual, its field empty
     * (`initialCostBasisMode`: a blocking cost todo wins over the Auto every other uncosted row gets), and only a value
     * answers the todo. The blocker listed after the hand-over, with Save held, is CONTROL. Nothing is saved.
     */
    test('E4 · a Receive with a blocking cost todo: its form opens in Manual, empty; Apply empty keeps the todo, 0 answers it', async ({page, request, owned}) => {
        const RECEIVE: CtRow = {kind: 'receive', date: '2024-02-10', quantity: '5'};
        // The generic CSV plugin's own blocker for an ADJUSTMENT without an inherited cost (broker_generic_csv/plugin.py).
        const todo: InjectedTodo = {date: RECEIVE.date, reason_code: 'corporate_action', message: 'Missing inherited per-unit cost basis (WAC). Enter the cost per single unit (not the total) to import.'};

        const seed = await seedImportAccount(page, request, owned, 'j57e4');
        const {root} = await test.step('the report, its parse carrying the blocking cost todo, to the editor', async () => importReport(page, owned, seed, {tag: 'cost-todo', rows: [RECEIVE], injectedTodo: todo}));

        const receive = rowByDate(root, RECEIVE.date);
        const save = root.getByTestId('tx-bulk-commit');
        const blockers = root.getByTestId('tx-bulk-todo-blockers');
        const entry = await test.step('the editor lists the blocker on the Receive, and holds Save', async () => {
            await expect(receive).toBeVisible({timeout: UI_TIMEOUT});
            const rowId = await receive.getAttribute('data-row-id');
            expect(rowId, 'an editor row carries its op tempId as data-row-id').toBeTruthy();
            await expect(blockers, 'the blockers banner lists the import todos that hold Save').toBeVisible({timeout: UI_TIMEOUT});
            const gotos = blockers.getByTestId('tx-bulk-todo-goto');
            // Folded by default: unfold it only when its entries are not drawn — a state read, never a blind toggle.
            if ((await gotos.count()) === 0) await blockers.getByTestId('tx-bulk-todo-blockers-toggle').click();
            const own = blockers.locator(`[data-testid="tx-bulk-todo-goto"][data-row-id="${rowId}"]`);
            await expect(own, 'one entry, for the Receive').toHaveCount(1, {timeout: UI_TIMEOUT});
            await expect(save, 'a blocker holds Save').toBeDisabled();
            return own;
        });

        await test.step('its form opens in Manual with the cost field empty', async () => {
            const form = await openRowForm(page, receive);
            await expect(costToggle(form, 'manual'), 'decisions 2 and 5: a row with a blocking cost todo starts in Manual at the hand-over, and its form opens there (before the cure: Auto)').toHaveAttribute('aria-pressed', 'true');
            await expect(costToggle(form, 'auto')).toHaveAttribute('aria-pressed', 'false');
            await expect(form.getByTestId('tx-form-cost-basis-input-amount'), 'with the cost field empty').toHaveValue('');
            await expect(form.getByTestId('tx-form-cost-basis-warning'), 'and the warning of an empty Manual cost').toBeVisible();

            // Apply with the field empty: patched and closed in one handler, so the banner below already reads the patched row.
            await applyForm(form);
            await expect(entry, 'an empty field answers nothing: the blocker is still listed').toHaveCount(1);
            await expect(save, 'and still holds Save').toBeDisabled();
        });

        await test.step('0 in the field answers the todo', async () => {
            const form = await openRowForm(page, receive);
            await expect(costToggle(form, 'manual'), 'the row kept Manual').toHaveAttribute('aria-pressed', 'true');
            await typeCost(form, '0');
            await applyForm(form);
            await expect(save, 'nothing holds Save any more').toBeEnabled({timeout: UI_TIMEOUT});
            await expect(blockers, 'the blocker is gone').toHaveCount(0);
        });

        await discardEditor(page, root, seed.broker);
    });
});
