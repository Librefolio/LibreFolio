/**
 * Import Wizard — the DEGIRO Account Statement in English: a currency conversion is ONE row
 * (workstream L, D3/D10 of the DEGIRO work, issue #35). Written red first.
 *
 * The DEGIRO plugin reads `degiro-account-en.csv` (synthetic, English, `;`) into 17 transactions.
 * Four of them are FX_CONVERSION legs: two conversions of two legs each, every pair under one
 * `link_uuid`, with one description, quantity 0 and no asset:
 *
 *   USD −4.08   → EUR +3.49     (no Order Id)            USD → EUR @ 0.8554
 *   EUR −770.16 → USD +901.25   (the Apple order's)      EUR → USD @ 1.1702
 *
 * The bulk editor already shows such a pair as one row (From/To), and the batch accepts a pair
 * only whole. The review step did not: four rows, one tick per leg, and the parse's own
 * `link_uuid` handed to the editor. The approved contract (plan 31_brimDegiro, D3):
 *
 *   ① the receiving leg (positive amount) is not a row of the table; the paying leg's row —
 *     `data-row-id` its merged index, as for every row — stands for the pair;
 *   ② its cash cell holds `import-tx-pair-cash`: a From line (the paying leg's amount) and a To
 *     line (the receiving leg's) with one rule between them, the editor's `renderDualHtml`, and
 *     the chip `import-tx-pair-rate`: `<base> → <quote> @ <rate.toFixed(4)>`, base the paying
 *     currency, quote the receiving one, rate |to| / |from| (`computeFxConversionInfo`);
 *   ③ its tick selects and deselects both legs, and shows "both legs selected";
 *   ④ the editor receives whole pairs only, each under a fresh `link_uuid` its two legs share.
 *
 * Counts (decided here, and pinned): `data-selected-count` and `data-total-count` on the review
 * step count TRANSACTIONS — legs, what the Import button hands to the editor — never table rows.
 * A pair ticked is +2; after "select all" the two counts agree (the invariant of tx-import-flow
 * R2). With every pair one row, the table holds 17 − 2 = 15 rows and the total stays 17.
 *
 *   P1 the review: one row per pair (①, ②), the counts in legs, one click on a pair's tick moves
 *      both legs (③), deselect all / select all agree.
 *   P2 both conversions ticked through their rows reach the editor (④): two legs per
 *      `link_uuid`, fresh links, one editor row per pair, no pair issue in its validation.
 *   P3 a conversion ticked, then unticked, leaves no leg behind: the editor gets the other
 *      conversion whole, and a lone row (the DEPOSIT) ticked beside it.
 *   P4 "select visible" (`import-wizard-select-visible`, `step4SelectVisible`) selects the rows of
 *      the current DataTable page — and, a pair's receiving leg being no row of the table, the
 *      partner of each pair row on it (`pairs.partnerOf`). With the sample's 15 rows on one page
 *      (read first: page 1 of 1, and its rows stand for every leg), after "deselect all" one click
 *      ticks each pair row (both legs selected) and the selected count is all 17 legs.
 *
 * The points of the contract are soft assertions: before the implementation one run reports
 * every missing piece, not only the first. The corridor (upload → plugin → parse → review) and
 * the cleanup are hard. The first assertion on the new review gives it `PAIR_FIRST`, so a red
 * run fails fast on the piece that is missing.
 *
 * The corridor. Each test owns a broker — no default plugin, opened before every date of the
 * sample, cash overdraft allowed so the conversions raise no balance issue — and uploads the
 * sample through step 1 under a unique name. DEGIRO must be proposed for it (the upload's
 * `compatible_plugins`, the plugin select of step 2) and used: the parse request names
 * `broker_degiro` and the owned broker. The parse's one notice (`degiro_flatex_withdrawal`)
 * asks for a confirmation on Continue (`import-wizard-warning-confirm`), read from the parse
 * response, never probed. The conditional steps (assets, fix, duplicates) are crossed only when
 * the stepper says the wizard landed on one: a single file on a fresh broker, two distinct
 * securities and no field todo normally raise none, and which ones were crossed is annotated on
 * the test. The two securities (Apple, the Vanguard ETF) may stay unresolved in this lane: no
 * asset is created, and P2/P3 never select a row with an asset (deselect all, then tick only the
 * conversions and the DEPOSIT), so Import is never held back by one; P1 and P4 stop at the review.
 *
 * Reading the editor. The batch handed over is read from the editor's own validation
 * (`POST /transactions/validate`, sent by `tx-bulk-validate-now`): its creates, and its issues
 * by code — the editor lists issues only as translated text (`tx-bulk-issue`), so the code comes
 * from the response. A pair is one editor row: `tx-bulk-date[data-partner-date]` equal to its
 * date, and the From/To rule in `tx-bulk-row-label`.
 *
 * Cleanup. Nothing is saved: P2 and P3 close the editor through its discard guard, and the owned
 * broker is then checked to hold no transaction. The fixture leaves the page, deletes the BRIM
 * files uploaded to the owned broker since it was created (the upload's own id among them), and
 * the broker (force) — never anything this test did not create.
 *
 * Key data-testids: tx-import-button · import-wizard-stepper [aria-current="step"][data-step-id]
 * · import-wizard-step1 / file-input / import-wizard-step1-broker-select /
 * search-select-option-<brokerId> / import-wizard-next · import-wizard-step2 /
 * import-wizard-broker-files-<brokerId> / dt-row-checkbox-<fileId> / import-plugin-select /
 * import-wizard-parse · import-wizard-step3 [data-parse-state] / import-wizard-continue /
 * import-wizard-warning-confirm · import-wizard-assets-continue / import-wizard-step-fix /
 * fix-step-accept-all / fix-step-row / import-wizard-fix-continue /
 * import-wizard-duplicates-continue · import-wizard-step4 [data-selected-count][data-total-count]
 * / import-wizard-select-all / import-wizard-select-visible / import-wizard-deselect-all /
 * import-wizard-import / data-table-pagination / pagination-prev / pagination-next ·
 * import-tx-pair-cash / import-tx-pair-rate (new) · tx-bulk-modal-root [data-busy]
 * [data-validate-runs] / tx-bulk-body / tx-bulk-row-label / tx-bulk-date / tx-bulk-validate-now
 * / tx-bulk-close / confirm-modal-confirm. A review row's tick is its only `button[aria-pressed]`
 * (the `editable-checkbox` cell, as in tx-import-duplicate-precedence).
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {validateRuns, waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix} from '../fixtures/unique';
import {readFileSync} from 'fs';
import path from 'path';
import {fileURLToPath} from 'url';

const API = '/api/v1';
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const VALIDATE_PATH = `${API}/transactions/validate`;
const SPEC_DIR = path.dirname(fileURLToPath(import.meta.url));
const SAMPLE = path.resolve(SPEC_DIR, '../../../backend/app/services/brim_providers/sample_reports/degiro-account-en.csv');
const DEGIRO = 'broker_degiro';
const UI_TIMEOUT = 10_000;
const STEP_TIMEOUT = 30_000;
/** The first assertion on the new review: short, so before the implementation it fails fast, on the missing piece. */
const PAIR_FIRST = 5_000;
/** The later contract assertions: the review has settled by then, and a red must not spend the whole budget. */
const CONTRACT_TIMEOUT = 3_000;
/** Before every date of the sample: no row is held back as "before the account opened". */
const OPENED_AT = '2020-01-01';
/** `uploaded_at` and `Date.now()` share this machine's clock; a second covers any rounding. */
const CLOCK_SLACK_MS = 1_000;
/** The validation codes about the shape of a linked pair (backend `transaction_service.py`, `TXValidationCode`). */
const PAIR_ISSUE_CODES = ['linkUuidPairCount', 'pairDescriptionMismatch', 'pairTagsMismatch', 'pairTypeMismatch', 'pairSameBroker'];

