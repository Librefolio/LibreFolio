// @vitest-environment jsdom
/**
 * L3RiskAdjusted — the portfolio's L3 on the Dashboard and a broker's page, mounted over the shared
 * `RiskReturnLevel` (Vitest + jsdom).
 *
 * What the developer approved in his visual reviews 3 and 4 (06/10/2026, «tutto perfetto»), pinned
 * where a DOM can show it — layout, colours and drags are the E2E's (`risk-analysis.spec.ts`):
 *
 *  - **the four cards are gone** («leviamo le 4 card perchè si assorbono nella tabella»): no
 *    `risk-l3-sortino`, `-sharpe`, `-volatility` or `-beta` card, no `risk-l3-metrics` grid and no
 *    `risk-l3-beta-benchmark` — their figures are the table's portfolio row, and the perimeter they
 *    stated is said once, in the title over the table: `risk.levels.l3.scatter.title` · the perimeter;
 *  - **the references open the table**: the portfolio first (`ref-portfolio`, added, its name cell
 *    `risk-l3-row-ref-name` with `data-reference="portfolio"` after a round role mark); a benchmark
 *    nobody holds second (`ref-<id>`, `data-reference="benchmark"`, a diamond mark); then the holdings,
 *    heaviest first. A benchmark the reader holds is no added row: its holding's row moves up second,
 *    keeps `risk-l3-row-*` and its asset id, takes the mark, and its beta and correlation are the dash
 *    that says it is the benchmark itself. `data-row-count` counts assets, `data-reference-count` the
 *    added rows;
 *  - **each figure from its own part of the payload**: the portfolio's volatility and return from its
 *    dot's pair (`asset_risk_return`), its Sortino and Sharpe from the KPI the level drew, its beta and
 *    correlation from `comparison`. A benchmark nobody holds has no weight, and its dash says so
 *    (`risk.levels.l3.table.notHeld`). A ratio the payload does not carry is a plain dash with no
 *    tooltip (`data-calculated="false"`), while a figure measured and not measurable keeps its explained
 *    dash;
 *  - **the columns**: the weight always, beta and correlation only with a measured benchmark; the
 *    return's title is the short `risk.levels.l3.table.expectedReturnShort`, its full name the column
 *    menu's `displayName` and the first line of its title's tooltip (`risk.levels.l3.table.namedHelp`);
 *    every figure column opens exactly as wide as its title (`width` = `min-width`), a longer title
 *    wider — jsdom has no canvas, so the component measures by letters and so does the relation here;
 *  - **one selection** for the table and the chart: the portfolio's row is the `portfolio` dot, an added
 *    benchmark's row the `benchmark` dot, an asset's row its `asset-<id>` dot, both ways;
 *  - **the notes under the chart (T10)**: one idea per line, in reading order — not plotted, above the
 *    line, the return with its warning in bold, prices only, where the line comes from, a dot's size.
 *
 * **The scatter is a stand-in**, as in `AssetSetRiskReturnSection.test.ts`: `ScatterChart` draws through
 * ECharts, whose canvas jsdom does not implement. The stand-in records the props it is handed and keeps
 * the props object (`live`), whose getters answer with what the level hands the chart now.
 *
 * **Translated text is never written down.** Every sentence compared is resolved through `$_` from the
 * shipped catalogue at test time; the rest is testids, data attributes, roles and the figures this file
 * invented. Every figure and name below is invented here: nothing was read off a running backend.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';
import {tick, type ComponentProps} from 'svelte';
import {get} from 'svelte/store';

/**
 * Every mount of the stand-in scatter, with the props object itself (`live`): the compiled level hands
 * a reactive prop as a getter, so `live.selectedId` read after a click is what the chart is handed now.
 */
const scatter = vi.hoisted(() => {
    interface StandInProps {
        points: readonly {id: string; role?: string}[];
        testId?: string;
        selectedId?: string | null;
        onpointclick?: (pointId: string) => void;
    }
    const mounts: {testId: string | undefined; live: StandInProps}[] = [];
    function ScatterChartStandIn(anchor: ChildNode, props: StandInProps): void {
        mounts.push({testId: props.testId, live: props});
        const stand = document.createElement('div');
        stand.setAttribute('data-testid', props.testId ?? 'risk-return-scatter');
        anchor.before(stand);
    }
    return {mounts, ScatterChartStandIn};
});

