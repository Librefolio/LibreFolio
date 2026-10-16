// @vitest-environment jsdom
/**
 * ExposureBars.test.ts — the colours the PAC planner's exposure bars hand ECharts, read off the real component (TD-1).
 *
 * ## The subject
 *
 * For each category of one dimension — Asset type or sector — the bars set the ideal weight beside the actual one: the
 * target and the weight after the plan (R9.8). TD-1 gives the two weights different jobs:
 *
 * - the ideal weight is one neutral role, the secondary text (`--lf-text-secondary`), on the whole first series;
 * - the actual weight wears its row's category colour, the dashboard's (GR1 of the designer's round 2), bar by bar: a
 *   sector by its key; an Asset type by its family, a subtype a GR4 shade of it by its rank of ideal weight among its
 *   family's subtypes — never the family's own colour, even with no generic member beside it — on the shade poles of the
 *   card the chart is drawn on; the uncategorised remainder in the «Unknown» colour;
 * - the legend swatch of the ideal is its role; the actual weight has no one colour, so its swatch is an outline in the
 *   grid's text colour, on the card;
 * - the tooltip of a row puts a dot in each of the row's two colours.
 *
 * The chart reads its roles from its own element (`chartRoles`) when it builds its option, and builds that option again,
 * whole, at a theme switch and at a chart-colour change (contract C4 with the Designer Lab). The brand greens the bars
 * were drawn in before TD-1 (`PAC_EXPOSURE_BAR_COLORS`, removed) are nowhere.
 *
 * ## How the expectations are built
 *
 * The roles are invented and injected with `setRoleReader`: answered for the bars' own element only, per theme, and reset
 * after every test, so a role read anywhere else — `<html>`, a stand-in, a literal — is not one of them. Category colours
 * come from the theme's own functions (`categoryColor`, `familyShade`, `shadePoles` on the injected card), never from
 * copied hex values, which the theme's tests pin. The family and the rank of every Asset-type row are spelled out in the
 * fixture, then checked against K's `assetTypeFamily` and against the rule. `exposureBarColours.ts`, which computes them
 * for the chart and which TA-1 tests, is not called here: the chart would be checked against its own helper.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer — jsdom has no canvas — as in `SemiDonutChart.test.ts`. It answers what the bars
 *   and their helpers call on an instance and keeps every `setOption` payload.
 * - `$lib/api`: inert, as in `ResultCell.test.ts`. The percentages' formatter reads the currency catalogue store, which
 *   imports the client; nothing is loaded, and no request leaves the test.
 *
 * Nothing translated is asserted: a legend entry is matched to its series by name, and the labels are props.
 *
 * The bars import K's `assetTypes.ts`, which reads the generated client at module load: they are imported after
 * asserting that the generated file exists, so a missing client is reported with the command that fixes it.
 *
 * @module features/tools/pac-allocator/planner/result/ExposureBars.test
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: it answers every call the bars and their helpers make on an instance (`attachChartReady` → `on`,
 * `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the teardown → `dispose`) and keeps every `setOption`
 * payload.
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

// The percentages' formatter reads the currency catalogue store, which imports the API client. Nothing here loads the
// catalogue: every call resolves to nothing, and no request leaves the test.
vi.mock('$lib/api', () => ({
    zodiosApi: new Proxy({}, {get: () => vi.fn(async () => undefined)}),
}));

import {flushSync, tick} from 'svelte';
import {render, setupI18n, waitFor} from '$test/component';
import {buildGridColors} from '$lib/components/charts/echartsTooltipHelpers';
import {categoryColor} from '$lib/theme/chartCategories';
import {familyShade, shadePoles} from '$lib/theme/chartShades';
import {chartRoles, setRoleReader} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import type {PacExactNumber, PacNumberAvailability} from '../types';
import {UNCATEGORISED_CATEGORY_ID, type WeightRow} from './model';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** The bars' element: the chart's container, the one element the injected roles answer for. */
const BARS_TESTID = 'pac-planner-exposures-bars';

type Theme = 'light' | 'dark';

/** The two themes, as the bars read them off the `dark` class of <html> when they build their option. */
const THEMES: readonly Theme[] = ['light', 'dark'];

