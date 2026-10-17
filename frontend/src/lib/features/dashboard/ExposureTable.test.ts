// @vitest-environment jsdom
/**
 * ExposureTable — component test (Vitest + jsdom).
 *
 * Subjects:
 * - F9 analyzed-row highlight.
 * - Yield on Cost default column, status cells, sorting, tooltips and persisted
 *   visibility override.
 * - Privacy (decision D5′): the quantity beside a price is masked, while the
 *   price and the PMC it used to protect become public.
 * - C-97c-3 (the last describe): a quantity keeps the ten decimals of its
 *   column, the price and the PMC their significant digits.
 *
 * Rows are addressed by `data-row-id` (`makePositionKey(assetId, brokerId)`),
 * never by position: the table sorts by value descending.
 *
 * The mocked `$lib/api` returns an empty asset list plus controlled currencies:
 * row behavior depends only on props, while tooltip formatting still exercises
 * the real currency/date helpers.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

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
import {flushSync, tick} from 'svelte';
import {get} from 'svelte/store';
import {_, locale, waitLocale} from 'svelte-i18n';
import {currentLanguage} from '$lib/stores/app/language';
import {isPrivacyEnabled, setPrivacyEnabled} from '$lib/stores/app/privacyStore.svelte';
import {uiLocale} from '$lib/stores/app/uiLocale';
import {ensureCurrenciesLoaded, getCurrencyInfo} from '$lib/stores/reference/currencyStore';
import {formatCurrencyAmountPlain} from '$lib/utils/currency/currencyFormat';
import {formatPercent} from '$lib/utils/core/formatPercent';
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
    reason: 'insufficient_history' | 'income_without_eligible_quantity' | 'replay_inconsistent' | 'invalid_split' | 'missing_fx' | 'missing_wac' | 'non_positive_wac' | 'negative_net_income' | null;
    provenance: YieldOnCostProvenance;
}

interface HoldingOptions {
    currentValue?: string;
    /** The backend's `nav_weight_percent`. Omitted, the field is absent; `null` is the backend sending no weight. */
    navWeightPercent?: string | null;
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
        ...(options.navWeightPercent === undefined ? {} : {nav_weight_percent: options.navWeightPercent}),
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

/**
 * The trimmed text of the cell of `columnId` in the row of asset 11, the position every describe that
 * reads a cell mounts. The row renders no per-cell handle, so the cell is found through its header's
 * index (`dt-header-<id>`), among the row's structural `td-data` cells (see the privacy describe).
 */
function cellText(columnId: string): string {
    const headers = [...document.querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')];
    const index = headers.findIndex((header) => header.dataset.testid === `dt-header-${columnId}`);
    if (index < 0) throw new Error(`column ${columnId} not rendered`);
    const cells = [...rowEl(11, 1).querySelectorAll<HTMLElement>('td.td-data')];
    if (cells.length !== headers.length) throw new Error(`${cells.length} data cells for ${headers.length} headers`);
    return (cells[index].textContent ?? '').trim();
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
            displayCurrency: 'EUR',
            analyzedAssetId: null,
        });

        await waitFor(() => expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(2));

        expect(document.querySelector('tbody tr.row-analyzed')).toBeNull();
    });

    it('moves the tint when the analyzed asset changes', async () => {
        const {rerender} = render(ExposureTable, {
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()})],
            displayCurrency: 'EUR',
            analyzedAssetId: 11,
        });

        await waitFor(() => expect(rowEl(11, 1).className).toContain('row-analyzed'));

        await rerender({
            holdings: [holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), holding(22, 1, {yieldOnCost: noIncomeYieldOnCost()})],
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

    it('names corrections exceeding the year income as the unavailable reason (MF-O2)', async () => {
        // Labels resolved through i18n as the cell resolves them, never as literal text.
        const titleKey = 'dashboard.yieldOnCostUnavailable';
        const reasonKey = 'dashboard.yieldOnCostReasons.negativeNetIncome';
        const title = get(_)(titleKey);
        const reason = get(_)(reasonKey);
        // Controls: the catalogue carries both keys (a missing key renders as itself), and the
        // reason is not the generic text the cell falls back to for a reason it does not know.
        expect(title, `control: the catalogue carries ${titleKey}`).not.toBe(titleKey);
        expect(reason, `control: the catalogue carries ${reasonKey}`).not.toBe(reasonKey);
        expect(reason, 'control: the reason differs from the generic unavailable text').not.toBe(title);

        const yieldOnCost: YieldOnCostResult = {
            status: 'unavailable',
            value: null,
            reason: 'negative_net_income',
            provenance: baseProvenance({
                gross_income_transaction_count: 2,
                gross_income_per_unit: {code: 'EUR', amount: '-2'},
            }),
        };
        render(ExposureTable, {holdings: [holding(11, 1, {yieldOnCost})], navAmount: 1000, displayCurrency: 'EUR'});
        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());

        const row = within(rowEl(11, 1));
        expect(row.getByTestId('yield-on-cost-unavailable')).toHaveTextContent('-');
        expect(row.queryByTestId('yield-on-cost-value')).not.toBeInTheDocument();
        const info = row.getByTestId('yield-on-cost-info');
        expect(info.getAttribute('aria-label')).toBe(`${title}\n${reason}`);

        const lines = await tooltipLines(info);
        expect(lines).toHaveLength(2);
        expect(lines[1]).toBe(reason);
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
            displayCurrency: 'EUR',
        });

        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-annualized-return')).toBeInTheDocument());
        expect(screen.queryByTestId('dt-header-yield-on-cost')).not.toBeInTheDocument();
        expect(JSON.parse(storage.get(visibilityKey) ?? '{}')).toEqual({'yield-on-cost': false});
    });
});

