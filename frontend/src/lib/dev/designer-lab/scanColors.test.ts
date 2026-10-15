/**
 * Designer Lab — the colour scanner (`frontend/scripts/designer-lab/scan-colors.mjs`).
 *
 * The scanner has two layers and so does this file. Counting mirrors `scripts/visual_review/color_inventory.py`: the
 * expected counts of the synthetic sources were derived by hand from that file's regular expressions. Annotation gives
 * every literal its zone, CSS rule, theme hint and live-preview layer: synthetic sources pin each rule. The real tree
 * is checked for shape and invariants only — its totals belong to whoever edits the app, so none is pinned here.
 */

import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join} from 'node:path';
import {CATALOG_SCHEMA, FRONTEND_DIR, isTestPath, LAB_DIRS, listSourceFiles, scanColors, scanSource, scriptTestidValues, STATIC_SOURCES, testidValues} from '../../../../scripts/designer-lab/scan-colors.mjs';
import {isInlineAlias} from './catalogView';
import type {CatalogLiteral, ColorCatalog, TestidVia, ThemeContext, Zone} from './types';

type Literal = Omit<CatalogLiteral, 'id' | 'file'>;

interface VarDef {
    name: string;
    value: string;
    line: number;
    zone: Zone;
    selector: string | null;
    theme: ThemeContext | null;
}

interface FileScan {
    counts: {tw: number; custom: number; arbitrary: number; hex: number; fn: number};
    varUses: {name: string; line: number; selector: string | null}[];
    varDefs: VarDef[];
    classes: {raw: string; var: string | null; line: number; dark: boolean}[];
    literals: Literal[];
    testids: {id: string; prefix: boolean; line: number; via: TestidVia}[];
}

/** One synthetic source, written one line per entry so that every expected line number can be read off the array. */
const scan = (rel: string, lines: string[], zoneOverride?: Zone): FileScan => scanSource(rel, lines.join('\n'), zoneOverride ? {zoneOverride} : {}) as unknown as FileScan;

/** How a test id reaches the page: a `data-testid` attribute, a component prop, or a script value. */
const VIAS: readonly TestidVia[] = ['attr', 'prop', 'script'];

const catalogOf = (opts: {root?: string; appVersion?: string} = {}): ColorCatalog => scanColors(opts) as unknown as ColorCatalog;

/** The one literal written as `raw` on `line`: found by what the source holds, never by its position in the list. */
function literal(result: FileScan, line: number, raw: string): Literal {
    const found = result.literals.filter((l) => l.line === line && l.raw === raw);
    expect(found, `${raw} on line ${line}`).toHaveLength(1);
    return found[0];
}

/** Temporary `frontend/`-like trees, removed after the file. */
const roots: string[] = [];

function makeTree(files: Record<string, string[]>): string {
    const root = mkdtempSync(join(tmpdir(), 'lf-designer-lab-scan-'));
    roots.push(root);
    for (const [rel, lines] of Object.entries(files)) writeTreeFile(root, rel, lines);
    return root;
}

function writeTreeFile(root: string, rel: string, lines: string[]): void {
    const full = join(root, rel);
    mkdirSync(dirname(full), {recursive: true});
    writeFileSync(full, lines.join('\n'));
}

afterAll(() => {
    for (const root of roots) rmSync(root, {recursive: true, force: true});
});

describe('scanSource — zones', () => {
    it('tells the zones of a component apart: script, markup, style', () => {
        const result = scan('src/lib/components/Card.svelte', ['<script lang="ts">', "    const accent = '#1a4031';", '</script>', '', '<p class="text-[#2b2b2b]">x</p>', '', '<style>', '    p {', '        color: #3c3c3c;', '    }', '</style>']);
        expect(literal(result, 2, '#1a4031')).toMatchObject({zone: 'svelte-script', layer: 'script', preview: false});
        expect(literal(result, 5, '#2b2b2b')).toMatchObject({zone: 'svelte-markup', layer: 'css-literal', via: 'tw-arbitrary', preview: true});
        expect(literal(result, 9, '#3c3c3c')).toMatchObject({zone: 'svelte-style', layer: 'css-literal', preview: true, selector: 'p', property: 'color'});
        expect(result.literals).toHaveLength(3);
    });

    it('gives a stylesheet, a module and a document outside the bundle their own zone', () => {
        expect(literal(scan('src/app.css', ['a {', '    color: #3c3c3c;', '}']), 2, '#3c3c3c')).toMatchObject({zone: 'css-file', layer: 'css-literal', preview: true, selector: 'a', property: 'color', theme: 'both'});
        expect(literal(scan('src/lib/utils/palette.ts', ["export const ink = '#3c3c3c';"]), 1, '#3c3c3c')).toMatchObject({zone: 'ts', layer: 'script', preview: false, chart: false, theme: null});
        expect(literal(scan('src/service-worker.js', ["const ink = '#3c3c3c';"]), 1, '#3c3c3c')).toMatchObject({zone: 'ts', layer: 'script'});
        expect(literal(scan('static/offline.html', ['<body style="background:#0f172a">'], 'static'), 1, '#0f172a')).toMatchObject({zone: 'static', layer: 'static', preview: false, theme: null});
    });
});

