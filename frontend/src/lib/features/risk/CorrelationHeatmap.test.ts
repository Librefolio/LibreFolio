// @vitest-environment jsdom
/**
 * CorrelationHeatmap.test.ts — the colours the correlation matrix hands ECharts and paints in its legend,
 * and the sector emoji of its badges, read off the real component.
 *
 * ## The subject: the designer's scale (round 3, §1.6)
 *
 * The coefficient is drawn from −1 to +1 on three values of the designer's own, a red, a grey-blue and the
 * cobalt of the ETF: `CORRELATION_SCALE` of the theme (`lib/theme/chartPalettes`), no longer the danger,
 * panel and info roles of her round 2 (GR5.3). So a page whose roles are other colours leaves the scale
 * where it is. The same three stops paint the HTML legend under the cells, and follow the `dark` class of
 * `<html>`. A cell's number is written in pure black or pure white (`CORRELATION_CELL_TEXT`), whichever
 * reads best on the cell's own colour — the scale's colour at its value, as ECharts' `visualMap`
 * interpolates it (`scaleColor`) — through `readableOn`; over the whole scale that choice reads at least
 * 4.5:1, in both themes. The matrix's neutrals (the gaps between cells, the hovered cell, the axis labels,
 * the tooltip) are still roles, read from its own element (`chartNeutrals`): a chart-colour change
 * (contract C4, `notifyChartColorsChange`) must draw them again.
 *
 * The sector badges above the matrix carry the emoji of the sector store, the backend's one map: the
 * matrix asks for it when it is given sectors, and the badges follow the moment it arrives.
 *
 * ## How the expectations are built
 *
 * Role values are injected with `setRoleReader`, answered only for the matrix's own element — so a
 * neutral read from `<html>`, a stand-in or a literal cannot pass — and reset after every test; the
 * danger, panel and info roles are answered too, as the negative control of the scale. Expectations come
 * from the theme's own tables and functions (`CORRELATION_SCALE`, `CORRELATION_CELL_TEXT`, `scaleColor`,
 * `readableOn`), never from copied hex values. A colour the browser writes back into an inline style may
 * come back as `rgb(…)`: it is read back to `#rrggbb`.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer — jsdom has no canvas — as in `AllocationPieChart.test.ts`.
 * - `$lib/api`: the sector list, the one request the matrix makes, answered by this file with invented
 *   emoji, so an emoji on a badge can only have come from it; every other endpoint answers an empty list.
 *
 * Nothing translated is asserted: the asset names are props, and a badge is read only for its emoji.
 *
 * The component imports K's `assetTypes.ts`, which reads the generated client at module load, so it is
 * imported after asserting the generated file exists: a missing client is reported with its fix.
 *
 * @module features/risk/CorrelationHeatmap.test
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: it answers every call the matrix and its helpers make on an instance
 * (`attachChartReady` → `on`, `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, a redraw →
 * `resize`/`dispatchAction`, the teardown → `dispose`) and keeps every `setOption` payload.
 */
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

/** GET /utilities/sectors: what the sector store loads, once per module. */
const sectorsEndpoint = vi.hoisted(() => vi.fn());

vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy(
        {},
        {
            get(_target, name) {
                return name === 'list_sectors_api_v1_utilities_sectors_get' ? sectorsEndpoint : vi.fn(async () => ({items: []}));
            },
        },
    ),
}));

import {flushSync, tick} from 'svelte';
import {render, screen, setupI18n, waitFor} from '$test/component';
import type {RiskCorrelationOutput} from '$lib/features/risk/riskTypes';
import {sectorEmojiVersion} from '$lib/stores/reference/sectorStore';
import {CORRELATION_CELL_TEXT, CORRELATION_SCALE} from '$lib/theme/chartPalettes';
import {scaleColor} from '$lib/theme/chartShades';
import {contrastRatio, readableOn} from '$lib/theme/contrast';
import {setRoleReader, type ChartRole} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import {themed} from '$lib/theme/themePair';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** Four invented holdings. */
const [ALPHA, BETA, GAMMA, DELTA] = [11, 12, 13, 14];
const LABELS: ReadonlyMap<number, string> = new Map([
    [ALPHA, 'Invented fund Alpha'],
    [BETA, 'Invented fund Beta'],
    [GAMMA, 'Invented fund Gamma'],
    [DELTA, 'Invented fund Delta'],
]);

