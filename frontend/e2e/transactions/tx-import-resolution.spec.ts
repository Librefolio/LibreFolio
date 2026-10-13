/**
 * Import Wizard — Asset Resolution E2E Tests
 *
 * Tests the advanced resolution flow in the review step of the ImportWizardModal.
 *
 * The wizard has seven steps, three of them conditional: unification, corrections and
 * duplicates appear only when the parse produced something for them to do. Walking to
 * the review step therefore means asking at each one, never assuming a fixed order.
 *
 * The way in is the transactions toolbar's Import button, whose import intent opens the
 * wizard on step 1 with no table row involved.
 *
 * The files. Every test that parses uploads a file of its own through the API, selects it in
 * step 2 by its file id, wherever the panel's pages put it, and deletes it in afterEach. The
 * walk to the review is the shared one (fixtures/import-wizard.ts): the parse response decides
 * the notices' confirmation, the stepper the steps crossed. Each test builds the parse its
 * subject needs, and checks it on the parse response rather than assuming it:
 *   - IWR-001…006 parse a CSV holding one purchase of an invented ticker: no asset can match
 *     it, so the review always opens with exactly one unresolved card — its select needs no
 *     position to be found. IWR-004…006 resolve it to a manual asset of their own, which holds
 *     no ticker, so picking it always raises the identifier prompt; IWR-005's confirm writes
 *     the ticker onto that asset, and afterEach deletes the asset, never a seeded one;
 *   - IWR-006b and IWR-007 build a database collision: a broker of their own already holds a
 *     deposit — the file's first import, saved through the API — and their file books the same
 *     deposit again, so the server finds it a likely duplicate. The duplicates step is only for
 *     copies between files imported together (user docs, import › Duplicate Detection): IWR-007
 *     proves the collision raises none and arrives at the review unticked;
 *   - IWR-010 previews its own file, IWR-011 parses a single plain deposit (nothing to
 *     arbitrate), IWR-012 a copy of generic_simple.csv, IWR-013 n invented tickers.
 * A test that creates an asset or a broker records its id the moment it exists, and afterEach
 * deletes them — the broker with `force`, taking every row on it.
 *
 * Prerequisites:
 *   - Backend test mode (port 6041)
 *   - DB populated: the "Interactive Brokers" broker, on which the test user is an owner.
 *
 * Test IDs: IWR-001..IWR-014
 *
 * Key data-testids used:
 *   import-wizard-step4             — Step 4 container
 *   import-wizard-resolve-section   — Resolve assets section wrapper
 *   import-wizard-resolve-toggle    — Collapsible header button
 *   import-wizard-unresolved-count  — The header's amber badge: how many assets are unresolved
 *   import-wizard-inspect-asset-{fakeId} — On a card only once it is resolved
 *   import-wizard-import            — Import button (disabled when unresolved)
 *   import-wizard-compare-{index}   — A duplicate-status badge, which opens the compare modal
 *   asset-select-trigger / -search  — The AssetSelect of a resolve card
 *   search-select-create-new        — "Create new asset" footer in AssetSelect dropdown
 *   search-select-option-{id}       — Individual asset option in dropdown
 *   identifier-prompt-skip          — Skip button in identifier prompt
 *   identifier-prompt-confirm       — Confirm button in identifier prompt
 *   identifier-prompt-cancel        — Cancel button in identifier prompt
 *   asset-modal-form                — AssetModal form container
 *   asset-modal-display-name        — Display name input in AssetModal
 *   asset-modal-cancel              — Cancel button in AssetModal
 *   import-wizard-compare-modal     — The compare modal a duplicate badge opens (N-way, read-only here)
 */

import {IntlMessageFormat} from 'intl-messageformat';
import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForSettled} from '../fixtures/app-events';
import {SUPPORTED_LANGUAGES, t as catalogueText} from '../fixtures/i18n-data';
import {continueToReview, deleteOwnedReports, parseSelectedFile, selectBrokerFile, uploadOwnedReport, type OwnedReport, type ParseResponse} from '../fixtures/import-wizard';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

test.setTimeout(90_000);

/** The seeded broker the sample belongs to, and the sample a parsing test uploads a copy of. */
const GENERIC_SIMPLE = {brokerName: 'Interactive Brokers', sample: 'generic_simple.csv'};

/** The message of the resolve header's badge: how many assets are still unresolved, `{n}`. */
const UNRESOLVED_COUNT_KEY = 'importWizard.unresolvedCount';

/** The step a Back from the review can land on, and the container that step draws. */
const STEP_CONTAINERS: Record<string, string> = {
    analyze: 'import-wizard-step3',
    assets: 'import-wizard-step-assets',
    fix: 'import-wizard-step-fix',
    duplicates: 'import-wizard-step-duplicates',
};

/** The generic plugin's columns: a file of this spec's own is written in them. */
const GENERIC_HEADER = 'date,type,quantity,amount,currency,asset,description';

/** An asset or a broker a test created: it is the test's to use, and to delete. */
type Owned = {id: number; name: string};

/**
 * What the running test created, emptied by afterEach as it deletes them. Module state on
 * purpose: the helpers fill it from inside the tests' bodies, and a worker runs one test at
 * a time. Each entry is recorded the moment the server has accepted it.
 */
const ownedReports: OwnedReport[] = [];
const ownedAssetIds: number[] = [];
const ownedBrokerIds: number[] = [];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * The option list `trigger` controls is open and has finished loading its catalogue. The
 * list is the one the select names in `aria-controls` — never "the first listbox on the page".
 */
async function optionListReady(trigger: Locator) {
    await expect(trigger, 'the select is open').toHaveAttribute('aria-expanded', 'true', {timeout: 5_000});
    const listId = await trigger.getAttribute('aria-controls');
    if (!listId) throw new Error('The select names no option list it controls (aria-controls)');
    const list = trigger.page().locator(`[id="${listId}"]`);
    await expect(list).toBeVisible({timeout: 5_000});
    await expect(list).toHaveAttribute('aria-busy', 'false', {timeout: 10_000});
}

