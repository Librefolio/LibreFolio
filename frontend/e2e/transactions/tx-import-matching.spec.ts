/**
 * Group E4 — real BRIM asset-candidate matching against the review step's resolution.
 *
 * Scope: whether the review step's per-instrument card ends up bound to the asset a real
 * candidate search actually finds — not the resolution UI's layout, not the unification
 * step (`tx-import-asset-identity.spec.ts`), not the inspector's persistence
 * (`tx-import-asset-inspector.spec.ts`, first-authored, not touched here).
 *
 * `ImportWizardModal.uniqueCandidateId` (formerly `uniqueExactCandidateId`) decides this:
 * one distinct asset id among the candidates, of *any* confidence, selects it; two or more
 * distinct ids reject the ambiguity. The unit tests in `importMerge.test.ts` pin that
 * function in isolation; these four exercise it through the real backend and the real
 * review card, because the candidate list here comes from `search_asset_candidates`
 * (`backend/test_scripts/test_db/test_brim_bulk_candidates.py`), never a fixture.
 *
 * E4-01: a primary-ISIN match (EXACT), including an inactive asset, resolves before any
 *        manual click.
 * E4-02: an alias-only match (`identifier_other`, HIGH — never EXACT) still resolves.
 *        This is the independent contract-control check for the review card: the original
 *        report was an expectation of auto-creation, not an actual failure here. The old
 *        `uniqueExactCandidateId` missed the case that matters, so an EXACT-only policy
 *        would have left this card unresolved at review time even though the backend had
 *        already auto-selected it during parsing.
 * E4-03: an asset created *after* parsing is still picked up — by the live refresh that
 *        "Continue" always runs, not by a second parse of the file.
 * E4-04: a competing alias on a second asset turns a previously-unique auto-match
 *        ambiguous on the next live refresh (unselecting it), while an explicit manual
 *        choice survives that same refresh.
 *
 * Each test owns its broker, inline seven-column Generic CSV, assets and file id, and
 * deletes exactly those rows in its own cleanup — nothing global is read or asserted on.
 * The final-recheck cases also own committed source transactions, removed with their
 * owned broker during cleanup. No provider/pricing I/O is involved in candidate matching.
 */

