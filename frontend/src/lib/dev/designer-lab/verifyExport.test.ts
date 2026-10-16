/**
 * Designer Lab — `verify-export.mjs`: an export checked against the code as it is now.
 *
 * Every occurrence must still be written at its `file:line`; else it is looked for in the file (`moved`, with the
 * nearest line) or reported `missing`. A specialisation's candidates are checked the same way and counted apart: a
 * candidate that moved or disappeared is a hint, and only a specialisation left with none is `lost` — the one case,
 * with a missing occurrence, where the CLI exits 1. The test ids of an anchor must still be written in the code.
 * A chart category is the exception to the search by value (`locateCategory`): categories share values, so its line is
 * the one its key and theme are written at in the tables, and a line holding another value is `missing`.
 * An export is input: a path leaving the frontend is never read.
 *
 * The frontend is a synthetic tree in a temporary directory, and the catalogue hash and test-id index are passed as
 * options, so no scan of the real tree runs. The CLI cases spawn the script on the same tree, which it scans itself.
 */

import {afterAll, beforeAll, describe, expect, it} from 'vitest';
import {spawnSync} from 'node:child_process';
import {mkdirSync, mkdtempSync, rmSync, writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CATEGORY_FILE, scanColors} from '../../../../scripts/designer-lab/scan-colors.mjs';
import {locate, locateCategory, testidKnown, verifyExport, VERIFY_SCHEMA} from '../../../../scripts/designer-lab/verify-export.mjs';
import {buildExport} from './export';
import {changeId, emptyState} from './store';
import type {ColorCatalog, LabChange} from './types';

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), '../../../..');
const SCRIPT = join(FRONTEND, 'scripts/designer-lab/verify-export.mjs');

const HASH = 'sha256:1111111111111111111111111111111111111111111111111111111111111111';
const INDEX = {statics: ['tx-table', 'tx-row'], prefixes: ['filter-currency-row-', 'row-']};

const DATA_TABLE = 'src/lib/components/table/DataTable.svelte';
const TX_TABLE = 'src/lib/features/transactions/TransactionsTable.svelte';
const APP_CSS = 'src/app.css';
const CARD = 'src/lib/components/ui/Card.svelte';
const TOKENS = 'src/lib/theme/tokens.css';
const TH = '[data-testid="tx-table"] > div > table > thead > tr > th';

/** The synthetic frontend: one line per entry, so every line number can be read off the array. */
const TREE: Record<string, string[]> = {
    [DATA_TABLE]: ['<script lang="ts">', '    let {rows} = $props();', '</script>', '', '<table class="text-gray-500">', '</table>', '', '<style>', '    th {', '        color: #64748b;', '    }', '    td {', '        border-color: #E2E8F0;', '    }', '</style>'],
    [APP_CSS]: [':root, html.light {', '    --theme-text-muted: #6b7280;', '    --theme-bg-card: #ffffff;', '}', 'html.dark {', '    --theme-text-muted: #94a3b8;', '}'],
    [TX_TABLE]: ['<div data-testid="tx-table">', '    <Row testid="tx-row" />', '</div>'],
    // A colour role: its classes name the alias of `@theme inline` (`bg-lf-card`), never the role itself.
    [CARD]: ['<div class="rounded-lg bg-lf-card">', '    <slot />', '</div>', '<p class="hover:border-lf-card/50">x</p>'],
    [TOKENS]: [':root,', 'html.light,', '.light {', '    --lf-surface-card: #f5f5f4;', '}', 'html.dark,', '.dark {', '    --lf-surface-card: #1c1917;', '}', '@theme inline {', '    --color-lf-card: var(--lf-surface-card);', '}'],
};

interface OccurrenceReport {
    file: string;
    line: number;
    raw?: string;
    to_line?: number;
}

interface ChangeReport {
    id: string;
    layer: string;
    target: string;
    ok: number;
    moved: OccurrenceReport[];
    missing: OccurrenceReport[];
    definitions: {file: string; line: number; status: string; to_line?: number; value_now?: string}[];
    anchor?: {status: 'ok' | 'testid-missing' | 'no-candidates' | 'lost'; testids_missing: string[]};
}

