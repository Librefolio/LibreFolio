// @vitest-environment jsdom
/**
 * SemiDonutChart.test.ts — the colours the ownership half-donut hands ECharts, read off the real component.
 *
 * ## The subject: a colour per owner's key (§1.5) and the readable initial
 *
 * The owners of a broker have no category of their own to wear a colour by, so they take the first eight
 * asset types of the designer's palette (`CATEGORY_SEQUENCE`) — by their **key**, never by the order of
 * the data (round 3, §1.5): sorted by key — the user id, numbers by value, anything else as text — the
 * owner of rank `r` takes the `r`-th of the eight, then, past the eighth, the next round of the same
 * colours one GR4 shade further (`sequenceColor`), never a silent repeat. So the same owners keep each
 * its colour whatever order the data lists them in. The colour is the slice's and the disc's behind the
 * owner's initial, and the initial is written in whichever text reads best on that disc:
 * `chartRoles(dark, chart element).readableText(disc)`, the primary text or the inverse one.
 *
 * The donut is drawn again when the page's theme switches (backlog R-7: it used to keep the colours it
 * was first drawn with) and when the chart colours change without one (contract C4 with the Designer
 * Lab, `notifyChartColorsChange`), the roles read again from its own element.
 *
 * Expectations come from the theme's own functions — `sequenceColor`, `categoryColor`, `familyShade`,
 * `chartRoles` — never from copied hex values, which the theme's tests pin. Each owner's rank by key is
 * spelled out in the fixture, then checked against the rule. Role values are injected through
 * `setRoleReader`, reset after every test.
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

/** An owner as the donut receives it: its key (a user id), its name, its share, no avatar. */
interface Owner {
    key: string | number;
    name: string;
    percentage: number;
    avatarUrl: null;
}

/**
 * Ten owners, no avatar, 9% each: two past the eight colours of the sequence, and a tenth of the donut
 * still available. Every name starts with a different letter, so every disc carries its own initial. Their
 * keys are user ids, listed out of their order, and sorted as numbers they are not sorted as text (2 and 5
 * before 10 and 12): an order by position, or by text, would colour them otherwise.
 */
const OWNERS: readonly Owner[] = (
    [
        ['Alba', 12],
        ['Bruno', 3],
        ['Carla', 25],
        ['Dario', 1],
        ['Elena', 10],
        ['Fabio', 2],
        ['Gaia', 40],
        ['Ivo', 7],
        ['Luca', 31],
        ['Marta', 5],
    ] as const
).map(([name, key]) => ({key, name, percentage: 9, avatarUrl: null}));

