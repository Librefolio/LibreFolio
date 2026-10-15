// @vitest-environment jsdom
/**
 * SemiDonutChart.test.ts — the colours the ownership half-donut hands ECharts, read off the real component.
 *
 * ## The subject: GR5.2 and the readable initial
 *
 * The owners of a broker have no key of their own to wear a colour by, so the designer's round 2 (D-T17,
 * GR5.2) gives them an order instead: owner `i` — its index in `data` — takes the `i`-th of the first
 * eight asset types (`CATEGORY_SEQUENCE`), then, past the eighth, the next round of the same colours one
 * GR4 shade further (`sequenceColor`), never a silent repeat. The colour is the slice's and the disc's
 * behind the owner's initial, and the initial is written in whichever text reads best on that disc:
 * `chartRoles(dark, chart element).readableText(disc)`, the primary text or the inverse one.
 *
 * The donut is drawn again when the page's theme switches (backlog R-7: it used to keep the colours it
 * was first drawn with) and when the chart colours change without one (contract C4 with the Designer
 * Lab, `notifyChartColorsChange`), the roles read again from its own element.
 *
 * Expectations come from the theme's own functions — `sequenceColor`, `categoryColor`, `familyShade`,
 * `chartRoles` — never from copied hex values, which the theme's tests pin. Role values are injected
 * through `setRoleReader`, reset after every test.
 *
 * ## What is replaced, and why
 *
 * - `echarts`: a recorder, not a renderer — jsdom has no canvas — as in `AllocationPieChart.test.ts`. It
 *   answers what the donut and its helpers call on an instance and keeps every `setOption` payload.
 * - Nothing else. jsdom lays nothing out, so the donut's wait for a sized container runs its four frames
 *   and draws anyway, as it does in a browser tab that is still laying out. No owner has an avatar: an
 *   image never loads in jsdom, and the initial on its disc is the subject.
 *
 * `BrokerSharingPanel.test.ts` mounts the panel with a stub in place of this chart, so the chart's own
 * drawing is tested here, alone.
 *
 * Nothing translated is asserted: the owners' names and the label of the available share are props.
 *
 * @module components/charts/SemiDonutChart.test
 */
