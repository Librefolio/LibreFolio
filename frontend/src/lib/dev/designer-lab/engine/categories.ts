/**
 * Designer Lab — the fixed colours of the chart categories, as the charts ask for them (contract C1–C4 with DV,
 * `lib/theme/chartCategories.ts`).
 *
 * Every chart reads the colour of an asset type or a sector through `categoryColor(kind, key, dark)` (C1), which in a
 * debug build first asks `globalThis.__lfDesignerLab.categoryColor` (C3). This module holds the `category` changes of
 * the applied state and answers for them: the colour a change gives the category in the asked theme, as a canvas reads
 * it — `#rrggbb` when opaque, so the GR4 shades can mix it, `rgba()` when translucent — or nothing, and the table's own
 * colour stands. The engine then tells the charts to read again (C4, `notifyChartColorsChange`).
 *
 * A change is found by key, never by value: asset types and sectors share values (`ETF` and `Technology`), and so do
 * some roles. The buckets (`Liquidity`, `Unknown`) are one entry for both kinds, as in the tables.
 */

import {lookupKey} from '$lib/theme/chartCategories';
import {toCanvasColor} from '../color.js';
import {changesForTheme} from '../store';
import type {LabChange} from '../types';
import {resolveTarget} from './targets';

/**
 * A key as `categoryColor` compares it: case, spaces and underscores ignored (`Health Care`, `HEALTH_CARE`). DV's own
 * `lookupKey` (TD-1), so that an edit and the table it overrides always agree on what the same key is.
 */
export const categoryKey = lookupKey;

const BUCKETS = new Set(['LIQUIDITY', 'UNKNOWN']);

/** The lookup key of a change target (`sector:Health Care` → `sector:HEALTHCARE`); null when it names no category. */
export function categoryTargetKey(target: string): string | null {
    const m = /^(type|sector|bucket):(.+)$/.exec(target);
    return m ? `${m[1]}:${categoryKey(m[2])}` : null;
}

let plan: {light: Map<string, string>; dark: Map<string, string>} = {light: new Map(), dark: new Map()};

/** Hold the `category` changes of the applied state (none when it has no effect). Returns how many name a category. */
export function setCategoryChanges(changes: LabChange[]): number {
    const next = {light: new Map<string, string>(), dark: new Map<string, string>()};
    for (const [theme, dark] of [
        ['light', false],
        ['dark', true],
    ] as const) {
        // Both themes first, then the theme's own: a theme's change wins over one for both, as in L1.
        const own = changesForTheme(changes, dark)
            .filter((c) => c.layer === 'category')
            .sort((a, b) => Number(a.scope !== 'both') - Number(b.scope !== 'both'));
        for (const c of own) {
            const key = categoryTargetKey(c.target);
            if (key) next[theme].set(key, c.to);
        }
    }
    plan = next;
    return changes.filter((c) => c.layer === 'category' && categoryTargetKey(c.target)).length;
}

/**
 * The answer to `categoryColor(kind, key, dark)`: the colour a change gives the category in that theme, as the canvas
 * reads it; undefined when no change applies, or its value does not resolve now (a `var()` the page does not define).
 */
export function categoryColor(kind: 'type' | 'sector', key: string, dark: boolean): string | undefined {
    const k = categoryKey(key);
    // A key of the change's kind, or a bucket for both kinds. A key outside the tables, which `categoryColor` draws in
    // the Unknown colour and the enum gates keep out of real data, is not answered by an edit of `bucket:Unknown`.
    const value = (dark ? plan.dark : plan.light).get(BUCKETS.has(k) ? `bucket:${k}` : `${kind}:${k}`);
    if (value === undefined) return undefined;
    // Resolved at each ask: a `var()` follows the page's current value, an L1 edit of it included.
    const rgba = resolveTarget(value)?.rgba;
    return rgba ? toCanvasColor(rgba) : undefined;
}
