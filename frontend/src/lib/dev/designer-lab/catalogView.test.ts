/**
 * Designer Lab — what the Lab page lists, derived from the catalogue (`catalogView.ts`).
 *
 * Pure functions over a synthetic catalogue: grouping and ordering of the palette, the variables that hold a colour,
 * the hand-written colours grouped by value, the search filter, and the value a variable has in a theme before and
 * after the changes. Every expectation follows from the few entries written below, never from the real tree.
 */

import {describe, expect, it} from 'vitest';
import {appVars, changedVarValue, matchesSearch, paletteFamilies, sourceVarValue, valueGroups} from './catalogView';
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
