// @vitest-environment jsdom
/**
 * AssetTable — component test (Vitest + jsdom).
 *
 * Subjects: the F15 usage badge plus lifecycle filtering, ordering and the
 * inactive table/card treatments. Lifecycle is read from the state the
 * components publish — `data-lifecycle` on the table's status dot and on the
 * card root, the `asset-row-inactive` row marker — never from a colour class.
 * Only the F15 usage badge still reads class tokens, exceptionally: its tint IS
 * the feature, and it stays on palette classes until the categorical roles
 * come (AF-2). Behaviour is located by semantic attributes and deterministic
 * ids, never by position.
 *
 * The store loaders the component kicks off (`ensureCurrenciesLoaded`,
 * `ensureAssetProvidersCached`) are fail-soft by design, so a `$lib/api` mock
 * whose calls resolve to `undefined` leaves the table rendering with empty
 * reference caches — which is exactly the state under test: the badge depends
 * on `txScope`/`txCount` props alone.
 *
 * Also the names of the Δ columns — the fixed 1D one and the period ones —
 * which come from the catalogues: read in a marker locale on the
 * `dt-header-*` testids, never in a language.
 *
 * C-97c-3 (the last describe): a quote keeps its significant digits — the
 * table's Last Price column, the card's live price and its absolute Δ.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => undefined);
            },
        },
    ),
}));

import {get} from 'svelte/store';
import {addMessages} from 'svelte-i18n';
import {render, screen, setupI18n, waitFor, within} from '$test/component';
import {_ as t} from '$lib/i18n';
import {uiLocale} from '$lib/stores/app/uiLocale';
import en from '$lib/i18n/en.json';
import itCatalogue from '$lib/i18n/it.json';
import fr from '$lib/i18n/fr.json';
import es from '$lib/i18n/es.json';
import AssetCard from './AssetCard.svelte';
import AssetTable, {type AssetRow} from './AssetTable.svelte';
import {matchesAssetLifecycle, orderAssetsByLifecycle} from './assetLifecycle';

function row(id: number, txCount: number, txScope: AssetRow['txScope'], active = true): AssetRow {
    return {
        id,
        display_name: `Asset ${id}`,
        currency: 'EUR',
        asset_type: 'STOCK',
        active,
        txCount,
        txScope,
    };
}

/** The one row of the mounted table, by the id this test gave it. */
function rowEl(id: number): HTMLElement {
    const el = document.querySelector<HTMLElement>(`tbody tr[data-row-id="${id}"]`);
    if (!el) throw new Error(`row ${id} not rendered`);
    return el;
}

/** The badge span in the row's txCount cell, or null. */
function badgeIn(rowElement: HTMLElement): HTMLElement | null {
    return rowElement.querySelector<HTMLElement>('td.td-data span.font-mono');
}

/** The lifecycle each status dot of the row publishes (`span[data-lifecycle]`), in document order. */
function lifecycleDotsIn(rowElement: HTMLElement): Array<string | null> {
    return Array.from(rowElement.querySelectorAll('span[data-lifecycle]'), (dot) => dot.getAttribute('data-lifecycle'));
}

beforeAll(async () => {
    await setupI18n();
});