interface Report {
    schema: string;
    exported_with: string | null;
    catalog_hash_now: string;
    catalog_hash_match: boolean;
    totals: Record<'changes' | 'ok' | 'moved' | 'missing' | 'definitions_changed' | 'candidates_ok' | 'candidates_moved' | 'candidates_missing' | 'anchors_lost' | 'anchor_testids_missing', number>;
    changes: ChangeReport[];
}

let base: string;
let root: string;

beforeAll(() => {
    base = mkdtempSync(join(tmpdir(), 'lf-designer-lab-verify-'));
    root = join(base, 'frontend');
    for (const [rel, lines] of Object.entries(TREE)) {
        mkdirSync(dirname(join(root, rel)), {recursive: true});
        writeFileSync(join(root, rel), lines.join('\n'));
    }
    // Outside the frontend, each with the needle on line 1: reading them would find it.
    writeFileSync(join(base, 'outside.txt'), '#64748b tx-table\n');
    mkdirSync(join(base, 'frontend-evil', 'src'), {recursive: true});
    writeFileSync(join(base, 'frontend-evil', 'src', 'x.svelte'), '#64748b tx-table\n');
});

afterAll(() => {
    rmSync(base, {recursive: true, force: true});
});

const exportOf = (changes: unknown[], catalog_hash = HASH) => ({schema: 'lf-designer-lab/1', app_version: 'test', catalog_hash, exported_at: '2026-10-14T21:00:00+02:00', author: '', notes: '', changes, contrast: [], variants: {}});

const verify = (doc: unknown, testids = INDEX): Report => verifyExport(doc, {root, catalogHash: HASH, testids}) as unknown as Report;

const only = (report: Report): ChangeReport => {
    expect(report.changes).toHaveLength(1);
    return report.changes[0];
};

/** A stylesheet colour exported by value. */
const literalChange = (occurrences: object[], extra: object = {}) => ({id: 'css-literal:#64748b@both', layer: 'css-literal', scope: 'both', preview: true, target: '#64748b', from: '#64748b', to: '#475569', granularity: 'value', alpha_variants: true, occurrences, ...extra});

const anchor = (testids: unknown[], candidates: object[] = []) => ({
    route: '/transactions',
    theme: 'light',
    testids,
    css_path: `${TH}:nth-of-type(2)`,
    element: {tag: 'th', classes: [], scope_class: null},
    selector: TH,
    breadth: 'component',
    matches: 12,
    property: 'color',
    computed: 'rgb(100, 116, 139)',
    source: {kind: 'rule-literal', selector: 'th', var: null, class: null},
    candidates,
});

/** A specialisation: its occurrences are the anchor's candidates, `raw` the text expected there. */
const elementChange = (candidates: {file: string; line: number; raw: string; why: string}[], testids: unknown[] = ['tx-table']) => ({
    id: `element:color@light~${TH}`,
    layer: 'element',
    scope: 'light',
    preview: true,
    target: TH,
    from: 'rgb(100, 116, 139)',
    to: '#dc2626',
    property: 'color',
    anchor: anchor(
        testids,
        candidates.map((c) => ({file: c.file, line: c.line, why: c.why, needle: c.raw})),
    ),
    occurrences: candidates,
});

describe('locate', () => {
    const lines = ['a', 'color: #64748b;', 'b', 'COLOR: #64748B;'];

    it('finds the text at its line, ignoring case', () => {
        expect(locate(lines, 2, '#64748b')).toEqual({status: 'ok', line: 2});
        expect(locate(lines, 4, '#64748b')).toEqual({status: 'ok', line: 4});
    });

    it('reports the nearest other line when the text moved, the upper one on a tie, a line past the end included', () => {
        expect(locate(lines, 1, '#64748b')).toEqual({status: 'moved', line: 2});
        expect(locate(lines, 3, '#64748b')).toEqual({status: 'moved', line: 2});
        expect(locate(lines, 99, '#64748b')).toEqual({status: 'moved', line: 4});
    });

    it('reports a text written nowhere in the file as missing', () => {
        expect(locate(lines, 2, '#ffffff')).toEqual({status: 'missing'});
        expect(locate([], 1, '#64748b')).toEqual({status: 'missing'});
    });
});

