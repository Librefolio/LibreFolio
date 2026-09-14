// @vitest-environment jsdom
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {waitLocale} from 'svelte-i18n';
import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {locale} from '$lib/i18n';
import {getClientSessionGeneration, transitionClientSession} from '$lib/stores/app/clientSession';
import {userSettings} from '$lib/stores/app/settings';
import type {FxDataPoint} from '$lib/stores/fxStoreRegistry';
import {getCompiledToolContract, validateToolCatalog, verifyToolDescriptor, type CompatibleToolDescriptor, type ToolInput, type ToolOutput} from '$lib/features/tools/contracts';
import type {ToolItemResult, ToolRunOptions} from '$lib/features/tools/client';
import type {FetchPacAllocationSourceOptions, PacAllocationSource, PacAllocationSourceAsset, PacAllocationSourceContext} from './allocationSource';
import {createManualPacAsset} from './draftFactories';
import PacAllocatorTool from './PacAllocatorTool.svelte';

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

type PacDescriptor = CompatibleToolDescriptor<'pac_allocator', '1.0.0'>;
type PacOutput = ToolOutput<'pac_allocator', '1.0.0'>;

const P1_MAX_ROWS = 32;

let accountGeneration = 0;
let descriptor: PacDescriptor;
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

function makeDescriptor(): PacDescriptor {
    const contract = getCompiledToolContract('pac_allocator', '1.0.0');
    if (!contract) throw new Error('pac_allocator/1.0.0 generated contract is required');
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
                    description: 'PAC allocator fixture',
                    description_i18n_key: null,
                    documentation: {path: 'tools/pac-allocator', version: '1.0.0'},
                    icon_key: 'calculator',
                    input_schema: {},
                    name: 'PAC allocator fixture',
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
    return verifyToolDescriptor(catalog, 'pac_allocator', '1.0.0');
}

function sourceAsset(
    overrides: Omit<Partial<PacAllocationSourceAsset>, 'quote'> & {
        quote?: Partial<PacAllocationSourceAsset['quote']>;
    } = {},
): PacAllocationSourceAsset {
    const base: PacAllocationSourceAsset = {
        assetId: 17,
        instrumentKey: 'asset:17',
        candidateKey: 'candidate:17',
        name: 'Fixture PAC ETF',
        ticker: 'PAC17',
        assetType: 'ETF',
        iconUrl: null,
        active: true,
        usageScope: 'owned',
        quote: {
            rawPrice: '123.450000000001',
            currency: 'USD',
            quoteBaseQuantity: 100,
            referenceDate: '2026-09-13',
            source: 'fixture',
            daysBeforeRequested: 1,
        },
        contexts: [],
    };
    return {
        ...base,
        ...overrides,
        quote: {...base.quote, ...overrides.quote},
        contexts: overrides.contexts ?? base.contexts,
    };
}

function sourceContext(overrides: Partial<PacAllocationSourceContext> = {}): PacAllocationSourceContext {
    return {
        contextKey: 'asset:17:broker:31',
        brokerId: 31,
        brokerName: 'Fixture PAC custody',
        brokerIconUrl: null,
        brokerPortalUrl: null,
        brokerDefaultImportPlugin: null,
        ownershipSharePercent: '100',
        custodyQuantity: '7',
        ...overrides,
    };
}

const CASH_SOURCE: PacAllocationSource['cashSources'][number] = {
    brokerId: 31,
    brokerName: 'Fixture owner broker',
    brokerIconUrl: null,
    brokerPortalUrl: null,
    brokerDefaultImportPlugin: null,
    ownershipSharePercent: '100',
    balances: [{currency: 'EUR', amount: '100.000000000000'}],
};

const CASH_SOURCES: PacAllocationSource['cashSources'] = [CASH_SOURCE];

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
        assets: options.assets ?? [sourceAsset()],
        cashSources: options.cashSources ?? [],
        selectedCashBalances: options.selectedCashBalances ?? [],
    };
}

function available<T>(value: T): {availability: 'available'; value: T; reason_codes: []} {
    return {availability: 'available', value, reason_codes: []};
}

