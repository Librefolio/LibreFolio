/**
 * The import wizard's corridor, shared: a file of the test's own, selected in step 2, parsed,
 * and walked from the analysis to a later step.
 *
 * ## Why this exists (plan 33_e2eImportInfra, §1.3)
 *
 * Every import spec carried its own copy of this walk, and every copy asked the wizard with
 * probes. `isVisible({timeout})` ignores its timeout: it answers about *this instant*. So a
 * step that rendered a moment late was taken for absent and skipped, and the test then timed
 * out waiting for the review while the wizard sat on the corrections (tx-brim-import T1,
 * tx-import-ca-contract CAC-011/012). Step 2 was worse: "the first checkbox" over every broker
 * panel, or the first row named like a seeded sample on the *current page* of its table. The
 * files accumulated by earlier runs moved the target to another page or another panel, and the
 * click went somewhere else or nowhere (tx-import-resolution IWR-001).
 *
 * ## What it does instead
 *
 * - **The file is the test's own.** {@link uploadOwnedReport} uploads a copy of a sample to the
 *   broker the test names, under a unique name; {@link deleteOwnedReports} deletes it afterwards.
 *   No two tests parse the same file — a parse moves the file and rewrites its metadata — and
 *   nothing is left behind for a later broker to inherit.
 * - **Step 2 is searched, not assumed.** {@link selectBrokerFile} opens the broker's panel by
 *   its `aria-expanded` state and walks the panel's pages until the row is there; when it is
 *   not, the failure says how many pages were searched.
 * - **The parse response decides.** {@link parseSelectedFile} captures the parse on the wire as
 *   Parse is clicked. Whether the notices' confirmation must be read past is then known from
 *   the response, never probed for.
 * - **The stepper says where the wizard is.** {@link continueToStep} reads the current step
 *   (`import-wizard-stepper [aria-current="step"][data-step-id]`), acts on it — the corrections
 *   are kept as read, deterministically — clicks that step's own Continue and waits for the
 *   marker to move. The steps crossed are annotated on the test.
 *
 * The model is `continueToReview` in tx-import-degiro.spec.ts.
 */

import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';
import {expect, test, type Locator, type Page} from './playwright';
import {waitForParseVerdict, waitForSettled} from './app-events';
import {findAcrossPages} from './paging';
import {uniqueSuffix} from './unique';

const API = '/api/v1';
const BROKERS_PATH = `${API}/brokers`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const FILES_PATH = `${API}/brokers/import/files`;
const SAMPLE_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../backend/app/services/brim_providers/sample_reports');
const UI_TIMEOUT = 10_000;
/** A step change waits on the server: candidates, the duplicate re-check. */
const STEP_TIMEOUT = 30_000;
/** Five files a page: 500 files on one broker before the walk gives up. A lane that ran many times without a cleanup holds dozens. */
const MAX_FILE_PAGES = 100;

/** The steps after the analysis, in the wizard's order (ImportWizardModal `STEP_DEFS`). `gapFix` is reached only from the review's Import. */
const LATER_STEPS = ['assets', 'fix', 'duplicates', 'review'] as const;
type LaterStep = (typeof LATER_STEPS)[number];
const LATER_STEP = /^(assets|fix|duplicates|review)$/;
const STEP_CONTAINER: Record<LaterStep, string> = {
    assets: 'import-wizard-step-assets',
    fix: 'import-wizard-step-fix',
    duplicates: 'import-wizard-step-duplicates',
    review: 'import-wizard-step4',
};

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

/** A copy of a sample report a test uploaded: it is the test's to select, and to delete. */
export interface OwnedReport {
    brokerId: number;
    fileId: string;
    /** The unique name it was uploaded under. */
    fileName: string;
}

/**
 * The parse response (`POST /brokers/import/files/{file_id}/parse`, `BRIMParseResponse`), reduced
 * to what the corridor and its callers read. `warnings` are the parse's notices, info or warning:
 * either level makes the wizard ask for a confirmation when the analysis is left.
 */
export interface ParseResponse {
    file_id: string;
    plugin_code: string;
    broker_id: number;
    transactions: unknown[];
    warnings?: Array<{severity?: string; code?: string}>;
    field_todos?: unknown[];
}

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type UploadedInfo = {file_id: string; filename: string; target_broker_id: number | null};

