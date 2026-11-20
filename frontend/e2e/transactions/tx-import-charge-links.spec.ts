/**
 * Linked charges through the import (project 66, lot P1b; contract `66-P1b-contract.md` §2.5, corrected by §4.4 and §5).
 *
 * A plugin that knows a FEE belongs to a BUY names the BUY `ref` and the FEE `parent_ref` (P1a). The wizard renews the
 * names for each hand-over and drops a name whose other end is not chosen (D10); the editor turns the names into its own
 * link (`chargeOf`) when its rule accepts the pair, and the commit sends `parent_ref` = the BUY's `ref`. No plugin
 * writes the names yet, so the parse response of this test's own file is extended on the wire (`page.route`, as
 * `tx-bulk-import-handoff.spec.ts` F1-D4 extends its todos): the BUY gets `ref: 'r1'`, the FEE `parent_ref: 'r1'` and
 * the BUY's fake asset id (a generic CSV gives a FEE without an asset none).
 *
 *   (a) RED — import BUY + FEE → the editor shows the FEE in the BUY's group, closed (§5: the chip counts 1) → Save all
 *       → the server reads the FEE with `parent_transaction_id` = the BUY. Today the editor drops the names: the FEE is
 *       saved free.
 *   (b) GUARD — the BUY already saved (unlinked), then BUY + FEE imported: the BUY is a database duplicate, unticked in
 *       the review; the FEE is saved FREE, nothing is refused (`CHARGE_PARENT_REF_NOT_FOUND`), and the old BUY is not
 *       linked. Green today because the editor drops every name.
 *   (c) GUARD — the FEE already saved, then BUY + FEE imported: the FEE is the duplicate; the BUY is saved alone, with
 *       nothing refused, and the old FEE stays free. Green today for the same reason.
 *   (b) and (c) guard the SAVED outcome only: the editor maps names within one hand-over and regenerates them at the
 *   save, so a stray `parent_ref` from the wizard would not reach the commit. The wizard's own drop of a name whose
 *   other end is not chosen is pinned by `ImportWizardModal.test.ts` («the BUY unticked») and `importChargeNames.test.ts`.
 *   The wizard's split (Danske, Crédit Agricole) is not walked here: `ImportWizardModal.test.ts` covers it (a declared gap).
 *
 * Data. Every test registers its own account (onboarding skipped over the API), which owns everything it sees: one
 * broker (opened 2020-01-01, overdraft allowed, default plugin `broker_generic_csv`) and one asset whose ticker is a
 * unique 6-character token, so the wizard's candidate search finds it alone and resolves the file's symbol to it (read
 * back from the parse's `asset_mappings`). The CSV is written here and uploaded over the API under a unique name;
 * invented date, amounts and descriptions, each carrying the test's marker. Rows are found by description — data, never
 * a translation. Cleanup (fixture, whatever the outcome): leave the page, delete the uploaded file, the broker (force:
 * its rows go with it), the asset, the account.
 *
 * Waits are states: `data-busy` (`waitForSettled`), the editor's `data-validate-runs` sampled before Import, the commit
 * answer armed before Save all.
 *
 * Key data-testids: tx-import-button · import-wizard-* (fixtures/import-wizard.ts) · import-wizard-step4
 * [data-selected-count] · tbody tr[data-row-id=<merged index>] · td[data-column-id="selected"] button[aria-pressed] ·
 * tx-bulk-modal-root [data-validate-runs] · tx-bulk-body · tx-bulk-charges-toggle-<rowId>[data-charges-count]
 * [aria-expanded] · tx-bulk-commit.
 */

import {expect, test as base, type APIRequestContext, type Locator, type Page} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {validateRuns, waitForSettled, waitForValidateRun} from '../fixtures/app-events';
import {navigateTo} from '../fixtures/auth-helpers';
import {continueToReview, parseSelectedFile, selectBrokerFile, type ParseResponse} from '../fixtures/import-wizard';
import {deleteDisposableUser, prepareOnboardingAccount, registerDisposableUser, type DisposableUser} from '../fixtures/onboarding-accounts';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const COMMIT_PATH = `${API}/transactions/commit`;
const UPLOAD_PATH = `${API}/brokers/import/upload`;
const PARSE_PATH = /^\/api\/v1\/brokers\/import\/files\/[^/]+\/parse$/;
const GENERIC = 'broker_generic_csv';
const BROKER_OPENED_AT = '2020-01-01';
const DATE = '2025-06-02';
const UI_TIMEOUT = 15_000;
const STEP_TIMEOUT = 30_000;

