// @vitest-environment jsdom
/**
 * ExposureTable — component test (Vitest + jsdom).
 *
 * Subjects:
 * - F9 analyzed-row highlight.
 * - Yield on Cost default column, status cells, sorting, tooltips and persisted
 *   visibility override.
 *
 * Rows are addressed by `data-row-id` (`makePositionKey(assetId, brokerId)`),
 * never by position: the table sorts by value descending.
 *
 * The mocked `$lib/api` returns an empty asset list plus controlled currencies:
 * row behavior depends only on props, while tooltip formatting still exercises
 * the real currency/date helpers.
 */
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, property) {
                if (property === 'list_currencies_api_v1_utilities_currencies_get') {
                    return vi.fn(async () => ({
                        items: [
                            {code: 'CAD', name: 'Canadian dollar', symbol: '$', flag_emoji: '🇨🇦', country_codes: ['CA'], country_names: ['Canada']},
                            {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
                            {code: 'JPY', name: 'Japanese yen', symbol: '¥', flag_emoji: '🇯🇵', country_codes: ['JP'], country_names: ['Japan']},
                        ],
                    }));
                }
                if (property === 'list_assets_api_v1_assets_query_get') {
                    return vi.fn(async () => []);
                }
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

const storage = new Map<string, string>();
vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => void storage.set(key, value),
    removeItem: (key: string) => void storage.delete(key),
});

import {fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {getUserStorageKey} from '$lib/utils/storage';
import ExposureTable from './ExposureTable.svelte';

interface FxProvenance {
    purpose: 'income' | 'wac';
    requested_date: string;
    rate_date: string;
    from_currency: string;
    to_currency: string;
    days_back: number;
}

interface YieldOnCostProvenance {
    source: 'transactions';
    window_start: string;
    window_end: string;
    first_pair_transaction_date: string | null;
    gross_income_transaction_count: number;
    gross_income_per_unit: {code: string; amount: string} | null;
    net_zero: boolean;
    fx: FxProvenance[];
    issue_date: string | null;
    issue_pair: string | null;
}

interface YieldOnCostResult {
    status: 'available' | 'no_income' | 'unavailable';
    value: string | null;
    reason: 'insufficient_history' | 'income_without_eligible_quantity' | 'replay_inconsistent' | 'invalid_split' | 'missing_fx' | 'missing_wac' | 'non_positive_wac' | null;
    provenance: YieldOnCostProvenance;
}

interface HoldingOptions {
    currentValue?: string;
    yieldOnCost: YieldOnCostResult;
}

function holding(asset_id: number, broker_id: number, options: HoldingOptions) {
    return {
        asset_id,
        asset_name: `Asset ${asset_id}`,
        asset_type: 'STOCK',
        broker_id,
        broker_name: `Broker ${broker_id}`,
        quantity: '10',
        current_value: options.currentValue ?? String(asset_id * 1000), // distinct values → deterministic sort
        yield_on_cost: options.yieldOnCost,
    };
}

function baseProvenance(overrides: Partial<YieldOnCostProvenance> = {}): YieldOnCostProvenance {
    return {
        source: 'transactions',
        window_start: '2025-09-12',
        window_end: '2026-09-11',
        first_pair_transaction_date: '2024-01-01',
        gross_income_transaction_count: 0,
        gross_income_per_unit: null,
        net_zero: false,
        fx: [],
        issue_date: null,
        issue_pair: null,
        ...overrides,
    };
}

function availableYieldOnCost(value = '0.025'): YieldOnCostResult {
    const netZero = value === '0';
    return {
        status: 'available',
        value,
        reason: null,
        provenance: baseProvenance({
            gross_income_transaction_count: 2,
            gross_income_per_unit: {code: 'EUR', amount: netZero ? '0' : '10.000000'},
            net_zero: netZero,
            fx: netZero
                ? []
                : [
                      {
                          purpose: 'income',
                          requested_date: '2026-06-20',
                          rate_date: '2026-06-18',
                          from_currency: 'CAD',
                          to_currency: 'EUR',
                          days_back: 2,
                      },
                  ],
        }),
    };
}

function noIncomeYieldOnCost(): YieldOnCostResult {
    return {
        status: 'no_income',
        value: '0',
        reason: null,
        provenance: baseProvenance({
            gross_income_transaction_count: 0,
            gross_income_per_unit: {code: 'EUR', amount: '0'},
        }),
    };
}

function unavailableYieldOnCost(reason: Exclude<YieldOnCostResult['reason'], null> = 'missing_fx'): YieldOnCostResult {
    return {
        status: 'unavailable',
        value: null,
        reason,
        provenance: baseProvenance({
            gross_income_transaction_count: 1,
            issue_date: '2026-06-20',
            issue_pair: 'JPY/EUR',
        }),
    };
}

/** The row for (assetId, brokerId): makePositionKey's "assetId-brokerId". */
function rowEl(assetId: number, brokerId: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${assetId}-${brokerId}"]`);
    if (!el) throw new Error(`row ${assetId}-${brokerId} not rendered`);
    return el;
}

function renderedRowIds(): string[] {
    return [...document.querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => row.dataset.rowId ?? '');
}

async function tooltipLines(trigger: HTMLElement): Promise<string[]> {
    await fireEvent.click(trigger);
    const tooltip = screen.getByRole('tooltip');
    const lines = tooltip.textContent?.split('\n') ?? [];
    await fireEvent.click(trigger);
    await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());
    return lines;
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    storage.clear();
});

