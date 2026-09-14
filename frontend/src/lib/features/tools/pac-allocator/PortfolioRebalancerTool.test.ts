// @vitest-environment jsdom
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
import {getCompiledToolContract, validateToolCatalog, verifyToolDescriptor, type CompatibleToolDescriptor, type ToolInput, type ToolOutput} from '$lib/features/tools/contracts';
import type {ToolItemResult, ToolRunOptions} from '$lib/features/tools/client';
import type {FetchPacAllocationSourceOptions, PacAllocationSource, PacAllocationSourceAsset, PacAllocationSourceContext} from './allocationSource';
import {closePercentDistribution, createManualRebalanceHolding} from './draftFactories';
import PortfolioRebalancerTool from './PortfolioRebalancerTool.svelte';

const {runToolMock, fetchSourceMock, lookupFxRateMock, ensureCurrenciesLoadedMock} = vi.hoisted(() => ({
    runToolMock: vi.fn<(code: 'portfolio_rebalancer', version: '1.0.0', options: ToolRunOptions<'portfolio_rebalancer', '1.0.0'>) => Promise<ToolItemResult<'portfolio_rebalancer', '1.0.0'>>>(),
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
    ],
    getCurrencyInfo: (code: string) => ({flag_emoji: code === 'EUR' ? '🇪🇺' : code === 'USD' ? '🇺🇸' : '🏳️'}),
}));
vi.mock('$lib/utils/providerHelpers', () => ({
    assetProvidersVersion: {
        subscribe: (run: (value: number) => void) => {
            run(0);
            return () => undefined;
        },
    },
    ensureAssetProvidersCached: vi.fn(() => Promise.resolve()),
    getAssetProviderIconUrl: vi.fn((code: string) => `/fixture/${code}.svg`),
}));

type RebalancerDescriptor = CompatibleToolDescriptor<'portfolio_rebalancer', '1.0.0'>;
type RebalancerOutput = ToolOutput<'portfolio_rebalancer', '1.0.0'>;

const P1_MAX_ROWS = 32;

let accountGeneration = 0;
let descriptor: RebalancerDescriptor;
let accountSequence = 0;

function deferred<T>(): {promise: Promise<T>; resolve: (value: T) => void} {
    let resolve!: (value: T) => void;
    const promise = new Promise<T>((accept) => {
        resolve = accept;
    });
    return {promise, resolve};
}

function policy() {
    return {
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
    };
}

function makeDescriptor(): RebalancerDescriptor {
    const contract = getCompiledToolContract('portfolio_rebalancer', '1.0.0');
    if (!contract) throw new Error('portfolio_rebalancer/1.0.0 generated contract is required');
    const catalog = validateToolCatalog(
        {
            catalog_version: '2',
            items: [
                {
                    tool_code: contract.toolCode,
                    contract_version: contract.contractVersion,
                    implementation_version: '1.0.0',
                    schema_fingerprint: contract.schemaFingerprint,
                    category: 'analysis',
                    description: 'Portfolio rebalancer fixture',
                    description_i18n_key: null,
                    documentation: {path: 'tools/portfolio-rebalancer', version: '1.0.0'},
                    icon_key: 'scale',
                    input_schema: {},
                    name: 'Portfolio rebalancer fixture',
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
                    ui: {kind: 'custom', component_key: contract.componentKey, version: contract.uiVersion},
                },
            ],
            policy: policy(),
            unavailable: [],
        },
        accountGeneration,
    );
    return verifyToolDescriptor(catalog, 'portfolio_rebalancer', '1.0.0');
}

function sourceContext(overrides: Partial<PacAllocationSourceContext> = {}): PacAllocationSourceContext {
    return {
        contextKey: 'asset:71:broker:11',
        brokerId: 11,
        brokerName: 'Fixture broker A',
        brokerIconUrl: null,
        brokerPortalUrl: null,
        brokerDefaultImportPlugin: null,
        ownershipSharePercent: '100',
        custodyQuantity: '2',
        ...overrides,
    };
}

function assetA(
    overrides: Omit<Partial<PacAllocationSourceAsset>, 'quote' | 'contexts'> & {
        quote?: Partial<PacAllocationSourceAsset['quote']>;
        contexts?: readonly PacAllocationSourceContext[];
    } = {},
): PacAllocationSourceAsset {
    const quote: PacAllocationSourceAsset['quote'] = {
        rawPrice: '10',
        currency: 'EUR',
        quoteBaseQuantity: 1,
        referenceDate: '2026-09-13',
        source: 'fixture',
        daysBeforeRequested: 1,
    };
    return {
        assetId: 71,
        instrumentKey: 'asset:71',
        candidateKey: 'candidate:71',
        name: 'Fixture aggregate ETF',
        ticker: 'AGG',
        assetType: 'ETF',
        iconUrl: null,
        active: true,
        usageScope: 'owned',
        ...overrides,
        quote: {...quote, ...overrides.quote},
        contexts: overrides.contexts ?? [
            sourceContext(),
            sourceContext({
                contextKey: 'asset:71:broker:12',
                brokerId: 12,
                brokerName: 'Fixture broker B',
                custodyQuantity: '3',
            }),
        ],
    };
}

function assetB(): PacAllocationSourceAsset {
    return {
        ...assetA(),
        assetId: 72,
        instrumentKey: 'asset:72',
        candidateKey: 'candidate:72',
        name: 'Fixture second ETF',
        ticker: 'SECOND',
        quote: {...assetA().quote, rawPrice: '25'},
        contexts: [
            sourceContext({
                contextKey: 'asset:72:broker:11',
                brokerId: 21,
                brokerName: 'Fixture broker Second',
                custodyQuantity: '4',
            }),
        ],
    };
}

