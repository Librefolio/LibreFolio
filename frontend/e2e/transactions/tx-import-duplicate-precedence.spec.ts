/**
 * Import Wizard — which copy of a cross-file duplicate is kept, when that movement also
 * collides with something outside the batch.
 *
 * Two overlapping exports of the same broker carry the same BUY. The wizard folds the two
 * copies into one cross-file duplicate group and keeps one of them (the one from the
 * highest-priority file). Independently, each copy can already exist in the database
 * (backend verdict `likely`). The two verdicts meet in `applyPendingDuplicateGroups`, and
 * the in-batch keeper used to win: the copy that is already in the database arrived at the
 * review PRE-SELECTED, and its "likely duplicate" badge opened the file-vs-file comparison
 * instead of the file-vs-database one. Found on real data (a TAX row present in two
 * overlapping exports and already imported).
 *
 * E1: both copies are already in the database. At review the one copy still shown arrives
 *     deselected, and its badge compares it with the database row. Was RED before workstream
 *     K's fix (C1): the copy arrived pre-selected and the badge opened the lot comparison. Both
 *     contract points are soft assertions, so one run reports both.
 * E2: control — same exports, nothing in the database. The keeper arrives selected with no
 *     database badge; keeping both copies from the resolver's lot comparison surfaces the
 *     second copy at review, and its in-batch badge compares the two files, not the database.
 * E5: the bulk-editor counterpart of E1. The two exports are imported once into the bulk editor
 *     and left unsaved, then parsed again from the editor's own Import. Every row now collides
 *     firmly with an unsaved editor row: the resolver keeps neither BUY copy by default, and the
 *     review pre-selects nothing. An export's deposit — listed, deselected — proves the editor
 *     rows reached the wizard: its badge compares it with the editor row. As with a database twin
 *     (E1), the BUY group's display primary — export A's copy — stays listed, deselected, and its
 *     editor badge compares it with the editor row, neither with the other file nor with the
 *     database; export B's copy is resolved away. Recalculating the resolver's defaults and
 *     returning to the review gives the same result: entering the duplicates step applies the
 *     editor verdict after the group pass, the recalculation re-runs the group pass alone, and
 *     the two must agree. The BUY contract points are soft assertions, so one run reports both.
 *
 * Each test owns its asset (synthetic ISIN, so the CSV asset cell auto-matches it), its broker,
 * its two inline seven-column Generic CSV uploads and, in E1, its committed database twin; all
 * are deleted in the fixture's cleanup (the broker with `force=true`, which removes its
 * transactions). E5 never saves its editor rows: it discards them through the editor's close
 * confirmation and checks the owned broker still has no transaction. Nothing global is read or
 * asserted on.
 *
 * Merged row indices — the review table's `data-row-id` — are derived from the parse
 * responses, not from DOM position: `buildMergedTransactions` numbers every row of every
 * parsed file, file by file in the order the files were *selected* (not the order the parse
 * responses arrive), and within a file in its response order. The selection order is also the
 * wizard's initial file priority, so export A (selected first) holds the default keeper.
 *
 * The import guide is not under test. Its per-step progress is lazily created `pending` for the
 * canonical users, and its coachmark panel can sit on top of the controls clicked here, so the
 * page is given a terminal onboarding view (the `tx-import-flow.spec.ts` pattern): page-scoped,
 * it never writes TEST_USER's onboarding rows.
 *
 * Key data-testids used:
 *   tx-import-button                              — opens the wizard inside a fresh bulk editor
 *   dt-row-checkbox-{fileId}                      — step 2 file selection
 *   import-wizard-stepper [aria-current="step"]   — the step the wizard is on (data-step-id)
 *   import-wizard-step-duplicates / -step4        — duplicates / review step containers
 *   import-wizard-step4 [data-selected-count]     — rows selected for import, listed or not
 *   import-wizard-duplicate-resolver-toggle       — folds the resolver panel
 *   import-wizard-resolver-recalc                 — recalculates the default keepers (resolver body)
 *   import-wizard-resolver-tier-toggle-sure       — the total-overlap tier
 *   import-wizard-duplicate-group                 — one duplicate group
 *   import-wizard-resolver-compare-{group.key}    — the group's lot comparison
 *   import-wizard-compare-{mergedIndex}           — a review row's status badge
 *   import-wizard-compare-modal / -col-{id} / -keep-{id} / -keep-all / -apply / -close
 *   import-wizard-compare-col-pending             — the unsaved editor row, in a comparison
 *   import-wizard-import / -close / -back, confirm-modal-confirm
 *   tx-bulk-modal-root / -body / -import / -close — the bulk editor, its rows, Import, close
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;
/** A step change waits on a candidate refresh and, into the duplicates step, a duplicate recheck. */
const STEP_TIMEOUT = 20_000;

