// @vitest-environment jsdom
/**
 * RiskReturnLevel — the table pages after five rows (B8, developer 05/10/2026 and 31/10/2026; Vitest + jsdom).
 *
 * «Nella tabella metti la paginazione se ci sono più di 5 righe» (05/10), widened on 31/10: pagination in every table of the risk
 * and correlation surfaces, with «all» among the sizes, because the reader who does not want pages sets it to infinite.
 *
 * Pinned, on test ids and data attributes, never on a translated sentence:
 *
 * - six rows draw five and a pagination bar; five rows draw all five and no bar; the page-size menu offers 5, 10, 25 and all (0);
 *   choosing «all» draws every row. `data-row-count` stays the number of assets, drawn or not;
 * - a click on a dot whose row is on another page takes the table to that page and selects the row, and the view does not move:
 *   the chart that was clicked sits under the table (D-B8b);
 * - the reference rows (the portfolio, a benchmark nobody holds) open the table while it is neither sorted nor filtered, and once
 *   the reader sorts they sort like any other row, so one may land on the second page (D-B8d, «tenute in cima senza filtri o
 *   ordinamenti; ordinate o filtrate si comportano come le altre»).
 *
 * The chart is a stand-in that hands the test its `onpointclick`: ECharts is not the subject.
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

const scatter = vi.hoisted(() => {
    const live: {onpointclick?: (pointId: string) => void} = {};
    function ScatterChartStandIn(anchor: ChildNode, props: {onpointclick?: (pointId: string) => void; testId?: string}): void {
        live.onpointclick = props.onpointclick;
        const stand = document.createElement('div');
        stand.setAttribute('data-testid', props.testId ?? 'scatter');
        anchor.before(stand);
    }
    return {live, ScatterChartStandIn};
});
vi.mock('$lib/components/charts/ScatterChart.svelte', () => ({default: scatter.ScatterChartStandIn}));

import {cleanup, fireEvent, render, screen, setupI18n, waitFor} from '$test/component';

import RiskReturnLevel from './RiskReturnLevel.svelte';
import type {RiskReturnRow} from './riskReturnLevel';

const PREFIX = 'rrl';
const LABELS = {volatility: 'Volatility', return: 'Return', capitalMarketLine: 'CML'};

/** `count` asset rows, ids 1…count; the volatility rises with the id so a sort is predictable. */
function assets(count: number): RiskReturnRow[] {
    return Array.from({length: count}, (_, index) => ({assetId: index + 1, name: `Invented asset ${index + 1}`, volatility: 0.1 + index * 0.01, expectedReturn: 0.05}));
}

const PORTFOLIO: RiskReturnRow = {assetId: 0, name: 'Invented portfolio', volatility: 0.9, expectedReturn: 0.05, role: 'portfolio', added: true};
const BENCHMARK: RiskReturnRow = {assetId: 99, name: 'Invented benchmark', volatility: 0.5, expectedReturn: 0.05, role: 'benchmark', added: true};

let scroll: ReturnType<typeof vi.fn>;

beforeAll(async () => {
    await setupI18n('en');
});

beforeEach(() => {
    scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll as unknown as Element['scrollIntoView'];
});

afterEach(() => {
    cleanup();
});

function mount(rows: RiskReturnRow[], key: string) {
    const points = rows.map((row) => ({id: row.role === 'portfolio' ? 'portfolio' : row.added ? 'benchmark' : `asset-${row.assetId}`, name: row.name, volatility: row.volatility ?? 0, annualReturn: row.expectedReturn ?? 0, role: 'asset' as const}));
    return render(RiskReturnLevel, {props: {rows, points, capabilities: {}, assetIcons: new Map(), testIdPrefix: PREFIX, storageKey: key, labels: LABELS}});
}

/** The row ids on screen, in order. */
const shown = () => Array.from(document.querySelectorAll(`[data-testid="${PREFIX}-table"] tbody tr[data-row-id]`)).map((tr) => tr.getAttribute('data-row-id'));

describe('RiskReturnLevel — pagination after five rows (B8)', () => {
    it('draws five of six rows and a pagination bar', () => {
        mount(assets(6), 'rrl-six');

        expect(shown()).toEqual(['1', '2', '3', '4', '5']);
        expect(screen.queryByTestId('data-table-pagination'), 'six rows and no way to the sixth').not.toBeNull();
        expect(screen.getByTestId(`${PREFIX}-table`).getAttribute('data-row-count'), 'the asset count counts assets, not the rows drawn').toBe('6');
    });

    it('draws five rows of five with no pagination bar at all', () => {
        mount(assets(5), 'rrl-five');

        expect(shown()).toEqual(['1', '2', '3', '4', '5']);
        expect(screen.queryByTestId('data-table-pagination')).toBeNull();
    });

    it('offers 5, 10, 25 and all among the sizes, and «all» draws every row', async () => {
        mount(assets(12), 'rrl-all');

        await fireEvent.click(screen.getByTestId('pagination-size-trigger'));
        for (const size of [5, 10, 25, 0]) expect(screen.queryByTestId(`pagination-size-option-${size}`), `the size menu has no option ${size}`).not.toBeNull();
        await fireEvent.click(screen.getByTestId('pagination-size-option-0'));

        await waitFor(() => expect(shown()).toHaveLength(12));
    });

    it('takes the table to the page of a clicked dot, selects its row, and does not move the view (D-B8b)', async () => {
        mount(assets(12), 'rrl-click');
        expect(shown()).not.toContain('9');

        scatter.live.onpointclick?.('asset-9');

        await waitFor(() => expect(shown()).toContain('9'));
        expect(document.querySelector('tr[data-row-id="9"]')).toHaveAttribute('data-selected', 'true');
        // The scroll, if one were queued, lands after the page is drawn; a navigation asked afterwards is the barrier behind it.
        await fireEvent.click(screen.getByTestId('pagination-prev'));
        await waitFor(() => expect(shown()).toContain('1'));
        expect(scroll, 'the view moved to the row: the chart that was clicked is out of sight').not.toHaveBeenCalled();
    });
});

describe('RiskReturnLevel — the reference rows (D-B8d)', () => {
    it('open the table, portfolio then benchmark, while it is neither sorted nor filtered', () => {
        mount([...assets(6), BENCHMARK, PORTFOLIO], 'rrl-refs');

        expect(shown().slice(0, 2)).toEqual(['ref-portfolio', 'ref-99']);
    });

    it('sort like any other row once the reader sorts: the most volatile one leaves the first page', async () => {
        mount([...assets(6), BENCHMARK, PORTFOLIO], 'rrl-refs-sorted');
        expect(shown()).toContain('ref-portfolio');

        // Ascending by volatility: the portfolio (90 %) is the last of eight rows, so it is on the second page.
        await fireEvent.click(screen.getByTestId(`dt-sort-volatility`));

        await waitFor(() => expect(shown()).not.toContain('ref-portfolio'));
        expect(shown()).toHaveLength(5);
    });
});