/** An ideal weight, as the backend publishes a finite decimal. */
const weight = (value: string): PacExactNumber => ({kind: 'finite_decimal', value});

/** An actual weight the backend published. */
const after = (value: string): PacNumberAvailability => ({kind: 'available', value: weight(value)});

/** An actual weight the backend could not publish: no bar is drawn for it, and its row keeps its colour. */
const UNPUBLISHED: PacNumberAvailability = {kind: 'unavailable', reason: 'dependency_unavailable'};

/** One row of a fixture, with what its actual weight is drawn in, spelled out. */
interface RowSpec {
    id: string;
    /** Asset types: the family the colour comes from. Absent for a sector and for the uncategorised remainder. */
    family?: string;
    /** Asset types: absent for the family's own colour, n for its n-th shade (GR4). */
    rank?: number;
    target: string;
    final: PacNumberAvailability;
}

interface Fixture {
    title: string;
    dimension: 'asset_type' | 'sector';
    rows: readonly RowSpec[];
}

/**
 * Asset types: the ETF family — its generic member and three subtypes, listed out of their order of ideal weight, so a
 * shade by position would differ from a shade by rank — a family with no subtype, a subtype with no generic member
 * beside it, and the uncategorised remainder. ETF_COMMODITY's actual weight is unpublished. Invented weights, summing to 1.
 */
const TYPE_FIXTURE: Fixture = {
    title: 'asset types',
    dimension: 'asset_type',
    rows: [
        {id: 'ETF', family: 'ETF', target: '0.30', final: after('0.27')},
        {id: 'ETF_BOND', family: 'ETF', rank: 2, target: '0.10', final: after('0.12')},
        {id: 'BOND', family: 'BOND', target: '0.15', final: after('0.15')},
        {id: 'ETF_STOCK', family: 'ETF', rank: 1, target: '0.20', final: after('0.22')},
        {id: 'ETF_COMMODITY', family: 'ETF', rank: 3, target: '0.05', final: UNPUBLISHED},
        {id: 'CROWDFUND_REAL_ESTATE', family: 'CROWDFUND', rank: 1, target: '0.12', final: after('0.10')},
        {id: UNCATEGORISED_CATEGORY_ID, target: '0.08', final: after('0.14')},
    ],
};

/** Sectors: five keys of the designer's table — `Other`, a sector of its own, among them — and the uncategorised remainder. */
const SECTOR_FIXTURE: Fixture = {
    title: 'sectors',
    dimension: 'sector',
    rows: [
        {id: 'Technology', target: '0.35', final: after('0.31')},
        {id: 'Health Care', target: '0.20', final: after('0.24')},
        {id: 'Energy', target: '0.15', final: after('0.11')},
        {id: 'Financials', target: '0.12', final: UNPUBLISHED},
        {id: 'Other', target: '0.10', final: after('0.12')},
        {id: UNCATEGORISED_CATEGORY_ID, target: '0.08', final: after('0.10')},
    ],
};

const FIXTURES: readonly Fixture[] = [TYPE_FIXTURE, SECTOR_FIXTURE];

/** The bars' `rows` prop for a fixture, with invented labels. */
function weightRows(fixture: Fixture): WeightRow[] {
    return fixture.rows.map((spec, index) => ({id: spec.id, label: `Row ${index + 1} (${spec.id})`, target: weight(spec.target), final: spec.final}));
}

/** Invented roles: the secondary text, which the ideal weight wears, and the card, the shades' near pole in the dark theme. */
interface InventedRoles {
    secondaryText: string;
    card: string;
}

type RoleSet = Readonly<Record<Theme, InventedRoles>>;

const ROLES: RoleSet = {
    light: {secondaryText: '#6b4f7a', card: '#f6f0e1'},
    dark: {secondaryText: '#a3b18c', card: '#2b1d36'},
};

/** A second set, as an edit of the roles in the Designer Lab would leave them. */
const EDITED_ROLES: RoleSet = {
    light: {secondaryText: '#3d6b74', card: '#eef6f1'},
    dark: {secondaryText: '#c79a6a', card: '#13262e'},
};

/** The theme <html> shows now: the one the bars draw. */
const themeNow = (): Theme => (document.documentElement.classList.contains('dark') ? 'dark' : 'light');

