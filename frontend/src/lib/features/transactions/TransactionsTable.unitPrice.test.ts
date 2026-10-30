// @vitest-environment jsdom
/**
 * TransactionsTable — the read-only «unit price» column (W2-6).
 * Component test (Vitest + jsdom).
 *
 * The column sits next to the cash amount and shows, for a trade, what one unit cost: |cash| / |quantity| × the asset's
 * `quote_base_quantity`, through `rowUnitPrice` (the helper the transaction form's unit-price field also uses), in the
 * currency of the cash amount. It is a PRICE, public for the privacy toggle: the cash amount beside it is a TOTAL, personal.
 *
 * What is covered, each against its opposite so a green is never «nothing was drawn»:
 *   - a BUY (negative cash) and a SELL (positive cash) show a positive price; a bond on base 100 shows the price per 100;
 *     a cash amount in another currency than the asset's is priced in the cash currency;
 *   - the cell is `—` where there is nothing to show: a type with no quantity (DEPOSIT), an asset the store does not know
 *     (no quote base), a type with no asset or no cash (an FX pair, an asset TRANSFER), and a pair leg;
 *   - privacy: with the toggle ON the cash cell of the same row is masked and the price is not — mounted in the clear and
 *     toggled in place, and mounted already on;
 *   - the column is visible by default and the table's column-visibility control hides it and brings it back.
 *
 * Selection. Rows by `tbody tr[data-row-id="tx-<id>"]`, the column's cell by `td[data-column-id="unitPrice"]` in the row,
 * the price by `tx-unit-price-cell-<id>`, the cash by `tx-cash-cell-<id>`. Nothing here reads translated text: the
 * expected price text is the formatter's own output (`formatCurrencyAmountHtml`, sensitivity `public`), checked once to
 * carry the digits put in. The `—` is a glyph, not a translation.
 *
 * Types. `getTypeRule` answers from the type store, loaded here from a fixture shaped as the backend declares it
 * (TX_TYPE_METADATA): without it every type would take the permissive fallback rule and DEPOSIT would look like a trade.
 * Assets. The asset store is filled through the mocked list call, with their `quote_base_quantity`.
 */
import {afterEach, beforeAll, describe, expect, it, vi} from 'vitest';
import {flushSync, tick} from 'svelte';

vi.mock('$lib/api', () => {
    const cache = new Map<string, ReturnType<typeof vi.fn>>();
    const zodiosApi = new Proxy(
        {},
        {
            get(_t, prop: string) {
                if (!cache.has(prop))
                    cache.set(
                        prop,
                        vi.fn(async () => undefined),
                    );
                return cache.get(prop);
            },
        },
    );
    return {zodiosApi, ApiError: class ApiError extends Error {}, axiosInstance: {}};
});

import {zodiosApi} from '$lib/api';
import {schemas} from '$lib/api/generated';
import {render, screen, setupI18n, waitFor} from '$test/component';
import {isPrivacyEnabled, setPrivacyEnabled, togglePrivacy} from '$lib/stores/app/privacyStore.svelte';
import {ensureAssetsLoaded, resetAssetStore} from '$lib/stores/reference/assetStore';
import {ensureCurrenciesLoaded} from '$lib/stores/reference/currencyStore';
import {ensureTypesLoaded, isTypesLoaded} from './transactionTypeStore';
import {formatCurrencyAmountHtml} from '$lib/utils/currency/currencyFormat';
import {PRIVACY_PLACEHOLDER} from '$lib/utils/privacy/maskable';
import TransactionsTable from './TransactionsTable.svelte';
import type {TXReadItem} from './types';

const P = PRIVACY_PLACEHOLDER;

const BROKER = {id: 51, name: 'W2-6 broker', portal_url: 'https://broker.example.com', icon_url: null, default_import_plugin: null};

/** Asset 61 quotes per unit (EUR); asset 62 is a bond quoted per 100 nominal (EUR). Asset 69 is not in the list: its quote base is unknown. */
const ASSETS = [
    {id: 61, display_name: 'W2-6 stock', currency: 'EUR', quote_base_quantity: 1, active: true},
    {id: 62, display_name: 'W2-6 bond', currency: 'EUR', quote_base_quantity: 100, active: true},
];
const UNKNOWN_ASSET_ID = 69;

