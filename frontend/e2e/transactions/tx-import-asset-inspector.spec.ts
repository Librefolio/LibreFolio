/**
 * Group E — real ImportWizard asset-inspector persistence and nested dialogs.
 *
 * E1-001: stored metadata + quote base survive a manual edit, including inactive assets.
 * E1-002: explicit, offline Ask Provider distributions survive PATCH, GET and reopen.
 * E1-003: clearing description preserves sector/geographic; whole classification can still be nulled.
 * E2-001: a real currency blocker is actionable above the inspector; cancel is inert,
 *         confirm wipes only the inspected asset's own market data.
 * E2-002: provider comparison is actionable above the inspector and saves the selection.
 *
 * Pre-E1/E2 baseline (independent U1 probe work may be present): FAinfoResponse
 * carries quote_base_quantity, but not
 * classification_params. Quote-base assertions are preservation checks, not a claim
 * that the summary omits it. Currency confirmation was a raw z50 dialog; comparison
 * was z70 beneath the z90 inspector. Overlay tests assert hit-testing, not z constants.
 *
 * Each test owns its broker, inline seven-column Generic CSV, assets and price rows.
 * Assets exist BEFORE parsing. The CSV deliberately uses an unmapped name, then the
 * user picks the existing asset by id: these tests do not depend on E4 auto-matching.
 * No transaction is imported/committed. All create/assign/read/PATCH/wipe calls are real.
 *
 * Only provider I/O is intercepted. Stored assignments use the real offline `mockprov`,
 * so another worker fetching this globally visible asset cannot reach a live provider.
 * Probe/sync/current response bodies are checked against the generated Zod schemas.
 *
 * No extra distribution-row hooks are needed: the existing distribution-editor test
 * ids scope the rendered numeric weight inputs and total. Canonical keys and weights
 * are checked exactly in the real PATCH and metadata GET, never via localized labels.
 */

import {expect, test as base, type Locator, type Page, type Response} from '../fixtures/playwright';
import {schemas} from '../../src/lib/api/generated';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {waitForParseVerdict, waitForSettled} from '../fixtures/app-events';
import {optionsClosed} from '../fixtures/probe';
import {TEST_USER} from '../fixtures/test-users';
import {uniqueSuffix, uniqueToken} from '../fixtures/unique';

const API = '/api/v1';
const TEST_PORT = process.env.TEST_PORT || '6041';
const UI_TIMEOUT = 10_000;
const PROVIDER = 'mockprov';

type Distribution = Record<string, number | string>;
type Classification = {
    short_description?: string | null;
    sector_area?: {distribution: Distribution} | null;
    geographic_area?: {distribution: Distribution} | null;
};
type AssetMetadata = {
    asset_id: number;
    display_name: string;
    currency: string;
    asset_type: string;
    quote_base_quantity: number;
    classification_params: Classification | null;
    provider_code: string | null;
};
type OwnedAsset = {
    id: number;
    name: string;
    ticker: string;
    active: boolean;
    quoteBase: number;
    classification: Classification | null;
};
type ProbeRequest = {
    provider_code: string;
    identifier: string;
    identifier_type: string;
    provider_params?: Record<string, unknown> | null;
    operations: string[];
};
type Mutation = {method: string; path: string; payload: unknown};
type Owned = {
    suffix: string;
    assetIds: number[];
    brokerIds: number[];
    fileIds: string[];
    metadata: Map<string, Record<string, unknown>>;
    probes: ProbeRequest[];
    syncs: unknown[];
    unexpectedProviderCalls: string[];
    mutations: Mutation[];
};
type HttpResponse = {
    ok(): boolean;
    status(): number;
    text(): Promise<string>;
    json(): Promise<unknown>;
};
type BulkResult = {asset_id: number; success: boolean; message?: string};

async function jsonFrom<T>(response: HttpResponse, purpose: string): Promise<T> {
    expect(response.ok(), `${purpose}: HTTP ${response.status()} ${await response.text()}`).toBeTruthy();
    return (await response.json()) as T;
}

/**
 * Intercepts no CRUD, assignment, parse, duplicate-check, backup, or wipe endpoint.
 * Unexpected provider calls fail closed, rather than escaping to a live provider.
 */
