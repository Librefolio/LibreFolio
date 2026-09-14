import {expect, test, type Locator, type Page} from '../fixtures/playwright';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import type {ToolComputeRequest, ToolComputeResponse, ToolInput, ToolOutput} from '../../src/lib/features/tools/contracts';
import {
    COMPUTE_PATH,
    REFERENCE_DATE,
    TEST_ALICE,
    TEST_BOB,
    TEST_CAROL,
    TEST_DAVE,
    TEST_EVE,
    exactSourceRequest,
    gate,
    isComputeRequest,
    only,
    openTool,
    principal,
    routeAllocationSource,
    runAndCaptureCompute,
    selectCurrency,
    setDate,
    soleIndexedField,
    sourceDateOf,
    sourcePayload,
    sourceRequestBody,
    type IndexedField,
    type SourceAssetWire,
} from './allocation-tool-fixtures';

const TOOL_CODE = 'pac_allocator';
const TOOL_ROOT = 'pac-allocator-tool';

type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;

const ALPHA: SourceAssetWire = {
    asset_id: 940_001,
    instrument_key: 'asset:pac-r4-alpha',
    candidate_key: 'candidate:pac-r4-alpha',
    name: 'PAC R4 Alpha',
    ticker: 'P4A',
    asset_type: 'ETF',
    icon_url: null,
    active: true,
    usage_scope: 'owned',
    quote: {
        raw_price: '123.45',
        currency: 'USD',
        quote_base_quantity: 100,
        reference_date: REFERENCE_DATE,
        source: 'pac-r4-fixture',
        days_before_requested: 0,
    },
    contexts: [
        {
            context_key: 'asset:pac-r4-alpha:broker:1',
            broker_id: 94_001,
            broker_name: 'PAC R4 broker Alpha',
            broker_icon_url: null,
            broker_portal_url: null,
            broker_default_import_plugin: null,
            ownership_share_percent: '100',
            custody_quantity: '17',
        },
    ],
};

const BETA: SourceAssetWire = {
    asset_id: 940_002,
    instrument_key: 'asset:pac-r4-beta',
    candidate_key: 'candidate:pac-r4-beta',
    name: 'PAC R4 Beta',
    ticker: 'P4B',
    asset_type: 'STOCK',
    icon_url: null,
    active: true,
    usage_scope: 'owned',
    quote: {
        raw_price: '88.5',
        currency: 'CHF',
        quote_base_quantity: 1,
        reference_date: REFERENCE_DATE,
        source: 'pac-r4-fixture',
        days_before_requested: 0,
    },
    contexts: [
        {
            context_key: 'asset:pac-r4-beta:broker:2',
            broker_id: 94_002,
            broker_name: 'PAC R4 broker Beta',
            broker_icon_url: null,
            broker_portal_url: null,
            broker_default_import_plugin: null,
            ownership_share_percent: '100',
            custody_quantity: '9',
        },
    ],
};

function pacItem(body: ToolComputeRequest) {
    return only(body.items, (item) => item.tool_code === TOOL_CODE, 'PAC compute item');
}

async function useManualCash(page: Page): Promise<IndexedField> {
    await page.getByTestId('pac-cash-use-manual').click();
    const fields = page.getByTestId(/^pac-cash-amount-\d+$/);
    await expect(fields).toHaveCount(1);
    return soleIndexedField(fields, 'pac-cash-amount', 'manual cash amount');
}

async function addContribution(page: Page, excludedTestIds: ReadonlySet<string> = new Set()): Promise<IndexedField> {
    await page.getByTestId('pac-add-contributions').click();
    const fields = page.getByTestId(/^pac-contributions-amount-\d+$/);
    await expect(fields).toHaveCount(excludedTestIds.size + 1);
    return soleIndexedField(fields, 'pac-contributions-amount', 'new contribution amount', excludedTestIds);
}

async function addManualAsset(page: Page): Promise<{name: IndexedField; target: Locator; remove: Locator}> {
    await page.getByTestId('pac-add-manual-asset').click();
    const name = await soleIndexedField(page.getByTestId(/^pac-asset-name-\d+$/), 'pac-asset-name', 'manual PAC Asset');
    await expect(name.field).toBeVisible();

    const targets = page.getByTestId(/^allocation-target-manual:asset:/);
    await expect(targets).toHaveCount(1);
    const targetTestId = await targets.getAttribute('data-testid');
    if (targetTestId === null) throw new Error('manual PAC target has no data-testid');
    const target = page.getByTestId(targetTestId);
    await expect(target).toBeVisible();

    const remove = page.getByTestId(`pac-remove-asset-${name.index}`);
    await expect(remove).toBeVisible();
    return {name, target, remove};
}

