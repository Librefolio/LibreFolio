#!/usr/bin/env node
/**
 * Branch-arm counter for a set of files inside an istanbul coverage-final.json.
 *
 * Counting rule (the one asked for): for every entry of `b`, every element of the
 * array is one *arm*, covered when its hit count is > 0. Lines come from
 * `statementMap`/`s` the same way. Pass several json files to union them first —
 * a file measured by two runs is covered by either.
 *
 * Usage: node scripts/branch-arms.mjs <coverage-final.json> [more.json ...] [--only=substr,substr]
 *
 * `--only` selects which files to report by path suffix; it defaults to the sync
 * modal family, which is what the tool was first written for.
 */
import {readFileSync} from 'node:fs';

const args = process.argv.slice(2);
const only = args.find((a) => a.startsWith('--only='));
const TARGETS = only ? only.slice('--only='.length).split(',').filter(Boolean) : ['ui/modals/SyncModalBase.svelte', 'ui/modals/PageSyncModal.svelte', 'assets/AssetSyncModal.svelte', 'fx/FxSyncModal.svelte'];

const union = new Map();
for (const path of args.filter((a) => !a.startsWith('--'))) {
    const raw = JSON.parse(readFileSync(path, 'utf8'));
    for (const [file, data] of Object.entries(raw)) {
        if (!TARGETS.some((t) => file.endsWith(t))) continue;
        const key = TARGETS.find((t) => file.endsWith(t));
        const prev = union.get(key);
        if (!prev) {
            union.set(key, {b: structuredClone(data.b), s: structuredClone(data.s)});
            continue;
        }
        for (const [id, arms] of Object.entries(data.b)) {
            if (!prev.b[id]) prev.b[id] = arms.slice();
            else arms.forEach((n, i) => (prev.b[id][i] = (prev.b[id][i] ?? 0) + n));
        }
        for (const [id, n] of Object.entries(data.s)) prev.s[id] = (prev.s[id] ?? 0) + n;
    }
}

const rows = [];
for (const key of TARGETS) {
    const data = union.get(key);
    if (!data) {
        rows.push({file: key, branches: 'absent', lines: 'absent'});
        continue;
    }
    const arms = Object.values(data.b).flat();
    const armsHit = arms.filter((n) => n > 0).length;
    const stmts = Object.values(data.s);
    const stmtsHit = stmts.filter((n) => n > 0).length;
    rows.push({
        file: key,
        branches: `${armsHit}/${arms.length} (${arms.length ? ((armsHit / arms.length) * 100).toFixed(1) : '0.0'}%)`,
        lines: `${stmtsHit}/${stmts.length} (${stmts.length ? ((stmtsHit / stmts.length) * 100).toFixed(1) : '0.0'}%)`,
    });
}
console.table(rows);