async function installOfflineProviderIO(page: Page, owned: Owned, baseURL: string): Promise<void> {
    const origin = new URL(baseURL).origin;
    await page.route('**/*', async (route) => {
        const url = new URL(route.request().url());
        if (['http:', 'https:'].includes(url.protocol) && url.origin !== origin) {
            // Seeded icon URLs must not turn this offline spec into an external request.
            await route.abort('blockedbyclient');
            return;
        }
        await route.fallback();
    });
    page.on('request', (request) => {
        const path = new URL(request.url()).pathname;
        if ((path === `${API}/assets` && request.method() === 'PATCH') || /\/assets\/\d+\/market-data\/wipe$/.test(path)) {
            owned.mutations.push({method: request.method(), path, payload: request.postData() ? request.postDataJSON() : null});
        }
    });

    await page.route('**/api/v1/assets/provider/probe', async (route) => {
        const request = route.request().postDataJSON() as ProbeRequest;
        owned.probes.push(request);
        const patch = owned.metadata.get(request.identifier);
        const expected = request.provider_code === PROVIDER && request.identifier_type === 'TICKER' && request.operations.length === 1 && request.operations.includes('metadata') && patch !== undefined;
        if (!expected) owned.unexpectedProviderCalls.push(`probe: ${JSON.stringify(request)}`);

        const unavailable = {success: false, execution_time_ms: 0, error_code: 'NO_DATA', error: 'Synthetic provider: this operation has no fixture data'};
        const body = {
            provider_code: request.provider_code,
            identifier: request.identifier,
            total_execution_time_ms: 0,
            ...(request.operations.includes('metadata') ? {metadata: expected ? {success: true, execution_time_ms: 0, patch_data: patch} : unavailable} : {}),
            ...(request.operations.includes('current_price') ? {current_price: unavailable} : {}),
            ...(request.operations.includes('history') ? {history: unavailable} : {}),
        };
        schemas.FAProviderProbeResponse.parse(body);
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });

    await page.route('**/api/v1/assets/prices/sync', async (route) => {
        const request = route.request().postDataJSON() as Array<{asset_id: number}>;
        owned.syncs.push(request);
        // No sync is expected in these unchanged-provider edit flows. If one regresses,
        // report that nothing was fetched/written, never fabricate a successful sync.
        const body = {
            results: request.map(({asset_id}) => ({
                asset_id,
                status: 'failed',
                provider_used: null,
                points_fetched: 0,
                points_changed: 0,
                inserted_count: 0,
                updated_count: 0,
                events_fetched: 0,
                events_changed: 0,
                changed_points: null,
                errors: ['Synthetic offline boundary: no sync performed'],
            })),
            success_count: 0,
            errors: [],
            total_points_changed: 0,
        };
        schemas.FABulkRefreshResponse.parse(body);
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });

    await page.route('**/api/v1/assets/prices/current', async (route) => {
        const ids = route.request().postDataJSON() as number[];
        // /current can write today's OHLC. Suppress that unrelated writer, but do not
        // claim a quote exists: persistence assertions below use the REAL backup API.
        const body = {
            results: ids.map((asset_id) => ({asset_id, value: null, currency: null, as_of_date: null, source: null, error: 'Synthetic offline boundary: no current quote requested'})),
            success_count: 0,
            errors: [],
        };
        schemas.FACurrentPriceResponse.parse(body);
        await route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify(body)});
    });
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
    // Unmount the wizard before removing its rows; do not leave an in-flight UI writer.
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
            const result = await jsonFrom<{results: BulkResult[]}>(await page.request.delete(`${API}/assets?asset_ids=${assetId}`), 'delete owned asset and its prices');
            expect(result.results.find((item) => item.asset_id === assetId)?.success).toBe(true);
        });
    }
    expect(failures, 'every cleanup operation is scoped to ids this test created').toEqual([]);
}

const test = base.extend<{owned: Owned}>({
    owned: async ({page}, use, testInfo) => {
        const baseURL = testInfo.project.use.baseURL;
        if (!baseURL || new URL(baseURL).port !== TEST_PORT || !['localhost', '127.0.0.1'].includes(new URL(baseURL).hostname)) {
            throw new Error(`Inspector regressions may only use the shared local test backend on port ${TEST_PORT}`);
        }
        const owned: Owned = {
            suffix: `w${testInfo.workerIndex}-${uniqueSuffix()}`,
            assetIds: [],
            brokerIds: [],
            fileIds: [],
            metadata: new Map(),
            probes: [],
            syncs: [],
            unexpectedProviderCalls: [],
            mutations: [],
        };
        await installOfflineProviderIO(page, owned, baseURL);
        try {
            await login(page, TEST_USER);
            await use(owned);
        } finally {
            await cleanupOwned(page, owned);
        }
    },
});

test.setTimeout(120_000);

async function createAsset(page: Page, owned: Owned, label: string, options: {classification?: Classification | null; quoteBase?: number; active?: boolean; provider?: boolean} = {}): Promise<OwnedAsset> {
    const name = `Inspector ${label} ${owned.suffix}`;
    const ticker = `GE${uniqueToken(14)}`;
    const active = options.active ?? true;
    const quoteBase = options.quoteBase ?? 100;
    const classification = options.classification ?? null;
    const data = {display_name: name, identifier_ticker: ticker, currency: 'EUR', asset_type: 'ETF', quote_base_quantity: quoteBase, active, classification_params: classification};
    schemas.FAAssetCreateItem.parse(data);
    const response = await jsonFrom<{results: Array<{asset_id: number | null; display_name: string; success: boolean}>}>(await page.request.post(`${API}/assets`, {data: [data]}), 'create owned asset');
    const created = response.results.find((item) => item.display_name === name);
    if (typeof created?.asset_id === 'number') owned.assetIds.push(created.asset_id);
    if (!created?.success || typeof created.asset_id !== 'number') throw new Error(`Asset creation failed: ${JSON.stringify(response)}`);
    const id = created.asset_id;
    if (options.provider) {
        const assignment = await jsonFrom<{results: BulkResult[]}>(await page.request.post(`${API}/assets/provider`, {data: [{asset_id: id, provider_code: PROVIDER, identifier: ticker, identifier_type: 'TICKER', provider_params: null}]}), 'assign offline provider');
        expect(assignment.results.find((item) => item.asset_id === id)?.success).toBe(true);
    }
    return {id, name, ticker, active, quoteBase, classification};
}