// ---------------------------------------------------------------------------
// Shapes
// ---------------------------------------------------------------------------

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type Owned = {user: DisposableUser | null; brokerIds: number[]; assetIds: number[]; fileIds: string[]};
type Seed = {brokerId: number; assetId: number; symbol: string; marker: string; buy: string; fee: string};
type ParsedTx = {type: string; description?: string | null; asset_id?: number | null; ref?: string | null; parent_ref?: string | null};
type Parse = Omit<ParseResponse, 'transactions'> & {transactions: ParsedTx[]; asset_mappings?: Array<{fake_asset_id: number; selected_asset_id: number | null}>};
type Saved = {id: number; type: string; description?: string | null; parent_transaction_id?: number | null; charges_count?: number};
type BatchAnswer = {committed?: boolean; issues?: Array<{code?: string | null; operation?: string; index?: number}>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBe(true);
    return (await response.json()) as T;
}

/** A wait armed before the action and awaited later; a failure in between does not leave it rejecting unobserved. */
function armed<T>(wait: Promise<T>): Promise<T> {
    wait.catch(() => undefined);
    return wait;
}

// ---------------------------------------------------------------------------
// Owned data
// ---------------------------------------------------------------------------

/**
 * A fresh account, welcomed, its guides skipped; one broker reading the generic CSV by default, overdraft allowed (the
 * BUY spends money the broker never received); one asset whose ticker is the file's symbol. Every id is recorded for
 * cleanup before anything about it is checked.
 */
async function seedAccount(page: Page, request: APIRequestContext, owned: Owned, tag: string): Promise<Seed> {
    const user = await registerDisposableUser(request, tag);
    owned.user = user;
    await prepareOnboardingAccount(page, user, []);

    const marker = `${tag} ${uniqueSuffix()}`;
    const brokerName = `p1b-${marker}`;
    const brokers = await jsonFrom<{results: Array<{name: string; success: boolean; broker_id: number | null}>}>(
        await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: BROKER_OPENED_AT, allow_cash_overdraft: true, default_import_plugin: GENERIC}]}),
        'create the owned broker',
    );
    const broker = brokers.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(brokers)}`);

    // Six characters: the generic plugin reads an identifier of 1–6 alphanumerics as a ticker.
    const symbol = `P${uniqueToken(5)}`;
    const assetName = `P1b asset ${marker}`;
    const item = {display_name: assetName, currency: 'EUR', asset_type: 'ETF', identifier_ticker: symbol, quote_base_quantity: 1, active: true};
    schemas.FAAssetCreateItem.parse(item);
    const assets = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [item]}), 'create the owned asset');
    const asset = assets.results.find((result) => result.display_name === assetName);
    if (typeof asset?.asset_id === 'number') owned.assetIds.push(asset.asset_id);
    if (!asset?.success || typeof asset.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(assets)}`);

    return {brokerId: broker.broker_id, assetId: asset.asset_id, symbol, marker, buy: `P1b buy ${marker}`, fee: `P1b fee ${marker}`};
}

/** The BUY and the FEE as the file and the seeds write them: one broker, one asset, one date. */
function buyRow(seed: Seed): Record<string, unknown> {
    return {broker_id: seed.brokerId, asset_id: seed.assetId, type: 'BUY', date: DATE, quantity: '10', cash: {code: 'EUR', amount: '-100'}, description: seed.buy};
}

function feeRow(seed: Seed): Record<string, unknown> {
    return {broker_id: seed.brokerId, asset_id: seed.assetId, type: 'FEE', date: DATE, quantity: '0', cash: {code: 'EUR', amount: '-5'}, description: seed.fee};
}

/** Save rows over the API, unlinked; returns their ids in order. */
async function seedSaved(page: Page, creates: Array<Record<string, unknown>>, purpose: string): Promise<number[]> {
    const body = await jsonFrom<{committed?: boolean; issues?: unknown[]; results?: Array<{operation: string; index: number; ids?: number[]}>}>(await page.request.post(COMMIT_PATH, {data: {creates}}), purpose);
    expect(body.committed, `${purpose}: rolled back — ${JSON.stringify(body.issues ?? [])}`).toBe(true);
    return creates.map((_, index) => {
        const id = body.results?.find((result) => result.operation === 'create' && result.index === index)?.ids?.[0];
        if (typeof id !== 'number') throw new Error(`${purpose}: no id for create #${index}`);
        return id;
    });
}