describe('scanSource — the CSS rule of a stylesheet colour', () => {
    it('records the selector, property, at-rules and theme of a colour in a component <style>', () => {
        const result = scan('src/lib/components/table/DataTable.svelte', [
            '<p>x</p>',
            '<style>',
            '    th {',
            '        color: #64748b;',
            '    }',
            '    :global(.dark) th {',
            '        color: #94a3b8;',
            '    }',
            '    @media (max-width: 640px) {',
            '        .cell {',
            '            border-color: rgb(226 232 240 / 50%);',
            '        }',
            '    }',
            '    .chip:hover,',
            '    .chip:focus-visible {',
            '        background-color: #10b981;',
            '    }',
            '</style>',
        ]);
        const th = literal(result, 4, '#64748b');
        expect(th).toMatchObject({zone: 'svelte-style', selector: 'th', property: 'color', theme: 'both'});
        expect(th.at).toBeUndefined();
        expect(literal(result, 7, '#94a3b8')).toMatchObject({selector: ':global(.dark) th', property: 'color', theme: 'dark'});
        expect(literal(result, 11, 'rgb(226 232 240 / 50%)')).toMatchObject({kind: 'fn', key: '#e2e8f0', alpha: 0.5, selector: '.cell', at: ['@media (max-width: 640px)'], property: 'border-color', theme: 'both'});
        expect(literal(result, 16, '#10b981')).toMatchObject({kind: 'hex', key: '#10b981', alpha: 1, selector: '.chip:hover, .chip:focus-visible', property: 'background-color', theme: 'both'});
    });

    it('reads the theme of a stylesheet rule from its selector and from its media query', () => {
        const result = scan('src/app.css', [
            "@import 'tailwindcss';",
            '@theme {',
            '    --color-libre-green: #1a4031;',
            '}',
            ':root {',
            '    --theme-text-muted: #6b7280;',
            '}',
            'html.dark {',
            '    --theme-text-muted: #9ca3af;',
            '}',
            '.btn:hover {',
            '    color: var(--theme-text-muted);',
            '    background-color: rgba(26, 64, 49, 0.08);',
            '}',
            '@media (prefers-color-scheme: dark) {',
            '    .auto {',
            '        color: #f1f5f9;',
            '    }',
            '}',
            '@media (prefers-color-scheme: light) {',
            '    .auto {',
            '        color: #0f172a;',
            '    }',
            '}',
            'html.light .card {',
            '    border-color: #e5e7eb;',
            '}',
            '/* #ff0000 in a comment: counted, as color_inventory.py counts it, but in no rule */',
        ]);
        expect(literal(result, 3, '#1a4031')).toMatchObject({zone: 'css-file', selector: '@theme', property: '--color-libre-green', theme: 'both'});
        expect(literal(result, 6, '#6b7280')).toMatchObject({selector: ':root', property: '--theme-text-muted', theme: 'both'});
        expect(literal(result, 9, '#9ca3af')).toMatchObject({selector: 'html.dark', property: '--theme-text-muted', theme: 'dark'});
        expect(literal(result, 13, 'rgba(26, 64, 49, 0.08)')).toMatchObject({selector: '.btn:hover', property: 'background-color', theme: 'both', key: '#1a4031', alpha: 0.08});
        expect(literal(result, 17, '#f1f5f9')).toMatchObject({selector: '.auto', at: ['@media (prefers-color-scheme: dark)'], property: 'color', theme: 'dark'});
        expect(literal(result, 22, '#0f172a')).toMatchObject({selector: '.auto', at: ['@media (prefers-color-scheme: light)'], property: 'color', theme: 'light'});
        expect(literal(result, 26, '#e5e7eb')).toMatchObject({selector: 'html.light .card', property: 'border-color', theme: 'light'});
        expect(literal(result, 28, '#ff0000')).toMatchObject({zone: 'css-file', layer: 'css-literal', selector: null, property: null, theme: 'both'});
    });

    it('reads a rule under `:not(.dark)` as light-theme only', () => {
        const result = scan('src/app.css', ['html:not(.dark) .card {', '    border-color: #e5e7eb;', '}']);
        expect(literal(result, 2, '#e5e7eb')).toMatchObject({selector: 'html:not(.dark) .card', property: 'border-color', theme: 'light'});
    });

    it('records color-mix() as an expression — kind mix, no key, no alpha — and the colour inside it as a literal of its own', () => {
        const result = scan('src/lib/components/Chip.svelte', ['<style>', '    .chip {', '        background: color-mix(in srgb, #10b981 20%, transparent);', '    }', '</style>']);
        expect(literal(result, 3, 'color-mix(in srgb, #10b981 20%, transparent)')).toMatchObject({kind: 'mix', key: null, alpha: null, selector: '.chip', property: 'background', layer: 'css-literal'});
        expect(literal(result, 3, '#10b981')).toMatchObject({kind: 'hex', key: '#10b981', alpha: 1, selector: '.chip', property: 'background'});
    });
});

describe('scanSource — the theme a selector restricts its rule to', () => {
    it('reads `.dark` and `:not(.light)` as dark, `.light` and `:not(.dark)` as light, and a longer class name as neither', () => {
        const result = scan('src/app.css', ['.dark .a {', '    color: #000001;', '}', 'html:not(.light) .b {', '    color: #000002;', '}', '.light .c {', '    color: #000003;', '}', ':root:not(.dark) .d {', '    color: #000004;', '}', '.darker .e {', '    color: #000005;', '}']);
        expect(literal(result, 2, '#000001').theme).toBe('dark');
        expect(literal(result, 5, '#000002').theme).toBe('dark');
        expect(literal(result, 8, '#000003').theme).toBe('light');
        expect(literal(result, 11, '#000004').theme).toBe('light');
        expect(literal(result, 14, '#000005').theme).toBe('both');
    });

    it('fixes the theme only when every selector of a list names it', () => {
        const result = scan('src/app.css', ['.a, html.dark .b {', '    color: #000006;', '}', 'html.dark .a,', '.dark .b {', '    color: #000007;', '}', 'html.light .a, html:not(.dark) .b {', '    color: #000008;', '}']);
        expect(literal(result, 2, '#000006')).toMatchObject({selector: '.a, html.dark .b', theme: 'both'});
        expect(literal(result, 6, '#000007')).toMatchObject({selector: 'html.dark .a, .dark .b', theme: 'dark'});
        expect(literal(result, 9, '#000008')).toMatchObject({selector: 'html.light .a, html:not(.dark) .b', theme: 'light'});
    });

    it('reads the theme down a chain of nested rules and at-rules', () => {
        const result = scan('src/app.css', [
            'html.dark {',
            '    .card {',
            '        color: #000009;',
            '    }',
            '    .a, .b {',
            '        color: #00000a;',
            '    }',
            '}',
            '.card {',
            '    html.dark & {',
            '        color: #00000b;',
            '    }',
            '}',
            '@media (prefers-color-scheme: dark) {',
            '    @supports (display: grid) {',
            '        .grid {',
            '            color: #00000c;',
            '        }',
            '    }',
            '}',
        ]);
        expect(literal(result, 3, '#000009')).toMatchObject({selector: 'html.dark .card', property: 'color', theme: 'dark'});
        // A nested list that names no theme leaves the outer one in force.
        expect(literal(result, 6, '#00000a').theme).toBe('dark');
        expect(literal(result, 11, '#00000b')).toMatchObject({selector: '.card html.dark &', theme: 'dark'});
        expect(literal(result, 17, '#00000c')).toMatchObject({selector: '.grid', at: ['@media (prefers-color-scheme: dark)', '@supports (display: grid)'], theme: 'dark'});
    });
});

