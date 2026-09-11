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
 *   - CSS classes, or the exact/formatted view toggle (a display preference, not
 *     a contract).
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import {ToolClientError, getCompiledToolContract, validateToolCatalog, verifyToolDescriptor, type CompatibleToolDescriptor, type ToolBatchMetrics, type ToolInput, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
import type {ToolItemResult, ToolRunOptions} from '$lib/features/tools/client';
import type {PacAllocationSource, PacAllocationSourceAsset} from './allocationSource';
import PacAllocatorTool from './PacAllocatorTool.svelte';

// =========================================================================
// The one boundary this spec mocks.
// =========================================================================
// `vi.mock` factories are hoisted above ordinary `const` declarations, so the
// mock itself must be created through `vi.hoisted` (see client.test.ts /
// ProviderAssignmentSection.test.ts for the same idiom).
const {runToolMock, fetchSourceMock, ensureCurrenciesLoadedMock} = vi.hoisted(() => ({
    runToolMock: vi.fn<(code: 'pac_allocator', version: '1.0.0', options: ToolRunOptions<'pac_allocator', '1.0.0'>) => Promise<ToolItemResult<'pac_allocator', '1.0.0'>>>(),
    fetchSourceMock: vi.fn(),
    ensureCurrenciesLoadedMock: vi.fn(),
}));

vi.mock('$lib/features/tools/client', () => ({runTool: runToolMock}));
vi.mock('./allocationSource', () => ({fetchPacAllocationSource: fetchSourceMock}));
vi.mock('$lib/stores/reference/currencyStore', () => ({
    ensureCurrenciesLoaded: ensureCurrenciesLoadedMock,
    getAllCurrencies: () => [
        {code: 'EUR', name: 'Euro fixture', symbol: '€', flag_emoji: '🇪🇺', country_codes: ['EU'], country_names: ['Fixture Europe']},
        {code: 'USD', name: 'Dollar fixture', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['Fixture United States']},
        {code: 'CHF', name: 'Franc fixture', symbol: 'CHF', flag_emoji: '🇨🇭', country_codes: ['CH'], country_names: ['Fixture Switzerland']},
    ],
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
        contributions: [{amount: '200', currency: 'EUR'}],
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
function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((res) => {
        resolve = res;
    });
    return {promise, resolve};
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
        name: 'Fixture global ETF',
        ticker: 'FIX',
        assetType: 'ETF',
        iconUrl: null,
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
                ownershipSharePercent: '25',
                custodyQuantity: '12.345678901234',
            },
            {
                contextKey: 'asset:17:broker:4',
                brokerId: 4,
                brokerName: 'Fixture broker B',
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

function allocationSource(asOfDate: string, assets: readonly PacAllocationSourceAsset[] = []): PacAllocationSource {
    return {
        generatedAt: `${asOfDate}T12:00:00Z`,
        asOfDate,
        assets,
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
    const row = document.querySelector<HTMLElement>(`[data-testid="pac-row"][data-row-index="${index}"]`);
    if (!row) throw new Error(`row ${index} not found`);
    return row;
}

function field(testid: string): HTMLInputElement {
    return screen.getByTestId(testid) as HTMLInputElement;
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

/** Selects a SimpleSelect option by keyboard distance from its current value. */
async function stepSimpleSelect(testId: string, arrowMoves: number): Promise<void> {
    const trigger = screen.getByTestId(`${testId}-button`);
    await fireEvent.click(trigger);
    for (let index = 0; index < arrowMoves; index += 1) {
        await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
    }
    await fireEvent.keyDown(trigger, {key: 'Enter'});
    await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));
}

/**
 * The three money modes, in the order `PacMoneySection` declares them. Naming the
 * index here rather than counting arrow presses from wherever the select happens
 * to be means a mode can be selected *absolutely* (Home, then N steps down), in
 * either direction, without ever matching on a translated option label.
 */
const MONEY_MODE_INDEX = {not_supplied: 0, none: 1, custom: 2} as const;

async function selectMoneyMode(kind: 'cash' | 'contributions', mode: keyof typeof MONEY_MODE_INDEX): Promise<void> {
    const trigger = screen.getByTestId(`pac-${kind}-mode-button`);
    await fireEvent.click(trigger);
    await fireEvent.keyDown(trigger, {key: 'Home'});
    for (let index = 0; index < MONEY_MODE_INDEX[mode]; index += 1) {
        await fireEvent.keyDown(trigger, {key: 'ArrowDown'});
    }
    await fireEvent.keyDown(trigger, {key: 'Enter'});
    await waitFor(() => expect(trigger).toHaveAttribute('aria-expanded', 'false'));
    // The section publishes which mode it landed in, so the helper ends on the
    // post-condition it promises instead of on "a key was pressed".
    if (mode === 'custom') await waitFor(() => expect(screen.getAllByTestId(`pac-${kind}-row`).length).toBeGreaterThan(0));
    else await waitFor(() => expect(screen.getByTestId(`pac-${kind}-${mode === 'none' ? 'none' : 'not-supplied'}`)).toBeInTheDocument());
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
    it('starts with no rows, the local date, and the configured report currency', async () => {
        userSettings.setDirect({language: 'en', base_currency: 'CHF', theme: 'auto', avatar_url: null});
        renderTool();

        expect(screen.getByTestId('pac-no-rows')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-row')).toHaveLength(0);
        expect(screen.getByTestId('pac-as-of-date')).toHaveValue(localIsoOffset(0));
        await waitFor(() => expect(screen.getByTestId('pac-report-currency-trigger')).toHaveTextContent('CHF'));
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

    it('keeps manual entry available when the allocation source fails', async () => {
        fetchSourceMock.mockRejectedValueOnce(new ToolClientError('network', 'network_failed'));
        renderTool();

        expect(await screen.findByTestId('pac-owned-assets-error')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        expect(rowByIndex(0)).toBeInTheDocument();
    });

    it('keeps manual entry available for an empty allocation source', async () => {
        renderTool();

        expect(await screen.findByTestId('pac-owned-assets-empty')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        expect(rowByIndex(0)).toBeInTheDocument();
    });

    it('renders custom currency/date/grid/quote selectors and exact decimal fields', async () => {
        renderTool();
        await addManualRow();

        expect(screen.getByTestId('pac-report-currency')).toContainElement(screen.getByTestId('pac-report-currency-trigger'));
        expect(screen.getByTestId('pac-as-of-date')).toHaveAttribute('type', 'text');
        expect(screen.getByTestId('pac-asset-currency-0')).toContainElement(screen.getByTestId('pac-asset-currency-0-trigger'));
        expect(screen.getByTestId('pac-price-basis-0')).toContainElement(screen.getByTestId('pac-price-basis-0-button'));
        expect(screen.getByTestId('pac-price-date-0')).toHaveAttribute('type', 'text');
        expect(screen.getByTestId('pac-grid-mode-0')).toContainElement(screen.getByTestId('pac-grid-mode-0-button'));

        for (const testid of ['pac-initial-quantity-0', 'pac-raw-price-0', 'pac-target-weight-0', 'pac-step-quantity-0']) {
            expect(screen.getByTestId(testid)).toHaveAttribute('type', 'text');
            expect(screen.getByTestId(testid)).toHaveAttribute('inputmode', 'decimal');
        }
    });

    it('caps custom cash and contributions independently at four rows', async () => {
        renderTool();

        await stepSimpleSelect('pac-cash-mode', 2);
        const addCash = screen.getByTestId('pac-add-cash');
        for (let index = 1; index < 4; index += 1) await fireEvent.click(addCash);
        expect(screen.getAllByTestId('pac-cash-row')).toHaveLength(4);
        expect(addCash).toBeDisabled();

        await stepSimpleSelect('pac-contributions-mode', 2);
        const addContribution = screen.getByTestId('pac-add-contributions');
        for (let index = 1; index < 4; index += 1) await fireEvent.click(addContribution);
        expect(screen.getAllByTestId('pac-contributions-row')).toHaveLength(4);
        expect(addContribution).toBeDisabled();
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
            cash_balances: null,
            contributions: null,
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

    it('imports every custody context of one canonical asset atomically and keeps missing-price assets', async () => {
        const requestedDate = localIsoOffset(0);
        const missingPrice = ownedAsset({
            assetId: 18,
            instrumentKey: 'asset:18',
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
                    ownershipSharePercent: '100',
                    custodyQuantity: '3',
                },
            ],
        });
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset(), missingPrice]));
        renderTool();

        const groupedCard = await screen.findByTestId('pac-owned-asset-17');
        expect(screen.queryAllByTestId('pac-owned-asset-17')).toHaveLength(1);
        await fireEvent.click(groupedCard);
        await fireEvent.click(screen.getByTestId('pac-owned-asset-18'));

        expect(screen.getAllByTestId('pac-row')).toHaveLength(3);
        expect(field('pac-initial-quantity-0')).toHaveValue('12.345678901234');
        expect(field('pac-initial-quantity-1')).toHaveValue('7.000000000001');
        expect(field('pac-raw-price-2')).toHaveValue('');
        expect(field('pac-target-weight-0')).toHaveValue('');
        expect(field('pac-step-quantity-0')).toHaveValue('');

        const parameters = await analyzeAndReadInput();
        expect(parameters.as_of_date).toBe(requestedDate);
        expect(parameters.rows).toHaveLength(3);
        expect(parameters.rows?.map((row) => row.initial_quantity)).toEqual(['12.345678901234', '7.000000000001', '3']);
        expect(parameters.rows?.[0]?.quote).toEqual({
            raw_price: '123.450000000001',
            currency: 'USD',
            quote_base_quantity: 100,
            reference_date: '2026-09-09',
        });
        expect(parameters.rows?.[2]?.quote?.raw_price).toBeNull();
        expect(parameters.rows?.[0]?.target_percent).toBe('');
        expect(parameters.rows?.[0]?.buy_grid).toEqual({mode: null, quantity_step: ''});

        for (const row of parameters.rows ?? []) {
            expect(Object.keys(row).sort()).toEqual(['buy_grid', 'initial_quantity', 'instrument_key', 'name', 'quote', 'row_key', 'target_percent']);
            expect(row).not.toHaveProperty('origin');
            expect(row).not.toHaveProperty('source');
            expect(row).not.toHaveProperty('importedValue');
            expect(row).not.toHaveProperty('stale');
        }
    });

    it('enforces the 32-row cap all-or-nothing for a multi-context asset', async () => {
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');

        for (let index = 0; index < 31; index += 1) {
            await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        }
        expect(screen.getAllByTestId('pac-row')).toHaveLength(31);

        await fireEvent.click(card);

        expect(screen.getAllByTestId('pac-row')).toHaveLength(31);
        expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    it('duplicates every payload field except for a fresh row key and keeps mobile actions accessible', async () => {
        const oneContext = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [oneContext]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await stepSimpleSelect('pac-grid-mode-0', 1);
        await fireEvent.input(field('pac-step-quantity-0'), {target: {value: '2.500000000001'}});

        const duplicate = screen.getByTestId('pac-duplicate-asset-0');
        const remove = screen.getByTestId('pac-remove-asset-0');
        expect(duplicate).toHaveAccessibleName();
        expect(remove).toHaveAccessibleName();
        await fireEvent.click(duplicate);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        const parameters = await analyzeAndReadInput();
        const rows = parameters.rows ?? [];
        expect(rows).toHaveLength(2);
        const [original, copy] = rows;
        if (!original || !copy) throw new Error('expected original and duplicate rows');
        const {row_key: originalKey, ...originalPayload} = original;
        const {row_key: copyKey, ...copyPayload} = copy;
        expect(copyKey).not.toBe(originalKey);
        expect(copyPayload).toEqual(originalPayload);
    });

    it('confirms deselection when an edited duplicate is linked to the selected asset', async () => {
        const oneContext = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [oneContext]));
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');
        await fireEvent.click(card);
        await fireEvent.click(screen.getByTestId('pac-duplicate-asset-0'));
        await fireEvent.input(field('pac-display-name-1'), {target: {value: 'Edited duplicate fixture'}});

        await fireEvent.click(card);

        const confirmation = screen.getByTestId('pac-confirm-deselect');
        expect(confirmation).toBeInTheDocument();
        expect(screen.getByRole('listitem')).toHaveTextContent('Edited duplicate fixture');
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        expect(screen.queryAllByTestId('pac-row')).toHaveLength(0);
        expect(card).toHaveAttribute('aria-pressed', 'false');
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
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Edited broker A row'}});
        await fireEvent.input(field('pac-display-name-1'), {target: {value: 'Edited broker B row'}});

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));

        const listed = screen.getAllByRole('listitem');
        expect(listed).toHaveLength(1);
        expect(listed[0]).toHaveTextContent('Edited broker A row');
        expect(listed[0]).toHaveTextContent('Fixture broker A');
        expect(listed[0]).not.toHaveTextContent('Fixture broker B');
        // Nothing is removed until the answer comes back.
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        expect(screen.getAllByTestId('pac-row')).toHaveLength(1);
        expect(field('pac-display-name-0')).toHaveValue('Edited broker B row');
        expect(card).toHaveAttribute('aria-pressed', 'true');
    });

    it('cancels a single-row removal without touching the draft', async () => {
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Edited broker A row'}});

        await fireEvent.click(screen.getByTestId('pac-remove-asset-0'));
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));

        expect(screen.queryAllByRole('listitem')).toHaveLength(0);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);
        expect(field('pac-display-name-0')).toHaveValue('Edited broker A row');
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

    it('describes and removes every linked context when the gallery card is deselected', async () => {
        // The contrast with the row button above: one click on the card is an
        // intention about the whole asset, so every modified context it owns is
        // named, and confirming takes all of them out.
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [ownedAsset()]));
        renderTool();
        const card = await screen.findByTestId('pac-owned-asset-17');
        await fireEvent.click(card);
        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Edited broker A row'}});
        await fireEvent.input(field('pac-display-name-1'), {target: {value: 'Edited broker B row'}});

        await fireEvent.click(card);

        // Two modified contexts, so the list starts collapsed: open it and read
        // what the user is about to lose.
        await expandConfirmationItems('pac-confirm-deselect');
        const listed = screen.getAllByRole('listitem').map((item) => item.textContent ?? '');
        expect(listed).toHaveLength(2);
        expect(listed.some((text) => text.includes('Edited broker A row') && text.includes('Fixture broker A'))).toBe(true);
        expect(listed.some((text) => text.includes('Edited broker B row') && text.includes('Fixture broker B'))).toBe(true);
        expect(screen.getAllByTestId('pac-row')).toHaveLength(2);

        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        expect(screen.queryAllByTestId('pac-row')).toHaveLength(0);
        expect(card).toHaveAttribute('aria-pressed', 'false');
    });

    it('marks imported rows stale, ignores a late source response, and confirms refresh conflicts without replacing target/grid', async () => {
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

        await fireEvent.input(field('pac-display-name-0'), {target: {value: 'Edited local name'}});
        await fireEvent.input(field('pac-target-weight-0'), {target: {value: '42.5'}});
        await stepSimpleSelect('pac-grid-mode-0', 1);
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

        superseded.resolve(
            allocationSource(supersededDate, [
                ownedAsset({
                    name: 'Late response name',
                    contexts: [{...ownedAsset().contexts[0]!, custodyQuantity: '88'}],
                }),
            ]),
        );
        await Promise.resolve();
        expect(field('pac-display-name-0')).toHaveValue('Edited local name');
        expect(field('pac-initial-quantity-0')).toHaveValue('12.345678901234');

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

        // Merely receiving the fresh source never overwrites the editable copy.
        expect(field('pac-display-name-0')).toHaveValue('Edited local name');
        expect(field('pac-initial-quantity-0')).toHaveValue('12.345678901234');
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));

        const confirmation = screen.getByTestId('pac-confirm-refresh');
        expect(confirmation).toBeInTheDocument();
        expect(screen.getByRole('listitem')).toHaveTextContent('Edited local name');
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));

        expect(field('pac-display-name-0')).toHaveValue('Fresh server name');
        expect(field('pac-initial-quantity-0')).toHaveValue('99.000000000001');
        expect(field('pac-raw-price-0')).toHaveValue('200.000000000001');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(field('pac-step-quantity-0')).toHaveValue('2.5');

        const parameters = await analyzeAndReadInput();
        expect(parameters.as_of_date).toBe(currentDate);
        expect(parameters.rows?.[0]).toMatchObject({
            name: 'Fresh server name',
            initial_quantity: '99.000000000001',
            target_percent: '42.5',
            buy_grid: {mode: 'whole', quantity_step: '2.5'},
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
        // Arrival alone changed nothing the user can see in their own copy.
        expect(field('pac-display-name-0')).toHaveValue('Fixture global ETF');
        expect(field('pac-initial-quantity-0')).toHaveValue('12.345678901234');
        expect(field('pac-initial-quantity-1')).toHaveValue('7.000000000001');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');

        // Reconciling takes the server's facts and leaves the draft-only fields
        // alone; with both contexts accounted for, the warning goes away again.
        await waitFor(() => expect(screen.getByTestId('pac-refresh-copied-facts')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));
        await waitFor(() => expect(field('pac-initial-quantity-0')).toHaveValue('55.000000000001'));
        expect(field('pac-display-name-0')).toHaveValue('Fresh server name');
        expect(field('pac-target-weight-0')).toHaveValue('42.5');
        expect(field('pac-initial-quantity-1')).toHaveValue('7.000000000001');
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
        expect(field('pac-initial-quantity-1')).toHaveValue('7.000000000001');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');

        // A row whose context vanished has nothing to reconcile against, so it
        // keeps the copy it has and keeps saying it is out of date.
        await waitFor(() => expect(screen.getByTestId('pac-refresh-copied-facts')).toBeEnabled());
        await fireEvent.click(screen.getByTestId('pac-refresh-copied-facts'));
        expect(field('pac-initial-quantity-1')).toHaveValue('7.000000000001');
        expect(field('pac-target-weight-1')).toHaveValue('57.5');
        expect(screen.getByTestId('pac-stale-source')).toBeInTheDocument();

        const parameters = await analyzeAndReadInput();
        expect(parameters.rows?.map((row) => row.initial_quantity)).toEqual(['55.000000000001', '7.000000000001']);
        expect(parameters.rows?.map((row) => row.target_percent)).toEqual(['42.5', '57.5']);
    });

    it('serializes cash and contributions as null, empty arrays, or entered values according to their tri-state modes', async () => {
        renderTool();

        const omitted = await analyzeAndReadInput();
        expect(omitted.cash_balances).toBeNull();
        expect(omitted.contributions).toBeNull();

        await stepSimpleSelect('pac-cash-mode', 1);
        await stepSimpleSelect('pac-contributions-mode', 1);
        const explicitNone = await analyzeAndReadInput();
        expect(explicitNone.cash_balances).toEqual([]);
        expect(explicitNone.contributions).toEqual([]);

        await stepSimpleSelect('pac-cash-mode', 1);
        await stepSimpleSelect('pac-contributions-mode', 1);
        await selectCurrency('pac-cash-currency-0', 'EUR');
        await fireEvent.input(field('pac-cash-amount-0'), {target: {value: '500.000000000001'}});
        await selectCurrency('pac-contributions-currency-0', 'USD');
        await fireEvent.input(field('pac-contributions-amount-0'), {target: {value: '200.000000000001'}});

        const entered = await analyzeAndReadInput();
        expect(entered.cash_balances).toEqual([{currency: 'EUR', amount: '500.000000000001'}]);
        expect(entered.contributions).toEqual([{currency: 'USD', amount: '200.000000000001'}]);
    });

    it('ignores cash and contribution rows retained behind an inactive mode when hinting at FX', async () => {
        // Switching a money section back to `not_supplied` / `none` keeps the
        // rows the user typed, so nothing is lost if they change their mind.
        // They are not part of the request in those modes, though, so a foreign
        // currency sitting in one of them must not ask for a rate that would
        // never be used — and must not disappear from the draft either.
        renderTool();
        expect(screen.queryByTestId('pac-fx-needed')).toBeNull();

        await selectMoneyMode('cash', 'custom');
        // A new row is created in the report currency, which is not foreign.
        expect(screen.queryByTestId('pac-fx-needed')).toBeNull();
        await selectCurrency('pac-cash-currency-0', 'CHF');
        await fireEvent.input(field('pac-cash-amount-0'), {target: {value: '500'}});
        expect(screen.getByTestId('pac-fx-needed')).toBeInTheDocument();

        await selectMoneyMode('contributions', 'custom');
        await selectCurrency('pac-contributions-currency-0', 'USD');
        await fireEvent.input(field('pac-contributions-amount-0'), {target: {value: '200'}});
        expect(screen.getByTestId('pac-fx-needed')).toBeInTheDocument();

        // Cash goes quiet; the contribution in USD is still live, so the hint is
        // still right to be there — which is what makes the next step a real
        // assertion rather than a hint that happened to vanish.
        await selectMoneyMode('cash', 'none');
        expect(screen.getByTestId('pac-fx-needed')).toBeInTheDocument();

        await selectMoneyMode('contributions', 'not_supplied');
        expect(screen.queryByTestId('pac-fx-needed')).toBeNull();

        // The hint is only half the contract. `addValuationRate()` suggests the
        // first foreign currency that is not configured yet, off the same
        // `foreignCurrencies` list, so a retained CHF/USD row must not seed a
        // rate the request would never carry either. Asserted on the serialized
        // payload — an empty `currency` is the machine-readable proof that
        // nothing was auto-selected, with no translated label involved.
        const rates = screen.getByTestId('pac-valuation-rates');
        await fireEvent.click(within(rates).getByRole('button', {expanded: false}));
        await fireEvent.click(screen.getByTestId('pac-enable-rates'));
        await fireEvent.click(screen.getByTestId('pac-add-rate'));
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(1);
        expect(screen.getByTestId('pac-rate-currency-0-trigger')).not.toHaveTextContent(/CHF|USD/);
        expect((await analyzeAndReadInput()).valuation_rates).toEqual([{currency: '', rate_to_report: '', reference_date: ''}]);

        // Hand the section back exactly as it was found: the empty rate goes, and
        // manual rates go off again, because `pac-fx-needed` is suppressed while
        // `allowFx` is on and the assertions below are about the hint.
        await fireEvent.click(screen.getByTestId('pac-remove-rate-0'));
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(0);
        await fireEvent.click(screen.getByTestId('pac-enable-rates'));
        await waitFor(() => expect(screen.queryByTestId('pac-add-rate')).toBeNull());
        expect(screen.queryByTestId('pac-fx-needed')).toBeNull();

        // Neither row was thrown away: both come back exactly as typed, and so
        // does the hint they justify.
        await selectMoneyMode('cash', 'custom');
        await selectMoneyMode('contributions', 'custom');
        expect(screen.getByTestId('pac-cash-currency-0-trigger')).toHaveTextContent('CHF');
        expect(field('pac-cash-amount-0')).toHaveValue('500');
        expect(screen.getByTestId('pac-contributions-currency-0-trigger')).toHaveTextContent('USD');
        expect(field('pac-contributions-amount-0')).toHaveValue('200');
        expect(screen.getByTestId('pac-fx-needed')).toBeInTheDocument();

        // And the same suggestion, on the same two rows, now that both modes are
        // live again: CHF is offered. Without this the empty suggestion above
        // would also be satisfied by a component that never suggests anything.
        await fireEvent.click(within(screen.getByTestId('pac-valuation-rates')).getByRole('button', {expanded: false}));
        await fireEvent.click(screen.getByTestId('pac-enable-rates'));
        await fireEvent.click(screen.getByTestId('pac-add-rate'));
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(1);
        expect((await analyzeAndReadInput()).valuation_rates).toEqual([{currency: 'CHF', rate_to_report: '', reference_date: ''}]);
    });

    it('keeps valuation rates manual even when imported rows use a foreign currency', async () => {
        const oneContext = ownedAsset({contexts: [ownedAsset().contexts[0]!]});
        fetchSourceMock.mockImplementation(async (asOfDate: string) => allocationSource(asOfDate, [oneContext]));
        renderTool();
        await fireEvent.click(await screen.findByTestId('pac-owned-asset-17'));

        expect(screen.getByTestId('pac-fx-needed')).toBeInTheDocument();
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(0);
        expect((await analyzeAndReadInput()).valuation_rates).toEqual([]);

        const rates = screen.getByTestId('pac-valuation-rates');
        await fireEvent.click(within(rates).getByRole('button', {expanded: false}));
        await fireEvent.click(screen.getByTestId('pac-enable-rates'));
        expect(screen.queryAllByTestId('pac-rate-row')).toHaveLength(0);
        await fireEvent.click(screen.getByTestId('pac-add-rate'));
        await selectCurrency('pac-rate-currency-0', 'USD');
        await fireEvent.input(field('pac-rate-value-0'), {target: {value: '0.900000000001'}});
        const rateDate = field('pac-rate-date-0');
        await fireEvent.input(rateDate, {target: {value: localIsoOffset(-1)}});
        await fireEvent.blur(rateDate);

        expect((await analyzeAndReadInput()).valuation_rates).toEqual([{currency: 'USD', rate_to_report: '0.900000000001', reference_date: localIsoOffset(-1)}]);
    });

    it('renders a ready result as backend facts, with execution metrics as an independent section', async () => {
        renderTool();
        queueSuccess(readyOutput());
        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const result = await screen.findByTestId('pac-result');
        expect(result).toHaveAttribute('data-state', 'ready');

        expect(screen.getByTestId('pac-total-invested')).toHaveTextContent('1150 EUR');
        expect(screen.getByTestId('pac-total-existing-cash')).toHaveTextContent('500 EUR');
        expect(screen.getByTestId('pac-total-contributions')).toHaveTextContent('200 EUR');
        expect(screen.getByTestId('pac-total-combined-cash')).toHaveTextContent('700 EUR');

        const resultRows = within(screen.getByTestId('pac-result-rows')).getAllByTestId('pac-result-row');
        expect(resultRows).toHaveLength(1);
        const [resultRow] = resultRows;
        expect(resultRow).toHaveTextContent('ETF Global');

        expect(screen.getByTestId('pac-normalized-details')).toBeInTheDocument();

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

    it('ignores a compute response after the account generation changes', async () => {
        const {promise, resolve} = deferred<PacSuccess>();
        runToolMock.mockImplementationOnce(() => promise);
        renderTool();

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));
        transitionClientSession(`pac-compute-other-account-${++accountSequence}`);
        resolve(successResult('c-account-stale', readyOutput(), accountGeneration));

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

        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const result = await screen.findByTestId('pac-result');
        await waitFor(() => expect(result).toHaveAttribute('data-state', availability));

        expect(screen.getByTestId('pac-issues')).toBeInTheDocument();
        // Normalized input/units are only meaningful for a ready result.
        expect(screen.queryByTestId('pac-normalized-details')).toBeNull();
    }

    it('renders a backend needs_input output as its own domain state, distinct from a ready result', async () => {
        await expectDomainState('needs_input', needsInputOutput());
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