describe('verifyExport — occurrences', () => {
    it('checks every occurrence at its line, then elsewhere in its file', () => {
        const report = verify(
            exportOf([
                literalChange([
                    {file: DATA_TABLE, line: 10, raw: '#64748b'},
                    {file: DATA_TABLE, line: 5, raw: '#64748b'},
                    {file: DATA_TABLE, line: 13, raw: '#e2e8f0'},
                    {file: DATA_TABLE, line: 20, raw: '#123456'},
                    {file: 'src/lib/components/Gone.svelte', line: 1, raw: '#64748b'},
                ]),
            ]),
        );
        const c = only(report);
        expect(c).toMatchObject({id: 'css-literal:#64748b@both', layer: 'css-literal', target: '#64748b', ok: 2});
        expect(c.moved).toEqual([{file: DATA_TABLE, line: 5, raw: '#64748b', to_line: 10}]);
        expect(c.missing).toEqual([
            {file: DATA_TABLE, line: 20, raw: '#123456'},
            {file: 'src/lib/components/Gone.svelte', line: 1, raw: '#64748b'},
        ]);
        expect(report.totals).toMatchObject({changes: 1, ok: 2, moved: 1, missing: 2, candidates_ok: 0, candidates_moved: 0, candidates_missing: 0, anchors_lost: 0});
        expect('anchor' in c).toBe(false);
    });

    it('looks for a palette use by its family and shade, written without a value', () => {
        const report = verify(exportOf([{id: 'css-var:--color-gray-500@both', layer: 'css-var', scope: 'both', target: '--color-gray-500', from: '', to: '#475569', occurrences: [{file: DATA_TABLE, line: 5}]}]));
        expect(only(report)).toMatchObject({ok: 1, moved: [], missing: []});
    });

    it('looks for a class that reads a role through its inline alias by the class the occurrence carries', () => {
        const change = {
            id: 'css-var:--lf-surface-card@both',
            layer: 'css-var',
            scope: 'both',
            target: '--lf-surface-card',
            from: '#f5f5f4',
            to: '#ffffff',
            occurrences: [
                {file: CARD, line: 1, raw: 'bg-lf-card'},
                {file: CARD, line: 4, raw: 'hover:border-lf-card/50'},
                {file: CARD, line: 2, raw: 'bg-lf-card'},
                {file: CARD, line: 3, raw: 'bg-lf-panel'},
            ],
            definitions: [
                {file: TOKENS, line: 4, selector: ':root, html.light, .light', theme: 'both', value: '#f5f5f4'},
                {file: TOKENS, line: 8, selector: 'html.dark, .dark', theme: 'dark', value: '#1c1917'},
            ],
        };
        const report = verify(exportOf([change]));
        const c = only(report);
        // In place where the line holds the class; else found elsewhere in the file, or nowhere (a class renamed).
        expect(c).toMatchObject({layer: 'css-var', target: '--lf-surface-card', ok: 2});
        expect(c.moved).toEqual([{file: CARD, line: 2, raw: 'bg-lf-card', to_line: 1}]);
        expect(c.missing).toEqual([{file: CARD, line: 3, raw: 'bg-lf-panel'}]);
        // The definitions are the role's own.
        expect(c.definitions).toEqual([
            {file: TOKENS, line: 4, status: 'ok'},
            {file: TOKENS, line: 8, status: 'ok'},
        ]);
        expect(report.totals).toMatchObject({changes: 1, ok: 2, moved: 1, missing: 1, definitions_changed: 0});
    });

    it('checks the definitions of a variable and reports the value it has now', () => {
        const change = {
            id: 'css-var:--theme-text-muted@both',
            layer: 'css-var',
            scope: 'both',
            target: '--theme-text-muted',
            from: '#6b7280',
            to: '#4b5563',
            occurrences: [],
            definitions: [
                {file: APP_CSS, line: 2, selector: ':root, html.light', theme: 'both', value: '#6b7280'},
                {file: APP_CSS, line: 6, selector: 'html.dark', theme: 'dark', value: '#cbd5e1'},
                {file: APP_CSS, line: 9, selector: 'html.dark', theme: 'dark', value: '#94a3b8'},
                {file: 'src/lib/theme/gone.css', line: 1, selector: ':root', theme: 'both', value: '#000000'},
            ],
        };
        const report = verify(exportOf([change]));
        expect(only(report).definitions).toEqual([
            {file: APP_CSS, line: 2, status: 'ok'},
            {file: APP_CSS, line: 6, status: 'ok', value_now: '#94a3b8'},
            {file: APP_CSS, line: 9, status: 'moved', to_line: 6},
            {file: 'src/lib/theme/gone.css', line: 1, status: 'missing'},
        ]);
        expect(report.totals.definitions_changed).toBe(1);
    });

    it('never reads a path that leaves the frontend, even where the text would be found', () => {
        const report = verify(
            exportOf([
                literalChange([
                    {file: '../outside.txt', line: 1, raw: '#64748b'},
                    {file: '../frontend-evil/src/x.svelte', line: 1, raw: '#64748b'},
                    {file: '../frontend/src/../../outside.txt', line: 1, raw: '#64748b'},
                    {file: join(base, 'outside.txt'), line: 1, raw: '#64748b'},
                ]),
            ]),
        );
        expect(only(report)).toMatchObject({ok: 0, moved: []});
        expect(only(report).missing).toHaveLength(4);
    });

    it('compares the catalogue the export was made on with the catalogue now', () => {
        expect(verify(exportOf([]))).toMatchObject({schema: VERIFY_SCHEMA, exported_with: HASH, catalog_hash_now: HASH, catalog_hash_match: true});
        expect(verify(exportOf([], 'sha256:other'))).toMatchObject({exported_with: 'sha256:other', catalog_hash_match: false});
        const {catalog_hash: _hash, ...unhashed} = exportOf([]);
        expect(verify(unhashed)).toMatchObject({exported_with: null, catalog_hash_match: false});
    });

    it('refuses what is not an export', () => {
        expect(() => verify({schema: 'lf-designer-lab/0', changes: []})).toThrow('not a lf-designer-lab/1 export');
        expect(() => verify({schema: 'lf-designer-lab/1'})).toThrow('not a lf-designer-lab/1 export');
        expect(() => verify(null)).toThrow('not a lf-designer-lab/1 export');
    });
});