const CSV_HEADER = 'date,type,quantity,amount,currency,asset,description';
const BUY_DATE = '2024-01-03';

type Owned = {
    suffix: string;
    assetIds: number[];
    brokerIds: number[];
    fileIds: string[];
};

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type DuplicateEntry = {tx_row_index: number; tx_existing_matches?: Array<{existing_tx_id: number}>};
type ParsedFile = {
    transactions: Array<{description: string; asset_id: number | null}>;
    warnings?: unknown[];
    duplicates?: {tx_likely_duplicates?: DuplicateEntry[]; tx_possible_duplicates?: DuplicateEntry[]} | unknown[] | null;
    asset_mappings: Array<{fake_asset_id: number; selected_asset_id: number | null}>;
};

/** The owned asset, broker and two overlapping exports, uploaded but not yet selected in the wizard. */
type SeededExports = {
    brokerId: number;
    assetId: number;
    buyDescription: string;
    depositDescriptionA: string;
    depositDescriptionB: string;
    fileA: string;
    fileB: string;
    /** The committed database twin of the shared BUY, when one was asked for. */
    existingBuyId: number | null;
};

/** Where the shared BUY sits in each export, and what the two parses said about it. */
type Exports = {
    brokerId: number;
    assetId: number;
    buyDescription: string;
    /** Merged-row index (review `data-row-id`) of the BUY copy from export A — the higher-priority file. */
    buyIndexA: number;
    /** Merged-row index of the BUY copy from export B. */
    buyIndexB: number;
    /** Merged-row indices of each export's own deposit (never a cross-file duplicate). */
    depositIndexA: number;
    depositIndexB: number;
    /** Whether either parse raised notices: Continue then asks for a confirmation first. */
    warned: boolean;
    parsedA: ParsedFile;
    parsedB: ParsedFile;
    /** Row index of the BUY inside each parse response (what the backend's duplicate report refers to). */
    buyRowA: number;
    buyRowB: number;
};

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

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A 12-char ISIN-shaped code the Generic CSV parser will classify as an ISIN (no checksum is enforced). */
function syntheticIsin(): string {
    return `XX${uniqueToken(9)}7`;
}

async function createAsset(page: Page, owned: Owned, isin: string): Promise<number> {
    const name = `DP asset ${owned.suffix}`;
    const data: Record<string, unknown> = {display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_ticker: `DP${uniqueToken(12)}`, identifier_isin: isin, active: true};
    schemas.FAAssetCreateItem.parse(data);
    const response = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [data]}), 'create owned asset');
    const created = response.results.find((item) => item.display_name === name);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(response)}`);
    owned.assetIds.push(created.asset_id);
    return created.asset_id;
}

async function createBroker(page: Page, owned: Owned): Promise<number> {
    const name = `DP broker ${owned.suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name, opened_at: '2020-01-01', default_import_plugin: 'broker_generic_csv'}]}), 'create owned import broker');
    const broker = created.results.find((item) => item.name === name);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(broker.broker_id);
    return broker.broker_id;
}

async function uploadCsv(page: Page, owned: Owned, brokerId: number, label: string, rows: string[]): Promise<string> {
    const csv = [CSV_HEADER, ...rows, ''].join('\n');
    const upload = await jsonFrom<{file_id: string; target_broker_id: number}>(
        await page.request.post(`${API}/brokers/import/upload`, {multipart: {broker_id: String(brokerId), file: {name: `dp-${label}-${owned.suffix}.csv`, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}}}),
        `upload export ${label}`,
    );
    owned.fileIds.push(upload.file_id);
    expect(upload.target_broker_id).toBe(brokerId);
    return upload.file_id;
}

/**
 * Commit the database twin of the shared BUY (same broker, asset, type, date, quantity, cash
 * and description), funded by an earlier deposit so the commit passes the balance check.
 * Returns the id of the committed BUY.
 */