import {afterEach, beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/**
 * The ECharts stand-in: it answers every call the donut and its helpers make on an instance
 * (`attachChartReady` → `on`, `scheduleFirstRenderStabilityFix` → `isDisposed`/`resize`, the teardown →
 * `dispose`) and keeps every `setOption` payload.
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

import {render, setupI18n, waitFor} from '$test/component';
import {CATEGORY_SEQUENCE, categoryColor, sequenceColor} from '$lib/theme/chartCategories';
import {familyShade, shadePoles} from '$lib/theme/chartShades';
import {chartRoles, setRoleReader, type ChartRole} from '$lib/theme/roleColors';
import {notifyChartColorsChange} from '$lib/theme/themeMode';
import SemiDonutChart from './SemiDonutChart.svelte';

// =============================================================================
// Fixtures
// =============================================================================

/** The label of the share still available: a prop, so the test's own word. */
const AVAILABLE = 'Still available';

/**
 * Ten owners, no avatar, 9% each: two past the eight colours of the sequence, and a tenth of the donut
 * still available. Every name starts with a different letter, so every disc carries its own initial.
 */
const OWNERS = ['Alba', 'Bruno', 'Carla', 'Dario', 'Elena', 'Fabio', 'Gaia', 'Ivo', 'Luca', 'Marta'].map((name) => ({name, percentage: 9, avatarUrl: null}));

/** The two themes, as the donut reads them off the `dark` class of <html> when it draws. */
const THEMES = [
    {theme: 'light', dark: false},
    {theme: 'dark', dark: true},
] as const;

/** A slice as the donut hands it to ECharts: the fields these tests read. */
interface DrawnSlice {
    name: string;
    value: number;
    itemStyle?: {color?: string};
    label?: {formatter?: string; rich?: {avatar?: {color?: string; backgroundColor?: unknown}}};
}

/** What one draw handed ECharts: its slices, owners first, the available share last. */
function drawnSlices(call: {option: Record<string, unknown>}): DrawnSlice[] {
    const series = call.option.series as Array<{data: DrawnSlice[]}> | undefined;
    if (!series?.[0]) throw new Error('a draw without a series');
    return series[0].data;
}

/** The last draw of the one chart the donut made. */
function lastDraw() {
    expect(chartInstances, 'the donut did not create exactly one chart').toHaveLength(1);
    const call = chartInstances[0].setOptionCalls.at(-1);
    if (!call) throw new Error('the donut never handed ECharts an option');
    return call;
}

/** The owners' slices of the last draw, the available share left out. */
function ownerSlices(): DrawnSlice[] {
    return drawnSlices(lastDraw()).filter((slice) => slice.name !== AVAILABLE);
}

/** Mounts the donut on `owners` and waits for its first draw. */
async function mountDonut(owners = OWNERS) {
    const view = render(SemiDonutChart, {props: {data: owners, availableLabel: AVAILABLE, height: '180px'}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the donut never drew').toBeGreaterThan(0));
    return view;
}

/** The colour of owner `index` in `dark`, by GR5.2: the sequence, then a GR4 shade of it per round. */
function ownerColour(index: number, dark: boolean, card = chartRoles(dark).color('--lf-surface-card')): string {
    return sequenceColor('type', CATEGORY_SEQUENCE, index, dark, shadePoles(dark, card));
}

beforeAll(async () => {
    await setupI18n();
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
// GR5.2 — the owners take the sequence in order
// =============================================================================

describe('SemiDonutChart — each owner in the colour of its place (GR5.2)', () => {
    it.each(THEMES)('$theme theme: owner i in the i-th of the first eight asset types, the ninth and tenth a first-round shade of the first two — on its slice and on the disc of its initial', async ({dark}) => {
        // Premise: the sequence is eight colours long, so the last two owners start its second round.
        expect(CATEGORY_SEQUENCE).toHaveLength(8);
        document.documentElement.classList.toggle('dark', dark);

        await mountDonut();
        const slices = ownerSlices();
        expect(slices.map((slice) => slice.name)).toEqual(OWNERS.map(({name}) => name));

        // Spelled out for the two rounds, then held to the function the donut is meant to call.
        const poles = shadePoles(dark, chartRoles(dark).color('--lf-surface-card'));
        const expected = OWNERS.map((_owner, index) => (index < 8 ? categoryColor('type', CATEGORY_SEQUENCE[index], dark) : familyShade(categoryColor('type', CATEGORY_SEQUENCE[index - 8], dark), 1, poles)));
        expect(expected).toEqual(OWNERS.map((_owner, index) => ownerColour(index, dark)));
        expect(slices.map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual(OWNERS.map(({name}, index) => `${name} ${expected[index]}`));
        // The disc behind each initial is the slice's own colour.
        expect(slices.map((slice) => `${slice.name} ${String(slice.label?.rich?.avatar?.backgroundColor)}`)).toEqual(OWNERS.map(({name}, index) => `${name} ${expected[index]}`));
        // Distinct, the second round included: no owner repeats another's colour in silence.
        expect(new Set(expected.map((colour) => colour.toLowerCase())).size).toBe(OWNERS.length);
        // The colours are on the slices, never in a list ECharts would hand out by index.
        expect(chartInstances[0].setOptionCalls.filter(({option}) => 'color' in option)).toEqual([]);
    });

    it('colours an owner by its index in data, whichever share it holds', async () => {
        // The shares reversed: the largest owner last. A colour handed out by share would move with them.
        const reversed = OWNERS.map((owner, index) => ({...owner, percentage: index + 1}));
        await mountDonut(reversed);

        expect(ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual(reversed.map(({name}, index) => `${name} ${ownerColour(index, false)}`));
    });
});

// =============================================================================
// The initial — in the text that reads best on its disc
// =============================================================================

describe('SemiDonutChart — the initial on each disc, in the text that reads best on it', () => {
    it.each(THEMES)("$theme theme: every initial in chartRoles(…).readableText of its disc, the roles read from the donut's own element", async ({dark}) => {
        // Text roles of the test's own, answered only for the donut's element: a text read anywhere else —
        // <html>, a stand-in, a literal — would be neither of them.
        const roles: Partial<Record<ChartRole, string>> = {'--lf-text-primary': '#102030', '--lf-text-on-inverse': '#f4ead8'};
        const chartElement = () => (chartInstances[0]?.getDom() as Element | undefined) ?? null;
        setRoleReader((role, scope) => (scope !== null && scope === chartElement() ? (roles[role] ?? '') : ''));
        document.documentElement.classList.toggle('dark', dark);

        await mountDonut();
        const slices = ownerSlices();
        const ownRoles = chartRoles(dark, chartElement());

        expect(slices.map((slice) => `${slice.name} ${slice.label?.rich?.avatar?.color}`)).toEqual(slices.map((slice) => `${slice.name} ${ownRoles.readableText(String(slice.itemStyle?.color))}`));
        expect(
            slices.filter((slice) => !Object.values(roles).includes(String(slice.label?.rich?.avatar?.color))).map((slice) => slice.name),
            "initials not in one of the donut's own text roles",
        ).toEqual([]);
        // The initial itself, on its disc.
        expect(slices.map((slice) => slice.label?.formatter?.split('|')[1]?.charAt(0))).toEqual(OWNERS.map(({name}) => name.charAt(0)));
    });

    it('chooses per disc: in the light theme the dark discs carry the light text and the light ones the dark text', async () => {
        await mountDonut();
        const slices = ownerSlices();
        const roles = chartRoles(false);
        const [primary, inverse] = [roles.color('--lf-text-primary'), roles.color('--lf-text-on-inverse')];

        // A constant text would pass the test above on discs that all asked for it: these ask for both.
        const texts = new Set(slices.map((slice) => slice.label?.rich?.avatar?.color));
        expect(texts, `the initials of the light theme's owners are all written in one text: ${[...texts].join(', ')}`).toEqual(new Set([primary, inverse]));
    });
});

// =============================================================================
// Redrawn when the theme switches (R-7) or the chart colours change (C4)
// =============================================================================

describe('SemiDonutChart — redrawn when the theme switches (R-7) or its colours change (C4)', () => {
    it('a switch of the `dark` class of <html> draws the owners again, in the other theme’s colours — and back', async () => {
        await mountDonut();
        const [chart] = chartInstances;
        expect(ownerSlices().map((slice) => slice.itemStyle?.color)).toEqual(OWNERS.map((_owner, index) => ownerColour(index, false)));
        const dark = OWNERS.map((_owner, index) => ownerColour(index, true));
        // Control: the two themes differ on every owner, so a donut that kept its first colours fails below.
        expect(OWNERS.filter((_owner, index) => ownerColour(index, false) === dark[index])).toEqual([]);

        const beforeDark = chart.setOptionCalls.length;
        document.documentElement.classList.add('dark');
        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the theme switched').toBeGreaterThan(beforeDark));
        await waitFor(() => expect(ownerSlices().map((slice) => slice.itemStyle?.color)).toEqual(dark));

        const beforeLight = chart.setOptionCalls.length;
        document.documentElement.classList.remove('dark');
        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the theme switched back').toBeGreaterThan(beforeLight));
        await waitFor(() => expect(ownerSlices().map((slice) => slice.itemStyle?.color)).toEqual(OWNERS.map((_owner, index) => ownerColour(index, false))));
        expect(chartInstances, 'a theme switch made a new chart').toHaveLength(1);
    });

    it('notifyChartColorsChange() draws it again with the roles read again: the initials follow the new text roles, the second round the new card', async () => {
        const first: Partial<Record<ChartRole, string>> = {'--lf-text-primary': '#102030', '--lf-text-on-inverse': '#f4ead8', '--lf-surface-card': '#2a1f3d'};
        const next: Partial<Record<ChartRole, string>> = {'--lf-text-primary': '#301020', '--lf-text-on-inverse': '#e0f4d8', '--lf-surface-card': '#1f3d2a'};
        let roles = first;
        const chartElement = () => (chartInstances[0]?.getDom() as Element | undefined) ?? null;
        setRoleReader((role, scope) => (scope !== null && scope === chartElement() ? (roles[role] ?? '') : ''));
        // The dark theme: its shades go toward the card, so the second round follows the card too.
        document.documentElement.classList.add('dark');

        await mountDonut();
        const [chart] = chartInstances;
        const textsOf = (slices: DrawnSlice[]) => slices.map((slice) => slice.label?.rich?.avatar?.color);
        expect(
            ownerSlices()
                .map((slice) => slice.itemStyle?.color)
                .slice(8),
        ).toEqual([8, 9].map((index) => ownerColour(index, true, first['--lf-surface-card'])));
        expect(textsOf(ownerSlices()).every((text) => text === first['--lf-text-primary'] || text === first['--lf-text-on-inverse'])).toBe(true);
        // Control: the new card moves the second round, so the comparison below cannot pass on the old one.
        expect([8, 9].map((index) => ownerColour(index, true, next['--lf-surface-card']))).not.toEqual([8, 9].map((index) => ownerColour(index, true, first['--lf-surface-card'])));

        roles = next;
        const before = chart.setOptionCalls.length;
        notifyChartColorsChange();

        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the notification').toBeGreaterThan(before));
        const slices = drawnSlices(chart.setOptionCalls.at(-1)!).filter((slice) => slice.name !== AVAILABLE);
        expect(slices.map((slice) => slice.itemStyle?.color).slice(8)).toEqual([8, 9].map((index) => ownerColour(index, true, next['--lf-surface-card'])));
        expect(textsOf(slices)).toEqual(slices.map((slice) => chartRoles(true, chartElement()).readableText(String(slice.itemStyle?.color))));
        expect(
            textsOf(slices).filter((text) => text !== next['--lf-text-primary'] && text !== next['--lf-text-on-inverse']),
            'initials still in the old text roles',
        ).toEqual([]);
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
    });
});