/** What the sample holds, checked against its parse (backend: test_brim_degiro.py, EN_SPEC). Conversions sorted by the paying leg. */
const SAMPLE_FACTS = {
    transactions: 17,
    notices: ['degiro_flatex_withdrawal'],
    conversions: [
        {paying: 'EUR -770.16', receiving: 'USD 901.25', rate: '1.1702'},
        {paying: 'USD -4.08', receiving: 'EUR 3.49', rate: '0.8554'},
    ],
};

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Cash = {code: string; amount: string | number};
type ParsedTx = {type: string; date: string; quantity?: string | number | null; asset_id?: number | null; cash?: Cash | null; description?: string | null; link_uuid?: string | null};
type ParseResponse = {file_id: string; plugin_code: string; broker_id: number; transactions: ParsedTx[]; warnings?: Array<{code?: string}>; field_todos?: unknown[]};
type UploadedInfo = {file_id: string; filename: string; uploaded_at: string; target_broker_id: number | null; compatible_plugins?: string[] | null};

/** One FX_CONVERSION leg of the parse; `index` is its merged index, the review row's `data-row-id`. */
type Leg = {index: number; code: string; amount: number; date: string; description: string; link: string};
type FxPair = {label: string; link: string; date: string; paying: Leg; receiving: Leg; rate: string};
type LoneRow = {index: number; date: string; cash: string};
type Review = {brokerId: number; step4: Locator; parsed: ParseResponse; pairs: FxPair[]; deposit: LoneRow};

/** A create of the editor's validation: the fields the checks below read. */
type StagedCreate = {type?: string; date?: string; cash?: Cash | null; link_uuid?: string | null};
type ValidateRequest = {creates?: StagedCreate[]};
type ValidateResponse = {committed?: boolean; issues?: Array<{code?: string | null; params?: Record<string, unknown> | null}>};

/** One line of a pair cell: a label with its colon, which of the pair's currencies it names, whether it holds the expected amount. */
type LineFacts = {label: boolean; codes: string[]; amount: boolean};
type PairCellFacts = {cells: number; rules: number | null; from: LineFacts | null; to: LineFacts | null; rateChips: number | null; rateTag: string | null; rate: string | null};
type EditorRow = {date: string; partnerDate: string; fromTo: boolean};

type Owned = {brokerId: number | null; since: number; fileIds: Set<string>};

// ---------------------------------------------------------------------------
// Onboarding: a terminal, page-scoped view (copied from tx-import-flow.spec.ts)
// ---------------------------------------------------------------------------

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

/**
 * The import guide is not under test, and its coachmark can sit over the controls clicked here.
 * Installed before login, so the app's first onboarding read already sees a terminal state; it
 * never writes TEST_USER's onboarding rows.
 */
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

// ---------------------------------------------------------------------------
// Owned data: one broker per test, its uploads, nothing else
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

/** The broker this test owns. The name goes through `uniqueSuffix()`: `brokers.name` is uniquely indexed. */
async function createOwnedBroker(page: Page, owned: Owned, tag: string): Promise<number> {
    const name = `DEGIRO pairs ${tag} ${uniqueSuffix()}`;
    owned.since = Date.now();
    const body = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: OPENED_AT, allow_cash_overdraft: true}]}), `create the owned broker ${name}`);
    const created = body.results.find((result) => result.name === name);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`Owned broker "${name}" was not created: ${JSON.stringify(body.results)}`);
    owned.brokerId = created.broker_id;
    return created.broker_id;
}

