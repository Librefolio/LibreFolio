/**
 * Designer Lab — what the Lab page lists, derived from the catalogue (`catalogView.ts`).
 *
 * Pure functions over a synthetic catalogue: grouping and ordering of the palette, the variables that hold a colour,
 * the hand-written colours grouped by value, the search filter, and the value a variable has in a theme before and
 * after the changes; for the colour roles, the inline aliases of `@theme inline` (`--color-lf-card`), the role each
 * stands for (`--lf-surface-card`, the variable the Lab edits), and what editing a variable reaches in the code.
 * Every expectation follows from the few entries written below, never from the real tree.
 */

import {describe, expect, it} from 'vitest';
import {appVars, categoryRows, changedVarValue, editTarget, isInlineAlias, matchesSearch, paletteFamilies, sourceCategoryValue, sourceVarValue, valueGroups, varImpact} from './catalogView';
import type {CatalogLiteral, CatalogPaletteEntry, CatalogVar, CatalogVarDef, ColorCatalog, LabChange} from './types';

function catalogOf(parts: Partial<ColorCatalog>): ColorCatalog {
    return {
        meta: {schema: 'lf-color-catalog/1', app_version: 'test', generated_at: '2026-10-14T18:00:00.000Z', hash: 'sha256:test', scan_ms: 0, parity: {}, layers: {}, excluded: []},
        files: ['src/app.css', 'src/lib/components/table/DataTable.svelte', 'src/lib/components/charts/GrowthChart.svelte'],
        css_vars: [],
        palette: [],
        literals: [],
        by_value: {},
        testids: {},
        testid_prefixes: [],
        ...parts,
    };
}

const paletteEntry = (name: string, uses: number): CatalogPaletteEntry => ({var: name, uses, dark: 0, classes: {}, files: {}, occ: []});

const def = (name: string, value: string, fields: Partial<CatalogVarDef> = {}): CatalogVarDef => ({file: 0, name, value, line: 1, zone: 'css-file', selector: ':root', theme: 'both', scope: 'root', ...fields});

const cssVar = (name: string, defs: CatalogVarDef[]): CatalogVar => ({name, defs, uses: 0, files: {}, use_sites: []});

function literal(id: number, fields: Partial<CatalogLiteral>): CatalogLiteral {
    return {id, file: 0, line: id + 1, col: 1, raw: '#000000', kind: 'hex', key: '#000000', alpha: 1, zone: 'css-file', theme: 'both', layer: 'css-literal', preview: true, snippet: '', ...fields};
}

const varChange = (target: string, scope: LabChange['scope'], to: string, layer: LabChange['layer'] = 'css-var'): LabChange => ({id: `${layer}:${target}@${scope}`, layer, target, scope, from: '', to});

/** A definition of `@theme inline`, as the scanner writes it: `aliasOf` the variable named when the value is only `var()`. */
const aliasDef = (name: string, value: string, aliasOf: string | null): CatalogVarDef => def(name, value, {selector: null, scope: 'scoped', inline: true, alias_of: aliasOf});

/** A palette entry with its class uses (`uses` is their sum, as in the scanner) and, for an inline alias, its role. */
function usedEntry(name: string, classes: Record<string, number>, files: Record<string, number>, role?: string): CatalogPaletteEntry {
    return {var: name, uses: Object.values(classes).reduce((n, c) => n + c, 0), dark: 0, classes, files, occ: [], ...(role ? {role} : {})};
}

