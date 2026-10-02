/**
 * Import Wizard — report sets (phase C2 of the Danske Bank workstream, issue 26)
 *
 * A report-set plugin reads several exports of one bank as one import: for Danske Bank the
 * custody transactions (XLSX) and the cash statement (CSV). The files uploaded together in
 * one step-1 session share a `batch_id` (C1), and in the wizard that batch is the set:
 *
 *   ① Upload  — after the upload the wizard previews each set; an incomplete one keeps the
 *               wizard on step 1 with a warning per missing role, and a second Next goes on.
 *   ② Select  — the set is one card (`report-set-card`): its members, what is missing, the
 *               note on the broker history, the timeline; "upload the missing file" (same
 *               batch) and "exclude from the import". A selected set that is not complete
 *               blocks the analysis (`import-wizard-set-blocks`).
 *   ③ Analyze — the set is ONE row: combined first (`POST /sets/combine`), then the combined
 *               file is parsed; its detail shows the pairing counts of the combine.
 *   ④ Review  — the rows dated before the broker history (H0) are already represented in
 *               LibreFolio: hidden behind a counter, shown on request, never selectable.
 *
 * Data: every test creates its own broker over the API and uploads the repository's
 * synthetic samples (`danske_bank-custody.xlsx`, `danske_bank-cash.csv`,
 * `generic_simple.csv` — invented values). The facts of the main set on a fresh broker come
 * from the backend phase B (RS-B01 in test_brim_api.py, test_brim_danske_bank.py): preview
 * complete on 2020-02-03…2020-06-26; combine outcomes pair 12 · standalone 15 · summarized 7
 * · deferred 1; the combined parse has 27 transactions, H0 2020-02-03, 7 rows before it, 11
 * trades whose charges ask for a decision in the corrections step.
 *
 * Cleanup: nothing is committed (the tests stop at the review), so what a test writes is its
 * broker and the BRIM files on it — the uploads and the combined file. afterEach leaves the
 * page first (about:blank, so the wizard does not react while its files go away), then
 * deletes the files uploaded to the owned broker since the test created it, and the broker.
 * Scoped to what the test created: safe in parallel, and blind to the leftovers of earlier
 * runs that a reused broker id can bring along (the lane's files outlive a repopulate).
 *
 * Each scenario gives its first C2 element a short budget (`C2_FIRST`), so before the
 * implementation it fails fast and on the piece that is missing.
 *
 * Phase C3 — "Align with the bank" (`gapFix`), after the review, and the badges of the files:
 *
 *   ⑤ Gap-fix — Import asks `POST /brokers/import/gap-fix` (one request per broker and plugin
 *               with truth points) what LibreFolio will lack against the bank. With something to
 *               show, the wizard opens the step: per truth point the comparison, the corrections
 *               (selected by default, D-S14) and the verifications. Back and Import again
 *               recompute. Continue hands the review's rows and the selected corrections, tagged
 *               `gap_fix`, to the editor.
 *   Files     — FilesTable (the files page and the broker's import files) badges a file:
 *               combined · stale · usedInCombined · set · incomplete.
 *
 *   R5 Import → the step: the opening deposit of a fresh broker, selected; Back and Import again
 *      make a second request; Continue gives the editor as many `gap_fix` rows as were selected.
 *   R6 every correction unticked → none reaches the editor, the imported rows do.
 *   R7 a lone generic CSV never calls the gap-fix and goes straight to the editor: a guard, green
 *      before C3 too, so the new step never touches single-file plugins.
 *   R8 badges, with the files uploaded (batch_id in the form) and combined over the API: combined
 *      on the combined file; usedInCombined and set on its originals; set and incomplete on a
 *      custody export uploaded alone.
 *   R9 — the guide step on the gap-fix, desktop and mobile — is tx-import-report-set-guide.spec.ts.
 *
 * C3 facts of the main set on a fresh broker (backend phase B, test_brim_danske_bank.py,
 * test_checkpoint_and_verification): one checkpoint, opening, on 2020-02-02 (cash EUR 2699.50, three
 * positions) and one verification on 2020-06-26. H0 is 2020-02-03 and the selection only holds rows
 * on or after it, so the cash correction is a DEPOSIT of 2699.50 EUR on 2020-02-02 whatever is
 * selected. Positions give corrections only for resolved assets, which depends on this lane's
 * database: the scenarios never count on it, and never create an asset (a global row that parallel
 * workers and reruns would share).
 *
 * Getting Import enabled. The review keeps Import disabled while a selected row points at an
 * unresolved asset, and whether the synthetic titles resolve here is unknown. So R5 and R6 keep
 * selected only the rows that carry no asset — the 5 cash movements on or after H0 — through the
 * review's own controls (deselect all, the asset column filter on "no asset", select visible):
 * nothing left to resolve, nothing created, and the opening deposit is proposed all the same.
 *
 * Leaving the editor. Nothing is ever saved: the editor is closed through its unsaved-changes
 * guard (close, then discard), as tx-import-flow does, before afterEach cleans up.
 *
 * Each C3 scenario gives its first new element a short budget (`C3_FIRST`).
 *
 * Phase F1 — the developer's review (2026-10-02):
 *
 *   F1-D1 with the step-1 set warning shown, a mousedown outside the drop zone leaves it open (it
 *         used to fold, moving Next under the pointer and losing the click), and ONE Next reaches
 *         step 2.
 */