/**
 * Leave the page, then delete the BRIM files on the owned broker uploaded since it was created —
 * the upload recorded from its response among them — and the broker (force, which would take its
 * transactions too; there are none). Scoped to what this test created: a broker id reused from an
 * earlier run may carry that run's files, which predate the broker and are left alone.
 */
async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const brokerId = owned.brokerId;
    if (brokerId === null) return;
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Unmount the wizard and the editor before the rows they look at go away.
    await attempt('leave the page', async () => {
        await page.goto('about:blank');
    });
    await attempt(`list the BRIM files of broker ${brokerId}`, async () => {
        const files = await jsonFrom<UploadedInfo[]>(await page.request.get(`${API}/brokers/import/files?broker_ids=${brokerId}`), `list the BRIM files of broker ${brokerId}`);
        for (const file of files) {
            if (file.target_broker_id === brokerId && Date.parse(file.uploaded_at) >= owned.since - CLOCK_SLACK_MS) owned.fileIds.add(file.file_id);
        }
    });
    for (const fileId of owned.fileIds) {
        await attempt(`BRIM file ${fileId}`, async () => {
            const result = await jsonFrom<{success?: boolean; file_id?: string}>(await page.request.delete(`${API}/brokers/import/files/${fileId}`), `delete BRIM file ${fileId}`);
            expect(result).toMatchObject({success: true, file_id: fileId});
        });
    }
    await attempt(`broker ${brokerId}`, async () => {
        const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), `delete broker ${brokerId}`);
        expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
    });
    expect(failures, 'cleanup removes the files and the broker this test created, and nothing else').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use) => {
        const owned: Owned = {brokerId: null, since: Date.now(), fileIds: new Set()};
        await installTerminalOnboardingProgress(page);
        await login(page, TEST_USER);
        try {
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// The corridor: upload → DEGIRO → parse → review
// ---------------------------------------------------------------------------

async function goToTransactions(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
}

/** Open the wizard from the toolbar (inside a fresh, empty editor); wait until step 1 has settled. */
async function openImportWizard(page: Page): Promise<void> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: UI_TIMEOUT});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1, 15_000);
}

function currentStep(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/** A plugin's product name, from the endpoint the plugin select renders: backend data, not a translation. */
async function pluginName(page: Page, code: string): Promise<string> {
    const plugins = await jsonFrom<Array<{code: string; name: string}>>(await page.request.get(`${API}/brokers/import/plugins`), 'list the import plugins');
    const plugin = plugins.find((candidate) => candidate.code === code);
    if (!plugin) throw new Error(`The backend serves no ${code} plugin: ${JSON.stringify(plugins.map((candidate) => candidate.code))}`);
    return plugin.name;
}

/**
 * Step 1 → 3 with the sample under a unique name: upload it to the owned broker, check that DEGIRO
 * is proposed for it, parse it, and return the parse response — the source of every index below.
 */
async function uploadAndParse(page: Page, owned: Owned, brokerId: number): Promise<ParseResponse> {
    // ① Upload: the sample, assigned to the owned broker through "assign all".
    const step1 = page.getByTestId('import-wizard-step1');
    const fileName = `degiro-account-en-${uniqueSuffix()}.csv`;
    await step1.getByTestId('file-input').setInputFiles({name: fileName, mimeType: 'text/csv', buffer: readFileSync(SAMPLE)});
    await expect(step1.locator('tbody tr[data-row-id]'), `${fileName} waits in the step-1 table`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await optionsClosed(page);
    await page.getByTestId('import-wizard-step1-broker-select').getByRole('combobox').click();
    const option = page.getByTestId(`search-select-option-${brokerId}`);
    await expect(option, `the owned broker ${brokerId} is offered by "assign all"`).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    const next = page.getByTestId('import-wizard-next');
    await expect(next).toBeEnabled({timeout: UI_TIMEOUT});
    const [uploadResponse] = await Promise.all([page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === UPLOAD_PATH, {timeout: STEP_TIMEOUT}), next.click()]);
    const uploaded = await jsonFrom<UploadedInfo>(uploadResponse, `upload ${fileName}`);
    owned.fileIds.add(uploaded.file_id);
    expect(uploaded.target_broker_id, 'the upload lands on the owned broker').toBe(brokerId);
    expect(uploaded.compatible_plugins ?? [], 'DEGIRO recognises its own statement').toContain(DEGIRO);

    // ② Select: the file arrives selected, with DEGIRO proposed in its plugin select.
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: STEP_TIMEOUT});
    await waitForSettled(step2, 20_000);
    const fileRow = page.getByTestId(`import-wizard-broker-files-${brokerId}`).locator(`tr[data-row-id="${uploaded.file_id}"]`);
    await expect(fileRow, 'the upload is listed under the owned broker').toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(fileRow.getByTestId(`dt-row-checkbox-${uploaded.file_id}`), 'a file uploaded in step 1 arrives selected').toHaveAttribute('data-state', 'checked', {timeout: UI_TIMEOUT});
    await expect(fileRow.getByTestId('import-plugin-select').getByRole('combobox'), 'the wizard proposes DEGIRO for the statement').toContainText(await pluginName(page, DEGIRO), {timeout: UI_TIMEOUT});

    // ③ Analyze: the parse asks DEGIRO, for the owned broker.
    const parse = page.getByTestId('import-wizard-parse');
    await expect(parse).toBeEnabled({timeout: UI_TIMEOUT});
    const parsePath = `${API}/brokers/import/files/${uploaded.file_id}/parse`;
    const [parseResponse] = await Promise.all([page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === parsePath, {timeout: STEP_TIMEOUT}), parse.click()]);
    expect(parseResponse.request().postDataJSON(), 'the analysis reads the statement with DEGIRO, for the owned broker').toMatchObject({plugin_code: DEGIRO, broker_id: brokerId});
    const parsed = await jsonFrom<ParseResponse>(parseResponse, `parse ${fileName}`);
    await waitForParseVerdict(page);
    await expect(page.getByTestId('import-wizard-step3')).toHaveAttribute('data-parse-state', 'ok');
    return parsed;
}

