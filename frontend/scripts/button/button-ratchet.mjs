#!/usr/bin/env node
// @ts-check
/**
 * Button ratchet — the scanner behind the standard-button gate (project 85, BTN-0, `src/button.gate.test.ts`).
 *
 * The app moves, area by area, from hand-written `<button>` elements to the standard `Button`
 * (`src/lib/components/ui/button/`). This module counts what is left of the old way and keeps the ratchet's
 * baseline; the gate calls it, and so does the command line at the bottom.
 *
 * Measured in every production source of frontend/src (the same files the colour gates read: `isProductionSource` of
 * theme-roles.mjs — not the tests, the mocks, the generated API, the Designer Lab), never inside a comment:
 *   - a `.svelte` file: its `<button>` elements, read from the Svelte compiler's own AST, plus the `<button` written
 *     inside the string literals of its `<script>` blocks (buttons built as HTML for a table cell). A `<button>` whose
 *     `role` is written as one of OTHER_ROLES does not count (BTN-2·0, C11): a control of another kind — an option, a
 *     tab, a menu item, a switch — keeps its own markup and keyboard by contract. The AST reads the whole opening tag,
 *     on as many lines as it takes; a computed `role={…}`, `role="button"` or a role outside the list still counts;
 *   - a `.ts` / `.js` file: the `<button` inside its string literals.
 *
 * The ratchet, against BASELINE (one line per file, `<path under src> TAB <count>[ TAB <reason>]`):
 *   B1  a file never rises above its line (absent: 0), plus its EXCEPTIONS allowance: a new hand-written button fails;
 *   B2  a drop passes and is reported; `--update` tightens the baseline to it and never widens it;
 *   B3  a moved or split file is declared: `--move OLD NEW` carries the record; `--accept FILE --reason R` takes a file
 *       as it is (only with the release coordinator's OK — the lane that owns the area brings it back down).
 * And on every `<Button>` / `<CloseButton>`:
 *   B4  its `class` carries size and position only, never a colour utility: the colours live in buttonClasses(), and
 *       the colour gate cannot see a class passed as a property.
 *
 * Command line, from any directory:
 *   node frontend/scripts/button/button-ratchet.mjs --report                 the count per file and the verdict
 *   node frontend/scripts/button/button-ratchet.mjs --check                  the gate's verdict; exit 1 on a violation
 *   node frontend/scripts/button/button-ratchet.mjs --update                 tighten the baseline to what dropped
 *   node frontend/scripts/button/button-ratchet.mjs --move OLD NEW           carry OLD's record to NEW (a move or split)
 *   node frontend/scripts/button/button-ratchet.mjs --accept FILE --reason R take FILE as it is (coordinator's OK)
 *   node frontend/scripts/button/button-ratchet.mjs --init                   write the first baseline
 */

import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parse} from 'svelte/compiler';
import {blankScriptComments, listSources, SRC_DIR, stringLiterals} from '../theme/theme-roles.mjs';

export {SRC_DIR};
export const BASELINE = join(SRC_DIR, 'button.baseline.tsv');

/**
 * The `<button>` elements that stay hand-written for good, each with its reason. A count per file: the file's other
 * buttons still move to `Button`.
 * @type {{file: string, count: number, reason: string}[]}
 */
export const EXCEPTIONS = [
    {file: 'lib/components/ui/button/Button.svelte', count: 1, reason: 'the standard button itself'},
    {file: 'lib/components/table/DataTableColumnHeader.svelte', count: 1, reason: 'the ⓘ of a table header: an information icon, tap = explanation, long press = guide (Q-BTN-3)'},
    {file: 'lib/features/tools/pac-allocator/planner/shared/HelpTip.svelte', count: 1, reason: 'an information icon: no action, tap = explanation (Q-BTN-3)'},
    {
        file: 'lib/components/ui/date/CalendarMonth.svelte',
        count: 1,
        reason: 'the day of a month: a cell of the calendar, a control of its own; no ARIA grid around it, so no gridcell (BTN-2·0, C11)',
    },
];

/**
 * The roles of a control that is not a button (BTN-2·0, C11): written literally on a `<button>`, they take it out of the
 * count. A closed list: anything else, `button` included, counts.
 */
export const OTHER_ROLES = new Set(['option', 'tab', 'menuitem', 'menuitemcheckbox', 'menuitemradio', 'treeitem', 'radio', 'checkbox', 'switch', 'combobox']);

/** The literal `role` of an element of the AST, or null when it has none or it is computed. */
function literalRole(/** @type {AstNode} */ node) {
    for (const attribute of /** @type {AstNode[]} */ (node.attributes ?? [])) {
        if (attribute.type !== 'Attribute' || attribute.name !== 'role') continue;
        const value = /** @type {unknown} */ (attribute.value);
        if (!Array.isArray(value) || value.length !== 1) return null;
        const [part] = value;
        return isNode(part) && part.type === 'Text' ? String(part.data ?? '').trim() : null;
    }
    return null;
}

const HTML_BUTTON_RE = /<button\b/g;

