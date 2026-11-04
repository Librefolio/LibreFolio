/**
 * chartTheme.test.ts — the shape of the chart colour tables, whatever tables they hold; and the neutrals of the charts on
 * the colour roles.
 *
 * `chartTheme.ts` and `chartPalettes.ts` are the one home of the chart colours: the charts read their values there,
 * copied by hand from where each chart used to write them, and more tables are on their way. A slip in them is silent
 * on screen — a canvas ignores a colour it cannot parse and paints on with the one before it, a pair missing a theme
 * hands that theme `undefined`, a dark list one entry short gives a category another colour family when the theme
 * changes, a list that repeats an entry gives two categories one colour — and nothing else would notice: the
 * refactor's whole point is that no pixel changed.
 *
 * So every export of both modules is walked, at any depth, and held to the shape the tables share:
 *
 * - an object with a `light` key has a `dark` key, and the other way round, the two of one kind;
 * - every string is a colour in a notation the tables use — `#rgb`, `#rrggbb`, `#rrggbbaa`, `rgb()`, `rgba()`,
 *   `hsl()`, `hsla()` — with its numbers in range. Another notation is refused until it is added here, on purpose;
 * - a list never repeats an entry, and the two lists of a pair have the same length;
 * - `themed(pair, dark)` hands back the very member of the theme, for every pair found.
 *
 * Walked, never listed: a table added tomorrow is held to the same rules without anyone touching this file. A walk
 * that finds nothing breaks no rule, so it must reach tables known to exist, and each rule is shown to fail on a
 * synthetic table that breaks it. A function export — `growthBrokerColor`, `chartNeutrals` — is behaviour read at each
 * draw, not a table: the walk skips it.
 *
 * **The neutrals on roles (B4, DV).** Axes, grids, labels, tooltip boxes, pointers, gaps and rings left the tables for
 * `chartNeutrals(dark, scope)`, which reads the roles of tokens.css through `chartRoles` at each draw. What it owns is
 * which role each neutral reads, and at what alpha in each theme, so that is what is pinned here, against a table written
 * by hand from DV's plan (section «B4», «La mappa, per ruolo»):
 *
 * - an injected reader (`setRoleReader`) answers every role with a colour of its own, so a neutral on another role, at
 *   another alpha, or hard-coded rather than read is red, in either theme;
 * - the table and the object are held to each other both ways: a neutral added without a row, or a row left without a
 *   neutral, is red;
 * - the roles are read on the element the chart hands over (`scope`), and on none when there is neither a scope nor a
 *   page;
 * - with no reader and no page, the stand-ins draw colours a canvas can paint, and the theme picks them.
 *
 * The mapping is the nearest role, «da rivedere» with the designer (D-T27): a change of mind is a row changed here. The
 * colours of the roles are tokens.css's, kept by the parity gate of `roleColors.test.ts`, and are not pinned here.
 *
 * `chartCategories.ts` is not walked: its exports are lists of keys, not colours, and its colour tables are private on
 * purpose (one read point, `categoryColor`, contract C1 with the Designer Lab). Its values, their shape and how far
 * apart they are, are `chartCategories.test.ts`'s.
 *
 * The values are not pinned: a value is the designer's call, its shape is not.
 *
 * No runes, no DOM: this stays in the default `node` environment, which the tests of the neutrals count on — with no
 * page there is no `<html>` to read on, so a role reads its stand-in unless a reader is injected.
 *
 * @module lib/theme/chartTheme.test
 */
import {afterEach, describe, expect, it, vi} from 'vitest';

import {chartNeutrals} from './chartTheme';
import {toRgba} from './colorAlpha';
import {type ChartRole, type RoleReader, setRoleReader} from './roleColors';
import {themed, type ThemePair} from './themePair';

/**
 * Both modules, every export. Through `vi.importActual` rather than `import * as`: knip reads a namespace walked whole
 * as a use of every export, and would stop reporting a table no chart reads any more.
 */
const MODULES: Record<string, Record<string, unknown>> = {
    chartTheme: await vi.importActual('./chartTheme'),
    chartPalettes: await vi.importActual('./chartPalettes'),
};

// =============================================================================
// The rules
// =============================================================================

/** One argument of a colour function: its form, the number in it, and the largest that number may be. */
interface ColourArgument {
    form: RegExp;
    max: number;
}

