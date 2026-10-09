/**
 * Import Wizard + bulk editor — Scalable Capital's internal transfers become Cash Transfers (plan 37, step 11).
 *
 * Scalable has two accounts and LibreFolio gives each its own broker: the broker account (default import plugin
 * `broker_scalable`) and the overnight account (`broker_scalable_deposit`). A transfer between them shows up in both
 * exports — same day, opposite amounts — as a WITHDRAWAL on the paying account and a DEPOSIT on the other. The samples
 * hold two (backend test_brim_scalable_api.py, TRANSFER_PAIRS):
 *
 *   2026-04-02  broker account −1000  →  overnight account +1000
 *   2026-06-01  overnight account −300  →  broker account +300
 *
 * Each leg's text carries its own exporter id, so the two texts of a pair differ and merging them opens the merge
 * dialog, which proposes both texts joined, one per line.
 *
 *   S1 same session: both exports in ONE wizard run, each assigned to its own broker, only their cash rows (no
 *      instrument, nothing to resolve) handed to the editor. The new rows are asked to the database search under
 *      negative ids (nothing saved: nothing proposed); the green banner proposes exactly the two transfers, each
 *      identified by the texts its merge dialog joins. One is merged with the joined text and saved: its two legs
 *      are CASH_TRANSFER, linked to each other, on the two brokers, with the joined text; the other stays a
 *      withdrawal and a deposit.
 *   S2 separate sessions: the broker account's cash rows (DEPOSIT, WITHDRAWAL, FEE, TAX without an instrument) are
 *      saved over the API first, as test_brim_scalable_api.py saves them; then the overnight export goes through the
 *      wizard. The database search proposes, for each new transfer leg, its saved other side and nothing else; the
 *      💡 shows in the toolbar and in the menu of those two rows only; opened from the 2026-06-01 row it offers the
 *      two saved sides, one is added, the banner proposes the new + saved pair; merged with the joined text and saved,
 *      the saved leg and the new leg are CASH_TRANSFER, linked to each other.
 *
 * Why a disposable account. The database search and the picker see every broker the user can access, and the
 * banner's proposals depend on what the editor holds: on the shared E2E user the transfers of a neighbouring test
 * would be proposed too, and every count here would depend on the schedule. Each test registers its own account
 * (fixtures/onboarding-accounts.ts, every onboarding flow skipped over the API so no guide covers the wizard or the
 * editor), which owns exactly the two brokers it creates — read back before anything else. The cleanup leaves the
 * page, deletes the BRIM files of those brokers, then the brokers (force: their transactions go with them) and the
 * account.
 *
 * What is asserted where. The banner rows publish no data attribute naming their rows, so a proposal is identified
 * by its merge dialog: the joined text holds the exporter id of each leg — file data, not a translation. The merged
 * pair is then read from the editor (`tx-bulk-date[data-partner-date]`), from the commit request, and from the API.
 *
 * Key data-testids: tx-import-button · import-wizard-stepper [aria-current="step"][data-step-id] ·
 * import-wizard-step1 / file-uploader / file-input / import-wizard-upload-more / search-select-option-<brokerId> /
 * import-wizard-next · import-broker-mismatch-modal · import-wizard-step2 [data-busy] /
 * import-wizard-broker-files-<brokerId> / dt-row-checkbox-<fileId> / import-wizard-parse · import-wizard-step3 ·
 * import-wizard-step4 [data-selected-count][data-total-count] / import-wizard-deselect-all / import-wizard-select-all
 * / import-wizard-select-visible / col-filter-trigger-asset / dt-header-asset / column-filter /
 * filter-enum-option-__null__ / import-wizard-import · tx-bulk-modal-root [data-busy] / tx-bulk-body /
 * tx-bulk-date [data-row-id][data-date][data-partner-date] / row-actions-<tempId> / context-menu /
 * context-menu-action-suggest / context-menu-action-mark-delete / tx-bulk-suggest-import / tx-picker-modal /
 * dt-row-checkbox-tx-<id> / tx-picker-add / promote-suggest-banner / promote-suggest-item-<n> /
 * promote-suggest-link-<n> / promote-merge-desc-input / promote-merge-confirm / tx-bulk-todo-blockers /
 * tx-bulk-todo-warnings / tx-bulk-commit / tx-bulk-modal.
 */