describe('paletteFamilies', () => {
    // In catalogue order (by variable name), as the scanner writes it.
    const catalog = catalogOf({
        palette: [
            paletteEntry('--color-emerald-100', 1),
            paletteEntry('--color-emerald-50', 2),
            paletteEntry('--color-emerald-600', 5),
            paletteEntry('--color-gray-500', 10),
            paletteEntry('--color-gray-950', 1),
            paletteEntry('--color-libre-green', 3),
            paletteEntry('--color-red-75', 4),
            paletteEntry('--color-white', 7),
        ],
    });

    it('groups the Tailwind palette by family, most used family first, and puts what has no shade last', () => {
        const families = paletteFamilies(catalog);
        // gray 11 uses, emerald 8; `other` holds 14 and still comes last.
        expect(families.map((f) => f.family)).toEqual(['gray', 'emerald', 'other']);
    });

    it('orders the shades of a family by the Tailwind scale, not as text', () => {
        const emerald = paletteFamilies(catalog).find((f) => f.family === 'emerald');
        // As text, '100' would sort before '50'.
        expect(emerald?.entries.map((e) => e.shade)).toEqual(['50', '100', '600']);
        expect(emerald?.entries.map((e) => e.uses)).toEqual([2, 1, 5]);
    });

    it('names an entry outside the scale by its variable, a shade that is not on the scale included', () => {
        const other = paletteFamilies(catalog).find((f) => f.family === 'other');
        expect(other?.entries.map((e) => [e.var, e.shade])).toEqual([
            ['--color-libre-green', 'libre-green'],
            ['--color-red-75', 'red-75'],
            ['--color-white', 'white'],
        ]);
    });

    it('groups the colour roles (`--color-lf-*`) as the family `lf`, each named by the rest of its variable, in alphabetical order', () => {
        const roles = catalogOf({
            palette: [
                paletteEntry('--color-gray-500', 10),
                {...paletteEntry('--color-lf-text-muted', 4), role: '--lf-text-muted'},
                {...paletteEntry('--color-lf-card', 5), role: '--lf-surface-card'},
                {...paletteEntry('--color-lf-action-hover', 3), role: '--lf-action-hover'},
                paletteEntry('--color-libre-green', 30),
            ],
        });
        const families = paletteFamilies(roles);
        // lf 12 uses, gray 10: the roles rank as a family, by their uses; `other` (30 uses) still comes last.
        expect(families.map((f) => f.family)).toEqual(['lf', 'gray', 'other']);
        const lf = families.find((f) => f.family === 'lf');
        expect(lf?.entries.map((e) => [e.var, e.shade])).toEqual([
            ['--color-lf-action-hover', 'action-hover'],
            ['--color-lf-card', 'card'],
            ['--color-lf-text-muted', 'text-muted'],
        ]);
        // The chip of an entry edits its role: the grouping keeps it.
        expect(lf?.entries.map((e) => editTarget(e))).toEqual(['--lf-action-hover', '--lf-surface-card', '--lf-text-muted']);
        expect(families.find((f) => f.family === 'other')?.entries.map((e) => e.var)).toEqual(['--color-libre-green']);
    });
});

describe('appVars', () => {
    it('keeps the variables with a colour definition — a value, a function, or a reference — in catalogue order', () => {
        const catalog = catalogOf({
            css_vars: [
                cssVar('--brand', [def('--brand', '#1a4031')]),
                cssVar('--font-sans', [def('--font-sans', 'Inter, sans-serif')]),
                cssVar('--mix', [def('--mix', 'color-mix(in srgb, #10b981 20%, transparent)')]),
                cssVar('--named', [def('--named', 'white')]),
                cssVar('--radius', [def('--radius', '4px')]),
                cssVar('--ring', [def('--ring', '0 0 0 2px rgb(37 99 235 / 50%)')]),
                cssVar('--theme-text', [def('--theme-text', 'var(--color-gray-900)')]),
                cssVar('--two', [def('--two', '1px'), def('--two', 'oklch(59.6% 0.145 163.225)', {theme: 'dark', selector: 'html.dark'})]),
                cssVar('--used-only', []),
            ],
        });
        expect(appVars(catalog).map((v) => v.name)).toEqual(['--brand', '--mix', '--named', '--ring', '--theme-text', '--two']);
    });

    it('leaves out the aliases of `@theme inline`, which no stylesheet defines at runtime, and keeps the roles they stand for', () => {
        const catalog = catalogOf({
            css_vars: [
                cssVar('--color-lf-card', [aliasDef('--color-lf-card', 'var(--lf-surface-card)', '--lf-surface-card')]),
                cssVar('--color-lf-overlay', [aliasDef('--color-lf-overlay', 'color-mix(in oklab, #0f1412 60%, transparent)', null)]),
                // Defined in `:root` too: a stylesheet defines it at runtime, so editing it changes the page.
                cssVar('--color-lf-shared', [def('--color-lf-shared', '#123456'), aliasDef('--color-lf-shared', 'var(--lf-surface-card)', '--lf-surface-card')]),
                cssVar('--lf-surface-card', [def('--lf-surface-card', '#f5f5f4', {selector: ':root, html.light, .light'}), def('--lf-surface-card', '#1c1917', {selector: 'html.dark, .dark', theme: 'dark'})]),
            ],
        });
        expect(appVars(catalog).map((v) => v.name)).toEqual(['--color-lf-shared', '--lf-surface-card']);
    });
});