vi.mock('$lib/components/charts/ScatterChart.svelte', () => ({default: scatter.ScatterChartStandIn}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor, within} from '$test/component';
import {_} from '$lib/i18n';
import type {RiskAnalyticResult} from '$lib/stores/risk/riskStore.svelte';
import L3RiskAdjusted from './L3RiskAdjusted.svelte';

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// Fixtures — invented
// ═══════════════════════════════════════════════════════════════════════════════════════════════

function result(instanceId: string, analyticCode: string, output: Record<string, unknown>, mode?: 'current_composition' | 'historical'): RiskAnalyticResult {
    return {instance_id: instanceId, analytic_code: analyticCode, status: 'ok', output, ...(mode ? {metadata: {mode}} : {})} as unknown as RiskAnalyticResult;
}

const ASSET_NAMES: Record<number, string> = {1: 'Invented holding A', 2: 'Invented holding B', 3: 'Invented holding C'};
const BENCHMARK_ID = 90;
const BENCHMARK_NAME = 'Invented index';

/**
 * The current-composition pair. The items are listed lightest first, so the table's heaviest-first
 * order is a decision and not the payload's. Holding 3 was measured on neither axis — `null`, not
 * absent — so it has a row and no dot. `excluded_weight` splits the 5% left out into cash and unpriced
 * holdings, so the "not plotted" note has both parts.
 */
const RISK_RETURN = result(
    'base-current_composition-asset_risk_return',
    'asset_risk_return',
    {
        kind: 'risk_return',
        portfolio_volatility: 0.118,
        portfolio_expected_annual_return: 0.071,
        cash_weight: 0.05,
        excluded_weight: 0.004,
        items: [
            {asset_id: 3, weight: 0.02, volatility: null, expected_annual_return: null},
            {asset_id: 2, weight: 0.35, volatility: 0.087, expected_annual_return: 0.041},
            {asset_id: 1, weight: 0.6, volatility: 0.152, expected_annual_return: 0.094},
        ],
    },
    'current_composition',
);
/** The KPI the level draws: its volatility deliberately not the pair's, so a row that read it shows it. */
const CURRENT_KPI = result('base-current_composition-historical_kpi', 'historical_kpi', {kind: 'kpi', volatility: 0.142, sharpe: 1.21, sortino: 1.68}, 'current_composition');
/** The other wave's KPI, which the level must not draw while the current one answered. */
const HISTORICAL_KPI = result('base-historical-historical_kpi', 'historical_kpi', {kind: 'kpi', volatility: 0.2, sharpe: 0.5, sortino: 0.7}, 'historical');
/** A benchmark nobody holds: its own figures, and the portfolio's beta and correlation against it. */
const COMPARISON_UNHELD = result('single-comparison', 'comparison', {kind: 'comparison', comparison_asset_id: BENCHMARK_ID, beta: 0.91, correlation: 0.62, comparison_volatility: 0.15, comparison_expected_annual_return: 0.058});
/** The lighter holding as the benchmark: held, so no row is added for it. */
const COMPARISON_HELD = result('single-comparison', 'comparison', {kind: 'comparison', comparison_asset_id: 2, beta: 0.91, correlation: 0.62, comparison_volatility: 0.09, comparison_expected_annual_return: 0.04});

/** What the portfolio's row draws, worked out by hand from the figures above. */
const PORTFOLIO_DRAWN = {weight: '100.0%', volatility: '11.8%', expectedReturn: '+7.1%', sortino: '1.68', sharpe: '1.21', beta: '0.91', correlation: '0.62'};

type Props = ComponentProps<typeof L3RiskAdjusted>;

const BASE: Props = {
    historicalResults: [HISTORICAL_KPI],
    currentResults: [RISK_RETURN, CURRENT_KPI],
    comparisonResult: null,
    benchmarkName: null,
    assetNames: ASSET_NAMES,
    assetIcons: new Map([[1, '/icons/asset-types/stock.png']]),
    appliedRiskFreePercent: 2,
};
const WITH_UNHELD: Props = {...BASE, comparisonResult: COMPARISON_UNHELD, benchmarkName: BENCHMARK_NAME};
const WITH_HELD: Props = {...BASE, comparisonResult: COMPARISON_HELD, benchmarkName: ASSET_NAMES[2]};

// ═══════════════════════════════════════════════════════════════════════════════════════════════
// Harness
// ═══════════════════════════════════════════════════════════════════════════════════════════════

/** Mount with `tableRef` bound the way `bind:tableRef` binds it: through a setter Svelte calls. */
function mount(props: Props): {tableRef: Props['tableRef']} {
    const bound: {tableRef: Props['tableRef']} = {tableRef: undefined};
    render(L3RiskAdjusted, {
        props: {
            ...props,
            get tableRef() {
                return bound.tableRef;
            },
            set tableRef(value: Props['tableRef']) {
                bound.tableRef = value;
            },
        },
    });
    return bound;
}

function t(key: string, values?: Record<string, string>): string {
    const message = get(_)(key, values ? {values} : undefined);
    expect(message, `premise: ${key} resolves to a message, not to itself`).not.toBe(key);
    return message;
}

function normalize(text: string | null | undefined): string {
    return (text ?? '').replace(/\s+/g, ' ').trim();
}

function table(): HTMLElement {
    return screen.getByTestId('risk-l3-table');
}

/** The row ids top to bottom, as DataTable publishes them. */
function drawnOrder(): string[] {
    return [...table().querySelectorAll<HTMLElement>('tbody tr[data-row-id]')].map((row) => row.dataset.rowId ?? '');
}

function rowById(rowId: string): HTMLElement {
    const rows = table().querySelectorAll<HTMLElement>(`tbody tr[data-row-id="${rowId}"]`);
    expect(rows, `no row of its own for ${rowId}`).toHaveLength(1);
    return rows[0];
}

/** One value cell of a row: an added row's cells are `-ref-`, an asset's are not. */
function cellOf(rowId: string, column: string): HTMLElement {
    const testId = rowId.startsWith('ref-') ? `risk-l3-row-ref-${column}` : `risk-l3-row-${column}`;
    const cells = within(rowById(rowId)).getAllByTestId(testId);
    expect(cells, `${rowId}: ${column} must be one cell`).toHaveLength(1);
    return cells[0];
}

function headerOrder(): string[] {
    return [...table().querySelectorAll<HTMLElement>('thead th[data-testid^="dt-header-"]')].map((header) => (header.dataset.testid ?? '').replace('dt-header-', ''));
}

/** The trigger the project's Tooltip draws around a cell (`role="button"`), between the figure and its `td`, or `null`. */
function explainerOf(cell: HTMLElement): HTMLElement | null {
    const td = cell.closest('td');
    const trigger = cell.closest<HTMLElement>('[role="button"]');
    return td !== null && trigger !== null && trigger !== td && td.contains(trigger) ? trigger : null;
}

/** Open a cell's explanation with a click, read it, and close it again. */
async function explanationOf(cell: HTMLElement): Promise<string> {
    expect(explainerOf(cell), 'the dash is bare: it must sit in the project’s Tooltip').not.toBeNull();
    await fireEvent.click(cell);
    const help = await screen.findByRole('tooltip');
    const text = normalize(help.textContent);
    await waitFor(() => expect(help).toHaveAttribute('data-dismissable', 'true'));
    await fireEvent.click(document.body);
    await waitFor(() => expect(screen.queryByRole('tooltip')).toBeNull());
    return text;
}

/** The selection as every row states it: `rowId` the one selected row, or `null`. */
function expectSelected(rowId: string | null, why: string): void {
    const order = drawnOrder();
    expect(order.length, `${why}: barrier — the table has rows`).toBeGreaterThan(0);
    for (const id of order) expect(rowById(id), `${why} — row ${id}`).toHaveAttribute('data-selected', id === rowId ? 'true' : 'false');
}

/** What the level hands the one scatter it drew, as it stands now. */
function handedToScatter(): (typeof scatter.mounts)[number]['live'] {
    const mounts = scatter.mounts.filter((mount) => mount.testId === 'risk-l3-scatter');
    expect(mounts, 'barrier: the level drew one scatter').toHaveLength(1);
    return mounts[0].live;
}

const storage = new Map<string, string>();

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    scatter.mounts.length = 0;
    storage.clear();
    // DataTable keeps widths and order in localStorage: a fresh store per case, so no case inherits a layout.
    vi.stubGlobal('localStorage', {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => void storage.set(key, value),
        removeItem: (key: string) => void storage.delete(key),
    });
});

afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
});

// ═══════════════════════════════════════════════════════════════════════════════════════════════

describe('L3RiskAdjusted — the four cards are the portfolio’s row now', () => {
    it('draws the table, and none of the cards that used to stand above it', () => {
        mount(WITH_UNHELD);

        // Presence first: the level drew its table with the portfolio's row, so the absences are about a level that rendered.
        expect(table()).toBeInTheDocument();
        expect(drawnOrder()).toContain('ref-portfolio');

        const cardTestIds = [...document.querySelectorAll<HTMLElement>('[data-testid]')].map((node) => node.dataset.testid ?? '').filter((testId) => /^risk-l3-(metrics|sortino|sharpe|volatility|beta)(-|$)/.test(testId));
        expect(cardTestIds, 'a card of the old L3 survived: its figure is the portfolio row’s now').toEqual([]);
    });
});

describe('L3RiskAdjusted — the title names the question and the perimeter', () => {
    it('reads «question · perimeter», the perimeter of the KPI the level drew', () => {
        mount(BASE);

        const heading = within(screen.getByTestId('risk-l3')).getByRole('heading', {level: 4});
        expect(normalize(heading.textContent)).toBe(normalize(`${t('risk.levels.l3.scatter.title')} · ${t('risk.levels.l3.perimeter.current_composition')}`));
    });

    it('asks the question alone when no measurement declared its perimeter', () => {
        const undeclared = result('base-current_composition-historical_kpi', 'historical_kpi', {kind: 'kpi', volatility: 0.142, sharpe: 1.21, sortino: 1.68});
        mount({...BASE, currentResults: [RISK_RETURN, undeclared]});

        expect(screen.getByTestId('risk-l3'), 'premise: no perimeter declared').toHaveAttribute('data-perimeter', '');
        const heading = within(screen.getByTestId('risk-l3')).getByRole('heading', {level: 4});
        expect(normalize(heading.textContent)).toBe(normalize(t('risk.levels.l3.scatter.title')));
    });
});