describe('asset lifecycle', () => {
    it.each([
        {
            label: 'active only',
            showActive: true,
            showInactive: false,
            expected: ['active'],
        },
        {
            label: 'inactive only',
            showActive: false,
            showInactive: true,
            expected: ['inactive'],
        },
        {
            label: 'both toggles form a union',
            showActive: true,
            showInactive: true,
            expected: ['active', 'inactive'],
        },
        {
            label: 'neither toggle means no lifecycle filter',
            showActive: false,
            showInactive: false,
            expected: ['active', 'inactive'],
        },
    ])('$label', ({showActive, showInactive, expected}) => {
        const assets = [
            {name: 'active', active: true},
            {name: 'inactive', active: false},
        ];

        expect(assets.filter((asset) => matchesAssetLifecycle(asset.active, showActive, showInactive)).map((asset) => asset.name)).toEqual(expected);
    });

    it('orders active assets first while preserving the prior name order within each group', () => {
        const nameOrdered = [
            {id: 1, name: 'Alpha inactive', active: false},
            {id: 2, name: 'Bravo active', active: true},
            {id: 3, name: 'Charlie active', active: true},
            {id: 4, name: 'Delta inactive', active: false},
        ];

        expect(orderAssetsByLifecycle(nameOrdered).map((asset) => asset.name)).toEqual(['Bravo active', 'Charlie active', 'Alpha inactive', 'Delta inactive']);
        expect(nameOrdered.map((asset) => asset.name)).toEqual(['Alpha inactive', 'Bravo active', 'Charlie active', 'Delta inactive']);
    });

    it('marks only the inactive table row and keeps both lifecycle status dots', async () => {
        render(AssetTable, {
            data: [row(21, 1, 'own'), row(22, 0, 'analysis', false)],
        });

        await waitFor(() => {
            expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(2);
        });

        const active = rowEl(21);
        const inactive = rowEl(22);
        expect(active).not.toHaveClass('asset-row-inactive');
        expect(inactive).toHaveClass('asset-row-inactive');
        // Exactly one status dot per row, publishing that row's lifecycle — so never the other one.
        expect(lifecycleDotsIn(active), 'active row: one dot, published active').toEqual(['active']);
        expect(lifecycleDotsIn(inactive), 'inactive row: one dot, published inactive').toEqual(['inactive']);
    });

    it('publishes the card lifecycle: active for an active asset, inactive for an inactive one', () => {
        render(AssetCard, {
            asset: {
                id: 31,
                display_name: 'Active card',
                currency: 'EUR',
                asset_type: 'STOCK',
                provider_code: null,
                active: true,
            },
        });
        render(AssetCard, {
            asset: {
                id: 32,
                display_name: 'Inactive card',
                currency: 'EUR',
                asset_type: 'STOCK',
                provider_code: null,
                active: false,
            },
        });

        const active = screen.getByTestId('asset-card-31');
        const inactive = screen.getByTestId('asset-card-32');
        expect(active).toHaveAttribute('data-lifecycle', 'active');
        expect(inactive).toHaveAttribute('data-lifecycle', 'inactive');
    });
});

describe('AssetTable — F15 usage badge', () => {
    it('tints the count by scope: own → emerald, others → blue, analysis → gray', async () => {
        render(AssetTable, {
            data: [row(1, 3, 'own'), row(2, 5, 'others'), row(3, 0, 'analysis')],
        });

        // Barrier: all three rows rendered before reading any badge.
        await waitFor(() => {
            expect(document.querySelectorAll('tbody tr[data-row-id]')).toHaveLength(3);
        });

        const own = badgeIn(rowEl(1));
        const others = badgeIn(rowEl(2));
        const analysis = badgeIn(rowEl(3));
        expect(own, 'own badge missing').not.toBeNull();
        expect(others, 'others badge missing').not.toBeNull();
        expect(analysis, 'analysis badge missing').not.toBeNull();

        expect(own!.className).toContain('bg-emerald-100');
        expect(others!.className).toContain('bg-blue-100');
        expect(analysis!.className).toContain('bg-gray-100');

        // The number the badge carries is the total tx count, whatever the scope.
        expect(own!.textContent?.trim()).toBe('3');
        expect(others!.textContent?.trim()).toBe('5');
        expect(analysis!.textContent?.trim()).toBe('0');
    });

    it('renders the badge with a zero count when txScope is omitted entirely', async () => {
        // Rows built before the F15 fields existed (or from a partial payload)
        // have neither txCount nor txScope: the cell must still render, gray,
        // rather than crash the column.
        render(AssetTable, {data: [row(9, 0, undefined)]});

        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="9"]')).not.toBeNull());
        const badge = badgeIn(rowEl(9));
        expect(badge).not.toBeNull();
        expect(badge!.className).toContain('bg-gray-100');
        expect(badge!.textContent?.trim()).toBe('0');
    });
});

