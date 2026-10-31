/**
 * @vitest-environment node
 *
 * Native date input — a gate over the source, not a test of behaviour.
 *
 * `<input type="date">` is drawn by the browser, in the browser's language: an Italian app with an
 * English browser shows `mm/dd/yyyy` fields. The app's own `DateRangePicker` follows the app's
 * language, so every date a reader picks or types goes through it. The risk panel's historical
 * replay kept two native fields after the rest moved (T-DI, ondata 6).
 *
 * The rule: **no component renders an `<input>` whose `type` is the literal `date`.** The gate
 * reads the Svelte compiler's own AST, so a comment, a string or a dynamic `type={…}` is not a hit.
 */
import {describe, expect, it} from 'vitest';
import {readdirSync, readFileSync, statSync} from 'node:fs';
import {join, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse} from 'svelte/compiler';

const SRC = fileURLToPath(new URL('./', import.meta.url));

type Node = Record<string, unknown> & {type: string; start?: number};

function isNode(value: unknown): value is Node {
    return value !== null && typeof value === 'object' && typeof (value as {type?: unknown}).type === 'string';
}

function* nodes(root: unknown, seen: WeakSet<object> = new WeakSet()): Generator<Node> {
    if (root === null || typeof root !== 'object' || seen.has(root)) return;
    seen.add(root);
    if (isNode(root)) yield root;
    for (const child of Array.isArray(root) ? root : Object.values(root)) yield* nodes(child, seen);
}

/** The text of a static attribute, or `null` when it is absent, dynamic or valueless. */
function staticAttribute(element: Node, name: string): string | null {
    for (const attribute of (element.attributes as Node[]) ?? []) {
        if (attribute.type !== 'Attribute' || attribute.name !== name) continue;
        const value = attribute.value;
        if (Array.isArray(value) && value.length === 1 && isNode(value[0]) && value[0].type === 'Text') return value[0].data as string;
    }
    return null;
}

/** The 1-based lines of the native date inputs in one component's source. */
function nativeDateInputLines(source: string): number[] {
    const lines: number[] = [];
    for (const node of nodes(parse(source, {modern: true}))) {
        if (node.type !== 'RegularElement' || node.name !== 'input' || node.start === undefined) continue;
        if (staticAttribute(node, 'type') === 'date') lines.push(source.slice(0, node.start).split('\n').length);
    }
    return lines;
}

function svelteFiles(dir: string, acc: string[] = []): string[] {
    for (const entry of readdirSync(dir)) {
        const full = join(dir, entry);
        if (statSync(full).isDirectory()) {
            if (entry === 'node_modules' || entry === '__tests__' || entry === '__mocks__') continue;
            svelteFiles(full, acc);
        } else if (entry.endsWith('.svelte')) {
            acc.push(full);
        }
    }
    return acc;
}

describe('no native date input', () => {
    it('finds a literal type="date" input, and only that', () => {
        expect(nativeDateInputLines('<div>\n<input type="date" bind:value={d} />\n</div>')).toEqual([2]);
        expect(nativeDateInputLines('<input type="text" /><input type={kind} /><!-- <input type="date"> -->')).toEqual([]);
    });

    it('is absent from every component under src/', () => {
        const hits: string[] = [];
        for (const file of svelteFiles(SRC)) {
            for (const line of nativeDateInputLines(readFileSync(file, 'utf8'))) hits.push(`${relative(SRC, file)}:${line}`);
        }
        expect(hits, 'a native date input follows the browser language, not the app: use components/ui/date/DateRangePicker.svelte').toEqual([]);
        // It parses every component of the app: well over the default 5 s on a busy machine.
    }, 60_000);
});