describe('isInlineAlias', () => {
    it('is true when every definition of the variable is an alias of `@theme inline`, an expression included', () => {
        expect(isInlineAlias(cssVar('--color-lf-card', [aliasDef('--color-lf-card', 'var(--lf-surface-card)', '--lf-surface-card')]))).toBe(true);
        expect(isInlineAlias(cssVar('--color-lf-x', [aliasDef('--color-lf-x', 'var(--lf-a)', '--lf-a'), aliasDef('--color-lf-x', 'color-mix(in oklab, var(--lf-a) 50%, white)', null)]))).toBe(true);
    });

    it('is false for a variable without definitions, and for one a stylesheet defines as well or alone', () => {
        expect(isInlineAlias(cssVar('--color-lf-card', []))).toBe(false);
        expect(isInlineAlias(cssVar('--color-lf-x', [aliasDef('--color-lf-x', 'var(--lf-a)', '--lf-a'), def('--color-lf-x', '#123456')]))).toBe(false);
        expect(isInlineAlias(cssVar('--theme-text', [def('--theme-text', '#111827')]))).toBe(false);
    });
});

describe('editTarget', () => {
    it('edits the role an inline alias stands for, and any other entry by its own variable', () => {
        expect(editTarget({...paletteEntry('--color-lf-card', 3), role: '--lf-surface-card'})).toBe('--lf-surface-card');
        expect(editTarget(paletteEntry('--color-gray-500', 1))).toBe('--color-gray-500');
    });
});

describe('varImpact', () => {
    const ROLE = '--lf-surface-card';
    // Files: 0 app.css, 1 DataTable.svelte, 2 GrowthChart.svelte.
    const gray = usedEntry('--color-gray-500', {'text-gray-500': 3, 'border-gray-500': 1}, {'1': 1, '2': 3});
    const card = usedEntry('--color-lf-card', {'bg-lf-card': 2, 'hover:border-lf-card/50': 1}, {'1': 2, '2': 1}, ROLE);
    const muted = usedEntry('--color-lf-muted', {'text-lf-muted': 4}, {'1': 4}, '--lf-text-muted');
    const grayVar: CatalogVar = {...cssVar('--color-gray-500', []), uses: 1, files: {'0': 1}};
    const role: CatalogVar = {...cssVar(ROLE, [def(ROLE, '#f5f5f4', {selector: ':root, html.light, .light'}), def(ROLE, '#1c1917', {selector: 'html.dark, .dark', theme: 'dark'})]), uses: 2, files: {'0': 1, '1': 1}};
    const catalog = catalogOf({palette: [gray, card, muted], css_vars: [grayVar, role]});

    it('reaches the classes of the alias standing for a role, and the stylesheets that read the role with `var()`', () => {
        const impact = varImpact(catalog, ROLE);
        expect(impact.entries).toEqual([card]);
        expect(impact.variable).toBe(role);
        // 3 class uses + 2 reads; the classes in DataTable and GrowthChart, the reads in app.css and DataTable.
        expect([impact.uses, impact.files]).toEqual([5, 3]);
        expect(impact.classes).toEqual({'bg-lf-card': 2, 'hover:border-lf-card/50': 1});
    });

    it('adds up a class that two aliases of one role share, and counts each file once', () => {
        const surface = usedEntry('--color-lf-surface', {'bg-lf-card': 1, 'bg-lf-surface': 2}, {'2': 3}, ROLE);
        const impact = varImpact(catalogOf({palette: [gray, card, muted, surface], css_vars: [grayVar, role]}), ROLE);
        expect(impact.entries).toEqual([card, surface]);
        // 3 + 3 class uses + 2 reads, in the files {1, 2} ∪ {2} ∪ {0, 1}.
        expect([impact.uses, impact.files]).toEqual([8, 3]);
        expect(impact.classes).toEqual({'bg-lf-card': 3, 'hover:border-lf-card/50': 1, 'bg-lf-surface': 2});
    });

    it('reaches a palette variable through its own classes and its `var()` reads', () => {
        const impact = varImpact(catalog, '--color-gray-500');
        expect(impact.entries).toEqual([gray]);
        expect(impact.variable).toBe(grayVar);
        // 4 class uses + 1 read, in the files {1, 2} ∪ {0}.
        expect([impact.uses, impact.files]).toEqual([5, 3]);
        expect(impact.classes).toEqual({'text-gray-500': 3, 'border-gray-500': 1});
    });

    it('reaches nothing for a variable the catalogue does not know', () => {
        const impact = varImpact(catalog, '--lf-unknown');
        expect(impact).toEqual({entries: [], variable: undefined, uses: 0, files: 0, classes: {}});
        expect(impact.variable).toBeUndefined();
    });
});