import {expect, test, type Locator, type Page, type Request, type Response} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {TEST_USER} from '../fixtures/test-users';
import {randomUUID} from 'crypto';
import {mkdirSync, readFileSync, writeFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const COMBINE_PATH = `${API}/brokers/import/sets/combine`;
const GAP_FIX_PATH = `${API}/brokers/import/gap-fix`;
const PARSE_PATH = /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/;
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
const SAMPLES = path.resolve(SPEC_DIR, '../../../backend/app/services/brim_providers/sample_reports');
const CUSTODY_XLSX = path.join(SAMPLES, 'danske_bank-custody.xlsx');
const CASH_CSV = path.join(SAMPLES, 'danske_bank-cash.csv');
const GENERIC_CSV = path.join(SAMPLES, 'generic_simple.csv');
const DANSKE = 'broker_danske_bank';
const GENERIC = 'broker_generic_csv';
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** The main synthetic set on a fresh broker (backend phase B). */
const MAIN_SET = {
    transactions: 27,
    beforeHistory: 7,
    trades: 11,
    outcomes: {pair: 12, standalone: 15, summarized: 7, deferred: 1, excluded: 0},
} as const;

/** Budget of the first C2 element of a scenario: before the implementation it is the one that fails. */
const C2_FIRST = 8_000;

/** The C3 facts of the main set on a fresh broker (backend phase B). */
const MAIN_TRUTH = {
    checkpoint: {asOf: '2020-02-02', kind: 'opening'},
    deposit: {currency: 'EUR', amount: 2699.5},
    verification: '2020-06-26',
    /** The rows without an asset on or after H0: DEPOSIT 03-20, FEE 03-31, TAX and WITHDRAWAL 06-10, FEE 06-30. */
    cashRowsInHistory: 5,
} as const;

/** Budget of the first C3 element of a scenario: before the implementation it is the one that fails. */
const C3_FIRST = 8_000;

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

type UploadedInfo = {file_id: string; filename: string; uploaded_at: string; target_broker_id: number | null; batch_id?: string | null};

/**
 * Margin on "uploaded after the broker was created": the server and the browser share this
 * machine's clock, and `uploaded_at` is an ISO instant — a second covers any rounding.
 */
const CLOCK_SLACK_MS = 1_000;

/** A broker this test owns. The name goes through `uniqueSuffix()`: `brokers.name` is uniquely indexed. */
async function createOwnedBroker(page: Page, name: string, extra: Record<string, unknown> = {}): Promise<number> {
    const response = await page.request.post(`${API}/brokers`, {data: [{name, allow_cash_overdraft: true, ...extra}]});
    expect(response.ok(), `create owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null}>};
    const created = results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(results)}`);
    return created.broker_id;
}

/** The BRIM files stored on one broker; the list also returns legacy files with no broker, so the target is filtered. */
async function brimFilesOn(page: Page, brokerId: number): Promise<UploadedInfo[]> {
    const response = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
    expect(response.ok(), `list the BRIM files of broker ${brokerId}: HTTP ${response.status()}`).toBe(true);
    const files = (await response.json()) as UploadedInfo[];
    return files.filter((file) => file.target_broker_id === brokerId);
}

/**
 * Delete the BRIM files this test put on its broker (uploads and combined files), then the broker.
 *
 * Only the files uploaded since the broker was created: the files of a lane outlive a database
 * repopulate, so a broker id reused from an earlier run can arrive with that run's leftovers
 * already attached. Those predate the broker, are not this test's, and are left alone.
 */
async function deleteOwnedBrokerAndFiles(page: Page, brokerId: number, ownedSince: number): Promise<void> {
    const failures: string[] = [];
    try {
        for (const file of await brimFilesOn(page, brokerId)) {
            if (!(Date.parse(file.uploaded_at) >= ownedSince - CLOCK_SLACK_MS)) continue;
            const response = await page.request.delete(`${API}/brokers/import/files/${file.file_id}`);
            if (!response.ok()) failures.push(`BRIM file ${file.file_id}: HTTP ${response.status()}`);
        }
    } catch (error) {
        failures.push(`list the BRIM files of broker ${brokerId}: ${String(error)}`);
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

// ---------------------------------------------------------------------------
// Responses: armed before the action, read after it
// ---------------------------------------------------------------------------

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

type JsonCall = {path: string; status: number; request: unknown; body: unknown};

/** Record the JSON POSTs whose path matches, from now until the returned `stop()`. */
function recordJsonPosts(page: Page, match: (pathname: string) => boolean): () => Promise<JsonCall[]> {
    const calls: Array<Promise<JsonCall>> = [];
    const listener = (response: Response) => {
        const request = response.request();
        const pathname = new URL(response.url()).pathname;
        if (request.method() !== 'POST' || !match(pathname)) return;
        calls.push(
            response.text().then((text) => {
                let body: unknown = text;
                try {
                    body = JSON.parse(text);
                } catch {
                    // Not JSON: kept as text, so a failure can quote it.
                }
                return {path: pathname, status: response.status(), request: request.postDataJSON() as unknown, body};
            }),
        );
    };
    page.on('response', listener);
    return async () => {
        page.off('response', listener);
        return Promise.all(calls);
    };
}

function expectUuid(value: string | null | undefined, what: string): string {
    expect(typeof value === 'string' && UUID_PATTERN.test(value), `${what}: ${JSON.stringify(value)} must be a UUID`).toBe(true);
    return value as string;
}

function uploadNamed(uploaded: UploadedInfo[], filename: string): UploadedInfo {
    const found = uploaded.filter((file) => file.filename === filename);
    expect(found, `exactly one upload of ${filename} among ${JSON.stringify(uploaded.map((file) => file.filename))}`).toHaveLength(1);
    return found[0];
}

// ---------------------------------------------------------------------------
// Wizard
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 10_000});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open the wizard via the toolbar Import button; wait until step 1 has settled. */
async function openImportWizard(page: Page) {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await step1.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step1, 15_000);
}

/** The pending-file rows of the step-1 table (owned by this wizard instance). */
function pendingRows(page: Page) {
    return page.getByTestId('import-wizard-step1').locator('tbody tr[data-row-id]');
}

/**
 * Drop files on step 1. The drop zone folds as soon as it holds files and only the
 * "upload more" button is left, so it is unfolded first — asking for its state rather than
 * clicking blind (the two are exclusive: exactly one of them is on screen).
 */
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

function setWarning(page: Page, role: string): Locator {
    return page.locator(`[data-testid="import-wizard-step1-set-warning"][data-role="${role}"]`);
}

/** The card of one set, by its key: broker, plugin and upload batch (`reportSetKey`). */
function setCard(page: Page, brokerId: number, batchId: string): Locator {
    return page.getByTestId('import-wizard-step2').locator(`[data-testid="report-set-card"][data-set-key="set:${brokerId}:${DANSKE}:${batchId}"]`);
}

function cardMember(card: Locator, fileId: string): Locator {
    return card.locator(`[data-testid="report-set-member"][data-file-id="${fileId}"]`);
}

/**
 * Make sure the card body is open. Whether a card starts open is the product's call, so the
 * spec asks before toggling (rule 14) — and only once the card has settled on a terminal
 * status, when the members it shows are the final ones. Every set has at least one member.
 */