const typeBase = {doc_slug: null, requires_link: false, event_compatible: false, swap_group: [] as string[], cost_basis_mode: 'forbidden' as const};
const TYPES_RESPONSE = schemas.TXTypesResponse.parse({
    transaction_types: [
        {...typeBase, code: 'BUY', name: 'Buy', description: 'Buy', icon_slug: 'buy', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'positive', cash_sign: 'negative'},
        {...typeBase, code: 'SELL', name: 'Sell', description: 'Sell', icon_slug: 'sell', asset_mode: 'required', cash_mode: 'required', quantity_mode: 'required', quantity_sign: 'negative', cash_sign: 'positive'},
        {...typeBase, code: 'DEPOSIT', name: 'Deposit', description: 'Deposit', icon_slug: 'deposit', asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', quantity_sign: 'zero', cash_sign: 'positive'},
        {...typeBase, code: 'FX_CONVERSION', name: 'FX', description: 'FX', icon_slug: 'fx-conversion', asset_mode: 'forbidden', cash_mode: 'required', quantity_mode: 'forbidden', requires_link: true, quantity_sign: 'zero', cash_sign: 'nonzero', pair_form_layout: 'fx'},
        {
            ...typeBase,
            code: 'TRANSFER',
            name: 'Asset transfer',
            description: 'Asset transfer',
            icon_slug: 'transfer',
            asset_mode: 'required',
            cash_mode: 'forbidden',
            quantity_mode: 'required',
            requires_link: true,
            quantity_sign: 'nonzero',
            cash_sign: 'zero',
            pair_form_layout: 'transfer_asset',
        },
    ],
    event_types: [],
});

const base = {asset_event_id: null, tags: [], description: null};

/** A BUY of 10 units of asset 61 for 1000.00 EUR: unit price 100. */
const BUY: TXReadItem = {...base, id: 8301, broker_id: BROKER.id, asset_id: 61, type: 'BUY', date: '2026-04-01', quantity: '10', cash: {code: 'EUR', amount: '-1000.00'}, related_transaction_id: null};
/** A SELL of 3 units of asset 61 for 450.30 EUR: unit price 150.1. */
const SELL: TXReadItem = {...base, id: 8302, broker_id: BROKER.id, asset_id: 61, type: 'SELL', date: '2026-04-02', quantity: '-3', cash: {code: 'EUR', amount: '450.30'}, related_transaction_id: null};
/** A bond BUY on base 100: 5000 nominal for 4950.00 EUR → 99 per 100. */
const BOND_BUY: TXReadItem = {...base, id: 8303, broker_id: BROKER.id, asset_id: 62, type: 'BUY', date: '2026-04-03', quantity: '5000', cash: {code: 'EUR', amount: '-4950.00'}, related_transaction_id: null};
/** The same kind of BUY, paid in USD: 10 units for 1250.00 USD → priced in USD, the cash currency, not the asset's EUR. */
const BUY_USD: TXReadItem = {...base, id: 8304, broker_id: BROKER.id, asset_id: 61, type: 'BUY', date: '2026-04-04', quantity: '10', cash: {code: 'USD', amount: '-1250.00'}, related_transaction_id: null};
/** A DEPOSIT: its type has no quantity and no asset. */
const DEPOSIT: TXReadItem = {...base, id: 8305, broker_id: BROKER.id, asset_id: null, type: 'DEPOSIT', date: '2026-04-05', quantity: '0', cash: {code: 'EUR', amount: '25.00'}, related_transaction_id: null};
/** A BUY of an asset the asset store does not know: no quote base, no price. */
const BUY_UNKNOWN_ASSET: TXReadItem = {...base, id: 8306, broker_id: BROKER.id, asset_id: UNKNOWN_ASSET_ID, type: 'BUY', date: '2026-04-06', quantity: '10', cash: {code: 'EUR', amount: '-1000.00'}, related_transaction_id: null};
/** A linked FX conversion: cash only, a pair. */
const FX_GIVER: TXReadItem = {...base, id: 8307, broker_id: BROKER.id, asset_id: null, type: 'FX_CONVERSION', date: '2026-04-07', quantity: '0', cash: {code: 'EUR', amount: '-100.00'}, related_transaction_id: 8308};
const FX_RECEIVER: TXReadItem = {...FX_GIVER, id: 8308, cash: {code: 'USD', amount: '109.00'}, related_transaction_id: FX_GIVER.id};
/** A linked asset transfer: asset and quantity, no cash. */
const TRANSFER_OUT: TXReadItem = {...base, id: 8309, broker_id: BROKER.id, asset_id: 61, type: 'TRANSFER', date: '2026-04-08', quantity: '-5', cash: null, related_transaction_id: 8310};
const TRANSFER_IN: TXReadItem = {...TRANSFER_OUT, id: 8310, quantity: '5', related_transaction_id: TRANSFER_OUT.id};
/**
 * Two BUY rows linked to each other. Not data the backend would accept: they exist to isolate the pair-leg clause. Each
 * has a quantity, a cash amount, a known asset and a type that allows all three, so only «this row is a pair leg» can
 * make the cell `—`.
 */
const LEG_A: TXReadItem = {...base, id: 8311, broker_id: BROKER.id, asset_id: 61, type: 'BUY', date: '2026-04-09', quantity: '10', cash: {code: 'EUR', amount: '-1000.00'}, related_transaction_id: 8312};
const LEG_B: TXReadItem = {...LEG_A, id: 8312, related_transaction_id: LEG_A.id};

const ALL_ROWS: TXReadItem[] = [BUY, SELL, BOND_BUY, BUY_USD, DEPOSIT, BUY_UNKNOWN_ASSET, FX_GIVER, FX_RECEIVER, TRANSFER_OUT, TRANSFER_IN, LEG_A, LEG_B];

/** Filled in `beforeAll`, with privacy off, from the formatter the column must use. */
const clear: Record<string, string> = {};

/** Text as a reader sees it: whitespace runs collapsed, surrounding blanks trimmed. */
function norm(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** What an HTML-formatted amount reads as once rendered. */
function readHtml(html: string): string {
    const host = document.createElement('span');
    host.innerHTML = html;
    return norm(host.textContent);
}

/** The public price text for `amount` in `code`, as the column must draw it. */
function priceText(amount: number, code: string): string {
    return readHtml(formatCurrencyAmountHtml(amount, code, {sensitivity: 'public'}));
}

function mount(): ReturnType<typeof render> {
    return render(TransactionsTable, {
        mainRows: ALL_ROWS.map((r) => structuredClone(r)),
        partnerRows: [],
        brokers: [{...BROKER}],
        eventTooltipMap: new Map(),
    });
}

function rowEl(txId: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="tx-${txId}"]`);
    if (!el) throw new Error(`row tx-${txId} not rendered`);
    return el;
}

/** Barrier: the table is drawn and the asset store has answered (the asset cell names the asset instead of `#<id>`). */
async function mounted(): Promise<void> {
    for (const tx of ALL_ROWS) await waitFor(() => rowEl(tx.id));
    const links = await screen.findAllByTestId(`tx-asset-link-${ASSETS[0].id}`);
    await waitFor(() => expect(norm(links[0].textContent), 'premise: the asset store answered').toContain(ASSETS[0].display_name));
}

/** The unit-price cell (`td`) of a row, whatever it holds. */
function unitPriceTd(txId: number): HTMLElement {
    const td = rowEl(txId).querySelector<HTMLElement>('td[data-column-id="unitPrice"]');
    if (!td) throw new Error(`row tx-${txId} has no unitPrice cell`);
    return td;
}

function priceCell(txId: number): HTMLElement {
    return screen.getByTestId(`tx-unit-price-cell-${txId}`);
}

async function togglePrivacyInPlace(): Promise<void> {
    togglePrivacy();
    flushSync();
    await tick();
}

beforeAll(async () => {
    await setupI18n();
    vi.mocked(zodiosApi.list_currencies_api_v1_utilities_currencies_get).mockResolvedValue({
        items: [
            {code: 'EUR', name: 'Euro', symbol: '€', flag_emoji: '🇪🇺', country_codes: [], country_names: []},
            {code: 'USD', name: 'US Dollar', symbol: '$', flag_emoji: '🇺🇸', country_codes: ['US'], country_names: ['United States']},
        ],
    } as never);
    vi.mocked(zodiosApi.list_assets_api_v1_assets_query_get).mockResolvedValue(ASSETS as never);
    vi.mocked(zodiosApi.get_transaction_types_api_v1_transactions_types_get).mockResolvedValue(TYPES_RESPONSE as never);
    resetAssetStore();
    await ensureCurrenciesLoaded('en');
    await ensureAssetsLoaded();
    await ensureTypesLoaded();
    expect(isTypesLoaded(), 'premise: the type store holds the fixture').toBe(true);

    setPrivacyEnabled(false);
    clear.buy = priceText(100, 'EUR');
    clear.sell = priceText(150.1, 'EUR');
    clear.bond = priceText(99, 'EUR');
    clear.buyUsd = priceText(125, 'USD');
    clear.buyCash = readHtml(formatCurrencyAmountHtml(-1000, 'EUR', {showSign: true}));

    // The expectations are the formatter's own output: check once that they carry the digits put in, so a formatter that
    // masked unconditionally could not make «the price is not masked» compare the placeholder with itself.
    const digits = (text: string): string => text.replace(/\D/g, '');
    expect(digits(clear.buy)).toBe('10000');
    expect(digits(clear.sell)).toBe('15010');
    expect(digits(clear.bond)).toBe('9900');
    expect(digits(clear.buyUsd)).toBe('12500');
    expect(clear.buyUsd).toMatch(/USD$/);
    expect(digits(clear.buyCash)).toBe('100000');
    for (const text of Object.values(clear)) expect(text).not.toContain(P);
});

afterEach(() => {
    // The flag is module-level state shared by every test in this file.
    setPrivacyEnabled(false);
});

describe('TransactionsTable — the unit price column shows what one unit cost', () => {
    it('a BUY, a SELL, a bond on base 100 and a BUY paid in another currency: the price, in the currency of the cash', async () => {
        mount();
        await mounted();

        expect(norm(priceCell(BUY.id).textContent), 'BUY 10 for −1000 → 100').toBe(clear.buy);
        expect(norm(priceCell(SELL.id).textContent), 'SELL −3 for +450.30 → 150.1').toBe(clear.sell);
        expect(norm(priceCell(BOND_BUY.id).textContent), 'bond: 5000 for −4950 on base 100 → 99 per 100').toBe(clear.bond);
        expect(norm(priceCell(BUY_USD.id).textContent), 'paid in USD → the price is in USD').toBe(clear.buyUsd);

        // The cell is the column's own: it sits in the unitPrice cell of the row, and the cash cell is another one.
        expect(unitPriceTd(BUY.id).contains(priceCell(BUY.id)), 'the price is drawn in the unitPrice column').toBe(true);
        expect(unitPriceTd(BUY.id).contains(screen.getByTestId(`tx-cash-cell-${BUY.id}`)), 'the cash is not').toBe(false);
    });

    it('is a dash where there is no price: no quantity, unknown asset, a type with no cash or no asset, a pair leg', async () => {
        mount();
        await mounted();

        const rows: Array<[string, TXReadItem]> = [
            ['DEPOSIT (no quantity, no asset)', DEPOSIT],
            ['BUY of an asset the store does not know (no quote base)', BUY_UNKNOWN_ASSET],
            ['FX conversion giver (cash only)', FX_GIVER],
            ['FX conversion receiver (cash only)', FX_RECEIVER],
            ['asset transfer out (no cash)', TRANSFER_OUT],
            ['asset transfer in (no cash)', TRANSFER_IN],
            ['linked row with all the fields of a trade (a pair leg)', LEG_A],
            ['its linked partner (a pair leg)', LEG_B],
        ];
        for (const [what, tx] of rows) {
            expect(norm(unitPriceTd(tx.id).textContent), what).toBe('—');
            expect(screen.queryByTestId(`tx-unit-price-cell-${tx.id}`)?.textContent ?? '', `${what}: no price drawn`).not.toMatch(/\d/);
        }
        // Control: the column is drawn and the same table does price its trades, so the dashes above are decisions, not an empty column.
        expect(norm(priceCell(BUY.id).textContent)).toBe(clear.buy);
    });
});

describe('TransactionsTable — the price is public, the cash beside it is personal', () => {
    /** One step: the positive control first (the cash), so a red names its layer; the subject (the price) last. */
    function expectStep(step: string, privacyOn: boolean): void {
        expect(isPrivacyEnabled(), `${step} — control: the flag`).toBe(privacyOn);

        const cash = norm(screen.getByTestId(`tx-cash-cell-${BUY.id}`).textContent);
        if (privacyOn) {
            expect(cash, `${step} — positive control: the cash is masked`).toContain(P);
            expect(cash, `${step} — positive control: the masked cash shows no digit`).not.toMatch(/\d/);
        } else {
            expect(cash, `${step} — positive control: the cash is in the clear`).toBe(clear.buyCash);
        }

        for (const [tx, expected] of [
            [BUY, clear.buy],
            [SELL, clear.sell],
            [BOND_BUY, clear.bond],
        ] as const) {
            const text = norm(priceCell(tx.id).textContent);
            expect(text, `${step} — the price of tx #${tx.id} is public: as with privacy off`).toBe(expected);
            expect(text, `${step} — no placeholder in the price of tx #${tx.id}`).not.toContain(P);
        }
    }

    it('mounted in the clear, then toggled in place: the cash masks, the price keeps its digits, both read as before when it turns off', async () => {
        mount();
        await mounted();
        expectStep('mount, privacy off', false);

        await togglePrivacyInPlace();
        expectStep('off → on', true);

        await togglePrivacyInPlace();
        expectStep('on → off', false);
    });

    it('mounted with privacy already on: the price is there from the first render', async () => {
        setPrivacyEnabled(true);
        flushSync();
        mount();
        await mounted();
        expectStep('mount, privacy on', true);
    });
});

describe('TransactionsTable — the column can be hidden', () => {
    it('is visible by default; the table’s column-visibility control hides it and brings it back', async () => {
        const view = mount();
        await mounted();
        const tableRef = (view.component as unknown as {getTableRef: () => {getColumnsForVisibility: () => Array<{id: string; visible: boolean}>; toggleColumnVisibilityById: (id: string) => void} | undefined}).getTableRef();
        if (!tableRef) throw new Error('the table exposes no DataTable ref');

        const state = () => tableRef.getColumnsForVisibility().find((c) => c.id === 'unitPrice');
        expect(state(), 'the column is offered by the visibility control').toBeDefined();
        expect(state()?.visible, 'visible by default').toBe(true);
        expect(screen.getByTestId(`tx-unit-price-cell-${BUY.id}`)).toBeInTheDocument();
        // Control: the cash column is not the one that goes.
        expect(rowEl(BUY.id).querySelector('td[data-column-id="cash"]'), 'control: the cash column is drawn').not.toBeNull();

        tableRef.toggleColumnVisibilityById('unitPrice');
        await tick();
        expect(state()?.visible, 'hidden').toBe(false);
        expect(rowEl(BUY.id).querySelector('td[data-column-id="unitPrice"]'), 'no unitPrice cell once hidden').toBeNull();
        expect(screen.queryByTestId(`tx-unit-price-cell-${BUY.id}`)).toBeNull();
        expect(rowEl(BUY.id).querySelector('td[data-column-id="cash"]'), 'control: the cash column stays').not.toBeNull();

        tableRef.toggleColumnVisibilityById('unitPrice');
        await tick();
        expect(state()?.visible, 'back').toBe(true);
        expect(norm((await screen.findByTestId(`tx-unit-price-cell-${BUY.id}`)).textContent)).toBe(clear.buy);
    });
});