describe('valueGroups', () => {
    const catalog = catalogOf({
        literals: [
            literal(0, {key: '#64748b', file: 0, alpha: 1, theme: 'both'}),
            literal(1, {key: '#64748b', raw: 'rgba(100, 116, 139, 0.5)', kind: 'fn', file: 1, alpha: 0.5, theme: 'dark'}),
            literal(2, {key: '#64748b', file: 1, alpha: 1, theme: null, zone: 'svelte-markup'}),
            literal(3, {key: '#10b981', layer: 'chart-color', zone: 'svelte-script', file: 2, alpha: 1, theme: null}),
            literal(4, {key: '#10b981', layer: 'chart-color', zone: 'svelte-script', file: 2, alpha: 0.2, theme: 'light'}),
            literal(5, {key: null, raw: 'color-mix(in srgb, #64748b 20%, transparent)', kind: 'mix', alpha: null}),
            literal(6, {key: '#0f172a', layer: 'static', zone: 'static', theme: null}),
            literal(7, {key: '#bbbbbb', file: 0}),
            literal(8, {key: '#aaaaaa', file: 0}),
        ],
    });

    it('groups the colours of the given layers by value, alpha variants together, most used first then by value', () => {
        const groups = valueGroups(catalog, ['css-literal']);
        expect(groups.map((g) => [g.key, g.literals.map((l) => l.id)])).toEqual([
            ['#64748b', [0, 1, 2]],
            ['#aaaaaa', [8]],
            ['#bbbbbb', [7]],
        ]);
    });

    it('counts the files of a group and lists its alphas (opaque first) and themes (`?` for none)', () => {
        const [gray] = valueGroups(catalog, ['css-literal']);
        expect(gray).toMatchObject({key: '#64748b', files: 2, alphas: [1, 0.5], themes: ['?', 'both', 'dark']});
        const [green] = valueGroups(catalog, ['chart-color']);
        expect(green).toMatchObject({key: '#10b981', files: 1, alphas: [1, 0.2], themes: ['?', 'light']});
    });

    it('leaves out expressions without a key and the layers not asked for', () => {
        expect(valueGroups(catalog, ['css-literal', 'chart-color']).map((g) => g.key)).toEqual(['#64748b', '#10b981', '#aaaaaa', '#bbbbbb']);
        expect(valueGroups(catalog, ['static']).map((g) => g.key)).toEqual(['#0f172a']);
        expect(valueGroups(catalog, [])).toEqual([]);
    });
});

describe('matchesSearch', () => {
    it('matches everything on an empty query', () => {
        expect(matchesSearch('', ['--color-gray-500'])).toBe(true);
        expect(matchesSearch('   ', [])).toBe(true);
    });

    it('matches a name, a value or a file, ignoring case and the spaces around the query', () => {
        expect(matchesSearch('GRAY', ['--color-gray-500'])).toBe(true);
        expect(matchesSearch('  datatable ', ['#64748b', 'src/lib/components/table/DataTable.svelte'])).toBe(true);
    });

    it('does not match when no text contains the query', () => {
        expect(matchesSearch('emerald', ['--color-gray-500', 'text-gray-500'])).toBe(false);
        expect(matchesSearch('gray', [])).toBe(false);
    });
});