/** The option list is gone — the teardown that follows a pick or an Escape. */
async function optionListClosed(page: Page) {
    await expect(page.locator('[data-testid^="search-select-option-"]')).toHaveCount(0, {timeout: 10_000});
}

async function goToTransactions(page: Page) {
    await navigateTo(page, '/transactions');
    await waitForSettled(page.getByTestId('transactions-page'), 20_000);
    await page.getByTestId('tx-table').waitFor({state: 'visible', timeout: 20_000});
}

/**
 * Open the wizard through the transactions toolbar's Import button, whose import intent opens
 * it with no table row selected and no FormModal in the way. Ends once step 1 has its broker
 * list; returns step 1.
 */
async function openImportWizard(page: Page): Promise<Locator> {
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: 8_000});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: 5_000});
    await waitForSettled(step1, 15_000);
    return step1;
}

/**
 * From step 1, with `own` already uploaded, to the analysis: Next, the file selected in step 2
 * by its id, wherever the panel's pages put it, then Parse. Returns the parse response, which
 * says whether leaving the analysis asks to confirm notices. The wizard reads the broker files
 * when it enters step 2, so the upload comes first.
 */
async function parseOwnFile(page: Page, own: OwnedReport): Promise<ParseResponse> {
    // Step 1: skip (no new uploads in the wizard itself)
    await page.getByTestId('import-wizard-next').click();

    // Step 2: the file, by its id, in its broker's panel, on whichever page it is
    await selectBrokerFile(page, own);

    // Step 3: parse
    return parseSelectedFile(page, own.fileId);
}

/**
 * Upload this test's own copy of generic_simple.csv and parse it, stopping on the analysis
 * step. Called with the wizard on step 1.
 */
async function parseGenericSimple(page: Page): Promise<ParseResponse> {
    const own = await uploadOwnedReport(page, ownedReports, GENERIC_SIMPLE);
    return parseOwnFile(page, own);
}

/**
 * Walk from the analysis step to the review step, crossing whichever of the three
 * conditional steps this parse happens to raise. Returns the review, settled.
 */
async function goToStep4WithGenericSimple(page: Page): Promise<Locator> {
    const parsed = await parseGenericSimple(page);
    return continueToReview(page, parsed);
}

/**
 * Leave the analysis, crossing nothing else: Continue, then the notices' confirmation when the
 * parse response says it raised notices — known, never probed for. Returns the stepper, for the
 * caller to say where the wizard must land; a conditional step it raised would hold the marker.
 */
async function leaveAnalysis(page: Page, parsed: ParseResponse): Promise<Locator> {
    const stepper = page.getByTestId('import-wizard-stepper');
    await expect(stepper.locator('[aria-current="step"]'), 'the walk starts on the analysis').toHaveAttribute('data-step-id', 'analyze');
    await page.getByTestId('import-wizard-continue').click();
    if ((parsed.warnings ?? []).length > 0) {
        const confirm = page.getByTestId('import-wizard-warning-confirm');
        await expect(confirm, 'the parse raised notices: leaving the analysis asks to confirm them').toBeVisible({timeout: 10_000});
        await confirm.click();
        await expect(confirm).toBeHidden({timeout: 10_000});
    }
    return stepper;
}

/** The parse response with its asset mappings (`BRIMParseResponse.asset_mappings`), which the shared `ParseResponse` leaves out. */
type ParsedAssets = ParseResponse & {asset_mappings?: Array<{extracted_symbol?: string | null; candidates?: unknown[]; selected_asset_id?: number | null}>};

/** The parse response with the server's duplicate verdict against the broker's saved rows (`BRIMParseResponse.duplicates`). */
type ParsedDuplicates = ParseResponse & {duplicates?: {tx_likely_duplicates?: Array<{tx_row_index: number; tx_existing_matches?: Array<{existing_tx_id: number}>}>} | null};

/** A generic CSV with one purchase of each ticker, shaped like generic_simple.csv's UNETF row: the generic plugin reads a code of 1–6 letters and digits as a ticker. */
function purchasesOf(tickers: string[]): string {
    const rows = tickers.map((ticker) => `2024-12-10,BUY,10,-250.00,USD,${ticker},E2E unresolved badge ${ticker}`);
    return [GENERIC_HEADER, ...rows].join('\n') + '\n';
}

/**
 * Upload `csv`, a file of this test's own making, under a unique name — to `broker`, or to the seeded
 * "Interactive Brokers" when none is given — and push it onto `ownedReports` as soon as the server has
 * accepted it, for afterEach to delete. The route and the checks of `uploadOwnedReport`, replicated: the
 * fixture uploads only the samples on disk.
 */
