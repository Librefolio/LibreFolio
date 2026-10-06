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
 *
 * Phase F2 — the graphics (plan F2.0, U1–U4), written red first:
 *
 *   U1 the card lists its files in one table per role (`report-set-role-table`, rows
 *      `tr[data-row-id=<file_id>]`; `report-set-member` is gone): R1–R4 read the members there. Above
 *      the single files of a broker that also has a set, the heading `import-wizard-other-files-<id>`
 *      (R4); never on a broker with only a set (R1) or only single files (R7).
 *   U2 F2-U2: with history already in LibreFolio — two transactions tagged `danske_bank`, seeded over
 *      the API before the upload — the timeline draws it from H0 to its newest transaction, with its
 *      count, and the legend names it. It stops at step 2; the transactions go with the broker.
 *   U3 R1: the pairing of the set's detail shows the five outcome chips, and its preview button opens
 *      the combined file in the file preview.
 *   U4 R5/R6: the gap-fix step has one summary card per truth point and one table of corrections; the
 *      opening card filters the table and opens its comparison, a second click clears it. R6 unticks
 *      the deposit through its row toggle (onToggle), then the rest with deselect all (onSetSelected).
 *
 * Each F2 scenario gives its first new element a short budget (`F2_FIRST`).
 *
 * Phase G — the user chooses how a set is read (plan §14 G.2), written red first:
 *
 *   A   the card's `report-set-read-as` select: the set's plugin, or "one by one" — our own select since step H (R1).
 *   B   a member's row menu: `read-alone-<plugin>` (a single file read by that plugin) and
 *       `remove-from-set` (a single file with no plugin — unselected in G, with its tick kept since R5, below).
 *       Back into the set: the set's plugin, chosen in the plugin select of the single file.
 *   C1  `report-set-default-note[data-default-plugin]` on a broker whose default plugin is another one.
 *   D   every POST /sets/preview and /sets/combine names the files left out: `exclude_file_ids`
 *       (empty when nothing is); recorded as the browser sends them (`recordSetRequests`).
 *   Memory: nothing is remembered before an analysis; after it, the wizard opens on what was analysed
 *       (the set with its members, `data-analysed="true"`; a file read alone, alone with its plugin;
 *       a file left out of the analysed set, out and unselected). The wizard is closed (discarding) and
 *       opened again as a user does it, from the editor it lives in (`tx-bulk-import`): closing it leaves
 *       that editor open, empty, over the toolbar. `reopenOnStep2` checks what the scenarios rest on —
 *       step 2 reads the files again and selects nothing.
 *
 *   G-A (H-E1 since step H), G-B, G-C, G-memory (set), G-memory (alone), G-no-memory, G-real; R1's combine body now carries
 *   `exclude_file_ids: []` (a soft assertion: the rest of R1 still runs, and says what still works).
 *
 * Decision 1 (the developer, step G): the generic CSV declares only the CSVs whose header names a
 * `date` and a `type` column, in any of its languages. The bank's cash statement names neither, so only
 * Danske reads `danske_bank-cash.csv`: its row menu offers to remove it from the set and never to read
 * it alone (G-real, on the samples themselves). Every scenario that needs a statement the generic CSV
 * reads too — A18, G-A (H-E1), G-B, G-C, G-memory (alone), G-no-memory, and the dual H-E2, H-E5, H-E6, the dual R5-E1 — uploads the dual statement
 * (`writeDualCash`): the sample's rows plus four columns the generic CSV maps (`date`, `type`, `amount`,
 * `currency`) after the bank's, which Danske ignores. Its premise is read from its upload, never
 * assumed (`dualCashUpload`): both plugins are among its `compatible_plugins`.
 *
 * A18 — a statement the generic CSV reads too joins the Danske set on a broker whose default is the
 * generic CSV, and the analysis reads it through the combined file — used to be a premise of R1 on the
 * sample; it is its own scenario now, on the dual statement. R1 runs on the samples, with no default.
 *
 * Decision 2 (rule A2): a failed original never joins a set — the server's `collect_members` skips it,
 * and the wizard mirrors it (importReportSets.test.ts). A file "analysed alone" is one the analysis
 * really parsed: G-memory (alone) reads the dual statement, which the generic CSV parses.
 *
 * Two files are written by the tests themselves, in their output folder, from the synthetic cash
 * sample (Latin-1, `;`): the dual statement, and a third statement with invented rows of 2021 in the
 * bank's format only, which only Danske reads, like the sample (G-memory (set)).
 *
 * Each G scenario gives its first G element a short budget (`G_FIRST`).
 *
 * Step H — the developer's first review of G (plan §17.5), written red first. The developer redefined R4 after the first
 * red round (§17.5, «Fuori pista — R4 ridefinito»), and the R4 scenarios follow the new contract:
 *
 *   R1  «Read as» is our own select (SimpleSelect, testId `report-set-read-as`), never the system's: its trigger
 *       `report-set-read-as-button` opens `report-set-read-as-dropdown`, whose options are
 *       `report-set-read-as-option-<plugin>` (the set's own `aria-selected="true"`) and
 *       `report-set-read-as-option-one-by-one`. No native `select` in the card's header — a folded card is its
 *       header. G-A drives it (H-E1); every scenario choosing how a set is read goes through `chooseReadAs`.
 *   R2  "one by one" changes how the files are read, never whether they are: every member stays ticked, each with
 *       its best single-file plugin or none. A file no single-file plugin reads — the custody export, and the cash
 *       statement as the bank exports it — stays ticked with an empty plugin select that still offers Danske, so Parse
 *       waits for a plugin; Danske chosen again on each file, in the plugin column, re-forms the set, ticked. H-E1 on the
 *       dual statement; H-E2 twice, through the re-formed set: on the bank's own exports (neither file has a plugin) and
 *       on the dual statement (the statement has the generic CSV, the custody export none).
 *   R4  (redefined) an unticked single file keeps «—» in its Plugin column, as before H: no select there. To choose its
 *       plugin the user ticks it first, and then its select appears. A plugin choice never changes the tick: "read it
 *       alone with…" leaves the file ticked or unticked as it was, only its plugin changes; "remove from the set" unticked
 *       it until R5 (below), which keeps its tick too. H-E5: read alone with the generic CSV from a set that is not
 *       ticked, the statement stays unticked with «—»; ticked, its select holds the generic CSV — the choice was kept. It
 *       does not go through «Read as», and guards today's behaviour. `expectUnselectedSingle` is G's expectation again — no
 *       select on an unticked file — with its «—» named (`pluginCellText`), and the memory scenarios are G's again. H-E3,
 *       the way back from "remove from the set", follows R5 now.
 *   The latent defect (H-E6): the table of the single files took the selection only when it was mounted, so a file
 *       read alone into a table already on screen was selected in the wizard with its checkbox clear, and the next
 *       click on another checkbox deselected it in silence. The checkbox always says the selection, and toggling
 *       another row never takes a file away — proven by the analysis that follows, from its parse requests.
 *   R3  each timeline row's label (`report-set-timeline-label`, `data-role` = the role code, `history` for
 *       LibreFolio's) holds its whole name on desktop: it has a width, and `scrollWidth ≤ clientWidth` (H-E7).
 *
 * Each H scenario gives its first H element a short budget (`H_FIRST`).
 *
 * R5 — the developer's second review of G (plan §19.9 and §20), written red first. «Remove from the set» does not
 * mean "do not import this file", only "not with this plugin": the file leaves its set with no plugin (override `''`)
 * and its tick does not change. Ticked before, it stays ticked: its Plugin column holds the plugin select with nothing
 * chosen, offering the plugins that read the file — the set's own among them — and Parse waits for a choice (behind the
 * set-blocks hint while a ticked set is not complete, on the missing plugin alone otherwise). Unticked before, it stays
 * unticked with «—». Choosing the set's plugin there puts it back in the set. With R5 no command of the card changes a
 * tick: «Read as» / one by one, "read it alone with…", "remove from the set".
 *
 *   R5-E1 the set ticked (`removeKeepsTheTick`): the statement removed stays ticked, its select empty and offering exactly
 *         the plugins that read it. Parse waits — first behind the set-blocks hint, the custody export alone being an
 *         incomplete set, still ticked; then, the custody export excluded, on the statement's missing plugin alone: no
 *         set-blocks hint, the statement still ticked, Parse still disabled. The custody export ticked again and Danske
 *         chosen in the statement's select: the set complete, ticked whole, Parse enabled. Twice, as H-E2: on the bank's
 *         own exports (the statement's select offers Danske alone), and on the dual statement, where the generic CSV reads
 *         the statement too — "no plugin" is then a choice, not the only option: removing is not reading it alone, and the
 *         select offers both.
 *   R5-E2 (guard, green before R5 too) the samples, the set unticked first: the statement removed stays unticked — «—»,
 *         no select — and the set left keeps its tick, none.
 *   H-E3  the way back, straight from the removal: ticked with an empty select, Parse waiting; Danske chosen there, the
 *         set with both members, ticked whole, Parse enabled.
 *   G-memory (set) the third statement removed from a ticked set stays ticked with no plugin, so Parse waits on it alone
 *         (the set left is complete); the user unticks it — «—» — to analyse the set without it, as before.
 *
 * The plugin-required hint (`importWizard.pluginRequired`) has no testid: where a scenario needs that state alone, it is
 * read by elimination — Parse disabled, no `import-wizard-set-blocks`, and a ticked file whose select holds no plugin.
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
const FILES_PATH = `${API}/brokers/import/files`;
const PREVIEW_PATH = `${API}/brokers/import/sets/preview`;
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

/**
 * The two members of the main set (backend phase B, test_brim_danske_bank.py, MEMBER_FACTS): the
 * custody export covers its trade dates, the cash statement its value dates.
 */
const MAIN_MEMBERS = {
    custody: {rows: 15, start: '2020-02-03', end: '2020-06-26'},
    cash: {rows: 32, start: '2019-01-07', end: '2020-07-03'},
} as const;

/** The tag of LibreFolio's Danske Bank history: `BRIMProvider.history_tag`, the plugin code without `broker_`. */
const DANSKE_HISTORY_TAG = 'danske_bank';

/** Budget of the first F2 element of a scenario: before the implementation it is the one that fails. */
const F2_FIRST = 8_000;

/** Budget of the first G element of a scenario: before the implementation it is the one that fails. */
const G_FIRST = 8_000;

/** Budget of the first H element of a scenario: before the implementation it is the one that fails. */
const H_FIRST = 8_000;

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

type UploadedInfo = {file_id: string; filename: string; uploaded_at: string; target_broker_id: number | null; batch_id?: string | null; compatible_plugins?: string[] | null};

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

/**
 * Give the owned broker the Danske Bank history an earlier import leaves: one DEPOSIT per date, with
 * the plugin's history tag as an exact tag. Committed over the API, before the set is uploaded; the
 * broker's forced delete in afterEach takes the rows with it. Read back, so the premise is checked.
 */
async function seedDanskeHistory(page: Page, brokerId: number, dates: readonly string[]): Promise<void> {
    const marker = uniqueSuffix();
    const response = await page.request.post(`${API}/transactions/commit`, {
        data: {creates: dates.map((date) => ({broker_id: brokerId, type: 'DEPOSIT', date, cash: {code: 'EUR', amount: '100'}, tags: ['import', DANSKE_HISTORY_TAG], description: `F2-U2 history ${date} ${marker}`}))},
    });
    const body = await response.text();
    expect(response.ok(), `seed the history: HTTP ${response.status()} ${body}`).toBe(true);
    const committed = JSON.parse(body) as {committed: boolean; issues?: unknown; results: Array<{operation: string; ids: number[]}>};
    expect(committed.committed, `the history rows were rolled back: ${JSON.stringify(committed.issues ?? [])}`).toBe(true);
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
    expect(ids, 'one transaction per date').toHaveLength(dates.length);

    const readback = await page.request.get(`${API}/transactions`, {params: {broker_id: brokerId}});
    expect(readback.ok(), `read the history back: HTTP ${readback.status()}`).toBe(true);
    const rows = ((await readback.json()) as Array<{id: number; date: string; tags?: string[] | null}>).filter((row) => ids.includes(row.id));
    expect(rows.map((row) => `${row.date} ${(row.tags ?? []).includes(DANSKE_HISTORY_TAG)}`).sort(), 'the seeded rows carry the history tag, on their dates').toEqual(dates.map((date) => `${date} true`).sort());
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

/** The wizard is open, on step 1, settled. */
async function wizardOnStep1(page: Page) {
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await step1.waitFor({state: 'visible', timeout: 5_000});
    await waitForSettled(step1, 15_000);
}

/** Open the wizard via the toolbar Import button; wait until step 1 has settled. */
async function openImportWizard(page: Page) {
    await page.getByTestId('tx-import-button').click();
    await wizardOnStep1(page);
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

/** The table of one role in a card (F2 · U1). */
function roleTable(card: Locator, role: string): Locator {
    return card.locator(`[data-testid="report-set-role-table"][data-role="${role}"]`);
}

/** The row of one file in the table of its role (F2 · U1). */
function roleRow(card: Locator, role: string, fileId: string): Locator {
    return roleTable(card, role).locator(`tbody tr[data-row-id="${fileId}"]`);
}

/** The heading above the single files of a broker that also has a set (F2 · U1). */
function otherFilesHeading(page: Page, brokerId: number): Locator {
    return page.getByTestId(`import-wizard-other-files-${brokerId}`);
}

/** The selectable rows of a broker panel: the single files (the role tables of a set have no selection). */
function singleFileRows(page: Page, brokerId: number): Locator {
    return page.getByTestId(`import-wizard-broker-files-${brokerId}`).locator('[data-testid^="dt-row-checkbox-"]');
}

/**
 * Make sure the card body is open. Whether a card starts open is the product's call, so the
 * spec asks before toggling (rule 14) — and only once the card has settled on a terminal status.
 */
async function expandCard(card: Locator) {
    await expect(card).toHaveAttribute('data-set-status', /^(complete|incomplete|error)$/, {timeout: 15_000});
    const toggle = card.getByTestId('report-set-toggle');
    if ((await toggle.getAttribute('aria-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
}

/**
 * Open the card and wait for its files — the final ones, since the card has settled. Every set
 * here has at least one recognised export, so its role tables have at least one row (F2 · U1).
 */
async function openCard(card: Locator) {
    await expandCard(card);
    await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]').first(), 'the open card lists its files in one table per role').toBeVisible({timeout: F2_FIRST});
}

/** Fold a card to its header once it has settled: whether it is open is asked, not assumed (rule 14). */
async function foldCard(card: Locator) {
    await expect(card).toHaveAttribute('data-set-status', /^(complete|incomplete|error)$/, {timeout: 15_000});
    const toggle = card.getByTestId('report-set-toggle');
    if ((await toggle.getAttribute('aria-expanded')) === 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
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

/**
 * The opening truth point and its deposit, selected by default; the verification has its card.
 *
 * F2 · U4: every truth point is a summary card. The opening card is clicked to make it the active
 * point — its comparison opens (`gapfix-point-details`) and the table keeps its corrections, the
 * deposit among them, pressed — then clicked again, which clears the filter. Whether a card starts
 * active is asked, not assumed (rule 14); the step is left with nothing active.
 */
async function expectOpeningDeposit(step: Locator) {
    const opening = step.locator(`[data-testid="gapfix-summary"][data-kind="${MAIN_TRUTH.checkpoint.kind}"][data-as-of="${MAIN_TRUTH.checkpoint.asOf}"]`);
    await expect(opening, 'the opening truth point has its summary card').toHaveCount(1, {timeout: F2_FIRST});
    await expect(step.locator(`[data-testid="gapfix-summary"][data-kind="verification"][data-as-of="${MAIN_TRUTH.verification}"]`), 'the verification has its summary card').toHaveCount(1);
    const pointKey = await opening.getAttribute('data-key');
    expect(pointKey, 'the opening card names its truth point').toBeTruthy();
    const details = step.getByTestId('gapfix-point-details');

    if ((await opening.getAttribute('aria-pressed')) === 'true') await opening.click();
    await expect(opening).toHaveAttribute('aria-pressed', 'false');
    await expect(details).toHaveCount(0);

    // One click: the opening point is active, its comparison open, the table on its corrections.
    await opening.click();
    await expect(opening).toHaveAttribute('aria-pressed', 'true');
    const openingDetails = step.locator(`[data-testid="gapfix-point-details"][data-key="${pointKey}"]`);
    await expect(openingDetails, 'the active card opens its comparison').toBeVisible({timeout: 5_000});
    await expect(details).toHaveCount(1);
    await expect(openingDetails.locator(`[data-testid="gapfix-checkpoint"][data-as-of="${MAIN_TRUTH.checkpoint.asOf}"][data-kind="${MAIN_TRUTH.checkpoint.kind}"]`)).toHaveCount(1);
    const deposit = step.locator('[data-testid="gapfix-table"] [data-testid="gapfix-proposal-toggle"][data-type="DEPOSIT"]');
    await expect(deposit, 'the opening deposit is a row of the corrections').toHaveCount(1, {timeout: 5_000});
    await expect(deposit).toHaveAttribute('aria-pressed', 'true');
    await expect(deposit).toHaveAttribute('data-date', MAIN_TRUTH.checkpoint.asOf);
    await expect(deposit).toHaveAttribute('data-point', pointKey ?? '');

    // A second click clears it: no comparison, nothing filtered.
    await opening.click();
    await expect(opening).toHaveAttribute('aria-pressed', 'false');
    await expect(details).toHaveCount(0);
    await expect(deposit).toHaveAttribute('aria-pressed', 'true');
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
// G: how a set is read
// ---------------------------------------------------------------------------

type SetRequestBody = {broker_id: number; plugin_code: string; batch_id: string; exclude_file_ids?: unknown};
type SetRequestCall = {endpoint: 'preview' | 'combine'; body: SetRequestBody};

/**
 * Every POST /sets/preview and /sets/combine of this page from now on, as the browser sends it: the
 * request body is the subject (D), whatever the answer. Read live, so a test can wait for the next
 * one; armed before the action, like every recorder here.
 */
function recordSetRequests(page: Page): {calls: SetRequestCall[]; stop: () => void} {
    const calls: SetRequestCall[] = [];
    const listener = (request: Request) => {
        if (request.method() !== 'POST') return;
        const pathname = new URL(request.url()).pathname;
        const endpoint = pathname === PREVIEW_PATH ? 'preview' : pathname === COMBINE_PATH ? 'combine' : null;
        if (endpoint !== null) calls.push({endpoint, body: request.postDataJSON() as SetRequestBody});
    };
    page.on('request', listener);
    return {calls, stop: () => page.off('request', listener)};
}

/** The bodies one set sent to one endpoint, in the order they were sent (the wizard previews every set it shows). */
function setBodies(calls: SetRequestCall[], endpoint: 'preview' | 'combine', brokerId: number, batchId: string): SetRequestBody[] {
    return calls.filter((call) => call.endpoint === endpoint && call.body.broker_id === brokerId && call.body.batch_id === batchId && call.body.plugin_code === DANSKE).map((call) => call.body);
}

function lastOf<T>(items: T[]): T | undefined {
    return items.length > 0 ? items[items.length - 1] : undefined;
}

/** The files a request leaves out, sorted (their order is not pinned); `undefined` when the body does not say. */
function excludedOf(body: SetRequestBody | undefined): string[] | undefined {
    const excluded = body?.exclude_file_ids;
    return Array.isArray(excluded) ? [...(excluded as string[])].sort() : undefined;
}

/** The names of the two plugins, from the endpoint the plugin select renders: backend product names, not translations. */
async function pluginNames(page: Page): Promise<{danske: string; generic: string}> {
    const response = await page.request.get(`${API}/brokers/import/plugins`);
    expect(response.ok(), `GET ${API}/brokers/import/plugins: HTTP ${response.status()}`).toBe(true);
    const byCode = new Map(((await response.json()) as Array<{code: string; name: string}>).map((plugin) => [plugin.code, plugin.name]));
    const danske = byCode.get(DANSKE);
    const generic = byCode.get(GENERIC);
    if (!danske || !generic) throw new Error(`The backend serves no ${DANSKE} or no ${GENERIC} plugin: ${JSON.stringify([...byCode.keys()])}`);
    return {danske, generic};
}

/** The row of a single file in its broker's table: the role tables of a card have no selection, so the checkbox tells them apart. */
function singleRow(page: Page, brokerId: number, fileId: string): Locator {
    return page
        .getByTestId(`import-wizard-broker-files-${brokerId}`)
        .locator(`tr[data-row-id="${fileId}"]`)
        .filter({has: page.getByTestId(`dt-row-checkbox-${fileId}`)});
}

/** A single file, selected and read by `pluginName`: its checkbox ticked, its plugin select naming that plugin (and not `otherName`). */
async function expectSelectedSingle(page: Page, brokerId: number, fileId: string, pluginName: string, otherName: string) {
    const row = singleRow(page, brokerId, fileId);
    await expect(row, `${fileId} is a single file of its broker`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId(`dt-row-checkbox-${fileId}`), `${fileId} is selected`).toHaveAttribute('data-state', 'checked');
    const plugin = row.getByTestId('import-plugin-select').getByRole('combobox');
    await expect(plugin, `${fileId} is read by ${pluginName}`).toContainText(pluginName, {timeout: 5_000});
    await expect(plugin).not.toContainText(otherName);
}

/** The product names of the two plugins, as `pluginNames` reads them. */
type PluginNames = {danske: string; generic: string};

/**
 * What the plugin select of a ticked single file shows (R4: only a ticked file has one): `pluginName` and not the other
 * plugin's name — or, with `pluginName` null, no plugin at all: neither name. Product names from the plugins endpoint, not
 * translations. The select lists only the plugins that read its file, and every file read here is read by Danske, by the
 * generic CSV, or by both: showing neither name is showing none.
 */
async function expectPluginShown(select: Locator, pluginName: string | null, names: PluginNames) {
    await expect(select, 'the single file has its plugin select').toBeVisible({timeout: H_FIRST});
    const combobox = select.getByRole('combobox');
    if (pluginName === null) {
        await expect(combobox, 'no plugin is chosen for it').not.toContainText(names.danske);
        await expect(combobox, 'no plugin is chosen for it').not.toContainText(names.generic);
        return;
    }
    await expect(combobox, `it is read by ${pluginName}`).toContainText(pluginName, {timeout: 5_000});
    await expect(combobox).not.toContainText(pluginName === names.danske ? names.generic : names.danske);
}

/**
 * The text of a single file's Plugin cell: the cell under its table's `dt-header-plugin`, found by that header's place in
 * the header row — the user can reorder the columns, so no index is assumed. Null when the table has no Plugin column.
 */
function pluginCellText(row: Locator): Promise<string | null> {
    return row.evaluate((tr) => {
        const headers = Array.from(tr.closest('table')?.querySelectorAll(':scope > thead > tr > th') ?? []);
        const index = headers.findIndex((th) => th.getAttribute('data-testid') === 'dt-header-plugin');
        return index < 0 ? null : (tr.children[index]?.textContent ?? '').trim();
    });
}

/**
 * A single file, not selected: its checkbox clear, and no plugin select — its Plugin column holds «—» (R4: a file is ticked
 * before its plugin is chosen). The «—» is the column's own mark for a file the wizard does not hold, not a translation,
 * and it is the positive half of the absence: the cell is there, and says so.
 */
async function expectUnselectedSingle(page: Page, brokerId: number, fileId: string) {
    const row = singleRow(page, brokerId, fileId);
    await expect(row, `${fileId} is a single file of its broker`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId(`dt-row-checkbox-${fileId}`), `${fileId} is not selected`).toHaveAttribute('data-state', 'unchecked');
    await expect.poll(() => pluginCellText(row), {message: `${fileId}: its Plugin column holds «—»`, timeout: 5_000}).toBe('—');
    await expect(row.getByTestId('import-plugin-select')).toHaveCount(0);
}

/** R2 and R5: a single file selected with no plugin chosen — its checkbox ticked, its plugin select showing none. */
async function expectSelectedSingleWithoutPlugin(page: Page, brokerId: number, fileId: string, names: PluginNames) {
    const row = singleRow(page, brokerId, fileId);
    await expect(row, `${fileId} is a single file of its broker`).toHaveCount(1, {timeout: 10_000});
    await expect(row.getByTestId(`dt-row-checkbox-${fileId}`), `${fileId} is selected`).toHaveAttribute('data-state', 'checked');
    await expectPluginShown(row.getByTestId('import-plugin-select'), null, names);
}

/**
 * Choose a plugin in the plugin select of a ticked single file (R4: an unticked one has none), as a user does in the plugin
 * column: one SearchSelect open at a time, since every one of them names its options `search-select-option-*` (rule 20).
 */
async function chooseSinglePlugin(page: Page, brokerId: number, fileId: string, code: string) {
    const select = singleRow(page, brokerId, fileId).getByTestId('import-plugin-select');
    await expect(select, `${fileId} has its plugin select`).toBeVisible({timeout: H_FIRST});
    await optionsClosed(page);
    await select.getByRole('combobox').click();
    const option = select.getByTestId(`search-select-option-${code}`);
    await expect(option, `${code} is offered for ${fileId}`).toBeVisible({timeout: 5_000});
    await option.click();
    await optionsClosed(page);
}

/**
 * R1: choose how a set is read through «Read as», our own select — its trigger opens the list, whose options are named by
 * plugin code, or `one-by-one`. The trigger is the first H element of its scenario.
 */
async function chooseReadAs(card: Locator, choice: string) {
    const trigger = card.getByTestId('report-set-read-as-button');
    await expect(trigger, '«Read as» is our own select: its trigger is on the card').toBeVisible({timeout: H_FIRST});
    await trigger.click();
    const dropdown = card.getByTestId('report-set-read-as-dropdown');
    await expect(dropdown, '«Read as» opens its list').toBeVisible({timeout: 5_000});
    await dropdown.getByTestId(`report-set-read-as-option-${choice}`).click();
    await expect(dropdown, 'a choice closes the list').toHaveCount(0, {timeout: 5_000});
}

/**
 * H-E2 (R2) on one upload of the custody export and a cash statement — a complete set, ticked: "one by one" chosen through
 * «Read as», then the set re-formed file by file in the plugin column. Both files stay ticked. The custody export, which no
 * single-file plugin reads, has no plugin; the statement has `statementAlone` — the generic CSV's name for the dual
 * statement, null (none) for the bank's own export. While a ticked file has no plugin, Parse waits. Danske, still offered
 * in each file's select (choosing it is the proof), put back on each file re-forms the set, ticked whole.
 */
async function readOneByOneThenBack(page: Page, brokerId: number, custody: UploadedInfo, cash: UploadedInfo, statementAlone: string | null, names: PluginNames) {
    const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
    // Premise, read from the upload: only Danske reads the custody export, so read alone it has no plugin.
    expect(custody.compatible_plugins, 'premise: no single-file plugin reads the custody export').toEqual([DANSKE]);
    const card = setCard(page, brokerId, batchId);
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card).toHaveAttribute('data-selected', 'all');
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse, 'premise: the complete set, ticked, can be analysed').toBeEnabled({timeout: 5_000});
    // The statement read alone: ticked, with its single-file plugin, or with none.
    const expectStatementAlone = () => (statementAlone === null ? expectSelectedSingleWithoutPlugin(page, brokerId, cash.file_id, names) : expectSelectedSingle(page, brokerId, cash.file_id, statementAlone, statementAlone === names.danske ? names.generic : names.danske));

    // One by one: only how the files are read changes — both stay ticked. On the dual statement its select names its plugin
    // first, so the names are on screen when the custody export's shows none; on the bank's own exports neither shows one,
    // and Parse waiting is what says that no plugin is held.
    await chooseReadAs(card, 'one-by-one');
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2.locator(`[data-testid="report-set-card"][data-batch-id="${batchId}"]`), 'no card holds this upload any more').toHaveCount(0, {timeout: 10_000});
    await expectStatementAlone();
    await expectSelectedSingleWithoutPlugin(page, brokerId, custody.file_id, names);
    await expect(parse, 'a ticked file with no plugin holds the analysis back').toBeDisabled();

    // Back to the set, file by file, in the plugin column: Danske on the custody export first — a set again, still ticked.
    await chooseSinglePlugin(page, brokerId, custody.file_id, DANSKE);
    await expect(card, 'Danske on the custody export brings the card back').toBeVisible({timeout: 15_000});
    await openCard(card);
    await expect(roleRow(card, 'custody', custody.file_id), 'the custody export is in the set again').toBeVisible();
    await expect(page.getByTestId(`dt-row-checkbox-${custody.file_id}`), 'and is no single file').toHaveCount(0);
    await expect(card, 'the custody export is still ticked').toHaveAttribute('data-selected', 'all');
    await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the statement is not in the set yet').toHaveCount(0);
    await expectStatementAlone();

    // Then on the statement: the set is whole again, and ticked whole.
    await chooseSinglePlugin(page, brokerId, cash.file_id, DANSKE);
    await expect(roleRow(card, 'cash', cash.file_id), 'the statement is back in the cash table of the card').toBeVisible({timeout: 15_000});
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card, 'the set is ticked whole').toHaveAttribute('data-selected', 'all');
    await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
    await expect(singleFileRows(page, brokerId), 'no file of the upload is a single file any more').toHaveCount(0);
    await expect(parse, 'the set, whole and ticked, can be analysed').toBeEnabled({timeout: 10_000});
}

/** B: one action of a member's row menu, in the table of its role. The action is the first G element of its scenario. */
async function runMemberAction(page: Page, card: Locator, role: string, fileId: string, actionId: string) {
    const row = roleRow(card, role, fileId);
    await expect(row, `${fileId} is in the ${role} table of the card`).toBeVisible();
    await row.getByTestId(`row-actions-${fileId}`).click();
    const menu = page.getByTestId('context-menu');
    await expect(menu).toBeVisible({timeout: 5_000});
    const action = menu.getByTestId(`context-menu-action-${actionId}`);
    await expect(action, `the row menu of ${fileId} offers ${actionId}`).toBeVisible({timeout: G_FIRST});
    await action.click();
    await expect(menu).toHaveCount(0, {timeout: 5_000});
}

/**
 * R5 on one upload of the custody export and a cash statement — a complete set, ticked: "remove from the set" on the
 * statement. It leaves the card and stays ticked with no plugin — not even one a single-file plugin could give it — and its
 * select offers exactly the plugins that read it, its `compatible_plugins`, the set's own among them. Parse waits: first
 * behind the set-blocks hint (the custody export alone is an incomplete set, still ticked), then — the custody export
 * excluded — on the statement's missing plugin alone: no set-blocks hint, the statement still ticked, Parse still disabled.
 * The custody export ticked again, Danske chosen in the statement's select puts it back: the set complete, ticked whole,
 * Parse enabled.
 */
async function removeKeepsTheTick(page: Page, brokerId: number, custody: UploadedInfo, cash: UploadedInfo, names: PluginNames) {
    const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
    expect(cash.compatible_plugins ?? [], 'premise: Danske reads the statement, so its select can bring it back').toContain(DANSKE);
    const card = setCard(page, brokerId, batchId);
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card, 'premise: the set is ticked whole').toHaveAttribute('data-selected', 'all');
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse, 'premise: the complete set, ticked, can be analysed').toBeEnabled({timeout: 5_000});
    await openCard(card);

    // Removed from the set: out of the card, a single file — still ticked, with no plugin chosen.
    await runMemberAction(page, card, 'cash', cash.file_id, 'remove-from-set');
    await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0, {timeout: 15_000});
    await expectSelectedSingleWithoutPlugin(page, brokerId, cash.file_id, names);
    const cashCheckbox = page.getByTestId(`dt-row-checkbox-${cash.file_id}`);

    // Parse waits. First behind the set: the custody export alone is an incomplete set, still ticked — its hint comes first.
    await expect(card, 'the custody export alone: the set misses its statement').toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
    await expect(card, 'the custody export keeps its tick').toHaveAttribute('data-selected', 'all');
    await expect(page.getByTestId('import-wizard-set-blocks'), 'a ticked set that is not complete blocks the analysis').toBeVisible();
    await expect(parse).toBeDisabled();

    // Then on the statement alone. The custody export excluded, no set blocks — and Parse still waits: the only ticked file
    // has no plugin. The plugin-required hint has no testid, so that state is read by elimination.
    await card.getByTestId('report-set-exclude').click();
    await expect(card, 'the custody export is excluded from the import').toHaveAttribute('data-selected', 'none', {timeout: 5_000});
    await expect(page.getByTestId('import-wizard-set-blocks'), 'no ticked set blocks any more').toHaveCount(0);
    await expect(cashCheckbox, 'excluding the set leaves the statement ticked').toHaveAttribute('data-state', 'checked');
    await expect(parse, 'a ticked file with no plugin holds the analysis back').toBeDisabled();

    // The custody export ticked again. The statement's select offers exactly what reads it — the set's plugin among them —
    // and Danske chosen there puts the statement back in the set.
    await card.getByTestId('report-set-select').click();
    await expect(card, 'the custody export is ticked again').toHaveAttribute('data-selected', 'all', {timeout: 5_000});
    const select = singleRow(page, brokerId, cash.file_id).getByTestId('import-plugin-select');
    await optionsClosed(page);
    await select.getByRole('combobox').click();
    const danskeOption = select.getByTestId(`search-select-option-${DANSKE}`);
    await expect(danskeOption, 'the set’s plugin is offered for the statement').toBeVisible({timeout: 5_000});
    const offered = () => select.locator('[data-testid^="search-select-option-"]').evaluateAll((options) => options.map((option) => option.getAttribute('data-testid')));
    await expect.poll(offered, {message: 'the select offers the plugins that read the statement: its compatible_plugins'}).toEqual((cash.compatible_plugins ?? []).map((code) => `search-select-option-${code}`));
    await danskeOption.click();
    await optionsClosed(page);

    // Back in the set: both members, complete, ticked whole — and Parse can go.
    await expect(roleRow(card, 'cash', cash.file_id), 'the statement is back in the cash table of the card').toBeVisible({timeout: 15_000});
    await expect(roleRow(card, 'custody', custody.file_id), 'beside the custody export').toBeVisible();
    await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]'), 'the card holds both members').toHaveCount(2);
    await expect(cashCheckbox, 'and the statement is no single file').toHaveCount(0);
    await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
    await expect(card, 'both members are ticked: the set is ticked whole').toHaveAttribute('data-selected', 'all');
    await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
    await expect(page.getByTestId('import-wizard-set-blocks')).toHaveCount(0);
    await expect(parse, 'the set, whole and ticked, can be analysed').toBeEnabled({timeout: 10_000});
}

