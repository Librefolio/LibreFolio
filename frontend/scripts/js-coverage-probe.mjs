/**
 * Test-infrastructure probe of the E2E JS coverage collection (project 71, block 3, C2). Not part of any report.
 *
 *   node scripts/js-coverage-probe.mjs timing <dir> [--json]
 *
 * `timing` reads the stopwatch lines the `jsCoverage` fixture writes under `LF_COV_TIMING=1`
 * (`coverage-js/timing/worker-<parallelIndex>-<pid>.jsonl`, one JSON object per test: `evaluate_ms`, `payload_bytes`,
 * `merge_ms`, `flush_ms`, `rss_mb`, `heap_mb`) and prints, per field, how many tests, the mean, the median (p50), the
 * 95th percentile, the total and the maximum. The total of the three times is what the collection costs the run outside
 * the tests; the maximum of the memory is what a worker reached. Percentiles are nearest-rank: a value that was measured,
 * never an interpolation between two. A line that is not JSON is counted as skipped, and said.
 *
 * `--json` prints the same as one JSON object, for a test or a script to read.
 */
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

export const TIMING_FIELDS = ['evaluate_ms', 'payload_bytes', 'merge_ms', 'flush_ms', 'rss_mb', 'heap_mb'];

/** Nearest-rank percentile of an ascending array: the value at rank ceil(q·n). */
function nearestRank(sorted, q) {
    return sorted[Math.max(0, Math.ceil(q * sorted.length) - 1)];
}

/** Read every `*.jsonl` of `dir`: the records and the number of lines that could not be parsed. */
export function readTiming(dir) {
    const records = [];
    let skipped = 0;
    let files = 0;
    for (const name of fs.readdirSync(dir).sort()) {
        if (!name.endsWith('.jsonl')) continue;
        files += 1;
        for (const line of fs.readFileSync(path.join(dir, name), 'utf-8').split('\n')) {
            if (!line.trim()) continue;
            try {
                records.push(JSON.parse(line));
            } catch {
                skipped += 1;
            }
        }
    }
    return {records, skipped, files};
}

/** Per field: n, mean, p50, p95, total, max. A field no record carries is left out. */
export function summarizeTiming(records) {
    const out = {};
    for (const field of TIMING_FIELDS) {
        const values = records.map((r) => r[field]).filter((v) => typeof v === 'number' && Number.isFinite(v));
        if (values.length === 0) continue;
        const sorted = [...values].sort((a, b) => a - b);
        const total = values.reduce((a, b) => a + b, 0);
        out[field] = {n: values.length, mean: total / values.length, p50: nearestRank(sorted, 0.5), p95: nearestRank(sorted, 0.95), total, max: sorted[sorted.length - 1]};
    }
    return out;
}

function printTiming(dir, asJson) {
    const {records, skipped, files} = readTiming(dir);
    const fields = summarizeTiming(records);
    if (asJson) {
        console.log(JSON.stringify({files, tests: records.length, skipped, fields}));
        return;
    }
    console.log(`[timing] ${records.length} test(s) in ${files} worker file(s)${skipped ? `, ${skipped} unreadable line(s) skipped` : ''}`);
    const fmt = (v) => (Math.abs(v) >= 1000 ? v.toFixed(0) : v.toFixed(2));
    console.log(`${'field'.padEnd(14)} ${'mean'.padStart(12)} ${'p50'.padStart(12)} ${'p95'.padStart(12)} ${'total'.padStart(14)} ${'max'.padStart(12)}`);
    for (const [field, s] of Object.entries(fields)) {
        console.log(`${field.padEnd(14)} ${fmt(s.mean).padStart(12)} ${fmt(s.p50).padStart(12)} ${fmt(s.p95).padStart(12)} ${fmt(s.total).padStart(14)} ${fmt(s.max).padStart(12)}`);
    }
}

function main(argv) {
    const [command, dir, ...rest] = argv;
    if (command === 'timing' && dir) {
        printTiming(dir, rest.includes('--json'));
        return 0;
    }
    console.error('usage: node scripts/js-coverage-probe.mjs timing <dir> [--json]');
    return 2;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));
