// @vitest-environment jsdom
/**
 * PacAllocatorTool — component test (Vitest + jsdom).
 *
 * This tool is a thin editor over one backend contract: the component builds a
 * typed `PacInput` draft from plain form fields and hands it to `runTool`
 * untouched (see `PacAllocatorTool.svelte`, `analyze()`: `$state.snapshot(draft)`
 * is sent as-is). Nothing about allocation, weighting or gaps is computed in the
 * browser — every number the result section shows comes from the mocked
 * `runTool` reply. So this spec mocks exactly that one boundary (`runTool` from
 * `$lib/features/tools/client`) and drives the rest — descriptor verification,
 * catalog validation, the account generation — through the real, unmocked
 * `$lib/features/tools/contracts` functions, the same way the production
 * renderer (`$lib/features/tools/registry.ts`) does before it ever mounts this
 * component. That keeps the descriptor genuinely branded/compatible instead of
 * a hand-typed stand-in, without needing a single cast.
 *
 * Fixtures are built from the generated `ToolInput`/`ToolOutput` projections for
 * `('pac_allocator', '1.0.0')` (`$lib/features/tools/contracts`), never from a
 * hand-rolled interface — the PAC financial shape (facts, ratios, money, issues)
 * is exactly as generated, so a schema change that breaks the component also
 * breaks this file's fixtures, not just its own tests.
 *
 * What it deliberately does NOT assert:
 *   - translated text. Every `$t(...)` string in the component is display-only;
 *     this file reads `data-testid`, `data-*` attributes, and — where the
 *     component itself concatenates a decimal string with a currency code or a
 *     numerator/denominator pair via plain template literals, not `$t()` — the
 *     resulting deterministic text (see `displayReportingFact`/`displayRatioFact`
 *     in the component, both untranslated formatting helpers).
 *   - CSS classes. The formatted/exact result state is asserted through the
 *     component's explicit `data-view` contract instead.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
import {getIndexColor} from '$lib/utils/colors';
import {ToolClientError, getCompiledToolContract, validateToolCatalog, verifyToolDescriptor, type CompatibleToolDescriptor, type ToolBatchMetrics, type ToolInput, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
import type {ToolItemResult, ToolRunOptions} from '$lib/features/tools/client';
import type {FetchPacAllocationSourceOptions, PacAllocationSource, PacAllocationSourceAsset, PacAllocationUsageScope} from './allocationSource';
import PacAllocatorTool from './PacAllocatorTool.svelte';

// =========================================================================
// The one boundary this spec mocks.
// =========================================================================
// `vi.mock` factories are hoisted above ordinary `const` declarations, so the
// mock itself must be created through `vi.hoisted` (see client.test.ts /
// ProviderAssignmentSection.test.ts for the same idiom).
const {runToolMock, fetchSourceMock, lookupFxRateMock, ensureCurrenciesLoadedMock} = vi.hoisted(() => ({
    runToolMock: vi.fn<(code: 'pac_allocator', version: '1.0.0', options: ToolRunOptions<'pac_allocator', '1.0.0'>) => Promise<ToolItemResult<'pac_allocator', '1.0.0'>>>(),
    fetchSourceMock: vi.fn<(asOfDate: string, accountGeneration: number, options?: FetchPacAllocationSourceOptions) => Promise<PacAllocationSource>>(),
    lookupFxRateMock: vi.fn<(base: string, quote: string, date: string) => Promise<FxDataPoint | null>>(),
    ensureCurrenciesLoadedMock: vi.fn(),
}));

vi.mock('$lib/features/tools/client', () => ({runTool: runToolMock}));
vi.mock('./allocationSource', () => ({fetchPacAllocationSource: fetchSourceMock}));
vi.mock('$lib/stores/fxStoreRegistry', () => ({lookupFxRate: lookupFxRateMock}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: ensureCurrenciesLoadedMock,
    currencyStoreVersion: {
        subscribe: (run: (value: number) => void) => {
            run(0);
            return () => undefined;
        },
    },
    getAllCurrencies: () => [
        {code: 'EUR', name: 'Euro fixture', symbol: '€', flag_emoji: '🇪🇺', country_codes: ['EU'], country_names: ['Fixture Europe']},
        {code: 'USD', name: 'Dollar fixture', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['Fixture United States']},
        {code: 'CHF', name: 'Franc fixture', symbol: 'CHF', flag_emoji: '🇨🇭', country_codes: ['CH'], country_names: ['Fixture Switzerland']},
    ],
    getCurrencyInfo: (code: string) => {
        const flags: Record<string, string> = {EUR: '🇪🇺', USD: '🇺🇸', CHF: '🇨🇭'};
        return {flag_emoji: flags[code] ?? '🏳️'};
    },
}));
vi.mock('$lib/utils/providerHelpers', () => ({
    assetProvidersVersion: {
        subscribe: (run: (value: number) => void) => {
            run(0);
            return () => undefined;
        },
    },
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderIconUrl: vi.fn((code: string) => `/test-provider-icons/${code}.svg`),
}));

// =========================================================================
// Generated-type projections. No financial interface is redeclared here: every
// alias below is a projection off the real `ToolInput`/`ToolOutput` for this
// tool, so a backend contract change that reshapes the PAC schema surfaces as a
// compile error in this file, not a silently-passing green.
// =========================================================================
type PacDescriptor = CompatibleToolDescriptor<'pac_allocator', '1.0.0'>;
type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;
type PacSuccess = Extract<ToolItemResult<'pac_allocator', '1.0.0'>, {status: 'success'}>;
type PacFailure = Extract<ToolItemResult<'pac_allocator', '1.0.0'>, {status: 'error'}>;
type PacError = PacFailure['error'];

type ReadyOutput = Extract<PacOutput, {availability: 'ready'}>;
type NeedsInputOutput = Extract<PacOutput, {availability: 'needs_input'}>;
type InvalidOutput = Extract<PacOutput, {availability: 'invalid'}>;
type UnsupportedOutput = Extract<PacOutput, {availability: 'unsupported'}>;

type RowFacts = ReadyOutput['rows'][number];
type Totals = ReadyOutput['totals'];
type CashPoolsFact = ReadyOutput['cash_pools'];
type AvailableCashPoolsFact = Extract<CashPoolsFact, {availability: 'available'}>;
type CashPool = AvailableCashPoolsFact['value'][number];
type Normalized = ReadyOutput['normalized'];
type InfoIssue = ReadyOutput['issues'][number];
type AnalyzeIssue = NeedsInputOutput['issues'][number];

type ReportingFact = Totals['initial_invested_reporting'];
type NativeMoneyFact = RowFacts['initial_value_native'];
type GapFact = Totals['max_abs_gap_pp'];
type SquaredGapFact = Totals['squared_gap_pp2'];
type PercentFact = RowFacts['current_weight_percent'];
type StringFact = Totals['target_total_percent'];

// =========================================================================
// Value-level fixture builders (money, ratios, facts). One shape per generated
// type, reused by every higher-level builder below — the "available" wrapper
// (`reason_codes: []`) is the only variant these tests need, since none of the
// five required behaviours depends on an "unavailable" backend fact.
// =========================================================================
function money(amount: string, currency: string): {amount: string; currency: string} {
    return {amount, currency};
}

function reportingFact(amount: string, currency: string): ReportingFact {
    return {availability: 'available', reason_codes: [], value: money(amount, currency)};
}

function nativeMoneyFact(amount: string, currency: string): NativeMoneyFact {
    return {availability: 'available', reason_codes: [], value: money(amount, currency)};
}

function percentFact(numerator: string, denominator: string, approximation: string): PercentFact {
    return {
        availability: 'available',
        reason_codes: [],
        value: {numerator, denominator, approximation, approximation_decimal_places: 28, approximation_exact: false, unit: 'percent'},
    };
}

function gapFact(numerator: string, denominator: string, approximation: string): GapFact {
    return {
        availability: 'available',
        reason_codes: [],
        value: {numerator, denominator, approximation, approximation_decimal_places: 28, approximation_exact: false, unit: 'percentage_points'},
    };
}

function squaredGapFact(numerator: string, denominator: string, approximation: string): SquaredGapFact {
    return {
        availability: 'available',
        reason_codes: [],
        value: {numerator, denominator, approximation, approximation_decimal_places: 28, approximation_exact: false, unit: 'percentage_points_squared'},
    };
}

function stringFact(value: string): StringFact {
    return {availability: 'available', reason_codes: [], value};
}

// =========================================================================
// Row / totals / cash-pool / issue / normalized-input fixtures.
// =========================================================================
function sampleRow(): RowFacts {
    return {
        row_key: 'server-row-1',
        instrument_key: 'server-instrument-1',
        name: 'ETF Global',
        row_index: 0,
        quantity: stringFact('12'),
        initial_value_native: nativeMoneyFact('1250', 'USD'),
        initial_value_reporting: reportingFact('1150', 'EUR'),
        current_weight_percent: percentFact('1150', '1150', '100'),
        target_percent: stringFact('100'),
        deviation_pp: gapFact('0', '1150', '0'),
    };
}

function sampleTotals(): Totals {
    return {
        initial_invested_reporting: reportingFact('1150', 'EUR'),
        existing_cash_reporting: reportingFact('500', 'EUR'),
        contributions_reporting: reportingFact('200', 'EUR'),
        cash_plus_contributions_reporting: reportingFact('700', 'EUR'),
        max_abs_gap_pp: gapFact('0', '1150', '0'),
        squared_gap_pp2: squaredGapFact('0', '1', '0'),
        target_total_percent: stringFact('100'),
    };
}

function samplePool(): CashPool {
    return {
        currency: 'EUR',
        existing_amount: '500',
        contribution_amount: '200',
        combined_amount: '700',
        existing_reporting: reportingFact('500', 'EUR'),
        contribution_reporting: reportingFact('200', 'EUR'),
        combined_reporting: reportingFact('700', 'EUR'),
    };
}

function sampleCashPools(): CashPoolsFact {
    return {availability: 'available', reason_codes: [], value: [samplePool()]};
}

function infoIssue(): InfoIssue {
    return {kind: 'info', code: 'reference_date_unspecified', params: {}, path: ['rows', 0, 'quote'], related_row_indices: [0]};
}

function missingIssue(): AnalyzeIssue {
    return {kind: 'missing', code: 'rows_required', params: {}, path: ['rows'], related_row_indices: []};
}

function invalidIssue(): AnalyzeIssue {
    return {kind: 'invalid', code: 'nonpositive_price', params: {}, path: ['rows', 0, 'quote', 'raw_price'], related_row_indices: [0]};
}

function unsupportedIssue(): AnalyzeIssue {
    return {kind: 'unsupported', code: 'currency_domain_exceeded', params: {}, path: ['report_currency'], related_row_indices: []};
}

function sampleNormalized(): Normalized {
    return {
        report_currency: 'EUR',
        as_of_date: null,
        rows: [
            {
                row_key: 'server-row-1',
                instrument_key: 'server-instrument-1',
                name: 'ETF Global',
                initial_quantity: '12',
                target_percent: '100',
                quote: {raw_price: '100', currency: 'EUR', quote_base_quantity: 1, reference_date: null},
                buy_grid: {mode: 'whole', quantity_step: '1'},
            },
        ],
        cash_balances: [{amount: '500', currency: 'EUR'}],
        contributions: [{amount: '200', currency: 'EUR', monetary_step: '0.01'}],
        valuation_rates: [],
    };
}

/** Fields shared, field-for-field, by all four `availability` variants. */
function baseOutputFields(): Omit<ReadyOutput, 'availability' | 'issues' | 'normalized'> {
    return {
        numeric_policy_id: 'pac-initial-state-v1',
        operation: 'analyze',
        optimization: 'not_run',
        result_kind: 'initial_state_analysis',
        trade_feasibility: 'not_evaluated',
        rows: [sampleRow()],
        totals: sampleTotals(),
        cash_pools: sampleCashPools(),
    };
}

function readyOutput(): ReadyOutput {
    return {...baseOutputFields(), availability: 'ready', issues: [infoIssue()], normalized: sampleNormalized()};
}

function needsInputOutput(): NeedsInputOutput {
    return {...baseOutputFields(), availability: 'needs_input', issues: [missingIssue()], normalized: null};
}

function invalidOutput(): InvalidOutput {
    return {...baseOutputFields(), availability: 'invalid', issues: [invalidIssue()], normalized: null};
}

function unsupportedOutput(): UnsupportedOutput {
    return {...baseOutputFields(), availability: 'unsupported', issues: [unsupportedIssue()], normalized: null};
}

// =========================================================================
// Metrics + wire-result fixtures (the `runTool` reply envelope).
// =========================================================================
function sampleItemMetrics(): ToolItemMetrics {
    return {
        cleanup_ms: 1,
        compute_ms: 4,
        execution_ms: 6,
        input_validation_ms: 1,
        output_validation_ms: 1,
        queue_wait_ms: 2,
        serialization_ms: 1,
        startup_ms: 1,
        total_ms: 17,
    };
}

function sampleBatchMetrics(): ToolBatchMetrics {
    return {server_processing_ms: 17};
}

