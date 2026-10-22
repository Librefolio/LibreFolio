/**
 * Designer Lab — the export the agent reads (`export.ts`, schema `lf-designer-lab/1`), its Markdown twin, the
 * one-paragraph summary, and the import that reads an export back.
 *
 * The catalogue is synthetic, so every place an export lists follows from the entries below. What is pinned:
 *   - each layer exports where it lives in the code — palette uses and definitions for a variable, the stylesheet
 *     occurrences of a colour (one theme leaves out only the occurrences certainly of the other), for a
 *     specialisation (`element`) its anchor and the candidate places to bind it, and for a chart category its own line
 *     in each theme of the change, found by key, never the other places that write its value;
 *   - the Markdown and the summary carry the same facts, in the Lab's language for the headings;
 *   - the import refuses what the Lab cannot apply safely — a category its catalogue does not know included —, keeps
 *     an anchor only in the shape and sizes the Lab writes, and finds a single occurrence again by place and value,
 *     never by an id of another catalogue.
 */

import {afterEach, describe, expect, it, vi} from 'vitest';
import {buildExport, isoWithOffset, literalsOf, parseImport, renderMarkdown, renderSummary, sanitizeAnchor, type ContrastRow, type LabExport} from './export';
import {changeId, emptyState} from './store';
import type {CatalogLiteral, ColorCatalog, LabAnchor, LabChange, LabState} from './types';

const HASH = 'sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef';
const APP = '1.2.0-test+150f2716';
const NOW = new Date(2026, 9, 20, 15, 2, 11);

const APP_CSS = 'src/app.css';
const DATA_TABLE = 'src/lib/components/table/DataTable.svelte';
const GROWTH = 'src/lib/components/charts/GrowthChart.svelte';
const COLORS_TS = 'src/lib/utils/colors.ts';
const OFFLINE = 'static/offline.html';
const BADGE = 'src/lib/components/Badge.svelte';
const TX_TABLE = 'src/lib/features/transactions/TransactionsTable.svelte';

function literal(id: number, fields: Partial<CatalogLiteral>): CatalogLiteral {
    return {id, file: 0, line: 1, col: 1, raw: '#64748b', kind: 'hex', key: '#64748b', alpha: 1, zone: 'css-file', theme: 'both', layer: 'css-literal', preview: true, snippet: '', ...fields};
}

/** Every `#64748b` is a variant of one colour; the zones and themes decide which a one-theme change reaches. */
const LITERALS: CatalogLiteral[] = [
    literal(0, {file: 1, line: 1607, col: 16, zone: 'svelte-style', snippet: 'color: #64748b;', selector: 'th', property: 'color'}),
    literal(1, {file: 1, line: 1612, col: 16, raw: '#94a3b8', key: '#94a3b8', zone: 'svelte-style', theme: 'dark', snippet: 'color: #94a3b8;', selector: ':global(.dark) th', property: 'color'}),
    literal(2, {file: 0, line: 40, col: 19, raw: 'rgba(100, 116, 139, 0.5)', kind: 'fn', alpha: 0.5, snippet: 'border-color: rgba(100, 116, 139, 0.5);', selector: '.muted', property: 'border-color'}),
    literal(3, {file: 0, line: 52, col: 12, theme: 'dark', snippet: 'color: #64748b;', selector: 'html.dark .x', property: 'color'}),
    literal(4, {file: 5, line: 3, col: 20, zone: 'svelte-markup', via: 'tw-arbitrary', theme: 'dark', snippet: '<p class="dark:text-[#64748b]">'}),
    literal(5, {file: 5, line: 8, col: 20, zone: 'svelte-markup', via: 'tw-arbitrary', theme: null, snippet: '<p class="text-[#64748b]">'}),
    literal(6, {file: 0, line: 60, col: 12, theme: 'light', snippet: 'color: #64748b;', selector: 'html:not(.dark) .y', property: 'color'}),
    literal(7, {file: 2, line: 120, col: 30, raw: '#10b981', key: '#10b981', zone: 'svelte-script', theme: 'light', layer: 'chart-color', chart: true}),
    literal(8, {file: 2, line: 121, col: 30, raw: 'rgba(16, 185, 129, 0.2)', kind: 'fn', key: '#10b981', alpha: 0.2, zone: 'svelte-script', theme: 'dark', layer: 'chart-color', chart: true}),
    literal(9, {file: 3, line: 5, col: 22, zone: 'ts', theme: 'dark', layer: 'script', preview: false, chart: false}),
    literal(10, {file: 4, line: 10, col: 25, raw: '#0f172a', key: '#0f172a', zone: 'static', theme: null, layer: 'static', preview: false}),
    literal(11, {file: 5, line: 12, col: 30, zone: 'svelte-markup', via: 'style-attr', theme: null, layer: 'markup', preview: false}),
];

function catalogOf(parts: Partial<ColorCatalog> = {}): ColorCatalog {
    return {
        meta: {schema: 'lf-color-catalog/1', app_version: APP, generated_at: '2026-10-20T13:00:00.000Z', hash: HASH, scan_ms: 1, parity: {}, layers: {}, excluded: []},
        files: [APP_CSS, DATA_TABLE, GROWTH, COLORS_TS, OFFLINE, BADGE, TX_TABLE],
        css_vars: [
            {name: '--color-gray-500', defs: [], uses: 1, files: {'0': 1}, use_sites: [[0, 70, '.z']]},
            {
                name: '--theme-text-muted',
                defs: [
                    {file: 0, name: '--theme-text-muted', value: '#6b7280', line: 130, zone: 'css-file', selector: ':root, html.light', theme: 'both', scope: 'root'},
                    {file: 0, name: '--theme-text-muted', value: '#94a3b8', line: 160, zone: 'css-file', selector: 'html.dark', theme: 'dark', scope: 'root'},
                ],
                uses: 4,
                files: {'1': 3, '5': 1},
                use_sites: [[1, 1650, 'th.sorted']],
            },
        ],
        palette: [
            {
                var: '--color-gray-500',
                uses: 3,
                dark: 1,
                classes: {'text-gray-500': 2, 'dark:bg-gray-500': 1},
                files: {'1': 2, '5': 1},
                occ: [
                    [1, 10, 0],
                    [1, 20, 0],
                    [5, 4, 1],
                ],
            },
        ],
        literals: LITERALS,
        by_value: {},
        testids: {},
        testid_prefixes: [],
        ...parts,
    };
}

const CATALOG = catalogOf();

const TH = '[data-testid="tx-table"] > div > table > thead > tr > th';