/**
 * Privacy, decision D5′ of the product owner (2026-09-23): a quantity is masked
 * where it sits next to a price, because quantity × price rebuilds what the user
 * owns. The price and the PMC were masked only to stop that reconstruction while
 * the quantity was visible; with the quantity masked they are public again, as
 * the product owner ruled that prices and WAC are not patrimony (2026-09-22).
 *
 * The row renders no per-cell handle, so a cell is found by its column: the
 * header's `dt-header-<id>` gives the index, and the row's data cells (DataTable's
 * structural `td-data`, the hook DataTable.test.ts also uses) follow the same
 * visible-column order. Price and PMC are `hiddenByDefault`, so they are revealed
 * through the user-scoped visibility override the test above already exercises.
 *
 * Unmasked expectations come from the same formatting calls the component makes,
 * with privacy off — the interface locale decides their separators (M-18) — and are
 * checked once against the digits put in. Masked ones are literals: a placeholder has
 * no locale. Every step checks the flag and a fresh formatter call before the table,
 * so a red names its layer. `browser: false` in the shared `$app/environment`
 * mock keeps `setPrivacyEnabled` in memory.
 */
describe('ExposureTable — privacy (D5′)', () => {
    const QUANTITY = 7.25;
    const PRICE = 123.45;
    const WAC = 98.76;
    /** `holding(11, …)` values the position at 11 × 1000. */
    const VALUE = 11000;

    let quantityClear = '';
    let priceClear = '';
    let pmcClear = '';
    let valueClear = '';

    /** One position carrying every column under test. */
    function position() {
        return {...holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), quantity: String(QUANTITY), current_price: String(PRICE), wac_per_unit: String(WAC)};
    }

    function mount(): void {
        render(ExposureTable, {holdings: [position()], displayCurrency: 'EUR'});
    }

    /** Barrier: the row is rendered and the stored override has revealed price and PMC. */
    async function mounted(): Promise<void> {
        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-price')).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-pmc')).toBeInTheDocument());
    }

    /** Set the flag, then flush: synchronously, and once more through the microtask the app itself waits on. */
    async function setPrivacy(value: boolean): Promise<void> {
        setPrivacyEnabled(value);
        flushSync();
        await tick();
    }

    function expectClear(step: string): void {
        expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(false);
        expect(formatCurrencyAmountPlain(VALUE, 'EUR'), `${step} — control: a fresh formatter call`).toBe(valueClear);

        expect(cellText('value'), `${step} — value`).toBe(valueClear);
        expect(cellText('quantity'), `${step} — quantity shows its digits`).toBe(quantityClear);
        expect(cellText('price'), `${step} — price`).toBe(priceClear);
        expect(cellText('pmc'), `${step} — PMC`).toBe(pmcClear);
    }

    function expectMasked(step: string): void {
        expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(true);
        expect(formatCurrencyAmountPlain(VALUE, 'EUR'), `${step} — control: a fresh formatter call`).toBe('••• € 🇪🇺 EUR');

        // Positive control in the table itself: the value is personal money, masked.
        const value = cellText('value');
        expect(value, `${step} — value masked`).toBe('••• € 🇪🇺 EUR');
        expect(value, `${step} — value shows no digit`).not.toMatch(/\d/);

        const quantity = cellText('quantity');
        expect(quantity, `${step} — quantity masked, marker kept`).toBe('••• 📈');
        expect(quantity, `${step} — quantity shows no digit`).not.toMatch(/\d/);
        expect(quantity, `${step} — quantity keeps its 📈 marker`).toContain('📈');

        for (const [columnId, clear] of [
            ['price', priceClear],
            ['pmc', pmcClear],
        ]) {
            const text = cellText(columnId);
            expect(text, `${step} — ${columnId} stays public`).toBe(clear);
            expect(text, `${step} — ${columnId} shows its digits`).toMatch(/\d/);
            expect(text, `${step} — ${columnId} shows its currency`).toContain('€ 🇪🇺 EUR');
        }
    }

    beforeAll(async () => {
        await ensureCurrenciesLoaded('en');
        // Control: the catalogue is loaded, so every money cell carries the real symbol and flag.
        expect(getCurrencyInfo('EUR').symbol).toBe('€');

        setPrivacyEnabled(false);
        // Why (re-pin, M-18 CP2): the quantity is written in the interface locale — en-US here, the
        // English UI on jsdom's en-US browser — no longer in the host's.
        // Why (C-97c-3): up to the ten decimals of its column, not six; 7.25 reads the same either way.
        quantityClear = `${QUANTITY.toLocaleString(uiLocale(), {minimumFractionDigits: 0, maximumFractionDigits: 10})} 📈`;
        priceClear = formatCurrencyAmountPlain(PRICE, 'EUR', {sensitivity: 'public'});
        pmcClear = formatCurrencyAmountPlain(WAC, 'EUR', {sensitivity: 'public'});
        valueClear = formatCurrencyAmountPlain(VALUE, 'EUR');
        // The clear expectations are the formatters' own output: check once that they carry
        // the digits put in, or "shows its digits" would compare a placeholder with itself.
        expect(quantityClear.replace(/\D/g, '')).toBe('725');
        expect(priceClear.replace(/\D/g, '')).toBe('12345');
        expect(pmcClear.replace(/\D/g, '')).toBe('9876');
        expect(valueClear.replace(/\D/g, '')).toBe('1100000');
    });

    beforeEach(() => {
        storage.set(getUserStorageKey('dataTable_dashboard-holdings-v5_columnVisibilityOverrides'), JSON.stringify({price: true, pmc: true}));
    });

    afterEach(() => {
        // Module-level flag: a leftover `true` would mount the next table masked.
        setPrivacyEnabled(false);
    });

    it('mounted with privacy on: masks the quantity and keeps its 📈 marker, while price and PMC stay public', async () => {
        await setPrivacy(true);
        mount();
        await mounted();

        expectMasked('mount, privacy on');
    });

    it('follows the flag both ways once mounted: off → on → off', async () => {
        mount();
        await mounted();
        expectClear('mount, privacy off');

        await setPrivacy(true);
        expectMasked('off → on');

        await setPrivacy(false);
        expectClear('on → off');
    });
});

