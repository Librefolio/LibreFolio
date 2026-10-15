/**
 * The guard of the allocation palettes: how many slots they have, and what is wrong with one.
 *
 * The palettes themselves are imported from `$lib/theme/chartPalettes` — `ALLOCATION_PIE_PALETTE` and
 * `ALLOCATION_HISTORY_PALETTE`, `light` and `dark` — the module the two allocation charts draw from. Three test
 * files used to measure copies of their own, which agreed with themselves whatever the charts drew; then they read
 * the palettes out of the components by name, through a source reader this file replaces (`sourcePalettes.ts`).
 * Since the colour refactor (R, W4) the charts and the tests import one declaration, so the import is the reading,
 * and that the charts draw it is proven on the mounted charts, in both themes: `AllocationPieChart.test.ts` and
 * `AllocationHistoryChart.test.ts`.
 *
 * Beside the other `$test` helpers: not a `*.test.ts`, so vitest does not collect it and `check-orphans` does not
 * count it, and every `__tests__` directory is outside coverage (`vitest.config.ts`).
 */

/**
 * How many slots each allocation palette has. Both charts colour by `palette[i % 14]`, and the comment above the
 * palette constants in `AllocationHistoryChart.svelte` says why 14.
 */
export const PALETTE_SLOTS = 14;

/**
 * What is wrong with a palette the allocation charts are built on, one sentence per
 * defect — empty when nothing is. Returned rather than asserted, so each test states
 * the guard in its own `expect` and a red names the slot at fault.
 */
export function paletteDefects(palette: readonly string[], slots: number = PALETTE_SLOTS): string[] {
    const defects: string[] = [];
    if (palette.length !== slots) defects.push(`has ${palette.length} entries, not ${slots}`);
    palette.forEach((hex, index) => {
        if (!/^#[0-9a-fA-F]{6}$/.test(hex)) defects.push(`slot ${index} (${hex}) is not #rrggbb`);
        const first = palette.findIndex((other) => other.toLowerCase() === hex.toLowerCase());
        if (first !== index) defects.push(`slot ${index} repeats slot ${first} (${hex})`);
    });
    return defects;
}
