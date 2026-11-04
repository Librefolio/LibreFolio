/**
 * Designer Lab — what the page lists, derived from the catalogue. Pure functions: no DOM, so they can be unit-tested.
 */

import {CATEGORY_ROLES} from '$lib/theme/chartCategories';

import {parseColor} from './color.js';
import type {CatalogCategory, CatalogLiteral, CatalogPaletteEntry, CatalogVar, ColorCatalog, LabChange, Layer} from './types';

export const SHADES = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'];

export interface PaletteFamily {
    family: string;
    entries: (CatalogPaletteEntry & {shade: string})[];
}

/**
 * Tailwind palette variables in use, grouped by family (`--color-emerald-*`), shades in order; the colour roles of
 * workstream T (`--color-lf-*`, utilities `bg-lf-card`…) as the family `lf`; the rest last.
 */
export function paletteFamilies(catalog: ColorCatalog): PaletteFamily[] {
    const families = new Map<string, PaletteFamily>();
    for (const entry of catalog.palette) {
        const role = /^--color-lf-(.+)$/.exec(entry.var);
        const m = /^--color-([a-z]+)-(\d{2,3})$/.exec(entry.var);
        const shaded = !!m && SHADES.includes(m[2]);
        const family = role ? 'lf' : shaded && m ? m[1] : 'other';
        const shade = role ? role[1] : shaded && m ? m[2] : entry.var.replace(/^--color-/, '');
        let f = families.get(family);
        if (!f) {
            f = {family, entries: []};
            families.set(family, f);
        }
        f.entries.push({...entry, shade});
    }
    const order = (s: string) => (SHADES.includes(s) ? SHADES.indexOf(s) : 100);
    for (const f of families.values()) f.entries.sort((a, b) => order(a.shade) - order(b.shade) || a.shade.localeCompare(b.shade));
    return [...families.values()].sort((a, b) => (a.family === 'other' ? 1 : b.family === 'other' ? -1 : b.entries.reduce((n, e) => n + e.uses, 0) - a.entries.reduce((n, e) => n + e.uses, 0)));
}

/**
 * CSS variables the app defines with a colour value (brand, `--theme-*`, the `--lf-*` roles, component variables), in
 * name order. Not the inline aliases of `@theme inline`: no stylesheet defines them at runtime, so editing one would
 * change nothing (the palette shows them, with the role they stand for).
 */
