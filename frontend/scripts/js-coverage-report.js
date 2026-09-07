/**
 * Merges istanbul coverage JSON files into one report.
 *
 *   node scripts/js-coverage-report.js <outDir> "<Report name>" <input…>
 *
 * Every input is either a `coverage-final.json` or a directory of per-test JSON
 * files. They are merged with `istanbul-lib-coverage`, which is the canonical
 * operation for this format: same file, same statement map, hit counts summed.
 *
 * Why istanbul end to end, and no monocart. Monocart's job was to take the V8
 * ranges Chromium reports about *bundles* and walk them back through sourcemaps
 * to the `.svelte` and `.ts` anyone reads. That job disappeared the day the
 * build started carrying its own instrumentation: `window.__coverage__` is
 * already in source coordinates. What remained was a cost — V8 reports an empty
 * branch map for a Svelte template, so every `{#if}` in the app was outside the
 * count — and an ambiguity: with both formats in the same cache, a file ended
 * up with one map or the other unpredictably, and `.ts` files kept V8's, which
 * was systematically coarser.
 *
 * Filtering lives here rather than in a config: it is three rules.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import libCoverage from 'istanbul-lib-coverage';
import libReport from 'istanbul-lib-report';
import libSourceMaps from 'istanbul-lib-source-maps';
import reports from 'istanbul-reports';

const FRONTEND_DIR = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

/**
 * Generated sources: ours by location, not ours by authorship.
 *
 * `api/generated.ts` comes out of `openapi-zod-client`: 17k lines of Zod
 * validators the app crosses on every call, hence covered by construction.
 * Counting them adds hundreds of always-green statements to the denominator —
 * it moves the overall percentage up without anyone having tested anything, and
 * that percentage exists to decide where the next tests go. If it is wrong, the
 * generator is wrong, and the place to notice is `./dev.py api sync`.
 */
const GENERATED = new Set(['src/lib/api/generated.ts']);

/** Normalise to a frontend-relative POSIX path, the key both levels agree on. */
function normalise(filePath) {
    const p = filePath.replace(/\\/g, '/');
    const idx = p.lastIndexOf('/src/');
    return idx === -1 ? p : p.slice(idx + 1);
}

function keep(relPath) {
    if (!relPath.startsWith('src/')) return false;
    if (relPath.includes('/node_modules/')) return false;
    if (GENERATED.has(relPath)) return false;
    if (/\.(test|spec)\.[tj]s$/.test(relPath)) return false;
    if (/\/__(tests|mocks)__\//.test(relPath)) return false;
    return true;
}

function* jsonFiles(input) {
    const full = path.isAbsolute(input) ? input : path.join(FRONTEND_DIR, input);
    let stat;
    try {
        stat = fs.statSync(full);
    } catch {
        return;
    }
    if (stat.isFile()) {
        yield full;
        return;
    }
    for (const entry of fs.readdirSync(full, {withFileTypes: true})) {
        if (entry.isDirectory()) yield* jsonFiles(path.join(full, entry.name));
        else if (entry.name.endsWith('.json')) yield path.join(full, entry.name);
    }
}

const [outDir, reportName, ...inputs] = process.argv.slice(2);
if (!outDir || inputs.length === 0) {
    console.error('usage: js-coverage-report.js <outDir> <name> <input…>');
    process.exit(2);
}

const map = libCoverage.createCoverageMap({});
let merged = 0;

// One map per input, remapped before the levels meet.
//
// This ordering is the whole correctness of the merge. `vite-plugin-istanbul`
// instruments *after* the rest of the pipeline, so the counters it produces are
// keyed to the transformed file — `formatPercent.ts` reported its first
// statement at line 2, inside the docblock. Vitest's provider remaps before
// writing, so it reported the same statement at line 36, where it actually is.
// Merging those two is merging two different coordinate systems: istanbul keys
// a statement by `start.line|start.column|end.line|end.column`, finds no match,
// and *appends*. Measured on the first combined report: 119 291 statements,
// exactly the sum of 83 527 and 35 764 — every shared file counted twice, with
// a denominator that could only make the percentage look worse than the truth.
for (const input of inputs) {
    const level = libCoverage.createCoverageMap({});
    let seen = 0;
    for (const file of jsonFiles(input)) {
        let data;
        try {
            data = JSON.parse(fs.readFileSync(file, 'utf-8'));
        } catch {
            continue; // A half-written file from a killed worker is not fatal.
        }
        const filtered = {};
        for (const [key, value] of Object.entries(data)) {
            if (!value || !value.statementMap) continue;
            const rel = normalise(value.path || key);
            if (!keep(rel)) continue;
            filtered[rel] = {...value, path: rel};
        }
        if (Object.keys(filtered).length === 0) continue;
        level.merge(filtered);
        seen += 1;
    }
    if (seen === 0) continue;
    // A no-op for data that carries no `inputSourceMap` — the unit level, which
    // its provider has already remapped.
    const remapped = await libSourceMaps.createSourceMapStore().transformCoverage(level);
    // Re-key afterwards, not before: the remapper resolves each source through
    // the sourcemap and hands back an *absolute* path, while the unit level —
    // untouched, because it has no map to follow — keeps the relative one. Two
    // keys for one file, and the accumulator merges neither into the other.
    const rekeyed = {};
    for (const [key, entry] of Object.entries(remapped.data)) {
        // `CoverageMap.data` holds `FileCoverage` instances, whose own payload
        // lives under `.data`; spreading the wrapper yields `{data, path}` and
        // istanbul rejects it as a malformed file coverage.
        const value = entry.data ?? entry;
        const rel = normalise(value.path || key);
        if (!keep(rel)) continue;
        // Drop the map once it has been followed. Keeping it would make this
        // report un-mergeable with itself: a second pass would remap already
        // remapped positions, and the combined step reads these reports.
        const {inputSourceMap: _dropped, ...rest} = value;
        rekeyed[rel] = {...rest, path: rel};
    }
    map.merge(rekeyed);
    merged += seen;
}

if (merged === 0) {
    console.error(`[js-coverage] no usable coverage found in: ${inputs.join(', ')}`);
    process.exit(1);
}

const outFull = path.isAbsolute(outDir) ? outDir : path.join(FRONTEND_DIR, outDir);
fs.rmSync(outFull, {recursive: true, force: true});
fs.mkdirSync(outFull, {recursive: true});
fs.writeFileSync(path.join(outFull, 'coverage-final.json'), JSON.stringify(map.toJSON()));

const context = libReport.createContext({
    dir: outFull,
    coverageMap: map,
    // The reporter reads the sources to render the annotated lines; without
    // this it looks for `src/…` relative to the process cwd.
    sourceFinder: (file) => fs.readFileSync(path.join(FRONTEND_DIR, file), 'utf-8'),
});
reports.create('html', {verbose: false}).execute(context);

const s = map.getCoverageSummary();
const pct = (m) => `${m.pct.toFixed(2).padStart(6)} %`;
const row = (label, m) => `│ ${label.padEnd(10)} │ ${pct(m)} │ ${String(m.covered).padStart(7)} │ ${String(m.total).padStart(7)} │`;
console.log(`[${reportName || 'coverage'}] merged ${merged} file(s)`);
console.log('┌────────────┬──────────┬─────────┬─────────┐');
console.log('│ Name       │ Coverage │ Covered │   Total │');
console.log('├────────────┼──────────┼─────────┼─────────┤');
console.log(row('Statements', s.statements));
console.log(row('Branches', s.branches));
console.log(row('Functions', s.functions));
console.log(row('Lines', s.lines));
console.log('└────────────┴──────────┴─────────┴─────────┘');