describe('ExposureTable — analyzedAssetId row highlight (F9)', () => {
    it('marks only the analyzed asset row with row-analyzed', async () => {
        render(ExposureTable, {
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(33, 2, {yieldOnCost: noIncomeYieldOnCost()})],
            navAmount: 6000,
            displayCurrency: 'EUR',
            analyzedAssetId: 22,
        });

        // Barrier: all three rows rendered before reading any class.
        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3));

        expect(rowEl(22, 1).className).toContain('row-analyzed');
        expect(rowEl(11, 1).className).not.toContain('row-analyzed');
        expect(rowEl(33, 2).className).not.toContain('row-analyzed');
    });

    it('marks nothing when no analysis is open (analyzedAssetId null/absent)', async () => {
        render(ExposureTable, {
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()})],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: null,
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(2));

        expect(document.querySelector('tbody tr.row-analyzed')).toBeNull();
    });

    it('moves the tint when the analyzed asset changes', async () => {
        const {rerender} = render(ExposureTable, {
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()})],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: 11,
        });

        await waitFor(() => expect(rowEl(11, 1).className).toContain('row-analyzed'));

        await rerender({
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()})],
            navAmount: 3000,
            displayCurrency: 'EUR',
            analyzedAssetId: 22,
        });

        await waitFor(() => expect(rowEl(22, 1).className).toContain('row-analyzed'));
        expect(rowEl(11, 1).className).not.toContain('row-analyzed');
    });
});