describe('L3RiskAdjusted — the references open the table', () => {
    it('the portfolio first, marked as itself; the benchmark nobody holds second; then the holdings, heaviest first', () => {
        mount(WITH_UNHELD);

        expect(drawnOrder()).toEqual(['ref-portfolio', `ref-${BENCHMARK_ID}`, '1', '2', '3']);
        expect(table(), 'one row per asset: an added reference is not an asset').toHaveAttribute('data-row-count', '3');
        expect(table(), 'the portfolio and the benchmark nobody holds were added').toHaveAttribute('data-reference-count', '2');

        const portfolioName = within(rowById('ref-portfolio')).getByTestId('risk-l3-row-ref-name');
        expect(portfolioName).toHaveAttribute('data-reference', 'portfolio');
        expect(portfolioName.firstElementChild, 'the round mark comes before the portfolio’s name').toHaveAttribute('data-role-mark', 'portfolio');
        expect(normalize(portfolioName.textContent), 'the mark has no text: the cell reads as the name alone').toBe(normalize(t('risk.levels.l3.scatter.portfolio')));

        const benchmarkName = within(rowById(`ref-${BENCHMARK_ID}`)).getByTestId('risk-l3-row-ref-name');
        expect(benchmarkName).toHaveAttribute('data-reference', 'benchmark');
        expect(benchmarkName.firstElementChild, 'the diamond comes before the benchmark’s name').toHaveAttribute('data-role-mark', 'benchmark');
        expect(normalize(benchmarkName.textContent)).toBe(BENCHMARK_NAME);

        // The holdings are plain asset rows: their own cells, no mark, no reference.
        for (const assetId of [1, 2, 3]) {
            const name = within(rowById(String(assetId))).getByTestId('risk-l3-row-name');
            expect(name).toHaveAttribute('data-asset-id', String(assetId));
            expect(name.querySelector('[data-role-mark]'), `holding ${assetId} carries a role mark`).toBeNull();
            expect(within(rowById(String(assetId))).queryAllByTestId(/^risk-l3-row-ref-/), `holding ${assetId} has a reference’s cells`).toHaveLength(0);
        }
    });

    it('a benchmark the reader holds keeps its holding’s row and cells, moves up second, and its beta and correlation are not applicable', async () => {
        mount(WITH_HELD);

        // Holding 2 weighs less than holding 1, so second place is the benchmark's, not its weight's.
        expect(drawnOrder()).toEqual(['ref-portfolio', '2', '1', '3']);
        expect(table()).toHaveAttribute('data-row-count', '3');
        expect(table(), 'only the portfolio was added: the benchmark is one of the holdings').toHaveAttribute('data-reference-count', '1');

        const held = rowById('2');
        const name = within(held).getByTestId('risk-l3-row-name');
        expect(name, 'the held benchmark keeps its asset cell').toHaveAttribute('data-asset-id', '2');
        expect(name.firstElementChild, 'and takes the benchmark’s mark').toHaveAttribute('data-role-mark', 'benchmark');
        expect(within(held).queryAllByTestId(/^risk-l3-row-ref-/), 'a held benchmark takes no reference cells').toHaveLength(0);
        expect(cellOf('2', 'weight'), 'its weight is the holding’s').toHaveTextContent('35.0%');

        for (const column of ['beta', 'correlation']) {
            const cell = cellOf('2', column);
            expect(cell, `${column}: measured against itself, not applicable`).toHaveAttribute('data-reference', 'true');
            expect(cell).toHaveAttribute('data-measured', 'false');
        }
        expect(await explanationOf(cellOf('2', 'beta'))).toBe(normalize(t('risk.assetSet.levels.l3.referenceItself')));
    });
});

