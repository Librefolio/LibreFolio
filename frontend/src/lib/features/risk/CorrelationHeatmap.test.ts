// @vitest-environment jsdom
/**
 * CorrelationHeatmap.test.ts — the colours the correlation matrix hands ECharts and paints in its legend,
 * and the sector emoji of its badges, read off the real component.
 *
 * ## The subject: GR5.3 and the sRGB bridge
 *
 * The designer's round 2 (D-T17, GR5.3) draws the coefficient from −1 to +1 on three colour roles: the
 * danger role, the secondary surface (`--lf-surface-panel`), the info role. ECharts paints on a canvas,
 * so the roles reach it only as colours resolved when the option is built — `chartRoles(dark, element)`,
 * read from the matrix's own element (tokens.css recomputes the roles in a forced `.light`/`.dark`
 * subtree) — and read again at each theme switch and each chart-colour change (contract C4,
 * `notifyChartColorsChange`). The same three stops paint the HTML legend under the cells. A cell's number
 * is written in the text that reads best on the cell's own colour: the scale's colour at its value, as
 * ECharts' `visualMap` interpolates it (`scaleColor`), through `readableText`.
 *
 * The sector badges above the matrix carry the emoji of the sector store, the backend's one map: the
 * matrix asks for it when it is given sectors, and the badges follow the moment it arrives.
 *
 * ## How the expectations are built
 *
 * Role values are injected with `setRoleReader`, answered only for the matrix's own element — so a scale
 * read from `<html>`, a stand-in or a literal cannot pass — and reset after every test. Expectations come
 * from the theme's own functions (`chartRoles`, `scaleColor`), never from copied hex values. A colour
 * the browser writes back into an inline style may come back as `rgb(…)`: it is read back to `#rrggbb`.
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
import {scaleColor} from '$lib/theme/chartShades';
import {chartRoles, setRoleReader, type ChartRole} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';

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

/** Role values of this file's own: dark saturated ends, a pale middle, two text roles far apart. */
const ROLES: Readonly<Partial<Record<ChartRole, string>>> = {
    '--lf-danger': '#8a1020',
    '--lf-surface-panel': '#f1ede4',
    '--lf-info': '#10308a',
    '--lf-text-primary': '#1d1f1a',
    '--lf-text-on-inverse': '#fdfaf3',
};

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

/** The last option the matrix handed ECharts. */
function lastOption(): {scale: string[]; cells: DrawnCell[]} {
    expect(chartInstances, 'the matrix did not create exactly one chart').toHaveLength(1);
    const call = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.visualMap !== undefined);
    if (!call) throw new Error('the matrix never handed ECharts a scale');
    const visualMap = call.option.visualMap as {inRange?: {color?: string[]}};
    const series = call.option.series as Array<{data: DrawnCell[]}>;
    return {scale: visualMap.inRange?.color ?? [], cells: series[0].data};
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
// GR5.3 — the scale, from the matrix's own roles
// =============================================================================

describe('CorrelationHeatmap — the scale: danger, panel, info, from the roles of its own element (GR5.3)', () => {
    it('hands visualMap the three roles as its range, and paints the legend with the same three stops', async () => {
        injectRoles(() => ROLES);
        await mountMatrix();

        const expected = [ROLES['--lf-danger'], ROLES['--lf-surface-panel'], ROLES['--lf-info']];
        expect(lastOption().scale, 'the range ECharts paints the cells with').toEqual(expected);
        expect(legendStops(), 'the stops of the legend under the cells').toEqual(expected);
    });

    it('writes every number in the text that reads best on its own cell: readableText of the scale at its value, an unknown value at 0', async () => {
        injectRoles(() => ROLES);
        await mountMatrix();
        const {scale, cells} = lastOption();
        const roles = chartRoles(false, chartInstances[0].getDom() as Element);

        // Barrier: all six pairs are drawn, the unknown one among them.
        expect(cells).toHaveLength(6);
        expect(cells.filter((drawn) => drawn.value[2] === null)).toHaveLength(1);
        expect(cells.map((drawn) => `${drawn.rowAssetId}-${drawn.columnAssetId} ${drawn.label?.color}`)).toEqual(cells.map((drawn) => `${drawn.rowAssetId}-${drawn.columnAssetId} ${roles.readableText(scaleColor(scale, drawn.value[2] ?? 0, -1, 1))}`));
        // The choice is the cell's: the saturated ends take one text and the pale middle the other, so a
        // constant could not pass the comparison above.
        expect(new Set(cells.map((drawn) => drawn.label?.color))).toEqual(new Set([ROLES['--lf-text-primary'], ROLES['--lf-text-on-inverse']]));
    });

    it('draws a theme switch in the other theme’s roles: the range and the legend follow the `dark` class of <html>', async () => {
        await mountMatrix();
        const [chart] = chartInstances;
        const rolesIn = (dark: boolean) => {
            const roles = chartRoles(dark, chart.getDom() as Element);
            return [roles.color('--lf-danger'), roles.color('--lf-surface-panel'), roles.color('--lf-info')];
        };
        // Control: the stand-ins of the two themes differ on every stop.
        expect(rolesIn(false).filter((stop, index) => stop === rolesIn(true)[index])).toEqual([]);
        expect(lastOption().scale).toEqual(rolesIn(false));

        const before = chart.setOptionCalls.length;
        document.documentElement.classList.add('dark');

        await waitFor(() => expect(chart.setOptionCalls.length, 'the matrix was not drawn again after the theme switched').toBeGreaterThan(before));
        expect(lastOption().scale).toEqual(rolesIn(true));
        expect(legendStops()).toEqual(rolesIn(true).map(asHex));
    });
});

// =============================================================================
// C4 — a chart-colour change reads the roles again
// =============================================================================

describe('CorrelationHeatmap — notifyChartColorsChange() reads the roles again (C4)', () => {
    it('draws the new roles on the cells, their numbers and the legend — and nothing redraws before the notification', async () => {
        const NEXT: Readonly<Partial<Record<ChartRole, string>>> = {...ROLES, '--lf-danger': '#6a0a40', '--lf-surface-panel': '#e9f1e4', '--lf-info': '#0a5a6a'};
        let current = ROLES;
        injectRoles(() => current);
        await mountMatrix();
        const [chart] = chartInstances;
        expect(lastOption().scale).toEqual([ROLES['--lf-danger'], ROLES['--lf-surface-panel'], ROLES['--lf-info']]);

        current = NEXT;
        const before = chart.setOptionCalls.length;
        // A role is read when the scale is built: until the signal comes, the matrix keeps what it drew.
        flushSync();
        await tick();
        expect(chart.setOptionCalls.length, 'the matrix redrew without being told its colours changed').toBe(before);
        expect(legendStops()).toEqual([ROLES['--lf-danger'], ROLES['--lf-surface-panel'], ROLES['--lf-info']]);

        notifyChartColorsChange();

        const expected = [NEXT['--lf-danger'], NEXT['--lf-surface-panel'], NEXT['--lf-info']];
        await waitFor(() => expect(lastOption().scale, 'the range after the notification').toEqual(expected));
        expect(legendStops()).toEqual(expected);
        const roles = chartRoles(false, chart.getDom() as Element);
        const {cells} = lastOption();
        expect(cells.map((drawn) => drawn.label?.color)).toEqual(cells.map((drawn) => roles.readableText(scaleColor(expected as string[], drawn.value[2] ?? 0, -1, 1))));
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