import {expect, test as base, type Locator, type Page} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {eventSeq, waitForEvent, waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;

type Owned = {
    suffix: string;
    assetIds: number[];
    brokerIds: number[];
    fileIds: string[];
    /** POSTs actually hitting `/parse` for our own file(s) — proves a refresh never reparses. */
    parseCalls: number;
};

type HttpResponse = {ok(): boolean; status(): number; text(): Promise<string>; json(): Promise<unknown>};
type CreatedAsset = {id: number; name: string; ticker: string};
type ParsedMapping = {fake_asset_id: number; extracted_isin: string | null; selected_asset_id: number | null; candidates: Array<{asset_id: number; match_confidence: string}>};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/** A 12-char ISIN-shaped code the Generic CSV parser will classify as an ISIN (no checksum is enforced). */
function syntheticIsin(): string {
    return `XX${uniqueToken(9)}7`;
}

async function createAsset(page: Page, owned: Owned, label: string, options: {isin?: string; other?: string[]; active?: boolean} = {}): Promise<CreatedAsset> {
    const name = `E4 ${label} ${owned.suffix}`;
    const ticker = `E4${uniqueToken(12)}`;
    const data: Record<string, unknown> = {display_name: name, currency: 'EUR', asset_type: 'ETF', identifier_ticker: ticker, active: options.active ?? true};
    if (options.isin) data.identifier_isin = options.isin;
    if (options.other) data.identifier_other = options.other;
    schemas.FAAssetCreateItem.parse(data);
    const response = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [data]}), `create owned asset ${label}`);
    const created = response.results.find((item) => item.display_name === name);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(response)}`);
    owned.assetIds.push(created.asset_id);
    return {id: created.asset_id, name, ticker};
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
            throw new Error(`E4 matching regressions may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {suffix: `m${testInfo.workerIndex}-${uniqueSuffix()}`, assetIds: [], brokerIds: [], fileIds: [], parseCalls: 0};
        page.on('request', (request) => {
            if (request.method() === 'POST' && /\/brokers\/import\/files\/[^/]+\/parse$/.test(new URL(request.url()).pathname)) owned.parseCalls++;
        });
        try {
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(120_000);

/**
 * Upload a broker's own single-instrument seven-column Generic CSV and drive the wizard from
 * the transactions page through the parsed step3 — stopping there so callers decide exactly
 * when (relative to their own asset mutations) the live candidate refresh should run.
 */
async function uploadAndParse(page: Page, owned: Owned, label: string, assetCell: string): Promise<ParsedMapping & {brokerId: number; buyIndex: number; fundingIndex: number}> {
    const brokerName = `E4 broker ${label} ${owned.suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_generic_csv'}]}), 'create owned import broker');
    const broker = created.results.find((item) => item.name === brokerName);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    owned.brokerIds.push(broker.broker_id);
    const brokerId = broker.broker_id;

    const fundingDescription = `E4 funding ${label} ${owned.suffix}`;
    const buyDescription = `E4 buy ${label} ${owned.suffix}`;
    const csv = ['date,type,quantity,amount,currency,asset,description', `2024-01-02,DEPOSIT,0,500,EUR,,${fundingDescription}`, `2024-01-03,BUY,3,-30,EUR,${assetCell},${buyDescription}`, ''].join('\n');
    const upload = await jsonFrom<{file_id: string; target_broker_id: number}>(
        await page.request.post(`${API}/brokers/import/upload`, {multipart: {broker_id: String(brokerId), file: {name: `e4-${label}-${owned.suffix}.csv`, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}}}),
        'upload synthetic Generic CSV',
    );
    owned.fileIds.push(upload.file_id);
    expect(upload.target_broker_id).toBe(brokerId);

    await navigateTo(page, '/transactions');
    await expect(page.getByTestId('transactions-page')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('transactions-page'));
    await page.getByTestId('tx-import-button').click();
    await expect(page.getByTestId('import-wizard-step1')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('import-wizard-step1'));
    await page.getByTestId('import-wizard-next').click();
    await expect(page.getByTestId('import-wizard-step2')).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(page.getByTestId('import-wizard-step2'));

    const checkbox = page.getByTestId('import-wizard-step2').getByTestId(`dt-row-checkbox-${upload.file_id}`);
    await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
    await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const [parsedResponse] = await Promise.all([page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/files/${upload.file_id}/parse` && response.request().method() === 'POST', {timeout: 30_000}), page.getByTestId('import-wizard-parse').click()]);
    const parsed = await jsonFrom<{transactions: Array<{description: string; asset_id: number | null}>; asset_mappings: ParsedMapping[]}>(parsedResponse, 'parse owned Generic CSV');
    const purchase = parsed.transactions.find((item) => item.description === buyDescription);
    const fakeAssetId = purchase?.asset_id;
    if (typeof fakeAssetId !== 'number') throw new Error(`Synthetic BUY row produced no fake asset id: ${JSON.stringify(parsed)}`);
    const mapping = parsed.asset_mappings.find((item) => item.fake_asset_id === fakeAssetId);
    if (!mapping) throw new Error(`No asset mapping for the synthetic BUY row: ${JSON.stringify(parsed)}`);
    await waitForParseVerdict(page);
    const buyIndex = parsed.transactions.findIndex((row) => row.description === buyDescription);
    const fundingIndex = parsed.transactions.findIndex((row) => row.description === fundingDescription);
    if (buyIndex < 0 || fundingIndex < 0) throw new Error('Owned source transactions missing from parse response');
    return {...mapping, brokerId, buyIndex, fundingIndex};
}

