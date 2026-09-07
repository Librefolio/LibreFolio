#!/usr/bin/env node
/**
 * Count istanbul branch *arms* for a set of files from a coverage-final.json.
 *
 * Every entry of `b` is an array with one counter per arm; an arm is covered
 * when its counter is > 0. This is the unit the campaign reports in, because a
 * `{#if}` exercised on one side only is half-covered and a percentage over
 * "branches" hides that.
 *
 * Usage: node scripts/arm-count.mjs <coverage-final.json> [pathSubstring]
 *
 * With no filter it reports every file in the report; pass a path fragment to
 * narrow it to one area.
 */
import {readFileSync} from 'node:fs';

const [, , jsonPath, filter = ''] = process.argv;
const data = JSON.parse(readFileSync(jsonPath, 'utf8'));

const rows = [];
for (const [file, entry] of Object.entries(data)) {
    if (!file.includes(filter)) continue;
    let arms = 0;
    let armsHit = 0;
    for (const counters of Object.values(entry.b ?? {})) {
        for (const c of counters) {
            arms += 1;
            if (c > 0) armsHit += 1;
        }
    }
    const stmts = Object.values(entry.s ?? {});
    const lines = stmts.length;
    const linesHit = stmts.filter((c) => c > 0).length;
    rows.push({file: file.split('/').pop(), arms, armsHit, lines, linesHit});
}

rows.sort((a, b) => a.file.localeCompare(b.file));
const pct = (hit, total) => (total === 0 ? '  n/a' : `${((hit / total) * 100).toFixed(1)}%`);
console.log('file'.padEnd(30), 'arms'.padStart(12), 'arm%'.padStart(8), 'stmt'.padStart(12), 'stmt%'.padStart(8));
let ta = 0;
let th = 0;
for (const r of rows) {
    console.log(r.file.padEnd(30), `${r.armsHit}/${r.arms}`.padStart(12), pct(r.armsHit, r.arms).padStart(8), `${r.linesHit}/${r.lines}`.padStart(12), pct(r.linesHit, r.lines).padStart(8));
    ta += r.arms;
    th += r.armsHit;
}
console.log('TOTAL'.padEnd(30), `${th}/${ta}`.padStart(12), pct(th, ta).padStart(8));
