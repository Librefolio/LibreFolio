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
    type SourceAssetWire,
} from './allocation-tool-fixtures';

const TOOL_CODE = 'portfolio_rebalancer';
const TOOL_ROOT = 'portfolio-rebalancer-tool';
const ALPHA_PRIMARY_CONTEXT_KEY = 'asset:rebalancer-r4-alpha:broker:1';
const ALPHA_ZERO_SHARE_CONTEXT_KEY = 'asset:rebalancer-r4-alpha:broker:2';

type RebalancerInput = ToolInput<'portfolio_rebalancer', '1.0.0'>;
type RebalancerOutput = ToolOutput<'portfolio_rebalancer', '1.0.0'>;

const ALPHA: SourceAssetWire = {
    asset_id: 950_001,
    instrument_key: 'asset:rebalancer-r4-alpha',
    candidate_key: 'candidate:rebalancer-r4-alpha',
    name: 'Rebalancer R4 Alpha',
    ticker: 'R4A',
    asset_type: 'ETF',
    icon_url: null,
    active: true,
    usage_scope: 'owned',
    quote: {
        raw_price: '100',
        currency: 'EUR',
        quote_base_quantity: 1,
        reference_date: REFERENCE_DATE,
        source: 'rebalancer-r4-fixture',
        days_before_requested: 0,
    },
    contexts: [
        {
            context_key: ALPHA_PRIMARY_CONTEXT_KEY,
            broker_id: 95_001,
            broker_name: 'Rebalancer R4 broker Alpha',
            broker_icon_url: null,
            broker_portal_url: null,
            broker_default_import_plugin: null,
            ownership_share_percent: '25',
            custody_quantity: '1',
        },
        {
            context_key: ALPHA_ZERO_SHARE_CONTEXT_KEY,
            broker_id: 95_002,
            broker_name: 'Rebalancer R4 broker Zero Share',
            broker_icon_url: null,
            broker_portal_url: null,
            broker_default_import_plugin: null,
            ownership_share_percent: '0',
            custody_quantity: '2',
        },
    ],
};

const BETA: SourceAssetWire = {
    asset_id: 950_002,
    instrument_key: 'asset:rebalancer-r4-beta',
    candidate_key: 'candidate:rebalancer-r4-beta',
    name: 'Rebalancer R4 Beta',
    ticker: 'R4B',
    asset_type: 'STOCK',
    icon_url: null,
    active: true,
    usage_scope: 'owned',
    quote: {
        raw_price: '100',
        currency: 'EUR',
        quote_base_quantity: 1,
        reference_date: REFERENCE_DATE,
        source: 'rebalancer-r4-fixture',
        days_before_requested: 0,
    },
    contexts: [
        {
            context_key: 'asset:rebalancer-r4-beta:broker:3',
            broker_id: 95_003,
            broker_name: 'Rebalancer R4 broker Beta',
            broker_icon_url: null,
            broker_portal_url: null,
            broker_default_import_plugin: null,
            ownership_share_percent: '100',
            custody_quantity: '6',
        },
    ],
};

const MANUAL_NAME = 'Rebalancer R4 Manual';

function rebalancerItem(body: ToolComputeRequest) {
    return only(body.items, (item) => item.tool_code === TOOL_CODE, 'rebalancer compute item');
}

async function manualTargetField(page: Page, knownTestIds: ReadonlySet<string>): Promise<Locator> {
    const candidates: Locator[] = [];
    const fields = page.getByTestId(/^allocation-target-(?:asset:|manual:asset:)/);
    await expect(fields).toHaveCount(knownTestIds.size + 1);
    for (const field of await fields.all()) {
        const testId = await field.getAttribute('data-testid');
        if (testId !== null && !knownTestIds.has(testId)) candidates.push(field);
    }
    expect(candidates, 'manual canonical target field').toHaveLength(1);
    const candidate = candidates.pop();
    if (candidate === undefined) throw new Error('manual canonical target field was not found');
    return candidate;
}

test.setTimeout(90_000);