/**
 * M-18 CP2: the quantity in the interface language.
 *
 * The quantity cell writes its figure with `toLocaleString(undefined, …)`, the browser's locale: an
 * Italian on an en-US browser reads `12,345.6789` beside a weight written `30,9%`. Every figure is
 * written in the interface language (the developer's decision M-18, 2026-10-12), through `uiLocale()`:
 * the same digits — up to six decimals, none forced — in the interface locale. Privacy is off here; the
 * mask is the subject of the describe above.
 *
 * Barrier. The NAV weight in the same row already follows the interface language (`formatPercent`,
 * CP1). Read first, it proves the row rendered in Italian, so a quantity still in English is the
 * quantity's own formatter and not a table that never redrew.
 *
 * Expectations come from `Intl` in an explicit locale: the quantity as `toLocaleString` writes it with
 * the cell's options, the weight through `formatPercent`. English is the control: the en-US text,
 * grouped from 1,000 as it is today.
 *
 * Language. Switched as LanguageSelector does — `currentLanguage.set`, which also drives svelte-i18n —
 * with both dictionaries loaded; the `afterEach` puts English back.
 */
describe('ExposureTable — the quantity in the interface language (M-18)', () => {
    /** Grouped from 10,000 — Italian groups only from there — and with four decimals, so both separators are read. */
    const QUANTITY = 12_345.6789;
    /**
     * The backend's weight, carried by the fixture as the backend sends it: `holding(11, …)` values the
     * position at 11 000, and on a NAV of 35 555 its `nav_weight_percent` is 11 000 / 35 555 · 100,
     * quantized to 0.01. The table computes no weight of its own (W7), so it is given no NAV.
     */
    const WEIGHT = 30.94;

    function mount(): void {
        render(ExposureTable, {holdings: [{...holding(11, 1, {navWeightPercent: WEIGHT.toFixed(2), yieldOnCost: noIncomeYieldOnCost()}), quantity: String(QUANTITY)}], displayCurrency: 'EUR'});
    }

    /** Barrier: the row is rendered with both columns read below. */
    async function mounted(): Promise<void> {
        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-quantity')).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-weight')).toBeInTheDocument());
    }

    /** The two figures of the row. */
    function readRow(): {weight: string; quantity: string} {
        return {weight: cellText('weight'), quantity: cellText('quantity')};
    }

    /** What the row must read in `localeTag`, from the calls the cells make. */
    function expectedIn(localeTag: string): {weight: string; quantity: string} {
        return {
            weight: formatPercent(WEIGHT, {signed: false, digits: 1, locale: localeTag}),
            // Why (C-97c-3): up to the ten decimals of its column, not six; QUANTITY's four read the same either way.
            quantity: `${QUANTITY.toLocaleString(localeTag, {minimumFractionDigits: 0, maximumFractionDigits: 10})} 📈`,
        };
    }

    const ENGLISH = expectedIn('en-US');
    const ITALIAN = expectedIn('it');

    /** Change the UI language as LanguageSelector does, then flush. The controls name the layer if the language did not move. */
    async function switchLanguage(lang: 'en' | 'it'): Promise<void> {
        currentLanguage.set(lang);
        await waitLocale(lang);
        flushSync();
        await tick();
        expect(get(currentLanguage), `control: the app language is ${lang}`).toBe(lang);
        expect(get(locale), `control: the svelte-i18n locale is ${lang}`).toBe(lang);
    }

    beforeAll(async () => {
        // English was loaded by the file's own beforeAll; Italian joins it, so a switch never waits on a loader.
        await waitLocale('it');
        // Controls: this runtime has Italian data, so both figures change notation; and the English
        // quantity carries the digits put in.
        expect(ITALIAN.quantity, 'the Italian quantity differs from English').not.toBe(ENGLISH.quantity);
        expect(ITALIAN.weight, 'the Italian weight differs from English').not.toBe(ENGLISH.weight);
        expect(ENGLISH.quantity.replace(/\D/g, '')).toBe('123456789');
    });

    afterEach(async () => {
        // The language is module-level state shared by every test of the file.
        await switchLanguage('en');
    });

    it('English UI on an en-US browser (control): the quantity is today’s text, grouped from 1,000', async () => {
        expect(uiLocale(), 'control: the interface locale is en-US').toBe('en-US');
        mount();
        await mounted();

        expect(readRow()).toEqual(ENGLISH);
    });

    it('mounted with the UI in Italian on an en-US browser: the quantity in Italian notation, beside a weight that already is', async () => {
        await switchLanguage('it');
        mount();
        await mounted();

        const row = readRow();
        expect(row.weight, 'barrier: the weight in the same row is Italian, so the row rendered in Italian').toBe(ITALIAN.weight);
        expect(row.quantity).toBe(ITALIAN.quantity);
    });

    it('follows an in-place switch of the UI language, en → it → en', async () => {
        mount();
        await mounted();
        expect(readRow(), 'en, mount — today’s text').toEqual(ENGLISH);

        await switchLanguage('it');
        const italian = readRow();
        expect(italian.weight, 'barrier: the weight followed the switch').toBe(ITALIAN.weight);
        expect(italian.quantity, 'en → it in place — Italian notation').toBe(ITALIAN.quantity);

        await switchLanguage('en');
        expect(readRow(), 'it → en in place — today’s text again').toEqual(ENGLISH);
    });
});