function successResult(correlationId: string, output: PacOutput, accountGeneration: number): PacSuccess {
    return {
        contract_version: '1.0.0',
        correlation_id: correlationId,
        execution_id: `${correlationId}-exec`,
        implementation_version: '1.0.0',
        metrics: sampleItemMetrics(),
        schema_fingerprint: 'f'.repeat(64),
        status: 'success',
        tool_code: 'pac_allocator',
        accountGeneration,
        batch: {failed_count: 0, metrics: sampleBatchMetrics(), request_id: `${correlationId}-batch`, success_count: 1},
        result: output,
    };
}

function errorResult(correlationId: string, code: PacError['code'], retryable: boolean, accountGeneration: number): PacFailure {
    return {
        contract_version: '1.0.0',
        correlation_id: correlationId,
        execution_id: `${correlationId}-exec`,
        implementation_version: '1.0.0',
        metrics: sampleItemMetrics(),
        schema_fingerprint: 'f'.repeat(64),
        status: 'error',
        tool_code: 'pac_allocator',
        accountGeneration,
        batch: {failed_count: 1, metrics: sampleBatchMetrics(), request_id: `${correlationId}-batch`, success_count: 0},
        error: {code, issue_count: 1, issues: [], retryable},
    };
}

/** A promise the test decides when to settle — the SyncModalBase.test.ts idiom. */
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void; reject: (reason?: unknown) => void} {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return {promise, resolve, reject};
}

// =========================================================================
// Descriptor / catalog setup. Rebuilt for each test through the real, unmocked
// `contracts.ts` functions so the descriptor the component receives is
// genuinely branded/compatible — the same path the production renderer takes
// (see `registry.ts`) — rather than a hand-typed stand-in.
// =========================================================================
let descriptor: PacDescriptor;
let accountGeneration: number;
let accountSequence = 0;

function makeDescriptor(): PacDescriptor {
    const contract = getCompiledToolContract('pac_allocator', '1.0.0');
    if (!contract) throw new Error('pac_allocator/1.0.0 tool contract is not compiled — run the API client generation step first.');
    const rawCatalog = {
        catalog_version: '1',
        items: [
            {
                tool_code: contract.toolCode,
                contract_version: contract.contractVersion,
                implementation_version: '1.0.0',
                schema_fingerprint: contract.schemaFingerprint,
                category: 'analysis',
                description: 'PAC allocator pilot tool.',
                description_i18n_key: null,
                documentation: {path: 'tools/pac-allocator', version: '1.0.0'},
                icon_key: 'calculator',
                input_schema: {},
                name: 'PAC allocator',
                name_i18n_key: null,
                operations: contract.operations.map((operation) => ({
                    operation,
                    deduplication: 'none',
                    deterministic: true,
                    job_timeout_ms: 30_000,
                    max_parameter_bytes: 65_536,
                    max_result_bytes: 65_536,
                    pure: true,
                    queue_timeout_ms: 30_000,
                    soft_timeout_ms: 30_000,
                })),
                output_schema: {},
                ui: {kind: 'custom', component_key: contract.componentKey, ui_contract_version: contract.uiContractVersion},
            },
        ],
        policy: {
            cleanup_timeout_ms: 5_000,
            client_timeout_ms: 30_000,
            envelope_reserve_bytes: 1_024,
            ingress_timeout_ms: 30_000,
            job_timeout_ms: 30_000,
            max_batch_items: 1,
            max_batches_per_principal: 1,
            max_json_depth: 16,
            max_parameter_bytes: 65_536,
            max_pending_items: 4,
            max_pending_per_principal: 4,
            max_request_bytes: 65_536,
            max_response_bytes: 65_536,
            max_result_bytes: 65_536,
            output_reserve_ms: 1_000,
            queue_timeout_ms: 30_000,
            request_timeout_ms: 30_000,
            response_reserve_ms: 1_000,
            soft_timeout_ms: 30_000,
            workers: 1,
        },
        unavailable: [],
    };
    const catalog = validateToolCatalog(rawCatalog, accountGeneration);
    return verifyToolDescriptor(catalog, 'pac_allocator', '1.0.0');
}

function localIsoOffset(days: number): string {
    const date = new Date();
    date.setDate(date.getDate() + days);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function ownedAsset(overrides: Partial<PacAllocationSourceAsset> = {}): PacAllocationSourceAsset {
    const base: PacAllocationSourceAsset = {
        assetId: 17,
        instrumentKey: 'asset:17',
        candidateKey: 'candidate:asset:17',
        name: 'Fixture global ETF',
        ticker: 'FIX',
        assetType: 'ETF',
        iconUrl: null,
        active: true,
        usageScope: 'owned',
        quote: {
            rawPrice: '123.450000000001',
            currency: 'USD',
            quoteBaseQuantity: 100,
            referenceDate: '2026-09-09',
            source: 'fixture-close',
            daysBeforeRequested: 1,
        },
        contexts: [
            {
                contextKey: 'asset:17:broker:3',
                brokerId: 3,
                brokerName: 'Fixture broker A',
                brokerIconUrl: null,
                brokerPortalUrl: null,
                brokerDefaultImportPlugin: null,
                ownershipSharePercent: '25',
                custodyQuantity: '12.345678901234',
            },
            {
                contextKey: 'asset:17:broker:4',
                brokerId: 4,
                brokerName: 'Fixture broker B',
                brokerIconUrl: null,
                brokerPortalUrl: null,
                brokerDefaultImportPlugin: null,
                ownershipSharePercent: '75',
                custodyQuantity: '7.000000000001',
            },
        ],
    };
    return {
        ...base,
        ...overrides,
        quote: {...base.quote, ...overrides.quote},
        contexts: overrides.contexts ?? base.contexts,
    };
}

function catalogCandidate(overrides: Partial<PacAllocationSourceAsset> = {}): PacAllocationSourceAsset {
    const candidate = ownedAsset({
        assetId: 19,
        instrumentKey: 'asset:19',
        candidateKey: 'candidate:asset:19',
        name: 'Fixture zero-position catalog candidate',
        ticker: 'ZERO',
        quote: {
            rawPrice: '88.765432100001',
            currency: 'CHF',
            quoteBaseQuantity: 100,
            referenceDate: '2026-09-08',
            source: 'fixture-catalog-close',
            daysBeforeRequested: 2,
        },
        contexts: [],
    });
    return {
        ...candidate,
        ...overrides,
        quote: {...candidate.quote, ...overrides.quote},
        contexts: overrides.contexts ?? candidate.contexts,
    };
}

const OWNER_CASH_SOURCES: PacAllocationSource['cashSources'] = [
    {
        brokerId: 3,
        brokerName: 'Fixture owner broker A',
        brokerIconUrl: null,
        brokerPortalUrl: null,
        brokerDefaultImportPlugin: 'fixture-owner-a',
        ownershipSharePercent: '25',
        balances: [
            {currency: 'EUR', amount: '100.10'},
            {currency: 'USD', amount: '5.50'},
        ],
    },
    {
        brokerId: 4,
        brokerName: 'Fixture owner broker B',
        brokerIconUrl: null,
        brokerPortalUrl: null,
        brokerDefaultImportPlugin: 'fixture-owner-b',
        ownershipSharePercent: '75',
        balances: [
            {currency: 'EUR', amount: '300.20'},
            {currency: 'CHF', amount: '7.25'},
        ],
    },
];

const BACKEND_SELECTED_CASH_BALANCES: PacAllocationSource['selectedCashBalances'] = [
    {currency: 'EUR', amount: '777.770000000001'},
    {currency: 'USD', amount: '8.880000000001'},
];

function allocationSource(asOfDate: string, assets: readonly PacAllocationSourceAsset[] = [], cash: Partial<Pick<PacAllocationSource, 'cashSources' | 'selectedCashBalances'>> = {}): PacAllocationSource {
    return {
        generatedAt: `${asOfDate}T12:00:00Z`,
        asOfDate,
        assets,
        cashSources: cash.cashSources ?? [],
        selectedCashBalances: cash.selectedCashBalances ?? [],
    };
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    transitionClientSession(`pac-allocator-component-test-${++accountSequence}`);
    accountGeneration = getClientSessionGeneration();
    descriptor = makeDescriptor();
    userSettings.setDirect({language: 'en', base_currency: 'EUR', theme: 'auto', avatar_url: null});
    runToolMock.mockReset();
    fetchSourceMock.mockReset();
    fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate));
    lookupFxRateMock.mockReset();
    lookupFxRateMock.mockResolvedValue(null);
    ensureCurrenciesLoadedMock.mockReset();
    ensureCurrenciesLoadedMock.mockResolvedValue(undefined);
});

// =========================================================================
// Render + DOM helpers.
// =========================================================================
function renderTool() {
    return render(PacAllocatorTool, {descriptor, accountGeneration});
}

/** The single `pac-row` article at a given index, identified by its own attribute — never by position in an unfiltered list. */
function rowByIndex(index: number): HTMLElement {
    const matches = screen.queryAllByTestId('pac-row').filter((row) => row.getAttribute('data-row-index') === String(index));
    expect(matches, `pac-row with data-row-index="${index}"`).toHaveLength(1);
    return matches[0]!;
}

function scopeChip(scope: PacAllocationUsageScope): HTMLButtonElement {
    return screen.getByTestId(`pac-asset-scope-${scope}`) as HTMLButtonElement;
}

function scopeCount(scope: PacAllocationUsageScope): number {
    const counter = scopeChip(scope).lastElementChild;
    if (!counter) throw new Error(`scope ${scope} has no count`);
    const count = Number(counter.textContent);
    if (!Number.isInteger(count)) throw new Error(`scope ${scope} count is not an integer: ${counter.textContent ?? '<null>'}`);
    return count;
}

function visibleAssetCardTestIds(): string[] {
    return screen.getAllByTestId(/^pac-owned-asset-\d+$/).map((card) => {
        const testId = card.getAttribute('data-testid');
        if (!testId) throw new Error('asset card has no data-testid');
        return testId;
    });
}

function field(testid: string): HTMLInputElement {
    return screen.getByTestId(testid) as HTMLInputElement;
}

function expectResultGuidance(): void {
    expect(screen.getByTestId('pac-denominator-note')).toBeInTheDocument();
    const cashPools = screen.getByTestId('pac-cash-pools');
    const nativePoolExplanation = cashPools.children.item(1);
    expect(nativePoolExplanation?.tagName).toBe('P');
    expect(nativePoolExplanation?.textContent?.trim()).toBeTruthy();
}

async function addManualRow(): Promise<HTMLElement> {
    await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
    return rowByIndex(screen.getAllByTestId('pac-row').length - 1);
}

async function selectCurrency(testId: string, value: string): Promise<void> {
    const trigger = screen.getByTestId(`${testId}-trigger`);
    await fireEvent.click(trigger);
    const listbox = await screen.findByRole('listbox');
    await fireEvent.click(within(listbox).getByTestId(`search-select-option-${value}`));
    await waitFor(() => expect(screen.queryByRole('listbox')).toBeNull());
}

async function useManualCash(): Promise<void> {
    await fireEvent.click(screen.getByTestId('pac-cash-use-manual'));
    await waitFor(() => expect(screen.getAllByTestId('pac-cash-row')).toHaveLength(1));
}

async function useBrokerCash(): Promise<void> {
    await fireEvent.click(screen.getByTestId('pac-cash-use-brokers'));
    await waitFor(() => expect(screen.getByTestId('pac-cash-broker-copy')).toBeInTheDocument());
}

async function addContribution(): Promise<void> {
    const before = screen.queryAllByTestId('pac-contributions-row').length;
    await fireEvent.click(screen.getByTestId('pac-add-contributions'));
    await waitFor(() => expect(screen.getAllByTestId('pac-contributions-row')).toHaveLength(before + 1));
}

function expectScopeColor(element: HTMLElement, scope: PacAllocationUsageScope): void {
    const scopeOrder: readonly PacAllocationUsageScope[] = ['owned', 'other_users', 'observed'];
    const expected = getIndexColor(scopeOrder.indexOf(scope), 140);
    expect(element).toHaveAttribute('data-scope-color', scope);
    expect(element.style.getPropertyValue('--scope-bg')).toBe(expected.bg);
    expect(element.style.getPropertyValue('--scope-text')).toBe(expected.text);
    expect(element.style.getPropertyValue('--scope-dark-bg')).toBe(expected.darkBg);
    expect(element.style.getPropertyValue('--scope-dark-text')).toBe(expected.darkText);
    expect(element.style.getPropertyValue('--scope-border')).toBe(expected.vivid);
}

/**
 * `ConfirmModal` shows its item list outright when there is exactly one item and
 * collapses it behind a toggle as soon as there are more
 * (`shouldShowItems = items.length === 1 || showItems`). A multi-context
 * description therefore has to be opened before it can be read.
 *
 * The toggle carries no test id and its label is translated, so it is identified
 * structurally instead: within this confirmation it is the only button that is
 * neither the header's close cross (a hardcoded `aria-label="Close"`, not a
 * translated string) nor one of the two footer actions, both of which do carry
 * test ids. The filter is asserted to resolve to exactly one button, so a future
 * button added to the modal body fails here rather than silently clicking the
 * wrong thing.
 */
async function expandConfirmationItems(testId: string): Promise<void> {
    const modal = screen.getByTestId(testId).closest('[role="dialog"]');
    if (!modal) throw new Error(`confirmation ${testId} is not inside a dialog`);
    const toggles = within(modal as HTMLElement)
        .getAllByRole('button')
        .filter((button) => !button.dataset.testid && button.getAttribute('aria-label') !== 'Close');
    expect(toggles).toHaveLength(1);
    await fireEvent.click(toggles[0]!);
}

