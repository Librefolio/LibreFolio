// @vitest-environment jsdom
/**
 * AllocationPieChart.tooltipEscape.test.ts — K-15: the allocation pie's tooltip escapes every text it interpolates.
 *
 * ## What it protects (K-15)
 *
 * ECharts sets what a tooltip formatter returns as `innerHTML`. Every text the pie's formatter interpolates must
 * therefore be escaped, or a label that holds markup becomes markup. The verdict, on a payload whose markup carries a
 * marker (`PAYLOAD`): parsed into a detached element, the tooltip holds no `[data-pwned]` element, and its text holds the
 * payload verbatim — escaped markup reads as text. Nothing is asserted about the pie's own markup: the type icon is an
 * `<img>` the component writes on purpose.
 *
 * ## Why it is red today
 *
 * `AllocationPieChart.svelte`, `tooltipFormatter` (:442–:483), in `mode === 'type'`:
 * - (i) the arc's title `translated` (:455) — `params.data.caption`, else the type's translation — is interpolated raw
 *   in the returned HTML (:479);
 * - (ii) the parent line's `parentLabel` (:471–:473) — the family's translation or, when there is none, the raw
 *   `primaryKey` — is interpolated raw (:477). The line shows when `showParent && primaryKey` (:468–:470): with two
 *   rings on an outer-ring member (`ringRole === 'member'`), with one ring when `groupSize > 1`. Both are covered.
 * - (iii) the `params.name` fallback of the title (`tr(…) || params.name`, :455) is unreachable: svelte-i18n answers a
 *   missing key with the key itself, never `''` (`formatMessage`: `handleMissingMessage ?? defaultValue ?? id`, and no
 *   `handleMissingMessage` is configured), and the key is built from the sanitised `rawKey` (`[A-Z_]` only). It is
 *   pinned green: whatever the title falls back to, `params.name` injects nothing.
 *
 * The sector mode already escapes `params.name` (:482): it is the green guard of the harness and of the verdict, driven
 * through real data — a slice named after the payload.
 *
 * ## How
 *
 * The real component in jsdom, ECharts replaced by a recorder — the pattern of `AllocationPieChart.test.ts`. A tooltip is
 * the formatter the component handed ECharts, called the way ECharts calls it on hover: with an arc of the series it
 * drew, one field overridden where a case says so. The pie imports K's `assetTypes.ts`, which reads the generated
 * client at module load, so the component is imported after asserting the generated file exists.
 *
 * Registered in chart-safety-unit (scripts/test_runner/_frontend_portfolio.py).
 */
import {existsSync} from 'node:fs';
import {join} from 'node:path';
import {beforeAll, beforeEach, describe, expect, it, vi} from 'vitest';

/** The ECharts stand-in: a recorder, not a renderer. It keeps every `setOption` payload. */
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

/** GET /utilities/sectors, the one call the sector pie makes; every other endpoint answers an empty list. */
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

import {get} from 'svelte/store';
import {render, setupI18n, waitFor} from '$test/component';
import {_} from '$lib/i18n';

// =============================================================================
// Fixtures
// =============================================================================

/** The generated client, from the frontend root vitest runs in (see `AllocationPieChart.test.ts` for why not a URL). */
const GENERATED_TS = join(process.cwd(), 'src', 'lib', 'api', 'generated.ts');

/** Markup whose element carries a marker: present after parsing only if it was interpolated unescaped. */
const PAYLOAD = '<b data-pwned="1">X</b>';

/** A family key no catalogue translates: the parent line writes it as it is. */
const UNTRANSLATED_FAMILY = 'ZZ_NO_SUCH_FAMILY';

/** One slice of `allocation_by_type` (or `by_sector`), as the Dashboard hands it to the pie. Synthetic values. */
interface Slice {
    name: string;
    value: number;
    amount: number;
}

const slice = (name: string, value: number): Slice => ({name, value, amount: value * 100});

/** ETF split by its stock subtype, beside a bond: the pie draws two rings, the members on the outer one. */
const SPLIT_CASE: Slice[] = [slice('ETF', 30), slice('ETF_STOCK', 25), slice('BOND', 45)];