const RGB_CHANNEL: ColourArgument = {form: /^(\d{1,3})$/, max: 255};
const HUE: ColourArgument = {form: /^(\d{1,3}(?:\.\d+)?)(?:deg)?$/, max: 360};
const PERCENTAGE: ColourArgument = {form: /^(\d{1,3}(?:\.\d+)?)%$/, max: 100};
const ALPHA: ColourArgument = {form: /^(\d?\.\d+|\d)$/, max: 1};

/** The colour functions the tables use, with their arguments in order: the comma notation, the alpha in 0-1. */
const COLOUR_FUNCTIONS: Record<string, readonly ColourArgument[]> = {
    rgb: [RGB_CHANNEL, RGB_CHANNEL, RGB_CHANNEL],
    rgba: [RGB_CHANNEL, RGB_CHANNEL, RGB_CHANNEL, ALPHA],
    hsl: [HUE, PERCENTAGE, PERCENTAGE],
    hsla: [HUE, PERCENTAGE, PERCENTAGE, ALPHA],
};

/** Why `value` is not a colour in a notation the tables use — `null` when it is one. */
function colourProblem(value: string): string | null {
    if (/^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value)) return null;
    const call = /^(rgba?|hsla?)\(([^()]*)\)$/.exec(value);
    if (!call) return 'not #rgb, #rrggbb, #rrggbbaa, rgb(), rgba(), hsl() or hsla()';

    const [, name, body] = call;
    const expected = COLOUR_FUNCTIONS[name];
    const args = body.split(',').map((arg) => arg.trim());
    if (args.length !== expected.length) return `${name}() takes ${expected.length} arguments, not ${args.length}`;
    const wrong = args.filter((arg, index) => {
        const number = expected[index].form.exec(arg);
        return !number || Number(number[1]) > expected[index].max;
    });
    return wrong.length === 0 ? null : `${name}() argument out of form or range: ${wrong.join(', ')}`;
}

/** The same colour written alike, to find a repeat: lower case, no spaces, `#rgb` doubled to `#rrggbb`. */
function normalised(colour: string): string {
    const compact = colour.toLowerCase().replace(/\s+/g, '');
    return /^#[0-9a-f]{3}$/.test(compact) ? `#${[...compact.slice(1)].map((digit) => digit + digit).join('')}` : compact;
}

/** What a value is, as a defect names it. */
function kindOf(value: unknown): string {
    if (Array.isArray(value)) return 'list';
    return value === null ? 'null' : typeof value;
}

interface Scan {
    /** Every `{light, dark}` pair, with its path. */
    pairs: Array<{path: string; pair: ThemePair<unknown>}>;
    /** The path of every string the walk found to be a colour. */
    colours: string[];
    /** One sentence per broken rule, naming the path at fault. */
    defects: string[];
}

/** Walks every export of `modules`, at any depth, and reports what breaks the shape the tables share. */
function scanTables(modules: Record<string, Record<string, unknown>>): Scan {
    const scan: Scan = {pairs: [], colours: [], defects: []};

    function visitTable(table: Record<string, unknown>, path: string): void {
        const [hasLight, hasDark] = ['light' in table, 'dark' in table];
        if (hasLight !== hasDark) {
            scan.defects.push(`${path} has ${hasLight ? 'light' : 'dark'} without ${hasLight ? 'dark' : 'light'}`);
        } else if (hasLight) {
            scan.pairs.push({path, pair: table as unknown as ThemePair<unknown>});
            const {light, dark} = table;
            if (kindOf(light) !== kindOf(dark)) scan.defects.push(`${path}: light is a ${kindOf(light)}, dark a ${kindOf(dark)}`);
            else if (Array.isArray(light) && Array.isArray(dark) && light.length !== dark.length) scan.defects.push(`${path}: light has ${light.length} entries, dark ${dark.length}`);
        }
        for (const [key, child] of Object.entries(table)) visit(child, `${path}.${key}`);
    }

    function visit(value: unknown, path: string): void {
        if (typeof value === 'string') {
            const problem = colourProblem(value);
            if (problem === null) scan.colours.push(path);
            else scan.defects.push(`${path} = ${JSON.stringify(value)}: ${problem}`);
        } else if (Array.isArray(value)) {
            const firstIndex = new Map<string, number>();
            value.forEach((entry, index) => {
                visit(entry, `${path}[${index}]`);
                if (typeof entry !== 'string') return;
                const first = firstIndex.get(normalised(entry));
                if (first === undefined) firstIndex.set(normalised(entry), index);
                else scan.defects.push(`${path}[${index}] repeats ${path}[${first}] (${entry})`);
            });
        } else if (value !== null && typeof value === 'object') {
            visitTable(value as Record<string, unknown>, path);
        } else if (typeof value !== 'function') {
            // A function is behaviour, not a table; anything else has no place among colours.
            scan.defects.push(`${path} is ${kindOf(value)}, not a colour`);
        }
    }

    for (const [moduleName, exports] of Object.entries(modules)) {
        for (const [name, value] of Object.entries(exports)) visit(value, `${moduleName}.${name}`);
    }
    return scan;
}