function queueSuccess(output: PacOutput = readyOutput()): void {
    runToolMock.mockImplementationOnce(async (_code, _version, options) => successResult(options.correlationId, output, accountGeneration));
}

async function analyzeAndReadInput(output: PacOutput = readyOutput()): Promise<ToolInput<'pac_allocator', '1.0.0'>> {
    const callIndex = runToolMock.mock.calls.length;
    queueSuccess(output);
    await fireEvent.click(screen.getByTestId('pac-analyze'));
    await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(callIndex + 1));
    await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
    const call = runToolMock.mock.calls[callIndex];
    if (!call) throw new Error(`runTool call ${callIndex} not found`);
    return call[2].parameters;
}

describe('PacAllocatorTool (pac-allocator)', () => {
    it('starts with compact valuation controls, no report-only FX, and funding before the asset gallery', async () => {
        userSettings.setDirect({language: 'en', base_currency: 'CHF', theme: 'auto', avatar_url: null});
        renderTool();

        expect(screen.getByTestId('pac-no-rows')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-row')).toHaveLength(0);
        const scenario = screen.getByTestId('pac-scenario');
        const reportCurrency = within(scenario).getByTestId('pac-report-currency');
        const reportCurrencyTrigger = within(scenario).getByTestId('pac-report-currency-trigger');
        const asOfRoot = within(scenario).getByTestId('pac-as-of-date-root');
        const asOfDate = within(asOfRoot).getByTestId('pac-as-of-date');
        const reportLabel = reportCurrency.parentElement;
        const asOfLabel = asOfRoot.parentElement;

        expect(reportCurrency).toContainElement(reportCurrencyTrigger);
        expect(reportLabel?.tagName).toBe('LABEL');
        expect(asOfLabel?.tagName).toBe('LABEL');
        expect(reportLabel?.parentElement).toBe(asOfLabel?.parentElement);
        expect(reportLabel?.parentElement?.children).toHaveLength(2);
        expect(reportLabel?.nextElementSibling).toBe(asOfLabel);
        expect(within(scenario).getByTestId('pac-valuation-settings-info')).toBeInTheDocument();
        expect(asOfDate).toHaveAttribute('type', 'text');
        expect(asOfDate).toHaveValue(localIsoOffset(0));

        const asOfLabels = Array.from(scenario.getElementsByTagName('label')).filter((label) => label.contains(asOfRoot));
        expect(asOfLabels).toEqual([asOfLabel]);
        expect(asOfRoot.getElementsByTagName('label')).toHaveLength(0);
        const externalAsOfText = asOfLabel?.children.item(0)?.textContent?.trim();
        expect(externalAsOfText).toBeTruthy();
        expect(asOfRoot.textContent?.includes(externalAsOfText ?? '')).toBe(false);

        await waitFor(() => expect(reportCurrencyTrigger).toHaveTextContent('CHF'));
        expect(screen.queryByTestId('pac-valuation-rates')).toBeNull();
        expect(screen.getByTestId('pac-cash-broker-copy')).toBeInTheDocument();
        const cashAction = screen.getByTestId('pac-cash-use-manual');
        expect(cashAction).toBeInTheDocument();
        const cashHeaderButtons = Array.from(cashAction.parentElement?.children ?? []).filter((element) => element.tagName === 'BUTTON');
        expect(cashHeaderButtons).toHaveLength(1);
        expect(cashHeaderButtons[0]).toBe(cashAction);
        expect(screen.queryByTestId('pac-cash-use-brokers')).toBeNull();
        expect(screen.getByTestId('pac-contributions-empty')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-contributions-row')).toHaveLength(0);

        const funding = screen.getByTestId('pac-funding');
        const gallery = await screen.findByTestId('pac-owned-assets');
        expect(funding.compareDocumentPosition(gallery) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    });

    it('falls back to EUR when user settings have not supplied a base currency', async () => {
        userSettings.reset();
        renderTool();

        await waitFor(() => expect(screen.getByTestId('pac-report-currency-trigger')).toHaveTextContent('EUR'));
    });

    it('keeps manual entry available while the allocation source is loading', async () => {
        const pending = deferred<PacAllocationSource>();
        fetchSourceMock.mockReturnValueOnce(pending.promise);
        renderTool();

        expect(await screen.findByTestId('pac-owned-assets-loading')).toBeInTheDocument();
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();
        await fireEvent.click(addManual);
        expect(rowByIndex(0)).toBeInTheDocument();

        pending.resolve(allocationSource(localIsoOffset(0)));
    });

    it('keeps a pending draft intact when the allocation source fails and manual cash fallback works', async () => {
        const failedSelection = deferred<PacAllocationSource>();
        fetchSourceMock.mockImplementation((asOfDate, _requestedGeneration, options = {}) => {
            const selectedBrokerIds = [...(options.selectedCashBrokerIds ?? [])];
            if (selectedBrokerIds.length === 0) {
                return Promise.resolve(allocationSource(asOfDate, [], {cashSources: OWNER_CASH_SOURCES}));
            }
            if (selectedBrokerIds.join(',') === '3') return failedSelection.promise;
            throw new Error(`unexpected selected cash brokers ${selectedBrokerIds.join(',')}`);
        });
        renderTool();
        await screen.findByTestId('pac-owned-assets-empty');

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Draft survives source failure'}});
        const broker = await screen.findByTestId('pac-cash-broker-3');
        await waitFor(() => expect(broker).toBeEnabled());
        await fireEvent.click(broker);
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'pending'));
        failedSelection.reject(new ToolClientError('network', 'network_failed'));

        expect(await screen.findByTestId('pac-cash-source-error')).toBeInTheDocument();
        expect(await screen.findByTestId('pac-owned-assets-error')).toBeInTheDocument();
        expect(rowByIndex(0)).toBeInTheDocument();
        expect(field('pac-display-name-0')).toHaveValue('Draft survives source failure');
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();
        await fireEvent.click(addManual);
        expect(rowByIndex(1)).toBeInTheDocument();
        await fireEvent.input(field('pac-display-name-1'), {target: {value: 'Manual fallback row'}});

        await useManualCash();
        await selectCurrency('pac-cash-currency-0', 'EUR');
        await fireEvent.input(field('pac-cash-amount-0'), {target: {value: '321.450000000001'}});

        const parameters = await analyzeAndReadInput();
        expect(parameters.rows?.find((row) => row.name === 'Draft survives source failure')).toBeDefined();
        expect(parameters.cash_balances).toEqual([{currency: 'EUR', amount: '321.450000000001'}]);
    });

    it('keeps manual entry available for an empty allocation source', async () => {
        renderTool();

        expect(await screen.findByTestId('pac-owned-assets-empty')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        expect(rowByIndex(0)).toBeInTheDocument();
    });

    it('renders manual initial and target sections, keeps grid defaults coherent, and accepts only positive integer quote bases', async () => {
        renderTool();
        const row = await addManualRow();

        expect(screen.getByTestId('pac-report-currency')).toContainElement(screen.getByTestId('pac-report-currency-trigger'));
        expect(screen.getByTestId('pac-as-of-date')).toHaveAttribute('type', 'text');
        expect(row).toHaveAttribute('data-origin', 'manual');
        expect(row).toHaveAttribute('data-source-mode', 'manual');
        expect(within(row).getByTestId('pac-initial-state-0')).toBeInTheDocument();
        expect(within(row).getByTestId('pac-target-state-0')).toBeInTheDocument();
        expect(screen.getByTestId('pac-asset-currency-0')).toContainElement(screen.getByTestId('pac-asset-currency-0-trigger'));
        expect(screen.getByTestId('pac-price-date-0')).toHaveAttribute('type', 'text');
        expect(screen.getByTestId('pac-grid-mode-0')).toContainElement(screen.getByTestId('pac-grid-whole-0'));
        expect(screen.getByTestId('pac-grid-mode-0')).toContainElement(screen.getByTestId('pac-grid-fractional-0'));

        for (const testid of ['pac-initial-quantity-0', 'pac-raw-price-0', 'pac-target-weight-0', 'pac-step-quantity-0']) {
            expect(screen.getByTestId(testid)).toHaveAttribute('type', 'text');
            expect(screen.getByTestId(testid)).toHaveAttribute('inputmode', 'decimal');
        }

        const whole = screen.getByTestId('pac-grid-whole-0');
        const fractional = screen.getByTestId('pac-grid-fractional-0');
        const quantityStep = field('pac-step-quantity-0');
        expect(whole).toHaveAttribute('aria-pressed', 'true');
        expect(fractional).toHaveAttribute('aria-pressed', 'false');
        expect(quantityStep).toHaveValue('1');

        await fireEvent.click(fractional);
        expect(fractional).toHaveAttribute('aria-pressed', 'true');
        expect(quantityStep).toHaveValue('0.001');
        await fireEvent.click(whole);
        expect(whole).toHaveAttribute('aria-pressed', 'true');
        expect(quantityStep).toHaveValue('1');

        await fireEvent.input(quantityStep, {target: {value: '5'}});
        await fireEvent.click(fractional);
        expect(quantityStep).toHaveValue('5');
        await fireEvent.click(whole);
        expect(quantityStep).toHaveValue('5');

        const quoteBasis = field('pac-price-basis-0');
        expect(quoteBasis).toHaveAttribute('type', 'number');
        expect(quoteBasis).toHaveAttribute('inputmode', 'numeric');
        expect(quoteBasis).toHaveAttribute('min', '1');
        expect(quoteBasis).toHaveAttribute('step', '1');
        expect(quoteBasis).toBeRequired();

        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Manual quote-basis fixture'}});
        await fireEvent.input(quoteBasis, {target: {value: '1000'}});
        expect(quoteBasis).toBeValid();
        const accepted = await analyzeAndReadInput();
        const manualRow = accepted.rows?.[0];
        if (!manualRow) throw new Error('manual row was not serialized');
        expect(manualRow.quote?.quote_base_quantity).toBe(1000);
        expect(within(row).queryByTestId('pac-instrument-id-0')).toBeNull();
        expect(within(row).queryByTestId('pac-custody-context-0')).toBeNull();
        expect(row).not.toHaveTextContent(manualRow.instrument_key);
        expect(row).not.toHaveTextContent(manualRow.row_key);

        const acceptedCalls = runToolMock.mock.calls.length;
        await fireEvent.input(quoteBasis, {target: {value: '0'}});
        expect(quoteBasis.validity.rangeUnderflow).toBe(true);
        expect(quoteBasis).toBeInvalid();
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        expect(runToolMock).toHaveBeenCalledTimes(acceptedCalls);

        await fireEvent.input(quoteBasis, {target: {value: '1.5'}});
        expect(quoteBasis.validity.stepMismatch).toBe(true);
        expect(quoteBasis).toBeInvalid();
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        expect(runToolMock).toHaveBeenCalledTimes(acceptedCalls);
    });

    it('caps manual cash and contribution rows independently at four', async () => {
        renderTool();

        await useManualCash();
        const addCash = screen.getByTestId('pac-add-cash');
        for (let index = 1; index < 4; index += 1) await fireEvent.click(addCash);
        expect(screen.getAllByTestId('pac-cash-row')).toHaveLength(4);
        expect(addCash).toBeDisabled();

        await addContribution();
        const addContributionButton = screen.getByTestId('pac-add-contributions');
        for (let index = 1; index < 4; index += 1) await fireEvent.click(addContributionButton);
        expect(screen.getAllByTestId('pac-contributions-row')).toHaveLength(4);
        expect(addContributionButton).toBeDisabled();
    });

    it('starts contributions empty, creates report-currency cents, and removes the last row without coupling quantity quantum', async () => {
        renderTool();
        await screen.findByTestId('pac-owned-assets-empty');

        expect(screen.getByTestId('pac-contributions-empty')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-contributions-row')).toHaveLength(0);
        const empty = await analyzeAndReadInput();
        expect(empty.cash_balances).toEqual([]);
        expect(empty.contributions).toEqual([]);

        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Independent quantity quantum'}});
        const quantityStep = field('pac-step-quantity-0');
        await fireEvent.input(quantityStep, {target: {value: '0.125'}});

        await addContribution();
        expect(screen.getByTestId('pac-contributions-currency-0-trigger')).toHaveTextContent('EUR');
        const monetaryStep = field('pac-contributions-monetary-step-0');
        expect(monetaryStep).toHaveValue('0.01');
        await fireEvent.input(field('pac-contributions-amount-0'), {target: {value: '200.000000000001'}});
        await fireEvent.input(monetaryStep, {target: {value: '0.000000000001'}});
        expect(quantityStep).toHaveValue('0.125');

        const custom = await analyzeAndReadInput();
        expect(custom.contributions).toEqual([{currency: 'EUR', amount: '200.000000000001', monetary_step: '0.000000000001'}]);
        const ownedRow = custom.rows?.find((row) => row.name === 'Independent quantity quantum');
        if (!ownedRow) throw new Error('manual row with independent quantity quantum was not serialized');
        expect(ownedRow.buy_grid?.quantity_step).toBe('0.125');

        await fireEvent.click(screen.getByTestId('pac-remove-contributions-0'));
        expect(screen.getByTestId('pac-contributions-empty')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-contributions-row')).toHaveLength(0);
        expect((await analyzeAndReadInput()).contributions).toEqual([]);
    });

    it('sends a manually filled draft without computing an economic result in the browser', async () => {
        const {promise, resolve} = deferred<PacSuccess>();
        runToolMock.mockImplementationOnce(() => promise);
        renderTool();
        await addManualRow();

        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Local ETF'}});
        await fireEvent.input(field('pac-initial-quantity-0'), {target: {value: '10.000000000001'}});
        await fireEvent.input(field('pac-raw-price-0'), {target: {value: '100.000000000001'}});
        await selectCurrency('pac-asset-currency-0', 'EUR');
        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '100'}});

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));

        const call = runToolMock.mock.calls[0];
        if (!call) throw new Error('runTool was not called');
        const [code, version, options] = call;
        expect(code).toBe('pac_allocator');
        expect(version).toBe('1.0.0');
        const parameters = options.parameters;
        expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'cash_balances', 'contributions', 'operation', 'report_currency', 'rows', 'valuation_rates']);
        expect(parameters).toMatchObject({
            operation: 'analyze',
            report_currency: 'EUR',
            cash_balances: [],
            contributions: [],
            valuation_rates: [],
        });
        expect(parameters.rows).toHaveLength(1);
        expect(parameters.rows?.[0]).toMatchObject({
            name: 'Local ETF',
            initial_quantity: '10.000000000001',
            target_percent: '100',
            quote: {raw_price: '100.000000000001', currency: 'EUR'},
        });

        expect(screen.queryByTestId('pac-result')).toBeNull();
        resolve(successResult(options.correlationId, readyOutput(), accountGeneration));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
    });

    it('filters and orders a counted multi-scope gallery while hidden selections survive and foreign details stay private', async () => {
        const baseContext = ownedAsset().contexts[0]!;
        const inactiveOwned = ownedAsset({
            assetId: 41,
            instrumentKey: 'asset:41',
            candidateKey: 'candidate:asset:41',
            name: 'Owned archive',
            ticker: 'OWN-OLD',
            active: false,
            contexts: [],
        });
        const activeOther = ownedAsset({
            assetId: 42,
            instrumentKey: 'asset:42',
            candidateKey: 'candidate:asset:42',
            name: 'Needle foreign active',
            ticker: 'OTHER',
            usageScope: 'other_users',
            contexts: [
                {
                    ...baseContext,
                    contextKey: 'asset:42:broker:942',
                    brokerId: 942,
                    brokerName: 'Foreign broker secret 42',
                    brokerPortalUrl: 'https://foreign.invalid/42',
                    brokerDefaultImportPlugin: 'foreign-secret-plugin-42',
                    ownershipSharePercent: '37.5',
                    custodyQuantity: '987654.321001',
                },
            ],
        });
        const inactiveObserved = ownedAsset({
            assetId: 43,
            instrumentKey: 'asset:43',
            candidateKey: 'candidate:asset:43',
            name: 'Observed archive',
            ticker: 'OBS-OLD',
            active: false,
            usageScope: 'observed',
            contexts: [
                {
                    ...baseContext,
                    contextKey: 'asset:43:broker:943',
                    brokerId: 943,
                    brokerName: 'Observed broker secret 43',
                    brokerPortalUrl: 'https://foreign.invalid/43',
                    brokerDefaultImportPlugin: 'foreign-secret-plugin-43',
                    ownershipSharePercent: '62.5',
                    custodyQuantity: '123456.789001',
                },
            ],
        });
        const selectedOwned = ownedAsset({
            assetId: 44,
            instrumentKey: 'asset:44',
            candidateKey: 'candidate:asset:44',
            name: 'Selected owned active',
            // Search is deliberately name-only: this ticker must not make the
            // card match the "Needle" query below.
            ticker: 'NEEDLE',
            contexts: [
                {
                    ...baseContext,
                    contextKey: 'asset:44:broker:944',
                    brokerId: 944,
                    brokerName: 'Owned broker 44',
                    ownershipSharePercent: '100',
                    custodyQuantity: '44.000000000001',
                },
            ],
        });
        const activeObserved = ownedAsset({
            assetId: 45,
            instrumentKey: 'asset:45',
            candidateKey: 'candidate:asset:45',
            name: 'Observed active',
            ticker: 'OBS',
            usageScope: 'observed',
            contexts: [],
        });
        const inactiveOther = ownedAsset({
            assetId: 46,
            instrumentKey: 'asset:46',
            candidateKey: 'candidate:asset:46',
            name: 'Other users archive',
            ticker: 'OTHER-OLD',
            active: false,
            usageScope: 'other_users',
            contexts: [],
        });
        const privateCashAmount = '654321.090001';
        fetchSourceMock.mockImplementation(async (asOfDate: string) =>
            allocationSource(asOfDate, [inactiveOwned, activeOther, inactiveObserved, selectedOwned, activeObserved, inactiveOther], {
                cashSources: [
                    {
                        brokerId: 942,
                        brokerName: 'Foreign broker secret 42',
                        brokerIconUrl: null,
                        brokerPortalUrl: 'https://foreign.invalid/42',
                        brokerDefaultImportPlugin: 'foreign-secret-plugin-42',
                        ownershipSharePercent: '37.5',
                        balances: [{currency: 'CHF', amount: privateCashAmount}],
                    },
                ],
            }),
        );
        renderTool();

        const selectedOwnedCard = await screen.findByTestId('pac-owned-asset-44');
        expect(scopeChip('owned')).toHaveAttribute('aria-pressed', 'true');
        expect(scopeChip('other_users')).toHaveAttribute('aria-pressed', 'false');
        expect(scopeChip('observed')).toHaveAttribute('aria-pressed', 'false');
        expect(scopeCount('owned')).toBe(2);
        expect(scopeCount('other_users')).toBe(2);
        expect(scopeCount('observed')).toBe(2);
        for (const scope of ['owned', 'other_users', 'observed'] as const) {
            const chip = scopeChip(scope);
            expectScopeColor(chip, scope);
            expect((chip.textContent ?? '').replace(String(scopeCount(scope)), '').trim()).not.toBe('');
        }
        expect(visibleAssetCardTestIds()).toEqual(['pac-owned-asset-44', 'pac-owned-asset-41']);
        expect(screen.queryByTestId('pac-owned-asset-42')).toBeNull();
        expect(screen.queryByTestId('pac-owned-asset-43')).toBeNull();
        expect(screen.queryByTestId('pac-owned-asset-45')).toBeNull();
        expect(screen.queryByTestId('pac-owned-asset-46')).toBeNull();

        await fireEvent.click(selectedOwnedCard);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(rowByIndex(0)).toHaveAttribute('data-origin', 'portfolio_context');
        expect(rowByIndex(0)).toHaveAttribute('data-source-mode', 'locked');
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('44.000000000001');
        expect(rowByIndex(0)).not.toHaveTextContent('asset:44:broker:944');
        expect(selectedOwnedCard).toHaveTextContent('🇺🇸');
        expect(selectedOwnedCard).toHaveTextContent('USD');
        expect(selectedOwnedCard).toHaveTextContent('123.450000000001');
        const ownedBadge = selectedOwnedCard.querySelector<HTMLElement>('[data-scope-color="owned"]');
        expect(ownedBadge).not.toBeNull();
        if (!ownedBadge) throw new Error('owned Asset card has no stable scope-color badge');
        expectScopeColor(ownedBadge, 'owned');

        // Scope chips form a union, not a radio group. Within that union the
        // backend order is stable inside each active/inactive partition.
        await fireEvent.click(scopeChip('other_users'));
        await fireEvent.click(scopeChip('observed'));
        expect(scopeChip('owned')).toHaveAttribute('aria-pressed', 'true');
        expect(scopeChip('other_users')).toHaveAttribute('aria-pressed', 'true');
        expect(scopeChip('observed')).toHaveAttribute('aria-pressed', 'true');
        await waitFor(() => expect(visibleAssetCardTestIds()).toEqual(['pac-owned-asset-42', 'pac-owned-asset-44', 'pac-owned-asset-45', 'pac-owned-asset-41', 'pac-owned-asset-43', 'pac-owned-asset-46']));

        for (const assetId of [42, 44, 45]) {
            expect(screen.getByTestId(`pac-owned-asset-${assetId}`)).toHaveAttribute('data-lifecycle', 'active');
        }
        // `data-lifecycle` is the stable semantic contract that drives the
        // inactive card's amber surface; the assertion does not couple the
        // behaviour to Tailwind class names.
        for (const assetId of [41, 43, 46]) {
            expect(screen.getByTestId(`pac-owned-asset-${assetId}`)).toHaveAttribute('data-lifecycle', 'inactive');
        }

        const otherCard = screen.getByTestId('pac-owned-asset-42');
        expect(otherCard).toHaveAttribute('data-usage-scope', 'other_users');
        const otherBadge = otherCard.querySelector<HTMLElement>('[data-scope-color="other_users"]');
        expect(otherBadge).not.toBeNull();
        if (!otherBadge) throw new Error('other-users Asset card has no stable scope-color badge');
        expectScopeColor(otherBadge, 'other_users');
        for (const privateFact of ['Foreign broker secret 42', 'foreign-secret-plugin-42', '37.5', '987654.321001', privateCashAmount]) {
            expect(otherCard).not.toHaveTextContent(privateFact);
        }
        const observedCard = screen.getByTestId('pac-owned-asset-43');
        expect(observedCard).toHaveAttribute('data-usage-scope', 'observed');
        const observedBadge = observedCard.querySelector<HTMLElement>('[data-scope-color="observed"]');
        expect(observedBadge).not.toBeNull();
        if (!observedBadge) throw new Error('observed Asset card has no stable scope-color badge');
        expectScopeColor(observedBadge, 'observed');
        for (const privateFact of ['Observed broker secret 43', 'foreign-secret-plugin-43', '62.5', '123456.789001', privateCashAmount]) {
            expect(observedCard).not.toHaveTextContent(privateFact);
        }

        // Removing the selected card's scope only hides the card. Its imported
        // row remains, and the card reports selected again when the scope returns.
        await fireEvent.click(scopeChip('owned'));
        await waitFor(() => expect(screen.queryByTestId('pac-owned-asset-44')).toBeNull());
        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('44.000000000001');
        await fireEvent.click(scopeChip('owned'));
        await waitFor(() => expect(screen.getByTestId('pac-owned-asset-44')).toHaveAttribute('aria-pressed', 'true'));

        // The query is trimmed and case-insensitive, matches Asset name, and
        // does not match the selected card merely because its ticker is NEEDLE.
        await fireEvent.input(field('pac-owned-assets-search'), {target: {value: '  nEeDlE  '}});
        await waitFor(() => expect(visibleAssetCardTestIds()).toEqual(['pac-owned-asset-42']));
        expect(screen.queryByTestId('pac-owned-asset-44')).toBeNull();
        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(scopeCount('owned')).toBe(2);
        expect(scopeCount('other_users')).toBe(2);
        expect(scopeCount('observed')).toBe(2);

        await fireEvent.input(field('pac-owned-assets-search'), {target: {value: ''}});
        await waitFor(() => expect(screen.getByTestId('pac-owned-asset-44')).toHaveAttribute('aria-pressed', 'true'));
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('44.000000000001');
    });

    it('imports custody contexts and a zero candidate as locked source facts with hidden canonical identities', async () => {
        const requestedDate = localIsoOffset(0);
        const canonicalBase = ownedAsset();
        const canonical = ownedAsset({
            iconUrl: '/test-asset-icons/asset-17.svg',
            contexts: canonicalBase.contexts.map((context) => ({
                ...context,
                brokerIconUrl: `/test-broker-icons/broker-${context.brokerId}.svg`,
            })),
        });
        const missingPrice = ownedAsset({
            assetId: 18,
            instrumentKey: 'asset:18',
            candidateKey: 'candidate:asset:18',
            name: 'Fixture no-price asset',
            ticker: null,
            quote: {
                rawPrice: null,
                currency: 'EUR',
                quoteBaseQuantity: 1,
                referenceDate: null,
                source: null,
                daysBeforeRequested: null,
            },
            contexts: [
                {
                    contextKey: 'asset:18:broker:9',
                    brokerId: 9,
                    brokerName: 'Fixture broker C',
                    brokerIconUrl: null,
                    brokerPortalUrl: null,
                    brokerDefaultImportPlugin: null,
                    ownershipSharePercent: '100',
                    custodyQuantity: '3',
                },
            ],
        });
        const zeroPosition = catalogCandidate({iconUrl: '/test-asset-icons/asset-19.svg'});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [canonical, missingPrice, zeroPosition]));
        renderTool();

        const groupedCard = await screen.findByTestId('pac-owned-asset-17');
        expect(groupedCard).toHaveAttribute('data-usage-scope', 'owned');
        expect(groupedCard).toBeEnabled();
        expect(screen.queryAllByTestId('pac-owned-asset-17')).toHaveLength(1);
        await fireEvent.click(groupedCard);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        expect(groupedCard).toHaveAttribute('aria-pressed', 'true');

        await fireEvent.click(screen.getByTestId('pac-owned-asset-18'));
        const zeroPositionCard = screen.getByTestId('pac-owned-asset-19');
        await fireEvent.click(zeroPositionCard);

        expect(screen.getAllByTestId('pac-row')).toHaveLength(4);
        expect(zeroPositionCard).toHaveAttribute('aria-pressed', 'true');

        const expectedOrigins = ['portfolio_context', 'portfolio_context', 'portfolio_context', 'catalog_candidate'];
        const expectedRowKeys = [...canonical.contexts.map((context) => context.contextKey), missingPrice.contexts[0]!.contextKey, zeroPosition.candidateKey];
        const expectedInstrumentKeys = [canonical.instrumentKey, canonical.instrumentKey, missingPrice.instrumentKey, zeroPosition.instrumentKey];
        const lockedControlPrefixes = ['pac-display-name', 'pac-initial-quantity', 'pac-raw-price', 'pac-asset-currency', 'pac-price-basis', 'pac-price-date'];
        for (let index = 0; index < expectedOrigins.length; index += 1) {
            const row = rowByIndex(index);
            expect(row).toHaveAttribute('data-origin', expectedOrigins[index]);
            expect(row).toHaveAttribute('data-source-mode', 'locked');
            expect(within(row).getByTestId(`pac-initial-state-${index}`)).toBeInTheDocument();
            expect(within(row).getByTestId(`pac-target-state-${index}`)).toBeInTheDocument();
            for (const prefix of lockedControlPrefixes) expect(within(row).queryByTestId(`${prefix}-${index}`)).toBeNull();
            expect(within(row).queryByTestId(`pac-instrument-id-${index}`)).toBeNull();
            expect(within(row).queryByTestId(`pac-custody-context-${index}`)).toBeNull();
            expect(row).not.toHaveTextContent(expectedInstrumentKeys[index]!);
            expect(row).not.toHaveTextContent(expectedRowKeys[index]!);
            expect(within(row).getByTestId(`pac-target-weight-${index}`)).toBeEnabled();
            expect(within(row).getByTestId(`pac-grid-whole-${index}`)).toHaveAttribute('aria-pressed', 'true');
            expect(within(row).getByTestId(`pac-grid-fractional-${index}`)).toHaveAttribute('aria-pressed', 'false');
            expect(within(row).getByTestId(`pac-step-quantity-${index}`)).toBeEnabled();
            expect(within(row).getByTestId(`pac-step-quantity-${index}`)).toHaveValue('1');
        }

        const firstContext = canonical.contexts[0]!;
        const firstRow = rowByIndex(0);
        expect(firstRow).toHaveTextContent(canonical.name);
        expect(firstRow).toHaveTextContent(firstContext.brokerName!);
        expect(within(firstRow).getByRole('img', {name: canonical.name})).toHaveAttribute('src', canonical.iconUrl!);
        expect(within(firstRow).getByRole('img', {name: firstContext.brokerName!})).toHaveAttribute('src', firstContext.brokerIconUrl!);

        const providerSource = within(firstRow).getByTestId('pac-provider-source-0');
        expect(providerSource).toHaveTextContent(canonical.quote.source!);
        expect(within(providerSource).getByRole('presentation')).toHaveAttribute('src', `/test-provider-icons/${canonical.quote.source}.svg`);

        // Custody and personal economic share are deliberately separate facts:
        // the imported quantity stays whole, while the percentage is only
        // informational and has its own accessible explanation.
        const custodyQuantity = within(firstRow).getByTestId('pac-imported-initial-quantity-0');
        expect(custodyQuantity).toHaveTextContent(firstContext.custodyQuantity);
        const custodyCell = custodyQuantity.parentElement;
        if (!custodyCell) throw new Error('custody-quantity fact has no container');
        expect(within(custodyCell).queryAllByRole('button')).toHaveLength(0);
        const ownershipShare = within(firstRow).getByTestId('pac-imported-ownership-share-0');
        expect(ownershipShare).toHaveTextContent(`${firstContext.ownershipSharePercent}%`);
        const ownershipCell = ownershipShare.parentElement;
        if (!ownershipCell) throw new Error('ownership-share fact has no container');
        expect(
            within(ownershipCell)
                .getAllByRole('button')
                .some((button) => Boolean(button.getAttribute('aria-label'))),
        ).toBe(true);
        expect(within(firstRow).getByTestId('pac-imported-price-0')).toHaveTextContent('123.450000000001');
        expect(within(firstRow).getByTestId('pac-imported-price-0')).toHaveTextContent('USD');
        expect(within(firstRow).getByTestId('pac-imported-price-basis-0')).toHaveTextContent('100');
        expect(firstRow).toHaveTextContent('2026-09-09');

        expect(screen.getByTestId('pac-imported-price-2')).toHaveTextContent('—');
        const candidateRow = rowByIndex(3);
        expect(candidateRow).toHaveTextContent(zeroPosition.name);
        expect(within(candidateRow).getByRole('img', {name: zeroPosition.name})).toHaveAttribute('src', zeroPosition.iconUrl!);
        expect(within(candidateRow).getByTestId('pac-provider-source-3')).toHaveTextContent(zeroPosition.quote.source!);
        expect(candidateRow).not.toHaveTextContent('Fixture broker A');
        expect(candidateRow).not.toHaveTextContent('Fixture broker B');
        expect(within(candidateRow).queryByTestId('pac-imported-ownership-share-3')).toBeNull();
        expect(within(candidateRow).getByTestId('pac-imported-initial-quantity-3')).toHaveTextContent('0');
        expect(within(candidateRow).getByTestId('pac-imported-price-3')).toHaveTextContent('88.765432100001');
        expect(within(candidateRow).getByTestId('pac-imported-price-3')).toHaveTextContent('CHF');
        expect(within(candidateRow).getByTestId('pac-imported-price-basis-3')).toHaveTextContent('100');
        expect(candidateRow).toHaveTextContent('2026-09-08');

        const parameters = await analyzeAndReadInput();
        expect(parameters.as_of_date).toBe(requestedDate);
        expect(parameters.rows).toHaveLength(4);
        expect(parameters.rows?.map((row) => row.initial_quantity)).toEqual(['12.345678901234', '7.000000000001', '3', '0']);
        expect(parameters.rows?.[0]?.quote).toEqual({
            raw_price: '123.450000000001',
            currency: 'USD',
            quote_base_quantity: 100,
            reference_date: '2026-09-09',
        });
        expect(parameters.rows?.[2]?.quote?.raw_price).toBeNull();
        expect(parameters.rows?.[0]?.target_percent).toBe('');
        expect(parameters.rows?.[0]?.buy_grid).toEqual({mode: 'whole', quantity_step: '1'});

        const canonicalRows = (parameters.rows ?? []).filter((row) => row.instrument_key === canonical.instrumentKey);
        expect(canonicalRows).toHaveLength(canonical.contexts.length);
        expect(canonicalRows.map((row) => row.row_key)).toEqual(canonical.contexts.map((context) => context.contextKey));

        const catalogRows = (parameters.rows ?? []).filter((row) => row.instrument_key === zeroPosition.instrumentKey);
        expect(catalogRows).toHaveLength(1);
        const [catalogRow] = catalogRows;
        if (!catalogRow) throw new Error('zero-context catalog candidate was not serialized');
        expect(catalogRow).toEqual({
            row_key: zeroPosition.candidateKey,
            instrument_key: zeroPosition.instrumentKey,
            name: zeroPosition.name,
            initial_quantity: '0',
            quote: {
                raw_price: '88.765432100001',
                currency: 'CHF',
                quote_base_quantity: 100,
                reference_date: '2026-09-08',
            },
            target_percent: '',
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
        expect(catalogRow).not.toHaveProperty('broker_id');
        expect(catalogRow).not.toHaveProperty('broker_name');
        expect(catalogRow).not.toHaveProperty('ownership_share_percent');

        for (const row of parameters.rows ?? []) {
            expect(Object.keys(row).sort()).toEqual(['buy_grid', 'initial_quantity', 'instrument_key', 'name', 'quote', 'row_key', 'target_percent']);
            expect(row).not.toHaveProperty('origin');
            expect(row).not.toHaveProperty('source');
            expect(row).not.toHaveProperty('importedValue');
            expect(row).not.toHaveProperty('stale');
        }
    });

    it('shows context-count capacity separately and enforces the 32-row cap atomically', async () => {
        const zeroPosition = catalogCandidate();
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset(), zeroPosition]));
        renderTool();
        const multiContextCard = await screen.findByTestId('pac-owned-asset-17');
        const zeroContextCard = screen.getByTestId('pac-owned-asset-19');
        const selectedCount = screen.getByTestId('pac-selected-context-count');
        const limitInfo = screen.getByTestId('pac-row-limit-info');

        expect(selectedCount).toHaveTextContent('0');
        expect(selectedCount).toHaveTextContent(/\p{L}/u);
        expect(selectedCount).not.toHaveTextContent('/');
        expect(limitInfo).toHaveAccessibleName();
        await fireEvent.click(limitInfo);
        expect(await screen.findByRole('tooltip')).toHaveTextContent('32');
        await fireEvent.click(limitInfo);
        await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());

        expect(screen.queryByTestId('pac-row-limit-warning')).toBeNull();
        for (let index = 0; index < 28; index += 1) {
            await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        }
        expect(screen.getAllByTestId('pac-row')).toHaveLength(28);
        expect(selectedCount).toHaveTextContent('28');
        expect(selectedCount).not.toHaveTextContent('/');
        expect(screen.getByTestId('pac-row-limit-warning')).toBeInTheDocument();

        for (let index = 28; index < 31; index += 1) {
            await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        }
        expect(screen.getAllByTestId('pac-row')).toHaveLength(31);
        expect(selectedCount).toHaveTextContent('31');
        expect(selectedCount).not.toHaveTextContent('/');

        await fireEvent.click(multiContextCard);

        expect(screen.getAllByTestId('pac-row')).toHaveLength(31);
        expect(multiContextCard).toHaveAttribute('aria-pressed', 'false');

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        expect(screen.getAllByTestId('pac-row')).toHaveLength(32);
        await fireEvent.click(zeroContextCard);

        expect(screen.getAllByTestId('pac-row')).toHaveLength(32);
        expect(zeroContextCard).toHaveAttribute('aria-pressed', 'false');
    });

    it('duplicates a locked row as a source-free editable manual copy with hidden identity and accessible actions', async () => {
        const oneContext = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [oneContext]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await fireEvent.click(screen.getByTestId('pac-grid-fractional-0'));
        await fireEvent.input(field('pac-step-quantity-0'), {target: {value: '2.500000000001'}});

        const duplicate = screen.getByTestId('pac-duplicate-asset-0');
        const remove = screen.getByTestId('pac-remove-asset-0');
        expect(duplicate).toHaveAccessibleName();
        expect(duplicate.getAttribute('aria-label')).toBeTruthy();
        expect(remove).toHaveAccessibleName();
        expect(remove.getAttribute('aria-label')).toBeTruthy();
        await fireEvent.click(duplicate);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        const originalRow = rowByIndex(0);
        const copiedRow = rowByIndex(1);
        expect(originalRow).toHaveAttribute('data-origin', 'portfolio_context');
        expect(originalRow).toHaveAttribute('data-source-mode', 'locked');
        expect(copiedRow).toHaveAttribute('data-origin', 'manual_duplicate');
        expect(copiedRow).toHaveAttribute('data-source-mode', 'manual');
        expect(within(copiedRow).getByTestId('pac-initial-state-1')).toBeInTheDocument();
        expect(within(copiedRow).getByTestId('pac-target-state-1')).toBeInTheDocument();
        expect(within(copiedRow).queryByTestId('pac-imported-initial-quantity-1')).toBeNull();
        expect(within(copiedRow).queryByTestId('pac-provider-source-1')).toBeNull();
        expect(within(copiedRow).queryByTestId('pac-instrument-id-1')).toBeNull();
        expect(within(copiedRow).queryByTestId('pac-custody-context-1')).toBeNull();

        expect(field('pac-display-name-1')).toBeEnabled();
        expect(field('pac-display-name-1')).toHaveValue(oneContext.name);
        expect(field('pac-initial-quantity-1')).toBeEnabled();
        expect(field('pac-initial-quantity-1')).toHaveValue(oneContext.contexts[0]!.custodyQuantity);
        expect(field('pac-raw-price-1')).toBeEnabled();
        expect(field('pac-raw-price-1')).toHaveValue(oneContext.quote.rawPrice);
        expect(screen.getByTestId('pac-asset-currency-1-trigger')).toBeEnabled();
        expect(screen.getByTestId('pac-asset-currency-1-trigger')).toHaveTextContent(oneContext.quote.currency);
        expect(field('pac-price-basis-1')).toBeEnabled();
        expect(field('pac-price-basis-1')).toHaveValue(oneContext.quote.quoteBaseQuantity);
        expect(field('pac-price-date-1')).toBeEnabled();
        expect(field('pac-price-date-1')).toHaveValue(oneContext.quote.referenceDate);
        expect(field('pac-target-weight-1')).toBeEnabled();
        expect(field('pac-target-weight-1')).toHaveValue('42.5');
        expect(screen.getByTestId('pac-grid-fractional-1')).toHaveAttribute('aria-pressed', 'true');
        expect(field('pac-step-quantity-1')).toHaveValue('2.500000000001');

        for (const action of [screen.getByTestId('pac-duplicate-asset-1'), screen.getByTestId('pac-remove-asset-1')]) {
            expect(action).toHaveAccessibleName();
            expect(action.getAttribute('aria-label')).toBeTruthy();
        }

        const parameters = await analyzeAndReadInput();
        const rows = parameters.rows ?? [];
        expect(rows).toHaveLength(2);
        const [original, copy] = rows;
        if (!original || !copy) throw new Error('expected original and duplicate rows');
        const {row_key: originalKey, ...originalPayload} = original;
        const {row_key: copyKey, ...copyPayload} = copy;
        expect(copyKey).not.toBe(originalKey);
        expect(copy.instrument_key).toBe(original.instrument_key);
        expect(copyPayload).toEqual(originalPayload);
        expect(originalRow).not.toHaveTextContent(original.instrument_key);
        expect(originalRow).not.toHaveTextContent(original.row_key);
        expect(copiedRow).not.toHaveTextContent(copy.instrument_key);
        expect(copiedRow).not.toHaveTextContent(copy.row_key);
    });

    it('keeps a manual duplicate independent of source refresh and asset deselection', async () => {
        const initial = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        const refreshed = ownedAsset({
            name: 'Refreshed source asset',
            quote: {...ownedAsset().quote, rawPrice: '456.780000000001'},
            contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '99.000000000001'}],
        });
        let sourceCalls = 0;
        fetchSourceMock.mockImplementation(async (asOfDate: string) => {
            sourceCalls += 1;
            return allocationSource(asOfDate, [sourceCalls === 1 ? initial : refreshed]);
        });
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');
        await fireEvent.click(card);
        await fireEvent.click(screen.getByTestId('pac-duplicate-asset-0'));
        await fireEvent.input(field('pac-display-name-1'), {target: {value: 'Independent duplicate fixture'}});

        await fireEvent.click(screen.getByTestId('pac-owned-assets-refresh'));
        await waitFor(() => expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument());
        expect(rowByIndex(1)).toHaveAttribute('data-origin', 'manual_duplicate');
        expect(rowByIndex(1)).toHaveAttribute('data-source-mode', 'manual');
        expect(field('pac-display-name-1')).toHaveValue('Independent duplicate fixture');
        expect(field('pac-initial-quantity-1')).toHaveValue(initial.contexts[0]!.custodyQuantity);
        expect(field('pac-raw-price-1')).toHaveValue(initial.quote.rawPrice);

        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));
        await waitFor(() => expect(screen.queryByTestId('pac-stale-source')).toBeNull());
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('99.000000000001');
        expect(screen.getByTestId('pac-imported-price-0')).toHaveTextContent('456.780000000001');
        expect(field('pac-display-name-1')).toHaveValue('Independent duplicate fixture');
        expect(field('pac-initial-quantity-1')).toHaveValue(initial.contexts[0]!.custodyQuantity);
        expect(field('pac-raw-price-1')).toHaveValue(initial.quote.rawPrice);

        await fireEvent.click(screen.getByTestId('pac-owned-asset-17'));
        expect(screen.queryByTestId('pac-confirm-deselect')).toBeNull();
        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(rowByIndex(0)).toHaveAttribute('data-origin', 'manual_duplicate');
        expect(rowByIndex(0)).toHaveAttribute('data-source-mode', 'manual');
        expect(field('pac-display-name-0')).toHaveValue('Independent duplicate fixture');
        expect(screen.getByTestId('pac-owned-asset-17')).toHaveAttribute('aria-pressed', 'false');

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));
        expect(screen.queryByTestId('pac-confirm-deselect')).toBeNull();
        expect(screen.queryAllByTestId('pac-row')).toHaveLength(0);
    });

    it('confirms one context only when a modified copied row is removed directly', async () => {
        // Removing a row and deselecting the asset are two different intentions
        // that both end in a destructive confirmation, so the confirmation has
        // to say which one is about to happen. Here only the row under the
        // button may be described and removed — the sibling context stays, and
        // the asset stays selected because a copy of it is still in the draft.
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');
        await fireEvent.click(card);

        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await fireEvent.input(field('pac-target-weight-1'), {target: {value: '57.5'}});

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));

        const listed = screen.getAllByRole('listitem');
        expect(listed).toHaveLength(1);
        expect(listed[0]).toHaveTextContent('Fixture global ETF');
        expect(listed[0]).toHaveTextContent('Fixture broker A');
        expect(listed[0]).not.toHaveTextContent('Fixture broker B');
        // Nothing is removed until the answer comes back.
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('7.000000000001');
        expect(field('pac-target-weight-0')).toHaveValue('57.5');
        expect(card).toHaveAttribute('aria-pressed', 'true');
    });

    it('cancels a single-row removal without touching the draft', async () => {
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));
        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));

        expect(screen.queryAllByRole('listitem')).toHaveLength(0);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
    });

    it('removes an unmodified copied row with no confirmation at all', async () => {
        // The confirmation exists to protect edits. A pristine copy has none to
        // lose, so asking would be a dialog for nothing.
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));

        expect(screen.queryAllByRole('listitem')).toHaveLength(0);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
    });

    it('describes and removes only linked contexts when the gallery card is deselected, preserving unrelated rows', async () => {
        // The contrast with the row button above: one click on the card is an
        // intention about the whole asset, so every modified context it owns is
        // named, and confirming takes all of them out without touching manual
        // rows or imported rows linked to another asset.
        const unrelated = catalogCandidate({
            assetId: 20,
            instrumentKey: 'asset:20',
            candidateKey: 'candidate:asset:20',
            name: 'Unrelated imported candidate',
            ticker: 'KEEP',
        });
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset(), unrelated]));
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');
        const unrelatedCard = screen.getByTestId('pac-owned-asset-20');

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Unrelated manual row'}});

        await fireEvent.click(card);
        await fireEvent.click(unrelatedCard);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(4);
        await fireEvent.input(field('pac-target-weight-1'), {target: {value: '42.5'}});
        await fireEvent.input(field('pac-target-weight-2'), {target: {value: '57.5'}});

        await fireEvent.click(card);

        // Two modified contexts, so the list starts collapsed: open it and read
        // what the user is about to lose.
        await expandConfirmationItems('pac-confirm-deselect');
        const listed = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
        expect(listed).toHaveLength(2);
        expect(listed.some((text) => text.includes('Fixture global ETF') && text.includes('Fixture broker A'))).toBe(true);
        expect(listed.some((text) => text.includes('Fixture global ETF') && text.includes('Fixture broker B'))).toBe(true);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(4);

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        expect(rowByIndex(0)).toHaveAttribute('data-origin', 'manual');
        expect(rowByIndex(0)).toHaveAttribute('data-source-mode', 'manual');
        expect(field('pac-display-name-0')).toHaveValue('Unrelated manual row');
        expect(rowByIndex(1)).toHaveAttribute('data-origin', 'catalog_candidate');
        expect(rowByIndex(1)).toHaveAttribute('data-source-mode', 'locked');
        expect(rowByIndex(1)).toHaveTextContent(unrelated.name);
        expect(screen.getByTestId('pac-imported-initial-quantity-1')).toHaveTextContent('0');
        expect(screen.queryByTestId('pac-instrument-id-0')).toBeNull();
        expect(screen.queryByTestId('pac-custody-context-0')).toBeNull();
        expect(screen.queryByTestId('pac-instrument-id-1')).toBeNull();
        expect(screen.queryByTestId('pac-custody-context-1')).toBeNull();
        expect(card).toHaveAttribute('aria-pressed', 'false');
        expect(unrelatedCard).toHaveAttribute('aria-pressed', 'true');

        const remaining = (await analyzeAndReadInput()).rows ?? [];
        const manual = remaining.find((row) => row.name === 'Unrelated manual row');
        const imported = remaining.find((row) => row.name === unrelated.name);
        if (!manual || !imported) throw new Error('unrelated rows were not preserved');
        expect(rowByIndex(0)).not.toHaveTextContent(manual.instrument_key);
        expect(rowByIndex(0)).not.toHaveTextContent(manual.row_key);
        expect(imported.instrument_key).toBe(unrelated.instrumentKey);
        expect(imported.row_key).toBe(unrelated.candidateKey);
        expect(rowByIndex(1)).not.toHaveTextContent(imported.instrument_key);
        expect(rowByIndex(1)).not.toHaveTextContent(imported.row_key);
    });

    it('marks imported rows stale, ignores a late source response, and refreshes locked facts without replacing target or grid edits', async () => {
        const today = localIsoOffset(0);
        const supersededDate = localIsoOffset(-1);
        const currentDate = localIsoOffset(-2);
        const superseded = deferred<PacAllocationSource>();
        const current = deferred<PacAllocationSource>();
        fetchSourceMock.mockImplementation((asOfDate: string) => {
            if (asOfDate === today) return Promise.resolve(allocationSource(asOfDate, [ownedAsset({contexts: [ownedAsset().contexts[0]!]})]));
            if (asOfDate === supersededDate) return superseded.promise;
            if (asOfDate === currentDate) return current.promise;
            throw new Error(`unexpected source date ${asOfDate}`);
        });
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await fireEvent.click(screen.getByTestId('pac-grid-fractional-0'));
        await fireEvent.input(field('pac-step-quantity-0'), {target: {value: '2.5'}});

        const date = field('pac-as-of-date');
        await fireEvent.input(date, {target: {value: supersededDate}});
        await fireEvent.blur(date);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        await fireEvent.focus(date);
        await fireEvent.input(date, {target: {value: currentDate}});
        await fireEvent.blur(date);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument();

        current.resolve(
            allocationSource(currentDate, [
                ownedAsset({
                    name: 'Fresh server name',
                    quote: {...ownedAsset().quote, rawPrice: '200.000000000001', referenceDate: currentDate},
                    contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '99.000000000001'}],
                }),
            ]),
        );
        await waitFor(() => expect(screen.getByTestId('pac-owned-assets-refresh')).toBeEnabled());

        // The superseded date answers after the current one. It must not
        // replace the current gallery source or make its refresh action stale.
        superseded.resolve(
            allocationSource(supersededDate, [
                ownedAsset({
                    name: 'Late response name',
                    contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '88'}],
                }),
            ]),
        );
        await superseded.promise;
        await Promise.resolve();
        expect(screen.getByTestId('pac-owned-asset-17')).toHaveTextContent('Fresh server name');
        expect(screen.getByTestId('pac-owned-asset-17')).not.toHaveTextContent('Late response name');
        expect(screen.getByTestId('pac-owned-assets-refresh')).toBeEnabled();

        // Merely receiving either source never overwrites the locked snapshot.
        expect(rowByIndex(0)).toHaveTextContent('Fixture global ETF');
        expect(rowByIndex(0)).not.toHaveTextContent('Fresh server name');
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('12.345678901234');
        expect(screen.getByTestId('pac-imported-price-0')).toHaveTextContent('123.450000000001');
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));

        expect(screen.queryByTestId('pac-confirm-refresh')).toBeNull();
        await waitFor(() => expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('99.000000000001'));
        expect(rowByIndex(0)).toHaveTextContent('Fresh server name');
        expect(screen.getByTestId('pac-imported-price-0')).toHaveTextContent('200.000000000001');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(field('pac-step-quantity-0')).toHaveValue('2.5');
        expect(screen.getByTestId('pac-grid-fractional-0')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.queryByTestId('pac-stale-source')).toBeNull();

        const parameters = await analyzeAndReadInput();
        expect(parameters.as_of_date).toBe(currentDate);
        expect(parameters.rows?.[0]).toMatchObject({
            name: 'Fresh server name',
            initial_quantity: '99.000000000001',
            target_percent: '42.5',
            buy_grid: {mode: 'fractional', quantity_step: '2.5'},
            quote: {raw_price: '200.000000000001', reference_date: currentDate},
        });
    });

    it('marks copied rows stale when the same date answers differently, and never overwrites the draft on its own', async () => {
        // The date-change path is covered above. This is the other half: the
        // request date does not move at all, so nothing in the draft says the
        // copy might be out of date — the *response* is the only evidence. The
        // two shapes that evidence takes, a context that changed and a context
        // that disappeared, are exercised one at a time and with the banner
        // cleared in between, so each is genuinely the cause of the red it
        // would produce. Neither may edit the user's draft by itself.
        const today = localIsoOffset(0);
        const changed = deferred<PacAllocationSource>();
        const removed = deferred<PacAllocationSource>();
        let sourceCalls = 0;
        fetchSourceMock.mockImplementation((asOfDate: string) => {
            if (asOfDate !== today) throw new Error(`unexpected source date ${asOfDate}`);
            sourceCalls += 1;
            if (sourceCalls === 1) return Promise.resolve(allocationSource(today, [ownedAsset()]));
            if (sourceCalls === 2) return changed.promise;
            return removed.promise;
        });
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await fireEvent.input(field('pac-target-weight-1'), {target: {value: '57.5'}});
        expect(screen.queryByTestId('pac-stale-source')).toBeNull();

        // ── 1. Same date, one context answers with a different custody quantity.
        await fireEvent.click(screen.getByTestId('pac-owned-assets-refresh'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        changed.resolve(
            allocationSource(today, [
                ownedAsset({
                    name: 'Fresh server name',
                    contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '55.000000000001'}, ownedAsset().contexts[1]!],
                }),
            ]),
        );

        await waitFor(() => expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument());
        // Arrival alone changed nothing in the locked snapshot.
        expect(rowByIndex(0)).toHaveTextContent('Fixture global ETF');
        expect(rowByIndex(0)).not.toHaveTextContent('Fresh server name');
        expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('12.345678901234');
        expect(screen.getByTestId('pac-imported-initial-quantity-1')).toHaveTextContent('7.000000000001');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');

        // Reconciling takes the server's facts and leaves the draft-only fields
        // alone; with both contexts accounted for, the warning goes away again.
        await waitFor(() => expect(screen.getByTestId('pac-refresh-copied-facts')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));
        await waitFor(() => expect(screen.getByTestId('pac-imported-initial-quantity-0')).toHaveTextContent('55.000000000001'));
        expect(rowByIndex(0)).toHaveTextContent('Fresh server name');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(screen.getByTestId('pac-imported-initial-quantity-1')).toHaveTextContent('7.000000000001');
        expect(screen.queryByTestId('pac-stale-source')).toBeNull();

        // ── 2. Same date again, and this time broker B's context is simply gone.
        await fireEvent.click(screen.getByTestId('pac-owned-assets-refresh'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        removed.resolve(
            allocationSource(today, [
                ownedAsset({
                    name: 'Fresh server name',
                    contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '55.000000000001'}],
                }),
            ]),
        );

        await waitFor(() => expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument());
        expect(screen.getByTestId('pac-imported-initial-quantity-1')).toHaveTextContent('7.000000000001');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');

        // A row whose context vanished has nothing to reconcile against, so it
        // keeps the copy it has and keeps saying it is out of date.
        await waitFor(() => expect(screen.getByTestId('pac-refresh-copied-facts')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));
        expect(screen.getByTestId('pac-imported-initial-quantity-1')).toHaveTextContent('7.000000000001');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');
        expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument();

        const parameters = await analyzeAndReadInput();
        expect(parameters.rows?.map((row) => row.initial_quantity)).toEqual(['55.000000000001', '7.000000000001']);
        expect(parameters.rows?.map((row) => row.target_percent)).toEqual(['42.5', '57.5']);
    });

    it('starts in broker cash copy, submits only backend aggregates, and preserves guarded state across manual fallback', async () => {
        const today = localIsoOffset(0);
        const lateBrokerSelection = deferred<PacAllocationSource>();
        const matchingBrokerSelection = deferred<PacAllocationSource>();
        let brokerThreeRequests = 0;
        fetchSourceMock.mockImplementation((asOfDate, _requestedGeneration, options = {}) => {
            if (asOfDate !== today) throw new Error(`unexpected source date ${asOfDate}`);
            const selectedBrokerIds = [...(options.selectedCashBrokerIds ?? [])];
            if (selectedBrokerIds.length === 0) {
                return Promise.resolve(allocationSource(asOfDate, [], {cashSources: OWNER_CASH_SOURCES}));
            }
            if (selectedBrokerIds.join(',') === '3') {
                brokerThreeRequests += 1;
                return brokerThreeRequests === 1 ? lateBrokerSelection.promise : matchingBrokerSelection.promise;
            }
            if (selectedBrokerIds.join(',') === '3,4') {
                return Promise.resolve(
                    allocationSource(asOfDate, [], {
                        cashSources: OWNER_CASH_SOURCES,
                        selectedCashBalances: BACKEND_SELECTED_CASH_BALANCES,
                    }),
                );
            }
            throw new Error(`unexpected selected cash brokers ${selectedBrokerIds.join(',')}`);
        });
        renderTool();
        await screen.findByTestId('pac-owned-assets-empty');

        const brokerA = await screen.findByTestId('pac-cash-broker-3');
        const brokerB = await screen.findByTestId('pac-cash-broker-4');
        await waitFor(() => expect(brokerA).toBeEnabled());
        expect(screen.getByTestId('pac-cash-broker-copy')).toBeInTheDocument();
        expect(screen.getByTestId('pac-cash-use-manual')).toBeInTheDocument();
        expect(screen.queryByTestId('pac-cash-use-brokers')).toBeNull();
        expect(brokerA).toHaveAttribute('aria-pressed', 'false');
        expect(brokerB).toHaveAttribute('aria-pressed', 'false');
        expect(brokerA).toHaveTextContent('Fixture owner broker A');
        expect(brokerA).toHaveTextContent('25%');
        expect(brokerA).toHaveTextContent('🇪🇺');
        expect(brokerA).toHaveTextContent('EUR');
        expect(brokerA).toHaveTextContent('100.1');
        expect(brokerA).toHaveTextContent('🇺🇸');
        expect(brokerA).toHaveTextContent('USD');
        expect(brokerA).toHaveTextContent('5.5');
        expect(brokerB).toHaveTextContent('Fixture owner broker B');
        expect(brokerB).toHaveTextContent('75%');
        expect(brokerB).toHaveTextContent('🇪🇺');
        expect(brokerB).toHaveTextContent('300.2');
        expect(brokerB).toHaveTextContent('🇨🇭');
        expect(brokerB).toHaveTextContent('7.25');

        const initial = await analyzeAndReadInput();
        expect(initial.cash_balances).toEqual([]);
        expect(initial.contributions).toEqual([]);

        const firstSelectionCallIndex = fetchSourceMock.mock.calls.length;
        await fireEvent.click(brokerA);
        await waitFor(() => expect(fetchSourceMock.mock.calls.length).toBeGreaterThan(firstSelectionCallIndex));
        const firstSelectionCall = fetchSourceMock.mock.calls[firstSelectionCallIndex];
        if (!firstSelectionCall) throw new Error('broker 3 source request not found');
        expect(firstSelectionCall[0]).toBe(today);
        expect(firstSelectionCall[1]).toBe(accountGeneration);
        expect(firstSelectionCall[2]?.selectedCashBrokerIds).toEqual([3]);
        expect(firstSelectionCall[2]?.signal?.aborted).toBe(false);
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'pending'));
        expect(screen.getByTestId('pac-analyze')).toBeDisabled();

        // Manual fallback keeps the selected broker id and owns a separate
        // draft. It also aborts the broker-copy request; the sequence guard is
        // still required because a transport is allowed to settle late.
        const manualSourceCallIndex = fetchSourceMock.mock.calls.length;
        await useManualCash();
        await waitFor(() => expect(fetchSourceMock.mock.calls.length).toBeGreaterThan(manualSourceCallIndex));
        await waitFor(() => expect(firstSelectionCall[2]?.signal?.aborted).toBe(true));
        await selectCurrency('pac-cash-currency-0', 'EUR');
        await fireEvent.input(field('pac-cash-amount-0'), {target: {value: '500.000000000001'}});

        lateBrokerSelection.resolve(
            allocationSource(today, [], {
                cashSources: OWNER_CASH_SOURCES.map((source) => (source.brokerId === 3 ? {...source, brokerName: 'Late stale broker'} : source)),
                selectedCashBalances: [{currency: 'EUR', amount: '999999.99'}],
            }),
        );
        await lateBrokerSelection.promise;
        await Promise.resolve();
        expect(field('pac-cash-amount-0')).toHaveValue('500.000000000001');

        // Returning to brokers preserves the selection. Only the matching
        // request may clear the pending state or replace its backend aggregate.
        const matchingSelectionCallIndex = fetchSourceMock.mock.calls.length;
        await useBrokerCash();
        await waitFor(() => expect(fetchSourceMock.mock.calls.length).toBeGreaterThan(matchingSelectionCallIndex));
        await waitFor(() => expect(brokerThreeRequests).toBe(2));
        expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'pending');
        expect(screen.getByTestId('pac-cash-broker-3')).toHaveTextContent('Fixture owner broker A');
        expect(screen.getByTestId('pac-cash-broker-3')).not.toHaveTextContent('Late stale broker');
        expect(screen.getByTestId('pac-analyze')).toBeDisabled();

        matchingBrokerSelection.resolve(
            allocationSource(today, [], {
                cashSources: OWNER_CASH_SOURCES,
                selectedCashBalances: [{currency: 'EUR', amount: '111.110000000001'}],
            }),
        );
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'ready'));
        expect(screen.getByTestId('pac-analyze')).toBeEnabled();
        expect(screen.getByTestId('pac-cash-broker-3')).toHaveAttribute('aria-pressed', 'true');

        const bothBrokersCallIndex = fetchSourceMock.mock.calls.length;
        await fireEvent.click(screen.getByTestId('pac-cash-broker-4'));
        await waitFor(() => expect(fetchSourceMock.mock.calls.length).toBeGreaterThan(bothBrokersCallIndex));
        const bothBrokersCall = fetchSourceMock.mock.calls[bothBrokersCallIndex];
        if (!bothBrokersCall) throw new Error('combined OWNER broker source request not found');
        expect(bothBrokersCall[0]).toBe(today);
        expect(bothBrokersCall[1]).toBe(accountGeneration);
        expect(bothBrokersCall[2]?.selectedCashBrokerIds).toEqual([3, 4]);
        await waitFor(() => expect(screen.getByTestId('pac-cash-aggregate-EUR')).toHaveTextContent('777.770000000001'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'ready'));
        expect(screen.getByTestId('pac-cash-aggregate-USD')).toHaveTextContent('8.880000000001');
        expect(screen.getByTestId('pac-cash-broker-3')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-cash-broker-4')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-analyze')).toBeEnabled();

        const brokerCopy = await analyzeAndReadInput();
        expect(brokerCopy.cash_balances).toEqual(BACKEND_SELECTED_CASH_BALANCES);
        expect(brokerCopy.cash_balances).not.toEqual([
            {currency: 'EUR', amount: '400.30'},
            {currency: 'USD', amount: '5.50'},
            {currency: 'CHF', amount: '7.25'},
        ]);
        expect(brokerCopy.contributions).toEqual([]);

        await useManualCash();
        expect(screen.queryByTestId('pac-cash-monetary-step-0')).toBeNull();
        const manual = await analyzeAndReadInput();
        expect(manual.cash_balances).toEqual([{currency: 'EUR', amount: '500.000000000001'}]);
        expect(manual.contributions).toEqual([]);

        await useBrokerCash();
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-cash-source', 'ready'));
        expect(screen.getByTestId('pac-cash-broker-3')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-cash-broker-4')).toHaveAttribute('aria-pressed', 'true');
        await useManualCash();
        expect(field('pac-cash-amount-0')).toHaveValue('500.000000000001');
    });

    it('shows FX only for concrete active mismatches, publishes separate reasons, and retries a missing saved lookup', async () => {
        renderTool();
        await screen.findByTestId('pac-owned-assets-empty');

        expect(screen.queryByTestId('pac-valuation-rates')).toBeNull();

        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Foreign Asset reason'}});
        await selectCurrency('pac-asset-currency-0', 'USD');
        const usdReason = screen.getByTestId('pac-fx-reason-USD');
        expect(usdReason).toBeInTheDocument();
        expect(within(usdReason).getByTestId('pac-fx-reason-assets-USD')).toBeInTheDocument();
        expect(within(usdReason).queryByTestId('pac-fx-reason-cash-USD')).toBeNull();
        expect(within(usdReason).queryByTestId('pac-fx-reason-contribution-USD')).toBeNull();

        await useManualCash();
        await selectCurrency('pac-cash-currency-0', 'CHF');
        await fireEvent.input(field('pac-cash-amount-0'), {target: {value: '500'}});
        const chfReason = screen.getByTestId('pac-fx-reason-CHF');
        expect(within(chfReason).getByTestId('pac-fx-reason-cash-CHF')).toBeInTheDocument();
        expect(within(chfReason).queryByTestId('pac-fx-reason-assets-CHF')).toBeNull();
        expect(within(chfReason).queryByTestId('pac-fx-reason-contribution-CHF')).toBeNull();

        await addContribution();
        await selectCurrency('pac-contributions-currency-0', 'USD');
        await fireEvent.input(field('pac-contributions-amount-0'), {target: {value: '200'}});
        expect(within(usdReason).getByTestId('pac-fx-reason-assets-USD')).toBeInTheDocument();
        expect(within(usdReason).getByTestId('pac-fx-reason-contribution-USD')).toBeInTheDocument();
        expect(within(usdReason).queryByTestId('pac-fx-reason-cash-USD')).toBeNull();

        expect(lookupFxRateMock).not.toHaveBeenCalled();
        const copy = screen.getByTestId('pac-copy-rate-USD');
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledWith('USD', 'EUR', localIsoOffset(0)));
        expect(await screen.findByTestId('pac-copy-rate-error-USD')).toBeInTheDocument();
        expect(copy).toBeEnabled();

        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledTimes(2));
        expect(await screen.findByTestId('pac-copy-rate-error-USD')).toBeInTheDocument();
        expect(copy).toBeEnabled();

        await useBrokerCash();
        await waitFor(() => expect(screen.queryByTestId('pac-fx-reason-CHF')).toBeNull());
        await fireEvent.click(screen.getByTestId('pac-remove-contributions-0'));
        await waitFor(() => expect(screen.getByTestId('pac-contributions-empty')).toBeInTheDocument());
        await waitFor(() => expect(within(usdReason).queryByTestId('pac-fx-reason-contribution-USD')).toBeNull());
        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));
        await waitFor(() => expect(screen.queryByTestId('pac-valuation-rates')).toBeNull());
    });

    it('copies a backward-filled saved FX rate into editable wire fields and rejects stale field, date, report, and account replies', async () => {
        const oneContext = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [oneContext]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        expect(screen.getByTestId('pac-valuation-rates')).toBeInTheDocument();
        expect(screen.getByTestId('pac-fx-reason-assets-USD')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(0);
        expect((await analyzeAndReadInput()).valuation_rates).toEqual([]);
        expect(lookupFxRateMock).not.toHaveBeenCalled();

        const requestedDate = localIsoOffset(0);
        const effectiveDate = localIsoOffset(-2);
        lookupFxRateMock.mockResolvedValueOnce({
            date: requestedDate,
            rate: 0.812345678901,
            backwardFillInfo: {actualRateDate: effectiveDate, daysBack: 2},
        });
        const copy = screen.getByTestId('pac-copy-rate-USD');
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledWith('USD', 'EUR', requestedDate));
        await waitFor(() => expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(1));
        expect(copy).toBeEnabled();
        expect(field('pac-rate-value-0')).toHaveValue('0.812345678901');
        expect(field('pac-rate-date-0')).toHaveValue(effectiveDate);

        const rateDate = field('pac-rate-date-0');
        await fireEvent.input(field('pac-rate-value-0'), {target: {value: '0.900000000001'}});
        await fireEvent.input(rateDate, {target: {value: localIsoOffset(-1)}});
        await fireEvent.blur(rateDate);

        const rateRow = screen.getByTestId('pac-rate-row');
        expect(rateRow).toHaveTextContent('1');
        expect(rateRow).toHaveTextContent('=');
        expect(rateRow).toHaveTextContent('EUR');
        expect(within(rateRow).getByTestId('pac-rate-currency-0-trigger')).toHaveTextContent('USD');
        expect(field('pac-rate-value-0')).toHaveValue('0.900000000001');
        const equationText = rateRow.textContent ?? '';
        const one = equationText.indexOf('1');
        const native = equationText.indexOf('USD', one + 1);
        const equals = equationText.indexOf('=', native + 1);
        const report = equationText.indexOf('EUR', equals + 1);
        expect(one >= 0 && native > one && equals > native && report > equals).toBe(true);
        const rateDateRoot = within(rateRow).getByTestId('pac-rate-date-0-root');
        const rateDateLabels = Array.from(rateRow.getElementsByTagName('label')).filter((label) => label.contains(rateDateRoot));
        expect(rateDateLabels).toHaveLength(1);
        expect(rateDateRoot.getElementsByTagName('label')).toHaveLength(0);

        const parameters = await analyzeAndReadInput();
        const imported = parameters.rows?.find((row) => row.name === oneContext.name);
        if (!imported) throw new Error('foreign imported row was not serialized');
        expect(parameters.report_currency).toBe('EUR');
        expect(imported.quote).toMatchObject({currency: 'USD', raw_price: '123.450000000001'});
        expect(parameters.valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.900000000001', reference_date: localIsoOffset(-1)}]);

        const fieldReply = deferred<FxDataPoint | null>();
        lookupFxRateMock.mockReturnValueOnce(fieldReply.promise);
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledTimes(2));
        expect(lookupFxRateMock).toHaveBeenNthCalledWith(2, 'USD', 'EUR', requestedDate);
        expect(copy).toBeDisabled();
        await fireEvent.input(field('pac-rate-value-0'), {target: {value: '0.777777777777'}});
        expect(copy).toBeEnabled();
        fieldReply.resolve({date: requestedDate, rate: 0.5, backwardFillInfo: null});
        await fieldReply.promise;
        await Promise.resolve();
        expect(field('pac-rate-value-0')).toHaveValue('0.777777777777');

        const dateReply = deferred<FxDataPoint | null>();
        lookupFxRateMock.mockReturnValueOnce(dateReply.promise);
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledTimes(3));
        expect(lookupFxRateMock).toHaveBeenNthCalledWith(3, 'USD', 'EUR', requestedDate);
        expect(copy).toBeDisabled();
        const revisedDate = localIsoOffset(-3);
        const asOfDate = field('pac-as-of-date');
        await fireEvent.input(asOfDate, {target: {value: revisedDate}});
        await fireEvent.blur(asOfDate);
        dateReply.resolve({date: requestedDate, rate: 0.6, backwardFillInfo: null});
        await dateReply.promise;
        await Promise.resolve();
        expect(field('pac-rate-value-0')).toHaveValue('0.777777777777');
        expect(field('pac-rate-date-0')).toHaveValue(localIsoOffset(-1));
        expect(copy).toBeEnabled();

        const reportReply = deferred<FxDataPoint | null>();
        lookupFxRateMock.mockReturnValueOnce(reportReply.promise);
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledTimes(4));
        expect(lookupFxRateMock).toHaveBeenNthCalledWith(4, 'USD', 'EUR', revisedDate);
        expect(copy).toBeDisabled();
        await selectCurrency('pac-report-currency', 'CHF');
        reportReply.resolve({date: revisedDate, rate: 0.7, backwardFillInfo: null});
        await reportReply.promise;
        await Promise.resolve();
        expect(field('pac-rate-value-0')).toHaveValue('0.777777777777');
        expect(copy).toBeEnabled();

        const accountReply = deferred<FxDataPoint | null>();
        lookupFxRateMock.mockReturnValueOnce(accountReply.promise);
        await fireEvent.click(copy);
        await waitFor(() => expect(lookupFxRateMock).toHaveBeenCalledTimes(5));
        expect(lookupFxRateMock).toHaveBeenNthCalledWith(5, 'USD', 'CHF', revisedDate);
        expect(copy).toBeDisabled();
        transitionClientSession(`pac-fx-other-account-${++accountSequence}`);
        accountReply.resolve({date: revisedDate, rate: 0.8, backwardFillInfo: null});
        await accountReply.promise;
        await waitFor(() => expect(copy).toBeEnabled());
        expect(field('pac-rate-value-0')).toHaveValue('0.777777777777');
        expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false');
    });

    it('starts a ready result formatted, exposes backend exact facts on toggle, and keeps guidance beside independent metrics', async () => {
        renderTool();
        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Ready result fixture'}});
        queueSuccess(readyOutput());
        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const result = await screen.findByTestId('pac-result');
        expect(result).toHaveAttribute('data-state', 'ready');
        expect(result).toHaveAttribute('data-view', 'formatted');
        expect(screen.getByTestId('pac-view-formatted')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-view-exact')).toHaveAttribute('aria-pressed', 'false');

        for (const [testid, amount] of [
            ['pac-total-invested', '1150'],
            ['pac-total-existing-cash', '500'],
            ['pac-total-contributions', '200'],
            ['pac-total-combined-cash', '700'],
        ] as const) {
            const money = screen.getByTestId(testid);
            expect(money).toHaveTextContent('🇪🇺');
            expect(money).toHaveTextContent('EUR');
            expect(money).toHaveTextContent(amount);
        }
        expect(screen.getByTestId('pac-max-gap')).toHaveTextContent('0');
        expect(screen.getByTestId('pac-max-gap')).not.toHaveTextContent('/');

        const resultRows = within(screen.getByTestId('pac-result-rows')).getAllByTestId('pac-result-row');
        expect(resultRows).toHaveLength(1);
        const [resultRow] = resultRows;
        expect(resultRow).toHaveTextContent('ETF Global');
        expect(resultRow).toHaveTextContent('100');
        expect(resultRow).not.toHaveTextContent('1150 / 1150');

        await fireEvent.click(screen.getByTestId('pac-view-exact'));
        expect(result).toHaveAttribute('data-view', 'exact');
        expect(screen.getByTestId('pac-view-exact')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-max-gap')).toHaveTextContent('0 / 1150');
        expect(resultRow).toHaveTextContent('1150 / 1150');

        await fireEvent.click(screen.getByTestId('pac-view-formatted'));
        expect(result).toHaveAttribute('data-view', 'formatted');
        expect(screen.getByTestId('pac-max-gap')).not.toHaveTextContent('/');

        expect(screen.getByTestId('pac-normalized-details')).toBeInTheDocument();
        expectResultGuidance();

        // Execution metrics are a platform fact, reported independently of the
        // backend's domain result — not nested inside it either way.
        const metrics = await screen.findByTestId('tool-execution-metrics');
        expect(result.contains(metrics)).toBe(false);
        expect(metrics.contains(result)).toBe(false);
        expect(within(metrics).getByTestId('tool-metrics-total_ms')).toHaveTextContent('17');
        expect(within(metrics).getByTestId('tool-metrics-server_processing_ms')).toHaveTextContent('17');
    });

    it('marks an in-flight request stale on edit, and ignores its response once it resolves', async () => {
        const {promise, resolve} = deferred<PacSuccess>();
        runToolMock.mockImplementationOnce(() => promise);
        renderTool();
        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Before in-flight edit'}});

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));

        // Edit the draft while the request above is still in flight.
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Changed mid-flight'}});

        await waitFor(() => expect(screen.getByTestId('pac-request-stale')).toBeInTheDocument());

        resolve(successResult('c-stale', readyOutput(), accountGeneration));

        await waitFor(() => expect(screen.getByTestId('pac-response-ignored')).toBeInTheDocument());
        expect(screen.queryByTestId('pac-result')).toBeNull();
        expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false');
    });

    it('ignores source and compute responses after the account generation changes', async () => {
        const oldSource = deferred<PacAllocationSource>();
        let sourceCalls = 0;
        fetchSourceMock.mockImplementation((asOfDate: string) => {
            sourceCalls += 1;
            return sourceCalls === 1 ? oldSource.promise : Promise.resolve(allocationSource(asOfDate, [ownedAsset()]));
        });
        const compute = deferred<PacSuccess>();
        runToolMock.mockImplementationOnce(() => compute.promise);
        const rendered = renderTool();
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(1));

        transitionClientSession(`pac-source-other-account-${++accountSequence}`);
        accountGeneration = getClientSessionGeneration();
        descriptor = makeDescriptor();
        await rendered.rerender({descriptor, accountGeneration});
        expect(await screen.findByTestId('pac-owned-asset-17')).toBeInTheDocument();

        oldSource.resolve(
            allocationSource(localIsoOffset(0), [
                ownedAsset({
                    assetId: 99,
                    instrumentKey: 'asset:99',
                    candidateKey: 'candidate:asset:99',
                    name: 'Late source from old account',
                }),
            ]),
        );
        await oldSource.promise;
        await Promise.resolve();
        expect(screen.getByTestId('pac-owned-asset-17')).toBeInTheDocument();
        expect(screen.queryByTestId('pac-owned-asset-99')).toBeNull();

        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Session-bound compute row'}});
        const computeGeneration = accountGeneration;
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));
        transitionClientSession(`pac-compute-other-account-${++accountSequence}`);
        compute.resolve(successResult('c-account-stale', readyOutput(), computeGeneration));

        await waitFor(() => expect(screen.getByTestId('pac-response-ignored')).toBeInTheDocument());
        expect(screen.queryByTestId('pac-result')).toBeNull();
        expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false');
    });

    // Three explicit cases rather than one `it.each`: each backend output
    // variant has its own concrete generated type (`NeedsInputOutput` /
    // `InvalidOutput` / `UnsupportedOutput`), and keeping them as separate
    // blocks lets every fixture call stay precisely typed to its own variant
    // instead of widening through a parameterized-array element type.
    async function expectDomainState(availability: 'needs_input' | 'invalid' | 'unsupported', output: PacOutput): Promise<void> {
        runToolMock.mockResolvedValueOnce(successResult(`c-${availability}`, output, accountGeneration));
        renderTool();
        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: `${availability} result fixture`}});

        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const result = await screen.findByTestId('pac-result');
        await waitFor(() => expect(result).toHaveAttribute('data-state', availability));
        expect(result).toHaveAttribute('data-view', 'formatted');

        expect(screen.getByTestId('pac-issues')).toBeInTheDocument();
        // Normalized input/units are only meaningful for a ready result.
        expect(screen.queryByTestId('pac-normalized-details')).toBeNull();
    }

    it('renders a backend needs_input output as its own domain state, distinct from a ready result', async () => {
        await expectDomainState('needs_input', needsInputOutput());
        expectResultGuidance();
    });

    it('renders a backend invalid output as its own domain state, distinct from a ready result', async () => {
        await expectDomainState('invalid', invalidOutput());
    });

    it('renders a backend unsupported output as its own domain state, distinct from a ready result', async () => {
        await expectDomainState('unsupported', unsupportedOutput());
    });

    it('renders a platform failure and preserves the draft', async () => {
        renderTool();
        await addManualRow();
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Kept ETF'}});

        runToolMock.mockResolvedValueOnce(errorResult('c-error', 'execution_failed', true, accountGeneration));
        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const platformError = await screen.findByTestId('pac-platform-error');
        expect(platformError).toHaveAttribute('data-error-code', 'execution_failed');
        expect(screen.queryByTestId('pac-result')).toBeNull();

        expect(screen.getByTestId('pac-report-currency-trigger')).toHaveTextContent('EUR');
        expect(field('pac-display-name-0')).toHaveValue('Kept ETF');
    });
});