function allocationSource(
    asOfDate: string,
    options: {
        assets?: readonly PacAllocationSourceAsset[];
        cashSources?: PacAllocationSource['cashSources'];
        selectedCashBalances?: PacAllocationSource['selectedCashBalances'];
    } = {},
): PacAllocationSource {
    return {
        generatedAt: `${asOfDate}T12:00:00Z`,
        asOfDate,
        assets: options.assets ?? [assetA(), assetB()],
        cashSources: options.cashSources ?? [],
        selectedCashBalances: options.selectedCashBalances ?? [],
    };
}

function available<T>(value: T): {availability: 'available'; value: T; reason_codes: []} {
    return {availability: 'available', value, reason_codes: []};
}

function percent(approximation: string): RebalancerOutput['instruments'][number]['current_weight_percent'] {
    return available({
        numerator: approximation.replace('.', ''),
        denominator: '1',
        approximation,
        approximation_decimal_places: 28,
        approximation_exact: true,
        unit: 'percent' as const,
    });
}

function gap(approximation: string): RebalancerOutput['instruments'][number]['gap_to_target_pp'] {
    return available({
        numerator: approximation.replace('.', ''),
        denominator: '1',
        approximation,
        approximation_decimal_places: 28,
        approximation_exact: true,
        unit: 'percentage_points' as const,
    });
}

function zeroInvestedUnavailable(): {availability: 'unavailable'; value: null; reason_codes: ['zero_invested_value']} {
    return {availability: 'unavailable', value: null, reason_codes: ['zero_invested_value']};
}

function readyOutput(nameA = 'Backend aggregate A', nameB = 'Backend aggregate B'): RebalancerOutput {
    return {
        operation: 'analyze',
        result_kind: 'portfolio_rebalancing_analysis',
        numeric_policy_id: 'portfolio-rebalancing-v1',
        availability: 'ready',
        holdings: [
            {
                holding_index: 0,
                row_key: 'asset:71:broker:11:0',
                instrument_key: 'asset:71',
                name: 'Fixture aggregate ETF',
                quantity: available('2'),
                current_value_native: available({amount: '20', currency: 'EUR'}),
                current_value_reporting: available({amount: '20', currency: 'EUR'}),
            },
            {
                holding_index: 1,
                row_key: 'asset:71:broker:12:1',
                instrument_key: 'asset:71',
                name: 'Fixture aggregate ETF',
                quantity: available('3'),
                current_value_native: available({amount: '30', currency: 'EUR'}),
                current_value_reporting: available({amount: '30', currency: 'EUR'}),
            },
            {
                holding_index: 2,
                row_key: 'asset:72:broker:11:0',
                instrument_key: 'asset:72',
                name: 'Fixture second ETF',
                quantity: available('4'),
                current_value_native: available({amount: '100', currency: 'EUR'}),
                current_value_reporting: available({amount: '100', currency: 'EUR'}),
            },
        ],
        instruments: [
            {
                target_index: 0,
                instrument_key: 'asset:71',
                name: nameA,
                custody_context_count: 2,
                current_value_reporting: available({amount: '50', currency: 'EUR'}),
                current_weight_percent: percent('33.333333333333'),
                target_percent: available('40'),
                target_value_reporting: available({amount: '60', currency: 'EUR'}),
                value_gap_to_target_reporting: available({amount: '10', currency: 'EUR'}),
                gap_to_target_pp: gap('6.666666666667'),
            },
            {
                target_index: 1,
                instrument_key: 'asset:72',
                name: nameB,
                custody_context_count: 1,
                current_value_reporting: available({amount: '100', currency: 'EUR'}),
                current_weight_percent: percent('66.666666666667'),
                target_percent: available('60'),
                target_value_reporting: available({amount: '90', currency: 'EUR'}),
                value_gap_to_target_reporting: available({amount: '-10', currency: 'EUR'}),
                gap_to_target_pp: gap('-6.666666666667'),
            },
        ],
        cash_pools: available([]),
        totals: {
            current_invested_reporting: available({amount: '150', currency: 'EUR'}),
            existing_cash_reporting: available({amount: '0', currency: 'EUR'}),
            contributions_reporting: available({amount: '0', currency: 'EUR'}),
            cash_plus_contributions_reporting: available({amount: '0', currency: 'EUR'}),
            target_total_percent: available('100'),
            max_abs_gap_pp: gap('6.666666666667'),
            squared_gap_pp2: available({
                numerator: '8888888888889777777777778',
                denominator: '100000000000000000000000',
                approximation: '88.88888888889777777777778',
                approximation_decimal_places: 28,
                approximation_exact: false,
                unit: 'percentage_points_squared',
            }),
        },
        normalized: {
            report_currency: 'EUR',
            as_of_date: null,
            holdings: [
                {
                    row_key: 'asset:71:broker:11:0',
                    instrument_key: 'asset:71',
                    name: 'Fixture aggregate ETF',
                    quantity: '2',
                    raw_price: '10',
                    currency: 'EUR',
                    quote_base_quantity: 1,
                    reference_date: null,
                    buy_grid: {mode: 'whole', quantity_step: '1'},
                },
                {
                    row_key: 'asset:71:broker:12:1',
                    instrument_key: 'asset:71',
                    name: 'Fixture aggregate ETF',
                    quantity: '3',
                    raw_price: '10',
                    currency: 'EUR',
                    quote_base_quantity: 1,
                    reference_date: null,
                    buy_grid: {mode: 'whole', quantity_step: '1'},
                },
                {
                    row_key: 'asset:72:broker:11:0',
                    instrument_key: 'asset:72',
                    name: 'Fixture second ETF',
                    quantity: '4',
                    raw_price: '25',
                    currency: 'EUR',
                    quote_base_quantity: 1,
                    reference_date: null,
                    buy_grid: {mode: 'whole', quantity_step: '1'},
                },
            ],
            targets: [
                {instrument_key: 'asset:71', target_percent: '40'},
                {instrument_key: 'asset:72', target_percent: '60'},
            ],
            cash_balances: [],
            contributions: [],
            valuation_rates: [],
        },
        issues: [],
    };
}