import {expect, test, type APIRequestContext, type Locator, type Page, type Response} from '../fixtures/playwright';
import {navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {continueToStep, type ParseResponse} from '../fixtures/import-wizard';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {optionsClosed} from '../fixtures/probe';
import {uniqueSuffix} from '../fixtures/unique';
import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const BROKERS_PATH = `${API}/brokers`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const FILES_PATH = `${API}/brokers/import/files`;
const PARSE_PATH = /^\/api\/v1\/brokers\/import\/files\/([^/]+)\/parse$/;
const TRANSACTIONS_PATH = `${API}/transactions`;
const VALIDATE_PATH = `${API}/transactions/validate`;
const COMMIT_PATH = `${API}/transactions/commit`;
const PROMOTE_SUGGEST_PATH = `${API}/transactions/promote-suggest`;
const SAMPLE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../backend/app/services/brim_providers/sample_reports');
const UI_TIMEOUT = 10_000;
/** An upload, a parse, a step change, a save: each waits on the server. */
const STEP_TIMEOUT = 30_000;

/** The two Scalable accounts: the broker each one gets, its default import plugin and its sample export. */
type Account = 'broker' | 'overnight';
const ACCOUNTS: Record<Account, {plugin: string; sample: string; label: string}> = {
    broker: {plugin: 'broker_scalable', sample: 'scalable-broker-export.csv', label: 'broker account'},
    overnight: {plugin: 'broker_scalable_deposit', sample: 'scalable-deposit-export.csv', label: 'overnight account'},
};

/** The internal transfers of the samples: a WITHDRAWAL of `amount` on `from`, a DEPOSIT of `amount` on `to`, the same day. */
const TRANSFERS: ReadonlyArray<{day: string; amount: number; from: Account; to: Account}> = [
    {day: '2026-04-02', amount: 1000, from: 'broker', to: 'overnight'},
    {day: '2026-06-01', amount: 300, from: 'overnight', to: 'broker'},
];

/** The rows S2 saves before the import, as test_brim_scalable_api.py saves them: cash movements without an instrument. */
const SAVED_TYPES = new Set(['DEPOSIT', 'WITHDRAWAL', 'FEE', 'TAX']);

/** The overnight account's first deposit (5000 EUR from the bank): the only row of its day, and no transfer. */
const QUIET_DAY = '2026-03-02';

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Cash = {code: string; amount: string | number};
type ParsedTx = {type: string; date: string; asset_id?: number | null; cash?: Cash | null; description?: string | null};
/** The parse response (`BRIMParseResponse`), its transactions typed as far as this spec reads them. */
type ParseBody = Omit<ParseResponse, 'transactions'> & {transactions: ParsedTx[]};
type UploadedInfo = {file_id: string; filename: string; target_broker_id: number | null; compatible_plugins?: string[] | null};
type DeleteResult = {success?: boolean; file_id?: string};
type OwnedBroker = {id: number; name: string};
type Brokers = Record<Account, OwnedBroker>;
/** What a test created, for its cleanup: its account and that account's brokers. */
type Owned = {user: DisposableUser | null; brokerIds: number[]};
/** One input of `POST /transactions/promote-suggest`, as the editor sends it. */
type SuggestInput = {id: number; type: string; broker_id: number; date: string};
type SuggestAnswer = {results: Record<string, Array<{id: number}>>};
type StagedCreate = {broker_id?: number; type?: string; date?: string; cash?: Cash | null; description?: string | null; link_uuid?: string | null};
type CommitPayload = {creates?: StagedCreate[]; updates?: unknown[]; deletes?: number[]; promotes?: Array<Record<string, unknown>>};
type CommitResult = {committed: boolean; issues?: unknown[]; results?: Array<{operation: string; index?: number; ids?: number[]}>};
type SavedTx = {id: number; broker_id: number; type: string; date: string; cash?: Cash | null; description?: string | null; related_transaction_id?: number | null};
/** One leg of an internal transfer, as its plugin parses it. */
type Leg = {account: Account; type: 'WITHDRAWAL' | 'DEPOSIT'; day: string; amount: number; description: string};
type Transfer = {day: string; amount: number; out: Leg; in: Leg};
/** A file for step 1: a copy of a sample under a unique name. */
type SampleFile = {name: string; mimeType: string; buffer: Buffer};

// ---------------------------------------------------------------------------
// The samples' facts, read from their parse
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

const byNumber = (a: number, b: number) => a - b;
const amountOf = (cash: Cash | null | undefined): number => Number(cash?.amount ?? Number.NaN);

/** A copy of an account's sample under a unique name: the name identifies the upload. */
function sampleFile(account: Account): SampleFile {
    const {sample} = ACCOUNTS[account];
    return {name: `${path.basename(sample, '.csv')}-${uniqueSuffix()}.csv`, mimeType: 'text/csv', buffer: readFileSync(path.join(SAMPLE_DIR, sample))};
}

/** The rows of a parse without an instrument: the only ones these tests import, so nothing needs resolving. */
function cashRows(parsed: ParseBody): ParsedTx[] {
    return parsed.transactions.filter((tx) => tx.asset_id == null);
}

function legOf(parsed: ParseBody, account: Account, type: Leg['type'], day: string, amount: number): Leg {
    const found = cashRows(parsed).filter((tx) => tx.type === type && tx.date === day && amountOf(tx.cash) === amount);
    expect(found, `${ACCOUNTS[account].sample}: exactly one ${type} of ${amount} EUR on ${day}, a leg of an internal transfer (backend test_brim_scalable_api.py, TRANSFER_PAIRS)`).toHaveLength(1);
    return {account, type, day, amount, description: found[0].description ?? ''};
}

/** The two internal transfers, each leg read from the parse of its own account's export. */
function transfersIn(parsed: Record<Account, ParseBody>): Transfer[] {
    return TRANSFERS.map(({day, amount, from, to}) => {
        const transfer: Transfer = {day, amount, out: legOf(parsed[from], from, 'WITHDRAWAL', day, -amount), in: legOf(parsed[to], to, 'DEPOSIT', day, amount)};
        expect(transfer.out.description, `premise: the legs of the ${day} transfer carry different texts (each its own exporter id), so merging them asks which text to keep`).not.toBe(transfer.in.description);
        return transfer;
    });
}

/** The transfer a merge dialog proposes, read from the text it joins: the two legs' texts, one per line. */
function transferJoinedBy(transfers: readonly Transfer[], joined: string): Transfer {
    const lines = JSON.stringify(joined.split('\n').sort());
    const found = transfers.filter((transfer) => JSON.stringify([transfer.out.description, transfer.in.description].sort()) === lines);
    expect(found, `the merge joins the two legs of one internal transfer; the joined text: ${JSON.stringify(joined)}`).toHaveLength(1);
    return found[0];
}

// ---------------------------------------------------------------------------
// The account and what it owns
// ---------------------------------------------------------------------------

/**
 * Register a disposable account, take it past the onboarding with every flow skipped, and create its two brokers —
 * each with the default import plugin of its account. Their ids are recorded for the cleanup before anything about
 * them is checked; then the account must see exactly these two brokers.
 */
async function startOnOwnAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<Brokers> {
    owned.user = await registerDisposableUser(request, tag);
    await prepareOnboardingAccount(page, owned.user, []);
    const items = (Object.keys(ACCOUNTS) as Account[]).map((account) => ({account, name: `Scalable ${ACCOUNTS[account].label} ${uniqueSuffix()}`}));
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null}>}>(await page.request.post(BROKERS_PATH, {data: items.map(({account, name}) => ({name, default_import_plugin: ACCOUNTS[account].plugin}))}), 'create the two brokers');
    for (const result of body.results) {
        if (result.success && typeof result.broker_id === 'number') owned.brokerIds.push(result.broker_id);
    }
    const brokers = {} as Brokers;
    for (const {account, name} of items) {
        const result = body.results.find((candidate) => candidate.name === name);
        if (!result?.success || typeof result.broker_id !== 'number') throw new Error(`Broker "${name}" was not created: ${JSON.stringify(body.results)}`);
        brokers[account] = {id: result.broker_id, name};
    }
    const listed = await jsonFrom<{items: Array<{id: number}>}>(await page.request.get(BROKERS_PATH), 'list the account’s brokers');
    expect(listed.items.map((item) => item.id).sort(byNumber), 'premise: the account sees exactly the two brokers this test created').toEqual([brokers.broker.id, brokers.overnight.id].sort(byNumber));
    return brokers;
}

/** The BRIM files stored on one broker. The list also returns files with no broker, so the target is filtered. */
async function filesOn(page: Page, brokerId: number): Promise<UploadedInfo[]> {
    const files = await jsonFrom<UploadedInfo[]>(await page.request.get(`${FILES_PATH}?broker_ids=${brokerId}`), `list the BRIM files of broker ${brokerId}`);
    return files.filter((file) => file.target_broker_id === brokerId);
}

