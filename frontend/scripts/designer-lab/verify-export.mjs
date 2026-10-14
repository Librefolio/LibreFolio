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
 * Exit code: 0 when nothing is missing (moved occurrences are fine), 1 when something is missing, 2 on bad input.
 */

import {existsSync, readFileSync} from 'node:fs';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {FRONTEND_DIR, scanColors} from './scan-colors.mjs';

export const VERIFY_SCHEMA = 'lf-designer-lab-verify/1';

/**
 * @param {string} root
 * @returns {(file: string) => string[] | null}
 */
function fileReader(root) {
    /** @type {Map<string, string[] | null>} */
    const cache = new Map();
    return (file) => {
        if (!cache.has(file)) {
            const full = join(root, file);
            cache.set(file, existsSync(full) ? readFileSync(full, 'utf8').split('\n') : null);
        }
        return /** @type {string[] | null} */ (cache.get(file));
    };
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
 * @param {{root?: string, catalogHash?: string}} [opts]
 */
export function verifyExport(doc, opts = {}) {
    const root = opts.root ?? FRONTEND_DIR;
    if (doc?.schema !== 'lf-designer-lab/1' || !Array.isArray(doc.changes)) throw new Error('not a lf-designer-lab/1 export');
    const read = fileReader(root);
    const catalogHash = opts.catalogHash ?? scanColors({root}).meta.hash;
    const totals = {changes: doc.changes.length, ok: 0, moved: 0, missing: 0, definitions_changed: 0};
    const changes = doc.changes.map((/** @type {any} */ change) => {
        /** @type {{file: string, line: number, raw?: string, to_line?: number}[]} */
        const moved = [];
        /** @type {{file: string, line: number, raw?: string}[]} */
        const missing = [];
        let ok = 0;
        for (const occ of change.occurrences ?? []) {
            const lines = read(occ.file);
            const where = lines ? locate(lines, occ.line, needleOf(occ, change)) : {status: 'missing'};
            if (where.status === 'ok') ok++;
            else if (where.status === 'moved') moved.push({file: occ.file, line: occ.line, raw: occ.raw, to_line: where.line});
            else missing.push({file: occ.file, line: occ.line, raw: occ.raw});
        }
        /** @type {{file: string, line: number, status: string, to_line?: number, value_now?: string}[]} */
        const definitions = [];
        for (const def of change.definitions ?? []) {
            const lines = read(def.file);
            const where = lines ? locate(lines, def.line, `${change.target}:`) : {status: 'missing'};
            const entry = {file: def.file, line: def.line, status: where.status, ...(where.line && where.status === 'moved' ? {to_line: where.line} : {})};
            const at = where.line ? lines?.[where.line - 1] : undefined;
            const value = at ? /:\s*([^;]+);?/.exec(at.slice(at.indexOf(`${change.target}:`)))?.[1]?.trim() : undefined;
            if (value !== undefined && value !== def.value) {
                Object.assign(entry, {value_now: value});
                totals.definitions_changed++;
            }
            definitions.push(entry);
        }
        totals.ok += ok;
        totals.moved += moved.length;
        totals.missing += missing.length;
        return {id: change.id, layer: change.layer, target: change.target, ok, moved, missing, definitions};
    });
    return {schema: VERIFY_SCHEMA, exported_with: doc.catalog_hash ?? null, catalog_hash_now: catalogHash, catalog_hash_match: doc.catalog_hash === catalogHash, totals, changes};
}

/** @param {ReturnType<typeof verifyExport>} report */
function printHuman(report) {
    const t = report.totals;
    console.log(`Designer Lab export check — ${t.changes} changes: ${t.ok} occurrences in place, ${t.moved} moved, ${t.missing} missing, ${t.definitions_changed} definitions changed.`);
    console.log(report.catalog_hash_match ? 'Catalogue unchanged since the export.' : `Catalogue changed since the export (${report.exported_with ?? 'no hash'} → ${report.catalog_hash_now}).`);
    for (const c of report.changes) {
        if (!c.moved.length && !c.missing.length && !c.definitions.some((d) => d.status !== 'ok' || d.value_now !== undefined)) continue;
        console.log(`\n${c.id}`);
        for (const m of c.moved) console.log(`  moved   ${m.file}:${m.line} → ${m.to_line}  ${m.raw ?? ''}`);
        for (const m of c.missing) console.log(`  MISSING ${m.file}:${m.line}  ${m.raw ?? ''}`);
        for (const d of c.definitions) if (d.status !== 'ok' || d.value_now !== undefined) console.log(`  definition ${d.file}:${d.line} ${d.status}${d.to_line ? ` → ${d.to_line}` : ''}${d.value_now !== undefined ? ` value now ${d.value_now}` : ''}`);
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
    return report.totals.missing ? 1 : 0;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = main(process.argv.slice(2));