function zeroInvestedReadyOutput(): RebalancerOutput {
    const output = readyOutput();
    if (output.availability !== 'ready') throw new Error('READY Rebalancer fixture expected');
    return {
        ...output,
        holdings: output.holdings.map((holding) => ({
            ...holding,
            quantity: available('0'),
            current_value_native: available({amount: '0', currency: 'EUR'}),
            current_value_reporting: available({amount: '0', currency: 'EUR'}),
        })),
        instruments: output.instruments.map((instrument) => ({
            ...instrument,
            current_value_reporting: available({amount: '0', currency: 'EUR'}),
            current_weight_percent: zeroInvestedUnavailable(),
            target_value_reporting: available({amount: '0', currency: 'EUR'}),
            value_gap_to_target_reporting: available({amount: '0', currency: 'EUR'}),
            gap_to_target_pp: zeroInvestedUnavailable(),
        })),
        totals: {
            ...output.totals,
            current_invested_reporting: available({amount: '0', currency: 'EUR'}),
            max_abs_gap_pp: zeroInvestedUnavailable(),
            squared_gap_pp2: zeroInvestedUnavailable(),
        },
        normalized: {
            ...output.normalized,
            holdings: output.normalized.holdings.map((holding) => ({...holding, quantity: '0'})),
        },
    };
}

function openDecimalDistributionOutput(): RebalancerOutput {
    const output = readyOutput();
    return {
        ...output,
        instruments: output.instruments.map((instrument) => {
            if (instrument.instrument_key === 'asset:71') {
                return {...instrument, current_weight_percent: percent('33.333333333333')};
            }
            if (instrument.instrument_key === 'asset:72') {
                return {...instrument, current_weight_percent: percent('66.666666666666')};
            }
            return instrument;
        }),
    };
}

function success(output: RebalancerOutput): ToolItemResult<'portfolio_rebalancer', '1.0.0'> {
    return {
        accountGeneration,
        batch: {
            request_id: 'rebalancer-batch',
            success_count: 1,
            failed_count: 0,
            metrics: null,
        },
        contract_version: '1.0.0',
        correlation_id: 'rebalancer-correlation',
        execution_id: 'rebalancer-execution',
        implementation_version: '1.0.0',
        metrics: null,
        result: output,
        schema_fingerprint: 'f'.repeat(64),
        status: 'success',
        tool_code: 'portfolio_rebalancer',
    } as unknown as ToolItemResult<'portfolio_rebalancer', '1.0.0'>;
}

function renderTool() {
    return render(PortfolioRebalancerTool, {descriptor, accountGeneration});
}

async function waitForSource(): Promise<void> {
    await waitFor(() => expect(screen.getByTestId('pac-owned-asset-71')).toBeEnabled());
}

async function selectBothAssets(): Promise<void> {
    await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
    await fireEvent.click(screen.getByTestId('pac-owned-asset-72'));
    await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(3));
}

function holdingByBroker(brokerName: string): HTMLElement {
    const matches = screen.getAllByTestId('rebalancer-holding').filter((row) => within(row).queryByText(brokerName) !== null);
    expect(matches, `holding for ${brokerName}`).toHaveLength(1);
    const match = matches.pop();
    if (!match) throw new Error(`holding for ${brokerName} was not found`);
    return match;
}

function manualHolding(): HTMLElement {
    const matches = screen.getAllByTestId('rebalancer-holding').filter((row) => within(row).queryByTestId(/^rebalancer-holding-name-\d+$/) !== null);
    expect(matches, 'manual holding row').toHaveLength(1);
    const match = matches.pop();
    if (!match) throw new Error('manual holding row was not found');
    return match;
}

async function runAndReadInput(output = readyOutput()): Promise<ToolInput<'portfolio_rebalancer', '1.0.0'>> {
    runToolMock.mockResolvedValueOnce(success(output));
    await fireEvent.click(screen.getByTestId('rebalancer-analyze'));
    await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'false'));
    const call = runToolMock.mock.calls[0];
    if (!call) throw new Error('Rebalancer runTool call was not captured');
    return call[2].parameters;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    transitionClientSession(`rebalancer-round4-component-${++accountSequence}`);
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

