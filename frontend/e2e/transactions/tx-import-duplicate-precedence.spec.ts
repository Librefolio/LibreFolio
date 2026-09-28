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
 * E3: an asset picked at review keeps the duplicates already arbitrated. Both exports carry the
 *     same BUY; export A also names an instrument two owned assets claim (one as its primary
 *     ISIN, one among its alternates), so that instrument reaches the review unresolved. The user
 *     keeps BOTH copies of the BUY on the duplicates step, then binds the instrument to the
 *     alternate asset at review and presses Import. Binding it invalidated the duplicate verdict,
 *     so Import rechecks first — and the recheck rebuilds exactly the group already arbitrated
 *     (same members). The wizard must hand the batch to the bulk editor, both BUY copies and the
 *     newly bound row, instead of going back to the duplicates step with the choice reset
 *     (workstream K, finding 1 / fix C2). RED before C2, on that single assertion.
 * E4: E3's negative control — an asset picked at review CREATES a cross-file group. The same
 *     movement sits in both exports under two different ISINs, each claimed by two owned assets
 *     that share one: P holds X1 as primary, R holds X2 as primary, Q holds both as alternates.
 *     Unbound, the two rows carry different asset identities: no group, no duplicates step (and
 *     nothing for the unification step to link — the Generic CSV extracts no name). Bound both to
 *     Q at review they are one movement: Import goes back to the duplicates step and must say so,
 *     a warning toast plus the event `tx.import.duplicates.changed` naming the new group (C2). RED
 *     before C2 on those two soft assertions only; continuing from there imports the default
 *     keeper alone, before and after C2.
 * E6: the status clause of C2. T sits in both exports; its ISIN is P's primary, so T auto-resolves
 *     to P, and the database already holds T itself — same broker, type, date, quantity, cash and
 *     description — bound to Q, which holds no code of T's. The backend scopes a resolved row's
 *     database match to its asset, so at parse T is unique. The user keeps BOTH copies, then
 *     re-binds T from P to Q at review (declining the add-identifier prompt, which keeps the
 *     binding) and presses Import: the recheck, now scoped to Q, reports both copies as likely
 *     duplicates of the committed row. The group the user arbitrated has the same members but no
 *     longer the same verdicts, so it is changed: Import goes back to the duplicates step, with the
 *     warning toast and the event, and the new default keeps no copy. Continuing, the review shows
 *     T's display copy (export A) deselected and the other resolved away, and Import stages
 *     export A's deposit alone, without a second recheck.
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
 * confirmation and checks the owned broker still has no transaction; E3 and E4 discard the batch
 * they hand to the bulk editor the same way. E3 and E4 own two and three assets respectively, the
 * claimants of their ambiguous codes. E6 owns two assets and, like E1, a committed twin (with its
 * funding deposit): after discarding, its broker must hold exactly those two rows. Nothing global
 * is read or asserted on.
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
 *   import-wizard-resolve-section                 — the review's resolution cards
 *   import-wizard-duplicate-hint-{fakeId}         — an ambiguous card's hint; its parent is the card
 *   import-wizard-inspect-asset-{fakeId}          — rendered once a card is bound; its parent is the card
 *   asset-select / search-select-option-{assetId} — a card's asset picker and its options
 *   identifier-prompt-confirm / -skip             — the add-identifier prompt; -skip keeps the binding
 *   toast-warning                                 — the human half of a warning notification
 *   tx-bulk-modal-root / -body / -import / -close — the bulk editor, its rows, Import, close
 *
 * Signals: `tx.import.duplicates.changed` (C2) and `tx.import.selection.changed` in the app-event
 * ring; the batch handed to the bulk editor, read from its first `POST /transactions/validate`.
 */

import {expect, test as base, type Locator, type Page, type Request} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
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
    asset_mappings: Array<{fake_asset_id: number; selected_asset_id: number | null; candidates?: Array<{asset_id: number}>}>;
};

/** An owned asset, with what the review's picker is searched by. */
type OwnedAsset = {id: number; name: string; ticker: string};

/** A create in the bulk editor's `POST /transactions/validate` (or a row the recheck asks about): the fields the checks read. */
type StagedCreate = {broker_id?: number; asset_id?: number | null; type?: string; description?: string};

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
    return (await createOwnedAsset(page, owned, 'asset', {isin})).id;
}