describe('L3RiskAdjusted — each figure from the part of the payload it belongs to', () => {
    it('the portfolio’s row: the weight of the whole, its dot’s pair, the drawn KPI’s ratios, the comparison’s beta and correlation', () => {
        mount(WITH_UNHELD);

        for (const [column, drawn] of Object.entries(PORTFOLIO_DRAWN)) {
            const cell = cellOf('ref-portfolio', column);
            expect(normalize(cell.textContent), `the portfolio’s ${column}`).toBe(drawn);
            expect(cell).toHaveAttribute('data-measured', 'true');
        }
    });

    it('a benchmark nobody holds has no weight, and its dash says why', async () => {
        mount(WITH_UNHELD);

        const weight = cellOf(`ref-${BENCHMARK_ID}`, 'weight');
        expect(normalize(weight.textContent)).toBe('\u2014');
        expect(weight).toHaveAttribute('data-held', 'false');
        expect(weight).toHaveAttribute('data-measured', 'false');
        expect(await explanationOf(weight)).toBe(normalize(t('risk.levels.l3.table.notHeld')));

        // Its own figures are the comparison's, measured on beta's calendar.
        expect(normalize(cellOf(`ref-${BENCHMARK_ID}`, 'volatility').textContent)).toBe('15.0%');
        expect(normalize(cellOf(`ref-${BENCHMARK_ID}`, 'expectedReturn').textContent)).toBe('+5.8%');
    });

    it('a ratio the payload does not carry is a plain dash with no tooltip; a figure measured and not measurable keeps its explained dash', async () => {
        mount(WITH_UNHELD);

        // No holding carries its Sortino or Sharpe yet, nor a beta of its own: not calculated here.
        for (const assetId of ['1', '2']) {
            for (const column of ['sortino', 'sharpe', 'beta', 'correlation']) {
                const cell = cellOf(assetId, column);
                expect(normalize(cell.textContent), `holding ${assetId}: ${column}`).toBe('\u2014');
                expect(cell, `holding ${assetId}: ${column} is not calculated here`).toHaveAttribute('data-calculated', 'false');
                expect(explainerOf(cell), `holding ${assetId}: ${column} claims, in a tooltip, a measurement nobody attempted`).toBeNull();
            }
        }

        // Holding 3 was measured and could not be: its dash explains itself, and says nothing of "not calculated".
        const unmeasured = cellOf('3', 'volatility');
        expect(normalize(unmeasured.textContent)).toBe('\u2014');
        expect(unmeasured).toHaveAttribute('data-measured', 'false');
        expect(unmeasured, 'a measured blank is not a ratio left uncalculated').not.toHaveAttribute('data-calculated');
        expect(await explanationOf(unmeasured)).toBe(normalize(t('risk.assetSet.levels.blankNote')));
    });
});

