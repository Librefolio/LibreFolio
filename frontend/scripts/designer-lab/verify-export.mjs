#!/usr/bin/env node
/**
 * Designer Lab — verify an export against the code as it is now (`design-designerLab.md` §7).
 *
 *     node frontend/scripts/designer-lab/verify-export.mjs designer-lab-changes.json [--json] [--root <frontend>]
 *
 * For every occurrence the export lists, the value must still be written at its `file:line`. When it is not, the
 * file is searched for it: found elsewhere → `moved` (with the nearest new line), not found → `missing`. Variable
 * definitions are checked the same way, and a definition whose value changed since the export is reported. The
 * catalogue is rebuilt to compare its hash with the export's.
 *
 * A specialisation (`element`) lists candidates instead of occurrences — the places where the agent may bind it —
 * checked the same way but counted apart: a candidate that moved or disappeared is a hint, not an error, until none
 * is left (`lost`). The test ids of every anchor must still be written in the code (static, or the prefix of a
 * templated id).
 *
 * Exit code: 0 when nothing is missing (moved occurrences are fine), 1 when an occurrence is missing or a
 * specialisation lost all its candidates, 2 on bad input.
 */

import {existsSync, readFileSync} from 'node:fs';
import {join, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {categoryLines, FRONTEND_DIR, scanColors} from './scan-colors.mjs';

export const VERIFY_SCHEMA = 'lf-designer-lab-verify/1';

/**
 * @param {string} root
 * @returns {(file: string) => string[] | null}
 */
function fileReader(root) {
    const base = resolve(root);
    /** @type {Map<string, string[] | null>} */
    const cache = new Map();
    return (file) => {
        if (!cache.has(file)) {
            const full = resolve(join(base, String(file)));
            // An export is input: a path leaving the frontend is not read.
            const inside = full.startsWith(base + sep);
            cache.set(file, inside && existsSync(full) ? readFileSync(full, 'utf8').split('\n') : null);
        }
        return /** @type {string[] | null} */ (cache.get(file));
    };
}

/**
 * Whether the code still writes a test id: a static id, or a templated one — `prefix*` when the code still writes ids
 * that start with it (a templated id with that prefix or a shorter one, or static ids: the picker may have cut an id
 * the index did not know before a record-like token), or an id a known prefix produces.
 * @param {string} id
 * @param {{statics: Set<string>, prefixes: string[]}} index
 */
export function testidKnown(id, index) {
    if (id.endsWith('*')) {
        const prefix = id.slice(0, -1);
        if (!prefix) return false;
        if (index.prefixes.some((p) => prefix.startsWith(p))) return true;
        for (const s of index.statics) if (s.startsWith(prefix)) return true;
        return false;
    }
    return index.statics.has(id) || index.prefixes.some((p) => id.length > p.length && id.startsWith(p));
}

/**
 * Where `needle` stands in `lines` now: at `line` (1-based), or the nearest other line, or nowhere.
 * @param {string[]} lines
 * @param {number} line
 * @param {string} needle
 * @returns {{status: 'ok' | 'moved' | 'missing', line?: number}}
 */
export function locate(lines, line, needle) {
    const n = needle.toLowerCase();
    if (lines[line - 1]?.toLowerCase().includes(n)) return {status: 'ok', line};
    let best = -1;
    lines.forEach((text, i) => {
        if (text.toLowerCase().includes(n) && (best === -1 || Math.abs(i + 1 - line) < Math.abs(best - line))) best = i + 1;
    });
    return best === -1 ? {status: 'missing'} : {status: 'moved', line: best};
}

/**
 * Where a chart category's value stands now (`category` changes): its line found by key and theme in the tables of
 * `chartCategories.ts` (`categoryLines`), never by value — categories share values (`ETF` and `Technology`), and a
 * value search would land on another category's line. `ok` at the same line, `moved` to the line its key and theme are
 * written at now, `missing` when the key is gone or its line holds another value (the export's starting value is stale).
 * @param {string[]} lines
 * @param {{line: number, raw?: string, theme_context?: string | null}} occ
 * @param {string} target  `type:ETF`, `sector:Health Care`, `bucket:Liquidity`
 * @returns {{status: 'ok' | 'moved' | 'missing', line?: number}}
 */
export function locateCategory(lines, occ, target) {
    let line = -1;
    for (const [n, c] of categoryLines(lines.join('\n'))) {
        if (c.target === target && c.theme === occ.theme_context) {
            line = n;
            break;
        }
    }
    if (line === -1) return {status: 'missing'};
    if (occ.raw && !(lines[line - 1] ?? '').toLowerCase().includes(occ.raw.toLowerCase())) return {status: 'missing'};
    return line === occ.line ? {status: 'ok', line} : {status: 'moved', line};
}

/**
 * The text to look for at an occurrence: its literal, or for a Tailwind class use the `family-shade` of the variable.
 * @param {{raw?: string}} occ
 * @param {{layer: string, target: string}} change
 */
function needleOf(occ, change) {
    if (occ.raw) return occ.raw;
    if (change.layer === 'css-var') return change.target.replace(/^--color-/, '');
    return change.target;
}

/**
 * @param {any} doc a parsed export
 * @param {{root?: string, catalogHash?: string, testids?: {statics: string[], prefixes: string[]}}} [opts]  `catalogHash`
 *   and `testids` stand in for the catalogue (tests); without them the catalogue is rebuilt.
 */
export function verifyExport(doc, opts = {}) {
    const root = opts.root ?? FRONTEND_DIR;
    if (doc?.schema !== 'lf-designer-lab/1' || !Array.isArray(doc.changes)) throw new Error('not a lf-designer-lab/1 export');
    const read = fileReader(root);
    const anchored = doc.changes.some((/** @type {any} */ c) => c?.anchor);
    const catalog = !opts.catalogHash || (anchored && !opts.testids) ? scanColors({root}) : null;
    const catalogHash = opts.catalogHash ?? /** @type {NonNullable<typeof catalog>} */ (catalog).meta.hash;
    const ids = opts.testids ?? (catalog ? {statics: Object.keys(catalog.testids), prefixes: [...new Set(catalog.testid_prefixes.map((p) => p[0]))]} : null);
    const index = ids ? {statics: new Set(ids.statics), prefixes: ids.prefixes} : null;
    const totals = {changes: doc.changes.length, ok: 0, moved: 0, missing: 0, definitions_changed: 0, candidates_ok: 0, candidates_moved: 0, candidates_missing: 0, anchors_lost: 0, anchor_testids_missing: 0};
    const changes = /** @type {any[]} */ (doc.changes).map((/** @type {any} */ change) => {
        const element = change.layer === 'element';
        /** @type {{file: string, line: number, raw?: string, to_line?: number}[]} */
        const moved = [];
        /** @type {{file: string, line: number, raw?: string}[]} */
        const missing = [];
        let ok = 0;
        for (const occ of change.occurrences ?? []) {
            const lines = read(occ.file);
            const where = !lines ? /** @type {ReturnType<typeof locate>} */ ({status: 'missing'}) : change.layer === 'category' ? locateCategory(lines, occ, change.target) : locate(lines, occ.line, needleOf(occ, change));
            if (where.status === 'ok') ok++;
            else if (where.status === 'moved') moved.push({file: occ.file, line: occ.line, raw: occ.raw, to_line: where.line});
            else missing.push({file: occ.file, line: occ.line, raw: occ.raw});
        }
        /** @type {{file: string, line: number, status: string, to_line?: number, value_now?: string}[]} */
        const definitions = [];
        for (const def of change.definitions ?? []) {
            const lines = read(def.file);
            const where = lines ? locate(lines, def.line, `${change.target}:`) : /** @type {ReturnType<typeof locate>} */ ({status: 'missing'});
            const entry = {file: def.file, line: def.line, status: where.status, ...(where.line && where.status === 'moved' ? {to_line: where.line} : {})};
            const at = where.line ? lines?.[where.line - 1] : undefined;
            const value = at ? /:\s*([^;]+);?/.exec(at.slice(at.indexOf(`${change.target}:`)))?.[1]?.trim() : undefined;
            if (value !== undefined && value !== def.value) {
                Object.assign(entry, {value_now: value});
                totals.definitions_changed++;
            }
            definitions.push(entry);
        }
        totals.ok += element ? 0 : ok;
        totals.moved += element ? 0 : moved.length;
        totals.missing += element ? 0 : missing.length;
        totals.candidates_ok += element ? ok : 0;
        totals.candidates_moved += element ? moved.length : 0;
        totals.candidates_missing += element ? missing.length : 0;
        /** @type {{status: 'ok' | 'testid-missing' | 'no-candidates' | 'lost', testids_missing: string[]} | undefined} */
        let anchor;
        if (change.anchor || element) {
            const testids = Array.isArray(change.anchor?.testids) ? change.anchor.testids.filter((/** @type {unknown} */ id) => typeof id === 'string') : [];
            const testidsMissing = index ? testids.filter((/** @type {string} */ id) => !testidKnown(id, index)) : [];
            const listed = (change.occurrences ?? []).length;
            const status = element && !listed ? 'no-candidates' : element && ok + moved.length === 0 ? 'lost' : testidsMissing.length ? 'testid-missing' : 'ok';
            anchor = {status, testids_missing: testidsMissing};
            if (status === 'lost') totals.anchors_lost++;
            totals.anchor_testids_missing += testidsMissing.length;
        }
        return {id: change.id, layer: change.layer, target: change.target, ok, moved, missing, definitions, ...(anchor ? {anchor} : {})};
    });
    return {schema: VERIFY_SCHEMA, exported_with: doc.catalog_hash ?? null, catalog_hash_now: catalogHash, catalog_hash_match: doc.catalog_hash === catalogHash, totals, changes};
}

/** @param {ReturnType<typeof verifyExport>} report */
function printHuman(report) {
    const t = report.totals;
    console.log(`Designer Lab export check — ${t.changes} changes: ${t.ok} occurrences in place, ${t.moved} moved, ${t.missing} missing, ${t.definitions_changed} definitions changed.`);
    if (t.candidates_ok + t.candidates_moved + t.candidates_missing) console.log(`Specialisations: ${t.candidates_ok} candidates in place, ${t.candidates_moved} moved, ${t.candidates_missing} gone; ${t.anchors_lost} lost every candidate; ${t.anchor_testids_missing} test ids no longer in the code.`);
    console.log(report.catalog_hash_match ? 'Catalogue unchanged since the export.' : `Catalogue changed since the export (${report.exported_with ?? 'no hash'} → ${report.catalog_hash_now}).`);
    for (const c of report.changes) {
        const anchor = 'anchor' in c ? c.anchor : undefined;
        if (!c.moved.length && !c.missing.length && !c.definitions.some((d) => d.status !== 'ok' || d.value_now !== undefined) && (!anchor || anchor.status === 'ok')) continue;
        console.log(`\n${c.id}`);
        for (const m of c.moved) console.log(`  moved   ${m.file}:${m.line} → ${m.to_line}  ${m.raw ?? ''}`);
        for (const m of c.missing) console.log(`  ${c.layer === 'element' ? 'gone   ' : 'MISSING'} ${m.file}:${m.line}  ${m.raw ?? ''}`);
        for (const d of c.definitions) if (d.status !== 'ok' || d.value_now !== undefined) console.log(`  definition ${d.file}:${d.line} ${d.status}${d.to_line ? ` → ${d.to_line}` : ''}${d.value_now !== undefined ? ` value now ${d.value_now}` : ''}`);
        if (anchor && anchor.status !== 'ok') console.log(`  anchor ${anchor.status.toUpperCase()}${anchor.testids_missing.length ? ` — test ids not in the code: ${anchor.testids_missing.join(', ')}` : ''}`);
    }
}

/** @param {string[]} argv */
function main(argv) {
    const file = argv.find((a) => !a.startsWith('--') && argv[argv.indexOf(a) - 1] !== '--root');
    const rootAt = argv.indexOf('--root');
    if (!file) {
        console.error('usage: verify-export.mjs <designer-lab-changes.json> [--json] [--root <frontend>]');
        return 2;
    }
    let report;
    try {
        report = verifyExport(JSON.parse(readFileSync(file, 'utf8')), {root: rootAt === -1 ? FRONTEND_DIR : resolve(argv[rootAt + 1])});
    } catch (e) {
        console.error(`verify-export: ${e instanceof Error ? e.message : String(e)}`);
        return 2;
    }
    if (argv.includes('--json')) console.log(JSON.stringify(report, null, 2));
    else printHuman(report);
    return report.totals.missing || report.totals.anchors_lost ? 1 : 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