/** An owned ETF named `DP {label} {suffix}`, carrying `identifiers` — a primary ISIN, alternates, or both. */
async function createOwnedAsset(page: Page, owned: Owned, label: string, identifiers: {isin?: string; other?: string[]}): Promise<OwnedAsset> {
    const name = `DP ${label} ${owned.suffix}`;
    const ticker = `DP${uniqueToken(12)}`;
    const data: Record<string, unknown> = {display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_ticker: ticker, active: true};
    if (identifiers.isin) data.identifier_isin = identifiers.isin;
    if (identifiers.other) data.identifier_other = identifiers.other;
    schemas.FAAssetCreateItem.parse(data);
    const response = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [data]}), `create owned ${label}`);
    const created = response.results.find((item) => item.display_name === name);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(response)}`);
    owned.assetIds.push(created.asset_id);
    return {id: created.asset_id, name, ticker};
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
 * From the wizard's first step (just opened, nothing uploaded in it), select `files` — in that
 * order — and parse them all, stopping on the analysis step. Returns the parse responses in the
 * same order. Selection order is merge order and the initial file priority.
 */
async function selectAndParseFiles(page: Page, files: Array<{fileId: string; label: string}>): Promise<ParsedFile[]> {
    await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('import-wizard-step1'));
    await page.getByTestId('import-wizard-next').click();
    const step2 = page.getByTestId('import-wizard-step2');
    await expect(step2).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step2);

    for (const {fileId} of files) {
        const checkbox = step2.getByTestId(`dt-row-checkbox-${fileId}`);
        await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
        await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
        await checkbox.click();
        await expect(checkbox).toHaveAttribute('data-state', 'checked');
    }

    const parseOf = (fileId: string) => page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/files/${fileId}/parse` && response.request().method() === 'POST', {timeout: 30_000});
    const [responses] = await Promise.all([Promise.all(files.map(({fileId}) => parseOf(fileId))), page.getByTestId('import-wizard-parse').click()]);
    const parsed: ParsedFile[] = [];
    for (const [index, {label}] of files.entries()) parsed.push(await jsonFrom<ParsedFile>(responses[index], `parse ${label}`));
    await waitForParseVerdict(page);
    return parsed;
}

/**
 * From the wizard's first step (just opened, nothing uploaded in it), select export A then
 * export B — that order — and parse both, stopping on the analysis step.
 */
async function selectAndParseExports(page: Page, seeded: SeededExports): Promise<Exports> {
    const {fileA, fileB, buyDescription, assetId} = seeded;
    // Selection order is merge order and initial file priority: A first.
    const [parsedA, parsedB] = await selectAndParseFiles(page, [
        {fileId: fileA, label: 'export A'},
        {fileId: fileB, label: 'export B'},
    ]);

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
 * Continue from the parsed analysis step — past the notice confirmation when a parse raised
 * notices — and report the step the wizard lands on.
 */
async function leaveAnalysis(page: Page, warned: boolean): Promise<string> {
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: UI_TIMEOUT});
    await page.getByTestId('import-wizard-continue').click();
    if (warned) {
        await expect(page.getByTestId('import-wizard-warning-confirm')).toBeVisible({timeout: UI_TIMEOUT});
        await page.getByTestId('import-wizard-warning-confirm').click();
    }
    return landedAfter(page, 'analyze');
}

/**
 * From the parsed analysis step to the duplicates step, crossing whichever of the optional steps
 * before it the wizard lands on: unification (both exports extracted the same ISIN) and, should
 * a row have been flagged, corrections. The duplicates step itself is not optional here — two
 * exports sharing a movement must raise it.
 */
