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
import {getCompiledToolContract, validateToolCatalog, verifyToolDescriptor, type CompatibleToolDescriptor, type ToolBatchMetrics, type ToolInput, type ToolItemMetrics, type ToolOutput} from '$lib/features/tools/contracts';
import type {ToolItemResult, ToolRunOptions} from '$lib/features/tools/client';
import PacAllocatorTool from './PacAllocatorTool.svelte';

// =========================================================================
// The one boundary this spec mocks.
// =========================================================================
// `vi.mock` factories are hoisted above ordinary `const` declarations, so the
// mock itself must be created through `vi.hoisted` (see client.test.ts /
// ProviderAssignmentSection.test.ts for the same idiom).
const {runToolMock} = vi.hoisted(() => ({
    runToolMock: vi.fn<(code: 'pac_allocator', version: '1.0.0', options: ToolRunOptions<'pac_allocator', '1.0.0'>) => Promise<ToolItemResult<'pac_allocator', '1.0.0'>>>(),
}));

vi.mock('$lib/features/tools/client', () => ({runTool: runToolMock}));

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
// Descriptor / catalog setup. Built once through the real, unmocked
// `contracts.ts` functions so the descriptor the component receives is
// genuinely branded/compatible — the same path the production renderer takes
// (see `registry.ts`) — rather than a hand-typed stand-in.
// =========================================================================
let descriptor: PacDescriptor;
let accountGeneration: number;

beforeAll(async () => {
    await setupI18n();

    transitionClientSession('pac-allocator-component-test');
    accountGeneration = getClientSessionGeneration();

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
    descriptor = verifyToolDescriptor(catalog, 'pac_allocator', '1.0.0');
});

beforeEach(() => {
    runToolMock.mockReset();
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

describe('PacAllocatorTool (pac-allocator)', () => {
    it('caps existing cash and contributions independently at four rows', async () => {
        renderTool();

        const addCash = screen.getByTestId('pac-add-cash');
        for (let index = 0; index < 4; index++) await fireEvent.click(addCash);
        expect(screen.getAllByTestId('pac-existing-cash-row')).toHaveLength(4);
        expect(addCash).toBeDisabled();
        await fireEvent.click(addCash);
        expect(screen.getAllByTestId('pac-existing-cash-row')).toHaveLength(4);

        const addContribution = screen.getByTestId('pac-add-contribution');
        for (let index = 0; index < 4; index++) await fireEvent.click(addContribution);
        expect(screen.getAllByTestId('pac-contribution-row')).toHaveLength(4);
        expect(addContribution).toBeDisabled();
        await fireEvent.click(addContribution);
        expect(screen.getAllByTestId('pac-contribution-row')).toHaveLength(4);
    });

    it('sends a manually-filled draft as a correctly separated typed request, with no browser-computed economic result', async () => {
        const {promise, resolve} = deferred<PacSuccess>();
        runToolMock.mockImplementationOnce(() => promise);
        renderTool();

        await fireEvent.input(screen.getByTestId('pac-report-currency'), {target: {value: 'EUR'}});

        const row0 = rowByIndex(0);
        await fireEvent.input(within(row0).getByTestId('pac-row-name'), {target: {value: 'Local ETF'}});
        await fireEvent.input(within(row0).getByTestId('pac-initial-quantity'), {target: {value: '10'}});
        await fireEvent.input(within(row0).getByTestId('pac-price'), {target: {value: '100'}});
        await fireEvent.input(within(row0).getByTestId('pac-price-currency'), {target: {value: 'EUR'}});
        await fireEvent.input(within(row0).getByTestId('pac-target-percent'), {target: {value: '100'}});

        await fireEvent.click(screen.getByTestId('pac-add-cash'));
        await fireEvent.input(screen.getByTestId('pac-cash-currency'), {target: {value: 'EUR'}});
        await fireEvent.input(screen.getByTestId('pac-cash-amount'), {target: {value: '500'}});

        await fireEvent.click(screen.getByTestId('pac-add-contribution'));
        await fireEvent.input(screen.getByTestId('pac-contribution-currency'), {target: {value: 'USD'}});
        await fireEvent.input(screen.getByTestId('pac-contribution-amount'), {target: {value: '200'}});

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));

        const [call] = runToolMock.mock.calls;
        if (!call) throw new Error('runTool was not called');
        const [code, version, options] = call;
        expect(code).toBe('pac_allocator');
        expect(version).toBe('1.0.0');

        const parameters: ToolInput<'pac_allocator', '1.0.0'> = options.parameters;

        // Exactly the seven `PacInput` fields — nothing computed (no aggregate
        // total, no merged cash figure) was added on top of the typed draft.
        expect(Object.keys(parameters).sort()).toEqual(['as_of_date', 'cash_balances', 'contributions', 'operation', 'report_currency', 'rows', 'valuation_rates']);

        expect(parameters.operation).toBe('analyze');
        expect(parameters.report_currency).toBe('EUR');

        // `cash_balances` and `contributions` are separate vectors, never merged.
        expect(parameters.cash_balances).toEqual([{currency: 'EUR', amount: '500'}]);
        expect(parameters.contributions).toEqual([{currency: 'USD', amount: '200'}]);
        expect(parameters.valuation_rates).toEqual([]);

        const requestRows = parameters.rows ?? [];
        expect(requestRows).toHaveLength(1);
        const [requestRow] = requestRows;
        expect(requestRow.name).toBe('Local ETF');
        expect(requestRow.initial_quantity).toBe('10');
        // The wire schema allows `quote` to be absent; this draft never leaves it
        // unset, so check that precondition instead of assuming it.
        if (!requestRow.quote) throw new Error('expected the row to carry a quote');
        expect(requestRow.quote.raw_price).toBe('100');
        expect(requestRow.quote.currency).toBe('EUR');
        expect(requestRow.target_percent).toBe('100');

        // Until the backend boundary resolves there is no economic result for
        // the browser to invent from the draft.
        expect(screen.queryByTestId('pac-result')).toBeNull();
        resolve(successResult('c-draft', readyOutput(), accountGeneration));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
    });

    it('renders a ready result as backend facts, with execution metrics as an independent section', async () => {
        runToolMock.mockResolvedValueOnce(successResult('c-ready', readyOutput(), accountGeneration));
        renderTool();

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

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));

        // Edit the draft while the request above is still in flight.
        const row0 = rowByIndex(0);
        await fireEvent.input(within(row0).getByTestId('pac-row-name'), {target: {value: 'Changed mid-flight'}});

        await waitFor(() => expect(screen.getByTestId('pac-request-stale')).toBeInTheDocument());

        resolve(successResult('c-stale', readyOutput(), accountGeneration));

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

        await fireEvent.input(screen.getByTestId('pac-report-currency'), {target: {value: 'EUR'}});
        const row0 = rowByIndex(0);
        await fireEvent.input(within(row0).getByTestId('pac-row-name'), {target: {value: 'Kept ETF'}});

        runToolMock.mockResolvedValueOnce(errorResult('c-error', 'execution_failed', true, accountGeneration));
        await fireEvent.click(screen.getByTestId('pac-analyze'));

        const platformError = await screen.findByTestId('pac-platform-error');
        expect(platformError).toHaveAttribute('data-error-code', 'execution_failed');
        expect(screen.queryByTestId('pac-result')).toBeNull();

        expect(screen.getByTestId('pac-report-currency')).toHaveValue('EUR');
        expect(within(rowByIndex(0)).getByTestId('pac-row-name')).toHaveValue('Kept ETF');
    });
});