describe('L3RiskAdjusted — the columns', () => {
    it('the weight always; beta and correlation only with a measured benchmark', () => {
        mount(BASE);
        expect(headerOrder()).toEqual(['name', 'weight', 'volatility', 'expectedReturn', 'sortino', 'sharpe']);
        cleanup();

        mount(WITH_UNHELD);
        expect(headerOrder()).toEqual(['name', 'weight', 'volatility', 'expectedReturn', 'sortino', 'sharpe', 'beta', 'correlation']);
    });

    it('the return’s title is short, its tooltip opens with the full name, and the column menu lists the full name', async () => {
        const bound = mount(BASE);
        const fullName = t('risk.assetSet.levels.l3.expectedReturn');

        expect(normalize(screen.getByTestId('dt-sort-expectedReturn').textContent), 'the title is the short name').toBe(normalize(t('risk.levels.l3.table.expectedReturnShort')));

        const columns = (bound.tableRef as {getColumnsForVisibility?: () => {id: string; displayName?: string | (() => string)}[]} | undefined)?.getColumnsForVisibility?.();
        expect(columns, 'tableRef is not the DataTable instance: the column menu would have nothing to read').toBeDefined();
        const listed = columns?.find((column) => column.id === 'expectedReturn')?.displayName;
        expect(typeof listed === 'function' ? listed() : listed, 'the column menu names the return in full').toBe(fullName);

        await fireEvent.click(screen.getByTestId('dt-sort-expectedReturn'));
        const help = await screen.findByRole('tooltip');
        expect((help.textContent ?? '').split('\n')[0].trim(), 'the tooltip opens with the full name, on its own line').toBe(fullName);
        expect(normalize(help.textContent)).toBe(normalize(t('risk.levels.l3.table.namedHelp', {name: fullName, help: t('risk.assetSet.levels.l3.columnHelp.expectedReturn')})));
    });

    it('every figure column opens exactly as wide as its title, and a longer title opens a wider one', () => {
        mount(WITH_UNHELD);

        const columns = ['weight', 'volatility', 'expectedReturn', 'sortino', 'sharpe', 'beta', 'correlation'].map((column) => {
            const header = screen.getByTestId(`dt-header-${column}`);
            return {column, width: parseFloat(header.style.width), minWidth: parseFloat(header.style.minWidth), letters: normalize(screen.getByTestId(`dt-sort-${column}`).textContent).length};
        });
        for (const {column, width, minWidth} of columns) {
            expect(Number.isFinite(width), `${column}: no width of its own`).toBe(true);
            expect(minWidth, `${column}: it may shrink below its title, or start wider than it`).toBe(width);
        }
        // jsdom has no canvas, so the level measures a title by its letters: more letters, a wider column.
        for (const left of columns) {
            for (const right of columns) {
                expect(Math.sign(left.width - right.width), `${left.column} (${left.letters} letters) against ${right.column} (${right.letters})`).toBe(Math.sign(left.letters - right.letters));
            }
        }
    });
});