describe('PortfolioRebalancerTool — Round 4 P1', () => {
    it('closes the final decimal target exactly to one hundred', () => {
        expect(closePercentDistribution(['33.333333333333', '66.666666666666'])).toEqual(['33.333333333333', '66.666666666667']);
    });

    it('keeps a detached baseline for a newly-created manual holding', () => {
        const holding = createManualRebalanceHolding(0);

        expect(holding.importedValue).toEqual(holding.value);
        expect(holding.importedValue).not.toBe(holding.value);
    });

    it('keeps manual holdings usable while the source request is pending', async () => {
        const pending = deferred<PacAllocationSource>();
        let requestedDate = '';
        fetchSourceMock.mockImplementationOnce((asOfDate: string) => {
            requestedDate = asOfDate;
            return pending.promise;
        });

        renderTool();
        await waitFor(() => expect(screen.getByTestId('pac-owned-assets-loading')).toBeInTheDocument());
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();

        await fireEvent.click(addManual);
        const name = screen.getByTestId('rebalancer-holding-name-0');
        const quantity = screen.getByTestId('rebalancer-quantity-0');
        expect(name).toBeEnabled();
        expect(quantity).toBeEnabled();
        await fireEvent.input(name, {target: {value: 'Pending source manual holding'}});
        await fireEvent.input(quantity, {target: {value: '3.5'}});
        expect(name).toHaveValue('Pending source manual holding');
        expect(quantity).toHaveValue('3.5');

        pending.resolve(allocationSource(requestedDate));
        await waitForSource();
        expect(name).toHaveValue('Pending source manual holding');
        expect(quantity).toHaveValue('3.5');
    });

    it('keeps manual holdings usable when the source request is unavailable', async () => {
        fetchSourceMock.mockRejectedValueOnce(new Error('fixture source unavailable'));

        renderTool();
        await waitFor(() => expect(screen.getByTestId('pac-owned-assets-error')).toBeInTheDocument());
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();

        await fireEvent.click(addManual);
        const name = screen.getByTestId('rebalancer-holding-name-0');
        const quantity = screen.getByTestId('rebalancer-quantity-0');
        expect(name).toBeEnabled();
        expect(quantity).toBeEnabled();
        await fireEvent.input(name, {target: {value: 'Unavailable source manual holding'}});
        await fireEvent.input(quantity, {target: {value: '4.25'}});
        expect(name).toHaveValue('Unavailable source manual holding');
        expect(quantity).toHaveValue('4.25');
    });

    it('keeps imported custody facts read-only while manual holdings expose quantity and quote editors', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2));

        for (const brokerName of ['Fixture broker A', 'Fixture broker B']) {
            const importedRow = holdingByBroker(brokerName);
            const rowIndex = importedRow.getAttribute('data-index');
            if (rowIndex === null) throw new Error(`imported holding for ${brokerName} has no data-index`);
            const imported = within(importedRow);
            expect(imported.queryByTestId(/^rebalancer-holding-name-\d+$/)).toBeNull();
            expect(imported.queryByTestId(/^rebalancer-quantity-\d+$/)).toBeNull();
            expect(imported.queryByTestId(/^rebalancer-currency-\d+-trigger$/)).toBeNull();
            expect(imported.queryByTestId(/^rebalancer-price-\d+$/)).toBeNull();
            expect(imported.queryByTestId(/^rebalancer-quote-basis-\d+$/)).toBeNull();
            expect(imported.queryByTestId(/^rebalancer-price-date-\d+$/)).toBeNull();
            const copiedFacts = imported.getByTestId(`rebalancer-holding-facts-${rowIndex}`);
            expect(copiedFacts).not.toHaveAttribute('open');
            expect(imported.getByTestId(`rebalancer-current-price-${rowIndex}`)).not.toBeVisible();
        }

        const importedGridStep = within(holdingByBroker('Fixture broker A')).getByTestId(/^rebalancer-quantity-step-\d+$/);
        expect(importedGridStep).toBeEnabled();
        await fireEvent.input(importedGridStep, {target: {value: '2'}});
        expect(importedGridStep).toHaveValue('2');

        const importedTarget = await screen.findByTestId('allocation-target-asset:71');
        expect(importedTarget).toBeEnabled();
        await fireEvent.input(importedTarget, {target: {value: '100'}});
        expect(importedTarget).toHaveValue('100');

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(3));
        const manual = within(manualHolding());
        expect(manual.getByTestId(/^rebalancer-holding-name-\d+$/)).toBeEnabled();
        expect(manual.getByTestId(/^rebalancer-quantity-\d+$/)).toBeEnabled();
        expect(manual.getByTestId(/^rebalancer-currency-\d+-trigger$/)).toBeEnabled();
        expect(manual.getByTestId(/^rebalancer-price-\d+$/)).toBeEnabled();
        expect(manual.getByTestId(/^rebalancer-quote-basis-\d+$/)).toBeEnabled();
        expect(manual.getByTestId(/^rebalancer-price-date-\d+$/)).toBeEnabled();
    });

    it('duplicates copied custody facts into a detached editable holding', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2));

        const imported = holdingByBroker('Fixture broker A');
        const importedIndex = imported.getAttribute('data-index');
        if (importedIndex === null) throw new Error('fixture imported holding has no data-index');
        const importedView = within(imported);
        const copiedFacts = importedView.getByTestId(`rebalancer-holding-facts-${importedIndex}`);
        expect(copiedFacts).not.toHaveAttribute('open');
        expect(importedView.getByTestId(`rebalancer-current-price-${importedIndex}`)).not.toBeVisible();

        await fireEvent.click(importedView.getByTestId(`rebalancer-duplicate-${importedIndex}`));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(3));

        const duplicate = manualHolding();
        const duplicateIndex = duplicate.getAttribute('data-index');
        if (duplicateIndex === null) throw new Error('fixture duplicated holding has no data-index');
        const editable = within(duplicate);
        expect(duplicate).toHaveAttribute('data-stale', 'false');
        expect(editable.queryByTestId(`rebalancer-holding-facts-${duplicateIndex}`)).toBeNull();
        expect(editable.getByTestId(`rebalancer-holding-name-${duplicateIndex}`)).toHaveValue('Fixture aggregate ETF');
        expect(editable.getByTestId(`rebalancer-quantity-${duplicateIndex}`)).toHaveValue('2');
        expect(editable.getByTestId(`rebalancer-price-${duplicateIndex}`)).toHaveValue('10');
        expect(editable.getByTestId(`rebalancer-quote-basis-${duplicateIndex}`)).toHaveValue('1');
        expect(editable.getByTestId(`rebalancer-price-date-${duplicateIndex}`)).toHaveValue('2026-09-13');
        expect(editable.getByTestId(`rebalancer-quantity-step-${duplicateIndex}`)).toHaveValue('1');

        await fireEvent.input(screen.getByTestId('allocation-target-asset:71'), {target: {value: '100'}});
        const input = await runAndReadInput();
        expect(() => structuredClone(input)).not.toThrow();
        const duplicatedInputs = input.holdings?.filter((holding) => holding.row_key.startsWith('manual:holding:')) ?? [];
        expect(duplicatedInputs).toHaveLength(1);
        const duplicatedInput = duplicatedInputs.pop();
        if (duplicatedInput === undefined) throw new Error('duplicated holding did not reach runTool');
        expect(duplicatedInput).toMatchObject({
            instrument_key: 'asset:71',
            name: 'Fixture aggregate ETF',
            quantity: '2',
            quote: {
                raw_price: '10',
                currency: 'EUR',
                quote_base_quantity: 1,
                reference_date: '2026-09-13',
            },
            buy_grid: {mode: 'whole', quantity_step: '1'},
        });
    });

    it('constrains a manual quote basis to twelve integer digits without exponent or letters', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));

        const manual = within(manualHolding());
        const basis = manual.getByTestId(/^rebalancer-quote-basis-\d+$/);
        expect(basis).toBeEnabled();
        expect(basis).toHaveAttribute('inputmode', 'decimal');

        await fireEvent.input(basis, {target: {value: '1e3'}});
        expect(basis).toHaveValue('13');

        await fireEvent.input(basis, {target: {value: 'abc'}});
        expect(basis).toHaveValue('');

        await fireEvent.input(basis, {target: {value: '1.5'}});
        expect(basis).toHaveValue('1.5');
        expect(basis).toHaveAttribute('aria-invalid', 'true');

        await fireEvent.input(basis, {target: {value: '999999999999'}});
        expect(basis).toHaveValue('999999999999');
        expect(basis).toHaveAttribute('aria-invalid', 'false');

        await fireEvent.input(basis, {target: {value: '1000000000000'}});
        expect(basis).toHaveValue('1000000000000');
        expect(basis).toHaveAttribute('aria-invalid', 'true');
        await fireEvent.blur(basis);
        expect(basis).toHaveValue('1000000000000');
        expect(basis).toHaveAttribute('aria-invalid', 'true');
    });

    it('removes a fresh manual holding immediately without opening confirmation', async () => {
        renderTool();
        await waitForSource();

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        const name = await screen.findByTestId('rebalancer-holding-name-0');
        expect(name).toBeEnabled();
        const row = manualHolding();
        expect(row).toBeInTheDocument();
        expect(within(row).getByTestId('rebalancer-holding-name-0')).toBeInTheDocument();
        const target = await screen.findByTestId(/^allocation-target-manual:asset:/);
        expect(target).toHaveValue('');

        await fireEvent.click(within(row).getByTestId('rebalancer-remove-0'));

        await waitFor(() => expect(row).not.toBeInTheDocument());
        expect(target).not.toBeInTheDocument();
        expect(screen.queryByTestId('rebalancer-customized-removal-confirm')).toBeNull();
        expect(screen.queryByTestId('rebalancer-holding-name-0')).toBeNull();
    });

    it('warns before removing an edited manual holding', async () => {
        renderTool();
        await waitForSource();

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        const name = await screen.findByTestId('rebalancer-holding-name-0');
        expect(name).toBeEnabled();
        const row = manualHolding();
        const target = await screen.findByTestId(/^allocation-target-manual:asset:/);
        expect(target).toHaveValue('');

        await fireEvent.input(name, {target: {value: 'Fixture edited manual Rebalancer holding'}});
        expect(name).toHaveValue('Fixture edited manual Rebalancer holding');
        await fireEvent.click(within(row).getByTestId('rebalancer-remove-0'));

        expect(screen.getByTestId('rebalancer-customized-removal-confirm')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('rebalancer-customized-removal-confirm')).toBeNull());
        expect(row).toBeInTheDocument();
        expect(name).toHaveValue('Fixture edited manual Rebalancer holding');

        await fireEvent.click(within(row).getByTestId('rebalancer-remove-0'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(row).not.toBeInTheDocument());
    });

    it('disables manual holding creation during compute and at the row cap', async () => {
        const contexts = Array.from({length: 32}, (_, index) =>
            sourceContext({
                contextKey: `asset:71:broker:${1_000 + index}`,
                brokerId: 1_000 + index,
                brokerName: `Fixture cap broker ${index + 1}`,
                custodyQuantity: String(index + 1),
            }),
        );
        fetchSourceMock.mockImplementationOnce(async (asOfDate: string) => allocationSource(asOfDate, {assets: [assetA({contexts})]}));

        renderTool();
        await waitForSource();
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();

        const pending = deferred<ToolItemResult<'portfolio_rebalancer', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => pending.promise);
        await fireEvent.click(screen.getByTestId('rebalancer-analyze'));
        await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'true'));
        expect(addManual).toBeDisabled();

        pending.resolve(success(readyOutput()));
        await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'false'));
        expect(addManual).toBeEnabled();

        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(32));
        expect(addManual).toBeDisabled();
    });

    it('permits exactly 32 contribution rows and prevents a 33rd', async () => {
        renderTool();
        await waitForSource();

        const tool = screen.getByTestId('portfolio-rebalancer-tool');
        await waitFor(() => expect(tool).toHaveAttribute('data-busy', 'false'));
        const funding = within(tool).getByTestId('rebalancer-funding-context');
        const contributionEditor = within(funding).getByTestId('pac-contributions');
        const editor = within(contributionEditor);
        const contributionRows = () => editor.queryAllByTestId('pac-contributions-row');
        const addContributionRow = () => editor.getByTestId('pac-add-contributions');

        expect(editor.getByTestId('pac-contributions-empty')).toBeInTheDocument();
        expect(addContributionRow()).toBeEnabled();
        expect(contributionRows()).toHaveLength(0);

        for (let expectedRows = 1; expectedRows <= P1_MAX_ROWS; expectedRows += 1) {
            expect(addContributionRow()).toBeEnabled();
            await fireEvent.click(addContributionRow());
            await waitFor(() => expect(contributionRows()).toHaveLength(expectedRows));
        }

        const cappedAdd = addContributionRow();
        expect(contributionRows()).toHaveLength(P1_MAX_ROWS);
        expect(cappedAdd).toBeDisabled();

        await fireEvent.click(cappedAdd);
        expect(contributionRows()).toHaveLength(P1_MAX_ROWS);
    });

    it('preserves customized buy grids and appends new custody contexts on refresh', async () => {
        let responseIndex = 0;
        fetchSourceMock.mockImplementation(async (asOfDate: string) => {
            responseIndex += 1;
            if (responseIndex === 1) {
                return allocationSource(asOfDate, {assets: [assetA()]});
            }
            if (responseIndex === 2) {
                return allocationSource(asOfDate, {
                    assets: [assetA()],
                    selectedCashBalances: [{currency: 'EUR', amount: '250'}],
                });
            }
            return allocationSource(asOfDate, {
                assets: [
                    assetA({
                        quote: {rawPrice: '12'},
                        contexts: [
                            sourceContext({custodyQuantity: '20'}),
                            sourceContext({
                                contextKey: 'asset:71:broker:12',
                                brokerId: 12,
                                brokerName: 'Fixture broker B',
                                custodyQuantity: '3',
                            }),
                            sourceContext({
                                contextKey: 'asset:71:broker:13',
                                brokerId: 13,
                                brokerName: 'Fixture broker C',
                                custodyQuantity: '5',
                            }),
                        ],
                    }),
                ],
            });
        });

        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2));

        const originalPrimary = holdingByBroker('Fixture broker A');
        const primaryStep = within(originalPrimary).getByTestId(/^rebalancer-quantity-step-\d+$/);
        expect(originalPrimary).toHaveAttribute('data-stale', 'false');
        await fireEvent.input(primaryStep, {target: {value: '2'}});
        expect(primaryStep).toHaveValue('2');

        const refresh = screen.getByTestId('pac-owned-assets-refresh');
        await fireEvent.click(refresh);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(refresh).toBeEnabled());
        expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2);
        const cashOnlyPrimary = holdingByBroker('Fixture broker A');
        expect(within(cashOnlyPrimary).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('2');
        expect(cashOnlyPrimary).toHaveAttribute('data-stale', 'false');

        await fireEvent.click(refresh);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(3));
        await waitFor(() => expect(refresh).toBeEnabled());

        const protectedPrimary = holdingByBroker('Fixture broker A');
        expect(within(protectedPrimary).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('2');
        expect(protectedPrimary).toHaveAttribute('data-stale', 'true');
        const replacedSecondary = holdingByBroker('Fixture broker B');
        expect(within(replacedSecondary).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('1');
        expect(replacedSecondary).toHaveAttribute('data-stale', 'false');

        const appended = holdingByBroker('Fixture broker C');
        expect(within(appended).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('1');
        expect(appended).toHaveAttribute('data-stale', 'false');
    });

    it('serializes every proxy-backed custody context under canonical targets and renders aggregated gaps', async () => {
        renderTool();
        await waitForSource();
        await selectBothAssets();

        await fireEvent.input(await screen.findByTestId('allocation-target-asset:71'), {target: {value: '40.000000000001'}});
        await fireEvent.input(await screen.findByTestId('allocation-target-asset:72'), {target: {value: '59.999999999999'}});

        const input = await runAndReadInput();
        expect(() => structuredClone(input)).not.toThrow();
        const holdings = input.holdings;
        if (!holdings) throw new Error('Rebalancer input did not include custody holdings');

        expect(
            holdings.map((holding) => ({
                row_key: holding.row_key,
                instrument_key: holding.instrument_key,
                quantity: holding.quantity,
            })),
        ).toEqual([
            {row_key: 'asset:71:broker:11:0', instrument_key: 'asset:71', quantity: '2'},
            {row_key: 'asset:71:broker:12:1', instrument_key: 'asset:71', quantity: '3'},
            {row_key: 'asset:72:broker:11:0', instrument_key: 'asset:72', quantity: '4'},
        ]);
        expect(input.targets).toEqual([
            {instrument_key: 'asset:71', target_percent: '40.000000000001'},
            {instrument_key: 'asset:72', target_percent: '59.999999999999'},
        ]);
        expect(input).not.toHaveProperty('mode');
        expect(input).not.toHaveProperty('orders');
        expect(input).not.toHaveProperty('solver');
        expect(input).not.toHaveProperty('draft_revision');

        const panel = screen.getByTestId('rebalancer-result-panel');
        expect(within(panel).getByTestId('allocation-diagnostics')).toBeInTheDocument();
        expect(within(panel).getByTestId('dt-header-contexts')).toBeInTheDocument();
        expect(within(panel).getByTestId('dt-header-gap')).toBeInTheDocument();
        expect(within(panel).getByText('Backend aggregate A')).toBeInTheDocument();
        const aggregateRow = panel.querySelector('[data-row-id="asset:71"]');
        expect(aggregateRow).not.toBeNull();
        expect(within(aggregateRow as HTMLElement).getByText('2')).toBeInTheDocument();
    });

    it('keys Broker cash by account, date, and sorted selection without reusing stale balances', async () => {
        const firstCashSource: PacAllocationSource['cashSources'][number] = {
            brokerId: 11,
            brokerName: 'Fixture owner broker A',
            brokerIconUrl: null,
            brokerPortalUrl: null,
            brokerDefaultImportPlugin: null,
            ownershipSharePercent: '100',
            balances: [{currency: 'EUR', amount: '110'}],
        };
        const secondCashSource: PacAllocationSource['cashSources'][number] = {
            ...firstCashSource,
            brokerId: 29,
            brokerName: 'Fixture owner broker B',
            balances: [{currency: 'USD', amount: '290'}],
        };
        const cashSources: PacAllocationSource['cashSources'] = [secondCashSource, firstCashSource];
        const cachedCash: PacAllocationSource['selectedCashBalances'] = [{currency: 'EUR', amount: '654.321987'}];
        const pendingFullSelection = deferred<PacAllocationSource>();
        let deferFullSelection = true;
        let rejectReplacement = false;
        fetchSourceMock.mockImplementation(async (asOfDate: string, _generation: number, options?: FetchPacAllocationSourceOptions) => {
            const brokerIds = options?.selectedCashBrokerIds ?? [];
            if (rejectReplacement) throw new Error('fixture Broker cash replacement unavailable');
            if (deferFullSelection && brokerIds.length === 2) return pendingFullSelection.promise;
            return allocationSource(asOfDate, {
                cashSources,
                selectedCashBalances: brokerIds.length > 0 ? cachedCash : [],
            });
        });

        const view = renderTool();
        await waitForSource();
        const initialDate = (screen.getByTestId('rebalancer-analysis-date') as HTMLInputElement).value;
        expect(initialDate).not.toBe('');
        expect(fetchSourceMock).toHaveBeenNthCalledWith(1, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: []}));

        await fireEvent.click(screen.getByTestId('pac-cash-broker-29'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(2, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [29]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-broker-29')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('pac-cash-broker-11'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(3, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [11, 29]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-source-pending')).toBeInTheDocument());
        expect(screen.queryByTestId('pac-cash-source-error')).toBeNull();
        expect(screen.getByTestId('rebalancer-analyze')).toBeDisabled();

        deferFullSelection = false;
        pendingFullSelection.resolve(
            allocationSource(initialDate, {
                cashSources,
                selectedCashBalances: cachedCash,
            }),
        );
        await waitFor(() => expect(screen.queryByTestId('pac-cash-source-pending')).toBeNull());
        expect(screen.queryByTestId('pac-cash-source-error')).toBeNull();
        expect(screen.getByTestId('rebalancer-analyze')).toBeEnabled();

        const acceptedInput = await runAndReadInput();
        expect(acceptedInput.cash_balances).toEqual(cachedCash);
        runToolMock.mockReset();

        transitionClientSession(`rebalancer-round4-cash-account-${++accountSequence}`);
        accountGeneration = getClientSessionGeneration();
        descriptor = makeDescriptor();
        await view.rerender({descriptor, accountGeneration});
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(4));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(4, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [11, 29]}));
        await waitFor(() => expect(screen.getByTestId('rebalancer-analyze')).toBeEnabled());

        const replacementDate = '2024-01-15';
        const dateInput = screen.getByTestId('rebalancer-analysis-date');
        await fireEvent.input(dateInput, {target: {value: replacementDate}});
        await fireEvent.blur(dateInput);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(5));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(5, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [11, 29]}));
        await waitFor(() => expect(screen.getByTestId('rebalancer-analyze')).toBeEnabled());

        rejectReplacement = true;
        await fireEvent.click(screen.getByTestId('pac-cash-broker-29'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(6));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(6, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [11]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-source-error')).toBeInTheDocument());
        const analyze = screen.getByTestId('rebalancer-analyze');
        expect(analyze).toBeDisabled();
        await fireEvent.click(analyze);
        expect(runToolMock).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('pac-cash-broker-11'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(7));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(7, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: []}));
        await waitFor(() => expect(analyze).toBeEnabled());

        const emptySelectionInput = await runAndReadInput();
        expect(emptySelectionInput.cash_balances).toEqual([]);
        expect(emptySelectionInput.cash_balances).not.toEqual(cachedCash);
    });

    it('explains a ready result with zero invested value and unavailable ratios', async () => {
        renderTool();
        await waitForSource();
        await selectBothAssets();

        await runAndReadInput(zeroInvestedReadyOutput());

        const panel = within(screen.getByTestId('rebalancer-result-panel'));
        expect(panel.getByTestId('allocation-diagnostics')).toBeInTheDocument();
        expect(panel.getByTestId('dt-header-currentWeight')).toBeInTheDocument();
        expect(panel.getByTestId('dt-header-gap')).toBeInTheDocument();
        expect(panel.getByTestId('rebalancer-zero-invested')).toBeInTheDocument();
        expect(screen.queryByTestId('rebalancer-copy-current-distribution')).toBeNull();
    });

    it('copies backend current weights and closes the last decimal target exactly to one hundred', async () => {
        renderTool();
        await waitForSource();
        await selectBothAssets();
        await fireEvent.input(await screen.findByTestId('allocation-target-asset:71'), {target: {value: '40'}});
        await fireEvent.input(await screen.findByTestId('allocation-target-asset:72'), {target: {value: '60'}});

        await runAndReadInput(openDecimalDistributionOutput());
        await fireEvent.click(screen.getByTestId('rebalancer-copy-current-distribution'));

        expect(screen.getByTestId('allocation-target-asset:71')).toHaveValue('33.333333333333');
        expect(screen.getByTestId('allocation-target-asset:72')).toHaveValue('66.666666666667');
    });

    it('warns before removing an imported holding with a customized buy grid and exposes no unsupported controls', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2));

        expect(screen.queryByTestId('rebalancer-draft-revision')).toBeNull();
        expect(screen.queryByTestId('rebalancer-mode-selector')).toBeNull();
        expect(screen.queryByTestId('rebalancer-orders')).toBeNull();
        expect(screen.queryByTestId('rebalancer-solver')).toBeNull();

        const primary = holdingByBroker('Fixture broker A');
        const gridStep = within(primary).getByTestId(/^rebalancer-quantity-step-\d+$/);
        const target = await screen.findByTestId('allocation-target-asset:71');
        expect(target).toHaveValue('');
        await fireEvent.input(gridStep, {target: {value: '2'}});
        expect(gridStep).toHaveValue('2');
        await fireEvent.click(within(primary).getByTestId(/^rebalancer-remove-\d+$/));

        expect(screen.getByTestId('rebalancer-customized-removal-confirm')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('rebalancer-customized-removal-confirm')).toBeNull());
        expect(primary).toBeInTheDocument();
        expect(within(holdingByBroker('Fixture broker A')).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('2');
    });

    it("warns before removing an unedited holding that owns its instrument's last target", async () => {
        renderTool();
        await waitForSource();
        const assetCard = () => screen.getByTestId('pac-owned-asset-72');
        await fireEvent.click(assetCard());
        const row = await waitFor(() => holdingByBroker('Fixture broker Second'));

        expect(within(row).getByTestId(/^rebalancer-quantity-step-\d+$/)).toHaveValue('1');
        const target = await screen.findByTestId('allocation-target-asset:72');
        await fireEvent.input(target, {target: {value: '100'}});
        expect(target).toHaveValue('100');

        await fireEvent.click(within(row).getByTestId(/^rebalancer-remove-\d+$/));

        expect(screen.getByTestId('rebalancer-customized-removal-confirm')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('rebalancer-customized-removal-confirm')).toBeNull());
        expect(row).toBeInTheDocument();
        expect(target).toHaveValue('100');

        await fireEvent.click(within(row).getByTestId(/^rebalancer-remove-\d+$/));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(row).not.toBeInTheDocument());
        expect(assetCard()).toHaveAttribute('aria-pressed', 'false');
        expect(screen.queryByTestId('allocation-target-asset:72')).toBeNull();
    });

    it('ignores a compute response superseded by a holding edit', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-71'));
        await waitFor(() => expect(screen.getAllByTestId('rebalancer-holding')).toHaveLength(2));

        runToolMock.mockResolvedValueOnce(success(readyOutput('Stable aggregate A', 'Stable aggregate B')));
        await fireEvent.click(screen.getByTestId('rebalancer-analyze'));
        await waitFor(() => expect(within(screen.getByTestId('rebalancer-result-panel')).getByText('Stable aggregate A')).toBeInTheDocument());

        const late = deferred<ToolItemResult<'portfolio_rebalancer', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => late.promise);
        await fireEvent.click(screen.getByTestId('rebalancer-analyze'));
        await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'true'));

        await fireEvent.input(screen.getByTestId('rebalancer-quantity-step-0'), {target: {value: '2'}});
        expect(screen.getByTestId('rebalancer-quantity-step-0')).toHaveValue('2');
        late.resolve(success(readyOutput('Late aggregate A', 'Late aggregate B')));

        await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'false'));
        const panel = within(screen.getByTestId('rebalancer-result-panel'));
        expect(panel.getByText('Stable aggregate A')).toBeInTheDocument();
        expect(panel.queryByText('Late aggregate A')).toBeNull();
        expect(panel.getByTestId('rebalancer-result-stale')).toBeInTheDocument();
    });

    it('ignores an in-flight response after the authenticated account changes', async () => {
        renderTool();
        await waitForSource();
        const pending = deferred<ToolItemResult<'portfolio_rebalancer', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => pending.promise);

        await fireEvent.click(screen.getByTestId('rebalancer-analyze'));
        await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));
        transitionClientSession(`rebalancer-round4-other-account-${++accountSequence}`);
        pending.resolve(success(readyOutput('Wrong-account A', 'Wrong-account B')));

        await waitFor(() => expect(screen.getByTestId('portfolio-rebalancer-tool')).toHaveAttribute('data-busy', 'false'));
        expect(screen.queryByTestId('allocation-diagnostics')).toBeNull();
        expect(screen.queryByTestId('rebalancer-client-error')).toBeNull();
        expect(screen.queryByTestId('rebalancer-platform-error')).toBeNull();
    });
});
