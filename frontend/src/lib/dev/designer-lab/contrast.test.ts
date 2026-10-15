/**
 * Designer Lab — the contrast panel's pure part (`contrast.ts`): which pairs are declared, how a value resolves through
 * `var()`, and the WCAG ratio of every pair before and after the changes, in both themes.
 *
 * The catalogue is synthetic and the palette fallback is a table, as the page would read it. The ratio formula itself
 * belongs to `color.test.ts`; here the known WCAG figures (21:1 black on white, 1:1 equal colours, 4.83:1 for
 * `#6b7280` on white) pin which values were paired, and `contrastRatio` is the oracle for the other rows.
 */

import {describe, expect, it} from 'vitest';
import {contrastRatio, parseColor} from './color.js';
import {contrastRows, declaredPairs, resolveColor, wcagLevel, type PairRow} from './contrast';
import type {CatalogVar, CatalogVarDef, ColorCatalog, LabChange} from './types';

function catalogOf(css_vars: CatalogVar[]): ColorCatalog {
    return {
        meta: {schema: 'lf-color-catalog/1', app_version: 'test', generated_at: '2026-10-14T18:00:00.000Z', hash: 'sha256:test', scan_ms: 0, parity: {}, layers: {}, excluded: []},
        files: ['src/app.css'],
        css_vars,
        palette: [],
        literals: [],
        by_value: {},
        testids: {},
        testid_prefixes: [],
    };
}

const def = (name: string, value: string, fields: Partial<CatalogVarDef> = {}): CatalogVarDef => ({file: 0, name, value, line: 1, zone: 'css-file', selector: ':root, html.light', theme: 'both', scope: 'root', ...fields});

/** A variable defined for the page in light (`:root`) and, when given, in dark (`html.dark`). */
const themed = (name: string, light: string, dark?: string): CatalogVar => ({
    name,
    defs: [def(name, light), ...(dark === undefined ? [] : [def(name, dark, {selector: 'html.dark', theme: 'dark'})])],
    uses: 1,
    files: {'0': 1},
    use_sites: [],
});

const scoped = (name: string, value: string): CatalogVar => ({name, defs: [def(name, value, {selector: '.card', scope: 'scoped'})], uses: 1, files: {'0': 1}, use_sites: []});

/** In catalogue order (by name), as the scanner writes it. */
const CATALOG = catalogOf([
    scoped('--card-accent', '#10b981'),
    themed('--theme-bg-card', '#ffffff', '#1e293b'),
    themed('--theme-bg-hover', '#f3f4f6', '#334155'),
    themed('--theme-bg-primary', '#ffffff', '#0f172a'),
    themed('--theme-border-primary', '#e5e7eb', '#334155'),
    themed('--theme-text-muted', '#6b7280', '#94a3b8'),
    themed('--theme-text-primary', 'var(--color-gray-900)', '#f8fafc'),
    scoped('--theme-text-scoped', '#000000'),
]);

/** Tailwind's palette as the page would report it: only what the sources do not define. */
const PAGE: Record<string, string> = {'--color-gray-900': '#111827'};
const fallback = (name: string): string => PAGE[name] ?? '';

const change = (target: string, scope: LabChange['scope'], to: string): LabChange => ({id: `css-var:${target}@${scope}`, layer: 'css-var', target, scope, from: '', to});

/** The oracle for a pair of plain colours: the WCAG ratio, rounded as the panel rounds it. */
function ratioOf(fg: string, bg: string): number {
    const f = parseColor(fg);
    const b = parseColor(bg);
    if (!f || !b) throw new Error(`not a colour: ${fg} / ${bg}`);
    return Math.round(contrastRatio(f, b) * 100) / 100;
}

function row(rows: PairRow[], fg: string, bg: string, scope: 'light' | 'dark'): PairRow {
    const found = rows.filter((r) => r.fg === fg && r.bg === bg && r.scope === scope);
    expect(found, `${fg} on ${bg} (${scope})`).toHaveLength(1);
    return found[0];
}

describe('declaredPairs', () => {
    it('pairs every page-wide text variable with every surface, and every border with the card surface', () => {
        expect(declaredPairs(CATALOG)).toEqual([
            {fg: '--theme-text-muted', bg: '--theme-bg-card', kind: 'text'},
            {fg: '--theme-text-muted', bg: '--theme-bg-primary', kind: 'text'},
            {fg: '--theme-text-primary', bg: '--theme-bg-card', kind: 'text'},
            {fg: '--theme-text-primary', bg: '--theme-bg-primary', kind: 'text'},
            {fg: '--theme-border-primary', bg: '--theme-bg-card', kind: 'ui'},
        ]);
    });

    it('measures borders on the first surface when there is no card surface, and not at all without a surface', () => {
        expect(declaredPairs(catalogOf([themed('--theme-bg-primary', '#ffffff'), themed('--theme-border-primary', '#e5e7eb')]))).toEqual([{fg: '--theme-border-primary', bg: '--theme-bg-primary', kind: 'ui'}]);
        expect(declaredPairs(catalogOf([themed('--theme-border-primary', '#e5e7eb'), themed('--theme-text-muted', '#6b7280')]))).toEqual([]);
    });
});