const ANCHOR: LabAnchor = {
    route: '/transactions',
    theme: 'light',
    testids: ['tx-table', 'tx-page'],
    css_path: '[data-testid="tx-table"] > div > table > thead > tr > th:nth-of-type(2)',
    element: {tag: 'th', classes: ['sorted'], scope_class: 'svelte-1x2y3z'},
    selector: TH,
    breadth: 'component',
    matches: 12,
    property: 'color',
    computed: 'rgb(100, 116, 139)',
    source: {kind: 'rule-literal', selector: 'th', var: null, class: null},
    candidates: [
        {file: DATA_TABLE, line: 1607, why: 'matched-rule', needle: '#64748b'},
        {file: TX_TABLE, line: 993, why: 'testid', needle: 'tx-table'},
    ],
};

const CHART_ANCHOR: LabAnchor = {
    ...ANCHOR,
    route: '/dashboard?tab=overview',
    theme: 'dark',
    testids: ['growth-chart'],
    css_path: '[data-testid="growth-chart"]',
    element: {tag: 'div', classes: [], scope_class: null},
    selector: '[data-testid="growth-chart"]',
    matches: 1,
    property: 'chart',
    computed: '#10b981',
    source: {kind: 'chart', selector: null, var: null, class: null},
    candidates: [{file: GROWTH, line: 120, why: 'literal', needle: '#10b981'}],
};

/** A change as the Lab stores it, with the id the store gives it. */
function make(fields: Omit<LabChange, 'id'>): LabChange {
    return {...fields, id: changeId(fields)};
}

const VAR = make({layer: 'css-var', target: '--color-gray-500', scope: 'both', from: 'oklch(55.1% 0.027 264.364)', to: '#475569', note: 'darker body text'});
const MUTED = make({layer: 'css-var', target: '--theme-text-muted', scope: 'dark', from: '#94a3b8', to: '#cbd5e1'});
const LIT = make({layer: 'css-literal', target: '#64748b', scope: 'both', from: '#64748b', to: '#475569', alphaVariants: true});
const OCC = make({layer: 'css-literal', target: '#64748b', scope: 'both', from: '#64748b', to: '#334155', alphaVariants: true, occurrence: 0, match: {selector: 'th', property: 'color'}});
const CHART = make({layer: 'chart-color', target: '#10b981', scope: 'both', from: '#10b981', to: '#dc2626', alphaVariants: true});
const PROPOSAL = make({layer: 'proposal', target: '#0f172a', scope: 'both', from: '#0f172a', to: '#111827', alphaVariants: true});
const ELEMENT = make({layer: 'element', target: TH, scope: 'light', from: 'rgb(100, 116, 139)', to: '#dc2626', property: 'color', anchor: ANCHOR, shots: ['transactions/table']});
const ELEMENT_CHART = make({layer: 'element', target: '[data-testid="growth-chart"]', scope: 'dark', from: '#10b981', to: '#f59e0b', property: 'chart', colorKey: '#10b981', anchor: CHART_ANCHOR});

const stateOf = (changes: LabChange[], extra: Partial<LabState> = {}): LabState => ({...emptyState(), changes, ...extra});

const exportOf = (changes: LabChange[], extra: Partial<LabState> = {}, contrast: ContrastRow[] = []): LabExport => buildExport(stateOf(changes, extra), CATALOG, APP, contrast, NOW);

const only = (doc: LabExport) => {
    expect(doc.changes).toHaveLength(1);
    return doc.changes[0];
};

const ids = (lits: CatalogLiteral[]) => lits.map((l) => l.id);

afterEach(() => {
    vi.restoreAllMocks();
});

describe('literalsOf', () => {
    it('reaches every variant of the colour in the change’s layer, translucent ones included unless excluded', () => {
        expect(ids(literalsOf(CATALOG, LIT))).toEqual([0, 2, 3, 4, 5, 6]);
        expect(ids(literalsOf(CATALOG, {...LIT, alphaVariants: false}))).toEqual([0, 3, 4, 5, 6]);
        expect(ids(literalsOf(CATALOG, {...LIT, target: '#64748B'}))).toEqual([0, 2, 3, 4, 5, 6]);
    });

    it('leaves out, for one theme, only the stylesheet and markup occurrences that certainly belong to the other', () => {
        // 3: a `html.dark` rule; 4: a `dark:` class. 5: markup without `dark:` is kept.
        expect(ids(literalsOf(CATALOG, {...LIT, scope: 'light'}))).toEqual([0, 2, 5, 6]);
        // 6: a `html:not(.dark)` rule.
        expect(ids(literalsOf(CATALOG, {...LIT, scope: 'dark'}))).toEqual([0, 2, 3, 4, 5]);
    });

    it('keeps a script occurrence in either theme: its theme is a guess from names and ternaries', () => {
        expect(ids(literalsOf(CATALOG, {...CHART, scope: 'light'}))).toEqual([7, 8]);
        expect(ids(literalsOf(CATALOG, {...CHART, scope: 'dark'}))).toEqual([7, 8]);
        expect(ids(literalsOf(CATALOG, {...PROPOSAL, target: '#64748b', scope: 'light'}))).toEqual([9, 11]);
    });

    it('reaches the one occurrence of a single-occurrence change, whatever its layer or theme', () => {
        expect(ids(literalsOf(CATALOG, OCC))).toEqual([0]);
        expect(ids(literalsOf(CATALOG, {...OCC, occurrence: 3, scope: 'light'}))).toEqual([3]);
    });
});