function cell(row: number, column: number, value: number | null, status: 'ok' | 'insufficient' = 'ok') {
    return {row_asset_id: row, column_asset_id: column, value, observations: 250, coverage: 1, status};
}

/**
 * Six pairs across the whole scale: near −1 and near +1, where the scale is saturated, near 0, where it is
 * the pale panel, two in between, and one with no usable value, which the matrix draws at 0.
 */
const OUTPUT: RiskCorrelationOutput = {
    kind: 'matrix',
    asset_ids: [ALPHA, BETA, GAMMA, DELTA],
    cells: [cell(BETA, ALPHA, -0.92), cell(GAMMA, ALPHA, 0.95), cell(GAMMA, BETA, 0.02), cell(DELTA, ALPHA, null, 'insufficient'), cell(DELTA, BETA, 0.55), cell(DELTA, GAMMA, -0.4)],
};

/** The sector list, with invented emoji: no table written by hand gives Technology a DNA helix. */
const SECTOR_LIST = {
    items: [
        {key: 'Technology', emoji: '🧬'},
        {key: 'Health Care', emoji: '🧪'},
    ],
    buckets: [
        {key: 'Liquidity', emoji: '🫙'},
        {key: 'Unknown', emoji: '🫥'},
    ],
    fallback_emoji: '🫧',
};

/** Sector distributions: two holdings mostly in technology, one in health care, one unclassified. */
const SECTORS: ReadonlyMap<number, Readonly<Record<string, number>> | null> = new Map<number, Readonly<Record<string, number>> | null>([
    [ALPHA, {Technology: 0.8, 'Health Care': 0.2}],
    [BETA, {Technology: 0.9, 'Health Care': 0.1}],
    [GAMMA, {'Health Care': 1}],
    [DELTA, null],
]);

/**
 * Role values of this file's own: dark saturated ends and a pale middle where the round-2 scale read its three roles
 * (the negative control of the scale), two text roles far apart, and a card, which the matrix draws its cell gaps in.
 */
const ROLES: Readonly<Partial<Record<ChartRole, string>>> = {
    '--lf-danger': '#8a1020',
    '--lf-surface-panel': '#f1ede4',
    '--lf-info': '#10308a',
    '--lf-text-primary': '#1d1f1a',
    '--lf-text-on-inverse': '#fdfaf3',
    '--lf-surface-card': '#f6f0e1',
};

/** The three roles the scale was made of until round 3, as `roles` answers them. */
const roleStops = (roles: Readonly<Partial<Record<ChartRole, string>>>): Array<string | undefined> => [roles['--lf-danger'], roles['--lf-surface-panel'], roles['--lf-info']];

/** The designer's scale of a theme, from −1 through 0 to +1, as `#rrggbb` lower case: what the legend is read back as. */
const scaleOf = (dark: boolean): string[] => themed(CORRELATION_SCALE, dark).map((stop) => stop.toLowerCase());

/** The number's colour on a cell of value `value`, as the rule of §1.6 picks it on `scale`: an unknown value at 0. */
const cellText = (scale: readonly string[], value: number | null): string => readableOn(scaleColor(scale, value ?? 0, -1, 1), CORRELATION_CELL_TEXT);

/** The element the matrix draws in: the one ECharts is given, inside the scrolling box that carries the testid. */
function isMatrixElement(scope: Element | null): boolean {
    return scope !== null && scope.parentElement?.getAttribute('data-testid') === 'risk-correlation-heatmap';
}

/** Answers `roles` for the matrix's own element, nothing anywhere else. */
function injectRoles(roles: () => Readonly<Partial<Record<ChartRole, string>>>): void {
    setRoleReader((role, scope) => (isMatrixElement(scope) ? (roles()[role] ?? '') : ''));
}