function legKey(leg: Pick<Leg, 'code' | 'amount'>): string {
    return `${leg.code} ${leg.amount}`;
}

function cashKey(cash: Cash | null | undefined): string {
    return cash ? `${cash.code} ${Number(cash.amount)}` : '(no cash)';
}

/**
 * The premises, read from the parse instead of assumed: the sample's 17 transactions and one
 * notice, no field todo, its two conversions — two legs per `link_uuid`, one paying and one
 * receiving, one description and one date, no asset, no quantity — and its one DEPOSIT.
 */
function sampleFacts(parsed: ParseResponse): {pairs: FxPair[]; deposit: LoneRow} {
    expect(parsed.plugin_code, 'premise: parsed by DEGIRO').toBe(DEGIRO);
    expect(parsed.transactions, `premise: the sample gives ${SAMPLE_FACTS.transactions} transactions`).toHaveLength(SAMPLE_FACTS.transactions);
    expect(
        (parsed.warnings ?? []).map((notice) => notice.code),
        'premise: the sample raises one notice',
    ).toEqual(SAMPLE_FACTS.notices);
    expect(parsed.field_todos ?? [], 'premise: no field asks for a fix').toEqual([]);

    const byLink = new Map<string, Leg[]>();
    parsed.transactions.forEach((tx, index) => {
        if (tx.type !== 'FX_CONVERSION') return;
        const link = tx.link_uuid ?? '';
        expect(link, `premise: FX leg #${index} carries a link_uuid`).not.toBe('');
        expect(tx.asset_id ?? null, `premise: FX leg #${index} has no asset`).toBeNull();
        expect(Number(tx.quantity ?? 0), `premise: FX leg #${index} moves no quantity`).toBe(0);
        const leg: Leg = {index, code: tx.cash?.code ?? '', amount: Number(tx.cash?.amount), date: String(tx.date).slice(0, 10), description: tx.description ?? '', link};
        byLink.set(link, [...(byLink.get(link) ?? []), leg]);
    });
    const pairs = [...byLink.values()].map((legs): FxPair => {
        expect(legs, 'premise: two legs per link_uuid').toHaveLength(2);
        const paying = legs.find((leg) => leg.amount < 0);
        const receiving = legs.find((leg) => leg.amount > 0);
        if (!paying || !receiving) throw new Error(`premise: a conversion pays one currency and receives another: ${JSON.stringify(legs)}`);
        expect(receiving.description, 'premise: one description per pair').toBe(paying.description);
        expect(receiving.date, 'premise: one date per pair').toBe(paying.date);
        const rate = (Math.abs(receiving.amount) / Math.abs(paying.amount)).toFixed(4);
        return {label: `${paying.code} → ${receiving.code} on ${paying.date}`, link: paying.link, date: paying.date, paying, receiving, rate};
    });
    const conversions = pairs.map((pair) => ({paying: legKey(pair.paying), receiving: legKey(pair.receiving), rate: pair.rate})).sort((a, b) => a.paying.localeCompare(b.paying));
    expect(conversions, 'premise: the two conversions of the sample').toEqual(SAMPLE_FACTS.conversions);

    const deposits = parsed.transactions.map((tx, index) => ({tx, index})).filter(({tx}) => tx.type === 'DEPOSIT');
    expect(deposits, 'premise: the sample holds one DEPOSIT').toHaveLength(1);
    const [{tx, index}] = deposits;
    expect(tx.asset_id ?? null, 'premise: the DEPOSIT has no asset').toBeNull();
    expect(tx.link_uuid ?? null, 'premise: the DEPOSIT is no pair').toBeNull();
    return {pairs, deposit: {index, date: String(tx.date).slice(0, 10), cash: cashKey(tx.cash)}};
}

/** The pair whose paying leg is in `code`: a conversion of this sample, named by its data. */
function pairPaying(pairs: FxPair[], code: string): FxPair {
    const pair = pairs.find((candidate) => candidate.paying.code === code);
    if (!pair) throw new Error(`No conversion of the sample pays in ${code}: ${JSON.stringify(pairs.map((candidate) => candidate.label))}`);
    return pair;
}

/**
 * Continue from the analysis to the review: past the notices' confirmation when the parse raised
 * notices, then across whichever conditional step the stepper lands on — never a probe for one.
 */
