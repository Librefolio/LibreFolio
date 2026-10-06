// @vitest-environment jsdom
/**
 * TornadoChart — component test (Vitest + jsdom), checkpoint k5b (D376).
 *
 * The rows of a replay or of a shock used to be bars with one number beside them: the drawn
 * value, a percent, then the money. D376 turns them into a table, with the bar kept as its last
 * column. The props do not change (`rows`, `label`, `amount`, `testId`); what the rows carry does
 * (`ownReturn` and `contribution`, pinned by `scenarioHelpers.test.ts`), and so does the shape.
 *
 * What is pinned here:
 *
 *   1. **A DataTable, used as is.** The container `data-testid={testId}` wraps the shared
 *      `DataTable`; its headers are `dt-header-{id}`, in the fixed order asset, weight, return,
 *      contribution, impact, bar. No selection, no row actions, no column filters, no column
 *      menu, and no paging: every row is drawn, past the ten of a page. The table is identified
 *      row by row by the row's key (`getRowId = row.key`, published by DataTable as
 *      `data-row-id`).
 *   2. **A column with nothing to say is not drawn.** Weight, return, contribution and impact are
 *      dropped when no row has a value for them; asset and bar always stay. A weighted replay
 *      shows all six, the Asset Global lab (no weights, no money) shows asset, return and bar, a
 *      shock by bucket has no money column. One value in one row is enough to keep a column.
 *   3. **The figures, each in its column.** The weight as `formatReplayShare` writes it; the
 *      return and the contribution signed, with two decimals, as `Intl.NumberFormat` writes them
 *      in the reader's language (`signDisplay: 'exceptZero'`); the money verbatim, as the caller's
 *      `amount` words it. Every expected string is computed here with the same helper or the same
 *      `Intl` options, in `$currentLanguage`; nothing is written down.
 *   4. **The rows.** In the order given — the caller's, worst first — one `{testId}-row` element
 *      per row, in the asset column, carrying `data-row-key` and the caller's label. An asset row
 *      shows the icon the asset cache knows, else a fallback; a bucket row shows none. The cache
 *      is read and never loaded: the page that mounts the table owns loading it.
 *   5. **The bars.** One per row, in the bar column, drawn on one scale for every row — the
 *      largest magnitude present, gains and losses alike — so their lengths are proportional to
 *      |value|; signed `loss` below zero and `gain` from zero up.
 *
 * **Guards and reds.** Several cases are green before k5b and must stay green after it: they pin
 * what the rewrite must not lose — nothing drawn for no rows, the order given, one bar per row on
 * one scale, its sign. Their lookups go from a row's own element to its bar, so they read the old
 * list and the new table alike. Every other case is red until the table lands.
 *
 * **Handles.** `data-testid` (the component's and DataTable's own `dt-header-*`), `data-row-key`,
 * `data-row-id`, `data-sign`, an icon's `src`, and a bar's declared width — read as a ratio, never
 * as a length, because jsdom lays nothing out. No class is read. A cell is found by its header's
 * position in the header row, never by a fixed index. The only sentences read are the column
 * headers, each resolved from the shipped catalogue through the same `$_`; the harness case says
 * the keys exist, so that a missing key echoed back on both sides cannot pass for a header.
 *
 * Not pinned, for want of a stable handle: the zero line (drawn, but published by nothing), and
 * column resizing and `storageKey` (DataTable's own markup and storage; this jsdom build has no
 * `localStorage`, so DataTable's preferences no-op here — `DataTable.test.ts` says the same).
 *
 * Left elsewhere: which rows a payload yields and their order (`scenarioHelpers.test.ts`), the
 * replay block around the table (`L4Replay.test.ts`, which reads the same `{testId}-row` handles),
 * and the table on a real page (`portfolio/risk-analysis.spec.ts`, `portfolio/risk-lab.spec.ts`).
 *
 * ⚠️ Every name, figure and icon below is invented.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick} from 'svelte';
import {get} from 'svelte/store';

// The asset cache, read for the icons: the real cache, seeded per test through `mergeAssets` and
// emptied after each. Only its two loaders are stubbed — so a read that turned into a load is
// counted, and never reaches the network.
vi.mock('$lib/stores/reference/assetStore', async (importOriginal) => ({
    ...(await importOriginal<typeof import('$lib/stores/reference/assetStore')>()),
    ensureAssetsLoaded: vi.fn(async () => undefined),
    refreshAllAssets: vi.fn(async () => undefined),
}));

import {render, screen, setupI18n, within} from '$test/component';
import {_, locale, SUPPORTED_LOCALES, type SupportedLocale} from '$lib/i18n';
import en from '$lib/i18n/en.json';
import es from '$lib/i18n/es.json';
import fr from '$lib/i18n/fr.json';
import itCatalogue from '$lib/i18n/it.json';
import {currentLanguage} from '$lib/stores/app/language';
import {ensureAssetsLoaded, mergeAssets, refreshAllAssets, resetAssetStore, type AssetInfo} from '$lib/stores/reference/assetStore';
import TornadoChart from './TornadoChart.svelte';
import {formatReplayShare, type TornadoRow} from './scenarioHelpers';

/** A row as `tornadoRows` hands it over since k5b: its own return and its contribution beside the value it is drawn by. */
type Row = TornadoRow & {ownReturn: number | null; contribution: number | null};