/** Each owner's rank by key, spelled out: the place of its colour in the sequence (checked against the rule below). */
const RANK: Readonly<Record<string, number>> = {Dario: 0, Fabio: 1, Bruno: 2, Marta: 3, Ivo: 4, Elena: 5, Alba: 6, Carla: 7, Luca: 8, Gaia: 9};

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
async function mountDonut(owners: readonly Owner[] = OWNERS) {
    const view = render(SemiDonutChart, {props: {data: [...owners], availableLabel: AVAILABLE, height: '180px'}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the donut never drew').toBeGreaterThan(0));
    return view;
}

/** The colour of the owner of rank `rank` by key in `dark` (§1.5): the sequence, then a GR4 shade of it per round. */
function ownerColour(rank: number, dark: boolean, card = chartRoles(dark).color('--lf-surface-card')): string {
    return sequenceColor(CATEGORY_SEQUENCE, rank, dark, shadePoles(dark, card));
}

/** Each owner's name and expected colour, in the order of `owners`: the colour of its rank by key. */
function expectedByName(owners: readonly Owner[], dark: boolean, card?: string): string[] {
    return owners.map(({name}) => `${name} ${ownerColour(RANK[name], dark, card)}`);
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
// §1.5 — the owners take the sequence by their key, never by the order of the data
// =============================================================================

describe('SemiDonutChart — each owner in the colour of its key (§1.5)', () => {
    it('premises: the ranks spelled out are the owners sorted by key as numbers; the data lists them otherwise, and text would sort them otherwise', () => {
        const byKey = [...OWNERS].sort((a, b) => Number(a.key) - Number(b.key)).map(({name}) => name);
        expect(
            Object.entries(RANK)
                .sort(([, a], [, b]) => a - b)
                .map(([name]) => name),
        ).toEqual(byKey);
        expect(
            OWNERS.map(({name}) => name),
            'the data in the order of the keys: a colour by position would pass',
        ).not.toEqual(byKey);
        expect(
            [...OWNERS].sort((a, b) => String(a.key).localeCompare(String(b.key))).map(({name}) => name),
            'the keys sorted as text come out as sorted as numbers: a comparison of text would pass',
        ).not.toEqual(byKey);
        // The sequence is eight colours long, so the two last owners by key start its second round.
        expect(CATEGORY_SEQUENCE).toHaveLength(8);
    });

    it.each(THEMES)('$theme theme: the first eight owners by key in the first eight asset types, the ninth and tenth a first-round shade of the first two — on the slice and on the disc of the initial', async ({dark}) => {
        document.documentElement.classList.toggle('dark', dark);

        await mountDonut();
        const slices = ownerSlices();
        expect(
            slices.map((slice) => slice.name),
            'the slices in the order of the data',
        ).toEqual(OWNERS.map(({name}) => name));

        // Spelled out for the two rounds, then held to the function the donut is meant to call.
        const poles = shadePoles(dark, chartRoles(dark).color('--lf-surface-card'));
        const base = (rank: number) => categoryColor(CATEGORY_SEQUENCE[rank].kind, CATEGORY_SEQUENCE[rank].key, dark);
        const spelled = OWNERS.map(({name}) => `${name} ${RANK[name] < 8 ? base(RANK[name]) : familyShade(base(RANK[name] - 8), 1, poles)}`);
        expect(spelled).toEqual(expectedByName(OWNERS, dark));
        expect(slices.map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual(spelled);
        // The disc behind each initial is the slice's own colour.
        expect(slices.map((slice) => `${slice.name} ${String(slice.label?.rich?.avatar?.backgroundColor)}`)).toEqual(spelled);
        // Distinct, the second round included: no owner repeats another's colour in silence.
        expect(new Set(slices.map((slice) => slice.itemStyle?.color?.toLowerCase())).size).toBe(OWNERS.length);
        // The colours are on the slices, never in a list ECharts would hand out by index.
        expect(chartInstances[0].setOptionCalls.filter(({option}) => 'color' in option)).toEqual([]);
    });

    it('keeps each owner in its colour, on the slice and on the disc, when the data lists the same owners in another order', async () => {
        const colours = (slices: DrawnSlice[]) => Object.fromEntries(slices.map((slice) => [slice.name, `${slice.itemStyle?.color} ${String(slice.label?.rich?.avatar?.backgroundColor)}`]));
        const first = await mountDonut();
        const asListed = colours(ownerSlices());
        first.unmount();
        chartInstances.length = 0;

        const reordered = [...OWNERS.slice(5), ...OWNERS.slice(0, 5)].reverse();
        expect(
            reordered.map(({name}) => name),
            'control: another order',
        ).not.toEqual(OWNERS.map(({name}) => name));
        await mountDonut(reordered);

        expect(
            ownerSlices().map((slice) => slice.name),
            'the slices in the new order of the data',
        ).toEqual(reordered.map(({name}) => name));
        expect(colours(ownerSlices())).toEqual(asListed);
        expect(ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual(expectedByName(reordered, false));
    });

    it('compares numeric keys by value: the owner with key 2 comes before the one with key 10, though "10" sorts first as text', async () => {
        const owners: Owner[] = [
            {key: 10, name: 'Zeno', percentage: 30, avatarUrl: null},
            {key: 2, name: 'Yara', percentage: 30, avatarUrl: null},
        ];
        expect('10'.localeCompare('2'), 'control: as text, 10 comes first').toBeLessThan(0);

        await mountDonut(owners);

        expect(ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual([`Zeno ${ownerColour(1, false)}`, `Yara ${ownerColour(0, false)}`]);
    });

    it('compares keys that are not numbers as text', async () => {
        const owners: Owner[] = [
            {key: 'user-b', name: 'Zeno', percentage: 30, avatarUrl: null},
            {key: 'user-a', name: 'Yara', percentage: 30, avatarUrl: null},
        ];

        await mountDonut(owners);

        expect(ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual([`Zeno ${ownerColour(1, false)}`, `Yara ${ownerColour(0, false)}`]);
    });

    it('colours an owner by its key, whichever share it holds', async () => {
        // The shares reversed: the largest owner last. A colour handed out by share would move with them.
        const reversed = OWNERS.map((owner, index) => ({...owner, percentage: index + 1}));
        await mountDonut(reversed);

        expect(ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`)).toEqual(expectedByName(reversed, false));
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
        const named = () => ownerSlices().map((slice) => `${slice.name} ${slice.itemStyle?.color}`);
        expect(named()).toEqual(expectedByName(OWNERS, false));
        // Control: the two themes differ on every owner, so a donut that kept its first colours fails below.
        expect(OWNERS.filter(({name}) => ownerColour(RANK[name], false) === ownerColour(RANK[name], true))).toEqual([]);

        const beforeDark = chart.setOptionCalls.length;
        document.documentElement.classList.add('dark');
        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the theme switched').toBeGreaterThan(beforeDark));
        await waitFor(() => expect(named()).toEqual(expectedByName(OWNERS, true)));

        const beforeLight = chart.setOptionCalls.length;
        document.documentElement.classList.remove('dark');
        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the theme switched back').toBeGreaterThan(beforeLight));
        await waitFor(() => expect(named()).toEqual(expectedByName(OWNERS, false)));
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
        /** The owners of the second round, by key: the ninth and the tenth, wherever the data lists them. */
        const secondRound = OWNERS.filter(({name}) => RANK[name] >= CATEGORY_SEQUENCE.length);
        const secondRoundOf = (slices: DrawnSlice[]) => slices.filter((slice) => secondRound.some(({name}) => name === slice.name)).map((slice) => `${slice.name} ${slice.itemStyle?.color}`);
        expect(
            secondRound.map(({name}) => name),
            'barrier: two owners past the eighth',
        ).toHaveLength(2);

        await mountDonut();
        const [chart] = chartInstances;
        const textsOf = (slices: DrawnSlice[]) => slices.map((slice) => slice.label?.rich?.avatar?.color);
        expect(secondRoundOf(ownerSlices())).toEqual(expectedByName(secondRound, true, first['--lf-surface-card']));
        expect(textsOf(ownerSlices()).every((text) => text === first['--lf-text-primary'] || text === first['--lf-text-on-inverse'])).toBe(true);
        // Control: the new card moves the second round, so the comparison below cannot pass on the old one.
        expect(expectedByName(secondRound, true, next['--lf-surface-card'])).not.toEqual(expectedByName(secondRound, true, first['--lf-surface-card']));

        roles = next;
        const before = chart.setOptionCalls.length;
        notifyChartColorsChange();

        await waitFor(() => expect(chart.setOptionCalls.length, 'the donut was not drawn again after the notification').toBeGreaterThan(before));
        const slices = drawnSlices(chart.setOptionCalls.at(-1)!).filter((slice) => slice.name !== AVAILABLE);
        expect(secondRoundOf(slices)).toEqual(expectedByName(secondRound, true, next['--lf-surface-card']));
        expect(textsOf(slices)).toEqual(slices.map((slice) => chartRoles(true, chartElement()).readableText(String(slice.itemStyle?.color))));
        expect(
            textsOf(slices).filter((text) => text !== next['--lf-text-primary'] && text !== next['--lf-text-on-inverse']),
            'initials still in the old text roles',
        ).toEqual([]);
        expect(chartInstances, 'the notification made a new chart').toHaveLength(1);
    });
});
