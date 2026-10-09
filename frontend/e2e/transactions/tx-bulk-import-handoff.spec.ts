/**
 * Transaction bulk editor — what happens when the import wizard hands rows over (F1 of the Danske
 * Bank workstream, issue 26: the developer's review, D4 and D5).
 *
 * D5 — one automatic validation after every import. The editor validates by itself only up to
 *      `AUTO_VALIDATE_THRESHOLD` (50) rows; above it "Validate now" is manual. The developer:
 *      «dopo un processo di import, indipendentemente dalla dimensione dell'import, un validate now
 *      è bene che parta in automatico, solo il primo però, gli altri sono in carico all'utente».
 *      So every hand-over (`onImportBatch`) runs ONE validation — the same POST /transactions/validate
 *      as "Validate now", over the whole editor — whatever the number of rows; afterwards today's
 *      rules hold (above 50 rows an edit does not validate); a new import runs one more.
 *      Pinned by counting the requests: a synthetic cash-only generic CSV of 55 rows goes through the
 *      wizard, then a plain edit (a clone, no form), then a second import of 3 rows.
 *
 * D4 — the todo banners lead to their rows. Every entry of the blockers banner
 *      (`tx-bulk-todo-blockers`) and of the warnings banner (`tx-bulk-todo-warnings`, until F1 a single
 *      line with a count) is a button `tx-bulk-todo-goto` whose `data-row-id` is the op's tempId (the
 *      row's `data-row-id` in the grid); a click pages the grid to the row and highlights it
 *      (`tableRef.navigateToRowId`, as `jumpToIssue` does: `tr[data-row-id][data-highlighted="true"]`).
 *      The blockers banner folds behind `tx-bulk-todo-blockers-toggle`; if the warnings banner folds
 *      too, its toggle is `tx-bulk-todo-warnings-toggle`. The spec asks for the state before toggling.
 *      The todos are the parse's: the file is a cash-only generic CSV, and the parse response of this
 *      test's own file is extended with three invented `field_todos` (one blocker on
 *      `cost_basis_override`, two warnings on other fields) — kinds the correction step does not own,
 *      so they travel to the editor untouched. They sit on rows dated last, on the grid's second page.
 *
 * S19 — the banners word a todo by its reason code (i18n audit, decisions A and B). A todo's `message` is
 *      the plugin's own, in the language of the parsed file; when `importWizard.brimNotice.<reason_code>`
 *      exists, its wording replaces it, in the UI language — the rule of the notices
 *      (`resolveBrimNotice.ts`), of ParseDetailModal and of the fix step. The parse response of a cash-only
 *      file is extended with a blocker and a warning on `corporate_action` (the generic CSV plugin's
 *      blocker, which the catalogue words) and with a blocker and a warning on a probe code no catalogue
 *      words, every message carrying its own marker. Each entry is found by the `data-row-id` of its row:
 *      the probe code's entries read the plugin's message; the `corporate_action` entries never show their
 *      marker nor a raw key, and read the catalogue's wording in the language of `<html lang>` — taken from
 *      the catalogue JSON at test time, so no translated copy is written here.
 *
 * Data: every test creates its own broker over the API (generic CSV plugin, opened 2020-01-01) and
 * writes its CSVs under `testInfo.outputPath()`; invented dates, amounts and descriptions. Nothing is
 * ever saved: the editor is closed through its unsaved-changes guard. afterEach leaves the page,
 * deletes the BRIM files uploaded to the broker since the test created it, the broker (force) and
 * the CSVs it wrote.
 *
 * Plan: `LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md`, F.0 (F1 · D4, D5);
 * `LibreFolio_developer_journal/Release_2/phases/29_i18nAudit/plan-phase00I18nAudit.prompt.md`, S18-S19 (A, B).
 */