/**
 * The tables of a synthetic `chartCategories.ts`, made-up keys and values, one entry per line as in the real file. As
 * there (`ETF` and `Technology`), a type and a sector share a value — `type:AAA` and `sector:Zed` both write `SHARED` in
 * the light theme — so a category is found by key and theme, never by value. `bucket:Unknown` writes one value in both
 * themes. Line numbers in the comments are 1-based.
 */
const SHARED = '#2B4C7E';
const CATEGORY_TABLES = [
    'const ASSET_TYPE_COLORS: Readonly<Record<string, ThemePair>> = {', // 1
    '    // first family',
    '    AAA: {',
    `        light: '${SHARED}',`, // 4
    "        dark: '#7EA6E0',", // 5
    '    },',
    '};',
    '',
    'const SECTOR_COLORS: Readonly<Record<string, ThemePair>> = {', // 9
    '    Zed: {',
    `        light: '${SHARED}',`, // 11
    "        dark: '#334455',", // 12
    '    },',
    '};',
    '',
    'const UNCLASSIFIED_COLOR: ThemePair = {', // 16
    "    light: '#5A6B7C',", // 17
    "    dark: '#5A6B7C',", // 18
    '};',
];

/** The tables with line `n` (1-based) written as `text`. */
const withLine = (n: number, text: string) => CATEGORY_TABLES.map((l, i) => (i === n - 1 ? text : l));