/** Click Continue from the parsed step3, past an optional warning confirm, into the review step4. */
async function continueToReview(page: Page): Promise<Locator> {
    await expect(page.getByTestId('import-wizard-continue')).toBeEnabled({timeout: UI_TIMEOUT});
    await page.getByTestId('import-wizard-continue').click();
    const confirm = page.getByTestId('import-wizard-warning-confirm');
    if (await confirm.isVisible({timeout: 1_500}).catch(() => false)) await confirm.click();
    const review = page.getByTestId('import-wizard-step4');
    await expect(review).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(review);
    return review;
}

/** "Reopen the cache": back to the parsed step3 (no reparse), the same round trip a user
 *  takes via the stepper. Reaching this step re-runs `refreshCandidates` on the next Continue. */
async function backToParsedStep(page: Page): Promise<void> {
    await page.getByTestId('import-wizard-back').click();
    await expect(page.getByTestId('import-wizard-step3')).toBeVisible({timeout: UI_TIMEOUT});
}

/** The lone resolution card's AssetSelect, for a file that extracted exactly one instrument. */
function assetSelect(review: Locator): Locator {
    const select = review.getByTestId('import-wizard-resolve-section').getByTestId('asset-select');
    return select;
}

/** `resolvedAssetId !== null` is exactly when the card renders its "inspect asset" button. */
function inspectButton(review: Locator): Locator {
    return review.getByTestId(/^import-wizard-inspect-asset-/);
}

async function expectResolvedTo(review: Locator, asset: CreatedAsset): Promise<void> {
    await expect(inspectButton(review)).toHaveCount(1);
    // The trigger renders the selected asset's ticker (real data, not a translated label).
    await expect(assetSelect(review).getByRole('combobox')).toContainText(asset.ticker, {timeout: UI_TIMEOUT});
}

async function expectUnresolved(review: Locator): Promise<void> {
    await expect(inspectButton(review)).toHaveCount(0);
}

async function pickManually(page: Page, review: Locator, asset: CreatedAsset): Promise<void> {
    const select = assetSelect(review);
    await optionsClosed(page);
    await select.getByRole('combobox').click();
    await expect(select.getByRole('listbox')).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
    await select.getByRole('textbox').fill(asset.ticker);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    await option.click();
    await optionsClosed(page);
    // The pick may itself trigger a candidate refresh (checkAndPromptIdentifier merges search
    // keys silently when the asset already holds the code); let it settle before moving on.
    await waitForSettled(review);
}

