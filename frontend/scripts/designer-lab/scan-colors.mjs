#!/usr/bin/env node
/**
 * Designer Lab — colour scanner: builds the `lf-color-catalog/1` catalogue of `frontend/src`.
 *
 * Debug-only tooling (`LibreFolio_developer_journal/Release_2/Phase_0/55_colorSystem/design-designerLab.md`). Three
 * callers: the Vite plugin of the debug builds (`vite-plugin.mjs`), this file as a CLI, and Vitest.
 *
 *     node frontend/scripts/designer-lab/scan-colors.mjs [--out catalog.json] [--pretty] [--summary] [--root <frontend>]
 *
 * Two layers, on purpose:
 *   1. **Counting** mirrors `scripts/visual_review/color_inventory.py` — same file selection, same regular
 *      expressions, line by line — so the two inventories give the same numbers (`meta.parity`). Change one, change
 *      the other.
 *   2. **Annotation** then gives every hand-written colour of production code what the Lab and the agent need: the
 *      zone it lives in, the CSS selector and property, a theme hint, the live-preview layer, and `file:line:col`.
 *
 * The Lab's own sources are not scanned: they are tooling, not the app.
 */

import {createHash} from 'node:crypto';
import {existsSync, readdirSync, readFileSync, writeFileSync} from 'node:fs';
import {dirname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {colorKey, parseColor} from '../../src/lib/dev/designer-lab/color.js';

export const CATALOG_SCHEMA = 'lf-color-catalog/1';

/** `frontend/`, the directory every path of the catalogue is relative to. */
export const FRONTEND_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');

/** The Lab's own sources: tooling, never part of the catalogue (nor of the Python inventory). */
export const LAB_DIRS = ['src/lib/dev/designer-lab/', 'src/routes/designer-lab/'];

/** Documents outside the bundle whose colours the Lab can only propose (layer `static`, no preview). */
export const STATIC_SOURCES = ['src/app.html', 'static/offline.html', 'static/manifest.json'];

// ---------------------------------------------------------------------------------------------------------------
// Counting — a mirror of scripts/visual_review/color_inventory.py
// ---------------------------------------------------------------------------------------------------------------

const EXTS = new Set(['.svelte', '.ts', '.js', '.css']);
const FAMILIES = 'slate gray zinc neutral stone red orange amber yellow lime green emerald teal cyan sky blue indigo violet purple fuchsia pink rose'.split(' ');
const PREFIXES = 'bg text border border-t border-b border-l border-r border-x border-y ring ring-offset outline divide from via to fill stroke shadow accent caret decoration placeholder'.split(' ');
const PREFIX_ALT = [...PREFIXES].sort((a, b) => b.length - a.length).join('|');

const TW_RE = new RegExp(`(?<![\\w-])((?:[a-z0-9-]+:)*)(${PREFIX_ALT})-(${FAMILIES.join('|')})-(50|100|200|300|400|500|600|700|800|900|950)(/\\d{1,3}|/\\[[^\\]]+\\])?(?![\\w-])`, 'g');
const TW_BW_RE = /(?<![\w-])((?:[a-z0-9-]+:)*)(bg|text|border|ring|fill|stroke|from|to|via)-(white|black|transparent|current)(\/\d{1,3})?(?![\w-])/g;
const TW_CUSTOM_RE = /(?<![\w-])((?:[a-z0-9-]+:)*)(bg|text|border|ring|fill|stroke|from|to|via|outline|divide)-(libre-[a-z-]+|theme-[a-z-]+|primary[a-z-]*|accent[a-z-]*)(\/\d{1,3})?(?![\w-])/g;
const TW_ARBITRARY_RE = /(?<![\w-])((?:[a-z0-9-]+:)*)(bg|text|border|ring|fill|stroke|from|to|via|outline|divide|shadow)-\[([^\]]*(?:#|rgb|hsl|var\(|oklch)[^\]]*)\]/g;
const HEX_RE = /(?<![\w&])#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g;
const FUNC_RE = /\b(rgba?|hsla?|oklch|color-mix)\(([^()]*(?:\([^()]*\)[^()]*)*)\)/g;
const VAR_USE_RE = /var\(\s*(--[\w-]+)/g;
const VAR_DEF_RE = /^\s*(--[\w-]+)\s*:\s*([^;]+);/gm;

/** @param {string} path a `frontend/`-relative POSIX path */
export const isTestPath = (path) => path.includes('__tests__') || path.includes('__mocks__') || path.includes('.test.') || path.includes('.spec.');

/** @param {string} name */
const isGeneratedName = (name) => name.startsWith('generated') || name.includes('openapi') || name.includes('tool-contract-map');

/** @param {string} path */
const isLabPath = (path) => LAB_DIRS.some((dir) => path.startsWith(dir));

/**
 * The source files the inventory reads: `.svelte`, `.ts`, `.js`, `.css` under `src/`, outside `node_modules`, minus
 * the generated API clients and the Lab's own folders. Sorted, `frontend/`-relative.
 * @param {string} root the `frontend/` directory
 * @returns {string[]}
 */
export function listSourceFiles(root = FRONTEND_DIR) {
    /** @type {string[]} */
    const out = [];
    /** @param {string} dir */
    const walk = (dir) => {
        for (const entry of readdirSync(dir, {withFileTypes: true})) {
            if (entry.name === 'node_modules') continue;
            const full = join(dir, entry.name);
            if (entry.isDirectory()) walk(full);
            else if (entry.isFile()) {
                const dot = entry.name.lastIndexOf('.');
                if (dot < 0 || !EXTS.has(entry.name.slice(dot)) || isGeneratedName(entry.name)) continue;
                const rel = relative(root, full).split('\\').join('/');
                if (!isLabPath(rel)) out.push(rel);
            }
        }
    };
    walk(join(root, 'src'));
    return out.sort();
}

// ---------------------------------------------------------------------------------------------------------------
// Annotation helpers
// ---------------------------------------------------------------------------------------------------------------

/** @typedef {'svelte-script' | 'svelte-style' | 'svelte-markup' | 'css-file' | 'ts' | 'static'} Zone */
/** @typedef {'css-literal' | 'chart-color' | 'script' | 'markup' | 'static'} Layer */
/** @typedef {{start: number, end: number, prelude: string, parent: CssBlock | null}} CssBlock */

const CHART_PATH_RE = /\/(components\/(charts|dashboard|risk|brokers\/lots)|charts|features\/tools\/pac-allocator\/planner\/result)\/|chart[^/]*$/i;
// Selectors that define a variable for the whole page, so the Lab overrides it on `<html>` (L1) instead of rewriting
// the rule. Same list as ROOT_SELECTOR in src/lib/dev/designer-lab/engine/stylesheets.ts (plus `@theme`, which only the
// sources have): change both together.
const ROOT_SELECTOR_RE = /^(:root|html|:host|@theme|html\.(light|dark)|\.dark|\.light|html:not\(\.(dark|light)\))$/;

/**
 * The `<script>` and `<style>` regions of a `.svelte` file; the rest is markup.
 * @param {string} text
 * @returns {{kind: 'script' | 'style', start: number, end: number}[]}
 */
function svelteRegions(text) {
    const regions = [];
    for (const m of text.matchAll(/<(script|style)\b[^>]*>([\s\S]*?)<\/\1\s*>/g)) {
        const start = /** @type {number} */ (m.index) + m[0].indexOf('>') + 1;
        regions.push({kind: /** @type {'script' | 'style'} */ (m[1]), start, end: start + m[2].length});
    }
    return regions;
}

/**
 * The blocks of a CSS text between `from` and `to` (comments and strings skipped), each with its prelude — the
 * selector or at-rule written before its `{` — and its parent block.
 * @param {string} text
 * @param {number} from
 * @param {number} to
 * @returns {CssBlock[]}
 */
function cssBlocks(text, from, to) {
    /** @type {CssBlock[]} */
    const blocks = [];
    /** @type {CssBlock[]} */
    const stack = [];
    let segment = from;
    for (let i = from; i < to; i++) {
        const ch = text[i];
        if (ch === '/' && text[i + 1] === '*') {
            const end = text.indexOf('*/', i + 2);
            i = end === -1 ? to : end + 1;
            continue;
        }
        if (ch === '"' || ch === "'") {
            let j = i + 1;
            while (j < to && text[j] !== ch) j += text[j] === '\\' ? 2 : 1;
            i = j;
            continue;
        }
        if (ch === '{') {
            const prelude = text
                .slice(segment, i)
                .replace(/\/\*[\s\S]*?\*\//g, '')
                .replace(/\s+/g, ' ')
                .trim();
            stack.push({start: i, end: to, prelude, parent: stack[stack.length - 1] ?? null});
            segment = i + 1;
        } else if (ch === '}') {
            const block = stack.pop();
            if (block) {
                block.end = i;
                blocks.push(block);
            }
            segment = i + 1;
        } else if (ch === ';') {
            segment = i + 1;
        }
    }
    for (const open of stack) blocks.push(open);
    return blocks;
}

/**
 * Selector, at-rules, property and theme context of a CSS offset.
 * @param {string} text
 * @param {CssBlock[]} blocks
 * @param {number} offset
 */
function cssContext(text, blocks, offset) {
    /** @type {CssBlock | null} */
    let inner = null;
    for (const b of blocks) if (b.start < offset && offset < b.end && (!inner || b.start > inner.start)) inner = b;
    if (!inner) return {selector: null, at: [], property: null, theme: 'both'};
    const chain = [];
    for (let b = /** @type {CssBlock | null} */ (inner); b; b = b.parent) chain.unshift(b.prelude);
    const at = chain.filter((p) => p.startsWith('@') && p !== '@theme');
    const selectors = chain.filter((p) => !p.startsWith('@') || p === '@theme');
    const selector = selectors.length ? selectors.join(' ') : null;
    let start = offset;
    while (start > inner.start && !';{}'.includes(text[start - 1])) start--;
    const declaration = text.slice(start, offset);
    const colon = declaration.indexOf(':');
    const property =
        colon > 0
            ? declaration
                  .slice(0, colon)
                  .replace(/\/\*[\s\S]*?\*\//g, '')
                  .trim() || null
            : null;
    return {selector, at, property, theme: themeOfChain(chain)};
}

/**
 * The theme one selector restricts its rule to: `dark` for `.dark` (or `:not(.light)`), `light` for `.light` (or
 * `:not(.dark)`, as in `html:not(.dark)`), `both` otherwise.
 * @param {string} selector
 * @returns {'light' | 'dark' | 'both'}
 */
function selectorTheme(selector) {
    const s = selector.replace(/:not\(\s*\.dark\s*\)/g, ':not-dark').replace(/:not\(\s*\.light\s*\)/g, ':not-light');
    if (/\.dark\b/.test(s) || s.includes(':not-light')) return 'dark';
    if (/\.light\b/.test(s) || s.includes(':not-dark')) return 'light';
    return 'both';
}

/**
 * `dark` or `light` when a level of the chain restricts the rule to that theme — every selector of the level names
 * it, or a `prefers-color-scheme` media query does — `both` otherwise. A level listing selectors of different themes
 * (`.a, html.dark .b`) applies in both, so it fixes nothing.
 * @param {string[]} chain
 * @returns {'light' | 'dark' | 'both'}
 */
function themeOfChain(chain) {
    /** @type {'light' | 'dark' | 'both'} */
    let theme = 'both';
    for (const prelude of chain) {
        if (prelude.startsWith('@')) {
            const media = /prefers-color-scheme:\s*(dark|light)/.exec(prelude);
            if (media) theme = /** @type {'light' | 'dark'} */ (media[1]);
            continue;
        }
        const themes = new Set(
            prelude
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean)
                .map(selectorTheme),
        );
        if (themes.size === 1 && !themes.has('both')) theme = /** @type {'light' | 'dark'} */ ([...themes][0]);
    }
    return theme;
}

/** A condition naming the dark theme at the end of a line (`isDark`, `!dark`, `this.isDark()`, `(isDark)`). */
const DARK_CONDITION_AT_END = /(!?)\s*\b[\w.$]*(?:dark|Dark|DARK)[\w.$]*(?:\(\))?\)*\s*$/;

/**
 * A theme hint for a colour written in a script: an object key (`dark: '#…'`), or the side of a ternary whose
 * condition names the dark theme — `isDark ? '#dark' : '#light'` on one line, or split over lines as Prettier writes
 * it (`isDark` / `? '#dark'` / `: '#light'`). A hint, not a fact: names and conditions can mislead.
 * @param {string[]} lines
 * @param {number} lineIndex 0-based
 * @param {number} col 0-based column of the literal
 * @returns {'light' | 'dark' | null}
 */
function scriptThemeHint(lines, lineIndex, col) {
    const line = lines[lineIndex];
    const before = line.slice(0, col);
    const key = /\b(dark|light)\w*['"]?\s*[:=]\s*['"`]?$/i.exec(before);
    if (key) return key[1].toLowerCase() === 'dark' ? 'dark' : 'light';
    for (const m of line.matchAll(/(!?)\s*\b[\w.]*(?:dark|Dark|DARK)[\w.]*(?:\(\))?\s*\?/g)) {
        const q = /** @type {number} */ (m.index) + m[0].length - 1;
        if (q >= col) break;
        const colon = ternaryColon(line, q + 1);
        if (colon === -1) continue;
        const consequent = col < colon;
        const negated = m[1] === '!';
        return consequent !== negated ? 'dark' : 'light';
    }
    const lead = line.trimStart()[0];
    if (lead !== '?' && lead !== ':') return null;
    // A branch on its own line: the `?` line is this one, or for a `:` line the nearest `?` line above it.
    let question = lineIndex;
    if (lead === ':') {
        question = -1;
        for (let i = lineIndex - 1; i >= Math.max(0, lineIndex - 8); i--) {
            const t = lines[i].trimStart();
            if (t.startsWith('?')) {
                question = i;
                break;
            }
            if (t.startsWith(':')) break;
        }
    }
    let condition = question - 1;
    while (condition >= 0 && lines[condition].trim() === '') condition--;
    if (question < 0 || condition < 0) return null;
    const m = DARK_CONDITION_AT_END.exec(lines[condition].replace(/\/\/.*$/, ''));
    if (!m) return null;
    return (lead === '?') !== (m[1] === '!') ? 'dark' : 'light';
}

/**
 * The `:` that closes the consequent of a ternary opened just before `from`, at depth 0 and outside strings.
 * @param {string} line
 * @param {number} from
 */
function ternaryColon(line, from) {
    let depth = 0;
    for (let i = from; i < line.length; i++) {
        const ch = line[i];
        if (ch === "'" || ch === '"' || ch === '`') {
            const close = line.indexOf(ch, i + 1);
            if (close === -1) return -1;
            i = close;
        } else if ('([{'.includes(ch)) depth++;
        else if (')]}'.includes(ch)) {
            if (depth === 0) return -1;
            depth--;
        } else if (ch === ':' && depth === 0) return i;
    }
    return -1;
}

/**
 * How a colour written in markup reaches the page: a Tailwind arbitrary class (compiled into a stylesheet, so it is
 * live-editable), an inline style, or other markup.
 * @param {string} line
 * @param {number} col
 * @returns {'tw-arbitrary' | 'style-attr' | 'markup'}
 */
function markupVia(line, col) {
    for (const m of line.matchAll(TW_ARBITRARY_RE)) {
        const start = /** @type {number} */ (m.index);
        if (start <= col && col < start + m[0].length) return 'tw-arbitrary';
    }
    return /\bstyle(?::[\w-]+)?\s*=/.test(line.slice(0, col)) ? 'style-attr' : 'markup';
}

/**
 * @param {Zone} zone
 * @param {boolean} chartFile
 * @param {'tw-arbitrary' | 'style-attr' | 'markup' | null} via
 * @returns {Layer}
 */
function layerOf(zone, chartFile, via) {
    if (zone === 'css-file' || zone === 'svelte-style') return 'css-literal';
    if (zone === 'svelte-markup') return via === 'tw-arbitrary' ? 'css-literal' : 'markup';
    if (zone === 'static') return 'static';
    return chartFile ? 'chart-color' : 'script';
}

/** @param {string} text */
function lineStarts(text) {
    const starts = [0];
    for (let i = 0; i < text.length; i++) if (text[i] === '\n') starts.push(i + 1);
    return starts;
}

/**
 * @param {number[]} starts
 * @param {number} offset
 */
function lineOf(starts, offset) {
    let lo = 0;
    let hi = starts.length - 1;
    while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (starts[mid] <= offset) lo = mid;
        else hi = mid - 1;
    }
    return lo;
}

/** @param {string} family @param {string} shade */
const paletteVar = (family, shade) => (shade ? `--color-${family}-${shade}` : family === 'white' || family === 'black' ? `--color-${family}` : null);

// ---------------------------------------------------------------------------------------------------------------
// One file
// ---------------------------------------------------------------------------------------------------------------

/**
 * @typedef {object} FileScan
 * @property {{tw: number, custom: number, arbitrary: number, hex: number, fn: number}} counts  matches in this file
 * @property {{name: string, line: number}[]} varUses
 * @property {{name: string, value: string, line: number, offset: number}[]} varDefs
 * @property {{raw: string, var: string | null, line: number, dark: boolean}[]} classes
 * @property {object[]} literals
 */

/**
 * Scan one source. `rel` decides the zone rules (`.svelte`, `.css`, script) and the chart hint.
 * @param {string} rel `frontend/`-relative path
 * @param {string} text
 * @param {{zoneOverride?: Zone}} [opts]
 * @returns {FileScan}
 */
export function scanSource(rel, text, opts = {}) {
    const isSvelte = rel.endsWith('.svelte');
    const isCss = rel.endsWith('.css');
    const chartFile = CHART_PATH_RE.test('/' + rel) || /from\s+['"]echarts['"]/.test(text);
    const starts = lineStarts(text);
    const lines = text.split('\n').map((l) => (l.endsWith('\r') ? l.slice(0, -1) : l));
    const regions = isSvelte ? svelteRegions(text) : [];
    /** @type {{start: number, end: number, blocks: CssBlock[]}[]} */
    const cssRegions = isCss ? [{start: 0, end: text.length, blocks: cssBlocks(text, 0, text.length)}] : regions.filter((r) => r.kind === 'style').map((r) => ({start: r.start, end: r.end, blocks: cssBlocks(text, r.start, r.end)}));

    /** @param {number} offset @returns {Zone} */
    const zoneAt = (offset) => {
        if (opts.zoneOverride) return opts.zoneOverride;
        if (isCss) return 'css-file';
        if (!isSvelte) return 'ts';
        const r = regions.find((x) => x.start <= offset && offset < x.end);
        return r ? (r.kind === 'style' ? 'svelte-style' : 'svelte-script') : 'svelte-markup';
    };

    const result = /** @type {FileScan} */ ({counts: {tw: 0, custom: 0, arbitrary: 0, hex: 0, fn: 0}, varUses: [], varDefs: [], classes: [], literals: []});

    /**
     * @param {RegExpMatchArray} m
     * @param {number} lineIndex
     * @param {'hex' | 'fn' | 'mix'} kind
     */
    const addLiteral = (m, lineIndex, kind) => {
        const col = /** @type {number} */ (m.index);
        const offset = starts[lineIndex] + col;
        const raw = m[0];
        const zone = zoneAt(offset);
        const rgba = kind === 'mix' ? null : parseColor(raw);
        /** @type {Record<string, unknown>} */
        const lit = {line: lineIndex + 1, col: col + 1, raw, kind, key: rgba ? colorKey(rgba) : null, alpha: rgba ? Math.round(rgba.alpha * 1000) / 1000 : null, zone, theme: null};
        if (zone === 'css-file' || zone === 'svelte-style') {
            const region = cssRegions.find((r) => r.start <= offset && offset < r.end);
            const ctx = region ? cssContext(text, region.blocks, offset) : null;
            if (ctx) {
                lit.selector = ctx.selector;
                if (ctx.at.length) lit.at = ctx.at;
                lit.property = ctx.property;
                lit.theme = ctx.theme;
            }
        } else if (zone === 'svelte-script' || zone === 'ts') {
            lit.theme = scriptThemeHint(lines, lineIndex, col);
            lit.chart = chartFile;
        } else if (zone === 'svelte-markup') {
            lit.via = markupVia(lines[lineIndex], col);
            // The `dark:` variant of the class holding the colour (`dark:bg-[#1e293b]`), never of a neighbouring class.
            let start = col;
            while (start > 0 && !/[\s"'`{}]/.test(lines[lineIndex][start - 1])) start--;
            lit.theme = /(^|:)dark:/.test(lines[lineIndex].slice(start, col)) ? 'dark' : null;
        }
        lit.layer = layerOf(zone, chartFile, /** @type {any} */ (lit.via ?? null));
        lit.preview = lit.layer === 'css-literal' || lit.layer === 'chart-color';
        lit.snippet = lines[lineIndex].trim().slice(0, 160);
        result.literals.push(lit);
    };

    lines.forEach((line, i) => {
        for (const m of line.matchAll(TW_RE)) {
            result.counts.tw++;
            result.classes.push({raw: m[0], var: paletteVar(m[3], m[4]), line: i + 1, dark: m[1].includes('dark:')});
        }
        for (const m of line.matchAll(TW_BW_RE)) {
            result.counts.tw++;
            result.classes.push({raw: m[0], var: paletteVar(m[3], ''), line: i + 1, dark: m[1].includes('dark:')});
        }
        for (const m of line.matchAll(TW_CUSTOM_RE)) {
            result.counts.custom++;
            result.classes.push({raw: m[0], var: `--color-${m[3]}`, line: i + 1, dark: m[1].includes('dark:')});
        }
        for (const _ of line.matchAll(TW_ARBITRARY_RE)) result.counts.arbitrary++;
        for (const m of line.matchAll(HEX_RE)) {
            result.counts.hex++;
            addLiteral(m, i, 'hex');
        }
        for (const m of line.matchAll(FUNC_RE)) {
            result.counts.fn++;
            addLiteral(m, i, m[1] === 'color-mix' ? 'mix' : 'fn');
        }
        for (const m of line.matchAll(VAR_USE_RE)) result.varUses.push({name: m[1], line: i + 1});
    });

    for (const m of text.matchAll(VAR_DEF_RE)) {
        const nameOffset = /** @type {number} */ (m.index) + m[0].indexOf(m[1]);
        result.varDefs.push({name: m[1], value: m[2].trim(), line: lineOf(starts, nameOffset) + 1, offset: nameOffset});
    }
    // Annotate the definitions with their rule, now that the CSS regions are known.
    for (const def of result.varDefs) {
        const region = cssRegions.find((r) => r.start <= def.offset && def.offset < r.end);
        const ctx = region ? cssContext(text, region.blocks, def.offset) : null;
        Object.assign(def, {zone: zoneAt(def.offset), selector: ctx?.selector ?? null, theme: ctx?.theme ?? null});
    }
    return result;
}

// ---------------------------------------------------------------------------------------------------------------
// The catalogue
// ---------------------------------------------------------------------------------------------------------------

/**
 * Whether a CSS variable defined by `selector` is inherited by the whole document (so the Lab can override it on
 * `<html>`) or scoped to a component (the Lab must rewrite the defining rule).
 * @param {string | null} selector
 */
function varScope(selector) {
    if (!selector) return 'scoped';
    return selector.split(',').every((s) => ROOT_SELECTOR_RE.test(s.trim())) ? 'root' : 'scoped';
}

/**
 * Build the catalogue of a `frontend/` tree.
 * @param {{root?: string, appVersion?: string, files?: string[]}} [opts]
 */
export function scanColors(opts = {}) {
    const root = opts.root ?? FRONTEND_DIR;
    const t0 = performance.now();
    const paths = opts.files ?? listSourceFiles(root);
    /** @type {string[]} */
    const files = [];
    /** @type {Map<string, number>} */
    const fileIndex = new Map();
    /** @param {string} rel */
    const idx = (rel) => {
        let i = fileIndex.get(rel);
        if (i === undefined) {
            i = files.length;
            files.push(rel);
            fileIndex.set(rel, i);
        }
        return i;
    };

    const parity = {files: paths.length, tw: 0, custom: 0, arbitrary: 0, hex: 0, fn: 0, var_uses: 0, var_uses_distinct: 0, var_defs: 0};
    /** @type {Set<string>} */
    const distinctUses = new Set();
    /** @type {Map<string, {var: string, uses: number, dark: number, classes: Record<string, number>, files: Record<string, number>, occ: number[][]}>} */
    const palette = new Map();
    /** @type {Map<string, {name: string, defs: object[], uses: number, files: Record<string, number>}>} */
    const cssVars = new Map();
    /** @type {object[]} */
    const literals = [];

    /** @param {string} name */
    const varEntry = (name) => {
        let v = cssVars.get(name);
        if (!v) {
            v = {name, defs: [], uses: 0, files: {}};
            cssVars.set(name, v);
        }
        return v;
    };

    for (const rel of paths) {
        let text;
        try {
            text = readFileSync(join(root, rel), 'utf8');
        } catch {
            continue;
        }
        const test = isTestPath(rel);
        const scan = scanSource(rel, text);
        parity.var_uses += scan.varUses.length;
        for (const u of scan.varUses) distinctUses.add(u.name);
        parity.var_defs += scan.varDefs.length;
        if (test) continue;
        parity.tw += scan.counts.tw;
        parity.custom += scan.counts.custom;
        parity.arbitrary += scan.counts.arbitrary;
        parity.hex += scan.counts.hex;
        parity.fn += scan.counts.fn;

        const f = idx(rel);
        for (const c of scan.classes) {
            if (!c.var) continue;
            let p = palette.get(c.var);
            if (!p) {
                p = {var: c.var, uses: 0, dark: 0, classes: {}, files: {}, occ: []};
                palette.set(c.var, p);
            }
            p.uses++;
            if (c.dark) p.dark++;
            p.classes[c.raw] = (p.classes[c.raw] ?? 0) + 1;
            p.files[f] = (p.files[f] ?? 0) + 1;
            p.occ.push([f, c.line]);
        }
        for (const u of scan.varUses) {
            const v = varEntry(u.name);
            v.uses++;
            v.files[f] = (v.files[f] ?? 0) + 1;
        }
        for (const d of scan.varDefs) {
            const {offset: _offset, ...def} = /** @type {any} */ (d);
            varEntry(d.name).defs.push({file: f, ...def, scope: varScope(def.selector)});
        }
        for (const lit of scan.literals) literals.push({file: f, ...lit});
    }
    parity.var_uses_distinct = distinctUses.size;

    for (const rel of STATIC_SOURCES) {
        const full = join(root, rel);
        if (!existsSync(full)) continue;
        const scan = scanSource(rel, readFileSync(full, 'utf8'), {zoneOverride: 'static'});
        const f = idx(rel);
        for (const lit of scan.literals) literals.push({file: f, ...lit});
    }

    literals.forEach((lit, i) => Object.assign(lit, {id: i}));
    /** @type {Record<string, number[]>} */
    const byValue = {};
    for (const lit of /** @type {{id: number, key: string | null}[]} */ (literals)) {
        if (lit.key) (byValue[lit.key] ??= []).push(lit.id);
    }

    const body = {
        files,
        css_vars: [...cssVars.values()].sort((a, b) => a.name.localeCompare(b.name)),
        palette: [...palette.values()].sort((a, b) => a.var.localeCompare(b.var)),
        literals,
        by_value: byValue,
    };
    const hash = 'sha256:' + createHash('sha256').update(JSON.stringify(body)).digest('hex');
    const layers = /** @type {Record<string, number>} */ ({});
    for (const lit of /** @type {{layer: string}[]} */ (literals)) layers[lit.layer] = (layers[lit.layer] ?? 0) + 1;
    return {
        meta: {
            schema: CATALOG_SCHEMA,
            app_version: opts.appVersion ?? 'unknown',
            generated_at: new Date().toISOString(),
            hash,
            scan_ms: Math.round(performance.now() - t0),
            parity,
            layers,
            excluded: LAB_DIRS,
        },
        ...body,
    };
}

// ---------------------------------------------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------------------------------------------

/** @param {string[]} argv */
function main(argv) {
    /** @param {string} flag */
    const value = (flag) => {
        const i = argv.indexOf(flag);
        return i === -1 ? undefined : argv[i + 1];
    };
    const catalog = scanColors({root: value('--root') ? resolve(/** @type {string} */ (value('--root'))) : FRONTEND_DIR, appVersion: value('--app-version')});
    const out = value('--out');
    if (out) writeFileSync(out, JSON.stringify(catalog, null, argv.includes('--pretty') ? 2 : 0));
    if (argv.includes('--summary') || !out) {
        const {meta} = catalog;
        console.log(
            JSON.stringify(
                {schema: meta.schema, hash: meta.hash, scan_ms: meta.scan_ms, parity: meta.parity, layers: meta.layers, literals: catalog.literals.length, palette_vars: catalog.palette.length, css_vars: catalog.css_vars.length, distinct_values: Object.keys(catalog.by_value).length},
                null,
                2,
            ),
        );
    }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main(process.argv.slice(2));