describe('ExposureTable — Yield on Cost', () => {
    it('shows YOC by default immediately after Annualized with header tooltip integration', async () => {
        render(ExposureTable, {
            holdings: [
                holding(11, 1, {
                    yieldOnCost: availableYieldOnCost(),
                }),
            ],
            navAmount: 1000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());

        const headerIds = [...document.querySelectorAll<HTMLElement>('thead [data-testid^="dt-header-"]')].map((header) => header.dataset.testid);
        const annualizedIndex = headerIds.indexOf('dt-header-annualized-return');
        const yieldOnCostIndex = headerIds.indexOf('dt-header-yield-on-cost');
        expect(annualizedIndex).toBeGreaterThanOrEqual(0);
        expect(yieldOnCostIndex).toBe(annualizedIndex + 1);

        const header = screen.getByTestId('dt-header-yield-on-cost');
        const guideTrigger = within(header).getByTestId('dt-header-tooltip-yield-on-cost');
        expect(guideTrigger).toHaveAttribute('type', 'button');
        expect(guideTrigger).not.toHaveAttribute('href');
        expect(guideTrigger).not.toHaveAttribute('title');
        expect(within(rowEl(11, 1)).getByTestId('yield-on-cost-value')).toHaveTextContent('2.50%');
    });

    it('renders every required YOC result without conflating known zero and unavailable', async () => {
        render(ExposureTable, {
            holdings: [
                holding(11, 1, {
                    yieldOnCost: availableYieldOnCost(),
                }),
                holding(22, 1, {
                    yieldOnCost: availableYieldOnCost('0'),
                }),
                holding(33, 1, {
                    yieldOnCost: noIncomeYieldOnCost(),
                }),
                holding(44, 1, {
                    yieldOnCost: unavailableYieldOnCost(),
                }),
            ],
            navAmount: 6000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(4));

        const available = within(rowEl(11, 1)).getByTestId('yield-on-cost-value');
        expect(available).toHaveTextContent('2.50%');
        expect(available).not.toHaveTextContent('+2.50%');

        const zeroAvailable = within(rowEl(22, 1)).getByTestId('yield-on-cost-value');
        expect(zeroAvailable).toHaveTextContent('0.00%');

        const noIncomeRow = within(rowEl(33, 1));
        expect(noIncomeRow.getByTestId('yield-on-cost-no-income')).toHaveTextContent('-');
        expect(noIncomeRow.queryByTestId('yield-on-cost-info')).not.toBeInTheDocument();

        const unavailableRow = within(rowEl(44, 1));
        expect(unavailableRow.getByTestId('yield-on-cost-unavailable')).toHaveTextContent('-');
        const infoButton = unavailableRow.getByTestId('yield-on-cost-info');
        expect(infoButton).toHaveAttribute('aria-label');
        expect(infoButton.getAttribute('aria-label')).not.toBe('');

        await fireEvent.click(infoButton);
        expect(screen.getByTestId('tooltip-content')).toBeInTheDocument();
        expect(screen.getByRole('tooltip')).toBeVisible();
    });

    it('keeps tooltip copy concise while localizing currency flags and dates', async () => {
        render(ExposureTable, {
            holdings: [
                holding(11, 1, {
                    yieldOnCost: availableYieldOnCost('0.1'),
                }),
                holding(22, 1, {
                    yieldOnCost: noIncomeYieldOnCost(),
                }),
                holding(33, 1, {
                    yieldOnCost: unavailableYieldOnCost(),
                }),
            ],
            navAmount: 6000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3));

        const available = within(rowEl(11, 1)).getByTestId('yield-on-cost-value');
        await waitFor(() => expect(available.getAttribute('aria-label')).toContain('🇨🇦 CAD → 🇪🇺 EUR'));
        const availableLines = await tooltipLines(available);
        expect(availableLines).toHaveLength(4);
        expect(availableLines[0]).toMatch(/10\.00%$/);
        expect(availableLines[1]).toMatch(/10 € 🇪🇺 EUR$/);
        expect(availableLines[2]).toContain('Sep 12, 2025');
        expect(availableLines[2]).toContain('Sep 11, 2026');
        expect(availableLines[3]).toContain('🇨🇦 CAD → 🇪🇺 EUR');
        expect(availableLines[3]).toContain('Jun 18, 2026');
        expect(availableLines.join('\n')).not.toContain('Jun 20, 2026');

        const noIncome = within(rowEl(22, 1)).getByTestId('yield-on-cost-no-income');
        const noIncomeLines = await tooltipLines(noIncome);
        expect(noIncomeLines).toHaveLength(3);
        expect(noIncomeLines[2]).toContain('Sep 12, 2025');
        expect(noIncomeLines[2]).toContain('Sep 11, 2026');

        const unavailable = within(rowEl(33, 1)).getByTestId('yield-on-cost-info');
        await waitFor(() => expect(unavailable.getAttribute('aria-label')).toContain('🇯🇵 JPY → 🇪🇺 EUR'));
        const unavailableLines = await tooltipLines(unavailable);
        expect(unavailableLines).toHaveLength(2);
        expect(unavailableLines[1]).toBe('The 🇯🇵 JPY → 🇪🇺 EUR exchange rate required for the calculation is missing on Jun 20, 2026.');
        expect(unavailableLines[1]).toContain('🇯🇵 JPY → 🇪🇺 EUR');
        expect(unavailableLines[1]).toContain('Jun 20, 2026');
    });

    it('deduplicates YOC FX tuples and caps distinct conversion lines with neutral overflow', async () => {
        const duplicateTuple: FxProvenance = {
            purpose: 'income',
            requested_date: '2026-06-20',
            rate_date: '2026-06-18',
            from_currency: 'CAD',
            to_currency: 'EUR',
            days_back: 2,
        };
        const yieldOnCost = availableYieldOnCost('0.1');
        yieldOnCost.provenance.fx = [
            duplicateTuple,
            {
                ...duplicateTuple,
                purpose: 'wac',
                requested_date: '2026-06-19',
                days_back: 1,
            },
            {
                purpose: 'income',
                requested_date: '2026-06-20',
                rate_date: '2026-06-18',
                from_currency: 'JPY',
                to_currency: 'EUR',
                days_back: 2,
            },
            {
                purpose: 'wac',
                requested_date: '2026-06-20',
                rate_date: '2026-06-19',
                from_currency: 'CAD',
                to_currency: 'EUR',
                days_back: 1,
            },
            {
                purpose: 'income',
                requested_date: '2026-06-20',
                rate_date: '2026-06-20',
                from_currency: 'EUR',
                to_currency: 'CAD',
                days_back: 0,
            },
            {
                purpose: 'wac',
                requested_date: '2026-06-22',
                rate_date: '2026-06-21',
                from_currency: 'JPY',
                to_currency: 'CAD',
                days_back: 1,
            },
            {
                purpose: 'income',
                requested_date: '2026-06-22',
                rate_date: '2026-06-22',
                from_currency: 'EUR',
                to_currency: 'EUR',
                days_back: 0,
            },
        ];

        render(ExposureTable, {
            holdings: [holding(11, 1, {yieldOnCost})],
            navAmount: 1000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());

        const available = within(rowEl(11, 1)).getByTestId('yield-on-cost-value');
        await waitFor(() => expect(available.getAttribute('aria-label')).toContain('🇨🇦 CAD → 🇪🇺 EUR'));
        const lines = await tooltipLines(available);
        const conversionLines = lines.filter((line) => line.includes(' → '));

        expect(conversionLines).toHaveLength(3);
        expect(new Set(conversionLines).size).toBe(3);
        expect(conversionLines.filter((line) => line.includes('🇨🇦 CAD → 🇪🇺 EUR') && line.includes('Jun 18, 2026'))).toHaveLength(1);
        expect(conversionLines.some((line) => line.includes('🇯🇵 JPY → 🇪🇺 EUR') && line.includes('Jun 18, 2026'))).toBe(true);
        expect(conversionLines.some((line) => line.includes('🇨🇦 CAD → 🇪🇺 EUR') && line.includes('Jun 19, 2026'))).toBe(true);
        expect(conversionLines.some((line) => line.includes('🇪🇺 EUR → 🇪🇺 EUR'))).toBe(false);
        expect(lines.filter((line) => line.startsWith('…'))).toEqual(['… (+2)']);
    });

    it('sorts known zero numerically while keeping unavailable last in both directions', async () => {
        render(ExposureTable, {
            holdings: [
                holding(11, 1, {
                    yieldOnCost: availableYieldOnCost('0.025'),
                }),
                holding(22, 1, {
                    yieldOnCost: availableYieldOnCost('0'),
                }),
                holding(33, 1, {
                    yieldOnCost: noIncomeYieldOnCost(),
                }),
                holding(44, 1, {
                    yieldOnCost: availableYieldOnCost('0.2'),
                }),
                holding(55, 1, {
                    yieldOnCost: unavailableYieldOnCost('missing_wac'),
                }),
            ],
            navAmount: 10000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(5));

        await fireEvent.click(screen.getByTestId('dt-sort-yield-on-cost'));
        await waitFor(() => {
            const rowIds = renderedRowIds();
            expect(new Set(rowIds.slice(0, 2))).toEqual(new Set(['22-1', '33-1']));
            expect(rowIds.slice(2, 4)).toEqual(['11-1', '44-1']);
            expect(rowIds[4]).toBe('55-1');
        });

        await fireEvent.click(screen.getByTestId('dt-sort-yield-on-cost'));
        await waitFor(() => {
            const rowIds = renderedRowIds();
            expect(rowIds.slice(0, 2)).toEqual(['44-1', '11-1']);
            expect(new Set(rowIds.slice(2, 4))).toEqual(new Set(['22-1', '33-1']));
            expect(rowIds[4]).toBe('55-1');
        });
    });

    it('keeps the existing user-scoped dashboard-holdings-v5 visibility override', async () => {
        const visibilityKey = getUserStorageKey('dataTable_dashboard-holdings-v5_columnVisibilityOverrides');
        storage.set(visibilityKey, JSON.stringify({'yield-on-cost': false}));

        render(ExposureTable, {
            holdings: [
                holding(11, 1, {
                    yieldOnCost: availableYieldOnCost(),
                }),
            ],
            navAmount: 1000,
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-annualized-return')).toBeInTheDocument());
        expect(screen.queryByTestId('dt-header-yield-on-cost')).not.toBeInTheDocument();
        expect(JSON.parse(storage.get(visibilityKey) ?? '{}')).toEqual({'yield-on-cost': false});
    });
});