// =============================================================================
// The tables
// =============================================================================

const SCAN = scanTables(MODULES);

describe('the chart colour tables — every export of chartTheme.ts and chartPalettes.ts, at any depth', () => {
    it('positive control: the walk reaches tables known to exist, at every depth', () => {
        // A pair exported as it is (a pair of lists), a pair inside a table, a pair two tables down. No list of pairs is left.
        const pairs = ['chartPalettes.GEO_CHOROPLETH_SCALE', 'chartTheme.PRICE_SERIES.line', 'chartTheme.LOT_WAC_COLORS.markers.buy'];
        // The last entry of a theme's list, an entry of a plain list, a theme of a pair inside a table, a theme of a pair two tables down (an rgba()), a plain string inside a table.
        const colours = ['chartPalettes.GEO_CHOROPLETH_SCALE.dark[5]', 'chartPalettes.SIGNAL_DEFAULT_PALETTE[0]', 'chartTheme.PRICE_SERIES.line.light', 'chartTheme.LOT_GANTT_COLORS.highlightBand.fill.dark', 'chartTheme.SIGNAL_COLORS.measure'];

        expect(SCAN.pairs.map(({path}) => path)).toEqual(expect.arrayContaining(pairs));
        expect(SCAN.colours).toEqual(expect.arrayContaining(colours));
    });

    it('skips a function export: growthBrokerColor and chartNeutrals are behaviour, read at each draw, not tables', () => {
        expect(typeof MODULES.chartPalettes.growthBrokerColor, 'barrier: the export exists, so the skip is about something').toBe('function');
        expect(typeof MODULES.chartTheme.chartNeutrals, 'barrier: the export exists among those walked, so the skip is about something').toBe('function');

        const reached = [...SCAN.pairs.map(({path}) => path), ...SCAN.colours, ...SCAN.defects].filter((entry) => ['growthBrokerColor', 'chartNeutrals'].some((name) => entry.includes(name)));
        expect(reached, 'a function walked as a table: what it draws is read at each draw, and tested on its own').toEqual([]);
    });

    it('breaks no rule: every pair whole and of one kind, every string a colour, no list repeating an entry, the two lists of a pair of one length', () => {
        expect(SCAN.defects).toEqual([]);
    });

    it('themed() hands back the very member of the theme, for every pair found', () => {
        expect(SCAN.pairs.length, 'no pair found: the check below would pass on nothing').toBeGreaterThan(0);

        const wrong = SCAN.pairs.filter(({pair}) => themed(pair, true) !== pair.dark || themed(pair, false) !== pair.light).map(({path}) => path);
        expect(wrong).toEqual([]);
    });
});

// =============================================================================
// The rules fail on what they guard against
// =============================================================================