/** Answers the roles `current()` holds for the theme on screen, for the bars' own element, and nothing anywhere else. */
function injectRoles(current: () => RoleSet): void {
    setRoleReader((role, scope) => {
        if (scope?.getAttribute('data-testid') !== BARS_TESTID) return '';
        const roles = current()[themeNow()];
        if (role === '--lf-text-secondary') return roles.secondaryText;
        if (role === '--lf-surface-card') return roles.card;
        return '';
    });
}

type BarsComponent = typeof import('./ExposureBars.svelte').default;
type Taxonomy = typeof import('$lib/utils/assetTypes');

let ExposureBars: BarsComponent;
let K: Taxonomy;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the bars that import it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    K = await import('$lib/utils/assetTypes');
    ExposureBars = (await import('./ExposureBars.svelte')).default;
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
// The expectations, and the premises they rest on
// =============================================================================

/**
 * What each row's actual weight must be drawn in, in the order of the rows: computed from the fixture with the theme's
 * own functions, the shades on the poles of `card`.
 */
function expectedActual(fixture: Fixture, dark: boolean, card: string): string[] {
    const poles = shadePoles(dark, card);
    return fixture.rows.map((spec) => {
        if (spec.id === UNCATEGORISED_CATEGORY_ID) return categoryColor(fixture.dimension === 'asset_type' ? 'type' : 'sector', 'Unknown', dark);
        if (fixture.dimension === 'sector') return categoryColor('sector', spec.id, dark);
        const family = categoryColor('type', spec.family ?? '', dark);
        return spec.rank ? familyShade(family, spec.rank, poles) : family;
    });
}

/**
 * The premises the expectations rest on, checked rather than assumed. Every key has a colour of its own, so no row passes
 * on the fallback grey. On Asset types: every family is the one K files the row under; every rank is the rule's — the
 * row's place among its family's subtypes by ideal weight, largest first, the generic member none — with no tie for the
 * rule to break; the ETF subtypes are not listed in their order of rank; one subtype has no generic member beside it.
 */
function checkFixture(fixture: Fixture): void {
    const kind = fixture.dimension === 'asset_type' ? 'type' : 'sector';
    expect(
        fixture.rows.filter((spec) => spec.id === UNCATEGORISED_CATEGORY_ID),
        'one uncategorised row',
    ).toHaveLength(1);
    const keyed = fixture.rows.filter((spec) => spec.id !== UNCATEGORISED_CATEGORY_ID);
    const keyOf = (spec: RowSpec) => (kind === 'type' ? (spec.family ?? '') : spec.id);
    expect(
        keyed.filter((spec) => THEMES.some((theme) => categoryColor(kind, keyOf(spec), theme === 'dark') === categoryColor(kind, 'Unknown', theme === 'dark'))).map((spec) => spec.id),
        'rows whose key has no colour of its own',
    ).toEqual([]);
    if (kind === 'sector') return;

    expect(
        keyed.map((spec) => `${spec.id} in ${K.assetTypeFamily(spec.id)}`),
        'the families K files the rows under',
    ).toEqual(keyed.map((spec) => `${spec.id} in ${spec.family}`));
    const ruleRanks = new Map<string, number>();
    for (const family of new Set(keyed.map((spec) => spec.family))) {
        const subtypes = keyed.filter((spec) => spec.family === family && spec.id !== family).sort((left, right) => Number(right.target) - Number(left.target));
        expect(new Set(subtypes.map((spec) => Number(spec.target))).size, `two subtypes of ${family} share an ideal weight`).toBe(subtypes.length);
        subtypes.forEach((spec, index) => ruleRanks.set(spec.id, index + 1));
    }
    expect(
        keyed.map((spec) => `${spec.id} ${spec.rank ?? 0}`),
        'ranks by ideal weight, the generic member none',
    ).toEqual(keyed.map((spec) => `${spec.id} ${ruleRanks.get(spec.id) ?? 0}`));
    const etfSubtypes = keyed.filter((spec) => spec.family === 'ETF' && spec.id !== 'ETF');
    expect(
        etfSubtypes.map((spec) => spec.rank),
        'the ETF subtypes are listed in their order of rank: a shade by position would pass',
    ).not.toEqual(etfSubtypes.map((_spec, index) => index + 1));
    expect(
        keyed.filter((spec) => spec.id !== spec.family && !keyed.some((other) => other.id === spec.family)).map((spec) => spec.id),
        'no subtype without its generic member',
    ).not.toEqual([]);
}