describe('locateCategory', () => {
    const light = (line: number, raw?: string) => ({line, raw, theme_context: 'light'});
    const dark = (line: number, raw?: string) => ({line, raw, theme_context: 'dark'});

    it('is ok at the line its key and theme are written at, the value compared without its case', () => {
        expect(locateCategory(CATEGORY_TABLES, light(4, SHARED), 'type:AAA')).toEqual({status: 'ok', line: 4});
        expect(locateCategory(CATEGORY_TABLES, dark(5, '#7ea6e0'), 'type:AAA')).toEqual({status: 'ok', line: 5});
        expect(locateCategory(CATEGORY_TABLES, light(11, SHARED), 'sector:Zed')).toEqual({status: 'ok', line: 11});
        expect(locateCategory(CATEGORY_TABLES, dark(18, '#5A6B7C'), 'bucket:Unknown')).toEqual({status: 'ok', line: 18});
    });

    it('moves to the line of its own key and theme, never to another category or theme writing the value', () => {
        // Line 4 writes the value of the sector's light line, line 18 the value of the bucket's dark line: neither is theirs.
        expect(locateCategory(CATEGORY_TABLES, light(4, SHARED), 'sector:Zed')).toEqual({status: 'moved', line: 11});
        expect(locateCategory(CATEGORY_TABLES, light(11, SHARED), 'type:AAA')).toEqual({status: 'moved', line: 4});
        expect(locateCategory(CATEGORY_TABLES, light(18, '#5A6B7C'), 'bucket:Unknown')).toEqual({status: 'moved', line: 17});
        expect(locateCategory(CATEGORY_TABLES, dark(17, '#5A6B7C'), 'bucket:Unknown')).toEqual({status: 'moved', line: 18});
    });

    it('is missing when its line holds another value, even where another category still writes it', () => {
        expect(locateCategory(withLine(4, "        light: '#111111',"), light(4, SHARED), 'type:AAA')).toEqual({status: 'missing'});
        expect(locateCategory(withLine(17, "    light: '#111111',"), light(17, '#5A6B7C'), 'bucket:Unknown')).toEqual({status: 'missing'});
    });

    it('is missing when the tables do not write its key, its kind or its theme', () => {
        expect(locateCategory(CATEGORY_TABLES, light(4, SHARED), 'type:Gone')).toEqual({status: 'missing'});
        expect(locateCategory(CATEGORY_TABLES, light(4, SHARED), 'sector:AAA')).toEqual({status: 'missing'});
        // The key is compared as the table writes it: a renamed key is another key.
        expect(locateCategory(withLine(3, '    AAB: {'), light(4, SHARED), 'type:AAA')).toEqual({status: 'missing'});
        // The bucket without a dark line: its light line, which writes the same value, is not the dark one.
        expect(locateCategory(withLine(18, ''), dark(18, '#5A6B7C'), 'bucket:Unknown')).toEqual({status: 'missing'});
        // An occurrence whose theme is not one the tables write cannot be placed.
        expect(locateCategory(CATEGORY_TABLES, {line: 4, raw: SHARED, theme_context: null}, 'type:AAA')).toEqual({status: 'missing'});
        expect(locateCategory(CATEGORY_TABLES, {line: 4, raw: SHARED, theme_context: 'both'}, 'type:AAA')).toEqual({status: 'missing'});
    });

    it('tells the two kinds apart when both tables write the same key', () => {
        const twoKinds = ['const ASSET_TYPE_COLORS = {', '    Same: {', "        light: '#0D0D0D',", '    },', '};', 'const SECTOR_COLORS = {', '    Same: {', "        light: '#0D0D0D',", '    },', '};'];
        expect(locateCategory(twoKinds, light(3, '#0D0D0D'), 'type:Same')).toEqual({status: 'ok', line: 3});
        expect(locateCategory(twoKinds, light(3, '#0D0D0D'), 'sector:Same')).toEqual({status: 'moved', line: 8});
    });

    it('places an occurrence that carries no value by its key and theme alone', () => {
        expect(locateCategory(CATEGORY_TABLES, light(4), 'type:AAA')).toEqual({status: 'ok', line: 4});
        expect(locateCategory(withLine(5, "        dark: '#111111',"), dark(1), 'type:AAA')).toEqual({status: 'moved', line: 5});
    });
});