function readyOutput(name = 'Backend PAC allocation', budget = '100.300000000003'): PacOutput {
    return {
        operation: 'analyze',
        result_kind: 'pac_budget_analysis',
        numeric_policy_id: 'pac-budget-allocation-v1',
        availability: 'ready',
        allocations: [
            {
                target_index: 0,
                instrument_key: 'asset:17',
                name,
                target_percent: available('100'),
                ideal_allocation_reporting: available({amount: budget, currency: 'EUR'}),
            },
        ],
        cash_pools: available([]),
        totals: {
            existing_cash_reporting: available({amount: '100', currency: 'EUR'}),
            contributions_reporting: available({amount: '0.300000000003', currency: 'EUR'}),
            investable_budget_reporting: available({amount: budget, currency: 'EUR'}),
            target_total_percent: available('100'),
        },
        normalized: {
            report_currency: 'EUR',
            as_of_date: null,
            assets: [{instrument_key: 'asset:17', name: 'Fixture PAC ETF', buy_grid: {mode: 'whole', quantity_step: '1'}}],
            targets: [{instrument_key: 'asset:17', target_percent: '100'}],
            cash_balances: [{currency: 'EUR', amount: '100'}],
            contributions: [
                {currency: 'EUR', amount: '0.100000000001', monetary_step: '0.000000000001'},
                {currency: 'EUR', amount: '0.200000000002', monetary_step: '0.000000000001'},
            ],
            valuation_rates: [],
        },
        issues: [],
    } as unknown as PacOutput;
}

function success(output: PacOutput): ToolItemResult<'pac_allocator', '1.0.0'> {
    return {
        accountGeneration,
        batch: {
            request_id: 'pac-batch',
            success_count: 1,
            failed_count: 0,
            metrics: null,
        },
        contract_version: '1.0.0',
        correlation_id: 'pac-correlation',
        execution_id: 'pac-execution',
        implementation_version: '1.0.0',
        metrics: null,
        result: output,
        schema_fingerprint: 'f'.repeat(64),
        status: 'success',
        tool_code: 'pac_allocator',
    } as unknown as ToolItemResult<'pac_allocator', '1.0.0'>;
}

function renderTool() {
    return render(PacAllocatorTool, {descriptor, accountGeneration});
}

async function waitForSource(): Promise<void> {
    await waitFor(() => expect(screen.getByTestId('pac-owned-asset-17')).toBeEnabled());
}

async function useManualCash(): Promise<void> {
    await fireEvent.click(screen.getByTestId('pac-cash-use-manual'));
    await waitFor(() => expect(screen.getByTestId('pac-cash-amount-0')).toBeInTheDocument());
}

async function addContribution(): Promise<void> {
    const count = screen.queryAllByTestId('pac-contributions-row').length;
    await fireEvent.click(screen.getByTestId('pac-add-contributions'));
    await waitFor(() => expect(screen.getAllByTestId('pac-contributions-row')).toHaveLength(count + 1));
}