async function continueToReview(page: Page, parsed: ParseResponse): Promise<Locator> {
    await page.getByTestId('import-wizard-continue').click();
    if ((parsed.warnings ?? []).length > 0) {
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm, 'the notices of the parse are confirmed before going on').toBeVisible({timeout: UI_TIMEOUT});
        await confirm.click();
        await expect(confirm).toBeHidden({timeout: UI_TIMEOUT});
    }
    const marker = currentStep(page);
    const crossed: string[] = [];
    for (let hop = 0; hop < 3; hop++) {
        await expect(marker, 'the wizard leaves the analysis for a step after it').toHaveAttribute('data-step-id', /^(assets|fix|duplicates|review)$/, {timeout: STEP_TIMEOUT});
        const stepId = (await marker.getAttribute('data-step-id')) ?? '';
        if (stepId === 'review') break;
        crossed.push(stepId);
        if (stepId === 'fix') {
            await expect(page.getByTestId('import-wizard-step-fix')).toBeVisible({timeout: UI_TIMEOUT});
            await page.getByTestId('fix-step-accept-all').click();
            await expect(page.locator('[data-testid="fix-step-row"][data-decision="pending"]')).toHaveCount(0, {timeout: UI_TIMEOUT});
        }
        const advance = page.getByTestId(`import-wizard-${stepId}-continue`);
        await expect(advance, `the ${stepId} step lets the import go on`).toBeEnabled({timeout: UI_TIMEOUT});
        await advance.click();
        await expect(marker).not.toHaveAttribute('data-step-id', stepId, {timeout: STEP_TIMEOUT});
    }
    await expect(marker, 'the wizard reaches the review').toHaveAttribute('data-step-id', 'review', {timeout: STEP_TIMEOUT});
    test.info().annotations.push({type: 'steps crossed before the review', description: crossed.length > 0 ? crossed.join(' → ') : 'none'});
    const step4 = page.getByTestId('import-wizard-step4');
    await expect(step4).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step4, STEP_TIMEOUT);
    return step4;
}

/** From the transactions page to the settled review of the sample, on a broker this test owns. */
async function walkToReview(page: Page, owned: Owned, tag: string): Promise<Review> {
    const brokerId = await createOwnedBroker(page, owned, tag);
    await goToTransactions(page);
    await openImportWizard(page);
    const parsed = await uploadAndParse(page, owned, brokerId);
    const {pairs, deposit} = sampleFacts(parsed);
    const step4 = await continueToReview(page, parsed);
    return {brokerId, step4, parsed, pairs, deposit};
}

// ---------------------------------------------------------------------------
// The review
// ---------------------------------------------------------------------------

/** A review row, addressed by its merged index (the parse's position: one file, so index = row of the response). */
function reviewRow(step4: Locator, index: number): Locator {
    return step4.locator(`tbody tr[data-row-id="${index}"]`);
}

/** A review row's tick: its only `aria-pressed` control (the `editable-checkbox` cell). */
function tickOf(row: Locator): Locator {
    return row.locator('button[aria-pressed]');
}

async function deselectAll(page: Page, step4: Locator): Promise<void> {
    await page.getByTestId('import-wizard-deselect-all').click();
    await expect(step4, 'deselect all leaves nothing selected').toHaveAttribute('data-selected-count', '0', {timeout: UI_TIMEOUT});
}

/**
 * Tick or untick a row. Its state is asked first and the click is never blind (rule 14); the state
 * it ends on is soft, since for a pair's row it is the contract under test.
 */
async function setTicked(row: Locator, ticked: boolean, what: string): Promise<void> {
    const tick = tickOf(row);
    await expect(tick, `${what} has one tick`).toHaveCount(1, {timeout: UI_TIMEOUT});
    await expect(tick, `${what} is ${ticked ? 'unticked' : 'ticked'} before the click`).toHaveAttribute('aria-pressed', String(!ticked));
    await tick.click();
    await expect.soft(tick, `${what} is ${ticked ? 'ticked' : 'unticked'} after the click`).toHaveAttribute('aria-pressed', String(ticked), {timeout: CONTRACT_TIMEOUT});
}

/** The `data-row-id` of every row on the review's current page. */
function reviewRowIds(step4: Locator): Promise<string[]> {
    return step4.locator('tbody tr[data-row-id]').evaluateAll((rows) => rows.map((row) => row.getAttribute('data-row-id') ?? ''));
}

/**
 * The legs some review rows stand for, as merged indices: each row's own, and the receiving leg
 * behind each pair row among them — the leg that is no row of the table. Sorted.
 */
function legsStoodFor(rowIds: readonly string[], pairs: readonly FxPair[]): number[] {
    const legs = new Set(rowIds.map(Number));
    for (const pair of pairs) if (legs.has(pair.paying.index)) legs.add(pair.receiving.index);
    return [...legs].sort((a, b) => a - b);
}

/** The `data-row-id` of every review row that holds a pair cell. */
function pairRowIds(step4: Locator): Promise<string[]> {
    return step4.locator('tbody tr[data-row-id]').evaluateAll((rows) =>
        rows
            .filter((row) => row.querySelector('[data-testid="import-tx-pair-cash"]') !== null)
            .map((row) => row.getAttribute('data-row-id') ?? '')
            .sort(),
    );
}

/**
 * What the pair cell of `pair` says, read in its paying leg's row: how many cells, the rule between
 * the From and To lines, each line's label, currencies and amount, and the implied-rate chip reduced
 * to its tokens (codes, arrow, `@`, number: symbols and flags around the codes are presentation).
 * Lines are split on the rule with the chip taken out, wherever the chip sits. Amounts are compared
 * on their digits, so the locale's separators do not matter. Null when the paying leg is no row.
 */