/**
 * W7 (U8 of the release plan): the NAV weight is the backend's.
 *
 * The frontend shows the backend's figures; financial math has one home, the backend. The backend sends
 * `nav_weight_percent` — current value / NAV · 100, quantized to 0.01 — and null when the position has
 * no current value. The table used to fill a null with a weight of its own, `current_value / navAmount
 * · 100`: the same figure by a second rule, in a second place.
 *
 * The position is worth 100 and the table is handed a NAV of 1 000, so a weight it computed would read
 * 10.0%. The red sends no weight and expects the placeholder; the control sends the backend's 12.34
 * and expects it as it is.
 */
describe('ExposureTable — the NAV weight is the backend’s (W7 / U8)', () => {
    /** One position worth 100, carrying the backend's `nav_weight_percent`. */
    function mount(navWeightPercent: string | null): void {
        render(ExposureTable, {
            holdings: [holding(11, 1, {currentValue: '100', navWeightPercent, yieldOnCost: noIncomeYieldOnCost()})],
            // Why, on purpose: after W7 this is a legacy prop the component's catch-all ignores. Kept, it is
            // what a fallback would divide by, so a fallback brought back fails the first test below again.
            navAmount: 1000,
            displayCurrency: 'EUR',
        });
    }

    /** Barrier: the row is rendered with the weight column, and carries the value a fallback would divide. */
    async function mounted(): Promise<void> {
        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-weight')).toBeInTheDocument());
        expect(cellText('value').replace(/\D/g, ''), 'precondition: the row is worth 100.00').toBe('10000');
    }

    it('shows no weight when the backend sends none, not value / NAV computed by the table', async () => {
        mount(null);
        await mounted();

        expect(cellText('weight'), 'nav_weight_percent null: the placeholder, not 100 / 1 000 · 100').toBe('—');
    });

    it('control: shows the backend’s weight as it is, not value / NAV', async () => {
        mount('12.34');
        await mounted();

        const backend = formatPercent(12.34, {signed: false, digits: 1});
        expect(backend, 'control: the backend’s weight reads differently from value / NAV').not.toBe(formatPercent(10, {signed: false, digits: 1}));
        expect(cellText('weight')).toBe(backend);
    });
});

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10), on the dashboard's positions: a quantity on screen keeps the
 * decimals of its column, a price its significant digits.
 *
 * Today the quantity cell writes up to six decimals (`toLocaleString(uiLocale(), {maximumFractionDigits: 6})`): a
 * position of 0.1234567891 reads `0.123457`, one of 10 satoshis (0.0000001) reads `0`, beside its 📈. The price and the
 * PMC (the WAC per unit) are written as money with two fixed decimals (`formatCurrencyAmountPlain(…, {sensitivity:
 * 'public'})`): 0.0000034573 EUR reads `0.00 € 🇪🇺 EUR`, 1.234 EUR `1.23 € 🇪🇺 EUR`. The contract: the quantity with up to
 * ten decimals, its column's (C-97a), through Intl on a number — never an exponent — and still masked under privacy
 * (`maskableQuantity`); the price and the PMC with `{minFraction, maxFraction}` from `priceFractionDigits(value)`,
 * still public.
 *
 * Reds: quantities of 0.1234567891 and 0.0000001 (today `0.123457` and `0`); a price of 0.0000034573 and a PMC of
 * 0.0000041234 (today `0.00` both); a price of 1.234 (today `1.23`). Guards, green today and after: a quantity of 7.25,
 * a price of 123.45 and a PMC of 98.76; and the 10-satoshi quantity under privacy, masked (`••• 📈`, no digit).
 *
 * Reading as the privacy describe reads: the row of asset 11 at broker 1, each cell through its column's header
 * (`cellText`), price and PMC revealed through the user-scoped visibility override. A figure is matched as a whole number
 * token, since the cell also holds the 📈 or the currency. English UI on jsdom's en-US browser, checked before each
 * case: the digits are typed.
 */