/** No subtype anywhere: the pie draws one ring. */
const FLAT_CASE: Slice[] = [slice('STOCK', 60), slice('BOND', 40)];

/** The sector list, with invented emoji, as the sector store reads it. */
const SECTOR_LIST = {
    items: [{key: 'Technology', emoji: '🧬'}],
    buckets: [{key: 'Unknown', emoji: '🫥'}],
    fallback_emoji: '🫧',
};

/** An arc as the pie hands it to ECharts: the fields its tooltip reads. */
interface DrawnArc {
    name: string;
    value: number;
    amount?: number;
    rawName: string;
    primaryKey?: string;
    caption?: string;
    ringRole?: 'base' | 'member' | 'filler';
    groupSize?: number;
    primaryTotal?: number;
}

interface Drawing {
    /** Whether the pie drew the two rings of D72. */
    rings: boolean;
    /** The inner ring — or the only one. */
    inner: DrawnArc[];
    /** The outer ring; empty with one ring. */
    outer: DrawnArc[];
    /** The HTML the tooltip shows when `arc` is hovered. */
    tooltipOf: (arc: DrawnArc) => string;
}

type PieComponent = typeof import('./AllocationPieChart.svelte').default;
let AllocationPieChart: PieComponent;

beforeAll(async () => {
    expect(existsSync(GENERATED_TS), 'src/lib/api/generated.ts is absent, so assetTypes.ts — and the pie that imports it — cannot be loaded. Run `./dev.py api sync`.').toBe(true);
    await setupI18n();
    AllocationPieChart = (await import('./AllocationPieChart.svelte')).default;
    sectorsEndpoint.mockResolvedValue(SECTOR_LIST);
    // The dynamic import compiles the component tree inside this hook: a budget of its own under a loaded machine.
}, 60_000);

beforeEach(() => {
    chartInstances.length = 0;
});

// =============================================================================
// Reading what the pie drew
// =============================================================================

/** Mount the pie as the Dashboard's allocation panel does, and read its last full build. */
async function drawPie(data: Slice[], mode: 'type' | 'sector' = 'type'): Promise<Drawing> {
    render(AllocationPieChart, {props: {data, mode, legendPosition: 'bottom', currency: 'EUR'}});
    await waitFor(() => expect(chartInstances[0]?.setOptionCalls.length ?? 0, 'the pie never drew').toBeGreaterThan(0), {timeout: 5_000});
    return drawing();
}

/** The last full build the pie handed ECharts — the one that carries the tooltip. */
function drawing(): Drawing {
    expect(chartInstances, 'the pie did not create exactly one chart').toHaveLength(1);
    const build = [...chartInstances[0].setOptionCalls].reverse().find(({option}) => option.tooltip !== undefined);
    if (!build) throw new Error('the pie never handed ECharts a full option');
    const series = build.option.series as Array<{id?: string; data: DrawnArc[]}>;
    const formatter = (build.option.tooltip as {formatter: (params: unknown) => string}).formatter;
    const tooltipOf = (arc: DrawnArc) => formatter({componentType: 'series', seriesType: 'pie', name: arc.name, value: arc.value, data: arc});
    const rings = series.some((entry) => entry.id === 'alloc-base');
    return {rings, inner: series[0].data, outer: rings ? series[1].data : [], tooltipOf};
}

/** A member arc of the outer ring: the arc whose tooltip carries the parent line with two rings. */
function memberOf(drawn: Drawing): DrawnArc {
    expect(drawn.rings, 'barrier: a family split by a subtype is drawn on two rings').toBe(true);
    const member = drawn.outer.find((arc) => arc.ringRole === 'member');
    if (!member) throw new Error('the outer ring holds no member arc');
    return member;
}

/** The arc drawn for `type` on a single ring. */
function arcOf(drawn: Drawing, type: string): DrawnArc {
    const arc = drawn.inner.find((candidate) => candidate.rawName === type);
    if (!arc) throw new Error(`the pie drew no arc for ${type}`);
    return arc;
}

/** A tooltip's HTML parsed into a detached element, as the browser parses it when ECharts sets it. */
function parse(html: string): HTMLDivElement {
    const host = document.createElement('div');
    host.innerHTML = html;
    return host;
}