async function expectCurrentPrices(page: Page, expected: readonly {currency: string; amount: string}[]): Promise<void> {
    const prices = page.getByTestId(/^pac-current-price-\d+$/);
    await expect(prices).toHaveCount(expected.length);
    await expect
        .poll(async () => {
            const texts = await prices.allTextContents();
            return expected.every(({currency, amount}) => texts.some((text) => text.includes(currency) && text.includes(amount)));
        })
        .toBe(true);
}

test.setTimeout(90_000);

test.describe('PAC allocator P1', () => {
    test('keeps source discovery and manual setup usable while a refresh is pending', async ({page}, testInfo) => {
        let holdRefresh = false;
        const refreshFetched = gate();
        const releaseRefresh = gate();
        await routeAllocationSource(page, async (request) => {
            if (holdRefresh) {
                refreshFetched.open();
                await releaseRefresh.promise;
            }
            return sourcePayload(request.allocation_source.as_of_date, [ALPHA, BETA]);
        });
        const user = principal(testInfo.project.name, TEST_BOB, TEST_CAROL);
        const tool = await openTool(page, user, TOOL_CODE, TOOL_ROOT);

        const alphaCard = page.getByTestId(`pac-owned-asset-${ALPHA.asset_id}`);
        const betaCard = page.getByTestId(`pac-owned-asset-${BETA.asset_id}`);
        await expect(alphaCard).toBeEnabled({timeout: 20_000});
        await expect(betaCard).toBeEnabled();

        const search = page.getByTestId('pac-owned-assets-search');
        for (const query of [ALPHA.name, ALPHA.ticker, ALPHA.asset_type, ALPHA.contexts.map((context) => context.broker_name).join(' ')]) {
            if (query === null) throw new Error('PAC Alpha search fixture must provide every searchable field');
            await search.fill(query);
            await expect(alphaCard).toBeVisible();
            await expect(betaCard).toHaveCount(0);
        }
        for (const query of [BETA.name, BETA.ticker, BETA.asset_type, BETA.contexts.map((context) => context.broker_name).join(' ')]) {
            if (query === null) throw new Error('PAC Beta search fixture must provide every searchable field');
            await search.fill(query);
            await expect(betaCard).toBeVisible();
            await expect(alphaCard).toHaveCount(0);
        }
        await search.fill('');
        await expect(alphaCard).toBeVisible();
        await expect(betaCard).toBeVisible();

        await alphaCard.click();
        const alphaTarget = page.getByTestId(`allocation-target-${ALPHA.instrument_key}`);
        await expect(alphaTarget).toBeVisible();
        await expect(alphaTarget).toHaveAttribute('aria-label', /\S/);

        holdRefresh = true;
        const refresh = page.getByTestId('pac-owned-assets-refresh');
        await refresh.click();
        await refreshFetched.promise;
        let manual: IndexedField | null = null;
        try {
            await expect(tool).toHaveAttribute('data-busy', 'false');
            await expect(refresh).toBeDisabled();
            await expect(alphaCard).toBeDisabled();

            const addManual = page.getByTestId('pac-add-manual-asset');
            await expect(addManual).toBeEnabled();
            await addManual.click();
            manual = await soleIndexedField(page.getByTestId(/^pac-asset-name-\d+$/), 'pac-asset-name', 'manual Asset created during refresh');
            await manual.field.fill('PAC R4 refresh-safe manual Asset');
            await expect(manual.field).toHaveValue('PAC R4 refresh-safe manual Asset');
        } finally {
            releaseRefresh.open();
        }

        if (manual === null) throw new Error('manual Asset was not created during the source refresh');
        await expect(refresh).toBeEnabled();
        await expect(manual.field).toHaveValue('PAC R4 refresh-safe manual Asset');
        await expect(alphaTarget).toBeVisible();
    });

    test('removes fresh manual Assets immediately and guards row edits or their last target', async ({page}, testInfo) => {
        await routeAllocationSource(page, (request) => sourcePayload(request.allocation_source.as_of_date, [ALPHA]));
        const user = principal(testInfo.project.name, TEST_DAVE, TEST_EVE);
        await openTool(page, user, TOOL_CODE, TOOL_ROOT);
        await expect(page.getByTestId(`pac-owned-asset-${ALPHA.asset_id}`)).toBeEnabled({timeout: 20_000});

        const fresh = await addManualAsset(page);
        await fresh.remove.click();
        await expect(fresh.name.field).toHaveCount(0);
        await expect(fresh.target).toHaveCount(0);
        await expect(page.getByTestId('pac-customized-removal-confirm')).toHaveCount(0);

        const edited = await addManualAsset(page);
        await edited.name.field.fill('PAC R4 customized manual Asset');
        await expect(edited.name.field).toHaveValue('PAC R4 customized manual Asset');
        await edited.remove.click();
        const confirmation = page.getByTestId('pac-customized-removal-confirm');
        await expect(confirmation).toBeVisible();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirmation).toHaveCount(0);
        await expect(edited.name.field).toHaveValue('PAC R4 customized manual Asset');

        await edited.remove.click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(edited.name.field).toHaveCount(0);
        await expect(edited.target).toHaveCount(0);
        await expect(confirmation).toHaveCount(0);

        const targeted = await addManualAsset(page);
        await targeted.target.fill('100');
        await expect(targeted.target).toHaveValue('100');
        await targeted.remove.click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(targeted.name.field).toHaveCount(0);
        await expect(targeted.target).toHaveCount(0);
        await expect(confirmation).toHaveCount(0);
    });

    test('keeps canonical Assets separate from exact targets and reports a same-currency P1 budget', async ({page}, testInfo) => {
        await routeAllocationSource(page, (request) => sourcePayload(request.allocation_source.as_of_date, [ALPHA, BETA]));
        const user = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        const tool = await openTool(page, user, TOOL_CODE, TOOL_ROOT);

        await expect(page.getByTestId('portfolio-rebalancer-tool')).toHaveCount(0);
        await selectCurrency(page, 'pac-report-currency', 'EUR');
        const datedSource = page.waitForRequest((request) => sourceDateOf(request) === REFERENCE_DATE, {timeout: 20_000});
        await setDate(page, 'pac-analysis-date', REFERENCE_DATE);
        const sourceRequest = await datedSource;
        expect(sourceRequestBody(sourceRequest)).toEqual(exactSourceRequest(REFERENCE_DATE));

        const alphaCard = page.getByTestId(`pac-owned-asset-${ALPHA.asset_id}`);
        const betaCard = page.getByTestId(`pac-owned-asset-${BETA.asset_id}`);
        await expect(alphaCard).toBeEnabled({timeout: 20_000});
        await expect(betaCard).toBeEnabled();
        await alphaCard.click();
        await betaCard.click();

        await expect(page.getByTestId('pac-asset-editor')).toHaveCount(2);
        await expect(page.getByTestId('allocation-target-editor')).toHaveAttribute('data-service', 'pac');
        const targetEditor = page.getByTestId('allocation-target-editor');
        await expect(targetEditor.getByTestId('dt-header-instrument')).toBeVisible();
        await expect(targetEditor.getByTestId('dt-header-target')).toBeVisible();
        await expect(targetEditor.getByTestId('dt-header-bar')).toBeVisible();

        const alphaTarget = page.getByTestId(`allocation-target-${ALPHA.instrument_key}`);
        const betaTarget = page.getByTestId(`allocation-target-${BETA.instrument_key}`);
        await alphaTarget.fill('25x.5percent');
        await betaTarget.fill('74y.5percent');
        await expect(alphaTarget).toHaveValue('25.5');
        await expect(betaTarget).toHaveValue('74.5');
        await expect(page.getByTestId('allocation-target-remaining')).toContainText('0%');

        const cash = await useManualCash(page);
        await cash.field.fill('1x0');
        await selectCurrency(page, `pac-cash-currency-${cash.index}`, 'USD');
        const fx = page.getByTestId('allocation-valuation-rates');
        await expect(fx).toBeVisible();
        await expect(fx.getByTestId('allocation-rate-add')).toBeVisible();
        await expect(fx).toContainText('USD');
        await expect(fx).toContainText('EUR');
        await selectCurrency(page, `pac-cash-currency-${cash.index}`, 'EUR');
        await expect(cash.field).toHaveValue('10');
        await expect(fx).toHaveCount(0);

        const firstContribution = await addContribution(page);
        await firstContribution.field.fill('2x.25');
        await expect(page.getByTestId(`pac-contributions-currency-${firstContribution.index}-trigger`)).toContainText('EUR');
        await page.getByTestId(`pac-contributions-monetary-step-${firstContribution.index}`).fill('0a.01');
        await expect(firstContribution.field).toHaveValue('2.25');

        const secondContribution = await addContribution(page, new Set([firstContribution.testId]));
        await secondContribution.field.fill('3y.75');
        await expect(page.getByTestId(`pac-contributions-currency-${secondContribution.index}-trigger`)).toContainText('EUR');
        await page.getByTestId(`pac-contributions-monetary-step-${secondContribution.index}`).fill('0b.01');
        await expect(secondContribution.field).toHaveValue('3.75');

        const funding = page.getByTestId('allocation-funding-EUR');
        await expect(funding).toBeVisible();
        await expect(funding).toContainText('10');
        await expect(funding).toContainText('2.25 + 3.75');
        await expectCurrentPrices(page, [
            {currency: 'USD', amount: '123.45'},
            {currency: 'CHF', amount: '88.5'},
        ]);

        // PAC prices are source context only. Foreign quote currencies do not
        // create valuation-rate requirements for a same-currency EUR budget.
        await expect(page.getByTestId('allocation-valuation-rates')).toHaveCount(0);

        const {request, response} = await runAndCaptureCompute(page, () => page.getByTestId('pac-analyze').click());

        const requestBody = request.postDataJSON() as ToolComputeRequest;
        expect(requestBody.items).toHaveLength(1);
        const item = pacItem(requestBody);
        expect(item).toMatchObject({
            tool_code: TOOL_CODE,
            contract_version: '1.0.0',
            implementation_version: '1.0.0',
        });
        const parameters = item.parameters as PacInput;
        expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'assets', 'cash_balances', 'contributions', 'operation', 'report_currency', 'targets', 'valuation_rates']);
        expect(parameters.operation).toBe('analyze');
        expect(parameters.report_currency).toBe('EUR');
        expect(parameters.as_of_date).toBe(REFERENCE_DATE);
        expect(parameters.cash_balances).toEqual([{currency: 'EUR', amount: '10'}]);
        expect(parameters.contributions).toEqual([
            {currency: 'EUR', amount: '2.25', monetary_step: '0.01'},
            {currency: 'EUR', amount: '3.75', monetary_step: '0.01'},
        ]);
        expect(parameters.valuation_rates).toEqual([]);
        const assets = parameters.assets ?? [];
        const targets = parameters.targets ?? [];
        expect(assets).toHaveLength(2);
        expect(only(assets, (asset) => asset.instrument_key === ALPHA.instrument_key, 'PAC Alpha input')).toEqual({
            instrument_key: ALPHA.instrument_key,
            name: ALPHA.name,
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        expect(only(assets, (asset) => asset.instrument_key === BETA.instrument_key, 'PAC Beta input')).toEqual({
            instrument_key: BETA.instrument_key,
            name: BETA.name,
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        expect(targets).toHaveLength(2);
        expect(only(targets, (target) => target.instrument_key === ALPHA.instrument_key, 'PAC Alpha target')).toEqual({
            instrument_key: ALPHA.instrument_key,
            target_percent: '25.5',
        });
        expect(only(targets, (target) => target.instrument_key === BETA.instrument_key, 'PAC Beta target')).toEqual({
            instrument_key: BETA.instrument_key,
            target_percent: '74.5',
        });
        for (const absent of ['holdings', 'orders', 'solver', 'trade_feasibility', 'optimization', 'draft_revision']) {
            expect(parameters).not.toHaveProperty(absent);
        }

        expect(response.status(), response.status() === 200 ? '' : await response.text()).toBe(200);
        const responseBody = (await response.json()) as ToolComputeResponse;
        expect(responseBody.request_id).toBe(requestBody.request_id);
        expect(responseBody.success_count).toBe(1);
        expect(responseBody.failed_count).toBe(0);
        const platformResult = only(responseBody.results, (result) => result.correlation_id === item.correlation_id && result.tool_code === TOOL_CODE, 'PAC compute result');
        expect(platformResult.status).toBe('success');
        if (platformResult.status !== 'success') throw new Error(`PAC compute failed with ${platformResult.error.code}`);
        expect(platformResult).toMatchObject({
            tool_code: item.tool_code,
            contract_version: item.contract_version,
            implementation_version: item.implementation_version,
            schema_fingerprint: item.schema_fingerprint,
            correlation_id: item.correlation_id,
        });
        const output = platformResult.result as PacOutput;
        expect(output.availability).toBe('ready');
        expect(output.result_kind).toBe('pac_budget_analysis');
        expect(output).not.toHaveProperty('trade_feasibility');
        expect(output).not.toHaveProperty('optimization');
        expect(output.totals.existing_cash_reporting).toMatchObject({availability: 'available', value: {currency: 'EUR', amount: '10'}});
        expect(output.totals.contributions_reporting).toMatchObject({availability: 'available', value: {currency: 'EUR', amount: '6'}});
        expect(output.totals.investable_budget_reporting).toMatchObject({availability: 'available', value: {currency: 'EUR', amount: '16'}});
        const alphaAllocation = only(output.allocations, (allocation) => allocation.instrument_key === ALPHA.instrument_key, 'PAC Alpha allocation');
        const betaAllocation = only(output.allocations, (allocation) => allocation.instrument_key === BETA.instrument_key, 'PAC Beta allocation');
        expect(alphaAllocation).toMatchObject({
            target_percent: {availability: 'available', value: '25.5'},
            ideal_allocation_reporting: {availability: 'available', value: {currency: 'EUR', amount: '4.08'}},
        });
        expect(betaAllocation).toMatchObject({
            target_percent: {availability: 'available', value: '74.5'},
            ideal_allocation_reporting: {availability: 'available', value: {currency: 'EUR', amount: '11.92'}},
        });
        expect(output.cash_pools).toMatchObject({
            availability: 'available',
            value: [
                {
                    currency: 'EUR',
                    existing_amount: '10',
                    contribution_amount: '6',
                    combined_amount: '16',
                },
            ],
        });

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        const result = page.getByTestId('pac-result-panel');
        await expect(result).toBeVisible();
        await expect(result.getByTestId('allocation-diagnostics')).toBeVisible();
        await expect(result.getByTestId('dt-header-asset')).toBeVisible();
        await expect(result.getByTestId('dt-header-target')).toBeVisible();
        await expect(result.getByTestId('dt-header-allocation')).toBeVisible();
        await expect(result).toContainText(ALPHA.name);
        await expect(result).toContainText(BETA.name);
        await expect(result).toContainText('25.5%');
        await expect(result).toContainText('74.5%');
        await expect(result).toContainText('4.08 EUR');
        await expect(result).toContainText('11.92 EUR');
        await expect(page.getByTestId('allocation-funding-total-EUR')).toContainText('16');

        await alphaCard.click();
        await expect(page.getByTestId('pac-customized-removal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('pac-customized-removal-confirm')).toHaveCount(0);
        await expect(alphaCard).toHaveAttribute('aria-pressed', 'true');
        await expect(alphaTarget).toHaveValue('25.5');

        await alphaTarget.fill('25.4');
        await expect(page.getByTestId('pac-result-stale')).toBeVisible();
    });

    test('ignores a response superseded by refreshed source facts without overwriting the draft or prior result', async ({page}, testInfo) => {
        let refreshed = false;
        let holdRefresh = false;
        const refreshFetched = gate();
        const releaseRefresh = gate();
        const staleAsset = (price: string, name: string): SourceAssetWire => ({
            ...ALPHA,
            asset_id: 940_011,
            instrument_key: 'asset:pac-r4-stale',
            candidate_key: 'candidate:pac-r4-stale',
            name,
            quote: {...ALPHA.quote, raw_price: price, currency: 'EUR'},
            contexts: ALPHA.contexts.map((context) => ({
                ...context,
                context_key: 'asset:pac-r4-stale:broker:1',
            })),
        });
        await routeAllocationSource(page, async (request) => {
            if (holdRefresh) {
                refreshFetched.open();
                await releaseRefresh.promise;
            }
            return sourcePayload(request.allocation_source.as_of_date, [refreshed ? staleAsset('20.000000000001', 'PAC R4 refreshed source') : staleAsset('10.000000000001', 'PAC R4 original source')]);
        });

        const user = principal(testInfo.project.name, TEST_ADMIN, TEST_ALICE);
        const tool = await openTool(page, user, TOOL_CODE, TOOL_ROOT);
        await selectCurrency(page, 'pac-report-currency', 'EUR');
        const datedSource = page.waitForRequest((request) => sourceDateOf(request) === REFERENCE_DATE, {timeout: 20_000});
        await setDate(page, 'pac-analysis-date', REFERENCE_DATE);
        expect(sourceRequestBody(await datedSource)).toEqual(exactSourceRequest(REFERENCE_DATE));

        const card = page.getByTestId('pac-owned-asset-940011');
        await expect(card).toBeEnabled({timeout: 20_000});
        await card.click();
        const target = page.getByTestId('allocation-target-asset:pac-r4-stale');
        await target.fill('1z00');
        await expect(target).toHaveValue('100');

        const cash = await useManualCash(page);
        await cash.field.fill('10');
        await selectCurrency(page, `pac-cash-currency-${cash.index}`, 'EUR');

        const analyze = page.getByTestId('pac-analyze');
        const baseline = await runAndCaptureCompute(page, () => analyze.click());
        expect(baseline.response.status()).toBe(200);
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        const result = page.getByTestId('pac-result-panel');
        await expect(result.getByTestId('allocation-diagnostics')).toBeVisible();
        await expect(result.getByTestId('dt-header-allocation')).toBeVisible();
        await expect(result).toContainText('10 EUR');

        await cash.field.fill('20');
        await expect(cash.field).toHaveValue('20');
        await expect(page.getByTestId('pac-result-stale')).toBeVisible();

        const fetched = gate();
        const release = gate();
        let heldStatus: number | undefined;
        let heldBody: ToolComputeResponse | undefined;
        await page.route(`**${COMPUTE_PATH}`, async (route) => {
            const response = await route.fetch();
            heldStatus = response.status();
            heldBody = (await response.json()) as ToolComputeResponse;
            fetched.open();
            await release.promise;
            // This response stays in the same document: delivery must succeed,
            // otherwise an aborted transport could masquerade as a stale guard.
            await route.fulfill({response});
        });

        const refresh = page.getByTestId('pac-owned-assets-refresh');
        await expect(refresh).toBeEnabled();
        holdRefresh = true;
        refreshed = true;
        const refreshedSource = page.waitForRequest((request) => sourceDateOf(request) === REFERENCE_DATE, {timeout: 20_000});
        await refresh.click();
        await refreshFetched.promise;

        await expect(analyze).toBeEnabled();
        await analyze.click();
        await fetched.promise;
        expect(heldStatus).toBe(200);
        if (heldBody === undefined) throw new Error('PAC response was not captured');
        const heldResult = only(heldBody.results, (result) => result.tool_code === TOOL_CODE, 'held PAC result');
        expect(heldResult.status).toBe('success');
        if (heldResult.status !== 'success') throw new Error(`held PAC result failed with ${heldResult.error.code}`);
        const heldOutput = heldResult.result as PacOutput;
        expect(heldOutput.availability).toBe('ready');
        expect(heldOutput.totals.investable_budget_reporting).toMatchObject({availability: 'available', value: {currency: 'EUR', amount: '20'}});
        await expect(tool).toHaveAttribute('data-busy', 'true');

        try {
            releaseRefresh.open();
            expect(sourceRequestBody(await refreshedSource)).toEqual(exactSourceRequest(REFERENCE_DATE));
            await expectCurrentPrices(page, [{currency: 'EUR', amount: '20.000000000001'}]);
            await expect(target).toHaveValue('100');
        } finally {
            releaseRefresh.open();
            release.open();
        }
        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        await expect(result).toBeVisible();
        await expect(result.getByTestId('allocation-diagnostics')).toBeVisible();
        await expect(result.getByTestId('dt-header-allocation')).toBeVisible();
        await expect(page.getByTestId('pac-result-stale')).toBeVisible();
        await expect(result).toContainText('10 EUR');
        await expect(result).not.toContainText('20 EUR');
        await expect(target).toHaveValue('100');
        await expect(cash.field).toHaveValue('20');
    });
});