describe('AssetTable — the Δ period columns are labelled from the catalogues (T, duration labels)', () => {
    // The Δ columns are headed with their period's key — `Δ 1D` for the fixed column, `Δ 3M` for the
    // period ones: English unit letters in every language. The contract is the date picker's and the
    // rolling window's, through the helper the asset and FX tables share (`deltaPeriodLabel`): `Δ ` and
    // then `datePicker.presets.days`, `.weeks`, `.months` or `.years` with the period's count as n.
    //
    // Observed without reading a language, in a marker locale: every key of the English catalogue reads
    // as a marker of itself (`⟦common.name⟧`) and each count key as a marker of itself and its n
    // (`⟦datePicker.presets.days n=1⟧`), so a header taken from the catalogue reads its marker and a
    // literal written in the code reads as itself. The Name header is the control: it already comes from
    // the catalogue. The marker locale registers the count keys itself, so whether the four catalogues
    // carry them — `days` is new — is asked of the JSON files, in the first case.
    //
    // Red today: the columns are headed `Δ 1D`, `Δ 3M` and `Δ 2Y`.

    /** A private-use language (BCP 47 reserves qaa–qtz): Intl accepts it, and it is none of the app's catalogues. */
    const MARKER_LOCALE = 'qaa';
    const CATALOGUES: Record<string, unknown> = {en, it: itCatalogue, fr, es};
    /** The count keys a Δ header reads, one per unit letter of a period key: D, W, M and Y. */
    const UNIT_KEYS = ['datePicker.presets.days', 'datePicker.presets.weeks', 'datePicker.presets.months', 'datePicker.presets.years'];

    /** How a label reads in the marker locale: `⟦key⟧`, or `⟦key n=3⟧` for a message given values. */
    const marked = (key: string, values: Record<string, string | number> = {}): string => `⟦${[key, ...Object.entries(values).map(([name, value]) => `${name}=${value}`)].join(' ')}⟧`;

    /** The value behind a dotted key of a catalogue, if any. */
    const leafOf = (catalogue: unknown, key: string): unknown => key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);

    /** Every dotted key of a catalogue that holds a string. */
    function stringKeysOf(node: unknown, prefix = ''): string[] {
        if (typeof node === 'string') return [prefix];
        if (node === null || typeof node !== 'object') return [];
        return Object.entries(node).flatMap(([part, child]) => stringKeysOf(child, prefix ? `${prefix}.${part}` : part));
    }

    /** Switch svelte-i18n to the marker locale: every key of the English catalogue reads as its marker, and each key of `counted` as its marker with the names of its values. */
    async function useMarkerLocale(counted: Record<string, readonly string[]>): Promise<void> {
        const messages: Record<string, string> = Object.fromEntries(stringKeysOf(en).map((key) => [key, marked(key)]));
        for (const [key, names] of Object.entries(counted)) messages[key] = marked(key, Object.fromEntries(names.map((name) => [name, `{${name}}`])));
        addMessages(MARKER_LOCALE, messages);
        await setupI18n(MARKER_LOCALE);
    }

    /** The text of a column's header, found by the `dt-header-<column id>` testid DataTable publishes. */
    const headerText = (columnId: string): string | undefined => screen.getByTestId(`dt-header-${columnId}`).textContent?.trim();

    /** Mount the table with one row and `visiblePeriods`, in the marker locale, and check that the locale is live. */
    async function mountMarked(visiblePeriods: ReadonlyArray<{key: string; days: number}> = []): Promise<void> {
        render(AssetTable, {data: [row(41, 2, 'own')], visiblePeriods});
        await waitFor(() => expect(document.querySelector('tbody tr[data-row-id="41"]')).not.toBeNull());
        expect(headerText('name'), 'control: a header the table already takes from the catalogue reads its marker').toBe(marked('common.name'));
    }

    beforeEach(async () => {
        await useMarkerLocale(Object.fromEntries(UNIT_KEYS.map((key) => [key, ['n']])));
    });

    afterEach(async () => {
        await setupI18n('en');
    });

    it('the four catalogues have days, weeks, months and years, each showing its count through {n}', () => {
        const gaps = UNIT_KEYS.flatMap((key) =>
            Object.entries(CATALOGUES).flatMap(([lang, catalogue]) => {
                const message = leafOf(catalogue, key);
                return typeof message === 'string' && message.includes('{n}') ? [] : [`${lang}: ${key}`];
            }),
        );

        expect(gaps, 'a count key missing from a catalogue, or without its {n}').toEqual([]);
    });

    it('heads the fixed 1D column Δ datePicker.presets.days n=1, with no period column visible', async () => {
        expect(get(t)('datePicker.presets.days', {values: {n: 1}}), 'control: the marker locale reads a count message called as the contract says').toBe(marked('datePicker.presets.days', {n: 1}));
        await mountMarked();

        expect(headerText('delta_1D')).toBe(`Δ ${marked('datePicker.presets.days', {n: 1})}`);
    });

    it('heads the 3M and 2Y columns Δ datePicker.presets.months n=3 and Δ datePicker.presets.years n=2', async () => {
        expect(get(t)('datePicker.presets.months', {values: {n: 3}}), 'control: the marker locale reads a count message called as the contract says').toBe(marked('datePicker.presets.months', {n: 3}));
        /** Two period columns as the page hands them to the table (`visiblePeriods`): the key and days of two of the backend's periods. */
        const periods = [
            {key: '3M', days: 91},
            {key: '2Y', days: 730},
        ];
        await mountMarked(periods);

        expect(Object.fromEntries(periods.map(({key}) => [key, headerText(`delta_${key}`)]))).toEqual({
            '3M': `Δ ${marked('datePicker.presets.months', {n: 3})}`,
            '2Y': `Δ ${marked('datePicker.presets.years', {n: 2})}`,
        });
    });
});