/**
 * Leave the page, delete the BRIM files of the account's brokers, then the brokers (force: their transactions go
 * with them) and the account itself. Every step is attempted; the failures are reported together.
 */
async function cleanupOwned(page: Page, request: APIRequestContext, owned: Owned): Promise<void> {
    const user = owned.user;
    if (!user) return;
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<unknown>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Unmount the wizard and the editor first, so nothing on the page reacts while their data goes away.
    await attempt('leave the page', () => page.goto('about:blank'));
    for (const brokerId of owned.brokerIds) {
        await attempt(`the BRIM files of broker ${brokerId}`, async () => {
            for (const file of await filesOn(page, brokerId)) {
                const result = await jsonFrom<DeleteResult>(await page.request.delete(`${FILES_PATH}/${file.file_id}`), `delete BRIM file ${file.file_id}`);
                expect(result, `BRIM file ${file.file_id} is deleted`).toMatchObject({success: true, file_id: file.file_id});
            }
        });
    }
    await attempt(`the account ${user.username} and its brokers`, () => deleteDisposableUser(request, user, owned.brokerIds));
    expect(failures, 'cleanup removes the files, the brokers and the account this test created — and nothing else').toEqual([]);
}

/**
 * S2's starting point, as test_brim_scalable_api.py builds it: the broker account's export uploaded and parsed over
 * the API, its cash rows (DEPOSIT, WITHDRAWAL, FEE, TAX without an instrument) validated and saved as parsed. The
 * uploaded file is deleted once parsed: only its transactions are needed. Returns the parse and the saved ids by text.
 */