async function walkToDuplicates(page: Page, warned: boolean): Promise<Locator> {
    let step = await leaveAnalysis(page, warned);
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
// Resolver choices across Import's final recheck (E3, E4)
// ---------------------------------------------------------------------------

/**
 * E3's owned world: one broker whose two exports both carry the same BUY — its ISIN auto-matches
 * an owned asset — and whose export A also names an instrument two owned assets claim, so that
 * instrument reaches the review unresolved.
 */
type ArbitratedTwinExports = {
    brokerId: number;
    twin: OwnedAsset;
    twinDescription: string;
    ambiguousIsin: string;
    /** Holds the ambiguous ISIN as its primary code. */
    ambiguousPrimary: OwnedAsset;
    /** Holds the ambiguous ISIN among its alternates — the asset the user picks at review. */
    ambiguousAlternate: OwnedAsset;
    ambiguousDescription: string;
    fileA: string;
    fileB: string;
};

async function seedArbitratedTwinExports(page: Page, owned: Owned): Promise<ArbitratedTwinExports> {
    const twinIsin = syntheticIsin();
    const ambiguousIsin = syntheticIsin();
    const twin = await createOwnedAsset(page, owned, 'twin asset', {isin: twinIsin});
    const ambiguousPrimary = await createOwnedAsset(page, owned, 'ambiguous primary', {isin: ambiguousIsin});
    const ambiguousAlternate = await createOwnedAsset(page, owned, 'ambiguous alternate', {other: [ambiguousIsin]});
    const brokerId = await createBroker(page, owned);
    const twinDescription = `DP twin buy ${owned.suffix}`;
    const ambiguousDescription = `DP ambiguous buy ${owned.suffix}`;

    const twinRow = `${BUY_DATE},BUY,3,-30,EUR,${twinIsin},${twinDescription}`;
    const fileA = await uploadCsv(page, owned, brokerId, 'a', [twinRow, `2024-01-04,BUY,2,-20,EUR,${ambiguousIsin},${ambiguousDescription}`]);
    const fileB = await uploadCsv(page, owned, brokerId, 'b', [twinRow]);
    return {brokerId, twin, twinDescription, ambiguousIsin, ambiguousPrimary, ambiguousAlternate, ambiguousDescription, fileA, fileB};
}

/**
 * E4's owned world: the same movement in both exports of one broker, under two ISINs. Each code
 * is claimed by two owned assets that share one — P holds X1 as its primary, R holds X2, Q holds
 * both among its alternates — so neither row is auto-matched, and bound to Q they are one movement.
 */
type TwoCodeMovementExports = {
    brokerId: number;
    description: string;
    /** X1, export A's code. */
    isinA: string;
    /** X2, export B's code. */
    isinB: string;
    /** P: X1 as its primary. */
    primaryA: OwnedAsset;
    /** R: X2 as its primary. */
    primaryB: OwnedAsset;
    /** Q: X1 and X2 among its alternates — what both rows are bound to at review. */
    shared: OwnedAsset;
    fileA: string;
    fileB: string;
};

async function seedTwoCodeMovementExports(page: Page, owned: Owned): Promise<TwoCodeMovementExports> {
    const isinA = syntheticIsin();
    const isinB = syntheticIsin();
    const primaryA = await createOwnedAsset(page, owned, 'code A primary', {isin: isinA});
    const shared = await createOwnedAsset(page, owned, 'shared alternate', {other: [isinA, isinB]});
    const primaryB = await createOwnedAsset(page, owned, 'code B primary', {isin: isinB});
    const brokerId = await createBroker(page, owned);
    const description = `DP same movement ${owned.suffix}`;

    // Same broker, type, date, quantity, cash and description: only the asset cell differs.
    const fileA = await uploadCsv(page, owned, brokerId, 'a', [`${BUY_DATE},BUY,3,-30,EUR,${isinA},${description}`]);
    const fileB = await uploadCsv(page, owned, brokerId, 'b', [`${BUY_DATE},BUY,3,-30,EUR,${isinB},${description}`]);
    return {brokerId, description, isinA, isinB, primaryA, primaryB, shared, fileA, fileB};
}

/**
 * E6's owned world: T in both exports of one broker — export A also carries a deposit — whose ISIN
 * is P's primary, so T auto-resolves to P at parse. Q holds no code of T's, so it is no candidate;
 * the database already holds T itself (same broker, type, date, quantity, cash and description)
 * bound to Q, funded by an earlier deposit so the commit passes the balance check.
 */
type RebindExports = {
    brokerId: number;
    twinIsin: string;
    twinDescription: string;
    depositDescription: string;
    /** P: holds T's ISIN as its primary — what T auto-resolves to. */
    primary: OwnedAsset;
    /** Q: holds no code of T's — the committed twin's asset, and what T is re-bound to at review. */
    target: OwnedAsset;
    committedBuyId: number;
    /** Everything the owned broker holds before the wizard runs: the committed twin and its funding. */
    committedIds: number[];
    fileA: string;
    fileB: string;
};

async function seedRebindExports(page: Page, owned: Owned): Promise<RebindExports> {
    const twinIsin = syntheticIsin();
    const primary = await createOwnedAsset(page, owned, 'rebind primary', {isin: twinIsin});
    const target = await createOwnedAsset(page, owned, 'rebind target', {});
    const brokerId = await createBroker(page, owned);
    const twinDescription = `DP rebound buy ${owned.suffix}`;
    const depositDescription = `DP funding A ${owned.suffix}`;
    const committedBuyId = await commitDatabaseTwin(page, owned, brokerId, target.id, twinDescription);
    const committed = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/transactions?broker_id=${brokerId}`), 'read the owned committed transactions');
    const committedIds = committed.map((row) => row.id);
    expect(committedIds, 'the owned broker holds the committed twin and its funding deposit').toHaveLength(2);
    expect(committedIds).toContain(committedBuyId);

    const twinRow = `${BUY_DATE},BUY,3,-30,EUR,${twinIsin},${twinDescription}`;
    const fileA = await uploadCsv(page, owned, brokerId, 'a', [`2024-01-02,DEPOSIT,0,500,EUR,,${depositDescription}`, twinRow]);
    const fileB = await uploadCsv(page, owned, brokerId, 'b', [twinRow]);
    return {brokerId, twinIsin, twinDescription, depositDescription, primary, target, committedBuyId, committedIds, fileA, fileB};
}

/** Whether any parse raised notices: Continue then asks for a confirmation first. */
function parseWarned(parsed: ParsedFile[]): boolean {
    return parsed.some((file) => (file.warnings?.length ?? 0) > 0);
}

/** Where `description` sits in a parse response — the index its merge and duplicate report use. */
function rowIndexOf(parsed: ParsedFile, description: string, file: string): number {
    const row = parsed.transactions.findIndex((candidate) => candidate.description === description);
    if (row < 0) throw new Error(`"${description}" is missing from the parse of ${file}: ${JSON.stringify(parsed)}`);
    return row;
}

/** The asset mapping of a parsed row's instrument, found through the row's fake asset id. */
function mappingOfRow(parsed: ParsedFile, row: number): ParsedFile['asset_mappings'][number] | undefined {
    const fakeAssetId = parsed.transactions[row]?.asset_id;
    return parsed.asset_mappings.find((mapping) => mapping.fake_asset_id === fakeAssetId);
}

/**
 * The review's resolution card for an instrument two owned assets claim, picked by the ISIN its
 * header prints (data, not a label). A card publishes no testid of its own; an ambiguous one —
 * two identifier-grade candidates — renders the duplicate-asset hint as a direct child, so the
 * card is that hint's parent. The hint stays while the card is bound: it reads the candidates.
 */
function ambiguousCard(review: Locator, isin: string): Locator {
    return review
        .getByTestId('import-wizard-resolve-section')
        .getByTestId(/^import-wizard-duplicate-hint-/)
        .locator('..')
        .filter({hasText: isin});
}

/**
 * The review's resolution card of a BOUND instrument, picked by the ISIN its header prints. A bound
 * card renders its inspector button as a direct child, so the card is that button's parent; it
 * stays addressable through a re-bind, since the card is bound before and after.
 */
function boundCard(review: Locator, isin: string): Locator {
    return review
        .getByTestId('import-wizard-resolve-section')
        .getByTestId(/^import-wizard-inspect-asset-/)
        .locator('..')
        .filter({hasText: isin});
}

/**
 * Bind a resolution card to `asset` the way a user does — search its ticker, click the option —
 * and prove it took: the card offers the inspector, its trigger shows the ticker, and no
 * add-identifier prompt is left open. E4-05's `pickManually` (`tx-import-matching.spec.ts`),
 * scoped to one card. The same gesture re-binds a card that is already bound.
 *
 * `identifierPrompt` says what the pick must raise. `none`: the asset already holds the card's
 * code (among its alternates), so no prompt opens. `skip`: the asset lacks it, the prompt offers
 * to add it, and it is declined with the control that keeps the binding — never Cancel, which
 * means "wrong asset" and unbinds the card.
 */
async function pickOnCard(page: Page, review: Locator, card: Locator, asset: OwnedAsset, identifierPrompt: 'none' | 'skip' = 'none'): Promise<void> {
    const select = card.getByTestId('asset-select');
    await optionsClosed(page);
    await select.getByRole('combobox').click();
    await expect(select.getByRole('listbox')).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
    await select.getByRole('textbox').fill(asset.ticker);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    if (identifierPrompt === 'skip') {
        const skip = page.getByTestId('identifier-prompt-skip');
        await expect(skip, 'the asset lacks the code: the add-identifier prompt opens').toBeVisible({timeout: UI_TIMEOUT});
        await skip.click();
        await expect(skip).toBeHidden();
    }
    // The pick (or the declined prompt) runs a candidate refresh; let it settle before reading the card.
    await waitForSettled(review);
    await expect(card.getByTestId(/^import-wizard-inspect-asset-/)).toHaveCount(1);
    await expect(select.getByRole('combobox')).toContainText(asset.ticker, {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('identifier-prompt-confirm'), identifierPrompt === 'none' ? 'the asset already holds the code: no add-identifier prompt' : 'the add-identifier prompt is answered').toBeHidden();
}

/**
 * On the duplicates step, keep every copy of the group titled `description` from its lot
 * comparison, where by default only `keeper` — the higher-priority file's copy — is kept.
 */
async function keepEveryCopy(page: Page, duplicates: Locator, description: string, keeper: number, other: number): Promise<void> {
    const group = await openBuyGroup(duplicates, description);
    await group.getByTestId(/^import-wizard-resolver-compare-/).click();
    const modal = page.getByTestId('import-wizard-compare-modal');
    await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
    await expect(modal.getByTestId(`import-wizard-compare-keep-${keeper}`)).toHaveAttribute('aria-checked', 'true');
    await expect(modal.getByTestId(`import-wizard-compare-keep-${other}`)).toHaveAttribute('aria-checked', 'false');
    await modal.getByTestId('import-wizard-compare-keep-all').click();
    await expect(modal.getByTestId(`import-wizard-compare-keep-${other}`)).toHaveAttribute('aria-checked', 'true');
    await modal.getByTestId('import-wizard-compare-apply').click();
    await expect(modal).toBeHidden();
}

/**
 * On the duplicates step, open the group titled `description`, check which of its copies its lot
 * comparison keeps — changing nothing — and return the group's key, as its compare trigger's
 * testid publishes it.
 */
async function groupKeyKeeping(page: Page, duplicates: Locator, description: string, kept: Array<[index: number, keep: boolean]>): Promise<string> {
    const group = await openBuyGroup(duplicates, description);
    const lotCompare = group.getByTestId(/^import-wizard-resolver-compare-/);
    const key = ((await lotCompare.getAttribute('data-testid')) ?? '').replace('import-wizard-resolver-compare-', '');
    await lotCompare.click();
    const modal = page.getByTestId('import-wizard-compare-modal');
    await expect(modal).toBeVisible({timeout: UI_TIMEOUT});
    for (const [index, keep] of kept) {
        await expect(modal.getByTestId(`import-wizard-compare-keep-${index}`), `copy ${index} is ${keep ? '' : 'not '}kept by default`).toHaveAttribute('aria-checked', String(keep));
    }
    await closeCompare(page);
    return key;
}

/** The duplicate recheck posted for `brokerId`; armed just before Import, it is Import's final one. */
function duplicateRecheckOf(page: Page, brokerId: number) {
    return page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/duplicates` && response.request().method() === 'POST' && response.request().postDataJSON()?.broker_id === brokerId, {timeout: STEP_TIMEOUT});
}