async function readMetadata(page: Page, assetId: number): Promise<AssetMetadata> {
    const items = await jsonFrom<AssetMetadata[]>(await page.request.get(`${API}/assets?asset_ids=${assetId}`), 'read persisted asset metadata');
    const item = items.find((row) => row.asset_id === assetId);
    if (!item) throw new Error(`Owned asset ${assetId} missing from the real metadata endpoint`);
    schemas.FAAssetMetadataResponse.parse(item);
    return item;
}

function normalizedClassification(value: Classification | null | undefined) {
    if (value == null) return null;
    const distribution = (block: {distribution: Distribution} | null | undefined) => (block ? Object.fromEntries(Object.entries(block.distribution).map(([key, weight]) => [key, Number(weight)])) : null);
    return {short_description: value.short_description ?? null, sector: distribution(value.sector_area), geographic: distribution(value.geographic_area)};
}

function expectMetadata(metadata: AssetMetadata, asset: OwnedAsset, name = asset.name, currency = 'EUR', classification = asset.classification): void {
    expect(metadata).toMatchObject({asset_id: asset.id, display_name: name, currency, asset_type: 'ETF', quote_base_quantity: asset.quoteBase});
    expect(normalizedClassification(metadata.classification_params)).toEqual(normalizedClassification(classification));
}

async function expectActivePersisted(page: Page, owned: Owned, asset: OwnedAsset): Promise<void> {
    // /assets/query is an unpaginated list and includes inactive assets by default.
    const items = await jsonFrom<Array<{id: number; active: boolean}>>(await page.request.get(`${API}/assets/query?search=${encodeURIComponent(owned.suffix)}`), 'read persisted active state');
    expect(items.find((item) => item.id === asset.id)?.active).toBe(asset.active);
}

/**
 * API setup follows the BRIM contract specs, but selection uses the uploaded file id
 * and the public Import action, never somebody else's first transaction/broker.
 */