const TEST_ID = 'probe-tornado';

/** The table's columns, in their fixed order. */
const COLUMNS = ['asset', 'weight', 'return', 'contribution', 'impact', 'bar'] as const;
type ColumnId = (typeof COLUMNS)[number];
/** The columns that hold a figure under a testid of their own. */
type FigureColumn = 'weight' | 'return' | 'contribution' | 'impact';
const FIGURE_COLUMNS: readonly FigureColumn[] = ['weight', 'return', 'contribution', 'impact'];

const HEADER_KEYS: Readonly<Record<ColumnId, string>> = {
    asset: 'risk.levels.l4.table.asset',
    weight: 'risk.levels.l4.table.weight',
    return: 'risk.levels.l4.table.return',
    contribution: 'risk.levels.l4.table.contribution',
    impact: 'risk.levels.l4.table.impact',
    bar: 'risk.levels.l4.table.bar',
};

const CATALOGUES: Record<SupportedLocale, unknown> = {en, it: itCatalogue, fr, es};

/** The names the page knows. The cache, when it names an asset, names it otherwise (see the icon case). */
const NAMES: Readonly<Record<number, string>> = {
    7: 'Synthetic Holding A',
    9: 'Synthetic Holding B',
    11: 'Synthetic Holding C',
    13: 'Synthetic Holding D',
};

/**
 * A portfolio replay, worst first as `tornadoRows` gives it: weighted, with money. Holding A's
 * contribution is twice Holding C's — the pair the scale is checked on.
 */
const WEIGHTED: readonly Row[] = [
    {key: 'asset:7', assetId: 7, value: -0.08, ownReturn: -0.2, contribution: -0.08, amount: -1600, weight: 0.4},
    {key: 'asset:11', assetId: 11, value: -0.04, ownReturn: -0.16, contribution: -0.04, amount: -800, weight: 0.25},
    {key: 'asset:9', assetId: 9, value: 0.01, ownReturn: 0.05, contribution: 0.01, amount: 200, weight: 0.2},
];

/** The Asset Global lab: a selection carries no weights, so no contribution and no money — the bar is the asset's own return. */
const LAB: readonly Row[] = [
    {key: 'asset:7', assetId: 7, value: -0.2, ownReturn: -0.2, contribution: null, amount: null, weight: null},
    {key: 'asset:9', assetId: 9, value: 0.05, ownReturn: 0.05, contribution: null, amount: null, weight: null},
];

/** A shock by asset class: buckets carry an exposure, a shock and a contribution, and no money. */
const BUCKETS: readonly Row[] = [
    {key: 'bucket:STOCK', bucketId: 'STOCK', value: -0.12, ownReturn: -0.2, contribution: -0.12, amount: null, weight: 0.6},
    {key: 'bucket:BOND', bucketId: 'BOND', value: -0.015, ownReturn: -0.05, contribution: -0.015, amount: null, weight: 0.3},
    {key: 'bucket:CRYPTO', bucketId: 'CRYPTO', value: 0.01, ownReturn: 0.1, contribution: 0.01, amount: null, weight: 0.1},
];