/**
 * The bulk editor's first validation carrying a row described `description` — the batch the
 * wizard handed over. A request is an edge, so this is armed before the click that may cause it.
 * When the test fails before awaiting it, the timeout it then raises is handled here rather than
 * left unhandled; awaiting the returned promise still rejects.
 */
function stagedBatchWith(page: Page, description: string): Promise<Request> {
    const staged = page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === `${API}/transactions/validate` && ((request.postDataJSON() as {creates?: StagedCreate[]} | null)?.creates ?? []).some((row) => row.description === description), {
        timeout: STEP_TIMEOUT,
    });
    staged.catch(() => undefined);
    return staged;
}

function stagedCreates(request: Request): StagedCreate[] {
    return (request.postDataJSON() as {creates?: StagedCreate[]} | null)?.creates ?? [];
}

/** The `detail` of each app event named `name` recorded after `since`, oldest first. The ring is state: reading late loses nothing. */
async function eventDetailsSince(page: Page, name: string, since: number): Promise<Array<Record<string, unknown> | null>> {
    return page.evaluate(({eventName, after}) => ((window as unknown as {__lf?: {events?: Array<{seq: number; name: string; detail?: Record<string, unknown>}>}}).__lf?.events ?? []).filter((event) => event.name === eventName && event.seq > after).map((event) => event.detail ?? null), {
        eventName: name,
        after: since,
    });
}