async function openWizardForExistingAsset(page: Page, owned: Owned, asset: OwnedAsset): Promise<Locator> {
    const brokerName = `Inspector broker ${owned.suffix}`;
    const created = await jsonFrom<{results: Array<{broker_id: number | null; name: string; success: boolean}>}>(await page.request.post(`${API}/brokers`, {data: [{name: brokerName, opened_at: '2020-01-01', default_import_plugin: 'broker_generic_csv'}]}), 'create owned import broker');
    const broker = created.results.find((item) => item.name === brokerName);
    if (typeof broker?.broker_id === 'number') owned.brokerIds.push(broker.broker_id);
    if (!broker?.success || typeof broker.broker_id !== 'number') throw new Error(`Broker creation failed: ${JSON.stringify(created)}`);
    const brokerId = broker.broker_id;
    const reportedName = `Unmapped report instrument ${owned.suffix}`;
    const fundingDescription = `Synthetic funding ${owned.suffix}`;
    const buyDescription = `Synthetic inspector purchase ${owned.suffix}`;
    const csv = ['date,type,quantity,amount,currency,asset,description', `2024-01-02,DEPOSIT,0,100,EUR,,${fundingDescription}`, `2024-01-03,BUY,2,-20,EUR,${reportedName},${buyDescription}`, ''].join('\n');
    const upload = await jsonFrom<{file_id: string; target_broker_id: number}>(
        await page.request.post(`${API}/brokers/import/upload`, {
            multipart: {broker_id: String(brokerId), file: {name: `inspector-${owned.suffix}.csv`, mimeType: 'text/csv', buffer: Buffer.from(csv, 'utf8')}},
        }),
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

    // loadBrokerFiles explicitly expands every broker with files. A missing checkbox
    // is a failure, not a reason to click another broker panel.
    const checkbox = page.getByTestId('import-wizard-step2').getByTestId(`dt-row-checkbox-${upload.file_id}`);
    await expect(checkbox).toBeVisible({timeout: UI_TIMEOUT});
    await expect(checkbox).toHaveAttribute('data-state', 'unchecked');
    await checkbox.click();
    await expect(checkbox).toHaveAttribute('data-state', 'checked');
    const [parsedResponse] = await Promise.all([page.waitForResponse((response) => new URL(response.url()).pathname === `${API}/brokers/import/files/${upload.file_id}/parse` && response.request().method() === 'POST', {timeout: 30_000}), page.getByTestId('import-wizard-parse').click()]);
    const parsed = await jsonFrom<{
        file_id: string;
        broker_id: number;
        plugin_code: string;
        transactions: Array<{description: string; type: string; asset_id: number | null; quantity: number | string; cash: {code: string; amount: number | string} | null}>;
        asset_mappings: Array<{fake_asset_id: number; extracted_name: string | null; extracted_symbol: string | null; extracted_isin: string | null}>;
        warnings: unknown[];
        field_todos: unknown[];
        validation_issues: unknown[];
    }>(parsedResponse, 'parse owned Generic CSV');
    expect(parsed).toMatchObject({file_id: upload.file_id, broker_id: brokerId, plugin_code: 'broker_generic_csv'});
    const purchase = parsed.transactions.find((item) => item.description === buyDescription);
    expect(purchase).toMatchObject({type: 'BUY', cash: {code: 'EUR'}});
    expect(Number(purchase?.quantity)).toBe(2);
    expect(Number(purchase?.cash?.amount), 'synthetic BUY spends cash').toBe(-20);
    const funding = parsed.transactions.find((item) => item.description === fundingDescription);
    expect(funding).toMatchObject({type: 'DEPOSIT', cash: {code: 'EUR'}});
    expect(Number(funding?.cash?.amount), 'synthetic DEPOSIT adds cash').toBe(100);
    const mapping = parsed.asset_mappings.find((item) => item.fake_asset_id === purchase?.asset_id);
    expect(mapping).toMatchObject({extracted_name: reportedName, extracted_symbol: null, extracted_isin: null});
    // Both collections belong entirely to our two-row file. No optional-step guessing:
    // no notices/corrections, one instrument, one file => straight to Review.
    expect(parsed.transactions).toHaveLength(2);
    expect(parsed.asset_mappings).toHaveLength(1);
    expect(parsed.warnings).toEqual([]);
    expect(parsed.field_todos).toEqual([]);
    expect(parsed.validation_issues).toEqual([]);
    await waitForParseVerdict(page);
    await page.getByTestId('import-wizard-continue').click();
    const review = page.getByTestId('import-wizard-step4');
    await expect(review).toBeVisible({timeout: UI_TIMEOUT});
    await waitForSettled(review);
    await expect(review.getByTestId('import-wizard-manual-asset-help')).toBeVisible({timeout: UI_TIMEOUT});

    // This wizard contains exactly our one extracted instrument. Always select the
    // intended existing id, regardless of the candidate-matcher's ranking.
    const select = review.getByTestId('import-wizard-resolve-section').getByTestId('asset-select');
    await expect(select).toHaveCount(1);
    await expect(select).toBeVisible({timeout: UI_TIMEOUT});
    await optionsClosed(page);
    await select.getByRole('combobox').click();
    await expect(select.getByRole('listbox')).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
    await select.getByRole('textbox').fill(asset.ticker);
    const option = page.getByTestId(`search-select-option-${asset.id}`);
    await expect(option).toBeVisible({timeout: UI_TIMEOUT});
    if (!asset.active) await expect(option.getByTestId('asset-select-inactive-badge')).toBeVisible();
    await option.click();
    await optionsClosed(page);
    // A name-only extraction offers no ISIN/ticker, so there is no identifier prompt.
    // The inspector button's presence is the positive barrier for resolution.
    const inspector = review.getByTestId(/^import-wizard-inspect-asset-/);
    await expect(inspector).toHaveCount(1);
    await expect(inspector).toBeVisible({timeout: UI_TIMEOUT});
    await expect(review.getByTestId('import-wizard-manual-asset-help')).toBeHidden({timeout: UI_TIMEOUT});
    if (!asset.active) await expect(select.getByTestId('asset-select-selected-inactive-badge')).toBeVisible();
    return inspector;
}

async function openInspector(page: Page, button: Locator, expectedName: string): Promise<void> {
    await button.click();
    const form = page.getByTestId('asset-modal-form');
    await expect(form).toBeVisible({timeout: UI_TIMEOUT});
    await expect(form).toHaveAttribute('data-snapshot-ready', 'true', {timeout: UI_TIMEOUT});
    await expect(page.getByTestId('asset-modal-display-name')).toHaveValue(expectedName, {timeout: UI_TIMEOUT});
}

async function expandClassification(page: Page): Promise<void> {
    const toggle = page.getByTestId('asset-modal-more-info');
    await expect(toggle).toHaveAttribute('data-expanded', /^(true|false)$/);
    if ((await toggle.getAttribute('data-expanded')) !== 'true') await toggle.click();
    await expect(toggle).toHaveAttribute('data-expanded', 'true');
    await expect(page.getByTestId('distribution-editor-sector')).toBeVisible();
    await expect(page.getByTestId('distribution-editor-geographic')).toBeVisible();
}

async function expectDistribution(page: Page, kind: 'sector' | 'geographic', distribution: Distribution): Promise<void> {
    const editor = page.getByTestId(`distribution-editor-${kind}`);
    await expect(editor).toBeVisible({timeout: UI_TIMEOUT});
    await optionsClosed(page);
    const total = editor.getByTestId(`distribution-total-${kind}`);
    await expect(total).toBeVisible({timeout: UI_TIMEOUT});
    await expect(total).toHaveText('100.00%');
    // With selects closed and column filters disabled, these are precisely the
    // DataTable editable-number controls (type=text, inputmode=decimal). Compare the
    // entire owned collection, never choose a row by position or translated label.
    const weights = editor.getByRole('textbox');
    const expectedWeights = Object.values(distribution)
        .map((weight) => Number(weight) * 100)
        .sort((left, right) => left - right);
    await expect(weights).toHaveCount(expectedWeights.length, {timeout: UI_TIMEOUT});
    await expect.poll(() => weights.evaluateAll((inputs) => inputs.map((input) => Number((input as HTMLInputElement).value)).sort((left, right) => left - right)), {timeout: UI_TIMEOUT, message: `${kind} must render the persisted allocation weights`}).toEqual(expectedWeights);
}

async function expectFrontmost(control: Locator, label: string): Promise<void> {
    await expect(control).toBeVisible({timeout: UI_TIMEOUT});
    await control.scrollIntoViewIfNeeded();
    await expect
        .poll(
            () =>
                control.evaluate((element) => {
                    const rect = element.getBoundingClientRect();
                    const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
                    return hit !== null && (hit === element || element.contains(hit));
                }),
            {timeout: 5_000, message: `${label} must receive real pointer events above the asset inspector, not merely exist behind its backdrop`},
        )
        .toBe(true);
}

function isPatchFor(response: Response, assetId: number): boolean {
    if (new URL(response.url()).pathname !== `${API}/assets` || response.request().method() !== 'PATCH') return false;
    const payload = response.request().postDataJSON() as Array<{asset_id: number}>;
    return Array.isArray(payload) && payload.some((item) => item.asset_id === assetId);
}

function patchItem(response: Response, assetId: number): Record<string, unknown> & {classification_params?: Classification | null} {
    const payload = response.request().postDataJSON() as Array<Record<string, unknown> & {classification_params?: Classification | null}>;
    expect(payload).toHaveLength(1);
    const item = payload.find((entry) => entry.asset_id === assetId);
    if (!item) throw new Error(`Save did not PATCH the owned asset ${assetId}: ${JSON.stringify(payload)}`);
    schemas.FAAssetPatchItem.parse(item);
    return item;
}

async function saveInspector(page: Page, asset: OwnedAsset): Promise<ReturnType<typeof patchItem>> {
    const [response] = await Promise.all([page.waitForResponse((candidate) => isPatchFor(candidate, asset.id), {timeout: UI_TIMEOUT}), page.getByTestId('asset-modal-save').click()]);
    const body = await jsonFrom<{results: BulkResult[]}>(response, 'real inspector PATCH');
    expect(body.results.find((item) => item.asset_id === asset.id)?.success).toBe(true);
    const item = patchItem(response, asset.id);
    await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: UI_TIMEOUT});
    await expect(page.getByTestId('import-wizard-step4')).toBeVisible();
    return item;
}