describe('scanSource — theme hints in scripts', () => {
    // One line per entry: the line numbers below are positions in this array, plus one.
    const source = [
        "export const keys = {dark: '#000010', light: '#000011'};",
        "const darkBg = '#000012';",
        "const tone = isDark ? '#000013' : '#000014';",
        "const flipped = !isDark ? '#000015' : '#000016';",
        "const call = this.isDark() ? '#000017' : '#000018';",
        'const fill = isDark',
        "    ? '#000019'",
        "    : '#00001a';",
        'const stroke = !isDarkMode',
        "    ? '#00001b'",
        "    : '#00001c';",
        'const plain = isActive',
        "    ? '#00001d'",
        "    : '#00001e';",
        "const loose = '#00001f';",
        'const commented = isDark // the theme decides',
        '',
        "    ? '#000020'",
        "    : '#000021';",
        'const nested = isDark',
        "    ? '#000022'",
        '    : isHigh',
        "      ? '#000023'",
        "      : '#000024';",
        // A Svelte store: `$` stands between the `!` and the name.
        "const store = $isDark ? '#000025' : '#000026';",
        "const negStore = !$isDark ? '#000027' : '#000028';",
        'const storeFill = !$isDark',
        "    ? '#000029'",
        "    : '#00002a';",
        'const storeStroke = $isDark',
        "    ? '#00002b'",
        "    : '#00002c';",
    ];
    const hint = (line: number, raw: string) => literal(scan('src/lib/utils/palette.ts', source), line, raw).theme;

    it('reads an object key or a variable name that says the theme', () => {
        expect(hint(1, '#000010')).toBe('dark');
        expect(hint(1, '#000011')).toBe('light');
        expect(hint(2, '#000012')).toBe('dark');
    });

    it('reads the side of a one-line ternary whose condition names the dark theme, `!` swapping the sides', () => {
        expect([hint(3, '#000013'), hint(3, '#000014')]).toEqual(['dark', 'light']);
        expect([hint(4, '#000015'), hint(4, '#000016')]).toEqual(['light', 'dark']);
        expect([hint(5, '#000017'), hint(5, '#000018')]).toEqual(['dark', 'light']);
    });

    it('reads a ternary split over lines as Prettier writes it, `!` swapping the sides', () => {
        expect([hint(7, '#000019'), hint(8, '#00001a')]).toEqual(['dark', 'light']);
        expect([hint(10, '#00001b'), hint(11, '#00001c')]).toEqual(['light', 'dark']);
        // A comment after the condition and a blank line before the branches change nothing.
        expect([hint(18, '#000020'), hint(19, '#000021')]).toEqual(['dark', 'light']);
    });

    it('gives no hint where the condition does not name the theme, nor to a colour outside a ternary', () => {
        expect([hint(13, '#00001d'), hint(14, '#00001e'), hint(15, '#00001f')]).toEqual([null, null, null]);
        // The inner ternary of a nested one has its own condition.
        expect([hint(21, '#000022'), hint(23, '#000023'), hint(24, '#000024')]).toEqual(['dark', null, null]);
    });

    it('reads a store condition (`$isDark`), its `!` swapping the sides, on one line and split over lines', () => {
        expect([hint(25, '#000025'), hint(25, '#000026')]).toEqual(['dark', 'light']);
        expect([hint(26, '#000027'), hint(26, '#000028')]).toEqual(['light', 'dark']);
        expect([hint(28, '#000029'), hint(29, '#00002a')]).toEqual(['light', 'dark']);
        expect([hint(31, '#00002b'), hint(32, '#00002c')]).toEqual(['dark', 'light']);
    });

    it('marks script colours as such: no live preview outside a chart', () => {
        expect(literal(scan('src/lib/utils/palette.ts', source), 15, '#00001f')).toMatchObject({zone: 'ts', layer: 'script', preview: false, chart: false});
    });
});

describe('scanSource — colours written in markup', () => {
    const result = scan('src/lib/components/Pill.svelte', [
        '<span class="bg-[#000030] dark:bg-[#000031]">a</span>',
        '<span class="dark:text-white bg-[#000032]">b</span>',
        '<span class="md:dark:hover:bg-[#000033]">c</span>',
        '<span style="color: #000034">d</span>',
        '<span style:color="#000035">e</span>',
        '<svg fill="#000036"><path stroke="#000037" /></svg>',
        '<span class={active ? "dark:bg-[#000038]" : "bg-[#000039]"}>f</span>',
    ]);

    it('tells a Tailwind arbitrary class, which compiles into a stylesheet, from an inline style and other markup', () => {
        expect(literal(result, 1, '#000030')).toMatchObject({zone: 'svelte-markup', via: 'tw-arbitrary', layer: 'css-literal', preview: true});
        expect(literal(result, 4, '#000034')).toMatchObject({zone: 'svelte-markup', via: 'style-attr', layer: 'markup', preview: false});
        expect(literal(result, 5, '#000035')).toMatchObject({via: 'style-attr', layer: 'markup'});
        expect(literal(result, 6, '#000036')).toMatchObject({via: 'markup', layer: 'markup', preview: false});
        expect(literal(result, 6, '#000037')).toMatchObject({via: 'markup', layer: 'markup'});
    });

    it('takes the theme from the `dark:` variant of the class that holds the colour, never from a neighbouring class', () => {
        expect(literal(result, 1, '#000030').theme).toBeNull();
        expect(literal(result, 1, '#000031').theme).toBe('dark');
        expect(literal(result, 2, '#000032').theme).toBeNull();
        expect(literal(result, 3, '#000033').theme).toBe('dark');
        expect(literal(result, 4, '#000034').theme).toBeNull();
        expect(literal(result, 7, '#000038')).toMatchObject({via: 'tw-arbitrary', theme: 'dark'});
        expect(literal(result, 7, '#000039')).toMatchObject({via: 'tw-arbitrary', theme: null});
    });
});

describe('scanSource — layers', () => {
    it('sends the script colours of a chart component to the chart layer, its style and markup to theirs', () => {
        const result = scan('src/lib/components/charts/Line.svelte', ['<script lang="ts">', "    const series = '#000040';", '</script>', '', '<svg fill="#000041"></svg>', '', '<style>', '    .line {', '        stroke: #000042;', '    }', '</style>']);
        expect(literal(result, 2, '#000040')).toMatchObject({zone: 'svelte-script', layer: 'chart-color', preview: true, chart: true});
        expect(literal(result, 5, '#000041')).toMatchObject({zone: 'svelte-markup', layer: 'markup', preview: false});
        expect(literal(result, 9, '#000042')).toMatchObject({zone: 'svelte-style', layer: 'css-literal', preview: true});
    });

    it.each([
        ['a chart folder', 'src/lib/components/dashboard/Kpi.svelte'],
        ['the risk folder', 'src/lib/components/risk/Heatmap.svelte'],
        ['the PAC planner results', 'src/lib/features/tools/pac-allocator/planner/result/ExposureBars.svelte'],
        ['a file named after charts', 'src/lib/utils/chartColors.ts'],
    ])('recognises a chart by %s', (_label, rel) => {
        const lines = rel.endsWith('.svelte') ? ['<script lang="ts">', "    const c = '#000043';", '</script>'] : ['', "export const c = '#000043';"];
        expect(literal(scan(rel, lines), 2, '#000043')).toMatchObject({layer: 'chart-color', chart: true});
    });

    it('recognises a chart by its import of echarts, wherever it lives', () => {
        const result = scan('src/lib/features/insights/Trend.svelte', ['<script lang="ts">', "    import * as echarts from 'echarts';", "    const c = '#000043';", '</script>']);
        expect(literal(result, 3, '#000043')).toMatchObject({layer: 'chart-color', chart: true});
    });

    it('keeps the colours of any other module in the script layer', () => {
        expect(literal(scan('src/lib/utils/format.ts', ["export const c = '#000044';"]), 1, '#000044')).toMatchObject({zone: 'ts', layer: 'script', preview: false, chart: false});
    });
});