/** The wizard is gone and the bulk editor — now holding the batch — finished validating it. */
async function expectHandedToBulkEditor(page: Page): Promise<void> {
    await expect(page.getByTestId('import-wizard-stepper'), 'the wizard closed on Import').toHaveCount(0, {timeout: UI_TIMEOUT});
    const bulkRoot = page.getByTestId('tx-bulk-modal-root');
    await expect(bulkRoot).toBeVisible();
    await waitForSettled(bulkRoot, STEP_TIMEOUT);
}

/**
 * Discard the batch through the bulk editor's close confirmation, and prove nothing was saved for
 * the owned broker: afterwards it holds exactly the rows the test committed itself, if any.
 */
async function discardBulkEditor(page: Page, brokerId: number, committedIds: number[] = []): Promise<void> {
    const bulkRoot = page.getByTestId('tx-bulk-modal-root');
    await page.getByTestId('tx-bulk-close').click();
    await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible({timeout: UI_TIMEOUT});
    await page.getByTestId('confirm-modal-confirm').click();
    await expect(bulkRoot).toHaveCount(0, {timeout: UI_TIMEOUT});
    const saved = await jsonFrom<Array<{id: number}>>(await page.request.get(`${API}/transactions?broker_id=${brokerId}`), 'read the owned broker transactions');
    const ascending = (ids: number[]) => [...ids].sort((a, b) => a - b);
    expect(ascending(saved.map((row) => row.id)), 'discarding the editor saved nothing').toEqual(ascending(committedIds));
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

test.describe('Import Wizard — resolver choices across the final duplicate recheck', () => {
    test('E3: an asset picked at review keeps the duplicates already arbitrated — Import hands both kept copies to the bulk editor instead of going back to the duplicates step', async ({page, owned}) => {
        const seeded = await seedArbitratedTwinExports(page, owned);
        await openWizardFromTransactionsPage(page);
        const [parsedA, parsedB] = await selectAndParseFiles(page, [
            {fileId: seeded.fileA, label: 'export A'},
            {fileId: seeded.fileB, label: 'export B'},
        ]);
        const twinRowA = rowIndexOf(parsedA, seeded.twinDescription, 'export A');
        const twinRowB = rowIndexOf(parsedB, seeded.twinDescription, 'export B');
        const ambiguousRow = rowIndexOf(parsedA, seeded.ambiguousDescription, 'export A');
        // Merged indices (the review's data-row-id): file by file in selection order, then response order.
        const twinIndexA = twinRowA;
        const twinIndexB = parsedA.transactions.length + twinRowB;
        const ambiguousIndex = ambiguousRow;

        // Preconditions: both twin copies auto-match their owned asset; the ambiguous row is claimed
        // by the two owned assets and matched to neither.
        expect(mappingOfRow(parsedA, twinRowA)?.selected_asset_id, "export A's twin copy auto-matches the owned asset").toBe(seeded.twin.id);
        expect(mappingOfRow(parsedB, twinRowB)?.selected_asset_id, "export B's twin copy auto-matches the owned asset").toBe(seeded.twin.id);
        const ambiguous = mappingOfRow(parsedA, ambiguousRow);
        expect(ambiguous?.selected_asset_id, 'two owned assets claim the ambiguous code: neither is auto-selected').toBeNull();
        expect(new Set(ambiguous?.candidates?.map((candidate) => candidate.asset_id)), 'the candidates are the two owned claimants').toEqual(new Set([seeded.ambiguousPrimary.id, seeded.ambiguousAlternate.id]));

        // The duplicates step: keep BOTH copies of the twin, from the group's lot comparison.
        const duplicates = await walkToDuplicates(page, parseWarned([parsedA, parsedB]));
        await keepEveryCopy(page, duplicates, seeded.twinDescription, twinIndexA, twinIndexB);

        // Review: the choice arrived — both copies listed and selected — and the ambiguous
        // instrument is still unbound, which is what keeps Import disabled.
        const review = await continueToReview(page);
        for (const index of [twinIndexA, twinIndexB]) {
            const row = reviewRow(review, index);
            await expect(row, `twin copy ${index} is listed`).toBeVisible({timeout: UI_TIMEOUT});
            await expect(importToggle(row), `twin copy ${index} is selected (aria-pressed=true)`).toHaveAttribute('aria-pressed', 'true');
        }
        await expect(reviewRow(review, ambiguousIndex)).toBeVisible();
        const card = ambiguousCard(review, seeded.ambiguousIsin);
        await expect(card).toBeVisible();
        // Presence first: the twin's card is bound, so exactly one inspector is on this review…
        await expect(review.getByTestId(/^import-wizard-inspect-asset-/)).toHaveCount(1);
        // …and it is not the ambiguous card's.
        await expect(card.getByTestId(/^import-wizard-inspect-asset-/)).toHaveCount(0);
        await expect(page.getByTestId('import-wizard-import'), 'a selected row on an unbound instrument blocks Import').toBeDisabled();

        // The change at review: bind the ambiguous instrument to the alternate asset.
        await pickOnCard(page, review, card, seeded.ambiguousAlternate);
        await expect(importToggle(reviewRow(review, ambiguousIndex))).toHaveAttribute('aria-pressed', 'true');
        await expect(review).toHaveAttribute('data-selected-count', '3');
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});

        // Import. The binding invalidated the duplicate verdict, so Import rechecks first.
        const staged = stagedBatchWith(page, seeded.twinDescription);
        const since = await eventSeq(page);
        const [recheck] = await Promise.all([duplicateRecheckOf(page, seeded.brokerId), page.getByTestId('import-wizard-import').click()]);
        await jsonFrom(recheck, 'final duplicate recheck');
        // Barrier: whatever Import decided, it has left the review.
        await expect(review, 'the final recheck settles by leaving the review step').toHaveCount(0, {timeout: STEP_TIMEOUT});

        // C2: the recheck rebuilt one group, with the same members as the one already arbitrated.
        await expect(
            page.getByTestId('import-wizard-step-duplicates'),
            'E3 (C2): the final recheck rebuilt only the group the user had already arbitrated (same members, both copies kept) — Import must hand the batch to the bulk editor, but the wizard went back to the duplicates step (import-wizard-step-duplicates)',
        ).toHaveCount(0);
        await expectHandedToBulkEditor(page);

        const creates = stagedCreates(await staged);
        expect(
            creates.filter((row) => row.description === seeded.twinDescription).map((row) => row.asset_id),
            'both kept copies of the twin are staged, on the twin asset',
        ).toEqual([seeded.twin.id, seeded.twin.id]);
        expect(creates, 'the row bound at review is staged on the alternate asset').toContainEqual(expect.objectContaining({broker_id: seeded.brokerId, asset_id: seeded.ambiguousAlternate.id, description: seeded.ambiguousDescription}));
        expect(creates, 'exactly the three rows the review had selected').toHaveLength(3);
        // Nothing new to arbitrate and nothing deselected behind the user's back: no warning at all.
        for (const name of ['tx.import.duplicates.changed', 'tx.import.selection.changed']) {
            expect(await eventDetailsSince(page, name, since), `no ${name} on the way to the bulk editor`).toEqual([]);
        }

        await discardBulkEditor(page, seeded.brokerId);
    });

    test('E4: an asset picked at review that makes two rows one movement sends Import back to the duplicates step, announced — continuing imports the default keeper alone', async ({page, owned}) => {
        const seeded = await seedTwoCodeMovementExports(page, owned);
        await openWizardFromTransactionsPage(page);
        const [parsedA, parsedB] = await selectAndParseFiles(page, [
            {fileId: seeded.fileA, label: 'export A'},
            {fileId: seeded.fileB, label: 'export B'},
        ]);
        const rowA = rowIndexOf(parsedA, seeded.description, 'export A');
        const rowB = rowIndexOf(parsedB, seeded.description, 'export B');
        // Merged indices: export A (selected first, the higher priority) numbers its rows first.
        const indexA = rowA;
        const indexB = parsedA.transactions.length + rowB;

        // Preconditions: each row is claimed by two owned assets — its code's primary and Q — and matched to neither.
        for (const [parsed, row, primary, label] of [
            [parsedA, rowA, seeded.primaryA, 'export A'],
            [parsedB, rowB, seeded.primaryB, 'export B'],
        ] as const) {
            const mapping = mappingOfRow(parsed, row);
            expect(mapping?.selected_asset_id, `${label}: two owned assets claim the code, neither is auto-selected`).toBeNull();
            expect(new Set(mapping?.candidates?.map((candidate) => candidate.asset_id)), `${label}: the candidates are the code's primary and the shared asset`).toEqual(new Set([primary.id, seeded.shared.id]));
        }

        // Unbound, the rows carry different asset identities (their two ISINs): the unification
        // step has nothing to link, no cross-file group exists, and the wizard goes straight to review.
        expect(await leaveAnalysis(page, parseWarned([parsedA, parsedB])), 'E4 precondition: neither the unification nor the duplicates step is shown before review').toBe('review');
        const stepper = page.getByTestId('import-wizard-stepper');
        await expect(stepper.locator('[data-step-id="assets"]')).toHaveCount(0);
        await expect(stepper.locator('[data-step-id="duplicates"]')).toHaveCount(0);
        const review = page.getByTestId('import-wizard-step4');
        await expect(review).toBeVisible({timeout: UI_TIMEOUT});
        await waitForSettled(review);
        for (const index of [indexA, indexB]) {
            await expect(reviewRow(review, index), `row ${index} is listed on its own`).toBeVisible({timeout: UI_TIMEOUT});
        }
        // Two cards, one per code — so the instruments were not unified — and neither is bound.
        const cardA = ambiguousCard(review, seeded.isinA);
        const cardB = ambiguousCard(review, seeded.isinB);
        await expect(cardA).toBeVisible();
        await expect(cardB).toBeVisible();
        await expect(review.getByTestId(/^import-wizard-inspect-asset-/)).toHaveCount(0);

        // The change at review: bind both rows to Q. Now they are the same movement.
        await pickOnCard(page, review, cardA, seeded.shared);
        await pickOnCard(page, review, cardB, seeded.shared);
        for (const index of [indexA, indexB]) {
            await expect(importToggle(reviewRow(review, index))).toHaveAttribute('aria-pressed', 'true');
        }
        await expect(review).toHaveAttribute('data-selected-count', '2');
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});

        const since = await eventSeq(page);
        const [recheck] = await Promise.all([duplicateRecheckOf(page, seeded.brokerId), page.getByTestId('import-wizard-import').click()]);
        await jsonFrom(recheck, 'final duplicate recheck');
        expect(await landedAfter(page, 'review'), 'the recheck found a cross-file group nobody arbitrated: Import goes back to the duplicates step').toBe('duplicates');
        const duplicates = page.getByTestId('import-wizard-step-duplicates');
        await expect(duplicates).toBeVisible();

        // C2, human half — soft, so one run reports both halves of the notification.
        const softly = expect.configure({soft: true});
        await softly(page.getByTestId('toast-warning'), 'E4 (C2): going back to the duplicates step is announced — a warning toast (toast-warning) must be visible').toBeVisible({timeout: 5_000});

        // The group now shown is the new one: A and B, with export A's copy kept by default.
        const groupKey = await groupKeyKeeping(page, duplicates, seeded.description, [
            [indexA, true],
            [indexB, false],
        ]);

        // C2, machine half: the event names the group the user is sent back for.
        await softly
            .poll(async () => (await eventDetailsSince(page, 'tx.import.duplicates.changed', since))[0]?.groups ?? null, {
                message: `E4 (C2): the event tx.import.duplicates.changed reports the new group — detail.groups = [{key: "${groupKey}", memberIndices: [${indexA}, ${indexB}]}]`,
                timeout: 5_000,
            })
            .toEqual([{key: groupKey, memberIndices: [indexA, indexB]}]);

        // Continuing from there imports the group's default keeper alone — before C2 and after it.
        const reviewAgain = await continueToReview(page);
        const keeper = reviewRow(reviewAgain, indexA);
        await expect(keeper).toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(keeper)).toHaveAttribute('aria-pressed', 'true');
        await expect(reviewRow(reviewAgain, indexB), "export B's copy is resolved away").toHaveCount(0);
        await expect(reviewAgain).toHaveAttribute('data-selected-count', '1');

        const staged = stagedBatchWith(page, seeded.description);
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});
        await page.getByTestId('import-wizard-import').click();
        await expectHandedToBulkEditor(page);
        expect(stagedCreates(await staged), 'one copy of the movement — the default keeper — is staged, on the shared asset').toEqual([expect.objectContaining({broker_id: seeded.brokerId, asset_id: seeded.shared.id, description: seeded.description})]);

        await discardBulkEditor(page, seeded.brokerId);
    });

    test('E6: re-binding an arbitrated group to another asset at review turns its copies into database duplicates — Import goes back, announced, the new default keeps no copy, and only the deposit is imported', async ({page, owned}) => {
        const seeded = await seedRebindExports(page, owned);
        // Every duplicate recheck posted for the owned broker, so the second Import can be shown to add none.
        let rechecks = 0;
        page.on('request', (request) => {
            if (request.method() === 'POST' && new URL(request.url()).pathname === `${API}/brokers/import/duplicates` && request.postDataJSON()?.broker_id === seeded.brokerId) rechecks++;
        });
        await openWizardFromTransactionsPage(page);
        const [parsedA, parsedB] = await selectAndParseFiles(page, [
            {fileId: seeded.fileA, label: 'export A'},
            {fileId: seeded.fileB, label: 'export B'},
        ]);
        const twinRowA = rowIndexOf(parsedA, seeded.twinDescription, 'export A');
        const twinRowB = rowIndexOf(parsedB, seeded.twinDescription, 'export B');
        const depositRow = rowIndexOf(parsedA, seeded.depositDescription, 'export A');
        // Merged indices (the review's data-row-id): file by file in selection order, then response order.
        const twinIndexA = twinRowA;
        const twinIndexB = parsedA.transactions.length + twinRowB;
        const depositIndex = depositRow;

        // Preconditions: T auto-resolves to P in both exports (Q holds none of its codes), so the backend
        // scopes T's database match to P and the committed twin — bound to Q — does not collide: at parse
        // T is unique. So is the deposit.
        for (const [parsed, row, label] of [
            [parsedA, twinRowA, 'export A'],
            [parsedB, twinRowB, 'export B'],
        ] as const) {
            expect(mappingOfRow(parsed, row)?.selected_asset_id, `${label}: T auto-resolves to P`).toBe(seeded.primary.id);
        }
        for (const [parsed, rows, label] of [
            [parsedA, [twinRowA, depositRow], 'export A'],
            [parsedB, [twinRowB], 'export B'],
        ] as const) {
            const collisions = [...parsedDuplicates(parsed, 'tx_likely_duplicates'), ...parsedDuplicates(parsed, 'tx_possible_duplicates')].map((entry) => entry.tx_row_index);
            for (const row of rows) expect(collisions, `${label}: row ${row} collides with nothing in the database at parse`).not.toContain(row);
        }

        // The duplicates step: keep BOTH copies of T.
        const duplicates = await walkToDuplicates(page, parseWarned([parsedA, parsedB]));
        await keepEveryCopy(page, duplicates, seeded.twinDescription, twinIndexA, twinIndexB);

        // Review: both copies and the deposit selected; T's card bound to P.
        const review = await continueToReview(page);
        for (const index of [twinIndexA, twinIndexB, depositIndex]) {
            const row = reviewRow(review, index);
            await expect(row, `row ${index} is listed`).toBeVisible({timeout: UI_TIMEOUT});
            await expect(importToggle(row), `row ${index} is selected (aria-pressed=true)`).toHaveAttribute('aria-pressed', 'true');
        }
        await expect(review).toHaveAttribute('data-selected-count', '3');
        const card = boundCard(review, seeded.twinIsin);
        await expect(card).toBeVisible();
        await expect(card.getByTestId('asset-select').getByRole('combobox'), "T's card is bound to P").toContainText(seeded.primary.ticker, {timeout: UI_TIMEOUT});

        // The change at review: re-bind T from P to Q. Q lacks T's ISIN, so the add-identifier prompt
        // opens; decline the code and keep the binding.
        await pickOnCard(page, review, card, seeded.target, 'skip');
        await expect(review).toHaveAttribute('data-selected-count', '3');
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});

        // Import. The re-bind invalidated the verdict, so Import rechecks — now scoped to Q, where the twin lives.
        const since = await eventSeq(page);
        const [recheck] = await Promise.all([duplicateRecheckOf(page, seeded.brokerId), page.getByTestId('import-wizard-import').click()]);
        const report = await jsonFrom<{tx_likely_duplicates?: DuplicateEntry[]}>(recheck, 'final duplicate recheck');
        const asked = (recheck.request().postDataJSON() as {transactions?: StagedCreate[]} | null)?.transactions ?? [];
        const askedTwins = asked.flatMap((row, index) => (row.description === seeded.twinDescription ? [index] : []));
        expect(
            askedTwins.map((index) => asked[index].asset_id),
            'the recheck asks about both copies of T, on Q',
        ).toEqual([seeded.target.id, seeded.target.id]);
        expect(
            (report.tx_likely_duplicates ?? [])
                .filter((entry) => entry.tx_existing_matches?.some((match) => match.existing_tx_id === seeded.committedBuyId))
                .map((entry) => entry.tx_row_index)
                .sort((a, b) => a - b),
            'the recheck reports both copies of T as likely duplicates of the committed twin',
        ).toEqual(askedTwins);

        // C2 status clause: same members, but the arbitrated copies now collide — back to the duplicates step, and said so.
        expect(await landedAfter(page, 'review'), 'the arbitrated group changed its verdicts: Import goes back to the duplicates step').toBe('duplicates');
        const duplicatesAgain = page.getByTestId('import-wizard-step-duplicates');
        await expect(duplicatesAgain).toBeVisible();
        await expect(page.getByTestId('toast-warning'), 'going back is announced with a warning toast').toBeVisible();
        const changed = await waitForEvent(page, 'tx.import.duplicates.changed', {since, timeout: UI_TIMEOUT});

        // The new default keeps NO copy of T: both collide with the committed twin.
        const groupKey = await groupKeyKeeping(page, duplicatesAgain, seeded.twinDescription, [
            [twinIndexA, false],
            [twinIndexB, false],
        ]);
        expect(changed.detail?.groups, "the event names T's group, with both copies").toContainEqual({key: groupKey, memberIndices: [twinIndexA, twinIndexB]});

        // Review: T's display copy (export A) listed and deselected, the other resolved away; the deposit still selected.
        const reviewAgain = await continueToReview(page);
        const display = reviewRow(reviewAgain, twinIndexA);
        await expect(display, "T's display copy (export A) is listed").toBeVisible({timeout: UI_TIMEOUT});
        await expect(importToggle(display), "T's display copy arrives deselected (aria-pressed=false)").toHaveAttribute('aria-pressed', 'false');
        await expect(reviewRow(reviewAgain, twinIndexB), "export B's copy of T is resolved away").toHaveCount(0);
        await expect(importToggle(reviewRow(reviewAgain, depositIndex)), 'the deposit stays selected').toHaveAttribute('aria-pressed', 'true');
        await expect(reviewAgain).toHaveAttribute('data-selected-count', '1');

        // Import again: the recheck is done, so this one goes straight to the bulk editor.
        const rechecksBefore = rechecks;
        const staged = stagedBatchWith(page, seeded.depositDescription);
        await expect(page.getByTestId('import-wizard-import')).toBeEnabled({timeout: UI_TIMEOUT});
        await page.getByTestId('import-wizard-import').click();
        await expectHandedToBulkEditor(page);
        expect(rechecks, 'the second Import posts no further duplicate recheck').toBe(rechecksBefore);
        const creates = stagedCreates(await staged);
        expect(creates, 'the deposit alone is staged').toEqual([expect.objectContaining({broker_id: seeded.brokerId, type: 'DEPOSIT', description: seeded.depositDescription})]);
        expect(
            creates.filter((row) => row.description === seeded.twinDescription),
            'no copy of T is staged',
        ).toEqual([]);

        await discardBulkEditor(page, seeded.brokerId, seeded.committedIds);
    });
});