type HeatmapComponent = typeof import('./CorrelationHeatmap.svelte').default;
let CorrelationHeatmap: HeatmapComponent;
let restoreCanvas: (() => void) | undefined;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the matrix that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    CorrelationHeatmap = (await import('./CorrelationHeatmap.svelte')).default;
    sectorsEndpoint.mockResolvedValue(SECTOR_LIST);
    // jsdom has no canvas: the matrix measures its axis labels with one and, without it, falls back to a
    // per-character estimate. `null` is what jsdom answers anyway — only without its "not implemented" log.
    const getContext = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    restoreCanvas = () => getContext.mockRestore();
});

afterAll(() => {
    restoreCanvas?.();
});

beforeEach(() => {
    chartInstances.length = 0;
});

afterEach(() => {
    // Module-level state every test of the file shares: the role reader and the theme class.
    setRoleReader(null);
    document.documentElement.classList.remove('dark');
});

// =============================================================================
// Reading what the matrix drew
// =============================================================================

/** A cell as the matrix hands it to ECharts. */
interface DrawnCell {
    value: [number, number, number | null];
    rowAssetId: number;
    columnAssetId: number;
    label?: {color?: string};
}

/** The last option the matrix handed ECharts: its scale, its cells, and the colour of the gaps between them. */
function lastOption(): {scale: string[]; cells: DrawnCell[]; cellGap: string | undefined} {
    expect(chartInstances, 'the matrix did not create exactly one chart').toHaveLength(1);
    const call = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.visualMap !== undefined);
    if (!call) throw new Error('the matrix never handed ECharts a scale');
    const visualMap = call.option.visualMap as {inRange?: {color?: string[]}};
    const series = call.option.series as Array<{data: DrawnCell[]; itemStyle?: {borderColor?: string}}>;
    return {scale: visualMap.inRange?.color ?? [], cells: series[0].data, cellGap: series[0].itemStyle?.borderColor};
}

