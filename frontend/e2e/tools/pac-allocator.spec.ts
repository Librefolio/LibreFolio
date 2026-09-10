import {expect, test, type Locator, type Page, type Request} from '../fixtures/playwright';
import {login, navigateTo} from '../fixtures/auth-helpers';
import {TEST_ADMIN, TEST_USER, TEST_USER_2} from '../fixtures/test-users';
import type {ToolComputeRequest, ToolComputeResponse, ToolInput, ToolOutput} from '../../src/lib/features/tools/contracts';

const TOOL_ROUTE = '/tools/pac_allocator';
const COMPUTE_PATH = '/api/v1/tools/compute';
const REFERENCE_DATE = '2026-09-08';
const PRIMARY_NAME = 'PAC P1 primary context';
const SECONDARY_NAME = 'PAC P1 secondary context';
const REVISED_NAME = 'PAC P1 primary context revised';

type TestUser = typeof TEST_USER;
type PacInput = ToolInput<'pac_allocator', '1.0.0'>;
type PacInputRow = NonNullable<PacInput['rows']>[number];
type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;
type PacReady = Extract<PacOutput, {availability: 'ready'}>;

const TEST_ALICE: TestUser = {
    username: 'e2e_user_alice',
    email: 'alice@test.example.com',
    password: 'AlicePass123!',
};

test.setTimeout(60_000);

function gate(): {promise: Promise<void>; open: () => void} {
    let open!: () => void;
    const promise = new Promise<void>((resolve) => {
        open = resolve;
    });
    return {promise, open};
}

function only<T>(items: readonly T[], predicate: (item: T) => boolean, label: string): T {
    const matches = items.filter(predicate);
    expect(matches, label).toHaveLength(1);
    const [match] = matches;
    if (!match) throw new Error(`${label}: expected exactly one match`);
    return match;
}

function isComputeRequest(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMPUTE_PATH;
}

function inputRow(page: Page, index: number): Locator {
    return page.locator(`[data-testid="pac-row"][data-row-index="${index}"]`);
}

async function openPacTool(page: Page, user: TestUser): Promise<Locator> {
    await login(page, user);
    await navigateTo(page, TOOL_ROUTE);

    const host = page.getByTestId('tool-host');
    await expect(host).toHaveAttribute('data-state', 'ready', {timeout: 15_000});
    await expect(host).toHaveAttribute('data-busy', 'false');

    const tool = page.getByTestId('pac-allocator-tool');
    await expect(tool).toBeVisible();
    await expect(tool).toHaveAttribute('data-busy', 'false');
    return tool;
}

async function fillRow(row: Locator, name: string, quantity: string): Promise<void> {
    await expect(row).toHaveCount(1);
    await expect(row).toBeVisible();
    await row.getByTestId('pac-row-name').fill(name);
    await row.getByTestId('pac-initial-quantity').fill(quantity);
    await row.getByTestId('pac-price').fill('10');
    await row.getByTestId('pac-price-currency').fill('EUR');
    await row.getByTestId('pac-quote-basis').fill('1');
    await row.getByTestId('pac-target-percent').fill('50');
    await row.getByTestId('pac-grid-mode').selectOption('whole');
    await row.getByTestId('pac-quantity-step').fill('1');
    await row.getByTestId('pac-quote-date').fill(REFERENCE_DATE);
}