test.describe('Import Wizard — E4 candidate matching', () => {
    test('E4-01: auto-matches an inactive existing asset by primary ISIN before parsing', async ({page, owned}) => {
        const isin = syntheticIsin();
        const asset = await createAsset(page, owned, 'primary-inactive', {isin, active: false});
        const mapping = await uploadAndParse(page, owned, 'primary', isin);
        expect(mapping.extracted_isin).toBe(isin);
        // Precondition: the backend already found and auto-selected this one candidate at
        // parse time — an inactive asset is not excluded from the search.
        expect(mapping.selected_asset_id).toBe(asset.id);

        const review = await continueToReview(page);
        await expectResolvedTo(review, asset);
        await expect(assetSelect(review).getByTestId('asset-select-selected-inactive-badge')).toBeVisible({timeout: UI_TIMEOUT});
        expect(owned.parseCalls, 'exactly the one explicit parse').toBe(1);
    });

    test('E4-02: auto-matches via an alias-only ISIN — a unique HIGH-confidence candidate, not just EXACT', async ({page, owned}) => {
        const isin = syntheticIsin();
        // No identifier_isin: the code lives only among the alternates, so the only match this
        // query can return is HIGH confidence, never EXACT.
        const asset = await createAsset(page, owned, 'alias-only', {other: [isin]});
        const mapping = await uploadAndParse(page, owned, 'alias', isin);
        expect(mapping.extracted_isin).toBe(isin);
        // Real BRIMAssetCandidate rows carry symbol/isin/name too; project down to the two
        // fields this precondition is about.
        expect(mapping.candidates.map((c) => ({asset_id: c.asset_id, match_confidence: c.match_confidence}))).toEqual([{asset_id: asset.id, match_confidence: 'high'}]);
        expect(mapping.selected_asset_id).toBe(asset.id);

        // At review time, the card is still bound to the live candidate contract. A policy
        // that only accepted an EXACT tier would leave this unresolved even though it is the
        // only candidate there is.
        const review = await continueToReview(page);
        await expectResolvedTo(review, asset);
        expect(owned.parseCalls).toBe(1);
    });

    test('E4-03: a live candidate refresh finds an asset created after parsing, without reparsing the file', async ({page, owned}) => {
        const isin = syntheticIsin();
        const mapping = await uploadAndParse(page, owned, 'post-parse', isin);
        expect(mapping.extracted_isin).toBe(isin);
        // Precondition: nothing matched at parse time — the asset does not exist yet.
        expect(mapping.candidates).toEqual([]);
        expect(mapping.selected_asset_id).toBeNull();

        // Real API call, made while the wizard still sits on the already-parsed step3. The
        // cached parse response (and its empty candidate snapshot) is untouched by this.
        const asset = await createAsset(page, owned, 'post-parse', {isin});

        const review = await continueToReview(page);
        await expectResolvedTo(review, asset);
        expect(owned.parseCalls, 'picked up by the live refresh, not a second parse').toBe(1);
    });

    test('E4-04: a competing alias unresolves a unique auto-match on refresh; an explicit manual choice survives the same refresh', async ({page, owned}) => {
        const isin = syntheticIsin();
        const primary = await createAsset(page, owned, 'primary', {isin});
        const mapping = await uploadAndParse(page, owned, 'competing', isin);
        expect(mapping.selected_asset_id).toBe(primary.id);

        const review = await continueToReview(page);
        await expectResolvedTo(review, primary);

        // A second, different asset now carries the very same code as an alternate — the next
        // query for this ISIN returns two distinct asset ids, not one.
        const competitor = await createAsset(page, owned, 'competitor', {other: [isin]});

        await backToParsedStep(page);
        const reopened = await continueToReview(page);
        await expectUnresolved(reopened);
        expect(owned.parseCalls, 'reopening the cached parse must not re-hit /parse').toBe(1);

        // The user arbitrates explicitly...
        await pickManually(page, reopened, competitor);
        await expectResolvedTo(reopened, competitor);

        // ...and a further refresh over the same still-ambiguous pair must not silently
        // override that explicit choice.
        await backToParsedStep(page);
        const reopenedAgain = await continueToReview(page);
        await expectResolvedTo(reopenedAgain, competitor);
        expect(owned.parseCalls).toBe(1);
    });

    for (const onlyPurchase of [false, true]) {
        test(`E4-05: final duplicate recheck cannot silently hand off a ${onlyPurchase ? 'zero-row' : 'reduced'} selection`, async ({page, owned}) => {
            const isin = syntheticIsin();
            const label = onlyPurchase ? 'final-buy-only' : 'final-with-funding';
            await createAsset(page, owned, `${label}-primary`, {isin});
            const asset = await createAsset(page, owned, `${label}-alternate`, {other: [isin]});
            const mapping = await uploadAndParse(page, owned, label, isin);
            expect(mapping.selected_asset_id).toBeNull();
            const buyDescription = `E4 buy ${label} ${owned.suffix}`;
            const committed = await jsonFrom<{committed: boolean; results: Array<{operation: string; ids: number[]}>}>(
                await page.request.post(`${API}/transactions/commit`, {
                    data: {
                        creates: [
                            {broker_id: mapping.brokerId, type: 'DEPOSIT', date: '2023-12-01', cash: {code: 'EUR', amount: '100'}, description: `Owned prior funding ${owned.suffix}`},
                            {broker_id: mapping.brokerId, asset_id: asset.id, type: 'BUY', date: '2024-01-03', quantity: '3', cash: {code: 'EUR', amount: '-30'}, description: buyDescription},
                        ],
                    },
                }),
                'create owned transaction for the real duplicate check',
            );
            expect(committed.committed).toBe(true);
            const ids = committed.results.filter((result) => result.operation === 'create').flatMap((result) => result.ids);
            const query = new URLSearchParams(ids.map((id) => ['ids', String(id)]));
            const saved = await jsonFrom<Array<{id: number; type: string; description: string}>>(await page.request.get(`${API}/transactions?${query}`), 'read owned duplicate fixture');
            const existingBuy = saved.find((row) => row.type === 'BUY' && row.description === buyDescription);
            if (!existingBuy) throw new Error('Owned BUY fixture was not persisted');

            const review = await continueToReview(page);
            await expectUnresolved(review);
            await pickManually(page, review, asset);
            await expectResolvedTo(review, asset);
            // This single owned file maps its identified parse rows to merged row IDs;
            // the review table does not display transaction descriptions.
            const buyIndex = String(mapping.buyIndex);
            const fundingIndex = String(mapping.fundingIndex);
            const buy = review.locator(`tr[data-row-id="${buyIndex}"]`);
            const funding = review.locator(`tr[data-row-id="${fundingIndex}"]`);
            await expect(buy).toHaveCount(1);
            await expect(funding).toHaveCount(1);
            const buyToggle = buy.locator('button[aria-pressed]');
            await expect(buyToggle).toHaveAttribute('aria-pressed', 'true');
            if (onlyPurchase) {
                await funding.locator('button[aria-pressed]').click();
            }
            await expect(review).toHaveAttribute('data-selected-count', onlyPurchase ? '1' : '2');
            const bulk = page.getByTestId('tx-bulk-modal');
            await expect(bulk.getByTestId('tx-bulk-date')).toHaveCount(0);
            const since = await eventSeq(page);
            const [duplicateResponse] = await Promise.all([
                page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/duplicates` && response.request().method() === 'POST' && response.request().postDataJSON().broker_id === mapping.brokerId),
                page.getByTestId('import-wizard-import').click(),
            ]);
            const report = await jsonFrom<{tx_likely_duplicates: Array<{tx_existing_matches: Array<{existing_tx_id: number}>}>}>(duplicateResponse, 'final real duplicate verdict');
            expect(report.tx_likely_duplicates.some((row) => row.tx_existing_matches.some((match) => match.existing_tx_id === existingBuy.id))).toBe(true);
            const changed = await waitForEvent(page, 'tx.import.selection.changed', {since, timeout: UI_TIMEOUT});
            expect(changed.detail).toEqual({
                previousIndices: onlyPurchase ? [Number(buyIndex)] : [Number(fundingIndex), Number(buyIndex)],
                currentIndices: onlyPurchase ? [] : [Number(fundingIndex)],
            });
            await waitForSettled(review);
            await expect(review).toBeVisible();
            await expect(bulk.getByTestId('tx-bulk-date')).toHaveCount(0);
            await expect(page.getByTestId('toast-warning')).toBeVisible();
            await expect(review).toHaveAttribute('data-selected-count', onlyPurchase ? '0' : '1');
            await expect(buyToggle).toHaveAttribute('aria-pressed', 'false');
            if (onlyPurchase) await expect(page.getByTestId('import-wizard-import')).toBeDisabled();

            await buyToggle.click();
            await expect(buyToggle).toHaveAttribute('aria-pressed', 'true');
            const [staged] = await Promise.all([
                page.waitForRequest((request) => request.method() === 'POST' && new URL(request.url()).pathname === `${API}/transactions/validate` && request.postDataJSON().creates?.some((row: {description?: string}) => row.description === buyDescription)),
                page.getByTestId('import-wizard-import').click(),
            ]);
            await expect(bulk).toBeVisible({timeout: UI_TIMEOUT});
            await expect(review).toBeHidden();
            expect(staged.postDataJSON().creates).toHaveLength(onlyPurchase ? 1 : 2);
            expect(staged.postDataJSON().creates).toEqual(expect.arrayContaining([expect.objectContaining({broker_id: mapping.brokerId, asset_id: asset.id, description: buyDescription})]));
            expect(owned.parseCalls).toBe(1);
        });
    }
});