/** Mounts the matrix and waits for its first drawing. */
async function mountMatrix(props: {assetSectors?: typeof SECTORS} = {}) {
    const view = render(CorrelationHeatmap, {props: {output: OUTPUT, assetLabels: LABELS, ...props}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the matrix never drew').toBeGreaterThan(0));
    return view;
}

/** A CSS colour as `#rrggbb`: the inline style may hand back `rgb(…)`. */
function asHex(colour: string): string {
    const rgb = /^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/i.exec(colour.trim());
    if (!rgb) return colour.trim().toLowerCase();
    return `#${rgb
        .slice(1, 4)
        .map((channel) => Number(channel).toString(16).padStart(2, '0'))
        .join('')}`;
}

/** The colour stops of the legend's gradient, in order, as `#rrggbb`. */
function legendStops(): string[] {
    const legend = screen.getByTestId('risk-correlation-legend');
    const bar = [...legend.querySelectorAll<HTMLElement>('*')].find((element) => (element.getAttribute('style') ?? '').includes('linear-gradient'));
    if (!bar) throw new Error(`the legend paints no gradient: ${legend.innerHTML}`);
    const gradient = /linear-gradient\((.*)\)/.exec(bar.getAttribute('style') ?? '')?.[1] ?? '';
    return [...gradient.matchAll(/#[0-9a-f]{6}\b|rgba?\([^)]*\)/gi)].map((match) => asHex(match[0]));
}

// =============================================================================
// §1.6 — the scale, the designer's own values, and the number on each cell
// =============================================================================

const THEMES = [
    {theme: 'light', dark: false},
    {theme: 'dark', dark: true},
] as const;

/** The lowest contrast of the text `candidates` lets `readableOn` pick, over `steps` values of r from −1 to +1 on `scale`. */
function worstOverScale(scale: readonly string[], candidates: readonly [string, ...string[]], steps = 401): {ratio: number; r: number} {
    let worst = {ratio: Infinity, r: Number.NaN};
    for (let step = 0; step < steps; step += 1) {
        const r = -1 + (2 * step) / (steps - 1);
        const cell = scaleColor(scale, r, -1, 1);
        const ratio = contrastRatio(cell, readableOn(cell, candidates));
        if (ratio < worst.ratio) worst = {ratio, r};
    }
    return worst;
}

describe('CorrelationHeatmap — the scale: the designer’s three values of the theme, whatever the roles (§1.6)', () => {
    it.each(THEMES)('$theme theme: hands visualMap CORRELATION_SCALE as its range, and paints the legend with the same three stops — not the danger, panel and info roles of its element', async ({dark}) => {
        injectRoles(() => ROLES);
        document.documentElement.classList.toggle('dark', dark);
        // Negative control: the roles answered for the matrix are not the scale, so a matrix still reading them fails below.
        expect(
            roleStops(ROLES).map((stop) => stop?.toLowerCase()),
            'control: the injected roles are the scale',
        ).not.toEqual(scaleOf(dark));

        await mountMatrix();

        expect(lastOption().scale, 'the range ECharts paints the cells with').toEqual([...themed(CORRELATION_SCALE, dark)]);
        expect(legendStops(), 'the stops of the legend under the cells').toEqual(scaleOf(dark));
    });

    it.each(THEMES)('$theme theme: writes every number in black or white, whichever reads best on its own cell — readableOn of the scale at its value, an unknown value at 0', async ({dark}) => {
        injectRoles(() => ROLES);
        document.documentElement.classList.toggle('dark', dark);
        await mountMatrix();
        const {scale, cells} = lastOption();

        // Barrier: all six pairs are drawn, the unknown one among them.
        expect(cells).toHaveLength(6);
        expect(cells.filter((drawn) => drawn.value[2] === null)).toHaveLength(1);
        expect(cells.map((drawn) => `${drawn.rowAssetId}-${drawn.columnAssetId} ${drawn.label?.color}`)).toEqual(cells.map((drawn) => `${drawn.rowAssetId}-${drawn.columnAssetId} ${cellText(scale, drawn.value[2])}`));
        // The choice is the cell's: on this matrix one cell takes black and another white, so a constant could not pass
        // the comparison above; and neither text role of the element is used.
        expect(new Set(cells.map((drawn) => drawn.label?.color))).toEqual(new Set(CORRELATION_CELL_TEXT));
    });

    it.each(THEMES)('$theme theme: over the whole scale — r in 401 steps from −1 to +1 — the number reads at least 4.5:1 on its cell', ({dark}) => {
        const scale = [...themed(CORRELATION_SCALE, dark)];
        const worst = worstOverScale(scale, CORRELATION_CELL_TEXT);

        expect(worst.ratio, `the weakest cell, r = ${worst.r.toFixed(3)}`).toBeGreaterThanOrEqual(4.5);
        // Positive control: neither text alone is enough, so the property depends on the choice cell by cell.
        expect(worstOverScale(scale, [CORRELATION_CELL_TEXT[0]]).ratio, 'black alone').toBeLessThan(4.5);
        expect(worstOverScale(scale, [CORRELATION_CELL_TEXT[1]]).ratio, 'white alone').toBeLessThan(4.5);
    });

    it('draws a theme switch in the other theme’s scale: the range and the legend follow the `dark` class of <html>', async () => {
        await mountMatrix();
        const [chart] = chartInstances;
        // Control: the scales of the two themes differ on every stop.
        expect(scaleOf(false).filter((stop, index) => stop === scaleOf(true)[index])).toEqual([]);
        expect(lastOption().scale).toEqual([...themed(CORRELATION_SCALE, false)]);

        const before = chart.setOptionCalls.length;
        document.documentElement.classList.add('dark');

        await waitFor(() => expect(chart.setOptionCalls.length, 'the matrix was not drawn again after the theme switched').toBeGreaterThan(before));
        expect(lastOption().scale).toEqual([...themed(CORRELATION_SCALE, true)]);
        expect(legendStops()).toEqual(scaleOf(true));
        const {scale, cells} = lastOption();
        expect(cells.map((drawn) => drawn.label?.color)).toEqual(cells.map((drawn) => cellText(scale, drawn.value[2])));
    });
});

// =============================================================================
// C4 — a chart-colour change reads the neutrals again; the scale stays the designer's
// =============================================================================

describe('CorrelationHeatmap — notifyChartColorsChange() draws the matrix again (C4)', () => {
    it('draws its neutrals again, read anew from its own element — with the same scale and the same numbers — and nothing redraws before the notification', async () => {
        const NEXT: Readonly<Partial<Record<ChartRole, string>>> = {...ROLES, '--lf-danger': '#6a0a40', '--lf-surface-panel': '#e9f1e4', '--lf-info': '#0a5a6a', '--lf-surface-card': '#e4ecf6'};
        let current = ROLES;
        injectRoles(() => current);
        await mountMatrix();
        const [chart] = chartInstances;
        const first = lastOption();
        // Barrier: the gaps between the cells are the card of the matrix's own element.
        expect(first.cellGap, 'the cell gaps, before the change').toBe(ROLES['--lf-surface-card']);
        expect(first.scale).toEqual([...themed(CORRELATION_SCALE, false)]);

        current = NEXT;
        const before = chart.setOptionCalls.length;
        // A role is read when the option is built: until the signal comes, the matrix keeps what it drew.
        flushSync();
        await tick();
        expect(chart.setOptionCalls.length, 'the matrix redrew without being told its colours changed').toBe(before);

        notifyChartColorsChange();

        await waitFor(() => expect(chart.setOptionCalls.length, 'the matrix was not drawn again after the notification: its neutrals keep the old roles').toBeGreaterThan(before));
        const next = lastOption();
        expect(next.cellGap, 'the cell gaps, after the change').toBe(NEXT['--lf-surface-card']);
        // The scale is no role: other danger, panel and info roles leave it, and the numbers on it, where they were.
        expect(next.scale).toEqual([...themed(CORRELATION_SCALE, false)]);
        expect(legendStops()).toEqual(scaleOf(false));
        expect(next.cells.map((drawn) => drawn.label?.color)).toEqual(first.cells.map((drawn) => drawn.label?.color));
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
    });
});

// =============================================================================
// The sector badges — the sector store's emoji
// =============================================================================

/**
 * Order matters in this block: the sector store loads once per module, so the first matrix given sectors
 * is the only one that can see the list arrive. Both tests check the state they start from.
 */
describe('CorrelationHeatmap — the sector badges carry the sector store’s emoji', () => {
    it('asks for no sector list when it is given no sectors', async () => {
        expect(sectorEmojiVersion(), 'precondition: the sector store has already loaded').toBe(0);
        await mountMatrix();

        expect(sectorsEndpoint, 'the matrix asked for the sector list without sectors to show').not.toHaveBeenCalled();
        expect(screen.queryByTestId('risk-correlation-groups-sector')).toBeNull();
    });

    it('asks for the sector list when it is given sectors, and its badges take each emoji the moment the list arrives', async () => {
        // Premise: the first matrix of the file given sectors — the store has never loaded, nobody has asked.
        expect(sectorsEndpoint, 'precondition: the sector list was requested before this test').not.toHaveBeenCalled();
        expect(sectorEmojiVersion(), 'precondition: the sector store has already loaded').toBe(0);
        let release: (list: typeof SECTOR_LIST) => void = () => {};
        sectorsEndpoint.mockImplementationOnce(() => new Promise((resolve) => (release = resolve)));

        await mountMatrix({assetSectors: SECTORS});
        expect(sectorsEndpoint, 'the matrix did not ask for the sector list').toHaveBeenCalledTimes(1);
        const row = screen.getByTestId('risk-correlation-groups-sector');
        // Before the list: the badges carry their sectors, and no emoji yet.
        expect([...SECTOR_LIST.items, ...SECTOR_LIST.buckets].filter(({emoji}) => (row.textContent ?? '').includes(emoji)).map(({key}) => key)).toEqual([]);

        release(SECTOR_LIST);

        await waitFor(() => expect(row.textContent ?? '', 'the badges did not follow the sector list').toContain('🧬'));
        expect(row.textContent ?? '').toContain('🧪');
        expect(sectorsEndpoint, 'the sector list was asked for twice').toHaveBeenCalledTimes(1);
    });
});