describe('scanSource — variables', () => {
    it('records each definition with its rule and theme, and each `var()` read inside a rule with that rule', () => {
        const result = scan('src/app.css', [':root,', 'html.light {', '    --theme-text: #111827;', '}', 'html.dark {', '    --theme-text: #f8fafc;', '}', '.card {', '    color: var(--theme-text);', '}']);
        expect(result.varDefs.map(({name, value, line, zone, selector, theme}) => ({name, value, line, zone, selector, theme}))).toEqual([
            {name: '--theme-text', value: '#111827', line: 3, zone: 'css-file', selector: ':root, html.light', theme: 'both'},
            {name: '--theme-text', value: '#f8fafc', line: 6, zone: 'css-file', selector: 'html.dark', theme: 'dark'},
        ]);
        expect(result.varUses).toEqual([{name: '--theme-text', line: 9, selector: '.card'}]);
    });

    it('records a read outside a stylesheet without a rule, and a component variable with its own', () => {
        const result = scan('src/lib/components/Chip.svelte', [
            '<script lang="ts">',
            "    const style = 'color: var(--theme-text)';",
            '</script>',
            '<span style="color: var(--theme-muted)">x</span>',
            '<style>',
            '    .chip {',
            '        --chip-bg: #fef3c7;',
            '        background: var(--chip-bg);',
            '    }',
            '</style>',
        ]);
        expect(result.varUses).toEqual([
            {name: '--theme-text', line: 2, selector: null},
            {name: '--theme-muted', line: 4, selector: null},
            {name: '--chip-bg', line: 8, selector: '.chip'},
        ]);
        expect(result.varDefs).toMatchObject([{name: '--chip-bg', value: '#fef3c7', line: 7, zone: 'svelte-style', selector: '.chip', theme: 'both'}]);
    });
});

describe('testidValues', () => {
    it('reads a quoted value as one id', () => {
        expect(testidValues('"tx-table" class="x">')).toEqual([{id: 'tx-table', prefix: false}]);
        expect(testidValues("'tx-row' />")).toEqual([{id: 'tx-row', prefix: false}]);
        expect(testidValues('"unterminated')).toEqual([]);
        expect(testidValues('"two words"')).toEqual([]);
    });

    it('cuts a templated id at its first placeholder into a prefix, and drops a prefix under three characters', () => {
        expect(testidValues('{`row-${id}`} />')).toEqual([{id: 'row-', prefix: true}]);
        expect(testidValues('{`row-${item.id}-cell`}')).toEqual([{id: 'row-', prefix: true}]);
        expect(testidValues('"row-{index}"')).toEqual([{id: 'row-', prefix: true}]);
        expect(testidValues('{`ab-${id}`}')).toEqual([{id: 'ab-', prefix: true}]);
        expect(testidValues('{`a-${id}`}')).toEqual([]);
        expect(testidValues('{`static-id`}')).toEqual([{id: 'static-id', prefix: false}]);
    });

    it('reads the literals in value position of an expression, never the operands of a comparison', () => {
        expect(testidValues("{active ? 'tab-active' : 'tab-idle'} />")).toEqual([
            {id: 'tab-active', prefix: false},
            {id: 'tab-idle', prefix: false},
        ]);
        expect(testidValues("{phase === 'catalog_loading' ? 'pane-loading' : 'pane-ready'}")).toEqual([
            {id: 'pane-loading', prefix: false},
            {id: 'pane-ready', prefix: false},
        ]);
        expect(testidValues('{tid ?? `tab-${key}`}')).toEqual([{id: 'tab-', prefix: true}]);
        expect(testidValues("{tid || 'fallback-id'}")).toEqual([{id: 'fallback-id', prefix: false}]);
        expect(testidValues("{ready && 'ready-id'}")).toEqual([{id: 'ready-id', prefix: false}]);
        expect(testidValues('{"quoted-id"}')).toEqual([{id: 'quoted-id', prefix: false}]);
        expect(testidValues("{kind === 'a' ? 'kind-a' : `kind-${kind}`}")).toEqual([
            {id: 'kind-a', prefix: false},
            {id: 'kind-', prefix: true},
        ]);
    });

    it('gives nothing for a pass-through, nor for a value with nothing static before its placeholder', () => {
        expect(testidValues('{testId} />')).toEqual([]);
        expect(testidValues('"{testid}-row"')).toEqual([]);
        expect(testidValues('{`${prefix}-row`}')).toEqual([]);
        expect(testidValues('testid')).toEqual([]);
    });

    it('reads what an arrow returns, and a literal inside grouping parentheses, but never a call argument', () => {
        expect(testidValues('{(o) => `opt-${o.value}`} />')).toEqual([{id: 'opt-', prefix: true}]);
        expect(testidValues("{(row) => 'row-menu'}")).toEqual([{id: 'row-menu', prefix: false}]);
        expect(testidValues("{('grouped-id')}")).toEqual([{id: 'grouped-id', prefix: false}]);
        expect(testidValues("{cond ? ('p-id') : 'q-id'}")).toEqual([
            {id: 'p-id', prefix: false},
            {id: 'q-id', prefix: false},
        ]);
        expect(testidValues("{label('call-arg')}")).toEqual([]);
        expect(testidValues("{ids.get('method-arg')}")).toEqual([]);
        expect(testidValues("{makers[0]('index-arg')}")).toEqual([]);
    });
});

describe('scriptTestidValues', () => {
    it('reads the expression of a property or a statement up to its end on the line', () => {
        expect(scriptTestidValues("'tab-a', key: 'a'}];")).toEqual([{id: 'tab-a', prefix: false}]);
        expect(scriptTestidValues('`row-${id}`;')).toEqual([{id: 'row-', prefix: true}]);
        expect(scriptTestidValues("active ? 'on-id' : 'off-id';")).toEqual([
            {id: 'on-id', prefix: false},
            {id: 'off-id', prefix: false},
        ]);
        expect(scriptTestidValues("'default-id', optionTestId}: Props = $props();")).toEqual([{id: 'default-id', prefix: false}]);
        expect(scriptTestidValues("'in-call'}), next('after-the-end')")).toEqual([{id: 'in-call', prefix: false}]);
    });

    it('gives nothing for a type, a flag, a call argument or a pass-through', () => {
        expect(scriptTestidValues('string; optionTestId?: string }')).toEqual([]);
        expect(scriptTestidValues('true;')).toEqual([]);
        expect(scriptTestidValues("label('call-arg');")).toEqual([]);
        expect(scriptTestidValues('props.testId,')).toEqual([]);
    });
});