async function closeUnchangedInspector(page: Page): Promise<void> {
    await expect(page.getByTestId('asset-modal-form')).toHaveAttribute('data-dirty', 'false', {timeout: UI_TIMEOUT});
    await page.getByTestId('asset-modal-cancel').click();
    await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: UI_TIMEOUT});
}

async function chooseCurrency(page: Page, currency: string): Promise<void> {
    await optionsClosed(page);
    const group = page.getByTestId('asset-modal-currency-group');
    await group.getByRole('combobox').click();
    await expect(group.getByRole('listbox')).toHaveAttribute('aria-busy', 'false', {timeout: UI_TIMEOUT});
    await group.getByRole('textbox').fill(currency);
    await page.getByTestId(`search-select-option-${currency}`).click();
    await optionsClosed(page);
    await expect(group.getByRole('combobox')).toHaveAttribute('aria-expanded', 'false');
    // ISO currency code is data, not translated UI copy; the closed trigger contains
    // only the selected currency, never the option list.
    await expect(group.getByRole('combobox')).toContainText(currency);
}

async function readStoredPrices(page: Page, assetId: number) {
    const backup = await jsonFrom<{entity: {id: number}; rows: Array<{date: string; close: string | number; currency: string}>}>(await page.request.get(`${API}/backup/asset/${assetId}/prices?format=json`), 'read actual stored price rows');
    expect(backup.entity.id).toBe(assetId);
    return backup.rows.map((row) => ({date: row.date, close: Number(row.close), currency: row.currency})).sort((left, right) => left.date.localeCompare(right.date));
}

function expectNoImplicitProviderIO(owned: Owned, probeCount: number): void {
    expect(owned.probes).toHaveLength(probeCount);
    expect(owned.syncs, 'opening/reopening and unchanged-provider saves must not force a price sync').toEqual([]);
    expect(owned.unexpectedProviderCalls).toEqual([]);
}