/** The `<button` written inside the string literals of script code (comments already blanked). */
function htmlButtonsIn(/** @type {string} */ code) {
    let count = 0;
    for (const {value} of stringLiterals(code)) count += (value.match(HTML_BUTTON_RE) ?? []).length;
    return count;
}

const SCRIPT_BODY_RE = /<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi;

/**
 * @typedef {Record<string, unknown> & {type: string, start?: number, end?: number, name?: string}} AstNode
 */

/** @returns {value is AstNode} */
function isNode(/** @type {unknown} */ value) {
    return value !== null && typeof value === 'object' && typeof (/** @type {{type?: unknown}} */ (value).type) === 'string';
}

/**
 * Every node of a Svelte AST.
 * @param {unknown} root
 * @param {WeakSet<object>} [seen]
 * @returns {Generator<AstNode>}
 */
function* nodes(root, seen = new WeakSet()) {
    if (root === null || typeof root !== 'object' || seen.has(root)) return;
    seen.add(root);
    if (isNode(root)) yield root;
    for (const child of Array.isArray(root) ? root : Object.values(root)) yield* nodes(child, seen);
}

/** A colour utility, any variants before it: a role, an arbitrary value, a palette colour with its shade, white/black. */
const COLOUR_CLASS_RE = /(?<![\w-])(?:[\w-]+:)*(?:bg|text|border(?:-[trblxy])?|ring|outline|fill|stroke|shadow|divide|from|via|to|placeholder|decoration|accent|caret)-(?:lf-|\[|(?:white|black|transparent|current)(?![\w-])|[a-z]+-\d)/;

/**
 * Measures one source.
 * @param {string} rel  path under src, POSIX
 * @param {string} text the file's content
 * @returns {{count: number, lines: number[], colourClasses: {line: number, value: string}[]}}
 */
export function measureSource(rel, text) {
    /** @type {number[]} */
    const lines = [];
    /** @type {{line: number, value: string}[]} */
    const colourClasses = [];
    let count = 0;
    if (rel.endsWith('.svelte')) {
        const ast = parse(text, {modern: true});
        for (const node of nodes(ast)) {
            if (node.start === undefined) continue;
            if (node.type === 'RegularElement' && node.name === 'button') {
                if (OTHER_ROLES.has(literalRole(node) ?? '')) continue;
                count += 1;
                lines.push(text.slice(0, node.start).split('\n').length);
            }
            if (node.type === 'Component' && (node.name === 'Button' || node.name === 'CloseButton')) {
                for (const attribute of /** @type {AstNode[]} */ (node.attributes ?? [])) {
                    if (attribute.type !== 'Attribute' || attribute.name !== 'class' || attribute.start === undefined) continue;
                    const source = text.slice(attribute.start, attribute.end);
                    const hit = source.match(COLOUR_CLASS_RE);
                    if (hit) colourClasses.push({line: text.slice(0, attribute.start).split('\n').length, value: hit[0]});
                }
            }
        }
        for (const match of text.matchAll(SCRIPT_BODY_RE)) {
            const html = htmlButtonsIn(blankScriptComments(match[1]));
            count += html;
            if (html > 0) lines.push(text.slice(0, match.index).split('\n').length);
        }
    } else {
        count = htmlButtonsIn(blankScriptComments(text));
    }
    return {count, lines, colourClasses};
}

/**
 * @typedef {{count: number, reason?: string}} BaselineLine
 * @typedef {Map<string, BaselineLine>} Baseline
 * @typedef {Map<string, {count: number, lines: number[], colourClasses: {line: number, value: string}[]}>} Scan
 */

/** Every production source with at least one hand-written button or one colour class on a Button. */
export function scanTree(srcDir = SRC_DIR) {
    /** @type {Scan} */
    const scan = new Map();
    for (const rel of listSources(srcDir)) {
        const text = readFileSync(join(srcDir, rel), 'utf8');
        if (!text.includes('<button') && !text.includes('Button')) continue;
        const measure = measureSource(rel, text);
        if (measure.count > 0 || measure.colourClasses.length > 0) scan.set(rel, measure);
    }
    return scan;
}

/** The allowance of EXCEPTIONS for one file. */
export function allowanceOf(/** @type {string} */ rel) {
    return EXCEPTIONS.filter((entry) => entry.file === rel).reduce((sum, entry) => sum + entry.count, 0);
}

export function parseBaseline(/** @type {string} */ text) {
    /** @type {Baseline} */
    const baseline = new Map();
    for (const raw of text.split('\n')) {
        if (!raw.trim() || raw.startsWith('#')) continue;
        const [file, count, reason] = raw.split('\t');
        baseline.set(file, {count: Number(count), ...(reason ? {reason} : {})});
    }
    return baseline;
}

const HEADER = [
    '# Standard-button ratchet baseline (project 85): the hand-written <button> left in each production source of frontend/src.',
    '# One line per file: <path under src> TAB <count> [TAB <reason, for a file taken as it is>]. Counts only go down.',
    '# Written only by `node frontend/scripts/button/button-ratchet.mjs` (--init, --update, --move, --accept).',
    '# Merge conflict: for each file keep the lower count, then run the gate on the merged tree. Never raise a line to pass.',
];

export function formatBaseline(/** @type {Baseline} */ baseline) {
    const files = [...baseline.keys()].sort();
    const body = files.map((file) => {
        const line = /** @type {BaselineLine} */ (baseline.get(file));
        return line.reason ? `${file}\t${line.count}\t${line.reason}` : `${file}\t${line.count}`;
    });
    return `${[...HEADER, ...body].join('\n')}\n`;
}

export function readBaseline(path = BASELINE) {
    return existsSync(path) ? parseBaseline(readFileSync(path, 'utf8')) : new Map();
}

export function writeBaseline(/** @type {Baseline} */ baseline, path = BASELINE) {
    writeFileSync(path, formatBaseline(baseline));
}

/** The baseline the tree has now: each file's count beyond its exception allowance. */
export function baselineOf(/** @type {Scan} */ scan) {
    /** @type {Baseline} */
    const baseline = new Map();
    for (const [rel, measure] of scan) {
        const over = measure.count - allowanceOf(rel);
        if (over > 0) baseline.set(rel, {count: over});
    }
    return baseline;
}

/**
 * The verdict: the rises (B1), the drops (B2), the colour classes on a Button (B4).
 * @param {Scan} scan
 * @param {Baseline} baseline
 */
export function compareWithBaseline(scan, baseline) {
    /** @type {{file: string, count: number, allowed: number, lines: number[]}[]} */
    const rises = [];
    /** @type {{file: string, count: number, recorded: number}[]} */
    const drops = [];
    /** @type {{file: string, line: number, value: string}[]} */
    const colours = [];
    for (const [rel, measure] of scan) {
        const allowed = (baseline.get(rel)?.count ?? 0) + allowanceOf(rel);
        if (measure.count > allowed) rises.push({file: rel, count: measure.count, allowed, lines: measure.lines});
        for (const hit of measure.colourClasses) colours.push({file: rel, ...hit});
    }
    for (const [rel, line] of baseline) {
        const count = Math.max(0, (scan.get(rel)?.count ?? 0) - allowanceOf(rel));
        if (count < line.count) drops.push({file: rel, count, recorded: line.count});
    }
    return {rises, drops, colours};
}

/** The baseline tightened to the drops; never widened. */
export function tightenBaseline(/** @type {Scan} */ scan, /** @type {Baseline} */ baseline) {
    /** @type {Baseline} */
    const next = new Map();
    for (const [rel, line] of baseline) {
        const count = Math.max(0, (scan.get(rel)?.count ?? 0) - allowanceOf(rel));
        const kept = Math.min(count, line.count);
        if (kept > 0) next.set(rel, {...line, count: kept});
    }
    return next;
}

function main(/** @type {string[]} */ argv) {
    const scan = scanTree();
    const baseline = readBaseline();
    const flag = argv[0];
    if (flag === '--init') {
        writeBaseline(baselineOf(scan));
        console.log(`baseline written: ${baselineOf(scan).size} files`);
        return 0;
    }
    if (flag === '--update') {
        writeBaseline(tightenBaseline(scan, baseline));
        console.log('baseline tightened');
        return 0;
    }
    if (flag === '--move') {
        const [from, to] = argv.slice(1);
        const line = baseline.get(from);
        if (!from || !to || !line) {
            console.error('usage: --move OLD NEW (OLD must have a baseline line)');
            return 2;
        }
        baseline.delete(from);
        baseline.set(to, {count: (baseline.get(to)?.count ?? 0) + line.count, ...(line.reason ? {reason: line.reason} : {})});
        writeBaseline(baseline);
        return 0;
    }
    if (flag === '--accept') {
        const file = argv[1];
        const reasonAt = argv.indexOf('--reason');
        const reason = reasonAt > 0 ? argv[reasonAt + 1] : '';
        if (!file || !reason) {
            console.error('usage: --accept FILE --reason "why" (with the release coordinator\'s OK)');
            return 2;
        }
        const count = Math.max(0, (scan.get(file)?.count ?? 0) - allowanceOf(file));
        baseline.set(file, {count, reason});
        writeBaseline(baseline);
        return 0;
    }
    const {rises, drops, colours} = compareWithBaseline(scan, baseline);
    if (flag === '--report') {
        const total = [...scan.values()].reduce((sum, measure) => sum + measure.count, 0);
        console.log(`hand-written buttons: ${total} in ${scan.size} files`);
    }
    for (const drop of drops) console.log(`dropped: ${drop.file} ${drop.recorded} → ${drop.count} (run --update)`);
    for (const rise of rises) console.error(`RISE: ${rise.file} has ${rise.count} hand-written <button>, allowed ${rise.allowed} (lines ${rise.lines.join(', ')}): use Button`);
    for (const hit of colours) console.error(`COLOUR: ${hit.file}:${hit.line} «${hit.value}» in the class of a Button: colours live in buttonClasses()`);
    return rises.length > 0 || colours.length > 0 ? 1 : 0;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) process.exit(main(process.argv.slice(2)));