async function commitDatabaseTwin(page: Page, owned: Owned, brokerId: number, assetId: number, buyDescription: string): Promise<number> {
    const committed = await jsonFrom<{committed: boolean; results: Array<{operation: string; ids: number[]}>}>(
        await page.request.post(`${API}/transactions/commit`, {
            data: {
                creates: [
                    {broker_id: brokerId, type: 'DEPOSIT', date: '2023-12-01', cash: {code: 'EUR', amount: '100'}, description: `DP prior funding ${owned.suffix}`},
                    {broker_id: brokerId, asset_id: assetId, type: 'BUY', date: BUY_DATE, quantity: '3', cash: {code: 'EUR', amount: '-30'}, description: buyDescription},
                ],
            },
        }),
        'commit the owned database twin',
    );
    expect(committed.committed).toBe(true);
    const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
    const query = new URLSearchParams(ids.map((id) => ['ids', String(id)]));
    const saved = await jsonFrom<Array<{id: number; type: string; description: string}>>(await page.request.get(`${API}/transactions?${query}`), 'read the owned database twin');
    const buy = saved.find((row) => row.type === 'BUY' && row.description === buyDescription);
    if (!buy) throw new Error(`The owned BUY twin was not persisted: ${JSON.stringify(saved)}`);
    return buy.id;
}