describe('buildExport', () => {
    it('stamps the export with the schema, the app, the catalogue and the local time', () => {
        const contrast: ContrastRow[] = [{fg: '--theme-text-muted', bg: '--theme-bg-card', scope: 'light', before: 4.83, after: 7}];
        const doc = exportOf([], {author: 'designer', notes: 'calmer greys', variants: {A: [VAR]}}, contrast);
        expect(doc).toEqual({schema: 'lf-designer-lab/1', app_version: APP, catalog_hash: HASH, exported_at: isoWithOffset(NOW), author: 'designer', notes: 'calmer greys', changes: [], contrast, variants: {A: [VAR]}});
    });

    it('exports a palette variable with its impact, its classes and every place it is used', () => {
        expect(only(exportOf([VAR]))).toEqual({
            id: 'css-var:--color-gray-500@both',
            layer: 'css-var',
            scope: 'both',
            preview: true,
            target: '--color-gray-500',
            from: 'oklch(55.1% 0.027 264.364)',
            to: '#475569',
            // 3 class uses + 1 `var()` use, in 3 files (DataTable and Badge for the classes, app.css for the `var()`).
            impact: {uses: 4, files: 3, classes: {'text-gray-500': 2, 'dark:bg-gray-500': 1}},
            occurrences: [
                {file: DATA_TABLE, line: 10},
                {file: DATA_TABLE, line: 20},
                {file: BADGE, line: 4},
            ],
            note: 'darker body text',
        });
    });

    it('exports a theme variable with its definitions, and a variable the catalogue does not know with no impact', () => {
        const muted = only(exportOf([MUTED]));
        expect(muted.impact).toEqual({uses: 4, files: 2});
        expect(muted.occurrences).toEqual([]);
        expect(muted.definitions).toEqual([
            {file: APP_CSS, line: 130, selector: ':root, html.light', theme: 'both', value: '#6b7280'},
            {file: APP_CSS, line: 160, selector: 'html.dark', theme: 'dark', value: '#94a3b8'},
        ]);
        const unknown = only(exportOf([{...VAR, target: '--lf-new-role'}]));
        expect(unknown.impact).toEqual({uses: 0, files: 0});
        expect(unknown.occurrences).toEqual([]);
        expect('definitions' in unknown).toBe(false);
    });

    it('exports a stylesheet colour by value with every occurrence it reaches, rule and snippet included', () => {
        const c = only(exportOf([LIT]));
        expect(c).toMatchObject({layer: 'css-literal', preview: true, granularity: 'value', alpha_variants: true});
        expect(c.occurrences.map((o) => `${o.file}:${o.line}`)).toEqual([`${DATA_TABLE}:1607`, `${APP_CSS}:40`, `${APP_CSS}:52`, `${BADGE}:3`, `${BADGE}:8`, `${APP_CSS}:60`]);
        expect(c.occurrences[0]).toEqual({file: DATA_TABLE, line: 1607, col: 16, raw: '#64748b', layer: 'css-literal', theme_context: 'both', selector: 'th', property: 'color', snippet: 'color: #64748b;'});
        // A Tailwind arbitrary class has no rule in the sources.
        expect(c.occurrences[3]).toEqual({file: BADGE, line: 3, col: 20, raw: '#64748b', layer: 'css-literal', theme_context: 'dark', snippet: '<p class="dark:text-[#64748b]">'});
    });

    it('exports a single occurrence alone, and a one-theme change without the other theme’s certain occurrences', () => {
        const occ = only(exportOf([OCC]));
        expect(occ).toMatchObject({granularity: 'occurrence', alpha_variants: true});
        expect(occ.occurrences.map((o) => o.line)).toEqual([1607]);
        const light = only(exportOf([{...LIT, scope: 'light', alphaVariants: false}]));
        expect(light.alpha_variants).toBe(false);
        expect(light.occurrences.map((o) => `${o.file}:${o.line}`)).toEqual([`${DATA_TABLE}:1607`, `${BADGE}:8`, `${APP_CSS}:60`]);
    });

    it('exports a chart colour and a proposal with their own layers, a proposal without live preview', () => {
        const chart = only(exportOf([CHART]));
        expect(chart).toMatchObject({layer: 'chart-color', preview: true, granularity: 'value'});
        expect(chart.occurrences.map((o) => [o.line, o.raw, o.layer, o.theme_context])).toEqual([
            [120, '#10b981', 'chart-color', 'light'],
            [121, 'rgba(16, 185, 129, 0.2)', 'chart-color', 'dark'],
        ]);
        const proposal = only(exportOf([PROPOSAL]));
        expect(proposal).toMatchObject({layer: 'proposal', preview: false, granularity: 'value'});
        expect(proposal.occurrences).toEqual([{file: OFFLINE, line: 10, col: 25, raw: '#0f172a', layer: 'static', theme_context: null, snippet: ''}]);
    });

    it('exports a specialisation with its property, its anchor, and the anchor’s candidates as occurrences', () => {
        expect(only(exportOf([ELEMENT]))).toEqual({
            id: `element:color@light~${TH}`,
            layer: 'element',
            scope: 'light',
            preview: true,
            target: TH,
            from: 'rgb(100, 116, 139)',
            to: '#dc2626',
            property: 'color',
            anchor: ANCHOR,
            occurrences: [
                {file: DATA_TABLE, line: 1607, raw: '#64748b', why: 'matched-rule'},
                {file: TX_TABLE, line: 993, raw: 'tx-table', why: 'testid'},
            ],
            shots: ['transactions/table'],
        });
        const chart = only(exportOf([ELEMENT_CHART]));
        expect(chart).toMatchObject({property: 'chart', color_key: '#10b981', anchor: CHART_ANCHOR, occurrences: [{file: GROWTH, line: 120, raw: '#10b981', why: 'literal'}]});
        expect(only(exportOf([{...ELEMENT, anchor: undefined}])).occurrences).toEqual([]);
    });

    it('carries the anchor of a change of another layer as context, and nothing when there is none', () => {
        expect(only(exportOf([{...LIT, anchor: ANCHOR}])).anchor).toEqual(ANCHOR);
        const plain = only(exportOf([LIT]));
        expect('anchor' in plain || 'note' in plain || 'shots' in plain).toBe(false);
        expect('shots' in only(exportOf([{...LIT, shots: []}]))).toBe(false);
    });
});