/** Drop `files` on step 1, give them to the owned broker, Next: the upload records, once step 2 has settled. */
async function uploadToStep2(page: Page, brokerId: number, files: string[]): Promise<UploadedInfo[]> {
    await dropFiles(page, files);
    await expect(pendingRows(page)).toHaveCount(files.length);
    await assignOwnedBroker(page, brokerId);
    const uploaded = await uploadsDuring(page, files.length, async () => {
        await page.getByTestId('import-wizard-next').click();
        await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: 30_000});
    });
    await waitForSettled(page.getByTestId('import-wizard-step2'), 20_000);
    return uploaded;
}

/** Close the wizard through its guard and discard: this session uploaded files, so closing asks first. */
async function closeWizardDiscarding(page: Page) {
    await page.getByTestId('import-wizard-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the wizard holds this session’s work: closing it asks to discard it').toBeVisible({timeout: 5_000});
    await discard.click();
    await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: 10_000});
}

/**
 * Open the wizard again the way a user does once it is closed: from the editor it lives in. The toolbar's Import
 * opens the editor with the wizard inside it, and closing the wizard leaves that editor on screen — empty, since
 * nothing was handed over — with its backdrop over the toolbar. The editor's own Import opens the wizard again.
 *
 * Then step 2 with nothing uploaded. The memory scenarios rest on what a reopened wizard does there, so it is
 * checked rather than assumed: the step reads the brokers' files again (a new request, which holds the files
 * `uploaded` before), and selects nothing — nothing to analyse, no set of the owned broker selected, no single
 * file ticked.
 */