/** A file in a broker's step-2 panel: by its id when the test knows it, else by its name. */
type PanelFile = {brokerId: number; fileId: string} | {brokerId: number; fileName: string; fileId?: undefined};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Owned files
// ---------------------------------------------------------------------------

/** A broker's id from its name — backend data, not a translation. Exactly one broker must carry it. */
async function brokerIdByName(page: Page, name: string): Promise<number> {
    const body = await jsonFrom<{items: Array<{id: number; name: string}>}>(await page.request.get(BROKERS_PATH), 'list the brokers');
    const matches = body.items.filter((broker) => broker.name === name);
    if (matches.length !== 1) {
        throw new Error(`Expected exactly one broker named "${name}" visible to this user, found ${matches.length}: it is seeded by backend/test_scripts/test_db/populate_mock_data.py (populate_brokers)`);
    }
    return matches[0].id;
}

/**
 * Upload a copy of a sample report to the broker named `brokerName`, under a unique name.
 *
 * `sample` is the file name of a CSV in `backend/app/services/brim_providers/sample_reports`.
 * The copy is pushed onto `owned` as soon as the server has accepted it — before anything about
 * it is checked — so a failed check still leaves it to {@link deleteOwnedReports}. The wizard
 * reads the broker files when it enters step 2: upload before that.
 */
export async function uploadOwnedReport(page: Page, owned: OwnedReport[], report: {brokerName: string; sample: string}): Promise<OwnedReport> {
    const brokerId = await brokerIdByName(page, report.brokerName);
    const extension = path.extname(report.sample);
    const fileName = `${path.basename(report.sample, extension)}-${uniqueSuffix()}${extension}`;
    const response = await page.request.post(UPLOAD_PATH, {
        multipart: {broker_id: String(brokerId), file: {name: fileName, mimeType: 'text/csv', buffer: readFileSync(path.join(SAMPLE_DIR, report.sample))}},
    });
    const uploaded = await jsonFrom<UploadedInfo>(response, `upload ${fileName} to "${report.brokerName}"`);
    const copy: OwnedReport = {brokerId, fileId: uploaded.file_id, fileName};
    owned.push(copy);
    expect(uploaded, `the copy of ${report.sample} lands on "${report.brokerName}" under its own name`).toMatchObject({filename: fileName, target_broker_id: brokerId});
    return copy;
}

/**
 * Delete every report in `owned` through the API, and empty the list. Asserts each delete: a file
 * left behind piles up on its broker and pushes other tests' rows to later pages — or, once the
 * broker is gone, is inherited by the next broker that reuses its id (plan 33, §1.1–1.2).
 * Scoped to what the test uploaded — never "whatever appeared since".
 */
export async function deleteOwnedReports(page: Page, owned: OwnedReport[]): Promise<void> {
    const failures: string[] = [];
    for (const report of owned.splice(0)) {
        try {
            const result = await jsonFrom<{success?: boolean; file_id?: string}>(await page.request.delete(`${FILES_PATH}/${report.fileId}`), `delete ${report.fileName}`);
            if (result.success !== true || result.file_id !== report.fileId) failures.push(`${report.fileName} (${report.fileId}): ${JSON.stringify(result)}`);
        } catch (error) {
            failures.push(`${report.fileName} (${report.fileId}): ${String(error)}`);
        }
    }
    expect(failures, 'cleanup deletes every report this test uploaded').toEqual([]);
}

// ---------------------------------------------------------------------------
// Step 2 → 3
// ---------------------------------------------------------------------------

/**
 * Select one file in step 2, without assuming where it is.
 *
 * Waits for step 2 to settle, opens the broker's panel (`import-wizard-broker-files-<brokerId>`)
 * if it is folded, then walks the panel's table page by page until the file is on screen: by
 * its checkbox (`dt-row-checkbox-<fileId>`) when the file id is known, else by the first row
 * whose name cell is exactly `fileName`. Ticks it, unless it is ticked already, and asserts it
 * ticked. Fails naming the number of pages searched; returns the selected file's id.
 */