describe('buildExport — a colour role, used through the inline aliases of `@theme inline`', () => {
    const ROLE = '--lf-surface-card';
    const TOKENS = 'src/lib/theme/tokens.css';
    const alias = (name: string, role: string, line: number) => ({name, defs: [{file: 7, name, value: `var(${role})`, line, zone: 'css-file' as const, selector: null, theme: 'both' as const, scope: 'scoped' as const, inline: true, alias_of: role}], uses: 0, files: {}, use_sites: []});
    // The files of every catalogue of this file, plus 7: the stylesheet of the roles.
    const roles = catalogOf({
        files: [...CATALOG.files, TOKENS],
        css_vars: [
            ...CATALOG.css_vars,
            alias('--color-lf-card', ROLE, 160),
            alias('--color-lf-muted', '--lf-text-muted', 161),
            alias('--color-lf-surface', ROLE, 162),
            {
                name: ROLE,
                defs: [
                    {file: 7, name: ROLE, value: '#f5f5f4', line: 35, zone: 'css-file', selector: ':root, html.light, .light', theme: 'both', scope: 'root'},
                    {file: 7, name: ROLE, value: '#1c1917', line: 110, zone: 'css-file', selector: 'html.dark, .dark', theme: 'dark', scope: 'root'},
                ],
                uses: 2,
                files: {'0': 1, '7': 1},
                use_sites: [
                    [0, 80, '.panel'],
                    [7, 75, ':root, .light, .dark'],
                ],
            },
        ],
        palette: [
            ...CATALOG.palette,
            {
                var: '--color-lf-card',
                role: ROLE,
                uses: 3,
                dark: 0,
                classes: {'bg-lf-card': 2, 'hover:border-lf-card/50': 1},
                files: {'5': 1, '6': 2},
                occ: [
                    [6, 30, 0],
                    [5, 12, 1],
                    [6, 31, 0],
                ],
            },
            {var: '--color-lf-muted', role: '--lf-text-muted', uses: 1, dark: 0, classes: {'text-lf-muted': 1}, files: {'1': 1}, occ: [[1, 5, 0]]},
            {var: '--color-lf-surface', role: ROLE, uses: 1, dark: 0, classes: {'bg-lf-surface': 1}, files: {'6': 1}, occ: [[6, 40, 0]]},
        ],
    });
    const ROLE_CHANGE = make({layer: 'css-var', target: ROLE, scope: 'both', from: '#f5f5f4', to: '#ffffff'});
    const exportOn = (changes: LabChange[]) => buildExport(stateOf(changes), roles, APP, [], NOW);

    it('exports the role with the classes of every alias standing for it, each occurrence with the class written there', () => {
        expect(only(exportOn([ROLE_CHANGE]))).toEqual({
            id: 'css-var:--lf-surface-card@both',
            layer: 'css-var',
            scope: 'both',
            preview: true,
            target: ROLE,
            from: '#f5f5f4',
            to: '#ffffff',
            // 4 class uses + 2 `var()` reads, in 4 files: TransactionsTable and Badge for the classes, app.css and the
            // stylesheet of the roles for the reads. `text-lf-muted` stands for another role.
            impact: {uses: 6, files: 4, classes: {'bg-lf-card': 2, 'hover:border-lf-card/50': 1, 'bg-lf-surface': 1}},
            // The class at each place is `Object.keys(classes)[classIndex]` of its alias.
            occurrences: [
                {file: TX_TABLE, line: 30, raw: 'bg-lf-card'},
                {file: BADGE, line: 12, raw: 'hover:border-lf-card/50'},
                {file: TX_TABLE, line: 31, raw: 'bg-lf-card'},
                {file: TX_TABLE, line: 40, raw: 'bg-lf-surface'},
            ],
            // The role's own definitions, never the aliases'.
            definitions: [
                {file: TOKENS, line: 35, selector: ':root, html.light, .light', theme: 'both', value: '#f5f5f4'},
                {file: TOKENS, line: 110, selector: 'html.dark, .dark', theme: 'dark', value: '#1c1917'},
            ],
        });
    });

    it('still exports the occurrences of a palette variable by place alone, with no `raw`', () => {
        const gray = only(exportOn([VAR]));
        expect(gray.impact).toEqual({uses: 4, files: 3, classes: {'text-gray-500': 2, 'dark:bg-gray-500': 1}});
        expect(gray.occurrences).toEqual([
            {file: DATA_TABLE, line: 10},
            {file: DATA_TABLE, line: 20},
            {file: BADGE, line: 4},
        ]);
        expect(gray.occurrences.filter((o) => 'raw' in o)).toEqual([]);
    });
});

describe('renderMarkdown', () => {
    const lines = (md: string) => md.split('\n');

    it('writes a specialisation with its element, its selector and a table of where to bind the new variable', () => {
        const md = lines(renderMarkdown(exportOf([ELEMENT]), 'en'));
        expect(md[0]).toBe('# Designer Lab — changes (1)');
        const at = md.indexOf(`## element · \`${TH}\` · color · light`);
        expect(at).toBeGreaterThan(0);
        expect(md.slice(at + 2, at + 7)).toEqual([
            '- `rgb(100, 116, 139)` → `#dc2626`',
            '- element: `/transactions` · light · `th` · `tx-table` ‹ `tx-page`',
            `- selector: \`${TH}\` (component, 12 elements on the page)`,
            '- source: rule-literal · `th`',
            '- css_path: `[data-testid="tx-table"] > div > table > thead > tr > th:nth-of-type(2)`',
        ]);
        const table = md.indexOf('Where to bind the new variable:');
        expect(table).toBeGreaterThan(at);
        expect(md.slice(table + 2, table + 6)).toEqual(['| File | Line | Expected text | Why |', '|---|---:|---|---|', `| \`${DATA_TABLE}\` | 1607 | \`#64748b\` | matched-rule |`, `| \`${TX_TABLE}\` | 993 | \`tx-table\` | testid |`]);
    });

    it('writes the headings in Italian by default and when asked', () => {
        const doc = exportOf([ELEMENT, PROPOSAL]);
        const md = lines(renderMarkdown(doc));
        expect(renderMarkdown(doc, 'it')).toBe(renderMarkdown(doc));
        expect(md[0]).toBe('# Designer Lab — modifiche (2)');
        expect(md).toContain('- elemento: `/transactions` · light · `th` · `tx-table` ‹ `tx-page`');
        expect(md).toContain(`- selettore: \`${TH}\` (component, 12 elementi nella pagina)`);
        expect(md).toContain('- sorgente: rule-literal · `th`');
        expect(md).toContain('Dove legare la nuova variabile:');
        expect(md).toContain('| File | Riga | Testo atteso | Perché |');
        expect(md).toContain('- `#0f172a` → `#111827` (proposta, senza anteprima)');
        expect(md).toContain('| File | Riga | Valore | Selettore / proprietà |');
    });

    it('writes a stylesheet colour with its reach, and a variable with its impact and definitions', () => {
        const md = lines(renderMarkdown(exportOf([LIT, MUTED]), 'en'));
        expect(md).toContain('- reach: value, translucent variants included');
        expect(md).toContain(`| \`${DATA_TABLE}\` | 1607 | \`#64748b\` | \`th\` color |`);
        expect(md).toContain(`| \`${BADGE}\` | 8 | \`#64748b\` |  |`);
        expect(md).toContain('- impact: 4 uses, 2 file');
        expect(md).toContain(`- \`${APP_CSS}:160\` \`html.dark\` = \`#94a3b8\``);
    });

    it('escapes the pipes and new lines that would break a table row', () => {
        const piped: LabAnchor = {...ANCHOR, candidates: [{file: DATA_TABLE, line: 5, why: 'literal', needle: 'grid|cell\nnext'}]};
        expect(renderMarkdown(exportOf([{...ELEMENT, anchor: piped}]), 'en')).toContain(`| \`${DATA_TABLE}\` | 5 | \`grid\\|cell next\` | literal |`);
        const catalog = catalogOf({literals: [literal(0, {selector: '[lang|=en] th', property: 'color'})]});
        const md = renderMarkdown(buildExport(stateOf([LIT]), catalog, APP, [], NOW), 'en');
        expect(md).toContain('| `src/app.css` | 1 | `#64748b` | `[lang\\|=en] th` color |');
    });

    it('lists forty occurrences and counts the rest, which stay in the JSON', () => {
        const many = catalogOf({literals: Array.from({length: 45}, (_, i) => literal(i, {line: i + 1, selector: '.x', property: 'color'}))});
        const doc = buildExport(stateOf([LIT]), many, APP, [], NOW);
        expect(doc.changes[0].occurrences).toHaveLength(45);
        const md = lines(renderMarkdown(doc, 'en'));
        expect(md.filter((l) => l.startsWith('| `src/app.css` |'))).toHaveLength(40);
        expect(md).toContain('… 5 more in the JSON');
        expect(renderMarkdown(doc, 'it')).toContain('… 5 altre nel JSON');
    });

    it('adds the notes, the author and the contrast table', () => {
        const contrast: ContrastRow[] = [{fg: '--theme-text-muted', bg: '--theme-bg-card', scope: 'dark', before: 4.5, after: 6.789}];
        const md = lines(renderMarkdown(exportOf([], {notes: 'calmer greys', author: 'designer'}, contrast), 'en'));
        expect(md).toContain('- author: designer');
        expect(md.slice(md.indexOf('## Notes'), md.indexOf('## Notes') + 3)).toEqual(['## Notes', '', 'calmer greys']);
        expect(md).toContain('| `--theme-text-muted` | `--theme-bg-card` | dark | 4.50 | 6.79 |');
    });
});

