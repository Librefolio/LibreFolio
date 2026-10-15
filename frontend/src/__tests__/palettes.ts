/**
 * The guard of the category colour tables: how many slots each has, how a test reads it, and what is wrong with one.
 *
 * Since the designer's round 2 (GR1–GR5, the developer's decision D-T17) no allocation chart colours a slice by its rank
 * in a 14-slot palette any more: every category keeps one colour wherever it is drawn (GR1), read through
 * `categoryColor` (`$lib/theme/chartCategories`), the charts' one read point (contract C1 with the Designer Lab). The
 * tables behind it are not exported, on purpose — nothing may bypass the Lab's hook (C3) — so a test reads a table the
 * way a chart does: one `categoryColor` call per key of `CATEGORY_KEYS`, in the designer's order (`categoryPalette`). Its
 * slots are its keys (`categorySlots`): the asset-type families, the sectors. The two buckets the engine adds beside
 * them (`CATEGORY_BUCKETS`, the cash and the unclassified) are shared by both tables and are not slots.
 *
 * Under Vitest the Lab's hook is off (`__LF_DESIGNER_LAB__` is a Vite `define`, absent here), so these are the
 * designer's values unless a test turns the hook on itself.
 *
 * `paletteDefects` is the guard the old palettes went through, kept: the number of slots asked for, each a `#rrggbb`,
 * none repeating another. `palettes.test.ts` pins every defect it names on synthetic palettes, then holds the two tables
 * to it in both themes. The values themselves, and how far apart they are, are `chartCategories.test.ts`'s; that the
 * charts draw them is proven on the mounted charts (`AllocationPieChart.test.ts`, `AllocationHistoryChart.test.ts`).
 *
 * Beside the other `$test` helpers: not a `*.test.ts`, so vitest does not collect it and `check-orphans` does not
 * count it, and every `__tests__` directory is outside coverage (`vitest.config.ts`).
 */
import {CATEGORY_KEYS, categoryColor, type CategoryKind} from '$lib/theme/chartCategories';

/** How many slots the table of `kind` has: one per key of `CATEGORY_KEYS`, the buckets aside. */
export function categorySlots(kind: CategoryKind): number {
    return CATEGORY_KEYS[kind].length;
}

/** The table of `kind` in one theme, as the charts read it: `categoryColor` for each key of `CATEGORY_KEYS`, in order. */
export function categoryPalette(kind: CategoryKind, dark: boolean): string[] {
    return CATEGORY_KEYS[kind].map((key) => categoryColor(kind, key, dark));
}

/**
 * What is wrong with a palette, one sentence per defect — empty when nothing is: not `slots` entries, an entry that is
 * not `#rrggbb`, an entry that repeats an earlier one whatever its letter case. Returned rather than asserted, so each
 * test states the guard in its own `expect` and a red names the slot at fault.
 */
export function paletteDefects(palette: readonly string[], slots: number): string[] {
    const defects: string[] = [];
    if (palette.length !== slots) defects.push(`has ${palette.length} entries, not ${slots}`);
    palette.forEach((hex, index) => {
        if (!/^#[0-9a-fA-F]{6}$/.test(hex)) defects.push(`slot ${index} (${hex}) is not #rrggbb`);
        const first = palette.findIndex((other) => other.toLowerCase() === hex.toLowerCase());
        if (first !== index) defects.push(`slot ${index} repeats slot ${first} (${hex})`);
    });
    return defects;
}
