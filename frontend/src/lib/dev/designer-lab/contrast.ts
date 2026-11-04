/**
 * Designer Lab — WCAG contrast of the declared pairs (`--theme-text-*` on `--theme-bg-*`, borders on cards), before
 * and after the changes, in both themes. Pure: values come from the catalogue and the changes; `fallback` resolves
 * what the sources do not define (Tailwind's palette, read from the page by the caller).
 */

import {contrastRatio, parseColor, type Rgba} from './color.js';
import {changedVarValue, sourceVarValue} from './catalogView';
import type {ColorCatalog, LabChange} from './types';

export interface Pair {
    fg: string;
    bg: string;
    /** `text`: AA asks 4.5:1; `ui`: borders and graphics ask 3:1. */
    kind: 'text' | 'ui';
}

export interface PairRow extends Pair {
    scope: 'light' | 'dark';
    before: number | null;
    after: number | null;
}

/** Text variables on surface variables, and border variables on the card surface, as the sources define them. */
export function declaredPairs(catalog: ColorCatalog): Pair[] {
    const names = catalog.css_vars.filter((v) => v.defs.some((d) => d.scope === 'root')).map((v) => v.name);
    const texts = names.filter((n) => /^--theme-text-/.test(n));
    const surfaces = names.filter((n) => /^--theme-bg-/.test(n) && !/hover/.test(n));
    const borders = names.filter((n) => /^--theme-border-/.test(n));
    const card = surfaces.find((n) => /card/.test(n)) ?? surfaces[0];
    const pairs: Pair[] = [];
    for (const fg of texts) for (const bg of surfaces) pairs.push({fg, bg, kind: 'text'});
    if (card) for (const fg of borders) pairs.push({fg, bg: card, kind: 'ui'});
    return pairs;
}

type Lookup = (name: string, dark: boolean) => string;

/** Resolve a value to a colour, following `var(--x)` (with or without a fallback) up to a few levels. */
export function resolveColor(value: string, dark: boolean, lookup: Lookup, depth = 0): Rgba | null {
    const v = value.trim();
    const ref = /^var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)$/.exec(v);
    if (ref) {
        if (depth > 4) return null;
        const inner = lookup(ref[1], dark);
        return resolveColor(inner || ref[2] || '', dark, lookup, depth + 1);
    }
    return parseColor(v);
}

const ratio = (fg: Rgba | null, bg: Rgba | null) => (fg && bg ? Math.round(contrastRatio(fg, bg) * 100) / 100 : null);

export function contrastRows(catalog: ColorCatalog, changes: LabChange[], fallback: (name: string) => string = () => ''): PairRow[] {
    const before: Lookup = (name, dark) => sourceVarValue(catalog, name, dark, fallback(name));
    const after: Lookup = (name, dark) => changedVarValue(changes, name, dark) ?? before(name, dark);
    const rows: PairRow[] = [];
    for (const pair of declaredPairs(catalog)) {
        for (const dark of [false, true]) {
            rows.push({
                ...pair,
                scope: dark ? 'dark' : 'light',
                before: ratio(resolveColor(`var(${pair.fg})`, dark, before), resolveColor(`var(${pair.bg})`, dark, before)),
                after: ratio(resolveColor(`var(${pair.fg})`, dark, after), resolveColor(`var(${pair.bg})`, dark, after)),
            });
        }
    }
    return rows;
}

/** The WCAG level a ratio reaches for this kind of pair. */
export function wcagLevel(value: number | null, kind: Pair['kind']): 'AAA' | 'AA' | 'fail' | '—' {
    if (value === null) return '—';
    if (kind === 'ui') return value >= 3 ? 'AA' : 'fail';
    return value >= 7 ? 'AAA' : value >= 4.5 ? 'AA' : 'fail';
}