async function reopenOnStep2(page: Page, brokerId: number, uploaded: UploadedInfo[]): Promise<Locator> {
    // The state the reopen starts from: no guard dialog left, the editor open, empty.
    await expect(page.getByTestId('confirm-modal-confirm'), 'no guard dialog is left open').toHaveCount(0, {timeout: 5_000});
    const bulk = page.getByTestId('tx-bulk-modal-root');
    await expect(bulk, 'closing the wizard leaves the editor it was opened in').toBeVisible({timeout: 10_000});
    await expect(bulk.getByTestId('tx-bulk-body').getByTestId('dt-empty'), 'the editor is empty: nothing was handed over').toBeVisible({timeout: 10_000});

    await bulk.getByTestId('tx-bulk-import').click();
    await wizardOnStep1(page);
    await expect(pendingRows(page), 'the wizard opens again with nothing to upload').toHaveCount(0);

    // Armed before the click: the listing is the subject here, the proof that the files are read again.
    const listing = page.waitForResponse(
        (response) => {
            const url = new URL(response.url());
            return response.request().method() === 'GET' && url.pathname === FILES_PATH && url.searchParams.getAll('broker_ids').includes(String(brokerId));
        },
        {timeout: 30_000},
    );
    await page.getByTestId('import-wizard-next').click();
    const listed = await listing;
    expect(listed.status(), `GET ${FILES_PATH} of step 2`).toBe(200);
    const listedIds = ((await listed.json()) as UploadedInfo[]).filter((file) => file.target_broker_id === brokerId).map((file) => file.file_id);
    expect(listedIds, 'step 2 reads again the files uploaded before').toEqual(expect.arrayContaining(uploaded.map((file) => file.file_id)));

    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: 30_000});
    await waitForSettled(step2, 30_000);
    // Nothing preselected. Presence barrier first: the owned broker's files are listed, unselected.
    const panel = page.getByTestId(`import-wizard-broker-files-${brokerId}`);
    await expect(panel.locator('[data-testid="report-set-card"][data-selected="none"], [data-testid^="dt-row-checkbox-"][data-state="unchecked"]').first(), 'step 2 lists the owned broker’s files, unselected').toBeVisible({timeout: 10_000});
    await expect(page.getByTestId('import-wizard-parse'), 'nothing is selected: nothing to analyse').toBeDisabled();
    await expect(panel.locator('[data-testid="report-set-card"]:not([data-selected="none"])'), 'no set of the owned broker is selected').toHaveCount(0);
    await expect(panel.locator('[data-testid^="dt-row-checkbox-"][data-state="checked"]'), 'no single file of the owned broker is ticked').toHaveCount(0);
    return step2;
}