async function saveBrokerCashRowsOverApi(page: Page, broker: OwnedBroker): Promise<{parsed: ParseBody; savedIdOf: (leg: Leg) => number}> {
    const file = sampleFile('broker');
    const uploaded = await jsonFrom<UploadedInfo>(await page.request.post(UPLOAD_PATH, {multipart: {broker_id: String(broker.id), file}}), `upload ${file.name}`);
    expect(uploaded.compatible_plugins ?? [], `premise: ${ACCOUNTS.broker.plugin} reads its own sample`).toContain(ACCOUNTS.broker.plugin);
    const parsed = await jsonFrom<ParseBody>(await page.request.post(`${FILES_PATH}/${uploaded.file_id}/parse`, {data: {plugin_code: ACCOUNTS.broker.plugin, broker_id: broker.id}}), `parse ${file.name}`);
    const deleted = await jsonFrom<DeleteResult>(await page.request.delete(`${FILES_PATH}/${uploaded.file_id}`), `delete ${file.name}`);
    expect(deleted, 'the parsed file is deleted').toMatchObject({success: true, file_id: uploaded.file_id});

    const creates = parsed.transactions.filter((tx) => SAVED_TYPES.has(tx.type) && tx.asset_id == null);
    const validated = await jsonFrom<{issues?: unknown[]}>(await page.request.post(VALIDATE_PATH, {data: {creates}}), 'validate the broker account’s cash rows');
    expect(validated.issues ?? [], 'the cash rows validate as parsed').toEqual([]);
    const committed = await jsonFrom<CommitResult>(await page.request.post(COMMIT_PATH, {data: {creates}}), 'save the broker account’s cash rows');
    expect(committed.committed, `the cash rows are saved: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    const idByIndex = new Map((committed.results ?? []).filter((result) => result.operation === 'create').map((result) => [result.index ?? -1, result.ids?.[0] ?? -1]));
    expect([...idByIndex.keys()].sort(byNumber), 'one saved id per cash row').toEqual(creates.map((_, index) => index));
    const idByText = new Map(creates.map((tx, index) => [tx.description ?? '', idByIndex.get(index) ?? -1]));
    expect(idByText.size, 'premise: each cash row has a text of its own (the exporter id)').toBe(creates.length);
    return {
        parsed,
        savedIdOf: (leg) => {
            const id = idByText.get(leg.description);
            if (id === undefined) throw new Error(`No saved row carries "${leg.description}"`);
            return id;
        },
    };
}

/** The transactions of one broker, as the API serves them. */
async function transactionsOn(page: Page, brokerId: number): Promise<SavedTx[]> {
    return jsonFrom<SavedTx[]>(await page.request.get(`${TRANSACTIONS_PATH}?broker_id=${brokerId}`), `read the transactions of broker ${brokerId}`);
}

/** A saved transaction as the assertions compare it. */
function savedFacts(tx: SavedTx | undefined): {type: string; related: number | null; amount: number; description: string} | undefined {
    return tx && {type: tx.type, related: tx.related_transaction_id ?? null, amount: amountOf(tx.cash), description: tx.description ?? ''};
}

// ---------------------------------------------------------------------------
// The wizard
// ---------------------------------------------------------------------------

function isCall(method: string, pathname: string | RegExp): (response: Response) => boolean {
    return (response) => {
        if (response.request().method() !== method) return false;
        const actual = new URL(response.url()).pathname;
        return typeof pathname === 'string' ? actual === pathname : pathname.test(actual);
    };
}

/** The responses `action` produces that `matches` picks: exactly `expected` of them. Armed before the action — a response is an edge, not a state. */
async function responsesDuring(page: Page, matches: (response: Response) => boolean, expected: number, what: string, action: () => Promise<void>): Promise<Response[]> {
    const seen: Response[] = [];
    const listener = (response: Response) => {
        if (matches(response)) seen.push(response);
    };
    page.on('response', listener);
    try {
        await action();
        await expect.poll(() => seen.length, {message: `${what}: ${expected} response(s)`, timeout: STEP_TIMEOUT}).toBe(expected);
    } finally {
        page.off('response', listener);
    }
    return seen;
}

async function goToTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open the wizard from the toolbar (inside a fresh, empty editor); return step 1 once it has settled. */
async function openImportWizard(page: Page): Promise<Locator> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: UI_TIMEOUT});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1, 15_000);
    return step1;
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/**
 * Drop one export on step 1 and assign it to `brokerId` through the broker select of its own row. The row is the one
 * step 1 did not list before — the ids in `staged`, to which its own is then added — never a position.
 */
async function stageFile(page: Page, step1: Locator, file: SampleFile, brokerId: number, staged: string[]): Promise<void> {
    if (staged.length > 0) {
        // A file in the list folds the drop zone: unfold it the way a user does.
        const more = page.getByTestId('import-wizard-upload-more');
        await expect(more, 'the drop zone folded after the first file').toBeVisible({timeout: UI_TIMEOUT});
        await more.click();
    }
    const uploader = step1.getByTestId('file-uploader');
    await expect(uploader, 'the drop zone is open').toBeVisible({timeout: UI_TIMEOUT});
    await uploader.getByTestId('file-input').setInputFiles(file);
    await expect(step1.locator('tbody tr[data-row-id]'), `${file.name} joins the step-1 list`).toHaveCount(staged.length + 1, {timeout: UI_TIMEOUT});
    const row = step1.locator(`tbody tr[data-row-id]${staged.map((id) => `:not([data-row-id="${id}"])`).join('')}`);
    await expect(row, `one row of step 1 is ${file.name}`).toHaveCount(1);
    const rowId = await row.getAttribute('data-row-id');
    if (!rowId) throw new Error(`The step-1 row of ${file.name} carries no data-row-id`);
    await optionsClosed(page);
    await row.getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option, `broker ${brokerId} is offered for ${file.name}`).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    staged.push(rowId);
}

/**
 * Continue on step 1: every staged file is uploaded, the uploads are checked against their brokers' default
 * plugins — each file is on the broker whose default plugin reads it, so nothing is asked — and step 2 settles.
 */
async function continueToSelection(page: Page, expected: number): Promise<UploadedInfo[]> {
    const next = page.getByTestId('import-wizard-next');
    await expect(next, 'every staged file has its broker').toBeEnabled({timeout: UI_TIMEOUT});
    const responses = await responsesDuring(page, isCall('POST', UPLOAD_PATH), expected, 'Continue uploads every staged file', () => next.click());
    const uploads = await Promise.all(responses.map((response) => jsonFrom<UploadedInfo>(response, 'upload a staged file')));
    await expect(currentStep(page), 'the uploads are reviewed and the wizard goes on to the file selection').toHaveAttribute('data-step-id', 'select', {timeout: STEP_TIMEOUT});
    await expect(page.getByTestId('import-broker-mismatch-modal'), 'each file is on the broker whose default plugin reads it: no question').toHaveCount(0);
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step2, STEP_TIMEOUT);
    return uploads;
}

/** The upload of `file`, by its unique name: on `brokerId`, read by that broker's default plugin. */
function uploadOf(uploads: readonly UploadedInfo[], file: SampleFile, brokerId: number, plugin: string): UploadedInfo {
    const found = uploads.filter((upload) => upload.filename === file.name);
    expect(found, `${file.name} is uploaded once`).toHaveLength(1);
    expect(found[0].target_broker_id, `${file.name} lands on broker ${brokerId}`).toBe(brokerId);
    expect(found[0].compatible_plugins ?? [], `premise: ${plugin}, the default plugin of broker ${brokerId}, reads ${file.name}`).toContain(plugin);
    return found[0];
}

/**
 * Step 2 → 3: the files uploaded in step 1 arrive selected under their brokers; Parse analyses each with the plugin
 * of its broker. Returns, per uploaded file, its parse request and response.
 */
async function parseUploads(page: Page, uploads: readonly UploadedInfo[]): Promise<Map<string, {request: {plugin_code?: string; broker_id?: number}; body: ParseBody}>> {
    const step2 = page.getByTestId('import-wizard-step2');
    for (const upload of uploads) {
        await expect(step2.getByTestId(`import-wizard-broker-files-${upload.target_broker_id}`).getByTestId(`dt-row-checkbox-${upload.file_id}`), `${upload.filename}, uploaded in step 1, arrives selected under its broker`).toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
    }
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse).toBeEnabled({timeout: UI_TIMEOUT});
    const responses = await responsesDuring(page, isCall('POST', PARSE_PATH), uploads.length, 'Parse analyses every selected file', () => parse.click());
    await expect(page.getByTestId('import-wizard-step3'), 'the wizard is on the analysis').toBeVisible({timeout: UI_TIMEOUT});
    await waitForParseVerdict(page);
    const parsed = new Map<string, {request: {plugin_code?: string; broker_id?: number}; body: ParseBody}>();
    for (const response of responses) {
        const fileId = PARSE_PATH.exec(new URL(response.url()).pathname)?.[1] ?? '';
        parsed.set(fileId, {request: response.request().postDataJSON() as {plugin_code?: string; broker_id?: number}, body: await jsonFrom<ParseBody>(response, `parse file ${fileId}`)});
    }
    expect([...parsed.keys()].sort(), 'one parse per uploaded file').toEqual(uploads.map((upload) => upload.file_id).sort());
    return parsed;
}

/** The review with nothing selected: deselect all, and say so. */
async function deselectAll(page: Page, step4: Locator): Promise<void> {
    await page.getByTestId('import-wizard-deselect-all').click();
    await expect(step4, 'nothing is selected').toHaveAttribute('data-selected-count', '0', {timeout: UI_TIMEOUT});
}

/**
 * Only the rows without an instrument selected: the asset column filtered on "no asset", then "select visible".
 * Nothing waits for an asset, nothing is created. `expected` is the number of such rows in the parses.
 */
async function selectOnlyCashRows(page: Page, step4: Locator, expected: number): Promise<void> {
    await deselectAll(page, step4);
    const trigger = step4.getByTestId('col-filter-trigger-asset');
    await trigger.click();
    const filter = step4.getByTestId('dt-header-asset').getByTestId('column-filter');
    await expect(filter).toBeVisible({timeout: UI_TIMEOUT});
    const noAsset = filter.getByTestId('filter-enum-option-__null__');
    await expect(noAsset).toHaveAttribute('data-checked', 'false');
    await noAsset.click();
    await expect(noAsset).toHaveAttribute('data-checked', 'true');
    await trigger.click();
    await expect(filter).toBeHidden({timeout: UI_TIMEOUT});
    await expect(step4.locator('tbody tr[data-row-id]'), `the review shows the ${expected} rows without an instrument, on one page`).toHaveCount(expected, {timeout: UI_TIMEOUT});
    await page.getByTestId('import-wizard-select-visible').click();
    await expect(step4, `the ${expected} rows without an instrument are selected`).toHaveAttribute('data-selected-count', String(expected), {timeout: UI_TIMEOUT});
}

/**
 * A promote-suggest answer whose request asks every leg in `legs` as a NEW row (a negative id): the editor asks the
 * database about the rows it was just handed. Waited for from now on — call it before the Import.
 */
function promoteSuggestAsking(page: Page, legs: ReadonlyArray<{brokerId: number; date: string; type: string}>): Promise<Response> {
    const answer = page.waitForResponse(
        (response) => {
            if (!isCall('POST', PROMOTE_SUGGEST_PATH)(response)) return false;
            let inputs: unknown;
            try {
                inputs = response.request().postDataJSON();
            } catch {
                return false;
            }
            return Array.isArray(inputs) && legs.every((leg) => (inputs as SuggestInput[]).some((input) => input.id < 0 && input.broker_id === leg.brokerId && input.date === leg.date && input.type === leg.type));
        },
        {timeout: STEP_TIMEOUT},
    );
    // Awaited later, once the editor is up: a failure before then must not surface as an unhandled rejection.
    answer.catch(() => undefined);
    return answer;
}

/** Import: the wizard hands over and closes; the editor underneath holds the batch, settled. */
async function importToEditor(page: Page): Promise<Locator> {
    const importButton = page.getByTestId('import-wizard-import');
    await expect(importButton, 'Import is enabled: rows are selected, none waits for an asset').toBeEnabled({timeout: 15_000});
    await importButton.click();
    await expect(page.getByTestId('import-wizard-stepper'), 'the wizard hands over and closes').toHaveCount(0, {timeout: STEP_TIMEOUT});
    const root = page.getByTestId('tx-bulk-modal-root');
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(root, STEP_TIMEOUT);
    return root;
}

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

function editorRows(page: Page): Locator {
    return page.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]');
}

/** The date cells of the editor rows dated `day`; with `partnerDay`, only the rows paired with a leg of that day ('' = standalone). */
function dateCells(page: Page, day: string, partnerDay?: string): Locator {
    const partner = partnerDay === undefined ? '' : `[data-partner-date="${partnerDay}"]`;
    return page.getByTestId('tx-bulk-body').locator(`[data-testid="tx-bulk-date"][data-date="${day}"]${partner}`);
}

/** The one editor row dated `day`, found by its date cell — never by its position. */
async function editorRowOn(page: Page, day: string): Promise<Locator> {
    const cell = dateCells(page, day);
    await expect(cell, `one row of the editor is dated ${day}`).toHaveCount(1, {timeout: UI_TIMEOUT});
    const rowId = await cell.getAttribute('data-row-id');
    if (!rowId) throw new Error(`The editor row dated ${day} carries no data-row-id`);
    return page.getByTestId('tx-bulk-body').locator(`tbody tr[data-row-id="${rowId}"]`);
}

/** Open the actions menu of an editor row (its ⋮); return the menu. */
async function openRowMenu(page: Page, row: Locator): Promise<Locator> {
    const rowId = await row.getAttribute('data-row-id');
    await row.hover();
    const kebab = row.getByTestId(`row-actions-${rowId}`);
    await expect(kebab).toBeVisible({timeout: UI_TIMEOUT});
    await kebab.click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: UI_TIMEOUT});
    return menu;
}

/** Close an open actions menu: Escape, which the menu takes for itself — the editor under it stays open. */
async function closeRowMenu(page: Page): Promise<void> {
    await page.keyboard.press('Escape');
    await expect(page.getByTestId('context-menu')).toBeHidden({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('tx-bulk-modal-root'), 'Escape closed the menu, not the editor').toBeVisible();
}

/** The proposals of the green banner. */
function bannerItems(page: Page): Locator {
    return page.getByTestId('promote-suggest-banner').locator('[data-testid^="promote-suggest-item-"]');
}

/**
 * Open the merge dialog of banner proposal `index` and return the text it proposes for the pair: the two legs'
 * texts joined, one per line. The two texts differ, so the dialog always opens; it is left open.
 */
async function openMergeOf(page: Page, index: number): Promise<string> {
    await page.getByTestId(`promote-suggest-link-${index}`).click();
    await expect(page.getByTestId('promote-merge-confirm'), 'two texts that differ: merging asks which to keep').toBeVisible({timeout: UI_TIMEOUT});
    const text = page.getByTestId('promote-merge-desc-input');
    await expect(text, 'the dialog proposes both texts, one per line').toHaveValue(/\n/, {timeout: UI_TIMEOUT});
    return text.inputValue();
}

/** Bring a checkbox to `checked`, whatever state it starts in, and prove it (a blind click is a toggle). */
async function ensureChecked(checkbox: Locator): Promise<void> {
    await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
}

/**
 * Save All, once the editor has settled and holds no import todo (a todo would ask for a confirmation first): returns
 * the commit request — the batch as sent — and its answer, which must say committed. The editor then closes.
 */
async function saveAll(page: Page): Promise<{payload: CommitPayload; result: CommitResult}> {
    const root = page.getByTestId('tx-bulk-modal-root');
    await waitForSettled(root, STEP_TIMEOUT);
    await expect(root.getByTestId('tx-bulk-todo-blockers'), 'premise: no import todo holds the save').toHaveCount(0);
    await expect(root.getByTestId('tx-bulk-todo-warnings'), 'premise: no import todo asks for a confirmation').toHaveCount(0);
    const commit = root.getByTestId('tx-bulk-commit');
    await expect(commit).toBeEnabled({timeout: UI_TIMEOUT});
    const [request] = await Promise.all([page.waitForRequest((sent) => sent.method() === 'POST' && new URL(sent.url()).pathname === COMMIT_PATH, {timeout: STEP_TIMEOUT}), commit.click()]);
    const response = await request.response();
    if (!response) throw new Error('The save completed without an HTTP response');
    const result = await jsonFrom<CommitResult>(response, 'save the editor');
    expect(result.committed, `the batch is saved: ${JSON.stringify(result.issues ?? [])}`).toBe(true);
    await expect(page.getByTestId('tx-bulk-modal'), 'the editor closes once saved').toBeHidden({timeout: UI_TIMEOUT});
    return {payload: request.postDataJSON() as CommitPayload, result};
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard + bulk editor — Scalable internal transfers merged into Cash Transfers', () => {
    let owned: Owned = {user: null, brokerIds: []};

    test.beforeEach(() => {
        owned = {user: null, brokerIds: []};
    });

    // afterEach, not `finally`: a cleanup throwing from `finally` would replace the assertion error it follows.
    test.afterEach(async ({page, request}) => {
        await cleanupOwned(page, request, owned);
    });

    test('S1: both exports in one wizard run — the banner proposes the two transfers, one is merged and saved as a linked Cash Transfer', async ({page, request}, testInfo) => {
        test.setTimeout(180_000);
        const brokers = await startOnOwnAccount(page, request, owned, `scs1_${testInfo.project.name}`);

        // ① Step 1: each export on its own broker, both uploaded by one Continue — nothing to ask about either.
        await goToTransactions(page);
        const step1 = await openImportWizard(page);
        const files: Record<Account, SampleFile> = {broker: sampleFile('broker'), overnight: sampleFile('overnight')};
        const staged: string[] = [];
        await stageFile(page, step1, files.broker, brokers.broker.id, staged);
        await stageFile(page, step1, files.overnight, brokers.overnight.id, staged);
        const uploads = await continueToSelection(page, 2);
        const upload: Record<Account, UploadedInfo> = {
            broker: uploadOf(uploads, files.broker, brokers.broker.id, ACCOUNTS.broker.plugin),
            overnight: uploadOf(uploads, files.overnight, brokers.overnight.id, ACCOUNTS.overnight.plugin),
        };

        // ② Step 2 → 3: each file read by its broker's default plugin.
        const parses = await parseUploads(page, uploads);
        const parsed = {} as Record<Account, ParseBody>;
        for (const account of Object.keys(ACCOUNTS) as Account[]) {
            const entry = parses.get(upload[account].file_id);
            expect(entry?.request, `${files[account].name} is parsed with ${ACCOUNTS[account].plugin}, for its broker`).toMatchObject({plugin_code: ACCOUNTS[account].plugin, broker_id: brokers[account].id});
            parsed[account] = entry!.body;
        }
        const transfers = transfersIn(parsed);
        const cashCount = cashRows(parsed.broker).length + cashRows(parsed.overnight).length;

        // ③ Review: only the rows without an instrument (nothing to resolve), then Import. The editor asks the
        // database about the new rows, under negative ids.
        const step4 = await continueToStep(page, [parsed.broker, parsed.overnight], 'review');
        await selectOnlyCashRows(page, step4, cashCount);
        const allLegs = transfers.flatMap((transfer) => [transfer.out, transfer.in]).map((leg) => ({brokerId: brokers[leg.account].id, date: leg.day, type: leg.type}));
        const suggestAnswer = promoteSuggestAsking(page, allLegs);
        await importToEditor(page);

        // ④ The editor holds the cash rows of both files; each transfer's two legs stand apart.
        await expect(editorRows(page), `the editor holds the ${cashCount} rows handed over`).toHaveCount(cashCount, {timeout: UI_TIMEOUT});
        for (const transfer of transfers) {
            await expect(dateCells(page, transfer.day, ''), `the two legs of the ${transfer.day} transfer are two standalone rows`).toHaveCount(2);
        }
        const suggest = await suggestAnswer;
        const asked = suggest.request().postDataJSON() as SuggestInput[];
        expect(asked, 'every new row with a type, a broker, a date and an amount is asked to the database').toHaveLength(cashCount);
        expect(
            asked.every((input) => input.id < 0),
            'new rows are asked under negative ids',
        ).toBe(true);
        expect(new Set(asked.map((input) => input.id)).size, 'each new row under an id of its own').toBe(asked.length);
        const answer = await jsonFrom<SuggestAnswer>(suggest, 'the database search for the new rows');
        expect(Object.values(answer.results).flat(), 'nothing of the account is saved yet: the database proposes nothing').toEqual([]);

        // ⑤ The banner proposes the two transfers. A proposal is identified by the texts its merge dialog joins.
        const items = bannerItems(page);
        await expect(items, 'the banner proposes exactly the two internal transfers').toHaveCount(2, {timeout: UI_TIMEOUT});
        const second = transferJoinedBy(transfers, await openMergeOf(page, 1));
        // Escape cancels the dialog: nothing is merged. Pressed inside the dialog — it focuses itself only on the next
        // frame, and an Escape that reached the editor underneath would ask to discard it instead.
        await page.getByTestId('promote-merge-desc-input').press('Escape');
        await expect(page.getByTestId('promote-merge-confirm'), 'the dialog is cancelled').toBeHidden({timeout: UI_TIMEOUT});
        await expect(items, 'a cancelled merge changes nothing').toHaveCount(2);
        await expect(editorRows(page)).toHaveCount(cashCount);

        const joined = await openMergeOf(page, 0);
        const merged = transferJoinedBy(transfers, joined);
        expect([merged.day, second.day].sort(), 'the two proposals are the two internal transfers').toEqual(TRANSFERS.map((transfer) => transfer.day).sort());
        const kept = second;
        test.info().annotations.push({type: 'merged transfer', description: `${merged.day} (${merged.out.account} → ${merged.in.account}, ${merged.amount} EUR)`});

        // ⑥ The dialog accepted with the joined text: the two legs become one paired row, the other proposal remains.
        await page.getByTestId('promote-merge-confirm').click();
        await expect(page.getByTestId('promote-merge-confirm'), 'the merge is accepted').toBeHidden({timeout: UI_TIMEOUT});
        await expect(editorRows(page), 'the two legs of the merged transfer are one row').toHaveCount(cashCount - 1, {timeout: UI_TIMEOUT});
        await expect(dateCells(page, merged.day, merged.day), `the ${merged.day} legs are paired`).toHaveCount(1);
        await expect(dateCells(page, kept.day, ''), `the ${kept.day} legs still stand apart`).toHaveCount(2);
        await expect(items, 'the other transfer is still proposed').toHaveCount(1);

        // ⑦ Save: the merged legs go as a CASH_TRANSFER pair with one link and the joined text; the other as they were.
        await expect(page.getByTestId('tx-bulk-suggest-import'), 'nothing saved to propose: no 💡').toHaveCount(0);
        const {payload} = await saveAll(page);
        const creates = payload.creates ?? [];
        expect(creates, `the ${cashCount} rows are created`).toHaveLength(cashCount);
        expect(payload.promotes ?? [], 'two new rows are merged in the editor itself: no promote').toEqual([]);
        const pair = creates.filter((create) => create.type === 'CASH_TRANSFER');
        const sortLegs = <T extends {broker_id?: number}>(legs: T[]) => [...legs].sort((a, b) => (a.broker_id ?? 0) - (b.broker_id ?? 0));
        expect(
            sortLegs(pair).map((create) => ({broker_id: create.broker_id, date: create.date, amount: amountOf(create.cash), description: create.description})),
            'the merged transfer goes as two CASH_TRANSFER legs, each on its own broker with its own amount, both with the joined text',
        ).toEqual(sortLegs([merged.out, merged.in].map((leg) => ({broker_id: brokers[leg.account].id, date: merged.day, amount: leg.amount, description: joined}))));
        expect(pair[0].link_uuid, 'the two legs share one link').toBeTruthy();
        expect(pair[1].link_uuid).toBe(pair[0].link_uuid);
        expect(
            creates
                .filter((create) => create.date === kept.day)
                .map((create) => [create.type, create.link_uuid ?? null])
                .sort(),
            `the ${kept.day} legs go unmerged`,
        ).toEqual([
            ['DEPOSIT', null],
            ['WITHDRAWAL', null],
        ]);

        // ⑧ The API: the merged legs are CASH_TRANSFER, linked to each other, on the two brokers, with the joined text.
        const saved: Record<Account, SavedTx[]> = {broker: await transactionsOn(page, brokers.broker.id), overnight: await transactionsOn(page, brokers.overnight.id)};
        for (const account of Object.keys(ACCOUNTS) as Account[]) {
            expect(saved[account], `every cash row of the ${ACCOUNTS[account].label} is saved on its broker`).toHaveLength(cashRows(parsed[account]).length);
        }
        const legsOn = (leg: Leg, day: string) => saved[leg.account].filter((tx) => tx.date === day);
        expect(legsOn(merged.out, merged.day), `one transaction on ${merged.day} on the paying broker`).toHaveLength(1);
        expect(legsOn(merged.in, merged.day), `one transaction on ${merged.day} on the receiving broker`).toHaveLength(1);
        const [outLeg] = legsOn(merged.out, merged.day);
        const [inLeg] = legsOn(merged.in, merged.day);
        expect(savedFacts(outLeg), 'the paying leg: a CASH_TRANSFER linked to the receiving one').toEqual({type: 'CASH_TRANSFER', related: inLeg.id, amount: -merged.amount, description: joined});
        expect(savedFacts(inLeg), 'the receiving leg: a CASH_TRANSFER linked to the paying one').toEqual({type: 'CASH_TRANSFER', related: outLeg.id, amount: merged.amount, description: joined});
        expect([...legsOn(kept.out, kept.day), ...legsOn(kept.in, kept.day)].map((tx) => [tx.type, tx.related_transaction_id ?? null]).sort(), `the ${kept.day} transfer stays a withdrawal and a deposit, unlinked`).toEqual([
            ['DEPOSIT', null],
            ['WITHDRAWAL', null],
        ]);
    });

    test('S2: the broker account saved first — the 💡 of the new transfer legs adds its saved side, and the new + saved pair is merged into a linked Cash Transfer', async ({page, request}, testInfo) => {
        test.setTimeout(180_000);
        const brokers = await startOnOwnAccount(page, request, owned, `scs2_${testInfo.project.name}`);

        // ① An earlier session: the broker account's cash rows saved over the API.
        const earlier = await saveBrokerCashRowsOverApi(page, brokers.broker);

        // ② This session: the overnight account's export through the wizard, on its own broker.
        // A full load once the rows are saved: the editor's picker reads the transactions the page loaded.
        await goToTransactions(page);
        const step1 = await openImportWizard(page);
        const file = sampleFile('overnight');
        await stageFile(page, step1, file, brokers.overnight.id, []);
        const uploads = await continueToSelection(page, 1);
        const upload = uploadOf(uploads, file, brokers.overnight.id, ACCOUNTS.overnight.plugin);
        const entry = (await parseUploads(page, uploads)).get(upload.file_id);
        expect(entry?.request, `${file.name} is parsed with ${ACCOUNTS.overnight.plugin}, for its broker`).toMatchObject({plugin_code: ACCOUNTS.overnight.plugin, broker_id: brokers.overnight.id});
        const parsed: Record<Account, ParseBody> = {broker: earlier.parsed, overnight: entry!.body};
        const transfers = transfersIn(parsed);
        const rowCount = parsed.overnight.transactions.length;
        expect(cashRows(parsed.overnight), 'premise: the overnight account’s export holds cash rows only').toHaveLength(rowCount);
        const quietRows = parsed.overnight.transactions.filter((tx) => tx.date === QUIET_DAY);
        expect(
            quietRows.map((tx) => tx.type),
            `premise: the overnight account’s only row on ${QUIET_DAY} is a deposit from the bank, no transfer`,
        ).toEqual(['DEPOSIT']);

        // The saved side and the new side of each transfer.
        const byDay = (day: string) => {
            const transfer = transfers.find((candidate) => candidate.day === day);
            if (!transfer) throw new Error(`No internal transfer on ${day}`);
            return {saved: transfer.out.account === 'broker' ? transfer.out : transfer.in, fresh: transfer.out.account === 'overnight' ? transfer.out : transfer.in};
        };
        const june = byDay('2026-06-01');
        const april = byDay('2026-04-02');
        const savedJuneId = earlier.savedIdOf(june.saved);
        const savedAprilId = earlier.savedIdOf(april.saved);

        // ③ Review: every row selected, then Import. The editor asks the database about the new rows.
        const step4 = await continueToStep(page, parsed.overnight, 'review');
        await deselectAll(page, step4);
        await page.getByTestId('import-wizard-select-all').click();
        await expect(step4, `the ${rowCount} rows are selected`).toHaveAttribute('data-selected-count', String(rowCount), {timeout: UI_TIMEOUT});
        await expect(step4).toHaveAttribute('data-total-count', String(rowCount));
        const freshLegs = [june.fresh, april.fresh].map((leg) => ({brokerId: brokers.overnight.id, date: leg.day, type: leg.type}));
        const suggestAnswer = promoteSuggestAsking(page, freshLegs);
        await importToEditor(page);
        await expect(editorRows(page), `the editor holds the ${rowCount} rows handed over`).toHaveCount(rowCount, {timeout: UI_TIMEOUT});

        // ④ The database proposes, for each new transfer leg, its saved other side — and nothing for any other row.
        const suggest = await suggestAnswer;
        const asked = suggest.request().postDataJSON() as SuggestInput[];
        expect(asked, 'every new row is asked').toHaveLength(rowCount);
        expect(
            asked.every((input) => input.id < 0),
            'new rows are asked under negative ids',
        ).toBe(true);
        const keyOf = (leg: Leg) => asked.find((input) => input.broker_id === brokers.overnight.id && input.date === leg.day && input.type === leg.type)?.id;
        const expectedCandidates = Object.fromEntries(asked.map((input) => [String(input.id), input.id === keyOf(june.fresh) ? [savedJuneId] : input.id === keyOf(april.fresh) ? [savedAprilId] : []]));
        const answer = await jsonFrom<SuggestAnswer>(suggest, 'the database search for the new rows');
        expect(Object.fromEntries(Object.entries(answer.results).map(([key, candidates]) => [key, candidates.map((candidate) => candidate.id)])), 'each new transfer leg is offered its saved other side, and no other row anything').toEqual(expectedCandidates);

        // ⑤ The 💡: in the toolbar, and in the menu of the two new transfer legs only. No banner yet: the other sides
        // are not in the editor.
        await expect(page.getByTestId('tx-bulk-suggest-import'), 'the toolbar offers the saved sides').toBeVisible({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('promote-suggest-banner'), 'nothing to merge inside the editor yet').toHaveCount(0);
        let menu = await openRowMenu(page, await editorRowOn(page, QUIET_DAY));
        await expect(menu.getByTestId('context-menu-action-mark-delete'), 'the menu of the deposit from the bank is open').toBeVisible();
        await expect(menu.getByTestId('context-menu-action-suggest'), 'nothing saved pairs with the deposit from the bank: no 💡').toBeHidden();
        await closeRowMenu(page);
        menu = await openRowMenu(page, await editorRowOn(page, april.fresh.day));
        await expect(menu.getByTestId('context-menu-action-suggest'), `the ${april.fresh.day} leg has its 💡`).toBeVisible();
        await closeRowMenu(page);
        menu = await openRowMenu(page, await editorRowOn(page, june.fresh.day));
        const lightbulb = menu.getByTestId('context-menu-action-suggest');
        await expect(lightbulb, `the ${june.fresh.day} leg has its 💡`).toBeVisible();
        await lightbulb.click();

        // ⑥ The picker offers the saved sides of the two transfers; the June one is added to the editor.
        const picker = page.getByTestId('tx-picker-modal');
        await expect(picker, 'the 💡 opens the picker of the saved sides').toBeVisible({timeout: UI_TIMEOUT});
        const offered = picker.locator('tbody tr[data-row-id]');
        await expect(offered, 'the picker offers the two saved sides, nothing else').toHaveCount(2, {timeout: UI_TIMEOUT});
        expect((await offered.evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id') ?? ''))).sort()).toEqual([`tx-${savedJuneId}`, `tx-${savedAprilId}`].sort());
        await ensureChecked(picker.getByTestId(`dt-row-checkbox-tx-${savedJuneId}`));
        const add = picker.getByTestId('tx-picker-add');
        await expect(add).toBeEnabled({timeout: UI_TIMEOUT});
        await add.click();
        await expect(picker, 'the picker closes on Add').toBeHidden({timeout: UI_TIMEOUT});
        await expect(editorRows(page), 'the saved side joins the editor').toHaveCount(rowCount + 1, {timeout: UI_TIMEOUT});
        await expect(dateCells(page, june.fresh.day, ''), `the new and the saved ${june.fresh.day} legs stand apart`).toHaveCount(2);

        // ⑦ The banner proposes the new + saved pair; its dialog joins the two texts; accepted.
        const items = bannerItems(page);
        await expect(items, 'the banner proposes the one pair whose two sides are in the editor').toHaveCount(1, {timeout: UI_TIMEOUT});
        const joined = await openMergeOf(page, 0);
        expect(transferJoinedBy(transfers, joined).day, 'the proposal is the June transfer: the new leg and its saved side').toBe(june.fresh.day);
        await page.getByTestId('promote-merge-confirm').click();
        await expect(page.getByTestId('promote-merge-confirm'), 'the merge is accepted').toBeHidden({timeout: UI_TIMEOUT});
        await expect(editorRows(page), 'the two June legs are one row').toHaveCount(rowCount, {timeout: UI_TIMEOUT});
        await expect(dateCells(page, june.fresh.day, june.fresh.day), 'the June legs are paired').toHaveCount(1);
        await expect(items, 'nothing else to merge in the editor').toHaveCount(0);
        await expect(page.getByTestId('tx-bulk-suggest-import'), 'the April leg still offers its saved side').toBeVisible();

        // ⑧ Save: the new leg is created under the link the promote names; the saved side travels in the promote.
        const {payload} = await saveAll(page);
        const creates = payload.creates ?? [];
        expect(creates, `the ${rowCount} new rows are created`).toHaveLength(rowCount);
        const newLeg = creates.filter((create) => create.date === june.fresh.day);
        expect(newLeg, 'one new June leg').toHaveLength(1);
        expect({broker_id: newLeg[0].broker_id, type: newLeg[0].type, amount: amountOf(newLeg[0].cash), description: newLeg[0].description}, 'the new leg goes with its own type — the backend promotes it from the two source types — and the joined text').toEqual({
            broker_id: brokers.overnight.id,
            type: june.fresh.type,
            amount: june.fresh.amount,
            description: joined,
        });
        expect(newLeg[0].link_uuid, 'the new leg carries the link the promote names').toBeTruthy();
        expect(payload.promotes, 'one promote: the saved side with the new leg’s link, and the joined text').toEqual([expect.objectContaining({id_a: savedJuneId, link_uuid_b: newLeg[0].link_uuid, resolved_fields: expect.objectContaining({description: joined})})]);
        expect(payload.updates ?? [], 'the saved side is not sent as an update').toEqual([]);

        // ⑨ The API: the saved leg and the new leg are CASH_TRANSFER, linked to each other; April stays apart.
        const onBroker = await transactionsOn(page, brokers.broker.id);
        const onOvernight = await transactionsOn(page, brokers.overnight.id);
        expect(onOvernight, 'every row of the import is saved on the overnight account’s broker').toHaveLength(rowCount);
        const newJune = onOvernight.filter((tx) => tx.date === june.fresh.day);
        expect(newJune, 'one June transaction on the overnight account’s broker').toHaveLength(1);
        expect(savedFacts(onBroker.find((tx) => tx.id === savedJuneId)), 'the saved leg: a CASH_TRANSFER linked to the new one, with the joined text').toEqual({
            type: 'CASH_TRANSFER',
            related: newJune[0].id,
            amount: june.saved.amount,
            description: joined,
        });
        expect(savedFacts(newJune[0]), 'the new leg: a CASH_TRANSFER linked to the saved one, with the joined text').toEqual({type: 'CASH_TRANSFER', related: savedJuneId, amount: june.fresh.amount, description: joined});
        expect(savedFacts(onBroker.find((tx) => tx.id === savedAprilId)), 'the saved April leg is untouched').toEqual({type: april.saved.type, related: null, amount: april.saved.amount, description: april.saved.description});
        expect(
            onOvernight.filter((tx) => tx.date === april.fresh.day).map((tx) => savedFacts(tx)),
            'the new April leg is saved as imported, unlinked',
        ).toEqual([{type: april.fresh.type, related: null, amount: april.fresh.amount, description: april.fresh.description}]);
    });
});