describe('verifyExport — a chart category, found by key and theme on its line', () => {
    let trees = 0;

    /**
     * A tree holding the tables, and the export the Lab writes there for `targets` (both themes each), from the catalogue
     * of the tree as it was. `after` rewrites the tables, then checks the export against them.
     */
    function exported(...targets: string[]) {
        const root = join(base, `frontend-categories-${++trees}`);
        const file = join(root, CATEGORY_FILE);
        mkdirSync(dirname(file), {recursive: true});
        writeFileSync(file, CATEGORY_TABLES.join('\n'));
        const catalog = scanColors({root}) as unknown as ColorCatalog;
        const changes = targets.map((target): LabChange => {
            const fields = {layer: 'category' as const, target, scope: 'both' as const, from: '', to: '#123456'};
            return {...fields, id: changeId(fields)};
        });
        const doc = buildExport({...emptyState(), changes}, catalog, 'test');
        const after = (lines: string[]): Report => {
            writeFileSync(file, lines.join('\n'));
            return verifyExport(doc, {root, catalogHash: catalog.meta.hash, testids: INDEX}) as unknown as Report;
        };
        return {doc, after};
    }

    const at = (line: number, raw: string) => ({file: CATEGORY_FILE, line, raw});

    it('exports each theme of a category at its own line, with that theme, and finds them all in place', () => {
        const {doc, after} = exported('type:AAA', 'sector:Zed', 'bucket:Unknown');
        // The premise of every case below: the export carries the line and the theme of each occurrence.
        expect(doc.changes.map((c) => c.occurrences.map((o) => [o.file, o.line, o.raw, o.theme_context]))).toEqual([
            [
                [CATEGORY_FILE, 4, SHARED, 'light'],
                [CATEGORY_FILE, 5, '#7EA6E0', 'dark'],
            ],
            [
                [CATEGORY_FILE, 11, SHARED, 'light'],
                [CATEGORY_FILE, 12, '#334455', 'dark'],
            ],
            [
                [CATEGORY_FILE, 17, '#5A6B7C', 'light'],
                [CATEGORY_FILE, 18, '#5A6B7C', 'dark'],
            ],
        ]);
        const report = after(CATEGORY_TABLES);
        expect(report.changes.map((c) => [c.id, c.layer, c.target, c.ok, c.moved.length, c.missing.length])).toEqual([
            ['category:type:AAA@both', 'category', 'type:AAA', 2, 0, 0],
            ['category:sector:Zed@both', 'category', 'sector:Zed', 2, 0, 0],
            ['category:bucket:Unknown@both', 'category', 'bucket:Unknown', 2, 0, 0],
        ]);
        expect(report.totals).toMatchObject({changes: 3, ok: 6, moved: 0, missing: 0});
    });

    it('reports a value changed at its line as missing, though another category still writes the old value', () => {
        // The type's light value changed; the sector's light line, 11, still writes the old one.
        const {after} = exported('type:AAA');
        const changed = withLine(4, "        light: '#111111',");
        expect(locate(changed, 4, SHARED), 'the control: a search by value takes the sector’s line for it').toEqual({status: 'moved', line: 11});
        const c = only(after(changed));
        expect(c).toMatchObject({ok: 1, moved: [], missing: [at(4, SHARED)]});
    });

    it('follows lines moved down to where their key and theme are written now, never to a nearer line writing the value', () => {
        // Twenty lines between the tables: the sector's lines move from 11–12 to 31–32, while line 4 — the type's, which
        // writes the sector's light value — is nearer to 11 than 31 is.
        const {after} = exported('sector:Zed');
        const grown = [...CATEGORY_TABLES.slice(0, 8), ...Array.from({length: 20}, (_, i) => `// added ${i + 1}`), ...CATEGORY_TABLES.slice(8)];
        expect(locate(grown, 11, SHARED), 'the control: a search by value lands on the type’s line').toEqual({status: 'moved', line: 4});
        const c = only(after(grown));
        expect(c).toMatchObject({ok: 0, missing: []});
        expect(c.moved).toEqual([
            {...at(11, SHARED), to_line: 31},
            {...at(12, '#334455'), to_line: 32},
        ]);
    });

    it('follows a family added above, and reports a dark value changed since the export as missing', () => {
        const {after} = exported('type:AAA');
        const added = only(after([...CATEGORY_TABLES.slice(0, 2), '    NEW: {', "        light: '#0E0E0E',", '    },', ...CATEGORY_TABLES.slice(2)]));
        expect(added).toMatchObject({ok: 0, missing: []});
        expect(added.moved).toEqual([
            {...at(4, SHARED), to_line: 7},
            {...at(5, '#7EA6E0'), to_line: 8},
        ]);
        expect(only(after(withLine(5, "        dark: '#0F0F0F',")))).toMatchObject({ok: 1, moved: [], missing: [at(5, '#7EA6E0')]});
    });

    it('never takes the other theme’s line of the same key, though it writes the same value', () => {
        const {after} = exported('bucket:Unknown');
        // The two themes written in the other order: each occurrence moves to its own theme's line.
        const swappedLines = withLine(17, "    dark: '#5A6B7C',").map((l, i) => (i === 17 ? "    light: '#5A6B7C'," : l));
        expect(locate(swappedLines, 17, '#5A6B7C'), 'the control: a search by value finds the dark line in place').toEqual({status: 'ok', line: 17});
        const swapped = only(after(swappedLines));
        expect(swapped).toMatchObject({ok: 0, missing: []});
        expect(swapped.moved).toEqual([
            {...at(17, '#5A6B7C'), to_line: 18},
            {...at(18, '#5A6B7C'), to_line: 17},
        ]);
        // No light line any more: the light occurrence is missing, though the dark line, now 17, writes its value.
        const darkOnly = only(after(CATEGORY_TABLES.filter((_, i) => i !== 16)));
        expect(darkOnly).toMatchObject({ok: 0, missing: [at(17, '#5A6B7C')]});
        expect(darkOnly.moved).toEqual([{...at(18, '#5A6B7C'), to_line: 17}]);
    });

    it('reports a category whose key was renamed or removed as missing in both themes', () => {
        const {after} = exported('sector:Zed');
        // Renamed: its values are still written on its old lines, under another key.
        const renamedLines = withLine(10, '    Zeta: {');
        expect([locate(renamedLines, 11, SHARED), locate(renamedLines, 12, '#334455')], 'the control: a search by value finds both in place').toEqual([
            {status: 'ok', line: 11},
            {status: 'ok', line: 12},
        ]);
        const renamed = only(after(renamedLines));
        expect(renamed).toMatchObject({ok: 0, moved: [], missing: [at(11, SHARED), at(12, '#334455')]});
        // Removed: the entry's four lines are gone.
        const removed = only(after([...CATEGORY_TABLES.slice(0, 9), ...CATEGORY_TABLES.slice(13)]));
        expect(removed).toMatchObject({ok: 0, moved: [], missing: [at(11, SHARED), at(12, '#334455')]});
        expect(after(CATEGORY_TABLES).totals).toMatchObject({ok: 2, moved: 0, missing: 0});
    });
});

