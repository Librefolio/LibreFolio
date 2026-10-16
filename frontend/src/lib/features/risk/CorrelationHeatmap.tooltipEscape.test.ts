// @vitest-environment jsdom
/**
 * CorrelationHeatmap.tooltipEscape.test.ts — C-34: the correlation matrix's tooltip escapes asset names with the shared
 * `escapeHtml`, not with a local copy that forgets the quotes.
 *
 * ## What it protects (C-34)
 *
 * Asset names are user data, and the matrix's tooltip is HTML that ECharts sets as `innerHTML`. The app has one HTML
 * escaper, `escapeHtml` (`src/lib/utils/core/escapeHtml.ts`), which escapes five characters — `& < > " '` — so that its
 * output is also safe inside an attribute, whichever quote the call site uses. A local copy that escapes fewer is the
 * defect C-34 removes: the day such a name lands in an attribute (`title="…"`), a quote in it ends the attribute.
 *
 * ## Why it is red today
 *
 * `CorrelationHeatmap.svelte` declares its own `escapeHtml` (:350–:353), which escapes only `& < >` (:352), and
 * `assetBlock()` interpolates the asset label through it (:363 — `nameOf(assetId)`, the `assetLabels` prop). With the
 * label `O'Brien "Q" <b data-pwned="1">X</b> & Co` the tooltip holds `O'Brien "Q" &lt;b …`, not the shared escaper's
 * `O&#39;Brien &quot;Q&quot; &lt;b …`.
 *
 * Green today, and kept: no element is injected — the local copy does escape `<` and `>` — and the label reads as text.
 * They are the guards of the harness and of the verdict: the red can only be about the quotes.
 *
 * ## How
 *
 * The real component in jsdom, ECharts replaced by a recorder — the pattern of `CorrelationHeatmap.test.ts`. The tooltip
 * is the `tooltip.formatter` of the option the matrix handed ECharts, called as ECharts calls an item tooltip: with the
 * hovered cell as `params.data`, a cell of the series the matrix drew. The matrix imports `assetTypes.ts`, which reads
 * the generated client at module load, so it is imported after asserting the generated file exists.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/** The ECharts stand-in of `CorrelationHeatmap.test.ts`: it answers every call the matrix makes, and keeps every `setOption` payload. */
const {chartInstances, echartsModule} = vi.hoisted(() => {
    interface SetOptionCall {
        option: Record<string, unknown>;
        opts: unknown;
    }

    interface FakeChart {
        setOptionCalls: SetOptionCall[];
        setOption: (option: Record<string, unknown>, opts?: unknown) => void;
        getDom: () => unknown;
        on: (event: string, handler: () => void) => void;
        off: (event: string, handler: () => void) => void;
        dispatchAction: (action: unknown) => void;
        clear: () => void;
        resize: () => void;
        isDisposed: () => boolean;
        dispose: () => void;
    }

    const chartInstances: FakeChart[] = [];

    function createFakeChart(dom: unknown): FakeChart {
        let disposed = false;
        const chart: FakeChart = {
            setOptionCalls: [],
            setOption(option, opts) {
                chart.setOptionCalls.push({option, opts});
            },
            getDom: () => dom,
            on: () => {},
            off: () => {},
            dispatchAction: () => {},
            clear: () => {},
            resize: () => {},
            isDisposed: () => disposed,
            dispose: () => {
                disposed = true;
            },
        };
        chartInstances.push(chart);
        return chart;
    }

    return {chartInstances, echartsModule: {init: (dom: unknown) => createFakeChart(dom)}};
});

vi.mock('echarts', () => echartsModule);