/** The verdict on a tooltip that interpolates PAYLOAD: escaped, it injects no element and reads as the payload's own text. */
function expectEscaped(html: string, where: string): void {
    const host = parse(html);
    expect(host.querySelector('[data-pwned]'), `${where}: the payload became an element — it was interpolated unescaped. Tooltip HTML: ${html}`).toBeNull();
    expect(host.textContent ?? '', `${where}: the payload does not read as text — is it on this path at all? Tooltip HTML: ${html}`).toContain(PAYLOAD);
}

// =============================================================================
// K-15 — the tooltip escapes what it interpolates
// =============================================================================

describe('AllocationPieChart — the tooltip escapes every text it interpolates (K-15)', {timeout: 20_000}, () => {
    it('harness — the catalogue is loaded, and a type key it does not hold (the payload) is answered with the key itself', () => {
        const tr = get(_);
        expect(tr('assets.types.ETF'), 'the catalogue is not loaded: every label would be its own key').not.toBe('assets.types.ETF');
        expect(tr(`assets.types.${PAYLOAD}`), 'a missing type key is not answered with itself: the parent line would not fall back to the raw key').toBe(`assets.types.${PAYLOAD}`);
    });

    it('guard — sector mode escapes params.name (:482): a slice named after the payload reads as text, nothing is injected', async () => {
        const drawn = await drawPie([slice(PAYLOAD, 40), slice('Technology', 60)], 'sector');

        expectEscaped(drawn.tooltipOf(arcOf(drawn, PAYLOAD)), 'sector tooltip');
    });

    it('guard — the parent line writes an untranslated family as its key, and a clean arc passes the verdict with its own <img>', async () => {
        const drawn = await drawPie(SPLIT_CASE);
        const member = memberOf(drawn);

        const clean = parse(drawn.tooltipOf(member));
        expect(clean.querySelector('img'), "the type icon — the component's own markup — is not drawn").not.toBeNull();
        expect(clean.querySelector('[data-pwned]')).toBeNull();

        expect(get(_)(`assets.types.${UNTRANSLATED_FAMILY}`), 'precondition: the catalogue translates the made-up family').toBe(`assets.types.${UNTRANSLATED_FAMILY}`);
        expect(parse(drawn.tooltipOf({...member, primaryKey: UNTRANSLATED_FAMILY})).textContent ?? '', 'the parent line does not write an untranslated family as its key: the fallback the (ii) cases go through is not taken').toContain(UNTRANSLATED_FAMILY);
    });

    it('(i) the arc title escapes a caption that holds markup (:455 → :479)', async () => {
        const drawn = await drawPie(SPLIT_CASE);
        const member = memberOf(drawn);

        expectEscaped(drawn.tooltipOf({...member, caption: PAYLOAD}), 'type tooltip, title from data.caption');
    });

    it('(ii) the parent line of an outer-ring member escapes a family key with markup and no translation (:473 → :477)', async () => {
        const drawn = await drawPie(SPLIT_CASE);
        const member = memberOf(drawn);

        expectEscaped(drawn.tooltipOf({...member, primaryKey: PAYLOAD}), 'type tooltip, parent line on two rings');
    });

    it('(ii) the parent line on a single ring (groupSize > 1) escapes the same fallback (:468, :473 → :477)', async () => {
        const drawn = await drawPie(FLAT_CASE);
        expect(drawn.rings, 'barrier: no subtype, one ring').toBe(false);

        expectEscaped(drawn.tooltipOf({...arcOf(drawn, 'STOCK'), groupSize: 2, primaryKey: PAYLOAD}), 'type tooltip, parent line on one ring');
    });

    it('(iii) guard — the params.name fallback of the title is unreachable: with no caption and an unknown type, params.name injects nothing', async () => {
        const drawn = await drawPie(FLAT_CASE);
        const arc = arcOf(drawn, 'STOCK');

        const html = drawn.tooltipOf({...arc, name: PAYLOAD, rawName: PAYLOAD, caption: undefined});

        expect(parse(html).querySelector('[data-pwned]'), `params.name reached the title unescaped. Tooltip HTML: ${html}`).toBeNull();
    });
});