async function cleanupOwned(page: Page, owned: Owned): Promise<void> {
    const failures: string[] = [];
    const attempt = async (label: string, action: () => Promise<void>) => {
        try {
            await action();
        } catch (error) {
            failures.push(`${label}: ${String(error)}`);
        }
    };
    // Unmount the wizard before removing the rows it is looking at.
    await attempt('unmount wizard', async () => {
        await page.goto('about:blank');
    });
    for (const fileId of owned.fileIds) {
        await attempt(`file ${fileId}`, async () => {
            const result = await jsonFrom<{success: boolean; file_id: string}>(await page.request.delete(`${API}/brokers/import/files/${fileId}`), 'delete owned CSV');
            expect(result).toMatchObject({success: true, file_id: fileId});
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const result = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete owned broker');
            expect(result.results.find((item) => item.id === brokerId)?.success).toBe(true);
        });
    }
    for (const assetId of owned.assetIds) {
        await attempt(`asset ${assetId}`, async () => {
            const result = await jsonFrom<{results: Array<{asset_id: number; success: boolean}>}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete owned asset');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`Duplicate-precedence regressions may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `dp${testInfo.workerIndex}-${uniqueSuffix()}`, assetIds: [], brokerIds: [], fileIds: []};
        await installTerminalOnboardingProgress(page);
        try {
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(120_000);

// ---------------------------------------------------------------------------
// Wizard walk
// ---------------------------------------------------------------------------

function parsedDuplicates(parsed: ParsedFile, tier: 'tx_likely_duplicates' | 'tx_possible_duplicates'): DuplicateEntry[] {
    const report = parsed.duplicates;
    if (!report || Array.isArray(report)) return [];
    return report[tier] ?? [];
}

/**
 * Upload two overlapping exports of one owned broker — each with its own deposit plus the SAME
 * BUY — optionally committing the BUY's database twin first.
 */
async function seedOverlappingExports(page: Page, owned: Owned, options: {databaseTwin: boolean}): Promise<SeededExports> {
    const isin = syntheticIsin();
    const assetId = await createAsset(page, owned, isin);
    const brokerId = await createBroker(page, owned);
    const buyDescription = `DP shared buy ${owned.suffix}`;
    const depositDescriptionA = `DP funding A ${owned.suffix}`;
    const depositDescriptionB = `DP funding B ${owned.suffix}`;
    const existingBuyId = options.databaseTwin ? await commitDatabaseTwin(page, owned, brokerId, assetId, buyDescription) : null;

    const buyRow = `${BUY_DATE},BUY,3,-30,EUR,${isin},${buyDescription}`;
    const fileA = await uploadCsv(page, owned, brokerId, 'a', [`2024-01-02,DEPOSIT,0,500,EUR,,${depositDescriptionA}`, buyRow]);
    const fileB = await uploadCsv(page, owned, brokerId, 'b', [`2024-01-01,DEPOSIT,0,250,EUR,,${depositDescriptionB}`, buyRow]);
    return {brokerId, assetId, buyDescription, depositDescriptionA, depositDescriptionB, fileA, fileB, existingBuyId};
}

/** Open the import wizard from the transactions page; it opens inside a fresh, empty bulk editor. */
async function openWizardFromTransactionsPage(page: Page): Promise<void> {
    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('transactions-page')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'));
    await page.getByTestId('tx-import-button').click();
}

/**
 * From the wizard's first step (just opened, nothing uploaded in it), select export A then
 * export B — that order — and parse both, stopping on the analysis step.
 */
async function selectAndParseExports(page: Page, seeded: SeededExports): Promise<Exports> {
    const {fileA, fileB, buyDescription, assetId} = seeded;
    await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('import-wizard-step1'));
    await page.getByTestId('import-wizard-next').click();
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step2);

    // Selection order is merge order and initial file priority: A first.
    for (const fileId of [fileA, fileB]) {
        const checkbox = step2.getByTestId(`dt-row-checkbox-${fileId}`);
        await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }

    const parseOf = (fileId: string) => page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/files/${fileId}/parse` && response.request().method() === 'POST', {timeout: 30_000});
    const [responseA, responseB] = await Promise.all([parseOf(fileA), parseOf(fileB), page.getByTestId('import-wizard-parse').click()]);
    const parsedA = await jsonFrom<ParsedFile>(responseA, 'parse export A');
    const parsedB = await jsonFrom<ParsedFile>(responseB, 'parse export B');
    await waitForParseVerdict(page);

    const buyRowA = parsedA.transactions.findIndex((row) => row.description === buyDescription);
    const buyRowB = parsedB.transactions.findIndex((row) => row.description === buyDescription);
    if (buyRowA < 0 || buyRowB < 0) throw new Error(`The shared BUY is missing from a parse response: ${JSON.stringify({parsedA, parsedB})}`);
    const depositRowA = parsedA.transactions.findIndex((row) => row.description === seeded.depositDescriptionA);
    const depositRowB = parsedB.transactions.findIndex((row) => row.description === seeded.depositDescriptionB);
    if (depositRowA < 0 || depositRowB < 0) throw new Error(`An export's deposit is missing from its parse response: ${JSON.stringify({parsedA, parsedB})}`);
    // Precondition: both copies auto-match the owned asset through the ISIN cell.
    for (const [parsed, row] of [
        [parsedA, buyRowA],
        [parsedB, buyRowB],
    ] as const) {
        const fakeAssetId = parsed.transactions[row].asset_id;
        expect(parsed.asset_mappings.find((mapping) => mapping.fake_asset_id === fakeAssetId)?.selected_asset_id, 'the BUY copy auto-matches the owned asset').toBe(assetId);
    }

    return {
        brokerId: seeded.brokerId,
        assetId,
        buyDescription,
        buyIndexA: buyRowA,
        buyIndexB: parsedA.transactions.length + buyRowB,
        depositIndexA: depositRowA,
        depositIndexB: parsedA.transactions.length + depositRowB,
        warned: (parsedA.warnings?.length ?? 0) + (parsedB.warnings?.length ?? 0) > 0,
        parsedA,
        parsedB,
        buyRowA,
        buyRowB,
    };
}

/** Seed the two overlapping exports, open the wizard from the transactions page and parse both. */
async function parseOverlappingExports(page: Page, owned: Owned, options: {databaseTwin: boolean}): Promise<Exports & {existingBuyId: number | null}> {
    const seeded = await seedOverlappingExports(page, owned, options);
    await openWizardFromTransactionsPage(page);
    return {...(await selectAndParseExports(page, seeded)), existingBuyId: seeded.existingBuyId};
}

/** The stepper entry the wizard marks as current; its `data-step-id` names the step. */
function currentStepMarker(page: Page): Locator {
    return page.getByTestId('import-wizard-stepper').locator('[aria-current="step"]');
}

/**
 * Wait until the wizard has left `from`, then report the step it landed on.
 *
 * The next step is chosen only after an asynchronous candidate refresh (and, on the way into
 * the duplicates step, a duplicate recheck), so the stepper's current marker changing is the
 * moment the choice is made. Reading it afterwards is a read of settled state — not a probe
 * that would turn a slow step into an absent one.
 */
async function landedAfter(page: Page, from: string): Promise<string> {
    const marker = currentStepMarker(page);
    await expect(marker).toHaveCount(1);
    await expect(marker).not.toHaveAttribute('data-step-id', from, {timeout: STEP_TIMEOUT});
    return (await marker.getAttribute('data-step-id')) ?? '';
}

const OPTIONAL_STEP_CONTINUE: Record<'assets' | 'fix', string> = {assets: 'import-wizard-assets-continue', fix: 'import-wizard-fix-continue'};

/**
 * From the parsed analysis step to the duplicates step, crossing whichever of the optional steps
 * before it the wizard lands on: unification (both exports extracted the same ISIN) and, should
 * a row have been flagged, corrections. The duplicates step itself is not optional here — two
 * exports sharing a movement must raise it.
 */
async function walkToDuplicates(page: Page, warned: boolean): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: UI_TIMEOUT});
    await page.getByTestId('import-wizard-continue').click();
    if (warned) {
        await expect(page.getByTestId('import-wizard-warning-confirm')).toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('import-wizard-warning-confirm').click();
    }
    let step = await landedAfter(page, 'analyze');
    for (let hops = 0; (step === 'assets' || step === 'fix') && hops < 2; hops++) {
        await page.getByTestId(OPTIONAL_STEP_CONTINUE[step]).click();
        step = await landedAfter(page, step);
    }
    expect(step, 'two exports sharing a movement raise the duplicates step').toBe('duplicates');
    const duplicates = page.getByTestId('import-wizard-step-duplicates');
    await expect(duplicates).toBeVisible();
    return duplicates;
}

