import {expect, type Locator, type Page, type Request} from '../fixtures/playwright';
import {login} from '../fixtures/auth-helpers';
import {TEST_USER} from '../fixtures/test-users';

export const COMPUTE_PATH = '/api/v1/tools/compute';
export const REPORT_PATH = '/api/v1/portfolio/report';
export const REFERENCE_DATE = '2024-09-08';

export type TestUser = typeof TEST_USER;

export const TEST_ALICE: TestUser = {
    username: 'e2e_user_alice',
    email: 'alice@test.example.com',
    password: 'AlicePass123!',
};

export const TEST_BOB: TestUser = {
    username: 'e2e_user_bob',
    email: 'bob@test.example.com',
    password: 'BobPass123!',
};

export const TEST_CAROL: TestUser = {
    username: 'e2e_user_carol',
    email: 'carol@test.example.com',
    password: 'CarolPass123!',
};

export const TEST_DAVE: TestUser = {
    username: 'e2e_user_dave',
    email: 'dave@test.example.com',
    password: 'DavePass123!',
};

export const TEST_EVE: TestUser = {
    username: 'e2e_user_eve',
    email: 'eve@test.example.com',
    password: 'EvePass123!',
};

export interface SourceQuoteWire {
    raw_price: string | null;
    currency: string;
    quote_base_quantity: number;
    reference_date: string | null;
    source: string | null;
    days_before_requested: number | null;
}

export interface SourceContextWire {
    context_key: string;
    broker_id: number;
    broker_name: string;
    broker_icon_url: string | null;
    broker_portal_url: string | null;
    broker_default_import_plugin: string | null;
    ownership_share_percent: string;
    custody_quantity: string;
}

export interface SourceAssetWire {
    asset_id: number;
    instrument_key: string;
    candidate_key: string;
    name: string;
    ticker: string | null;
    asset_type: string;
    icon_url: string | null;
    active: boolean;
    usage_scope: 'owned' | 'other_users' | 'observed';
    quote: SourceQuoteWire;
    contexts: SourceContextWire[];
}

export interface SourceCashBalanceWire {
    currency: string;
    amount: string;
}

export interface SourceCashSourceWire {
    broker_id: number;
    broker_name: string;
    broker_icon_url: string | null;
    broker_portal_url: string | null;
    broker_default_import_plugin: string | null;
    ownership_share_percent: string;
    balances: SourceCashBalanceWire[];
}

export interface AllocationSourceWire {
    generated_at: string;
    as_of_date: string;
    assets: SourceAssetWire[];
    cash_sources: SourceCashSourceWire[];
    selected_cash_balances: SourceCashBalanceWire[];
}

export interface AllocationSourceRequestWire {
    include_summary: boolean;
    include_history: boolean;
    include_allocation_history: boolean;
    include_positions_contribution: boolean;
    include_breakdown: boolean;
    allocation_source: {
        as_of_date: string;
        selected_cash_broker_ids: number[];
    };
}

export function principal(projectName: string, desktop: TestUser, mobile: TestUser): TestUser {
    return projectName === 'mobile' ? mobile : desktop;
}

export function only<T>(items: readonly T[], predicate: (item: T) => boolean, label: string): T {
    const matches = items.filter(predicate);
    expect(matches, label).toHaveLength(1);
    const match = matches.pop();
    if (match === undefined) throw new Error(`${label}: expected exactly one match`);
    return match;
}

export function gate(): {promise: Promise<void>; open: () => void} {
    let open!: () => void;
    const promise = new Promise<void>((resolve) => {
        open = resolve;
    });
    return {promise, open};
}

export function sourcePayload(
    asOfDate: string,
    assets: SourceAssetWire[],
    {
        cashSources = [],
        selectedCashBalances = [],
    }: {
        cashSources?: SourceCashSourceWire[];
        selectedCashBalances?: SourceCashBalanceWire[];
    } = {},
): AllocationSourceWire {
    return {
        generated_at: `${asOfDate}T12:00:00+00:00`,
        as_of_date: asOfDate,
        assets,
        cash_sources: cashSources,
        selected_cash_balances: selectedCashBalances,
    };
}

export function sourceRequestBody(request: Request): AllocationSourceRequestWire | null {
    if (request.method() !== 'POST' || new URL(request.url()).pathname !== REPORT_PATH) return null;
    const body = request.postDataJSON() as Partial<AllocationSourceRequestWire> | null;
    return body?.allocation_source ? (body as AllocationSourceRequestWire) : null;
}