async function fillScenario(page: Page): Promise<void> {
    await page.getByTestId('pac-report-currency').fill('EUR');
    await page.getByTestId('pac-as-of-date').fill(REFERENCE_DATE);

    const primary = inputRow(page, 0);
    await fillRow(primary, PRIMARY_NAME, '10');
    await primary.getByTestId('pac-add-same-instrument').click();
    await fillRow(inputRow(page, 1), SECONDARY_NAME, '0');

    await page.getByTestId('pac-add-cash').click();
    const cash = page.getByTestId('pac-existing-cash-row');
    await expect(cash).toHaveCount(1);
    await cash.getByTestId('pac-cash-currency').fill('USD');
    await cash.getByTestId('pac-cash-amount').fill('10');

    await page.getByTestId('pac-add-contribution').click();
    const contribution = page.getByTestId('pac-contribution-row');
    await expect(contribution).toHaveCount(1);
    await contribution.getByTestId('pac-contribution-currency').fill('EUR');
    await contribution.getByTestId('pac-contribution-amount').fill('5');

    await page.getByTestId('pac-add-rate').click();
    const rate = page.getByTestId('pac-rate-row');
    await expect(rate).toHaveCount(1);
    await rate.getByTestId('pac-rate-currency').fill('USD');
    await rate.getByTestId('pac-rate-value').fill('0.9');
    await rate.getByTestId('pac-rate-date').fill(REFERENCE_DATE);

    // The component exposes no page-overflow state. These are the key stacked
    // inputs/actions whose visibility guards both default viewport projects.
    await expect(page.getByTestId('pac-report-currency')).toBeVisible();
    await expect(inputRow(page, 1).getByTestId('pac-row-name')).toBeVisible();
    await expect(page.getByTestId('pac-cash-amount')).toBeVisible();
    await expect(page.getByTestId('pac-contribution-amount')).toBeVisible();
    await expect(page.getByTestId('pac-rate-value')).toBeVisible();
    await expect(page.getByTestId('pac-analyze')).toBeVisible();
}