/** Continue from the duplicates step into the review. */
async function continueToReview(page: Page): Promise<Locator> {
    await page.getByTestId('import-wizard-duplicates-continue').click();
    expect(await landedAfter(page, 'duplicates')).toBe('review');
    const review = page.getByTestId('import-wizard-step4');
    await expect(review).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(review);
    return review;
}

/** A review row, addressed by its merged index. */
function reviewRow(review: Locator, mergedIndex: number): Locator {
    return review.locator(`tr[data-row-id="${mergedIndex}"]`);
}

/** The row's import toggle (the only `aria-pressed` control in a review row). */
function importToggle(row: Locator): Locator {
    return row.locator('button[aria-pressed]');
}

/**
 * Unfold the duplicates step down to the group holding the shared BUY and return it. Every
 * fold is asked for its state before it is clicked (the resolver opens folded when, as here,
 * every group is a total overlap). The group header publishes no testid: it is addressed, inside
 * the group, by the owned description it renders as its title.
 */
async function openBuyGroup(duplicates: Locator, buyDescription: string): Promise<Locator> {
    const tierToggle = duplicates.getByTestId('import-wizard-resolver-tier-toggle-sure');
    if (!(await tierToggle.isVisible())) await duplicates.getByTestId('import-wizard-duplicate-resolver-toggle').click();
    await expect(tierToggle).toBeVisible();

    const group = duplicates.getByTestId('import-wizard-duplicate-group').filter({hasText: buyDescription});
    if ((await group.count()) === 0) await tierToggle.click();
    await expect(group).toHaveCount(1);

    const lotCompare = group.getByTestId(/^import-wizard-resolver-compare-/);
    if ((await lotCompare.count()) === 0) await group.getByRole('button', {name: buyDescription}).click();
    await expect(lotCompare).toBeVisible();
    return group;
}

async function closeCompare(page: Page): Promise<void> {
    const modal = page.getByTestId('import-wizard-compare-modal');
    await modal.getByTestId('import-wizard-compare-close').click();
    await expect(modal).toBeHidden();
}

/**
 * Recalculate the resolver's default keepers. The button sits in the file-priority column of the
 * resolver body, which stays rendered but hidden while the resolver is folded, so the fold is
 * asked for its state before it is clicked. The recalculation sends no request — it drops the
 * manual choices and re-runs the group pass on the merged rows synchronously — so the step's
 * Continue, clicked next, reads its result.
 */
async function recalculateResolverDefaults(duplicates: Locator): Promise<void> {
    const fold = duplicates.getByTestId('import-wizard-duplicate-resolver-toggle');
    await expect(fold).toBeVisible();
    const recalc = duplicates.getByTestId('import-wizard-resolver-recalc');
    if (!(await recalc.isVisible())) await fold.click();
    await expect(recalc).toBeVisible();
    await recalc.click();
}

