/**
 * Designer Lab — what the Lab makes of a picked element (`pickView.ts`).
 *
 * For each colour the app tab reported, the Lab names the source that sets it in the code (a variable, a Tailwind
 * class, a stylesheet rule, an inline style…), what editing that shared source means, the specialisation of the
 * element alone, and the places where an agent would bind it. Pure functions over a synthetic catalogue and synthetic
 * picks: every expected place follows from the entries below.
 *
 * The cases mirror the three of the step 5b check: a component rule (`th { color: #64748b }` in `DataTable.svelte`,
 * test id `tx-table` in `TransactionsTable.svelte`), a Tailwind class reading a palette variable, and the dark P1
 * override of `app.css` sitting on top of a `dark:` class. A fourth follows the colour roles: a utility (`bg-lf-card`)
 * that reads its role (`--lf-surface-card`) directly, its alias of `@theme inline` existing in the sources only.
 */

import {describe, expect, it} from 'vitest';
import {buildAnchor, classify, firstClass, keyOfColor, keysOf, pickView, ruleLiterals, testidSites, varChain, type PropertyView} from './pickView';
import type {CatalogLiteral, CatalogPaletteEntry, CatalogVar, CatalogVarDef, ColorCatalog, PickedChart, PickedDeclaration, PickedElement, PickedProperty} from './types';

const DATA_TABLE = 'src/lib/components/table/DataTable.svelte';
const TX_TABLE = 'src/lib/features/transactions/TransactionsTable.svelte';
const APP_CSS = 'src/app.css';
const ELSEWHERE = 'src/lib/components/other/Elsewhere.svelte';
const GROWTH = 'src/lib/features/dashboard/GrowthChart.svelte';
const FILES = [DATA_TABLE, TX_TABLE, APP_CSS, ELSEWHERE, GROWTH];
const [F_DATA_TABLE, F_TX_TABLE, F_APP_CSS, F_ELSEWHERE, F_GROWTH] = [0, 1, 2, 3, 4];

function literal(id: number, fields: Partial<CatalogLiteral>): CatalogLiteral {
    return {id, file: F_DATA_TABLE, line: 1, col: 1, raw: '#64748b', kind: 'hex', key: '#64748b', alpha: 1, zone: 'svelte-style', theme: 'both', layer: 'css-literal', preview: true, snippet: '', ...fields};
}

const LITERALS: CatalogLiteral[] = [
    literal(0, {file: F_DATA_TABLE, line: 1607, selector: 'th', property: 'color'}),
    literal(1, {file: F_ELSEWHERE, line: 12, selector: 'th', property: 'color'}),
    literal(2, {file: F_DATA_TABLE, line: 1700, selector: '.cell', property: 'border-color'}),
    literal(3, {file: F_APP_CSS, line: 400, raw: '#94a3b8', key: '#94a3b8', zone: 'css-file', theme: 'dark', selector: 'html.dark .text-gray-500', property: 'color'}),
    literal(4, {file: F_TX_TABLE, line: 1000, raw: '#ef4444', key: '#ef4444', zone: 'svelte-markup', via: 'style-attr', theme: null, layer: 'markup', preview: false}),
    literal(5, {file: F_GROWTH, line: 120, raw: '#10b981', key: '#10b981', zone: 'svelte-script', theme: null, layer: 'chart-color', chart: true}),
    literal(6, {file: F_GROWTH, line: 121, raw: '#3b82f6', key: '#3b82f6', zone: 'svelte-script', theme: null, layer: 'chart-color', chart: true}),
    literal(7, {file: F_ELSEWHERE, line: 30, raw: '#10b981', key: '#10b981', zone: 'svelte-script', theme: null, layer: 'chart-color', chart: true}),
    literal(8, {file: F_ELSEWHERE, line: 31, raw: '#ef4444', key: '#ef4444', zone: 'svelte-script', theme: null, layer: 'script', preview: false}),
];

const paletteEntry = (name: string, classes: Record<string, number>, occ: [number, number, number][]): CatalogPaletteEntry => ({var: name, uses: occ.length, dark: 0, classes, files: {}, occ});

const PALETTE: CatalogPaletteEntry[] = [
    paletteEntry(
        '--color-blue-500',
        {'text-blue-500': 15},
        Array.from({length: 15}, (_, i): [number, number, number] => [F_TX_TABLE, 2000 + i, 0]),
    ),
    paletteEntry('--color-gray-400', {'dark:text-gray-400': 2}, [
        // Twice on one line: `class={cond ? 'dark:text-gray-400' : 'dark:text-gray-400 font-bold'}`.
        [F_TX_TABLE, 1001, 0],
        [F_TX_TABLE, 1001, 0],
    ]),
    paletteEntry('--color-gray-500', {'text-gray-500': 2, 'border-gray-500': 1}, [
        [F_TX_TABLE, 1001, 0],
        [F_ELSEWHERE, 7, 0],
        [F_TX_TABLE, 1002, 1],
    ]),
];

const def = (name: string, value: string, fields: Partial<CatalogVarDef> = {}): CatalogVarDef => ({file: F_APP_CSS, name, value, line: 1, zone: 'css-file', selector: ':root', theme: 'both', scope: 'root', ...fields});

