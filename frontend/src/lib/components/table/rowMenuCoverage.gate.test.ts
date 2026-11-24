/**
 * Gate: a table row that shows the ⋮ also opens the same menu on a right click (81 U15).
 *
 * The developer's rule: «tutte le tabelle con un menu ⋮» answer the right click with that menu. A `<DataTable>` that
 * passes `rowActions` must therefore not switch the context menu off: `enableContextMenu={false}`, or a value that
 * follows the phone (`enableContextMenu={phone.current}`), leaves the row without a right click on the desktop.
 *
 * Not flagged:
 * - a table with no `rowActions` (nothing to open: the risk and report tables);
 * - `enableContextMenu` left out (the default is on), `{true}`, or an expression that does not name `phone`
 *   (`TransactionsTable`: `{!compact}`, and with `compact` its `rowActions` are empty).
 *
 * `EXCEPTIONS` is the whole list of allowed misses and it is empty: add a path only with the reason written next to it.
 * The input fields inside a row keep the browser's own menu, so «Paste» works there: that is `DataTable`'s job
 * (DataTable.test.ts), not a reason to switch the row menu off.
 */
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {describe, expect, it} from 'vitest';

const LIB = fileURLToPath(new URL('../../', import.meta.url));

/** `path:reason`, none today. */
const EXCEPTIONS: string[] = [];

function walk(dir: string, out: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
        if (name === 'node_modules' || name === '__tests__') continue;
        const full = join(dir, name);
        if (statSync(full).isDirectory()) walk(full, out);
        else if (full.endsWith('.svelte')) out.push(full);
    }
    return out;
}

/** The text of each `<DataTable …>` opening tag: from `<DataTable` to the `>` that closes it (braces and quotes balanced). */
function dataTableTags(text: string): {tag: string; line: number}[] {
    const tags: {tag: string; line: number}[] = [];
    let from = text.indexOf('<DataTable');
    while (from !== -1) {
        const next = text[from + '<DataTable'.length];
        if (next === undefined || /[\s/>]/.test(next)) {
            let depth = 0;
            let quote = '';
            let end = from;
            for (; end < text.length; end++) {
                const c = text[end];
                if (quote) {
                    if (c === quote) quote = '';
                } else if (depth === 0 && (c === '"' || c === "'")) quote = c;
                else if (c === '{') depth++;
                else if (c === '}') depth--;
                else if (c === '>' && depth === 0) break;
            }
            tags.push({tag: text.slice(from, end + 1), line: text.slice(0, from).split('\n').length});
        }
        from = text.indexOf('<DataTable', from + 1);
    }
    return tags;
}

/** The attribute's value text (`{false}`, `{phone.current}`), `''` for a bare attribute, `null` when it is not there. */
function attribute(tag: string, name: string): string | null {
    const match = new RegExp(`(?<![\\w-])${name}(?:\\s*=\\s*(\\{[^\\n]*?\\}|"[^"]*"|'[^']*'))?(?=[\\s/>}])`).exec(tag);
    if (!match) return null;
    return match[1] ?? '';
}

/** `file:line` for each `<DataTable>` with row actions whose right click is off or follows the phone. */
function findSwitchedOff(text: string, label: string): string[] {
    const hits: string[] = [];
    for (const {tag, line} of dataTableTags(text)) {
        if (attribute(tag, 'rowActions') === null) continue;
        const value = attribute(tag, 'enableContextMenu');
        if (value === null) continue;
        if (/^\{\s*false\s*\}$/.test(value) || /\bphone\b/.test(value)) hits.push(`${label}:${line}  enableContextMenu${value ? `=${value}` : ''}`);
    }
    return hits;
}

describe('every table row with a ⋮ opens its menu on a right click (81 U15)', () => {
    it('the scanner flags a table that switches the menu off or ties it to the phone', () => {
        const sample = ['<DataTable data={rows} rowActions={actions} enableContextMenu={false} />', '<DataTable', '    data={rows}', '    enableContextMenu={phone.current}', '    {rowActions}', '/>', '<DataTable rowActions={a} onclick={() => x > 1} enableContextMenu={ false } />'].join('\n');
        expect(findSwitchedOff(sample, 's').map((h) => h.split('  ')[0])).toEqual(['s:1', 's:2', 's:7']);
    });

    it('the scanner leaves alone a table without actions, a default, `true` and a non-phone expression', () => {
        const sample = [
            '<DataTable data={rows} enableContextMenu={false} />',
            '<DataTable data={rows} rowActions={a} />',
            '<DataTable data={rows} rowActions={a} enableContextMenu />',
            '<DataTable data={rows} rowActions={a} enableContextMenu={true} />',
            '<DataTable data={rows} rowActions={compact ? [] : a} enableContextMenu={!compact} />',
        ].join('\n');
        expect(findSwitchedOff(sample, 's')).toEqual([]);
    });

    it('no DataTable in the app switches the right-click menu off where it shows the ⋮', () => {
        const hits = walk(LIB).flatMap((file) => {
            const label = relative(LIB, file).split(sep).join('/');
            return findSwitchedOff(readFileSync(file, 'utf8'), label);
        });
        const allowed = hits.filter((h) => EXCEPTIONS.some((e) => h.startsWith(`${e.split(':')[0]}:`)));
        expect(hits.filter((h) => !allowed.includes(h))).toEqual([]);
    });
});