async function runAndReadInput(output = readyOutput()): Promise<ToolInput<'pac_allocator', '1.0.0'>> {
    runToolMock.mockResolvedValueOnce(success(output));
    await fireEvent.click(screen.getByTestId('pac-analyze'));
    await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
    const call = runToolMock.mock.calls[0];
    if (!call) throw new Error('PAC runTool call was not captured');
    return call[2].parameters;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    transitionClientSession(`pac-round4-component-${++accountSequence}`);
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

describe('PacAllocatorTool — Round 4 P1', () => {
    it('keeps a detached baseline for a newly-created manual Asset', () => {
        const asset = createManualPacAsset(0);

        expect(asset.importedValue).toEqual(asset.value);
        expect(asset.importedValue).not.toBe(asset.value);
    });

    it('searches source Assets by name, ticker, type, and Broker', async () => {
        const alpha = sourceAsset({contexts: [sourceContext()]});
        const beta = sourceAsset({
            assetId: 18,
            instrumentKey: 'asset:18',
            candidateKey: 'candidate:18',
            name: 'Fixture Bond Candidate',
            ticker: 'BND18',
            assetType: 'BOND',
            contexts: [
                sourceContext({
                    contextKey: 'asset:18:broker:32',
                    brokerId: 32,
                    brokerName: 'Fixture Bond Custodian',
                }),
            ],
        });
        fetchSourceMock.mockImplementationOnce(async (asOfDate: string) => allocationSource(asOfDate, {assets: [alpha, beta]}));

        renderTool();
        await waitFor(() => expect(screen.getByTestId('pac-owned-asset-17')).toBeEnabled());
        const search = screen.getByTestId('pac-owned-assets-search');
        const alphaCard = () => screen.queryByTestId('pac-owned-asset-17');
        const betaCard = () => screen.queryByTestId('pac-owned-asset-18');

        for (const query of ['Fixture PAC ETF', 'PAC17', 'ETF', 'Fixture PAC custody']) {
            await fireEvent.input(search, {target: {value: query}});
            expect(alphaCard()).toBeInTheDocument();
            expect(betaCard()).toBeNull();
        }

        for (const query of ['Fixture Bond Candidate', 'BND18', 'BOND', 'Fixture Bond Custodian']) {
            await fireEvent.input(search, {target: {value: query}});
            expect(betaCard()).toBeInTheDocument();
            expect(alphaCard()).toBeNull();
        }

        await fireEvent.input(search, {target: {value: ''}});
        expect(alphaCard()).toBeInTheDocument();
        expect(betaCard()).toBeInTheDocument();
    });

    it('keeps manual Assets usable while the source request is pending', async () => {
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
        const name = screen.getByTestId('pac-asset-name-0');
        expect(name).toBeEnabled();
        await fireEvent.input(name, {target: {value: 'Pending source manual Asset'}});
        expect(name).toHaveValue('Pending source manual Asset');

        pending.resolve(allocationSource(requestedDate));
        await waitFor(() => expect(screen.getByTestId('pac-owned-asset-17')).toBeEnabled());
        expect(name).toHaveValue('Pending source manual Asset');
    });

    it('keeps manual Assets usable when the source request is unavailable', async () => {
        fetchSourceMock.mockRejectedValueOnce(new Error('fixture source unavailable'));

        renderTool();
        await waitFor(() => expect(screen.getByTestId('pac-owned-assets-error')).toBeInTheDocument());
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();

        await fireEvent.click(addManual);
        const name = screen.getByTestId('pac-asset-name-0');
        expect(name).toBeEnabled();
        await fireEvent.input(name, {target: {value: 'Unavailable source manual Asset'}});
        expect(name).toHaveValue('Unavailable source manual Asset');
    });

    it('disables manual Asset creation during compute and at the row cap', async () => {
        renderTool();
        await waitForSource();
        const addManual = screen.getByTestId('pac-add-manual-asset');
        expect(addManual).toBeEnabled();

        const pending = deferred<ToolItemResult<'pac_allocator', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => pending.promise);
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));
        expect(addManual).toBeDisabled();

        pending.resolve(success(readyOutput()));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
        expect(addManual).toBeEnabled();

        for (let count = 0; count < 32; count += 1) {
            await fireEvent.click(addManual);
        }
        expect(screen.getAllByTestId('pac-asset-editor')).toHaveLength(32);
        expect(addManual).toBeDisabled();
    });

    it('permits exactly 32 contribution rows and prevents a 33rd', async () => {
        renderTool();
        await waitForSource();

        const tool = screen.getByTestId('pac-allocator-tool');
        await waitFor(() => expect(tool).toHaveAttribute('data-busy', 'false'));
        const funding = within(tool).getByTestId('pac-funding');
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

    it('preserves a customized Asset across cash-only and changed-source refreshes', async () => {
        let responseIndex = 0;
        fetchSourceMock.mockImplementation(async (asOfDate: string) => {
            responseIndex += 1;
            if (responseIndex === 1) {
                return allocationSource(asOfDate, {
                    assets: [sourceAsset({quote: {rawPrice: '10'}})],
                    cashSources: CASH_SOURCES,
                });
            }
            if (responseIndex === 2) {
                return allocationSource(asOfDate, {
                    assets: [sourceAsset({quote: {rawPrice: '10'}})],
                    cashSources: [
                        {
                            ...CASH_SOURCE,
                            balances: [{currency: 'EUR', amount: '250.000000000000'}],
                        },
                    ],
                });
            }
            return allocationSource(asOfDate, {
                assets: [
                    sourceAsset({
                        name: 'Fixture PAC ETF refreshed',
                        quote: {rawPrice: '20.000000000001'},
                    }),
                ],
                cashSources: CASH_SOURCES,
            });
        });

        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-17'));
        expect(screen.getByTestId('pac-asset-editor')).toHaveAttribute('data-stale', 'false');
        const quantityStep = screen.getByTestId('pac-asset-quantity-step-0');
        await fireEvent.input(quantityStep, {target: {value: '2'}});
        expect(quantityStep).toHaveValue('2');

        const refresh = screen.getByTestId('pac-owned-assets-refresh');
        await fireEvent.click(refresh);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        await waitFor(() => expect(refresh).toBeEnabled());
        expect(quantityStep).toHaveValue('2');
        expect(screen.getByTestId('pac-owned-asset-17')).toHaveAttribute('aria-pressed', 'true');
        expect(screen.getByTestId('pac-current-price-0')).toHaveTextContent('10');
        expect(screen.getByTestId('pac-asset-editor')).toHaveAttribute('data-stale', 'false');

        await fireEvent.click(refresh);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        await waitFor(() => expect(refresh).toBeEnabled());
        expect(quantityStep).toHaveValue('2');
        expect(screen.getByTestId('pac-current-price-0')).toHaveTextContent('20.000000000001');
        expect(screen.getByTestId('pac-asset-editor')).toHaveAttribute('data-stale', 'true');
    });

    it('updates target decimal aria labels and DataTable headers when the locale changes', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-owned-asset-17'));
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));

        const targetPattern = /^allocation-target-(?:asset:|manual:asset:)/;
        const originalTargets = screen.getAllByTestId(targetPattern);
        expect(originalTargets).toHaveLength(2);
        const targetHeader = screen.getByTestId('dt-header-target');
        const originalHeader = targetHeader.textContent?.trim();
        expect(originalHeader).toBeTruthy();
        const originalLabels = new Map<string, string>();
        for (const target of originalTargets) {
            const testId = target.getAttribute('data-testid');
            const label = target.getAttribute('aria-label');
            expect(testId).not.toBeNull();
            expect(label).not.toBeNull();
            expect(label).not.toBe('');
            originalLabels.set(testId as string, label as string);
        }

        try {
            locale.set('it');
            await waitLocale('it');
            await waitFor(() => {
                const localizedTargets = screen.getAllByTestId(targetPattern);
                expect(localizedTargets).toHaveLength(2);
                for (const target of localizedTargets) {
                    const testId = target.getAttribute('data-testid');
                    const label = target.getAttribute('aria-label');
                    expect(label).not.toBeNull();
                    expect(label).not.toBe('');
                    expect(label).not.toBe(originalLabels.get(testId as string));
                }
                expect(screen.getByTestId('dt-header-target').textContent?.trim()).not.toBe(originalHeader);
            });
        } finally {
            locale.set('en');
            await waitLocale('en');
        }
    });

    it('serializes proxy-backed assets and exact targets separately and preserves repeated contribution currencies', async () => {
        renderTool();
        await waitForSource();

        await fireEvent.click(screen.getByTestId('pac-owned-asset-17'));
        const target = (await screen.findByTestId('allocation-target-asset:17')) as HTMLInputElement;
        await fireEvent.input(target, {target: {value: '100.000000000000'}});

        await useManualCash();
        await fireEvent.input(screen.getByTestId('pac-cash-amount-0'), {target: {value: '100.000000000000'}});

        await addContribution();
        await addContribution();
        await fireEvent.input(screen.getByTestId('pac-contributions-amount-0'), {target: {value: '0.100000000001'}});
        await fireEvent.input(screen.getByTestId('pac-contributions-monetary-step-0'), {target: {value: '0.000000000001'}});
        await fireEvent.input(screen.getByTestId('pac-contributions-amount-1'), {target: {value: '0.200000000002'}});
        await fireEvent.input(screen.getByTestId('pac-contributions-monetary-step-1'), {target: {value: '0.000000000001'}});

        const input = await runAndReadInput();
        expect(() => structuredClone(input)).not.toThrow();

        expect(input.assets).toEqual([
            {
                instrument_key: 'asset:17',
                name: 'Fixture PAC ETF',
                buy_grid: {mode: 'whole', quantity_step: '1'},
            },
        ]);
        expect(input.targets).toEqual([{instrument_key: 'asset:17', target_percent: '100.000000000000'}]);
        expect(input.cash_balances).toEqual([{currency: 'EUR', amount: '100.000000000000'}]);
        expect(input.contributions).toEqual([
            {currency: 'EUR', amount: '0.100000000001', monetary_step: '0.000000000001'},
            {currency: 'EUR', amount: '0.200000000002', monetary_step: '0.000000000001'},
        ]);
        expect(input).not.toHaveProperty('holdings');
        expect(input).not.toHaveProperty('mode');
        expect(input).not.toHaveProperty('orders');
        expect(input).not.toHaveProperty('solver');
        expect(input).not.toHaveProperty('draft_revision');

        const result = screen.getByTestId('pac-result-panel');
        expect(within(result).getByTestId('allocation-diagnostics')).toBeInTheDocument();
        expect(within(result).getByTestId('dt-header-target')).toBeInTheDocument();
        expect(within(result).getByTestId('dt-header-allocation')).toBeInTheDocument();
        expect(within(result).getByText('Backend PAC allocation')).toBeInTheDocument();
    });

    it('keeps Broker cash pending and invalidates stale keyed balances', async () => {
        const secondCashSource: PacAllocationSource['cashSources'][number] = {
            ...CASH_SOURCE,
            brokerId: 47,
            brokerName: 'Fixture second owner broker',
            balances: [{currency: 'USD', amount: '47'}],
        };
        const cashSources: PacAllocationSource['cashSources'] = [secondCashSource, CASH_SOURCE];
        const cachedCash: PacAllocationSource['selectedCashBalances'] = [{currency: 'EUR', amount: '987.654321'}];
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
        const initialDate = (screen.getByTestId('pac-analysis-date') as HTMLInputElement).value;
        expect(initialDate).not.toBe('');
        expect(fetchSourceMock).toHaveBeenNthCalledWith(1, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: []}));

        await fireEvent.click(screen.getByTestId('pac-cash-broker-47'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(2));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(2, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [47]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-broker-47')).toBeEnabled());

        await fireEvent.click(screen.getByTestId('pac-cash-broker-31'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(3));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(3, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [31, 47]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-source-pending')).toBeInTheDocument());
        expect(screen.queryByTestId('pac-cash-source-error')).toBeNull();
        expect(screen.getByTestId('pac-analyze')).toBeDisabled();

        deferFullSelection = false;
        pendingFullSelection.resolve(
            allocationSource(initialDate, {
                cashSources,
                selectedCashBalances: cachedCash,
            }),
        );
        await waitFor(() => expect(screen.queryByTestId('pac-cash-source-pending')).toBeNull());
        expect(screen.queryByTestId('pac-cash-source-error')).toBeNull();
        expect(screen.getByTestId('pac-analyze')).toBeEnabled();

        const acceptedInput = await runAndReadInput();
        expect(acceptedInput.cash_balances).toEqual(cachedCash);
        runToolMock.mockReset();

        transitionClientSession(`pac-round4-cash-account-${++accountSequence}`);
        accountGeneration = getClientSessionGeneration();
        descriptor = makeDescriptor();
        await view.rerender({descriptor, accountGeneration});
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(4));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(4, initialDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [31, 47]}));
        await waitFor(() => expect(screen.getByTestId('pac-analyze')).toBeEnabled());

        const replacementDate = '2024-01-15';
        const dateInput = screen.getByTestId('pac-analysis-date');
        await fireEvent.input(dateInput, {target: {value: replacementDate}});
        await fireEvent.blur(dateInput);
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(5));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(5, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [31, 47]}));
        await waitFor(() => expect(screen.getByTestId('pac-analyze')).toBeEnabled());

        rejectReplacement = true;
        await fireEvent.click(screen.getByTestId('pac-cash-broker-47'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(6));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(6, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: [31]}));
        await waitFor(() => expect(screen.getByTestId('pac-cash-source-error')).toBeInTheDocument());
        const analyze = screen.getByTestId('pac-analyze');
        expect(analyze).toBeDisabled();
        await fireEvent.click(analyze);
        expect(runToolMock).not.toHaveBeenCalled();

        await fireEvent.click(screen.getByTestId('pac-cash-broker-31'));
        await waitFor(() => expect(fetchSourceMock).toHaveBeenCalledTimes(7));
        expect(fetchSourceMock).toHaveBeenNthCalledWith(7, replacementDate, accountGeneration, expect.objectContaining({selectedCashBrokerIds: []}));
        await waitFor(() => expect(analyze).toBeEnabled());

        const emptySelectionInput = await runAndReadInput();
        expect(emptySelectionInput.cash_balances).toEqual([]);
        expect(emptySelectionInput.cash_balances).not.toEqual(cachedCash);
    });

    it('removes a fresh manual Asset immediately without opening confirmation', async () => {
        renderTool();
        await waitForSource();

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        const name = await screen.findByTestId('pac-asset-name-0');
        expect(name).toBeEnabled();
        const row = name.closest<HTMLElement>('[data-testid="pac-asset-editor"]');
        if (!row) throw new Error('fixture manual PAC Asset row was not rendered');
        expect(row).toBeInTheDocument();
        const target = await screen.findByTestId(/^allocation-target-manual:asset:/);
        expect(target).toHaveValue('');

        await fireEvent.click(within(row).getByTestId('pac-remove-asset-0'));

        await waitFor(() => expect(row).not.toBeInTheDocument());
        expect(target).not.toBeInTheDocument();
        expect(screen.queryByTestId('pac-customized-removal-confirm')).toBeNull();
        expect(screen.queryByTestId('pac-asset-name-0')).toBeNull();
    });

    it('warns before removing an edited manual Asset', async () => {
        renderTool();
        await waitForSource();

        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        const name = await screen.findByTestId('pac-asset-name-0');
        expect(name).toBeEnabled();
        const row = name.closest<HTMLElement>('[data-testid="pac-asset-editor"]');
        if (!row) throw new Error('fixture manual PAC Asset row was not rendered');
        const target = await screen.findByTestId(/^allocation-target-manual:asset:/);
        expect(target).toHaveValue('');

        await fireEvent.input(name, {target: {value: 'Fixture edited manual PAC Asset'}});
        expect(name).toHaveValue('Fixture edited manual PAC Asset');
        await fireEvent.click(within(row).getByTestId('pac-remove-asset-0'));

        expect(screen.getByTestId('pac-customized-removal-confirm')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument();

        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('pac-customized-removal-confirm')).toBeNull());
        expect(row).toBeInTheDocument();
        expect(name).toHaveValue('Fixture edited manual PAC Asset');

        await fireEvent.click(within(row).getByTestId('pac-remove-asset-0'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(row).not.toBeInTheDocument());
    });

    it('keeps source and manual choices distinct and warns when removal loses the last target', async () => {
        renderTool();
        await waitForSource();

        const assetCard = () => screen.getByTestId('pac-owned-asset-17');
        await fireEvent.click(assetCard());
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        await waitFor(() => expect(screen.getAllByTestId('pac-asset-editor')).toHaveLength(2));

        const sourcePrice = screen.getByTestId('pac-current-price-0');
        const sourceRow = sourcePrice.closest<HTMLElement>('[data-testid="pac-asset-editor"]');
        if (!sourceRow) throw new Error('fixture imported PAC Asset row was not rendered');
        expect(sourceRow).toBeInTheDocument();
        expect(screen.queryByTestId('pac-current-price-1')).toBeNull();
        expect(screen.queryByTestId('pac-draft-revision')).toBeNull();
        expect(screen.queryByTestId('pac-mode-selector')).toBeNull();
        expect(screen.queryByTestId('pac-orders')).toBeNull();
        expect(screen.queryByTestId('pac-solver')).toBeNull();

        const target = (await screen.findByTestId('allocation-target-asset:17')) as HTMLInputElement;
        await fireEvent.input(target, {target: {value: '60.125000000001'}});
        await fireEvent.click(within(sourceRow).getByTestId('pac-remove-asset-0'));

        expect(screen.getByTestId('pac-customized-removal-confirm')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-cancel')).toBeInTheDocument();
        expect(screen.getByTestId('confirm-modal-confirm')).toBeInTheDocument();
        await fireEvent.click(screen.getByTestId('confirm-modal-cancel'));
        await waitFor(() => expect(screen.queryByTestId('pac-customized-removal-confirm')).toBeNull());
        expect(sourceRow).toBeInTheDocument();
        expect(assetCard()).toHaveAttribute('aria-pressed', 'true');
        expect(target).toHaveValue('60.125000000001');

        await fireEvent.click(within(sourceRow).getByTestId('pac-remove-asset-0'));
        await fireEvent.click(screen.getByTestId('confirm-modal-confirm'));
        await waitFor(() => expect(sourceRow).not.toBeInTheDocument());
        expect(assetCard()).toHaveAttribute('aria-pressed', 'false');
        expect(screen.queryByTestId('allocation-target-asset:17')).toBeNull();
    });

    it('ignores a compute response superseded by a draft edit', async () => {
        renderTool();
        await waitForSource();
        await fireEvent.click(screen.getByTestId('pac-add-manual-asset'));
        await fireEvent.input(screen.getByTestId('pac-asset-name-0'), {target: {value: 'Editable draft'}});

        runToolMock.mockResolvedValueOnce(success(readyOutput('Stable backend result', '10')));
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(within(screen.getByTestId('pac-result-panel')).getByText('Stable backend result')).toBeInTheDocument());

        const late = deferred<ToolItemResult<'pac_allocator', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => late.promise);
        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'true'));

        await fireEvent.input(screen.getByTestId('pac-asset-name-0'), {target: {value: 'Edited while pending'}});
        expect(screen.getByTestId('pac-asset-name-0')).toHaveValue('Edited while pending');
        late.resolve(success(readyOutput('Late backend result', '999')));

        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
        const result = within(screen.getByTestId('pac-result-panel'));
        expect(result.getByText('Stable backend result')).toBeInTheDocument();
        expect(result.queryByText('Late backend result')).toBeNull();
        expect(result.getByTestId('pac-result-stale')).toBeInTheDocument();
    });

    it('ignores an in-flight response after the authenticated account changes', async () => {
        renderTool();
        await waitForSource();
        const pending = deferred<ToolItemResult<'pac_allocator', '1.0.0'>>();
        runToolMock.mockImplementationOnce(() => pending.promise);

        await fireEvent.click(screen.getByTestId('pac-analyze'));
        await waitFor(() => expect(runToolMock).toHaveBeenCalledTimes(1));
        transitionClientSession(`pac-round4-other-account-${++accountSequence}`);
        pending.resolve(success(readyOutput('Wrong-account result')));

        await waitFor(() => expect(screen.getByTestId('pac-allocator-tool')).toHaveAttribute('data-busy', 'false'));
        expect(screen.queryByTestId('allocation-diagnostics')).toBeNull();
        expect(screen.queryByTestId('pac-client-error')).toBeNull();
        expect(screen.queryByTestId('pac-platform-error')).toBeNull();
    });
});