// =============================================================================
// Reading what the bars drew
// =============================================================================

type FakeChart = (typeof chartInstances)[number];

/** A whole option, the fields these tests read: what one build of the bars hands ECharts. */
interface DrawnOption {
    legend: {data: unknown[]};
    tooltip: {formatter: (params: unknown) => string};
    yAxis: {data: string[]};
    series: Array<{name: string; itemStyle?: {color?: string}; data: unknown[]}>;
}

/** The keys of a whole option: every build of the bars hands ECharts all of them, a data-only update would not. */
const WHOLE_OPTION = ['grid', 'legend', 'tooltip', 'xAxis', 'yAxis', 'series'];

function isWholeOption(option: Record<string, unknown>): boolean {
    return WHOLE_OPTION.every((key) => key in option);
}

/** The latest whole option the one chart of the bars was handed. */
function lastOption(): DrawnOption {
    expect(chartInstances, 'the bars did not create exactly one chart').toHaveLength(1);
    const call = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => isWholeOption(option));
    if (!call) throw new Error('the bars never handed ECharts a whole option');
    return call.option as unknown as DrawnOption;
}

/** What the tooltip shows on row `index`: ECharts hands an axis tooltip one entry per series of the hovered category. */
function tooltipOf(option: DrawnOption, index: number): string {
    return option.tooltip.formatter([0, 1].map((seriesIndex) => ({componentType: 'series', seriesType: 'bar', seriesIndex, dataIndex: index})));
}

/** The colour of every dot in a tooltip, in order: the round swatches in front of its rows. */
function dotsOf(html: string): string[] {
    const host = document.createElement('div');
    host.innerHTML = html;
    return Array.from(host.querySelectorAll('span'))
        .map((span) => span.getAttribute('style') ?? '')
        .filter((style) => /border-radius:\s*50%/.test(style))
        .map((style) => /(?:^|;)\s*background:\s*([^;]+)/.exec(style)?.[1].trim() ?? '(a dot with no background)');
}