describe('verifyExport — specialisations', () => {
    it('counts the candidates apart from the occurrences', () => {
        const report = verify(
            exportOf([
                literalChange([
                    {file: DATA_TABLE, line: 10, raw: '#64748b'},
                    {file: DATA_TABLE, line: 20, raw: '#123456'},
                ]),
                elementChange([
                    {file: DATA_TABLE, line: 10, raw: '#64748b', why: 'matched-rule'},
                    {file: TX_TABLE, line: 5, raw: 'tx-table', why: 'testid'},
                    {file: DATA_TABLE, line: 30, raw: 'gone-needle', why: 'literal'},
                ]),
            ]),
        );
        expect(report.totals).toMatchObject({changes: 2, ok: 1, moved: 0, missing: 1, candidates_ok: 1, candidates_moved: 1, candidates_missing: 1, anchors_lost: 0, anchor_testids_missing: 0});
        const element = report.changes[1];
        expect(element.moved).toEqual([{file: TX_TABLE, line: 5, raw: 'tx-table', to_line: 1}]);
        expect(element.missing).toEqual([{file: DATA_TABLE, line: 30, raw: 'gone-needle'}]);
        expect(element.anchor).toEqual({status: 'ok', testids_missing: []});
    });

    it('accepts the test ids the code still writes: static, `prefix*`, or an id a prefix produces', () => {
        const ok = [{file: DATA_TABLE, line: 10, raw: '#64748b', why: 'matched-rule'}];
        expect(only(verify(exportOf([elementChange(ok, ['tx-table', 'row-*', 'filter-currency-row-EUR', 42])]))).anchor).toEqual({status: 'ok', testids_missing: []});
    });

    it('warns about a test id the code no longer writes, without failing', () => {
        const report = verify(exportOf([elementChange([{file: DATA_TABLE, line: 10, raw: '#64748b', why: 'matched-rule'}], ['tx-table', 'renamed-id', 'tab-*'])]));
        expect(only(report).anchor).toEqual({status: 'testid-missing', testids_missing: ['renamed-id', 'tab-*']});
        expect(report.totals).toMatchObject({anchor_testids_missing: 2, anchors_lost: 0, missing: 0});
    });

    it('tells a specialisation that listed no candidate from one that lost them all', () => {
        const none = verify(exportOf([elementChange([])]));
        expect(only(none).anchor?.status).toBe('no-candidates');
        expect(none.totals.anchors_lost).toBe(0);

        const lost = verify(
            exportOf([
                elementChange([
                    {file: DATA_TABLE, line: 30, raw: 'gone-needle', why: 'literal'},
                    {file: '../outside.txt', line: 1, raw: 'tx-table', why: 'testid'},
                ]),
            ]),
        );
        expect(only(lost).anchor?.status).toBe('lost');
        expect(lost.totals).toMatchObject({anchors_lost: 1, candidates_missing: 2, missing: 0});
    });

    it('checks the anchor of a change of another layer for its test ids only', () => {
        const report = verify(exportOf([literalChange([{file: DATA_TABLE, line: 20, raw: '#123456'}], {anchor: anchor(['renamed-id'])})]));
        expect(only(report).anchor).toEqual({status: 'testid-missing', testids_missing: ['renamed-id']});
        expect(report.totals).toMatchObject({missing: 1, anchors_lost: 0});
    });
});