describe('scanSource — test ids given in scripts', () => {
    it('indexes a property, a variable or a default whose name ends with `testid` and that takes a literal', () => {
        const result = scan('src/lib/components/tabs/tabs.ts', [
            "export const TABS = [{key: 'a', testId: 'tab-a'}, {key: 'b', testId: `tab-${key}`}];",
            'const rowTestId = `row-${id}`;',
            "export function Picker({testId = 'picker'}: Props) {}",
            "const data = {optionTestId: 'opt-list'};",
            "if (testId === 'tab-b') run();",
            "const tabTestIdPrefix = 'tab-p';",
            'let hasTestId = true;',
            'interface Props { testId?: string; optionTestId: string }',
            // Markup written in a script string: the attribute is not a script name ending with `testid`.
            'const html = \'<td data-testid="cell-x"></td>\';',
        ]);
        expect(result.testids).toEqual([
            {id: 'tab-a', prefix: false, line: 1, via: 'script'},
            {id: 'tab-', prefix: true, line: 1, via: 'script'},
            {id: 'row-', prefix: true, line: 2, via: 'script'},
            {id: 'picker', prefix: false, line: 3, via: 'script'},
            {id: 'opt-list', prefix: false, line: 4, via: 'script'},
        ]);
    });

    it('reads a component’s script as a script, and its markup as markup', () => {
        const result = scan('src/lib/components/Tabs.svelte', ['<script lang="ts">', "    const tabTestId = 'tab-x';", '    const html = \'<td data-testid="script-only"></td>\';', '</script>', '<div data-testid="tabs" listTestId="tab-list"></div>']);
        expect(result.testids).toEqual([
            {id: 'tab-x', prefix: false, line: 2, via: 'script'},
            {id: 'tabs', prefix: false, line: 5, via: 'attr'},
            {id: 'tab-list', prefix: false, line: 5, via: 'prop'},
        ]);
    });
});

describe('scanColors — the files and counts of a synthetic tree', () => {
    let root: string;
    let catalog: ColorCatalog;

    beforeAll(() => {
        root = makeTree({
            'src/lib/components/Badge.svelte': [
                '<script lang="ts">',
                "    const ring = '#1a4031';",
                '</script>',
                '',
                '<span class="bg-emerald-600 dark:bg-emerald-900/40 text-white border-[#2b2b2b] text-libre-green">x</span>',
                '',
                '<style>',
                '    span {',
                '        color: rgb(30 41 59 / 50%);',
                '        background: var(--theme-bg-card);',
                '    }',
                '</style>',
            ],
            'src/app.css': ['@theme {', '    --color-libre-green: #1a4031;', '}', ':root {', '    --theme-bg-card: #ffffff;', '    --theme-text: var(--color-gray-900);', '}', 'html.dark {', '    --theme-bg-card: oklch(27.9% 0.041 260.031);', '}'],
            'src/lib/utils/chartTheme.ts': ["export const axis = (isDark: boolean) => (isDark ? '#94a3b8' : '#475569');", "export const grid = 'rgba(148, 163, 184, 0.2)';"],
            // A test file counts in `files` and in the variable figures, as in the inventory; its colours do not.
            'src/lib/components/Card.test.ts': ["const classes = 'bg-red-500 #abcdef rgb(1 2 3)';", "const v = 'var(--test-only)';", 'const css = `', '    --test-def: #000000;', '`;'],
            'src/lib/components/__tests__/fixture.ts': ["export const fixture = 'text-blue-500 #fedcba';"],
            // Never read: generated clients, the Lab, dependencies, other extensions.
            'src/lib/api/generated.ts': ["export const x = '#111111';"],
            'src/lib/api/openapi-types.ts': ["export const y = '#222222';"],
            'src/lib/dev/designer-lab/Lab.svelte': ['<p class="text-red-500">#333333</p>'],
            'src/routes/designer-lab/+page.svelte': ['<p>#444444</p>'],
            'src/node_modules/pkg/index.js': ["export const z = '#555555';"],
            'src/lib/README.md': ['#666666'],
            // Outside the bundle: proposals only.
            'src/app.html': ['<meta name="theme-color" content="#1a4031">'],
            'static/offline.html': ['<body style="background:#0f172a">'],
        });
        catalog = catalogOf({root, appVersion: '1.2.0-test'});
    });

    it('reads the files the inventory reads, and catalogues the production ones and the documents outside the bundle', () => {
        expect(listSourceFiles(root)).toEqual(['src/app.css', 'src/lib/components/Badge.svelte', 'src/lib/components/Card.test.ts', 'src/lib/components/__tests__/fixture.ts', 'src/lib/utils/chartTheme.ts']);
        expect(catalog.files).toEqual(['src/app.css', 'src/lib/components/Badge.svelte', 'src/lib/utils/chartTheme.ts', 'src/app.html', 'static/offline.html']);
        expect(['src/lib/x.test.ts', 'e2e/a.spec.ts', 'src/lib/__tests__/x.ts', 'src/__mocks__/$app/stores.ts'].every(isTestPath)).toBe(true);
        expect(isTestPath('src/lib/utils/latest.ts')).toBe(false);
    });

    it('counts what color_inventory.py counts', () => {
        // tw: bg-emerald-600, dark:bg-emerald-900/40 (palette) + text-white (black/white); custom: text-libre-green;
        // arbitrary: border-[#2b2b2b]; hex: 2 + 2 + 2; fn: rgb(), oklch(), rgba(); var() reads: --theme-bg-card,
        // --color-gray-900 and the test file's --test-only; definitions: 4 in app.css + 1 in the test file.
        expect(catalog.meta.parity).toEqual({files: 5, tw: 3, custom: 1, arbitrary: 1, hex: 6, fn: 3, var_uses: 3, var_uses_distinct: 3, var_defs: 5});
    });

    it('gives every literal an id, a layer and its place, documents outside the bundle included', () => {
        expect(catalog.meta.layers).toEqual({'css-literal': 5, script: 1, 'chart-color': 3, static: 2});
        expect(catalog.literals.map((l) => [l.id, catalog.files[l.file], l.line, l.raw, l.layer])).toEqual([
            [0, 'src/app.css', 2, '#1a4031', 'css-literal'],
            [1, 'src/app.css', 5, '#ffffff', 'css-literal'],
            [2, 'src/app.css', 9, 'oklch(27.9% 0.041 260.031)', 'css-literal'],
            [3, 'src/lib/components/Badge.svelte', 2, '#1a4031', 'script'],
            [4, 'src/lib/components/Badge.svelte', 5, '#2b2b2b', 'css-literal'],
            [5, 'src/lib/components/Badge.svelte', 9, 'rgb(30 41 59 / 50%)', 'css-literal'],
            [6, 'src/lib/utils/chartTheme.ts', 1, '#94a3b8', 'chart-color'],
            [7, 'src/lib/utils/chartTheme.ts', 1, '#475569', 'chart-color'],
            [8, 'src/lib/utils/chartTheme.ts', 2, 'rgba(148, 163, 184, 0.2)', 'chart-color'],
            [9, 'src/app.html', 1, '#1a4031', 'static'],
            [10, 'static/offline.html', 1, '#0f172a', 'static'],
        ]);
        expect(catalog.by_value['#1a4031']).toEqual([0, 3, 9]);
        for (const [key, ids] of Object.entries(catalog.by_value))
            expect(
                ids.every((id) => catalog.literals[id].key === key),
                key,
            ).toBe(true);
    });

    it('stamps the catalogue with its schema, the app version, a content hash and the folders it left out', () => {
        expect(catalog.meta).toMatchObject({schema: CATALOG_SCHEMA, app_version: '1.2.0-test', excluded: LAB_DIRS});
        expect(catalog.meta.hash).toMatch(/^sha256:[0-9a-f]{64}$/);
        expect(catalogOf({root, appVersion: 'another'}).meta.hash).toBe(catalog.meta.hash);
    });

    it('lists the variables of the production files with their definitions, and the palette with its uses', () => {
        expect(catalog.css_vars.map((v) => v.name)).toEqual(['--color-gray-900', '--color-libre-green', '--theme-bg-card', '--theme-text']);
        expect(catalog.css_vars.find((v) => v.name === '--theme-bg-card')).toEqual({
            name: '--theme-bg-card',
            defs: [
                {file: 0, name: '--theme-bg-card', value: '#ffffff', line: 5, zone: 'css-file', selector: ':root', theme: 'both', scope: 'root'},
                {file: 0, name: '--theme-bg-card', value: 'oklch(27.9% 0.041 260.031)', line: 9, zone: 'css-file', selector: 'html.dark', theme: 'dark', scope: 'root'},
            ],
            uses: 1,
            files: {'1': 1},
            use_sites: [[1, 10, 'span']],
        });
        expect(catalog.palette.map((p) => p.var)).toEqual(['--color-emerald-600', '--color-emerald-900', '--color-libre-green', '--color-white']);
        expect(catalog.palette.find((p) => p.var === '--color-emerald-900')).toEqual({var: '--color-emerald-900', uses: 1, dark: 1, classes: {'dark:bg-emerald-900/40': 1}, files: {'1': 1}, occ: [[1, 5, 0]]});
    });
});

