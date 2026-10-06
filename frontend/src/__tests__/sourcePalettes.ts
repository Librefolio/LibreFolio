/**
 * A chart's colour palette, read from the component that declares it.
 *
 * Three test files used to measure "the real palettes" on copies of their own,
 * pinned by comments naming line numbers the constants had long since left, and
 * nobody read the `.svelte`: a slot repeated, an entry dropped or the constant
 * renamed left all of them green. Reading the declaration is what makes "real"
 * true.
 *
 * Found by NAME, never by line: `const <NAME> = ['#rrggbb', …];`. Anything the
 * reader cannot vouch for throws, naming the file and the constant — a
 * declaration that is missing or repeated, an initialiser that is not a literal
 * array, an entry that is not a `'#rrggbb'` literal, an array with no colour in
 * it — so a read never goes vacuous: it returns the whole palette, or it fails.
 *
 * Beside the other `$test` helpers: not a `*.test.ts`, so vitest does not
 * collect it and `check-orphans` does not count it, and every `__tests__`
 * directory is outside coverage (`vitest.config.ts`).
 */
import {readFileSync} from 'node:fs';
import {basename} from 'node:path';
import {fileURLToPath} from 'node:url';

/** One `'#rrggbb'` string literal, in either quote, and nothing else. */
const HEX_ENTRY = /^(['"])(#[0-9a-fA-F]{6})\1$/;

function escapeRegExp(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * The palette `const <constName> = [...]` declares in `source`, entries in order
 * and as written. `origin` names the source in the errors.
 */
export function parseSourcePalette(source: string, constName: string, origin = 'source'): string[] {
    const name = escapeRegExp(constName);

    // Every declaration of the name counts, whatever it is initialised with: two of
    // them leave "which one does the chart use" unanswerable from here.
    const declarations = source.match(new RegExp(String.raw`\bconst\s+${name}\s*[:=]`, 'g')) ?? [];
    if (declarations.length === 0) throw new Error(`${origin}: no \`const ${constName}\` declaration — renamed or removed? The palette is looked up by name.`);
    if (declarations.length > 1) throw new Error(`${origin}: \`const ${constName}\` is declared ${declarations.length} times — which one the chart uses cannot be told from here.`);

    const literal = new RegExp(String.raw`\bconst\s+${name}\s*(?::[^=]*)?=\s*\[([^\]]*)\]\s*(?:as\s+const\s*)?;`).exec(source);
    if (!literal) throw new Error(`${origin}: \`const ${constName}\` is not initialised with a literal array of '#rrggbb' strings.`);

    const entries = literal[1]
        .split(',')
        .map((entry) => entry.trim())
        .filter((entry) => entry !== '');
    if (entries.length === 0) throw new Error(`${origin}: \`${constName}\` holds no colour.`);
    const invalid = entries.filter((entry) => !HEX_ENTRY.test(entry));
    if (invalid.length > 0) throw new Error(`${origin}: \`${constName}\` holds ${invalid.join(', ')} — only '#rrggbb' literals are read.`);

    return entries.map((entry) => (HEX_ENTRY.exec(entry) as RegExpExecArray)[2]);
}

/** The palette `const <constName> = [...]` declares in the file at `sourceUrl`. */
export function readSourcePalette(sourceUrl: URL, constName: string): string[] {
    return parseSourcePalette(readFileSync(sourceUrl, 'utf8'), constName, basename(fileURLToPath(sourceUrl)));
}

/**
 * How many slots each allocation palette has. Both charts colour by `palette[i % 14]`,
 * and the comment above the constants in `AllocationHistoryChart.svelte` says why 14.
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