export async function selectBrokerFile(page: Page, file: PanelFile): Promise<string> {
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2, 'the wizard is on the file selection').toBeVisible({timeout: STEP_TIMEOUT});
    // The step renders before its broker files have loaded, and says so through data-busy.
    await waitForSettled(step2, STEP_TIMEOUT);

    const {brokerId} = file;
    const panel = step2.getByTestId(`import-wizard-broker-files-${brokerId}`);
    await expect(panel, `broker ${brokerId} has files listed in step 2`).toBeVisible({timeout: UI_TIMEOUT});
    const toggle = panel.getByTestId(`import-wizard-broker-toggle-${brokerId}`);
    await expect(toggle).toBeVisible({timeout: UI_TIMEOUT});
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle, `broker ${brokerId}'s panel is open`).toHaveAttribute('aria-expanded', 'true', {timeout: UI_TIMEOUT});
    // A barrier, not a choice: the table has drawn its first page.
    await expect(panel.locator('tbody tr[data-row-id]').first(), `broker ${brokerId}'s panel shows its files`).toBeVisible({timeout: UI_TIMEOUT});

    const what = file.fileId !== undefined ? `file ${file.fileId}` : `"${file.fileName}"`;
    const target =
        file.fileId !== undefined
            ? panel.getByTestId(`dt-row-checkbox-${file.fileId}`)
            : panel
                  .locator('tbody tr[data-row-id]')
                  .filter({has: page.getByText(file.fileName, {exact: true})})
                  .first();
    let pagesSearched = 0;
    const foundOn = await findAcrossPages(
        panel,
        async () => {
            pagesSearched += 1;
            return (await target.count()) > 0;
        },
        {maxPages: MAX_FILE_PAGES},
    );
    if (foundOn === null) {
        throw new Error(`${what} not found in ${pagesSearched} page(s) of broker ${brokerId}'s files in step 2${pagesSearched >= MAX_FILE_PAGES ? ` (the walk stops at ${MAX_FILE_PAGES})` : ''}`);
    }
    test.info().annotations.push({type: 'import wizard: file selected', description: `${what} on page ${foundOn} of broker ${brokerId}'s files`});

    const fileId = file.fileId ?? (await target.getAttribute('data-row-id'));
    if (!fileId) throw new Error(`The row of ${what} carries no data-row-id`);
    const checkbox = panel.getByTestId(`dt-row-checkbox-${fileId}`);
    if ((await checkbox.getAttribute('data-state')) !== 'checked') await checkbox.click();
    await expect(checkbox, `${what} is selected`).toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
    return fileId;
}

/**
 * Click Parse with `fileId` selected — the selection being that one file — and return its parse
 * response, captured as the request goes out. Waits for the analysis verdict, which throws with
 * the wizard's own reason when the parse produced nothing usable.
 *
 * For the first analysis of a selection only: the wizard reuses its results, and sends no
 * request, when the analysis is re-entered with the same files and plugins (`usingCachedResults`).
 */
export async function parseSelectedFile(page: Page, fileId: string): Promise<ParseResponse> {
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse, 'Parse is offered for the selection').toBeEnabled({timeout: UI_TIMEOUT});
    const parsePath = `${FILES_PATH}/${fileId}/parse`;
    const [response] = await Promise.all([page.waitForResponse((candidate) => candidate.request().method() === 'POST' && new URL(candidate.url()).pathname === parsePath, {timeout: STEP_TIMEOUT}), parse.click()]);
    const parsed = await jsonFrom<ParseResponse>(response, `parse file ${fileId}`);
    await expect(page.getByTestId('import-wizard-step3'), 'the wizard is on the analysis').toBeVisible({timeout: UI_TIMEOUT});
    await waitForParseVerdict(page);
    return parsed;
}

// ---------------------------------------------------------------------------
// Step 3 → later steps
// ---------------------------------------------------------------------------

/** The corrections step: every flagged row kept as read — the plugin's own reading, the one decision that is always available. */
async function keepAllCorrections(page: Page): Promise<void> {
    const step = page.getByTestId(STEP_CONTAINER.fix);
    await expect(step, 'the corrections step is on screen').toBeVisible({timeout: UI_TIMEOUT});
    await step.getByTestId('fix-step-accept-all').click();
    await expect(step.locator('[data-testid="fix-step-row"][data-decision="pending"]'), 'every flagged row is kept as read').toHaveCount(0, {timeout: UI_TIMEOUT});
}