describe('ExposureTable — a quantity keeps its column’s decimals, a price its significant digits (C-97c-3, D-C97c-1)', () => {
    /** A number written in exponent notation: `1e-7`. */
    const EXPONENT = /\d[eE][-+]?\d/;

    /** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** One position of asset 11 at broker 1 with `figures`, as the backend sends them (decimal strings). */
    function mountPosition(figures: {quantity: string; price: string; wac: string}): void {
        render(ExposureTable, {holdings: [{...holding(11, 1, {yieldOnCost: noIncomeYieldOnCost()}), quantity: figures.quantity, current_price: figures.price, wac_per_unit: figures.wac}], displayCurrency: 'EUR'});
    }

    /** Barrier: the row is rendered, and the stored override has revealed price and PMC. */
    async function mounted(): Promise<void> {
        await waitFor(() => expect(rowEl(11, 1)).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-price')).toBeInTheDocument());
        await waitFor(() => expect(screen.getByTestId('dt-header-pmc')).toBeInTheDocument());
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the table writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
        storage.set(getUserStorageKey('dataTable_dashboard-holdings-v5_columnVisibilityOverrides'), JSON.stringify({price: true, pmc: true}));
    });

    afterEach(() => {
        // Module-level flag: a leftover `true` would mount the next table masked.
        setPrivacyEnabled(false);
    });

    it('a quantity of 0.1234567891 reads whole: the ten decimals of its column, not six', async () => {
        mountPosition({quantity: '0.1234567891', price: '123.45', wac: '98.76'});
        await mounted();

        expect(cellText('quantity'), 'the quantity (today cut at the sixth decimal: 0.123457)').toMatch(numberToken('0.1234567891'));
    });

    it('a quantity of 0.0000001, a position of 10 satoshis, reads 0.0000001 — not 0, never in exponent notation', async () => {
        mountPosition({quantity: '0.0000001', price: '123.45', wac: '98.76'});
        await mounted();
        const quantity = cellText('quantity');

        expect.soft(quantity, 'the quantity (today 0: the position reads empty)').toMatch(numberToken('0.0000001'));
        expect.soft(quantity, 'no exponent notation').not.toMatch(EXPONENT);
    });

    it('a price of 0.0000034573 EUR and a PMC of 0.0000041234 EUR keep four significant digits: 0.000003457 and 0.000004123, not 0.00', async () => {
        mountPosition({quantity: '7.25', price: '0.0000034573', wac: '0.0000041234'});
        await mounted();

        expect.soft(cellText('price'), 'the price (today 0.00)').toMatch(numberToken('0.000003457'));
        expect.soft(cellText('pmc'), 'the PMC (today 0.00)').toMatch(numberToken('0.000004123'));
    });

    it('a price of 1.234 EUR reads 1.234 — four significant digits — not 1.23', async () => {
        mountPosition({quantity: '7.25', price: '1.234', wac: '98.76'});
        await mounted();

        expect(cellText('price'), 'the price (today 1.23)').toMatch(numberToken('1.234'));
    });

    it('guard: a quantity of 7.25, a price of 123.45 and a PMC of 98.76 read as today', async () => {
        mountPosition({quantity: '7.25', price: '123.45', wac: '98.76'});
        await mounted();

        expect.soft(cellText('quantity'), 'the quantity').toMatch(numberToken('7.25'));
        expect.soft(cellText('price'), 'the price').toMatch(numberToken('123.45'));
        expect.soft(cellText('pmc'), 'the PMC').toMatch(numberToken('98.76'));
    });

    it('guard: under privacy the 10-satoshi quantity stays masked — ••• 📈, no digit — while its price stays public', async () => {
        setPrivacyEnabled(true);
        flushSync();
        await tick();
        expect(isPrivacyEnabled(), 'control: the flag').toBe(true);
        mountPosition({quantity: '0.0000001', price: '123.45', wac: '98.76'});
        await mounted();

        expect.soft(cellText('quantity'), 'the quantity, masked with its marker').toBe('••• 📈');
        expect.soft(cellText('price'), 'the price, public').toMatch(numberToken('123.45'));
    });
});