/** The synthetic cash statement of the samples, line by line: Latin-1, `;`, the newest row first. */
function sampleCashLines(): string[] {
    return readFileSync(CASH_CSV, 'latin1')
        .split(/\r?\n/)
        .filter((line) => line !== '');
}

/**
 * A third cash statement for the main set, invented: the sample's header and encoding, three rows of
 * 2021 that continue its running balance (1657,96 after 03.07.2020). Danske reads it as a cash export
 * after the custody period, so the set stays complete with it and without it. In the bank's format
 * only, like the sample: the plugins that read it are the sample's.
 */
function writeThirdCashStatement(filePath: string): string {
    const rows = ['15.03.2021;Palvelumaksut 03/2021;-3,5;1900,96;Toteutunut;Ei', '10.02.2021;Matti Meikäläinen;250;1904,46;Toteutunut;Ei', '05.01.2021;Palvelumaksut 12/2020;-3,5;1654,46;Toteutunut;Ei'];
    mkdirSync(path.dirname(filePath), {recursive: true});
    writeFileSync(filePath, Buffer.from([sampleCashLines()[0], ...rows, ''].join('\n'), 'latin1'));
    return filePath;
}

/** What the dual statement needs of the test's `testInfo`: its output folder. */
type OutputFolder = {outputPath: (...pathSegments: string[]) => string};

/**
 * The dual statement (decision 1): the sample cash statement that the generic CSV reads too — the same
 * rows, plus four columns the generic CSV maps (`date`, `type`, `amount`, `currency`) after the bank's,
 * which Danske ignores. The sample itself names no `date` nor `type` column, so only Danske reads it;
 * every scenario that needs the generic CSV to read the statement uploads this one instead. Written in
 * the test's output folder under a unique name, Latin-1 and `;` like the sample; it combines like it.
 */
function writeDualCash(testInfo: OutputFolder): string {
    const filePath = testInfo.outputPath(`danske_bank-cash-both-${uniqueSuffix()}.csv`);
    const [header, ...rows] = sampleCashLines();
    const extended = rows.map((row) => {
        const [day, , amount] = row.split(';');
        const [dd, mm, yyyy] = day.split('.');
        const value = Number(amount.replace(',', '.'));
        return `${row};${yyyy}-${mm}-${dd};${value < 0 ? 'withdrawal' : 'deposit'};${value.toFixed(2)};EUR`;
    });
    mkdirSync(path.dirname(filePath), {recursive: true});
    writeFileSync(filePath, Buffer.from([`${header};date;type;amount;currency`, ...extended, ''].join('\n'), 'latin1'));
    return filePath;
}