describe('renderSummary', () => {
    it('gives one line per change, a specialisation with its property and candidates, after a header with the short hash', () => {
        const summary = renderSummary(exportOf([VAR, ELEMENT, ELEMENT_CHART, {...PROPOSAL, from: ''}], {notes: 'calmer greys'})).split('\n');
        expect(summary).toEqual([
            `Designer Lab · ${APP} · 4 changes · sha256:0123456789ab`,
            '- [css-var/both] --color-gray-500: oklch(55.1% 0.027 264.364) → #475569 (3 occ.) — darker body text',
            `- [element/light] ${TH} {color}: rgb(100, 116, 139) → #dc2626 (2 cand.)`,
            '- [element/dark] [data-testid="growth-chart"] {chart #10b981}: #10b981 → #f59e0b (1 cand.)',
            '- [proposal/both] #0f172a: — → #111827 (1 occ.)',
            '',
            'calmer greys',
        ]);
    });
});

describe('parseImport', () => {
    const json = (doc: unknown) => JSON.stringify(doc);

    it('reads back every layer exactly as the Lab stored it', () => {
        const changes = [VAR, MUTED, LIT, OCC, CHART, PROPOSAL, ELEMENT, ELEMENT_CHART, {...LIT, scope: 'dark' as const, id: changeId({...LIT, scope: 'dark'}), anchor: ANCHOR}];
        const state = stateOf(changes, {notes: 'calmer greys', author: 'designer', variants: {A: [VAR]}});
        const result = parseImport(json(buildExport(state, CATALOG, APP, [], NOW)), emptyState(), CATALOG);
        expect(result.errors).toEqual([]);
        expect(result.warnings).toEqual([]);
        expect(result.state?.changes).toEqual(changes);
        expect(result.state).toMatchObject({schema: 'lf-designer-lab-state/1', notes: 'calmer greys', author: 'designer', variants: {A: [VAR]}});
    });

    it('keeps the base state where the export says nothing', () => {
        const base = {...emptyState(), notes: 'mine', author: 'me', cvd: 'tritanopia' as const, variants: {B: [LIT]}};
        const doc: Partial<LabExport> = {schema: 'lf-designer-lab/1', changes: []};
        expect(parseImport(json(doc), base, CATALOG).state).toMatchObject({notes: 'mine', author: 'me', cvd: 'tritanopia', variants: {B: [LIT]}, changes: []});
    });

    it.each([
        ['text that is not JSON', '{"schema":', 'not JSON'],
        ['another schema', JSON.stringify({schema: 'lf-designer-lab/0', changes: []}), 'schema is not lf-designer-lab/1'],
        ['no list of changes', JSON.stringify({schema: 'lf-designer-lab/1'}), 'changes missing'],
    ])('refuses %s', (_label, text, error) => {
        expect(parseImport(text, emptyState(), CATALOG)).toEqual({state: null, errors: [error], warnings: []});
    });

    it('drops a change it cannot apply safely and keeps the others', () => {
        const doc = exportOf([VAR, CHART]);
        const good = doc.changes[1];
        const bad = [{...good, to: 'red; background: url(x)'}, {...good, to: 'red /* x */'}, {...good, layer: 'gradient'}, {...good, scope: 'auto'}, {...good, target: 42}, null];
        const result = parseImport(json({...doc, changes: [...bad, good]}), emptyState(), CATALOG);
        expect(result.errors).toEqual(bad.map((_, i) => `change ${i}: invalid`));
        expect(result.state?.changes).toEqual([CHART]);
    });

    it.each([
        ['a block in the selector', {target: `${TH} { color: red }`}],
        ['a semicolon in the selector', {target: `${TH};`}],
        ['a new line in the selector', {target: `${TH}\ntd`}],
        ['a comment in the selector', {target: `${TH} /* x */`}],
        ['a property it does not specialise', {property: 'box-shadow'}],
        ['no property', {property: undefined}],
        ['a chart colour without its key', {property: 'chart', color_key: undefined}],
        ['a chart colour key that is not a key', {property: 'chart', color_key: 'red'}],
        ['a chart colour key in capitals', {property: 'chart', color_key: '#10B981'}],
    ])('refuses a specialisation with %s', (_label, patch) => {
        const doc = exportOf([ELEMENT]);
        const result = parseImport(json({...doc, changes: [{...doc.changes[0], ...patch}]}), emptyState(), CATALOG);
        expect(result.errors).toEqual(['change 0: invalid specialisation']);
        expect(result.state?.changes).toEqual([]);
    });

    it('accepts a chart colour outside sRGB by its OKLCH key', () => {
        const doc = exportOf([{...ELEMENT_CHART, colorKey: 'oklch(0.596 0.145 163.2)'}]);
        expect(parseImport(json(doc), emptyState(), CATALOG).state?.changes[0]).toMatchObject({property: 'chart', colorKey: 'oklch(0.596 0.145 163.2)'});
    });

    it('drops an anchor it cannot read, with a warning, and keeps the change', () => {
        const doc = exportOf([CHART]);
        const result = parseImport(json({...doc, changes: [{...doc.changes[0], anchor: {route: 42}}]}), emptyState(), CATALOG);
        expect(result.errors).toEqual([]);
        expect(result.warnings).toEqual(['change 0: anchor not readable, dropped']);
        expect(result.state?.changes[0]).toEqual(CHART);
    });

    it('finds a single stylesheet occurrence again by file, line and value in a catalogue whose ids moved', () => {
        // The new catalogue has one more literal in front: the occurrence of id 0 is id 1 there.
        const moved = catalogOf({literals: [literal(0, {file: 0, line: 2, raw: '#ffffff', key: '#ffffff'}), ...LITERALS.map((l) => ({...l, id: l.id + 1}))]});
        const result = parseImport(json(exportOf([OCC])), emptyState(), moved);
        expect(result.errors).toEqual([]);
        expect(result.state?.changes[0]).toMatchObject({occurrence: 1, match: {selector: 'th', property: 'color'}, id: 'css-literal:#64748b@both#1'});
    });

    it('applies an occurrence it cannot find to the whole colour, and says so', () => {
        const doc = exportOf([OCC]);
        const lost = {...doc.changes[0], occurrences: [{...doc.changes[0].occurrences[0], line: 9999}]};
        const result = parseImport(json({...doc, changes: [lost]}), emptyState(), CATALOG);
        expect(result.warnings).toEqual([`change 0: occurrence ${DATA_TABLE}:9999 not found, applied to every occurrence of #64748b`]);
        const change = result.state?.changes[0];
        expect(change?.occurrence).toBeUndefined();
        expect(change?.match).toBeUndefined();
        expect(change?.id).toBe('css-literal:#64748b@both');
    });

    it('binds an occurrence only for a stylesheet colour', () => {
        const doc = exportOf([CHART]);
        const single = {...doc.changes[0], granularity: 'occurrence', occurrences: [doc.changes[0].occurrences[0]]};
        const result = parseImport(json({...doc, changes: [single]}), emptyState(), CATALOG);
        expect(result.warnings).toEqual([]);
        expect(result.state?.changes[0]).toEqual(CHART);
    });

    it('keeps one change per id: a repeated change replaces the earlier one where it stood, and says so', () => {
        const doc = exportOf([CHART, VAR]);
        const again = {...doc.changes[0], to: '#2563eb'};
        const result = parseImport(json({...doc, changes: [...doc.changes, again]}), emptyState(), CATALOG);
        expect(result.errors).toEqual([]);
        expect(result.warnings).toEqual([`change 2: repeats ${CHART.id}, the later one is kept`]);
        expect(result.state?.changes).toEqual([{...CHART, to: '#2563eb'}, VAR]);
    });

    it('counts as a repeat an occurrence that falls back to its whole colour', () => {
        const doc = exportOf([LIT, OCC]);
        const lost = {...doc.changes[1], occurrences: [{...doc.changes[1].occurrences[0], line: 9999}]};
        const result = parseImport(json({...doc, changes: [doc.changes[0], lost]}), emptyState(), CATALOG);
        expect(result.warnings).toEqual([`change 1: occurrence ${DATA_TABLE}:9999 not found, applied to every occurrence of #64748b`, 'change 1: repeats css-literal:#64748b@both, the later one is kept']);
        expect(result.state?.changes).toHaveLength(1);
        expect(result.state?.changes[0]).toMatchObject({id: 'css-literal:#64748b@both', to: '#334155'});
    });

    it('warns when the export was made on another catalogue, and not when it carries no hash', () => {
        const doc = exportOf([VAR]);
        const other = parseImport(json({...doc, catalog_hash: 'sha256:ffff'}), emptyState(), CATALOG);
        expect(other.warnings).toHaveLength(1);
        expect(other.warnings[0]).toMatch(/^catalog_hash differs/);
        expect(other.state?.changes).toEqual([VAR]);
        expect(parseImport(json({...doc, catalog_hash: undefined}), emptyState(), CATALOG).warnings).toEqual([]);
    });
});