async function pairCellFacts(step4: Locator, pair: FxPair): Promise<PairCellFacts | null> {
    const facts = await reviewRow(step4, pair.paying.index).evaluateAll(
        (rows, expected) => {
            const lineFacts = (text: string, digits: string): LineFacts => {
                const flat = text.replace(/\s+/g, ' ').trim();
                return {
                    label: /^[^\d:+\-−]+:/.test(flat),
                    codes: expected.codes.filter((code) => new RegExp(`\\b${code}\\b`).test(flat)),
                    amount: flat.replace(/\D/g, '').includes(digits),
                };
            };
            return rows.map((row): PairCellFacts => {
                const cells = row.querySelectorAll('[data-testid="import-tx-pair-cash"]');
                if (cells.length !== 1) return {cells: cells.length, rules: null, from: null, to: null, rateChips: null, rateTag: null, rate: null};
                const clone = cells[0].cloneNode(true) as HTMLElement;
                const chips = clone.querySelectorAll('[data-testid="import-tx-pair-rate"]');
                const chip = chips.length === 1 ? chips[0] : null;
                const rate = chip ? (chip.textContent?.match(/[A-Z]{3}|→|@|\d+(?:[.,]\d+)?/g) ?? []).join(' ') : null;
                chips.forEach((element) => element.remove());
                const rules = clone.querySelectorAll('hr');
                let from: LineFacts | null = null;
                let to: LineFacts | null = null;
                if (rules.length === 1) {
                    const before = document.createRange();
                    before.setStart(clone, 0);
                    before.setEndBefore(rules[0]);
                    const after = document.createRange();
                    after.setStartAfter(rules[0]);
                    after.setEnd(clone, clone.childNodes.length);
                    from = lineFacts(before.toString(), expected.payingDigits);
                    to = lineFacts(after.toString(), expected.receivingDigits);
                }
                return {cells: 1, rules: rules.length, from, to, rateChips: chips.length, rateTag: chip?.tagName ?? null, rate};
            });
        },
        {
            codes: [pair.paying.code, pair.receiving.code],
            payingDigits: pair.paying.amount.toFixed(2).replace(/\D/g, ''),
            receivingDigits: pair.receiving.amount.toFixed(2).replace(/\D/g, ''),
        },
    );
    return facts.length === 1 ? facts[0] : null;
}

/** The pair cell of the contract: From the paying leg, To the receiving leg, one rule between, one rate chip. */
function expectedPairCell(pair: FxPair): PairCellFacts {
    return {
        cells: 1,
        rules: 1,
        from: {label: true, codes: [pair.paying.code], amount: true},
        to: {label: true, codes: [pair.receiving.code], amount: true},
        rateChips: 1,
        rateTag: 'SPAN',
        rate: `${pair.paying.code} → ${pair.receiving.code} @ ${pair.rate}`,
    };
}

// ---------------------------------------------------------------------------
// The editor
// ---------------------------------------------------------------------------

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

/**
 * The editor's own validation of what it holds, asked explicitly once the hand-over's has settled:
 * its request (the creates, as they would be committed) and its response (the issues, by code).
 * The run counter is sampled before the click (rule 16).
 */
async function validateNow(page: Page, root: Locator): Promise<{request: ValidateRequest; response: ValidateResponse}> {
    await waitForSettled(root, STEP_TIMEOUT);
    const before = await validateRuns(root);
    const [sent] = await Promise.all([page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === VALIDATE_PATH, {timeout: 15_000}), root.getByTestId('tx-bulk-validate-now').click()]);
    const answered = await sent.response();
    if (!answered) throw new Error('The editor validation completed without an HTTP response');
    const response = await jsonFrom<ValidateResponse>(answered, 'validate the batch handed to the editor');
    await expect.poll(() => validateRuns(root), {timeout: 20_000}).toBeGreaterThan(before);
    await waitForSettled(root, STEP_TIMEOUT);
    return {request: sent.postDataJSON() as ValidateRequest, response};
}

/** The FX legs of the batch grouped by `link_uuid`, each group its legs' cash, sorted: links compared apart. */
function legGroups(creates: StagedCreate[]): string[][] {
    const byLink = new Map<string, string[]>();
    for (const create of creates) {
        if (create.type !== 'FX_CONVERSION') continue;
        const link = create.link_uuid ?? '(no link_uuid)';
        byLink.set(link, [...(byLink.get(link) ?? []), cashKey(create.cash)]);
    }
    return [...byLink.values()].map((legs) => [...legs].sort()).sort((a, b) => a.join(' | ').localeCompare(b.join(' | ')));
}

function expectedGroups(pairs: FxPair[]): string[][] {
    return pairs.map((pair) => [legKey(pair.paying), legKey(pair.receiving)].sort()).sort((a, b) => a.join(' | ').localeCompare(b.join(' | ')));
}

function fxLinks(creates: StagedCreate[]): string[] {
    return creates.filter((create) => create.type === 'FX_CONVERSION').map((create) => create.link_uuid ?? '');
}

function describeCreate(create: StagedCreate): string {
    return `${create.type ?? '?'} ${cashKey(create.cash)} ${String(create.date ?? '').slice(0, 10)}`;
}

function pairIssues(response: ValidateResponse): string[] {
    return (response.issues ?? []).filter((issue) => PAIR_ISSUE_CODES.includes(issue.code ?? '')).map((issue) => `${issue.code} ${JSON.stringify(issue.params ?? {})}`);
}

/** Every row of the editor: its date, its partner's date (empty with no partner), and whether its label is drawn From/To. */
function editorRows(root: Locator): Promise<EditorRow[]> {
    return root
        .getByTestId('tx-bulk-body')
        .locator('tbody tr[data-row-id]')
        .evaluateAll((rows) =>
            rows
                .map((row): EditorRow => {
                    const date = row.querySelector('[data-testid="tx-bulk-date"]');
                    const label = row.querySelector('[data-testid="tx-bulk-row-label"]');
                    return {date: date?.getAttribute('data-date') ?? '', partnerDate: date?.getAttribute('data-partner-date') ?? '', fromTo: !!label && label.querySelector('hr') !== null};
                })
                .sort((a, b) => `${a.date}|${a.partnerDate}`.localeCompare(`${b.date}|${b.partnerDate}`)),
        );
}

function sortedRows(rows: EditorRow[]): EditorRow[] {
    return [...rows].sort((a, b) => `${a.date}|${a.partnerDate}`.localeCompare(`${b.date}|${b.partnerDate}`));
}