const cssVar = (name: string, defs: CatalogVarDef[], use_sites: [number, number, string | null][] = []): CatalogVar => ({name, defs, uses: use_sites.length, files: {}, use_sites});

/** `--deep-0` → `--deep-1` → … → `--deep-9` → `#000000`. */
const DEEP = Array.from({length: 10}, (_, i) => cssVar(`--deep-${i}`, [def(`--deep-${i}`, i === 9 ? '#000000' : `var(--deep-${i + 1})`)]));

const CSS_VARS: CatalogVar[] = [
    cssVar('--cyc-a', [def('--cyc-a', 'var(--cyc-b)')]),
    cssVar('--cyc-b', [def('--cyc-b', 'var(--cyc-a)')]),
    ...DEEP,
    cssVar('--dual', [def('--dual', 'var(--dual-light)'), def('--dual', 'var(--dual-dark)', {selector: 'html.dark', theme: 'dark'})]),
    cssVar('--lf-a', [def('--lf-a', 'var(--lf-b)')]),
    cssVar('--lf-b', [def('--lf-b', 'var(--lf-c, #000)')]),
    cssVar('--lf-c', [def('--lf-c', '#123456')]),
    cssVar(
        '--theme-text-muted',
        [def('--theme-text-muted', '#6b7280', {selector: ':root, html.light'}), def('--theme-text-muted', '#94a3b8', {selector: 'html.dark', theme: 'dark'})],
        [
            [F_APP_CSS, 400, 'html.dark .text-gray-500'],
            [F_DATA_TABLE, 1650, 'th.sorted'],
            [F_ELSEWHERE, 9, '.far'],
        ],
    ),
];

const CATALOG: ColorCatalog = {
    meta: {schema: 'lf-color-catalog/1', app_version: 'test', generated_at: '2026-10-14T18:00:00.000Z', hash: 'sha256:test', scan_ms: 0, parity: {}, layers: {}, excluded: []},
    files: FILES,
    css_vars: CSS_VARS,
    palette: PALETTE,
    literals: LITERALS,
    by_value: {},
    testids: {
        'data-table': [[F_DATA_TABLE, 1500, 'attr']],
        'growth-chart': [
            [F_GROWTH, 50, 'attr'],
            [F_GROWTH, 51, 'prop'],
        ],
        'many-places': Array.from({length: 6}, (_, i): [number, number, 'attr' | 'prop'] => [F_ELSEWHERE, 100 + i, 'attr']),
        'tx-page': [[F_TX_TABLE, 900, 'attr']],
        'tx-table': [[F_TX_TABLE, 993, 'attr']],
    },
    testid_prefixes: [
        ['filter-currency-row-', F_ELSEWHERE, 40, 'attr'],
        ['filter-', F_ELSEWHERE, 39, 'attr'],
        ['row-', F_DATA_TABLE, 300, 'prop'],
        ['row-', F_ELSEWHERE, 301, 'attr'],
    ],
};

const TH = '[data-testid="tx-table"] > div > div > table > thead > tr > th';

const decl = (fields: Partial<PickedDeclaration> = {}): PickedDeclaration => ({origin: 'rule', selector: 'th.svelte-1x2y3z', value: '#64748b', declared_as: 'color', important: false, layer: null, sheet: '0.C3P6fEz2.css', conditions: [], state: false, wins: true, ...fields});

const prop = (fields: Partial<PickedProperty> = {}): PickedProperty => ({
    property: 'color',
    computed: 'rgb(100, 116, 139)',
    colors: ['rgb(100, 116, 139)'],
    depth: 0,
    ancestor_tag: null,
    ancestor_testid: null,
    declarations: [decl()],
    proved: true,
    current_color: false,
    lab_override: false,
    selector: TH,
    breadth: 'component',
    matches: 12,
    at_ancestor: false,
    ...fields,
});

const element = (properties: PickedProperty[], fields: Partial<PickedElement> = {}): PickedElement => ({
    at: 0,
    route: '/transactions',
    theme: 'light',
    testids: ['tx-table', 'tx-page'],
    css_path: `${TH}:nth-of-type(2)`,
    element: {tag: 'th', classes: ['sorted'], scope_class: 'svelte-1x2y3z'},
    selector: TH,
    breadth: 'component',
    matches: 12,
    properties,
    chart: null,
    ...fields,
});

/** The view of the one property of a pick. */
function viewOf(p: PickedProperty, fields: Partial<PickedElement> = {}): PropertyView {
    const view = pickView(CATALOG, element([p], fields));
    expect(view.properties).toHaveLength(1);
    return view.properties[0];
}

const places = (view: PropertyView) => view.candidates.map((c) => `${c.why} ${c.file}:${c.line} ${c.needle}`);

/** The dark P1 case: an `!important` rule of `app.css` on top of the `dark:` utility it overrides. */
const P1_WINNER = decl({selector: 'html.dark .text-gray-500', value: 'var(--theme-text-muted)', important: true, sheet: '0.app.css', layer: null});
const P1_LOSER = decl({selector: '.dark\\:text-gray-400:where(.dark, .dark *)', value: 'var(--color-gray-400)', layer: 'utilities', wins: false});