test.describe('Portfolio rebalancer P1', () => {
    test('removes fresh manual holdings immediately and guards edits or a final targeted holding', async ({page}, testInfo) => {
        await routeAllocationSource(page, (request) => sourcePayload(request.allocation_source.as_of_date, [ALPHA]));
        const user = principal(testInfo.project.name, TEST_ADMIN, TEST_ALICE);
        await openTool(page, user, TOOL_CODE, TOOL_ROOT);

        const alphaCard = page.getByTestId(`pac-owned-asset-${ALPHA.asset_id}`);
        await expect(alphaCard).toBeEnabled({timeout: 20_000});

        await page.getByTestId('pac-add-manual-asset').click();
        const freshName = await soleIndexedField(page.getByTestId(/^rebalancer-holding-name-\d+$/), 'rebalancer-holding-name', 'fresh manual holding');
        await expect(freshName.field).toBeVisible();
        const freshTarget = await manualTargetField(page, new Set<string>());
        const freshTargetId = await freshTarget.getAttribute('data-testid');
        if (freshTargetId === null) throw new Error('fresh manual holding target has no data-testid');
        const ownedFreshTarget = page.getByTestId(freshTargetId);
        const freshRemove = page.getByTestId(`rebalancer-remove-${freshName.index}`);
        await expect(freshRemove).toBeVisible();
        await freshRemove.click();
        await expect(freshName.field).toHaveCount(0);
        await expect(ownedFreshTarget).toHaveCount(0);
        await expect(page.getByTestId('rebalancer-customized-removal-confirm')).toHaveCount(0);

        await page.getByTestId('pac-add-manual-asset').click();
        const editedName = await soleIndexedField(page.getByTestId(/^rebalancer-holding-name-\d+$/), 'rebalancer-holding-name', 'edited manual holding');
        await expect(editedName.field).toBeVisible();
        const editedTarget = await manualTargetField(page, new Set<string>());
        const editedTargetId = await editedTarget.getAttribute('data-testid');
        if (editedTargetId === null) throw new Error('edited manual holding target has no data-testid');
        const ownedEditedTarget = page.getByTestId(editedTargetId);
        const editedRemove = page.getByTestId(`rebalancer-remove-${editedName.index}`);
        await expect(editedRemove).toBeVisible();
        await editedName.field.fill('Rebalancer R4 customized manual holding');
        await expect(editedName.field).toHaveValue('Rebalancer R4 customized manual holding');
        await editedRemove.click();
        const confirmation = page.getByTestId('rebalancer-customized-removal-confirm');
        await expect(confirmation).toBeVisible();
        await expect(page.getByTestId('confirm-modal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(confirmation).toHaveCount(0);
        await expect(editedName.field).toHaveValue('Rebalancer R4 customized manual holding');

        await editedRemove.click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(editedName.field).toHaveCount(0);
        await expect(ownedEditedTarget).toHaveCount(0);
        await expect(confirmation).toHaveCount(0);

        await alphaCard.click();
        const alphaTarget = page.getByTestId(`allocation-target-${ALPHA.instrument_key}`);
        await expect(alphaTarget).toBeVisible();
        await alphaTarget.fill('100');
        await expect(alphaTarget).toHaveValue('100');

        const primaryBrokerName = only(ALPHA.contexts, (context) => context.context_key === ALPHA_PRIMARY_CONTEXT_KEY, 'Alpha primary deletion context').broker_name;
        const lastBrokerName = only(ALPHA.contexts, (context) => context.context_key === ALPHA_ZERO_SHARE_CONTEXT_KEY, 'Alpha final deletion context').broker_name;

        const primary = page.getByTestId('rebalancer-holding').filter({hasText: primaryBrokerName});
        await expect(primary).toHaveCount(1);
        const primaryRemove = primary.getByTestId(/^rebalancer-remove-\d+$/);
        await expect(primaryRemove).toHaveCount(1);
        await primaryRemove.click();
        await expect(primary).toHaveCount(0);
        await expect(confirmation).toHaveCount(0);
        await expect(alphaTarget).toHaveValue('100');

        const last = page.getByTestId('rebalancer-holding').filter({hasText: lastBrokerName});
        await expect(last).toHaveCount(1);
        const lastRemove = last.getByTestId(/^rebalancer-remove-\d+$/);
        await expect(lastRemove).toHaveCount(1);
        await lastRemove.click();
        await expect(confirmation).toBeVisible();
        await page.getByTestId('confirm-modal-confirm').click();
        await expect(last).toHaveCount(0);
        await expect(alphaTarget).toHaveCount(0);
        await expect(confirmation).toHaveCount(0);
        await expect(alphaCard).toHaveAttribute('aria-pressed', 'false');
    });

    test('imports read-only custody contexts, keeps canonical targets exact, and guards target removal', async ({page}, testInfo) => {
        await routeAllocationSource(page, (request) => sourcePayload(request.allocation_source.as_of_date, [ALPHA, BETA]));
        const user = principal(testInfo.project.name, TEST_DAVE, TEST_EVE);
        const tool = await openTool(page, user, TOOL_CODE, TOOL_ROOT);

        await expect(page.getByTestId('pac-allocator-tool')).toHaveCount(0);
        await selectCurrency(page, 'rebalancer-report-currency', 'EUR');
        const datedSource = page.waitForRequest((request) => sourceDateOf(request) === REFERENCE_DATE, {timeout: 20_000});
        await setDate(page, 'rebalancer-analysis-date', REFERENCE_DATE);
        expect(sourceRequestBody(await datedSource)).toEqual(exactSourceRequest(REFERENCE_DATE));

        const alphaCard = page.getByTestId(`pac-owned-asset-${ALPHA.asset_id}`);
        const betaCard = page.getByTestId(`pac-owned-asset-${BETA.asset_id}`);
        await expect(alphaCard).toBeEnabled({timeout: 20_000});
        await expect(betaCard).toBeEnabled();
        await alphaCard.click();
        await betaCard.click();

        await expect(page.getByTestId('rebalancer-holding')).toHaveCount(3);
        await expect(page.getByTestId(/^rebalancer-quantity-\d+$/)).toHaveCount(0);
        await expect(page.getByTestId(/^rebalancer-currency-\d+-trigger$/)).toHaveCount(0);
        await expect(page.getByTestId(/^rebalancer-price-\d+$/)).toHaveCount(0);
        await expect(page.getByTestId(/^rebalancer-quote-basis-\d+$/)).toHaveCount(0);
        await expect(page.getByTestId(/^rebalancer-price-date-\d+$/)).toHaveCount(0);
        const alphaPrimaryName = only(ALPHA.contexts, (context) => context.context_key === ALPHA_PRIMARY_CONTEXT_KEY, 'Alpha primary facts context').broker_name;
        const alphaPrimaryRow = page.getByTestId('rebalancer-holding').filter({hasText: alphaPrimaryName});
        await expect(alphaPrimaryRow).toHaveCount(1);
        const alphaPrimaryIndex = await alphaPrimaryRow.getAttribute('data-index');
        if (alphaPrimaryIndex === null) throw new Error('Alpha primary holding has no data-index');
        const copiedFacts = alphaPrimaryRow.getByTestId(`rebalancer-holding-facts-${alphaPrimaryIndex}`);
        await expect(copiedFacts).toBeVisible();
        await expect(copiedFacts).not.toHaveAttribute('open', '');
        await expect(copiedFacts.getByTestId(`rebalancer-current-price-${alphaPrimaryIndex}`)).toBeHidden();
        const targetEditor = page.getByTestId('allocation-target-editor');
        await expect(targetEditor).toHaveAttribute('data-service', 'rebalancer');
        await expect(targetEditor.getByTestId('dt-header-instrument')).toBeVisible();
        await expect(targetEditor.getByTestId('dt-header-target')).toBeVisible();
        await expect(targetEditor.getByTestId('dt-header-bar')).toBeVisible();

        const alphaTargetId = `allocation-target-${ALPHA.instrument_key}`;
        const betaTargetId = `allocation-target-${BETA.instrument_key}`;
        const alphaTarget = page.getByTestId(alphaTargetId);
        const betaTarget = page.getByTestId(betaTargetId);
        await alphaTarget.fill('2x0');
        await betaTarget.fill('5y0');
        await expect(alphaTarget).toHaveValue('20');
        await expect(betaTarget).toHaveValue('50');

        await page.getByTestId('pac-add-manual-asset').click();
        await expect(page.getByTestId('rebalancer-holding')).toHaveCount(4);
        await expect(page.getByTestId(/^rebalancer-quantity-\d+$/)).toHaveCount(1);
        await expect(page.getByTestId(/^rebalancer-currency-\d+-trigger$/)).toHaveCount(1);
        await expect(page.getByTestId(/^rebalancer-price-\d+$/)).toHaveCount(1);
        await expect(page.getByTestId(/^rebalancer-quote-basis-\d+$/)).toHaveCount(1);
        await expect(page.getByTestId(/^rebalancer-price-date-\d+$/)).toHaveCount(1);
        const manualNameFields = page.getByTestId(/^rebalancer-holding-name-\d+$/);
        await expect(manualNameFields).toHaveCount(1);
        const manualName = await soleIndexedField(manualNameFields, 'rebalancer-holding-name', 'manual holding name');
        await manualName.field.fill(MANUAL_NAME);

        const quantity = page.getByTestId(`rebalancer-quantity-${manualName.index}`);
        const price = page.getByTestId(`rebalancer-price-${manualName.index}`);
        await quantity.fill('1unit');
        await price.fill('1hundred00');
        await selectCurrency(page, `rebalancer-currency-${manualName.index}`, 'USD');
        const fx = page.getByTestId('allocation-valuation-rates');
        await expect(fx).toBeVisible();
        await expect(fx.getByTestId('allocation-rate-add')).toBeVisible();
        await expect(fx).toContainText('USD');
        await expect(fx).toContainText('EUR');
        await selectCurrency(page, `rebalancer-currency-${manualName.index}`, 'EUR');
        await expect(fx).toHaveCount(0);
        await setDate(page, `rebalancer-price-date-${manualName.index}`, REFERENCE_DATE);
        await expect(quantity).toHaveValue('1');
        await expect(price).toHaveValue('100');
        await expect(page.getByTestId(`rebalancer-quote-basis-${manualName.index}`)).toHaveValue('1');

        const manualTarget = await manualTargetField(page, new Set([alphaTargetId, betaTargetId]));
        await manualTarget.fill('3z0');
        await expect(manualTarget).toHaveValue('30');
        await expect(page.getByTestId('allocation-target-remaining')).toContainText('0%');
        await expect(page.getByTestId('rebalancer-funding-context').getByTestId('allocation-funding-summary')).toHaveCount(1);
        await expect(page.getByTestId('allocation-valuation-rates')).toHaveCount(0);

        const {request, response} = await runAndCaptureCompute(page, () => page.getByTestId('rebalancer-analyze').click());

        const requestBody = request.postDataJSON() as ToolComputeRequest;
        expect(requestBody.items).toHaveLength(1);
        const item = rebalancerItem(requestBody);
        expect(item).toMatchObject({
            tool_code: TOOL_CODE,
            contract_version: '1.0.0',
            implementation_version: '1.0.0',
        });
        const parameters = item.parameters as RebalancerInput;
        expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'cash_balances', 'contributions', 'holdings', 'operation', 'report_currency', 'targets', 'valuation_rates']);
        expect(parameters.operation).toBe('analyze');
        expect(parameters.report_currency).toBe('EUR');
        expect(parameters.as_of_date).toBe(REFERENCE_DATE);
        expect(parameters.cash_balances).toEqual([]);
        expect(parameters.contributions).toEqual([]);
        expect(parameters.valuation_rates).toEqual([]);
        const holdings = parameters.holdings ?? [];
        const targets = parameters.targets ?? [];
        expect(holdings).toHaveLength(4);

        const alphaHoldings = holdings.filter((holding) => holding.instrument_key === ALPHA.instrument_key);
        expect(alphaHoldings).toHaveLength(2);
        const alphaPrimaryHolding = only(alphaHoldings, (holding) => holding.row_key.startsWith(`${ALPHA_PRIMARY_CONTEXT_KEY}:`), 'Alpha primary custody');
        const alphaZeroShareHolding = only(alphaHoldings, (holding) => holding.row_key.startsWith(`${ALPHA_ZERO_SHARE_CONTEXT_KEY}:`), 'Alpha zero-share custody');
        expect(alphaPrimaryHolding).toMatchObject({
            instrument_key: ALPHA.instrument_key,
            name: ALPHA.name,
            quantity: '1',
            quote: {raw_price: '100', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        expect(alphaZeroShareHolding).toMatchObject({
            instrument_key: ALPHA.instrument_key,
            name: ALPHA.name,
            quantity: '2',
            quote: {raw_price: '100', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        const betaHolding = only(holdings, (holding) => holding.instrument_key === BETA.instrument_key, 'Beta custody');
        expect(betaHolding).toMatchObject({
            name: BETA.name,
            quantity: '6',
            quote: {raw_price: '100', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        const manualHolding = only(holdings, (holding) => holding.name === MANUAL_NAME, 'manual holding');
        expect(manualHolding).toMatchObject({
            name: MANUAL_NAME,
            quantity: '1',
            quote: {raw_price: '100', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });

        expect(targets).toHaveLength(3);
        expect(targets.filter((target) => target.instrument_key === ALPHA.instrument_key)).toHaveLength(1);
        expect(targets.filter((target) => target.instrument_key === BETA.instrument_key)).toHaveLength(1);
        expect(only(targets, (target) => target.instrument_key === ALPHA.instrument_key, 'Alpha canonical target')).toEqual({
            instrument_key: ALPHA.instrument_key,
            target_percent: '20',
        });
        expect(only(targets, (target) => target.instrument_key === BETA.instrument_key, 'Beta canonical target')).toEqual({
            instrument_key: BETA.instrument_key,
            target_percent: '50',
        });
        expect(only(targets, (target) => target.instrument_key === manualHolding.instrument_key, 'manual canonical target')).toEqual({
            instrument_key: manualHolding.instrument_key,
            target_percent: '30',
        });
        for (const absent of ['assets', 'orders', 'solver', 'trade_feasibility', 'optimization', 'draft_revision']) {
            expect(parameters).not.toHaveProperty(absent);
        }

        expect(response.status(), response.status() === 200 ? '' : await response.text()).toBe(200);
        const responseBody = (await response.json()) as ToolComputeResponse;
        expect(responseBody.request_id).toBe(requestBody.request_id);
        expect(responseBody.success_count).toBe(1);
        expect(responseBody.failed_count).toBe(0);
        const platformResult = only(responseBody.results, (result) => result.correlation_id === item.correlation_id && result.tool_code === TOOL_CODE, 'rebalancer compute result');
        expect(platformResult.status).toBe('success');
        if (platformResult.status !== 'success') throw new Error(`rebalancer compute failed with ${platformResult.error.code}`);
        expect(platformResult).toMatchObject({
            tool_code: item.tool_code,
            contract_version: item.contract_version,
            implementation_version: item.implementation_version,
            schema_fingerprint: item.schema_fingerprint,
            correlation_id: item.correlation_id,
        });
        const output = platformResult.result as RebalancerOutput;
        expect(output.availability).toBe('ready');
        expect(output.result_kind).toBe('portfolio_rebalancing_analysis');
        expect(output).not.toHaveProperty('trade_feasibility');
        expect(output).not.toHaveProperty('optimization');
        expect(output.totals.current_invested_reporting).toMatchObject({availability: 'available', value: {currency: 'EUR', amount: '1000'}});
        const alphaResult = only(output.instruments, (instrument) => instrument.instrument_key === ALPHA.instrument_key, 'Alpha instrument result');
        const betaResult = only(output.instruments, (instrument) => instrument.instrument_key === BETA.instrument_key, 'Beta instrument result');
        const manualResult = only(output.instruments, (instrument) => instrument.instrument_key === manualHolding.instrument_key, 'manual instrument result');
        expect(alphaResult).toMatchObject({
            custody_context_count: 2,
            current_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '300'}},
            current_weight_percent: {availability: 'available', value: {approximation: '30'}},
            target_percent: {availability: 'available', value: '20'},
            target_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '200'}},
            value_gap_to_target_reporting: {availability: 'available', value: {currency: 'EUR', amount: '-100'}},
        });
        expect(betaResult).toMatchObject({
            custody_context_count: 1,
            current_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '600'}},
            current_weight_percent: {availability: 'available', value: {approximation: '60'}},
            target_percent: {availability: 'available', value: '50'},
            target_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '500'}},
            value_gap_to_target_reporting: {availability: 'available', value: {currency: 'EUR', amount: '-100'}},
        });
        expect(manualResult).toMatchObject({
            custody_context_count: 1,
            current_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '100'}},
            current_weight_percent: {availability: 'available', value: {approximation: '10'}},
            target_percent: {availability: 'available', value: '30'},
            target_value_reporting: {availability: 'available', value: {currency: 'EUR', amount: '300'}},
            value_gap_to_target_reporting: {availability: 'available', value: {currency: 'EUR', amount: '200'}},
        });

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 40_000});
        const result = page.getByTestId('rebalancer-result-panel');
        await expect(result).toBeVisible();
        await expect(result.getByTestId('allocation-diagnostics')).toBeVisible();
        for (const header of ['asset', 'contexts', 'currentValue', 'currentWeight', 'target', 'targetValue', 'gap']) {
            await expect(result.getByTestId(`dt-header-${header}`)).toBeVisible();
        }
        await expect(result).toContainText(ALPHA.name);
        await expect(result).toContainText(BETA.name);
        await expect(result).toContainText(MANUAL_NAME);
        await expect(result).toContainText('300 EUR');
        await expect(result).toContainText('600 EUR');
        await expect(result).toContainText('-100 EUR');
        await expect(result).toContainText('200 EUR');

        const copyCurrent = page.getByTestId('rebalancer-copy-current-distribution');
        await expect(copyCurrent).toBeEnabled();
        await copyCurrent.click();
        await expect(alphaTarget).toHaveValue('30');
        await expect(betaTarget).toHaveValue('60');
        await expect(manualTarget).toHaveValue('10');
        await expect(page.getByTestId('allocation-target-remaining')).toContainText('0%');
        await expect(page.getByTestId('rebalancer-result-stale')).toBeVisible();

        // No imported buy grid was changed in this flow, so the warning below
        // specifically protects the customized canonical target.
        await alphaCard.click();
        await expect(page.getByTestId('rebalancer-customized-removal-confirm')).toBeVisible();
        await page.getByTestId('confirm-modal-cancel').click();
        await expect(page.getByTestId('rebalancer-customized-removal-confirm')).toHaveCount(0);
        await expect(alphaCard).toHaveAttribute('aria-pressed', 'true');
        await expect(page.getByTestId('rebalancer-holding')).toHaveCount(4);
        await expect(alphaTarget).toHaveValue('30');
    });

    test('drops an in-flight result across an account change and opens a clean replacement draft', async ({page}, testInfo) => {
        await routeAllocationSource(page, (request) => sourcePayload(request.allocation_source.as_of_date, [BETA]));
        const originalUser = principal(testInfo.project.name, TEST_BOB, TEST_CAROL);
        const replacementUser = principal(testInfo.project.name, TEST_USER, TEST_USER_2);
        const tool = await openTool(page, originalUser, TOOL_CODE, TOOL_ROOT);

        await selectCurrency(page, 'rebalancer-report-currency', 'EUR');
        const datedSource = page.waitForRequest((request) => sourceDateOf(request) === REFERENCE_DATE, {timeout: 20_000});
        await setDate(page, 'rebalancer-analysis-date', REFERENCE_DATE);
        expect(sourceRequestBody(await datedSource)).toEqual(exactSourceRequest(REFERENCE_DATE));

        const card = page.getByTestId(`pac-owned-asset-${BETA.asset_id}`);
        await expect(card).toBeEnabled({timeout: 20_000});
        await card.click();
        const target = page.getByTestId(`allocation-target-${BETA.instrument_key}`);
        await target.fill('1x00');
        await expect(target).toHaveValue('100');

        const fetched = gate();
        const release = gate();
        const settled = gate();
        let heldBody: ToolComputeResponse | undefined;
        await page.route(`**${COMPUTE_PATH}`, async (route) => {
            const response = await route.fetch();
            heldBody = (await response.json()) as ToolComputeResponse;
            fetched.open();
            await release.promise;
            try {
                await route.fulfill({response});
            } catch {
                // Logging out aborts the old document's request. A rejected
                // late fulfilment is therefore the expected transport outcome.
            } finally {
                settled.open();
            }
        });

        await page.getByTestId('rebalancer-analyze').click();
        await fetched.promise;
        if (heldBody === undefined) throw new Error('rebalancer response was not captured');
        const heldResult = only(heldBody.results, (result) => result.tool_code === TOOL_CODE, 'held rebalancer result');
        expect(heldResult.status).toBe('success');
        if (heldResult.status !== 'success') throw new Error(`held rebalancer result failed with ${heldResult.error.code}`);
        expect((heldResult.result as RebalancerOutput).availability).toBe('ready');
        await expect(tool).toHaveAttribute('data-busy', 'true');

        try {
            if (testInfo.project.name === 'mobile') {
                await page.getByTestId('mobile-menu-toggle').click();
            }
            const logout = page.getByTestId('logout-button');
            await expect(logout).toBeVisible();
            await logout.click();
            await expect(page.getByTestId('login-page')).toBeVisible({timeout: 20_000});
        } finally {
            release.open();
        }
        await settled.promise;

        await openTool(page, replacementUser, TOOL_CODE, TOOL_ROOT);
        const replacementCard = page.getByTestId(`pac-owned-asset-${BETA.asset_id}`);
        await expect(replacementCard).toBeEnabled({timeout: 20_000});
        await expect(replacementCard).toHaveAttribute('aria-pressed', 'false');
        await expect(page.getByTestId('rebalancer-holding')).toHaveCount(0);
        await expect(page.getByTestId('allocation-target-empty')).toBeVisible();
        const result = page.getByTestId('rebalancer-result-panel');
        await expect(result).toBeVisible();
        await expect(result.getByTestId('allocation-diagnostics')).toHaveCount(0);
        await expect(result.getByTestId('dt-header-currentWeight')).toHaveCount(0);
        await expect(page.getByTestId('rebalancer-copy-current-distribution')).toHaveCount(0);
    });
});