/** No request leaves jsdom: the matrix asks for the sector list only when given sectors, and this file gives none. */
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get() {
                return vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {render, setupI18n, waitFor} from '$test/component';
import type {RiskCorrelationOutput} from '$lib/features/risk/riskTypes';
import {escapeHtml} from '$lib/utils/core/escapeHtml';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** An asset label with every character the shared escaper escapes, and markup whose element carries a marker. */
const LABEL = 'O\'Brien "Q" <b data-pwned="1">X</b> & Co';

/** Three invented holdings: the middle one carries LABEL. */
const [ALPHA, BETA, GAMMA] = [21, 22, 23];
const LABELS: ReadonlyMap<number, string> = new Map([
    [ALPHA, 'Invented fund Alpha'],
    [BETA, LABEL],
    [GAMMA, 'Invented fund Gamma'],
]);

function cell(row: number, column: number, value: number) {
    return {row_asset_id: row, column_asset_id: column, value, observations: 250, coverage: 1, status: 'ok' as const};
}

const OUTPUT: RiskCorrelationOutput = {
    kind: 'matrix',
    asset_ids: [ALPHA, BETA, GAMMA],
    cells: [cell(BETA, ALPHA, 0.42), cell(GAMMA, ALPHA, -0.3), cell(GAMMA, BETA, 0.81)],
};

/** A cell as the matrix hands it to ECharts: the fields its tooltip reads. */
interface DrawnCell {
    value: [number, number, number | null];
    rowAssetId: number;
    columnAssetId: number;
    observations: number;
    coverage: number;
    status: string;
}

type HeatmapComponent = typeof import('./CorrelationHeatmap.svelte').default;
let CorrelationHeatmap: HeatmapComponent;
let restoreCanvas: (() => void) | undefined;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the matrix that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    CorrelationHeatmap = (await import('./CorrelationHeatmap.svelte')).default;
    // jsdom has no canvas: the matrix measures its axis labels with one and, without it, falls back to a per-character
    // estimate. `null` is what jsdom answers anyway — only without its "not implemented" log.
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    restoreCanvas = () => getContext.mockRestore();
    // The dynamic import compiles the component tree inside this hook: a budget of its own under a loaded machine.
}, 60_000);

afterAll(() => {
    restoreCanvas?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

// =============================================================================
// Reading the tooltip
// =============================================================================

/** The tooltip's HTML for a drawn cell that involves LABEL's asset, from the formatter the matrix handed ECharts. */
async function tooltipNamingTheLabel(): Promise<string> {
    render(CorrelationHeatmap, {props: {output: OUTPUT, assetLabels: LABELS}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the matrix never drew').toBeGreaterThan(0), {timeout: 5_000});
    expect(chartInstances, 'the matrix did not create exactly one chart').toHaveLength(1);
    const call = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.tooltip !== undefined && option.series !== undefined);
    if (!call) throw new Error('the matrix never handed ECharts a tooltip with its cells');
    const formatter = (call.option.tooltip as {formatter: (params: {data?: DrawnCell}) => string}).formatter;
    const cells = (call.option.series as Array<{data: DrawnCell[]}>)[0].data;
    const hovered = cells.find((drawn) => drawn.rowAssetId === BETA || drawn.columnAssetId === BETA);
    if (!hovered) throw new Error(`no drawn cell involves asset ${BETA}: ${JSON.stringify(cells)}`);
    return formatter({data: hovered});
}

/** A tooltip's HTML parsed into a detached element, as the browser parses it when ECharts sets it. */
function parse(html: string): HTMLDivElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    return host;
}

// =============================================================================
// C-34 — one escaper
// =============================================================================

describe('CorrelationHeatmap — the tooltip escapes asset names with the shared escapeHtml (C-34)', {timeout: 20_000}, () => {
    it('harness — the shared escaper turns both quotes of the label into entities: the last case asks for something the local copy does not produce', () => {
        const shared = escapeHtml(LABEL);

        expect(shared).toContain('&#39;');
        expect(shared).toContain('&quot;');
        expect(shared).toContain('&lt;b');
    });

    it('guard — no element is injected, and the label reads as text: the local copy escapes < and >', async () => {
        const html = await tooltipNamingTheLabel();
        const host = parse(html);

        expect(host.querySelector('[data-pwned]'), `the label became an element. Tooltip HTML: ${html}`).toBeNull();
        expect(host.textContent ?? '', `the label does not read as text in the tooltip — is the hovered cell the right one? Tooltip HTML: ${html}`).toContain(LABEL);
    });

    it('the asset name is escaped by the shared escapeHtml: the tooltip holds escapeHtml(label) exactly (local copy at :350–:353, used at :363)', async () => {
        const html = await tooltipNamingTheLabel();

        expect(html, 'the tooltip escapes the asset name with the local copy, which leaves the quotes').toContain(escapeHtml(LABEL));
    });
});