describe('scanColors — variable scopes, class uses and test ids of a synthetic tree', () => {
    let catalog: ColorCatalog;
    const file = (rel: string) => {
        const at = catalog.files.indexOf(rel);
        expect(at, rel).toBeGreaterThanOrEqual(0);
        return at;
    };

    beforeAll(() => {
        const root = makeTree({
            'src/app.css': [
                ':root,',
                'html.light {',
                '    --theme-text: #111827;',
                '}',
                'html:not(.dark) {',
                '    --theme-muted: #6b7280;',
                '}',
                'html:not(.light) {',
                '    --theme-muted: #9ca3af;',
                '}',
                '.card {',
                '    --card-accent: #10b981;',
                '    color: var(--theme-text);',
                '}',
                '@layer base {',
                '    :root {',
                '        --lf-ring: #2563eb;',
                '    }',
                '}',
            ],
            'src/lib/components/Chip.svelte': [
                '<script lang="ts">',
                "    const style = 'color: var(--theme-text)';",
                '</script>',
                '',
                '<span class="chip" style="color: var(--theme-muted)">x</span>',
                '',
                '<style>',
                '    .chip {',
                '        --chip-bg: #fef3c7;',
                '        background: var(--chip-bg);',
                '    }',
                '</style>',
            ],
            'src/lib/components/More.svelte': ['<b class="text-gray-500">e</b>'],
            'src/lib/components/Table.svelte': [
                '<script lang="ts">',
                "    if (testid === 'compared-id') probe();",
                "    const tabs = [{testId: 'menu-a'}, {testId: `menu-${name}`}];",
                "    let {testId = 'default-id', optionTestId}: Props = $props();",
                '    const rowTestId = `row-${id}`;',
                "    const tabTestIdPrefix = 'tab-p';",
                '    let hasTestId = true;',
                '    interface Props { testId?: string; optionTestId: string }',
                '</script>',
                '',
                '<div data-testid="tx-table">',
                '    <Row testid="tx-row" />',
                '    <Cell data-testid={`cell-${id}`} />',
                '    <Cell testId={`ab-${id}`} />',
                '    <Cell testid={`a-${id}`} />',
                "    <Tab data-testid={active ? 'tab-active' : 'tab-idle'} />",
                "    <Pane data-testid={phase === 'catalog_loading' ? 'pane-loading' : 'pane-ready'} />",
                '    <Thing data-testid={testId} />',
                '    <Other data-testid="{testid}-row" />',
                '    <Row data-testid={`filter-currency-row-${code}`} />',
                '</div>',
                '<A data-testid={tid ?? `tab-${key}`} />',
                "<B data-testid={tid || 'fallback-id'} />",
                '<Select optionTestId={(o) => `opt-${o.value}`} filterRowTestId="filter-row" testIdPrefix="pre-" />',
                "<C data-testid={label('call-arg')} />",
                "<D data-testid={('grouped-id')} />",
                '<style>',
                "    [data-testid='styled'] {",
                '        color: red;',
                '    }',
                '</style>',
            ],
            'src/lib/components/Text.svelte': ['<p class="text-gray-500 dark:text-gray-400">a</p>', '<p class="text-gray-500">b</p>', '<span class="bg-gray-500/20">c</span>', '<i class="border-gray-500 text-gray-500">d</i>'],
            'src/lib/utils/markup.ts': ['export const row = \'<tr data-testid="ts-only"></tr>\';'],
            'src/lib/utils/tabs.ts': ["export const TABS = [{key: 'a', testId: 'settings-tab-general'}, {key: 'b', testId: `settings-tab-${key}`}];"],
            'src/lib/utils/vars.ts': ['export const css = `', '    --ts-var: #123456;', '`;'],
        });
        catalog = catalogOf({root});
    });

    it('marks a definition `root` when its selectors cover the page — `html:not(.dark|.light)` included — and `scoped` otherwise', () => {
        const defs = catalog.css_vars.flatMap((v) => v.defs.map((d) => [d.name, d.selector, d.theme, d.scope, d.zone]));
        expect(defs).toEqual([
            ['--card-accent', '.card', 'both', 'scoped', 'css-file'],
            ['--chip-bg', '.chip', 'both', 'scoped', 'svelte-style'],
            ['--lf-ring', ':root', 'both', 'root', 'css-file'],
            ['--theme-muted', 'html:not(.dark)', 'light', 'root', 'css-file'],
            ['--theme-muted', 'html:not(.light)', 'dark', 'root', 'css-file'],
            ['--theme-text', ':root, html.light', 'both', 'root', 'css-file'],
            ['--ts-var', null, null, 'scoped', 'ts'],
        ]);
    });

    it('records where each variable is read: file, line, and the rule when a stylesheet reads it', () => {
        const sites = (name: string) => catalog.css_vars.find((v) => v.name === name)?.use_sites;
        expect(sites('--theme-text')).toEqual([
            [file('src/app.css'), 13, '.card'],
            [file('src/lib/components/Chip.svelte'), 2, null],
        ]);
        expect(sites('--theme-muted')).toEqual([[file('src/lib/components/Chip.svelte'), 5, null]]);
        expect(sites('--chip-bg')).toEqual([[file('src/lib/components/Chip.svelte'), 10, '.chip']]);
    });

    it('indexes every class use of a palette variable by the class it is written with', () => {
        const gray = catalog.palette.find((p) => p.var === '--color-gray-500');
        const more = file('src/lib/components/More.svelte');
        const text = file('src/lib/components/Text.svelte');
        expect(gray).toMatchObject({uses: 6, dark: 0, classes: {'text-gray-500': 4, 'bg-gray-500/20': 1, 'border-gray-500': 1}});
        expect(Object.keys(gray?.classes ?? {})).toEqual(['text-gray-500', 'bg-gray-500/20', 'border-gray-500']);
        expect(gray?.occ).toEqual([
            [more, 1, 0],
            [text, 1, 0],
            [text, 2, 0],
            [text, 3, 1],
            [text, 4, 2],
            [text, 4, 0],
        ]);
        expect(catalog.palette.find((p) => p.var === '--color-gray-400')).toMatchObject({uses: 1, dark: 1, classes: {'dark:text-gray-400': 1}, occ: [[text, 1, 0]]});
    });

    it('indexes the test ids the code writes — attribute, prop, script — and the prefixes of the templated ones, longest first', () => {
        const table = file('src/lib/components/Table.svelte');
        const tabs = file('src/lib/utils/tabs.ts');
        // Not indexed: a comparison operand, a `…Prefix` name, an optional property's type, a flag, a pass-through,
        // a prefix under three characters, a call argument, a selector in the component's own <style>, and markup
        // written in a script string (`markup.ts`).
        expect(catalog.testids).toEqual({
            'menu-a': [[table, 3, 'script']],
            'default-id': [[table, 4, 'script']],
            'tx-table': [[table, 11, 'attr']],
            'tx-row': [[table, 12, 'prop']],
            'tab-active': [[table, 16, 'attr']],
            'tab-idle': [[table, 16, 'attr']],
            'pane-loading': [[table, 17, 'attr']],
            'pane-ready': [[table, 17, 'attr']],
            'fallback-id': [[table, 23, 'attr']],
            'filter-row': [[table, 24, 'prop']],
            'grouped-id': [[table, 26, 'attr']],
            'settings-tab-general': [[tabs, 1, 'script']],
        });
        expect(catalog.testid_prefixes).toEqual([
            ['filter-currency-row-', table, 20, 'attr'],
            ['settings-tab-', tabs, 1, 'script'],
            ['menu-', table, 3, 'script'],
            ['cell-', table, 13, 'attr'],
            ['row-', table, 5, 'script'],
            ['tab-', table, 22, 'attr'],
            ['opt-', table, 24, 'prop'],
            ['ab-', table, 14, 'prop'],
        ]);
    });
});

