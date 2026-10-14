/**
 * Designer Lab — what the page lists, derived from the catalogue. Pure functions: no DOM, so they can be unit-tested.
 */

import {parseColor} from './color.js';
import type {CatalogLiteral, CatalogPaletteEntry, CatalogVar, ColorCatalog, LabChange, Layer} from './types';

export const SHADES = ['50', '100', '200', '300', '400', '500', '600', '700', '800', '900', '950'];

export interface PaletteFamily {
    family: string;
    entries: (CatalogPaletteEntry & {shade: string})[];
}

/** Tailwind palette variables in use, grouped by family (`--color-emerald-*`), shades in order; the rest last. */
export function paletteFamilies(catalog: ColorCatalog): PaletteFamily[] {
    const families = new Map<string, PaletteFamily>();
    for (const entry of catalog.palette) {
        const m = /^--color-([a-z]+)-(\d{2,3})$/.exec(entry.var);
        const family = m && SHADES.includes(m[2]) ? m[1] : 'other';
        const shade = m && SHADES.includes(m[2]) ? m[2] : entry.var.replace(/^--color-/, '');
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

/** CSS variables the app defines with a colour value (brand, `--theme-*`, component variables), in name order. */
export function appVars(catalog: ColorCatalog): CatalogVar[] {
    return catalog.css_vars.filter((v) => v.defs.some((d) => parseColor(d.value) || /color-mix\(|var\(|rgba?\(|hsla?\(|oklch\(/.test(d.value)));
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
 * (`html.dark` for dark; `:root`, `@theme` for light), else `fallback` (Tailwind's own palette, read from the page).
 */
export function sourceVarValue(catalog: ColorCatalog, name: string, dark: boolean, fallback = ''): string {
    const v = catalog.css_vars.find((x) => x.name === name);
    const roots = v?.defs.filter((d) => d.scope === 'root') ?? [];
    const pick = dark ? (roots.find((d) => d.theme === 'dark') ?? roots.find((d) => d.theme !== 'dark')) : roots.find((d) => d.theme !== 'dark');
    return pick?.value ?? fallback;
}

/** The value a variable has in a theme once the changes apply (the change for that theme wins over `both`). */
export function changedVarValue(changes: LabChange[], name: string, dark: boolean): string | null {
    const theme = dark ? 'dark' : 'light';
    const own = changes.find((c) => c.layer === 'css-var' && c.target === name && c.scope === theme);
    const both = changes.find((c) => c.layer === 'css-var' && c.target === name && c.scope === 'both');
    return (own ?? both)?.to ?? null;
}