/**
 * At review, a BUY that both exports carry and the bulk editor already holds unsaved: the group's
 * display primary — export A's copy, the higher-priority file — stays listed, deselected, and its
 * badge compares it with the editor row; export B's copy is resolved away. The contract points are
 * soft, so a run reports every pass that disagrees; `pass` names the pass in their messages.
 */
async function expectEditorHeldBuyAtReview(page: Page, review: Locator, exports: Exports, pass: string): Promise<void> {
    // Presence first, so the absence below cannot pass on a slow table.
    const shown = reviewRow(review, exports.buyIndexA);
    await expect(shown, `${pass}: export A's BUY copy, the group's display primary, is listed`).toBeVisible({timeout: UI_TIMEOUT});
    await expect.soft(importToggle(shown), `${pass}: export A's BUY copy arrives deselected (aria-pressed=false)`).toHaveAttribute('aria-pressed', 'false');
    await expect.soft(reviewRow(review, exports.buyIndexB), `${pass}: export B's BUY copy is resolved away`).toHaveCount(0);

    const badge = review.getByTestId(`import-wizard-compare-${exports.buyIndexA}`);
    await expect(badge, `${pass}: export A's BUY copy carries a duplicate badge`).toBeVisible();
    await badge.click();
    const modal = page.getByTestId('import-wizard-compare-modal');
    await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
    await expect(modal.getByTestId(`import-wizard-compare-col-${exports.buyIndexA}`)).toBeVisible();
    await expect.soft(modal.getByTestId('import-wizard-compare-col-pending'), `${pass}: the badge compares the copy with the unsaved editor row`).toBeVisible();
    await expect.soft(modal.getByTestId(/^import-wizard-compare-col-db-/), `${pass}: the badge does not compare the copy with the database`).toHaveCount(0);
    // Exactly the copy and the editor row: the lot comparison would list export B's copy instead.
    await expect.soft(modal.getByTestId(/^import-wizard-compare-col-/), `${pass}: the comparison holds the copy and the editor row only`).toHaveCount(2);
    await closeCompare(page);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — cross-file duplicate keeper vs. database collisions', () => {
    test('E1: a cross-file copy already in the database arrives deselected at review, and its likely-duplicate badge compares it with the database row', async ({page, owned}) => {
        const exports = await parseOverlappingExports(page, owned, {databaseTwin: true});
        const existingBuyId = exports.existingBuyId!;
        // Precondition: the backend reports BOTH copies as likely duplicates of the owned twin.
        for (const [parsed, row] of [
            [exports.parsedA, exports.buyRowA],
            [exports.parsedB, exports.buyRowB],
        ] as const) {
            const entry = parsedDuplicates(parsed, 'tx_likely_duplicates').find((candidate) => candidate.tx_row_index === row);
            expect(
                entry?.tx_existing_matches?.map((match) => match.existing_tx_id),
                'each BUY copy is a likely duplicate of the database twin',
            ).toContain(existingBuyId);
        }

        await walkToDuplicates(page, exports.warned);
        const review = await continueToReview(page);

        // One copy stays on screen (the group's primary: export A, the higher-priority file); the
        // other is resolved away. Presence first, so the absence below cannot pass on a slow table.
        const shown = reviewRow(review, exports.buyIndexA);
        await expect(shown).toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(shown)).toBeVisible();
        await expect(reviewRow(review, exports.buyIndexB)).toHaveCount(0);

        // Contract 1 — a firm database collision is never pre-selected, keeper or not.
        await expect.soft(importToggle(shown), 'a copy already in the database arrives deselected (aria-pressed=false)').toHaveAttribute('aria-pressed', 'false', {timeout: 5_000});

        // Contract 2 — its "likely duplicate" badge opens the file-vs-database comparison.
        const badge = review.getByTestId(`import-wizard-compare-${exports.buyIndexA}`);
        await expect(badge).toBeVisible();
        await badge.click();
        const modal = page.getByTestId('import-wizard-compare-modal');
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        await expect(modal.getByTestId(`import-wizard-compare-col-${exports.buyIndexA}`)).toBeVisible();
        await expect.soft(modal.getByTestId(`import-wizard-compare-col-db-${existingBuyId}`), 'the likely-duplicate badge compares the row with the database twin').toBeVisible({timeout: UI_TIMEOUT});

        await closeCompare(page);
    });

    test('E2: without a database twin the keeper arrives selected with no DB badge; keeping both copies surfaces the second, whose badge compares the two files', async ({page, owned}) => {
        const exports = await parseOverlappingExports(page, owned, {databaseTwin: false});
        // Precondition: nothing in the database collides with either copy.
        for (const [parsed, row] of [
            [exports.parsedA, exports.buyRowA],
            [exports.parsedB, exports.buyRowB],
        ] as const) {
            const collisions = [...parsedDuplicates(parsed, 'tx_likely_duplicates'), ...parsedDuplicates(parsed, 'tx_possible_duplicates')];
            expect(
                collisions.map((candidate) => candidate.tx_row_index),
                'the BUY copy collides with nothing in the database',
            ).not.toContain(row);
        }

        await walkToDuplicates(page, exports.warned);
        let review = await continueToReview(page);

        // Default resolution: export A's copy is kept and selected; export B's is resolved away.
        const keeper = reviewRow(review, exports.buyIndexA);
        await expect(keeper).toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(keeper)).toHaveAttribute('aria-pressed', 'true');
        // A unique row's status cell renders no compare trigger at all (the row itself is the barrier).
        await expect(review.getByTestId(`import-wizard-compare-${exports.buyIndexA}`)).toHaveCount(0);
        await expect(reviewRow(review, exports.buyIndexB)).toHaveCount(0);

        // Back on the duplicates step, keep both copies from the group's lot comparison.
        await page.getByTestId('import-wizard-back').click();
        expect(await landedAfter(page, 'review')).toBe('duplicates');
        const duplicates = page.getByTestId('import-wizard-step-duplicates');
        await expect(duplicates).toBeVisible();
        const group = await openBuyGroup(duplicates, exports.buyDescription);
        await group.getByTestId(/^import-wizard-resolver-compare-/).click();

        const modal = page.getByTestId('import-wizard-compare-modal');
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        // The lot comparison offers the two BUY copies by merged index (a check on the index
        // derivation too); by default only export A's is kept.
        await expect(modal.getByTestId(`import-wizard-compare-keep-${exports.buyIndexA}`)).toHaveAttribute('aria-checked', 'true');
        await expect(modal.getByTestId(`import-wizard-compare-keep-${exports.buyIndexB}`)).toHaveAttribute('aria-checked', 'false');
        await modal.getByTestId('import-wizard-compare-keep-all').click();
        await expect(modal.getByTestId(`import-wizard-compare-keep-${exports.buyIndexB}`)).toHaveAttribute('aria-checked', 'true');
        await modal.getByTestId('import-wizard-compare-apply').click();
        await expect(modal).toBeHidden();

        review = await continueToReview(page);
        const second = reviewRow(review, exports.buyIndexB);
        await expect(second).toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(second)).toHaveAttribute('aria-pressed', 'true');
        await expect(importToggle(reviewRow(review, exports.buyIndexA))).toHaveAttribute('aria-pressed', 'true');

        // The second copy's in-batch badge opens the lot comparison: both files, no database column.
        await review.getByTestId(`import-wizard-compare-${exports.buyIndexB}`).click();
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        await expect(modal.getByTestId(`import-wizard-compare-col-${exports.buyIndexA}`)).toBeVisible();
        await expect(modal.getByTestId(`import-wizard-compare-col-${exports.buyIndexB}`)).toBeVisible();
        await expect(modal.getByTestId(/^import-wizard-compare-col-db-/)).toHaveCount(0);

        await closeCompare(page);
    });

    test('E5: re-importing the same exports from the bulk editor keeps and pre-selects no copy of a movement the editor already holds', async ({page, owned}) => {
        // First pass: import the two exports into the bulk editor, where they stay unsaved.
        const seeded = await seedOverlappingExports(page, owned, {databaseTwin: false});
        await openWizardFromTransactionsPage(page);
        const first = await selectAndParseExports(page, seeded);
        await walkToDuplicates(page, first.warned);
        const firstReview = await continueToReview(page);
        // Default resolution: export A's BUY copy kept (B's resolved away), both deposits selected.
        await expect(importToggle(reviewRow(firstReview, first.buyIndexA))).toHaveAttribute('aria-pressed', 'true');
        await expect(firstReview).toHaveAttribute('data-selected-count', '3');

        const bulkRoot = page.getByTestId('tx-bulk-modal-root');
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});
        await page.getByTestId('import-wizard-import').click();
        await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(bulkRoot).toBeVisible();
        await waitForSettled(bulkRoot, STEP_TIMEOUT);
        const bulkBody = page.getByTestId('tx-bulk-body');
        for (const description of [seeded.depositDescriptionA, seeded.depositDescriptionB, seeded.buyDescription]) {
            await expect(bulkBody.locator('tr', {hasText: description}), `the editor holds one unsaved "${description}"`).toHaveCount(1);
        }

        // Second pass: from the bulk editor, the wizard again, on the same two exports.
        await page.getByTestId('tx-bulk-import').click();
        const second = await selectAndParseExports(page, seeded);
        for (const parsed of [second.parsedA, second.parsedB]) {
            expect([...parsedDuplicates(parsed, 'tx_likely_duplicates'), ...parsedDuplicates(parsed, 'tx_possible_duplicates')], 'the editor rows are unsaved: nothing collides in the database').toEqual([]);
        }
        const duplicates = await walkToDuplicates(page, second.warned);

        // C1: the resolver keeps neither copy of the BUY by default — the editor already holds it.
        const group = await openBuyGroup(duplicates, seeded.buyDescription);
        await group.getByTestId(/^import-wizard-resolver-compare-/).click();
        const modal = page.getByTestId('import-wizard-compare-modal');
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        await expect(modal.getByTestId(`import-wizard-compare-keep-${second.buyIndexA}`)).toHaveAttribute('aria-checked', 'false');
        await expect(modal.getByTestId(`import-wizard-compare-keep-${second.buyIndexB}`)).toHaveAttribute('aria-checked', 'false');
        await closeCompare(page);

        const review = await continueToReview(page);
        // The editor rows did reach the wizard: an export's own deposit is listed, deselected.
        const deposit = reviewRow(review, second.depositIndexA);
        await expect(deposit).toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(deposit)).toHaveAttribute('aria-pressed', 'false');
        // No row is pre-selected: every one collides firmly with an unsaved editor row. The count
        // covers the rows the review does not list too, so it holds for both BUY copies.
        await expect(review).toHaveAttribute('data-selected-count', '0');
        // The deposit's status badge compares it with the unsaved editor row — not a file, nor the database.
        await review.getByTestId(`import-wizard-compare-${second.depositIndexA}`).click();
        await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
        await expect(modal.getByTestId(`import-wizard-compare-col-${second.depositIndexA}`)).toBeVisible();
        await expect(modal.getByTestId('import-wizard-compare-col-pending')).toBeVisible();
        await expect(modal.getByTestId(/^import-wizard-compare-col-/)).toHaveCount(2);
        await closeCompare(page);

        // As with a database twin (E1), the BUY group keeps its display primary on screen.
        await expectEditorHeldBuyAtReview(page, review, second, 'on entry');

        // Re-apply. Entering the duplicates step applied the editor verdict after the group pass;
        // recalculating the defaults re-runs the group pass alone. Both must land on the same review.
        await page.getByTestId('import-wizard-back').click();
        expect(await landedAfter(page, 'review')).toBe('duplicates');
        await expect(duplicates).toBeVisible();
        await recalculateResolverDefaults(duplicates);
        const reapplied = await continueToReview(page);
        await expect(reapplied).toHaveAttribute('data-selected-count', '0');
        await expectEditorHeldBuyAtReview(page, reapplied, second, 'after recalculating the defaults');

        // Discard through the UI: the wizard first, then the editor's unsaved rows. Nothing is saved.
        await page.getByTestId('import-wizard-close').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(page.getByTestId('import-wizard-stepper')).toHaveCount(0, {timeout: UI_TIMEOUT});
        await expect(bulkRoot).toBeVisible();
        await page.getByTestId('tx-bulk-close').click();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(bulkRoot).toHaveCount(0, {timeout: UI_TIMEOUT});
        const saved = await jsonFrom<unknown[]>(await page.request.get(`${API}/transactions?broker_id=${seeded.brokerId}`), 'read the owned broker transactions');
        expect(saved, 'discarding the editor saved nothing').toEqual([]);
    });
});