/** Mounts the bars on `rows` and waits for their first build. */
async function mountBars(rows: readonly WeightRow[], dimension: Fixture['dimension']) {
    const view = render(ExposureBars, {props: {rows, dimension}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the bars never drew').toBeGreaterThan(0));
    return view;
}

/** The latest build's series: the ideal one in the secondary text, each actual bar in its row's colour. */
function expectSeries(fixture: Fixture, rows: readonly WeightRow[], theme: Theme, roles: InventedRoles): void {
    const drawn = lastOption();
    const actual = expectedActual(fixture, theme === 'dark', roles.card);
    // Barrier: row i is the i-th category of both series, so each colour is read on the row it belongs to.
    expect(drawn.yAxis.data, 'the categories, in the order of the rows').toEqual(rows.map((row) => row.label));
    expect(
        drawn.series.map((series) => series.data.length),
        'one bar per row on each of the two series',
    ).toEqual([rows.length, rows.length]);

    expect(drawn.series[0].itemStyle?.color, 'the ideal series').toBe(roles.secondaryText);
    expect(
        drawn.series[1].data.map((item, index) => `${rows[index].id} ${(item as {itemStyle?: {color?: string}} | null)?.itemStyle?.color}`),
        'the actual bars, row by row',
    ).toEqual(rows.map((row, index) => `${row.id} ${actual[index]}`));
}

/** The latest build's legend — the ideal's swatch in its role, the actual's an outline on the card — and every row's tooltip dots. */
function expectLegendAndDots(fixture: Fixture, rows: readonly WeightRow[], theme: Theme, roles: InventedRoles): void {
    const drawn = lastOption();
    const actual = expectedActual(fixture, theme === 'dark', roles.card);
    const [idealSeries, actualSeries] = drawn.series;
    // Barrier: a legend entry is matched to its series by name, so the two names differ.
    expect(idealSeries.name, 'the two series share a name').not.toBe(actualSeries.name);

    expect(drawn.legend.data, 'the legend').toEqual([
        {name: idealSeries.name, itemStyle: {color: roles.secondaryText}},
        {name: actualSeries.name, itemStyle: {color: roles.card, borderColor: buildGridColors(theme === 'dark').textColor, borderWidth: 1}},
    ]);
    expect(
        rows.map((row, index) => `${row.id} ${dotsOf(tooltipOf(drawn, index)).join(' ')}`),
        'the two dots of each row’s tooltip: the ideal, then the actual weight',
    ).toEqual(rows.map((row, index) => `${row.id} ${roles.secondaryText} ${actual[index]}`));
}

/** Everything one build must hold: the series, the legend and the tooltips. */
function expectDrawn(fixture: Fixture, rows: readonly WeightRow[], theme: Theme, roles: InventedRoles): void {
    expectSeries(fixture, rows, theme, roles);
    expectLegendAndDots(fixture, rows, theme, roles);
}

/** Every call since `before` hands ECharts a whole option — a rebuild, never a data-only update — and there is one. */
function expectWholeOptionsSince(chart: FakeChart, before: number, what: string): void {
    const since = chart.setOptionCalls.slice(before);
    expect(since.length, `no option after ${what}`).toBeGreaterThan(0);
    expect(
        since.map(({option}) => WHOLE_OPTION.filter((key) => key in option).join('+')),
        `a call after ${what} that is not a whole option`,
    ).toEqual(since.map(() => WHOLE_OPTION.join('+')));
}

/** The brand greens the bars were drawn in before TD-1 (`PAC_EXPOSURE_BAR_COLORS`, light and dark, removed). */
const OLD_GREENS = ['#1a4031', '#00d681'];

/**
 * No brand green anywhere: in no option the bars handed ECharts, nor in any tooltip one of them could show. A positive
 * control first: the scan sees the colours drawn — the latest ideal among them — so it cannot pass by reading nothing.
 */
function expectNoOldGreens(rows: readonly WeightRow[], ideal: string): void {
    const options = chartInstances.flatMap((chart) => chart.setOptionCalls.map(({option}) => option));
    const tooltips = options.filter(isWholeOption).flatMap((option) => rows.map((_row, index) => tooltipOf(option as unknown as DrawnOption, index)));
    const drawn = [...options.map((option) => JSON.stringify(option)), ...tooltips].join('\n').toLowerCase();
    expect(drawn, 'the scan does not see the colours the bars drew').toContain(ideal.toLowerCase());
    expect(
        OLD_GREENS.filter((green) => drawn.includes(green)),
        'a brand green of the bars before TD-1',
    ).toEqual([]);
}

// =============================================================================
// TD-1 — the ideal in its neutral role, the actual weight in its category's colour
// =============================================================================

const CASES = FIXTURES.flatMap((fixture) => THEMES.map((theme) => ({fixture, title: fixture.title, theme})));

describe('ExposureBars — the ideal in its neutral role, each actual bar in its row’s category colour (TD-1)', () => {
    it.each(CASES)('$title, $theme theme: the ideal series in the secondary text, each actual bar in its row’s colour — the roles of the bars’ own element', async ({fixture, theme}) => {
        checkFixture(fixture);
        const dark = theme === 'dark';
        const roles = ROLES[theme];
        injectRoles(() => ROLES);
        document.documentElement.classList.toggle('dark', dark);
        // Controls: the invented roles are not the stand-ins, so a role read anywhere but the bars' element fails below;
        // in the dark theme, where the card is the shades' near pole, the invented card moves them; and no subtype is
        // expected in its family's own colour.
        expect(roles.secondaryText, 'control: the invented secondary text is the stand-in').not.toBe(chartRoles(dark).color('--lf-text-secondary'));
        expect(roles.card, 'control: the invented card is the stand-in').not.toBe(chartRoles(dark).color('--lf-surface-card'));
        const expected = expectedActual(fixture, dark, roles.card);
        if (fixture.dimension === 'asset_type') {
            if (dark) expect(expected, 'control: the card does not move the shades').not.toEqual(expectedActual(fixture, true, chartRoles(true).color('--lf-surface-card')));
            expect(
                fixture.rows.filter((spec, index) => spec.rank !== undefined && expected[index] === categoryColor('type', spec.family ?? '', dark)).map((spec) => spec.id),
                'control: a subtype expected in its family’s own colour',
            ).toEqual([]);
        }

        const rows = weightRows(fixture);
        await mountBars(rows, fixture.dimension);

        expectSeries(fixture, rows, theme, roles);
        expect(chartInstances[0].setOptionCalls.filter(({option}) => 'color' in option).length, 'an option handing ECharts a palette to paint a bar by its index').toBe(0);
        expectNoOldGreens(rows, roles.secondaryText);
    });

    it.each(CASES)('$title, $theme theme: the legend’s two swatches, and in each row’s tooltip a dot in each of the row’s two colours', async ({fixture, theme}) => {
        checkFixture(fixture);
        const dark = theme === 'dark';
        const roles = ROLES[theme];
        injectRoles(() => ROLES);
        document.documentElement.classList.toggle('dark', dark);
        // Control: the ideal is no row's colour, so the two dots of a row drawn the wrong way round fail below.
        expect(expectedActual(fixture, dark, roles.card), 'control: a row expected in the ideal colour').not.toContain(roles.secondaryText);

        const rows = weightRows(fixture);
        await mountBars(rows, fixture.dimension);

        expectLegendAndDots(fixture, rows, theme, roles);
        expectNoOldGreens(rows, roles.secondaryText);
    });
});

// =============================================================================
// Built again, whole, at a theme switch and at a chart-colour change (C4)
// =============================================================================

describe('ExposureBars — built again, whole, at a theme switch and at a chart-colour change (C4)', () => {
    it.each(FIXTURES)('$title: a theme switch on <html> builds the whole option again in the other theme’s roles and colours — and back', async (fixture) => {
        checkFixture(fixture);
        injectRoles(() => ROLES);
        const rows = weightRows(fixture);
        // Control: the themes differ on every actual bar, as on the invented roles, so bars deaf to a switch fail below.
        const [light, dark] = THEMES.map((theme) => expectedActual(fixture, theme === 'dark', ROLES[theme].card));
        expect(
            rows.filter((_row, index) => light[index] === dark[index]).map((row) => row.id),
            'control: rows in one colour in both themes',
        ).toEqual([]);

        await mountBars(rows, fixture.dimension);
        const [chart] = chartInstances;
        expectDrawn(fixture, rows, 'light', ROLES.light);

        for (const theme of ['dark', 'light'] as const) {
            const before = chart.setOptionCalls.length;
            document.documentElement.classList.toggle('dark', theme === 'dark');
            await waitFor(() => expectDrawn(fixture, rows, theme, ROLES[theme]));
            expectWholeOptionsSince(chart, before, `the switch to ${theme}`);
        }
        expect(chartInstances, 'a theme switch made a new chart').toHaveLength(1);
        expectNoOldGreens(rows, ROLES.light.secondaryText);
    });

    it.each(FIXTURES)('$title: notifyChartColorsChange() builds the whole option again with the roles read again — and nothing is drawn again before it', async (fixture) => {
        checkFixture(fixture);
        let current: RoleSet = ROLES;
        injectRoles(() => current);
        // The dark theme: there the card is the shades' near pole, so the subtypes' bars follow it as well.
        document.documentElement.classList.add('dark');
        const rows = weightRows(fixture);
        await mountBars(rows, fixture.dimension);
        const [chart] = chartInstances;
        expectDrawn(fixture, rows, 'dark', ROLES.dark);
        if (fixture.dimension === 'asset_type') expect(expectedActual(fixture, true, EDITED_ROLES.dark.card), 'control: the edited card does not move the shades').not.toEqual(expectedActual(fixture, true, ROLES.dark.card));

        current = EDITED_ROLES;
        const before = chart.setOptionCalls.length;
        // A role is read when the option is built: until the signal comes, the bars keep what they drew.
        flushSync();
        await tick();
        expect(chart.setOptionCalls.length, 'the bars were drawn again without being told their colours changed').toBe(before);

        notifyChartColorsChange();

        await waitFor(() => expectDrawn(fixture, rows, 'dark', EDITED_ROLES.dark));
        expectWholeOptionsSince(chart, before, 'the notification');
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
        expectNoOldGreens(rows, EDITED_ROLES.dark.secondaryText);
    });
});