/** Each optional column has a value in one row only: enough to keep it. */
const PARTIAL: readonly Row[] = [
    {key: 'asset:7', assetId: 7, value: -0.08, ownReturn: null, contribution: -0.08, amount: -1600, weight: 0.4},
    {key: 'asset:9', assetId: 9, value: 0.05, ownReturn: 0.05, contribution: null, amount: null, weight: null},
];

/**
 * Four rows given in an order that is no natural one — not by value, magnitude, key, id or label,
 * either way — so an order on screen equal to it can only be the order given.
 */
const SHUFFLED: readonly Row[] = [
    {key: 'asset:11', assetId: 11, value: -0.04, ownReturn: -0.16, contribution: -0.04, amount: -800, weight: 0.25},
    {key: 'asset:7', assetId: 7, value: -0.08, ownReturn: -0.2, contribution: -0.08, amount: -1600, weight: 0.4},
    {key: 'asset:9', assetId: 9, value: 0.01, ownReturn: 0.05, contribution: 0.01, amount: 200, weight: 0.2},
    {key: 'asset:13', assetId: 13, value: -0.02, ownReturn: -0.1, contribution: -0.02, amount: -400, weight: 0.2},
];

/** Twelve rows, worst first: two more than DataTable's default page. */
const TWELVE: readonly Row[] = Array.from({length: 12}, (_unused, index) => {
    const value = -0.12 + index * 0.01;
    return {key: `asset:${101 + index}`, assetId: 101 + index, value, ownReturn: value * 4, contribution: value, amount: value * 20_000, weight: 0.25};
});

/** Row label, as a caller resolves it: the page's name for an asset, the bucket's id for a bucket. */
function labelOf(row: TornadoRow): string {
    return row.assetId !== undefined ? (NAMES[row.assetId] ?? `#${row.assetId}`) : (row.bucketId ?? '');
}