async function ledgerOf(page: Page, seed: Seed): Promise<Saved[]> {
    return jsonFrom<Saved[]>(await page.request.get(`${API}/transactions`, {params: {broker_id: seed.brokerId}}), 'read the owned broker');
}

/** The one saved row described `description`. */
function savedDescribed(ledger: Saved[], description: string): Saved {
    const found = ledger.filter((row) => row.description === description);
    expect(found, `one saved row described ${JSON.stringify(description)}`).toHaveLength(1);
    return found[0];
}

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
            await jsonFrom(await page.request.delete(`${API}/brokers/import/files/${fileId}`), `delete the uploaded file ${fileId}`);
        });
    }
    for (const brokerId of owned.brokerIds) {
        await attempt(`broker ${brokerId}`, async () => {
            const body = await jsonFrom<{results: Array<{id: number; success: boolean}>}>(await page.request.delete(`${API}/brokers?ids=${brokerId}&force=true`), 'delete the owned broker and its rows');
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
    if (user) await attempt(`account ${user.username}`, () => deleteDisposableUser(request, user));
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

// Registration, the welcome hand-off, the wizard's corridor and a save: the 30 s default is a fraction of it.
test.setTimeout(180_000);

// ---------------------------------------------------------------------------
// The import
// ---------------------------------------------------------------------------

/**
 * Extend this page's parse responses with the names a linking plugin writes (P1a): the BUY `ref: 'r1'`, the FEE
 * `parent_ref: 'r1'` and the BUY's fake asset id. Found by description; a response without both rows is passed on as it
 * is. Returns a flag the caller checks: the names did reach the page.
 */
async function nameTheChargeOnTheWire(page: Page, seed: Seed): Promise<{patched: boolean}> {
    const state = {patched: false};
    await page.route(
        (url) => PARSE_PATH.test(url.pathname),
        async (route) => {
            const response = await route.fetch();
            if (!response.ok()) {
                await route.fulfill({response});
                return;
            }
            const body = (await response.json()) as Parse;
            const buy = body.transactions.find((tx) => tx.description === seed.buy);
            const fee = body.transactions.find((tx) => tx.description === seed.fee);
            if (buy && fee) {
                buy.ref = 'r1';
                fee.parent_ref = 'r1';
                fee.asset_id = buy.asset_id ?? null;
                state.patched = true;
            }
            // A new body, so not the original headers: their content-length is the old body's.
            await route.fulfill({status: response.status(), contentType: 'application/json', body: JSON.stringify(body)});
        },
    );
    return state;
}

/** The file: a BUY of the owned asset's symbol and a FEE (no asset: the wire gives it the BUY's), one date. */
function csv(seed: Seed): string {
    return ['date,type,quantity,amount,currency,asset,description', `${DATE},BUY,10,-100.00,EUR,${seed.symbol},${seed.buy}`, `${DATE},FEE,0,-5.00,EUR,,${seed.fee}`].join('\n') + '\n';
}

/**
 * Upload the file to the owned broker over the API, open the wizard from the transactions page, select and parse the
 * file (the names added on the wire), check the symbol resolved to the owned asset, and walk to the review. Returns the
 * review, settled, and the merged index of each row — its position in the parse response of this one file, which is
 * the review row's `data-row-id` (the review shows no description column).
 */
async function importToReview(page: Page, owned: Owned, seed: Seed): Promise<{review: Locator; buyIndex: number; feeIndex: number}> {
    const wire = await nameTheChargeOnTheWire(page, seed);
    const fileName = `p1b-${uniqueSuffix()}.csv`;
    const uploaded = await jsonFrom<{file_id: string; target_broker_id: number | null; compatible_plugins?: string[]}>(
        await page.request.post(UPLOAD_PATH, {multipart: {broker_id: String(seed.brokerId), file: {name: fileName, mimeType: 'text/csv', buffer: Buffer.from(csv(seed), 'utf8')}}}),
        `upload ${fileName}`,
    );
    owned.fileIds.push(uploaded.file_id);
    expect(uploaded.target_broker_id, 'the file lands on the owned broker').toBe(seed.brokerId);
    expect(uploaded.compatible_plugins ?? [], 'the generic CSV plugin reads it').toContain(GENERIC);

    await navigateTo(page, '/transactions');
    const transactionsPage = page.getByTestId('transactions-page');
    await expect(transactionsPage).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(transactionsPage, 20_000);
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-stepper')).toBeVisible({timeout: UI_TIMEOUT});
    const step1 = page.getByTestId('import-wizard-step1');
    await expect(step1).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(step1, STEP_TIMEOUT);
    // Nothing to upload in step 1: the file is already on the broker.
    await page.getByTestId('import-wizard-next').click();
    await selectBrokerFile(page, {brokerId: seed.brokerId, fileId: uploaded.file_id});
    const parsed = (await parseSelectedFile(page, uploaded.file_id)) as Parse;

    expect(wire.patched, 'premise: the names reached the page').toBe(true);
    const buy = parsed.transactions.find((tx) => tx.description === seed.buy);
    const fee = parsed.transactions.find((tx) => tx.description === seed.fee);
    expect([buy?.type, fee?.type], 'premise: the plugin reads a BUY and a FEE').toEqual(['BUY', 'FEE']);
    expect({ref: buy?.ref, parent_ref: fee?.parent_ref}, 'premise: the page holds the names').toEqual({ref: 'r1', parent_ref: 'r1'});
    const resolved = parsed.asset_mappings?.find((mapping) => mapping.fake_asset_id === buy?.asset_id)?.selected_asset_id ?? null;
    expect(resolved, "premise: the file's symbol resolves to the owned asset").toBe(seed.assetId);
    expect(fee?.asset_id, 'premise: the FEE has the BUY’s asset').toBe(buy?.asset_id);

    const review = await continueToReview(page, parsed);
    return {review, buyIndex: parsed.transactions.findIndex((tx) => tx.description === seed.buy), feeIndex: parsed.transactions.findIndex((tx) => tx.description === seed.fee)};
}

/** The review's switch of the row of merged index `index` (`aria-pressed`). */
function reviewSwitch(review: Locator, index: number): Locator {
    return review.locator(`tbody tr[data-row-id="${index}"] td[data-column-id="selected"] button[aria-pressed]`);
}

function editorRoot(page: Page): Locator {
    return page.getByTestId('tx-bulk-modal-root');
}

/** Import from the review; ends on the editor, its hand-over validation run and settled. */
async function importToEditor(page: Page): Promise<Locator> {
    const root = editorRoot(page);
    await expect(root, 'the editor is open beneath the wizard').toBeAttached();
    const before = await validateRuns(root);
    const importButton = page.getByTestId('import-wizard-import');
    await expect(importButton, 'Import is offered').toBeEnabled({timeout: STEP_TIMEOUT});
    await importButton.click();
    await expect(page.getByTestId('import-wizard-stepper'), 'the wizard hands over and closes').toHaveCount(0, {timeout: STEP_TIMEOUT});
    await expect(root).toBeVisible({timeout: UI_TIMEOUT});
    await waitForValidateRun(root, before, STEP_TIMEOUT);
    await waitForSettled(root, STEP_TIMEOUT);
    return root;
}

function editorRow(root: Locator, description: string): Locator {
    return root.getByTestId('tx-bulk-body').locator('tbody tr[data-row-id]').filter({hasText: description});
}

/** Save all, and the commit's answer, armed before the click. */
async function saveAll(page: Page, root: Locator): Promise<BatchAnswer> {
    const save = root.getByTestId('tx-bulk-commit');
    await expect(save, 'Save all is offered').toBeEnabled({timeout: UI_TIMEOUT});
    const answer = armed(page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === COMMIT_PATH, {timeout: 60_000}));
    await save.click();
    return jsonFrom<BatchAnswer>(await answer, 'the commit answer');
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Import → editor: the linked charges a plugin names (66 P1b)', () => {
    test('(a) BUY + FEE named by the file: the FEE arrives under the BUY, closed, and is saved linked to it', async ({page, request, owned}) => {
        const seed = await seedAccount(page, request, owned, 'p1b-a');
        const {review} = await importToReview(page, owned, seed);
        await expect(review, 'both rows are selected').toHaveAttribute('data-selected-count', '2', {timeout: UI_TIMEOUT});

        const root = await importToEditor(page);
        const buyRowLocator = editorRow(root, seed.buy);
        await expect(buyRowLocator).toHaveCount(1, {timeout: UI_TIMEOUT});
        const rowId = await buyRowLocator.getAttribute('data-row-id');
        const chip = root.getByTestId(`tx-bulk-charges-toggle-${rowId}`);
        // Soft: the save below is the deciding assertion, and it must run either way.
        await expect.soft(chip, 'the BUY row carries the chip of its imported FEE').toHaveAttribute('data-charges-count', '1', {timeout: UI_TIMEOUT});
        await expect.soft(chip, 'closed: an import brings its charges closed (§5)').toHaveAttribute('aria-expanded', 'false');

        const answer = await saveAll(page, root);
        expect(answer.committed, `the batch is committed: ${JSON.stringify(answer.issues ?? [])}`).toBe(true);

        const ledger = await ledgerOf(page, seed);
        const buy = savedDescribed(ledger, seed.buy);
        const fee = savedDescribed(ledger, seed.fee);
        expect(fee.parent_transaction_id ?? null, 'the server reads the FEE linked to the BUY').toBe(buy.id);
        expect(buy.charges_count ?? 0, 'and the BUY counts it').toBe(1);
    });

    test('(b) guard — the BUY already saved: it is a duplicate, unticked; the FEE is saved free and the old BUY stays unlinked', async ({page, request, owned}) => {
        const seed = await seedAccount(page, request, owned, 'p1b-b');
        const [oldBuyId] = await seedSaved(page, [buyRow(seed)], 'save the BUY first, unlinked');

        const {review, buyIndex, feeIndex} = await importToReview(page, owned, seed);
        await expect(reviewSwitch(review, buyIndex), 'the BUY is a database duplicate: unticked').toHaveAttribute('aria-pressed', 'false', {timeout: UI_TIMEOUT});
        await expect(reviewSwitch(review, feeIndex), 'the FEE is new: ticked').toHaveAttribute('aria-pressed', 'true');
        await expect(review).toHaveAttribute('data-selected-count', '1');

        const root = await importToEditor(page);
        await expect(editorRow(root, seed.fee), 'the FEE reached the editor').toHaveCount(1, {timeout: UI_TIMEOUT});
        const answer = await saveAll(page, root);
        expect(answer.committed, `nothing is refused (no CHARGE_PARENT_REF_NOT_FOUND): ${JSON.stringify(answer.issues ?? [])}`).toBe(true);

        const ledger = await ledgerOf(page, seed);
        expect(
            ledger.filter((row) => row.type === 'BUY').map((row) => row.id),
            'one BUY, the old one',
        ).toEqual([oldBuyId]);
        expect(savedDescribed(ledger, seed.fee).parent_transaction_id ?? null, 'the FEE is saved free').toBeNull();
        expect(savedDescribed(ledger, seed.buy).charges_count ?? 0, 'the old BUY is not linked').toBe(0);
    });

    test('(c) guard — the FEE already saved: it is a duplicate, unticked; the BUY is saved alone and nothing is refused', async ({page, request, owned}) => {
        const seed = await seedAccount(page, request, owned, 'p1b-c');
        const [oldFeeId] = await seedSaved(page, [feeRow(seed)], 'save the FEE first, unlinked');

        const {review, buyIndex, feeIndex} = await importToReview(page, owned, seed);
        await expect(reviewSwitch(review, feeIndex), 'the FEE is a database duplicate: unticked').toHaveAttribute('aria-pressed', 'false', {timeout: UI_TIMEOUT});
        await expect(reviewSwitch(review, buyIndex), 'the BUY is new: ticked').toHaveAttribute('aria-pressed', 'true');
        await expect(review).toHaveAttribute('data-selected-count', '1');

        const root = await importToEditor(page);
        await expect(editorRow(root, seed.buy), 'the BUY reached the editor').toHaveCount(1, {timeout: UI_TIMEOUT});
        const answer = await saveAll(page, root);
        expect(answer.committed, `nothing is refused: ${JSON.stringify(answer.issues ?? [])}`).toBe(true);

        const ledger = await ledgerOf(page, seed);
        expect(
            ledger.filter((row) => row.type === 'FEE').map((row) => row.id),
            'one FEE, the old one',
        ).toEqual([oldFeeId]);
        expect(savedDescribed(ledger, seed.fee).parent_transaction_id ?? null, 'the old FEE stays free').toBeNull();
        expect(savedDescribed(ledger, seed.buy).charges_count ?? 0, 'the new BUY has no charge').toBe(0);
    });
});