describe('scanColors — the colour roles of a synthetic tree: aliases of `@theme inline` and the role they stand for', () => {
    let catalog: ColorCatalog;
    const file = (rel: string) => {
        const at = catalog.files.indexOf(rel);
        expect(at, rel).toBeGreaterThanOrEqual(0);
        return at;
    };
    const defsOf = (name: string) => {
        const v = catalog.css_vars.find((x) => x.name === name);
        expect(v, name).toBeDefined();
        return v?.defs ?? [];
    };

    beforeAll(() => {
        const root = makeTree({
            'src/lib/theme/tokens.css': [
                ':root,',
                'html.light {',
                '    --lf-surface-card: #f5f5f4;',
                '    --lf-chart-1: #3d5a80;',
                '}',
                'html.dark,',
                '.dark {',
                '    --lf-surface-card: #1c1917;',
                '}',
                '@theme inline {',
                '    --color-lf-card: var(--lf-surface-card);',
                '    --color-lf-mixed: color-mix(in oklab, var(--lf-surface-card) 50%, white);',
                '    --color-lf-both: var(--lf-surface-card);',
                '    --color-lf-split: var(--lf-surface-card);',
                '    --color-lf-twice: var(--lf-surface-card);',
                '    --color-lf-chart-1: var(--lf-chart-1);',
                '}',
                '@theme {',
                '    --color-libre-green: #1a4031;',
                '}',
            ],
            // A second stylesheet: `--color-lf-both` defined again as a plain variable, `--color-lf-split` aliased to
            // another variable, `--color-lf-twice` aliased again to the same one (spaces inside `var()` included).
            'src/app.css': [':root {', '    --color-lf-both: #123456;', '}', '@theme inline {', '    --color-lf-split: var(--lf-other);', '    --color-lf-twice: var( --lf-surface-card );', '}'],
            // `bg-lf-ghost` names an alias no stylesheet defines; `bg-lf-chart-1/40` a numbered role.
            'src/lib/components/Card.svelte': ['<div class="bg-lf-card hover:border-lf-card/50 text-lf-mixed bg-libre-green text-gray-500"></div>', '<p class="ring-lf-both text-lf-split fill-lf-twice bg-lf-ghost"></p>', '<span class="bg-lf-chart-1/40"></span>'],
        });
        catalog = catalogOf({root});
    });

    it('counts a role utility as a custom class, a variant, an opacity and a digit in its name included, under the alias variable it names', () => {
        // custom: bg-lf-card, hover:border-lf-card/50, text-lf-mixed, bg-libre-green, ring-lf-both, text-lf-split,
        // fill-lf-twice, bg-lf-ghost, bg-lf-chart-1/40; tw: text-gray-500.
        expect(catalog.meta.parity).toMatchObject({tw: 1, custom: 9});
        const card = file('src/lib/components/Card.svelte');
        expect(catalog.palette.find((p) => p.var === '--color-lf-card')).toEqual({
            var: '--color-lf-card',
            uses: 2,
            dark: 0,
            classes: {'bg-lf-card': 1, 'hover:border-lf-card/50': 1},
            files: {[card]: 2},
            occ: [
                [card, 1, 0],
                [card, 1, 1],
            ],
            role: '--lf-surface-card',
        });
        expect(catalog.palette.find((p) => p.var === '--color-lf-chart-1')).toEqual({var: '--color-lf-chart-1', uses: 1, dark: 0, classes: {'bg-lf-chart-1/40': 1}, files: {[card]: 1}, occ: [[card, 3, 0]], role: '--lf-chart-1'});
    });

    it('marks a definition of `@theme inline` as inline, with the variable it names when its value is only `var()`', () => {
        expect(defsOf('--color-lf-card')).toEqual([expect.objectContaining({value: 'var(--lf-surface-card)', inline: true, alias_of: '--lf-surface-card'})]);
        expect(defsOf('--color-lf-chart-1')).toEqual([expect.objectContaining({value: 'var(--lf-chart-1)', inline: true, alias_of: '--lf-chart-1'})]);
        expect(defsOf('--color-lf-mixed')).toEqual([expect.objectContaining({value: 'color-mix(in oklab, var(--lf-surface-card) 50%, white)', inline: true, alias_of: null})]);
        expect(defsOf('--color-lf-split').map((d) => [catalog.files[d.file], d.inline, d.alias_of])).toEqual([
            ['src/app.css', true, '--lf-other'],
            ['src/lib/theme/tokens.css', true, '--lf-surface-card'],
        ]);
        expect(defsOf('--color-lf-twice').map((d) => d.alias_of)).toEqual(['--lf-surface-card', '--lf-surface-card']);
    });

    it('writes neither field for any other definition, a plain `@theme` included', () => {
        const fields = (name: string) => defsOf(name).map((d) => ['inline', 'alias_of'].filter((k) => k in d));
        expect(fields('--color-libre-green')).toEqual([[]]);
        expect(fields('--lf-surface-card')).toEqual([[], []]);
        // The same variable, defined in `:root` and in `@theme inline`: only the inline definition carries them.
        expect(defsOf('--color-lf-both').map((d) => [d.value, ['inline', 'alias_of'].filter((k) => k in d)])).toEqual([
            ['#123456', []],
            ['var(--lf-surface-card)', ['inline', 'alias_of']],
        ]);
    });

    it('gives a palette entry a role only when every definition of its variable is an inline alias of one same variable', () => {
        expect(Object.fromEntries(catalog.palette.map((p) => [p.var, p.role ?? null]))).toEqual({
            '--color-gray-500': null,
            // Also defined in `:root`: a stylesheet defines the variable at runtime.
            '--color-lf-both': null,
            '--color-lf-card': '--lf-surface-card',
            // A digit in the role's name.
            '--color-lf-chart-1': '--lf-chart-1',
            // No definition at all.
            '--color-lf-ghost': null,
            // An expression, not a plain alias.
            '--color-lf-mixed': null,
            // Two aliases naming two variables.
            '--color-lf-split': null,
            // Two aliases naming the same variable, in two files.
            '--color-lf-twice': '--lf-surface-card',
            // A plain `@theme` variable.
            '--color-libre-green': null,
        });
        // An entry without a role carries no `role` key.
        expect(catalog.palette.filter((p) => !p.role && 'role' in p).map((p) => p.var)).toEqual([]);
    });
});