/**
 * C-97c-3 (decision D-C97c-1 of the coordinator, 17/10): a price on screen keeps its significant digits.
 *
 * The asset list writes a quote with two fixed decimals in three places: the table's Last Price column
 * (`formatCurrencyAmountHtml(price, row.currency, {sensitivity: 'public'})`), the card's live price
 * (`formatFixed(Number(livePrice), 2)`) and the card's absolute Δ over the range (`asset-range-delta`,
 * `data-mode="absolute"`: `formatFixed(Number(deltaAbs), 2, {signed: true})`). A token quoted 0.0000034573 USD reads
 * `0.00`, one quoted 1.234 reads `1.23`, a Δ of 1.2e-7 `+0.00`. The contract: the column keeps its formatter, given
 * `{minFraction, maxFraction}` from `priceFractionDigits(price)`; the card's price is `formatPrice(livePrice)` and its Δ
 * `formatPrice(deltaAbs, {signed: true})` — two decimals at least, as many as the first four significant digits need
 * (`priceFractionDigits`, formatFixed.ts), a `+` on a rise and no sign on a zero.
 *
 * Reds: 0.0000034573 and 1.234 in the column and on the card (today `0.00` and `1.23`), the card's Δ of 1.2e-7 and of
 * -0.0000012 (today `+0.00` and `-0.00`). Guards, green today and after: 123.45 in the column and on the card, Δs of 1.5
 * (`+1.50`), -12.5 (`-12.50`) and 0 (`0.00`).
 *
 * Reading. The column's cell: in the row of the id this test gave it (`data-row-id`), the cell DataTable stamps with
 * the column's id (`data-column-id="lastPrice"`). The card's live price has no handle of its own: it is read in its
 * card (`asset-card-<id>`), mounted with no Δ, no transaction count and no chart, so the price is the only figure there.
 * The card's Δ: `asset-range-delta`, its mode checked. Each figure is matched as a whole number token, since the cell
 * and the card also hold the currency. English UI on jsdom's en-US browser, checked before each case: the digits are
 * typed.
 */