function assertAnalyzeRequest(body: ToolComputeRequest): {
    correlationId: string;
    parameters: PacInput;
    primary: PacInputRow;
    secondary: PacInputRow;
} {
    expect(body.items).toHaveLength(1);
    const item = only(body.items, (candidate) => candidate.tool_code === 'pac_allocator', 'PAC compute item');
    expect(item.contract_version).toBe('1.0.0');
    expect(item.implementation_version).toBe('1.0.0');

    const parameters = item.parameters as PacInput;
    expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'cash_balances', 'contributions', 'operation', 'report_currency', 'rows', 'valuation_rates']);
    expect(parameters.operation).toBe('analyze');
    expect(parameters.report_currency).toBe('EUR');
    expect(parameters.as_of_date).toBe(REFERENCE_DATE);
    expect(parameters.cash_balances).toEqual([{currency: 'USD', amount: '10'}]);
    expect(parameters.contributions).toEqual([{currency: 'EUR', amount: '5'}]);
    expect(parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.9', reference_date: REFERENCE_DATE}]);
    expect(parameters).not.toHaveProperty('solver');
    expect(parameters).not.toHaveProperty('orders');

    const rows = parameters.rows ?? [];
    expect(rows).toHaveLength(2);
    const primary = only(rows, (row) => row.name === PRIMARY_NAME, 'primary PAC input row');
    const secondary = only(rows, (row) => row.name === SECONDARY_NAME, 'secondary PAC input row');
    expect(primary.row_key).toMatch(/^local-row-[0-9]+$/);
    expect(secondary.row_key).toMatch(/^local-row-[0-9]+$/);
    expect(primary.row_key).not.toBe(secondary.row_key);
    expect(primary.instrument_key).toBe(secondary.instrument_key);
    expect(primary).toEqual({
        row_key: primary.row_key,
        instrument_key: primary.instrument_key,
        name: PRIMARY_NAME,
        initial_quantity: '10',
        quote: {raw_price: '10', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
        target_percent: '50',
        buy_grid: {mode: 'whole', quantity_step: '1'},
    });
    expect(secondary).toEqual({
        row_key: secondary.row_key,
        instrument_key: primary.instrument_key,
        name: SECONDARY_NAME,
        initial_quantity: '0',
        quote: {raw_price: '10', currency: 'EUR', quote_base_quantity: 1, reference_date: REFERENCE_DATE},
        target_percent: '50',
        buy_grid: {mode: 'whole', quantity_step: '1'},
    });
    return {correlationId: item.correlation_id, parameters, primary, secondary};
}

function available<T>(value: T): {availability: 'available'; reason_codes: never[]; value: T} {
    return {availability: 'available', reason_codes: [], value};
}

function money(amount: string) {
    return available({currency: 'EUR', amount});
}

function ratio(numerator: string, denominator: string, approximation: string, unit: 'percent' | 'percentage_points' | 'percentage_points_squared') {
    return available({
        numerator,
        denominator,
        unit,
        approximation,
        approximation_decimal_places: 28,
        approximation_exact: true,
    });
}

function assertReadyOutput(output: PacOutput, primaryInput: PacInputRow, secondaryInput: PacInputRow): asserts output is PacReady {
    expect(output.availability).toBe('ready');
    if (output.availability !== 'ready') throw new Error(`Expected ready PAC output, got ${output.availability}`);
    expect({
        operation: output.operation,
        result_kind: output.result_kind,
        numeric_policy_id: output.numeric_policy_id,
        trade_feasibility: output.trade_feasibility,
        optimization: output.optimization,
        issues: output.issues,
    }).toEqual({
        operation: 'analyze',
        result_kind: 'initial_state_analysis',
        numeric_policy_id: 'pac-initial-state-v1',
        trade_feasibility: 'not_evaluated',
        optimization: 'not_run',
        issues: [],
    });

    expect(output.rows).toHaveLength(2);
    const primary = only(output.rows, (row) => row.name === PRIMARY_NAME, 'primary PAC output row');
    const secondary = only(output.rows, (row) => row.name === SECONDARY_NAME, 'secondary PAC output row');
    expect(primary).toEqual({
        row_index: 0,
        row_key: primaryInput.row_key,
        instrument_key: primaryInput.instrument_key,
        name: PRIMARY_NAME,
        quantity: available('10'),
        initial_value_native: available({currency: 'EUR', amount: '100'}),
        initial_value_reporting: money('100'),
        current_weight_percent: ratio('10000', '100', '100', 'percent'),
        target_percent: available('50'),
        deviation_pp: ratio('5000', '100', '50', 'percentage_points'),
    });
    expect(secondary).toEqual({
        row_index: 1,
        row_key: secondaryInput.row_key,
        instrument_key: primaryInput.instrument_key,
        name: SECONDARY_NAME,
        quantity: available('0'),
        initial_value_native: available({currency: 'EUR', amount: '0'}),
        initial_value_reporting: money('0'),
        current_weight_percent: ratio('0', '100', '0', 'percent'),
        target_percent: available('50'),
        deviation_pp: ratio('-5000', '100', '-50', 'percentage_points'),
    });

    expect(output.totals).toEqual({
        initial_invested_reporting: money('100'),
        existing_cash_reporting: money('9'),
        contributions_reporting: money('5'),
        cash_plus_contributions_reporting: money('14'),
        target_total_percent: available('100'),
        max_abs_gap_pp: ratio('5000', '100', '50', 'percentage_points'),
        squared_gap_pp2: ratio('50000000', '10000', '5000', 'percentage_points_squared'),
    });

    expect(output.cash_pools.availability).toBe('available');
    if (output.cash_pools.availability !== 'available') throw new Error('Expected available PAC cash pools');
    expect(output.cash_pools.reason_codes).toEqual([]);
    expect(output.cash_pools.value).toHaveLength(2);
    expect(only(output.cash_pools.value, (pool) => pool.currency === 'EUR', 'EUR PAC cash pool')).toEqual({
        currency: 'EUR',
        existing_amount: '0',
        contribution_amount: '5',
        combined_amount: '5',
        existing_reporting: money('0'),
        contribution_reporting: money('5'),
        combined_reporting: money('5'),
    });
    expect(only(output.cash_pools.value, (pool) => pool.currency === 'USD', 'USD PAC cash pool')).toEqual({
        currency: 'USD',
        existing_amount: '10',
        contribution_amount: '0',
        combined_amount: '10',
        existing_reporting: money('9'),
        contribution_reporting: money('0'),
        combined_reporting: money('9'),
    });

    expect(output.normalized.cash_balances).toEqual([
        {currency: 'EUR', amount: '0'},
        {currency: 'USD', amount: '10'},
    ]);
    expect(output.normalized.contributions).toEqual([
        {currency: 'EUR', amount: '5'},
        {currency: 'USD', amount: '0'},
    ]);
    expect(output.normalized.valuation_rates).toEqual([
        {currency: 'EUR', rate_to_report: '1', reference_date: null},
        {currency: 'USD', rate_to_report: '0.9', reference_date: REFERENCE_DATE},
    ]);
}

async function expectReadyDom(page: Page): Promise<void> {
    const result = page.getByTestId('pac-result');
    await expect(result).toBeVisible();
    await expect(result).toHaveAttribute('data-state', 'ready');
    await expect(result).toHaveAttribute('data-stale', 'false');
    await expect(page.getByTestId('pac-total-invested')).toHaveText('100 EUR');
    await expect(page.getByTestId('pac-total-existing-cash')).toHaveText('9 EUR');
    await expect(page.getByTestId('pac-total-contributions')).toHaveText('5 EUR');
    await expect(page.getByTestId('pac-total-combined-cash')).toHaveText('14 EUR');
    await expect(page.getByTestId('pac-max-gap')).toHaveText('5000 / 100');
    await expect(page.getByTestId('pac-squared-gap')).toHaveText('50000000 / 10000');

    const primary = page.getByTestId('pac-result-row').filter({hasText: PRIMARY_NAME});
    const secondary = page.getByTestId('pac-result-row').filter({hasText: SECONDARY_NAME});
    await expect(primary).toHaveCount(1);
    await expect(secondary).toHaveCount(1);
    await expect(primary).toBeVisible();
    await expect(secondary).toBeVisible();
    await expect(primary).toContainText('100 EUR');
    await expect(primary).toContainText('10000 / 100');
    await expect(primary).toContainText('5000 / 100');
    await expect(secondary).toContainText('0 EUR');
    await expect(secondary).toContainText('-5000 / 100');

    await expect(page.getByTestId('pac-cash-pool').filter({hasText: /^\s*EUR\b/})).toBeVisible();
    await expect(page.getByTestId('pac-cash-pool').filter({hasText: /^\s*USD\b/})).toBeVisible();
    await expect(page.getByTestId('pac-normalized-details')).toBeVisible();
}

// The ready and held-response cases each hit the real executor in both projects.
// Give those four concurrent runs distinct seeded principals: one active Tool
// batch per principal is a platform invariant. The 503 case never reaches it.
test.describe('PAC allocator P1 pilot', () => {
    test('analyzes a manual same-instrument scenario with separate cash vectors on desktop and mobile', async ({page}, testInfo) => {
        const user = testInfo.project.name === 'mobile' ? TEST_USER_2 : TEST_USER;
        const tool = await openPacTool(page, user);
        await fillScenario(page);

        const requestPromise = page.waitForRequest(isComputeRequest, {timeout: 15_000});
        const responsePromise = page.waitForResponse((response) => isComputeRequest(response.request()), {timeout: 15_000});
        await page.getByTestId('pac-analyze').click();
        const [request, response] = await Promise.all([requestPromise, responsePromise]);

        const requestBody = request.postDataJSON() as ToolComputeRequest;
        const sent = assertAnalyzeRequest(requestBody);
        expect(response.status(), response.status() === 200 ? '' : await response.text()).toBe(200);
        const responseBody = (await response.json()) as ToolComputeResponse;
        expect(responseBody.request_id).toBe(requestBody.request_id);
        expect(responseBody.success_count).toBe(1);
        expect(responseBody.failed_count).toBe(0);
        const platformResult = only(responseBody.results, (result) => result.correlation_id === sent.correlationId && result.tool_code === 'pac_allocator', 'PAC platform result');
        expect(platformResult.status).toBe('success');
        if (platformResult.status !== 'success') throw new Error(`PAC platform failed with ${platformResult.error.code}`);
        expect(platformResult.execution_id).toBeTruthy();
        assertReadyOutput(platformResult.result as PacOutput, sent.primary, sent.secondary);

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await expectReadyDom(page);
    });

    test('ignores a real compute response when the draft changes in flight', async ({page}, testInfo) => {
        const user = testInfo.project.name === 'mobile' ? TEST_ALICE : TEST_ADMIN;
        const tool = await openPacTool(page, user);
        await fillScenario(page);

        const fetched = gate();
        const release = gate();
        let heldStatus: number | undefined;
        let heldBody: ToolComputeResponse | undefined;
        await page.route('**/api/v1/tools/compute', async (route) => {
            const response = await route.fetch();
            heldStatus = response.status();
            heldBody = (await response.json()) as ToolComputeResponse;
            fetched.open();
            await release.promise;
            await route.fulfill({response});
        });

        const requestPromise = page.waitForRequest(isComputeRequest, {timeout: 15_000});
        await page.getByTestId('pac-analyze').click();

        try {
            const request = await requestPromise;
            const sent = assertAnalyzeRequest(request.postDataJSON() as ToolComputeRequest);
            await fetched.promise;
            expect(heldStatus).toBe(200);
            if (!heldBody) throw new Error('Real PAC compute response was not captured');
            expect(heldBody.success_count).toBe(1);
            const heldResult = only(heldBody.results, (result) => result.correlation_id === sent.correlationId, 'held PAC platform result');
            expect(heldResult.status).toBe('success');
            if (heldResult.status !== 'success') throw new Error(`Held PAC platform result failed with ${heldResult.error.code}`);
            expect((heldResult.result as PacOutput).availability).toBe('ready');
            await expect(tool).toHaveAttribute('data-busy', 'true');

            const revisionBefore = Number(await tool.getAttribute('data-revision'));
            expect(Number.isSafeInteger(revisionBefore)).toBe(true);
            await inputRow(page, 0).getByTestId('pac-row-name').fill(REVISED_NAME);
            await expect.poll(async () => Number(await tool.getAttribute('data-revision'))).toBeGreaterThan(revisionBefore);
            await expect(page.getByTestId('pac-request-stale')).toBeVisible();
        } finally {
            release.open();
        }

        await expect(tool).toHaveAttribute('data-busy', 'false', {timeout: 15_000});
        await expect(page.getByTestId('pac-response-ignored')).toBeVisible();
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expect(inputRow(page, 0).getByTestId('pac-row-name')).toHaveValue(REVISED_NAME);
    });

    test('preserves the draft when the compute platform returns 503', async ({page}, testInfo) => {
        const user = testInfo.project.name === 'mobile' ? TEST_USER_2 : TEST_USER;
        const tool = await openPacTool(page, user);
        await fillScenario(page);

        await page.route('**/api/v1/tools/compute', async (route) => {
            await route.fulfill({status: 503, contentType: 'application/json', body: '{}'});
        });
        const responsePromise = page.waitForResponse((response) => isComputeRequest(response.request()), {timeout: 15_000});
        await page.getByTestId('pac-analyze').click();
        const response = await responsePromise;
        expect(response.status()).toBe(503);

        await expect(tool).toHaveAttribute('data-busy', 'false');
        await expect(page.getByTestId('pac-client-error')).toHaveAttribute('data-error-code', 'request_rejected');
        await expect(page.getByTestId('pac-platform-error')).toHaveCount(0);
        await expect(page.getByTestId('pac-result')).toHaveCount(0);
        await expect(page.getByTestId('pac-report-currency')).toHaveValue('EUR');
        await expect(page.getByTestId('pac-as-of-date')).toHaveValue(REFERENCE_DATE);
        await expect(inputRow(page, 0).getByTestId('pac-row-name')).toHaveValue(PRIMARY_NAME);
        await expect(inputRow(page, 0).getByTestId('pac-initial-quantity')).toHaveValue('10');
        await expect(inputRow(page, 0).getByTestId('pac-price')).toHaveValue('10');
        await expect(inputRow(page, 0).getByTestId('pac-target-percent')).toHaveValue('50');
        await expect(inputRow(page, 1).getByTestId('pac-row-name')).toHaveValue(SECONDARY_NAME);
        await expect(inputRow(page, 1).getByTestId('pac-initial-quantity')).toHaveValue('0');
        await expect(inputRow(page, 1).getByTestId('pac-price')).toHaveValue('10');
        await expect(inputRow(page, 1).getByTestId('pac-target-percent')).toHaveValue('50');
        await expect(page.getByTestId('pac-cash-currency')).toHaveValue('USD');
        await expect(page.getByTestId('pac-cash-amount')).toHaveValue('10');
        await expect(page.getByTestId('pac-contribution-currency')).toHaveValue('EUR');
        await expect(page.getByTestId('pac-contribution-amount')).toHaveValue('5');
        await expect(page.getByTestId('pac-rate-currency')).toHaveValue('USD');
        await expect(page.getByTestId('pac-rate-value')).toHaveValue('0.9');
        await expect(page.getByTestId('pac-rate-date')).toHaveValue(REFERENCE_DATE);
    });
});