describe('sourceVarValue', () => {
    // Definitions in source order, as the scanner lists them; `def` defaults to `:root`, shared by both themes.
    const catalog = catalogOf({
        css_vars: [
            cssVar('--both-only', [def('--both-only', '#123456')]),
            cssVar('--card-accent', [def('--card-accent', '#10b981', {selector: '.card', scope: 'scoped'})]),
            cssVar('--dark-only', [def('--dark-only', '#000000', {selector: 'html.dark', theme: 'dark'})]),
            cssVar('--dark-twice', [def('--dark-twice', '#555555', {selector: 'html.dark', theme: 'dark'}), def('--dark-twice', '#666666', {selector: 'html.dark', theme: 'dark', line: 40})]),
            cssVar('--light-before-root', [def('--light-before-root', '#222222', {selector: 'html:not(.dark)', theme: 'light'}), def('--light-before-root', '#111111', {line: 40})]),
            cssVar('--light-only', [def('--light-only', '#ffffff', {selector: 'html.light', theme: 'light'})]),
            cssVar('--light-over-root', [def('--light-over-root', '#111111'), def('--light-over-root', '#222222', {selector: 'html.light', theme: 'light', line: 40})]),
            cssVar('--shared-twice', [def('--shared-twice', '#333333'), def('--shared-twice', '#444444', {selector: 'html.light, html.dark', line: 40})]),
            cssVar('--theme-text-muted', [def('--theme-text-muted', '#6b7280', {selector: ':root, html.light'}), def('--theme-text-muted', '#94a3b8', {selector: 'html.dark', theme: 'dark'})]),
        ],
    });

    it('reads the light value from the root definition and the dark value from the dark one', () => {
        expect(sourceVarValue(catalog, '--theme-text-muted', false)).toBe('#6b7280');
        expect(sourceVarValue(catalog, '--theme-text-muted', true)).toBe('#94a3b8');
    });

    it('gives a variable defined once for both themes the same value in both', () => {
        expect(sourceVarValue(catalog, '--both-only', false)).toBe('#123456');
        expect(sourceVarValue(catalog, '--both-only', true)).toBe('#123456');
    });

    it('prefers the definition of the theme asked to one both themes share, wherever it stands', () => {
        // `html.light` after `:root`, and `html:not(.dark)` before it: the light rule is the light value either way.
        expect(sourceVarValue(catalog, '--light-over-root', false)).toBe('#222222');
        expect(sourceVarValue(catalog, '--light-before-root', false)).toBe('#222222');
        // In dark the light rule does not apply: the shared definition does.
        expect(sourceVarValue(catalog, '--light-over-root', true)).toBe('#111111');
        expect(sourceVarValue(catalog, '--light-before-root', true)).toBe('#111111');
    });

    it('never reads the other theme’s definition', () => {
        expect(sourceVarValue(catalog, '--light-only', false, 'fallback')).toBe('#ffffff');
        expect(sourceVarValue(catalog, '--light-only', true, 'fallback')).toBe('fallback');
        expect(sourceVarValue(catalog, '--dark-twice', false, 'fallback')).toBe('fallback');
    });

    it('takes the later of two definitions on equal footing, as the cascade does', () => {
        expect(sourceVarValue(catalog, '--shared-twice', false)).toBe('#444444');
        expect(sourceVarValue(catalog, '--shared-twice', true)).toBe('#444444');
        expect(sourceVarValue(catalog, '--dark-twice', true)).toBe('#666666');
    });

    it('falls back where the sources define no page-wide value for that theme', () => {
        // Tailwind's own palette is not in the sources: the caller reads it from the page.
        expect(sourceVarValue(catalog, '--color-gray-500', false, 'oklch(55.1% 0.027 264.364)')).toBe('oklch(55.1% 0.027 264.364)');
        expect(sourceVarValue(catalog, '--color-gray-500', true)).toBe('');
        // A component-scoped definition is not the page's value.
        expect(sourceVarValue(catalog, '--card-accent', false, 'fallback')).toBe('fallback');
        // A variable only the dark theme defines has no light value in the sources.
        expect(sourceVarValue(catalog, '--dark-only', false, 'fallback')).toBe('fallback');
        expect(sourceVarValue(catalog, '--dark-only', true, 'fallback')).toBe('#000000');
    });
});