describe('buildExport and parseImport — a chart category, edited by key', () => {
    const CATEGORIES_TS = 'src/lib/theme/chartCategories.ts';
    /** A line of the category tables (file 7): a chart colour with its category and the theme of its property. */
    const tableLine = (id: number, line: number, raw: string, theme: 'light' | 'dark', category: string): CatalogLiteral => literal(id, {file: 7, line, col: 16, raw, key: raw.toLowerCase(), zone: 'ts', theme, layer: 'chart-color', chart: true, snippet: `${theme}: '${raw}',`, category});
    // `type:AAA` and `sector:Zed Sector` share their light value, and a chart elsewhere writes it too: a category change
    // must name the category's own lines, never the other places of its value.
    const CATEGORY_LITERALS = [
        tableLine(12, 40, '#2B4C7E', 'light', 'type:AAA'),
        tableLine(13, 41, '#7EA6E0', 'dark', 'type:AAA'),
        tableLine(14, 80, '#2B4C7E', 'light', 'sector:Zed Sector'),
        tableLine(15, 81, '#334455', 'dark', 'sector:Zed Sector'),
        tableLine(16, 90, '#5A6B7C', 'light', 'bucket:Nowhere'),
        literal(17, {file: 2, line: 130, col: 30, raw: '#2b4c7e', key: '#2b4c7e', zone: 'svelte-script', theme: 'light', layer: 'chart-color', chart: true}),
    ];
    const WITH_CATEGORIES = catalogOf({
        files: [APP_CSS, DATA_TABLE, GROWTH, COLORS_TS, OFFLINE, BADGE, TX_TABLE, CATEGORIES_TS],
        literals: [...LITERALS, ...CATEGORY_LITERALS],
        categories: [
            {target: 'type:AAA', kind: 'type', key: 'AAA', light: 12, dark: 13},
            {target: 'sector:Zed Sector', kind: 'sector', key: 'Zed Sector', light: 14, dark: 15},
            // A table without a dark value for it.
            {target: 'bucket:Nowhere', kind: 'bucket', key: 'Nowhere', light: 16, dark: null},
        ],
    });
    const aaa = (scope: LabChange['scope']) => make({layer: 'category', target: 'type:AAA', scope, from: '#2B4C7E', to: '#123456'});
    const AAA = aaa('both');
    const exportWith = (catalog: ColorCatalog, changes: LabChange[]) => buildExport(stateOf(changes), catalog, APP, [], NOW);
    const json = (doc: unknown) => JSON.stringify(doc);
    const occurrence = (line: number, raw: string, theme: 'light' | 'dark') => ({file: CATEGORIES_TS, line, col: 16, raw, layer: 'chart-color', theme_context: theme, snippet: `${theme}: '${raw}',`});

    it('exports the category with its kind and key, and as occurrences its own line in each theme of the change', () => {
        expect(only(exportWith(WITH_CATEGORIES, [aaa('light')]))).toEqual({
            id: 'category:type:AAA@light',
            layer: 'category',
            scope: 'light',
            preview: true,
            target: 'type:AAA',
            from: '#2B4C7E',
            to: '#123456',
            category: {kind: 'type', key: 'AAA'},
            occurrences: [occurrence(40, '#2B4C7E', 'light')],
        });
        expect(only(exportWith(WITH_CATEGORIES, [aaa('dark')])).occurrences).toEqual([occurrence(41, '#7EA6E0', 'dark')]);
        const both = only(exportWith(WITH_CATEGORIES, [AAA]));
        expect(both.occurrences).toEqual([occurrence(40, '#2B4C7E', 'light'), occurrence(41, '#7EA6E0', 'dark')]);
        // By key: neither the dark-only reach nor the value-wide reach of a literal layer.
        expect('granularity' in both).toBe(false);
        expect('alpha_variants' in both).toBe(false);
    });

    it('exports a key written with spaces as its table writes it, and a theme its table leaves empty with no occurrence', () => {
        const zed = only(exportWith(WITH_CATEGORIES, [make({layer: 'category', target: 'sector:Zed Sector', scope: 'both', from: '#2B4C7E', to: '#123456'})]));
        expect(zed.category).toEqual({kind: 'sector', key: 'Zed Sector'});
        expect(zed.occurrences).toEqual([occurrence(80, '#2B4C7E', 'light'), occurrence(81, '#334455', 'dark')]);
        const nowhere = make({layer: 'category', target: 'bucket:Nowhere', scope: 'dark', from: '', to: '#123456'});
        expect(only(exportWith(WITH_CATEGORIES, [nowhere])).occurrences).toEqual([]);
        expect(only(exportWith(WITH_CATEGORIES, [{...nowhere, scope: 'both'}])).occurrences).toEqual([occurrence(90, '#5A6B7C', 'light')]);
    });

    it('exports a category its catalogue does not know with no occurrence and no category, a catalogue without categories included', () => {
        const ghost = only(exportWith(WITH_CATEGORIES, [make({layer: 'category', target: 'type:Ghost', scope: 'both', from: '', to: '#123456'})]));
        expect(ghost.occurrences).toEqual([]);
        expect('category' in ghost).toBe(false);
        const older = only(exportWith(CATALOG, [AAA]));
        expect(older.occurrences).toEqual([]);
        expect('category' in older).toBe(false);
    });

    it('reads a category change back as the Lab stored it, without translucent variants', () => {
        const changes = [AAA, make({layer: 'category', target: 'sector:Zed Sector', scope: 'dark', from: '#334455', to: '#654321', note: 'calmer'}), make({layer: 'category', target: 'bucket:Nowhere', scope: 'light', from: '#5A6B7C', to: '#abcdef'})];
        const doc = exportWith(WITH_CATEGORIES, changes);
        // An export written by hand may carry the field of the literal layers: it is not read for a category.
        const result = parseImport(json({...doc, changes: doc.changes.map((c) => ({...c, alpha_variants: false}))}), emptyState(), WITH_CATEGORIES);
        expect(result.errors).toEqual([]);
        expect(result.warnings).toEqual([]);
        expect(result.state?.changes).toEqual(changes);
        expect(result.state?.changes[0].id).toBe('category:type:AAA@both');
        expect(result.state?.changes.filter((c) => 'alphaVariants' in c)).toEqual([]);
    });

    it('refuses a category its catalogue does not know, and keeps the other changes', () => {
        const doc = exportWith(WITH_CATEGORIES, [AAA]);
        const result = parseImport(json({...doc, changes: [{...doc.changes[0], target: 'type:Ghost'}, doc.changes[0]]}), emptyState(), WITH_CATEGORIES);
        expect(result.errors).toEqual(['change 0: unknown category type:Ghost']);
        expect(result.state?.changes).toEqual([AAA]);
    });

    it.each([
        ['markup in the key', 'type:<script>'],
        ['a kind the tables do not have', 'region:Europe'],
        ['no key', 'sector:'],
        ['a key longer than sixty characters', `sector:${'x'.repeat(61)}`],
        ['a colour instead of a category', '#2b4c7e'],
    ])('refuses a category target with %s, whatever the catalogue', (_label, target) => {
        const doc = exportWith(WITH_CATEGORIES, [AAA]);
        for (const catalog of [WITH_CATEGORIES, CATALOG]) {
            const result = parseImport(json({...doc, changes: [{...doc.changes[0], target}]}), emptyState(), catalog);
            expect(result.errors).toEqual([`change 0: unknown category ${target.slice(0, 80)}`]);
            expect(result.state?.changes).toEqual([]);
        }
    });

    it('imports an asset type or the cash edited as a category before DV-11 as a change of its role, with a warning', () => {
        const doc = exportWith(WITH_CATEGORIES, [AAA]);
        const legacy = [
            {...doc.changes[0], target: 'type:REAL_ESTATE', scope: 'light', from: '#96602C', to: '#123456'},
            {...doc.changes[0], target: 'bucket:Liquidity', scope: 'both', from: '', to: '#654321'},
        ];
        const result = parseImport(json({...doc, changes: legacy}), emptyState(), WITH_CATEGORIES);
        expect(result.errors).toEqual([]);
        expect(result.warnings).toEqual(['change 0: type:REAL_ESTATE is the role --lf-cat-real-estate since DV-11, imported as a change of that variable', 'change 1: bucket:Liquidity is the role --lf-cat-liquidity since DV-11, imported as a change of that variable']);
        expect(result.state?.changes.map((c) => [c.id, c.layer, c.target, c.scope, c.from, c.to])).toEqual([
            ['css-var:--lf-cat-real-estate@light', 'css-var', '--lf-cat-real-estate', 'light', '#96602C', '#123456'],
            ['css-var:--lf-cat-liquidity@both', 'css-var', '--lf-cat-liquidity', 'both', '', '#654321'],
        ]);
    });

    it('accepts any well-formed category from a catalogue built before the categories, which has no list to check', () => {
        const doc = exportWith(WITH_CATEGORIES, [AAA]);
        const result = parseImport(json({...doc, changes: [{...doc.changes[0], target: 'type:Ghost'}]}), emptyState(), CATALOG);
        expect(result.errors).toEqual([]);
        expect(result.state?.changes).toEqual([{...AAA, target: 'type:Ghost', id: 'category:type:Ghost@both'}]);
    });
});