describe('scanColors — the real tree, invariants only', () => {
    let first: ColorCatalog;
    let second: ColorCatalog;

    // Two scans of `frontend/src`: a few seconds each, more on a loaded machine.
    beforeAll(() => {
        first = catalogOf();
        second = catalogOf();
    }, 120_000);

    it('is a catalogue of this schema, made of the app’s own sources', () => {
        expect(first.meta.schema).toBe(CATALOG_SCHEMA);
        expect(first.meta.excluded).toEqual(LAB_DIRS);
        expect(first.meta.hash).toMatch(/^sha256:[0-9a-f]{64}$/);
        const sources = first.files.filter((f) => !STATIC_SOURCES.includes(f));
        expect(sources.length).toBeGreaterThan(0);
        expect(sources.filter((f) => LAB_DIRS.some((dir) => f.startsWith(dir)) || isTestPath(f))).toEqual([]);
        for (const rel of STATIC_SOURCES) expect(first.files.includes(rel), rel).toBe(existsSync(join(FRONTEND_DIR, rel)));
    });

    it('is the same catalogue on a second scan of the same tree', () => {
        expect(second.meta.hash).toBe(first.meta.hash);
    });

    it('carries every parity figure of the Python inventory', () => {
        expect(Object.keys(first.meta.parity).sort()).toEqual(['arbitrary', 'custom', 'files', 'fn', 'hex', 'tw', 'var_defs', 'var_uses', 'var_uses_distinct']);
        for (const [key, value] of Object.entries(first.meta.parity)) expect(Number.isInteger(value) && value >= 0, key).toBe(true);
        expect(first.meta.parity.files).toBe(listSourceFiles().length);
        expect(first.meta.parity.var_uses_distinct).toBeLessThanOrEqual(first.meta.parity.var_uses);
    });

    it('gives every literal one of the five layers, and the layer counts add up to the literals', () => {
        const layers = ['chart-color', 'css-literal', 'markup', 'script', 'static'];
        expect(Object.keys(first.meta.layers).filter((l) => !layers.includes(l))).toEqual([]);
        expect(Object.values(first.meta.layers).reduce((a, b) => a + b, 0)).toBe(first.literals.length);
    });

    it('points every index at an entry that exists', () => {
        const fileOk = (f: number) => Number.isInteger(f) && f >= 0 && f < first.files.length;
        const bad: string[] = [];
        first.literals.forEach((l, i) => {
            if (l.id !== i || !fileOk(l.file) || l.line < 1) bad.push(`literal ${i}`);
        });
        for (const [key, ids] of Object.entries(first.by_value)) if (!ids.every((id) => first.literals[id]?.key === key)) bad.push(`by_value ${key}`);
        for (const p of first.palette) {
            const classes = Object.keys(p.classes);
            if (p.occ.length !== p.uses || Object.values(p.classes).reduce((a, b) => a + b, 0) !== p.uses) bad.push(`palette ${p.var} uses`);
            if (!p.occ.every(([f, line, c]) => fileOk(f) && line >= 1 && Number.isInteger(c) && c >= 0 && c < classes.length)) bad.push(`palette ${p.var} occ`);
            if (!Object.keys(p.files).every((f) => fileOk(Number(f)))) bad.push(`palette ${p.var} files`);
        }
        for (const v of first.css_vars) {
            if (!v.defs.every((d) => fileOk(d.file) && (d.scope === 'root' || d.scope === 'scoped'))) bad.push(`css_var ${v.name} defs`);
            if (v.use_sites.length !== v.uses || !v.use_sites.every(([f, line]) => fileOk(f) && line >= 1)) bad.push(`css_var ${v.name} use_sites`);
        }
        for (const [id, sites] of Object.entries(first.testids)) if (!sites.every(([f, line, via]) => fileOk(f) && line >= 1 && VIAS.includes(via))) bad.push(`testid ${id}`);
        first.testid_prefixes.forEach(([prefix, f, line, via], i) => {
            if (!fileOk(f) || line < 1 || !VIAS.includes(via) || (i > 0 && prefix.length > first.testid_prefixes[i - 1][0].length)) bad.push(`testid prefix ${prefix}`);
        });
        expect(bad).toEqual([]);
    });

    it('gives every `--color-lf-*` entry a stylesheet defines a role defined for the whole page, and leaves the others to the theme-roles gate', () => {
        const lf = first.palette.filter((p) => p.var.startsWith('--color-lf-'));
        // A role class whose alias no stylesheet defines (a name written in a comment, a utility that does not exist) is
        // not checked here: the theme-roles gate of workstream T owns the validity of the role classes.
        const defined = new Set(first.css_vars.filter((v) => v.defs.length).map((v) => v.name));
        const aliases = lf.filter((p) => defined.has(p.var));
        expect(aliases.filter((p) => p.role).length, 'the scanner sees the role utilities (bg-lf-…)').toBeGreaterThan(0);
        expect(aliases.filter((p) => !p.role).map((p) => p.var)).toEqual([]);
        // The role is the variable the Lab overrides on <html>: some definition of it covers the whole page.
        const pageWide = new Set(first.css_vars.filter((v) => v.defs.some((d) => d.scope === 'root')).map((v) => v.name));
        expect(aliases.filter((p) => p.role && !pageWide.has(p.role)).map((p) => `${p.var} → ${p.role}`)).toEqual([]);
        // An alias exists only in `@theme inline`: no stylesheet defines it at runtime.
        expect(first.css_vars.filter((v) => v.name.startsWith('--color-lf-') && v.defs.length && !isInlineAlias(v)).map((v) => v.name)).toEqual([]);
        // Every use of a role utility, defined or not, is a custom class of the inventory.
        expect(lf.reduce((n, p) => n + p.uses, 0)).toBeLessThanOrEqual(first.meta.parity.custom);
    });
});
