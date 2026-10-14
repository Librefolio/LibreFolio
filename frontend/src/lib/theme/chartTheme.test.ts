/**
 * chartTheme.test.ts — the shape of the chart colour tables, whatever tables they hold.
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
 * synthetic table that breaks it.
 *
 * The values are not pinned: a value is the designer's call, its shape is not.
 *
 * No runes, no DOM: this stays in the default `node` environment.
 *
 * @module lib/theme/chartTheme.test
 */
import {describe, expect, it, vi} from 'vitest';

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
        expect(SCAN.pairs.map(({path}) => path)).toEqual(expect.arrayContaining(['chartPalettes.ALLOCATION_PIE_PALETTE', 'chartTheme.CHART_TOOLTIP_COLORS.box.background']));
        expect(SCAN.colours).toEqual(expect.arrayContaining(['chartPalettes.ALLOCATION_PIE_PALETTE.dark[13]', 'chartPalettes.SEMI_DONUT_PALETTE[0]', 'chartTheme.CHART_TOOLTIP_COLORS.box.background.light', 'chartTheme.CHART_TOOLTIP_COLORS.aside']));
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