describe('AssetTable and AssetCard — a price keeps its significant digits (C-97c-3, D-C97c-1)', () => {
    /** `digits` as a whole number in a text: no digit, decimal mark, group separator or sign glued to either side. */
    function numberToken(digits: string): RegExp {
        return new RegExp(`(?<![\\d.,+\\-\\u2212])${digits.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(?![.,]?\\d)`);
    }

    /** A table row of this block: asset `id`, quoted `lastPrice` USD. */
    function quoted(id: number, lastPrice: number): AssetRow {
        return {...row(id, 0, 'analysis'), currency: 'USD', lastPrice};
    }

    /** Mount the table on `rows` and wait for each of them. */
    async function mountTable(rows: AssetRow[]): Promise<void> {
        render(AssetTable, {data: rows});
        await waitFor(() => {
            for (const {id} of rows) expect(document.querySelector(`tbody tr[data-row-id="${id}"]`), `barrier: row ${id} is rendered`).not.toBeNull();
        });
    }

    /** The Last Price cell of row `id`, as text. */
    function lastPriceOf(id: number): string {
        const cell = rowEl(id).querySelector<HTMLElement>('td[data-column-id="lastPrice"]');
        if (!cell) throw new Error(`row ${id} has no lastPrice cell`);
        return (cell.textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    /** Mount the card of asset `id` (USD, manual, active) with `props`, and return its root. */
    function mountCard(id: number, props: {livePrice?: number | null; deltaAbs?: number | null; globalViewMode?: 'percentage' | 'absolute'}): HTMLElement {
        render(AssetCard, {asset: {id, display_name: 'Quoted asset', currency: 'USD', asset_type: 'STOCK', provider_code: null, active: true}, ...props});
        return screen.getByTestId(`asset-card-${id}`);
    }

    /** The card's text: its live price is the only figure in it when it is mounted with no Δ. */
    function livePriceCardText(id: number, livePrice: number): string {
        return (mountCard(id, {livePrice}).textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    /** The card's absolute Δ over the range, as text: `asset-range-delta`, checked to be in the absolute mode. */
    function absoluteDeltaOf(id: number, deltaAbs: number): string {
        const delta = within(mountCard(id, {deltaAbs, globalViewMode: 'absolute'})).getByTestId('asset-range-delta');
        expect(delta, 'barrier: the Δ shown is the absolute one').toHaveAttribute('data-mode', 'absolute');
        return (delta.textContent ?? '').replace(/\s+/g, ' ').trim();
    }

    beforeEach(() => {
        // The expected digits are typed: the premise that the list writes en-US, checked.
        expect(uiLocale(), 'control: an English UI on jsdom’s en-US browser is written en-US').toBe('en-US');
    });

    it('the Last Price column: 0.0000034573 USD reads 0.000003457 and 1.234 USD reads 1.234, not 0.00 and 1.23', async () => {
        await mountTable([quoted(61, 0.0000034573), quoted(62, 1.234)]);

        expect.soft(lastPriceOf(61), 'a quote of 0.0000034573 USD (today 0.00)').toMatch(numberToken('0.000003457'));
        expect.soft(lastPriceOf(62), 'a quote of 1.234 USD (today 1.23)').toMatch(numberToken('1.234'));
    });

    it('guard: the Last Price column still reads 123.45 for 123.45 USD', async () => {
        await mountTable([quoted(63, 123.45)]);

        expect(lastPriceOf(63)).toMatch(numberToken('123.45'));
    });

    it('the card’s live price: 0.0000034573 reads 0.000003457 and 1.234 reads 1.234, not 0.00 and 1.23', () => {
        expect.soft(livePriceCardText(71, 0.0000034573), 'a live price of 0.0000034573 (today 0.00)').toMatch(numberToken('0.000003457'));
        expect.soft(livePriceCardText(72, 1.234), 'a live price of 1.234 (today 1.23)').toMatch(numberToken('1.234'));
    });

    it('the card’s absolute Δ over the range: +1.2e-7 reads +0.00000012 and -0.0000012 reads -0.0000012, not +0.00 and -0.00', () => {
        expect.soft(absoluteDeltaOf(81, 1.2e-7), 'a rise of 1.2e-7 (today +0.00)').toMatch(numberToken('+0.00000012'));
        expect.soft(absoluteDeltaOf(82, -0.0000012), 'a fall of 1.2e-6 (today -0.00)').toMatch(numberToken('-0.0000012'));
    });

    it('guard: the card’s live price 123.45 reads 123.45; its Δs of 1.5, -12.5 and 0 read +1.50, -12.50 and 0.00', () => {
        expect.soft(livePriceCardText(73, 123.45), 'the live price').toMatch(numberToken('123.45'));
        expect.soft(absoluteDeltaOf(83, 1.5), 'a Δ of 1.5').toMatch(numberToken('+1.50'));
        expect.soft(absoluteDeltaOf(84, -12.5), 'a Δ of -12.5').toMatch(numberToken('-12.50'));
        expect.soft(absoluteDeltaOf(85, 0), 'a Δ of 0, no sign').toMatch(numberToken('0.00'));
    });
});