async function openCard(card: Locator) {
    await expect(card).toHaveAttribute('data-set-status', /^(complete|incomplete|error)$/, {timeout: 15_000});
    const member = card.getByTestId('report-set-member').first();
    if (!(await member.isVisible())) await card.getByTestId('report-set-toggle').click();
    await expect(member).toBeVisible({timeout: 5_000});
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/** Show every row of a DataTable inside `scope` on one page (page size ∞). */
async function showAllRows(page: Page, scope: Locator) {
    const pagination = scope.getByTestId('data-table-pagination');
    await expect(pagination).toBeVisible({timeout: 5_000});
    await pagination.getByTestId('pagination-size-trigger').click();
    await page.getByTestId('pagination-size-option-0').click();
    await expect(page.getByTestId('pagination-size-menu')).toHaveCount(0, {timeout: 5_000});
}

// ---------------------------------------------------------------------------
// C3: the gap-fix step and the editor after it
// ---------------------------------------------------------------------------

type GapFixRequestBody = {
    broker_id: number;
    plugin_code: string;
    checkpoints: Array<{as_of: string; kind: string}>;
    verifications: Array<{as_of: string}>;
    selection: Array<{broker_id: number}>;
    pending_creates: unknown[];
    pending_delete_tx_ids: number[];
};
type GapFixResponseBody = {checkpoints: Array<{as_of: string; proposals: Array<{type: string; date: string; cash?: {code: string; amount: string} | null}>}>};

/** Every POST /gap-fix of this page from now on: a live count of the requests, and the calls once stopped. */
function recordGapFixPosts(page: Page): {count: () => number; stop: () => Promise<JsonCall[]>} {
    let requests = 0;
    const onRequest = (request: Request) => {
        if (request.method() === 'POST' && new URL(request.url()).pathname === GAP_FIX_PATH) requests += 1;
    };
    // Armed before the action, like every recorder here.
    page.on('request', onRequest);
    const stopCalls = recordJsonPosts(page, (pathname) => pathname === GAP_FIX_PATH);
    return {
        count: () => requests,
        stop: async () => {
            page.off('request', onRequest);
            return stopCalls();
        },
    };
}

/**
 * R1's corridor without its C2 assertions: both exports in one step-1 session → one complete set →
 * its combined file parsed → the notices read past → every charge kept in the corrections → review.
 */
async function walkMainSetToReview(page: Page, brokerId: number): Promise<Locator> {
    await dropFiles(page, [CUSTODY_XLSX, CASH_CSV]);
    await expect(pendingRows(page)).toHaveCount(2);
    await assignOwnedBroker(page, brokerId);
    const uploaded = await uploadsDuring(page, 2, async () => {
        await page.getByTestId('import-wizard-next').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
    });
    const batchId = expectUuid(uploadNamed(uploaded, 'danske_bank-custody.xlsx').batch_id, 'batch_id of the step-1 session');

    const step2 = page.getByTestId('import-wizard-step2');
    await waitForSettled(step2, 20_000);
    const card = setCard(page, brokerId, batchId);
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card).toHaveAttribute('data-selected', 'all');
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse).toBeEnabled({timeout: 5_000});
    await parse.click();
    await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
    await waitForParseVerdict(page, 60_000);

    await page.getByTestId('import-wizard-continue').click();
    const confirm = page.getByTestId('import-wizard-warning-confirm');
    await expect(confirm).toBeVisible({timeout: 5_000});
    await confirm.click();
    await expect(currentStep(page)).toHaveAttribute('data-step-id', 'fix', {timeout: 30_000});
    await expect(page.getByTestId('fix-step-row')).toHaveCount(MAIN_SET.trades, {timeout: 10_000});
    await page.getByTestId('fix-step-accept-all').click();
    await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: 10_000});
    await page.getByTestId('import-wizard-fix-continue').click();
    await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
    const step4 = page.getByTestId('import-wizard-step4');
    await waitForSettled(step4, 30_000);
    return step4;
}

/**
 * Keep selected only the review rows that carry no asset: the set's cash movements on or after H0.
 * Import stays disabled while a selected row points at an unresolved asset, and whether the
 * synthetic titles resolve in this lane is unknown; a cash row never needs one. Through the review's
 * own controls: deselect all, filter the asset column on "no asset", select the visible rows.
 * Returns how many rows are selected.
 */
async function selectOnlyCashRows(page: Page, step4: Locator): Promise<number> {
    await page.getByTestId('import-wizard-deselect-all').click();
    await expect(step4).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});

    const trigger = step4.getByTestId('col-filter-trigger-asset');
    await trigger.click();
    const filter = step4.getByTestId('dt-header-asset').getByTestId('column-filter');
    await expect(filter).toBeVisible({timeout: 5_000});
    const noAsset = filter.getByTestId('filter-enum-option-__null__');
    await expect(noAsset).toHaveAttribute('data-checked', 'false');
    await noAsset.click();
    await expect(noAsset).toHaveAttribute('data-checked', 'true');
    await trigger.click();
    await expect(filter).toBeHidden({timeout: 5_000});

    // The filter is on: the rows on screen are the cash movements of the history, all of them.
    await expect(step4.locator('tbody tr[data-row-id]')).toHaveCount(MAIN_TRUTH.cashRowsInHistory, {timeout: 5_000});
    await page.getByTestId('import-wizard-select-visible').click();
    await expect(step4).toHaveAttribute('data-selected-count', String(MAIN_TRUTH.cashRowsInHistory), {timeout: 5_000});
    await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: 15_000});
    return MAIN_TRUTH.cashRowsInHistory;
}

/** What one Import asked: the owned broker, the set plugin, its truth points, the selection — and the deposit the premise of R5/R6 rests on. */
function expectGapFixCall(call: JsonCall, brokerId: number, selected: number) {
    expect(call.status, `POST ${GAP_FIX_PATH}: ${JSON.stringify(call.body)}`).toBe(200);
    const body = call.request as GapFixRequestBody;
    expect(body.broker_id, 'the gap-fix is asked for the owned broker').toBe(brokerId);
    expect(body.plugin_code).toBe(DANSKE);
    expect(
        body.checkpoints.map((checkpoint) => [checkpoint.as_of, checkpoint.kind]),
        'the truth point of the combined parse',
    ).toEqual([[MAIN_TRUTH.checkpoint.asOf, MAIN_TRUTH.checkpoint.kind]]);
    expect(body.verifications.map((verification) => verification.as_of)).toEqual([MAIN_TRUTH.verification]);
    expect(body.selection, 'the selection is the final list of the review').toHaveLength(selected);
    expect(body.selection.every((tx) => tx.broker_id === brokerId)).toBe(true);
    expect(body.pending_creates, 'the editor opened from the toolbar is empty').toEqual([]);
    expect(body.pending_delete_tx_ids).toEqual([]);

    const response = call.body as GapFixResponseBody;
    const deposits = response.checkpoints.flatMap((checkpoint) => checkpoint.proposals.filter((proposal) => proposal.type === 'DEPOSIT'));
    expect(
        deposits.map((proposal) => [proposal.date, proposal.cash?.code, Number(proposal.cash?.amount)]),
        'premise: on a fresh broker the opening cash correction is one deposit of 2699.50 EUR',
    ).toEqual([[MAIN_TRUTH.checkpoint.asOf, MAIN_TRUTH.deposit.currency, MAIN_TRUTH.deposit.amount]]);
}