export function appVars(catalog: ColorCatalog): CatalogVar[] {
    return catalog.css_vars.filter((v) => !isInlineAlias(v) && v.defs.some((d) => parseColor(d.value) || /color-mix\(|var\(|rgba?\(|hsla?\(|oklch\(/.test(d.value)));
}

/** Whether every definition of a variable is an alias of `@theme inline`. */
export function isInlineAlias(v: CatalogVar): boolean {
    return v.defs.length > 0 && v.defs.every((d) => d.inline);
}

/** The variable the Lab edits for a palette entry: the role an inline alias stands for, else the entry's own. */
export function editTarget(entry: CatalogPaletteEntry): string {
    return entry.role ?? entry.var;
}

export interface VarImpact {
    /** The palette entries whose classes change with the variable: its own, and the inline aliases standing for it. */
    entries: CatalogPaletteEntry[];
    variable: CatalogVar | undefined;
    uses: number;
    files: number;
    /** Every class of those entries, with its number of uses. */
    classes: Record<string, number>;
}

/**
 * What editing a variable reaches in the code: the palette classes that read it — directly (`text-gray-500` for
 * `--color-gray-500`) or through an inline alias (`bg-lf-card` for `--lf-surface-card`) — and the stylesheets that
 * read it with `var()`.
 */
export function varImpact(catalog: ColorCatalog, name: string): VarImpact {
    const entries = catalog.palette.filter((p) => p.var === name || p.role === name);
    const variable = catalog.css_vars.find((v) => v.name === name);
    const classes: Record<string, number> = {};
    for (const e of entries) for (const [cls, n] of Object.entries(e.classes)) classes[cls] = (classes[cls] ?? 0) + n;
    const files = new Set([...entries.flatMap((e) => Object.keys(e.files)), ...Object.keys(variable?.files ?? {})]);
    return {entries, variable, uses: entries.reduce((n, e) => n + e.uses, 0) + (variable?.uses ?? 0), files: files.size, classes};
}

export interface ValueGroup {
    key: string;
    literals: CatalogLiteral[];
    files: number;
    /** Distinct alpha values written for this colour (1 = opaque). */
    alphas: number[];
    themes: string[];
}

/** Hand-written colours of the given layers, grouped by colour (alpha variants together), most used first. */
export function valueGroups(catalog: ColorCatalog, layers: Layer[]): ValueGroup[] {
    const groups = new Map<string, CatalogLiteral[]>();
    for (const lit of catalog.literals) {
        if (!lit.key || !layers.includes(lit.layer)) continue;
        const list = groups.get(lit.key) ?? [];
        list.push(lit);
        groups.set(lit.key, list);
    }
    return [...groups.entries()]
        .map(([key, literals]) => ({
            key,
            literals,
            files: new Set(literals.map((l) => l.file)).size,
            alphas: [...new Set(literals.map((l) => l.alpha ?? 1))].sort((a, b) => b - a),
            themes: [...new Set(literals.map((l) => l.theme ?? '?'))].sort(),
        }))
        .sort((a, b) => b.literals.length - a.literals.length || a.key.localeCompare(b.key));
}

/** Whether a search text matches a group or entry: name, value or one of its files. */
export function matchesSearch(query: string, texts: string[]): boolean {
    const q = query.trim().toLowerCase();
    return !q || texts.some((t) => t.toLowerCase().includes(q));
}

/**
 * The value a CSS variable has in a theme before any change: its definition for that theme in the app's sources
 * (`html.dark` for dark; `html.light`, `html:not(.dark)` for light), else a definition both themes share (`:root`,
 * `@theme`) — never the other theme's — and at equal footing the later one, as in the cascade; else `fallback`
 * (Tailwind's own palette, read from the page).
 */
export function sourceVarValue(catalog: ColorCatalog, name: string, dark: boolean, fallback = ''): string {
    const v = catalog.css_vars.find((x) => x.name === name);
    const roots = v?.defs.filter((d) => d.scope === 'root') ?? [];
    const theme = dark ? 'dark' : 'light';
    const own = roots.filter((d) => d.theme === theme);
    const shared = roots.filter((d) => d.theme !== 'dark' && d.theme !== 'light');
    const pick = own.length ? own[own.length - 1] : shared[shared.length - 1];
    return pick?.value ?? fallback;
}

/** The value a variable has in a theme once the changes apply (the change for that theme wins over `both`). */
export function changedVarValue(changes: LabChange[], name: string, dark: boolean): string | null {
    const theme = dark ? 'dark' : 'light';
    const own = changes.find((c) => c.layer === 'css-var' && c.target === name && c.scope === theme);
    const both = changes.find((c) => c.layer === 'css-var' && c.target === name && c.scope === 'both');
    return (own ?? both)?.to ?? null;
}

/**
 * A chart category with the value its table writes in each theme (`null` when it writes none). An asset type or the
 * cash is a view of its role (DV-11): `role` names it, the values are the role's in tokens.css, and an edit of the row
 * is an edit of that variable.
 */
export interface CategoryRow extends CatalogCategory {
    lightValue: string | null;
    darkValue: string | null;
    role?: string;
}

/** The chart categories, in the order of their tables: the asset types and the cash as views of their roles, then the rest. */
export function categoryRows(catalog: ColorCatalog): CategoryRow[] {
    const value = (id: number | null) => (id === null ? null : (catalog.literals[id]?.raw ?? null));
    const roleValue = (role: string, dark: boolean) => sourceVarValue(catalog, role, dark) || null;
    const roles = CATEGORY_ROLES.map((c): CategoryRow => ({target: c.target, kind: c.kind, key: c.key, light: null, dark: null, role: c.role, lightValue: roleValue(c.role, false), darkValue: roleValue(c.role, true)}));
    const own = (catalog.categories ?? []).filter((c) => !roles.some((r) => r.target === c.target)).map((c) => ({...c, lightValue: value(c.light), darkValue: value(c.dark)}));
    return [...roles.filter((r) => r.kind === 'type'), ...own.filter((c) => c.kind !== 'bucket'), ...roles.filter((r) => r.kind === 'bucket'), ...own.filter((c) => c.kind === 'bucket')];
}

/** The value the tables give a category in a theme; `''` when the catalogue does not know it. */
export function sourceCategoryValue(catalog: ColorCatalog, target: string, dark: boolean): string {
    const row = categoryRows(catalog).find((c) => c.target === target);
    return (dark ? row?.darkValue : row?.lightValue) ?? '';
}