describe('resolveColor', () => {
    const table: Record<'light' | 'dark', Record<string, string>> = {
        light: {'--a': 'var(--b)', '--b': 'var(--c)', '--c': '#000000', '--loop': 'var(--loop)', '--themed': '#ffffff'},
        dark: {'--themed': '#000000'},
    };
    const lookup = (name: string, dark: boolean): string => table[dark ? 'dark' : 'light'][name] ?? '';

    it('reads a plain colour, and follows a chain of variables to one', () => {
        expect(resolveColor('#ffffff', false, lookup)).toEqual(parseColor('#ffffff'));
        expect(resolveColor('  var( --a )  ', false, lookup)).toEqual(parseColor('#000000'));
    });

    it('asks the lookup for the theme it resolves', () => {
        expect(resolveColor('var(--themed)', false, lookup)).toEqual(parseColor('#ffffff'));
        expect(resolveColor('var(--themed)', true, lookup)).toEqual(parseColor('#000000'));
    });

    it('uses the fallback of `var()` when the variable has no value', () => {
        expect(resolveColor('var(--missing, #ff0000)', false, lookup)).toEqual(parseColor('#ff0000'));
        expect(resolveColor('var(--missing, var(--c))', false, lookup)).toEqual(parseColor('#000000'));
    });

    it('gives null for what does not resolve to a colour, a cycle included, without looping', () => {
        expect(resolveColor('var(--missing)', false, lookup)).toBeNull();
        expect(resolveColor('var(--loop)', false, lookup)).toBeNull();
        expect(resolveColor('Inter, sans-serif', false, lookup)).toBeNull();
    });
});

describe('contrastRows', () => {
    it('measures every declared pair in light and then dark, the same before and after when nothing changed', () => {
        const rows = contrastRows(CATALOG, [], fallback);
        expect(rows.map((r) => `${r.fg} ${r.bg} ${r.scope}`)).toEqual(declaredPairs(CATALOG).flatMap((p) => [`${p.fg} ${p.bg} light`, `${p.fg} ${p.bg} dark`]));
        for (const r of rows) expect(r.after, `${r.fg} on ${r.bg} (${r.scope})`).toBe(r.before);
        expect(row(rows, '--theme-text-muted', '--theme-bg-card', 'light').before).toBe(4.83);
        expect(row(rows, '--theme-text-muted', '--theme-bg-card', 'dark').before).toBe(ratioOf('#94a3b8', '#1e293b'));
        expect(row(rows, '--theme-border-primary', '--theme-bg-card', 'dark')).toMatchObject({kind: 'ui', before: ratioOf('#334155', '#1e293b')});
    });

    it('resolves what the sources leave to Tailwind through the page fallback, and gives null without one', () => {
        expect(row(contrastRows(CATALOG, [], fallback), '--theme-text-primary', '--theme-bg-card', 'light').before).toBe(ratioOf('#111827', '#ffffff'));
        const blind = row(contrastRows(CATALOG, []), '--theme-text-primary', '--theme-bg-card', 'light');
        expect(blind.before).toBeNull();
        expect(blind.after).toBeNull();
    });

    it('applies a one-theme change to that theme only', () => {
        const rows = contrastRows(CATALOG, [change('--theme-text-muted', 'light', '#000000')], fallback);
        expect(row(rows, '--theme-text-muted', '--theme-bg-card', 'light')).toMatchObject({before: 4.83, after: 21});
        expect(row(rows, '--theme-text-muted', '--theme-bg-primary', 'light').after).toBe(21);
        const dark = row(rows, '--theme-text-muted', '--theme-bg-card', 'dark');
        expect(dark.after).toBe(dark.before);
    });

    it('follows a change to a variable the declared ones read, and a change to a surface', () => {
        // `--theme-text-primary` reads `--color-gray-900` in light only.
        const rows = contrastRows(CATALOG, [change('--color-gray-900', 'both', '#ffffff'), change('--theme-bg-card', 'dark', '#ffffff')], fallback);
        expect(row(rows, '--theme-text-primary', '--theme-bg-card', 'light').after).toBe(1);
        expect(row(rows, '--theme-text-primary', '--theme-bg-primary', 'light').after).toBe(1);
        const darkPrimary = row(rows, '--theme-text-primary', '--theme-bg-primary', 'dark');
        expect(darkPrimary.after).toBe(darkPrimary.before);
        expect(row(rows, '--theme-text-primary', '--theme-bg-card', 'dark').after).toBe(ratioOf('#f8fafc', '#ffffff'));
        expect(row(rows, '--theme-border-primary', '--theme-bg-card', 'dark').after).toBe(ratioOf('#334155', '#ffffff'));
    });
});

describe('wcagLevel', () => {
    it('grades text against 7:1 and 4.5:1, and borders and graphics against 3:1', () => {
        expect([7, 6.99, 4.5, 4.49].map((v) => wcagLevel(v, 'text'))).toEqual(['AAA', 'AA', 'AA', 'fail']);
        expect([21, 3, 2.99].map((v) => wcagLevel(v, 'ui'))).toEqual(['AA', 'AA', 'fail']);
        expect(wcagLevel(null, 'text')).toBe('—');
        expect(wcagLevel(null, 'ui')).toBe('—');
    });
});