/** The opening truth point holds the deposit, selected by default; the verification is there (whether it holds depends on the selection). */
async function expectOpeningDeposit(step: Locator) {
    const opening = step.locator(`[data-testid="gapfix-checkpoint"][data-as-of="${MAIN_TRUTH.checkpoint.asOf}"][data-kind="${MAIN_TRUTH.checkpoint.kind}"]`);
    await expect(opening, 'the opening truth point of the set').toHaveCount(1, {timeout: 5_000});
    const deposit = opening.locator('[data-testid="gapfix-proposal"][data-type="DEPOSIT"]');
    await expect(deposit).toHaveCount(1);
    await expect(deposit).toHaveAttribute('data-selected', 'true');
    await expect(deposit).toHaveAttribute('data-date', MAIN_TRUTH.checkpoint.asOf);
    await expect(step.locator(`[data-testid="gapfix-verification"][data-as-of="${MAIN_TRUTH.verification}"]`)).toHaveCount(1);
}

/** The wizard handed over and closed: the editor underneath, settled. */
async function editorAfterHandoff(page: Page): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 15_000});
    const bulk = page.getByTestId('tx-bulk-modal-root');
    await expect(bulk).toBeVisible({timeout: 10_000});
    await waitForSettled(bulk, 30_000);
    return bulk;
}

/** The editor rows tagged `gap_fix` (a tag is data, not a translation). */
function gapFixRows(bulk: Locator): Locator {
    return bulk.getByTestId('tx-bulk-tags').filter({has: bulk.page().locator('span', {hasText: /^gap_fix$/})});
}

/** Never Save All: close the editor through its unsaved-changes guard and discard. */
async function closeEditorWithoutSaving(page: Page, bulk: Locator) {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(bulk).toHaveCount(0, {timeout: 10_000});
}

// ---------------------------------------------------------------------------
// C3: the badges of FilesTable
// ---------------------------------------------------------------------------

type StoredFile = UploadedInfo & {kind?: string; combined_into?: string[] | null};

/** Upload one sample over the API into an upload batch of this test (multipart form, as the wizard sends it). */
async function uploadOverApi(page: Page, brokerId: number, filePath: string, batchId: string): Promise<StoredFile> {
    const name = path.basename(filePath);
    const mimeType = name.endsWith('.xlsx') ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' : 'text/csv';
    const response = await page.request.post(UPLOAD_PATH, {multipart: {broker_id: String(brokerId), batch_id: batchId, file: {name, mimeType, buffer: readFileSync(filePath)}}});
    const body = await response.text();
    expect(response.status(), `upload ${name} into batch ${batchId}: ${body}`).toBe(200);
    const uploaded = JSON.parse(body) as StoredFile;
    expect(uploaded).toMatchObject({filename: name, target_broker_id: brokerId, batch_id: batchId});
    return uploaded;
}

/** The broker detail → Transactions tab → import history: the broker's files in a FilesTable of type brim. */
async function openBrokerImportFiles(page: Page, brokerId: number, brokerName: string): Promise<Locator> {
    await navigateTo(page, `/brokers/${brokerId}`);
    await expect(page.getByTestId('broker-name')).toHaveText(brokerName, {timeout: 10_000});
    await page.getByTestId('broker-tab-transazioni').click();
    await expect(page.getByTestId('broker-transactions-tab')).toBeVisible({timeout: 5_000});
    await page.getByTestId('broker-show-import-history').click();
    const modal = page.getByTestId('import-files-modal');
    await expect(modal).toBeVisible({timeout: 5_000});
    const table = modal.getByTestId('files-table-brim');
    await expect(table).toBeVisible({timeout: 10_000});
    return table;
}