describe('sanitizeAnchor', () => {
    const anchor = (patch: Record<string, unknown>) => sanitizeAnchor({...ANCHOR, ...patch});

    it('keeps an anchor the Lab wrote as it is', () => {
        expect(sanitizeAnchor(JSON.parse(JSON.stringify(ANCHOR)))).toEqual(ANCHOR);
    });

    it.each([
        ['nothing', null],
        ['a string', 'th'],
        ['no route', {...ANCHOR, route: undefined}],
        ['a route that is not text', {...ANCHOR, route: 42}],
        ['a route over 300 characters', {...ANCHOR, route: `/${'a'.repeat(300)}`}],
        ['a route on two lines', {...ANCHOR, route: '/transactions\n/x'}],
        ['no selector', {...ANCHOR, selector: ''}],
        ['a selector with a block', {...ANCHOR, selector: 'th { color: red }'}],
        ['a selector with a semicolon', {...ANCHOR, selector: 'th;'}],
        ['a selector with a comment', {...ANCHOR, selector: 'th /* x */'}],
        ['a property in capitals', {...ANCHOR, property: 'Color'}],
        ['a property with a semicolon', {...ANCHOR, property: 'color;'}],
        ['no element', {...ANCHOR, element: undefined}],
        ['a tag in capitals', {...ANCHOR, element: {...ANCHOR.element, tag: 'TH'}}],
        ['a tag that starts with a digit', {...ANCHOR, element: {...ANCHOR.element, tag: '1th'}}],
        ['a tag with a combinator', {...ANCHOR, element: {...ANCHOR.element, tag: 'th>td'}}],
    ])('is null for %s', (_label, raw) => {
        expect(sanitizeAnchor(raw)).toBeNull();
    });

    it('brings the enumerations back to what the Lab knows', () => {
        expect(anchor({theme: 'auto', breadth: 'page', source: {...ANCHOR.source, kind: 'magic'}})).toMatchObject({theme: 'light', breadth: 'component', source: {kind: 'unknown'}});
        expect(anchor({theme: 'dark', breadth: 'element'})).toMatchObject({theme: 'dark', breadth: 'element'});
        for (const matches of [-1, 1.5, '12', null]) expect(anchor({matches})?.matches).toBe(0);
    });

    it('drops the texts that are too long or on more than one line', () => {
        const a = anchor({
            css_path: `body > ${'div > '.repeat(120)}th`,
            computed: `rgb(${'1 '.repeat(160)})`,
            testids: ['tx-table', 'x'.repeat(201), 'a\nb', 42, 'tx-page'],
            element: {tag: 'th', classes: ['sorted', 'c'.repeat(201), 'two\nlines'], scope_class: `svelte-${'a'.repeat(60)}`},
            source: {kind: 'var', selector: 's'.repeat(601), var: '--theme-text-muted', class: 'k'.repeat(201)},
        });
        expect(a).toMatchObject({css_path: '', computed: '', testids: ['tx-table', 'tx-page'], element: {tag: 'th', classes: ['sorted'], scope_class: null}, source: {kind: 'var', selector: null, var: '--theme-text-muted', class: null}});
    });

    it('keeps a source variable only when it is a custom property name', () => {
        expect(anchor({source: {...ANCHOR.source, var: 'color'}})?.source.var).toBeNull();
        expect(anchor({source: {...ANCHOR.source, var: '--x;y'}})?.source.var).toBeNull();
        expect(anchor({source: {...ANCHOR.source, var: '--theme-text-muted'}})?.source.var).toBe('--theme-text-muted');
    });

    it('keeps only well-formed candidates, from the first twenty', () => {
        const good = ANCHOR.candidates[0];
        const candidates = [good, {...good, file: undefined}, {...good, line: 0}, {...good, line: 1.5}, {...good, why: 'guess'}, {...good, needle: 'a\nb'}, {...good, needle: 'n'.repeat(201)}, null, 'src/app.css:1', {...good, line: 2}];
        expect(anchor({candidates})?.candidates).toEqual([good, {...good, line: 2}]);
        const many = Array.from({length: 25}, (_, i) => ({...good, line: i + 1}));
        expect(anchor({candidates: many})?.candidates.map((c) => c.line)).toEqual(many.slice(0, 20).map((c) => c.line));
        expect(anchor({candidates: 'all'})?.candidates).toEqual([]);
    });

    it('caps the test ids at eight and the classes at forty', () => {
        const a = anchor({testids: Array.from({length: 12}, (_, i) => `id-${i}`), element: {tag: 'th', classes: Array.from({length: 50}, (_, i) => `c${i}`), scope_class: null}});
        expect(a?.testids).toEqual(Array.from({length: 8}, (_, i) => `id-${i}`));
        expect(a?.element.classes).toHaveLength(40);
    });
});

describe('isoWithOffset', () => {
    it('writes the local time with the local offset, as people read dates', () => {
        const d = new Date(2026, 9, 20, 15, 2, 11);
        const offset = vi.spyOn(d, 'getTimezoneOffset');
        offset.mockReturnValue(-120);
        expect(isoWithOffset(d)).toBe('2026-10-20T15:02:11+02:00');
        offset.mockReturnValue(-330);
        expect(isoWithOffset(d)).toBe('2026-10-20T15:02:11+05:30');
        offset.mockReturnValue(570);
        expect(isoWithOffset(d)).toBe('2026-10-20T15:02:11-09:30');
        offset.mockReturnValue(0);
        expect(isoWithOffset(d)).toBe('2026-10-20T15:02:11+00:00');
    });

    it('names the same instant in the time zone the tests run in', () => {
        const d = new Date(2026, 0, 2, 3, 4, 5);
        expect(isoWithOffset(d)).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$/);
        expect(new Date(isoWithOffset(d)).getTime()).toBe(d.getTime());
    });
});