/** The upload record of the dual statement, its premise read from the upload response: Danske and the generic CSV both read it. */
function dualCashUpload(uploaded: UploadedInfo[], filePath: string): UploadedInfo {
    const cash = uploadNamed(uploaded, path.basename(filePath));
    expect(cash.compatible_plugins ?? [], `premise: Danske and the generic CSV both read the dual statement ${cash.filename}`).toEqual(expect.arrayContaining([DANSKE, GENERIC]));
    return cash;
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
        // The bank's own exports, on a broker with no default plugin. A18 — a set plugin wins over a broker
        // default that reads a member too — is its own scenario, on the dual statement: the generic CSV does
        // not read this sample, which names no date and no type column (decision 1).
        const brokerId = await startOnOwnedBroker(page, 'R1');

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
        // U1: one table per role, each listing its export of this upload; nothing listed the old way.
        await expect(roleRow(card, 'custody', custody.file_id), 'the custody export in the custody table').toBeVisible();
        await expect(roleRow(card, 'cash', cash.file_id), 'the cash statement in the cash table').toBeVisible();
        await expect(roleTable(card, 'custody').locator('tbody tr[data-row-id]')).toHaveCount(1);
        await expect(roleTable(card, 'cash').locator('tbody tr[data-row-id]')).toHaveCount(1);
        await expect(card.getByTestId('report-set-member')).toHaveCount(0);
        await expect(card.locator('[data-testid="report-set-role-table"] [data-testid^="dt-row-checkbox-"]'), 'the set is chosen whole: no row selection').toHaveCount(0);
        await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
        // U1: a broker with a set and no single file has no heading for "the other files".
        await expect(singleFileRows(page, brokerId), 'precondition: the owned broker holds the set of this upload and nothing else').toHaveCount(0);
        await expect(otherFilesHeading(page, brokerId)).toHaveCount(0);
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
        // G (D): every set request names the files left out — none here. Soft, so the rest of R1 still runs and reports.
        expect
            .soft(
                combines.map((call) => [call.status, call.request]),
                'one combine of the set, leaving nothing out',
            )
            .toEqual([[200, {broker_id: brokerId, plugin_code: DANSKE, batch_id: batchId, exclude_file_ids: []}]]);
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
        // U3: the five outcomes are chips, in reading order, each with its count.
        const chips = pairing.getByTestId('parse-detail-pairing-outcome');
        await expect(chips, 'one chip per outcome of the combine').toHaveCount(Object.keys(MAIN_SET.outcomes).length, {timeout: F2_FIRST});
        await expect.poll(() => chips.evaluateAll((elements) => elements.map((element) => `${element.getAttribute('data-outcome')}=${element.getAttribute('data-count')}`))).toEqual(Object.entries(MAIN_SET.outcomes).map(([outcome, count]) => `${outcome}=${count}`));
        // U3: the preview opens the combined file — the one just built — over the detail.
        await pairing.getByTestId('parse-detail-preview-combined').click();
        const preview = page.getByTestId('file-preview-modal');
        await expect(preview, 'the preview of the combined file opens').toBeVisible({timeout: 8_000});
        await expect(page.getByTestId('file-preview-shell')).toHaveAttribute('data-busy', 'false', {timeout: 30_000});
        await expect(page.getByTestId('file-preview-download'), 'the preview shows the combined file').toHaveAttribute('href', `${API}/brokers/import/files/${combined.file_id}/download`);
        await preview.press('Escape');
        await expect(preview).toHaveCount(0, {timeout: 5_000});
        await expect(detail, 'closing the preview leaves the detail open').toBeVisible();
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

    test('A18: on a broker that imports with the generic CSV by default, a statement both plugins read joins the Danske set and is analysed through its combined file', async ({page}, testInfo) => {
        test.setTimeout(150_000);
        // A18 — a file a report-set plugin recognises belongs to that plugin's set, default or not. The
        // dual statement, because the generic CSV does not read the bank's own one (decision 1).
        const brokerId = await startOnOwnedBroker(page, 'A18', {default_import_plugin: GENERIC});
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        expect(cash.batch_id, 'the two exports of one step-1 session share its batch').toBe(batchId);

        // ② the statement is a member of the Danske set: in its cash table, not a single file read with the default.
        const step2 = page.getByTestId('import-wizard-step2');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-plugin-code', DANSKE);
        await expect(card).toHaveAttribute('data-selected', 'all');
        await expect(step2.locator(`[data-testid="report-set-card"][data-batch-id="${batchId}"]`), 'one card for the upload').toHaveCount(1);
        await openCard(card);
        await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
        await expect(roleRow(card, 'cash', cash.file_id), 'the dual statement is in the cash table of the Danske set').toBeVisible();
        await expect(singleFileRows(page, brokerId), 'no file of the upload is a single file').toHaveCount(0);

        // ③ one combine of the set, then one parse — of the combined file, with Danske: never the statement alone with the default.
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeEnabled({timeout: 5_000});
        const stopRecording = recordJsonPosts(page, (pathname) => pathname === COMBINE_PATH || PARSE_PATH.test(pathname));
        await parse.click();
        const step3 = page.getByTestId('import-wizard-step3');
        await expect(step3).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 60_000);
        await expect(step3).toHaveAttribute('data-parse-state', 'ok');
        const calls = await stopRecording();
        const combines = calls.filter((call) => call.path === COMBINE_PATH);
        // The set's fields only: whether the body also names the files left out is G's (R1, G-B).
        expect(
            combines.map((call) => {
                const body = call.request as SetRequestBody;
                return [call.status, body.broker_id, body.plugin_code, body.batch_id];
            }),
            'one combine of the set, with Danske',
        ).toEqual([[200, brokerId, DANSKE, batchId]]);
        const combined = (combines[0].body as {combined: {file_id: string; derived_from: Array<{file_id: string}>}}).combined;
        expect(combined.derived_from.map((ref) => ref.file_id).sort(), 'the combined file holds both exports').toEqual([custody.file_id, cash.file_id].sort());
        expect(
            calls.filter((call) => PARSE_PATH.test(call.path)).map((call) => [call.path, call.status, (call.request as {plugin_code?: string}).plugin_code]),
            'one parse, of the combined file, with the set plugin',
        ).toEqual([[`${API}/brokers/import/files/${combined.file_id}/parse`, 200, DANSKE]]);
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
        await expect(roleRow(card, 'custody', custody.file_id), 'the export of the first upload in the custody table').toBeVisible();
        await expect(roleRow(card, 'cash', cash.file_id), 'the statement dropped after the warning in the cash table').toBeVisible();
        await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]')).toHaveCount(2);
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
        await expect(roleRow(card, 'custody', custody.file_id), 'the custody export in its table').toBeVisible();
        // The role without a file keeps its missing block, and has no table.
        await expect(card.locator('[data-testid="report-set-missing"][data-role="cash"]')).toBeVisible();
        await expect(card.getByTestId('report-set-missing')).toHaveCount(1);
        await expect(roleTable(card, 'cash')).toHaveCount(0);
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
        await expect(roleRow(card, 'cash', cash.file_id), 'the uploaded statement joins the cash table').toBeVisible();
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
        const genericCheckbox = page.getByTestId(`dt-row-checkbox-${generic.file_id}`);
        await expect(genericCheckbox).toHaveAttribute('data-state', 'checked');
        // U1: a broker with a set and a single file — the single files sit under their own heading, in
        // the broker's panel, outside the card, before the row of the generic file.
        const heading = otherFilesHeading(page, brokerId);
        await expect(heading, 'the single files of a broker that has a set too have their heading').toBeVisible({timeout: F2_FIRST});
        await expect(page.getByTestId(`import-wizard-broker-files-${brokerId}`).getByTestId(`import-wizard-other-files-${brokerId}`)).toHaveCount(1);
        await expect(card.getByTestId(`import-wizard-other-files-${brokerId}`)).toHaveCount(0);
        const headingFirst = await heading.evaluate((element, rowTestId) => {
            const row = document.querySelector(`[data-testid="${rowTestId}"]`);
            return row !== null && (element.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0;
        }, `dt-row-checkbox-${generic.file_id}`);
        expect(headingFirst, 'the heading comes before the single file it introduces').toBe(true);

        await openCard(card);
        await expect(roleRow(card, 'custody', custody.file_id), 'the custody export in its table').toBeVisible();
        // The generic file is a single: a selected row of the broker table, not a member of the set.
        await expect(card.locator(`tr[data-row-id="${generic.file_id}"]`)).toHaveCount(0);
        await expect(card.locator(`[data-testid="report-set-unrecognised"][data-file-id="${generic.file_id}"]`)).toHaveCount(0);
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
    // F2 — U2: the history LibreFolio already holds, on the timeline of the card
    // -----------------------------------------------------------------------

    /**
     * U2-B. An earlier import left the broker a Danske Bank history: two transactions tagged
     * `danske_bank`, seeded over the API before this upload (out of date order, on purpose). The
     * preview reads it — H0 is the oldest date, `history_end` the newest, `history_count` 2 — and the
     * timeline draws it from H0 to that end, no longer to the end of the line; the legend names it.
     * The files are drawn with their periods and rows, without a hole. Nothing is analysed or saved:
     * the test stops at step 2, and the seeded rows go with the broker's forced delete.
     */
    test('F2-U2: the timeline draws the history LibreFolio holds, from H0 to its newest transaction, with its count', async ({page}) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'F2-U2');
        const history = {dates: ['2020-04-20', '2019-11-04'], start: '2019-11-04', end: '2020-04-20'} as const;
        await seedDanskeHistory(page, brokerId, history.dates);

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

        await waitForSettled(page.getByTestId('import-wizard-step2'), 20_000);
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expandCard(card);
        // Premise, read rather than inferred: the preview found the seeded history (the note of a later import).
        await expect(card.locator('[data-testid="report-set-history"][data-kind="later"]'), 'the preview found the seeded history').toBeVisible();
        const timeline = card.getByTestId('report-set-timeline');
        await expect(timeline).toBeVisible();

        const historyBar = timeline.getByTestId('report-set-timeline-history');
        await expect(historyBar, 'the history starts on H0, its oldest transaction').toHaveAttribute('data-start', history.start, {timeout: F2_FIRST});
        await expect(historyBar, 'the history ends on its newest transaction').toHaveAttribute('data-end', history.end);
        await expect(historyBar, 'the history counts its transactions').toHaveAttribute('data-count', String(history.dates.length));

        // The files, each one bar with its role, period and rows; no hole in either role.
        for (const [role, file] of [
            ['custody', custody],
            ['cash', cash],
        ] as const) {
            const bar = timeline.locator(`[data-testid="report-set-timeline-bar"][data-file-id="${file.file_id}"]`);
            await expect(bar, `${role}: one bar`).toHaveCount(1);
            await expect(bar).toHaveAttribute('data-role', role);
            await expect(bar).toHaveAttribute('data-start', MAIN_MEMBERS[role].start);
            await expect(bar).toHaveAttribute('data-end', MAIN_MEMBERS[role].end);
            await expect(bar).toHaveAttribute('data-rows', String(MAIN_MEMBERS[role].rows));
        }
        await expect(timeline.getByTestId('report-set-timeline-gap')).toHaveCount(0);

        // The legend: the files and the history; no gap to name.
        const legend = timeline.getByTestId('report-set-timeline-legend');
        await expect(legend.locator('[data-testid="report-set-timeline-legend-item"][data-kind="file"]')).toHaveCount(1);
        await expect(legend.locator('[data-testid="report-set-timeline-legend-item"][data-kind="history"]')).toHaveCount(1);
        await expect(legend.locator('[data-testid="report-set-timeline-legend-item"][data-kind="gap"]')).toHaveCount(0);
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

        // D-S14: every correction is selected by default. Nothing is active (expectOpeningDeposit left it
        // so): the table holds every correction of the group, each toggle pressed.
        const proposalCount = Number(await step.getAttribute('data-proposal-count'));
        expect(proposalCount, 'at least the opening deposit is proposed').toBeGreaterThan(0);
        await expect(step).toHaveAttribute('data-selected-count', String(proposalCount));
        const toggles = step.locator('[data-testid="gapfix-table"] [data-testid="gapfix-proposal-toggle"]');
        await expect(toggles, 'one row per correction').toHaveCount(proposalCount);
        await expect(step.locator('[data-testid="gapfix-table"] [data-testid="gapfix-proposal-toggle"][aria-pressed="true"]')).toHaveCount(proposalCount);
        await expect(step.getByTestId('gapfix-proposal'), 'the list of C3 is gone').toHaveCount(0);
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
        const proposalCount = Number(await step.getAttribute('data-proposal-count'));
        expect(proposalCount, 'at least the opening deposit is proposed').toBeGreaterThan(0);
        await expect(step).toHaveAttribute('data-selected-count', String(proposalCount));

        // onToggle: the deposit unticked by the toggle of its own row.
        const group = step.locator(`[data-testid="gapfix-group"][data-broker-id="${brokerId}"]`);
        const deposit = group.locator('[data-testid="gapfix-table"] [data-testid="gapfix-proposal-toggle"][data-type="DEPOSIT"]');
        await expect(deposit).toHaveAttribute('aria-pressed', 'true');
        await deposit.click();
        await expect(deposit).toHaveAttribute('aria-pressed', 'false', {timeout: 5_000});
        await expect(step).toHaveAttribute('data-selected-count', String(proposalCount - 1));

        // onSetSelected: every other correction of the group goes with deselect all, in one go.
        await group.getByTestId('gapfix-deselect-all').click();
        await expect(step).toHaveAttribute('data-selected-count', '0', {timeout: 5_000});
        await expect(group.locator('[data-testid="gapfix-proposal-toggle"][aria-pressed="false"]')).toHaveCount(proposalCount);
        await expect(group.locator('[data-testid="gapfix-proposal-toggle"][aria-pressed="true"]')).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-gapfix-count')).toHaveAttribute('data-count', '0');

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
        // U1: a broker with single files and no set has no heading for "the other files".
        await expect(page.getByTestId(`import-wizard-broker-sets-${brokerId}`), 'precondition: the owned broker holds no set').toHaveCount(0);
        await expect(otherFilesHeading(page, brokerId)).toHaveCount(0);
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

    // -----------------------------------------------------------------------
    // G — the user chooses how a set is read (plan §14 G.2)
    // -----------------------------------------------------------------------

    test('H-E1 (G-A, R1): «Read as» is our own select, and "one by one" chosen through it keeps both files ticked — the statement with the generic CSV, the custody export with no plugin', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'H-E1');
        // The dual statement: one by one, the generic CSV is the single-file plugin that reads it (decision 1).
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');

        // R1: folded, the card is its header — and «Read as» there is our own select, not the system's.
        await foldCard(card);
        const trigger = card.getByTestId('report-set-read-as-button');
        await expect(trigger, '«Read as» is our own select: its trigger is in the header').toBeVisible({timeout: H_FIRST});
        await expect(card.locator('select'), 'no native select in the header of the card').toHaveCount(0);
        // Opened, it says how the set is read — with Danske — and offers to read the files one by one.
        await trigger.click();
        const dropdown = card.getByTestId('report-set-read-as-dropdown');
        await expect(dropdown, '«Read as» opens its list').toBeVisible({timeout: 5_000});
        await expect(dropdown.getByTestId(`report-set-read-as-option-${DANSKE}`), 'the set is read with Danske').toHaveAttribute('aria-selected', 'true');
        const oneByOne = dropdown.getByTestId('report-set-read-as-option-one-by-one');
        await expect(oneByOne, 'the "one by one" choice').toHaveAttribute('aria-selected', 'false');
        await oneByOne.click();

        // No set any more: each file is a single, and both stay ticked (R2) — the statement with its best single-file
        // plugin, the custody export, which no single-file plugin reads, with none.
        const step2 = page.getByTestId('import-wizard-step2');
        await expect(step2.locator(`[data-testid="report-set-card"][data-batch-id="${batchId}"]`), 'no card holds this upload any more').toHaveCount(0, {timeout: 10_000});
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);
        await expectSelectedSingleWithoutPlugin(page, brokerId, custody.file_id, names);
    });

    test('G-B: "read it alone" takes the statement out of the set and the set requests say so; its plugin select brings it back', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'G-B');
        // The dual statement: the generic CSV reads it, so it can be read alone with it (decision 1).
        const dualCash = writeDualCash(testInfo);
        const requests = recordSetRequests(page);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);
        // D: nothing is left out yet, and every preview of the set says so with an empty list.
        const firstPreviews = setBodies(requests.calls, 'preview', brokerId, batchId);
        expect(firstPreviews.length, 'the wizard previewed the set it uploaded').toBeGreaterThan(0);
        expect.soft(firstPreviews.map(excludedOf), 'a set with nothing left out sends exclude_file_ids: []').toEqual(firstPreviews.map(() => []));

        // B: the statement, read alone with the generic CSV.
        await runMemberAction(page, card, 'cash', cash.file_id, `read-alone-${GENERIC}`);
        await expect(card.locator('[data-testid="report-set-missing"][data-role="cash"]'), 'without its statement the set misses the cash role').toBeVisible({timeout: 15_000});
        await expect(card).toHaveAttribute('data-set-status', 'incomplete');
        await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0);
        await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
        await expect(otherFilesHeading(page, brokerId), 'the statement is now one of the broker’s other files').toBeVisible();
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);
        await expect.poll(() => excludedOf(lastOf(setBodies(requests.calls, 'preview', brokerId, batchId))), {message: 'the next preview of the set leaves the statement out', timeout: 10_000}).toEqual([cash.file_id]);

        // Back into the set: the set's plugin, chosen in the plugin select of the single file.
        const previewsBefore = setBodies(requests.calls, 'preview', brokerId, batchId).length;
        const pluginSelect = singleRow(page, brokerId, cash.file_id).getByTestId('import-plugin-select');
        await optionsClosed(page);
        await pluginSelect.getByRole('combobox').click();
        const danskeOption = pluginSelect.getByTestId(`search-select-option-${DANSKE}`);
        await expect(danskeOption).toBeVisible({timeout: 5_000});
        await danskeOption.click();
        await optionsClosed(page);
        await expect(roleRow(card, 'cash', cash.file_id), 'the statement is back in the cash table of the card').toBeVisible({timeout: 15_000});
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await expect(card.getByTestId('report-set-missing')).toHaveCount(0);
        await expect(page.getByTestId(`dt-row-checkbox-${cash.file_id}`), 'no longer a single file').toHaveCount(0);
        await expect.poll(() => excludedOf(lastOf(setBodies(requests.calls, 'preview', brokerId, batchId).slice(previewsBefore))), {message: 'the next preview of the set leaves nothing out', timeout: 10_000}).toEqual([]);
        requests.stop();
    });

    test('G-C: a broker that imports with the generic CSV by default — the card of its set says so', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'G-C', {default_import_plugin: GENERIC});
        // The dual statement: the note needs a member the default reads, and it reads no export of the bank's own (decision 1).
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(uploadNamed(uploaded, 'danske_bank-custody.xlsx').batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        // A18: the set's plugin reads the set, default or not; C1 says that the default would read a member differently.
        await expect(card).toHaveAttribute('data-plugin-code', DANSKE);
        await openCard(card);
        await expect(roleRow(card, 'cash', cash.file_id), 'premise: the member the default reads is in the set').toBeVisible();
        await expect(card.locator(`[data-testid="report-set-default-note"][data-default-plugin="${GENERIC}"]`), 'the note names the broker’s default plugin').toBeVisible({timeout: G_FIRST});
        await expect(card.getByTestId('report-set-default-note')).toHaveCount(1);
    });

    test('G-memory (set): reopened after an analysis, the set is the one analysed — the statement removed from it stays out, unselected', async ({page}, testInfo) => {
        test.setTimeout(180_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'G-MA');
        const thirdPath = writeThirdCashStatement(testInfo.outputPath(`danske_bank-cash-2021-${uniqueSuffix()}.csv`));
        const requests = recordSetRequests(page);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV, thirdPath]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        const third = uploadNamed(uploaded, path.basename(thirdPath));
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        // In the bank's format only: the plugins that read it are the sample's — Danske, and since decision 1 only Danske.
        expect(third.compatible_plugins, 'premise: the invented statement is read like the sample').toEqual(cash.compatible_plugins);
        expect(third.compatible_plugins, 'premise: Danske reads the invented statement').toContain(DANSKE);
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);
        await expect(roleRow(card, 'cash', third.file_id), 'premise: the third statement is a member of the set').toBeVisible();

        // B: removed from the set — a single file, still ticked but with no plugin (R5) — and the set's preview leaves it out.
        await runMemberAction(page, card, 'cash', third.file_id, 'remove-from-set');
        await expect(card.locator(`tr[data-row-id="${third.file_id}"]`), 'the card no longer lists it').toHaveCount(0, {timeout: 15_000});
        await expectSelectedSingleWithoutPlugin(page, brokerId, third.file_id, names);
        await expect.poll(() => excludedOf(lastOf(setBodies(requests.calls, 'preview', brokerId, batchId))), {message: 'the next preview of the set leaves the third statement out', timeout: 10_000}).toEqual([third.file_id]);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        requests.stop();

        // The set left is complete and ticked, so nothing blocks: Parse waits on the third statement alone, ticked with no
        // plugin. To analyse the set without it the user unticks it — «—», no select.
        await expect(page.getByTestId('import-wizard-set-blocks'), 'the set left is complete: it blocks nothing').toHaveCount(0);
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse, 'the ticked statement with no plugin holds the analysis back').toBeDisabled();
        await page.getByTestId(`dt-row-checkbox-${third.file_id}`).click();
        await expectUnselectedSingle(page, brokerId, third.file_id);

        // The analysis: the combine leaves it out too, and the combined file of the two kept exports is parsed.
        await expect(parse).toBeEnabled({timeout: 10_000});
        const stopRecording = recordJsonPosts(page, (pathname) => pathname === COMBINE_PATH || PARSE_PATH.test(pathname));
        await parse.click();
        await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 60_000);
        const calls = await stopRecording();
        const combines = calls.filter((call) => call.path === COMBINE_PATH);
        expect(
            combines.map((call) => [call.status, call.request]),
            'one combine of the set, leaving the third statement out',
        ).toEqual([[200, {broker_id: brokerId, plugin_code: DANSKE, batch_id: batchId, exclude_file_ids: [third.file_id]}]]);
        const combined = (combines[0].body as {combined: {file_id: string; derived_from: Array<{file_id: string}>}}).combined;
        expect(combined.derived_from.map((ref) => ref.file_id).sort(), 'the combined file holds the two kept exports').toEqual([custody.file_id, cash.file_id].sort());
        expect(
            calls.filter((call) => PARSE_PATH.test(call.path)).map((call) => [call.path, call.status]),
            'one parse, of the combined file',
        ).toEqual([[`${API}/brokers/import/files/${combined.file_id}/parse`, 200]]);

        // Closed without importing, then opened again: what was analysed, not what detection would say.
        await closeWizardDiscarding(page);
        const step2 = await reopenOnStep2(page, brokerId, uploaded);
        await expect(card, 'the set of the upload is a card again').toBeVisible({timeout: 15_000});
        await expect(step2.locator(`[data-testid="report-set-card"][data-batch-id="${batchId}"]`), 'one card for the upload').toHaveCount(1);
        await expect(card).toHaveAttribute('data-analysed', 'true');
        await openCard(card);
        await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
        await expect(roleRow(card, 'cash', cash.file_id)).toBeVisible();
        await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]'), 'exactly the two exports it was analysed with').toHaveCount(2);
        await expect(card.locator(`tr[data-row-id="${third.file_id}"]`)).toHaveCount(0);
        await expect(otherFilesHeading(page, brokerId), 'the third statement is one of the broker’s other files').toBeVisible();
        await expectUnselectedSingle(page, brokerId, third.file_id);
    });

    test('G-memory (alone): reopened after an analysis, a statement analysed alone stays alone with its plugin; the custody export is an incomplete set by itself', async ({page}, testInfo) => {
        test.setTimeout(180_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'G-MS');
        // The dual statement: a file analysed alone is one the analysis really parsed, and the generic CSV parses this one.
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);

        // B: the statement read alone with the generic CSV; the custody export alone is excluded from this import.
        await runMemberAction(page, card, 'cash', cash.file_id, `read-alone-${GENERIC}`);
        await expect(card.locator('[data-testid="report-set-missing"][data-role="cash"]')).toBeVisible({timeout: 15_000});
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);
        await card.getByTestId('report-set-exclude').click();
        await expect(card).toHaveAttribute('data-selected', 'none', {timeout: 5_000});

        // The analysis: one parse, of the statement alone, with the generic CSV; no combine.
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse).toBeEnabled({timeout: 10_000});
        const stopRecording = recordJsonPosts(page, (pathname) => pathname === COMBINE_PATH || PARSE_PATH.test(pathname));
        await parse.click();
        await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 60_000);
        const calls = await stopRecording();
        expect(
            calls.map((call) => [call.path, call.status, (call.request as {plugin_code?: string}).plugin_code]),
            'one parse, of the statement alone, with the generic CSV',
        ).toEqual([[`${API}/brokers/import/files/${cash.file_id}/parse`, 200, GENERIC]]);

        // Closed without importing, then opened again.
        await closeWizardDiscarding(page);
        await reopenOnStep2(page, brokerId, uploaded);
        // The custody export is a set by itself: incomplete, the statement is none of its members.
        await expect(card).toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
        await openCard(card);
        await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
        await expect(card.locator('[data-testid="report-set-missing"][data-role="cash"]')).toBeVisible();
        await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]'), 'the custody export alone').toHaveCount(1);
        // The statement is a single file — unselected, as everything after a reopen — read with the generic CSV once selected.
        await expectUnselectedSingle(page, brokerId, cash.file_id);
        await page.getByTestId(`dt-row-checkbox-${cash.file_id}`).click();
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);
    });

    test('G-no-memory: a choice made before any analysis is not remembered — reopened, the statement is back in its set', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'G-NM');
        // The dual statement: the generic CSV reads it, so it can be read alone with it (decision 1).
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);
        await runMemberAction(page, card, 'cash', cash.file_id, `read-alone-${GENERIC}`);
        await expect(page.getByTestId(`dt-row-checkbox-${cash.file_id}`), 'read alone: a single file, for this session').toBeVisible({timeout: 10_000});

        // Closed with the files only uploaded, then opened again: detection, as if nothing had been chosen.
        await closeWizardDiscarding(page);
        await reopenOnStep2(page, brokerId, uploaded);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);
        await expect(roleRow(card, 'custody', custody.file_id)).toBeVisible();
        await expect(roleRow(card, 'cash', cash.file_id), 'the statement is back in the set').toBeVisible();
        await expect(page.getByTestId(`dt-row-checkbox-${cash.file_id}`), 'and is no single file').toHaveCount(0);
    });

    test('G-real: the bank’s own statement can only be removed from its set — nothing offers to read it alone, not even the broker’s default', async ({page}) => {
        test.setTimeout(90_000);
        // The samples themselves, on a broker whose default is the generic CSV: a default that cannot read a file is no way to read it.
        const brokerId = await startOnOwnedBroker(page, 'G-R', {default_import_plugin: GENERIC});
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        // Decision 1, read from the upload: no `date` nor `type` column, so only Danske reads the bank's statement.
        // Soft, so that the menu below still reports.
        expect.soft(cash.compatible_plugins, 'decision 1: only Danske reads danske_bank-cash.csv').toEqual([DANSKE]);
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await openCard(card);

        const row = roleRow(card, 'cash', cash.file_id);
        await expect(row, 'the statement is in the cash table of the card').toBeVisible();
        await row.getByTestId(`row-actions-${cash.file_id}`).click();
        const menu = page.getByTestId('context-menu');
        await expect(menu).toBeVisible({timeout: 5_000});
        // Presence barrier: the menu is open on its actions, so the absence below is not a menu still rendering.
        await expect(menu.getByTestId('context-menu-action-preview'), 'the menu of a member offers its preview').toBeVisible();
        await expect(menu.getByTestId('context-menu-action-remove-from-set'), 'the menu of a member offers to remove it from the set').toBeVisible({timeout: G_FIRST});
        await expect(menu.locator('[data-testid^="context-menu-action-read-alone-"]'), 'no single-file plugin reads the bank’s statement: nothing offers to read it alone').toHaveCount(0);
        await page.keyboard.press('Escape');
        await expect(menu).toHaveCount(0, {timeout: 5_000});
    });

    // -----------------------------------------------------------------------
    // H — the developer's first review of G (plan §17.5)
    // -----------------------------------------------------------------------

    test('H-E2 (R2), the bank’s own exports: "one by one" keeps both members ticked, neither with a plugin — Parse waits; Danske, still offered on each file, re-forms the set, ticked', async ({page}) => {
        test.setTimeout(120_000);
        const names = await pluginNames(page);
        // The samples as the bank exports them: one by one, no single-file plugin reads either file.
        const brokerId = await startOnOwnedBroker(page, 'H-E2');
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        // Premise, read from the upload (decision 1): only Danske reads the bank's statement, so read alone it has no plugin.
        expect(cash.compatible_plugins, 'premise: no single-file plugin reads the bank’s statement').toEqual([DANSKE]);
        await readOneByOneThenBack(page, brokerId, custody, cash, null, names);
    });

    test('H-E2 (R2), the dual statement: "one by one" keeps both members ticked — the statement with the generic CSV, the custody export with none, so Parse waits; Danske on each file re-forms the set, ticked', async ({page}, testInfo) => {
        test.setTimeout(120_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'H-E2-dual');
        // The dual statement: one by one, the generic CSV is the single-file plugin that reads it; Danske reads it back into the set.
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        await readOneByOneThenBack(page, brokerId, custody, cash, names.generic, names);
    });

    test('H-E3 (R5): the way back from "remove from the set" — the statement stays ticked with an empty plugin select, and Parse waits; Danske chosen there puts it back in the set, both members ticked', async ({page}) => {
        test.setTimeout(90_000);
        const names = await pluginNames(page);
        // The samples themselves: the bank's statement, which only Danske reads.
        const brokerId = await startOnOwnedBroker(page, 'H-E3');
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        await openCard(card);

        // Removed from the set: a single file, still ticked — its plugin select there with no plugin chosen (R5).
        await runMemberAction(page, card, 'cash', cash.file_id, 'remove-from-set');
        await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0, {timeout: 15_000});
        await expectSelectedSingleWithoutPlugin(page, brokerId, cash.file_id, names);
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse, 'nothing can be analysed yet: the set misses its statement, and the statement has no plugin').toBeDisabled();

        // Danske chosen there, straight away: back in the set, which holds both members again, ticked whole.
        await chooseSinglePlugin(page, brokerId, cash.file_id, DANSKE);
        await expect(roleRow(card, 'cash', cash.file_id), 'the statement is back in the cash table of the card').toBeVisible({timeout: 15_000});
        await expect(roleRow(card, 'custody', custody.file_id), 'beside the custody export').toBeVisible();
        await expect(card.locator('[data-testid="report-set-role-table"] tbody tr[data-row-id]'), 'the card holds both members').toHaveCount(2);
        await expect(page.getByTestId(`dt-row-checkbox-${cash.file_id}`), 'and the statement is no single file').toHaveCount(0);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card, 'both members are ticked: the set is ticked whole').toHaveAttribute('data-selected', 'all');
        await expect(parse, 'the set, whole and ticked, can be analysed').toBeEnabled({timeout: 10_000});
    });

    test('H-E5 (R4): "read it alone with the generic CSV" from a set that is not ticked leaves the statement unticked — «—», no select; ticked, its select holds the generic CSV', async ({page}, testInfo) => {
        test.setTimeout(90_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'H-E5');
        // The dual statement: the generic CSV reads it, so it can be read alone with it (decision 1).
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');

        // The set unticked first: none of its files is selected.
        await card.getByTestId('report-set-select').click();
        await expect(card, 'the set is not ticked').toHaveAttribute('data-selected', 'none', {timeout: 5_000});
        await openCard(card);

        // "Read it alone with…" changes how the statement is read, never whether: out of the set, it is still unticked.
        await runMemberAction(page, card, 'cash', cash.file_id, `read-alone-${GENERIC}`);
        await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0, {timeout: 15_000});
        await expectUnselectedSingle(page, brokerId, cash.file_id);
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse, 'nothing is ticked: nothing to analyse').toBeDisabled();

        // Ticked, its plugin select holds the choice made in the menu: the generic CSV.
        await page.getByTestId(`dt-row-checkbox-${cash.file_id}`).click();
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);
        // The custody export, a set by itself, stays as it was — unticked — and the statement alone can be analysed.
        await expect(card).toHaveAttribute('data-selected', 'none');
        await expect(parse, 'the ticked statement, with its plugin, can be analysed').toBeEnabled({timeout: 10_000});
    });

    test('H-E6 (latent defect): a statement read alone into a table already on screen is ticked there, and toggling another row keeps it — the checkbox and the analysis agree', async ({page}, testInfo) => {
        test.setTimeout(150_000);
        const names = await pluginNames(page);
        const brokerId = await startOnOwnedBroker(page, 'H-E6');
        // The dual statement, and generic_simple.csv: another single file of the broker, whose table is on screen first.
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash, GENERIC_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        const other = uploadNamed(uploaded, 'generic_simple.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        expect(other.compatible_plugins ?? [], 'premise: generic_simple.csv is no member of the Danske set').not.toContain(DANSKE);
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');
        // The precondition, verified: the other file is a single of the broker, ticked, in a table already mounted.
        const otherCheckbox = singleRow(page, brokerId, other.file_id).getByTestId(`dt-row-checkbox-${other.file_id}`);
        await expect(otherCheckbox, 'precondition: generic_simple.csv is a ticked single file, in the table on screen').toHaveAttribute('data-state', 'checked', {timeout: 10_000});
        await openCard(card);

        // Read alone with the generic CSV, the statement joins that table — ticked there, as the wizard holds it.
        await runMemberAction(page, card, 'cash', cash.file_id, `read-alone-${GENERIC}`);
        await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0, {timeout: 15_000});
        await expectSelectedSingle(page, brokerId, cash.file_id, names.generic, names.danske);

        // Toggling another row of that table leaves the statement ticked.
        await otherCheckbox.click();
        await expect(otherCheckbox, 'the other file is unticked').toHaveAttribute('data-state', 'unchecked');
        await expect(page.getByTestId(`dt-row-checkbox-${cash.file_id}`), 'the statement stays ticked').toHaveAttribute('data-state', 'checked');

        // The wizard agrees. The custody export, an incomplete set by itself, is excluded; what is analysed is the statement, alone.
        await expect(card).toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
        await card.getByTestId('report-set-exclude').click();
        await expect(card).toHaveAttribute('data-selected', 'none', {timeout: 5_000});
        const parse = page.getByTestId('import-wizard-parse');
        await expect(parse, 'the statement is still selected, with its plugin').toBeEnabled({timeout: 10_000});
        const stopRecording = recordJsonPosts(page, (pathname) => pathname === COMBINE_PATH || PARSE_PATH.test(pathname));
        await parse.click();
        await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: 10_000});
        await waitForParseVerdict(page, 60_000);
        const calls = await stopRecording();
        expect(
            calls.map((call) => [call.path, call.status, (call.request as {plugin_code?: string}).plugin_code]),
            'one parse, of the statement alone, with the generic CSV: not the file unticked, no combine',
        ).toEqual([[`${API}/brokers/import/files/${cash.file_id}/parse`, 200, GENERIC]]);
    });

    test('H-E7 (R3): on desktop each label of the timeline holds its whole name — the roles’ and LibreFolio’s history', async ({page}, testInfo) => {
        test.skip(testInfo.project.name !== 'desktop', 'R3 is a desktop contract: on a narrow screen a label may wrap');
        test.setTimeout(90_000);
        const brokerId = await startOnOwnedBroker(page, 'H-E7');
        // A history in LibreFolio, so the timeline has its third row: two transactions tagged danske_bank, seeded over the API.
        await seedDanskeHistory(page, brokerId, ['2020-04-20', '2019-11-04']);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const batchId = expectUuid(uploadNamed(uploaded, 'danske_bank-custody.xlsx').batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expandCard(card);
        await expect(card.locator('[data-testid="report-set-history"][data-kind="later"]'), 'premise: the preview found the seeded history').toBeVisible();
        const timeline = card.getByTestId('report-set-timeline');
        await expect(timeline).toBeVisible();

        // One label per row, keyed by its role: the custody export, the cash statement, and LibreFolio's history.
        const labels = timeline.getByTestId('report-set-timeline-label');
        await expect.poll(() => labels.evaluateAll((elements) => elements.map((element) => element.getAttribute('data-role') ?? '').sort()), {message: 'one label per row of the timeline, keyed by its role', timeout: H_FIRST}).toEqual(['cash', 'custody', 'history']);
        for (const role of ['custody', 'cash', 'history']) await expect(timeline.locator(`[data-testid="report-set-timeline-label"][data-role="${role}"]`), `the ${role} label is on screen`).toBeVisible();

        // Each holds its whole name: it has a width, and its text fits in it — nothing cut behind an ellipsis.
        const measure = () => labels.evaluateAll((elements) => elements.map((element) => ({role: element.getAttribute('data-role'), scrollWidth: element.scrollWidth, clientWidth: element.clientWidth})));
        await expect.poll(async () => (await measure()).filter((label) => !(label.clientWidth > 0 && label.scrollWidth <= label.clientWidth)), {message: 'on desktop no label of the timeline is cut: each has a width, and scrollWidth ≤ clientWidth', timeout: 5_000}).toEqual([]);
    });

    // -----------------------------------------------------------------------
    // R5 — the developer's second review of G: «Remove from the set» keeps the tick (plan §19.9, §20)
    // -----------------------------------------------------------------------

    test('R5-E1, the bank’s own exports: "remove from the set" keeps the statement ticked — no plugin, its select offering the set’s, Parse waiting on it; Danske chosen there puts it back, the set whole and ticked', async ({page}) => {
        test.setTimeout(120_000);
        const names = await pluginNames(page);
        // The samples themselves: the custody export, and the statement as the bank exports it, which only Danske reads.
        const brokerId = await startOnOwnedBroker(page, 'R5-E1');
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        // Premise, read from the upload (decision 1): out of the set, the statement's select has the set's plugin to offer, and nothing else.
        expect(cash.compatible_plugins, 'premise: only Danske reads the bank’s statement').toEqual([DANSKE]);
        await removeKeepsTheTick(page, brokerId, custody, cash, names);
    });

    test('R5-E1, the dual statement: removed from the set, the statement stays ticked with no plugin — not the generic CSV that reads it too; its select offers both, Parse waits; Danske puts it back', async ({page}, testInfo) => {
        test.setTimeout(120_000);
        const names = await pluginNames(page);
        // The dual statement: the generic CSV reads it too, so "no plugin" is a choice the removal has to make — "one by one"
        // would give it the generic CSV; removing it from the set gives it nothing.
        const brokerId = await startOnOwnedBroker(page, 'R5-E1-dual');
        const dualCash = writeDualCash(testInfo);
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, dualCash]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = dualCashUpload(uploaded, dualCash);
        await removeKeepsTheTick(page, brokerId, custody, cash, names);
    });

    test('R5-E2 (guard): "remove from the set" on a set that is not ticked leaves the statement unticked — «—», no select', async ({page}) => {
        test.setTimeout(90_000);
        // The samples themselves.
        const brokerId = await startOnOwnedBroker(page, 'R5-E2');
        const uploaded = await uploadToStep2(page, brokerId, [CUSTODY_XLSX, CASH_CSV]);
        const custody = uploadNamed(uploaded, 'danske_bank-custody.xlsx');
        const cash = uploadNamed(uploaded, 'danske_bank-cash.csv');
        const batchId = expectUuid(custody.batch_id, 'batch_id of the step-1 session');
        const card = setCard(page, brokerId, batchId);
        await expect(card).toHaveAttribute('data-set-status', 'complete', {timeout: 15_000});
        await expect(card).toHaveAttribute('data-selected', 'all');

        // The set unticked first: none of its files is selected.
        await card.getByTestId('report-set-select').click();
        await expect(card, 'the set is not ticked').toHaveAttribute('data-selected', 'none', {timeout: 5_000});
        await openCard(card);

        // Removed from the set, the statement stays as unticked as it was: «—» in its Plugin column, no select (R4).
        await runMemberAction(page, card, 'cash', cash.file_id, 'remove-from-set');
        await expect(card.locator(`tr[data-row-id="${cash.file_id}"]`), 'the card no longer lists the statement').toHaveCount(0, {timeout: 15_000});
        await expectUnselectedSingle(page, brokerId, cash.file_id);
        // Nor does the set left change its tick: the custody export alone, an incomplete set, stays unticked.
        await expect(card).toHaveAttribute('data-set-status', 'incomplete', {timeout: 15_000});
        await expect(card, 'the set left keeps its tick: none').toHaveAttribute('data-selected', 'none');
        await expect(page.getByTestId('import-wizard-parse'), 'nothing is ticked: nothing to analyse').toBeDisabled();
    });
});
