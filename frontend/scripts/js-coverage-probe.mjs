/**
 * Test-infrastructure probe of the E2E JS coverage collection (project 71, block 3, C2). Not part of any report.
 *
 *   node scripts/js-coverage-probe.mjs timing <dir> [--json]
 *   node scripts/js-coverage-probe.mjs compare <dirA> <dirB> [--json]
 *
 * `timing` reads the stopwatch lines the `jsCoverage` fixture writes under `LF_COV_TIMING=1`
 * (`coverage-js/timing/worker-<parallelIndex>-<pid>.jsonl`, one JSON object per test: `evaluate_ms`, `payload_bytes`,
 * `merge_ms`, `flush_ms`, `rss_mb`, `heap_mb`) and prints, per field, how many tests, the mean, the median (p50), the
 * 95th percentile, the total and the maximum. The total of the three times is what the collection costs the run outside
 * the tests; the maximum of the memory is what a worker reached. Percentiles are nearest-rank: a value that was measured,
 * never an interpolation between two. A line that is not JSON is counted as skipped, and said.
 *
 * `compare` holds two directories of worker files to each other (step 3.8: `coverage-js/e2e-raw-full/`, the full sum of
 * `LF_COV_COMPARE=1`, against `coverage-js/e2e-raw/`, the light one). Each directory is summed with istanbul's own
 * `CoverageMap.merge`, as the report sums it, and the two sums are compared file by file: the files on one side only, and
 * the files whose maps or counters differ. A file whose two sides differ only by istanbul's fold — the same file, folded on
 * one side because that side merged it more often, which renumbers and merges items at one position — is listed apart
 * (`foldOnly`) and is not a difference: both sides are folded and compared again before a file is called different. Exit 0
 * when nothing differs, 1 otherwise.
 *
 * `--json` prints the same as one JSON object, for a test or a script to read.
 */
import fs from 'node:fs';
import {createRequire} from 'node:module';
import path from 'node:path';
import {isDeepStrictEqual} from 'node:util';
import {pathToFileURL} from 'node:url';

// The same library, from the same `node_modules`, as the sink and the report.
const libCoverage = createRequire(import.meta.url)('istanbul-lib-coverage');

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

/** A directory of worker files summed as the report sums them: one istanbul map, plain data. */
export function sumDirectory(dir) {
    const map = libCoverage.createCoverageMap({});
    for (const name of fs.readdirSync(dir).sort()) {
        if (!/^worker-\d+-\d+\.json$/.test(name)) continue;
        map.merge(JSON.parse(fs.readFileSync(path.join(dir, name), 'utf-8')));
    }
    return JSON.parse(JSON.stringify(map.toJSON()));
}

/** istanbul's fold of one file coverage: merged with a copy of itself at zero, which keys its items by position. */
function folded(file) {
    const zero = JSON.parse(JSON.stringify(file));
    for (const counter of ['s', 'f']) for (const key of Object.keys(zero[counter])) zero[counter][key] = 0;
    for (const counter of ['b', 'bT']) if (zero[counter]) for (const key of Object.keys(zero[counter])) zero[counter][key] = zero[counter][key].map(() => 0);
    const map = libCoverage.createCoverageMap({[file.path]: JSON.parse(JSON.stringify(file))});
    map.merge({[file.path]: zero});
    return JSON.parse(JSON.stringify(map.toJSON()))[file.path];
}

/** Compare two sums: files on one side only, files that differ, files that differ only by istanbul's fold. */
export function compareSums(a, b) {
    const onlyA = Object.keys(a)
        .filter((key) => !(key in b))
        .sort();
    const onlyB = Object.keys(b)
        .filter((key) => !(key in a))
        .sort();
    const differ = [];
    const foldOnly = [];
    for (const key of Object.keys(a)
        .filter((k) => k in b)
        .sort()) {
        if (isDeepStrictEqual(a[key], b[key])) continue;
        if (isDeepStrictEqual(folded(a[key]), folded(b[key]))) foldOnly.push(key);
        else differ.push(key);
    }
    return {onlyA, onlyB, differ, foldOnly};
}

function printCompare(dirA, dirB, asJson) {
    const result = compareSums(sumDirectory(dirA), sumDirectory(dirB));
    if (asJson) {
        console.log(JSON.stringify(result));
    } else {
        const list = (names) => (names.length ? `: ${names.slice(0, 10).join(', ')}${names.length > 10 ? ', …' : ''}` : '');
        console.log(`[compare] ${dirA} ↔ ${dirB}`);
        console.log(`  only in the first:  ${result.onlyA.length}${list(result.onlyA)}`);
        console.log(`  only in the second: ${result.onlyB.length}${list(result.onlyB)}`);
        console.log(`  different:          ${result.differ.length}${list(result.differ)}`);
        console.log(`  differ only by istanbul's fold (not a difference): ${result.foldOnly.length}${list(result.foldOnly)}`);
    }
    return result.onlyA.length + result.onlyB.length + result.differ.length === 0 ? 0 : 1;
}

function main(argv) {
    const [command, first, second, ...rest] = argv;
    if (command === 'timing' && first) {
        printTiming(first, [second, ...rest].includes('--json'));
        return 0;
    }
    if (command === 'compare' && first && second) return printCompare(first, second, rest.includes('--json'));
    console.error('usage: node scripts/js-coverage-probe.mjs timing <dir> [--json] | compare <dirA> <dirB> [--json]');
    return 2;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) process.exit(main(process.argv.slice(2)));