/**
 * From the analysis to the `target` step, crossing whichever conditional steps the wizard lands
 * on first, and return the target's container: `import-wizard-step4` for the review (settled:
 * its `data-busy` is false), `import-wizard-step-<id>` otherwise (on screen, untouched).
 *
 * - Clicks Continue on the analysis. When `parsed` — the parse response(s) of the files analysed
 *   — carries notices, the wizard asks for a confirmation first: it is expected, confirmed and
 *   gone before the walk goes on. Without notices it is never looked for.
 * - Then follows the stepper. On the corrections step every flagged row is kept as read; on any
 *   step crossed, `import-wizard-<step>-continue` must be enabled, is clicked, and the marker must
 *   move. Unification proposals still open hold the assets step: the walk then fails there, by
 *   name, rather than deciding them for the test.
 * - A wizard that goes past `target` without stopping on it fails, saying where it went.
 *
 * The steps crossed are annotated on the test, also when the walk fails.
 */
export async function continueToStep(page: Page, parsed: ParseResponse | ParseResponse[], target: LaterStep): Promise<Locator> {
    const notices = (Array.isArray(parsed) ? parsed : [parsed]).flatMap((response) => response.warnings ?? []);
    const marker = page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
    await expect(marker, 'the walk starts on the analysis').toHaveAttribute('data-step-id', 'analyze', {timeout: UI_TIMEOUT});

    const leave = page.getByTestId('import-wizard-continue');
    await expect(leave, 'the analysis lets the import go on').toBeEnabled({timeout: UI_TIMEOUT});
    await leave.click();
    if (notices.length > 0) {
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm, `the parse raised ${notices.length} notice(s): leaving the analysis asks to confirm them`).toBeVisible({timeout: UI_TIMEOUT});
        await confirm.click();
        await expect(confirm, 'the notices are confirmed').toBeHidden({timeout: UI_TIMEOUT});
    }

    const crossed: LaterStep[] = [];
    try {
        for (let hop = 0; hop < LATER_STEPS.length; hop++) {
            await expect(marker, crossed.length === 0 ? 'the wizard leaves the analysis for a step after it' : `the wizard goes on from ${crossed[crossed.length - 1]}`).toHaveAttribute('data-step-id', LATER_STEP, {timeout: STEP_TIMEOUT});
            const stepId = (await marker.getAttribute('data-step-id')) as LaterStep;
            if (stepId === target) break;
            if (LATER_STEPS.indexOf(stepId) > LATER_STEPS.indexOf(target)) {
                throw new Error(`The wizard went on to "${stepId}" without stopping on "${target}" (steps crossed: ${crossed.join(' → ') || 'none'})`);
            }
            crossed.push(stepId);
            if (stepId === 'fix') await keepAllCorrections(page);
            const advance = page.getByTestId(`import-wizard-${stepId}-continue`);
            await expect(advance, `the ${stepId} step lets the import go on${stepId === 'assets' ? ' (open unification proposals hold it)' : ''}`).toBeEnabled({timeout: UI_TIMEOUT});
            await advance.click();
            await expect(marker, `the wizard leaves the ${stepId} step`).not.toHaveAttribute('data-step-id', stepId, {timeout: STEP_TIMEOUT});
        }
        await expect(marker, `the wizard stops on the ${target} step`).toHaveAttribute('data-step-id', target, {timeout: STEP_TIMEOUT});
    } finally {
        test.info().annotations.push({type: `import wizard: steps crossed before ${target}`, description: crossed.join(' → ') || 'none'});
    }

    const container = page.getByTestId(STEP_CONTAINER[target]);
    await expect(container, `the ${target} step is on screen`).toBeVisible({timeout: UI_TIMEOUT});
    // Only the review publishes data-busy: waiting on it anywhere else would burn the whole timeout.
    if (target === 'review') await waitForSettled(container, STEP_TIMEOUT);
    return container;
}

/** {@link continueToStep} to the review: returns `import-wizard-step4`, settled. */
export async function continueToReview(page: Page, parsed: ParseResponse | ParseResponse[]): Promise<Locator> {
    return continueToStep(page, parsed, 'review');
}