/** Money, as a caller words it: a string the table could not have produced itself, so "verbatim" is checkable. */
function amountOf(row: TornadoRow): string {
    return row.amount === null ? '' : `${row.amount < 0 ? '−' : '+'}${Math.abs(row.amount).toFixed(2)} SYN`;
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

/** A catalogue sentence as the component words it: `$_`. Never a literal. */
function t(key: string): string {
    return normalize(get(_)(key));
}

function at(catalogue: unknown, key: string): unknown {
    return key.split('.').reduce<unknown>((node, part) => (node !== null && typeof node === 'object' ? (node as Record<string, unknown>)[part] : undefined), catalogue);
}

/** The language the table formats in. The harness proves the two stores that could carry it agree. */
function lang(): string {
    return get(currentLanguage);
}

/** A return or a contribution as the table writes it: pinned against `Intl` itself, with the contract's options. */
function signedPercent(value: number, language = lang()): string {
    return normalize(new Intl.NumberFormat(language, {style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2, signDisplay: 'exceptZero'}).format(value));
}

/** A weight as the table writes it: the replay block's own share formatter. */
function share(fraction: number, language = lang()): string {
    return normalize(formatReplayShare(fraction, language));
}

interface MountOptions {
    /** The caller's money; `null` mounts the table with no `amount` at all. Defaults to {@link amountOf}. */
    amount?: ((row: TornadoRow) => string) | null;
}

/** The table, mounted alone with props only; its container. */
function mount(rows: readonly Row[], {amount}: MountOptions = {}): HTMLElement {
    const props = {rows: [...rows], label: labelOf, testId: TEST_ID, ...(amount === null ? {} : {amount: amount ?? amountOf})};
    render(TornadoChart, {props});
    return screen.getByTestId(TEST_ID);
}

/** The column ids the table heads, in its order — read off DataTable's header cells, never off a tooltip trigger. */
function headers(root: HTMLElement): string[] {
    return [...root.querySelectorAll('th[data-testid^="dt-header-"]')].map((header) => (header.getAttribute('data-testid') ?? '').slice('dt-header-'.length));
}

/** The barrier every column case stands on: the table is there, with exactly these columns, in this order. */
function expectColumns(root: HTMLElement, columns: readonly ColumnId[], why: string): void {
    expect(root.querySelector('table'), 'the container wraps no table: the rows are not drawn as a DataTable (D376)').not.toBeNull();
    expect(headers(root), why).toEqual(columns);
}

/** The rows' keys, in the order on screen. */
function rowKeys(root: HTMLElement): string[] {
    return within(root)
        .queryAllByTestId(`${TEST_ID}-row`)
        .map((row) => row.getAttribute('data-row-key') ?? '');
}

/** A row's own element, which must be exactly one. */
function rowMarker(root: HTMLElement, key: string): HTMLElement {
    const markers = root.querySelectorAll<HTMLElement>(`[data-testid="${TEST_ID}-row"][data-row-key="${key}"]`);
    expect(markers, `row ${key} must be drawn by exactly one ${TEST_ID}-row element`).toHaveLength(1);
    return markers[0];
}

/** The table row a row's element lives in. */
function tableRowOf(root: HTMLElement, key: string): HTMLTableRowElement {
    const row = rowMarker(root, key).closest('tr');
    if (!row || !root.contains(row)) throw new Error(`row ${key} is not drawn as a row of the table`);
    return row;
}

/** A row's cell under a column, found through the header's position in the header row — never a fixed index. */
function cellOf(root: HTMLElement, key: string, column: ColumnId): HTMLElement {
    const header = root.querySelector(`th[data-testid="dt-header-${column}"]`);
    if (!header?.parentElement) throw new Error(`the table has no ${column} column; it heads ${JSON.stringify(headers(root))}`);
    const index = [...header.parentElement.children].indexOf(header);
    const cell = tableRowOf(root, key).children[index];
    if (!(cell instanceof HTMLElement) || cell.tagName !== 'TD') throw new Error(`row ${key} has no cell under the ${column} header`);
    return cell;
}

/** The figure a row shows in one column, as written. */
function figureOf(root: HTMLElement, key: string, column: FigureColumn): string {
    const figure = within(cellOf(root, key, column)).queryByTestId(`${TEST_ID}-${column}`);
    if (!figure) throw new Error(`row ${key}: the ${column} cell holds no ${TEST_ID}-${column} figure`);
    return normalize(figure.textContent);
}

/**
 * A row's bar: the one bar in the nearest box around the row's own element — the list item
 * before k5b, the table row after it — so the guards below read both shapes alike.
 */
function barOf(root: HTMLElement, key: string): HTMLElement {
    for (let node: HTMLElement | null = rowMarker(root, key); node && root.contains(node); node = node.parentElement) {
        const bars = node.querySelectorAll<HTMLElement>(`[data-testid="${TEST_ID}-bar"]`);
        if (bars.length === 1) return bars[0];
        if (bars.length > 1) break;
    }
    throw new Error(`row ${key} has no bar of its own`);
}

/** A bar's declared width, in whatever unit it declares — only ever compared with another bar's. */
function widthOf(bar: HTMLElement, key: string): number {
    const width = Number.parseFloat(bar.style.width || bar.getAttribute('width') || '');
    if (!Number.isFinite(width)) throw new Error(`the bar of ${key} declares no width (style ${JSON.stringify(bar.getAttribute('style'))}): its length cannot be compared with the others`);
    return width;
}

/** The pictures in a cell: images and top-level SVGs (an icon component is one SVG, however many paths it holds). */
function picturesIn(cell: Element): string[] {
    return [...cell.querySelectorAll('img, svg')].filter((node) => node.parentElement?.closest('svg') == null).map((node) => (node.tagName.toLowerCase() === 'img' ? `img ${node.getAttribute('src') ?? ''}` : node.tagName.toLowerCase()));
}

beforeAll(async () => {
    await setupI18n();
});

beforeEach(() => {
    vi.mocked(ensureAssetsLoaded).mockClear();
    vi.mocked(refreshAllAssets).mockClear();
});

afterEach(() => {
    resetAssetStore();
});

describe('TornadoChart — the harness itself', () => {
    it('formats in the language the catalogue speaks, and the formats tell the languages apart', () => {
        // The figures are formatted in a language the table reads from a store; the two stores
        // that could carry it agree, so the expectations do not depend on which one it reads.
        expect(lang(), 'the app language and the catalogue locale disagree: a figure could be formatted in one and headed in the other').toBe(get(locale));
        // The language case below would agree with a table that ignored the language, were the
        // two languages to write these figures alike; they do not.
        expect(signedPercent(-0.2, 'it'), 'premise: Italian writes a signed percent otherwise than English').not.toBe(signedPercent(-0.2, 'en'));
        expect(share(0.4, 'it'), 'premise: Italian writes a share otherwise than English').not.toBe(share(0.4, 'en'));
    });

    it('has the six column headers in every catalogue, six different words', () => {
        // One line per key and locale, so a red names every sentence that is missing.
        const missing = SUPPORTED_LOCALES.flatMap((code) => COLUMNS.filter((column) => typeof at(CATALOGUES[code], HEADER_KEYS[column]) !== 'string').map((column) => `${code}: ${HEADER_KEYS[column]}`));
        expect(missing, 'the table’s column headers are missing from these catalogues (k5b adds risk.levels.l4.table.*)').toEqual([]);
        // svelte-i18n echoes the id back on a miss, and so would the table: both sides would then
        // "agree" on a key that does not exist.
        for (const column of COLUMNS) expect(t(HEADER_KEYS[column]), `${HEADER_KEYS[column]} does not resolve: the catalogue is not loaded`).not.toBe(HEADER_KEYS[column]);
        // Two columns headed alike could not be told apart by the reader, nor by the case below.
        expect(new Set(COLUMNS.map((column) => t(HEADER_KEYS[column]))).size, 'two columns share a header').toBe(COLUMNS.length);
    });
});

describe('TornadoChart — nothing to draw', () => {
    it('renders nothing at all for no rows: no container, no table, no header (guard)', () => {
        const {container} = render(TornadoChart, {props: {rows: [], label: labelOf, amount: amountOf, testId: TEST_ID}});

        expect(screen.queryByTestId(TEST_ID), 'an empty answer drew a container').toBeNull();
        expect(container.querySelector('*'), 'an empty answer drew an element — an empty table, a header, a placeholder').toBeNull();
        expect(ensureAssetsLoaded, 'an empty table asked the asset cache to load').not.toHaveBeenCalled();
    });
});

describe('TornadoChart — a table, its columns in a fixed order (k5b)', () => {
    it('draws a weighted replay as a DataTable with all six columns, in order', () => {
        const root = mount(WEIGHTED);

        expectColumns(root, COLUMNS, 'a weighted replay has a value for every column, so it must head all six, in the fixed order');
    });

    it.each([
        ['an amount that is always empty', () => ''],
        ['no amount at all', null],
    ] as const)('draws the Asset Global lab — no weight, no contribution, %s — as the asset, its return and the bar', (_case, amount) => {
        const root = mount(LAB, {amount});

        expectColumns(root, ['asset', 'return', 'bar'], 'a selection with no weights and no money has nothing to say under weight, contribution and impact: those columns are not drawn');
        for (const column of ['weight', 'contribution', 'impact'] as const) {
            expect(within(root).queryAllByTestId(`${TEST_ID}-${column}`), `a ${column} figure is drawn though no row has one`).toEqual([]);
        }
        for (const row of LAB) expect(figureOf(root, row.key, 'return'), `the return of ${row.key} is not its own return, signed with two decimals`).toBe(signedPercent(row.ownReturn ?? Number.NaN));
    });

    it('draws a shock by bucket without the money column, which no bucket carries', () => {
        const root = mount(BUCKETS);

        expectColumns(root, ['asset', 'weight', 'return', 'contribution', 'bar'], 'every bucket’s amount is empty, so the impact column is not drawn — and only that one');
        expect(within(root).queryAllByTestId(`${TEST_ID}-impact`), 'an impact figure is drawn though no bucket has money').toEqual([]);
    });

    it('keeps a column as soon as one row has a value for it', () => {
        const root = mount(PARTIAL);

        expectColumns(root, COLUMNS, 'each optional column has a value in one row: one value is enough to keep a column');
        expect(figureOf(root, 'asset:7', 'weight')).toBe(share(0.4));
        expect(figureOf(root, 'asset:7', 'contribution')).toBe(signedPercent(-0.08));
        expect(figureOf(root, 'asset:7', 'impact')).toBe(amountOf(PARTIAL[0]));
        expect(figureOf(root, 'asset:9', 'return')).toBe(signedPercent(0.05));
    });

    it('heads each column with its own sentence', () => {
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        for (const column of COLUMNS) {
            const header = root.querySelector(`th[data-testid="dt-header-${column}"]`);
            expect(normalize(header?.textContent), `the ${column} column is not headed by ${HEADER_KEYS[column]}`).toContain(t(HEADER_KEYS[column]));
        }
    });

    it('is the plain table: no selection, no row actions, no column filters, no column menu and no paging — every row drawn, past the ten of a page', () => {
        const root = mount(TWELVE);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        expect(rowKeys(root), 'not every row is drawn, in the order given: the table pages (DataTable shows ten per page by default)').toEqual(TWELVE.map((row) => row.key));
        const single = ['dt-select-all', 'dt-show-selected-only', 'data-table-pagination', 'column-visibility-toggle'].filter((testId) => within(root).queryAllByTestId(testId).length > 0);
        expect(single, 'the table offers a control D376 does not give it').toEqual([]);
        const families = ['dt-row-checkbox-', 'row-actions-', 'col-filter-trigger-'].filter((prefix) => root.querySelector(`[data-testid^="${prefix}"]`) !== null);
        expect(families, 'the table offers per-row selection, row actions or column filters').toEqual([]);
    });
});

describe('TornadoChart — the rows', () => {
    it('keeps the order it is given — neither by value, magnitude, key nor label (guard)', () => {
        const root = mount(SHUFFLED);

        expect(rowKeys(root), 'the table re-ordered the rows: the order is the caller’s, worst first, and the table must not sort them again').toEqual(SHUFFLED.map((row) => row.key));
    });

    it('draws each row’s element in the asset column of a table row identified by its key, named by the caller', () => {
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        expect(rowKeys(root)).toEqual(WEIGHTED.map((row) => row.key));
        for (const row of WEIGHTED) {
            const marker = rowMarker(root, row.key);
            expect(cellOf(root, row.key, 'asset').contains(marker), `the element of ${row.key} is not in the asset column`).toBe(true);
            expect(tableRowOf(root, row.key), `the table does not identify the row of ${row.key} by its key (getRowId = row.key)`).toHaveAttribute('data-row-id', row.key);
            expect(normalize(marker.textContent), `${row.key} is not named by the caller’s label`).toContain(labelOf(row));
        }
    });

    it('writes each figure in its column: the weight as a share, the return and the contribution signed with two decimals, the money verbatim', () => {
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        for (const row of WEIGHTED) {
            expect(figureOf(root, row.key, 'weight'), `the weight of ${row.key} is not written as formatReplayShare writes it`).toBe(share(row.weight ?? Number.NaN));
            expect(figureOf(root, row.key, 'return'), `the return of ${row.key} is not its own return, signed with two decimals`).toBe(signedPercent(row.ownReturn ?? Number.NaN));
            expect(figureOf(root, row.key, 'contribution'), `the contribution of ${row.key} is not signed with two decimals`).toBe(signedPercent(row.contribution ?? Number.NaN));
            expect(figureOf(root, row.key, 'impact'), `the money of ${row.key} is not the caller’s, verbatim`).toBe(amountOf(row));
        }
    });

    it('writes the figures in the reader’s language', async () => {
        await setupI18n('it');
        currentLanguage.set('it');
        try {
            const root = mount(WEIGHTED);
            expectColumns(root, COLUMNS, 'barrier: the six columns');

            for (const row of WEIGHTED) {
                expect(figureOf(root, row.key, 'weight'), `the weight of ${row.key} is not written in Italian`).toBe(share(row.weight ?? Number.NaN, 'it'));
                expect(figureOf(root, row.key, 'return'), `the return of ${row.key} is not written in Italian`).toBe(signedPercent(row.ownReturn ?? Number.NaN, 'it'));
                expect(figureOf(root, row.key, 'contribution'), `the contribution of ${row.key} is not written in Italian`).toBe(signedPercent(row.contribution ?? Number.NaN, 'it'));
            }
        } finally {
            currentLanguage.set('en');
            await setupI18n('en');
        }
    });

    it('draws an asset with the icon the asset cache knows, else a fallback — reading the cache, never loading it', () => {
        const icon = '/synthetic-icons/holding-a.svg';
        const cache: AssetInfo[] = [
            // Named otherwise than the page names it: the row's name is the caller's label.
            {id: 7, display_name: 'Synthetic Holding A, as the cache names it', currency: 'EUR', asset_type: 'STOCK', icon_url: icon, active: true},
            // Known, with no icon of its own.
            {id: 9, display_name: 'Synthetic Holding B, as the cache names it', currency: 'EUR', asset_type: 'ETF', icon_url: null, active: true},
        ];
        mergeAssets(cache);
        // Holding C (11) is unknown to the cache.
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        expect(picturesIn(cellOf(root, 'asset:7', 'asset')), 'an asset the cache knows is not drawn with the cache’s icon, alone').toEqual([`img ${icon}`]);
        for (const key of ['asset:9', 'asset:11']) {
            const pictures = picturesIn(cellOf(root, key, 'asset'));
            expect(pictures, `${key} has no icon of its own in the cache, and must be drawn with one fallback picture`).toHaveLength(1);
            expect(pictures, `${key} is drawn with another asset’s icon`).not.toContain(`img ${icon}`);
        }
        for (const row of WEIGHTED) expect(normalize(rowMarker(root, row.key).textContent), `${row.key} is not named by the caller’s label`).toContain(labelOf(row));
        expect(ensureAssetsLoaded, 'the table asked the asset cache to load: it reads it, and the page that mounts it loads it').not.toHaveBeenCalled();
        expect(refreshAllAssets, 'the table asked the asset cache to reload').not.toHaveBeenCalled();
    });

    it('draws the icon the asset cache learns after the table is on screen', async () => {
        // Every risk surface reads the cache through `$assetStoreVersion`, because the pages load
        // it without waiting: a table drawn before the load lands must not keep its fallbacks.
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');
        const before = picturesIn(cellOf(root, 'asset:7', 'asset'));
        expect(before, 'premise: an asset unknown to the cache is drawn with one fallback picture').toHaveLength(1);

        const icon = '/synthetic-icons/holding-a-late.svg';
        mergeAssets([{id: 7, display_name: NAMES[7], currency: 'EUR', asset_type: 'STOCK', icon_url: icon, active: true}]);
        await tick();

        expect(picturesIn(cellOf(root, 'asset:7', 'asset')), 'the table kept its fallback after the cache learned the icon: it read the cache once, not reactively').toEqual([`img ${icon}`]);
        expect(ensureAssetsLoaded, 'the table asked the asset cache to load').not.toHaveBeenCalled();
    });

    it('draws no picture for a bucket: a bucket has no icon', () => {
        // The positive control is the case above: the same reader finds an asset's icon.
        const root = mount(BUCKETS);
        expectColumns(root, ['asset', 'weight', 'return', 'contribution', 'bar'], 'barrier: a bucket table');

        for (const row of BUCKETS) {
            expect(normalize(rowMarker(root, row.key).textContent), `${row.key} is not named by the caller’s label`).toContain(labelOf(row));
            expect(picturesIn(cellOf(root, row.key, 'asset')), `${row.key} is a bucket and is drawn with a picture`).toEqual([]);
        }
        expect(ensureAssetsLoaded, 'a bucket table asked the asset cache to load').not.toHaveBeenCalled();
    });
});

describe('TornadoChart — the bars', () => {
    it('draws every bar on one scale, the largest magnitude present, gains and losses alike (guard)', () => {
        // The widest bar is the largest magnitude, whichever its sign; every other bar is that
        // fraction of it. Holding A's −8% is twice Holding C's −4%, and eight times B's +1%.
        const root = mount(WEIGHTED);

        expect(rowKeys(root), 'barrier: the rows are drawn').toEqual(WEIGHTED.map((row) => row.key));
        const widths = Object.fromEntries(WEIGHTED.map((row) => [row.key, widthOf(barOf(root, row.key), row.key)]));
        const largest = Math.max(...WEIGHTED.map((row) => Math.abs(row.value)));
        const widest = Math.max(...Object.values(widths));
        for (const row of WEIGHTED) {
            expect(widths[row.key] / widest, `the bar of ${row.key} is not |value| / largest |value| of the widest: the bars are not on one shared scale`).toBeCloseTo(Math.abs(row.value) / largest, 3);
        }
        expect(widths['asset:7'] / widths['asset:11'], 'a contribution twice another is not drawn twice as long').toBeCloseTo(2, 3);
    });

    it('draws the value — here the contribution — and not the own return (guard)', () => {
        // Holding B fell 50% on its own and Holding A 10%; weighted, A cost the scope more. The
        // bars follow what the holdings did to the scope, so A's is the longer.
        const rows: Row[] = [
            {key: 'asset:7', assetId: 7, value: -0.08, ownReturn: -0.1, contribution: -0.08, amount: -1600, weight: 0.8},
            {key: 'asset:9', assetId: 9, value: -0.05, ownReturn: -0.5, contribution: -0.05, amount: -1000, weight: 0.1},
        ];
        const root = mount(rows);

        expect(rowKeys(root), 'barrier: the rows are drawn').toEqual(rows.map((row) => row.key));
        const ratio = widthOf(barOf(root, 'asset:9'), 'asset:9') / widthOf(barOf(root, 'asset:7'), 'asset:7');
        expect(ratio, 'the bars are drawn by the own return, not by the value').toBeCloseTo(0.05 / 0.08, 3);
    });

    it('signs every bar: a loss below zero, a gain above, and a flat row a gain (guard)', () => {
        const rows: Row[] = [
            {key: 'asset:7', assetId: 7, value: -0.04, ownReturn: -0.1, contribution: -0.04, amount: -800, weight: 0.4},
            {key: 'asset:13', assetId: 13, value: 0, ownReturn: 0, contribution: 0, amount: 0, weight: 0.2},
            {key: 'asset:9', assetId: 9, value: 0.02, ownReturn: 0.05, contribution: 0.02, amount: 400, weight: 0.4},
        ];
        const root = mount(rows);

        expect(rowKeys(root), 'barrier: the rows are drawn').toEqual(rows.map((row) => row.key));
        expect(
            rows.map((row) => barOf(root, row.key).getAttribute('data-sign')),
            'a bar is not signed by its value: loss below zero, gain from zero up',
        ).toEqual(['loss', 'gain', 'gain']);
    });

    it('draws a flat answer — every row at zero — at equal, finite lengths (guard)', () => {
        // One scale taken from a largest magnitude of zero must not divide by it.
        const rows: Row[] = [
            {key: 'asset:7', assetId: 7, value: 0, ownReturn: 0, contribution: 0, amount: 0, weight: 0.5},
            {key: 'asset:9', assetId: 9, value: 0, ownReturn: 0, contribution: 0, amount: 0, weight: 0.5},
        ];
        const root = mount(rows);

        const widths = rows.map((row) => widthOf(barOf(root, row.key), row.key));
        expect(widths.every(Number.isFinite), `a flat answer drew a bar of no finite length: ${JSON.stringify(widths)}`).toBe(true);
        expect(widths[0], 'two flat rows are drawn at different lengths').toBe(widths[1]);
    });

    it('puts each row’s bar in the bar column, the last one', () => {
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        for (const row of WEIGHTED) {
            expect(cellOf(root, row.key, 'bar').contains(barOf(root, row.key)), `the bar of ${row.key} is not in the bar column`).toBe(true);
        }
    });
});

describe('TornadoChart — figures stay figures', () => {
    it('writes no figure outside its own column', () => {
        // The figure testids are column-bound: a weight drawn under "return" would read as a return.
        const root = mount(WEIGHTED);
        expectColumns(root, COLUMNS, 'barrier: the six columns');

        for (const row of WEIGHTED) {
            for (const column of FIGURE_COLUMNS) {
                const placed = [...tableRowOf(root, row.key).querySelectorAll(`[data-testid="${TEST_ID}-${column}"]`)];
                expect(placed, `${row.key} must show exactly one ${column} figure`).toHaveLength(1);
                expect(cellOf(root, row.key, column).contains(placed[0]), `the ${column} figure of ${row.key} is outside the ${column} column`).toBe(true);
            }
        }
    });
});