export function sourceDateOf(request: Request): string | null {
    return sourceRequestBody(request)?.allocation_source.as_of_date ?? null;
}

export function exactSourceRequest(asOfDate: string, selectedCashBrokerIds: number[] = []): AllocationSourceRequestWire {
    return {
        include_summary: false,
        include_history: false,
        include_allocation_history: false,
        include_positions_contribution: false,
        include_breakdown: false,
        allocation_source: {
            as_of_date: asOfDate,
            selected_cash_broker_ids: selectedCashBrokerIds,
        },
    };
}

export async function routeAllocationSource(page: Page, resolve: (request: AllocationSourceRequestWire) => AllocationSourceWire | Promise<AllocationSourceWire>): Promise<void> {
    await page.route(`**${REPORT_PATH}`, async (route) => {
        const request = sourceRequestBody(route.request());
        if (request === null) {
            await route.fallback();
            return;
        }
        const payload = await resolve(request);
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                metadata: {
                    target_currency: 'EUR',
                    generated_at: payload.generated_at,
                },
                allocation_source: payload,
            }),
        });
    });
}

export function isComputeRequest(request: Request): boolean {
    return request.method() === 'POST' && new URL(request.url()).pathname === COMPUTE_PATH;
}

export async function runAndCaptureCompute(page: Page, action: () => Promise<void>) {
    await expect(page.getByTestId('toast-error')).toHaveCount(0);
    const roundTrip = Promise.all([page.waitForRequest(isComputeRequest, {timeout: 30_000}), page.waitForResponse((response) => isComputeRequest(response.request()), {timeout: 30_000})]).then(([request, response]) => ({request, response}));
    const interfaceError = page
        .getByTestId('toast-error')
        .waitFor({state: 'visible', timeout: 30_000})
        .then(() => {
            throw new Error('The tool interface reported an error before sending a compute request');
        });

    await action();
    return Promise.race([roundTrip, interfaceError]);
}

export async function openTool(page: Page, user: TestUser, toolCode: string, rootTestId: string): Promise<Locator> {
    await login(page, user);
    await page.goto(`/tools/${toolCode}`);
    const host = page.getByTestId('tool-host');
    await expect(host).toHaveAttribute('data-state', 'ready', {timeout: 30_000});
    await expect(host).toHaveAttribute('data-busy', 'false');
    const root = page.getByTestId(rootTestId);
    await expect(root).toBeVisible();
    await expect(root).toHaveAttribute('data-busy', 'false');
    return root;
}

async function optionsClosed(page: Page): Promise<void> {
    await expect(page.getByTestId(/^search-select-option-/)).toHaveCount(0);
}

export async function setDate(page: Page, testId: string, iso: string): Promise<void> {
    const input = page.getByTestId(testId);
    const root = page.getByTestId(`${testId}-root`);
    await expect(input).toBeVisible();
    await input.click();
    await expect(root).toHaveAttribute('data-open', 'true');
    await input.fill(iso);
    await input.press('Enter');
    await expect(input).toHaveValue(iso);
    await expect(root).toHaveAttribute('data-open', 'false');
    await expect(root).toHaveAttribute('data-invalid', 'false');
}

export async function selectCurrency(page: Page, testId: string, code: string): Promise<void> {
    await optionsClosed(page);
    const trigger = page.getByTestId(`${testId}-trigger`);
    await expect(trigger).toBeVisible();
    const option = page.getByTestId(`search-select-option-${code}`);
    await expect
        .poll(async () => {
            if (await option.isVisible()) return true;
            await trigger.click();
            return option.isVisible();
        })
        .toBe(true);
    await option.click();
    await optionsClosed(page);
    await expect(trigger).toContainText(code);
}

export interface IndexedField {
    field: Locator;
    index: string;
    testId: string;
}

export async function soleIndexedField(fields: Locator, prefix: string, label: string, excludedTestIds: ReadonlySet<string> = new Set()): Promise<IndexedField> {
    const candidates: IndexedField[] = [];
    for (const field of await fields.all()) {
        const testId = await field.getAttribute('data-testid');
        if (testId === null || excludedTestIds.has(testId)) continue;
        const match = new RegExp(`^${prefix}-(\\d+)$`).exec(testId);
        const [, index] = match ?? [];
        if (index !== undefined) candidates.push({field, index, testId});
    }
    expect(candidates, label).toHaveLength(1);
    const candidate = candidates.pop();
    if (candidate === undefined) throw new Error(`${label}: expected one indexed field`);
    return candidate;
}