import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {validateRuns, waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';
import {SUPPORTED_LANGUAGES, t as catalogueText} from '../fixtures/i18n-data';
import {mkdirSync, rmSync, writeFileSync} from 'fs';
import path from 'path';

const API = '/api/v1';
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const VALIDATE_PATH = `${API}/transactions/validate`;
const GENERIC = 'broker_generic_csv';
/** Mirror of `AUTO_VALIDATE_THRESHOLD` in TransactionBulkModal.svelte: above it an edit does not validate. */
const AUTO_VALIDATE_THRESHOLD = 50;
/** The editor's page size in a fresh browser context (`defaultPageSize`). */
const EDITOR_PAGE_SIZE = 25;
const UI_TIMEOUT = 10_000;

type UploadedInfo = {file_id: string; filename: string; uploaded_at: string; target_broker_id: number | null};
type ParseResponse = {
    file_id: string;
    transactions: Array<{description?: string | null}>;
    warnings: unknown[];
    field_todos?: Array<{tx_index: number; field: string; severity: string; reason_code: string; message: string}>;
};
type ValidatePayload = {creates?: unknown[]; updates?: unknown[]; deletes?: unknown[]};

/** Margin on "uploaded after the broker was created": the server and the browser share this machine's clock. */
const CLOCK_SLACK_MS = 1_000;

/** Where a BRIM todo or notice finds its wording: `importWizard.brimNotice.<reason_code>`. */
const BRIM_NOTICE_NAMESPACE = 'importWizard.brimNotice.';
/** The generic CSV plugin's blocker (`broker_generic_csv.py`), worded by the catalogue (decision B). */
const WORDED_CODE = 'corporate_action';
/** A reason code no catalogue words: its message is the plugin's, whatever the UI language. */
const UNWORDED_CODE = 's19_probe_unworded';

/** A todo to add to a parse response, on the transaction whose description it names. */
type InventedTodo = {description: string; field: string; severity: 'blocker' | 'warning'; reason_code: string; message: string};

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

/** A broker this test owns. The name goes through `uniqueSuffix()`: `brokers.name` is uniquely indexed. */
async function createOwnedBroker(page: Page, name: string): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', allow_cash_overdraft: true, default_import_plugin: GENERIC}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    return created.broker_id;
}

/**
 * Delete the BRIM files this test put on its broker, then the broker. Only the files uploaded since
 * the broker was created: a broker id reused from an earlier run can arrive with that run's leftovers.
 */