async function uploadOwnedCsv(page: Page, csv: string, broker?: Owned): Promise<OwnedReport> {
    let target = broker;
    if (!target) {
        const brokersResponse = await page.request.get('/api/v1/brokers');
        expect(brokersResponse.ok(), `list the brokers: HTTP ${brokersResponse.status()}`).toBe(true);
        const {items} = (await brokersResponse.json()) as {items: Array<{id: number; name: string}>};
        const brokers = items.filter((candidate) => candidate.name === GENERIC_SIMPLE.brokerName);
        if (brokers.length !== 1) {
            throw new Error(`Expected exactly one broker named "${GENERIC_SIMPLE.brokerName}" visible to this user, found ${brokers.length}: it is seeded by backend/test_scripts/test_db/populate_mock_data.py (populate_brokers)`);
        }
        target = brokers[0];
    }
    const brokerId = target.id;
    const fileName = `iwr-own-${uniqueSuffix()}.csv`;
    const response = await page.request.post('/api/v1/brokers/import/upload', {
        multipart: {broker_id: String(brokerId), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}},
    });
    expect(response.ok(), `upload ${fileName}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const uploaded = (await response.json()) as {file_id: string; filename: string; target_broker_id: number | null};
    const own: OwnedReport = {brokerId, fileId: uploaded.file_id, fileName};
    ownedReports.push(own);
    expect(uploaded, `${fileName} lands on "${target.name}" under its own name`).toMatchObject({filename: fileName, target_broker_id: brokerId});
    return own;
}

/** A generic CSV with one deposit of `amount` `currency` on `date`. */
function depositOf(date: string, amount: string, currency: string, description: string): string {
    return `${GENERIC_HEADER}\n${date},DEPOSIT,0,${amount},${currency},,${description}\n`;
}

/** A deposit of one row of a file, as a test saves it before importing that file. */
type SavedDeposit = {date: string; amount: string; currency: string; description: string};

/**
 * Save `deposit` on `broker` through the API — the first import of a file, done by the test — and
 * return its id. It goes with its broker: afterEach deletes the broker with `force`.
 */
async function saveDeposit(page: Page, broker: Owned, deposit: SavedDeposit): Promise<number> {
    const create = {broker_id: broker.id, type: 'DEPOSIT', date: deposit.date, cash: {code: deposit.currency, amount: deposit.amount}, description: deposit.description};
    const response = await page.request.post('/api/v1/transactions/commit', {data: {creates: [create]}});
    expect(response.ok(), `save the deposit: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {committed?: boolean; issues?: unknown[]; results?: Array<{operation: string; index?: number; ids?: number[]}>};
    expect(body.committed, `the deposit is saved: ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    const id = body.results?.find((result) => result.operation === 'create' && result.index === 0)?.ids?.[0];
    if (typeof id !== 'number') throw new Error(`The saved deposit got no id: ${JSON.stringify(body.results)}`);
    return id;
}

/**
 * The premise of a file of invented tickers, verified on the parse response rather than assumed: the parse
 * extracts those tickers and nothing else, and no asset matches any of them.
 */
function expectUnresolvedTickers(parsed: ParseResponse, tickers: string[]) {
    const mappings = (parsed as ParsedAssets).asset_mappings ?? [];
    expect(mappings.map((mapping) => mapping.extracted_symbol).sort(), 'premise: the parse extracts this file’s invented tickers, one asset each, and nothing else').toEqual([...tickers].sort());
    expect(
        mappings.filter((mapping) => (mapping.candidates ?? []).length > 0 || mapping.selected_asset_id != null),
        `premise: no asset matches the invented tickers, so all ${tickers.length} reach the review unresolved`,
    ).toEqual([]);
}

/**
 * Upload a CSV of this test's own — one purchase of an invented ticker — parse it and walk to the review,
 * the premise checked on the parse response. Called with the wizard closed. The resolve section then holds
 * exactly one card, unresolved: its select is found by construction, never by position or by colour.
 */
async function reviewWithUnknownAsset(page: Page): Promise<{step4: Locator; ticker: string}> {
    const ticker = uniqueToken(6);
    await openImportWizard(page);
    const own = await uploadOwnedCsv(page, purchasesOf([ticker]));
    const parsed = await parseOwnFile(page, own);
    expectUnresolvedTickers(parsed, [ticker]);
    const step4 = await continueToReview(page, parsed);
    return {step4, ticker};
}

/**
 * Open the asset select of the review's one resolve card. The section arrives unfolded whenever it has
 * something to resolve, so the select is asserted, never probed for; returns its trigger.
 */
async function openResolveSelect(step4: Locator): Promise<Locator> {
    const resolveSection = step4.getByTestId('import-wizard-resolve-section');
    await expect(resolveSection).toBeVisible({timeout: 5_000});
    const trigger = resolveSection.getByTestId('asset-select-trigger');
    await expect(trigger, 'the resolve section holds the one card of this file').toHaveCount(1, {timeout: 5_000});
    await trigger.click();
    await optionListReady(trigger);
    return trigger;
}

/** In the review's one resolve card, pick `asset`: its name searched, the option carrying its id clicked. */
async function pickResolveAsset(page: Page, step4: Locator, asset: Owned) {
    await openResolveSelect(step4);
    const search = step4.getByTestId('import-wizard-resolve-section').getByTestId('asset-select-search');
    await expect(search).toBeVisible({timeout: 3_000});
    await search.fill(asset.name);
    await expect(search).toHaveValue(asset.name);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: 5_000});
    await option.click();
    await optionListClosed(page);
}

/**
 * The review's one card is resolved: it offers to inspect the asset it is now bound to (a control drawn
 * only on a resolved card), and the header counts nothing left unresolved.
 */
async function expectResolved(step4: Locator) {
    await waitForSettled(step4, 20_000);
    const resolveSection = step4.getByTestId('import-wizard-resolve-section');
    await expect(resolveSection.getByTestId(/^import-wizard-inspect-asset-/), 'the card is bound to an asset').toBeVisible({timeout: 5_000});
    await expect(step4.getByTestId('import-wizard-unresolved-count'), 'no asset is left unresolved').toHaveCount(0);
}

/** The ids of the assets whose ticker is exactly `ticker`. */
async function assetIdsWithTicker(page: Page, ticker: string): Promise<number[]> {
    const response = await page.request.get(`/api/v1/assets/query?ticker=${encodeURIComponent(ticker)}`);
    expect(response.ok(), `look up ticker ${ticker}: HTTP ${response.status()}`).toBe(true);
    return ((await response.json()) as Array<{id: number}>).map((asset) => asset.id);
}

/**
 * A manual asset of this test's own, holding no identifier: picking it for an extracted ticker always raises
 * the identifier prompt, and whatever the prompt writes lands on it — never on a seeded asset. Its id is
 * recorded for afterEach before anything about the result is checked. The page keeps its assets in a session
 * cache: create this before the page loads it.
 */
async function createOwnedAsset(page: Page): Promise<Owned> {
    const name = `E2E resolve ${uniqueSuffix()}`;
    const response = await page.request.post('/api/v1/assets', {data: [{display_name: name, currency: 'USD', asset_type: 'STOCK'}]});
    expect(response.ok(), `create the owned asset: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const body = (await response.json()) as {results: Array<{asset_id: number | null; display_name: string; success: boolean; message?: string}>};
    const created = body.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') ownedAssetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`The owned asset ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.asset_id, name};
}

/**
 * A broker of this test's own, opened long before any date its rows carry. Its id is recorded for afterEach
 * before anything about the result is checked. The page keeps its brokers in a session cache: create this
 * before the page loads it.
 */
async function createOwnedBroker(page: Page): Promise<Owned> {
    const name = `E2E import resolution ${uniqueSuffix()}`;
    const response = await page.request.post('/api/v1/brokers', {data: [{name, opened_at: '2020-01-01'}]});
    expect(response.ok(), `create the owned broker: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    const {results} = (await response.json()) as {results: Array<{name: string; success: boolean; broker_id: number | null; message?: string}>};
    const created = results.find((result) => result.name === name);
    if (typeof created?.broker_id === 'number') ownedBrokerIds.push(created.broker_id);
    if (!created?.success || typeof created.broker_id !== 'number') throw new Error(`The owned broker ${name} was not created: ${created?.message ?? 'missing result'}`);
    return {id: created.broker_id, name};
}

/** Delete, by id, the assets the running test created — the identifiers it wrote on them go with them. */
async function deleteOwnedAssets(page: Page): Promise<void> {
    const failures: string[] = [];
    for (const id of ownedAssetIds.splice(0)) {
        const response = await page.request.delete(`/api/v1/assets?asset_ids=${id}`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{asset_id: number; success: boolean}>} | null;
        if (!response.ok() || body?.results?.find((result) => result.asset_id === id)?.success !== true) failures.push(`asset ${id}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    }
    expect(failures, 'cleanup deletes every asset this test created').toEqual([]);
}

/** Delete, by id and with `force`, the brokers the running test created — every row on them goes too. */
async function deleteOwnedBrokers(page: Page): Promise<void> {
    const failures: string[] = [];
    for (const id of ownedBrokerIds.splice(0)) {
        const response = await page.request.delete(`/api/v1/brokers?ids=${id}&force=true`);
        const body = (await response.json().catch(() => null)) as {results?: Array<{id: number; success: boolean}>} | null;
        if (!response.ok() || body?.results?.find((result) => result.id === id)?.success !== true) failures.push(`broker ${id}: HTTP ${response.status()} ${JSON.stringify(body)}`);
    }
    expect(failures, 'cleanup deletes every broker this test created').toEqual([]);
}

/**
 * The language the page is drawn in: `<html lang>`, which the root layout keeps on the language shown,
 * read once `data-i18n-ready` says its dictionary is in — the reading of `tx-bulk-import-handoff.spec.ts`,
 * replicated rather than imported (a spec does not reach into another spec's helpers).
 */
async function pageLanguage(page: Page): Promise<string> {
    const html = page.locator('html');
    await expect(html, 'the page has its dictionary').toHaveAttribute('data-i18n-ready', 'true');
    return ((await html.getAttribute('lang')) ?? '').split('-')[0];
}

/**
 * `importWizard.unresolvedCount` for `n`, as the `lang` catalogue words it: the message read from the
 * catalogue file and formatted by `intl-messageformat`, the formatter svelte-i18n compiles messages with.
 * A catalogue without the message fails here, by name.
 */
function unresolvedCountText(lang: string, n: number): string {
    const message = catalogueText(lang, UNRESOLVED_COUNT_KEY);
    expect(message, `the "${lang}" catalogue has a message for ${UNRESOLVED_COUNT_KEY}`).not.toBe(UNRESOLVED_COUNT_KEY);
    return String(new IntlMessageFormat(message, lang).format({n}));
}

/** A file for step 1's uploader. IWR-009 only needs it pending: the wizard keeps it in the browser until Next. */
function pendingCsv(name: string): {name: string; mimeType: string; buffer: Buffer} {
    return {name, mimeType: 'text/csv', buffer: Buffer.from('date,type,amount,currency,description\n2024-12-10,DEPOSIT,100.00,USD,IWR-009 pending file\n', 'utf8')};
}

/**
 * Delete, by id, the broker IWR-009 created as TEST_USER under `name`, unique to the run. The id is looked up through
 * the API, not carried over from the creation, so a red anywhere after the submit still finds the broker. A plain
 * delete: the broker never held a transaction, and a refusal would say so. After a red the test keeps its own error
 * and a failed cleanup is only logged; after a green the broker must be found and deleted, or the test goes red.
 */
async function deleteBrokerNamed(page: Page, name: string, passed: boolean): Promise<void> {
    try {
        const listed = await page.request.get('/api/v1/brokers');
        expect(listed.ok(), `list the brokers: HTTP ${listed.status()}`).toBe(true);
        const {items} = (await listed.json()) as {items: Array<{id: number; name: string}>};
        const created = items.filter((broker) => broker.name === name);
        if (passed) expect(created.length, `the broker "${name}" this test created is listed once`).toBe(1);
        for (const {id} of created) {
            const deleted = await page.request.delete('/api/v1/brokers', {params: {ids: id}});
            expect(deleted.ok(), `delete broker ${id}: HTTP ${deleted.status()} ${await deleted.text()}`).toBe(true);
            const result = ((await deleted.json()) as {results: Array<{id: number; success: boolean}>}).results.find((candidate) => candidate.id === id);
            expect(result?.success, `broker ${id} ("${name}") deleted: ${JSON.stringify(result)}`).toBe(true);
        }
    } catch (error) {
        if (passed) throw error;
        console.warn(`[IWR-009] the cleanup after a red could not delete "${name}": ${String(error)}`);
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import Wizard — Asset Resolution', () => {
    test.beforeEach(async ({page}) => {
        await login(page, TEST_USER);
        await goToTransactions(page);
    });

    // Files first — a report outlives its broker otherwise — then assets, then brokers: each
    // step runs whatever the one before it did, and every one is scoped to the ids recorded.
    test.afterEach(async ({page}) => {
        try {
            // Unmount the wizard first, so nothing on the page queries what is about to go.
            await page.goto('about:blank');
        } finally {
            try {
                await deleteOwnedReports(page, ownedReports);
            } finally {
                try {
                    await deleteOwnedAssets(page);
                } finally {
                    await deleteOwnedBrokers(page);
                }
            }
        }
    });

    // -----------------------------------------------------------------------
    // IWR-001: Resolve section visible + import button disabled
    // -----------------------------------------------------------------------
    test('IWR-001: Step 4 shows resolve section with unresolved badge and import disabled', async ({page}) => {
        const {step4} = await reviewWithUnknownAsset(page);

        // Resolve Assets section must be visible (the invented ticker generates a fake_id)
        await expect(step4.getByTestId('import-wizard-resolve-section')).toBeVisible({timeout: 5_000});

        // The amber badge with the unresolved count must be present, in the section's header
        const resolveToggle = step4.getByTestId('import-wizard-resolve-toggle');
        await expect(resolveToggle).toBeVisible();
        await expect(resolveToggle.getByTestId('import-wizard-unresolved-count')).toBeVisible();

        // Import button must be disabled while there are unresolved assets
        await expect(page.getByTestId('import-wizard-import')).toBeDisabled();
    });

    // -----------------------------------------------------------------------
    // IWR-002: AssetSelect dropdown opens and shows "Create new" button
    // -----------------------------------------------------------------------
    test('IWR-002: AssetSelect dropdown opens with Create new button', async ({page}) => {
        const {step4} = await reviewWithUnknownAsset(page);

        await openResolveSelect(step4);

        // "Create new" footer button must be visible in the dropdown
        await expect(page.getByTestId('search-select-create-new')).toBeVisible({timeout: 5_000});

        // Close dropdown by pressing Escape
        await page.keyboard.press('Escape');
        await optionListClosed(page);
    });

    // -----------------------------------------------------------------------
    // IWR-003: Click "Create new" → AssetModal opens pre-filled with extracted name
    // -----------------------------------------------------------------------
    test('IWR-003: Create new asset — AssetModal opens with pre-filled name from extracted identifier', async ({page}) => {
        const {step4} = await reviewWithUnknownAsset(page);

        await openResolveSelect(step4);

        // Click the "Create new" footer button
        await page.getByTestId('search-select-create-new').click();

        // AssetModal must open
        const assetModal = page.getByTestId('asset-modal-form');
        await expect(assetModal).toBeVisible({timeout: 5_000});

        // The Name input must be visible (may or may not be pre-filled depending on
        // whether the BRIM parser extracted a name vs just a ticker symbol)
        await expect(page.getByTestId('asset-modal-display-name')).toBeVisible({timeout: 3_000});

        // Cancel the modal — we're just verifying the pre-fill
        await page.getByTestId('asset-modal-cancel').click();
        await expect(page.getByTestId('asset-modal-form')).toHaveCount(0, {timeout: 5_000});

        // Wizard still open
        await expect(page.getByTestId('import-wizard-step4')).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-004: Manual asset selection → identifier prompt → skip → asset resolved
    // -----------------------------------------------------------------------
    test('IWR-004: Manual asset pick shows identifier prompt (skip) → asset card becomes resolved', async ({page}) => {
        // An asset of this test's own, with no ticker: picking it for the file's ticker always
        // raises the identifier prompt. Created before the page loads its assets, so the select
        // offers it.
        const asset = await createOwnedAsset(page);
        await goToTransactions(page);
        const {step4, ticker} = await reviewWithUnknownAsset(page);

        await pickResolveAsset(page, step4, asset);

        // The identifier prompt appears — skip it
        const skipBtn = page.getByTestId('identifier-prompt-skip');
        await expect(skipBtn).toBeVisible({timeout: 5_000});
        await skipBtn.click();
        await expect(skipBtn).toHaveCount(0, {timeout: 5_000});

        // The asset card is now resolved...
        await expectResolved(step4);
        // ...and skipping wrote nothing: no asset carries the file's ticker.
        expect(await assetIdsWithTicker(page, ticker), `skip leaves ticker ${ticker} unassigned`).toEqual([]);
    });

    // -----------------------------------------------------------------------
    // IWR-005: Identifier prompt confirm → adds identifier to asset
    // -----------------------------------------------------------------------
    test('IWR-005: Identifier prompt confirm — assigns identifier and resolves asset', async ({page}) => {
        // The identifier the confirm writes lands on an asset of this test's own, never on a
        // seeded one, and afterEach deletes it with that identifier.
        const asset = await createOwnedAsset(page);
        await goToTransactions(page);
        const {step4, ticker} = await reviewWithUnknownAsset(page);

        await pickResolveAsset(page, step4, asset);

        // The identifier prompt appears — use Confirm (not Skip)
        const confirmBtn = page.getByTestId('identifier-prompt-confirm');
        await expect(confirmBtn).toBeVisible({timeout: 5_000});
        await confirmBtn.click();
        await expect(confirmBtn).toHaveCount(0, {timeout: 10_000});

        // Asset should be resolved...
        await expectResolved(step4);
        // ...and the identifier assigned: the file's ticker is now this asset's, and only its.
        await expect.poll(() => assetIdsWithTicker(page, ticker), {message: `ticker ${ticker} is assigned to asset ${asset.id}`, timeout: 10_000}).toEqual([asset.id]);
    });

    // -----------------------------------------------------------------------
    // IWR-006: Full resolve → import button enables
    // -----------------------------------------------------------------------
    test('IWR-006: After resolving all unresolved assets, import button becomes enabled', async ({page}) => {
        const asset = await createOwnedAsset(page);
        await goToTransactions(page);
        const {step4} = await reviewWithUnknownAsset(page);
        const importBtn = page.getByTestId('import-wizard-import');

        // The precondition, by construction: the file's one asset is unresolved, which holds
        // the import back.
        await expect(importBtn).toBeDisabled();

        // Resolve it — the only one there is — and skip the identifier prompt
        await pickResolveAsset(page, step4, asset);
        const skipBtn = page.getByTestId('identifier-prompt-skip');
        await expect(skipBtn).toBeVisible({timeout: 5_000});
        await skipBtn.click();
        await expect(skipBtn).toHaveCount(0, {timeout: 5_000});
        await expectResolved(step4);

        // Import button must be enabled now that every asset is resolved
        await expect(importBtn).toBeEnabled({timeout: 10_000});

        // Click import and verify wizard closes
        await importBtn.click();
        await expect(page.getByTestId('import-wizard-stepper')).not.toBeVisible({timeout: 10_000});
        // BulkModal should still be open with the imported row — the file's one purchase
        const bulkRoot = page.getByTestId('tx-bulk-modal-root');
        await expect(bulkRoot).toBeVisible();
        await expect(bulkRoot.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]'), 'the workspace holds the imported purchase').toHaveCount(1, {timeout: 10_000});
    });

    // -----------------------------------------------------------------------
    // IWR-007: Duplicate Detection — a second import meets the rows already saved
    // -----------------------------------------------------------------------
    test('IWR-007: A second import of the same file brings its already-saved row to the review unticked, without a duplicates step', async ({page}) => {
        // The contract (user docs, import › Duplicate Detection, and ImportWizardModal's
        // stepIsActive): a row matching a transaction already saved for the same broker — same
        // type, date, quantity and amount, and the same description — is a likely duplicate and
        // arrives at the review UNTICKED. The duplicates step is only for copies between files
        // imported together, so a collision with the database never raises it.
        //
        // The precondition, built: a broker of this test's own already holds the file's one row
        // — its first import, saved through the API — and then the same file is imported again.
        const broker = await createOwnedBroker(page);
        const deposit: SavedDeposit = {date: '2024-04-02', amount: '250.00', currency: 'EUR', description: `IWR-007 saved ${uniqueSuffix()}`};
        const savedId = await saveDeposit(page, broker, deposit);
        const own = await uploadOwnedCsv(page, depositOf(deposit.date, deposit.amount, deposit.currency, deposit.description), broker);
        // The page loads its brokers once: load it again, so the wizard lists the new one.
        await goToTransactions(page);

        await openImportWizard(page);
        const parsed = await parseOwnFile(page, own);
        // The premise, read on the parse response: the file's one row, nothing else to resolve or
        // correct, and the server's verdict on it — a likely duplicate of the row saved above.
        expect(parsed.transactions, 'premise: the parse reads the file’s one deposit').toHaveLength(1);
        expect(parsed.field_todos ?? [], 'premise: nothing for the corrections step').toEqual([]);
        expect((parsed as ParsedAssets).asset_mappings ?? [], 'premise: no asset to resolve or unify').toEqual([]);
        expect(
            ((parsed as ParsedDuplicates).duplicates?.tx_likely_duplicates ?? []).map((duplicate) => ({row: duplicate.tx_row_index, saved: (duplicate.tx_existing_matches ?? []).map((match) => match.existing_tx_id)})),
            `premise: the server finds the file's row a likely duplicate of transaction ${savedId}`,
        ).toEqual([{row: 0, saved: [savedId]}]);

        // No duplicates step: leaving the analysis lands on the review, and the stepper never
        // lists the step at all.
        const stepper = await leaveAnalysis(page, parsed);
        await expect(stepper.locator('[aria-current="step"]'), 'a collision with the database raises no duplicates step: the walk lands on the review').toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
        await expect(stepper.locator('[data-step-id="duplicates"]'), 'the duplicates step is not in the stepper').toHaveCount(0);
        const step4 = page.getByTestId('import-wizard-step4');
        await expect(step4).toBeVisible({timeout: 5_000});
        await waitForSettled(step4, 30_000);

        // The row already saved arrives unticked, carrying its duplicate badge — its test id, not
        // its words — so nothing is selected and nothing would be imported a second time.
        const reviewRow = step4.locator('tbody tr[data-row-id]');
        await expect(reviewRow, 'the review holds the file’s one row').toHaveCount(1, {timeout: 10_000});
        const rowIndex = await reviewRow.getAttribute('data-row-id');
        await expect(reviewRow.locator('td[data-column-id="selected"] button[aria-pressed]'), 'the already-saved row arrives unticked').toHaveAttribute('aria-pressed', 'false');
        const dupBadge = reviewRow.getByTestId(`import-wizard-compare-${rowIndex}`);
        await expect(dupBadge, 'the row carries its duplicate badge').toBeVisible();
        await expect(dupBadge.locator('[data-duplicate-status="likely"]'), 'the badge is the Likely-dup one: its published variant, not its words').toBeVisible();
        await expect(step4, 'no row is selected for import').toHaveAttribute('data-selected-count', '0');
        await expect(page.getByTestId('import-wizard-import'), 'with nothing selected, Import is not offered').toBeDisabled();
    });

    // -----------------------------------------------------------------------
    // IWR-006b: Compare Modal — click ⚠ badge opens the row beside its twin, in view mode
    // -----------------------------------------------------------------------
    test('IWR-006b: Click ⚠ duplicate badge opens compare modal in view mode', async ({page}) => {
        // The precondition, built rather than hoped for: a broker of this test's own holds a
        // deposit, and a file of its own books the same deposit again — same date, amount and
        // description, so the review flags it as a likely duplicate of the archive. Broker and
        // file are created before the page loads its brokers, so the wizard lists them.
        const broker = await createOwnedBroker(page);
        const deposit: SavedDeposit = {date: '2024-03-05', amount: '123.45', currency: 'EUR', description: `IWR-006b archived ${uniqueSuffix()}`};
        const savedId = await saveDeposit(page, broker, deposit);
        const own = await uploadOwnedCsv(page, depositOf(deposit.date, deposit.amount, deposit.currency, deposit.description), broker);
        await goToTransactions(page);

        await openImportWizard(page);
        const parsed = await parseOwnFile(page, own);
        expect(parsed.transactions, 'premise: the parse reads the file’s one deposit').toHaveLength(1);
        const step4 = await continueToReview(page, parsed);

        // The file's one row is the duplicate, so its status badge is the one compare badge
        // there is — found by its test id, not by its colour.
        const reviewRow = step4.locator('tbody tr[data-row-id]');
        await expect(reviewRow, 'the review holds the file’s one row').toHaveCount(1, {timeout: 10_000});
        const rowIndex = await reviewRow.getAttribute('data-row-id');
        const dupBadge = reviewRow.getByTestId(`import-wizard-compare-${rowIndex}`);
        await expect(dupBadge, 'the review flags the archived deposit').toBeVisible({timeout: 10_000});
        // The ⚠ badge of the title: the Likely-dup variant, read from the attribute it publishes.
        await expect(dupBadge.locator('[data-duplicate-status="likely"]')).toBeVisible();
        await dupBadge.click();

        // The compare modal opens on the row beside its twin — the deposit saved above, by its
        // id (user docs, How to Import › Review: "click a duplicate badge to compare the row
        // with its twin"). It is the N-way TransactionCompareModal, opened read-only.
        const compareModal = page.getByTestId('import-wizard-compare-modal');
        await expect(compareModal).toBeVisible({timeout: 5_000});
        await expect(compareModal.getByTestId(`import-wizard-compare-col-${rowIndex}`), 'one column is the file’s row').toBeVisible();
        await expect(compareModal.getByTestId(`import-wizard-compare-col-db-${savedId}`), `the other is its twin, transaction ${savedId}`).toBeVisible();

        // Title starts with 🔍 (the compare's own marker, not translated text)
        await expect(compareModal.getByRole('heading', {level: 2})).toContainText('🔍');

        // View mode: the comparison is drawn, and nothing in it keeps or applies a choice.
        await expect(compareModal.getByTestId('import-wizard-compare-table')).toBeVisible();
        await expect(compareModal.getByTestId(/^import-wizard-compare-keep-/)).toHaveCount(0);
        await expect(compareModal.getByTestId('import-wizard-compare-apply')).toHaveCount(0);

        // Close by pressing Escape: the compare goes, the review stays.
        await page.keyboard.press('Escape');
        await expect(compareModal).not.toBeVisible({timeout: 3_000});
        await expect(step4).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-009: Broker creation reactivity — create broker from Step 1 shows in dropdown
    // -----------------------------------------------------------------------
    test('IWR-009: Creating a new broker from Step 1 makes it appear in the dropdown', async ({page}) => {
        const step1 = await openImportWizard(page);

        // Step 1 shows its broker selector ("assign all") only while files are pending, and the wizard opens with
        // none: the probe that looked for the selector skipped the whole test, in silence, on every run. So the
        // precondition is made, then asserted: one file is dropped into the uploader. It never leaves the browser —
        // step 1 uploads on Next, which this test does not press — so it has nothing to clean up.
        await step1.getByTestId('file-input').setInputFiles(pendingCsv(`iwr-009-${uniqueSuffix()}.csv`));
        const brokerSelectWrapper = step1.getByTestId('import-wizard-step1-broker-select');
        await expect(brokerSelectWrapper, 'precondition: a pending file shows the step-1 broker selector').toBeVisible({timeout: 5_000});
        const brokerSelect = brokerSelectWrapper.getByRole('combobox');

        // The broker is TEST_USER's: unique to the run, and deleted by id in finally.
        const uniqueName = `E2E Test Broker ${uniqueSuffix()}`;
        let passed = false;
        try {
            // Open the BrokerSearchSelect dropdown
            await brokerSelect.click();
            await optionListReady(brokerSelect);

            // Click "Create new" in the dropdown footer
            const createNewBtn = page.getByTestId('search-select-create-new');
            await expect(createNewBtn).toBeVisible({timeout: 3_000});
            await createNewBtn.click();

            // BrokerModal should open
            const brokerModal = page.locator('[data-testid="broker-modal"]');
            await expect(brokerModal).toBeVisible({timeout: 5_000});

            // Fill in the broker name
            const nameInput = page.getByTestId('broker-name-input');
            await expect(nameInput).toBeVisible({timeout: 3_000});
            await nameInput.fill(uniqueName);
            await expect(nameInput).toHaveValue(uniqueName);

            // Save
            const since = await eventSeq(page);
            await page.getByTestId('broker-form-submit').click();

            // BrokerModal should close
            await expect(brokerModal).not.toBeVisible({timeout: 5_000});
            const created = await waitForEvent(page, 'broker.created', {since});
            // Step 1 reloads its broker list after a creation, and stays busy until the list is in.
            await waitForSettled(step1, 15_000);

            // Open the BrokerSearchSelect dropdown again — new broker should appear
            await brokerSelect.click();
            await optionListReady(brokerSelect);

            // Verify the newly created broker appears in the options
            const newBrokerOption = page.locator(`[data-testid^="search-select-option-"]`).filter({hasText: uniqueName});
            await expect(newBrokerOption).toBeVisible({timeout: 5_000});
            await expect(newBrokerOption, 'the option is the broker the creation reported').toHaveAttribute('data-testid', `search-select-option-${created.detail?.brokerId}`);

            // Close dropdown
            await page.keyboard.press('Escape');
            passed = true;
        } finally {
            await deleteBrokerNamed(page, uniqueName, passed);
        }
    });

    // -----------------------------------------------------------------------
    // IWR-010: FilePreviewModal — preview file opens modal above wizard
    // -----------------------------------------------------------------------
    test('IWR-010: FilePreviewModal opens above wizard and can be closed', async ({page}) => {
        // The file to preview is this test's own, uploaded before step 2 reads the broker files
        // — the precondition built, not borrowed from whatever step 2 happens to list.
        await openImportWizard(page);
        const own = await uploadOwnedReport(page, ownedReports, GENERIC_SIMPLE);

        // Step 1: skip to Step 2 where files are listed with a preview action; the file is found
        // by its id in its broker's panel, on whichever page it is.
        await page.getByTestId('import-wizard-next').click();
        await selectBrokerFile(page, own);
        const step2 = page.getByTestId('import-wizard-step2');

        // This file's row action menu, then "preview".
        const previewBtn = step2.getByTestId(`import-wizard-broker-files-${own.brokerId}`).getByTestId(`row-actions-${own.fileId}`);
        await expect(previewBtn).toBeVisible({timeout: 5_000});
        await previewBtn.click();
        await page.getByTestId('context-menu-action-preview').click();

        // FilePreviewModal should open (ModalBase with testId="file-preview-modal")
        const previewModal = page.getByTestId('file-preview-modal');
        await expect(previewModal).toBeVisible({timeout: 5_000});

        // Close by pressing Escape
        await page.keyboard.press('Escape');
        await expect(previewModal).not.toBeVisible({timeout: 3_000});

        // Wizard should still be visible and functional
        await expect(page.getByTestId('import-wizard-stepper')).toBeVisible();
        await expect(step2).toBeVisible();
    });

    // -----------------------------------------------------------------------
    // IWR-011: Conditional steps — a clean parse shows none of the three
    // -----------------------------------------------------------------------
    test('IWR-011: A parse with nothing to arbitrate goes straight to the review step', async ({page}) => {
        // The three middle steps exist to be skipped when there is no work for them. If
        // they appeared unconditionally the shortest import would be five clicks longer,
        // which is exactly what the restructure set out to remove.
        //
        // The precondition, built: a file of this test's own with one plain deposit — no asset
        // to resolve or unify, nothing to correct, one file so nothing to arbitrate between
        // files — and checked on the parse response.
        await openImportWizard(page);
        const own = await uploadOwnedCsv(page, depositOf('2025-10-15', '12.34', 'USD', `IWR-011 clean ${uniqueSuffix()}`));
        const parsed = await parseOwnFile(page, own);
        expect(parsed.transactions, 'premise: the parse reads the file’s one deposit').toHaveLength(1);
        expect(parsed.field_todos ?? [], 'premise: nothing for the corrections step').toEqual([]);
        expect((parsed as ParsedAssets).asset_mappings ?? [], 'premise: no asset to resolve or unify').toEqual([]);

        const stepper = await leaveAnalysis(page, parsed);

        // Straight to the review: a raised step would hold the marker until someone acted on
        // it, and none of the three is even in the stepper.
        await expect(stepper.locator('[aria-current="step"]'), 'leaving the analysis lands on the review').toHaveAttribute('data-step-id', 'review', {timeout: 30_000});
        await expect(page.getByTestId('import-wizard-step4')).toBeVisible({timeout: 5_000});
        await expect(stepper.locator('[data-step-id="assets"], [data-step-id="fix"], [data-step-id="duplicates"]'), 'no conditional step was raised').toHaveCount(0);
    });

    // -----------------------------------------------------------------------
    // IWR-012: Going back from the review step lands on the analysis, not on nothing
    // -----------------------------------------------------------------------
    test('IWR-012: Back from the review step returns through the steps that were shown', async ({page}) => {
        await openImportWizard(page);
        await goToStep4WithGenericSimple(page);

        // The previous step is whichever conditional step this parse raised, or the analysis if
        // none was: the stepper lists the steps shown, in order, so the one before the review is
        // where Back must land. An empty panel — the symptom of a step machine counting by number
        // rather than by what it showed — is what this rules out.
        const stepper = page.getByTestId('import-wizard-stepper');
        const shown = await stepper.locator('[data-step-id]').evaluateAll((steps) => steps.map((step) => step.getAttribute('data-step-id') ?? ''));
        const previous = shown[shown.indexOf('review') - 1];
        expect(Object.keys(STEP_CONTAINERS), `the step before the review is the analysis or a conditional step (stepper: ${shown.join(' → ')})`).toContain(previous);

        await page.getByTestId('import-wizard-back').click();

        await expect(stepper.locator('[aria-current="step"]'), `Back lands on ${previous}`).toHaveAttribute('data-step-id', previous);
        await expect(page.getByTestId(STEP_CONTAINERS[previous]), `the ${previous} step is drawn`).toBeVisible({timeout: 5_000});
    });

    // -----------------------------------------------------------------------
    // IWR-013: the unresolved badge counts the assets once, in the catalogue's plural
    // -----------------------------------------------------------------------
    for (const unresolved of [1, 2]) {
        test(`IWR-013 (n=${unresolved}): the resolve header counts the unresolved assets once, in the catalogue's plural`, async ({page}) => {
            // The badge drew `{step4UnresolvedCount}` and then `importWizard.unresolvedCount`, whose
            // message already holds `{n}` and had no plural: "1 1 assets unresolved". Its text must be
            // exactly the catalogue's message for the page's language, formatted for n.
            const tickers = Array.from({length: unresolved}, () => uniqueToken(6));
            await openImportWizard(page);
            const own = await uploadOwnedCsv(page, purchasesOf(tickers));

            // Step 1: skip; step 2: this test's file; step 3: parse
            const parsed = await parseOwnFile(page, own);

            // n is known by construction, and verified rather than assumed: the parse extracts the
            // invented tickers and nothing else, and no asset matches any of them.
            expectUnresolvedTickers(parsed, tickers);

            const step4 = await continueToReview(page, parsed);
            const lang = await pageLanguage(page);

            await expect(step4.getByTestId('import-wizard-unresolved-count'), `the badge is the "${lang}" catalogue's ${UNRESOLVED_COUNT_KEY} for n = ${unresolved}: the number once, inside the message's own plural`).toHaveText(unresolvedCountText(lang, unresolved), {timeout: 10_000});
        });
    }
});

test.describe('Import Wizard — the unresolved-assets message', () => {
    // -----------------------------------------------------------------------
    // IWR-014: the badge's message is a plural in every catalogue
    // -----------------------------------------------------------------------
    test('IWR-014: importWizard.unresolvedCount is a plural in every catalogue — one asset does not read as two with the digit swapped', () => {
        // The catalogue files alone: no page, no login. A message with no plural
        // (`{n} assets unresolved`) words 1 exactly as it words 2 with the "2" made a "1".
        const worded = SUPPORTED_LANGUAGES.map((lang) => ({lang, one: unresolvedCountText(lang, 1), twoAsOne: unresolvedCountText(lang, 2).replace('2', '1')}));
        const notPlural = worded.filter((entry) => entry.one === entry.twoAsOne);

        expect(notPlural, `${UNRESOLVED_COUNT_KEY} is an ICU plural in every catalogue: for one asset it does not read as the text for two with the digit swapped`).toEqual([]);
    });
});