describe('changedVarValue', () => {
    it('gives the change of the theme precedence over a change of both, wherever it stands in the list', () => {
        const changes = [varChange('--x', 'both', '#aaaaaa'), varChange('--x', 'dark', '#bbbbbb')];
        expect(changedVarValue(changes, '--x', true)).toBe('#bbbbbb');
        expect(changedVarValue(changes, '--x', false)).toBe('#aaaaaa');
        expect(changedVarValue([...changes].reverse(), '--x', true)).toBe('#bbbbbb');
    });

    it('is null for a theme no change reaches, and ignores changes of other layers or variables', () => {
        const changes = [varChange('--x', 'dark', '#bbbbbb'), varChange('--x', 'both', '#cccccc', 'css-literal'), varChange('--y', 'both', '#dddddd')];
        expect(changedVarValue(changes, '--x', false)).toBeNull();
        expect(changedVarValue(changes, '--z', true)).toBeNull();
        expect(changedVarValue([], '--x', true)).toBeNull();
    });
});

describe('categoryRows and sourceCategoryValue — the chart categories of the catalogue', () => {
    /** A line of the category tables: a chart colour of the categories file, with its category and theme. */
    const tableLine = (id: number, raw: string, theme: 'light' | 'dark', category: string) => literal(id, {file: 2, raw, key: raw.toLowerCase(), zone: 'ts', theme, layer: 'chart-color', chart: true, category});
    const catalog = catalogOf({
        files: ['src/app.css', 'src/lib/components/charts/GrowthChart.svelte', 'src/lib/theme/chartCategories.ts'],
        literals: [
            literal(0, {raw: '#2B4C7E', key: '#2b4c7e'}),
            tableLine(1, '#2B4C7E', 'light', 'type:AAA'),
            tableLine(2, '#7EA6E0', 'dark', 'type:AAA'),
            tableLine(3, '#5A6B7C', 'light', 'bucket:Nowhere'),
            tableLine(4, '#334455', 'dark', 'sector:Zed Sector'),
            tableLine(5, '#0E0E0E', 'light', 'sector:Zed Sector'),
        ],
        // In table order; the bucket has no dark line, and one entry points at a literal the catalogue does not have.
        categories: [
            {target: 'type:AAA', kind: 'type', key: 'AAA', light: 1, dark: 2},
            {target: 'sector:Zed Sector', kind: 'sector', key: 'Zed Sector', light: 5, dark: 4},
            {target: 'bucket:Nowhere', kind: 'bucket', key: 'Nowhere', light: 3, dark: null},
            {target: 'bucket:Lost', kind: 'bucket', key: 'Lost', light: 99, dark: 2},
        ],
    });

    it('lists the categories in the catalogue’s order, each with the value its line writes in each theme', () => {
        expect(categoryRows(catalog)).toEqual([
            {target: 'type:AAA', kind: 'type', key: 'AAA', light: 1, dark: 2, lightValue: '#2B4C7E', darkValue: '#7EA6E0'},
            {target: 'sector:Zed Sector', kind: 'sector', key: 'Zed Sector', light: 5, dark: 4, lightValue: '#0E0E0E', darkValue: '#334455'},
            {target: 'bucket:Nowhere', kind: 'bucket', key: 'Nowhere', light: 3, dark: null, lightValue: '#5A6B7C', darkValue: null},
            {target: 'bucket:Lost', kind: 'bucket', key: 'Lost', light: 99, dark: 2, lightValue: null, darkValue: '#7EA6E0'},
        ]);
    });

    it('lists nothing for a catalogue built before the categories', () => {
        expect(categoryRows(catalogOf({literals: catalog.literals}))).toEqual([]);
        expect(categoryRows(catalogOf({categories: []}))).toEqual([]);
    });

    it('gives the value of a category in the theme asked, and an empty value where the catalogue has none', () => {
        expect(sourceCategoryValue(catalog, 'type:AAA', false)).toBe('#2B4C7E');
        expect(sourceCategoryValue(catalog, 'type:AAA', true)).toBe('#7EA6E0');
        expect(sourceCategoryValue(catalog, 'sector:Zed Sector', false)).toBe('#0E0E0E');
        expect(sourceCategoryValue(catalog, 'bucket:Nowhere', true), 'no dark line').toBe('');
        expect(sourceCategoryValue(catalog, 'bucket:Lost', false), 'a literal the catalogue does not have').toBe('');
        // By target, as the table writes the key: never by a key compared loosely, nor by value.
        expect(sourceCategoryValue(catalog, 'type:aaa', false)).toBe('');
        expect(sourceCategoryValue(catalog, 'type:Ghost', false)).toBe('');
        expect(sourceCategoryValue(catalogOf({literals: catalog.literals}), 'type:AAA', false), 'a catalogue without categories').toBe('');
    });
});