describe('the rules — each fails on what it guards against', () => {
    it('names every defect of a synthetic table that breaks each rule once', () => {
        const broken = {
            HALF: {light: '#ffffff'},
            TYPO: {deep: {light: '#1a403', dark: '#4ade80'}},
            REPEAT: ['#1a4031', '#2563eb', '#1A4031'],
            UNEVEN: {light: ['#1a4031', '#2563eb'], dark: ['#4ade80']},
            MIXED: {light: '#1a4031', dark: ['#4ade80']},
            OPACITY: 0.5,
        };

        expect(scanTables({broken}).defects).toEqual([
            'broken.HALF has light without dark',
            'broken.TYPO.deep.light = "#1a403": not #rgb, #rrggbb, #rrggbbaa, rgb(), rgba(), hsl() or hsla()',
            'broken.REPEAT[2] repeats broken.REPEAT[0] (#1A4031)',
            'broken.UNEVEN: light has 2 entries, dark 1',
            'broken.MIXED: light is a string, dark a list',
            'broken.OPACITY is number, not a colour',
        ]);
    });

    it('accepts every notation the tables use, and refuses the slips a hand makes', () => {
        const accepted = ['#fff', '#1a4031', '#1A4031', '#1a4031cc', 'rgb(0,0,0)', 'rgba(255, 255, 255, 0.75)', 'rgba(2, 6, 23, .95)', 'hsl(210, 40%, 96%)', 'hsla(210deg, 40%, 96.5%, 1)'];
        const refused = ['#1a403', '#1a40311', '#1a4o31', '1a4031', '#1a4031 ', 'red', '', 'rgba(255,255,255)', 'rgb(255, 255, 256)', 'rgba(0, 0, 0, 60)', 'hsl(120, 50, 50)', 'rgb(0 0 0 / 0.5)'];

        expect(accepted.filter((colour) => colourProblem(colour) !== null)).toEqual([]);
        expect(refused.filter((colour) => colourProblem(colour) === null)).toEqual([]);
    });
});

// =============================================================================
// The neutrals on roles — chartNeutrals
// =============================================================================

/** A neutral drawn translucent: the role it reads, and its alpha in each theme. */
interface Translucent {
    role: ChartRole;
    light: number;
    dark: number;
}

/** What a neutral reads: a role, drawn as the role reads; or a role at an alpha. */
type NeutralRead = ChartRole | Translucent;

function translucent(role: ChartRole, light: number, dark: number): Translucent {
    return {role, light, dark};
}

/** The role a neutral reads, whatever its alpha. */
function roleOf(read: NeutralRead): ChartRole {
    return typeof read === 'string' ? read : read.role;
}

/**
 * Every neutral of `chartNeutrals()`, by its path, and what it reads: written by hand from DV's plan (section «B4», «La
 * mappa, per ruolo»), never read from the module under test. The groups keep the names of the tables they left.
 */