describe('keyOfColor / keysOf', () => {
    it('gives the grouping key of a colour, whatever its spelling', () => {
        expect(keyOfColor('#64748B')).toBe('#64748b');
        expect(keyOfColor('  rgb(100 116 139 / 50%) ')).toBe('#64748b');
        expect(keyOfColor('#fff')).toBe('#ffffff');
        expect(keyOfColor('oklch(59.6% .145 163.225)')).toMatch(/^oklch\(/);
        expect(keyOfColor('currentColor')).toBeNull();
        expect(keyOfColor('var(--theme-text-muted)')).toBeNull();
    });

    it('gives every distinct colour of a value that holds several, and one key for a value that is a colour', () => {
        expect(keysOf('rgb(100, 116, 139)')).toEqual(['#64748b']);
        expect(keysOf('0 1px 2px rgba(0, 0, 0, 0.1), 0 0 0 1px #64748b')).toEqual(['#000000', '#64748b']);
        expect(keysOf('linear-gradient(#ffffff, rgb(255 255 255 / 0))')).toEqual(['#ffffff']);
        expect(keysOf('none')).toEqual([]);
    });
});

describe('firstClass', () => {
    it('unescapes the first class of a selector as the code writes it', () => {
        expect(firstClass('.dark\\:text-gray-400:where(.dark, .dark *)')).toBe('dark:text-gray-400');
        expect(firstClass('.w-1\\/2')).toBe('w-1/2');
        expect(firstClass('.bg-\\[\\#123456\\]')).toBe('bg-[#123456]');
        // A hex escape and the space that ends it: `\32 ` is `2`.
        expect(firstClass('.\\32 xl\\:p-4')).toBe('2xl:p-4');
    });

    it('takes the first class only, past a tag, and gives null without one', () => {
        expect(firstClass('th.sorted.text-gray-500')).toBe('sorted');
        expect(firstClass('.a.b')).toBe('a');
        expect(firstClass('th')).toBeNull();
        expect(firstClass(null)).toBeNull();
    });
});

describe('varChain', () => {
    it('follows a variable to what it is defined with, a reference with a fallback included', () => {
        expect(varChain(CATALOG, '--lf-a', false)).toEqual(['--lf-a', '--lf-b', '--lf-c']);
        expect(varChain(CATALOG, '--color-gray-500', false)).toEqual(['--color-gray-500']);
    });

    it('reads the definition of the theme picked', () => {
        expect(varChain(CATALOG, '--dual', false)).toEqual(['--dual', '--dual-light']);
        expect(varChain(CATALOG, '--dual', true)).toEqual(['--dual', '--dual-dark']);
    });

    it('stops on a cycle and after six steps', () => {
        expect(varChain(CATALOG, '--cyc-a', false)).toEqual(['--cyc-a', '--cyc-b']);
        expect(varChain(CATALOG, '--deep-0', false)).toEqual(['--deep-0', '--deep-1', '--deep-2', '--deep-3', '--deep-4', '--deep-5', '--deep-6']);
    });
});

describe('classify', () => {
    it('reads an inline style and an SVG attribute as such', () => {
        expect(classify(prop({declarations: [decl({origin: 'inline', selector: null, value: '#ef4444'})]}))).toMatchObject({kind: 'inline', varName: null, className: null});
        expect(classify(prop({declarations: [decl({origin: 'inline', selector: null, value: 'var(--theme-text-muted)'})]}))).toMatchObject({kind: 'inline', varName: '--theme-text-muted'});
        expect(classify(prop({property: 'fill', declarations: [decl({origin: 'attribute', selector: null, value: '#ef4444', declared_as: 'fill'})]}))).toMatchObject({kind: 'attribute'});
    });

    it('reads `currentColor` as following `color`, proved or not', () => {
        const fill = decl({selector: '.fill-current', value: 'currentcolor', layer: 'utilities', declared_as: 'fill'});
        expect(classify(prop({property: 'fill', current_color: true, declarations: [fill]}))).toMatchObject({kind: 'current-color', winner: fill});
        expect(classify(prop({property: 'fill', current_color: true, proved: false}))).toMatchObject({kind: 'current-color', winner: null});
    });

    it('reads a winner in the `utilities` layer as a Tailwind class, unescaped, with the variable it reads', () => {
        const winner = decl({selector: '.dark\\:text-gray-400:where(.dark, .dark *)', value: 'var(--color-gray-400)', layer: 'utilities'});
        expect(classify(prop({declarations: [winner]}))).toEqual({kind: 'tailwind-class', winner, varName: '--color-gray-400', className: 'dark:text-gray-400'});
        expect(classify(prop({declarations: [decl({selector: '.text-gray-500', value: 'var(--color-gray-500)', layer: 'theme.utilities'})]}))).toMatchObject({kind: 'tailwind-class', className: 'text-gray-500'});
    });

    it('reads any other rule as a variable when it reads one, else as a literal', () => {
        expect(classify(prop({declarations: [P1_WINNER]}))).toEqual({kind: 'var', winner: P1_WINNER, varName: '--theme-text-muted', className: null});
        expect(classify(prop({declarations: [decl({layer: 'components'})]}))).toMatchObject({kind: 'rule-literal', varName: null, className: null});
    });

    it('reads nothing it could not prove', () => {
        expect(classify(prop({proved: false}))).toEqual({kind: 'unknown', winner: null, varName: null, className: null});
        expect(classify(prop({declarations: [decl({wins: false})]}))).toMatchObject({kind: 'unknown', winner: null});
        expect(classify(prop({declarations: []}))).toMatchObject({kind: 'unknown'});
    });
});

describe('testidSites', () => {
    const sites = (testids: string[]) => testidSites(CATALOG, testids).map((c) => `${c.file}:${c.line} ${c.needle}`);

    it('finds a static id where the code writes it', () => {
        expect(testidSites(CATALOG, ['tx-table'])).toEqual([{file: TX_TABLE, line: 993, why: 'testid', needle: 'tx-table'}]);
        expect(sites(['growth-chart'])).toEqual([`${GROWTH}:50 growth-chart`, `${GROWTH}:51 growth-chart`]);
    });

    it('finds a templated id by its prefix, written `prefix*` or seen as one of its instances', () => {
        expect(sites(['filter-currency-row-*'])).toEqual([`${ELSEWHERE}:40 filter-currency-row-`]);
        expect(sites(['row-*'])).toEqual([`${DATA_TABLE}:300 row-`, `${ELSEWHERE}:301 row-`]);
        expect(sites(['row-42'])).toEqual([`${DATA_TABLE}:300 row-`, `${ELSEWHERE}:301 row-`]);
    });

    it('finds a `prefix*` the picker cut from an id the index did not know by the longest catalogue prefix it extends', () => {
        // `filter-currency-row-eur-*` extends both `filter-` and `filter-currency-row-`: the longer one is the template.
        expect(sites(['filter-currency-row-eur-*'])).toEqual([`${ELSEWHERE}:40 filter-currency-row-`]);
        expect(sites(['filter-panel-*'])).toEqual([`${ELSEWHERE}:39 filter-`]);
        expect(sites(['row-total-*'])).toEqual([`${DATA_TABLE}:300 row-`, `${ELSEWHERE}:301 row-`]);
        // No catalogue prefix it extends: the next id of the chain answers.
        expect(sites(['fil-*', 'tx-table'])).toEqual([`${TX_TABLE}:993 tx-table`]);
    });

    it('answers for the nearest id the catalogue knows, at most four places', () => {
        expect(sites(['unknown-id', 'tx-page', 'tx-table'])).toEqual([`${TX_TABLE}:900 tx-page`]);
        expect(sites(['many-places'])).toHaveLength(4);
        expect(sites(['unknown-id'])).toEqual([]);
        expect(sites([])).toEqual([]);
    });
});

describe('ruleLiterals', () => {
    const lines = (lits: CatalogLiteral[]) => lits.map((l) => `${FILES[l.file]}:${l.line}`);

    it('matches the scoped selector of the page with the selector of the source', () => {
        // `th.svelte-1x2y3z` in the CSSOM is `th` in the component.
        expect(lines(ruleLiterals(CATALOG, decl(), 'color', new Set([F_TX_TABLE])))).toEqual([`${DATA_TABLE}:1607`, `${ELSEWHERE}:12`]);
    });

    it('prefers the files of the component, when the rule is written there', () => {
        expect(lines(ruleLiterals(CATALOG, decl(), 'color', new Set([F_ELSEWHERE])))).toEqual([`${ELSEWHERE}:12`]);
        expect(lines(ruleLiterals(CATALOG, decl(), 'color', new Set([F_DATA_TABLE])))).toEqual([`${DATA_TABLE}:1607`]);
    });

    it('needs a declaration of the property, a shorthand included', () => {
        const border = decl({selector: '.cell.svelte-1x2y3z', declared_as: 'border-color'});
        expect(lines(ruleLiterals(CATALOG, border, 'border-top-color', new Set()))).toEqual([`${DATA_TABLE}:1700`]);
        expect(ruleLiterals(CATALOG, border, 'color', new Set())).toEqual([]);
    });

    it('falls back to the colour in the component’s files when the selectors do not compare', () => {
        const nested = decl({selector: 'div.svelte-1x2y3z > th'});
        expect(lines(ruleLiterals(CATALOG, nested, 'color', new Set([F_DATA_TABLE])))).toEqual([`${DATA_TABLE}:1607`]);
        expect(ruleLiterals(CATALOG, nested, 'color', new Set([F_GROWTH]))).toEqual([]);
    });

    it('finds nothing for a winner without a colour, and at most six places far from the component', () => {
        expect(ruleLiterals(CATALOG, decl({value: 'var(--theme-text-muted)'}), 'color', new Set([F_DATA_TABLE]))).toEqual([]);
        const spread: ColorCatalog = {...CATALOG, literals: Array.from({length: 9}, (_, i) => literal(i, {file: F_ELSEWHERE, line: i + 1, selector: 'td', property: 'color'}))};
        expect(ruleLiterals(spread, decl({selector: 'td.svelte-1x2y3z'}), 'color', new Set())).toHaveLength(6);
    });
});

describe('pickView — sources and candidates', () => {
    it('gives a component rule its exact places first, then the test id', () => {
        const view = viewOf(prop());
        expect(view).toMatchObject({kind: 'rule-literal', keys: ['#64748b'], className: null, varChain: [], darkOverride: false, followsColor: false});
        expect(view.literals.map((l) => l.id)).toEqual([0, 1]);
        expect(places(view)).toEqual([`matched-rule ${DATA_TABLE}:1607 #64748b`, `matched-rule ${ELSEWHERE}:12 #64748b`, `testid ${TX_TABLE}:993 tx-table`]);
    });

    it('gives a Tailwind class its uses near the test ids, each line once', () => {
        const gray = viewOf(prop({declarations: [decl({selector: '.text-gray-500', value: 'var(--color-gray-500)', layer: 'utilities'})]}));
        expect(gray).toMatchObject({kind: 'tailwind-class', className: 'text-gray-500', varChain: ['--color-gray-500']});
        expect(places(gray)).toEqual([`class-use ${TX_TABLE}:1001 text-gray-500`, `testid ${TX_TABLE}:993 tx-table`]);

        const twice = viewOf(prop({declarations: [decl({selector: '.dark\\:text-gray-400:where(.dark, .dark *)', value: 'var(--color-gray-400)', layer: 'utilities'})]}));
        expect(places(twice)).toEqual([`class-use ${TX_TABLE}:1001 dark:text-gray-400`, `testid ${TX_TABLE}:993 tx-table`]);
    });

    it('keeps twelve candidates at most, the exact places first', () => {
        const blue = viewOf(prop({declarations: [decl({selector: '.text-blue-500', value: 'var(--color-blue-500)', layer: 'utilities'})]}));
        expect(blue.candidates).toHaveLength(12);
        expect(blue.candidates.every((c) => c.why === 'class-use')).toBe(true);
    });

    it('gives a variable the rule that reads it, and a class the catalogue does not know the uses of its variable', () => {
        const p1 = viewOf(prop({declarations: [P1_WINNER, P1_LOSER]}), {theme: 'dark'});
        expect(p1).toMatchObject({kind: 'var', varChain: ['--theme-text-muted']});
        expect(places(p1)).toEqual([`var-use ${APP_CSS}:400 --theme-text-muted`, `testid ${TX_TABLE}:993 tx-table`]);

        const unknownClass = viewOf(prop({declarations: [decl({selector: '.text-muted', value: 'var(--theme-text-muted)', layer: 'utilities'})]}));
        expect(places(unknownClass)).toEqual([`var-use ${APP_CSS}:400 --theme-text-muted`, `var-use ${DATA_TABLE}:1650 --theme-text-muted`, `var-use ${ELSEWHERE}:9 --theme-text-muted`, `testid ${TX_TABLE}:993 tx-table`]);
    });

    it('gives an inline colour the markup that writes it near the component', () => {
        const inline = viewOf(prop({computed: 'rgb(239, 68, 68)', colors: ['rgb(239, 68, 68)'], declarations: [decl({origin: 'inline', selector: null, value: '#ef4444'})]}));
        expect(places(inline)).toEqual([`literal ${TX_TABLE}:1000 #ef4444`, `testid ${TX_TABLE}:993 tx-table`]);
    });
});

describe('pickView — edit', () => {
    it('edits the variable a declaration reads', () => {
        expect(viewOf(prop({declarations: [P1_WINNER]}), {theme: 'dark'}).edit).toMatchObject({layer: 'css-var', target: '--theme-text-muted'});
        expect(viewOf(prop({declarations: [decl({selector: '.text-gray-500', value: 'var(--color-gray-500)', layer: 'utilities'})]})).edit).toMatchObject({layer: 'css-var', target: '--color-gray-500'});
        expect(viewOf(prop({declarations: [decl({origin: 'inline', selector: null, value: 'var(--theme-text-muted)'})]})).edit).toMatchObject({layer: 'css-var', target: '--theme-text-muted'});
    });

    it('edits a stylesheet colour by value, on its one occurrence when only one place writes it', () => {
        const twoPlaces = viewOf(prop()).edit;
        expect(twoPlaces).toMatchObject({layer: 'css-literal', target: '#64748b'});
        expect(twoPlaces?.occurrence).toBeUndefined();
        expect(viewOf(prop(), {testids: ['data-table']}).edit).toMatchObject({layer: 'css-literal', target: '#64748b', occurrence: 0});
        const arbitrary = viewOf(prop({property: 'background-color', computed: 'rgb(18, 52, 86)', colors: ['rgb(18, 52, 86)'], declarations: [decl({selector: '.bg-\\[\\#123456\\]', value: '#123456', layer: 'utilities', declared_as: 'background-color'})]}));
        expect(arbitrary).toMatchObject({kind: 'tailwind-class', className: 'bg-[#123456]', edit: {layer: 'css-literal', target: '#123456'}});
    });

    it('proposes an inline or attribute colour, which has no live preview', () => {
        expect(viewOf(prop({declarations: [decl({origin: 'inline', selector: null, value: '#ef4444'})]})).edit).toMatchObject({layer: 'proposal', target: '#ef4444'});
        // A colour name the parser does not read (`red`) is proposed by its computed value.
        expect(viewOf(prop({property: 'fill', computed: 'rgb(255, 0, 0)', colors: ['rgb(255, 0, 0)'], declarations: [decl({origin: 'attribute', selector: null, value: 'red', declared_as: 'fill'})]})).edit).toMatchObject({layer: 'proposal', target: '#ff0000'});
    });

    it('edits nothing for `currentColor` or a source it could not prove', () => {
        expect(viewOf(prop({current_color: true, declarations: [decl({value: 'currentColor'})]})).edit).toBeNull();
        expect(viewOf(prop({proved: false})).edit).toBeNull();
    });

    it('carries the anchor of the pick into the edit', () => {
        const view = viewOf(prop());
        expect(view.edit?.anchor).toEqual(buildAnchor(element([prop()]), view, TH, 12, 'component'));
    });
});

describe('pickView — specialise', () => {
    it('specialises a one-colour property with its own selector, count and computed value', () => {
        const own = '[data-testid="tx-table"] > div > div > table > thead > tr > th.text-gray-500';
        const view = viewOf(prop({selector: own, matches: 3}));
        expect(view.specialise).toMatchObject({layer: 'element', target: own, property: 'color', from: 'rgb(100, 116, 139)'});
        expect(view.specialise?.anchor).toMatchObject({selector: own, matches: 3, breadth: 'component', property: 'color'});
    });

    it('does not specialise a property that holds several colours', () => {
        expect(viewOf(prop({property: 'box-shadow', computed: '0 0 0 1px #64748b', declarations: [decl({declared_as: 'box-shadow'})]})).specialise).toBeNull();
        expect(viewOf(prop({property: 'background-image', computed: 'linear-gradient(#fff, #000)', declarations: [decl({declared_as: 'background-image'})]})).specialise).toBeNull();
    });

    it('does not specialise a background seen through from outside the component, but does the component’s own', () => {
        const through = prop({property: 'background-color', depth: 3, ancestor_tag: 'main', at_ancestor: false, declarations: [decl({declared_as: 'background-color'})]});
        expect(viewOf(through).specialise).toBeNull();

        const card = '[data-testid="tx-table"] > div';
        const own = prop({property: 'background-color', depth: 1, ancestor_tag: 'div', at_ancestor: true, selector: card, matches: 1, breadth: 'component', declarations: [decl({declared_as: 'background-color'})]});
        expect(viewOf(own).specialise).toMatchObject({layer: 'element', target: card, property: 'background-color'});
        expect(viewOf(own).specialise?.anchor).toMatchObject({selector: card, matches: 1});
    });

    it('specialises an inherited text colour wherever it is declared', () => {
        expect(viewOf(prop({depth: 2, ancestor_tag: 'tr', at_ancestor: false})).specialise).toMatchObject({layer: 'element', target: TH, property: 'color'});
    });
});

describe('pickView — badges', () => {
    it('tells the dark P1 override and the utility it overrides', () => {
        const view = viewOf(prop({declarations: [P1_WINNER, P1_LOSER]}), {theme: 'dark'});
        expect(view.darkOverride).toBe(true);
        expect(view.overriddenClass).toBe('dark:text-gray-400');
    });

    it('needs `!important` and `html.dark` for a dark override', () => {
        expect(viewOf(prop({declarations: [{...P1_WINNER, important: false}]})).darkOverride).toBe(false);
        expect(viewOf(prop({declarations: [{...P1_WINNER, selector: '.dark .text-gray-500'}]})).darkOverride).toBe(false);
        expect(viewOf(prop({declarations: [{...P1_WINNER, selector: 'html.darker .text-gray-500'}]})).darkOverride).toBe(false);
        expect(viewOf(prop({declarations: [{...P1_WINNER, selector: ':is(html.dark) .text-gray-500'}]})).darkOverride).toBe(true);
    });

    it('names no overridden class for a state the element was not in, or for a rule outside the utilities', () => {
        expect(viewOf(prop({declarations: [P1_WINNER, {...P1_LOSER, state: true}]})).overriddenClass).toBeNull();
        expect(viewOf(prop({declarations: [P1_WINNER, {...P1_LOSER, layer: null}]})).overriddenClass).toBeNull();
    });

    it('passes on what the app tab saw: a Lab override, `currentColor`, the ancestor', () => {
        const view = viewOf(prop({lab_override: true, current_color: true, declarations: [decl({value: 'currentColor'})], depth: 2, ancestor_tag: 'tr', ancestor_testid: 'row-*'}));
        expect(view).toMatchObject({labOverride: true, followsColor: true, kind: 'current-color', depth: 2, ancestorTag: 'tr', ancestorTestid: 'row-*'});
    });
});

describe('buildAnchor', () => {
    it('says where the change was decided with the pick’s facts and the view’s source, never anything else', () => {
        const pick = element([prop()]);
        const view = viewOf(prop());
        expect(buildAnchor(pick, view)).toEqual({
            route: '/transactions',
            theme: 'light',
            testids: ['tx-table', 'tx-page'],
            css_path: `${TH}:nth-of-type(2)`,
            element: {tag: 'th', classes: ['sorted'], scope_class: 'svelte-1x2y3z'},
            selector: TH,
            breadth: 'component',
            matches: 12,
            property: 'color',
            computed: 'rgb(100, 116, 139)',
            source: {kind: 'rule-literal', selector: 'th.svelte-1x2y3z', var: null, class: null},
            candidates: view.candidates,
        });
        expect(buildAnchor(pick, view, 'body > main > p', 1, 'element')).toMatchObject({selector: 'body > main > p', matches: 1, breadth: 'element'});
        const tw = viewOf(prop({declarations: [decl({selector: '.text-gray-500', value: 'var(--color-gray-500)', layer: 'utilities'})]}));
        expect(buildAnchor(pick, tw).source).toEqual({kind: 'tailwind-class', selector: '.text-gray-500', var: '--color-gray-500', class: 'text-gray-500'});
    });
});

describe('pickView — charts', () => {
    const CHART: PickedChart = {
        host_testid: 'growth-chart',
        selector: '[data-testid="growth-chart"]',
        matches: 1,
        colors: ['#3b82f6', '#10b981', 'rgb(16 185 129)', 'not-a-colour', 'rgba(16, 185, 129, 0.2)'],
        pointed: '#10B981',
    };
    const chartPick = (chart: PickedChart | null) =>
        element([], {route: '/dashboard?tab=overview', testids: ['growth-chart', 'dashboard-page'], css_path: '[data-testid="growth-chart"] > div > canvas', element: {tag: 'canvas', classes: [], scope_class: null}, selector: '[data-testid="growth-chart"] > div > canvas', matches: 1, chart});

    it('lists the chart’s colours once each, the colour under the pointer first', () => {
        const view = pickView(CATALOG, chartPick(CHART)).chart;
        expect(view).toMatchObject({hostTestid: 'growth-chart', selector: '[data-testid="growth-chart"]', matches: 1});
        expect(view?.colors.map((c) => [c.key, c.color, c.pointed])).toEqual([
            ['#10b981', '#10b981', true],
            ['#3b82f6', '#3b82f6', false],
        ]);
        expect(pickView(CATALOG, chartPick({...CHART, pointed: null})).chart?.colors.map((c) => c.key)).toEqual(['#3b82f6', '#10b981']);
        expect(pickView(CATALOG, chartPick(null)).chart).toBeNull();
    });

    it('edits a chart colour everywhere, or specialises it in the charts of this component', () => {
        const green = pickView(CATALOG, chartPick(CHART)).chart?.colors[0];
        expect(green?.edit).toMatchObject({layer: 'chart-color', target: '#10b981'});
        expect(green?.specialise).toMatchObject({layer: 'element', target: '[data-testid="growth-chart"]', property: 'chart', colorKey: '#10b981', from: '#10b981'});
        expect(green?.specialise.anchor).toBe(green?.edit.anchor);
        expect(green?.specialise.anchor).toMatchObject({selector: '[data-testid="growth-chart"]', matches: 1, property: 'chart', computed: '#10b981', source: {kind: 'chart', selector: null, var: null, class: null}});
    });

    it('binds a chart colour where the component writes it, then where its test id is', () => {
        const green = pickView(CATALOG, chartPick(CHART)).chart?.colors[0];
        // `#10b981` is also written in Elsewhere.svelte, away from the chart: not a candidate.
        expect(green?.specialise.anchor?.candidates.map((c) => `${c.why} ${c.file}:${c.line}`)).toEqual([`literal ${GROWTH}:120`, `testid ${GROWTH}:50`, `testid ${GROWTH}:51`]);
    });
});

describe('pickView — filter', () => {
    it('keeps the colours and variables of the winners, of the declarations they beat, and of the chart', () => {
        const hover = decl({selector: 'th.svelte-1x2y3z:hover', value: '#ef4444', state: true, wins: false});
        const view = pickView(
            CATALOG,
            element(
                [
                    prop({computed: 'rgb(148, 163, 184)', colors: ['rgb(148, 163, 184)'], declarations: [P1_WINNER, P1_LOSER, hover]}),
                    prop({property: 'border-bottom-color', computed: 'rgb(18, 52, 86)', colors: ['rgb(18, 52, 86)'], declarations: [decl({value: 'var(--lf-a)', declared_as: 'border-color'})]}),
                ],
                {theme: 'dark', chart: {host_testid: null, selector: '[data-testid="tx-table"]', matches: 1, colors: ['#3b82f6'], pointed: null}},
            ),
        );
        expect([...view.filter.vars].sort()).toEqual(['--color-gray-400', '--lf-a', '--lf-b', '--lf-c', '--theme-text-muted']);
        expect([...view.filter.keys].sort()).toEqual(['#123456', '#3b82f6', '#94a3b8', '#ef4444']);
    });

    it('keeps the catalogue colours of a component rule', () => {
        const view = pickView(CATALOG, element([prop()]));
        expect([...view.filter.keys]).toEqual(['#64748b']);
        expect([...view.filter.vars]).toEqual([]);
        expect(view.element.selector).toBe(TH);
    });
});

describe('pickView — a colour role, read by its utility through an inline alias', () => {
    // `bg-lf-card` is listed under `--color-lf-card`, an alias of `@theme inline` that no stylesheet defines at runtime:
    // Tailwind writes `var(--lf-surface-card)` into the utility itself, so the winning declaration reads the role.
    const ROLE = '--lf-surface-card';
    const alias = (name: string, role: string, classes: Record<string, number>, occ: [number, number, number][]): CatalogPaletteEntry => ({...paletteEntry(name, classes, occ), role});
    const aliasVar = (name: string, role: string) => cssVar(name, [def(name, `var(${role})`, {selector: null, scope: 'scoped', inline: true, alias_of: role})]);
    const ROLES: ColorCatalog = {
        ...CATALOG,
        palette: [
            ...PALETTE,
            alias('--color-lf-card', ROLE, {'bg-lf-card': 2, 'hover:border-lf-card/50': 1}, [
                [F_ELSEWHERE, 60, 0],
                [F_TX_TABLE, 1010, 0],
                [F_TX_TABLE, 1011, 1],
            ]),
            alias('--color-lf-muted', '--lf-text-muted', {'text-lf-muted': 1}, [[F_TX_TABLE, 1012, 0]]),
            alias('--color-lf-on-brand', '--lf-on-brand', {'text-lf-on-brand': 1}, [[F_TX_TABLE, 1014, 0]]),
            // A second alias of the same role, after the first in the palette.
            alias('--color-lf-surface', ROLE, {'bg-lf-surface': 1}, [[F_TX_TABLE, 1013, 0]]),
        ],
        css_vars: [
            ...CSS_VARS,
            aliasVar('--color-lf-card', ROLE),
            aliasVar('--color-lf-muted', '--lf-text-muted'),
            aliasVar('--color-lf-on-brand', '--lf-on-brand'),
            aliasVar('--color-lf-surface', ROLE),
            // A derived role, defined with another role.
            cssVar('--lf-on-brand', [def('--lf-on-brand', `var(${ROLE})`, {selector: ':root, .light, .dark'})]),
            cssVar(ROLE, [def(ROLE, '#f5f5f4', {selector: ':root, html.light, .light'}), def(ROLE, '#1c1917', {selector: 'html.dark, .dark', theme: 'dark'})]),
            cssVar('--lf-text-muted', [def('--lf-text-muted', '#57534e', {selector: ':root, html.light, .light'})]),
        ],
    };

    /** A background set by a role utility, as the app tab reports it: a winner in the `utilities` layer reading the role. */
    const utility = (className: string) => prop({property: 'background-color', computed: 'rgb(245, 245, 244)', colors: ['rgb(245, 245, 244)'], declarations: [decl({selector: `.${className}`, value: `var(${ROLE})`, layer: 'utilities', declared_as: 'background-color'})]});

    const roleView = (p: PickedProperty) => {
        const view = pickView(ROLES, element([p]));
        expect(view.properties).toHaveLength(1);
        return view;
    };

    it('reads the utility as a Tailwind class and edits the role, bound to the uses of the alias near the test ids', () => {
        const [view] = roleView(utility('bg-lf-card')).properties;
        expect(view).toMatchObject({kind: 'tailwind-class', className: 'bg-lf-card'});
        expect(view.varChain[0]).toBe(ROLE);
        expect(view.edit).toMatchObject({layer: 'css-var', target: ROLE});
        expect(view.edit?.anchor?.source).toEqual({kind: 'tailwind-class', selector: '.bg-lf-card', var: ROLE, class: 'bg-lf-card'});
        // The use in Elsewhere.svelte is far from the test ids: not a candidate.
        expect(view.candidates[0]).toEqual({file: TX_TABLE, line: 1010, why: 'class-use', needle: 'bg-lf-card'});
        expect(places(view)).toEqual([`class-use ${TX_TABLE}:1010 bg-lf-card`, `testid ${TX_TABLE}:993 tx-table`]);
    });

    it('binds the utility to the alias that lists its class when two aliases stand for one role', () => {
        // `--color-lf-card` comes first and stands for the same role, but it does not list `bg-lf-surface`.
        const [view] = roleView(utility('bg-lf-surface')).properties;
        expect(view).toMatchObject({kind: 'tailwind-class', className: 'bg-lf-surface', edit: {layer: 'css-var', target: ROLE}});
        expect(places(view)).toEqual([`class-use ${TX_TABLE}:1013 bg-lf-surface`, `testid ${TX_TABLE}:993 tx-table`]);
    });

    it('keeps in the filter the role and every alias standing for it, never the alias of another role', () => {
        const view = roleView(utility('bg-lf-card'));
        expect([...view.filter.vars].sort()).toEqual(['--color-lf-card', '--color-lf-surface', ROLE]);
        expect(view.filter.vars.has('--color-lf-muted')).toBe(false);
    });

    it('keeps the aliases of every role down the chain of a derived role', () => {
        const view = roleView(prop({declarations: [decl({selector: '.text-lf-on-brand', value: 'var(--lf-on-brand)', layer: 'utilities'})]}));
        const [on] = view.properties;
        expect(on.varChain).toEqual(['--lf-on-brand', ROLE]);
        expect(places(on)).toEqual([`class-use ${TX_TABLE}:1014 text-lf-on-brand`, `testid ${TX_TABLE}:993 tx-table`]);
        expect([...view.filter.vars].sort()).toEqual(['--color-lf-card', '--color-lf-on-brand', '--color-lf-surface', '--lf-on-brand', ROLE]);
    });
});