/** The badge kinds of one row, in the order they are shown. */
function badgeKinds(row: Locator): Promise<string[]> {
    return row.locator('[data-testid="file-set-badge"]').evaluateAll((badges) => badges.map((badge) => badge.getAttribute('data-kind') ?? ''));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — report sets', () => {
    let ownedBrokerId: number | undefined;
    let ownedSince = 0;

    test.beforeEach(async ({page}) => {
        ownedBrokerId = undefined;
        await login(page, TEST_USER);
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the
    // assertion error it follows, and that assertion is the point of the test.
    test.afterEach(async ({page}) => {
        if (ownedBrokerId === undefined) return;
        await page.goto('about:blank');
        await deleteOwnedBrokerAndFiles(page, ownedBrokerId, ownedSince);
    });

    /** Own a broker, then open the wizard: the broker exists before the wizard reads the list. */
    async function startOnOwnedBroker(page: Page, tag: string, extra: Record<string, unknown> = {}): Promise<number> {
        ownedSince = Date.now();
        const brokerId = await createOwnedBroker(page, `Report set ${tag} ${uniqueSuffix()}`, extra);
        ownedBrokerId = brokerId;
        await goToTransactions(page);
        await openImportWizard(page);
        return brokerId;
    }

    test('R1: a complete set is one card, one analysis row through its combined file, and a review that hides the rows before H0', async ({page}) => {
        test.setTimeout(150_000);
        // The broker's default plugin is the generic CSV, which also reads the cash CSV: A18 —
        // a file a report-set plugin recognises belongs to that plugin's set, default or not.
        const brokerId = await startOnOwnedBroker(page, 'R1', {default_import_plugin: GENERIC});

        // ① both exports together, one Next: a complete set does not stop on step 1.
        await dropFiles(page, [CUSTODY_XLSX, CASH_CSV]);
        await expect(pendingRows(page)).toHaveCount(2);
        await assignOwnedBroker(page, brokerId);
        const uploaded = await uploadsDuring(page, 2, async () => {
            await page.getByTestId('import-wizard-next').click();
            await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
        });
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        expect(cash.batch_id, 'the two exports of one step-1 session share its batch').toBe(batchId);
        await expect(page.getByTestId('import-wizard-step1-set-warning')).toHaveCount(0);

        // ② one card for the owned broker: complete, selected, two members with their roles.
        const step2 = page.getByTestId('import-wizard-step2');
        await waitForSettled(step2, 20_000);
        const card = setCard(page, brokerId, batchId);
        await expect(card, 'step 2 shows the set of the upload as one report-set card').toBeVisible({timeout: C2_FIRST});
        // One upload, one set: no other card holds this batch.
        await expect(step2.locator(`[data-testid="report-set-card"][data-batch-id="${batchId}"]`)).toHaveCount(1);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await expect(card).toHaveAttribute('data-batch-id', batchId);
        await expect(card).toHaveAttribute('data-plugin-code', DANSKE);
        // Uploaded in this session: never combined, never analysed.
        await expect(card).toHaveAttribute('data-analysed', 'false');
        await openCard(card);
        await expect(card.getByTestId('report-set-member')).toHaveCount(2);
        await expect(cardMember(card, custody.file_id)).toHaveAttribute('data-role', 'custody');
        await expect(cardMember(card, cash.file_id)).toHaveAttribute('data-role', 'cash');
        await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
        // A fresh broker: this is its first import.
        await expect(card.locator('[data-testid="report-set-history"][data-kind="first"]')).toBeVisible();
        await expect(card.getByTestId('report-set-timeline')).toBeVisible();
        await expect(page.getByTestId('import-wizard-set-blocks')).toHaveCount(0);
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeEnabled();

        // ③ combine, then parse the combined file — and only that: a member parsed alone is a 422.
        const stopRecording = recordJsonPosts(page, (pathname) => pathname === COMBINE_PATH || PARSE_PATH.test(pathname));
        await parse.click();
        const step3 = page.getByTestId('import-wizard-step3');
        await expect(step3).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 60_000);
        await expect(step3).toHaveAttribute('data-parse-state', 'ok');
        const calls = await stopRecording();
        const combines = calls.filter((call) => call.path === COMBINE_PATH);
        expect(
            combines.map((call) => [call.status, call.request]),
            'one combine of the set',
        ).toEqual([[200, {broker_id: brokerId, plugin_code: DANSKE, batch_id: batchId}]]);
        const combined = (combines[0].body as {combined: {file_id: string; kind: string}}).combined;
        expect(combined.kind).toBe('combined');
        expect(
            calls.filter((call) => PARSE_PATH.test(call.path)).map((call) => [call.path, call.status, (call.request as {plugin_code?: string}).plugin_code]),
            'one parse, of the combined file, with the set plugin',
        ).toEqual([[`${API}/brokers/import/files/${combined.file_id}/parse`, 200, DANSKE]]);

        // The set is one row of the results, labelled as a set with its files under it.
        const rows = step3.locator('tbody tr[data-row-id]');
        await expect(rows).toHaveCount(1);
        const setRow = rows.filter({has: page.getByTestId('parse-row-set')});
        await expect(setRow, 'the analysis row of a set carries parse-row-set').toHaveCount(1, {timeout: C2_FIRST});
        await expect(setRow.getByTestId('parse-row-set')).toContainText('danske_bank-custody.xlsx');
        await expect(setRow.getByTestId('parse-row-set')).toContainText('danske_bank-cash.csv');

        // Its detail carries the pairing counts of the combine.
        await setRow.dblclick();
        const detail = page.getByTestId('parse-detail-modal');
        await expect(detail).toBeVisible({timeout: 5_000});
        const pairing = detail.getByTestId('parse-detail-pairing');
        await expect(pairing).toBeVisible({timeout: C2_FIRST});
        for (const [outcome, count] of Object.entries(MAIN_SET.outcomes)) {
            await expect(pairing, `combine outcome "${outcome}"`).toHaveAttribute(`data-${outcome}`, String(count));
        }
        await page.getByTestId('parse-detail-close').click();
        await expect(detail).toHaveCount(0, {timeout: 5_000});

        // The combined parse raises notices (deferred_rows, deposit_assumed): read past them.
        await page.getByTestId('import-wizard-continue').click();
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm).toBeVisible({timeout: 5_000});
        await confirm.click();
        // The 11 trades include their charges: each asks for a decision; "keep all" gives it.
        await expect(currentStep(page)).toHaveAttribute('data-step-id', 'fix', {timeout: 30_000});
        await expect(page.getByTestId('fix-step-row')).toHaveCount(MAIN_SET.trades, {timeout: 10_000});
        await page.getByTestId('fix-step-accept-all').click();
        await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: 10_000});
        await page.getByTestId('import-wizard-fix-continue').click();
        await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
        const step4 = page.getByTestId('import-wizard-step4');
        await waitForSettled(step4, 30_000);

        // ④ the 7 rows before H0 (2020-02-03) sit behind a counter, out of the total.
        const counter = page.getByTestId('import-wizard-before-history-count');
        await expect(counter, 'the review counts the rows before H0').toHaveAttribute('data-count', String(MAIN_SET.beforeHistory), {timeout: C2_FIRST});
        const importable = MAIN_SET.transactions - MAIN_SET.beforeHistory;
        await showAllRows(page, step4);
        const reviewRows = step4.locator('tbody tr[data-row-id]');
        const lockedToggles = step4.locator('tbody tr[data-row-id] button[aria-pressed][disabled]');
        await expect(step4).toHaveAttribute('data-total-count', String(importable));
        await expect(reviewRows).toHaveCount(importable);
        await expect(lockedToggles).toHaveCount(0);

        // Shown on request: in the table, with a disabled checkbox, never selected, still out of the total.
        await page.getByTestId('import-wizard-before-history-toggle').click();
        await expect(reviewRows).toHaveCount(MAIN_SET.transactions, {timeout: 5_000});
        await expect(lockedToggles).toHaveCount(MAIN_SET.beforeHistory);
        await expect(step4.locator('tbody tr[data-row-id] button[aria-pressed="true"][disabled]')).toHaveCount(0);
        await expect(step4).toHaveAttribute('data-total-count', String(importable));
        await expect(counter).toHaveAttribute('data-count', String(MAIN_SET.beforeHistory));
    });

    test('R2: an export missing on step 1 is announced there, and the CSV dropped next joins the same batch', async ({page}) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'R2');

        await dropFiles(page, [CUSTODY_XLSX]);
        await expect(pendingRows(page)).toHaveCount(1);
        await assignOwnedBroker(page, brokerId);
        const next = page.getByTestId('import-wizard-next');
        const [custody] = await uploadsDuring(page, 1, () => next.click());
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');

        // The wizard previews the set it just uploaded: the cash statement is missing, so it stays on step 1.
        const cashWarning = setWarning(page, 'cash');
        await expect(cashWarning, 'step 1 warns about the missing cash export of the set').toBeVisible({timeout: C2_FIRST});
        await expect(cashWarning).toHaveAttribute('data-plugin-code', DANSKE);
        await expect(page.getByTestId('import-wizard-step1-set-warning')).toHaveCount(1);
        const step1 = page.getByTestId('import-wizard-step1');
        await waitForSettled(step1);
        await expect(page.getByTestId('import-wizard-step2')).toHaveCount(0);

        // The CSV dropped now goes to the same broker ("assign all") and to the same batch.
        await dropFiles(page, [CASH_CSV]);
        await expect(pendingRows(page)).toHaveCount(2);
        await expect(next).toBeEnabled({timeout: 5_000});
        const [cash] = await uploadsDuring(page, 1, async () => {
            await next.click();
            await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
        });
        expect(cash.filename).toBe('danske_bank-cash.csv');
        expect(cash.target_broker_id).toBe(brokerId);
        expect(cash.batch_id, 'the file added after the warning joins the batch of the first upload').toBe(batchId);

        const step2 = page.getByTestId('import-wizard-step2');
        await waitForSettled(step2, 20_000);
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await openCard(card);
        await expect(card.getByTestId('report-set-member')).toHaveCount(2);
        await expect(cardMember(card, custody.file_id)).toHaveAttribute('data-role', 'custody');
        await expect(cardMember(card, cash.file_id)).toHaveAttribute('data-role', 'cash');
        await expect(page.getByTestId('import-wizard-parse')).toBeEnabled();
    });

    test('R3: an incomplete set blocks the analysis until the missing export is uploaded from its card', async ({page}) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'R3');

        await dropFiles(page, [CUSTODY_XLSX]);
        await expect(pendingRows(page)).toHaveCount(1);
        await assignOwnedBroker(page, brokerId);
        const next = page.getByTestId('import-wizard-next');
        const [custody] = await uploadsDuring(page, 1, () => next.click());
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        // The first Next stops on the warning; a second one goes on with the set incomplete.
        await expect(setWarning(page, 'cash'), 'step 1 warns about the missing cash export of the set').toBeVisible({timeout: C2_FIRST});
        await waitForSettled(page.getByTestId('import-wizard-step1'));
        await next.click();
        const step2 = page.getByTestId('import-wizard-step2');
        await expect(step2).toBeVisible({timeout: 15_000});
        await waitForSettled(step2, 20_000);

        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await openCard(card);
        await expect(card.locator('[data-testid="report-set-missing"][data-role="cash"]')).toBeVisible();
        await expect(card.getByTestId('report-set-missing')).toHaveCount(1);
        await expect(card.getByTestId('report-set-upload-missing')).toBeVisible();
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeDisabled();
        await expect(page.getByTestId('import-wizard-set-blocks')).toBeVisible();

        // "Upload the missing file": same broker, same batch.
        const input = card.getByTestId('report-set-upload-input');
        await expect(input).toHaveAttribute('accept', /\.csv/);
        const [cash] = await uploadsDuring(page, 1, () => input.setInputFiles(CASH_CSV));
        expect(cash.filename).toBe('danske_bank-cash.csv');
        expect(cash.target_broker_id).toBe(brokerId);
        expect(cash.batch_id, 'the missing export joins the batch of its set').toBe(batchId);
        await expect(card).toHaveAttribute('data-batch-id', batchId);

        // The card re-reads the files, previews again, and selects the new member with its set.
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await waitForSettled(step2, 20_000);
        await expect(card).toHaveAttribute('data-selected', 'all');
        await openCard(card);
        await expect(cardMember(card, cash.file_id)).toHaveAttribute('data-role', 'cash');
        await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-set-blocks')).toHaveCount(0);
        await expect(parse).toBeEnabled();
    });

    test('R4: excluding an incomplete set unblocks the analysis of the file uploaded with it', async ({page}) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'R4');

        await dropFiles(page, [CUSTODY_XLSX, GENERIC_CSV]);
        await expect(pendingRows(page)).toHaveCount(2);
        await assignOwnedBroker(page, brokerId);
        const next = page.getByTestId('import-wizard-next');
        const uploaded = await uploadsDuring(page, 2, () => next.click());
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const generic = uploadNamed(uploaded, 'generic_simple.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        await expect(setWarning(page, 'cash'), 'step 1 warns about the missing cash export of the set').toBeVisible({timeout: C2_FIRST});
        await waitForSettled(page.getByTestId('import-wizard-step1'));
        await next.click();
        const step2 = page.getByTestId('import-wizard-step2');
        await expect(step2).toBeVisible({timeout: 15_000});
        await waitForSettled(step2, 20_000);

        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await openCard(card);
        // The generic file is a single: a selected row of the broker table, not a member of the set.
        await expect(cardMember(card, generic.file_id)).toHaveCount(0);
        const genericCheckbox = page.getByTestId(`dt-row-checkbox-${generic.file_id}`);
        await expect(genericCheckbox).toHaveAttribute('data-state', 'checked');
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeDisabled();
        await expect(page.getByTestId('import-wizard-set-blocks')).toBeVisible();

        await card.getByTestId('report-set-exclude').click();
        await expect(card).toHaveAttribute('data-selected', 'none', {timeout: 5_000});
        await expect(page.getByTestId('import-wizard-set-blocks')).toHaveCount(0);
        await expect(parse).toBeEnabled();
        await expect(genericCheckbox).toHaveAttribute('data-state', 'checked');
    });

    // -----------------------------------------------------------------------
    // F1 — the developer's review: D1, the second Next lost on step 1
    // -----------------------------------------------------------------------

    /**
     * D1. The drop zone used to fold on every mousedown outside it. The incomplete-set warning reopens
     * it, so the mousedown half of the next click on Next folded it again: the modal lost height, the
     * button moved before the mouseup, and the click never happened. While a set warning is shown the
     * zone stays open. The mousedown is dispatched on its own, so the fold is observed whatever the
     * geometry of this viewport — Playwright's real click lands wherever the button ends up.
     */
    test('F1-D1: with the step-1 set warning shown, a mousedown outside keeps the drop zone open and one Next reaches step 2', async ({page}) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'F1-D1');

        await dropFiles(page, [CUSTODY_XLSX]);
        await expect(pendingRows(page)).toHaveCount(1);
        await assignOwnedBroker(page, brokerId);
        const next = page.getByTestId('import-wizard-next');
        await uploadsDuring(page, 1, () => next.click());

        // The warning reopens the drop zone: the missing export can be dropped into the same set.
        await expect(setWarning(page, 'cash'), 'step 1 warns about the missing cash export of the set').toBeVisible({timeout: C2_FIRST});
        const step1 = page.getByTestId('import-wizard-step1');
        await waitForSettled(step1);
        const uploader = step1.getByTestId('file-uploader');
        await expect(uploader, 'the set warning opens the drop zone').toBeVisible({timeout: 5_000});

        // The first half of a click on Next: a mousedown outside the drop zone.
        await next.dispatchEvent('mousedown');
        await expect(uploader, 'a mousedown outside the drop zone leaves it open while the set warning is shown').toBeVisible();
        await expect(page.getByTestId('import-wizard-upload-more')).toHaveCount(0);
        await expect(setWarning(page, 'cash')).toBeVisible();

        // ONE click on Next goes on, with the set incomplete.
        await next.click();
        const step2 = page.getByTestId('import-wizard-step2');
        await expect(step2, 'one click on Next reaches step 2').toBeVisible({timeout: 15_000});
        await waitForSettled(step2, 20_000);
        await expect(page.getByTestId('import-wizard-step1')).toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // C3 — "Align with the bank" and the file badges
    // -----------------------------------------------------------------------

    test('R5: Import on a report set opens the gap-fix step — the opening deposit selected, recomputed on Back, handed to the editor tagged gap_fix', async ({page}) => {
        test.setTimeout(180_000);
        const brokerId = await startOnOwnedBroker(page, 'R5');
        const step4 = await walkMainSetToReview(page, brokerId);
        const selected = await selectOnlyCashRows(page, step4);
        const gapFixCalls = recordGapFixPosts(page);
        const importButton = page.getByTestId('import-wizard-import');

        // First Import: one request, then the step — not the editor.
        await importButton.click();
        await expect(currentStep(page), 'Import on a report set opens the gap-fix step').toHaveAttribute('data-step-id', 'gapFix', {timeout: C3_FIRST});
        const step = page.getByTestId('import-wizard-gapfix');
        await expect(step).toBeVisible({timeout: 5_000});
        await expectOpeningDeposit(step);
        await expect.poll(gapFixCalls.count, {message: 'one POST /gap-fix for the first Import', timeout: 5_000}).toBe(1);

        // Back to the review, Import again: recomputed, with a second request.
        await page.getByTestId('import-wizard-back').click();
        await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 10_000});
        await expect(step).toHaveCount(0);
        await expect(step4).toHaveAttribute('data-selected-count', String(selected), {timeout: 10_000});
        await expect(importButton).toBeEnabled({timeout: 15_000});
        await importButton.click();
        await expect(currentStep(page)).toHaveAttribute('data-step-id', 'gapFix', {timeout: 30_000});
        await expect(step).toBeVisible({timeout: 5_000});
        await expectOpeningDeposit(step);
        await expect.poll(gapFixCalls.count, {message: 'one more POST /gap-fix for the second Import', timeout: 5_000}).toBe(2);
        const calls = await gapFixCalls.stop();
        expect(calls, 'two Imports, two gap-fix requests').toHaveLength(2);
        for (const call of calls) expectGapFixCall(call, brokerId, selected);

        // D-S14: every correction is selected by default.
        const proposals = step.locator('[data-testid="gapfix-proposal"]');
        const proposalCount = await proposals.count();
        expect(proposalCount, 'at least the opening deposit is proposed').toBeGreaterThan(0);
        await expect(step).toHaveAttribute('data-proposal-count', String(proposalCount));
        await expect(step).toHaveAttribute('data-selected-count', String(proposalCount));
        await expect(step.locator('[data-testid="gapfix-proposal"][data-selected="true"]')).toHaveCount(proposalCount);
        await expect(page.getByTestId('import-wizard-gapfix-count')).toHaveAttribute('data-count', String(proposalCount));

        // Continue: the review's rows and the selected corrections, tagged gap_fix, in the editor.
        await page.getByTestId('import-wizard-gapfix-continue').click();
        const bulk = await editorAfterHandoff(page);
        await showAllRows(page, bulk);
        await expect(bulk.getByTestId('tx-bulk-row-label'), 'the selected rows of the review and the selected corrections').toHaveCount(selected + proposalCount, {timeout: 10_000});
        await expect(gapFixRows(bulk), 'as many gap_fix rows as corrections were selected').toHaveCount(proposalCount);
        await closeEditorWithoutSaving(page, bulk);
    });

    test('R6: with every correction unticked, none reaches the editor, and the imported rows do', async ({page}) => {
        test.setTimeout(180_000);
        const brokerId = await startOnOwnedBroker(page, 'R6');
        const step4 = await walkMainSetToReview(page, brokerId);
        const selected = await selectOnlyCashRows(page, step4);

        await page.getByTestId('import-wizard-import').click();
        await expect(currentStep(page), 'Import on a report set opens the gap-fix step').toHaveAttribute('data-step-id', 'gapFix', {timeout: C3_FIRST});
        const step = page.getByTestId('import-wizard-gapfix');
        await expect(step).toBeVisible({timeout: 5_000});
        await expectOpeningDeposit(step);

        // Untick them one by one, by key, each to its end state.
        const keys = await step.locator('[data-testid="gapfix-proposal"]').evaluateAll((proposals) => proposals.map((proposal) => proposal.getAttribute('data-key') ?? ''));
        expect(keys.length, 'at least the opening deposit is proposed').toBeGreaterThan(0);
        expect(new Set(keys).size, 'every proposal has its own key').toBe(keys.length);
        for (const key of keys) {
            const proposal = step.locator(`[data-testid="gapfix-proposal"][data-key="${key}"]`);
            await expect(proposal).toHaveAttribute('data-selected', 'true');
            await proposal.getByTestId('gapfix-proposal-toggle').click();
            await expect(proposal).toHaveAttribute('data-selected', 'false', {timeout: 5_000});
        }
        await expect(page.getByTestId('import-wizard-gapfix-count')).toHaveAttribute('data-count', '0');
        await expect(step).toHaveAttribute('data-selected-count', '0');

        await page.getByTestId('import-wizard-gapfix-continue').click();
        const bulk = await editorAfterHandoff(page);
        // The editor always shows its pagination bar: every row is put on one page first, as in R5, so
        // the counts below are about the whole editor — no page before or after this one.
        await showAllRows(page, bulk);
        await expect(bulk.getByTestId('pagination-prev')).toBeDisabled();
        await expect(bulk.getByTestId('pagination-next')).toBeDisabled();
        // The imported rows are there, and no correction is.
        await expect(bulk.getByTestId('tx-bulk-row-label'), 'the selected rows of the review reach the editor').toHaveCount(selected, {timeout: 10_000});
        await expect(gapFixRows(bulk), 'no correction was selected').toHaveCount(0);
        await closeEditorWithoutSaving(page, bulk);
    });

    test('R7: a single generic CSV never asks for the gap-fix and goes straight to the editor', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'R7');
        // generic_simple.csv needs assets and corrections; three cash movements in its format need neither.
        const marker = uniqueSuffix();
        const csvPath = testInfo.outputPath(`r7-cash-only-${marker}.csv`);
        mkdirSync(path.dirname(csvPath), {recursive: true});
        writeFileSync(csvPath, 'date,type,quantity,amount,currency,asset,description\n' + `2025-03-01,DEPOSIT,0,1000.00,EUR,,R7 funding ${marker}\n` + `2025-03-02,WITHDRAWAL,0,-250.00,EUR,,R7 cash out ${marker}\n` + `2025-03-03,DEPOSIT,0,175.50,EUR,,R7 top up ${marker}\n`);
        const gapFixCalls = recordGapFixPosts(page);

        await dropFiles(page, [csvPath]);
        await expect(pendingRows(page)).toHaveCount(1);
        await assignOwnedBroker(page, brokerId);
        const [uploaded] = await uploadsDuring(page, 1, async () => {
            await page.getByTestId('import-wizard-next').click();
            await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
        });
        await waitForSettled(page.getByTestId('import-wizard-step2'), 20_000);
        await expect(page.getByTestId(`dt-row-checkbox-${uploaded.file_id}`)).toHaveAttribute('data-state', 'checked', {timeout: 5_000});
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeEnabled({timeout: 5_000});
        await parse.click();
        await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 30_000);
        await page.getByTestId('import-wizard-continue').click();
        await expect(currentStep(page)).toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
        const step4 = page.getByTestId('import-wizard-step4');
        await waitForSettled(step4, 30_000);
        await expect(step4).toHaveAttribute('data-selected-count', '3');

        const importButton = page.getByTestId('import-wizard-import');
        await expect(importButton).toBeEnabled({timeout: 15_000});
        await importButton.click();
        const bulk = await editorAfterHandoff(page);
        await expect(bulk.getByTestId('tx-bulk-row-label')).toHaveCount(3, {timeout: 10_000});
        // The editor is up, so the import is over: no gap-fix was asked, ever.
        expect(gapFixCalls.count(), 'a single-file plugin has no truth points: no POST /gap-fix').toBe(0);
        expect(await gapFixCalls.stop()).toEqual([]);
        await expect(gapFixRows(bulk)).toHaveCount(0);
        await closeEditorWithoutSaving(page, bulk);
    });

    test('R8: FilesTable badges the combined file, its originals, and a custody export uploaded alone', async ({page}) => {
        test.setTimeout(90_000);
        ownedSince = Date.now();
        const brokerName = `Report set R8 ${uniqueSuffix()}`;
        const brokerId = await createOwnedBroker(page, brokerName);
        ownedBrokerId = brokerId;

        // B1: both exports in one upload batch, then combined. B2: the custody export alone, in another.
        const b1 = randomUUID();
        const b2 = randomUUID();
        const custody1 = await uploadOverApi(page, brokerId, CUSTODY_XLSX, b1);
        const cash1 = await uploadOverApi(page, brokerId, CASH_CSV, b1);
        const combineResponse = await page.request.post(COMBINE_PATH, {data: {broker_id: brokerId, plugin_code: DANSKE, batch_id: b1}});
        const combineBody = await combineResponse.text();
        expect(combineResponse.status(), `combine B1: ${combineBody}`).toBe(200);
        const combined = (JSON.parse(combineBody) as {combined: StoredFile}).combined;
        const custody2 = await uploadOverApi(page, brokerId, CUSTODY_XLSX, b2);

        // The preconditions the badges stand on, read back rather than inferred.
        const stored = new Map(((await brimFilesOn(page, brokerId)) as StoredFile[]).map((file) => [file.file_id, file]));
        expect(stored.get(combined.file_id), 'the combined file of B1').toMatchObject({kind: 'combined', batch_id: b1});
        for (const original of [custody1, cash1]) expect(stored.get(original.file_id)?.combined_into, `${original.filename} of B1 is used in the combined file`).toContain(combined.file_id);
        expect(stored.get(custody2.file_id)?.combined_into ?? [], 'the custody export of B2 was never combined').toEqual([]);

        const table = await openBrokerImportFiles(page, brokerId, brokerName);
        // The modal lists what GET /files?broker_ids=<id> returns: this broker's files — a reused broker id
        // can bring the leftovers of an earlier run — and legacy files without a broker. Past 10 rows the
        // table pages, so every row is shown on one page before any is looked for.
        const listed = await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`);
        expect(listed.ok()).toBe(true);
        if (((await listed.json()) as unknown[]).length > 10) await showAllRows(page, table);
        const row = (fileId: string) => table.locator(`tr[data-row-id="${fileId}"]`);
        for (const file of [combined, custody1, cash1, custody2]) await expect(row(file.file_id), `${file.filename} (${file.file_id}) is listed`).toHaveCount(1, {timeout: 10_000});

        await expect(row(combined.file_id).locator('[data-testid="file-set-badge"][data-kind="combined"]'), 'the combined file carries the combined badge').toBeVisible({timeout: C3_FIRST});
        // `incomplete` waits for the preview of its set: once B2's is in, the badges have settled.
        await expect(row(custody2.file_id).locator('[data-testid="file-set-badge"][data-kind="incomplete"]'), 'the lone custody export of B2 is an incomplete set').toBeVisible({timeout: 15_000});
        await expect.poll(() => badgeKinds(row(combined.file_id)), {message: 'combined file'}).toEqual(['combined']);
        await expect.poll(() => badgeKinds(row(custody1.file_id)), {message: 'custody original of B1'}).toEqual(['usedInCombined', 'set']);
        await expect.poll(() => badgeKinds(row(cash1.file_id)), {message: 'cash original of B1'}).toEqual(['usedInCombined', 'set']);
        await expect.poll(() => badgeKinds(row(custody2.file_id)), {message: 'custody export of B2'}).toEqual(['set', 'incomplete']);
    });
});