const NEUTRAL_READS: Readonly<Record<string, NeutralRead>> = {
    'priceAxis.line': '--lf-border-subtle',
    'priceAxis.label': '--lf-text-muted',
    'priceAxis.gridLine': '--lf-border-subtle',
    'dashboard.text': '--lf-text-muted',
    'dashboard.gridLine': '--lf-border-subtle',
    legendPageIconInactive: translucent('--lf-text-muted', 0.4, 0.4),
    secondaryAxisFallback: '--lf-text-muted',
    referenceLevelLabel: '--lf-text-muted',
    'axisPointer.line': '--lf-border-input',
    'axisPointer.shadow': translucent('--lf-text-muted', 0.2, 0.2),
    'tooltip.box.background': '--lf-surface-card',
    'tooltip.box.border': '--lf-border-raised',
    'tooltip.box.text': '--lf-text-primary',
    'tooltip.box.muted': '--lf-text-muted',
    'tooltip.candlestickBox.border': '--lf-border-raised',
    'tooltip.candlestickBox.text': '--lf-text-primary',
    'tooltip.candlestickBox.heading': '--lf-text-primary',
    'tooltip.candlestickBox.muted': '--lf-text-muted',
    'tooltip.candlestickBox.crosshair': '--lf-border-input',
    'tooltip.aside': '--lf-text-muted',
    'tooltip.staleWarning': '--lf-warning',
    'price.baseline': '--lf-border-input',
    'price.pendingEditPointRing': '--lf-surface-card',
    'riskReturn.axis': '--lf-border-subtle',
    'riskReturn.axisText': '--lf-text-secondary',
    'riskReturn.capitalMarketLine': '--lf-border-input',
    'allocation.sliceBorder': '--lf-surface-card',
    'allocation.caption': '--lf-text-secondary',
    'allocation.historyAreaLabel': '--lf-text-primary',
    'allocation.historyAreaLabelShadow': '--lf-surface-card',
    'semiDonut.label': '--lf-text-primary',
    'semiDonut.labelShadow': translucent('--lf-surface-card', 0.8, 0.6),
    'semiDonut.labelLine': '--lf-border-input',
    'semiDonut.avatarBorder': '--lf-surface-card',
    'semiDonut.sliceGap': '--lf-surface-card',
    'semiDonut.available': '--lf-surface-neutral',
    'geoMap.border': '--lf-surface-card',
    'geoMap.label': '--lf-text-primary',
    'geoMap.labelBackground': translucent('--lf-surface-card', 0.72, 0.55),
    'correlation.cellGap': '--lf-surface-card',
    'correlation.emphasisBorder': '--lf-text-primary',
    'correlation.emphasisHalo': translucent('--lf-surface-card', 0.95, 0.95),
    'correlation.axisLabel': '--lf-text-secondary',
    'correlation.tooltipBadge.background': '--lf-surface-panel',
    'correlation.tooltipBadge.text': '--lf-text-secondary',
    'correlation.tooltipDivider': '--lf-border-subtle',
    'growth.pnlReference': '--lf-border-input',
    'growth.bucketSeparator': '--lf-border-input',
    'performance.zeroValue': '--lf-text-primary',
    'performance.axisName': '--lf-text-primary',
    'performance.axisSecondary': '--lf-text-muted',
    'performance.axisSection': '--lf-text-secondary',
    'performance.zeroLine': '--lf-text-muted',
    'performance.sectionSeparator': '--lf-border-subtle',
    'performance.rowHighlight': translucent('--lf-text-muted', 0.16, 0.14),
    'performance.axisPointerShadow': translucent('--lf-text-muted', 0.14, 0.12),
    'treemap.groupLabel': '--lf-text-secondary',
    'treemap.groupLabelBackground': translucent('--lf-surface-card', 0.8, 0.8),
    'treemap.groupBorder': '--lf-border-subtle',
    'treemap.tileBorder': '--lf-border-subtle',
    'lots.markerRing': '--lf-surface-card',
    'lots.markerEmphasisRing': '--lf-text-primary',
    'lots.gantt.selectedSegmentBorder': '--lf-text-primary',
    'lots.gantt.lineageConnector': translucent('--lf-text-primary', 0.45, 0.48),
    'lots.gantt.segmentLabel': '--lf-text-primary',
    'lots.gantt.stateChipText': '--lf-on-status',
    'lots.wacZeroLine': '--lf-border-input',
};

/**
 * A colour of its own for every role of `ChartRole`, none of them a stand-in: a neutral drawn in one of them names the
 * role it read, through the reader. The roles no neutral reads are listed too, the record being complete; their colours
 * only have to collide with no other. All `#rrggbb`, the one notation `chartRoles` takes as it is where there is no
 * canvas to resolve the others; the last two digits number the role, in hex.
 */
const INJECTED_COLOURS: Readonly<Record<ChartRole, string>> = {
    '--lf-surface-card': '#1e0001',
    '--lf-surface-panel': '#1e0002',
    '--lf-surface-neutral': '#1e0003',
    '--lf-text-primary': '#1e0004',
    '--lf-text-secondary': '#1e0005',
    '--lf-text-muted': '#1e0006',
    '--lf-text-on-inverse': '#1e0007',
    '--lf-border-subtle': '#1e0008',
    '--lf-border-raised': '#1e0009',
    '--lf-border-input': '#1e000a',
    '--lf-on-status': '#1e000b',
    '--lf-warning': '#1e000c',
    '--lf-danger': '#1e000d',
    '--lf-info': '#1e000e',
    '--lf-surface-field': '#1e000f',
    '--lf-surface-hover': '#1e0010',
    '--lf-focus': '#1e0011',
    '--lf-selected': '#1e0012',
    '--lf-checked': '#1e0013',
    '--lf-action': '#1e0014',
    '--lf-on-action': '#1e0015',
    '--lf-mark-bg': '#1e0016',
    '--lf-cat-stock': '#1e0017',
    '--lf-cat-etf': '#1e0018',
    '--lf-cat-bond': '#1e0019',
    '--lf-cat-crypto': '#1e001a',
    '--lf-cat-fund': '#1e001b',
    '--lf-cat-hold': '#1e001c',
    '--lf-cat-crowdfund': '#1e001d',
    '--lf-cat-commodity': '#1e001e',
    '--lf-cat-real-estate': '#1e001f',
    '--lf-cat-index': '#1e0020',
    '--lf-cat-other': '#1e0021',
    '--lf-cat-liquidity': '#1e0022',
};