/** Never Save All: close the editor through its unsaved-changes guard, then prove nothing reached the owned broker. */
async function discardEditor(page: Page, root: Locator, brokerId: number): Promise<void> {
    await page.getByTestId('tx-bulk-close').click();
    const discard = page.getByTestId('confirm-modal-confirm');
    await expect(discard, 'the editor holds the imported rows: closing it asks to discard them').toBeVisible({timeout: UI_TIMEOUT});
    await discard.click();
    await expect(root).toHaveCount(0, {timeout: UI_TIMEOUT});
    const saved = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/transactions?broker_id=${brokerId}`), 'read the owned broker transactions');
    expect(
        saved.map((row) => row.id),
        'discarding the editor saved nothing on the owned broker',
    ).toEqual([]);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — DEGIRO currency conversions as linked pairs', () => {
    test('P1: in review a conversion is one row — the paying leg, with From/To and the implied rate — and its tick moves both legs', async ({page, owned}) => {
        const {step4, parsed, pairs} = await walkToReview(page, owned, 'P1');
        const legs = parsed.transactions.length;

        // Presence barrier for every absence below: each paying leg is a row — it always was one,
        // and it stands for its pair now.
        for (const pair of pairs) await expect(reviewRow(step4, pair.paying.index), `the paying leg of ${pair.label} is a row of the review`).toBeVisible({timeout: UI_TIMEOUT});

        // ① One row per pair: its cell in the paying leg's row, the receiving leg no row of its own.
        await expect.soft(step4.getByTestId('import-tx-pair-cash'), 'one From/To cash cell per currency conversion').toHaveCount(pairs.length, {timeout: PAIR_FIRST});
        await expect.soft.poll(() => pairRowIds(step4), {message: 'the pair cells sit in the paying legs’ rows', timeout: CONTRACT_TIMEOUT}).toEqual(pairs.map((pair) => String(pair.paying.index)).sort());
        for (const pair of pairs) await expect.soft(reviewRow(step4, pair.receiving.index), `the receiving leg of ${pair.label} is not a row of its own`).toHaveCount(0, {timeout: CONTRACT_TIMEOUT});
        await expect.soft(step4.locator('tbody tr[data-row-id]'), `${legs} transactions, ${pairs.length} of them pairs: ${legs - pairs.length} rows`).toHaveCount(legs - pairs.length, {timeout: CONTRACT_TIMEOUT});

        // ② The cell: From = the paying leg, To = the receiving leg, one rule between, the implied rate.
        for (const pair of pairs) {
            await expect.soft.poll(() => pairCellFacts(step4, pair), {message: `${pair.label}: From/To lines and the implied-rate chip in the cash cell`, timeout: CONTRACT_TIMEOUT}).toEqual(expectedPairCell(pair));
        }

        // ③ The counts are in transactions (legs), selected and total alike.
        await expect.soft(step4, 'the total counts transactions (legs), not rows').toHaveAttribute('data-total-count', String(legs), {timeout: CONTRACT_TIMEOUT});
        await expect.soft(step4, 'every leg arrives selected').toHaveAttribute('data-selected-count', String(legs), {timeout: CONTRACT_TIMEOUT});

        // ④ One tick, both legs: the conversion without an Order Id, out and back in.
        const pair = pairPaying(pairs, 'USD');
        const row = reviewRow(step4, pair.paying.index);
        await setTicked(row, false, `the row of ${pair.label}`);
        await expect.soft(step4, `unticking ${pair.label} leaves out both its legs`).toHaveAttribute('data-selected-count', String(legs - 2), {timeout: CONTRACT_TIMEOUT});
        await expect.soft(step4, 'the total does not move').toHaveAttribute('data-total-count', String(legs), {timeout: CONTRACT_TIMEOUT});
        await setTicked(row, true, `the row of ${pair.label}`);
        await expect.soft(step4, `ticking ${pair.label} again brings both its legs back`).toHaveAttribute('data-selected-count', String(legs), {timeout: CONTRACT_TIMEOUT});

        // ⑤ Deselect all, select all: the pair rows follow, and the two counts agree.
        await deselectAll(page, step4);
        for (const each of pairs) await expect.soft(tickOf(reviewRow(step4, each.paying.index)), `deselect all unticks ${each.label}`).toHaveAttribute('aria-pressed', 'false', {timeout: CONTRACT_TIMEOUT});
        await page.getByTestId('import-wizard-select-all').click();
        await expect.soft(step4, 'select all selects every leg').toHaveAttribute('data-selected-count', String(legs), {timeout: CONTRACT_TIMEOUT});
        await expect.soft(step4, 'select all: selected and total agree').toHaveAttribute('data-total-count', String(legs), {timeout: CONTRACT_TIMEOUT});
        for (const each of pairs) await expect.soft(tickOf(reviewRow(step4, each.paying.index)), `select all ticks ${each.label}: both legs selected`).toHaveAttribute('aria-pressed', 'true', {timeout: CONTRACT_TIMEOUT});
    });

    test('P2: both conversions ticked through their rows reach the editor whole — two legs under one fresh link_uuid each, one editor row each, no pair issue', async ({page, owned}) => {
        const {brokerId, step4, pairs} = await walkToReview(page, owned, 'P2');
        const parsedLinks = new Set(pairs.map((pair) => pair.link));

        await deselectAll(page, step4);
        let selected = 0;
        for (const pair of pairs) {
            await setTicked(reviewRow(step4, pair.paying.index), true, `the row of ${pair.label}`);
            selected += 2;
            await expect.soft(step4, `ticking ${pair.label} selects both its legs`).toHaveAttribute('data-selected-count', String(selected), {timeout: PAIR_FIRST});
        }

        const root = await importToEditor(page);
        const {request, response} = await validateNow(page, root);
        const creates = request.creates ?? [];
        expect.soft(creates.filter((create) => create.type !== 'FX_CONVERSION').map(describeCreate), 'only the conversions were ticked').toEqual([]);
        expect.soft(legGroups(creates), 'each conversion reaches the editor whole: its two legs under one link_uuid').toEqual(expectedGroups(pairs));
        const links = fxLinks(creates);
        expect
            .soft(
                links.filter((link) => link === '' || parsedLinks.has(link)),
                'every leg carries a fresh link_uuid, never the one the parse proposed',
            )
            .toEqual([]);
        expect.soft(new Set(links).size, 'one link_uuid per conversion').toBe(pairs.length);
        expect.soft(pairIssues(response), 'the editor’s validation reports no pair issue').toEqual([]);
        await expect.soft.poll(() => editorRows(root), {message: 'the editor shows each conversion as one From/To row', timeout: 5_000}).toEqual(sortedRows(pairs.map((pair) => ({date: pair.date, partnerDate: pair.date, fromTo: true}))));

        await discardEditor(page, root, brokerId);
    });

    test('P3: a conversion ticked then unticked through its row leaves no leg behind — the editor gets the other conversion whole, and the lone row ticked beside it', async ({page, owned}) => {
        const {brokerId, step4, pairs, deposit} = await walkToReview(page, owned, 'P3');
        const kept = pairPaying(pairs, 'USD');
        const dropped = pairPaying(pairs, 'EUR');

        await deselectAll(page, step4);
        await setTicked(reviewRow(step4, kept.paying.index), true, `the row of ${kept.label}`);
        await setTicked(reviewRow(step4, dropped.paying.index), true, `the row of ${dropped.label}`);
        await setTicked(reviewRow(step4, deposit.index), true, 'the DEPOSIT row');
        await expect.soft(step4, 'two conversions and a lone row: five legs').toHaveAttribute('data-selected-count', '5', {timeout: PAIR_FIRST});
        await setTicked(reviewRow(step4, dropped.paying.index), false, `the row of ${dropped.label}`);
        await expect.soft(step4, `unticking ${dropped.label} leaves out both its legs`).toHaveAttribute('data-selected-count', '3', {timeout: CONTRACT_TIMEOUT});

        const root = await importToEditor(page);
        const {request, response} = await validateNow(page, root);
        const creates = request.creates ?? [];
        expect.soft(creates.filter((create) => create.type !== 'FX_CONVERSION').map(describeCreate), 'the lone row reaches the editor, alone').toEqual([`DEPOSIT ${deposit.cash} ${deposit.date}`]);
        expect.soft(legGroups(creates), `${kept.label} reaches the editor whole, and no leg of ${dropped.label}: no orphan`).toEqual(expectedGroups([kept]));
        const links = fxLinks(creates);
        expect
            .soft(
                links.filter((link) => link === '' || link === kept.link),
                `${kept.label} carries a fresh link_uuid`,
            )
            .toEqual([]);
        expect.soft(pairIssues(response), 'the editor’s validation reports no pair issue').toEqual([]);
        await expect.soft
            .poll(() => editorRows(root), {message: 'the editor shows the conversion as one From/To row, and the lone row alone', timeout: 5_000})
            .toEqual(
                sortedRows([
                    {date: kept.date, partnerDate: kept.date, fromTo: true},
                    {date: deposit.date, partnerDate: '', fromTo: false},
                ]),
            );

        await discardEditor(page, root, brokerId);
    });

    test('P4: select visible moves both legs of every pair row on the page — each pair row ticked, every leg the page stands for selected', async ({page, owned}) => {
        const {step4, parsed, pairs, deposit} = await walkToReview(page, owned, 'P4');
        const legs = parsed.transactions.length;

        // The page holds every row — read, not assumed: page 1 of 1, nothing before it and nothing after,
        // and its rows, with the receiving leg behind each pair row, stand for every leg of the sample.
        const pagination = step4.getByTestId('data-table-pagination');
        await expect(pagination, 'the review pages its rows').toBeVisible({timeout: UI_TIMEOUT});
        await expect(pagination.getByTestId('pagination-prev'), 'no page before this one').toBeDisabled();
        await expect(pagination.getByTestId('pagination-next'), 'no page after this one').toBeDisabled();
        await expect.poll(async () => legsStoodFor(await reviewRowIds(step4), pairs), {message: `the rows of the page stand for all ${legs} legs`, timeout: UI_TIMEOUT}).toEqual(parsed.transactions.map((_, index) => index));
        const onPage = legsStoodFor(await reviewRowIds(step4), pairs);

        // The state select visible starts from: nothing selected, every pair row unticked.
        await deselectAll(page, step4);
        for (const pair of pairs) await expect(tickOf(reviewRow(step4, pair.paying.index)), `deselect all unticks ${pair.label}`).toHaveAttribute('aria-pressed', 'false', {timeout: UI_TIMEOUT});

        // Select visible: every row of the page, and the receiving leg behind each pair row on it.
        await page.getByTestId('import-wizard-select-visible').click();
        await expect.soft(step4, `select visible selects the ${onPage.length} legs the page stands for, each pair's receiving leg among them`).toHaveAttribute('data-selected-count', String(onPage.length), {timeout: PAIR_FIRST});
        for (const pair of pairs) await expect.soft(tickOf(reviewRow(step4, pair.paying.index)), `select visible ticks ${pair.label}: both its legs selected`).toHaveAttribute('aria-pressed', 'true', {timeout: CONTRACT_TIMEOUT});
        await expect.soft(tickOf(reviewRow(step4, deposit.index)), 'select visible ticks a row that is no pair, as before').toHaveAttribute('aria-pressed', 'true', {timeout: CONTRACT_TIMEOUT});
    });
});