async function deleteOwnedBrokerAndFiles(page: Page, brokerId: number, ownedSince: number): Promise<void> {
    const failures: string[] = [];
    try {
        const listed = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
        const files = listed.ok() ? ((await listed.json()) as UploadedInfo[]) : [];
        if (!listed.ok()) failures.push(`list the BRIM files of broker ${brokerId}: HTTP ${listed.status()}`);
        for (const file of files.filter((f) => f.target_broker_id === brokerId)) {
            if (!(Date.parse(file.uploaded_at) >= ownedSince - CLOCK_SLACK_MS)) continue;
            const response = await page.request.delete(`${API}/brokers/import/files/${file.file_id}`);
            if (!response.ok()) failures.push(`BRIM file ${file.file_id}: HTTP ${response.status()}`);
        }
    } catch (error) {
        failures.push(`BRIM files of broker ${brokerId}: ${String(error)}`);
    }
    try {
        const response = await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || !body?.results?.find((result) => result.id === brokerId)?.success) failures.push(`broker ${brokerId}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    } catch (error) {
        failures.push(`broker ${brokerId}: ${String(error)}`);
    }
    expect(failures, 'cleanup removes the BRIM files and the broker this test created').toEqual([]);
}

type CashRow = {date: string; type: 'DEPOSIT' | 'WITHDRAWAL'; amount: string; description: string};

/** A cash-only file in the format of generic_simple.csv: no asset, no correction, nothing to resolve. */
function writeCashCsv(filePath: string, rows: CashRow[]): string {
    mkdirSync(path.dirname(filePath), {recursive: true});
    writeFileSync(filePath, 'date,type,quantity,amount,currency,asset,description\n' + rows.map((row) => `${row.date},${row.type},0,${row.amount},EUR,,${row.description}`).join('\n') + '\n');
    return filePath;
}

/** `count` cash rows on consecutive days from `firstDay`, every amount its own; deposits outweigh withdrawals. */
function cashRows(count: number, firstDay: string, describe: (n: number) => string): CashRow[] {
    const start = Date.parse(`${firstDay}T00:00:00Z`);
    return Array.from({length: count}, (_, i) => {
        const n = i + 1;
        const date = new Date(start + i * 86_400_000).toISOString().slice(0, 10);
        return n % 2 === 1 ? {date, type: 'DEPOSIT', amount: (1000 + n * 7.13).toFixed(2), description: describe(n)} : {date, type: 'WITHDRAWAL', amount: (-(10 + n * 1.37)).toFixed(2), description: describe(n)};
    });
}

// ---------------------------------------------------------------------------
// Wizard
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** The wizard is open on step 1, settled. */
async function wizardOnStep1(page: Page) {
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await step1.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step1, 15_000);
}

/** The pending-file rows of the step-1 table (owned by this wizard instance). */
function pendingRows(page: Page) {
    return page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]');
}

/** Drop files on step 1, unfolding the drop zone first if it is folded (exactly one of the two is on screen). */
async function dropFiles(page: Page, files: string[]) {
    const step1 = page.getByTestId('import-wizard-step1');
    const uploader = step1.getByTestId('file-uploader');
    const uploadMore = page.getByTestId('import-wizard-upload-more');
    await expect(uploader.or(uploadMore)).toBeVisible({timeout: 5_000});
    if (!(await uploader.isVisible())) await uploadMore.click();
    await expect(uploader).toBeVisible({timeout: 5_000});
    await uploader.getByTestId('file-input').setInputFiles(files);
}

/** Assign every unassigned step-1 file to the owned broker through the "assign all" select. */
async function assignOwnedBroker(page: Page, brokerId: number) {
    await optionsClosed(page);
    await page.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option, `owned broker ${brokerId} must be offered by the "assign all" select`).toBeVisible({timeout: 8_000});
    await option.click();
    await optionsClosed(page);
    await expect(page.getByTestId('import-wizard-next')).toBeEnabled({timeout: 5_000});
}

/** The upload responses `action` produces on this page: exactly `expected` of them, each a 200. */
async function uploadsDuring(page: Page, expected: number, action: () => Promise<void>): Promise<UploadedInfo[]> {
    const replies: Array<Promise<{status: number; body: string}>> = [];
    const listener = (response: Response) => {
        if (response.request().method() === 'POST' && new URL(response.url()).pathname === UPLOAD_PATH) replies.push(response.text().then((body) => ({status: response.status(), body})));
    };
    // Armed before the action: a response is an edge, not a state.
    page.on('response', listener);
    try {
        await action();
        await expect.poll(() => replies.length, {message: `${expected} upload response(s) from one action`, timeout: 15_000}).toBe(expected);
    } finally {
        page.off('response', listener);
    }
    const settled = await Promise.all(replies);
    for (const {status, body} of settled) expect(status, `POST ${UPLOAD_PATH}: ${body}`).toBe(200);
    return settled.map(({body}) => JSON.parse(body) as UploadedInfo);
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/**
 * Extend the parse responses of this page with `invented` todos, each on the transaction whose description
 * it names (the F1-D4 injection, as a helper). Returns the set of descriptions that found their transaction,
 * filled as the parses go by.
 */
async function injectFieldTodos(page: Page, invented: InventedTodo[]): Promise<Set<string>> {
    const injected = new Set<string>();
    await page.route(
        (url) => /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/.test(url.pathname),
        async (route) => {
            const response = await route.fetch();
            const body = (await response.json()) as ParseResponse;
            const todos = invented.flatMap(({description, ...todo}) => {
                const txIndex = body.transactions.findIndex((tx) => tx.description === description);
                if (txIndex < 0) return [];
                injected.add(description);
                return [{tx_index: txIndex, ...todo}];
            });
            // A new body, so not the original headers: their content-length is the old body's.
            await route.fulfill({status: response.status(), contentType: 'application/json', body: JSON.stringify({...body, field_todos: [...(body.field_todos ?? []), ...todos]})});
        },
    );
    return injected;
}

/**
 * Step 1 → review for one cash-only CSV: drop it, assign the owned broker, upload it (Next), check that
 * step 2 selected it and nothing else of `alsoListed`, parse it, read past the notices, reach the review
 * with every row selected. Returns the upload and the parse response the page received.
 */
async function walkCsvToReview(page: Page, brokerId: number, csvPath: string, rows: number, alsoListed: string[] = []): Promise<{uploaded: UploadedInfo; parsed: ParseResponse; step4: Locator}> {
    await dropFiles(page, [csvPath]);
    await expect(pendingRows(page)).toHaveCount(1);
    await assignOwnedBroker(page, brokerId);
    const [uploaded] = await uploadsDuring(page, 1, async () => {
        await page.getByTestId('import-wizard-next').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
    });
    expect(uploaded.target_broker_id).toBe(brokerId);

    const step2 = page.getByTestId('import-wizard-step2');
    await waitForSettled(step2, 20_000);
    await expect(page.getByTestId(`dt-row-checkbox-${uploaded.file_id}`), 'the file uploaded in this session is selected').toHaveAttribute('data-state', 'checked', {timeout: 5_000});
    for (const fileId of alsoListed) await expect(page.getByTestId(`dt-row-checkbox-${fileId}`), `the file of an earlier import (${fileId}) is not selected`).toHaveAttribute('data-state', 'unchecked');

    const parseResponse = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === `${API}/brokers/import/files/${uploaded.file_id}/parse`, {timeout: 30_000});
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse).toBeEnabled({timeout: 5_000});
    await parse.click();
    const parsedResponse = await parseResponse;
    expect(parsedResponse.status(), `parse ${uploaded.filename}`).toBe(200);
    const parsed = (await parsedResponse.json()) as ParseResponse;
    expect(parsed.transactions, 'every row of the CSV is a transaction').toHaveLength(rows);
    await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForParseVerdict(page, 30_000);

    await page.getByTestId('import-wizard-continue').click();
    // The parse response, not a probe, says whether its notices ask for a confirmation.
    if (parsed.warnings.length > 0) {
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm).toBeVisible({timeout: 5_000});
        await confirm.click();
    }
    await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
    const step4 = page.getByTestId('import-wizard-step4');
    await waitForSettled(step4, 30_000);
    await expect(step4, 'every row of the CSV is selected in the review').toHaveAttribute('data-selected-count', String(rows), {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: 15_000});
    return {uploaded, parsed, step4};
}

/** The wizard handed over and closed: the editor underneath, settled. */
async function editorAfterHandoff(page: Page): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 15_000});
    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(root, 30_000);
    return root;
}

/** Never Save All: close the editor through its unsaved-changes guard and discard. */
async function closeEditorWithoutSaving(page: Page, root: Locator) {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: UI_TIMEOUT});
}

// ---------------------------------------------------------------------------
// Editor
// ---------------------------------------------------------------------------

/** Every POST /transactions/validate of this page from now on, in order. */
function recordValidations(page: Page): {requests: Request[]; stop: () => void} {
    const requests: Request[] = [];
    const onRequest = (request: Request) => {
        if (request.method() === 'POST' && new URL(request.url()).pathname === VALIDATE_PATH) requests.push(request);
    };
    // Armed before the action, like every recorder here.
    page.on('request', onRequest);
    return {requests, stop: () => page.off('request', onRequest)};
}

function createsOf(request: Request): number {
    return ((request.postDataJSON() as ValidatePayload).creates ?? []).length;
}

/** The editor row holding `description` on the page shown. */
function editorRow(root: Locator, description: string): Locator {
    return root.getByTestId('tx-bulk-body').locator('tr[data-row-id]').filter({hasText: description});
}

/** Hover an editor row and run one of its actions through the kebab menu. */
async function clickRowAction(row: Locator, actionId: string) {
    const page = row.page();
    await row.hover();
    const kebab = row.getByTestId(/^row-actions-/);
    await expect(kebab).toBeVisible({timeout: 5_000});
    await kebab.click();
    const action = page.getByTestId(`context-menu-action-${actionId}`);
    await expect(action).toBeVisible({timeout: 5_000});
    await action.click();
}

/** Show the grid's first page, proved by the row that sorts first being on it. */
async function showFirstPage(root: Locator, firstDescription: string) {
    const input = root.getByTestId('tx-bulk-body').getByTestId('data-table-pagination').getByRole('textbox');
    await expect(input).toBeVisible({timeout: UI_TIMEOUT});
    await input.fill('1');
    await input.press('Enter');
    await expect(input).toHaveValue('1');
    await expect(editorRow(root, firstDescription)).toHaveCount(1, {timeout: UI_TIMEOUT});
}

/** The goto buttons of a todo banner, its list unfolded first when it is folded (asked, never toggled blind). */
async function bannerGotos(banner: Locator, toggleTestId: string): Promise<Locator> {
    await expect(banner).toBeVisible({timeout: UI_TIMEOUT});
    const gotos = banner.getByTestId('tx-bulk-todo-goto');
    if (!(await gotos.first().isVisible())) {
        const toggle = banner.getByTestId(toggleTestId);
        await expect(toggle, `the banner lists its entries, or folds them behind ${toggleTestId}`).toBeVisible({timeout: 5_000});
        await toggle.click();
    }
    return gotos;
}

/**
 * Click one goto from the grid's first page and prove where it led: the row it names was not on that
 * page, is on screen after the click, highlighted, and is one of `targets`. Returns the target found.
 */
async function followGoto(root: Locator, goto: Locator, firstDescription: string, targets: string[]): Promise<string> {
    const rowId = await goto.getAttribute('data-row-id');
    expect(rowId, 'a goto names its row: data-row-id is the op tempId').toBeTruthy();
    const row = root.getByTestId('tx-bulk-body').locator(`tr[data-row-id="${rowId}"]`);
    await showFirstPage(root, firstDescription);
    await expect(row, 'the target sits on a later page: the first page does not show it').toHaveCount(0);

    await goto.click();
    await expect(row, 'the goto pages the grid to its row').toBeVisible({timeout: UI_TIMEOUT});
    await expect(row, 'the goto highlights its row').toHaveAttribute('data-highlighted', 'true');
    // The row is on screen (barrier above): its text is final.
    const rowText = (await row.textContent()) ?? '';
    const reached = targets.filter((target) => rowText.includes(target));
    expect(reached, `the goto leads to one of ${JSON.stringify(targets)}; the row reads: ${rowText}`).toHaveLength(1);
    return reached[0];
}

/**
 * The entry of an unfolded todo banner for the editor row holding `description`: the goto whose `data-row-id`
 * is that row's — found by the row, never by the entry's text, which is what is under test.
 */
async function bannerEntryFor(root: Locator, banner: Locator, description: string): Promise<Locator> {
    const row = editorRow(root, description);
    await expect(row, `the editor shows the row "${description}"`).toHaveCount(1, {timeout: UI_TIMEOUT});
    const rowId = await row.getAttribute('data-row-id');
    expect(rowId, 'an editor row carries its op tempId as data-row-id').toBeTruthy();
    const entry = banner.locator(`[data-testid="tx-bulk-todo-goto"][data-row-id="${rowId}"]`);
    await expect(entry, `the banner has one entry for the row "${description}"`).toHaveCount(1, {timeout: 5_000});
    return entry;
}

/**
 * The catalogue's wording of `key` in the language the page is drawn in: `<html lang>`, which the root layout
 * keeps on the language shown, read once `data-i18n-ready` says its dictionary is in — the reading of
 * `risk-lab.spec.ts`, replicated rather than imported (a spec does not reach into another spec's helpers).
 * A key that catalogue lacks fails here, by name.
 */
async function catalogueWording(page: Page, key: string): Promise<string> {
    const html = page.locator('html');
    await expect(html).toHaveAttribute('data-i18n-ready', 'true');
    const lang = ((await html.getAttribute('lang')) ?? '').split('-')[0];
    const wording = catalogueText(lang, key);
    expect(wording, `the "${lang}" catalogue has no message for ${key}`).not.toBe(key);
    return wording;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Bulk editor after an import hand-over (F1: D4, D5)', () => {
    let ownedBrokerId: number | undefined;
    let ownedSince = 0;
    let writtenFiles: string[] = [];

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        writtenFiles = [];
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page}) => {
        for (const file of writtenFiles) rmSync(file, {force: true});
        if (ownedBrokerId === undefined) return;
        await page.goto('about:blank');
        await deleteOwnedBrokerAndFiles(page, ownedBrokerId, ownedSince);
    });

    /** Own a broker, then open the wizard from the toolbar: the broker exists before the wizard reads the list. */
    async function startOnOwnedBroker(page: Page, tag: string): Promise<number> {
        ownedSince = Date.now();
        const brokerId = await createOwnedBroker(page, `Bulk handoff ${tag} ${uniqueSuffix()}`);
        ownedBrokerId = brokerId;
        await goToTransactions(page);
        await page.getByTestId('tx-import-button').click();
        await wizardOnStep1(page);
        return brokerId;
    }

    test('F1-D5: an import of more than 50 rows is validated once on hand-over; an edit is not; the next import is validated once more', async ({page}, testInfo) => {
        test.setTimeout(180_000);
        const brokerId = await startOnOwnedBroker(page, 'D5');
        const marker = uniqueSuffix();
        const firstCount = AUTO_VALIDATE_THRESHOLD + 5;
        const secondCount = 3;
        const describeFirst = (n: number) => `F1 D5 first ${String(n).padStart(2, '0')} ${marker}`;
        const describeSecond = (n: number) => `F1 D5 second ${String(n).padStart(2, '0')} ${marker}`;
        const firstCsv = writeCashCsv(testInfo.outputPath(`f1-d5-first-${marker}.csv`), cashRows(firstCount, '2024-02-01', describeFirst));
        const secondCsv = writeCashCsv(testInfo.outputPath(`f1-d5-second-${marker}.csv`), cashRows(secondCount, '2024-06-01', describeSecond));
        writtenFiles.push(firstCsv, secondCsv);

        // ① The first import: 55 rows, above the threshold.
        const first = await walkCsvToReview(page, brokerId, firstCsv, firstCount);
        const root = page.getByTestId('tx-bulk-modal-root');
        await expect(root, 'the editor is open beneath the wizard').toBeAttached();
        const runsBefore = await validateRuns(root);
        const validations = recordValidations(page);
        try {
            await page.getByTestId('import-wizard-import').click();
            await editorAfterHandoff(page);
            await expect(root.getByTestId('tx-bulk-auto-off'), `premise: ${firstCount} rows are above the threshold, the automatic validation is off`).toBeVisible();

            await expect.poll(() => validations.requests.length, {message: `the hand-over of ${firstCount} rows runs ONE validation (POST ${VALIDATE_PATH}), above the threshold too`, timeout: 15_000}).toBe(1);
            await expect.poll(() => validateRuns(root), {message: 'the validation completes', timeout: 20_000}).toBeGreaterThan(runsBefore);
            await waitForSettled(root, 20_000);
            expect(validations.requests.length, 'exactly one: nothing else queued behind the import').toBe(1);
            expect(createsOf(validations.requests[0]), 'the validation covers every imported row, as "Validate now" does').toBe(firstCount);
            const runsAfterImport = await validateRuns(root);

            // ② A plain edit — a clone through the row menu, no form — above the threshold: no validation.
            const source = editorRow(root, describeFirst(1));
            await expect(source, 'the earliest row is on the first page').toHaveCount(1, {timeout: UI_TIMEOUT});
            await clickRowAction(source, 'clone');
            // Barrier: the clone is in the grid, next to its source (same day): the draft has changed.
            await expect(editorRow(root, describeFirst(1)), 'the clone sits next to its source').toHaveCount(2, {timeout: UI_TIMEOUT});
            // A validation the edit had scheduled would be pending now (data-busy) and counted once done.
            await waitForSettled(root, 20_000);
            expect(validations.requests.length, 'an edit above the threshold does not validate').toBe(1);
            expect(await validateRuns(root), 'no run completed since the import').toBe(runsAfterImport);

            // ③ A second import, from the editor: one more validation, over the whole editor.
            await root.getByTestId('tx-bulk-import').click();
            await wizardOnStep1(page);
            await walkCsvToReview(page, brokerId, secondCsv, secondCount, [first.uploaded.file_id]);
            const runsBeforeSecond = await validateRuns(root);
            await page.getByTestId('import-wizard-import').click();
            await editorAfterHandoff(page);
            await expect.poll(() => validations.requests.length, {message: 'the second hand-over runs one more validation', timeout: 15_000}).toBe(2);
            await expect.poll(() => validateRuns(root), {message: 'the second validation completes', timeout: 20_000}).toBeGreaterThan(runsBeforeSecond);
            await waitForSettled(root, 20_000);
            expect(validations.requests.length, 'exactly one more').toBe(2);
            expect(createsOf(validations.requests[1]), 'the whole editor: both imports and the clone').toBe(firstCount + 1 + secondCount);
        } finally {
            validations.stop();
        }

        await closeEditorWithoutSaving(page, root);
    });

    test('F1-D4: every entry of the todo banners is a goto button that pages the grid to its row and highlights it', async ({page}, testInfo) => {
        test.setTimeout(150_000);
        const brokerId = await startOnOwnedBroker(page, 'D4');
        const marker = uniqueSuffix();
        const rows = EDITOR_PAGE_SIZE + 5;
        const describe = (n: number) => `F1 D4 row ${String(n).padStart(2, '0')} ${marker}`;
        const csv = writeCashCsv(testInfo.outputPath(`f1-d4-${marker}.csv`), cashRows(rows, '2024-03-01', describe));
        writtenFiles.push(csv);
        // The rows dated last: the grid sorts by date, so they are on its second page.
        const blockerTarget = describe(rows);
        const warningTargets = [describe(rows - 3), describe(rows - 2)];
        const firstRow = describe(1);
        const invented = [
            {description: blockerTarget, field: 'cost_basis_override', severity: 'blocker', reason_code: 'f1_probe_blocker', message: `F1 probe blocker ${marker}`},
            {description: warningTargets[0], field: 'quantity', severity: 'warning', reason_code: 'f1_probe_warning', message: `F1 probe warning one ${marker}`},
            {description: warningTargets[1], field: 'description', severity: 'warning', reason_code: 'f1_probe_warning', message: `F1 probe warning two ${marker}`},
        ];

        // The parse response of this test's file gains the invented todos, each on the row it names.
        const injected = new Set<string>();
        await page.route(
            (url) => /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/.test(url.pathname),
            async (route) => {
                const response = await route.fetch();
                const body = (await response.json()) as ParseResponse;
                const todos = invented.flatMap(({description, ...todo}) => {
                    const txIndex = body.transactions.findIndex((tx) => tx.description === description);
                    if (txIndex < 0) return [];
                    injected.add(description);
                    return [{tx_index: txIndex, ...todo}];
                });
                // A new body, so not the original headers: their content-length is the old body's.
                await route.fulfill({status: response.status(), contentType: 'application/json', body: JSON.stringify({...body, field_todos: [...(body.field_todos ?? []), ...todos]})});
            },
        );

        const {parsed} = await walkCsvToReview(page, brokerId, csv, rows);
        expect([...injected], 'every invented todo found the row it names').toEqual(invented.map((todo) => todo.description));
        expect(
            parsed.field_todos?.map((todo) => todo.reason_code),
            'the page received the invented todos',
        ).toEqual(invented.map((todo) => todo.reason_code));
        await page.getByTestId('import-wizard-import').click();
        const root = await editorAfterHandoff(page);
        await showFirstPage(root, firstRow);

        // The blockers banner: one entry, a goto to the blocker's row.
        const blockers = root.getByTestId('tx-bulk-todo-blockers');
        const blockerGotos = await bannerGotos(blockers, 'tx-bulk-todo-blockers-toggle');
        await expect(blockerGotos, 'each entry of the blockers banner is a tx-bulk-todo-goto button').toHaveCount(1, {timeout: 5_000});
        await expect(blockers).toContainText(invented[0].message);
        expect(await followGoto(root, blockerGotos.first(), firstRow, [blockerTarget])).toBe(blockerTarget);

        // The warnings banner: the same list, one goto per warning.
        const warnings = root.getByTestId('tx-bulk-todo-warnings');
        const warningGotos = await bannerGotos(warnings, 'tx-bulk-todo-warnings-toggle');
        await expect(warningGotos, 'each entry of the warnings banner is a tx-bulk-todo-goto button').toHaveCount(2, {timeout: 5_000});
        await expect(warnings).toContainText(invented[1].message);
        await expect(warnings).toContainText(invented[2].message);
        const reached: string[] = [];
        for (let i = 0; i < 2; i++) reached.push(await followGoto(root, warningGotos.nth(i), firstRow, warningTargets));
        expect([...reached].sort(), 'the two warnings lead to their two rows').toEqual([...warningTargets].sort());

        await closeEditorWithoutSaving(page, root);
    });

    test('S19 (A, B): a todo whose reason code the catalogue words reads in the UI language in both banners; an unworded code keeps the plugin message', async ({page}, testInfo) => {
        test.setTimeout(120_000);
        const unwordedKey = `${BRIM_NOTICE_NAMESPACE}${UNWORDED_CODE}`;
        // Verified, not assumed: no catalogue words the probe code, so its entries can only read the plugin's message.
        expect(
            SUPPORTED_LANGUAGES.filter((lang) => catalogueText(lang, unwordedKey) !== unwordedKey),
            `premise: no catalogue has ${unwordedKey}`,
        ).toEqual([]);

        const brokerId = await startOnOwnedBroker(page, 'S19');
        const marker = uniqueSuffix();
        const rows = 4;
        const describe = (n: number) => `S19 todo wording row ${String(n).padStart(2, '0')} ${marker}`;
        const csv = writeCashCsv(testInfo.outputPath(`s19-todo-wording-${marker}.csv`), cashRows(rows, '2024-04-01', describe));
        writtenFiles.push(csv);
        /** A todo on row `n` whose message carries its own mark: whether the mark reaches the screen says whose words the entry reads. */
        const probe = (n: number, severity: 'blocker' | 'warning', reasonCode: string) => {
            const mark = uniqueSuffix();
            // Fields the correction step does not own (a blocker on the cost basis, a warning on the description): both reach the editor.
            const todo: InventedTodo = {description: describe(n), field: severity === 'blocker' ? 'cost_basis_override' : 'description', severity, reason_code: reasonCode, message: `Plugin wording of a ${reasonCode} ${severity} ${mark}`};
            return {todo, mark};
        };
        const probes = {
            wordedBlocker: probe(1, 'blocker', WORDED_CODE),
            unwordedBlocker: probe(2, 'blocker', UNWORDED_CODE),
            wordedWarning: probe(3, 'warning', WORDED_CODE),
            unwordedWarning: probe(4, 'warning', UNWORDED_CODE),
        };
        const invented = Object.values(probes).map((each) => each.todo);

        const injected = await injectFieldTodos(page, invented);
        const {parsed} = await walkCsvToReview(page, brokerId, csv, rows);
        expect([...injected], 'every invented todo found the row it names').toEqual(invented.map((todo) => todo.description));
        expect(
            parsed.field_todos?.map((todo) => todo.reason_code),
            'the page received the invented todos, and only them',
        ).toEqual(invented.map((todo) => todo.reason_code));
        await page.getByTestId('import-wizard-import').click();
        const root = await editorAfterHandoff(page);

        // Both banners unfolded; every entry found by its row.
        const blockers = root.getByTestId('tx-bulk-todo-blockers');
        await expect(await bannerGotos(blockers, 'tx-bulk-todo-blockers-toggle'), 'one blockers entry per blocker').toHaveCount(2, {timeout: 5_000});
        const warnings = root.getByTestId('tx-bulk-todo-warnings');
        await expect(await bannerGotos(warnings, 'tx-bulk-todo-warnings-toggle'), 'one warnings entry per warning').toHaveCount(2, {timeout: 5_000});
        const entries = {
            wordedBlocker: await bannerEntryFor(root, blockers, probes.wordedBlocker.todo.description),
            unwordedBlocker: await bannerEntryFor(root, blockers, probes.unwordedBlocker.todo.description),
            wordedWarning: await bannerEntryFor(root, warnings, probes.wordedWarning.todo.description),
            unwordedWarning: await bannerEntryFor(root, warnings, probes.unwordedWarning.todo.description),
        };

        // ① No catalogue words the probe code: its entries read the plugin's message, never a raw key.
        for (const which of ['unwordedBlocker', 'unwordedWarning'] as const) {
            await expect(entries[which], `${which} (${UNWORDED_CODE}): no key, the plugin's message`).toContainText(probes[which].todo.message);
            await expect(entries[which], `${which} (${UNWORDED_CODE}): never a raw i18n key`).not.toContainText(BRIM_NOTICE_NAMESPACE);
        }

        // ② corporate_action has a key: the plugin's message gives way to it, in both banners. Soft, so that one
        //    banner's verdict does not hide the other's.
        for (const which of ['wordedBlocker', 'wordedWarning'] as const) {
            await expect.soft(entries[which], `${which} (${WORDED_CODE}): the plugin's message gives way to the catalogue's wording`).not.toContainText(probes[which].mark);
            await expect.soft(entries[which], `${which} (${WORDED_CODE}): never a raw i18n key`).not.toContainText(BRIM_NOTICE_NAMESPACE);
        }

        // ③ … and what replaces it is the catalogue's wording, in the language the page is drawn in.
        const wording = await catalogueWording(page, `${BRIM_NOTICE_NAMESPACE}${WORDED_CODE}`);
        for (const which of ['wordedBlocker', 'wordedWarning'] as const) {
            await expect(entries[which], `${which} (${WORDED_CODE}): the catalogue's wording, in the UI language`).toContainText(wording);
        }

        await closeEditorWithoutSaving(page, root);
    });
});