describe('L3RiskAdjusted — one selection, in the table and on the chart', () => {
    it('the portfolio’s row and the portfolio’s dot are one selection, both ways', async () => {
        mount(WITH_UNHELD);
        const handed = handedToScatter();
        expect(handed.selectedId, 'nothing selected on opening').toBeNull();

        await fireEvent.click(cellOf('ref-portfolio', 'volatility'));
        expectSelected('ref-portfolio', 'a click on the portfolio’s row selects it');
        expect(handed.selectedId, 'and marks the portfolio’s dot').toBe('portfolio');

        handed.onpointclick?.('portfolio');
        await tick();
        expectSelected(null, 'a click on the selected portfolio dot clears it, as a second click on its row does');
        expect(handed.selectedId).toBeNull();

        handed.onpointclick?.('portfolio');
        await tick();
        expectSelected('ref-portfolio', 'a click on the portfolio dot selects the portfolio’s row');
        expect(handed.selectedId).toBe('portfolio');
    });

    it('the benchmark’s dot selects its added row, and an asset’s dot its row', async () => {
        mount(WITH_UNHELD);
        const handed = handedToScatter();
        expect(
            handed.points.map((point) => point.id),
            'premise: the benchmark nobody holds is a dot of its own',
        ).toContain('benchmark');

        handed.onpointclick?.('benchmark');
        await tick();
        expectSelected(`ref-${BENCHMARK_ID}`, 'the benchmark dot selects the benchmark’s row');
        expect(handed.selectedId).toBe('benchmark');

        handed.onpointclick?.('asset-1');
        await tick();
        expectSelected('1', 'an asset’s dot moves the selection to its row');
        expect(handed.selectedId).toBe('asset-1');
    });
});

describe('L3RiskAdjusted — the notes under the chart, one idea per line (T10)', () => {
    /** The notes' lines, top to bottom. */
    function noteLines(): HTMLElement[] {
        return [...screen.getByTestId('risk-l3-scatter-note').children].map((child) => {
            expect(child.tagName, 'every note is a line of the list').toBe('LI');
            return child as HTMLElement;
        });
    }

    it('in reading order: not plotted, above the line, the return and its warning, prices only, the line through the benchmark, a dot’s size', () => {
        mount(WITH_UNHELD);
        const lines = noteLines();

        expect(lines, 'six ideas, six lines').toHaveLength(6);
        expect(lines[0]).toHaveAttribute('data-testid', 'risk-l3-scatter-outside');
        expect(within(lines[0]).getByTestId('risk-l3-scatter-cash'), 'cash is not plotted').toBeInTheDocument();
        expect(within(lines[0]).getByTestId('risk-l3-scatter-unpriced'), 'nor are the unpriced holdings').toBeInTheDocument();
        expect(normalize(lines[1].textContent)).toBe(normalize(t('risk.levels.l3.scatter.notes.above')));
        expect(normalize(lines[2].textContent)).toBe(normalize(`${t('risk.levels.l3.scatter.notes.expected')} ${t('risk.levels.l3.scatter.notes.expectedWarning')}`));
        const warning = lines[2].querySelector('strong');
        expect(normalize(warning?.textContent), 'the warning is the part in bold').toBe(normalize(t('risk.levels.l3.scatter.notes.expectedWarning')));
        expect(lines[3]).toHaveAttribute('data-testid', 'risk-l3-scatter-price-only');
        expect(normalize(lines[3].textContent)).toBe(normalize(t('risk.levels.l3.scatter.notes.priceOnly')));
        expect(lines[4]).toHaveAttribute('data-testid', 'risk-l3-scatter-line');
        expect(lines[4], 'a benchmark is placed: the line runs through it').toHaveAttribute('data-anchor', 'benchmark');
        expect(normalize(lines[4].textContent)).toBe(normalize(t('risk.levels.l3.scatter.notes.lineBenchmark')));
        expect(normalize(lines[5].textContent)).toBe(normalize(t('risk.levels.l3.scatter.notes.size')));
    });

    it('with no benchmark, the line through the portfolio, in the same place', () => {
        mount(BASE);
        const lines = noteLines();

        expect(lines).toHaveLength(6);
        expect(lines[4]).toHaveAttribute('data-anchor', 'portfolio');
        expect(normalize(lines[4].textContent)).toBe(normalize(t('risk.levels.l3.scatter.notes.line')));
    });
});