test.describe('Group E — import asset inspector', () => {
    test('E1-001: inactive inspector hydrates and preserves metadata on a manual name save', async ({page, owned}, testInfo) => {
        const classification: Classification = {
            short_description: `Stored description ${owned.suffix}`,
            sector_area: {distribution: {Technology: 0.6, Financials: 0.4}},
            geographic_area: {distribution: {USA: 0.75, ITA: 0.25}},
        };
        const asset = await createAsset(page, owned, 'stored', {classification, quoteBase: 100, active: false});
        const persistedBefore = await readMetadata(page, asset.id);
        expectMetadata(persistedBefore, asset);
        await expectActivePersisted(page, owned, asset);
        const inspector = await openWizardForExistingAsset(page, owned, asset);
        await openInspector(page, inspector, asset.name);
        // openInspector already waited for data-snapshot-ready. Observe the initialized
        // fields without asserting yet: the baseline's blank description must not stop
        // the test BEFORE it demonstrates the destructive name-only PATCH and real GET.
        const openedDescription = await page.getByTestId('asset-modal-description').inputValue();
        const openedQuoteBase = await page.getByTestId('asset-modal-quote-base-quantity').inputValue();

        const editedName = `${asset.name} edited`;
        await page.getByTestId('asset-modal-display-name').fill(editedName);
        await expect(page.getByTestId('asset-modal-display-name')).toHaveValue(editedName);
        await expectFrontmost(page.getByTestId('asset-modal-save'), 'Name-only Save');
        const [response, patch] = await Promise.all([page.waitForResponse((candidate) => isPatchFor(candidate, asset.id), {timeout: UI_TIMEOUT}), saveInspector(page, asset)]);
        const persistedAfter = await readMetadata(page, asset.id);
        await openInspector(page, inspector, editedName);
        const reopenedDescription = await page.getByTestId('asset-modal-description').inputValue();
        await testInfo.attach('summary-name-edit-persistence.json', {
            contentType: 'application/json',
            body: JSON.stringify(
                {
                    asset_id: asset.id,
                    persisted_before: persistedBefore,
                    opened_form: {description: openedDescription, quote_base_quantity: openedQuoteBase},
                    patch_status: response.status(),
                    patch_request: patch,
                    patch_response: await response.json(),
                    persisted_after: persistedAfter,
                    reopened_form: {description: reopenedDescription},
                },
                null,
                2,
            ),
        });

        // The primary baseline failure is now DB data loss, with the actual successful
        // PATCH and both metadata GETs retained above, not merely an empty UI field.
        expect(normalizedClassification(persistedAfter.classification_params), 'REAL metadata GET after a name-only inspector save must retain all three classification fields').toEqual(normalizedClassification(classification));
        expectMetadata(persistedAfter, asset, editedName);
        expect(patch).toMatchObject({asset_id: asset.id, display_name: editedName, quote_base_quantity: 100, active: false});
        expect(patch).not.toHaveProperty('classification_params');
        expect(openedDescription).toBe(classification.short_description);
        expect(openedQuoteBase).toBe('100');
        await expectActivePersisted(page, owned, asset);
        await expect(page.getByTestId('asset-modal-description')).toHaveValue(classification.short_description!);
        await expect(page.getByTestId('asset-modal-quote-base-quantity')).toHaveValue('100');
        await expect(page.getByTestId('asset-active-toggle')).toHaveAttribute('aria-checked', 'false');
        await expandClassification(page);
        await expectDistribution(page, 'sector', classification.sector_area!.distribution);
        await expectDistribution(page, 'geographic', classification.geographic_area!.distribution);
        await closeUnchangedInspector(page);
        expectNoImplicitProviderIO(owned, 0);
    });

    test('E1-002: Ask Provider distributions survive real save and reopen without refetch', async ({page, owned}) => {
        const asset = await createAsset(page, owned, 'provider', {provider: true, quoteBase: 25});
        const classification: Classification = {
            sector_area: {distribution: {Technology: 0.7, Financials: 0.3}},
            geographic_area: {distribution: {USA: 0.6, ITA: 0.4}},
        };
        const providerPatch = {asset_id: 0, classification_params: classification};
        schemas.FAAssetPatchItem.parse(providerPatch);
        owned.metadata.set(asset.ticker, providerPatch);
        const before = await readMetadata(page, asset.id);
        expectMetadata(before, asset);
        expect(before.provider_code).toBe(PROVIDER);
        const inspector = await openWizardForExistingAsset(page, owned, asset);
        await openInspector(page, inspector, asset.name);
        await expandClassification(page);
        await expect(page.getByTestId('distribution-add-sector')).toBeVisible();
        await expect(page.getByTestId('distribution-add-geographic')).toBeVisible();
        await expect(page.getByTestId('distribution-editor-sector').getByRole('textbox')).toHaveCount(0);
        await expect(page.getByTestId('distribution-editor-geographic').getByRole('textbox')).toHaveCount(0);
        expectNoImplicitProviderIO(owned, 0);

        // Global Ask Provider covers both empty distributions in one dry-run request;
        // no per-section button handles are required in the baseline build.
        await page.getByTestId('asset-modal-ask-provider').click();
        await expectDistribution(page, 'sector', classification.sector_area!.distribution);
        await expectDistribution(page, 'geographic', classification.geographic_area!.distribution);
        // A probe is a dry run. Only the user's real Save may persist its proposal.
        expect((await readMetadata(page, asset.id)).classification_params).toBeNull();
        const patch = await saveInspector(page, asset);
        expect(patch.quote_base_quantity).toBe(25);
        expect(normalizedClassification(patch.classification_params)).toEqual(normalizedClassification(classification));
        expectMetadata(await readMetadata(page, asset.id), asset, asset.name, 'EUR', classification);
        const expectedProbe: ProbeRequest = {provider_code: PROVIDER, identifier: asset.ticker, identifier_type: 'TICKER', provider_params: null, operations: ['metadata']};
        expect(owned.probes.map((request) => ({...request, provider_params: request.provider_params ?? null}))).toEqual([expectedProbe]);

        const beforeReopen = owned.probes.length;
        await openInspector(page, inspector, asset.name);
        await expect(page.getByTestId('asset-modal-quote-base-quantity')).toHaveValue('25');
        await expandClassification(page);
        await expectDistribution(page, 'sector', classification.sector_area!.distribution);
        await expectDistribution(page, 'geographic', classification.geographic_area!.distribution);
        await closeUnchangedInspector(page);
        expectNoImplicitProviderIO(owned, beforeReopen);
    });

    test('E1-003: clearing description keeps the other classification fields intact', async ({page, owned}) => {
        const classification: Classification = {
            short_description: `Stored description ${owned.suffix}`,
            sector_area: {distribution: {Technology: 0.6, Financials: 0.4}},
            geographic_area: {distribution: {USA: 0.75, ITA: 0.25}},
        };
        const asset = await createAsset(page, owned, 'clear-description', {classification, quoteBase: 100, active: false});
        expectMetadata(await readMetadata(page, asset.id), asset);
        await expectActivePersisted(page, owned, asset);

        const inspector = await openWizardForExistingAsset(page, owned, asset);
        await openInspector(page, inspector, asset.name);
        await expect(page.getByTestId('asset-modal-description')).toHaveValue(classification.short_description!);
        await expandClassification(page);
        await expectDistribution(page, 'sector', classification.sector_area!.distribution);
        await expectDistribution(page, 'geographic', classification.geographic_area!.distribution);

        await page.getByTestId('asset-modal-description').fill('');
        await expect(page.getByTestId('asset-modal-description')).toHaveValue('');
        const patch = await saveInspector(page, asset);
        expect(patch).toMatchObject({asset_id: asset.id, classification_params: {short_description: null}});
        expect(patch.classification_params).toEqual({short_description: null});
        const cleared = await readMetadata(page, asset.id);
        expectMetadata(cleared, asset, asset.name, 'EUR', {
            sector_area: classification.sector_area,
            geographic_area: classification.geographic_area,
        });
        expect(cleared.classification_params?.short_description).toBeNull();

        await openInspector(page, inspector, asset.name);
        await expect(page.getByTestId('asset-modal-description')).toHaveValue('');
        await expandClassification(page);
        await expectDistribution(page, 'sector', classification.sector_area!.distribution);
        await expectDistribution(page, 'geographic', classification.geographic_area!.distribution);
        await closeUnchangedInspector(page);

        const totalClear = {asset_id: asset.id, classification_params: null};
        schemas.FAAssetPatchItem.parse(totalClear);
        const totalClearResponse = await jsonFrom<{results: BulkResult[]}>(await page.request.patch(`${API}/assets`, {data: [totalClear]}), 'clear classification_params via real API');
        expect(totalClearResponse.results.find((item) => item.asset_id === asset.id)?.success).toBe(true);
        const wiped = await readMetadata(page, asset.id);
        expectMetadata(wiped, asset, asset.name, 'EUR', null);
        expect(wiped.classification_params).toBeNull();
        expectNoImplicitProviderIO(owned, 0);
    });

    test('E2-001: currency blocker cancel preserves data; confirm wipes only the inspected asset', async ({page, owned}) => {
        const asset = await createAsset(page, owned, 'currency');
        const control = await createAsset(page, owned, 'unrelated control');
        const prices = [
            {date: '2024-01-04', close: 101, currency: 'EUR'},
            {date: '2024-01-05', close: 102, currency: 'EUR'},
        ];
        const controlPrices = [{date: '2024-01-04', close: 203, currency: 'EUR'}];
        const seeded = await jsonFrom<{results: Array<{asset_id: number; count: number}>}>(
            await page.request.post(`${API}/assets/prices`, {
                data: [
                    {asset_id: asset.id, prices},
                    {asset_id: control.id, prices: controlPrices},
                ],
            }),
            'seed owned market data',
        );
        expect(seeded.results.find((item) => item.asset_id === asset.id)?.count).toBe(prices.length);
        expect(seeded.results.find((item) => item.asset_id === control.id)?.count).toBe(controlPrices.length);
        expect(await readStoredPrices(page, asset.id)).toEqual(prices);
        expect(await readStoredPrices(page, control.id)).toEqual(controlPrices);

        const inspector = await openWizardForExistingAsset(page, owned, asset);
        await openInspector(page, inspector, asset.name);
        const currencyModal = page.getByTestId('currency-change-modal');
        const blockedSave = async () => {
            await chooseCurrency(page, 'USD');
            const [response] = await Promise.all([page.waitForResponse((candidate) => isPatchFor(candidate, asset.id), {timeout: UI_TIMEOUT}), page.getByTestId('asset-modal-save').click()]);
            expect(response.status()).toBe(409);
            expect(patchItem(response, asset.id)).toMatchObject({asset_id: asset.id, currency: 'USD'});
            const body = (await response.json()) as {detail: {results: BulkResult[]}};
            const result = body.detail.results.find((item) => item.asset_id === asset.id);
            expect(result?.success).toBe(false);
            expect(result?.message).toContain('CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA');
            expect(result?.message).toContain(`|prices=${prices.length}|`);
            expect(result?.message).toContain('|from=EUR|to=USD');
            await expect(currencyModal).toBeVisible({timeout: UI_TIMEOUT});
            await expect(currencyModal.getByTestId('currency-change-summary-prices')).toBeVisible();
            await expect(page.getByTestId('asset-modal-form')).toBeVisible();
        };
        await blockedSave();
        await expectFrontmost(currencyModal.getByTestId('currency-change-cancel'), 'Currency cancel');
        await expectFrontmost(currencyModal.getByTestId('currency-change-confirm'), 'Currency confirm');
        const beforeCancel = owned.mutations.length;
        await currencyModal.getByTestId('currency-change-cancel').click();
        await expect(currencyModal).toBeHidden({timeout: UI_TIMEOUT});
        expectMetadata(await readMetadata(page, asset.id), asset);
        expect(await readStoredPrices(page, asset.id)).toEqual(prices);
        expect(await readStoredPrices(page, control.id)).toEqual(controlPrices);
        expect(owned.mutations.slice(beforeCancel), 'cancel emits neither wipe nor another PATCH').toEqual([]);

        await blockedSave();
        await expectFrontmost(currencyModal.getByTestId('currency-change-confirm'), 'Currency confirm');
        const beforeConfirm = owned.mutations.length;
        const wipePath = `${API}/assets/${asset.id}/market-data/wipe`;
        const [wipeResponse, patchResponse] = await Promise.all([
            page.waitForResponse((response) => new URL(response.url()).pathname === wipePath && response.request().method() === 'POST', {timeout: UI_TIMEOUT}),
            page.waitForResponse((response) => isPatchFor(response, asset.id), {timeout: UI_TIMEOUT}),
            currencyModal.getByTestId('currency-change-confirm').click(),
        ]);
        expect(wipeResponse.ok(), await wipeResponse.text()).toBeTruthy();
        const patched = await jsonFrom<{results: BulkResult[]}>(patchResponse, 'post-wipe real currency PATCH');
        expect(patched.results.find((item) => item.asset_id === asset.id)?.success).toBe(true);
        expect(patchItem(patchResponse, asset.id)).toMatchObject({asset_id: asset.id, currency: 'USD', quote_base_quantity: asset.quoteBase});
        await expect(currencyModal).toBeHidden({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('asset-modal-form')).toBeHidden({timeout: UI_TIMEOUT});
        expect(owned.mutations.slice(beforeConfirm).map(({method, path}) => ({method, path}))).toEqual([
            {method: 'POST', path: wipePath},
            {method: 'PATCH', path: `${API}/assets`},
        ]);
        expectMetadata(await readMetadata(page, asset.id), asset, asset.name, 'USD');
        expect(await readStoredPrices(page, asset.id)).toEqual([]);
        expect(await readStoredPrices(page, control.id)).toEqual(controlPrices);
        expectMetadata(await readMetadata(page, control.id), control);

        await openInspector(page, inspector, asset.name);
        const currency = page.getByTestId('asset-modal-currency-group').getByRole('combobox');
        await expect(currency).toHaveAttribute('aria-expanded', 'false');
        await expect(currency).toContainText('USD');
        await closeUnchangedInspector(page);
        expectNoImplicitProviderIO(owned, 0);
    });

    test('E2-002: provider comparison is above inspector and persists only selected scalar changes', async ({page, owned}) => {
        const asset = await createAsset(page, owned, 'comparison', {provider: true});
        const proposedName = `${asset.name} provider`;
        // Both scalar fields have stored values, so this always creates a real diff
        // even on the pre-fix build that fails to hydrate classification metadata.
        const providerPatch = {asset_id: 0, display_name: proposedName, currency: 'USD'};
        schemas.FAAssetPatchItem.parse(providerPatch);
        owned.metadata.set(asset.ticker, providerPatch);
        const inspector = await openWizardForExistingAsset(page, owned, asset);
        await openInspector(page, inspector, asset.name);
        expectNoImplicitProviderIO(owned, 0);
        await page.getByTestId('asset-modal-ask-provider').click();
        const comparison = page.getByTestId('comparison-modal');
        await expect(comparison).toBeVisible({timeout: UI_TIMEOUT});
        await expect(comparison.getByTestId('comparison-checkbox-display_name')).toBeChecked();
        await expect(comparison.getByTestId('comparison-checkbox-currency')).toBeChecked();
        await expect(page.getByTestId('asset-modal-form')).toBeVisible();
        await expectFrontmost(comparison.getByTestId('comparison-deselect-all'), 'Provider difference selection');
        await comparison.getByTestId('comparison-deselect-all').click();
        await expect(comparison.getByTestId('comparison-checkbox-display_name')).not.toBeChecked();
        await expect(comparison.getByTestId('comparison-checkbox-currency')).not.toBeChecked();
        await comparison.getByTestId('comparison-checkbox-display_name').check();
        await expectFrontmost(comparison.getByTestId('comparison-apply'), 'Provider comparison apply');
        await comparison.getByTestId('comparison-apply').click();
        await expect(comparison).toBeHidden({timeout: UI_TIMEOUT});
        await expect(page.getByTestId('asset-modal-display-name')).toHaveValue(proposedName);
        expectMetadata(await readMetadata(page, asset.id), asset);

        const patch = await saveInspector(page, asset);
        expect(patch).toMatchObject({asset_id: asset.id, display_name: proposedName, currency: 'EUR', quote_base_quantity: asset.quoteBase});
        expectMetadata(await readMetadata(page, asset.id), asset, proposedName);
        const beforeReopen = owned.probes.length;
        expect(beforeReopen).toBe(1);
        await openInspector(page, inspector, proposedName);
        const currency = page.getByTestId('asset-modal-currency-group').getByRole('combobox');
        await expect(currency).toHaveAttribute('aria-expanded', 'false');
        await expect(currency).toContainText('EUR');
        await closeUnchangedInspector(page);
        expectNoImplicitProviderIO(owned, beforeReopen);
    });
});