/** What the neutral `read` draws in a theme when every role answers its injected colour. */
function injectedDraw(read: NeutralRead, dark: boolean): string {
    return typeof read === 'string' ? INJECTED_COLOURS[read] : toRgba(INJECTED_COLOURS[read.role], dark ? read.dark : read.light);
}

/** Every leaf of a nested object, by its dotted path: a plain object is descended, anything else is a leaf. */
function leavesOf(root: unknown): Map<string, unknown> {
    const leaves = new Map<string, unknown>();
    const visit = (node: unknown, path: string): void => {
        if (node !== null && typeof node === 'object' && !Array.isArray(node)) {
            for (const [key, child] of Object.entries(node)) visit(child, path === '' ? key : `${path}.${key}`);
        } else {
            leaves.set(path, node);
        }
    };
    visit(root, '');
    return leaves;
}

/** Why `value` is not a colour in a form the neutrals draw — `#rrggbb`, or `rgba(r,g,b,a)` as `toRgba` writes it, in range — `null` when it is one. */
function drawnColourProblem(value: unknown): string | null {
    if (typeof value !== 'string') return `${kindOf(value)}, not a colour`;
    if (!/^(?:#[0-9a-f]{6}|rgba\([^()]*\))$/i.test(value)) return 'neither #rrggbb nor rgba()';
    return colourProblem(value);
}

function themeName(dark: boolean): string {
    return dark ? 'dark' : 'light';
}

/** One read of a role, with the element it was asked on. */
interface RoleRead {
    role: ChartRole;
    scope: Element | null;
}

describe('chartNeutrals — the neutrals of the charts, on the colour roles', () => {
    const ROWS = Object.entries(NEUTRAL_READS);
    const ROW_PATHS = new Set(Object.keys(NEUTRAL_READS));
    /** Every role a row names. */
    const NAMED_ROLES = new Set(ROWS.map(([, read]) => roleOf(read)));

    afterEach(() => {
        setRoleReader(null);
    });

    /** Injects a reader that answers every role with its colour of {@link INJECTED_COLOURS}; returns the reads it gets. */
    function injectRoles(): RoleRead[] {
        const reads: RoleRead[] = [];
        const reader: RoleReader = (role, scope) => {
            reads.push({role, scope});
            return INJECTED_COLOURS[role];
        };
        setRoleReader(reader);
        return reads;
    }

    it('reads every neutral from the role of its row, at the alpha of its row, in both themes', () => {
        // Positive controls: the comparison tells two roles apart only if they answer two colours, and a read from a
        // stand-in only if no injected colour is one. The stand-ins are drawn first, with no reader: a draw that kept
        // them for the next one would be red below as well.
        const injected = Object.values(INJECTED_COLOURS);
        expect(
            injected.filter((colour) => !/^#[0-9a-f]{6}$/.test(colour)),
            'an answer that is not #rrggbb needs a canvas to resolve, which node has not: it would come back as the stand-in',
        ).toEqual([]);
        expect(new Set(injected).size, 'two roles answering one colour: a neutral on the wrong one of the two would pass').toBe(injected.length);
        const standIns = new Set([false, true].flatMap((dark) => [...leavesOf(chartNeutrals(dark)).values()]));
        expect(
            injected.filter((colour) => standIns.has(colour)),
            'an injected colour that a stand-in draws too: a neutral that never asked the reader could pass',
        ).toEqual([]);
        expect(ROWS.length, 'barrier: an empty table compares nothing').toBeGreaterThan(0);

        injectRoles();
        for (const dark of [false, true]) {
            const drawn = leavesOf(chartNeutrals(dark));
            const wrong = ROWS.filter(([path, read]) => drawn.get(path) !== injectedDraw(read, dark)).map(([path, read]) => `${path}: ${String(drawn.get(path))}, not ${injectedDraw(read, dark)}`);
            expect(wrong, `${themeName(dark)}: a neutral on another role than its row's, at another alpha, or not read through chartRoles`).toEqual([]);
        }
    });

    it('holds the table and the neutrals to each other: a row for every neutral, a neutral for every row, in both themes', () => {
        // Positive control: the walk descends — a leaf three objects down is named by its whole path, a group by none.
        expect([...leavesOf({a: {b: {c: '#000000'}}, d: '#ffffff'}).keys()], 'a walk that stops at the first level would miss a deep neutral, added or lost').toEqual(['a.b.c', 'd']);

        for (const dark of [false, true]) {
            const paths = [...leavesOf(chartNeutrals(dark)).keys()];
            expect(paths, `${themeName(dark)} barrier: the walk reaches a neutral three levels down`).toContain('lots.gantt.lineageConnector');
            expect(
                paths.filter((path) => !ROW_PATHS.has(path)),
                `${themeName(dark)}: a neutral without a row — its role and its alpha pinned by nothing`,
            ).toEqual([]);
            expect(
                [...ROW_PATHS].filter((path) => !paths.includes(path)),
                `${themeName(dark)}: a row without a neutral — renamed or removed, the row pins nothing`,
            ).toEqual([]);
        }
    });

    it('reads the roles on the element it is handed, and on none when there is neither a scope nor a page', () => {
        const reads = injectRoles();
        // Node has no DOM: a plain object stands in for the chart's element, compared by identity.
        const chartElement = {} as Element;
        chartNeutrals(false, chartElement);
        const asked = new Set(reads.map(({role}) => role));
        expect(
            [...NAMED_ROLES].filter((role) => !asked.has(role)),
            'barrier: the reader was asked for every role a row names, so the scope check is about real reads',
        ).toEqual([]);
        expect(
            reads.filter(({scope}) => scope !== chartElement).map(({role}) => role),
            "a role read elsewhere than on the chart's element: in a forced .light/.dark subtree, or in the Lab's preview, the chart would draw the page's theme",
        ).toEqual([]);

        expect(typeof document, 'barrier: node has no page, so with no scope there is no <html> to fall back on').toBe('undefined');
        reads.length = 0;
        chartNeutrals(false);
        chartNeutrals(true, null);
        expect(reads.length, 'barrier: the reader was asked, so the check below is about real reads').toBeGreaterThan(0);
        expect(
            reads.filter(({scope}) => scope !== null).map(({role}) => role),
            'with neither a scope nor a page, the reader must be handed null, not an element from elsewhere',
        ).toEqual([]);
    });

    it('with no reader and no page, draws the stand-ins: well-formed colours, picked by the theme', () => {
        setRoleReader(null);
        // Positive control: the check refuses what a broken read would hand the canvas, and takes the two forms the
        // neutrals draw.
        const refused = [undefined, '', '#616d6', '#616d67cc', 'rgba(97,109,103)', 'rgba(256,109,103,0.4)', 'rgba(97,109,103,4)', 'oklch(0.5 0.1 120 / 0.4)', 'var(--lf-text-muted)'];
        expect(
            refused.filter((value) => drawnColourProblem(value) === null),
            'the check takes a value that is not #rrggbb or rgba(r,g,b,a) in range',
        ).toEqual([]);
        expect(
            ['#616d67', 'rgba(97,109,103,0.4)'].filter((value) => drawnColourProblem(value) !== null),
            'the check refuses a form the neutrals draw',
        ).toEqual([]);

        for (const dark of [false, true]) {
            const leaves = [...leavesOf(chartNeutrals(dark))];
            expect(leaves.length, `${themeName(dark)} barrier: neutrals were drawn, so "every leaf" is about something`).toBeGreaterThan(0);
            const malformed = leaves.flatMap(([path, value]) => {
                const problem = drawnColourProblem(value);
                return problem === null ? [] : [`${path} = ${JSON.stringify(value)}: ${problem}`];
            });
            expect(malformed, `${themeName(dark)}: a neutral not drawn as #rrggbb or rgba(r,g,b,a) in range — a value the canvas cannot parse is ignored, and the colour before it painted instead`).toEqual([]);
        }
        expect(chartNeutrals(true).tooltip.box.background, 'the theme does not reach the stand-ins: a dark chart would draw its tooltip box in the light card').not.toBe(chartNeutrals(false).tooltip.box.background);
    });
});