describe('testidKnown', () => {
    const index = {statics: new Set(['tx-table']), prefixes: ['row-']};

    it('knows a static id, a templated id written `prefix*`, and an id a prefix produces', () => {
        expect(testidKnown('tx-table', index)).toBe(true);
        expect(testidKnown('row-*', index)).toBe(true);
        expect(testidKnown('row-42', index)).toBe(true);
    });

    it('knows a `prefix*` the picker cut from an id the index did not know: one that extends a known prefix, or starts a static id', () => {
        expect(testidKnown('row-total-*', index)).toBe(true);
        expect(testidKnown('tx-*', index)).toBe(true);
    });

    it('does not know an id the code does not write, nor a prefix written alone', () => {
        expect(testidKnown('tab-*', index)).toBe(false);
        // Shorter than the known prefix, and no static id starts with it.
        expect(testidKnown('ro-*', index)).toBe(false);
        expect(testidKnown('renamed-id', index)).toBe(false);
        expect(testidKnown('row-', index)).toBe(false);
        // An empty prefix, which every id would start with: a hand-edited export, never one the Lab writes.
        expect(testidKnown('*', index)).toBe(false);
    });
});

describe('verify-export CLI', () => {
    let exports = 0;

    /** Run the script as an agent would, on the synthetic tree, which it scans itself. */
    function cli(doc: unknown, ...flags: string[]) {
        const file = join(base, `export-${++exports}.json`);
        writeFileSync(file, typeof doc === 'string' ? doc : JSON.stringify(doc));
        const run = spawnSync(process.execPath, [SCRIPT, file, '--root', root, ...flags], {encoding: 'utf8', timeout: 60_000});
        return {status: run.status, stdout: run.stdout, stderr: run.stderr};
    }

    const inPlace = {file: DATA_TABLE, line: 10, raw: '#64748b', why: 'matched-rule'};
    const gone = {file: DATA_TABLE, line: 30, raw: 'gone-needle', why: 'literal'};

    it('exits 0 when nothing is missing, a moved candidate and a renamed test id included', {timeout: 60_000}, () => {
        const run = cli(exportOf([elementChange([inPlace, {file: TX_TABLE, line: 5, raw: 'tx-table', why: 'testid'}], ['tx-table', 'renamed-id'])]));
        expect(run.status, run.stderr).toBe(0);
    });

    it('exits 1 when a specialisation lost every candidate, and when an occurrence is missing', {timeout: 60_000}, () => {
        expect(cli(exportOf([elementChange([gone])])).status).toBe(1);
        expect(cli(exportOf([literalChange([{file: DATA_TABLE, line: 20, raw: '#123456'}])])).status).toBe(1);
    });

    it('exits 2 on input that is not an export, and prints the report as JSON when asked', {timeout: 60_000}, () => {
        expect(cli('{"schema": "lf-designer-lab/1"').status).toBe(2);
        expect(cli({schema: 'other', changes: []}).status).toBe(2);

        const run = cli(exportOf([elementChange([inPlace])]), '--json');
        expect(run.status, run.stderr).toBe(0);
        const report = JSON.parse(run.stdout) as Report;
        expect(report.schema).toBe(VERIFY_SCHEMA);
        // The CLI scanned the synthetic tree: both test ids written there are known.
        expect(only(report).anchor).toEqual({status: 'ok', testids_missing: []});
        expect(report.catalog_hash_match).toBe(false);
    });
});
